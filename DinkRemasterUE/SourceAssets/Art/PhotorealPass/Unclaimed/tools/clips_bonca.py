"""Animation clips for the bonca (SK_Bonca_PR: 19 bones, a heavy two-legged beast with a long tail, forward = -Y).

The source had a rig and no clips. This adds Bonca_Idle, Bonca_Walk, Bonca_Run, Bonca_Attack, Bonca_Hit and Bonca_Death
to SK_Bonca_PR.blend and exports one armature-only FBX per clip (A_Bonca_<Clip>.fbx, 30 fps, in place: the root bone
never moves). Every pose is built in armature space, parent first, as rotations about the animal's own axes (pitch
about X, yaw about Z, roll about Y) around each bone's head, so the script does not depend on bone rolls.

How it is meant to move: the weight sits over the hips and is carried from one leg to the other (the pelvis drops and
rolls over the standing leg, yaws with the stride), the tail swings against the hips and lags down its length, the
head stays level while the body works under it. Walk: 24 frames, about 1.5 m/s. Run: 16 frames with both feet off the
ground twice a cycle, about 4 m/s. Attack: rear back, lunge and snap, recover. Death: the legs give way, it falls on
its side and the tail drops last.

usage: tools/bl.sh clips_bonca.py build [review] [export]
"""
import bpy, sys, os, math
from mathutils import Matrix, Vector

A = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['build']
HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(os.path.dirname(HERE), 'bonca_gray', 'Bonca')
BLEND = os.path.join(DIR, 'SK_Bonca_PR.blend')
FPS = 30
TAU = math.tau
SPINE = ('spine_01', 'spine_02', 'spine_03')
TAIL = ('tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05')
AX = {'pitch': 'X', 'yaw': 'Z', 'roll': 'Y'}


def rot(arm, bone, axis, deg):
    """Turn a bone (and what hangs from it) about a body axis through its head. Pitch +: nose down (forward is -Y)."""
    if abs(deg) < 1e-6: return
    pb = arm.pose.bones[bone]; h = pb.matrix.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, AX[axis]) @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def move(arm, bone, d):
    pb = arm.pose.bones[bone]; pb.matrix = Matrix.Translation(Vector(d)) @ pb.matrix; bpy.context.view_layer.update()


def ease(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
def bump(t, a, b): return 0.0 if t <= a or t >= b else math.sin(math.pi * (t - a) / (b - a)) ** 2


def leg(arm, side, swing, lift, toe=0.0):
    """swing: thigh pitch, + = foot forward. lift 0..1: the knee folds and the foot comes off the ground. toe: push-off."""
    s = '_' + side
    rot(arm, 'thigh' + s, 'pitch', swing - 16 * lift)
    rot(arm, 'calf' + s, 'pitch', 34 * lift - .35 * swing)
    rot(arm, 'foot' + s, 'pitch', -(swing - 16 * lift) * .65 - (34 * lift - .35 * swing) * .8 + 14 * lift + toe * .5)
    rot(arm, 'ball' + s, 'pitch', -toe)


def tail(arm, yaw, pitch, lag, ph):
    for i, b in enumerate(TAIL):
        rot(arm, b, 'yaw', yaw * (.5 + .22 * i) * math.sin(ph - lag * i))
        rot(arm, b, 'pitch', pitch * (.6 + .15 * i) * math.sin(2 * ph - lag * i * 1.3))


def idle(arm, t):
    ph = TAU * t
    br = math.sin(2 * ph)                                   # two breaths in the clip
    move(arm, 'pelvis', (0, 0, -.008 + .008 * math.sin(ph)))
    rot(arm, 'pelvis', 'roll', 1.2 * math.sin(ph))          # the weight settles from one leg to the other
    rot(arm, 'spine_01', 'pitch', -1.2 * br); rot(arm, 'spine_02', 'pitch', 2.0 * br); rot(arm, 'spine_03', 'pitch', -.8 * br)
    rot(arm, 'spine_03', 'yaw', 5 * math.sin(ph)); rot(arm, 'head', 'yaw', 7 * math.sin(ph - .6)); rot(arm, 'head', 'pitch', 2.5 * math.sin(2 * ph + 1))
    tail(arm, 7, 1.5, .55, ph)


def gait(arm, t, swing, lift_k, bob, lean, yaw, roll, tail_yaw, air=0.0):
    ph = TAU * t
    move(arm, 'pelvis', (0, 0, -bob * .5 + bob * math.cos(2 * ph) * .5 + air * abs(math.sin(ph + .3))))   # lowest as each foot takes the weight
    rot(arm, 'pelvis', 'pitch', lean + 1.5 * math.sin(2 * ph + .8))
    rot(arm, 'pelvis', 'yaw', yaw * math.sin(ph)); rot(arm, 'pelvis', 'roll', roll * math.sin(ph + .5))
    for side, o in (('l', 0.0), ('r', math.pi)):
        s = math.sin(ph + o)                                # + = this foot is behind
        # rot() pitch + carries a hanging leg BACK, so the foot is behind when s > 0 and travels forward while s falls:
        # it is in the air then (cos < 0). The first version lifted it on the way back: the walk ran backwards (found by
        # measuring the foot's travel in the air, 14 Nov 2026).
        up = max(0.0, -math.cos(ph + o))
        leg(arm, side, swing * s, lift_k * up ** 1.4, toe=22 * max(0.0, s) * (1 if math.cos(ph + o) > -0.2 else 0))
    # the trunk turns against the hips and the head stays on its line
    rot(arm, 'spine_01', 'yaw', -yaw * .5 * math.sin(ph)); rot(arm, 'spine_02', 'yaw', -yaw * .4 * math.sin(ph)); rot(arm, 'spine_03', 'yaw', -yaw * .3 * math.sin(ph))
    rot(arm, 'spine_01', 'roll', -roll * .6 * math.sin(ph + .5))
    rot(arm, 'spine_02', 'pitch', -lean * .5 + 1.5 * math.sin(2 * ph)); rot(arm, 'head', 'pitch', -lean * .5 - 2.0 * math.sin(2 * ph + .4))
    tail(arm, tail_yaw, 3.0, .6, ph + math.pi)


def walk(arm, t): gait(arm, t, 24, 1.0, .035, 2, 6, 3.5, 9)
def run(arm, t): gait(arm, t, 34, 1.5, .05, 9, 8, 4, 12, air=.06)


def attack(arm, t):
    back = bump(t, 0.0, .45)                                # gathers itself
    snap = bump(t, .30, .75)                                # throws the head and chest forward and down
    move(arm, 'pelvis', (0, .07 * back - .16 * snap, -.05 * back - .03 * snap))
    rot(arm, 'pelvis', 'pitch', -9 * back + 13 * snap)
    for b, k in zip(SPINE, (.8, 1.0, 1.2)): rot(arm, b, 'pitch', (-7 * back + 12 * snap) * k)
    rot(arm, 'head', 'pitch', -16 * back + 10 * snap + 14 * bump(t, .5, .8))
    leg(arm, 'l', 10 * snap, 0, toe=10 * snap); leg(arm, 'r', -12 * snap + 4 * back, 0, toe=18 * snap)
    for i, b in enumerate(TAIL): rot(arm, b, 'pitch', (5 * back - 9 * snap) * (.6 + .2 * i)); rot(arm, b, 'yaw', 6 * snap * math.sin(TAU * t * 2 - i * .7))


def hit(arm, t):
    k = bump(t, 0.0, 1.0) * (1.25 - .5 * t)
    move(arm, 'pelvis', (.0, .05 * k, -.03 * k))
    rot(arm, 'pelvis', 'pitch', -6 * k); rot(arm, 'pelvis', 'roll', 5 * k)
    for b in SPINE: rot(arm, b, 'pitch', -5 * k)
    rot(arm, 'spine_03', 'yaw', 12 * k); rot(arm, 'head', 'yaw', 16 * k); rot(arm, 'head', 'pitch', -10 * k)
    leg(arm, 'l', -6 * k, 0); leg(arm, 'r', 5 * k, .25 * k)
    for i, b in enumerate(TAIL): rot(arm, b, 'yaw', -8 * k * (.5 + .2 * i))


def death(arm, t):
    stagger = bump(t, 0.0, .35)
    fall = ease((t - .22) / .43)                             # the legs give way and it goes over on its left side
    rest = ease((t - .6) / .4)                               # head and tail come down last
    hip = arm.pose.bones['pelvis'].matrix.to_translation().z
    move(arm, 'pelvis', (-.20 * fall, .05 * stagger, -(hip - .36) * fall + .03 * stagger))
    rot(arm, 'pelvis', 'pitch', -8 * stagger + 4 * fall); rot(arm, 'pelvis', 'roll', -6 * stagger - 78 * fall)
    for b, k in zip(SPINE, (6, 9, 8)): rot(arm, b, 'pitch', -6 * stagger + k * rest); rot(arm, b, 'yaw', 5 * fall)
    rot(arm, 'head', 'pitch', -20 * stagger + 14 * rest); rot(arm, 'head', 'yaw', 14 * stagger - 10 * rest)
    leg(arm, 'l', 26 * fall, .9 * fall); leg(arm, 'r', -14 * fall + 10 * stagger, .45 * fall + .5 * bump(t, .25, .7))
    for i, b in enumerate(TAIL):
        rot(arm, b, 'yaw', 10 * stagger * math.sin(TAU * t * 2 - i) * (1 - rest) + 7 * rest)
        rot(arm, b, 'pitch', -4 * stagger + (3 + 2.5 * i) * rest * .4)


CLIPS = (('Bonca_Idle', idle, 60, True), ('Bonca_Walk', walk, 24, True), ('Bonca_Run', run, 16, True),
         ('Bonca_Attack', attack, 18, False), ('Bonca_Hit', hit, 10, False), ('Bonca_Death', death, 36, False))


def build(arm):
    sc = bpy.context.scene; sc.render.fps = FPS
    arm.animation_data_create(); arm.data.pose_position = 'POSE'
    order = [b.name for b in arm.data.bones]                # parents come first
    for name, fn, n, loop in CLIPS:
        if name in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[name])
        act = bpy.data.actions.new(name); act.use_fake_user = True; arm.animation_data.action = act
        for f in range(n + 1):
            sc.frame_set(f + 1)
            for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'; pb.matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()
            fn(arm, (f % n) / n if loop else f / n)
            for b in order:
                pb = arm.pose.bones[b]
                if b == 'root': continue
                pb.keyframe_insert('rotation_quaternion', frame=f + 1)
                if b == 'pelvis': pb.keyframe_insert('location', frame=f + 1)
        for layer in act.layers:
            for strip in layer.strips:
                for slot in act.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for cu in bag.fcurves:
                            for k in cu.keyframe_points: k.interpolation = 'LINEAR'
        print('[CLIPS] made', name, n + 1, 'frames')
    arm.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)


def set_clip(arm, name, frame):
    a = bpy.data.actions[name]; arm.animation_data_create(); arm.animation_data.action = a
    try:
        if arm.animation_data.action_slot is None and a.slots: arm.animation_data.action_slot = a.slots[0]
    except Exception: pass
    arm.data.pose_position = 'POSE'; bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()


def review(arm):
    from PIL import Image
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = 480; sc.render.resolution_y = 360; sc.render.film_transparent = False
    skinned = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)]
    keep = max(skinned, key=lambda o: len(o.data.vertices))
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = o is not keep
    world = sc.world or bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.55, .62, .7, 1); world.node_tree.nodes['Background'].inputs[1].default_value = .9
    sun = bpy.data.objects.new('ReviewSun', bpy.data.lights.new('ReviewSun', 'SUN')); sun.data.energy = 3.5; sun.rotation_euler = (math.radians(52), 0, math.radians(115)); sc.collection.objects.link(sun)
    bpy.ops.mesh.primitive_plane_add(size=30); ground = bpy.context.active_object
    gm = bpy.data.materials.new('ReviewGround'); gm.diffuse_color = (.32, .36, .22, 1); ground.data.materials.append(gm)
    cam = bpy.data.objects.new('ReviewCam', bpy.data.cameras.new('ReviewCam')); cam.data.lens = 45; sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (5.2, -.6, 1.5); look = Vector((0, .2, .75)); cam.rotation_euler = (look - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for name, frames in (('Bonca_Walk', (1, 4, 7, 10, 13, 16, 19, 22)), ('Bonca_Run', (1, 3, 5, 7, 9, 11, 13, 15)), ('Bonca_Attack', (1, 5, 8, 10, 12, 14, 16, 19)),
                         ('Bonca_Death', (1, 6, 11, 16, 21, 26, 31, 37)), ('Bonca_Idle', (1, 16, 31, 46)), ('Bonca_Hit', (1, 4, 6, 9))):
        tiles = []
        for f in frames:
            set_clip(arm, name, f); p = os.path.join(DIR, '_clip.png'); sc.render.filepath = p; bpy.ops.render.render(write_still=True); tiles.append(Image.open(p).convert('RGB'))
        cols = 4; rows = (len(tiles) + cols - 1) // cols; sheet = Image.new('RGB', (480 * cols, 360 * rows))
        for i, im in enumerate(tiles): sheet.paste(im, (480 * (i % cols), 360 * (i // cols)))
        sheet.save(os.path.join(DIR, 'clip_%s.jpg' % name[6:].lower()), quality=88); os.remove(os.path.join(DIR, '_clip.png'))
        print('[CLIPS] sheet', name)


def export(arm):
    sc = bpy.context.scene
    for o in bpy.context.view_layer.objects: o.select_set(False)
    arm.hide_set(False); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    # the clips and the skeletal mesh go to Unreal through export_monster_ue.py (the creature importer's convention)
    # the body as it lies after the death clip: the static mesh a kill leaves (sprites 551-559)
    set_clip(arm, 'Bonca_Death', 37)
    src = next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith('_LOD0')), None) or max((o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)), key=lambda o: len(o.data.vertices))
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), depsgraph=dg)
    ob = bpy.data.objects.new('SM_Bonca_Corpse_PR', me); sc.collection.objects.link(ob); ob.matrix_world = src.matrix_world.copy()
    zmin = min((ob.matrix_world @ v.co).z for v in me.vertices)
    for v in me.vertices: v.co.z -= zmin - .004
    cx = (max(v.co.x for v in me.vertices) + min(v.co.x for v in me.vertices)) / 2; cy = (max(v.co.y for v in me.vertices) + min(v.co.y for v in me.vertices)) / 2
    for v in me.vertices: v.co.x -= cx; v.co.y -= cy                      # the body lies in the middle of its pool (the ground decal is centred on the kill)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    p = os.path.join(DIR, 'SM_Bonca_Corpse_PR.fbx')
    bpy.ops.export_scene.fbx(filepath=p, use_selection=True, object_types={'MESH'}, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='Y', axis_up='Z', bake_space_transform=False, mesh_smooth_type='FACE', use_mesh_modifiers=False, bake_anim=False, path_mode='STRIP')
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print('[CLIPS] exported', os.path.basename(p), 'size', round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - min(zs), 2))
    import json
    with open(os.path.join(DIR, 'clips.json'), 'w') as fh:
        json.dump({'Idle': {'frames': 61, 'loop': True}, 'Walk': {'frames': 25, 'loop': True, 'stride_m': 0.476, 'speed_cm_s': 119.0}, 'Run': {'frames': 17, 'loop': True, 'stride_m': 0.664, 'speed_cm_s': 249.0},
                   'Attack': {'frames': 19, 'loop': False}, 'Hit': {'frames': 11, 'loop': False}, 'Death': {'frames': 37, 'loop': False}}, fh, indent=1)


bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if 'build' in A:
    build(arm); arm.data.pose_position = 'REST'; bpy.ops.wm.save_mainfile(); arm.data.pose_position = 'POSE'
if 'review' in A: review(arm)
if 'export' in A:
    bpy.ops.wm.open_mainfile(filepath=BLEND); export(next(o for o in bpy.data.objects if o.type == 'ARMATURE'))
