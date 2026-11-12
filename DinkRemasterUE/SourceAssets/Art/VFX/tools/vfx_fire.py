"""Fire family: flipbook, temperature variant, fireball core/trail, embers."""
import numpy as np
from vfxlib import *

RAMP = FireRamp()


def curl_warp(noise, u, v, s, freq, py, pz, eps=0.012, octaves=3):
    """Incompressible displacement: curl of a looping scalar potential.
    Returns (du, dv) normalised to ~unit amplitude."""
    def psi(uu, vv):
        return noise.fbm(uu * freq + 11.3, vv * freq - s * py, np.full_like(uu, s * pz) + 3.1,
                         octaves, py=py, pz=pz)
    d_dv = (psi(u, v + eps) - psi(u, v - eps)) / (2 * eps)
    d_du = (psi(u + eps, v) - psi(u - eps, v)) / (2 * eps)
    k = 1.0 / (freq * 0.55)
    return d_dv * k, -d_du * k


def flame_field(u, v, s, noise, p):
    """Core flame model on a cell grid.

    u in [-1,1] across, v in [0,1] bottom->top, s loop phase in [0,1).
    Returns dict of float fields: T (0..1 temperature), dens, soot, core.
    """
    py, pz = p["py"], p["pz"]
    du, dv = curl_warp(noise, u, v, s, p["warp_freq"], py, pz)
    vv = np.clip(v, 0, 1)
    u2 = u + du * p["warp_amp"] * (0.15 + vv ** 1.1)
    v2 = v + dv * p["warp_amp"] * 0.25 * vv
    width = p["width"] * (1.0 - p["taper"] * vv ** p["taper_pow"])
    r = np.abs(u2) / np.maximum(width, 1e-3)
    core = np.clip(1 - r * r, 0, 1) ** p["core_pow"]
    n = noise.fbm(u2 * p["fx"] + 3.7, v2 * p["fy"] - s * py, np.full_like(u, s * pz) + 1.7,
                  p["oct"], py=py, pz=pz)
    n01 = np.clip(0.5 + 0.9 * n, 0, 1)
    # fine flickering licks (anisotropic: stretched vertically)
    n2 = noise.fbm(u2 * p["fx"] * 2.6 + 8.1, v2 * p["fy"] * 1.6 - s * py * 2.0,
                   np.full_like(u, s * pz * 2) + 5.3, 3, py=py * 2, pz=pz * 2)
    n3 = noise.fbm(u2 * p["fx"] * 6.0 + 2.9, v2 * p["fy"] * 3.5 - s * py * 4.0,
                   np.full_like(u, s * pz * 4) + 7.7, 2, py=py * 4, pz=pz * 4)
    n01 = np.clip(n01 + 0.22 * n2 + 0.16 * n3 * (0.3 + vv), 0, 1)
    heat = np.exp(-p["cool"] * vv)                     # radiative cooling with height
    erosion = (1 - n01) * (p["erode0"] + p["erode1"] * vv ** p["erode_pow"])
    field = core * (0.35 + 0.65 * heat) * (0.6 + 0.8 * n01) - erosion * p["erode_gain"]
    dens = smoothstep(0.0, p["soft"], field)
    T = np.clip(field * p["t_gain"] + p["t_bias"], 0, 1.05) ** p["t_pow"] * (0.8 + 0.3 * heat)
    base = np.exp(-((vv - p["base_v"]) / p["base_w"]) ** 2) * core
    T = np.clip(T + p["base_boost"] * base * dens, 0, 1.05)
    soot = np.clip((1 - T) * smoothstep(0.35, 0.95, vv) * dens * (0.5 + 0.8 * (1 - n01)) * p["soot"], 0, 1)
    return dict(T=T, dens=dens, soot=soot, core=smoothstep(0.62, 0.95, T) * dens)


FIRE_P = dict(py=3, pz=2, warp_freq=1.3, warp_amp=0.08, width=0.44, taper=0.72, taper_pow=0.9,
              core_pow=0.6, fx=3.4, fy=0.75, oct=5, cool=1.1, erode0=0.04, erode1=1.0,
              erode_pow=1.1, erode_gain=1.0, soft=0.40, t_gain=1.15, t_bias=-0.02, t_pow=1.25,
              base_v=0.10, base_w=0.22, base_boost=0.15, soot=0.9)


def colourise(f, ramp=RAMP, desat=0.10):
    """Field dict -> straight sRGB colour (HxWx3 float)."""
    t = f["T"]
    lin = ramp.lookup_linear(np.clip(t, 0, 1))
    lin = lin * (1 - 0.55 * f["soot"][..., None])
    grey = lin.mean(-1, keepdims=True)
    amt = desat * smoothstep(0.55, 1.0, t)[..., None]
    lin = lin * (1 - amt) + (grey + 0.35) * amt
    return srgb_encode(np.clip(lin, 0, 1))


def render_flipbook(n, cell, seed, params=FIRE_P, margin=0.06, vspan=(0.03, 0.97), progress=None):
    noise = Noise(seed)
    ys, xs = np.mgrid[0:cell, 0:cell].astype(F32)
    u = (xs + 0.5) / cell * 2 - 1
    v = 1 - (ys + 0.5) / cell
    v = (v - vspan[0]) / (vspan[1] - vspan[0])
    win = window_edges(cell, cell, margin) * smoothstep(-0.02, 0.02, v)
    col, tmp = [], []
    for i in range(n):
        s = i / n
        f = flame_field(u, v, s, noise, params)
        for k in ("dens", "soot", "core"):
            f[k] = f[k] * win
        f["T"] = f["T"] * win ** 0.5
        rgb = colourise(f)
        a = f["dens"]
        rgb = bleed_colour(rgb, a)
        col.append(np.dstack([rgb, a]).astype(F32))
        tmp.append(np.dstack([f["T"], f["dens"], f["soot"], f["core"]]).astype(F32))
        if progress: progress(i, n)
    return col, tmp
