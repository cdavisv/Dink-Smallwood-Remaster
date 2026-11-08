"""Render screens (tiles + placed sprites, depth-sorted) with each sprite
labelled 'index:seq.frame' to identify what a placement is in context.
Writes out/screens/sNNN.png. Usage: python3 render_screen.py N [N ...]"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import dinkdata as d
import features as F

OUT = os.path.join(d.REPO, 'tools', 'data', 'out', 'screens')


def render(n, seqs, labels=True):
    rec = None
    for num, blk, _ in d.iter_screens():
        if num == n:
            rec = blk
            break
    if rec is None:
        return None
    img = np.zeros((400, 600, 3), np.uint8)
    for i, t in enumerate(d.screen_tiles(rec)):
        p = F.tile_pixels(t)
        if p is not None:
            img[(i // 12) * 50:(i // 12) * 50 + 50, (i % 12) * 50:(i % 12) * 50 + 50] = p
    M = 500
    im = Image.new('RGBA', (600 + 2 * M, 400 + 2 * M), (0, 0, 0, 255))
    im.paste(Image.fromarray(img).convert('RGBA'), (M, M))
    ps = d.screen_placements(n, rec)
    ps.sort(key=lambda p: ((p.que or p.y), p.index))
    marks = []
    for p in ps:
        fr, _ = d.load_frame_rgba(seqs, p.seq, p.frame)
        if fr is None:
            marks.append((p, p.x - 20, p.y))
            continue
        if p.size and p.size != 100:
            fr = fr.resize((max(1, fr.width * p.size // 100), max(1, fr.height * p.size // 100)))
        xo, yo = d.frame_origin(seqs, p.seq, p.frame, *d.load_frame_rgba(seqs, p.seq, p.frame)[0].size)
        xo, yo = xo * (p.size or 100) // 100, yo * (p.size or 100) // 100
        x, y = p.x - 20 - xo, p.y - yo
        if p.type == 2:
            fr.putalpha(fr.getchannel('A').point(lambda a: a // 3))
        if -M < x < 600 + M - fr.width and -M < y < 400 + M - fr.height:
            im.alpha_composite(fr, (x + M, y + M))
        marks.append((p, p.x - 20, p.y))
    im = im.crop((M, M, M + 600, M + 400))
    if labels:
        dr = ImageDraw.Draw(im)
        for p, x, y in marks:
            t = '%d:%d.%d' % (p.index, p.seq, p.frame)
            col = (255, 255, 0) if p.type == 1 else ((0, 255, 255) if p.type == 0 else (255, 0, 255))
            dr.rectangle([x - 1, y - 1, x + 1, y + 1], fill=(255, 0, 0))
            dr.text((x + 2, y - 10), t, fill=col, stroke_width=1, stroke_fill=(0, 0, 0))
    return im


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    seqs = d.read_dink_ini()
    for a in argv:
        im = render(int(a), seqs)
        if im is not None:
            im.convert('RGB').save(os.path.join(OUT, 's%03d.png' % int(a)))
    print('rendered', argv)


if __name__ == '__main__':
    main(sys.argv[1:])
