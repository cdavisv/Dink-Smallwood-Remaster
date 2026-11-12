"""Blender helpers: build modelled sprays/leaves in the XY plane and render them to atlas passes (bc+alpha, normal, aux, sss)."""
import bpy, numpy as np, os, math
from mathutils import Vector

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'METRIC'; s.unit_settings.scale_length = 1.0
    return s

def mesh_obj(name, verts, faces, cols=None, uvs=None, smooth=True):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, dtype=np.float32)
    me.from_pydata(verts.tolist() if len(verts) < 5000 else [], [], [])
    if len(verts) >= 5000:
        me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.ravel())
    if isinstance(faces, np.ndarray):
        nf, k = faces.shape
        me.loops.add(nf * k); me.loops.foreach_set('vertex_index', faces.ravel().astype(np.int32))
        me.polygons.add(nf)
        me.polygons.foreach_set('loop_start', np.arange(0, nf * k, k, dtype=np.int32))
        me.polygons.foreach_set('loop_total', np.full(nf, k, dtype=np.int32))
    else:
        tot = sum(len(f) for f in faces)
        me.loops.add(tot); me.polygons.add(len(faces))
        me.loops.foreach_set('vertex_index', np.fromiter((i for f in faces for i in f), dtype=np.int32, count=tot))
        ls = np.cumsum([0] + [len(f) for f in faces[:-1]]).astype(np.int32)
        me.polygons.foreach_set('loop_start', ls)
        me.polygons.foreach_set('loop_total', np.array([len(f) for f in faces], dtype=np.int32))
    me.update(calc_edges=True); me.validate()
    if cols is not None:
        a = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        c = np.asarray(cols, dtype=np.float32)
        if c.shape[1] == 3: c = np.hstack([c, np.ones((len(c), 1), np.float32)])
        a.data.foreach_set('color', c.ravel())
    if uvs is not None:
        uv = me.uv_layers.new(name='UVMap')
        uv.data.foreach_set('uv', np.asarray(uvs, dtype=np.float32).ravel())
    if smooth:
        me.polygons.foreach_set('use_smooth', np.ones(len(me.polygons), dtype=bool))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

# ---------- pass materials -------------
def pass_material(name, mode, albedo, alpha=None, normal=None, rough=0.5, sss=None, height_range=0.12):
    """albedo / alpha / normal / sss are callables (nodes, links) -> socket, or constants."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); N = nt.nodes; L = nt.links
    def val(x, default):
        if x is None: x = default
        if callable(x): return x(N, L)
        if isinstance(x, (int, float)):
            n = N.new('ShaderNodeValue'); n.outputs[0].default_value = x; return n.outputs[0]
        n = N.new('ShaderNodeRGB'); n.outputs[0].default_value = (*x, 1); return n.outputs[0]
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission')
    geo = N.new('ShaderNodeNewGeometry')
    if mode == 'bc':
        L.new(val(albedo, (0.5, 0.5, 0.5)), em.inputs[0])
    elif mode == 'sss':
        L.new(val(sss, (0, 0, 0)), em.inputs[0])
    elif mode == 'n':
        nsock = normal(N, L) if normal else geo.outputs['Normal']
        # flip to face the camera (+Z) and encode
        flip = N.new('ShaderNodeMath'); flip.operation = 'MULTIPLY_ADD'
        L.new(geo.outputs['Backfacing'], flip.inputs[0]); flip.inputs[1].default_value = -2; flip.inputs[2].default_value = 1
        if normal is None:
            sc = N.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'
            L.new(nsock, sc.inputs[0]); L.new(flip.outputs[0], sc.inputs['Scale']); nsock = sc.outputs[0]
        ma = N.new('ShaderNodeVectorMath'); ma.operation = 'MULTIPLY_ADD'
        L.new(nsock, ma.inputs[0]); ma.inputs[1].default_value = (0.5, 0.5, 0.5); ma.inputs[2].default_value = (0.5, 0.5, 0.5)
        L.new(ma.outputs[0], em.inputs[0])
    elif mode == 'aux':
        ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.06; ao.samples = 8
        sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs[0])
        mr = N.new('ShaderNodeMapRange'); L.new(sep.outputs['Z'], mr.inputs[0])
        mr.inputs[1].default_value = -height_range; mr.inputs[2].default_value = height_range
        cmb = N.new('ShaderNodeCombineColor')
        L.new(ao.outputs['AO'], cmb.inputs[0]); L.new(val(rough, 0.5), cmb.inputs[1]); L.new(mr.outputs[0], cmb.inputs[2])
        L.new(cmb.outputs[0], em.inputs[0])
    if alpha is not None:
        tr = N.new('ShaderNodeBsdfTransparent'); mix = N.new('ShaderNodeMixShader')
        L.new(val(alpha, 1.0), mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
        L.new(mix.outputs[0], out.inputs[0])
    else:
        L.new(em.outputs[0], out.inputs[0])
    return m

def attr_col(name='Col'):
    def f(N, L):
        a = N.new('ShaderNodeAttribute'); a.attribute_name = name; return a.outputs['Color']
    return f

def render_atlas(scene, world_w, world_h, px_w, px_h, out_prefix, rebuild, samples=24):
    """rebuild(mode) must (re)create all materials for the mode. Camera looks down -Z, +X right, +Y up; atlas origin at (0,0)."""
    cam = bpy.data.cameras.new('AtlasCam'); cam.type = 'ORTHO'; cam.ortho_scale = max(world_w, world_h)
    cam.clip_start = 0.1; cam.clip_end = 50
    co = bpy.data.objects.new('AtlasCam', cam); scene.collection.objects.link(co)
    co.location = (world_w / 2, world_h / 2, 10)
    scene.camera = co
    r = scene.render
    r.engine = 'CYCLES'; scene.cycles.samples = samples; scene.cycles.use_denoising = False
    import bl_tree; bl_tree.use_hip_gpu(scene)
    scene.cycles.max_bounces = 2; scene.cycles.transparent_max_bounces = 16
    r.resolution_x = px_w; r.resolution_y = px_h; r.resolution_percentage = 100
    r.film_transparent = True; r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'; r.image_settings.color_depth = '8'
    scene.display_settings.display_device = 'sRGB'
    w = bpy.data.worlds.new('W'); scene.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.0
    for mode in ('bc', 'n', 'aux', 'sss'):
        rebuild(mode)
        scene.view_settings.view_transform = 'Standard' if mode in ('bc', 'sss') else 'Raw'
        scene.view_settings.look = 'None'
        r.filepath = f'{out_prefix}_{mode}.png'
        bpy.ops.render.render(write_still=True)
        print('rendered', r.filepath, flush=True)

# ---------- twig / leaf modelling helpers -------------
def frame(d):
    d = d / np.linalg.norm(d)
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(d, a); u /= np.linalg.norm(u); v = np.cross(d, u)
    return d, u, v

def curve(p0, d0, L, rng, n=10, wander=0.15, droop=0.0, zscale=0.5, grav=(0, 0, -1)):
    pts = [np.array(p0, float)]; d = np.array(d0, float); d /= np.linalg.norm(d)
    for i in range(n):
        d = d + rng.normal(0, wander / n ** 0.5, 3) * np.array([1, 1, zscale]) + np.array(grav) * droop / n
        d /= np.linalg.norm(d); pts.append(pts[-1] + d * L / n)
    return np.array(pts)

class Geo:
    """accumulates a vertex-coloured, UV-mapped mesh"""
    def __init__(s): s.v = []; s.f = []; s.c = []; s.uv = []
    def tube(s, pts, radii, col, sides=6, rng=None):
        base = len(s.v)
        for i, p in enumerate(pts):
            d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            _, u, v = frame(d)
            for k in range(sides):
                a = 2 * math.pi * k / sides
                s.v.append(p + radii[i] * (math.cos(a) * u + math.sin(a) * v)); s.c.append(np.asarray(col) * (0.85 + 0.3 * (rng.random() if rng else 0.5)))
        for i in range(len(pts) - 1):
            for k in range(sides):
                a = base + i * sides + k; b = base + i * sides + (k + 1) % sides
                s.f.append((a, b, b + sides, a + sides)); s.uv.append(((0, 0),) * 4)
    def leaf(s, base, d, n, length, width, uvrect, tint, fold=0.15, curl=0.1, twist=0.0, nu=4, nv=6, wave=0.0, rng=None):
        d = d / np.linalg.norm(d); n = n - d * np.dot(n, d); n /= np.linalg.norm(n); side = np.cross(d, n)
        u0, v0, u1, v1 = uvrect; b0 = len(s.v); idx = {}
        for j in range(nv + 1):
            t = j / nv; tw = twist * t
            sd = side * math.cos(tw) + n * math.sin(tw); nn = np.cross(sd, d)
            c = np.asarray(base) + d * length * t + nn * (-curl) * length * t * t
            for i in range(nu + 1):
                x = i / nu - 0.5
                wv = wave * width * math.sin(t * 9 + i * 2.1) * abs(x) * 2 if wave else 0
                s.v.append(c + sd * x * width + nn * (fold * abs(x) * width + wv)); s.c.append(tint)
                idx[(i, j)] = (u0 + (u1 - u0) * (i / nu), v0 + (v1 - v0) * t)
        for j in range(nv):
            for i in range(nu):
                a = b0 + j * (nu + 1) + i
                s.f.append((a, a + 1, a + nu + 2, a + nu + 1))
                s.uv.append((idx[(i, j)], idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    def obj(s, name):
        uv = np.array([c for f in s.uv for p in f for c in p], dtype=np.float32).reshape(-1, 2) if s.uv else None
        return mesh_obj(name, np.array(s.v), np.array(s.f, dtype=np.int32), np.array(s.c), uv)

def tex(N, path, cs='sRGB'):
    n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(path, check_existing=True); n.image.colorspace_settings.name = cs
    n.extension = 'EXTEND'; return n

def leaf_mats(mode, name, color_path, opacity_path, normal_path, rough=0.5, sss_mul=(1.7, 1.6, 0.6), alpha_from_color=False, nstrength=1.0):
    """leaf material whose albedo = texture * vertex colour 'Col'."""
    def alb(N, L):
        t = tex(N, color_path); a = N.new('ShaderNodeAttribute'); a.attribute_name = 'Col'
        m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'; m.inputs[0].default_value = 1
        L.new(t.outputs[0], m.inputs[6]); L.new(a.outputs['Color'], m.inputs[7]); return m.outputs[2]
    def alpha(N, L):
        if alpha_from_color: return tex(N, color_path).outputs['Alpha']
        return tex(N, opacity_path, 'Non-Color').outputs[0]
    def nrm_(N, L):
        t = tex(N, normal_path, 'Non-Color'); nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstrength
        L.new(t.outputs[0], nm.inputs['Color']); return nm.outputs[0]
    def sss(N, L):
        a = alb(N, L); m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = 'MULTIPLY'; m.inputs[0].default_value = 1
        L.new(a, m.inputs[6]); m.inputs[7].default_value = (*sss_mul, 1); return m.outputs[2]
    return pass_material(name, mode, alb, alpha=alpha, normal=nrm_ if normal_path else None, rough=rough, sss=sss)
