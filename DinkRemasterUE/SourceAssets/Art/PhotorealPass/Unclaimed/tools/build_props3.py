"""Stone and machine props of the unclaimed families: save machine (449), snake pillar (82), demon idol (80/24), freestanding
arch (80/25), golden duck statue (159/8), carved "Dink Smallwood" rock (159/4), snake carving (81), stone fountain (66/23-24),
teleport machine (84) and the cave hole (89/10).

    tools/bl.sh build_props3.py <name,name|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
import build_props as P
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_props3.py'


def stone(seed, tint=(0.80, 0.80, 0.82), value=0.85, sat=0.4, moss=0.35, lichen=0.35, scan='rock_face_03', scale=2.0, dirt_z=0.15):
    return P.rock_mat('stone%d' % int(seed), scan, tint=tint, value=value, sat=sat, moss=moss, lichen=lichen, dirt_z=dirt_z, scale=scale, seed=float(seed))


def chisel(o, seed=0, amp=0.003):
    """dense source only: tooling and weathering on cut stone"""
    L.displace_np(o, lambda Q: amp * fbm(Q, seed, 9, 3) - amp * 1.2 * (1 - np.abs(fbm(Q, seed + 2, 16, 3))) ** 4 + amp * 0.3 * fbm(Q, seed + 4, 70, 2)); return o


def rot_z(o, ang):
    return L.xform(o, Matrix.Rotation(ang, 4, 'Z'))


# ---------------------------------------------------------------------------------------------- save machine
def save_machine(hi, c):
    """a round stone hearth of a machine, 2.7 m across: stepped ring, sunk bowl with a boss, four horn scrolls, eight timber spokes, an iron grating round the foot"""
    seg = 96 if hi else 28; parts = []
    base = L.lathe('ring', [(0, 0.12), (0.16, 0.2), (0.22, 0.1), (0.5, 0.16), (0.62, 0.42), (0.74, 0.5), (0.92, 0.5), (0.98, 0.42), (1.02, 0.2), (1.12, 0.16), (1.15, 0.0), (0, 0.0)][::-1] if False else
                   [(0, 0.0), (1.15, 0.0), (1.12, 0.16), (1.02, 0.2), (0.98, 0.42), (0.92, 0.5), (0.74, 0.5), (0.62, 0.42), (0.5, 0.16), (0.22, 0.1), (0.16, 0.2), (0, 0.24)], seg=seg, c=c, cap0=False, cap1=False)
    if hi:
        L.subsurf(base, 2); chisel(base, 3, 0.002)
        Pq = L.co(base); r = np.hypot(Pq[:, 0], Pq[:, 1]); a = np.arctan2(Pq[:, 1], Pq[:, 0]); joint = np.exp(-(((a * 8 / np.pi) % 1.0 - 0.5) / 0.03) ** 2) * smoothstep(0.6, 0.75, r)        # sixteen ring stones
        nrm = L.vnormals(base); L.set_co(base, Pq - nrm * (joint * 0.006)[:, None]); base.data.materials.append(stone(21, tint=(0.62, 0.60, 0.56), value=0.7, moss=0.3))
    parts.append(base)
    for k in range(4):                                         # horn scrolls curling over the rim
        a = math.pi / 4 + k * math.pi / 2; rows = []
        for i in range(9):
            t = i / 8; th = t * 4.4; rr = 0.84 + 0.27 * math.cos(th) * (1 - 0.35 * t); zz = 0.56 + 0.32 * math.sin(th) * (1 - 0.3 * t) + 0.12 * t; rad = 0.12 * (1 - 0.72 * t) + 0.014
            rows.append((rr, 0.0, zz, rad, rad * 0.9, 2.2))
        h = L.sweep('scroll%d' % k, rows, nu=(14 if hi else 6), nv=(60 if hi else 12), c=c, up=(0, 1, 0), cap=0.4); rot_z(h, a)
        if hi:
            chisel(h, 30 + k, 0.002); h.data.materials.append(stone(22, tint=(0.60, 0.58, 0.54), value=0.7, moss=0.2))
        parts.append(h)
    wm = T.wood_mat('oak', axis=0, light=(0.20, 0.11, 0.05), dark=(0.07, 0.035, 0.015)) if hi else None
    for k in range(8):
        b = L.box('spoke%d' % k, (0.98, -0.065, 0.05), (1.56, 0.065, 0.17), c, hi, bevel=0.008, warp=0.003, seed=k)
        if hi:                                                  # the shader grain runs along X: paint before turning, so bake it per spoke through object space is not possible; use radial-safe isotropic settings
            b.data.materials.append(wm)
        rot_z(b, k * math.pi / 4 + math.pi / 8); parts.append(b)
    g = L.lathe('grating', [(1.14, 0.0), (1.48, 0.0), (1.48, 0.03), (1.14, 0.03), (1.14, 0.0)], seg=seg, c=c, cap0=False, cap1=False); L.clean_mesh(g); L.fix_normals(g)
    if hi:
        L.subsurf(g, 2) if False else None
        t = NT('grate'); sp = t.sep(t.obj); rr = t.vmath('LENGTH', t.comb(sp[0], sp[1], 0.0)); bars = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', t.math('MULTIPLY', rr, 22.0)), 0.5)), [(0.2, 1.0), (0.3, 0.0)])
        n = t.noise(60, 4, 0.6); rust = t.ramp(t.noise(14, 4, 0.7), [(0.45, 0.0), (0.65, 1.0)]); col = t.mix(bars, (0.012, 0.011, 0.01), t.mix(n, (0.03, 0.028, 0.026), (0.07, 0.065, 0.06))); col = t.mix(t.math('MULTIPLY', rust, 0.6), col, (0.12, 0.05, 0.02))
        t.set(base=col, rough=t.mixf(rust, 0.5, 0.85), metal=t.mixf(rust, t.mixf(bars, 0.2, 0.8), 0.1), normal=t.bump(bars, 0.9, 0.006)); g.data.materials.append(t.mat)
    parts.append(g)
    return parts


# ---------------------------------------------------------------------------------------------- snake pillar, snake carving
def snake(name, pts, r0, r1, c, hi, head=1.6):
    """serpent along pts: tapering body, a flattened wedge head at the end"""
    P_ = np.array(pts, float); n = len(P_); rows = []
    for i, p in enumerate(P_):
        t = i / (n - 1); r = r0 * (0.35 + 0.65 * min(1, t * 6)) if t < 0.2 else r0 + (r1 - r0) * 0; r = r0 * min(1.0, 0.3 + t * 5) * (1 - 0.0 * t)
        if t > 0.9:
            k = (t - 0.9) / 0.1; r = r0 * (1 + (head - 1) * math.sin(math.pi * min(1, k * 1.15)) ** 0.8) * (1 - 0.55 * k ** 3)
        rows.append((p[0], p[1], p[2], r * (1.25 if t > 0.92 else 1.0), r * (0.75 if t > 0.92 else 1.0), 2.2))
    o = L.sweep(name, rows, nu=(16 if hi else 7), nv=(n * 6 if hi else max(8, n)), c=c, up=(0, 0, 1), cap=0.35)
    return o


def snake_mat(col=((0.03, 0.09, 0.02), (0.08, 0.20, 0.04), (0.20, 0.34, 0.08)), stone_like=False):
    t = NT('snake'); cell = t.voronoi(260, feature='DISTANCE_TO_EDGE'); cv = t.sep(t.voronoi(260, out='Color')); n = t.noise(18, 5, 0.65); nz = t.sep(t.gnormal)[2]
    base = t.ramp(n, [(0.3, col[0]), (0.55, col[1]), (0.8, col[2])]); base = t.hsv(base, v=t.maprange(cv[0], 0, 1, 0.75, 1.25))
    band = t.ramp(t.noise(1.0, 3, 0.6, vec=t.mapping(scale=(7, 7, 7))), [(0.52, 0.0), (0.6, 1.0)]); base = t.mix(t.math('MULTIPLY', band, 0.6), base, tuple(c * 0.25 for c in col[1]))
    base = t.mix(t.math('MULTIPLY', t.ramp(cell, [(0.0, 1.0), (0.1, 0.0)]), 0.6), base, (0.01, 0.02, 0.008)); base = t.mix(t.maprange(nz, -0.9, -0.3, 0.6, 0.0), base, (0.30, 0.32, 0.16))
    t.set(base=base, rough=0.75 if stone_like else t.mixf(n, 0.22, 0.4), normal=t.bump(t.ramp(cell, [(0.0, 0.0), (0.3, 1.0)]), 0.8, 0.002), coat=0.0 if stone_like else 0.4, coat_rough=0.1)
    return t.mat


def snake_pillar(hi, c):
    """round stone column, 2.5 m, with a base and capital, a green snake wound four times round it"""
    seg = 64 if hi else 20
    col = L.lathe('column', [(0, 0), (0.30, 0), (0.30, 0.10), (0.25, 0.14), (0.235, 0.22), (0.22, 0.30), (0.205, 2.1), (0.22, 2.18), (0.27, 2.24), (0.28, 2.36), (0.24, 2.42), (0.26, 2.5), (0, 2.5)], seg=seg, c=c, cap0=False, cap1=False)
    if hi:
        L.subsurf(col, 2); chisel(col, 5, 0.0012); Pq = L.co(col); nrm = L.vnormals(col); z = Pq[:, 2]; drums = np.exp(-(((z - 0.3) / 0.45) % 1.0 - 0.5) ** 2 / 0.0008) * smoothstep(0.3, 0.35, z) * (1 - smoothstep(2.05, 2.1, z))
        a = np.arctan2(Pq[:, 1], Pq[:, 0]); flute = (0.5 + 0.5 * np.cos(a * 14)) ** 3 * smoothstep(0.32, 0.4, z) * (1 - smoothstep(2.0, 2.08, z))
        L.set_co(col, Pq - nrm * (drums * 0.006 + flute * 0.006)[:, None]); col.data.materials.append(stone(31, tint=(0.92, 0.84, 0.68), value=1.05, sat=0.6, moss=0.3))
    pts = []
    for i in range(72):
        t = i / 71; a = t * 4.1 * 2 * math.pi; r = 0.235 + 0.03 - 0.02 * t; pts.append((r * math.cos(a), r * math.sin(a), 0.42 + 1.45 * t))
    pts += [(0.30 * math.cos(pts[-1][2] * 0 + 4.1 * 2 * math.pi + 0.25), 0.30 * math.sin(4.1 * 2 * math.pi + 0.25), 1.93), (0.38 * math.cos(4.1 * 2 * math.pi + 0.5), 0.38 * math.sin(4.1 * 2 * math.pi + 0.5), 1.98)]
    sn = snake('snake', pts, 0.036, 0.03, c, hi)
    if hi:
        sn.data.materials.append(snake_mat())
    return [col, sn]


def snake_carving(hi, c):
    """small stone snake, 45 cm, carved in one S-curve from green soapstone"""
    pts = [(-0.2 + 0.42 * t, 0.07 * math.sin(t * 7.5) * (1 - 0.4 * t), 0.028 + 0.02 * max(0, t - 0.75) * 4) for t in np.linspace(0, 1, 26)]
    sn = snake('carving', pts, 0.027, 0.024, c, hi, head=1.45)
    if hi:
        chisel(sn, 9, 0.0012); sn.data.materials.append(snake_mat(((0.05, 0.10, 0.045), (0.12, 0.2, 0.09), (0.25, 0.33, 0.17)), stone_like=True))
    return [sn]


# ---------------------------------------------------------------------------------------------- idol, duck
def idol(hi, c):
    """squat horned demon idol, 1.05 m, cut from one block of brown stone: hunched shoulders, arms folded on the belly, five horns"""
    J = {'base': (0, 0, 0.12), 'belly': (0, -0.02, 0.38), 'chest': (0, 0.0, 0.62), 'head': (0, -0.05, 0.80), 'jaw': (0, -0.13, 0.72), 'brow': (0, -0.14, 0.86)}
    R = {'base': (0.34, 0.28, 0.12), 'belly': (0.33, 0.27, 0.22), 'chest': (0.30, 0.22, 0.18), 'head': (0.17, 0.17, 0.15), 'jaw': (0.13, 0.09, 0.07), 'brow': (0.15, 0.06, 0.04)}
    E = [('base', 'belly'), ('belly', 'chest'), ('chest', 'head'), ('head', 'jaw'), ('head', 'brow')]
    for s, sx in (('l', 1), ('r', -1)):
        J.update({'sh' + s: (0.33 * sx, 0.0, 0.66), 'el' + s: (0.42 * sx, -0.08, 0.42), 'ha' + s: (0.16 * sx, -0.27, 0.36), 'kn' + s: (0.30 * sx, -0.26, 0.16), 'ft' + s: (0.22 * sx, -0.38, 0.06)})
        R.update({'sh' + s: 0.15, 'el' + s: 0.10, 'ha' + s: (0.09, 0.08, 0.07), 'kn' + s: 0.13, 'ft' + s: (0.11, 0.12, 0.06)})
        E += [('chest', 'sh' + s), ('sh' + s, 'el' + s), ('el' + s, 'ha' + s), ('base', 'kn' + s), ('kn' + s, 'ft' + s)]
    body = C.graph_body('idol', J, E, R, c, voxel=0.008 if hi else 0.02, smooth=6 if hi else 3); parts = [body]
    for k, (hx, hz, ln) in enumerate(((0, 0.93, 0.2), (0.1, 0.90, 0.16), (-0.1, 0.90, 0.16), (0.17, 0.82, 0.13), (-0.17, 0.82, 0.13))):
        parts.append(C.cone('horn%d' % k, (hx, -0.04, hz - 0.03), (hx * 1.7, -0.02, hz + ln), 0.045, c, nu=10 if hi else 6, nv=8 if hi else 4, sharp=1.2))
    if hi:
        Pq = L.co(body); N = L.vnormals(body); x, y, z = Pq[:, 0], Pq[:, 1], Pq[:, 2]
        eye = np.exp(-(((np.abs(x) - 0.065) / 0.03) ** 2 + ((z - 0.825) / 0.018) ** 2)) * smoothstep(-0.1, -0.16, y); mouth = np.exp(-((z - (0.735 + 0.8 * x * x)) / 0.012) ** 2) * smoothstep(-0.14, -0.19, y) * (1 - smoothstep(0.09, 0.11, np.abs(x)))
        L.set_co(body, Pq - N * (eye * 0.03 + mouth * 0.02)[:, None]); m = stone(41, tint=(0.80, 0.64, 0.46), value=0.9, sat=0.7, moss=0.25, lichen=0.3)
        for o in parts:
            chisel(o, 43, 0.0015); o.data.materials.append(m)
    return parts


def duck_statue(hi, c):
    """the golden duck: a life-size-and-a-half gilt duck on a dark rough stone mound, 2.2 m to the top of its head"""
    seg = 64 if hi else 20
    mound = L.lathe('mound', [(0, 0), (0.75, 0), (0.78, 0.1), (0.66, 0.34), (0.5, 0.52), (0.42, 0.78), (0.3, 1.0), (0.16, 1.1), (0, 1.12)], seg=seg, c=c, cap0=False, cap1=False)
    J = {'body': (0, 0.06, 1.42), 'breast': (0, -0.14, 1.44), 'rump': (0, 0.30, 1.46), 'tail': (0, 0.46, 1.56), 'neck1': (0, -0.24, 1.62), 'neck2': (0, -0.26, 1.84), 'head': (0, -0.30, 2.02), 'bill': (0, -0.46, 1.98), 'billtip': (0, -0.56, 1.96),
         'legl': (0.09, 0.04, 1.2), 'legr': (-0.09, 0.04, 1.2), 'footl': (0.1, -0.06, 1.13), 'footr': (-0.1, -0.06, 1.13)}
    R = {'body': (0.2, 0.26, 0.19), 'breast': (0.18, 0.18, 0.18), 'rump': (0.15, 0.16, 0.13), 'tail': (0.08, 0.08, 0.03), 'neck1': (0.085, 0.09, 0.1), 'neck2': 0.065, 'head': (0.085, 0.1, 0.085), 'bill': (0.055, 0.07, 0.03), 'billtip': (0.045, 0.03, 0.016),
         'legl': 0.03, 'legr': 0.03, 'footl': (0.07, 0.09, 0.02), 'footr': (0.07, 0.09, 0.02)}
    E = [('breast', 'body'), ('body', 'rump'), ('rump', 'tail'), ('breast', 'neck1'), ('neck1', 'neck2'), ('neck2', 'head'), ('head', 'bill'), ('bill', 'billtip'), ('body', 'legl'), ('body', 'legr'), ('legl', 'footl'), ('legr', 'footr')]
    duck = C.graph_body('duck', J, E, R, c, voxel=0.007 if hi else 0.02, smooth=8 if hi else 3)
    if hi:
        L.subsurf(mound, 2); L.displace_np(mound, lambda Q: 0.035 * fbm(Q, 3, 2.5, 3) + 0.012 * fbm(Q, 5, 9, 3)); mound.data.materials.append(stone(51, tint=(0.36, 0.40, 0.52), value=0.6, sat=0.5, moss=0.4, lichen=0.25, scan='rock_boulder_dry', scale=1.2))
        Pq = L.co(duck); N = L.vnormals(duck); x, y, z = Pq[:, 0], Pq[:, 1], Pq[:, 2]; wing = np.exp(-((np.abs(x) - 0.17) / 0.06) ** 2) * smoothstep(1.3, 1.4, z) * smoothstep(-0.12, 0.0, y)
        feather = (0.5 + 0.5 * np.sin((y * 1.6 + z) * 70)) * wing; eye = np.exp(-(((np.abs(x) - 0.07) / 0.014) ** 2 + ((z - 2.045) / 0.014) ** 2 + ((y + 0.33) / 0.02) ** 2))
        L.set_co(duck, Pq + N * (wing * 0.012 + feather * 0.004 - eye * 0.008 + 0.0015 * fbm(Pq, 7, 60, 2))[:, None])
        t = NT('gilt'); n = t.noise(22, 5, 0.65); pit = t.noise(400, 3, 0.6); ao = t.ao(0.03, 10); hi_ = t.ramp(t.pointiness, [(0.5, 0.0), (0.57, 1.0)])
        base = t.mix(n, (0.72, 0.42, 0.08), (0.95, 0.62, 0.16)); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.9, 0.0)]), 0.75), base, (0.10, 0.06, 0.02)); wear = t.ramp(t.noise(9, 4, 0.7), [(0.66, 0.0), (0.76, 1.0)])
        base = t.mix(t.math('MULTIPLY', wear, 0.5), base, (0.10, 0.11, 0.09)); t.set(base=base, rough=t.mixf(hi_, t.mixf(pit, 0.28, 0.48), 0.16), metal=t.mixf(wear, 1.0, 0.5), normal=t.bump(pit, 0.2, 0.0006)); duck.data.materials.append(t.mat)
    return [mound, duck]


# ---------------------------------------------------------------------------------------------- arch, fountain, cave hole
def blocks(parts, name, mn, mx, c, hi, mat, seed=0, rot=None, bevel=0.012, warp=0.004):
    o = L.box(name, mn, mx, c, hi, bevel=bevel, warp=warp, seed=seed, rot=rot)
    if hi:
        o.data.materials.append(mat)
    parts.append(o); return o


def arch(hi, c):
    """freestanding ashlar archway, 2.3 m wide and 3.5 m tall: two piers of six courses on plinths, an arch of eleven voussoirs with a keystone"""
    m = [stone(60 + k, tint=(0.90 + 0.03 * k, 0.82, 0.66), value=1.0, sat=0.6, moss=0.3) for k in range(3)] if hi else [None] * 3; parts = []; D = 0.42; W = 0.46; span = 1.3
    for s in (-1, 1):
        x0 = s * (span / 2 + W / 2); blocks(parts, 'plinth', (x0 - W / 2 - 0.05, -D / 2 - 0.05, 0), (x0 + W / 2 + 0.05, D / 2 + 0.05, 0.22), c, hi, m[0], seed=1 + s)
        for k in range(6):
            blocks(parts, 'course', (x0 - W / 2 + 0.006 * (k % 2), -D / 2, 0.22 + k * 0.34), (x0 + W / 2 - 0.004 * (k % 2), D / 2, 0.22 + (k + 1) * 0.34 - 0.006), c, hi, m[k % 3], seed=10 + k + 7 * s)
        blocks(parts, 'impost', (x0 - W / 2 - 0.04, -D / 2 - 0.03, 2.26), (x0 + W / 2 + 0.04, D / 2 + 0.03, 2.38), c, hi, m[1], seed=30 + s)
    zc = 2.38; Ri = span / 2; Ro = Ri + W; n = 11
    for k in range(n):
        a0 = math.pi * k / n; a1 = math.pi * (k + 1) / n; am = (a0 + a1) / 2; wd = (Ri + Ro) / 2 * (a1 - a0) - 0.008; key = (k == n // 2)
        o = blocks(parts, 'voussoir', (-wd / 2, -D / 2 - (0.03 if key else 0), Ri), (wd / 2, D / 2 + (0.03 if key else 0), Ro + (0.08 if key else 0)), c, hi, m[k % 3], seed=40 + k)
        L.xform(o, Matrix.Translation((0, 0, zc)) @ Matrix.Rotation(am - math.pi / 2, 4, 'Y') if False else Matrix.Translation((0, 0, zc)) @ Matrix.Rotation(-(am - math.pi / 2), 4, 'Y'))
    return parts


def fountain(hi, c):
    """round stone fountain, 2.7 m across: a basin wall of twelve stones with a coping, still water, a pedestal with an upper bowl"""
    seg = 96 if hi else 28; parts = []; m = stone(71, tint=(0.70, 0.74, 0.82), value=0.8, sat=0.5, moss=0.45, lichen=0.3) if hi else None
    wall = L.lathe('wall', [(0, 0.0), (1.36, 0.0), (1.38, 0.08), (1.30, 0.12), (1.30, 0.44), (1.37, 0.48), (1.37, 0.58), (1.08, 0.58), (1.08, 0.50), (1.12, 0.46), (1.12, 0.16), (0, 0.14)], seg=seg, c=c, cap0=False, cap1=False)
    ped = L.lathe('pedestal', [(0, 0.12), (0.34, 0.12), (0.34, 0.22), (0.24, 0.28), (0.2, 0.5), (0.18, 0.92), (0.24, 1.0), (0.42, 1.06), (0.5, 1.14), (0.5, 1.2), (0.42, 1.2), (0.36, 1.13), (0.1, 1.1), (0, 1.16)], seg=seg, c=c, cap0=False, cap1=False)
    water = L.lathe('water', [(0, 0.40), (1.125, 0.40), (1.125, 0.36), (0, 0.36)], seg=seg, c=c, cap0=False, cap1=False)
    for o in (wall, ped):
        if hi:
            L.subsurf(o, 2); chisel(o, 5, 0.004); o.data.materials.append(m)
    if hi:
        Pq = L.co(wall); nrm = L.vnormals(wall); a = np.arctan2(Pq[:, 1], Pq[:, 0]); r = np.hypot(Pq[:, 0], Pq[:, 1]); joint = np.exp(-(((a * 6 / np.pi) % 1.0 - 0.5) / 0.035) ** 2) * smoothstep(1.0, 1.1, r); L.set_co(wall, Pq - nrm * (joint * 0.008)[:, None])
        L.subsurf(water, 2); t = NT('water'); n = t.noise(3.0, 4, 0.6); rip = t.noise(26, 3, 0.6, distortion=1.0); scum = t.ramp(t.noise(7, 5, 0.7), [(0.56, 0.0), (0.68, 1.0)])
        col = t.mix(n, (0.010, 0.030, 0.040), (0.020, 0.065, 0.075)); col = t.mix(t.math('MULTIPLY', scum, 0.6), col, (0.10, 0.16, 0.05)); t.set(base=col, rough=t.mixf(scum, 0.04, 0.5), normal=t.bump(rip, 0.12, 0.004), spec=0.8)
        water.data.materials.append(t.mat)
    return [wall, ped, water]


def cave_hole(hi, c):
    """timber-shored hole into a cave, 1.7 x 1.3 m: a log kerb at ground level, plank-lined walls going down 1.3 m, two planks left as a ramp, dark earth below"""
    wm = [T.wood_mat('shoring_%s' % 'xyz'[a], axis=a, light=(0.24, 0.15, 0.075), dark=(0.085, 0.048, 0.022)) for a in range(3)] if hi else [None] * 3; parts = []; X, Y, Dp = 0.85, 0.65, 1.3

    def bd(name, mn, mx, seed, rot=None, bev=0.012):
        d = np.abs(np.array(mx) - np.array(mn)); ax = int(np.argmax(d)); o = L.box(name, mn, mx, c, hi, bevel=bev, warp=0.006, seed=seed, rot=rot)
        if hi:
            o.data.materials.append(wm[ax])
        parts.append(o); return o
    bd('kerb_n', (-X - 0.16, Y, -0.04), (X + 0.16, Y + 0.16, 0.13), 1); bd('kerb_s', (-X - 0.16, -Y - 0.16, -0.04), (X + 0.16, -Y, 0.13), 2); bd('kerb_e', (X, -Y - 0.02, -0.03), (X + 0.15, Y + 0.02, 0.11), 3); bd('kerb_w', (-X - 0.15, -Y - 0.02, -0.03), (-X, Y + 0.02, 0.11), 4)
    for k in range(5):                                         # plank lining, long sides then ends
        z1 = -0.02 - k * 0.26; z0 = z1 - 0.25
        bd('lin_n%d' % k, (-X, Y - 0.035, z0), (X, Y, z1), 10 + k); bd('lin_s%d' % k, (-X, -Y, z0), (X, -Y + 0.035, z1), 20 + k); bd('lin_e%d' % k, (X - 0.035, -Y, z0), (X, Y, z1), 30 + k); bd('lin_w%d' % k, (-X, -Y, z0), (-X + 0.035, Y, z1), 40 + k)
    for k, y in enumerate((-0.3, 0.02)):                       # two ramp planks from the west kerb down to the floor
        bd('ramp%d' % k, (-X + 0.02, y, -0.02), (-X + 0.02 + 1.75, y + 0.26, 0.02), 50 + k, rot=('Y', math.radians(40), (-X + 0.02, 0, 0.0)))
    fl = L.box('floor', (-X, -Y, -Dp - 0.06), (X, Y, -Dp), c, hi, bevel=0.01, warp=0.03, seed=60); parts.append(fl)
    if hi:
        t = NT('earth'); n = t.noise(9, 5, 0.65); t.set(base=t.mix(n, (0.012, 0.009, 0.006), (0.045, 0.032, 0.02)), rough=0.95, normal=t.bump(t.noise(40, 4, 0.6), 0.6, 0.01)); fl.data.materials.append(t.mat)
    return parts


# ---------------------------------------------------------------------------------------------- teleport machine
def teleport(hi, c):
    """armillary sphere on a brick-domed drum, 3 m: brass meridian, equator and tilted rings on an axis, a crescent finial"""
    seg = 64 if hi else 20; parts = []
    drum = L.lathe('drum', [(0, 0), (0.62, 0), (0.64, 0.1), (0.58, 0.14), (0.58, 0.5), (0.62, 0.56), (0.56, 0.62), (0.5, 0.82), (0.36, 1.0), (0.18, 1.1), (0.12, 1.16), (0, 1.18)], seg=seg, c=c, cap0=False, cap1=False); parts.append(drum)
    cz = 1.86; Rr = 0.62; rings = []
    for k, (M, R_, r_) in enumerate(((Matrix.Rotation(math.pi / 2, 4, 'X'), Rr, 0.026), (Matrix.Rotation(math.pi / 2, 4, 'Y'), Rr * 0.985, 0.022), (Matrix.Identity(4), Rr * 0.97, 0.03),
                                     (Matrix.Rotation(math.radians(23.5), 4, 'X'), Rr * 0.88, 0.02), (Matrix.Rotation(math.radians(-40), 4, 'Y') @ Matrix.Rotation(math.radians(20), 4, 'X'), Rr * 0.78, 0.018))):
        o = L.ring('ring%d' % k, R_, r_, c, seg=72 if hi else 22, sides=12 if hi else 5, squash=1.6); L.xform(o, Matrix.Translation((0, 0, cz)) @ M); rings.append(o)
    axis = L.sweep('axis', [(0, 0, 1.14, 0.03, 0.03, 2), (0, 0, 1.3, 0.022, 0.022, 2), (0, 0, 2.5, 0.02, 0.02, 2), (0, 0, 2.62, 0.035, 0.035, 2), (0, 0, 2.66, 0.012, 0.012, 2)], nu=12 if hi else 6, nv=24 if hi else 6, c=c, up=(0, 1, 0), cap=0.6)
    globe = L.icosphere('globe', 0.11, 4 if hi else 2, c); Pq = L.co(globe); Pq[:, 2] += cz; L.set_co(globe, Pq); globe.data.polygons.foreach_set('use_smooth', [True] * len(globe.data.polygons))
    cres = []
    for i in range(9):
        t = i / 8; a = -0.5 + t * 4.0; cres.append((0.17 * math.cos(a), 0.0, 2.84 + 0.17 * math.sin(a), 0.006 + 0.03 * math.sin(math.pi * t), 0.014, 2.6))
    cr = L.sweep('crescent', cres, nu=10 if hi else 5, nv=40 if hi else 9, c=c, up=(0, 1, 0), cap=0.3); brass_parts = rings + [axis, globe, cr]; parts += brass_parts
    if hi:
        L.subsurf(drum, 2); Pq = L.co(drum); nrm = L.vnormals(drum); z = Pq[:, 2]; a = np.arctan2(Pq[:, 1], Pq[:, 0]); row = np.floor(z / 0.075); bj = np.maximum(np.exp(-(((z / 0.075) % 1.0 - 0.5) / 0.08) ** 2), np.exp(-((((a * 14 / np.pi) + (row % 2) * 0.5) % 1.0 - 0.5) / 0.05) ** 2))
        msk = smoothstep(0.13, 0.16, z) * (1 - smoothstep(1.0, 1.08, z)); L.set_co(drum, Pq - nrm * (bj * msk * 0.006)[:, None]); C.set_attr(drum, 'mortar', bj * msk)
        t = NT('brick'); mo = t.attr('mortar'); n = t.noise(8, 5, 0.65); n2 = t.noise(90, 4, 0.6); cv = t.sep(t.voronoi(13.3, out='Color', vec=t.mapping(scale=(1, 1, 1))))
        col = t.ramp(n, [(0.3, (0.16, 0.055, 0.03)), (0.55, (0.28, 0.10, 0.05)), (0.8, (0.38, 0.17, 0.09))]); col = t.hsv(col, v=t.maprange(n2, 0.2, 0.8, 0.8, 1.2)); col = t.mix(mo, col, t.mix(n2, (0.22, 0.20, 0.17), (0.38, 0.36, 0.31)))
        ao = t.ao(0.05, 8); col = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.9, 0.0)]), 0.6), col, (0.03, 0.025, 0.02)); t.set(base=col, rough=t.mixf(n2, 0.7, 0.92), normal=t.bump(n2, 0.4, 0.002)); drum.data.materials.append(t.mat)
        b = NT('brass'); n = b.noise(20, 5, 0.65); pit = b.noise(300, 3, 0.6); ao = b.ao(0.02, 8); verd = b.ramp(b.math('ADD', b.noise(7, 5, 0.7), b.math('MULTIPLY', b.math('SUBTRACT', 1.0, ao), 0.5)), [(0.6, 0.0), (0.75, 1.0)])
        col = b.mix(n, (0.50, 0.30, 0.07), (0.78, 0.55, 0.16)); col = b.mix(b.math('MULTIPLY', b.ramp(ao, [(0.4, 1.0), (0.9, 0.0)]), 0.7), col, (0.07, 0.045, 0.02)); col = b.mix(b.math('MULTIPLY', verd, 0.75), col, b.mix(pit, (0.07, 0.20, 0.16), (0.16, 0.36, 0.28)))
        b.set(base=col, rough=b.mixf(verd, b.mixf(pit, 0.25, 0.42), 0.8), metal=b.mixf(verd, 1.0, 0.1), normal=b.bump(pit, 0.25, 0.0006))
        for o in brass_parts:
            o.data.materials.append(b.mat)
    return parts


W_STONE = ' Stone is one tinted rock scan with procedural moss and lichen; carving detail comes from displacement, not from modelled tool work.'
SPECS = {
    'Save_Machine': dict(fn=save_machine, fam='save_machine', seq='449 inter/save/save- frame 1', cls='prop', px=2048, tris=7000, ground='forrest_ground_01', third=['rock_face_03'], shot=dict(az=30, el=26, fill=0.85, close=(0.3, 0.3, 0.6, 0.25)),
                         weak='Read from a 120-pixel frame: a stepped stone ring with a bowl, four horn scrolls, eight timber spokes and an iron grating. The original has more ornament (interlaced arcs) than is built, and nothing here moves or glows; in game the machine is animated and lit when used. Spokes share one wood material whose grain follows world X, not each spoke.' + W_STONE,
                         dresses='save machine: round stone hearth 2.3 m across (3.1 m over the spokes), sunk bowl with a boss, four horn scrolls over the rim, eight oak spokes, iron grating round the foot',
                         extra={'triangle_note': '7,000 triangles: above the 6,000 soft target of class prop, spent on the ring and scrolls'}),
    'Snake_Pillar': dict(fn=snake_pillar, fam='snake_pillar', seq='82 inside/stnwalls/snake/snakc- frame 1', cls='prop', px=1024, tris=3000, uv_angle=40, ground='forrest_ground_01', third=['rock_face_03'], shot=dict(az=30, el=10, fill=1.15, close=(0.5, 0.5, 0.72, 0.16)),
                         weak='The snake is a smooth tapering sweep with a wedge head: no eyes, mouth or belly scutes, and it floats a few millimetres off the shaft in places instead of pressing into it. Scripted pillars in the game animate the snake; this is the still frame.' + W_STONE,
                         dresses='sandstone column, 2.5 m, fluted drums on a moulded base, a green snake wound four times round the shaft with its head lifted'),
    'Snake_Carving': dict(fn=snake_carving, fam='snake_carving', seq='81 inside/stnwalls/snake/snakb- frame 1', cls='prop_small', px=512, tris=700, ground='weathered_brown_planks', third=[],
                          weak='A 15-pixel frame: built as a small S-curved soapstone snake. Scales are a Voronoi pattern in the normal map; no eyes or mouth.', dresses='small green soapstone snake carving, 45 cm, one S-curve with a wedge head'),
    'Idol_Demon': dict(fn=idol, fam='idol_statue_small', seq='80 inside/stnwalls/stonw- frame 24', cls='prop', px=1024, tris=3500, ground='forrest_ground_01', third=['rock_face_03'], shot=dict(az=20, el=14, fill=1.0, close=(0.5, 0.2, 0.8, 0.22)),
                       weak='A fused blob figure with pressed-in eyes and mouth: it reads as a worn idol at gameplay distance, but there is no cut detail (fingers, teeth, ornament) and the horns are plain cones. The game pushes this idol along the floor; no base slab is modelled.' + W_STONE,
                       dresses='squat horned demon idol in brown stone, 1.1 m: hunched shoulders, arms folded on the belly, five horns, sunk eyes and a wide mouth'),
    'Duck_Statue_Gold': dict(fn=duck_statue, fam='golden_duck_statue', seq='159 struct/stone/mdink/monum- frame 8', cls='prop', px=1024, tris=4500, ground='forrest_ground_01', third=['rock_boulder_dry'], shot=dict(az=35, el=10, fill=1.1, close=(0.5, 0.3, 0.8, 0.2)),
                             weak='The duck is a fused blob form with a wing relief and feather ridges from displacement: no modelled primaries, webbing or eye, so at 1 m it reads as a cast lump in the shape of a duck. Gilding is clean gold with dirt in the hollows and a few worn patches.' + W_STONE,
                             dresses='the golden duck statue: a gilt duck, 0.9 m, standing on a dark blue-grey rock mound, 2.1 m in all'),
    'Arch_Stone': dict(fn=arch, fam='dungeon_arch_freestanding', seq='80 inside/stnwalls/stonw- frame 25', cls='prop_large', px=2048, tris=0, lo='param', ground='forrest_ground_01', third=['rock_face_03'], extrude=0.008, maxdist=0.025, shot=dict(az=28, el=8, fill=1.15, close=(0.5, 0.2, 0.75, 0.2)),
                       weak='Every stone is a bevelled block of 12 triangles in the game mesh: joints are real gaps, arrises are in the normal map only. No mortar, and all blocks of a course are one stone deep. One convex hull is exported, which blocks the opening: a walk-through arch needs two pier hulls and a lintel hull, a level decision.' + W_STONE,
                       dresses='freestanding sandstone archway, 2.3 m wide and 3.4 m tall: plinths, two piers of six courses, imposts, a round arch of eleven voussoirs with a proud keystone'),
    'Fountain_Stone': dict(fn=fountain, fam='fountain_stone', seq='66 lands/garden/gardn- frames 23, 24', cls='prop', px=2048, tris=5000, ground='forrest_ground_01', third=['rock_face_03'], shot=dict(az=30, el=24, fill=0.9, close=(0.5, 0.4, 0.7, 0.22)),
                           weak='The water is a still, opaque dark disc with ripples in the normal map and a little algae: no transparency, depth or flow, and the spray of the original (family fountain_spray_fx) is not here. Wall stones are scored joints in one ring, not separate blocks.' + W_STONE,
                           dresses='round stone fountain, 2.75 m across: basin wall of twelve stones with a coping, dark still water, a central pedestal carrying an upper bowl, 1.2 m tall'),
    'Cave_Hole': dict(fn=cave_hole, fam='cave_hole_warp', seq='89 lands/details/crack- frame 10', cls='prop', px=2048, tris=0, lo='param', ground='forrest_ground_01', third=[], keep_z=True, ground_hole=(0.85, 0.65), extrude=0.006, maxdist=0.02, shot=dict(az=32, el=42, fill=0.9, close=(0.4, 0.5, 0.6, 0.3)),
                      weak='The shaft goes 1.3 m below z = 0, so it only shows where the terrain has a matching hole cut (or as a raised kerb if it has not): that is level work, not done here. Planks are bevelled blocks without nails or bark. The floor is a dark slab, not a cave. The convex hull covers the opening, so the warp trigger must stay the gameplay collision.',
                      dresses='timber-shored hole into a cave, 1.7 x 1.3 m: log kerb at ground level, plank lining going down 1.3 m, two planks left as a ramp, dark earth at the bottom',
                      extra={'pivot': 'ground level at the centre of the opening (z = 0); the shaft is below it'}),
    'Teleport_Machine': dict(fn=teleport, fam='teleport_machine', seq='84 struct/teleport/telep- frame 1', cls='prop', px=2048, tris=6000, ground='forrest_ground_01', third=[], shot=dict(az=30, el=8, fill=1.15, close=(0.5, 0.5, 0.64, 0.24)),
                             weak='Rings are plain flattened brass hoops without graduations, pivots or the small planets of a real armillary, and they do not turn. The brick drum is one lathed body with joints pressed in. In game the machine flashes when used; no emissive map is authored.',
                             dresses='teleport machine: an armillary sphere 1.25 m across (meridian, equator and three tilted rings round a small globe on a polar axis) with a crescent finial, on a brick-domed drum, 3 m tall'),
}
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
