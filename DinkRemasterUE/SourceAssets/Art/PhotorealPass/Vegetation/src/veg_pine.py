"""Pine generator v2: whorled conifer, drooping secondary twigs, small (<= 60 cm) needle sprays arranged in 3D around every branchlet,
dead interior, buttressed base that dives below the pivot. Variants: large, medium, storm-broken (fallen top beside it), dry, burnt."""
import numpy as np, math
from bl_tree import *

E = 3.0 / 2048
def tile(c, r): return (c * 0.5 + E, 1 - (r + 1) / 4 + E, (c + 1) * 0.5 - E, 1 - r / 4 - E)
T_DENSE = [tile(0, 0), tile(1, 0)]; T_NARROW = tile(0, 1); T_OPEN = tile(1, 1); T_OLD = tile(0, 2); T_YOUNG = tile(1, 2); T_HALF = tile(0, 3); T_BARE = tile(1, 3)
UPV = np.array([0, 0, 1.0])
SPRAY_STEP = 0.42; SPRAY_MAX = 0.6; HANG_P = 0.25; SIDE_P = 0.72; LET_GAP = (0.16, 0.25); TOP_STEP = 0.26      # v3: more and smaller spray cards, hanging secondary twigs, sprays lying along the bough

LOD = {0: dict(tr_sides=12, k=3, br_sides=4, br_ds=1.15, keep=1.0, scale=1.0, stub=1.0, min_r=0.0, twigs=True),
       1: dict(tr_sides=8, k=2, br_sides=4, br_ds=0.9, keep=0.5, scale=1.32, stub=0.5, min_r=0.0, twigs=False),
       2: dict(tr_sides=6, k=1, br_sides=3, br_ds=1.6, keep=0.14, scale=2.3, stub=0.0, min_r=0.0275, twigs=False)}

PINES = {
 'SM_Veg_Pine_Large_01': dict(gap=0.97, seed=101, H=16.5, hc=1.9, Rmax=4.1, r0=0.25, lean=(0.0, 0.0), wander=0.14, whorl0=0.66, nper=(5, 7)),
 'SM_Veg_Pine_Medium_01': dict(gap=0.8, seed=202, H=10.8, hc=1.2, Rmax=2.8, r0=0.165, lean=(0.02, -0.01), wander=0.09, whorl0=0.52, nper=(5, 7)),
 'SM_Veg_Pine_Storm_01': dict(gap=0.8, seed=303, H=16.0, hc=2.1, Rmax=3.8, r0=0.23, lean=(0.15, 0.05), wander=0.16, whorl0=0.66, nper=(5, 6),
                              top_break=0.7, bald_az=2.2, bald_w=1.3, dead_frac=0.12),
 'SM_Veg_Pine_Dry_01': dict(seed=404, H=14.5, hc=2.0, Rmax=3.5, r0=0.21, lean=(-0.03, 0.02), wander=0.13, whorl0=0.72, nper=(4, 6), dry=True, dead_frac=0.3),
 'SM_Veg_Pine_Burnt_01': dict(seed=505, H=13.5, hc=1.8, Rmax=3.2, r0=0.21, lean=(0.04, -0.03), wander=0.13, whorl0=0.8, nper=(3, 5), burnt=True, top_break=0.78),
}

def rot(v, axis, ang):
    axis = nrm(axis); return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))

def skeleton(P):
    rng = np.random.default_rng(P['seed'])
    H, hc, Rmax, r0 = P['H'], P['hc'], P['Rmax'], P['r0']
    tb = P.get('top_break'); Htop = H * tb if tb else H
    burnt = P.get('burnt', False); dry = P.get('dry', False); cs = P.get('card_scale', 1.0)
    zs = np.concatenate([np.linspace(0, 1.0, 40, endpoint=False), np.linspace(1.0, Htop, 110)])
    ph = rng.uniform(0, 6.28, 4); wd = P['wander']; lx, ly = P['lean']
    leanf = zs - 0.5 * zs ** 2 / H * 0.9          # lean straightens toward the top (a tree corrects itself)
    x = lx * leanf + wd * np.sin(zs * 0.45 + ph[0]) + 0.35 * wd * np.sin(zs * 1.3 + ph[1])
    y = ly * leanf + wd * np.sin(zs * 0.38 + ph[2]) + 0.35 * wd * np.sin(zs * 1.1 + ph[3])
    x -= x[0]; y -= y[0]
    tr = np.stack([x, y, zs], 1)
    rad = r0 * (1 - zs / (H * 1.02)) ** 0.85 + 0.012
    def at(z): return np.array([np.interp(z, zs, x), np.interp(z, zs, y), z])
    def rat(z): return float(np.interp(z, zs, rad))
    S = dict(trunk=tr, trad=rad, at=at, rat=rat, H=H, Htop=Htop, P=P, branches=[], cards=[], twigs=[],
             knots=[(rng.uniform(0.9, hc + 2.5), rng.uniform(0, 6.28), rng.uniform(0.10, 0.2)) for _ in range(5)])
    def add_card(cross=False, **k):
        u = rng.random(); k['key'] = 0.5 + 0.5 * u if cross else u
        if dry and rng.random() > 0.5: return
        if not burnt: S['cards'].append(k)
    def in_bald(az):
        if 'bald_az' not in P: return False
        d = (az - P['bald_az'] + math.pi) % (2 * math.pi) - math.pi
        return abs(d) < P['bald_w'] / 2
    def spray_axis(p, d, Lb, wind_, inner, twig):
        """a drooping branchlet: sprays in sequence along it, two crossed cards per position plus side sprays, all <= 60 cm"""
        npos = max(1, int(round(Lb / SPRAY_STEP))); q = np.array(p, float); dd = nrm(d); pts = [q.copy()]
        for j in range(npos):
            tip = j == npos - 1
            cl = min(SPRAY_MAX, Lb / npos * 1.3) * cs
            if tip: tl = T_YOUNG if rng.random() < 0.18 else T_DENSE[rng.integers(2)]
            else: tl = (T_HALF if rng.random() < 0.6 else T_BARE) if inner else (T_OPEN if rng.random() < 0.6 else T_OLD)
            w = nrm(np.cross(dd, UPV) + 1e-6); r0_ = rng.normal(0, 0.35)
            add_card(o=q - dd * 0.03, d=dd, w=rot(w, dd, r0_), L=cl, tile=tl, droop=rng.uniform(0.15, 0.4), wind=wind_, flip=rng.random() < 0.5, keep=tip)
            t2 = T_NARROW if tip else (T_OPEN if not inner else T_BARE)
            add_card(cross=True, o=q - dd * 0.03, d=dd, w=rot(w, dd, r0_ + rng.uniform(1.1, 2.0)), L=cl * rng.uniform(0.75, 0.95), tile=t2, droop=rng.uniform(0.15, 0.4), wind=wind_, flip=rng.random() < 0.5)
            for sd in (-1, 1):
                if rng.random() < (SIDE_P if not inner else 0.3):
                    ds_ = nrm(dd * 0.75 + w * sd * rng.uniform(0.5, 0.95) + UPV * rng.uniform(-0.55, 0.15))
                    ts = T_BARE if (inner and rng.random() < 0.5) else (T_YOUNG if rng.random() < 0.25 else T_DENSE[rng.integers(2)])
                    add_card(o=q + dd * cl * rng.uniform(0.15, 0.55), d=ds_, w=rot(nrm(np.cross(ds_, UPV) + 1e-6), ds_, rng.uniform(-1.2, 1.2)), L=rng.uniform(0.3, 0.5) * cs,
                             tile=ts, droop=rng.uniform(0.1, 0.45), wind=wind_, flip=rng.random() < 0.5)
            if not inner and rng.random() < HANG_P:          # a secondary twig hanging straight down from the branchlet
                dh = nrm(-UPV + dd * rng.uniform(0.0, 0.35) + w * rng.normal(0, 0.2))
                add_card(o=q + dd * cl * rng.uniform(0.2, 0.8), d=dh, w=rot(nrm(np.cross(dh, dd) + 1e-6), dh, rng.uniform(-1.5, 1.5)), L=rng.uniform(0.3, 0.5) * cs, tile=T_NARROW, droop=0.0, wind=wind_, flip=rng.random() < 0.5)
            dd = nrm(dd + np.array([0, 0, -0.25])); q = q + dd * cl * 0.8; pts.append(q.copy())
        if twig: S['twigs'].append(np.array(pts))
    # dead stubs under the crown
    z = 0.9
    while z < hc + 1.0:
        for _ in range(rng.integers(1, 3)):
            az = rng.uniform(0, 6.28); L = rng.uniform(0.1, 0.6) * (0.6 + 0.4 * z / hc)
            o = np.array([math.cos(az), math.sin(az), 0]); p0 = at(z) + o * rat(z) * 0.5
            pts = path(p0, o + [0, 0, rng.uniform(-0.35, 0.1)], L + rat(z) * 0.5, 5, rng, 0.45, lambda t, d, p: (0, 0, -0.3))
            rb = rng.uniform(0.011, 0.024)
            S['branches'].append(dict(pts=pts, r0=rb, r1=rb * 0.55, kind='stub', phase=rng.random(), key=rng.random()))
        z += rng.uniform(0.25, 0.5)
    # whorls
    z = hc; rot_ = rng.uniform(0, 6.28)
    while z < Htop - 0.25:
        f = (z - hc) / (H - hc)
        n = rng.integers(P['nper'][0], P['nper'][1] + 1)
        if f > 0.85: n = max(3, n - 1)
        rot_ += rng.uniform(0.5, 1.2)
        for i in range(n):
            if rng.random() < (0.10 if not burnt else 0.3): continue
            az = rot_ + 2 * math.pi * i / n + rng.normal(0, 0.22)
            R = Rmax * (1 - f) ** 0.72 + 0.28
            if f < 0.12: R *= 0.82 + 1.5 * f
            L = R * rng.uniform(0.78, 1.08)
            if tb and z > Htop - 1.6: L *= 1.2
            dead = rng.random() < P.get('dead_frac', 0.05) * (2.2 if f < 0.2 else 1.0)
            if in_bald(az) and rng.random() < 0.75:
                dead = True
                if rng.random() < 0.45: L *= rng.uniform(0.1, 0.3)
            if burnt: dead = True; L *= rng.uniform(0.2, 0.5) if rng.random() < 0.6 else rng.uniform(0.6, 1.0)
            e0 = math.radians(-6 + 58 * f ** 1.5 + rng.normal(0, 5))
            o = np.array([math.cos(az), math.sin(az), 0]); d0 = o * math.cos(e0) + np.array([0, 0, math.sin(e0)])
            g = 0.42 * min(1.3, L / 2.6) + 0.12; up = 1.1 if f < 0.8 else 0.5
            if dead and not burnt: L *= rng.uniform(0.45, 0.75); g *= 1.3; up = 0
            p0 = at(z + rng.normal(0, 0.05)) + o * rat(z) * 0.4
            pts = path(p0, d0, L, 10, rng, 0.16 if not burnt else 0.3, lambda t, d, p: (0, 0, -g * math.sin(math.pi * min(1, t * 1.15)) + up * max(0, t - 0.55) * 2.2))
            rb = 0.011 + 0.0095 * L * (1.0 if not burnt else 2.4) + (0.012 if burnt else 0)      # v4: live boughs 5-10 cm thick, not poles
            b = dict(pts=pts, r0=rb, r1=0.006 if not dead else rb * (0.4 if not burnt else 0.8), kind='dead' if dead else 'live', phase=rng.random(), key=rng.random())
            S['branches'].append(b)
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); LL = cum[-1]
            def pt(s):
                i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2)); t = (s - cum[i]) / seg[i]
                return pts[i] + (pts[i + 1] - pts[i]) * t, nrm(pts[i + 1] - pts[i])
            wind = lambda s: (pt(s)[0][2] / H, b['phase'], 0, s / LL)
            if dead:
                for s in np.arange(LL * 0.3, LL, 0.4):
                    if rng.random() < 0.65:
                        p, tg = pt(s); lat = nrm(np.cross(UPV, tg)) * rng.choice([-1, 1]); d = nrm(tg * 0.6 + lat + [0, 0, -0.4])
                        add_card(o=p, d=d, w=rot(nrm(np.cross(d, UPV)), d, rng.uniform(-1, 1)), L=rng.uniform(0.4, 0.6) * cs, tile=T_BARE, droop=0.3, wind=wind(s), flip=rng.random() < 0.5)
                continue
            low = f < 0.22
            s = max(0.3, 0.14 * LL) + rng.uniform(0, 0.15); k = 0
            while s < LL - 0.15:
                p, tg = pt(s); sd = 1 if k % 2 == 0 else -1; k += 1
                lat = nrm(np.cross(UPV, tg)) * sd; inner = s / LL < 0.3
                yaw = math.radians(rng.uniform(40, 70))
                d = nrm(tg * math.cos(yaw) + lat * math.sin(yaw) + UPV * rng.uniform(-0.6, -0.12))
                Lb = rng.uniform(0.45, 1.0) * (1.0 - 0.45 * s / LL) * (1.0 if LL > 1.3 else 0.7) * cs
                if inner and rng.random() < 0.5: s += rng.uniform(0.2, 0.3); continue      # the interior near the trunk is thin and dead
                spray_axis(p, d, Lb, wind(s), inner, low and Lb > 0.5)
                if rng.random() < 0.45 and not inner:   # a branchlet hanging straight down
                    rad_o = nrm(np.array([p[0] - at(p[2])[0], p[1] - at(p[2])[1], 0]) + 1e-6)
                    spray_axis(p, nrm(rad_o * rng.uniform(0.1, 0.4) + lat * 0.3 - UPV), rng.uniform(0.45, 0.8) * cs, wind(s), False, False)
                s += rng.uniform(*LET_GAP) * P.get('gap', 1.0)
            s = LL * 0.3 + rng.uniform(0, TOP_STEP)
            while s < LL - 0.2:
                p, tg = pt(s); lat = nrm(np.cross(UPV, tg)); yw = rng.normal(0, 0.45)
                d = nrm(tg * math.cos(yw) + lat * math.sin(yw) + UPV * rng.uniform(0.0, 0.3))
                add_card(o=p + UPV * rng.uniform(0.0, 0.05) - d * 0.12, d=d, w=rot(nrm(np.cross(d, UPV)), d, rng.normal(0, 0.35)), L=rng.uniform(0.45, 0.6) * cs, tile=(T_DENSE[rng.integers(2)] if s / LL > 0.45 else T_OPEN), droop=rng.uniform(0.1, 0.3), wind=wind(s), flip=rng.random() < 0.5)
                s += TOP_STEP * rng.uniform(0.7, 1.3)
            p, tg = pt(LL - 0.02)
            spray_axis(p - tg * 0.1, tg, 0.55 * cs, wind(LL), False, False)
        z += P['whorl0'] * (1 - 0.45 * f) * rng.uniform(0.85, 1.15)
    # leader
    top = at(Htop)
    if not tb:
        for i in range(4):
            az = i * 1.57 + rng.uniform(0, 0.6); o = np.array([math.cos(az), math.sin(az), 0])
            d = nrm(o * 0.45 + [0, 0, 1]); add_card(o=top - [0, 0, 0.4], d=d, w=np.cross(d, o), L=0.55 * cs, tile=T_YOUNG, droop=0.0, wind=(1, 0.5, 0, 0.3), flip=i % 2 == 0, keep=True)
    return S

def emit(P, C, lod, base=True):
    S = skeleton(P); mb = MeshB(); H = S['H']; at = S['at']; rat = S['rat']
    circ = 2 * math.pi * P['r0'] * 1.05; tile_len = circ; top = max(0.6, tile_len / 2) if base else 0.0
    if base: mb.root_base(at, rat, P['seed'], lod, top=top, strength=P.get('roots', 1.0))
    zs = S['trunk'][:, 2]; sel = zs > top + 1e-3
    t0 = top                          # the bole starts exactly on the base surface's top ring
    rj = rat(top) * (1 + 0.22 * math.exp(-top / 0.4)) if base else rat(0)
    lap = np.array([0, 0, 0.07 if base else 0.0])            # the bole starts 7 cm inside the base surface: no groove can open at the join
    tp0 = np.vstack([(at(t0) - lap)[None, :], at(t0)[None, :], S['trunk'][sel]]); tr0 = np.concatenate([[rj, rj], S['trad'][sel]])
    tp, trd = resample(tp0, tr0, tile_len / C['k']); zt = tp[:, 2]
    def radial(i, a):
        if i <= 1: return 1.0
        t = 0.02 * math.sin(4 * a + zt[i] * 0.9)
        for zk, ak, amp in S['knots']:      # old branch scars: low swellings on the bole
            d = (a - ak + math.pi) % (2 * math.pi) - math.pi; t += amp * math.exp(-((zt[i] - zk) / 0.2) ** 2 - (d / 0.5) ** 2)
        return 1 + t
    mb.tube(tp, trd, C['tr_sides'], 'body', 1, tile_len, wind=(top / H, 0, 0, 0), wind1=(S['Htop'] / H, 0, 0, 0), radial=radial, cap=True)
    if 'top_break' in P and lod < 2:  # splintered snapped top: long torn fibres, one side standing higher
        rng = np.random.default_rng(7); tpt = tp[-1]; rt = trd[-1]
        for i in range(12 if lod == 0 else 6):
            a = i * 0.55 + rng.uniform(0, 0.4); hi = 0.5 + 0.5 * math.cos(a - 1.0)
            o = np.array([math.cos(a), math.sin(a), 0]) * rt * rng.uniform(0.35, 0.85)
            pts = np.array([tpt + o - [0, 0, 0.3], tpt + o * 0.95 + [0, 0, 0.15 + 0.5 * hi * rng.uniform(0.6, 1.0)], tpt + o * rng.uniform(0.8, 1.2) + [0, 0, 0.25 + 1.1 * hi * rng.uniform(0.5, 1.0)]])
            mb.tube(pts, [rt * 0.4, rt * rng.uniform(0.12, 0.22), rt * 0.02], 3, 'limb', 1, 0.5, wind=(1, 0, 0, 0), cap=True)
    for b in S['branches']:
        if b['kind'] == 'stub' and b['key'] > C['stub']: continue
        if b['r0'] < C['min_r']: continue
        cp = chaikin(b['pts'], 1); cp[:, 2] = np.maximum(cp[:, 2], 0.06)
        pts, _ = resample(cp, np.zeros(len(cp)), C['br_ds'] if b['kind'] != 'stub' else max(0.2, C['br_ds'] * 0.6))
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]); t = s / s[-1]
        r = (b['r0'] * (1 - t) + b['r1'] * t) * (1 + 0.9 * np.exp(-s / 0.08))          # branch collar
        sides = C['br_sides'] if b['r0'] > 0.03 or lod > 0 else max(3, C['br_sides'] - 1)
        mb.tube(pts, r, sides, 'limb', 1, 0.6, wind=(pts[0][2] / H, b['phase'], 0, 0), wind1=(pts[-1][2] / H, b['phase'], 0, 1), cap=True)
    if C.get('twigs'):
        for tw in S['twigs']:
            tw = tw.copy(); tw[:, 2] = np.maximum(tw[:, 2], 0.04)
            if len(tw) >= 2: mb.tube(tw, np.linspace(0.009, 0.003, len(tw)), 3, 'limb', 1, 0.3, wind=(tw[0][2] / H, 0, 0, 0.6), cap=False)
    sc = C['scale']; v_cards = mb.nv()
    for c in S['cards']:
        if not (c['key'] < C['keep'] or (c.get('keep') and c['key'] < C['keep'] * 3.0)): continue
        Lc = c['L'] * sc
        ctr = at(max(0.5, min(S['Htop'], c['o'][2] - 1.0)))
        o2 = np.asarray(c['o']) - nrm(c['d']) * (Lc - c['L']) * 0.5       # grow LOD cards about their middle, not outward
        mb.card(o2, c['d'], c['w'], Lc, Lc * 0.5, c['tile'], 1, 1, c['droop'], 0, ctr, 0.8, c['wind'], 1, c['flip'])
    for i in range(v_cards, mb.nv()):          # the lowest boughs rest on the ground instead of passing through it
        if mb.v[i][2] < 0.03: mb.v[i] = np.array([mb.v[i][0], mb.v[i][1], 0.03])
    return mb

def merge(mb, m, Rm, off):
    base = mb.nv()
    mb.v += [Rm @ p + off for p in m.v]; mb.n += [Rm @ q for q in m.n]; mb.col += m.col
    mb.faces += [tuple(base + i for i in f) for f in m.faces]; mb.uv += m.uv; mb.mat += m.mat

def pine_mats(P=None):
    P = P or {}
    if P.get('burnt'): return [game_mat('MI_Veg_CharredBark', 'T_Veg_CharredBark', basemask=True)]
    if P.get('dry'): return [game_mat('MI_Veg_PineBarkDry', 'T_Veg_PineBarkDry', basemask=True), game_mat('MI_Veg_PineNeedlesDry', 'T_Veg_PineNeedlesDry', alpha=True, translucency=0.12)]
    return [game_mat('MI_Veg_PineBark', 'T_Veg_PineBark', basemask=True), game_mat('MI_Veg_PineNeedles', 'T_Veg_PineNeedles', alpha=True, translucency=0.3)]

# forest-edge modules: a staggered strip of pines plus saplings; H = along X (sprite 32/08), V = along Y (sprites 32/09, 32/10)
ELOD = {0: dict(tr_sides=8, k=2, br_sides=3, br_ds=1.3, keep=0.36, scale=1.5, stub=0.4, min_r=0.0215, twigs=False),
        1: dict(tr_sides=6, k=1, br_sides=3, br_ds=1.8, keep=0.13, scale=2.3, stub=0.0, min_r=0.0275, twigs=False),
        2: dict(tr_sides=4, k=1, br_sides=3, br_ds=2.5, keep=0.045, scale=3.6, stub=0.0, min_r=0.2, twigs=False)}
def _edge(seed, n, length, depth, along, hr=(10.5, 15.5), whorl0=0.66, nper=(4, 6)):
    rng = np.random.default_rng(seed); out = []
    for i in range(n):
        t = (i + 0.5) / n * length - length / 2 + rng.normal(0, length / n * 0.12); q = rng.uniform(-0.3, 0.3) * depth + (0.18 * depth if i % 2 else -0.18 * depth)
        H = rng.uniform(*hr)
        P = dict(seed=seed * 10 + i, H=H, hc=rng.uniform(0.9, 1.8), Rmax=H * 0.2, r0=0.015 * H, lean=(rng.normal(0, 0.02), rng.normal(0, 0.02)), wander=0.11, whorl0=whorl0, nper=nper, dead_frac=0.08, roots=0.7)
        out.append((P, (t, q) if along == 'x' else (q, t), rng.uniform(0, 6.28)))
    for i in range(n):   # understory saplings
        t = rng.uniform(-0.5, 0.5) * length; q = rng.uniform(-0.5, 0.5) * depth; H = rng.uniform(1.4, 3.2)
        P = dict(seed=seed * 10 + 50 + i, H=H, hc=0.25, Rmax=H * 0.3, r0=0.02 * H, lean=(rng.normal(0, 0.04), rng.normal(0, 0.04)), wander=0.04, whorl0=0.34, nper=(3, 5), card_scale=0.6, sapling=True)
        out.append((P, (t, q) if along == 'x' else (q, t), rng.uniform(0, 6.28)))
    return out
EDGES = {'SM_Veg_PineForestEdge_H_01': _edge(5, 4, 7.6, 1.6, 'x', (7.0, 10.0), 0.46, (5, 7)), 'SM_Veg_PineForestEdge_V_01': _edge(8, 5, 11.5, 1.6, 'y', (10.0, 14.0))}

EDGE0 = {'SM_Veg_PineForestEdge_H_01': dict(keep=0.6, scale=1.15), 'SM_Veg_PineForestEdge_V_01': dict(keep=0.5, scale=1.25)}
def build(name, lod):
    P = PINES.get(name)
    if P:
        C0 = dict(LOD[lod])
        if lod == 0 and (P.get('burnt') or P.get('dry')): C0.update(tr_sides=14, k=4, br_sides=4)      # leafless / thin trees keep the rounder wood
        mb = emit(P, C0, lod)
        if name == 'SM_Veg_Pine_Storm_01':   # the snapped-off top lies beside the tree, butt toward the trunk
            Pt = dict(seed=909, H=5.2, hc=0.9, Rmax=1.9, r0=0.085, lean=(0, 0), wander=0.03, whorl0=0.5, nper=(4, 6), dead_frac=0.25)
            Ct = dict(LOD[lod]); Ct.update(keep=LOD[lod]['keep'] * 0.8, tr_sides=(8, 6, 4)[lod], stub=0)
            m = emit(Pt, Ct, lod, base=False)
            # lay it down: trunk axis z -> horizontal, then yaw; squash what would go underground
            Ry = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float); yaw = 2.5; c, s_ = math.cos(yaw), math.sin(yaw)
            Rm = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]]) @ Ry
            base = mb.nv(); merge(mb, m, Rm, np.array([-1.6, 1.3, 0.22]))
            for i in range(base, mb.nv()):
                if mb.v[i][2] < 0.03: mb.v[i] = np.array([mb.v[i][0], mb.v[i][1], 0.03 + 0.25 * max(-0.4, mb.v[i][2] - 0.03) * 0.2])
    else:
        mb = MeshB(); mb.keep_z = True
        for Pe, (x, y), yaw in EDGES[name]:
            C = dict(ELOD[lod])
            if lod == 0: C.update(EDGE0[name])          # v4: more and smaller sprays at LOD0 (big scaled cards read as broad leaves)
            if Pe.get('sapling'):
                if lod == 2: continue
                C.update(keep=(0.8, 0.3)[lod], scale=(1.1, 1.9)[lod], min_r=0.5, stub=0)
            m = emit(Pe, C, max(lod, 1), base=not Pe.get('sapling')); c, s_ = math.cos(yaw), math.sin(yaw)
            merge(mb, m, np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]]), np.array([x, y, 0]))
    recenter(mb, xy=name not in PINES)
    print('CARDS', sum(1 for m in mb.mat if m == 1), 'woodtris', sum(len(f) - 2 for f, m in zip(mb.faces, mb.mat) if m == 0))
    ob = mb.build(f'{name}_LOD{lod}', pine_mats(P)); ob['trunk_r'] = P['r0'] if P else 0.2
    return ob
