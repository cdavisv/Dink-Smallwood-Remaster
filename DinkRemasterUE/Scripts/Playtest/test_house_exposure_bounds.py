"""Temporary exposure-volume containment comparison; restores exact original bounds."""
import unreal,json,time
from pathlib import Path
root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()));out=root/'Saved/Playtest/verified-live';out.mkdir(parents=True,exist_ok=True)
world=None
for candidate in unreal.ObjectIterator(unreal.World):
 try:
  if unreal.GameplayStatics.get_player_pawn(candidate,0):world=candidate;break
 except Exception:pass
manager=unreal.GameplayStatics.get_player_camera_manager(world,0);point=manager.get_camera_location();box=None
for component in unreal.ObjectIterator(unreal.PostProcessComponent):
 owner=component.get_owner()
 if owner and owner.get_path_name().startswith(world.get_path_name()+':') and component.get_name()=='ArtExposure':box=owner.get_editor_property('root_component');break
assert isinstance(box,unreal.BoxComponent)
original=box.get_unscaled_box_extent();center=box.get_owner().get_actor_location();candidate=unreal.Vector(1220,1130,650)
def vector(v):return [float(v.x),float(v.y),float(v.z)]
assert not all(abs(getattr(point,k)-getattr(center,k))<=getattr(original,k) for k in ['x','y','z']),'Expected measured outside-camera baseline'
box.set_box_extent(candidate,False)
assert all(abs(getattr(point,k)-getattr(center,k))<=getattr(candidate,k) for k in ['x','y','z'])
(out/'house-exposure-candidate.json').write_text(json.dumps({'fixture':'Temporary PP box bounds only; no blocking/overlap settings changed','component':box.get_path_name(),'original_extent':vector(original),'candidate_extent':vector(candidate),'camera_cm':vector(point),'center_cm':vector(center),'restoration_required':True},indent=2)+'\n')
unreal.log('QA_HOUSE_EXPOSURE_CANDIDATE_SET')
