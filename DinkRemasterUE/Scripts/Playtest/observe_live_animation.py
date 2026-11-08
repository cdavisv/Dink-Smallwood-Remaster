"""Executed by Unreal's Python console. Read-only pose sampling; only motion fixture travels Dink."""
import unreal,time,json
from pathlib import Path
_root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
_out=_root/'Saved/Playtest/verified-live';_out.mkdir(parents=True,exist_ok=True)
_kind=globals().get('QA_CAPTURE_KIND','fist')
assert _kind in ['fist','motion','camera']
_world=None
for _w in unreal.ObjectIterator(unreal.World):
 try:
  if unreal.GameplayStatics.get_player_pawn(_w,0):_world=_w;break
 except Exception:pass
assert _world is not None,'No player world'
_pawn=unreal.GameplayStatics.get_player_pawn(_world,0)
def _v(p):return [float(p.x),float(p.y),float(p.z)]
if _kind=='camera':
 manager=unreal.GameplayStatics.get_player_camera_manager(_world,0);point=manager.get_camera_location();volumes=[]
 for comp in unreal.ObjectIterator(unreal.PostProcessComponent):
  owner=comp.get_owner()
  if owner is None or not owner.get_path_name().startswith(_world.get_path_name()+':'):continue
  row={'component':comp.get_path_name()};settings=comp.get_editor_property('settings');row['bias']=settings.get_editor_property('auto_exposure_bias');row['overrides_bias']=settings.get_editor_property('override_auto_exposure_bias')
  box=owner.get_editor_property('root_component')
  if isinstance(box,unreal.BoxComponent):
   center=owner.get_actor_location();extent=box.get_scaled_box_extent();row.update(center=_v(center),extent=_v(extent),contains_camera=all(abs(getattr(point,k)-getattr(center,k))<=getattr(extent,k) for k in ['x','y','z']))
  volumes.append(row)
 (_out/'camera.json').write_text(json.dumps({'camera_cm':_v(point),'fov':manager.get_fov_angle(),'pawn_cm':_v(_pawn.get_actor_location()),'post_process_components':volumes},indent=2)+'\n');unreal.log('QA_CAMERA_READBACK_DONE')
else:
 _actors=[]
 if _kind=='fist':_actors=[(_pawn,_pawn.get_component_by_class(unreal.SkeletalMeshComponent),'Dink')]
 else:
  for actor in unreal.GameplayStatics.get_all_actors_of_class(_world,unreal.Actor):
   origin=actor.get_component_by_class(unreal.DinkOriginComponent)
   if not origin:continue
   oid=origin.get_editor_property('origin_id');screen=oid.get_editor_property('screen');index=oid.get_editor_property('placement')
   if screen==438 and index in [3,4,7]:
    comp=actor.get_component_by_class(unreal.DinkCreatureComponent)
    if comp:_actors.append((actor,comp,f'S438_P{index:02d}'))
  unreal.SystemLibrary.execute_console_command(_world,'dink.Inventory')
  unreal.SystemLibrary.execute_console_command(_world,'dink.Goto 438 550 50')
 assert _actors and all(c is not None for a,c,n in _actors)
 _ctx={'start':time.perf_counter()+(.3 if _kind=='motion' else 0),'rows':[],'handle':None,'nextlog':0}
 def _tick(slate_dt):
  elapsed=time.perf_counter()-_ctx['start']
  if elapsed<0:return
  try:
   if elapsed>=(3 if _kind=='motion' else 2):
    unreal.unregister_slate_post_tick_callback(_ctx['handle'])
    if _kind=='motion':
     unreal.SystemLibrary.execute_console_command(_world,'dink.Goto 439 450 350');unreal.SystemLibrary.execute_console_command(_world,'dink.Inventory')
    (_out/(_kind+'.json')).write_text(json.dumps({'kind':_kind,'duration_s':elapsed,'fixture':'Original animation/AI observation. Fist uses real F; motion only travels Dink for setup and automatic end parking, no creature/AI/fact setters.','rows':_ctx['rows']},indent=2)+'\n');unreal.log('QA_ANIMATION_OBSERVER_DONE '+_kind);return
   row={'elapsed_s':elapsed,'world_dt_s':unreal.GameplayStatics.get_world_delta_seconds(_world),'actors':{}}
   for actor,mesh,name in _actors:
    mode=mesh.get_animation_mode();single=mode==unreal.AnimationMode.ANIMATION_SINGLE_NODE;instance=mesh.get_anim_instance()
    r={'world_cm':_v(actor.get_actor_location()),'mode':str(mode),'anim_class':instance.get_class().get_path_name() if instance else None,'position':mesh.get_position() if single else None,'play_rate':mesh.get_play_rate() if single else None,'bones':{}}
    for bone in (['hand_r','middle_03_r','hand_l'] if _kind=='fist' else ['head','leg_01_lower_l','leg_01_lower_r']):r['bones'][bone]=_v(mesh.get_socket_transform(bone,unreal.RelativeTransformSpace.RTS_COMPONENT).translation)
    row['actors'][name]=r
   _ctx['rows'].append(row)
   if _kind=='motion' and elapsed>=_ctx['nextlog']:
    unreal.SystemLibrary.execute_console_command(_world,'dink.Creatures');_ctx['nextlog']=elapsed+.073
  except Exception as e:
   unreal.unregister_slate_post_tick_callback(_ctx['handle'])
   if _kind=='motion':
    try:unreal.SystemLibrary.execute_console_command(_world,'dink.Goto 439 450 350')
    except Exception:pass
   (_out/(_kind+'.json')).write_text(json.dumps({'error':str(e),'rows':_ctx['rows']},indent=2)+'\n');unreal.log_error('QA_ANIMATION_OBSERVER_ERROR '+str(e))
 _ctx['handle']=unreal.register_slate_post_tick_callback(_tick);unreal.log('QA_ANIMATION_OBSERVER_REGISTERED '+_kind)
