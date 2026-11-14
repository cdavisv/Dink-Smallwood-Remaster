"""Garment construction helpers: implicit cuts, cloth settle, metric chart UVs, lips, lofts."""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
from prlib import *

def implicit_cut(o, f, keep_negative=True):
    """Cut mesh along f(P)=0 exactly (edge splits) and delete the f>0 side. f is vectorised: (n,3) -> (n,)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    arr = np.asarray(f(np.array([v.co[:] for v in bm.verts], float)), float)
    vals = {v: float(arr[i]) for i, v in enumerate(bm.verts)}
    newv = set()
    for e in list(bm.edges):
        a, b = e.verts; va, vb = vals[a], vals[b]
        if va * vb < 0:
            t = va / (va - vb)
            if t < .08: vals[a] = 0.0; newv.add(a); continue
            if t > .92: vals[b] = 0.0; newv.add(b); continue
            ne, nv = bmesh.utils.edge_split(e, a, t); vals[nv] = 0.0; newv.add(nv)
    for face in list(bm.faces):
        vs = [v for v in face.verts if v in newv]
        if len(vs) == 2:
            fv = list(face.verts); i, j = fv.index(vs[0]), fv.index(vs[1])
            if abs(i - j) not in (1, len(fv) - 1):
                try: bmesh.utils.face_split(face, vs[0], vs[1])
                except Exception: pass
    bm.faces.ensure_lookup_table()
    cen = np.array([fc.calc_center_median()[:] for fc in bm.faces], float)
    fcv = np.asarray(f(cen), float)
    dead = [fc for i, fc in enumerate(bm.faces) if (fcv[i] > 0) == keep_negative]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update()

def boundary_loops(bm):
    """Ordered boundary vertex loops."""
    bedges = [e for e in bm.edges if e.is_boundary]
    nxt = {}
    for e in bedges:
        l = e.link_loops[0]; nxt[l.vert] = l.link_loop_next.vert
    loops = []; seen = set()
    for v0 in list(nxt):
        if v0 in seen: continue
        loop = [v0]; seen.add(v0); v = nxt[v0]
        while v is not v0 and v in nxt and v not in seen:
            loop.append(v); seen.add(v); v = nxt[v]
        loops.append(loop)
    return loops

def tidy_rim(o, sharp=75.0, passes=3):
    """After a cut: drop the slivers it leaves on an open border. A border triangle whose other two edges are
    both open (an ear) is a tab that sticks out of the rim; a border vertex where the rim turns back on itself
    by more than `sharp` degrees is the tip of one. Both go, and loose pieces smaller than 40 faces with them."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    for _ in range(passes):
        dead = [f for f in bm.faces if sum(e.is_boundary for e in f.edges) >= 2]
        for v in bm.verts:
            be = [e for e in v.link_edges if e.is_boundary]
            if len(be) != 2: continue
            a = be[0].other_vert(v).co - v.co; b = be[1].other_vert(v).co - v.co
            if a.length < 1e-9 or b.length < 1e-9: continue
            if math.degrees(a.angle(b)) < 180 - sharp and len(v.link_faces) <= 2: dead.extend(v.link_faces)
        if not dead: break
        bmesh.ops.delete(bm, geom=list(set(dead)), context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    seen = set()
    for f0 in list(bm.faces):
        if f0 in seen: continue
        isl = [f0]; seen.add(f0); st = [f0]
        while st:
            g_ = st.pop()
            for e in g_.edges:
                for h in e.link_faces:
                    if h not in seen: seen.add(h); isl.append(h); st.append(h)
        if len(isl) < 40: bmesh.ops.delete(bm, geom=isl, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # a cut that passes within a hair of an old vertex leaves two rim vertices almost on one spot; their lip faces
    # would coincide (two faces on one edge after the assembly merges them)
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.is_boundary], dist=.0005)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < 1e-10], context='FACES')
    bm.to_mesh(o.data); bm.free(); o.data.update()

def clear_of_skin(o, skin_bvh, clear=.004, reach=.03, mask=None, spread=4):
    """Cloth never lies in or under the skin: every vertex nearer than `clear` to the skin's outer side (or inside it,
    up to `reach`) is pushed out along the skin normal. The push is shared with the neighbours before it is applied
    (a vertex moved alone leaves a tooth). mask(co) -> bool array limits it to a region."""
    c = co_np(o.data); push = np.zeros((len(c), 3)); n_moved = 0; worst = 0.0
    idx = np.nonzero(mask(c))[0] if mask is not None else range(len(c))
    for i in idx:
        loc, nrm, _, dist = skin_bvh.find_nearest(Vector(c[i]), reach)
        if loc is None: continue
        sd = float((Vector(c[i]) - loc).dot(nrm))
        if sd < clear: push[i] = np.array(nrm) * (clear - sd); n_moved += 1; worst = max(worst, clear - sd)
    if n_moved:
        bm_ = bmesh.new(); bm_.from_mesh(o.data); bm_.verts.ensure_lookup_table()
        nbr = [[e.other_vert(v).index for e in v.link_edges] for v in bm_.verts]; bm_.free()
        raw = push.copy(); need = np.linalg.norm(raw, axis=1)
        for _ in range(spread):
            avg = np.array([(push[i] + push[nb].sum(0)) / (1 + len(nb)) if nb else push[i] for i, nb in enumerate(nbr)])
            push = np.where((np.linalg.norm(avg, axis=1) > need)[:, None], avg, raw)
        set_co(o.data, c + push)
    log('cleared of the skin', o.name, 'vertices', n_moved, 'largest push mm', round(worst * 1000, 1))

def smooth_boundary(o, it=4, lam=.5):
    bm = bmesh.new(); bm.from_mesh(o.data)
    for loop in boundary_loops(bm):
        n = len(loop)
        if n < 8: continue
        for _ in range(it):
            P = [v.co.copy() for v in loop]
            for i, v in enumerate(loop): v.co = P[i] * (1 - lam) + (P[i - 1] + P[(i + 1) % n]) * (lam / 2)
    bm.to_mesh(o.data); bm.free(); o.data.update()

def add_lips(o, thickness=.003, lip=.012, select=None, uv_layers=True):
    """Give open borders thickness: rim down along -normal, then a strip turned inside.
    select(center)->bool chooses which boundary loops get a lip."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    uvls = list(bm.loops.layers.uv.values())
    for loop in boundary_loops(bm):
        if len(loop) < 3: continue
        cen = sum((v.co for v in loop), Vector()) / len(loop)
        if select and not select(cen): continue
        n = len(loop)
        # inward direction per vertex: away from boundary into the surface
        r1 = []; r2 = []
        for i, v in enumerate(loop):
            t = (loop[(i + 1) % n].co - loop[i - 1].co)
            if t.length < 1e-9: t = Vector((1, 0, 0))
            t.normalize(); nrm = v.normal
            inw = nrm.cross(t); 
            # orient inward using the adjacent faces (all of them: the first alone may be a sliver lying along the rim)
            fc = sum((lf.calc_center_median() for lf in v.link_faces), Vector()) / len(v.link_faces) - v.co
            if inw.dot(fc) < 0: inw = -inw
            r1.append((v, nrm, inw))
        # the turned-in strip runs along the rim's own smoothed direction, and is shorter where the rim bends back on
        # itself (the point of a V neckline): strips that cross there came out of the leather as pale spikes
        INW = [q[2].copy() for q in r1]
        for _ in range(3): INW = [(INW[i - 1] + INW[i] * 2 + INW[(i + 1) % n]).normalized() if (INW[i - 1] + INW[i] * 2 + INW[(i + 1) % n]).length > 1e-9 else INW[i] for i in range(n)]
        rr = r1; r1 = []; r2 = []
        for i, (v, nrm, inw0) in enumerate(rr):
            a_ = loop[i - 1].co - v.co; b_ = loop[(i + 1) % n].co - v.co
            bend = a_.angle(b_) if a_.length > 1e-9 and b_.length > 1e-9 else math.pi      # pi on a straight rim
            concave = (a_ + b_).dot(INW[i]) > 0                                            # the rim closes in on its own strip
            k = max(.25, min(1.0, bend / math.pi)) if concave else 1.0
            a = bm.verts.new(v.co - nrm * thickness); b = bm.verts.new(v.co - nrm * thickness + INW[i] * lip * k - nrm * .0005)
            r1.append(a); r2.append(b)
        for i in range(n):
            j = (i + 1) % n
            v0, v1 = loop[i], loop[j]
            # find loop uv of v0 on its boundary face for uv copy
            try:
                f1 = bm.faces.new((v1, v0, r1[i], r1[j])); f2 = bm.faces.new((r1[j], r1[i], r2[i], r2[j]))
            except ValueError: continue
            f1.smooth = True; f2.smooth = True
            src = {}
            for vv in (v0, v1):
                for l in vv.link_loops:
                    if l.face not in (f1, f2): src[vv] = l; break
            for uvl in uvls:
                for f in (f1, f2):
                    for l in f.loops:
                        base = v0 if l.vert in (v0, r1[i], r2[i]) else v1
                        if base in src: l[uvl].uv = src[base][uvl].uv
            mi = src[v0].face.material_index if v0 in src else 0
            f1.material_index = mi; f2.material_index = mi
    bm.normal_update(); bm.to_mesh(o.data); bm.free(); o.data.update()

def loft(name, rings, closed=True, cap_end=False, cap_start=False):
    """rings: list of lists of points (same count). Returns object with grid UVs in metres (UVMetric)."""
    nr = len(rings); nc = len(rings[0])
    verts = [p for r in rings for p in r]; faces = []
    cols = nc if closed else nc - 1
    for i in range(nr - 1):
        for j in range(cols):
            a = i * nc + j; b = i * nc + (j + 1) % nc; c = (i + 1) * nc + (j + 1) % nc; d = (i + 1) * nc + j
            faces.append((a, b, c, d))
    o = new_obj(name, verts, faces)
    me = o.data; uv = me.uv_layers.new(name='UVMetric')
    P = np.array(verts, float).reshape(nr, nc, 3)
    # arclength around (per ring, averaged) and along
    seg = np.linalg.norm(np.roll(P, -1, 1) - P, axis=2)
    ucum = np.concatenate([np.zeros((nr, 1)), np.cumsum(seg, 1)], 1)  # nr x nc+1
    umean = ucum.mean(0)
    vseg = np.linalg.norm(P[1:] - P[:-1], axis=2).mean(1); vcum = np.concatenate([[0], np.cumsum(vseg)])
    for p in me.polygons:
        i = p.vertices[0] // nc; j = p.vertices[0] % nc
        cu = [(umean[j], vcum[i]), (umean[j + 1], vcum[i]), (umean[j + 1], vcum[i + 1]), (umean[j], vcum[i + 1])]
        for li, c in zip(p.loop_indices, cu): uv.data[li].uv = c
    if cap_end or cap_start:
        bm = bmesh.new(); bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        uvl = bm.loops.layers.uv[0]
        ringsv = {idx: [bm.verts[idx * nc + j] for j in range(nc)] for idx in (0, nr - 1)}
        for flag, idx in ((cap_start, 0), (cap_end, nr - 1)):
            if not flag: continue
            ring = ringsv[idx]
            cen = sum((v.co for v in ring), Vector()) / nc; cv = bm.verts.new(cen)
            for j in range(nc):
                tri = (ring[j], ring[(j + 1) % nc], cv) if idx else (ring[(j + 1) % nc], ring[j], cv)
                f = bm.faces.new(tri)
                for l in f.loops: l[uvl].uv = (l.vert.co.x - cen.x + .5 * umean[-1], l.vert.co.y - cen.y + vcum[idx])
        bm.normal_update(); bm.to_mesh(me); bm.free()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    smooth_shade(o); return o

class Poly:
    """Polyline axis with projection: returns (arclength s, radial vector, local frame)."""
    def __init__(self, pts, ref=(0, -1, 0)):
        self.p = [Vector(p) for p in pts]; self.ref = Vector(ref)
        self.len = [(self.p[i + 1] - self.p[i]).length for i in range(len(self.p) - 1)]
        self.cum = [0]
        for l in self.len: self.cum.append(self.cum[-1] + l)
    def project(self, q):
        q = Vector(q); best = None
        for i in range(len(self.p) - 1):
            a, b = self.p[i], self.p[i + 1]; d = (b - a) / self.len[i]
            t = (q - a).dot(d)
            tc = t
            if i > 0: tc = max(tc, 0)
            if i < len(self.p) - 2: tc = min(tc, self.len[i])
            c = a + d * tc; dist = (q - c).length
            if best is None or dist < best[0]: best = (dist, self.cum[i] + tc, q - c, d)
        return best  # dist, s, radial, axis dir
    def frame(self, d):
        x = self.ref - d * self.ref.dot(d); x.normalize(); y = d.cross(x); return x, y
    def angle(self, q):
        dist, s, rad, d = self.project(q); x, y = self.frame(d)
        return s, math.atan2(rad.dot(y), rad.dot(x)), dist
    def point(self, s):
        for i in range(len(self.len)):
            if s <= self.cum[i + 1] or i == len(self.len) - 1:
                d = (self.p[i + 1] - self.p[i]) / self.len[i]; return self.p[i] + d * (s - self.cum[i]), d

def chart_uv(o, classify, charts, layer='UVMetric'):
    """Vectorised metric chart UVs. classify(centers, normals) -> int array of chart ids.
    charts: id -> ('cyl', pts, ref, radius)  u = angle*radius (unwrapped about the face centre), v = -s
                  ('planar', origin, uaxis, vaxis)"""
    me = o.data; nl = len(me.loops); npoly = len(me.polygons)
    uv = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    att = me.attributes.get('chart') or me.attributes.new('chart', 'INT', 'FACE')
    co = co_np(me)
    lv = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
    ltot = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_total', ltot)
    lstart = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_start', lstart)
    cen = np.empty(npoly * 3, np.float32); me.polygons.foreach_get('center', cen); cen = cen.reshape(-1, 3).astype(float)
    nor = np.empty(npoly * 3, np.float32); me.polygons.foreach_get('normal', nor); nor = nor.reshape(-1, 3).astype(float)
    cid = np.asarray(classify(cen, nor), np.int32)
    srt = np.argsort(lstart); face_of_loop = np.repeat(srt, ltot[srt])
    out = np.zeros((nl, 2), np.float32)
    P = co[lv]; lc = cid[face_of_loop]
    for c, spec in charts.items():
        m = lc == c
        if not m.any(): continue
        if spec[0] == 'cyl':
            _, pts, ref, rad = spec
            s, a, _d = poly_params(P[m], pts, ref); s0, a0, _d0 = poly_params(cen[face_of_loop[m]], pts, ref)
            da = (a - a0 + np.pi) % (2 * np.pi) - np.pi
            out[m, 0] = (a0 + da) * rad; out[m, 1] = -s
        else:
            _, org, ua, va = spec; d = P[m] - np.asarray(org, float)
            out[m, 0] = d @ np.asarray(ua, float); out[m, 1] = d @ np.asarray(va, float)
    uv.data.foreach_set('uv', out.ravel())
    att.data.foreach_set('value', cid)
    me.update()

def settle_cloth(o, colliders, pin_group, frames=30, grow=.05, bend=.4, stiff=12, quality=6, mass=.25, gravity=1.0, coll_dist=.004):
    sc = bpy.context.scene
    sc.frame_set(1)
    for c in colliders:
        m = c.modifiers.new('col', 'COLLISION'); c.collision.thickness_outer = .003; c.collision.thickness_inner = .01; c.collision.cloth_friction = 8
    m = o.modifiers.new('cloth', 'CLOTH'); s = m.settings
    s.quality = quality; s.mass = mass; s.tension_stiffness = stiff; s.compression_stiffness = stiff; s.shear_stiffness = stiff * .5; s.bending_stiffness = bend
    s.tension_damping = 5; s.compression_damping = 5; s.shear_damping = 5; s.bending_damping = .5; s.air_damping = 3
    s.vertex_group_mass = pin_group; s.pin_stiffness = 1.0
    s.shrink_min = -grow; s.shrink_max = -grow
    s.effector_weights.gravity = gravity
    cs = m.collision_settings; cs.use_collision = True; cs.distance_min = coll_dist; cs.collision_quality = 3; cs.use_self_collision = False
    m.point_cache.frame_start = 1; m.point_cache.frame_end = frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg)
    co = np.array([v.co[:] for v in ev.data.vertices])
    o.modifiers.remove(m)
    for c in colliders: c.modifiers.remove(c.modifiers['col'])
    sc.frame_set(1)
    set_co(o.data, co)
    return co

def laplacian_smooth(o, mask=None, it=2, lam=.5):
    me = o.data; co = co_np(me); n = len(co)
    e = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
    for _ in range(it):
        acc = np.zeros_like(co); cnt = np.zeros(n)
        np.add.at(acc, e[:, 0], co[e[:, 1]]); np.add.at(acc, e[:, 1], co[e[:, 0]]); np.add.at(cnt, e[:, 0], 1); np.add.at(cnt, e[:, 1], 1)
        avg = acc / np.maximum(cnt, 1)[:, None]; w = lam if mask is None else (lam * mask)[:, None]
        co = co + (avg - co) * w
    set_co(me, co)

def vgroup(o, name, weights):
    g = o.vertex_groups.get(name) or o.vertex_groups.new(name=name)
    for i, w in enumerate(weights):
        if w > 0: g.add([i], float(min(1, w)), 'REPLACE')
    return g

def sstep(a, b, x):
    t = np.clip((np.asarray(x) - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- numpy helpers
def _hash(i, j, k, seed):
    h = (i * 374761393 + j * 668265263 + k * 2147483647 + seed * 974711) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)

def vnoise(p, scale=1.0, seed=0):
    """Smooth value noise in [0,1], p: (n,3) array."""
    q = np.asarray(p, float) * scale + 100.0
    i = np.floor(q).astype(np.int64); f = q - i; f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out

def fbm(p, scale=1.0, octaves=4, seed=0):
    a = 0; amp = 1; tot = 0
    for o in range(octaves):
        a = a + amp * vnoise(p, scale * 2 ** o, seed + o * 17); tot += amp; amp *= .5
    return a / tot

def ridge(ph, sharp=2.2):
    return (.5 + .5 * np.cos(ph)) ** sharp - .3

def poly_params(P, pts, ref):
    """Vectorised projection of points P (n,3) on polyline pts. Returns s, theta, dist."""
    P = np.asarray(P, float); pts = [np.asarray(p, float) for p in pts]; ref = np.asarray(ref, float)
    best_d = np.full(len(P), 1e9); S = np.zeros(len(P)); TH = np.zeros(len(P)); cum = 0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = np.linalg.norm(b - a); d = (b - a) / L
        t = (P - a) @ d; tc = t.copy()
        if i > 0: tc = np.maximum(tc, 0)
        if i < len(pts) - 2: tc = np.minimum(tc, L)
        c = a + tc[:, None] * d; rad = P - c; dist = np.linalg.norm(rad, axis=1)
        x = ref - d * (ref @ d); x /= np.linalg.norm(x); y = np.cross(d, x)
        th = np.arctan2(rad @ y, rad @ x)
        m = dist < best_d
        best_d[m] = dist[m]; S[m] = cum + tc[m]; TH[m] = th[m]
        cum += L
    return S, TH, best_d

def pack_charts(objs, size, margin_px=12, layer_src='UVMetric', layer_dst='UVMap', rotate=True):
    """Shelf-pack every (object, chart id) bbox into 0-1 at one common texel density. Returns px per metre."""
    items = []; cache = {}
    for o in objs:
        me = o.data; nl = len(me.loops); npoly = len(me.polygons)
        cid = np.empty(npoly, np.int32); me.attributes['chart'].data.foreach_get('value', cid)
        uv = np.empty(nl * 2, np.float32); me.uv_layers[layer_src].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2).astype(float)
        ltot = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_total', ltot)
        lstart = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_start', lstart)
        srt = np.argsort(lstart); fol = np.repeat(srt, ltot[srt]); lc = cid[fol]
        cache[o.name] = (uv, lc); cache[o.name + '/dst'] = np.zeros_like(uv)
        scale = float(o.get('texel_scale', 1.0))
        for c in np.unique(lc):
            m = lc == c; b = [uv[m, 0].min(), uv[m, 1].min(), uv[m, 0].max(), uv[m, 1].max()]
            items.append(dict(o=o, cid=int(c), b=b, w=(b[2] - b[0]) * scale, h=(b[3] - b[1]) * scale, scale=scale))
    def try_pack(ppm, mode=0):
        """MaxRects-lite: skyline shelves with per-item best orientation; mode picks the sort key."""
        m = margin_px / size
        key = [lambda it: -max(it['w'], it['h']), lambda it: -(it['w'] * it['h']), lambda it: -min(it['w'], it['h'])][mode % 3]
        its = sorted(items, key=key)
        free = [(m, m, 1 - 2 * m, 1 - 2 * m)]; res = []     # guillotine free rectangles
        for it in its:
            w0, h0 = it['w'] * ppm / size + m, it['h'] * ppm / size + m; best = None
            for fi, (fx, fy, fw, fh) in enumerate(free):
                for rot in ((False, True) if rotate else (False,)):
                    w, h = (h0, w0) if rot else (w0, h0)
                    if w <= fw and h <= fh:
                        score = min(fw - w, fh - h)
                        if best is None or score < best[0]: best = (score, fi, rot, w, h)
            if best is None: return None
            _, fi, rot, w, h = best; fx, fy, fw, fh = free.pop(fi)
            res.append((it, fx, fy, rot))
            if fw - w > fh - h: free += [(fx + w, fy, fw - w, fh), (fx, fy + h, w, fh - h)]
            else: free += [(fx + w, fy, fw - w, h), (fx, fy + h, fw, fh - h)]
        return res
    best = (0, None)
    for mode in range(3):
        lo, hi = 50.0, 40000.0
        for _ in range(36):
            mid = (lo + hi) / 2
            if try_pack(mid, mode): lo = mid
            else: hi = mid
        if lo > best[0]: best = (lo, mode)
    if best[1] is None or try_pack(best[0], best[1]) is None:
        bad = [(it['o'].name, it['cid']) for it in items if not (np.isfinite(it['w']) and np.isfinite(it['h']))]
        if bad: raise RuntimeError('pack_charts: charts with non-finite UVs: ' + str(bad))
        big = sorted(items, key=lambda it: -max(it['w'], it['h']))[:6]
        raise RuntimeError('pack_charts: the charts do not fit at any density; largest (object, chart, w m, h m): ' + str([(it['o'].name, it['cid'], round(it['w'], 3), round(it['h'], 3)) for it in big]))
    ppm = best[0]; res = try_pack(ppm, best[1])
    for it, x, y, rot in res:
        o = it['o']; uv, lc = cache[o.name]; b = it['b']; k = ppm * it['scale'] / size
        m = lc == it['cid']; dst = cache[o.name + '/dst']
        du = (uv[m, 0] - b[0]) * k; dv = (uv[m, 1] - b[1]) * k
        if rot: dst[m, 0] = x + dv; dst[m, 1] = y + du
        else: dst[m, 0] = x + du; dst[m, 1] = y + dv
    for o in objs:
        me = o.data
        l = me.uv_layers.get(layer_dst) or me.uv_layers.new(name=layer_dst)
        me.uv_layers[layer_dst].data.foreach_set('uv', cache[o.name + '/dst'].astype(np.float32).ravel())
        me.uv_layers.active = me.uv_layers[layer_dst]; me.uv_layers[layer_dst].active_render = True
        o['px_per_m'] = ppm * o.get('texel_scale', 1.0)
    return ppm
