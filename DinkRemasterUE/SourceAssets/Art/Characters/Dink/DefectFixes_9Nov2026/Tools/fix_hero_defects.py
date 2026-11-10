"""Hero defect fixes of 9 Nov 2026 (owner report: chest bumps, floating buckle, wrist cuffs).

blender -b <SK_Dink.blend | SK_Dink_Hands.blend> -P fix_hero_defects.py -- <report.json> [--save]

Works on every <name>_LOD0..3 mesh of the file, keeps the 89-bone rig, vertex/face counts,
UVs, material slots and every vertex outside the three fixed regions bit-identical:
  * chest: the shirt was the body offset 12 mm along its normals; the MakeHuman nipple and
    lower-pectoral relief survived the drape smoothing as two dimples. Normal-direction Taubin
    smoothing over the front chest window removes them (no tangential slide, so the cloth UVs
    stay put; no shrinkage).
  * buckle: the five iron boxes were placed 39 mm in front of the body, the belt only 18 mm,
    leaving a 15 mm air gap. The rigid buckle moves back along +Y until its back face sits
    0.6 mm into the belt's outer surface, and takes the belt's interpolated weights.
  * wrists: the turned cuff was a separate ring 14 mm off the wrist skin with the sleeve end
    loose above it (dark slot between cuff and wrist, sleeve hole showing). The cuff now hugs
    the wrist (2.5 mm at the hand edge opening to 9.5 mm at its top), the sleeve end tapers
    inside it, and both take the skin's weights near the wrist so they move with it.
"""
import bpy, bmesh, json, sys, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index('--') + 1:]
REPORT = argv[0]
SAVE = '--save' in argv
arm = bpy.data.objects['Armature']
meshes = sorted([o for o in bpy.data.objects if o.type == 'MESH' and '_LOD' in o.name], key=lambda o: o.name)
WARDROBE, SKIN = 4, 0
from pathlib import Path
_src = Path(bpy.data.filepath).resolve()
_proj = next((q for q in _src.parents if (q / 'DinkRemaster.uproject').exists()), _src.parent)
report = {'file': str(_src.relative_to(_proj)), 'meshes': []}

def islands(me):
    parent = np.arange(len(me.vertices))
    def find(i):
        root = i
        while parent[root] != root: root = parent[root]
        while parent[i] != root: parent[i], i = root, parent[i]
        return root
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b: parent[a] = b
    return np.array([find(i) for i in range(len(me.vertices))])

def smoothstep(t):
    t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)

def weights_of(ob, i):
    names = {g.index: g.name for g in ob.vertex_groups}
    return {names[g.group]: g.weight for g in ob.data.vertices[i].groups if g.weight > 1e-6}

def set_weights(ob, i, w):
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    total = sum(v for _, v in top)
    for g in ob.vertex_groups: g.remove([i])
    for name, v in top: ob.vertex_groups[name].add([i], v / total, 'REPLACE')

def idw_weights(ob, co, candidates, p, k=3):
    d = np.linalg.norm(co[candidates] - np.array(p), axis=1)
    order = np.argsort(d)[:k]; acc = {}
    for j in order:
        f = 1.0 / max(d[j], 1e-5)
        for name, v in weights_of(ob, int(candidates[j])).items(): acc[name] = acc.get(name, 0) + f * v
    return acc

def blend(wa, wb, t):
    out = {}
    for name in set(wa) | set(wb): out[name] = (1 - t) * wa.get(name, 0) + t * wb.get(name, 0)
    return out

for ob in meshes:
    me = ob.data
    before_co = np.array([v.co for v in me.vertices]); co = before_co.copy()
    lab = islands(me)
    vmat = np.full(len(me.vertices), -1)
    for p in me.polygons:
        for vi in p.vertices: vmat[vi] = p.material_index
    groups = {}
    for i, l in enumerate(lab): groups.setdefault(l, []).append(i)
    isl = {l: np.array(ix) for l, ix in groups.items()}
    def mat_of(ix):
        m = vmat[ix]; m = m[m >= 0]
        return np.bincount(m, minlength=5).argmax() if len(m) else -1
    ward = {l: ix for l, ix in isl.items() if mat_of(ix) == WARDROBE}
    shirt_l = max((l for l, ix in ward.items() if co[ix][:, 2].max() > 1.5 and np.ptp(co[ix][:, 0]) > 0.8), key=lambda l: len(ward[l]))
    belt_l = max((l for l, ix in ward.items() if co[ix][:, 2].min() > 0.99 and co[ix][:, 2].max() < 1.06 and np.ptp(co[ix][:, 0]) > 0.25), key=lambda l: len(ward[l]))
    shirt, belt = ward[shirt_l], ward[belt_l]
    belt_front = co[belt][:, 1].min()
    buckle = np.concatenate([ix for l, ix in ward.items() if l != belt_l and np.abs(co[ix][:, 0]).max() < 0.04
                             and co[ix][:, 2].min() > 0.995 and co[ix][:, 2].max() < 1.055 and co[ix][:, 1].max() < belt_front - 0.004])
    skin = np.where(vmat == SKIN)[0]
    entry = {'mesh': ob.name, 'vertices': len(me.vertices), 'faces': len(me.polygons)}

    # ---- buckle: back face onto the belt's outer surface --------------------------------
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    belt_set = set(belt.tolist())
    belt_faces = [f for f in bm.faces if all(v.index in belt_set for v in f.verts)]
    belt_tree = BVHTree.FromPolygons([tuple(co[v.index]) for v in bm.verts], [[v.index for v in f.verts] for f in belt_faces], all_triangles=False)
    back_y = co[buckle][:, 1].max()
    back = buckle[co[buckle][:, 1] > back_y - 0.0015]
    gaps = []
    for i in back:
        hit = belt_tree.ray_cast(Vector(co[i]), Vector((0, 1, 0)), 0.1)
        if hit[0] is not None: gaps.append(hit[3])
    if not gaps: raise RuntimeError(ob.name + ': buckle back face does not see the belt')
    dy = min(gaps) + 0.0006
    co[buckle, 1] += dy
    for i in buckle: set_weights(ob, int(i), idw_weights(ob, co, belt, co[i]))
    entry['buckle'] = {'vertices': int(len(buckle)), 'gap_before_mm': round(min(gaps) * 1000, 2),
                       'gap_spread_mm': round((max(gaps) - min(gaps)) * 1000, 2), 'moved_back_mm': round(dy * 1000, 2)}

    # ---- chest: remove the anatomical dimples from the shirt ------------------------------
    nbr = [[] for _ in range(len(me.vertices))]
    shirt_set = set(shirt.tolist())
    for e in me.edges:
        a, b = e.vertices
        if a in shirt_set and b in shirt_set: nbr[a].append(b); nbr[b].append(a)
    def chest_weight(p):
        x, y, z = p
        if y > -0.01: return 0.0
        wz = smoothstep((z - 1.13) / 0.05) * smoothstep((1.415 - z) / 0.04)
        wx = smoothstep((0.215 - abs(x)) / 0.05)
        wy = smoothstep((-0.01 - y) / 0.04)
        return wz * wx * wy
    region = np.array([i for i in shirt if chest_weight(co[i]) > 0])
    wgt = np.array([chest_weight(co[i]) for i in region])
    normals = np.array([me.vertices[i].normal for i in region])
    # One wide Gaussian pass over the cloth surface (geodesic, so the inner shell never
    # mixes with the outer one): features narrower than ~4 cm (the dimples) vanish, the
    # chest's own curvature (radius > 15 cm) moves by about a millimetre.
    import heapq
    sigma = 0.018; reach = 3 * sigma
    snap = co.copy(); new_pos = {}
    # area weights: the nipple survives as a dense ring of tiny faces, which a plain vertex
    # average would favour
    varea = np.zeros(len(co))
    for p in me.polygons:
        for vi in p.vertices: varea[vi] += p.area / len(p.vertices)
    for k, i in enumerate(region):
        dist = {int(i): 0.0}; heap = [(0.0, int(i))]
        while heap:
            d, v = heapq.heappop(heap)
            if d > dist.get(v, 1e9): continue
            for n_ in nbr[v]:
                nd = d + float(np.linalg.norm(snap[n_] - snap[v]))
                if nd < reach and nd < dist.get(n_, 1e9): dist[n_] = nd; heapq.heappush(heap, (nd, n_))
        ids = np.fromiter(dist.keys(), int); dd = np.fromiter(dist.values(), float)
        w = np.exp(-dd * dd / (2 * sigma * sigma)) * varea[ids]
        mean = (snap[ids] * w[:, None]).sum(0) / w.sum()
        n = normals[k]
        new_pos[int(i)] = snap[i] + wgt[k] * n * float(np.dot(mean - snap[i], n))
    for i, p_ in new_pos.items(): co[i] = p_
    disp = np.linalg.norm(co[region] - before_co[region], axis=1)
    entry['chest'] = {'vertices': int(len(region)), 'max_move_mm': round(float(disp.max()) * 1000, 2),
                      'mean_move_mm': round(float(disp.mean()) * 1000, 2)}

    # ---- wrists: cuff hugs the wrist, sleeve end tucks inside it -------------------------
    entry['wrists'] = {}
    for side in ('l', 'r'):
        A = Vector(arm.data.bones['lowerarm_' + side].head_local); B = Vector(arm.data.bones['hand_' + side].head_local)
        axis = (A - B).normalized()  # from the wrist up the forearm
        def local(p):
            v = Vector(p) - B; s = v.dot(axis); r = v - axis * s
            return s, r
        cuff_l = [l for l, ix in ward.items() if len(ix) >= 8 and np.linalg.norm(co[ix].mean(0) - np.array(B), axis=0) < 0.12
                  and np.ptp(co[ix], axis=0).max() < 0.16 and l != shirt_l]
        if len(cuff_l) != 1: raise RuntimeError(f'{ob.name}: expected one {side} cuff, found {len(cuff_l)}')
        cuff = ward[cuff_l[0]]
        arm_skin = np.array([i for i in skin if -0.03 < local(co[i])[0] < 0.20 and local(co[i])[1].length < 0.09])
        sset = set(arm_skin.tolist())
        skin_faces = [[v.index for v in f.verts] for f in bm.faces if all(v.index in sset for v in f.verts)]
        tree = BVHTree.FromPolygons([tuple(c) for c in co], skin_faces, all_triangles=False)
        s_skin = max(local(co[i])[0] for i in arm_skin if local(co[i])[1].length < 0.07)
        def skin_radius(s, r):
            # the forearm skin under the sleeve was removed at build time: above the visible
            # wrist skin, measure the last real skin ring (the forearm only widens upwards)
            s = min(s, s_skin - 0.003)
            origin = B + axis * s
            if r.length < 1e-6: return None
            hit = tree.ray_cast(origin, r.normalized(), 0.12)
            if hit[0] is not None: return hit[3]
            near = tree.find_nearest(origin + r)
            if near[0] is None: return None
            return local(near[0])[1].length
        cs = [local(co[i])[0] for i in cuff]; s0, s1 = min(cs), max(cs)
        # weight donors: forearm skin above the HandBindingV2 fit region (which ends 25 mm up
        # the forearm), so SK_Dink and SK_Dink_Hands get identical cuffs
        donors = np.array([i for i in arm_skin if local(co[i])[0] >= 0.03])
        moved_cuff = []
        for i in cuff:
            s, r = local(co[i]); rs = skin_radius(s, r)
            if rs is None: continue
            u = (s - s0) / max(1e-6, s1 - s0)
            shrink = 0.0105 - 0.0070 * u
            new_off = max(0.0015, (r.length - rs) - shrink)
            co[i] = np.array(B + axis * s + r.normalized() * (rs + new_off))
            moved_cuff.append((r.length - rs, new_off))
            set_weights(ob, int(i), idw_weights(ob, co, donors, co[i]))
        # The sleeve narrows into the cuff: inside the cuff it sits 1.5 mm within the cuff's
        # inner wall, and above the cuff top it eases back to its drape over 35 mm.
        cset = set(cuff.tolist())
        cuff_faces = [[v.index for v in f.verts] for f in bm.faces if all(v.index in cset for v in f.verts)]
        ctree = BVHTree.FromPolygons([tuple(c) for c in co], cuff_faces, all_triangles=False)
        def cuff_inner(s, r):
            hit = ctree.ray_cast(B + axis * s, r.normalized(), 0.12)
            if hit[0] is not None: return hit[3]
            # a ray along a polygon edge can slip through; take the nearest cuff wall instead
            hits = [ctree.ray_cast(B + axis * s, (r.normalized() + q).normalized(), 0.12) for q in
                    (axis.cross(r).normalized() * 0.02, axis.cross(r).normalized() * -0.02)]
            hits = [h[3] for h in hits if h[0] is not None]
            return min(hits) if hits else None
        sleeve = [i for i in shirt if -0.02 < local(co[i])[0] < s1 + 0.06 and local(co[i])[1].length < 0.065]
        ref_u = axis.cross(Vector((0, 0, 1))).normalized(); ref_v = axis.cross(ref_u)
        def angle(r): return math.atan2(r.dot(ref_v), r.dot(ref_u))
        # The sleeve end is cut on a slant (62 mm above the wrist on one side, 82 mm on the
        # other) and the cuff stops at 72 mm: the high side left an open, skinless slot.
        # Per angle (10 degree bins, widened by a +-25 degree max filter) stretch the last
        # 35 mm of sleeve down so its end sits 8 mm inside the cuff everywhere.
        bins = [None] * 36
        for i in sleeve:
            s_, r_ = local(co[i]); b = int((math.degrees(angle(r_)) + 180) // 10) % 36
            bins[b] = s_ if bins[b] is None else min(bins[b], s_)
        known = [k for k in range(36) if bins[k] is not None]
        for k in range(36):
            if bins[k] is None: bins[k] = bins[min(known, key=lambda j: min(abs(j - k), 36 - abs(j - k)))]
        # a 10 degree bin can miss the decimated end ring: close such gaps with a +-1 bin min
        bins = [min(bins[(k + d) % 36] for d in (-1, 0, 1)) for k in range(36)]
        rim = [max(bins[(k + d) % 36] for d in range(-2, 3)) for k in range(36)]
        s_end = min(bins); rim_top = max(rim); depth = s1 - 0.008; L = 0.035
        moved_sleeve = 0; misses = 0
        for i in sleeve:
            s, r = local(co[i]); rl = r.length
            f = (math.degrees(angle(r)) + 180) / 10 - 0.5; k = int(math.floor(f)); t_ = f - k
            e = rim[k % 36] * (1 - t_) + rim[(k + 1) % 36] * t_
            shift = max(0.0, e - depth) * min(1.0, max(0.0, 1 - (s - e) / L))
            s_new = max(s - shift, s0 + 0.004)
            ci = None
            for back in (0.002, 0.005, 0.009, 0.014):
                ci = cuff_inner(min(s_new, s1 - back), r)
                if ci is not None: break
            if ci is None: misses += 1; continue
            target = ci - 0.0015
            if s_new > s1 - 0.002: target = target + (rl - target) * smoothstep((s_new - s1) / 0.035)
            rs = skin_radius(s_new, r)
            if rs is not None: target = max(target, rs + 0.001)
            r_new = min(rl, target)
            if s_new != s or r_new != rl:
                co[i] = np.array(B + axis * s_new + r.normalized() * r_new); moved_sleeve += 1
        if misses: raise RuntimeError(f'{ob.name}: {misses} {side} sleeve vertices do not see the cuff')
        if len(moved_cuff) != len(cuff): raise RuntimeError(f'{ob.name}: {len(cuff)-len(moved_cuff)} {side} cuff vertices without skin under them')
        entry['wrists'][side] = {'skin_top_mm': round(s_skin * 1000, 1), 'cuff_vertices': int(len(cuff)), 'cuff_span_mm': [round(s0 * 1000, 1), round(s1 * 1000, 1)],
                                 'sleeve_end_mm': [round(s_end * 1000, 1), round(rim_top * 1000, 1)], 'sleeve_vertices_tapered': moved_sleeve,
                                 'cuff_offset_before_mm': [round(min(a for a, _ in moved_cuff) * 1000, 1), round(max(a for a, _ in moved_cuff) * 1000, 1)],
                                 'cuff_offset_after_mm': [round(min(b for _, b in moved_cuff) * 1000, 1), round(max(b for _, b in moved_cuff) * 1000, 1)]}
    bm.free()
    for v, c in zip(me.vertices, co): v.co = Vector(c)
    me.update()
    changed = np.where(np.linalg.norm(co - before_co, axis=1) > 0)[0]
    entry['changed_vertices'] = int(len(changed))
    # every vertex weighted, at most four influences
    bad = [v.index for v in me.vertices if not v.groups or len([g for g in v.groups if g.weight > 1e-6]) > 4]
    if bad: raise RuntimeError(f'{ob.name}: weight rule broken at {bad[:5]}')
    zero = sum(n.vector.length < 1e-4 for n in me.corner_normals)
    entry['zero_corner_normals'] = int(zero)
    report['meshes'].append(entry)
    print('FIXED', json.dumps(entry), flush=True)

report['bones'] = len(arm.data.bones)
with open(REPORT, 'w') as f: json.dump(report, f, indent=2); f.write('\n')
if SAVE:
    bpy.context.preferences.filepaths.save_version = 0  # no stray .blend1 next to the source
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, relative_remap=False)
    print('SAVED', bpy.data.filepath, flush=True)
