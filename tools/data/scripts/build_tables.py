"""Merge machine-derived usage (scan_map.py) with the hand labels
(tile_labels.py, sprite_labels.py) into the two deliverable tables:

  tools/data/tile_classes.csv
  tools/data/sprite_classes.csv

Usage: python3 build_tables.py   (runs scan_map first)
"""
import csv
import os
import sys

import dinkdata as d
import scan_map
import sprite_labels
import tile_labels

DATA = os.path.join(d.REPO, 'tools', 'data')

TILE_COLS = ['tile_num', 'tileset', 'cell', 'use_count', 'screen_count', 'indoor_use', 'terrain',
             'is_transition', 'blend_classes', 'walkable_hint', 'animated', 'hard_solid_pct', 'hard_low_pct',
             'confidence', 'notes']
SPRITE_COLS = ['seq', 'frame', 'placement_count', 'type0_background', 'type1_live', 'type2_hardness_only',
               'screen_count', 'source_file', 'pixel_size', 'class_id', 'category', 'name', 'family',
               'treatment', 'original_view', 'gameplay_flags', 'script_flags', 'scripts', 'warp_count',
               'confidence', 'notes', 'example_screens']


def build_tiles():
    rows = []
    for u in scan_map.scan_tiles():
        lab = tile_labels.label(u['tile_num'])
        if lab is None:
            raise SystemExit('no tile label for %d' % u['tile_num'])
        terr, other = lab['terrain'], lab['transition']
        walk = tile_labels.TERRAIN[terr][0]
        if other:
            w2 = tile_labels.TERRAIN[other][0]
            if w2 != walk:
                walk = 'partial'
        rows.append({
            'tile_num': u['tile_num'], 'tileset': u['tileset'], 'cell': u['cell'],
            'use_count': u['use_count'], 'screen_count': u['screen_count'], 'indoor_use': u['indoor_use'],
            'terrain': terr, 'is_transition': 1 if other else 0,
            'blend_classes': ('%s|%s' % (terr, other)) if other else '',
            'walkable_hint': walk, 'animated': u['animated'],
            'hard_solid_pct': u['hard_solid_pct'], 'hard_low_pct': u['hard_low_pct'],
            'confidence': lab['confidence'], 'notes': lab['notes'],
        })
    return rows


def build_sprites():
    usage, _ = scan_map.scan_sprites()
    rows = []
    for u in usage:
        s, f = int(u['seq']), int(u['frame'])
        lab = sprite_labels.label(s, f)
        if lab is None:
            raise SystemExit('no sprite label for %d.%d' % (s, f))
        rows.append({
            'seq': s, 'frame': f, 'placement_count': u['placement_count'],
            'type0_background': u['type0_background'], 'type1_live': u['type1_live'],
            'type2_hardness_only': u['type2_hardness_only'], 'screen_count': u['screen_count'],
            'source_file': u['source_file'], 'pixel_size': u['pixel_size'],
            'class_id': lab['class_id'], 'category': lab['category'], 'name': lab['name'],
            'family': lab['family'], 'treatment': lab['treatment'], 'original_view': lab['view'],
            'gameplay_flags': lab['flags'], 'script_flags': u['script_flags'], 'scripts': u['scripts'],
            'warp_count': u['warp_count'], 'confidence': lab['confidence'], 'notes': lab['notes'],
            'example_screens': u['example_screens'],
        })
    return rows


def write(path, cols, rows):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main():
    t = build_tiles()
    write(os.path.join(DATA, 'tile_classes.csv'), TILE_COLS, t)
    s = build_sprites()
    write(os.path.join(DATA, 'sprite_classes.csv'), SPRITE_COLS, s)
    print('tile_classes.csv: %d rows, %d tile cells' % (len(t), sum(r['use_count'] for r in t)))
    print('sprite_classes.csv: %d rows, %d placements' % (len(s), sum(r['placement_count'] for r in s)))


if __name__ == '__main__':
    sys.exit(main())
