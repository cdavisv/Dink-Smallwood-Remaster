#!/usr/bin/env python3
"""Offline assembler of structures that the 1997 game draws in several sprites: python3 -I Scripts/assemble_structures.py

Reads ImportData/placements.json and tools/dinkex/out/sequences.json (frame hotspots and hardboxes) and writes
Content/Dink/Data/Art/structure_sets.json in the schema of town_houses.json (dink-town-houses/3), which
UDinkEnvironmentSubsystem shows instead of the sprite cards (dink.TownHouses 0 keeps the cards). Visual only:
hardness, warps, scripts and origin IDs are untouched; a hidden card keeps its actor, its hardbox and its script.

Why not family rows: a family mesh stands at real size under the middle of its card. The remaster lays the outdoor
screens out at 2.75 to 4 times the sprite scale, so a fence sprite is 18 m of ground and a 4.4 m fence module in the
middle of it leaves gaps; a bridge deck would be a third as wide as the ground the player walks on. Here every
piece is laid along the ground line its sprite stands on and scaled along that line to close the run.

What is assembled (each rule names the sprite frames it reads):
  split-rail fence   93 lands/fence/fence-: frame 1 an east-west run, 4 a north-south run seen edge-on, 2 and 5 runs that
                     rise to the right, 3 and 6 runs that fall to the right. The ground line is the frame's hardbox (its
                     middle line, or its diagonal). SM_Fence_SplitRail_4m_PR every 4 m, scaled along the run.
  island fence       424 struct/island/isle- frames 7 (east-west) and 8 (north-south): SM_Island_Fence_Lattice_PR every 4.4 m.
  wooden bridge      58 struct/bridge/brdge-: frames 1-3 are deck pieces of a north-south bridge (the picture is the deck);
                     frames 6, 8, 10 are the far rail of an east-west bridge with the deck boards drawn under it and
                     7, 9, 11 its near rail. Deck modules fill the picture (north-south) or the ground between the
                     two rail lines (east-west); a rope rail stands on each rail line (the far side boarded).
  well               186 struct/landmark/landm- frames 1-3: SM_Well_Stone_PR with SM_Well_ShaftCap_PR (the shaft goes
                     below the ground, which is not cut: the cap closes it with an unlit black disc).
  thatched cottage   63 struct/home: frames 1 (long), 6 (large), 7 and 8 (small), 4 and 5 (two-storey), 10 (L-shaped). The
                     sprite is a house turned 45 degrees; its hardbox is an east-west rectangle. The house stands at real
                     size, square to the screen, its front (south) wall on the hardbox's south line. The door stands on
                     that wall where the warp door sprite (61, 62) or the door picture (63 frames 2, 3) is; the house
                     moves east or west so the door is on its wall. The warp trigger stays where it was, a few metres in
                     front of the wall. Door, chimney and window pictures on such a screen are hidden: the meshes carry
                     their own chimneys and windows.
  island hut         424 struct/island/isle- frames 1-3 (round) and 4-6 (two tiers): the hut at 1.25 x on the middle of its
                     picture, turned so that the doorway looks where the sprite's does (frames differ only in that).

Left to the family rows or to their cards: everything else. Screens and origins that an art manifest dresses
(Content/Dink/Data/Art, schema dink-art/1) are skipped, as the family layer skips them.

The JSON lists per screen `houses` (one per run or structure: id, kind, note, the placements it stands for in `hide`,
and `modules`: mesh package path, px = map pixel of the piece's middle, offset_cm, yaw in Unreal degrees, scale) and
`footprints` (the grass carpet stays out of bridge decks)."""
import collections
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
S = '/Game/Dink/Photoreal/Structures/'
FENCE, LATTICE = S + 'SM_Fence_SplitRail_4m_PR', S + 'SM_Island_Fence_Lattice_PR'
DECK, RAIL_ROPE, RAIL_PLANK = S + 'SM_Bridge_Wood_Deck_PR', S + 'SM_Bridge_Wood_Rail_Rope_PR', S + 'SM_Bridge_Wood_Rail_Plank_PR'
WELL, WELL_CAP = S + 'SM_Well_Stone_PR', S + 'SM_Well_ShaftCap_PR'
COTTAGE_DOOR = S + 'SM_Cottage_Door_PR'            # hinge pivot at x = 0, leaf 1.44 m along +X, face to the south
HUT_ROUND, HUT_TWO, HUT_SCALE = S + 'SM_Island_Hut_Round_PR', S + 'SM_Island_Hut_TwoStorey_PR', 1.25
# The two-storey house (63 frames 4, 5): the Stonebrook440 kit's house (SourceAssets/Art/Stonebrook440, imported to /Game/Dink/Kits/Stonebrook440 by
# Scripts/import_stonebrook440.sh). Chosen by eye over SM_Cottage_Thatched_TwoStorey_PR (queue row DS-03, 15 Nov 2026): rounded thatch with a rolled
# eave over drystone rubble, as the 1997 picture; lower walls 11.0 x 8.5 m (eaves 13.3 x 10.8 m), its double door modelled in the south wall 1.73 m
# west of the middle (no separate door leaf).
K440 = '/Game/Dink/Kits/Stonebrook440/'
HOUSE_440 = K440 + 'SM_House_Stonebrook_TwoStorey_01'
MODELLED_DOOR = {HOUSE_440}
TURNED = set()      # filled below: meshes that may be turned off the screen axes
# The yard of screen 440 (the 1997 screen shows a pitchfork, a scythe, an axe, tongs and a hatchet beside the house: the first two are family rows).
# Rows: (mesh, metres east / south of the house middle or None for a map pixel, map pixel or None, yaw, z cm, origins it stands for).
# Pieces that read as solid stand on the closed ground of the house's hardness outline (structure_walk_check.py); the three hand tools lie flat.
YARD_440 = [('SM_Woodpile_Split_01', (5.5 + 0.30, -1.6), None, 90.0, 0.0, []), ('SM_WaterTrough_Oak_01', (-5.5 - 0.45, 1.2), None, 90.0, 0.0, []),
            ('SM_ChoppingBlock_Axe_01', (5.5 + 1.9, 3.0), None, 160.0, 0.0, []), ('SM_Wheelbarrow_Oak_01', (5.5 + 2.6, 0.2), None, 205.0, 0.0, []),
            ('SM_HayBale_01', (5.5 + 1.2, -3.4), None, 12.0, 0.0, []), ('SM_HayBale_01', (5.5 + 1.25, -3.35), None, 96.0, 36.0, []), ('SM_HayBale_01', (5.5 + 2.5, -2.9), None, -24.0, 0.0, []),
            ('SM_Axe_Felling_01', None, 'S440_P23', 205.0, 0.0, ['S440_P23']), ('SM_Tongs_Iron_01', None, 'S440_P24', 40.0, 0.0, ['S440_P24']), ('SM_Hatchet_01', None, 'S440_P25', 120.0, 0.0, ['S440_P25'])]
# class -> (mesh, wall width east-west, wall depth, x of the doorway cut in the front wall or None when the wall is whole); metres
U = '/Game/Dink/Photoreal/Unclaimed/'
CABIN, CABIN_DOOR, CABIN_WINDOW = U + 'SM_Log_Cabin_PR', U + 'SM_Door_Cabin_PR', U + 'SM_Cabin_Window_PR'     # door opening x -1.9..-0.9, window x 1.2..2.2, z 0.95..1.75
# The church of screens 187 / 188 (60 frame 1): SM_Church_PR, nave walls about 21 x 8.4 m (22.3 x 10.6 m over the buttresses), which is the size of
# its 1997 hardbox; the door opening (1.6 m wide, 3.1 m to the crown) is in the south wall 8 m west of the middle. Off until imported and seen (--church).
CHURCH, CHURCH_DOOR = U + 'SM_Church_PR', U + 'SM_Door_Church_PR'
TURNED.update((CABIN, CHURCH))
COTTAGE = {'log_cabin': (CABIN, 7.6, 4.5, -1.4), 'church': (CHURCH, 21.0, 8.4, -8.0),
           'cottage_thatched_small': (S + 'SM_Cottage_Thatched_Small_PR', 7.0, 5.5, None), 'cottage_thatched_large': (S + 'SM_Cottage_Thatched_Large_PR', 10.0, 6.5, None),
           'cottage_thatched_long': (S + 'SM_Cottage_Stonebrook_PR', 18.0, 9.0, 5.3), 'cottage_thatched_two_storey': (HOUSE_440, 11.0, 8.5, -1.73),
           'cottage_thatched_l_shape': (S + 'SM_Cottage_Thatched_LShape_PR', 9.3, 6.0, None)}
FENCE_PITCH, LATTICE_PITCH, DECK_LEN, DECK_WIDTH, RAIL_LEN = 4.0, 4.4, 2.5, 1.76, 2.5   # metres of run per module / deck width
SNAP_PX = 16.0    # fence ends closer than this (map pixels) are one corner

placements = json.load(open(os.path.join(ROOT, 'ImportData/placements.json')))['placements']
sys.path.insert(0, os.path.join(ROOT, 'Scripts'))
from export_import_bundle import label_components    # noqa: E402
COLLISION = json.load(open(os.path.join(ROOT, 'ImportData/collision.json')))['screens']
BLOCKING = ('solid', 'low', 'sprite', 'warp', 'fill_water', 'fill_solid')
GATE, GATE_POST = S + 'SM_Fence_Gate_PR', S + 'SM_Fence_GatePost_PR'
_BLOCKED = {}


def blocked3(screen):
    """bool (1200, 1800): the 1997 hardness of the screen and its eight neighbours (the screen is the middle; a screen that
    does not exist is closed). What stops the player; a warp rectangle counts, it takes the player away."""
    if screen not in _BLOCKED:
        big = np.ones((1200, 1800), bool)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                c, r = (screen - 1) % 32 + dc, (screen - 1) // 32 + dr
                row = COLLISION.get('SCR_%03d' % (r * 32 + c + 1)) if 0 <= c < 32 and 0 <= r < 24 else None
                if row is None:
                    continue
                m = np.zeros((400, 600), bool)
                for k in BLOCKING:
                    for x0, y0, x1, y1 in row.get(k) or []:
                        m[max(0, y0):y1, max(0, x0):x1] = True
                big[(dr + 1) * 400:(dr + 2) * 400, (dc + 1) * 600:(dc + 2) * 600] = m
        _BLOCKED[screen] = big
    return _BLOCKED[screen]


def closed_ground(screen, x, y):
    """The closed ground around map pixel (x, y): the hardness outline the 1997 map draws round a building together with the
    ground inside it, which has hardness 0 but cannot be walked to. bool (1200, 1800) in the block of blocked3, or None."""
    big = blocked3(screen)
    lab, _ = label_components(~big)
    rim = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
    closed = ~np.isin(lab, sorted(rim)) if rim else np.ones_like(big)
    lab2, _ = label_components(closed)
    v = lab2[int(round(y)) + 400, int(round(x)) + 600] if 0 <= y + 400 < 1200 and 0 <= x + 600 < 1800 else 0
    return (lab2 == v) if v else None


_OPEN = {}


def open_area(screen, hx, hy, sx, sy, rect_m, core=0.25):
    """m2 of a rectangle (metres east / south of map pixel (hx, hy), shrunk by `core`) on ground the player can walk to"""
    if screen not in _OPEN:
        lab, _ = label_components(~blocked3(screen))
        rim = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
        _OPEN[screen] = np.isin(lab, sorted(rim))
    x0, y0 = int(math.floor(hx + (rect_m[0] + core) / sx)) + 600, int(math.floor(hy + (rect_m[1] + core) / sy)) + 400
    x1, y1 = int(math.ceil(hx + (rect_m[2] - core) / sx)) + 600, int(math.ceil(hy + (rect_m[3] - core) / sy)) + 400
    return float(_OPEN[screen][max(0, y0):max(0, y1), max(0, x0):max(0, x1)].sum()) * sx * sy


def open_rot(screen, hx, hy, sx, sy, cx, cy, W, D, yaw, core=0.25, step=0.25):
    """m2 of a W x D rectangle (middle cx, cy metres east / south of map pixel (hx, hy), turned by yaw degrees, shrunk by `core`) on ground the player can walk to"""
    open_area(screen, hx, hy, sx, sy, (0, 0, 0, 0))
    a = math.radians(yaw); lx, ly = np.meshgrid(np.arange(-W / 2 + core, W / 2 - core + 1e-6, step), np.arange(-D / 2 + core, D / 2 - core + 1e-6, step))
    x = np.rint(hx + (cx + lx * math.cos(a) - ly * math.sin(a)) / sx).astype(int) + 600; y = np.rint(hy + (cy + lx * math.sin(a) + ly * math.cos(a)) / sy).astype(int) + 400
    ok = (x >= 0) & (x < 1800) & (y >= 0) & (y < 1200)
    return float(_OPEN[screen][y[ok], x[ok]].sum()) * step * step


CASTLE = {'wall': S + 'SM_Castle_Wall_8m', 'tower': S + 'SM_Castle_Tower_Round', 'gate': S + 'SM_Castle_Gatehouse'}
CASTLE_PITCH, CASTLE_WALL_Z, CASTLE_TOWER = 8.0, 1.5, 1.6      # metres of run per wall module; height scale of the walls; scale of the towers


def block_of(c0, r0, c1, r1):
    """blocked (True) over the screens of columns c0..c1, rows r0..r1 (0-based); a screen that does not exist and the map's own
    edge are closed. -> bool array with a one-pixel closed frame where the block ends at the edge of the map."""
    big = np.ones(((r1 - r0 + 1) * 400, (c1 - c0 + 1) * 600), bool)
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            row = COLLISION.get('SCR_%03d' % (r * 32 + c + 1))
            if row is None:
                continue
            m = np.zeros((400, 600), bool)
            for k in BLOCKING:
                for x0, y0, x1, y1 in row.get(k) or []:
                    m[max(0, y0):y1, max(0, x0):x1] = True
            big[(r - r0) * 400:(r - r0 + 1) * 400, (c - c0) * 600:(c - c0 + 1) * 600] = m
    if r0 == 0: big[0, :] = True
    if r1 == 23: big[-1, :] = True
    if c0 == 0: big[:, 0] = True
    if c1 == 31: big[:, -1] = True
    return big


def castles():
    """Curtain walls of the castles (sprite family 67): the 1997 map draws a castle as one closed hardness outline several screens
    wide, with a handful of wall and tower pictures on it. Kit wall modules run along that outline (so the wall the player sees
    is the line that stops him), a round tower stands at the outline corner nearest each tower picture and the gatehouse where
    the gate picture or the door's warp is. -> {screen: (modules, [placements hidden], note)}"""
    out = {}
    cast = [p for p in placements if p['seq'] == 67 and p.get('vision', 0) == 0 and p['screen'] not in SKIP_SCREENS and p['id'] not in SKIP_ORIGINS]
    todo = sorted({p['screen'] for p in cast}); groups = []
    while todo:                                        # screens that touch (also diagonally) are one castle
        g = {todo.pop(0)}; grew = True
        while grew:
            grew = False
            for n in list(todo):
                if any(abs((n - 1) % 32 - (m - 1) % 32) <= 1 and abs((n - 1) // 32 - (m - 1) // 32) <= 1 for m in g):
                    g.add(n); todo.remove(n); grew = True
        groups.append(sorted(g))
    for g in groups:
        c0, c1 = max(0, min((n - 1) % 32 for n in g) - 1), min(31, max((n - 1) % 32 for n in g) + 1)
        r0, r1 = max(0, min((n - 1) // 32 for n in g) - 1), min(23, max((n - 1) // 32 for n in g) + 1)
        big = block_of(c0, r0, c1, r1)
        gp = lambda p: ((( p['screen'] - 1) % 32 - c0) * 600 + p['map_x'], ((p['screen'] - 1) // 32 - r0) * 400 + p['map_y'])
        lab, _ = label_components(~big)
        rim = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
        closed = ~np.isin(lab, sorted(rim)) if rim else np.ones_like(big)
        lab2, _ = label_components(closed)
        mine = [p for p in cast if p['screen'] in g]
        doors_ = [p for p in placements if p['screen'] in g and p.get('vision', 0) == 0 and p.get('class_id') == 'castle_door']
        hits = collections.Counter(int(lab2[min(big.shape[0] - 1, max(0, int(gp(p)[1]))), min(big.shape[1] - 1, max(0, int(gp(p)[0])))]) for p in mine)
        hits.pop(0, None)
        if not hits:
            total['castle_without_closed_ground'] += 1; continue
        v = hits.most_common(1)[0][0]; region = lab2 == v
        if region.sum() < 40000 and '--debug' in sys.argv: print('small castle', g, int(region.sum()), dict(hits))
        if region.sum() < 40000:                       # a few metres of wall, not a castle: left to the cards
            total['castle_too_small'] += 1; continue
        core = shrink(region, 8)
        poly = simplify(outline(core), 24.0)
        if len(poly) < 3:
            continue
        mpp_at = lambda x, y: SCREEN_MPP.get(int(min(r1, max(r0, r0 + y // 400))) * 32 + int(min(c1, max(c0, c0 + x // 600))) + 1, (0.1, 0.1))
        open_ = np.isin(lab, sorted(rim))

        def beside_open(x, y, r=36):
            xi, yi = int(round(x)), int(round(y))
            return bool(open_[max(0, yi - r):yi + r + 1, max(0, xi - r):xi + r + 1].any())
        towers = []
        for p in mine:
            if p['class_id'] != 'castle_tower_round':
                continue
            x, y = gp(p); vx = min(poly, key=lambda q: math.hypot(q[0] - x, q[1] - y))
            if math.hypot(vx[0] - x, vx[1] - y) <= 260 and beside_open(*vx) and all(math.hypot(vx[0] - t[0], vx[1] - t[1]) > 60 for t in towers):
                towers.append(vx)
        if len(towers) < 2:                            # a stray wall picture (an interior sheet, a ruin): left to its cards
            total['castle_without_towers'] += 1; continue
        tr = 3.1 * CASTLE_TOWER
        moved = []
        for t in towers:                               # the tower stands inside the corner: its outer side one metre past the wall line, the rest on closed ground
            ys_, xs_ = np.nonzero(region[max(0, int(t[1]) - 90):int(t[1]) + 90, max(0, int(t[0]) - 90):int(t[0]) + 90])
            sx, sy = mpp_at(*t); cx_, cy_ = xs_.mean() + max(0, int(t[0]) - 90), ys_.mean() + max(0, int(t[1]) - 90)
            dx, dy = (cx_ - t[0]) * sx, (cy_ - t[1]) * sy; L = math.hypot(dx, dy) or 1.0
            moved.append((t[0] + dx / L * (tr - 0.5) / sx, t[1] + dy / L * (tr - 0.5) / sy))
        towers = moved
        gates = []
        for p in placements:
            if p['screen'] in g and p.get('vision', 0) == 0 and (p.get('class_id') in ('castle_gatehouse', 'castle_door') or (p.get('is_warp') and (p.get('class_id') or '').startswith('door'))):
                x, y = gp(p); best = None
                for i, a in enumerate(poly):
                    b = poly[(i + 1) % len(poly)]; L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 or 1e-9
                    t = max(0.0, min(1.0, ((x - a[0]) * (b[0] - a[0]) + (y - a[1]) * (b[1] - a[1])) / L2)); q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                    d = math.hypot(q[0] - x, q[1] - y)
                    if best is None or d < best[0]: best = (d, q, a, b)
                if best and best[0] <= 90 and all(math.hypot(best[1][0] - q[1][0], best[1][1] - q[1][1]) > 120 for q in gates):
                    gates.append(best)
        mods = []          # (global px x, y, mesh, yaw, scale)

        def facing(x, y, yaw):
            """yaw turned by 180 when the module's field face (-Y) would look into the castle"""
            a = math.radians(yaw); ox, oy = math.sin(a), -math.cos(a)
            xi, yi = int(round(x + 14 * ox)), int(round(y + 14 * oy))
            inside = 0 <= yi < region.shape[0] and 0 <= xi < region.shape[1] and core[yi, xi]
            return yaw + 180.0 if inside else yaw
        for t in towers:
            mods.append((t[0], t[1], CASTLE['tower'], 0.0, [CASTLE_TOWER] * 3))
        for d, q, a, b in gates:
            sx, sy = mpp_at(*q); yaw = math.degrees(math.atan2((b[1] - a[1]) * sy, (b[0] - a[0]) * sx))
            yaw = facing(q[0], q[1], yaw); a_ = math.radians(yaw); ix, iy = -math.sin(a_), math.cos(a_)      # into the castle
            # the gate block is 6 m deep with its turrets: it stands back so that its field face is on the wall's, not on the road
            mods.append((q[0] + 2.6 * ix / sx, q[1] + 2.6 * iy / sy, CASTLE['gate'], yaw, [1.25, 1.25, 1.25]))

        def keep(x, y):
            sx, sy = mpp_at(x, y)
            if not beside_open(x, y):
                return False
            if any(math.hypot((x - t[0]) * sx, (y - t[1]) * sy) < tr - 0.6 for t in towers):
                return False
            return not any(math.hypot((x - q[1][0]) * sx, (y - q[1][1]) * sy) < 6.3 for q in gates)     # the walls end inside the gatehouse: at 7.2 m a dark slit stood on each side of it (402)
        length = 0.0
        for a, b in yard_runs(poly, mpp_at((poly[0][0]), poly[0][1]), keep, min_m=3.0):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); sx, sy = mpp_at(*mid)
            ux, uy = (b[0] - a[0]) * sx, (b[1] - a[1]) * sy; L = math.hypot(ux, uy) or 1.0
            nx, ny = uy / L, -ux / L                   # a unit normal (metres); made to point out of the castle
            turned = False
            if core[min(core.shape[0] - 1, max(0, int(round(mid[1] + 14 * ny / sy)))), min(core.shape[1] - 1, max(0, int(round(mid[0] + 14 * nx / sx))))]:
                nx, ny = -nx, -ny; turned = True
            # The outline is a staircase of tiles and the wall is straight: the wall is moved in until its field face (0.9 m out from
            # its middle) no longer stands on ground the player can reach, so the wall he sees is never in front of the line that stops him.
            shift = 0.0
            while shift < 4.0:
                bad = 0; n_ = max(2, int(L / 0.5))
                for k in range(n_):
                    px_ = a[0] + (b[0] - a[0]) * (k + 0.5) / n_ + (0.9 - shift) * nx / sx; py_ = a[1] + (b[1] - a[1]) * (k + 0.5) / n_ + (0.9 - shift) * ny / sy
                    yi, xi = int(round(py_)), int(round(px_))
                    bad += bool(0 <= yi < open_.shape[0] and 0 <= xi < open_.shape[1] and open_[yi, xi])
                if bad <= 0.04 * n_:
                    break
                shift += 0.2
            a2 = (a[0] - shift * nx / sx, a[1] - shift * ny / sy); b2 = (b[0] - shift * nx / sx, b[1] - shift * ny / sy)
            # each run is 1.2 m longer at both ends: runs moved in by different amounts would leave slits one can see through
            L0 = L
            ex, ey = ux / L * 1.2 / sx, uy / L * 1.2 / sy
            a2 = (a2[0] - ex, a2[1] - ey); b2 = (b2[0] + ex, b2[1] + ey)
            ms, L = run_modules(CASTLE['wall'], a2, b2, (sx, sy), CASTLE_PITCH)
            length += L
            for m in ms:
                mods.append((m['px'][0], m['px'][1], m['mesh'], m['yaw'] + (180.0 if turned else 0.0), [m['scale'][0] * 1.012, 1.0, CASTLE_WALL_Z]))      # 1.2 % (10 cm) overlap: the joints showed as dark slits (433)
            # The wall module has no end faces. Where a run ends beside one that was moved in by another amount, its open end showed
            # as a black slit one sees through (433, and left of the gatehouse of 402). Each end is closed by a 2.5 m piece of the
            # same wall turned across it, standing inside the wall's own thickness (2.6 m), its face 5 cm proud of the end.
            if ms:
                yaw_run = ms[0]['yaw']
                for end, sign in ((a2, 1.0), (b2, -1.0)):
                    cx_, cy_ = end[0] + sign * ux / L0 * 1.25 / sx, end[1] + sign * uy / L0 * 1.25 / sy
                    mods.append((cx_, cy_, CASTLE['wall'], yaw_run + 90.0, [2.5 / CASTLE_PITCH, 1.0, CASTLE_WALL_Z]))
        per = collections.defaultdict(list)
        for x, y, mesh, yaw, sc in mods:
            c, r = int(min(c1, max(c0, c0 + x // 600))), int(min(r1, max(r0, r0 + y // 400))); n = r * 32 + c + 1
            if 'SCR_%03d' % n not in COLLISION:              # no such screen (the edge of a sheet): the nearest screen of the castle carries it
                n = min(g, key=lambda m: abs((m - 1) % 32 - c) + abs((m - 1) // 32 - r)); c, r = (n - 1) % 32, (n - 1) // 32
            per[n].append({'mesh': mesh, 'px': [round(x - (c - c0) * 600, 2), round(y - (r - r0) * 400, 2)], 'offset_cm': [0.0, 0.0, 0.0], 'yaw': round(yaw % 360.0, 2), 'scale': [round(v_, 4) for v_ in sc]})
        note = 'castle of screens %s: %.0f m of curtain wall along its hardness outline, %d towers, %d gatehouses' % (', '.join(str(n) for n in g), length, len(towers), len(gates))
        total['castles'] += 1; total['castle_modules'] += len(mods)
        screens_with = sorted(per)
        for n in sorted(set(g) | set(per)):
            hide = [p for p in mine + (doors_ if gates else []) if p['screen'] == n]
            # a screen of the castle whose pictures lie inside the outline has no module of its own: its cards are stood for by the
            # nearest screen's part of the wall (the loader hides by origin, whichever screen names it)
            out.setdefault(n, {'mods': per.get(n, []), 'hide': hide, 'note': note})
        lonely = [n for n in g if not per.get(n)]
        for n in lonely:
            if screens_with:
                tgt = min(screens_with, key=lambda m: abs((m - 1) % 32 - (n - 1) % 32) + abs((m - 1) // 32 - (n - 1) // 32))
                # the loader hides cards screen by screen, so the lonely screen keeps a set of its own: one wall module of the nearest
                # screen's wall, a little smaller, inside that wall (the trick of the cottage twins)
                src = next((m for m in out[tgt]['mods'] if m['mesh'] == CASTLE['wall']), out[tgt]['mods'][0]); m = dict(src)
                gx = src['px'][0] + ((tgt - 1) % 32 - (n - 1) % 32) * 600.0; gy = src['px'][1] + ((tgt - 1) // 32 - (n - 1) // 32) * 400.0
                m['px'] = [round(gx, 2), round(gy, 2)]; m['scale'] = [round(v_ * 0.97, 4) for v_ in src['scale']]
                out[n]['mods'] = [m]; out[n]['note'] += '; this screen holds no part of the wall: one module inside the wall of screen %d stands for its pictures' % tgt
    return out


def shrink(mask, r):
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r or (dx == 0 and dy == 0):
                continue
            sh = np.zeros_like(mask)
            sh[max(0, -dy):mask.shape[0] + min(0, -dy), max(0, -dx):mask.shape[1] + min(0, -dx)] = mask[max(0, dy):mask.shape[0] + min(0, dy), max(0, dx):mask.shape[1] + min(0, dx)]
            out &= sh
    return out


def outline(mask):
    """the longest closed boundary of a mask as a list of pixel-corner points (x, y), walked with the inside on the right"""
    m = np.pad(mask, 1); nxt = collections.defaultdict(list)
    ys, xs = np.nonzero(m)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if not m[y - 1, x]: nxt[(x, y)].append((x + 1, y))
        if not m[y, x + 1]: nxt[(x + 1, y)].append((x + 1, y + 1))
        if not m[y + 1, x]: nxt[(x + 1, y + 1)].append((x, y + 1))
        if not m[y, x - 1]: nxt[(x, y + 1)].append((x, y))
    best = []
    while nxt:
        start = next(iter(nxt)); loop = [start]; cur = start
        while True:
            outs = nxt[cur]; b = outs.pop()
            if not outs: del nxt[cur]
            if b == start: break
            loop.append(b); cur = b
            if cur not in nxt: break
        if len(loop) > len(best): best = loop
    return [(x - 1, y - 1) for x, y in best]


def simplify(pts, tol):
    """Douglas-Peucker on a closed outline"""
    def dp(a):
        if len(a) < 3: return a
        (x0, y0), (x1, y1) = a[0], a[-1]; L = math.hypot(x1 - x0, y1 - y0) or 1e-9
        d = [abs((x1 - x0) * (y0 - y) - (x0 - x) * (y1 - y0)) / L for x, y in a[1:-1]]
        i = max(range(len(d)), key=d.__getitem__)
        if d[i] <= tol: return [a[0], a[-1]]
        return dp(a[:i + 2])[:-1] + dp(a[i + 1:])
    if len(pts) < 4: return pts
    far = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
    return dp(pts[:far + 1])[:-1] + dp(pts[far:] + [pts[0]])[:-1]


def yard_runs(poly, mpp, keep, step_m=0.25, min_m=1.6, closed=True):
    """the stretches of an outline (map pixels; closed, or an open line) where keep(x, y) holds: [(a, b)] along its edges, each at least min_m long"""
    runs = []
    for i, a in enumerate(poly if closed else poly[:-1]):
        b = poly[(i + 1) % len(poly)]
        L = math.hypot((b[0] - a[0]) * mpp[0], (b[1] - a[1]) * mpp[1]); n = max(1, int(math.ceil(L / step_m)))
        flags = [keep(a[0] + (b[0] - a[0]) * (k + 0.5) / n, a[1] + (b[1] - a[1]) * (k + 0.5) / n) for k in range(n)]
        k = 0
        while k < n:
            if not flags[k]:
                k += 1; continue
            j = k
            while j < n and flags[j]: j += 1
            if (j - k) * L / n >= min_m:
                runs.append(((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n), (a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n)))
            k = j
    return runs


def yard(screen, seed, picture_rect, mpp, mesh, pitch, keep, inset_px=6, reach_px=45):
    """Fence modules along the closed ground a building stands in. The remaster lays these screens out at three to four times the
    sprite scale while a house keeps its real size, so the blocked ground is far larger than the house: without the fence the
    player is stopped metres away from it by nothing he can see. The closed ground is taken within reach_px of the picture
    (it often runs on into a cliff, a shore or the next house); the fence stands only where open ground lies just outside it.
    -> (modules, note) or ([], reason)."""
    region = closed_ground(screen, *seed)
    if region is None:
        return [], 'no closed ground at the building'
    x0, y0, x1, y1 = [int(round(v)) for v in picture_rect]
    win = np.zeros_like(region); win[max(0, y0 - reach_px + 400):y1 + reach_px + 400, max(0, x0 - reach_px + 600):x1 + reach_px + 600] = True
    lab, _ = label_components(region & win)
    v = lab[int(round(seed[1])) + 400, int(round(seed[0])) + 600]
    if not v:
        return [], 'no closed ground at the building'
    region = lab == v
    core = shrink(region, inset_px)
    if not core.any():
        return [], 'the closed ground is too narrow for a fence line'
    walk = ~blocked3(screen)
    lab, _ = label_components(walk)
    rim = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
    open_ = np.isin(lab, sorted(rim))
    r = inset_px + 5

    def beside_open(x, y):
        xi, yi = int(round(x)) + 600, int(round(y)) + 400
        return bool(open_[max(0, yi - r):yi + r + 1, max(0, xi - r):xi + r + 1].any())
    poly = [(x - 600, y - 400) for x, y in simplify(outline(core), 4.0)]
    mods = []; total = 0.0
    for a, b in yard_runs(poly, mpp, lambda x, y: keep(x, y) and beside_open(x, y)):
        m, length = run_modules(mesh, a, b, mpp, pitch); mods += m; total += length
    if not mods:
        return [], 'no open ground beside the closed ground'
    return mods, '%.0f m of fence in %d modules along its hardness outline' % (total, len(mods))


FRAMES = {(q['seq'], f['frame']): f for q in json.load(open(os.path.join(REPO, 'tools/dinkex/out/sequences.json')))['sequences'] for f in q['frames']}


def dressed():
    """screens and origins an art manifest handles (FDinkFamilyPrecedence::AddManifest)"""
    screens, origins = set(), set()
    art = os.path.join(ROOT, 'Content/Dink/Data/Art')
    for fn in sorted(os.listdir(art)):
        if not fn.endswith('.json'):
            continue
        try:
            d = json.load(open(os.path.join(art, fn)))
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get('schema') != 'dink-art/1':
            continue
        for field in ('replacements', 'warp_overrides'):
            origins.update(x['origin'] for x in d.get(field) or [] if isinstance(x, dict) and x.get('origin'))
        origins.update(o for o in d.get('hide_origins') or [] if isinstance(o, str))
        hv = d.get('hide_origins_by_vision')
        for lst in (hv.values() if isinstance(hv, dict) else [hv] if isinstance(hv, list) else []):
            origins.update(o for o in lst or [] if isinstance(o, str))
        for field in ('hide_screen_visuals', 'authored_collision_screens'):
            screens.update(int(x) for x in d.get(field) or [] if isinstance(x, (int, float)))
        if d.get('elements') and isinstance(d.get('screen'), (int, float)):
            screens.add(int(d['screen']))
    return screens, origins


SKIP_SCREENS, SKIP_ORIGINS = dressed()
SCREEN_MPP = {}
for _p in placements:
    SCREEN_MPP.setdefault(_p['screen'], (_p['scale_x'], _p['scale_y']))
for _s in json.load(open(os.path.join(ROOT, 'ImportData/screens.json')))['screens']:      # a screen without placements
    _c = _s.get('corners')
    if _c:
        SCREEN_MPP.setdefault(_s['screen'], (math.hypot(_c['ne'][0] - _c['nw'][0], _c['ne'][1] - _c['nw'][1]) / 600.0, math.hypot(_c['sw'][0] - _c['nw'][0], _c['sw'][1] - _c['nw'][1]) / 400.0))
by_screen = collections.defaultdict(list)
for p in placements:
    if p['screen'] not in SKIP_SCREENS and p['id'] not in SKIP_ORIGINS and p.get('vision', 0) == 0:
        by_screen[p['screen']].append(p)


def unique(ps):
    """the bundle lists some placements twice (a background and a live copy at the same point, sometimes a pixel apart): one piece for both"""
    out = []
    for p in ps:
        twin = next((q for q in out if q['seq'] == p['seq'] and q['frame'] == p['frame'] and abs(q['map_x'] - p['map_x']) <= 2 and abs(q['map_y'] - p['map_y']) <= 2), None)
        if twin:
            twin['_also'].append(p['id'])
        else:
            out.append(dict(p, _also=[]))
    return out


def run_modules(mesh, a, b, mpp, pitch, yaw_add=0.0, z=0.0, scale_y=1.0):
    """modules of `pitch` metres along the ground line a -> b (map pixels), scaled along their own X to close it"""
    dx, dy = (b[0] - a[0]) * mpp[0], (b[1] - a[1]) * mpp[1]
    length = math.hypot(dx, dy)
    if length < 0.3:
        return [], 0.0
    n = max(1, int(round(length / pitch)))
    yaw = math.degrees(math.atan2(dy, dx))
    mods = []
    for i in range(n):
        t = (i + 0.5) / n
        mods.append({'mesh': mesh, 'px': [round(a[0] + (b[0] - a[0]) * t, 2), round(a[1] + (b[1] - a[1]) * t, 2)], 'offset_cm': [0.0, 0.0, round(z, 1)],
                     'yaw': round(yaw + yaw_add, 2), 'scale': [round(length / (n * pitch), 4), round(scale_y, 4), 1.0]})
    return mods, length


def ground_line(p, kind):
    """the ground line of a fence sprite from its hardbox: 'ew' the middle line, 'ns' the middle column, 'rise' / 'fall' a diagonal"""
    hb = FRAMES[(p['seq'], p['frame'])]['hardbox']; x, y = p['map_x'], p['map_y']
    if kind == 'ew':
        m = (hb['top'] + hb['bottom']) / 2.0
        return (x + hb['left'], y + m), (x + hb['right'], y + m)
    if kind == 'ns':
        m = (hb['left'] + hb['right']) / 2.0
        return (x + m, y + hb['top']), (x + m, y + hb['bottom'])
    if kind == 'rise':
        return (x + hb['left'], y + hb['bottom']), (x + hb['right'], y + hb['top'])
    return (x + hb['left'], y + hb['top']), (x + hb['right'], y + hb['bottom'])


def picture(p):
    """map-pixel rectangle (x0, y0, x1, y1) the sprite's picture covers"""
    f = FRAMES[(p['seq'], p['frame'])]; k = p.get('size_percent', 100) / 100.0
    x0, y0 = p['map_x'] - f['origin']['x'] * k, p['map_y'] - f['origin']['y'] * k
    return x0, y0, x0 + f['width'] * k, y0 + f['height'] * k


FENCE_KIND = {1: 'ew', 4: 'ns', 2: 'rise', 5: 'rise', 3: 'fall', 6: 'fall'}
out = {'schema': 'dink-town-houses/3', 'generated_by': 'Scripts/assemble_structures.py', 'families_yield': True,
       'note': 'Structures the 1997 game draws in several sprites, laid along their ground lines: split-rail and island fences, wooden bridges, wells. '
               'Reads ImportData/placements.json and tools/dinkex/out/sequences.json; shown by UDinkEnvironmentSubsystem beside town_houses.json (dink.TownHouses). '
               'Visual only: hardness, warps and scripts are untouched.', 'screens': {}}
total = collections.Counter()
CASTLES = castles()
for screen in sorted(set(by_screen) | set(CASTLES)):
    ps = by_screen[screen]; sets = []; footprints = []; fence_lines = []

    def emit(kind, pieces, mods, note, **extra):
        ids = sorted({i for p in pieces for i in [p['id']] + p.get('_also', [])})
        sets.append(dict({'id': 'S%d_%s%d' % (screen, kind, len(sets) + 1), 'kind': kind, 'note': note, 'modules': mods, 'hide': ids}, **extra))
        total[kind] += 1; total['modules'] += len(mods); total['hidden'] += len(ids)

    if screen in CASTLES and CASTLES[screen]['mods']:
        emit('castle', CASTLES[screen]['hide'], CASTLES[screen]['mods'], CASTLES[screen]['note'])

    # ---- fences: one set per sprite, so a run reads in the JSON as the sprites it came from
    for cls_prefix, seq, mesh, pitch, kinds in (('fence_rail_', 93, FENCE, FENCE_PITCH, FENCE_KIND), ('island_fence_lattice', 424, LATTICE, LATTICE_PITCH, {7: 'ew', 8: 'ns'})):
        pieces = unique([q for q in ps if q['seq'] == seq and (q.get('class_id') or '').startswith(cls_prefix) and q['frame'] in kinds])
        lines = [list(ground_line(p, kinds[p['frame']])) for p in pieces]
        # the hardboxes of neighbouring sprites end a few pixels apart: ends within SNAP_PX of each other become one point, so a run has no gaps or steps
        ends = [(i, j) for i in range(len(lines)) for j in (0, 1)]; done = set()
        for e in ends:
            if e in done:
                continue
            group = [f for f in ends if f not in done and math.hypot(lines[f[0]][f[1]][0] - lines[e[0]][e[1]][0], lines[f[0]][f[1]][1] - lines[e[0]][e[1]][1]) <= SNAP_PX]
            if len(group) > 1 and len({f[0] for f in group}) > 1:
                m = (sum(lines[f[0]][f[1]][0] for f in group) / len(group), sum(lines[f[0]][f[1]][1] for f in group) / len(group))
                for f in group:
                    lines[f[0]][f[1]] = m
            done.update(group)
        for p, (a, b) in zip(pieces, lines):
            fence_lines.append((a, b))
            mods, length = run_modules(mesh, a, b, (p['scale_x'], p['scale_y']), pitch)
            if mods:
                emit('fence' if seq == 93 else 'lattice', [p], mods, '%s frame %d: %.1f m of ground, %d modules' % (p['class_id'], p['frame'], length, len(mods)), length_m=round(length, 2))

    # ---- wooden bridges
    decks = unique([q for q in ps if q['seq'] == 58 and q['frame'] in (1, 2, 3)])
    for p in decks:                                    # north-south bridge: the picture is the deck
        x0, y0, x1, y1 = picture(p); cx = (x0 + x1) / 2.0
        width = (x1 - x0) * p['scale_x'] * 0.86        # the picture's side beams are part of its width
        mods, length = run_modules(DECK, (cx, y0), (cx, y1), (p['scale_x'], p['scale_y']), DECK_LEN, scale_y=width / DECK_WIDTH)
        emit('deck', [p], mods, 'bridge_wood_deck frame %d: %.1f m long, %.1f m wide' % (p['frame'], length, width), length_m=round(length, 2), width_m=round(width, 2))
        footprints.append({'px': [round(cx, 2), round((y0 + y1) / 2.0, 2)], 'yaw': 0.0,
                           'rect_cm': [round(-50.0 * width - 30.0, 1), round(-50.0 * length - 30.0, 1), round(50.0 * width + 30.0, 1), round(50.0 * length + 30.0, 1)]})
    far = unique([q for q in ps if q['seq'] == 58 and q['frame'] in (6, 8, 10)])
    near = unique([q for q in ps if q['seq'] == 58 and q['frame'] in (7, 9, 11)])
    if far and near:                                   # east-west bridge: the deck lies between the two rail lines
        ends = lambda ps_, fr: [p for p in ps_ if p['frame'] in fr] or ps_     # the middle pieces (10, 11) have another hotspot
        yf = sum(p['map_y'] for p in ends(far, (6, 8))) / len(ends(far, (6, 8))); yn = sum(p['map_y'] for p in ends(near, (7, 9))) / len(ends(near, (7, 9)))
        x0 = min(picture(p)[0] for p in far + near); x1 = max(picture(p)[2] for p in far + near)
        mpp = (far[0]['scale_x'], far[0]['scale_y'])
        # The walkway is the band of hardness 0 between the rails: the rails stand on the blocked rows just outside it and end where
        # those rows end, so nothing that looks solid stands where the player walks (owner decision, 14 Nov 2026).
        big = blocked3(screen); tops, bots = [], []
        for x in range(int(x0) + 12, int(x1) - 12, 4):
            col = big[400:800, 600 + x] if 0 <= x < 600 else None
            ym = int(round((yf + yn) / 2.0))
            if col is None or not (0 <= ym < 400) or col[ym]:
                continue
            t = ym
            while t > 0 and not col[t - 1]: t -= 1
            b_ = ym
            while b_ < 399 and not col[b_ + 1]: b_ += 1
            tops.append(t); bots.append(b_)
        if tops:
            yf, yn = float(np.median(tops)) - 2.0, float(np.median(bots)) + 3.0
        def rail(mesh_, y, yaw_add=0.0):
            """rail modules along row y, only over the stretches of it that are blocked"""
            row = big[400 + int(round(min(399, max(0, y)))), 600:1200]; out_ = []
            for a_, b_ in yard_runs([(max(0.0, x0), y), (min(600.0, x1), y)], mpp, lambda x, y_: bool(row[int(min(599, max(0, x)))]), min_m=5.0, closed=False):       # a lone 2.5 m of rail in mid-bridge read as a shelf (seen on 404)
                out_ += run_modules(mesh_, a_, b_, mpp, RAIL_LEN, yaw_add=yaw_add)[0]
            return out_
        width = (yn - yf) * mpp[1]
        deck, length = run_modules(DECK, (x0, (yf + yn) / 2.0), (x1, (yf + yn) / 2.0), mpp, DECK_LEN, scale_y=width / DECK_WIDTH)
        rails = rail(RAIL_PLANK, yf) + rail(RAIL_ROPE, yn, 180.0)
        emit('bridge', far + near, deck + rails, 'east-west wooden bridge: %.1f m long, %.1f m between the rail lines (the rows of hardness beside the walkway), %d deck and %d rail modules' % (length, width, len(deck), len(rails)),
             length_m=round(length, 2), width_m=round(width, 2))
        footprints.append({'px': [round((x0 + x1) / 2.0, 2), round((yf + yn) / 2.0, 2)], 'yaw': 0.0,
                           'rect_cm': [round(-50.0 * length - 30.0, 1), round(-50.0 * width - 60.0, 1), round(50.0 * length + 30.0, 1), round(50.0 * width + 60.0, 1)]})
    elif far or near:
        total['bridge_rails_without_pair'] += len(far) + len(near)

    # ---- wells
    for p in unique([q for q in ps if q.get('class_id') == 'well_stone']):
        hb = FRAMES[(p['seq'], p['frame'])]['hardbox']
        at = [round(p['map_x'] + (hb['left'] + hb['right']) / 2.0, 2), round(p['map_y'] + (hb['top'] + hb['bottom']) / 2.0, 2)]
        emit('well', [p], [{'mesh': m, 'px': at, 'offset_cm': [0.0, 0.0, 0.0], 'yaw': 0.0, 'scale': [1.0, 1.0, 1.0]} for m in (WELL, WELL_CAP)],
             'well_stone frame %d at the middle of its hardbox, with the shaft cap' % p['frame'])
        footprints.append({'px': at, 'yaw': 0.0, 'rect_cm': [-150.0, -110.0, 150.0, 110.0]})

    # ---- thatched cottages: the house at real size on its hardbox, front wall on the hardbox's south line, a door on that wall where the warp door is
    # The log cabin (59 frame 1; screens 251 and 270) is written but switched off: on 251 the door's trigger lies in the middle of the cabin's
    # hardness and a cabin square to the screen does not fit between it and the open ground (it needs a turned house), and the mesh has
    # not been imported or judged in the game. --log-cabin turns it on.
    cottages = unique([q for q in ps if (q.get('class_id') or '').startswith('cottage_thatched') or (q.get('class_id') == 'log_cabin' and '--log-cabin' in sys.argv) or (q.get('class_id') == 'church' and '--church' in sys.argv)])
    doors = [q for q in ps if q.get('class_id') in ('door_wood_single', 'door_wood_wide', 'cottage_door')]
    used_doors = []
    for p in cottages:
        mesh, W, D, opening = COTTAGE[p['class_id']]
        hb = FRAMES[(p['seq'], p['frame'])]['hardbox']; sx, sy = p['scale_x'], p['scale_y']
        hx, hy = p['map_x'] + (hb['left'] + hb['right']) / 2.0, p['map_y'] + (hb['top'] + hb['bottom']) / 2.0
        south = p['map_y'] + hb['bottom']
        # the door: the warp sprite (61 / 62) first, else the door picture (63 frames 2, 3), within reach of this house's front
        near = sorted((q for q in doors if p['map_x'] + hb['left'] - 45 <= q['map_x'] <= p['map_x'] + hb['right'] + 45 and p['map_y'] + hb['top'] <= q['map_y'] <= south + 75),
                      key=lambda q: (not q['class_id'].startswith('door_wood'), abs(q['map_y'] - south) + 0.3 * abs(q['map_x'] - hx)))
        door = near[0] if near else None
        # The remaster lays these screens out at about four times the sprite scale, so the hardbox (and the door's place on it) is far
        # wider than a real cottage. The house is stretched along its front, at most 1.6 times, toward the hardbox width; a house with a
        # doorway cut in its wall is not stretched. Then it moves east or west only as far as it must for the door to be on its wall.
        scale_x = 1.0 if opening is not None else max(1.0, min(1.6, (hb['right'] - hb['left']) * sx / W))
        half = W * scale_x / 2.0 - 0.9
        mirror = bool(door) and (mesh in MODELLED_DOOR or mesh in (CABIN, CHURCH)) and (door['map_x'] - hx) * sx > 0.0      # frame 5 is frame 4 mirrored: the door on the east half
        if mirror:
            opening = -opening
        cx = 0.0; local = None                         # cx: metres east of the hardbox centre; local: door middle on the wall, from the house middle
        if door:
            d = (door['map_x'] - hx) * sx
            if opening is not None:
                local = opening; cx = d - local
            else:
                # the visible door may stand anywhere over the warp trigger (the door sprite's hardbox), which lets the house stay nearer its hardbox
                dh = FRAMES[(door['seq'], door['frame'])]['hardbox'] if door['class_id'].startswith('door_wood') else {'left': 0, 'right': 0}
                lo, hi = d + dh['left'] * sx + 0.5, d + dh['right'] * sx - 0.5
                lo, hi = (lo, hi) if lo <= hi else (d, d)
                target = max(lo, min(hi, max(-half, min(half, d))))
                local = max(-half, min(half, target)); cx = target - local
        cy = (south - hy) * sy + 0.10 - D / 2.0         # the front wall stands 10 cm south of the hardbox line
        # Better where the ground allows it (15 Nov 2026): the front wall on the south edge of the door's warp trigger, so Dink walks into the
        # door he sees instead of vanishing some metres in front of the house. Kept only if no part of the walls then stands on open ground.
        if door and door['class_id'].startswith('door_wood'):
            dh_ = FRAMES[(door['seq'], door['frame'])]['hardbox']
            # search: the door (1.5 m of wall) anywhere over the trigger's width, the front wall from the trigger's south edge northwards;
            # the southernmost place where the walls stand clear of open ground wins, then the one nearest the trigger's middle
            tx0, tx1 = (door['map_x'] + dh_['left'] - hx) * sx + 0.8, (door['map_x'] + dh_['right'] - hx) * sx - 0.8
            tmid = (tx0 + tx1) / 2.0; best = None
            for k in range(0, 13):
                front_y = (door['map_y'] + dh_['bottom'] - 3 - hy) * sy - 0.5 * k
                if front_y - D / 2.0 <= cy:
                    break
                xs_ = sorted({round(tmid + (tx1 - tx0) / 2.0 * f, 2) for f in (0.0, -0.5, 0.5, -1.0, 1.0)} if tx1 > tx0 else {round(tmid, 2)}, key=lambda v: abs(v - tmid))
                for dx_ in xs_:
                    for loc in ([opening] if opening is not None else [0.0, -half * 0.5, half * 0.5, -half, half]):
                        cx_try, cy_try = dx_ - loc, front_y - D / 2.0
                        if open_area(screen, hx, hy, sx, sy, (cx_try - W * scale_x / 2, cy_try - D / 2, cx_try + W * scale_x / 2, cy_try + D / 2)) <= 0.3:
                            best = (cx_try, cy_try, loc); break
                    if best: break
                if best: break
            if best:
                cx, cy, local = best; total['cottage_on_its_door'] += 1
        # A house whose 1997 hardness is a diagonal staircase (the picture shows it turned 45 degrees): the church and the log cabin are turned
        # about the vertical until their walls stand clear of open ground with the door over its trigger (--church, --log-cabin).
        yaw_h = 0.0
        if mesh in TURNED and door and door['class_id'].startswith('door_wood') and open_rot(screen, hx, hy, sx, sy, cx, cy, W, D, 0.0) > 0.3:
            dh_ = FRAMES[(door['seq'], door['frame'])]['hardbox']; found = None
            txm = (door['map_x'] + (dh_['left'] + dh_['right']) / 2.0 - hx) * sx; txh = max(0.0, (dh_['right'] - dh_['left']) * sx / 2.0 - 0.8)
            for k in range(0, 13):
                ty = (door['map_y'] + dh_['bottom'] - 3 - hy) * sy - 0.5 * k
                for yw in (0.0, 20.0, -20.0, 35.0, -35.0, 45.0, -45.0, 60.0, -60.0):
                    a_ = math.radians(yw)
                    for op in (abs(opening), -abs(opening)):
                        for f in (0.0, -1.0, 1.0):
                            tx = txm + f * txh
                            ccx = tx - (op * math.cos(a_) - D / 2.0 * math.sin(a_)); ccy = ty - (op * math.sin(a_) + D / 2.0 * math.cos(a_))
                            if open_rot(screen, hx, hy, sx, sy, ccx, ccy, W, D, yw) <= 0.3:
                                found = (ccx, ccy, yw, op); break
                        if found: break
                    if found: break
                if found: break
            if found:
                cx, cy, yaw_h, op = found; mirror = (op > 0) != (COTTAGE[p['class_id']][3] > 0); opening = op; total['house_turned'] += 1
            else:
                total['house_does_not_fit'] += 1; continue        # left to its card
        sgn = -1.0 if mirror else 1.0

        def at(lx, ly, z=0.0, cx=cx, cy=cy, a_=math.radians(yaw_h)):
            """offset_cm of a point (metres east / south of the house middle before the turn)"""
            return [round(100 * (cx + lx * math.cos(a_) - ly * math.sin(a_)), 1), round(100 * (cy + lx * math.sin(a_) + ly * math.cos(a_)), 1), z]
        mods = [{'mesh': mesh, 'px': [round(hx, 2), round(hy, 2)], 'offset_cm': at(0.0, 0.0), 'yaw': yaw_h, 'scale': [round(-scale_x if mirror else scale_x, 4), 1.0, 1.0]}]
        hide = [p]
        if mesh == CABIN:                                 # the cabin's own leaf (hinge at x = 0, 1.03 m along +X) and the pane of its window opening
            for mesh_, lx_, z_, sc_ in ((CABIN_DOOR, sgn * -1.4 - 0.5, 0.0, [1.0, 1.0, 1.0]), (CABIN_WINDOW, sgn * 1.7, 95.0, [1.19, 1.0, 0.95])):
                mods.append({'mesh': mesh_, 'px': [round(hx, 2), round(hy, 2)], 'offset_cm': at(lx_, D / 2.0 - 0.2, z_), 'yaw': yaw_h, 'scale': sc_})
        elif mesh == CHURCH:                              # the leaf (1.19 x 2.42 m, hinge at x = 0) fills the 1.6 m opening
            mods.append({'mesh': CHURCH_DOOR, 'px': [round(hx, 2), round(hy, 2)], 'offset_cm': at(sgn * -8.0 - 0.8, D / 2.0 - 0.25), 'yaw': yaw_h, 'scale': [1.35, 1.0, 1.2]})
        elif door and mesh not in MODELLED_DOOR:
            front = D / 2.0
            if p['class_id'] == 'cottage_thatched_l_shape':   # the wing stands forward of the two-storey block: the door goes on the face in front of it
                front = 5.7 if local > 0.1 else 1.6
            leaf_x, leaf_y = (opening - 0.72, front - 0.2) if opening is not None else (local - 0.72, front + 0.06)
            mods.append({'mesh': COTTAGE_DOOR, 'px': [round(hx, 2), round(hy, 2)], 'offset_cm': [round(100 * (cx + leaf_x), 1), round(100 * (cy + leaf_y), 1), 0.0], 'yaw': 0.0, 'scale': [1.0, 1.0, 1.0]})
        if door:
            used_doors += [q for q in doors if abs(q['map_x'] - door['map_x']) <= 40 and abs(q['map_y'] - door['map_y']) <= 40]
        if screen == 440 and mesh == HOUSE_440:
            by_id = {q['id']: q for q in ps}
            for name, rel, origin, yaw_, z_, stands in YARD_440:
                if rel is not None:
                    mods.append({'mesh': K440 + name, 'px': [round(hx, 2), round(hy, 2)], 'offset_cm': [round(100 * (cx + rel[0]), 1), round(100 * (cy + rel[1]), 1), z_], 'yaw': yaw_, 'scale': [1.0, 1.0, 1.0]})
                elif origin in by_id:
                    mods.append({'mesh': K440 + name, 'px': [by_id[origin]['map_x'], by_id[origin]['map_y']], 'offset_cm': [0.0, 0.0, z_], 'yaw': yaw_, 'scale': [1.0, 1.0, 1.0]})
                    hide.append(by_id[origin])
        # the yard: a split-rail fence along the hardness outline the house stands in, open where the door's warp is (the gate)
        ext_x = (W * scale_x * abs(math.cos(math.radians(yaw_h))) + D * abs(math.sin(math.radians(yaw_h)))) / 2; ext_y = (W * scale_x * abs(math.sin(math.radians(yaw_h))) + D * abs(math.cos(math.radians(yaw_h)))) / 2
        hx0, hy0, hx1, hy1 = cx - ext_x - 0.6, cy - ext_y - 0.6, cx + ext_x + 0.6, cy + ext_y + 0.6      # the house (its bounding box when turned), metres from (hx, hy)
        gate = (door['map_x'], door['map_y']) if door else None

        def keep(x, y, sx=sx, sy=sy, hx=hx, hy=hy, box=(hx0, hy0, hx1, hy1), gate=gate):
            mx, my = (x - hx) * sx, (y - hy) * sy
            if box[0] <= mx <= box[2] and box[1] <= my <= box[3]:
                return False
            for (ax, ay), (bx, by) in fence_lines:           # a fence sprite already runs here
                ux, uy = (bx - ax) * sx, (by - ay) * sy; L2 = ux * ux + uy * uy or 1e-9
                t = max(0.0, min(1.0, (((x - ax) * sx) * ux + ((y - ay) * sy) * uy) / L2))
                if math.hypot((x - ax) * sx - t * ux, (y - ay) * sy - t * uy) < 1.8:
                    return False
            return not (gate and abs(x - gate[0]) * sx <= 1.7 and abs(y - gate[1]) * sy <= 4.5)
        fence, yard_note = yard(screen, (hx, hy), picture(p), (sx, sy), FENCE, FENCE_PITCH, keep)
        total['yard_modules'] += len(fence); total['yards'] += bool(fence); total['no_yard'] += not fence
        mods += fence
        emit('cottage', hide, mods, '%s frame %d: %s, front x %.2f, %.1f m %s of its hardbox middle%s; yard: %s' % (p['class_id'], p['frame'], mesh.split('/')[-1], scale_x, abs(cx), 'east' if cx >= 0 else 'west',
             ', door at %s' % door['id'] if door else ', no door sprite in reach', yard_note), door=door['id'] if door else None)
        footprints.append({'px': [round(hx + cx / sx, 2), round(hy + cy / sy, 2)], 'yaw': yaw_h, 'rect_cm': [round(-50 * W * scale_x - 60, 1), round(-50 * D - 60, 1), round(50 * W * scale_x + 60, 1), round(50 * D + 160, 1)]})
    if cottages:
        # What the sprites draw on the houses and the meshes carry themselves: door pictures and warp door cards, chimneys, window
        # pictures. Each is hidden with the house it is drawn on (the nearest one), which stands for it.
        extra = [q for q in ps if q.get('class_id') in ('chimney_stone', 'cottage_door', 'log_cabin_window', 'log_cabin_door', 'church_door', 'church_stained_glass', 'church_window_small') or q in used_doors]
        houses_here = [h for h in sets if h['kind'] == 'cottage']
        for q in (unique(extra) if houses_here else []):
            h = min(houses_here, key=lambda h: math.hypot(h['modules'][0]['px'][0] - q['map_x'], h['modules'][0]['px'][1] - q['map_y']))
            ids = [q['id']] + q.get('_also', [])
            h['hide'] = sorted(set(h['hide']) | set(ids)); h.setdefault('parts', []).extend(sorted(ids)); total['hidden'] += len(ids); total['cottage_parts'] += len(ids)

    # ---- island huts: the hut at HUT_SCALE on the middle of its picture, turned so that its doorway looks where the sprite's does
    for p in unique([q for q in ps if q.get('class_id') in ('island_hut_round', 'island_hut_two_storey')]):
        x0, y0, x1, y1 = picture(p)
        mesh = HUT_ROUND if p['class_id'] == 'island_hut_round' else HUT_TWO
        yaw = {1: 35.0, 2: 0.0, 3: -35.0, 4: 35.0, 5: 0.0, 6: -35.0}[p['frame']]
        # The hut stands in the middle of its hardbox's depth (it was 1.4 m north of it: the back third of the hut could be walked
        # through); the hardbox is three times as wide as a real hut, so a lashed fence runs along the rest of it: a pen on each side.
        hb = FRAMES[(p['seq'], p['frame'])]['hardbox']; sx, sy = p['scale_x'], p['scale_y']
        hut_scale = round(max(0.85, min(HUT_SCALE, ((hb['bottom'] - hb['top']) * sy - 0.1) / 5.2)), 3)      # the wall ring (5.2 m across) fits the hardbox's depth
        radius = 2.6 * hut_scale
        hy_ = p['map_y'] + (hb['top'] + hb['bottom']) / 2.0
        hx_ = max(p['map_x'] + hb['left'] + radius / sx, min(p['map_x'] + hb['right'] - radius / sx, (x0 + x1) / 2.0))
        at = [round(hx_, 2), round(hy_, 2)]
        rect = [(p['map_x'] + hb['left'] + 4, p['map_y'] + hb['top'] + 4), (p['map_x'] + hb['right'] - 4, p['map_y'] + hb['top'] + 4),
                (p['map_x'] + hb['right'] - 4, p['map_y'] + hb['bottom'] - 4), (p['map_x'] + hb['left'] + 4, p['map_y'] + hb['bottom'] - 4)]
        pen = []
        for a, b in yard_runs(rect, (sx, sy), lambda x, y: math.hypot((x - hx_) * sx, (y - hy_) * sy) > radius + 0.5):
            pen += run_modules(LATTICE, a, b, (sx, sy), LATTICE_PITCH)[0]
        total['pen_modules'] += len(pen)
        emit('hut', [p], [{'mesh': mesh, 'px': at, 'offset_cm': [0.0, 0.0, 0.0], 'yaw': yaw, 'scale': [hut_scale] * 3}] + pen,
             '%s frame %d, doorway yaw %g, scale %g, on the middle of its hardbox with %d fence modules along the rest of it' % (p['class_id'], p['frame'], yaw, hut_scale, len(pen)))
        footprints.append({'px': at, 'yaw': 0.0, 'rect_cm': [-420.0, -420.0, 420.0, 520.0]})

    if sets:
        out['screens'][str(screen)] = {'houses': sets, 'footprints': footprints,
                                       'stands_for': {o: h['id'] for h in sets for o in h['hide']}}

# ---- one building drawn from two or three screens (the 1997 map repeats a house that crosses a screen edge on each of them):
# every screen's set must hide its own cards, but only one house may stand. The owner is the set whose house lies on (or nearest
# to) its own screen: a point far off a screen is placed less exactly; a twin keeps one module, the same mesh on the owner's spot and a little smaller, inside the owner's walls.
_SCREENS = {q['screen']: q for q in json.load(open(os.path.join(ROOT, 'ImportData/screens.json')))['screens']}


def _world(n, px):
    c = _SCREENS[n]['corners']; u, v = px[0] / 600.0, px[1] / 400.0
    top = [c['nw'][i] + (c['ne'][i] - c['nw'][i]) * u for i in (0, 1)]; bot = [c['sw'][i] + (c['se'][i] - c['sw'][i]) * u for i in (0, 1)]
    return [top[i] + (bot[i] - top[i]) * v for i in (0, 1)]


def _px(n, w):
    """the map pixel of screen n that lies at world point w: the screens are sheared quadrilaterals, so the blend of _world is
    inverted by Newton steps from the middle of the screen"""
    x, y = 300.0, 200.0
    for _ in range(12):
        f = _world(n, (x, y)); fx = _world(n, (x + 1.0, y)); fy = _world(n, (x, y + 1.0))
        a11, a21, a12, a22 = fx[0] - f[0], fx[1] - f[1], fy[0] - f[0], fy[1] - f[1]; det = a11 * a22 - a12 * a21
        rx, ry = w[0] - f[0], w[1] - f[1]
        x += (rx * a22 - ry * a12) / det; y += (ry * a11 - rx * a21) / det
    return [round(x, 2), round(y, 2)]


def _true_world(n, px):
    """World point of a map pixel given in screen n's frame, also off that screen. The 1997 map continues over a screen edge
    as a rectangle (y -40 of a screen is y 360 of the one above); the remaster's screens are sheared quadrilaterals, and the
    runtime carries a set's pixel through its OWN screen's blend, which leaves the neighbour's ground by metres a few dozen
    pixels past the edge. So a point off the screen is read through the screen it lies on (found in the walk audit of
    16 Nov 2026: a house repeated on the next screen stood 9 m beside itself, in the lane between two yards)."""
    dc, dr = int(px[0] // 600), int(px[1] // 400)
    c, r = (n - 1) % 32 + dc, (n - 1) // 32 + dr
    other = r * 32 + c + 1
    if (dc or dr) and 0 <= c < 32 and 0 <= r < 24 and other in _SCREENS and 'SCR_%03d' % other in COLLISION \
            and _SCREENS[other].get('indoor') == _SCREENS[n].get('indoor') and _SCREENS[other].get('sheet') == _SCREENS[n].get('sheet'):
        return _world(other, (px[0] - dc * 600.0, px[1] - dr * 400.0))
    return _world(n, px)


bodies = []
for key, row in out['screens'].items():
    for h in row['houses']:
        if h['kind'] in ('cottage', 'hut') and h['modules']:
            m = h['modules'][0]; spot = _true_world(int(key), m['px']); w = [spot[0] + m['offset_cm'][0] / 100.0, spot[1] + m['offset_cm'][1] / 100.0]
            x_, y_ = m['px'][0] + m['offset_cm'][0] / 100.0 / SCREEN_MPP[int(key)][0], m['px'][1] + m['offset_cm'][1] / 100.0 / SCREEN_MPP[int(key)][1]
            away = math.hypot(max(0.0, -x_, x_ - 600.0), max(0.0, -y_, y_ - 400.0))        # how far off its own screen the house stands (px)
            bodies.append({'screen': int(key), 'set': h, 'world': w, 'spot': spot, 'away': away})
bodies.sort(key=lambda b: (b['away'], b['set']['id']))
owners = []
for b in bodies:
    # the same building: the same mesh where the same 1997 sprite stands (`spot`, before a house is moved onto its door; two
    # screens repeat a sprite on the same map pixel), or where the houses themselves ended up
    own = next((o for o in owners if o['set']['modules'][0]['mesh'] == b['set']['modules'][0]['mesh'] and
                min(math.hypot(o['spot'][0] - b['spot'][0], o['spot'][1] - b['spot'][1]), math.hypot(o['world'][0] - b['world'][0], o['world'][1] - b['world'][1])) < 4.0), None)
    if own is None:
        owners.append(b); continue
    m = dict(own['set']['modules'][0]); m['px'] = _px(b['screen'], own['world']); m['offset_cm'] = [0.0, 0.0, 0.0]; m['scale'] = [round(v * 0.985, 4) for v in m['scale']]
    b['set']['modules'] = [m]; b['set']['twin_of'] = own['set']['id']
    b['set']['note'] += '; the same building as %s on the next screen: one module inside that house, no door or fence of its own' % own['set']['id']
    total['twins'] += 1

# every module off its own screen: its pixel is rewritten so that the runtime's blend of the set's screen gives the point
# the 1997 map means (a twin's module was already placed through _px)
for key, row in out['screens'].items():
    for h in row['houses']:
        if h.get('twin_of'):
            continue
        for m in h['modules']:
            if not (0.0 <= m['px'][0] < 600.0 and 0.0 <= m['px'][1] < 400.0):
                m['px'] = _px(int(key), _true_world(int(key), m['px'])); total['off_screen_modules'] += 1

dest = os.path.join(ROOT, 'Content/Dink/Data/Art/structure_sets.json')
json.dump(out, open(dest, 'w'), indent=1)
print('structures: %d screens; %s; skipped %d dressed screens -> %s' % (len(out['screens']), ', '.join('%s %d' % kv for kv in sorted(total.items())), len(SKIP_SCREENS), os.path.relpath(dest, ROOT)))
