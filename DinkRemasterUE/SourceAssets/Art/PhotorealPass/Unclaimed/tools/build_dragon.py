"""dragon (202-208 foes/dragon/f2-w): an upright, long-necked dragon with membrane wings, about 3.4 m at the head.

    tools/bl.sh build_dragon.py [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_bonca as B
import build_slayer as S
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_dragon.py'
J = {'pelvis': (0, 0.28, 1.25), 'belly': (0, 0.06, 1.68), 'chest': (0, -0.16, 2.16), 'neck1': (0, -0.38, 2.62), 'neck2': (0, -0.66, 2.98), 'neck3': (0, -0.98, 3.18), 'head': (0, -1.28, 3.14), 'snout': (0, -1.58, 3.02),
     'snout_tip': (0, -1.76, 2.95), 'jaw': (0, -1.50, 2.93), 'tail1': (0, 0.74, 1.00), 'tail2': (0, 1.24, 0.72), 'tail3': (0, 1.84, 0.52), 'tail4': (0, 2.44, 0.46), 'tail5': (0, 3.02, 0.55), 'tail6': (0, 3.52, 0.76),
     'tail7': (0, 3.92, 1.02)}
R = {'pelvis': (0.36, 0.38, 0.36), 'belly': (0.42, 0.44, 0.42), 'chest': (0.40, 0.40, 0.42), 'neck1': 0.245, 'neck2': 0.185, 'neck3': 0.155, 'head': (0.16, 0.2, 0.165), 'snout': (0.11, 0.14, 0.10), 'snout_tip': (0.08, 0.08, 0.065),
     'jaw': (0.09, 0.14, 0.05), 'tail1': 0.29, 'tail2': 0.215, 'tail3': 0.155, 'tail4': 0.105, 'tail5': 0.068, 'tail6': 0.042, 'tail7': 0.024}
E = [('pelvis', 'belly'), ('belly', 'chest'), ('chest', 'neck1'), ('neck1', 'neck2'), ('neck2', 'neck3'), ('neck3', 'head'), ('head', 'snout'), ('snout', 'snout_tip'), ('head', 'jaw'),
     ('pelvis', 'tail1'), ('tail1', 'tail2'), ('tail2', 'tail3'), ('tail3', 'tail4'), ('tail4', 'tail5'), ('tail5', 'tail6'), ('tail6', 'tail7')]
for s, sx in (('l', 1), ('r', -1)):
    J.update({'hip_' + s: (0.36 * sx, 0.14, 1.16), 'knee_' + s: (0.50 * sx, -0.36, 0.76), 'hock_' + s: (0.48 * sx, 0.20, 0.44), 'ankle_' + s: (0.48 * sx, 0.02, 0.15), 'foot_' + s: (0.50 * sx, -0.28, 0.085),
              'toe1_' + s: (0.36 * sx, -0.52, 0.06), 'toe2_' + s: (0.51 * sx, -0.58, 0.06), 'toe3_' + s: (0.66 * sx, -0.50, 0.06),
              'shoulder_' + s: (0.40 * sx, -0.30, 2.16), 'elbow_' + s: (0.60 * sx, -0.58, 1.82), 'wrist_' + s: (0.52 * sx, -0.88, 1.92),
              'wroot_' + s: (0.26 * sx, 0.22, 2.40), 'welbow_' + s: (1.15 * sx, 0.52, 3.25), 'wwrist_' + s: (2.05 * sx, 0.34, 3.85), 'f1_' + s: (3.35 * sx, 0.62, 3.42), 'f2_' + s: (2.95 * sx, 1.02, 2.42), 'f3_' + s: (2.25 * sx, 1.22, 1.72)})
    R.update({'hip_' + s: (0.27, 0.32, 0.33), 'knee_' + s: 0.185, 'hock_' + s: 0.12, 'ankle_' + s: 0.10, 'foot_' + s: (0.12, 0.13, 0.085), 'toe1_' + s: 0.058, 'toe2_' + s: 0.064, 'toe3_' + s: 0.058,
              'shoulder_' + s: 0.165, 'elbow_' + s: 0.10, 'wrist_' + s: 0.078, 'wroot_' + s: 0.13, 'welbow_' + s: 0.085, 'wwrist_' + s: 0.062, 'f1_' + s: 0.02, 'f2_' + s: 0.02, 'f3_' + s: 0.02})
    E += [('pelvis', 'hip_' + s), ('hip_' + s, 'knee_' + s), ('knee_' + s, 'hock_' + s), ('hock_' + s, 'ankle_' + s), ('ankle_' + s, 'foot_' + s), ('foot_' + s, 'toe1_' + s), ('foot_' + s, 'toe2_' + s), ('foot_' + s, 'toe3_' + s),
          ('chest', 'shoulder_' + s), ('shoulder_' + s, 'elbow_' + s), ('elbow_' + s, 'wrist_' + s), ('chest', 'wroot_' + s), ('wroot_' + s, 'welbow_' + s), ('welbow_' + s, 'wwrist_' + s),
          ('wwrist_' + s, 'f1_' + s), ('wwrist_' + s, 'f2_' + s), ('wwrist_' + s, 'f3_' + s)]

BONES = [('root', (0, 0, 0), (0, 0.15, 0), None), ('pelvis', 'pelvis', 'belly', 'root'), ('spine_01', 'belly', 'chest', 'pelvis'), ('spine_02', 'chest', 'neck1', 'spine_01'), ('neck_01', 'neck1', 'neck2', 'spine_02'),
         ('neck_02', 'neck2', 'neck3', 'neck_01'), ('neck_03', 'neck3', 'head', 'neck_02'), ('head', 'head', 'snout_tip', 'neck_03'), ('jaw', 'head', 'jaw', 'head')] + \
        [('tail_%02d' % (i + 1), a, b, 'pelvis' if i == 0 else 'tail_%02d' % i) for i, (a, b) in enumerate([('pelvis', 'tail1'), ('tail1', 'tail2'), ('tail2', 'tail3'), ('tail3', 'tail4'), ('tail4', 'tail5'), ('tail5', 'tail6'), ('tail6', 'tail7')])]
for s in 'lr':
    BONES += [('thigh_' + s, 'hip_' + s, 'knee_' + s, 'pelvis'), ('calf_' + s, 'knee_' + s, 'hock_' + s, 'thigh_' + s), ('foot_' + s, 'hock_' + s, 'ankle_' + s, 'calf_' + s), ('ball_' + s, 'ankle_' + s, 'toe2_' + s, 'foot_' + s),
              ('upperarm_' + s, 'shoulder_' + s, 'elbow_' + s, 'spine_02'), ('lowerarm_' + s, 'elbow_' + s, 'wrist_' + s, 'upperarm_' + s),
              ('wing_01_' + s, 'wroot_' + s, 'welbow_' + s, 'spine_02'), ('wing_02_' + s, 'welbow_' + s, 'wwrist_' + s, 'wing_01_' + s), ('wing_f1_' + s, 'wwrist_' + s, 'f1_' + s, 'wing_02_' + s),
              ('wing_f2_' + s, 'wwrist_' + s, 'f2_' + s, 'wing_02_' + s), ('wing_f3_' + s, 'wwrist_' + s, 'f3_' + s, 'wing_02_' + s)]


def hide_mat():
    """orange-brown scaled hide, darker saddle along the back, pale plated belly"""
    t = NT('hide'); scute = t.attr('scute'); n1 = t.noise(4, 5, 0.65); n2 = t.noise(26, 4, 0.6, distortion=0.6); nz = t.sep(t.gnormal)[2]
    cell = t.voronoi(95, feature='DISTANCE_TO_EDGE'); cv = t.sep(t.voronoi(95, out='Color')); edge = t.ramp(cell, [(0.0, 1.0), (0.1, 0.0)])
    base = t.ramp(n1, [(0.25, (0.085, 0.030, 0.010)), (0.55, (0.20, 0.080, 0.022)), (0.85, (0.36, 0.17, 0.045))]); base = t.hsv(base, v=t.maprange(cv[0], 0, 1, 0.7, 1.3), h=t.maprange(cv[1], 0, 1, 0.485, 0.515))
    back = t.maprange(nz, 0.2, 0.9, 0.0, 1.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', back, 0.6), base, t.mix(n2, (0.045, 0.016, 0.008), (0.11, 0.04, 0.014)))
    base = t.mix(t.math('MULTIPLY', scute, 0.9), base, t.mix(n2, (0.30, 0.20, 0.085), (0.52, 0.40, 0.19)))
    ao = t.ao(0.07, 12); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.8, 0.0)]), 0.7), base, (0.02, 0.012, 0.008)); base = t.mix(t.math('MULTIPLY', edge, 0.55), base, (0.018, 0.01, 0.006))
    rough = t.mixf(n2, 0.36, 0.56); rough = t.math('ADD', rough, t.math('MULTIPLY', edge, 0.3))
    h = t.math('ADD', t.math('MULTIPLY', t.ramp(cell, [(0.0, 0.0), (0.3, 1.0)]), 0.8), t.math('MULTIPLY', t.noise(300, 3, 0.6), 0.2))
    t.set(base=base, rough=rough, normal=t.bump(t.noise(40, 4, 0.65, distortion=0.8), 0.3, 0.008, normal=t.bump(h, 0.9, 0.004)), spec=0.6); return t.mat


def membrane_mat():
    """wing skin from its own UV (u from the leading finger to the trailing one, v from the wrist to the edge): green, veined, torn and reddened towards the trailing edge"""
    t = NT('membrane'); uv = t.sep(t.uv); u = uv[0]; v = uv[1]; n = t.noise(1.0, 5, 0.65, vec=t.comb(t.math('MULTIPLY', u, 6.0), t.math('MULTIPLY', v, 9.0), 0.0)); n2 = t.noise(120, 3, 0.6)
    base = t.ramp(n, [(0.25, (0.022, 0.060, 0.018)), (0.55, (0.055, 0.125, 0.035)), (0.85, (0.14, 0.21, 0.06))])
    vein = t.ramp(t.voronoi(1.0, vec=t.comb(t.math('MULTIPLY', u, 9.0), t.math('MULTIPLY', v, 5.0), 0.0), feature='DISTANCE_TO_EDGE'), [(0.0, 1.0), (0.05, 0.0)])
    ray = t.ramp(t.math('ABSOLUTE', t.math('SUBTRACT', t.math('FRACT', t.math('MULTIPLY', u, 5.0)), 0.5)), [(0.0, 1.0), (0.06, 0.0)])
    base = t.mix(t.math('MULTIPLY', t.math('MAXIMUM', vein, ray), 0.6), base, (0.02, 0.045, 0.014))
    red = t.maprange(t.math('ADD', v, t.math('MULTIPLY', t.math('SUBTRACT', n, 0.5), 0.3)), 0.70, 1.02, 0.0, 1.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', red, 0.8), base, t.mix(n2, (0.13, 0.022, 0.012), (0.27, 0.06, 0.022)))
    t.set(base=base, rough=t.mixf(n, 0.4, 0.62), normal=t.bump(t.math('ADD', t.math('MAXIMUM', vein, ray), t.math('MULTIPLY', n2, 0.3)), 0.5, 0.003), sss=0.1, sss_scale=0.02); return t.mat


def membrane(name, a0, a1, b0, b1, c, hi, sag=0.12, thick=0.012):
    """skin stretched between two spars (a0 -> a1 and b0 -> b1), scalloped at the free edge; a thin closed shell"""
    a0, a1, b0, b1 = (np.array(p, float) for p in (a0, a1, b0, b1)); nu, nv = (40, 40) if hi else (7, 7)

    def fn(U, V):
        A = a0[None] * (1 - V[:, None]) + a1[None] * V[:, None]; Bp = b0[None] * (1 - V[:, None]) + b1[None] * V[:, None]; P = A * (1 - U[:, None]) + Bp * U[:, None]
        pull = sag * np.sin(np.pi * U) * V ** 1.5                                   # the free edge sags back towards the wrist
        d = (a0 + b0) / 2 - P; d /= np.linalg.norm(d, axis=1)[:, None] + 1e-9; span = np.linalg.norm(a1 - b1)
        P = P + d * (pull * span)[:, None]; P[:, 2] -= 0.04 * span * np.sin(np.pi * U) * V                                  # and bellies down a little
        return P
    ob = L.grid_surface(name, fn, nu, nv, c, closed_u=False); L.mod(ob, 'SOLIDIFY', thickness=thick, offset=0.0); L.apply_mods(ob); L.fix_normals(ob); return ob


def build_hi(c, hi=True):
    body = C.graph_body('body', J, E, R, c, voxel=0.016, smooth=12); L.subsurf(body, 1)
    P = L.co(body); N = L.vnormals(body); x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # belly scutes: broad overlapping plates down the front of neck, chest and belly, and under the tail
    front = smoothstep(0.25, 0.75, -N[:, 1] * 0.8 - N[:, 2] * 0.45 + 0.15) * smoothstep(0.34, 0.2, np.abs(x)) * smoothstep(0.9, 1.2, z) * (1 - smoothstep(-1.2, -1.35, y))
    under = smoothstep(0.3, 0.8, -N[:, 2]) * smoothstep(0.6, 0.9, y) * smoothstep(0.25, 0.12, np.abs(x)); s_ = z + 0.6 * y; saw = (s_ / 0.11) % 1.0; saw2 = (y / 0.12) % 1.0
    scute = np.clip(front + under, 0, 1); step = front * (saw ** 1.5) + under * (saw2 ** 1.5)
    lump = 0.010 * fbm(P, 11, 5, 3) - 0.007 * (1 - np.abs(fbm(P, 13, 12, 3))) ** 3 + 0.002 * np.abs(fbm(P, 17, 50, 2))
    L.set_co(body, P + N * (step * 0.022 + lump * (1 - 0.6 * scute))[:, None]); C.set_attr(body, 'scute', scute); body.data.materials.append(hide_mat())
    obs = [body]; hm = S.horn_mat(); em = S.eye_mat(); tm = B.tooth_mat(); mm = membrane_mat()
    for s, sx in (('l', 1), ('r', -1)):
        hit = C.surface_hit(body, (0.5 * sx, -1.36, 3.19), (-sx, 0, 0)); ex = (hit[0][0] if hit else 0.14 * sx) - 0.02 * sx
        e = C.ball('eye', (ex, -1.36, 3.19), 0.036, c, squash=(0.8, 1, 0.85)); e.data.materials.append(em); obs.append(e)
        hn = C.cone('horn', (0.10 * sx, -1.10, 3.27), (0.22 * sx, -0.62, 3.62), 0.06, c, bend=(0.03 * sx, 0.05, 0.10), nu=12, nv=12); hn.data.materials.append(hm); obs.append(hn)
        for k, (tx, ty) in enumerate(((0.36, -0.52), (0.51, -0.58), (0.66, -0.50))):
            d = np.array([tx - 0.50, ty + 0.28, 0]); d /= np.linalg.norm(d)
            cl = C.cone('claw', (tx * sx, ty - 0.01, 0.07), ((tx + d[0] * 0.17) * sx, ty + d[1] * 0.2, 0.008), 0.046, c, bend=(0, 0, 0.06)); cl.data.materials.append(hm); obs.append(cl)
        w = np.array(J['wrist_' + s])
        for k, off in enumerate(((0.05, -0.12, -0.1), (0.0, -0.16, -0.06), (-0.06, -0.13, -0.1))):
            cl = C.cone('fclaw', tuple(w + np.array([off[0] * sx * 0.3, -0.03, -0.02])), tuple(w + np.array([off[0] * sx, off[1], off[2]])), 0.028, c, bend=(0, -0.03, 0.03)); cl.data.materials.append(hm); obs.append(cl)
        ww = np.array(J['wwrist_' + s]); f1, f2, f3 = (np.array(J['f%d_%s' % (i, s)]) for i in (1, 2, 3)); body_pt = np.array([0.30 * sx, 0.50, 1.55]); el_ = np.array(J['welbow_' + s]); rt = np.array(J['wroot_' + s])
        for nm, a0, a1, b0, b1 in (('m1', ww, f1, ww, f2), ('m2', ww, f2, ww, f3), ('m3', ww * 0.5 + el_ * 0.5, f3, rt * 0.6 + el_ * 0.4, body_pt), ('m4', ww, f3, ww * 0.5 + el_ * 0.5, f3 * 0.999 + 0.001 * ww)):
            if nm == 'm4':
                continue
            m_ = membrane('%s_%s' % (nm, s), a0 + (a1 - a0) * (0.02 if nm != 'm3' else 0), a1, b0 + (b1 - b0) * (0.02 if nm != 'm3' else 0), b1, c, hi); m_.data.materials.append(mm); obs.append(m_)
        tc = C.cone('wclaw', tuple(ww), tuple(ww + np.array([0.08 * sx, -0.22, 0.2])), 0.04, c, bend=(0, -0.05, 0.05)); tc.data.materials.append(hm); obs.append(tc)
    for k in range(16):                                            # ridge of spines from the crown down the neck and back
        t_ = k / 15; pts = [J['head'], J['neck3'], J['neck2'], J['neck1'], J['chest'], J['belly'], J['pelvis'], J['tail1']]; f = t_ * (len(pts) - 1); i = min(int(f), len(pts) - 2); p = np.array(pts[i]) * (1 - (f - i)) + np.array(pts[i + 1]) * (f - i)
        hit = C.surface_hit(body, (0.0, p[1] + 1.5, p[2] + 1.5), (0, -1, -1));
        if not hit:
            continue
        b0 = hit[0] - hit[1] * 0.03; ln = 0.10 + 0.10 * math.sin(math.pi * t_)
        s_ = C.cone('spine', tuple(b0), tuple(b0 + hit[1] * ln + np.array([0, 0.5 * ln, 0])), 0.04, c, nu=8, nv=6); s_.data.materials.append(hm); obs.append(s_)
    for k in range(8):
        for sx in (1, -1):
            ty = -1.50 - k * 0.032; tz = 3.0 - k * 0.012; hit = C.surface_hit(body, (0.4 * sx, ty, tz), (-sx, 0, 0)); tx = (hit[0][0] if hit else 0.08 * sx) - 0.01 * sx
            tt = C.cone('tooth', (tx, ty, tz), (tx * 1.03, ty - 0.004, tz - 0.05), 0.011, c, nu=6, nv=5); tt.data.materials.append(tm); obs.append(tt)
    return obs


WEAK = ('NOT photoreal at 1 m: a lit maquette. Anatomy is a joint-graph blob with displaced belly plates; no modelled musculature, wing-finger joints, eyelids, nostrils or mouth interior (there is a jaw bone but no mouth opening). '
        'Wing membranes are 12 mm solid shells stretched between straight spars: opaque in the game material (no translucency map), with no folds when the wing bends. '
        'Game mesh is a decimation of the remeshed source (no edge loops at joints). Inverse-distance skin weights, checked in one pose; membranes follow the nearest finger bone and will stretch badly if the wings fold. '
        'No animation clips (the dragon of the game flies, breathes fire and dies: none of that is here), no Physics Asset. Scale is a guess from the sprite: 3.4 m at the head, 6.7 m wingspan.')


def main(mode):
    L.reset(); asset = 'SK_Dragon_PR'; outdir = os.path.join(L.UNC, 'dragon', 'Dragon'); hi = build_hi(L.coll('Source_Hi'))
    R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.35, exposure=-5.0, ground_size=60)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=40, el=8, fill=1.1, lens=50, spp=192, dz=-0.2)
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, -1.2, 3.0), radius=0.9, az=48, el=2, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
        L.shot(R_, os.path.join(d, '%s_back.png' % tag), obs, az=205, el=14, fill=1.1, lens=50, res=(1000, 750), spp=128, dz=-0.2)
    if mode == 'review':
        shots(hi, 'Dragon_hi', L.REVIEW); return
    lo = L.make_lo(hi, 24000, asset, L.coll(asset), angle=72, margin=0.003); arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset)); ids = L.origin_ids(['dragon'])
    C.finish_creature(asset, 'creature', lo, hi, arm, outdir, 2048, families=['dragon', '202-208 foes/dragon/f2-w'], origin=ids,
                      dresses='dragon standing upright on its hind legs, 3.4 m at the head with a 6.7 m wingspan: orange-brown scaled hide with a dark back and pale belly plates, long neck, horned head, green veined wing membranes reddening to the trailing edge, long tail, dorsal spines',
                      weaknesses=WEAK, script=SCRIPT + ' final', extrude=0.02, maxdist=0.05, extra={'contact_crop': 0.95})
    shots([lo], 'render', outdir)
    C.pose(arm, {'tail_02': (0, 0, 16), 'tail_03': (0, 0, 20), 'tail_04': (0, 0, 20), 'neck_01': (0, 0, -14), 'neck_02': (0, 0, -12), 'head': (12, 0, -10), 'wing_01_l': (0, 22, 0), 'wing_01_r': (0, -22, 0),
                 'thigh_l': (-20, 0, 0), 'calf_l': (18, 0, 0), 'upperarm_l': (-30, 0, 0)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=40, el=8, fill=1.1, lens=50, res=(1000, 750), spp=128, dz=-0.2); C.pose(arm, {}); L.save_blend()


if __name__ == '__main__':
    a = L.args(); main(a[0] if a else 'review')
