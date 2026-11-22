#!/usr/bin/env python3
"""World heightfield ("landforms") from the 1997 map: real shape under the flat ground sheets.

    python3 Scripts/export_landforms.py [--data <data repo>] [--bundle ImportData] [--out Content/Dink/Data/Environment]
                                        [--screens all|N,N-M,...] [--preview <dir>] [--check]

Owner direction of 15 Nov 2026 ("real shape to the landscape, reshape terrain since we can, photoreal, not blocky").
The SIMULATION stays the 1997 hardness: this is presentation only (coordinator decision of 16 Nov 2026: a VISUAL height
layer; UDinkLandformsSubsystem lays a ground mesh WITHOUT collision, the player's capsule keeps the importer's flat
floor and only his drawn body stands on this ground). Rules, in order of precedence:

  * Ground a player can reach in 1997 (walkable components that tools/analyse marks `reached`, plus the hardboxes
    of the things that stand on it) is LAND: 0 .. about 0.5 m of gentle, low-frequency undulation, never below 0
    (only the player's drawn body wades), worn a few centimetres where the tiles are paths, and sloping to 0 at the
    water's edge (banks). Its slope stays gentle (his drawn feet follow it).
  * Water (water tiles nobody reaches, the collision's water fill) is a BED below the 3 cm water surface, deepening
    away from the shore. The shoreline used for banks and beds is the DRAWN waterline of the natural shorelines (PR #150:
    the alpha of the export's ground masks is the signed distance from it, +-2 m), so the bank meets the drawn water
    exactly; away from that band the 1997 water outline with its tile steps rounded off takes over, joined to the drawn
    line by a correction that fades over DRAWN_FADE_M. Banks curve, never stair. Walkable 1997 ground the drawn water
    covers stays at 0 (just under the 3 cm surface: the shallow edge; bridge decks stay level).
  * Ground nobody reaches rises where its tiles paint rock (cliff faces, rock masses, cave walls), forest canopy
    (rolling hills under the pines) or unreachable land, and drops where they paint chasms. The rise grows with the
    distance from reachable ground and is capped by the PLAY CAMERA (boom 400 cm, pitch -12, free yaw): within the
    boom's reach of any walkable point the ground stays under the line from the camera to Dink (CAMERA_* below), so
    no hill ever stands between the camera and the player. Further away cliffs stand up to their full height.
  * Interiors, dungeons, settlements, screens dressed by an authored art manifest and the 1997 building facades stay
    flat (0), with a smooth falloff into their neighbours, so authored meshes, houses and floors are untouched.

Everything is computed on ONE raster of the whole 32 x 24 screen map (CELL_PX map pixels per cell), so screens that
share an edge share the same heights there. Output, per screen that has any height:

  landforms.json  schema dink-landforms/1: grid spacing, per screen its atlas cell, mm range, flags; the screens list
  landforms.png   16-bit greyscale atlas, one (601/GRID_PX + 1) x (401/GRID_PX + 1) vertex tile per screen;
                  value = height in mm + 32768 at map pixel (i * GRID_PX, j * GRID_PX).

Stdlib + numpy + Pillow. Deterministic (same input, same bytes).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from remaster_paths import default_data_repo  # noqa: E402
from export_import_bundle import label_components, read_index_png  # noqa: E402

SCHEMA = "dink-landforms/1"
COLS, ROWS = 32, 24
SW, SH = 600, 400
CELL_PX = 5            # raster cell (map pixels)
GRID_PX = 10           # output vertex spacing (map pixels): 61 x 41 vertices per screen
GW, GH = SW // GRID_PX + 1, SH // GRID_PX + 1

# land
LAND_BASE_M = 0.10     # lowest open ground (paths dip from here, never below 0)
LAND_AMP_M = 0.34      # undulation on top (two octaves of smooth value noise)
LAND_WAVE_PX = 420.0   # about 29 m in the wilderness layout
PATH_WEAR_M = 0.06
BANK_M = 1.6           # e-folding width of the bank (land side)
FOOTHILL_M = 0.10      # open ground rises a little towards rock
WALK_RISE_MAX_M = 0.14 # what the final smoothing may lift reachable ground above its own land height
# water
WADE_DEPTH_M = 0.25    # walkable 1997 water (fords, shallows): shin deep, knee at most where it is widest
WADE_WIDTH_M = 1.1     # e-folding width from the walkable water's edge
BED_DEPTH_M = 0.9      # rivers and ponds (the far backdrop skirt lies at -1.5 m: stay above it)
SEA_BED_DEPTH_M = 1.3
BED_WIDTH_M = 7.0      # width of the fall from the shelf to the full depth
BED_SHELF_M = 2.0      # shallow shelf along the shore
BED_SHELF_DEPTH_M = 0.04
SHORE_BLUR_PX = 30.0   # rounds the tile steps of the 1997 outline ...
SHORE_DEVIATION_PX = 25.0   # ... within half a tile of it (coordinator decision of 15 Nov 2026)
SHORE_RANGE_CM = 400.0      # the ground masks' alpha: 0.5 at the drawn waterline, +-0.5 over +-2 m (export_import_bundle.py)
DRAWN_BAND = 0.47           # alpha within 0.5 +- this is inside the measured band (not clipped)
DRAWN_FADE_M = 2.5          # the drawn line's correction of the 1997 shoreline fades over this distance outside the band
# rises (metres above the land height), by tile class of the unreached ground
RISE = {"cliff_face": (4.2, 1.8), "rock_mass": (3.2, 1.6), "cave_wall": (3.6, 1.4), "canopy": (1.5, 5.0), "hill": (0.9, 4.0)}
CHASM_DEPTH_M = 1.3
# the play camera (Scripts/PhotorealQA/town_script.py: boom 400 cm, pitch -12, free yaw; zoom to 650 cm)
CAMERA_BASE_M = 0.45   # pivot (capsule centre, 0.96 m) minus the boom probe and a margin
CAMERA_SLOPE = 0.18    # tan(12 deg) = 0.21, with a margin
CAMERA_REACH_M = 7.0   # beyond the zoomed-out boom: the cap opens up
CAMERA_OPEN_SLOPE = 1.0
SOFT_MIN_M = 0.12
# flat things
FLAT_FALLOFF_M = 6.0
PAD_M = 1.2            # a building's footprint (structure sets, town houses) is levelled this far round it ...
PAD_FALLOFF_M = 3.5    # ... and blends back into the land over this distance
FINAL_BLUR_CELLS = 1.2
RISE_BLUR_CELLS = 3.0

ROCK_CLASSES = ("cliff_face", "rock_mass", "cave_wall")
FLAT_TILE_CLASSES = ("structure_facade", "lava", "wood_floor", "stone_floor")
PATH_CLASSES = ("path", "dirt")


# ------------------------------------------------------------------------------------------------ raster helpers
def box_blur(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    if r <= 0:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def gauss(a: np.ndarray, sigma_cells: float) -> np.ndarray:
    """Three box passes per axis (close to a Gaussian of that sigma)."""
    if sigma_cells <= 0.05:
        return a.astype(np.float32)
    r = max(1, int(round(math.sqrt(12.0 * sigma_cells * sigma_cells / 3.0 + 1.0) / 2.0 - 0.5)))
    out = a.astype(np.float32)
    for axis in (0, 1):
        for _ in range(3):
            out = box_blur(out, r, axis)
    return out


def distance(src: np.ndarray, limit_cells: int) -> np.ndarray:
    """Chamfer (3-4) distance in cells from the True cells of src, saturating at limit_cells."""
    big = np.float32(limit_cells + 1)
    d = np.where(src, np.float32(0), big).astype(np.float32)
    for _ in range(limit_cells + 1):
        prev = d
        n = d.copy()
        n[1:, :] = np.minimum(n[1:, :], d[:-1, :] + 1)
        n[:-1, :] = np.minimum(n[:-1, :], d[1:, :] + 1)
        n[:, 1:] = np.minimum(n[:, 1:], d[:, :-1] + 1)
        n[:, :-1] = np.minimum(n[:, :-1], d[:, 1:] + 1)
        s2 = np.float32(math.sqrt(2.0))
        n[1:, 1:] = np.minimum(n[1:, 1:], d[:-1, :-1] + s2)
        n[1:, :-1] = np.minimum(n[1:, :-1], d[:-1, 1:] + s2)
        n[:-1, 1:] = np.minimum(n[:-1, 1:], d[1:, :-1] + s2)
        n[:-1, :-1] = np.minimum(n[:-1, :-1], d[1:, 1:] + s2)
        d = np.minimum(n, big)
        if np.array_equal(d, prev):
            break
    return d


def value_noise(shape, wave_cells: float, seed: int) -> np.ndarray:
    """Smooth 0..1 noise: a coarse random lattice, bicubic-resized (deterministic)."""
    h, w = shape
    gh, gw = int(math.ceil(h / wave_cells)) + 3, int(math.ceil(w / wave_cells)) + 3
    rng = np.random.default_rng(seed)
    lattice = rng.random((gh, gw)).astype(np.float32)
    img = Image.fromarray(lattice).resize((int(gw * wave_cells), int(gh * wave_cells)), Image.BICUBIC)
    a = np.asarray(img, dtype=np.float32)[int(wave_cells):int(wave_cells) + h, int(wave_cells):int(wave_cells) + w]
    lo, hi = np.percentile(a, 1), np.percentile(a, 99)
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)


def drawn_shore(screens: list, bundle: Path, H: int, W: int, cpx: int):
    """Signed distance (m, + land, - water) from the DRAWN waterline on the raster, from each outdoor screen's ground
    mask alpha (texel i of 96 at map x = i / 95 * 600, j of 64 at y = j / 63 * 400, edge to edge); NaN where a mask is
    missing or its alpha is clipped (farther than ~2 m from the line)."""
    out = np.full((H, W), np.nan, np.float32)
    n_masks = 0
    for s in screens:
        rel = s.get("ground_mask")
        if s.get("excluded") or not rel or s["indoor"] or s["sheet"].startswith("interior:"):
            continue
        path = bundle / rel
        if not path.exists():
            continue
        img = Image.open(path)
        if img.mode != "RGBA":
            continue
        a = np.asarray(img, dtype=np.float32)[:, :, 3] / 255.0           # 64 x 96
        mh, mw = a.shape
        c, r = s["col"], s["row"]
        px = (np.arange(SW // cpx) + 0.5) * cpx
        py = (np.arange(SH // cpx) + 0.5) * cpx
        u = px / SW * (mw - 1)
        v = py / SH * (mh - 1)
        u0 = np.clip(np.floor(u).astype(int), 0, mw - 2); fu = u - u0
        v0 = np.clip(np.floor(v).astype(int), 0, mh - 2); fv = v - v0
        top = a[v0][:, u0] * (1 - fu) + a[v0][:, u0 + 1] * fu
        bot = a[v0 + 1][:, u0] * (1 - fu) + a[v0 + 1][:, u0 + 1] * fu
        al = top * (1 - fv)[:, None] + bot * fv[:, None]
        d = np.where(np.abs(al - 0.5) < DRAWN_BAND, (al - 0.5) * SHORE_RANGE_CM / 100.0, np.nan)
        out[r * SH // cpx:(r + 1) * SH // cpx, c * SW // cpx:(c + 1) * SW // cpx] = d
        n_masks += 1
    return out, n_masks


def fade_out(values: np.ndarray, known: np.ndarray, decay: np.ndarray, steps: int) -> np.ndarray:
    """`values` where `known`, carried outward one cell per step (mean of the known 4-neighbours) times `decay`."""
    v = np.where(known, values, 0.0).astype(np.float64)
    k = known.copy()
    for _ in range(steps):
        acc = np.zeros_like(v)
        cnt = np.zeros_like(v)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            kv = np.roll(k, (dy, dx), axis=(0, 1))
            vv = np.roll(v, (dy, dx), axis=(0, 1))
            acc += np.where(kv, vv, 0.0)
            cnt += kv
        new = ~k & (cnt > 0)
        if not new.any():
            break
        v = np.where(new, acc / np.maximum(cnt, 1) * decay, v)
        k = k | new
    return np.where(k, v, 0.0).astype(np.float32)


def building_pads(project: Path, screens: list, H: int, W: int, cpx: int):
    """-> list of (bool footprint mask on the raster, dilated by PAD_M) for every building footprint of the structure sets
    and town houses (Content/Dink/Data/Art/*.json `footprints`: map px, yaw, rect_cm local)."""
    by_num = {s["screen"]: s for s in screens}
    pads = []
    for name in ("town_houses.json", "structure_sets.json"):
        f = project / "Content/Dink/Data/Art" / name
        if not f.exists():
            continue
        rows = json.loads(f.read_text()).get("screens", {})
        for key, row in rows.items():
            s = by_num.get(int(key))
            if not s or s.get("excluded"):
                continue
            mpp = math.dist(s["corners"]["nw"], s["corners"]["ne"]) / SW
            for fp in row.get("footprints", []) or []:
                (px, py), yaw, (x0, y0, x1, y1) = fp["px"], math.radians(fp.get("yaw", 0.0)), fp["rect_cm"]
                pad = PAD_M * 100.0
                x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
                gx = s["col"] * SW + px
                gy = s["row"] * SH + py
                r = math.hypot(max(abs(x0), abs(x1)), max(abs(y0), abs(y1))) / (100.0 * mpp)
                ys = slice(max(0, int((gy - r) // cpx)), min(H, int((gy + r) // cpx) + 1))
                xs = slice(max(0, int((gx - r) // cpx)), min(W, int((gx + r) // cpx) + 1))
                if ys.start >= ys.stop or xs.start >= xs.stop:
                    continue
                cy, cx = np.mgrid[ys, xs]
                dx = ((cx + 0.5) * cpx - gx) * mpp * 100.0
                dy = ((cy + 0.5) * cpx - gy) * mpp * 100.0
                lx = dx * math.cos(yaw) + dy * math.sin(yaw)
                ly = -dx * math.sin(yaw) + dy * math.cos(yaw)
                m = np.zeros((H, W), bool)
                m[ys, xs] = (lx >= x0) & (lx <= x1) & (ly >= y0) & (ly <= y1)
                if m.any():
                    pads.append(m)
    return pads


def smin(a, b, k):
    """Smooth minimum (k in the units of a and b)."""
    return np.minimum(a, b) - k * np.log1p(np.exp(-np.abs(a - b) / k))


def parse_screens(text: str):
    if text in ("", "all"):
        return None
    out = set()
    for part in text.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


# ------------------------------------------------------------------------------------------------ inputs
def flat_screens(project: Path, screens: list) -> dict:
    """Screens that keep a flat floor: interiors, dungeons, settlements, authored art screens, town houses."""
    out = {}
    for s in screens:
        n = s["screen"]
        if s["indoor"]:
            out[n] = "indoor"
        elif s["kind"] in ("interior", "dungeon"):
            out[n] = s["kind"]
        elif s["kind"] == "settlement":
            out[n] = "settlement"
    art = project / "Content/Dink/Data/Art"
    for f in sorted(art.glob("*.json")):
        try:
            j = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(j, dict):
            continue
        for key in ("hide_screen_visuals", "authored_collision_screens"):
            for v in j.get(key) or []:
                if isinstance(v, (int, float)):
                    out.setdefault(int(v), f"authored ({f.name})")
        if isinstance(j.get("screen"), int) and j.get("hide_screen_visuals"):
            out.setdefault(int(j["screen"]), f"authored ({f.name})")
        if f.name == "town_houses.json" and isinstance(j.get("screens"), dict):
            for k in j["screens"]:
                out.setdefault(int(k), "town houses")
    return out


def reached_mask(sid: str, hard: np.ndarray, comps: list) -> tuple[np.ndarray, int]:
    """Pixels of the walkable components tools/analyse marks reached (matched by area and bbox, as the bundle export
    does). A component it labelled differently counts as reached when a reached component's centroid lies in it or
    their boxes overlap by more than half (never raise ground someone may stand on)."""
    walk = hard == 0
    labels, n = label_components(walk)
    if n == 0:
        return np.zeros_like(walk), 0
    flat = labels.ravel()
    area = np.bincount(flat, minlength=n + 1)
    yy, xx = np.indices(labels.shape)
    bx0 = np.full(n + 1, SW); by0 = np.full(n + 1, SH); bx1 = np.zeros(n + 1, int); by1 = np.zeros(n + 1, int)
    nz = flat > 0
    np.minimum.at(bx0, flat[nz], xx.ravel()[nz]); np.minimum.at(by0, flat[nz], yy.ravel()[nz])
    np.maximum.at(bx1, flat[nz], xx.ravel()[nz] + 1); np.maximum.at(by1, flat[nz], yy.ravel()[nz] + 1)
    key = {(int(area[l]), int(bx0[l]), int(by0[l]), int(bx1[l]), int(by1[l])): l for l in range(1, n + 1)}
    reached = np.zeros(n + 1, bool)
    unmatched = 0
    for c in comps:
        k = (int(c["area_px"]), *[int(v) for v in c["bbox"]])
        if k in key:
            if c.get("reached"):
                reached[key[k]] = True
            continue
        if not c.get("reached"):
            continue
        unmatched += 1
        cx, cy = int(c["centroid"][0]), int(c["centroid"][1])
        if 0 <= cx < SW and 0 <= cy < SH and labels[cy, cx] > 0:
            reached[labels[cy, cx]] = True
        x0, y0, x1, y1 = c["bbox"]
        sub = labels[y0:y1, x0:x1]
        for l in np.unique(sub[sub > 0]):
            ox = max(0, min(x1, bx1[l]) - max(x0, bx0[l])); oy = max(0, min(y1, by1[l]) - max(y0, by0[l]))
            if ox * oy > 0.5 * (bx1[l] - bx0[l]) * (by1[l] - by0[l]):
                reached[l] = True
    return reached[labels] & walk, unmatched


# ------------------------------------------------------------------------------------------------ main build
def build(data: Path, bundle: Path, project: Path, only=None, log=print):
    screens = json.loads((bundle / "screens.json").read_text())["screens"]
    collision = json.loads((bundle / "collision.json").read_text())["screens"]
    tile_classes = {int(r["tile_num"]): r for r in csv.DictReader(open(data / "tools/data/tile_classes.csv", encoding="utf-8"))}
    connectivity = json.loads((data / "tools/analyse/out/connectivity.json").read_text())["components"]
    dinkex = data / "tools/dinkex/out"
    flat_of = flat_screens(project, screens)
    if only is not None:
        # a test region: everything outside it keeps its flat sheet, and the region falls off to meet it
        for s in screens:
            if s["screen"] not in only:
                flat_of.setdefault(s["screen"], "outside the landforms region")

    W, H = COLS * SW // CELL_PX, ROWS * SH // CELL_PX
    cpx = CELL_PX
    valid = np.zeros((H, W), bool)          # an outdoor screen with height here
    mpp = np.full((H, W), 0.069, np.float32)  # metres per map pixel of the cell's screen
    sea = np.zeros((H, W), np.float32)
    flat_src = np.zeros((H, W), bool)
    frac = {k: np.zeros((H, W), np.float32) for k in ("reach", "obj", "water", "water_reached", "rock_cliff_face", "rock_rock_mass",
                                                       "rock_cave_wall", "canopy", "chasm", "hill", "path", "facade")}
    by_num = {s["screen"]: s for s in screens}
    stats = {"screens": 0, "unmatched_components": 0}
    for s in screens:
        n = s["screen"]
        if s.get("excluded"):
            continue
        c, r = s["col"], s["row"]
        ys, xs = slice(r * SH // cpx, (r + 1) * SH // cpx), slice(c * SW // cpx, (c + 1) * SW // cpx)
        corners = s["corners"]
        m_per_px = math.dist(corners["nw"], corners["ne"]) / SW
        mpp[ys, xs] = m_per_px
        if n in flat_of:
            flat_src[ys, xs] = True
        if s["indoor"] or s["sheet"].startswith("interior:"):
            continue
        sea[ys, xs] = float(s.get("water_sea", 1.0 if s["kind"] == "sea" else 0.0) or 0.0)
        scr = json.loads((dinkex / "screens" / f"{s['id']}.json").read_text())
        hard = read_index_png(dinkex / scr["hardness"]["image"])
        terr = np.empty((8, 12), object)
        terr[:] = ""
        for t in scr["tiles"]:
            terr[t["row"], t["col"]] = (tile_classes.get(t["num"]) or {}).get("terrain", "")
        tpix = np.repeat(np.repeat(terr, 50, axis=0), 50, axis=1)
        reached, unmatched = reached_mask(s["id"], hard, connectivity.get(s["id"], []))
        stats["unmatched_components"] += unmatched
        coll = collision.get(s["id"], {})
        fill_water = np.zeros((SH, SW), bool)
        for x0, y0, x1, y1 in coll.get("fill_water", []):
            fill_water[y0:y1, x0:x1] = True
        fill_solid = np.zeros((SH, SW), bool)
        for x0, y0, x1, y1 in coll.get("fill_solid", []):
            fill_solid[y0:y1, x0:x1] = True
        obj = np.isin(hard, (100, 200))
        is_water_tile = tpix == "water"
        # water the collision lets a walker into (hardness 0, not filled): fords and shallows; wading water, never raised
        wade_water = is_water_tile & (hard == 0) & ~fill_water & ~fill_solid
        reached = reached | wade_water
        free = ~reached & ~obj
        water = (is_water_tile & ~reached) | fill_water
        rocks = {k: free & (tpix == k) & ~water for k in ROCK_CLASSES}
        canopy = free & (tpix == "forest_canopy") & ~water
        chasm = free & np.isin(tpix, ("chasm", "void")) & ~water
        facade = free & np.isin(tpix, FLAT_TILE_CLASSES) & ~water
        hill = free & ~water & ~canopy & ~chasm & ~facade & ~np.logical_or.reduce(list(rocks.values()))
        path = reached & np.isin(tpix, PATH_CLASSES)

        def down(m):
            return m.reshape(SH // cpx, cpx, SW // cpx, cpx).mean(axis=(1, 3)).astype(np.float32)

        frac["reach"][ys, xs] = down(reached)
        frac["obj"][ys, xs] = down(obj)
        frac["water"][ys, xs] = down(water)
        frac["water_reached"][ys, xs] = down(is_water_tile & reached & ~fill_water)
        for k in ROCK_CLASSES:
            frac["rock_" + k][ys, xs] = down(rocks[k])
        frac["canopy"][ys, xs] = down(canopy)
        frac["chasm"][ys, xs] = down(chasm)
        frac["hill"][ys, xs] = down(hill)
        frac["path"][ys, xs] = down(path)
        frac["facade"][ys, xs] = down(facade)
        valid[ys, xs] = True
        stats["screens"] += 1
    log(f"landforms: {stats['screens']} outdoor screens rasterised ({W} x {H} cells of {cpx} px), "
        f"{stats['unmatched_components']} reached components matched loosely")

    mpc = mpp * cpx                                   # metres per cell
    land_support = (frac["reach"] + frac["obj"]) >= 0.5
    walk = frac["reach"] >= 0.5
    # --- land undulation (map-pixel space: continuous over every shared edge)
    wave = LAND_WAVE_PX / cpx
    n1 = value_noise((H, W), wave, 1997)
    n2 = value_noise((H, W), wave * 0.37, 2026)
    n3 = value_noise((H, W), wave * 0.6, 15)
    land = LAND_BASE_M + LAND_AMP_M * (0.72 * n1 + 0.28 * n2)
    land -= PATH_WEAR_M * np.clip(gauss(frac["path"], 2.0) * 1.6, 0.0, 1.0)
    # --- shoreline: signed distance (cells, + land, - water) to the 1997 water outline, steps rounded off
    water = frac["water"] >= 0.5
    water_any = water | (frac["water_reached"] >= 0.5)
    lim = 80
    d_out = distance(water_any, lim)
    d_in = distance(~water_any, lim)
    sd = np.where(water_any, -(d_in - 0.5), d_out - 0.5).astype(np.float32)
    sd_s = gauss(sd, SHORE_BLUR_PX / cpx)
    dev = SHORE_DEVIATION_PX / cpx
    sd_s = np.clip(sd_s, sd - dev, sd + dev)
    s_1997 = sd_s * mpc
    # the drawn waterline (#150) where the masks measure it; the 1997 shoreline beyond, joined by a fading correction
    s_draw, n_masks = drawn_shore(screens, bundle, H, W, cpx)
    band = np.isfinite(s_draw) & valid
    corr = fade_out(np.where(band, s_draw - s_1997, 0.0), band, np.exp(-mpc / DRAWN_FADE_M), 40)
    s_m = np.where(band, s_draw, s_1997 + corr).astype(np.float32)
    drawn_water = valid & (s_m < 0)
    stats["drawn_masks"] = n_masks
    stats["drawn_band_cells"] = int(band.sum())
    log(f"landforms: drawn waterline from {n_masks} ground masks ({int(band.sum())} cells in the measured band)")
    bank = np.where(s_m > 0, 1.0 - np.exp(-np.maximum(s_m, 0) / BANK_M), 0.0)
    depth = BED_DEPTH_M + (SEA_BED_DEPTH_M - BED_DEPTH_M) * sea
    # a shallow shelf first (the shore water's clear-to-deep colour runs over the first two metres of the mask, and the
    # single-layer water darkens with real depth), then the bed falls away
    t = np.clip((np.maximum(-s_m, 0) - BED_SHELF_M) / BED_WIDTH_M, 0.0, 1.0)
    bed = -(BED_SHELF_DEPTH_M * np.clip(np.maximum(-s_m, 0) / 0.5, 0.0, 1.0) + depth * t * t * (3.0 - 2.0 * t))
    # --- rises of the ground nobody reaches
    d_walk = distance(land_support | water_any, 160) * mpc        # metres to reachable ground (or water's edge)
    rise = np.zeros((H, W), np.float32)
    for k in ROCK_CLASSES:
        amp, width = RISE[k]
        f = gauss(frac["rock_" + k], 1.0)
        rise = np.maximum(rise, f * amp * (0.75 + 0.5 * n3) * (1.0 - np.exp(-d_walk / width)))
    for k in ("canopy", "hill"):
        amp, width = RISE[k]
        f = gauss(frac[k], 1.0)
        rise = np.maximum(rise, f * amp * (0.6 + 0.8 * n3) * (1.0 - np.exp(-d_walk / width)))
    rise = gauss(rise, RISE_BLUR_CELLS)            # the 1997 outlines scallop; a hillside does not
    rock_any = sum(frac["rock_" + k] for k in ROCK_CLASSES)
    d_rock = distance(rock_any >= 0.5, 40) * mpc
    land = land + FOOTHILL_M * np.exp(-d_rock / 3.0) * (1.0 - walk * 0.3)
    chasm_drop = gauss(frac["chasm"], 1.0) * CHASM_DEPTH_M * (1.0 - np.exp(-d_walk / 1.2))
    # --- compose
    # walkable 1997 land under the drawn water (its shallow edge, bridge decks) is not a bed: bank 0 there, i.e. 0
    bed_here = drawn_water & ~(walk & ~(frac["water_reached"] >= 0.5))
    h = np.where(bed_here, bed, land * bank)
    h = h + rise - chasm_drop
    # --- the play camera: under the line from the camera to Dink within the boom's reach of any walkable point
    d_cam = distance(walk, 200) * mpc
    cap = np.where(d_cam <= CAMERA_REACH_M, CAMERA_BASE_M + CAMERA_SLOPE * d_cam,
                   CAMERA_BASE_M + CAMERA_SLOPE * CAMERA_REACH_M + CAMERA_OPEN_SLOPE * (d_cam - CAMERA_REACH_M))
    h = np.where(h > land, smin(h, land + cap, SOFT_MIN_M), h)
    # --- flat things (interiors, settlements, authored screens, building facades) with a smooth falloff
    flat = flat_src | (frac["facade"] >= 0.5)
    d_flat = distance(flat, 200) * mpc
    f = 1.0 - np.clip(d_flat / FLAT_FALLOFF_M, 0.0, 1.0)
    f = f * f * (3.0 - 2.0 * f)
    h = (1.0 - f) * h + f * np.minimum(bed * drawn_water, 0.0)
    # --- final smoothing, then the hard rules on reachable ground
    h = gauss(h, FINAL_BLUR_CELLS)
    # --- buildings (#184 structure sets, town houses) stand on level ground: each footprint (plus PAD_M) at its mean
    # height, blending back over PAD_FALLOFF_M (a house is one mesh at one height; a slope under it would bury a corner)
    pads = building_pads(project, screens, H, W, cpx)
    used = 0
    for m in pads:
        dry = m & ~drawn_water & ~(frac["water_reached"] >= 0.5)
        wet = dry.sum() < 0.7 * m.sum()
        # a bridge or a jetty over water: its walkable deck at 0 (the bridge mesh's level), the water keeps its bed
        level = 0.0 if wet else float(h[dry].mean())
        used += 1
        yy, xx = np.nonzero(m)
        g = 40
        ys = slice(max(0, yy.min() - g), min(H, yy.max() + g + 1))
        xs = slice(max(0, xx.min() - g), min(W, xx.max() + g + 1))
        d = distance(m[ys, xs], g) * mpc[ys, xs]
        t = 1.0 - np.clip(d / PAD_FALLOFF_M, 0.0, 1.0)
        t = t * t * (3.0 - 2.0 * t)
        blend = ((1.0 - t) * h[ys, xs] + t * level).astype(np.float32)
        # never over the walkable 1997 water (fords): it keeps its wading depth below
        keep = (frac["water_reached"][ys, xs] >= 0.5) | (~walk[ys, xs] if wet else False)
        h[ys, xs] = np.where(keep, h[ys, xs], blend)
    stats["building_pads"] = used
    land_cap = (1.0 - f) * land * bank + WALK_RISE_MAX_M
    # water the 1997 hardness lets Dink walk (fords, shallows): he wades in it, shallow at its edges and at most WADE_DEPTH_M
    # deep; the rest of the walkable ground stays at or above 0 (the importer's flat floor). Deep, blocked water keeps its bed.
    wade_water = frac["water_reached"] >= 0.5
    d_wade = distance(~wade_water, 40) * mpc
    wade = -WADE_DEPTH_M * (1.0 - np.exp(-np.maximum(d_wade - 0.5 * mpc, 0) / WADE_WIDTH_M))
    wade = gauss(np.where(wade_water, wade, 0.0), 1.0)
    floor = np.where(wade < -0.005, np.maximum(wade, -WADE_DEPTH_M), 0.0)
    h = np.where(walk, np.clip(h, floor, np.maximum(land_cap, floor)), h)
    h = np.where(walk & wade_water, np.minimum(h, floor), h)
    h = np.where(valid, h, 0.0).astype(np.float32)
    return {"h": h, "valid": valid, "walk": walk, "water": water_any | drawn_water, "drawn_water": drawn_water, "s_m": s_m, "mpp": mpp, "flat_of": flat_of, "screens": screens,
            "by_num": by_num, "W": W, "H": H, "stats": stats, "rise": rise, "frac": frac}


def vertex_grid(h: np.ndarray, col: int, row: int) -> np.ndarray:
    """Heights (m) at map pixels (i * GRID_PX, j * GRID_PX) of one screen, bilinear on the cell centres."""
    cpx = CELL_PX
    gx = (col * SW + np.arange(GW) * GRID_PX) / cpx - 0.5
    gy = (row * SH + np.arange(GH) * GRID_PX) / cpx - 0.5
    gx = np.clip(gx, 0, h.shape[1] - 1.001)
    gy = np.clip(gy, 0, h.shape[0] - 1.001)
    x0 = np.floor(gx).astype(int); y0 = np.floor(gy).astype(int)
    fx = (gx - x0)[None, :]; fy = (gy - y0)[:, None]
    a = h[np.ix_(y0, x0)]; b = h[np.ix_(y0, x0 + 1)]; c = h[np.ix_(y0 + 1, x0)]; d = h[np.ix_(y0 + 1, x0 + 1)]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def checks(res, grids: dict) -> dict:
    """Walkable slope, camera line of sight on a sample of walkable points, seam continuity."""
    h, walk, mpp = res["h"], res["walk"], res["mpp"]
    mpc = mpp * CELL_PX
    # slope between neighbouring walkable cells only (a walkable cell beside a cliff is not on the cliff)
    sl = []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        b = np.roll(h, (-dy, -dx), axis=(0, 1))
        wb = np.roll(walk, (-dy, -dx), axis=(0, 1))
        ok = walk & wb
        if dy:
            ok[-dy:, :] = False
        if dx > 0:
            ok[:, -dx:] = False
        if dx < 0:
            ok[:, :-dx] = False
        sl.append((np.abs(b - h) / (mpc * math.hypot(dx, dy)))[ok])
    ws = np.concatenate(sl) if sl else np.zeros(0)
    out = {"walk_slope_max_deg": float(np.degrees(np.arctan(ws.max()))) if ws.size else 0.0,
           "walk_slope_p99_deg": float(np.degrees(np.arctan(np.percentile(ws, 99)))) if ws.size else 0.0,
           "walk_slope_p999_deg": float(np.degrees(np.arctan(np.percentile(ws, 99.9)))) if ws.size else 0.0,
           "walk_cells_over_20deg": int((ws > math.tan(math.radians(20))).sum()),
           "walk_height_min_m": float(h[walk].min()) if walk.any() else 0.0, "walk_height_max_m": float(h[walk].max()) if walk.any() else 0.0}
    # camera: boom 400 cm at pitch -12 from the pivot 96 cm above the feet, 16 yaws, every 6th walkable cell;
    # a ray is blocked when the ground anywhere along it comes within the boom's probe (12 cm) of the line
    ys, xs = np.nonzero(walk)
    sel = np.arange(0, len(ys), 6)
    ys, xs = ys[sel], xs[sel]
    blocked = 0
    worst = {}
    pitch = math.radians(12.0)
    for k in range(16):
        a = 2 * math.pi * k / 16
        ray = np.zeros(len(ys), bool)
        for t in np.linspace(0.1, 1.0, 12):
            dist_m = 4.0 * math.cos(pitch) * t
            line = h[ys, xs] + 0.96 + 4.0 * math.sin(pitch) * t
            step = dist_m / mpc[ys, xs]
            sx = np.clip(np.round(xs + math.cos(a) * step).astype(int), 0, h.shape[1] - 1)
            sy = np.clip(np.round(ys + math.sin(a) * step).astype(int), 0, h.shape[0] - 1)
            ray |= h[sy, sx] > line - 0.12
        blocked += int(ray.sum())
        for yy, xx in zip(ys[ray], xs[ray]):
            scr = (yy * CELL_PX // SH) * COLS + (xx * CELL_PX // SW) + 1
            worst[scr] = worst.get(scr, 0) + 1
    out["camera_rays"] = int(len(ys) * 16)
    out["camera_rays_blocked"] = blocked
    out["camera_blocked_rays_by_screen"] = dict(sorted(worst.items(), key=lambda kv: -kv[1])[:15])
    # seams: shared edge values of grid neighbours must be equal (they are sampled from one raster)
    worst_seam = 0.0
    for n, g in grids.items():
        c, r = (n - 1) % COLS, (n - 1) // COLS
        e = grids.get(n + 1) if c + 1 < COLS else None
        if e is not None:
            worst_seam = max(worst_seam, float(np.abs(g[:, -1] - e[:, 0]).max()))
        s = grids.get(n + COLS)
        if s is not None:
            worst_seam = max(worst_seam, float(np.abs(g[-1, :] - s[0, :]).max()))
    out["seam_max_mm"] = round(worst_seam * 1000.0, 3)
    return out


def write(res, out_dir: Path, only=None, log=print):
    h = res["h"]
    grids, rows = {}, []
    for s in res["screens"]:
        n = s["screen"]
        if s.get("excluded") or s["indoor"] or s["sheet"].startswith("interior:"):
            continue
        if only is not None and n not in only:
            continue
        g = vertex_grid(h, s["col"], s["row"])
        if np.abs(g).max() < 0.005:
            continue
        grids[n] = g
    names = sorted(grids)
    per_row = 16
    atlas_w = per_row * GW
    atlas_h = max(1, (len(names) + per_row - 1) // per_row) * GH
    atlas = np.full((atlas_h, atlas_w), 32768, np.uint16)
    for i, n in enumerate(names):
        ax, ay = (i % per_row) * GW, (i // per_row) * GH
        mm = np.clip(np.round(grids[n] * 1000.0), -32000, 32000).astype(np.int32)
        atlas[ay:ay + GH, ax:ax + GW] = (mm + 32768).astype(np.uint16)
        s = res["by_num"][n]
        c = s["corners"]
        c0, r0 = s["col"], s["row"]
        cells = (slice(r0 * SH // CELL_PX, (r0 + 1) * SH // CELL_PX), slice(c0 * SW // CELL_PX, (c0 + 1) * SW // CELL_PX))
        wade = bool((res["walk"][cells] & (h[cells] < -0.01)).any())
        rows.append({"screen": n, "atlas": [ax, ay], "min_mm": int(mm.min()), "max_mm": int(mm.max()), "wade": wade,
                     "flat": res["flat_of"].get(n, ""), "corners": [c["nw"], c["ne"], c["sw"], c["se"]]})
    buf = io.BytesIO()
    Image.fromarray(atlas).save(buf, format="PNG", optimize=False, compress_level=9)
    png = buf.getvalue()
    header = {
        "schema": SCHEMA,
        "note": "World heightfield of the landforms pass (Scripts/export_landforms.py; UDinkLandformsSubsystem). Per screen a "
                f"{GW} x {GH} vertex grid at {GRID_PX} map px, 16-bit atlas landforms.png (mm + 32768). Presentation and the "
                "player's own footing only: the 1997 hardness, NPCs, creatures and missiles are unchanged. dink.Landforms 0 turns it off.",
        "grid_px": GRID_PX, "grid": [GW, GH], "atlas": "landforms.png", "atlas_size": [atlas_w, atlas_h],
        "atlas_sha1": hashlib.sha1(png).hexdigest(),
        "params": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))},
        "screens": rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "landforms.png").write_bytes(png)
    (out_dir / "landforms.json").write_text(json.dumps(header, indent=1) + "\n", encoding="utf-8")
    log(f"landforms: wrote {len(rows)} screens, atlas {atlas_w} x {atlas_h} ({len(png) // 1024} KB) to {out_dir}")
    return grids


def preview(res, out: Path, log=print):
    """Overview images: hillshade of the whole map and a height colour map."""
    out.mkdir(parents=True, exist_ok=True)
    h, mpc = res["h"], res["mpp"] * CELL_PX
    gy, gx = np.gradient(h)
    gx, gy = gx / mpc, gy / mpc
    az, alt = math.radians(315), math.radians(40)
    shade = np.clip(math.sin(alt) + math.cos(alt) * (gx * -math.sin(az) - gy * -math.cos(az)) / np.sqrt(1 + gx * gx + gy * gy) * 1.0, 0, 1)
    shade = np.clip((math.sin(alt) * 1.0 - (gx * math.cos(az) + gy * math.sin(az)) * math.cos(alt)) / np.sqrt(1 + gx * gx + gy * gy), 0, 1)
    # colour: water blue, land green-brown by height, rock grey
    t = np.clip(h / 4.0, -1, 1)
    r = np.where(t < 0, 0.15 + 0.1 * (1 + t), 0.35 + 0.5 * t)
    g = np.where(t < 0, 0.30 + 0.2 * (1 + t), 0.45 + 0.25 * t)
    b = np.where(t < 0, 0.55 + 0.3 * (1 + t), 0.25 + 0.55 * t)
    rgb = np.dstack([r, g, b]) * (0.35 + 0.65 * shade[..., None])
    rgb = np.where(res["valid"][..., None], rgb, 0.08)
    img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB")
    img.save(out / "landforms_overview.png")
    img.resize((img.width // 2, img.height // 2), Image.BOX).save(out / "landforms_overview_half.png")
    log(f"landforms: previews in {out}")


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", default=str(default_data_repo(here)), help="data repo root (tools/*/out)")
    ap.add_argument("--bundle", default=str(here / "ImportData"), help="the world export (screens.json, collision.json)")
    ap.add_argument("--out", default=str(here / "Content/Dink/Data/Environment"))
    ap.add_argument("--screens", default="all", help="screens to write (all, or N,N-M,...): the rest stay flat")
    ap.add_argument("--preview", default="", help="write overview images here")
    ap.add_argument("--check", action="store_true", help="print the slope, camera and seam checks as JSON")
    args = ap.parse_args(argv)
    only = parse_screens(args.screens)
    res = build(Path(args.data).resolve(), Path(args.bundle).resolve(), here, only)
    grids = write(res, Path(args.out).resolve(), only)
    if args.preview:
        preview(res, Path(args.preview))
    if args.check:
        print(json.dumps(checks(res, grids), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
