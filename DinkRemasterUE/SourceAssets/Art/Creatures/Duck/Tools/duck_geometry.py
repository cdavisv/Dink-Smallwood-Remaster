"""Original domestic (Pekin-type) duck anatomy, built procedurally in metres.

Design space -> final space: the upper body is modelled in a design space and then
counter-tilted at the head and pitched nose-up/lowered onto short, thick legs
(`duck_common.final`).  The legs are modelled directly in final space.

Parts:
* body/neck/head: one metaball field, bisected across the mid neck (decapitation plane);
* folded wing per side built from 24 real feathers (coverts, tertials, secondaries,
  primaries), conformed to the flank and stacked, with the primaries crossing the tail;
* about 1100 alpha-tested contour-feather cards (plus "pocket" cards over the lower wing
  edge) for a broken, fluffy outline;
* rectrix fan, two-part bill, eyes with lid rings, legs, toes, claws, webs;
* gore set for the faithful original death: body and head wound caps on the cut ring and
  thin blood shells running down the neck stump and head stub.

Point attributes: duck_part, duck_a, duck_c, duck_len, duck_card, duck_dpos (design-space
position for texture synthesis).  Face attribute: duck_fpart.
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

import duck_common as D

MB_K = 0.575  # metaball surface radius / element radius (stiffness 2, threshold 0.6; measured)
CUT_P = Vector(D.CUT_POINT)
CUT_N = Vector(D.CUT_NORMAL).normalized()


def _link(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)


def _tag(ob, part, a=None, c=None, length=None, card=None):
    me = ob.data
    n = len(me.vertices)
    for name, typ in (('duck_part', 'INT'), ('duck_a', 'FLOAT'), ('duck_c', 'FLOAT'), ('duck_len', 'FLOAT'), ('duck_card', 'INT')):
        if name not in me.attributes:
            me.attributes.new(name, typ, 'POINT')
    if 'duck_fpart' not in me.attributes:
        me.attributes.new('duck_fpart', 'INT', 'FACE')
    me.attributes['duck_part'].data.foreach_set('value', [part] * n)
    me.attributes['duck_a'].data.foreach_set('value', a if a is not None else [0.0] * n)
    me.attributes['duck_c'].data.foreach_set('value', c if c is not None else [0.0] * n)
    me.attributes['duck_len'].data.foreach_set('value', length if length is not None else [0.0] * n)
    me.attributes['duck_card'].data.foreach_set('value', card if card is not None else [-1] * n)
    me.attributes['duck_fpart'].data.foreach_set('value', [part] * len(me.polygons))


def _mesh(name, verts, faces, coll, mat, part, a=None, c=None, smooth=True, length=None, card=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(clean_customdata=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    _tag(ob, part, a, c, length, card)
    return ob


def _ring_loft(rings, close_start=True, close_end=True):
    seg = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    for j in range(len(rings) - 1):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    if close_start:
        verts.append(sum((Vector(v) for v in rings[0]), Vector()) / seg)
        ci = len(verts) - 1
        for i in range(seg):
            faces.append((ci, (i + 1) % seg, i))
    if close_end:
        base = (len(rings) - 1) * seg
        verts.append(sum((Vector(v) for v in rings[-1]), Vector()) / seg)
        ci = len(verts) - 1
        for i in range(seg):
            faces.append((ci, base + i, base + (i + 1) % seg))
    return verts, faces


def _frame(tangent):
    t = tangent.normalized()
    up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
    side = t.cross(up).normalized()
    up = side.cross(t).normalized()
    return t, side, up


def _fix_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def tube(name, pts, radii, coll, mat, part, seg=12, flat=1.0):
    pts = [Vector(p) for p in pts]
    rings = []
    for k, p in enumerate(pts):
        tan = (pts[1] - pts[0]) if k == 0 else (pts[-1] - pts[-2]) if k == len(pts) - 1 else (pts[k + 1] - pts[k - 1])
        t, side, up = _frame(tan)
        r = radii[k]
        rings.append([p + side * (r * flat * math.cos(math.tau * i / seg)) + up * (r * math.sin(math.tau * i / seg)) for i in range(seg)])
    v, f = _ring_loft(rings)
    ob = _mesh(name, v, f, coll, mat, part)
    _fix_normals(ob)
    return ob


# ---------------------------------------------------------------------------------------------
def build_body(coll, mat):
    mb = bpy.data.metaballs.new('DuckBodyField')
    mb.resolution = 0.0042
    mb.render_resolution = 0.0042
    mb.threshold = 0.6

    def ell(center, semi, pitch_up=0.0):
        e = mb.elements.new(type='ELLIPSOID')
        m = max(semi)
        e.radius = m / MB_K
        e.size_x, e.size_y, e.size_z = semi[0] / m, semi[1] / m, semi[2] / m
        e.co = center
        e.rotation = Quaternion((0, 1, 0), -math.radians(pitch_up))
        e.stiffness = 2.0

    ell((-0.020, 0, 0.205), (0.150, 0.092, 0.080), pitch_up=10)
    ell((0.062, 0, 0.212), (0.074, 0.080, 0.080))           # keel breast
    ell((-0.035, 0, 0.155), (0.112, 0.082, 0.060))          # belly
    ell((-0.125, 0, 0.212), (0.080, 0.070, 0.058), pitch_up=-10)  # rump
    ell((-0.188, 0, 0.245), (0.056, 0.044, 0.032), pitch_up=-38)  # tail base, upturned
    for s in (-1, 1):
        ell((-0.002, s * 0.047, 0.117), (0.036, 0.025, 0.042))  # feathered thighs cover the knee joint
        ell((0.030, s * 0.050, 0.225), (0.070, 0.035, 0.052), pitch_up=6)
    neck = [((0.090, 0.262), 0.047), ((0.106, 0.290), 0.039), ((0.118, 0.316), 0.032),
            ((0.127, 0.340), 0.0285), ((0.134, 0.362), 0.0275), ((0.140, 0.384), 0.0275),
            ((0.146, 0.404), 0.029)]
    for (x, z), r in neck:
        ell((x, 0, z), (r * 1.06, r * 0.90, r))
    ell((0.162, 0, 0.429), (0.045, 0.032, 0.034))
    ell((0.178, 0, 0.442), (0.031, 0.024, 0.024), pitch_up=-10)
    for s in (-1, 1):
        mbe = mb.elements.new(type='ELLIPSOID')
        mbe.radius = 0.027 / MB_K
        mbe.size_x, mbe.size_y, mbe.size_z = 1.0, 0.018 / 0.027, 0.020 / 0.027
        mbe.co = (0.181, s * 0.013, 0.421)
    ob = bpy.data.objects.new('DuckBodyField', mb)
    coll.objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target='MESH')
    body = bpy.context.object
    body.name = 'Duck body'
    _link(body, coll)
    me = body.data
    rnd = random.Random(D.SEED)
    phases = [(rnd.uniform(0, 6.28), rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)) for _ in range(6)]
    me.update()
    for v in me.vertices:
        p = v.co
        d = 0.0
        for k, (a, b, c) in enumerate(phases):
            f = 55 + 23 * k
            d += math.sin(p.x * f + a) * math.sin(p.y * f * 1.3 + b) * math.sin(p.z * f * 0.9 + c)
        v.co = p + v.normal * d * 0.00025
    sm = body.modifiers.new('relax', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = 2
    bpy.ops.object.modifier_apply(modifier=sm.name)
    me.calc_loop_triangles()
    dec = body.modifiers.new('game topology', 'DECIMATE')
    dec.ratio = min(1.0, 8200 / max(1, len(me.loop_triangles)))
    bpy.ops.object.modifier_apply(modifier=dec.name)
    me.materials.clear()
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    # Decapitation plane: split the neck faces exactly on the cut so variants share one surface.
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=CUT_P, plane_no=CUT_N, dist=1e-6)
    bm.to_mesh(me)
    bm.free()
    me.update()
    _tag(body, D.PART_BODY)
    return body


def cut_ring(body):
    """Ordered loop of body vertices on the cut plane."""
    me = body.data
    ring = [v.index for v in me.vertices if abs((v.co - CUT_P).dot(CUT_N)) < 2e-6]
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    on = set(ring)
    adj = {i: [] for i in ring}
    for e in bm.edges:
        a, b = e.verts[0].index, e.verts[1].index
        if a in on and b in on:
            adj[a].append(b)
            adj[b].append(a)
    bm.free()
    start = ring[0]
    loop = [start]
    prev = None
    cur = start
    while True:
        nxt = [n for n in adj[cur] if n != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        if cur == start:
            break
        loop.append(cur)
    if len(loop) != len(ring):
        raise RuntimeError('neck cut is not a single loop (%d of %d vertices)' % (len(loop), len(ring)))
    return [me.vertices[i].co.copy() for i in loop]


def cut_frame():
    u = Vector((1, 0, 0)) - CUT_N * CUT_N.x
    u.normalize()
    v = CUT_N.cross(u).normalized()
    return u, v


def build_caps(ring, coll, mat):
    """Wound caps on both sides of the cut: raw tissue domed slightly out of the opening."""
    c = sum(ring, Vector()) / len(ring)
    u, v = cut_frame()
    caps = []
    for part, sgn in ((D.PART_CAP_BODY, 1.0), (D.PART_CAP_HEAD, -1.0)):
        R = 7
        verts, A, C = [], [], []
        for k in range(R):
            t = k / R
            for p in ring:
                q = c + (p - c) * (1 - t) ** 0.9 + CUT_N * sgn * 0.0028 * math.sin(0.5 * math.pi * t) ** 0.7
                verts.append(q)
                A.append(t)
                C.append((math.atan2((p - c).dot(v), (p - c).dot(u)) / math.tau) % 1.0)
        verts.append(c + CUT_N * sgn * 0.0030)
        A.append(1.0)
        C.append(0.0)
        n = len(ring)
        faces = []
        for k in range(R - 1):
            for i in range(n):
                a = k * n + i
                b = k * n + (i + 1) % n
                faces.append((a, b, b + n, a + n))
        ci = len(verts) - 1
        for i in range(n):
            faces.append(((R - 1) * n + i, (R - 1) * n + (i + 1) % n, ci))
        me_v = [Vector(p) for p in verts]
        fixed = []
        for f in faces:
            nrm = (me_v[f[1]] - me_v[f[0]]).cross(me_v[f[-1]] - me_v[f[0]])
            fixed.append(tuple(reversed(f)) if nrm.dot(CUT_N) * sgn < 0 else f)
        caps.append(_mesh('Wound cap', verts, fixed, coll, mat, part, A, C))
    return caps


def build_blood_shells(body, coll, mat):
    """Thin closed shells (solidified offsets) of the neck surface on both sides of the cut,
    painted later with alpha-tested runs of blood."""
    me = body.data
    shells = []
    u, v = cut_frame()
    for part, lo, hi in ((D.PART_BLOOD_BODY, -0.080, 0.0), (D.PART_BLOOD_HEAD, 0.0, 0.016)):
        keep = []
        for poly in me.polygons:
            ds = [(me.vertices[i].co - CUT_P).dot(CUT_N) for i in poly.vertices]
            if min(ds) >= lo - 1e-7 and max(ds) <= hi + 1e-7:
                keep.append(poly)
        index = {}
        verts, faces, A, C = [], [], [], []
        for poly in keep:
            f = []
            for i in poly.vertices:
                if i not in index:
                    vv = me.vertices[i]
                    index[i] = len(verts)
                    verts.append(vv.co + vv.normal * 0.00055)
                    d = (vv.co - CUT_P).dot(CUT_N)
                    A.append(abs(d))
                    rel = vv.co - CUT_P
                    C.append((math.atan2(rel.dot(v), rel.dot(u)) / math.tau) % 1.0)
                f.append(index[i])
            faces.append(tuple(f))
        ob = _mesh('Blood shell', verts, faces, coll, mat, part, A, C)
        sol = ob.modifiers.new('film', 'SOLIDIFY')
        sol.thickness = 0.00035
        sol.offset = -1
        sol.use_rim = True
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=sol.name)
        shells.append(ob)
    return shells


def surface_tools(objs):
    verts, polys = [], []
    for ob in objs:
        base = len(verts)
        verts += [v.co.copy() for v in ob.data.vertices]
        polys += [[base + i for i in p.vertices] for p in ob.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def _hit_side(bvh, x, z, s):
    hit = bvh.ray_cast(Vector((x, s * 0.4, z)), Vector((0, -s, 0)), 1.0)
    if hit[0] is None:
        return None
    n = hit[1].normalized()
    if n.y * s < 0:
        n = -n
    return hit[0].copy(), n


# ---------------------------------------------------------------------------------------------
# Folded wing: real stacked feathers.  (x0, z0) design side-view base, angle up from -X (deg),
# length, width, layer offset above the flank (m), tuck (base sunk under body feathers).
def wing_feathers():
    F = []
    for i in range(5):   # primaries: bottom layer, longest, tips cross over the tail
        F.append(('primary', -0.004 - 0.004 * i, 0.247 - 0.004 * i, 6.0 + 0.8 * i, 0.178 - 0.010 * i, 0.019, 0.0020 + 0.00025 * (4 - i), 0.0))
    for i in range(6):   # secondaries: stacked down the flank, lower under upper
        F.append(('secondary', 0.012 - 0.003 * i, 0.252 - 0.0085 * i, 2.5 + 1.6 * i, 0.150 - 0.009 * i, 0.027, 0.0034 - 0.00030 * i, 0.0))
    for i in range(3):   # tertials: broad, along the back edge
        F.append(('tertial', 0.018 - 0.004 * i, 0.278 - 0.008 * i, 1.0 + i, 0.118 - 0.010 * i, 0.032, 0.0044 - 0.0003 * i, 0.0))
    for i in range(5):   # greater coverts over the secondary bases
        F.append(('covert', 0.044 - 0.004 * i, 0.268 - 0.0090 * i, -3.0, 0.066, 0.031, 0.0040, 0.0040))
    for i in range(5):   # lesser coverts at the wrist, sunk into the breast/shoulder feathers
        F.append(('covert', 0.076 - 0.004 * i, 0.272 - 0.0085 * i, -6.0, 0.054, 0.029, 0.0046, 0.0050))
    return F


def build_wing(bvh, s, coll, mat):
    objs = []
    n_st, seg = 9, 6
    for kind, x0, z0, ang, L, W, off, tuck in wing_feathers():
        a = math.radians(ang)
        last = None
        centers, normals = [], []
        for k in range(n_st):
            t = k / (n_st - 1)
            x = x0 - L * t * math.cos(a)
            z = z0 + L * t * math.sin(a)
            h = _hit_side(bvh, x, z, s)
            if h is None:
                p0, n0 = last
                p = Vector((x, p0.y - s * 0.003, z))
                n = n0
            else:
                p, n = h
            last = (p, n)
            # flatter stack: smaller steps between layers so the folded wing reads soft, not tiled
            lift = 0.70 * off + 0.0018 * t * t - tuck * (1 - D.smoothstep(t / 0.40))
            centers.append(p + n * lift)
            normals.append(n)
        rings, A, C, LEN = [], [], [], []
        for k in range(n_st):
            t = k / (n_st - 1)
            tan = (centers[min(k + 1, n_st - 1)] - centers[max(k - 1, 0)]).normalized()
            n = normals[k]
            across = n.cross(tan).normalized()
            hw = 0.5 * W * (0.55 + 0.45 * math.sin(0.5 * math.pi * min(1.0, t / 0.2))) * math.sqrt(max(0.0, 1 - max(0.0, (t - 0.55) / 0.45) ** 2)) + 0.0004
            th = (0.0011 * (1 - 0.6 * t) + 0.0003) * (0.40 if kind == 'covert' else 0.60)
            camber = 0.10 if kind == 'covert' else 0.18
            ring = []
            for j in range(seg):
                ang2 = math.tau * j / seg
                cy, sy = math.cos(ang2), math.sin(ang2)
                ring.append(centers[k] + across * (hw * cy) + n * (th * sy - camber * hw * cy * cy))
                A.append(t)
                C.append(cy)
                LEN.append(L)
            rings.append(ring)
        v, f = _ring_loft(rings)
        A += [0.0, 1.0]
        C += [0.0, 0.0]
        LEN += [L, L]
        ob = _mesh('Wing feather', v, f, coll, mat, D.PART_WING, A, C, length=LEN)
        _fix_normals(ob)
        objs.append(ob)
    return objs


def build_tail(coll, mat):
    objs = []
    for i in range(-3, 4):
        yaw = math.radians(8.0 * i)
        pitch = math.radians(27 - 1.5 * abs(i))
        d = Vector((-math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), math.sin(pitch)))
        base = Vector((-0.170, 0.005 * i, 0.242 - 0.0016 * abs(i)))
        L = 0.072 - 0.0040 * abs(i)
        w = 0.0165
        side = d.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(d).normalized()
        rings, A, C, LEN = [], [], [], []
        n, seg = 12, 8
        for k in range(n + 1):
            a = k / n
            rad = w * (0.55 + 0.45 * math.sin(0.5 * math.pi * min(1.0, a / 0.25)))
            tipf = max(0.0, (a - 0.55) / 0.45) ** 2
            hw = rad * math.sqrt(max(0.0, 1 - tipf)) + 0.0004
            ht = 0.0011 * (1 - 0.6 * a) + 0.0003
            ctr = base + d * (L * a) + up * (0.010 * math.sin(math.pi * a * 0.8))
            ring = []
            for j in range(seg):
                ang = math.tau * j / seg
                cy = math.cos(ang)
                ring.append(ctr + side * (hw * cy) + up * (ht * math.sin(ang) - 0.25 * hw * cy * cy))
                A.append(a)
                C.append(cy)
                LEN.append(L)
            rings.append(ring)
        v, f = _ring_loft(rings)
        A += [0.0, 1.0]
        C += [0.0, 0.0]
        LEN += [L, L]
        objs.append(_mesh('Rectrix', v, f, coll, mat, D.PART_TAIL, A, C, length=LEN))
    return objs


def _superellipse_loft(name, stations, coll, mat, part, seg=24, e=2.6):
    rings = []
    for x, zt, zb, hw in stations:
        zc = 0.5 * (zt + zb)
        ht = 0.5 * (zt - zb)
        ring = []
        for i in range(seg):
            a = math.tau * i / seg
            ca, sa = math.cos(a), math.sin(a)
            ring.append(Vector((x, hw * math.copysign(abs(ca) ** (2 / e), ca), zc + ht * math.copysign(abs(sa) ** (2 / e), sa))))
        rings.append(ring)
    v, f = _ring_loft(rings)
    ob = _mesh(name, v, f, coll, mat, part)
    _fix_normals(ob)
    return ob


def build_bill(coll, mat):
    upper = [(0.184, 0.452, 0.419, 0.0175), (0.196, 0.447, 0.418, 0.0168), (0.208, 0.441, 0.416, 0.0160),
             (0.222, 0.433, 0.414, 0.0158), (0.236, 0.426, 0.4115, 0.0163), (0.248, 0.4215, 0.409, 0.0168),
             (0.258, 0.4185, 0.4075, 0.0166), (0.265, 0.4165, 0.4068, 0.0150), (0.270, 0.4145, 0.4068, 0.0118),
             (0.2735, 0.4122, 0.4075, 0.0070), (0.2752, 0.4102, 0.4085, 0.0022)]
    lower = [(0.190, 0.4185, 0.3985, 0.0128), (0.204, 0.4170, 0.4000, 0.0140), (0.222, 0.4148, 0.4012, 0.0146),
             (0.240, 0.4122, 0.4022, 0.0146), (0.254, 0.4100, 0.4030, 0.0140), (0.263, 0.4085, 0.4038, 0.0120),
             (0.268, 0.4078, 0.4045, 0.0080), (0.2705, 0.4072, 0.4052, 0.0030)]
    upper = [(x, zt, zb, hw * 1.12) for x, zt, zb, hw in upper]
    lower = [(x, zt, zb, hw * 1.12) for x, zt, zb, hw in lower]
    return [_superellipse_loft('Upper mandible', upper, coll, mat, D.PART_BILL_UP, seg=24, e=2.4),
            _superellipse_loft('Lower mandible', lower, coll, mat, D.PART_BILL_LO, seg=18, e=2.2)]


def build_eyes(bvh, coll, eye_mat, lid_mat):
    objs = []
    for s in (-1, 1):
        p, n = _hit_side(bvh, 0.181, 0.4405, s)
        r = 0.0056
        center = p - n * 0.0030
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=r, location=(0, 0, 0))
        eye = bpy.context.object
        eye.name = 'Eye'
        _link(eye, coll)
        q = Vector((0, 0, 1)).rotation_difference(n)
        eye.data.transform(Matrix.Translation(center) @ q.to_matrix().to_4x4())
        eye.data.materials.append(eye_mat)
        for poly in eye.data.polygons:
            poly.use_smooth = True
        pole = [((v.co - center).dot(n) / r) for v in eye.data.vertices]
        _tag(eye, D.PART_EYE, pole, [float(s)] * len(pole))
        objs.append(eye)
        bpy.ops.mesh.primitive_torus_add(major_radius=r * 0.86, minor_radius=0.0008, major_segments=16, minor_segments=6)
        lid = bpy.context.object
        lid.name = 'Eyelid ring'
        _link(lid, coll)
        lid.data.transform(Matrix.Translation(center + n * 0.0031) @ q.to_matrix().to_4x4() @ Matrix.Scale(0.86, 4, (0, 1, 0)))
        lid.data.materials.append(lid_mat)
        for poly in lid.data.polygons:
            poly.use_smooth = True
        _tag(lid, D.PART_LID)
        objs.append(lid)
    return objs


# ---------------------------------------------------------------------------------------------
def _flow(p):
    """Nearest point on the design flow curve: arc length s and unit tangent toward the tail."""
    curve = [Vector(c) for c in D.SPINE_CURVE]
    best = (1e9, 0.0, Vector((-1, 0, 0)))
    acc = 0.0
    for a, b in zip(curve, curve[1:]):
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        d = (p - (a + ab * t)).length
        if d < best[0]:
            best = (d, acc + t * ab.length, ab.normalized())
        acc += ab.length
    return best[1], best[2]


def _card_quad(p, n, d, length, width, tilt):
    """Bent two-segment card: rises off the skin at its base, then lies back down toward the tip."""
    side = n.cross(d).normalized()
    b = p - n * 0.0014 - d * (0.25 * length)
    m = b + d * (0.55 * length) + n * (0.55 * length * math.sin(tilt) + 0.0007)
    t = m + d * (0.45 * length) + n * (0.45 * length * math.sin(0.25 * tilt))
    return [b - side * (0.5 * width), b + side * (0.5 * width), m + side * (0.44 * width), m - side * (0.44 * width),
            t + side * (0.30 * width), t - side * (0.30 * width)]


def build_cards(body, occluders, coll, mat):
    """Alpha-tested contour-feather cards seeded on the body surface, plus pocket cards that
    lap over the lower edge of each folded wing."""
    rnd = random.Random(D.SEED + 5)
    me = body.data
    me.calc_loop_triangles()
    tris = list(me.loop_triangles)
    areas = np.array([t.area for t in tris])
    cdf = np.cumsum(areas) / areas.sum()
    occ = surface_tools(occluders)
    verts, faces, A, C, LEN, CARD, CN = [], [], [], [], [], [], []
    k = 0

    def add(quad, length, n):
        nonlocal k
        CN.extend([tuple(n)] * 6)
        base = len(verts)
        verts.extend(quad)
        # winding gives a face normal along +skin normal, matching the custom normals
        faces.append((base + 3, base + 2, base + 1, base))
        faces.append((base + 5, base + 4, base + 2, base + 3))
        A.extend([0.0, 0.0, 0.55, 0.55, 1.0, 1.0])
        C.extend([-1.0, 1.0, 1.0, -1.0, 1.0, -1.0])
        LEN.extend([length] * 6)
        CARD.extend([k] * 6)
        k += 1

    tries = 0
    while k < 380 and tries < 30000:
        tries += 1
        ti = int(np.searchsorted(cdf, rnd.random()))
        tri = tris[min(ti, len(tris) - 1)]
        r1, r2 = rnd.random(), rnd.random()
        if r1 + r2 > 1:
            r1, r2 = 1 - r1, 1 - r2
        vs = [me.vertices[i] for i in tri.vertices]
        p = vs[0].co * (1 - r1 - r2) + vs[1].co * r1 + vs[2].co * r2
        n = (vs[0].normal * (1 - r1 - r2) + vs[1].normal * r1 + vs[2].normal * r2).normalized()
        s, T = _flow(p)
        if s < 0.075 or (p - CUT_P).dot(CUT_N) > -0.028 or p.z < 0.118:
            continue
        if rnd.random() > D.smoothstep((s - 0.16) / 0.10):  # density fades in down the neck: no seam at the cut
            continue
        if occ.ray_cast(p + n * 0.0008, n, 0.022)[0] is not None:
            continue
        # keep cards where the silhouette breaks (back line, rump, tail coverts); thin out breast/flank/belly ~68 %
        dorsal_w = D.smoothstep((n.z - 0.25) / 0.50)
        rump_w = D.smoothstep((s - 0.40) / 0.10)
        if rnd.random() > 0.32 + 0.68 * max(dorsal_w, rump_w):
            continue
        d = T - n * T.dot(n)
        if d.length < 0.2:
            continue
        d.normalize()
        d = Quaternion(n, math.radians(rnd.uniform(-14, 14))) @ d
        L = float(np.interp(s, D.FEATHER_S, D.FEATHER_L))
        length = 1.70 * L * rnd.uniform(0.85, 1.15)
        width = 1.35 * L * rnd.uniform(0.85, 1.15)
        tilt = math.radians(0.5 + 2.0 * rnd.random())   # almost flush: a few mm of lift at most
        add(_card_quad(p, n, d, length, width, tilt), length, n)
    # pocket feathers: flank cards pointing up-and-back over the lower wing edge
    for s in (-1, 1):
        for i in range(14):
            x = 0.055 - 0.0145 * i
            z = 0.214 + 0.0035 * i - 0.00035 * i * i + rnd.uniform(-0.003, 0.003)
            h = _hit_side(surface_tools([body]), x, z - 0.010, s)
            if h is None:
                continue
            p, n = h
            d = Vector((-0.80, 0, 0.60))
            d = (d - n * d.dot(n)).normalized()
            length = 0.034 * rnd.uniform(0.85, 1.1)
            add(_card_quad(p, n, d, length * 1.15, 0.032 * rnd.uniform(0.9, 1.1), math.radians(6 + 2 * rnd.random())), length * 1.15, n)
    ob = _mesh('Contour feather cards', verts, faces, coll, mat, D.PART_CARD, A, C, length=LEN, card=CARD)
    # cards shade with the skin normal they grow from (set as custom normals after the posture transform)
    ob.data.attributes.new('duck_cn', 'FLOAT_VECTOR', 'POINT')
    ob.data.attributes['duck_cn'].data.foreach_set('vector', [x for v in CN for x in v])
    return ob


# ---------------------------------------------------------------------------------------------
def build_leg(s, coll, mat):
    """Short, thick Pekin legs (final space)."""
    objs = []
    y = s * D.LEG_Y
    knee = Vector((D.KNEE[0], y, D.KNEE[1]))
    ankle = Vector((D.ANKLE[0], y, D.ANKLE[1]))
    F = Vector((D.FOOT[0], y, D.FOOT[1]))
    pts = [knee, knee.lerp(ankle, 0.5), ankle + Vector((0.001, 0, 0.003)), ankle.lerp(F, 0.33), ankle.lerp(F, 0.66), F + Vector((0.002, 0, -0.002))]
    radii = [0.0128, 0.0112, 0.0098, 0.0090, 0.0085, 0.0079]
    objs.append(tube('Tarsus', pts, radii, coll, mat, D.PART_LEG, seg=12, flat=0.80))
    toe_out = math.radians(9) * s
    tips = []
    for ang, L in [(-26, 0.049), (0, 0.061), (25, 0.056)]:
        yaw = toe_out + math.radians(ang) * s
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        tp, tr = [], []
        for k in range(9):
            t = k / 8
            p = Vector((F.x, F.y, 0)) + d * (0.003 + L * t)
            p.z = 0.0105 - 0.0078 * (t ** 0.7) + 0.0006 * math.sin(math.pi * t)
            tp.append(p)
            knuckle = 1 + 0.10 * max(0.0, math.cos(t * math.pi * 6)) * (1 - t)
            tr.append((0.0042 - 0.0019 * t) * knuckle)
        objs.append(tube('Toe', tp, tr, coll, mat, D.PART_TOE, seg=8, flat=1.15))
        tip = tp[-1]
        tips.append((yaw, L))
        claw = [tip - d * 0.0012, tip + d * 0.0030 + Vector((0, 0, -0.0004)), tip + d * 0.0056 + Vector((0, 0, -0.0016))]
        objs.append(tube('Claw', claw, [0.0018, 0.0013, 0.0003], coll, mat, D.PART_CLAW, seg=6))
    d = Vector((-0.92, -0.35 * s, 0)).normalized()
    hb = Vector((F.x - 0.002, F.y, 0.012))
    objs.append(tube('Hallux', [hb, hb + d * 0.006 + Vector((0, 0, -0.003)), hb + d * 0.012 + Vector((0, 0, -0.006))], [0.0029, 0.0023, 0.0013], coll, mat, D.PART_TOE, seg=6))
    (y0, L0), (y1, L1), (y2, L2) = tips
    nth, nr = 16, 7
    verts, faces = [], []
    for it in range(nth + 1):
        u = it / nth
        w = u / 0.5 if u <= 0.5 else (u - 0.5) / 0.5
        yaw = D.lerp(y0, y1, w) if u <= 0.5 else D.lerp(y1, y2, w)
        Lr = D.lerp(L0, L1, w) if u <= 0.5 else D.lerp(L1, L2, w)
        dip = math.sin(math.pi * w)
        R = (Lr * 0.90) * (1 - 0.20 * dip)
        dd = Vector((math.cos(yaw), math.sin(yaw), 0))
        for ir in range(nr + 1):
            t = ir / nr
            r = 0.004 + R * t
            p = Vector((F.x, F.y, 0)) + dd * r
            p.z = 0.0105 - 0.0078 * (min(1, r / max(Lr, 1e-6)) ** 0.7) - 0.0010 * dip * t
            verts.append(p)
    for it in range(nth):
        for ir in range(nr):
            a = it * (nr + 1) + ir
            faces.append((a, a + nr + 1, a + nr + 2, a + 1))
    if s < 0:
        faces = [tuple(reversed(f)) for f in faces]
    web = _mesh('Web', verts, faces, coll, mat, D.PART_WEB)
    sol = web.modifiers.new('membrane', 'SOLIDIFY')
    sol.thickness = 0.0013
    sol.offset = 0
    bpy.ops.object.select_all(action='DESELECT')
    web.select_set(True)
    bpy.context.view_layer.objects.active = web
    bpy.ops.object.modifier_apply(modifier=sol.name)
    _fix_normals(web)
    objs.append(web)
    return objs


def _to_final(ob, design=True):
    me = ob.data
    if 'duck_dpos' not in me.attributes:
        me.attributes.new('duck_dpos', 'FLOAT_VECTOR', 'POINT')
    co = [0.0] * (len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    me.attributes['duck_dpos'].data.foreach_set('vector', co)
    if design:
        for v in me.vertices:
            v.co = Vector(D.final(v.co))
        if 'duck_cn' in me.attributes:
            R = D.posture_matrix().to_3x3()
            cn = me.attributes['duck_cn'].data
            for i in range(len(cn)):
                cn[i].vector = (R @ Vector(cn[i].vector)).normalized()
    me.update()


def build_geometry(coll, mats):
    feather, bill, feet, eye = mats
    body = build_body(coll, feather)
    bvh = surface_tools([body])
    ring = cut_ring(body)
    design = [body]
    for s in (1, -1):
        design += build_wing(bvh, s, coll, feather)
    tail = build_tail(coll, feather)
    design += tail
    design += build_bill(coll, bill)
    design += build_eyes(bvh, coll, eye, feather)
    occluders = [o for o in design if o is not body]
    design.append(build_cards(body, occluders, coll, feather))
    design += build_caps(ring, coll, feather)
    design += build_blood_shells(body, coll, feather)
    legs = []
    for s in (1, -1):
        legs += build_leg(s, coll, feet)
    for ob in design:
        _to_final(ob, True)
    for ob in legs:
        _to_final(ob, False)
    body.data.materials.clear()
    for m in mats:
        body.data.materials.append(m)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in design + legs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    ob = body
    ob.name = D.LOD0
    ob.data.name = D.LOD0
    me = ob.data
    fpart = [0] * len(me.polygons)
    me.attributes['duck_fpart'].data.foreach_get('value', fpart)
    for poly, fp in zip(me.polygons, fpart):
        poly.material_index = D.PART_MATERIAL[fp]
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bad = [f for f in bm.faces if f.calc_area() < 1e-10]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    zmin = min(v.co.z for v in bm.verts)
    if abs(zmin) > 0.003:
        raise RuntimeError('feet not on the ground: z min %.4f' % zmin)
    for v in bm.verts:
        v.co.z -= zmin
    bm.to_mesh(me)
    bm.free()
    me.update()
    set_card_normals(ob)
    return ob


def set_card_normals(ob):
    me = ob.data
    if 'duck_cn' not in me.attributes:
        return
    cn = np.zeros(len(me.vertices) * 3, np.float32)
    me.attributes['duck_cn'].data.foreach_get('vector', cn)
    cn = cn.reshape(-1, 3)
    corner = np.zeros(len(me.loops) * 3, np.float32)
    for i, c in enumerate(me.corner_normals):
        corner[3 * i:3 * i + 3] = c.vector
    corner = corner.reshape(-1, 3)
    lv = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    use = np.linalg.norm(cn[lv], axis=1) > 0.5
    corner[use] = cn[lv][use]
    for p in me.polygons:
        p.use_smooth = True
    me.normals_split_custom_set([tuple(x) for x in corner])
