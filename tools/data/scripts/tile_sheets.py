"""Render one labelled contact sheet per tileset into tools/data/out/tiles/.

Each 50x50 cell is drawn at SCALE with its cell index (top-left) and its
use count in map.dat (bottom-left, red). Unused cells are dimmed.
Usage: python3 tile_sheets.py [tileset ...]
"""
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw

import dinkdata as d

OUT = os.path.join(d.REPO, 'tools', 'data', 'out', 'tiles')
SCALE = 2


def tile_usage():
    c = Counter()
    for _n, blk, _ in d.iter_screens():
        c.update(d.screen_tiles(blk))
    return c


def tile_image(ts, cell):
    im = Image.open(d.tileset_path(ts)).convert('RGB')
    x, y = (cell % 12) * 50, (cell // 12) * 50
    if x + 50 > im.width or y + 50 > im.height:
        return None
    return im.crop((x, y, x + 50, y + 50))


def sheet(ts, use):
    src = Image.open(d.tileset_path(ts)).convert('RGB')
    S = 50 * SCALE
    W, H = 12 * S, 11 * S
    out = Image.new('RGB', (W, H), (40, 0, 40))
    dr = ImageDraw.Draw(out)
    for cell in range(128):
        x, y = (cell % 12) * 50, (cell // 12) * 50
        ox, oy = (cell % 12) * S, (cell // 12) * S
        n = use.get((ts - 1) * 128 + cell, 0)
        if x + 50 <= src.width and y + 50 <= src.height:
            t = src.crop((x, y, x + 50, y + 50)).resize((S, S), Image.NEAREST)
            if not n:
                t = Image.blend(t, Image.new('RGB', t.size, (0, 0, 0)), 0.7)
            out.paste(t, (ox, oy))
        dr.rectangle([ox, oy, ox + S - 1, oy + S - 1], outline=(255, 0, 0) if n else (90, 90, 90))
        dr.rectangle([ox + 1, oy + 1, ox + 22, oy + 11], fill=(0, 0, 0))
        dr.text((ox + 2, oy + 1), str(cell), fill=(255, 255, 0))
        if n:
            dr.rectangle([ox + 1, oy + S - 12, ox + 34, oy + S - 2], fill=(0, 0, 0))
            dr.text((ox + 2, oy + S - 12), str(n), fill=(255, 80, 80))
    os.makedirs(OUT, exist_ok=True)
    out.save(os.path.join(OUT, 'ts%02d.png' % ts))


def main(argv):
    use = tile_usage()
    used_ts = sorted({d.tile_of(t)[0] for t in use})
    sel = [int(a) for a in argv] or used_ts
    for ts in sel:
        sheet(ts, use)
    print('wrote', len(sel), 'sheets to', OUT)


if __name__ == '__main__':
    main(sys.argv[1:])
