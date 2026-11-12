"""Understory pieces: thorn brambles (hazard dressing), fern clumps, hanging vines. Materials: MI_Veg_DarkBark, MI_Veg_Understory."""
import numpy as np, math
from bl_tree import *
from veg_broadleaf import FERN_T, VINE_T, TWIG_S
UP = np.array([0, 0, 1.0])
def und(): return game_mat('MI_Veg_Understory', 'T_Veg_Understory', alpha=True, translucency=0.25)
def dark(): return game_mat('MI_Veg_DarkBark', 'T_Veg_DarkBark')

def _cane(mb, rng, start, yaw, L, h, r0, lod, loop=False, emit=True):
    """one arching bramble cane with thorns; generated at full resolution so every LOD is the same cane"""
    n = max(8, int(L / 0.09)); d = np.array([math.cos(yaw), math.sin(yaw), 0]); side = np.array([-d[1], d[0], 0])
    ph = rng.uniform(0, 6.28, 3); wig = rng.uniform(0.08, 0.22) * L; pts = []
    for i in range(n + 1):
        t = i / n
        z = h * math.sin(math.pi * min(1.0, t * (1.0 if not loop else 0.85))) ** 0.8 + 0.015
        p = np.array(start) + d * L * t + side * wig * math.sin(t * rng.uniform(4.9, 5.1) + ph[0]) + UP * z
        if loop: a = t * 2 * math.pi; p = np.array(start) + d * (L * 0.35 * math.sin(a)) + side * wig * math.sin(2 * a + ph[1]) + UP * (h * 0.5 * (1 - math.cos(a)) + 0.02)
        pts.append(p + rng.normal(0, 0.012, 3))
    pts = np.array(pts); pts[1:-1] = 0.25 * pts[:-2] + 0.5 * pts[1:-1] + 0.25 * pts[2:]; pts[:, 2] = np.maximum(pts[:, 2], 0.012)
    rad = np.linspace(r0, r0 * 0.45, n + 1)
    sel = np.unique(np.round(np.linspace(0, n, max(3, int(n / (2, 4, 7)[lod]) + 1))).astype(int))
    tg = mb if emit else MeshB()
    tg.tube(pts[sel], rad[sel], (4, 3, 3)[lod], 'limb', 1, 0.3, wind=(0, rng.random(), 0, 0), cap=True)
    for i in range(1, n, 3):          # thorns: stout, hooked back along the cane
        for q in range(2):
            a = rng.uniform(0, 6.28); dd = nrm(pts[i + 1] - pts[i - 1]); u = nrm(np.cross(dd, UP) + 1e-6); w = np.cross(dd, u)
            o = math.cos(a) * u + math.sin(a) * w; ln = rng.uniform(0.035, 0.07); p = pts[i] + dd * rng.uniform(-0.05, 0.05)
            ok = (lod == 0) or (lod == 1 and (i + q) % 3 == 0)
            (tg if ok else MeshB()).tube(np.array([p + o * rad[i] * 0.6, p + o * (rad[i] + ln * 0.6) - dd * ln * 0.15, p + o * (rad[i] + ln) - dd * ln * 0.5]),
                                         [rad[i] * 0.6, rad[i] * 0.28, 0.001], 3, 'limb', 1, 0.2, cap=False)

THORN = {'SM_Veg_ThornBush_01': dict(seed=5, canes=16, R=0.95, L=(1.3, 2.4), h=(0.45, 1.15), r=(0.02, 0.034), loops=6),
         'SM_Veg_ThornBush_02': dict(seed=9, canes=8, R=0.8, L=(1.1, 2.1), h=(0.35, 0.9), r=(0.018, 0.03), loops=4),
         'SM_Veg_ThornBranch_01': dict(seed=14, canes=2, R=0.1, L=(0.5, 0.75), h=(0.05, 0.14), r=(0.012, 0.016), loops=0)}
def build_thorn(name, lod):
    P = THORN[name]; rng = np.random.default_rng(P['seed']); mb = MeshB()
    for k in range(P['canes']):
        a = rng.uniform(0, 6.28); rr = P['R'] * math.sqrt(rng.random()); st = np.array([math.cos(a) * rr, math.sin(a) * rr, 0])
        yaw = a + math.pi + rng.normal(0, 0.9); L = rng.uniform(*P['L']); h = rng.uniform(*P['h']); r0 = rng.uniform(*P['r'])
        _cane(mb, rng, st, yaw, L, h, r0, lod, loop=k < P['loops'], emit=not (lod == 2 and k % 2 == 1 and P['canes'] > 3))
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.0); mb.v = list(V); recenter(mb)
    return mb.build(f'{name}_LOD{lod}', [dark()])

def build_fern(name, lod):
    rng = np.random.default_rng({'SM_Veg_Fern_01': 21, 'SM_Veg_Fern_02': 22}[name]); mb = MeshB(); n = 13 if name.endswith('01') else 9
    for k in range(n):
        key = rng.random(); a = k * 2.4 + rng.normal(0, 0.25); L = rng.uniform(0.55, 0.95) * (0.8 if name.endswith('02') else 1.0); inner = k > n * 0.6
        d = nrm(np.array([math.cos(a), math.sin(a), 0]) * (0.5 if inner else 1.0) + UP * (1.5 if inner else rng.uniform(0.55, 1.0)))
        w = nrm(np.cross(d, UP)); o = np.array([math.cos(a) * 0.03, math.sin(a) * 0.03, 0.0])
        if key < (1.0, 0.75, 0.5)[lod]:
            mb.card(o, d, w, L * (1, 1.1, 1.3)[lod], L * 0.5 * (1, 1.1, 1.3)[lod], FERN_T[rng.integers(2)], (4, 2, 1)[lod], (2, 1, 1)[lod], rng.uniform(1.3, 2.2), -0.12 if lod == 0 else 0,
                    None, 0.6, (0, rng.random(), 0, 0), 0, rng.random() < 0.5)
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.005); mb.v = list(V); recenter(mb)
    return mb.build(f'{name}_LOD{lod}', [und()])

def build_vines(name, lod):
    rng = np.random.default_rng({'SM_Veg_HangingVines_01': 31, 'SM_Veg_HangingVines_02': 37}[name]); mb = MeshB(); top = 2.8
    for k in range(6 if name.endswith('01') else 4):
        key = rng.random(); x = rng.uniform(-0.5, 0.5); y = rng.normal(0, 0.06); L = rng.uniform(1.6, 2.75); o = np.array([x, y, top]); yaw = rng.uniform(-0.9, 0.9)
        w = np.array([math.cos(yaw), math.sin(yaw), 0]); d = nrm(np.array([rng.normal(0, 0.06), rng.normal(0, 0.06), -1])); ph = rng.random()
        emit = key < (1.0, 0.7, 0.5)[lod]
        while L > 0.2:
            L1 = min(L, rng.uniform(0.55, 1.0)); tl = VINE_T[rng.integers(2)]; u_off = rng.uniform(0, 1.0 - L1) * (tl[2] - tl[0]); tl = (tl[0] + u_off, tl[1], tl[0] + u_off + (tl[2] - tl[0]) * L1 / 1.0, tl[3])
            fl = rng.random() < 0.5; lf = rng.uniform(-0.12, 0.12); w2 = nrm(w * math.cos(1.4) + np.cross(UP, w) * math.sin(1.4)); wn = (0, ph, 0, 1 - (o[2] - L1) / top)
            if emit:
                mb.card(o, d, w, L1, 0.3 * (1, 1.2, 1.5)[lod], tl, (2, 1, 1)[lod], 1, 0.0, 0, None, 0.5, wn, 0, fl, lift=lf)
                if lod == 0: mb.card(o, d, w2, L1, 0.3, tl, 2, 1, 0.0, 0, None, 0.5, wn, 0, not fl, lift=-lf)       # second plane so a strand has depth from the side
            w = nrm(w * math.cos(0.7) + np.cross(UP, w) * math.sin(0.7))
            o = o + d * (L1 - 0.03); L -= L1; d = nrm(d + rng.normal(0, 0.06, 3) * np.array([1, 1, 0]))
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.0); mb.v = list(V)
    off = recenter(mb); mb.v = [p - np.array([0, 0, off[2]]) for p in mb.v]; mb.keep_z = False       # keep the hang height: pivot stays on the floor under the vines
    return mb.build(f'{name}_LOD{lod}', [und()])

UNDER = {**{k: build_thorn for k in THORN}, 'SM_Veg_Fern_01': build_fern, 'SM_Veg_Fern_02': build_fern, 'SM_Veg_HangingVines_01': build_vines, 'SM_Veg_HangingVines_02': build_vines}
def build(name, lod): return UNDER[name](name, lod)
