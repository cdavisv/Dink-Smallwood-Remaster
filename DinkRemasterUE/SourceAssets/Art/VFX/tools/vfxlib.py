"""Shared procedural-texture toolkit for the Dink remaster VFX sources.

numpy + Pillow only. Everything is deterministic from integer seeds.
Conventions: images are float32 arrays shaped (H, W[, C]) with row 0 at the TOP
(image convention). Flame/smoke "up" is therefore -row; helpers take v in [0,1]
with v=0 at the bottom of a cell.
"""
import hashlib
import numpy as np
from PIL import Image

F32 = np.float32


# --------------------------------------------------------------------------
# Gradient noise (periodic per axis, optional) -------------------------------
# --------------------------------------------------------------------------
class Noise:
    """3D gradient (Perlin) noise with per-axis integer lattice periods.

    A period of 0 means "no wrap" on that axis.  Octave k of an fBm uses
    frequency 2**k and period p*2**k, so a coordinate shift of exactly one base
    period is a perfect loop for every octave.
    """

    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        self.perm = rng.permutation(256).astype(np.int32)
        g = rng.normal(size=(256, 3))
        g /= np.linalg.norm(g, axis=1, keepdims=True)
        self.gx, self.gy, self.gz = (g[:, i].astype(F32) for i in range(3))

    def perlin(self, x, y, z, px=0, py=0, pz=0):
        x = np.asarray(x, F32); y = np.asarray(y, F32); z = np.asarray(z, F32)
        x, y, z = np.broadcast_arrays(x, y, z)
        xi = np.floor(x); yi = np.floor(y); zi = np.floor(z)
        xf = x - xi; yf = y - yi; zf = z - zi
        ix = xi.astype(np.int64); iy = yi.astype(np.int64); iz = zi.astype(np.int64)
        P = self.perm

        def fade(t):
            return t * t * t * (t * (t * F32(6) - F32(15)) + F32(10))

        u = fade(xf); v = fade(yf); w = fade(zf)

        def wrap(i, p):
            return (i % p if p else i) & 255

        cx = [wrap(ix, px), wrap(ix + 1, px)]
        cy = [wrap(iy, py), wrap(iy + 1, py)]
        cz = [wrap(iz, pz), wrap(iz + 1, pz)]
        out = None
        res = {}
        for dz in (0, 1):
            for dy in (0, 1):
                for dx in (0, 1):
                    h = P[(P[(P[cx[dx]] + cy[dy]) & 255] + cz[dz]) & 255]
                    res[(dx, dy, dz)] = (self.gx[h] * (xf - dx) + self.gy[h] * (yf - dy)
                                         + self.gz[h] * (zf - dz))
        def lerp(a, b, t):
            return a + (b - a) * t
        x00 = lerp(res[(0, 0, 0)], res[(1, 0, 0)], u)
        x10 = lerp(res[(0, 1, 0)], res[(1, 1, 0)], u)
        x01 = lerp(res[(0, 0, 1)], res[(1, 0, 1)], u)
        x11 = lerp(res[(0, 1, 1)], res[(1, 1, 1)], u)
        y0 = lerp(x00, x10, v)
        y1 = lerp(x01, x11, v)
        return lerp(y0, y1, w) * F32(1.6)  # ~[-1,1]

    def fbm(self, x, y, z, octaves=5, px=0, py=0, pz=0, gain=0.5, lac=2.0, ridge=False):
        """Returns roughly [-1,1] (or [0,1] when ridge/billow is requested)."""
        amp = 1.0; tot = 0.0; acc = 0
        for k in range(octaves):
            f = lac ** k
            n = self.perlin(x * f, y * f, z * f,
                            int(px * f) if px else 0, int(py * f) if py else 0,
                            int(pz * f) if pz else 0)
            if ridge:
                n = 1.0 - np.abs(n)
            acc = acc + n * F32(amp)
            tot += amp; amp *= gain
        return acc / F32(tot)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1).astype(F32)
    return t * t * (3 - 2 * t)


def fft_blur(img, sigma):
    """Periodic Gaussian blur via FFT (last two axes of a 2D or HxWxC array)."""
    if sigma <= 0:
        return img
    a = np.asarray(img, F32)
    squeeze = a.ndim == 2
    if squeeze:
        a = a[..., None]
    H, W = a.shape[:2]
    fy = np.fft.fftfreq(H)[:, None]; fx = np.fft.fftfreq(W)[None, :]
    k = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * (fx ** 2 + fy ** 2)).astype(F32)
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        out[..., c] = np.fft.ifft2(np.fft.fft2(a[..., c]) * k).real
    return out[..., 0] if squeeze else out


def resize(img, size, resample=Image.BILINEAR):
    """Resize a float HxW or HxWxC array to (w,h) via per-channel float PIL."""
    a = np.asarray(img, F32)
    w, h = size
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a, "F").resize((w, h), resample), F32)
    return np.stack([np.asarray(Image.fromarray(a[..., c], "F").resize((w, h), resample), F32)
                     for c in range(a.shape[2])], -1)


# --------------------------------------------------------------------------
# Worley / cellular, curl ----------------------------------------------------
# --------------------------------------------------------------------------
def worley_tile(size, cells, seed, jitter=1.0, want_id=False):
    """Tileable 2D Worley. Returns F1, F2 distances in cell units (and a
    per-cell random id in [0,1) of the nearest point when want_id)."""
    rng = np.random.default_rng(seed)
    pts = (rng.random((cells, cells, 2)) * jitter + (1 - jitter) * 0.5).astype(F32)
    ys, xs = np.mgrid[0:size, 0:size].astype(F32) * (cells / size)
    cx = np.floor(xs).astype(int); cy = np.floor(ys).astype(int)
    f1 = np.full((size, size), 9.0, F32); f2 = f1.copy()
    ids = rng.random((cells, cells)).astype(F32)
    cid = np.zeros((size, size), F32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            nx = cx + ox; ny = cy + oy
            p = pts[ny % cells, nx % cells]
            d = np.hypot(nx + p[..., 0] - xs, ny + p[..., 1] - ys)
            new_f2 = np.where(d < f1, f1, np.minimum(f2, d))
            if want_id:
                cid = np.where(d < f1, ids[ny % cells, nx % cells], cid)
            f1 = np.minimum(f1, d)
            f2 = new_f2
    return (f1, f2, cid) if want_id else (f1, f2)


def perlin_tile(size, freq, seed, octaves=5, gain=0.5):
    n = Noise(seed)
    ys, xs = np.mgrid[0:size, 0:size].astype(F32) / size * freq
    return n.fbm(xs, ys, np.full_like(xs, 0.37), octaves, px=freq, py=freq, gain=gain)


def curl_from_potential(psi):
    """Periodic curl of a scalar potential on a unit grid -> (vx, vy)."""
    dpdy = (np.roll(psi, -1, 0) - np.roll(psi, 1, 0)) * 0.5
    dpdx = (np.roll(psi, -1, 1) - np.roll(psi, 1, 1)) * 0.5
    return dpdy, -dpdx


# --------------------------------------------------------------------------
# Colour: blackbody ----------------------------------------------------------
# --------------------------------------------------------------------------
def _g(l, mu, s1, s2):
    s = np.where(l < mu, s1, s2)
    return np.exp(-0.5 * ((l - mu) / s) ** 2)


def _cie(l):  # Wyman, Sloan, Shirley 2013 multi-lobe fit of CIE 1931
    x = 1.056 * _g(l, 599.8, 37.9, 31.0) + 0.362 * _g(l, 442.0, 16.0, 26.7) - 0.065 * _g(l, 501.1, 20.4, 26.2)
    y = 0.821 * _g(l, 568.8, 46.9, 40.5) + 0.286 * _g(l, 530.9, 16.3, 31.1)
    z = 1.217 * _g(l, 437.0, 11.8, 36.0) + 0.681 * _g(l, 459.0, 26.0, 13.8)
    return x, y, z


_XYZ2RGB = np.array([[3.2406, -1.5372, -0.4986],
                     [-0.9689, 1.8758, 0.0415],
                     [0.0557, -0.2040, 1.0570]])


def blackbody_linear_rgb(kelvin):
    """Planck radiance integrated against CIE 1931 -> linear sRGB (unnormalised,
    relative units).  Negative (out-of-gamut) components are clipped."""
    kelvin = np.atleast_1d(np.asarray(kelvin, np.float64))
    lam = np.arange(360.0, 831.0, 5.0)
    x, y, z = _cie(lam)
    lm = lam * 1e-9
    h, c, kB = 6.62607e-34, 2.99792458e8, 1.380649e-23
    out = np.zeros((kelvin.size, 3))
    for i, T in enumerate(kelvin):
        B = 1.0 / (lm ** 5 * (np.exp(h * c / (lm * kB * T)) - 1.0))
        XYZ = np.array([np.sum(B * x), np.sum(B * y), np.sum(B * z)])
        out[i] = np.clip(_XYZ2RGB @ XYZ, 0, None)
    return out


class FireRamp:
    """Maps normalised temperature t in [0,1] -> display colour.

    t=0 -> k_lo, t=1 -> k_hi.  Chromaticity is the true blackbody chromaticity;
    radiance is compressed (L/Lref)**gamma because a camera/eye adapts to the
    huge Planck dynamic range, then a soft filmic shoulder maps to [0,1].
    """

    def __init__(self, k_lo=850.0, k_hi=2350.0, ref=1900.0, gamma=0.42, exposure=1.25, n=512):
        self.k_lo, self.k_hi, self.n = k_lo, k_hi, n
        ks = np.linspace(k_lo, k_hi, n)
        rgb = blackbody_linear_rgb(ks)
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
        lref = (blackbody_linear_rgb(ref) @ np.array([0.2126, 0.7152, 0.0722]))[0]
        chroma = rgb / np.maximum(rgb.max(1, keepdims=True), 1e-12)
        mult = (lum / lref) ** gamma * exposure
        hdr = chroma * mult[:, None]
        self.hdr = hdr.astype(F32)                       # linear, may exceed 1
        self.ldr = (1 - np.exp(-self.hdr * 1.6)).astype(F32)  # filmic-ish shoulder
        self.kelvin = ks

    def lookup_linear(self, t, hdr=False):
        t = np.clip(np.asarray(t, F32), 0, 1) * (self.n - 1)
        i0 = np.floor(t).astype(int); i1 = np.minimum(i0 + 1, self.n - 1); f = (t - i0)[..., None]
        tab = self.hdr if hdr else self.ldr
        return tab[i0] * (1 - f) + tab[i1] * f


def srgb_encode(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055).astype(F32)


def srgb_decode(s):
    s = np.clip(s, 0, 1)
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4).astype(F32)


# --------------------------------------------------------------------------
# Image helpers --------------------------------------------------------------
# --------------------------------------------------------------------------
def bleed_colour(rgb, a, passes=3, sigma=2.5):
    """Extend colour into transparent texels (premultiply-friendly, no dark
    fringes under bilinear/mip filtering).  rgb straight, a in [0,1]."""
    out = rgb.copy()
    cov = a.copy()
    acc = rgb * a[..., None]
    w = a.copy()
    s = sigma
    for _ in range(passes):
        bl_rgb = fft_blur(acc, s); bl_w = fft_blur(w, s)
        est = bl_rgb / np.maximum(bl_w[..., None], 1e-6)
        mask = (a < 0.04)[..., None]
        out = np.where(mask, est, out)
        acc = np.where(mask, est * np.maximum(bl_w[..., None], 1e-6), acc)
        w = np.maximum(w, bl_w)
        s *= 1.8
    return out


def to_u8(a):
    return np.clip(np.rint(np.asarray(a) * 255.0), 0, 255).astype(np.uint8)


def save_png(path, arr_u8):
    if arr_u8.ndim == 2:
        im = Image.fromarray(arr_u8, "L")
    else:
        im = Image.fromarray(arr_u8, "RGBA" if arr_u8.shape[2] == 4 else "RGB")
    im.save(path, optimize=True, compress_level=9)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def window_edges(h, w, margin):
    """Smooth 0..1 window that is 0 on the cell border (margin as fraction)."""
    ys = (np.arange(h, dtype=F32) + 0.5) / h; xs = (np.arange(w, dtype=F32) + 0.5) / w
    wy = smoothstep(0, margin, ys) * smoothstep(0, margin, 1 - ys)
    wx = smoothstep(0, margin, xs) * smoothstep(0, margin, 1 - xs)
    return wy[:, None] * wx[None, :]


def cell_origins(n, atlas):
    """Pixel origin and size of each of n cells along one axis of an atlas.
    Cell size is floor(atlas/n) so n that don't divide the atlas (6) stay in a
    power-of-two canvas; Unreal's UV cell is atlas/n so drift is <1 px."""
    size = atlas // n
    return [int(round(i * atlas / n)) for i in range(n)], size


def pack_atlas(frames, cols, rows, atlas, channels=4, fill=0.0):
    """frames: list of HxWxC float arrays (cell-sized). Returns atlas float array."""
    xs, cw = cell_origins(cols, atlas)
    ys, ch = cell_origins(rows, atlas)
    out = np.full((atlas, atlas, channels), fill, F32)
    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        out[ys[r]:ys[r] + ch, xs[c]:xs[c] + cw] = f[:ch, :cw]
    return out


def atlas_frame(atlas_img, i, cols, rows):
    A = atlas_img.shape[0]
    xs, cw = cell_origins(cols, A); ys, ch = cell_origins(rows, A)
    r, c = divmod(i, cols)
    return atlas_img[ys[r]:ys[r] + ch, xs[c]:xs[c] + cw]
