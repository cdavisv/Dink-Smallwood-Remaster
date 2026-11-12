"""Review renders of the wall kit: each module in sun-and-sky and in a dim torch-lit interior.
blender -b -t 4 WallKits.blend --python wallkit_review.py -- OUTDIR [name-substring ...]"""
import bpy, os, sys, json, math
import numpy as np
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
TERRAIN = os.path.join(os.path.dirname(OUT), 'Terrain')
argv = sys.argv[sys.argv.index('--') + 1:]
DEST = argv[0]; ONLY = argv[1:]
os.makedirs(DEST, exist_ok=True)
SPP = int(os.environ.get('SPP', '28'))
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.render.resolution_x = 800; sc.render.resolution_y = 600
sc.render.image_settings.file_format = 'PNG'
try:
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass


def floor_mat(setname):
    info = json.load(open(os.path.join(TERRAIN, setname, 'set.json')))
    m = bpy.data.materials.new('floor_' + setname); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    def t(k, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(TERRAIN, info['files'][k]), check_existing=True); n.image.colorspace_settings.name = cs; return n
    bc = t('BC', 'sRGB'); nm = t('N', 'Non-Color'); orm = t('ORM', 'Non-Color')
    nt.links.new(bc.outputs[0], b.inputs['Base Color'])
    s = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs[0], s.inputs[0]); nt.links.new(s.outputs[1], b.inputs['Roughness'])
    n = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(nm.outputs[0], n.inputs['Color']); nt.links.new(n.outputs[0], b.inputs['Normal'])
    return m, info['tile_size_m']


FM = {'Plaster': floor_mat('PlankFloor'), 'Dungeon': floor_mat('DungeonFlagstone')}


def floor(cx, kind):
    mat, T = FM[kind]
    me = bpy.data.meshes.new('floor'); s = 9.0
    me.from_pydata([(cx - s, -s, 0), (cx + s, -s, 0), (cx + s, s, 0), (cx - s, s, 0)], [], [[0, 1, 2, 3]])
    uv = me.uv_layers.new()
    for l, c in zip(uv.data, [(-s, -s), (s, -s), (s, s), (-s, s)]):
        l.uv = (c[0] / T, c[1] / T)
    me.materials.append(mat)
    ob = bpy.data.objects.new('floor', me); sc.collection.objects.link(ob)
    return ob


def world(mode):
    w = bpy.data.worlds.new('w_' + mode); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    if mode == 'sun':
        sky = nt.nodes.new('ShaderNodeTexSky')
        ids = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
        for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
            if t in ids:
                sky.sky_type = t; break
        sky.sun_elevation = math.radians(40); sky.sun_rotation = math.radians(-150)
        nt.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 1.0
        sc.view_settings.exposure = -4.6
    else:
        bg.inputs[0].default_value = (0.02, 0.03, 0.05, 1); bg.inputs[1].default_value = 0.35
        sc.view_settings.exposure = 1.2


mods = [c for c in bpy.data.collections if c.get('dink_class')]
allobs = [o for c in mods for o in c.objects]
torch = bpy.data.lights.new('torch', 'POINT'); torch.energy = 55; torch.color = (1.0, 0.56, 0.24); torch.shadow_soft_size = 0.06
tob = bpy.data.objects.new('torch', torch); sc.collection.objects.link(tob)
camd = bpy.data.cameras.new('cam'); camd.lens = 32
cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam); sc.camera = cam
for c in mods:
    if ONLY and not any(s in c.name for s in ONLY):
        continue
    if ONLY == ['room']:
        continue
    lod0 = [o for o in c.objects if o.name.endswith('_LOD0') and not o.name.startswith('UCX')][0]
    for o in allobs:
        o.hide_render = True
    lod0.hide_render = False
    bb = [lod0.matrix_world @ Vector(v) for v in lod0.bound_box]
    lo = Vector((min(p.x for p in bb), min(p.y for p in bb), 0)); hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
    cen = (lo + hi) / 2
    kind = 'Plaster' if 'Plaster' in c.name else 'Dungeon'
    fl = floor(cen.x, kind)
    size = max(hi.x - lo.x, hi.z)
    dist = 1.25 * size + 2.2
    cam.location = (cen.x + 0.42 * dist, lo.y - 0.9 * dist, 1.6)
    tgt = Vector((cen.x, cen.y, hi.z * 0.47))
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for mode in ('sun', 'torch'):
        world(mode)
        tob.hide_render = (mode == 'sun')
        tob.location = (cen.x - 0.9, lo.y - 1.3, 1.9)
        sc.render.filepath = os.path.join(DEST, '%s_%s.png' % (c.name, mode))
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(fl)
    print('RENDERED', c.name)

# ---- assembled rooms: a corner with a door, seen as the game camera sees it (high, about 45 degrees down)
ROOMS = {
 'Plaster': [('CornerPost_L', 0, 0, 0), ('Straight_B', 2.5, 0, 0), ('DoorJamb_L', 5.0, 0, 0), ('DoorHeader', 5.45, 0, 0), ('DoorJamb_R', 6.45, 0, 0), ('End_R', 6.9, 0, 0),
             ('Straight_A', 0.09, 0, -90), ('End_R', 0.09, -2.5, -90)],
 'Dungeon': [('Straight_A', 0, 0, 0), ('Ivy', 2.5, 0, 0), ('Arch', 5.0, 0, 0), ('Breach', 7.5, 0, 0), ('Curve', 0, 0, 180), ('Straight_B', -2.5, -2.5, -90), ('Half', -2.5, -5.0, -90)],
}
if not ONLY or 'room' in ONLY:
    for kind, items in ROOMS.items():
        for o in allobs:
            o.hide_render = True
        made = []
        for (nm, x, y, yaw) in items:
            src = bpy.data.objects['SM_Wall_%s_%s_LOD0' % (kind, nm)]
            o = src.copy(); sc.collection.objects.link(o); o.hide_render = False
            o.location = (x, y, 0); o.rotation_euler = (0, 0, math.radians(yaw)); made.append(o)
        fl = floor(4.0, kind)
        cx = 4.2 if kind == 'Plaster' else 3.5
        cam.location = (cx + 1.0, -9.0, 8.6)
        tgt = Vector((cx, -1.2, 0.9))
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        camd.lens = 30
        for mode in ('sun', 'torch'):
            world(mode)
            tob.hide_render = (mode == 'sun'); tob.location = (3.0, -2.2, 2.0); torch.energy = 160
            sc.render.resolution_x = 1200; sc.render.resolution_y = 800
            sc.render.filepath = os.path.join(DEST, 'Room_%s_%s.png' % (kind, mode))
            bpy.ops.render.render(write_still=True)
        for o in made:
            bpy.data.objects.remove(o)
        bpy.data.objects.remove(fl)
        print('ROOM', kind)
print('REVIEW DONE')
