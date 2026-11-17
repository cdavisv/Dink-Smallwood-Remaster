"""Translucent fire frames from the HDR flame renders of build_fire_fx.py: an opaque glowing flame body with wisps at
its edges, smoke made from the flames' own past (what burned k steps ago has risen, spread and drifted; rising noise
breaks it into billows; the fire lights it from below) and sparks that rise once per loop. The loop stays closed:
every term is periodic over the frames. numpy and PIL only, so it runs inside Blender and outside.

    encode_loop(hdr_frames, P) -> list of H x W x 4 float arrays (straight sRGB colour + alpha, top row first)
"""
import math
import numpy as np
from PIL import Image, ImageFilter


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _box(a, r, axis):
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def blur(a, sigma):
    """near-Gaussian blur: three box passes per axis (numpy only)"""
    if sigma <= 0.3:
        return a
    r = max(1, int(round(math.sqrt(sigma * sigma * 12 / 3 + 1) / 2 - 0.5)))
    out = a.astype(np.float32)
    for _ in range(3):
        out = _box(_box(out, r, 0), r, 1)
    return out


def shift(a, dy, dx):
    """content moves up by dy px and right by dx px (sub-pixel, bilinear), zero fill"""
    h, w = a.shape
    out = np.zeros_like(a)
    iy, fy = int(math.floor(dy)), dy - math.floor(dy)
    ix, fx = int(math.floor(dx)), dx - math.floor(dx)
    def put(sy, sx, wgt):
        if wgt <= 0: return
        ys0, ys1 = max(0, sy), min(h, h + sy)      # source rows
        xs0, xs1 = max(0, -sx), min(w, w - sx)
        if ys1 <= ys0 or xs1 <= xs0: return
        out[ys0 - sy:ys1 - sy, xs0 + sx:xs1 + sx] += a[ys0:ys1, xs0:xs1] * wgt
    put(iy, ix, (1 - fy) * (1 - fx)); put(iy + 1, ix, fy * (1 - fx)); put(iy, ix + 1, (1 - fy) * fx); put(iy + 1, ix + 1, fy * fx)
    return out


def value_noise(n, cells, rng):
    """periodic 1-D noise over n samples"""
    k = rng.standard_normal(cells)
    x = np.arange(n) * cells / n
    i = np.floor(x).astype(int); f = x - i; f = f * f * (3 - 2 * f)
    return k[i % cells] * (1 - f) + k[(i + 1) % cells] * f


def periodic_fbm(n, h, w, rng, octaves=4, cx=3, cy=3, ct=2, wraps=1):
    """fractal value noise, n x h x w, periodic over the n frames and rising: each octave's lattice wraps a whole number
    of times in y per loop, so frame n equals frame 0"""
    t = np.arange(n, dtype=np.float32)[:, None, None]
    y = np.arange(h, dtype=np.float32)[None, :, None]
    x = np.arange(w, dtype=np.float32)[None, None, :]
    out = np.zeros((n, h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        kx, ky, kt = cx * 2 ** o, cy * 2 ** o, ct * 2 ** min(o, 2)
        lat = rng.random((kt, ky, kx)).astype(np.float32)
        fx = x * kx / w
        fy = y * ky / h + t * (wraps * (o + 1)) * ky / n          # the pattern moves up (towards row 0) as t grows
        ft = t * kt / n
        def split(f, k):
            i = np.floor(f).astype(np.int64); u = f - i; u = u * u * (3 - 2 * u)
            return i % k, (i + 1) % k, u
        x0, x1, ux = split(fx, kx); y0, y1, uy = split(fy, ky); t0, t1, ut = split(ft, kt)
        def at(ti, yi, xi): return lat[ti, yi, xi]
        v = ((at(t0, y0, x0) * (1 - ux) + at(t0, y0, x1) * ux) * (1 - uy) + (at(t0, y1, x0) * (1 - ux) + at(t0, y1, x1) * ux) * uy) * (1 - ut) + \
            ((at(t1, y0, x0) * (1 - ux) + at(t1, y0, x1) * ux) * (1 - uy) + (at(t1, y1, x0) * (1 - ux) + at(t1, y1, x1) * ux) * uy) * ut
        out += v * amp
        tot += amp
        amp *= 0.55
    return out / tot


def encode_loop(hdr, P):
    n = len(hdr)
    h, w = hdr[0].shape[:2]
    rng = np.random.default_rng(P.get('seed', 427))
    # the fire's foot: the render ends on a straight line (the row of timbers); break it into uneven tongues so no ruler
    # edge shows where the card meets a floor or a roof
    foot = float(P.get('foot_px', 0.0)) * h / 512.0
    if foot > 0:
        n1, n2 = value_noise(w, 5, rng), value_noise(w, 13, rng)
        rise = np.clip(0.30 + 0.22 * n1 + 0.12 * n2, 0.0, 0.9) * foot
        rows = (h - 1 - np.arange(h, dtype=np.float32))[:, None]                 # 0 at the bottom row
        # a soft foot: the flames thin out towards the floor over about twice foot_px, from a height that wanders along
        # the fire. A hard cut (the first version) read as a serrated cut-out hovering over the floor.
        keep = np.clip((rows - rise[None, :]) / max(foot * float(P.get('foot_soft', 2.0)), 1.0), 0, 1)
        keep = (keep * keep * (3 - 2 * keep))[..., None]
        hdr = [f[..., :3] * keep for f in hdr]
    # the fire's two ends: the row of burning timbers stops dead, and the flames above it stood behind a plumb line.
    # Thin them out over ends_px, behind a boundary that wanders with height, so the wall of flame ends in wisps.
    ends = float(P.get('ends_px', 0.0)) * w / 512.0
    if ends > 0:
        ever = np.max(np.stack([f[..., :3].max(-1).max(0) for f in hdr]), 0)                 # per column: does it ever burn
        cols = np.nonzero(ever > 0.04 * float(ever.max()))[0]
        if len(cols):
            xl, xr = float(cols[0]), float(cols[-1])
            wob = (value_noise(h, 5, rng) * 0.55 + value_noise(h, 17, rng) * 0.30)[:, None] * ends * 0.5      # by row
            wob2 = (value_noise(h, 6, rng) * 0.55 + value_noise(h, 19, rng) * 0.30)[:, None] * ends * 0.5
            xs = np.arange(w, dtype=np.float32)[None, :]
            left = np.clip((xs - (xl + ends * 0.15 + wob)) / ends, 0, 1)
            right = np.clip(((xr - ends * 0.15 + wob2) - xs) / ends, 0, 1)
            win = (left * left * (3 - 2 * left)) * (right * right * (3 - 2 * right))
            hdr = [f[..., :3] * win[..., None] ** 1.6 for f in hdr]
    lum = [f[..., :3].max(-1) for f in hdr]
    # 1. the flames: an opaque glowing body where the fire is thick, wisps at its edges
    body = [1.0 - np.exp(-l / P['l_alpha']) for l in lum]
    tone = [np.power(1.0 - np.exp(-l / P['l0']), P['gamma']) for l in lum]
    # 2. smoke: what burned k steps ago has risen, spread and drifted
    yy = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None]      # 1 at the top row
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    small = [np.asarray(Image.fromarray(l.astype(np.float32), 'F').resize((w // 4, h // 4), Image.BILINEAR), np.float32) for l in body]
    sway = value_noise(n, 5, rng) * P['sway_px'] / 4.0
    smoke = []
    fbm = periodic_fbm(n, h // 4, w // 4, rng, cx=3, cy=2)
    fine = periodic_fbm(n, h // 4, w // 4, rng, octaves=3, cx=9, cy=7, ct=4, wraps=2)
    for t in range(n):
        acc = np.zeros((h // 4, w // 4), np.float32)
        for k in range(1, P['smoke_taps'] + 1):
            src = small[(t - k * P['smoke_step']) % n]
            age = k / P['smoke_taps']
            rise = (P['rise_px'] * age ** 0.85) / 4.0
            drift = (sway[(t - k * P['smoke_step']) % n] - sway[t]) * age * 0.0 + P['wind_px'] * age ** 1.3 / 4.0 + sway[(t + 7 * k) % n] * age
            young = min(1.0, max(0.0, (age - 0.10) / 0.18))          # smoke shows above the flames, not inside them
            acc += shift(blur(src, (P['sigma0'] + P['sigma1'] * age) / 4.0), rise, drift) * (1.0 - 0.6 * age) * young
        s = acc / P['smoke_taps']
        # billows: the rising field is broken up by rising noise, and thinned where the noise is low
        puff = np.clip((fbm[t] - P['puff_lo']) / (P['puff_hi'] - P['puff_lo']), 0, 1)
        s = s * (0.10 + 1.5 * puff * puff * (3 - 2 * puff)) * (0.55 + 0.9 * fine[t])
        s = np.asarray(Image.fromarray(s, 'F').resize((w, h), Image.BICUBIC), np.float32)
        smoke.append(np.clip(s, 0, None))
    smax = max(float(s.max()) for s in smoke) or 1.0
    edge = np.clip((1.0 - yy) / 0.10, 0, 1) * np.clip((1.0 - np.abs(xx)) / 0.12, 0, 1)      # never touch the frame's top or sides
    edge = edge * edge * (3 - 2 * edge)
    out = []
    bed = None
    if P.get('bed', 0.0) > 0:
        width = blur(np.max(np.stack(lum), 0).max(0)[None, :].repeat(h, 0), 6.0)           # where the fire ever burns, by column
        width = np.clip(width / (width.max() + 1e-6) * 3.0, 0, 1)
        rows = (h - 1 - np.arange(h, dtype=np.float32))[:, None] / (h / 512.0)
        bed = (np.exp(-((rows - 16.0) / 14.0) ** 2) * width * P['bed']).astype(np.float32)
    spark = sparks(n, h, w, P, rng)
    for t in range(n):
        l = lum[t]
        hue = hdr[t][..., :3] / np.maximum(l, 1e-6)[..., None]
        hue = np.where(l[..., None] > 1e-5, hue, 0.0)
        frgb = hue * tone[t][..., None]                              # linear display colour of the flame
        fa = body[t]
        dens = 1.0 - np.exp(-P['smoke_density'] * smoke[t] / smax)
        sa = P['smoke_max'] * dens * edge
        glow = blur(l, 34.0)
        glow = glow / (glow.max() + 1e-6)
        # thin smoke is lighter and browner than its thick cores; the fire lights it from below
        thin = (1.0 - dens)[..., None]
        srgb_lin = np.array(P['smoke_colour'], np.float32)[None, None, :] * (0.7 + 1.9 * thin) + np.array(P['smoke_lit'], np.float32)[None, None, :] * (glow[..., None] ** 1.3)
        # flame over smoke (premultiplied), sparks over both
        pr = frgb * fa[..., None] + srgb_lin * (sa * (1 - fa))[..., None]
        a = fa + sa * (1 - fa)
        if bed is not None:      # the glowing bed the flames stand in: under them, never above
            ba = bed * (0.75 + 0.25 * math.sin(2 * math.pi * (t / n) * 3 + 1.0)) * (1 - a)
            pr = pr + np.array((1.0, 0.30, 0.04), np.float32)[None, None, :] * ba[..., None]
            a = a + ba
        sp = spark[t]
        pr = pr * (1 - sp[..., 3:4]) + sp[..., :3] * sp[..., 3:4]
        a = a + sp[..., 3] * (1 - a)
        a = a * (edge * 0 + 1)
        rgb = pr / np.maximum(a, 1e-4)[..., None]
        out.append(np.concatenate([srgb(rgb), a[..., None]], -1).astype(np.float32))
    return out


def sparks(n, h, w, P, rng):
    """embers torn off the fire: each rises along a wavering path once per loop (or twice), so the loop closes"""
    frames = [np.zeros((h, w, 4), np.float32) for _ in range(n)]
    for _ in range(P['sparks']):
        x0 = rng.uniform(-0.30, 0.30) * w + w / 2
        y0 = h - rng.uniform(0.10, 0.45) * h
        life = int(rng.uniform(0.35, 0.8) * n)
        start = rng.integers(0, n)
        speed = rng.uniform(0.35, 0.75) * h / life
        amp = rng.uniform(4, 22); freq = rng.uniform(1.0, 2.5); ph = rng.uniform(0, 6.28)
        lean = rng.uniform(-0.25, 0.25)
        size = rng.uniform(0.7, 1.5)
        for i in range(life):
            u = i / life
            x = x0 + amp * math.sin(ph + freq * 6.28 * u) * u + lean * i * speed * 0.4
            y = y0 - speed * i * (1.0 - 0.35 * u)
            bright = (1.0 - u) ** 1.3 * min(1.0, i / 2.0)
            if not (4 < x < w - 5 and 4 < y < h - 8) or bright < 0.03:
                continue
            f = frames[(start + i) % n]
            ix, iy = int(x), int(y)
            for dy in range(-3, 7):
                for dx in range(-3, 4):
                    ddy = iy + dy + 0.5 - y
                    stretch = 3.0 if ddy > 0 else 1.0        # a tail below the ember: it is moving up
                    d2 = (ix + dx + 0.5 - x) ** 2 + (ddy / stretch) ** 2
                    g = math.exp(-d2 / (2 * (0.8 * size) ** 2)) * bright
                    if g < 0.02: continue
                    px = f[iy + dy, ix + dx]
                    col = np.array((1.0, 0.55 + 0.35 * bright, 0.12 + 0.3 * bright), np.float32)
                    px[:3] = px[:3] * (1 - g) + col * g
                    px[3] = max(px[3], min(1.0, g * 1.4))
    return frames


DEFAULT = dict(l_alpha=0.45, l0=2.2, gamma=0.5, smoke_taps=18, smoke_step=2, rise_px=300.0, sigma0=4.0, sigma1=22.0, sway_px=26.0, wind_px=22.0,
               puff_lo=0.34, puff_hi=0.72, smoke_density=3.2, smoke_max=0.55, smoke_colour=(0.030, 0.026, 0.024), smoke_lit=(0.30, 0.11, 0.03), sparks=46, seed=427, foot_px=30.0, foot_soft=2.0, ends_px=64.0, bed=0.0)
