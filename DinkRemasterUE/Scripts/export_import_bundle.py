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


def release_picture_keys(family_policy: dict, placements: list, canonical_sequences: list) -> dict:
    """Canonical animation pictures required by fitted-source release; no IO/native writes."""
    fitted_ids = {row["origin"] for row in family_policy.get("collision_fit", {}).get("origins", [])}
    release_sequences = {p["seq"] for p in placements if p["id"] in fitted_ids}
    pictures = {}
    if release_sequences:
        found = set()
        for sequence in canonical_sequences:
            if sequence["seq"] not in release_sequences:
                continue
            found.add(sequence["seq"])
            for frame in sequence["frames"]:
                if frame.get("empty") or not frame.get("width") or not frame.get("height"):
                    continue
                if not frame.get("image"):
                    raise ValueError(f"missing release picture source {sequence['seq']}/{frame['frame']}")
                pictures.setdefault(f"{sequence['seq']}_{frame['frame']:02d}", frame["image"])
        if found != release_sequences:
            raise ValueError("missing canonical release sequence metadata")

    return pictures


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
        rect_total += sum(len(v) for v in rects.values())
        coll_hash = sha1_json(rects)
        collision_out[sid] = rects

        # --- samples for the parity tests (deterministic)
        rng = random.Random(n * 7919)
        walk_ok = walk & ~fill_water & ~fill_solid
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

    by_id = {p["id"]: p for p in placements_out}
    screen_by_num = {s["screen"]: s for s in screens_out}

    # Fitted replacements can release into any authored frame of their source sequence.
    # Include these images through the SAME ordinary texture generation path, never a private QA asset pack.
    family_policy = json.loads((here / "Content/Dink/Data/Art/families.json").read_text())
    canonical_sequences = json.loads((dinkex / "sequences.json").read_text())["sequences"]
    for key, image in release_picture_keys(family_policy, placements_out, canonical_sequences).items():
        pic_keys.setdefault(key, image)

    # --- sprites
    sprites_out = {}
    for key, image in sorted(pic_keys.items()):
        src = dinkex / image
        img = Image.open(src).convert("RGBA")
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

    write_json(out / "screens.json", {"schema": EXPORTER_VERSION + "/screens", "screens": screens_out})
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
