"""Review renders of the scatter game meshes (re-imported FBX, LOD0, baked atlases) on the terrain sets.
blender -b -t 4 --python scatter_review.py -- OUTDIR"""
import bpy, sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN = os.path.dirname(HERE)
src = open(os.path.join(HERE, 'review.py')).read()
argv_keep = list(sys.argv)
OUTDIR = sys.argv[sys.argv.index('--') + 1]
sys.argv = sys.argv[:sys.argv.index('--') + 1] + [OUTDIR]
exec(src[:src.index('man = json.load')])      # reset(), grid(), material(), cam()
man = json.load(open(os.path.join(TERRAIN, 'manifest.json')))
recs = []
for f in ('BeachPebbles', 'Pebbles', 'Clam', 'Starfish'):
    p = os.path.join(TERRAIN, 'Scatter', 'scatter_%s.json' % f)
    if os.path.exists(p):
        recs += json.load(open(p))
REC = {r['name']: r for r in recs}
MATS = {}


def scatter_mat(rec):
    k = rec['material']
    if k in MATS:
        return MATS[k]
    m = bpy.data.materials.new(k); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    def t(key, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(TERRAIN, rec['textures'][key])); n.image.colorspace_settings.name = cs; return n
    bc = t('BC', 'sRGB'); nm = t('N', 'Non-Color'); orm = t('ORM', 'Non-Color')
    s = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs[0], s.inputs[0])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 0.6
    nt.links.new(bc.outputs[0], mx.inputs[6]); nt.links.new(s.outputs[0], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs['Base Color']); nt.links.new(s.outputs[1], b.inputs['Roughness'])
    n = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(nm.outputs[0], n.inputs['Color']); nt.links.new(n.outputs[0], b.inputs['Normal'])
    MATS[k] = m
    return m


def place(name, x, y, yaw, ground, lod=0, sink=0.002):
    rec = REC[name]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(TERRAIN, rec['fbx']))
    new = [o for o in bpy.data.objects if o not in before]
    keep = None
    for o in new:
        if o.name.startswith(name + '_LOD%d' % lod):
            keep = o
        else:
            bpy.data.objects.remove(o)
    keep.data.materials.clear(); keep.data.materials.append(scatter_mat(rec))
    # ground height under the footprint: mean of nearby ground vertices
    V = ground['V']
    d = (V[:, 0] - x) ** 2 + (V[:, 1] - y) ** 2
    r = max(keep.dimensions.x, keep.dimensions.y) * 0.35
    z = float(np.median(V[d < r * r, 2])) if (d < r * r).any() else 0.0
    keep.location = (x, y, z - sink); keep.rotation_euler = (0, 0, yaw)
    return keep


def scene(tag, setname, items, cams, size=1.6):
    sc = reset()
    MATS.clear()
    info = [s for s in man['sets'] if s['name'] == setname][0]
    T = info['tile_size_m']; hr = info['height_range_m']
    img = bpy.data.images.load(os.path.join(TERRAIN, info['files']['H']))
    w = img.size[0]
    H = np.empty(w * w * 4, np.float32); img.pixels.foreach_get(H)
    H = H.reshape(w, w, 4)[::-1, :, 0].copy(); H = H - H.mean()
    g = grid('ground', -size / 2, -size / 2, size, size, 1100, 1100, T, H, hr)
    g.data.materials.append(material(info))
    big = grid('far', -6, -6, 12, 12, 400, 400, T, H * 0, hr)
    big.location.z = -0.004; big.data.materials.append(g.data.materials[0])
    V = np.empty(len(g.data.vertices) * 3, np.float32); g.data.vertices.foreach_get('co', V)
    ground = {'V': V.reshape(-1, 3)}
    for it in items:
        place(it[0], it[1], it[2], it[3], ground, *(it[4:]))
    for i, (loc, pitch, lens, yaw) in enumerate(cams):
        c = cam('c%d' % i, loc, pitch, lens, yaw)
        c.data.dof.use_dof = False
        sc.camera = c
        sc.render.filepath = os.path.join(OUTDIR, 'scatter_%s_%d.png' % (tag, i))
        bpy.ops.render.render(write_still=True)
    print('SCENE', tag)


def cam_at(target, dist, pitch, lens=50):
    p = math.radians(pitch)
    return ((target[0], target[1] - dist * math.cos(p), target[2] + dist * math.sin(p)), pitch, lens, 0.0)


want = argv_keep[argv_keep.index('--') + 2:] or ['beach', 'pebbles']
if 'beach' in want:
    items = [('SM_BeachPebbles_A', -0.30, 0.22, 0.3), ('SM_BeachPebbles_B', 0.05, 0.30, 1.2), ('SM_BeachPebbles_C', 0.10, -0.02, 2.0), ('SM_BeachPebbles_D', -0.32, -0.05, 4.0),
             ('SM_ClamShell_Closed', 0.40, 0.18, 0.8), ('SM_ClamShell_Open', -0.12, -0.28, 2.4), ('SM_Starfish_A', 0.22, -0.30, 0.5), ('SM_Starfish_B', 0.46, -0.10, 1.9),
             ('SM_Starfish_A', -0.48, -0.30, 2.9, 1), ('SM_BeachPebbles_B', -0.50, 0.42, 0.2, 1)]
    cams = [cam_at((0.02, 0.0, 0.0), 1.15, 42)] + [cam_at((it[1], it[2], 0.0), 0.34 if 'Pebbles' in it[0] else 0.2, 38) for it in items[:8]]
    scene('beach', 'WetSand' if 'wet' in want else 'DrySand', items, cams)
if 'pebbles' in want:
    items = [('SM_Pebbles_A', -0.30, 0.18, 0.3), ('SM_Pebbles_B', 0.10, 0.25, 1.2), ('SM_Pebbles_C', 0.14, -0.14, 2.0), ('SM_Pebbles_D', -0.30, -0.14, 4.0)]
    cams = [cam_at((0.0, 0.02, 0.0), 1.0, 42)] + [cam_at((it[1], it[2], 0.0), 0.36, 36) for it in items]
    scene('pebbles', 'EarthPath', items, cams)
