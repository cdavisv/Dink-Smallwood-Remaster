"""Read-only access to the stage-1 IR written by tools/dinkex (and the
stage-2 tables in tools/data). Nothing here writes anything."""

import csv
import glob
import json
import os

import numpy as np
from PIL import Image

W, H = 600, 400            # playfield of one screen, map pixels
GRID_W, GRID_H = 32, 24
TILE = 50
SIDEBAR = 20               # placement x / warp_x include the 20 px side bar

# hardness PNG codes (tools/dinkex/README.md)
WALKABLE, SOLID, LOW, OTHER, SPRITE, WARP = 0, 1, 2, 3, 100, 200


def screen_id(n):
    return "SCR_%03d" % n


def screen_of(col, row):
    return row * GRID_W + col + 1


def col_row(n):
    return (n - 1) % GRID_W, (n - 1) // GRID_W


class IR:
    def __init__(self, ir_dir, data_dir=None, story_dir=None, classes_dir=None):
        self.dir = os.path.abspath(ir_dir)
        self.world = self._json("world.json")
        self.summary = self._json("summary.json")
        self.screens = {}
        for f in sorted(glob.glob(os.path.join(self.dir, "screens", "SCR_*.json"))):
            with open(f, encoding="utf-8") as fh:
                s = json.load(fh)
            self.screens[s["screen"]] = s
        self.used = sorted(self.screens)
        self._seq = None
        self._hard = {}
        self.hard_patches = {}      # screen -> designed-join sides (joins.install)
        here = os.path.dirname(os.path.abspath(__file__))
        repo = os.path.normpath(os.path.join(here, "..", "..", ".."))
        self.data_dir = data_dir or os.path.join(repo, "bin", "dink")
        self.story_dir = story_dir or os.path.join(self.data_dir, "story")
        self.classes_dir = classes_dir or os.path.join(repo, "tools", "data")
        self._tile_classes = None

    def _json(self, name):
        with open(os.path.join(self.dir, name), encoding="utf-8") as fh:
            return json.load(fh)

    @property
    def sequences(self):
        if self._seq is None:
            self._seq = {q["seq"]: q for q in self._json("sequences.json")["sequences"]}
        return self._seq

    def indoor(self, n):
        return bool(self.screens[n]["indoor"])

    def raw_hardness(self, n, vision=0):
        """uint8 (400, 600) code image for screen n at a vision value, as tools/dinkex wrote it."""
        s = self.screens[n]
        if vision == 0:
            rel = s["hardness"]["image"]
        else:
            rel = s["hardness"]["vision_variants"][str(vision)]
        return np.array(Image.open(os.path.join(self.dir, rel)))

    def hardness(self, n, vision=0):
        """uint8 (400, 600) code image for screen n at a vision value, with the designed joins of
        regions.toml applied (joins.apply_patch)."""
        key = (n, vision)
        if key not in self._hard:
            h = self.raw_hardness(n, vision)
            if n in self.hard_patches:
                from .joins import apply_patch
                for side in self.hard_patches[n]:
                    h = apply_patch(h, side)[0]
            self._hard[key] = h
        return self._hard[key]

    def owner(self, n, vision=0):
        s = self.screens[n]
        rel = s["hardness"]["owner_image"] if vision == 0 else \
            s["hardness"]["vision_variants"][str(vision)].replace(".png", "_owner.png")
        return np.array(Image.open(os.path.join(self.dir, rel)))

    def visions(self, n):
        return [0] + sorted(int(v) for v in self.screens[n]["hardness"].get("vision_variants", {}))

    def drop_cache(self):
        self._hard.clear()

    # ---- stage-2 tile classes -------------------------------------------
    @property
    def tile_classes(self):
        if self._tile_classes is None:
            path = os.path.join(self.classes_dir, "tile_classes.csv")
            self._tile_classes = {}
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    for r in csv.DictReader(fh):
                        self._tile_classes[int(r["tile_num"])] = r
        return self._tile_classes

    def scripts_on(self, n):
        """(base, random, load scripts) plus every placement script/talk/hit/die name."""
        s = self.screens[n]
        out = []
        for k in ("base_script", "random_script", "load_script"):
            if s.get(k):
                out.append(s[k])
        for p in s["placements"]:
            for k in ("script",):
                if p.get(k) and len(p[k]) > 1:
                    out.append(p[k])
        return out
