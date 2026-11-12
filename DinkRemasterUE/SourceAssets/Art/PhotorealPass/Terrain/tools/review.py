"""Cycles review renders of terrain sets.  blender -b -t 4 --python review.py -- OUTDIR Name [Name ...]
Per set: eye view (1.7 m, 30 deg down), 1 m close-up, 4x4 tiling check; sun elevation 25 deg, Nishita sky."""
import bpy, sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN = os.path.dirname(HERE)
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
NAMES = argv[1:]
os.makedirs(OUT, exist_ok=True)
SPP = int(os.environ.get('SPP', '40'))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = SPP
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    sc.render.resolution_x = 1100
    sc.render.resolution_y = 620
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    w = bpy.data.worlds.new('W')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky')
    ids = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
        if t in ids:
            sky.sky_type = t
            break
    sky.sun_elevation = math.radians(25)
    sky.sun_rotation = math.radians(-125)
    try:
        sky.sun_size = math.radians(1.0)
    except Exception:
        pass
    bg = nt.nodes['Background']
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 1.0
    sc.view_settings.exposure = float(os.environ.get('EXPO', '-4.3'))
    return sc


def grid(name, x0, y0, sx, sy, nx, ny, T, H, hr, blur_px=0):
    xs = np.linspace(x0, x0 + sx, nx)
    ys = np.linspace(y0, y0 + sy, ny)
    X, Y = np.meshgrid(xs, ys)
    n = H.shape[0]
    u = (X / T) % 1.0
    v = (Y / T) % 1.0
    fx = u * n - 0.5
    fy = (1 - v) * n - 0.5
    ix = np.floor(fx).astype(int); iy = np.floor(fy).astype(int)
    tx = fx - ix; ty = fy - iy
    def g(a, b): return H[a % n, b % n]
    Z = (g(iy, ix) * (1 - tx) + g(iy, ix + 1) * tx) * (1 - ty) + (g(iy + 1, ix) * (1 - tx) + g(iy + 1, ix + 1) * tx) * ty
    Z = Z * hr
    V = np.stack([X, Y, Z], -1).reshape(-1, 3).astype(np.float32)
    idx = np.arange(nx * ny).reshape(ny, nx)
    Q = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
    me.loops.add(Q.size); me.loops.foreach_set('vertex_index', Q.ravel().astype(np.int32))
    me.polygons.add(len(Q)); me.polygons.foreach_set('loop_start', (np.arange(len(Q)) * 4).astype(np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(len(Q), bool))
    me.update(calc_edges=True)
    uv = me.uv_layers.new(name='UV')
    UV = np.stack([X / T, Y / T], -1).reshape(-1, 2).astype(np.float32)
    uv.data.foreach_set('uv', UV[Q.ravel()].ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def material(info):
    m = bpy.data.materials.new('M'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    def tex(key, cs):
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(os.path.join(TERRAIN, info['files'][key]))
        t.image.colorspace_settings.name = cs
        return t
    bc = tex('BC', 'sRGB'); nm = tex('N', 'Non-Color'); orm = tex('ORM', 'Non-Color')
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs[0], sep.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 0.45
    nt.links.new(bc.outputs[0], mix.inputs[6]); nt.links.new(sep.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    nt.links.new(sep.outputs[1], b.inputs['Roughness'])
    nmap = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(nm.outputs[0], nmap.inputs['Color'])
    nmap.inputs['Strength'].default_value = 1.0
    nt.links.new(nmap.outputs[0], b.inputs['Normal'])
    if 'E' in info['files']:
        e = tex('E', 'Non-Color')
        ramp = nt.nodes.new('ShaderNodeMix'); ramp.data_type = 'RGBA'
        ramp.inputs[6].default_value = (1.0, 0.12, 0.0, 1); ramp.inputs[7].default_value = (1.0, 0.75, 0.25, 1)
        nt.links.new(e.outputs[0], ramp.inputs[0])
        nt.links.new(ramp.outputs[2], b.inputs['Emission Color'])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 22.0
        nt.links.new(e.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], b.inputs['Emission Strength'])
    return m


def cam(name, loc, pitch_down_deg, lens=35, yaw=0.0):
    c = bpy.data.cameras.new(name); c.lens = lens; c.clip_start = 0.02; c.clip_end = 200
    o = bpy.data.objects.new(name, c)
    o.location = loc
    o.rotation_euler = (math.radians(90 - pitch_down_deg), 0, yaw)
    bpy.context.scene.collection.objects.link(o)
    return o


man = json.load(open(os.path.join(TERRAIN, 'manifest.json')))
for name in NAMES:
    info = [s for s in man['sets'] if s['name'] == name][0]
    sc = reset()
    T = info['tile_size_m']; hr = info['height_range_m']
    img = bpy.data.images.load(os.path.join(TERRAIN, info['files']['H']))
    w = img.size[0]
    H = np.empty(w * w * 4, np.float32); img.pixels.foreach_get(H)
    H = H.reshape(w, w, 4)[::-1, :, 0].copy()     # row 0 = image top
    H = H - H.mean()
    mat = material(info)
    # big field: eye view and tiling view
    S = max(10.0, 4 * T + 0.5)
    nres = 1500
    f = grid('field', -S / 2, 0.0, S, S, nres, nres, T, H, hr)
    f.data.materials.append(mat)
    # fine patch for the close-up
    p = grid('patch', 100.0, 0.0, 1.6, 1.6, 1100, 1100, T, H, hr)
    p.data.materials.append(mat)
    c1 = cam('eye', (0.0, 0.25, 1.7), 30, 35)
    c2 = cam('close', (100.8, 0.05, 0.62), 48, 40)
    hgt = 4 * T * 0.95
    c3 = cam('tile', (0.0, S / 2 - 4 * T * 0.5 - hgt * 0.62, hgt), 58, 30)
    for c, tag in ((c1, 'eye'), (c2, 'close'), (c3, 'tile')):
        sc.camera = c
        sc.render.filepath = os.path.join(OUT, '%s_%s.png' % (name, tag))
        bpy.ops.render.render(write_still=True)
    print('REVIEWED', name)
