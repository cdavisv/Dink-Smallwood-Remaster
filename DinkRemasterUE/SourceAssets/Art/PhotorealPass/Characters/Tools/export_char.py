"""Validate and export an assembled photoreal character the way the Characters README prescribes:
dinkasset validator, then a process-only centimetre copy (verts and edit bones x100, unit scale .01, FBX_SCALE_ALL,
'Armature' wrapper, no leaf bones), one FBX per LOD. The .blend is not saved.
blender -b <SK_X_Photoreal.blend> -P export_char.py -- <export dir> <report.json>"""
import bpy, json, os, sys
from pathlib import Path
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
EXPORT, REPORT = Path(argv[0]), Path(argv[1])
repo = next(p for p in Path(__file__).resolve().parents if (p / 'tools/blender/dinkasset').is_dir())
sys.path.insert(0, str(repo / 'tools/blender'))
from dinkasset import common, validate, export_ue
scene = bpy.context.scene; arm = bpy.data.objects['Armature']
if arm.animation_data: arm.animation_data.action = None
arm.data.pose_position = 'REST'
lod0 = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith('_LOD0')); base = lod0.name[:-5]
coll = bpy.data.collections.get(base) or bpy.data.collections.new(base)
if coll.name not in [c.name for c in scene.collection.children]: scene.collection.children.link(coll)
for o in [arm] + [bpy.data.objects[f'{base}_LOD{i}'] for i in range(4)]:
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o)
coll['dink_class'] = argv[2] if len(argv) > 2 else 'character_hero'
for o in list(bpy.data.objects):
    if o.name not in coll.objects: bpy.data.objects.remove(o, do_unlink=True)
asset = common.Asset(coll); normals = []
for ob in asset.renders:
    ob.data.update(); zero = {i for i, n in enumerate(ob.data.corner_normals) if n.vector.length < 1e-4}; flat = 0
    for face in ob.data.polygons:
        if any(i in zero for i in face.loop_indices): face.use_smooth = False; flat += 1
    normals.append({'mesh': ob.name, 'flat_faces_for_cancelled_normals': flat})
verdict = validate.validate_scene(only=[coll.name])
finds = [(f['severity'], f['code'], f['message'][:200]) for a in verdict['assets'] for f in a['findings']]
for f in finds: print('VALIDATION', *f, flush=True)
bounds = [common.world_bounds(o) for o in asset.renders]; lo, hi = common.world_bounds(lod0)
def infl(o): return max((len([g for g in v.groups if g.weight > 0]) for v in o.data.vertices), default=0)
report = {'asset': base, 'validation': verdict['summary'], 'findings': finds, 'normals': normals,
          'lods': [{'mesh': o.name, 'triangles': common.tri_count(o), 'vertices': len(o.data.vertices), 'max_influences': infl(o),
                    'unweighted': sum(1 for v in o.data.vertices if not v.groups),
                    **({'shape_keys': [k.name for k in o.data.shape_keys.key_blocks[1:]]} if o.data.shape_keys else {})} for o in asset.renders],
          'bones': [b.name for b in arm.data.bones], 'bone_count': len(arm.data.bones), 'dimensions_m': list(hi - lo),
          'materials': [s.material.name for s in lod0.material_slots]}
# the validator tests UV0 across the whole mesh; this asset has one texture set per slot, so test each slot on its own
import numpy as np
def slot_uv(o):
    me = o.data; me.calc_loop_triangles(); n = len(me.loop_triangles)
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    tl = np.empty(n * 3, np.int32); me.loop_triangles.foreach_get('loops', tl); mi = np.empty(n, np.int32); me.loop_triangles.foreach_get('material_index', mi)
    T = uv[tl].reshape(-1, 3, 2); out = {}; N = 1024
    for s, slot in enumerate(o.material_slots):
        t = T[mi == s]; e1 = t[:, 1] - t[:, 0]; e2 = t[:, 2] - t[:, 0]; area = float(np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum() / 2)
        grid = np.zeros((N, N), np.int16)        # count triangle centroids and edge midpoints per texel as a cheap overlap probe
        cnt = np.zeros((N, N), bool)
        for k in range(0, len(t), 1):
            a, b, c = t[k]; mn = np.floor(np.minimum(np.minimum(a, b), c) * N).astype(int).clip(0, N - 1); mx = np.ceil(np.maximum(np.maximum(a, b), c) * N).astype(int).clip(0, N)
            if (mx - mn).min() <= 0 or (mx[0] - mn[0]) * (mx[1] - mn[1]) > 40000: continue
            ys, xs = np.mgrid[mn[1]:mx[1], mn[0]:mx[0]]; p = np.stack([(xs + .5) / N, (ys + .5) / N], -1)
            d = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(d) < 1e-12: continue
            w1 = ((p[..., 0] - a[0]) * (c[1] - a[1]) - (p[..., 1] - a[1]) * (c[0] - a[0])) / d; w2 = ((b[0] - a[0]) * (p[..., 1] - a[1]) - (b[1] - a[1]) * (p[..., 0] - a[0])) / d
            ins = (w1 > .02) & (w2 > .02) & (w1 + w2 < .98)
            grid[mn[1]:mx[1], mn[0]:mx[0]] += ins
        used = int((grid > 0).sum()); over = int((grid > 1).sum())
        out[slot.material.name] = {'uv_area': round(area, 4), 'texels_used_1k': used, 'texels_overlapping_1k': over, 'overlap_fraction': round(over / max(used, 1), 4),
                                   'outside_0_1': int(((t < -1e-4) | (t > 1 + 1e-4)).any(axis=(1, 2)).sum())}
    return out
report['uv_per_slot'] = slot_uv(lod0)
print('UV PER SLOT', json.dumps(report['uv_per_slot']), flush=True)
REPORT.write_text(json.dumps(report, indent=1) + '\n')
from mathutils import Matrix
for mesh in asset.renders:
    if mesh.data.shape_keys:        # shape keys hold their own coordinates: scale mesh and keys together
        for k in mesh.data.shape_keys.key_blocks: k.value = 0.0
        mesh.data.transform(Matrix.Scale(100, 4), shape_keys=True); mesh.data.update()
    else:
        for v in mesh.data.vertices: v.co *= 100
bpy.ops.object.select_all(action='DESELECT'); arm.hide_set(False); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones: b.head *= 100; b.tail *= 100
bpy.ops.object.mode_set(mode='OBJECT'); scene.unit_settings.scale_length = .01
for material in bpy.data.materials:
    if material.node_tree: material.node_tree.nodes.clear()
EXPORT.mkdir(parents=True, exist_ok=True)
for lod in range(4):
    m = bpy.data.objects[f'{base}_LOD{lod}']
    proxy = type('ExportAsset', (), {'renders': [m], 'collision': [], 'armatures': [arm], 'sockets': []})()
    if m.data.shape_keys:
        # Blender's FBX exporter drops shape keys whenever it has to evaluate the mesh (apply modifiers, triangulate).
        # The game meshes are triangles already and carry only the Armature modifier, so both can be switched off:
        # the geometry written is the same and the keys go out as FBX blend shapes (Unreal morph targets).
        if any(len(p.vertices) != 3 for p in m.data.polygons) or [x.type for x in m.modifiers] != ['ARMATURE']:
            raise RuntimeError(f'{m.name}: shape keys need a triangulated mesh with only the Armature modifier')
        with export_ue.unhidden([m, arm]), export_ue.renamed_armature(proxy, 'Armature'):
            common.select_only([m, arm])
            bpy.ops.export_scene.fbx(
                filepath=str(EXPORT / f'{base}_LOD{lod}.fbx'), use_selection=True, object_types={'MESH', 'ARMATURE', 'EMPTY'},
                use_mesh_modifiers=False, mesh_smooth_type='FACE', use_triangles=False, use_tspace=False,
                use_custom_props=False, colors_type='NONE', apply_unit_scale=True, global_scale=1.0,
                apply_scale_options=export_ue.FBX_SCALE_MODES['all'], axis_forward='Y', axis_up='Z', bake_space_transform=False,
                use_space_transform=True, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                use_armature_deform_only=False, armature_nodetype='NULL', bake_anim=False, path_mode='STRIP',
                embed_textures=False, batch_mode='OFF')
        continue
    with export_ue.unhidden([m, arm]): export_ue.export_fbx(proxy, str(EXPORT / f'{base}_LOD{lod}.fbx'), 'all', 'Armature')
print('EXPORT DONE', json.dumps({'asset': base, 'dims': report['dimensions_m'], 'validation': verdict['summary'], 'lods': [l['triangles'] for l in report['lods']]}), flush=True)
