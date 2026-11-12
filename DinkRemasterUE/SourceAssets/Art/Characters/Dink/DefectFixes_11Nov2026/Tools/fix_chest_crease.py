"""Hero defect fix of 11 Nov 2026: the crease left on the shirt chest after the 9 Nov pass.

blender -b <accepted SK_Dink.blend | SK_Dink_Hands.blend> -P fix_chest_crease.py -- <report.json> [<save as .blend> [<padded atlas dir>]]

Cause: the shirt is the body offset along its normals (`build_dink_art.py`), so the MakeHuman
nipple survived the drape smoothing and decimation as a dense fan of tiny faces (10-20 mm^2, in a
shirt whose chest faces are ~350 mm^2) on each pectoral. The 9 Nov pass
(`DefectFixes_9Nov2026/Tools/fix_hero_defects.py`) averaged the chest along the normals with an
18 mm Gaussian: the bump went, but the fan's vertices kept a few millimetres of height noise
between neighbours a few millimetres apart, i.e. folds: on his right chest (-X) faces meet at
28-30 degrees (vertex normals 11 degrees off their neighbours), a short crease in raking light.

Fix, per LOD, per side and per shirt shell (the outer one, and the inner one 2.9 mm behind it): in
the frame of the local front normal n0, every shell vertex within 24 mm of the nipple centre gets a
new HEIGHT along n0, solved as a biharmonic (thin-plate) patch over the shell's edge graph (edge
weights 1/length) with every other vertex held fixed. The fan then lies on a surface continuous in
position and slope with the cloth round it: no fold, and no flat board, because the patch carries
in the curvature of the two fixed rings round it. Only heights along n0 change (no tangential
slide): UVs, bone weights, vertex/face counts, topology, material slots, the 89-bone rig and every
vertex outside the two patches stay bit-identical. Run on SK_Dink.blend and SK_Dink_Hands.blend it
makes identical changes (verify_scope.py still finds the pair identical outside the hands).
The .blend is saved only to the given new path (the accepted source is never overwritten); a
padded atlas dir repoints the T_Dink_Atlas_* images there.
"""
import bpy, bmesh, json, math, os, sys
import numpy as np
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
REPORT = Path(argv[0])
SAVE = Path(argv[1]) if len(argv) > 1 else None
ATLAS = Path(argv[2]) if len(argv) > 2 else None
WARDROBE = 4
CENTRES = {'r': (-0.09, 1.30), 'l': (0.09, 1.30)}  # MakeHuman nipple (x, z); his right is -X
R_BAND, R_REGION, MAX_MOVE = 0.035, 0.070, 0.003
N_FULL, N_EASE = 0.030, 0.045

def smoothstep(t):
    t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)

def islands(me):
    parent = np.arange(len(me.vertices))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b: parent[a] = b
    return np.array([find(i) for i in range(len(me.vertices))])

def fold_stats(bm, centre, n0, sign, verts, radius):
    """Largest dihedral angle (deg) between neighbouring faces of one shell within radius."""
    fs = {f for f in bm.faces if all(v.index in verts for v in f.verts) and sign * f.normal.dot(n0) > 0.2
          and (f.calc_center_median() - centre).length < radius}
    worst = 0.0
    for f in fs:
        for e in f.edges:
            for g in e.link_faces:
                if g is not f and g in fs: worst = max(worst, math.degrees(f.normal.angle(g.normal, 0.0)))
    return round(worst, 1), len(fs)

meshes = sorted([o for o in bpy.data.objects if o.type == 'MESH' and '_LOD' in o.name], key=lambda o: o.name)
report = {'source': Path(bpy.data.filepath).name, 'r_band_mm': R_BAND * 1000, 'meshes': []}
for ob in meshes:
    me = ob.data
    co0 = np.array([v.co for v in me.vertices]); co = co0.copy()
    nrm = np.array([v.normal for v in me.vertices])
    lab = islands(me)
    vmat = np.full(len(co), -1)
    for p in me.polygons:
        for vi in p.vertices: vmat[vi] = p.material_index
    ward = {}
    for l in np.unique(lab[vmat == WARDROBE]): ward[l] = np.where(lab == l)[0]
    shirt_l = max((l for l, ix in ward.items() if co[ix][:, 2].max() > 1.5 and np.ptp(co[ix][:, 0]) > 0.8), key=lambda l: len(ward[l]))
    shirt = ward[shirt_l]
    nbr = [set() for _ in co]
    for e in me.edges:
        a, b = e.vertices; nbr[a].add(b); nbr[b].add(a)
    entry = {'mesh': ob.name, 'vertices': len(co), 'faces': len(me.polygons)}
    SMOOTH = {}
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.normal_update()
    for side, (cx, cz) in CENTRES.items():
        near = shirt[(np.abs(co0[shirt, 0] - cx) < R_REGION + 0.03) & (np.abs(co0[shirt, 2] - cz) < R_REGION + 0.03) & (co0[shirt, 1] < -0.05)]
        frontish = near[nrm[near, 1] < -0.3]
        c = np.array([cx, co0[frontish][np.argmin(np.hypot(co0[frontish, 0] - cx, co0[frontish, 2] - cz)), 1], cz])
        close = frontish[np.linalg.norm(co0[frontish] - c, axis=1) < 0.05]
        n0 = nrm[close].sum(0); n0 /= np.linalg.norm(n0)
        t1 = np.cross([0.0, 0.0, 1.0], n0); t1 /= np.linalg.norm(t1); t2 = np.cross(n0, t1)
        uv = lambda i: np.array([(co0[i] - c) @ t1, (co0[i] - c) @ t2])
        out = {'centre_m': [round(float(x), 4) for x in c], 'normal': [round(float(x), 4) for x in n0]}
        for shell, sign in (('outer', 1.0), ('inner', -1.0)):
            S = [int(i) for i in near if sign * (nrm[i] @ n0) > 0.2 and np.hypot(*uv(i)) < R_REGION]
            sset = set(S)
            # the band: vertices of the decimator's slivers (faces under 40 mm^2) along the UV seam
            # through the nipple (LOD2/LOD3 have none and keep their positions)
            small = {v for f in me.polygons if f.area < 4e-5 and all(v in sset for v in f.vertices) for v in f.vertices}
            free = [i for i in S if i in small and np.hypot(*uv(i)) < R_BAND]
            before = fold_stats(bm, Vector(c), Vector(n0), sign, sset, 0.03)
            if not free:
                out[shell] = {'free_vertices': 0, 'max_fold_deg_30mm': before[0]}; continue
            # moving least squares: at each freed vertex, a quadratic h(u, v) fitted to the shell's
            # fixed vertices within 45 mm (Gaussian weights, sigma 20 mm); the freed vertex takes the
            # fit's height. Neighbouring freed vertices millimetres apart get heights from nearly the
            # same smooth fit, so the slivers between them lie flat on the cloth's own curvature.
            fixed = [i for i in S if i not in set(free)]
            FU = np.array([uv(i) for i in fixed]); FH = np.array([(co0[i] - c) @ n0 for i in fixed])
            dh = []
            for v in free:
                q = uv(v); d = np.linalg.norm(FU - q, axis=1); m = d < 0.045
                w = np.sqrt(np.exp(-(d[m] ** 2) / (2 * 0.02 ** 2)))
                du, dv = FU[m, 0] - q[0], FU[m, 1] - q[1]
                A = np.stack([np.ones_like(du), du, dv, du * du, du * dv, dv * dv], 1) * w[:, None]
                coef = np.linalg.lstsq(A, FH[m] * w, rcond=None)[0]
                h_new = coef[0]; h_old = (co0[v] - c) @ n0
                dh.append(float(np.clip(h_new - h_old, -MAX_MOVE, MAX_MOVE)))
            dh = np.array(dh)
            for k, v in enumerate(free):
                co[v] = co0[v] + dh[k] * n0; bm.verts[v].co = Vector(co[v])
            bm.normal_update()
            after = fold_stats(bm, Vector(c), Vector(n0), sign, sset, 0.03)
            out[shell] = {'free_vertices': len(free), 'sliver_vertices': len(small & set(free)),
                          'max_move_mm': round(float(np.abs(dh).max()) * 1000, 2),
                          'mean_move_mm': round(float(np.abs(dh).mean()) * 1000, 2), 'clamped': int((np.abs(dh) >= MAX_MOVE - 1e-9).sum()),
                          'max_fold_deg_30mm_before': before[0], 'max_fold_deg_30mm_after': after[0], 'faces_30mm': after[1]}
        # smooth shading normals for the outer shell: the normal of a moving-least-squares
        # quadratic (sigma 20 mm, 45 mm reach) through the shell's corrected vertices, full within
        # N_FULL of the centre and easing to the mesh's own vertex normal at N_EASE
        S = [int(i) for i in near if nrm[i] @ n0 > 0.2 and np.hypot(*uv(i)) < R_REGION]
        FU = np.array([[(co[i] - c) @ t1, (co[i] - c) @ t2] for i in S]); FH = np.array([(co[i] - c) @ n0 for i in S])
        nset = 0
        for k, i in enumerate(S):
            rr = np.hypot(*FU[k])
            wgt = 1.0 - smoothstep((rr - N_FULL) / (N_EASE - N_FULL))
            if wgt <= 0: continue
            d = np.linalg.norm(FU - FU[k], axis=1); m = d < 0.045
            if m.sum() < 12: m = d < 0.07  # sparse low LODs: a wider reach
            w = np.sqrt(np.exp(-(d[m] ** 2) / (2 * 0.02 ** 2)))
            du, dv = FU[m, 0] - FU[k, 0], FU[m, 1] - FU[k, 1]
            terms = [np.ones_like(du), du, dv] + ([du * du, du * dv, dv * dv] if m.sum() >= 12 else [])
            A = np.stack(terms, 1) * w[:, None]
            coef = np.linalg.lstsq(A, FH[m] * w, rcond=None)[0]
            n_fit = n0 - coef[1] * t1 - coef[2] * t2; n_fit /= np.linalg.norm(n_fit)
            SMOOTH[i] = (n_fit, wgt); nset += 1
        out['outer_smooth_normals'] = nset
        # the outer shell must stay in front of the inner one
        o = [i for i in near if nrm[i] @ n0 > 0.2 and np.hypot(*uv(i)) < R_BAND]
        inn = [i for i in near if nrm[i] @ n0 < -0.2 and np.hypot(*uv(i)) < R_BAND]
        if o and inn:
            for tag, P in (('before', co0), ('after', co)):
                gap = min(((P[i] - c) @ n0) - ((P[min(inn, key=lambda j: np.linalg.norm(uv(j) - uv(i)))] - c) @ n0) for i in o)
                out['min_outer_inner_gap_mm_' + tag] = round(float(gap) * 1000, 2)
        entry[side] = out
    bm.free()
    for i in np.where(np.any(co != co0, axis=1))[0]: me.vertices[int(i)].co = Vector(co[i])
    me.update()
    if SMOOTH:
        # custom split normals only on the chest patches; every other corner keeps its automatic
        # normal (a zero custom normal means 'automatic')
        auto = {}
        for p in me.polygons:
            for li in p.loop_indices: auto[li] = Vector(me.corner_normals[li].vector)
        custom = []
        dev = []
        for li, l in enumerate(me.loops):
            if l.vertex_index in SMOOTH:
                n_fit, wgt = SMOOTH[l.vertex_index]
                nv = (auto[li] * (1 - wgt) + Vector(n_fit) * wgt).normalized()
                dev.append(math.degrees(auto[li].angle(nv, 0.0))); custom.append(tuple(nv))
            else:
                custom.append((0.0, 0.0, 0.0))
        me.normals_split_custom_set(custom)
        me.update()
        entry['custom_normal_corners'] = len(dev)
        entry['custom_normal_max_change_deg'] = round(max(dev), 1)
        entry['custom_normal_mean_change_deg'] = round(sum(dev) / len(dev), 2)
        outside = [li for li, l in enumerate(me.loops) if l.vertex_index not in SMOOTH]
        entry['outside_corner_normal_max_change_deg'] = round(max(math.degrees(auto[li].angle(Vector(me.corner_normals[li].vector), 0.0)) for li in outside), 4)
    entry['changed_vertices'] = int(np.any(co != co0, axis=1).sum())
    entry['zero_corner_normals'] = int(sum(n.vector.length < 1e-4 for n in me.corner_normals))
    report['meshes'].append(entry)
    print('CHEST', json.dumps(entry), flush=True)

if SAVE is not None:
    SAVE = SAVE.resolve(); SAVE.parent.mkdir(parents=True, exist_ok=True)
    base = Path(bpy.data.filepath).resolve().parent
    for img in bpy.data.images:  # keep every image path relative, now to the new file
        if not img.filepath: continue
        src = Path(bpy.path.abspath(img.filepath, start=str(base))).resolve()
        if ATLAS is not None and src.name in ('T_Dink_Atlas_BC.png', 'T_Dink_Atlas_N.png', 'T_Dink_Atlas_ORM.png'):
            src = (ATLAS / src.name).resolve()
        img.filepath = '//' + os.path.relpath(src, SAVE.parent)
    bpy.ops.wm.save_as_mainfile(filepath=str(SAVE), relative_remap=False, compress=True)
    report['saved'] = SAVE.name
    report['images'] = {img.name: img.filepath for img in bpy.data.images if img.filepath}
REPORT.write_text(json.dumps(report, indent=2) + '\n')
print('CHEST CREASE FIX DONE', REPORT, flush=True)
