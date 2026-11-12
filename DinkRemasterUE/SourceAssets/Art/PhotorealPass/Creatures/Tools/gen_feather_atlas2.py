"""Feather-card atlas v2 for the duck (pure numpy/Pillow, no third-party pixels). 8 cells of 256x512 in a 1024x1024 sheet.
Row 0 (top): primary, secondary, tertial/scapular, tail. Row 1: contour A, contour B, covert, down tuft.
Base (quill) at the bottom of each cell, tip at the top. Painted shading: grey shadowed base (where the next feather overlaps),
rachis, barb striation, frayed and split vane edges. Writes <out>_BC.png (RGBA straight alpha), _N.png (OpenGL), _ORM.png.
usage: python3 -I gen_feather_atlas2.py <out_prefix> [bloody]
"""
import sys, math
import numpy as np
from PIL import Image

out = sys.argv[1]; BLOODY = len(sys.argv) > 2 and sys.argv[2] == 'bloody'
CW, CH = 256, 512
# name, max half width, peak position exponent, tip power, leading-vane scale, fluff (downy base fraction), splits, fray
SPEC = [('primary', .42, .85, 1.0, .5, .05, 3, .05), ('secondary', .56, 1.0, .7, .75, .06, 3, .06), ('tertial', .70, 1.25, .55, .9, .10, 4, .08), ('tail', .50, 1.1, .6, 1.0, .06, 3, .06),
        ('contourA', .88, 1.5, .5, 1.0, .34, 5, .12), ('contourB', .80, 1.35, .55, .92, .42, 7, .16), ('covert', .74, 1.4, .5, 1.0, .22, 3, .09), ('down', .9, 1.0, .5, 1.0, 1.0, 0, .3)]


def vnoise(x, seed, octaves=3):
    r = np.random.default_rng(seed); tab = r.random(4096); res = np.zeros_like(x); amp = 1.0; tot = 0
    for o in range(octaves):
        xi = np.floor(x).astype(int); f = x - xi; f = f * f * (3 - 2 * f)
        res += amp * (tab[xi % 4096] * (1 - f) + tab[(xi + 1) % 4096] * f); tot += amp; amp *= .5; x = x * 2.03 + 17
    return res / tot


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def feather(k, name, W, pk, tp, lead, fluff, nsplit, fray):
    rng = np.random.default_rng(100 + k)
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float64)
    u = 1 - (yy + .5) / CH; u = (u - .03) / .95                                   # 0 base .. 1 tip, small margin
    bend = (.10 * (u - .5) ** 2 - .025) * (1 if k % 2 else -1) * (name in ('primary', 'secondary'))
    v = ((xx + .5) / CW - .5) * 2 - bend
    uc = np.clip(u, 0, 1)
    if name == 'down':
        a = np.zeros_like(u); sh = np.zeros_like(u); h = np.zeros_like(u)
        for i in range(46):
            ang = rng.uniform(-1.05, 1.05); L = rng.uniform(.45, .98); cv = rng.uniform(-.5, .5); wd = rng.uniform(.012, .022)
            t = np.clip(u / L, 0, 1); cx = (math.sin(ang) * t + cv * t * t * .35) * L * .9
            d = np.abs(v - cx) / (wd * (1.15 - t)); f = np.clip(1 - d, 0, 1) * (u > 0) * (u < L)
            a = np.maximum(a, f); sh = np.maximum(sh, f * rng.uniform(.8, 1)); h = np.maximum(h, f)
        return np.clip(a * 1.6, 0, 1) * .85, .86 + .14 * sh, h * .5, np.zeros_like(u)
    w = W * np.sin(math.pi * np.clip(uc, 0, 1) ** pk * .97 + .03) ** tp
    w = w * ss(1.0, .9, uc) ** .5
    w = np.where(v < 0, w * lead, w)
    w = np.maximum(w, .02 * (u >= -.03))
    av = np.abs(v); e = av / np.maximum(w, 1e-6)                                  # 0 rachis .. 1 vane edge
    # barb coordinate: barbs leave the rachis at ~40 degrees toward the tip
    bc = (u * CH / CW * 2 - av * .85) * 46
    tooth = vnoise(bc * 1.0 + (v > 0) * 31, 7 + k, 2)
    edge = 1 - fray * (.3 + 1.4 * tooth) * ss(.0, .35, uc)
    alpha = ss(edge, edge - .10, e) * (u > 0) * (u < 1)
    for i in range(nsplit):                                                       # splits: barbs come unzipped
        us = rng.uniform(.25, .9); sd = rng.choice((-1, 1)); dep = rng.uniform(.35, .8); wd = rng.uniform(.006, .016)
        d = np.abs((u - av * .42) - (us - .2)); notch = (d < wd * (e ** 1.5) * 1.7) & (np.sign(v) == sd) & (e > 1 - dep)
        alpha = np.where(notch, 0, alpha)
    fl = ss(fluff, fluff * .35, uc)                                              # downy base: wispy filaments
    fil = vnoise(v * 26 + uc * 9 + k, 60 + k, 3)
    alpha = alpha * (1 - fl) + fl * alpha * ss(.38, .62, fil) * .85
    quill = (av < .03) & (u > -.03) & (u <= .08); alpha = np.maximum(alpha, quill * 1.0)
    barb = np.sin(bc * 2.2 + tooth * 2)
    sh = (.74 + .26 * ss(.0, .55, uc)) * (1 + .028 * barb) * (1 - .10 * ss(.75, 1.0, e))
    sh = sh * (1 - .12 * np.exp(-(av / .02) ** 2) * (uc < .9))                    # rachis shadow line
    sh *= .93 + .14 * vnoise(u * 5 + v * 3 + k * 3, 90 + k, 2)
    h = .55 * np.sqrt(np.clip(1 - e * e, 0, 1)) * ss(0, .2, uc) + .05 * barb * ss(.0, .15, uc) + .22 * np.exp(-(av / .025) ** 2)
    return np.clip(alpha, 0, 1), sh, h, fl


sheet_a = np.zeros((CH * 2, CW * 4)); sheet_s = np.ones((CH * 2, CW * 4)); sheet_h = np.zeros((CH * 2, CW * 4)); sheet_f = np.zeros((CH * 2, CW * 4))
for k, sp in enumerate(SPEC):
    a, s, h, f = feather(k, *sp); r0, c0 = divmod(k, 4)
    sl = (slice(r0 * CH, (r0 + 1) * CH), slice(c0 * CW, (c0 + 1) * CW)); sheet_a[sl] = a; sheet_s[sl] = s; sheet_h[sl] = h; sheet_f[sl] = f
tip = np.array((.74, .735, .70)); base = np.array((.58, .59, .61))                 # linear: warm white tips, cool grey shadowed bases
t = np.clip((sheet_s - .72) / .3, 0, 1)[..., None]; lin = (base * (1 - t) + tip * t) * np.clip(sheet_s, 0, 1.1)[..., None]
if BLOODY:
    yy, xx = np.mgrid[0:CH * 2, 0:CW * 4].astype(np.float64); n = vnoise(xx * .035 + np.sin(yy * .02) * 2, 5, 3) * vnoise(yy * .03 + 3, 6, 3)
    m = np.clip((n - .03) * 7, 0, 1)[..., None]; lin = lin * (1 - m) + (lin * np.array((.5, .02, .02)) * .4 + np.array((.09, .003, .003))) * m
    sheet_a = np.clip(sheet_a * (1 + .5 * m[..., 0]), 0, 1)
srgb = np.where(lin <= .0031308, lin * 12.92, 1.055 * np.clip(lin, 0, 1) ** (1 / 2.4) - .055)
Image.fromarray((np.concatenate([srgb, sheet_a[..., None]], -1) * 255 + .5).astype(np.uint8), 'RGBA').save(out + '_BC.png')
gy, gx = np.gradient(sheet_h); nx = -gx * 14; ny = gy * 14; ln = np.sqrt(nx * nx + ny * ny + 1)
Image.fromarray((np.stack([nx / ln * .5 + .5, ny / ln * .5 + .5, 1 / ln * .5 + .5], -1) * 255 + .5).astype(np.uint8), 'RGB').save(out + '_N.png')
rough = np.clip(.62 + .2 * sheet_f - (.35 * m[..., 0] if BLOODY else 0), .1, 1)
Image.fromarray((np.stack([np.clip(.75 + .25 * sheet_s, 0, 1), rough, np.zeros_like(rough)], -1) * 255 + .5).astype(np.uint8), 'RGB').save(out + '_ORM.png')
print('feather atlas v2 written', out)
