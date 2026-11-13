"""goblin_soldier (801-809 foes/goblin/soldier/walk) and goblin_hammer (761-769 foes/goblin/hammer/walk): one goblin body,
two kits, on the bone names of the project humanoid skeleton.

    tools/bl.sh build_goblin.py <Soldier|Hammer|all> [review|final]
"""
import bpy, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L
import creature as C
import build_tools as T
import build_bonca as B
from pplib import NT, smoothstep, fbm

SCRIPT = 'build_goblin.py'
J = {'pelvis': (0, 0.02, 0.62), 'spine_01': (0, 0.025, 0.70), 'spine_02': (0, 0.03, 0.78), 'spine_03': (0, 0.02, 0.86), 'spine_04': (0, 0.01, 0.94), 'spine_05': (0, 0.0, 1.01), 'neck_01': (0, -0.02, 1.07), 'neck_02': (0, -0.04, 1.12),
     'head': (0, -0.07, 1.20), 'head_top': (0, -0.07, 1.34), 'jaw': (0, -0.15, 1.12), 'nose': (0, -0.225, 1.19), 'brow': (0, -0.17, 1.245)}
R = {'pelvis': (0.15, 0.12, 0.12), 'spine_01': (0.16, 0.125, 0.1), 'spine_02': (0.17, 0.13, 0.1), 'spine_03': (0.185, 0.14, 0.1), 'spine_04': (0.2, 0.15, 0.11), 'spine_05': (0.19, 0.14, 0.1), 'neck_01': 0.075, 'neck_02': 0.07,
     'head': (0.125, 0.14, 0.125), 'jaw': (0.09, 0.085, 0.06), 'nose': (0.032, 0.06, 0.034), 'brow': (0.105, 0.05, 0.03)}
E = [('pelvis', 'spine_01'), ('spine_01', 'spine_02'), ('spine_02', 'spine_03'), ('spine_03', 'spine_04'), ('spine_04', 'spine_05'), ('spine_05', 'neck_01'), ('neck_01', 'neck_02'), ('neck_02', 'head'), ('head', 'jaw'), ('head', 'nose'), ('head', 'brow')]
for s, sx in (('l', 1), ('r', -1)):
    J.update({'clav_' + s: (0.06 * sx, 0, 1.02), 'shoulder_' + s: (0.22 * sx, 0.0, 1.0), 'elbow_' + s: (0.30 * sx, -0.04, 0.75), 'wrist_' + s: (0.30 * sx, -0.17, 0.53), 'hand_' + s: (0.30 * sx, -0.21, 0.45),
              'hip_' + s: (0.11 * sx, 0.02, 0.58), 'knee_' + s: (0.155 * sx, -0.09, 0.33), 'ankle_' + s: (0.14 * sx, 0.02, 0.09), 'ball_' + s: (0.15 * sx, -0.1, 0.04), 'toe_' + s: (0.155 * sx, -0.2, 0.035),
              'ear_' + s: (0.15 * sx, -0.03, 1.235), 'eartip_' + s: (0.28 * sx, 0.02, 1.3)})
    R.update({'shoulder_' + s: 0.088, 'elbow_' + s: 0.06, 'wrist_' + s: 0.05, 'hand_' + s: (0.055, 0.06, 0.065), 'hip_' + s: (0.105, 0.11, 0.12), 'knee_' + s: 0.075, 'ankle_' + s: 0.058, 'ball_' + s: (0.065, 0.09, 0.045), 'toe_' + s: (0.06, 0.05, 0.035),
              'ear_' + s: (0.05, 0.02, 0.055), 'eartip_' + s: (0.02, 0.012, 0.02)})
    E += [('spine_05', 'shoulder_' + s), ('shoulder_' + s, 'elbow_' + s), ('elbow_' + s, 'wrist_' + s), ('wrist_' + s, 'hand_' + s), ('pelvis', 'hip_' + s), ('hip_' + s, 'knee_' + s), ('knee_' + s, 'ankle_' + s), ('ankle_' + s, 'ball_' + s),
          ('ball_' + s, 'toe_' + s), ('head', 'ear_' + s), ('ear_' + s, 'eartip_' + s)]
BONES = [('root', (0, 0, 0), (0, 0.1, 0), None), ('pelvis', 'pelvis', 'spine_01', 'root')] + [('spine_%02d' % i, 'spine_%02d' % i, 'spine_%02d' % (i + 1) if i < 5 else 'neck_01', 'pelvis' if i == 1 else 'spine_%02d' % (i - 1)) for i in range(1, 6)] + \
        [('neck_01', 'neck_01', 'neck_02', 'spine_05'), ('neck_02', 'neck_02', 'head', 'neck_01'), ('head', 'head', 'head_top', 'neck_02')]
for s in 'lr':
    BONES += [('clavicle_' + s, 'clav_' + s, 'shoulder_' + s, 'spine_05'), ('upperarm_' + s, 'shoulder_' + s, 'elbow_' + s, 'clavicle_' + s), ('lowerarm_' + s, 'elbow_' + s, 'wrist_' + s, 'upperarm_' + s), ('hand_' + s, 'wrist_' + s, 'hand_' + s, 'lowerarm_' + s),
              ('thigh_' + s, 'hip_' + s, 'knee_' + s, 'pelvis'), ('calf_' + s, 'knee_' + s, 'ankle_' + s, 'thigh_' + s), ('foot_' + s, 'ankle_' + s, 'ball_' + s, 'calf_' + s), ('ball_' + s, 'ball_' + s, 'toe_' + s, 'foot_' + s)]


def body_mat(cloth_cols, boot=(0.035, 0.022, 0.013), scales=False):
    """green warty skin; tunic and breeches by region (attribute `cloth`), boots (attribute `boot`); the soldier's coat carries iron scales"""
    t = NT('goblin'); cl = t.attr('cloth'); bt = t.attr('boot'); mouth = t.attr('mouth'); n = t.noise(14, 5, 0.65); n2 = t.noise(120, 4, 0.6); cell = t.voronoi(240, feature='DISTANCE_TO_EDGE'); nz = t.sep(t.gnormal)[2]
    wart = t.ramp(t.voronoi(90, feature='F1'), [(0.0, 1.0), (0.14, 0.0)]); skin = t.ramp(n, [(0.25, (0.045, 0.085, 0.022)), (0.55, (0.085, 0.15, 0.04)), (0.85, (0.15, 0.22, 0.07))]); skin = t.mix(t.math('MULTIPLY', wart, 0.4), skin, (0.19, 0.21, 0.10))
    skin = t.mix(t.math('MULTIPLY', t.ramp(cell, [(0.0, 1.0), (0.1, 0.0)]), 0.35), skin, (0.02, 0.035, 0.012)); skin = t.mix(mouth, skin, (0.06, 0.012, 0.012))
    weave = t.math('MULTIPLY', t.math('SINE', t.math('MULTIPLY', t.sep(t.obj)[2], 1500.0)), t.math('SINE', t.math('MULTIPLY', t.math('ARCTAN2', t.sep(t.obj)[1], t.sep(t.obj)[0]), 160.0)))
    cloth = t.mix(n, cloth_cols[0], cloth_cols[1]); cloth = t.mix(t.math('MULTIPLY', t.ramp(t.noise(7, 5, 0.7), [(0.5, 0.0), (0.75, 1.0)]), 0.5), cloth, (0.03, 0.025, 0.018)); metal = t.val(0.0); h = t.math('MULTIPLY', weave, 0.3)
    if scales:
        sc = t.voronoi(1.0, vec=t.mapping(scale=(46, 46, 30)), feature='DISTANCE_TO_EDGE'); sedge = t.ramp(sc, [(0.0, 1.0), (0.12, 0.0)]); cloth = t.mix(t.math('MULTIPLY', sedge, 0.8), t.mix(n2, (0.05, 0.06, 0.08), (0.16, 0.18, 0.22)), (0.012, 0.012, 0.015))
        rust = t.ramp(t.noise(18, 4, 0.7), [(0.6, 0.0), (0.72, 1.0)]); cloth = t.mix(t.math('MULTIPLY', rust, 0.6), cloth, (0.11, 0.05, 0.02)); metal = t.math('MULTIPLY', cl, t.math('MULTIPLY', t.math('SUBTRACT', 1.0, sedge), 0.85)); h = t.ramp(sc, [(0.0, 0.0), (0.3, 1.0)])
    base = t.mix(cl, skin, cloth); base = t.mix(bt, base, t.mix(n2, boot, tuple(v * 2.2 for v in boot))); ao = t.ao(0.03, 10); base = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.85, 0.0)]), 0.7), base, (0.012, 0.012, 0.01))
    rough = t.mixf(cl, t.mixf(n2, 0.4, 0.6), 0.5 if scales else 0.85); rough = t.mixf(bt, rough, 0.55)
    nrm = t.bump(t.mixf(cl, t.math('ADD', t.math('MULTIPLY', wart, 1.0), t.math('MULTIPLY', t.ramp(cell, [(0.0, 0.0), (0.3, 1.0)]), 0.5)), h), 0.6, 0.0015)
    t.set(base=base, rough=rough, metal=metal, normal=nrm, sss=0.05, sss_scale=0.006); return t.mat


def goblin(kind, c):
    body = C.graph_body('body', J, E, R, c, voxel=0.006, smooth=8); L.subsurf(body, 1); Pq = L.co(body); N = L.vnormals(body); x, y, z = Pq[:, 0], Pq[:, 1], Pq[:, 2]
    mouth = np.exp(-((z - (1.125 - 0.6 * x * x)) / 0.008) ** 2) * smoothstep(-0.16, -0.2, y) * (1 - smoothstep(0.065, 0.08, np.abs(x)))
    eye = np.exp(-(((np.abs(x) - 0.05) / 0.022) ** 2 + ((z - 1.215) / 0.014) ** 2)) * smoothstep(-0.14, -0.18, y)
    torso = smoothstep(0.50, 0.54, z) * (1 - smoothstep(1.03, 1.06, z)) * (1 - smoothstep(0.21, 0.25, np.abs(x) - 0.04 * smoothstep(0.9, 1.0, z))); breeches = smoothstep(0.26, 0.3, z) * (1 - smoothstep(0.5, 0.54, z)) * (1 - smoothstep(0.215, 0.235, np.abs(x)))
    skirt = smoothstep(0.42, 0.46, z) * (1 - smoothstep(0.5, 0.56, z)) * (1 - smoothstep(0.215, 0.235, np.abs(x))); cloth = np.clip(torso + breeches, 0, 1); boot = 1 - smoothstep(0.2, 0.23, z)
    fold = 0.004 * np.sin(z * 55 + 3 * np.sin(x * 20)) * cloth; puff = 0.012 * cloth + 0.014 * skirt + 0.008 * boot
    L.set_co(body, Pq + N * (puff + fold - 0.012 * mouth - 0.014 * eye + 0.0025 * fbm(Pq, 5, 26, 3) * (1 - cloth))[:, None])
    C.set_attr(body, 'cloth', cloth); C.set_attr(body, 'boot', boot); C.set_attr(body, 'mouth', np.clip(mouth, 0, 1))
    soldier = kind == 'Soldier'
    body.data.materials.append(body_mat(((0.05, 0.06, 0.08), (0.12, 0.14, 0.18)), scales=True) if soldier else body_mat(((0.10, 0.055, 0.025), (0.24, 0.14, 0.065))))
    parts = [body]; im = T.iron_mat('iron', rust=0.5, seed=5.0 if soldier else 9.0); hm = B.tooth_mat(); wm = T.wood_mat('shaft', axis=2, light=(0.24, 0.14, 0.06), dark=(0.085, 0.045, 0.02))
    t = NT('eye'); nrm = t.sep(t.gnormal); t.set(base=t.mix(t.ramp(t.math('MULTIPLY', nrm[1], -1.0), [(0.86, 0.0), (0.9, 1.0)]), (0.62, 0.42, 0.04), (0.01, 0.008, 0.005)), rough=0.06, coat=1.0, coat_rough=0.03)
    for sx in (1, -1):
        hit = C.surface_hit(body, (0.05 * sx, -1.0, 1.215), (0, 1, 0)); ey = (hit[0][1] if hit else -0.2) + 0.012; e = C.ball('eye', (0.05 * sx, ey, 1.215), 0.017, c, seg=14, squash=(1, 0.8, 0.85)); e.data.materials.append(t.mat); parts.append(e)
        hit = C.surface_hit(body, (0.045 * sx, -1.0, 1.118), (0, 1, 0)); ty = (hit[0][1] if hit else -0.2) + 0.008; tk = C.cone('tusk', (0.045 * sx, ty, 1.112), (0.05 * sx, ty - 0.012, 1.15), 0.0085, c, nu=8, nv=5); tk.data.materials.append(hm); parts.append(tk)
    hr = np.array(J['hand_r']); hl = np.array(J['hand_l'])
    if soldier:
        helm = L.sweep('helm', [(0, -0.07, 1.25, 0.134, 0.15, 2.2), (0, -0.07, 1.295, 0.136, 0.152, 2.2), (0, -0.07, 1.35, 0.108, 0.123, 2.1), (0, -0.07, 1.39, 0.05, 0.06, 2.0)], nu=48, nv=30, c=c, up=(0, 1, 0), cap=0.5)
        crest = L.sweep('crest', [(0, 0.07, 1.30, 0.008, 0.02, 3), (0, 0.03, 1.40, 0.009, 0.03, 3), (0, -0.07, 1.44, 0.009, 0.035, 3), (0, -0.17, 1.40, 0.008, 0.025, 3), (0, -0.21, 1.33, 0.006, 0.014, 3)], nu=20, nv=40, c=c, up=(1, 0, 0), cap=0.4)
        nasal = L.sweep('nasal', [(0, -0.215, 1.29, 0.014, 0.005, 4), (0, -0.262, 1.22, 0.012, 0.005, 4), (0, -0.275, 1.17, 0.009, 0.004, 4)], nu=16, nv=16, c=c, up=(0, 1, 0), cap=0.5)
        shield = L.lathe('shield', [(0, 0.0), (0.07, 0.004), (0.09, 0.03), (0.3, 0.055), (0.335, 0.06), (0.335, 0.075), (0.3, 0.07), (0.09, 0.05), (0.06, 0.075), (0, 0.085)], seg=64, c=c, cap0=False, cap1=False); L.subsurf(shield, 1)
        from mathutils import Matrix
        L.xform(shield, Matrix.Translation((hl[0] + 0.1, hl[1] - 0.02, hl[2] + 0.2)) @ Matrix.Rotation(math.radians(-80), 4, 'Y') @ Matrix.Rotation(math.radians(8), 4, 'X'))
        pole = L.sweep('pole', [(hr[0], hr[1] - 0.01, 0.0, 0.015, 0.015, 2.1), (hr[0], hr[1] - 0.01, 0.9, 0.016, 0.016, 2.1), (hr[0], hr[1] - 0.01, 1.78, 0.014, 0.014, 2.1)], nu=30, nv=60, c=c, up=(0, 1, 0), cap=0.7)
        blade = L.sweep('blade', [(hr[0] + 0.005, hr[1] - 0.01, 1.6, 0.006, 0.03, 4), (hr[0] - 0.08, hr[1] - 0.01, 1.62, 0.005, 0.07, 3.4), (hr[0] - 0.17, hr[1] - 0.01, 1.64, 0.0012, 0.105, 3)], nu=30, nv=30, c=c, up=(0, 0, 1), cap=0.3)          # the bill faces outwards, not forwards
        spike = L.sweep('spike', [(hr[0], hr[1] - 0.01, 1.74, 0.014, 0.014, 4), (hr[0], hr[1] - 0.01, 1.86, 0.009, 0.009, 4), (hr[0], hr[1] - 0.01, 2.02, 0.001, 0.001, 3)], nu=20, nv=24, c=c, up=(0, 1, 0), cap=0.3)
        sm = NT('shield'); sp = sm.sep(sm.obj); n = sm.noise(40, 5, 0.65); gr = sm.noise(1.0, 5, 0.65, vec=sm.mapping(scale=(50, 50, 2.5))); col = sm.mix(gr, (0.05, 0.03, 0.014), (0.16, 0.09, 0.04)); sm.set(base=col, rough=sm.mixf(n, 0.5, 0.75), normal=sm.bump(gr, 0.4, 0.001))
        for o, m in ((helm, im), (crest, im), (nasal, im), (shield, sm.mat), (pole, wm), (blade, im), (spike, im)):
            o.data.materials.append(m); parts.append(o)
    else:
        cap = L.sweep('cap', [(0, -0.07, 1.235, 0.132, 0.147, 2.2), (0, -0.07, 1.29, 0.13, 0.145, 2.2), (0, -0.07, 1.34, 0.095, 0.11, 2.1), (0, -0.07, 1.365, 0.03, 0.04, 2.0)], nu=48, nv=30, c=c, up=(0, 1, 0), cap=0.5)
        lt = NT('leather'); n = lt.noise(60, 4, 0.6); cr = lt.voronoi(200, feature='DISTANCE_TO_EDGE'); col = lt.mix(n, (0.035, 0.018, 0.009), (0.11, 0.058, 0.026)); col = lt.mix(lt.ramp(cr, [(0.0, 0.6), (0.08, 0.0)]), col, (0.012, 0.007, 0.004))
        lt.set(base=col, rough=lt.mixf(n, 0.45, 0.7), normal=lt.bump(lt.ramp(cr, [(0.0, 0.0), (0.12, 1.0)]), 0.4, 0.001)); cap.data.materials.append(lt.mat); parts.append(cap)
        shaft = L.sweep('shaft', [(hr[0], hr[1] - 0.01, 0.12, 0.018, 0.018, 2.2), (hr[0], hr[1] - 0.01, 0.6, 0.02, 0.02, 2.2), (hr[0], hr[1] - 0.01, 1.18, 0.02, 0.02, 2.2)], nu=30, nv=50, c=c, up=(0, 1, 0), cap=0.7)
        head = L.sweep('hammer', [(hr[0], hr[1] - 0.2, 1.1, 0.07, 0.07, 7), (hr[0], hr[1] - 0.17, 1.1, 0.082, 0.082, 7), (hr[0], hr[1] - 0.01, 1.1, 0.085, 0.085, 6), (hr[0], hr[1] + 0.15, 1.1, 0.082, 0.082, 7), (hr[0], hr[1] + 0.18, 1.1, 0.07, 0.07, 7)], nu=48, nv=40, c=c, up=(0, 0, 1), cap=0.8)
        L.displace_np(head, lambda Q: 0.0006 * fbm(Q, 3, 40, 3)); shaft.data.materials.append(wm); head.data.materials.append(im); parts += [shaft, head]
    zmin = min(L.co(o)[:, 2].min() for o in parts)           # stand it on the ground: the puffed boots must not dip below the pivot plane
    for o in parts:
        Pq = L.co(o); Pq[:, 2] -= zmin; L.set_co(o, Pq)
    return parts


WEAK = ('NOT photoreal at 1 m: a fused blob figure. Clothing is the body surface puffed out and recoloured by region, not separate garments, so there are no hems, belts, buckles or layered edges; the face is pressed-in eyes and mouth with ball eyes and two tusks, without lids or nostrils. '
        'Hands are mittens: the weapon passes through the fist. Helmet, weapon and shield are skinned by nearest bone with the same automatic weights as the body (they should be rigid attachments on sockets). '
        'Decimated game mesh without joint loops; one test pose; no animation clips, no Physics Asset. Rest pose is a standing guard pose, not the A pose of the Manny skeleton.')
KITS = {'Soldier': dict(fam='goblin_soldier', seq='801-809 foes/goblin/soldier/walk', dresses='goblin soldier, 1.35 m (2.0 m to the spike of his polearm): green warty skin, iron scale coat, crested helmet with a nasal, round wooden shield with an iron boss on the left arm, a bill in the right hand'),
        'Hammer': dict(fam='goblin_hammer', seq='761-769 foes/goblin/hammer/walk', dresses='goblin with a war hammer, 1.37 m: green warty skin, brown tunic and breeches, leather skullcap, a square-headed iron hammer on a 1.1 m shaft in the right hand')}


def main(kind, mode):
    L.reset(); asset = 'SK_Goblin_%s_PR' % kind; kt = KITS[kind]; outdir = os.path.join(L.UNC, kt['fam'], 'Goblin_' + kind); hi = goblin(kind, L.coll('Source_Hi'))
    R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=30, el=8, fill=1.15, lens=70, spp=192, res=(900, 1200), dz=0.05)
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, -0.08, 1.15), radius=0.3, az=26, el=4, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
    if mode == 'review':
        shots(hi, 'Goblin_%s_hi' % kind, L.REVIEW); return
    lo = L.make_lo(hi, 14000, asset, L.coll(asset), angle=72, margin=0.004); arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset)); ids = L.origin_ids([kt['fam']])
    C.finish_creature(asset, 'character_humanoid', lo, hi, arm, outdir, 2048, families=[kt['fam'], kt['seq']], origin=ids, dresses=kt['dresses'], weaknesses=WEAK, script=SCRIPT + ' ' + kind + ' final', extrude=0.008, maxdist=0.02,
                      lod_ratios=(0.5, 0.25, 0.12), third_party=['rusty_metal_02'], extra={'contact_crop': 0.95, 'skeleton_note': 'bone names and hierarchy of the project humanoid core set (CONVENTIONS.md section 11), goblin proportions'})
    shots([lo], 'render', outdir)
    C.pose(arm, {'upperarm_l': (0, 0, -30), 'lowerarm_l': (-35, 0, 0), 'thigh_l': (-28, 0, 0), 'calf_l': (30, 0, 0), 'thigh_r': (14, 0, 0), 'head': (0, 0, 22), 'spine_03': (0, 0, 8)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=30, el=8, fill=1.15, lens=70, res=(750, 1000), spp=128, dz=0.05); C.pose(arm, {}); L.save_blend()


if __name__ == '__main__':
    a = L.args(); kinds = list(KITS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for k in kinds:
        main(k, mode)
