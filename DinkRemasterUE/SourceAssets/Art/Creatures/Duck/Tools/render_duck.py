"""Review renders: beauty three-quarter, turnaround and per-clip frames (Cycles, low samples).

    blender -b --factory-startup -t 3 --python Tools/render_duck.py -- [blend] [--quick] [--only beauty,turn,clips]

Frames go to Working/frames; Tools/make_sheets.py (python3 + Pillow) composes the
contact sheets into Previews/.  The stage lives in its own `Preview_Stage`
collection outside the asset collection and is never saved into the source.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
quick = '--quick' in argv
only = None
if '--only' in argv:
    only = argv[argv.index('--only') + 1].split(',')
blend = next((a for a in argv if a.endswith('.blend')), str(D.ROOT / 'SK_Duck.blend'))
OUT = Path(argv[argv.index('--out') + 1]) if '--out' in argv else D.PREVIEWS
bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene
arm = bpy.data.objects['Armature']
lod0 = bpy.data.objects[D.LOD0]
headless = bpy.data.objects.get('SK_Duck_Headless_LOD0')
head_prop = bpy.data.objects.get('SM_Duck_Head_LOD0')
for ob in bpy.data.objects:
    if ob.type == 'MESH' and (ob.name.startswith('SK_Duck') or ob.name.startswith('SM_Duck') or ob.name.startswith('UCX_')):
        ob.hide_render = ob is not lod0


def variant(name):
    lod0.hide_render = name != 'intact'
    if headless:
        headless.hide_render = name != 'headless'
FR = D.WORKING / 'frames'
FR.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

stage = bpy.data.collections.new('Preview_Stage')
scene.collection.children.link(stage)


def link(ob):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    stage.objects.link(ob)


# Ground: short grass over packed earth, procedural.
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
ground = bpy.context.object
ground.name = 'Preview ground'
link(ground)
gm = bpy.data.materials.new('Preview ground')
gm.use_nodes = True
nt = gm.node_tree
bs = nt.nodes['Principled BSDF']
tc = nt.nodes.new('ShaderNodeTexCoord')
n1 = nt.nodes.new('ShaderNodeTexNoise')
n1.inputs['Scale'].default_value = 18
n1.inputs['Detail'].default_value = 8
n2 = nt.nodes.new('ShaderNodeTexNoise')
n2.inputs['Scale'].default_value = 260
n2.inputs['Detail'].default_value = 4
nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.055, 0.075, 0.025, 1)
ramp.color_ramp.elements[1].color = (0.13, 0.105, 0.065, 1)
ramp.color_ramp.elements[0].position = 0.42
ramp.color_ramp.elements[1].position = 0.62
nt.links.new(n1.outputs['Fac'], ramp.inputs[0])
nt.links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
bs.inputs['Roughness'].default_value = 0.95
bump = nt.nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.35
bump.inputs['Distance'].default_value = 0.002
nt.links.new(n2.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
ground.data.materials.append(gm)

world = bpy.data.worlds.new('DuckDaylight')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.42, 0.52, 0.68, 1)
bg.inputs['Strength'].default_value = 0.85
sun_d = bpy.data.lights.new('Sun', 'SUN')
sun_d.energy = 3.2
sun_d.angle = math.radians(2.0)
sun_d.color = (1.0, 0.95, 0.88)
sun = bpy.data.objects.new('Sun', sun_d)
stage.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
fill_d = bpy.data.lights.new('Bounce', 'AREA')
fill_d.energy = 20
fill_d.size = 2.0
fill_d.color = (0.85, 0.9, 1.0)
fill = bpy.data.objects.new('Bounce', fill_d)
stage.objects.link(fill)
fill.location = (-1.2, 1.5, 1.2)
fill.rotation_euler = (Vector((0, 0, 0.2)) - fill.location).to_track_quat('-Z', 'Y').to_euler()

camd = bpy.data.cameras.new('Review')
cam = bpy.data.objects.new('Review', camd)
stage.objects.link(cam)
scene.camera = cam
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False


def shoot(path, loc, target=(0.01, 0, 0.22), lens=85, res=(1600, 1200), samples=96, dof=True):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    camd.lens = lens
    camd.dof.use_dof = dof
    camd.dof.focus_distance = (Vector(target) - Vector(loc)).length
    camd.dof.aperture_fstop = 5.6
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.cycles.samples = 24 if quick else samples
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


arm.data.pose_position = 'POSE'


def pose(action, frame):
    variant('headless' if 'Headless' in action else 'intact')
    act = bpy.data.actions[action]
    arm.animation_data.action = act
    if arm.animation_data.action_slot is None and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    scene.frame_set(frame)


if only is None or 'game' in only:
    # third-person game camera: ~4 m away, ~1.7 m eye height, 35 mm lens
    pose('Duck_Idle', 1)
    ang = math.radians(-50)
    shoot(OUT / 'preview_duck_game_distance.png', (4.0 * math.cos(ang), 4.0 * math.sin(ang), 1.70), target=(0.0, 0, 0.22),
          lens=35, res=(1280, 720), samples=96, dof=False)
if only is None or 'beauty' in only:
    pose('Duck_Idle', 1)
    shoot(OUT / 'preview_duck_beauty.png', (1.05, -1.05, 0.42), target=(0.02, 0, 0.23), res=(1600, 1200), samples=128)
    shoot(OUT / 'preview_duck_head_closeup.png', (0.55, -0.42, 0.50), target=(0.17, 0, 0.42), lens=100, res=(1200, 900), samples=128)
if only is None or 'turn' in only:
    pose('Duck_Idle', 1)
    for i, ang in enumerate([0, 60, 120, 180, 240, 300]):
        a = math.radians(ang - 90)
        loc = (1.45 * math.cos(a), 1.45 * math.sin(a), 0.40)
        shoot(FR / ('turn_%d.png' % i), loc, target=(0.0, 0, 0.23), lens=70, res=(640, 560), samples=48, dof=False)
if only is None or 'clips' in only:
    for name, spec in D.ACTIONS.items():
        n = spec['frames']
        picks = sorted({1 + round(i * (n - 1) / 4) for i in range(5)}) if not spec['loop'] else sorted({1 + round(i * (n - 1) / 5) for i in range(5)})
        for j, f in enumerate(picks):
            pose(name, f)
            shoot(FR / ('clip_%s_%02d_f%03d.png' % (name, j, f)), (0.95, -1.05, 0.45), target=(0.02, 0, 0.18), lens=60, res=(480, 400), samples=32, dof=False)
if (only is None or 'gore' in only) and headless and head_prop:
    # faithful original: head off, body still strutting; head lying in its blood beside it
    import bmesh as _bm  # noqa: F401
    from mathutils import Matrix as _M
    hp = head_prop.copy()
    hp.data = head_prop.data.copy()
    stage.objects.link(hp)
    hp.hide_render = False
    hp.data.transform(_M.Rotation(math.radians(84), 4, 'X'))
    zmin = min(v.co.z for v in hp.data.vertices)
    hp.location = (0.30, -0.20, -zmin)
    hp.rotation_euler = (0, 0, math.radians(-150))
    for key in ('BloodPool',):
        img = bpy.data.images.load(str(D.TEXTURES / ('T_Duck_%s_BC.png' % key)))
        dm = bpy.data.materials.new('Preview blood pool')
        dm.use_nodes = True
        dn = dm.node_tree
        b = dn.nodes['Principled BSDF']
        t = dn.nodes.new('ShaderNodeTexImage')
        t.image = img
        dn.links.new(t.outputs['Color'], b.inputs['Base Color'])
        dn.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
        b.inputs['Roughness'].default_value = 0.12
        bpy.ops.mesh.primitive_plane_add(size=0.30, location=(0.30, -0.19, 0.0006))
        pool = bpy.context.object
        link(pool)
        pool.data.materials.append(dm)
        bpy.ops.object.mode_set(mode='OBJECT')
    pose('Duck_HeadlessRun', 3)
    shoot(D.PREVIEWS / 'preview_duck_headless_gore.png', (0.95, -0.95, 0.42), target=(0.12, -0.05, 0.16), res=(1600, 1200), samples=128)
    shoot(D.PREVIEWS / 'preview_duck_stump_closeup.png', (0.32, -0.30, 0.48), target=(0.09, 0, 0.30), lens=100, res=(1200, 900), samples=128)
    shoot(D.PREVIEWS / 'preview_duck_head_prop.png', (0.30, -0.62, 0.22), target=(0.30, -0.20, 0.03), lens=85, res=(1200, 900), samples=128)
    hp.hide_render = True
    pool.hide_render = True
print('DUCK RENDERS DONE', flush=True)
