#!/usr/bin/env python3
"""Do the player-only blockers cut anything off? (alpha QA, 14 Nov 2026)

    python3 Scripts/check_player_blockers.py <audit dir>

Reads walk_blockers.csv of a `dink.WalkAudit` run made with the blockers on (one map-pixel polygon per blocker) and its
walk_mask.csv (where the capsule centre may stand on the game's collision with the blockers ignored; without it, each
screen's 1997 hardness, Content/Dink/Data/Gameplay/Hardness/SCR_nnn.txt vision 0, shrunk by the capsule). Per screen: that
walkable ground split into connected areas; then each area again with every blocker
polygon (grown by the capsule radius) taken out. An area that the blockers split leaves pieces that can no longer be
reached from its largest piece nor from the screen's edges (the next screen). A piece that holds (within reach) a placement with a script, a brain or a warp
(placements.csv) fails the check (exit 1); other pieces (house interiors, niches) are listed as pockets. Stdlib + numpy.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HARD = ROOT / "Content/Dink/Data/Gameplay/Hardness"
PLACEMENTS = ROOT / "Content/Dink/Data/Gameplay/placements.csv"
REACH_PX = 12  # a talk, touch or pick-up reaches this far past the capsule
CAPSULE_CM = 28.0


def load_hardness(screen: int) -> np.ndarray | None:
    f = HARD / f"SCR_{screen:03d}.txt"
    if not f.exists():
        return None
    rows, started = [], False
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("vision"):
            if started:
                break
            started = line.split()[1] == "0"
            continue
        if line.startswith("tiles"):
            break
        if not started:
            continue
        row = []
        for t in line.split():
            if ":" in t:
                n, c = t.split(":")
                row += [int(c)] * int(n)
            else:
                row += [0] * int(t)
        rows.append(row)
    return np.array(rows[:400], dtype=np.int32) if len(rows) >= 400 else None


def load_masks(audit: Path) -> dict[int, np.ndarray]:
    """walk_mask.csv (dink.WalkAudit): per screen, where the capsule centre may stand without the blockers, expanded to pixels."""
    out = {}
    for f in sorted(audit.glob("**/walk_mask.csv")):
        for line in f.read_text().splitlines():
            parts = line.split(",")
            if len(parts) != 3 or not parts[2] or not parts[0].isdigit():  # the header, or an empty mask
                continue
            screen, step = int(parts[0]), int(parts[1])
            cells, num = [], ""
            for ch in parts[2]:
                if ch.isdigit():
                    num += ch
                else:
                    cells += [ch == "F"] * int(num)
                    num = ""
            w, h = (600 + step - 1) // step, (400 + step - 1) // step
            if len(cells) != w * h:
                continue
            grid = np.array(cells, dtype=bool).reshape(h, w)
            out[screen] = np.repeat(np.repeat(grid, step, axis=0), step, axis=1)[:400, :600]
    return out


def interest_points() -> dict[int, list[tuple[int, int, str]]]:
    """Placements the player must reach: anything with a script, a brain or a warp (map pixels: engine x - 20)."""
    out: dict[int, list] = {}
    with PLACEMENTS.open() as f:
        for r in csv.DictReader(f):
            if r["script"] or r["brain"] not in ("", "0") or r["warp_map"] not in ("", "0"):
                out.setdefault(int(r["screen"]), []).append((int(r["x"]) - 20, int(r["y"]), r["origin"]))
    return out


def flood(mask: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    """4-connected flood fill of mask from seeds (both boolean 400x600)."""
    out = seeds & mask
    while True:
        grown = out.copy()
        grown[1:, :] |= out[:-1, :]
        grown[:-1, :] |= out[1:, :]
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        grown &= mask
        if (grown == out).all():
            return out
        out = grown


def label(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """4-connected components by row runs and union-find; returns (labels 1..n, n)."""
    parent: list[int] = []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    runs_prev: list[tuple[int, int, int]] = []
    all_runs = []
    for y in range(mask.shape[0]):
        row = mask[y]
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        runs = []
        j = 0
        for a, b in zip(starts.tolist(), ends.tolist()):
            rid = len(parent)
            parent.append(rid)
            while j < len(runs_prev) and runs_prev[j][1] <= a:
                j += 1
            k = j
            while k < len(runs_prev) and runs_prev[k][0] < b:
                ra, rb = find(rid), find(runs_prev[k][2])
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
                k += 1
            runs.append((a, b, rid))
            all_runs.append((y, a, b, rid))
        runs_prev = runs
    out = np.zeros(mask.shape, dtype=np.int32)
    ids: dict[int, int] = {}
    for y, a, b, rid in all_runs:
        root = find(rid)
        out[y, a:b] = ids.setdefault(root, len(ids) + 1)
    return out, len(ids)


def disc_erode(mask: np.ndarray, r: int) -> np.ndarray:
    """Pixels whose disc of radius r is all inside mask."""
    if r <= 0:
        return mask.copy()
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            shifted = np.zeros_like(mask)
            ys = slice(max(0, dy), mask.shape[0] + min(0, dy))
            yd = slice(max(0, -dy), mask.shape[0] + min(0, -dy))
            xs = slice(max(0, dx), mask.shape[1] + min(0, dx))
            xd = slice(max(0, -dx), mask.shape[1] + min(0, -dx))
            shifted[yd, xd] = mask[ys, xs]
            out &= shifted
    return out


def polygon_mask(poly: list[tuple[float, float]], grow: float) -> np.ndarray:
    """Pixels inside a convex polygon grown by `grow` pixels (distance to the polygon <= grow)."""
    yy, xx = np.mgrid[0:400, 0:600]
    px, py = xx + 0.5, yy + 0.5
    n = len(poly)
    inside = np.ones((400, 600), dtype=bool)
    sign = 1.0 if sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)) > 0 else -1.0
    dist = np.full((400, 600), np.inf)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        inside &= sign * ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) >= 0
        ex, ey = bx - ax, by - ay
        L = ex * ex + ey * ey or 1e-9
        t = np.clip(((px - ax) * ex + (py - ay) * ey) / L, 0, 1)
        dist = np.minimum(dist, np.hypot(px - (ax + t * ex), py - (ay + t * ey)))
    return inside | (dist <= grow)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audit", type=Path)
    ap.add_argument("--cm-per-px", type=float, default=0.0, help="override; default: measured per screen from walk_audit.csv")
    a = ap.parse_args(argv)
    blockers: dict[int, list] = {}
    for f in sorted(a.audit.glob("**/walk_blockers.csv")):
        for r in csv.DictReader(f.open()):
            if r["enabled"] != "1" or not r["polygon_px"]:
                continue
            blockers.setdefault(int(r["screen"]), []).append(
                (r["mesh"].rsplit(".", 1)[-1], [tuple(float(v) for v in p.split(":")) for p in r["polygon_px"].split(";")]))
    # cm per map pixel per screen, from the audit's centre positions (x in cm against x in px)
    scale: dict[int, float] = {}
    pts: dict[int, list] = {}
    for f in sorted(a.audit.glob("**/walk_audit.csv")):
        for r in csv.DictReader(f.open()):
            pts.setdefault(int(r["screen"]), []).append((float(r["centre_px_x"]), float(r["centre_x"])))
    for s, p in pts.items():
        p = sorted(p)
        if len(p) >= 2 and p[-1][0] - p[0][0] > 20:
            scale[s] = abs((p[-1][1] - p[0][1]) / (p[-1][0] - p[0][0]))
    masks = load_masks(a.audit)
    points = interest_points()
    failed, total = 0, 0
    for s in sorted(blockers):
        h = load_hardness(s)
        if h is None:
            continue
        total += 1
        cm = a.cm_per_px or scale.get(s, 5.0)
        r = max(1, int(round(CAPSULE_CM / cm)))
        walk = h == 0
        # the game's own walker collision when the audit measured it (voids the importer closes are not walkable),
        # else the 1997 hardness shrunk by the capsule
        centre_ok = masks[s] if s in masks else disc_erode(walk, r)
        under = np.zeros_like(walk)
        for _, poly in blockers[s]:
            under |= polygon_mask(poly, r)
        lost = np.zeros_like(walk)
        main = np.zeros_like(walk)
        areas, n_areas = label(centre_ok)
        pieces, _ = label(centre_ok & ~under)
        for k in range(1, n_areas + 1):
            ids, counts = np.unique(pieces[areas == k], return_counts=True)
            keep = [(c, i) for i, c in zip(ids.tolist(), counts.tolist()) if i != 0]
            if not keep:
                continue
            keep.sort(reverse=True)
            main |= pieces == keep[0][1]
            for _, i in keep[1:]:
                piece = pieces == i
                # a piece on the screen's edge is still entered from the next screen
                if piece[0, :].any() or piece[-1, :].any() or piece[:, 0].any() or piece[:, -1].any():
                    main |= piece
                else:
                    lost |= piece

        def near(mask, x, y):
            return mask[max(0, y - REACH_PX - r):y + REACH_PX + r + 1, max(0, x - REACH_PX - r):x + REACH_PX + r + 1].any()

        # A cut-off piece matters only if something the player must reach can be reached from it and no longer from the
        # main piece of its area (a door on a house front is still reached from the street when the house behind it is closed).
        cut = []
        if lost.any():
            pockets, n_pockets = label(lost)
            for k in range(1, n_pockets + 1):
                piece = pockets == k
                ys, xs = np.nonzero(piece)
                orphans = [o for x, y, o in points.get(s, []) if 0 <= x < 600 and 0 <= y < 400 and near(piece, x, y) and not near(main, x, y)]
                if orphans:
                    cut.append((int(piece.sum()), int(xs.mean()), int(ys.mean()), orphans))
        n = int(lost.sum())
        if cut:
            failed += 1
            for size, x, y, orphans in cut:
                print(f"SCR_{s:03d} CUT OFF: {size} px around px {x},{y}; only from there: {', '.join(orphans)}; {len(blockers[s])} blockers ({cm:.1f} cm/px)")
        elif n:
            print(f"SCR_{s:03d} pockets only: {n} px with nothing to reach (house interiors, niches)")
    print(f"{total} screens with blockers checked, {failed} cut off something the player must reach")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
