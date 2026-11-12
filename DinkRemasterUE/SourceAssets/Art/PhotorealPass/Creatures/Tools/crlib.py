"""Shared helpers for the photoreal creature pass (Blender 5.2 batch, metres, +X forward, +Z up)."""
import bpy, bmesh, math, json, os, sys, random
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion, noise

OUT = Path(__file__).resolve().parents[1]            # .../PhotorealPass/Creatures
ART = OUT.parents[1]                                 # .../SourceAssets/Art
PROJ = ART.parents[1]                                # DinkRemasterUE
REPO = PROJ.parent
THIRD = OUT.parent / 'ThirdParty'
sys.path.insert(0, str(REPO / 'tools/blender'))


def use_hip_gpu(scene=None):
    """Render/bake on the RX 6800 via HIP (CYCLES_GPU.md); only the discrete card, preferences changed in memory only. CR_CPU=1 forces CPU."""
    scene = scene or bpy.context.scene; scene.render.engine = 'CYCLES'; found = False
    try:
        if os.environ.get('CR_CPU'): raise RuntimeError('CPU forced')
        prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'HIP'; prefs.refresh_devices()
        for d in prefs.devices:
            d.use = (d.type == 'HIP' and 'Radeon RX 6800' in d.name); found |= d.use
    except Exception as ex: print('[CR] GPU not used:', ex, flush=True)
    scene.cycles.device = 'GPU' if found else 'CPU'; print('[CR] Cycles device', scene.cycles.device, flush=True); return found


def log(*a): print('[CR]', *a, flush=True)
def args(): return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def activate(o):
    bpy.context.view_layer.update()
    for x in bpy.context.view_layer.objects:
        if x is not None: x.select_set(False)
    o.hide_set(False); o.select_set(True); bpy.context.view_layer.objects.active = o


# ------------------------------------------------------------------ mesh builder
class MB:
    """Accumulates parts into one skinned mesh with two colour attributes used as shader masks."""
    def __init__(self):
        self.v = []; self.f = []; self.w = []; self.msk = []; self.loc = []; self.hid = []

    def add(self, vs, fs, bone, msk=(0, 0, 0, 0), loc=None, hidden=False):
        """bone: name, or per-vertex list of {bone: w}. msk/loc: tuple or per-vertex list."""
        b = len(self.v); n = len(vs)
        self.v += [tuple(p) for p in vs]
        self.f += [tuple(b + i for i in f) for f in fs]
        self.w += ([{bone: 1.0}] * n) if isinstance(bone, str) else list(bone)
        self.msk += ([tuple(msk)] * n) if isinstance(msk[0], (int, float)) else [tuple(m) for m in msk]
        if loc is None: loc = (0, 0, 0, 0)
        self.loc += ([tuple(loc)] * n) if isinstance(loc[0], (int, float)) else [tuple(m) for m in loc]
        self.hid += [hidden] * len(fs)
        return range(b, b + n)

    def build(self, name, coll, mats):
        me = bpy.data.meshes.new(name); me.from_pydata(self.v, [], self.f); me.update()
        ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
        for m in mats: me.materials.append(m)
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        groups = {}
        for i, d in enumerate(self.w):
            for k, w in d.items():
                g = groups.get(k) or groups.setdefault(k, ob.vertex_groups.new(name=k)); g.add([i], w, 'REPLACE')
        for nm, data in (('msk', self.msk), ('loc', self.loc)):
            a = me.color_attributes.new(nm, 'FLOAT_COLOR', 'POINT'); a.data.foreach_set('color', np.asarray(data, np.float32).ravel())
        h = me.attributes.new('hid', 'BOOLEAN', 'FACE'); h.data.foreach_set('value', self.hid)
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(me); bm.free(); me.update()
        return ob


def frame(t, ref=(0, 0, 1)):
    t = Vector(t).normalized(); r = Vector(ref)
    if abs(t.dot(r)) > .95: r = Vector((0, 1, 0))
    u = t.cross(r).normalized(); v = t.cross(u).normalized(); return u, v


def tube(points, radii, n=8, squash=(1, 1), ref=(0, 0, 1), cap=(True, True), twist=0.0):
    """Lofted tube. Returns verts, faces, t (0..1 along per vertex), ang (0..1 around)."""
    pts = [Vector(p) for p in points]; vs = []; fs = []; ts = []; an = []
    L = [0.0]
    for i in range(1, len(pts)): L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    for i, p in enumerate(pts):
        tg = pts[min(i + 1, len(pts) - 1)] - pts[max(0, i - 1)]
        u, v = frame(tg, ref)
        for j in range(n):
            a = math.tau * j / n + twist * i
            vs.append(p + radii[i] * (math.cos(a) * u * squash[0] + math.sin(a) * v * squash[1])); ts.append(L[i] / max(L[-1], 1e-9)); an.append(j / n)
    for i in range(len(pts) - 1):
        for j in range(n):
            a = i * n + j; b = i * n + (j + 1) % n; fs.append((a, b, b + n, a + n))
    if cap[0]:
        vs.append(pts[0]); ts.append(0); an.append(0); c = len(vs) - 1
        fs += [(c, (j + 1) % n, j) for j in range(n)]
    if cap[1]:
        vs.append(pts[-1]); ts.append(1); an.append(0); c = len(vs) - 1; o = (len(pts) - 1) * n
        fs += [(c, o + j, o + (j + 1) % n) for j in range(n)]
    return vs, fs, ts, an


def ellipsoid(center, radii, n=16, rings=8, fn=None):
    """UV ellipsoid; fn(unit_vec)->Vector offset multiplier hook for sculpting. Returns verts, faces, unit dirs."""
    c = Vector(center); dirs = [Vector((0, 0, 1))]; fs = []
    for i in range(1, rings):
        p = math.pi * i / rings
        for j in range(n):
            a = math.tau * j / n; dirs.append(Vector((math.sin(p) * math.cos(a), math.sin(p) * math.sin(a), math.cos(p))))
    dirs.append(Vector((0, 0, -1))); bot = len(dirs) - 1
    for j in range(n):
        fs.append((0, 1 + j, 1 + (j + 1) % n)); fs.append((bot, 1 + (rings - 2) * n + (j + 1) % n, 1 + (rings - 2) * n + j))
    for i in range(rings - 2):
        for j in range(n):
            a = 1 + i * n + j; b = 1 + i * n + (j + 1) % n; fs.append((a, a + n, b + n, b))
    vs = []
    for d in dirs:
        p = Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2]))
        if fn: p = fn(d, p)
        vs.append(c + p)
    return vs, fs, dirs


def nz(p, scale=1.0, seed=0.0):
    """Signed smooth noise in about -1..1."""
    return noise.noise(Vector(p) * scale + Vector((seed, seed * 1.7, seed * 2.3)))


# ------------------------------------------------------------------ shader node helper
class NT:
    def __init__(self, mat):
        mat.use_nodes = True; self.nt = mat.node_tree; self.nt.nodes.clear(); self.L = self.nt.links
    def node(self, t, **kw):
        n = self.nt.nodes.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def link(self, a, b): self.L.new(a, b)
    def _set(self, sock, v):
        if v is None: return
        if hasattr(v, 'bl_idname') or hasattr(v, 'is_linked'): self.link(v, sock)
        else: sock.default_value = v
    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp); self._set(n.inputs[0], a); self._set(n.inputs[1], b); self._set(n.inputs[2], c); return n.outputs[0]
    def vmath(self, op, a, b=None, s=None):
        n = self.node('ShaderNodeVectorMath', operation=op); self._set(n.inputs[0], a); self._set(n.inputs[1], b)
        if s is not None: self._set(n.inputs['Scale'], s)
        return n.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs[0]
    def mix(self, f, a, b, blend='MIX'):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend); n.clamp_factor = True
        self._set(n.inputs[0], f); self._set(n.inputs[6], a if not isinstance(a, tuple) else (*a, 1)[:4]); self._set(n.inputs[7], b if not isinstance(b, tuple) else (*b, 1)[:4]); return n.outputs[2]
    def mixf(self, f, a, b):
        n = self.node('ShaderNodeMix', data_type='FLOAT'); n.clamp_factor = True
        self._set(n.inputs[0], f); self._set(n.inputs[2], a); self._set(n.inputs[3], b); return n.outputs[0]
    def noise(self, vec, scale, detail=4, rough=.6, dist=0.0, dim='3D'):
        n = self.node('ShaderNodeTexNoise', noise_dimensions=dim); self._set(n.inputs['Vector'], vec)
        n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = dist
        return n.outputs['Fac'], n.outputs['Color']
    def voronoi(self, vec, scale, feature='F1', rand=1.0, smooth=None):
        n = self.node('ShaderNodeTexVoronoi', feature=feature); self._set(n.inputs['Vector'], vec); n.inputs['Scale'].default_value = scale; n.inputs['Randomness'].default_value = rand
        if smooth is not None and 'Smoothness' in n.inputs: n.inputs['Smoothness'].default_value = smooth
        return n.outputs['Distance'], n.outputs['Color']
    def ramp(self, f, stops, interp='LINEAR'):
        n = self.node('ShaderNodeValToRGB'); r = n.color_ramp; r.interpolation = interp
        while len(r.elements) < len(stops): r.elements.new(.5)
        for e, (p, c) in zip(r.elements, stops):
            e.position = p; e.color = (c, c, c, 1) if isinstance(c, (int, float)) else (*c, 1)[:4]
        self._set(n.inputs[0], f); return n.outputs[0]
    def smooth(self, f, lo, hi):
        n = self.node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP'); self._set(n.inputs[0], f); n.inputs[1].default_value = lo; n.inputs[2].default_value = hi; return n.outputs[0]
    def attr(self, name):
        n = self.node('ShaderNodeAttribute', attribute_name=name); return n
    def sep(self, c):
        n = self.node('ShaderNodeSeparateColor'); self._set(n.inputs[0], c); return n.outputs
    def sepxyz(self, v):
        n = self.node('ShaderNodeSeparateXYZ'); self._set(n.inputs[0], v); return n.outputs
    def comb(self, x, y, z):
        n = self.node('ShaderNodeCombineXYZ'); self._set(n.inputs[0], x); self._set(n.inputs[1], y); self._set(n.inputs[2], z); return n.outputs[0]
    def mapping(self, vec, scale=(1, 1, 1), rot=(0, 0, 0), loc=(0, 0, 0)):
        n = self.node('ShaderNodeMapping'); self._set(n.inputs[0], vec); n.inputs['Scale'].default_value = scale; n.inputs['Rotation'].default_value = rot; n.inputs['Location'].default_value = loc; return n.outputs[0]
    def bump(self, height, dist, strength=1.0, normal=None):
        n = self.node('ShaderNodeBump'); self._set(n.inputs['Height'], height); n.inputs['Distance'].default_value = dist; n.inputs['Strength'].default_value = strength
        if normal is not None: self._set(n.inputs['Normal'], normal)
        return n.outputs[0]
    def finish(self, color, rough, normal, sss=None, sss_color=None, sss_radius=(.01, .004, .002), spec=.5, alpha=None, coat=None):
        """Principled surface; stores sockets for the baker on the tree."""
        b = self.node('ShaderNodeBsdfPrincipled'); o = self.node('ShaderNodeOutputMaterial')
        self._set(b.inputs['Base Color'], color); self._set(b.inputs['Roughness'], rough)
        if normal is not None: self._set(b.inputs['Normal'], normal)
        b.inputs['Specular IOR Level'].default_value = spec
        if sss is not None:
            self._set(b.inputs['Subsurface Weight'], sss); b.inputs['Subsurface Radius'].default_value = sss_radius; b.inputs['Subsurface Scale'].default_value = 1.0
        if alpha is not None: self._set(b.inputs['Alpha'], alpha)
        if coat is not None: self._set(b.inputs['Coat Weight'], coat); b.inputs['Coat Roughness'].default_value = .08
        self.link(b.outputs[0], o.inputs[0])
        b.name = 'PR_BSDF'; o.name = 'PR_OUT'
        em = self.node('ShaderNodeEmission'); em.name = 'PR_EMIT'
        self.bake = {'color': color, 'rough': rough, 'sss': sss if sss is not None else 0.0, 'alpha': alpha if alpha is not None else 1.0}
        return b


# ------------------------------------------------------------------ baking (same-mesh, procedural source)
def uv_unwrap(ob, angle=66, margin=.002, hidden_scale=.45):
    me = ob.data
    for l in list(me.uv_layers): me.uv_layers.remove(l)
    me.uv_layers.new(name='UVMap'); activate(ob)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=.3, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.seams_from_islands(); bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    if 'hid' in me.attributes and hidden_scale < 1:
        from bpy_extras import mesh_utils
        hid = np.zeros(len(me.polygons), bool); me.attributes['hid'].data.foreach_get('value', hid)
        uv = me.uv_layers.active.data
        for isl in mesh_utils.mesh_linked_uv_islands(me):
            if sum(hid[i] for i in isl) * 2 > len(isl):
                li = [l for p in isl for l in me.polygons[p].loop_indices]
                c = sum((uv[l].uv for l in li), Vector((0, 0))) / len(li)
                for l in li: uv[l].uv = c + (uv[l].uv - c) * hidden_scale
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale() if hidden_scale >= 1 else None
    try: bpy.ops.uv.pack_islands(rotate=True, margin=margin, shape_method='CONCAVE', rotate_method='ANY', margin_method='FRACTION')
    except Exception as ex: log('concave pack failed', ex); bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    # faces the unwrap collapsed to (almost) no UV area would bake as black patches: re-project them and repack
    uvd = me.uv_layers.active.data; rat = []
    for p in me.polygons:
        l = [uvd[i].uv for i in p.loop_indices]; ua = abs(sum(l[i].x * l[(i + 1) % len(l)].y - l[(i + 1) % len(l)].x * l[i].y for i in range(len(l)))) * .5
        rat.append(ua / max(p.area, 1e-12))
    med = float(np.median(rat)); bad = [i for i, r in enumerate(rat) if r < med * .08]
    if bad and len(bad) < len(rat) * .5:
        log('UV: re-projecting collapsed faces', len(bad))
        for p in me.polygons: p.select = False
        for i in bad: me.polygons[i].select = True
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, scale_to_bounds=False)
        bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.average_islands_scale()
        try: bpy.ops.uv.pack_islands(rotate=True, margin=margin, shape_method='CONCAVE', rotate_method='ANY', margin_method='FRACTION')
        except Exception: bpy.ops.uv.pack_islands(rotate=True, margin=margin)
        bpy.ops.object.mode_set(mode='OBJECT')
    from dinkasset.validate import uv_stats
    st = uv_stats(me); log('UV', ob.name, st); return st


def _img(name, n, linear, fl=False):
    if name in bpy.data.images: bpy.data.images.remove(bpy.data.images[name])
    im = bpy.data.images.new(name, width=n, height=n, alpha=False, float_buffer=fl); im.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'; return im


def _px(im):
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a); return a.reshape(im.size[1], im.size[0], 4)


def bake_set(ob, texdir, prefix, res=2048, ao_samples=24, extra=(), margin=8, source=None, cage=.012, maxray=.03, bc_only=False, shared_prefix=None):
    """Bake procedural materials of `ob` to <prefix>_BC/N/ORM (+ _SSS when 'sss' in extra, alpha into BC when 'alpha' in extra)."""
    texdir = Path(texdir); texdir.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; use_hip_gpu(sc); sc.cycles.use_denoising = False
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.render.bake.use_selected_to_active = False; sc.render.bake.margin = margin; sc.render.bake.use_clear = True
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o is not ob and o is not source: o.hide_render = True
    activate(ob); kw = {}
    mats = [s.material for s in ob.material_slots]
    if source is not None:
        source.hide_render = False; source.hide_set(False); source.select_set(True); ob.hide_render = False
        kw = dict(use_selected_to_active=True, cage_extrusion=cage, max_ray_distance=maxray)
        mats = list({m.name: m for m in mats + [s.material for s in source.material_slots]}.values())
    def target(im):
        for m in mats:
            nt = m.node_tree; n = nt.nodes.get('PR_BAKE') or nt.nodes.new('ShaderNodeTexImage'); n.name = 'PR_BAKE'; n.image = im
            for x in nt.nodes: x.select = False
            n.select = True; nt.nodes.active = n
    def emit(key):
        for m in mats:
            nt = m.node_tree; em = nt.nodes['PR_EMIT']; out = nt.nodes['PR_OUT']
            for l in list(em.inputs[0].links): nt.links.remove(l)
            src = BAKE[m.name][key]
            if hasattr(src, 'is_linked') or hasattr(src, 'bl_idname'): nt.links.new(src, em.inputs[0])
            else: em.inputs[0].default_value = (src, src, src, 1) if isinstance(src, (int, float)) else (*src, 1)[:4]
            nt.links.new(em.outputs[0], out.inputs[0])
    def surface():
        for m in mats:
            nt = m.node_tree; nt.links.new(nt.nodes['PR_BSDF'].outputs[0], nt.nodes['PR_OUT'].inputs[0])
    res_px = {}
    def run(name, kind, linear, key=None, samples=1):
        im = _img(name, res, linear, name == 'pos'); target(im); sc.cycles.samples = samples
        if kind == 'EMIT': emit(key)
        else: surface()
        bpy.ops.object.bake(type=kind, margin=margin, use_clear=True, **kw) if kind != 'NORMAL' else bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=margin, use_clear=True, **kw)
        res_px[name] = _px(im).copy(); log('baked', name); return im
    bc = run('bc', 'EMIT', False, 'color')
    if bc_only:
        c = res_px['bc'].copy(); c[..., 3] = 1
        if 'alpha' in extra: run('alpha', 'EMIT', True, 'alpha', samples=4); c[..., 3] = res_px['alpha'][..., 0]
        surface(); im = bpy.data.images.new(prefix + '_BC_o', res, res, alpha='alpha' in extra); im.pixels.foreach_set(np.ascontiguousarray(c, np.float32).ravel())
        p = texdir / (prefix + '_BC.png'); im.filepath_raw = str(p); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
        out = {'BC': p}
        for k in ('N', 'ORM', 'SSS'):
            q = texdir / ('%s_%s.png' % (shared_prefix, k))
            if q.exists(): out[k] = q
        return out
    run('rough', 'EMIT', True, 'rough')
    nim = run('nrm', 'NORMAL', True, samples=6)
    run('ao', 'AO', True, samples=ao_samples)
    if 'sss' in extra: run('sss', 'EMIT', True, 'sss')
    if 'alpha' in extra: run('alpha', 'EMIT', True, 'alpha', samples=4)
    if 'pos' in extra: run('pos', 'EMIT', True, 'pos')
    surface()
    def save(arr, name, linear):
        im = bpy.data.images.new(name + '_o', res, res, alpha=arr.shape[2] == 4 and bool((arr[..., 3] < .999).any()))
        im.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'
        im.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel()); p = texdir / (name + '.png'); im.filepath_raw = str(p); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im); return p
    out = {}
    c = res_px['bc'].copy()
    if 'alpha' in extra: c[..., 3] = res_px['alpha'][..., 0]
    else: c[..., 3] = 1
    out['BC'] = save(c, prefix + '_BC', False)
    n = res_px['nrm'].copy(); n[..., 3] = 1; out['N'] = save(n, prefix + '_N', True)
    orm = np.ones_like(c); orm[..., 0] = np.clip(res_px['ao'][..., 0], 0, 1); orm[..., 1] = np.clip(res_px['rough'][..., 0], 0, 1); orm[..., 2] = 0
    out['ORM'] = save(orm, prefix + '_ORM', True)
    if 'sss' in extra:
        s = res_px['sss'].copy(); s[..., 3] = 1; out['SSS'] = save(s, prefix + '_SSS', True)
    if 'pos' in extra: out['_pos'] = res_px['pos']
    return out


BAKE = {}   # material name -> NT.bake dict (python side registry, valid within the building process)


def game_material(name, tex, sss=False, alpha=False, sss_radius=(.012, .005, .003), sss_scale=.35):
    """Runtime-equivalent material reading the baked set (what Unreal will show)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    b = nt.nodes.new('ShaderNodeBsdfPrincipled'); o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(b.outputs[0], o.inputs[0])
    def im(p, linear):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(str(p), check_existing=True); n.image.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'; return n
    bc = im(tex['BC'], False); nt.links.new(bc.outputs[0], b.inputs['Base Color'])
    orm = im(tex['ORM'], True); sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs[0], sp.inputs[0]); nt.links.new(sp.outputs[1], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(im(tex['N'], True).outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    if sss and 'SSS' in tex:
        s = im(tex['SSS'], True); mu = nt.nodes.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 1.0
        nt.links.new(s.outputs[0], mu.inputs[0]); nt.links.new(mu.outputs[0], b.inputs['Subsurface Weight']); b.inputs['Subsurface Radius'].default_value = sss_radius; b.inputs['Subsurface Scale'].default_value = sss_scale
    if alpha:
        nt.links.new(bc.outputs['Alpha'], b.inputs['Alpha'])
        try: m.surface_render_method = 'DITHERED'
        except Exception: pass
    return m


# ------------------------------------------------------------------ review rendering
def setup_review(samples=48, res=(1200, 900), ground='dirt', sun_elev=40, sun_az=200, ground_scale=2.2, strength=.09):
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; use_hip_gpu(sc); sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = .03; sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100; sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.render.image_settings.file_format = 'PNG'; sc.render.film_transparent = False
    w = bpy.data.worlds.new('CR_Sky'); w.use_nodes = True; sc.world = w; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground'); sky = nt.nodes.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
        try: sky.sky_type = t; break
        except Exception: pass
    sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_az)
    try: sky.sun_size = math.radians(2.0)
    except Exception: pass
    bg.inputs[1].default_value = strength; nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    for o in [o for o in bpy.data.objects if o.name.startswith('CR_')]: bpy.data.objects.remove(o)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0)); g = bpy.context.object; g.name = 'CR_Ground'
    for c in list(g.users_collection): c.objects.unlink(g)
    sc.collection.objects.link(g)
    m = bpy.data.materials.new('CR_GroundMat'); m.use_nodes = True; n = m.node_tree; b = n.nodes['Principled BSDF']
    d = THIRD / 'polyhaven' / ground
    tc = n.nodes.new('ShaderNodeTexCoord'); mp = n.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (40 / ground_scale,) * 3; mp.inputs['Rotation'].default_value = (0, 0, .6); n.links.new(tc.outputs['UV'], mp.inputs[0])
    def im(suffix, linear):
        x = n.nodes.new('ShaderNodeTexImage'); x.image = bpy.data.images.load(str(d / (ground + suffix)), check_existing=True); x.image.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'; n.links.new(mp.outputs[0], x.inputs[0]); return x
    try:
        n.links.new(im('_diff_2k.jpg', False).outputs[0], b.inputs['Base Color'])
        arm = im('_arm_2k.jpg', True); s = n.nodes.new('ShaderNodeSeparateColor'); n.links.new(arm.outputs[0], s.inputs[0]); n.links.new(s.outputs[1], b.inputs['Roughness'])
        nm = n.nodes.new('ShaderNodeNormalMap'); n.links.new(im('_nor_gl_2k.jpg', True).outputs[0], nm.inputs['Color']); n.links.new(nm.outputs[0], b.inputs['Normal'])
    except Exception as ex:
        log('ground scan missing', ex); b.inputs['Base Color'].default_value = (.12, .09, .06, 1); b.inputs['Roughness'].default_value = .95
    g.data.materials.append(m)
    cd = bpy.data.cameras.new('CR_Cam'); c = bpy.data.objects.new('CR_Cam', cd); sc.collection.objects.link(c); sc.camera = c
    return sc


def shoot(path, loc, target, lens=70, res=None, samples=None, exposure=0.0):
    sc = bpy.context.scene; c = sc.camera; c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); c.data.lens = lens; c.data.clip_start = .01
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    if samples: sc.cycles.samples = samples
    sc.view_settings.exposure = exposure
    sc.render.filepath = str(path); bpy.ops.render.render(write_still=True); log('rendered', path)


def game_cam(target, dist=6.0, az=-55, elev=45):
    t = Vector(target); a = math.radians(az); e = math.radians(elev)
    return (t.x + dist * math.cos(e) * math.cos(a), t.y + dist * math.cos(e) * math.sin(a), t.z + dist * math.sin(e))


def set_action(arm, name, frame_no):
    sc = bpy.context.scene; arm.data.pose_position = 'POSE'
    if name is None:
        if arm.animation_data: arm.animation_data.action = None
        for b in arm.pose.bones: b.matrix_basis = Matrix.Identity(4)
        return
    arm.animation_data_create(); act = bpy.data.actions[name]; arm.animation_data.action = act
    try:
        if arm.animation_data.action_slot is None and act.slots: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    sc.frame_set(frame_no); bpy.context.view_layer.update()


def montage(files, out, cols=2, width=None):
    from PIL import Image
    ims = [Image.open(f).convert('RGB') for f in files]; w = max(i.width for i in ims); h = max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols; sh = Image.new('RGB', (w * cols, h * rows), (20, 20, 20))
    for k, i in enumerate(ims): sh.paste(i, ((k % cols) * w, (k // cols) * h))
    if width: sh.thumbnail((width, 100000))
    sh.save(out)


# ------------------------------------------------------------------ LODs, validation, export
def clean_mesh(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bad = [f for f in bm.faces if f.calc_area() < 1e-9]
    if bad: bmesh.ops.delete(bm, geom=bad, context='FACES_ONLY')
    wire = [e for e in bm.edges if not e.link_faces]
    if wire: bmesh.ops.delete(bm, geom=wire, context='EDGES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose: bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data); bm.free(); ob.data.update()


def limit_weights(ob, n=4):
    for v in ob.data.vertices:
        ws = sorted([(g.group, g.weight) for g in v.groups if g.weight > 1e-6], key=lambda x: -x[1])[:n]; t = sum(w for _, w in ws)
        if t <= 0: raise RuntimeError('unweighted vertex in ' + ob.name)
        for g in ob.vertex_groups: g.remove([v.index])
        for g, w in ws: ob.vertex_groups[g].add([v.index], w / t, 'REPLACE')


def tri_count(ob): return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def export_skeletal(coll_name, arm, exportdir, actions, anim_prefix, fps, validate_out=None):
    """Mirror of the repo's creature exporters: metres source, temporary x100 cm export scene, FBX_SCALE_ALL,
    one FBX per LOD plus one armature-only FBX per action. Call LAST: it mutates the scene (do not save after)."""
    from dinkasset import common, validate, export_ue
    exportdir = Path(exportdir); exportdir.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene; coll = bpy.data.collections[coll_name]; asset = common.Asset(coll)
    arm.animation_data_create(); arm.animation_data.action = None; arm.data.pose_position = 'REST'; sc.frame_set(1)
    verdict = None
    try:
        verdict = validate.validate_scene(only=[coll_name])
        if validate_out: Path(validate_out).write_text(json.dumps(verdict, indent=2) + '\n')
        for e in verdict['assets']:
            for f in e['findings']:
                if f['severity'] in ('error', 'warning'): log('VALIDATE', f['severity'], f['code'], f['message'])
    except Exception as ex: log('validate failed to run', ex)
    lods = sorted([o for o in coll.objects if o.type == 'MESH' and '_LOD' in o.name], key=lambda o: o.name)
    for m in lods:
        for v in m.data.vertices: v.co *= 100
    activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    for b in arm.data.edit_bones: b.head *= 100; b.tail *= 100
    bpy.ops.object.mode_set(mode='OBJECT'); sc.unit_settings.scale_length = .01
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for cu in bag.fcurves:
                            if cu.data_path.endswith('.location'):
                                for k in cu.keyframe_points: k.co.y *= 100; k.handle_left.y *= 100; k.handle_right.y *= 100
    for material in bpy.data.materials:
        if material.node_tree: material.node_tree.nodes.clear()
    files = []
    for m in lods:
        proxy = type('ExportAsset', (), {'renders': [m], 'collision': [], 'armatures': [arm], 'sockets': []})()
        p = exportdir / (m.name + '.fbx')
        with export_ue.unhidden([m, arm]): export_ue.export_fbx(proxy, str(p), 'all', 'Armature')
        files.append(p.name)
    arm.data.pose_position = 'POSE'
    for key, act in actions.items():
        a = bpy.data.actions[act]; arm.animation_data.action = a
        try:
            if arm.animation_data.action_slot is None and a.slots: arm.animation_data.action_slot = a.slots[0]
        except Exception: pass
        sc.frame_start = int(a.frame_range[0]); sc.frame_end = int(a.frame_range[1]); sc.render.fps = fps; sc.frame_set(sc.frame_start)
        activate(arm); p = exportdir / ('%s_%s.fbx' % (anim_prefix, key))
        bpy.ops.export_scene.fbx(filepath=str(p), use_selection=True, object_types={'ARMATURE'}, apply_unit_scale=True, global_scale=1, apply_scale_options='FBX_SCALE_ALL', axis_forward='Y', axis_up='Z', bake_space_transform=False, use_space_transform=True, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False, armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0, path_mode='STRIP', embed_textures=False, use_custom_props=False)
        files.append(p.name)
    log('exported', files); return files, verdict


# ------------------------------------------------------------------ numpy mesh access
def co_np(me):
    a = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', a); return a.reshape(-1, 3).astype(np.float64)
def set_co(me, a):
    me.vertices.foreach_set('co', np.asarray(a, np.float32).ravel()); me.update()
def nrm_np(me):
    a = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('normal', a); return a.reshape(-1, 3).astype(np.float64)
def gauss(d, r): return np.exp(-(d / r) ** 2)
def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def set_color_attr(me, name, arr):
    if name in me.color_attributes: me.color_attributes.remove(me.color_attributes[name])
    a = me.color_attributes.new(name, 'FLOAT_COLOR', 'POINT'); a.data.foreach_set('color', np.asarray(arr, np.float32).ravel())
def get_color_attr(me, name):
    a = np.empty(len(me.vertices) * 4, np.float32); me.color_attributes[name].data.foreach_get('color', a); return a.reshape(-1, 4)
def mesh_obj(name, vs, fs, coll=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in vs], [], [tuple(f) for f in fs]); me.update()
    o = bpy.data.objects.new(name, me); (coll or bpy.context.scene.collection).objects.link(o)
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(me); bm.free(); return o
def join(objs, name):
    bpy.context.view_layer.update()
    for x in bpy.context.view_layer.objects:
        if x is not None: x.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); o = bpy.context.view_layer.objects.active; o.name = name; o.data.name = name; return o
def apply_mod(o, kind, **kw):
    m = o.modifiers.new(kind, kind)
    for k, v in kw.items(): setattr(m, k, v)
    activate(o); bpy.ops.object.modifier_apply(modifier=m.name)
def loft(stations, n=32, cap=True):
    """stations: list of (center Vector, axis_u Vector*radius, axis_v Vector*radius_up, axis_v*radius_down or None, exponent). Closed superellipse loft."""
    vs = []; fs = []
    for (c, U, Vu, Vd, e) in stations:
        c = Vector(c); U = Vector(U); Vu = Vector(Vu); Vd = Vector(Vd) if Vd is not None else Vu
        for j in range(n):
            a = math.tau * j / n; cu = math.cos(a); su = math.sin(a)
            x = math.copysign(abs(cu) ** (2 / e), cu); y = math.copysign(abs(su) ** (2 / e), su)
            vs.append(c + U * x + (Vu if su >= 0 else Vd) * y)
    m = len(stations)
    for i in range(m - 1):
        for j in range(n):
            a = i * n + j; b = i * n + (j + 1) % n; fs.append((a, b, b + n, a + n))
    if cap:
        vs.append(Vector(stations[0][0])); c0 = len(vs) - 1; vs.append(Vector(stations[-1][0])); c1 = len(vs) - 1; o = (m - 1) * n
        fs += [(c0, (j + 1) % n, j) for j in range(n)] + [(c1, o + j, o + (j + 1) % n) for j in range(n)]
    return vs, fs
def auto_weights(ob, arm):
    bpy.context.view_layer.update()
    for x in bpy.context.view_layer.objects:
        if x is not None: x.select_set(False)
    ob.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    un = sum(1 for v in ob.data.vertices if not any(g.weight > 1e-5 for g in v.groups)); log('auto weights; unweighted', un); return un
def set_rigid(ob, idx, weights):
    """weights: {bone: w}; replaces all weights for vertex indices idx."""
    idx = [int(i) for i in idx]
    for g in ob.vertex_groups: g.remove(idx)
    for k, w in weights.items():
        g = ob.vertex_groups.get(k) or ob.vertex_groups.new(name=k); g.add(idx, w, 'REPLACE')
def decimate_to(ob, tris):
    r = tris / max(1, tri_count(ob)); 
    if r < 1: apply_mod(ob, 'DECIMATE', ratio=r, use_collapse_triangulate=True)


def fill_unbaked(tex, pos, keys=('BC', 'N', 'ORM', 'SSS'), iters=48):
    """Texels the selected-to-active bake left empty (ray found no source surface; position map is exactly zero there) are filled from neighbours."""
    from PIL import Image as _I
    ok = (np.abs(pos[::-1, :, :3]).sum(-1) > 1e-6); imgs = {k: np.asarray(_I.open(tex[k]).convert('RGB'), dtype=np.float64) / 255.0 for k in keys if k in tex}
    m = ok.astype(np.float64)
    for _ in range(iters):
        cnt_ = np.zeros_like(m); acc = {k: np.zeros_like(v) for k, v in imgs.items()}
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            rm = np.roll(m, (dy, dx), (0, 1)); cnt_ += rm
            for k, v in imgs.items(): acc[k] += np.roll(v * m[..., None], (dy, dx), (0, 1))
        fill = (m == 0) & (cnt_ > 0)
        if not fill.any(): break
        for k, v in imgs.items(): v[fill] = acc[k][fill] / cnt_[fill][:, None]
        m = np.maximum(m, fill)
    for k, v in imgs.items(): _I.fromarray((np.clip(v, 0, 1) * 255 + .5).astype(np.uint8)).save(tex[k])
    log('fill_unbaked: empty texels', int((~ok).sum()))
