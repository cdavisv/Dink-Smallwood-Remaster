#!/usr/bin/env python3
"""ShadowDepths and GPU totals of the twelve csvprofile captures of a world-life audit (312, 438, 650 x Epic/High x layer off/on).

    python3 -I Scripts/PhotorealQA/world_life_gpu.py <project>/Saved/Profiling/CSV [--since=<unix time>]

Takes the twelve newest CSV files (written in the audit's order: per screen Epic off, Epic on, High off, High on) and prints the mean
ms of every GPU pass whose name holds Shadow, plus FrameTime and the GPU total, per capture."""
import csv, glob, os, sys

LABELS = ['%03d %s, dink.World.Life %d' % (n, q, l) for n in (312, 438, 650) for q in ('Epic', 'High') for l in (0, 1)]


def mean_columns(path):
    rows = list(csv.reader(open(path, encoding='utf-8', errors='replace')))
    if len(rows) < 3: return {}, 0
    head = rows[0]
    data = [r for r in rows[1:] if len(r) == len(head) and r != head and not r[0].startswith('[')]
    out = {}
    for i, name in enumerate(head):
        vals = []
        for r in data:
            try: vals.append(float(r[i]))
            except ValueError: pass
        if vals: out[name] = sum(vals) / len(vals)
    return out, len(data)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opt = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    since = float(opt.get('since') or 0)
    files = sorted((f for f in glob.glob(os.path.join(args[0], '*.csv')) if os.path.getmtime(f) >= since), key=os.path.getmtime)[-len(LABELS):]
    for label, f in zip(LABELS, files):
        cols, n = mean_columns(f)
        keys = [k for k in cols if 'Shadow' in k and k.startswith('GPU/')] + [k for k in ('FrameTime', 'GPU/Total', 'GPUTime') if k in cols]
        print('%-26s %4d frames  ' % (label, n) + '  '.join('%s %.2f' % (k, cols[k]) for k in keys) + '  (%s)' % os.path.basename(f))
    if len(files) < len(LABELS): print('only %d CSV files found' % len(files)); return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
