"""Re-export a fixed hero source (SK_Dink.blend or SK_Dink_Hands.blend) the way its builder did.

blender -b <file.blend> -P export_fixed_hero.py -- <export dir> <validation.json> <lod_report.json>

Same steps as Characters/Tools/finalize_dink.py and HandBindingV2/Tools/export_hands.py: the
data repo's dinkasset validator, faces with cancelled smooth normals set flat, then a
process-only copy scaled x100 (centimetre FBX, unit scale 0.01, identity root, Armature
wrapper, no leaf bones) with material graphs cleared, one FBX per LOD. The .blend is not saved.
"""
import bpy, json, os, sys
from pathlib import Path
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
EXPORT, VALIDATION, LOD_REPORT = Path(argv[0]), Path(argv[1]), Path(argv[2])
project = next(p for p in Path(bpy.data.filepath).resolve().parents if (p / 'DinkRemaster.uproject').exists())
candidates = [os.environ.get('DINK_BLENDER_TOOLS', ''), project.parent / 'tools/blender',
              project.parent / 'Dink-Smallwood-Remaster/tools/blender', Path.home() / 'Repos/Dink-Smallwood/Dink-Smallwood-Remaster/tools/blender']
tools = next(Path(c) for c in candidates if c and (Path(c) / 'dinkasset').is_dir())
sys.path.insert(0, str(tools))
from dinkasset import common, validate, export_ue

scene = bpy.context.scene
arm = bpy.data.objects['Armature']
if arm.animation_data: arm.animation_data.action = None
arm.data.pose_position = 'REST'
coll = next(c for c in bpy.data.collections if any(o.name == c.name + '_LOD0' for o in c.objects))
asset = common.Asset(coll)
normals = []
for ob in asset.renders:
    ob.data.update(); zero = {i for i, n in enumerate(ob.data.corner_normals) if n.vector.length < 1e-4}; flat = 0
    for face in ob.data.polygons:
        if any(i in zero for i in face.loop_indices): face.use_smooth = False; flat += 1
    ob.data.update(); remaining = sum(n.vector.length < 1e-4 for n in ob.data.corner_normals)
    if remaining: raise RuntimeError('Zero normals ' + ob.name)
    normals.append({'mesh': ob.name, 'flat_faces_for_cancelled_normals': flat, 'zero_normals_remaining': remaining})
verdict = validate.validate_scene(only=[coll.name])
VALIDATION.write_text(json.dumps(verdict, indent=2) + '\n')
if verdict['summary']['errors']:
    for a in verdict['assets']:
        for f in a['findings']:
            if f['severity'] == 'error': print('VALIDATION ERROR', f['code'], f['message'], flush=True)
    raise RuntimeError('source guide gate failed')
lod0 = bpy.data.objects[coll.name + '_LOD0']
lo, hi = common.world_bounds(lod0)
bounds = [common.world_bounds(o) for o in asset.renders]
mn = Vector(tuple(min(b[0][i] for b in bounds) for i in range(3))); mx = Vector(tuple(max(b[1][i] for b in bounds) for i in range(3)))
report = {'validation': verdict['summary'], 'normals': normals,
          'lods': [{'mesh': o.name, 'triangles': common.tri_count(o), 'vertices': len(o.data.vertices)} for o in asset.renders],
          'rest_rig_bones': len(arm.data.bones), 'dimensions_m': list(hi - lo), 'lod_union_dimensions_m': list(mx - mn),
          'materials': [s.material.name for s in lod0.material_slots]}
LOD_REPORT.write_text(json.dumps(report, indent=2) + '\n')
# process-only centimetre copy
for mesh in asset.renders:
    for v in mesh.data.vertices: v.co *= 100
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for b in arm.data.edit_bones: b.head *= 100; b.tail *= 100
bpy.ops.object.mode_set(mode='OBJECT'); scene.unit_settings.scale_length = .01
for material in bpy.data.materials:
    if material.node_tree: material.node_tree.nodes.clear()
    material.use_nodes = False
EXPORT.mkdir(parents=True, exist_ok=True)
for lod in range(4):
    m = bpy.data.objects[f'{coll.name}_LOD{lod}']
    proxy = type('ExportAsset', (), {'renders': [m], 'collision': [], 'armatures': [arm], 'sockets': []})()
    with export_ue.unhidden([m, arm]): export_ue.export_fbx(proxy, str(EXPORT / f'{coll.name}_LOD{lod}.fbx'), 'all', 'Armature')
print('HERO EXPORT PASS', json.dumps({'asset': coll.name, 'dimensions_m': report['dimensions_m'], 'validation': verdict['summary']}), flush=True)
