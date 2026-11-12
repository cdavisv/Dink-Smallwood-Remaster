"""Procedural bristle-card atlas (pure numpy/Pillow): 4 cells of 128x512 in a 512x512 sheet, roots at the bottom, tips at the top.
Cells: 0 sparse body bristles, 1 denser crest, 2 short fine, 3 tail tuft / ear fringe. Writes <out>_BC.png (RGBA) , _N.png, _ORM.png.
usage: python3 -I gen_bristle_atlas.py <out_prefix> r g b   (linear root colour; tips are lightened)"""
import sys, math
import numpy as np
from PIL import Image, ImageDraw

out = sys.argv[1]; col = tuple(float(x) for x in sys.argv[2:5]) if len(sys.argv) > 4 else (.78, .70, .58)
S = 4; W, H = 512 * S, 512 * S
rng = np.random.default_rng(41)
alpha = Image.new('L', (W, H), 0); shade = Image.new('L', (W, H), 0); da = ImageDraw.Draw(alpha); ds = ImageDraw.Draw(shade)
SPEC = [(int(x) for x in t) if False else t for t in ((7, .55, 1.0, .22), (16, .8, 1.0, .18), (9, .35, .6, .3), (10, .6, 1.0, .35))]   # count, min length, max length, curl
for c, (cnt, lmin, lmax, curl) in enumerate(SPEC):
    x0 = c * 128 * S; cw = 128 * S
    for k in range(cnt):
        bx = x0 + cw * rng.uniform(.14, .86); L = H * rng.uniform(lmin, lmax) * .96; lean = rng.uniform(-.22, .22); cv = rng.uniform(-curl, curl); wd = rng.uniform(1.6, 3.0) * S * (.8 if c == 2 else 1)
        pts = []
        for i in range(25):
            t = i / 24; x = bx + (lean * t + cv * t * t) * cw * .5; y = H - 2 - t * L; pts.append((x, y, t))
        tone = int(rng.uniform(150, 255))
        for (xa, ya, ta), (xb, yb, tb) in zip(pts[:-1], pts[1:]):
            w = max(1, wd * (1 - ta) ** .7)
            if min(xa, xb) < x0 + 3 * S or max(xa, xb) > x0 + cw - 3 * S: continue
            da.line([(xa, ya), (xb, yb)], fill=255, width=int(round(w))); ds.line([(xa, ya), (xb, yb)], fill=int(tone * (.65 + .35 * ta)), width=int(round(w)))
alpha = alpha.resize((512, 512), Image.LANCZOS); shade = shade.resize((512, 512), Image.LANCZOS)
a = np.asarray(alpha, np.float64) / 255; s = np.asarray(shade, np.float64) / 255
s = np.where(a > .02, s / np.maximum(a, .02), .8)
lin = np.stack([np.clip(col[i] * (.8 + .3 * s), 0, 1) for i in range(3)], -1)
srgb = np.where(lin <= .0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - .055)
Image.fromarray((np.concatenate([srgb, np.clip(a * 1.5, 0, 1)[..., None] * (float(sys.argv[5]) if len(sys.argv) > 5 else 1.0)], -1) * 255 + .5).astype(np.uint8), 'RGBA').save(out + '_BC.png')
gy, gx = np.gradient(a); nx = -gx * 2.5; ny = gy * 2.5; ln = np.sqrt(nx * nx + ny * ny + 1)
Image.fromarray((np.stack([nx / ln * .5 + .5, ny / ln * .5 + .5, 1 / ln * .5 + .5], -1) * 255 + .5).astype(np.uint8), 'RGB').save(out + '_N.png')
Image.fromarray((np.stack([np.ones_like(a), np.full_like(a, .42), np.zeros_like(a)], -1) * 255 + .5).astype(np.uint8), 'RGB').save(out + '_ORM.png')
print('bristle atlas written', out)
