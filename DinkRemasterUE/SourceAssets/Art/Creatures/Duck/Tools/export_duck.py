"""Stage 3: variants, LODs, source/pose validation, SK_Duck.blend, manifests and FBX exports.

    blender -b --factory-startup -t 3 --python Tools/export_duck.py

From the textured master mesh three assets are split off:
* SK_Duck           intact duck (no gore surfaces)                      class creature, 3 LODs
* SK_Duck_Headless  neck stump with wound cap and blood runs, same rig  class creature, 3 LODs
* SM_Duck_Head      severed head prop with wound cap, convex UCX hull   class prop_small, 3 LODs
Contour-feather cards are kept out of the decimator and re-added per LOD as deterministic
subsets (100 % / 50 % / 22 %), so the alpha-tested silhouette survives the LOD chain.

Uses the companion tools/blender/dinkasset pipeline (make_lods, validate, export_ue).  Source
stays in metres; only this process's copy is converted to centimetres for FBX (mesh, edit
bones and location keys x100, scene unit scale 0.01, FBX_SCALE_ALL, apply_unit_scale=True).
"""
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_common as D  # noqa: E402

sys.path.insert(0, str(D.pipeline_dir()))
from dinkasset import common, make_lods, validate, export_ue  # noqa: E402

bpy.ops.wm.open_mainfile(filepath=str(D.WORKING / 'Duck_Textured.blend'))
scene = bpy.context.scene
coll = bpy.data.collections[D.ASSET]
master = bpy.data.objects[D.LOD0]
arm = bpy.data.objects['Armature']
arm.animation_data.action = None
arm.data.pose_position = 'REST'
CUTP = np.array(D.CUT_POINT)
CUTN = np.array(D.CUT_NORMAL) / np.linalg.norm(D.CUT_NORMAL)
HEADABLE = (D.PART_BODY, D.PART_BILL_UP, D.PART_BILL_LO, D.PART_EYE, D.PART_LID, D.PART_NOSTRIL)


def face_classes(ob):
    me = ob.data
    nv = len(me.vertices)
    dpos = np.zeros(nv * 3, np.float32)
    me.attributes['duck_dpos'].data.foreach_get('vector', dpos)
    side = (dpos.reshape(-1, 3) - CUTP) @ CUTN
    fp = np.zeros(len(me.polygons), np.int32)
    me.attributes['duck_fpart'].data.foreach_get('value', fp)
    head = np.zeros(len(me.polygons), bool)
    for i, poly in enumerate(me.polygons):
        if fp[i] in D.GORE_HEAD:
            head[i] = True
        elif fp[i] in HEADABLE:
            head[i] = side[list(poly.vertices)].mean() > 0
    return fp, head


def copy_object(src, name, target_coll):
    ob = src.copy()
    ob.data = src.data.copy()
    ob.name = name
    ob.data.name = name
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    target_coll.objects.link(ob)
    return ob


def keep_faces(ob, keep):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep[f.index]], context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def drop_unused_slots(ob):
    used = sorted({p.material_index for p in ob.data.polygons})
    mats = [ob.data.materials[i] for i in used]
    remap = {old: new for new, old in enumerate(used)}
    idx = [remap[p.material_index] for p in ob.data.polygons]
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)
    ob.data.polygons.foreach_set('material_index', idx)
    ob.data.update()


def card_subset(cards_src, frac, name, target_coll):
    ob = copy_object(cards_src, name, target_coll)
    me = ob.data
    cid = np.zeros(len(me.vertices), np.int32)
    me.attributes['duck_card'].data.foreach_get('value', cid)
    keep = []
    for poly in me.polygons:
        c = int(cid[poly.vertices[0]])
        h = ((c * 2654435761) % 2 ** 32) / 2 ** 32
        keep.append(h < frac)
    keep_faces(ob, keep)
    return ob


def clean_lod(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bad = [f for f in bm.faces if f.calc_area() < 1e-10]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context='FACES_ONLY')
    wire = [e for e in bm.edges if not e.link_faces]
    if wire:
        bmesh.ops.delete(bm, geom=wire, context='EDGES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(mesh.data)
    bm.free()
    mesh.data.update()
    zero = {i for i, n in enumerate(mesh.data.corner_normals) if n.vector.length < 1e-4}
    fixed = 0
    for face in mesh.data.polygons:
        if any(i in zero for i in face.loop_indices):
            face.use_smooth = False
            fixed += 1
    mesh.data.update()
    remaining = sum(n.vector.length < 1e-4 for n in mesh.data.corner_normals)
    if remaining:
        raise RuntimeError('Zero normals remain in ' + mesh.name)
    if mesh.vertex_groups:
        for v in mesh.data.vertices:
            w = sorted([(g.group, g.weight) for g in v.groups if g.weight > 1e-6], key=lambda p: -p[1])[:4]
            tot = sum(x for _, x in w)
            if tot <= 0:
                raise RuntimeError('Unweighted vertex in ' + mesh.name)
            for g in list(v.groups):
                mesh.vertex_groups[g.group].remove([v.index])
            for g, x in w:
                mesh.vertex_groups[g].add([v.index], x / tot, 'REPLACE')
    return {'mesh': mesh.name, 'removed_zero_area_faces': len(bad), 'flat_faces_for_cancelled_normals': fixed}


def skeletal_lods(asset_coll, lod0):
    """make_lods on the solid surfaces; feather cards re-added as subsets per LOD."""
    fp, _ = face_classes(lod0)
    cards = copy_object(lod0, lod0.name + '_cards_tmp', asset_coll)
    keep_faces(cards, fp == D.PART_CARD)
    keep_faces(lod0, fp != D.PART_CARD)
    # solid surfaces decimate with plain smooth normals; only the cards carry custom (skin) normals
    bpy.ops.object.select_all(action='DESELECT')
    lod0.select_set(True)
    bpy.context.view_layer.objects.active = lod0
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    asset = common.Asset(asset_coll)
    log = make_lods.make_lods(asset, [0.5, 0.25], replace=True, force=True)
    asset.refresh()
    base = lod0.name[:-1]
    for i, frac in enumerate((1.0, 0.5, 0.22)):
        target = bpy.data.objects[base + str(i)]
        sub = card_subset(cards, frac, target.name + '_cards', asset_coll)
        bpy.ops.object.select_all(action='DESELECT')
        sub.select_set(True)
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.join()
    bpy.data.objects.remove(cards, do_unlink=True)
    asset.refresh()
    rep = []
    for m in asset.renders:
        rep.append(clean_lod(m))
        for attr in ('duck_part', 'duck_a', 'duck_c', 'duck_len', 'duck_card', 'duck_fpart', 'duck_dpos', 'duck_cn'):
            if attr in m.data.attributes:
                m.data.attributes.remove(m.data.attributes[attr])
    return asset, log, rep


# ------------------------------------------------------------------ split the master into variants
fp, head = face_classes(master)
headless_coll = bpy.data.collections.new('SK_Duck_Headless')
scene.collection.children.link(headless_coll)
headless_coll['dink_class'] = 'creature'
headless_coll['dink_path'] = 'Duck'
headless_coll['dink_tex_px'] = D.TEX_PX
headless_coll.objects.link(arm)          # one shared armature: same skeleton, bind pose and clips
head_coll = bpy.data.collections.new('SM_Duck_Head')
scene.collection.children.link(head_coll)
head_coll['dink_class'] = 'prop_small'
head_coll['dink_path'] = 'Duck'
head_coll['dink_tex_px'] = D.TEX_PX

headless0 = copy_object(master, 'SK_Duck_Headless_LOD0', headless_coll)
keep_faces(headless0, ~head & ~np.isin(fp, D.GORE_HEAD))
head0 = copy_object(master, 'SM_Duck_Head_LOD0', head_coll)
keep_faces(head0, head)
keep_faces(master, ~np.isin(fp, D.GORE))

# Severed head prop: static, unskinned, eye shares the feather material (2-slot budget), pivot base centre.
head0.parent = None
head0.matrix_world.identity()
for m in list(head0.modifiers):
    head0.modifiers.remove(m)
head0.vertex_groups.clear()
hfp, _ = face_classes(head0)
idx = [0 if mi == 3 else mi for mi in (p.material_index for p in head0.data.polygons)]
head0.data.polygons.foreach_set('material_index', idx)
drop_unused_slots(head0)
co = np.array([v.co for v in head0.data.vertices])
shift = Vector((-(co[:, 0].min() + co[:, 0].max()) / 2, -(co[:, 1].min() + co[:, 1].max()) / 2, -co[:, 2].min()))
head_rest_offset_m = [-x for x in shift]
head0.data.transform(__import__('mathutils').Matrix.Translation(shift))
for attr in ('duck_part', 'duck_a', 'duck_c', 'duck_len', 'duck_card', 'duck_fpart', 'duck_dpos', 'duck_cn'):
    if attr in head0.data.attributes:
        head0.data.attributes.remove(head0.data.attributes[attr])
bpy.ops.object.select_all(action='DESELECT')
head0.select_set(True)
bpy.context.view_layer.objects.active = head0
bpy.ops.mesh.customdata_custom_splitnormals_clear()
head_asset = common.Asset(head_coll)
if common.tri_count(head0) > 4900:
    make_lods.decimate_object(head0, 4800)
head_lod_log = make_lods.make_lods(head_asset, [0.5, 0.25], replace=True, force=True)
head_asset.refresh()
head_col_log = make_lods.make_collision(head_asset, mode='hull', replace=True)
head_asset.refresh()
head_report = [clean_lod(m) for m in head_asset.renders]

drop_unused_slots(headless0)
asset, lod_log, normal_report = skeletal_lods(coll, master)
ob = bpy.data.objects[D.LOD0]
h_asset, h_lod_log, h_normal_report = skeletal_lods(headless_coll, headless0)
for m in asset.renders + h_asset.renders:
    m.hide_render = m.name not in (D.LOD0,)

# ------------------------------------------------------------------ pose contract over every frame of every clip
rig = json.loads((D.ROOT / 'duck_rig_report.json').read_text())
actions = {k: v for k, v in rig['actions'].items() if not k.startswith('_')}
arm.data.pose_position = 'POSE'
pose_report = {}
for name, row in actions.items():
    eval_ob = bpy.data.objects['SK_Duck_Headless_LOD0'] if 'Headless' in name else ob
    arm.animation_data.action = bpy.data.actions[name]
    if arm.animation_data.action_slot is None:
        arm.animation_data.action_slot = bpy.data.actions[name].slots[0]
    gap = root = 0.0
    zmin = 1e9
    start = end = None
    for f in range(row['frames'][0], row['frames'][1] + 1):
        scene.frame_set(f)
        for s in 'lr':
            chain = ['thigh_' + s, 'calf_' + s, 'foot_' + s, 'toes_' + s]
            for a, b in zip(chain, chain[1:]):
                gap = max(gap, (arm.pose.bones[a].tail - arm.pose.bones[b].head).length)
        for a, b in (('pelvis', 'spine_01'), ('spine_01', 'spine_02'), ('spine_02', 'neck_01'), ('neck_01', 'neck_02'), ('neck_02', 'neck_03'), ('neck_03', 'head')):
            gap = max(gap, (arm.pose.bones[a].tail - arm.pose.bones[b].head).length)
        rm = arm.pose.bones['root'].matrix
        root = max(root, rm.translation.length, rm.to_quaternion().rotation_difference(arm.data.bones['root'].matrix_local.to_quaternion()).angle)
        ev = eval_ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m = ev.to_mesh()
        cz = np.zeros(len(m.vertices) * 3, np.float32)
        m.vertices.foreach_get('co', cz)
        ev.to_mesh_clear()
        zmin = min(zmin, float(cz.reshape(-1, 3)[:, 2].min()))
        snap = {b.name: b.matrix.copy() for b in arm.pose.bones}
        if f == row['frames'][0]:
            start = snap
        end = snap
    seam = max(max(abs(start[n][r][c] - end[n][r][c]) for r in range(4) for c in range(4)) for n in start)
    pose_report[name] = {'evaluated_mesh': eval_ob.name, 'max_joint_gap_m': gap, 'root_motion_m': root,
                         'start_end_pose_matrix_max_difference': seam, 'lowest_skinned_vertex_z_m': zmin, 'loop': row['loop'],
                         'max_planted_foot_slip_m': row.get('max_planted_foot_ik_error_m')}
    if gap > 0.001 or root > 1e-5 or (row['loop'] and seam > 0.001) or zmin < -0.006:
        raise RuntimeError('Pose contract failed ' + name + ': ' + str(pose_report[name]))
pose_report['_solves'] = rig['actions'].get('_solves')
arm.animation_data.action = bpy.data.actions['Duck_Idle']
arm.animation_data.action_slot = bpy.data.actions['Duck_Idle'].slots[0]
scene.frame_set(1)

# ------------------------------------------------------------------ source save + validation
for image in bpy.data.images:
    if image.filepath and 'Textures' in image.filepath:
        image.filepath = '//Textures/' + Path(image.filepath).name
bpy.ops.wm.save_as_mainfile(filepath=str(D.ROOT / 'SK_Duck.blend'), relative_remap=False)
arm.animation_data.action = None
arm.data.pose_position = 'REST'
scene.frame_set(1)
ASSETS = [D.ASSET, 'SK_Duck_Headless', 'SM_Duck_Head']
verdict = validate.validate_scene(only=ASSETS)
(D.ROOT / 'duck_validation.json').write_text(json.dumps(verdict, indent=2) + '\n')
if verdict['summary']['errors']:
    for entry in verdict['assets']:
        for finding in entry['findings']:
            if finding['severity'] == 'error':
                print('DUCK VALIDATION ERROR', entry['name'], finding['code'], finding['message'], flush=True)
    raise RuntimeError('Duck source validation must pass')

# ------------------------------------------------------------------ manifests
def bounds_of(objs):
    bb = [common.world_bounds(o) for o in objs]
    mn = Vector(tuple(min(b[0][i] for b in bb) for i in range(3)))
    mx = Vector(tuple(max(b[1][i] for b in bb) for i in range(3)))
    return mn, mx


tex = {'BC': 'Textures/T_Duck_Atlas_BC.png', 'N': 'Textures/T_Duck_Atlas_N.png', 'ORM': 'Textures/T_Duck_Atlas_ORM.png'}
tstats = json.loads((D.ROOT / 'duck_texture_report.json').read_text())
materials = {
    'MI_Duck_Feather': {'base_color': [0.70, 0.688, 0.64], 'roughness': 0.70, 'metallic': 0, 'masked': True, 'alpha_mask': True,
                        'opacity_mask_clip': 0.4, 'two_sided': True, 'subsurface': 0.0, 'normal_strength': 1, 'normal_flip_green': True,
                        'textures': tex,
                        'notes': 'Opacity mask = BC alpha (contour-feather cards, blood films); everything else alpha 1. Two-sided for the cards. '
                                 'Wound caps and blood films use this material too: their wet look comes from the ORM roughness. '
                                 'Blender preview adds sheen 0.22; recreate in Unreal optionally.'},
    'MI_Duck_Bill': {'base_color': [0.80, 0.33, 0.035], 'roughness': 0.58, 'metallic': 0, 'masked': False, 'two_sided': False,
                     'subsurface': 0.18, 'normal_strength': 1, 'normal_flip_green': True, 'textures': tex},
    'MI_Duck_Feet': {'base_color': [0.74, 0.26, 0.04], 'roughness': 0.50, 'metallic': 0, 'masked': False, 'two_sided': False,
                     'subsurface': 0.10, 'normal_strength': 1, 'normal_flip_green': True, 'textures': tex},
    'MI_Duck_Eye': {'base_color': [0.105, 0.052, 0.022], 'roughness': 0.035, 'metallic': 0, 'masked': False, 'two_sided': False,
                    'subsurface': 0.0, 'normal_strength': 1, 'normal_flip_green': True, 'clear_coat': 1.0, 'textures': tex},
}
(D.ROOT / 'duck_materials.json').write_text(json.dumps(materials, indent=2) + '\n')
key_names = {n: n.split('_', 1)[1] for n in actions}
animations = {}
for name, row in actions.items():
    k = key_names[name]
    animations[k] = {'fbx': 'Export/A_Duck_%s.fbx' % k, 'loop': row['loop'], 'fps': row['fps'], 'duration_s': row['duration_s'],
                     'frames': row['frames'], 'root_motion': False}
    if row.get('nominal_speed_cm_s'):
        animations[k]['nominal_speed_cm_s'] = row['nominal_speed_cm_s']
    if 'Headless' in name:
        animations[k]['mesh_variant'] = 'SK_Duck_Headless'
        animations[k]['minimum_pose_rotation_rad'] = 0.1
for k in ('Death', 'HeadlessDeath'):
    animations[k]['hold_last_frame'] = True
co = np.array([v.co for v in ob.data.vertices])


def fitted_box(points):
    lo = points.min(0)
    hi = points.max(0)
    c = (lo + hi) * 50
    c[1] *= -1
    return {'offset_cm': [float(x) for x in c], 'extent_cm': [float(x) for x in (hi - lo) * 50 + 1]}


body_pts = co[(co[:, 0] < 0.13) & (co[:, 0] > -0.20) & (co[:, 2] > 0.07) & (co[:, 2] < 0.29)]
head_pts = co[(co[:, 0] > 0.06) & (co[:, 2] > 0.30)]


def skel_row(a, lod0, box_pts, blend_note):
    bmin, bmax = common.world_bounds(lod0)
    umin, umax = bounds_of(a.renders)
    return {'fbx': 'Export/%s.fbx' % lod0.name, 'lod_fbx': ['Export/%s_LOD%d.fbx' % (a.name, i) for i in range(3)],
            'dimensions_m': list(bmax - bmin), 'lod_union_dimensions_m': list(umax - umin), 'bounds_min_m': list(bmin), 'bounds_max_m': list(bmax),
            'materials': [s.material.name for s in lod0.material_slots], 'root_bone': 'root', 'bones': [b.name for b in arm.data.bones],
            'head_bone': 'head', 'pelvis_bone': 'pelvis', 'class': 'creature', 'rotation_deg': [0, 0, 0], 'forward': '+X',
            'source_blend': 'SK_Duck.blend', 'body_boxes': [fitted_box(p) for p in box_pts], 'body_boxes_note': blend_note}


intact_row = skel_row(asset, ob, [body_pts, head_pts], 'Measured rest-surface AABBs of trunk and neck/head, excluding tail fan and feet; 1 cm padding, actor-forward UE cm.')
manifest = {'schema': 'dink-creature-art/1', 'assets': {'SK_Duck': intact_row}, 'materials': materials, 'animations': animations,
            'source': 'Original project-authored domestic (Pekin-type) duck anatomy, procedural materials, own 23-bone rig and actions; no third-party geometry/textures.',
            'export_units': 'Source metres; temporary mesh/edit-bone/action-location coordinates 100x, scene 0.01 and FBX header 1 cm; identity root, no leaf bones.',
            'origins_note': 'Draft: no origins are applied. duck_origins.json lists the original duck placements (Quackers = s1-oldd).',
            'variants_manifest': 'duck_gore_manifest.json',
            'status': 'candidate', 'appearance_revision': 'pekin-white-v2-feathered'}
(D.ROOT / 'duck_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

hl0 = bpy.data.objects['SK_Duck_Headless_LOD0']
hco = np.array([v.co for v in hl0.data.vertices])
headless_row = skel_row(h_asset, hl0, [hco[(hco[:, 0] < 0.13) & (hco[:, 0] > -0.20) & (hco[:, 2] > 0.07) & (hco[:, 2] < 0.29)]],
                        'Trunk AABB only (no head); 1 cm padding, actor-forward UE cm.')
hmin, hmax = common.world_bounds(head_asset.lod0())
neck_head = arm.data.bones['neck_02'].head_local
gore = {
    'schema': 'dink-creature-variants/1',
    'base_manifest': 'duck_manifest.json',
    'skeleton_from': 'SK_Duck',
    'variants': {'SK_Duck_Headless': dict(headless_row, import_against_skeleton_of='SK_Duck',
                                           notes='Same 23-bone hierarchy and bind pose as SK_Duck (one source armature). Import with the SK_Duck '
                                                 'Skeleton so every Duck clip plays on it. Wound cap and blood runs use MI_Duck_Feather (opacity mask).')},
    'props': {'SM_Duck_Head': {
        'fbx': 'Export/SM_Duck_Head_LOD0.fbx', 'lod_fbx': ['Export/SM_Duck_Head_LOD%d.fbx' % i for i in range(3)],
        'class': 'prop_small', 'collision': 'UCX_SM_Duck_Head_LOD0_01 (single convex hull, in the LOD0 FBX)',
        'dimensions_m': list(hmax - hmin), 'materials': [s.material.name for s in head_asset.lod0().material_slots],
        'material_note': 'Eye faces use MI_Duck_Feather on the prop (2-slot prop_small budget); gloss comes from the ORM roughness.',
        'pivot': 'base centre of the head-with-stub at rest',
        'rest_offset_from_duck_root_m': head_rest_offset_m,
        'spawn_from_bone': 'neck_03', 'physics': 'Simulate physics on the UCX hull; suggested mass 0.12 kg, linear damping 0.6, angular damping 0.4.'}},
    'decals': {
        'blood_pool': {'BC': 'Textures/T_Duck_BloodPool_BC.png', 'N': 'Textures/T_Duck_BloodPool_N.png', 'ORM': 'Textures/T_Duck_BloodPool_ORM.png',
                       'size_cm': 30, 'notes': 'Deferred decal, BC alpha = opacity; wet roughness in ORM.G.'},
        'blood_spatter': {'BC': 'Textures/T_Duck_BloodSpatter_BC.png', 'N': 'Textures/T_Duck_BloodSpatter_N.png', 'ORM': 'Textures/T_Duck_BloodSpatter_ORM.png',
                          'size_cm': 25, 'notes': 'Random drip decal for the headless run (original random_blood seq 187-189).'}},
    'original_behaviour': {
        'source': 'source/dink/dink.cpp duck_brain (D:12723) and one_time_brain (D:15741); dink.ini seq 111-129',
        'first_hit': ['draw_damage, add_exp, kill script (die/die5 sets editor_type 6 so the duck stays dead)',
                      'spawn the head: brain 5 one-shot, seq 121-129 (4 frames x 125 ms = 0.5 s), moving in the duck direction at speed 1-3, '
                      'then frozen into the background as a head in a pool of blood',
                      'body switches to base_walk 110 (bloody headless walk, 4 frames x 75 ms loop = 0.3 s), speed 1, keeps wandering like a live duck',
                      'while headless: 1 % chance per think to drop a random blood splat (seq 187-189)'],
        'second_hit': ['magic flash effect seq 164 at the body, add_exp, check_for_duck_script (duckdie), the body is removed at once'],
        'remaster_wiring': ['On first hit: swap the component mesh SK_Duck -> SK_Duck_Headless (same skeleton), play HeadlessRun at the brain speed.',
                            'Spawn SM_Duck_Head at the neck_03 bone transform with a small impulse along the duck heading (original speed 1-3) plus spin; '
                            'when it settles, place the blood_pool decal under it.',
                            'While headless, 1 % per think: blood_spatter decal at the body.',
                            'On second hit: either the faithful instant removal with the seq-164 flash, or play HeadlessDeath (1.6 s, hold last frame) '
                            'and then remove; keep the original exp/script timing either way.',
                            'Non-gory alternatives remain available: Hit and Death on the intact SK_Duck.']},
    'tone': 'Darkly comic, not horror: the body keeps strutting and flapping as if nothing happened; blood is bright and wet, not lingered on.',
}
(D.ROOT / 'duck_gore_manifest.json').write_text(json.dumps(gore, indent=2) + '\n')
(D.ROOT / 'duck_pose_validation.json').write_text(json.dumps(pose_report, indent=2) + '\n')


def lod_rows(a):
    return [{'name': m.name, 'triangles': common.tri_count(m), 'vertices': len(m.data.vertices),
             'max_influences': max((sum(g.weight > 1e-6 for g in v.groups) for v in m.data.vertices), default=0),
             'dimensions_m': list(common.world_bounds(m)[1] - common.world_bounds(m)[0])} for m in a.renders]


(D.ROOT / 'duck_lod_report.json').write_text(json.dumps({
    'validation': verdict['summary'],
    'SK_Duck': {'make_lods_log': lod_log, 'normals': normal_report, 'lods': lod_rows(asset), 'feather_card_fraction_per_lod': [1.0, 0.5, 0.22]},
    'SK_Duck_Headless': {'make_lods_log': h_lod_log, 'normals': h_normal_report, 'lods': lod_rows(h_asset)},
    'SM_Duck_Head': {'make_lods_log': head_lod_log, 'collision_log': head_col_log, 'normals': head_report, 'lods': lod_rows(head_asset)},
    'texture': tstats}, indent=2) + '\n')
if os.environ.get('DUCK_VALIDATE_ONLY'):
    print('DUCK SOURCE VALIDATION OK', verdict['summary'], flush=True)
    sys.exit(0)

# ------------------------------------------------------------------ export copy in centimetres (never saved)
for m in asset.renders + h_asset.renders + head_asset.renders + head_asset.collision:
    for v in m.data.vertices:
        v.co *= 100
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones:
    b.head *= 100
    b.tail *= 100
bpy.ops.object.mode_set(mode='OBJECT')
scene.unit_settings.scale_length = 0.01
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag = strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        if curve.data_path.endswith('.location'):
                            for kp in curve.keyframe_points:
                                kp.co.y *= 100
                                kp.handle_left.y *= 100
                                kp.handle_right.y *= 100
for material in bpy.data.materials:
    if material.node_tree:
        material.node_tree.nodes.clear()
D.EXPORT.mkdir(exist_ok=True)
for a in (asset, h_asset):
    for lod in range(3):
        mesh = bpy.data.objects['%s_LOD%d' % (a.name, lod)]
        proxy = type('ExportAsset', (), {'renders': [mesh], 'collision': [], 'armatures': [arm], 'sockets': []})()
        with export_ue.unhidden([mesh, arm]):
            export_ue.export_fbx(proxy, str(D.EXPORT / ('%s_LOD%d.fbx' % (a.name, lod))), 'all', 'Armature')
for lod in range(3):
    mesh = bpy.data.objects['SM_Duck_Head_LOD%d' % lod]
    proxy = type('ExportAsset', (), {'renders': [mesh], 'collision': head_asset.collision if lod == 0 else [], 'armatures': [], 'sockets': []})()
    with export_ue.unhidden([mesh] + list(proxy.collision)):
        export_ue.export_fbx(proxy, str(D.EXPORT / ('SM_Duck_Head_LOD%d.fbx' % lod)), 'all', None)
arm.data.pose_position = 'POSE'
for name, row in actions.items():
    k = key_names[name]
    arm.animation_data.action = bpy.data.actions[name]
    if arm.animation_data.action_slot is None:
        arm.animation_data.action_slot = bpy.data.actions[name].slots[0]
    scene.frame_start, scene.frame_end = row['frames']
    scene.frame_set(scene.frame_start)
    bpy.ops.object.select_all(action='DESELECT')
    arm.hide_set(False)
    arm.hide_viewport = False
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=str(D.ROOT / animations[k]['fbx']), use_selection=True, object_types={'ARMATURE'},
                             apply_unit_scale=True, global_scale=1, apply_scale_options='FBX_SCALE_ALL',
                             axis_forward='Y', axis_up='Z', bake_space_transform=False, use_space_transform=True,
                             add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X', use_armature_deform_only=False,
                             armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_step=1,
                             bake_anim_simplify_factor=0, path_mode='STRIP', embed_textures=False, use_custom_props=False)
print('DUCK EXPORT OK: SK_Duck + SK_Duck_Headless (3 LODs each), SM_Duck_Head (3 LODs + UCX), %d actions, %d bones; SOURCE VALIDATION %s'
      % (len(actions), len(arm.data.bones), verdict['summary']), flush=True)
