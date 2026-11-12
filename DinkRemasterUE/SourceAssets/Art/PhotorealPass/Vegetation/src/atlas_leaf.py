"""Model leaf sprays from single leaves and render cluster atlases. blender -b -t 4 --python atlas_leaf.py -- oak|willow"""
import bpy, sys, os, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas as A
WORK = os.path.join(HERE, '..', 'work'); TP = os.path.join(HERE, '..', '..', 'ThirdParty')
which = sys.argv[sys.argv.index('--') + 1]
A.reset(); scene = bpy.context.scene
UP = np.array([0, 0, 1.0])

def leaf_on(g, p, twig_d, rng, length, width, rect, side, spread=(40, 75), tilt=0.5, tintf=None, **kw):
    ang = math.radians(rng.uniform(*spread)) * side
    d = np.array([twig_d[0] * math.cos(ang) - twig_d[1] * math.sin(ang), twig_d[0] * math.sin(ang) + twig_d[1] * math.cos(ang), rng.normal(0, 0.25)])
    n = UP + rng.normal(0, tilt, 3) * np.array([1, 1, 0.3])
    g.leaf(p, d, n, length, width, rect, tintf(rng), **kw)

if which == 'oak':
    TW = 0.8; COLS = ROWS = 2
    base = f'{TP}/ambientcg/LeafSet016/LeafSet016_2K-JPG_'
    rects = [(c / 3 + 0.01, 1 - (r + 1) / 2 + 0.01, (c + 1) / 3 - 0.01, 1 - r / 2 - 0.01) for r in range(2) for c in range(3)]
    def tint(rng):
        v = rng.uniform(0.3, 0.68)
        return np.array([v * rng.uniform(0.55, 0.85), v * rng.uniform(0.85, 1.0), v * rng.uniform(0.35, 0.6)])
    g = A.Geo(); w = A.Geo(); wood = np.array([0.055, 0.045, 0.035])
    def spray(origin, seed, main_len=0.72, side_n=9, side_len=0.34, leaf_gap=0.015, tuft=False, sparse=1.0):
        rng = np.random.default_rng(seed); o = np.array(origin, float)
        main = A.curve(o + [0.005, 0, 0], [1, rng.normal(0, 0.1), 0], main_len, rng, 14, 0.25)
        w.tube(main, np.linspace(0.006, 0.002, len(main)), wood, 6, rng)
        twigs = [(main, 0.35 if not tuft else 0.6)]
        for k in range(side_n):
            t = 0.12 + 0.75 * (k + rng.uniform(-0.3, 0.3)) / side_n; i = int(t * (len(main) - 1))
            d = main[i + 1] - main[i]; d /= np.linalg.norm(d); sd = 1 if k % 2 == 0 else -1
            ang = math.radians(rng.uniform(35, 65)) * sd
            dd = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang), rng.normal(0, 0.1)])
            L = side_len * rng.uniform(0.6, 1.1) * (1 - 0.5 * t)
            L = min(L, (TW * 0.44 - abs(main[i][1] - o[1])) / max(abs(dd[1]), 0.25), (o[0] + TW * 0.93 - main[i][0]) / max(dd[0], 0.25))
            if L < 0.05: continue
            pts = A.curve(main[i], dd, L, rng, 8, 0.3)
            w.tube(pts, np.linspace(0.003, 0.0015, len(pts)), wood, 5, rng); twigs.append((pts, 0.15))
        for pts, f0 in twigs:
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1]
            s = f0 * L; k = 0
            while s < L:
                i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2)); p = pts[i] + (pts[i + 1] - pts[i]) * (s - cum[i]) / seg[i]
                d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d); t = s / L
                ln = rng.uniform(0.085, 0.13) * (0.8 + 0.3 * t)
                if rng.random() < sparse:
                    yb = abs(p[1] - o[1]); room = TW * 0.48 - yb
                    ln = min(ln, max(0.05, room * 1.2))
                    leaf_on(g, p + [0, 0, rng.normal(0, 0.012)], d, rng, ln, ln * rng.uniform(0.58, 0.7), rects[rng.integers(6)], 1 if k % 2 == 0 else -1, tintf=tint,
                            spread=(30, 80) if t < 0.85 else (0, 40), fold=rng.uniform(0.05, 0.25), curl=rng.uniform(-0.1, 0.3), twist=rng.normal(0, 0.3), wave=0.04)
                k += 1; s += leaf_gap * rng.uniform(0.6, 1.5) * (1.6 - t)   # leaves crowd toward the shoot tip
            # terminal rosette
            d = pts[-1] - pts[-2]; d /= np.linalg.norm(d)
            for q in range(5):
                ln = min(rng.uniform(0.09, 0.13), max(0.05, (o[0] + TW * 0.99 - pts[-1][0])))
                leaf_on(g, pts[-1], d, rng, ln, ln * 0.64, rects[rng.integers(6)], rng.choice([-1, 1]), tintf=tint, spread=(0, 75), fold=0.15, curl=rng.uniform(0, 0.3), wave=0.04)
    spray((0, TW * 1.5, 0), 3)
    spray((TW, TW * 1.5, 0), 8, side_n=10, side_len=0.36)
    spray((0, TW * 0.5, 0), 15, side_n=6, side_len=0.28, sparse=0.7)
    spray((TW, TW * 0.5, 0), 21, main_len=0.55, side_n=8, side_len=0.34, tuft=True, leaf_gap=0.012)
    lo = g.obj('leaves'); wo = w.obj('wood')
    def rebuild(mode):
        ml = A.leaf_mats(mode, 'leaf', base + 'Color.jpg', base + 'Opacity.jpg', base + 'NormalGL.jpg', rough=0.62)
        mw = A.pass_material('wood', mode, A.attr_col(), rough=0.85, sss=(0.01, 0.006, 0.003))
        lo.data.materials.clear(); lo.data.materials.append(ml); wo.data.materials.clear(); wo.data.materials.append(mw)
    A.render_atlas(scene, TW * COLS, TW * ROWS, 2048, 2048, os.path.join(WORK, 'oak_atlas'), rebuild)

if which == 'willow':
    TWd, THt = 0.5, 2.0; COLS = 4
    g = A.Geo(); gy = A.Geo(); w = A.Geo(); wood = np.array([0.16, 0.15, 0.035])
    def tint(rng):
        v = rng.uniform(0.6, 1.25); return np.array([v * rng.uniform(0.85, 1.15), v, v * rng.uniform(0.7, 1.1)])
    def strand(col, seed, n_withes, length=1.9, gap=0.03, spread=0.3):
        rng = np.random.default_rng(seed); x0 = col * TWd + TWd / 2
        for k in range(n_withes):
            xs = x0 + (k - (n_withes - 1) / 2) * spread / max(1, n_withes) + rng.normal(0, 0.015)
            L = length * rng.uniform(0.72, 1.0) if k else length
            pts = A.curve([xs, THt - 0.005, rng.normal(0, 0.02)], [rng.normal(0, 0.12), -1, 0], L, rng, 24, 0.22, droop=0.6, grav=(0, -1, 0))
            pts[:, 0] = np.clip(pts[:, 0], col * TWd + 0.07, (col + 1) * TWd - 0.07)
            w.tube(pts, np.linspace(0.0035, 0.0012, len(pts)), wood, 5, rng)
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)])
            s = 0.04; j = 0
            while s < cum[-1]:
                i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2)); p = pts[i] + (pts[i + 1] - pts[i]) * (s - cum[i]) / seg[i]
                d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d)
                ln = rng.uniform(0.075, 0.12) * (1 - 0.35 * (s / cum[-1]) ** 3)
                room = min(p[0] - col * TWd, (col + 1) * TWd - p[0]) - 0.012
                tgt = gy if rng.random() < 0.06 else g
                sd = 1 if j % 2 == 0 else -1
                ang = math.radians(rng.uniform(22, 55)) * sd
                dd = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang), rng.normal(0, 0.3)])
                ln = min(ln, max(0.03, room / max(abs(dd[0]), 0.3)))
                tgt.leaf(p, dd, UP + rng.normal(0, 0.6, 3) * np.array([1, 1, 0.2]), ln, max(0.014, ln * 0.17), (0, 0, 1, 1), tint(rng), fold=0.25, curl=rng.uniform(-0.1, 0.35), twist=rng.normal(0, 0.5), nu=2, nv=5)
                j += 1; s += gap * rng.uniform(0.6, 1.4)
    strand(0, 4, 5, gap=0.024); strand(1, 9, 4, gap=0.028); strand(2, 14, 3, gap=0.03, spread=0.22); strand(3, 19, 6, length=1.25, gap=0.022, spread=0.34)
    lo = g.obj('leaves'); ly = gy.obj('leavesy'); wo = w.obj('wood')
    def rebuild(mode):
        ml = A.leaf_mats(mode, 'leaf', f'{WORK}/willow_leaf_c.png', f'{WORK}/willow_leaf_a.png', f'{WORK}/willow_leaf_n.png', rough=0.52)
        my = A.leaf_mats(mode, 'leafy', f'{WORK}/willow_leaf_y_c.png', f'{WORK}/willow_leaf_y_a.png', f'{WORK}/willow_leaf_y_n.png', rough=0.5)
        mw = A.pass_material('wood', mode, A.attr_col(), rough=0.6, sss=(0.02, 0.02, 0.004))
        for o, m in ((lo, ml), (ly, my), (wo, mw)): o.data.materials.clear(); o.data.materials.append(m)
    A.render_atlas(scene, TWd * COLS, THt, 2048, 2048, os.path.join(WORK, 'willow_atlas'), rebuild)
