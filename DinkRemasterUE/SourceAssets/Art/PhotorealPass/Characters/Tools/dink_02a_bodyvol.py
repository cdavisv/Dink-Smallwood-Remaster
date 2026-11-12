"""Stage 2: garments. Old MakeHuman-derived shirt/trouser topology gives clean armhole and crotch loops; everything is
re-cut, re-shaped and folded here. Produces *_Base (undisplaced, with UVMetric and chart ids) objects; fold functions
are applied later at two resolutions (game mesh: macro folds; bake source: macro + fine)."""
import bpy, sys, os, pickle
sys.path.insert(0, os.path.dirname(__file__))
from prlib import *; from garlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Dink/Work/dink_base.blend'))
arm = bpy.data.objects['Armature']; B = arm.data.bones
def bh(n): return np.array(B[n].head_local)
S, E_, Wr = bh('upperarm_l'), bh('lowerarm_l'), bh('hand_l')
T, K, A, BALL = bh('thigh_l'), bh('calf_l'), bh('foot_l'), bh('ball_l')
dU = (E_ - S) / np.linalg.norm(E_ - S); dF = (Wr - E_) / np.linalg.norm(Wr - E_)
MIR = np.array([-1, 1, 1.0])
def mirx(c):
    m = np.array(c, float).copy(); m[..., 0] = np.abs(m[..., 0]); return m
def s_arm(c): return (mirx(c) - S) @ dU
def f_arm(c): return (mirx(c) - E_) @ dF


import folds
folds.setup({n: list(B[n].head_local) for n in ('upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l')})

old_bvh = bvh_of([bpy.data.objects['OldShirtTopo'], bpy.data.objects['OldTrousersTopo']])
def scan_tube(name, pts, ref, s0, s1, nr, nu, rmax, rdef, shrink=.006):
    """Loft a closed tube by scanning the old garment wall with inside-out rays around a polyline axis."""
    poly = Poly(pts, ref=ref); rings = []; R = np.zeros((nr, nu)); C = []; FR = []
    for i in range(nr):
        s = s0 + (s1 - s0) * i / (nr - 1); c, d = poly.point(min(max(s, 0), poly.cum[-1])); c = c + d * (s - min(max(s, 0), poly.cum[-1]))
        x, y = poly.frame(d); C.append(c); FR.append((x, y))
        for j in range(nu):
            a = 2 * math.pi * j / nu; dr = x * math.cos(a) + y * math.sin(a)
            lim = rmax(s, a) if callable(rmax) else rmax
            hit = old_bvh.ray_cast(c, dr, lim)
            R[i, j] = (hit[0] - c).length if hit[0] is not None else (rdef(s, a) if callable(rdef) else rdef)
    for _ in range(2):
        R = (np.roll(R, 1, 1) + 2 * R + np.roll(R, -1, 1)) / 4
        R[1:-1] = (R[:-2] + 2 * R[1:-1] + R[2:]) / 4
    R -= shrink
    for i in range(nr):
        x, y = FR[i]
        rings.append([tuple(C[i] + (x * math.cos(2 * math.pi * j / nu) + y * math.sin(2 * math.pi * j / nu)) * R[i, j]) for j in range(nu)])
    return loft(name, rings, cap_end=True, cap_start=True)
parts = []
def torso_rmax(s, a):
    z = .86 + s
    lat = abs(math.sin(a))
    return .30 if z < 1.30 else (.30 - (.30 - .19) * lat * min(1, (z - 1.30) / .08))
parts.append(scan_tube('bv_torso', [(0, -.02, .86), (0, -.02, 1.53)], (0, -1, 0), 0, .612, 62, 72, torso_rmax, lambda s, a: .15))
for sg in (1, -1):
    M = np.array([sg, 1, 1.0])
    parts.append(scan_tube('bv_arm%d' % sg, [S * M, E_ * M, Wr * M], (0, 0, -1), -.02, np.linalg.norm(E_ - S) + np.linalg.norm(Wr - E_) - .006, 60, 40, .085, .036))
    parts.append(scan_tube('bv_sho%d' % sg, [np.array([.04, .0, 1.45]) * M, np.array([.215, .026, 1.44]) * M], (0, 0, 1), 0, .176, 22, 40, .115, .075))
    parts.append(scan_tube('bv_leg%d' % sg, [T * M, K * M, A * M], (0, -1, 0), -.06, np.linalg.norm(K - T) + .355, 80, 48, .13, .07))
bv = join(parts, 'BodyVol')
m = bv.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = .005; m.adaptivity = 0
apply_mods(bv); laplacian_smooth(bv, it=8, lam=.6); smooth_shade(bv)
for l in list(bv.data.uv_layers): bv.data.uv_layers.remove(l)
log('BodyVol', len(bv.data.vertices), co_np(bv.data).min(0), co_np(bv.data).max(0))
save_blend(filepath=str(OUT / 'Dink/Work/dink_bodyvol.blend'))
for nm in ('OldHair', 'OldEyes', 'BrowLash', 'OldWardrobe', 'OldShirtTopo', 'OldTrousersTopo', 'Skin'): bpy.data.objects[nm].hide_render = True
mt = bpy.data.materials.new('pv'); mt.use_nodes = True; bv.data.materials.append(mt)
setup_render(samples=16, res=(1100, 800)); bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = .08
shoot(OUT / 'Dink/Review/bodyvol.png', (0.9, -3.4, 1.3), (0, 0, .92), lens=60)
