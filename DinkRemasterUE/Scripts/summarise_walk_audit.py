#!/usr/bin/env python3
"""Summarise dink.WalkAudit output (walk_audit.csv, walk_walls.csv under a folder) into ranked walk-through and invisible-wall lists.

    python3 Scripts/summarise_walk_audit.py <audit dir> [min depth cm, default 20]
"""
import csv, sys, glob, os, collections

SOLID = ['boulder', 'rock', 'stone', 'stump', 'trunk', 'tree', 'pine', 'oak', 'willow', 'dead', 'fence', 'wall', 'barrel', 'chest',
         'table', 'chair', 'bed', 'bench', 'cabinet', 'statue', 'pillar', 'monument', 'gravestone', 'fountain', 'house', 'cottage',
         'idol', 'post', 'log', 'cliff', 'crate', 'well', 'fireplace', 'shelf', 'pot', 'urn', 'anvil', 'cart', 'altar', 'throne', 'column']
SOFT = ['grass', 'flower', 'fern', 'bush', 'shrub', 'reed', 'weed', 'leaf', 'moss', 'puddle', 'blood', 'decal', 'card', 'rug', 'carpet',
        'mushroom', 'ivy', 'vine', 'pebble', 'gravel', 'straw', 'hay', 'bone', 'skull', 'corpse', 'sign', 'lamp', 'candle', 'torch',
        'window', 'curtain', 'flame', 'smoke', 'roof', 'ceiling', 'beam']

def cls(mesh):
    m = mesh.lower().split('/')[-1]
    if any(k in m for k in SOFT): return 'soft'
    if any(k in m for k in SOLID): return 'solid'
    return 'other'

def main(d, thr=20.0):
    rows = []
    for f in sorted(glob.glob(os.path.join(d, '*/walk_audit.csv'))) + sorted(glob.glob(os.path.join(d, 'walk_audit.csv'))):
        rows += list(csv.DictReader(open(f)))
    walls = []
    for f in sorted(glob.glob(os.path.join(d, '*/walk_walls.csv'))) + sorted(glob.glob(os.path.join(d, 'walk_walls.csv'))):
        walls += list(csv.DictReader(open(f)))
    screens = sorted({int(r['screen']) for r in rows})
    print(f'# rows {len(rows)} on {len(screens)} screens; walls rows {len(walls)}')
    items = [r for r in rows if r['kind'] != 'card']
    for r in items:
        r['cls'] = cls(r['mesh'])
        r['depth'] = float(r['depth_cm'])
    bad = [r for r in items if r['depth'] >= thr and r['cls'] != 'soft']
    print(f'# non-card items {len(items)}; walk-in >= {thr} cm (not soft): {len(bad)}')
    by = collections.defaultdict(list)
    for r in bad: by[(r['kind'], r['mesh'].split('.')[-1])].append(r)
    print('\n## by mesh (count, max depth, screens)')
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f'{len(v):5d} {max(x["depth"] for x in v):6.0f} {k[0]:16s} {k[1]:40s} {cls(k[1])} ' +
              ' '.join(sorted({x["screen"] for x in v}, key=int)[:12]))
    print('\n## worst 60')
    for r in sorted(bad, key=lambda r: -r['depth'])[:60]:
        print(f'SCR_{int(r["screen"]):03d} {r["kind"]:15s} {r["origin"] or r["actor"]+"#"+r["instance"]:28s} {r["mesh"].split(".")[-1]:36s} '
              f'depth {r["depth"]:5.0f} allowed {r["allowed"]}/{r["tested"]} fp {float(r["footprint_m2"]):.2f} m2 at px {r["deepest_px_x"]},{r["deepest_px_y"]} hard {r["hard_at_deepest"]}/{r["hard_at_centre"]} bbox {r["bounds_only"]}')
    bw = [w for w in walls if int(w['bare_pixels']) > 0.5 * int(w['pixels']) and int(w['pixels']) >= 40]
    print(f'\n## hardboxes with > half the pixels {">"} 40 cm from anything drawn: {len(bw)} of {len(walls)}')
    for w in sorted(bw, key=lambda w: -int(w['bare_pixels']))[:60]:
        print(f'SCR_{int(w["screen"]):03d} P{int(w["placement"]):02d} px {w["pixels"]} bare {w["bare_pixels"]} max {float(w["max_distance_cm"]):.0f} cm box {w["min_px_x"]},{w["min_px_y"]}-{w["max_px_x"]},{w["max_px_y"]}')

if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 20.0)
