"""Import isolated cosmetic hero actions onto verified existing SK_Dink.skeleton.
No gameplay damage/notifies, mesh/material rebuild or shared skeleton save.
"""
import json,math,os,hashlib
from pathlib import Path
import unreal
ROOT=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
SOURCE=ROOT/'SourceAssets/Art/Characters/Animations/Unarmed'
SPEC=json.loads((SOURCE/'animation_manifest.json').read_text())
if SPEC.get('schema')!='dink-character-animation/1':raise RuntimeError('Unsupported hero animation manifest')
LIB=unreal.EditorAssetLibrary;TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
reference=unreal.load_asset('/Game/Dink/Hero/SK_Dink.SK_Dink')
if not isinstance(reference,unreal.SkeletalMesh):raise RuntimeError('Verified original SK_Dink required')
skeleton=reference.get_editor_property('skeleton')
if not isinstance(skeleton,unreal.Skeleton):raise RuntimeError('SK_Dink.skeleton is not a real Skeleton asset')
rig_before=json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(reference))
if len(rig_before.get('bones',[]))!=89:raise RuntimeError('Hero reference must have exact89bones')
skeleton_path=skeleton.get_path_name()
def full_skeleton_snapshot():
 pose=unreal.AnimPoseExtensions.get_reference_pose(skeleton)
 names=unreal.AnimPoseExtensions.get_bone_names(pose)
 rows=[]
 for name in names:
  t=unreal.AnimPoseExtensions.get_ref_bone_pose(pose,name,unreal.AnimPoseSpaces.LOCAL)
  rows.append({'name':str(name),'translation':[t.translation.x,t.translation.y,t.translation.z],
               'rotation':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
               'scale':[t.scale3d.x,t.scale3d.y,t.scale3d.z]})
 return rows
full_before=full_skeleton_snapshot()
source_validation=json.loads((SOURCE/'fist_validation.json').read_text())
source_bone_names=set(source_validation['rest_bones'])
mesh_bone_names={bone['name'] for bone in rig_before['bones']}
if len(source_bone_names)!=89 or source_bone_names!=mesh_bone_names:
 raise RuntimeError('Source89-bone inventory does not match verified hero mesh')

# The real asset type/path comes from the verified mesh, never an assumed SK_ prefix.
skeleton_file=ROOT/'Content'/(skeleton_path.removeprefix('/Game/').split('.')[0]+'.uasset')
if not skeleton_file.is_file():raise RuntimeError('Cannot locate existing shared Skeleton package')
skeleton_hash=hashlib.sha256(skeleton_file.read_bytes()).hexdigest()
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
reports=[];actions=[]
for key,spec in SPEC['animations'].items():
 if key!='Fist' or spec.get('source_sequences')!=[102,104,106,108]:raise RuntimeError('Unreviewed hero action contract')
 if spec.get('fps')!=40 or spec.get('frames')!=[1,17] or abs(spec.get('duration_s',0)-.4)>1e-6 or abs(spec.get('impact_s',0)-.175)>1e-6 or spec.get('loop'):
  raise RuntimeError('Original fist timing must remain400ms/impact175ms,40fps17frames')
 source=(SOURCE/spec['fbx']).resolve()
 if SOURCE.resolve() not in source.parents or not source.is_file():raise RuntimeError('Invalid local hero FBX')
 destination=spec.get('content_folder','/Game/Dink/Hero/Animations');name=spec.get('asset_name','AN_Dink_Fist')
 if destination!='/Game/Dink/Hero/Animations' or name!='AN_Dink_Fist':raise RuntimeError('Hero action destination must be isolated reviewed asset')
 options=unreal.FbxImportUI()
 for n,v in {'automated_import_should_detect_type':False,'mesh_type_to_import':unreal.FBXImportType.FBXIT_ANIMATION,'import_as_skeletal':True,'import_mesh':False,'import_materials':False,'import_textures':False,'import_animations':True,'create_physics_asset':False,'skeleton':skeleton}.items():options.set_editor_property(n,v)
 settings={'convert_scene':True,'convert_scene_unit':True,'import_uniform_scale':1.,'import_bone_tracks':True,'use_default_sample_rate':False,'custom_sample_rate':40,'animation_length':unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME}
 for n,v in settings.items():options.anim_sequence_import_data.set_editor_property(n,v)
 target=destination+'/'+name
 if LIB.does_asset_exist(target):
  old=LIB.load_asset(target).get_editor_property('asset_import_data')
  for n,v in settings.items():old.set_editor_property(n,v)
  old.scripted_add_filename(str(source),0,'')
 task=unreal.AssetImportTask();task.filename=str(source);task.destination_path=destination;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;task.options=options;task.factory=unreal.FbxFactory();TOOLS.import_asset_tasks([task])
 animation=LIB.load_asset(target)
 if not isinstance(animation,unreal.AnimSequence):raise RuntimeError('Hero action FBX did not produce AnimSequence')
 info=json.loads(unreal.DinkCharacterArtLibrary.inspect_creature_animation(animation))
 # Native bone_count describes the shared USkeleton (161 here), not source tracks.
 model=animation.get_editor_property('data_model_interface')
 if model is None:raise RuntimeError('Imported hero animation lacks source data model')
 tracks=[str(name) for name in model.get_bone_track_names()]
 if model.get_num_bone_tracks()!=89 or len(tracks)!=89 or len(set(tracks))!=89 or set(tracks)!=source_bone_names:
  raise RuntimeError('Imported animation tracks must exactly match all89 source/reference mesh bones')
 full_after=full_skeleton_snapshot()
 if full_before!=full_after:raise RuntimeError('Shared Skeleton inventory/reference poses changed')
 if info.get('skeleton')!=skeleton_path or info.get('bone_count')!=len(full_before) or not info.get('finite_poses'):raise RuntimeError('Hero shared-skeleton/finite pose gate failed')
 if abs(info.get('duration_s',0)-.4)>.002 or info['root_motion_cm']>.1 or info['max_scale_error']>.001 or info['max_pose_rotation_rad']<.1:raise RuntimeError('Hero action duration/root/scale/motion gate failed')
 if info['loop_seam_rotation_rad']>.002 or info['loop_seam_translation_cm']>.02:raise RuntimeError('Hero idle-matched endpoints changed')
 rig_after=json.loads(unreal.DinkCharacterArtLibrary.inspect_rig(reference))
 if rig_after['bones']!=rig_before['bones'] or hashlib.sha256(skeleton_file.read_bytes()).hexdigest()!=skeleton_hash:raise RuntimeError('Existing shared skeleton modified during action import')
 if not LIB.save_loaded_asset(animation,only_if_is_dirty=False):raise RuntimeError('Cannot save isolated hero animation')
 if hashlib.sha256(skeleton_file.read_bytes()).hexdigest()!=skeleton_hash or full_skeleton_snapshot()!=full_before:raise RuntimeError('Shared Skeleton package/reference changed during animation save')
 reports.append({'action':key,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_mesh':reference.get_path_name(),'resolved_skeleton':skeleton_path,'animation_track_names':tracks,'animation_track_count':len(tracks),'reference_mesh_bone_names':sorted(mesh_bone_names),'source_bone_names':sorted(source_bone_names),'shared_skeleton_reference_before':full_before,'shared_skeleton_reference_after':full_after,'full_reference_unchanged':full_before==full_after,'skeleton_package_sha256_before':skeleton_hash,'skeleton_package_sha256_after':skeleton_hash,'native':info})
 actions.append({'sequences':[102,104,106,108],'animation':animation.get_path_name(),'duration_s':.4,'impact_s':.175,'loop':False})
# Publish only after every imported clip and immutable-skeleton gate succeeds.
runtime={'schema':'dink-hero-actions/1','skeleton':skeleton_path,'actions':actions,'gameplay_authority':'Original sp_seq/pending-hit timing; animation is cosmetic only'}
target=ROOT/'Content/Dink/Data/Art/hero_actions.json';target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(runtime,indent=2)+'\n');os.replace(temporary,target)
report=ROOT/'Saved/Art/hero_animation_import_report.json';report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps({'passed':True,'animations':reports,'runtime':str(target.relative_to(ROOT))},indent=2)+'\n')
unreal.log('DINK HERO ANIMATION IMPORT OK:1clip,89tracks,400ms/impact175ms,sharedSkeletonunchanged')
