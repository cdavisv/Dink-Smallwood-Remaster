"""Review renders of the ground decal sheets (Corpses/Decals picture decals, Props/Decals class cells) for a look WITHOUT the
game: each cell laid on a ground plane at the size the game gives it (environment.json decals: the square of the placement's
card x 1.15), under a sun, from the play camera (6.5 m south, 5.2 m up, 60 degrees), from near and from low. Cycles, CPU.
  DINK_CPU=1 ../Unclaimed/tools/bl.sh ../../Corpses/tools/review_decals.py <out folder> [case,case...]     (from Unclaimed/)
A decal in the game is a deferred decal (it replaces base colour, normal and roughness of the ground under it by its alpha);
here it is a quad 2 mm above the ground with the same maps, which shades the same way on flat ground. What this cannot show:
the game's ground, grass, exposure and the decal on a slope."""
import bpy, math, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); PASS = os.path.dirname(os.path.dirname(HERE))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else os.path.join(PASS, 'Corpses', '_review'); os.makedirs(OUT, exist_ok=True)
ONLY = set(argv[1].split(',')) if len(argv) > 1 else None

# name: (folder, set, cell, side m, ground)   side: 1.15 x the longer side of a placement's card (the median one unless said)
CASES = {
    'blood_187_01': ('Corpses', 'Blood1997A', 0, 0.92, 'dirt'),      # S094_P03
    'blood_187_02': ('Corpses', 'Blood1997A', 1, 0.60, 'dirt'),      # S094_P04, P05
    'blood_187_03': ('Corpses', 'Blood1997A', 2, 1.61, 'dirt'),      # S094_P02
    'blood_188_02': ('Corpses', 'Blood1997A', 3, 1.09, 'grass'),     # S094_P06..P08, S126_P05
    'blood_188_04': ('Corpses', 'Blood1997B', 0, 1.24, 'dirt'),      # 19 placements, 0.61 to 3.91 m
    'blood_188_04_big': ('Corpses', 'Blood1997B', 0, 3.91, 'dirt'),  # S091_P09, the largest
    'blood_189_01': ('Corpses', 'Blood1997B', 1, 0.78, 'grass'),     # S122_P11
    'blood_189_02': ('Corpses', 'Blood1997B', 2, 1.12, 'dirt'),      # S126_P02, P03
    'blood_189_04': ('Corpses', 'Blood1997B', 3, 1.61, 'grass'),     # 15 placements, 0.85 to 1.61 m
    'burn_158_01': ('Corpses', 'Burn1997', 0, 2.56, 'dirt'),         # S533, S536
    'burn_158_02': ('Corpses', 'Burn1997', 1, 2.59, 'grass'),
    'burn_158_03': ('Corpses', 'Burn1997', 2, 2.12, 'dirt'),
    'burn_158_03_big': ('Corpses', 'Burn1997', 2, 4.76, 'grass'),    # S439_P26
    'class_burn_0': ('Props', 'BurnHole', 0, 2.56, 'dirt'),          # what master lays on a 158 actor placement today
    'class_burn_3': ('Props', 'BurnHole', 3, 2.59, 'grass'),
    'class_blood_0': ('Props', 'BloodSplat', 0, 1.24, 'dirt'),       # the class cell (no placed frame takes it once `pictures` is in)
}
GROUNDS = {'dirt': ((0.30, 0.22, 0.15), (0.20, 0.15, 0.10)), 'grass': ((0.10, 0.20, 0.035), (0.06, 0.13, 0.025))}


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32; sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = 800, 500; sc.render.image_settings.file_format = 'PNG'; sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.55, 0.68, 1.0, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.55
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.2; sun.data.angle = math.radians(2.0)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-35)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.sensor_fit = 'HORIZONTAL'
    return sc, cam


def aim(cam, pos, at, fov):
    cam.location = pos; cam.data.angle = math.radians(fov); cam.rotation_euler = (Vector(at) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()


def ground(kind):
    a, b = GROUNDS[kind]; m = bpy.data.materials.new('ground_' + kind); m.use_nodes = True; nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
    n1 = nt.nodes.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 3.0; n1.inputs['Detail'].default_value = 8.0
    n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 90.0; n2.inputs['Detail'].default_value = 4.0
    mix = nt.nodes.new('ShaderNodeMixRGB'); mix.inputs[1].default_value = (*a, 1); mix.inputs[2].default_value = (*b, 1); nt.links.new(n1.outputs[0], mix.inputs[0])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.5; bump.inputs['Distance'].default_value = 0.02; nt.links.new(n2.outputs[0], bump.inputs['Height'])
    nt.links.new(mix.outputs[0], bsdf.inputs['Base Color']); nt.links.new(bump.outputs[0], bsdf.inputs['Normal']); bsdf.inputs['Roughness'].default_value = 0.9
    bpy.ops.mesh.primitive_plane_add(size=60); o = bpy.context.object; o.data.materials.append(m); return o


def decal(folder, name, cell, side):
    d = os.path.join(PASS, folder, 'Decals'); m = bpy.data.materials.new('decal'); m.use_nodes = True; nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
    def tex(key, colour):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(d, 'T_Decal_%s_%s.png' % (name, key))); t.extension = 'EXTEND'
        if t.image.size[0] < 16: raise SystemExit('not an image (an LFS pointer?): ' + t.image.filepath)
        if not colour: t.image.colorspace_settings.name = 'Non-Color'
        return t
    bc, nm, orm = tex('BC', True), tex('N', False), tex('ORM', False)
    nmap = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(nm.outputs['Color'], nmap.inputs['Color']); sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs['Color'], sep.inputs[0])
    nt.links.new(bc.outputs['Color'], bsdf.inputs['Base Color']); nt.links.new(bc.outputs['Alpha'], bsdf.inputs['Alpha']); nt.links.new(nmap.outputs[0], bsdf.inputs['Normal']); nt.links.new(sep.outputs[1], bsdf.inputs['Roughness'])
    bpy.ops.mesh.primitive_plane_add(size=1); o = bpy.context.object; o.scale = (side, side, 1); o.location = (0, 0, 0.002); o.data.materials.append(m); o.visible_shadow = False
    i, j = cell % 2, cell // 2; uv = o.data.uv_layers.active.data                # image row 0 is the top (north) half
    for l in uv: l.uv = (0.5 * i + 0.5 * l.uv[0], 0.5 * (1 - j) + 0.5 * l.uv[1])
    return o


sc, cam = setup()
for key, (folder, name, cell, side, gkind) in CASES.items():
    if ONLY and key not in ONLY: continue
    for o in [o for o in bpy.data.objects if o.type == 'MESH']: bpy.data.objects.remove(o, do_unlink=True)
    ground(gkind); decal(folder, name, cell, side)
    for view, pos, at, fov in (('play', (0, -6.5, 5.2), (0, 0, 0), 60), ('near', (0, -1.25 * side - 0.6, 1.0 * side + 0.5), (0, 0, 0), 50), ('low', (0.4 * side, -1.6 * side - 0.8, 0.45 * side + 0.3), (0, 0, 0), 45)):
        aim(cam, pos, at, fov); sc.render.filepath = os.path.join(OUT, '%s_%s.png' % (key, view)); bpy.ops.render.render(write_still=True)
print('review renders in', OUT)
