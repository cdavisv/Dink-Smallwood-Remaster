"""Synthesise a hair-card strand atlas (BC+alpha, flow normal, ORM) with numpy. Original work, no scans.
usage: hair_tex.py <out_prefix> <r,g,b mid colour sRGB 0-255> [seed] [grey_fraction]
Layout 2048x2048: rows 0-767 and 768-1535 hold 8 strips each (256 px wide; root at top).
Strips 0-9 dense clumps, 10-13 thin clumps, 14-15 flyaways. Bottom 512 rows are left for brows/lashes."""
import sys, numpy as np
from PIL import Image
out = sys.argv[1]; mid = np.array([float(x) for x in sys.argv[2].split(',')]) / 255.0
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7; grey = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
rng = np.random.default_rng(seed)
W = H = 2048; SW = 256; SH = 768
col = np.zeros((H, W, 3), np.float32); alpha = np.zeros((H, W), np.float32); nx = np.zeros((H, W), np.float32); depth = np.zeros((H, W), np.float32); ao = np.ones((H, W), np.float32)
def srgb2lin(c): return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
def lin2srgb(c): return np.where(c <= .0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - .055)
midl = srgb2lin(mid)
for strip in range(16):
    if strip in (8, 9): continue        # undercoat cap tile, filled below
    ox = (strip % 8) * SW; oy = (strip // 8) * SH
    if strip < 8 or strip in (10, 11): n = int(rng.integers(120, 170)); spread = .38; wmax = 2.3
    elif strip < 14: n = int(rng.integers(40, 70)); spread = .30; wmax = 1.7
    else: n = int(rng.integers(7, 14)); spread = .34; wmax = 1.3
    cx = SW / 2
    nclump = int(rng.integers(2, 5)); ccen = rng.uniform(-spread * .6, spread * .6, nclump) * SW; ctip = ccen * rng.uniform(.2, .9, nclump) + rng.normal(0, 8, nclump)
    wave_f = rng.uniform(.6, 1.6); wave_a = rng.uniform(2, 7)
    strip_val = float(np.clip(rng.normal(1.0, .16), .72, 1.32))
    ds = np.sort(rng.uniform(0, 1, n))
    for k in range(n):
        ci = rng.integers(0, nclump)
        x0 = ccen[ci] + rng.normal(0, spread * SW * .28); xt = ctip[ci] + rng.normal(0, spread * SW * (.10 if strip < 14 else .3))
        x0 = np.clip(x0, -SW * .44, SW * .44); xt = np.clip(xt, -SW * .42, SW * .42)
        L = SH * np.clip(rng.normal(.84, .14), .45, .985) if strip < 14 else SH * rng.uniform(.6, .98)
        y = np.arange(0, int(L)); t = y / L
        ph = rng.uniform(0, 6.28); a = wave_a * rng.uniform(.5, 1.5) * (1.6 if strip >= 14 else 1)
        x = cx + x0 + (xt - x0) * t ** 1.3 + a * np.sin(wave_f * t * 6.28 + ph) * t + rng.normal(0, .6) * np.sin(t * 23 + ph)
        wdt = wmax * rng.uniform(.6, 1.0) * (1 - .75 * t ** 3)
        al = np.clip(1.15 - t ** 6, 0, 1) * (1 - np.clip((t - .93) / .07, 0, 1)) * rng.uniform(.75, 1.0)
        val = np.clip(rng.normal(1.0, .34), .4, 1.9) * strip_val
        if rng.uniform() < .05: val *= 1.5
        hue = rng.normal(0, .05)
        rootdark = .45 + .55 * np.clip(t / .35, 0, 1) ** .8; tipl = 1 + .28 * t ** 2
        c = midl[None, :] * (val * rootdark * tipl)[:, None] * np.array([1 + hue, 1, 1 - hue * 1.5])[None, :]
        if grey and rng.uniform() < grey: c = np.ones_like(c) * (.45 * val * rootdark)[:, None]
        d = ds[k]
        for off in range(-3, 4):
            xi = np.floor(x).astype(int) + off; fx = (xi + .5 - x) / np.maximum(wdt, .3)
            g = np.exp(-fx * fx * 1.2) * al
            okm = (xi >= 2) & (xi < SW - 2) & (g > .02)
            yy = y[okm] + oy; xx = xi[okm] + ox; gg = g[okm].astype(np.float32)
            # alpha-over, back to front (strands sorted by depth)
            col[yy, xx] = col[yy, xx] * (1 - gg[:, None]) + c[okm] * gg[:, None] * (1 - .35 * np.abs(fx[okm]) ** 2)[:, None]
            nx[yy, xx] = nx[yy, xx] * (1 - gg) + np.clip(fx[okm], -1, 1) * gg
            depth[yy, xx] = depth[yy, xx] * (1 - gg) + d * gg
            alpha[yy, xx] = alpha[yy, xx] + gg * (1 - alpha[yy, xx])
# undercoat cap tile (strips 8-9): opaque combed hair, ragged alpha at the bottom for a soft hairline
cw = 2 * SW; yy0 = SH
colv = rng.normal(1.0, .30, cw).clip(.45, 1.8); colv = (colv + np.roll(colv, 1)) / 2
tt = (np.arange(SH) / SH)[:, None]
streak = colv[None, :] * (.9 + .2 * np.sin(tt * 9 + rng.uniform(0, 6.28, cw)[None, :]))
capc = midl[None, None, :] * (streak * (.55 + .45 * np.clip(tt / .5, 0, 1)) * .8)[..., None]
thr = rng.uniform(.80, 1.0, cw)[None, :]
capa = np.clip((thr - tt) / .05, 0, 1)
col[yy0:yy0 + SH, :cw] = capc * capa[..., None]; alpha[yy0:yy0 + SH, :cw] = capa; depth[yy0:yy0 + SH, :cw] = .55 + .4 * (streak - streak.min()) / (np.ptp(streak) + 1e-6); nx[yy0:yy0 + SH, :cw] = 0
# occlusion from depth (deeper strands darker) and root shadow
ao = .55 + .45 * depth
yy = (np.arange(H) % SH) / SH
ao[:1536] *= (.75 + .25 * np.clip(yy[:1536] / .25, 0, 1))[:, None]
col *= (.45 + .55 * depth)[..., None]
# bleed colour under transparent texels
avg = (col * alpha[..., None]).sum((0, 1)) / max(alpha.sum(), 1)
bc = np.where(alpha[..., None] > .02, col / np.maximum(alpha[..., None], .02) * np.minimum(alpha[..., None] / .02, 1) + 0, avg[None, None, :])
m = np.clip(alpha[..., None] * 6, 0, 1); bc = bc * m + avg[None, None, :] * (1 - m)
rgba = np.dstack([np.clip(lin2srgb(bc), 0, 1), np.clip(alpha * 1.25, 0, 1)])
Image.fromarray((rgba * 255 + .5).astype(np.uint8), 'RGBA').save(out + '_BC.png')
nz = np.sqrt(np.clip(1 - (nx * .75) ** 2, 0, 1)); nrm = np.dstack([nx * .75 * .5 + .5, np.full_like(nx, .5), nz * .5 + .5])
nrm = np.where(alpha[..., None] > .05, nrm, np.array([.5, .5, 1.0])[None, None, :])
Image.fromarray((nrm * 255 + .5).astype(np.uint8), 'RGB').save(out + '_N.png')
rough = .62 + .2 * (1 - depth) + rng.normal(0, .02, (H, W))
orm = np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0, 1), np.zeros_like(ao)])
Image.fromarray((orm * 255 + .5).astype(np.uint8), 'RGB').save(out + '_ORM.png')
print('hair atlas', out, 'coverage', float((alpha[:1536] > .5).mean()))
