"""Procedural feather-card atlas for the duck (pure numpy/Pillow, no third-party pixels).
8 cells of 256x512 in a 1024x1024 sheet. Cell order (col,row): row 0 = primary, primary2, secondary, tail; row 1 = contour, contour2, covert, down.
Each feather: base at the bottom of its cell, tip at the top. Writes <out>_BC.png (RGBA, straight alpha), _N.png (OpenGL), _ORM.png.
usage: python3 -I gen_feather_atlas.py <out_prefix> [tint r g b]
"""
import sys, math
import numpy as np
from PIL import Image, ImageFilter

out = sys.argv[1]
rng = np.random.default_rng(23)
CW, CH = 256, 512
SPEC = [  # name, half width (fraction of cell half), asym, roundness, fluff, split amount
    ('primary', .50, .45, .55, .05, .5), ('primary2', .46, .40, .5, .05, .7), ('secondary', .62, .2, .8, .08, .5), ('tail', .60, .0, .7, .08, .6),
    ('contour', .86, .0, 1.25, .45, .5), ('contour2', .80, .08, 1.1, .55, .7), ('covert', .74, .1, 1.0, .25, .5), ('down', .88, .0, 1.3, 1.0, 1.0)]

def vnoise(x, seed, octaves=3):
    """1D smooth value noise, x in arbitrary units."""
    r = np.random.default_rng(seed); tab = r.random(4096); res = np.zeros_like(x); amp = 1.0; tot = 0
    for o in range(octaves):
        xi = np.floor(x).astype(int); f = x - xi; f = f * f * (3 - 2 * f)
        res += amp * (tab[xi % 4096] * (1 - f) + tab[(xi + 1) % 4096] * f); tot += amp; amp *= .5; x = x * 2.03 + 17
    return res / tot

def feather(k, name, hw, asym, rnd, fluff, split):
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float64)
    u = 1 - (yy + .5) / CH                      # 0 base .. 1 tip
    bend = .06 * np.sin(u * math.pi * .9) * (1 if k % 2 else -1) * (asym > 0)
    v = ((xx + .5) / CW - .5) * 2 - bend        # -1..1 across
    cal = .10                                   # calamus (bare quill) length
    uu = np.clip((u - cal) / (1 - cal - .02), 0, 1)
    prof = np.sin(np.clip(uu, 0, 1) ** (.55 / rnd) * math.pi) ** (.5 / rnd) * (1 - .25 * uu ** 3)
    wl = hw * prof * (1 - asym); wr = hw * prof * (1 + asym * .35)      # narrow leading vane, wide trailing vane
    w = np.where(v < 0, wl, wr) + 1e-6
    q = np.abs(v) / w                            # 0 rachis .. 1 vane edge
    # barbs run outward and toward the tip
    slope = .55 + .25 * (1 - uu)
    b = uu - q * w * slope * .5                  # barb id coordinate (constant along a barb)
    freq = 150 if fluff < .3 else 95
    wig = vnoise(b * 40 + (v > 0) * 300, 11 + k) * .9
    barb = np.sin((b * freq + wig) * math.tau)
    # splits: notches opening from the edge inward along barb lines
    sn = vnoise(b * 16 + (v > 0) * 99, 31 + k, 2)
    depth = np.clip((sn - (.68 - .16 * split)) / .2, 0, 1) * (.25 + .5 * split)
    gapw = np.clip(1 - np.abs(((b * 16 + (v > 0) * 99) % 1) - .5) * 5, 0, 1)
    notch = (q > 1 - depth * gapw) & (uu > .08)
    edge = 1 - q
    if fluff > 0:                                # downy frayed margin: barbs separate progressively toward the edge and the base
        F = .12 + .5 * fluff
        T = np.clip((q - (1 - F)) / F, 0, 1) ** 1.3 * (.55 + .4 * fluff)
        cut = .1 + .34 * fluff
        T2 = np.clip((cut - uu) / cut, 0, 1) ** .8 * (.5 + .45 * fluff) * np.clip(q * 6, 0, 1)
        fr = vnoise(b * freq * .25 + (v > 0) * 50, 71 + k, 1) * .25
        notch |= np.abs(barb) < np.maximum(T, T2) + fr * np.maximum(T, T2)
    alpha = ((q < 1) & (uu > 0) & (uu < 1) & ~notch).astype(np.float64)
    rw = .020 * (1 - .75 * uu) / max(hw, .3) * .5 + .006      # rachis half width in v
    rach = (np.abs(v) < rw * np.where(u < cal, 1.25, 1)) & (u > .012) & (uu < .97)
    alpha = np.maximum(alpha, rach.astype(np.float64))
    # height: rachis ridge, barb ridges, vane curl
    rr = np.clip(1 - np.abs(v) / (rw * 2.2), 0, 1)
    h = rr ** 1.5 * 1.0 + .16 * barb * (q > .02) + .5 * np.clip(1 - q, 0, 1) ** .7 * .5 - .35 * np.clip(q, 0, 1.5) ** 3
    h = h * alpha
    # colour: white feather, ivory rachis, slightly greyer/yellower toward the base and in barb troughs
    base = np.stack([np.full_like(u, .93), np.full_like(u, .925), np.full_like(u, .90)], -1)
    shade = (.93 + .07 * (barb * .5 + .5)) * (.90 + .10 * uu) * (1 - .06 * vnoise(b * 9 + q * 3, 51 + k))
    col = base * shade[..., None]
    col = np.where(rach[..., None], np.array([.90, .86, .74]) * (.9 + .1 * uu[..., None]), col)
    stain = vnoise(uu * 6 + v * 2, 91 + k) * (1 - uu) * .08
    col = col * (1 - stain[..., None] * np.array([.3, .5, 1.0]))
    rough = np.where(rach, .38, .62 + .12 * (barb * .5 + .5) + .1 * q)
    return col, alpha, h, rough

BC = np.zeros((1024, 1024, 4)); H = np.zeros((1024, 1024)); R = np.full((1024, 1024), .7)
for k, sp in enumerate(SPEC):
    col, al, h, rough = feather(k, *sp)
    r0 = (k // 4) * CH; c0 = (k % 4) * CW
    BC[r0:r0 + CH, c0:c0 + CW, :3] = col; BC[r0:r0 + CH, c0:c0 + CW, 3] = al; H[r0:r0 + CH, c0:c0 + CW] = h; R[r0:r0 + CH, c0:c0 + CW] = rough
# dilate colour under transparent texels so mips do not pull in black
rgb = BC[..., :3].copy(); a = BC[..., 3]
for _ in range(10):
    m = (a > 0).astype(np.float64) if _ == 0 else m
    acc = np.zeros_like(rgb); cnt = np.zeros_like(m)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        acc += np.roll(rgb * m[..., None], (dy, dx), (0, 1)); cnt += np.roll(m, (dy, dx), (0, 1))
    fill = (m == 0) & (cnt > 0); rgb[fill] = acc[fill] / cnt[fill][:, None]; m = np.maximum(m, fill)
rgb[m == 0] = (.92, .91, .88)
def srgb(x): return np.where(x <= .0031308, x * 12.92, 1.055 * np.clip(x, 0, 1) ** (1 / 2.4) - .055)
img = np.concatenate([srgb(rgb), a[..., None]], -1)
Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), 'RGBA').save(out + '_BC.png')
H = np.nan_to_num(H); Hs = H * .5 + .25
for _ in range(2): Hs = (Hs * 2 + np.roll(Hs, 1, 0) + np.roll(Hs, -1, 0) + np.roll(Hs, 1, 1) + np.roll(Hs, -1, 1)) / 6
gy, gx = np.gradient(Hs); s = 7.0
nx = -gx * s; ny = gy * s; nzv = np.ones_like(nx); ln = np.sqrt(nx * nx + ny * ny + nzv * nzv)      # image y is down: +gy is OpenGL green-up
N = np.stack([nx / ln * .5 + .5, ny / ln * .5 + .5, nzv / ln * .5 + .5], -1)
Image.fromarray((np.clip(N, 0, 1) * 255 + .5).astype(np.uint8), 'RGB').save(out + '_N.png')
ao = np.clip(.75 + Hs, 0, 1)
ORM = np.stack([ao, R, np.zeros_like(R)], -1)
Image.fromarray((np.clip(ORM, 0, 1) * 255 + .5).astype(np.uint8), 'RGB').save(out + '_ORM.png')
print('feather atlas written', out)
