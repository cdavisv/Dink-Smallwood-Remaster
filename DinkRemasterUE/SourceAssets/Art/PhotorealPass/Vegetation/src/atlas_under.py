"""Understory atlas (T_Veg_Understory, 2048^2 = 2 m x 2 m): bush sprays, bare twig sprays, fern fronds, grass clump cards, vine strands.
All modelled from leaves / twigs and rendered. blender -b -t 4 --python atlas_under.py"""
import bpy, sys, os, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas as A
WORK = os.path.join(HERE, '..', 'work'); TP = os.path.join(HERE, '..', '..', 'ThirdParty')
A.reset(); scene = bpy.context.scene
UP = np.array([0, 0, 1.0])
L22 = f'{TP}/ambientcg/LeafSet022/LeafSet022_2K-JPG_'
BB = [(140, 1094, 582, 1975), (140, 61, 582, 933), (1466, 1073, 1855, 1948), (834, 1098, 1208, 1972), (834, 78, 1208, 950), (1466, 112, 1855, 928)]
R22 = [(x0 / 2048, 1 - y1 / 2048, x1 / 2048, 1 - y0 / 2048) for x0, y0, x1, y1 in BB]
leaf = A.Geo(); wl = A.Geo(); wood = A.Geo()      # scanned-leaf geometry, willow-leaf-textured geometry, wood
BROWN = np.array([0.045, 0.033, 0.024]); GREYTW = np.array([0.035, 0.03, 0.027])

def rot2(d, ang, z=0.0):
    return np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang), z])

def bush_spray(o, w, h, seed, dens=1.0):
    rng = np.random.default_rng(seed); o = np.array(o, float)
    main = A.curve(o + [0.004, 0, 0], [1, rng.normal(0, 0.1), 0], w * 0.88, rng, 12, 0.3)
    wood.tube(main, np.linspace(0.004, 0.0015, len(main)), BROWN, 5, rng); twigs = [(main, 0.2)]
    for k in range(11):
        t = 0.1 + 0.8 * (k + rng.uniform(-0.3, 0.3)) / 11; i = int(t * (len(main) - 1)); d = main[min(i + 1, len(main) - 1)] - main[i - 1 if i else 0]; d /= np.linalg.norm(d)
        dd = rot2(d, math.radians(rng.uniform(35, 70)) * (1 if k % 2 else -1), rng.normal(0, 0.15))
        L = min(w * 0.42 * rng.uniform(0.5, 1.0), (h * 0.46 - abs(main[i][1] - o[1])) / max(abs(dd[1]), 0.3), (o[0] + w * 0.95 - main[i][0]) / max(dd[0], 0.3))
        if L < 0.04: continue
        pts = A.curve(main[i], dd, L, rng, 6, 0.3); wood.tube(pts, np.linspace(0.0022, 0.001, len(pts)), BROWN, 4, rng); twigs.append((pts, 0.1))
    for pts, f0 in twigs:
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); s = f0 * cum[-1]; k = 0
        while s < cum[-1]:
            i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2)); p = pts[i] + (pts[i + 1] - pts[i]) * (s - cum[i]) / seg[i]; d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d)
            ln = rng.uniform(0.032, 0.052); room = h * 0.49 - abs(p[1] - o[1]); ln = min(ln, max(0.02, room * 1.3))
            v = rng.uniform(0.32, 0.75); tint = np.array([v * rng.uniform(0.55, 0.8), v * rng.uniform(0.85, 1.0), v * rng.uniform(0.4, 0.6)])
            dd = rot2(d, math.radians(rng.uniform(30, 80)) * (1 if k % 2 else -1), rng.normal(0, 0.3))
            if rng.random() < dens: leaf.leaf(p + [0, 0, rng.normal(0, 0.008)], dd, UP + rng.normal(0, 0.5, 3) * np.array([1, 1, 0.3]), ln, ln * 0.52, R22[rng.integers(6)], tint, fold=0.2, curl=rng.uniform(-0.1, 0.3), twist=rng.normal(0, 0.3), nu=2, nv=4)
            k += 1; s += 0.007 * rng.uniform(0.6, 1.5)

def twig_spray(o, w, h, seed, col=GREYTW, r0=0.006):
    rng = np.random.default_rng(seed); o = np.array(o, float)
    def grow(p, d, L, r, depth):
        pts = A.curve(p, d, L, rng, 8, 0.45); pts[:, 1] = np.clip(pts[:, 1], o[1] - h * 0.48, o[1] + h * 0.48); pts[:, 0] = np.clip(pts[:, 0], o[0] + 0.003, o[0] + w * 0.985); wood.tube(pts, np.linspace(r, r * 0.35, len(pts)), col, 5 if depth == 0 else 4, rng)
        if depth >= 3 or L < 0.05: return
        for k in range(int(rng.integers(3, 6)) if depth < 2 else 2):
            j = int(rng.uniform(0.2, 0.9) * (len(pts) - 2)); dd = pts[j + 1] - pts[j]; dd /= np.linalg.norm(dd)
            d2 = rot2(dd, math.radians(rng.uniform(25, 60)) * rng.choice([-1, 1]), rng.normal(0, 0.1)); L2 = L * rng.uniform(0.35, 0.6)
            end = pts[j] + d2 * L2
            if abs(end[1] - o[1]) > h * 0.47 or end[0] > o[0] + w * 0.97 or end[0] < o[0] + 0.01: continue
            grow(pts[j], d2, L2, r * 0.55, depth + 1)
    grow(o + [0.004, 0, 0], np.array([1, rng.normal(0, 0.08), 0]), w * 0.82, r0, 0)

def fern(o, w, h, seed):
    rng = np.random.default_rng(seed); o = np.array(o, float)
    rach = A.curve(o + [0.004, 0, 0], [1, rng.normal(0, 0.04), 0], w * 0.94, rng, 30, 0.06)
    wood.tube(rach, np.linspace(0.004, 0.0008, len(rach)), np.array([0.07, 0.10, 0.03]), 5, rng)
    n = 46
    for k in range(n):
        t = 0.08 + 0.9 * k / n; i = int(t * (len(rach) - 1)); p = rach[i]; d = rach[min(i + 1, len(rach) - 1)] - rach[i - 1]; d /= np.linalg.norm(d)
        L = h * 0.47 * (math.sin(math.pi * min(1.0, (t - 0.04) ** 0.75)) ** 0.9) * rng.uniform(0.9, 1.05) + 0.012
        for sd in (-1, 1):
            dd = rot2(d, math.radians(rng.uniform(62, 76)) * sd, rng.normal(0, 0.08)); v = rng.uniform(0.75, 1.2)
            # each pinna is itself toothed: a row of small pinnules along its length
            m = max(3, int(L / 0.011)); pin = p.copy()
            for q in range(m):
                tq = (q + 0.5) / m; pl = 0.02 * (1 - tq) ** 0.6 + 0.004
                for s2 in (-1, 1):
                    d3 = rot2(dd, math.radians(rng.uniform(55, 70)) * s2, rng.normal(0, 0.1))
                    wl.leaf(p + dd * L * tq, d3, UP + rng.normal(0, 0.25, 3) * np.array([1, 1, 0.2]), pl, pl * 0.42, (0, 0, 1, 1), np.array([0.75, 1.0, 0.6]) * v * rng.uniform(0.85, 1.15), fold=0.2, curl=0.1, nu=2, nv=2)
            wood.tube(np.array([p, p + dd * L]), [0.0012, 0.0004], np.array([0.07, 0.10, 0.03]), 3, rng)

def grass(o, w, h, seed, n=46, dry=0.25):
    rng = np.random.default_rng(seed); o = np.array(o, float); base = o + [w / 2, 0.004, 0]
    for k in range(n):
        x = float(np.clip(rng.normal(0, w * 0.07), -w * 0.2, w * 0.2)); a = float(np.clip(rng.normal(0, 0.36) + x / w * 2.0, -0.75, 0.75)); L = h * rng.uniform(0.45, 0.97)
        b = base + [x, 0, rng.normal(0, 0.01)]; isdry = rng.random() < dry
        tint = (np.array([2.6, 1.9, 1.3]) if isdry else np.array([0.9, 1.0, 0.7])) * rng.uniform(0.7, 1.25)
        # curved blade: three leaf segments bending over
        d = np.array([math.sin(a), math.cos(a), 0.0]); p = b.copy(); bend = rng.normal(0, 0.5) + a * 0.6
        segs = 3; wdt = rng.uniform(0.008, 0.013)
        for s_ in range(segs):
            Ls = L / segs
            if s_ == segs - 1: wl.leaf(p, d, UP, Ls, wdt, (0.0, 0.38, 1.0, 1.0), tint, fold=0.3, curl=0, nu=2, nv=3)
            else: wl.leaf(p, d, UP, Ls * 1.02, wdt, (0.0, 0.36, 1.0, 0.40), tint, fold=0.3, curl=0, nu=2, nv=2)
            p = p + d * Ls; d = rot2(d, -bend / segs * 0.8); d /= np.linalg.norm(d)
            end_x = abs(p[0] - (o[0] + w / 2))
            if end_x > w * 0.40 or p[1] > o[1] + h * 0.9:
                break

def vine(o, w, h, seed):
    rng = np.random.default_rng(seed); o = np.array(o, float)
    for s_ in range(2):
        pts = [o + [0.004, (s_ - 0.5) * 0.03, 0]]; n = 40
        for i in range(n):
            t = (i + 1) / n; y = o[1] + h * 0.28 * math.sin(t * rng.uniform(9, 11) + s_ * 3.1 + seed) * (0.5 + 0.5 * math.sin(t * 3 + s_))
            pts.append(np.array([o[0] + 0.004 + t * w * 0.97, y, 0.012 * math.cos(t * 10 + s_ * 3.1)]))
        pts = np.array(pts); wood.tube(pts, np.linspace(0.007, 0.003, len(pts)), np.array([0.05, 0.045, 0.025]), 6, rng)
        for i in range(2, n, 2):
            if rng.random() < 0.55:
                d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d); dd = rot2(d, math.radians(rng.uniform(40, 100)) * rng.choice([-1, 1]), rng.normal(0, 0.2))
                ln = rng.uniform(0.035, 0.06); room = h * 0.48 - abs(pts[i][1] - o[1]); ln = min(ln, max(0.02, room))
                v = rng.uniform(0.3, 0.6); leaf.leaf(pts[i], dd, UP + rng.normal(0, 0.4, 3) * np.array([1, 1, 0.3]), ln, ln * 0.6, R22[rng.integers(6)], np.array([v * 0.6, v, v * 0.45]), fold=0.2, curl=0.2, nu=2, nv=4)
            if rng.random() < 0.25:   # tendril
                d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d); t2 = A.curve(pts[i], rot2(d, rng.uniform(-1.5, 1.5)), 0.06, rng, 6, 0.9)
                t2[:, 1] = np.clip(t2[:, 1], o[1] - h * 0.47, o[1] + h * 0.47); wood.tube(t2, np.linspace(0.0015, 0.0006, len(t2)), np.array([0.06, 0.07, 0.03]), 3, rng)

# layout (metres, origin bottom-left). Row A y 1.5-2.0, B 1.0-1.5, C 0.6-1.0, D 0.0-0.6
for i in range(3): bush_spray((i * 0.5, 1.75, 0), 0.5, 0.5, 20 + i, dens=(1.0, 1.0, 0.7)[i])
twig_spray((1.5, 1.75, 0), 0.5, 0.5, 31)
fern((0.0, 1.25, 0), 1.0, 0.5, 41); fern((1.0, 1.25, 0), 1.0, 0.5, 42)
for i in range(4): grass((i * 0.5, 0.6, 0), 0.5, 0.4, 50 + i, n=(50, 40, 56, 34)[i], dry=(0.15, 0.3, 0.2, 0.6)[i])
vine((0.0, 0.45, 0), 1.0, 0.3, 61); vine((0.0, 0.15, 0), 1.0, 0.3, 62)
twig_spray((1.0, 0.3, 0), 1.0, 0.6, 71, r0=0.011)
lo = leaf.obj('leaves'); wo = wood.obj('wood'); wlo = wl.obj('wl')
def rebuild(mode):
    ml = A.leaf_mats(mode, 'leaf', L22 + 'Color.jpg', L22 + 'Opacity.jpg', L22 + 'NormalGL.jpg', rough=0.5)
    mw2 = A.leaf_mats(mode, 'wl', f'{WORK}/willow_leaf_c.png', f'{WORK}/willow_leaf_a.png', f'{WORK}/willow_leaf_n.png', rough=0.5)
    mw = A.pass_material('wood', mode, A.attr_col(), rough=0.85, sss=(0.01, 0.008, 0.004))
    for o, m in ((lo, ml), (wlo, mw2), (wo, mw)): o.data.materials.clear(); o.data.materials.append(m)
A.render_atlas(scene, 2.0, 2.0, 2048, 2048, os.path.join(WORK, 'under_atlas'), rebuild, samples=12)
