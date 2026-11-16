#!/usr/bin/env python3
"""Gather everything the greybox importer needs from the data repo into ImportData/.

    python3 Scripts/export_import_bundle.py [--data ../Dink-Smallwood-Remaster] [--out ImportData]

The Unreal importer (DinkImport, Scripts/import_greybox.sh) reads ONLY this bundle, never the
data repo. The bundle is deterministic (no timestamps): exporting twice from the same data gives
byte-identical files, so the importer's hashes (and therefore its "no drift" check) are stable.

Inputs (all regenerable, git-ignored `out/` folders of the data repo's tools; see its AGENTS.md):
  tools/dinkex/out/screens/*.json, hardness/*.png, tiles/*.png, sprites/<seq>/<NN>.png
  tools/analyse/out/world_layout.json, warps.json, interiors.json, encounters.json,
                    vision_variants.json, regions.csv, connectivity.json (incl. `designed_joins`: owner
                    decisions such as the cobbler's booth doorway, applied to tiles and hardness here)
  tools/data/sprite_classes.csv, tile_classes.csv
  tools/dinkc/out/script_kinds.csv, ast/*.json

Outputs (ImportData/, git-ignored):
  bundle.json       manifest: source commit + input hashes, settings, counts per region, start
  screens.json      one record per used screen (corners in metres, music, indoor, encounter, vision)
  placements.json   one record per active placement (layout position, card geometry, classes)
  warps.json        one record per warp trigger (93 sprite warps + script-warp sources)
  collision.json    per screen: merged hardness rectangles in map pixels, per collision class
  samples.json      per screen: walkable / blocked sample points for the parity tests; screen links
  ground/SCR_nnn.png   tile layer at the original 600x400 (the importer stretches it to 1024x512)
  sprites/<seq>_<NN>.png  every placed picture, RGBA, resampled to power-of-two (nearest)

Stdlib + numpy + Pillow (both on the dev machine).
"""
from __future__ import annotations

from remaster_paths import default_data_repo
from sync_gameplay_data import release_picture_keys, saved_picture_keys

import argparse
import csv
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

EXPORTER_VERSION = "dink-bundle/1"
SPRITE_MAX = 1024
SAMPLES_PER_SCREEN = 8

# Hardness codes (tools/dinkex README): 0 walkable, 1 solid, 2 low, 3 other, 100 sprite hardbox,
# 200 warp trigger hardbox. Collision classes written to collision.json:
#   solid  = codes 1, 3        -> profile DinkHardSolid (blocks everything)
#   low    = code 2            -> profile DinkHardLow (blocks pawns, projectiles cross)
#   sprite = code 100          -> DinkHardSolid (sprite hardboxes; kept apart so they stay traceable)
#   warp   = code 200          -> DinkHardSolid (the original blocks and triggers on warp hardboxes)
#   fill_water = walkable (code 0) pixels of components whose terrain is water   -> DinkHardLow
#   fill_solid = walkable pixels of components whose terrain is forest canopy, void or chasm -> DinkHardSolid
# The fills exist because the original draws tile hardness as outlines only (open sea, canopy
# interiors and the black void around rooms are hardness 0); tools/analyse shows that no such
# component is ever reached, so filling them changes nothing the player could do in the original
# except closing its 10 "edge leaks".
# Component classes follow tools/analyse/analyse/connectivity.py (tile_group): the class of a
# component is the terrain GROUP with the most pixels under it.
TERRAIN_GROUP = {"water": "water", "forest_canopy": "canopy", "void": "void", "chasm": "void",
                 "lava": "blocked", "rock_mass": "blocked", "cave_wall": "blocked", "structure_facade": "blocked"}
GROUPS = ["land", "water", "canopy", "void", "blocked"]
FILL_GROUP = {"water": "fill_water", "canopy": "fill_solid", "void": "fill_solid"}


def tile_group(row) -> str:
    if row is None:
        return "land"
    t = row["terrain"]
    if t in TERRAIN_GROUP:
        return TERRAIN_GROUP[t]
    if t == "cliff_face" or row["walkable_hint"] == "no":
        return "blocked"
    return "land"

# Card scale: things whose footprint is part of the layout-stretched ground (buildings, walls,
# trees, rocks, furniture...) use the local layout scale so card, ground painting and hardness
# blocker agree. Characters and small loose things use the base scale (true human size), so a
# villager is not 4x taller in a settlement.
BASE_SCALE_CATEGORIES = {"npc", "enemy", "animal", "pickup", "effect", "ui"}


def sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def sha1_json(obj) -> str:
    return sha1_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode())


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj, indent=None) -> None:
    text = json.dumps(obj, sort_keys=False, indent=indent, separators=(",", ":") if indent is None else None)
    path.write_text(text + "\n", encoding="utf-8")


def write_png_if_changed(path: Path, img: Image.Image) -> None:
    """Pillow PNG output is deterministic for the same pixels; skip rewriting identical files."""
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False, compress_level=6)
    data = buf.getvalue()
    if path.exists() and path.stat().st_size == len(data) and path.read_bytes() == data:
        return
    path.write_bytes(data)


# ---------------------------------------------------------------------------------------------
# Photoreal pass: per-screen terrain layer masks for the master ground material (M_Env_Terrain).
# The tile classes (tools/data/tile_classes.csv) choose up to three layers of the catalogue
# SourceAssets/Art/PhotorealPass/Environment/terrain_layers.json; transition tiles are split per
# pixel by colour distance to the mean colours of their two classes. The mask is 96x64 (8 px per
# tile), RGB = weights of layers A, B, C. Screens dominated by unmapped classes (wood floors,
# building facades, void) keep the original painted ground.
TERRAIN_MASK_W, TERRAIN_MASK_H = 96, 64
COVER_DIV = 2   # the grass cover grid is the mask at half resolution (48 x 32 per screen, sampled bilinearly; 24 x 16 before)
# The master material blends four layers: the mask's RGB carry the first three weights, the fourth takes what
# they leave (1 - R - G - B). A screen with more layers folds the smallest into a layer of the same family
# (the look is close; the audit lists it as merged) or, failing that, into the nearest other layer (listed as dropped).
TERRAIN_MAX_LAYERS = 4
TERRAIN_FAMILIES = (("MeadowTurf", "RockyGrass", "WildGrass"), ("Snow", "SnowTrampled"), ("EarthPath", "TransitionDirt"),
                    ("DrySand", "WetSand"), ("CliffRock", "CaveRock"), ("CobbleStreet", "DungeonFlagstone"))
TERRAIN_NEAREST = {
    "CliffRock": ("RockyGrass", "ScorchedSoil", "EarthPath"), "CaveRock": ("CaveFloor", "ScorchedSoil"), "CaveFloor": ("CaveRock",),
    "EarthPath": ("DrySand", "ForestFloor", "ScorchedSoil"), "TransitionDirt": ("DrySand", "ForestFloor"),
    "ForestFloor": ("EarthPath", "MeadowTurf"), "DrySand": ("ShingleBeach", "EarthPath"), "WetSand": ("PondMud", "ShingleBeach", "EarthPath"),
    "ShingleBeach": ("DrySand", "WetSand"), "MeadowTurf": ("ForestFloor",), "RockyGrass": ("ForestFloor",),
    "DungeonMasonry": ("CobbleStreet", "DungeonFlagstone"), "CobbleStreet": ("DungeonMasonry", "EarthPath"),
    "Snow": ("CliffRock",), "SnowTrampled": ("CliffRock",), "ScorchedSoil": ("CaveRock", "CliffRock"), "LavaCrust": ("ScorchedSoil", "CaveRock"),
}


def fold_terrain_layers(weights: dict, limit: int = TERRAIN_MAX_LAYERS, keep: dict | None = None):
    """Fold the smallest layers of `weights` (name -> weight array) into others until at most `limit` are left.
    -> (weights, merged {layer: the same-family layer that draws it}, dropped {layer: the other layer that draws it}).
    Pure bookkeeping: a screen with `limit` layers or fewer comes back untouched. `keep` (layer -> priority, natural
    outlines): layers of a lower priority fold first, whatever their size (a neighbour's sliver before the screen's
    own layers, a layer that never reaches the rim before one that does)."""
    weights = dict(weights)
    merged, dropped = {}, {}
    size = (lambda k: (float(weights[k].sum()), k)) if keep is None else (lambda k: (keep.get(k, 0), float(weights[k].sum()), k))
    while len(weights) > limit:
        victim = target = None
        # with priorities only the lowest group is a candidate: a neighbour's sliver goes before ANY of the screen's own
        # layers, even one that has a relative to merge into
        low = min(keep.get(k, 0) for k in weights) if keep is not None else None
        candidates = [k for k in weights if keep is None or keep.get(k, 0) == low]
        for name in sorted(candidates, key=size):     # the smallest layer that has a relative on the screen goes first
            family = next((f for f in TERRAIN_FAMILIES if name in f), ())
            relatives = [k for k in family if k in weights and k != name]
            if relatives:
                victim, target = name, max(relatives, key=size)
                merged[victim] = target
                break
        if victim is None:
            victim = min(candidates, key=size)
            target = next((k for k in TERRAIN_NEAREST.get(victim, ()) if k in weights), None) or max((k for k in weights if k != victim), key=size)
            dropped[victim] = target
        weights[target] = weights[target] + weights.pop(victim)
        for book in (merged, dropped):                 # a layer folded earlier follows its target
            for k, v in list(book.items()):
                if v == victim: book[k] = target
    return weights, merged, dropped


def load_terrain_catalogue(project: Path):
    path = project / "SourceAssets/Art/PhotorealPass/Environment/terrain_layers.json"
    if not path.exists():
        return None
    cat = json.loads(path.read_text())
    manifest = project / "SourceAssets/Art/PhotorealPass/Terrain/manifest.json"
    sets = {s["name"]: s for s in json.loads(manifest.read_text())["sets"]} if manifest.exists() else {}
    layers = {}
    for name, row in cat["layers"].items():
        if row["source"] == "terrain":
            if row["set"] not in sets:
                continue
            tile_m = float(sets[row["set"]]["tile_size_m"])
        else:
            tile_m = float(row["tile_m"])
        tile_m *= float(row.get("tile_scale", 1.0))
        layers[name] = {"name": name, "tile_cm": round(tile_m * 100.0, 3), "normal_strength": float(row.get("normal_strength", 1.0)),
                        "backlight": float(row.get("backlight", 0.0)), "emissive": float(row.get("emissive", 0.0))}
        # only written when set, so the rows of other layers stay as they were
        if row.get("structured"):
            layers[name]["structured"] = 1.0
        if row.get("structured") or row.get("drift") is False:
            layers[name]["drift"] = 0.0
    cat["resolved_layers"] = layers
    return cat


def terrain_class_means(tile_classes: dict, tileset) -> dict:
    """Mean RGB of every terrain class over its non-transition tiles (tileset art)."""
    sums, counts = {}, {}
    for row in tile_classes.values():
        if row.get("is_transition") == "1":
            continue
        ts = tileset(int(row["tileset"]))
        if ts is None:
            continue
        cell = int(row["cell"])
        x, y = (cell % 12) * 50, (cell // 12) * 50
        if x + 50 > ts.width or y + 50 > ts.height:
            continue
        mean = np.asarray(ts.crop((x, y, x + 50, y + 50)), dtype=np.float64).reshape(-1, 3).mean(axis=0)
        sums[row["terrain"]] = sums.get(row["terrain"], 0) + mean
        counts[row["terrain"]] = counts.get(row["terrain"], 0) + 1
    return {k: sums[k] / counts[k] for k in sums}


def signed_shore_distance(water: np.ndarray, px_cm: float) -> np.ndarray:
    """Signed distance (cm) to the waterline on a small boolean grid: positive on land, negative in water.
    A screen without water returns +inf-like (far), one without land -far."""
    far = 1.0e4
    inside = np.argwhere(water)
    outside = np.argwhere(~water)
    out = np.full(water.shape, far)
    if len(inside) == 0:
        return out
    if len(outside) == 0:
        return -out
    d = np.sqrt(((inside[:, None, :] - outside[None, :, :]) ** 2).sum(axis=2)) * px_cm
    out[tuple(outside.T)] = d.min(axis=0) - 0.5 * px_cm
    out[tuple(inside.T)] = -(d.min(axis=1) - 0.5 * px_cm)
    return out


SHORE_PX_CM = 600.0 / TERRAIN_MASK_W * 4.38     # one mask texel (6.25 map px of about 4.4 cm)
SHORE_RANGE_CM = 400.0                           # alpha 0.5 +- 0.5 over +-2 m from the waterline
SHORE_CAP_CELLS = 11                             # beyond 2 m (7.3 texels) plus bilinear slack the alpha is clamped anyway
SHORE_MARGIN_CELLS = 12                          # texels of the neighbours' water round a screen's own (> SHORE_CAP_CELLS)


def water_cells(fill_water=None, shore_water=None) -> np.ndarray:
    """The 64 x 96 texel grid of a screen's drawn water (as terrain_mask's shore): the collision's water fill, or
    where it has none the drawn water's shape (natural_water_shape)."""
    if (fill_water is None or not fill_water.any()) and shore_water is not None:
        fill_water = shore_water
    if fill_water is None or not fill_water.any():
        return np.zeros((TERRAIN_MASK_H, TERRAIN_MASK_W), bool)
    fw = np.asarray(Image.fromarray(fill_water.astype(np.uint8) * 255).resize((TERRAIN_MASK_W, TERRAIN_MASK_H), Image.BOX))
    return fw > 127


def capped_shore_distance(water: np.ndarray, px_cm: float, cap: int = SHORE_CAP_CELLS) -> np.ndarray:
    """signed_shore_distance (cm, positive on land, negative in water, between cell centres) for every cell whose
    waterline lies within `cap` cells; farther cells get +-1e4. Exact where it is not capped, and linear in the grid
    size, so it runs on a screen with its neighbours round it."""
    far = 1.0e4
    h, w = water.shape
    to_water = np.full(water.shape, np.inf)
    to_land = np.full(water.shape, np.inf)
    wp = np.pad(water, cap, constant_values=False)
    lp = np.pad(~water, cap, constant_values=False)
    for dy in range(-cap, cap + 1):
        for dx in range(-cap, cap + 1):
            r = math.hypot(dy, dx)
            if r > cap or (dy == 0 and dx == 0):
                continue
            sw = wp[cap + dy:cap + dy + h, cap + dx:cap + dx + w]
            sl = lp[cap + dy:cap + dy + h, cap + dx:cap + dx + w]
            np.minimum(to_water, np.where(sw, r, np.inf), out=to_water)
            np.minimum(to_land, np.where(sl, r, np.inf), out=to_land)
    out = np.where(water, -(to_land * px_cm - 0.5 * px_cm), to_water * px_cm - 0.5 * px_cm)
    return np.where(np.isinf(out), np.where(water, -far, far), out)


# the eight screens round screen n on the 1997 map: (column step, row step, corner pairs (own, theirs) that a
# neighbour placed against it in the world layout shares with it)
SHORE_NEIGHBOURS = (
    (-1, -1, (("nw", "se"),)), (0, -1, (("nw", "sw"), ("ne", "se"))), (1, -1, (("ne", "sw"),)),
    (-1, 0, (("nw", "ne"), ("sw", "se"))), (1, 0, (("ne", "nw"), ("se", "sw"))),
    (-1, 1, (("sw", "ne"),)), (0, 1, (("sw", "nw"), ("se", "ne"))), (1, 1, (("se", "nw"),)))


def world_neighbours(n: int, corners: dict) -> dict:
    """(column step, row step) -> screen number of the up to eight screens round n on the 1997 map that also lie
    against it in the world layout (they share the corners of the edge or corner between them; tools/analyse moves
    some screens, and indoor screens sit anywhere). `corners`: screen -> {nw, ne, sw, se} in metres."""
    col, row = (n - 1) % MAP_COLUMNS, (n - 1) // MAP_COLUMNS
    out = {}
    own = corners.get(n)
    if own is None:
        return out
    for dc, dr, pairs in SHORE_NEIGHBOURS:
        if not (0 <= col + dc < MAP_COLUMNS) or row + dr < 0:
            continue
        m = n + dc + dr * MAP_COLUMNS
        other = corners.get(m)
        if other is not None and all(math.dist(own[a], other[b]) < 0.01 for a, b in pairs):
            out[(dc, dr)] = m
    return out


def shore_alpha(n: int, cells: dict, neighbours: dict) -> np.ndarray:
    """The terrain mask's alpha of screen n (64 x 96, 0..1: 0.5 at the waterline, 1 two metres or more on land, 0 two
    metres or more into the water) with the waterline found across screen borders: the shore distance is measured on
    the screen's water grid with SHORE_MARGIN_CELLS of the world-adjacent neighbours' grids round it (`cells`: screen
    -> water_cells; `neighbours`: world_neighbours of n; a side without a neighbour repeats the screen's own edge,
    which is the same as measuring inside the screen only). The texels hold the distance at points spread from edge
    to edge (texel 0 on the west edge, texel 95 on the east edge), so the two screens of a border hold the same
    value on it and the water's depth and colour run on across it."""
    m = SHORE_MARGIN_CELLS
    h, w = TERRAIN_MASK_H, TERRAIN_MASK_W
    own = cells[n]
    window = np.pad(own, m, mode="edge")
    for (dc, dr), other in neighbours.items():
        grid = cells.get(other)
        if grid is None:
            continue
        ys = slice(0, m) if dr < 0 else slice(m, m + h) if dr == 0 else slice(m + h, m + h + m)
        xs = slice(0, m) if dc < 0 else slice(m, m + w) if dc == 0 else slice(m + w, m + w + m)
        gy = slice(h - m, h) if dr < 0 else slice(0, h) if dr == 0 else slice(0, m)
        gx = slice(w - m, w) if dc < 0 else slice(0, w) if dc == 0 else slice(0, m)
        window[ys, xs] = grid[gy, gx]
    if not window.any():
        return np.ones((h, w))
    sd = capped_shore_distance(window, SHORE_PX_CM)
    # sample points: x = i / (w - 1) of the screen width, in window cell coordinates (cell centres at k + 0.5)
    cx = np.arange(w) * (w / (w - 1.0)) - 0.5 + m
    cy = np.arange(h) * (h / (h - 1.0)) - 0.5 + m
    x0 = np.clip(np.floor(cx).astype(int), 0, w + 2 * m - 2); fx = cx - x0
    y0 = np.clip(np.floor(cy).astype(int), 0, h + 2 * m - 2); fy = cy - y0
    top = sd[y0][:, x0] * (1 - fx) + sd[y0][:, x0 + 1] * fx
    bottom = sd[y0 + 1][:, x0] * (1 - fx) + sd[y0 + 1][:, x0 + 1] * fx
    d = top * (1 - fy)[:, None] + bottom * fy[:, None]
    return np.clip(0.5 + d / SHORE_RANGE_CM, 0.0, 1.0)


def terrain_mask(scr: dict, ground: "Image.Image", tile_classes: dict, cat: dict, means: dict, fill_water=None, indoor=False, facts=None, shore_water=None,
                 raw_out=None):
    """-> (layers [dict], RGBA mask Image, grass cover base64 or None), or (None, None, None) when the screen
    keeps its painted ground. Alpha is the signed distance to the waterline: 128 at the shore, 255 at 2 m or
    more on land (also the value without water), 0 at 2 m or more into the water.
    `facts` (a dict) is filled with what the art audit needs to know about the screen's ground: the tile classes
    on it, the layer each maps to, the layers the mask carries and the layers folded into others (merged, dropped).
    `raw_out` (a dict) receives the 1997 tile weights before folding (`weights`: layer -> 64 x 96 cells), whether the
    screen keeps its painted ground (`painted`) and its water cells (`water`), for naturalise_ground_masks."""
    layers = cat["resolved_layers"]
    class_map = dict(cat["classes"])
    if indoor:
        class_map.update(cat.get("classes_indoor", {}))
    class_layer = {c: l for c, l in class_map.items() if l in layers}
    secondary = {c: v for c, v in cat.get("class_secondary", {}).items() if v[0] in layers}
    px = TERRAIN_MASK_W // 12
    small = np.asarray(ground.resize((TERRAIN_MASK_W, TERRAIN_MASK_H), Image.BOX), dtype=np.float64)
    weights = {}
    unmapped = 0

    def add(layer, r, c, w):
        a = weights.setdefault(layer, np.zeros((TERRAIN_MASK_H, TERRAIN_MASK_W)))
        a[r * px:(r + 1) * px, c * px:(c + 1) * px] += w

    # '@surroundings' classes (the picture of a building's upper storeys, drawn over open ground behind the assembled
    # houses): each tile takes the layer of the nearest tile of ordinary ground on the screen
    surround = {c for c, l in class_map.items() if l == "@surroundings"}
    ordinary = [(t["row"], t["col"], class_layer[(tile_classes.get(t["num"]) or {}).get("terrain", "")]) for t in scr["tiles"]
                if (tile_classes.get(t["num"]) or {}).get("terrain", "") in class_layer
                and (tile_classes.get(t["num"]) or {}).get("terrain") not in ("water", "void", "chasm")]
    fallback = cat.get("surroundings_fallback")
    surrounded = {}
    for t in scr["tiles"]:
        row = tile_classes.get(t["num"])
        terrain = row["terrain"] if row else ""
        r, c = t["row"], t["col"]
        if terrain in surround:
            near = min(ordinary, key=lambda o: ((o[0] - r) ** 2 + (o[1] - c) ** 2, o[2]))[2] if ordinary else fallback
            if near in layers:
                add(near, r, c, 1.0)
                surrounded[near] = surrounded.get(near, 0) + 1
                continue
        if terrain not in class_layer:
            unmapped += 1
            continue
        parts = [p for p in (row.get("blend_classes") or "").split("|") if p in class_layer and p in means]
        if row.get("is_transition") == "1" and len(parts) == 2 and class_layer[parts[0]] != class_layer[parts[1]]:
            block = small[r * px:(r + 1) * px, c * px:(c + 1) * px]
            d0 = np.linalg.norm(block - means[parts[0]], axis=2)
            d1 = np.linalg.norm(block - means[parts[1]], axis=2)
            w1 = np.clip(0.5 + (d0 - d1) / (np.linalg.norm(means[parts[0]] - means[parts[1]]) + 1e-6), 0.0, 1.0)
            add(class_layer[parts[0]], r, c, 1.0 - w1)
            add(class_layer[parts[1]], r, c, w1)
            continue
        if terrain in secondary:
            add(class_layer[terrain], r, c, 1.0 - secondary[terrain][1])
            add(secondary[terrain][0], r, c, secondary[terrain][1])
        else:
            add(class_layer[terrain], r, c, 1.0)
    painted = not weights or unmapped > 0.10 * len(scr["tiles"])
    if raw_out is not None:
        raw_out.update(weights={k: v.copy() for k, v in weights.items()}, painted=bool(painted), water=None)
    tiles_of = {k: round(float(v.sum()) / (px * px), 2) for k, v in weights.items()}
    weights, merged, dropped = fold_terrain_layers(weights)
    names = [] if painted else sorted(weights, key=lambda k: (-weights[k].sum(), k))
    if facts is not None:
        classes = {}
        for t in scr["tiles"]:
            row = tile_classes.get(t["num"])
            terrain = (row["terrain"] if row else "") or "unclassified"
            classes[terrain] = classes.get(terrain, 0) + 1
        facts.update({
            "indoor": bool(indoor), "classes": dict(sorted(classes.items())),
            "layer_of": {c: class_layer[c] if c in class_layer else "@surroundings" for c in sorted(classes) if c in class_layer or c in surround},
            "surroundings": dict(sorted(surrounded.items())),      # tiles of '@surroundings' classes per layer they took
            "layers": list(names), "painted_ground": bool(painted), "unmapped_tiles": int(unmapped),
            # layers the mask does not carry (more than TERRAIN_MAX_LAYERS on the screen): tiles' worth of weight and
            # the layer that draws them instead; `merged` into a layer of the same family, `dropped` into another one
            "merged": {k: {"tiles": tiles_of[k], "drawn_as": merged[k]} for k in sorted(merged)} if not painted else {},
            "dropped": {k: {"tiles": tiles_of[k], "drawn_as": dropped[k]} for k in sorted(dropped)} if not painted else {},
            "water_surface": bool(fill_water is not None and fill_water.any())})
    if painted:
        return None, None, None
    stack = np.zeros((TERRAIN_MASK_H, TERRAIN_MASK_W, max(3, len(names))))
    for i, name in enumerate(names):
        stack[:, :, i] = weights[name]
    total = stack.sum(axis=2, keepdims=True)
    first = np.zeros(stack.shape[2]); first[0] = 1.0
    stack = np.where(total > 1e-6, stack / np.maximum(total, 1e-6), first)
    # 3x3 box blur with edge clamp: one-texel soft edges, then the material's height blend shapes them
    pad = np.pad(stack, ((1, 1), (1, 1), (0, 0)), mode="edge")
    stack = sum(pad[dy:dy + TERRAIN_MASK_H, dx:dx + TERRAIN_MASK_W] for dy in range(3) for dx in range(3)) / 9.0
    shore = np.full((TERRAIN_MASK_H, TERRAIN_MASK_W), 1.0)
    water_small = np.zeros((TERRAIN_MASK_H, TERRAIN_MASK_W), bool)
    if (fill_water is None or not fill_water.any()) and shore_water is not None:
        fill_water = shore_water      # no water fill in the collision: the drawn water's shape (natural_water_shape) gives the shore
    if fill_water is not None and fill_water.any():
        fw = np.asarray(Image.fromarray(fill_water.astype(np.uint8) * 255).resize((TERRAIN_MASK_W, TERRAIN_MASK_H), Image.BOX))
        water_small = fw > 127
        px_cm = 600.0 / TERRAIN_MASK_W * 4.38  # about 4.4 cm per map pixel
        shore = np.clip(0.5 + signed_shore_distance(water_small, px_cm) / 400.0, 0.0, 1.0)
    if raw_out is not None:
        raw_out["water"] = water_small
    rgba = np.dstack([np.clip(stack[:, :, :3], 0.0, 1.0), shore])   # a fourth layer is what R + G + B leave
    img = Image.fromarray((rgba * 255.0 + 0.5).astype(np.uint8), "RGBA")
    cover = None
    grass = cat.get("grass_layer", "MeadowTurf")
    if grass in names:
        g = stack[:, :, names.index(grass)] * (~water_small)
        g = g.reshape(TERRAIN_MASK_H // COVER_DIV, COVER_DIV, TERRAIN_MASK_W // COVER_DIV, COVER_DIV).mean(axis=(1, 3))
        import base64
        cover = base64.b64encode((np.clip(g, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()).decode("ascii")
    return [layers[n] for n in names], img, cover


def naturalise_ground_masks(out: Path, cat: dict, ground_raw: dict, ground_masks: dict, corners: dict, ground_classes: dict,
                            layer_cover: dict) -> dict:
    """Replace the tile-shaped layer weights of every outdoor screen's terrain mask by natural outlines computed in
    world space with the screens round it (Scripts/ground_layer_fields.py: rounded, noise-bent within half a tile of
    the 1997 outline, feathered, continuous across screen borders), then write the masks. Indoor floors keep their
    tile weights. Every mask is written edge-aligned (texel 0 on the west edge, texel 95 on the east edge), as
    M_Env_Terrain's clamped lookup shows on the border (ground_layer_fields.py). The alpha (shore distance) is left as terrain_mask made it.
    `ground_raw`: screen -> terrain_mask's raw_out plus `indoor`; `ground_masks`: screen -> (mask Image, layer rows,
    screens.json record), updated in place with the new layers and hash; `corners`: screen -> world corners;
    `ground_classes` (facts) and `layer_cover` are updated for the screens whose layers change. -> counts."""
    from ground_layer_fields import STRUCTURED_BEND, region_sources, connected_weights, connectivity_faults, edge_aligned_own, smooth_screen_layers
    layers = cat["resolved_layers"]
    grass = cat.get("grass_layer", "MeadowTurf")
    bend = {k: STRUCTURED_BEND for k, row in layers.items() if row.get("structured")}
    # patch size varies over a field for the layers the 1997 map scatters in small patches (not paths, ledges or
    # the ground round them)
    vary = {k: 1.0 for k in ("RockyGrass", "WildGrass", "TransitionDirt") if k in layers}
    outdoor = {m for m, r in ground_raw.items() if not r.get("indoor") and r.get("weights")}
    stats = {"natural": 0, "indoor": 0, "bleed_folded": 0, "own_folded": 0, "split_before": 0, "merged_before": 0,
             "split": 0, "merged": 0, "final_split": 0, "final_merged": 0, "final_split_screens": [], "final_merged_screens": []}
    px = TERRAIN_MASK_W // 12
    for n, (img, _, rec) in sorted(ground_masks.items()):
        rgba = np.asarray(img).astype(np.float64) / 255.0
        raw = ground_raw[n]
        if raw.get("indoor") or n not in outdoor:
            rgb = edge_aligned_own({c: rgba[:, :, c] for c in range(3)})
            rgba = np.dstack([rgb[0], rgb[1], rgb[2], rgba[:, :, 3]])
            stats["indoor"] += 1
        else:
            neighbours = {k: m for k, m in world_neighbours(n, corners).items() if m in outdoor}
            smooth = smooth_screen_layers(n, {m: ground_raw[m]["weights"] for m in [n] + list(neighbours.values())}, neighbours, bend, vary=vary,
                                          report=stats, fixed={cat.get("classes", {}).get("water", "WetSand")})
            own = raw["weights"]
            rim = {k: float(v[0].sum() + v[-1].sum() + v[:, 0].sum() + v[:, -1].sum()) for k, v in smooth.items()}
            # the screen's own layers keep their channels (the smallest own layer folds only when the own layers alone
            # are more than four); a neighbour's sliver folds first, one that reaches the rim last of them
            # (priority 3: a layer of the screen's tile classes; 2: one that only comes from a transition tile's colour split)
            f0 = ground_classes.get(str(n)) or {}
            tile_layers = {f0.get("layer_of", {}).get(c) for c, k in (f0.get("classes") or {}).items() if k} | set(f0.get("surroundings") or {})
            keep = {k: 3 if k in tile_layers else 2 if k in own and float(own[k].sum()) > 0.0 else (1 if rim[k] > 0.5 else 0) for k in smooth}
            weights, merged, dropped = fold_terrain_layers(smooth, keep=keep)
            # the written winners keep every 1997 region of the screen in one piece and apart (after blur, feather, fold)
            weights = connected_weights(weights, own, report=stats.setdefault("final_fix", {}))
            names = sorted(weights, key=lambda k: (-weights[k].sum(), k))
            # the written mask against the 1997 tiles: no 1997 layer region split in two, no two joined (per screen)
            own_names = sorted(own)
            own_frac = np.stack([own[k] for k in own_names]); own_frac = own_frac / np.maximum(own_frac.sum(axis=0, keepdims=True), 1e-6)
            res_names = sorted(weights)
            res_win = np.array(res_names)[np.argmax(np.stack([weights[k] for k in res_names]), axis=0)]
            own_src = region_sources(own_frac, np.argmax(own_frac, axis=0))
            for k in set(own_names) & set(res_names):
                sp, mg = connectivity_faults(own_src[own_names.index(k)], res_win == k)
                stats["final_split"] += sp; stats["final_merged"] += mg
                if sp: stats["final_split_screens"].append((n, k))
                if mg: stats["final_merged_screens"].append((n, k))
            stack = np.stack([weights[k] for k in names], axis=2)
            stack = stack / np.maximum(stack.sum(axis=2, keepdims=True), 1e-6)
            rgb = np.zeros((TERRAIN_MASK_H, TERRAIN_MASK_W, 3))
            rgb[:, :, :min(3, len(names))] = stack[:, :, :3]
            rgba = np.dstack([rgb, rgba[:, :, 3]])
            rows = [layers[k] for k in names]
            ground_masks[n] = (img, rows, rec)
            rec["ground_layers"] = rows
            tiles_of = lambda k: round(float((own[k] if k in own else smooth[k]).sum()) / (px * px), 2)
            facts = ground_classes.get(str(n))
            if facts is not None:
                facts["layers"] = list(names)
                # a layer the screen's own tiles do not have (it only reaches in from a neighbour's outline) is not
                # counted as merged or dropped; it is listed apart
                facts["merged"] = {k: {"tiles": tiles_of(k), "drawn_as": merged[k]} for k in sorted(merged) if k in own}
                facts["dropped"] = {k: {"tiles": tiles_of(k), "drawn_as": dropped[k]} for k in sorted(dropped) if k in own}
                folded = dict(merged, **dropped)
                bleed = {k: {"tiles": tiles_of(k), "drawn_as": folded[k]} for k in sorted(folded) if k not in own}
                if bleed:
                    facts["neighbour_layers_folded"] = bleed
                else:
                    facts.pop("neighbour_layers_folded", None)
                facts["outline"] = "natural"
            stats["bleed_folded"] += sum(1 for k in list(dropped) + list(merged) if k not in own)
            stats["own_folded"] += sum(1 for k in list(dropped) + list(merged) if k in own)
            if grass in names:
                water = raw.get("water")
                g = weights[grass] * (~water if water is not None else 1.0)
                g = g.reshape(TERRAIN_MASK_H // COVER_DIV, COVER_DIV, TERRAIN_MASK_W // COVER_DIV, COVER_DIV).mean(axis=(1, 3))
                import base64
                layer_cover[str(n)] = base64.b64encode((np.clip(g, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8).tobytes()).decode("ascii")
            else:
                layer_cover.pop(str(n), None)
            stats["natural"] += 1
        mask = Image.fromarray((np.clip(rgba, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), "RGBA")
        write_png_if_changed(out / "ground_mask" / f"{rec['id']}.png", mask)
        rec["ground_mask_hash"] = sha1_bytes(mask.tobytes() + json.dumps(rec["ground_layers"], sort_keys=True).encode())
    return stats


FOREST_CLEAR_PX = 40      # about 2.8 m in the wilderness layout: the reach of a large pine's lower boughs
FOREST_CAMERA_PX = 110     # about 7.5 m: the camera boom (4 m) plus a crown


def forest_points(screen: int, tiles: list, tile_classes: dict, walk_ok: np.ndarray):
    """Where trees stand on a screen's forest-canopy tiles (the 1997 tiles paint a closed pine forest there):
    one [map_x, map_y, edge] per tile, edge 1 when a neighbouring tile of the screen is not canopy. The trees have
    no collision and their boughs reach metres from the trunk, so a point is only kept when
      - nobody can walk within FOREST_CLEAR_PX of it (no bough over ground a player stands on), and
      - no walkable ground lies up to FOREST_CAMERA_PX north of it within FOREST_CLEAR_PX to either side: the play
        camera hangs about 4 m south of the hero, and a tree there would stand between the two.
    A transition tile gets its tree on the forest side or none. Positions are jittered by a stable hash of screen
    and tile."""
    canopy = {(t["row"], t["col"]) for t in tiles if (tile_classes.get(t["num"]) or {}).get("terrain") == "forest_canopy"}
    points = []
    for row, col in sorted(canopy):
        edge = int(any((row + dr, col + dc) not in canopy for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                       if 0 <= row + dr < 8 and 0 <= col + dc < 12))
        for attempt in range(8):
            h = hashlib.md5(f"{screen}:{row}:{col}:{attempt}".encode()).digest()
            x = col * 50 + 25 + int((int.from_bytes(h[0:2], "little") / 65535.0 - 0.5) * 38)
            y = row * 50 + 25 + int((int.from_bytes(h[2:4], "little") / 65535.0 - 0.5) * 38)
            c = FOREST_CLEAR_PX
            if not walk_ok[max(0, y - c):min(400, y + c + 1), max(0, x - c):min(600, x + c + 1)].any() \
                    and not walk_ok[max(0, y - FOREST_CAMERA_PX):y + 1, max(0, x - c):min(600, x + c + 1)].any():
                points.append([x, y, edge])
                break
    return points


RELIEF_CLASSES = ("cliff_face", "rock_mass", "cave_wall")
RELIEF_MIN_CLEAR_PX = 10      # about 45 cm: a smaller stone is not worth standing up
RELIEF_MAX_CLEAR_PX = 40


def relief_points(screen: int, tiles: list, tile_classes: dict, walk_ok: np.ndarray, warp: np.ndarray, entries=(), indoor=False):
    """Where rock may stand on a screen's cliff-face, rock-mass and cave-wall tiles without anybody ever meeting
    it: one [map_x, map_y, clear_px, tier, class index] per tile, clear_px = the radius round the point in which
    nobody can stand (RELIEF_MIN_CLEAR_PX..RELIEF_MAX_CLEAR_PX; tiles with less get no point).
    tier 1: no walkable pixel at all within clear_px (the 1997 hardness blocks the whole disc).
    tier 2 (outdoor screens only): the only walkable pixels within clear_px lie in a pocket: a walkable component
    of this screen that touches no screen edge, holds no warp pixel, no placement and no point of `entries` (map
    pixels: centroids of the components the route analysis reaches), so a walking player cannot enter it and
    nothing was put there for him.
    The rock is visual only (no collision); the runtime shows tier 1 by default (dink.Relief)."""
    labels, _ = label_components(walk_ok)
    open_labels = set(labels[0, :].tolist()) | set(labels[-1, :].tolist()) | set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    open_labels |= set(labels[warp].tolist())
    for ex, ey in entries:
        if 0 <= int(ey) < 400 and 0 <= int(ex) < 600:
            open_labels.add(int(labels[int(ey), int(ex)]))
    open_labels.discard(0)
    reachable = np.isin(labels, sorted(open_labels)) if open_labels else np.zeros_like(walk_ok)
    points = []
    for t in sorted(tiles, key=lambda t: (t["row"], t["col"])):
        terrain = (tile_classes.get(t["num"]) or {}).get("terrain")
        if terrain not in RELIEF_CLASSES:
            continue
        h = hashlib.md5(f"relief:{screen}:{t['row']}:{t['col']}".encode()).digest()
        x = t["col"] * 50 + 25 + int((h[0] / 255.0 - 0.5) * 16)
        y = t["row"] * 50 + 25 + int((h[1] / 255.0 - 0.5) * 16)
        for tier, mask in ((1, walk_ok),) if indoor else ((1, walk_ok), (2, reachable)):
            clear = 0
            for r in range(RELIEF_MAX_CLEAR_PX, RELIEF_MIN_CLEAR_PX - 1, -2):
                y0, y1, x0, x1 = max(0, y - r), min(400, y + r + 1), max(0, x - r), min(600, x + r + 1)
                yy, xx = np.ogrid[y0:y1, x0:x1]
                if not (mask[y0:y1, x0:x1] & ((yy - y) ** 2 + (xx - x) ** 2 <= r * r)).any():
                    clear = r
                    break
            if clear:
                points.append([x, y, clear, tier, RELIEF_CLASSES.index(terrain)])
                break
    return points


def natural_water_shape(tiles: list, tile_classes: dict, screen: int) -> np.ndarray:
    """A 400 x 600 mask of where water is drawn on a screen whose water tiles have no water fill in the collision
    (ponds and fords a player can stand in or that hardness outlines close): the tile squares rounded off and
    their outline bent by low-frequency noise, so the surface ends on a shoreline and not on tile edges. Within
    40 px of the screen's rim the noise fades out and the tile outline holds, so water meets the next screen's.
    Visual only: it feeds the terrain mask's shore distance and the grass cover, never the collision."""
    from PIL import ImageFilter
    tile_water = np.zeros((400, 600), np.uint8)
    for t in tiles:
        if (tile_classes.get(t["num"]) or {}).get("terrain") == "water":
            tile_water[t["row"] * 50:t["row"] * 50 + 50, t["col"] * 50:t["col"] * 50 + 50] = 255
    if not tile_water.any():
        return tile_water.astype(bool)
    soft = np.asarray(Image.fromarray(tile_water).filter(ImageFilter.GaussianBlur(17))) / 255.0
    core = np.asarray(Image.fromarray(tile_water).filter(ImageFilter.MinFilter(25))) > 0     # 12 px inside the tiles: a river is never cut
    rng = random.Random(screen * 7919 + 17)
    coarse = np.array([[rng.random() for _ in range(9)] for _ in range(7)])
    noise = np.asarray(Image.fromarray((coarse * 255).astype(np.uint8)).resize((600, 400), Image.BICUBIC)) / 255.0
    ys, xs = np.mgrid[0:400, 0:600]
    rim = np.clip(np.minimum(np.minimum(xs, 599 - xs), np.minimum(ys, 399 - ys)) / 40.0, 0.0, 1.0)
    return (soft + (noise - 0.5) * 0.8 * rim > 0.5) | core


SEA_LAYERS = ("DrySand", "ShingleBeach")
MAP_COLUMNS = 32          # screen n sits at column (n - 1) % 32, row (n - 1) // 32 of the 1997 map


def water_is_sea(kind: str, layers) -> bool:
    """The importer's own rule for the colour of a screen's water (DinkGreyboxAssets.cpp, the shore water instance):
    a screen of kind "sea", or one whose mask carries dry sand or shingle, has the sea's blue-green body; anything
    else is silty pond water. WetSand is every water bed, pond or sea, so it does not count."""
    return kind == "sea" or bool(set(layers or []) & set(SEA_LAYERS))


def map_neighbours(n: int) -> list:
    """Screen numbers west, east, north and south of screen n on the 1997 map, without wrapping across a row end
    (screen 385 is the west end of its row: 384 is the east end of the row above, not its neighbour)."""
    col = (n - 1) % MAP_COLUMNS
    return ([n - 1] if col > 0 else []) + ([n + 1] if col < MAP_COLUMNS - 1 else []) + [n - MAP_COLUMNS, n + MAP_COLUMNS]


SEA_OPEN_WATER_TILES = 90  # of a screen's 96 tiles: a screen that is (nearly) all water is open sea, whatever its tiles


def water_meets(a_rects, b_rects, side: str) -> bool:
    """Whether the water fills of two screens meet across their shared edge: `side` "E" (b is east of a) or "S"
    (b is south of a); rects are [x0, y0, x1, y1) map pixels. More than 5 px of shared water edge counts."""
    if side == "E":
        a = [(r[1], r[3]) for r in a_rects if r[2] >= 600]; b = [(r[1], r[3]) for r in b_rects if r[0] <= 0]
    else:
        a = [(r[0], r[2]) for r in a_rects if r[3] >= 400]; b = [(r[0], r[2]) for r in b_rects if r[1] <= 0]
    return any(min(p[1], q[1]) - max(p[0], q[0]) > 5 for p in a for q in b)


def water_links(water: dict) -> dict:
    """screen -> the neighbouring water screens its water joins (`water` as in water_sea_weights): their fills meet
    across the shared edge (`water_meets`), or one of the two is a runtime sheet. Never across a row end."""
    links = {n: set() for n in water}
    for n, w in water.items():
        for m in map_neighbours(n):
            o = water.get(m)
            if o is None or m in links[n]:
                continue
            if w["sheet"] or o["sheet"]:
                joined = True
            elif m == n + 1:
                joined = water_meets(w["fill"], o["fill"], "E")
            elif m == n - 1:
                joined = water_meets(o["fill"], w["fill"], "E")
            elif m == n + MAP_COLUMNS:
                joined = water_meets(w["fill"], o["fill"], "S")
            else:
                joined = water_meets(o["fill"], w["fill"], "S")
            if joined:
                links[n].add(m)
                links[m].add(n)
    return links


def water_sea_weights(water: dict) -> dict:
    """How much of the sea's colour each screen's water takes, 0 (silty pond water) to 1 (the sea's blue-green).
    `water`: screen number -> {"kind", "layers" (the mask's), "tiles" (water tiles of 96), "fill" (fill_water rects),
    "sheet" (True when the runtime draws the water: `water_tiles`)}.

    Rivers in the 1997 map run into the sea as one body of water, and the importer used to colour each screen on its
    own (`water_is_sea`), so open sea with only wet sand (the south coast, the water round Koka Isle) was pond-olive
    and straight seams ran along screen edges. Now: open water (SEA_OPEN_WATER_TILES) and the importer's sea screens
    are the sea; water one screen away from them is sea too, two screens away half and half, further away pond. A
    screen whose water joins two or more sea screens is sea (a strip of coast between two sea screens, the corner of
    an estuary). Between two joined screens the colour never steps by more than half. Screens join when their fills
    meet across the shared edge (`water_meets`); a sheet joins any neighbour with water.
    Neighbours never wrap across a row end (`map_neighbours`)."""
    links = water_links(water)
    dist = {n: 0 for n in sorted(water) if water_is_sea(water[n]["kind"], water[n]["layers"]) or water[n]["tiles"] >= SEA_OPEN_WATER_TILES}
    queue = sorted(dist)
    while queue:
        n = queue.pop(0)
        for m in sorted(links[n]):
            if m not in dist:
                dist[m] = dist[n] + 1
                queue.append(m)
    base = {n: 1.0 if dist.get(n, 99) <= 1 else 0.5 if dist.get(n) == 2 else 0.0 for n in water}
    weight = {n: 1.0 if base[n] < 1.0 and sum(base[m] == 1.0 for m in links[n]) >= 2 else base[n] for n in water}
    changed = True
    while changed:                      # no step bigger than half between joined screens: raise the lower side
        changed = False
        for n in sorted(weight):
            top = max([weight[m] for m in links[n]] + [0.0]) - 0.5
            if top > weight[n]:
                weight[n] = top
                changed = True
    return weight


def mark_sea_water(ground_classes: dict, kinds: dict, fills: dict) -> dict:
    """`water_sea` (0..1, `water_sea_weights`) on every screen whose tiles hold water; returns screen -> weight.
    `kinds`: screen -> kind; `fills`: screen -> fill_water rects. The importer colours a water fill with it and the
    runtime colours a water sheet (`water_tiles`) with it."""
    water = {}
    for number, row in ground_classes.items():
        if row.get("classes", {}).get("water"):
            n = int(number)
            water[n] = {"kind": kinds.get(n, ""), "layers": row.get("layers") or [], "tiles": row["classes"]["water"],
                        "fill": fills.get(n) or [], "sheet": bool(row.get("water_tiles"))}
    weights = water_sea_weights(water)
    patches = water_sea_patches(weights, water_links(water))
    for n, weight in weights.items():
        ground_classes[str(n)]["water_sea"] = weight
        ground_classes[str(n)]["water_sea_patch"] = patches[n]
    return weights


def water_sea_patches(weights: dict, links: dict) -> dict:
    """screen -> its sea weight at nine points [NW, N, NE, W, centre, E, SW, S, SE] (corners, edge middles, centre;
    rows north to south). M_Env_WaterShore blends between them over the screen, so the colour runs on across a
    border instead of stepping at it: the middle of an edge to a joined screen (`links`) holds the mean of the two
    weights, a corner the mean of the joined screens round it; toward a screen it does not join, its own weight.
    Two joined screens therefore hold the same values all along their shared edge."""
    def corner(cc: int, rr: int) -> dict:
        # the up to four screens round map corner (column cc, row rr), grouped by how their water joins
        round_it = [r * MAP_COLUMNS + c + 1 for r in (rr - 1, rr) for c in (cc - 1, cc)
                    if 0 <= c < MAP_COLUMNS and r >= 0 and (r * MAP_COLUMNS + c + 1) in weights]
        group = {s: {s} for s in round_it}
        for a in round_it:
            for b in round_it:
                if b in links.get(a, ()) and group[a] is not group[b]:
                    merged = group[a] | group[b]
                    for s in merged:
                        group[s] = merged
        return {s: sum(weights[t] for t in g) / len(g) for s, g in group.items()}

    patches = {}
    for n in sorted(weights):
        col, row = (n - 1) % MAP_COLUMNS, (n - 1) // MAP_COLUMNS
        own = weights[n]
        edge = lambda m: (own + weights[m]) / 2.0 if m in links.get(n, ()) else own
        west = edge(n - 1) if col > 0 else own
        east = edge(n + 1) if col < MAP_COLUMNS - 1 else own
        north, south = edge(n - MAP_COLUMNS), edge(n + MAP_COLUMNS)
        nw, ne = corner(col, row)[n], corner(col + 1, row)[n]
        sw, se = corner(col, row + 1)[n], corner(col + 1, row + 1)[n]
        patches[n] = [round(v, 3) for v in (nw, north, ne, west, own, east, sw, south, se)]
    return patches


def water_tile_rects(tiles: list, tile_classes: dict):
    """Map-pixel rectangles [x0, y0, x1, y1] of a screen's water tiles, row runs merged."""
    water = sorted((t["row"], t["col"]) for t in tiles if (tile_classes.get(t["num"]) or {}).get("terrain") == "water")
    rects = []
    for row, col in water:
        if rects and rects[-1][1] == row * 50 and rects[-1][2] == col * 50:
            rects[-1][2] = col * 50 + 50
        else:
            rects.append([col * 50, row * 50, col * 50 + 50, row * 50 + 50])
    return rects


def next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def bilinear(c, x, y):
    """World metres of map pixel (x, y) on a screen with corners c (nw/ne/sw/se). Same as
    tools/analyse: u = x/600, v = y/400, P = (1-u)(1-v)nw + u(1-v)ne + (1-u)v sw + uv se."""
    u, v = x / 600.0, y / 400.0
    nw, ne, sw, se = c["nw"], c["ne"], c["sw"], c["se"]
    px = (1 - u) * (1 - v) * nw[0] + u * (1 - v) * ne[0] + (1 - u) * v * sw[0] + u * v * se[0]
    py = (1 - u) * (1 - v) * nw[1] + u * (1 - v) * ne[1] + (1 - u) * v * sw[1] + u * v * se[1]
    return [round(px, 4), round(py, 4)]


# ---------------------------------------------------------------------------------------------
# Hardness: rectangles and components


def mask_to_rects(mask: np.ndarray):
    """Greedy merge of a boolean mask into axis-aligned rectangles [x0, y0, x1, y1) (map pixels):
    horizontal runs per row, then identical runs on consecutive rows are merged vertically."""
    h, w = mask.shape
    rects = []
    active = {}  # (x0, x1) -> y0
    padded = np.zeros((h, w + 2), dtype=np.int8)
    padded[:, 1:-1] = mask
    d = np.diff(padded, axis=1)
    for y in range(h):
        starts = np.flatnonzero(d[y] == 1)
        ends = np.flatnonzero(d[y] == -1)
        runs = set(zip(starts.tolist(), ends.tolist()))
        for key in list(active):
            if key not in runs:
                rects.append([key[0], active.pop(key), key[1], y])
        for key in runs:
            if key not in active:
                active[key] = y
    for key, y0 in active.items():
        rects.append([key[0], y0, key[1], h])
    rects.sort(key=lambda r: (r[1], r[0]))
    return rects


def label_components(mask: np.ndarray):
    """4-connected labelling of a boolean mask via row runs + union-find. Returns int32 labels
    (0 = background, 1..n) and n."""
    h, w = mask.shape
    padded = np.zeros((h, w + 2), dtype=np.int8)
    padded[:, 1:-1] = mask
    d = np.diff(padded, axis=1)
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    rows = []
    prev = []
    for y in range(h):
        starts = np.flatnonzero(d[y] == 1).tolist()
        ends = np.flatnonzero(d[y] == -1).tolist()
        cur = []
        j = 0
        for s, e in zip(starts, ends):
            rid = len(parent)
            parent.append(rid)
            while j < len(prev) and prev[j][1] <= s:
                j += 1
            k = j
            while k < len(prev) and prev[k][0] < e:
                ra, rb = find(rid), find(prev[k][2])
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
                k += 1
            cur.append((s, e, rid))
        rows.append(cur)
        prev = cur
    labels = np.zeros((h, w), dtype=np.int32)
    remap = {}
    for y, cur in enumerate(rows):
        for s, e, rid in cur:
            root = find(rid)
            lab = remap.setdefault(root, len(remap) + 1)
            labels[y, s:e] = lab
    return labels, len(remap)


# Designed joins (tools/analyse regions.toml [[join]], resolved in connectivity.json `designed_joins`): owner
# decisions that change the 1997 map for the remaster, applied here exactly as tools/analyse/analyse/joins.py applies
# them to its own copy, so components, fills and collision agree with the analysis. Per side: the named void tiles
# take the named floor tile (number, tileset cell and source rectangle of that tile elsewhere on the screen); the
# `open` rectangle becomes hardness 0 (the passage); free pixels of the named tiles within JAMB_PX of it become
# hardness 1 (the jambs that keep the passage apart from the void, which is still filled solid).
JOIN_JAMB_PX = 2


def join_tiles(scr: dict, side: dict) -> None:
    by_num = {}
    for t in scr["tiles"]:
        by_num.setdefault(t["num"], t)
    for jt in side["tiles"]:
        i = jt["row"] * 12 + jt["col"]
        old = scr["tiles"][i]
        if old["num"] != jt["from"]:
            raise SystemExit(f"EXPORT FAILED: designed join on {scr['id']}: tile ({jt['col']}, {jt['row']}) is {old['num']}, "
                             f"connectivity.json says {jt['from']} (stale tools/analyse output?)")
        new = dict(by_num[jt["to"]])
        for k in ("id", "index", "col", "row", "x", "y"):
            new[k] = old[k]
        scr["tiles"][i] = new


def join_hardness(hard: np.ndarray, side: dict) -> np.ndarray:
    x0, y0, x1, y1 = side["open"]
    out = hard.copy()
    opened = np.zeros(hard.shape, bool)
    opened[y0:y1, x0:x1] = True
    tiles = np.zeros(hard.shape, bool)
    for jt in side["tiles"]:
        tiles[jt["row"] * 50:(jt["row"] + 1) * 50, jt["col"] * 50:(jt["col"] + 1) * 50] = True
    ring = np.zeros(hard.shape, bool)
    ring[max(0, y0 - JOIN_JAMB_PX):min(400, y1 + JOIN_JAMB_PX), max(0, x0 - JOIN_JAMB_PX):min(600, x1 + JOIN_JAMB_PX)] = True
    closed = tiles & (hard == 0) & ring & ~opened
    out[opened] = 0
    out[closed] = 1
    return out


def read_index_png(path: Path) -> np.ndarray:
    img = Image.open(path)
    if img.mode != "P" and img.mode != "L":
        raise SystemExit(f"{path}: expected an 8-bit palette/greyscale hardness PNG, got {img.mode}")
    return np.array(img, dtype=np.uint8)


# ---------------------------------------------------------------------------------------------
# Layout sanity: screens must not overlap in the world


def _poly(corners):
    return [tuple(corners["nw"]), tuple(corners["ne"]), tuple(corners["se"]), tuple(corners["sw"])]


def _area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def _clip(subject, clipper):
    """Sutherland-Hodgman intersection of two convex polygons."""
    def inside(pt, a, b):
        return (b[0] - a[0]) * (pt[1] - a[1]) - (b[1] - a[1]) * (pt[0] - a[0]) >= 0

    def cross_point(p1, p2, a, b):
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p1, p2, a, b
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    if sum(clipper[i][0] * clipper[(i + 1) % 4][1] - clipper[(i + 1) % 4][0] * clipper[i][1] for i in range(4)) < 0:
        clipper = clipper[::-1]
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break
        prev = inp[-1]
        for cur in inp:
            if inside(cur, a, b):
                if not inside(prev, a, b):
                    out.append(cross_point(prev, cur, a, b))
                out.append(cur)
            elif inside(prev, a, b):
                out.append(cross_point(prev, cur, a, b))
            prev = cur
    return out


def find_overlaps(layout_screens, min_area_m2=1.0):
    """[(area m2, id a, id b)] for every pair of screens whose quads overlap in the world."""
    items = [(s["id"], _poly(s["corners"])) for s in layout_screens]
    boxes = {sid: (min(x for x, _ in p), min(y for _, y in p), max(x for x, _ in p), max(y for _, y in p)) for sid, p in items}
    found = []
    for i, (a, pa) in enumerate(items):
        ba = boxes[a]
        for b, pb in items[i + 1:]:
            bb = boxes[b]
            if ba[2] <= bb[0] or bb[2] <= ba[0] or ba[3] <= bb[1] or bb[3] <= ba[1]:
                continue
            inter = _clip(pa, pb)
            if len(inter) >= 3 and _area(inter) > min_area_m2:
                found.append((round(_area(inter), 1), a, b))
    return sorted(found, reverse=True)


# ---------------------------------------------------------------------------------------------
# Vision rules from the DinkC ASTs


def vision_rules(ast_dir: Path, script: str):
    """[(vision value, condition text, line)] for every `&vision = N` in a script, with the
    conjunction of the enclosing if/else conditions (engine-effective text). Early returns are
    not modelled (a later assignment may also need the earlier conditions to be false)."""
    path = ast_dir / f"{script}.json"
    if not path.exists():
        return []
    ast = json.loads(path.read_text(encoding="utf-8"))
    out = []

    def cond_text(node):
        eng = node.get("engine") or {}
        return eng.get("effective") or node.get("cond_text") or "?"

    def walk(node, conds):
        if isinstance(node, list):
            for n in node:
                walk(n, conds)
            return
        if not isinstance(node, dict):
            return
        t = node.get("type")
        if t == "assign" and node.get("target") == "&vision" and node.get("op") == "=":
            val = node.get("value") or {}
            if val.get("type") == "int":
                out.append((int(val["value"]), " && ".join(conds) if conds else "always", node.get("line")))
            return
        if t == "if":
            c = cond_text(node)
            walk(node.get("then"), conds + [f"({c})"])
            if node.get("else") is not None:
                walk(node.get("else"), conds + [f"!({c})"])
            return
        for key in ("body", "then", "else", "procedures"):
            if key in node:
                walk(node[key], conds)

    for proc in ast.get("procedures", []):
        walk(proc.get("body", []), [])
    return out


# ---------------------------------------------------------------------------------------------


def git_head(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"



def main(argv=None) -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default=str(default_data_repo(here)), help="data repo root")
    ap.add_argument("--out", default=str(here / "ImportData"), help="bundle directory")
    args = ap.parse_args(argv)

    t0 = time.time()
    data = Path(args.data).resolve()
    out = Path(args.out).resolve()
    dinkex = data / "tools/dinkex/out"
    analyse = data / "tools/analyse/out"
    classes = data / "tools/data"
    dinkc = data / "tools/dinkc/out"

    required = {
        dinkex / "screens": "cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out",
        analyse / "world_layout.json": "cd tools/analyse && python3 -m analyse build --ir ../dinkex/out --out out",
        classes / "sprite_classes.csv": "(tracked in the data repo)",
        dinkc / "script_kinds.csv": "cd tools/dinkc && python3 -m dinkc build --scripts ../../bin/dink/story --map ../../bin/dink/map.dat --dat ../../bin/dink/dink.dat --out out",
    }
    for path, cmd in required.items():
        if not path.exists():
            print(f"EXPORT FAILED: missing {path}\n  regenerate in the data repo with: {cmd}", file=sys.stderr)
            return 2

    out.mkdir(parents=True, exist_ok=True)
    (out / "ground").mkdir(exist_ok=True)
    (out / "ground_mask").mkdir(exist_ok=True)
    terrain_cat = load_terrain_catalogue(here)
    terrain_means = None
    layer_cover = {}
    ground_classes = {}
    shore_cells = {}      # screen -> water_cells (every screen, so each mask can see its neighbours' water)
    screen_masks = {}     # screen -> (terrain mask, its layers, screens.json record): alpha filled in after the loop
    ground_raw = {}       # screen -> the 1997 tile weights of its terrain mask (terrain_mask raw_out), for naturalise_ground_masks
    ground_masks = {}     # screen -> (terrain mask, its layers, screens.json record): written after the loop
    (out / "sprites").mkdir(exist_ok=True)

    layout = json.loads((analyse / "world_layout.json").read_text())
    warps_in = json.loads((analyse / "warps.json").read_text())
    interiors = json.loads((analyse / "interiors.json").read_text())
    encounters = json.loads((analyse / "encounters.json").read_text())
    visions = json.loads((analyse / "vision_variants.json").read_text())
    connectivity = json.loads((analyse / "connectivity.json").read_text())
    regions_csv = {r["id"]: r for r in csv.DictReader(open(analyse / "regions.csv", encoding="utf-8"))}
    sprite_classes = {(int(r["seq"]), int(r["frame"])): r for r in csv.DictReader(open(classes / "sprite_classes.csv", encoding="utf-8"))}
    tile_classes = {int(r["tile_num"]): r for r in csv.DictReader(open(classes / "tile_classes.csv", encoding="utf-8"))}
    script_kinds = {r["script"]: r for r in csv.DictReader(open(dinkc / "script_kinds.csv", encoding="utf-8"))}

    problems = []  # data issues found while exporting (reported, not fatal)

    layout_by_screen = {s["screen"]: s for s in layout["screens"]}
    base_m_per_px = float(layout["base_m_per_px"])

    interior_of = {}
    for it in interiors["interiors"]:
        for sid in it["screens"]:
            interior_of[sid] = it
    enc_by_screen = {e["screen"]: e for e in encounters["screens"]}
    vis_by_screen = {v["screen"]: v for v in visions["screens"]}
    reached_centroids = {}
    for sid, comps in connectivity["components"].items():
        reached_centroids[sid] = [c for c in comps if c.get("reached")]
    join_sides = {}
    for j in connectivity.get("designed_joins", []):
        for side in j["sides"]:
            join_sides.setdefault(side["screen"], []).append(side)

    def group_of(sheet: str) -> str:
        if sheet.startswith("interior:"):
            return "interiors"
        return sheet

    tileset_cache = {}

    def tileset(n: int):
        if n not in tileset_cache:
            p = dinkex / "tiles" / f"ts{n:02d}.png"
            tileset_cache[n] = Image.open(p).convert("RGB") if p.exists() else None
        return tileset_cache[n]

    screens_out, placements_out, collision_out, samples_out = [], [], {}, {}
    pic_keys = {}
    vision_rule_cache = {}
    fill_conflicts = []
    rect_total = 0

    # Overlapping screens would put one screen's blockers on top of another's walkable ground.
    # tools/analyse keeps grid pieces that touch nothing at their nominal position, which can land
    # on stretched neighbours (SCR_299 "Islets" on SCR_333 Murkwood in the 5 Nov 2026 data). The
    # unreached screen of an overlapping pair is excluded; two reached screens overlapping stop the export.
    excluded = {}
    overlaps = find_overlaps(layout["screens"])
    for area_m2, a, b in overlaps:
        ra, rb = regions_csv.get(a, {}).get("reached") == "1", regions_csv.get(b, {}).get("reached") == "1"
        if ra and rb:
            print(f"EXPORT FAILED: reached screens {a} and {b} overlap by {area_m2} m2 in world_layout.json", file=sys.stderr)
            return 1
        loser, winner = (b, a) if ra else (a, b)
        excluded[loser] = f"overlaps {winner} by {area_m2} m2 in tools/analyse world_layout.json (layout bug); unreached, so left out"
        problems.append(f"{loser}: {excluded[loser]}")

    screen_files = sorted((dinkex / "screens").glob("SCR_*.json"))
    for sf in screen_files:
        scr = json.loads(sf.read_text())
        n = scr["screen"]
        sid = scr["id"]
        lay = layout_by_screen.get(n)
        if lay is None:
            problems.append(f"{sid}: in dinkex but not in world_layout.json; skipped")
            continue
        corners = lay["corners"]
        reg = regions_csv.get(sid, {})
        for side in join_sides.get(sid, []):
            join_tiles(scr, side)

        # --- ground image from the tile layer
        ground = Image.new("RGB", (600, 400), (255, 0, 255))
        groups = np.zeros((8, 12), dtype=np.int64)
        for t in scr["tiles"]:
            ts = tileset(t["tileset"])
            src = t["src"]
            if ts is not None and t["src_in_bounds"]:
                ground.paste(ts.crop((src["x"], src["y"], src["x"] + src["w"], src["y"] + src["h"])), (t["x"], t["y"]))
            else:
                problems.append(f"{t['id']}: tileset ts{t['tileset']:02d} missing or source out of bounds; magenta")
            groups[t["row"], t["col"]] = GROUPS.index(tile_group(tile_classes.get(t["num"])))
        # native 600x400; the importer stretches it to a power of two (StretchToPowerOfTwo)
        write_png_if_changed(out / "ground" / f"{sid}.png", ground)
        ground_hash = sha1_bytes(ground.tobytes())
        # --- hardness -> collision rectangles
        hard = read_index_png(dinkex / scr["hardness"]["image"])
        if hard.shape != (400, 600):
            problems.append(f"{sid}: hardness image is {hard.shape}, expected (400, 600)")
        for side in join_sides.get(sid, []):
            hard = join_hardness(hard, side)
        walk = hard == 0
        labels, ncomp = label_components(walk)
        # terrain group per pixel (tile = 50x50), class per component = group with most pixels
        gpix = np.repeat(np.repeat(groups, 50, axis=0), 50, axis=1)
        gc = np.bincount((labels * len(GROUPS) + gpix).ravel(), minlength=(ncomp + 1) * len(GROUPS))
        comp_group = np.argmax(gc.reshape(ncomp + 1, len(GROUPS)), axis=1)
        comp_classes = {lab: GROUPS[int(comp_group[lab])] for lab in range(1, ncomp + 1)}
        flat = labels.ravel()
        comp_area = np.bincount(flat, minlength=ncomp + 1).tolist()
        yy, xx = np.indices(labels.shape)
        bx0 = np.full(ncomp + 1, 600); by0 = np.full(ncomp + 1, 400)
        bx1 = np.zeros(ncomp + 1, int); by1 = np.zeros(ncomp + 1, int)
        nz = flat > 0
        np.minimum.at(bx0, flat[nz], xx.ravel()[nz]); np.minimum.at(by0, flat[nz], yy.ravel()[nz])
        np.maximum.at(bx1, flat[nz], xx.ravel()[nz] + 1); np.maximum.at(by1, flat[nz], yy.ravel()[nz] + 1)
        comp_bbox = {lab: [int(bx0[lab]), int(by0[lab]), int(bx1[lab]), int(by1[lab])] for lab in range(1, ncomp + 1)}
        water_labels = [lab for lab, g in comp_classes.items() if FILL_GROUP.get(g) == "fill_water"]
        solid_labels = [lab for lab, g in comp_classes.items() if FILL_GROUP.get(g) == "fill_solid"]
        fill_water = np.isin(labels, water_labels) if water_labels else np.zeros_like(walk)
        fill_solid = np.isin(labels, solid_labels) if solid_labels else np.zeros_like(walk)
        # cross-check against tools/analyse: no reached component may be filled
        for c in reached_centroids.get(sid, []):
            cx, cy = int(c["centroid"][0]), int(c["centroid"][1])
            # match by area + bbox (analyse labels the permissive mask; where no vision variant or
            # removable hardbox differs, its components equal these exactly)
            match = [lab for lab in comp_classes if comp_area[lab] == c["area_px"] and comp_bbox[lab] == list(c["bbox"])]
            if match:
                lab = match[0]
                if lab in water_labels or lab in solid_labels:
                    fill_conflicts.append(f"{sid}#{c['k']} is reached ({c['area_px']} px) but was filled as {comp_classes[lab]}")
            else:
                # permissive component differs: no reached pixel may be filled. Check the bbox
                # overlap of filled components with a reached component of class land.
                x0, y0, x1, y1 = c["bbox"]
                inside = (fill_water | fill_solid)[y0:y1, x0:x1]
                if c["class"] == "land" and inside.mean() > 0.5:
                    fill_conflicts.append(f"{sid}#{c['k']} is reached, unmatched, and more than half its bbox is filled")
        classes_masks = {
            "solid": (hard == 1) | (hard == 3),
            "low": hard == 2,
            "sprite": hard == 100,
            "warp": hard == 200,
            "fill_water": fill_water,
            "fill_solid": fill_solid,
        }
        other = ~np.isin(hard, [0, 1, 2, 3, 100, 200])
        if other.any():
            problems.append(f"{sid}: {int(other.sum())} hardness pixels with unknown codes {sorted(set(hard[other].tolist()))}; treated as solid")
            classes_masks["solid"] |= other
        rects = {k: mask_to_rects(m) for k, m in classes_masks.items()}
        ground_layers, ground_mask = (None, None)
        if terrain_cat is not None:
            if terrain_means is None:
                terrain_means = terrain_class_means(tile_classes, tileset)
            ground_classes[str(n)] = {}
            shore_water = None if fill_water.any() or scr["indoor"] else natural_water_shape(scr["tiles"], tile_classes, n)
            raw = {}
            ground_layers, ground_mask, cover = terrain_mask(scr, ground, tile_classes, terrain_cat, terrain_means, fill_water, bool(scr["indoor"]),
                                                             facts=ground_classes[str(n)], shore_water=shore_water, raw_out=raw)
            shore_cells[n] = water_cells(fill_water, shore_water)
            ground_raw[n] = dict(raw, indoor=bool(scr["indoor"]))
            if ground_mask is not None:
                if cover is not None:
                    layer_cover[str(n)] = cover
                # written after the loop (shore_alpha, then naturalise_ground_masks)

        rect_total += sum(len(v) for v in rects.values())
        coll_hash = sha1_json(rects)
        collision_out[sid] = rects

        # --- samples for the parity tests (deterministic)
        rng = random.Random(n * 7919)
        walk_ok = walk & ~fill_water & ~fill_solid
        if str(n) in ground_classes:
            trees = forest_points(n, scr["tiles"], tile_classes, walk_ok)
            if trees:
                ground_classes[str(n)]["trees"] = trees
            entries = [c["centroid"] for c in reached_centroids.get(sid, [])] + [(p.get("x", -1), p.get("y", -1)) for p in scr.get("placements") or []]
            relief = relief_points(n, scr["tiles"], tile_classes, walk_ok, hard == 200, entries, bool(scr["indoor"]))
            if relief:
                ground_classes[str(n)]["relief"] = relief
            # water tiles the collision gives no water fill (their hardness blocks them, or the riverbed is ground a
            # player walks): the runtime lays a water surface over them (visual only, dink.WaterTiles)
            if ground_classes[str(n)].get("classes", {}).get("water") and not ground_classes[str(n)].get("water_surface"):
                ground_classes[str(n)]["water_tiles"] = water_tile_rects(scr["tiles"], tile_classes)
        ys, xs = np.nonzero(walk_ok)
        wsamp = []
        if len(xs):
            for i in sorted(rng.sample(range(len(xs)), min(SAMPLES_PER_SCREEN, len(xs)))):
                # keep the sample one pixel away from any blocked pixel so a 1 cm probe is unambiguous
                x, y = int(xs[i]), int(ys[i])
                if 0 < x < 599 and 0 < y < 399 and walk_ok[y - 1:y + 2, x - 1:x + 2].all():
                    wsamp.append({"x": x + 0.5, "y": y + 0.5, "world": bilinear(corners, x + 0.5, y + 0.5)})
        bsamp = []
        for cls, codes in (("solid", (1, 3, 100, 200)), ("low", (2,))):
            m = np.isin(hard, codes)
            ys, xs = np.nonzero(m)
            for i in sorted(rng.sample(range(len(xs)), min(SAMPLES_PER_SCREEN // 2, len(xs)))) if len(xs) else []:
                x, y = int(xs[i]), int(ys[i])
                bsamp.append({"x": x + 0.5, "y": y + 0.5, "world": bilinear(corners, x + 0.5, y + 0.5), "class": cls,
                              "code": int(hard[y, x])})
        samples_out[sid] = {"walkable": wsamp, "blocked": bsamp}

        # --- vision
        vis = vis_by_screen.get(sid)
        vision_info = None
        if vis:
            rules = {}
            for script in sorted(vis.get("vision_setting_scripts", {})):
                if script not in vision_rule_cache:
                    vision_rule_cache[script] = vision_rules(dinkc / "ast", script)
                for val, cond, line in vision_rule_cache[script]:
                    rules.setdefault(str(val), []).append(f"{script}:{line} [{cond}]")
            values = sorted(int(v) for v in vis["visions"])
            for v in values:
                if str(v) not in rules:
                    rules[str(v)] = ["unknown: no script found on this screen assigns &vision = %d" % v]
                    problems.append(f"{sid}: vision {v} is used by placements but no script found on the screen assigns it")
            vision_info = {"values": values, "rules": rules, "setting_scripts": sorted(vis.get("vision_setting_scripts", {}))}

        enc = enc_by_screen.get(sid)
        interior = interior_of.get(sid)
        screen_rec = {
            "id": sid,
            "screen": n,
            "col": scr["col"],
            "row": scr["row"],
            "region": lay["region"],
            "region_name": reg.get("region_name", lay["region"]),
            "name": reg.get("sub_area", ""),
            "kind": lay["kind"],
            "sheet": lay["sheet"],
            "group": group_of(lay["sheet"]),
            "indoor": bool(scr["indoor"]),
            "music": {"raw": scr["music"]["raw"], "action": scr["music"]["action"], "file": scr["music"].get("file")},
            "base_script": scr.get("base_script") or "",
            "encounter": {"screenlock": bool(enc), "locking": bool(enc and enc.get("locking")),
                          "scripts": sorted({s["script"] for s in enc["scripts"]}) if enc else [],
                          "provisional": bool(enc and enc.get("provisional"))},
            "interior": {"id": interior["id"], "name": interior.get("name", ""), "kind": interior.get("kind", "")} if interior else None,
            "vision": vision_info,
            "corners": corners,
            "center": lay["center"],
            "m_per_px_center": lay["m_per_px_center"],
            "ground_image": f"ground/{sid}.png",
            "ground_hash": ground_hash,
            "collision_hash": coll_hash,
            "rect_counts": {k: len(v) for k, v in rects.items()},
            "reached": reg.get("reached") == "1",
            "excluded": excluded.get(sid, ""),
        }
        screen_rec["hash"] = sha1_json(screen_rec)
        # Presentation only, deliberately outside the screen hash: actors and collision do not depend on it.
        if ground_mask is not None:
            screen_rec["ground_layers"] = ground_layers
            screen_rec["ground_mask"] = f"ground_mask/{sid}.png"
            screen_masks[n] = (ground_mask, ground_layers, screen_rec)
            ground_masks[n] = (ground_mask, ground_layers, screen_rec)
        screens_out.append(screen_rec)

        # --- placements
        lay_pl = {p["id"]: p for p in lay["placements"]}
        for p in scr["placements"]:
            pid = p["id"]
            lp = lay_pl.get(pid)
            if lp is None:
                problems.append(f"{pid}: placement missing from world_layout.json; position computed here")
                w = bilinear(corners, p["map_x"], p["map_y"])
                lp = {"x": w[0], "y": w[1], "m_per_px": lay["m_per_px_center"], "scale_x": lay["m_per_px_center"],
                      "scale_y": lay["m_per_px_center"], "rot_deg": 0.0, "size_factor": 1.0}
            sc = sprite_classes.get((p["seq"], p["frame"]))
            if sc is None:
                problems.append(f"{pid}: (seq {p['seq']}, frame {p['frame']}) not in sprite_classes.csv")
            category = sc["category"] if sc else "other"
            pic = p.get("pic")
            card = None
            if pic:
                key = f"{pic['seq']}_{pic['frame']:02d}"
                pic_keys.setdefault(key, pic["image"])
                size = p["size_percent"] / 100.0
                mode = "base" if category in BASE_SCALE_CATEGORIES else "layout"
                sx = (base_m_per_px if mode == "base" else lp["scale_x"]) * size
                sz = (base_m_per_px if mode == "base" else lp["m_per_px"]) * size
                ox, oy = pic["origin"]["x"], pic["origin"]["y"]
                card = {
                    "sprite": key,
                    "scale_mode": mode,
                    "width_m": round(pic["width"] * sx, 4),
                    "height_m": round(pic["height"] * sz, 4),
                    # card centre relative to the placement point, in the card's own frame:
                    # x along the screen's east axis, z up (origin pixel row = ground)
                    "offset_x_m": round((pic["width"] / 2.0 - ox) * sx, 4),
                    "offset_z_m": round(-(pic["height"] - oy) * sz, 4),
                    "pixel_w": pic["width"],
                    "pixel_h": pic["height"],
                }
            vision = int(p["vision"])
            vrule = None
            if vision:
                vrule = (vision_info or {}).get("rules", {}).get(str(vision), ["unknown"])
            # representation: background (type 0) decoration becomes instanced geometry, except
            # when it needs per-object state (vision-gated or a warp) or has no picture to instance.
            if p["type"] == 0 and not vision and not p["is_warp"] and card is not None:
                rep = "instance"
            else:
                rep = "actor"
            script = p.get("script") or ""
            sk = script_kinds.get(script)
            stamp = p.get("hardness_stamp")
            rec = {
                "id": pid,
                "screen": n,
                "index": p["index"],
                "map_x": p["map_x"],
                "map_y": p["map_y"],
                "world": [lp["x"], lp["y"]],
                "m_per_px": lp["m_per_px"],
                "scale_x": lp["scale_x"],
                "scale_y": lp["scale_y"],
                "rot_deg": lp["rot_deg"],
                "size_factor": lp["size_factor"],
                "seq": p["seq"],
                "frame": p["frame"],
                "type": p["type"],
                "kind": p["kind"],
                "size_percent": p["size_percent"],
                "brain": p["brain"],
                "script": script,
                "script_kind": sk["kind"] if sk else ("" if not script else "unknown"),
                "vision": vision,
                "vision_rule": vrule,
                "hardness": {"rect": [stamp["x0"], stamp["y0"], stamp["x1"], stamp["y1"]], "kind": stamp["kind"]} if stamp else None,
                "is_warp": bool(p["is_warp"]),
                "class_id": sc["class_id"] if sc else "",
                "category": category,
                "name": sc["name"] if sc else "",
                "treatment": sc["treatment"] if sc else "",
                "card": card,
                "representation": rep,
                "group": group_of(lay["sheet"]),
                "region": lay["region"],
                "excluded": excluded.get(sid, ""),
            }
            if sk is None and script:
                problems.append(f"{pid}: script '{script}' not in script_kinds.csv")
            rec["hash"] = sha1_json(rec)
            placements_out.append(rec)

    # --- terrain masks: the shore distance in the alpha runs across screen borders (shore_alpha), so water deepens
    # and clears the same way on both sides of a border; presentation only (outside the screen hash, like the mask)
    world_corners = {s["screen"]: s["corners"] for s in screens_out}
    for n, (ground_mask, ground_layers, screen_rec) in sorted(screen_masks.items()):
        alpha = shore_alpha(n, shore_cells, world_neighbours(n, world_corners))
        rgba = np.asarray(ground_mask).copy()
        rgba[:, :, 3] = (alpha * 255.0 + 0.5).astype(np.uint8)
        ground_mask = Image.fromarray(rgba, "RGBA")
        ground_masks[n] = (ground_mask, ground_layers, screen_rec)   # RGB natural outlines and write: naturalise_ground_masks

    by_id = {p["id"]: p for p in placements_out}
    screen_by_num = {s["screen"]: s for s in screens_out}

    # Fitted replacements can release into any authored frame of their source sequence.
    # Include these images through the SAME ordinary texture generation path, never a private QA asset pack.
    family_policy = json.loads((here / "Content/Dink/Data/Art/families.json").read_text())
    canonical_sequences = json.loads((dinkex / "sequences.json").read_text())["sequences"]
    for key, image in release_picture_keys(family_policy, placements_out, canonical_sequences).items():
        pic_keys.setdefault(key, image)
    # Pictures a script saves for a placement (editor_seq / editor_frame: the flat barrel, the open chest) are shown on later
    # visits (UDinkGameplay::PresentPlacementPictures); the importer builds their sprite materials whatever region it imports.
    story = data / "bin/dink/story"
    saved_pictures = saved_picture_keys({p.stem: p.read_text(errors="replace") for p in sorted(story.glob("*.c"))}, canonical_sequences)
    for key, image in saved_pictures.items():
        pic_keys.setdefault(key, image)
    # Script-created sprites without a family mesh are drawn as their 1997 picture on a card (A53): every picture listed
    # in Content/Dink/Data/Art/sprite_pictures.json (Scripts/export_sprite_pictures.py) gets its texture and material too.
    script_pictures = here / "Content/Dink/Data/Art/sprite_pictures.json"
    if script_pictures.exists():
        wanted = set(json.loads(script_pictures.read_text())["pictures"])
        for sequence in canonical_sequences:
            for frame in sequence["frames"]:
                key = f"{sequence['seq']}_{frame['frame']:02d}"
                if key in wanted and frame.get("image"):
                    pic_keys.setdefault(key, frame["image"])
    # Sequences a script replaces with init("load_sequence_now ...") (Seth's pose and walks, s7-mil.c): their frames come from
    # the 1997 archives, keyed "init_<file>_<frame>" (export_sprite_pictures.init_frames).
    from export_sprite_pictures import init_frames
    init_images = {}
    for key, (image, _size) in init_frames(data / "bin/dink", {p.stem: p.read_text(errors="replace") for p in sorted(story.glob("*.c"))}).items():
        init_images[key] = image
        pic_keys.setdefault(key, f"init:{key}")

    # --- sprites
    sprites_out = {}
    for key, image in sorted(pic_keys.items()):
        img = init_images[key] if key in init_images else Image.open(dinkex / image).convert("RGBA")
        w, h = img.size
        pw, ph = min(next_pow2(w), SPRITE_MAX), min(next_pow2(h), SPRITE_MAX)
        arr = np.array(img)
        # bleed opaque colours into transparent pixels (colour-key RGB is white or black) so
        # filtering does not draw a fringe around the cut-out
        alpha = arr[..., 3] > 0
        rgb = arr[..., :3].astype(np.float32)
        filled = alpha.copy()
        for _ in range(4):
            if filled.all():
                break
            acc = np.zeros_like(rgb)
            cnt = np.zeros(filled.shape, dtype=np.float32)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                sh = np.roll(np.roll(filled, dy, 0), dx, 1)
                acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * sh[..., None]
                cnt += sh
            grow = ~filled & (cnt > 0)
            rgb[grow] = acc[grow] / cnt[grow][:, None]
            filled |= grow
        arr[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out_img = Image.fromarray(arr, "RGBA").resize((pw, ph), Image.NEAREST)
        write_png_if_changed(out / "sprites" / f"{key}.png", out_img)
        sprites_out[key] = {"file": f"sprites/{key}.png", "source": image, "width": w, "height": h,
                            "tex_width": pw, "tex_height": ph, "hash": sha1_bytes(arr.tobytes())}
        if key in saved_pictures:
            sprites_out[key]["saved"] = True

    # --- warps
    warps_out = []

    def world_quad(screen_num, rect):
        c = screen_by_num[screen_num]["corners"]
        x0, y0, x1, y1 = rect
        return [bilinear(c, x0, y0), bilinear(c, x1, y0), bilinear(c, x1, y1), bilinear(c, x0, y1)]

    for w in warps_in["sprite_warps"]:
        pl = by_id.get(w["id"])
        if pl is None:
            problems.append(f"warp {w['id']}: no placement record")
            continue
        rect = pl["hardness"]["rect"] if pl["hardness"] else None
        if rect is None:
            problems.append(f"warp {w['id']}: no hardness stamp; trigger from picture hardbox")
        dst = screen_by_num.get(w["dst_screen"])
        rec = {
            "id": w["id"], "source": "sprite", "placement": w["id"], "src_screen": w["src_screen"],
            "trigger_mode": "walk_in", "trigger_rect": rect,
            "trigger_quad": world_quad(w["src_screen"], rect) if rect else None,
            "dst_screen": w["dst_screen"], "dst_x": w["dst_x"], "dst_y": w["dst_y"], "dst_valid": bool(w["dst_valid"] and dst),
            "dst_world": bilinear(dst["corners"], w["dst_x"], w["dst_y"]) if dst else None,
            "kind": w["kind"], "anim_seq": w.get("anim_seq"), "vision": w.get("vision", 0),
            "return_warps": w.get("return_warps", []), "one_way": bool(w.get("one_way")),
            "src_region": w.get("src_region"), "dst_region": w.get("dst_region"), "script": w.get("script") or "",
            "note": "",
        }
        rec["hash"] = sha1_json(rec)
        warps_out.append(rec)

    for w in warps_in["script_warps"]:
        dst = screen_by_num.get(w["dst_screen"])
        base = {
            "source": "script", "script": w["script"], "line": w["line"], "dst_screen": w["dst_screen"],
            "dst_x": w["dst_x"], "dst_y": w["dst_y"], "dst_valid": bool(w["dst_valid"] and dst),
            "dst_world": bilinear(dst["corners"], w["dst_x"], w["dst_y"]) if dst else None,
            "kind": w["kind"], "anim_seq": None, "vision": 0, "return_warps": w.get("return_warps", []),
            "one_way": bool(w.get("one_way")), "dst_region": w.get("dst_region"),
        }
        if w["dst_y"] > 400 or w["dst_x"] > 600 or w["dst_x"] < 0 or w["dst_y"] < 0:
            problems.append(f"warp {w['id']}: destination ({w['dst_x']},{w['dst_y']}) lies outside screen {w['dst_screen']}'s 600x400 map; extrapolated")
        sources = []
        if w.get("src_how") == "placed":
            for sn in w["src_screens"]:
                for p in placements_out:
                    if p["screen"] == sn and p["script"] == w["script"]:
                        sources.append(p)
            if not sources:
                problems.append(f"warp {w['id']}: src_how=placed but no placement on {w['src_screens']} runs {w['script']}")
        for p in sources:
            if p["hardness"]:
                rect = p["hardness"]["rect"]
            elif p["card"]:
                # no hardbox: a trigger around the placement's feet (the sprite's lower third)
                pw, ph = p["card"]["pixel_w"], p["card"]["pixel_h"]
                rect = [p["map_x"] - pw // 4, p["map_y"] - ph // 8, p["map_x"] + pw // 4, p["map_y"] + ph // 8]
            else:
                rect = [p["map_x"] - 15, p["map_y"] - 10, p["map_x"] + 15, p["map_y"] + 10]
            rec = dict(base, id=f"{w['id']}@{p['id']}", warp=w["id"], placement=p["id"], src_screen=p["screen"],
                       trigger_mode="touch_approx", trigger_rect=rect, trigger_quad=world_quad(p["screen"], rect),
                       src_region=screen_by_num[p["screen"]]["region"],
                       note=f"script warp: {w['script']} line {w['line']}; story conditions and dialogue are not modelled, walking into the placement fires it")
            rec["hash"] = sha1_json(rec)
            warps_out.append(rec)
        if not sources:
            for sn in w["src_screens"]:
                if sn not in screen_by_num:
                    continue
                rec = dict(base, id=f"{w['id']}@SCR_{sn:03d}", warp=w["id"], placement=None, src_screen=sn,
                           trigger_mode="script_only", trigger_rect=None, trigger_quad=None,
                           src_region=screen_by_num[sn]["region"],
                           note=f"script warp fired {w.get('src_how')}; no placement to walk into, so the trigger is inactive (marker only)")
                rec["hash"] = sha1_json(rec)
                warps_out.append(rec)

    # --- start
    start_cfg = {"screen": 1, "x": 314, "y": 161, "dir": 4}  # main.c &player_map = 1; start-1.c sp_x 334 (-20), sp_y 161, sp_dir 4
    start = dict(start_cfg, world=bilinear(screen_by_num[1]["corners"], start_cfg["x"], start_cfg["y"]),
                 note="new game: main.c make_global_int(&player_map, 1); start-1.c click(): sp_x(1,334) sp_y(1,161) sp_dir(1,4); "
                      "screen 1 is Dink's house (vision 0 = intact; vision 1/2 = burning/burnt, set by s1-h1-s on &story)")

    # --- links for the continuity test: walkable grid crossings inside one sheet
    links = []
    sheet_of = {s["id"]: s["sheet"] for s in screens_out}
    for c in connectivity["crossings"]:
        if not c.get("walkable"):
            continue
        a, b = c["a"], c["b"]
        if a not in sheet_of or b not in sheet_of:
            continue
        links.append({"a": a, "b": b, "dir": c["dir"], "axis": c["axis"], "from": c["from"], "to": c["to"],
                      "same_sheet": sheet_of[a] == sheet_of[b], "reached": bool(c.get("reached"))})
    seams = [l for l in links if not l["same_sheet"]]

    # --- counts per region (the import tests compute their expectations from these)
    regions = sorted({s["region"] for s in screens_out})

    def counts_for(pred_screen):
        scr_ids = {s["screen"] for s in screens_out if pred_screen(s) and not s["excluded"]}
        pls = [p for p in placements_out if p["screen"] in scr_ids]
        ws = [w for w in warps_out if w["src_screen"] in scr_ids]
        return {
            "screens": len(scr_ids),
            "indoor_screens": sum(1 for s in screens_out if s["screen"] in scr_ids and s["indoor"]),
            "placements": len(pls),
            "placement_actors": sum(1 for p in pls if p["representation"] == "actor"),
            "placement_instances": sum(1 for p in pls if p["representation"] == "instance"),
            "vision_gated": sum(1 for p in pls if p["vision"]),
            "warps": len(ws),
            "sprite_warps": sum(1 for w in ws if w["source"] == "sprite"),
            "script_warps": sum(1 for w in ws if w["source"] == "script"),
            "encounter_screens": sum(1 for s in screens_out if s["screen"] in scr_ids and s["encounter"]["screenlock"]),
        }

    counts = {"all": counts_for(lambda s: True)}
    for r in regions:
        counts[r] = counts_for(lambda s, r=r: s["region"] == r)

    inputs = {}
    for p in [analyse / f for f in ("world_layout.json", "warps.json", "interiors.json", "encounters.json",
                                    "vision_variants.json", "regions.csv", "connectivity.json")] + \
             [classes / "sprite_classes.csv", classes / "tile_classes.csv", dinkc / "script_kinds.csv"]:
        inputs[str(p.relative_to(data))] = sha1_file(p)

    if terrain_cat is not None:
        # the colour of each screen's water, sea to pond (visual only; the importer reads `water_sea` for water fills)
        sea = mark_sea_water(ground_classes, {s["screen"]: s["kind"] for s in screens_out},
                             {s["screen"]: collision_out.get(s["id"], {}).get("fill_water") or [] for s in screens_out})
        for s in screens_out:
            if s["screen"] in sea and (collision_out.get(s["id"], {}).get("fill_water")):
                s["water_sea"] = sea[s["screen"]]
                s["water_sea_patch"] = ground_classes[str(s["screen"])]["water_sea_patch"]
        # natural land-layer outlines across screen borders (after the sea colour, which reads the 1997 layers);
        # presentation only (outside the screen hash, like the mask)
        natural = naturalise_ground_masks(out, terrain_cat, ground_raw, ground_masks, {s["screen"]: s["corners"] for s in screens_out},
                                          ground_classes, layer_cover)
        print(f"terrain masks: {natural['natural']} outdoor screens with natural layer outlines, {natural['indoor']} kept tile-shaped "
              f"(indoor); folded for want of a mask channel: {natural['bleed_folded']} neighbour layers, {natural['own_folded']} own layers")
        print(f"terrain masks: 1997 layer regions split by the smoothing {natural['split_before']} -> {natural['split']}, joined "
              f"{natural['merged_before']} -> {natural['merged']} (window); written masks before the final check split "
              f"{natural['final_fix'].get('split_before', 0)}, joined {natural['final_fix'].get('merged_before', 0)}; written split {natural['final_split']}, "
              f"joined {natural['final_merged']}: " + ", ".join(f"{n} {k}" for n, k in (natural['final_split_screens'] + natural['final_merged_screens'])[:40]))
    write_json(out / "screens.json", {"schema": EXPORTER_VERSION + "/screens", "screens": screens_out})
    if terrain_cat is not None:
        # Runtime grass scatter hook (UDinkEnvironmentSubsystem): meadow coverage per screen (w x h, sampled bilinearly).
        cover_dir = here / "Content/Dink/Data/Environment"
        cover_dir.mkdir(parents=True, exist_ok=True)
        cover_text = json.dumps({"schema": "dink-environment-layer-cover/1", "layer": terrain_cat.get("grass_layer", "MeadowTurf"),
                                 "w": TERRAIN_MASK_W // COVER_DIV, "h": TERRAIN_MASK_H // COVER_DIV, "screens": layer_cover}, sort_keys=True)
        cover_file = cover_dir / "layer_cover.json"
        if not cover_file.exists() or cover_file.read_text() != cover_text:
            cover_file.write_text(cover_text)
        # What each screen's ground is made of (Scripts/art_coverage.py screen_ground_state reads it with ground_review.json).
        classes_text = json.dumps({"schema": "dink-environment-ground-classes/3",
                                   "note": "Generated by Scripts/export_import_bundle.py; never hand-edit. Per screen: tile classes (tiles of 96), "
                                           "the terrain layer each class maps to, the layers the screen's mask carries (at most four), "
                                           "the layers folded into another one (merged: same family, dropped: another layer), "
                                           "where trees stand on its forest-canopy tiles (map x, y, 1 on the forest's edge), where rock may stand on its cliff, "
                                           "rock-mass and cave-wall tiles (`relief`: map x, y, clear radius px, tier 1 = hardness blocks the disc / 2 = only an "
                                           "enclosed pocket is walkable there, class 0 cliff_face 1 rock_mass 2 cave_wall), whether the importer draws a water "
                                           "surface, the water tiles the runtime covers when it does not (`water_tiles`: map-pixel rects), and how much "
                                           "of the sea's colour the screen's water takes (`water_sea`, 0 pond .. 1 sea, water_sea_weights; `water_sea_patch`: the weight at its corners, edge middles and centre, water_sea_patches).",
                                   "screens": ground_classes}, sort_keys=True, indent=0) + "\n"
        classes_file = cover_dir / "ground_classes.json"
        if not classes_file.exists() or classes_file.read_text() != classes_text:
            classes_file.write_text(classes_text)
    write_json(out / "placements.json", {"schema": EXPORTER_VERSION + "/placements", "placements": placements_out})
    write_json(out / "warps.json", {"schema": EXPORTER_VERSION + "/warps", "warps": warps_out})
    write_json(out / "collision.json", {"schema": EXPORTER_VERSION + "/collision",
                                        "classes": {"solid": "codes 1,3", "low": "code 2", "sprite": "code 100",
                                                    "warp": "code 200", "fill_water": "code 0, water component",
                                                    "fill_solid": "code 0, canopy/void/chasm component"},
                                        "screens": collision_out})
    write_json(out / "samples.json", {"schema": EXPORTER_VERSION + "/samples", "screens": samples_out, "links": links})
    write_json(out / "sprites.json", {"schema": EXPORTER_VERSION + "/sprites", "sprites": sprites_out})
    bundle = {
        "schema": EXPORTER_VERSION,
        "source": {"data_repo_commit": git_head(data), "inputs": inputs},
        "transform": {
            "map_pixel": "map_x = placement x - 20, map_y = y; u = map_x/600, v = map_y/400",
            "world_metres": "bilinear blend of the screen's corners nw/ne/sw/se (tools/analyse world_layout.json); x east, y south",
            "unreal": "X = 100 * x_east_m, Y = 100 * y_south_m, Z = 100 * height_m (left-handed, Z up; no mirroring)",
        },
        "base_m_per_px": base_m_per_px,
        "ground_texture": [600, 400],
        "start": start,
        "regions": regions,
        "groups": sorted({s["group"] for s in screens_out}),
        "counts": counts,
        "rect_total": rect_total,
        "seams_in_links": len(seams),
        "fill_conflicts": fill_conflicts,
        "designed_joins": [{"id": j["id"], "decided": j["decided"], "screens": j["screens"],
                            "open": {sd["screen"]: sd["open"] for sd in j["sides"]}}
                           for j in connectivity.get("designed_joins", [])],
        "overlaps": [{"area_m2": a, "a": x, "b": y} for a, x, y in overlaps],
        "excluded_screens": excluded,
        "problems": problems,
        "files": {
            name: sha1_file(out / name) for name in
            ("screens.json", "placements.json", "warps.json", "collision.json", "samples.json", "sprites.json")
        },
    }
    write_json(out / "bundle.json", bundle, indent=1)
    secs = time.time() - t0
    c = counts["all"]
    print(f"EXPORT OK in {secs:.1f}s: {c['screens']} screens, {c['placements']} placements "
          f"({c['placement_actors']} actors, {c['placement_instances']} instances), {c['warps']} warp triggers "
          f"({c['sprite_warps']} sprite, {c['script_warps']} script), {len(sprites_out)} sprites, {rect_total} collision rects, "
          f"{len(problems)} data notes, {len(fill_conflicts)} fill conflicts -> {out}")
    sb = counts.get("stonebrook")
    if sb:
        print(f"  stonebrook: {sb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
