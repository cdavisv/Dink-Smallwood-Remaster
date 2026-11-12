"""Blender previews of the SCR_440 kit (opens KIT_Stonebrook440.blend read-only; never saves it).

    blender -b --factory-startup -t 3 -P render_previews.py -- house|props|closeup|layout [--samples N] [--res WxH] [--out file]

house    beauty shot of the two-storey house with yard dressing
props    lineup of all props with a 1.75 m scale post
closeup  close material check of tools, block and barrow
layout   SCR_440 as laid out by layout_440.json, emulating the Unreal transform (see layout_ue_emulation)
"""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Euler

ART = Path(__file__).resolve().parent
UE = ART.parents[2]
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['house']
MODE = argv[0]
SAMPLES = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 48
RES = [int(v) for v in argv[argv.index('--res') + 1].split('x')] if '--res' in argv else [1600, 1000]
OUT = argv[argv.index('--out') + 1] if '--out' in argv else str(ART / f'preview_{MODE}.png')

bpy.ops.wm.open_mainfile(filepath=str(ART / 'KIT_Stonebrook440.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = RES; scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.film_transparent = False
scene.cycles.max_bounces = 6
scene.view_settings.exposure = -0.6

assets = {c.name: c for c in bpy.data.collections if c.get('dink_class')}
for c in assets.values():
    for ob in c.objects:
        ob.hide_render = ob.name.startswith('UCX_') or '_LOD1' in ob.name or '_LOD2' in ob.name


def lod0(name):
    c = assets[name]
    return next(o for o in c.objects if o.name.endswith('_LOD0') or o.name == name)


def move_asset(name, loc, rot_z=0.0, M=None):
    if name not in assets:
        return
    for ob in assets[name].objects:
        if M is not None:
            ob.matrix_world = M
        else:
            ob.location = loc; ob.rotation_euler = (0, 0, rot_z)


def hide_all_but(names):
    for n, c in assets.items():
        for ob in c.objects:
            if n not in names:
                ob.hide_render = True


# ----------------------------------------------------------------------------- environment
def ground(size=600, mat_name='GroundMeadow'):
    mat = bpy.data.materials.new(mat_name); mat.use_nodes = True
    nt = mat.node_tree; bs = nt.nodes['Principled BSDF']
    shared = UE / 'SourceAssets/Art/StonebrookExterior/Textures'
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / 2.5, 1 / 2.5, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    for s in ('BC', 'N', 'ORM'):
        img = bpy.data.images.load(str(shared / f'T_Stonebrook_Meadow_{s}.png'), check_existing=True)
        img.colorspace_settings.name = 'sRGB' if s == 'BC' else 'Non-Color'
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = img; nt.links.new(mp.outputs[0], n.inputs[0])
        if s == 'BC':
            nt.links.new(n.outputs[0], bs.inputs['Base Color'])
        elif s == 'N':
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .5
            nt.links.new(n.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
        else:
            sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(n.outputs[0], sp.inputs[0]); nt.links.new(sp.outputs[1], bs.inputs['Roughness'])
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    g = bpy.context.object; g.name = 'PreviewGround'; g.data.materials.append(mat)
    return g


def sky_and_sun(sun_rot=(math.radians(52), 0, math.radians(-35)), energy=3.2):
    world = bpy.data.worlds.new('PreviewWorld'); scene.world = world; world.use_nodes = True
    nt = world.node_tree; bg = nt.nodes['Background']
    try:
        sky = nt.nodes.new('ShaderNodeTexSky')
        for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'HOSEK_WILKIE'):
            try:
                sky.sky_type = t; break
            except TypeError:
                continue
        try:
            sky.sun_disc = False
            sky.sun_elevation = math.radians(90 - math.degrees(sun_rot[0])); sky.sun_rotation = sun_rot[2] + math.pi
        except AttributeError:
            pass
        nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = .12
    except Exception:
        bg.inputs[0].default_value = (.55, .68, .85, 1); bg.inputs[1].default_value = .5
    sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = energy; sun.angle = math.radians(1.5); sun.color = (1, .96, .9)
    so = bpy.data.objects.new('Sun', sun); scene.collection.objects.link(so); so.rotation_euler = sun_rot


def camera(loc, target, lens=40):
    cam = bpy.data.cameras.new('PreviewCam'); cam.lens = lens; cam.clip_end = 500
    co = bpy.data.objects.new('PreviewCam', cam); scene.collection.objects.link(co)
    co.location = loc; co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co
    return co


def link_kit(blend, names):
    """Link (read-only) collections from an existing kit for context."""
    out = {}
    with bpy.data.libraries.load(str(blend), link=True) as (src, dst):
        dst.collections = [n for n in names if n in src.collections]
    for c in dst.collections:
        out[c.name] = c
    return out


def instance(coll, M, hide_lods=True):
    e = bpy.data.objects.new('I_' + coll.name, None); e.instance_type = 'COLLECTION'; e.instance_collection = coll
    e.matrix_world = M; scene.collection.objects.link(e)
    return e


# ----------------------------------------------------------------------------- modes
if MODE == 'house':
    ground(); sky_and_sun()
    camera((15.5, -21.5, 4.2), (0.3, 0, 4.1), lens=34)
    house = 'SM_House_Stonebrook_TwoStorey_01'
    hide_all_but([house, 'SM_Pitchfork_Ash_01', 'SM_Scythe_Ash_01', 'SM_Woodpile_Split_01', 'SM_ChoppingBlock_Axe_01', 'SM_Wheelbarrow_Oak_01',
                  'SM_HayBale_01', 'SM_WaterTrough_Oak_01', 'SM_Shovel_Ash_01'])
    move_asset(house, (0, 0, 0))
    move_asset('SM_Woodpile_Split_01', (6.15, 2.4, 0), math.pi / 2)
    move_asset('SM_ChoppingBlock_Axe_01', (8.2, -3.0, 0), .6)
    move_asset('SM_Wheelbarrow_Oak_01', (9.0, -.4, 0), 2.3)
    move_asset('SM_HayBale_01', (10.5, 2.0, 0), .2)
    move_asset('SM_WaterTrough_Oak_01', (-8.2, -2.6, 0), math.pi / 2)
    # tools leaning on the east wall (rotation about the wall tangent)
    for name, y in (('SM_Pitchfork_Ash_01', -1.4), ('SM_Scythe_Ash_01', -2.3), ('SM_Shovel_Ash_01', -3.2)):
        M = Matrix.Translation((5.5 + .42, y, 0)) @ Matrix.Rotation(math.radians(-14), 4, 'Y') @ Matrix.Rotation(math.pi / 2, 4, 'Z')
        move_asset(name, None, M=M)
elif MODE == 'props':
    ground(60); sky_and_sun(energy=2.8)
    rows = [['SM_Pitchfork_Ash_01', 'SM_Scythe_Ash_01', 'SM_Hoe_Ash_01', 'SM_Shovel_Ash_01', 'SM_Axe_Felling_01', 'SM_Hatchet_01', 'SM_Tongs_Iron_01'],
            ['SM_ChoppingBlock_Axe_01', 'SM_HayBale_01', 'SM_WaterTrough_Oak_01', 'SM_Wheelbarrow_Oak_01', 'SM_Woodpile_Split_01']]
    hide_all_but(rows[0] + rows[1])
    for ry, row in zip((0.0, 2.4), rows):
        x = 0.0
        for n in row:
            d = lod0(n).dimensions; w = d.x if n != 'SM_Wheelbarrow_Oak_01' else d.y
            x += w / 2; move_asset(n, (x - (2.6 if ry == 0 else 3.4), ry, 0), math.pi / 2 if n == 'SM_Wheelbarrow_Oak_01' else 0); x += w / 2 + .3
    x = 6.0
    # 1.75 m scale post with 25 cm bands
    for k in range(7):
        bpy.ops.mesh.primitive_cylinder_add(radius=.03, depth=.25, location=(-3.0, -.5, .125 + k * .25))
        m = bpy.data.materials.new('band%d' % k); m.diffuse_color = (.8, .1, .1, 1) if k % 2 else (.9, .9, .9, 1)
        m.use_nodes = True; m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = m.diffuse_color
        bpy.context.object.data.materials.append(m)
    camera((.2, -6.2, 2.9), (.2, 1.2, .45), lens=38)
elif MODE == 'closeup':
    ground(30); sky_and_sun(energy=3.0)
    order = ['SM_Pitchfork_Ash_01', 'SM_Shovel_Ash_01', 'SM_ChoppingBlock_Axe_01', 'SM_Hatchet_01', 'SM_Tongs_Iron_01', 'SM_Wheelbarrow_Oak_01']
    hide_all_but(order)
    move_asset('SM_ChoppingBlock_Axe_01', (0, 0, 0), .3)
    move_asset('SM_Hatchet_01', (.45, -.55, 0), 2.6)
    move_asset('SM_Tongs_Iron_01', (-.2, -.7, 0), .4)
    move_asset('SM_Wheelbarrow_Oak_01', (-1.3, .8, 0), -.9)
    move_asset('SM_Pitchfork_Ash_01', None, M=Matrix.Translation((.9, .6, 0)) @ Matrix.Rotation(math.radians(-12), 4, 'X'))
    move_asset('SM_Shovel_Ash_01', None, M=Matrix.Translation((1.3, .7, 0)) @ Matrix.Rotation(math.radians(-10), 4, 'X') @ Matrix.Rotation(.5, 4, 'Z'))
    camera((1.6, -2.6, 1.25), (0.15, 0.1, .45), lens=40)
elif MODE == 'detail':
    ground(30); sky_and_sun(sun_rot=(math.radians(58), 0, math.radians(-50)), energy=3.0)
    order = ['SM_HayBale_01', 'SM_ChoppingBlock_Axe_01', 'SM_Woodpile_Split_01']
    hide_all_but(order)
    move_asset('SM_Woodpile_Split_01', (0, .9, 0), 0)
    move_asset('SM_HayBale_01', (-.75, -.45, 0), .35)
    move_asset('SM_ChoppingBlock_Axe_01', (.75, -.35, 0), 2.2)
    camera((.2, -2.9, 1.15), (0, .1, .42), lens=36)
elif MODE == 'layout':
    sys.path.insert(0, str(ART)); import layout_preview
    layout_preview.build(scene, assets, link_kit, instance, ground, sky_and_sun, camera, ART, UE)
if '--cam' in argv:
    v = [float(x) for x in argv[argv.index('--cam') + 1].split(',')]
    camera(tuple(v[:3]), tuple(v[3:6]), lens=v[6] if len(v) > 6 else 40)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print('PREVIEW WRITTEN', OUT)
