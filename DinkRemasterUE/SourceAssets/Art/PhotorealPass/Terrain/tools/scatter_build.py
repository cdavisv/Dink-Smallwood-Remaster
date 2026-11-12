"""Build the beach / pebble ground scatter: high-detail sources, game meshes (LOD0, LOD1), 1024 family atlases, FBX.
blender -b -t 4 --python scatter_build.py -- [family ...]     families: BeachPebbles Pebbles Clam Starfish"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN = os.path.dirname(HERE)
OUT = os.path.join(TERRAIN, 'Scatter')
TP = os.path.join(os.path.dirname(TERRAIN), 'ThirdParty')
os.makedirs(os.path.join(OUT, 'Textures'), exist_ok=True)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAMS = argv or ['BeachPebbles', 'Pebbles', 'Clam', 'Starfish']
ATLAS = 1024
SAND = (0.78, 0.69, 0.53, 1)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 24
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
    return sc


def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def mesh_obj(name, V, F, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], [tuple(int(i) for i in f) for f in F])
    me.update()
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    return link(bpy.data.objects.new(name, me))


def big_mesh(name, V, Q, uv=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', np.asarray(V, np.float32).ravel())
    Q = np.asarray(Q, np.int32)
    me.loops.add(Q.size); me.loops.foreach_set('vertex_index', Q.ravel())
    me.polygons.add(len(Q)); me.polygons.foreach_set('loop_start', (np.arange(len(Q)) * Q.shape[1]).astype(np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(len(Q), bool))
    me.update(calc_edges=True)
    if uv is not None:
        l = me.uv_layers.new(name='UVMap')
        l.data.foreach_set('uv', np.asarray(uv, np.float32)[Q.ravel()].ravel())
    me.validate()
    return link(bpy.data.objects.new(name, me))


def only(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    only(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def decimate_to(ob, target):
    n = tris(ob)
    if n > target:
        m = ob.modifiers.new('d', 'DECIMATE'); m.ratio = target / n
        apply_mods(ob)
    only(ob)
    bpy.ops.object.shade_smooth()


def weld(ob, dist=1e-5):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free()


def cut_ground(ob):
    """remove what is below z=0 and cap it, so the mesh is closed and sits on its base"""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, -1), clear_outer=True)
    edges = [e for e in r['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    for _ in range(3):
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=2e-5)
        dead = [f for f in bm.faces if f.calc_area() < 2e-8]
        if not dead:
            break
        bmesh.ops.delete(bm, geom=dead, context='FACES')
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uvl = bm.loops.layers.uv.active
    if uvl is not None:            # the ground cap is never seen: park its UVs on one texel so it cannot overlap the shell's islands
        for f in bm.faces:
            if f.normal.z < -0.9 and abs(f.calc_center_median().z) < 1e-4:
                for l in f.loops:
                    l[uvl].uv = (0.0015, 0.0015)
    bm.to_mesh(ob.data); bm.free()


def tex(name, kind, **kw):
    t = bpy.data.textures.new(name, kind)
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def displace(ob, t, strength, mid=0.5):
    m = ob.modifiers.new('disp', 'DISPLACE'); m.texture = t; m.strength = strength; m.mid_level = mid
    m.texture_coords = 'GLOBAL'
    return m


# ---------------------------------------------------------------- materials
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes['Principled BSDF']


def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def ramp(nt, stops, interp='LINEAR', mask=False):
    r = N(nt, 'ShaderNodeValToRGB')
    r.color_ramp.interpolation = interp
    el = r.color_ramp.elements
    while len(el) < len(stops):
        el.new(0.5)
    for e, (p, c) in zip(el, stops):
        e.position = p; e.color = lin(c) if not mask else (*c[:3], 1)
    return r


def lin(c):
    """constants in this file are written as sRGB (0-1); shader sockets want linear"""
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c[:3]) + (1.0,)


def mixc(nt, a, b, fac, blend='MIX'):
    m = N(nt, 'ShaderNodeMix', data_type='RGBA', blend_type=blend)
    L = nt.links
    for sock, v in ((m.inputs[0], fac), (m.inputs[6], a), (m.inputs[7], b)):
        if hasattr(v, 'is_linked') or hasattr(v, 'links'):
            L.new(v, sock)
        elif isinstance(v, (tuple, list)):
            sock.default_value = lin(v) if blend == 'MIX' else tuple(v)
        else:
            sock.default_value = v
    return m.outputs[2]


def mth(nt, op, a, b=None, clamp=False):
    m = N(nt, 'ShaderNodeMath', operation=op); m.use_clamp = clamp
    for sock, v in ((m.inputs[0], a), (m.inputs[1], b)):
        if v is None:
            continue
        if hasattr(v, 'links'):
            nt.links.new(v, sock)
        else:
            sock.default_value = v
    return m.outputs[0]


def ground_terms(nt, wet_h, sand_h):
    """world-height masks: wet band near the ground, sand caught low down and in crevices"""
    geo = N(nt, 'ShaderNodeNewGeometry')
    sep = N(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sep.inputs[0])
    z = sep.outputs[2]
    sepn = N(nt, 'ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Normal'], sepn.inputs[0])
    noise = N(nt, 'ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 90; noise.inputs['Detail'].default_value = 3
    zz = mth(nt, 'ADD', z, mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', noise.outputs[0], 0.5), wet_h * 0.9))
    wet = mth(nt, 'SUBTRACT', 1.0, mth(nt, 'DIVIDE', zz, wet_h), clamp=True)
    ao = N(nt, 'ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.012; ao.samples = 8
    crev = mth(nt, 'SUBTRACT', 1.0, ao.outputs['AO'], clamp=True)            # 0 open .. 1 buried
    grain = N(nt, 'ShaderNodeTexNoise'); grain.inputs['Scale'].default_value = 1400; grain.inputs['Detail'].default_value = 1
    low = mth(nt, 'SUBTRACT', 1.0, mth(nt, 'DIVIDE', zz, sand_h), clamp=True)
    up = mth(nt, 'MAXIMUM', sepn.outputs[2], 0.0)
    s = mth(nt, 'MULTIPLY', mth(nt, 'ADD', mth(nt, 'MULTIPLY', crev, 1.6), low), mth(nt, 'ADD', 0.35, mth(nt, 'MULTIPLY', up, 0.65)))
    s = mth(nt, 'MULTIPLY', s, mth(nt, 'ADD', 0.45, grain.outputs[0]))
    sm = N(nt, 'ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nt.links.new(s, sm.inputs[0]); sm.inputs[1].default_value = 0.42; sm.inputs[2].default_value = 0.75
    return wet, sm.outputs[0], grain.outputs[0]


def finish_surface(nt, b, col, rough, bump_h, bump_dist, wet_h, sand_h, sand_gain=1.0):
    wet, sand, grain = ground_terms(nt, wet_h, sand_h)
    if sand_gain != 1.0:
        sand = mth(nt, 'MULTIPLY', sand, sand_gain)
    L = nt.links
    col = mixc(nt, col, (0, 0, 0, 1), mth(nt, 'MULTIPLY', wet, 0.42))                # wet darkening
    sandc = mixc(nt, (SAND[0] * 0.85, SAND[1] * 0.85, SAND[2] * 0.85, 1), (min(SAND[0] * 1.12, 1), min(SAND[1] * 1.12, 1), min(SAND[2] * 1.12, 1), 1), grain)
    col = mixc(nt, col, sandc, sand)
    L.new(col, b.inputs['Base Color'])
    r = mth(nt, 'SUBTRACT', rough, mth(nt, 'MULTIPLY', wet, 0.3))
    r = mixc(nt, r, 0.92, sand) if False else mth(nt, 'ADD', mth(nt, 'MULTIPLY', r, mth(nt, 'SUBTRACT', 1.0, sand)), mth(nt, 'MULTIPLY', sand, 0.92))
    L.new(r, b.inputs['Roughness'])
    bh = mth(nt, 'ADD', bump_h, mth(nt, 'MULTIPLY', mth(nt, 'MULTIPLY', sand, grain), 1.5))
    bm = N(nt, 'ShaderNodeBump'); bm.inputs['Distance'].default_value = bump_dist; bm.inputs['Strength'].default_value = 1.0
    L.new(bh, bm.inputs['Height']); L.new(bm.outputs[0], b.inputs['Normal'])


LITH = [  # name, scan, repeats per metre (range), tint, tint amount, value gain, saturation, roughness, bump, banding stretch
    ('banded', 'cliff_side', (5.0, 9.0), (0.55, 0.52, 0.48), 0.70, 1.0, 0.35, 0.62, 0.5, 4.0),
    ('banded_red', 'cliff_side', (4.0, 7.0), (0.52, 0.36, 0.30), 0.45, 0.9, 0.7, 0.66, 0.5, 3.0),
    ('quartz_veined', 'stone_tiles_02', (2.2, 3.5), (0.34, 0.36, 0.38), 0.35, 0.75, 0.6, 0.48, 0.3, 1.0),
    ('basalt', 'rock_face_04', (3.0, 5.0), (0.13, 0.13, 0.14), 0.75, 0.6, 0.3, 0.42, 0.8, 1.0),
    ('pink_granite', 'dry_riverbed_rock', (6.0, 9.0), (0.72, 0.50, 0.44), 0.42, 1.25, 0.9, 0.74, 0.6, 1.0),
    ('grey_granite', 'dry_riverbed_rock', (6.0, 9.0), (0.62, 0.62, 0.60), 0.45, 1.3, 0.25, 0.72, 0.6, 1.0),
    ('pale_limestone', 'rock_face', (3.0, 5.0), (0.80, 0.77, 0.68), 0.72, 1.3, 0.5, 0.80, 0.4, 1.0),
    ('lichen_slate', 'mossy_rock', (3.0, 5.0), (0.40, 0.42, 0.40), 0.55, 0.9, 0.4, 0.58, 0.5, 2.0),
]
LITH_ORDER = [0, 4, 3, 2, 6, 1, 5, 7]


def mat_beach_pebble(i, rng):
    name, scan, reps, tint, tamt, gain, sat, rough0, bumpk, stretch = LITH[LITH_ORDER[i % len(LITH)]]
    m, nt, b = new_mat('HP_BeachPebble_%d_%s' % (i, name))
    sc = float(rng.uniform(*reps))
    t, mp = scan_tex(nt, scan, '_diff', 'sRGB', sc)
    loc = tuple(rng.uniform(0, 1, 3)); rot = tuple(rng.uniform(0, 3, 3))
    mp.inputs['Location'].default_value = loc; mp.inputs['Rotation'].default_value = rot
    mp.inputs['Scale'].default_value = (sc, sc, sc * stretch)
    d, mp2 = scan_tex(nt, scan, '_disp', 'Non-Color', sc)
    mp2.inputs['Location'].default_value = loc; mp2.inputs['Rotation'].default_value = rot; mp2.inputs['Scale'].default_value = (sc, sc, sc * stretch)
    hsv = N(nt, 'ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = sat; hsv.inputs['Value'].default_value = gain
    nt.links.new(t.outputs[0], hsv.inputs['Color'])
    col = mixc(nt, hsv.outputs[0], (*tint, 1), tamt)
    n2 = N(nt, 'ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 900; n2.inputs['Detail'].default_value = 2
    col = mixc(nt, col, (0.5, 0.5, 0.5, 1), mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', n2.outputs[0], 0.5), 0.35), 'OVERLAY')
    # sea-worn: smooth where proud, pitted and matte in the hollows of the scan
    rough = mth(nt, 'ADD', rough0, mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', 0.5, d.outputs[0]), 0.3))
    bump = mth(nt, 'ADD', mth(nt, 'MULTIPLY', d.outputs[0], bumpk), mth(nt, 'MULTIPLY', n2.outputs[0], 0.2))
    finish_surface(nt, b, col, rough, bump, 0.0005, 0.012, 0.006)
    return m


def scan_tex(nt, aid, key, cs, scale):
    import glob
    f = [x for x in glob.glob(os.path.join(TP, '*', aid, '*')) if key in os.path.basename(x)][0]
    t = N(nt, 'ShaderNodeTexImage'); t.image = bpy.data.images.load(f, check_existing=True); t.image.colorspace_settings.name = cs
    t.projection = 'BOX'; t.projection_blend = 0.35
    tc = N(nt, 'ShaderNodeTexCoord'); mp = N(nt, 'ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs[0]); nt.links.new(mp.outputs[0], t.inputs[0])
    return t, mp


def mat_dark_pebble(i, rng):
    m, nt, b = new_mat('HP_Pebble_%d' % i)
    sc = float(rng.uniform(2.5, 4.0))             # scan repeats per metre: rock detail shrunk to pebble size
    t, mp = scan_tex(nt, 'rock_face_04', '_diff', 'sRGB', sc)
    mp.inputs['Location'].default_value = tuple(rng.uniform(0, 1, 3)); mp.inputs['Rotation'].default_value = tuple(rng.uniform(0, 3, 3))
    d, mp2 = scan_tex(nt, 'rock_face_04', '_disp', 'Non-Color', sc)
    mp2.inputs['Location'].default_value = mp.inputs['Location'].default_value; mp2.inputs['Rotation'].default_value = mp.inputs['Rotation'].default_value
    tint = [(0.50, 0.47, 0.42), (0.40, 0.39, 0.37), (0.55, 0.48, 0.40), (0.36, 0.37, 0.36), (0.48, 0.44, 0.36)][rng.integers(5)]
    hsv = N(nt, 'ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = 0.6; hsv.inputs['Value'].default_value = 1.5
    nt.links.new(t.outputs[0], hsv.inputs['Color'])
    col = mixc(nt, hsv.outputs[0], (*tint, 1), 0.45)
    n2 = N(nt, 'ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 700; n2.inputs['Detail'].default_value = 2
    col = mixc(nt, col, (0.1, 0.1, 0.1, 1), mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', n2.outputs[0], 0.5), 0.5), 'OVERLAY')
    rough = mth(nt, 'ADD', 0.72, mth(nt, 'MULTIPLY', d.outputs[0], 0.2))
    bump = mth(nt, 'ADD', mth(nt, 'MULTIPLY', d.outputs[0], 2.5), mth(nt, 'MULTIPLY', n2.outputs[0], 0.3))
    global SAND
    keep = SAND; SAND = (0.50, 0.42, 0.33, 1)      # dry soil rather than beach sand
    finish_surface(nt, b, col, rough, bump, 0.0008, 0.008, 0.005)
    SAND = keep
    return m


# ---------------------------------------------------------------- pebbles
def icosphere(sub):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    V = np.array([v.co[:] for v in bm.verts]); F = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return V, F


def stone(name, rng, size, angular, hi=True):
    """returns (high, low_source) objects at the origin, longest axis about `size` metres"""
    V, F = icosphere(6 if hi else 3)
    ax = np.array([1.0, rng.uniform(0.6, 0.9), rng.uniform(0.38, 0.62) if not angular else rng.uniform(0.40, 0.66)])
    # low-frequency lumps (same function for every resolution)
    P = V.copy()
    for k in range(5):
        d = rng.normal(size=3); d /= np.linalg.norm(d)
        f = rng.uniform(0.8, 2.2); ph = rng.uniform(0, 6.28)
        P = P * (1 + (0.10 if not angular else 0.14) / (k * 0.5 + 1) * np.sin(f * (V @ d) * 3.0 + ph))[:, None]
    if angular:
        for k in range(int(rng.integers(9, 15))):
            n = rng.normal(size=3); n /= np.linalg.norm(n)
            dd = rng.uniform(0.66, 0.92)
            over = np.maximum(P @ n - dd, 0)
            P = P - over[:, None] * n[None, :]
    P = P * ax * size * 0.5
    ob = mesh_obj(name, P, F)
    if angular:
        s = ob.modifiers.new('s', 'SMOOTH'); s.factor = 0.5; s.iterations = 25 if hi else 3
        apply_mods(ob)
    return ob


STONE_SEQ = 0


def stone_pair(rng, size, angular):
    global STONE_SEQ
    STONE_SEQ += 1
    st = rng.bit_generator.state
    hi = stone('hi_%d' % STONE_SEQ, rng, size, angular, True)
    rng.bit_generator.state = st
    lo = stone('lo_%d' % STONE_SEQ, rng, size, angular, False)
    # fine relief on the high source only
    t1 = tex('c%d' % STONE_SEQ, 'CLOUDS', noise_scale=size * 0.22, noise_depth=3)
    displace(hi, t1, size * (0.035 if angular else 0.012))
    if angular:
        t2 = tex('v%d' % STONE_SEQ, 'VORONOI', noise_scale=size * 0.12)
        displace(hi, t2, -size * 0.02, 0.2)
    else:
        t2 = tex('v%d' % STONE_SEQ, 'VORONOI', noise_scale=size * 0.03)
        displace(hi, t2, -size * 0.004, 0.1)          # pitting
    apply_mods(hi)
    only(hi); bpy.ops.object.shade_smooth()
    return hi, lo


CLUSTERS = {
    # name: list of (x, y, size) in metres
    'A': [(0.0, 0.0, 0.085), (0.07, 0.03, 0.05), (-0.03, 0.06, 0.035), (0.03, -0.055, 0.028)],
    'B': [(-0.12, 0.02, 0.06), (-0.04, -0.03, 0.045), (0.05, 0.05, 0.07), (0.13, -0.02, 0.04), (0.02, -0.09, 0.03), (-0.09, 0.10, 0.025), (0.10, 0.11, 0.022)],
    'C': [(-0.21, -0.05, 0.05), (-0.11, 0.08, 0.035), (-0.02, -0.02, 0.06), (0.06, 0.10, 0.03), (0.12, -0.07, 0.045), (0.21, 0.04, 0.038),
          (0.0, -0.13, 0.025), (-0.16, 0.14, 0.022), (0.17, 0.15, 0.02), (0.08, 0.0, 0.018)],
    'D': [(0.0, 0.0, 0.14), (0.10, 0.05, 0.04), (-0.085, 0.06, 0.03)],
}


def build_pebbles(fam, angular, seed):
    rng = np.random.default_rng(seed)
    assets = []
    for ci, (cn, items) in enumerate(CLUSTERS.items()):
        his, los = [], []
        budget = 1450
        wsum = sum(s for _, _, s in items)
        for (x, y, s) in items:
            if angular:
                s *= rng.uniform(0.9, 1.25)
            hi, lo = stone_pair(rng, s, angular)
            rot = Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(rng.normal(0, 0.18), 4, 'X') @ Matrix.Rotation(rng.normal(0, 0.18), 4, 'Y')
            zext = max((rot @ Vector(v.co)).z for v in lo.data.vertices)
            sink = rng.uniform(0.18, 0.38) if not angular else rng.uniform(0.1, 0.3)
            M = Matrix.Translation((x * (1.15 if angular else 1.0), y * (1.15 if angular else 1.0), zext * (1 - 2 * sink))) @ rot
            for o in (hi, lo):
                o.data.transform(M); o.data.update()
            hi.data.materials.append(mat_dark_pebble(STONE_SEQ, rng) if angular else mat_beach_pebble(STONE_SEQ + ci, rng))
            decimate_to(lo, max(48, int(budget * s / wsum)))
            cut_ground(lo)
            his.append(hi); los.append(lo)
        only(los[0])
        for o in los:
            o.select_set(True)
        bpy.ops.object.join()
        lo = los[0]; lo.name = 'SM_%s_%s_LOD0' % (fam, cn); lo.data.name = lo.name
        assets.append({'name': 'SM_%s_%s' % (fam, cn), 'lo': lo, 'his': his})
    return assets


# ---------------------------------------------------------------- clam
def valve(nr, nf, L, rng_seed, detail=True, thick=0.0, flip=False):
    """one valve, umbo at origin, fanning toward -Y, dome toward +Z. returns V, Q, attrs(t, phi)"""
    r = np.random.default_rng(rng_seed)
    t = np.linspace(0, 1, nr + 1)[:, None] ** 0.85
    f = np.linspace(-1, 1, nf + 1)[None, :]
    al = f * math.radians(104)
    Rv = L * (np.cos(al * 0.60) ** 1.25) * (1 + 0.035 * np.sin(al * 2.0 + 0.6))       # slightly inequilateral
    nrib = 23
    ribphase = al * nrib / math.radians(208) * 2 * math.pi
    x = Rv * t * np.sin(al)
    y = -Rv * t * np.cos(al) * 0.94
    prof = np.sin(np.pi * np.clip(t, 0, 1) ** 0.70) ** 0.95
    side = 0.06 + 0.94 * (1 - np.abs(f) ** 2.6) ** 0.6
    z = 0.27 * L * prof * side
    z = z + 0.05 * L * np.exp(-((t - 0.08) / 0.08) ** 2) * side * np.clip(t / 0.03, 0, 1)                         # umbo beak
    if detail:
        rib = np.cos(ribphase)
        ribsh = np.sign(rib) * np.abs(rib) ** 0.7
        z = z + 0.012 * L * ribsh * (t ** 0.8) * side ** 0.5 * (1 - 0.75 * t ** 6)
        g = np.sin(2 * np.pi * 26 * t ** 1.35 + 0.8 * np.sin(al * 3))
        z = z + 0.0028 * L * g * (0.4 + t)
        for tc in (0.46, 0.71, 0.88):                                                   # growth checks
            z = z - 0.006 * L * np.exp(-((t - tc - 0.01 * np.sin(al * 2)) / 0.012) ** 2)
    if thick:
        zi = 0.27 * L * prof * side + 0.05 * L * np.exp(-((t - 0.08) / 0.08) ** 2) * side * np.clip(t / 0.03, 0, 1)
        z = zi - thick * (0.75 + 0.25 * np.sin(np.pi * np.clip(t, 0, 1) ** 0.8)) * np.clip(t * 12, 0, 1)
    X = np.broadcast_to(x, (nr + 1, nf + 1)); Y = np.broadcast_to(y, X.shape); Z = np.broadcast_to(z, X.shape)
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    idx = np.arange((nr + 1) * (nf + 1)).reshape(nr + 1, nf + 1)
    Q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    if flip:
        Q = Q[:, ::-1]
    T = np.broadcast_to(t, X.shape).ravel(); F = np.broadcast_to(f, X.shape).ravel()
    return V, Q, T, F


def shell(name, L, nr, nf, detail, seed, solid=False):
    """a full valve with thickness: outer sheet wrapped round the margin into the inner sheet (one grid).
    vertex colour attribute 'st' = (t, phi*0.5+0.5, inner, ribcrest)"""
    Vo, _, T, F = valve(nr, nf, L, seed, detail)
    Vi, _, _, _ = valve(nr, nf, L, seed, False, thick=0.0018)
    if solid:                    # closed shell: the inner sheet is a flat membrane on the commissure plane, never seen
        Vi = Vi * np.array([0.985, 0.985, 0.0])
    R_, C_ = nr + 1, nf + 1
    Vo = Vo.reshape(R_, C_, 3); Vi = Vi.reshape(R_, C_, 3)[::-1]
    V = np.concatenate([Vo, Vi]).reshape(-1, 3)
    Tg = T.reshape(R_, C_); Fg = F.reshape(R_, C_)
    idx = np.arange(2 * R_ * C_).reshape(2 * R_, C_)
    Q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    # UVs from the flat valve outline, quarter-turned: outer sheet in the upper half, inner sheet in the lower half of a 1 x 2 cell
    flat = Vo.reshape(-1, 3)
    uu = (-flat[:, 1] / (L * 1.02)).reshape(R_, C_)                     # 0..1 from umbo to margin
    vv = (flat[:, 0] / (L * 2.05) + 0.5).reshape(R_, C_)
    uo = np.stack([0.03 + 0.94 * uu, 0.515 + 0.47 * vv], -1)
    ui = np.stack([0.03 + 0.94 * uu, 0.015 + 0.47 * vv], -1)[::-1]
    UV = np.concatenate([uo, ui]).reshape(-1, 2)
    ob = big_mesh(name, V, Q, UV)
    # the margin band joins the two islands: give it the outer margin's texels
    ld = ob.data.uv_layers.active.data
    q0 = (R_ - 1) * (C_ - 1)
    for qi in range(q0, q0 + C_ - 1):
        for k in range(4):
            vi = int(Q[qi, k])
            if vi >= R_ * C_:
                ld[qi * 4 + k].uv = UV[vi - C_]
    ob['uv_ready'] = 1
    a = ob.data.color_attributes.new('st', 'FLOAT_COLOR', 'POINT')
    T2 = np.concatenate([Tg, Tg[::-1]]).ravel(); F2 = np.concatenate([Fg, Fg[::-1]]).ravel()
    inner = np.concatenate([np.zeros((R_, C_)), np.ones((R_, C_))]).ravel()
    rib = np.cos(F2 * 23 * math.pi) * 0.5 + 0.5
    st = np.stack([T2, F2 * 0.5 + 0.5, inner, rib], -1)
    a.data.foreach_set('color', st.astype(np.float32).ravel())
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
    be = [e for e in bm.edges if e.is_boundary]
    if be:
        bmesh.ops.holes_fill(bm, edges=be, sides=0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free()
    ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
    return ob


def uv_cell(ob, k):
    uv = ob.data.uv_layers.active.data
    a = np.empty(len(uv) * 2, np.float32); uv.foreach_get('uv', a); a = a.reshape(-1, 2)
    a[:, 0] = a[:, 0] * 0.5 + 0.5 * k
    uv.foreach_set('uv', a.ravel())


def mat_clam():
    m, nt, b = new_mat('HP_Clam')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='st')
    sep = N(nt, 'ShaderNodeSeparateColor'); nt.links.new(at.outputs['Color'], sep.inputs[0])
    t, phi, rib = sep.outputs[0], sep.outputs[1], at.outputs['Alpha']
    inner = sep.outputs[2]
    n1 = N(nt, 'ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 120; n1.inputs['Detail'].default_value = 4
    n2 = N(nt, 'ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 1500
    # outside: chalky cream to blue-grey growth bands, darker between the ribs, bleached umbo
    tt = mth(nt, 'ADD', t, mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', n1.outputs[0], 0.5), 0.05))
    bands = ramp(nt, [(0.0, (0.86, 0.80, 0.68)), (0.16, (0.80, 0.74, 0.62)), (0.30, (0.46, 0.50, 0.56)), (0.44, (0.78, 0.72, 0.60)), (0.58, (0.36, 0.41, 0.50)),
                      (0.70, (0.72, 0.68, 0.58)), (0.82, (0.38, 0.42, 0.50)), (0.93, (0.64, 0.58, 0.48)), (1.0, (0.44, 0.38, 0.32))])
    nt.links.new(tt, bands.inputs[0])
    nb = N(nt, 'ShaderNodeTexNoise'); nb.inputs['Scale'].default_value = 55; nb.inputs['Detail'].default_value = 3
    ribdark = mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', 1.0, rib), mth(nt, 'MULTIPLY', mth(nt, 'MULTIPLY', nb.outputs[0], t), 0.55))
    out = mixc(nt, bands.outputs[0], (0.34, 0.31, 0.28, 1), ribdark)
    wear = N(nt, 'ShaderNodeMapRange'); nt.links.new(n1.outputs[0], wear.inputs[0]); wear.inputs[1].default_value = 0.5; wear.inputs[2].default_value = 0.7
    umb = ramp(nt, [(0.0, (1, 1, 1)), (0.25, (1, 1, 1)), (0.55, (0, 0, 0))], mask=True); nt.links.new(tt, umb.inputs[0])
    out = mixc(nt, out, (0.86, 0.83, 0.76, 1), mth(nt, 'MULTIPLY', mth(nt, 'MAXIMUM', wear.outputs[0], umb.outputs[0]), 0.6))   # chalky abraded umbo and patches
    out = mixc(nt, out, (0.85, 0.82, 0.76, 1), mth(nt, 'MULTIPLY', mth(nt, 'MULTIPLY', rib, n1.outputs[0]), 0.5))   # abraded rib crests
    out = mixc(nt, out, (0.5, 0.5, 0.5, 1), mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', n2.outputs[0], 0.5), 0.4), 'OVERLAY')
    # inside: nacre, with pallial line, muscle scars and a purple stain at the hinge
    hue = N(nt, 'ShaderNodeTexNoise'); hue.inputs['Scale'].default_value = 35; hue.inputs['Detail'].default_value = 2
    nac = ramp(nt, [(0.25, (0.80, 0.70, 0.70)), (0.45, (0.84, 0.80, 0.70)), (0.6, (0.68, 0.80, 0.76)), (0.78, (0.70, 0.74, 0.86))])
    nt.links.new(hue.outputs[0], nac.inputs[0])
    stain = ramp(nt, [(0.0, (1, 1, 1)), (0.2, (1, 1, 1)), (0.5, (0, 0, 0))]); nt.links.new(tt, stain.inputs[0])
    ins = mixc(nt, nac.outputs[0], (0.40, 0.24, 0.34, 1), mth(nt, 'MULTIPLY', stain.outputs[0], 0.8))
    gb = N(nt, 'ShaderNodeTexWave'); gb.inputs['Scale'].default_value = 1.0; gb.inputs['Distortion'].default_value = 0.0
    gsc = mth(nt, 'MULTIPLY', tt, 60.0); gs = mth(nt, 'SINE', gsc)
    ins = mixc(nt, ins, (0.52, 0.50, 0.50, 1), mth(nt, 'MULTIPLY', mth(nt, 'MAXIMUM', gs, 0.0), 0.22))
    pal = ramp(nt, [(0.80, (0, 0, 0)), (0.835, (1, 1, 1)), (0.87, (0, 0, 0))]); nt.links.new(tt, pal.inputs[0])
    ins = mixc(nt, ins, (0.50, 0.46, 0.46, 1), mth(nt, 'MULTIPLY', pal.outputs[0], 0.75))
    rim = ramp(nt, [(0.9, (0, 0, 0)), (1.0, (1, 1, 1))]); nt.links.new(t, rim.inputs[0])
    ins = mixc(nt, ins, (0.70, 0.66, 0.60, 1), rim.outputs[0])
    # adductor scars: two dull ovals at phi about 0.22 and 0.78, t about 0.55
    sc1 = mth(nt, 'ADD', mth(nt, 'POWER', mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', phi, 0.2), 9.0), 2.0), mth(nt, 'POWER', mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', t, 0.55), 6.0), 2.0))
    sc2 = mth(nt, 'ADD', mth(nt, 'POWER', mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', phi, 0.8), 9.0), 2.0), mth(nt, 'POWER', mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', t, 0.55), 6.0), 2.0))
    scar = mth(nt, 'SUBTRACT', 1.0, mth(nt, 'MINIMUM', sc1, sc2), clamp=True)
    ins = mixc(nt, ins, (0.60, 0.54, 0.50, 1), mth(nt, 'MULTIPLY', scar, 0.9))
    col = mixc(nt, out, ins, inner)
    r_out = mth(nt, 'ADD', 0.62, mth(nt, 'MULTIPLY', n1.outputs[0], 0.2))
    r_in = mth(nt, 'ADD', mth(nt, 'ADD', 0.14, mth(nt, 'MULTIPLY', hue.outputs[0], 0.22)), mth(nt, 'MULTIPLY', mth(nt, 'MAXIMUM', scar, pal.outputs[0]), 0.4))
    rough = mth(nt, 'ADD', mth(nt, 'MULTIPLY', r_out, mth(nt, 'SUBTRACT', 1.0, inner)), mth(nt, 'MULTIPLY', r_in, inner))
    bump = mth(nt, 'MULTIPLY', mth(nt, 'MULTIPLY', n2.outputs[0], 0.3), mth(nt, 'SUBTRACT', 1.0, inner))
    finish_surface(nt, b, col, rough, bump, 0.0003, 0.006, 0.004)
    return m


def build_clam():
    L = 0.058
    mat = mat_clam()
    assets = []
    # --- closed: two valves margin to margin, lying on one side, a third sunk in the sand
    def closed(nr, nf, detail, nm):
        a = shell(nm + 'a', L, nr, nf, detail, 5, solid=True)
        b_ = shell(nm + 'b', L * 0.99, nr, nf, detail, 5, solid=True)
        b_.data.transform(Matrix.Scale(-1, 4, (0, 0, 1))); b_.data.flip_normals()
        uv_cell(a, 0); uv_cell(b_, 1)
        only(a); b_.select_set(True); bpy.ops.object.join()
        M = Matrix.Translation((0, 0.026, 0.0085)) @ Matrix.Rotation(math.radians(14), 4, 'X') @ Matrix.Rotation(math.radians(-7), 4, 'Y')
        a.data.transform(M); a.data.update()
        return a
    hi = closed(260, 420, True, 'clam_c_hi'); hi.data.materials.append(mat)
    lo = closed(8, 20, False, 'clam_c_lo')
    weld(lo, 1e-5); cut_ground(lo)
    lo.name = 'SM_ClamShell_Closed_LOD0'
    assets.append({'name': 'SM_ClamShell_Closed', 'lo': lo, 'his': [hi]})
    # --- open: butterflied pair, nacre up
    def opened(nr, nf, detail, nm):
        parts = []
        for k in (0, 1):
            v = shell(nm + str(k), L * (1.0 if k == 0 else 0.985), nr, nf, detail, 5)
            v.data.transform(Matrix.Rotation(math.radians(180), 4, 'Y'))          # interior up, still fanning toward -Y
            if k == 1:
                v.data.transform(Matrix.Scale(-1, 4, (0, 1, 0))); v.data.flip_normals()   # the mirror partner across the hinge
                v.data.transform(Matrix.Translation((0.003, 0.0045, 0.0015)) @ Matrix.Rotation(math.radians(-6), 4, 'X') @ Matrix.Rotation(math.radians(9), 4, 'Z'))
            else:
                v.data.transform(Matrix.Translation((0, -0.0045, 0)) @ Matrix.Rotation(math.radians(5), 4, 'X'))
            v.data.update()
            uv_cell(v, k)
            parts.append(v)
        only(parts[0]); parts[1].select_set(True); bpy.ops.object.join()
        o = parts[0]
        zmin = min(v.co.z for v in o.data.vertices)
        o.data.transform(Matrix.Rotation(math.radians(4), 4, 'Y')); o.data.update()
        zmin = min(v.co.z for v in o.data.vertices)
        o.data.transform(Matrix.Translation((0, 0, -zmin - 0.0005))); o.data.update()
        return o
    hi = opened(240, 400, True, 'clam_o_hi'); hi.data.materials.append(mat)
    lo = opened(7, 18, False, 'clam_o_lo')
    weld(lo, 1e-5); cut_ground(lo)
    lo.name = 'SM_ClamShell_Open_LOD0'
    assets.append({'name': 'SM_ClamShell_Open', 'lo': lo, 'his': [hi]})
    return assets


# ---------------------------------------------------------------- starfish
MAD = [None]


def starfish(nth, ns, detail, seed, R=0.075):
    r = np.random.default_rng(seed)
    arms = 5
    Ls = R * r.uniform(0.9, 1.08, arms)
    bends = r.normal(0, 0.22, arms)
    lifts = r.uniform(-0.1, 1.0, arms) * 0.006
    curls = r.uniform(0.0, 1.0, arms) ** 2 * 0.011                        # some tips curl up as it dries
    r_in = R * 0.30
    w0 = r_in * math.sin(math.pi / arms) * 1.18
    th = np.linspace(0, 2 * math.pi, nth, endpoint=False)
    # denser sampling near the arm axes
    th = th - 0.115 * np.sin(arms * th) * (2 / arms) * 1.9
    k = np.round(th / (2 * math.pi / arms)).astype(int) % arms
    dth = th - np.round(th / (2 * math.pi / arms)) * (2 * math.pi / arms)
    L = Ls[k]
    aa = np.linspace(0, 1, 600)[None, :] * L[:, None]

    def width(a, Lk):
        u = np.clip(a / Lk, 0, 1)
        return w0 * (1 - u) ** 0.62 * (1 - 0.12 * u) + 0.0085 * np.sqrt(np.clip(1 - u ** 2, 0, 1) + 1e-9) * (u < 1)
    ok = width(aa, L[:, None]) >= aa * np.tan(np.abs(dth))[:, None]
    amax = (aa * ok).max(1)
    Rb = np.maximum(amax / np.cos(dth), r_in * 0.98)
    s = (np.linspace(0, 1, ns + 1) ** 0.8)[:, None]
    rr = s * Rb[None, :]
    a = rr * np.cos(dth)[None, :]
    bl = rr * np.sin(dth)[None, :]
    Lk = L[None, :]
    w = np.maximum(width(a, Lk), 1e-5)
    q = np.clip(np.abs(bl) / w, 0, 1)
    # the rim (s = 1) is the outline: lateral fraction 1 there, also in the valleys between arms
    edge = np.maximum(q, s ** 6)
    u = np.clip(a / Lk, 0, 1)
    Hc = 0.0100 * (1 - u) ** 0.45 + 0.0042 * np.sqrt(np.clip(1 - u ** 3, 0, 1))
    disc = 0.0125 * np.exp(-(rr / (r_in * 1.15)) ** 2)
    ztop = np.maximum(Hc * (1 - edge ** 2.0) ** 0.5, disc * (1 - s ** 8))
    zbot = -0.0028 * (1 - edge ** 2) ** 0.5 * (1 - u * 0.5)
    groove = np.exp(-(q / 0.20) ** 2) * (u > 0.02)
    zbot = zbot + 0.0030 * groove * (1 - u) ** 0.3
    if detail:
        jit = np.sin(a * 900 + bl * 700) * 0.15
        # tubercles: carinal row down each arm plus oblique lateral rows, fading to the margin
        da = 0.0058
        car = np.maximum(np.cos(2 * math.pi * a / da), 0) ** 1.2 * np.exp(-(bl / 0.0022) ** 2)
        dl = 0.0052                                                        # round knobs on a staggered lattice in millimetres, not in arm-relative units
        rowi = np.round(bl / dl)
        lat = (np.maximum(np.cos(2 * math.pi * (a / da + 0.5 * rowi)), 0) * np.maximum(np.cos(2 * math.pi * bl / dl), 0)) ** 1.2 * (np.abs(rowi) >= 1) * (q < 0.85)
        marg = np.maximum(np.cos(2 * math.pi * a / (da * 0.7)), 0) ** 3 * np.exp(-((q - 0.9) / 0.1) ** 2)
        tub = (car * 1.0 + lat * 0.55 + marg * 0.6) * (rr > r_in * 0.15)
        dd = np.maximum(np.cos(th * 9)[None, :] * np.cos(rr / r_in * 7), 0) ** 2 * (rr < r_in * 0.9)   # disc granules
        mx, my = r_in * 0.42 * math.cos(0.63), r_in * 0.42 * math.sin(0.63)                # madreporite: a pale sieve plate off-centre on the disc
        xx0 = rr * np.cos(th)[None, :]; yy0 = rr * np.sin(th)[None, :]
        mad = np.exp(-(((xx0 - mx) ** 2 + (yy0 - my) ** 2) / (0.0026 ** 2)) ** 2)
        tub = np.clip(tub * (1 - mad), 0, 1.6)
        ztop = ztop + 0.0019 * tub * (1 - edge ** 6) + 0.0008 * dd * (1 - mad) + 0.0011 * mad
        MAD[0] = mad
        feet = (np.maximum(np.cos(2 * math.pi * a / 0.0024), 0) ** 2) * np.exp(-((q - 0.22) / 0.14) ** 2)
        zbot = zbot - 0.0011 * feet * (u < 0.95) * (rr > r_in * 0.25)
    else:
        tub = np.zeros_like(ztop); feet = np.zeros_like(ztop); MAD[0] = np.zeros_like(ztop)
    # arm pose: sideways bend and tip lift
    bend = bends[k][None, :] * u ** 2
    thb = th[None, :] + bend * np.exp(-(q * 0 + 0))
    x = rr * np.cos(thb); y = rr * np.sin(thb)
    lift = lifts[k][None, :] * u ** 2.5 + curls[k][None, :] * np.clip((u - 0.72) / 0.28, 0, 1) ** 2
    lift = lift + 0.0015 * u * np.sin(u * 5 + k[None, :])
    Vt = np.stack([x, y, ztop + lift], -1)
    Vb = np.stack([x, y, zbot + lift], -1)
    nS, nT = ns + 1, nth
    idx = np.arange(nS * nT).reshape(nS, nT)
    j1 = np.roll(idx, -1, 1)
    Qt = np.stack([idx[:-1], idx[1:], j1[1:], j1[:-1]], -1).reshape(-1, 4)
    V = np.concatenate([Vt.reshape(-1, 3), Vb.reshape(-1, 3)])
    Q = np.concatenate([Qt, Qt[:, ::-1] + nS * nT])
    att = np.stack([np.concatenate([u.ravel(), u.ravel()]), np.concatenate([q.ravel(), q.ravel()]),
                    np.concatenate([np.zeros(nS * nT), np.ones(nS * nT)]), np.concatenate([np.where(MAD[0] > 0.3, 0.5 + 0.5 * MAD[0], 0.5 * np.clip(tub, 0, 1)).ravel(), np.clip(feet, 0, 1).ravel() * 0.5])], -1)
    x0 = rr * np.cos(th)[None, :]; y0 = rr * np.sin(th)[None, :]
    m = R * 1.12 * 2
    ut = np.stack([x0 / m + 0.5, 0.5 + (y0 / m + 0.5) * 0.5], -1).reshape(-1, 2)
    ub = np.stack([x0 / m + 0.5, (y0 / m + 0.5) * 0.5], -1).reshape(-1, 2)
    return V, Q, att, nS, nT, np.concatenate([ut, ub])


def star_obj(name, nth, ns, detail, seed):
    V, Q, att, nS, nT, UV = starfish(nth, ns, detail, seed)
    ob = big_mesh(name, V, Q, UV)
    ob['uv_ready'] = 1
    a = ob.data.color_attributes.new('st', 'FLOAT_COLOR', 'POINT')
    a.data.foreach_set('color', att.astype(np.float32).ravel())
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5 if detail else 1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # recalc can settle on 'inside out' for a thin closed shell: the top sheet must face up
    zs = sum(f.normal.z * f.calc_area() for f in bm.faces if f.calc_center_median().z > 0.004)
    if zs < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        print('   flipped normals for', name)
    bm.to_mesh(ob.data); bm.free()
    zmin = min(v.co.z for v in ob.data.vertices) if not detail else None
    ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
    return ob


def mat_star():
    m, nt, b = new_mat('HP_Starfish')
    at = N(nt, 'ShaderNodeAttribute', attribute_name='st')
    sep = N(nt, 'ShaderNodeSeparateColor'); nt.links.new(at.outputs['Color'], sep.inputs[0])
    u, q, under, a_raw = sep.outputs[0], sep.outputs[1], sep.outputs[2], at.outputs['Alpha']
    bumpy = mth(nt, 'MULTIPLY', a_raw, 2.0, clamp=True)                      # alpha 0..0.5 = tubercle / tube foot, above 0.5 = madreporite
    mad = mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', a_raw, 0.5), 2.0, clamp=True)
    n1 = N(nt, 'ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 45; n1.inputs['Detail'].default_value = 5
    n3 = N(nt, 'ShaderNodeTexNoise'); n3.inputs['Scale'].default_value = 16; n3.inputs['Detail'].default_value = 3
    n2 = N(nt, 'ShaderNodeTexVoronoi'); n2.inputs['Scale'].default_value = 1500
    # dried skin: brick to ochre mottling in patches, never one flat orange
    mot = N(nt, 'ShaderNodeMapRange'); nt.links.new(n3.outputs[0], mot.inputs[0]); mot.inputs[1].default_value = 0.38; mot.inputs[2].default_value = 0.62
    top = mixc(nt, (0.46, 0.22, 0.14, 1), (0.60, 0.36, 0.22, 1), n1.outputs[0])
    top = mixc(nt, top, (0.58, 0.46, 0.34, 1), mth(nt, 'MULTIPLY', mot.outputs[0], 0.65))
    top = mixc(nt, top, (0.38, 0.13, 0.08, 1), mth(nt, 'MULTIPLY', mth(nt, 'POWER', q, 2.0), 0.35))
    top = mixc(nt, top, (0.80, 0.60, 0.40, 1), mth(nt, 'MULTIPLY', bumpy, 0.8))            # pale tubercle caps
    gran = mth(nt, 'SUBTRACT', 1.0, mth(nt, 'MULTIPLY', n2.outputs['Distance'], 2.5), clamp=True)
    top = mixc(nt, top, (0.74, 0.46, 0.26, 1), mth(nt, 'MULTIPLY', gran, 0.3))
    top = mixc(nt, top, (0.84, 0.74, 0.58, 1), mth(nt, 'MULTIPLY', mad, 0.9))
    tipf = N(nt, 'ShaderNodeMapRange'); nt.links.new(u, tipf.inputs[0]); tipf.inputs[1].default_value = 0.8; tipf.inputs[2].default_value = 1.0
    top = mixc(nt, top, (0.74, 0.52, 0.32, 1), mth(nt, 'MULTIPLY', tipf.outputs[0], 0.5))  # bleached tips
    bot = mixc(nt, (0.70, 0.50, 0.30, 1), (0.82, 0.66, 0.44, 1), n1.outputs[0])
    groove = mth(nt, 'SUBTRACT', 1.0, mth(nt, 'MULTIPLY', q, 3.0), clamp=True)
    bot = mixc(nt, bot, (0.45, 0.24, 0.14, 1), mth(nt, 'MULTIPLY', groove, 0.6))
    bot = mixc(nt, bot, (0.90, 0.82, 0.66, 1), mth(nt, 'MULTIPLY', bumpy, 0.9))
    col = mixc(nt, top, bot, under)
    rough = mth(nt, 'ADD', 0.74, mth(nt, 'MULTIPLY', n1.outputs[0], 0.2))                  # dry and matte
    bump = mth(nt, 'ADD', mth(nt, 'MULTIPLY', gran, 0.8), mth(nt, 'MULTIPLY', n1.outputs[0], 0.3))
    finish_surface(nt, b, col, rough, bump, 0.00025, 0.0015, 0.0012, sand_gain=0.45)
    return m


def build_starfish():
    mat = mat_star()
    assets = []
    for nm, seed in (('A', 3), ('B', 8)):
        hi = star_obj('star_hi_' + nm, 1600, 150, True, seed)
        lo = star_obj('star_lo_' + nm, 80, 5, False, seed)
        zmin = min(v.co.z for v in lo.data.vertices)
        for o in (hi, lo):
            o.data.transform(Matrix.Translation((0, 0, -zmin))); o.data.update()
        hi.data.materials.append(mat)
        lo.name = 'SM_Starfish_%s_LOD0' % nm
        assets.append({'name': 'SM_Starfish_' + nm, 'lo': lo, 'his': [hi]})
    return assets


# ---------------------------------------------------------------- bake + export
def unwrap(lo, slot, nslots):
    only(lo)
    if lo.get('uv_ready'):
        # two assets side by side, each in a 0.5 x 1 cell (clam: its two valves split that cell again)
        uv = lo.data.uv_layers.active.data
        a = np.empty(len(uv) * 2, np.float32); uv.foreach_get('uv', a); a = a.reshape(-1, 2)
        a = np.clip(a, 0.002, 0.998)
        a[:, 0] = a[:, 0] * 0.5 + slot * 0.5
        uv.foreach_set('uv', a.ravel())
        return
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.012, area_weight=0.0)
    bpy.ops.uv.pack_islands(margin=0.012, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    n = 2 if nslots > 1 else 1
    uv = lo.data.uv_layers.active.data
    a = np.empty(len(uv) * 2, np.float32); uv.foreach_get('uv', a); a = a.reshape(-1, 2)
    a = np.clip(a, 0.004, 0.996) / n + np.array([slot % n, slot // n], np.float32) / n
    uv.foreach_set('uv', a.ravel())


def bake_family(fam, assets):
    sc = bpy.context.scene
    imgs = {}
    for k, cs in (('BC', 'sRGB'), ('N', 'Non-Color'), ('R', 'Non-Color'), ('AO', 'Non-Color')):
        im = bpy.data.images.new('%s_%s' % (fam, k), ATLAS, ATLAS, alpha=False, float_buffer=(k != 'BC'))
        im.colorspace_settings.name = cs
        im.generated_color = (0.5, 0.5, 1, 1) if k == 'N' else ((1, 1, 1, 1) if k == 'AO' else (0.5, 0.45, 0.4, 1))
        imgs[k] = im
    gm = bpy.data.materials.new('MI_Scatter_' + fam); gm.use_nodes = True
    nt = gm.node_tree
    tn = nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active = tn
    # ground plane for contact occlusion
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, -0.0002)); plane = bpy.context.active_object
    for i, a in enumerate(assets):
        lo = a['lo']
        lo.data.materials.clear(); lo.data.materials.append(gm)
        unwrap(lo, i, len(assets))
    for i, a in enumerate(assets):
        lo = a['lo']
        for o in bpy.context.view_layer.objects:      # hide the other assets from rays
            o.hide_render = True
        plane.hide_render = False
        for h in a['his']:
            h.hide_render = False
        lo.hide_render = False
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for h in a['his']:
            h.select_set(True)
        lo.select_set(True); bpy.context.view_layer.objects.active = lo
        size = max(lo.dimensions)
        bk = sc.render.bake
        bk.use_selected_to_active = True; bk.cage_extrusion = max(0.0015, size * 0.02); bk.max_ray_distance = max(0.004, size * 0.05)
        if fam == 'Clam':
            bk.cage_extrusion = 0.003; bk.max_ray_distance = 0.007
        if fam == 'Starfish':
            bk.cage_extrusion = 0.0035; bk.max_ray_distance = 0.008
        bk.margin = 6; bk.use_clear = False
        for k, typ in (('BC', 'DIFFUSE'), ('R', 'ROUGHNESS'), ('N', 'NORMAL'), ('AO', 'AO')):
            tn.image = imgs[k]
            sc.cycles.samples = 48 if k == 'AO' else (16 if k == 'BC' else 4)
            plane.hide_render = (k != 'AO')
            if typ == 'DIFFUSE':
                bk.use_pass_direct = False; bk.use_pass_indirect = False; bk.use_pass_color = True
            bpy.ops.object.bake(type=typ, pass_filter={'COLOR'} if typ == 'DIFFUSE' else set(), use_selected_to_active=True, cage_extrusion=bk.cage_extrusion, max_ray_distance=bk.max_ray_distance,
                                margin=6, use_clear=False, normal_space='TANGENT')
        print('baked', a['name'])
    # compose and save
    def px(im):
        a = np.empty(ATLAS * ATLAS * 4, np.float32); im.pixels.foreach_get(a); return a.reshape(ATLAS, ATLAS, 4)
    R_ = px(imgs['R'])[..., 0]; AO = px(imgs['AO'])[..., 0]
    orm = np.stack([np.clip(AO, 0, 1), np.clip(R_, 0.04, 1), np.zeros_like(R_), np.ones_like(R_)], -1)
    o = bpy.data.images.new(fam + '_ORM', ATLAS, ATLAS, alpha=False); o.colorspace_settings.name = 'Non-Color'
    o.pixels.foreach_set(orm.ravel())
    out = {}
    for key, im in (('BC', imgs['BC']), ('N', imgs['N']), ('ORM', o)):
        p = os.path.join(OUT, 'Textures', 'T_Scatter_%s_%s.png' % (fam, key))
        im.filepath_raw = p; im.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGB'
        im.save_render(p) if False else im.save()
        out[key] = 'Scatter/Textures/' + os.path.basename(p)
    bpy.data.objects.remove(plane)
    # final game material preview wiring
    nt.nodes.remove(tn)
    b = nt.nodes['Principled BSDF']
    def t(key, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(TERRAIN, out[key])); n.image.colorspace_settings.name = cs; return n
    tb = t('BC', 'sRGB'); tnn = t('N', 'Non-Color'); to = t('ORM', 'Non-Color')
    nt.links.new(tb.outputs[0], b.inputs['Base Color'])
    s = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(to.outputs[0], s.inputs[0]); nt.links.new(s.outputs[1], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tnn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    return out


def finish_assets(fam, assets, texs, families, cls='prop_small'):
    recs = []
    for a in assets:
        lo = a['lo']
        # pivot: base centre
        bb = np.array([v.co[:] for v in lo.data.vertices])
        c = np.array([(bb[:, 0].min() + bb[:, 0].max()) / 2, (bb[:, 1].min() + bb[:, 1].max()) / 2, bb[:, 2].min()])
        lo.data.transform(Matrix.Translation(tuple(-c))); lo.data.update()
        for h in a['his']:
            h.data.transform(Matrix.Translation(tuple(-c)))
        lo.location = (0, 0, 0)
        only(lo); bpy.ops.object.duplicate()
        l1 = bpy.context.active_object; l1.name = a['name'] + '_LOD1'; l1.data.name = l1.name
        m = l1.modifiers.new('d', 'DECIMATE'); m.ratio = 0.42; m.use_collapse_triangulate = True
        apply_mods(l1)
        coll = bpy.data.collections.new(a['name']); bpy.context.scene.collection.children.link(coll)
        coll['dink_class'] = cls; coll['dink_path'] = 'Scatter'; coll['dink_tex_px'] = ATLAS
        coll['dink_source'] = 'authored in Blender (procedural high-detail source baked to the game mesh), photoreal pass 11 Nov 2026'
        for o in (lo, l1):
            for cc in list(o.users_collection):
                cc.objects.unlink(o)
            coll.objects.link(o)
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        lo.select_set(True); l1.select_set(True); bpy.context.view_layer.objects.active = lo
        fbx = os.path.join(OUT, a['name'] + '.fbx')
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL',
                                 axis_forward='Y', axis_up='Z', bake_space_transform=False, use_triangles=True, mesh_smooth_type='FACE',
                                 use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP', object_types={'MESH', 'EMPTY'})
        # checks
        bm = bmesh.new(); bm.from_mesh(lo.data)
        nonman = sum(1 for e in bm.edges if not e.is_manifold)
        if nonman:
            print('NONMANIFOLD', a['name'], [(len(e.link_faces), tuple(round(c, 4) for c in ((e.verts[0].co + e.verts[1].co) / 2))) for e in bm.edges if not e.is_manifold][:20])
        bm.free()
        uv = np.empty(len(lo.data.uv_layers.active.data) * 2, np.float32); lo.data.uv_layers.active.data.foreach_get('uv', uv)
        d = lo.dimensions
        recs.append({'name': a['name'], 'class': cls, 'fbx': 'Scatter/' + os.path.basename(fbx), 'dimensions_m': [round(x, 4) for x in d],
                     'lod0_triangles': tris(lo), 'lod1_triangles': tris(l1), 'textures': texs, 'texture_px': ATLAS,
                     'material': 'MI_Scatter_' + fam, 'families': families, 'pivot': 'base_center',
                     'checks': {'non_manifold_edges': nonman, 'uv_min': round(float(uv.min()), 4), 'uv_max': round(float(uv.max()), 4)},
                     'source_blend': 'Scatter/Scatter_%s.blend' % fam})
        print('ASSET', recs[-1]['name'], recs[-1]['dimensions_m'], recs[-1]['lod0_triangles'], recs[-1]['lod1_triangles'], recs[-1]['checks'])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Scatter_%s.blend' % fam), compress=True)
    json.dump(recs, open(os.path.join(OUT, 'scatter_%s.json' % fam), 'w'), indent=1)


for fam in FAMS:
    reset()
    if fam == 'BeachPebbles':
        A = build_pebbles(fam, False, 101)
        fams = ['beach_pebbles']
    elif fam == 'Pebbles':
        A = build_pebbles(fam, True, 202)
        fams = ['pebbles']
    elif fam == 'Clam':
        A = build_clam(); fams = ['seashell_clam']
    else:
        A = build_starfish(); fams = ['starfish']
    texs = bake_family(fam, A)
    finish_assets(fam, A, texs, fams)
    print('FAMILY DONE', fam)
