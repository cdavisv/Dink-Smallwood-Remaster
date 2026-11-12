"""slayer (641-649 foes/slayers/walk, 632-636 attack): a gaunt, hunched biped with scythe arms, a row of dorsal
spines and a long whip tail.

    tools/bl.sh build_slayer.py [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_bonca as B
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_slayer.py'
J = {'pelvis': (0, 0.28, 1.04), 'spine1': (0, 0.02, 1.20), 'chest': (0, -0.26, 1.30), 'neck': (0, -0.50, 1.30), 'head': (0, -0.70, 1.20), 'snout': (0, -0.94, 1.05), 'snout_tip': (0, -1.13, 0.93),
     'jaw': (0, -0.80, 1.07), 'tail1': (0, 0.58, 1.00), 'tail2': (0, 0.98, 0.95), 'tail3': (0, 1.42, 1.02), 'tail4': (0, 1.84, 1.24), 'tail5': (0, 2.16, 1.60), 'tail6': (0, 2.30, 2.02), 'tail7': (0, 2.16, 2.38)}
R = {'pelvis': (0.16, 0.20, 0.17), 'spine1': (0.17, 0.2, 0.19), 'chest': (0.21, 0.22, 0.24), 'neck': (0.11, 0.12, 0.13), 'head': (0.105, 0.13, 0.11), 'snout': (0.06, 0.08, 0.06), 'snout_tip': 0.03, 'jaw': (0.06, 0.09, 0.04),
     'tail1': 0.115, 'tail2': 0.078, 'tail3': 0.052, 'tail4': 0.036, 'tail5': 0.025, 'tail6': 0.017, 'tail7': 0.012}
E = [('pelvis', 'spine1'), ('spine1', 'chest'), ('chest', 'neck'), ('neck', 'head'), ('head', 'snout'), ('snout', 'snout_tip'), ('head', 'jaw'),
     ('pelvis', 'tail1'), ('tail1', 'tail2'), ('tail2', 'tail3'), ('tail3', 'tail4'), ('tail4', 'tail5'), ('tail5', 'tail6'), ('tail6', 'tail7')]
for s, sx in (('l', 1), ('r', -1)):
    J.update({'hip_' + s: (0.16 * sx, 0.16, 0.98), 'knee_' + s: (0.25 * sx, -0.16, 0.66), 'hock_' + s: (0.22 * sx, 0.20, 0.37), 'ankle_' + s: (0.22 * sx, 0.04, 0.10), 'foot_' + s: (0.23 * sx, -0.14, 0.05),
              'toe1_' + s: (0.15 * sx, -0.30, 0.035), 'toe2_' + s: (0.24 * sx, -0.33, 0.035), 'toe3_' + s: (0.33 * sx, -0.28, 0.035),
              'shoulder_' + s: (0.24 * sx, -0.30, 1.26), 'elbow_' + s: (0.40 * sx, -0.36, 0.90), 'wrist_' + s: (0.34 * sx, -0.66, 0.74)})
    R.update({'hip_' + s: (0.12, 0.15, 0.15), 'knee_' + s: 0.075, 'hock_' + s: 0.052, 'ankle_' + s: 0.045, 'foot_' + s: (0.055, 0.06, 0.04), 'toe1_' + s: 0.028, 'toe2_' + s: 0.03, 'toe3_' + s: 0.028,
              'shoulder_' + s: 0.10, 'elbow_' + s: 0.055, 'wrist_' + s: 0.046})
    E += [('pelvis', 'hip_' + s), ('hip_' + s, 'knee_' + s), ('knee_' + s, 'hock_' + s), ('hock_' + s, 'ankle_' + s), ('ankle_' + s, 'foot_' + s), ('foot_' + s, 'toe1_' + s), ('foot_' + s, 'toe2_' + s),
          ('foot_' + s, 'toe3_' + s), ('chest', 'shoulder_' + s), ('shoulder_' + s, 'elbow_' + s), ('elbow_' + s, 'wrist_' + s)]
SCYTHE = {1: (0.27, -1.22, 0.015), -1: (-0.27, -1.22, 0.015)}

BONES = [('root', (0, 0, 0), (0, 0.12, 0), None), ('pelvis', 'pelvis', 'spine1', 'root'), ('spine_01', 'spine1', 'chest', 'pelvis'), ('spine_02', 'chest', 'neck', 'spine_01'), ('neck_01', 'neck', 'head', 'spine_02'),
         ('head', 'head', 'snout_tip', 'neck_01')] + [('tail_%02d' % (i + 1), a, b, 'pelvis' if i == 0 else 'tail_%02d' % i) for i, (a, b) in enumerate(
             [('pelvis', 'tail1'), ('tail1', 'tail2'), ('tail2', 'tail3'), ('tail3', 'tail4'), ('tail4', 'tail5'), ('tail5', 'tail6'), ('tail6', 'tail7')])]
for s, sx in (('l', 1), ('r', -1)):
    BONES += [('thigh_' + s, 'hip_' + s, 'knee_' + s, 'pelvis'), ('calf_' + s, 'knee_' + s, 'hock_' + s, 'thigh_' + s), ('foot_' + s, 'hock_' + s, 'ankle_' + s, 'calf_' + s), ('ball_' + s, 'ankle_' + s, 'toe2_' + s, 'foot_' + s),
              ('upperarm_' + s, 'shoulder_' + s, 'elbow_' + s, 'spine_02'), ('lowerarm_' + s, 'elbow_' + s, 'wrist_' + s, 'upperarm_' + s), ('hand_' + s, 'wrist_' + s, SCYTHE[sx], 'lowerarm_' + s)]


def hide_mat():
    """dark teal hide, brown saddle blotches, raw red sores, bony highlights; fine pebbled scales"""
    t = NT('hide'); rib = t.attr('rib'); n1 = t.noise(6, 5, 0.65); n2 = t.noise(34, 4, 0.6, distortion=0.6); nz = t.sep(t.gnormal)[2]
    cell = t.voronoi(230, feature='DISTANCE_TO_EDGE'); cellv = t.sep(t.voronoi(230, out='Color'))[0]; edge = t.ramp(cell, [(0.0, 1.0), (0.1, 0.0)])
    base = t.ramp(n1, [(0.25, (0.014, 0.034, 0.030)), (0.55, (0.030, 0.075, 0.062)), (0.85, (0.060, 0.120, 0.095))]); base = t.hsv(base, v=t.maprange(cellv, 0, 1, 0.75, 1.25))
    blot = t.ramp(t.noise(3.4, 4, 0.6, vec=t.mapping(loc=(2, 5, 3))), [(0.44, 0.0), (0.56, 1.0)]); base = t.mix(t.math('MULTIPLY', blot, 0.9), base, t.mix(n2, (0.055, 0.026, 0.012), (0.15, 0.075, 0.032)))
    sore = t.ramp(t.noise(7, 4, 0.7, vec=t.mapping(loc=(7, 1, 4))), [(0.62, 0.0), (0.68, 1.0)]); base = t.mix(t.math('MULTIPLY', sore, 0.85), base, t.mix(n2, (0.10, 0.012, 0.010), (0.30, 0.035, 0.022)))
    belly = t.maprange(nz, -0.8, -0.2, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', belly, 0.8), base, t.mix(n2, (0.13, 0.10, 0.055), (0.26, 0.21, 0.12)))
    base = t.mix(t.math('MULTIPLY', rib, 0.6), base, (0.16, 0.19, 0.14))                                   # skin stretched pale over bone
    ao = t.ao(0.04, 12); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.8, 0.0)]), 0.75), base, (0.010, 0.012, 0.011)); base = t.mix(t.math('MULTIPLY', edge, 0.5), base, (0.008, 0.012, 0.011))
    rough = t.mixf(n2, 0.42, 0.62); rough = t.mixf(sore, rough, 0.22); rough = t.math('ADD', rough, t.math('MULTIPLY', edge, 0.25))
    h = t.math('ADD', t.math('MULTIPLY', t.ramp(cell, [(0.0, 0.0), (0.25, 1.0)]), 0.7), t.math('MULTIPLY', t.noise(500, 3, 0.6), 0.3))
    nrm = t.bump(t.noise(70, 4, 0.65, distortion=0.8), 0.3, 0.004, normal=t.bump(h, 0.85, 0.0018)); t.set(base=base, rough=rough, normal=nrm, spec=0.6); return t.mat


def horn_mat():
    """amber-orange keratin, dark at the root, split and ridged along its length, paler worn tips"""
    t = NT('horn'); n = t.noise(30, 4, 0.6); fib = t.noise(4, 4, 0.65, vec=t.mapping(scale=(110, 110, 9)))
    base = t.ramp(fib, [(0.25, (0.10, 0.035, 0.010)), (0.55, (0.30, 0.12, 0.028)), (0.85, (0.50, 0.26, 0.07))]); ao = t.ao(0.03, 8)
    base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.85, 0.0)]), 0.85), base, (0.025, 0.014, 0.008)); base = t.mix(t.math('MULTIPLY', t.ramp(t.pointiness, [(0.52, 0.0), (0.62, 1.0)]), 0.6), base, (0.55, 0.42, 0.24))
    t.set(base=base, rough=t.mixf(n, 0.28, 0.5), normal=t.bump(fib, 0.5, 0.001)); return t.mat


def eye_mat():
    t = NT('eye'); nrm = t.sep(t.gnormal); n = t.noise(200, 3, 0.6); t.set(base=t.mix(n, (0.25, 0.012, 0.008), (0.55, 0.05, 0.02)), rough=0.05, coat=1.0, coat_rough=0.02, emission=(0.4, 0.02, 0.01), emission_strength=0.0); return t.mat


def build_hi(c):
    body = C.graph_body('body', J, E, R, c, voxel=0.008, smooth=12); L.subsurf(body, 1)
    P = L.co(body); N = L.vnormals(body); x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # ribs: hoops round the chest, stronger low on the flanks; vertebral bumps along the top line
    trunk = smoothstep(-0.5, -0.38, y) * (1 - smoothstep(0.1, 0.3, y)) * smoothstep(0.95, 1.05, z) * (1 - smoothstep(0.2, 0.3, np.abs(x)) * 0)
    ribs = (0.5 + 0.5 * np.sin(2 * np.pi * (y + 0.25 * (z - 1.2)) / 0.085)) ** 2 * trunk * smoothstep(0.3, -0.5, N[:, 2])
    spine = np.exp(-(x / 0.035) ** 2) * smoothstep(0.2, 0.8, N[:, 2]) * (0.5 + 0.5 * np.sin(2 * np.pi * y / 0.075)) * (1 - smoothstep(1.0, 1.6, y))
    rib = np.clip(ribs + spine, 0, 1)
    lump = 0.005 * fbm(P, 11, 10, 3) - 0.004 * (1 - np.abs(fbm(P, 13, 24, 3))) ** 3 + 0.0012 * np.abs(fbm(P, 17, 90, 2))
    thin = smoothstep(0.02, 0.06, np.minimum(1.0, np.abs(lump) * 0 + 1))               # keep the thin tail and limbs from tearing
    L.set_co(body, P + N * ((ribs * 0.02 + spine * 0.016 - trunk * 0.008) + lump * smoothstep(1.2, 0.9, y) * 0 + lump)[:, None])
    C.set_attr(body, 'rib', rib); body.data.materials.append(hide_mat()); obs = [body]; hm = horn_mat(); em = eye_mat(); tm = B.tooth_mat()
    for sx in (1, -1):
        hit = C.surface_hit(body, (0.3 * sx, -0.74, 1.215), (-sx, 0, 0)); ex = (hit[0][0] if hit else 0.085 * sx) - 0.012 * sx
        e = C.ball('eye', (ex, -0.74, 1.215), 0.022, c, squash=(0.8, 1, 0.9)); e.data.materials.append(em); obs.append(e)
        w = np.array(J['wrist_' + ('l' if sx > 0 else 'r')])                                     # the scythe: one long down-curved blade from each wrist to the ground
        sc = C.cone('scythe', tuple(w + np.array([0, 0.05, 0.02])), SCYTHE[sx], 0.05, c, bend=(0.07 * sx, -0.10, 0.30), nu=12, nv=14, sharp=1.1); P_ = L.co(sc)
        cx = (P_[:, 0] - (w[0] + SCYTHE[sx][0]) / 2); L.set_co(sc, P_ - np.array([1, 0, 0]) * (cx * 0.45)[:, None]); sc.data.materials.append(hm); obs.append(sc)      # flattened to a blade
        th = C.cone('thumb', tuple(w + np.array([-0.02 * sx, 0.0, -0.02])), (w[0] - 0.10 * sx, w[1] - 0.16, w[2] - 0.20), 0.026, c, bend=(0, -0.05, 0.03)); th.data.materials.append(hm); obs.append(th)
        for k, (tx, ty) in enumerate(((0.15, -0.30), (0.24, -0.33), (0.33, -0.28))):
            d = np.array([tx - 0.23, ty + 0.14, 0]); d /= np.linalg.norm(d)
            cl = C.cone('claw', (tx * sx, ty - 0.005, 0.04), ((tx + d[0] * 0.10) * sx, ty + d[1] * 0.12, 0.005), 0.022, c, bend=(0, 0, 0.035)); cl.data.materials.append(hm); obs.append(cl)
        sp = C.cone('spur', (0.22 * sx, 0.24, 0.39), (0.22 * sx, 0.38, 0.47), 0.03, c, bend=(0, 0.0, -0.03)); sp.data.materials.append(hm); obs.append(sp)
    # dorsal spines from the neck to the hips, tallest over the shoulders, raked back
    for k, (yy, ln) in enumerate(((-0.52, 0.20), (-0.36, 0.31), (-0.20, 0.38), (-0.04, 0.36), (0.12, 0.31), (0.27, 0.25), (0.42, 0.18))):
        hit = C.surface_hit(body, (0.0, yy, 2.5), (0, 0, -1)); z0 = (hit[0][2] if hit else 1.4) - 0.03
        s_ = C.cone('spine', (0.0, yy, z0), (0.012 * ((k % 2) * 2 - 1), yy + ln * 0.5, z0 + ln), 0.034, c, bend=(0, -0.05, 0.02), nu=10, nv=10); s_.data.materials.append(hm); obs.append(s_)
    for k in range(7):                                             # needle teeth along the upper jaw
        for sx in (1, -1):
            ty = -0.86 - k * 0.034; tz = 1.045 - (k * 0.034) * 0.62; hit = C.surface_hit(body, (0.2 * sx, ty, tz), (-sx, 0, 0)); tx = (hit[0][0] if hit else 0.05 * sx) - 0.006 * sx
            tt = C.cone('tooth', (tx, ty, tz), (tx * 1.05, ty - 0.004, tz - 0.03), 0.006, c, nu=6, nv=5); tt.data.materials.append(tm); obs.append(tt)
    return obs


WEAK = ('NOT photoreal at 1 m: a lit maquette. Anatomy is invented from 110-pixel sprites on a joint graph: no modelled muscle, tendon or joint structure beyond rib hoops and a vertebral ridge from displacement. '
        'Scythes, spines, claws and teeth are separate horn solids pushed into the body, without sockets or gums. The head has no mouth opening, lids or nostrils, and there is no jaw bone. '
        'The game mesh is a decimation of the remeshed source: no edge loops at joints, and the 1 cm tail tip keeps few triangles. Skin weights are inverse-distance, checked in one pose (render_pose.png). '
        'No animation clips, no Physics Asset. Smart-projected UVs with many islands.')


def main(mode):
    L.reset(); asset = 'SK_Slayer_PR'; outdir = os.path.join(L.UNC, 'slayer', 'Slayer'); hi = build_hi(L.coll('Source_Hi'))
    R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=52, el=10, fill=1.25, lens=60, spp=192, dz=-0.1)
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, -0.72, 1.12), radius=0.5, az=40, el=6, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
        L.shot(R_, os.path.join(d, '%s_back.png' % tag), obs, az=215, el=18, fill=1.25, lens=60, res=(1000, 750), spp=128)
    if mode == 'review':
        shots(hi, 'Slayer_hi', L.REVIEW); return
    lo = L.make_lo(hi, 18000, asset, L.coll(asset), angle=72, margin=0.004); arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset)); ids = L.origin_ids(['slayer'])
    C.finish_creature(asset, 'creature', lo, hi, arm, outdir, 2048, families=['slayer', '641-649 foes/slayers/walk', '632-636 foes/slayers/attack'], origin=ids,
                      dresses='slayer: a gaunt hunched biped, 1.7 m at the spines and about 3.5 m from snout to the tip of its whip tail; dark teal hide with brown blotches and raw red sores, one long amber scythe on each arm, seven raked dorsal spines, digitigrade clawed legs, red eyes',
                      weaknesses=WEAK, script=SCRIPT + ' final', extrude=0.01, maxdist=0.03, extra={'contact_crop': 0.9})
    shots([lo], 'render', outdir)
    C.pose(arm, {'tail_02': (0, 0, 18), 'tail_03': (0, 0, 22), 'tail_04': (0, 0, 22), 'tail_05': (0, 0, 20), 'thigh_l': (-25, 0, 0), 'calf_l': (22, 0, 0), 'thigh_r': (18, 0, 0),
                 'upperarm_l': (-35, 0, 0), 'lowerarm_l': (-25, 0, 0), 'neck_01': (0, 0, -16), 'head': (0, 0, -10)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=52, el=10, fill=1.25, lens=60, res=(1000, 750), spp=128, dz=-0.1); C.pose(arm, {}); L.save_blend()


if __name__ == '__main__':
    a = L.args(); main(a[0] if a else 'review')
