#!/usr/bin/env python3
"""Build the cosmetic context manifest from the reviewed Blender compositions."""
import argparse
import json
from pathlib import Path

from vista_import_support import sha, validate_bundle


def build(project):
    source = project / 'SourceAssets/Art/Stonebrook/InteriorVistaV3'
    _, proposal, bundle_sha = validate_bundle(source)
    revision = project / 'SourceAssets/Art/Stonebrook/InteriorVistaV4'
    additions_path = revision / 'additions.json'
    additions = json.loads(additions_path.read_text())
    if additions.get('base_scene_sha256') != sha(source / 'Stonebrook_InteriorVista_Candidate_V3.blend'):
        raise ValueError('Horizon composition references a different source scene')
    if additions.get('new_mesh_packages') != 0 or len(additions.get('instances', [])) != 43:
        raise ValueError('Unexpected horizon composition inventory')
    scene_sha = sha(revision / 'Stonebrook_HorizonV4.blend')
    additions_sha = sha(additions_path)
    receipt_path = revision / 'source-verification.json'
    if not receipt_path.is_file():
        raise ValueError('Run the V4 Blender source checker before building context Data')
    receipt = json.loads(receipt_path.read_text())
    if not isinstance(receipt, dict) or receipt.get('schema') != 'dink-vista-source-verification/2' or receipt.get('passed') is not True:
        raise ValueError('V4 source verification is missing or failed')
    if receipt.get('composition_scene_sha256') != scene_sha or receipt.get('composition_additions_sha256') != additions_sha:
        raise ValueError('V4 source verification is stale for scene/additions')
    if receipt.get('base_scene_sha256') != additions['base_scene_sha256'] or receipt.get('existing_mesh_objects') != 519 or receipt.get('existing_mesh_transform_geometry_uv_material_changes') != []:
        raise ValueError('V4 source verification does not preserve the 519-object baseline')
    names = sorted(row['name'] for row in additions['instances'])
    checked = receipt.get('checked_instances', [])
    if receipt.get('new_instance_count') != 43 or receipt.get('new_mesh_packages') != 0 or receipt.get('new_instances') != names or len(checked) != 43 or sorted(row.get('name', '') for row in checked) != names:
        raise ValueError('V4 source verification did not check all 43 additions')
    if receipt.get('missing_texture_references') != [] or receipt.get('all_texture_paths_project_relative') is not True:
        raise ValueError('V4 source verification has unresolved texture references')
    rows = []
    for index, placement in enumerate(proposal['instances'] + additions['instances']):
        if placement['collision'] is not False or placement['camera_occluder'] is not False:
            raise ValueError('Cosmetic context cannot own collision or camera policy')
        name = ('Vista_%03d_%s' % (index, placement['name']) if index < 316 else placement['name'])
        rows.append({'name': name, 'mesh': placement['asset_path_proposal'],
                     'world_cm': placement['world_cm_proposal'],
                     'rotation_deg': [0, placement['UE_yaw_deg'], 0],
                     'scale': placement['scale'], 'collision': False, 'camera_occluder': False})
    if len(rows) != 359 or len({row['name'] for row in rows}) != 359:
        raise ValueError('Unexpected or duplicate context instances')
    return {'schema': 'dink-art/1', 'screen': 1,
            'context': {'visibility': 'owner_screen_only', 'render_only': True},
            'elements': rows,
            'source_provenance': {'source_bundle_sha256': bundle_sha,
                'composition_source': str(revision.relative_to(project) / 'Stonebrook_HorizonV4.blend'),
                'composition_scene_sha256': scene_sha,
                'composition_additions_sha256': additions_sha}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='Explicit destination, including a private QA manifest path')
    parser.add_argument('--check', action='store_true', help='Compare the destination without writing it')
    args = parser.parse_args()
    manifest = build(Path(__file__).resolve().parent.parent)
    if args.check:
        if json.loads(args.output.read_text()) != manifest:
            raise SystemExit('Context manifest differs from reviewed source compositions')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, indent=2) + '\n')
    print('VISTA CONTEXT OK: 359 render-only placements from reviewed Blender sources')


if __name__ == '__main__':
    main()
