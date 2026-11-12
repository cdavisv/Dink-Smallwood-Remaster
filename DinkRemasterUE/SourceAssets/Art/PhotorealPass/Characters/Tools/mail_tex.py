"""Authored tileable riveted-mail tile (4-in-1 look): diffuse, OpenGL normal, roughness. 1024 px = 8 x 12 rings.
usage: python3 -I mail_tex.py <out_dir>"""
import sys, numpy as np
from pathlib import Path
from PIL import Image
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
N = 1024; NX, NY = 8, 12
rng = np.random.default_rng(4)
y, x = np.mgrid[0:N, 0:N].astype(np.float32); x /= N; y /= N
px, py = 1.0 / NX, 1.0 / NY
H = np.zeros((N, N), np.float32); ID = np.zeros((N, N), np.float32)
R = .60 * px; Wd = .13 * px
for i in range(-1, NY + 1):
    for j in range(-1, NX + 1):
        cx = (j + (.5 if i % 2 else 0)) * px; cy = (i + .5) * py
        tilt = (1 if i % 2 else -1) * .9
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                dx = x - cx - ox; dy = (y - cy - oy) * (px / py) * .62
                m = (np.abs(dx) < R * 1.4) & (np.abs(dy) < R * 1.4)
                if not m.any(): continue
                d = np.sqrt(dx[m] ** 2 + dy[m] ** 2); t = (d - R) / Wd
                h = np.sqrt(np.clip(1 - t * t, 0, 1)) * Wd + tilt * dx[m] * .32 + .5 * Wd
                h = np.where(np.abs(t) < 1, h, 0)
                cur = H[m]; win = h > cur
                cur[win] = h[win]; H[m] = cur
                idv = ID[m]; idv[win] = (i * 31 + j * 17) % 97 / 97.0; ID[m] = idv
H /= H.max()
gap = H < .05
val = .62 + .25 * H + (ID - .5) * .10 + rng.normal(0, .015, (N, N))
diff = np.dstack([val * .98, val, val * 1.03]); diff[gap] = np.array([.13, .12, .11])
Image.fromarray((np.clip(diff, 0, 1) * 255).astype(np.uint8)).save(out / 'mail_diff.png')
gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 14; gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 14
n = np.dstack([-gx, gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2)[..., None]
Image.fromarray(((n * .5 + .5) * 255).astype(np.uint8)).save(out / 'mail_nor.png')
rough = np.where(gap, .9, .30 + .25 * (1 - H) + ID * .12)
Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8)).save(out / 'mail_rough.png')
print('mail tile', out, 'gap fraction', float(gap.mean()))
