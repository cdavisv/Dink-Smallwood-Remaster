"""More small props of the unclaimed families: food (421 items/food: ham leg, braided loaf, cheese, grapes, steak),
long farm tools (447 items/tools: pitchfork, rake, scythe) and the island spear (424 struct/island).

    tools/bl.sh build_props2.py <name,name|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
import build_fruit as F
import build_props as P
from pplib import NT, smoothstep, fbm
from mathutils import Matrix

SCRIPT = 'build_props2.py'


# ---------------------------------------------------------------------------------------------- food
def ham(hi, c):
    """cured ham leg, 42 cm: smoked rind with net marks, a flat cut face (lean, fat ring, bone), the shank bone standing out of the narrow end"""
    q = 4 if hi else 1; z = 0.085
    body = L.sweep('ham', [(-0.135, 0, z, 0.088, 0.078, 2.3), (-0.12, 0, z, 0.098, 0.084, 2.2), (-0.04, 0, z, 0.105, 0.085, 2.1), (0.05, 0, z * 0.92, 0.082, 0.07, 2.1), (0.13, 0, z * 0.8, 0.05, 0.045, 2.1), (0.185, 0, z * 0.72, 0.03, 0.028, 2.1)],
                   nu=20 * q, nv=20 * q, c=c, up=(0, 0, 1), cap=0.93)
    bone = L.sweep('bone', [(0.16, 0, z * 0.74, 0.014, 0.013, 2), (0.23, 0, z * 0.66, 0.012, 0.011, 2), (0.275, 0, z * 0.62, 0.017, 0.014, 2.2), (0.29, 0, z * 0.61, 0.019, 0.015, 2.2)], nu=10 * q, nv=8 * q, c=c, up=(0, 0, 1), cap=0.6)
    if hi:
        P_ = L.co(body); N = L.vnormals(body); face = smoothstep(-0.6, -0.9, N[:, 0]); L.set_co(body, P_ + N * ((0.0025 * fbm(P_, 3, 16, 3) + 0.001 * fbm(P_, 5, 70, 2)) * (1 - face))[:, None]); C.set_attr(body, 'face', face)
        t = NT('ham'); f = t.attr('face'); sp = t.sep(t.obj); rr = t.vmath('LENGTH', t.comb(0.0, sp[1], t.math('SUBTRACT', sp[2], z))); n = t.noise(40, 4, 0.6); n2 = t.noise(220, 3, 0.6)
        rind = t.ramp(t.noise(9, 5, 0.65), [(0.3, (0.060, 0.022, 0.008)), (0.6, (0.17, 0.065, 0.02)), (0.85, (0.30, 0.13, 0.04))]); net = t.voronoi(42, feature='DISTANCE_TO_EDGE'); netl = t.ramp(net, [(0.0, 1.0), (0.06, 0.0)])
        rind = t.mix(t.math('MULTIPLY', netl, 0.55), rind, (0.035, 0.014, 0.006))
        seam = t.ramp(t.voronoi(55, feature='DISTANCE_TO_EDGE', vec=t.mapping(scale=(0.2, 1, 1))), [(0.0, 1.0), (0.07, 0.0)])
        lean = t.mix(n, (0.30, 0.045, 0.045), (0.52, 0.12, 0.11)); lean = t.mix(t.math('MULTIPLY', seam, 0.7), lean, (0.72, 0.60, 0.50))
        fat = t.mix(n2, (0.70, 0.62, 0.48), (0.86, 0.80, 0.68)); meat = t.mix(t.maprange(t.math('ADD', rr, t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.012)), 0.058, 0.066, 0.0, 1.0), lean, fat)
        meat = t.mix(t.maprange(rr, 0.076, 0.08, 0.0, 1.0), meat, (0.20, 0.08, 0.03)); meat = t.mix(t.maprange(rr, 0.017, 0.014, 0.0, 1.0), meat, (0.74, 0.68, 0.55)); meat = t.mix(t.maprange(rr, 0.008, 0.006, 0.0, 1.0), meat, (0.30, 0.10, 0.07))
        t.set(base=t.mix(f, rind, meat), rough=t.mixf(f, t.mixf(n, 0.3, 0.5), t.mixf(n2, 0.28, 0.42)), normal=t.bump(t.math('ADD', t.math('MULTIPLY', netl, -1.0), t.math('MULTIPLY', n2, 0.3)), 0.35, 0.002), sss=0.15, sss_scale=0.01)
        body.data.materials.append(t.mat)
        b = NT('bone'); bn = b.noise(60, 4, 0.6); b.set(base=b.mix(bn, (0.50, 0.44, 0.32), (0.76, 0.72, 0.60)), rough=b.mixf(bn, 0.4, 0.6), normal=b.bump(b.noise(300, 2, 0.5), 0.2, 0.0005)); bone.data.materials.append(b.mat)
    return [body, bone]


def loaf(hi, c):
    """braided loaf, 36 cm: three strands plaited, glazed dark on the crests, pale and floury in the creases"""
    q = 4 if hi else 1; strands = []
    for k in range(3):
        rows = []
        for i in range(13):
            t_ = i / 12; x = -0.17 + 0.34 * t_; ph = 2 * np.pi * (t_ * 2.3 + k / 3); env = np.sin(np.pi * t_) ** 0.5; r = 0.012 + 0.024 * env
            rows.append((x, 0.036 * np.sin(ph) * env, 0.03 + 0.014 * np.cos(2 * ph) * env + 0.006 * env, r * 1.05, r * 0.9, 2.0))
        strands.append(L.sweep('strand%d' % k, rows, nu=12 * q, nv=30 * q, c=c, up=(0, 0, 1), cap=0.5))
    if hi:
        t = NT('crust'); nz = t.sep(t.gnormal)[2]; z = t.sep(t.obj)[2]; n = t.noise(30, 5, 0.65); n2 = t.noise(260, 3, 0.6); ao = t.ao(0.02, 12); top = t.math('MULTIPLY', t.maprange(nz, 0.0, 0.8, 0.0, 1.0), t.ramp(ao, [(0.5, 0.0), (0.9, 1.0)]))
        base = t.mix(top, t.mix(n, (0.50, 0.33, 0.13), (0.68, 0.50, 0.24)), t.mix(n, (0.20, 0.075, 0.018), (0.40, 0.18, 0.045))); flour = t.math('MULTIPLY', t.ramp(t.noise(18, 4, 0.7), [(0.55, 0.0), (0.7, 1.0)]), t.ramp(ao, [(0.4, 1.0), (0.85, 0.2)]))
        base = t.mix(t.math('MULTIPLY', flour, 0.55), base, (0.72, 0.66, 0.54)); crack = t.ramp(t.voronoi(60, feature='DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.035, 0.0)]); base = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', crack, top), 0.5), base, (0.62, 0.45, 0.2))
        t.set(base=base, rough=t.mixf(top, 0.75, t.mixf(n, 0.28, 0.45)), normal=t.bump(t.math('ADD', t.math('MULTIPLY', n2, 0.5), t.math('MULTIPLY', crack, -0.6)), 0.3, 0.001), sss=0.08, sss_scale=0.005)
        for o in strands:
            L.displace_np(o, lambda Q: 0.0015 * fbm(Q, 3, 30, 3)); o.data.materials.append(t.mat)
    return strands


def cheese(hi, c):
    """small cheese wheel, 19 cm, with a wedge cut out: waxed orange-yellow rind, paler paste with eyes on the cut faces"""
    seg = 96 if hi else 28; wheel = L.lathe('wheel', [(0, 0), (0.08, 0), (0.092, 0.006), (0.096, 0.03), (0.094, 0.058), (0.084, 0.072), (0.04, 0.078), (0, 0.079)], seg=seg, c=c)
    if hi:
        L.subsurf(wheel, 2)
    cut = L.new_obj('cut', [(0, 0, -0.05), (0.2, -0.045, -0.05), (0.2, 0.11, -0.05), (0, 0, 0.2), (0.2, -0.045, 0.2), (0.2, 0.11, 0.2)], [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)], c, smooth=False); L.fix_normals(cut)
    m = wheel.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cut; m.solver = 'EXACT'; L.apply_mods(wheel); bpy.data.objects.remove(cut)
    wheel.data.polygons.foreach_set('use_smooth', [True] * len(wheel.data.polygons))
    try:
        wheel.data.set_sharp_from_angle(angle=math.radians(40))
    except Exception:
        pass
    if hi:
        t = NT('cheese'); sp = t.sep(t.obj); ang = t.math('ARCTAN2', sp[1], sp[0]); rr = t.vmath('LENGTH', t.comb(sp[0], sp[1], 0.0)); n = t.noise(30, 4, 0.6); n2 = t.noise(200, 3, 0.6)
        inside = t.math('MULTIPLY', t.math('MULTIPLY', t.maprange(ang, -0.2215, -0.20, 0.0, 1.0), t.maprange(ang, 0.4827, 0.50, 1.0, 0.0)), 1.0)                # between the two cut planes: paste
        inside = t.math('MULTIPLY', inside, t.math('MULTIPLY', t.maprange(rr, 0.089, 0.093, 1.0, 0.0), t.math('MULTIPLY', t.maprange(sp[2], 0.004, 0.007, 0.0, 1.0), t.maprange(sp[2], 0.072, 0.069, 0.0, 1.0))))
        eyes = t.ramp(t.voronoi(55, feature='F1'), [(0.0, 1.0), (0.2, 0.0)]); paste = t.mix(n, (0.62, 0.42, 0.12), (0.80, 0.60, 0.24)); paste = t.mix(t.math('MULTIPLY', eyes, 0.6), paste, (0.30, 0.17, 0.04))
        rind = t.mix(n, (0.50, 0.24, 0.035), (0.72, 0.42, 0.08)); rind = t.mix(t.ramp(t.noise(12, 4, 0.7), [(0.6, 0.0), (0.72, 0.6)]), rind, (0.62, 0.56, 0.42)); cloth = t.math('SINE', t.math('MULTIPLY', sp[2], 2400.0))
        t.set(base=t.mix(inside, rind, paste), rough=t.mixf(inside, t.mixf(n, 0.3, 0.5), t.mixf(n2, 0.4, 0.55)), normal=t.bump(t.math('ADD', t.math('MULTIPLY', t.math('MULTIPLY', eyes, inside), -3.0), t.math('MULTIPLY', t.math('MULTIPLY', cloth, t.math('SUBTRACT', 1.0, inside)), 0.25)), 0.4, 0.001),
              sss=0.12, sss_scale=0.008); wheel.data.materials.append(t.mat)
    return [wheel]


def grapes(hi, c):
    """bunch of about seventy dark grapes on a branched stalk with one vine leaf, 20 cm, lying on its side"""
    rng = np.random.default_rng(4); obs = []; pts = []
    for k in range(400):
        t_ = rng.uniform(0, 1); rad = 0.042 * (1 - t_) ** 0.7 + 0.006; a = rng.uniform(0, 6.28); p = np.array([-0.02 + 0.15 * t_, rad * math.cos(a), 0.02 + rad * 0.75 * abs(math.sin(a)) * 1.3]); r = rng.uniform(0.0085, 0.0105)
        if all(np.linalg.norm(p - q) > (r + r2) * 0.92 for q, r2 in pts):
            pts.append((p, r))
        if len(pts) >= 72:
            break
    for i, (p, r) in enumerate(pts):
        o = L.icosphere('grape%d' % i, r, 3 if hi else 1, c, scale=(1.12, 1, 1)); o.rotation_euler = tuple(rng.uniform(0, 6.28, 3)); o.location = tuple(p + np.array([0, 0, max(0, r - p[2])])); L.apply_xf(o); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons)); obs.append(o)
    stalk = L.sweep('stalk', [(-0.085, 0.004, 0.035, 0.0036, 0.0036, 2), (-0.06, 0.0, 0.032, 0.0034, 0.0034, 2), (-0.03, -0.002, 0.03, 0.004, 0.004, 2), (0.03, 0, 0.028, 0.0035, 0.0035, 2), (0.09, 0, 0.022, 0.0025, 0.0025, 2)], nu=8 if hi else 5, nv=30 if hi else 8, c=c, up=(0, 0, 1), cap=0.7)
    lf = F.leaf('leaf', hi, (-0.078, 0.004, 0.036), 0.085, 0.085, yaw=math.radians(105), droop=0.5, curl=0.1, c=c, seed=3, pitch=0.12)
    if hi:
        t = NT('grape'); n = t.noise(70, 4, 0.6); bl = t.ramp(t.noise(28, 4, 0.65, vec=t.mapping(loc=(3, 1, 2))), [(0.35, 0.0), (0.7, 1.0)]); cv = t.sep(t.voronoi(60, out='Color'))
        base = t.mix(n, (0.016, 0.006, 0.03), (0.07, 0.016, 0.085)); base = t.mix(t.math('MULTIPLY', bl, 0.45), base, (0.30, 0.30, 0.42)); t.set(base=base, rough=t.math('ADD', t.mixf(n, 0.12, 0.25), t.math('MULTIPLY', bl, 0.3)), sss=0.2, sss_radius=(0.6, 0.1, 0.5), sss_scale=0.004)
        for o in obs:
            o.data.materials.append(t.mat)
        stalk.data.materials.append(F.stem_mat('stalk', green=(0.10, 0.11, 0.035), woody=0.5)); lf.data.materials.append(F.leaf_mat('leaf', col=(0.045, 0.085, 0.02)))
    return obs + [stalk, lf]


def steak(hi, c):
    """raw T-bone steak, 26 cm, 2.5 cm thick: marbled red lean, a rim of fat, the bone through the middle"""
    q = 4 if hi else 1; h = 0.0125
    o = L.sweep('steak', [(-0.13, 0.0, h, 0.045, h, 3.2), (-0.10, 0.004, h, 0.078, h, 3.4), (-0.03, 0.008, h, 0.094, h, 3.4), (0.04, 0.0, h, 0.085, h, 3.4), (0.10, -0.012, h, 0.058, h, 3.4), (0.135, -0.02, h, 0.028, h, 3.2)], nu=24 * q, nv=20 * q, c=c, up=(0, 0, 1), cap=0.75)
    if hi:
        L.displace_np(o, lambda Q: 0.0008 * fbm(Q, 3, 40, 3))
        t = NT('steak'); sp = t.sep(t.obj); n = t.noise(24, 5, 0.65); n2 = t.noise(180, 3, 0.6); ao = t.ao(0.01, 6)
        marb = t.ramp(t.noise(1.0, 5, 0.75, vec=t.mapping(scale=(60, 22, 60)), distortion=1.5), [(0.56, 0.0), (0.62, 1.0)]); lean = t.mix(n, (0.28, 0.022, 0.03), (0.50, 0.06, 0.07)); lean = t.mix(t.math('MULTIPLY', marb, 0.8), lean, (0.78, 0.66, 0.58))
        edge = t.ramp(t.pointiness, [(0.50, 0.0), (0.54, 1.0)]); rim = t.maprange(t.math('ADD', sp[1], t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.03)), 0.045, 0.062, 0.0, 1.0); fat = t.mix(n2, (0.72, 0.62, 0.50), (0.88, 0.82, 0.72)); base = t.mix(rim, lean, fat)
        bone = t.math('MAXIMUM', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', sp[0], 0.012)), [(0.008, 1.0), (0.011, 0.0)]), t.math('MULTIPLY', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', sp[1], 0.03)), [(0.007, 1.0), (0.01, 0.0)]), t.maprange(sp[0], -0.05, -0.04, 0.0, 1.0)))
        bone = t.math('MULTIPLY', t.math('MULTIPLY', bone, t.maprange(sp[1], -0.05, -0.04, 0.0, 1.0)), t.maprange(sp[0], 0.075, 0.065, 0.0, 1.0)); base = t.mix(bone, base, t.mix(n2, (0.62, 0.55, 0.42), (0.80, 0.76, 0.64)))
        t.set(base=base, rough=t.mixf(bone, t.mixf(n, 0.16, 0.34), 0.5), normal=t.bump(t.math('ADD', t.math('MULTIPLY', marb, 0.4), t.math('MULTIPLY', bone, 1.2)), 0.25, 0.0008), sss=0.2, sss_radius=(1.0, 0.2, 0.15), sss_scale=0.006, coat=0.3, coat_rough=0.15)
        o.data.materials.append(t.mat)
    return [o]


# ---------------------------------------------------------------------------------------------- long tools (lying flat, working end towards +X)
def _mats(hi, parts, grip=None, dark=None, iron_kw=None):
    if not hi:
        return
    w = T.wood_mat('ash', axis=0, grip=grip, dark_from=dark); ir = T.iron_mat('iron', **(iron_kw or dict(rust=0.5, seed=2.0)))
    for o, k in parts:
        o.data.materials.append(w if k == 'w' else ir)
        L.displace_np(o, (lambda Q: 0.0003 * fbm(Q, 5, 70, 3)) if k == 'i' else (lambda Q: 0.0002 * fbm(Q * np.array([0.1, 1, 1]), 7, 160, 2)))


def pitchfork(hi, c):
    """hay fork, 1.75 m: ash shaft, forged socket and three curved tines"""
    q = 4 if hi else 1; z = 0.017; parts = [(L.sweep('shaft', [(-0.86, 0, z, 0.016, 0.016, 2.1), (-0.5, 0.004, z, 0.0165, 0.0165, 2.1), (0.2, -0.003, z, 0.017, 0.017, 2.1), (0.54, 0, z, 0.0155, 0.0155, 2.1)], nu=10 * q, nv=24 * q, c=c, up=(0, 0, 1), cap=0.7), 'w'),
                                            (L.sweep('socket', [(0.44, 0, z, 0.0185, 0.0185, 2.2), (0.52, 0, z, 0.0175, 0.0175, 2.4), (0.58, 0, z, 0.016, 0.013, 3)], nu=10 * q, nv=6 * q, c=c, up=(0, 0, 1), cap=0.8), 'i')]
    for k, dy in enumerate((-0.075, 0.0, 0.075)):
        parts.append((L.sweep('tine%d' % k, [(0.57, dy * 0.15, z, 0.007, 0.006, 3), (0.61, dy * 0.75, z - 0.004, 0.007, 0.006, 3), (0.66, dy, z - 0.008, 0.0062, 0.0058, 2.4), (0.78, dy, z - 0.005, 0.0052, 0.0052, 2.2), (0.88, dy * 0.96, z + 0.012, 0.0022, 0.0022, 2.0)],
                              nu=8 * q, nv=14 * q, c=c, up=(0, 0, 1), cap=0.3), 'i'))
    _mats(hi, parts, grip=(-0.8, -0.2), dark=(0.36, 0.46)); return [o for o, k in parts]


def rake(hi, c):
    """wooden hay rake, 1.75 m: ash shaft split into a bow at the head, a 62 cm head with fourteen pegged teeth"""
    q = 4 if hi else 1; hz = 0.105; parts = [(L.sweep('shaft', [(-0.9, 0, 0.017, 0.015, 0.015, 2.1), (-0.3, 0, 0.045, 0.0155, 0.0155, 2.1), (0.4, 0, 0.078, 0.0155, 0.0155, 2.1), (0.82, 0, 0.1, 0.014, 0.014, 2.1)], nu=10 * q, nv=24 * q, c=c, up=(0, 0, 1), cap=0.7), 'w'),
                                             (L.sweep('head', [(0.83, -0.31, hz, 0.019, 0.015, 3.5), (0.83, -0.1, hz, 0.02, 0.016, 3.5), (0.83, 0.1, hz, 0.02, 0.016, 3.5), (0.83, 0.31, hz, 0.019, 0.015, 3.5)], nu=10 * q, nv=12 * q, c=c, up=(0, 0, 1), cap=0.85), 'w')]
    for sy in (-1, 1):
        parts.append((L.sweep('bow%d' % sy, [(0.38, sy * 0.012, 0.079, 0.006, 0.006, 2), (0.6, sy * 0.1, 0.09, 0.006, 0.006, 2), (0.815, sy * 0.2, 0.103, 0.006, 0.006, 2)], nu=8 * q, nv=10 * q, c=c, up=(0, 0, 1), cap=0.6), 'w'))
    for k in range(14):
        y = -0.285 + k * 0.57 / 13; parts.append((L.sweep('tooth%d' % k, [(0.83, y, hz + 0.014, 0.0062, 0.0062, 2.2), (0.83, y, hz - 0.03, 0.006, 0.006, 2.2), (0.832, y, 0.0, 0.0035, 0.0035, 2.2)], nu=6 * q, nv=5 * q, c=c, up=(1, 0, 0), cap=0.5), 'w'))
    _mats(hi, parts, grip=(-0.85, -0.2)); return [o for o, k in parts]


def scythe(hi, c):
    """scythe, 1.6 m snath with two grips and a 75 cm forged blade"""
    q = 4 if hi else 1; z = 0.018
    parts = [(L.sweep('snath', [(-0.8, 0.02, z, 0.0165, 0.0165, 2.1), (-0.4, -0.03, z, 0.017, 0.017, 2.1), (0.1, 0.03, z, 0.0175, 0.0175, 2.1), (0.5, 0.0, z, 0.0175, 0.0175, 2.2), (0.72, -0.02, z, 0.017, 0.016, 2.4)], nu=10 * q, nv=24 * q, c=c, up=(0, 0, 1), cap=0.7), 'w'),
             (L.sweep('grip1', [(-0.42, -0.03, z, 0.013, 0.013, 2), (-0.43, 0.04, z + 0.02, 0.012, 0.012, 2), (-0.44, 0.13, z + 0.03, 0.014, 0.014, 2)], nu=8 * q, nv=8 * q, c=c, up=(0, 0, 1), cap=0.6), 'w'),
             (L.sweep('grip2', [(0.05, 0.03, z, 0.013, 0.013, 2), (0.05, -0.04, z + 0.02, 0.012, 0.012, 2), (0.05, -0.12, z + 0.03, 0.014, 0.014, 2)], nu=8 * q, nv=8 * q, c=c, up=(0, 0, 1), cap=0.6), 'w'),
             (L.sweep('ring', [(0.66, -0.016, z, 0.021, 0.021, 2.4), (0.69, -0.018, z, 0.0215, 0.0215, 2.4), (0.72, -0.02, z, 0.021, 0.021, 2.4)], nu=10 * q, nv=4 * q, c=c, up=(0, 0, 1), cap=0.9), 'i'),
             (L.sweep('blade', [(0.70, -0.03, 0.006, 0.02, 0.004, 3.5), (0.72, 0.08, 0.006, 0.036, 0.0032, 3.2), (0.68, 0.30, 0.006, 0.042, 0.0028, 3.0), (0.56, 0.52, 0.006, 0.034, 0.0022, 3.0), (0.38, 0.68, 0.006, 0.02, 0.0016, 3.0), (0.22, 0.74, 0.006, 0.003, 0.001, 2.5)],
                      nu=12 * q, nv=24 * q, c=c, up=(0, 0, 1), cap=0.3), 'i')]
    _mats(hi, parts, grip=(-0.8, 0.1), iron_kw=dict(rust=0.45, seed=6.0)); return [o for o, k in parts]


def spear(hi, c):
    """island spear standing in the ground, 2.25 m: pole, leaf blade bound on with cord, a strip of red cloth under the head"""
    q = 4 if hi else 1; parts = [(L.sweep('pole', [(0.004, 0, -0.12, 0.014, 0.014, 2.1), (0, 0.004, 0.6, 0.0155, 0.0155, 2.1), (-0.004, 0, 1.4, 0.0145, 0.0145, 2.1), (0, 0, 1.95, 0.0125, 0.0125, 2.1)], nu=10 * q, nv=26 * q, c=c, up=(0, 1, 0), cap=0.7), 'w'),
                                (L.sweep('blade', [(0, 0, 1.86, 0.011, 0.007, 2.6), (0, 0, 1.93, 0.014, 0.006, 2.8), (0, 0, 1.99, 0.034, 0.005, 3), (0, 0, 2.08, 0.026, 0.004, 3), (0, 0, 2.2, 0.002, 0.001, 2.5)], nu=12 * q, nv=14 * q, c=c, up=(0, 1, 0), cap=0.3), 'i'),
                                (L.sweep('lash', [(0, 0, 1.80, 0.0145, 0.0145, 2.1), (0, 0, 1.86, 0.016, 0.0155, 2.1), (0, 0, 1.93, 0.016, 0.014, 2.2)], nu=10 * q, nv=10 * q, c=c, up=(0, 1, 0), cap=0.9), 'c'),
                                (L.sweep('rag', [(0.012, 0, 1.79, 0.004, 0.02, 3), (0.03, 0.004, 1.72, 0.003, 0.026, 3), (0.036, -0.004, 1.62, 0.0025, 0.03, 3), (0.03, 0.006, 1.52, 0.002, 0.018, 3)], nu=10 * q, nv=14 * q, c=c, up=(0, 1, 0), cap=0.5), 'r')]
    if hi:
        w = T.wood_mat('pole', axis=2, grip=(0.8, 1.5), light=(0.30, 0.20, 0.10), dark=(0.11, 0.065, 0.03)); ir = T.iron_mat('iron', polish=(2, 2.0, 2.2), rust=0.5, seed=8.0)
        cd = NT('cord'); sp = cd.sep(cd.obj); cd.set(base=cd.mix(cd.noise(700, 2, 0.5), (0.10, 0.075, 0.04), (0.30, 0.23, 0.13)), rough=0.88, normal=cd.bump(cd.math('SINE', cd.math('MULTIPLY', sp[2], 1500.0)), 0.9, 0.001))
        rg = NT('rag'); n = rg.noise(40, 4, 0.6); wv = rg.math('MULTIPLY', rg.math('SINE', rg.math('MULTIPLY', rg.sep(rg.obj)[2], 3000.0)), rg.math('SINE', rg.math('MULTIPLY', rg.sep(rg.obj)[1], 3000.0)))
        rg.set(base=rg.mix(n, (0.16, 0.012, 0.01), (0.42, 0.045, 0.03)), rough=0.85, normal=rg.bump(wv, 0.4, 0.0004), sheen=0.3)
        for o, k in parts:
            o.data.materials.append({'w': w, 'i': ir, 'c': cd.mat, 'r': rg.mat}[k])
            if k in 'wi':
                L.displace_np(o, lambda Q: 0.0003 * fbm(Q, 5, 60, 3))
    return [o for o, k in parts]


W_TOOL = ' Parts are separate swept solids pushed together (no modelled sockets, rivets, wedges or pegs). Wood grain is procedural streaking along the object axis. Authored lying flat; the original frames show it leaning against a wall, which is a placement rotation.'
SH_LONG = dict(az=22, el=30, fill=1.0, close=(0.88, 0.5, 0.5, 0.16))
SPECS = {
    'Ham_Leg': dict(fn=ham, fam='food_drumstick', seq='421 items/food/food- frames 1, 2', cls='prop_small', px=1024, tris=1300, ground='weathered_brown_planks', third=[],
                    weak='The cut face is a painted pattern on a flat cap (rings by radius): no fibre direction, no moist sheen difference between lean and fat. Rind net marks are a Voronoi grid. No subsurface in the game material, which meat needs.',
                    dresses='cured ham leg, 42 cm: smoked brown rind with net marks, a cut face with lean, fat ring and bone, shank bone at the narrow end (the frame the audit calls a drumstick)'),
    'Bread_Braided': dict(fn=loaf, fam='food_bread', seq='421 items/food/food- frame 7', cls='prop_small', px=1024, tris=1500, ground='weathered_brown_planks', third=[],
                          weak='Three strands plaited as swept tubes: they do not flatten against each other or the board as dough does, and the ends are simply tapered rather than pinched. Crust blistering and flour are procedural.',
                          dresses='braided loaf, 36 cm, three strands, dark glazed crests and floury creases'),
    'Cheese_Wheel': dict(fn=cheese, fam='food_cheese', seq='421 items/food/food- frame 9', cls='prop_small', px=1024, tris=900, lo='param', ground='weathered_brown_planks', third=[], extrude=0.002, maxdist=0.006,
                         weak='The original frame is a plain yellow dome; a wheel with a wedge cut out was chosen to make it read as cheese. Paste eyes are a Voronoi dot pattern in the normal map, not holes. The rind is clean: no mould bloom or cloth seam beyond a faint weave.',
                         dresses='small cheese wheel, 19 cm, orange-yellow rind, one wedge cut out showing paler paste with eyes'),
    'Grapes': dict(fn=grapes, fam='food_grapes', seq='421 items/food/food- frame 14', cls='prop_small', px=1024, tris=2600, lo='remesh', voxel=0.0022, ground='weathered_brown_planks', third=[], extrude=0.003, maxdist=0.008,
                   weak='The game mesh is one skin over the whole bunch (2,600 triangles), so gaps between grapes are shallow and carried by the normal map; grapes do not have individual stalks. No subsurface or transmission in the game material: backlit grapes will look opaque.',
                   dresses='bunch of about seventy dark purple grapes with bloom, on a stalk with one vine leaf, 22 cm'),
    'Steak_TBone': dict(fn=steak, fam='food_ham', seq='421 items/food/food- frame 3', cls='prop_small', px=1024, tris=900, ground='weathered_brown_planks', third=[],
                        weak='A slab with a painted cut: bone, fat rim and marbling are colour and normal only and identical on both faces. The outline is smooth.', dresses='raw T-bone steak, 27 cm, marbled lean with a fat rim and the bone through it (the frame the audit calls ham / steak)'),
    'Pitchfork': dict(fn=pitchfork, fam='pitchfork', seq='447 items/tools/tool- frames 1, 11', cls='prop', px=1024, tris=1500, ground='forrest_ground_01', third=['rusty_metal_02'], collision=False, extrude=0.0015, maxdist=0.005, shot=SH_LONG,
                      weak='Tines are smooth round sweeps without forge facets.' + W_TOOL + ' A 1.75 m object in a 1024 px set: about 1.5 px per mm on the shaft.', dresses='hay fork, 1.75 m: ash shaft, forged socket, three curved tines'),
    'Rake': dict(fn=rake, fam='rake', seq='447 items/tools/tool- frames 3, 13', cls='prop', px=1024, tris=2400, ground='forrest_ground_01', third=[], collision=False, extrude=0.0015, maxdist=0.005, shot=SH_LONG,
                 weak='Teeth are identical tapered pegs.' + W_TOOL, dresses='wooden hay rake, 1.75 m: ash shaft with a split bow, 62 cm head, fourteen pegged teeth'),
    'Scythe': dict(fn=scythe, fam='scythe', seq='447 items/tools/tool- frame 12', cls='prop', px=1024, tris=1700, ground='forrest_ground_01', third=['rusty_metal_02'], collision=False, extrude=0.0015, maxdist=0.005, shot=dict(az=22, el=34, fill=0.95, close=(0.8, 0.6, 0.5, 0.2)),
                   weak='The blade is a flat tapered sweep: no rib along its back, no tang, and the edge is not ground to a bevel. The original frame is closer to a long-handled hook; a scythe was built.' + W_TOOL,
                   dresses='scythe, 1.6 m snath with two grips, iron ring and a 75 cm curved blade'),
    'Spear_Island': dict(fn=spear, fam='island_spear_pole', seq='424 struct/island/isle- frames 13, 16, 17', cls='prop', px=1024, tris=1300, ground='forrest_ground_01', third=['rusty_metal_02'], collision=False, extrude=0.0015, maxdist=0.005, keep_z=True,
                         shot=dict(az=30, el=10, fill=1.2, close=(0.5, 0.5, 0.88, 0.14)),
                         weak='The cloth strip is a stiff swept ribbon, not simulated cloth. Lashing is a sleeve with a cord pattern in the normal map. The pole is straight and evenly round. Stands upright with 12 cm below ground for planting.',
                         dresses='island spear planted upright, 2.2 m above ground: wooden pole, forged leaf head bound with cord, a strip of red cloth under the head',
                         extra={'pivot': 'ground level on the pole axis (z = 0); the pole continues 12 cm below for planting'}),
}
for k_, v_ in SPECS.items():
    v_['script'] = SCRIPT
P.SPECS.update(SPECS)

if __name__ == '__main__':
    a = L.args(); names = list(SPECS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for n in names:
        P.build(n, mode)
