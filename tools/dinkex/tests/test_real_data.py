"""Facts measured independently on the shipped game data, plus end-to-end output checks."""
import collections
import json
import os
import tempfile
import unittest

from PIL import Image

from dinkex import hard as hardmod
from dinkex.extract import Extractor
from tests.helpers import DATA

HAVE_DATA = os.path.isfile(os.path.join(DATA, "dink.dat"))


@unittest.skipUnless(HAVE_DATA, "bin/dink not found")
class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = cls.tmp.name
        cls.ex = Extractor(DATA, cls.out)
        cls.summary = cls.ex.run()
        cls.screens = {}
        for n in cls.ex.world.used_screens():
            with open(os.path.join(cls.out, "screens", "SCR_%03d.json" % n)) as f:
                cls.screens[n] = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # --- the numbers measured independently ---------------------------------
    def test_screen_counts(self):
        self.assertEqual(self.summary["screens_used"], 644)
        self.assertEqual(self.summary["screens_indoor"], 74)
        self.assertEqual(self.summary["map_dat_records"], 644)

    def test_placements(self):
        pls = [p for s in self.screens.values() for p in s["placements"]]
        self.assertEqual(len(pls), 5846)
        self.assertEqual(sum(1 for p in pls if p["prop"] == 1), 93)
        self.assertEqual(sum(1 for p in pls if p["is_warp"]), 93)
        self.assertEqual({p["prop"] for p in pls}, {0, 1})
        self.assertEqual(len({p["script"] for p in pls if p["script"]}), 191)
        self.assertEqual(max(len(s["placements"]) for s in self.screens.values()), 90)
        self.assertEqual(self.summary["max_placements_on_one_screen"], 90)

    def test_base_scripts(self):
        self.assertEqual(len({s["base_script"] for s in self.screens.values() if s["base_script"]}), 62)

    def test_bmp_frames(self):
        c = self.summary["bmp_census"]
        self.assertEqual(c["total_bmps"], 3569)
        self.assertEqual(c["archives"], 142)
        self.assertEqual(c["loose_bmps"], 122)
        self.assertEqual(c["ff_bmp_entries"], 3447)
        # three archives also hold a bogus "dir.ff" entry; 3,572 raw entries minus those
        self.assertEqual(c["ff_nonbmp_entries"], 3)

    # --- structure ---------------------------------------------------------------
    def test_ids_unique_and_traceable(self):
        ids = [p["id"] for s in self.screens.values() for p in s["placements"]]
        self.assertEqual(len(ids), len(set(ids)))
        s1 = self.screens[1]
        self.assertEqual(s1["id"], "SCR_001")
        self.assertTrue(all(p["id"] == "S001_P%02d" % p["index"] for p in s1["placements"]))
        self.assertEqual(len(s1["tiles"]), 96)
        self.assertEqual(s1["tiles"][0]["id"], "S001_T00")

    def test_inverted_hard_flag(self):
        for s in self.screens.values():
            for p in s["placements"]:
                self.assertEqual(p["has_hardness"], p["hard"] == 0)
        self.assertEqual(self.summary["placements_by_hard_value"], {"0": 2722, "1": 3122, "200": 2})

    def test_placement_kinds(self):
        self.assertEqual(self.summary["placements_by_kind"], {"background": 1658, "live": 4119, "hardness_only": 69})

    def test_tile_fields_consistent(self):
        for s in self.screens.values():
            for t in s["tiles"]:
                self.assertEqual(t["tileset"], t["num"] // 128 + 1)
                self.assertEqual(t["cell"], t["num"] % 128)
                self.assertEqual(t["src"]["x"], (t["cell"] % 12) * 50)
                self.assertEqual(t["src"]["y"], (t["cell"] // 12) * 50)
                self.assertTrue(t["src_in_bounds"])

    def test_hard_dat_facts(self):
        hd = self.summary["hard_dat"]
        self.assertEqual(hd["file_size"], 2107392)
        self.assertEqual(hd["short_by_bytes"], 11008)
        self.assertEqual(hd["index_entries_in_file"], 5248)
        self.assertEqual(hd["index_entries_out_of_range"], 106)
        self.assertFalse(hd["used_flags_nonzero"])

    def test_hardness_png(self):
        im = Image.open(os.path.join(self.out, "hardness", "SCR_001.png"))
        self.assertEqual(im.size, (600, 400))
        self.assertEqual(im.mode, "P")
        vals = {v for _, v in im.getcolors()}
        self.assertTrue(vals <= {0, 1, 2, 3, 100, 200})
        self.assertIn(hardmod.CODE_WARP, vals)         # the door warp on screen 1
        for n, s in self.screens.items():
            self.assertTrue(os.path.isfile(os.path.join(self.out, s["hardness"]["image"])))
            self.assertTrue(os.path.isfile(os.path.join(self.out, s["hardness"]["owner_image"])))

    def test_every_hard_sprite_resolves(self):
        self.assertEqual(self.summary["unresolved_placement_pics_with_hardness"], [])
        # only the four seq 0 / frame 0 placements have no picture at all
        self.assertEqual(self.summary["unresolved_placement_pics"], [{"seq": 0, "frame": 0, "count": 4}])

    def test_sequences(self):
        with open(os.path.join(self.out, "sequences.json")) as f:
            doc = json.load(f)
        by = {s["seq"]: s for s in doc["sequences"]}
        self.assertEqual(len(by), 408)
        self.assertEqual(sorted(int(k) for k in doc["redefined"]), [102, 104, 106, 108])
        self.assertEqual(by[10]["keyword"], "BLACK")
        self.assertEqual(by[10]["transparency"], "black")
        self.assertEqual(by[181]["flags"]["leftalign"], True)
        self.assertEqual(by[181]["transparency"], "none")
        f11 = [f for f in by[181]["frames"] if f["frame"] == 11][0]
        self.assertEqual(f11["transparency"], "white")      # engine hack (D:1743)
        # seq 12 idle: frames 5 and 6 are SET_FRAME_FRAME aliases of frames 3 and 2 (ini lines 21-24)
        fr = {f["frame"]: f for f in by[12]["frames"]}
        self.assertEqual(fr[5]["alias"]["frame"], 3)
        self.assertEqual(fr[5]["delay_ms"], 250)
        self.assertEqual(by[12]["file_frame_count"], 4)
        # every image referenced exists
        for s in by.values():
            for f in s["frames"]:
                if f["image"]:
                    self.assertTrue(os.path.isfile(os.path.join(self.out, f["image"])), f["image"])

    def test_sprite_png_keying(self):
        # a white-keyed sprite has transparent corners; seq 181 (no key) is fully opaque
        im = Image.open(os.path.join(self.out, "sprites", "12", "01.png"))
        self.assertEqual(im.mode, "RGBA")
        self.assertEqual(im.getpixel((0, 0))[3], 0)
        im = Image.open(os.path.join(self.out, "sprites", "181", "01.png"))
        self.assertEqual(im.getextrema()[3], (255, 255))
        self.assertEqual(len(self.ex.seqs.pics), self.summary["sprite_pngs_written"])

    def test_world_outputs(self):
        with Image.open(os.path.join(self.out, "world_tiles.png")) as im:
            self.assertEqual(im.size, (3840, 1920))
        self.assertEqual(len(os.listdir(os.path.join(self.out, "tiles"))), 41)
        self.assertEqual(self.summary["world_tiles_png"]["tiles_outside_tileset_bounds"], 0)

    def test_all_hardbox_stamps_inside_playfield(self):
        for s in self.screens.values():
            for p in s["placements"]:
                st = p["hardness_stamp"]
                if st:
                    self.assertTrue(0 <= st["x0"] < st["x1"] <= 600 and 0 <= st["y0"] < st["y1"] <= 400)


if __name__ == "__main__":
    unittest.main()
