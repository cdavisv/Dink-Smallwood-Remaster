"""Import own-rig Blender creatures and verify real animation/LOD assets.
Run with import_creature_art.sh. Never assigns the mannequin skeleton.
"""
import json
import math
import os
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
import sys
sys.path.insert(0, str(ROOT / 'Scripts'))
from creature_art_manifest import BUDGETS, asset_origins, load_source, merge_runtime

SOURCE, SPEC = load_source(ROOT / 'SourceAssets/Art/Creatures',
                           os.environ.get('DINK_CREATURE_MANIFEST', 'Pig/pig_manifest.json'))
DEST = '/Game/Dink/Creatures/' + SOURCE.name
RUNTIME_TARGET = ROOT / 'Content/Dink/Data/Art/creatures.json'
PREVIOUS_RUNTIME = (json.loads(RUNTIME_TARGET.read_text()) if RUNTIME_TARGET.exists()
                    else {'schema':'dink-creatures/1','assets':[],'placements':[]})
# Detect accidental actor reassignment before any imported assets are changed.
planned_assets = []
planned_placements = []
for name, asset in SPEC['assets'].items():
    destination = asset.get('content_folder', DEST)
    if not destination.startswith('/Game/Dink/Creatures/'):
        raise RuntimeError('Creature destination must be inside /Game/Dink/Creatures')
    mesh_path = destination + '/' + name + '.' + name
    planned_assets.append({'mesh':mesh_path})
    planned_placements += [{'origin':origin,'mesh':mesh_path} for origin in asset_origins(SPEC, asset)]
merge_runtime(PREVIOUS_RUNTIME, {'schema':'dink-creatures/1','assets':planned_assets,
                                'placements':planned_placements})
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDIT = unreal.MaterialEditingLibrary
MATS = '/Game/Dink/Materials/Creatures'
TEXTURES = '/Game/Dink/Textures/Creatures'
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


if SPEC.get('schema') != 'dink-creature-art/1':
    raise RuntimeError('Unsupported creature source manifest')
reports = []
runtime = {'schema': 'dink-creatures/1', 'assets': [], 'placements': []}
for name, row in SPEC['assets'].items():
    destination = row.get('content_folder', DEST)
    if not destination.startswith('/Game/Dink/Creatures/'):
        raise RuntimeError('Creature assets must remain in /Game/Dink/Creatures/')
    target = destination + '/' + name
    previous = LIB.load_asset(target) if LIB.does_asset_exist(target) else None
    old_rig = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(previous)) if previous else None
    options = unreal.FbxImportUI()
    for key, value in {'automated_import_should_detect_type': False,
                       'mesh_type_to_import': unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                       'import_as_skeletal': True, 'import_mesh': True, 'import_materials': False,
                       'import_textures': False, 'import_animations': False, 'create_physics_asset': True}.items():
        options.set_editor_property(key, value)
    options.skeleton = previous.skeleton if previous else None
    settings = {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1.,
                'update_skeleton_reference_pose': False, 'use_t0_as_ref_pose': False,
                'import_mesh_lods': False, 'import_meshes_in_bone_hierarchy': True,
                'normal_import_method': unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}
    for key, value in settings.items():
        options.skeletal_mesh_import_data.set_editor_property(key, value)
    if previous:
        data = previous.get_editor_property('asset_import_data')
        for key, value in settings.items(): data.set_editor_property(key, value)
        data.scripted_add_filename(str((SOURCE / row['fbx']).resolve()), 0, '')
    mesh = import_asset(row['fbx'], destination, name, options, unreal.FbxFactory())
    rig = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(mesh))
    expected = [v * 100 for v in row['dimensions_m']]
    if any(abs(a-b) > 1. for a,b in zip(rig['bounds_size_cm'], expected)):
        raise RuntimeError(f'{name}: source/import centimetre dimensions differ')
    bone_names = [b['name'] for b in rig['bones']]
    if set(bone_names) != set(row['bones']) or len(bone_names) != len(row['bones']):
        raise RuntimeError(f'{name}: imported bone inventory differs')
    roots = [b for b in rig['bones'] if b['parent'] < 0]
    if len(roots) != 1 or roots[0]['name'] != row.get('root_bone', 'root'):
        raise RuntimeError(f'{name}: expected one explicit root')
    if any(math.dist(b['scale'], [1,1,1]) > .001 for b in rig['bones']):
        raise RuntimeError(f'{name}: non-unit reference bone scale')
    if old_rig:
        old = {b['name']: b for b in old_rig['bones']}
        for b in rig['bones']:
            prior = old.get(b['name'])
            if not prior or prior['parent'] != b['parent'] or math.dist(prior['translation_cm'],b['translation_cm']) > .1 or abs(sum(a*c for a,c in zip(prior['rotation_xyzw'],b['rotation_xyzw']))) < .999999:
                raise RuntimeError(f'{name}: reimport changed its existing animation bind pose')
    lods = row['lod_fbx']
    if len(lods) != 3: raise RuntimeError('Creatures require three source LODs')
    for index, filename in enumerate(lods[1:], 1):
        if unreal.SkeletalMeshEditorSubsystem.import_lod(mesh,index,str((SOURCE/filename).resolve())) != index:
            raise RuntimeError(f'{name}: LOD{index} failed')
    if unreal.SkeletalMeshEditorSubsystem.get_lod_count(mesh) != 3:
        raise RuntimeError(f'{name}: missing actual LOD chain')
    slots = list(mesh.materials)
    creature_class = row.get('class', 'creature_quadruped')
    material_budget = BUDGETS[creature_class][1]
    if len(slots) > material_budget: raise RuntimeError('Creature exceeds class material budget')
    for slot in slots:
        key = str(slot.material_slot_name).split('.')[0]
        if key not in materials: raise RuntimeError('Unknown creature material '+key)
        slot.material_interface = materials[key]
    mesh.materials = slots
    skeleton = mesh.skeleton
    if skeleton.get_path_name().startswith('/Game/Characters/Mannequins/'):
        raise RuntimeError('Creature must use its own anatomical rig')
    save(skeleton)
    physics = mesh.physics_asset or unreal.SkeletalMeshEditorSubsystem.create_physics_asset(mesh, True, 0)
    if not physics: raise RuntimeError('Missing required creature Physics Asset')
    save(physics); save(mesh)
    animations = {}; animation_reports = {}
    for action, spec in SPEC['animations'].items():
        anim_options = unreal.FbxImportUI()
        for key, value in {'automated_import_should_detect_type': False,
                           'mesh_type_to_import': unreal.FBXImportType.FBXIT_ANIMATION,
                           'import_as_skeletal': True, 'import_mesh': False,
                           'import_materials': False, 'import_textures': False,
                           'import_animations': True, 'create_physics_asset': False,
                           'skeleton': skeleton}.items(): anim_options.set_editor_property(key,value)
        anim_settings = {'convert_scene': True, 'convert_scene_unit': True,
                           'import_uniform_scale': 1., 'import_bone_tracks': True,
                           'use_default_sample_rate': False,
                           'custom_sample_rate': int(spec.get('fps',30)),
                           'animation_length': unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME}
        for key, value in anim_settings.items():
            anim_options.anim_sequence_import_data.set_editor_property(key,value)
        anim_name = 'AN_'+name.removeprefix('SK_')+'_'+action
        anim_path = destination+'/Animations/'+anim_name
        if LIB.does_asset_exist(anim_path):
            old_data = LIB.load_asset(anim_path).get_editor_property('asset_import_data')
            for key, value in anim_settings.items(): old_data.set_editor_property(key,value)
            old_data.scripted_add_filename(str((SOURCE / spec['fbx']).resolve()),0,'')
        animation = import_asset(spec['fbx'], destination+'/Animations', anim_name, anim_options, unreal.FbxFactory())
        inspection = json.loads(unreal.DinkCharacterArtLibrary.inspect_creature_animation(animation))
        if inspection.get('skeleton') != skeleton.get_path_name() or inspection.get('duration_s',0) <= 0 or not inspection.get('finite_poses'):
            raise RuntimeError(f'{action}: invalid imported animation')
        if inspection['root_motion_cm'] > .1 or inspection['max_scale_error'] > .001:
            raise RuntimeError(f'{action}: root motion or bone scaling in in-place animation')
        if spec.get('loop') and (inspection['loop_seam_rotation_rad'] > .05 or inspection['loop_seam_translation_cm'] > .2):
            raise RuntimeError(f'{action}: animation loop seam does not close')
        minimum_motion = float(spec.get('minimum_pose_rotation_rad', .1 if action in ['Walk','Run','Feed'] else 0.))
        if inspection['max_pose_rotation_rad'] < minimum_motion:
            raise RuntimeError(f'{action}: animation does not meet its motion contract')
        if 'duration_s' in spec and abs(inspection['duration_s']-float(spec['duration_s'])) > .002:
            raise RuntimeError(f'{action}: imported duration differs from source')
        save(animation); animations[action] = animation; animation_reports[action] = inspection
    if not all(k in animations for k in ['Idle','Walk']):
        raise RuntimeError('Creature requires Idle/Walk actions')
    blend_name = 'BS_'+name.removeprefix('SK_')+'_Locomotion'
    blend_path = destination+'/'+blend_name
    if LIB.does_asset_exist(blend_path): blend = LIB.load_asset(blend_path)
    else:
        factory = unreal.BlendSpaceFactory1D(); factory.target_skeleton = skeleton; factory.preview_skeletal_mesh = mesh
        blend = TOOLS.create_asset(blend_name, destination, unreal.BlendSpace1D, factory)
    walk_speed = float(SPEC['animations']['Walk'].get('nominal_speed_cm_s',80))
    run_speed = float(SPEC['animations'].get('Run',{}).get('nominal_speed_cm_s',0))
    if not unreal.DinkCharacterArtLibrary.configure_creature_locomotion(blend, animations['Idle'], animations['Walk'], walk_speed, animations.get('Run'), run_speed):
        raise RuntimeError('Own-rig creature locomotion blend space failed')
    save(blend)
    by_name = {b['name']:b for b in rig['bones']}
    head = by_name[row.get('head_bone','head')]['component_translation_cm']
    pelvis = by_name[row.get('pelvis_bone','pelvis')]['component_translation_cm']
    heading = -math.degrees(math.atan2(head[1]-pelvis[1],head[0]-pelvis[0]))
    boxes = row.get('body_boxes')
    if not boxes: raise RuntimeError('Artist must declare measured actor-local body boxes')
    for box in boxes:
        if len(box['offset_cm'])!=3 or len(box['extent_cm'])!=3 or min(box['extent_cm']) <= 0:
            raise RuntimeError('Invalid measured collision body')
    report = {'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),
              'expected_size_cm':expected,'bone_count':len(bone_names),'expected_lods':3,
              'animation_reports':animation_reports,'animation_loops':{a:bool(v.get('loop')) for a,v in SPEC['animations'].items()},
              'class':creature_class,'material_budget':material_budget,
              'nominal_walk_speed_cm_s':walk_speed,'nominal_run_speed_cm_s':run_speed,'rotation_deg':[0,heading,0],
              'body_boxes':boxes,'locomotion':blend.get_path_name()}
    reports.append(report); runtime['assets'].append(report)
    for origin in asset_origins(SPEC, row):
        runtime['placements'].append({'origin':origin,'mesh':mesh.get_path_name(),'locomotion':blend.get_path_name(),
            'feed_animation':animations['Feed'].get_path_name() if 'Feed' in animations else '','offset_cm':[0,0,0],
            'rotation_deg':[0,heading,0],'scale':[1,1,1],'body_boxes':boxes,
            'food_sequences':SPEC.get('food_sequences',[430,431]) if 'Feed' in animations else [],'food_bone':row.get('head_bone','head'),
            'food_radius_cm':70,'food_forward_dot':.5,'stationary_speed_cm_s':5,
            'nominal_walk_speed_cm_s':walk_speed,'nominal_run_speed_cm_s':run_speed})
# Optional scatter is produced by the separate PigPen environment bridge.
food_mesh = SPEC.get('food_mesh')
if food_mesh:
    if not LIB.does_asset_exist(food_mesh): raise RuntimeError('Import PigPen feed scatter before publishing its reference')
    for placement in runtime['placements']:
        placement.update(food_mesh=food_mesh,food_mesh_offset_cm=SPEC.get('food_mesh_offset_cm',[0,0,-59.4]))
runtime = merge_runtime(PREVIOUS_RUNTIME, runtime)
target = RUNTIME_TARGET
temporary = target.with_suffix('.tmp'); temporary.write_text(json.dumps(runtime,indent=2)+'\n'); os.replace(temporary,target)
report = ROOT/('Saved/Art/creature'+os.environ.get('DINK_CREATURE_LOG_SUFFIX','')+'_import_report.json'); report.parent.mkdir(parents=True,exist_ok=True)
report.write_text(json.dumps({'assets':reports,'runtime':str(target)},indent=2)+'\n')
unreal.log(f'DINK CREATURE IMPORT OK: {len(reports)} own-rig creatures, {len(runtime["placements"])} total original actors')
