"""Check the editable V4 scene against its immutable base and placement source."""
import array
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'SourceAssets/Art/Stonebrook/InteriorVistaV4'
BASE = ROOT / 'SourceAssets/Art/Stonebrook/InteriorVistaV3/Stonebrook_InteriorVista_Candidate_V3.blend'
SCENE = OUT / 'Stonebrook_HorizonV4.blend'
ADDITIONS = OUT / 'additions.json'
ASSET_PATHS = {
    'SM_Grass_Meadow_01': '/Game/Dink/Kits/StonebrookExterior/SM_Grass_Meadow_01.SM_Grass_Meadow_01',
    'SM_Pine_Stonebrook_V3': '/Game/Dink/Foliage/StonebrookFields/Refinements/SM_Pine_Stonebrook_V3.SM_Pine_Stonebrook_V3',
}
ANCHOR_CM = (-183806.0975, 393595.98, 0.)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_digest(mesh):
    h = hashlib.sha256()
    fields = [(mesh.vertices, 'co', 'f', 3), (mesh.loops, 'vertex_index', 'i', 1),
              (mesh.polygons, 'loop_start', 'i', 1), (mesh.polygons, 'loop_total', 'i', 1),
              (mesh.polygons, 'material_index', 'i', 1), (mesh.polygons, 'use_smooth', 'b', 1),
              (mesh.edges, 'vertices', 'i', 2), (mesh.edges, 'use_edge_sharp', 'b', 1),
              (mesh.corner_normals, 'vector', 'f', 3)]
    for collection, field, typecode, width in fields:
        values = array.array(typecode, [0]) * (len(collection) * width)
        collection.foreach_get(field, values)
        h.update(values.tobytes())
    for uv in mesh.uv_layers:
        values = array.array('f', [0]) * (len(uv.data) * 2)
        uv.data.foreach_get('uv', values)
        h.update(uv.name.encode() + values.tobytes())
    return h.hexdigest()


def snapshot():
    bpy.context.view_layer.update()
    mesh_hashes, result = {}, {}
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        key = ob.data.as_pointer()
        if key not in mesh_hashes:
            mesh_hashes[key] = mesh_digest(ob.data)
        result[ob.name] = {
            'mesh': ob.data.name, 'geometry_uv_material_smoothing_normals_sha256': mesh_hashes[key],
            'location': list(ob.location), 'rotation': list(ob.rotation_euler),
            'scale': list(ob.scale), 'rotation_mode': ob.rotation_mode,
            'matrix_world': [list(row) for row in ob.matrix_world],
            'matrix_parent_inverse': [list(row) for row in ob.matrix_parent_inverse],
            'parent': ob.parent.name if ob.parent else None,
            'materials': [m.name if m else None for m in ob.data.materials],
            'material_slots': [(slot.link, slot.material.name if slot.material else None)
                               for slot in ob.material_slots],
            'hide_render': ob.hide_render,
        }
    return result


def vector(row, key):
    value = row.get(key)
    if not isinstance(value, list) or len(value) != 3 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in value):
        raise ValueError('Invalid composition vector: ' + key)
    return value


def template_for(asset):
    return (bpy.data.objects.get(asset) or bpy.data.objects.get(asset + '_LOD0') or
            next((ob for ob in bpy.data.objects if ob.type == 'MESH' and
                  ob.data.name.startswith(asset)), None))


def check_added(row):
    name, asset = row.get('name'), row.get('reused_asset')
    if not isinstance(name, str) or not name.startswith('VistaV4_') or asset not in ASSET_PATHS:
        raise ValueError('Unexpected V4 instance identity')
    if row.get('asset_path_proposal') != ASSET_PATHS[asset]:
        raise ValueError('V4 asset path differs from source identity: ' + name)
    if row.get('collision') is not False or row.get('camera_occluder') is not False:
        raise ValueError('V4 must remain cosmetic: ' + name)
    location, scale = vector(row, 'local_blender_m'), vector(row, 'scale')
    world = vector(row, 'world_cm_proposal')
    yaw, ue_yaw = row.get('blender_yaw_deg'), row.get('UE_yaw_deg')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in (yaw, ue_yaw)) or any(v <= 0 for v in scale):
        raise ValueError('Invalid V4 orientation or scale: ' + name)
    ob, template = bpy.data.objects.get(name), template_for(asset)
    if ob is None or ob.type != 'MESH' or template is None or ob.data != template.data:
        raise ValueError('V4 instance mesh differs from source asset: ' + name)
    if ob.parent is not None or ob.constraints or ob.modifiers or ob.hide_render or not ob.visible_camera:
        raise ValueError('V4 instance cannot reproduce this object policy: ' + name)
    if any(collection.hide_render for collection in ob.users_collection):
        raise ValueError('V4 instance belongs to a hidden render collection: ' + name)
    if [(s.link, s.material) for s in ob.material_slots] != [
            (s.link, s.material) for s in template.material_slots]:
        raise ValueError('V4 material override is absent from placement Data: ' + name)
    expected = Matrix.LocRotScale(Vector(location), Euler((0, 0, math.radians(yaw))).to_quaternion(),
                                 Vector(scale))
    if max(abs(a - b) for x, y in zip(expected, ob.matrix_world) for a, b in zip(x, y)) > 1e-5:
        raise ValueError('V4 instance transform differs from additions.json: ' + name)
    # Blender stores object coordinates as float32; proposal arithmetic can retain
    # the original Python doubles. Permit only a ten-micrometre world delta.
    derived = [ANCHOR_CM[0] + ob.location.x * 100,
               ANCHOR_CM[1] - ob.location.y * 100, ob.location.z * 100]
    if max(abs(a - b) for a, b in zip(world, derived)) > .001 or abs(ue_yaw + yaw) > 1e-6:
        raise ValueError('V4 world transform differs from Blender conversion: ' + name)
    return {'name': name, 'asset': asset, 'mesh': ob.data.name,
            'local_blender_m': list(ob.location), 'world_cm': derived,
            'blender_yaw_deg': yaw, 'scale': list(ob.scale)}


def main():
    base_hash, scene_hash, additions_hash = sha(BASE), sha(SCENE), sha(ADDITIONS)
    spec = json.loads(ADDITIONS.read_text())
    rows = spec.get('instances', [])
    if spec.get('schema') != 'dink-vista-composition-additions/1' or spec.get('base_scene_sha256') != base_hash:
        raise ValueError('V4 additions do not reference this immutable base')
    if spec.get('new_mesh_packages') != 0 or len(rows) != 43:
        raise ValueError('Unexpected V4 composition inventory')
    names = [row.get('name') for row in rows]
    if len(set(names)) != 43:
        raise ValueError('Duplicate V4 composition instance')
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    before = snapshot()
    bpy.ops.wm.open_mainfile(filepath=str(SCENE))
    after = snapshot()
    changed = [name for name, state in before.items() if after.get(name) != state]
    added = sorted(set(after) - set(before))
    if len(before) != 519 or changed or added != sorted(names):
        raise ValueError('V4 original/addition inventory changed: ' + repr(changed or added))
    checked = [check_added(row) for row in rows]
    missing = [im.name for im in bpy.data.images if im.source == 'FILE' and
               not Path(bpy.path.abspath(im.filepath)).is_file()]
    relative = all(im.filepath.startswith('//') for im in bpy.data.images if im.source == 'FILE')
    if missing or not relative:
        raise ValueError('V4 textures must resolve through relative paths: ' + repr(missing))
    if (sha(BASE), sha(SCENE), sha(ADDITIONS)) != (base_hash, scene_hash, additions_hash):
        raise ValueError('Composition inputs changed while checking')
    report = {'schema': 'dink-vista-source-verification/2', 'passed': True,
              'base_scene_sha256': base_hash, 'composition_scene_sha256': scene_hash,
              'composition_additions_sha256': additions_hash, 'existing_mesh_objects': len(before),
              'existing_mesh_transform_geometry_uv_material_changes': changed,
              'new_instances': added, 'new_instance_count': len(added), 'checked_instances': checked,
              'new_mesh_packages': 0, 'missing_texture_references': missing,
              'all_texture_paths_project_relative': relative,
              'source_preview': 'Cycles CPU source preview; not native rendered acceptance'}
    (OUT / 'source-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('HORIZON SOURCE CHECK PASS: 519 originals preserved; 43 mesh identities/transforms checked')


if __name__ == '__main__':
    main()
