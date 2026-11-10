"""Same-camera review renders of the Dink hero source (never saves the .blend).
blender -b <file.blend> -P render.py -- <outdir> <tag> [shots...]"""
import bpy, sys, math
from mathutils import Vector, Matrix, Quaternion
argv = sys.argv[sys.argv.index('--')+1:]
out, tag = argv[0], argv[1]
shots = argv[2:] or ['idle_front','idle_34','walk_34','hunch_side','chest_close','belt_close','wrist_close','wrist_side']
s = bpy.context.scene
a = bpy.data.objects['Armature']
lod0 = next(o for o in bpy.data.objects if o.type=='MESH' and o.name.endswith('_LOD0'))
for o in bpy.data.objects:
    if o.type=='MESH': o.hide_render = (o is not lod0)
idle = {pb.name: pb.rotation_quaternion.copy() for pb in a.pose.bones}
def reset():
    for pb in a.pose.bones:
        pb.rotation_mode='QUATERNION'; pb.rotation_quaternion = idle[pb.name]; pb.location=(0,0,0)
    a.data.pose_position='POSE'; bpy.context.view_layer.update()
def rot(name, axis, deg):
    pb = a.pose.bones[name]; m = pb.matrix.copy(); h = m.translation.copy()
    r = Matrix.Rotation(math.radians(deg), 4, Vector(axis))
    pb.matrix = Matrix.Translation(h) @ r @ Matrix.Translation(-h) @ m
    bpy.context.view_layer.update()
def walk():
    # mid-stride: left leg forward (-Y is the front), right leg back, opposite arms
    rot('thigh_l',(1,0,0),-28); rot('calf_l',(1,0,0),18); rot('foot_l',(1,0,0),-8)
    rot('thigh_r',(1,0,0),20); rot('calf_r',(1,0,0),30)
    rot('upperarm_r',(1,0,0),-24); rot('lowerarm_r',(1,0,0),-20)
    rot('upperarm_l',(1,0,0),18)
    rot('spine_01',(0,0,1),5); rot('pelvis',(0,0,1),-4)
def hunch():
    for b,d in [('spine_01',4),('spine_03',6),('spine_05',6),('neck_01',10),('head',12)]: rot(b,(1,0,0),d)
s.render.engine='CYCLES'; s.cycles.samples=48; s.cycles.use_denoising=True
s.render.resolution_x=900; s.render.resolution_y=1100; s.render.resolution_percentage=100
s.render.film_transparent=False
cam = s.camera
def look(loc, target, lens):
    cam.location=Vector(loc); cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=lens
def bone_head(n): return a.matrix_world @ a.pose.bones[n].head
for shot in shots:
    reset()
    if shot.startswith('rest'): a.data.pose_position='REST'; bpy.context.view_layer.update(); shot=shot[5:]
    if shot.startswith('walk'): walk()
    if shot.startswith('hunch'): hunch()
    if shot=='idle_front': look((0,-4.2,1.05),(0,0,0.95),55)
    elif shot in ('idle_34','walk_34'): look((2.4,-3.6,1.5),(0,0,0.95),55)
    elif shot=='walk_front': look((0,-4.2,1.05),(0,0,0.95),55)
    elif shot=='hunch_side': look((3.6,-0.4,1.3),(0,0,1.0),55)
    elif shot=='chest_close': look((0.25,-1.25,1.30),(0,0,1.27),70)
    elif shot=='chest_raking': look((0.9,-0.9,1.25),(0,0,1.27),80)
    elif shot in ('belt_close','walk_belt'): look((0.35,-1.0,1.08),(0,-.05,1.02),75)
    elif shot in ('belt_side','hunch_belt'): look((0.9,-0.35,1.04),(0,-.08,1.02),90)
    elif shot=='wrist_close':
        w=bone_head('hand_r'); look(w+Vector((-0.05,-0.55,0.05)), w+Vector((0,0,0.02)), 85)
    elif shot=='wrist_side':
        w=bone_head('hand_r'); look(w+Vector((-0.5,-0.15,0.08)), w+Vector((0,0,0.02)), 85)
    elif shot=='wrist_l':
        w=bone_head('hand_l'); look(w+Vector((0.35,-0.4,0.06)), w+Vector((0,0,0.02)), 85)
    elif shot=='walk_wrist':
        w=bone_head('hand_r'); look(w+Vector((-0.45,-0.35,0.05)), w, 85)
    s.render.filepath=f'{out}/{tag}_{shot}{"_rest" if a.data.pose_position=="REST" else ""}.png'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', s.render.filepath, flush=True)
