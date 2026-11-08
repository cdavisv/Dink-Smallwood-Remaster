"""Temporary live camera composition only. Call qa_restore_camera() before ending review."""
import unreal,json
from pathlib import Path
qa_camera_world=next(w for w in unreal.ObjectIterator(unreal.World) if unreal.GameplayStatics.get_player_pawn(w,0))
qa_camera_pawn=unreal.GameplayStatics.get_player_pawn(qa_camera_world,0)
qa_camera_arm=qa_camera_pawn.get_component_by_class(unreal.SpringArmComponent)
assert qa_camera_arm
qa_camera_saved={k:qa_camera_arm.get_editor_property(k) for k in ['target_arm_length','target_offset','use_pawn_control_rotation','relative_rotation']}
qa_camera_offset=qa_camera_saved['target_offset'];qa_camera_saved['target_offset']=unreal.Vector(qa_camera_offset.x,qa_camera_offset.y,qa_camera_offset.z)
qa_camera_rotation=qa_camera_saved['relative_rotation'];qa_camera_saved['relative_rotation']=unreal.Rotator(pitch=qa_camera_rotation.pitch,yaw=qa_camera_rotation.yaw,roll=qa_camera_rotation.roll)
qa_camera_out=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))/'Saved/Playtest/camera-prototype';qa_camera_out.mkdir(parents=True,exist_ok=True)
def qa_camera_vec(v):return [float(v.x),float(v.y),float(v.z)]
def qa_camera_read(label):
 manager=unreal.GameplayStatics.get_player_camera_manager(qa_camera_world,0)
 r={'label':label,'camera_cm':qa_camera_vec(manager.get_camera_location()),'pawn_cm':qa_camera_vec(qa_camera_pawn.get_actor_location()),'rotation':str(manager.get_camera_rotation()),'arm_cm':qa_camera_arm.get_editor_property('target_arm_length'),'target_offset_cm':qa_camera_vec(qa_camera_arm.get_editor_property('target_offset'))}
 (qa_camera_out/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n');unreal.log('QA_CAMERA_PROTOTYPE_READ '+json.dumps(r))
def qa_camera_preset(arm,pitch,pivot_offset):
 yaw=unreal.GameplayStatics.get_player_controller(qa_camera_world,0).get_control_rotation().yaw
 qa_camera_arm.set_editor_property('use_pawn_control_rotation',False)
 qa_camera_arm.set_editor_property('target_arm_length',arm)
 qa_camera_arm.set_editor_property('target_offset',unreal.Vector(0,0,pivot_offset))
 qa_camera_arm.set_world_rotation(unreal.Rotator(pitch=pitch,yaw=yaw,roll=0),False,True)
 unreal.log('QA_CAMERA_PROTOTYPE_SET')
def qa_restore_camera():
 for k,v in qa_camera_saved.items():qa_camera_arm.set_editor_property(k,v)
 unreal.log('QA_CAMERA_PROTOTYPE_RESTORED')
qa_camera_read('baseline');unreal.log('QA_CAMERA_PROTOTYPE_READY')
