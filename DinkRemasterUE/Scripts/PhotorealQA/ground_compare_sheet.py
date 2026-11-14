#!/usr/bin/env python3
"""Before/after sheets of the screen-ground captures:
    python3 -I Scripts/PhotorealQA/ground_compare_sheet.py <before dir> <after dir> <out dir> [--screens=a,b]

Both folders hold the NNN_play / NNN_close / NNN_above PNGs of ground_script.py; the after folder's ground_index.json
labels the rows. One JPEG per screen (ground_NNN.jpg): the upper row is before, the lower row after, three views each.
A screen without a before capture gets the after row only. Needs Pillow."""
import json, os, sys
from PIL import Image, ImageDraw

CELL = (640, 360)
VIEWS = ('play', 'close', 'above')


def row(folder, screen, label):
    img = Image.new('RGB', (CELL[0] * 3, CELL[1] + 20), (24, 24, 24))
    ImageDraw.Draw(img).text((6, 4), label, fill=(240, 240, 240))
    for i, kind in enumerate(VIEWS):
        f = os.path.join(folder, '%03d_%s.png' % (screen, kind))
        if os.path.isfile(f): img.paste(Image.open(f).convert('RGB').resize(CELL, Image.LANCZOS), (i * CELL[0], 20))
    return img


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    before, after, out = (os.path.abspath(a) for a in args[:3]); os.makedirs(out, exist_ok=True)
    only = next((set(int(n) for n in a.split('=', 1)[1].split(',')) for a in sys.argv[1:] if a.startswith('--screens=')), None)
    made = 0
    for rec in json.load(open(os.path.join(after, 'ground_index.json'))):
        n = rec['screen']
        if (only and n not in only) or not os.path.isfile(os.path.join(after, '%03d_play.png' % n)): continue
        classes = ', '.join('%s %d' % kv for kv in sorted(rec['classes'].items(), key=lambda kv: -kv[1]))
        rows = []
        if os.path.isfile(os.path.join(before, '%03d_play.png' % n)):
            rows.append(row(before, n, 'screen %d BEFORE (%s): %s' % (n, rec['region'], classes)))
        rows.append(row(after, n, 'screen %d AFTER: layers %s   (play camera | 1.1 m above the ground | from above the south edge)' % (n, ', '.join(rec['layers']))))
        sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)), (24, 24, 24)); y = 0
        for r in rows: sheet.paste(r, (0, y)); y += r.height
        sheet.save(os.path.join(out, 'ground_%03d.jpg' % n), quality=84); made += 1
    print('%d sheets -> %s' % (made, out))


if __name__ == '__main__':
    main()
