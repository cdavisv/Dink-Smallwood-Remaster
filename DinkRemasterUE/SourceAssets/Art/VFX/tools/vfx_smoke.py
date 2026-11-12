"""Smoke / dust: low-res density volumes, 6-way light baking, projected to flipbooks."""
import numpy as np
from vfxlib import *


def _grid(W, H, D):
    xs = (np.arange(W, dtype=F32) + 0.5) / W * 2 - 1
    ys = 1 - (np.arange(H, dtype=F32) + 0.5) / H * 2          # row 0 = top (+1)
    zs = (np.arange(D, dtype=F32) + 0.5) / D * 2 - 1          # index D-1 = front (+1, toward camera)
    z, y, x = np.meshgrid(zs, ys, xs, indexing="ij")
    return x, y, z


def smoke_density(x, y, z, s, noise, P):
    """Looping rising smoke column.  s in [0,1) is the loop phase."""
    py = P["py"]
    th = 2 * np.pi * s
    ox = P["morph"] * np.cos(th); oz = P["morph"] * np.sin(th)
    f = P["freq"]
    # curl-like advection of the sampling point: a looping scalar potential (y-period 2 lattice
    # cells, scrolled exactly 2 cells per loop) whose 2D curl displaces x/y; z gets a plain noise shift.
    def psi(xx, yy, zz):
        return noise.fbm(xx * 0.9 + ox, yy * 0.9 - s * 2, zz * 0.9 + oz, 3, py=2)
    e = 0.02
    gx = (psi(x, y + e, z) - psi(x, y - e, z)) / (2 * e)
    gy = (psi(x + e, y, z) - psi(x - e, y, z)) / (2 * e)
    wx = gx * P["warp"]; wy = -gy * P["warp"]
    wz = noise.fbm(x * 0.8 + 21.0 + ox, y * 0.8 - s * 2, z * 0.8 + oz, 2, py=2) * P["warp"] * 0.6
    X = x + wx; Y = y + wy; Z = z + wz
    n = noise.fbm(X * f + ox + 5.1, Y * f * 0.8 - s * py, Z * f + oz + 9.4, P["oct"], py=py)
    n01 = np.clip(0.5 + 0.85 * n, 0, 1)
    # puff envelope (ellipsoid with rising/spreading profile)
    yy = Y
    rx = P["rx"] * (1.0 + 0.22 * (yy * 0.5 + 0.5))        # spreads as it rises
    r2 = (X / rx) ** 2 + ((Y - P["cy"]) / P["ry"]) ** 2 + (Z / P["rz"]) ** 2
    env = np.clip(1 - r2, 0, 1) ** 0.8
    field = env * P["gain"] + (n01 - 0.5) * P["amp"] - P["thr"]
    return np.clip(smoothstep(0.0, P["soft"], field), 0, 1) * env ** 0.35


SMOKE_P = dict(py=3, morph=0.55, freq=1.7, warp=0.20, oct=4, rx=0.62, ry=0.80, rz=0.55, cy=0.0,
               gain=1.5, amp=1.2, thr=0.46, soft=0.6)


def six_way(D, k_light=6.0, k_view=4.6, ms=(1.0, 0.5, 0.25), a=0.5, b=0.38):
    """D: density volume [z,y,x] (z=D-1 front, y row0=top).  Returns dict of
    projected maps (H,W) float: dirs R,L,T,B,K(back),F(front), alpha, thick."""
    Nz, H, W = D.shape
    dl = 2.0 / W
    def tau_from(axis, reverse):
        d = np.flip(D, axis) if reverse else D
        c = np.cumsum(d, axis=axis, dtype=F32) - d       # exclusive prefix sum
        c *= dl
        return np.flip(c, axis) if reverse else c
    def L(tau):
        acc = 0; norm = 0
        for n in range(3):
            acc = acc + (b ** n) * np.exp(-k_light * (a ** n) * tau)
            norm += b ** n
        return acc / norm
    # tau toward each light: light "from +X" travels through voxels with larger x
    taus = {
        "R": tau_from(2, True),   # +x side
        "L": tau_from(2, False),  # -x side
        "T": tau_from(1, False),  # rows above (smaller row index) = top
        "B": tau_from(1, True),
        "F": tau_from(0, True),   # front = larger z index
        "K": tau_from(0, False),  # back
    }
    tv = taus["F"] * 1.0
    wgt = D * np.exp(-k_view * tv)
    wsum = wgt.sum(0)
    eps = 1e-4
    out = {}
    for key, tau in taus.items():
        out[key] = ((wgt * L(tau)).sum(0) + eps * 0.5) / (wsum + eps)
    out["alpha"] = 1 - np.exp(-k_view * D.sum(0) * dl)
    out["thick"] = np.clip(D.sum(0) * dl / 1.2, 0, 1)
    return out


def bake_colour(m, albedo=(0.46, 0.45, 0.44)):
    """Baked 'lit from above' colour (linear) from the 6-way maps."""
    sky = np.array([0.90, 0.95, 1.05]); sun = np.array([1.25, 1.12, 0.95])
    ground = np.array([0.55, 0.45, 0.38])
    lit = (m["T"][..., None] * sky * 1.05 + m["L"][..., None] * sun * 0.40 + m["F"][..., None] * sun * 0.18
           + m["R"][..., None] * sky * 0.05 + m["B"][..., None] * ground * 0.06 + m["K"][..., None] * sky * 0.03)
    return np.clip(lit * np.array(albedo), 0, 1)


def render_smoke(n, cell, seed, W=128, D=32, P=SMOKE_P, progress=None):
    noise = Noise(seed)
    x, y, z = _grid(W, W, D)
    mapsA, mapsB, baked = [], [], []
    win = window_edges(cell, cell, 0.05)
    for i in range(n):
        dens = smoke_density(x, y, z, i / n, noise, P)
        m = six_way(dens)
        up = {k: resize(v, (cell, cell)) for k, v in m.items()}
        al = np.clip(up["alpha"] * win, 0, 1)
        # fine 2D detail wisps at the silhouette (periodic in the loop)
        mapsA.append(np.dstack([up["R"], up["L"], up["T"], al]))
        mapsB.append(np.dstack([up["B"], up["K"], up["F"], up["thick"] * win]))
        col = srgb_encode(bake_colour(up))
        col = bleed_colour(col, al)
        baked.append(np.dstack([col, al]).astype(F32))
        if progress: progress(i, n)
    return mapsA, mapsB, baked
