"""Props variant of Structures/tools/review.py: an assembly with "interior": [x, y, z] is lit by a warm 1900 K point light there under a dim sky instead of the sun (same exposure handling otherwise).
Review renders for a kit .blend: every module in sun at the gameplay camera (45 degrees down from 9 m) and from street level
(eye 1.5 m), plus assemblies.   blender -b -t 4 X.blend --python review.py -- DEST spec.json [only ...]
spec: {"ground": set name, "ground_tile": m, "modules": [names] | "all" | [], "assemblies": [{"name", "items": [[module, x, y, z, yaw]...],
"cams": [{"name", "loc", "tgt", "lens"}]}], "res": [w, h], "sun_rot": deg}"""
import bpy, os, sys, json, math
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
DEST = argv[0]; spec = json.load(open(argv[1])); ONLY = argv[2:]
PP = os.environ.get('DINK_PP') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs(DEST, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('SPP', '24')); sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
sc.render.image_settings.file_format = 'PNG'
try:
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
nt = w.node_tree; sky = nt.nodes.new('ShaderNodeTexSky')
ids = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
    if t in ids:
        sky.sky_type = t; break
sky.sun_elevation = math.radians(40); sky.sun_rotation = math.radians(spec.get('sun_rot', -150))
nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0]); sc.view_settings.exposure = spec.get('exposure', -4.6)
gset = spec.get('ground', 'CobbleStreet')
root = os.path.join(PP, 'Terrain')
info = json.load(open(os.path.join(root, gset, 'set.json')))
fm = bpy.data.materials.new('ground'); fm.use_nodes = True
n2 = fm.node_tree; b = n2.nodes['Principled BSDF']
def t(k, cs):
    n = n2.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(root, info['files'][k])); n.image.colorspace_settings.name = cs; return n
bc = t('BC', 'sRGB'); nm = t('N', 'Non-Color'); orm = t('ORM', 'Non-Color')
n2.links.new(bc.outputs[0], b.inputs['Base Color'])
s = n2.nodes.new('ShaderNodeSeparateColor'); n2.links.new(orm.outputs[0], s.inputs[0]); n2.links.new(s.outputs[1], b.inputs['Roughness'])
nn = n2.nodes.new('ShaderNodeNormalMap'); n2.links.new(nm.outputs[0], nn.inputs['Color']); n2.links.new(nn.outputs[0], b.inputs['Normal'])
me = bpy.data.meshes.new('floor'); S = 60.0
fh = spec.get('floor_holes', [])                 # [[x, y, half]]: square holes in the review ground (a well shaft)
if fh:
    hx_, hy_, hh_ = fh[0]
    co = [(-S, -S, 0), (S, -S, 0), (S, S, 0), (-S, S, 0), (hx_ - hh_, hy_ - hh_, 0), (hx_ + hh_, hy_ - hh_, 0), (hx_ + hh_, hy_ + hh_, 0), (hx_ - hh_, hy_ + hh_, 0)]
    me.from_pydata(co, [], [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])
else:
    co = [(-S, -S, 0), (S, -S, 0), (S, S, 0), (-S, S, 0)]
    me.from_pydata(co, [], [[0, 1, 2, 3]])
uv = me.uv_layers.new()
for p_ in me.polygons:
    for li in p_.loop_indices:
        c = co[me.loops[li].vertex_index]; uv.data[li].uv = (c[0] / info['tile_size_m'], c[1] / info['tile_size_m'])
me.materials.append(fm)
fl = bpy.data.objects.new('floor', me); sc.collection.objects.link(fl)
mods = [c for c in bpy.data.collections if c.get('dink_class')]
allobs = [o for c in mods for o in c.objects]
camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam); sc.camera = cam
camd.clip_start = 0.05


def look(loc, tgt, lens=32):
    cam.location = loc; camd.lens = lens
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def render(name):
    sc.render.filepath = os.path.join(DEST, name + '.png'); bpy.ops.render.render(write_still=True); print('RENDERED', name)


res = spec.get('res', [800, 600])
want = spec.get('modules', [])
for c in mods:
    if want != 'all' and c.name not in want:
        continue
    if ONLY and c.name not in ONLY:
        continue
    sc.render.resolution_x, sc.render.resolution_y = res
    lod0 = [o for o in c.objects if o.name.endswith('_LOD0') and not o.name.startswith('UCX')][0]
    for o in allobs:
        o.hide_render = True
    lod0.hide_render = False
    bb = [lod0.matrix_world @ Vector(v) for v in lod0.bound_box]
    lo = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb))); hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
    cen = (lo + hi) / 2
    fl.location.z = lo.z if ((lo.z < -0.01 and not spec.get('floor_zero')) or spec.get('floor_at_min')) else 0.0
    size = max(hi.x - lo.x, hi.z - lo.z, hi.y - lo.y)
    # gameplay camera: 45 degrees down, 9 m above the ground, lens chosen to frame the module
    hgt = 9.0 + fl.location.z; d = hgt - cen.z
    dist = math.sqrt(2) * d
    lens = max(24, min(120, 36 * dist / (size * 1.9) * 0.62))
    look((cen.x + 0.35 * d, cen.y - 0.94 * d, hgt), (cen.x, cen.y, cen.z), lens)
    render(c.name + '_sun')
    if not spec.get('no_close'):
        eye = fl.location.z + 1.5; zt = min(max(cen.z, fl.location.z + 0.6), fl.location.z + 2.2) if hi.z - fl.location.z < 4 else fl.location.z + 1.9
        look((cen.x + 0.9 + 0.2 * size, lo.y - 1.7 - 0.25 * size, eye), (cen.x - 0.1 * size, cen.y, zt), 26)
        render(c.name + '_close')
fl.location.z = 0.0
for A in spec.get('assemblies', []):
    if ONLY and A['name'] not in ONLY:
        continue
    for o in allobs:
        o.hide_render = True
    made = []
    for (name, x, y, z, yaw) in A['items']:
        src = bpy.data.objects[name + '_LOD0']
        o = src.copy(); sc.collection.objects.link(o); o.hide_render = False
        o.location = (x, y, z); o.rotation_euler = (0, 0, math.radians(yaw)); made.append(o)
    bg = nt.nodes['Background']; inter = A.get('interior')
    if inter:
        bg.inputs[1].default_value = 0.004; sky.sun_disc = False; sc.view_settings.exposure = A.get('exposure', 1.2)
        ld = bpy.data.lights.new('fire', 'POINT'); ld.energy = A.get('watts', 60.0); ld.color = (1.0, 0.56, 0.26); ld.shadow_soft_size = 0.06
        lo_ = bpy.data.objects.new('fire', ld); sc.collection.objects.link(lo_); lo_.location = inter; made.append(lo_)
        if A.get('fill'):
            ld2 = bpy.data.lights.new('fill', 'AREA'); ld2.energy = A['fill']; ld2.color = (0.55, 0.65, 1.0); ld2.size = 2.0
            lo2 = bpy.data.objects.new('fill', ld2); sc.collection.objects.link(lo2); lo2.location = (-3.0, -4.0, 2.5); lo2.rotation_euler = (math.radians(60), 0, math.radians(-35)); made.append(lo2)
    else:
        bg.inputs[1].default_value = 1.0; sky.sun_disc = True; sc.view_settings.exposure = spec.get('exposure', -4.6)
    for cm in A['cams']:
        sc.render.resolution_x, sc.render.resolution_y = cm.get('res', [1300, 850])
        look(cm['loc'], cm['tgt'], cm.get('lens', 32))
        render(A['name'] + '_' + cm['name'])
    for o in made:
        bpy.data.objects.remove(o)
print('REVIEW DONE')
