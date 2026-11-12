"""Material recipes. Each returns finish(...) of a Ctx. Units: metres, colours sRGB 0..255.

Seeds are fixed per material (see REGISTRY); a recipe consumes noise salts in a fixed
order, so output is bit-for-bit reproducible.
"""
import numpy as np
from sm_lib import *


# ------------------------------------------------------------------ utils ---
def pal_ramp(pal):
    """[(weight,(r,g,b)),...] -> hard-stepped ramp stops over 0..1."""
    tot = sum(w for w, _ in pal)
    stops, acc = [], 0.0
    for w, col in pal:
        stops.append((acc + 1e-4, col))
        acc += w / tot
        stops.append((acc - 1e-4, col))
    stops[0] = (0.0, stops[0][1])
    stops[-1] = (1.0, stops[-1][1])
    return stops


def top_layer(layers):
    z = None
    for k, (d, zo) in enumerate(layers):
        zz = np.where(d["hit"], d["z"] + zo, -1e9).astype(F32)
        if z is None:
            z = np.full(zz.shape, -1e9, F32)
            which = np.full(zz.shape, -1, np.int32)
        b = zz > z
        z = np.where(b, zz, z)
        which = np.where(b, k, which)
    return which, z


def line_noise_x(c, lmax, lmin, salt=None):
    """1-D periodic noise along x, broadcast over y."""
    return fbm(c, lmax, lmin, 1.0, salt=salt)[0:1, :]


def mul(rgb, f):
    return rgb * np.asarray(f, F32)[..., None]


def speck(c, size_lo=0.002, size_hi=0.012):
    return fbm(c, size_hi, size_lo, a=0.6)


# ----------------------------------------------------------------- paving ---
def paving(c, g, stagger, jitter, edge_w, top_h, top_var, tilt, dome, warp_m, pal, joint_cols,
           rough_base, joint_depth_note=None, wear=0.12, mott=0.08, aspect=(1.0, 1.0)):
    T = c.T
    cell = T / g
    wx = fbm(c, 0.9, 0.25, a=1.2) * warp_m
    wy = fbm(c, 0.9, 0.25, a=1.2) * warp_m
    u = (c.X * T + wx) / cell
    v = (c.Y * T + wy) / cell
    ox, oy = cell_offsets(c, g, jitter, 21, stagger)
    F1, F2, idx, dx, dy = voronoi(u, v, g, ox, oy)
    edge = F2 - F1
    cnt = g * g
    s = smoothstep(edge_w * 0.12, edge_w, edge)
    s_h = s ** 0.6
    top = by_id(c, idx, cnt, 31, top_h - top_var, top_h + top_var)
    tx = by_id(c, idx, cnt, 32, -tilt, tilt)
    ty = by_id(c, idx, cnt, 33, -tilt, tilt)
    surf = fbm(c, 0.5, 0.06, a=1.3) * 0.0016 + fbm(c, 0.06, 0.004, a=1.2) * 0.0010 + fbm(c, 0.01, 0.002, a=0.8) * 0.0003
    h = s_h * (top + (tx * dx + ty * dy) * cell - dome * (F1 / 0.6) ** 2 + surf)
    # joint fill: soil with a little unevenness
    jfill = fbm(c, 0.2, 0.01, a=1.2)
    h += (1 - s_h) * (jfill * 0.003)
    # colour
    sel = by_id(c, idx, cnt, 34, 0, 1)
    base = ramp(sel, pal_ramp(pal))
    bright = by_id(c, idx, cnt, 35, 0.84, 1.14)
    m1 = fbm(c, 0.18, 0.025, a=1.2)
    m2 = speck(c, 0.002, 0.007)
    veins = ridged(c, 0.3, 0.03, a=1.0, power=3.0)
    stone = mul(base, bright * (1 + mott * m1 + mott * 0.7 * m2 + 0.10 * veins))
    # dust on rounded shoulders + dark pits
    shoulder = (1 - smoothstep(edge_w * 0.3, edge_w * 1.6, edge)) * s
    stone = mul(stone, 1 + wear * shoulder)
    pits = norm01(surf)
    stone = mul(stone, 0.80 + 0.30 * pits)
    jn = norm01(jfill + 0.5 * fbm(c, 0.05, 0.004))
    joint = ramp(jn, [(0, joint_cols[0]), (0.6, joint_cols[1]), (1, joint_cols[2])])
    alb = mix(joint, stone, smoothstep(0.1, 0.5, s))
    # darken the stone right at the joint (shadowed grime)
    alb = mul(alb, 0.78 + 0.22 * smoothstep(edge_w * 0.1, edge_w * 1.1, edge))
    rough = (rough_base + 0.14 * m1 * 0.5 - 0.12 * (1 - np.clip(F1 / 0.6, 0, 1)) * (0.5 + 0.5 * bright - 0.5)).astype(F32)
    rough = mix(rough[..., None], np.full_like(rough, 0.95)[..., None], 1 - s)[..., 0]
    return alb, h, rough, F1, edge, idx


def cobble(c):
    pal = [(4, (116, 114, 110)), (3, (128, 118, 104)), (3, (102, 104, 106)), (2, (110, 100, 90)), (1, (126, 112, 104)),
           (2, (88, 88, 88))]
    alb, h, rough, *_ = paving(c, 12, 1.0, 0.50, 0.26, 0.040, 0.007, 0.05, 0.016, 0.010, pal,
                               [(52, 44, 36), (88, 76, 60), (122, 108, 88)], 0.70, wear=0.14, mott=0.10)
    # grass / moss threading the joints
    g = np.clip(fbm(c, 0.35, 0.05, a=1.0) * 0.5 + 0.1, 0, 1)
    jointness = 1 - smoothstep(0.003, 0.012, h)
    alb = mix(alb, np.broadcast_to(np.array([58, 70, 36], F32), alb.shape), jointness * g * 0.5)
    return finish(c, alb, h, rough, normal_gain=1.0)


def bedded_blocks(c, n_beds, hlo, hhi, wlo, whi, skew_max, warp_m, salt):
    """Rock beds of random thickness, each cut by oblique joints into blocks (periodic)."""
    T = c.T
    r = c.rng(salt)
    hts = r.uniform(hlo, hhi, n_beds)
    hts = hts * (T / hts.sum())
    skew = r.uniform(-skew_max, skew_max, n_beds)
    cum = np.concatenate([[0], np.cumsum(hts)])
    wy = fbm(c, 3.0, 0.7, a=1.3) * warp_m + fbm(c, 0.5, 0.15, a=1.3) * warp_m * 0.15
    wx0 = fbm(c, 1.2, 0.25, a=1.3) * warp_m * 0.3
    yy = np.mod(c.Y * T + wy, T)
    row = np.clip(np.searchsorted(cum, yy, side="right") - 1, 0, n_beds - 1)
    v = (yy - cum[row]) / hts[row]
    wx = wx0 + skew[row] * (v - 0.5) * hts[row]
    wf = random_widths(wlo, whi, T)
    R = ragged_rows(c, hts, lambda ri, rr: (wf(ri, rr), rr.uniform(0, T)), wx, wy, salt=salt + 1)
    return R, hts


def dungeon_flags(c):
    T = c.T
    hts = [0.50, 0.42, 0.58, 0.50]
    wf = random_widths(0.45, 0.85, T)

    def widths(ri, r):
        return (wf(ri, r), r.uniform(0, T))
    pal = [(3, (100, 98, 94)), (2, (88, 90, 92)), (2, (110, 102, 92)), (1, (76, 78, 80))]
    alb, h, rough, damp, face = _ashlar(c, hts, widths, 120, 0.016, 0.012, 0.022, 0.006, pal, 0.012, 0.0045,
                                        [(40, 38, 32), (62, 58, 48), (86, 80, 68)], 0.10, 0.2, 0.66)
    # mineral texture: bedding laminae, quartz and mica flecks, dark grains, iron blooms
    lam = fbm(c, 0.6, 0.004, a=0.8, aniso=(14.0, 1.0))
    lam2 = fbm(c, 0.6, 0.004, a=0.8, aniso=(1.0, 14.0))
    L = lam
    alb = mul(alb, 1 + 0.045 * L)
    h = h + L * 0.0004 * (face > 0.5)
    q, mi, dk = mineral_flecks(c, 2.2)
    alb = mix(alb, np.array([204, 200, 190], F32) * np.ones_like(alb), (q * face)[..., None] * 0.65)
    alb = mix(alb, np.array([172, 176, 184], F32) * np.ones_like(alb), (mi * face)[..., None] * 0.6)
    alb = mix(alb, np.array([34, 32, 30], F32) * np.ones_like(alb), (dk * face)[..., None] * 0.45)
    bloom = smoothstep(0.7, 0.92, norm01(fbm(c, 0.3, 0.03)))
    alb = mix(alb, alb * np.array([1.15, 0.92, 0.74], F32), bloom[..., None] * 0.4)
    # chipped edges: lighter fresh stone, stepped
    jointness = 1 - smoothstep(0.002, 0.010, h)
    chipn = smoothstep(0.55, 0.82, norm01(fbm(c, 0.08, 0.01)))
    nearj = gblur(jointness, 0.025 / c.px)
    chip = chipn * np.clip(nearj * 1.6, 0, 1) * face
    h -= chip * 0.004
    alb = mix(alb, alb * 1.22, chip[..., None] * 0.7)
    # wear on the walking paths: polished, lighter, dished; grimy and dusty elsewhere
    meander = line_noise_x(c, 2.0, 0.6) * 0.05
    path1 = np.exp(-(((c.Y - 0.5 - meander) / 0.15) ** 2))
    path2 = np.exp(-(((c.X - 0.18 - 0.05 * fbm(c, 2.0, 0.6)[:, 0:1]) / 0.10) ** 2))
    wear = np.clip(path1 + 0.8 * path2, 0, 1) * smoothstep(0.2, 0.7, 0.5 + 0.35 * fbm(c, 0.4, 0.08) + 0.3)
    wear = np.clip(wear, 0, 1)
    h -= wear * (0.0035 + 0.003 * (1 - face * 0)) * face
    h = h + wear * (-0.0015) * (1 - face)
    alb = mix(alb, alb * 1.30 + 8, wear[..., None] * 0.90)
    alb = mul(alb, 1 - 0.30 * (1 - wear) * smoothstep(0.55, 0.9, norm01(fbm(c, 0.4, 0.05))))
    mg = norm01(fbm(c, 0.4, 0.05))
    jointness = 1 - smoothstep(0.002, 0.010, h + wear * 0.003)
    alb = mix(alb, np.array([40, 56, 30], F32) * np.ones_like(alb), (jointness * smoothstep(0.55, 0.9, mg) * 0.7 * (1 - wear))[..., None])
    rough = rough * (1 - 0.45 * wear) - 0.10 * mi
    return finish(c, alb, h, rough)


# -------------------------------------------------------------- dirt road ---
def dirt_road(c):
    T = c.T
    Y = c.Y * T
    mean = line_noise_x(c, 1.8, 0.5) * 0.045 + line_noise_x(c, 0.4, 0.12) * 0.006
    depth = 0.065 + 0.018 * line_noise_x(c, 1.2, 0.3)
    w = 0.11
    ruts = np.zeros_like(c.X)
    ridge = np.zeros_like(c.X)
    rutw = np.zeros_like(c.X)
    for yc in (0.55 * T - 0.6, 0.55 * T + 0.6):
        d = np.abs(Y - yc - mean)
        prof = 1.0 / (1.0 + (d / w) ** 3)
        ruts += prof * depth
        ridge += 0.022 * np.exp(-(((d - 1.8 * w) / (0.8 * w)) ** 2))
        rutw += prof
    rutw = np.clip(rutw, 0, 1)
    base = (fbm(c, 1.5, 0.35, a=1.3) * 0.010 + fbm(c, 0.35, 0.08, a=1.3) * 0.0035
            + fbm(c, 0.06, 0.012, a=1.1) * 0.0014 + fbm(c, 0.012, 0.0025, a=0.6) * 0.00035)
    # puddle-dried hollows and clods in the horse path between the ruts
    clod = splat(c, 24, 46, (0.18, 0.40), (0.6, 1.0), kind="ellipse", zrange=1.0)
    clod["hit"] = clod["hit"] & (clod["rid"] < 0.45)
    h = base - ruts + ridge + np.where(clod["hit"], np.sqrt(np.clip(clod["edge"], 0, 1)) * 0.008, 0)
    # embedded stones
    g = 44
    cell = T / g
    ox, oy = cell_offsets(c, g, 0.9, 41)
    F1, F2, idx, dx, dy = voronoi(c.X * g, c.Y * g, g, ox, oy)
    has = by_id(c, idx, g * g, 42, 0, 1) < 0.22
    rad = by_id(c, idx, g * g, 43, 0.14, 0.40)
    dome = np.sqrt(np.clip((rad * cell) ** 2 - (F1 * cell) ** 2, 0, None)) * 0.75
    stone = has & (F1 < rad)
    h = h + np.where(stone, dome - 0.003, 0).astype(F32)
    t = norm01(base * 1.0 + 0.5 * fbm(c, 0.2, 0.03) * 0.004)
    soil = ramp(t, [(0, (70, 54, 40)), (0.5, (104, 82, 60)), (1, (138, 114, 88))])
    dust = smoothstep(0.55, 0.95, norm01(ridge * 6 + base * 30))
    soil = mix(soil, np.broadcast_to(np.array([150, 130, 104], F32), soil.shape), dust * 0.30)
    soil = mix(soil, soil * np.array([0.74, 0.72, 0.72], F32), rutw * 0.85)
    soil = mul(soil, 1 + 0.10 * fbm(c, 0.05, 0.006, a=0.9) + 0.05 * speck(c))
    clc = ramp(norm01(fbm(c, 0.1, 0.01)), [(0, (74, 58, 44)), (1, (112, 90, 66))])
    soil = mix(soil, clc, clod["hit"].astype(F32) * 0.5 * smoothstep(0, 0.4, clod["edge"]))
    pcol = ramp(by_id(c, idx, g * g, 44, 0, 1), pal_ramp([(3, (122, 116, 106)), (2, (140, 124, 100)), (2, (92, 88, 86)), (1, (154, 146, 134))]))
    alb = mix(soil, pcol, np.where(stone, 1, 0).astype(F32) * smoothstep(0, 0.08, rad - F1))
    alb = mul(alb, np.where(stone, 0.8 + 0.3 * smoothstep(0, 0.5, rad - F1), 1.0))
    nd = splat(c, 56, 45, (0.8, 1.05), (0.04, 0.08), kind="needle", zrange=1.0)
    verge = smoothstep(0.35, 0.7, norm01(fbm(c, 0.8, 0.2)) - 0.55 * rutw)
    sm = (nd["hit"] & (nd["rid"] < 0.30 * verge * 3)).astype(F32)
    straw = ramp(nd["rid"] * 3.0 % 1.0, [(0, (140, 120, 78)), (0.5, (112, 94, 60)), (1, (88, 78, 50))])
    alb = mix(alb, straw, sm * 0.85)
    h = h + sm * 0.0012
    rough = 0.90 - 0.08 * rutw + 0.04 * fbm(c, 0.2, 0.03)
    rough = np.where(stone, 0.78, rough)
    return finish(c, alb, h, rough, normal_gain=1.0)


# ------------------------------------------------------------ forest floor ---
def forest_floor(c):
    T = c.T
    hum = norm01(fbm(c, 0.5, 0.02, a=1.1))
    col = ramp(hum, [(0, (32, 25, 18)), (0.5, (50, 39, 28)), (1, (74, 58, 42))])
    h = fbm(c, 0.5, 0.05, a=1.2) * 0.010 + fbm(c, 0.05, 0.004, a=1.0) * 0.0015
    col = mul(col, 1 + 0.08 * speck(c))
    # moss patches
    mpatch = smoothstep(0.62, 0.85, norm01(fbm(c, 0.6, 0.08)))
    mcol = ramp(norm01(fbm(c, 0.05, 0.004, a=0.8)), [(0, (40, 62, 28)), (0.6, (66, 92, 38)), (1, (104, 128, 60))])
    col = mix(col, mcol, mpatch * 0.85)
    h += mpatch * fbm(c, 0.04, 0.004, a=0.9) * 0.0018
    rough = 0.92 - 0.04 * mpatch + 0.04 * speck(c)

    leaf_pal = pal_ramp([(4, (96, 66, 38)), (3, (124, 92, 50)), (3, (104, 58, 36)), (1, (84, 80, 44)), (5, (52, 38, 28)),
                         (2, (118, 100, 74)), (1, (66, 80, 40))])
    L1 = splat(c, 34, 61, (0.45, 0.80), (0.45, 0.70), kind="leaf", zrange=1.0)
    L2 = splat(c, 26, 62, (0.40, 0.70), (0.40, 0.62), kind="leaf", zrange=1.0)
    nd = splat(c, 66, 63, (0.85, 1.05), (0.035, 0.06), kind="needle", zrange=1.0)
    ndmask = smoothstep(0.45, 0.62, norm01(fbm(c, 0.7, 0.15))) * 0.7 + 0.15
    nd["hit"] = nd["hit"] & (nd["rid"] < ndmask)
    tw = splat(c, 6, 64, (0.25, 0.40), (0.035, 0.055), kind="ellipse", zrange=1.0)
    tw["hit"] = tw["hit"] & (tw["rid"] < 0.30)
    L1["hit"] = L1["hit"] & (L1["rid"] < 0.80)
    L2["hit"] = L2["hit"] & (L2["rid"] < 0.70)
    which, z = top_layer([(L1, 0.0), (L2, 0.45), (nd, 0.55), (tw, 0.50)])
    zh = np.where(which >= 0, z, 0).astype(F32)
    for k, (L, sc, th) in enumerate([(L1, 0.012, 0), (L2, 0.012, 0), (nd, 0.012, 0), (tw, 0.012, 0)]):
        pass
    h = h + zh * 0.012
    for k, L in enumerate((L1, L2)):
        m = (which == k).astype(F32)
        lc = ramp(L["rid"], leaf_pal)
        rib = 1 - smoothstep(0.0, 0.12, np.abs(L["ly"]))
        veins = 0.5 + 0.5 * np.cos(np.clip(L["lx"], -1, 1) * 14 + np.abs(L["ly"]) * 6)
        lc = mul(lc, 0.80 + 0.30 * norm01(fbm(c, 0.04, 0.004)) + 0.12 * rib * 0.5 + 0.06 * veins * (1 - rib))
        lc = mul(lc, 0.75 + 0.35 * smoothstep(0.0, 0.35, L["edge"]))  # edges darker/curled
        col = mix(col, lc, m)
        h += m * (rib * -0.0012 + 0.0008 * veins)
        rough = np.where(which == k, 0.70 + 0.12 * L["rid"], rough)
    m = (which == 2).astype(F32)
    nc = ramp(nd["rid"] * 1.6 % 1.0, [(0, (128, 84, 48)), (0.4, (108, 72, 42)), (0.7, (138, 108, 72)), (1, (74, 52, 36))])
    col = mix(col, mul(nc, 0.8 + 0.3 * smoothstep(0, 0.7, nd["edge"])), m)
    rough = np.where(which == 2, 0.6, rough)
    m = (which == 3).astype(F32)
    tcol = ramp(norm01(fbm(c, 0.05, 0.003)), [(0, (60, 48, 40)), (1, (112, 98, 84))])
    col = mix(col, tcol, m)
    h += m * (0.004 * fbm(c, 0.03, 0.002) * 0.5)
    rough = np.where(which == 3, 0.88, rough)
    return finish(c, col, h, rough, normal_gain=1.0)


# --------------------------------------------------------------- wet sand ---
def wet_sand(c):
    T = c.T
    # two ripple trains (wave ripples, sharp-crested) blended by a low-frequency mask
    def train(i, j, lam_amp, sal):
        ph = i * c.X + j * c.Y + 0.30 * fbm(c, 1.6, 0.4, a=1.2) + 0.05 * fbm(c, 0.3, 0.06)
        fr = ph - np.floor(ph)
        saw = np.abs(2 * fr - 1)                                   # 0 at crest, 1 in trough
        return (1 - saw ** 1.6) * 2 - 1                            # sharp crest, rounded trough
    A = train(2, 14, 1, 1)
    B = train(-3, 10, 1, 2)
    mAB = smoothstep(-0.4, 0.4, fbm(c, 1.5, 0.5, a=1.2))
    amp = 0.25 + 0.75 * smoothstep(0.1, 0.7, norm01(fbm(c, 1.4, 0.4)))
    rip = (A * (1 - mAB) + B * mAB) * amp
    macro = fbm(c, 1.5, 0.3, a=1.3) * 0.0035 + fbm(c, 0.3, 0.05, a=1.2) * 0.0015
    grain = fbm(c, 0.006, 0.0018, a=0.2)
    hbase = 0.0085 * rip + macro + fbm(c, 0.03, 0.005, a=1.0) * 0.0006
    # drainage rills across the ripples
    rill = (1 - smoothstep(0.0, 0.08, np.abs(fbm(c, 1.0, 0.1, a=1.3, aniso=(1.0, 3.0))))) * smoothstep(0.0, 0.7, fbm(c, 1.0, 0.2))
    hbase -= rill * 0.0025
    # worm casts and bubble holes
    pits = splat(c, 38, 71, (0.06, 0.16), (0.9, 1.0), kind="ellipse", zrange=0.0)
    pits["hit"] = pits["hit"] & (pits["rid"] < 0.10)
    hbase -= np.where(pits["hit"], np.sqrt(np.clip(pits["edge"], 0, 1)) * 0.0025, 0)
    # wet/dry decided by height: crests and high swells drain and dry out, troughs hold water
    hs = gblur(hbase, 0.01 / c.px)
    hn = norm01(hs + 0.002 * fbm(c, 0.4, 0.05))
    dry = smoothstep(0.60, 0.76, hn + 0.06 * fbm(c, 1.0, 0.2))
    damp = smoothstep(0.38, 0.62, hn)
    wet = 1 - dry
    h = hbase + grain * 0.00015 + dry * 0.0004
    dry_c = ramp(norm01(fbm(c, 0.4, 0.03)), [(0, (162, 140, 108)), (1, (192, 170, 134))])
    wet_c = ramp(norm01(fbm(c, 0.5, 0.04)), [(0, (92, 76, 58)), (1, (122, 102, 78))])
    alb = mix(dry_c, wet_c, wet)
    alb = mix(alb, alb * np.array([0.90, 0.89, 0.88], F32), damp[..., None] * 0.35 * dry[..., None])   # damp fringe
    alb = mul(alb, 1 + 0.12 * grain + 0.06 * fbm(c, 0.02, 0.004))
    trough = smoothstep(0.0, 0.5, 1 - hn)
    alb = mix(alb, alb * np.array([0.76, 0.74, 0.74], F32), (trough * 0.5)[..., None])  # heavy-mineral laminae
    alb = mix(alb, alb * np.array([0.8, 0.78, 0.76], F32), (rill * 0.5)[..., None])
    # shells: whole bivalves with ribs, scallop fans and many fragments, each sitting in a little sand pile
    shc_pal = [(0, (218, 206, 190)), (0.25, (196, 160, 146)), (0.5, (172, 150, 120)), (0.7, (70, 66, 78)), (1, (232, 224, 210))]
    layers = [(splat(c, 16, 72, (0.16, 0.28), (0.6, 0.85), kind="ellipse", zrange=1.0), 0.14, 0.0030),
              (splat(c, 46, 73, (0.14, 0.42), (0.3, 0.7), kind="angular", zrange=1.0), 0.16, 0.0012)]
    for L, dens, th in layers:
        L["hit"] = L["hit"] & (L["rid"] < dens)
    which, z = top_layer([(L, 0.0) for L, _, _ in layers])
    for k, (L, dens, th) in enumerate(layers):
        m = (which == k)
        rr_ = np.hypot(L["lx"], L["ly"])
        rib = 0.5 + 0.5 * np.cos(rr_ * (13 if k == 0 else 5) + 3 * np.arctan2(L["ly"], L["lx"]) * (k == 0) * 0)
        shc = ramp(L["rid"] / dens, shc_pal)
        shc = mul(shc, 0.80 + 0.25 * rib)
        pile = gblur(m.astype(F32), 0.012 / c.px)
        alb = mul(alb, 1 - 0.35 * np.clip(pile - m, 0, 1) * 1.0)
        alb = mix(alb, shc, m.astype(F32) * 0.96)
        h += np.where(m, th * (0.6 + 0.4 * L["edge"]) + 0.0006 * rib, 0) + np.clip(pile - m, 0, 1) * 0.0012
    shell = (which >= 0).astype(F32)
    rough = 0.90 - 0.64 * wet + 0.08 * fbm(c, 0.2, 0.02) * wet + 0.12 * damp * dry
    rough = np.where(shell > 0.5, 0.42, rough)
    return finish(c, alb, h, rough, normal_gain=1.0, h_soften_px=0.9)


# ---------------------------------------------------------- beach pebbles ---
def beach_pebbles(c):
    T = c.T
    pal = pal_ramp([(3, (122, 120, 116)), (2, (150, 145, 136)), (2, (138, 122, 100)), (2, (104, 94, 84)), (2, (88, 92, 98)),
                    (1, (124, 98, 80)), (1, (182, 178, 168)), (2, (64, 62, 64))])
    layers = []
    for g, salt, zoff, hmul, jit in ((15, 81, 0.012, 0.50, 0.9), (34, 82, 0.0, 0.50, 0.9)):
        cell = T / g
        wx = fbm(c, 0.5, 0.06, a=1.2) * 0.006
        wy = fbm(c, 0.5, 0.06, a=1.2) * 0.006
        u = (c.X * T + wx) / cell
        v = (c.Y * T + wy) / cell
        ox, oy = cell_offsets(c, g, jit, salt)
        F1, F2, idx, dx, dy = voronoi(u, v, g, ox, oy)
        cnt = g * g
        R = by_id(c, idx, cnt, salt + 10, 0.55, 0.78)
        hh = by_id(c, idx, cnt, salt + 11, 0.40, 0.70) * cell * 0.9
        q = np.clip(F1 / R, 0, 1)
        dome = np.sqrt(np.clip(1 - q * q, 0, 1)) * hh
        edge = F2 - F1
        ang = by_id(c, idx, cnt, salt + 12, 0, np.pi)
        cl = np.cos(ang); sl = np.sin(ang)
        # elongate: squash along a per-pebble axis for oval pebbles
        ratio = by_id(c, idx, cnt, salt + 13, 0.0, 0.35)
        pa = (dx * cl + dy * sl)
        pb = (-dx * sl + dy * cl)
        qa = np.sqrt((pa / (1 + ratio)) ** 2 + (pb * (1 + ratio)) ** 2) / R
        dome = np.sqrt(np.clip(1 - np.clip(qa, 0, 1) ** 2, 0, 1)) * hh
        inside = (qa < 1.0)
        layers.append(dict(hit=inside, z=dome + zoff * inside, dome=dome, edge=edge, idx=idx, cnt=cnt, pa=pa, pb=pb, cell=cell,
                           F1=F1, salt=salt, q=qa))
    bed = fbm(c, 0.3, 0.02, a=1.2) * 0.003
    z0, z1 = layers[0]["z"], layers[1]["z"]
    use0 = layers[0]["hit"] & ((z0 >= z1) | ~layers[1]["hit"])
    use1 = layers[1]["hit"] & ~use0
    h = np.where(use0, z0, np.where(use1, z1, bed))
    # bed (sand/gravel) colour, wet and dark
    bedc = ramp(norm01(fbm(c, 0.2, 0.01)), [(0, (70, 58, 46)), (1, (116, 100, 80))])
    alb = bedc * 1.0
    rough = np.full_like(h, 0.7)
    m1 = fbm(c, 0.1, 0.012, a=1.2)
    for L, use in ((layers[1], use1), (layers[0], use0)):
        sel = by_id(c, L["idx"], L["cnt"], L["salt"] + 20, 0, 1)
        pc = ramp(sel, pal)
        pc = mul(pc, by_id(c, L["idx"], L["cnt"], L["salt"] + 21, 0.85, 1.12))
        # quartz veins
        angv = by_id(c, L["idx"], L["cnt"], L["salt"] + 22, 0, np.pi)
        phv = by_id(c, L["idx"], L["cnt"], L["salt"] + 23, 0, 6.28)
        fv = by_id(c, L["idx"], L["cnt"], L["salt"] + 24, 20, 60)
        hasv = by_id(c, L["idx"], L["cnt"], L["salt"] + 25, 0, 1) < 0.28
        d = (L["pa"] * np.cos(angv) + L["pb"] * np.sin(angv)) * fv / 4 + phv + 0.25 * fbm(c, 0.06, 0.01)
        band = smoothstep(0.82, 0.94, 0.5 + 0.5 * np.sin(d))
        pc = mix(pc, np.broadcast_to(np.array([208, 202, 190], F32), pc.shape), band * hasv * 0.9)
        pc = mul(pc, 1 + 0.09 * m1 + 0.07 * speck(c, 0.0015, 0.006))
        # wet sheen darkening + crevice dirt
        pc = mul(pc, 0.86 + 0.14 * smoothstep(0.0, 0.25, L["edge"]))
        alb = np.where(use[..., None], pc, alb)
        rough = np.where(use, 0.42 + 0.22 * norm01(m1) + 0.2 * (1 - smoothstep(0, 0.3, L["edge"])), rough)
        h = h + np.where(use, fbm(c, 0.02, 0.002, a=1.0) * 0.0003 + 0.0006 * m1, 0)
    return finish(c, alb, h, rough, normal_gain=1.0, h_soften_px=0.8)


# ----------------------------------------------------------- mossy cave rock ---
def cave_rock(c):
    T = c.T
    nb = 10
    R, hts = bedded_blocks(c, nb, 0.12, 0.70, 0.4, 2.0, 0.7, 0.05, 90)
    ns = R["nseg"]
    rs = lambda sl, lo, hi: c.rng(100 + sl).random(ns).astype(F32)[R["sid"]] * (hi - lo) + lo
    du = np.minimum(R["u"] * R["w"], (1 - R["u"]) * R["w"])
    dv = np.minimum(R["v"] * R["h"], (1 - R["v"]) * R["h"])
    dmin = np.minimum(du, dv)
    openj = smoothstep(-0.6, 0.5, fbm(c, 1.2, 0.3, salt=107))
    gap = (0.003 + 0.014 * norm01(fbm(c, 1.0, 0.2))) * (0.2 + 0.8 * openj)
    face = smoothstep(gap * 0.5, gap * 0.5 + 0.005, dmin)
    # dissolution rounds the blocks heavily; crevices stay sharp and deep
    round_ = 1 - np.exp(-np.clip(dmin - gap * 0.5, 0, None) / 0.07)
    top = rs(1, -0.05, 0.05) + (R["u"] - 0.5) * R["w"] * rs(2, -0.16, 0.16) + (R["v"] - 0.5) * R["h"] * rs(3, -0.10, 0.10)
    scallop = ridged(c, 0.5, 0.08, a=1.2, power=2.0)
    h = (top - 0.08 * (1 - round_) + fbm(c, 1.5, 0.3, a=1.3) * 0.025 + fbm(c, 0.3, 0.06, a=1.3) * 0.010 - 0.012 * scallop
         + fbm(c, 0.06, 0.008, a=1.2) * 0.0025 + fbm(c, 0.01, 0.0015, a=0.8) * 0.0005)
    h = h * face + (-0.03 - 0.10 * openj) * (1 - face)
    cr_all = np.zeros_like(h)
    for (i, j, sal) in ((2, 3, 111), (3, -2, 112)):
        d = joint_dist(c, i, j, fbm(c, 1.5, 0.4) * 0.03)
        pres = smoothstep(-0.1, 0.6, fbm(c, 1.2, 0.3, salt=sal))
        w = 0.006 + 0.012 * norm01(fbm(c, 0.6, 0.1))
        cr = (1 - smoothstep(w * 0.5, w * 0.5 + 0.005, d)) * pres
        cr_all = np.maximum(cr_all, cr)
    h -= cr_all * 0.05
    # pitted, wet limestone
    pit = splat(c, 24, 94, (0.2, 0.5), (0.7, 1.0), kind="ellipse", zrange=0.0)
    pit["hit"] = pit["hit"] & (pit["rid"] < 0.25)
    h -= np.where(pit["hit"], np.sqrt(np.clip(pit["edge"], 0, 1)) * 0.006, 0)
    h = gblur(h, 0.9)
    hs = gblur(h, 4.0 * 1024 / c.n * c.n / 1024)
    gx = (np.roll(hs, -1, 1) - np.roll(hs, 1, 1)) / (2 * c.px)
    gy = (np.roll(hs, -1, 0) - np.roll(hs, 1, 0)) / (2 * c.px)
    upness = 1 / np.sqrt(1 + gx * gx + gy * gy)
    cav = np.clip((gblur(h, 0.05 / c.px) - h) / 0.03, 0, 1)
    cav2 = np.clip((gblur(h, 0.15 / c.px) - h) / 0.08, 0, 1)
    score = 0.50 * norm01(0.6 * cav + 0.4 * cav2) + 0.30 * norm01(upness) + 0.20 * norm01(fbm(c, 1.0, 0.15, a=1.1))
    moss = np.clip(smoothstep(0.42, 0.62, score), 0, 1)
    moss = moss * (0.55 + 0.45 * smoothstep(0.2, 0.7, norm01(fbm(c, 0.12, 0.015))))
    rt = norm01(fbm(c, 0.7, 0.06, a=1.1))
    bedcol = np.array([(112, 108, 100), (96, 92, 86), (126, 118, 104), (84, 82, 80), (118, 106, 90), (100, 98, 94), (90, 86, 78)], F32)
    pick = np.concatenate([c.rng(88).permutation(7), c.rng(89).permutation(7)])[:nb]
    rock = bedcol[pick][R["row"]] * rs(4, 0.74, 0.96)[..., None]
    rock = mul(rock, 0.88 + 0.24 * rt)
    stain = smoothstep(0.55, 0.85, norm01(fbm(c, 0.6, 0.06) + 0.7 * fbm(c, 0.15, 0.02)))
    rock = mix(rock, np.broadcast_to(np.array([122, 92, 60], F32), rock.shape), stain * 0.30)
    vein = (1 - smoothstep(0.003, 0.007, joint_dist(c, 4, 1, fbm(c, 1.0, 0.3) * 0.02))) * smoothstep(0.0, 0.6, fbm(c, 1.0, 0.2, salt=113))
    rock = mix(rock, np.broadcast_to(np.array([190, 186, 174], F32), rock.shape), vein * 0.8)
    q, mi, dk = mineral_flecks(c, 0.7)
    rock = mix(rock, np.array([196, 192, 182], F32) * np.ones_like(rock), q[..., None] * 0.5)
    rock = mul(rock, 1 + 0.06 * speck(c, 0.003, 0.012) + 0.08 * fbm(c, 0.1, 0.012))
    rock = mul(rock, 0.45 + 0.55 * (1 - cav2 * 0.8))
    rock = mix(rock, np.array([30, 28, 26], F32) * np.ones_like(rock), np.clip((1 - face) + cr_all * 0.8, 0, 1)[..., None] * 0.85)
    mm = norm01(fbm(c, 0.12, 0.02, a=0.9))
    mcol = ramp(mm, [(0, (38, 56, 28)), (0.5, (58, 80, 36)), (1, (92, 114, 52))])
    mcol = mul(mcol, 0.78 + 0.25 * (1 - cav))
    alb = mix(rock, mcol, moss)
    h = h + moss * (0.004 + 0.0015 * fbm(c, 0.08, 0.015, a=0.9))
    wet = 0.5 + 0.3 * smoothstep(0.3, 0.7, norm01(fbm(c, 0.8, 0.2)))
    rock_r = 0.85 - 0.32 * wet + 0.05 * fbm(c, 0.05, 0.005)
    rough = mix(rock_r[..., None], np.full(h.shape + (1,), 0.93, F32), moss[..., None])[..., 0]
    return finish(c, alb, h, rough, normal_gain=0.9, ao_strength=1.1)


# -------------------------------------------------------- dungeon masonry ---
def _ashlar(c, hts, widths, salt, joint, depth, bevel, warp_m, pal, tilt, dish, mort_cols, streak_amt, damp_amt, rough0):
    T = c.T
    wx = fbm(c, 0.5, 0.12, a=1.3) * warp_m
    wy = fbm(c, 0.5, 0.12, a=1.3) * warp_m
    R = ragged_rows(c, hts, widths, wx, wy, salt=salt)
    ns = R["nseg"]
    rs = lambda sl, lo, hi: c.rng(salt + sl).random(ns).astype(F32)[R["sid"]] * (hi - lo) + lo
    dmin = np.minimum(np.minimum(R["u"] * R["w"], (1 - R["u"]) * R["w"]), np.minimum(R["v"] * R["h"], (1 - R["v"]) * R["h"]))
    face = smoothstep(joint * 0.5, joint * 0.5 + 0.003, dmin)
    bev = smoothstep(joint * 0.5, joint * 0.5 + bevel, dmin)
    off = rs(1, -depth * 0.35, depth * 0.35)
    tx = rs(2, -tilt, tilt)
    ty = rs(3, -tilt, tilt)
    surf = (fbm(c, 0.5, 0.05, a=1.4) * 0.0035 + fbm(c, 0.05, 0.005, a=1.2) * 0.0013 + fbm(c, 0.012, 0.0015, a=0.8) * 0.00035)
    chip = smoothstep(0.58, 0.88, norm01(fbm(c, 0.07, 0.01))) * (1 - smoothstep(0.0, 0.05, dmin)) * 0.008
    du = (R["u"] - 0.5) * 2
    dv = (R["v"] - 0.5) * 2
    h = face * (depth + off + du * R["w"] * 0.5 * tx + dv * R["h"] * 0.5 * ty + 0.5 * depth * bev + surf - chip
                - dish * (du * du + dv * dv))
    mort = fbm(c, 0.1, 0.004, a=0.9)
    h += (1 - face) * (mort * 0.0015)
    base = ramp(rs(4, 0, 1), pal_ramp(pal))
    base = mul(base, rs(5, 0.84, 1.14))
    m1 = fbm(c, 0.3, 0.04, a=1.2)
    stone = mul(base, 1 + 0.09 * m1 + 0.07 * speck(c, 0.002, 0.01) + 0.05 * fbm(c, 0.03, 0.003))
    streak = norm01(fbm(c, 1.2, 0.05, aniso=(1.0, 5.0)))
    stone = mul(stone, 1 - streak_amt * smoothstep(0.55, 0.95, streak))
    damp = smoothstep(0.55, 0.9, norm01(fbm(c, 0.8, 0.15, aniso=(1.0, 2.0))))
    stone = mix(stone, stone * np.array([0.68, 0.78, 0.64], F32), damp * damp_amt)
    eff = smoothstep(0.78, 0.95, norm01(fbm(c, 0.3, 0.03)))
    stone = mix(stone, np.broadcast_to(np.array([150, 146, 138], F32), stone.shape), eff * 0.18)
    stone = mul(stone, 0.80 + 0.30 * norm01(surf))
    mcol = ramp(norm01(mort + 0.4 * fbm(c, 0.05, 0.005)), [(0, mort_cols[0]), (0.6, mort_cols[1]), (1, mort_cols[2])])
    alb = mix(mcol, stone, smoothstep(0.2, 0.8, face))
    alb = mul(alb, 0.78 + 0.22 * smoothstep(0.0, 0.04, dmin))
    rough = rough0 - 0.18 * damp * damp_amt + 0.06 * m1
    rough = np.where(face < 0.5, 0.95, rough)
    return alb, h, rough, damp, face


def dungeon_wall(c):
    T = c.T
    hts = [0.34, 0.26, 0.30, 0.28, 0.32, 0.24, 0.26]

    def widths(ri, r):
        n = [3, 4, 3, 4, 3, 4, 3][ri]
        return (np.full(n, T / n), r.uniform(0, T / n))
    pal = [(3, (106, 102, 96)), (2, (94, 92, 92)), (2, (112, 102, 90)), (1, (88, 90, 94))]
    alb, h, rough, *_ = _ashlar(c, hts, widths, 110, 0.016, 0.020, 0.030, 0.0055, pal, 0.03, 0.0, [(58, 52, 46), (86, 79, 68), (116, 107, 92)], 0.22, 0.4, 0.80)
    return finish(c, alb, h, rough, normal_gain=1.0, ao_strength=1.1)


# -------------------------------------------------------------- Darklands ---
def darklands(c):
    T = c.T
    wx = fbm(c, 1.2, 0.4, a=1.2) * 0.015
    wy = fbm(c, 1.2, 0.4, a=1.2) * 0.015
    g1 = 5
    ox, oy = cell_offsets(c, g1, 1.0, 121)
    F1, F2, idx, dx, dy = voronoi((c.X * T + wx) / T * g1, (c.Y * T + wy) / T * g1, g1, ox, oy)
    d1 = (F2 - F1) * (T / g1) * 0.5
    g2 = 14
    ox2, oy2 = cell_offsets(c, g2, 1.0, 126)
    G1, G2, idx2, ex, ey = voronoi((c.X * T + wy) / T * g2, (c.Y * T + wx) / T * g2, g2, ox2, oy2)
    d2 = (G2 - G1) * (T / g2) * 0.5
    w1 = 0.003 + 0.009 * norm01(fbm(c, 0.8, 0.15))
    cr1 = 1 - smoothstep(w1 * 0.5, w1 * 0.5 + 0.010, d1)
    pres2 = smoothstep(-0.3, 0.6, fbm(c, 0.8, 0.15, salt=127))
    cr2 = (1 - smoothstep(0.0015, 0.004, d2)) * pres2
    cnt = g1 * g1
    plate = by_id(c, idx, cnt, 122, -0.006, 0.006)
    tx = by_id(c, idx, cnt, 125, -0.06, 0.06)
    ty = by_id(c, idx, cnt, 128, -0.06, 0.06)
    curl = np.exp(-(d1 / 0.035)) * by_id(c, idx, cnt, 123, 0.005, 0.016)   # plate edges curl up
    craze = (1 - smoothstep(0.0, 0.10, np.abs(fbm(c, 0.05, 0.005, a=0.8)))) * 0.0006
    chip = smoothstep(0.66, 0.9, norm01(fbm(c, 0.12, 0.015))) * np.exp(-(d1 / 0.04)) * 0.008
    top = plate + (tx * dx + ty * dy) * (T / g1) + curl - chip + fbm(c, 0.8, 0.12, a=1.3) * 0.005 + fbm(c, 0.1, 0.012, a=1.2) * 0.0018 - craze
    top += fbm(c, 0.012, 0.0018, a=0.8) * 0.0005 + fbm(c, 0.06, 0.012, a=0.9) * 0.0022 * smoothstep(0.4, 0.8, norm01(fbm(c, 0.4, 0.1)))
    h = top * (1 - cr1) + (-0.045) * cr1 - cr2 * 0.008
    h = gblur(h, 0.9)
    cav = np.clip((gblur(h, 0.05 / c.px) - h) / 0.04, 0, 1)
    # ash: settled in cracks and hollows, plus wind-streaked drifts on the plates
    streaks = norm01(fbm(c, 1.5, 0.04, aniso=(5.0, 1.0)))
    ash = np.clip((0.30 + 0.70 * smoothstep(0.2, 0.7, norm01(fbm(c, 0.5, 0.06)))) * 0.95 * cr1 + 0.9 * cav + 0.55 * smoothstep(0.55, 0.85, 0.6 * streaks + 0.4 * norm01(fbm(c, 0.9, 0.15))), 0, 1)
    h += ash * 0.006 * (0.4 + cr1)
    # cinders: angular scoria, plus a few larger clinkers
    cA = splat(c, 30, 124, (0.18, 0.46), (0.45, 1.0), kind="angular", zrange=1.0)
    cA["hit"] = cA["hit"] & (cA["rid"] < 0.16)
    cB = splat(c, 9, 129, (0.20, 0.35), (0.6, 1.0), kind="angular", zrange=1.0)
    cB["hit"] = cB["hit"] & (cB["rid"] < 0.12)
    which, z = top_layer([(cA, 0.0), (cB, 0.6)])
    cin = (which >= 0).astype(F32)
    edgeA = np.where(which == 1, cB["edge"], cA["edge"])
    ridA = np.where(which == 1, cB["rid"], cA["rid"])
    h += cin * (0.003 + 0.012 * np.clip(edgeA, 0, 1) ** 0.8 * (1 + 0.8 * (which == 1)))
    # colour
    t = norm01(fbm(c, 0.6, 0.05, a=1.1))
    crust = ramp(t, [(0, (44, 38, 40)), (0.5, (62, 54, 55)), (1, (92, 84, 82))])
    crust = mul(crust, 1 + 0.14 * speck(c, 0.002, 0.01) + 0.14 * fbm(c, 0.06, 0.006) + 0.10 * fbm(c, 0.4, 0.05))
    rust = smoothstep(0.3, 0.8, norm01(fbm(c, 0.5, 0.05))) * (1 - smoothstep(0.0, 0.10, d1))
    crust = mix(crust, np.array([104, 58, 46], F32) * np.ones_like(crust), rust[..., None] * 0.22)
    crust = mul(crust, 0.78 + 0.22 * smoothstep(0.0, 0.03, d1))
    ashc = ramp(norm01(fbm(c, 0.05, 0.005)), [(0, (108, 102, 106)), (1, (150, 144, 148))])
    alb = mix(crust, ashc, ash * 0.78)
    cc = ramp(ridA, [(0, (40, 34, 38)), (0.55, (58, 40, 38)), (0.8, (104, 50, 36)), (1, (36, 32, 40))])
    cc = mul(cc, 0.65 + 0.5 * np.clip(edgeA, 0, 1))
    alb = mix(alb, cc, cin * 0.95)
    alb = mix(alb, ashc * 0.9, cin * 0.35 * smoothstep(0.5, 0.9, np.clip(edgeA, 0, 1)) * 0.0 + (cin * ash * 0.25))
    alb = mul(alb, 0.70 + 0.30 * (1 - cr2 * 0.6))
    rough = 0.90 - 0.06 * ash
    rough = np.where(cin > 0.5, 0.45, rough)
    return finish(c, alb, h, rough, normal_gain=1.0, ao_strength=1.1)


# ---------------------------------------------------------------- snow ---
def snow_fresh(c):
    T = c.T
    drift = fbm(c, 1.6, 0.3, a=1.4)
    ph = c.Y * 8 + 0.25 * fbm(c, 1.5, 0.4, a=1.2)
    rip = np.sin(2 * np.pi * ph) * smoothstep(0.35, 0.8, norm01(fbm(c, 1.4, 0.4)))
    h = drift * 0.020 + rip * 0.0020 + fbm(c, 0.2, 0.04, a=1.3) * 0.0016 + fbm(c, 0.03, 0.006, a=1.0) * 0.00035
    grains = fbm(c, 0.008, 0.002, a=0.2)
    h += grains * 0.00006
    cav = np.clip((gblur(h, 0.12 / c.px) - h) / 0.02, 0, 1)
    base = ramp(norm01(fbm(c, 0.6, 0.06)), [(0, (218, 222, 230)), (1, (232, 234, 236))])
    cool = np.broadcast_to(np.array([190, 206, 228], F32), base.shape)
    alb = mix(base, cool, np.clip(cav * 0.7, 0, 0.6))
    alb = mul(alb, 1 + 0.015 * grains)
    sparkle = smoothstep(1.5, 2.6, grains)
    rough = 0.76 - 0.14 * sparkle + 0.06 * fbm(c, 0.2, 0.02)
    return finish(c, alb, h, rough, normal_gain=1.0, ao_strength=0.6, h_soften_px=1.0)


def snow_trampled(c):
    T = c.T
    drift = fbm(c, 1.6, 0.3, a=1.4)
    h = drift * 0.014 + fbm(c, 0.2, 0.04, a=1.3) * 0.0030 + fbm(c, 0.03, 0.006, a=1.0) * 0.0006
    grains = fbm(c, 0.008, 0.002, a=0.2)
    h += grains * 0.00006
    comp = smoothstep(0.42, 0.75, norm01(fbm(c, 1.4, 0.3)))
    h -= comp * 0.010 + comp * fbm(c, 0.12, 0.015) * 0.003
    prints = splat(c, 6, 131, (0.60, 0.66), (0.36, 0.40), kind="boot", zrange=1.0, jitter=1.0)
    prints["hit"] = prints["hit"] & (prints["rid"] < 0.62)
    inner = prints["hit"].astype(F32)
    soft = gblur(inner, 0.012 / c.px)
    lug = 0.5 + 0.5 * np.sign(np.sin(prints["lx"] * 30 + 1.2 * fbm(c, 0.05, 0.01))) * smoothstep(0.25, 0.5, prints["edge"])
    depth = (0.016 + 0.020 * prints["rid"]) * soft * (0.85 + 0.15 * lug)
    h -= depth
    ring = gblur(inner, 0.030 / c.px)
    h += np.clip(ring - soft, 0, 1) * 0.018
    h += fbm(c, 0.1, 0.01) * 0.0012 * soft
    fl = splat(c, 64, 132, (0.08, 0.30), (0.5, 0.9), kind="ellipse", zrange=0.0)
    fl["hit"] = fl["hit"] & (fl["rid"] < 0.05)
    base = ramp(norm01(fbm(c, 0.6, 0.06)), [(0, (210, 214, 222)), (1, (230, 232, 236))])
    cool = np.broadcast_to(np.array([188, 204, 228], F32), base.shape)
    cav = np.clip((gblur(h, 0.12 / c.px) - h) / 0.02, 0, 1)
    alb = mix(base, cool, np.clip(cav * 0.7, 0, 0.6))
    dirty = np.broadcast_to(np.array([160, 150, 140], F32), base.shape)
    alb = mix(alb, dirty, comp * 0.45)
    pc = ramp(np.clip(soft * (0.55 + 0.9 * prints["rid"]) , 0, 1), [(0, (214, 216, 222)), (0.5, (176, 170, 168)), (1, (136, 126, 118))])
    alb = mix(alb, pc, soft * 0.8)
    alb = mix(alb, np.broadcast_to(np.array([100, 90, 82], F32), alb.shape), fl["hit"].astype(F32) * 0.8)
    rough = 0.76 - 0.14 * smoothstep(1.5, 2.6, grains) + 0.06 * fbm(c, 0.2, 0.02)
    rough = rough - 0.20 * soft - 0.22 * comp
    return finish(c, alb, h, rough, normal_gain=1.0, ao_strength=0.8, h_soften_px=1.0)


# ----------------------------------------------------------------- cliff ---
def cliff_rock(c):
    T = c.T
    nb = 13
    R, hts = bedded_blocks(c, nb, 0.10, 0.80, 0.35, 2.4, 0.9, 0.05, 140)
    ns = R["nseg"]
    rs = lambda sl, lo, hi: c.rng(150 + sl).random(ns).astype(F32)[R["sid"]] * (hi - lo) + lo
    rr = c.rng(149)
    bed_hard = rr.uniform(0.0, 1.0, nb).astype(F32)[R["row"]]
    bed_rec = (-0.10 * (1 - bed_hard) + rr.uniform(-0.02, 0.02, nb).astype(F32)[R["row"]])
    du = np.minimum(R["u"] * R["w"], (1 - R["u"]) * R["w"])
    dv = np.minimum(R["v"] * R["h"], (1 - R["v"]) * R["h"])
    dmin = np.minimum(du, dv)
    openj = smoothstep(-0.6, 0.5, fbm(c, 1.2, 0.3, salt=147))
    gap = (0.004 + 0.026 * norm01(fbm(c, 1.0, 0.2))) * (0.25 + 0.75 * openj)
    face = smoothstep(gap * 0.5, gap * 0.5 + 0.004, dmin)           # sharp joint edge
    # erosion rounding: soft beds round off strongly, hard beds stay crisp
    rad = 0.015 + 0.07 * (1 - bed_hard)
    round_ = 1 - np.exp(-np.clip(dmin - gap * 0.5, 0, None) / rad)
    off = rs(1, -0.05, 0.05)
    tx = rs(2, -0.10, 0.10)
    ty = rs(3, -0.08, 0.08)
    top = bed_rec + off + (R["u"] - 0.5) * R["w"] * tx + (R["v"] - 0.5) * R["h"] * ty
    chip = smoothstep(0.62, 0.86, norm01(fbm(c, 0.25, 0.03))) * (1 - smoothstep(0.0, 0.12, dmin)) * 0.05
    lam = fbm(c, 1.5, 0.01, a=0.9, aniso=(10.0, 1.0))                # bedding laminations
    surf = (fbm(c, 0.3, 0.04, a=1.4) * 0.008 + fbm(c, 0.04, 0.005, a=1.2) * 0.0025 + lam * 0.0012 +
            fbm(c, 0.01, 0.0015, a=0.8) * 0.0005)
    h = np.where(face > 0.5, 1.0, 1.0) * (top - 0.045 * (1 - round_) + surf - chip * (1 - round_ * 0.3))
    h = h * face + (-0.04 - 0.14 * openj + bed_rec * 0.5) * (1 - face)
    # second and third joint sets: oblique, angular, fading in and out (no curves)
    cr_all = np.zeros_like(h)
    for (i, j, sal) in ((3, 2, 160), (3, -3, 161)):
        d = joint_dist(c, i, j, fbm(c, 1.5, 0.4) * 0.03)
        pres = smoothstep(-0.2, 0.5, fbm(c, 1.2, 0.3, salt=sal))
        w = 0.008 + 0.014 * norm01(fbm(c, 0.6, 0.1))
        cr = (1 - smoothstep(w * 0.5, w * 0.5 + 0.006, d)) * pres
        cr_all = np.maximum(cr_all, cr)
    h -= cr_all * 0.07
    h = gblur(h, 0.9)
    cav = np.clip((gblur(h, 0.10 / c.px) - h) / 0.06, 0, 1)
    # colour: every bed has its own rock type; blocks and laminations vary inside it
    cr_ = c.rng(148)
    bedpal = np.array([(150, 128, 98), (118, 114, 108), (160, 140, 112), (128, 100, 78), (108, 104, 98),
                       (170, 154, 126), (96, 90, 86), (140, 112, 84), (124, 120, 104)], F32)
    pick = np.concatenate([cr_.permutation(len(bedpal)) for _ in range(3)])[:nb]
    bc = bedpal[pick][R["row"]]
    bc = bc * 0.78 + bc.mean(-1, keepdims=True) * 0.22
    ct = bc * (rs(4, 0.88, 1.10))[..., None]
    ct = mul(ct, 1 + 0.10 * lam + 0.10 * fbm(c, 0.5, 0.04, a=1.1) + 0.07 * speck(c, 0.003, 0.012))
    ct = mul(ct, 1 + 0.12 * fbm(c, 4.0, 0.8, a=1.0))
    fe = smoothstep(0.55, 0.85, norm01(fbm(c, 0.8, 0.1, aniso=(3.0, 1.0))))
    ct = mix(ct, ct * np.array([1.12, 0.92, 0.72], F32), fe * 0.5)     # iron staining along beds
    streak = norm01(fbm(c, 2.0, 0.06, aniso=(1.0, 6.0)))
    ct = mul(ct, 0.74 + 0.30 * (1 - smoothstep(0.6, 0.95, streak)))
    ct = mul(ct, 0.50 + 0.50 * (1 - cav))
    fresh = (1 - smoothstep(0.0, 0.04, np.abs(chip))) * 0 + smoothstep(0.1, 0.5, chip / 0.05)
    ct = mix(ct, ct * 1.18, fresh * 0.7)                              # fresh un-weathered fracture faces
    jd = 1 - face
    ct = mix(ct, np.array([34, 30, 28], F32) * np.ones_like(ct), np.clip(jd + cr_all * 0.8, 0, 1)[..., None] * 0.85)
    lich = splat(c, 14, 144, (0.2, 0.5), (0.7, 1.0), kind="ellipse", zrange=0.0)
    lich["hit"] = lich["hit"] & (lich["rid"] < 0.16) & (cav < 0.35)
    lcol = ramp(lich["rid"] * 6, [(0, (160, 132, 64)), (0.5, (146, 150, 118)), (1, (176, 172, 138))])
    lm = lich["hit"].astype(F32) * smoothstep(0.0, 0.5, lich["edge"]) * 0.55
    alb = mix(ct, lcol, lm)
    rough = 0.88 - 0.08 * cav + 0.05 * fbm(c, 0.1, 0.01) - 0.06 * fresh
    rough = np.where(lm > 0.2, 0.95, rough)
    return finish(c, alb, h, rough, normal_gain=0.9, ao_strength=1.2)


# ------------------------------------------------------------- timber planks ---
def planks(c):
    T = c.T
    hts = [0.17, 0.21, 0.19, 0.23, 0.18, 0.20, 0.22, 0.17, 0.20, 0.23]

    def widths(ri, r):
        p = r.uniform(0.55, 1.45)
        return ([p, T - p], r.uniform(0, T))
    wy = fbm(c, 0.3, 0.05, a=1.3) * 0.0015
    wx = fbm(c, 0.3, 0.05, a=1.3) * 0.0015
    R = ragged_rows(c, hts, widths, wx, wy, salt=151)
    ns = R["nseg"]
    rs = lambda salt, lo, hi: c.rng(salt).random(ns).astype(F32)[R["sid"]] * (hi - lo) + lo
    gap = 0.0035
    dv = np.minimum(R["v"] * R["h"], (1 - R["v"]) * R["h"])
    du = np.minimum(R["u"] * R["w"], (1 - R["u"]) * R["w"])
    dmin = np.minimum(dv, du)
    face = smoothstep(gap * 0.5, gap * 0.5 + 0.0018, dmin)
    # grain
    wn = fbm(c, 1.6, 0.06, a=1.2, aniso=(7.0, 1.0))
    knots = splat(c, 4, 152, (0.10, 0.20), (0.55, 0.85), kind="ellipse", zrange=0.0)
    knots["hit"] = knots["hit"] & (knots["rid"] < 0.55)
    kq = np.sqrt(np.clip(1 - knots["edge"], 0, 1))
    kring = np.where(knots["hit"], 0.9 * (1 - kq) ** 1.0 * 6.0 + 0.0, 0.0)
    g = R["yy"] * 46 + 2.2 * wn + rs(153, 0, 40) + kring
    sfrac = g - np.floor(g)
    late = smoothstep(0.50, 0.92, sfrac) * (1 - smoothstep(0.96, 1.0, sfrac))
    fibre = fbm(c, 0.2, 0.0016, a=0.7, aniso=(18.0, 1.0))
    # cupping + per-plank offsets
    cup = (R["v"] - 0.5) ** 2 * 0.012
    off = rs(154, -0.0012, 0.0012)
    erosion = -0.0011 * (1 - late)
    # surface checks
    ck = fbm(c, 1.0, 0.1, a=1.0, aniso=(9.0, 1.0))
    ckmask = smoothstep(0.7, 1.2, fbm(c, 0.9, 0.15))
    crack = (1 - smoothstep(0.0, 0.05, np.abs(ck))) * ckmask
    h = face * (0.006 + off + cup + erosion + fibre * 0.00018 + 0.0004 * wn) - crack * 0.003
    h += np.where(knots["hit"], knots["edge"] * -0.0006 + 0.0012 * (1 - knots["edge"]), 0) * face
    # colours: weathered silver/brown
    tone = rs(155, 0.0, 1.0)
    base = ramp(tone, [(0, (106, 86, 64)), (0.5, (132, 112, 88)), (1, (156, 144, 128))])
    warm = smoothstep(0.55, 0.9, norm01(fbm(c, 0.8, 0.12, aniso=(2.0, 1.0))))
    base = mix(base, np.broadcast_to(np.array([124, 92, 62], F32), base.shape), warm * 0.45)
    col = mul(base, 0.86 + 0.16 * late * -1 + 0.12 * (1 - late) * 0.5 + 0.10 * fibre + 0.06 * wn)
    col = mul(col, 0.96 - 0.14 * late)
    kc = ramp(np.clip(knots["edge"], 0, 1), [(0, (92, 74, 56)), (0.5, (66, 46, 30)), (1, (44, 30, 22))])
    col = mix(col, kc, np.where(knots["hit"], 0.8 * (1 - knots["edge"] ** 2 * 0.0), 0).astype(F32) * 0.85 * smoothstep(0, 0.3, 1 - knots["edge"] + 0.15))
    col = mix(col, np.broadcast_to(np.array([46, 36, 28], F32), col.shape), crack * 0.85)
    gcol = ramp(norm01(fbm(c, 0.05, 0.004)), [(0, (28, 22, 18)), (1, (58, 46, 36))])
    col = mix(gcol, col, smoothstep(0.1, 0.9, face))
    # nails with rust streaks
    xs = R["u"] * R["w"]
    ds = np.minimum(np.abs(xs - 0.035), np.abs(xs - (R["w"] - 0.035)))
    ds2 = np.minimum(ds, np.abs(xs - R["w"] * 0.5) + 10 * (rs(156, 0, 1) < 0.5))
    vn = np.where(R["v"] < 0.5, 0.26, 0.74)
    dyn = (R["v"] - vn) * R["h"]
    dist = np.sqrt(ds2 ** 2 + dyn ** 2)
    nail = (dist < 0.0034) & (face > 0.5)
    streak = np.exp(-(ds2 / 0.0055) ** 2) * np.where(dyn > 0, np.exp(-np.clip(dyn, 0, 1) / 0.05), 0) * (face > 0.5)
    col = mul(col, 1 - 0.28 * streak)
    col = mix(col, np.broadcast_to(np.array([58, 48, 42], F32), col.shape), nail.astype(F32))
    h += nail * 0.0006
    rough = 0.82 + 0.10 * late - 0.06 * fibre
    rough = np.where(nail, 0.55, rough)
    return finish(c, col, h, rough, normal_gain=1.0, ao_strength=1.0)


# ---------------------------------------------------------------- roofs ---
def _course_profile(v, thick, drop_margin=0.0):
    """Overlapped course: ramps from 0 at the top (tucked under the course above) to
    `thick` at the free butt edge."""
    return thick * (v ** 1.3)


def slate_roof(c):
    T = c.T
    n = 10
    hts = [T / n] * n

    def widths(ri, r):
        return (np.full(8, T / 8), r.uniform(0, T / 8))
    wx = fbm(c, 0.3, 0.06, a=1.3) * 0.0025
    wy = fbm(c, 0.3, 0.06, a=1.3) * 0.0020
    R = ragged_rows(c, hts, widths, wx, wy, salt=161)
    ns = R["nseg"]
    rs = lambda salt, lo, hi: c.rng(salt).random(ns).astype(F32)[R["sid"]] * (hi - lo) + lo
    du = np.minimum(R["u"] * R["w"], (1 - R["u"]) * R["w"])
    dfree = np.minimum(du, (1 - R["v"]) * R["h"])             # distance to a free (exposed) edge
    gap = 0.004
    side = smoothstep(gap * 0.5, gap * 0.5 + 0.0016, du)
    thick = 0.012 + rs(162, 0.0, 0.0035)
    bow = rs(163, -0.0015, 0.0015) * np.sin(np.pi * R["u"])
    prof = _course_profile(R["v"], thick)
    # cleavage: fine parallel laminae running across each slate, with step-like delamination
    lam = fbm(c, 0.5, 0.0025, a=0.7, aniso=(14.0, 1.0))
    lam_h = np.round(lam * 2.0) / 2.0                          # terraced cleavage steps
    surf = fbm(c, 0.2, 0.02, a=1.3) * 0.0010 + fbm(c, 0.02, 0.0025, a=0.9) * 0.0003
    chipn = norm01(fbm(c, 0.07, 0.008))
    chip = smoothstep(0.55, 0.82, chipn) * (1 - smoothstep(0.0, 0.035, dfree))
    spall = smoothstep(0.45, 0.75, norm01(fbm(c, 0.03, 0.004))) * (1 - smoothstep(0.0, 0.012, dfree))
    h = side * (prof + bow + surf + lam_h * 0.0006 + lam * 0.0003 - chip * 0.006 - spall * 0.0025)
    h -= (1 - side) * 0.004
    # colour: blue-grey slate; sheen along cleavage, chipped edges show paler fresh rock
    tone = rs(164, 0, 1)
    base = ramp(tone, pal_ramp([(4, (68, 74, 82)), (3, (76, 80, 88)), (1, (70, 77, 77)), (1, (86, 90, 96)), (1, (76, 72, 80))]))
    base = mul(base, rs(165, 0.82, 1.15))
    m1 = fbm(c, 0.3, 0.03, a=1.2)
    col = mul(base, 1 + 0.05 * m1 + 0.12 * lam + 0.05 * fbm(c, 0.006, 0.001, a=0.3))
    shade = smoothstep(0.0, 0.22, R["v"])
    col = mul(col, 0.62 + 0.38 * shade)
    q, mi, dk = mineral_flecks(c, 1.4)
    col = mix(col, np.array([186, 188, 194], F32) * np.ones_like(col), (mi * side)[..., None] * 0.70)   # mica
    col = mix(col, np.array([200, 198, 190], F32) * np.ones_like(col), (q * side)[..., None] * 0.55)    # quartz
    col = mix(col, np.array([30, 30, 34], F32) * np.ones_like(col), (dk * side)[..., None] * 0.40)
    vein = (1 - smoothstep(0.0008, 0.0022, joint_dist(c, 5, 3, fbm(c, 0.8, 0.2) * 0.01))) * smoothstep(0.0, 0.7, fbm(c, 0.8, 0.2, salt=165))
    col = mix(col, np.array([150, 152, 150], F32) * np.ones_like(col), (vein * side)[..., None] * 0.45)  # quartz veins
    rust = smoothstep(0.7, 0.92, norm01(fbm(c, 0.2, 0.02))) * smoothstep(0.5, 1.0, R["v"])
    col = mix(col, col * np.array([1.30, 1.0, 0.72], F32), rust[..., None] * 0.55)           # iron stain below nail holes
    col = mix(col, np.array([118, 124, 134], F32) * np.ones_like(col), (np.maximum(chip, spall * 0.6) * (0.4 + 0.6 * np.abs(lam_h)))[..., None] * 0.65)
    lich = smoothstep(0.68, 0.9, norm01(fbm(c, 0.3, 0.03) + 0.4 * fbm(c, 0.05, 0.004)))
    lcol = ramp(norm01(fbm(c, 0.03, 0.003)), [(0, (84, 96, 70)), (1, (138, 142, 112))])
    col = mix(col, lcol, lich * 0.32 * shade)
    col = mix(col, np.array([150, 134, 112], F32) * np.ones_like(col), (smoothstep(0.80, 0.98, R["v"]) * 0.14)[..., None])
    col = mix(np.array([30, 30, 34], F32) * np.ones_like(col), col, smoothstep(0.1, 0.9, side)[..., None])
    wet = smoothstep(0.55, 0.9, norm01(fbm(c, 1.0, 0.08, aniso=(1.0, 4.0))))
    col = mul(col, 1 - 0.20 * wet)
    rough = 0.60 + 0.16 * norm01(m1) - 0.12 * wet + 0.1 * lich - 0.28 * mi + 0.12 * (chip + spall)
    return finish(c, col, h, rough, normal_gain=1.0, ao_strength=1.2)


def shingle_roof(c):
    T = c.T
    n = 16
    hts = [T / n] * n
    wmin, wmax = 0.09, 0.16

    def widths(ri, r):
        w = []
        while sum(w) < T - wmax:
            w.append(r.uniform(wmin, wmax))
        rest = T - sum(w)
        if rest < wmin * 0.8:
            w[-1] += rest
        else:
            w.append(rest)
        w = np.array(w)
        w *= T / w.sum()
        return (w, r.uniform(0, T))
    wx = fbm(c, 0.3, 0.06, a=1.3) * 0.0016
    wy = fbm(c, 0.3, 0.06, a=1.3) * 0.0012
    R = ragged_rows(c, hts, widths, wx, wy, salt=171)
    ns = R["nseg"]
    rs = lambda salt, lo, hi: c.rng(salt).random(ns).astype(F32)[R["sid"]] * (hi - lo) + lo
    du = np.minimum(R["u"] * R["w"], (1 - R["u"]) * R["w"])
    gap = 0.0032
    side = smoothstep(gap * 0.5, gap * 0.5 + 0.0016, du)
    thick = 0.013 + rs(172, 0.0, 0.004)
    cup = (R["u"] - 0.5) ** 2 * rs(173, 0.0, 0.016)
    prof = thick * (R["v"] ** 1.15)
    # vertical wood grain on each shingle
    wn = fbm(c, 1.0, 0.05, a=1.2, aniso=(1.0, 6.0))
    gcoord = R["xx"] * 52 + 3.2 * wn + rs(174, 0, 50)
    gf = gcoord - np.floor(gcoord)
    late = smoothstep(0.5, 0.92, gf) * (1 - smoothstep(0.96, 1.0, gf))
    fibre = fbm(c, 0.2, 0.0016, a=0.7, aniso=(1.0, 18.0))
    # splits
    u0 = rs(175, 0.15, 0.85)
    has = rs(176, 0, 1) < 0.30
    sd = np.abs(R["u"] - u0 + 0.04 * wn) * R["w"]
    split = (sd < 0.0016) & has & (R["v"] > 0.0)
    h = side * (prof + cup - 0.00055 * (1 - late) + fibre * 0.00018 + fbm(c, 0.1, 0.01, a=1.2) * 0.0008) - split * 0.004
    h -= (1 - side) * 0.005
    tone = rs(177, 0, 1)
    base = ramp(tone, [(0, (86, 68, 52)), (0.5, (122, 100, 78)), (1, (150, 134, 114))])
    base = mul(base, rs(178, 0.84, 1.12))
    col = mul(base, 0.90 + 0.12 * (1 - late) + 0.10 * fibre + 0.05 * wn)
    col = mul(col, 0.58 + 0.42 * smoothstep(0.0, 0.2, R["v"]))
    moss = smoothstep(0.64, 0.88, norm01(fbm(c, 0.5, 0.05) + 0.3 * fbm(c, 0.05, 0.005)))
    mcol = ramp(norm01(fbm(c, 0.03, 0.003)), [(0, (50, 70, 34)), (1, (96, 118, 56))])
    col = mix(col, mcol, moss * 0.6)
    col = mix(col, np.broadcast_to(np.array([36, 28, 22], F32), col.shape), split.astype(F32) * 0.85)
    sooty = smoothstep(0.6, 0.9, norm01(fbm(c, 1.0, 0.08, aniso=(1.0, 4.0))))
    col = mul(col, 1 - 0.22 * sooty)
    gcol = np.broadcast_to(np.array([52, 40, 30], F32), col.shape)
    col = mix(gcol, col, smoothstep(0.1, 0.9, side))
    h += moss * 0.0015
    rough = 0.80 + 0.10 * late + 0.06 * moss
    return finish(c, col, h, rough, normal_gain=1.0, ao_strength=1.2)


# ------------------------------------------------------------------ brick ---
def brick(c):
    T = c.T
    n = 26
    hts = [T / n] * n

    def widths(ri, r):
        return (np.full(9, T / 9), (T / 9) * 0.5 * (ri % 2))
    wx = fbm(c, 0.2, 0.03, a=1.3) * 0.0012
    wy = fbm(c, 0.2, 0.03, a=1.3) * 0.0012
    R = ragged_rows(c, hts, widths, wx, wy, salt=181)
    ns = R["nseg"]
    rs = lambda salt, lo, hi: c.rng(salt).random(ns).astype(F32)[R["sid"]] * (hi - lo) + lo
    dmin = np.minimum(np.minimum(R["u"] * R["w"], (1 - R["u"]) * R["w"]), np.minimum(R["v"] * R["h"], (1 - R["v"]) * R["h"]))
    mj = 0.010
    face = smoothstep(mj * 0.5, mj * 0.5 + 0.0016, dmin)
    arris = smoothstep(mj * 0.5, mj * 0.5 + 0.004, dmin)
    pit = fbm(c, 0.04, 0.0015, a=1.0)
    surf = fbm(c, 0.3, 0.03, a=1.2) * 0.0007 + pit * 0.00035
    off = rs(182, -0.0016, 0.0016)
    chip = smoothstep(0.72, 0.95, norm01(fbm(c, 0.03, 0.004))) * (1 - arris) * 0.003
    h = face * (0.008 + off + 0.0015 * arris + surf - chip)
    mort = fbm(c, 0.06, 0.0015, a=0.9)
    h += (1 - face) * (mort * 0.0008)
    tone = rs(183, 0, 1)
    base = ramp(tone, pal_ramp([(4, (136, 70, 52)), (3, (150, 84, 58)), (2, (116, 62, 50)), (1, (160, 120, 88)), (1, (92, 54, 48))]))
    base = mul(base, rs(184, 0.86, 1.12))
    burn = norm01(fbm(c, 0.12, 0.02, a=1.2))
    col = mul(base, 0.85 + 0.30 * burn)
    col = mix(col, col * np.array([0.66, 0.62, 0.66], F32), rs(185, 0, 1)[..., None] * (R["u"][..., None] > 0.55) * 0.3 * (rs(186, 0, 1) < 0.35)[..., None])
    col = mul(col, 1 + 0.09 * speck(c, 0.0015, 0.008) + 0.12 * pit)
    eff = smoothstep(0.72, 0.95, norm01(fbm(c, 0.4, 0.04)))
    col = mix(col, np.broadcast_to(np.array([200, 196, 188], F32), col.shape), eff * 0.22)
    streak = smoothstep(0.6, 0.92, norm01(fbm(c, 1.0, 0.04, aniso=(1.0, 5.0))))
    col = mul(col, 1 - 0.16 * streak)
    col = mul(col, 0.80 + 0.20 * smoothstep(0.0, 0.012, dmin))
    mcol = ramp(norm01(mort + 0.4 * fbm(c, 0.2, 0.01)), [(0, (136, 128, 114)), (0.5, (164, 156, 140)), (1, (188, 180, 164))])
    mcol = mul(mcol, 1 - 0.20 * streak)
    alb = mix(mcol, col, smoothstep(0.1, 0.9, face))
    rough = 0.78 + 0.10 * burn
    rough = np.where(face < 0.5, 0.93, rough)
    return finish(c, alb, h, rough, normal_gain=1.0, ao_strength=1.1)


# ------------------------------------------------------------- registry ---
# name: (function, tile_m, seed, region note)
REGISTRY = {
    "CobbleStreet": (cobble, 2.0, 2101),
    "DirtRoadRuts": (dirt_road, 3.0, 2102),
    "ForestFloor": (forest_floor, 2.0, 2103),
    "WetSand": (wet_sand, 2.0, 2104),
    "BeachPebbles": (beach_pebbles, 1.0, 2105),
    "MossyCaveRock": (cave_rock, 2.0, 2106),
    "DungeonMasonry": (dungeon_wall, 2.0, 2107),
    "DungeonFlagstone": (dungeon_flags, 2.0, 2108),
    "DarklandsSoil": (darklands, 2.0, 2109),
    "SnowFresh": (snow_fresh, 2.0, 2110),
    "SnowTrampled": (snow_trampled, 2.0, 2111),
    "CliffRock": (cliff_rock, 4.0, 2112),
    "TimberPlanks": (planks, 2.0, 2113),
    "RoofSlate": (slate_roof, 2.0, 2114),
    "RoofShingles": (shingle_roof, 2.0, 2115),
    "BrickWall": (brick, 2.0, 2116),
}
