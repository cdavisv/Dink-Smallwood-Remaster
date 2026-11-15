#!/usr/bin/env python3
"""Sheets of the ground relief captures (relief_script.py):
    python3 -I Scripts/PhotorealQA/relief_sheet.py <capture dir> <out dir> [--crop=0.5]

One JPEG per screen (relief_NNN.jpg): one row per relief scale (the upper row is the flat sheet), the columns are
the play camera, the feet, the close view and the grazing view. --crop=f also writes relief_NNN_detail.jpg: the
middle f of the close and grazing views at full capture resolution, flat left and relief right. Needs Pillow."""
import json, os, sys
from PIL import Image, ImageDraw

CELL = (640, 360)
VIEWS = ('play', 'feet', 'close', 'low')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src, out = (os.path.abspath(a) for a in args[:2]); os.makedirs(out, exist_ok=True)
    crop = next((float(a.split('=', 1)[1]) for a in sys.argv[1:] if a.startswith('--crop=')), 0.0)
    index = json.load(open(os.path.join(src, 'relief_index.json')))
    tags = ['%03d' % round(s * 100) for s in index['scales']]
    for rec in index['screens']:
        n = rec['screen']
        sheet = Image.new('RGB', (CELL[0] * len(VIEWS), (CELL[1] + 20) * len(tags)), (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for r, tag in enumerate(tags):
            draw.text((6, r * (CELL[1] + 20) + 4), 'screen %d  %s  relief scale %.2f  (%s)' % (n, 'indoor' if rec['indoor'] else 'outdoor', int(tag) / 100.0, ', '.join(rec['layers'])), fill=(240, 240, 240))
            for c, kind in enumerate(VIEWS):
                f = os.path.join(src, '%03d_%s_%s.png' % (n, kind, tag))
                if os.path.isfile(f): sheet.paste(Image.open(f).convert('RGB').resize(CELL, Image.LANCZOS), (c * CELL[0], r * (CELL[1] + 20) + 20))
        sheet.save(os.path.join(out, 'relief_%03d.jpg' % n), quality=88)
        if crop > 0.0 and len(tags) >= 2:
            cells = []
            for kind in ('close', 'low'):
                for tag in (tags[0], tags[-1]):
                    f = os.path.join(src, '%03d_%s_%s.png' % (n, kind, tag))
                    if not os.path.isfile(f): continue
                    im = Image.open(f).convert('RGB'); w, h = im.size
                    cw, ch = int(w * crop), int(h * crop)
                    cells.append(im.crop(((w - cw) // 2, (h - ch) // 2 + h // 8, (w - cw) // 2 + cw, (h - ch) // 2 + h // 8 + ch)))
            if cells:
                cw, ch = cells[0].size
                detail = Image.new('RGB', (cw * 2, ch * ((len(cells) + 1) // 2)), (24, 24, 24))
                for i, im in enumerate(cells): detail.paste(im, ((i % 2) * cw, (i // 2) * ch))
                detail.save(os.path.join(out, 'relief_%03d_detail.jpg' % n), quality=90)
    print('%d sheets -> %s' % (len(index['screens']), out))


if __name__ == '__main__':
    main()
