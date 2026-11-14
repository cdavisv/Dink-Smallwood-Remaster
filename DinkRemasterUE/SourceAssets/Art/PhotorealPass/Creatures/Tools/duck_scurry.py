"""Fast gaits for the duck: Duck_Scurry and Duck_HeadlessScurry, made from Duck_Run and Duck_HeadlessRun.

The game moves a duck 60 pixels a second, 6 to 8.5 m/s at the remaster's world scale (measured in the game). The run clips cover about 0.5 m/s of
ground: at 4 m/s their feet would slide. The scurry is the flapping sprint of a frightened farmyard duck: body pitched
forward, two wing beats and two bounding steps per cycle with the feet clear of the ground between them, longer leg
reach. One cycle is 8 frames at 30 fps; the importer declares it for 400 cm/s.

usage: blender -b -t 4 --python duck_scurry.py -- build [review] [export]
  build   adds/replaces the two actions in Duck/SK_Duck.blend and saves it
  review  renders Review/scurry_strip.png and Review/headless_scurry_strip.png (after build)
  export  writes Export/A_Duck_Scurry.fbx and Export/A_Duck_HeadlessScurry.fbx (last: it scales the scene, nothing is saved)
"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from crlib import *
from mathutils import Quaternion, Matrix, Vector

A = args()
DST = OUT / 'Duck'
N = 8                      # frame intervals per cycle
FPS = 30
GAIN = {'thigh': 1.9, 'calf': 1.35, 'foot': 1.15, 'toes': 1.0, 'pelvis': 1.25, 'tail': 1.6, 'spine': 1.2, 'neck': 1.15, 'head': 1.0, 'jaw': 1.0}
LEAN = math.radians(13)    # extra forward pitch of the body
LIFT, BOUNCE = .010, .026  # metres: the body rides higher and leaves the ground twice a cycle


def gain_of(name):
    for k, v in GAIN.items():
        if name.startswith(k): return v
    return 1.0


def qmean(qs):
    ref = qs[0]; acc = Quaternion((0, 0, 0, 0))
    for q in qs:
        acc = acc + (q if q.dot(ref) >= 0 else -q)
    acc.normalize(); return acc


def qpow(q, k):
    axis, angle = q.to_axis_angle()
    if angle > math.pi: angle -= 2 * math.pi
    return Quaternion(axis, angle * k)


def sample(arm, action):
    act = bpy.data.actions[action]; f0, f1 = act.frame_range
    sc = bpy.context.scene; out = []
    for i in range(N):
        t = f0 + (f1 - f0) * i / N
        set_action(arm, action, int(math.floor(t)))
        sc.frame_set(int(math.floor(t)), subframe=t - math.floor(t)); bpy.context.view_layer.update()
        out.append({pb.name: (pb.rotation_quaternion.copy(), pb.location.copy()) for pb in arm.pose.bones})
    return out


def make(arm, src, dst, headless):
    S = sample(arm, src)
    names = [pb.name for pb in arm.pose.bones]
    mean = {n: qmean([s[n][0] for s in S]) for n in names}
    wings = {}
    for n in ('wing_l', 'wing_r', 'wingtip_l', 'wingtip_r'):
        qs = [s[n][0] for s in S]
        ang = [q.angle if q.angle <= math.pi else 2 * math.pi - q.angle for q in qs]
        wings[n] = (qs[ang.index(min(ang))], qs[ang.index(max(ang))])
    if dst in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[dst])
    act = bpy.data.actions.new(dst); act.use_fake_user = True
    arm.animation_data_create(); arm.animation_data.action = act; arm.data.pose_position = 'POSE'
    sc = bpy.context.scene
    for i in range(N + 1):
        ph = (i % N) / N; s = S[i % N]
        sc.frame_set(i + 1)
        for pb in arm.pose.bones:
            n = pb.name; q, loc = s[n]
            if n in wings:
                closed, opened = wings[n]
                lag = .07 if 'tip' in n else 0.0
                a = .70 + 1.0 * math.sin(2 * math.pi * (2 * (ph - lag)) + (.9 if headless and n.endswith('_r') else 0.0))
                d = closed.inverted() @ opened
                pb.rotation_quaternion = closed @ qpow(d, a)
            else:
                d = mean[n].inverted() @ (q if q.dot(mean[n]) >= 0 else -q)
                pb.rotation_quaternion = mean[n] @ qpow(d, gain_of(n))
            pb.location = loc
        bpy.context.view_layer.update()
        # body: pitched forward about the hip line, lifted, two bounds per cycle (feet leave the ground at the top)
        pel = arm.pose.bones['pelvis']; hip = pel.matrix.to_translation()
        bound = abs(math.sin(2 * math.pi * ph + .35))
        m = Matrix.Translation(Vector((0, 0, LIFT + BOUNCE * bound))) @ Matrix.Translation(hip) @ Matrix.Rotation(LEAN, 4, 'Y') @ Matrix.Translation(-hip) @ pel.matrix
        pel.matrix = m; bpy.context.view_layer.update()
        if not headless:
            # the neck reaches forward and up so the head stays level and leads
            nk = arm.pose.bones['neck_01']; base = nk.matrix.to_translation()
            nk.matrix = Matrix.Translation(base) @ Matrix.Rotation(-LEAN * .75, 4, 'Y') @ Matrix.Translation(-base) @ nk.matrix
            bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            pb.keyframe_insert('rotation_quaternion', frame=i + 1)
            if pb.name == 'pelvis': pb.keyframe_insert('location', frame=i + 1)
    for layer in act.layers:
        for strip in layer.strips:
            for slot in act.slots:
                bag = strip.channelbag(slot)
                if bag:
                    for cu in bag.fcurves:
                        for k in cu.keyframe_points: k.interpolation = 'LINEAR'
    log('made', dst, 'frames', act.frame_range[:])


def strip(arm, action, mesh, out):
    files = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith(('SK_Duck', 'SM_Duck')): o.hide_render = o.name != mesh
    for f in range(1, N + 1):
        set_action(arm, action, f); p = DST / 'Review' / ('_s%d.png' % f)
        shoot(p, (.12, -1.25, .30), (0, 0, .2), 70, (560, 420), 40, exposure=-.7); files.append(p)
    montage(files, DST / 'Review' / out, cols=4); [p.unlink() for p in files]


bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Duck.blend')); arm = bpy.data.objects['Armature']
if 'build' in A:
    make(arm, 'Duck_Run', 'Duck_Scurry', False)
    make(arm, 'Duck_HeadlessRun', 'Duck_HeadlessScurry', True)
    set_action(arm, None, 1); arm.data.pose_position = 'REST'
    bpy.ops.wm.save_mainfile()
if 'review' in A:
    for o in list(bpy.data.objects):
        if o.name == 'DuckHigh': bpy.data.objects.remove(o)
    setup_review(samples=40, ground='leafy_grass', ground_scale=1.2)
    strip(arm, 'Duck_Scurry', 'SK_Duck_LOD0', 'scurry_strip.png')
    strip(arm, 'Duck_HeadlessScurry', 'SK_Duck_Headless_LOD0', 'headless_scurry_strip.png')
if 'export' in A:
    bpy.ops.wm.open_mainfile(filepath=str(DST / 'SK_Duck.blend')); arm = bpy.data.objects['Armature']; sc = bpy.context.scene
    activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    for b in arm.data.edit_bones: b.head *= 100; b.tail *= 100
    bpy.ops.object.mode_set(mode='OBJECT'); sc.unit_settings.scale_length = .01
    for key in ('Scurry', 'HeadlessScurry'):
        a = bpy.data.actions['Duck_' + key]
        for layer in a.layers:
            for st in layer.strips:
                for slot in a.slots:
                    bag = st.channelbag(slot)
                    if bag:
                        for cu in bag.fcurves:
                            if cu.data_path.endswith('.location'):
                                for k in cu.keyframe_points: k.co.y *= 100; k.handle_left.y *= 100; k.handle_right.y *= 100
        arm.data.pose_position = 'POSE'; arm.animation_data_create(); arm.animation_data.action = a
        try:
            if arm.animation_data.action_slot is None and a.slots: arm.animation_data.action_slot = a.slots[0]
        except Exception: pass
        sc.frame_start = int(a.frame_range[0]); sc.frame_end = int(a.frame_range[1]); sc.render.fps = FPS; sc.frame_set(sc.frame_start)
        activate(arm); p = DST / 'Export' / ('A_Duck_%s.fbx' % key)
        bpy.ops.export_scene.fbx(filepath=str(p), use_selection=True, object_types={'ARMATURE'}, apply_unit_scale=True, global_scale=1, apply_scale_options='FBX_SCALE_ALL', axis_forward='Y', axis_up='Z', bake_space_transform=False, use_space_transform=True, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False, armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0, path_mode='STRIP', embed_textures=False, use_custom_props=False)
        log('exported', p.name)
