"""Format-trap tests on synthetic data (no game files needed)."""
import os
import struct
import tempfile
import unittest

import numpy as np

from dinkex import ff, hard, mapdata
from dinkex.bmp import bmp_size, to_rgba
from dinkex.sequences import (SequenceModel, atol, default_hardbox, default_origin, tokenize)
from dinkex.gfx import Graphics
from tests.helpers import make_bmp8, make_ff


class FFTests(unittest.TestCase):
    def test_sentinel_is_not_an_entry(self):
        data = make_ff([("A-01.BMP", b"x" * 10), ("A-02.BMP", b"y" * 7)])
        es = ff.parse_ff(data)
        self.assertEqual([e.name for e in es], ["a-01.bmp", "a-02.bmp"])   # lower-cased, no sentinel
        self.assertEqual([e.size for e in es], [10, 7])
        self.assertEqual(data[es[1].offset:es[1].offset + es[1].size], b"y" * 7)

    def test_zero_next_offset_skips_one_record(self):
        # FFReader.cpp:157: if next offset is 0, use the record after it
        body = b"A" * 5
        count = 3
        hdr = 4 + count * 17
        recs = struct.pack("<i13s", hdr, b"ONE.BMP".ljust(13, b"\0"))
        recs += struct.pack("<i13s", 0, b"SKIP".ljust(13, b"\0"))
        recs += struct.pack("<i13s", hdr + 5, b"\0" * 13)
        es = ff.parse_ff(struct.pack("<i", count) + recs + body)
        one = [e for e in es if e.name == "one.bmp"][0]
        self.assertEqual(one.size, 5)

    def test_non_bmp_entry_is_reported_by_catalog(self):
        with tempfile.TemporaryDirectory() as d:
            gdir = os.path.join(d, "graphics", "x")
            os.makedirs(gdir)
            bmp = make_bmp8(4, 4)
            with open(os.path.join(gdir, "dir.ff"), "wb") as f:
                f.write(make_ff([("DIR.FF", b"hdr"), ("X-01.BMP", bmp)]))
            cen = Graphics(d).census()
            self.assertEqual(cen["ff_bmp_entries"], 1)
            self.assertEqual(cen["ff_nonbmp_entries"], 1)
            self.assertEqual(cen["total_bmps"], 1)


class HardDatTests(unittest.TestCase):
    def _data(self, index_entries, short=True):
        blocks = bytearray(hard.BLOCK_COUNT * hard.BLOCK_BYTES)
        # block 7: left half solid (x < 25), block 8: all 2, block 9: a lone 3
        def put(b, x, y, v):
            blocks[b * hard.BLOCK_BYTES + x * 51 + y] = v      # [x][y] layout
        for x in range(25):
            for y in range(50):
                put(7, x, y, 1)
        for x in range(50):
            for y in range(50):
                put(8, x, y, 2)
        put(9, 3, 4, 3)
        idx = struct.pack("<%di" % len(index_entries), *index_entries)
        return bytes(blocks) + idx

    def test_short_file_zero_fills_index(self):
        h = hard.HardDat(self._data([7, 8, 9]))
        self.assertEqual(h.short_by, hard.FULL_SIZE - len(self._data([7, 8, 9])))
        self.assertEqual(h.index_entries_in_file, 3)
        self.assertEqual(h.lookup(1, 0), (8, "index", True))
        # entry not in the file reads as 0 (engine memsets before the short read)
        self.assertEqual(h.lookup(5000, 0), (0, "index_beyond_file", True))

    def test_shipped_size_gap(self):
        self.assertEqual(hard.FULL_SIZE - 2107392, 11008)
        self.assertEqual(hard.INDEX_OFFSET, 2086400)

    def test_xy_layout_is_transposed_for_images(self):
        h = hard.HardDat(self._data([7]))
        t = h.tiles[7]            # [y][x]
        self.assertTrue((t[:, :25] == 1).all())
        self.assertTrue((t[:, 25:] == 0).all())
        self.assertEqual(h.tiles[9][4, 3], 3)   # px[x=3][y=4] -> [y=4][x=3]

    def test_althard_overrides_index(self):
        h = hard.HardDat(self._data([7, 8]))
        self.assertEqual(h.lookup(0, 0)[0], 7)
        self.assertEqual(h.lookup(0, 8), (8, "althard", True))

    def test_out_of_range_index_tile_is_skipped(self):
        h = hard.HardDat(self._data([8, 52421, -1]))
        self.assertEqual(h.lookup(1, 0)[2], False)
        self.assertEqual(h.lookup(2, 0)[2], False)
        tiles = [{"num": 0, "althard": 0}, {"num": 1, "althard": 0}, {"num": 2, "althard": 0}] + \
                [{"num": 0, "althard": 0}] * 93
        hit, skipped = hard.build_tile_layer(h, tiles)
        self.assertEqual(skipped, [1, 2])
        self.assertTrue((hit[0:50, 0:50] == 2).all())          # tile 0 -> hardness block 8
        self.assertTrue((hit[0:50, 50:150] == 0).all())         # skipped cells stay 0
        self.assertTrue((hit[50:100, 0:50] == 2).all())         # tile 12 on row 1

    def test_stamp_rect_clips_and_uses_20px_offset(self):
        sp = {"x": 120, "y": 50}
        hb = {"left": -10, "top": -5, "right": 10, "bottom": 5}
        self.assertEqual(hard.stamp_rect(sp, hb), (90, 45, 110, 55))
        self.assertIsNone(hard.stamp_rect({"x": 10, "y": 395}, hb))     # x-20 < 0 for the whole box
        self.assertIsNone(hard.stamp_rect({"x": 5, "y": 5}, {"left": -40, "top": 0, "right": -30, "bottom": 5}))
        r = hard.stamp_rect({"x": 640, "y": 405}, {"left": -30, "top": -10, "right": 30, "bottom": 10})
        self.assertEqual(r, (590, 395, 600, 400))

    def test_rank_order_uses_que_then_y_ties_to_lower_index(self):
        sp = {i: {"active": True, "que": 0, "y": 100} for i in (3, 5, 9)}
        sp[5]["y"] = 50
        sp[9]["que"] = 10
        sp[100] = {"active": True, "que": 0, "y": 0}      # index 100 is never placed
        self.assertEqual(hard.placement_rank(sp), [9, 5, 3])

    def test_hitmap_stamps_in_rank_order_and_vision_gates(self):
        h = hard.HardDat(self._data([7]))
        tiles = [{"num": 99, "althard": 0}] * 96        # index beyond file -> block 0 (empty)
        box = {"left": -5, "top": -5, "right": 5, "bottom": 5}
        base = {"active": True, "que": 0, "hard": 0, "prop": 0, "vision": 0, "type": 1}
        sprites = {
            1: dict(base, x=120, y=100),                      # solid
            2: dict(base, x=300, y=100, prop=1),              # warp
            3: dict(base, x=400, y=100, vision=2),            # gated
            4: dict(base, x=500, y=100, hard=1),              # no hardness (inverted flag)
        }
        codes, owner, _ = hard.build_hitmap(h, tiles, sprites, lambda s: box, vision=0)
        self.assertEqual(codes[100, 100], hard.CODE_SPRITE)
        self.assertEqual(owner[100, 100], 1)
        self.assertEqual(codes[100, 280], hard.CODE_WARP)
        self.assertEqual(codes[100, 380], 0)
        self.assertEqual(codes[100, 480], 0)
        codes2, _, _ = hard.build_hitmap(h, tiles, sprites, lambda s: box, vision=2)
        self.assertEqual(codes2[100, 380], hard.CODE_SPRITE)


class TileMathTests(unittest.TestCase):
    def test_set_and_cell(self):
        self.assertEqual(mapdata.tile_set_and_cell(0), (1, 0))
        self.assertEqual(mapdata.tile_set_and_cell(127), (1, 127))
        self.assertEqual(mapdata.tile_set_and_cell(128), (2, 0))
        self.assertEqual(mapdata.tile_set_and_cell(5211), (41, 91))

    def test_source_rect_12_per_row(self):
        self.assertEqual(mapdata.tile_source_rect(0), (0, 0, 50, 50))
        self.assertEqual(mapdata.tile_source_rect(11), (550, 0, 50, 50))
        self.assertEqual(mapdata.tile_source_rect(12), (0, 50, 50, 50))
        self.assertEqual(mapdata.tile_source_rect(30), (300, 100, 50, 50))

    def test_screen_grid(self):
        self.assertEqual(mapdata.screen_col_row(1), (0, 0))
        self.assertEqual(mapdata.screen_col_row(32), (31, 0))
        self.assertEqual(mapdata.screen_col_row(33), (0, 1))
        self.assertEqual(mapdata.screen_col_row(768), (31, 23))

    def test_music(self):
        self.assertEqual(mapdata.music_info(0)["action"], "none")
        self.assertEqual(mapdata.music_info(-1)["action"], "stop")
        self.assertEqual(mapdata.music_info(1007)["name"], "7.mid")
        self.assertEqual(mapdata.music_info(105)["name"], "105.mid")
        self.assertEqual(mapdata.music_info(7, {"7.ogg": "7.ogg", "7.mid": "7.mid"})["file"], "sound/7.ogg")


class RecordTests(unittest.TestCase):
    def test_sprite_offsets(self):
        rec = bytearray(220)
        struct.pack_into("<6i", rec, 0, 300, 200, 12, 3, 1, 150)
        rec[24] = 1
        struct.pack_into("<3i", rec, 28, 7, 8, 9)
        rec[40:46] = b"S1-Bob"
        rec[53:56] = b"hit"
        struct.pack_into("<i", rec, 120, 1)             # hard
        struct.pack_into("<4i", rec, 124, 1, 2, 3, 4)   # alt
        struct.pack_into("<i", rec, 140, 1)             # prop
        struct.pack_into("<4i", rec, 144, 42, 111, 222, 5)
        struct.pack_into("<i", rec, 188, 3)             # vision
        struct.pack_into("<i", rec, 196, 11)            # touch_damage
        struct.pack_into("<5i", rec, 200, 1, 2, 3, 4, 5)
        sp = mapdata.parse_sprite(bytes(rec))
        self.assertEqual((sp["x"], sp["y"], sp["seq"], sp["frame"], sp["type"], sp["size"]), (300, 200, 12, 3, 1, 150))
        self.assertEqual((sp["rotation"], sp["special"], sp["brain"]), (7, 8, 9))
        self.assertEqual((sp["script"], sp["hit"]), ("S1-Bob", "hit"))
        self.assertEqual(sp["hard"], 1)
        self.assertEqual(sp["alt"], {"left": 1, "top": 2, "right": 3, "bottom": 4})
        self.assertEqual((sp["prop"], sp["warp_map"], sp["warp_x"], sp["warp_y"], sp["parm_seq"]), (1, 42, 111, 222, 5))
        self.assertEqual((sp["vision"], sp["touch_damage"]), (3, 11))
        self.assertEqual(sp["buff"], [1, 2, 3, 4, 5])

    def test_tile_offsets(self):
        rec = struct.pack("<4iBB2x15i", 900, 1, 20, 2, 3, 4, *range(15))
        t = mapdata.parse_tile(rec)
        self.assertEqual((t["num"], t["property"], t["althard"], t["more2"], t["more3"], t["more4"]), (900, 1, 20, 2, 3, 4))
        self.assertEqual(t["buff"], list(range(15)))
        self.assertEqual(len(rec), 80)


class BmpTests(unittest.TestCase):
    def test_colour_key(self):
        white_bg = make_bmp8(3, 2, pixel=0)
        im = to_rgba(white_bg, "white")
        self.assertEqual(im.getpixel((0, 0))[3], 0)
        self.assertEqual(to_rgba(white_bg, "black").getpixel((0, 0))[3], 255)
        self.assertEqual(to_rgba(white_bg, "none").getpixel((0, 0))[3], 255)
        black_bg = make_bmp8(3, 2, pixel=255)
        self.assertEqual(to_rgba(black_bg, "black").getpixel((0, 0))[3], 0)
        self.assertEqual(bmp_size(make_bmp8(5, 7)), (5, 7))


class IniTests(unittest.TestCase):
    def test_tokenize_stops_at_double_space(self):
        self.assertEqual(tokenize("load_sequence a\\b- 5  75"), ["load_sequence", "a\\b-", "5"])
        self.assertEqual(tokenize("SET_SPRITE_INFO 1 2 3   \n"), ["SET_SPRITE_INFO", "1", "2", "3"])
        self.assertEqual(atol("-12abc"), -12)
        self.assertEqual(atol("BLACK"), 0)

    def test_defaults(self):
        self.assertEqual(default_origin(48, 97), (48 - 24 + 8, 97 - 24 - 3))
        self.assertEqual(default_hardbox(48, 97), {"left": -12, "top": -9, "right": 12, "bottom": 9})

    def _model(self, ini, frames):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        for rel, items in frames.items():
            full = os.path.join(d.name, rel)
            os.makedirs(full)
            with open(os.path.join(full, "dir.ff"), "wb") as f:
                f.write(make_ff(items))
        p = os.path.join(d.name, "dink.ini")
        with open(p, "w") as f:
            f.write(ini)
        return SequenceModel.from_ini(p, Graphics(d.name))

    def test_anim_origin_hardbox_and_overrides(self):
        bm = lambda w, h: make_bmp8(w, h)
        ini = "\n".join([
            "load_sequence graphics\\a\\x- 1 100 5 6 -4 -3 4 3",   # anim, explicit origin/hardbox
            "load_sequence graphics\\b\\y- 2 NOTANIM",              # per-frame defaults
            "load_sequence graphics\\c\\z- 3 BLACK",
            "set_sprite_info 1 2 9 8 -1 -2 3 4",
            "set_frame_special 1 1 1",
            "set_frame_delay 1 2 250",
            "set_frame_frame 1 3 2 1",
            "set_frame_frame 1 4 -1 0",
            "",
        ])
        m = self._model(ini, {
            os.path.join("graphics", "a"): [("X-01.BMP", bm(40, 80)), ("X-02.BMP", bm(20, 20))],
            os.path.join("graphics", "b"): [("Y-01.BMP", bm(40, 80)), ("Y-02.BMP", bm(20, 20))],
            os.path.join("graphics", "c"): [("Z-01.BMP", bm(8, 8))],
        })
        s1 = {f["frame"]: f for f in m.seq_json(1)["frames"]}
        self.assertEqual(s1[1]["origin"], {"x": 5, "y": 6})
        self.assertEqual(s1[1]["hardbox"], {"left": -4, "top": -3, "right": 4, "bottom": 3})
        self.assertEqual(s1[1]["delay_ms"], 100)
        self.assertTrue(s1[1]["is_hit_frame"])
        # SET_SPRITE_INFO beats the sequence settings on that frame only
        self.assertEqual(s1[2]["origin"], {"x": 9, "y": 8})
        self.assertEqual(s1[2]["hardbox"], {"left": -1, "top": -2, "right": 3, "bottom": 4})
        self.assertEqual(s1[2]["delay_ms"], 250)
        # alias: frame 3 draws sequence 2 frame 1
        self.assertEqual(s1[3]["alias"]["seq"], 2)
        self.assertEqual((s1[3]["width"], s1[3]["height"]), (40, 80))
        self.assertTrue(s1[4]["loop_to_start"])
        # NOTANIM: every frame gets defaults from its own size
        s2 = {f["frame"]: f for f in m.seq_json(2)["frames"]}
        self.assertEqual(s2[1]["origin"], dict(zip("xy", default_origin(40, 80))))
        self.assertEqual(s2[2]["origin"], dict(zip("xy", default_origin(20, 20))))
        self.assertEqual(m.seq_json(2)["default_delay_ms"], 0)
        c = m.seq_json(3)
        self.assertEqual((c["flags"]["black"], c["transparency"], c["is_anim"]), (True, "black", True))
        # anim without explicit origin: frame 1 decides for all frames
        m2 = self._model("load_sequence graphics\\a\\x- 1 50\n", {
            os.path.join("graphics", "a"): [("X-01.BMP", bm(40, 80)), ("X-02.BMP", bm(20, 20))]})
        f = {x["frame"]: x for x in m2.seq_json(1)["frames"]}
        self.assertEqual(f[2]["origin"], f[1]["origin"])
        self.assertEqual(f[2]["origin"], dict(zip("xy", default_origin(40, 80))))
        self.assertEqual(f[2]["hardbox"], default_hardbox(20, 20))      # hardbox is still per-frame

    def test_set_sprite_info_follows_alias_table(self):
        # engine edits g_picInfo[g_seq[s].frame[f]]: after an alias, that is the OTHER sequence's picture
        ini = "\n".join([
            "load_sequence graphics\\a\\x- 1 100",
            "load_sequence graphics\\b\\y- 2 100",
            "set_frame_frame 1 1 2 1",
            "set_sprite_info 1 1 7 7 -1 -1 1 1",
            "",
        ])
        m = self._model(ini, {
            os.path.join("graphics", "a"): [("X-01.BMP", make_bmp8(10, 10))],
            os.path.join("graphics", "b"): [("Y-01.BMP", make_bmp8(10, 10))]})
        s2 = m.seq_json(2)["frames"][0]
        self.assertEqual(s2["origin"], {"x": 7, "y": 7})

    def test_later_definition_wins(self):
        ini = "load_sequence graphics\\a\\x- 1 100\nload_sequence graphics\\b\\y- 1 100\n"
        m = self._model(ini, {
            os.path.join("graphics", "a"): [("X-01.BMP", make_bmp8(10, 10))],
            os.path.join("graphics", "b"): [("Y-01.BMP", make_bmp8(12, 12)), ("Y-02.BMP", make_bmp8(12, 12))]})
        self.assertEqual(m.seq_json(1)["prefix"], "y-")
        self.assertEqual(m.seq_json(1)["file_frame_count"], 2)
        self.assertEqual(m.seq_json(1)["ini_lines"], [1, 2])


if __name__ == "__main__":
    unittest.main()
