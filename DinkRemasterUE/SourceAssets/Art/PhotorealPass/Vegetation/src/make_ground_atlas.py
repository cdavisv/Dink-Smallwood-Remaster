"""Shared ground-cover atlas T_Veg_GroundCover (1024^2): grass blade strips (procedural), seed head (ambientCG Foliage003),
dock leaf (LeafSet022), plantain-type leaf (LeafSet020), nettle leaf (procedural), daisy / buttercup heads, mushroom caps, stem, gills.
Run with python3 -I."""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from texlib import *
OUT = os.path.join(HERE, '..', 'Export', 'Textures'); TP = os.path.join(HERE, '..', '..', 'ThirdParty', 'ambientcg'); WK = os.path.join(HERE, '..', 'work')
S = 1024
bc = np.zeros((S, S, 3)); al = np.zeros((S, S)); nm = np.zeros((S, S, 3)); nm[..., 2] = 1; ro = np.full((S, S), 0.6); ao = np.ones((S, S)); ss = np.zeros((S, S, 3))
def s2l(a): return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
def put(x, y, c, a, n=None, r=0.55, sss_mul=(1.6, 1.5, 0.5), aoo=None):
    h, w = a.shape
    bc[y:y + h, x:x + w] = c; al[y:y + h, x:x + w] = a
    if n is not None: nm[y:y + h, x:x + w] = n
    ro[y:y + h, x:x + w] = r; ss[y:y + h, x:x + w] = np.clip(c * np.array(sss_mul), 0, 1)
    if aoo is not None: ao[y:y + h, x:x + w] = aoo

def comps(op, thr=0.5, minsize=40):
    """bounding boxes of blobs via column runs then row runs."""
    m = op > thr; out = []
    cols = m.any(0); xs = np.flatnonzero(np.diff(np.concatenate([[0], cols.astype(int), [0]])))
    for x0, x1 in zip(xs[0::2], xs[1::2]):
        if x1 - x0 < minsize: continue
        rows = m[:, x0:x1].any(1); ys = np.flatnonzero(np.diff(np.concatenate([[0], rows.astype(int), [0]])))
        for y0, y1 in zip(ys[0::2], ys[1::2]):
            if y1 - y0 >= minsize: out.append((x0, y0, x1, y1))
    return out

def scan_leaf(aid, pick, w, h, tint=(1, 1, 1), crop=None, gain=1.0):
    ld = lambda m: np.asarray(Image.open(f'{TP}/{aid}/{aid}_2K-JPG_{m}.jpg').convert('RGB')).astype(float) / 255
    col, op, nr = ld('Color'), ld('Opacity')[..., 0], ld('NormalGL')
    bbs = comps(op); bbs.sort(key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))
    print(aid, 'blobs', len(bbs), bbs[:8])
    x0, y0, x1, y1 = bbs[pick]
    if crop: y1 = y0 + int((y1 - y0) * crop)
    pad = 6; x0 = max(0, x0 - pad); y0 = max(0, y0 - pad); x1 += pad; y1 += pad
    def rz(a, mode='RGB'):
        im = Image.fromarray(lin8(a[y0:y1, x0:x1]), mode); return np.asarray(im.resize((w, h), Image.LANCZOS)).astype(float) / 255
    c = s2l(rz(col)) * np.array(tint) * gain; a = rz(op, 'L'); n = rz(nr) * 2 - 1
    c = dilate_rgb(c, (a > 0.5).astype(float), 10)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return c, a, n

# ---- grass blade strips (each 64 x 1024, v up = blade tip at row 0)
for i, (base, mid, tip, dry) in enumerate([((0.30, 0.33, 0.12), (0.055, 0.13, 0.022), (0.10, 0.19, 0.03), 0.0),
                                           ((0.33, 0.36, 0.13), (0.075, 0.16, 0.028), (0.16, 0.24, 0.04), 0.0),
                                           ((0.34, 0.33, 0.14), (0.09, 0.15, 0.03), (0.42, 0.36, 0.12), 0.35),
                                           ((0.40, 0.33, 0.17), (0.46, 0.38, 0.17), (0.52, 0.44, 0.22), 1.0)]):
    h, w = 1024, 64
    t = (1 - np.arange(h) / (h - 1))[:, None] * np.ones((1, w)); x = (np.arange(w) / (w - 1) - 0.5)[None, :] * 2 * np.ones((h, 1))
    n1 = fbm(h, w, 40 + i, 1.4, 1, 12); n2 = fbm(h, w, 50 + i, 2.2, 1, 3)
    c = lerp(np.array(base), np.array(mid), sstep(0.0, 0.16, t)); c = lerp(c, np.array(tip), sstep(0.55 - 0.2 * dry, 1.0, t + 0.25 * (n2 - 0.5)))
    veins = 0.5 + 0.5 * np.cos(x * np.pi * 7)
    c = c * (0.82 + 0.25 * n1 + 0.1 * veins)[..., None]
    c = lerp(c, np.array([0.30, 0.34, 0.12]) if dry < 0.5 else np.array([0.55, 0.47, 0.25]), np.exp(-(x / 0.12) ** 2) * 0.55)      # pale midrib
    spots = sstep(0.72, 0.8, fbm(h, w, 60 + i, 1.0)) * (0.3 + 0.7 * dry + 0.3 * t)
    c = lerp(c, np.array([0.20, 0.13, 0.05]), spots * 0.6)
    hm = -np.abs(x) * 0.6 + 0.2 * veins + 0.2 * n1
    put(i * 64, 0, c, np.ones((h, w)), normal_from_height(hm, 6.0, wrap=False), r=0.42 + 0.3 * dry + 0.1 * n1, sss_mul=(1.8, 1.6, 0.5) if dry < 0.5 else (0.8, 0.7, 0.3))

# ---- scans
c, a, n = scan_leaf('Foliage003', 1, 256, 512, crop=0.62, gain=1.0); put(256, 0, c, a, n, r=0.7, sss_mul=(0.9, 0.9, 0.4))
c, a, n = scan_leaf('LeafSet022', 2, 256, 512, tint=(0.40, 0.58, 0.36)); put(512, 0, c, a, n, r=0.45)
c, a, n = scan_leaf('LeafSet020', 1, 256, 512, tint=(0.36, 0.56, 0.30)); put(768, 0, c, a, n, r=0.45)
# ---- nettle leaf (procedural, from make_leaftex)
im = np.asarray(Image.open(f'{WK}/nettle_leaf_c.png').convert('RGBA')).astype(float) / 255
put(256, 512, s2l(im[..., :3]), im[..., 3], np.asarray(Image.open(f'{WK}/nettle_leaf_n.png').convert('RGB')).astype(float) / 255 * 2 - 1, r=0.55)

# ---- flower heads, top view 256x256
def flower(seed, petals, pc0, pc1, cc, plen=0.92, pw=0.55, crad=0.24, notch=0.0):
    h = w = 256; r_ = rng(seed)
    y, x = np.mgrid[0:h, 0:w]; X = (x - 127.5) / 127.5; Y = (y - 127.5) / 127.5
    rr = np.sqrt(X * X + Y * Y); th = np.arctan2(Y, X)
    alpha = np.zeros((h, w)); hm = np.zeros((h, w)); col = np.zeros((h, w, 3)); n1 = fbm(h, w, seed, 2.0)
    for k in range(petals):
        a0 = 2 * np.pi * k / petals + r_.normal(0, 0.06); L = plen * r_.uniform(0.82, 1.0); wd = pw * 2 * np.pi / petals * r_.uniform(0.85, 1.1)
        dth = (th - a0 + np.pi) % (2 * np.pi) - np.pi
        lx = rr * np.cos(dth); ly = rr * np.sin(dth)                     # petal local coords
        t = np.clip(lx / L, 0, 1)
        half = wd * 0.5 * L * (np.sin(np.pi * t ** 0.7) ** 0.6) * (1 - notch * sstep(0.85, 1.0, t) * (np.abs(ly) < 0.02))
        inside = sstep(-0.01, 0.012, half - np.abs(ly)) * (lx > 0) * (lx < L)
        shade = r_.uniform(0.85, 1.0)
        pc = lerp(np.array(pc0), np.array(pc1), np.clip(t + 0.2 * (n1 - 0.5), 0, 1)[..., None] if False else np.clip(t, 0, 1)) * shade
        streak = 0.9 + 0.1 * np.cos(ly / (half + 1e-3) * 6)
        newer = inside > alpha
        col = np.where(newer[..., None], pc * streak[..., None], col); hm = np.where(newer, 0.3 + 0.2 * np.cos(ly / (half + 1e-3) * 1.5) - 0.15 * t + 0.1 * (k % 2), hm)
        alpha = np.maximum(alpha, inside)
    cen = sstep(crad, crad - 0.03, rr)
    dots = 0.5 + 0.5 * np.cos(rr * 150) * np.cos(th * 21 + rr * 40)
    ccol = np.array(cc) * (0.75 + 0.35 * dots)[..., None] * (1 - 0.35 * sstep(0.0, crad, rr))[..., None]
    col = lerp(col, ccol, cen); alpha = np.maximum(alpha, cen); hm = np.where(cen > 0.5, 0.8 + 0.3 * np.sqrt(np.clip(1 - (rr / crad) ** 2, 0, 1)) + 0.05 * dots, hm)
    col = dilate_rgb(col, (alpha > 0.5).astype(float), 10)
    return col, alpha, normal_from_height(blur(hm, 1.0), 10.0, wrap=False)
c, a, n = flower(3, 21, (0.80, 0.80, 0.74), (0.86, 0.86, 0.84), (0.75, 0.50, 0.03)); put(512, 512, c, a, n, r=0.5, sss_mul=(1.0, 1.0, 0.9))
c, a, n = flower(8, 5, (0.80, 0.56, 0.02), (0.85, 0.66, 0.03), (0.55, 0.50, 0.04), plen=0.9, pw=1.25, crad=0.2); put(768, 512, c, a, n, r=0.3, sss_mul=(1.0, 0.9, 0.3))

# ---- mushroom strips 128 x 256: u = angle (tiles), v: row 0 = cap centre / stem top
def strip(seed, fn):
    h, w = 256, 128; t = (np.arange(h) / (h - 1))[:, None] * np.ones((1, w)); u = (np.arange(w) / w)[None, :] * np.ones((h, 1))
    return fn(t, u, fbm(h, w, seed, 1.6), fbm(h, w, seed + 1, 0.6), h, w, seed)
def cap_brown(t, u, n1, n2, h, w, seed):
    c = lerp(np.array([0.30, 0.12, 0.04]), np.array([0.16, 0.055, 0.025]), sstep(0.2, 0.9, t + 0.3 * (n1 - 0.5)))
    c = lerp(c, np.array([0.42, 0.25, 0.10]), sstep(0.85, 1.0, t) * 0.7) * (0.8 + 0.4 * n2)[..., None]
    f1, f2, _, _ = worley(h, w, 5, 10, seed, 0.9); sc = sstep(0.0, 0.05, f2 - f1)
    c = c * (0.75 + 0.25 * sc)[..., None]
    return c, normal_from_height(sc * 0.4 + n2 * 0.3, 4.0), 0.35 + 0.2 * n1
def cap_agaric(t, u, n1, n2, h, w, seed):
    c = lerp(np.array([0.50, 0.035, 0.012]), np.array([0.62, 0.10, 0.015]), sstep(0.5, 1.0, t + 0.3 * (n1 - 0.5))) * (0.85 + 0.3 * n2)[..., None]
    f1, f2, _, cr = worley(h, w, 6, 9, seed, 0.95); wart = sstep(0.34, 0.24, f1 + 0.25 * cr) * (cr > 0.25)
    c = lerp(c, np.array([0.78, 0.74, 0.62]) * (0.8 + 0.2 * n2)[..., None], wart)
    return c, normal_from_height(wart * 1.0 + n2 * 0.15, 5.0), lerp(0.22 + 0.1 * n1, 0.8, wart)
def stem(t, u, n1, n2, h, w, seed):
    fib = fbm(h, w, seed + 5, 1.2, 1, 14)
    c = lerp(np.array([0.72, 0.68, 0.56]), np.array([0.50, 0.42, 0.30]), sstep(0.55, 1.0, t + 0.3 * (n1 - 0.5))) * (0.75 + 0.35 * fib)[..., None]
    return c, normal_from_height(fib, 5.0), 0.7 + 0.2 * n1
def gills(t, u, n1, n2, h, w, seed):
    g = 0.5 + 0.5 * np.cos(u * 2 * np.pi * 32 + 2 * n1)
    c = lerp(np.array([0.30, 0.25, 0.17]), np.array([0.70, 0.64, 0.50]), g) * (0.8 + 0.3 * n2)[..., None]
    return c, normal_from_height(g, 6.0), 0.8 * np.ones((h, w))
for i, fn in enumerate((cap_brown, cap_agaric, stem, gills)):
    c, n, r = strip(90 + 7 * i, fn); put(512 + i * 128, 768, c, np.ones(c.shape[:2]), n, r=r, sss_mul=(0.3, 0.2, 0.1))

solid = (al > 0.5).astype(float)
bcd = dilate_rgb(bc, solid, 12); nmd = dilate_rgb(nm, solid, 8); nmd /= np.linalg.norm(nmd, axis=-1, keepdims=True); ssd = dilate_rgb(ss, solid, 12)
save_rgb(f'{OUT}/T_Veg_GroundCover_BC.png', srgb8(np.clip(bcd, 0.01, 0.9)), lin8(np.clip(al * 1.15, 0, 1)))
save_normal(f'{OUT}/T_Veg_GroundCover_N.png', nmd); save_orm(f'{OUT}/T_Veg_GroundCover_ORM.png', ao, np.clip(ro, 0.2, 1)); save_rgb(f'{OUT}/T_Veg_GroundCover_SSS.png', srgb8(ssd))
a = Image.open(f'{OUT}/T_Veg_GroundCover_BC.png'); bg = Image.new('RGBA', a.size, (110, 120, 140, 255)); bg.alpha_composite(a); bg.convert('RGB').save(f'{WK}/ground_view.png')
print('ok')
