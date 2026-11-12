"""Deadwood: stumps, fallen log, forked fallen branch, twig cluster. Materials: MI_Veg_Deadwood (bark bands) + MI_Veg_DeadwoodEnd (cut face)."""
import numpy as np, math
from bl_tree import *
UP = np.array([0, 0, 1.0])
def mats(): return [game_mat('MI_Veg_Deadwood', 'T_Veg_Deadwood'), game_mat('MI_Veg_DeadwoodEnd', 'T_Veg_DeadwoodEnd')]
def clamp_ground(mb):
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.0); mb.v = list(V); recenter(mb)

def shards(mb, c, axis, r, rng, n=7, L=(0.08, 0.3), step=1):
    n = n * 4          # torn fibres: many thin splinters of uneven length
    axis = nrm(axis); a = np.array([0, 0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0, 0]); u = nrm(np.cross(a, axis)); w = np.cross(axis, u)
    for i in range(n):
        ang = 2 * math.pi * i / n + rng.uniform(0, 0.5); rr = r * rng.uniform(0.2, 0.85); o = (math.cos(ang) * u + math.sin(ang) * w) * rr
        ln = rng.uniform(*L); pts = np.array([c + o - axis * 0.06, c + o * 0.95 + axis * ln * 0.5, c + o * 0.85 + axis * ln + rng.normal(0, 0.01, 3)])
        if i % step == 0: mb.tube(pts, [r * 0.2, r * rng.uniform(0.05, 0.14), r * 0.01], 3, 'limb', 1, 0.6, cap=True)

def cut_face(mb, c, n, ring_pts, rmax, rng, uvrot=0.0):
    """end-grain disc: centre + mid ring + rim (ring_pts are the outer loop positions)."""
    n = nrm(n); m = len(ring_pts); ring = np.asarray(ring_pts); rng = np.random.default_rng(1234)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0]); u = nrm(np.cross(n, a)); w = np.cross(n, u)
    def uv(p):
        d = p - c; x = np.dot(d, u) / rmax; y = np.dot(d, w) / rmax
        ca, sa = math.cos(uvrot), math.sin(uvrot)
        return (0.5 + 0.44 * (x * ca - y * sa), 0.5 + 0.44 * (x * sa + y * ca))
    V = [np.array(c)]; N = [n]; U = [uv(np.array(c))]; F = []
    for f in (0.5, 0.93, 1.0):
        for i in range(m):
            p = c + (ring[i] - c) * f
            if f < 1: p = p + n * (rng.normal(0, 0.004) + (0.012 if f > 0.9 else 0))
            V.append(p); N.append(nrm(n + (ring[i] - c) * (0.6 if f == 1.0 else 0.0))); U.append(uv(c + (ring[i] - c) * min(f, 0.97)))
    for i in range(m): F.append((0, 1 + i, 1 + (i + 1) % m))
    for k in range(2):
        for i in range(m):
            a0 = 1 + k * m + i; a1 = 1 + k * m + (i + 1) % m; F.append((a0, a0 + m, a1 + m, a1))
    mb.poly(V, N, U, 1, (0, 0, 0, 0), F)

def dome(mb, c, n, r, h, sides=8):
    r = r * 0.7; h = h * 0.8
    """moss cushion: a low dome mapped to the mossy bottom of the 'base' band"""
    n = nrm(n); a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0]); u = nrm(np.cross(n, a)); w = np.cross(n, u)
    V = [np.array(c) + n * h]; N = [n]; U = [(0.5, 0.06)]; F = []
    for ring, (rr, hh) in enumerate(((0.6, 0.72), (1.0, -0.01))):
        for k in range(sides):
            ang = 2 * math.pi * k / sides + ring * 0.5; o = math.cos(ang) * u + math.sin(ang) * w
            V.append(np.array(c) + o * r * rr * (0.7 + 0.6 * abs(math.sin(k * 2.3 + r * 90 + ring))) + n * h * hh * (0.8 + 0.4 * math.sin(k * 1.7 + r * 50))); N.append(nrm(n * (1.6 if ring == 0 else 0.7) + o))
            U.append((0.5 + 0.12 * rr * math.cos(ang), 0.06 + 0.035 * rr * math.sin(ang)))
    for k in range(sides):
        F.append((0, 1 + k, 1 + (k + 1) % sides)); F.append((1 + k, 1 + sides + k, 1 + sides + (k + 1) % sides, 1 + (k + 1) % sides))
    mb.poly(V, N, U, 0, (0, 0, 0, 0), F)

def bracket(mb, p, out, r, rng, sides=7):
    """bracket fungus: a half-disc shelf, pale zoned top (end-grain texture rings), mapped to the cut-face material"""
    out = nrm(out); side = nrm(np.cross(UP, out)); th = r * 0.28
    V = [np.array(p) - out * 0.01 + UP * th * 0.3]; N = [UP]; U = [(0.5, 0.5)]; F = []
    for k in range(sides + 1):
        ang = math.pi * k / sides; o = math.cos(ang) * side + math.sin(ang) * out; rr = r * (0.9 + 0.2 * rng.random()) * (0.75 + 0.25 * math.sin(ang))
        V.append(np.array(p) + o * rr + UP * rng.normal(0, r * 0.03)); N.append(nrm(UP * 0.8 + o * 0.6)); U.append((0.5 + 0.3 * math.cos(ang), 0.5 + 0.3 * math.sin(ang)))
    for k in range(sides + 1):
        ang = math.pi * k / sides; o = math.cos(ang) * side + math.sin(ang) * out
        V.append(V[1 + k] * 1.0 - UP * th + (-o) * r * 0.25); N.append(nrm(-UP + o * 0.4)); U.append((0.5 + 0.42 * math.cos(ang), 0.5 + 0.42 * math.sin(ang)))
    for k in range(sides):
        F.append((0, 1 + k, 2 + k)); F.append((1 + k, sides + 2 + k, sides + 3 + k, 2 + k))
    mb.poly(V, N, U, 1, (0, 0, 0, 0), F)

def build_stump(name, lod):
    seed = {'SM_Veg_Stump_01': 61, 'SM_Veg_Stump_02': 67}[name]; rng = np.random.default_rng(seed); mb = MeshB()
    big = name.endswith('01'); r0 = 0.27 if big else 0.21; hc = 0.52 if big else 0.38
    tilt = np.array([rng.normal(0, 0.05), rng.normal(0, 0.05)])
    axis = lambda z: np.array([tilt[0] * z, tilt[1] * z, z]); rfun = lambda z: r0 * (1.0 - 0.06 * z / hc)
    mb.root_base(axis, rfun, seed, lod, top=hc, strength=1.25, nroots=6 if big else 5)       # one surface: bole, buttress ridges, roots diving under the soil
    base, R, S, angs = mb.last_base
    c = axis(hc); nrmcut = nrm(np.array([rng.normal(0, 0.07), rng.normal(0, 0.07), 1]))
    top = [mb.v[base + (R - 1) * S + j] for j in range(S)]
    top = [p + nrmcut * (-np.dot(p - c, nrmcut)) for p in top]                               # planar, slightly tilted saw cut
    for j in range(S): mb.v[base + (R - 1) * S + j] = top[j]
    inner = [c + (p - c) * 0.93 for p in top]
    cut_face(mb, c, nrmcut, inner, max(np.linalg.norm(np.asarray(top) - c, axis=1)), rng, rng.uniform(0, 6))
    # bark standing proud of the cut and peeling away in places
    prng = np.random.default_rng(seed + 5); V = []; N = []; U = []; F = []
    for j in range(S):
        o = nrm(top[j] - c); wv = math.sin(angs[j] * 3 + seed) + 0.6 * math.sin(angs[j] * 7 + 1.3); peel = wv > 0.9; up = 0.006 + 0.008 * wv if not peel else -0.02; outw = 0.003 if not peel else 0.022
        V += [top[j], top[j] + o * outw + nrmcut * up, inner[j] + nrmcut * (up - 0.004)]; N += [o, nrm(o + nrmcut), nrm(nrmcut - o * 0.5)]
        u = angs[j] / (2 * math.pi); U += [(u, 0.235), (u, 0.247), (u, 0.249)]
    if lod < 2:
        for j in range(S):
            a0 = 3 * j; a1 = 3 * ((j + 1) % S)
            if abs(angs[(j + 1) % S] - angs[j]) < 1.0: F += [(a0, a1, a1 + 1, a0 + 1), (a0 + 1, a1 + 1, a1 + 2, a0 + 2)]
        mb.poly(V, N, U, 0, (0, 0, 0, 0), F)
    for k in range(3 if big else 2):          # bracket fungi on the shaded side
        az = 2.4 + k * 0.5 + rng.normal(0, 0.15); z = rng.uniform(0.14, hc * 0.75); o = np.array([math.cos(az), math.sin(az), 0])
        bracket(mb if lod < 2 else MeshB(), axis(z) + o * rfun(z) * 1.2, o, rng.uniform(0.05, 0.1), rng, 7 if lod == 0 else 4)
    for k in range(9):                        # moss cushions on the root shoulders and the rim
        az = rng.uniform(0, 6.28); z = rng.choice([0.03, 0.08, 0.16, hc + 0.005]); o = np.array([math.cos(az), math.sin(az), 0])
        rr = rfun(z) * (rng.uniform(1.25, 1.9) if z < 0.2 else rng.uniform(0.5, 0.9)); n = nrm(UP + o * (0.6 if z < 0.2 else 0.0))
        dome(mb if (lod == 0 or (lod == 1 and k % 2 == 0)) else MeshB(), axis(z) + o * rr, n, rng.uniform(0.04, 0.09), rng.uniform(0.015, 0.03))
    recenter(mb, xy=False)
    return mb.build(f'{name}_LOD{lod}', mats())

def build_log(name, lod):
    rng = np.random.default_rng(71); mb = MeshB(); L = 2.6; r0, r1 = 0.21, 0.13
    sides = (16, 10, 6)[lod]; n = (16, 8, 4)[lod]
    xs = np.linspace(-L / 2, L / 2, n + 1); zc = np.linspace(r0, r1, n + 1) * 0.8
    pts = np.stack([xs, 0.09 * np.sin(xs * 1.1 + 0.4), zc + 0.012 * np.sin(xs * 2.3)], 1)
    rad = np.linspace(r0, r1, n + 1) * (1 + 0.05 * np.sin(xs * 5.1) + 0.04 * np.sin(xs * 11.3 + 1))
    ph = rng.uniform(0, 6.28, 3)
    def radial(i, a): return 1 + 0.06 * math.sin(2 * a + ph[0] + xs[i] * 1.2) + 0.03 * math.sin(5 * a + ph[1] - xs[i] * 3) + 0.02 * math.sin(11 * a + ph[2])
    # bare wood core, then the bark shell with sheets missing
    b_in = mb.nv(); mb.tube(pts, rad - 0.014, sides, 'limb', 1, 0.8, radial=radial, cap=False)
    f0 = len(mb.faces); b0 = mb.nv(); mb.tube(pts, rad, sides, 'body', 1, 2 * math.pi * r0, radial=radial, cap=False)
    holes = [(0.28, 1.1, 0.16, 0.9), (0.62, 2.6, 0.2, 0.7), (0.85, 0.6, 0.1, 1.1), (0.45, 4.4, 0.12, 0.8)]       # (t along, angle, half-length t, half-angle)
    drop = []
    for fi in range(f0, len(mb.faces)):
        k = fi - f0; i = k // sides; j = k % sides; t = (i + 0.5) / n; a = 2 * math.pi * (j + 0.5) / sides
        for (ht, ha, hl, hw) in holes:
            if abs(t - ht) < hl * (0.7 + 0.5 * math.sin(j * 1.7)) and abs((a - ha + math.pi) % (2 * math.pi) - math.pi) < hw * (0.7 + 0.4 * math.sin(i * 2.1)): drop.append(fi); break
    for fi in reversed(drop): del mb.faces[fi]; del mb.uv[fi]; del mb.mat[fi]
    for i in range(b_in, mb.nv()):      # oval section: a lying log settles
        mb.v[i] = np.array([mb.v[i][0], mb.v[i][1], pts[0][2] * 0 + (mb.v[i][2] - 0.0) * 0.86])
    first = [mb.v[b0 + j] for j in range(sides)]; c0 = np.mean(first, axis=0); ax0 = nrm(pts[1] - pts[0])
    # rot hollow at the butt end: end-grain annulus and a dark tube going in
    hol = [c0 + (p - c0) * 0.55 * (0.85 + 0.3 * math.sin(j * 1.3)) for j, p in enumerate(first)]
    V = first + hol; N = [-ax0] * (2 * sides); rm = max(np.linalg.norm(np.asarray(first) - c0, axis=1))
    u_ = nrm(np.cross(ax0, UP)); w_ = np.cross(u_, ax0)
    U = [(0.5 + 0.44 * np.dot(p - c0, u_) / rm, 0.5 + 0.44 * np.dot(p - c0, w_) / rm) for p in V]
    mb.poly(V, N, U, 1, (0, 0, 0, 0), [(j, (j + 1) % sides, sides + (j + 1) % sides, sides + j) for j in range(sides)])
    deep = [p + ax0 * (0.55 + 0.1 * math.sin(j)) + (c0 - p) * 0.5 for j, p in enumerate(hol)]
    V = hol + deep + [c0 + ax0 * 0.7]; N = [nrm(c0 - p) for p in hol] + [nrm(c0 - p + 1e-6) for p in deep] + [-ax0]
    U = [(j / sides, 0.80) for j in range(sides)] + [(j / sides, 0.86) for j in range(sides)] + [(0.5, 0.88)]
    F = [(j, (j + 1) % sides, sides + (j + 1) % sides, sides + j) for j in range(sides)] + [(sides + j, sides + (j + 1) % sides, 2 * sides) for j in range(sides)]
    if lod < 2: mb.poly(V, N, U, 0, (0, 0, 0, 0), F)
    last = np.array([pts[-1][0], pts[-1][1], pts[-1][2] * 0.86])
    shards(mb if lod < 2 else MeshB(), last, nrm(pts[-1] - pts[-2]), r1, rng, 9, (0.1, 0.5), step=1 if lod == 0 else 3)
    if lod == 2: mb.tube(np.array([last, last + nrm(pts[-1] - pts[-2]) * 0.2]), [r1, r1 * 0.2], sides, 'limb', 1, 0.6, cap=True)
    for i, (t, az, ln) in enumerate([(0.3, 1.3, 0.28), (0.55, 2.2, 0.16), (0.72, 0.7, 0.4)]):   # branch stubs with collars and torn ends
        tg = mb if not (lod == 2 and i != 2) else MeshB()
        j = int(t * n); p = pts[j] * np.array([1, 1, 0.86]); d = nrm(pts[j + 1] - pts[j]); side = np.cross(UP, d); o = nrm(side * math.cos(az) + UP * math.sin(az) + d * 0.35)
        pp = path(p + o * rad[j] * 0.5, o, ln + rad[j] * 0.5, 4, rng, 0.2); rr = rng.uniform(0.03, 0.045)
        tg.tube(pp, rr * np.array([2.3, 1.35, 1.05, 0.95, 0.85]), (7, 5, 4)[lod], 'body', 1, 0.4, cap=False)
        shards(tg if lod == 0 else MeshB(), pp[-1], nrm(pp[-1] - pp[-2]), rr * 0.8, rng, 3, (0.03, 0.12))
        if lod > 0: tg.tube(np.array([pp[-1], pp[-1] + nrm(pp[-1] - pp[-2]) * 0.05]), [rr * 0.8, rr * 0.1], (5, 4)[lod - 1], 'limb', 1, 0.4, cap=True)
    for k in range(10):                       # moss cushions along the top
        t = rng.uniform(0.08, 0.92); j = int(t * n); a = math.pi / 2 + rng.normal(0, 0.5); c = pts[j] * np.array([1, 1, 0.86]); o = np.array([0, math.cos(a), math.sin(a) * 0.86])
        dome(mb if (lod == 0 or (lod == 1 and k % 2 == 0)) else MeshB(), c + o * rad[j] * 0.98, nrm(o), rng.uniform(0.05, 0.11), rng.uniform(0.015, 0.03))
    clamp_ground(mb)
    return mb.build(f'{name}_LOD{lod}', mats())

def _branch(mb, p0, d0, L, r0, rng, lod, depth=0, lift=0.0):
    n = max(2, int(L / 0.16))                       # skeleton is always generated at LOD0 resolution so every LOD is the same branch
    pp = path(p0, d0, L, n, rng, 0.35, lambda t, d, p: (0, 0, (0.8 if p[2] < r0 * 1.2 else -0.9) + lift))
    rr = np.linspace(r0, max(0.003, r0 * 0.3), n + 1)
    pp[:, 2] = np.maximum(pp[:, 2], rr * 0.8)
    sides = (8 if r0 > 0.03 else (5 if r0 > 0.012 else 4), 5 if r0 > 0.03 else 3, 3)[lod]
    band = 'body' if r0 > 0.018 and rng.random() < 0.8 else 'limb'; vph = int(rng.integers(0, 4))
    sel = np.unique(np.round(np.linspace(0, n, max(2, int(n / (1, 2, 3.5)[lod]) + 1))).astype(int))
    mb.tube(pp[sel], rr[sel], sides, band, 1, max(0.25, 6.28 * r0), cap=True, vphase=vph)
    if depth < 2 and r0 > 0.007:
        nk = (rng.integers(2, 4) if depth == 0 else rng.integers(1, 3))
        for k in range(nk):
            t = rng.uniform(0.3, 0.85); j = min(int(t * n), n - 1); d = nrm(pp[j + 1] - pp[j]); sd = nrm(np.cross(UP, d)) * (1 if k % 2 else -1)
            dd = nrm(d * 0.75 + sd * rng.uniform(0.45, 0.9) + UP * rng.uniform(-0.1, 0.5))
            _branch(mb if not (lod == 2 and depth == 1) else MeshB(), pp[j], dd, L * rng.uniform(0.35, 0.6), rr[j] * rng.uniform(0.5, 0.7), rng, lod, depth + 1, lift=rng.uniform(0, 0.5))
    return pp

def build_branch(name, lod):
    rng = np.random.default_rng(83); mb = MeshB()
    pp = _branch(mb, (-0.9, 0, 0.05), (1, 0.15, 0.1), 1.0, 0.05, rng, lod, depth=1)
    d = nrm(pp[-1] - pp[-2]); sd = np.cross(UP, d)
    _branch(mb, pp[-1] - d * 0.03, nrm(d + sd * 0.42 + UP * 0.1), 1.15, 0.036, rng, lod, 0)
    _branch(mb, pp[-1] - d * 0.03, nrm(d - sd * 0.5 + UP * 0.25), 0.9, 0.03, rng, lod, 0, lift=0.3)
    shards(mb if lod < 2 else MeshB(), np.array(pp[0]), -nrm(pp[1] - pp[0]), 0.05, rng, 5, (0.03, 0.12))
    clamp_ground(mb)
    return mb.build(f'{name}_LOD{lod}', mats())

def build_twigs(name, lod):
    rng = np.random.default_rng(97); mb = MeshB()
    for i in range(5):
        a = rng.uniform(0, 6.28); c = np.array([rng.normal(0, 0.16), rng.normal(0, 0.13), 0.008])
        _branch(mb if (lod < 2 or i < 3) else MeshB(), c, (math.cos(a), math.sin(a), 0.02), rng.uniform(0.28, 0.6), rng.uniform(0.006, 0.011), rng, lod, depth=1, lift=0.6)
    clamp_ground(mb)
    return mb.build(f'{name}_LOD{lod}', mats())

DEAD = {'SM_Veg_Stump_01': build_stump, 'SM_Veg_Stump_02': build_stump, 'SM_Veg_FallenLog_01': build_log, 'SM_Veg_FallenBranch_Forked_01': build_branch, 'SM_Veg_TwigCluster_01': build_twigs}
def build(name, lod): return DEAD[name](name, lod)
