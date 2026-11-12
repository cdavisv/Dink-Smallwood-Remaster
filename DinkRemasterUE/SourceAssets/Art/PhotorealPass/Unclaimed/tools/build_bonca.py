"""bonca_gray (601-609 walk, 592-598 attack), bonca_brown (531-544) and bonca_purple (613-628): one creature, three hides.

The bonca of the sprites is a hunched, neckless biped: a heavy humped trunk with the face set low in its front,
two stout clawed legs under the hump and a thick tail held out behind. Built from a joint graph (Skin modifier,
voxel remesh), folded and wrinkled by displacement, rigged on the same joints.

    tools/bl.sh build_bonca.py [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_bonca.py'
J = {'pelvis': (0, 0.30, 0.80), 'spine1': (0, 0.04, 0.96), 'hump': (0, -0.22, 1.08), 'chest': (0, -0.46, 0.97), 'head': (0, -0.66, 0.80), 'snout': (0, -0.80, 0.71),
     'brow_l': (0.13, -0.785, 0.905), 'brow_r': (-0.13, -0.785, 0.905),
     'tail1': (0, 0.56, 0.82), 'tail2': (0, 0.84, 0.90), 'tail3': (0, 1.12, 1.01), 'tail4': (0, 1.38, 1.10), 'tail5': (0, 1.62, 1.14)}
R = {'pelvis': (0.25, 0.27), 'spine1': (0.33, 0.33), 'hump': (0.37, 0.36), 'chest': (0.32, 0.31), 'head': (0.245, 0.23), 'snout': (0.165, 0.135), 'brow_l': (0.08, 0.07, 0.04), 'brow_r': (0.08, 0.07, 0.04),
     'tail1': 0.19, 'tail2': 0.14, 'tail3': 0.10, 'tail4': 0.07, 'tail5': 0.04}
E = [('pelvis', 'spine1'), ('spine1', 'hump'), ('hump', 'chest'), ('chest', 'head'), ('head', 'snout'), ('head', 'brow_l'), ('head', 'brow_r'),
     ('pelvis', 'tail1'), ('tail1', 'tail2'), ('tail2', 'tail3'), ('tail3', 'tail4'), ('tail4', 'tail5')]
for s, sx in (('l', 1), ('r', -1)):
    J.update({'hip_' + s: (0.25 * sx, -0.10, 0.68), 'knee_' + s: (0.31 * sx, -0.30, 0.40), 'ankle_' + s: (0.29 * sx, -0.12, 0.13), 'foot_' + s: (0.30 * sx, -0.30, 0.055),
              'toe1_' + s: (0.21 * sx, -0.47, 0.04), 'toe2_' + s: (0.31 * sx, -0.50, 0.04), 'toe3_' + s: (0.41 * sx, -0.45, 0.04), 'heel_' + s: (0.29 * sx, -0.02, 0.045)})
    R.update({'hip_' + s: (0.18, 0.21, 0.2), 'knee_' + s: 0.105, 'ankle_' + s: 0.07, 'foot_' + s: (0.085, 0.06), 'toe1_' + s: 0.036, 'toe2_' + s: 0.04, 'toe3_' + s: 0.036, 'heel_' + s: 0.045})
    E += [('spine1', 'hip_' + s), ('hip_' + s, 'knee_' + s), ('knee_' + s, 'ankle_' + s), ('ankle_' + s, 'foot_' + s), ('foot_' + s, 'toe1_' + s), ('foot_' + s, 'toe2_' + s), ('foot_' + s, 'toe3_' + s),
          ('ankle_' + s, 'heel_' + s)]

BONES = [('root', (0, 0, 0), (0, 0.12, 0), None), ('pelvis', 'pelvis', 'spine1', 'root'), ('spine_01', 'spine1', 'hump', 'pelvis'), ('spine_02', 'hump', 'chest', 'spine_01'),
         ('spine_03', 'chest', 'head', 'spine_02'), ('head', 'head', 'snout', 'spine_03'),
         ('tail_01', 'pelvis', 'tail1', 'pelvis'), ('tail_02', 'tail1', 'tail2', 'tail_01'), ('tail_03', 'tail2', 'tail3', 'tail_02'), ('tail_04', 'tail3', 'tail4', 'tail_03'), ('tail_05', 'tail4', 'tail5', 'tail_04')]
for s in 'lr':
    BONES += [('thigh_' + s, 'hip_' + s, 'knee_' + s, 'pelvis'), ('calf_' + s, 'knee_' + s, 'ankle_' + s, 'thigh_' + s), ('foot_' + s, 'ankle_' + s, 'foot_' + s, 'calf_' + s),
              ('ball_' + s, 'foot_' + s, 'toe2_' + s, 'foot_' + s)]


def hide_mat():
    t = NT('hide'); fold = t.attr('fold'); mouth = t.attr('mouth'); n1 = t.noise(7, 5, 0.65); n2 = t.noise(38, 4, 0.6, distortion=0.5); nz = t.sep(t.gnormal)[2]
    cell = t.voronoi(170, feature='DISTANCE_TO_EDGE'); scale_edge = t.ramp(cell, [(0.0, 1.0), (0.09, 0.0)]); cellv = t.voronoi(170, out='Color')
    base = t.ramp(n1, [(0.25, (0.028, 0.036, 0.030)), (0.55, (0.070, 0.085, 0.066)), (0.85, (0.115, 0.125, 0.095))])
    base = t.hsv(base, v=t.maprange(t.sep(cellv)[0], 0, 1, 0.8, 1.2))
    ridge = t.math('MULTIPLY', t.ramp(fold, [(0.45, 0.0), (0.9, 1.0)]), t.maprange(nz, -0.2, 0.6, 0.15, 1.0)); ridge = t.math('MULTIPLY', ridge, t.ramp(n2, [(0.2, 0.45), (0.7, 1.0)]))
    base = t.mix(t.math('MULTIPLY', t.math('MULTIPLY', ridge, t.maprange(t.sep(cellv)[1], 0, 1, 0.45, 1.0)), 0.7), base, t.mix(n2, (0.17, 0.19, 0.15), (0.30, 0.31, 0.25)))                         # pale banding on the fold crests
    belly = t.maprange(nz, -0.75, -0.15, 1.0, 0.0, interp='SMOOTHSTEP'); base = t.mix(t.math('MULTIPLY', belly, 0.7), base, t.mix(n2, (0.17, 0.165, 0.125), (0.27, 0.25, 0.19)))
    moss = t.ramp(t.noise(4.3, 4, 0.6, vec=t.mapping(loc=(3, 7, 1))), [(0.56, 0.0), (0.7, 1.0)]); base = t.mix(t.math('MULTIPLY', moss, 0.45), base, (0.05, 0.10, 0.035))
    ao = t.ao(0.05, 12); crease = t.ramp(ao, [(0.35, 1.0), (0.8, 0.0)]); base = t.mix(t.math('MULTIPLY', crease, 0.75), base, (0.016, 0.016, 0.014))
    base = t.mix(t.math('MULTIPLY', scale_edge, 0.5), base, (0.015, 0.018, 0.015)); base = t.mix(mouth, base, t.mix(n2, (0.035, 0.008, 0.008), (0.10, 0.02, 0.018)))
    rough = t.mixf(ridge, t.mixf(n2, 0.48, 0.66), 0.42); rough = t.math('ADD', rough, t.math('MULTIPLY', scale_edge, 0.25)); rough = t.mixf(mouth, rough, 0.25)
    h = t.math('ADD', t.math('MULTIPLY', t.ramp(cell, [(0.0, 0.0), (0.25, 1.0)]), 0.7), t.math('MULTIPLY', t.noise(420, 3, 0.6), 0.3))
    nrm = t.bump(t.noise(60, 4, 0.65, distortion=0.8), 0.3, 0.005, normal=t.bump(h, 0.85, 0.0022))
    t.set(base=base, rough=rough, normal=nrm, spec=0.6)
    return t.mat


def horn_mat():
    t = NT('horn'); n = t.noise(40, 4, 0.6); fib = t.noise(3, 3, 0.6, vec=t.mapping(scale=(150, 150, 12)))
    base = t.mix(t.math('MULTIPLY', t.ramp(t.pointiness, [(0.5, 0.0), (0.62, 1.0)]), 0.8), t.mix(fib, (0.03, 0.025, 0.02), (0.11, 0.09, 0.065)), (0.42, 0.36, 0.26))
    t.set(base=base, rough=t.mixf(n, 0.3, 0.55), normal=t.bump(fib, 0.3, 0.0008)); return t.mat


def eye_mat():
    """amber iris with a vertical slit pupil looking forward (-Y), dark rim, wet cornea"""
    t = NT('eye'); nrm = t.sep(t.gnormal); fwd = t.math('MULTIPLY', nrm[1], -1.0); slit = t.math('MULTIPLY', t.ramp(t.math('ABSOLUTE', nrm[0]), [(0.07, 1.0), (0.13, 0.0)]), t.ramp(fwd, [(0.55, 0.0), (0.7, 1.0)]))
    fib = t.noise(3.0, 3, 0.6, vec=t.mapping(scale=(40, 4, 40))); iris = t.mix(fib, (0.20, 0.085, 0.012), (0.48, 0.27, 0.04)); rim = t.ramp(fwd, [(0.35, 1.0), (0.62, 0.0)])
    base = t.mix(rim, iris, (0.02, 0.012, 0.008)); base = t.mix(slit, base, (0.004, 0.004, 0.004)); t.set(base=base, rough=0.05, spec=0.8, coat=1.0, coat_rough=0.02); return t.mat


def tooth_mat():
    t = NT('tooth'); n = t.noise(90, 3, 0.6); t.set(base=t.mix(n, (0.42, 0.36, 0.24), (0.66, 0.62, 0.48)), rough=t.mixf(n, 0.25, 0.45), sss=0.1, sss_scale=0.003); return t.mat


def build_hi(c):
    body = C.graph_body('body', J, E, R, c, voxel=0.011, smooth=14); L.subsurf(body, 1)
    P = L.co(body); N = L.vnormals(body); x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # mouth: a wide slit low in the face, corners pulled up and back
    zm = 0.675 - 0.9 * x * x; mouth = np.exp(-((z - zm) / 0.014) ** 2) * smoothstep(-0.56, -0.68, y) * (1 - smoothstep(0.17, 0.21, np.abs(x)))
    # folds: thick bands of hide wrapping the trunk and tail across the spine, warped; rings on the legs
    w = fbm(P, 3, 1.6, 3); w2 = fbm(P, 5, 4.5, 2); s_trunk = y + 0.33 * z + 0.34 * w + 0.06 * w2; s_leg = z + 0.10 * w
    legm = smoothstep(0.62, 0.50, z) * smoothstep(0.12, 0.2, np.abs(x)) * smoothstep(0.28, 0.1, y)
    band = 0.5 + 0.5 * np.sin(2 * np.pi * (s_trunk / (0.12 + 0.03 * w2))); bandl = 0.5 + 0.5 * np.sin(2 * np.pi * (s_leg / 0.075))
    brk = smoothstep(-0.25, 0.25, fbm(P, 7, 3.0, 2)); band = band * (0.35 + 0.65 * brk) + 0.5 * (1 - (0.35 + 0.65 * brk)) * 0.6
    fold = (band ** 0.7) * (1 - legm) + (bandl ** 0.7) * legm
    amp = (0.004 + 0.011 * smoothstep(-0.3, 0.5, N[:, 2])) * (1 - 0.6 * legm) * (1 - smoothstep(-0.55, -0.7, y) * 0.8) * (1 - smoothstep(1.2, 1.6, y) * 0.7)
    lump = 0.007 * fbm(P, 11, 9, 3) + 0.004 * (1 - np.abs(fbm(P, 13, 26, 3))) ** 3 * -1 + 0.0015 * np.abs(fbm(P, 17, 90, 2))
    L.set_co(body, P + N * ((fold - 0.5) * 2 * amp + lump - 0.028 * mouth)[:, None])
    C.set_attr(body, 'fold', fold); C.set_attr(body, 'mouth', np.clip(mouth * 1.3, 0, 1)); body.data.materials.append(hide_mat())
    obs = [body]; hm = horn_mat(); em = eye_mat(); tm = tooth_mat()
    for sx in (1, -1):
        hit = C.surface_hit(body, (0.135 * sx, -1.5, 0.842), (0, 1, 0)); ey = (hit[0][1] if hit else -0.86) + 0.024            # sunk into the socket: only a shallow dome shows
        e = C.ball('eye', (0.135 * sx, ey, 0.842), 0.034, c, squash=(1, 0.9, 0.8)); e.data.materials.append(em); obs.append(e)
        for k, (tx, ty) in enumerate(((0.21, -0.47), (0.31, -0.50), (0.41, -0.45))):
            d = np.array([tx - 0.30, ty + 0.30, 0]); d /= np.linalg.norm(d)
            cl = C.cone('claw', (tx * sx, ty - 0.01, 0.045), ((tx + d[0] * 0.10) * sx, ty + d[1] * 0.11, 0.006), 0.027, c, bend=(0, 0, 0.035)); cl.data.materials.append(hm); obs.append(cl)
        sp = C.cone('spur', (0.29 * sx, 0.01, 0.05), (0.29 * sx, 0.085, 0.008), 0.03, c, bend=(0, 0, 0.03)); sp.data.materials.append(hm); obs.append(sp)
    for k in range(9):                                            # peg teeth along the lower lip
        tx = (k - 4) * 0.038; zt = 0.675 - 0.9 * tx * tx - 0.006; yt = -0.925 + 2.4 * tx * tx
        th = C.cone('tooth', (tx, yt + 0.012, zt - 0.004), (tx * 1.02, yt - 0.006, zt + 0.02 + 0.006 * (k % 2)), 0.0085, c, nu=8, nv=6); th.data.materials.append(tm); obs.append(th)
    return obs


def tint(bc, col, keep=0.3):
    lum = bc @ np.array([0.2126, 0.7152, 0.0722], np.float32); return bc * keep + (lum[..., None] ** 0.9) * np.array(col, np.float32) * 2.2 * (1 - keep)


WEAK = ('NOT photoreal at 1 m: it reads as a carefully lit maquette, smooth and rubbery, and passes only at gameplay distance. Anatomy is invented from 90-pixel sprites: a blob of a trunk on a joint graph, with no modelled musculature, knees or ankle tendons; folds are a sine band pattern, not sculpted. '
        'The face is two amber eye domes, a displaced slit and nine peg teeth; no lids, nostrils, gums or tongue, and the mouth cannot open (no jaw bone). '
        'The game mesh is a decimation of the remeshed source, so it has no edge loops at the joints: it will crease when the legs and tail bend far. '
        'Skin weights are inverse-distance to the bones (bone heat did not solve on the multi-shell mesh), checked in one test pose only (render_pose.png). No animation clips, no Physics Asset. Smart-projected UVs: many islands, so mip seams are possible. '
        'The brown and purple hides are tints of the grey base colour, not separately painted.')


def main(mode):
    L.reset(); asset = 'SK_Bonca_PR'; outdir = os.path.join(L.UNC, 'bonca_gray', 'Bonca'); hi = build_hi(L.coll('Source_Hi'))
    R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0)

    def shots(obs, tag, d, pose=False):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=38, el=14, fill=1.45, lens=60, spp=192)
        if not pose:
            L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, -0.72, 0.8), radius=0.42, az=28, el=8, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
            L.shot(R_, os.path.join(d, '%s_back.png' % tag), obs, az=205, el=22, fill=1.45, lens=60, res=(1000, 750), spp=128)
    if mode == 'review':
        print('BOUNDS', L.bounds(hi), [(o.name, [round(v, 2) for v in o.dimensions]) for o in hi if max(o.dimensions) > 3])
        shots(hi, 'Bonca_hi', L.REVIEW); return
    lo = L.make_lo(hi, 14000, asset, L.coll(asset), angle=72, margin=0.004)
    arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset))
    fams = {'bonca_gray': 'Gray', 'bonca_brown': 'Brown', 'bonca_purple': 'Purple'}; ids = L.origin_ids(list(fams))
    man, lods, files, vfiles = C.finish_creature(
        asset, 'creature', lo, hi, arm, outdir, 2048, families=list(fams) + ['601-609 foes/bonca/gray/walk', '592-598 foes/bonca/gray/attack', '531-544 foes/bonca', '613-628 foes/bonca/purple'], origin=ids,
        dresses='bonca: a hunched, neckless biped about 1.45 m at the hump and 2.5 m nose to tail tip; grey-green banded hide with pale fold crests, pale eyes low in the front of the trunk, wide slit mouth with peg teeth, three-clawed feet with a rear spur, thick tail',
        weaknesses=WEAK, script=SCRIPT + ' final', extrude=0.012, maxdist=0.035, ss=1,
        variants={'Brown': lambda bc: tint(bc, (0.52, 0.36, 0.22), keep=0.35), 'Purple': lambda bc: tint(bc, (0.40, 0.31, 0.50), keep=0.4)},
        extra={'colour_families': {'bonca_gray': 'T_Bonca_PR_BC.png', 'bonca_brown': 'T_Bonca_PR_Brown_BC.png', 'bonca_purple': 'T_Bonca_PR_Purple_BC.png'}, 'contact_crop': 0.9})
    shots([lo], 'render', outdir)
    C.pose(arm, {'tail_01': (0, 0, 14), 'tail_02': (0, 0, 20), 'tail_03': (0, 0, 24), 'tail_04': (0, 0, 24), 'thigh_l': (-28, 0, 0), 'calf_l': (30, 0, 0), 'thigh_r': (20, 0, 0), 'head': (0, 0, -14), 'spine_03': (0, 0, -8)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=38, el=14, fill=1.45, lens=60, res=(1000, 750), spp=128); C.pose(arm, {})
    # the two colour variants, side by side with the grey one
    for i, (suf, p) in enumerate(vfiles.items()):
        o = L.dup(lo, 'variant_' + suf, L.coll('Review')); o.modifiers.clear(); o.parent = None; o.location = ((i + 1) * 1.5, 0.3 * (i + 1), 0)
        o.data.materials.clear(); o.data.materials.append(L.game_material('MI_Bonca_PR_' + suf, dict(files, BC=p)))
    L.shot(R_, os.path.join(outdir, 'render_variants.png'), [lo] + [o for o in bpy.data.objects if o.name.startswith('variant_')], az=20, el=14, fill=1.3, lens=60, res=(1400, 700), spp=128)
    for o in [o for o in bpy.data.objects if o.name.startswith('variant_')]:
        bpy.data.objects.remove(o)
    L.save_blend()


if __name__ == '__main__':
    a = L.args(); main(a[0] if a else 'review')
