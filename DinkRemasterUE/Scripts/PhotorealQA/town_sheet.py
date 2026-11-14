#!/usr/bin/env python3
"""Review sheets of the town-house captures: python3 -I Scripts/PhotorealQA/town_sheet.py <on dir> <off dir> <out dir>

One JPEG per screen (town_<screen>.jpg): the sprite cards (dink.TownHouses 0) beside the assembled houses (1) at the
play camera and from above the south edge, and the houses from above the north edge. Needs Pillow."""
import glob, os, re, sys
from PIL import Image, ImageDraw

CELL = (640, 360)


def main():
    on, off, out = (os.path.abspath(a) for a in sys.argv[1:4])
    os.makedirs(out, exist_ok=True)
    screens = sorted({int(re.match(r'(\d+)_', os.path.basename(f)).group(1)) for f in glob.glob(os.path.join(on, '*_play.png'))})
    for s in screens:
        cells = [('sprite cards, play camera', off, 'play'), ('houses, play camera', on, 'play'),
                 ('sprite cards, from the south', off, 'south'), ('houses, from the south', on, 'south'),
                 ('sprite cards, from the north', off, 'north'), ('houses, from the north', on, 'north')]
        sheet = Image.new('RGB', (CELL[0] * 2, (CELL[1] + 22) * 3), (24, 24, 24)); d = ImageDraw.Draw(sheet)
        for i, (label, folder, kind) in enumerate(cells):
            x, y = (i % 2) * CELL[0], (i // 2) * (CELL[1] + 22)
            d.text((x + 6, y + 5), 'screen %d: %s' % (s, label), fill=(235, 235, 235))
            f = os.path.join(folder, '%03d_%s.png' % (s, kind))
            if os.path.isfile(f): sheet.paste(Image.open(f).convert('RGB').resize(CELL, Image.LANCZOS), (x, y + 22))
        sheet.save(os.path.join(out, 'town_%03d.jpg' % s), quality=86)
    print('%d sheets -> %s' % (len(screens), out))


if __name__ == '__main__':
    main()
