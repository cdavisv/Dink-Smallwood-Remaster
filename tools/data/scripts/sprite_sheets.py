"""Labelled contact sheets of every placed (seq, frame) into out/sprites/.

Each frame is drawn on a grey checker (colour key already transparent) with
'seq.frame', placement count and pixel size underneath. Frames wider or taller
than MAXDIM are scaled down (marked with '~').
Usage: python3 sprite_sheets.py [seq ...]   (default: all placed seqs, packed)
"""
import csv
import os
import sys

from PIL import Image, ImageDraw

import dinkdata as d

OUT = os.path.join(d.REPO, 'tools', 'data', 'out', 'sprites')
USAGE = os.path.join(d.REPO, 'tools', 'data', 'out', 'sprite_usage.csv')
W, H, MAXDIM = 1500, 1100, 360


def checker(w, h):
    im = Image.new('RGB', (w, h), (110, 110, 120))
    dr = ImageDraw.Draw(im)
    for y in range(0, h, 10):
        for x in range(0, w, 10):
            if (x // 10 + y // 10) % 2:
                dr.rectangle([x, y, x + 9, y + 9], fill=(130, 130, 140))
    return im


def tiles_for(pairs, counts, seqs):
    out = []
    for seq, frame in pairs:
        im, _ = d.load_frame_rgba(seqs, seq, frame)
        if im is None:
            im = Image.new('RGBA', (40, 40), (255, 0, 255, 255))
        w, h = im.size
        scaled = ''
        if max(w, h) > MAXDIM:
            f = MAXDIM / max(w, h)
            im = im.resize((max(1, int(w * f)), max(1, int(h * f))), Image.LANCZOS)
            scaled = '~'
        cw, ch = max(im.width, 90), im.height + 26
        cell = checker(cw, ch)
        cell.paste(im, (0, 0), im)
        dr = ImageDraw.Draw(cell)
        dr.rectangle([0, ch - 26, cw, ch], fill=(0, 0, 0))
        dr.text((2, ch - 25), '%d.%d n=%d' % (seq, frame, counts.get((seq, frame), 0)), fill=(255, 255, 0))
        dr.text((2, ch - 13), '%s%dx%d' % (scaled, w, h), fill=(200, 200, 200))
        out.append(cell)
    return out


def pack(cells, name):
    sheets = []
    cur = []
    x = y = rowh = 0
    for c in cells:
        if x + c.width > W:
            x, y, rowh = 0, y + rowh + 4, 0
        if y + c.height > H and cur:
            sheets.append(cur)
            cur, x, y, rowh = [], 0, 0, 0
        cur.append((x, y, c))
        x += c.width + 4
        rowh = max(rowh, c.height)
    if cur:
        sheets.append(cur)
    paths = []
    for i, s in enumerate(sheets):
        w = max(px + c.width for px, py, c in s)
        h = max(py + c.height for px, py, c in s)
        im = Image.new('RGB', (w, h), (30, 0, 30))
        for px, py, c in s:
            im.paste(c, (px, py))
        p = os.path.join(OUT, '%s_%d.png' % (name, i + 1))
        im.save(p)
        paths.append(p)
    return paths


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    seqs = d.read_dink_ini()
    rows = list(csv.DictReader(open(USAGE)))
    counts = {(int(r['seq']), int(r['frame'])): int(r['placement_count']) for r in rows}
    pairs = sorted(counts)
    sel = [int(a) for a in argv]
    if sel:
        for s in sel:
            ps = [p for p in pairs if p[0] == s]
            print(pack(tiles_for(ps, counts, seqs), 'seq%03d' % s))
        return
    # default: group consecutive seqs into packed sheets
    cells = tiles_for(pairs, counts, seqs)
    print('\n'.join(pack(cells, 'all')))


if __name__ == '__main__':
    main(sys.argv[1:])
