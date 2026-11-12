"""Shared numpy toolkit for the Dink remaster tileable material library.

Everything here is periodic by construction (FFT noise, wrapped warps, wrapped
Voronoi), so every texture tiles exactly. All physical quantities are in metres
so recipes look the same at 1024 or 2048 px.
"""
import numpy as np

F32 = np.float32


class Ctx:
    """One material canvas: n x n pixels covering T metres."""

    def __init__(self, n, T, seed):
        self.n, self.T, self.seed = n, float(T), int(seed)
        self.px = self.T / n
        y, x = np.mgrid[0:n, 0:n]
        self.X = ((x + 0.5) / n).astype(F32)
        self.Y = ((y + 0.5) / n).astype(F32)
        self._salt = 0

    def rng(self, salt=None):
        if salt is None:
            self._salt += 1
            salt = 1000 + self._salt
        return np.random.default_rng([self.seed, int(salt)])


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1).astype(F32)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def norm01(a, lo=1.0, hi=99.0):
    l, h = np.percentile(a, [lo, hi])
    return np.clip((a - l) / max(h - l, 1e-9), 0, 1).astype(F32)


def _freq_r(n, ax=1.0, ay=1.0):
    kx = np.fft.rfftfreq(n) * n * ax
    ky = np.fft.fftfreq(n) * n * ay
    return np.sqrt(kx[None, :] ** 2 + ky[:, None] ** 2).astype(F32)


def fbm(c, lmax, lmin, a=1.0, aniso=(1.0, 1.0), salt=None):
    """Periodic band-limited noise, unit std. Features between lmax and lmin metres.
    amplitude spectrum ~ r^-a. aniso=(ax,ay): ax>1 elongates features along x."""
    n = c.n
    r = _freq_r(n, aniso[0], aniso[1])
    fmin = c.T / lmax
    fmax = min(c.T / lmin, 0.45 * n)
    win = smoothstep(fmin * 0.6, fmin, r) * (1 - smoothstep(fmax, fmax * 1.25, r))
    amp = (np.maximum(r, 0.5) ** (-a)) * win
    w = c.rng(salt).standard_normal((n, n)).astype(F32)
    s = np.fft.rfft2(w) * amp
    out = np.fft.irfft2(s, s=(n, n)).astype(F32)
    out -= out.mean()
    out /= max(out.std(), 1e-9)
    return out


def ridged(c, lmax, lmin, a=1.0, aniso=(1.0, 1.0), salt=None, power=1.0):
    """1 on creases, 0 away from them (periodic)."""
    f = fbm(c, lmax, lmin, a, aniso, salt)
    return (1.0 - np.clip(np.abs(f) / 1.2, 0, 1)) ** power


def gblur(a, sigma_px):
    if sigma_px < 0.3:
        return a
    n = a.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    g = np.exp(-2 * np.pi ** 2 * sigma_px ** 2 * (fx ** 2 + fy ** 2)).astype(F32)
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=(n, n)).astype(F32)


def sample(a, x, y):
    """Bilinear lookup with wrap. x,y are pixel coords (float arrays)."""
    n = a.shape[0]
    x0 = np.floor(x)
    y0 = np.floor(y)
    fx = (x - x0).astype(F32)
    fy = (y - y0).astype(F32)
    x0 = x0.astype(np.int32) % n
    y0 = y0.astype(np.int32) % n
    x1 = (x0 + 1) % n
    y1 = (y0 + 1) % n
    if a.ndim == 3:
        return np.stack([sample(a[..., k], x, y) for k in range(a.shape[2])], -1)
    top = a[y0, x0] * (1 - fx) + a[y0, x1] * fx
    bot = a[y1, x0] * (1 - fx) + a[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def warp(c, a, ax_m, ay_m=None):
    """Displace image a by periodic offset fields (metres)."""
    ay_m = ax_m if ay_m is None else ay_m
    yy, xx = np.mgrid[0:c.n, 0:c.n].astype(F32)
    return sample(a, xx + ax_m / c.px, yy + ay_m / c.px)


def ramp(t, stops):
    """Piecewise-linear colour ramp. stops: [(pos,(r,g,b)),...] -> (...,3) float32 (0..255)."""
    pos = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], dtype=F32)
    t = np.asarray(t, dtype=F32)
    return np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], -1).astype(F32)


def mix(a, b, t):
    t = np.asarray(t, dtype=F32)
    if a.ndim == 3 and t.ndim == 2:
        t = t[..., None]
    return a + (b - a) * t


# ---------------------------------------------------------------- Voronoi ---
def cell_offsets(c, g, jitter, salt, stagger=0.0, gy=None):
    """Per-cell centre offsets (gy,g) inside cell units. stagger shifts odd rows by half."""
    gy = gy or g
    r = c.rng(salt)
    ox = 0.5 + (r.random((gy, g)) - 0.5) * jitter
    oy = 0.5 + (r.random((gy, g)) - 0.5) * jitter
    if stagger:
        ox = ox * (1 - stagger * 0.5) + 0.25 * stagger + 0.5 * stagger * (np.arange(gy)[:, None] % 2)
    return ox.astype(F32), oy.astype(F32)


def voronoi(u, v, g, ox, oy, reach=1, gy=None):
    """u,v unwrapped coords in cell units. Returns F1,F2,idx,dx,dy (to nearest centre)."""
    gy = gy or g
    i0 = np.floor(u).astype(np.int32)
    j0 = np.floor(v).astype(np.int32)
    F1 = np.full(u.shape, 9e9, F32)
    F2 = np.full(u.shape, 9e9, F32)
    idx = np.zeros(u.shape, np.int32)
    ddx = np.zeros(u.shape, F32)
    ddy = np.zeros(u.shape, F32)
    for dj in range(-reach, reach + 1):
        cj = j0 + dj
        wj = cj % gy
        for di in range(-reach, reach + 1):
            ci = i0 + di
            wi = ci % g
            dx = u - (ci + ox[wj, wi])
            dy = v - (cj + oy[wj, wi])
            d = dx * dx + dy * dy
            closer = d < F1
            second = (~closer) & (d < F2)
            F2 = np.where(closer, F1, np.where(second, d, F2))
            idx = np.where(closer, wj * g + wi, idx)
            ddx = np.where(closer, dx, ddx)
            ddy = np.where(closer, dy, ddy)
            F1 = np.where(closer, d, F1)
    return np.sqrt(F1), np.sqrt(F2), idx, ddx, ddy


def by_id(c, idx, count, salt, lo=0.0, hi=1.0):
    """Random value per cell id, gathered per pixel."""
    r = c.rng(salt).random(count).astype(F32) * (hi - lo) + lo
    return r[idx]


# --------------------------------------------------- oriented object splats ---
def splat(c, g, salt, half_len, aspect, kind="ellipse", jitter=1.0, zrange=1.0, u=None, v=None):
    """Scatter one oriented object per grid cell (g x g per tile), objects may spill
    into neighbours (3x3 search, so half_len*(1+aspect) must stay <~1.3 cells).
    half_len: (lo,hi) cell units. aspect: (lo,hi) width/length.
    Returns dict(z, rid, lx, ly, edge, hit, ang) of the top-most object per pixel."""
    n = c.n
    r = c.rng(salt)
    ox = (0.5 + (r.random((g, g)) - 0.5) * jitter).astype(F32)
    oy = (0.5 + (r.random((g, g)) - 0.5) * jitter).astype(F32)
    ang = (r.random((g, g)) * np.pi).astype(F32)
    hl = (half_len[0] + r.random((g, g)) * (half_len[1] - half_len[0])).astype(F32)
    asp = (aspect[0] + r.random((g, g)) * (aspect[1] - aspect[0])).astype(F32)
    zz = (r.random((g, g)) * zrange).astype(F32)
    rid = r.random((g, g)).astype(F32)
    if u is None:
        u = c.X * g
        v = c.Y * g
    i0 = np.floor(u).astype(np.int32)
    j0 = np.floor(v).astype(np.int32)
    best = np.full((n, n), -1e9, F32)
    out = {k: np.zeros((n, n), F32) for k in ("rid", "lx", "ly", "edge", "ang")}
    for dj in (-1, 0, 1):
        cj = j0 + dj
        wj = cj % g
        for di in (-1, 0, 1):
            ci = i0 + di
            wi = ci % g
            dx = u - (ci + ox[wj, wi])
            dy = v - (cj + oy[wj, wi])
            a_ = ang[wj, wi]
            ca, sa = np.cos(a_), np.sin(a_)
            L = hl[wj, wi]
            lx = (dx * ca + dy * sa) / L
            ly = (-dx * sa + dy * ca) / (L * asp[wj, wi])
            if kind == "leaf":
                w = np.clip(1 - lx * lx, 0, 1) ** 0.8
                t = np.abs(ly) / np.maximum(w, 1e-4)
                inside = (np.abs(lx) < 1) & (t < 1)
                prof = np.sqrt(np.clip(1 - t * t, 0, 1)) * np.sqrt(w)
            elif kind == "needle":
                w = np.clip(1 - lx * lx * lx * lx, 0, 1)
                t = np.abs(ly) / np.maximum(w, 1e-4)
                inside = (np.abs(lx) < 1) & (t < 1)
                prof = np.sqrt(np.clip(1 - t * t, 0, 1))
            elif kind == "angular":
                q = np.abs(lx) + np.abs(ly)
                inside = q < 1
                t = np.clip(q, 0, 1)
                prof = np.clip(1 - q, 0, 1)
            elif kind == "boot":
                lxs = lx
                wf = 0.95 * np.sqrt(np.clip(1 - ((lxs + 0.45) / 0.58) ** 2, 0, 1))
                wh = 0.80 * np.sqrt(np.clip(1 - ((lxs - 0.64) / 0.30) ** 2, 0, 1))
                w = np.where(lxs < 0.2, wf, np.where(lxs > 0.32, wh, 0.0))
                t = np.abs(ly) / np.maximum(w, 1e-4)
                inside = (w > 0.02) & (t < 1)
                prof = np.sqrt(np.clip(1 - t * t, 0, 1))
            else:  # ellipse
                q = lx * lx + ly * ly
                inside = q < 1
                t = np.sqrt(np.clip(q, 0, 1))
                prof = np.sqrt(np.clip(1 - q, 0, 1))
            z = zz[wj, wi] + 0.35 * prof
            z = np.where(inside, z, -1e9)
            better = z > best
            best = np.where(better, z, best)
            out["rid"] = np.where(better, rid[wj, wi], out["rid"])
            out["lx"] = np.where(better, lx, out["lx"])
            out["ly"] = np.where(better, ly, out["ly"])
            out["edge"] = np.where(better, 1 - t, out["edge"])
            out["ang"] = np.where(better, a_, out["ang"])
    hit = best > -1e8
    out["hit"] = hit
    out["z"] = np.where(hit, best, 0).astype(F32)  # 0..zrange+0.35 layered height (unitless)
    return out


# ------------------------------------------------------------ ragged rows ---
def ragged_rows(c, heights_m, widths_fn, warp_x=None, warp_y=None, salt=100):
    """Rows of varying height, each split in segments (butt joints). All rows span
    exactly T metres so the layout tiles. widths_fn(row, rng) -> widths (m, sum==T).
    warp_x/warp_y: metre offsets per pixel to roughen the edges."""
    T = c.T
    hts = np.array(heights_m, float)
    assert abs(hts.sum() - T) < 1e-6, hts.sum()
    cum = np.concatenate([[0], np.cumsum(hts)])
    yy = c.Y * T + (0 if warp_y is None else warp_y)
    xx = c.X * T + (0 if warp_x is None else warp_x)
    yy = np.mod(yy, T)
    xx = np.mod(xx, T)
    row = np.clip(np.searchsorted(cum, yy, side="right") - 1, 0, len(hts) - 1)
    v = (yy - cum[row]) / hts[row]
    sid = np.zeros(c.n * c.n, np.int32).reshape(c.n, c.n)
    u = np.zeros_like(xx)
    wseg = np.zeros_like(xx)
    seg_count = 0
    r = c.rng(salt)
    for ri in range(len(hts)):
        res = widths_fn(ri, r)
        w, shift = res if isinstance(res, tuple) else (res, 0.0)
        w = np.asarray(w, float)
        assert abs(w.sum() - T) < 1e-6, (ri, w.sum())
        wc = np.concatenate([[0], np.cumsum(w)])
        m = row == ri
        xs = np.mod(xx[m] - shift, T)
        si = np.clip(np.searchsorted(wc, xs, side="right") - 1, 0, len(w) - 1)
        sid[m] = seg_count + si
        u[m] = (xs - wc[si]) / w[si]
        wseg[m] = w[si]
        seg_count += len(w)
    return dict(row=row, sid=sid, u=u.astype(F32), v=v.astype(F32), w=wseg.astype(F32),
                h=hts[row].astype(F32), nseg=seg_count, xx=xx, yy=yy)


def even_widths(count, T):
    return lambda ri, r: np.full(count, T / count)


def random_widths(lo, hi, T):
    def fn(ri, r):
        w = []
        while sum(w) < T:
            w.append(r.uniform(lo, hi))
        w = np.array(w)
        # drop last, rescale so the row closes exactly
        if len(w) > 1 and w[:-1].sum() > T - lo:
            w = w[:-1]
        return w * (T / w.sum())
    return fn


# ----------------------------------------------------------------- maps ---
def srgb_to_lin(a):
    a = np.clip(a / 255.0, 0, 1)
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).astype(F32)


def lin_to_srgb(a):
    a = np.clip(a, 0, 1)
    return (np.where(a <= 0.0031308, a * 12.92, 1.055 * a ** (1 / 2.4) - 0.055) * 255.0).astype(F32)


def fit_albedo(rgb, lo=32.0, hi=238.0, knee=5.0):
    """Smoothly keep luma >= lo and max channel <= hi (physically plausible albedo)."""
    L = rgb @ np.array([0.2126, 0.7152, 0.0722], F32)
    x = L - lo
    L2 = lo + 0.5 * (x + np.sqrt(x * x + knee * knee))
    rgb = rgb + (L2 - L)[..., None]
    m = rgb.max(-1)
    y = hi - m
    m2 = hi - 0.5 * (y + np.sqrt(y * y + knee * knee))
    m2 = np.where(m > hi - 3 * knee, m2, m)
    rgb = rgb * (m2 / np.maximum(m, 1e-3))[..., None]
    return np.clip(rgb, 0, 255)


def normals_from_height(h, px, gain=1.0):
    """OpenGL tangent-space normal (X right, Y up in image = -row). h in metres."""
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px)
    gr = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px)  # d/drow (down)
    nx = -gx * gain
    ny = gr * gain
    nz = np.ones_like(nx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + 1)
    return np.stack([nx * inv, ny * inv, nz * inv], -1).astype(F32)


def cavity_ao(h, px, strength=1.0):
    """Cheap multi-scale height-cavity ambient occlusion."""
    occ = np.zeros_like(h)
    for s_m, w in ((0.006, 0.35), (0.02, 0.35), (0.07, 0.30)):
        s = max(s_m / px, 1.0)
        d = (gblur(h, s) - h) / s_m
        occ += w * np.clip(d * 0.9, 0, 1)
    return np.clip(1 - strength * occ, 0.25, 1).astype(F32)


def finish(c, alb, h, rough, ao=None, ao_strength=1.0, normal_gain=1.0, h_soften_px=0.6):
    """Package a material: returns dict of float arrays (+metadata) ready for writing."""
    h = h.astype(F32)
    hs = gblur(h, h_soften_px)
    nrm = normals_from_height(hs, c.px, normal_gain)
    occ = cavity_ao(hs, c.px, ao_strength)
    if ao is not None:
        occ = occ * ao
    return dict(alb=fit_albedo(alb.astype(F32)), height=h, rough=np.clip(rough, 0.18, 1.0).astype(F32),
                ao=np.clip(occ, 0.2, 1).astype(F32), normal=nrm, normal_gain=normal_gain, T=c.T)


def box_down(a):
    return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])


def downsample_set(m, c_px):
    """2x downsample of a finished set (albedo averaged in linear light, normals rebuilt)."""
    alb = lin_to_srgb(box_down(srgb_to_lin(m["alb"])))
    h = box_down(m["height"])
    nrm = normals_from_height(h, c_px * 2, m["normal_gain"])
    return dict(alb=alb, height=h, rough=box_down(m["rough"]), ao=box_down(m["ao"]), normal=nrm,
                normal_gain=m["normal_gain"], T=m["T"])


def joint_dist(c, i, j, warp_m=None):
    """Distance (m) to the nearest line of an integer-vector joint set (periodic, straight/angular).
    Lines run where i*X + j*Y is an integer; spacing T/sqrt(i^2+j^2)."""
    nrm = float(np.hypot(i, j))
    ph = i * c.X + j * c.Y
    if warp_m is not None:
        ph = ph + warp_m * nrm / c.T
    fr = ph - np.floor(ph)
    return (np.minimum(fr, 1 - fr) * c.T / nrm).astype(F32)


def mineral_flecks(c, density=1.0):
    """Tiny quartz / mica / dark-grain flecks (masks 0..1). Millimetre scale."""
    q = smoothstep(2.35 / density, 3.0, fbm(c, 0.008, 0.0016, a=0.1))
    m = smoothstep(2.55 / density, 3.2, fbm(c, 0.006, 0.0014, a=0.1))
    d = smoothstep(2.0 / density, 2.8, fbm(c, 0.010, 0.002, a=0.1))
    return q, m, d
