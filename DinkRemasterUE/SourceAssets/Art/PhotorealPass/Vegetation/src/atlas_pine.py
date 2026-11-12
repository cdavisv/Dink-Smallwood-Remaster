"""Model eight conifer needle sprays, v2: thin pinnate branchlets, comb rows of short needles with real gaps (real needle geometry) and render the needle atlas passes. blender -b -t 4 --python atlas_pine.py"""
import bpy, sys, os, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas as A
WORK = os.path.join(HERE, '..', 'work')
TW, TH = 0.60, 0.30          # tile size in metres (1024 x 512 px): no spray card is longer than 60 cm
COLS, ROWS = 2, 4

def frame(d):
    d = d / np.linalg.norm(d)
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(d, a); u /= np.linalg.norm(u); v = np.cross(d, u)
    return d, u, v

class Build:
    def __init__(s): s.wv = []; s.wf = []; s.wc = []; s.nv = []; s.nf = []; s.nc = []
    def tube(s, pts, radii, col, sides=6):
        base = len(s.wv)
        for i, p in enumerate(pts):
            d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            _, u, v = frame(d)
            for k in range(sides):
                a = 2 * math.pi * k / sides
                s.wv.append(p + radii[i] * (math.cos(a) * u + math.sin(a) * v)); s.wc.append(col * (0.8 + 0.4 * np.random.random()))
        for i in range(len(pts) - 1):
            for k in range(sides):
                a = base + i * sides + k; b = base + i * sides + (k + 1) % sides
                s.wf.append((a, b, b + sides, a + sides))
    def needles(s, pts, rng, dens, nlen, frac0, age_fn, dead=0.0, width=0.0011):
        """needles along polyline pts from fraction frac0 to the tip."""
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1]
        # pine habit: a dense tuft on the last TUFT metres of each shoot, thinning older needles behind it, bare wood below
        TUFT = 0.085; OLD = 0.10
        a0 = max(0.0, L - TUFT - OLD); a1 = max(0.0, L - TUFT)
        if frac0 > 0.8: a0 = a1 = L * frac0
        n_t = int((L - a1) * dens); n_o = int((a1 - a0) * dens * 0.3)
        ts = np.concatenate([a0 + (a1 - a0) * rng.random(n_o), a1 + (L - a1) * (np.arange(n_t) + rng.random(n_t)) / max(n_t, 1)]) / L
        ts = np.sort(ts); phi = rng.random() * 6.28
        for j in range(len(ts)):
            t = float(ts[j])
            sdist = t * L; i = min(np.searchsorted(cum, sdist) - 1, len(pts) - 2); i = max(i, 0)
            p = pts[i] + (pts[i + 1] - pts[i]) * ((sdist - cum[i]) / max(seg[i], 1e-9))
            d, u, v = frame(pts[i + 1] - pts[i])
            phi += 2.399963 + rng.normal(0, 0.3)
            inc = math.radians(rng.uniform(24, 58)) * (1.0 - 0.6 * max(0, (t * L - (L - 0.03)) / 0.03))
            out = math.cos(phi) * u + math.sin(phi) * v
            nd = math.cos(inc) * d + math.sin(inc) * out
            ln = nlen * rng.uniform(0.75, 1.15)
            bend = out * rng.normal(0, 0.12) + d * rng.uniform(0.0, 0.25)
            age = age_fn(t)
            if rng.random() < dead: col = np.array([0.22, 0.11, 0.04]) * rng.uniform(0.7, 1.3)
            else:
                young = np.array([0.085, 0.17, 0.045]); mid = np.array([0.028, 0.078, 0.036]); old = np.array([0.016, 0.044, 0.026])   # blue-green, lighter new growth
                col = (young * (1 - age * 2) + mid * age * 2) if age < 0.5 else (mid * (2 - age * 2) + old * (age * 2 - 1))
                col = col * rng.uniform(0.75, 1.3) * np.array([rng.uniform(0.9, 1.15), 1, rng.uniform(0.8, 1.2)])
            _, nu, nv_ = frame(nd)
            base = len(s.nv)
            for r_, (tt, wr) in enumerate(((0, 1.0), (0.5, 0.9), (1.0, 0.15))):
                c = p + nd * ln * tt + bend * ln * tt * tt
                for k in range(3):
                    a = 2.094 * k
                    s.nv.append(c + width * wr * (math.cos(a) * nu + math.sin(a) * nv_))
                    s.nc.append(col * (0.8 + 0.3 * tt))
            for r_ in range(2):
                for k in range(3):
                    a = base + r_ * 3 + k; b = base + r_ * 3 + (k + 1) % 3
                    s.nf.append((a, b, b + 3, a + 3))

def curve(p0, d0, L, rng, n=10, wander=0.15, droop=0.0):
    pts = [np.array(p0, float)]; d = np.array(d0, float); d /= np.linalg.norm(d)
    for i in range(n):
        d = d + rng.normal(0, wander / n ** 0.5, 3) * np.array([1, 1, 0.5]) + np.array([0, 0, -droop / n])
        d /= np.linalg.norm(d); pts.append(pts[-1] + d * L / n)
    return np.array(pts)

ZUP = np.array([0, 0, 1.0])
def comb(b, pts, rng, pitch, nlen, age_fn, dead=0.0, shed=0.0, start=0.0, width=0.0014, top=0.25):
    """v2 needles: two comb rows (left and right of the twig, in the spray plane) with a real gap between neighbouring needles (`pitch` metres),
    plus a few on top. Stretches of the twig are shed (bare wood). Needles are short, so a twig reads as a thin feathered line, not a lobe."""
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1]
    if L < 0.01: return
    s = start * L + rng.uniform(0, pitch); gap_until = -1.0
    while s < L:
        t = s / L
        if s > gap_until and rng.random() < shed * pitch / 0.02: gap_until = s + rng.uniform(0.008, 0.035)       # a shed stretch
        if s < gap_until: s += pitch; continue
        i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2)); p = pts[i] + (pts[i + 1] - pts[i]) * ((s - cum[i]) / max(seg[i], 1e-9))
        d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d); perp = np.cross(ZUP, d); perp /= (np.linalg.norm(perp) + 1e-9)
        age = age_fn(t); tipf = 1.0 - 0.45 * max(0.0, (s - (L - 0.02)) / 0.02)          # needles shorten and close up at the shoot tip
        rows = [(-1, False), (1, False)] + ([(rng.choice([-1, 1]), True)] if rng.random() < top else [])
        for sd, ontop in rows:
            if rng.random() < 0.07: continue
            inc = math.radians(rng.uniform(52, 72)) * tipf; el = rng.normal(0.25, 0.2) if not ontop else rng.uniform(0.9, 1.3)
            out = sd * perp * math.cos(el) + ZUP * math.sin(el); nd = math.cos(inc) * d + math.sin(inc) * out
            ln = nlen * rng.uniform(0.8, 1.15) * (0.75 + 0.25 * tipf); bend = d * rng.uniform(0.05, 0.3) + out * rng.normal(0, 0.08)
            if rng.random() < dead: col = np.array([0.22, 0.11, 0.04]) * rng.uniform(0.7, 1.3)
            else:
                young = np.array([0.085, 0.17, 0.045]); mid = np.array([0.028, 0.078, 0.036]); old = np.array([0.016, 0.044, 0.026])
                col = (young * (1 - age * 2) + mid * age * 2) if age < 0.5 else (mid * (2 - age * 2) + old * (age * 2 - 1))
                col = col * rng.uniform(0.75, 1.3) * np.array([rng.uniform(0.9, 1.15), 1, rng.uniform(0.8, 1.2)])
            _, nu, nv_ = frame(nd); base = len(b.nv); pb = p + rng.normal(0, 0.0006, 3)
            for r_, (tt, wr) in enumerate(((0, 0.9), (0.5, 1.0), (1.0, 0.2))):
                c = pb + nd * ln * tt + bend * ln * tt * tt
                for k in range(3):
                    a = 2.094 * k; b.nv.append(c + width * wr * (math.cos(a) * nu + math.sin(a) * nv_)); b.nc.append(col * (0.8 + 0.3 * tt))
            for r_ in range(2):
                for k in range(3):
                    a = base + r_ * 3 + k; bb = base + r_ * 3 + (k + 1) % 3; b.nf.append((a, bb, bb + 3, a + 3))
        s += pitch * rng.uniform(0.85, 1.15)

def rot2(d, ang, z=0.0):
    v = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang), z]); return v / np.linalg.norm(v)

def spray(b, origin, seed, main_len=0.57, step=0.03, side_len=0.185, pitch=0.0031, nlen=0.018, dead=0.01, shed=0.05, age_shift=0.0, second=1.0,
          skip=0.08, bare_main=0.12, shape=0.75, hang=False, wood_only=False):
    """v2 spray: a thin branchlet with many slender side twigs (pinnate, like a spruce / fir frond); every twig is a narrow comb of short needles
    with open sky between neighbouring twigs."""
    rng = np.random.default_rng(seed); o = np.array(origin, float); wood = np.array([0.05, 0.03, 0.017])
    main = curve(o + [0.01, 0, 0], [1, rng.normal(0, 0.05), 0], main_len, rng, 16, 0.10)
    main[:, 1] = np.clip(main[:, 1], o[1] - TH * 0.2, o[1] + TH * 0.2)
    b.tube(main, np.linspace(0.0042, 0.0013, len(main)), wood)
    age = lambda t: np.clip(0.75 - 0.75 * t + age_shift, 0, 1)
    if not wood_only or True: comb(b, main, rng, pitch, nlen, age, dead, shed, start=bare_main)
    seg = np.linalg.norm(np.diff(main, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); LL = cum[-1]
    s = 0.035 + rng.uniform(0, step); k = 0
    while s < LL - 0.03:
        t = s / LL; side = 1 if k % 2 == 0 else -1; k += 1
        if rng.random() < skip: s += step * rng.uniform(0.35, 0.65); continue
        i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(main) - 2)); p = main[i] + (main[i + 1] - main[i]) * ((s - cum[i]) / seg[i]); d = main[i + 1] - main[i]; d /= np.linalg.norm(d)
        ang = math.radians(rng.uniform(42, 62) if not hang else rng.uniform(22, 40)) * side
        dd = rot2(d, ang, rng.normal(0, 0.12))
        env = (math.sin(math.pi * min(1.0, 0.12 + t * 0.95) ** shape) ** 0.25) if not hang else (1 - 0.6 * t)       # a broad frond: side twigs keep their length almost to the tip
        L = side_len * env * rng.uniform(0.5, 1.12) + 0.018          # uneven twig lengths: the frond outline is notched at twig scale, which survives mipping
        maxL = (TH * 0.475 - abs(p[1] - o[1])) / max(abs(dd[1]), 0.2)
        L = max(0.02, min(L, maxL, (o[0] + TW * 0.985 - p[0]) / max(dd[0], 0.2)))
        pts = curve(p, dd, L, rng, 7, 0.14, 0.03); pts[:, 1] = np.clip(pts[:, 1], o[1] - TH * 0.485, o[1] + TH * 0.485)
        b.tube(pts, np.linspace(0.0022, 0.0009, len(pts)), wood, 4)
        comb(b, pts, rng, pitch, nlen * 0.95, lambda tt: np.clip(0.6 - 0.6 * tt + age_shift, 0, 1), dead, shed, start=0.1)
        if L > 0.05:            # third order: short twiglets, mostly on the outer side of the twig
            nq = int(L / 0.028 * second + rng.random())
            for q in range(nq):
                f = 0.25 + 0.6 * (q + rng.uniform(0.2, 0.8)) / max(nq, 1); j = int((len(pts) - 2) * f); d2 = pts[j + 1] - pts[j]; d2 /= np.linalg.norm(d2)
                a2 = math.radians(rng.uniform(38, 58)) * (side if q % 2 == 0 else -side)
                dd2 = rot2(d2, a2, rng.normal(0, 0.1)); L2 = max(0.018, L * rng.uniform(0.22, 0.42) * (1 - 0.5 * f))
                if abs(pts[j][1] + dd2[1] * L2 - o[1]) > TH * 0.48 or pts[j][0] + dd2[0] * L2 > o[0] + TW * 0.985: continue
                p2 = curve(pts[j], dd2, L2, rng, 4, 0.12); b.tube(p2, np.linspace(0.0013, 0.0008, len(p2)), wood, 3)
                comb(b, p2, rng, pitch, nlen * 0.85, lambda tt: np.clip(0.4 - 0.4 * tt + age_shift, 0, 1), dead, shed, start=0.05)
        s += step * rng.uniform(0.75, 1.25)

A.reset(); scene = bpy.context.scene
np.random.seed(3)
b = Build()
tiles = [
    dict(seed=11, step=0.032, second=0.85, nlen=0.016),                                 # 0 dense tip A (v4: open sky between neighbouring side twigs)
    dict(seed=23, step=0.031, side_len=0.18, second=0.85, nlen=0.016),                  # 1 dense tip B
    dict(seed=31, step=0.03, side_len=0.10, hang=True, second=0.8),                   # 2 narrow hanging tip
    dict(seed=47, step=0.04, side_len=0.18, second=0.6, age_shift=0.25, skip=0.2, shed=0.12),      # 3 open spray: sky between the twigs
    dict(seed=53, step=0.045, side_len=0.16, second=0.4, age_shift=0.45, dead=0.06, skip=0.25, shed=0.3),   # 4 sparse old growth
    dict(seed=59, main_len=0.5, step=0.031, side_len=0.17, age_shift=-0.4, second=0.85, nlen=0.016),            # 5 light new growth
    dict(seed=67, step=0.05, side_len=0.12, dead=0.55, age_shift=0.5, second=0.3, skip=0.25, shed=0.5),    # 6 half dead interior
    dict(seed=71, step=0.045, side_len=0.14, dead=0.9, second=0.8, shed=3.5, pitch=0.006),                 # 7 bare dead twig
]
for i, t in enumerate(tiles):
    c, r = i % COLS, i // COLS
    spray(b, (c * TW, (ROWS - 1 - r) * TH + TH / 2, 0), **t)
wood = A.mesh_obj('wood', b.wv, np.array(b.wf, dtype=np.int32), b.wc)
need = A.mesh_obj('needles', b.nv, np.array(b.nf, dtype=np.int32), b.nc)
print('needles verts', len(b.nv))
def rebuild(mode):
    mw = A.pass_material('wood', mode, A.attr_col(), rough=0.85, sss=(0.01, 0.006, 0.003))
    def sss(N, L):
        a = N.new('ShaderNodeAttribute'); a.attribute_name = 'Col'
        m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'; m.inputs[0].default_value = 1
        L.new(a.outputs['Color'], m.inputs[6]); m.inputs[7].default_value = (1.85, 1.7, 0.85, 1)
        return m.outputs[2]
    mn = A.pass_material('needle', mode, A.attr_col(), rough=0.77, sss=sss)
    wood.data.materials.clear(); wood.data.materials.append(mw)
    need.data.materials.clear(); need.data.materials.append(mn)
A.render_atlas(scene, COLS * TW, ROWS * TH, 2048, 2048, os.path.join(WORK, 'pine_atlas'), rebuild, samples=12)
