#!/usr/bin/env python3
"""Frame timings of a rendering_set.py capture as a Markdown table (one row per frame, one column group per variant).

    python3 -I Scripts/PhotorealQA/rendering_table.py <capture.log> [--csv out.csv]

Reads the `DINK CAPTURE: fps <variant>/<frame> <fps> (...) game <ms> render <ms> gpu <ms> (max <ms>)` lines."""
import re, sys
from collections import OrderedDict

LINE = re.compile(r'DINK CAPTURE: fps (\S+)/(\S+) ([\d.]+) \((\d+) frames in ([\d.]+)s\) game ([\d.]+) ms render ([\d.]+) ms gpu ([\d.]+) ms \(max ([\d.]+)\)')


def main():
    log = sys.argv[1]
    rows, variants = OrderedDict(), []
    for line in open(log, errors='replace'):
        m = LINE.search(line)
        if not m: continue
        v, f = m.group(1), m.group(2)
        if v not in variants: variants.append(v)
        rows.setdefault(f, {})[v] = dict(fps=float(m.group(3)), game=float(m.group(6)), render=float(m.group(7)), gpu=float(m.group(8)), gpumax=float(m.group(9)))
    head = '| frame | ' + ' | '.join('%s GPU ms | %s fps' % (v, v) for v in variants) + ' |'
    print(head); print('|' + '---|' * (1 + 2 * len(variants)))
    sums = {v: [0.0, 0] for v in variants}
    for f, per in rows.items():
        cells = []
        for v in variants:
            r = per.get(v)
            cells += ['%.2f' % r['gpu'], '%.0f' % r['fps']] if r else ['', '']
            if r: sums[v][0] += r['gpu']; sums[v][1] += 1
        print('| %s | %s |' % (f, ' | '.join(cells)))
    print('| **mean** | ' + ' | '.join('**%.2f** | ' % (sums[v][0] / max(1, sums[v][1])) for v in variants) + '|')
    if '--csv' in sys.argv:
        with open(sys.argv[sys.argv.index('--csv') + 1], 'w') as o:
            o.write('frame,variant,fps,game_ms,render_ms,gpu_ms,gpu_max_ms\n')
            for f, per in rows.items():
                for v, r in per.items(): o.write('%s,%s,%.1f,%.2f,%.2f,%.2f,%.2f\n' % (f, v, r['fps'], r['game'], r['render'], r['gpu'], r['gpumax']))


if __name__ == '__main__':
    main()
