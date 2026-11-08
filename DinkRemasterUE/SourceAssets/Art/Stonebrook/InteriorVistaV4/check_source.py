import array, hashlib, json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'SourceAssets/Art/Stonebrook/InteriorVistaV4'
BASE = ROOT / 'SourceAssets/Art/Stonebrook/InteriorVistaV3/Stonebrook_InteriorVista_Candidate_V3.blend'

def mesh_digest(mesh):
    h = hashlib.sha256()
    values = array.array('f', [0]) * (len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', values)
    h.update(values.tobytes())
    indices = array.array('i', [0]) * len(mesh.loops)
    mesh.loops.foreach_get('vertex_index', indices)
    h.update(indices.tobytes())
    for uv in mesh.uv_layers:
        values = array.array('f', [0]) * (len(uv.data) * 2)
        uv.data.foreach_get('uv', values)
        h.update(values.tobytes())
    return h.hexdigest()

def snapshot():
    mesh_hashes = {}
    result = {}
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        digest = mesh_hashes.setdefault(ob.data.name, mesh_digest(ob.data))
        result[ob.name] = {'mesh': ob.data.name, 'geometry_uv_sha256': digest,
            'location': list(ob.location), 'rotation': list(ob.rotation_euler), 'scale': list(ob.scale),
            'materials': [m.name if m else None for m in ob.data.materials], 'hide_render': ob.hide_render}
    return result

base_hash = hashlib.sha256(BASE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE))
before = snapshot()
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Stonebrook_HorizonV4.blend'))
after = snapshot()
changed = [name for name, state in before.items() if after.get(name) != state]
added = sorted(set(after) - set(before))
assert not changed, changed
assert len(added) == 43 and all(name.startswith('VistaV4_') for name in added), added
missing = [image.name for image in bpy.data.images if image.source == 'FILE' and
           not Path(bpy.path.abspath(image.filepath)).is_file()]
assert not missing, missing
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == base_hash
report = {'passed': True, 'base_scene_sha256': base_hash, 'existing_mesh_objects': len(before),
    'existing_mesh_transform_geometry_uv_material_changes': changed,
    'new_instances': added, 'new_instance_count': len(added), 'new_mesh_packages': 0,
    'missing_texture_references': missing, 'all_texture_paths_project_relative':
    all(image.filepath.startswith('//') for image in bpy.data.images if image.source == 'FILE'),
    'source_preview': 'Cycles CPU 12 samples at actual native door camera pose; no hero or native indoor lighting; not a game screenshot'}
(OUT / 'source-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print('HORIZON SOURCE CHECK PASS:', len(before), 'old mesh objects preserved;', len(added), 'new instances')
