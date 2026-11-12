"""npc_knight_blue (281-289 people/knight/blue), npc_knight_red (271-279), npc_knight_silver (291-299): a guard in full
plate with a halberd. One mesh, three base-colour sets.

Every armour piece is its own swept solid and belongs to exactly one bone of the project humanoid skeleton
(CONVENTIONS.md section 11), so the skinning is rigid, as plate is.

    tools/bl.sh build_knight.py [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
from pplib import NT, fbm

SCRIPT = 'build_knight.py'
UP = (0, 1, 0)
J = {'pelvis': (0, 0, 1.00), 'spine_01': (0, 0, 1.08), 'spine_02': (0, 0, 1.17), 'spine_03': (0, 0, 1.27), 'spine_04': (0, 0, 1.37), 'spine_05': (0, 0, 1.45), 'neck_01': (0, 0, 1.53), 'neck_02': (0, 0, 1.58),
     'head': (0, 0, 1.63), 'head_top': (0, 0, 1.84)}
for s, sx in (('l', 1), ('r', -1)):
    J.update({'clav_' + s: (0.03 * sx, 0, 1.48), 'shoulder_' + s: (0.205 * sx, 0, 1.47), 'elbow_' + s: (0.275 * sx, 0.015, 1.18), 'wrist_' + s: (0.315 * sx, -0.05, 0.93), 'hand_end_' + s: (0.325 * sx, -0.075, 0.82),
              'hip_' + s: (0.105 * sx, 0, 0.97), 'knee_' + s: (0.125 * sx, -0.015, 0.53), 'ankle_' + s: (0.125 * sx, 0.02, 0.095), 'ball_' + s: (0.13 * sx, -0.12, 0.03), 'toe_' + s: (0.135 * sx, -0.235, 0.025)})
BONES = [('root', (0, 0, 0), (0, 0.1, 0), None), ('pelvis', 'pelvis', 'spine_01', 'root')] + [('spine_%02d' % i, 'spine_%02d' % i, 'spine_%02d' % (i + 1) if i < 5 else 'neck_01', 'pelvis' if i == 1 else 'spine_%02d' % (i - 1)) for i in range(1, 6)] + \
        [('neck_01', 'neck_01', 'neck_02', 'spine_05'), ('neck_02', 'neck_02', 'head', 'neck_01'), ('head', 'head', 'head_top', 'neck_02')]
for s in 'lr':
    BONES += [('clavicle_' + s, 'clav_' + s, 'shoulder_' + s, 'spine_05'), ('upperarm_' + s, 'shoulder_' + s, 'elbow_' + s, 'clavicle_' + s), ('lowerarm_' + s, 'elbow_' + s, 'wrist_' + s, 'upperarm_' + s),
              ('hand_' + s, 'wrist_' + s, 'hand_end_' + s, 'lowerarm_' + s), ('thigh_' + s, 'hip_' + s, 'knee_' + s, 'pelvis'), ('calf_' + s, 'knee_' + s, 'ankle_' + s, 'thigh_' + s),
              ('foot_' + s, 'ankle_' + s, 'ball_' + s, 'calf_' + s), ('ball_' + s, 'ball_' + s, 'toe_' + s, 'foot_' + s)]


def steel_mat(name, slit=False, seed=0.0):
    """blued and painted plate: deep blue coat worn to bare steel on edges and high spots, scratches, grime and rust in the laps"""
    t = NT(name); n1 = t.noise(9, 5, 0.65, vec=t.mapping(loc=(seed, 0, 0))); n2 = t.noise(70, 4, 0.6); n3 = t.noise(260, 3, 0.6)
    coat = t.ramp(n1, [(0.25, (0.012, 0.030, 0.105)), (0.55, (0.022, 0.055, 0.175)), (0.85, (0.040, 0.085, 0.235))])
    scr = t.noise(3.0, 3, 0.6, vec=t.mapping(scale=(8, 8, 190), rot=(0.4, 0.2, seed))); scr2 = t.noise(3.0, 3, 0.6, vec=t.mapping(scale=(170, 9, 9), rot=(0.1, 0.5, 0.3)))
    wear = t.math('MULTIPLY', t.ramp(t.pointiness, [(0.505, 0.0), (0.56, 1.0)]), t.ramp(n2, [(0.25, 0.3), (0.7, 1.0)]))
    wear = t.math('MAXIMUM', wear, t.math('MULTIPLY', t.ramp(t.math('MAXIMUM', scr, scr2), [(0.70, 0.0), (0.76, 1.0)]), 0.8))
    wear = t.math('MAXIMUM', wear, t.ramp(t.noise(5, 4, 0.7, vec=t.mapping(loc=(0, seed, 4))), [(0.62, 0.0), (0.74, 0.7)]))        # patches rubbed through
    steel = t.mix(n3, (0.30, 0.31, 0.33), (0.56, 0.57, 0.58)); base = t.mix(wear, coat, steel)
    ao = t.ao(0.03, 12); grime = t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.85, 0.0)]), t.ramp(n2, [(0.2, 0.5), (0.8, 1.0)])); base = t.mix(t.math('MULTIPLY', grime, 0.85), base, (0.020, 0.016, 0.012))
    rust = t.math('MULTIPLY', t.ramp(t.noise(26, 5, 0.7, vec=t.mapping(loc=(3, 1, seed))), [(0.66, 0.0), (0.74, 1.0)]), t.ramp(ao, [(0.5, 1.0), (0.98, 0.25)])); base = t.mix(t.math('MULTIPLY', rust, 0.8), base, t.mix(n3, (0.09, 0.035, 0.012), (0.22, 0.09, 0.03)))
    metal = t.mixf(rust, t.mixf(grime, t.mixf(wear, 0.75, 1.0), 0.2), 0.0); rough = t.mixf(wear, t.mixf(n2, 0.30, 0.46), t.mixf(n3, 0.22, 0.36)); rough = t.mixf(grime, rough, 0.8); rough = t.mixf(rust, rough, 0.85)
    h = t.math('ADD', t.math('MULTIPLY', t.noise(28, 3, 0.5), 0.5), t.math('MULTIPLY', t.math('MAXIMUM', scr, scr2), -0.25))
    if slit:
        sp = t.sep(t.obj); m = t.math('MULTIPLY', t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', sp[2], 1.713)), [(0.0065, 1.0), (0.0085, 0.0)]), t.maprange(sp[1], -0.075, -0.085, 0.0, 1.0))
        m = t.math('MULTIPLY', m, t.ramp(t.math('ABSOLUTE', sp[0]), [(0.012, 0.0), (0.018, 1.0)])); base = t.mix(m, base, (0.004, 0.004, 0.004)); metal = t.mixf(m, metal, 0.0); rough = t.mixf(m, rough, 1.0)
        h = t.math('ADD', h, t.math('MULTIPLY', m, -6.0))
        br = t.math('MULTIPLY', t.ramp(t.voronoi(95, feature='F1', vec=t.comb(sp[0], sp[2], 0.0)), [(0.18, 1.0), (0.26, 0.0)]), t.math('MULTIPLY', t.maprange(sp[2], 1.60, 1.62, 0.0, 1.0), t.maprange(sp[2], 1.665, 1.685, 1.0, 0.0)))
        br = t.math('MULTIPLY', br, t.maprange(sp[1], -0.07, -0.09, 0.0, 1.0)); base = t.mix(br, base, (0.004, 0.004, 0.004)); metal = t.mixf(br, metal, 0.0); rough = t.mixf(br, rough, 1.0)      # breaths
    t.set(base=base, rough=rough, metal=metal, normal=t.bump(h, 0.12, 0.002)); return t.mat


def mail_mat():
    t = NT('mail'); sp = t.sep(t.obj); ang = t.math('ARCTAN2', sp[1], sp[0]); v = t.comb(t.math('MULTIPLY', ang, 30.0), t.math('MULTIPLY', sp[2], 190.0), 0.0)
    ring = t.voronoi(1.0, vec=v, feature='DISTANCE_TO_EDGE'); r = t.ramp(ring, [(0.0, 0.0), (0.2, 1.0)]); n = t.noise(40, 3, 0.6)
    base = t.mix(r, (0.006, 0.006, 0.007), t.mix(n, (0.10, 0.10, 0.11), (0.30, 0.30, 0.31))); rust = t.ramp(t.noise(15, 4, 0.7), [(0.6, 0.0), (0.72, 1.0)]); base = t.mix(t.math('MULTIPLY', rust, 0.7), base, (0.11, 0.045, 0.016))
    t.set(base=base, rough=t.mixf(r, 0.9, t.mixf(n, 0.32, 0.5)), metal=t.mixf(rust, t.mixf(r, 0.2, 0.95), 0.1), normal=t.bump(r, 0.9, 0.003)); return t.mat


def leather_mat():
    t = NT('leather'); n = t.noise(60, 4, 0.6); cr = t.voronoi(220, feature='DISTANCE_TO_EDGE'); base = t.mix(n, (0.035, 0.018, 0.009), (0.11, 0.058, 0.026)); base = t.mix(t.ramp(cr, [(0.0, 0.6), (0.08, 0.0)]), base, (0.012, 0.007, 0.004))
    t.set(base=base, rough=t.mixf(n, 0.45, 0.7), normal=t.bump(t.ramp(cr, [(0.0, 0.0), (0.12, 1.0)]), 0.4, 0.001)); return t.mat


def limb(name, p0, p1, r0, r1, c, q, mid=1.0, n=2.2, flare0=1.0, flare1=1.0, flat=1.0):
    """tube of plate round a limb: thicker in the middle by `mid`, flared lips by flare0/flare1; flat squashes front to back"""
    p0 = np.array(p0, float); p1 = np.array(p1, float); rows = []
    for k, (t, f) in enumerate(((0.0, flare0), (0.07, 1.0), (0.5, mid), (0.93, 1.0), (1.0, flare1))):
        p = p0 * (1 - t) + p1 * t; r = (r0 * (1 - t) + r1 * t) * f; rows.append((p[0], p[1], p[2], r, r * flat, n))
    return L.sweep(name, rows, nu=12 * q, nv=10 * q, c=c, up=UP, cap=0.75)


def build(q, c):
    """returns [(object, bone, material key)]"""
    P = []; a = P.append
    # ---- head: sallet with a pointed visor and a bevor
    a((L.sweep('helm', [(0, 0.005, 1.585, 0.098, 0.112, 2.3), (0, 0.004, 1.63, 0.105, 0.122, 2.3), (0, 0.0, 1.70, 0.108, 0.128, 2.2), (0, 0.004, 1.775, 0.098, 0.118, 2.1), (0, 0.008, 1.825, 0.066, 0.082, 2.0), (0, 0.01, 1.848, 0.022, 0.03, 2.0)],
               nu=20 * q, nv=14 * q, c=c, up=UP, cap=0.5), 'head', 'helm'))
    a((L.sweep('visor', [(0, -0.058, 1.608, 0.066, 0.046, 2.1), (0, -0.088, 1.65, 0.078, 0.058, 2.0), (0, -0.112, 1.695, 0.068, 0.056, 2.0), (0, -0.094, 1.74, 0.08, 0.050, 2.0), (0, -0.066, 1.775, 0.072, 0.040, 2.1)],
               nu=16 * q, nv=10 * q, c=c, up=UP, cap=0.6), 'head', 'helm'))
    a((L.sweep('crest', [(0, 0.115, 1.68, 0.005, 0.012, 3), (0, 0.085, 1.80, 0.006, 0.016, 3), (0, 0.01, 1.855, 0.006, 0.016, 3), (0, -0.07, 1.80, 0.005, 0.012, 3)], nu=8 * q, nv=12 * q, c=c, up=(1, 0, 0), cap=0.4), 'head', 'steel'))
    a((L.sweep('bevor', [(0, -0.01, 1.50, 0.105, 0.105, 2.4), (0, -0.018, 1.545, 0.092, 0.10, 2.4), (0, -0.03, 1.60, 0.086, 0.098, 2.4), (0, -0.034, 1.625, 0.09, 0.10, 2.4)], nu=16 * q, nv=8 * q, c=c, up=UP, cap=0.85), 'neck_01', 'steel'))
    # ---- trunk: globose breastplate, backplate in one, waist lames, mail skirt, belt
    a((L.sweep('cuirass', [(0, 0.0, 1.085, 0.150, 0.118, 2.5), (0, -0.004, 1.13, 0.146, 0.116, 2.4), (0, -0.022, 1.26, 0.192, 0.150, 2.3), (0, -0.026, 1.36, 0.205, 0.158, 2.3), (0, -0.012, 1.44, 0.185, 0.132, 2.4), (0, -0.002, 1.50, 0.13, 0.105, 2.4)],
               nu=24 * q, nv=16 * q, c=c, up=UP, cap=0.8), 'spine_03', 'steel'))
    for k, (z0, z1, w0, w1) in enumerate(((1.035, 1.10, 0.168, 0.155), (0.985, 1.05, 0.182, 0.168), (0.935, 1.0, 0.196, 0.182))):
        a((L.sweep('fauld%d' % k, [(0, 0, z0, w0, w0 * 0.80, 2.4), (0, 0, (z0 + z1) / 2, (w0 + w1) / 2 + 0.004, (w0 + w1) / 2 * 0.80, 2.4), (0, 0, z1, w1, w1 * 0.80, 2.4)], nu=24 * q, nv=5 * q, c=c, up=UP, cap=0.9), 'pelvis', 'steel'))
    a((L.sweep('skirt', [(0, 0, 0.80, 0.205, 0.165, 2.3), (0, 0, 0.88, 0.196, 0.158, 2.3), (0, 0, 0.96, 0.184, 0.148, 2.3)], nu=24 * q, nv=6 * q, c=c, up=UP, cap=0.9), 'pelvis', 'mail'))
    a((L.sweep('belt', [(0, 0, 1.062, 0.160, 0.128, 2.5), (0, 0, 1.08, 0.162, 0.130, 2.5), (0, 0, 1.098, 0.160, 0.128, 2.5)], nu=24 * q, nv=4 * q, c=c, up=UP, cap=0.92), 'spine_01', 'leather'))
    a((L.sweep('buckle', [(0, -0.133, 1.058, 0.022, 0.006, 5), (0, -0.136, 1.08, 0.024, 0.007, 5), (0, -0.133, 1.102, 0.022, 0.006, 5)], nu=10 * q, nv=4 * q, c=c, up=UP, cap=0.8), 'spine_01', 'steel'))
    for s, sx in (('l', 1), ('r', -1)):
        sh = np.array(J['shoulder_' + s]); el = np.array(J['elbow_' + s]); wr = np.array(J['wrist_' + s]); he = np.array(J['hand_end_' + s])
        hp = np.array(J['hip_' + s]); kn = np.array(J['knee_' + s]); an = np.array(J['ankle_' + s]); bl = np.array(J['ball_' + s]); toe = np.array(J['toe_' + s])
        # pauldron: three lames lapping down over the shoulder
        for k, (dx, dz, w, hgt) in enumerate(((-0.035, 0.030, 0.076, 0.052), (0.008, 0.010, 0.084, 0.058), (0.042, -0.028, 0.078, 0.054))):
            cx = sh[0] + dx * sx; a((L.sweep('pauldron_%s%d' % (s, k), [(cx - 0.062 * sx, 0, sh[2] + dz + 0.012, w * 0.75, hgt * 0.8, 2.3), (cx, 0, sh[2] + dz + 0.02, w, hgt, 2.2), (cx + 0.058 * sx, 0, sh[2] + dz - 0.03, w * 0.9, hgt * 0.95, 2.2),
                                                                      (cx + 0.074 * sx, 0, sh[2] + dz - 0.075, w * 0.72, hgt * 0.7, 2.3)], nu=14 * q, nv=8 * q, c=c, up=(0, 0, 1), cap=0.55), 'clavicle_' + s if k == 0 else 'upperarm_' + s, 'steel'))
        a((limb('rerebrace_' + s, sh + (el - sh) * 0.22, sh + (el - sh) * 0.9, 0.058, 0.052, c, q, mid=1.06, flare1=1.08), 'upperarm_' + s, 'steel'))
        a((C.ball('couter_' + s, tuple(el + np.array([0.004 * sx, 0.012, 0])), 0.066, c, seg=16 * (2 if q > 1 else 1), squash=(1.0, 1.05, 1.0)), 'lowerarm_' + s, 'steel'))
        a((L.sweep('couter_fan_' + s, [(el[0] + 0.03 * sx, el[1] - 0.02, el[2] + 0.055, 0.012, 0.045, 2.5), (el[0] + 0.072 * sx, el[1] - 0.005, el[2], 0.014, 0.062, 2.5), (el[0] + 0.03 * sx, el[1] - 0.02, el[2] - 0.055, 0.012, 0.045, 2.5)],
                   nu=10 * q, nv=6 * q, c=c, up=UP, cap=0.6), 'lowerarm_' + s, 'steel'))
        a((limb('vambrace_' + s, el + (wr - el) * 0.12, el + (wr - el) * 0.93, 0.054, 0.042, c, q, mid=1.04, flare0=1.06, flare1=1.1), 'lowerarm_' + s, 'steel'))
        a((limb('cuff_' + s, wr + (wr - el) * -0.02, wr + (he - wr) * 0.3, 0.056, 0.047, c, q, flare0=1.12, n=2.4), 'hand_' + s, 'steel'))
        a((L.sweep('gauntlet_' + s, [tuple(wr + (he - wr) * 0.25) + (0.046, 0.030, 3.0), tuple(wr + (he - wr) * 0.7) + (0.050, 0.032, 3.0), tuple(wr + (he - wr) * 1.15) + (0.046, 0.034, 3.0), tuple(wr + (he - wr) * 1.5) + (0.036, 0.03, 3.0)],
                   nu=12 * q, nv=8 * q, c=c, up=(sx, 0, 0), cap=0.6), 'hand_' + s, 'steel'))
        # legs: tasset, cuisse, poleyn with a side wing, greave, sabaton
        a((L.sweep('tasset_' + s, [(hp[0] + 0.012 * sx, -0.118, 0.955, 0.070, 0.012, 3.5), (hp[0] + 0.014 * sx, -0.128, 0.86, 0.078, 0.014, 3.5), (hp[0] + 0.016 * sx, -0.122, 0.775, 0.060, 0.011, 3.0)], nu=10 * q, nv=8 * q, c=c, up=UP, cap=0.7), 'thigh_' + s, 'steel'))
        a((limb('cuisse_' + s, hp + (kn - hp) * 0.08, hp + (kn - hp) * 0.9, 0.102, 0.076, c, q, mid=1.06, flare1=1.05), 'thigh_' + s, 'steel'))
        a((C.ball('poleyn_' + s, tuple(kn + np.array([0, -0.022, 0])), 0.074, c, seg=16 * (2 if q > 1 else 1), squash=(1.0, 1.05, 1.1)), 'calf_' + s, 'steel'))
        a((L.sweep('poleyn_wing_' + s, [(kn[0] + 0.045 * sx, kn[1] - 0.01, kn[2] + 0.06, 0.012, 0.045, 2.5), (kn[0] + 0.088 * sx, kn[1] + 0.005, kn[2], 0.014, 0.066, 2.5), (kn[0] + 0.045 * sx, kn[1] - 0.01, kn[2] - 0.06, 0.012, 0.045, 2.5)],
                   nu=10 * q, nv=6 * q, c=c, up=UP, cap=0.6), 'calf_' + s, 'steel'))
        a((L.sweep('greave_' + s, [tuple(kn + (an - kn) * 0.12) + (0.062, 0.066, 2.2), tuple(kn + (an - kn) * 0.35 + np.array([0, 0.012, 0])) + (0.066, 0.074, 2.2), tuple(kn + (an - kn) * 0.7) + (0.052, 0.056, 2.2), tuple(kn + (an - kn) * 0.97) + (0.046, 0.05, 2.2),
                                   tuple(an + np.array([0, -0.005, -0.03])) + (0.052, 0.058, 2.3)], nu=12 * q, nv=10 * q, c=c, up=UP, cap=0.75), 'calf_' + s, 'steel'))
        a((L.sweep('sabaton_' + s, [(an[0], an[1] + 0.055, 0.045, 0.045, 0.042, 2.6), (an[0], an[1] - 0.02, 0.055, 0.05, 0.052, 2.4), (bl[0], bl[1] + 0.02, 0.045, 0.052, 0.042, 2.4), (bl[0], bl[1] - 0.04, 0.036, 0.047, 0.033, 2.4),
                                    (toe[0], toe[1] - 0.02, 0.026, 0.026, 0.022, 2.2), (toe[0], toe[1] - 0.06, 0.018, 0.008, 0.008, 2.0)], nu=12 * q, nv=12 * q, c=c, up=(0, 0, 1), cap=0.4), 'foot_' + s, 'steel'))
    # ---- halberd in the right hand, butt on the ground
    hx, hy = J['hand_end_r'][0] - 0.01, J['hand_end_r'][1] - 0.012
    a((L.sweep('shaft', [(hx, hy, 0.0, 0.0165, 0.0165, 2.2), (hx, hy, 0.6, 0.0175, 0.0175, 2.2), (hx, hy, 1.4, 0.0175, 0.0175, 2.2), (hx, hy, 2.02, 0.016, 0.016, 2.2)], nu=10 * q, nv=20 * q, c=c, up=UP, cap=0.7), 'hand_r', 'wood'))
    a((L.sweep('socket', [(hx, hy, 1.86, 0.021, 0.021, 2.4), (hx, hy, 1.96, 0.021, 0.021, 2.6), (hx, hy, 2.06, 0.019, 0.019, 3.0)], nu=10 * q, nv=6 * q, c=c, up=UP, cap=0.8), 'hand_r', 'iron'))
    a((L.sweep('axe', [(hx, hy - 0.015, 1.99, 0.008, 0.045, 4), (hx, hy - 0.07, 1.99, 0.006, 0.06, 3.5), (hx, hy - 0.14, 1.985, 0.004, 0.105, 3.2), (hx, hy - 0.195, 1.98, 0.0012, 0.135, 3)], nu=12 * q, nv=10 * q, c=c, up=(0, 0, 1), cap=0.35), 'hand_r', 'iron'))
    a((L.sweep('fluke', [(hx, hy + 0.015, 1.995, 0.008, 0.03, 4), (hx, hy + 0.07, 1.985, 0.006, 0.02, 3), (hx, hy + 0.135, 1.955, 0.002, 0.004, 2.5)], nu=10 * q, nv=8 * q, c=c, up=(0, 0, 1), cap=0.3), 'hand_r', 'iron'))
    a((L.sweep('spike', [(hx, hy, 2.04, 0.014, 0.014, 4), (hx, hy, 2.16, 0.009, 0.009, 4), (hx, hy, 2.33, 0.0012, 0.0012, 3)], nu=8 * q, nv=10 * q, c=c, up=UP, cap=0.3), 'hand_r', 'iron'))
    return P


def tint(bc, col, keep, sat_gate=0.0):
    """recolour only what is blue paint: weight by how blue the texel is"""
    lum = bc @ np.array([0.2126, 0.7152, 0.0722], np.float32); blue = np.clip((bc[..., 2] - np.maximum(bc[..., 0], bc[..., 1])) * 4.0, 0, 1)[..., None]
    return bc * (1 - blue) + blue * (bc * keep + (lum[..., None] ** 0.85) * np.array(col, np.float32) * 2.6 * (1 - keep))


WEAK = ('NOT photoreal at 1 m. The harness is forty clean swept solids: lames have no rolled edges, rivets, straps, buckles or hinges, the helm has a painted-dark sight and breaths rather than cut ones, and there are no fingers, only a mitten gauntlet. '
        'Nobody is inside: no arming doublet at the joints, no mail at the armpit or neck, so gaps between plates look into empty space when the limbs bend. '
        'The halberd is merged into the mesh on hand_r rather than delivered as a separate weapon with a grip socket. Rest pose is a standing guard pose with the arms down, not the A pose of the Manny skeleton, so retargeted clips need a pose offset. '
        'Rigid one-bone skinning (correct for plate, wrong for the mail skirt and belt). No animation clips, no Physics Asset. The red and silver sets recolour only the blue paint of the base colour map.')


def main(mode):
    L.reset(); asset = 'SK_Knight_PR'; outdir = os.path.join(L.UNC, 'npc_knight_blue', 'Knight'); hc = L.coll('Source_Hi'); parts = build(4, hc)
    mats = {'steel': steel_mat('steel', seed=1.0), 'helm': steel_mat('helm', slit=True, seed=2.0), 'mail': mail_mat(), 'leather': leather_mat(), 'wood': T.wood_mat('ash', axis=2, grip=(0.6, 1.3), dark_from=(1.75, 1.9)), 'iron': T.iron_mat('iron', polish=(1, J['hand_end_r'][1] - 0.012 - 0.16, J['hand_end_r'][1] - 0.012 - 0.2), rust=0.4, seed=3.0)}
    for i, (o, b, m) in enumerate(parts):
        if m in ('steel', 'helm', 'iron'):
            L.displace_np(o, lambda P_, i=i: 0.0005 * fbm(P_, 40 + i, 28, 3) + 0.00015 * fbm(P_, 90 + i, 120, 2))
        o.data.materials.append(mats[m])
    hi = [o for o, b, m in parts]; R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=28, el=8, fill=1.15, lens=70, spp=192, res=(900, 1200), dz=0.05)
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, 0, 1.5), radius=0.42, az=32, el=4, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
        L.shot(R_, os.path.join(d, '%s_back.png' % tag), obs, az=200, el=10, fill=1.15, lens=70, res=(750, 1000), spp=128, dz=0.05)
    if mode == 'review':
        shots(hi, 'Knight_hi', L.REVIEW); return
    lo = C.rigid_lo([(o, b) for o, b, m in parts], 16000, asset, L.coll(asset)); arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset))
    fams = ['npc_knight_blue', 'npc_knight_red', 'npc_knight_silver', 'npc_knight_red_attacking']; ids = L.origin_ids(fams)
    man, lods, files, vfiles = C.finish_creature(
        asset, 'character_humanoid', lo, hi, arm, outdir, 2048, families=fams + ['281-289 people/knight/blue', '271-279 people/knight/red', '291-299 people/knight/silver', '712 people/knight/red/attack'], origin=ids,
        dresses='castle guard in full plate, 1.85 m, with a 2.3 m halberd in the right hand: sallet with pointed visor and bevor, globose cuirass, three-lame pauldrons and fauld, mail skirt, tassets, winged couters and poleyns, greaves, pointed sabatons; blue painted steel worn to bare metal',
        weaknesses=WEAK, script=SCRIPT + ' final', extrude=0.006, maxdist=0.015, lod_ratios=(0.5, 0.25, 0.12), rigid=True,
        variants={'Red': lambda bc: tint(bc, (0.50, 0.06, 0.04), 0.15), 'Silver': lambda bc: tint(bc, (0.40, 0.41, 0.42), 0.1)},
        extra={'colour_families': {'npc_knight_blue': 'T_Knight_PR_BC.png', 'npc_knight_red': 'T_Knight_PR_Red_BC.png', 'npc_knight_silver': 'T_Knight_PR_Silver_BC.png', 'npc_knight_red_attacking': 'T_Knight_PR_Red_BC.png (the attack is a clip, not a mesh; no clip is delivered)'},
               'skeleton_note': 'bone names and hierarchy of the project humanoid (CONVENTIONS.md section 11 core set: root, pelvis, spine_01..05, neck_01..02, head, clavicle/upperarm/lowerarm/hand/thigh/calf/foot/ball _l/_r)', 'contact_crop': 0.95})
    man_p = os.path.join(outdir, 'manifest.json')
    shots([lo], 'render', outdir)
    C.pose(arm, {'upperarm_l': (0, 0, -35), 'lowerarm_l': (-40, 0, 0), 'thigh_l': (-30, 0, 0), 'calf_l': (35, 0, 0), 'thigh_r': (12, 0, 0), 'head': (0, 0, 25), 'spine_03': (0, 0, 8)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=28, el=8, fill=1.15, lens=70, res=(750, 1000), spp=128, dz=0.05); C.pose(arm, {})
    for i, (suf, p) in enumerate(vfiles.items()):
        o = L.dup(lo, 'variant_' + suf, L.coll('Review')); o.modifiers.clear(); o.parent = None; o.location = ((i + 1) * 0.95, 0.15 * (i + 1), 0); o.data.materials.clear(); o.data.materials.append(L.game_material('MI_Knight_PR_' + suf, dict(files, BC=p)))
    vs = [o for o in bpy.data.objects if o.name.startswith('variant_')]
    L.shot(R_, os.path.join(outdir, 'render_variants.png'), [lo] + vs, az=15, el=8, fill=1.25, lens=70, res=(1400, 1000), spp=128, dz=0.05)
    for o in vs:
        bpy.data.objects.remove(o)
    L.save_blend()


if __name__ == '__main__':
    a = L.args(); main(a[0] if a else 'review')
