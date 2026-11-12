"""Stage 1: original duck anatomy, unique UVs, own 23-bone rig, skin weights and actions.

    blender -b --factory-startup -t 3 --python Tools/build_duck.py

Writes Working/Duck_Working.blend and duck_rig_report.json.  Deterministic (seed 1997).
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402
import duck_geometry as G  # noqa: E402
from duck_actions import create_duck_actions  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.render.fps = D.FPS
D.WORKING.mkdir(parents=True, exist_ok=True)

COLL = bpy.data.collections.new(D.ASSET)
scene.collection.children.link(COLL)
COLL['dink_class'] = 'creature'
COLL['dink_path'] = 'Duck'
COLL['dink_tex_px'] = D.TEX_PX


def placeholder(name, color, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough
    m.diffuse_color = (*color, 1)
    return m


mats = [placeholder('MI_Duck_Feather', (0.74, 0.73, 0.69), 0.62), placeholder('MI_Duck_Bill', (0.72, 0.27, 0.03), 0.4),
        placeholder('MI_Duck_Feet', (0.70, 0.24, 0.04), 0.5), placeholder('MI_Duck_Eye', (0.02, 0.01, 0.005), 0.05)]
ob = G.build_geometry(COLL, mats)
me = ob.data

# ---------------------------------------------------------------- unique UVs (no overlap)
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
for layer in list(me.uv_layers):
    me.uv_layers.remove(layer)
me.uv_layers.new(name='UVMap')
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(52), island_margin=0.002, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.seams_from_islands(mark_seams=True)
bpy.ops.uv.unwrap(method='CONFORMAL', margin=0.002)
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode='OBJECT')
# Cards and blood films need less texel density than the body: shrink their islands before packing.
fpart_f = [0] * len(me.polygons)
me.attributes['duck_fpart'].data.foreach_get('value', fpart_f)
uvl = me.uv_layers[0].data
for poly, fp in zip(me.polygons, fpart_f):
    k = {D.PART_CARD: 0.45, D.PART_BLOOD_BODY: 0.7, D.PART_BLOOD_HEAD: 0.7}.get(fp)
    if k is None:
        continue
    if fp == D.PART_CARD:
        pass  # card islands (two faces each) are scaled with the blood films below
bm_uv = bmesh.new()
bm_uv.from_mesh(me)
uvlay = bm_uv.loops.layers.uv.active
fl = bm_uv.faces.layers.int.get('duck_fpart')
# blood films: scale each connected UV island about its own centre
seen = set()
for f in bm_uv.faces:
    if f.index in seen or f[fl] not in (D.PART_BLOOD_BODY, D.PART_BLOOD_HEAD, D.PART_CARD):
        continue
    stack, island = [f], []
    seen.add(f.index)
    while stack:
        g = stack.pop()
        island.append(g)
        for e in g.edges:
            if e.seam:
                continue
            for h in e.link_faces:
                if h.index not in seen and h[fl] == g[fl]:
                    seen.add(h.index)
                    stack.append(h)
    pts = [l[uvlay].uv.copy() for g in island for l in g.loops]
    cen = sum(pts, Vector((0, 0))) / len(pts)
    for g in island:
        for l in g.loops:
            l[uvlay].uv = cen + (l[uvlay].uv - cen) * (0.45 if island[0][fl] == D.PART_CARD else 0.7)
bm_uv.to_mesh(me)
bm_uv.free()
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.0012, scale=True)
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- own armature
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm = bpy.context.object
arm.name = 'Armature'
arm.data.name = 'SK_Duck_Skeleton'
G._link(arm, COLL)
eb = arm.data.edit_bones
eb.remove(eb[0])
for name, head, tail, parent in D.BONES:
    b = eb.new(name)
    b.head = head
    b.tail = tail
    b.roll = 0
    if parent:
        b.parent = eb[parent]
bpy.ops.object.mode_set(mode='OBJECT')
arm.show_in_front = True
ob.parent = arm
mod = ob.modifiers.new('Armature', 'ARMATURE')
mod.object = arm

# ---------------------------------------------------------------- skin weights
N = len(me.vertices)
P = np.zeros(N * 3, np.float32)
me.vertices.foreach_get('co', P)
P = P.reshape(-1, 3).astype(np.float64)
part = np.zeros(N, np.int32)
me.attributes['duck_part'].data.foreach_get('value', part)
pa = np.zeros(N, np.float32)
me.attributes['duck_a'].data.foreach_get('value', pa)
names = [b[0] for b in D.BONES]
bidx = {n: i for i, n in enumerate(names)}
heads = np.array([b[1] for b in D.BONES], float)
tails = np.array([b[2] for b in D.BONES], float)


def seg_dist(points, i):
    a, b = heads[i], tails[i]
    ab = b - a
    t = np.clip(((points - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(points - (a + t[:, None] * ab), axis=1)


W = np.zeros((N, len(names)))
side = np.where(P[:, 1] >= 0, 'l', 'r')


def dist_weights(mask, bones, power, bias=None):
    idx = np.nonzero(mask)[0]
    if not len(idx):
        return
    pts = P[idx]
    ds = []
    for bn in bones:
        d = seg_dist(pts, bidx[bn])
        if bias and bn in bias:
            d = d * bias[bn]
        ds.append(np.maximum(d, 0.004))
    ds = np.array(ds).T
    w = 1.0 / ds ** power
    for k, bn in enumerate(bones):
        W[idx, bidx[bn]] += w[:, k] / w.sum(1)


body_bones = ['pelvis', 'spine_01', 'spine_02', 'neck_01', 'neck_02', 'neck_03', 'head', 'tail_01', 'tail_02']
dist_weights(part == D.PART_BODY, body_bones, 4, bias={'tail_01': 1.5, 'tail_02': 1.2, 'pelvis': 0.9})
# Feathered thighs follow the drumstick a little.
for s, sd in (('l', 1), ('r', -1)):
    m = (part == D.PART_BODY) & (P[:, 1] * sd > 0.022) & (P[:, 2] < 0.165)
    idx = np.nonzero(m)[0]
    d = seg_dist(P[idx], bidx['calf_' + s])
    k = np.clip(1 - (d - 0.010) / 0.022, 0, 1) * 0.55
    W[idx] *= (1 - k)[:, None]
    W[idx, bidx['calf_' + s]] += k
for prt, bone in ((D.PART_BILL_UP, 'head'), (D.PART_NOSTRIL, 'head'), (D.PART_EYE, 'head'), (D.PART_LID, 'head'), (D.PART_BILL_LO, 'jaw')):
    W[part == prt, bidx[bone]] = 1.0
DP = np.zeros(N * 3, np.float32)
me.attributes['duck_dpos'].data.foreach_get('vector', DP)
DP = DP.reshape(-1, 3).astype(np.float64)
for s, sd in (('l', 1), ('r', -1)):
    sm = P[:, 1] * sd > 0
    wing = (part == D.PART_WING) & sm
    t = np.clip((0.010 - DP[wing, 0]) / 0.11, 0, 1)
    t = t * t * (3 - 2 * t)
    sp = np.clip((DP[wing, 0] - 0.035) / 0.04, 0, 1) * 0.30
    W[wing, bidx['wingtip_' + s]] = t * (1 - sp)
    W[wing, bidx['wing_' + s]] = (1 - t) * (1 - sp)
    W[wing, bidx['spine_01']] = sp
    leg = (part == D.PART_LEG) & sm
    dist_weights(leg, ['thigh_' + s, 'calf_' + s, 'foot_' + s], 7)
    toe = np.isin(part, [D.PART_TOE, D.PART_WEB, D.PART_CLAW]) & sm
    idx = np.nonzero(toe)[0]
    F = heads[bidx['toes_' + s]]
    r = np.linalg.norm(P[idx] - F, axis=1)
    k = np.clip((r - 0.004) / 0.010, 0, 1)
    behind = (P[idx, 0] < F[0] - 0.002)
    k[behind] = 0.0  # hallux stays on the tarsometatarsus
    W[idx, bidx['toes_' + s]] = k
    W[idx, bidx['foot_' + s]] = 1 - k
tail = part == D.PART_TAIL
t = np.clip(pa[tail] / 0.35, 0, 1)
W[tail, bidx['tail_02']] = 0.35 + 0.65 * t
W[tail, bidx['tail_01']] = 0.65 * (1 - t)

# Cards, wound caps and blood films ride on the skin: copy the nearest body vertex weights.
bodyi = np.nonzero(part == D.PART_BODY)[0]
riders = np.nonzero(np.isin(part, [D.PART_CARD] + list(D.GORE)))[0]
for chunk in np.array_split(riders, max(1, len(riders) // 400)):
    d2 = ((P[chunk, None, :] - P[None, bodyi, :]) ** 2).sum(2)
    W[chunk] = W[bodyi[np.argmin(d2, 1)]]
# Relax body weights over the surface (removes Euclidean seams near the neck root).
bm = bmesh.new()
bm.from_mesh(me)
edges = np.array([(e.verts[0].index, e.verts[1].index) for e in bm.edges], np.int64)
bm.free()
bodym = part == D.PART_BODY
em = bodym[edges[:, 0]] & bodym[edges[:, 1]]
E = edges[em]
for _ in range(4):
    acc = np.zeros_like(W)
    cnt = np.zeros(N)
    np.add.at(acc, E[:, 0], W[E[:, 1]])
    np.add.at(acc, E[:, 1], W[E[:, 0]])
    np.add.at(cnt, E[:, 0], 1)
    np.add.at(cnt, E[:, 1], 1)
    sel = bodym & (cnt > 0)
    W[sel] = 0.5 * W[sel] + 0.5 * acc[sel] / cnt[sel, None]
# Top four influences, normalised; root never deforms.
W[:, bidx['root']] = 0
order = np.argsort(-W, axis=1)
keep = np.zeros_like(W, bool)
np.put_along_axis(keep, order[:, :4], True, axis=1)
W = np.where(keep & (W > 1e-4), W, 0)
W /= W.sum(1, keepdims=True)
if not np.isfinite(W).all() or (W.sum(1) < 0.999).any():
    raise RuntimeError('unweighted duck vertices')
ob.vertex_groups.clear()
for i, n in enumerate(names):
    if n == 'root':
        continue
    vg = ob.vertex_groups.new(name=n)
    nz = np.nonzero(W[:, i])[0]
    for wv in np.unique(np.round(W[nz, i], 5)):
        sel = nz[np.round(W[nz, i], 5) == wv]
        vg.add(sel.tolist(), float(wv), 'REPLACE')
arm.data.bones['root'].use_deform = False

for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
actions = create_duck_actions(arm, ob, scene)

me.calc_loop_triangles()
report = {
    'schema': 'dink-duck-source/1',
    'bone_count': len(arm.data.bones),
    'bones': [{'name': b.name, 'parent': b.parent.name if b.parent else None,
               'matrix_local': [list(r) for r in b.matrix_local]} for b in arm.data.bones],
    'skinning': 'Procedural: surface-relaxed inverse-distance weights on bone segments for the metaball body; '
                'parametric wing/tail blends; rigid head/jaw/eye; distance-chained legs; max 4 normalised influences.',
    'max_influences': int((W > 0).sum(1).max()),
    'triangles_before_lods': len(me.loop_triangles),
    'vertices': N,
    'materials': [m.name for m in me.materials],
    'forward': '+X', 'up': '+Z', 'units': 'metres',
    'actions': actions,
    'seed': D.SEED,
}
(D.ROOT / 'duck_rig_report.json').write_text(json.dumps(report, indent=2) + '\n')
G.set_card_normals(ob)
arm.animation_data.action = bpy.data.actions['Duck_Idle']
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(D.WORKING / 'Duck_Working.blend'))
print('DUCK SOURCE READY', len(me.loop_triangles), 'triangles', len(arm.data.bones), 'bones', flush=True)
