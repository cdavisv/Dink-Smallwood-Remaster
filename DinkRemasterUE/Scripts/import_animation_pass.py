"""Import the animation pass clips (SourceAssets/Art/Characters/Animations/AnimationPassV1) onto
the verified SK_Dink skeleton and publish Content/Dink/Data/Art/animation_pass.json.

Animation only: no mesh, material or skeleton is saved; the shared skeleton's reference pose and
package hash must be identical before and after. Clips carry no notifies and no root motion:
gameplay keeps every timing (see UDinkPlayerActionComponent, UDinkBodyAnimInstance).
DINK_ANIM_ONLY=name,name limits the import to some clips (the manifest still lists all present).
"""
import json, os, hashlib
from pathlib import Path
import unreal
ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
SOURCE = ROOT / 'SourceAssets/Art/Characters/Animations/AnimationPassV1'
SPEC = json.loads((SOURCE / 'animation_manifest.json').read_text())
if SPEC.get('schema') != 'dink-animation-pass/1':
    raise RuntimeError('Unsupported animation pass manifest')
FOLDER = SPEC['content_folder']
if FOLDER != '/Game/Dink/Hero/Animations/Pass1':
    raise RuntimeError('Animation pass clips must stay in their own folder')
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
reference = unreal.load_asset(SPEC['skeleton_from_mesh'])
if not isinstance(reference, unreal.SkeletalMesh):
    raise RuntimeError('Verified SK_Dink required')
skeleton = reference.get_editor_property('skeleton')
rig = json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(reference))
mesh_bones = {b['name'] for b in rig['bones']}
if len(mesh_bones) != 89:
    raise RuntimeError('Hero reference must have exactly 89 bones')
skeleton_path = skeleton.get_path_name()
skeleton_file = ROOT / 'Content' / (skeleton_path.removeprefix('/Game/').split('.')[0] + '.uasset')


def snapshot():
    pose = unreal.AnimPoseExtensions.get_reference_pose(skeleton)
    rows = []
    for name in unreal.AnimPoseExtensions.get_bone_names(pose):
        t = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, name, unreal.AnimPoseSpaces.LOCAL)
        rows.append((str(name), t.translation.x, t.translation.y, t.translation.z, t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))
    return rows


before = snapshot()
skeleton_hash = hashlib.sha256(skeleton_file.read_bytes()).hexdigest()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
only = [n for n in os.environ.get('DINK_ANIM_ONLY', '').split(',') if n]
runtime = {}
imported = 0
for name, spec in sorted(SPEC['clips'].items()):
    source = (SOURCE / spec['fbx']).resolve()
    if SOURCE.resolve() not in source.parents or not source.is_file():
        raise RuntimeError('Invalid clip FBX for ' + name)
    if hashlib.sha256(source.read_bytes()).hexdigest() != spec['sha256']:
        raise RuntimeError('FBX differs from the manifest: ' + name)
    asset_name = spec['asset_name']
    target = FOLDER + '/' + asset_name
    if not only or name in only or not LIB.does_asset_exist(target):
        options = unreal.FbxImportUI()
        for n, v in {'automated_import_should_detect_type': False, 'mesh_type_to_import': unreal.FBXImportType.FBXIT_ANIMATION,
                     'import_as_skeletal': True, 'import_mesh': False, 'import_materials': False, 'import_textures': False,
                     'import_animations': True, 'create_physics_asset': False, 'skeleton': skeleton}.items():
            options.set_editor_property(n, v)
        settings = {'convert_scene': True, 'convert_scene_unit': True, 'import_uniform_scale': 1., 'import_bone_tracks': True,
                    'use_default_sample_rate': False, 'custom_sample_rate': int(spec['fps']),
                    'animation_length': unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME}
        for n, v in settings.items():
            options.anim_sequence_import_data.set_editor_property(n, v)
        task = unreal.AssetImportTask()
        task.filename = str(source); task.destination_path = FOLDER; task.destination_name = asset_name
        task.automated = True; task.replace_existing = True; task.save = False; task.options = options
        task.factory = unreal.FbxFactory()
        TOOLS.import_asset_tasks([task])
        animation = LIB.load_asset(target)
        if not isinstance(animation, unreal.AnimSequence):
            raise RuntimeError('No AnimSequence from ' + name)
        info = json.loads(unreal.DinkCharacterArtLibrary.inspect_creature_animation(animation))
        model = animation.get_editor_property('data_model_interface')
        tracks = {str(t) for t in model.get_bone_track_names()}
        if tracks != mesh_bones:
            raise RuntimeError('Clip tracks must be the 89 rig bones: ' + name)
        if info.get('skeleton') != skeleton_path or not info.get('finite_poses'):
            raise RuntimeError('Skeleton/finite gate failed: ' + name)
        if abs(info.get('duration_s', 0) - spec['duration_s']) > .003 or info['root_motion_cm'] > .1 or info['max_scale_error'] > .001:
            raise RuntimeError('Duration/root/scale gate failed: %s %s' % (name, info))
        if spec.get('loop') and (info['loop_seam_rotation_rad'] > .004 or info['loop_seam_translation_cm'] > .05):
            raise RuntimeError('Loop seam gate failed: %s %s' % (name, info))
        if snapshot() != before:
            raise RuntimeError('Shared skeleton reference pose changed')
        if not LIB.save_loaded_asset(animation, only_if_is_dirty=False):
            raise RuntimeError('Cannot save ' + target)
        imported += 1
    row = {'asset': target + '.' + asset_name, 'duration_s': spec['duration_s'], 'loop': bool(spec.get('loop')), 'fps': spec['fps']}
    if spec.get('speed_m_s'):
        row['speed_cm_s'] = round(spec['speed_m_s'] * 100, 3)
        row['stride_cm'] = round(spec['stride_m'] * 100, 3)
    for key, value in (spec.get('events') or {}).items():
        row[key] = value
    runtime[name] = row
if hashlib.sha256(skeleton_file.read_bytes()).hexdigest() != skeleton_hash or snapshot() != before:
    raise RuntimeError('Shared skeleton package changed during the import')
out = {'schema': 'dink-animation-pass/1', 'skeleton': skeleton_path, 'folder': FOLDER, 'clips': runtime,
       'gameplay_authority': 'Original sp_seq/pending-hit timing; every clip is cosmetic'}
target = ROOT / 'Content/Dink/Data/Art/animation_pass.json'
temporary = target.with_suffix('.tmp')
temporary.write_text(json.dumps(out, indent=1) + '\n')
os.replace(temporary, target)
unreal.log('DINK ANIMATION PASS IMPORT OK: %d clips imported, %d listed, shared skeleton unchanged' % (imported, len(runtime)))
