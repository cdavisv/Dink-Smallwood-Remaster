"""Meadow grass atlas (work/meadow_atlas_*.png -> T_Veg_MeadowGrass): tiles of many narrow modelled blades (2-6 mm) standing side by side
(no fan), with drooping tips, kinked / broken blades, seed-head stems, dead straw at the base; grazed-turf tiles; dry tiles; lying thatch.
blender -b -t 4 --python atlas_meadow.py ; then python3 -I compose_meadow.py"""
import bpy, sys, os, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bl_atlas as A
from meadow_layout import TILES, WORLD
WORK = os.path.join(HERE, '..', 'work')
A.reset(); scene = bpy.context.scene
green = A.Geo(); dry = A.Geo()        # two objects: different roughness / translucency
def sm(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
# linear albedo palette
G_ROOT = np.array([0.058, 0.085, 0.028]); G_MID = np.array([0.072, 0.158, 0.036]); G_TIP = np.array([0.125, 0.230, 0.058])
S_ROOT = np.array([0.150, 0.110, 0.050]); S_MID = np.array([0.330, 0.255, 0.105]); S_TIP = np.array([0.450, 0.370, 0.170])
BROWN = np.array([0.140, 0.085, 0.035])

def blade(G, p0, L, w, th0, droop, rng, cols, rect, kink=None, tw=(0.0, 0.0), crease=0.3, zlean=0.0, nseg=12, tipbrown=0.0, taper=3.0, check=True):
    """one blade as a creased strip in the XY plane. th0: lean from vertical (rad, + = right). droop: extra turn over the length.
    kink=(t, angle): a break. Returns False (nothing added) if it leaves its tile."""
    x0, y0, tw_, th_ = rect; root, mid, tip = cols
    P = [np.array(p0, float)]; TH = [th0]; wa = rng.normal(0, 0.13); wf = rng.uniform(4.0, 9.0); wp = rng.uniform(0, 6.28)
    for j in range(1, nseg + 1):
        t = j / nseg; th = th0 + droop * t ** 2.2 + wa * math.sin(wf * t + wp) * min(1.0, t * 3)
        if kink and t > kink[0]: th += kink[1] * min(1.0, (t - kink[0]) * nseg * 0.7)
        P.append(P[-1] + np.array([math.sin(th), math.cos(th), zlean]) * L / nseg); TH.append(th)
    P = np.array(P)
    if check and (P[:, 0].min() < x0 + 0.006 or P[:, 0].max() > x0 + tw_ - 0.006 or P[:, 1].max() > y0 + th_ - 0.006 or P[:, 1].min() < y0 + 0.002): return False
    b0 = len(G.v); var = rng.uniform(0.8, 1.2); hue = rng.normal(0, 0.06)
    for j in range(nseg + 1):
        t = j / nseg; th = TH[j]; d = np.array([math.sin(th), math.cos(th), 0]); side = np.array([math.cos(th), -math.sin(th), 0]); up = np.array([0, 0, 1.0])
        a = tw[0] + tw[1] * t; s = side * math.cos(a) + up * math.sin(a); nb = np.cross(s, d); nb = nb if nb[2] > 0 else -nb
        wj = w * min(1.0, 0.55 + t * 3.0) * max(0.0, 1 - t ** taper) ** 0.75
        wj = max(wj, 0.0004)
        c = lerp(root, mid, sm(0.0, 0.3, t)); c = lerp(c, tip, sm(0.4, 1.0, t)) * var * np.array([1 + hue, 1, 1 - hue])
        if tipbrown > 0: c = lerp(c, S_MID * var, sm(1 - tipbrown, 1 - tipbrown * 0.4, t))
        G.v += [P[j] - s * wj / 2, P[j] - nb * crease * wj, P[j] + s * wj / 2]; G.c += [c * 0.92, c * 1.12, c * 0.92]
    for j in range(nseg):
        for k in range(2):
            a0 = b0 + j * 3 + k; G.f.append((a0, a0 + 1, a0 + 4, a0 + 3)); G.uv.append(((0, 0),) * 4)
    return True

def try_blade(G, rng, n=8, **kw):
    for i in range(n):
        if blade(G, rng=rng, **kw): return True
        kw['droop'] *= 0.6; kw['th0'] *= 0.6; kw['L'] *= 0.93
        if kw.get('kink'): kw['kink'] = (kw['kink'][0], kw['kink'][1] * 0.7)
    return False

def seed_stem(rect, x, H, rng, kind):
    """flowering stem rising above the leaves with a panicle or a dense spike"""
    x0, y0, tw_, th_ = rect; H = min(H, th_ - 0.012); th0 = rng.normal(0, 0.05); dr = rng.normal(0, 0.18)
    z = rng.uniform(-0.01, 0.01); cols = (lerp(G_MID, S_MID, 0.35), lerp(G_MID, S_MID, 0.6), S_MID * 0.9)
    if not blade(green, (x, y0 + 0.003, z), H, 0.0022, th0, dr, rng, cols, rect, crease=0.0, nseg=14, taper=8.0): return
    # walk the same path again to place the head on its last part
    nseg = 60; P = [np.array([x, y0 + 0.003, z])]; TH = []
    for j in range(1, nseg + 1):
        t = j / nseg; th = th0 + dr * t ** 2.2; P.append(P[-1] + np.array([math.sin(th), math.cos(th), 0]) * H / nseg); TH.append(th)
    hl = rng.uniform(0.06, 0.10) if kind == 'panicle' else rng.uniform(0.035, 0.06); n0 = int(nseg * (1 - hl / H))
    gr = rng.random() < 0.45
    hc = (lerp(G_MID, S_MID, 0.45), lerp(G_TIP, S_MID, 0.5), lerp(G_TIP, S_TIP, 0.6)) if gr else (lerp(S_MID, BROWN, rng.uniform(0.2, 0.6)), lerp(S_MID, BROWN, 0.3), S_TIP * 0.8)
    for j in range(n0, nseg):
        tt = (j - n0) / max(1, nseg - n0); p = P[j]; th = TH[min(j, len(TH) - 1)]
        if kind == 'panicle':
            if j % 2: continue
            for sd in (-1, 1):
                if rng.random() < 0.2: continue
                bl = (0.010 + 0.036 * (1 - tt) ** 0.8) * rng.uniform(0.6, 1.0); ba = th + sd * rng.uniform(0.45, 0.95) * (1 - 0.4 * tt)
                blade(dry, p, bl, 0.0009, ba, sd * rng.uniform(0.1, 0.6), rng, hc, rect, crease=0, nseg=4, taper=9.0, check=False)
                for q in range(int(2 + bl / 0.006)):
                    f = rng.uniform(0.3, 1.0); pp = p + np.array([math.sin(ba), math.cos(ba), 0]) * bl * f
                    blade(dry, pp + [0, 0, 0.002], rng.uniform(0.0045, 0.0075), rng.uniform(0.0016, 0.0024), ba + rng.normal(0, 0.5), 0, rng, hc, rect, crease=0.2, nseg=3, taper=2.0, check=False)
        else:
            for q in range(3):
                ba = th + rng.normal(0, 0.55); r = 0.0035 * math.sin(math.pi * min(0.999, max(0.05, tt))) ** 0.5
                pp = p + np.array([math.cos(th), -math.sin(th), 0]) * rng.uniform(-r, r)
                blade(dry, pp + [0, 0, 0.002], rng.uniform(0.005, 0.009), rng.uniform(0.0016, 0.0024), ba, 0, rng, hc, rect, crease=0.2, nseg=3, taper=2.0, check=False)

def tall_tile(name, seed, n, hrange, dryfrac=0.0, stems=0, straw=14, broken=0.08, droop=0.55, wrange=(0.002, 0.006), short=0.25):
    rng = np.random.default_rng(seed); rect = TILES[name]; x0, y0, tw_, th_ = rect
    xs = (np.arange(n) + rng.uniform(0.1, 0.9, n)) / n; rng.shuffle(xs)          # roots spread along the whole tile width: no fan
    for i in range(n):
        x = x0 + 0.012 + xs[i] * (tw_ - 0.024); isdry = rng.random() < dryfrac
        L = th_ * rng.uniform(*hrange) * (rng.uniform(0.35, 0.7) if rng.random() < short else 1.0)
        w = rng.uniform(*wrange) * (0.75 + 0.5 * L / (th_ * hrange[1])) * (1.45 if rng.random() < 0.2 else 1.0)        # one blade in five is a broad one
        cols = (S_ROOT, S_MID, S_TIP) if isdry else (G_ROOT, G_MID * rng.uniform(0.85, 1.2), G_TIP * rng.uniform(0.8, 1.25))
        kink = (rng.uniform(0.35, 0.75), rng.choice([-1, 1]) * rng.uniform(1.3, 2.6)) if rng.random() < broken * (2.0 if isdry else 1.0) else None
        dr = rng.choice([-1, 1]) * abs(rng.normal(droop * 0.6, droop * 0.7)) * (0.4 + 0.9 * L / (th_ * hrange[1]))
        try_blade(dry if isdry else green, rng, p0=(x, y0 + 0.003, rng.uniform(-0.02, 0.02)), L=L, w=w, th0=rng.normal(0, 0.2), droop=dr, cols=cols, rect=rect, kink=kink,
                  tw=(rng.normal(0, 0.5), rng.normal(0, 0.9)), crease=rng.uniform(0.15, 0.45), zlean=rng.normal(0, 0.04), nseg=14,
                  tipbrown=(rng.uniform(0.08, 0.3) if rng.random() < 0.3 and not isdry else 0.0), taper=rng.uniform(2.2, 4.0))
    for i in range(straw):             # dead straw low down, crossing at all angles
        x = x0 + 0.02 + rng.random() * (tw_ - 0.04); L = rng.uniform(0.05, 0.2)
        kink = (rng.uniform(0.3, 0.7), rng.choice([-1, 1]) * rng.uniform(0.8, 2.2)) if rng.random() < 0.4 else None
        try_blade(dry, rng, p0=(x, y0 + 0.003, rng.uniform(-0.025, 0.025)), L=L, w=rng.uniform(0.0018, 0.0035), th0=rng.normal(0, 0.7), droop=rng.normal(0, 0.8), cols=(S_ROOT, S_MID * rng.uniform(0.7, 1.1), S_TIP * rng.uniform(0.7, 1.0)),
                  rect=rect, kink=kink, tw=(rng.normal(0, 0.6), rng.normal(0, 1.0)), crease=0.15, nseg=8, taper=5.0)
    for i in range(stems):
        seed_stem(rect, x0 + tw_ * (0.15 + 0.7 * (i + rng.uniform(0.2, 0.8)) / stems), th_ * rng.uniform(0.86, 0.985), rng, 'panicle' if rng.random() < 0.6 else 'spike')

def short_tile(name, seed, n, dryfrac=0.05):
    rng = np.random.default_rng(seed); rect = TILES[name]; x0, y0, tw_, th_ = rect
    xs = (np.arange(n) + rng.uniform(0.1, 0.9, n)) / n
    for i in range(n):
        x = x0 + 0.01 + xs[i] * (tw_ - 0.02); isdry = rng.random() < dryfrac; L = rng.uniform(0.045, 0.125) * (1.25 if rng.random() < 0.08 else 1.0)
        cols = (S_ROOT, S_MID, S_TIP) if isdry else (G_ROOT * 1.1, G_MID * rng.uniform(0.85, 1.2), G_TIP * rng.uniform(0.8, 1.2))
        # grazed: many blades end in a bitten-off blunt tip (low taper exponent = blunt)
        try_blade(dry if isdry else green, rng, p0=(x, y0 + 0.003, rng.uniform(-0.015, 0.015)), L=L, w=rng.uniform(0.002, 0.0042), th0=rng.normal(0, 0.38), droop=rng.normal(0, 0.7), cols=cols, rect=rect,
                  tw=(rng.normal(0, 0.5), rng.normal(0, 0.8)), crease=rng.uniform(0.15, 0.4), zlean=rng.normal(0, 0.05), nseg=7,
                  tipbrown=(0.25 if rng.random() < 0.25 and not isdry else 0.0), taper=(rng.uniform(6, 14) if rng.random() < 0.45 else rng.uniform(2.2, 3.5)))

def thatch_tile(name, seed, n):
    rng = np.random.default_rng(seed); rect = TILES[name]; x0, y0, tw_, th_ = rect
    for i in range(n):
        p = (x0 + rng.uniform(0.03, tw_ - 0.03), y0 + rng.uniform(0.02, th_ - 0.02), rng.uniform(-0.01, 0.01)); isg = rng.random() < 0.18
        kink = (rng.uniform(0.3, 0.7), rng.choice([-1, 1]) * rng.uniform(0.6, 2.0)) if rng.random() < 0.35 else None
        cols = (G_ROOT, G_MID * 0.8, G_MID) if isg else (S_ROOT * rng.uniform(0.6, 1.2), S_MID * rng.uniform(0.55, 1.1), S_TIP * rng.uniform(0.6, 1.0))
        try_blade(green if isg else dry, rng, p0=p, L=rng.uniform(0.05, 0.19), w=rng.uniform(0.002, 0.0045), th0=rng.uniform(-math.pi, math.pi), droop=rng.normal(0, 0.9), cols=cols, rect=rect, kink=kink,
                  tw=(rng.normal(0, 0.6), rng.normal(0, 1.0)), crease=0.2, nseg=8, taper=4.0)

tall_tile('T0', 1, 46, (0.62, 0.90), dryfrac=0.06, straw=16)
tall_tile('T1', 2, 44, (0.55, 0.84), dryfrac=0.08, straw=18, droop=0.8)
tall_tile('T2', 3, 40, (0.55, 0.82), dryfrac=0.06, stems=2, straw=14)
tall_tile('T3', 4, 42, (0.58, 0.86), dryfrac=0.10, stems=1, straw=16, broken=0.2)
tall_tile('T4', 5, 20, (0.60, 0.92), dryfrac=0.10, stems=2, straw=6, short=0.1)
tall_tile('T5', 6, 50, (0.35, 0.62), dryfrac=0.15, straw=24, droop=0.9, broken=0.15)
tall_tile('D0', 7, 44, (0.50, 0.86), dryfrac=0.86, stems=2, straw=20, broken=0.07, droop=0.8)
tall_tile('D1', 8, 42, (0.45, 0.80), dryfrac=0.93, stems=1, straw=22, broken=0.08, droop=1.0)
for i, nm in enumerate(('S0', 'S1', 'S2', 'S3')): short_tile(nm, 20 + i, (82, 74, 90, 66)[i], dryfrac=(0.04, 0.08, 0.03, 0.14)[i])
short_tile('SD0', 30, 76, dryfrac=0.85); short_tile('SD1', 31, 68, dryfrac=0.92)
thatch_tile('TH0', 40, 120); thatch_tile('TH1', 41, 95)
go = green.obj('green'); do = dry.obj('dry')
def mulcol(mul):
    def f(N, L):
        a = N.new('ShaderNodeAttribute'); a.attribute_name = 'Col'; m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'; m.inputs[0].default_value = 1
        L.new(a.outputs['Color'], m.inputs[6]); m.inputs[7].default_value = (*mul, 1); return m.outputs[2]
    return f
def rebuild(mode):
    mg = A.pass_material('green', mode, A.attr_col(), rough=0.42, sss=mulcol((1.7, 1.6, 0.6)), height_range=0.03)
    md = A.pass_material('dry', mode, A.attr_col(), rough=0.72, sss=mulcol((0.7, 0.6, 0.3)), height_range=0.03)
    for o, m in ((go, mg), (do, md)): o.data.materials.clear(); o.data.materials.append(m)
print('verts', len(green.v), len(dry.v), flush=True)
A.render_atlas(scene, WORLD, WORLD, 2048, 2048, os.path.join(WORK, 'meadow_atlas'), rebuild, samples=16)
