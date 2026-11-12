"""Photoreal props: barrel, crates, storage jars and bowl, grain sacks, tables, chair, bench, stool, bed, chest, gravestones,
candle. Same builder (Structures/tools/kitlib.py Mod2), tiling scan sets and vertex-colour weathering contract as the structure
kits, so the Unreal integrator needs no new material graph.
    DINK_PP=<PhotorealPass> blender -b -t 4 --python props_build.py [-- name-filter ...]     -> Props/_build/"""
import os, sys
_T = os.path.join(os.environ['DINK_PP'], 'Structures', 'tools', 'stonebrook_build.py')
__file__ = _T
_s = open(_T).read()
exec(_s[:_s.index('\ndef sb_modules(rows):')])
PROPS = os.path.join(os.environ['DINK_PP'], 'Props')
OUT = os.path.join(PROPS, '_build')
os.makedirs(OUT, exist_ok=True)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
_set_info0 = set_info


def set_info(setname):
    p = os.path.join(PROPS, 'Sets', setname, 'set.json')
    if os.path.exists(p):
        return os.path.join(PROPS, 'Sets'), json.load(open(p))
    return _set_info0(setname)


TAG_CLOTH, TAG_CERAMIC, TAG_WAX, TAG_TOP, TAG_ASH2, TAG_METAL = 56, 57, 58, 59, 60, 61
T_IRON = 1.0
T_HESS, T_LINEN, T_GLAZE, T_PL = 0.3, 0.4, 0.5, 2.5


def RX(c, ang):
    return np.array(Matrix.Translation(c) @ Matrix.Rotation(ang, 4, 'X') @ Matrix.Translation([-c[0], -c[1], -c[2]]))


def RYm(c, ang):
    return np.array(Matrix.Translation(c) @ Matrix.Rotation(ang, 4, 'Y') @ Matrix.Translation([-c[0], -c[1], -c[2]]))


def RZ(c, ang):
    return np.array(Matrix.Translation(c) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Translation([-c[0], -c[1], -c[2]]))


def brd(m):
    return m.timber_rows[m.rng.integers(len(m.timber_rows))]


def board(m, lo, hi, bevel=0.005, jitter=0.001, tag=TAG_TIMBER, slot=1):
    m.block(lo, hi, slot, T_TIMBER, bevel, jitter, mode='board', board=brd(m), tag=tag)


def nail(m, p, axis, r=0.006, slot=1, l=0.006):
    p = np.array(p, float); d = np.zeros(3); d[abs(axis) - 1] = 1.0 if axis > 0 else -1.0
    m.tube([p - d * 0.004, p + d * l], [r, r * 0.6], slot, sides=6, tag=TAG_IRON, smooth=True)


def whip(m, c, r_loop, turns=4.0, rad=0.008, slot=2, rise=0.05, sq=1.0):
    n = int(turns * 10); pts = []
    for i in range(n + 1):
        a = 2 * math.pi * turns * i / n
        pts.append([c[0] + r_loop * math.cos(a), c[1] + r_loop * sq * math.sin(a), c[2] - rise / 2 + rise * i / n + 0.003 * math.sin(a * 3)])
    m.tube(pts, rad, slot, sides=6, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))


def lathe(m, prof, slot, tile, n=24, tag=TAG_CERAMIC, wob=0.0, sx=1.0, deform=None, c=(0.0, 0.0), smooth=True, vscale=1.0, maxseg=None):
    """closed solid of revolution about Z. prof: (r, z) points from the bottom pole (r = 0) outward and up and back to a pole.
    wob: hand-made out-of-round; deform(P) -> P for sacks and drips. UV: u round, v along the profile."""
    r_ = m.rng; prof = [(float(a), float(b)) for a, b in prof]
    if maxseg:
        q = [prof[0]]
        for a_, b_ in prof[1:]:
            k_ = max(1, int(math.ceil(math.hypot(a_ - q[-1][0], b_ - q[-1][1]) / maxseg))); a0_, b0_ = q[-1]
            q += [(a0_ + (a_ - a0_) * i / k_, b0_ + (b_ - b0_) * i / k_) for i in range(1, k_ + 1)]
        prof = q
    ph = r_.uniform(0, 6.28, 3); V = []; idx = []; arc = [0.0]
    for i in range(1, len(prof)):
        arc.append(arc[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
    rmax = max(p[0] for p in prof)
    for i, (rr, z) in enumerate(prof):
        if rr <= 1e-9:
            idx.append([len(V)] * n); V.append([c[0], c[1], z])
        else:
            row = []
            for k in range(n):
                a = 2 * math.pi * k / n
                q = rr * (1 + wob * (math.sin(2 * a + ph[0]) + 0.5 * math.sin(3 * a + ph[1] + z * 9) + 0.4 * math.sin(a + ph[2] + z * 5)))
                row.append(len(V)); V.append([c[0] + q * math.cos(a) * sx, c[1] + q * math.sin(a), z])
            idx.append(row)
    V = np.array(V, float)
    if deform is not None:
        V = deform(V)
    F = []; UV = []; uo = r_.uniform(0, 1, 2); per = 2 * math.pi * rmax * (1 + sx) / 2
    for i in range(len(prof) - 1):
        p0, p1 = prof[i][0] <= 1e-9, prof[i + 1][0] <= 1e-9
        if p0 and p1:
            continue
        for k in range(n):
            k2 = (k + 1) % n
            ua, ub = k / n * per / tile + uo[0], (k + 1) / n * per / tile + uo[0]; va, vb = arc[i] * vscale / tile + uo[1], arc[i + 1] * vscale / tile + uo[1]
            if p0:
                F.append([idx[i][k], idx[i + 1][k2], idx[i + 1][k]]); UV.append([((ua + ub) / 2, va), (ub, vb), (ua, vb)])
            elif p1:
                F.append([idx[i][k], idx[i][k2], idx[i + 1][k]]); UV.append([(ua, va), (ub, va), ((ua + ub) / 2, vb)])
            else:
                F.append([idx[i][k], idx[i][k2], idx[i + 1][k2], idx[i + 1][k]]); UV.append([(ua, va), (ub, va), (ub, vb), (ua, vb)])
    # orientation: signed volume must be positive
    vol = 0.0
    for f in F:
        a_, b_, c_ = V[f[0]], V[f[1]], V[f[2]]; vol += np.dot(a_, np.cross(b_, c_))
        if len(f) == 4:
            vol += np.dot(a_, np.cross(V[f[2]], V[f[3]]))
    if vol < 0:
        F = [f[::-1] for f in F]; UV = [u[::-1] for u in UV]
    m.add_uv(V, F, UV, slot, tag, smooth)


def prop_paint(m, kind):
    seed = int(m.rng.integers(1e6))

    def f(P, tags, N, col):
        z = P[:, 2]; n = vnoise(P, seed, 2.6); n2 = vnoise(P, seed + 3, 11.0); n3 = vnoise(P, seed + 9, 1.1)
        R = np.zeros(len(P)); G = np.zeros(len(P)); B = np.zeros(len(P)); A = np.ones(len(P))
        up = np.clip(N[:, 2], 0, 1); under = N[:, 2] < -0.3; H = max(float(z.max()), 0.05)
        foot = np.clip((0.07 * (1 + 0.5 * n) - z) / 0.07, 0, 1)
        spots = np.zeros(len(P)); rub = np.zeros(len(P))
        for (c_, rad, k) in getattr(m, 'stains', ()):           # greasy or wet patches, rings from standing pots
            d = np.linalg.norm(P - np.array(c_), axis=1) / rad
            spots = np.maximum(spots, k * np.clip(1.25 - d * (1 + 0.3 * n2), 0, 1))
        for (c_, rad, k) in getattr(m, 'rubs', ()):             # polished or scrubbed pale by use
            d = np.linalg.norm(P - np.array(c_), axis=1) / rad
            rub = np.maximum(rub, k * np.clip(1.2 - d, 0, 1))
        part = np.array(list(getattr(m, 'part', [])) + [0] * len(P))[:len(P)]
        rq = np.random.default_rng(seed + 77).uniform(-0.5, 0.5, (int(part.max()) + 1, 2)); rp, rp2 = rq[part, 0], rq[part, 1]          # every board, stave and stone its own tone
        low = np.clip((0.22 * (1 + 0.6 * n3) - z) / 0.22, 0, 1)
        for (zb_, wd_) in getattr(m, 'bands', ()):               # damp and rust runs under hoops
            spots = np.maximum(spots, 0.55 * np.clip(1 - np.abs(z - (zb_ - wd_)) / wd_, 0, 1) * np.clip(0.5 + n2 + n, 0, 1))
        tim = (tags == TAG_TIMBER) | (tags == TAG_END) | (tags == TAG_TOP)
        dk = np.clip(0.22 + 0.22 * n + 0.2 * n2 + 0.3 * rp + 0.75 * foot + 0.3 * low + 0.4 * under + spots + 0.2 * np.clip(n3, 0, 1), 0, 1)
        wr = np.clip(0.06 + 0.15 * n3 + 0.1 * n2 + 0.2 * rp2 + 0.15 * up * (0.5 + n) + rub - 0.6 * foot, 0, 1)
        wr = np.where(tags == TAG_TOP, np.clip(wr + 0.1 + 0.2 * n3, 0, 1), wr)        # table and seat tops: scrubbed and worn
        mt = tags == TAG_METAL; mb = getattr(m, 'metal_b', 0.3)
        R = np.where(mt, np.clip(0.3 + 0.45 * n2 + 0.3 * n + 0.4 * rp + 0.6 * foot + 0.3 * under, 0, 1), R); B = np.where(mt, np.clip(mb + 0.3 * n3 + 0.25 * n2 + 0.3 * rp2 + rub, 0, 1), B)
        R = np.where(tim, dk, R); B = np.where(tim, wr, B)
        if kind == 'outdoor':
            G = np.where(tim, np.clip(0.7 * foot * (0.5 + n) + 0.3 * up * np.clip(n3, 0, 1), 0, 1), G)
        cl = tags == TAG_CLOTH
        R = np.where(cl, np.clip(0.18 + 0.3 * n3 + 0.2 * n + 0.2 * rp + 0.3 * low + 0.8 * foot + 0.45 * under + 0.25 * (np.abs(N[:, 2]) < 0.25) + spots, 0, 1), R)
        B = np.where(cl, np.clip(getattr(m, 'cloth_b', 0.15) + 0.3 * up * np.clip(n3 + 0.2, 0, 1) + 0.15 * n + rub, 0, 1), B)
        ce = tags == TAG_CERAMIC
        rad = np.hypot(P[:, 0] - getattr(m, 'axis', (0, 0))[0], P[:, 1] - getattr(m, 'axis', (0, 0))[1])
        inward = ((P[:, 0] - getattr(m, 'axis', (0, 0))[0]) * N[:, 0] + (P[:, 1] - getattr(m, 'axis', (0, 0))[1]) * N[:, 1]) < -0.25 * np.maximum(rad, 1e-3)
        R = np.where(ce, np.clip(0.1 + 0.2 * n3 + 0.2 * np.clip(n2, 0, 1) + 0.9 * foot + 0.9 * (inward & (z > 0.25 * H)) + 0.35 * under + spots, 0, 1), R)
        B = np.where(ce, np.clip(0.25 * np.clip(n3 + n - 0.6, 0, 1) + 0.7 * np.clip(1 - (H - z) / 0.02, 0, 1) * (0.5 + n2) + rub + 0.9 * (z < 0.012), 0, 1), B)
        if kind == 'pie':                                # crust: browned on the crown and the crimps, pale in the hollows; the cut shows dark filling
            cr = tags == TAG_WAX; rad_ = np.hypot(P[:, 0], P[:, 1]); cut = np.zeros(len(P), bool)
            R = np.where(cr, np.clip(0.25 + 0.5 * np.clip(n2 + 0.3 * n, 0, 1) + 0.45 * (rad_ > 0.2) + 0.5 * np.clip((z - 0.1) / 0.02, 0, 1) + 1.0 * cut, 0, 1), R)
            B = np.where(cr, np.clip(0.35 - 0.5 * n2 - 0.4 * cut, 0, 1), B)
            tags = np.where(cr, -1, tags)
        wx = tags == TAG_WAX
        R = np.where(wx, np.clip(0.1 + 0.25 * n2 + 0.3 * np.clip((0.5 * H - z) / (0.5 * H), 0, 1) + 0.6 * np.clip(1 - (H - z) / 0.025, 0, 1), 0, 1), R); B = np.where(wx, 0.3 + 0.2 * n, B)
        st = (tags == TAG_SHEET) | (tags == TAG_STONE)
        if st.any():
            north = np.clip(N[:, 1], 0, 1)
            Rs = np.clip(0.25 + 0.3 * n + 0.2 * n2 + 0.8 * np.clip((0.3 * (1 + 0.5 * n3) - z) / 0.3, 0, 1) + 0.35 * streaks(P, seed + 5, 9.0, 0) * np.clip(z / H, 0, 1) + spots, 0, 1)
            Gs = np.clip(0.9 * np.clip((0.3 * (1 + n3) - z) / 0.25, 0, 1) + 0.8 * up * np.clip(n3 + 0.6 * n + 0.1, 0, 1) + 0.75 * north * (0.45 + n3) + 0.45 * np.clip(n3 + n - 0.25, 0, 1), 0, 1)
            Bs = np.clip(0.2 + 0.3 * n + 0.7 * np.clip(n2 * 0.6 + n3 - 0.35, 0, 1) + rub, 0, 1)
            if kind == 'indoor_stone':
                Gs = Gs * 0.0
            if kind == 'dungeon':                       # damp, not green: a little algae low down only
                Gs = Gs * 0.3 * (z < 0.5); Rs = np.clip(Rs + 0.15, 0, 1)
            R = np.where(st, Rs, R); G = np.where(st, Gs, G); B = np.where(st, Bs, B)
        if kind == 'hearth':                             # smoke: the fireback, the throat, a tongue up the breast over the opening
            fx, fy, fz, fw = m.fire
            inside = (np.abs(P[:, 0]) < fw + 0.05) & (z < fz + 0.35)
            tongue = np.clip(1.25 - np.abs(P[:, 0]) / (fw * 1.1), 0, 1) * np.clip(1 - (z - fz) / 2.3, 0, 1) ** 0.7 * (z >= fz - 0.1)
            soot = np.clip(1.3 * inside * np.clip(z / 0.5, 0.5, 1) + 1.5 * tongue * (0.75 + 0.4 * n) + 0.15 * n3, 0, 1)
            A = np.where(st, np.clip(1 - soot, 0, 1), A); G = np.where(st, 0.0, G); R = np.where(st, np.clip(R + 0.85 * soot, 0, 1), R)
            R = np.where(tim, np.clip(dk + 0.5 * np.clip(1 - np.abs(P[:, 0]) / (fw * 1.3), 0, 1) * (N[:, 2] < 0.3), 0, 1), R)
        if kind == 'torch':                              # everything near the fire is scaled and sooted: little bright wear, heavy rust
            sc_ = getattr(m, 'soot_c', None)
            if sc_ is not None:
                d_ = np.clip(0.55 + 0.6 * (z - 0.42) / 0.5 + 0.2 * n2, 0, 1) * (z > 0.4)          # the whole smoke plate, blacker toward the top
                col_s = d_
            R = np.where(mt, np.clip(R + 0.25, 0, 1), R); B = np.where(mt, B * 0.5, B)
            if sc_ is not None:                              # soot last: black over rust and wear alike
                R = np.where(mt, R * (1 - np.clip(1.6 * col_s, 0, 1)), R); B = np.where(mt, B * (1 - np.clip(1.6 * col_s, 0, 1)), B)
        ash = tags == TAG_ASH2
        R = np.where(ash, 0.2 + 0.3 * n2, R); B = np.where(ash, np.clip(0.9 + 0.3 * n, 0, 1), B); A = np.where(ash, np.clip(0.8 + 0.5 * n2 + 0.3 * n, 0, 1), A); G = np.where(ash, 0.0, G)
        A = np.where(tags == TAG_CHAR, 0.5, A); R = np.where(tags == TAG_CHAR, 1.0, R)
        bn = tags == TAG_BONE2
        R = np.where(bn, np.clip(0.5 + 0.4 * n2 + 0.35 * n + 0.3 * n3 + 0.3 * rp + 0.7 * np.clip((0.03 - z) / 0.03, 0, 1) + 0.3 * under, 0, 1), R); G = np.where(bn, np.clip(0.75 * np.clip(n3 + n + 0.5 * n2 - 0.3, 0, 1) + 0.6 * np.clip((0.02 - z) / 0.02, 0, 1), 0, 1) * (kind == 'outdoor'), G); B = np.where(bn, np.clip(0.2 + 0.3 * up * np.clip(n3 + 0.5, 0, 1), 0, 1), B)
        ea = (tags >= TAG_EARTH) & (tags <= TAG_EARTH + 2)
        qm = np.ones(len(P))
        for (cx_, cy_, rx_, ry_) in getattr(m, 'mounds', ()):       # turf creeping up the mound from its rim; the crown still bare, sunken earth
            qm = np.minimum(qm, np.hypot((P[:, 0] - cx_) / rx_, (P[:, 1] - cy_) / ry_))
        R = np.where(ea, np.clip(0.45 + 0.3 * n + 0.2 * n2, 0, 1), R); G = np.where(ea, (0.0 if kind == 'dungeon' else 1.0) * np.clip(0.55 + 1.1 * qm ** 2 - 0.5 * (tags == TAG_EARTH + 2) * np.clip(1 - qm / 0.6, 0, 1) + 0.35 * n + 0.3 * n2, 0, 1), G); B = np.where(ea, 0.25, B)
        rope = tags == TAG_ROPE
        R = np.where(rope, np.clip(0.7 + 0.2 * n2, 0, 1), R); G = np.where(rope, 0.0, G); B = np.where(rope, np.clip(0.3 + 0.2 * n, 0, 1), B)
        A = np.where(tags == TAG_IRON, 0.5, A); A = np.where(tags == TAG_LEAD, 0.75, A); A = np.where(tags == TAG_GLASS, 0.0, A)
        blk = tags == TAG_GLASS + 30
        A = np.where(blk, 0.5, A); R = np.where(blk, 1.0, R)
        return np.stack([R, G, B, A], -1)
    return f


# ---------------------------------------------------------------- barrel
def barrel(m, H=1.0, re=0.335, rm=0.42, ns=20):
    r = m.rng; th = 0.028; nz = 9
    rad = lambda z: re + (rm - re) * max(0.0, 1 - (2 * z / H - 1) ** 2) ** 0.85
    for k in range(ns):
        a0 = 2 * math.pi * k / ns + 0.004; a1 = 2 * math.pi * (k + 1) / ns - 0.004
        dr = r.normal(0, 0.0016); zt = H - abs(r.normal(0, 0.003)); zb0 = abs(r.normal(0, 0.002))
        top = np.zeros((nz, 3, 3)); und = np.zeros_like(top)
        for j in range(nz):
            z = zb0 + (zt - zb0) * j / (nz - 1)
            for c_ in range(3):
                a = a0 + (a1 - a0) * c_ / 2; q = rad(z) + dr + (0.0015 if c_ == 1 else 0.0)
                top[j, c_] = [q * math.cos(a), q * math.sin(a), z]; und[j, c_] = [(q - th) * math.cos(a), (q - th) * math.sin(a), z]
        v0, w = brd(m); uo = r.uniform(0, 1)

        def uvw(P, v0=v0, w=w, uo=uo):
            idx = np.arange(len(P)); c_ = idx % 3
            return np.stack([P[:, 2] / T_TIMBER + uo, v0 + (c_ / 2.0 - 0.5) * w * 0.8], -1)
        am = (a0 + a1) / 2
        m.hgrid(top, und, 1, T_TIMBER, tag=TAG_TIMBER, up=(math.cos(am), math.sin(am), 0), uvfn=uvw, smooth=True, grid_under=True)
    for (zh, top_) in ((0.035, False), (H - 0.06, True)):        # heads: four boards each, cut to the round, set in the croze
        rh = rad(zh) - th + 0.006; ys = [-rh, -rh * 0.45, rh * 0.05, rh * 0.55, rh]
        for a_, b_ in zip(ys[:-1], ys[1:]):
            n0 = len(m.V)
            m.beam([-rh, a_ + 0.001, zh], [rh, b_ - 0.001, zh + 0.024], 0.003, 0.0, 6, 0.0006)
            V = np.array(m.V); W_ = V[n0:]; xc = np.sqrt(np.maximum(rh * rh - W_[:, 1] ** 2, 1e-6)); W_[:, 0] = np.clip(W_[:, 0], -xc, xc); V[n0:] = W_; m.V = V.tolist()
            if top_:
                m.VT[n0:] = [TAG_TOP] * (len(m.V) - n0)
    for (zc, wd) in ((0.075, 0.052), (0.25, 0.042), (H - 0.25, 0.042), (H - 0.075, 0.052)):      # hoops, driven on: each sits on the taper
        za, zb_ = zc - wd / 2, zc + wd / 2; sag = r.normal(0, 0.004)
        n0 = len(m.V)
        ring(m, rad(za) + 0.0005, rad(za) + 0.0055, za, zb_, 40, 3, T_IRON, tag=TAG_METAL, r0b=rad(zb_) + 0.0005, r1b=rad(zb_) + 0.0055)
        m.xform_since(n0, RX([0, 0, zc], sag) @ RYm([0, 0, zc], float(r.normal(0, 0.004))))
        a = r.uniform(0, 6.28); q = rad(zc) + 0.006
        for da in (-0.03, 0.03):                                # the riveted lap
            m.tube([[(q - 0.004) * math.cos(a + da), (q - 0.004) * math.sin(a + da), zc], [(q + 0.004) * math.cos(a + da), (q + 0.004) * math.sin(a + da), zc]], [0.007, 0.005], 3, sides=6, tag=TAG_METAL, smooth=True)
    m.bands = [(0.05, 0.05), (0.23, 0.06), (H - 0.27, 0.07), (H - 0.1, 0.05)]; m.metal_b = 0.4
    a = 0.6; q = rad(H / 2)
    m.tube([[(q - 0.02) * math.cos(a), (q - 0.02) * math.sin(a), H / 2], [(q + 0.022) * math.cos(a), (q + 0.022) * math.sin(a), H / 2]], [0.03, 0.024], 1, sides=8, tag=TAG_END, smooth=True)   # bung
    m.stains = [([0.1, -0.05, H - 0.04], 0.16, 0.5), ([q * math.cos(a), q * math.sin(a), H / 2 - 0.12], 0.14, 0.7)]
    m.rubs = [([0, 0, H], 0.3, 0.25)]
    m.hulls = [[[rm * math.cos(t), rm * math.sin(t), z] for t in np.linspace(0, 2 * math.pi, 9)[:-1] for z in (0.0, H)]]


# ---------------------------------------------------------------- crate
def crate(m, L=0.9, W=0.62, H=0.55, slats=3):
    r = m.rng; t = 0.018; hx, hy = L / 2, W / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            timber(m, [sx * hx - (0.05 if sx > 0 else 0) + (0.0 if sx > 0 else 0.0) - (0.0 if sx > 0 else 0.0) + (0 if sx > 0 else 0.0), sy * hy - (0.05 if sy > 0 else 0.0), 0.0],
                   [sx * hx + (0.0 if sx > 0 else 0.05), sy * hy + (0.0 if sy > 0 else 0.05), H - t], 0.006, 0.002)
    sh = (H - t - 0.02 - (slats - 1) * 0.028) / slats
    for k in range(slats):
        z0 = 0.02 + k * (sh + 0.028)
        for sy in (-1, 1):
            n0 = len(m.V); y0 = sy * hy + (0.0 if sy > 0 else -t)
            board(m, [-hx - 0.004 + r.normal(0, 0.003), y0, z0 + r.normal(0, 0.003)], [hx + 0.004 + r.normal(0, 0.003), y0 + t, z0 + sh + r.normal(0, 0.003)], 0.004, 0.0012)
            m.xform_since(n0, RYm([0, y0, z0 + sh / 2], float(r.normal(0, 0.006))))
            for sx in (-1, 1):
                for dz in (0.3, 0.7):
                    nail(m, [sx * (hx - 0.025), y0 + (t if sy > 0 else 0.0), z0 + sh * dz + r.normal(0, 0.004)], 2 * sy, 0.005)
        for sx in (-1, 1):
            n0 = len(m.V); x0 = sx * hx + (0.0 if sx > 0 else -t)
            board(m, [x0, -hy - 0.002 + t * 0, z0 + r.normal(0, 0.003)], [x0 + t, hy + 0.002, z0 + sh + r.normal(0, 0.003)], 0.004, 0.0012)
            m.xform_since(n0, RX([x0, 0, z0 + sh / 2], float(r.normal(0, 0.006))))
            for sy in (-1, 1):
                for dz in (0.3, 0.7):
                    nail(m, [x0 + (t if sx > 0 else 0.0), sy * (hy - 0.025), z0 + sh * dz + r.normal(0, 0.004)], 1 * sx, 0.005)
    nb = 4; bw = (W + 2 * t) / nb                                # lid boards along the length, two battens across on top
    for k in range(nb):
        y0 = -hy - t + k * bw
        n0 = len(m.V)
        board(m, [-hx - t - 0.008 + r.normal(0, 0.004), y0 + 0.002, H - t], [hx + t + 0.008 + r.normal(0, 0.004), y0 + bw - 0.002, H + r.normal(0, 0.0015)], 0.004, 0.0012, tag=TAG_TOP)
        m.xform_since(n0, RZ([0, y0 + bw / 2, H], float(r.normal(0, 0.004))))
    for sx in (-1, 1):
        x0 = sx * (hx - 0.11)
        board(m, [x0 - 0.035, -hy - t + 0.01, H], [x0 + 0.035, hy + t - 0.01, H + 0.02], 0.005, 0.0012, tag=TAG_TOP)
        for k in range(nb):
            nail(m, [x0 + r.normal(0, 0.008), -hy - t + (k + 0.5) * bw, H + 0.02], 3, 0.0055)
    m.block([-hx + 0.003, -hy + 0.003, 0.004], [hx - 0.003, hy - 0.003, H - t - 0.002], 1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)     # the dark inside behind the gaps
    m.stains = [([hx * 0.3, -hy, 0.15], 0.25, 0.4), ([-hx * 0.4, 0.05, H], 0.2, 0.35)]
    m.rubs = [([hx, -hy, H], 0.12, 0.5), ([-hx, hy, H], 0.12, 0.5), ([hx, hy, H], 0.1, 0.4), ([-hx, -hy, H], 0.1, 0.4)]
    m.ucx = [([-hx - t, -hy - t, 0], [hx + t, hy + t, H + 0.02])]


# ---------------------------------------------------------------- storage jars and bowl
JARS = {
 'Storage': dict(prof=[(0, 0.0), (0.09, 0.0), (0.105, 0.006), (0.115, 0.03), (0.17, 0.12), (0.235, 0.25), (0.255, 0.36), (0.235, 0.47), (0.17, 0.555), (0.115, 0.6), (0.1, 0.635), (0.105, 0.675), (0.132, 0.71), (0.14, 0.725), (0.132, 0.738),
                       (0.115, 0.735), (0.09, 0.7), (0.082, 0.64), (0.09, 0.58), (0, 0.56)], slot='glaze_brown', handles=0),
 'Jug': dict(prof=[(0, 0.0), (0.1, 0.0), (0.118, 0.008), (0.14, 0.05), (0.215, 0.15), (0.245, 0.26), (0.225, 0.36), (0.16, 0.44), (0.125, 0.475), (0.12, 0.52), (0.145, 0.555), (0.155, 0.568), (0.147, 0.58), (0.13, 0.575),
                   (0.105, 0.535), (0.105, 0.48), (0.12, 0.44), (0, 0.42)], slot='glaze_blue', handles=2),
 'Vase': dict(prof=[(0, 0.0), (0.06, 0.0), (0.07, 0.006), (0.072, 0.03), (0.095, 0.12), (0.125, 0.24), (0.12, 0.33), (0.085, 0.42), (0.052, 0.5), (0.042, 0.57), (0.05, 0.63), (0.068, 0.665), (0.072, 0.675), (0.066, 0.684), (0.055, 0.68),
                    (0.036, 0.63), (0.032, 0.56), (0.04, 0.5), (0, 0.48)], slot='glaze_red', handles=0),
 'Bowl': dict(prof=[(0, 0.0), (0.075, 0.0), (0.088, 0.005), (0.09, 0.02), (0.13, 0.05), (0.185, 0.105), (0.208, 0.15), (0.212, 0.16), (0.205, 0.166), (0.195, 0.158), (0.165, 0.11), (0.11, 0.065), (0.05, 0.045), (0, 0.042)], slot='glaze_brown', handles=0)}


def jar(m, kind):
    J = JARS[kind]; r = m.rng
    prof = []
    for i, (a, b) in enumerate(J['prof']):                       # refine the profile so the vertex colours have something to hold on to
        prof.append((a, b))
        if i + 1 < len(J['prof']):
            a2, b2 = J['prof'][i + 1]
            if math.hypot(a2 - a, b2 - b) > 0.07:
                prof.append(((a + a2) / 2 * 1.012, (b + b2) / 2))
    H = max(p[1] for p in prof)

    def lean(P):                                                # thrown a little off true, sagged in the drying
        P = P.copy(); t = P[:, 2] / H
        P[:, 0] += 0.012 * t * t; P[:, 1] += 0.006 * t; return P
    lathe(m, prof, 0, T_GLAZE, n=28 if kind != 'Vase' else 22, tag=TAG_CERAMIC, wob=0.012, deform=lean)
    if J['handles']:
        for sx in (-1, 1):
            pts = [[sx * 0.2, 0, 0.385], [sx * 0.262, 0, 0.43], [sx * 0.275, 0, 0.49], [sx * 0.235, 0, 0.535], [sx * 0.15, 0, 0.545], [sx * 0.118, 0, 0.535]]
            cp = np.array(pts); tt = np.linspace(0, 1, 15); seg = np.linspace(0, 1, len(cp))            # a pulled handle: smooth curve, oval section
            for _ in range(2):
                cp = np.array([cp[0]] + [(cp[i - 1] + 2 * cp[i] + cp[i + 1]) / 4 for i in range(1, len(cp) - 1)] + [cp[-1]])
            fine = np.stack([np.interp(tt, seg, cp[:, k]) for k in range(3)], -1)
            m.tube(fine, [0.022] + [0.0165] * 13 + [0.022], 0, sides=10, tag=TAG_CERAMIC, smooth=True, tile=T_GLAZE, vrange=(0.5, 0.1), shape=[1.25, 1.1, 0.8, 0.8, 1.1, 1.25, 1.1, 0.8, 0.8, 1.1])
    rm = max(p[0] for p in prof)
    m.rubs = [([rm, 0, H * 0.45], 0.1, 0.5), ([-rm * 0.7, rm * 0.7, H * 0.5], 0.08, 0.4)]
    m.stains = [([0, -rm, H * 0.3], 0.12, 0.3)]
    m.hulls = [[[rm * math.cos(t), rm * math.sin(t), z] for t in np.linspace(0, 2 * math.pi, 9)[:-1] for z in (0.0, H)]]


# ---------------------------------------------------------------- sacks
def sack_lying(m, a=0.47, b=0.31, c=0.17):
    """a full grain sack on its side: plump, slumped flat underneath, the mouth end folded and sewn with twine, two ears"""
    r = m.rng; nu, nv = 48, 20; sd = int(r.integers(1e6))
    sp = lambda v, e: math.copysign(abs(v) ** e, v)
    V = []; idx = []
    for j in range(nv + 1):
        ph = -math.pi / 2 + math.pi * j / nv
        if j in (0, nv):
            idx.append([len(V)] * nu); V.append([0, 0, c * (1 if j == nv else -1)]); continue
        row = []
        for k in range(nu):
            th = 2 * math.pi * k / nu
            x = a * sp(math.cos(ph), 0.45) * sp(math.cos(th), 0.6); y = b * sp(math.cos(ph), 0.45) * sp(math.sin(th), 0.62); z = c * sp(math.sin(ph), 0.75)
            row.append(len(V)); V.append([x, y, z])
        idx.append(row)
    V = np.array(V)
    t = np.clip((V[:, 0] / a - 0.55) / 0.45, 0, 1)                # the mouth end (+X): flattened into a sewn seam with ears at the corners
    V[:, 2] *= 1 - 0.8 * t ** 1.5; V[:, 1] *= 1 + 0.1 * t; V[:, 0] += 0.05 * t * np.abs(V[:, 1] / b) ** 3
    t2 = np.clip((-V[:, 0] / a - 0.7) / 0.3, 0, 1)                # the bottom end: gusset corners
    V[:, 2] *= 1 - 0.45 * t2 ** 2; V[:, 0] -= 0.035 * t2 * np.abs(V[:, 1] / b) ** 3
    lum = 0.03 * vnoise(V, sd, 5.0) + 0.016 * vnoise(V, sd + 1, 13.0)       # the grain inside, and creases pulling toward the seam
    cre = 0.013 * np.sin(V[:, 1] * 24 + 2.5 * vnoise(V, sd + 2, 5.0)) * np.clip((V[:, 0] / a - 0.1) / 0.6, 0, 1) + 0.008 * np.sin(V[:, 0] * 16 + 3 * vnoise(V, sd + 4, 4.0)) * np.clip(1 - np.abs(V[:, 2]) / (0.5 * c), 0, 1)
    nrm = V / (np.linalg.norm(V / np.array([a, b, c]), axis=1)[:, None] + 1e-6); nrm /= (np.linalg.norm(nrm, axis=1)[:, None] + 1e-9)
    V = V + nrm * (lum + cre)[:, None]
    V[:, 2] -= 0.05 * (1 - (V[:, 0] / a) ** 2) * (V[:, 2] > 0)    # slumped top
    zf = -c * 0.62
    low = V[:, 2] < zf; V[low, 2] = zf + (V[low, 2] - zf) * 0.12; V[low, 0] *= 1.02; V[low, 1] *= 1.03
    V[:, 2] -= V[:, 2].min()
    F = []; UV = []; uo = r.uniform(0, 1, 2); per = 2 * math.pi * (a + b) / 2
    for j in range(nv):
        for k in range(nu):
            k2 = (k + 1) % nu
            f = [idx[0][k], idx[1][k2], idx[1][k]] if j == 0 else ([idx[j][k], idx[j][k2], idx[j + 1][k]] if j == nv - 1 else [idx[j][k], idx[j][k2], idx[j + 1][k2], idx[j + 1][k]])
            sg = 1.0 if j >= nv // 2 else -1.0                   # the cloth laid flat: top and underside each mapped straight down, the weave square to the sack
            F.append(f); UV.append([(V[q][0] / T_HESS + uo[0], (sg * V[q][1] + 0.5 * V[q][2]) / T_HESS + uo[1] + (0.37 if sg < 0 else 0.0)) for q in f])
    m.add_uv(V, F, UV, 0, TAG_CLOTH, True)
    zs = float(V[np.abs(V[:, 0] - a * 0.97).argmin(), 2])
    xs_ = a * 0.9; zc = float(V[(np.abs(V[:, 0] - xs_) < 0.03) & (np.abs(V[:, 1]) < 0.05), 2].max()) if ((np.abs(V[:, 0] - xs_) < 0.03) & (np.abs(V[:, 1]) < 0.05)).any() else c
    for k in range(9):                                           # twine stitches across the mouth
        y = -b * 0.8 + 1.6 * b * k / 8
        m.tube([[xs_ - 0.03, y - 0.012, zc + 0.004], [xs_ - 0.005, y, zc + 0.016], [xs_ + 0.03, y + 0.012, zc + 0.002]], 0.004, 2, sides=5, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))
    m.tube([[xs_, b * 0.8, zc + 0.01], [xs_ + 0.04, b * 0.93, zc - 0.01], [xs_ + 0.03, b * 1.02, 0.02], [xs_ - 0.03, b * 1.1, 0.006]], 0.004, 2, sides=5, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))
    m.stains = [([-a * 0.3, b * 0.4, c * 1.3], 0.2, 0.35), ([a * 0.2, -b, 0.1], 0.2, 0.4)]
    m.rubs = [([0, 0, 2 * c], 0.25, 0.3)]
    m.hulls = [[[sx * a, sy * b, z] for sx in (-0.95, 0.95) for sy in (-0.95, 0.95) for z in (0, 1.5 * c)]]


def sack_standing(m, rx=0.35, ry=0.27, H=0.75):
    """a feed sack stood on end, its neck gathered and tied"""
    r = m.rng; sd = int(r.integers(1e6)); zn = H * 0.8
    prof = [(0, 0.0), (0.5, 0.0), (0.86, 0.012), (0.97, 0.06), (1.0, 0.16), (1.0, 0.28), (0.98, 0.4), (0.9, 0.5), (0.72, 0.565), (0.45, 0.6), (0.24, 0.615), (0.2, 0.63), (0.26, 0.66), (0.42, 0.71), (0.5, 0.745), (0.47, 0.75), (0.3, 0.71), (0.12, 0.67), (0, 0.665)]
    prof = [(a * ry, b * H / 0.75) for a, b in prof]

    def deform(P):
        P = P.copy(); ang = np.arctan2(P[:, 1], P[:, 0]); z = P[:, 2]; rad = np.hypot(P[:, 0], P[:, 1])
        neck = np.clip((z - 0.5 * H) / (0.3 * H), 0, 1)
        fold = 1 + (0.11 * np.sin(ang * 8 + 1.6 * np.sin(ang * 2 + 1)) + 0.05 * np.sin(ang * 15 + 2 * np.sin(ang * 3))) * neck ** 1.5          # gathers at the neck
        bulge = 1 + 0.07 * vnoise(P, sd, 4.0) + 0.035 * vnoise(P, sd + 1, 11.0) + 0.08 * np.clip((0.3 * H - z) / (0.3 * H), 0, 1) + 0.02 * np.sin(z * 55 + 3 * vnoise(P, sd + 2, 3.0)) * np.clip((0.4 * H - z) / (0.3 * H), 0, 1)   # weight settling to the bottom, slump creases
        k = fold * bulge
        P[:, 0] *= k * (rx / ry * (1 - neck) + 1.0 * neck); P[:, 1] *= k
        P[:, 0] += 0.05 * neck * neck + 0.03 * (z / H) ** 2; P[:, 1] += 0.025 * (z / H) ** 2; P[:, 2] += 0.02 * np.sin(ang * 3 + 1) * np.clip((z - 0.85 * H) / (0.1 * H), 0, 1)
        return P
    lathe(m, prof, 0, T_HESS, n=48, tag=TAG_CLOTH, deform=deform, vscale=1.0, maxseg=0.03)
    whip(m, [0.012, 0, 0.63 * H / 0.75], 0.068, turns=3.5, rad=0.005, slot=2, rise=0.03)
    m.tube([[0.07, 0.01, 0.63 * H / 0.75], [0.11, 0.03, 0.6 * H / 0.75], [0.13, 0.05, 0.52 * H / 0.75]], 0.005, 2, sides=5, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2))
    m.stains = [([rx, 0, 0.2], 0.25, 0.4), ([-rx * 0.5, -ry, 0.1], 0.2, 0.4)]
    m.rubs = [([0, -ry, H * 0.4], 0.2, 0.3)]
    m.hulls = [[[sx * rx, sy * ry, z] for sx in (-1, 1) for sy in (-1, 1) for z in (0, H * 0.8)]]


# ---------------------------------------------------------------- furniture
def top_boards(m, x0, x1, y0, y1, z0, th, nb, circle=None, over=0.006):
    """a board top: nb boards along X, uneven ends and thickness, hairline to 3 mm gaps; circle = radius to cut the outline round"""
    r = m.rng; bw = (y1 - y0) / nb
    for k in range(nb):
        ya, yb = y0 + k * bw + r.uniform(0.0005, 0.0016), y0 + (k + 1) * bw - r.uniform(0.0005, 0.0016)
        if circle:                                              # round top: each board a grid whose ends follow the circle
            ya, yb = max(ya, -circle * 0.985), min(yb, circle * 0.985); ys = np.linspace(ya, yb, 4); nx = 14; zt = z0 + th + r.normal(0, 0.0012)
            top = np.zeros((4, nx + 1, 3)); und = np.zeros_like(top)
            for j, y in enumerate(ys):
                xc = math.sqrt(max(circle ** 2 - y * y, 1e-4)) + r.normal(0, 0.0015)
                for i in range(nx + 1):
                    x = -xc + 2 * xc * i / nx
                    top[j, i] = [x, y, zt - (0.0035 if j in (0, 3) else 0.0) - (0.005 if i in (0, nx) else 0.0) + 0.0012 * math.sin(x * 7 + k)]; und[j, i] = [x * 0.995, y, z0]
            v0, w = brd(m); uo = r.uniform(0, 1)

            def uvw(P, v0=v0, w=w, uo=uo, C=nx + 1):
                idx = np.arange(len(P)); j_ = (idx // C) % 4
                return np.stack([P[:, 0] / T_TIMBER + uo, v0 + (j_ / 3.0 - 0.5) * w * 0.8], -1)
            m.hgrid(top, und, 1, T_TIMBER, tag=TAG_TOP, up=(0, 0, 1), uvfn=uvw, smooth=True, grid_under=True)
            continue
        n0 = len(m.V)
        m.beam([x0 - abs(r.normal(0, over)), ya, z0], [x1 + abs(r.normal(0, over)), yb, z0 + th + r.normal(0, 0.0012)], 0.004, 0.0015, max(4, int((x1 - x0) / 0.22)), 0.0008)
        if circle:
            V = np.array(m.V); W_ = V[n0:]; xc = np.sqrt(np.maximum(circle ** 2 - np.clip(np.abs(W_[:, 1]), 0, circle) ** 2, 1e-5)); W_[:, 0] = np.clip(W_[:, 0], -xc, xc); V[n0:] = W_; m.V = V.tolist()
        m.VT[n0:] = [TAG_TOP] * (len(m.V) - n0)


def leg(m, x, y, z0, z1, s=0.09, taper=0.8):
    """square leg, tapered below the rail, chamfered"""
    n0 = len(m.V)
    timber(m, [x - s / 2, y - s / 2, z0], [x + s / 2, y + s / 2, z1], 0.01, 0.002, segs=6)
    V = np.array(m.V); W_ = V[n0:]; k = taper + (1 - taper) * np.clip((W_[:, 2] - z0) / max(0.6 * (z1 - z0), 1e-3), 0, 1)
    W_[:, 0] = x + (W_[:, 0] - x) * k; W_[:, 1] = y + (W_[:, 1] - y) * k; V[n0:] = W_; m.V = V.tolist()


def table_long(m, L=2.65, W=1.5, H=0.905):
    r = m.rng; th = 0.048; lx, ly = L / 2 - 0.22, W / 2 - 0.16
    top_boards(m, -L / 2, L / 2, -W / 2, W / 2, H - th, th, 6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg(m, sx * lx, sy * ly, 0.0, H - th, 0.11)
    for sy in (-1, 1):                                           # rails tenoned into the legs, pegged
        timber(m, [-lx + 0.04, sy * ly - 0.018, H - th - 0.15], [lx - 0.04, sy * ly + 0.018, H - th], 0.006, 0.002)
    for sx in (-1, 1):
        timber(m, [sx * lx - 0.018, -ly + 0.04, H - th - 0.15], [sx * lx + 0.018, ly - 0.04, H - th], 0.006, 0.002)
        timber(m, [sx * lx - 0.02, -ly + 0.04, 0.16], [sx * lx + 0.02, ly - 0.04, 0.24], 0.008, 0.003)          # foot rails, worn by boots
    timber(m, [-lx + 0.015, -0.03, 0.17], [lx - 0.015, 0.03, 0.23], 0.008, 0.004)                              # long stretcher
    for sx in (-1, 1):
        for sy in (-1, 1):
            nail_p = [sx * (lx - 0.0), sy * (ly + 0.057), H - th - 0.075]
            m.tube([[nail_p[0] - 0.02 * sx, nail_p[1] + 0.006 * sy, nail_p[2]], [nail_p[0] - 0.02 * sx, nail_p[1] - 0.02 * sy, nail_p[2]]], [0.01, 0.008], 1, sides=6, tag=TAG_END, smooth=False)
    m.stains = [([0.5, -0.2, H], 0.13, 0.55), ([-0.7, 0.3, H], 0.2, 0.45), ([0.1, 0.45, H], 0.09, 0.6), ([-0.2, -0.5, H], 0.3, 0.3), ([lx, 0, 0.2], 0.5, 0.3)]
    m.rubs = [([0, -W / 2, H], 0.5, 0.5), ([0.6, W / 2, H], 0.4, 0.45), ([-0.8, -W / 2, H], 0.35, 0.4), ([sx * lx, 0, 0.24], 0.3, 0.5)]
    m.ucx = [([-L / 2, -W / 2, H - th - 0.15], [L / 2, W / 2, H])] + [([sx * lx - 0.06, sy * ly - 0.06, 0], [sx * lx + 0.06, sy * ly + 0.06, H - th]) for sx in (-1, 1) for sy in (-1, 1)]


def table_round(m, D=1.6, H=0.8):
    r = m.rng; th = 0.044; R_ = D / 2; lr = R_ * 0.62
    top_boards(m, -R_, R_, -R_, R_, H - th, th, 8, circle=R_)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; x, y = lr * math.cos(a), lr * math.sin(a)
        leg(m, x, y, 0.0, H - th, 0.085, taper=0.78)
    for k in range(2):                                           # two battens under the top, clenched through; crossed stretchers below
        a = math.pi / 4 + k * math.pi / 2
        n0 = len(m.V); timber(m, [-lr - 0.12, -0.04, H - th - 0.05 - 0.05 * k], [lr + 0.12, 0.04, H - th - 0.05 * k], 0.006, 0.002); m.xform_since(n0, RZ([0, 0, 0], a))
        n0 = len(m.V); timber(m, [-lr + 0.02, -0.022, 0.2 + 0.045 * k], [lr - 0.02, 0.022, 0.245 + 0.045 * k], 0.007, 0.003); m.xform_since(n0, RZ([0, 0, 0], a))
    m.stains = [([0.2, -0.2, H], 0.11, 0.6), ([-0.3, 0.25, H], 0.16, 0.45), ([0.1, 0.4, H], 0.25, 0.3)]
    m.rubs = [([R_ * math.cos(a), R_ * math.sin(a), H], 0.3, 0.45) for a in (0.3, 2.0, 3.6, 5.1)]
    m.hulls = [[[R_ * math.cos(t), R_ * math.sin(t), z] for t in np.linspace(0, 2 * math.pi, 9)[:-1] for z in (H - 0.1, H)]]
    m.ucx = [([-lr * 0.75, -lr * 0.75, 0], [lr * 0.75, lr * 0.75, H - 0.1])]


def chair(m, W=0.5, D=0.46, SH=0.46, H=1.0):
    r = m.rng; hx, hy = W / 2 - 0.035, D / 2 - 0.035
    for sx in (-1, 1):
        leg(m, sx * hx, -hy, 0.0, SH - 0.03, 0.05, taper=0.8)    # front legs
        n0 = len(m.V); timber(m, [sx * hx - 0.025, hy - 0.022, 0.0], [sx * hx + 0.025, hy + 0.022, H], 0.008, 0.003, segs=8)
        V = np.array(m.V); W_ = V[n0:]; W_[:, 1] += 0.09 * np.clip((W_[:, 2] - SH) / (H - SH), 0, 1) ** 1.3 + 0.03 * np.clip((0.2 - W_[:, 2]) / 0.2, 0, 1); V[n0:] = W_; m.V = V.tolist()   # raked back, kicked foot
    top_boards(m, -W / 2 - 0.01, W / 2 + 0.01, -D / 2 - 0.015, D / 2 - 0.03, SH - 0.03, 0.03, 3, over=0.002)
    for sy in (-1, 1):
        timber(m, [-hx + 0.02, sy * hy - 0.012, SH - 0.1], [hx - 0.02, sy * hy + 0.012, SH - 0.03], 0.004, 0.001)
        timber(m, [-hx + 0.02, sy * hy - 0.011, 0.14 + 0.07 * (sy > 0)], [hx - 0.02, sy * hy + 0.011, 0.175 + 0.07 * (sy > 0)], 0.005, 0.002)
    for sx in (-1, 1):
        timber(m, [sx * hx - 0.012, -hy + 0.02, SH - 0.1], [sx * hx + 0.012, hy - 0.02, SH - 0.03], 0.004, 0.001)
        timber(m, [sx * hx - 0.011, -hy + 0.02, 0.2], [sx * hx + 0.011, hy - 0.02, 0.235], 0.005, 0.002)
    for (za, zb_, th_) in ((H - 0.13, H - 0.02, 0.022), (SH + 0.2, SH + 0.27, 0.016)):          # crest rail and one slat, following the rake
        zm = (za + zb_) / 2; off = 0.09 * ((zm - SH) / (H - SH)) ** 1.3
        n0 = len(m.V); timber(m, [-hx + 0.02, hy - th_ / 2 + off, za], [hx - 0.02, hy + th_ / 2 + off, zb_], 0.005, 0.002); m.xform_since(n0, RX([0, hy + off, zm], -0.12))
    for sx in (-1, 1):
        for zz in (SH - 0.065, H - 0.075):
            off = 0.09 * max(0.0, (zz - SH) / (H - SH)) ** 1.3
            m.tube([[sx * (hx + 0.028), hy + off, zz], [sx * (hx + 0.01), hy + off, zz]], [0.007, 0.006], 1, sides=6, tag=TAG_END, smooth=False)
    m.stains = [([0, 0, SH], 0.2, 0.35), ([0, hy + 0.09, H - 0.07], 0.2, 0.5), ([hx, -hy, 0.1], 0.15, 0.4)]
    m.rubs = [([0, -D / 2, SH], 0.22, 0.6), ([0, hy + 0.09, H], 0.15, 0.5)]
    m.ucx = [([-W / 2, -D / 2, 0], [W / 2, D / 2, SH]), ([-W / 2, hy - 0.03, SH], [W / 2, hy + 0.13, H])]


def bench(m, L=2.3, W=0.3, H=0.45):
    r = m.rng
    top_boards(m, -L / 2, L / 2, -W / 2, W / 2, H - 0.045, 0.045, 1, over=0.004)
    for sx in (-1, 1):                                           # slab ends with a boot notch, through-tenoned
        x = sx * (L / 2 - 0.25)
        for sy in (-1, 1):
            board(m, [x - 0.02, sy * 0.04 if sy > 0 else -W / 2 + 0.02, 0.0], [x + 0.02, W / 2 - 0.02 if sy > 0 else -0.04, H - 0.045], 0.006, 0.002)
        board(m, [x - 0.02, -0.045, 0.14], [x + 0.02, 0.045, H - 0.045], 0.004, 0.001)
        for sy in (-0.07, 0.07):
            m.block([x - 0.022, sy - 0.02, H - 0.004], [x + 0.022, sy + 0.02, H + 0.004], 1, T_TIMBER, 0.003, 0.001, tag=TAG_END)
    timber(m, [-L / 2 + 0.25, -0.016, H - 0.2], [L / 2 - 0.25, 0.016, H - 0.11], 0.005, 0.003)
    m.stains = [([0.3, 0, H], 0.2, 0.3), ([-L / 2 + 0.25, 0, 0.05], 0.2, 0.5)]
    m.rubs = [([-0.5, 0, H], 0.3, 0.55), ([0.45, 0, H], 0.3, 0.55), ([0, -W / 2, H], 1.0, 0.25)]
    m.ucx = [([-L / 2, -W / 2, 0], [L / 2, W / 2, H])]


def stool(m, D=0.36, H=0.45):
    r = m.rng; R_ = D / 2
    prof = [(0, H - 0.05), (R_ * 0.9, H - 0.05), (R_, H - 0.038), (R_, H - 0.012), (R_ * 0.96, H - 0.002), (R_ * 0.6, H - 0.008), (0, H - 0.012)]
    lathe(m, prof, 1, T_TIMBER, n=20, tag=TAG_TOP, wob=0.01, vscale=1.0)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4; d = np.array([math.cos(a), math.sin(a), 0.0])
        p1 = d * R_ * 0.55 + np.array([0, 0, H - 0.02]); p0 = d * (R_ * 1.05) + np.array([0, 0, 0.0])
        m.tube([p0, p0 * 0.6 + p1 * 0.4, p1, p1 + (p1 - p0) * 0.03], [0.02, 0.023, 0.019, 0.017], 1, sides=8, tag=TAG_TIMBER, smooth=True, shape=[1, 0.9, 1, 0.92, 1, 0.9, 1, 0.93])
    m.rubs = [([0, 0, H], 0.14, 0.6)]; m.stains = [([0.05, 0.05, H], 0.08, 0.3)]
    m.hulls = [[[R_ * 1.05 * math.cos(t), R_ * 1.05 * math.sin(t), z] for t in np.linspace(0, 2 * math.pi, 7)[:-1] for z in (0.0, H)]]


def cushion(m, cx, cy, cz, a, b, c, slot, tile, dent=0.0, nu=24, nv=10, yaw=0.0):
    """a stuffed pillow: superellipsoid with piped edge, pinched corners and a head dent"""
    r = m.rng; sd = int(r.integers(1e6)); sp = lambda v, e: math.copysign(abs(v) ** e, v)
    V = []; idx = []
    for j in range(nv + 1):
        ph = -math.pi / 2 + math.pi * j / nv
        if j in (0, nv):
            idx.append([len(V)] * nu); V.append([0, 0, c * (1 if j == nv else -1)]); continue
        row = []
        for k in range(nu):
            th = 2 * math.pi * k / nu
            row.append(len(V)); V.append([a * sp(math.cos(ph), 0.35) * sp(math.cos(th), 0.5), b * sp(math.cos(ph), 0.35) * sp(math.sin(th), 0.5), c * sp(math.sin(ph), 1.0)])
        idx.append(row)
    V = np.array(V)
    corner = (np.abs(V[:, 0]) / a) ** 4 * (np.abs(V[:, 1]) / b) ** 4
    V[:, 2] *= 1 - 0.75 * corner
    V[:, 2] -= dent * np.exp(-((V[:, 0] / (a * 0.5)) ** 2 + (V[:, 1] / (b * 0.55)) ** 2)) * (V[:, 2] > 0)
    V[:, 2] += (0.014 * vnoise(V, sd, 9.0) + 0.008 * np.sin(V[:, 0] * 40 + 3 * vnoise(V, sd + 1, 6.0)) * (np.abs(V[:, 1]) / b) ** 2) * (1 - corner)
    F = []; UV = []; uo = r.uniform(0, 1, 2)
    for j in range(nv):
        for k in range(nu):
            k2 = (k + 1) % nu
            P4 = lambda q: (V[q][0] / tile + uo[0], V[q][1] / tile + uo[1])
            if j == 0:
                f = [idx[0][k], idx[1][k2], idx[1][k]]
            elif j == nv - 1:
                f = [idx[j][k], idx[j][k2], idx[j + 1][k]]
            else:
                f = [idx[j][k], idx[j][k2], idx[j + 1][k2], idx[j + 1][k]]
            F.append(f); UV.append([P4(q) for q in f])
    M = np.array(Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(yaw, 4, 'Z'))
    V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
    m.add_uv(V, F, UV, slot, TAG_CLOTH, True)


def bed(m, L=2.5, W=1.36, HH=1.12, FH=0.68):
    """oak bed: four posts, plank head and foot boards, side rails pegged through, a straw mattress in ticking, a quilted wool
    blanket turned back with a madder border, one pillow"""
    r = m.rng; hx, hy = L / 2 - 0.06, W / 2 - 0.06; ps = 0.115
    for sx in (-1, 1):
        for sy in (-1, 1):
            hgt = HH if sx < 0 else FH
            leg(m, sx * hx, sy * hy, 0.0, hgt, ps, taper=0.9)
            m.block([sx * hx - ps / 2 - 0.008, sy * hy - ps / 2 - 0.008, hgt - 0.004], [sx * hx + ps / 2 + 0.008, sy * hy + ps / 2 + 0.008, hgt + 0.03], 1, T_TIMBER, 0.012, 0.002, mode='board', board=brd(m), tag=TAG_TOP)
    for (sx, zs) in ((-1, (0.5, 0.67, 0.84, 1.0)), (1, (0.3, 0.45, 0.6))):
        for za, zb_ in zip(zs[:-1], zs[1:]):
            board(m, [sx * hx - 0.016, -hy + 0.03, za + 0.002], [sx * hx + 0.016, hy - 0.03, zb_ - 0.002], 0.005, 0.0015)
    for sy in (-1, 1):
        timber(m, [-hx + 0.04, sy * hy - 0.02, 0.26], [hx - 0.04, sy * hy + 0.02, 0.46], 0.008, 0.003)
        for sx in (-1, 1):
            for zz in (0.31, 0.41):
                m.tube([[sx * (hx - 0.01), sy * (hy + 0.066), zz], [sx * (hx - 0.01), sy * (hy + 0.04), zz]], [0.009, 0.008], 1, sides=6, tag=TAG_END, smooth=False)
    # mattress: straw-stuffed tick, sagging in the middle, bulging between the rails
    mx0, mx1, my = -hx + 0.07, hx - 0.07, hy - 0.035; nxg, nyg = 34, 20; sd = int(r.integers(1e6))

    def sheet(z0, x0, x1, ymax, thick, droop, slot, tile, quilt=0.0, sag=0.03, edge=0.16):
        top = np.zeros((nyg + 1, nxg + 1, 3)); und = np.zeros_like(top)
        for j in range(nyg + 1):
            for i in range(nxg + 1):
                x = x0 + (x1 - x0) * i / nxg; y = -ymax + 2 * ymax * j / nyg
                ex = min(x - x0, x1 - x) / edge; ey = (ymax - abs(y)) / edge
                e = min(1.0, max(0.0, ex)) ** 0.5 * min(1.0, max(0.0, ey)) ** 0.5
                z = z0 - droop * (1 - e) - sag * math.exp(-((x + 0.1) / 0.7) ** 2 - (y / 0.42) ** 2)
                z += 0.012 * vnoise(np.array([[x, y, 0.0]]), sd, 5.0)[0] + 0.006 * vnoise(np.array([[x, y, 0.0]]), sd + 1, 13.0)[0]
                z += 0.01 * math.sin(x * 11 + 4 * vnoise(np.array([[x, y, 0.0]]), sd + 7, 2.0)[0]) * math.sin(y * 7 + 1.0) * (0.4 + 0.6 * e)          # rumples
                if quilt:
                    z += quilt * (abs(math.sin(math.pi * (x + y) / 0.25)) * abs(math.sin(math.pi * (x - y) / 0.25))) ** 0.45 * (1.0 if e >= 0.999 else e ** 3)
                top[j, i] = [x, y, z]; und[j, i] = [x, y, z0 - droop - thick]
        n0 = len(m.V)
        m.hgrid(top, und, slot, tile, tag=TAG_CLOTH, up=(0, 0, 1), smooth=True, grid_under=True)
        return n0
    sheet(0.6, mx0, mx1, my, 0.16, 0.06, 3, T_LINEN, sag=0.035)
    xb = -0.42                                                   # blanket from the foot up to the turn-back, hanging over the sides
    sheet(0.628, xb, mx1 - 0.005, my - 0.012, 0.03, 0.075, 4, T_LINEN, quilt=0.028, sag=0.035, edge=0.13)      # tucked in inside the rails
    tb = np.zeros((6, nyg + 1, 3)); tu = np.zeros_like(tb)       # the turned-back border: a roll of the blanket's madder lining
    for j in range(nyg + 1):
        y = -(my - 0.012) + 2 * (my - 0.012) * j / nyg; ey = min(1.0, max(0.0, (my - 0.012 - abs(y)) / 0.13)) ** 0.5
        zb_ = 0.63 - 0.07 * (1 - ey) - 0.03 * math.exp(-(y / 0.42) ** 2)
        for i, (dx, dz) in enumerate(((-0.02, 0.004), (0.0, 0.03), (0.06, 0.042), (0.15, 0.04), (0.2, 0.03), (0.22, 0.012))):
            wv = 0.008 * math.sin(y * 23 + i) + 0.006 * vnoise(np.array([[y, i * 0.3, 0.0]]), sd + 5, 6.0)[0]
            tb[i, j] = [xb + dx + wv, y, zb_ + dz + wv * 0.5]; tu[i, j] = [xb + dx, y, zb_ - 0.01]
    m.hgrid(tb, tu, 5, T_LINEN, tag=TAG_CLOTH, up=(0, 0, 1), smooth=True, grid_under=True)
    cushion(m, -hx + 0.42, 0.04, 0.685, 0.27, 0.42, 0.085, 3, T_LINEN, dent=0.05, yaw=0.06)
    m.stains = [([0.3, -0.2, 0.62], 0.3, 0.3), ([-hx + 0.42, 0.04, 0.75], 0.2, 0.3), ([hx, -hy, 0.15], 0.3, 0.4)]
    m.rubs = [([-hx, 0, HH], 0.5, 0.45), ([hx, 0, FH], 0.5, 0.45), ([0, -hy, 0.46], 0.9, 0.35)]; m.cloth_b = 0.0
    m.ucx = [([-L / 2, -W / 2, 0], [L / 2, W / 2, 0.68]), ([-L / 2, -W / 2, 0.68], [-L / 2 + 0.14, W / 2, HH])]


# ---------------------------------------------------------------- chest
def chest(m, L=0.85, W=0.5, HB=0.36, HL=0.2):
    """iron-bound chest with a barrel lid (sprite 175): plank carcase, coopered lid, three straps, hasp and lock plate"""
    r = m.rng; hx, hy = L / 2, W / 2; t = 0.022
    for sy in (-1, 1):
        for (za, zb_) in ((0.02, 0.19), (0.19, HB)):
            y0 = sy * hy - (t if sy > 0 else 0.0)
            board(m, [-hx, y0, za + 0.001], [hx, y0 + t, zb_ - 0.001], 0.004, 0.001)
    for sx in (-1, 1):
        x0 = sx * hx - (t if sx > 0 else 0.0)
        board(m, [x0 + (0.002 if sx < 0 else -0.002), -hy + t, 0.02], [x0 + t + (0.002 if sx < 0 else -0.002), hy - t, HB], 0.004, 0.001)
    board(m, [-hx + 0.004, -hy + 0.004, 0.0], [hx - 0.004, hy - 0.004, 0.024], 0.004, 0.001)
    ns = 7; Rl = hy / math.sin(math.radians(62)); zc = HB + 0.012 - Rl * math.cos(math.radians(62))
    for k in range(ns):                                          # coopered lid staves
        a = math.radians(-62 + 124 * (k + 0.5) / ns); wd = 2 * Rl * math.sin(math.radians(62) / ns) + 0.002
        cy, cz = Rl * math.sin(a), zc + Rl * math.cos(a)
        m.block([-hx - 0.004, cy - wd / 2 + 0.001, cz - t], [hx + 0.004, cy + wd / 2 - 0.001, cz + r.normal(0, 0.001)], 1, T_TIMBER, 0.004, 0.001, mode='board', board=brd(m), tag=TAG_TOP, rot=(0, -a, 0))
    for sx in (-1, 1):                                           # lid ends: a segment of board
        poly = [(Rl * 0.985 * math.sin(math.radians(a_)), zc + Rl * 0.985 * math.cos(math.radians(a_))) for a_ in np.linspace(-61, 61, 9)]
        x0 = sx * hx - (t if sx > 0 else 0.0)
        m.prism(poly, x0, x0 + t, 1, T_TIMBER, tag=TAG_TIMBER, axis=0, mode='board')
    m.block([-hx + t, -hy + t, 0.03], [hx - t, hy - t, HB + 0.05], 1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)
    for xs_ in (-hx + 0.09, 0.0, hx - 0.09):                     # straps: up the front, over the lid, down the back
        w2 = 0.026
        for sy in (-1, 1):
            y0 = sy * hy
            m.block([xs_ - w2, min(y0, y0 + sy * 0.005), 0.0], [xs_ + w2, max(y0, y0 + sy * 0.005), HB - 0.004], 3, T_IRON, 0.002, 0.0006, tag=TAG_METAL)
            for zz in (0.06, 0.17, 0.3):
                nail(m, [xs_ + r.normal(0, 0.004), y0 + sy * 0.004, zz], 2 * sy, 0.008, l=0.005)
        nseg = 9
        for k in range(nseg):
            a = math.radians(-63 + 126 * (k + 0.5) / nseg); wd = 2 * (Rl + 0.004) * math.sin(math.radians(63) / nseg) + 0.004
            cy, cz = (Rl + 0.003) * math.sin(a), zc + (Rl + 0.003) * math.cos(a)
            m.block([xs_ - w2, cy - wd / 2, cz - 0.003], [xs_ + w2, cy + wd / 2, cz + 0.003], 3, T_IRON, 0.0015, 0.0005, tag=TAG_METAL, rot=(0, -a, 0))
            if k % 2 == 1:
                nail(m, [xs_, cy, cz + 0.002], 3, 0.007, l=0.004)
    for sx in (-1, 1):                                           # corner irons
        for sy in (-1, 1):
            m.block([sx * hx - (0.05 if sx > 0 else -0.0) - (0.0 if sx > 0 else 0.0), sy * hy - (0.004 if sy < 0 else -0.0), 0.0] if False else [min(sx * hx, sx * (hx - 0.05)), min(sy * hy, sy * (hy + 0.004)), 0.0],
                    [max(sx * hx, sx * (hx - 0.05)), max(sy * hy, sy * (hy + 0.004)), 0.07], 3, T_IRON, 0.002, 0.0006, tag=TAG_METAL)
    m.block([-0.05, -hy - 0.007, HB - 0.13], [0.05, -hy, HB - 0.02], 1, T_TIMBER, 0.004, 0.001, tag=TAG_IRON)             # lock plate, keyhole, hasp
    m.block([-0.006, -hy - 0.009, HB - 0.1], [0.006, -hy - 0.006, HB - 0.07], 1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)
    m.block([-0.02, -hy - 0.014, HB - 0.05], [0.02, -hy - 0.006, HB + 0.05], 1, T_TIMBER, 0.004, 0.001, tag=TAG_IRON)
    for sx in (-1, 1):                                           # drop handles on the ends
        x0 = sx * (hx + 0.004)
        pts = [[x0 + sx * 0.012, -0.07, 0.26], [x0 + sx * 0.03, -0.07, 0.2], [x0 + sx * 0.034, -0.03, 0.18], [x0 + sx * 0.034, 0.03, 0.18], [x0 + sx * 0.03, 0.07, 0.2], [x0 + sx * 0.012, 0.07, 0.26]]
        m.tube(pts, 0.007, 1, sides=6, tag=TAG_IRON, smooth=True)
        for sy in (-0.07, 0.07):
            m.block([min(x0, x0 + sx * 0.008), sy - 0.018, 0.245], [max(x0, x0 + sx * 0.008), sy + 0.018, 0.275], 1, T_TIMBER, 0.003, 0.0006, tag=TAG_IRON)
    m.stains = [([0, -hy, 0.1], 0.3, 0.4), ([hx, 0, 0.05], 0.3, 0.4)]
    m.rubs = [([0, -hy * 0.6, HB + HL], 0.25, 0.5), ([0, -hy, HB], 0.12, 0.5)]
    m.metal_b = 0.5
    m.ucx = [([-hx, -hy, 0], [hx, hy, HB + HL * 0.8])]


# ---------------------------------------------------------------- bones
TAG_BONE2 = 62


def mound2(m, cx, cy, rx, ry, h, slot, tile, tag, seed, n=13):
    """a heap with a round outline (the square grid of mound() mapped onto a disc), lumpy, feathered to nothing at the edge"""
    top = np.zeros((n, n, 3)); under = np.zeros_like(top)
    for i in range(n):
        for j in range(n):
            u, v = (i / (n - 1)) * 2 - 1, (j / (n - 1)) * 2 - 1
            du, dv = u * math.sqrt(1 - v * v / 2), v * math.sqrt(1 - u * u / 2); q = min(1.0, math.hypot(du, dv))
            wob = 1 + 0.12 * vnoise(np.array([[du * 2.0, dv * 2.0, seed * 0.1]]), seed + 3, 1.0)[0]
            x = cx + du * rx * wob; y = cy + dv * ry * wob
            z = h * (1 - q * q) ** 0.8 * (1 + 0.35 * vnoise(np.array([[x, y, 0.0]]), seed, 3.0)[0] + 0.15 * vnoise(np.array([[x, y, 0.0]]), seed + 1, 9.0)[0]) + 0.004
            top[i, j] = [x, y, max(z, 0.004)]; under[i, j] = [x, y, -0.02]
    m.hgrid(top, under, slot, tile, tag=tag, up=(0, 0, 1), smooth=True, grid_under=True)
    m.mounds = getattr(m, 'mounds', []) + [(cx, cy, rx, ry)]


def skull(m, slot):
    """a human skull without its jaw: cranium, brow, cheek bones, eye sockets and nose as dark hollows, a row of upper teeth.
    Faces -Y, rests on the palate at z = 0"""
    prof = [(0, 0.0), (0.035, 0.0), (0.055, 0.012), (0.068, 0.04), (0.08, 0.075), (0.086, 0.11), (0.08, 0.145), (0.062, 0.172), (0.035, 0.188), (0, 0.193)]

    def sk(P):
        P = P.copy(); z = P[:, 2]; fr = np.clip(-P[:, 1] / 0.08, 0, 1); bk = np.clip(P[:, 1] / 0.08, 0, 1)
        face = np.clip((0.085 - z) / 0.085, 0, 1)                                         # below the brow the face narrows to the upper jaw
        P[:, 1] = P[:, 1] * 1.28 + 0.02
        P[:, 0] *= 1 - 0.38 * face * (0.4 + 0.6 * fr) - 0.25 * face * bk
        P[:, 1] += 0.03 * face * bk * -1 + 0.012 * fr * np.clip(1 - np.abs(z - 0.095) / 0.02, 0, 1) * -1          # occiput tucks under; brow ridge
        for sx in (-1, 1):
            d = np.hypot(P[:, 0] - sx * 0.034, z - 0.072); P[:, 1] += 0.028 * np.clip(1 - d / 0.027, 0, 1) ** 0.6 * (fr > 0.3)       # sockets
            d = np.hypot(P[:, 0] - sx * 0.062, z - 0.05); P[:, 0] += sx * 0.008 * np.clip(1 - d / 0.03, 0, 1) * (fr > 0.2)         # cheek bones
        d = np.hypot(P[:, 0], z - 0.04); P[:, 1] += 0.02 * np.clip(1 - d / 0.016, 0, 1) * (fr > 0.5)
        return P
    lathe(m, prof, slot, T_PL, n=26, tag=TAG_BONE2, deform=sk, maxseg=0.014)
    for sx in (-1, 1):
        m.rock([sx * 0.034, -0.082, 0.072], [0.04, 0.03, 0.036], 1, T_TIMBER, sub=1, tag=TAG_GLASS + 30, lump=0.1, smooth=True, facets=0)
    m.rock([0.0, -0.092, 0.04], [0.02, 0.02, 0.03], 1, T_TIMBER, sub=1, tag=TAG_GLASS + 30, lump=0.1, smooth=True, facets=0)
    for k in range(8):                                           # teeth
        a = math.pi * (0.22 + 0.56 * k / 7)
        m.block([-0.04 * math.cos(a) - 0.0045, -0.062 - 0.03 * math.sin(a) - 0.004, -0.008], [-0.04 * math.cos(a) + 0.0045, -0.062 - 0.03 * math.sin(a) + 0.004, 0.006], slot, T_PL, 0.002, 0.0006, tag=TAG_BONE2)


def long_bone(m, p0, p1, rad, slot):
    p0 = np.array(p0, float); p1 = np.array(p1, float); ts = [0, 0.015, 0.04, 0.07, 0.11, 0.16, 0.24, 0.5, 0.78, 0.86, 0.91, 0.95, 0.985, 1.0]; rs = [0.5, 1.4, 1.85, 1.9, 1.6, 1.25, 1.05, 0.9, 1.05, 1.3, 1.65, 1.8, 1.4, 0.6]
    side = np.cross(p1 - p0, [0, 0, 1.0]); side /= np.linalg.norm(side) + 1e-9
    pts = [p0 + (p1 - p0) * t + side * 0.012 * math.sin(math.pi * t) * np.linalg.norm(p1 - p0) for t in ts]
    m.tube(pts, [rad * q for q in rs], slot, sides=10, tag=TAG_BONE2, smooth=True, tile=T_PL, vrange=(0.5, 0.2), shape=[1, 0.92, 0.85, 0.92, 1, 1.08, 0.95, 0.88, 0.95, 1.05])


def bones(m, with_skull=True):
    """what the grave gave back: a skull on its side, thigh and shin bones, a broken fan of ribs, a pelvis half, all weathered"""
    r = m.rng
    if with_skull:
        n0 = len(m.V); skull(m, 0)
        m.xform_since(n0, np.array(Matrix.Translation((0.2, 0.12, 0.062)) @ Matrix.Rotation(0.9, 4, 'Z') @ Matrix.Rotation(1.25, 4, 'Y')))
    long_bone(m, [-0.42, -0.1, 0.022], [0.02, -0.22, 0.02], 0.014, 0); long_bone(m, [-0.3, 0.12, 0.02], [0.1, 0.3, 0.035], 0.012, 0)
    long_bone(m, [0.05, -0.05, 0.016], [0.36, -0.25, 0.014], 0.0095, 0); long_bone(m, [-0.12, -0.3, 0.012], [0.16, -0.36, 0.012], 0.008, 0)
    for k in range(5):                                           # ribs: flat curved blades, some snapped
        a0 = -0.5 + 0.22 * k; L = 0.2 + 0.03 * (k % 3) - (0.08 if k == 3 else 0.0)
        pts = [[-0.1 + 0.07 * k + 0.02 * math.sin(t * 2.5), 0.02 + L * math.sin(t * 1.4) * math.cos(a0 * 0.3), 0.012 + 0.07 * math.sin(t * 2.6) * (0.5 + 0.1 * k)] for t in np.linspace(0, 1, 8)]
        m.tube(pts, [0.007, 0.0065, 0.006, 0.006, 0.0055, 0.005, 0.0045, 0.003], 0, sides=6, tag=TAG_BONE2, smooth=True, tile=T_PL, vrange=(0.5, 0.2), shape=[1.5, 0.8, 0.8, 1.5, 0.8, 0.8])
    V = np.array(m.V); V[:, 2] -= V[:, 2].min() - 0.0; m.V = V.tolist()
    m.hulls = [[[sx * 0.4, sy * 0.35, z] for sx in (-1, 1) for sy in (-1, 1) for z in (0, 0.12)]]


# ---------------------------------------------------------------- gravestones
def gravestone(m, kind):
    r = m.rng; sd = int(r.integers(1e6))
    W, H, T = {'Round': (0.8, 1.05, 0.15), 'Pointed': (0.66, 1.2, 0.14), 'Broken': (0.78, 0.74, 0.16)}[kind]
    hw = W / 2

    def ztop(x):
        u = abs(x) / hw
        if kind == 'Round':
            return H - hw + hw * math.sqrt(max(0.0, 1 - u * u)) * 0.98 + 0.012 * math.sin(x * 23)
        if kind == 'Pointed':
            return H - 0.3 * u ** 1.2 - (0.05 if u > 0.72 else 0.0)
        return H - 0.34 * (x + hw) / W + 0.05 * math.sin(x * 17) + 0.035 * math.sin(x * 41 + 1)               # snapped across on a slant
    n0 = len(m.V)
    m.slab(-hw, hw, -0.35, H, -T / 2, T / 2, 0, T_BOULDER, nx=14, nz=16, relief=0.012, ztop=ztop, tag=TAG_SHEET)
    V = np.array(m.V); W_ = V[n0:]                              # edges rounded off by weather: pinch the thickness toward the outline
    edge = np.minimum(np.clip((hw - np.abs(W_[:, 0])) / 0.07, 0, 1), np.clip((np.array([ztop(x) for x in W_[:, 0]]) - W_[:, 2]) / 0.07, 0, 1))
    W_[:, 1] *= 0.72 + 0.28 * edge ** 0.5
    W_[:, 0] += 0.012 * vnoise(W_, sd, 7.0) * (1 - edge); V[n0:] = W_; m.V = V.tolist()
    if kind != 'Broken':                                        # a cross cut in relief, nearly weathered away
        zc = H * 0.62
        m.block([-0.03, -T / 2 - 0.008, zc - 0.17], [0.03, -T / 2 + 0.02, zc + 0.13], 0, T_BOULDER, 0.008, 0.003, tag=TAG_STONE)
        m.block([-0.11, -T / 2 - 0.008, zc + 0.01], [0.11, -T / 2 + 0.02, zc + 0.065], 0, T_BOULDER, 0.008, 0.003, tag=TAG_STONE)
    lean = {'Round': (-0.07, 0.03), 'Pointed': (0.05, -0.05), 'Broken': (-0.03, 0.09)}[kind]
    m.xform_since(n0, np.array(Matrix.Rotation(lean[0], 4, 'X') @ Matrix.Rotation(lean[1], 4, 'Y')))
    if kind == 'Broken':                                        # the head of the stone lies where it fell, face down, and a skull has worked up out of the grave
        n1 = len(m.V)
        m.slab(-hw, hw, 0.0, 0.42, -T / 2, T / 2, 0, T_BOULDER, nx=10, nz=6, relief=0.012, ztop=lambda x: 0.42 - 0.2 * (abs(x) / hw) ** 2.2, tag=TAG_SHEET)
        m.xform_since(n1, np.array(Matrix.Translation((0.25, -0.62, 0.05)) @ Matrix.Rotation(0.5, 4, 'Z') @ Matrix.Rotation(math.radians(-83), 4, 'X')))
        n2 = len(m.V); skull(m, 3)
        m.xform_since(n2, np.array(Matrix.Translation((-0.42, -0.42, -0.03)) @ Matrix.Rotation(0.5, 4, 'Z') @ Matrix.Rotation(-0.5, 4, 'X')))
    mound2(m, 0.05, -0.78, 0.5, 0.92, 0.17, 2, 4.0, TAG_EARTH + 2, sd)                     # the grave mound, half turfed over
    mound2(m, 0.0, 0.0, 0.5, 0.26, 0.06, 2, 4.0, TAG_EARTH + 1, sd + 1)
    m.ucx = [([-hw, -T / 2 - 0.04, 0], [hw, T / 2 + 0.04, H])]


# ---------------------------------------------------------------- candle
def candle(m):
    """tallow candle on a forged pricket stick: dished foot, stem with a knop, drip pan; the candle guttered, with runs of wax"""
    r = m.rng
    lathe(m, [(0, 0.0), (0.085, 0.0), (0.097, 0.004), (0.1, 0.012), (0.09, 0.018), (0.05, 0.024), (0.02, 0.034), (0.012, 0.05), (0.011, 0.1), (0.022, 0.112), (0.024, 0.122), (0.012, 0.134), (0.011, 0.2),
              (0.03, 0.212), (0.06, 0.218), (0.066, 0.232), (0.062, 0.236), (0.05, 0.226), (0.02, 0.224), (0, 0.224)], 4, T_IRON, n=18, tag=TAG_METAL, wob=0.015)
    m.metal_b = 0.15
    H = 0.45; zt = H - 0.012
    prof = [(0, 0.222), (0.021, 0.222), (0.0235, 0.23), (0.023, 0.3), (0.0225, 0.38), (0.022, zt - 0.02), (0.0235, zt - 0.006), (0.022, zt), (0.016, zt - 0.004), (0.008, zt - 0.012), (0, zt - 0.014)]

    def gut(P):
        P = P.copy(); top = np.clip((P[:, 2] - (zt - 0.03)) / 0.03, 0, 1); ang = np.arctan2(P[:, 1], P[:, 0])
        P[:, 2] -= 0.012 * top * (0.5 + 0.5 * np.cos(ang - 0.8))                         # burnt down on one side
        return P
    lathe(m, prof, 3, T_PL, n=16, tag=TAG_WAX, wob=0.02, deform=gut)
    for (a, l, rr) in ((0.8, 0.14, 0.006), (1.5, 0.07, 0.005), (3.9, 0.19, 0.0065), (5.2, 0.05, 0.0045)):       # runs of wax, each ending in a bead; one reaches the pan
        q = 0.0235; x, y = q * math.cos(a), q * math.sin(a)
        m.tube([[x * 0.9, y * 0.9, zt - 0.012], [x * 1.05, y * 1.05, zt - 0.03], [x * 1.08, y * 1.08, zt - l * 0.6], [x * 1.12, y * 1.12, zt - l], [x * 1.0, y * 1.0, zt - l - rr]],
               [rr * 0.6, rr, rr * 0.85, rr * 1.35, rr * 0.4], 3, sides=6, tag=TAG_WAX, smooth=True, tile=T_PL, vrange=(0.5, 0.05))
    lathe(m, [(0, 0.224), (0.036, 0.224), (0.04, 0.229), (0.03, 0.234), (0, 0.236)], 3, T_PL, n=12, tag=TAG_WAX, wob=0.1, c=(0.012, 0.008))      # the puddle in the pan
    m.tube([[0, 0, zt - 0.016], [0.001, 0.0, zt + 0.004], [0.004, 0.001, zt + 0.012]], [0.0018, 0.0016, 0.0012], 4, sides=5, tag=TAG_METAL, smooth=True)      # wick
    m.hulls = [[[0.1 * math.cos(t), 0.1 * math.sin(t), 0.0] for t in np.linspace(0, 2 * math.pi, 7)[:-1]] + [[0.03 * math.cos(t), 0.03 * math.sin(t), H] for t in np.linspace(0, 2 * math.pi, 7)[:-1]]]


# ---------------------------------------------------------------- fireplace, basket, pie, potion, counter
def fireplace(m, W=4.0, D=1.54, H=4.14):
    """the cottage hearth: fieldstone jambs and breast in two stages, an oak bressummer over a 1.6 m opening, a sooted fireback,
    flagged hearth, a pair of fire dogs with three part-burnt logs on a bed of ash, an iron crane with a hook"""
    r = m.rng; yb = D / 2; yf = -0.32; ow = 0.8; jw = 1.45; zo = 1.5
    for sx in (-1, 1):                                           # jambs
        xa, xb = (-jw, -ow) if sx < 0 else (ow, jw)
        m.slab(xa, xb, 0.0, zo, yf, yb, 0, T_STONE, relief=0.03, tag=TAG_SHEET)
        z = 0.0; i = 0
        while z < zo - 1e-6:                                     # dressed stones up the opening and the outer corners
            h = min(float(r.uniform(0.26, 0.4)), zo - z)
            if zo - (z + h) < 0.15:
                h = zo - z
            for (xe, dr_) in ((sx * ow, sx), (sx * jw, -sx)):
                l = (0.42 if i % 2 == 0 else 0.26) + r.normal(0, 0.02)
                lo = [min(xe - dr_ * 0.03, xe + dr_ * l), yf - 0.035 + r.normal(0, 0.008), z + 0.005]; hi = [max(xe - dr_ * 0.03, xe + dr_ * l), yf + 0.42, z + h - 0.005]
                m.block(lo, hi, 3, T_BOULDER * 0.5, 0.026, 0.008, tag=TAG_STONE)
            z += h; i += 1
    m.slab(-ow, ow, 0.0, zo + 0.3, yb - 0.25, yb, 0, T_STONE, relief=0.02, tag=TAG_SHEET)                   # fireback
    m.slab(-jw, jw, zo + 0.26, 2.75, yf + 0.06, yb, 0, T_STONE, relief=0.03, tag=TAG_SHEET)                 # breast
    m.slab(-0.85, 0.85, 2.75, H, yf + 0.3, yb, 0, T_STONE, relief=0.03, tag=TAG_SHEET)                      # stack
    for sx in (-1, 1):                                           # tumbled-in shoulders gathering the breast to the stack, each under three sloping cover stones
        m.prism([(sx * 0.85, 2.74), (sx * jw, 2.74), (sx * 0.85, 3.4)], yf + 0.07, yb, 0, T_STONE, tag=TAG_SHEET, axis=1)
        for k in range(3):
            t0, t1 = k / 3.0, (k + 1) / 3.0
            pa = np.array([sx * (jw - (jw - 0.85) * t0), 2.74 + 0.66 * t0]); pb = np.array([sx * (jw - (jw - 0.85) * t1), 2.74 + 0.66 * t1]); c_ = (pa + pb) / 2; L_ = float(np.linalg.norm(pb - pa)) + 0.04
            m.block([c_[0] - L_ / 2, yf + 0.03, c_[1] - 0.01], [c_[0] + L_ / 2, yb, c_[1] + 0.075], 3, T_BOULDER * 0.5, 0.02, 0.008, tag=TAG_STONE, rot=(0, 0, sx * math.atan2(0.66, jw - 0.85)))
    n0 = len(m.V)
    timber(m, [-jw - 0.12, yf - 0.1, zo], [jw + 0.12, yf + 0.24, zo + 0.3], 0.03, 0.012, segs=12)             # the bressummer
    m.block([-jw - 0.2, yf - 0.2, zo + 0.3], [jw + 0.2, yf + 0.1, zo + 0.345], 1, T_TIMBER, 0.008, 0.002, mode='board', board=brd(m), tag=TAG_TOP)       # mantel shelf
    x = -2.0                                                     # hearth flags
    while x < 2.0 - 1e-6:
        l = min(float(r.uniform(0.5, 0.8)), 2.0 - x)
        if 2.0 - (x + l) < 0.25:
            l = 2.0 - x
        for (ya, yb_) in ((-D / 2, -D / 2 + 0.46), (-D / 2 + 0.46, yf + 0.0)):
            m.block([x + 0.005, ya + 0.005, 0.0], [x + l - 0.005, yb_ - 0.005, 0.085 + r.normal(0, 0.005)], 3, T_BOULDER * 0.5, 0.014, 0.004, tag=TAG_STONE)
        x += l
    m.block([-ow, yf, 0.0], [ow, yb - 0.25, 0.06], 3, T_BOULDER * 0.5, 0.01, 0.004, tag=TAG_STONE)            # firebox floor
    mound(m, 0.0, 0.2, 0.55, 0.3, 0.09, 0, T_STONE, TAG_ASH2, int(r.integers(1e6)))                                # ash
    for sx in (-1, 1):                                           # fire dogs
        x0 = sx * 0.3
        m.block([x0 - 0.012, -0.12, 0.06], [x0 + 0.012, 0.42, 0.2], 4, T_IRON, 0.004, 0.001, tag=TAG_METAL)
        m.block([x0 - 0.015, -0.13, 0.06], [x0 + 0.015, -0.1, 0.46], 4, T_IRON, 0.004, 0.001, tag=TAG_METAL)
        m.tube([[x0, -0.115, 0.46], [x0, -0.115, 0.5]], [0.028, 0.02], 4, sides=7, tag=TAG_METAL, smooth=True)
        m.block([x0 - 0.06, -0.14, 0.06], [x0 + 0.06, -0.09, 0.085], 4, T_IRON, 0.004, 0.001, tag=TAG_METAL)
    for (y, z, a, l, rad_) in ((0.08, 0.26, 0.08, 0.95, 0.065), (0.3, 0.25, -0.12, 0.85, 0.055), (0.2, 0.36, 0.3, 0.8, 0.05)):       # logs, burnt through in the middle
        dx, dy = math.cos(a), math.sin(a)
        pts = [[-l / 2 * dx + dy * 0.0, y - l / 2 * dy, z], [-l / 4 * dx, y - l / 4 * dy, z + 0.01], [0, y, z - 0.012], [l / 4 * dx, y + l / 4 * dy, z + 0.005], [l / 2 * dx, y + l / 2 * dy, z]]
        n1 = len(m.V)
        m.tube(pts, [rad_, rad_ * 1.03, rad_ * 0.8, rad_, rad_ * 0.95], 1, sides=8, tag=TAG_TIMBER, smooth=True, rough=0.06)
        V = np.array(m.V); mid = np.abs((V[n1:, 0] * dx + (V[n1:, 1] - y) * dy)) < l * 0.3
        T_ = np.array(m.VT); T_[n1:][mid] = TAG_CHAR; m.VT = T_.tolist()
    pts = [[-ow + 0.06, yb - 0.3, 0.3], [-ow + 0.06, yb - 0.3, 1.25]]                                         # crane: upright, arm, hook
    m.tube(pts, 0.014, 4, sides=6, tag=TAG_METAL, smooth=True)
    m.tube([[-ow + 0.06, yb - 0.3, 1.2], [-0.3, yb - 0.5, 1.2], [0.1, yb - 0.55, 1.18]], [0.012, 0.011, 0.009], 4, sides=6, tag=TAG_METAL, smooth=True)
    m.tube([[-ow + 0.06, yb - 0.3, 0.85], [-0.42, yb - 0.46, 1.2]], 0.008, 4, sides=5, tag=TAG_METAL, smooth=True)
    m.tube([[0.05, yb - 0.55, 1.18], [0.05, yb - 0.55, 0.95], [0.07, yb - 0.55, 0.9], [0.1, yb - 0.55, 0.93]], 0.006, 4, sides=5, tag=TAG_METAL, smooth=True)
    m.fire = (0.0, 0.15, zo, ow); m.metal_b = 0.1
    m.stains = [([0, -D / 2 + 0.3, 0.08], 0.5, 0.5), ([0.0, 0.2, 0.3], 0.75, 0.9)]
    m.ucx = [([-jw, yf, 0], [-ow, yb, zo]), ([ow, yf, 0], [jw, yb, zo]), ([-jw, yf, zo], [jw, yb, 2.75]), ([-0.85, yf + 0.3, 2.75], [0.85, yb, H]), ([-ow, yb - 0.25, 0], [ow, yb, zo]), ([-2.0, -D / 2, 0], [2.0, yf, 0.08])]


def basket(m, a=0.5, b=0.4, H=0.4):
    """oval willow basket with a bow handle: stake-and-strand weave modelled in the wall, a waled foot, a rope-twist border"""
    r = m.rng; nrow = 22; n = 44
    prof = [(0, 0.0), (0.3, 0.0), (0.72, 0.004)]
    for i in range(nrow + 1):
        t = i / nrow; prof.append((0.78 + 0.22 * t ** 0.7, 0.012 + (H - 0.012) * t))
    prof += [(0.97, H - 0.004)] + [(0.75 + 0.21 * (i / 8) ** 0.7, 0.03 + (H - 0.04) * i / 8) for i in range(8, -1, -1)] + [(0.3, 0.022), (0, 0.022)]
    prof = [(q * b, z) for q, z in prof]

    def weave(P):
        P = P.copy(); ang = np.arctan2(P[:, 1], P[:, 0]); rad = np.hypot(P[:, 0], P[:, 1]); row = np.round((P[:, 2] - 0.012) / ((H - 0.012) / nrow))
        wall = (rad > 0.7 * b) & (P[:, 2] > 0.01)
        k = 1 + wall * 0.022 * np.cos(ang * (n / 2) + math.pi * row)
        P[:, 0] *= k * a / b; P[:, 1] *= k
        return P
    lathe(m, prof, 0, 0.35, n=n, tag=TAG_ROPE, deform=weave, vscale=0.4)
    for (zz, rad_, q) in ((H + 0.004, 0.017, 1.0), (0.02, 0.013, 0.8)):                                        # border and foot wale
        pts = [[q * a * math.cos(t), q * b * math.sin(t), zz + 0.004 * math.sin(t * 3)] for t in np.linspace(0, 2 * math.pi, 41)]
        m.tube(pts, rad_, 0, sides=8, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2), shape=[1.0, 0.8] * 4, twist=38.0)
    pts = [[0.01 * math.sin(t * 2), b * 0.98 * math.cos(t), H - 0.03 + 0.3 * math.sin(t) ** 0.8] for t in np.linspace(0, math.pi, 25)]         # bow handle of three rods, wrapped
    m.tube(pts, 0.015, 0, sides=8, tag=TAG_ROPE, smooth=True, tile=0.35, vrange=(0.5, 0.2), shape=[1.0, 0.82] * 4, twist=30.0)
    m.stains = [([0, 0, 0.03], 0.3, 0.5)]; m.rubs = [([0, 0, H + 0.3], 0.15, 0.6)]
    m.hulls = [[[a * math.cos(t), b * math.sin(t), z] for t in np.linspace(0, 2 * math.pi, 9)[:-1] for z in (0.0, H)]]


def pie(m, R=0.245, H=0.115):
    """a raised pie in an earthenware dish: domed crust with a crimped edge, three knife vents, one wedge cut and gone"""
    r = m.rng
    lathe(m, [(0, 0.0), (0.7 * R, 0.0), (0.74 * R, 0.004), (0.9 * R, 0.04), (R, 0.062), (R, 0.07), (0.96 * R, 0.07), (0.86 * R, 0.045), (0.6 * R, 0.02), (0, 0.016)], 0, T_GLAZE, n=28, tag=TAG_CERAMIC, wob=0.008)
    prof = [(0, 0.03), (0.6 * R, 0.03), (0.9 * R, 0.056), (0.975 * R, 0.066), (1.0 * R, 0.076), (0.97 * R, 0.086), (0.9 * R, 0.088), (0.84 * R, 0.084), (0.76 * R, 0.094), (0.6 * R, 0.106), (0.4 * R, 0.113), (0.2 * R, H - 0.001), (0, H)]
    sd = int(r.integers(1e6))

    def crust(P):
        P = P.copy(); ang = np.arctan2(P[:, 1], P[:, 0]); rad = np.hypot(P[:, 0], P[:, 1]); rim = np.clip((rad - 0.82 * R) / (0.15 * R), 0, 1) * (P[:, 2] > 0.06)
        P[:, 2] += 0.005 * rim * np.sin(ang * 12)                                         # thumb crimps
        k = 1 + 0.025 * rim * np.cos(ang * 12)
        P[:, 0] *= k; P[:, 1] *= k
        P[:, 2] += (0.006 * vnoise(P, sd, 18.0) + 0.004 * vnoise(P, sd + 1, 40.0)) * (P[:, 2] > 0.08)       # blistered top
        P[:, 2] -= 0.008 * np.exp(-((P[:, 0] - 0.05) ** 2 + (P[:, 1] + 0.03) ** 2) / 0.004) * (P[:, 2] > 0.09)                # a sunk place where the filling settled
        return P
    lathe(m, prof, 2, T_PL * 0.12, n=72, tag=TAG_WAX, deform=crust, vscale=1.0, maxseg=0.02)
    m.fillcut = (0.6, 0.33)
    m.hulls = [[[R * math.cos(t), R * math.sin(t), z] for t in np.linspace(0, 2 * math.pi, 9)[:-1] for z in (0.0, H * 0.8)]]


def potion(m):
    """round-bellied flask with a long neck and a cork, as sprite 56: 0.16 x 0.36 m"""
    prof = [(0, 0.0), (0.035, 0.0), (0.05, 0.004), (0.072, 0.03), (0.08, 0.07), (0.072, 0.11), (0.05, 0.14), (0.027, 0.165), (0.02, 0.2), (0.019, 0.29), (0.026, 0.3), (0.027, 0.31), (0.02, 0.315), (0, 0.315)]
    lathe(m, prof, 1, T_TIMBER, n=20, tag=TAG_GLASS, wob=0.01)
    lathe(m, [(0, 0.3), (0.017, 0.3), (0.019, 0.33), (0.021, 0.352), (0.016, 0.36), (0, 0.36)], 1, T_TIMBER, n=10, tag=TAG_END, wob=0.03)
    n0 = len(m.V); whip(m, [0, 0, 0.292], 0.022, turns=2.5, rad=0.0025, slot=1, rise=0.01); m.VT[n0:] = [TAG_END] * (len(m.V) - n0)
    m.hulls = [[[0.08 * math.cos(t), 0.08 * math.sin(t), z] for t in np.linspace(0, 2 * math.pi, 7)[:-1] for z in (0.0, 0.14)] + [[0, 0, 0.36]]]


def counter(m, L=3.9, D=0.8, H=1.0):
    """shop counter as sprite 64 frame 2: thick three-board top on five posts, a boarded back, a low shelf, open and dark in front"""
    r = m.rng; th = 0.06
    top_boards(m, -L / 2, L / 2, -D / 2 - 0.05, D / 2, H - th, th, 3)
    xs = np.linspace(-L / 2 + 0.08, L / 2 - 0.08, 5)
    for x in xs:
        leg(m, x, -D / 2 + 0.07, 0.0, H - th, 0.1, taper=1.0)
        leg(m, x, D / 2 - 0.06, 0.0, H - th, 0.08, taper=1.0)
    for k, (za, zb_) in enumerate(((0.05, 0.3), (0.3, 0.52), (0.52, 0.76), (0.76, H - th))):
        board(m, [-L / 2 + 0.02 + r.normal(0, 0.004), D / 2 - 0.022, za + 0.002], [L / 2 - 0.02 + r.normal(0, 0.004), D / 2, zb_ - 0.002], 0.004, 0.0015)
    for sx in (-1, 1):
        for (za, zb_) in ((0.05, 0.36), (0.36, 0.66), (0.66, H - th)):
            board(m, [sx * (L / 2 - 0.02) - 0.011, -D / 2 + 0.12, za + 0.002], [sx * (L / 2 - 0.02) + 0.011, D / 2 - 0.02, zb_ - 0.002], 0.004, 0.0015)
    top_boards(m, -L / 2 + 0.04, L / 2 - 0.04, -D / 2 + 0.1, D / 2 - 0.02, 0.2, 0.025, 2, over=0.0)
    timber(m, [-L / 2 + 0.04, -D / 2 + 0.03, H - th - 0.12], [L / 2 - 0.04, -D / 2 + 0.06, H - th], 0.006, 0.003, segs=10)
    m.block([-L / 2 + 0.03, -D / 2 + 0.12, 0.23], [L / 2 - 0.03, D / 2 - 0.025, H - th - 0.01], 1, T_TIMBER, 0.0, 0.0, tag=TAG_GLASS + 30)
    m.stains = [([0.6, -0.1, H], 0.14, 0.55), ([-1.0, 0.1, H], 0.22, 0.45), ([1.4, 0.0, H], 0.1, 0.6), ([-0.3, -D / 2, 0.1], 1.5, 0.3)]
    m.rubs = [([0, -D / 2 - 0.05, H], 1.2, 0.5), ([-1.2, -D / 2, H], 0.5, 0.4), ([1.3, -D / 2, H], 0.5, 0.4)]
    m.ucx = [([-L / 2, -D / 2 - 0.05, 0], [L / 2, D / 2, H])]



# ---------------------------------------------------------------- light sources asked for by the integrator
def ibar(m, lo, hi, bevel=0.003, rot=None):
    m.block(lo, hi, 3, T_IRON, bevel, 0.0008, tag=TAG_METAL, rot=rot)


def torch_wall(m):
    """wall torch: forged back plate spiked to the wall (the wall plane is y = 0, the torch stands out to -Y), a sooted smoke
    plate above it, a bracket arm ending in a ring, and in the ring a cleft ash stave whose head is bound in pitch-soaked rag"""
    r = m.rng
    ibar(m, [-0.045, -0.008, 0.0], [0.045, 0.0, 0.3], 0.004)                               # back plate
    for zz in (0.035, 0.265):
        m.tube([[0, -0.016, zz], [0, 0.0, zz]], [0.011, 0.008], 3, sides=6, tag=TAG_METAL, smooth=True)
    n0 = len(m.V)
    ibar(m, [-0.075, -0.004, 0.42], [0.075, 0.0, 0.95], 0.003)                              # smoke plate: thin sheet, curled at the top
    V = np.array(m.V); W_ = V[n0:]; W_[:, 1] -= 0.03 * np.clip((W_[:, 2] - 0.8) / 0.15, 0, 1) ** 2; V[n0:] = W_; m.V = V.tolist()
    for (x, z) in ((-0.055, 0.45), (0.055, 0.45), (0.0, 0.76)):
        m.tube([[x, -0.01, z], [x, 0.0, z]], [0.007, 0.005], 3, sides=6, tag=TAG_METAL, smooth=True)
    pts = [[0, -0.008, 0.06], [0, -0.05, 0.075], [0, -0.1, 0.12], [0, -0.125, 0.18]]          # arm, forged square and scrolled up
    m.tube(pts, [0.011, 0.01, 0.009, 0.009], 3, sides=4, tag=TAG_METAL, smooth=False)
    pts = [[0, -0.008, 0.25], [0, -0.06, 0.24], [0, -0.115, 0.22]]
    m.tube(pts, [0.008, 0.007, 0.007], 3, sides=4, tag=TAG_METAL, smooth=False)
    ax = np.array([0.0, -math.sin(0.33), math.cos(0.33)]); c0 = np.array([0.0, -0.135, 0.2]); side = np.array([1.0, 0, 0]); fw = np.cross(ax, side)
    for zc in (0.0, 0.08):                                                                  # two rings holding the stave
        ring_ = [c0 + ax * zc + 0.03 * (math.cos(t) * side + math.sin(t) * fw) for t in np.linspace(0, 2 * math.pi, 15)]
        m.tube(ring_, 0.006, 3, sides=5, tag=TAG_METAL, smooth=True)
    p0 = c0 - ax * 0.16; p1 = c0 + ax * 0.52
    m.tube([p0, p0 + ax * 0.02, c0 + ax * 0.3, p1], [0.014, 0.021, 0.024, 0.022], 1, sides=8, tag=TAG_TIMBER, smooth=True, rough=0.04, shape=[1, 0.9, 1, 0.85, 1, 0.92, 1, 0.88])
    hb = c0 + ax * 0.36                                                                     # the head: a wad of rag bound round in strips, black with pitch, burnt ragged at the top
    prof = [(0, 0.0), (0.03, 0.0), (0.044, 0.02), (0.05, 0.07), (0.052, 0.12), (0.046, 0.17), (0.034, 0.2), (0.02, 0.215), (0, 0.22)]
    n0 = len(m.V); sd = int(r.integers(1e6))

    def lump(P):
        P = P.copy(); ang = np.arctan2(P[:, 1], P[:, 0]); k = 1 + 0.1 * vnoise(P * 30, sd, 1.0) + 0.06 * np.sin(ang * 3 + P[:, 2] * 40)
        P[:, 0] *= k; P[:, 1] *= k; P[:, 2] += 0.012 * np.sin(ang * 4 + 1) * (P[:, 2] > 0.17); return P
    lathe(m, prof, 1, T_TIMBER, n=14, tag=TAG_CHAR, deform=lump, maxseg=0.03)
    pts = []
    for i in range(61):
        a = 2 * math.pi * 6 * i / 60; zz = 0.012 + 0.165 * i / 60; q = 0.046 + 0.007 * math.sin(math.pi * i / 60) + 0.002 * math.sin(i * 1.3)
        pts.append([q * math.cos(a), q * math.sin(a), zz])
    m.tube(pts, 0.0055, 1, sides=6, tag=TAG_CHAR, smooth=True, shape=[1.3, 0.9, 0.7, 1.3, 0.9, 0.7])
    Mh = np.eye(4); Mh[:3, 0] = side; Mh[:3, 1] = fw; Mh[:3, 2] = ax; Mh[:3, 3] = hb
    m.xform_since(n0, Mh)
    m.socket = [round(float(x), 3) for x in (hb + ax * 0.24)]
    m.soot_c = (0.0, 0.0, 0.62); m.metal_b = 0.12
    m.ucx = [([-0.075, -0.33, 0.0], [0.075, 0.0, 0.95])]


def brazier(m):
    """standing fire basket: three forged legs splayed from a collar, a basket of eight hoops-and-staves straps, a pan under it
    for the ash, charcoal heaped in the basket"""
    r = m.rng; H = 0.95; Rb = 0.24
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3; d = np.array([math.cos(a), math.sin(a), 0.0])
        pts = [d * 0.36 + [0, 0, 0.0], d * 0.33 + [0, 0, 0.03], d * 0.16 + [0, 0, 0.4], d * 0.07 + [0, 0, 0.62], d * 0.12 + [0, 0, 0.74], d * 0.2 + [0, 0, H - 0.2]]
        m.tube(pts, [0.016, 0.012, 0.011, 0.011, 0.011, 0.01], 3, sides=4, tag=TAG_METAL, smooth=False, twist=3.0)
        m.block((d * 0.37 - [0.03, 0.03, 0]).tolist()[:2] + [0.0], (d * 0.37 + [0.03, 0.03, 0]).tolist()[:2] + [0.012], 3, T_IRON, 0.004, 0.001, tag=TAG_METAL, rot=(a, 0, 0))
    for (zz, q, rr) in ((0.62, 0.075, 0.009), (0.4, 0.165, 0.007)):                                  # collar and a stretcher ring
        m.tube([[q * math.cos(t), q * math.sin(t), zz] for t in np.linspace(0, 2 * math.pi, 19)], rr, 3, sides=5, tag=TAG_METAL, smooth=True)
    lathe(m, [(0, H - 0.26), (0.2, H - 0.26), (0.215, H - 0.25), (0.22, H - 0.235), (0.2, H - 0.238), (0.1, H - 0.25), (0, H - 0.252)], 3, T_IRON, n=18, tag=TAG_METAL, wob=0.02)      # ash pan
    for k in range(10):                                                                           # basket straps, flaring up
        a = 2 * math.pi * k / 10
        pts = [[q * math.cos(a), q * math.sin(a), zz] for (q, zz) in ((0.1, H - 0.235), (0.16, H - 0.2), (0.215, H - 0.1), (Rb, H - 0.01), (Rb + 0.012, H + 0.012))]
        m.tube(pts, 0.0075, 3, sides=4, tag=TAG_METAL, smooth=False)
    for (zz, q) in ((H - 0.2, 0.162), (H - 0.1, 0.218), (H, Rb + 0.004)):
        m.tube([[q * math.cos(t) * (1 + 0.012 * math.sin(3 * t)), q * math.sin(t), zz + 0.004 * math.sin(2 * t)] for t in np.linspace(0, 2 * math.pi, 25)], 0.008, 3, sides=5, tag=TAG_METAL, smooth=True)
    for k in range(34):                                                                           # charcoal
        a = r.uniform(0, 6.28); q = Rb * 0.8 * math.sqrt(r.uniform(0, 1)); zz = H - 0.2 + 0.2 * (1 - (q / Rb) ** 2) * r.uniform(0.3, 1.0) + 0.1 * (q / Rb)
        sz = [float(r.uniform(0.04, 0.085)), float(r.uniform(0.035, 0.06)), float(r.uniform(0.03, 0.05))]
        n0 = len(m.V)
        m.rock([0, 0, 0], sz, 1, T_TIMBER, sub=1, tag=TAG_CHAR, lump=0.25, smooth=False, facets=3)
        m.xform_since(n0, np.array(Matrix.Translation((q * math.cos(a), q * math.sin(a), zz)) @ Matrix.Rotation(float(r.uniform(0, 3)), 4, 'Z') @ Matrix.Rotation(float(r.uniform(0, 3)), 4, 'X')))
    lathe(m, [(0, H - 0.25), (0.19, H - 0.25), (0.2, H - 0.2), (0.21, H - 0.12), (0.15, H - 0.06), (0, H - 0.04)], 1, T_TIMBER, n=12, tag=TAG_CHAR, wob=0.03)      # the bed of the fire under the lumps
    m.socket = [0.0, 0.0, round(H + 0.02, 3)]; m.metal_b = 0.1
    m.hulls = [[[0.37 * math.cos(t), 0.37 * math.sin(t), 0.0] for t in np.linspace(0, 2 * math.pi, 7)[:-1]] + [[0.26 * math.cos(t), 0.26 * math.sin(t), H] for t in np.linspace(0, 2 * math.pi, 7)[:-1]]]


def lantern(m):
    """hanging lantern: riveted sheet-iron frame with four horn panes, a pierced conical cap, a ring and six links of chain to a
    ceiling hook. Origin at the hook (it hangs down -Z)"""
    r = m.rng; w = 0.085; zb = -0.78; zt = -0.5
    rot45 = lambda P: np.c_[(P[:, 0] - P[:, 1]) * 0.7071, (P[:, 0] + P[:, 1]) * 0.7071, P[:, 2]]
    lathe(m, [(0, zb), (w * 1.45, zb), (w * 1.5, zb + 0.008), (w * 1.45, zb + 0.016), (0, zb + 0.016)], 3, T_IRON, n=4, tag=TAG_METAL, smooth=False, deform=rot45)       # base tray (square: 4 sides)
    lathe(m, [(0, zt - 0.006), (w * 1.5, zt - 0.006), (w * 1.55, zt), (w * 1.1, zt + 0.045), (w * 0.5, zt + 0.1), (w * 0.3, zt + 0.108), (0, zt + 0.11)], 3, T_IRON, n=4, tag=TAG_METAL, smooth=False, deform=rot45)   # cap
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; x, y = w * 1.42 * math.cos(a), w * 1.42 * math.sin(a)
        m.tube([[x, y, zb + 0.01], [x, y, zt]], 0.0065, 3, sides=4, tag=TAG_METAL, smooth=False)                                  # corner bars
        a2 = k * math.pi / 2; nx_, ny_ = math.cos(a2), math.sin(a2); tx, ty = -ny_, nx_; d = w * 0.98
        P4 = [[d * nx_ - tx * w * 0.95, d * ny_ - ty * w * 0.95, zb + 0.02], [d * nx_ + tx * w * 0.95, d * ny_ + ty * w * 0.95, zb + 0.02], [d * nx_ + tx * w * 0.95, d * ny_ + ty * w * 0.95, zt - 0.01], [d * nx_ - tx * w * 0.95, d * ny_ - ty * w * 0.95, zt - 0.01]]
        Pi = [[p[0] - nx_ * 0.003, p[1] - ny_ * 0.003, p[2]] for p in P4]
        m.add(P4 + Pi, [[0, 1, 2, 3], [7, 6, 5, 4], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]], 1, T_TIMBER, tag=TAG_GLASS)                   # horn pane
        m.tube([[d * nx_ * 1.01, d * ny_ * 1.01, zb + 0.02], [d * nx_ * 1.01, d * ny_ * 1.01, zt - 0.01]], 0.004, 3, sides=4, tag=TAG_METAL, smooth=False)   # glazing bar
    lathe(m, [(0, zb + 0.016), (0.014, zb + 0.016), (0.014, zb + 0.09), (0.008, zb + 0.094), (0, zb + 0.094)], 2, T_PL, n=8, tag=TAG_WAX)                 # the candle stub inside
    zz = zt + 0.11
    for k in range(7):                                                                           # ring and chain
        tw = (k % 2) * math.pi / 2; c_ = zz + 0.028 + k * 0.05; lh = 0.034
        pts = [[0.012 * math.cos(t) * math.cos(tw), 0.012 * math.cos(t) * math.sin(tw), c_ + lh * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 11)]
        m.tube(pts, 0.004, 3, sides=5, tag=TAG_METAL, smooth=True)
    m.tube([[0, 0, -0.07], [0, 0, -0.03], [0.02, 0, -0.012], [0.03, 0, -0.03], [0.02, 0, -0.05]], 0.005, 3, sides=5, tag=TAG_METAL, smooth=True)             # hook
    ibar(m, [-0.03, -0.03, -0.006], [0.03, 0.03, 0.0], 0.002)
    m.socket = [0.0, 0.0, round(zb + 0.115, 3)]; m.metal_b = 0.12
    m.ucx = [([-0.13, -0.13, zb], [0.13, 0.13, zt + 0.11])]


# ---------------------------------------------------------------- coordinator priority list: post, sideboard, pillar, rubble, bottle shelf
def support_post(m, H=2.65):
    """roof post as sprite 87 frame 10: a chamfered oak post on a dressed stone pad, a cross head and two braces pegged to it"""
    r = m.rng
    for k, (w_, za, zb_) in enumerate(((0.42, 0.0, 0.2), (0.34, 0.2, 0.52))):
        for sx in (-1, 1):
            m.block([min(0, sx * w_ / 2), -w_ / 2 + r.normal(0, 0.006), za + 0.004], [max(0, sx * w_ / 2), w_ / 2 + r.normal(0, 0.006), zb_ - 0.004], 3, T_BOULDER * 0.5, 0.02, 0.006, tag=TAG_STONE, rot=(0, 0, 0))
    leg(m, 0, 0, 0.5, H, 0.17, taper=1.0)
    timber(m, [-0.58, -0.075, H - 0.5], [0.58, 0.075, H - 0.34], 0.012, 0.004)
    for sx in (-1, 1):
        bar(m, (sx * 0.085, H - 1.05), (sx * 0.5, H - 0.5), 0.1, -0.05, 0.05, slot=1, tag=TAG_TIMBER, tile=T_TIMBER)
        for (x, z) in ((sx * 0.14, H - 0.97), (sx * 0.45, H - 0.56)):
            m.tube([[x, -0.062, z], [x, -0.04, z]], [0.011, 0.01], 1, sides=6, tag=TAG_END, smooth=False)
    m.stains = [([0, 0, 0.6], 0.3, 0.5)]; m.rubs = [([0, -0.09, 1.2], 0.3, 0.4)]
    m.ucx = [([-0.21, -0.21, 0], [0.21, 0.21, 0.52]), ([-0.09, -0.09, 0.52], [0.09, 0.09, H])]


def sideboard(m, L=2.35, W=1.42, H=0.92):
    """the heavy side table of sprite 87 frames 1 and 7: a five-board top, four square legs and deep plank aprons all round"""
    r = m.rng; th = 0.05; lx, ly = L / 2 - 0.1, W / 2 - 0.1
    top_boards(m, -L / 2, L / 2, -W / 2, W / 2, H - th, th, 5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg(m, sx * lx, sy * ly, 0.0, H - th, 0.1, taper=0.85)
    for sy in (-1, 1):
        for (za, zb_) in ((H - th - 0.2, H - th), (H - th - 0.4, H - th - 0.2)):
            board(m, [-lx + 0.05, sy * ly - 0.012, za + 0.002], [lx - 0.05, sy * ly + 0.012, zb_ - 0.002], 0.004, 0.0015)
    for sx in (-1, 1):
        for (za, zb_) in ((H - th - 0.2, H - th), (H - th - 0.4, H - th - 0.2)):
            board(m, [sx * lx - 0.012, -ly + 0.05, za + 0.002], [sx * lx + 0.012, ly - 0.05, zb_ - 0.002], 0.004, 0.0015)
        timber(m, [sx * lx - 0.02, -ly + 0.05, 0.14], [sx * lx + 0.02, ly - 0.05, 0.2], 0.008, 0.003)
    m.stains = [([0.4, -0.2, H], 0.13, 0.55), ([-0.6, 0.3, H], 0.2, 0.45), ([0, -ly, 0.5], 0.8, 0.25)]
    m.rubs = [([0, -W / 2, H], 0.6, 0.5), ([0.5, W / 2, H], 0.4, 0.4)]
    m.ucx = [([-L / 2, -W / 2, 0], [L / 2, W / 2, H])]


def column(m, cx, cy, z0, z1, rad, slot=0):
    """a column of three or four drums, each a little out of true, with a swelling shaft, a necking and a square abacus"""
    r = m.rng; z = z0; n = 4; hd = (z1 - z0 - 0.3) / n
    lathe(m, [(0, z0), (rad * 1.25, z0), (rad * 1.3, z0 + 0.03), (rad * 1.22, z0 + 0.09), (rad * 1.05, z0 + 0.13), (0, z0 + 0.13)], slot, T_BOULDER, n=14, tag=TAG_STONE, wob=0.015, c=(cx, cy))
    z = z0 + 0.13
    for k in range(n):
        q0 = rad * (1.0 - 0.1 * k / n) * (1 + r.normal(0, 0.012)); q1 = rad * (1.0 - 0.1 * (k + 1) / n) * (1 + r.normal(0, 0.012))
        lathe(m, [(0, z + 0.004), (q0 * 0.96, z + 0.004), (q0, z + 0.02), (q1, z + hd - 0.02), (q1 * 0.96, z + hd - 0.004), (0, z + hd - 0.004)], slot, T_BOULDER, n=14, tag=TAG_SHEET if k % 2 else TAG_STONE, wob=0.02,
              c=(cx + r.normal(0, 0.006), cy + r.normal(0, 0.006)), maxseg=0.22)
        z += hd
    lathe(m, [(0, z), (rad * 0.92, z), (rad * 1.0, z + 0.03), (rad * 1.28, z + 0.1), (rad * 1.3, z + 0.12), (0, z + 0.12)], slot, T_BOULDER, n=14, tag=TAG_STONE, wob=0.015, c=(cx, cy))
    m.block([cx - rad * 1.4, cy - rad * 1.4, z + 0.12], [cx + rad * 1.4, cy + rad * 1.4, z1], slot, T_BOULDER * 0.5, 0.02, 0.006, tag=TAG_STONE)


def dungeon_pillar(m):
    """twin columns on a common plinth (sprite 80 frames 27, 28): 1.0 x 0.55 x 2.4 m"""
    r = m.rng
    for sx in (-1, 1):
        m.block([min(0, sx * 0.52), -0.3, 0.0], [max(0, sx * 0.52), 0.3, 0.2 + r.normal(0, 0.004)], 0, T_BOULDER * 0.5, 0.025, 0.008, tag=TAG_STONE)
        m.block([min(0, sx * 0.46) , -0.26, 0.2], [max(0, sx * 0.46), 0.26, 0.34], 0, T_BOULDER * 0.5, 0.02, 0.006, tag=TAG_STONE)
        column(m, sx * 0.23, 0.0, 0.34, 2.4, 0.17)
    m.rock([0.35, -0.38, 0.05], [0.2, 0.14, 0.1], 0, T_BOULDER * 0.5, sub=2, tag=TAG_STONE, lump=0.3)                 # a spall fallen from the plinth
    m.ucx = [([-0.52, -0.3, 0], [0.52, 0.3, 2.4])]


def rubble_pile(m):
    """fallen masonry (sprite 80 frame 23): squared blocks and broken stone heaped over a low mound of mortar dust, 2.1 x 1.2 x 0.45 m"""
    r = m.rng
    mound2(m, 0.0, 0.0, 1.05, 0.6, 0.2, 1, 4.0, TAG_EARTH, int(r.integers(1e6)))
    for k in range(46):
        u = r.uniform(-1, 1); v = r.uniform(-1, 1)
        if u * u + v * v > 1:
            continue
        x, y = u * 0.95, v * 0.52; zz = 0.2 * (1 - (u * u + v * v)) + 0.02
        big = r.uniform() < 0.3; s_ = r.uniform(0.16, 0.34) if big else r.uniform(0.06, 0.15)
        n0 = len(m.V)
        if big:
            m.block([-s_ * 0.7, -s_ * 0.45, -s_ * 0.3], [s_ * 0.7, s_ * 0.45, s_ * 0.3], 0, T_BOULDER * 0.5, 0.02, 0.012, tag=TAG_STONE)
        else:
            m.rock([0, 0, 0], [s_ * 1.3, s_, s_ * 0.8], 0, T_BOULDER * 0.5, sub=2, tag=TAG_SHEET, lump=0.3, facets=5)
        m.xform_since(n0, np.array(Matrix.Translation((x, y, zz + s_ * 0.25)) @ Matrix.Rotation(float(r.uniform(0, 6.3)), 4, 'Z') @ Matrix.Rotation(float(r.normal(0, 0.45)), 4, 'X') @ Matrix.Rotation(float(r.normal(0, 0.35)), 4, 'Y')))
    V = np.array(m.V); V[:, 2] = np.maximum(V[:, 2], -0.02); m.V = V.tolist()
    m.hulls = [[[sx * 0.95, sy * 0.5, 0.0] for sx in (-1, 1) for sy in (-1, 1)] + [[sx * 0.5, sy * 0.25, 0.42] for sx in (-1, 1) for sy in (-1, 1)]]


BOTTLES = [[(0, 0.0), (0.05, 0.0), (0.062, 0.01), (0.07, 0.06), (0.06, 0.13), (0.03, 0.17), (0.02, 0.25), (0.026, 0.262), (0.02, 0.27), (0, 0.27)],
           [(0, 0.0), (0.04, 0.0), (0.085, 0.03), (0.095, 0.08), (0.075, 0.14), (0.03, 0.19), (0.022, 0.3), (0.03, 0.31), (0.022, 0.32), (0, 0.32)],
           [(0, 0.0), (0.045, 0.0), (0.05, 0.01), (0.05, 0.2), (0.03, 0.25), (0.022, 0.33), (0.028, 0.342), (0.02, 0.35), (0, 0.35)]]


def shelf_bottles(m, L=3.85, H=2.9, D=0.42):
    """the apothecary wall of sprite 64 frame 1: a boarded dresser base and three shelves on a plank back, set with glazed bottles
    in blue, red and green"""
    r = m.rng; hx = L / 2
    for k in range(8):                                           # plank back
        za, zb_ = 0.02 + k * (H - 0.02) / 8, 0.02 + (k + 1) * (H - 0.02) / 8
        board(m, [-hx + r.normal(0, 0.004), D / 2 - 0.025, za + 0.002], [hx + r.normal(0, 0.004), D / 2, zb_ - 0.002], 0.004, 0.0015)
    for sx in (-1, 1):
        board(m, [sx * hx - (0.035 if sx > 0 else 0.0), -D / 2 + 0.02, 0.0], [sx * hx + (0.0 if sx > 0 else 0.035), D / 2 - 0.025, H], 0.006, 0.002)
    for k in range(4):                                           # dresser front
        za, zb_ = 0.04 + k * 0.24, 0.04 + (k + 1) * 0.24
        board(m, [-hx + 0.035, -D / 2, za + 0.002], [hx - 0.035, -D / 2 + 0.024, zb_ - 0.002], 0.004, 0.0015)
    zs = (1.02, 1.62, 2.2)
    for zz in zs:
        top_boards(m, -hx + 0.03, hx - 0.03, -D / 2 - (0.03 if zz == zs[0] else 0.0), D / 2 - 0.025, zz - 0.04, 0.04, 1, over=0.0)
        for x in np.linspace(-hx + 0.6, hx - 0.6, 4):
            if zz != zs[0]:
                bar(m, (D / 2 - 0.03, zz - 0.22), (-D / 2 + 0.06, zz - 0.04), 0.05, x - 0.015, x + 0.015, slot=1, tag=TAG_TIMBER, tile=T_TIMBER) if False else m.block([x - 0.015, -D / 2 + 0.08, zz - 0.2], [x + 0.015, D / 2 - 0.025, zz - 0.04], 1, T_TIMBER, 0.004, 0.001, mode='board', board=brd(m), tag=TAG_TIMBER)
        x = -hx + 0.28
        while x < hx - 0.2:
            k = int(r.integers(3)); sc_ = float(r.uniform(0.95, 1.3)); slot = [0, 2, 0, 4, 2, 0][int(r.integers(6))]
            y = float(r.uniform(-0.08, 0.06))
            lathe(m, [(a * sc_, zz + b * sc_) for a, b in BOTTLES[k]], slot, T_GLAZE, n=10, tag=TAG_CERAMIC, wob=0.015, c=(x, y))
            m.tube([[x, y, zz + BOTTLES[k][-1][1] * sc_ - 0.004], [x, y, zz + BOTTLES[k][-1][1] * sc_ + 0.018]], [0.014 * sc_, 0.016 * sc_], 1, sides=6, tag=TAG_END, smooth=True)     # cork
            x += float(r.uniform(0.3, 0.46))
    m.stains = [([0, -D / 2, 0.3], 1.5, 0.3)]; m.rubs = [([0.5, -D / 2, 1.02], 0.8, 0.4)]; m.axis = (0.0, 1000.0)
    m.ucx = [([-hx, -D / 2 - 0.03, 0], [hx, D / 2, H])]


# ---------------------------------------------------------------- modules
def prop_modules(rows):
    out = []

    def want(name):
        return not ARGS or any(a in name for a in ARGS)

    def mk(name, cls, slots, kind='indoor'):
        m = Mod2(name, 1, 1, rows, cls, 'Props'); m.slots = list(slots); m.streak_src = []; m.streak_w = []
        m.floor0 = False; m.paint.append(prop_paint(m, kind)); m.lod_ratio = (0.5, 0.22); m.part = []; m._pid = 1
        a0, u0 = m.add, m.add_uv

        def track(fn):
            def g(*a, **k):
                n0 = len(m.V)
                if len(m.part) < n0:
                    m.part += [m._pid] * (n0 - len(m.part)); m._pid += 1
                fn(*a, **k); m.part += [m._pid] * (len(m.V) - len(m.part)); m._pid += 1
            return g
        m.add, m.add_uv = track(a0), track(u0); return m

    def rec(m, fams, sup, note, **k):
        used = sorted(set(m.FM)); m.FM = [used.index(i) for i in m.FM]; m.slots = [m.slots[i] for i in used]
        V = np.array(m.V); V[:, 2] -= V[:, 2].min() if k.pop('drop', True) else 0.0; m.V = V.tolist()
        out.append(dict(m=m, families=fams, supersedes=sup, dresses=note, **k))
    W3 = ('fieldstone', 'oak', 'rope', 'iron')
    if want('Barrel'):
        m = mk('SM_Barrel_Oak_PR', 'prop', W3); barrel(m)
        rec(m, ['173 bonuses/barrels/barel- frame 1', 'barrel'], 'Stonebrook/SM_Barrel_Oak_01 (0.84 x 0.84 x 1.01 m, base_center) and the family binding of class barrel (97 placements)',
            'coopered oak barrel, 0.84 m at the bilge, 1.0 m: twenty separate staves with their own thickness, four driven hoops each with a riveted lap, four-board heads set in the croze, a bung',
            fit={'pivot': 'base centre', 'size': 'same height and bilge as SM_Barrel_Oak_01', 'states': 'the broken frames 2-6 (the barrel being smashed) are not built: keep the existing break effect'})
    if want('Crate'):
        for nm, dims, fam, cnt in (('Large', (0.9, 0.62, 0.55), ['443 items/boxes/boxb1-', 'crate', 'crate_stack'], 21), ('Small', (0.68, 0.5, 0.44), ['444 items/boxes/boxb3-', 'crate_small'], 13)):
            m = mk('SM_Crate_%s_PR' % nm, 'prop', W3); crate(m, *dims)
            rec(m, fam, 'none (class was placeholder, %d placements)' % cnt, 'slatted packing crate %.2f x %.2f x %.2f m: corner posts, three slats a side with open gaps onto a dark interior, four lid boards under two nailed battens, forged nail heads' % dims,
                fit={'pivot': 'base centre', 'stack': 'class crate_stack (11 placements) is one large crate with a small one on top, turned about 20 degrees'})
    if want('Jar'):
        for nm in ('Storage', 'Jug', 'Vase', 'Bowl'):
            J = JARS[nm]
            m = mk('SM_Jar_%s_PR' % nm, 'prop' if nm != 'Bowl' else 'prop_small', (J['slot'], 'oak')); jar(m, nm)
            rec(m, ['448 items/cup/cup- ' + {'Storage': 'frames 5, 9, 12', 'Jug': 'frames 6, 8, 16', 'Vase': 'frames 4, 7, 10, 11, 13-15, 17, 18', 'Bowl': 'frames 1-3'}[nm], 'bowl' if nm == 'Bowl' else 'jar_vase'], 'none (family 448 was placeholder: jar_vase 52, bowl 17 placements)',
                {'Storage': 'wheel-thrown storage jar, 0.51 x 0.74 m, rolled rim, brown glaze', 'Jug': 'two-handled crock, 0.55 x 0.58 m, blue-grey glaze', 'Vase': 'narrow-necked bottle vase, 0.25 x 0.68 m, ox-red glaze', 'Bowl': 'footed dish, 0.42 x 0.17 m'}[nm] +
                '; thrown out of true, hollow to a real inner wall, glaze worn at rim and belly, unglazed foot',
                fit={'pivot': 'base centre', 'colours': 'the sprite frames differ only in glaze colour: swap the material instance (MI_Prop_Glaze_Brown / _Blue / _Red / _Green / _Purple, all in materials.json) per frame', 'sprite_scale': 'frames are 12-22 px wide (0.3-0.55 m at 0.025 m/px)'})
    if want('Sack'):
        m = mk('SM_Sack_Grain_PR', 'prop', ('hessian', 'oak', 'rope')); sack_lying(m)
        rec(m, ['463 items/grain/bag-', 'grain_sack'], 'none (grain_sack placeholder, 19 placements)', 'full grain sack lying on its side, 0.95 x 0.64 x 0.3 m: slumped flat underneath, sewn mouth with nine twine stitches and a loose tail, gusset corners',
            fit={'pivot': 'base centre; mouth to +X', 'colours': 'frames are tan, olive and madder red: MI_Prop_Hessian, MI_Prop_Hessian_Olive, MI_Prop_Hessian_Red'})
        m = mk('SM_FeedSack_Jute_PR', 'prop', ('hessian', 'oak', 'rope')); sack_standing(m)
        rec(m, ['opening cottage (screen 1) feed sacks'], 'Stonebrook/SM_FeedSack_Jute_01 (0.72 x 0.55 x 0.75 m, base_center)', 'feed sack stood on end, 0.72 x 0.56 x 0.75 m: weight settled to the bottom, neck gathered in folds and whipped with twine, a flared ruff above the tie',
            fit={'pivot': 'base centre', 'size': 'as SM_FeedSack_Jute_01'})
    if want('Table'):
        m = mk('SM_Table_Oak_Long_PR', 'prop', W3); table_long(m)
        rec(m, ['87 inside/details/table- frames 3, 5', 'table_long'], 'Stonebrook/SM_Table_Oak_01 (2.65 x 1.50 x 0.906 m, base_center) and the family binding of table_long (7 placements)',
            'oak table 2.65 x 1.5 x 0.905 m: six-board top with uneven ends, square tapered legs, rails pegged into the legs, foot rails and a long stretcher', fit={'pivot': 'base centre', 'size': 'as SM_Table_Oak_01'})
        m = mk('SM_Table_Oak_Round_PR', 'prop', W3); table_round(m)
        rec(m, ['87 inside/details/table- frame 9', 'table_round'], 'none (table_round placeholder, 9 placements)', 'round oak table, 1.6 m across, 0.8 m: seven boards cut to the round on two battens, four tapered legs, crossed stretchers',
            fit={'pivot': 'base centre', 'sprite_scale': 'frame 9 is 65 px (1.6 m) wide'})
    if want('Chair') or want('Bench') or want('Stool'):
        m = mk('SM_Chair_Oak_PR', 'prop', W3); chair(m)
        rec(m, ['chair (19 placements)', 'opening cottage chairs'], 'Stonebrook/SM_Chair_Oak_01 (0.65 x 0.54 x 1.005 m, base_center) and the family binding of chair',
            'joined oak side chair, 0.52 x 0.56 x 1.0 m: raked back legs with a kicked foot, three-board seat, seat rails and stretchers, crest rail and slat, pegged', fit={'pivot': 'base centre; the sitter faces -Y', 'size': 'seat 0.46 m high; 0.13 m narrower than SM_Chair_Oak_01, same height'})
        m = mk('SM_Bench_Oak_PR', 'prop', W3); bench(m)
        rec(m, ['87 inside/details/table- frames 2, 4, 6', 'bench_long', 'bench_short'], 'none (bench_long 6, bench_short 8 placements)', 'plank bench 2.3 x 0.3 x 0.45 m: one thick board on two slab ends with boot notches, through tenons showing in the seat, a stretcher',
            fit={'pivot': 'base centre, along X', 'short': 'bench_short (76 px) is the same bench scaled 0.8 in X, or build bench(L=1.9)'})
        m = mk('SM_Stool_Oak_PR', 'prop_small', W3); stool(m)
        rec(m, ['stool (10 placements)'], 'none', 'three-legged turned stool, 0.36 m seat, 0.45 m', fit={'pivot': 'base centre'})
    if want('Bed'):
        m = mk('SM_Bed_Oak_PR', 'prop', ('fieldstone', 'oak', 'rope', 'linen', 'blanket', 'madder')); bed(m)
        rec(m, ['64 inside/details/inacc- frame 3', 'bed'], 'Stonebrook/SM_Bed_Oak_01 (2.51 x 1.37 x 1.12 m, base_center) and the family binding of bed (16 placements)',
            'oak bed 2.5 x 1.36 x 1.15 m as sprite 64 frame 3: four capped posts, plank head and foot boards, pegged side rails, a sagging straw mattress in linen ticking, a quilted yellow-green blanket hanging over the sides and turned back in a madder roll, one dented pillow',
            fit={'pivot': 'base centre; head to -X', 'size': 'as SM_Bed_Oak_01'})
    if want('Chest'):
        m = mk('SM_Chest_Small_PR', 'prop', ('fieldstone', 'oakred', 'rope', 'iron')); chest(m)
        rec(m, ['175 bonuses/chest/chst1- frame 1', 'chest_small', 'chest_medium', 'chest_large'], 'none (chest_small placeholder, 14 placements)',
            'iron-bound chest 0.85 x 0.5 x 0.57 m, closed: red-stained plank carcase, coopered barrel lid of seven staves, three grey iron straps nailed over lid and body, corner irons, lock plate with hasp, drop handles',
            fit={'pivot': 'base centre; lock faces -Y', 'states': 'closed only: the opening frames 2-6 need the lid as a separate hinged mesh (not built)'})
    if want('Grave'):
        for nm, fr in (('Round', 'frame 1'), ('Pointed', 'frame 3'), ('Broken', 'frame 2')):
            m = mk('SM_Gravestone_%s_PR' % nm, 'prop', ('boulder', 'oak', 'earth', 'bone'), 'outdoor'); gravestone(m, nm)
            rec(m, ['446 items/tomb/tomb- ' + fr, 'gravestone'], 'none (gravestone placeholder, 14 placements)',
                {'Round': 'round-headed headstone 0.8 x 1.05 m, leaning, a cross in worn relief', 'Pointed': 'shouldered pointed headstone 0.66 x 1.2 m', 'Broken': 'headstone snapped across on a slant, its head lying face down on the grave, and a skull worked up out of the mound beside it'}[nm] +
                '; weather-rounded edges, moss from the foot and on the north face, lichen; a turfed grave mound in front (the stone runs 0.35 m into the ground)',
                fit={'pivot': 'ground at the foot of the stone; face to -Y, the grave lies toward -Y'}, drop=False)
    if want('Bones') or want('Skull'):
        m = mk('SM_Skull_PR', 'prop_small', ('bone', 'oak'), 'outdoor'); skull(m, 0)
        rec(m, ['90 lands/details/grave- (skull frames)', 'skull'], 'none (skull placeholder, 13 placements)', 'human skull without the jaw, 0.17 x 0.22 x 0.2 m: cranium, brow ridge, cheek bones, eye sockets and nose as dark hollows, eight upper teeth; earth-stained, lichened',
            fit={'pivot': 'base centre (resting on the palate), faces -Y; tip it on its side for variety'})
        m = mk('SM_Bones_Scatter_PR', 'prop', ('bone', 'oak'), 'outdoor'); bones(m)
        rec(m, ['90 lands/details/grave- (bones frames)', 'bones'], 'none (bones placeholder, 46 placements)', 'scatter of human remains, 0.8 x 0.7 m: a skull on its side, four long bones with knuckled ends, five ribs (one snapped)',
            fit={'pivot': 'ground centre; yaw at random', 'gore': 'kept as the sprite has it: these lie about the graveyards and dungeons'})
    if want('Candle'):
        m = mk('SM_Candle_Iron_PR', 'prop_small', ('fieldstone', 'oak', 'rope', 'tallow', 'iron')); candle(m)
        rec(m, ['opening cottage candles', 'candle'], 'Stonebrook/SM_Candle_Iron_01 (0.2 x 0.2 x 0.45 m, base_center)',
            'tallow candle on a forged iron pricket stick, 0.2 x 0.45 m: dished foot, knopped stem, drip pan with a puddle of wax, the candle guttered down one side with four runs of wax, a charred wick',
            fit={'pivot': 'base centre', 'size': 'as SM_Candle_Iron_01'},
            emissive={'type': 'flame (no flame mesh in the FBX: add the engine flame card or particle)', 'position_m': [0.003, 0.0, 0.455], 'colour_temperature_K': 1850, 'attenuation_radius_m': 3.5, 'intensity_cd': 1.0,
                      'note': 'point light 2 cm above the wick, soft source radius 1 cm, slow flicker 5-10 percent; the wax within 3 cm of the flame should glow (subsurface or a small emissive mask) and is not authored'})
    if want('Fireplace'):
        m = mk('SM_Fireplace_Fieldstone_PR', 'prop_large', ('fieldstone', 'oak', 'rope', 'boulder', 'iron'), 'hearth'); fireplace(m)
        rec(m, ['opening cottage (screen 1) fireplace', '64 inside/details/inacc- frame 5 (fireplace_brick)'], 'Stonebrook/SM_Fireplace_Fieldstone_01 (4.02 x 1.54 x 4.145 m, base_center) and its FiredClay / V2 refinements',
            'fieldstone cottage hearth, 4.0 x 1.54 x 4.14 m: rubble jambs with dressed stones up the opening and corners, an oak bressummer and mantel shelf over a 1.6 x 1.5 m opening, a smoke-blackened fireback and breast, a stack in a second stage with weathered shoulders, a flagged hearth, two iron fire dogs carrying three logs burnt through in the middle on a bed of ash, a swinging crane with a pot hook',
            fit={'pivot': 'base centre of the 4.0 x 1.54 m footprint; opening faces -Y, the back (+Y) stands against the wall', 'size': 'as SM_Fireplace_Fieldstone_01'},
            emissive={'type': 'hearth fire (no flame mesh in the FBX: use the engine fire, sprite seq hearth_fire, on the logs)', 'position_m': [0.0, 0.2, 0.42], 'colour_temperature_K': 1900, 'attenuation_radius_m': 7.0, 'intensity_cd': 60.0,
                      'note': 'point light among the logs with a 15 cm soft source radius, flicker 10-20 percent at 4-9 Hz; a second dim red light (1200 K, 2 m radius) on the ash bed sells the embers; the logs carry no emissive ember mask'})
    if want('Basket'):
        m = mk('SM_Basket_Wicker_PR', 'prop', ('wicker', 'oak')); basket(m)
        rec(m, ['opening cottage basket', 'basket_wicker'], 'Stonebrook/SM_Basket_Wicker_01 (1.14 x 0.94 x 0.67 m, base_center)',
            'oval willow basket 1.0 x 0.8 x 0.7 m with a bow handle: the stake-and-strand weave is modelled in the wall (22 rows over 22 stakes), waled foot, twisted border', fit={'pivot': 'base centre', 'size': '0.14 m smaller in plan than SM_Basket_Wicker_01, same height over the handle; empty'})
    if want('Pie'):
        m = mk('SM_Pie_Rustic_PR', 'prop_small', ('glaze_brown', 'oak', 'crust'), 'pie'); pie(m)
        rec(m, ['opening cottage pie', '421 items/food/food- (food_pie)'], 'Stonebrook/SM_Pie_Rustic_01 (0.49 x 0.49 x 0.12 m, base_center)',
            'raised pie in a brown earthenware dish, 0.49 m across: blistered domed crust with a thumb-crimped edge, whole', fit={'pivot': 'base centre', 'size': 'as SM_Pie_Rustic_01'})
    if want('Potion'):
        m = mk('SM_Potion_Flask_PR', 'prop_small', ('fieldstone', 'glass_red', 'oak', 'rope')); potion(m)
        rec(m, ['56 bonuses/bottles/botl-r', 'potion_red', 'potion_purple', 'potion_blue'], 'none (potion pickups placeholder: red 15, purple 11, blue 9 placements)',
            'round-bellied glass flask with a long neck, a cork and a twine tie, 0.16 x 0.36 m', fit={'pivot': 'base centre', 'colours': 'MI_Prop_PotionGlass_Red / _Purple / _Blue (the opaque dark-glass switch of the kit material, tinted): swap per pickup', 'scale': 'the pickup sprite is 19 x 52 px, drawn large for visibility: scale the mesh 1.5-2x as a pickup'},
            emissive={'type': 'optional pickup glow', 'position_m': [0, 0, 0.07], 'colour_temperature_K': None, 'colour_linear': [1.0, 0.08, 0.05], 'attenuation_radius_m': 0.8, 'intensity_cd': 0.3, 'note': 'only if pickups are meant to glow; the glass is opaque in this material'})
    if want('Counter'):
        m = mk('SM_Counter_Oak_PR', 'prop_large', W3); counter(m)
        rec(m, ['64 inside/details/inacc- frame 2', 'counter_wood'], 'none (counter_wood placeholder, 22 placements)', 'shop counter 3.9 x 0.85 x 1.0 m: three-board top 6 cm thick on five front posts, boarded back and ends, a low shelf, open in front',
            fit={'pivot': 'base centre; the open (shopkeeper) side faces -Y as the sprite shows it', 'sprite_scale': 'frame 2 is 156 px (3.9 m) wide'})
    if want('SM_Prop_'):
        def light(pos, K, rad, cd, note):
            return {'type': 'flame, done in engine (no flame mesh in the FBX)', 'flame_socket_m': pos, 'position_m': pos, 'colour_temperature_K': K, 'attenuation_radius_m': rad, 'intensity_cd': cd, 'note': note}
        m = mk('SM_Prop_Torch_Wall_01', 'prop', W3, 'torch'); torch_wall(m)
        rec(m, ['wall torch / sconce (integrator light sources with no visible source)', 'island_torch (the wall-mounted uses)'], 'none (new; asked for by the Unreal integrator)',
            'wall torch, 0.15 x 0.33 x 0.95 m: forged back plate on two spikes, a sheet-iron smoke plate above it curled at the top and blackened, a square bracket arm with two rings holding a cleft stave at 19 degrees from the wall, its head a wad of rag bound in six turns of strip, black with pitch',
            fit={'pivot': 'on the wall plane (y = 0) at the foot of the back plate, centred in x; the torch stands out to -Y; mount with the origin about 1.45 m above the floor', 'socket': 'flame socket (mesh space, metres, Z up, before the Unreal front flip): %s, on top of the head; the flame leans 19 degrees out from the wall' % m.socket},
            emissive=light(m.socket, 1900, 6.0, 18.0, 'point light 10 cm above the socket, soft radius 5 cm, flicker 10-25 percent at 3-9 Hz; the smoke plate is authored sooted so no decal is needed on it; a wall soot decal above 0.95 m is the integrator\'s'), drop=False)
        m = mk('SM_Prop_Brazier_Standing_01', 'prop', W3, 'torch'); brazier(m)
        rec(m, ['standing brazier (integrator light sources)', 'small_fire_fx / fire_fx hosts'], 'none (new)',
            'standing fire basket, 0.75 x 0.75 x 0.97 m: three square forged legs with flattened feet, twisted, gathered in a collar with a stretcher ring, a basket of ten straps on three hoops over an ash pan, heaped with thirty-odd lumps of charcoal',
            fit={'pivot': 'base centre', 'socket': 'flame socket: %s, on top of the coals' % m.socket},
            emissive=light(m.socket, 1800, 7.0, 45.0, 'point light 15 cm above the socket, soft radius 12 cm, flicker 10-20 percent; add a dim red light (1200 K, 1.5 m) inside the basket for the embers; the charcoal has no ember emissive mask'))
        m = mk('SM_Prop_Candle_Holder_01', 'prop_small', ('fieldstone', 'oak', 'rope', 'tallow', 'iron')); candle(m)
        rec(m, ['candle on a holder (integrator light sources)', 'opening cottage candles'], 'Stonebrook/SM_Candle_Iron_01 (same mesh as SM_Candle_Iron_PR under the name the integrator asked for)',
            'tallow candle on a forged iron pricket stick, 0.2 x 0.45 m (identical to SM_Candle_Iron_PR)', fit={'pivot': 'base centre', 'socket': 'flame socket: [0.003, 0.0, 0.452] (top of the wick)'},
            emissive=light([0.003, 0.0, 0.452], 1850, 3.5, 1.0, 'point light 2 cm above the wick, soft radius 1 cm, slow flicker 5-10 percent'))
        m = mk('SM_Prop_Lantern_Hanging_01', 'prop', ('fieldstone', 'horn', 'tallow', 'iron'), 'torch'); lantern(m)
        rec(m, ['hanging lantern (integrator light sources)'], 'none (new)',
            'hanging lantern, 0.26 x 0.26 x 0.78 m with its chain: riveted iron tray and pyramid cap, four corner bars, four horn panes each with a glazing bar, a candle stub inside, seven links of chain to a ceiling hook and plate',
            fit={'pivot': 'the ceiling plate (top of the hook): the lantern hangs down -Z from the origin; the lantern body spans z = -0.78 to -0.39', 'socket': 'flame socket: %s, inside the body' % m.socket,
                 'panes': 'the panes are the opaque amber switch of MI_Prop_LanternHorn (alpha 0 = glass_tint): give that material an emissive of about 2-4 nits x amber, or swap it for a translucent horn material, so the lantern reads as lit'},
            emissive=light(m.socket, 2000, 5.0, 6.0, 'point light at the socket with shadow casting OFF for the lantern mesh itself (the panes are opaque), soft radius 4 cm, flicker 3-8 percent'), drop=False)
    if want('Extra'):
        m = mk('SM_Post_Support_Oak_PR', 'prop', W3 if False else ('fieldstone', 'oak', 'rope', 'boulder'), 'indoor_stone'); support_post(m)
        rec(m, ['87 inside/details/table- frame 10', 'support_post_timber'], 'none (support_post_timber placeholder, 21 placements)', 'oak roof post 2.65 m on a two-course dressed stone pad, with a cross head and two pegged braces',
            fit={'pivot': 'base centre; the cross head runs along X', 'sprite_scale': 'frame 10 is 106 px (2.65 m) tall'})
        m = mk('SM_Cabinet_Oak_PR', 'prop', W3); sideboard(m)
        rec(m, ['87 inside/details/table- frames 1, 7', 'cabinet_wood', 'cabinet_narrow'], 'none (cabinet_wood placeholder, 20 placements)', 'heavy oak side table 2.35 x 1.42 x 0.92 m with deep two-board aprons all round (class cabinet_wood: frames 1 and 7 are its front and end views)',
            fit={'pivot': 'base centre', 'sprite_scale': 'frame 1 is 94 px (2.35 m) wide, frame 7 57 px (1.42 m)'})
        m = mk('SM_Dungeon_Pillar_Twin_PR', 'prop_large', ('boulder', 'oak'), 'dungeon'); dungeon_pillar(m)
        rec(m, ['80 inside/stnwalls/stonw- frames 27, 28', 'dungeon_pillar'], 'none (dungeon_pillar placeholder, 17 placements)', 'twin stone columns on a two-step plinth, 1.04 x 0.6 x 2.4 m: each of four drums a little out of true, moulded base and capital, square abacus; a spall lying by the plinth',
            fit={'pivot': 'base centre; the pair stands along X', 'moss': 'painted damp and dirty with a trace of algae at the foot only'})
        m = mk('SM_Rubble_Pile_PR', 'prop', ('boulder', 'earth'), 'dungeon'); rubble_pile(m)
        rec(m, ['80 inside/stnwalls/stonw- frame 23', 'rubble_pile'], 'none (rubble_pile placeholder, 12 placements)', 'heap of fallen masonry 2.1 x 1.2 x 0.45 m: about a dozen squared blocks and twenty-odd broken stones tumbled over a low mound of dust', fit={'pivot': 'ground centre; yaw at random'})
        m = mk('SM_Shelf_Bottles_PR', 'prop_large', ('glaze_blue', 'oak', 'glaze_red', 'iron', 'glaze_green')); shelf_bottles(m)
        rec(m, ['64 inside/details/inacc- frame 1', 'shelf_bottles', 'shelf_empty'], 'none (shelf_bottles placeholder, 12 placements; shelf_empty 12)', 'apothecary wall unit 3.85 x 0.45 x 2.9 m: plank back and ends, a boarded dresser base, three shelves on brackets carrying about thirty corked glazed bottles of three shapes in blue, red and green',
            fit={'pivot': 'base centre; the back (+Y) stands against the wall', 'sprite_scale': 'frame 1 is 154 x 116 px (3.85 x 2.9 m)', 'empty': 'class shelf_empty (sprite 459) is not built: it needs this unit without bottles'})
    return out


def main_props():
    sc = new_scene()
    rows = board_rows('OakWeathered')
    oak = dict(dirt=(0.2, 0.14, 0.09), pale=(0.66, 0.5, 0.32), pale_amt=0.6, special=True)
    hes = dict(dirt=(0.34, 0.28, 0.2), pale=(0.82, 0.76, 0.6), pale_amt=0.4, dirt_amt=0.9)
    lin = dict(dirt=(0.42, 0.36, 0.27), pale=(0.9, 0.88, 0.8), pale_amt=0.35, dirt_amt=0.9)
    glz = dict(dirt=(0.3, 0.25, 0.18), pale=(0.55, 0.36, 0.24), pale_amt=0.85, dirt_amt=0.9, macro=0.3)
    mats = {'fieldstone': wmat('MI_Struct_Fieldstone', 'Fieldstone', dirt=(0.36, 0.30, 0.22), pale=(0.62, 0.60, 0.52), pale_amt=0.5, soot=True),
            'oak': wmat('MI_Prop_OakWarm', 'OakWeathered', tint=(1.0, 0.6, 0.33, 1), **oak),
            'iron': wmat('MI_Prop_Iron', 'WroughtIron', dirt=(0.30, 0.13, 0.05), dirt_mix=True, dirt_amt=0.85, pale=(0.13, 0.145, 0.165), pale_amt=0.9, macro=0.3),
            'oakred': wmat('MI_Prop_OakRed', 'OakWeathered', tint=(0.9, 0.36, 0.2, 1), **oak),
            'rope': wmat('MI_Struct_Rope', 'Thatch', dirt=(0.5, 0.45, 0.38), pale=(0.7, 0.62, 0.45), pale_amt=0.4, tint=(0.9, 0.85, 0.8, 1)),
            'earth': wmat('MI_Struct_Earth', 'EarthPath', tint=(0.62, 0.56, 0.50, 1), dirt=(0.36, 0.30, 0.24), pale=(0.80, 0.79, 0.77), pale_amt=0.85, moss=(0.045, 0.075, 0.02), moss_rough=0.9, soot=True),
            'boulder': wmat('MI_Struct_FieldBoulder', 'FieldBoulder', dirt=(0.34, 0.27, 0.18), pale=(0.66, 0.66, 0.58), pale_amt=0.5, moss=(0.045, 0.06, 0.02)),
            'hessian': wmat('MI_Prop_Hessian', 'Hessian', **hes),
            'hessian_olive': wmat('MI_Prop_Hessian_Olive', 'Hessian', tint=(0.8, 0.86, 0.42, 1), **hes),
            'hessian_red': wmat('MI_Prop_Hessian_Red', 'Hessian', tint=(0.85, 0.42, 0.36, 1), **hes),
            'linen': wmat('MI_Prop_Linen', 'Linen', **lin),
            'blanket': wmat('MI_Prop_Blanket_Weld', 'Linen', tint=(0.6, 0.56, 0.16, 1), **lin),
            'madder': wmat('MI_Prop_Cloth_Madder', 'Linen', tint=(0.62, 0.15, 0.06, 1), **lin),
            'glaze_brown': wmat('MI_Prop_Glaze_Brown', 'Earthenware', tint=(0.3, 0.13, 0.055, 1), **glz),
            'glaze_blue': wmat('MI_Prop_Glaze_Blue', 'Earthenware', tint=(0.13, 0.2, 0.34, 1), **glz),
            'glaze_red': wmat('MI_Prop_Glaze_Red', 'Earthenware', tint=(0.36, 0.04, 0.035, 1), **glz),
            'glaze_green': wmat('MI_Prop_Glaze_Green', 'Earthenware', tint=(0.16, 0.32, 0.1, 1), **glz),
            'glaze_purple': wmat('MI_Prop_Glaze_Purple', 'Earthenware', tint=(0.3, 0.1, 0.42, 1), **glz),
            'tallow': wmat('MI_Prop_Tallow', 'PlasterWall', tint=(1.0, 0.92, 0.7, 1), dirt=(0.5, 0.4, 0.25), pale=(0.95, 0.93, 0.85), pale_amt=0.3, dirt_amt=0.8, macro=0.1),
            'wicker': wmat('MI_Prop_Wicker', 'Thatch', tint=(0.78, 0.6, 0.42, 1), dirt=(0.3, 0.22, 0.14), pale=(0.8, 0.7, 0.5), pale_amt=0.45, dirt_amt=0.9),
            'crust': wmat('MI_Prop_PieCrust', 'PlasterWall', tint=(0.72, 0.43, 0.17, 1), dirt=(0.36, 0.15, 0.05), pale=(0.95, 0.85, 0.6), pale_amt=0.5, dirt_amt=0.95, macro=0.3),
            'glass_red': wmat('MI_Prop_PotionGlass_Red', 'OakWeathered', special=True, glass_tint=(0.075, 0.002, 0.003), dirt=(0.2, 0.14, 0.09), pale=(0.56, 0.46, 0.34), pale_amt=0.6, tint=(1.0, 0.66, 0.4, 1)),
            'glass_purple': wmat('MI_Prop_PotionGlass_Purple', 'OakWeathered', special=True, glass_tint=(0.03, 0.004, 0.07), dirt=(0.2, 0.14, 0.09), pale=(0.56, 0.46, 0.34), pale_amt=0.6, tint=(1.0, 0.66, 0.4, 1)),
            'glass_blue': wmat('MI_Prop_PotionGlass_Blue', 'OakWeathered', special=True, glass_tint=(0.004, 0.015, 0.09), dirt=(0.2, 0.14, 0.09), pale=(0.56, 0.46, 0.34), pale_amt=0.6, tint=(1.0, 0.66, 0.4, 1)),
            'horn': wmat('MI_Prop_LanternHorn', 'OakWeathered', special=True, glass_tint=(0.55, 0.3, 0.07), dirt=(0.2, 0.14, 0.09), pale=(0.66, 0.5, 0.32), pale_amt=0.6, tint=(1.0, 0.6, 0.33, 1)),
            'bone': wmat('MI_Prop_Bone', 'PlasterWall', tint=(0.95, 0.9, 0.78, 1), dirt=(0.32, 0.26, 0.17), pale=(0.9, 0.9, 0.86), pale_amt=0.5, dirt_amt=0.95, moss=(0.05, 0.07, 0.03))}
    mods = prop_modules(rows)
    blend = 'Props.blend' if not ARGS else 'Props_part.blend'
    regall = dict(MATREG)
    recs = export_modules(mods, mats, OUT, blend)
    mj = os.path.join(OUT, 'modules.json'); old = json.load(open(mj)) if os.path.exists(mj) else []
    names = [r_['name'] for r_ in recs]
    json.dump([o for o in old if o['name'] not in names] + recs, open(mj, 'w'), indent=1)
    json.dump(regall, open(os.path.join(OUT, 'materials.json'), 'w'), indent=1)
    print('PROPS DONE', len(recs))


main_props()
