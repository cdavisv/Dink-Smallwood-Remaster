"""Synthesise an eye texture set (BC, N, ORM) 1024 px. Azimuthal layout: texture centre = pupil, radius .5 = 105 deg.
usage: eye_tex.py <out_prefix> <iris r,g,b> [seed]"""
import sys, numpy as np
from PIL import Image, ImageFilter
out = sys.argv[1]; iris_c = np.array([float(x) for x in sys.argv[2].split(',')]) / 255; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 3
rng = np.random.default_rng(seed); N = 1024
y, x = np.mgrid[0:N, 0:N]; u = (x + .5) / N - .5; v = (y + .5) / N - .5
r = np.hypot(u, v); ang = np.arctan2(v, u)
deg = r / .5 * 105.0
def sm(a, b, t): t = np.clip((t - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def blur(a, s): return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s)), float) / 255
IR = 21.0; PU = 6.3
# sclera
scl = np.ones((N, N, 3)) * np.array([.86, .82, .78])
pink = sm(40, 100, deg)[..., None]; scl = scl * (1 - pink * .22) + np.array([.80, .50, .45]) * pink * .22
# veins: random walks
vein = np.zeros((N, N), np.float32)
for k in range(46):
    a = rng.uniform(0, 6.28); rr = rng.uniform(.30, .5); px, py = N / 2 + rr * N * np.cos(a), N / 2 + rr * N * np.sin(a)
    d = a + np.pi + rng.normal(0, .5); w = rng.uniform(.5, 1.4)
    for s in range(int(rng.uniform(60, 240))):
        d += rng.normal(0, .22); px += np.cos(d) * 1.5; py += np.sin(d) * 1.5
        xi, yi = int(px), int(py)
        if not (2 < xi < N - 2 and 2 < yi < N - 2): break
        if np.hypot(xi - N / 2, yi - N / 2) / N / .5 * 105 < IR + 6: break
        vein[yi - 1:yi + 1, xi - 1:xi + 1] += w * .5
        if rng.random() < .012: w *= .7
vein = blur(np.clip(vein, 0, 1), 1.0)
scl = scl * (1 - vein[..., None] * .55) + np.array([.62, .16, .14]) * vein[..., None] * .55
scl *= (1 + (blur(rng.random((N, N)), 6)[..., None] - .5) * .08)
scl *= (1 - .45 * sm(34, 80, deg))[..., None]                     # the white darkens toward the lids
car = np.exp(-(((u - .34) / .05) ** 2 + (v / .06) ** 2))[..., None]   # caruncle, inner corner (u is mirrored per eye)
scl = scl * (1 - car * .8) + np.array([.62, .30, .28]) * car * .8
# iris
t = np.clip(deg / IR, 0, 1)
fib = np.zeros((N, N))
for f_, amp in ((70, .5), (150, .3), (310, .2)):
    ph = rng.uniform(0, 6.28, 1024)
    idx = ((ang + np.pi) / (2 * np.pi) * f_).astype(int) % f_
    tab = rng.random(f_); fib += amp * tab[idx]
fib = blur(fib, 1.2); fib = fib + .25 * blur(rng.random((N, N)), 2)
base = iris_c[None, None, :] * (.38 + .62 * fib[..., None])
inner = np.array([.62, .42, .16])    # amber collarette round the pupil
coll = np.exp(-((t - .36) / .13) ** 2)[..., None] * (.5 + .5 * fib[..., None])
iris = base * (1 - coll * .7) + inner * coll * .7
iris *= (1 - .65 * sm(.78, 1.0, t))[..., None]           # dark limbal ring
iris *= (.75 + .25 * sm(.3, .6, t))[..., None]
pup = 1 - sm(PU - 1.2, PU + .6, deg)
iris = iris * (1 - pup[..., None]) + np.array([.012, .010, .010]) * pup[..., None]
m = (1 - sm(IR - 1.0, IR + 2.2, deg))[..., None]
bc = scl * (1 - m) + iris * m
Image.fromarray((np.clip(bc, 0, 1) * 255 + .5).astype(np.uint8)).save(out + '_BC.png')
# normal: nearly flat; faint iris fibre relief
h = blur(fib * m[..., 0], 1.0) * .6
gx = np.gradient(h, axis=1) * 6; gy = np.gradient(h, axis=0) * 6
n = np.dstack([-gx, gy, np.ones_like(gx)]); n /= np.linalg.norm(n, axis=2)[..., None]
Image.fromarray(((n * .5 + .5) * 255 + .5).astype(np.uint8)).save(out + '_N.png')
rough = .22 * (1 - m[..., 0]) + .06 * m[..., 0] + vein * .1
ao = 1 - .35 * sm(60, 105, deg)
Image.fromarray((np.dstack([ao, rough, np.zeros_like(ao)]) * 255 + .5).astype(np.uint8)).save(out + '_ORM.png')
print('eye', out)
