"""Pose a character in Blender from the game's bone trace and render it (Cycles on the CPU): a look at a posture value
without a rendered game. Positions only: every traced bone is aimed at its traced child, so twists (the turn of a hand)
are the rest pose's; the posture row's W is applied the way the game applies it (arm_clearance.turn_arm).
  python3 -I Scripts/AnimationQA/arm_clearance.py <trace.csv> --frames frames.json
  blender -b -t 4 <SK_<Name>_Photoreal.blend> --python Scripts/AnimationQA/trace_pose.py -- frames.json <state=key,state=key> <W,W,W> <out prefix> [views]
state = idle / walk / run / act:<clip>, key = near / mid / far; views of front, back, q, close, play (comma list).
Writes <out prefix>.png: one row per pose and W, one column per view (needs ImageMagick `montage`).
Env: SMP (samples, 28), HERO_SCALE (the size the game draws the body at against its source, 0.975 for the hero)."""
import bpy, sys, json, math, os
import numpy as np
from mathutils import Vector, Matrix
a = sys.argv[sys.argv.index('--') + 1:]; poses = json.load(open(a[0])); sel = [s.split('=') for s in a[1].split(',')]; WS = [float(x) for x in a[2].split(',')]; out = a[3]
views = (a[4] if len(a) > 4 else 'front,back,play').split(',')
sc = bpy.context.scene; arm = bpy.data.objects['Armature']
for o in list(sc.objects):
    if o.type == 'MESH' and '_LOD' in o.name and not o.name.endswith('_LOD0'): bpy.data.objects.remove(o, do_unlink=True)
    elif o.type in ('LIGHT', 'CAMERA'): bpy.data.objects.remove(o, do_unlink=True)
SCALE = float(os.environ.get('HERO_SCALE', .975))      # the game draws the hero a little smaller than his source (bone lengths in the trace against the rest pose)
arm.data.pose_position = 'POSE'; arm.animation_data_clear()
def cv(p): return Vector((p[0] / 100 / SCALE, -p[1] / 100 / SCALE, p[2] / 100 / SCALE))
CHAINS = [('spine_01', 'spine_03'), ('spine_03', 'spine_05'), ('spine_05', 'neck_01'), ('neck_01', 'head')]
for s in 'lr': CHAINS += [('clavicle_' + s, 'upperarm_' + s), ('upperarm_' + s, 'lowerarm_' + s), ('lowerarm_' + s, 'hand_' + s), ('thigh_' + s, 'calf_' + s), ('calf_' + s, 'foot_' + s), ('foot_' + s, 'ball_' + s)]
def upd(): bpy.context.view_layer.update()
def turn_about(pb, R, h):
    pb.matrix = Matrix.Translation(h) @ R.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix; upd()
def pose(B, Wd):
    T = {k: np.array(v, float) for k, v in B.items()}
    for sd, sg in (('l', 1.0), ('r', -1.0)):      # the posture row's W: the upper arm turned about its joint towards the trunk in mesh space
        S_ = T['upperarm_' + sd]; th = math.radians(Wd) * sg; c, s_ = math.cos(th), math.sin(th)
        for b in ('lowerarm_' + sd, 'hand_' + sd):
            v = T[b] - S_; T[b] = S_ + np.array([v[0] * c + v[2] * s_, v[1], -v[0] * s_ + v[2] * c])
    T = {k: cv(v) for k, v in T.items()}; P = arm.pose.bones
    for pb in P: pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    upd(); pv = P['pelvis']
    pv.matrix = Matrix.Translation(T['pelvis'] - pv.head) @ pv.matrix; upd()
    side_c = (P['thigh_l'].head - P['thigh_r'].head).normalized(); side_t = (T['thigh_l'] - T['thigh_r']).normalized(); turn_about(pv, side_c.rotation_difference(side_t), pv.head.copy())
    up_c = P['spine_01'].head - pv.head; up_t = T['spine_01'] - T['pelvis']; ax = side_t
    up_c = (up_c - ax * up_c.dot(ax)).normalized(); up_t = (up_t - ax * up_t.dot(ax)).normalized(); turn_about(pv, up_c.rotation_difference(up_t), pv.head.copy())
    for b, c in CHAINS:
        pb = P[b]; cur = (P[c].head - pb.head); tgt = (T[c] - T[b])
        if cur.length < 1e-5 or tgt.length < 1e-5: continue
        turn_about(pb, cur.normalized().rotation_difference(tgt.normalized()), pb.head.copy())
    errs = sorted(((round((P[k].head - T[k]).length * 100, 1), k) for k in T if k in P), reverse=True); print('ERRS', errs[:8]); return errs[0][0] / 100, T
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('SMP', 28)); sc.cycles.use_denoising = True
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; nt = w.node_tree; sky = nt.nodes.new('ShaderNodeTexSky'); nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0]); nt.nodes['Background'].inputs[1].default_value = .35
try: sky.sun_elevation = math.radians(48); sky.sun_rotation = math.radians(140)
except Exception: pass
m = bpy.data.meshes.new('g'); m.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)]); g = bpy.data.objects.new('g', m); sc.collection.objects.link(g)
gm = bpy.data.materials.new('g'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.10, .17, .05, 1); gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .9; m.materials.append(gm)
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
VIEW = {'front': (0, 3, 4.2, 1.12, 62, 360, 600), 'back': (180, 3, 4.2, 1.12, 62, 360, 600), 'q': (38, 6, 4.2, 1.12, 62, 360, 600), 'play': (180, 30, 8.5, .95, 50, 480, 300), 'close': (0, 2, 2.6, 1.22, 70, 420, 420)}
files = []; rep = []
for st, key in sel:
    B = poses[st][key]['bones']
    for Wd in WS:
        err, T = pose(B, Wd); rep.append((st, key, Wd, round(err * 100, 1)))
        root = arm.pose.bones['pelvis'].head.copy(); row = []
        for vn in views:
            az, el, dist, tz, lens, rx, ry = VIEW[vn]; t = Vector((root.x, root.y, tz)); r = math.radians(az); e = math.radians(el); cam.data.lens = lens
            cam.location = t + Vector((math.sin(r) * math.cos(e), -math.cos(r) * math.cos(e), math.sin(e))) * dist; cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.resolution_x = rx; sc.render.resolution_y = ry; f = '%s_%s_%s_W%g_%s.png' % (out, st.replace(':', ''), key, Wd, vn); sc.render.filepath = f; bpy.ops.render.render(write_still=True); row.append(f)
        files.append(row)
print('POSE_ERR_CM', rep)
os.system('montage ' + ' '.join(f for row in files for f in row) + ' -tile %dx%d -geometry +2+2 %s.png && rm ' % (len(views), len(files), out) + ' '.join(f for row in files for f in row))
