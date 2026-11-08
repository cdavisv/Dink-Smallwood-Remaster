"""Print the README summary tables (markdown) from the two CSVs."""
import csv
import os
from collections import Counter, defaultdict

DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def rows(name):
    with open(os.path.join(DATA, name), newline='') as f:
        return list(csv.DictReader(f))


def main():
    T, S = rows('tile_classes.csv'), rows('sprite_classes.csv')
    cells, nrow, ntr = Counter(), Counter(), Counter()
    for r in T:
        cells[r['terrain']] += int(r['use_count'])
        nrow[r['terrain']] += 1
        ntr[r['terrain']] += int(r['is_transition'])
    tot = sum(cells.values())
    print('| terrain | tile rows | of which transitions | cells placed | % of world cells |')
    print('|---|---:|---:|---:|---:|')
    for k, v in cells.most_common():
        print('| %s | %d | %d | %d | %.1f |' % (k, nrow[k], ntr[k], v, 100.0 * v / tot))
    print()
    for key in ('category', 'treatment'):
        rc, pc, cc = Counter(), Counter(), defaultdict(set)
        for r in S:
            rc[r[key]] += 1
            pc[r[key]] += int(r['placement_count'])
            cc[r[key]].add(r['class_id'])
        print('| %s | (seq,frame) rows | distinct class_ids | placements |' % key)
        print('|---|---:|---:|---:|')
        for k, v in pc.most_common():
            print('| %s | %d | %d | %d |' % (k, rc[k], len(cc[k]), v))
        print()
    print('| confidence | tile rows | tile cells | sprite rows | placements |')
    print('|---|---:|---:|---:|---:|')
    for c in ('high', 'medium', 'low'):
        print('| %s | %d | %d | %d | %d |' % (
            c, sum(1 for r in T if r['confidence'] == c), sum(int(r['use_count']) for r in T if r['confidence'] == c),
            sum(1 for r in S if r['confidence'] == c),
            sum(int(r['placement_count']) for r in S if r['confidence'] == c)))
    print()
    bk = defaultdict(lambda: [set(), 0, '', ''])
    for r in S:
        if r['treatment'] in ('bespoke', 'modular_kit'):
            e = bk[(r['treatment'], r['family'], r['class_id'])]
            e[0].add('%s.%s' % (r['seq'], r['frame']))
            e[1] += int(r['placement_count'])
            e[2] = r['category']
            e[3] = r['name']
    print('| treatment | family | class_id | category | example name | placements | seq.frame |')
    print('|---|---|---|---|---|---:|---|')
    for k in sorted(bk):
        e = bk[k]
        fr = sorted(e[0], key=lambda s: tuple(int(x) for x in s.split('.')))
        print('| %s | %s | %s | %s | %s | %d | %s |' % (k[0], k[1], k[2], e[2], e[3], e[1], ' '.join(fr)))


if __name__ == '__main__':
    main()
