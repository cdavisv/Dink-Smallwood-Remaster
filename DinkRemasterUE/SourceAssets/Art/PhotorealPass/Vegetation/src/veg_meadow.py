"""Meadow grass carpet patches for the engine grass layer (instanced with random yaw / scale): SM_Veg_GrassPatch_Tall_01..03, _Short_01..02, _Dry_01.
Material MI_Veg_MeadowGrass (atlas T_Veg_MeadowGrass, see meadow_layout.py). Cards stand at random positions and yaw in three crossing direction
families (no rosette), lean and arch individually, normals bent to straight up so a carpet lights evenly. Wind: G phase, B 0 at the root to 1 at the tip."""
import numpy as np, math
from bl_tree import *
from meadow_layout import uv as TUV
UP = np.array([0, 0, 1.0])
def mg_mat(): return game_mat('MI_Veg_MeadowGrass', 'T_Veg_MeadowGrass', alpha=True, translucency=0.3)

def gcard(mb, o, yaw, lean, arch, width, height, tile, segs, phase, flip, tilt=0.0, flutter=1.0):
    """upright card: root line through o, growing up, leaning `lean` rad toward its normal and arching a further `arch` rad to the tip."""
    w = np.array([math.cos(yaw), math.sin(yaw), 0]); nf = np.array([-math.sin(yaw), math.cos(yaw), 0]); u0, v0, u1, v1 = TUV(tile)
    if flip: u0, u1 = u1, u0
    V = []; Nn = []; UVs = []; W = []; F = []; p = np.array(o, float)
    wv = nrm(w + UP * tilt)
    for a in range(segs + 1):
        t = a / segs; ang = lean + arch * t ** 1.5; d = UP * math.cos(ang) + nf * math.sin(ang)
        if a > 0: p = p + d * height / segs
        for b in (0, 1):
            V.append(p + wv * (b - 0.5) * width); UVs.append((u0 + (u1 - u0) * b, v0 + (v1 - v0) * t))
            Nn.append(nrm(UP * 1.0 + nf * 0.22 * math.copysign(1, lean + arch + 1e-6) + w * (b - 0.5) * 0.35)); W.append((0, phase, flutter * t ** 1.3, 0))
    for a in range(segs): F.append((a * 2, a * 2 + 1, a * 2 + 3, a * 2 + 2))
    mb.poly(V, Nn, UVs, 0, W, F)

def flat(mb, o, yaw, width, length, tile, phase, z=0.012):
    """thatch card lying on the ground, slightly domed"""
    w = np.array([math.cos(yaw), math.sin(yaw), 0]); d = np.array([-math.sin(yaw), math.cos(yaw), 0]); u0, v0, u1, v1 = TUV(tile); o = np.array(o, float)
    V = [o - w * width / 2 - d * length / 2, o + w * width / 2 - d * length / 2, o + w * width / 2 + d * length / 2, o - w * width / 2 + d * length / 2]
    V = [p + UP * z * (0.6 + 0.8 * ((i * 7) % 3) / 2) for i, p in enumerate(V)]
    mb.poly(V, [UP] * 4, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], 0, [(0, phase, 0, 0)] * 4, [(0, 1, 2, 3)])

def scatter(rng, n, size, k=12):
    """best-candidate points in a square: even cover without a grid"""
    pts = [rng.uniform(-size / 2, size / 2, 2)]
    for i in range(1, n):
        c = rng.uniform(-size / 2, size / 2, (k, 2)); d = np.min(np.linalg.norm(c[:, None, :] - np.array(pts)[None], axis=2), axis=1); pts.append(c[np.argmax(d)])
    return np.array(pts)

PATCH = {
 'SM_Veg_GrassPatch_Tall_01': dict(seed=101, size=0.64, n=74, tiles=('T0', 'T1', 'T2', 'T3', 'T5', 'T0', 'T1'), wisp=('T4', 3), h=(0.82, 1.05), thatch=8, lean=0.2, arch=0.45),
 'SM_Veg_GrassPatch_Tall_02': dict(seed=102, size=0.62, n=70, tiles=('T1', 'T3', 'T5', 'T0', 'T5', 'T2'), wisp=('T4', 2), h=(0.72, 1.0), thatch=9, lean=0.24, arch=0.55),
 'SM_Veg_GrassPatch_Tall_03': dict(seed=103, size=0.60, n=66, tiles=('T0', 'T2', 'T3', 'T1', 'T5'), wisp=('T4', 5), h=(0.85, 1.08), thatch=7, lean=0.18, arch=0.4),
 'SM_Veg_GrassPatch_Dry_01': dict(seed=104, size=0.62, n=68, tiles=('D0', 'D1', 'D0', 'D1', 'T5'), wisp=('D0', 4), h=(0.70, 1.0), thatch=12, lean=0.26, arch=0.6),
 'SM_Veg_GrassPatch_Short_01': dict(seed=105, size=0.68, n=120, tiles=('S0', 'S1', 'S2', 'S3'), wisp=None, h=(0.75, 1.1), thatch=8, lean=0.5, arch=0.5, short=True),
 'SM_Veg_GrassPatch_Short_02': dict(seed=106, size=0.66, n=108, tiles=('S1', 'S3', 'S2', 'S0', 'SD0'), wisp=None, h=(0.6, 1.0), thatch=12, lean=0.55, arch=0.5, short=True),
}
def build(name, lod):
    P = PATCH[name]; rng = np.random.default_rng(P['seed']); mb = MeshB(); short = P.get('short', False); th = 0.2 if short else 0.6
    if lod == 2:      # two crossed quads, each showing two tiles side by side
        t = P['tiles']; a0 = rng.uniform(0, 3.14)
        for q in range(2):
            yaw = a0 + q * math.pi / 2 + rng.normal(0, 0.1); w = np.array([math.cos(yaw), math.sin(yaw), 0])
            for hlf in (0, 1):
                gcard(mb, w * (hlf - 0.5) * 0.45, yaw, 0.0, 0.0, 0.45, th * P['h'][1] * 0.95, t[(q * 2 + hlf) % len(t)], 1, rng.random(), False)
        recenter(mb); return mb.build(f'{name}_LOD{lod}', [mg_mat()])
    n = P['n']; pts = scatter(rng, n, P['size']); fam0 = rng.uniform(0, math.pi)
    keep = 1.0 if lod == 0 else 0.5; wm = 1.0 if lod == 0 else 1.3
    for i in range(n):
        key = rng.random(); yaw = fam0 + (i % 3) * math.pi / 3 + rng.normal(0, 0.3) + (math.pi if rng.random() < 0.5 else 0)
        tile = P['tiles'][rng.integers(len(P['tiles']))]; hs = rng.uniform(*P['h']); wd = 0.4 * rng.uniform(0.8, 1.1) * wm
        lean = rng.normal(0, P['lean']); arch = math.copysign(abs(rng.normal(0, P['arch'])), lean)
        args = (np.array([pts[i][0], pts[i][1], -0.012]), yaw, lean, arch, wd, th * hs, tile, 1 if short else 2, rng.random(), rng.random() < 0.5, rng.normal(0, 0.06))
        if key < keep: gcard(mb, *args)
    if P['wisp']:
        tl, k = P['wisp']
        for i in range(k):
            key = rng.random(); p = rng.uniform(-P['size'] * 0.42, P['size'] * 0.42, 2)
            args = (np.array([p[0], p[1], -0.01]), rng.uniform(0, 6.28), rng.normal(0, 0.15), rng.normal(0, 0.3), 0.4, th * rng.uniform(0.95, 1.12), tl, 2 if lod == 0 else 1, rng.random(), rng.random() < 0.5, 0.0)
            if key < keep: gcard(mb, *args)
    for i in range(P['thatch']):
        key = rng.random(); p = rng.uniform(-P['size'] * 0.3, P['size'] * 0.3, 2)
        if key < keep: flat(mb, (p[0], p[1], 0), rng.uniform(0, 6.28), 0.4 * rng.uniform(0.8, 1.1), 0.2 * rng.uniform(0.8, 1.1), ('TH0', 'TH1')[rng.integers(2)], rng.random())
    V = np.asarray(mb.v); V[:, 2] = np.maximum(V[:, 2], 0.0); mb.v = list(V); recenter(mb)
    return mb.build(f'{name}_LOD{lod}', [mg_mat()])
MEADOW = list(PATCH)
