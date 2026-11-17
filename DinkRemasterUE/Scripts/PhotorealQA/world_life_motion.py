#!/usr/bin/env python3
"""Motion maps and sheets of a world-life audit run (Scripts/PhotorealQA/world_life_audit.py).

    python3 -I Scripts/PhotorealQA/world_life_motion.py <out dir> [--sheet-dir=<dir>]

For each screen and pass: the share of pixels that change between frame 0 and frame 2 (about 1.3 s apart) by more
than 6/255 in luma (`moving`), the mean change, the same for the close pair, written to motion.csv; and JPEG sheets of
rows [pass 0 frame | pass 0 motion | pass 1 frame | pass 1 motion] (motion drawn red over a dimmed frame), ten
screens per sheet, plus strips of the interaction captures (walk, demos, fires, barrel, rock)."""
import csv, glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

THRESH = 6.0


def load(path, w=480):
    im = Image.open(path).convert('RGB')
    h = int(im.height * w / im.width)
    return im.resize((w, h), Image.BILINEAR)


def luma(im):
    a = np.asarray(im, dtype=np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def motion(a, b):
    d = np.abs(luma(a) - luma(b))
    return float((d > THRESH).mean()), float(d.mean()), d


def overlay(im, d):
    base = np.asarray(im, dtype=np.float32) * 0.45
    m = np.clip(d / 30.0, 0, 1)[..., None]
    red = np.array([255, 40, 40], dtype=np.float32)
    out = base * (1 - m) + red * m
    return Image.fromarray(out.astype(np.uint8))


def label(im, text):
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, im.width, 14], fill=(0, 0, 0))
    dr.text((3, 1), text, fill=(255, 255, 255))
    return im


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0]
    opt = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    sheets = opt.get('sheet-dir') or os.path.join(out, 'sheets')
    os.makedirs(sheets, exist_ok=True)
    index = json.load(open(os.path.join(out, 'audit_index.json')))
    rows, pics = [], []
    for s in index:
        n = s['screen']
        row = {'screen': n, 'region': s['region'], 'kind': s['kind'], 'name': s['name']}
        tiles = []
        for p in (0, 1):
            f = [os.path.join(out, 'P%d_%03d_%s.png' % (p, n, k)) for k in ('0', '2', 'c0', 'c1')]
            if not all(os.path.exists(x) for x in f):
                row['p%d_moving' % p] = ''
                continue
            a, b, c0, c1 = (load(x) for x in f)
            share, mean, d = motion(a, b)
            cs, cm, _ = motion(c0, c1)
            row.update({'p%d_moving' % p: round(share, 4), 'p%d_mean' % p: round(mean, 3), 'p%d_close_moving' % p: round(cs, 4)})
            tiles += [label(a.copy(), '%03d pass %d %s' % (n, p, s['region'])), label(overlay(a, d), 'moving %.1f%%' % (100 * share))]
        rows.append(row)
        if tiles: pics.append(tiles)
    with open(os.path.join(out, 'motion.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}, key=lambda k: (k not in ('screen', 'region', 'kind', 'name'), k)))
        w.writeheader(); w.writerows(rows)
    for i in range(0, len(pics), 10):
        chunk = pics[i:i + 10]
        tw, th = chunk[0][0].size
        sheet = Image.new('RGB', (tw * 4, th * len(chunk)), (20, 20, 20))
        for r, tiles in enumerate(chunk):
            for c, t in enumerate(tiles[:4]):
                sheet.paste(t, (c * tw, r * th))
        sheet.save(os.path.join(sheets, 'motion_%02d.jpg' % (i // 10)), quality=80)
    # interaction strips
    groups = {}
    for f in sorted(glob.glob(os.path.join(out, '*.png'))):
        b = os.path.basename(f)[:-4]
        if b.startswith('P0_') or b.startswith('P1_'):
            if 'walk' not in b: continue
        key = b.rsplit('_', 1)[0]
        groups.setdefault(key, []).append(f)
    for key, files in groups.items():
        ims = [label(load(f, 400), os.path.basename(f)[:-4]) for f in files[:8]]
        tw, th = ims[0].size
        strip = Image.new('RGB', (tw * min(len(ims), 4), th * ((len(ims) + 3) // 4)), (20, 20, 20))
        for i, im in enumerate(ims):
            strip.paste(im, ((i % 4) * tw, (i // 4) * th))
        strip.save(os.path.join(sheets, 'strip_%s.jpg' % key), quality=80)
    moving0 = [r['p0_moving'] for r in rows if r.get('p0_moving') != '' and 'p0_moving' in r]
    moving1 = [r['p1_moving'] for r in rows if r.get('p1_moving') != '' and 'p1_moving' in r]
    print('%d screens; median moving share pass 0 %.4f, pass 1 %.4f; sheets in %s' % (
        len(rows), float(np.median(moving0)) if moving0 else -1, float(np.median(moving1)) if moving1 else -1, sheets))


if __name__ == '__main__':
    main()
