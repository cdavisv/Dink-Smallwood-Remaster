"""Shrub atlas (work/shrub_atlas_*.png -> T_Veg_Shrub, 2048^2 = 2 m x 2 m, 4 x 4 tiles of 0.5 m), all modelled from scanned single leaves and rendered:
  row 0 (top)  leaf type A (ovate, ambientCG LeafSet022): spray light / mid / mid / dark-interior
  row 1        leaf type B (three-lobed, ambientCG LeafSet029): spray light / mid / mid / dark-interior
  row 2        A sparse (twiggy, half bare), B sparse, bare dead twig spray, bare dead twig spray 2
  row 3        A with yellowing leaves, B with yellowing leaves, A open shoots, B open shoots
The light / dark grading is done afterwards by compose_shrub.py.   blender -b -t 4 --python atlas_shrub.py"""
import bpy, sys, os, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas as A
WORK = os.path.join(HERE, '..', 'work'); TP = os.path.join(HERE, '..', '..', 'ThirdParty')
A.reset(); scene = bpy.context.scene
UP = np.array([0, 0, 1.0]); TS = 0.5
L22 = f'{TP}/ambientcg/LeafSet022/LeafSet022_2K-JPG_'; L29 = f'{TP}/ambientcg/LeafSet029/LeafSet029_2K-JPG_'
BB22 = [(140, 1094, 582, 1975), (140, 61, 582, 933), (1466, 1073, 1855, 1948), (834, 1098, 1208, 1972), (834, 78, 1208, 950), (1466, 112, 1855, 928)]
BB29 = [(86, 86, 615, 606), (732, 102, 1324, 630), (1447, 94, 1978, 586), (143, 758, 597, 1303), (719, 726, 1340, 1325), (1426, 711, 2008, 1342), (31, 1401, 649, 2022)]
BB29Y = [(849, 1466, 1300, 1933), (1556, 1512, 1942, 1893)]         # the two yellowing leaves
rc = lambda bb: [(x0 / 2048, 1 - y1 / 2048, x1 / 2048, 1 - y0 / 2048) for x0, y0, x1, y1 in bb]
R22 = rc(BB22); R29 = rc(BB29); R29Y = rc(BB29Y)
la = A.Geo(); lb = A.Geo(); wood = A.Geo()
BROWN = np.array([0.045, 0.033, 0.024]); GREY = np.array([0.038, 0.032, 0.028])

def rot2(d, ang, z=0.0):
    return np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang), z])

def leaf(G, base, d, n, length, width, uvrect, tint, sideways=False, fold=0.15, curl=0.1, twist=0.0, nu=2, nv=4):
    """as bl_atlas.Geo.leaf, plus sideways=True for scans whose leaf lies along +U (stalk at u0, tip at u1)"""
    d = d / np.linalg.norm(d); n = n - d * np.dot(n, d); n /= np.linalg.norm(n); side = np.cross(d, n)
    u0, v0, u1, v1 = uvrect; b0 = len(G.v); idx = {}
    for j in range(nv + 1):
        t = j / nv; tw = twist * t; sd = side * math.cos(tw) + n * math.sin(tw); nn = np.cross(sd, d)
        c = np.asarray(base) + d * length * t + nn * (-curl) * length * t * t
        for i in range(nu + 1):
            x = i / nu - 0.5
            G.v.append(c + sd * x * width + nn * (fold * abs(x) * width)); G.c.append(tint)
            idx[(i, j)] = (u0 + (u1 - u0) * t, v0 + (v1 - v0) * (1 - i / nu)) if sideways else (u0 + (u1 - u0) * (i / nu), v0 + (v1 - v0) * t)
    for j in range(nv):
        for i in range(nu):
            a = b0 + j * (nu + 1) + i
            G.f.append((a, a + 1, a + nu + 2, a + nu + 1)); G.uv.append((idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))

def tintA(rng, yel=0.0):
    v = rng.uniform(0.34, 0.75); c = np.array([v * rng.uniform(0.55, 0.8), v * rng.uniform(0.85, 1.0), v * rng.uniform(0.4, 0.6)])
    return np.array([1.25, 1.0, 0.35]) * rng.uniform(0.6, 0.9) if rng.random() < yel else c
def tintB(rng, yel=0.0):
    v = rng.uniform(0.24, 0.62); c = np.array([v * rng.uniform(0.5, 0.8), v * rng.uniform(0.82, 1.0), v * rng.uniform(0.42, 0.7)])
    return np.array([1.2, 0.95, 0.4]) * rng.uniform(0.6, 0.9) if rng.random() < yel else c

def put_leaf(kind, rng, p, d, k, room, yel, box):
    x0, y0, x1, y1 = box
    if kind == 'A':
        ln = min(rng.uniform(0.032, 0.054), max(0.02, room * 1.3)); dd = rot2(d, math.radians(rng.uniform(30, 80)) * (1 if k % 2 else -1), rng.normal(0, 0.3))
        leaf(la, p + [0, 0, rng.normal(0, 0.008)], dd, UP + rng.normal(0, 0.5, 3) * np.array([1, 1, 0.3]), ln, ln * 0.52, R22[rng.integers(6)], tintA(rng, yel), fold=0.2, curl=rng.uniform(-0.1, 0.3), twist=rng.normal(0, 0.3))
    else:
        ln = min(rng.uniform(0.038, 0.06), max(0.022, room * 1.3)); dd = rot2(d, math.radians(rng.uniform(35, 85)) * (1 if k % 2 else -1), rng.normal(0, 0.3))
        tipp = p + dd / np.linalg.norm(dd) * ln * 1.22; m = ln * 0.55
        if tipp[0] < x0 + m or tipp[0] > x1 - m or tipp[1] < y0 + m or tipp[1] > y1 - m or p[1] < y0 + m or p[1] > y1 - m: return      # a lobed leaf must not cross into the next tile
        isy = rng.random() < yel
        # a short leaf stalk, then the lobed blade
        st = p + dd / np.linalg.norm(dd) * ln * 0.22; wood.tube(np.array([p, st]), [0.0007, 0.0006], np.array([0.09, 0.11, 0.035]), 3, rng)
        leaf(lb, st + [0, 0, rng.normal(0, 0.008)], dd, UP + rng.normal(0, 0.5, 3) * np.array([1, 1, 0.3]), ln, ln * 0.95, (R29Y[rng.integers(2)] if isy else R29[rng.integers(7)]),
             np.array([1.0, 1.0, 1.0]) * rng.uniform(0.7, 1.0) if isy else tintB(rng), sideways=True, fold=0.18, curl=rng.uniform(-0.1, 0.35), twist=rng.normal(0, 0.3), nu=2, nv=3)

def spray(col, row, seed, kind, dens=1.0, side_n=11, yel=0.0, gap=0.0075, bare_twigs=0.0):
    rng = np.random.default_rng(seed); w = h = TS; o = np.array([col * TS, (3 - row) * TS + TS / 2, 0.0])
    main = A.curve(o + [0.004, 0, 0], [1, rng.normal(0, 0.1), 0], w * 0.88, rng, 12, 0.3); main[:, 1] = np.clip(main[:, 1], o[1] - h * 0.16, o[1] + h * 0.16)
    box = (o[0], o[1] - h / 2, o[0] + w, o[1] + h / 2)
    wood.tube(main, np.linspace(0.0042, 0.0015, len(main)), BROWN, 5, rng); twigs = [(main, 0.2, False)]
    for k in range(side_n):
        t = 0.1 + 0.8 * (k + rng.uniform(-0.3, 0.3)) / side_n; i = int(t * (len(main) - 1)); d = main[min(i + 1, len(main) - 1)] - main[i - 1 if i else 0]; d /= np.linalg.norm(d)
        dd = rot2(d, math.radians(rng.uniform(35, 70)) * (1 if k % 2 else -1), rng.normal(0, 0.15))
        L = min(w * 0.42 * rng.uniform(0.5, 1.0), (h * 0.46 - abs(main[i][1] - o[1])) / max(abs(dd[1]), 0.3), (o[0] + w * 0.95 - main[i][0]) / max(dd[0], 0.3))
        if L < 0.04: continue
        pts = A.curve(main[i], dd, L, rng, 6, 0.3); bare = rng.random() < bare_twigs
        wood.tube(pts, np.linspace(0.0022, 0.001, len(pts)), GREY if bare else BROWN, 4, rng); twigs.append((pts, 0.1, bare))
        if L > 0.1 and rng.random() < 0.6:           # a third-order twiglet
            j = int(rng.uniform(0.3, 0.7) * (len(pts) - 2)); d2 = pts[j + 1] - pts[j]; d2 /= np.linalg.norm(d2); dd2 = rot2(d2, math.radians(rng.uniform(30, 55)) * rng.choice([-1, 1]), rng.normal(0, 0.1))
            L2 = L * rng.uniform(0.3, 0.5)
            if abs(pts[j][1] + dd2[1] * L2 - o[1]) < h * 0.45 and pts[j][0] + dd2[0] * L2 < o[0] + w * 0.95:
                p2 = A.curve(pts[j], dd2, L2, rng, 4, 0.25); wood.tube(p2, np.linspace(0.0014, 0.0008, len(p2)), GREY if bare else BROWN, 3, rng); twigs.append((p2, 0.1, bare))
    step = gap * (1.0 if kind == 'A' else 1.9)
    for pts, f0, bare in twigs:
        if bare: continue
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); s = f0 * cum[-1]; k = 0
        while s < cum[-1]:
            i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(pts) - 2)); p = pts[i] + (pts[i + 1] - pts[i]) * (s - cum[i]) / seg[i]; d = pts[i + 1] - pts[i]; d /= np.linalg.norm(d)
            room = h * 0.49 - abs(p[1] - o[1])
            if rng.random() < dens and p[0] < o[0] + w * 0.96: put_leaf(kind, rng, p, d, k, min(room, (o[0] + w * 0.99 - p[0]) * 1.2), yel, box)
            k += 1; s += step * rng.uniform(0.6, 1.5)

def twig_spray(col, row, seed, r0=0.0065):
    rng = np.random.default_rng(seed); w = h = TS; o = np.array([col * TS, (3 - row) * TS + TS / 2, 0.0])
    def grow(p, d, L, r, depth):
        pts = A.curve(p, d, L, rng, 8, 0.45); pts[:, 1] = np.clip(pts[:, 1], o[1] - h * 0.48, o[1] + h * 0.48); pts[:, 0] = np.clip(pts[:, 0], o[0] + 0.003, o[0] + w * 0.985)
        wood.tube(pts, np.linspace(r, r * 0.35, len(pts)), GREY * rng.uniform(0.8, 1.3), 5 if depth == 0 else 4, rng)
        if depth >= 3 or L < 0.05: return
        for k in range(int(rng.integers(3, 6)) if depth < 2 else 2):
            j = int(rng.uniform(0.2, 0.9) * (len(pts) - 2)); dd = pts[j + 1] - pts[j]; dd /= np.linalg.norm(dd)
            d2 = rot2(dd, math.radians(rng.uniform(25, 60)) * rng.choice([-1, 1]), rng.normal(0, 0.1)); L2 = L * rng.uniform(0.35, 0.6); end = pts[j] + d2 * L2
            if abs(end[1] - o[1]) > h * 0.47 or end[0] > o[0] + w * 0.97 or end[0] < o[0] + 0.01: continue
            grow(pts[j], d2, L2, r * 0.55, depth + 1)
    grow(o + [0.004, 0, 0], np.array([1, rng.normal(0, 0.08), 0]), w * 0.82, r0, 0)

for c in range(4): spray(c, 0, 200 + c, 'A', dens=(1.0, 1.0, 0.9, 0.85)[c], side_n=(11, 12, 10, 9)[c])
for c in range(4): spray(c, 1, 210 + c, 'B', dens=(1.0, 1.0, 0.9, 0.85)[c], side_n=(11, 12, 10, 9)[c])
spray(0, 2, 220, 'A', dens=0.55, side_n=9, bare_twigs=0.4); spray(1, 2, 221, 'B', dens=0.55, side_n=9, bare_twigs=0.4)
twig_spray(2, 2, 231); twig_spray(3, 2, 232, r0=0.008)
spray(0, 3, 240, 'A', dens=0.95, yel=0.14); spray(1, 3, 241, 'B', dens=0.95, yel=0.14)
spray(2, 3, 242, 'A', dens=0.8, side_n=5, gap=0.011); spray(3, 3, 243, 'B', dens=0.8, side_n=5, gap=0.011)
lao = la.obj('leafA'); lbo = lb.obj('leafB'); wo = wood.obj('wood')
def rebuild(mode):
    ma = A.leaf_mats(mode, 'leafA', L22 + 'Color.jpg', L22 + 'Opacity.jpg', L22 + 'NormalGL.jpg', rough=0.5)
    mb_ = A.leaf_mats(mode, 'leafB', L29 + 'Color.jpg', L29 + 'Opacity.jpg', L29 + 'NormalGL.jpg', rough=0.55)
    mw = A.pass_material('wood', mode, A.attr_col(), rough=0.85, sss=(0.01, 0.008, 0.004))
    for o, m in ((lao, ma), (lbo, mb_), (wo, mw)): o.data.materials.clear(); o.data.materials.append(m)
print('verts', len(la.v), len(lb.v), len(wood.v), flush=True)
A.render_atlas(scene, 2.0, 2.0, 2048, 2048, os.path.join(WORK, 'shrub_atlas'), rebuild, samples=12)
