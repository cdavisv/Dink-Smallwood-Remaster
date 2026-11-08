"""Pure source validation and incremental runtime merge for own-rig creature art."""
import json
from pathlib import Path
import re

BUDGETS = {'creature_quadruped': (3, 4), 'creature': (3, 6)}


def load_source(creatures_root, relative_manifest):
    root = Path(creatures_root).resolve()
    manifest = (root / relative_manifest).resolve()
    if not manifest.is_relative_to(root) or not manifest.is_file():
        raise ValueError('Creature manifest must be a file inside SourceAssets/Art/Creatures')
    spec = json.loads(manifest.read_text())
    validate_source(spec, manifest.parent)
    return manifest.parent, spec


def asset_origins(spec, asset):
    return asset.get('origins', spec.get('origins', []) if len(spec['assets']) == 1 else [])


def validate_source(spec, source):
    source = Path(source).resolve()
    if spec.get('schema') != 'dink-creature-art/1':
        raise ValueError('Unsupported creature source manifest')
    if not spec.get('assets') or not spec.get('materials'):
        raise ValueError('Creature source needs assets and materials')
    actions = spec.get('animations', {})
    if not all(action in actions for action in ['Idle', 'Walk']):
        raise ValueError('Creature source requires Idle and Walk actions')
    required = []
    origins = set()
    for name, asset in spec['assets'].items():
        if not re.fullmatch(r'SK_[A-Za-z0-9_]+', name):
            raise ValueError('Invalid creature asset name: ' + name)
        creature_class = asset.get('class', 'creature_quadruped')
        if creature_class not in BUDGETS:
            raise ValueError('Unsupported creature class: ' + creature_class)
        lod_count, material_budget = BUDGETS[creature_class]
        if len(asset.get('lod_fbx', [])) != lod_count:
            raise ValueError(name + ': requires three explicit single-LOD FBX files')
        dimensions = asset.get('dimensions_m', [])
        if len(dimensions) != 3 or min(dimensions) <= 0:
            raise ValueError(name + ': invalid physical dimensions')
        if not asset.get('bones') or len(set(asset['bones'])) != len(asset['bones']):
            raise ValueError(name + ': missing or duplicated bone inventory')
        if not asset.get('body_boxes'):
            raise ValueError(name + ': missing measured body boxes')
        for box in asset['body_boxes']:
            if len(box.get('offset_cm', [])) != 3 or len(box.get('extent_cm', [])) != 3 or min(box['extent_cm']) <= 0:
                raise ValueError(name + ': invalid body box')
        if not asset.get('materials') or len(asset['materials']) > material_budget:
            raise ValueError(name + ': material budget exceeded')
        if any(material not in spec['materials'] for material in asset['materials']):
            raise ValueError(name + ': undefined material')
        if not asset_origins(spec, asset):
            raise ValueError(name + ': explicit original actor IDs are required')
        for origin in asset_origins(spec, asset):
            match = re.fullmatch(r'S(\d{3})_P(\d{2})', origin)
            if not match or not (1 <= int(match[1]) <= 768 and 1 <= int(match[2]) <= 99) or origin in origins:
                raise ValueError('Invalid or duplicated original actor ID: ' + str(origin))
            origins.add(origin)
        required += [asset['fbx'], *asset['lod_fbx']]
    for name, action in actions.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name) or action.get('fps', 30) <= 0:
            raise ValueError('Invalid animation contract: ' + name)
        if name in ['Walk', 'Run'] and action.get('nominal_speed_cm_s', 0) <= 0:
            raise ValueError(name + ': positive nominal speed is required')
        required.append(action['fbx'])
    if 'Run' in actions and actions['Run']['nominal_speed_cm_s'] <= actions['Walk']['nominal_speed_cm_s']:
        raise ValueError('Run nominal speed must exceed Walk')
    if spec.get('food_mesh') and 'Feed' not in actions:
        raise ValueError('Food presentation requires an authored Feed action')
    for material in spec['materials'].values():
        required += list(material.get('textures', {}).values())
    for filename in required:
        path = (source / filename).resolve()
        if not path.is_relative_to(source) or not path.is_file():
            raise ValueError('Missing or escaped creature source: ' + str(filename))


def merge_runtime(previous, current):
    """Replace only imported meshes' placements; retain all unrelated creature art."""
    for data in [previous, current]:
        if data.get('schema') != 'dink-creatures/1':
            raise ValueError('Cannot merge unsupported creature runtime schema')
        for field, key in [('assets', 'mesh'), ('placements', 'origin')]:
            values = [row[key] for row in data.get(field, [])]
            if len(values) != len(set(values)):
                raise ValueError('Duplicate creature runtime ' + field)
    meshes = {row['mesh'] for row in current.get('assets', [])}
    if not meshes or any(row['mesh'] not in meshes for row in current.get('placements', [])):
        raise ValueError('New creature placements must reference their imported assets')
    retained = [row for row in previous.get('placements', []) if row['mesh'] not in meshes]
    retained_origins = {row['origin'] for row in retained}
    if any(row['origin'] in retained_origins for row in current.get('placements', [])):
        raise ValueError('New creature would replace an unrelated original actor')
    result = {**previous, **current}
    result['assets'] = [row for row in previous.get('assets', []) if row['mesh'] not in meshes] + current['assets']
    result['placements'] = retained + current.get('placements', [])
    return result
