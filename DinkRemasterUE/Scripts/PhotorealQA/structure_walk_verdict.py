#!/usr/bin/env python3
"""Verdict of a `dink.WalkAudit` run for the structure sets: which set meshes can the player walk into in the game?

    python3 -I Scripts/PhotorealQA/structure_walk_verdict.py <audit dir> [<project dir>]

Reads walk_audit.csv and walk_mask.csv of the audit (the whole outdoor map, e.g. `dink.WalkAudit 187 766 <dir> quit`) and
Content/Dink/Data/Art/structure_sets.json. A walk-in of a set mesh (the capsule 30 cm or more inside its body-height
footprint) counts only where its deepest standing point lies on ground the player can reach: the walk masks of the
outdoor screens are stitched into the 32 x 24 world, warp rectangles closed (a warp takes the player away), and a free
area under 100,000 px (0.4 screen) is the closed ground inside a 1997 building outline. The castle gatehouse's doorway is
meant to be walked into (the castle door's warp stands in it). Complements structure_walk_check.py, which checks the same
offline against the 1997 hardness; this one found what that cannot see: houses the runtime drew a second time beside
themselves, and straight wall runs across the notches of the outline. Exit 1 when anything but the gatehouse is listed."""
import csv, json, sys, collections
import numpy as np
from pathlib import Path
D = Path(sys.argv[1])
PC = sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve().parents[2])
sys.path.insert(0, PC + '/Scripts')
import check_player_blockers as cb
masks = cb.load_masks(D)
from export_import_bundle import label_components
S = 3                                              # the audit's mask cell, px
gw, gh = 600 // S, (400 + S - 1) // S
world = np.zeros((24 * gh, 32 * gw), bool)
COLLISION = json.load(open(PC + '/ImportData/collision.json'))
COLLISION = COLLISION.get('screens', COLLISION)
screens = {q['screen']: q for q in json.load(open(PC + '/ImportData/screens.json'))['screens']}
for n, m in masks.items():
    c, r = (n - 1) % 32, (n - 1) // 32
    if screens.get(n, {}).get('indoor'): continue          # an interior's slot in the 32 x 24 grid is not its place in the world
    m = m.copy()
    for kind in ('warps', 'warp', 'door_warps'):       # a warp takes the player away: he never walks through its rectangle
        for x0, y0, x1, y1 in (COLLISION.get('SCR_%03d' % n) or {}).get(kind) or []:
            m[max(0, y0):y1, max(0, x0):x1] = False
    if r < 24: world[r * gh:r * gh + (m[::S, ::S].shape[0]), c * gw:(c + 1) * gw] = m[::S, ::S]
lab, k = label_components(world)
sizes = np.bincount(lab.ravel()); big = sizes >= 100000 // (S * S); big[0] = False
sets = json.load(open(PC + '/Content/Dink/Data/Art/structure_sets.json'))['screens']
meshes = {m['mesh'].split('/')[-1].split('.')[0] for v in sets.values() for h in v['houses'] for m in h['modules']}
rows = [r for r in csv.DictReader(open(D / 'walk_audit.csv')) if r['mesh'].split('/')[-1].split('.')[0] in meshes and r['screen'] in sets]
real, closed, shallow = [], 0, 0
for r in rows:
    n = int(r['screen']); a = int(r['allowed']); d = float(r['depth_cm'])
    if a == 0 or d < 30: shallow += 1; continue
    c, rr = (n - 1) % 32, (n - 1) // 32
    x, y = int(round(float(r['deepest_px_x']))), int(round(float(r['deepest_px_y'])))
    gx, gy = c * gw + min(599, max(0, x)) // S, rr * gh + min(399, max(0, y)) // S
    win = lab[max(0, gy - 1):gy + 2, max(0, gx - 1):gx + 2]
    comp = int(sizes[win].max()) * S * S
    if big[win].any(): real.append((d, n, r['mesh'].split('.')[-1], a, int(r['tested']), x, y, comp))
    else: closed += 1
print('structure-set mesh rows on set screens:', len(rows), '| no walk-in of 30 cm:', shallow, '| deepest point on closed ground:', closed, '| on reachable ground:', len(real))
print(dict(collections.Counter(x[2] for x in real)))
for x in sorted(real, reverse=True)[:60]: print('  depth %.0f cm  screen %d  %s  standable cells %d of %d  at px %d,%d  free area %d px' % x)
sys.exit(1 if any('Gatehouse' not in x[2] and x[0] >= 50 for x in real) else 0)
