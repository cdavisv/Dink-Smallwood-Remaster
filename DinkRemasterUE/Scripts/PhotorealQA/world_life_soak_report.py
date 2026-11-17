#!/usr/bin/env python3
"""Reads the DINK WORLD lines of a world-life soak (Scripts/PhotorealQA/world_life_audit.py --soak) from a game log.

    python3 -I Scripts/PhotorealQA/world_life_soak_report.py <game log> [--out=<csv>]

Prints: duration, the most particles / lights at once, the last non-finite count (must stay 0), the actor count at the
start and end of every lap screen visit (a world-life leak would make it grow lap over lap) and the layer's CPU ms
(mean, 95th percentile, max). Exit 1 when non-finite > 0, or the actors on the same screen grow by more than 5 between
the first and the last visit, or the log has no DINK WORLD line."""
import csv, re, sys

LINE = re.compile(r'DINK WORLD: screen (-?\d+) region (\S+) wind ([\d.]+) dir (-?[\d.]+) gust ([\d.]+) \| particles (\d+) lights (\d+) '
                  r'emitted (\d+) nonfinite (\d+) chimneys (\d+) fires (\d+) rigidshadows (\d+) \| actors (\d+) \| tick ([\d.]+) ms')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opt = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    rows = []
    for line in open(args[0], errors='replace'):
        m = LINE.search(line)
        if m:
            g = m.groups()
            rows.append({'screen': int(g[0]), 'region': g[1], 'wind': float(g[2]), 'particles': int(g[5]), 'lights': int(g[6]),
                         'emitted': int(g[7]), 'nonfinite': int(g[8]), 'rigid': int(g[11]), 'actors': int(g[12]), 'tick_ms': float(g[13])})
    if not rows:
        print('no DINK WORLD lines'); return 1
    if opt.get('out'):
        with open(opt['out'], 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    ticks = sorted(r['tick_ms'] for r in rows)
    p95 = ticks[min(len(ticks) - 1, int(0.95 * len(ticks)))]
    first, last = {}, {}
    for r in rows:
        first.setdefault(r['screen'], r['actors']); last[r['screen']] = r['actors']
    growth = {s: last[s] - first[s] for s in first}
    worst = max(growth.values()) if growth else 0
    nonfinite = rows[-1]['nonfinite']
    print('lines %d (~%d s) | particles max %d | lights max %d | emitted %d | nonfinite %d | layer tick mean %.3f ms p95 %.3f max %.3f'
          % (len(rows), 2 * len(rows), max(r['particles'] for r in rows), max(r['lights'] for r in rows), rows[-1]['emitted'], nonfinite,
             sum(ticks) / len(ticks), p95, ticks[-1]))
    print('actors per screen, first -> last visit: ' + ', '.join('%d: %d -> %d' % (s, first[s], last[s]) for s in sorted(first)))
    ok = nonfinite == 0 and worst <= 5
    print('SOAK %s' % ('OK' if ok else 'FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
