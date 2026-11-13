#!/usr/bin/env python3
"""Per-placement table of the town-house kit (sprite family 33):
    python3 -I Scripts/PhotorealQA/town_table.py <out.csv>     (after python3 -I Scripts/art_coverage.py)

One row per placement of sequence 33 in Content/Dink/Data/Gameplay/placements.csv: what the greybox drew it as
(actor card or decor instance, from Saved/Import/coverage.csv), whether town_houses.json hides it on its own screen,
the house and building that stand for it, the distance to the nearest house body when none covers where it stood,
and the audit's state. Prints the totals per class."""
import collections, csv, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLASS = {7: 'town_wall_gable_end', 10: 'town_wall_gable_end', 24: 'town_wall_gable_end', 8: 'town_roof_ridge_cap', 25: 'town_roof_ridge_cap',
         9: 'town_roof_slope', 26: 'town_roof_slope', 27: 'town_roof_slope', 12: 'town_roof_flat', 29: 'town_roof_flat', 30: 'town_roof_flat',
         13: 'town_roof_dormer', 31: 'town_roof_dormer', 32: 'town_roof_dormer'}


def main():
    town = json.load(open(os.path.join(ROOT, 'Content/Dink/Data/Art/town_houses.json')))
    building = {h: b['id'] for b in town.get('buildings', []) for h in b['houses']}
    hidden, stands, gap = {}, {}, {}
    for s, row in town['screens'].items():
        for h in row['houses']:
            for o in h.get('hide') or []: hidden[o] = int(s)
        stands.update(row.get('stands_for') or {}); gap.update(row.get('uncovered_m') or {})
    became = {r['origin_id']: r for r in csv.DictReader(open(os.path.join(ROOT, 'Saved/Import/coverage.csv'), newline='', encoding='utf-8')) if r['type'] == 'placement'}
    audit = {r['origin_id']: r for r in csv.DictReader(open(os.path.join(ROOT, 'Saved/Import/art_coverage.csv'), newline='', encoding='utf-8')) if r['type'] == 'placement'}
    rows, totals = [], collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(os.path.join(ROOT, 'Content/Dink/Data/Gameplay/placements.csv'), newline='', encoding='utf-8')):
        if r['seq'] != '33': continue
        o, frame = r['origin'], int(r['frame'])
        cls = audit.get(o, {}).get('evidence', '')
        name = CLASS.get(frame) or ('town_wall_stone_door' if frame in (3, 5, 6, 21, 23, 33, 34, 38, 39) else 'town_wall_stone_window')
        state = audit.get(o, {}).get('state', 'missing')
        rows.append({'origin': o, 'screen': r['screen'], 'class': name, 'frame': frame,
                     'greybox': 'actor card' if became.get(o, {}).get('became', '').startswith('actor') else 'decor instance',
                     'card_hidden_on_its_screen': 'yes' if hidden.get(o) == int(r['screen']) else 'no', 'house': stands.get(o, ''), 'building': building.get(stands.get(o, ''), ''),
                     'house_body_covers_it': 'no, nearest %.1f m' % gap[o] if o in gap else 'yes', 'audit_state': state})
        totals[name][state] += 1
    with open(sys.argv[1], 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); w.writeheader(); w.writerows(rows)
    print('%d placements -> %s' % (len(rows), sys.argv[1]))
    for name in sorted(totals): print('  %-24s final %3d  placeholder %3d' % (name, totals[name]['final'], totals[name]['placeholder']))
    print('  %-24s final %3d  placeholder %3d' % ('all', sum(t['final'] for t in totals.values()), sum(t['placeholder'] for t in totals.values())))


if __name__ == '__main__':
    main()
