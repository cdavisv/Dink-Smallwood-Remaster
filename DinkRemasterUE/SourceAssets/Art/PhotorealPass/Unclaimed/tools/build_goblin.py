"""goblin_hammer (761-769), goblin_horned (781-789: Mog, script-made) and goblin_soldier (801-809): one goblin body under
three kits, on the bone names of the project humanoid skeleton.

Rebuilt 16 Nov 2026 (Fable packet GP-Q3). The first build was one blob with the clothes painted on it. Now the body is
bare skin (a heavy-shouldered, long-armed brute, olive, not cartoon green) and every garment is its own shell lifted off
it with a real hem: jerkin or scale coat, breeches, boots with cuffs, bracers, a belt; helmet, pauldrons, weapon and
shield are separate solids, and in the game mesh the gear is rigid: every vertex of the helmet rides `head`, of the
weapon `hand_r`, of the shield `lowerarm_l` (classified by the nearest source part, weight 1).

    tools/bl.sh build_goblin.py <Soldier|Hammer|Horned|all> [review|final]
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
J = {'pelvis': (0, 0.02, 0.62), 'spine_01': (0, 0.025, 0.70), 'spine_02': (0, 0.03, 0.78), 'spine_03': (0, 0.015, 0.86), 'spine_04': (0, -0.005, 0.94), 'spine_05': (0, -0.02, 1.01), 'neck_01': (0, -0.045, 1.07), 'neck_02': (0, -0.065, 1.12),
     'head': (0, -0.095, 1.20), 'head_top': (0, -0.095, 1.34), 'jaw': (0, -0.18, 1.115), 'nose': (0, -0.25, 1.185), 'brow': (0, -0.20, 1.245)}
R = {'pelvis': (0.16, 0.125, 0.12), 'spine_01': (0.17, 0.13, 0.1), 'spine_02': (0.18, 0.14, 0.1), 'spine_03': (0.20, 0.15, 0.1), 'spine_04': (0.225, 0.17, 0.12), 'spine_05': (0.215, 0.16, 0.11), 'neck_01': 0.095, 'neck_02': 0.088,
     'head': (0.125, 0.14, 0.125), 'jaw': (0.105, 0.095, 0.068), 'nose': (0.036, 0.06, 0.036), 'brow': (0.112, 0.055, 0.034)}
E = [('pelvis', 'spine_01'), ('spine_01', 'spine_02'), ('spine_02', 'spine_03'), ('spine_03', 'spine_04'), ('spine_04', 'spine_05'), ('spine_05', 'neck_01'), ('neck_01', 'neck_02'), ('neck_02', 'head'), ('head', 'jaw'), ('head', 'nose'), ('head', 'brow')]
for s, sx in (('l', 1), ('r', -1)):
    J.update({'clav_' + s: (0.07 * sx, -0.01, 1.02), 'shoulder_' + s: (0.26 * sx, -0.01, 1.0), 'elbow_' + s: (0.335 * sx, -0.05, 0.73), 'wrist_' + s: (0.335 * sx, -0.19, 0.50), 'hand_' + s: (0.335 * sx, -0.235, 0.42),
              'hip_' + s: (0.115 * sx, 0.02, 0.58), 'knee_' + s: (0.16 * sx, -0.09, 0.33), 'ankle_' + s: (0.145 * sx, 0.02, 0.09), 'ball_' + s: (0.155 * sx, -0.1, 0.04), 'toe_' + s: (0.16 * sx, -0.2, 0.035),
              'ear_' + s: (0.14 * sx, -0.05, 1.23), 'eartip_' + s: (0.205 * sx, 0.0, 1.27)})
    R.update({'shoulder_' + s: 0.108, 'elbow_' + s: 0.072, 'wrist_' + s: 0.058, 'hand_' + s: (0.062, 0.068, 0.075), 'hip_' + s: (0.11, 0.115, 0.125), 'knee_' + s: 0.08, 'ankle_' + s: 0.06, 'ball_' + s: (0.065, 0.09, 0.045), 'toe_' + s: (0.06, 0.05, 0.035),
              'ear_' + s: (0.045, 0.018, 0.05), 'eartip_' + s: (0.016, 0.01, 0.016)})
    E += [('spine_05', 'shoulder_' + s), ('shoulder_' + s, 'elbow_' + s), ('elbow_' + s, 'wrist_' + s), ('wrist_' + s, 'hand_' + s), ('pelvis', 'hip_' + s), ('hip_' + s, 'knee_' + s), ('knee_' + s, 'ankle_' + s), ('ankle_' + s, 'ball_' + s),
          ('ball_' + s, 'toe_' + s), ('head', 'ear_' + s), ('ear_' + s, 'eartip_' + s)]
BONES = [('root', (0, 0, 0), (0, 0.1, 0), None), ('pelvis', 'pelvis', 'spine_01', 'root')] + [('spine_%02d' % i, 'spine_%02d' % i, 'spine_%02d' % (i + 1) if i < 5 else 'neck_01', 'pelvis' if i == 1 else 'spine_%02d' % (i - 1)) for i in range(1, 6)] + \
        [('neck_01', 'neck_01', 'neck_02', 'spine_05'), ('neck_02', 'neck_02', 'head', 'neck_01'), ('head', 'head', 'head_top', 'neck_02')]
for s in 'lr':
    BONES += [('clavicle_' + s, 'clav_' + s, 'shoulder_' + s, 'spine_05'), ('upperarm_' + s, 'shoulder_' + s, 'elbow_' + s, 'clavicle_' + s), ('lowerarm_' + s, 'elbow_' + s, 'wrist_' + s, 'upperarm_' + s), ('hand_' + s, 'wrist_' + s, 'hand_' + s, 'lowerarm_' + s),
              ('thigh_' + s, 'hip_' + s, 'knee_' + s, 'pelvis'), ('calf_' + s, 'knee_' + s, 'ankle_' + s, 'thigh_' + s), ('foot_' + s, 'ankle_' + s, 'ball_' + s, 'calf_' + s), ('ball_' + s, 'ball_' + s, 'toe_' + s, 'foot_' + s)]
GEAR = {}                     # source part name -> bone it rides rigidly in the game mesh


def skin_mat():
    """olive goblin hide: mottled, warty, darker and browner in the creases, pale at lips and knuckles"""
    t = NT('goblin_skin'); mouth = t.attr('mouth'); n = t.noise(14, 5, 0.65); n2 = t.noise(120, 4, 0.6); cell = t.voronoi(260, feature='DISTANCE_TO_EDGE')
    wart = t.ramp(t.voronoi(95, feature='F1'), [(0.0, 1.0), (0.13, 0.0)]); skin = t.ramp(n, [(0.25, (0.030, 0.048, 0.016)), (0.55, (0.062, 0.090, 0.030)), (0.85, (0.110, 0.140, 0.052))])
    mott = t.ramp(t.noise(5.5, 4, 0.6, vec=t.mapping(loc=(3, 1, 7))), [(0.5, 0.0), (0.66, 1.0)]); skin = t.mix(t.math('MULTIPLY', mott, 0.55), skin, t.mix(n2, (0.050, 0.040, 0.018), (0.095, 0.075, 0.032)))
    skin = t.mix(t.math('MULTIPLY', wart, 0.35), skin, (0.13, 0.14, 0.07)); skin = t.mix(t.math('MULTIPLY', t.ramp(cell, [(0.0, 1.0), (0.1, 0.0)]), 0.4), skin, (0.014, 0.022, 0.009)); skin = t.mix(mouth, skin, (0.07, 0.014, 0.014))
    ao = t.ao(0.03, 10); skin = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.35, 1.0), (0.85, 0.0)]), 0.7), skin, (0.012, 0.012, 0.008))
    nrm = t.bump(t.math('ADD', wart, t.math('MULTIPLY', t.ramp(cell, [(0.0, 0.0), (0.3, 1.0)]), 0.5)), 0.6, 0.0016)
    t.set(base=skin, rough=t.mixf(n2, 0.38, 0.58), normal=nrm, sss=0.05, sss_scale=0.006); return t.mat


def leather_mat(name, dark, light, studs=False):
    """worn hide: creased, scuffed pale on the high spots, dark and greasy in the folds; optional iron studs"""
    t = NT(name); n = t.noise(55, 4, 0.6); n1 = t.noise(8, 5, 0.7); cr = t.voronoi(210, feature='DISTANCE_TO_EDGE'); col = t.mix(n1, dark, light)
    col = t.mix(t.ramp(cr, [(0.0, 0.6), (0.08, 0.0)]), col, tuple(v * 0.25 for v in dark)); col = t.mix(t.math('MULTIPLY', t.ramp(t.pointiness, [(0.52, 0.0), (0.62, 1.0)]), 0.5), col, tuple(min(1.0, v * 2.3) for v in light))
    ao = t.ao(0.02, 8); col = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.85, 0.0)]), 0.7), col, (0.008, 0.006, 0.004)); h = t.ramp(cr, [(0.0, 0.0), (0.12, 1.0)]); rough = t.mixf(n, 0.42, 0.7); metal = t.val(0.0)
    if studs:
        st = t.voronoi(1.0, vec=t.mapping(scale=(24, 24, 24)), feature='F1'); dot = t.ramp(st, [(0.0, 1.0), (0.11, 1.0), (0.14, 0.0)]); col = t.mix(dot, col, (0.20, 0.19, 0.17)); rough = t.mixf(dot, rough, 0.32); metal = t.math('MULTIPLY', dot, 0.9)
        h = t.math('ADD', h, t.math('MULTIPLY', dot, 2.0))
    t.set(base=col, rough=rough, metal=metal, normal=t.bump(h, 0.5, 0.0014)); return t.mat


def scale_mat():
    """the soldier's coat: rows of small iron scales, blued, rusted in patches, dark between them"""
    t = NT('scales'); n2 = t.noise(120, 4, 0.6); sc = t.voronoi(1.0, vec=t.mapping(scale=(46, 46, 30)), feature='DISTANCE_TO_EDGE'); sedge = t.ramp(sc, [(0.0, 1.0), (0.12, 0.0)])
    col = t.mix(t.math('MULTIPLY', sedge, 0.8), t.mix(n2, (0.045, 0.055, 0.075), (0.15, 0.17, 0.21)), (0.010, 0.010, 0.013)); rust = t.ramp(t.noise(18, 4, 0.7), [(0.6, 0.0), (0.72, 1.0)]); col = t.mix(t.math('MULTIPLY', rust, 0.6), col, (0.11, 0.05, 0.02))
    ao = t.ao(0.02, 8); col = t.mix(t.math('MULTIPLY', t.ramp(ao, [(0.4, 1.0), (0.85, 0.0)]), 0.6), col, (0.008, 0.008, 0.008))
    t.set(base=col, rough=t.mixf(n2, 0.36, 0.55), metal=t.math('MULTIPLY', t.math('SUBTRACT', 1.0, sedge), 0.85), normal=t.bump(t.ramp(sc, [(0.0, 0.0), (0.3, 1.0)]), 0.7, 0.002)); return t.mat


def shell(body, name, mask, offset, thick, c, mat, wrinkle=0.0035):
    """A garment: the part of the body surface where mask > 0.5, lifted off the skin by `offset` and given `thick` of its own, so
    it ends in a real hem. mask is per body vertex."""
    import bmesh
    o = L.dup(body, name, c); o.data.materials.clear(); bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if mask[v.index] < 0.5], context='VERTS'); bm.to_mesh(o.data); bm.free(); o.data.update()
    P = L.co(o); N = L.vnormals(o); L.set_co(o, P + N * (offset + wrinkle * np.sin(P[:, 2] * 60 + 3 * np.sin(P[:, 0] * 22) + 2 * np.sin(P[:, 1] * 17)) + 0.002 * fbm(P, 9, 14, 3))[:, None])
    L.mod(o, 'SMOOTH', factor=0.5, iterations=5); L.apply_mods(o)                    # a garment hangs: it does not show every muscle under it
    L.mod(o, 'SOLIDIFY', thickness=thick, offset=1.0); L.apply_mods(o); L.fix_normals(o); o.data.materials.append(mat); return o


def goblin(kind, c):
    GEAR.clear()
    body = C.graph_body('body', J, E, R, c, voxel=0.006, smooth=8); L.subsurf(body, 1); Pq = L.co(body); N = L.vnormals(body); x, y, z = Pq[:, 0], Pq[:, 1], Pq[:, 2]
    mouth = np.exp(-((z - (1.118 - 0.6 * x * x)) / 0.009) ** 2) * smoothstep(-0.19, -0.23, y) * (1 - smoothstep(0.075, 0.09, np.abs(x)))
    eye = np.exp(-(((np.abs(x) - 0.052) / 0.022) ** 2 + ((z - 1.213) / 0.014) ** 2)) * smoothstep(-0.17, -0.21, y)
    L.set_co(body, Pq + N * (-0.014 * mouth - 0.016 * eye + 0.003 * fbm(Pq, 5, 26, 3) + 0.004 * fbm(Pq, 7, 9, 2))[:, None])
    C.set_attr(body, 'mouth', np.clip(mouth, 0, 1)); body.data.materials.append(skin_mat())
    ax = np.abs(x); arm = smoothstep(0.245, 0.27, ax - 0.05 * smoothstep(0.92, 1.0, z))                       # 1 on the arms (outside the trunk)
    coat = (z > 0.44) & (z < 1.075 - 0.25 * np.maximum(0, 0.12 - ax)) & (arm < 0.5); breeches = (z > 0.25) & (z < 0.56) & (ax < 0.26) & (arm < 0.5); boots = z < 0.235
    bracer = (arm > 0.5) & (z > 0.50) & (z < 0.66)
    soldier = kind == 'Soldier'; horned = kind == 'Horned'
    im = T.iron_mat('iron', rust=0.5, seed={'Soldier': 5.0, 'Hammer': 9.0, 'Horned': 13.0}[kind]); hm = B.tooth_mat(); wm = T.wood_mat('shaft', axis=2, light=(0.24, 0.14, 0.06), dark=(0.085, 0.045, 0.02))
    boot_m = leather_mat('boot', (0.020, 0.012, 0.007), (0.060, 0.036, 0.018)); br_m = leather_mat('breeches', (0.035, 0.028, 0.018), (0.085, 0.066, 0.040)) if not soldier else leather_mat('breeches', (0.028, 0.030, 0.036), (0.070, 0.074, 0.085))
    coat_m = scale_mat() if soldier else leather_mat('jerkin', (0.032, 0.017, 0.008), (0.105, 0.056, 0.024), studs=True) if not horned else leather_mat('jerkin', (0.050, 0.014, 0.010), (0.130, 0.040, 0.022), studs=True)
    parts = [body, shell(body, 'breeches', breeches, 0.006, 0.006, c, br_m), shell(body, 'coat', coat, 0.020, 0.008 if soldier else 0.006, c, coat_m, wrinkle=0.002 if soldier else 0.0035),
             shell(body, 'boots', boots, 0.009, 0.007, c, boot_m, wrinkle=0.0015), shell(body, 'bracers', bracer, 0.007, 0.006, c, leather_mat('bracer', (0.022, 0.013, 0.007), (0.070, 0.040, 0.018), studs=True), wrinkle=0.001)]
    belt = L.ring('belt', 1.0, 0.022, c, seg=64, sides=10, squash=1.0, z=0.0); Pb = L.co(belt); Pb[:, 0] *= 0.212; Pb[:, 1] = Pb[:, 1] * 0.178 + 0.025; Pb[:, 2] = Pb[:, 2] * 1.6 + 0.62; L.set_co(belt, Pb); belt.data.materials.append(boot_m); parts.append(belt)
    buckle = L.box('buckle', (-0.03, -0.178, 0.595), (0.03, -0.158, 0.645), c, hi=True, bevel=0.004); buckle.data.materials.append(im); parts.append(buckle)
    t = NT('eye'); nrm = t.sep(t.gnormal); t.set(base=t.mix(t.ramp(t.math('MULTIPLY', nrm[1], -1.0), [(0.86, 0.0), (0.9, 1.0)]), (0.55, 0.30, 0.03), (0.01, 0.008, 0.005)), rough=0.06, coat=1.0, coat_rough=0.03)
    for sx in (1, -1):
        hit = C.surface_hit(body, (0.052 * sx, -1.0, 1.213), (0, 1, 0)); ey = (hit[0][1] if hit else -0.22) + 0.013; e = C.ball('eye', (0.052 * sx, ey, 1.213), 0.017, c, seg=14, squash=(1, 0.8, 0.85)); e.data.materials.append(t.mat); parts.append(e)
        hit = C.surface_hit(body, (0.05 * sx, -1.0, 1.112), (0, 1, 0)); ty = (hit[0][1] if hit else -0.22) + 0.008; tk = C.cone('tusk', (0.05 * sx, ty, 1.106), (0.056 * sx, ty - 0.014, 1.152), 0.0095, c, nu=8, nv=5); tk.data.materials.append(hm); parts.append(tk)
        if soldier or horned:                                      # pauldrons: an iron cap over each shoulder
            pd = C.ball('pauldron', (0.265 * sx, -0.01, 1.035), 0.135, c, seg=24, squash=(1.0, 0.95, 0.62)); pd.data.materials.append(im); parts.append(pd)
            if horned:
                for k, a in enumerate((-40, 0, 40)):
                    d = np.array([math.sin(math.radians(a)) * 0.4 + 0.75 * sx, 0, 1.0]); d[1] = math.sin(math.radians(a)) * 0.6; d /= np.linalg.norm(d); b0 = np.array([0.265 * sx, -0.01, 1.035]) + d * np.array([0.12, 0.12, 0.075])
                    sp = C.cone('pspike', tuple(b0), tuple(b0 + d * 0.085), 0.018, c, nu=8, nv=5); sp.data.materials.append(im); parts.append(sp)
    hr = np.array(J['hand_r']); hl = np.array(J['hand_l']); hy = J['head'][1]

    def gear(o, mat, bone):
        o.data.materials.append(mat); parts.append(o); GEAR[o.name] = bone; return o
    if soldier:
        gear(L.sweep('helm', [(0, hy, 1.25, 0.136, 0.152, 2.2), (0, hy, 1.295, 0.138, 0.154, 2.2), (0, hy, 1.35, 0.110, 0.125, 2.1), (0, hy, 1.39, 0.05, 0.06, 2.0)], nu=48, nv=30, c=c, up=(0, 1, 0), cap=0.5), im, 'head')
        gear(L.sweep('crest', [(0, hy + 0.14, 1.30, 0.008, 0.02, 3), (0, hy + 0.10, 1.40, 0.009, 0.03, 3), (0, hy, 1.44, 0.009, 0.035, 3), (0, hy - 0.10, 1.40, 0.008, 0.025, 3), (0, hy - 0.14, 1.33, 0.006, 0.014, 3)], nu=20, nv=40, c=c, up=(1, 0, 0), cap=0.4), im, 'head')
        gear(L.sweep('nasal', [(0, hy - 0.145, 1.29, 0.014, 0.005, 4), (0, hy - 0.192, 1.22, 0.012, 0.005, 4), (0, hy - 0.205, 1.17, 0.009, 0.004, 4)], nu=16, nv=16, c=c, up=(0, 1, 0), cap=0.5), im, 'head')
        shield = L.lathe('shield', [(0, 0.0), (0.07, 0.004), (0.09, 0.03), (0.3, 0.055), (0.335, 0.06), (0.335, 0.075), (0.3, 0.07), (0.09, 0.05), (0.06, 0.075), (0, 0.085)], seg=64, c=c, cap0=False, cap1=False); L.subsurf(shield, 1)
        from mathutils import Matrix
        L.xform(shield, Matrix.Translation((hl[0] + 0.1, hl[1] - 0.02, hl[2] + 0.2)) @ Matrix.Rotation(math.radians(-80), 4, 'Y') @ Matrix.Rotation(math.radians(8), 4, 'X'))
        sm = NT('shield'); n = sm.noise(40, 5, 0.65); gr = sm.noise(1.0, 5, 0.65, vec=sm.mapping(scale=(50, 50, 2.5))); col = sm.mix(gr, (0.05, 0.03, 0.014), (0.16, 0.09, 0.04)); sm.set(base=col, rough=sm.mixf(n, 0.5, 0.75), normal=sm.bump(gr, 0.4, 0.001))
        gear(shield, sm.mat, 'lowerarm_l')
        gear(L.sweep('pole', [(hr[0], hr[1] - 0.01, 0.0, 0.015, 0.015, 2.1), (hr[0], hr[1] - 0.01, 0.9, 0.016, 0.016, 2.1), (hr[0], hr[1] - 0.01, 1.78, 0.014, 0.014, 2.1)], nu=30, nv=60, c=c, up=(0, 1, 0), cap=0.7), wm, 'hand_r')
        # the bill of 801: a broad cleaver blade with a hooked beak, edge outwards
        gear(L.sweep('blade', [(hr[0] + 0.005, hr[1] - 0.01, 1.52, 0.006, 0.05, 4), (hr[0] - 0.09, hr[1] - 0.01, 1.56, 0.005, 0.13, 3.4), (hr[0] - 0.21, hr[1] - 0.01, 1.62, 0.0012, 0.17, 3)], nu=30, nv=30, c=c, up=(0, 0, 1), cap=0.3), im, 'hand_r')
        gear(L.sweep('spike', [(hr[0], hr[1] - 0.01, 1.74, 0.014, 0.014, 4), (hr[0], hr[1] - 0.01, 1.86, 0.009, 0.009, 4), (hr[0], hr[1] - 0.01, 2.02, 0.001, 0.001, 3)], nu=20, nv=24, c=c, up=(0, 1, 0), cap=0.3), im, 'hand_r')
    else:
        gear(L.sweep('cap', [(0, hy, 1.235, 0.134, 0.149, 2.2), (0, hy, 1.29, 0.132, 0.147, 2.2), (0, hy, 1.34, 0.097, 0.112, 2.1), (0, hy, 1.365, 0.03, 0.04, 2.0)], nu=48, nv=30, c=c, up=(0, 1, 0), cap=0.5), im, 'head')
        if horned:                                                 # Mog (781): bull horns on the helmet, a spiked club
            for sx in (1, -1):
                gear(C.cone('horn', (0.105 * sx, hy, 1.305), (0.27 * sx, hy - 0.05, 1.46), 0.036, c, bend=(0.07 * sx, 0.0, -0.035), nu=12, nv=12), hm, 'head')
            gear(L.sweep('club', [(hr[0], hr[1] - 0.01, 0.16, 0.019, 0.019, 2.2), (hr[0], hr[1] - 0.01, 0.62, 0.023, 0.023, 2.2), (hr[0], hr[1] - 0.01, 0.98, 0.045, 0.045, 2.2), (hr[0], hr[1] - 0.01, 1.22, 0.07, 0.07, 2.3), (hr[0], hr[1] - 0.01, 1.30, 0.05, 0.05, 2.2)], nu=30, nv=60, c=c, up=(0, 1, 0), cap=0.8), wm, 'hand_r')
            for k in range(14):
                a = k * 2.4; zc = 1.02 + 0.2 * (k % 7) / 6.0; rr = 0.05 + 0.02 * ((zc - 1.0) / 0.22); d = np.array([math.cos(a), math.sin(a), 0.15]); b0 = np.array([hr[0], hr[1] - 0.01, zc]) + d * rr * 0.8
                gear(C.cone('cspike', tuple(b0), tuple(b0 + d * 0.085), 0.016, c, nu=8, nv=5), im, 'hand_r')
        else:
            gear(L.sweep('shaft', [(hr[0], hr[1] - 0.01, 0.12, 0.018, 0.018, 2.2), (hr[0], hr[1] - 0.01, 0.6, 0.02, 0.02, 2.2), (hr[0], hr[1] - 0.01, 1.18, 0.02, 0.02, 2.2)], nu=30, nv=50, c=c, up=(0, 1, 0), cap=0.7), wm, 'hand_r')
            head = L.sweep('hammer', [(hr[0], hr[1] - 0.2, 1.1, 0.07, 0.07, 7), (hr[0], hr[1] - 0.17, 1.1, 0.082, 0.082, 7), (hr[0], hr[1] - 0.01, 1.1, 0.085, 0.085, 6), (hr[0], hr[1] + 0.15, 1.1, 0.082, 0.082, 7), (hr[0], hr[1] + 0.18, 1.1, 0.07, 0.07, 7)], nu=48, nv=40, c=c, up=(0, 0, 1), cap=0.8)
            L.displace_np(head, lambda Q: 0.0006 * fbm(Q, 3, 40, 3)); gear(head, im, 'hand_r')
    zmin = min(L.co(o)[:, 2].min() for o in parts)           # stand it on the ground
    for o in parts:
        Pq = L.co(o); Pq[:, 2] -= zmin; L.set_co(o, Pq)
    return parts


def rigid_gear(lods, hi, arm, outdir, asset):
    """Gear does not bend: every game-mesh vertex whose nearest source part is a piece of gear rides that part's bone, weight 1."""
    from mathutils.bvhtree import BVHTree
    import bmesh
    trees = []
    for o in hi:
        bm = bmesh.new(); bm.from_mesh(o.data); trees.append((GEAR.get(o.name.split('.')[0]), BVHTree.FromBMesh(bm))); bm.free()
    for i, o in enumerate(lods):
        n = 0
        for v in o.data.vertices:
            best = (1e9, None)
            for bone, tr in trees:
                hit = tr.find_nearest(v.co)
                if hit[0] is not None and hit[3] < best[0]: best = (hit[3], bone)
            if best[1]:
                for g in o.vertex_groups: g.remove([v.index])
                o.vertex_groups[best[1]].add([v.index], 1.0, 'REPLACE'); n += 1
        print('RIGID', o.name, n, 'of', len(o.data.vertices)); C.export_skeletal(os.path.join(outdir, '%s_LOD%d.fbx' % (asset, i)), arm, o)


WEAK = ('NOT photoreal at 1 m. The body is a joint-graph sculpt (no modelled muscle, hands are mittens round the weapon, the face is pressed-in eyes and mouth with ball eyes and two tusks, no lids or nostrils). '
        'Garments are shells lifted off that body: real hems, but no seams, lacing or cloth simulation, and they bend with the automatic skin weights of the body. Helmet, weapon and shield are rigid on their bone; pauldrons are skinned. '
        'Decimated game mesh without joint loops. Clips are the poses made for the knight (clips_monsters.py). The horned goblin (Mog) is the same body in another kit, not a bigger build.')
KITS = {'Soldier': dict(fam='goblin_soldier', seq='801-809 foes/goblin/soldier/walk', dresses='goblin soldier, 1.37 m (2.0 m to the spike of his bill): olive warty skin, iron scale coat over breeches, crested helmet with a nasal, iron pauldrons, round wooden shield on the left arm, a broad-bladed bill in the right hand'),
        'Hammer': dict(fam='goblin_hammer', seq='761-769 foes/goblin/hammer/walk', dresses='goblin with a war hammer, 1.37 m: olive warty skin, studded leather jerkin, breeches, boots, iron skullcap, a square-headed iron hammer on a 1.1 m shaft in the right hand'),
        'Horned': dict(fam='goblin_horned', seq='781-789 foes/goblin/horns/walk', dresses='horned goblin (Mog), 1.37 m before the class row scales him up: olive skin, red-brown studded jerkin, spiked iron pauldrons, a helmet with bull horns, a spiked club in the right hand')}


def main(kind, mode):
    L.reset(); asset = 'SK_Goblin_%s_PR' % kind; kt = KITS[kind]; outdir = os.path.join(L.UNC, kt['fam'], 'Goblin_' + kind); hi = goblin(kind, L.coll('Source_Hi'))
    R_ = L.review_setup(ground='forrest_ground_01', ground_scale=0.5, exposure=-5.0)

    def shots(obs, tag, d):
        L.shot(R_, os.path.join(d, '%s_beauty.png' % tag), obs, az=30, el=8, fill=1.15, lens=70, spp=192, res=(900, 1200), dz=0.05)
        L.shot(R_, os.path.join(d, '%s_close.png' % tag), center=(0, -0.08, 1.15), radius=0.3, az=26, el=4, fill=0.9, lens=85, res=(1000, 800), spp=192, fstop=8)
    if mode == 'review':
        shots(hi, 'Goblin_%s_hi' % kind, L.REVIEW); return
    lo = L.make_lo(hi, 20000, asset, L.coll(asset), angle=72, margin=0.004); arm = C.make_armature(asset + '_Armature', J, BONES, L.coll(asset)); ids = L.origin_ids([kt['fam']]) if kind != 'Horned' else {}
    man, lods, files, vfiles = C.finish_creature(asset, 'character_humanoid', lo, hi, arm, outdir, 2048, families=[kt['fam'], kt['seq']], origin=ids, dresses=kt['dresses'], weaknesses=WEAK, script=SCRIPT + ' ' + kind + ' final', extrude=0.008, maxdist=0.02,
                      lod_ratios=(0.5, 0.25, 0.12), third_party=['rusty_metal_02'], extra={'contact_crop': 0.95, 'skeleton_note': 'bone names and hierarchy of the project humanoid core set (CONVENTIONS.md section 11), goblin proportions'})
    rigid_gear(lods, hi, arm, outdir, asset)
    shots([lo], 'render', outdir)
    C.pose(arm, {'upperarm_l': (0, 0, -30), 'lowerarm_l': (-35, 0, 0), 'thigh_l': (-28, 0, 0), 'calf_l': (30, 0, 0), 'thigh_r': (14, 0, 0), 'head': (0, 0, 22), 'spine_03': (0, 0, 8)})
    L.shot(R_, os.path.join(outdir, 'render_pose.png'), [lo], az=30, el=8, fill=1.15, lens=70, res=(750, 1000), spp=128, dz=0.05); C.pose(arm, {}); L.save_blend()


if __name__ == '__main__':
    a = L.args(); kinds = list(KITS) if a[0] == 'all' else a[0].split(','); mode = a[1] if len(a) > 1 else 'review'
    for k in kinds:
        main(k, mode)
