"""Field boulders with a unique bake: a fractured high-detail stone carrying the rock scan by box (tri-planar) projection plus
lichen, moss, crevice dirt and a soil skirt, baked to the game mesh's own UVs (BC / N / ORM), so there are no projection seams.
blender -b -t 4 --python boulder_bake.py [A B C]"""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['DINK_PP'] = os.path.dirname(os.path.dirname(HERE))
exec(open(os.path.join(HERE, 'kitlib.py')).read())
OUT = os.path.join(os.environ['DINK_PP'], 'Structures', 'Stonebrook')
TEX = os.path.join(OUT, 'Textures'); os.makedirs(TEX, exist_ok=True)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SPECS = {'A': dict(size=(2.12, 1.69, 1.55), seed=4391, px=2048, tris=5600, extra=()),
         'B': dict(size=(1.35, 1.05, 1.0), seed=4392, px=1024, tris=4200, extra=((0.78, 0.28, (0.62, 0.5, 0.5)),)),
         'C': dict(size=(0.85, 0.7, 0.6), seed=4393, px=1024, tris=3600, extra=((-0.52, 0.25, (0.46, 0.4, 0.34)), (0.3, -0.46, (0.36, 0.3, 0.28))))}


def stone(size, seed, c=(0, 0, 0), sub=6):
    """fractured field stone: bedding planes on a tilted axis, a dozen split faces, cracks; returns (verts, faces)"""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    P = np.array([v.co[:] for v in bm.verts]); r = np.random.default_rng(seed)
    d = 1 + 0.2 * vnoise(P, seed, 1.2) + 0.09 * vnoise(P, seed + 1, 2.9)
    for _ in range(13):                                   # split faces
        n = r.normal(size=3); n[2] *= 0.6; n /= np.linalg.norm(n); lim = r.uniform(0.6, 0.92)
        k = P @ n; over = np.maximum(k * d - lim, 0); d = d - over / np.maximum(k, 1e-3) * 0.93
    ax = np.array([0.25, 0.12, 1.0]) + r.normal(0, 0.12, 3); ax /= np.linalg.norm(ax)
    t = (P * d[:, None]) @ ax * 5.5 + 0.6 * vnoise(P, seed + 3, 1.5)
    fr = t - np.floor(t)
    d = d * (1 - 0.035 * np.clip((fr - 0.72) / 0.1, 0, 1) * np.clip((1.0 - fr) / 0.05, 0, 1) - 0.022 * (np.floor(t) % 2))      # bedding ledges and open joints
    crack = np.abs(vnoise(P, seed + 5, 2.2)); d = d - 0.05 * np.clip(1 - crack / 0.05, 0, 1) ** 2
    d = d + 0.012 * vnoise(P, seed + 6, 9.0) + 0.006 * vnoise(P, seed + 7, 21.0)
    V = P * d[:, None] * (np.array(size) / 2)
    V[:, 2] += size[2] * 0.33; V[:, 2] = np.maximum(V[:, 2], 0.0)
    V += np.array(c, float)
    F = [[v.index for v in f.verts] for f in bm.faces]; bm.free()
    return V, F


def join(parts, name):
    V = []; F = []
    for (v, f) in parts:
        b = len(V); V += v.tolist(); F += [[b + i for i in q] for q in f]
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def source_material():
    root, info = set_info('FieldBoulder')
    m = bpy.data.materials.new('boulder_source'); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.5, 0.5, 0.5)
    L.new(tc.outputs['Object'], mp.inputs[0])

    def box(key, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(root, info['files'][key]), check_existing=True)
        t.image.colorspace_settings.name = cs; t.projection = 'BOX'; t.projection_blend = 0.35; L.new(mp.outputs[0], t.inputs[0]); return t
    bc = box('BC', 'sRGB'); orm = box('ORM', 'Non-Color'); hh = box('H', 'Non-Color')

    def N(scale, detail=4.0, off=0.0):
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
        mp2 = nt.nodes.new('ShaderNodeMapping'); mp2.inputs['Location'].default_value = (off, off * 1.7, off * 0.3); L.new(tc.outputs['Object'], mp2.inputs[0]); L.new(mp2.outputs[0], n.inputs['Vector']); return n.outputs['Fac']

    def M(op, a, b_=None, c=None, clamp=False):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for sock, v in zip(n.inputs, (a, b_, c)):
            if v is None:
                continue
            if hasattr(v, 'links'):
                L.new(v, sock)
            else:
                sock.default_value = v
        return n.outputs[0]

    def mix(a, b_, f, bt='MIX'):
        n = nt.nodes.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = bt
        for sock, v in ((n.inputs[0], f), (n.inputs[6], a), (n.inputs[7], b_)):
            if hasattr(v, 'links'):
                L.new(v, sock)
            else:
                sock.default_value = v if not isinstance(v, tuple) or len(v) == 4 else (*v, 1)
        return n.outputs[2]

    def ramp(x, lo, hi):
        n = nt.nodes.new('ShaderNodeMapRange'); n.inputs[1].default_value = lo; n.inputs[2].default_value = hi; L.new(x, n.inputs[0]); n.clamp = True; return n.outputs[0]
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sn = nt.nodes.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sn.inputs[0])
    sp = nt.nodes.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sp.inputs[0])
    up, north, zz = sn.outputs[2], sn.outputs[1], sp.outputs[2]
    so = nt.nodes.new('ShaderNodeSeparateColor'); L.new(orm.outputs[0], so.inputs[0])
    so_ = so.outputs
    c = mix(bc.outputs[0], so_[0], 0.6, 'MULTIPLY')
    c = mix(c, M('MULTIPLY_ADD', N(0.9, 2.0, 3.0), 0.5, 0.75), 1.0, 'MULTIPLY')                         # broad value drift
    # dirt in the cracks and concave joints
    crev = ramp(geo.outputs['Pointiness'], 0.5, 0.44)
    c = mix(c, (0.07, 0.055, 0.04), M('MULTIPLY', crev, 0.85))
    # crustose lichens: pale grey-green rosettes and a few orange ones, on faces the rain reaches
    wet = ramp(up, -0.25, 0.35)
    v1 = nt.nodes.new('ShaderNodeTexVoronoi'); v1.inputs['Scale'].default_value = 9.0; L.new(tc.outputs['Object'], v1.inputs['Vector'])
    ros = M('MULTIPLY', ramp(v1.outputs['Distance'], 0.34, 0.16), ramp(N(2.3, 3.0, 7.0), 0.5, 0.62))
    lg = M('MULTIPLY', M('MULTIPLY', ros, wet), ramp(N(40.0, 2.0, 1.0), 0.3, 0.55))
    c = mix(c, (0.34, 0.37, 0.29), M('MULTIPLY', lg, 0.85))
    v2 = nt.nodes.new('ShaderNodeTexVoronoi'); v2.inputs['Scale'].default_value = 15.0; L.new(mp.outputs[0], v2.inputs['Vector'])
    lo_ = M('MULTIPLY', M('MULTIPLY', ramp(v2.outputs['Distance'], 0.27, 0.12), ramp(N(1.7, 3.0, 19.0), 0.6, 0.7)), ramp(up, 0.1, 0.6))
    c = mix(c, (0.50, 0.26, 0.045), M('MULTIPLY', lo_, 0.9))
    # moss: on the lee (north) side and in hollows on top, thick enough to hide the stone
    lee = M('ADD', M('MULTIPLY', ramp(north, 0.05, 0.6), ramp(up, -0.5, 0.2)), M('MULTIPLY', ramp(up, 0.55, 0.9), 0.75), clamp=True)
    mo = ramp(M('ADD', M('MULTIPLY', lee, 0.9), M('MULTIPLY_ADD', N(3.1, 5.0, 11.0), 0.9, -0.62)), 0.28, 0.42)
    mcol = mix((0.035, 0.06, 0.012), (0.085, 0.11, 0.025), N(26.0, 2.0, 5.0))
    c = mix(c, mcol, mo)
    # soil skirt and the stain line where the grass stands
    sk = ramp(M('ADD', zz, M('MULTIPLY_ADD', N(5.0, 3.0, 2.0), 0.12, -0.06)), 0.16, 0.03)
    c = mix(c, (0.085, 0.062, 0.04), M('MULTIPLY', sk, 0.92))
    gl = M('MULTIPLY', ramp(M('ADD', zz, M('MULTIPLY_ADD', N(7.0, 3.0, 9.0), 0.1, -0.05)), 0.3, 0.17), M('SUBTRACT', 1.0, sk))
    c = mix(c, (0.06, 0.085, 0.03), M('MULTIPLY', gl, 0.5))
    L.new(c, b.inputs['Base Color'])
    rgh = M('ADD', so_[1], M('MULTIPLY', mo, 0.1), clamp=True); rgh = M('ADD', rgh, M('MULTIPLY', lg, 0.05), clamp=True)
    L.new(rgh, b.inputs['Roughness'])
    hsum = M('ADD', hh.outputs[0], M('ADD', M('MULTIPLY', mo, M('MULTIPLY_ADD', N(60.0, 2.0, 0.0), 0.6, 0.5)), M('MULTIPLY', lg, 0.12)))
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = 0.035; L.new(hsum, bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m


def bake_one(key, sp):
    name = 'SM_Boulder_Field_%s_PR' % key
    parts = [stone(sp['size'], sp['seed'])] + [stone(s_, sp['seed'] + 7 + int(dx * 10), (dx, dy, 0)) for (dx, dy, s_) in sp['extra']]
    hi = join(parts, name + '_high')
    V = np.array([v.co[:] for v in hi.data.vertices]); cxy = (V[:, :2].min(0) + V[:, :2].max(0)) / 2
    for v in hi.data.vertices:
        v.co.x -= cxy[0]; v.co.y -= cxy[1]
    hi.data.materials.append(SRC)
    coll = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(coll)
    coll['dink_class'] = 'prop'; coll['dink_path'] = 'Structures/Stonebrook'; coll['dink_tex_px'] = sp['px']
    coll['dink_source'] = 'authored in Blender (boulder_bake.py); bake of Poly Haven rock_face / rock_face_04 (CC0) by box projection plus procedural lichen, moss and soil'
    lods = []
    ntri = len(hi.data.polygons)
    for li, tr in enumerate((sp['tris'], int(sp['tris'] * 0.45), int(sp['tris'] * 0.2))):
        lo = bpy.data.objects.new('%s_LOD%d' % (name, li), (hi.data if li == 0 else lods[0].data).copy()); coll.objects.link(lo)
        md = lo.modifiers.new('d', 'DECIMATE'); md.ratio = tr / (ntri if li == 0 else len(lods[0].data.polygons)); md.use_collapse_triangulate = True
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(lo.evaluated_get(dg)); lo.modifiers.clear(); old = lo.data; lo.data = me; bpy.data.meshes.remove(old); me.name = lo.name
        if li == 0:
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            lo.select_set(True); bpy.context.view_layer.objects.active = lo
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.012); bpy.ops.object.mode_set(mode='OBJECT')
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.materials.clear()
        lods.append(lo)
    lo = lods[0]
    # bake high -> LOD0
    gm = bpy.data.materials.new('MI_Boulder_Field_%s_PR' % key); gm.use_nodes = True
    nt = gm.node_tree; b = nt.nodes['Principled BSDF']
    px = sp['px']; imgs = {}
    for k_, cs in (('BC', 'sRGB'), ('N', 'Non-Color'), ('R', 'Non-Color'), ('AO', 'Non-Color')):
        im = bpy.data.images.new('%s_%s' % (name, k_), px, px, alpha=False, float_buffer=(k_ != 'BC')); im.colorspace_settings.name = cs; imgs[k_] = im
    tn = nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active = tn
    for o in lods:
        o.data.materials.append(gm)
    sc = bpy.context.scene
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    hi.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    for k_, typ, kw, spp in (('BC', 'DIFFUSE', dict(pass_filter={'COLOR'}), 6), ('N', 'NORMAL', dict(normal_space='TANGENT'), 6), ('R', 'ROUGHNESS', {}, 4)):
        tn.image = imgs[k_]; sc.cycles.samples = spp
        bpy.ops.object.bake(type=typ, use_selected_to_active=True, cage_extrusion=0.05, max_ray_distance=0.12, margin=10, **kw)
        print('BAKED', name, k_)
    # Ambient occlusion is baked on LOD0 alone, with every other mesh of the scene hidden: the high stone and the other LODs are shells in the
    # same place, and the boulders baked earlier in this run stand at the origin too (B and C lie inside A). Wherever another surface lay
    # outside LOD0 it shadowed it completely, so 41 % of boulder A and 85 % of B and C came out with occlusion 0 and were black wherever the
    # sun did not reach (found in the game, 13 Nov 2026). The fine crevices are in the base colour and the normal map; this pass only needs
    # the large forms.
    others = [(o, o.hide_render) for o in sc.objects if o is not lo and o.type == 'MESH']
    for o, _ in others:
        o.hide_render = True; o.select_set(False)
    tn.image = imgs['AO']; sc.cycles.samples = 64
    bpy.ops.object.bake(type='AO', use_selected_to_active=False, margin=10)
    for o, was in others:
        o.hide_render = was
    print('BAKED', name, 'AO')
    ao_ = np.empty(px * px * 4, np.float32); imgs['AO'].pixels.foreach_get(ao_); ao_ = ao_.reshape(px, px, 4)[..., 0]; lit_ = ao_[ao_ > 0]
    print('AO CHECK', name, 'percentiles 5/50/95 of the baked texels:', [round(float(x), 2) for x in np.percentile(lit_, [5, 50, 95])] if len(lit_) else None)
    def arr(im):
        a = np.empty(px * px * 4, np.float32); im.pixels.foreach_get(a); return a.reshape(px, px, 4)
    from_lin = lambda a: a
    A = {k_: arr(v) for k_, v in imgs.items()}
    orm = np.zeros((px, px, 4), np.float32); orm[..., 0] = np.clip(A['AO'][..., 0] * 1.15, 0, 1); orm[..., 1] = A['R'][..., 0]; orm[..., 3] = 1
    files = {}
    for k_, data, cs in (('BC', None, 'sRGB'), ('N', A['N'], 'Non-Color'), ('ORM', orm, 'Non-Color')):
        fn = 'T_Boulder_Field_%s_PR_%s.png' % (key, k_); path = os.path.join(TEX, fn)
        if data is None:
            im = imgs['BC']
        else:
            im = bpy.data.images.new(fn, px, px, alpha=False); im.colorspace_settings.name = cs; im.pixels.foreach_set(np.clip(data, 0, 1).ravel())
        im.filepath_raw = path; im.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; im.save()
        files[k_] = fn
    # game material preview
    L = nt.links
    def T(fn, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, fn), check_existing=False); t.image.colorspace_settings.name = cs; return t
    tb = T(files['BC'], 'sRGB'); tnn = T(files['N'], 'Non-Color'); to = T(files['ORM'], 'Non-Color')
    L.new(tb.outputs[0], b.inputs['Base Color'])
    so = nt.nodes.new('ShaderNodeSeparateColor'); L.new(to.outputs[0], so.inputs[0]); L.new(so.outputs[1], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); L.new(tnn.outputs[0], nm.inputs['Color']); L.new(nm.outputs[0], b.inputs['Normal'])
    nt.nodes.remove(tn)
    # collision hull from the lowest LOD
    Vh = np.array([v.co[:] for v in lods[2].data.vertices])
    pick = set(range(0, len(Vh), max(1, len(Vh) // 22))) | {int(Vh[:, k].argmin()) for k in range(3)} | {int(Vh[:, k].argmax()) for k in range(3)}
    bmc = bmesh.new()
    for i in sorted(pick):
        bmc.verts.new(tuple(Vh[i]))
    r_ = bmesh.ops.convex_hull(bmc, input=bmc.verts[:])
    bmesh.ops.delete(bmc, geom=list({g for g in r_.get('geom_interior', []) + r_.get('geom_unused', []) if isinstance(g, bmesh.types.BMVert)}), context='VERTS')
    bmesh.ops.recalc_face_normals(bmc, faces=bmc.faces[:])
    mc = bpy.data.meshes.new('UCX_%s_LOD0_01' % name); bmc.to_mesh(mc); bmc.free()
    oc = bpy.data.objects.new(mc.name, mc); coll.objects.link(oc); oc.hide_render = True
    bpy.data.objects.remove(hi)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in lods + [oc]:
        o.hide_render = False; o.select_set(True)
    bpy.context.view_layer.objects.active = lo
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + '.fbx'), use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='Y', axis_up='Z', bake_space_transform=False, use_triangles=True, mesh_smooth_type='EDGE', use_tspace=False, add_leaf_bones=False,
                             bake_anim=False, path_mode='STRIP', object_types={'MESH', 'EMPTY'})
    for o in lods[1:] + [oc]:
        o.hide_render = True
    Vl = np.array([v.co[:] for v in lo.data.vertices]); tr = []
    for o in lods:
        o.data.calc_loop_triangles(); tr.append(len(o.data.loop_triangles))
    return {'name': name, 'class': 'prop', 'fbx': name + '.fbx', 'materials': [gm.name], 'source_blend': 'Boulders.blend', 'lod0_triangles': tr[0], 'lod1_triangles': tr[1], 'lod2_triangles': tr[2],
            'dimensions_m': [round(float(x), 3) for x in (Vl.max(0) - Vl.min(0))], 'bounds_min_m': [round(float(x), 3) for x in Vl.min(0)], 'bounds_max_m': [round(float(x), 3) for x in Vl.max(0)],
            'open_edges': 0, 'collision_hulls': 1, 'textures': {k_: 'Textures/' + v for k_, v in files.items()}, 'texture_px': px}


sc = new_scene(); sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
SRC = source_material()
recs = [bake_one(k, SPECS[k]) for k in (argv or ['A', 'B', 'C'])]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Boulders.blend'), compress=True)
json.dump(recs, open(os.path.join(OUT, 'modules_boulders.json'), 'w'), indent=1)
print('BOULDERS DONE', [(r['name'], r['lod0_triangles'], r['dimensions_m']) for r in recs])
