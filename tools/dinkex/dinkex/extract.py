"""Orchestration: read ``bin/dink`` and write the intermediate representation."""

import collections
import os
import time

import numpy as np
from PIL import Image

from . import (PLAY_H, PLAY_W, SCHEMA_VERSION, SCREEN_COUNT, SCREENS_X, SCREENS_Y,
               TILE, TILES_PER_SCREEN, TILES_X, TILES_Y, __version__)
from . import hard as hardmod
from . import mapdata
from .bmp import bmp_size, load_rgb, to_rgba
from .fsutil import CIResolver
from .gfx import Graphics
from .jsonfmt import write_json
from .runtime_hardness import runtime_layers
from .sequences import SequenceModel, image_path

ALL_STEPS = ("screens", "sequences", "sprites", "tiles", "hardness", "world")
WORLD_DOWNSAMPLE = 5            # 19200x9600 -> 3840x1920


def screen_id(n):
    return "SCR_%03d" % n


def placement_id(n, i):
    return "S%03d_P%02d" % (n, i)


def tile_id(n, t):
    return "S%03d_T%02d" % (n, t)


def kind_of(t):
    return {0: "background", 1: "live", 2: "hardness_only"}.get(t, "unknown_%d" % t)


class Extractor:
    def __init__(self, data_dir, out_dir, steps=ALL_STEPS, log=None):
        self.data = os.path.abspath(data_dir)
        self.out = os.path.abspath(out_dir)
        self.steps = set(steps)
        self.log = log or (lambda m: None)
        self.res = CIResolver(self.data)
        self.gfx = Graphics(self.data)
        self.world = mapdata.read_dink_dat(self._need("dink.dat"))
        self.map = mapdata.MapDat(self._need("map.dat"))
        self.hard = hardmod.HardDat.from_file(self._need("hard.dat"))
        self.seqs = SequenceModel.from_ini(self._need("dink.ini"), self.gfx)
        sound = self.res.resolve("sound")
        self.sound = {e.lower(): e for e in os.listdir(sound)} if sound else {}
        self._tileset_sizes = {}
        for n in range(1, 62):
            p = self.res.resolve("tiles/ts%02d.bmp" % n)
            if p:
                with open(p, "rb") as f:
                    self._tileset_sizes[n] = bmp_size(f.read(32))
        self.screens = {}            # n -> mapdata.ScreenRecord (parsed lazily)
        self.summary = {}

    def _need(self, rel):
        p = self.res.resolve(rel)
        if p is None:
            raise FileNotFoundError("%s not found under %s" % (rel, self.data))
        return p

    def _mk(self, *parts):
        d = os.path.join(self.out, *parts)
        os.makedirs(d, exist_ok=True)
        return d

    def screen(self, n):
        s = self.screens.get(n)
        if s is None:
            s = self.map.record(self.world.loc[n])
            self.screens[n] = s
        return s

    # ------------------------------------------------------------------
    def run(self):
        t0 = time.time()
        os.makedirs(self.out, exist_ok=True)
        if "sequences" in self.steps:
            self.write_sequences()
        if "sprites" in self.steps:
            self.write_sprites()
        if "tiles" in self.steps:
            self.write_tiles()
        if "screens" in self.steps or "hardness" in self.steps:
            self.write_screens()
        if "world" in self.steps:
            self.write_world()
        self.write_summary(time.time() - t0)
        return self.summary

    # -- sequences / sprites ---------------------------------------------
    def write_sequences(self):
        self.log("sequences.json ...")
        write_json(os.path.join(self.out, "sequences.json"), self.seqs.to_json(), expand_levels=3)

    def write_sprites(self):
        self.log("sprite PNGs ...")
        n = 0
        for (seq, frame), pic in sorted(self.seqs.pics.items()):
            key = self.seqs.transparency_for(seq, frame)
            im = to_rgba(pic.source.read(), key)
            path = os.path.join(self._mk("sprites", str(seq)), "%02d.png" % frame)
            im.save(path, optimize=False)
            n += 1
        self.summary["sprite_pngs_written"] = n

    def write_tiles(self):
        self.log("tile PNGs ...")
        n = 0
        for ts in sorted(self._tileset_sizes):
            src = self._need("tiles/ts%02d.bmp" % ts)
            with open(src, "rb") as f:
                rgb = load_rgb(f.read())
            Image.fromarray(rgb).save(os.path.join(self._mk("tiles"), "ts%02d.png" % ts))
            n += 1
        self.summary["tileset_pngs_written"] = n

    # -- screens ------------------------------------------------------------
    def tile_json(self, n, t, tl):
        tileset, cell = mapdata.tile_set_and_cell(tl["num"])
        sx, sy, sw, sh = mapdata.tile_source_rect(cell)
        size = self._tileset_sizes.get(tileset)
        in_bounds = bool(size and sx + sw <= size[0] and sy + sh <= size[1])
        hid, hsrc, valid = self.hard.lookup(tl["num"], tl["althard"])
        x0, y0 = hardmod.tile_cell_origin(t)
        d = {
            "id": tile_id(n, t), "index": t, "col": t % TILES_X, "row": t // TILES_X,
            "x": x0, "y": y0,
            "num": tl["num"], "tileset": tileset, "cell": cell,
            "src": {"x": sx, "y": sy, "w": sw, "h": sh},
            "tileset_exists": size is not None, "src_in_bounds": in_bounds,
            "althard": tl["althard"],
            "hardness_tile": hid, "hardness_source": hsrc, "hardness_valid": valid,
            "property": tl["property"], "more2": tl["more2"], "more3": tl["more3"], "more4": tl["more4"],
        }
        if any(tl["buff"]):
            d["buff"] = tl["buff"]
        return d

    def placement_json(self, n, i, sp, rank):
        pic = self.seqs.pic_for(sp["seq"], sp["frame"])
        d = {"id": placement_id(n, i), "index": i, "rank": rank}
        d.update({
            "x": sp["x"], "y": sp["y"], "map_x": sp["x"] - 20, "map_y": sp["y"],
            "seq": sp["seq"], "frame": sp["frame"], "type": sp["type"], "size": sp["size"],
            "active": bool(sp["active"]),
            "rotation": sp["rotation"], "special": sp["special"], "brain": sp["brain"],
            "script": sp["script"].lower(), "hit": sp["hit"].lower(), "die": sp["die"].lower(),
            "talk": sp["talk"].lower(),
            "speed": sp["speed"], "base_walk": sp["base_walk"], "base_idle": sp["base_idle"],
            "base_attack": sp["base_attack"], "base_hit": sp["base_hit"],
            "timer": sp["timer"], "que": sp["que"], "hard": sp["hard"], "alt": sp["alt"],
            "prop": sp["prop"], "warp_map": sp["warp_map"], "warp_x": sp["warp_x"], "warp_y": sp["warp_y"],
            "parm_seq": sp["parm_seq"], "base_die": sp["base_die"], "gold": sp["gold"],
            "hitpoints": sp["hitpoints"], "strength": sp["strength"], "defense": sp["defense"],
            "exp": sp["exp"], "sound": sp["sound"], "vision": sp["vision"], "nohit": sp["nohit"],
            "touch_damage": sp["touch_damage"], "buff": sp["buff"],
        })
        d["kind"] = kind_of(sp["type"])
        d["drawn"] = sp["type"] in (0, 1)
        d["size_percent"] = 100 if sp["size"] == 0 else sp["size"]
        d["has_hardness"] = sp["hard"] == 0
        d["is_warp"] = sp["prop"] != 0
        d["vision_gated"] = sp["vision"] != 0
        d["has_script"] = len(sp["script"]) > 1       # the engine only loads scripts longer than 1 char (D:6137)
        if d["is_warp"]:
            wm = sp["warp_map"]
            d["warp_target_valid"] = 1 <= wm <= SCREEN_COUNT and self.world.loc[wm] > 0
        d["pic"] = None if pic is None else {
            "seq": pic.key[0], "frame": pic.key[1], "image": image_path(*pic.key),
            "width": pic.width, "height": pic.height, "origin": pic.origin, "hardbox": pic.hardbox}
        d["pic_resolved"] = pic is not None
        d["hardness_stamp"] = None
        if d["has_hardness"] and pic is not None:
            r = hardmod.stamp_rect(sp, pic.hardbox)
            d["hardness_stamp"] = None if r is None else {
                "x0": r[0], "y0": r[1], "x1": r[2], "y1": r[3], "kind": "warp" if d["is_warp"] else "solid"}
        return d

    def write_screens(self):
        want_json = "screens" in self.steps
        want_hard = "hardness" in self.steps
        if want_json:
            self._mk("screens")
        if want_hard:
            self._mk("hardness")
        self.log("screens ...")
        agg = collections.Counter()
        scripts = set()
        base_scripts = set()
        placed_per_screen = {}
        prop_vals = collections.Counter()
        kinds = collections.Counter()
        hard_vals = collections.Counter()
        brain_vals = collections.Counter()
        unresolved = collections.Counter()
        invalid_tiles = []
        music_counts = collections.Counter()
        hard_variants = 0
        hard_pngs = 0
        pix = collections.Counter()
        unresolved_with_hard = []
        vision_gated = 0
        vision_screens = set()
        for n in self.world.used_screens():
            scr = self.screen(n)
            col, row = mapdata.screen_col_row(n)
            indoor_raw = self.world.indoor[n]
            music = mapdata.music_info(self.world.music[n], self.sound)
            music_counts[self.world.music[n]] += 1
            base_script = scr.script.lower()
            if base_script:
                base_scripts.add(base_script)
            # engine sprites are 1..99
            sprites = {i: s for i, s in scr.sprites.items()}
            engine_sprites = {i: s for i, s in sprites.items() if 1 <= i <= mapdata.ENGINE_SPRITE_MAX}
            order = hardmod.placement_rank(engine_sprites)
            rank_of = {i: r for r, i in enumerate(order, 1)}
            tiles = [self.tile_json(n, t, tl) for t, tl in enumerate(scr.tiles[:TILES_PER_SCREEN])]
            placements = [self.placement_json(n, i, sprites[i], rank_of.get(i)) for i in sorted(sprites)]

            for p in placements:
                scripts.add(p["script"]) if p["script"] else None
                prop_vals[p["prop"]] += 1
                kinds[p["kind"]] += 1
                hard_vals[p["hard"]] += 1
                brain_vals[p["brain"]] += 1
                if p["vision_gated"]:
                    vision_gated += 1
                    vision_screens.add(n)
                if not p["pic_resolved"]:
                    unresolved[(p["seq"], p["frame"])] += 1
                    if p["has_hardness"]:
                        unresolved_with_hard.append(p["id"])
            placed_per_screen[n] = len(placements)
            for t in tiles:
                if not t["hardness_valid"]:
                    invalid_tiles.append(t["id"])

            # --- collision maps ----------------------------------------------
            hb_of = lambda s: (lambda pic: None if pic is None else pic.hardbox)(self.seqs.pic_for(s["seq"], s["frame"]))
            visions = sorted({s["vision"] for s in engine_sprites.values() if s["vision"] != 0})
            hard_info = {"image": "hardness/%s.png" % screen_id(n),
                         "owner_image": "hardness/%s_owner.png" % screen_id(n),
                         "vision_variants": {}}
            codes, owner, info = hardmod.build_hitmap(self.hard, scr.tiles[:TILES_PER_SCREEN], engine_sprites, hb_of, vision=0)
            hard_info["skipped_tiles"] = [tile_id(n, t) for t in info["skipped_tiles"]]
            hard_info["stamps"] = info["stamps"]
            hard_info["pixel_counts"] = {str(int(k)): int(v) for k, v in zip(*np.unique(codes, return_counts=True))}
            for k, v in hard_info["pixel_counts"].items():
                pix[k] += v
            if want_hard:
                self._save_codes(codes, "hardness/%s.png" % screen_id(n))
                self._save_owner(owner, "hardness/%s_owner.png" % screen_id(n))
                hard_pngs += 2
                # Additive source packet: retain tile pixels hidden beneath stamps.
                write_json(os.path.join(self.out, "hardness", "%s_layers.json" % screen_id(n)),
                           runtime_layers(self.hard, scr.tiles[:TILES_PER_SCREEN], engine_sprites, hb_of, editor_hard_flags=scr.editor_hard_flags),
                           expand_levels=1)
                for v in visions:
                    c2, o2, _ = hardmod.build_hitmap(self.hard, scr.tiles[:TILES_PER_SCREEN], engine_sprites, hb_of, vision=v)
                    self._save_codes(c2, "hardness/%s_v%d.png" % (screen_id(n), v))
                    self._save_owner(o2, "hardness/%s_v%d_owner.png" % (screen_id(n), v))
                    hard_info["vision_variants"][str(v)] = "hardness/%s_v%d.png" % (screen_id(n), v)
                    write_json(os.path.join(self.out, "hardness", "%s_v%d_layers.json" % (screen_id(n), v)),
                               runtime_layers(self.hard, scr.tiles[:TILES_PER_SCREEN], engine_sprites, hb_of, vision=v, editor_hard_flags=scr.editor_hard_flags),
                               expand_levels=1)
                    hard_variants += 1
                    hard_pngs += 2
            else:
                for v in visions:
                    hard_info["vision_variants"][str(v)] = None

            if want_json:
                doc = {
                    "schema": "dinkex.screen/%d" % SCHEMA_VERSION,
                    "id": screen_id(n), "screen": n,
                    "col": col, "row": row,
                    "map_record": self.world.loc[n],
                    "editor_hard_flags": scr.editor_hard_flags,
                    "name": scr.name,
                    "indoor": indoor_raw != 0, "indoor_raw": indoor_raw,
                    "music": music,
                    "base_script": base_script,
                    "random_script": scr.random.lower(), "load_script": scr.load.lower(),
                    "neighbours": self._neighbours(n),
                    "counts": {
                        "placements": len(placements),
                        "warps": sum(1 for p in placements if p["is_warp"]),
                        "with_hardness": sum(1 for p in placements if p["has_hardness"]),
                        "vision_gated": sum(1 for p in placements if p["vision_gated"]),
                        "with_script": sum(1 for p in placements if p["script"]),
                    },
                    "hardness": hard_info,
                    "tiles": tiles,
                    "placements": placements,
                }
                if any(scr.v):
                    doc["v"] = scr.v
                if scr.s:
                    doc["s"] = scr.s
                if scr.buffer_nonzero:
                    doc["buffer_nonzero"] = True
                write_json(os.path.join(self.out, "screens", "%s.json" % screen_id(n)), doc, expand_levels=1)
            agg["screens"] += 1

        used = self.world.used_screens()
        self.summary.update({
            "screens_used": len(used),
            "screens_indoor": sum(1 for n in used if self.world.indoor[n] != 0),
            "screens_outdoor": sum(1 for n in used if self.world.indoor[n] == 0),
            "map_dat_records": self.map.count,
            "active_placements": sum(placed_per_screen.values()),
            "placements_by_kind": dict(kinds),
            "placements_by_prop": {str(k): v for k, v in sorted(prop_vals.items())},
            "placements_by_hard_value": {str(k): v for k, v in sorted(hard_vals.items())},
            "vision_gated_placements": vision_gated,
            "screens_with_vision_gated_placements": len(vision_screens),
            "warp_placements": sum(v for k, v in prop_vals.items() if k != 0),
            "distinct_placement_scripts": len(scripts),
            "distinct_screen_base_scripts": len(base_scripts),
            "max_placements_on_one_screen": max(placed_per_screen.values()) if placed_per_screen else 0,
            "screen_with_max_placements": max(placed_per_screen, key=placed_per_screen.get) if placed_per_screen else None,
            "placements_by_brain": {str(k): v for k, v in sorted(brain_vals.items())},
            "music_values": {str(k): v for k, v in sorted(music_counts.items())},
            "unresolved_placement_pics": [{"seq": s, "frame": f, "count": c} for (s, f), c in sorted(unresolved.items())],
            "unresolved_placement_pics_with_hardness": unresolved_with_hard,
            "tiles_with_invalid_hardness_id": len(invalid_tiles),
            "tiles_with_invalid_hardness_id_ids": invalid_tiles,
            "hardness_pngs_written": hard_pngs,
            "hardness_vision_variants": hard_variants,
            "hardness_pixel_totals_default_vision": dict(sorted(pix.items(), key=lambda kv: int(kv[0]))),
        })

    def _neighbours(self, n):
        out = {}
        for name, dn in (("left", -1), ("right", 1), ("up", -SCREENS_X), ("down", SCREENS_X)):
            m = n + dn
            ok = 1 <= m <= SCREEN_COUNT and not (dn in (-1, 1) and (m - 1) // SCREENS_X != (n - 1) // SCREENS_X)
            out[name] = m if ok and self.world.loc[m] > 0 else None
        return out

    def _save_codes(self, codes, rel):
        # A palette image whose pixel *values* are the codes (viewers show colours).
        im = Image.frombytes("P", (PLAY_W, PLAY_H), np.ascontiguousarray(codes).tobytes())
        pal = [0] * 768
        colours = {
            hardmod.CODE_WALKABLE: (0, 0, 0),
            hardmod.CODE_SOLID: (230, 60, 60),
            hardmod.CODE_LOW: (60, 140, 230),
            hardmod.CODE_OTHER: (230, 230, 60),
            hardmod.CODE_SPRITE: (150, 90, 200),
            hardmod.CODE_WARP: (60, 230, 90),
        }
        for k, (r, g, b) in colours.items():
            pal[k * 3: k * 3 + 3] = [r, g, b]
        im.putpalette(pal)
        im.save(os.path.join(self.out, rel))

    def _save_owner(self, owner, rel):
        Image.fromarray(owner).save(os.path.join(self.out, rel))

    # -- world ----------------------------------------------------------------
    def write_world(self):
        self.log("world_tiles.png ...")
        ds = WORLD_DOWNSAMPLE
        sw, sh = PLAY_W // ds, PLAY_H // ds
        canvas = Image.new("RGB", (SCREENS_X * sw, SCREENS_Y * sh), (0, 0, 0))
        tilesets = {}
        missing = 0
        for n in self.world.used_screens():
            scr = self.screen(n)
            buf = np.zeros((PLAY_H, PLAY_W, 3), dtype=np.uint8)
            for t, tl in enumerate(scr.tiles[:TILES_PER_SCREEN]):
                ts, cell = mapdata.tile_set_and_cell(tl["num"])
                size = self._tileset_sizes.get(ts)
                sx, sy, w, h = mapdata.tile_source_rect(cell)
                if size is None or sx + w > size[0] or sy + h > size[1]:
                    missing += 1
                    continue
                img = tilesets.get(ts)
                if img is None:
                    with open(self._need("tiles/ts%02d.bmp" % ts), "rb") as f:
                        img = tilesets[ts] = load_rgb(f.read())
                x0, y0 = hardmod.tile_cell_origin(t)
                buf[y0:y0 + TILE, x0:x0 + TILE] = img[sy:sy + h, sx:sx + w]
            small = Image.fromarray(buf).resize((sw, sh), Image.BOX)
            col, row = mapdata.screen_col_row(n)
            canvas.paste(small, (col * sw, row * sh))
        canvas.save(os.path.join(self.out, "world_tiles.png"))
        self.summary["world_tiles_png"] = {"width": canvas.width, "height": canvas.height,
                                           "downsample": ds, "tiles_outside_tileset_bounds": missing}
        grid = []
        for row in range(SCREENS_Y):
            grid.append([row * SCREENS_X + c + 1 if self.world.loc[row * SCREENS_X + c + 1] > 0 else 0
                         for c in range(SCREENS_X)])
        write_json(os.path.join(self.out, "world.json"), {
            "schema": "dinkex.world/%d" % SCHEMA_VERSION,
            "name": self.world.name,
            "screens_x": SCREENS_X, "screens_y": SCREENS_Y,
            "screen_px": [PLAY_W, PLAY_H],
            "grid": grid,
            "indoor": [[1 if g and self.world.indoor[g] else 0 for g in r] for r in grid],
            "music": [[self.world.music[g] if g else 0 for g in r] for r in grid],
        }, expand_levels=1)

    # -- summary ----------------------------------------------------------------
    def write_summary(self, seconds):
        cen = self.gfx.census()
        files_used = {(p.source.rel, p.source.entry) for p in self.seqs.pics.values()}
        s = self.summary
        s["bmp_census"] = cen
        s["bmp_frames_total"] = cen["total_bmps"]
        s["bmp_frames_referenced_by_sequences"] = len(files_used)
        s["bmp_frames_unreferenced"] = cen["total_bmps"] - len(files_used)
        s["sequences_defined"] = len(self.seqs.defs)
        s["sequences_redefined"] = sorted(self.seqs.superseded)
        s["sequence_frames_with_files"] = len(self.seqs.pics)
        s["sequence_warnings"] = self.seqs.warnings
        s["hard_dat"] = {
            "file_size": self.hard.file_size, "short_by_bytes": self.hard.short_by,
            "index_entries_in_file": self.hard.index_entries_in_file,
            "index_entries_out_of_range": int(((self.hard.index[:self.hard.index_entries_in_file] < 0) |
                                               (self.hard.index[:self.hard.index_entries_in_file] >= hardmod.BLOCK_COUNT)).sum()),
            "used_flags_nonzero": bool(self.hard.used_flags_nonzero),
        }
        s["tilesets"] = len(self._tileset_sizes)
        s["extractor_version"] = __version__
        s["seconds"] = round(seconds, 1)
        write_json(os.path.join(self.out, "summary.json"), s, expand_levels=1)
