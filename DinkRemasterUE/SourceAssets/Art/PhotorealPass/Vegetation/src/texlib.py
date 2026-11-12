"""Shared numpy texture helpers for the vegetation photoreal pass (no downloads, all synthesised)."""
import numpy as np
from PIL import Image

def rng(seed): return np.random.default_rng(seed)

def fbm(h, w, seed, beta=2.0, ax=1.0, ay=1.0, lo=0.0):
    """Periodic fractal noise in 0..1 by FFT filtering. ax, ay stretch features (>1 = longer along that axis)."""
    r = rng(seed)
    n = r.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None] * h * ay
    fx = np.fft.fftfreq(w)[None, :] * w * ax
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    amp = 1.0 / f ** (beta / 2.0 + 0.5)
    amp[f < lo] = 0
    amp[0, 0] = 0
    o = np.real(np.fft.ifft2(np.fft.fft2(n) * amp))
    o = (o - o.min()) / (o.max() - o.min() + 1e-9)
    return o

def blur(a, s):
    """Periodic gaussian blur via FFT."""
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * s) ** 2 * (fx * fx + fy * fy))
    if a.ndim == 3:
        return np.stack([np.real(np.fft.ifft2(np.fft.fft2(a[..., i]) * g)) for i in range(a.shape[2])], -1)
    return np.real(np.fft.ifft2(np.fft.fft2(a) * g))

def worley(h, w, gx, gy, seed, jitter=0.9, warp=None):
    """Periodic Worley noise on a gx*gy jittered grid. Returns F1, F2 (in cell units), cell id, per-cell random."""
    r = rng(seed)
    px = r.random((gy, gx)) * jitter + (1 - jitter) / 2
    py = r.random((gy, gx)) * jitter + (1 - jitter) / 2
    cr = r.random((gy, gx))
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    u = x / w * gx
    v = y / h * gy
    if warp is not None:
        u = u + warp[0]
        v = v + warp[1]
    ci = np.floor(u).astype(int)
    cj = np.floor(v).astype(int)
    f1 = np.full((h, w), 1e9); f2 = np.full((h, w), 1e9)
    cid = np.zeros((h, w), int); crnd = np.zeros((h, w))
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ii = ci + di; jj = cj + dj
            iw = ii % gx; jw = jj % gy
            dx = ii + px[jw, iw] - u
            dy = jj + py[jw, iw] - v
            d = np.sqrt(dx * dx + dy * dy)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, jw * gx + iw, cid)
            crnd = np.where(closer, cr[jw, iw], crnd)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid, crnd

def sstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-12), 0, 1)
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    if np.ndim(t) == 2 and np.ndim(a) != 2: t = t[..., None]
    return np.asarray(a) * (1 - t) + np.asarray(b) * t

def normal_from_height(hm, strength, wrap=True):
    """hm in arbitrary units; strength = height range in texels. OpenGL (green up; image row 0 = top)."""
    if wrap:
        dx = (np.roll(hm, -1, 1) - np.roll(hm, 1, 1)) * 0.5
        dy = (np.roll(hm, -1, 0) - np.roll(hm, 1, 0)) * 0.5
    else:
        dy, dx = np.gradient(hm)
    nx = -dx * strength
    ny = dy * strength  # image y is down, GL green is up
    nz = np.ones_like(hm)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l, ny / l, nz / l], -1)

def ao_from_height(hm, radii=(3, 9, 27), k=2.5):
    ao = np.ones_like(hm)
    for r_ in radii:
        ao -= k / len(radii) * np.clip(blur(hm, r_) - hm, 0, 1)
    return np.clip(ao, 0.15, 1)

def srgb8(lin):
    lin = np.clip(lin, 0, 1)
    s = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return (s * 255 + 0.5).astype(np.uint8)

def lin8(a): return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)

def save_rgb(path, arr8, alpha8=None):
    if alpha8 is not None:
        Image.fromarray(np.dstack([arr8, alpha8]), 'RGBA').save(path)
    else:
        Image.fromarray(arr8, 'RGB').save(path)

def save_normal(path, n): save_rgb(path, lin8(n * 0.5 + 0.5))

def save_orm(path, ao, rough, metal=None):
    if metal is None: metal = np.zeros_like(ao)
    save_rgb(path, lin8(np.stack([ao, rough, metal], -1)))

def dilate_rgb(rgb, alpha, iters=24):
    """Bleed colour outward from opaque texels so mips / bilinear never pull in background (rgb float HxWx3)."""
    rgb = rgb.copy(); known = alpha > 0.5
    for _ in range(iters):
        acc = np.zeros_like(rgb); cnt = np.zeros(alpha.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            k = np.roll(known, (dy, dx), (0, 1))
            acc += np.roll(rgb, (dy, dx), (0, 1)) * k[..., None]; cnt += k
        new = (~known) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        known |= new
    if (~known).any():
        mean = rgb[known].mean(0)
        rgb[~known] = mean
    return rgb
