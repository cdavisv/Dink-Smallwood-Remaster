"""Bushes v2: a multi-stemmed shrub. Stems rise from the ground at a common stool and arch out, fork into branches and twigs; leaf-spray cards sit
on the twigs at every depth (dark interior tiles inside and underneath, sunlit tiles on the top shell), with bare dead stems, sky gaps and long
shoots breaking the dome outline. Two leaf types (atlas T_Veg_Shrub rows 0 / 1). Materials: MI_Veg_DarkBark, MI_Veg_Shrub."""
import numpy as np, math
from bl_tree import *
E = 3.0 / 2048
def ST(c, r): return (c * 0.25 + E, 1 - (r + 1) * 0.25 + E, (c + 1) * 0.25 - E, 1 - r * 0.25 - E)
UPV = np.array([0, 0, 1.0]); NSUB = 4
BUSH = {
 'SM_Veg_Bush_Small_01': dict(seed=111, rad=(0.86, 0.82), H=1.12, stems=10, leaf='A', dead=1, gaps=0, br=1.1),
 'SM_Veg_Bush_Round_Medium_01': dict(seed=123, rad=(0.86, 0.84), H=1.05, stems=11, leaf='B', dead=1, gaps=1, br=1.0),
 'SM_Veg_Bush_Round_Large_01': dict(seed=137, rad=(1.32, 1.22), H=1.42, stems=15, leaf='A', dead=2, gaps=2, br=1.1),
 'SM_Veg_Bush_Wide_01': dict(seed=149, rad=(1.36, 1.18), H=1.36, stems=16, leaf='B', dead=2, gaps=2, br=1.1),
}
BL = {0: dict(st_sides=4, st_ds=0.2, br_keep=1.0, br_sides=3, br_segs=2, twigs=True, keep=1.0, scale=1.0, segs=1),
      1: dict(st_sides=4, st_ds=0.28, br_keep=0.6, br_sides=3, br_segs=2, twigs=False, keep=0.5, scale=1.35, segs=1),
      2: dict(st_sides=3, st_ds=0.5, br_keep=0.0, br_sides=3, br_segs=1, twigs=False, keep=0.2, scale=2.0, segs=1)}

def bez(p0, c, p1, n):
    t = np.linspace(0, 1, n + 1)[:, None]; return (1 - t) ** 2 * p0 + 2 * t * (1 - t) * c + t ** 2 * p1

def build(name, lod):
    P = BUSH[name]; C = BL[lod]; rng = np.random.default_rng(P['seed']); mb = MeshB(); rx, ry = P['rad']; H = P['H']; kind = P['leaf']; row = 0 if kind == 'A' else 1
    radv = np.array([rx, ry, H]); cc = np.array([0, 0, H * 0.42]); ph = rng.uniform(0, 6.28, 4)
    def env(az, el):          # lumpy dome
        b = 1 + 0.13 * math.sin(3 * az + ph[0]) * math.cos(el) + 0.10 * math.sin(5 * az + ph[1] + 2 * el) + 0.08 * math.sin(4 * el + ph[2] + az)
        return np.array([rx * math.cos(el) * math.cos(az), ry * math.cos(el) * math.sin(az), H * math.sin(el)]) * b
    gaps = [env(rng.uniform(0, 6.28), rng.uniform(0.35, 1.0)) for _ in range(P['gaps'])]; grad = 0.26 * (rx + ry) / 2 + 0.08
    def in_gap(p): return any(np.linalg.norm(p - g) < grad for g in gaps)
    def tile_for(p, d):
        rf = float(np.linalg.norm(p / radv)); out = nrm(p - cc); u = rng.random()
        if u < 0.07: return ST(0 if kind == 'A' else 1, 3)                                 # yellowing
        if u < 0.16: return ST(0 if kind == 'A' else 1, 2)                                 # sparse, twiggy
        if p[2] < 0.28 * H or out[2] < -0.1 or rf < 0.58: return ST(3, row) if rng.random() < 0.8 else ST(2, row)     # underside / interior: dark
        if rf > 0.8 and out[2] > 0.35: return ST(0, row) if rng.random() < 0.4 else ST(1, row)                       # sunlit top
        return ST(1 + int(rng.integers(2)), row)
    def card(o, d, L, tile, wind, key, mat=1, droop=None, width=1.0, cross=False, split=True):
        # v3: every spray is a small group of little cards at different depths around the twig, not one 40 cm plate
        if not split: return card1(o, d, L * 0.75, tile, wind, key, mat, droop, width, cross)
        for j in range(NSUB):
            off = rng.normal(0, 0.22, 3) * np.array([1, 1, 0.75]) * L; dj = nrm(nrm(d) + rng.normal(0, 0.5, 3)); Lj = L * rng.uniform(0.5, 0.68); kj = key if j == 0 else rng.random()
            card1(np.asarray(o) + (off if j else 0), dj, Lj, tile, wind, kj, mat, droop, width, cross if j == 0 else (j % 2 == 1))
    def card1(o, d, L, tile, wind, key, mat=1, droop=None, width=1.0, cross=False):
        jit = rng.normal(0, 0.4, 3); dr = rng.uniform(0.0, 0.45); fl = rng.random() < 0.5          # drawn before the LOD test: every LOD is the same bush
        if key >= C['keep']: return
        sc = C['scale']; d = nrm(d); out_ = nrm(np.asarray(o) - cc); d = nrm(d - out_ * max(0.0, float(np.dot(d, out_))) * 0.55)      # lay sprays over toward the dome surface: fewer radial spikes seen end-on
        w = nrm(np.cross(d, out_ + jit) + 1e-6)
        if cross: w = np.cross(d, w)        # the partner card of a crossed pair: no cluster is ever seen as one edge-on plane
        mb.card(np.asarray(o) - d * (0.05 + L * (sc - 1) * 0.5), d, w, L * sc, L * sc * width, tile, C['segs'], 1, dr if droop is None else droop, 0,
                np.array([0, 0, H * 0.25]), 0.7, wind, mat, fl)
    ns = P['stems']; dead_ids = set(rng.choice(ns, P['dead'], replace=False).tolist())
    for si in range(ns):
        az = 2 * math.pi * (si + rng.uniform(-0.35, 0.35)) / ns; isdead = si in dead_ids
        el = math.radians(rng.uniform(10, 30)) if isdead else math.asin(min(0.995, (0.16 + 0.84 * ((si * 0.618 + rng.uniform(0, 0.2)) % 1.0))))      # targets spread evenly over the dome: plenty of stems arch out low
        tgt = env(az, el) * rng.uniform(0.85, 1.0) * (0.85 if isdead else 1.0); tgt[2] = max(tgt[2], 0.22)
        b0 = np.array([math.cos(az), math.sin(az), 0]) * rng.uniform(0.03, 0.16) * (rx + ry) / 2
        L0 = np.linalg.norm(tgt - b0); ctrl = b0 + UPV * L0 * rng.uniform(0.45, 0.7) + (tgt - b0) * np.array([0.18, 0.18, 0])
        pts = bez(b0, ctrl, tgt, 12); pts[1:-1] += rng.normal(0, 0.012, (11, 3)); pts[:, 2] = np.maximum(pts[:, 2], 0.0)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); LL = cum[-1]; phase = rng.random()
        r0 = 0.011 + 0.010 * LL; rad = r0 * (1 - 0.72 * (cum / LL) ** 0.9)
        skip_stem = lod == 2 and si % 2 == 1
        if not skip_stem:
            p2, r2 = resample(pts, rad, C['st_ds'])
            mb.tube(p2, r2, C['st_sides'], 'limb', 1, 0.35, wind=(0, phase, 0, 0), wind1=(p2[-1][2] / H, phase, 0, 0.6), cap=True)
        def pt(s):
            i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2)); return pts[i] + (pts[i + 1] - pts[i]) * (s - cum[i]) / seg[i], nrm(pts[i + 1] - pts[i])
        # branches
        s = LL * rng.uniform(0.22, 0.32); k = 0
        while s < LL - 0.04:
            p, tg = pt(s); t = s / LL; key_b = rng.random()
            perp = nrm(np.cross(tg, rng.normal(0, 1, 3))); out = nrm(p - cc * np.array([1, 1, 0.5]))
            d = nrm(tg * 0.55 + perp * 0.8 + out * 0.35 + UPV * 0.15); Lb = rng.uniform(0.24, 0.5) * (1.15 - 0.55 * t) * P['br']
            bp = path(p, d, Lb, 4, rng, 0.3, lambda tt, dd, pp: (0, 0, -0.25)); bp[:, 2] = np.maximum(bp[:, 2], 0.03)
            wind = (p[2] / H, phase, 0, 0.3 + 0.7 * t); bare = isdead or in_gap(bp[-1])
            if key_b < C['br_keep']:
                sel = np.unique(np.round(np.linspace(0, 4, C['br_segs'] + 1)).astype(int))
                mb.tube(bp[sel], np.linspace(0.0065, 0.003, 5)[sel], C['br_sides'], 'limb', 1, 0.3, wind=wind, wind1=wind, cap=False)
            for q in range(2):                  # twigs off the branch
                j = 1 + q; d2 = nrm(nrm(bp[j + 1] - bp[j]) * 0.5 + np.cross(nrm(bp[j + 1] - bp[j]), rng.normal(0, 1, 3)) * 0.8 + UPV * 0.2); L2 = rng.uniform(0.12, 0.22)
                e2 = bp[j] + d2 * L2; key_t = rng.random(); key_c = rng.random(); Lc = rng.uniform(0.3, 0.46)
                if C['twigs'] and key_t < 0.45: mb.tube(np.array([bp[j], e2]), [0.0035, 0.002], 3, 'limb', 1, 0.3, wind=wind, wind1=wind, cap=False)
                if bare:
                    if key_c < 0.5: card(bp[j], d2, Lc * 1.1, ST(2 + int(rng.integers(2)), 2), wind, rng.random(), split=False)
                else: card(bp[j] + d2 * 0.03, d2, Lc, tile_for(e2, d2), wind, rng.random())
            dtip = nrm(bp[-1] - bp[-2]); key_c = rng.random(); Lc = rng.uniform(0.32, 0.5)
            if bare: card(bp[-2], dtip, Lc * 1.1, ST(2 + int(rng.integers(2)), 2), wind, key_c, split=False)
            else:
                tl_ = tile_for(bp[-1] + dtip * 0.2, dtip); card(bp[-2], dtip, Lc, tl_, wind, key_c); card(bp[-2], dtip, Lc * 0.9, tl_, wind, 0.25 + 0.75 * rng.random(), cross=True)
                card(bp[1], nrm(d + rng.normal(0, 0.5, 3)), rng.uniform(0.3, 0.44), tile_for(bp[2], d), wind, rng.random())
            s += rng.uniform(0.11, 0.2) / P['br']; k += 1
        # stem tip
        p, tg = pt(LL - 0.02); wind = (p[2] / H, phase, 0, 1.0)
        if isdead:
            for q in range(2): card(p - tg * 0.1, nrm(tg + rng.normal(0, 0.4, 3)), rng.uniform(0.38, 0.5), ST(2 + q, 2), wind, rng.random() * 0.5, split=False)
        else:
            for q in range(4): card(p - tg * 0.08, nrm(tg + rng.normal(0, 0.55, 3)), rng.uniform(0.34, 0.5), tile_for(p + tg * 0.2, tg), wind, rng.random() * (0.6 if q == 0 else 1.0), cross=q % 2 == 1)
            if p[2] > 0.55 * H and rng.random() < 0.7:        # a long open shoot standing clear of the dome
                card(p, nrm(tg * 0.6 + UPV * 0.7 + rng.normal(0, 0.25, 3)), rng.uniform(0.42, 0.56), ST(2 + (0 if kind == 'A' else 1), 3), wind, rng.random() * 0.45, droop=0.05, split=False)
    for q in range(4 + P['dead'] * 2):       # dead twigs in the dark at the foot of the stool
        a = rng.uniform(0, 6.28); o = np.array([math.cos(a), math.sin(a), 0]) * rng.uniform(0.05, 0.3) * rx + UPV * rng.uniform(0.05, 0.3)
        card(o, nrm(np.array([math.cos(a), math.sin(a), rng.uniform(0.1, 0.9)])), rng.uniform(0.35, 0.5), ST(2 + int(rng.integers(2)), 2), (0.1, rng.random(), 0, 0.2), rng.random(), split=False)
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.0); mb.v = list(V); recenter(mb)
    print('BUSH', name, lod, 'cardtris', sum(len(f) - 2 for f, m in zip(mb.faces, mb.mat) if m >= 1), 'woodtris', sum(len(f) - 2 for f, m in zip(mb.faces, mb.mat) if m == 0))
    ob = mb.build(f'{name}_LOD{lod}', [game_mat('MI_Veg_DarkBark', 'T_Veg_DarkBark'), game_mat('MI_Veg_Shrub', 'T_Veg_Shrub', alpha=True, translucency=0.3)])
    ob['trunk_r'] = 0.05
    return ob
