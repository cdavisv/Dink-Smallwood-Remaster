"""Import authored Blender humans only after independent bind-pose validation.
Run with import_character_art.sh. Preserves the existing mannequin Skeleton asset.
"""
import json
import math
import os
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
SOURCE = ROOT / 'SourceAssets/Art/Characters'
SPEC = json.loads((SOURCE / os.environ.get('DINK_CHARACTER_MANIFEST','character_manifest.json')).read_text())
MERGE_RUNTIME = os.environ.get('DINK_CHARACTER_MERGE_RUNTIME') == '1'
PREVIOUS_RUNTIME = None
if MERGE_RUNTIME:
    previous_path = ROOT / 'Content/Dink/Data/Art/characters.json'
    if previous_path.exists():
        PREVIOUS_RUNTIME = json.loads(previous_path.read_text())
        if PREVIOUS_RUNTIME.get('schema') != 'dink-characters/1':
            raise RuntimeError('Cannot merge an unsupported character runtime manifest')
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDIT = unreal.MaterialEditingLibrary
MATS = '/Game/Dink/Materials/Characters'
TEXTURES = '/Game/Dink/Textures/Characters'
DEST = '/Game/Dink/NPC/Mother'
WORLD = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(WORLD, 'Interchange.FeatureFlags.Import.FBX 0')


def save(asset):
    if not LIB.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def import_asset(path, folder, name, options=None, factory=None):
    task = unreal.AssetImportTask()
    task.filename = str((SOURCE / path).resolve())
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    if factory is not None:
        task.factory = factory
    TOOLS.import_asset_tasks([task])
    target = folder + '/' + name
    asset = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    if asset is None:
        raise RuntimeError(f'Import failed {path}: {task.imported_object_paths}')
    return asset


def expr(mat, cls, x=0, y=0, **props):
    node = EDIT.create_material_expression(mat, cls, x, y)
    for key, value in props.items():
        node.set_editor_property(key, value)
    return node


def scalar(mat, value, prop, y):
    node = expr(mat, unreal.MaterialExpressionConstant, -200, y, r=float(value))
    EDIT.connect_material_property(node, '', prop)


materials = {}
imported_textures = {}
for name, row in SPEC['materials'].items():
    path = MATS + '/' + name
    mat = LIB.load_asset(path) if LIB.does_asset_exist(path) else TOOLS.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    EDIT.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided', row.get('two_sided', False))
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if row.get('masked', row.get('alpha_mask', False)) else unreal.BlendMode.BLEND_OPAQUE)
    channels = {}
    for suffix, filename in row.get('textures', {}).items():
        if filename not in imported_textures:
            imported_textures[filename] = import_asset(filename, TEXTURES, Path(filename).stem)
        texture = imported_textures[filename]
        texture.set_editor_property('srgb', suffix == 'BC')
        if suffix == 'N':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('flip_green_channel', row.get('normal_flip_green', True))
        elif suffix == 'ORM':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        save(texture)
        sample = expr(mat, unreal.MaterialExpressionTextureSample, -700, len(channels) * 240, texture=texture)
        sample.set_editor_property('sampler_type', {'BC': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                                                  'N': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                                                  'ORM': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}[suffix])
        channels[suffix] = sample
    if 'BC' in channels:
        EDIT.connect_material_property(channels['BC'], 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
        if row.get('masked', row.get('alpha_mask', False)):
            EDIT.connect_material_property(channels['BC'], 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    else:
        color = expr(mat, unreal.MaterialExpressionConstant3Vector, -600, 0,
                     constant=unreal.LinearColor(*row.get('base_color', [.4, .3, .2]), 1))
        EDIT.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    if 'ORM' in channels:
        for pin, prop in [('R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                          ('G', unreal.MaterialProperty.MP_ROUGHNESS), ('B', unreal.MaterialProperty.MP_METALLIC)]:
            EDIT.connect_material_property(channels['ORM'], pin, prop)
    else:
        scalar(mat, row.get('roughness', .65), unreal.MaterialProperty.MP_ROUGHNESS, 200)
        scalar(mat, row.get('metallic', 0), unreal.MaterialProperty.MP_METALLIC, 300)
    if 'N' in channels:
        strength = float(row.get('normal_strength', .32))
        vec = expr(mat, unreal.MaterialExpressionConstant3Vector, -450, 600,
                   constant=unreal.LinearColor(strength, strength, 1, 1))
        mul = expr(mat, unreal.MaterialExpressionMultiply, -200, 600)
        norm = expr(mat, unreal.MaterialExpressionNormalize, 0, 600)
        EDIT.connect_material_expressions(channels['N'], 'RGB', mul, 'A')
        EDIT.connect_material_expressions(vec, '', mul, 'B')
        EDIT.connect_material_expressions(mul, '', norm, 'VectorInput')
        EDIT.connect_material_property(norm, '', unreal.MaterialProperty.MP_NORMAL)
    scalar(mat, .3, unreal.MaterialProperty.MP_SPECULAR, 400)
    EDIT.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    EDIT.recompile_material(mat)
    save(mat)
    materials[name] = mat

# Corrective mesh candidates can reuse immutable, already-reviewed character materials.
# Loading references must never rebuild/save the live hero's material/texture assets.
for name, path in SPEC.get('existing_materials', {}).items():
    if name in materials or not path.startswith('/Game/Dink/Materials/'):
        raise RuntimeError('Invalid or conflicting existing character material: '+name)
    material = LIB.load_asset(path)
    if material is None or not isinstance(material, unreal.MaterialInterface):
        raise RuntimeError('Missing existing character material: '+path)
    materials[name] = material

reference_mesh = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
reference = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(reference_mesh))
reference_by = {r['name']: r for r in reference['bones']}
original_skeleton = reference_mesh.get_editor_property('skeleton')
meshes = {}
reports = []
for name, row in SPEC['assets'].items():
    options = unreal.FbxImportUI()
    values = {'automated_import_should_detect_type': False,
              'mesh_type_to_import': unreal.FBXImportType.FBXIT_SKELETAL_MESH,
              'import_as_skeletal': True, 'import_mesh': True, 'import_materials': False,
              'import_textures': False, 'import_animations': False, 'create_physics_asset': True}
    for key, value in values.items():
        options.set_editor_property(key, value)
    # A new candidate gets its own temporary skeleton for inspection. Existing production
    # meshes retain the already-validated shared skeleton; never update its bind transforms.
    destination = row.get('content_folder', DEST)
    if not destination.startswith('/Game/Dink/'):
        raise RuntimeError('Character destination must be under /Game/Dink/')
    target = destination + '/' + name
    options.set_editor_property('skeleton', original_skeleton if LIB.does_asset_exist(target) else None)
    data = options.skeletal_mesh_import_data
    settings = {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.0,
                'update_skeleton_reference_pose': False, 'use_t0_as_ref_pose': False,
                'import_mesh_lods': False, 'import_meshes_in_bone_hierarchy': True,
                'normal_import_method': unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}
    for key, value in settings.items():
        data.set_editor_property(key, value)
    if LIB.does_asset_exist(target):
        old = LIB.load_asset(target).get_editor_property('asset_import_data')
        for key, value in settings.items():
            old.set_editor_property(key, value)
        old.scripted_add_filename(str((SOURCE / row['fbx']).resolve()), 0, '')
    mesh = import_asset(row['fbx'], destination, name, options, unreal.FbxFactory())
    actual = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(mesh))
    expected_size = [v * 100 for v in row['dimensions_m']]
    if any(abs(a-b) > 1.0 for a, b in zip(actual['bounds_size_cm'], expected_size)):
        raise RuntimeError(f'{name} dimensions mismatch: {actual["bounds_size_cm"]} expected {expected_size}')
    differences = []
    names = {r['name'] for r in actual['bones']}
    if names != set(reference_by):
        differences.append({'missing': sorted(set(reference_by)-names), 'extra': sorted(names-set(reference_by))})
    for bone in actual['bones']:
        expected = reference_by.get(bone['name'])
        if expected is None:
            continue
        parent = actual['bones'][bone['parent']]['name'] if bone['parent'] >= 0 else None
        expected_parent = reference['bones'][expected['parent']]['name'] if expected['parent'] >= 0 else None
        distance = math.dist(bone['translation_cm'], expected['translation_cm'])
        dot = abs(sum(a*b for a, b in zip(bone['rotation_xyzw'], expected['rotation_xyzw'])))
        angle = 2*math.acos(min(1, dot))
        if parent != expected_parent or distance > .1 or angle > .002 or math.dist(bone['scale'], expected['scale']) > .001:
            differences.append({'bone': bone['name'], 'parent': parent, 'expected_parent': expected_parent,
                                'translation_difference_cm': distance, 'rotation_difference_rad': angle})
    if differences:
        raise RuntimeError(f'{name} bind pose does not match shared animation rig: {differences[:8]}')
    # Assign only after the independent mesh bind pose has matched the original reference.
    if not unreal.DinkCharacterArtLibrary.assign_matching_skeleton(mesh, reference_mesh):
        raise RuntimeError(f'{name}: native bind-pose assignment gate rejected mesh')
    for index, filename in enumerate(row.get('lod_fbx', [])[1:], 1):
        if unreal.SkeletalMeshEditorSubsystem.import_lod(mesh, index, str((SOURCE / filename).resolve())) != index:
            raise RuntimeError(f'{name} LOD{index} import failed')
    slots = list(mesh.get_editor_property('materials'))
    for slot in slots:
        key = str(slot.get_editor_property('material_slot_name')).split('.')[0]
        if key not in materials:
            raise RuntimeError(f'{name}: unknown material slot {key}')
        slot.set_editor_property('material_interface', materials[key])
    mesh.set_editor_property('materials', slots)
    lod_count = unreal.SkeletalMeshEditorSubsystem.get_lod_count(mesh)
    expected_lods = len(row.get('lod_fbx', [])) or 1
    if lod_count != expected_lods:
        raise RuntimeError(f'{name}: imported {lod_count} LODs, expected {expected_lods}')
    physics = mesh.get_editor_property('physics_asset')
    if physics is None:
        physics = unreal.SkeletalMeshEditorSubsystem.create_physics_asset(mesh, True, 0)
    if physics is None:
        raise RuntimeError(f'{name}: missing required Physics Asset')
    save(physics)
    save(mesh)
    meshes[name] = mesh.get_path_name()
    reports.append({'mesh': mesh.get_path_name(), 'skeleton': original_skeleton.get_path_name(),
                    'expected_size_cm': expected_size, 'bone_count': len(actual['bones']),
                    'expected_lods': expected_lods, 'bind_pose_differences': differences})
    unreal.log(f'DINK CHARACTER IMPORT: {name}, {len(actual["bones"])} matching bones, {lod_count} LODs')

runtime = {'schema': 'dink-characters/1', 'assets': reports, 'placements': []}
for row in SPEC.get('placements', [{'origin': 'S001_P26', 'mesh': 'SK_Mother'}] if 'SK_Mother' in meshes else []):
    runtime['placements'].append({'origin': row['origin'], 'mesh': meshes[row['mesh']],
        'locomotion': '/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run.BS_Idle_Walk_Run',
        'offset_cm': row.get('offset_cm', [0, 0, 0]), 'rotation_deg': row.get('rotation_deg', [0, -90, 0]),
        'scale': row.get('scale', [.9, .9, .9]), 'capsule_radius_cm': row.get('capsule_radius_cm', 25),
        'capsule_halfheight_cm': row.get('capsule_halfheight_cm', 82)})
runtime['script_profiles'] = {}
for script, profile in SPEC.get('script_profiles', {}).items():
    runtime['script_profiles'][script.lower()] = {'mesh': meshes[profile['mesh']],
        'locomotion': '/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run.BS_Idle_Walk_Run',
        'offset_cm': profile.get('offset_cm',[0,0,-60]), 'rotation_deg': profile.get('rotation_deg',[0,-90,0]),
        'scale': profile.get('scale',[1,1,1]), 'capsule_radius_cm': profile.get('capsule_radius_cm',28),
        'capsule_halfheight_cm': profile.get('capsule_halfheight_cm',92)}
if 'player' in SPEC:
    runtime['player'] = {'mesh': meshes[SPEC['player']['mesh']]}
if PREVIOUS_RUNTIME:
    combined = {**PREVIOUS_RUNTIME, **runtime}
    for field, key in [('assets','mesh'),('placements','origin')]:
        indexed = {entry[key]:entry for entry in PREVIOUS_RUNTIME.get(field,[])}
        indexed.update({entry[key]:entry for entry in runtime.get(field,[])})
        combined[field] = list(indexed.values())
    combined['script_profiles'] = {**PREVIOUS_RUNTIME.get('script_profiles',{}),**runtime.get('script_profiles',{})}
    runtime = combined
target = ROOT / 'Content/Dink/Data/Art/characters.json'
temporary = target.with_suffix('.tmp')
temporary.write_text(json.dumps(runtime, indent=2)+'\n')
os.replace(temporary, target)
report = ROOT / ('Saved/Art/character'+os.environ.get('DINK_CHARACTER_LOG_SUFFIX','')+'_import_report.json')
report.write_text(json.dumps({'assets': reports, 'runtime': str(target)}, indent=2)+'\n')
unreal.log(f'DINK CHARACTER IMPORT OK: {len(meshes)} skeletal models, {len(materials)} materials, exact shared bind pose')
