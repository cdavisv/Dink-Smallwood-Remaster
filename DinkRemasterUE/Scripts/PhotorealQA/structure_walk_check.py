#!/usr/bin/env python3
"""Does a structure set put a solid-looking body on ground the player can walk?
    python3 -I Scripts/PhotorealQA/structure_walk_check.py [--sets <structure_sets.json>] [--out report.txt] [--radius-cm 30] [--plot dir]

The assembled structures (Content/Dink/Data/Art/structure_sets.json) have no collision: the player is stopped by the 1997
hardness (ImportData/collision.json: solid, low, sprite, fill_water, fill_solid; a warp rectangle takes the player away and
counts as closed). For every module that reads as a solid body (house, hut, well, fence, rail; not a bridge deck) this
rasterises its ground footprint at one map pixel, shrinks it by `--core-cm` (default 25: what a shoulder may overlap) and
reports how much of that core lies where the middle of a 30 cm capsule can stand AND can be walked to: the ground
inside a 1997 building outline has hardness 0 but is closed off, so only ground joined to the open ground counts (the
screen and three screens around it are labelled together; a component that reaches the outer edge of that block is open). Owner decision of 14 Nov 2026: what looks
solid at body height must stop the player, and the visual is fitted to the hardness, never the reverse.
Exit code 1 when any set has more than LIMIT_M2 of walkable core. A check of the exported collision, not a walk in the game.
Blind spot: only the part of a footprint that lies on its set's own screen is looked at (a house that stands across a screen
edge is checked on the screen that owns it; the assembler gives a building drawn from several screens to the nearest one)."""
import json, math, os, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'Scripts'))
from export_import_bundle import label_components    # noqa: E402
BLOCKING = ('solid', 'low', 'sprite', 'warp', 'fill_water', 'fill_solid')
LIMIT_M2 = 0.5
# solid ground footprint of a mesh at scale 1, metres, about its pivot: ('rect', x0, y0, x1, y1) (x east, y south at yaw 0) or ('disc', r)
FOOT = {'SM_Cottage_Thatched_Small_PR': ('rect', -3.5, -2.75, 3.5, 2.75), 'SM_Cottage_Thatched_Large_PR': ('rect', -5.0, -3.25, 5.0, 3.25),
        'SM_Cottage_Stonebrook_PR': ('rect', -9.0, -4.5, 9.0, 4.5), 'SM_Cottage_Thatched_TwoStorey_PR': ('rect', -3.3, -3.0, 3.3, 3.0),
        'SM_Cottage_Thatched_LShape_PR': ('rect', -4.65, -3.0, 4.65, 3.0), 'SM_Island_Hut_Round_PR': ('disc', 2.6), 'SM_Island_Hut_TwoStorey_PR': ('disc', 2.6),
        'SM_Well_Stone_PR': ('disc', 0.8), 'SM_Fence_SplitRail_4m_PR': ('rect', -2.0, -0.08, 2.0, 0.08), 'SM_Island_Fence_Lattice_PR': ('rect', -2.2, -0.08, 2.2, 0.08),
        'SM_Castle_Wall_8m': ('rect', -4.0, -0.9, 4.0, 0.9), 'SM_Castle_Tower_Round': ('disc', 3.0), 'SM_Castle_Gatehouse': ('rect', -4.0, -2.5, 4.0, 2.5),
        'SM_Church_PR': ('rect', -10.5, -4.2, 10.5, 4.2), 'SM_Log_Cabin_PR': ('rect', -3.8, -2.25, 3.8, 2.25), 'SM_House_Stonebrook_TwoStorey_01': ('rect', -5.5, -4.25, 5.5, 4.25), 'SM_Woodpile_Split_01': ('rect', -1.1, -0.23, 1.1, 0.23), 'SM_WaterTrough_Oak_01': ('rect', -0.75, -0.33, 0.75, 0.33),
        'SM_ChoppingBlock_Axe_01': ('disc', 0.3), 'SM_Wheelbarrow_Oak_01': ('rect', -0.32, -0.85, 0.32, 0.85), 'SM_HayBale_01': ('rect', -0.56, -0.35, 0.56, 0.35),
        'SM_Bridge_Wood_Rail_Plank_PR': ('rect', -1.25, -0.08, 1.25, 0.08), 'SM_Bridge_Wood_Rail_Rope_PR': ('rect', -1.25, -0.08, 1.25, 0.08)}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def erode(mask, r):
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r or (dx == 0 and dy == 0): continue
            sh = np.zeros_like(mask)
            sh[max(0, -dy):mask.shape[0] + min(0, -dy), max(0, -dx):mask.shape[1] + min(0, -dx)] = mask[max(0, dy):mask.shape[0] + min(0, dy), max(0, dx):mask.shape[1] + min(0, dx)]
            out &= sh
    return out


def footprint(mod, sx, sy, core):
    """bool (400, 600): map pixels whose middle lies in the module's solid footprint shrunk by `core` metres"""
    name = mod['mesh'].split('/')[-1].split('.')[0]; f = FOOT.get(name)
    if f is None: return None
    yy, xx = np.mgrid[0:400, 0:600]
    ox, oy = (mod.get('offset_cm') or [0, 0, 0])[:2]
    dx = (xx + 0.5 - mod['px'][0]) * sx - ox / 100.0; dy = (yy + 0.5 - mod['px'][1]) * sy - oy / 100.0       # metres from the pivot, world axes
    a = math.radians(mod.get('yaw', 0.0)); lx = dx * math.cos(a) + dy * math.sin(a); ly = -dx * math.sin(a) + dy * math.cos(a)
    s = mod.get('scale') or [1, 1, 1]
    if f[0] == 'disc':
        return np.hypot(lx / s[0], ly / s[1]) <= max(0.0, f[1] - core / max(s[0], s[1]))
    x0, x1 = sorted((f[1] * s[0], f[3] * s[0])); y0, y1 = sorted((f[2] * s[1], f[4] * s[1]))        # a mirrored module has a negative scale
    c = min(core, (y1 - y0) / 2 - 0.01, (x1 - x0) / 2 - 0.01) if (y1 - y0) > 0.6 else 0.0     # a fence or rail line is not shrunk
    return (lx >= x0 + c) & (lx <= x1 - c) & (ly >= y0 + c) & (ly <= y1 - c)


def main():
    sets = json.load(open(arg('--sets', os.path.join(ROOT, 'Content/Dink/Data/Art/structure_sets.json'))))['screens']
    radius_cm = float(arg('--radius-cm', 30.0)); core = float(arg('--core-cm', 25.0)) / 100.0; plot = arg('--plot')
    coll = json.load(open(os.path.join(ROOT, 'ImportData/collision.json')))['screens']
    mpp = {}
    for p in json.load(open(os.path.join(ROOT, 'ImportData/placements.json')))['placements']: mpp.setdefault(p['screen'], (p['scale_x'], p['scale_y']))
    for sc in json.load(open(os.path.join(ROOT, 'ImportData/screens.json')))['screens']:          # a screen without placements
        c = sc.get('corners')
        if c: mpp.setdefault(sc['screen'], (math.hypot(c['ne'][0] - c['nw'][0], c['ne'][1] - c['nw'][1]) / 600.0, math.hypot(c['sw'][0] - c['nw'][0], c['sw'][1] - c['nw'][1]) / 400.0))
    lines, bad, tot = [], 0, 0.0
    for key in sorted(sets, key=int):
        n = int(key); row = coll.get('SCR_%03d' % n) or {}; sx, sy = mpp[n]
        r = max(1, int(round(radius_cm / 100.0 / max(sx, sy))))
        R = 3                                                                              # screens around: a castle is four screens wide
        big = np.ones(((2 * R + 1) * 400, (2 * R + 1) * 600), bool)                        # blocked; the screen and its neighbours
        for dr in range(-R, R + 1):
            for dc in range(-R, R + 1):
                c, rw = (n - 1) % 32 + dc, (n - 1) // 32 + dr
                if not (0 <= c < 32 and 0 <= rw < 24): continue
                nb = coll.get('SCR_%03d' % (rw * 32 + c + 1))
                if nb is None: continue                                                    # no such screen: closed
                m = np.zeros((400, 600), bool)
                for k in BLOCKING:
                    for x0, y0, x1, y1 in nb.get(k) or []: m[max(0, y0):y1, max(0, x0):x1] = True
                big[(dr + R) * 400:(dr + R + 1) * 400, (dc + R) * 600:(dc + R + 1) * 600] = m
        mid = (slice(R * 400, (R + 1) * 400), slice(R * 600, (R + 1) * 600))
        block = big[mid]
        lab, _ = label_components(~big)                                                    # open ground: joined to the edge of the block
        edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
        open_ = np.isin(lab, sorted(edge))[R * 400 - 40:(R + 1) * 400 + 40, R * 600 - 40:(R + 1) * 600 + 40]
        stand = erode(open_, r)[40:-40, 40:-40]                                            # where a capsule's middle can be and can get to
        img = None
        if plot:
            img = np.zeros((400, 600, 3), np.uint8); img[...] = (70, 110, 60); img[block] = (40, 40, 40)
        for h in sets[key]['houses']:
            solid = np.zeros((400, 600), bool); known = False
            for m in h['modules']:
                fp = footprint(m, sx, sy, core)
                if fp is not None: solid |= fp; known = True
            if not known: continue
            area = solid.sum() * sx * sy; walk = (solid & stand).sum() * sx * sy; tot += walk
            if img is not None:
                img[solid & ~stand] = (150, 150, 200); img[solid & stand] = (255, 40, 40)
            flag = 'WALKABLE' if walk > LIMIT_M2 else 'ok'
            bad += walk > LIMIT_M2
            lines.append('%-22s %-8s solid core %6.1f m2, of it walkable %6.1f m2  %s' % (h['id'], h['kind'], area, walk, flag))
        if img is not None:
            from PIL import Image
            os.makedirs(plot, exist_ok=True); Image.fromarray(img).resize((1200, 800), Image.NEAREST).save(os.path.join(plot, 'SCR_%03d.png' % n))
    lines.append('%d sets with more than %.1f m2 of solid-looking core on ground the player can stand on; %.1f m2 in all' % (bad, LIMIT_M2, tot))
    text = '\n'.join(lines)
    print(text)
    if arg('--out'): open(arg('--out'), 'w').write(text + '\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
