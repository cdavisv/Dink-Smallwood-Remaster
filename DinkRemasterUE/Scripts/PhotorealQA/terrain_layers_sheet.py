#!/usr/bin/env python3
"""Before/after sheets of Scripts/PhotorealQA/terrain_layers_script.py captures:

    python3 -I Scripts/PhotorealQA/terrain_layers_sheet.py <before dir> <after dir> <out dir>

One JPEG per screen (terrain_NNN.jpg: play, over and top views; before above, after below) and per border
(terrain_border_A_B.jpg: play and over views). Needs Pillow."""
import os
import re
import sys

from PIL import Image, ImageDraw

CELL = (640, 360)


def cell(path, label):
    im = Image.new('RGB', CELL, (40, 40, 40))
    if os.path.exists(path):
        im.paste(Image.open(path).convert('RGB').resize(CELL, Image.LANCZOS))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 + 7 * len(label), 16), fill=(0, 0, 0))
    d.text((4, 2), label, fill=(255, 255, 255))
    return im


def sheet(before, after, stem, views, out):
    im = Image.new('RGB', (CELL[0] * len(views), CELL[1] * 2), (0, 0, 0))
    for i, v in enumerate(views):
        im.paste(cell(os.path.join(before, '%s_%s.png' % (stem, v)), 'before (master) %s %s' % (stem, v)), (i * CELL[0], 0))
        im.paste(cell(os.path.join(after, '%s_%s.png' % (stem, v)), 'after (natural outlines) %s %s' % (stem, v)), (i * CELL[0], CELL[1]))
    im.save(out, quality=82)


def main():
    before, after, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    names = sorted(set(re.sub(r'_(play|over|top)\.png$', '', f) for f in os.listdir(after) if f.endswith('.png')))
    for stem in names:
        if stem.startswith('border_'):
            sheet(before, after, stem, ('play', 'over'), os.path.join(out, 'terrain_%s.jpg' % stem))
        else:
            sheet(before, after, stem, ('play', 'over', 'top'), os.path.join(out, 'terrain_%s.jpg' % stem))
    print('%d sheets -> %s' % (len(names), out))


if __name__ == '__main__':
    main()
