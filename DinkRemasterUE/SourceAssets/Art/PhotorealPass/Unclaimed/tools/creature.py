"""Creature toolkit for the unclaimed-family sources: body from a joint graph (Skin modifier, voxel remesh),
armature from the same joints, automatic weights, LODs that keep the weights, per-LOD FBX and the manifest.

Bone names follow tools/blender/CONVENTIONS.md section 11: one root bone `root` at the asset origin (between the
feet), lower-case names, `_l` / `_r`, deform bones only, at most 4 influences per vertex.
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pplib as L


def _r3(r):
    if np.isscalar(r):
        return np.array((r, r, r), float)
    r = tuple(r); return np.array(r if len(r) == 3 else (r[0], (r[0] + r[1]) / 2, r[1]), float)      # (x, z) pair -> (x, mean, z)


def graph_body(name, J, E, R, c=None, seg=0.35, voxel=0.012, smooth=10, sub=None):
    """J {joint: (x, y, z)}, E [(a, b)], R {joint: r | (rx, rz) | (rx, ry, rz)} world-axis ellipsoid radii -> one closed organic mesh.
    Ellipsoids are strung along every edge (spacing = seg x local radius) and fused by a voxel remesh, then relaxed."""
    bm = bmesh.new(); done = set()

    def blob(p, r):
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0, matrix=Matrix.Translation(Vector(p)) @ Matrix.Diagonal((r[0], r[1], r[2], 1.0)))
    for a, b in E:
        pa, pb = np.array(J[a], float), np.array(J[b], float); ra, rb = _r3(R[a]), _r3(R[b]); ln = np.linalg.norm(pb - pa); n = max(1, int(ln / (seg * min(ra.min(), rb.min()) + 1e-9)))
        n = min(n, 60)
        for k in range(n + 1):
            if (k == 0 and a in done) or (k == n and b in done):
                continue
            t = k / n; s_ = t * t * (3 - 2 * t) * 0.5 + t * 0.5; blob(pa * (1 - t) + pb * t, ra * (1 - s_) + rb * s_)
        done.add(a); done.add(b)
    ob = L.bm_obj(name, bm, c)
    L.mod(ob, 'REMESH', mode='VOXEL', voxel_size=voxel, adaptivity=0.0, use_smooth_shade=True); L.apply_mods(ob)
    if smooth:
        L.mod(ob, 'SMOOTH', factor=0.6, iterations=smooth); L.apply_mods(ob)
    ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons)); L.fix_normals(ob)
    return ob


def set_attr(ob, name, values):
    a = ob.data.attributes.get(name) or ob.data.attributes.new(name, 'FLOAT', 'POINT'); a.data.foreach_set('value', np.asarray(values, np.float32)); return a


def cone(name, base, tip, r0, c=None, bend=(0, 0, 0), nu=10, nv=8, r1=0.0006, sharp=1.4):
    """claw / spine / tooth: tapered, slightly curved horn from base to tip"""
    b = np.array(base, float); t_ = np.array(tip, float); mid = (b + t_) / 2 + np.array(bend, float)
    rows = []
    for k in np.linspace(0, 1, 5):
        p = (1 - k) ** 2 * b + 2 * k * (1 - k) * mid + k * k * t_; r = r1 + (r0 - r1) * (1 - k) ** sharp; rows.append((p[0], p[1], p[2], r, r, 2.0))
    ax = t_ - b; up = (0, 0, 1) if abs(ax[2]) < 0.8 * np.linalg.norm(ax) else (1, 0, 0)
    return L.sweep(name, rows, nu=nu, nv=nv, c=c, up=up, cap=0.2)


def ball(name, center, r, c=None, seg=20, squash=(1, 1, 1)):
    V = []; F = []; n = seg; m = seg // 2
    for j in range(m + 1):
        ph = math.pi * j / m
        for i in range(n):
            th = 2 * math.pi * i / n; V.append((center[0] + r * squash[0] * math.sin(ph) * math.cos(th), center[1] + r * squash[1] * math.sin(ph) * math.sin(th), center[2] + r * squash[2] * math.cos(ph)))
    for j in range(m):
        for i in range(n):
            i1 = (i + 1) % n; F.append((j * n + i, (j + 1) * n + i, (j + 1) * n + i1, j * n + i1))
    ob = L.new_obj(name, V, F, c); bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bm.to_mesh(ob.data); bm.free(); L.fix_normals(ob); return ob


def surface_hit(ob, origin, direction, dist=5.0):
    """first hit of a ray on the mesh (object space = world for applied transforms); None if it misses"""
    dg = bpy.context.evaluated_depsgraph_get(); dg.update(); ok, loc, nrm, idx = ob.ray_cast(Vector(origin), Vector(direction).normalized(), distance=dist, depsgraph=dg)
    return (np.array(loc), np.array(nrm)) if ok else None



# ------------------------------------------------------------------ rig
def make_armature(name, J, bones, c=None):
    """bones = [(bone, head_joint_or_xyz, tail_joint_or_xyz, parent_bone_or_None)]; first must be `root`"""
    ad = bpy.data.armatures.new(name); arm = bpy.data.objects.new(name, ad); L.link(arm, c); L.activate(arm); bpy.ops.object.mode_set(mode='EDIT')
    def P(x):
        return Vector(J[x]) if isinstance(x, str) else Vector(x)
    for b, h, t, par in bones:
        eb = ad.edit_bones.new(b); eb.head = P(h); eb.tail = P(t)
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + Vector((0, 0, 0.05))
        if par:
            eb.parent = ad.edit_bones[par]; eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT'); return arm


def _seg_dist(P, a, b):
    ab = b - a; t = np.clip(((P - a) @ ab) / max(1e-12, ab @ ab), 0, 1); return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def bind(mesh, arm, skip=('root',), power=4.0, try_heat=True):
    """automatic weights (bone heat); falls back to inverse-distance weights when heat fails. Limits to 4 influences, normalised."""
    ok = False
    if try_heat:
        L.activate(arm, [mesh])
        try:
            bpy.ops.object.parent_set(type='ARMATURE_AUTO');
            n = len(mesh.data.vertices); cnt = np.zeros(n, int)
            for v in mesh.data.vertices:
                cnt[v.index] = sum(1 for g in v.groups if g.weight > 1e-4)
            ok = bool((cnt > 0).all())
        except Exception as e:
            print('bone heat failed:', e)
    method = 'bone heat'
    if not ok:
        method = 'inverse distance'
        for g in list(mesh.vertex_groups):
            mesh.vertex_groups.remove(g)
        P = L.co(mesh); bl = [b for b in arm.data.bones if b.name not in skip]; D = np.stack([_seg_dist(P, np.array(b.head_local), np.array(b.tail_local)) for b in bl], 1)
        Wt = 1.0 / np.maximum(D, 1e-4) ** power; idx = np.argsort(-Wt, 1)[:, :4]; rows = np.arange(len(P))[:, None]; W4 = Wt[rows, idx]; W4 /= W4.sum(1, keepdims=True)
        groups = [mesh.vertex_groups.new(name=b.name) for b in bl]
        for vi in range(len(P)):
            for k in range(4):
                if W4[vi, k] > 0.01:
                    groups[idx[vi, k]].add([vi], float(W4[vi, k]), 'REPLACE')
        mesh.parent = arm
        if not any(m.type == 'ARMATURE' for m in mesh.modifiers):
            m = mesh.modifiers.new('Armature', 'ARMATURE'); m.object = arm
    L.activate(mesh)
    try:
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4); bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    except Exception as e:
        print('limit/normalise:', e)
    mx = max((sum(1 for g in v.groups if g.weight > 1e-4) for v in mesh.data.vertices), default=0)
    un = sum(1 for v in mesh.data.vertices if not any(g.weight > 1e-4 for g in v.groups))
    return {'method': method, 'max_influences': mx, 'unweighted_vertices': un}


def lod_keep_weights(lo, ratio, name):
    """decimated copy that keeps vertex groups and the armature binding"""
    o = L.dup(lo, name); arm = None
    for m in list(o.modifiers):
        if m.type == 'ARMATURE':
            arm = m.object; o.modifiers.remove(m)
    L.mod(o, 'DECIMATE', ratio=ratio, use_collapse_triangulate=True); L.apply_mods(o)
    if arm:
        m = o.modifiers.new('Armature', 'ARMATURE'); m.object = arm; o.parent = arm
    return o


def pose(arm, rots):
    """rots {bone: (rx, ry, rz) degrees, local}; {} resets"""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0)
    for b, r in rots.items():
        arm.pose.bones[b].rotation_euler = tuple(math.radians(v) for v in r)
    bpy.context.view_layer.update()


def export_skeletal(path, arm, mesh):
    L.activate(arm, [mesh]); os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_ALL', axis_forward='Y', axis_up='Z',
                             bake_space_transform=False, use_triangles=True, mesh_smooth_type='FACE', use_tspace=False, add_leaf_bones=False, bake_anim=False, path_mode='STRIP',
                             object_types={'MESH', 'ARMATURE', 'EMPTY'}, colors_type='NONE', use_mesh_modifiers=False, use_armature_deform_only=True, primary_bone_axis='Y', secondary_bone_axis='X')
    return path


def finish_creature(asset, cls, lo, hi_obs, arm, outdir, px, families, origin, dresses, weaknesses, third_party=(), script=None, extrude=0.006, maxdist=0.02, ss=1,
                    lod_ratios=(0.5, 0.25), variants=None, extra=None, sss=None, post=None):
    """bake the dense source to the game mesh, bind it to the armature, LODs, one FBX per LOD (mesh + skeleton), .blend, manifest.
    variants = {suffix: fn(bc_srgb_float_array) -> array}: recoloured base-colour maps that share N / ORM (colour families of one creature)."""
    from PIL import Image
    os.makedirs(outdir, exist_ok=True); name = asset[3:]; ac = L.coll(asset); ac['dink_class'] = cls; ac['dink_tex_px'] = px
    L.link(lo, ac); L.link(arm, ac); lo.name = asset + '_LOD0'; lo.data.name = asset + '_LOD0'; arm.name = asset + '_Armature'
    files, stats = L.bake_set(lo, hi_obs, px, outdir, name, extrude=extrude, maxdist=maxdist, ss=ss, post=post)
    gm = L.game_material('MI_' + name, files, sss=sss); L.assign(lo, gm)
    vfiles = {}
    if variants:
        bc = np.asarray(Image.open(files['BC']).convert('RGB'), np.float32) / 255.0
        for suf, fn in variants.items():
            p = os.path.join(outdir, 'T_%s_%s_BC.png' % (name, suf)); Image.fromarray((np.clip(fn(bc), 0, 1) * 255 + 0.5).astype(np.uint8)).save(p, optimize=True); vfiles[suf] = p
    rigrep = bind(lo, arm); lods = [lo]
    for i, r in enumerate(lod_ratios):
        lods.append(lod_keep_weights(lo, r, asset + '_LOD%d' % (i + 1)))
    fbx = []
    for i, o in enumerate(lods):
        p = os.path.join(outdir, '%s_LOD%d.fbx' % (asset, i)); export_skeletal(p, arm, o); fbx.append(L.rel(p))
    for o in lods[1:]:
        o.hide_render = True
    st = L.mesh_stats(lo); hc = L.coll('Source_Hi')
    for o in hi_obs:
        L.link(o, hc); o.hide_render = True; o.hide_viewport = True
    blend = os.path.join(outdir, asset + '.blend'); L.save_blend(blend); soft, hard = L.BUDGET.get(cls, (None, None))
    man = {'name': asset, 'class': cls, 'fbx': fbx[0], 'lod_fbx': fbx, 'source_blend': L.rel(blend), 'build': 'Unclaimed/tools/bl.sh %s' % (script or '?'),
           'dimensions_m': st['dimensions_m'], 'bounds_min_m': st['bounds_min_m'], 'bounds_max_m': st['bounds_max_m'],
           'lod0_triangles': st['triangles'], **{'lod%d_triangles' % (i + 1): L.tri_count(o) for i, o in enumerate(lods[1:])},
           'triangle_budget': {'soft': soft, 'hard': hard, 'within_soft': st['triangles'] <= soft},
           'textures': [{'file': L.rel(p), 'size_px': list(Image.open(p).size), 'channels': {'BC': 'base colour sRGB', 'N': 'tangent normal, OpenGL (green up; flip green on import)', 'ORM': 'R occlusion, G roughness, B metallic'}[k]} for k, p in files.items()]
                       + [{'file': L.rel(p), 'size_px': list(Image.open(p).size), 'channels': 'base colour sRGB, colour variant "%s" (shares N and ORM)' % s} for s, p in vfiles.items()],
           'materials': ['MI_' + name] + ['MI_%s_%s' % (name, s) for s in vfiles],
           'rig': {'root_bone': 'root', 'bones': [b.name for b in arm.data.bones], 'bone_count': len(arm.data.bones), 'weights': rigrep, 'rest_pose': 'standing pose as modelled (not a T pose)',
                   'animation': 'none: skeleton and skin weights only; no clips, no Physics Asset, no control rig', 'skeleton': 'bespoke (CONVENTIONS.md section 11: any skeleton with a single root bone named root)'},
           'validation': {k: st[k] for k in ('non_manifold_edges', 'open_edges', 'loose_verts', 'zero_area_faces', 'uv_range', 'transforms_applied')}, 'bake_stats': stats,
           'pivot': 'feet: armature origin on the ground between the feet, front on -Y', 'families': families, 'origin_ids': origin, 'supersedes': 'none (placeholder greybox cards)', 'dresses': dresses,
           'third_party': list(third_party), 'status': 'source delivered; not imported into Unreal, not bound to any placement', 'known_weaknesses': weaknesses}
    if extra:
        man.update(extra)
    json.dump(man, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1); print('MANIFEST', outdir)
    return man, lods, files, vfiles
