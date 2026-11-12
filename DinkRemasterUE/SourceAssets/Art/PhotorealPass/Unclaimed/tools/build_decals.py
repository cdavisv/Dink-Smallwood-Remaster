"""blood_splat (187-189 effects/spurt) and burn_hole_decal (158 struct/details/damage frames 1-3): alpha decal sets.

A decal has no game mesh, so nothing is baked from geometry: each set is a height field authored here (metaball
drops for blood, cracked char blocks for burns), from which base colour + opacity, the normal (OpenGL) and the
ORM are derived. The beauty renders show exactly those PNGs blended over a scanned ground, as a deferred decal does.

    tools/bl.sh build_decals.py <name|blood|burn|all> [final]
"""
import bpy, math, os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
from pplib import NT, smoothstep

SCRIPT = 'build_decals.py'
W = 2048            # working resolution; written at 1024


# ---------------------------------------------------------------------------------------------- 2D field helpers
def spectral(rng, px=W, beta=2.0, lo=2.0, hi=None):
    """band-limited 1/f^beta noise, 0..1 (periodic)"""
    f = np.fft.fftfreq(px) * px; fx, fy = np.meshgrid(np.fft.rfftfreq(px) * px, f); k = np.hypot(fx, fy); k[0, 0] = 1
    amp = k ** (-beta / 2) * (k >= lo) * ((k <= hi) if hi else 1.0)
    a = np.fft.irfft2(amp * np.exp(2j * np.pi * rng.random(k.shape)), s=(px, px)); a -= a.min(); return (a / a.max()).astype(np.float32)


def blur(a, sigma):
    px = a.shape[0]; f = np.fft.fftfreq(px); fx, fy = np.meshgrid(np.fft.rfftfreq(px), f)
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy)), s=a.shape).astype(np.float32)


def warp(a, dx, dy):
    px = a.shape[0]; yy, xx = np.mgrid[0:px, 0:px].astype(np.float32); x = np.clip(xx + dx, 0, px - 1.001); y = np.clip(yy + dy, 0, px - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32); fx = x - x0; fy = y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy) + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy).astype(np.float32)


def gauss(F, x, y, s_major, s_minor=None, ang=0.0, amp=1.0):
    """add an anisotropic gaussian (pixels) to F inside a local window"""
    s_minor = s_minor or s_major; r = int(4 * max(s_major, s_minor)) + 2; px = F.shape[0]
    x0 = max(0, int(x) - r); x1 = min(px, int(x) + r + 1); y0 = max(0, int(y) - r); y1 = min(px, int(y) + r + 1)
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32); dx = xx - x; dy = yy - y; c = math.cos(ang); s = math.sin(ang)
    u = dx * c + dy * s; v = -dx * s + dy * c
    F[y0:y1, x0:x1] += amp * np.exp(-0.5 * ((u / s_major) ** 2 + (v / s_minor) ** 2))


def voronoi(px, cx, cy, rng, jitter=0.9):
    """jittered-grid Voronoi with cx x cy cells: returns F1, F2 (in units of cell size) and a random value per cell"""
    yy, xx = np.mgrid[0:px, 0:px].astype(np.float32); gx = xx / px * cx; gy = yy / px * cy; ix = np.floor(gx).astype(np.int32); iy = np.floor(gy).astype(np.int32)
    jx = rng.random((cy + 2, cx + 2)).astype(np.float32); jy = rng.random((cy + 2, cx + 2)).astype(np.float32); rv = rng.random((cy + 2, cx + 2)).astype(np.float32)
    f1 = np.full((px, px), 9.0, np.float32); f2 = f1.copy(); val = np.zeros((px, px), np.float32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            cxi = np.clip(ix + ox, -1, cx) + 1; cyi = np.clip(iy + oy, -1, cy) + 1
            px_ = (ix + ox) + 0.5 + (jx[cyi, cxi] - 0.5) * jitter; py_ = (iy + oy) + 0.5 + (jy[cyi, cxi] - 0.5) * jitter
            d = np.hypot(gx - px_, gy - py_); closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d)); val = np.where(closer, rv[cyi, cxi], val); f1 = np.where(closer, d, f1)
    return f1, f2, val


def normal_map(H, px_m, strength=1.0):
    """H in metres (row 0 at the bottom, y up) -> OpenGL tangent normal encoded 0..1"""
    gy, gx = np.gradient(H, px_m); nx = -gx * strength; ny = -gy * strength; nz = np.ones_like(H); n = np.sqrt(nx * nx + ny * ny + 1)
    return np.dstack([nx / n * 0.5 + 0.5, ny / n * 0.5 + 0.5, nz / n * 0.5 + 0.5]).astype(np.float32)


def down(a, f=2):
    s = a.shape; return a.reshape(s[0] // f, f, s[1] // f, f, *s[2:]).mean((1, 3))


def lerp(a, b, t):
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32); t = np.asarray(t, np.float32)
    if (a.ndim in (1, 3) or b.ndim in (1, 3)) and t.ndim == 2:
        t = t[..., None]
    return a * (1 - t) + b * t


# ---------------------------------------------------------------------------------------------- blood
def blood(spec, seed):
    rng = np.random.default_rng(seed); S = spec['size']; ppm = W / S; F = np.zeros((W, W), np.float32); c = W / 2

    def m(v):
        return v * ppm

    def drop(x, y, r, direction=None, elong=1.0, tail=0.0):
        """one stain: r = radius in metres of the minor axis; elongated ones get a thinning tail and a satellite dot past the tip"""
        s = m(r) / 1.177
        if direction is None or elong <= 1.05:
            gauss(F, x, y, s * rng.uniform(1.0, 1.25), s, rng.uniform(0, 3.14)); return
        gauss(F, x, y, s * elong, s, direction)
        if tail > 0:
            dx, dy = math.cos(direction), math.sin(direction); L_ = s * elong * 1.6; n = int(3 + tail * 6)
            for i in range(1, n + 1):
                t = i / n; gauss(F, x + dx * (L_ + t * tail * m(r) * 5), y + dy * (L_ + t * tail * m(r) * 5), s * (0.55 - 0.38 * t), s * (0.5 - 0.38 * t), direction, amp=1.0)
            if rng.random() < 0.7:
                d2 = L_ + tail * m(r) * 5 + m(r) * rng.uniform(1.2, 3.0); gauss(F, x + dx * d2, y + dy * d2, s * 0.32, s * 0.28, direction)

    for p in spec.get('pools', []):                                       # (x, y, radius, lobes): a random walk of overlapping blobs
        px_, py_, pr, n = p; x = c + m(px_); y = c + m(py_)
        for i in range(n):
            a = rng.uniform(0, 6.283); d = m(pr) * rng.uniform(0, 0.75) ** 0.8; r = pr * rng.uniform(0.22, 0.5)
            gauss(F, x + math.cos(a) * d, y + math.sin(a) * d, m(r) / 1.177 * rng.uniform(1, 1.5), m(r) / 1.177, rng.uniform(0, 3.14), amp=rng.uniform(0.8, 1.4))
        for i in range(int(n * 1.2)):                                     # spines and scallops round the rim
            a = rng.uniform(0, 6.283); d = m(pr) * rng.uniform(0.85, 1.25); r = pr * rng.uniform(0.03, 0.09)
            drop(x + math.cos(a) * d, y + math.sin(a) * d, r, a, elong=rng.uniform(1.5, 3.5), tail=rng.uniform(0, 0.5))
    for sc in spec.get('scatter', []):                                    # satellite cloud: (x, y, count, spread, rmin, rmax, radial?)
        sx, sy, n, spread, r0, r1 = sc[:6]
        for i in range(n):
            a = rng.uniform(0, 6.283); d = abs(rng.normal(0, spread)) + sc[6] if len(sc) > 6 else abs(rng.normal(0, spread))
            r = math.exp(rng.uniform(math.log(r0), math.log(r1))); el = 1.0 + max(0.0, rng.normal(0.4, 0.5)) * min(1.0, d / spread)
            drop(c + m(sx + math.cos(a) * d), c + m(sy + math.sin(a) * d), r, a, elong=el, tail=rng.uniform(0, 0.6) if el > 1.4 else 0)
    for cast in spec.get('cast', []):                                     # directional spurt: (x0, y0, heading deg, fan deg, count, reach, rmin, rmax)
        x0, y0, hd, fan, n, reach, r0, r1 = cast
        for i in range(n):
            a = math.radians(hd + rng.normal(0, fan)); d = reach * (0.12 + rng.gamma(2.6, 0.24)); r = math.exp(rng.uniform(math.log(r0), math.log(r1))) * (1.25 - 0.5 * min(1, d / reach))
            el = 1.0 + min(4.0, max(0.0, rng.normal(1.0, 0.7)) * (0.4 + d / reach))
            drop(c + m(x0 + math.cos(a) * d), c + m(y0 + math.sin(a) * d), r, a, elong=el, tail=rng.uniform(0.2, 1.0) if el > 1.5 else 0)
    for st in spec.get('streaks', []):                                    # smeared runs: (x0, y0, heading deg, length, width)
        x0, y0, hd, ln, wd = st; a = math.radians(hd); n = int(m(ln) / (m(wd) * 0.5)) + 2
        for i in range(n):
            t = i / (n - 1); wob = math.sin(t * 9 + hd) * wd * 0.5
            gauss(F, c + m(x0 + math.cos(a) * ln * t - math.sin(a) * wob), c + m(y0 + math.sin(a) * ln * t + math.cos(a) * wob), m(wd) * (1.3 - 0.7 * t) * rng.uniform(0.8, 1.2),
                  m(wd) * (1.0 - 0.6 * t) * rng.uniform(0.7, 1.1), a, amp=rng.uniform(0.7, 1.1))
    # organic outlines: domain warp at two scales, then fine scallops near the threshold
    w1x = (spectral(rng, beta=2.6, lo=3, hi=40) - 0.5); w1y = (spectral(rng, beta=2.6, lo=3, hi=40) - 0.5)
    F = warp(F, w1x * m(0.035), w1y * m(0.035))
    fine = spectral(rng, beta=1.2, lo=40, hi=500) - 0.5; F = F + 0.22 * fine * smoothstep(0.15, 0.5, F) * (1 - smoothstep(0.8, 1.4, F))
    core = smoothstep(0.47, 0.53, F)                                       # where liquid sat on the surface
    t = np.where(F > 0.5, 1 - np.exp(-(F - 0.5) * 4.5), 0).astype(np.float32)          # thickness 0..1: quick meniscus rise to a flat top
    low = spectral(rng, beta=2.4, lo=3, hi=30); clot = spectral(rng, beta=2.2, lo=10, hi=160)
    depth = np.clip(smoothstep(0.55, 2.4, F) * (0.6 + 0.8 * low), 0, 1)   # where several drops ran together the layer is deeper and darker
    deep = blur(t, m(0.012)); dry = 1 - smoothstep(0.25, 0.8, deep)       # thin films and small drops dry first; pool centres are still wet
    dry = np.clip(dry * 0.8 + (spectral(rng, beta=2.0, lo=6, hi=80) - 0.5) * 0.5 + spec.get('dry', -0.12), 0, 1)
    jelly = smoothstep(0.66, 0.8, spectral(rng, beta=2.4, lo=5, hi=40)) * smoothstep(0.6, 0.95, deep)      # coagulated lumps in the pools
    # soaked stain halo and fine mist
    halo = blur(core, m(0.022)); stain_n = spectral(rng, beta=1.8, lo=5, hi=200)
    stain = smoothstep(0.10, 0.45, halo * (0.55 + 0.9 * stain_n)) * spec.get('stain', 0.7)
    mist_n = spectral(rng, beta=0.4, lo=120, hi=700); near = smoothstep(0.02, 0.3, blur(core, m(0.06)))
    mist = smoothstep(0.78 - 0.10 * near, 0.84 - 0.10 * near, mist_n) * smoothstep(0.004, 0.05, blur(core, m(0.10))) * 0.9
    alpha = np.clip(np.maximum(np.maximum(core, stain), mist), 0, 1)
    # colour (linear): a wet film is saturated red, deep blood nearly black-red, dried films brown-maroon, the drying rim darkest
    wet = lerp((0.15, 0.007, 0.005), (0.045, 0.003, 0.003), depth)
    dried = lerp((0.150, 0.016, 0.010), (0.075, 0.010, 0.007), smoothstep(0.3, 0.7, clot))
    col = lerp(wet, dried, dry); col = lerp(col, (0.030, 0.002, 0.002), jelly * 0.85)
    rim = core * (1 - smoothstep(0.5, 0.95, F)); col = lerp(col, (0.045, 0.006, 0.005), rim * 0.8)
    stain_col = lerp((0.120, 0.020, 0.012), (0.060, 0.012, 0.008), stain_n)
    col = lerp(stain_col, col, core)
    rough = lerp(0.05 + 0.06 * low, 0.36 + 0.22 * clot, dry); rough = lerp(rough, 0.07, jelly); rough = lerp(0.86, rough, core)
    # height: liquid thickness (about 1 mm, deeper where it pooled), lumps of clot, a wrinkled skin only where it dried
    Hm = t * spec.get('thick', 0.0009) * (0.6 + 0.9 * depth) + blur(jelly, 6.0) * 0.0004 + core * dry * (spectral(rng, beta=1.0, lo=150, hi=600) - 0.5) * 0.00010
    N = normal_map(blur(Hm, 1.0), S / W, strength=1.0)
    ao = 1 - 0.25 * rim
    bc = np.dstack([L.lin2srgb(col), alpha]); orm = np.dstack([ao, np.clip(rough, 0.04, 1), np.zeros_like(ao)])
    return down(bc), down(N), down(orm), {'opaque_fraction': float((down(alpha) > 0.5).mean())}


BLOOD = {
    'Blood_Pool_01': dict(frame='187/1', size=0.9, seed=11, pools=[(0.0, 0.0, 0.17, 26), (0.13, -0.05, 0.08, 9)], scatter=[(0, 0, 150, 0.17, 0.003, 0.02, 0.13)],
                          dresses='dense splat: a lobed pool about 40 cm across with spines, satellite drops and a soaked halo'),
    'Blood_Pool_02': dict(frame='187/3', size=1.1, seed=12, pools=[(0.0, 0.02, 0.21, 34), (-0.2, -0.12, 0.07, 8), (0.19, 0.16, 0.06, 7)], scatter=[(0, 0, 220, 0.2, 0.003, 0.022, 0.17)], dry=-0.4,
                          thick=0.0011, dresses='fresh wet pool about 50 cm across (the bright frame with highlights), two side pools and a wide ring of satellite drops'),
    'Blood_Drips_01': dict(frame='187/2', size=0.6, seed=13, pools=[(-0.11, 0.05, 0.045, 6), (0.07, 0.09, 0.055, 7), (0.10, -0.08, 0.04, 6), (-0.05, -0.1, 0.03, 5)],
                           scatter=[(0, 0, 70, 0.16, 0.002, 0.012)], dresses='four separate thick drips, 6 to 11 cm, with a few satellites'),
    'Blood_Spurt_L_01': dict(frame='188/2', size=1.2, seed=14, cast=[(0.42, -0.05, 172, 24, 150, 0.62, 0.003, 0.013)], pools=[(0.42, -0.04, 0.04, 6)], stain=0.4,
                             dresses='cast-off spatter thrown to the left: elongated drops with tails and satellites fanning out over about a metre from a small source pool'),
    'Blood_Spurt_L_02': dict(frame='188/4', size=1.3, seed=15, cast=[(0.45, 0.0, 180, 14, 130, 0.68, 0.003, 0.014)], streaks=[(0.4, 0.02, 181, 0.42, 0.022), (0.36, -0.06, 187, 0.26, 0.014)],
                             pools=[(0.4, 0.0, 0.07, 10)], dresses='arterial spurt to the left: a pool with two smeared runs and a long narrow fan of drops'),
    'Blood_Spurt_R_01': dict(frame='189/2', size=1.2, seed=16, cast=[(-0.42, 0.03, 6, 26, 160, 0.62, 0.003, 0.013)], pools=[(-0.42, 0.03, 0.04, 6)], stain=0.4,
                             dresses='cast-off spatter thrown to the right: elongated drops with tails over about a metre'),
    'Blood_Spurt_R_02': dict(frame='189/4', size=1.3, seed=17, cast=[(-0.45, 0.0, 0, 15, 140, 0.68, 0.003, 0.014)], streaks=[(-0.4, -0.02, -2, 0.44, 0.022), (-0.36, 0.05, 6, 0.24, 0.014)],
                             pools=[(-0.4, 0.0, 0.075, 10)], dresses='arterial spurt to the right: a pool with two smeared runs and a long narrow fan of drops'),
    'Blood_Drops_Large_01': dict(frame='189/1', size=0.8, seed=18, scatter=[(0, 0, 26, 0.17, 0.012, 0.04), (0, 0, 80, 0.2, 0.003, 0.012)], pools=[(0.02, -0.03, 0.06, 8)],
                                 dresses='loose scatter of large round drops, 2 to 8 cm, round one small pool'),
}


# ---------------------------------------------------------------------------------------------- burns
def burn(spec, seed):
    rng = np.random.default_rng(seed); S = spec['size']; ppm = W / S
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32); X = (xx - W / 2) / ppm; Y = (yy - W / 2) / ppm
    n_lo = spectral(rng, beta=2.4, lo=2, hi=24); n_mid = spectral(rng, beta=2.0, lo=10, hi=120); n_fine = spectral(rng, beta=1.0, lo=120, hi=700)
    # grain-following noise: stretched along the planks (X), so char edges and splinters run with the wood
    g = rng.random((W // 2, W // 16)).astype(np.float32); grain = blur(np.repeat(np.repeat(g, 2, 0), 16, 1), 2.0)
    grain = (grain - grain.min()) / (grain.max() - grain.min())
    rr_all = np.full((W, W), 9.0, np.float32)
    for (cx, cy, R) in spec['centres']:
        dx = X - cx; dy = (Y - cy) * spec.get('aniso', 1.3); r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
        tongues = np.zeros_like(r)                                         # flame-lick tongues at random bearings (the spiky star of the sprite)
        for i in range(spec.get('tongues', 13)):
            a0 = rng.uniform(-np.pi, np.pi); wdt = rng.uniform(0.07, 0.2); ln = rng.uniform(0.12, 0.6) * (1.6 if abs(math.cos(a0)) > 0.8 else 1.0)
            d = np.angle(np.exp(1j * (th - a0))); tongues = np.maximum(tongues, ln * np.exp(-np.abs(d / wdt) ** 1.5))
        Rth = R * (1 + tongues + 0.6 * (n_lo - 0.5)); rr_all = np.minimum(rr_all, r / Rth)
    rr = rr_all + (n_mid - 0.5) * 0.30 + (grain - 0.5) * 0.22 + (n_fine - 0.5) * 0.05
    char = 1 - smoothstep(0.97, 1.0, rr)                                   # crisp char edge
    hole = (1 - smoothstep(0.30, 0.33, rr + (grain - 0.5) * 0.25)) * spec.get('hole', 1.0)          # burnt through in the middle, splintered along the grain
    singe = np.clip(1 - smoothstep(1.0, 1.32, rr + (n_mid - 0.5) * 0.25), 0, 1) * (1 - char)       # brown scorched band outside the char
    soot = np.exp(-(np.clip(rr_all, 0, 9) / 1.5) ** 3.0) * (0.45 + 0.9 * n_mid) * (1 - char)        # thin soot veil beyond that
    pit = 1 - smoothstep(0.25, 1.0, rr)
    spots = smoothstep(0.80, 0.84, spectral(rng, beta=1.2, lo=25, hi=160)) * smoothstep(2.3, 1.1, rr_all) * (1 - char)   # spark burns round it
    char = np.maximum(char, spots)
    # alligatored char: blocks elongated along the grain, cracks between them
    cells = int(S / 0.013); f1, f2, cv = voronoi(W, max(4, int(cells * 0.4)), cells, rng); edge = f2 - f1
    block = smoothstep(0.0, 0.2, edge); crack = 1 - smoothstep(0.0, 0.06, edge)
    f1b, f2b, cvb = voronoi(W, cells * 2, cells * 3, rng); micro = smoothstep(0.0, 0.2, f2b - f1b)
    ash_n = spectral(rng, beta=2.2, lo=6, hi=90)
    ash_m = smoothstep(0.50, 0.85, ash_n * (0.55 + 0.75 * pit)) * char * (1 - hole) * spec.get('ash', 0.6)
    ash_m = np.maximum(ash_m, smoothstep(0.86, 0.9, spectral(rng, beta=0.8, lo=60, hi=400)) * char * 0.8)   # flecks
    ember = smoothstep(0.66, 0.76, spectral(rng, beta=1.4, lo=30, hi=300)) * smoothstep(0.3, 0.9, pit) * char * (1 - hole) * spec.get('rust', 0.5)
    # colour (linear): charcoal 2 to 4 % with a faint sheen on the block faces, cracks near black, ash light grey, scorched wood brown
    ch = lerp(0.018, 0.042, cv)[..., None] * np.array([1.0, 0.98, 0.96], np.float32); ch = ch * (0.7 + 0.3 * micro[..., None]); ch = lerp(ch, (0.014, 0.013, 0.013), crack)
    ash_c = lerp((0.16, 0.155, 0.15), (0.40, 0.39, 0.37), n_fine); ch = lerp(ch, ash_c, ash_m * (0.35 + 0.65 * n_mid))
    ch = lerp(ch, lerp((0.22, 0.07, 0.02), (0.36, 0.15, 0.04), n_fine), ember); ch = lerp(ch, (0.006, 0.006, 0.006), hole)
    singe_c = lerp((0.115, 0.050, 0.018), (0.035, 0.018, 0.010), smoothstep(0.2, 0.95, singe))
    col = lerp(np.float32((0.03, 0.026, 0.023)) + 0 * ch, singe_c, smoothstep(0.0, 0.25, singe)); col = lerp(col, ch, char)
    alpha = np.clip(np.maximum(np.maximum(char, smoothstep(0.0, 0.9, singe) * 0.9), soot * 0.5), 0, 1)
    rough = lerp(0.62 + 0.25 * cv, 0.98, np.maximum(crack, ash_m)); rough = lerp(rough, 1.0, hole); rough = lerp(0.85, rough, char)
    # height: blocks stand 2 mm proud of their cracks, the whole char sinks towards the hole, whose edge drops 12 mm; ash heaps a little
    Hm = char * (block * (0.5 + 0.5 * cv) * 0.0022 + micro * 0.0003 - pit ** 1.3 * spec.get('depth', 0.008)) - hole * 0.012 + ash_m * (n_fine - 0.3) * 0.0014 - singe * 0.0003
    N = normal_map(blur(Hm, 0.7), S / W, strength=1.0)
    ao = 1 - 0.75 * crack * char * (1 - ash_m) - 0.3 * char * smoothstep(0.3, 0.95, pit); ao = lerp(ao, 0.15, hole)
    bc = np.dstack([L.lin2srgb(col), alpha]); orm = np.dstack([np.clip(ao, 0, 1), np.clip(rough, 0.04, 1), np.zeros_like(ao)])
    return down(bc), down(N), down(orm), {'opaque_fraction': float((down(alpha) > 0.5).mean())}


BURN = {
    'Burn_Scorch_01': dict(frame='158/1', size=0.9, seed=31, centres=[(0.0, 0.0, 0.19)], tongues=14, dresses='scorch mark about 55 cm across: alligatored char, a sunken middle with grey ash, soot tongues licking outwards'),
    'Burn_Scorch_02': dict(frame='158/2', size=0.9, seed=32, centres=[(0.02, -0.01, 0.2)], tongues=11, ash=0.4, rust=1.0, depth=0.01, hole=0.0,
                           dresses='scorch mark with a rust-brown ember bed in the middle (the frame with the orange centre), less ash'),
    'Burn_Scorch_03': dict(frame='158/3', size=1.5, seed=33, centres=[(-0.22, 0.2, 0.2), (0.2, -0.17, 0.25)], tongues=12, dresses='two overlapping burns on a diagonal, about 1.1 m end to end, sharing one soot halo'),
}


# ---------------------------------------------------------------------------------------------- output
WEAK = {
    'blood': 'A flat decal: pooled blood has no real meniscus or parallax, only a normal map, so at a grazing 1 m view the thick pools read thinner than they are. Opacity is authored for a mid-toned ground; on very dark ground the soaked halo disappears, on pale stone it reads strong. The sets are static: no drying over time, no interaction with the ground relief (blood does not run into cracks or round pebbles). Unreal decal material (DBuffer, opacity from BC alpha) is not built here.',
    'burn': 'A flat decal: the burnt-through middle is a black patch with a normal-map lip, not a hole, so it cannot show the joists or the depth below that the original frame hints at. The char blocks follow one grain direction (decal X); rotate the decal to the planks it sits on. Soot halo opacity assumes a mid-toned floor. Unreal decal material is not built here.',
}


def write_set(name, spec, kind, fam, seq, gen):
    outdir = os.path.join(L.UNC, fam, name); os.makedirs(outdir, exist_ok=True); bc, N, orm, st = gen(spec, spec['seed']); files = {}
    # outside the opaque part keep the colour (no black fringe when the alpha is filtered)
    for key, arr in (('BC', bc), ('N', N), ('ORM', orm)):
        p = os.path.join(outdir, 'T_Decal_%s_%s.png' % (name, key)); L.save_png(arr, p); files[key] = p
    lum = (bc[..., :3] @ np.array([0.2126, 0.7152, 0.0722]))[bc[..., 3] > 0.5] * 255
    ids = L.origin_ids([fam])[fam]
    man = {'name': 'Decal_' + name, 'class': 'decal (alpha decal texture set; no mesh)', 'decal_size_m': [spec['size'], spec['size']], 'lod0_triangles': 0,
           'dimensions_m': [spec['size'], spec['size'], 0.0],
           'textures': [{'file': L.rel(files['BC']), 'size_px': [W // 2, W // 2], 'channels': 'base colour sRGB + opacity in alpha'},
                        {'file': L.rel(files['N']), 'size_px': [W // 2, W // 2], 'channels': 'tangent normal, OpenGL (green up; flip green on import)'},
                        {'file': L.rel(files['ORM']), 'size_px': [W // 2, W // 2], 'channels': 'R occlusion, G roughness, B metallic (0)'}],
           'materials': ['MI_Decal_' + name], 'material_exception': 'decal set private to this decal; a deferred decal cannot use the tiling library sets of ART_STANDARD.md section 2',
           'build': 'Unclaimed/tools/bl.sh %s %s final' % (SCRIPT, name), 'source_blend': L.rel(os.path.join(outdir, 'Decal_%s.blend' % name)),
           'source_note': 'the source is the height field generated by the build script (seeded, deterministic); the .blend holds the review scene with the decal blended over the ground',
           'families': [fam, '%s frame %s' % (seq, spec['frame'].split('/')[1])], 'origin_ids': {fam: ids},
           'origin_ids_note': 'the family shares its origin IDs between all of its frames; this decal dresses the placements that show frame %s' % spec['frame'],
           'supersedes': 'none (placeholder greybox cards)', 'dresses': spec['dresses'],
           'stats': {'opaque_fraction': round(st['opaque_fraction'], 3), 'albedo_luma_srgb_opaque': {'p1': round(float(np.percentile(lum, 1)), 1), 'mean': round(float(lum.mean()), 1), 'p99': round(float(np.percentile(lum, 99)), 1)},
                     'roughness_opaque': {'p5': round(float(np.percentile(orm[..., 1][bc[..., 3] > 0.5], 5)), 3), 'p95': round(float(np.percentile(orm[..., 1][bc[..., 3] > 0.5], 95)), 3)}},
           'third_party': [], 'status': 'source delivered; not imported into Unreal, not bound in families.json', 'known_weaknesses': WEAK[kind]}
    return outdir, files, man


def render(name, spec, kind, outdir, files, man):
    L.reset(); S = spec['size']; ground = 'park_dirt' if kind == 'blood' else 'weathered_brown_planks'
    R = L.review_setup(ground=None, exposure=-5.0)
    g = L.new_obj('ground', [(-15, -15, 0), (15, -15, 0), (15, 15, 0), (-15, 15, 0)], [(0, 1, 2, 3)], smooth=False)
    t = NT('ground_with_decal'); sset = t.scan(ground, scale=0.6 if kind == 'blood' else 1.1, proj='FLAT')
    gb = t.bsdf; t.set(base=sset['diff'], rough=sset['rough'], normal=t.normalmap(sset['nor_gl'], 1.0))
    uv = t.mapping(t.obj, scale=(1 / S, 1 / S, 1), loc=(0.5, 0.5, 0))
    bc = t.image(files['BC'], 'sRGB', uv, ext='CLIP'); nm = t.image(files['N'], 'Non-Color', uv, ext='CLIP'); orm = t.image(files['ORM'], 'Non-Color', uv, ext='CLIP')
    db = t.node('ShaderNodeBsdfPrincipled'); sp = t.node('ShaderNodeSeparateColor'); t.L.new(orm.outputs[0], sp.inputs[0])
    t.L.new(bc.outputs[0], db.inputs['Base Color']); t.L.new(sp.outputs[1], db.inputs['Roughness']); t.L.new(t.normalmap(nm.outputs[0], 1.0), db.inputs['Normal'])
    mx = t.node('ShaderNodeMixShader'); t.L.new(bc.outputs[1], mx.inputs[0]); t.L.new(gb.outputs[0], mx.inputs[1]); t.L.new(db.outputs[0], mx.inputs[2]); t.L.new(mx.outputs[0], t.out.inputs['Surface'])
    L.assign(g, t.mat); man['third_party'] = [ground]
    L.shot(R, os.path.join(outdir, 'render_beauty.png'), center=(0, 0, 0), radius=S * 0.62, az=20, el=42, fill=0.8, lens=50, spp=192)
    L.shot(R, os.path.join(outdir, 'render_close.png'), center=(S * 0.05, -S * 0.05, 0), radius=S * 0.2, az=-30, el=24, fill=0.9, lens=70, res=(1000, 800), spp=192, fstop=5.6)
    L.save_blend(os.path.join(outdir, 'Decal_%s.blend' % name))
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', outdir)


if __name__ == '__main__':
    a = L.args(); sel = a[0]
    todo = [(n, s, 'blood', 'blood_splat', '%s effects/spurt' % {'187': '187', '188': '188', '189': '189'}[s['frame'][:3]], blood) for n, s in BLOOD.items()] + \
           [(n, s, 'burn', 'burn_hole_decal', '158 struct/details/damage/hole-', burn) for n, s in BURN.items()]
    for n, s, kind, fam, seq, gen in todo:
        if sel in ('all', kind) or n in sel.split(','):
            outdir, files, man = write_set(n, s, kind, fam, seq, gen); render(n, s, kind, outdir, files, man)
