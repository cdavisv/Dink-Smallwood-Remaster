"""Shared pipeline for the unclaimed-family photoreal sources (Blender 5.2 batch, Cycles on HIP).

One build script per asset group imports this module. It gives: an empty metric scene, mesh helpers, a small
shader-node builder for procedural high-detail materials, CC0 scan loading (box projected), the high -> game-mesh
bake (BC / N OpenGL / ORM, optional alpha in BC and E), the sun-and-sky review renders, LODs, UCX hull, the FBX
export of tools/blender/CONVENTIONS.md, validation numbers and manifest.json.
"""
import bpy, bmesh, math, os, sys, json, time
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
UNC = os.path.dirname(HERE)                         # .../PhotorealPass/Unclaimed
PP = os.path.dirname(UNC)                           # .../PhotorealPass
TP = os.path.join(PP, 'ThirdParty')
REPO = os.path.abspath(os.path.join(PP, '..', '..', '..', '..'))
REVIEW = os.environ.get('DINK_REVIEW') or os.path.join(UNC, '_review')     # scratch renders (git-ignored)

BUDGET = {'prop_small': (1500, 5000), 'prop': (6000, 20000), 'prop_large': (20000, 60000), 'weapon': (3000, 8000),
          'kit_piece': (3000, 10000), 'door': (4000, 12000), 'building': (60000, 200000), 'foliage': (8000, 25000),
          'character_humanoid': (20000, 35000), 'creature_quadruped': (15000, 30000), 'creature': (25000, 60000)}
LOD_RATIOS = {'creature': (0.5, 0.25), 'creature_quadruped': (0.5, 0.25), 'character_humanoid': (0.5, 0.25, 0.12), 'foliage': (0.5, 0.25)}


def rel(p):
    return os.path.relpath(p, REPO).replace(os.sep, '/')


def args():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return a


# ------------------------------------------------------------------ scene
def use_hip_gpu(scene=None):
    """Render/bake on the RX 6800 via HIP; preferences change in memory only. DINK_CPU=1 forces the CPU."""
    scene = scene or bpy.context.scene; scene.render.engine = 'CYCLES'; found = False
    if not os.environ.get('DINK_CPU'):
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'HIP'; prefs.refresh_devices()
            for d in prefs.devices:
                d.use = (d.type == 'HIP' and 'Radeon RX 6800' in d.name); found |= d.use
        except Exception as e:
            print('HIP not available:', e); found = False
    scene.cycles.device = 'GPU' if found else 'CPU'
    print('Cycles device:', scene.cycles.device); return found


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
    use_hip_gpu(sc); sc.render.threads_mode = 'FIXED'; sc.render.threads = 4
    return sc


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(ob, c=None):
    for k in list(ob.users_collection):
        k.objects.unlink(ob)
    (c or bpy.context.scene.collection).objects.link(ob); return ob


def activate(ob, others=()):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in others:
        o.select_set(True)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob


# ------------------------------------------------------------------ mesh helpers
def new_obj(name, V, F, c=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(f) for f in F]); me.update()
    ob = bpy.data.objects.new(name, me); link(ob, c)
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    return ob


def bm_obj(name, bm, c=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); ob = bpy.data.objects.new(name, me); link(ob, c)
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    return ob


def lathe(name, profile, seg=32, c=None, cap0=True, cap1=True):
    """revolve (r, z) profile about Z; closes onto the axis where r == 0"""
    V = []; F = []; rings = []
    for (r, z) in profile:
        if r <= 1e-9:
            rings.append([len(V)]); V.append((0, 0, z))
        else:
            rings.append(list(range(len(V), len(V) + seg))); V += [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z) for i in range(seg)]
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                F.append((a[0], b[j], b[i]))
            elif len(b) == 1:
                F.append((a[i], a[j], b[0]))
            else:
                F.append((a[i], a[j], b[j], b[i]))
    if cap0 and len(rings[0]) > 1:
        F.append(tuple(reversed(rings[0])))
    if cap1 and len(rings[-1]) > 1:
        F.append(tuple(rings[-1]))
    ob = new_obj(name, V, F, c); fix_normals(ob); return ob


def tube(name, pts, rad, sides=10, c=None, caps=True):
    """swept tube along pts with per-point radius (parallel transport frame)"""
    P = np.array(pts, float); n = len(P); R = np.full(n, rad, float) if np.isscalar(rad) else np.array(rad, float)
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None] + 1e-12
    u = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N = u - T[0] * (u @ T[0]); N /= np.linalg.norm(N); V = []; F = []
    for i in range(n):
        if i:
            N = N - T[i] * (N @ T[i]); N /= np.linalg.norm(N) + 1e-12
        B = np.cross(T[i], N)
        for k in range(sides):
            a = 2 * math.pi * k / sides; V.append(P[i] + R[i] * (math.cos(a) * N + math.sin(a) * B))
    for i in range(n - 1):
        for k in range(sides):
            k1 = (k + 1) % sides; F.append((i * sides + k, i * sides + k1, (i + 1) * sides + k1, (i + 1) * sides + k))
    if caps:
        F.append(tuple(reversed(range(sides)))); F.append(tuple(range((n - 1) * sides, n * sides)))
    ob = new_obj(name, V, F, c); fix_normals(ob); return ob


def fix_normals(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free(); ob.data.update()


def mod(ob, typ, name=None, **kw):
    m = ob.modifiers.new(name or typ, typ)
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data; ob.modifiers.clear(); ob.data = me; me.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def subsurf(ob, lv, apply=True):
    mod(ob, 'SUBSURF', levels=lv, render_levels=lv)
    return apply_mods(ob) if apply else ob


def dup(ob, name, c=None):
    o = ob.copy(); o.data = ob.data.copy(); o.name = name; o.data.name = name; link(o, c or ob.users_collection[0]); return o


def join(obs, name):
    obs = [o for o in obs if o]
    activate(obs[0], obs[1:]); bpy.ops.object.join(); o = bpy.context.view_layer.objects.active; o.name = name; o.data.name = name; return o


def apply_xf(ob):
    activate(ob); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); return ob


def co(ob):
    n = len(ob.data.vertices); P = np.zeros(n * 3, np.float32); ob.data.vertices.foreach_get('co', P); return P.reshape(n, 3).astype(np.float64)


def set_co(ob, P):
    ob.data.vertices.foreach_set('co', np.asarray(P, np.float32).ravel()); ob.data.update()


def vnormals(ob):
    n = len(ob.data.vertices); N = np.zeros(n * 3, np.float32); ob.data.vertices.foreach_get('normal', N); return N.reshape(n, 3).astype(np.float64)


def tex_displace(ob, kind='CLOUDS', strength=0.01, scale=0.1, depth=4, name=None, mid=0.5, vg=None, coords='LOCAL', **texkw):
    """Displace modifier driven by a legacy procedural texture (works in batch, evaluated on the CPU)"""
    t = bpy.data.textures.new(name or ('d_' + kind), kind)
    if hasattr(t, 'noise_scale'):
        t.noise_scale = scale
    if hasattr(t, 'noise_depth'):
        t.noise_depth = depth
    for k, v in texkw.items():
        setattr(t, k, v)
    m = mod(ob, 'DISPLACE', texture=t, strength=strength, mid_level=mid, texture_coords=coords)
    if vg:
        m.vertex_group = vg
    return m


def pivot_base_center(ob):
    """origin at bbox centre in X/Y and the mesh bottom in Z; transforms applied"""
    apply_xf(ob); P = co(ob); c = (P.min(0) + P.max(0)) / 2; c[2] = P[:, 2].min(); set_co(ob, P - c); return ob


def tri_count(ob):
    ob.data.calc_loop_triangles(); return len(ob.data.loop_triangles)


def mesh_stats(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    nonman = sum(1 for e in bm.edges if not e.is_manifold); open_e = sum(1 for e in bm.edges if e.is_boundary)
    loose = sum(1 for v in bm.verts if not v.link_faces); zero = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    vol = bm.calc_volume(signed=True) if open_e == 0 else None
    bm.free(); P = co(ob)
    uv = ob.data.uv_layers.active; uvo = None
    if uv:
        U = np.zeros(len(ob.data.loops) * 2, np.float32); uv.data.foreach_get('uv', U); uvo = [round(float(U.min()), 4), round(float(U.max()), 4)]
    return {'triangles': tri_count(ob), 'vertices': len(ob.data.vertices), 'non_manifold_edges': nonman, 'open_edges': open_e, 'loose_verts': loose,
            'zero_area_faces': zero, 'signed_volume_positive': (vol is None or vol > 0), 'uv_range': uvo,
            'bounds_min_m': [round(float(v), 4) for v in P.min(0)], 'bounds_max_m': [round(float(v), 4) for v in P.max(0)],
            'dimensions_m': [round(float(v), 4) for v in (P.max(0) - P.min(0))],
            'transforms_applied': bool(np.allclose(ob.matrix_world, np.eye(4), atol=1e-6))}


def smart_uv(ob, angle=66, margin=0.012):
    activate(ob); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT'); return ob


def seam_uv(ob, seam_fn, margin=0.012, method='ANGLE_BASED'):
    """unwrap with seams marked where seam_fn(edge_mid_co, v0_co, v1_co) is true, then pack"""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for e in bm.edges:
        a, b = e.verts[0].co, e.verts[1].co; e.seam = bool(seam_fn((a + b) / 2, a, b))
    bm.to_mesh(ob.data); bm.free()
    activate(ob); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method=method, margin=margin); bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT'); return ob


def decimate(ob, ratio=None, tris=None, name=None):
    o = dup(ob, name or ob.name + '_dec')
    if tris:
        ratio = min(1.0, tris / max(1, tri_count(o)))
    mod(o, 'DECIMATE', ratio=ratio, use_collapse_triangulate=True); apply_mods(o); return o


def make_lods(lo, ratios):
    out = []
    for i, r in enumerate(ratios):
        o = decimate(lo, ratio=r, name=lo.name.replace('_LOD0', '') + '_LOD%d' % (i + 1)); out.append(o)
    return out


def _hull(points):
    """closed convex hull mesh (bmesh) of a point set"""
    bm = bmesh.new()
    for p in points:
        bm.verts.new(tuple(p))
    r = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    junk = [e for e in r.get('geom_interior', []) + r.get('geom_unused', []) if isinstance(e, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(bm, geom=list(set(junk)), context='VERTS')
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.6), verts=bm.verts, edges=bm.edges)          # coplanar triangles become one planar face
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm


def make_ucx(lo, maxv=26):
    """one convex collision hull of the game mesh, at most maxv vertices: hull, thin it out by clustering its vertices, hull again"""
    P = co(lo); bm = _hull(P); H = np.array([v.co[:] for v in bm.verts]); bm.free(); cell = float(np.linalg.norm(P.max(0) - P.min(0))) / 14
    for _ in range(12):
        if len(H) <= maxv:
            break
        key = np.round(H / cell).astype(int); _, idx = np.unique(key, axis=0, return_index=True); bm = _hull(H[np.sort(idx)]); H = np.array([v.co[:] for v in bm.verts]); bm.free(); cell *= 1.25
    c0 = P.mean(0)                                                   # clustering can pull the hull in a little: push it back out so it still contains the mesh
    bm = _hull(H); H = np.array([v.co[:] for v in bm.verts]); k = 1.0
    ob = bm_obj('UCX_%s_01' % lo.name, bm, lo.users_collection[0], smooth=False); ob.display_type = 'WIRE'; ob.hide_render = True; return ob


# ------------------------------------------------------------------ numpy noise (shape decisions shared by the source and the game mesh)
def _hash(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 974711) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(P, seed=0, freq=1.0):
    """value noise -1..1 at points P (n, 3)"""
    P = np.asarray(P, float).reshape(-1, 3) * freq; i = np.floor(P).astype(np.int64); f = P - i; f = f * f * (3 - 2 * f); out = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out * 2 - 1


def fbm(P, seed=0, freq=1.0, octaves=4, gain=0.5):
    a = 1.0; s = np.zeros(len(np.asarray(P).reshape(-1, 3))); tot = 0.0
    for o in range(octaves):
        s += a * vnoise(P, seed + o * 17, freq * 2 ** o); tot += a; a *= gain
    return s / tot


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def grid_surface(name, fn, nu, nv, c=None, closed_u=True, pole0=False, pole1=False, flip=False):
    """parametric surface fn(U, V) -> (n, 3) sampled on nu x nv; closed_u wraps u; pole0/pole1 collapse the v = 0 / v = 1 row to one vertex.
    UVs are per loop: u = i / nu, v = j / (nv - 1), so a closed surface gets one clean seam and no duplicated vertices."""
    us = np.arange(nu) / (nu if closed_u else nu - 1); vs = np.arange(nv) / (nv - 1)
    U, V = np.meshgrid(us, vs); P = np.asarray(fn(U.ravel(), V.ravel()), float).reshape(nv, nu, 3)
    verts = []; idx = np.zeros((nv, nu), int)
    for j in range(nv):
        if (j == 0 and pole0) or (j == nv - 1 and pole1):
            idx[j, :] = len(verts); verts.append(P[j].mean(0))
        else:
            idx[j, :] = np.arange(len(verts), len(verts) + nu); verts += list(P[j])
    faces = []; fuv = []; ncol = nu if closed_u else nu - 1
    for j in range(nv - 1):
        for i in range(ncol):
            i1 = (i + 1) % nu; u0 = i / ncol; u1 = (i + 1) / ncol; v0 = vs[j]; v1 = vs[j + 1]
            q = [idx[j, i], idx[j, i1], idx[j + 1, i1], idx[j + 1, i]]; uvq = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            if j == 0 and pole0:
                q = [q[0], q[2], q[3]]; uvq = [((u0 + u1) / 2, v0), uvq[2], uvq[3]]
            elif j == nv - 2 and pole1:
                q = [q[0], q[1], q[2]]; uvq = [uvq[0], uvq[1], ((u0 + u1) / 2, v1)]
            if flip:
                q = q[::-1]; uvq = uvq[::-1]
            faces.append(q); fuv.append(uvq)
    ob = new_obj(name, verts, faces, c); uv = ob.data.uv_layers.new(name='UVMap'); k = 0
    for f, uvq in zip(ob.data.polygons, fuv):
        for li, t in zip(f.loop_indices, uvq):
            uv.data[li].uv = t
    return ob


def cr_spline(pts, n=240):
    """Catmull-Rom through pts (k, d) -> dense (n, d)"""
    P = np.array(pts, float); Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []; k = len(P) - 1; per = max(2, n // k)
    for i in range(k):
        p0, p1, p2, p3 = Q[i], Q[i + 1], Q[i + 2], Q[i + 3]; t = np.linspace(0, 1, per, endpoint=(i == k - 1))[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.vstack(out)


def curve_fn(pts):
    """arc-length parametrised smooth curve through pts: f(v in 0..1) -> (n, d)"""
    D = cr_spline(pts); s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(D, axis=0), axis=1))]; s /= s[-1]
    return lambda v: np.stack([np.interp(v, s, D[:, k]) for k in range(D.shape[1])], -1)


def sweep(name, rows, nu=12, nv=24, c=None, up=(0, 0, 1), cap=0.55):
    """swept solid: rows = [(x, y, z, a, b, n)] centre, half-width a (across), half-height b (along `up`), superellipse exponent n (2 round, 6 boxy).
    Smoothly interpolated along the path; both ends are closed with a slightly domed cap."""
    R = np.array(rows, float); f = curve_fn(R); upv = np.array(up, float)
    d0 = R[1, :3] - R[0, :3]; d1 = R[-1, :3] - R[-2, :3]

    def fn(U, V):
        # v 0..1 runs: cap in (0..e), body (e..1-e), cap out
        e = 1.5 / nv; t = np.clip((V - e) / (1 - 2 * e), 0, 1); q = f(t); P = q[:, :3]; a = q[:, 3]; b = q[:, 4]; n = np.maximum(q[:, 5], 1.2)
        k = np.where(V < e, V / e, np.where(V > 1 - e, (1 - V) / e, 1.0)); kk = np.sqrt(np.clip(1 - (1 - k) ** 2, 0, 1))          # quarter-round shrink into the cap
        T = f(np.clip(t + 1e-3, 0, 1))[:, :3] - f(np.clip(t - 1e-3, 0, 1))[:, :3]
        T /= np.linalg.norm(T, axis=1)[:, None] + 1e-12
        N = upv[None, :] - T * (T @ upv)[:, None]; N /= np.linalg.norm(N, axis=1)[:, None] + 1e-12; B = np.cross(T, N)
        th = 2 * np.pi * U; cu = np.cos(th); su = np.sin(th); ex = 2.0 / n
        x = np.sign(cu) * np.abs(cu) ** ex * a * (cap + (1 - cap) * kk) * np.where(k < 1e-6, 0, 1); y = np.sign(su) * np.abs(su) ** ex * b * (cap + (1 - cap) * kk) * np.where(k < 1e-6, 0, 1)
        bulge = (1 - kk) * np.minimum(a, b) * 0.25 * np.where(V < 0.5, -1, 1)
        return P + B * x[:, None] + N * y[:, None] + T * bulge[:, None]
    ob = grid_surface(name, fn, nu, nv, c, pole0=True, pole1=True); fix_normals(ob); return ob


def make_lo(hi_obs, tris, name, c=None, angle=66, margin=0.012, weld=0.0):
    """game mesh = decimated copy of the (joined) source, smart-unwrapped"""
    cps = []
    for o in hi_obs:
        d = dup(o, o.name + '_tmp', c); apply_mods(d); d.data.materials.clear(); cps.append(d)
    lo = join(cps, name) if len(cps) > 1 else cps[0]; lo.name = name; lo.data.name = name
    for l in list(lo.data.uv_layers):
        lo.data.uv_layers.remove(l)
    if tri_count(lo) > tris:
        mod(lo, 'DECIMATE', ratio=tris / tri_count(lo)); apply_mods(lo)
    if weld:
        mod(lo, 'WELD', merge_threshold=weld); apply_mods(lo)
    clean_mesh(lo); lo.data.polygons.foreach_set('use_smooth', [True] * len(lo.data.polygons)); fix_normals(lo); smart_uv(lo, angle=angle, margin=margin); pack_uv(lo, margin=margin)
    return lo



def remesh_lo(hi_obs, voxel, tris, name, c=None, angle=66, margin=0.012, smooth=2):
    """game mesh for a heap of many small solids: one closed skin over their union (voxel remesh), decimated and unwrapped"""
    cps = []
    for o in hi_obs:
        d = dup(o, o.name + '_tmp', c); apply_mods(d); d.data.materials.clear(); cps.append(d)
    lo = join(cps, name) if len(cps) > 1 else cps[0]; lo.name = name; lo.data.name = name
    for l in list(lo.data.uv_layers):
        lo.data.uv_layers.remove(l)
    mod(lo, 'REMESH', mode='VOXEL', voxel_size=voxel, adaptivity=0.0, use_smooth_shade=True); apply_mods(lo)
    if smooth:
        mod(lo, 'SMOOTH', factor=0.5, iterations=smooth); apply_mods(lo)
    if tri_count(lo) > tris:
        mod(lo, 'DECIMATE', ratio=tris / tri_count(lo)); apply_mods(lo)
    clean_mesh(lo); lo.data.polygons.foreach_set('use_smooth', [True] * len(lo.data.polygons)); fix_normals(lo); smart_uv(lo, angle=angle, margin=margin); pack_uv(lo, margin=margin)
    return lo


def icosphere(name, radius=1.0, sub=5, c=None, scale=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=radius, matrix=Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))); return bm_obj(name, bm, c)



def box(name, mn, mx, c=None, hi=False, bevel=0.003, warp=0.0, seed=0, rot=None):
    """board / block between two corners. Game mesh: 12 triangles. Dense source: bevelled edges, subdivided, optionally warped."""
    mn = np.array(mn, float); mx = np.array(mx, float); V = [(x, y, z) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
    F = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]; ob = new_obj(name, V, F, c, smooth=False); fix_normals(ob)
    if hi:
        mod(ob, 'BEVEL', width=min(bevel, float((mx - mn).min()) * 0.3), segments=3, limit_method='ANGLE'); apply_mods(ob)
        m = mod(ob, 'SUBSURF', levels=4, render_levels=4); m.subdivision_type = 'SIMPLE'; apply_mods(ob)
        if warp:
            P = co(ob); P = P + warp * np.stack([fbm(P, seed + k * 7, 2.0, 2) for k in range(3)], 1) + 0.15 * warp * np.stack([fbm(P, seed + 30 + k * 7, 40.0, 2) for k in range(3)], 1); set_co(ob, P)
        ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
    if rot is not None:                      # (axis, angle_rad, pivot)
        ax, ang, piv = rot; ob.matrix_world = Matrix.Translation(Vector(piv)) @ Matrix.Rotation(ang, 4, ax) @ Matrix.Translation(-Vector(piv)); apply_xf(ob)
    return ob



def clean_mesh(ob, dist=6e-5):
    """drop slivers, coincident vertices and anything left hanging by decimation or remeshing"""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for _ in range(3):
        bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
        bad = [f for f in bm.faces if f.calc_area() < 2e-8]
        if not bad:
            break
        bmesh.ops.delete(bm, geom=bad, context='FACES'); holes = [e for e in bm.edges if e.is_boundary]
        if holes:
            bmesh.ops.holes_fill(bm, edges=holes, sides=6)
    wire = [e for e in bm.edges if not e.link_faces]
    if wire:
        bmesh.ops.delete(bm, geom=wire, context='EDGES')
    loose = [v for v in bm.verts if not v.link_edges]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data); bm.free(); ob.data.update(); return ob


def pack_uv(ob, margin=0.012, average=True, rotate=True):
    activate(ob); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
    if average:
        bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=margin, rotate=rotate)
    bpy.ops.object.mode_set(mode='OBJECT'); return ob


def displace_np(ob, fn):
    """move vertices along their normals by fn(P) metres"""
    P = co(ob); N = vnormals(ob); set_co(ob, P + N * np.asarray(fn(P))[:, None]); return ob



# ------------------------------------------------------------------ shader nodes
class NT:
    """tiny node-graph builder: every method returns an output socket (or the node for multi-output nodes)"""

    def __init__(s, name):
        s.mat = bpy.data.materials.new(name); s.mat.use_nodes = True; s.nt = s.mat.node_tree; s.N = s.nt.nodes; s.L = s.nt.links
        s.bsdf = s.N['Principled BSDF']; s.out = s.N['Material Output']
        s._tc = s.N.new('ShaderNodeTexCoord'); s.obj = s._tc.outputs['Object']; s.uv = s._tc.outputs['UV']; s.gen = s._tc.outputs['Generated']
        s._geo = s.N.new('ShaderNodeNewGeometry'); s.pointiness = s._geo.outputs['Pointiness']; s.gnormal = s._geo.outputs['Normal']; s.pos = s._geo.outputs['Position']

    def node(s, typ, **kw):
        n = s.N.new(typ)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def _in(s, sock, v):
        if v is None:
            return
        if isinstance(v, bpy.types.NodeSocket):
            s.L.new(v, sock)
        else:
            try:
                sock.default_value = v
            except Exception:
                sock.default_value = (v, v, v, 1.0) if not hasattr(v, '__len__') else (tuple(v) + (1.0,))[:len(sock.default_value)]

    def val(s, v):
        n = s.node('ShaderNodeValue'); n.outputs[0].default_value = v; return n.outputs[0]

    def rgb(s, c):
        n = s.node('ShaderNodeRGB'); n.outputs[0].default_value = (c[0], c[1], c[2], 1.0); return n.outputs[0]

    def mapping(s, vec=None, scale=1.0, loc=(0, 0, 0), rot=(0, 0, 0)):
        n = s.node('ShaderNodeMapping'); s._in(n.inputs['Vector'], vec if vec is not None else s.obj)
        n.inputs['Scale'].default_value = (scale,) * 3 if np.isscalar(scale) else tuple(scale); n.inputs['Location'].default_value = loc; n.inputs['Rotation'].default_value = rot
        return n.outputs[0]

    def noise(s, scale=5.0, detail=6.0, rough=0.55, vec=None, distortion=0.0, lac=2.0, out='Fac', typ='FBM'):
        n = s.node('ShaderNodeTexNoise'); n.noise_dimensions = '3D'
        try:
            n.noise_type = typ
        except Exception:
            pass
        s._in(n.inputs['Vector'], vec if vec is not None else s.obj); s._in(n.inputs['Scale'], scale); s._in(n.inputs['Detail'], detail)
        s._in(n.inputs['Roughness'], rough); s._in(n.inputs['Lacunarity'], lac); s._in(n.inputs['Distortion'], distortion)
        return n.outputs[out]

    def voronoi(s, scale=5.0, vec=None, feature='F1', out='Distance', randomness=1.0, dist='EUCLIDEAN', smooth=None):
        n = s.node('ShaderNodeTexVoronoi'); n.feature = feature; n.distance = dist
        s._in(n.inputs['Vector'], vec if vec is not None else s.obj); s._in(n.inputs['Scale'], scale); s._in(n.inputs['Randomness'], randomness)
        if smooth is not None and 'Smoothness' in n.inputs:
            s._in(n.inputs['Smoothness'], smooth)
        return n.outputs[out]

    def wave(s, scale=5.0, vec=None, distortion=2.0, detail=3.0, dscale=1.0, typ='BANDS', direction='X', profile='SIN'):
        n = s.node('ShaderNodeTexWave'); n.wave_type = typ; n.wave_profile = profile
        if typ == 'BANDS':
            n.bands_direction = direction
        else:
            n.rings_direction = direction
        s._in(n.inputs['Vector'], vec if vec is not None else s.obj); s._in(n.inputs['Scale'], scale); s._in(n.inputs['Distortion'], distortion)
        s._in(n.inputs['Detail'], detail); s._in(n.inputs['Detail Scale'], dscale)
        return n.outputs['Fac']

    def ramp(s, fac, stops, interp='LINEAR'):
        """stops = [(pos, colour or grey), ...]"""
        n = s.node('ShaderNodeValToRGB'); cr = n.color_ramp; cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p; e.color = (c, c, c, 1.0) if np.isscalar(c) else (c[0], c[1], c[2], 1.0)
        s._in(n.inputs['Fac'], fac); return n.outputs['Color']

    def math(s, op, a, b=None, c=None, clamp=False):
        n = s.node('ShaderNodeMath', operation=op, use_clamp=clamp); s._in(n.inputs[0], a)
        if b is not None:
            s._in(n.inputs[1], b)
        if c is not None:
            s._in(n.inputs[2], c)
        return n.outputs[0]

    def mix(s, fac, a, b, blend='MIX', clamp=True):
        n = s.node('ShaderNodeMix', data_type='RGBA', blend_type=blend); n.clamp_result = clamp
        s._in(n.inputs['Factor'], fac); s._in(n.inputs['A'][0] if False else n.inputs[6], a); s._in(n.inputs[7], b); return n.outputs[2]

    def mixf(s, fac, a, b):
        n = s.node('ShaderNodeMix', data_type='FLOAT'); s._in(n.inputs[0], fac); s._in(n.inputs[2], a); s._in(n.inputs[3], b); return n.outputs[0]

    def maprange(s, v, a0=0.0, a1=1.0, b0=0.0, b1=1.0, clamp=True, interp='LINEAR'):
        n = s.node('ShaderNodeMapRange', clamp=clamp, interpolation_type=interp)
        s._in(n.inputs[0], v); s._in(n.inputs[1], a0); s._in(n.inputs[2], a1); s._in(n.inputs[3], b0); s._in(n.inputs[4], b1); return n.outputs[0]

    def sep(s, vec):
        n = s.node('ShaderNodeSeparateXYZ'); s._in(n.inputs[0], vec); return n.outputs

    def comb(s, x=0.0, y=0.0, z=0.0):
        n = s.node('ShaderNodeCombineXYZ'); s._in(n.inputs[0], x); s._in(n.inputs[1], y); s._in(n.inputs[2], z); return n.outputs[0]

    def vmath(s, op, a, b=None, scale=None):
        n = s.node('ShaderNodeVectorMath', operation=op); s._in(n.inputs[0], a)
        if b is not None:
            s._in(n.inputs[1], b)
        if scale is not None:
            s._in(n.inputs['Scale'], scale)
        return n.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs[0]

    def hsv(s, col, h=0.5, sat=1.0, v=1.0, fac=1.0):
        n = s.node('ShaderNodeHueSaturation'); s._in(n.inputs['Color'], col); s._in(n.inputs['Hue'], h); s._in(n.inputs['Saturation'], sat); s._in(n.inputs['Value'], v); s._in(n.inputs['Fac'], fac); return n.outputs[0]

    def ao(s, dist=0.05, samples=8, inside=False, only_local=False):
        n = s.node('ShaderNodeAmbientOcclusion', samples=samples, inside=inside, only_local=only_local); n.inputs['Distance'].default_value = dist; return n.outputs['AO']

    def bevel(s, radius=0.002, samples=6):
        n = s.node('ShaderNodeBevel', samples=samples); n.inputs['Radius'].default_value = radius; return n.outputs[0]

    def attr(s, name, out='Fac'):
        n = s.node('ShaderNodeAttribute'); n.attribute_name = name; return n.outputs[out]

    def bump(s, height, strength=0.3, dist=0.001, normal=None):
        n = s.node('ShaderNodeBump'); s._in(n.inputs['Height'], height); n.inputs['Strength'].default_value = strength; n.inputs['Distance'].default_value = dist
        if normal is not None:
            s._in(n.inputs['Normal'], normal)
        return n.outputs[0]

    def image(s, path, cs='sRGB', vec=None, proj='FLAT', blend=0.25, interp='Linear', ext='REPEAT'):
        n = s.node('ShaderNodeTexImage'); n.image = bpy.data.images.load(path, check_existing=True); n.image.colorspace_settings.name = cs
        n.projection = proj; n.interpolation = interp; n.extension = ext
        if proj == 'BOX':
            n.projection_blend = blend
        if vec is not None:
            s._in(n.inputs['Vector'], vec)
        return n

    def normalmap(s, col, strength=1.0):
        n = s.node('ShaderNodeNormalMap'); s._in(n.inputs['Color'], col); n.inputs['Strength'].default_value = strength; return n.outputs[0]

    def scan(s, aid, scale=1.0, vec=None, res='2k', proj='BOX', blend=0.3, rot=(0, 0, 0), loc=(0, 0, 0)):
        """Poly Haven set (diff / nor_gl / rough) box-projected in object space; returns dict of sockets"""
        d = os.path.join(TP, 'polyhaven', aid); m = s.mapping(vec if vec is not None else s.obj, scale=scale, rot=rot, loc=loc); r = {}
        for k, cs in (('diff', 'sRGB'), ('nor_gl', 'Non-Color'), ('rough', 'Non-Color'), ('ao', 'Non-Color'), ('disp', 'Non-Color')):
            for ext in ('jpg', 'png'):
                p = os.path.join(d, '%s_%s_%s.%s' % (aid, k, res, ext))
                if os.path.exists(p):
                    r[k] = s.image(p, cs, m, proj, blend).outputs[0]; break
        return r

    def set(s, **kw):
        """wire Principled inputs by python-ish names: base, rough, metal, normal, alpha, sss, sss_radius, sss_scale, coat, coat_rough, spec, emission, emission_strength, transmission, ior, sheen"""
        names = {'base': 'Base Color', 'rough': 'Roughness', 'metal': 'Metallic', 'normal': 'Normal', 'alpha': 'Alpha', 'sss': 'Subsurface Weight', 'sss_radius': 'Subsurface Radius',
                 'sss_scale': 'Subsurface Scale', 'coat': 'Coat Weight', 'coat_rough': 'Coat Roughness', 'spec': 'Specular IOR Level', 'emission': 'Emission Color',
                 'emission_strength': 'Emission Strength', 'transmission': 'Transmission Weight', 'ior': 'IOR', 'sheen': 'Sheen Weight', 'sheen_rough': 'Sheen Roughness',
                 'sheen_tint': 'Sheen Tint', 'coat_normal': 'Coat Normal', 'aniso': 'Anisotropic', 'spec_tint': 'Specular Tint', 'sss_aniso': 'Subsurface Anisotropy'}
        for k, v in kw.items():
            s._in(s.bsdf.inputs[names[k]], v)
        return s.mat


def assign(ob, mat):
    ob.data.materials.clear(); ob.data.materials.append(mat); return ob


# ------------------------------------------------------------------ bake
def lin2srgb(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def srgb2lin(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def save_png(arr, path, mode=None):
    """arr float 0..1 (h, w, c) with row 0 at the BOTTOM (Blender order); written top-down as 8-bit PNG"""
    from PIL import Image
    a = (np.clip(arr[::-1], 0, 1) * 255.0 + 0.5).astype(np.uint8)
    if a.ndim == 3 and a.shape[2] == 1:
        a = a[..., 0]
    Image.fromarray(a, mode).save(path, optimize=True)


def _emit_swap(mats, channel):
    """rewire every material so `channel` of its Principled BSDF drives an emission shader; returns the undo list"""
    undo = []
    for m in mats:
        nt = m.node_tree; out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not out or not b:
            continue
        old = out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].links else None
        em = nt.nodes.new('ShaderNodeEmission'); src = b.inputs[channel]
        if src.links:
            nt.links.new(src.links[0].from_socket, em.inputs['Color'])
        else:
            v = src.default_value; em.inputs['Color'].default_value = (v, v, v, 1.0) if isinstance(v, float) else (v[0], v[1], v[2], 1.0)
        nt.links.new(em.outputs[0], out.inputs['Surface']); undo.append((nt, out, old, em))
    return undo


def _emit_undo(undo):
    for nt, out, old, em in undo:
        if old:
            nt.links.new(old, out.inputs['Surface'])
        nt.nodes.remove(em)


def bake_set(lo, hi_obs, px, outdir, tname, extrude=0.004, maxdist=0.02, alpha=False, emissive=False, ao_dist=None, spp_ao=48, margin=16, ss=1,
             ao_floor=0.0, post=None):
    """bake the high source onto the game mesh (selected to active). Writes T_<tname>_BC/_N/_ORM(/_E).png; returns (files, stats).
    ss = supersample factor (bake at px*ss, box-filter down). The game mesh needs one material slot (any) and UVs in 0..1."""
    sc = bpy.context.scene; use_hip_gpu(sc); sc.cycles.use_denoising = False; sc.cycles.max_bounces = 2; sc.cycles.use_adaptive_sampling = False
    os.makedirs(outdir, exist_ok=True); P = px * ss
    joined = None
    if len(hi_obs) > 6:                              # Blender bakes every selected source object as its own pass: join copies of a many-part source first
        cps = [dup(o, o.name + '_bk') for o in hi_obs]
        for o in hi_obs:
            o.hide_render = True
        joined = join(cps, 'bake_source'); hi_all = hi_obs; hi_obs = [joined]
    hidden = [o for o in sc.objects if o.type == 'MESH' and o not in hi_obs and o is not lo and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    for o in hi_obs:
        o.hide_render = False
    lo.hide_render = False; activate(lo, hi_obs)
    vis = ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission')
    for k in vis:
        setattr(lo, k, False)
    img = bpy.data.images.new('bake_tmp', P, P, alpha=True, float_buffer=True, is_data=True)
    bm_ = bpy.data.materials.new('bake_target'); bm_.use_nodes = True; tn = bm_.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = img; bm_.node_tree.nodes.active = tn
    old_mats = list(lo.data.materials); lo.data.materials.clear(); lo.data.materials.append(bm_)
    himats = []
    for o in hi_obs:
        for m in o.data.materials:
            if m and m not in himats:
                himats.append(m)
    res = {}

    def run(typ, spp, **kw):
        sc.cycles.samples = spp
        k = dict(type=typ, use_selected_to_active=True, cage_extrusion=extrude, max_ray_distance=maxdist, margin=margin * ss, margin_type='EXTEND', use_clear=True, save_mode='INTERNAL')
        k.update(kw)
        try:
            bpy.ops.object.bake(**k)
        except RuntimeError as e:
            print('GPU bake failed, CPU retry:', e); sc.cycles.device = 'CPU'; bpy.ops.object.bake(**k)
        a = np.zeros(P * P * 4, np.float32); img.pixels.foreach_get(a); a = a.reshape(P, P, 4)
        if ss > 1:
            a = a.reshape(px, ss, px, ss, 4).mean((1, 3))
        return a.copy()

    t0 = time.time()
    chans = [('bc', 'Base Color', 4), ('rough', 'Roughness', 4), ('metal', 'Metallic', 2)] + ([('alpha', 'Alpha', 4)] if alpha else [])
    for key, ch, spp in chans:
        u = _emit_swap(himats, ch); res[key] = run('EMIT', spp); _emit_undo(u)
    if emissive:
        u = _emit_swap(himats, 'Emission Color'); res['e'] = run('EMIT', 4); _emit_undo(u)
    res['n'] = run('NORMAL', 8, normal_space='TANGENT')
    if ao_dist:
        sc.world.light_settings.distance = ao_dist
    res['ao'] = run('AO', spp_ao)
    print('BAKED %s %dpx in %.0fs' % (tname, px, time.time() - t0)); sys.stdout.flush()
    lo.data.materials.clear()
    for m in old_mats:
        lo.data.materials.append(m)
    bpy.data.materials.remove(bm_); bpy.data.images.remove(img)
    for k in vis:
        setattr(lo, k, True)
    for o in hidden:
        o.hide_render = False
    if joined:
        bpy.data.objects.remove(joined)
        for o in hi_all:
            o.hide_render = False
    if post:
        post(res)
    ao = np.clip(res['ao'][..., 0], 0, 1); ao = ao_floor + (1 - ao_floor) * ao
    orm = np.dstack([ao, res['rough'][..., 0], res['metal'][..., 0]])
    bc = lin2srgb(res['bc'][..., :3]); files = {}
    if alpha:
        bc = np.dstack([bc, np.clip(res['alpha'][..., 0], 0, 1)])
    for key, arr in (('BC', bc), ('N', res['n'][..., :3]), ('ORM', orm)) + ((('E', lin2srgb(res['e'][..., :3])),) if emissive else ()):
        p = os.path.join(outdir, 'T_%s_%s.png' % (tname, key)); save_png(arr, p); files[key] = p
    lum = (bc[..., :3] @ np.array([0.2126, 0.7152, 0.0722])) * 255
    stats = {'albedo_luma_srgb': {'p1': round(float(np.percentile(lum, 1)), 1), 'mean': round(float(lum.mean()), 1), 'p99': round(float(np.percentile(lum, 99)), 1)},
             'roughness': {'p5': round(float(np.percentile(orm[..., 1], 5)), 3), 'mean': round(float(orm[..., 1].mean()), 3), 'p95': round(float(np.percentile(orm[..., 1], 95)), 3)},
             'metallic_mean': round(float(orm[..., 2].mean()), 3), 'ao_mean': round(float(ao.mean()), 3)}
    return files, stats


def game_material(name, files, alpha=None, sss=None, emissive_strength=None, normal_strength=1.0):
    """the shipping look: Principled fed by the baked BC / N / ORM set (what Unreal's M_Standard does)"""
    t = NT(name); bc = t.image(files['BC'], 'sRGB'); n = t.image(files['N'], 'Non-Color'); orm = t.image(files['ORM'], 'Non-Color')
    for nd, k in ((bc, 'BC'), (n, 'N'), (orm, 'ORM')):
        nd.image.name = os.path.splitext(os.path.basename(files[k]))[0]          # T_<Name>_<BC|N|ORM>, as the validator wants
    sp = t.node('ShaderNodeSeparateColor'); t.L.new(orm.outputs[0], sp.inputs[0])
    aomix = t.mix(1.0, bc.outputs[0], t.maprange(sp.outputs[0], 0, 1, 0.5, 1.0), blend='MULTIPLY')        # AO shown as Unreal shows it: on indirect light only (approximated)
    t.set(base=aomix, rough=sp.outputs[1], metal=sp.outputs[2], normal=t.normalmap(n.outputs[0], normal_strength))
    if alpha:
        t.set(alpha=bc.outputs[1])
        if alpha == 'CLIP':
            try:
                t.mat.blend_method = 'CLIP'
            except Exception:
                pass
    if sss:
        t.set(sss=sss.get('weight', 0.2), sss_radius=sss.get('radius', (1.0, 0.3, 0.15)), sss_scale=sss.get('scale', 0.01))
    if emissive_strength and 'E' in files:
        e = t.image(files['E'], 'sRGB'); t.set(emission=e.outputs[0], emission_strength=emissive_strength)
    return t.mat


# ------------------------------------------------------------------ review renders
def review_setup(ground='forrest_ground_01', ground_scale=0.8, exposure=-4.6, sun_rot=-150.0, sun_elev=40.0, ground_size=30.0, ground_tint=None):
    sc = bpy.context.scene; use_hip_gpu(sc)
    sc.cycles.use_denoising = True; sc.cycles.max_bounces = 6; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.01
    try:
        sc.cycles.denoising_use_gpu = True
    except Exception:
        pass
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
    for k in dir(sc.render):                         # no render metadata in the PNG: it would carry the absolute path of the .blend
        if k.startswith('use_stamp'):
            try:
                setattr(sc.render, k, False)
            except Exception:
                pass
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    w = bpy.data.worlds.new('review_sky'); sc.world = w; w.use_nodes = True; nt = w.node_tree; sky = nt.nodes.new('ShaderNodeTexSky')
    ids = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING'):
        if t in ids:
            sky.sky_type = t; break
    sky.sun_elevation = math.radians(sun_elev); sky.sun_rotation = math.radians(sun_rot); sky.sun_disc = True
    nt.links.new(sky.outputs[0], nt.nodes['Background'].inputs[0]); sc.view_settings.exposure = exposure
    rc = coll('Review'); gnd = None
    if ground:
        S = ground_size; gnd = new_obj('review_ground', [(-S, -S, 0), (S, -S, 0), (S, S, 0), (-S, S, 0)], [(0, 1, 2, 3)], rc, smooth=False)
        t = NT('review_ground'); sset = t.scan(ground, scale=ground_scale, proj='FLAT')
        # break the tile repeat with a second, rotated, larger sample and a large-scale value drift
        s2 = t.scan(ground, scale=ground_scale * 0.37, proj='FLAT', rot=(0, 0, 1.1), loc=(3.3, 1.7, 0))
        f = t.ramp(t.noise(0.9, 3, 0.5), [(0.38, 0.0), (0.62, 1.0)])
        base = t.mix(f, sset['diff'], s2['diff']); base = t.mix(t.noise(0.25, 2, 0.5), base, (0.0, 0.0, 0.0), blend='MULTIPLY') if False else base
        base = t.hsv(base, v=t.maprange(t.noise(0.35, 2, 0.5), 0.3, 0.7, 0.8, 1.15))
        if ground_tint:
            base = t.mix(1.0, base, ground_tint, blend='MULTIPLY')
        nrm = t.mix(f, sset['nor_gl'], s2['nor_gl'])
        t.set(base=base, rough=t.mixf(f, sset['rough'], s2['rough']) if 'rough' in sset else 0.8, normal=t.normalmap(nrm, 1.0))
        assign(gnd, t.mat)
    camd = bpy.data.cameras.new('review_cam'); cam = bpy.data.objects.new('review_cam', camd); rc.objects.link(cam); sc.camera = cam; camd.clip_start = 0.005; camd.clip_end = 500
    return {'sky': sky, 'cam': cam, 'ground': gnd, 'coll': rc}


def bounds(obs):
    dg = bpy.context.evaluated_depsgraph_get(); lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for o in obs:
        e = o.evaluated_get(dg)
        for c in e.bound_box:
            p = np.array(e.matrix_world @ Vector(c)); lo = np.minimum(lo, p); hi = np.maximum(hi, p)
    return lo, hi


def shot(R, path, obs=None, az=35.0, el=28.0, fill=0.72, lens=70.0, res=(1200, 900), spp=160, center=None, radius=None, fstop=None, exposure=None, dz=0.0):
    """frame obs (or centre/radius) from azimuth/elevation in degrees; fill = fraction of the frame the bounding sphere takes"""
    sc = bpy.context.scene; cam = R['cam']
    if center is None:
        lo, hi = bounds(obs); center = (lo + hi) / 2; radius = float(np.linalg.norm(hi - lo)) / 2
    center = np.array(center, float) + np.array([0, 0, dz]); cam.data.lens = lens; cam.data.sensor_width = 36.0
    aspect = res[0] / res[1]; hfov = 2 * math.atan(18.0 / lens); vfov = 2 * math.atan(18.0 / lens / aspect); fov = min(hfov, vfov)
    dist = radius / math.sin(fov / 2) / max(0.05, fill)
    a = math.radians(az); e = math.radians(el); d = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    loc = center + d * dist; loc[2] = max(loc[2], 0.02); cam.location = loc
    cam.rotation_euler = (Vector(center) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.dof.use_dof = bool(fstop)
    if fstop:
        cam.data.dof.focus_distance = float(np.linalg.norm(loc - center)); cam.data.dof.aperture_fstop = fstop
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100; sc.cycles.samples = spp; sc.render.filepath = path
    if exposure is not None:
        sc.view_settings.exposure = exposure
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        bpy.ops.render.render(write_still=True)
    except RuntimeError as ex:
        print('GPU render failed, CPU retry:', ex); sc.cycles.device = 'CPU'; bpy.ops.render.render(write_still=True)
    print('RENDERED', path); sys.stdout.flush()


# ------------------------------------------------------------------ export / manifest
def scratch_export(path):
    """FBX stores the absolute path it was written to: write under a scratch folder, then move it into place"""
    d = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'dink_unclaimed_export'); os.makedirs(d, exist_ok=True); os.makedirs(os.path.dirname(path), exist_ok=True)
    return os.path.join(d, os.path.basename(path))


def export_fbx(path, obs):
    activate(obs[0], obs[1:]); final = path; path = scratch_export(final)
    hid = [(o, o.hide_render) for o in obs]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL', axis_forward='Y', axis_up='Z',
                             bake_space_transform=False, use_triangles=True, mesh_smooth_type='FACE', use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP',
                             object_types={'MESH', 'ARMATURE', 'EMPTY'}, colors_type='NONE', use_mesh_modifiers=True)
    import shutil; shutil.move(path, final); return final


def save_blend(path=None):
    """save compressed with relative paths; the render path buffer is overwritten first so no absolute path fragment stays in the file"""
    sc = bpy.context.scene; sc.render.filepath = '/' * 1000; sc.render.filepath = '//render'
    if path:
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, relative_remap=True)
    try:
        bpy.ops.file.make_paths_relative()
    except Exception as e:
        print('relative paths:', e)
    bpy.ops.wm.save_mainfile(compress=True)



def finish_static(asset, cls, lo, hi_obs, outdir, px, families, origin, dresses, weaknesses, extrude=0.004, maxdist=0.02, alpha=None, sss=None, third_party=(),
                  collision=None, extra=None, ss=1, ao_dist=None, script=None, lods=None, post=None, emissive=False, emissive_strength=None, keep_hi=True, ao_floor=0.0):
    """bake, bind the baked set to the game mesh, LODs/UCX, export FBX, save the .blend and write manifest.json. Returns the manifest dict."""
    os.makedirs(outdir, exist_ok=True); name = asset[3:] if asset[:3] in ('SM_', 'SK_') else asset
    ac = coll(asset); ac['dink_class'] = cls; ac['dink_tex_px'] = px; ac['dink_source'] = 'authored in Blender by script (%s); CC0 scans: %s' % (script or '', ', '.join(third_party) or 'none')
    link(lo, ac); lo.name = asset; lo.data.name = asset
    files, stats = bake_set(lo, hi_obs, px, outdir, name, extrude=extrude, maxdist=maxdist, alpha=bool(alpha), ss=ss, ao_dist=ao_dist, post=post, emissive=emissive, ao_floor=ao_floor)
    gm = game_material('MI_' + name, files, alpha=alpha, sss=sss, emissive_strength=emissive_strength); assign(lo, gm)
    exp = [lo]; lodtris = {}
    ratios = lods if lods is not None else LOD_RATIOS.get(cls, ())
    if ratios:
        lo.name = asset + '_LOD0'
        for o in make_lods(lo, ratios):
            exp.append(o); lodtris[o.name[-4:].lower() + '_triangles'] = tri_count(o)
    want_col = collision if collision is not None else cls in ('prop', 'prop_large', 'kit_piece', 'door', 'building')
    ucx = None
    if want_col:
        ucx = make_ucx(lo); exp.append(ucx)
    st = mesh_stats(lo); fbx = os.path.join(outdir, asset + '.fbx'); export_fbx(fbx, exp)
    hc = coll('Source_Hi')
    for o in hi_obs:
        link(o, hc); o.hide_render = True; o.hide_viewport = True
        if not keep_hi:
            bpy.data.objects.remove(o)
    blend = os.path.join(outdir, asset + '.blend'); save_blend(blend)
    soft, hard = BUDGET.get(cls, (None, None))
    from PIL import Image
    man = {'name': asset, 'class': cls, 'fbx': rel(fbx), 'source_blend': rel(blend), 'build': 'Unclaimed/tools/bl.sh %s' % (script or '?'),
           'dimensions_m': st['dimensions_m'], 'bounds_min_m': st['bounds_min_m'], 'bounds_max_m': st['bounds_max_m'], 'lod0_triangles': st['triangles'], **lodtris,
           'triangle_budget': {'soft': soft, 'hard': hard, 'within_soft': (soft is None or st['triangles'] <= soft)},
           'textures': [{'file': rel(p), 'size_px': list(Image.open(p).size), 'channels': {'BC': 'base colour sRGB' + (' + alpha' if alpha else ''), 'N': 'tangent normal, OpenGL (green up; flip green on import)', 'ORM': 'R occlusion, G roughness, B metallic', 'E': 'emissive sRGB'}[k]} for k, p in files.items()],
           'materials': ['MI_' + name], 'material_exception': 'unique BC/N/ORM bake private to this asset (not a row of ART_STANDARD.md section 2): the task for the unclaimed families asks for a baked set per asset, and the surface detail here (see dresses) does not exist in the shared library',
           'collision_hulls': 1 if ucx else 0, 'validation': {k: st[k] for k in ('non_manifold_edges', 'open_edges', 'loose_verts', 'zero_area_faces', 'signed_volume_positive', 'uv_range', 'transforms_applied')},
           'bake_stats': stats, 'pivot': 'base centre (bbox centre in X/Y, mesh bottom at z = 0), front on -Y',
           'families': families, 'origin_ids': origin, 'supersedes': 'none (placeholder greybox cards)', 'dresses': dresses,
           'third_party': list(third_party), 'status': 'source delivered; not imported into Unreal, not bound in families.json', 'known_weaknesses': weaknesses}
    if sss:
        man['render_hint'] = {'subsurface': sss}
    if extra:
        man.update(extra)
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', os.path.join(outdir, 'manifest.json'))
    return man


def origin_ids(families):
    """origin IDs (Snnn_Pnn) per class id from the gate-2 backlog report"""
    import re
    txt = open(os.path.join(REPO, 'doc', 'remaster', 'ALPHA_GATE2_BACKLOG.md')).read(); out = {}
    for fam in families:
        m = re.search(r'^\*\*\d+\. `%s`\*\*.*?\n(.*?)\n' % re.escape(fam), txt, re.M); ids = []
        for part in (m.group(1).split(' \u00b7 ') if m else []):
            sm = re.match(r'(S\d{3}): (.*)', part.strip())
            if sm:
                ids += ['%s_%s' % (sm.group(1), p_) for p_ in sm.group(2).split()]
        out[fam] = ids
    return out
