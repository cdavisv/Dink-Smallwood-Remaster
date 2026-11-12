"""Buildings of the unclaimed families: the log cabin (59 struct/cabin/cabin- frame 1).

Every log is its own swept solid, notched over its neighbours at the corners; the roof is two shingled slabs; the chimney
is fieldstone blocks. Door and window openings are left for the door and window families.

    tools/bl.sh build_buildings.py <Log_Cabin|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
import build_props as P
import build_props3 as P3
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_buildings.py'


def log_mat(axis, seed=0.0):
    """peeled, weathered pine log: silver-brown, long drying checks, knots, darker damp underside, pale end grain is left to the cap colour"""
    t = NT('log_%s' % 'xyz'[axis]); sc = [26.0, 26.0, 26.0]; sc[axis] = 0.9; gr = t.noise(1.0, 6, 0.65, vec=t.mapping(scale=tuple(sc), loc=(seed, 0, 0)), distortion=0.8)
    sc2 = [120.0, 120.0, 120.0]; sc2[axis] = 1.6; chk = t.ramp(t.noise(1.0, 3, 0.6, vec=t.mapping(scale=tuple(sc2))), [(0.60, 0.0), (0.66, 1.0)]); knot = t.ramp(t.voronoi(3.2, feature='F1', vec=t.mapping(loc=(seed, 1, 2))), [(0.0, 1.0), (0.06, 0.0)])
    base = t.ramp(gr, [(0.3, (0.075, 0.055, 0.038)), (0.5, (0.17, 0.135, 0.095)), (0.75, (0.30, 0.26, 0.20))]); base = t.mix(t.math('MULTIPLY', chk, 0.8), base, (0.02, 0.015, 0.01)); base = t.mix(t.math('MULTIPLY', knot, 0.7), base, (0.05, 0.03, 0.015))
    nz = t.sep(t.gnormal)[2]; under = t.maprange(nz, -0.9, -0.2, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', under, 0.6), base, (0.03, 0.028, 0.022)); moss = t.math('MULTIPLY', t.ramp(t.noise(5, 5, 0.7, vec=t.mapping(loc=(2, seed, 5))), [(0.58, 0.0), (0.7, 1.0)]), t.maprange(nz, 0.0, 0.7, 0.0, 1.0))
    base = t.mix(t.math('MULTIPLY', moss, 0.6), base, (0.045, 0.075, 0.02)); ao = t.ao(0.12, 10); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.3, 1.0), (0.8, 0.0)]), 0.75), base, (0.015, 0.012, 0.009))
    t.set(base=base, rough=t.mixf(gr, 0.7, 0.9), normal=t.bump(t.math('ADD', t.math('ADD', t.math('MULTIPLY', gr, 0.6), t.math('MULTIPLY', chk, -2.5)), t.math('MULTIPLY', knot, 1.0)), 0.45, 0.004)); return t.mat


WOOD_SHINGLE = ((0.07, 0.065, 0.058), (0.16, 0.15, 0.135), (0.30, 0.29, 0.26))
SLATE = ((0.030, 0.034, 0.042), (0.075, 0.082, 0.098), (0.15, 0.16, 0.18))
STONE_SLAB = ((0.10, 0.10, 0.085), (0.20, 0.20, 0.17), (0.33, 0.33, 0.29))


def shingle_mat(pitch, ridge_z, course=0.2, width=0.16, mode='ridge', apex=(0.0, 0.0), cols=WOOD_SHINGLE, moss_amt=0.7, name='shingles', lift=0.012):
    """roof covering laid in courses: each piece its own tone, dark laps and butt shadows, moss in the laps.
    mode 'ridge': ridge along X at y = 0; 'cone' / 'pyramid': courses by height below the apex (ridge_z), columns round the cone or along each pyramid face"""
    t = NT(name); sp = t.sep(t.obj); x = t.math('SUBTRACT', sp[0], apex[0]); y = t.math('SUBTRACT', sp[1], apex[1])
    if mode == 'ridge':
        d = t.math('DIVIDE', t.math('ABSOLUTE', sp[1]), math.cos(pitch)); u = sp[0]
    else:
        d = t.math('DIVIDE', t.math('SUBTRACT', ridge_z, sp[2]), math.sin(pitch))
        if mode == 'cone':
            u = t.math('MULTIPLY', t.math('ARCTAN2', y, x), 2.2)
        else:
            m = t.math('GREATER_THAN', t.math('ABSOLUTE', x), t.math('ABSOLUTE', y)); u = t.math('ADD', t.math('MULTIPLY', x, t.math('SUBTRACT', 1.0, m)), t.math('MULTIPLY', y, m))
    fr = t.math('DIVIDE', d, course); row = t.math('FLOOR', fr); rf = t.math('FRACT', fr)
    fx = t.math('ADD', t.math('DIVIDE', u, width), t.math('MULTIPLY', row, 0.47)); col = t.math('FLOOR', fx); cf = t.math('FRACT', fx); cv = t.sep(t.voronoi(1.0, vec=t.comb(col, row, 0.0), out='Color'))
    gr = t.noise(1.0, 5, 0.65, vec=t.comb(t.math('MULTIPLY', u, 90.0), t.math('MULTIPLY', d, 4.0), cv[0]), distortion=0.6); base = t.ramp(gr, [(0.3, cols[0]), (0.5, cols[1]), (0.75, cols[2])])
    base = t.hsv(base, v=t.maprange(cv[1], 0, 1, 0.65, 1.25)); gap = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', cf, 0.5)), [(0.455, 0.0), (0.49, 1.0)]); butt = t.ramp(rf, [(0.9, 0.0), (0.98, 1.0)])
    base = t.mix(t.math('MULTIPLY', t.math('MAXIMUM', gap, butt), 0.9), base, (0.012, 0.011, 0.01)); moss = t.math('MULTIPLY', t.ramp(t.noise(1.6, 5, 0.7), [(0.5, 0.0), (0.66, 1.0)]), t.ramp(rf, [(0.3, 0.2), (0.9, 1.0)])); base = t.mix(t.math('MULTIPLY', moss, moss_amt), base, t.mix(gr, (0.03, 0.06, 0.015), (0.09, 0.13, 0.03)))
    h = t.math('ADD', t.math('ADD', t.math('MULTIPLY', t.math('SUBTRACT', 1.0, rf), 1.2), t.math('MULTIPLY', gr, 0.3)), t.math('MULTIPLY', t.math('MAXIMUM', gap, butt), -2.0)); t.set(base=base, rough=t.mixf(gr, 0.75, 0.92), normal=t.bump(h, 0.6, lift)); return t.mat


def ashlar_mat(name, tint=(0.34, 0.37, 0.44), bw=0.62, rh=0.31, round_at=None, seed=0.0, moss=0.35, value=1.0):
    """coursed stone wall in object space: stones of varied tone with recessed mortar joints, a rock scan for the faces, rain streaks under ledges, moss and damp at the foot.
    round_at = (cx, cy, r): courses wrap a round wall"""
    t = NT(name); sp = t.sep(t.obj)
    h = t.math('MULTIPLY', t.math('ARCTAN2', t.math('SUBTRACT', sp[1], round_at[1]), t.math('SUBTRACT', sp[0], round_at[0])), round_at[2]) if round_at else t.math('ADD', sp[0], sp[1])
    br = t.node('ShaderNodeTexBrick'); br.offset = 0.5; t._in(br.inputs['Vector'], t.comb(h, sp[2], 0.0)); t._in(br.inputs['Scale'], 1.0); t._in(br.inputs['Mortar Size'], 0.012); t._in(br.inputs['Mortar Smooth'], 0.3); t._in(br.inputs['Bias'], 0.0)
    t._in(br.inputs['Brick Width'], bw); t._in(br.inputs['Row Height'], rh); t._in(br.inputs['Color1'], (0.55, 0.55, 0.55, 1.0)); t._in(br.inputs['Color2'], (1.0, 1.0, 1.0, 1.0)); t._in(br.inputs['Mortar'], (0.0, 0.0, 0.0, 1.0)); mortar = br.outputs['Fac']; tone = t.sep(br.outputs['Color'])[0]
    sc = t.scan('rock_face_03', scale=1.1, loc=(seed, seed * 0.4, 0)); n = t.noise(0.6, 5, 0.65, vec=t.mapping(loc=(seed, 0, 3))); n2 = t.noise(40, 4, 0.6)
    base = t.hsv(sc['diff'], sat=0.35, v=t.math('MULTIPLY', t.maprange(tone, 0.5, 1.0, 0.72, 1.12), value)); base = t.mix(1.0, base, tint, blend='MULTIPLY'); base = t.mix(1.0, base, (2.2, 2.2, 2.2), blend='MULTIPLY', clamp=False)
    base = t.mix(t.math('MULTIPLY', mortar, 0.85), base, t.mix(n2, (0.10, 0.10, 0.095), (0.20, 0.195, 0.18)))
    streak = t.ramp(t.noise(1.0, 4, 0.7, vec=t.comb(t.math('MULTIPLY', h, 3.0), t.math('MULTIPLY', sp[2], 0.25), seed)), [(0.5, 0.0), (0.72, 1.0)]); base = t.mix(t.math('MULTIPLY', streak, 0.4), base, (0.035, 0.037, 0.04))
    foot = t.maprange(t.math('ADD', sp[2], t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 1.6)), 0.0, 1.3, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', foot, moss), base, t.mix(n2, (0.03, 0.055, 0.02), (0.08, 0.11, 0.035)))
    ao = t.ao(0.4, 10); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.3, 1.0), (0.85, 0.0)]), 0.6), base, (0.02, 0.02, 0.022))
    hgt = t.math('ADD', t.math('MULTIPLY', mortar, -3.0), t.math('MULTIPLY', tone, 0.6)); t.set(base=base, rough=t.mixf(mortar, sc['rough'], 0.95), normal=t.bump(hgt, 0.7, 0.012, normal=t.normalmap(sc['nor_gl'], 0.8))); return t.mat


def plaster_mat(name, col=((0.36, 0.33, 0.26), (0.52, 0.49, 0.40)), seed=0.0):
    """old lime plaster: trowel undulation, hairline cracks, damp grey staining low down and under timbers"""
    t = NT(name); sp = t.sep(t.obj); n = t.noise(1.2, 5, 0.65, vec=t.mapping(loc=(seed, 1, 2))); n2 = t.noise(60, 4, 0.6); base = t.mix(n, col[0], col[1])
    crack = t.ramp(t.voronoi(1.6, feature='DISTANCE_TO_EDGE', vec=t.mapping(loc=(seed, 3, 1))), [(0.0, 1.0), (0.012, 0.0)]); crack = t.math('MULTIPLY', crack, t.ramp(t.noise(0.7, 3, 0.6), [(0.45, 0.0), (0.6, 1.0)])); base = t.mix(t.math('MULTIPLY', crack, 0.7), base, (0.06, 0.055, 0.045))
    damp = t.maprange(t.math('ADD', sp[2], t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 1.2)), 0.0, 1.0, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', damp, 0.5), base, (0.12, 0.125, 0.11))
    ao = t.ao(0.25, 10); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.3, 1.0), (0.85, 0.0)]), 0.55), base, (0.05, 0.045, 0.04))
    t.set(base=base, rough=t.mixf(n2, 0.8, 0.95), normal=t.bump(t.math('ADD', t.math('MULTIPLY', t.noise(5, 4, 0.6), 1.0), t.math('ADD', t.math('MULTIPLY', n2, 0.15), t.math('MULTIPLY', crack, -1.5))), 0.5, 0.006)); return t.mat


def cut(ob, cutters):
    """boolean-difference the cutters out of ob (the cutters are kept for reuse; delete them when done)"""
    for k in cutters:
        m = ob.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = k; m.solver = 'EXACT'
    L.apply_mods(ob); ob.data.polygons.foreach_set('use_smooth', [False] * len(ob.data.polygons)); return ob


def opening(c, w, spring, kind, depth, at, yaw=0.0, sill=0.0, rise=None):
    """cutter prism for a door / window: outline in the wall plane, `depth` through the wall, centred at `at`, turned by yaw about Z"""
    out = [(x, z + sill) for x, z in L.arch_outline(w, spring, kind, n=10, rise=rise)]; o = L.prism('cutter', out, -depth / 2, depth / 2, c, False)
    L.xform(o, Matrix.Translation(at) @ Matrix.Rotation(yaw, 4, 'Z')); o.hide_render = True; return o


def roof_pair(parts, c, hi, x0, x1, half, ridge_z, pitch, mat, eave=0.4, th=0.12, seed=0):
    """two roof slabs meeting at a ridge along X at y = 0"""
    sl = (half + eave) / math.cos(pitch)
    for sy in (-1, 1):
        o = L.box('roof', (x0, 0.0 if sy > 0 else -sl, -th), (x1, sl if sy > 0 else 0.0, 0.0), c, hi, bevel=0.012, warp=0.008, seed=seed + sy)
        L.xform(o, Matrix.Translation((0, 0, ridge_z)) @ Matrix.Rotation(-pitch if sy > 0 else pitch, 4, 'X'))
        if hi:
            o.data.materials.append(mat)
        parts.append(o)


def gable(parts, c, hi, x, th, half, z0, pitch, mat, cutters=()):
    """triangular gable wall in the YZ plane at x (thickness th along X)"""
    o = L.prism('gable', [(-half, z0), (half, z0), (0.0, z0 + half * math.tan(pitch))], -th / 2, th / 2, c, hi, bevel=0.01); L.xform(o, Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'))
    if cutters:
        cut(o, cutters)
    if hi:
        L.assign(o, mat)
    parts.append(o); return o


def log_cabin(hi, c):
    """log cabin, 7.6 x 4.8 m: ten courses of notched logs, log gables, a shingled roof at 38 degrees, a fieldstone chimney on the west gable; door and window openings in the south wall"""
    parts = []; LX, LY, r = 7.0, 4.2, 0.14; sp_ = 2 * r * 0.9; n = 10; ov = 0.3; q = 3 if hi else 1; rng = np.random.default_rng(3); lm = [log_mat(a, seed=float(a)) for a in range(3)] if hi else [None] * 3

    def log(p0, p1, axis, rad=r, seed=0):
        p0 = np.array(p0, float); p1 = np.array(p1, float); rows = []
        for t_ in (0.0, 0.3, 0.7, 1.0):
            p = p0 * (1 - t_) + p1 * t_; rr = rad * (1.0 + 0.06 * math.sin(seed * 1.7 + t_ * 3)); rows.append((p[0], p[1], p[2] + 0.01 * math.sin(seed + t_ * 4), rr, rr * 0.97, 2.1))
        o = L.sweep('log', rows, nu=10 * q if hi else 8, nv=8 * q if hi else 5, c=c, up=(0, 0, 1), cap=0.8)
        if hi:
            L.displace_np(o, lambda Q: 0.004 * fbm(Q, 3 + seed, 4, 3) + 0.0015 * fbm(Q, 9 + seed, 30, 2)); o.data.materials.append(lm[axis])
        parts.append(o)
    door = (-1.9, -0.9, 2.0); win = (1.2, 2.2, 0.95, 1.75)            # door x0, x1, height; window x0, x1, z0, z1 (south wall, y = -LY/2)
    for k in range(n):
        z = r + k * sp_; zs = z + sp_ / 2
        for sy in (-1, 1):                                        # long walls (along X)
            y = sy * LY / 2; cuts = []
            if sy < 0:
                if z < door[2]:
                    cuts.append((door[0], door[1]))
                if win[2] < z < win[3]:
                    cuts.append((win[0], win[1]))
            xs = [-LX / 2 - ov] + [v for cseg in sorted(cuts) for v in cseg] + [LX / 2 + ov]
            for i in range(0, len(xs), 2):
                log((xs[i], y, z), (xs[i + 1], y, z), 0, seed=k * 7 + i + (sy > 0) * 3)
        if k < n - 1 or True:
            for sx in (-1, 1):                                    # end walls (along Y), half a course higher
                log((sx * LX / 2, -LY / 2 - ov, zs), (sx * LX / 2, LY / 2 + ov, zs), 1, seed=100 + k * 5 + (sx > 0))
    top = r + (n - 1) * sp_ + sp_ / 2 + r; pitch = math.radians(38); k = 0
    while True:                                                   # log gables, each course shorter, up to the ridge
        z = top + r * 0.8 + k * sp_; half = LY / 2 + 0.1 - (z - top) / math.tan(pitch)
        if half < 0.35:
            break
        for sx in (-1, 1):
            log((sx * LX / 2, -half, z), (sx * LX / 2, half, z), 1, seed=200 + k * 3 + (sx > 0))
        k += 1
    ridge_z = top + (LY / 2 + 0.1) * math.tan(pitch) + 0.12; sm = shingle_mat(pitch, ridge_z) if hi else None; eave = 0.55; run = LY / 2 + eave; sl = run / math.cos(pitch)
    for sy in (-1, 1):                                            # roof slabs: built flat, pitched about the ridge line
        o = L.box('roof', (-LX / 2 - 0.5, 0.0 if sy > 0 else -sl, -0.09), (LX / 2 + 0.5, sl if sy > 0 else 0.0, 0.0), c, hi, bevel=0.01, warp=0.006, seed=5 + sy)
        L.xform(o, Matrix.Translation((0, 0, ridge_z)) @ Matrix.Rotation(-pitch if sy > 0 else pitch, 4, 'X'))
        if hi:
            o.data.materials.append(sm)
        parts.append(o)
    rc = L.sweep('ridge', [(-LX / 2 - 0.55, 0, ridge_z + 0.02, 0.09, 0.07, 2.2), (0, 0, ridge_z + 0.03, 0.09, 0.07, 2.2), (LX / 2 + 0.55, 0, ridge_z + 0.02, 0.09, 0.07, 2.2)], nu=8 * q if hi else 6, nv=8 * q if hi else 5, c=c, up=(0, 0, 1), cap=0.8)
    if hi:
        rc.data.materials.append(lm[0])
    parts.append(rc)
    for nm, pl in (('purlin_s', -1), ('purlin_n', 1)):            # eaves purlins under the roof edge
        log((-LX / 2 - 0.45, pl * (LY / 2 + 0.02), top + 0.05), (LX / 2 + 0.45, pl * (LY / 2 + 0.02), top + 0.05), 0, rad=0.1, seed=300 + pl)
    st = [P3.stone(110 + i, tint=(0.62 + 0.05 * i, 0.58, 0.50), value=0.8, sat=0.5, moss=0.4, lichen=0.4, scan='rock_boulder_dry', scale=1.6) for i in range(3)] if hi else [None] * 3; cx = -LX / 2 - 0.62; H = ridge_z + 0.9; crs = 0.3; k = 0
    while k * crs < H:                                            # fieldstone chimney: battered stack against the west gable, three stones to a course
        z0 = k * crs; t_ = z0 / H; wy = 1.5 * (1 - 0.55 * smoothstep(0.25, 0.6, t_)); wx = 0.82 * (1 - 0.3 * smoothstep(0.25, 0.6, t_)); ys = np.linspace(-wy / 2, wy / 2, 4) if k % 2 == 0 else np.r_[-wy / 2, np.linspace(-wy / 6, wy / 6, 2), wy / 2]
        for i in range(len(ys) - 1):
            P3.blocks(parts, 'stone', (cx - wx / 2 + rng.uniform(-0.015, 0.015), ys[i] + 0.006, z0), (cx + wx / 2 + rng.uniform(-0.015, 0.015), ys[i + 1] - 0.006, z0 + crs - 0.012), c, hi, st[(k + i) % 3], seed=400 + k * 4 + i, bevel=0.03, warp=0.012)
        k += 1
    P3.blocks(parts, 'cap', (cx - 0.36, -0.42, H), (cx + 0.36, 0.42, H + 0.1), c, hi, st[0], seed=500, bevel=0.02)
    fl = L.box('floor', (-LX / 2 + 0.05, -LY / 2 + 0.05, 0.0), (LX / 2 - 0.05, LY / 2 - 0.05, 0.06), c, hi, bevel=0.01, warp=0.0, seed=600)
    dk = L.box('dark', (-LX / 2 + 0.1, -LY / 2 + 0.16, 0.06), (LX / 2 - 0.1, LY / 2 - 0.16, top - 0.05), c, hi, bevel=0.01, warp=0.0, seed=601)       # a dark core so the openings do not show the far wall or the sky
    if hi:
        d = NT('dark'); d.set(base=(0.006, 0.005, 0.005), rough=1.0); dk.data.materials.append(d.mat); fl.data.materials.append(T.wood_mat('floor', axis=0, light=(0.12, 0.07, 0.03), dark=(0.04, 0.022, 0.01)))
    parts += [fl, dk]; return parts


# ---------------------------------------------------------------------------------------------- church
def _dark():
    d = NT('dark'); d.set(base=(0.006, 0.005, 0.005), rough=1.0); return d.mat


def church(hi, c):
    """stone church, 19 m long: buttressed nave of four bays with lancets, a lower chancel, a round apse, slate roofs, a bell turret with a spire over the west gable"""
    import build_doors as D
    parts = []; cutters = []; TH = 0.7; NX0, NX1, NH, WH = -8.0, 6.0, 4.0, 6.5; pitch = math.radians(50); CX1, CH, CWH, CT = 10.5, 3.0, 4.5, 0.6
    st = ashlar_mat('ashlar', seed=1.0) if hi else None; st2 = ashlar_mat('ashlar_dark', tint=(0.28, 0.31, 0.38), seed=4.0) if hi else None; apm = ashlar_mat('ashlar_round', round_at=(CX1, 0.0, 3.0), seed=7.0) if hi else None
    slate = shingle_mat(pitch, 0, course=0.3, width=0.32, cols=SLATE, name='slate', moss_amt=0.3, lift=0.02) if hi else None; glass = D.glass_mat('leaded', z0=0.0) if hi else None; dark = _dark() if hi else None

    def wall(mn, mx, mat, cuts=()):
        o = L.box('wall', mn, mx, c, hi, bevel=0.02, warp=0.006, seed=len(parts))
        if cuts:
            cut(o, cuts)
        if hi:
            L.assign(o, mat)                       # a boolean leaves an empty slot: assign, do not append
        parts.append(o); return o

    def pane(w, spring, sill, at, yaw=0.0):
        out = [(x, z + sill) for x, z in L.arch_outline(w + 0.04, spring, 'pointed', n=10)]; o = L.prism('pane', out, -0.02, 0.02, c, hi, bevel=0.002); L.xform(o, Matrix.Translation(at) @ Matrix.Rotation(yaw, 4, 'Z'))
        if hi:
            o.data.materials.append(glass)
        parts.append(o)
    bays = [-6.25, -2.75, 0.75, 4.25]; door = opening(c, 1.6, 2.3, 'round', 1.6, (NX0, 0, 0), yaw=math.pi / 2); wwin = opening(c, 1.1, 1.5, 'pointed', 1.6, (NX0, 0, 0), yaw=math.pi / 2, sill=5.2); cutters += [door, wwin]
    for sy in (-1, 1):
        ws = [opening(c, 0.8, 2.0, 'pointed', 1.6, (x, sy * NH, 0), sill=2.4) for x in bays]; cutters += ws; wall((NX0, sy * NH - TH / 2, 0), (NX1, sy * NH + TH / 2, WH), st, ws)
        for x in bays:
            pane(0.8, 2.0, 2.4, (x, sy * NH, 0))
        cw = opening(c, 0.7, 1.5, 'pointed', 1.6, ((NX1 + CX1) / 2, sy * CH, 0), sill=1.9); cutters.append(cw); wall((NX1, sy * CH - CT / 2, 0), (CX1, sy * CH + CT / 2, CWH), st, [cw]); pane(0.7, 1.5, 1.9, ((NX1 + CX1) / 2, sy * CH, 0))
        for k, x in enumerate((NX0 + 0.35, -4.5, -1.0, 2.5, NX1 - 0.35)):             # two-stage buttresses with weathered offsets
            y0 = sy * (NH + TH / 2)
            for (pr, z0, z1) in ((0.95, 0.0, 3.4), (0.55, 3.4, 5.5)):
                wall((x - 0.36, min(y0, y0 + sy * pr), z0), (x + 0.36, max(y0, y0 + sy * pr), z1), st2)
                o = L.box('offset', (x - 0.4, min(y0, y0 + sy * (pr + 0.08)), z1 + 0.28 - 0.08), (x + 0.4, max(y0, y0 + sy * (pr + 0.08)), z1 + 0.28), c, hi, bevel=0.012, warp=0.003, seed=k, rot=('X', -sy * math.radians(34), (x, y0, z1 + 0.28)))
                if hi:
                    o.data.materials.append(st2)
                parts.append(o)
    wall((NX0 - TH / 2, -NH - TH / 2, 0), (NX0 + TH / 2, NH + TH / 2, WH), st, [door, wwin]); wall((NX1 - TH / 2, -NH - TH / 2, 0), (NX1 + TH / 2, NH + TH / 2, WH), st)
    gable(parts, c, hi, NX0, TH, NH + TH / 2, WH, pitch, st, [wwin]); gable(parts, c, hi, NX1, TH, NH + TH / 2, WH, pitch, st); pane(1.1, 1.5, 5.2, (NX0, 0, 0), yaw=math.pi / 2)
    ridge = WH + (NH + TH / 2) * math.tan(pitch) + 0.2; roof_pair(parts, c, hi, NX0 - 0.35, NX1 + 0.25, NH + TH / 2, ridge, pitch, slate, eave=0.45, seed=1)
    cridge = CWH + (CH + CT / 2) * math.tan(pitch) + 0.2; wall((CX1 - CT / 2, -CH - CT / 2, 0), (CX1 + CT / 2, CH + CT / 2, CWH), st); gable(parts, c, hi, CX1, CT, CH + CT / 2, CWH, pitch, st)
    roof_pair(parts, c, hi, NX1 + 0.2, CX1 + 0.3, CH + CT / 2, cridge, pitch, slate, eave=0.4, seed=5)
    seg = 64 if hi else 20; ap = L.lathe('apse', [(0, 0), (3.0, 0), (3.0, 4.0), (0, 4.0)], seg=seg, c=c); L.xform(ap, Matrix.Translation((CX1, 0, 0)))
    cone = L.lathe('apse_roof', [(0, 3.98), (3.38, 3.98), (3.4, 4.08), (0, 6.9)], seg=seg, c=c); L.xform(cone, Matrix.Translation((CX1, 0, 0)))
    if hi:
        ap.data.materials.append(apm); cone.data.materials.append(shingle_mat(math.atan2(2.82, 3.4), 6.9, course=0.3, width=0.3, mode='cone', apex=(CX1, 0.0), cols=SLATE, name='slate_cone', moss_amt=0.3, lift=0.02))
    parts += [ap, cone]
    tx = NX0 + 0.85; tz = ridge - 1.3; wall((tx - 0.75, -0.75, tz), (tx + 0.75, 0.75, tz + 2.9), st2)                                        # bell turret astride the west gable
    for sy in (-1, 1):
        lo_ = L.box('louvre', (tx - 0.3, sy * 0.76 - 0.02, tz + 1.5), (tx + 0.3, sy * 0.76 + 0.02, tz + 2.5), c, hi, bevel=0.004, seed=3)
        if hi:
            lo_.data.materials.append(dark)
        parts.append(lo_)
    sz = tz + 2.9; sp_ = L.lathe('spire', [(0, sz), (1.2, sz), (1.2, sz + 0.08), (0, sz + 4.4)], seg=4, c=c); L.xform(sp_, Matrix.Translation((tx, 0, 0)) @ Matrix.Rotation(math.pi / 4, 4, 'Z'))
    if hi:
        sp_.data.materials.append(shingle_mat(math.atan2(4.32, 0.85), sz + 4.4, course=0.3, width=0.24, mode='pyramid', apex=(tx, 0.0), cols=SLATE, name='slate_spire', moss_amt=0.2, lift=0.02))
    parts.append(sp_); im = T.iron_mat('iron', rust=0.7, seed=3.0) if hi else None
    for mn, mx in (((tx - 0.02, -0.02, sz + 4.3), (tx + 0.02, 0.02, sz + 5.2)), ((tx - 0.02, -0.22, sz + 4.8), (tx + 0.02, 0.22, sz + 4.86))):
        o = L.box('cross', mn, mx, c, hi, bevel=0.006, seed=9)
        if hi:
            o.data.materials.append(im)
        parts.append(o)
    for mn, mx in (((NX0 + 0.45, -NH + 0.45, 0.02), (NX1 - 0.4, NH - 0.45, WH - 0.2)), ((NX1 - 0.2, -CH + 0.4, 0.02), (CX1 - 0.4, CH - 0.4, CWH - 0.2))):          # dark cores behind the lights and the door
        o = L.box('core', mn, mx, c, hi, bevel=0.01, seed=11)
        if hi:
            o.data.materials.append(dark)
        parts.append(o)
    for k in cutters:
        bpy.data.objects.remove(k)
    return parts


# ---------------------------------------------------------------------------------------------- snow house (three stacking parts)
def _frame_kit(c, hi, parts, light=(0.045, 0.027, 0.013), dark=(0.014, 0.009, 0.005)):
    wm = [T.wood_mat('timber_%s' % 'xyz'[a], axis=a, light=light, dark=dark) for a in range(3)] if hi else [None] * 3

    def beam(mn, mx, yaw=0.0, rot=None, axis=None):
        o = L.box('beam', mn, mx, c, hi, bevel=0.012, warp=0.004, seed=len(parts), rot=rot)
        if yaw:
            L.xform(o, Matrix.Rotation(yaw, 4, 'Z'))
        if hi:
            Pq = L.co(o); d = Pq.max(0) - Pq.min(0); o.data.materials.append(wm[int(np.argmax(d)) if axis is None else axis])
        parts.append(o); return o
    return beam, wm


def _panel(c, hi, parts, mn, mx, mat, yaw=0.0, bevel=0.004):
    o = L.box('panel', mn, mx, c, hi, bevel=bevel, warp=0.0, seed=len(parts))
    if yaw:
        L.xform(o, Matrix.Rotation(yaw, 4, 'Z'))
    if hi:
        o.data.materials.append(mat)
    parts.append(o); return o


def snow_lower(hi, c):
    """ground storey of the house, 10 x 10 m and 3 m high: dark timber frame on a stone sill, plastered panels, bands of leaded windows, two doorways with stone steps"""
    import build_doors as D
    parts = []; S, H = 5.0, 3.0; beam, wm = _frame_kit(c, hi, parts); pl = plaster_mat('plaster', col=((0.22, 0.20, 0.15), (0.34, 0.31, 0.24)), seed=2.0) if hi else None; glass = D.glass_mat('leaded', z0=0.0) if hi else None; dark = _dark() if hi else None
    stn = P3.stone(120, tint=(0.62, 0.60, 0.54), value=0.85, sat=0.4, moss=0.4, scan='rock_boulder_dry', scale=1.4) if hi else None
    _panel(c, hi, parts, (-S + 0.07, -S + 0.07, 0.0), (S - 0.07, S - 0.07, H), pl, bevel=0.01)
    for k in range(4):
        yaw = k * math.pi / 2; front = k in (0, 1)
        beam((-S - 0.04, -S - 0.04, 0.0), (S + 0.04, -S + 0.2, 0.24), yaw); beam((-S - 0.06, -S - 0.06, H - 0.26), (S + 0.06, -S + 0.2, H), yaw); beam((-S, -S - 0.01, 1.02), (S, -S + 0.16, 1.18), yaw)
        for x in (-S + 0.13, -2.5, 0.0, 2.5, S - 0.13):
            beam((x - 0.13, -S - 0.03, 0.24), (x + 0.13, -S + 0.2, H - 0.26), yaw)
        for (x0, x1) in (((-2.5, 0.0), (0.0, 2.5)) if front else ((-2.5, 0.0),)):                   # leaded lights with two mullions
            _panel(c, hi, parts, (x0 + 0.2, -S - 0.004, 1.3), (x1 - 0.2, -S + 0.06, 2.45), glass, yaw); beam((x0 + 0.13, -S - 0.02, 1.22), (x1 - 0.13, -S + 0.1, 1.3), yaw); beam((x0 + 0.13, -S - 0.02, 2.45), (x1 - 0.13, -S + 0.1, 2.53), yaw)
            for xm in (x0 + (x1 - x0) / 3, x0 + 2 * (x1 - x0) / 3):
                beam((xm - 0.03, -S - 0.02, 1.3), (xm + 0.03, -S + 0.08, 2.45), yaw)
        if front:                                                                                # doorway in the right-hand bay, two stone steps
            _panel(c, hi, parts, (3.0, -S - 0.006, 0.24), (4.3, -S + 0.07, 2.3), dark, yaw); beam((2.9, -S - 0.03, 2.3), (4.4, -S + 0.12, 2.42), yaw)
            _panel(c, hi, parts, (2.7, -S - 0.75, 0.0), (4.6, -S - 0.04, 0.12), stn, yaw, bevel=0.02); _panel(c, hi, parts, (2.85, -S - 0.42, 0.12), (4.45, -S - 0.04, 0.24), stn, yaw, bevel=0.02)
    return parts


def snow_timber(hi, c):
    """jettied upper storey, 10.6 x 10.6 m and 2.8 m high: close timber frame with straight and curved braces over cream plaster, joist ends showing under the jetty, small leaded windows"""
    import build_doors as D
    parts = []; S, H = 5.3, 2.8; beam, wm = _frame_kit(c, hi, parts); pl = plaster_mat('plaster', col=((0.34, 0.30, 0.22), (0.48, 0.44, 0.34)), seed=5.0) if hi else None; glass = D.glass_mat('leaded', z0=0.0) if hi else None
    _panel(c, hi, parts, (-S + 0.07, -S + 0.07, 0.0), (S - 0.07, S - 0.07, H), pl, bevel=0.01); xs = np.linspace(-S + 0.12, S - 0.12, 7)
    for k in range(4):
        yaw = k * math.pi / 2
        for x in np.arange(-S + 0.3, S - 0.2, 0.62):                                               # joist ends under the jetty
            beam((x - 0.07, -S - 0.07, 0.0), (x + 0.07, -S + 0.25, 0.17), yaw, axis=1 if k % 2 == 0 else 0)
        beam((-S - 0.05, -S - 0.05, 0.17), (S + 0.05, -S + 0.2, 0.4), yaw); beam((-S - 0.06, -S - 0.06, H - 0.24), (S + 0.06, -S + 0.2, H), yaw); beam((-S, -S - 0.01, 1.35), (S, -S + 0.16, 1.5), yaw)
        for x in xs:
            beam((x - 0.11, -S - 0.03, 0.4), (x + 0.11, -S + 0.2, H - 0.24), yaw)
        for i in (0, 5):                                                                         # straight braces in the end bays
            xa, xb = xs[i], xs[i + 1]; sgn = 1 if i == 0 else -1; ln = math.hypot(xb - xa - 0.22, 0.95); ang = math.atan2(0.95, (xb - xa - 0.22)) * sgn
            o = beam((0, -S - 0.015, -0.055), (ln, -S + 0.15, 0.055), rot=('Y', -ang, (0, 0, 0)), axis=0); L.xform(o, Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Translation(((xa + 0.11) if sgn > 0 else (xb - 0.11) - ln * math.cos(ang), 0, 0.4 if sgn > 0 else 0.4 + 0.95)))
        for i in (2, 3):                                                                         # curved braces in the middle bays, rising to the top plate
            xa, xb = xs[i], xs[i + 1]; sgn = 1 if i == 2 else -1; x0 = xa + 0.11 if sgn > 0 else xb - 0.11; x1 = xb - 0.11 if sgn > 0 else xa + 0.11
            rows = [(x0 + (x1 - x0) * t_, -S + 0.065, 1.5 + (H - 0.24 - 1.5) * (1 - (1 - t_) ** 2.2), 0.05, 0.08, 8) for t_ in np.linspace(0, 1, 6)]
            o = L.sweep('brace', rows, nu=8, nv=24 if hi else 8, c=c, up=(0, 1, 0), cap=0.9); L.xform(o, Matrix.Rotation(yaw, 4, 'Z'))
            if hi:
                o.data.materials.append(wm[2])
            parts.append(o)
        for i in ((1, 4) if k in (0, 1) else (1,)):
            xa, xb = xs[i], xs[i + 1]; _panel(c, hi, parts, (xa + 0.16, -S - 0.004, 1.55), (xb - 0.16, -S + 0.06, 2.4), glass, yaw); beam(((xa + xb) / 2 - 0.03, -S - 0.02, 1.5), ((xa + xb) / 2 + 0.03, -S + 0.08, 2.45), yaw)
    return parts


def snow_roof(hi, c):
    """pyramid roof, 11.8 m square and 4.3 m tall: heavy stone slates in diminishing courses, four hip rolls, a ball finial"""
    parts = []; Hh = 5.9; apex = 4.3; R = Hh * math.sqrt(2); pitch = math.atan2(apex - 0.16, Hh)
    ro = L.lathe('roof', [(0, 0), (R, 0), (R, 0.16), (0, apex)], seg=4, c=c); L.xform(ro, Matrix.Rotation(math.pi / 4, 4, 'Z')); ro.data.polygons.foreach_set('use_smooth', [False] * len(ro.data.polygons))
    stn = P3.stone(130, tint=(0.60, 0.60, 0.54), value=0.85, sat=0.35, moss=0.5, scan='rock_boulder_dry', scale=1.5) if hi else None
    if hi:
        ro.data.materials.append(shingle_mat(pitch, apex, course=0.42, width=0.62, mode='pyramid', cols=STONE_SLAB, name='stone_slates', moss_amt=0.6, lift=0.03))
    parts.append(ro)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; o = L.sweep('hip', [(R * math.cos(a) * 0.99, R * math.sin(a) * 0.99, 0.2, 0.09, 0.07, 2.4), (R * math.cos(a) * 0.5, R * math.sin(a) * 0.5, 0.2 + (apex - 0.16) * 0.5, 0.085, 0.065, 2.4), (0.0, 0.0, apex + 0.03, 0.08, 0.06, 2.4)],
                                                nu=8, nv=30 if hi else 6, c=c, up=(0, 0, 1), cap=0.8)
        if hi:
            o.data.materials.append(stn)
        parts.append(o)
    f = C.ball('finial', (0, 0, apex + 0.2), 0.18, c, seg=24 if hi else 10)
    if hi:
        f.data.materials.append(stn)
    parts.append(f); return parts


# ---------------------------------------------------------------------------------------------- castle drawbridge
def drawbridge(hi, c):
    """castle gate with its drawbridge down: a 5.2 m length of curtain wall with a round-arched gateway and merlons, a 2.8 x 4.7 m plank bridge, two chains from the wall to its outer corners"""
    parts = []; st = ashlar_mat('ashlar', tint=(0.38, 0.38, 0.40), seed=3.0, bw=0.7, rh=0.35) if hi else None; dark = _dark() if hi else None; im = T.iron_mat('chain', rust=0.6, seed=7.0) if hi else None
    op = opening(c, 2.6, 2.5, 'round', 3.0, (0, 0, 0)); w = L.box('wall', (-2.6, -0.6, 0), (2.6, 0.6, 5.2), c, hi, bevel=0.02, warp=0.006, seed=1); cut(w, [op]); bpy.data.objects.remove(op)
    if hi:
        L.assign(w, st)
    parts.append(w)
    for x in (-2.15, -0.72, 0.72, 2.15):
        o = L.box('merlon', (x - 0.45, -0.6, 5.2), (x + 0.45, 0.6, 6.0), c, hi, bevel=0.02, warp=0.005, seed=int(x * 10) + 30)
        if hi:
            o.data.materials.append(st)
        parts.append(o)
    bk = L.box('gate_dark', (-1.4, 0.4, 0.0), (1.4, 0.58, 3.9), c, hi, bevel=0.01, seed=5)
    if hi:
        bk.data.materials.append(dark)
    parts.append(bk); wm = [T.wood_mat('deck_%s' % 'xyz'[a], axis=a, light=(0.19, 0.11, 0.05), dark=(0.065, 0.035, 0.016)) for a in range(3)] if hi else [None] * 3
    for k in range(9):
        x0 = -1.4 + k * 0.311; o = L.box('plank', (x0, -5.3, 0.14), (x0 + 0.3, -0.62, 0.23), c, hi, bevel=0.008, warp=0.004, seed=40 + k)
        if hi:
            o.data.materials.append(wm[1])
        parts.append(o)
    for y in (-4.9, -3.0, -1.1):
        o = L.box('bearer', (-1.45, y - 0.09, 0.0), (1.45, y + 0.09, 0.14), c, hi, bevel=0.01, warp=0.004, seed=int(-y * 10))
        if hi:
            o.data.materials.append(wm[0])
        parts.append(o)
    from mathutils import Vector
    for sx in (-1, 1):
        a = Vector((sx * 1.15, -0.63, 4.4)); b = Vector((sx * 1.32, -5.0, 0.3)); d = (b - a); n = int(d.length / 0.2); dn = d.normalized(); rot = dn.to_track_quat('X', 'Z').to_matrix().to_4x4()
        for k in range(n + 1):
            p = a + d * (k / n); o = L.ring('link', 0.062, 0.016, c, seg=14 if hi else 6, sides=6 if hi else 3)
            L.xform(o, Matrix.Translation(p) @ rot @ Matrix.Rotation((k % 2) * math.pi / 2, 4, 'X') @ Matrix.Diagonal((1.6, 1.0, 1.0, 1.0)))
            if hi:
                o.data.materials.append(im)
            parts.append(o)
        for p in (a, b):
            o = C.ball('staple', tuple(p), 0.07, c, seg=12 if hi else 6)
            if hi:
                o.data.materials.append(im)
            parts.append(o)
    return parts


W_B = ' One 4096 px bake covers the whole building, about 100 px/m: it holds at the gameplay camera and is soft at 1 m (a tiling masonry material with trim would be the engine-side answer). Walls are flat slabs with the coursing in the textures; the inside is a dark core, not a room. One convex hull is exported.'

SPECS = {
    'Log_Cabin': dict(fn=log_cabin, fam='log_cabin', seq='59 struct/cabin/cabin- frame 1', cls='building', px=4096, tris=0, lo='param', ground='forrest_ground_01', third=['rock_boulder_dry'], extrude=0.02, maxdist=0.06, collision=True,
                      shot=dict(az=38, el=16, fill=1.0, close=(0.2, 0.0, 0.3, 0.2)),
                      weak='The corner notches are not cut: logs of one wall simply pass over those of the next with their ends proud, and the gaps between courses are closed by overlap rather than by chinking. '
                           'The roof is two flat slabs with the shingles in the textures (no shingle silhouette at the eaves, no rafters or sagging); the inside is a dark core, not a room. Chimney stones are bevelled blocks. '
                           'Door and window openings are empty: the leaf and the light are the log_cabin_door and log_cabin_window assets. One convex hull is exported.',
                      dresses='log cabin, 7.6 x 4.8 m and 5.4 m to the ridge: ten courses of weathered logs with proud ends, log gables, a mossy shingle roof at 38 degrees, a battered fieldstone chimney on the west gable, door and window openings in the south wall',
                      extra={'openings_m': {'door': {'wall': 'south (y = -2.1)', 'x': [-1.9, -0.9], 'height': 2.0}, 'window': {'wall': 'south (y = -2.1)', 'x': [1.2, 2.2], 'z': [0.95, 1.75]}}}),
}
SPECS.update({
    'Church': dict(fn=church, fam='church', seq='60 struct/church/chrch- frame 1', cls='building', px=4096, tris=0, lo='param', ground='forrest_ground_01', third=['rock_face_03', 'rusty_metal_02'], extrude=0.03, maxdist=0.09, collision=True,
                   shot=dict(az=38, el=16, fill=1.0, close=(0.15, 0.0, 0.3, 0.16)),
                   weak='Lancets are plain pointed openings with dark leaded panes: no tracery, hood moulds or stained glass (the stained-glass assets can stand in them). Buttresses are two plain stages; there is no plinth course, string course, corbel table or porch, and the west door opening is empty for the church_door leaf.' + W_B,
                   dresses='stone church, 19.5 m long and 17 m to the spire cross: buttressed nave of four bays with lancet windows, lower chancel, round apse with a conical roof, slate roofs at 50 degrees, a bell turret with a slated spire over the west gable',
                   extra={'openings_m': {'west door': {'x': -8.0, 'width': 1.6, 'height_to_crown': 3.1}}}),
    'Snow_House_Lower': dict(fn=snow_lower, fam='snow_house_lower', seq='96 struct/building/build- frame 1', cls='building', px=4096, tris=0, lo='param', ground='forrest_ground_01', third=['rock_boulder_dry'], extrude=0.02, maxdist=0.06, collision=True,
                             shot=dict(az=45, el=14, fill=1.0, close=(0.8, 0.0, 0.4, 0.2)),
                             weak='A box of plaster with the frame laid on it: timbers are bevelled blocks without joints or pegs, windows are opaque dark leaded panels, doorways are dark recesses (the snow_house_door asset goes in front). It has no top: it is meant to carry the timbered storey.' + W_B,
                             dresses='ground storey of the snow-country house, 10 x 10 m and 3 m high: dark timber frame, grey plaster panels, bands of leaded windows, two doorways with stone steps',
                             extra={'stacking': 'SM_Snow_House_Timber_PR sits on top at z = 3.0 m; SM_Snow_House_Roof_PR at z = 5.8 m; all three share the same centre'}),
    'Snow_House_Timber': dict(fn=snow_timber, fam='snow_house_timber', seq='96 struct/building/build- frame 2', cls='building', px=4096, tris=0, lo='param', ground='forrest_ground_01', third=[], extrude=0.02, maxdist=0.06, collision=True,
                              shot=dict(az=45, el=14, fill=1.0, close=(0.6, 0.0, 0.5, 0.2)),
                              weak='Braces are laid on the plaster rather than framed into the posts; the curved braces are swept bars of even section. Opaque window panels. Rendered standing on the ground; in use it sits on the lower storey.' + W_B,
                              dresses='jettied upper storey, 10.6 x 10.6 m and 2.8 m high: close-studded dark timber frame with straight and curved braces over cream plaster, joist ends under the jetty, small leaded windows',
                              extra={'stacking': 'place at z = 3.0 m on SM_Snow_House_Lower_PR'}),
    'Snow_House_Roof': dict(fn=snow_roof, fam='snow_house_roof', seq='96 struct/building/build- frame 3', cls='building', px=4096, tris=0, lo='param', ground='forrest_ground_01', third=['rock_boulder_dry'], extrude=0.03, maxdist=0.08, collision=True,
                            shot=dict(az=45, el=20, fill=1.0, close=(0.7, 0.2, 0.3, 0.2)),
                            weak='Four flat faces with the stone slates in the textures: no slate edges on the silhouette, no sag, no snow (the family name is the house, not the weather). Hip rolls are plain swept bars. Rendered on the ground; in use it sits on the timbered storey.' + W_B,
                            dresses='pyramid roof, 11.8 m square and 4.3 m tall, in heavy mossy stone slates with four hip rolls and a ball finial',
                            extra={'stacking': 'place at z = 5.8 m on SM_Snow_House_Timber_PR'}),
    'Castle_Drawbridge': dict(fn=drawbridge, fam='castle_drawbridge', seq='68 struct/castle/cdoor- frame 6', cls='prop_large', px=4096, tris=0, lo='param', ground='forrest_ground_01', third=['rock_face_03', 'rusty_metal_02'], extrude=0.012, maxdist=0.04,
                              shot=dict(az=32, el=16, fill=1.0, close=(0.7, 0.2, 0.3, 0.2)),
                              weak='The bridge is fixed down: no pivot, no rig, and the chains are straight runs of links without sag. The gate passage is a dark slab 1 m in; the wall is a 5.2 m sample of curtain wall whose coursing is in the textures, not the castle kit. One convex hull covers wall and bridge.',
                              dresses='castle gate with the drawbridge down: 5.2 m of crenellated curtain wall with a round-arched gateway, a 2.8 x 4.7 m oak plank bridge on three bearers, two iron chains to its outer corners'),
})
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
