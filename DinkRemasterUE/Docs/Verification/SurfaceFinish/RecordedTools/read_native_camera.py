"""Game-safe readback of the native interior camera and managed surface alpha."""
import unreal,json
from pathlib import Path
qa_nc_world=next(w for w in unreal.ObjectIterator(unreal.World) if unreal.GameplayStatics.get_player_pawn(w,0))
qa_nc_pawn=unreal.GameplayStatics.get_player_pawn(qa_nc_world,0)
qa_nc_comp=qa_nc_pawn.get_component_by_class(unreal.DinkInteriorCameraComponent)
qa_nc_cam=unreal.GameplayStatics.get_player_camera_manager(qa_nc_world,0)
qa_nc_arm=qa_nc_pawn.get_component_by_class(unreal.SpringArmComponent)
def qa_nc_vec(v):return [float(v.x),float(v.y),float(v.z)]
def qa_nc_read(label):
 r={'pawn_cm':qa_nc_vec(qa_nc_pawn.get_actor_location()),'camera_cm':qa_nc_vec(qa_nc_cam.get_camera_location()),'camera_rotation':str(qa_nc_cam.get_camera_rotation()),'control_rotation':str(unreal.GameplayStatics.get_player_controller(qa_nc_world,0).get_control_rotation()),'field_of_view':qa_nc_cam.get_fov_angle(),'arm_cm':qa_nc_arm.get_editor_property('target_arm_length'),'target_offset':qa_nc_vec(qa_nc_arm.get_editor_property('target_offset')),'socket_offset':qa_nc_vec(qa_nc_arm.get_editor_property('socket_offset')),'interior_mode':qa_nc_comp.get_editor_property('interior_mode'),'managed_occluders':qa_nc_comp.get_editor_property('managed_occluder_count'),'fading_occluders':qa_nc_comp.get_editor_property('fading_occluder_count'),'floor_framing_shift':qa_nc_vec(qa_nc_comp.get_editor_property('floor_framing_shift')),'floor_framing_available':qa_nc_comp.get_editor_property('floor_framing_available'),'floor_framing_feasible':qa_nc_comp.get_editor_property('floor_framing_feasible'),'fading_materials':[]}
 for mat in unreal.ObjectIterator(unreal.MaterialInstanceDynamic):
  if mat.get_outer()!=qa_nc_comp:continue
  a=mat.get_scalar_parameter_value('DinkCameraOpacity')
  if a<.999:r['fading_materials'].append({'material':mat.get_path_name(),'opacity':a})
 out=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))/('Saved/Playtest/'+globals().get('QA_NATIVE_CAMERA_OUTPUT','NativeCameraV1'));out.mkdir(exist_ok=True)
 (out/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n');unreal.log('QA_NATIVE_CAMERA_READ '+label)
unreal.log('QA_NATIVE_CAMERA_READER_READY')
