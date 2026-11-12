"""Shared Blender helpers for the SCR_440 kit: closed-solid primitives with per-part wood-grain
attributes, collection/asset bookkeeping, and UV utilities.  Blender 5.2, no add-ons."""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

STATE = {'coll': None, 'pieces': [], 'rng': None}


def rng():
    return STATE['rng']


# --------------------------------------------------------------------------- attributes
ATTRS = {  # name: (type, domain)
    'grain': ('FLOAT_VECTOR', 'POINT'),   # wood: part-local coordinates, Z along the grain, pith at XY origin
    'gaxis': ('FLOAT_VECTOR', 'POINT'),   # wood: grain direction in object space (end-grain detection)
    'polish': ('FLOAT', 'POINT'),         # hand polish / wear 0..1
    'edge': ('FLOAT', 'POINT'),           # sharpened/polished metal edge 0..1
    'logr': ('FLOAT', 'POINT'),           # log radius (bark ring on end grain), 0 = none
    'bark': ('FLOAT', 'FACE'),            # 1 on bark-covered faces
    'chop': ('FLOAT', 'FACE'),            # 1 on a chopping surface (axe marks)
    'stalk': ('FLOAT', 'FACE'),           # 1 on loose straw stalks (kept through the bale LODs)
}


def write_attrs(me, values):
    """values: dict name -> per-vertex (or per-face for FACE domain) sequence."""
    for name, (typ, dom) in ATTRS.items():
        if name in me.attributes:
            continue
        a = me.attributes.new(name, typ, dom)
        n = len(me.vertices) if dom == 'POINT' else len(me.polygons)
        if typ == 'FLOAT_VECTOR':
            data = np.zeros((n, 3), np.float32)
            if name in values:
                data[:] = np.asarray(values[name], np.float32).reshape(n, 3)
            a.data.foreach_set('vector', data.ravel())
        else:
            data = np.zeros(n, np.float32)
            if name in values:
                v = values[name]
                data[:] = v if np.ndim(v) else np.full(n, v, np.float32)
            a.data.foreach_set('value', data)


# --------------------------------------------------------------------------- object creation
def new_collection(name, cls, path, source):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    coll['dink_class'] = cls
    coll['dink_path'] = path
    coll['dink_source'] = source
    STATE['coll'] = coll
    STATE['pieces'] = []
    return coll


def obj_from_bm(bm, name, mat, attrs=None, smooth_angle=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    if attrs is not None:
        write_attrs(me, attrs)
    ob = bpy.data.objects.new(name, me)
    STATE['coll'].objects.link(ob)
    me.materials.append(mat)
    STATE['pieces'].append(ob)
    return ob


def bm_vertex_array(bm):
    bm.verts.ensure_lookup_table()
    return np.array([v.co[:] for v in bm.verts])


def frame_from_axis(axis, up_hint=(0, 0, 1)):
    z = Vector(axis).normalized()
    up = Vector(up_hint)
    if abs(z.dot(up)) > .95:
        up = Vector((1, 0, 0)) if abs(z.x) < .9 else Vector((0, 1, 0))
    x = up.cross(z).normalized(); y = z.cross(x)
    return Matrix((x, y, z)).transposed()   # columns x,y,z


def grain_values(local, axis_world, pith=(0, 0), offset=None, polish=0.0, edge=0.0, logr=0.0):
    """local: (n,3) part-local coordinates with z along the grain."""
    r = rng()
    off = np.array(offset if offset is not None else (pith[0], pith[1], r.uniform(-5, 5)))
    g = local + off
    n = len(local)
    return {'grain': g, 'gaxis': np.tile(np.array(axis_world[:3]), (n, 1)), 'polish': polish, 'edge': edge, 'logr': logr}


# --------------------------------------------------------------------------- primitives
def box(center, dims, mat, bevel=.006, segments=2, rot=None, grain_axis=2, pith=None, polish=0.0, edge=0.0, subdiv=0, attrs=True):
    """Bevelled closed box.  rot: Matrix(3x3) or Euler; grain_axis: which local axis carries the grain."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    if subdiv:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdiv, use_grid_fill=True)
    if bevel > 0:
        b = min(bevel, min(dims) * .45)
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=b, segments=segments, affect='EDGES', profile=.5)
    local = bm_vertex_array(bm)
    R = rot if isinstance(rot, Matrix) else (rot.to_matrix() if rot is not None else Matrix.Identity(3))
    perm = {0: (1, 2, 0), 1: (2, 0, 1), 2: (0, 1, 2)}[grain_axis]
    axis_local = Vector([1 if i == grain_axis else 0 for i in range(3)])
    g = local[:, perm]
    if pith is None:
        pith = (rng().uniform(.08, .3) * rng().choice([-1, 1]), rng().uniform(.05, .3))
    vals = grain_values(g, R @ axis_local, pith=pith, polish=polish, edge=edge) if attrs else None
    M = Matrix.Translation(Vector(center)) @ R.to_4x4()
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    return obj_from_bm(bm, 'Box', mat, vals)


def beam(a, b, w, d, mat, bevel=.006, polish=0.0, roll=0.0):
    a = Vector(a); b = Vector(b); delta = b - a
    R = frame_from_axis(delta) @ Matrix.Rotation(roll, 3, 'Z')
    return box((a + b) / 2, (w, d, delta.length), mat, bevel, rot=R, grain_axis=2, polish=polish)


def tube(points, radii, mat, sides=10, cap=True, polish=None, edge=None, grain=True, pith=None, ovals=None, twist=0.0):
    """Swept closed tube along a polyline with parallel-transport frames.
    radii: scalar or per-point list; polish/edge: per-point lists or scalar; ovals: per-point (sx,sy)."""
    pts = [Vector(p) for p in points]; n = len(pts)
    radii = radii if isinstance(radii, (list, tuple, np.ndarray)) else [radii] * n
    ovals = ovals or [(1, 1)] * n
    tangents = []
    for i in range(n):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        tangents.append(t)
    F = frame_from_axis(tangents[0]); xs = [F.col[0]]; ys = [F.col[1]]
    for i in range(1, n):
        x = xs[-1] - tangents[i] * xs[-1].dot(tangents[i]); x.normalize()
        xs.append(x); ys.append(tangents[i].cross(x))
    bm = bmesh.new(); rings = []; local = []; s = 0.0; pol = []; edg = []
    for i in range(n):
        if i:
            s += (pts[i] - pts[i - 1]).length
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides + twist * s
            cx, cy = math.cos(a) * radii[i] * ovals[i][0], math.sin(a) * radii[i] * ovals[i][1]
            ring.append(bm.verts.new(pts[i] + xs[i] * cx + ys[i] * cy))
            local.append((cx, cy, s))
            pol.append(polish[i] if isinstance(polish, (list, tuple, np.ndarray)) else (polish or 0.0))
            edg.append(edge[i] if isinstance(edge, (list, tuple, np.ndarray)) else (edge or 0.0))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if pith is None:
        pith = (rng().uniform(.06, .25), rng().uniform(.04, .2))
    vals = grain_values(np.array(local), tangents[n // 2], pith=pith, polish=np.array(pol), edge=np.array(edg)) if grain else None
    if vals is not None:
        # grain axis per vertex follows the tube
        vals['gaxis'] = np.repeat(np.array([t[:] for t in tangents]), sides, axis=0)
    return obj_from_bm(bm, 'Tube', mat, vals)


def lathe(profile, mat, axis_m=None, sides=24, center=(0, 0, 0), polish=0.0, edge=0.0, close=True, pith=(0, 0)):
    """Surface of revolution about local Z.  profile: [(r, z)] from bottom to top; r=0 end points become poles."""
    bm = bmesh.new(); rings = []; local = []
    for r, z in profile:
        ring = []
        cnt = 1 if r < 1e-6 else sides
        for k in range(cnt):
            a = 2 * math.pi * k / sides
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
            local.append((math.cos(a) * r, math.sin(a) * r, z))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        if len(A) == 1 and len(B) == 1:
            continue
        for k in range(sides):
            k2 = (k + 1) % sides
            if len(A) == 1:
                bm.faces.new((A[0], B[k], B[k2]))
            elif len(B) == 1:
                bm.faces.new((A[k], B[0], A[k2]))
            else:
                bm.faces.new((A[k], A[k2], B[k2], B[k]))
    if close:
        if len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    R = axis_m if axis_m is not None else Matrix.Identity(3)
    vals = grain_values(np.array(local), R.col[2], pith=pith, polish=polish, edge=edge)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ R.to_4x4(), verts=bm.verts[:])
    return obj_from_bm(bm, 'Lathe', mat, vals)


def ring_solid(radius, width, thick, mat, center=(0, 0, 0), axis_m=None, sides=48, bevel_frac=.25, grain_tangent=True):
    """Rectangular-section ring (tyre, felloe, hoop). radius = mid radius; width along axis, thick radial."""
    prof = []
    b = min(width, thick) * bevel_frac
    r0, r1 = radius - thick / 2, radius + thick / 2; z0, z1 = -width / 2, width / 2
    sec = [(r0 + b, z0), (r1 - b, z0), (r1, z0 + b), (r1, z1 - b), (r1 - b, z1), (r0 + b, z1), (r0, z1 - b), (r0, z0 + b)]
    bm = bmesh.new(); rings = []; local = []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        ring = []
        for (r, z) in sec:
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
            # grain runs around the ring: local coords (radial, axial, arc)
            local.append((r - radius + .15, z, a * radius))
        rings.append(ring)
    m = len(sec)
    for k in range(sides):
        A, B = rings[k], rings[(k + 1) % sides]
        for j in range(m):
            j2 = (j + 1) % m
            bm.faces.new((A[j], A[j2], B[j2], B[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    R = axis_m if axis_m is not None else Matrix.Identity(3)
    vals = grain_values(np.array(local), R.col[0], pith=(0, 0), offset=(0, 0, 0))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ R.to_4x4(), verts=bm.verts[:])
    return obj_from_bm(bm, 'Ring', mat, vals)


def plate(fn, nu, nv, thick_fn, mat, edge_fn=None, polish=0.0):
    """Closed solid around a parametric mid-surface fn(u,v)->Vector, u,v in [0,1].
    thick_fn(u,v)->thickness (m).  Normals by finite differences."""
    bm = bmesh.new()
    P = [[Vector(fn(i / (nu - 1), j / (nv - 1))) for j in range(nv)] for i in range(nu)]
    top = [[None] * nv for _ in range(nu)]; bot = [[None] * nv for _ in range(nu)]
    local = []; edges = []
    for i in range(nu):
        for j in range(nv):
            du = P[min(i + 1, nu - 1)][j] - P[max(i - 1, 0)][j]
            dv = P[i][min(j + 1, nv - 1)] - P[i][max(j - 1, 0)]
            nrm = du.cross(dv)
            nrm = nrm.normalized() if nrm.length > 1e-12 else Vector((0, 0, 1))
            t = max(thick_fn(i / (nu - 1), j / (nv - 1)), 4e-4) / 2
            top[i][j] = bm.verts.new(P[i][j] + nrm * t)
            bot[i][j] = bm.verts.new(P[i][j] - nrm * t)
            e = edge_fn(i / (nu - 1), j / (nv - 1)) if edge_fn else 0.0
            for _ in range(2):
                local.append(tuple(P[i][j])); edges.append(e)
    for i in range(nu - 1):
        for j in range(nv - 1):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    for i in range(nu - 1):
        bm.faces.new((top[i][0], bot[i][0], bot[i + 1][0], top[i + 1][0]))
        bm.faces.new((top[i][nv - 1], top[i + 1][nv - 1], bot[i + 1][nv - 1], bot[i][nv - 1]))
    for j in range(nv - 1):
        bm.faces.new((top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]))
        bm.faces.new((top[nu - 1][j], bot[nu - 1][j], bot[nu - 1][j + 1], top[nu - 1][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    vals = grain_values(np.array(local), Vector((0, 0, 1)), offset=(0, 0, 0), polish=polish, edge=np.array(edges))
    return obj_from_bm(bm, 'Plate', mat, vals)


def prism(outline, z0, z1, mat, M=None, bark_edges=None, logr=0.0, grain=True):
    """Extrude a 2D polygon (CCW list of (x,y)) along local Z from z0 to z1.
    bark_edges: set of outline edge indices whose side faces are bark."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in outline]
    hi = [bm.verts.new((x, y, z1)) for x, y in outline]
    bm.faces.new(list(reversed(lo))); bm.faces.new(hi)
    bark = [0.0, 0.0]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        bark.append(1.0 if bark_edges and i in bark_edges else 0.0)
    local = np.array([v.co[:] for v in bm.verts])
    M = M or Matrix.Identity(4)
    vals = grain_values(local, (M.to_3x3() @ Vector((0, 0, 1))).normalized(), pith=(0, 0), offset=(0, 0, 0), logr=logr) if grain else {}
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    # face order is preserved by recalc (normals only)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    vals['bark'] = np.array(bark)
    return obj_from_bm(bm, 'Prism', mat, vals)


# --------------------------------------------------------------------------- joining and finishing
def join_pieces(name, smooth_angle=35):
    pieces = STATE['pieces']
    bpy.ops.object.select_all(action='DESELECT')
    for ob in pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    if len(pieces) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name; ob.data.name = name + '_Mesh'
    # merge only exactly coincident points produced inside a part
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges[:])
    bm.to_mesh(ob.data); bm.free()
    for p in ob.data.polygons:
        p.use_smooth = True
    if smooth_angle is not None:
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth_angle), keep_sharp_edges=True)
    STATE['pieces'] = [ob]
    return ob


def recenter(objs, rule='base_center'):
    """Move all vertices so the render mesh bounds obey the pivot rule (origin at world 0)."""
    ref = objs[0]
    co = np.array([v.co[:] for v in ref.data.vertices])
    mn, mx = co.min(0), co.max(0)
    delta = Vector(((mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]))
    for ob in objs:
        for v in ob.data.vertices:
            v.co -= delta
        ob.data.update()
    return delta, Vector(mx - mn)


def collision_box(coll, base_name, index, center, dims, rot=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    R = rot if isinstance(rot, Matrix) else Matrix.Identity(3)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(center)) @ R.to_4x4(), verts=bm.verts[:])
    me = bpy.data.meshes.new('UCX_%s_%02d' % (base_name, index)); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(me.name, me); coll.objects.link(ob)
    ob.display_type = 'WIRE'; ob.hide_render = True
    return ob


def collision_hull(coll, base_name, index, points):
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    me = bpy.data.meshes.new('UCX_%s_%02d' % (base_name, index)); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(me.name, me); coll.objects.link(ob)
    ob.display_type = 'WIRE'; ob.hide_render = True
    return ob


def smart_uv(ob, margin=.004, angle=60):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def rounded_box(xs, ys, zs, r, mat, disp=None, grain_axis=1, face_attrs=None):
    """Closed rounded box from grid coordinate lists (each sorted, first/last = extents).
    Edges/corners are rounded with radius r; disp(p, n) -> outward offset per vertex."""
    bm = bmesh.new(); V = {}
    nx, ny, nz = len(xs), len(ys), len(zs)
    def vert(i, j, k):
        key = (i, j, k)
        if key not in V:
            V[key] = bm.verts.new((xs[i], ys[j], zs[k]))
        return V[key]
    faces = []
    for (fixed, a_n, b_n) in ((0, ny, nz), (1, nx, nz), (2, nx, ny)):
        for side in (0, -1):
            for a in range(a_n - 1):
                for b in range(b_n - 1):
                    q = []
                    for (da, db) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        aa, bb = a + da, b + db
                        if fixed == 0:
                            idx = (0 if side == 0 else nx - 1, aa, bb)
                        elif fixed == 1:
                            idx = (aa, 0 if side == 0 else ny - 1, bb)
                        else:
                            idx = (aa, bb, 0 if side == 0 else nz - 1)
                        q.append(vert(*idx))
                    faces.append(bm.faces.new(q))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    lo = Vector((xs[0], ys[0], zs[0])) + Vector((r, r, r)); hi = Vector((xs[-1], ys[-1], zs[-1])) - Vector((r, r, r))
    for v in bm.verts:
        p = v.co.copy(); q = Vector((min(max(p[i], lo[i]), hi[i]) for i in range(3)))
        d = p - q
        n = d.normalized() if d.length > 1e-9 else Vector((0, 0, 1))
        v.co = q + n * r
        if disp:
            v.co += n * disp(p, n)
    local = np.array([v.co[:] for v in bm.verts])
    perm = {0: (1, 2, 0), 1: (2, 0, 1), 2: (0, 1, 2)}[grain_axis]
    axis = Vector([1 if i == grain_axis else 0 for i in range(3)])
    vals = grain_values(local[:, perm], axis, pith=(rng().uniform(-3, 3), rng().uniform(-3, 3)))
    if face_attrs:
        vals.update(face_attrs)
    return obj_from_bm(bm, 'RoundedBox', mat, vals)
