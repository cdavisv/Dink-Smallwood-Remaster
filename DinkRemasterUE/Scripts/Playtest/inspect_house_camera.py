"""Read-only component/bounds diagnosis. Execute in the owned game Python console."""
import unreal,json
from pathlib import Path
world=next((w for w in unreal.ObjectIterator(unreal.World) if unreal.GameplayStatics.get_player_pawn(w,0)),None)
assert world,'No live player world'
pawn=unreal.GameplayStatics.get_player_pawn(world,0)
camera=unreal.GameplayStatics.get_player_camera_manager(world,0)
a=camera.get_camera_location();b=pawn.get_actor_location()
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def prop(c,n):
 try:return str(c.get_editor_property(n))
 except Exception as e:return 'unavailable:'+str(e)
def crosses(lo,hi):
 t0,t1=0.,1.
 for x,y,mn,mx in zip(vec(a),vec(b),lo,hi):
  d=y-x
  if abs(d)<1e-8:
   if x<mn or x>mx:return False
  else:
   p,q=(mn-x)/d,(mx-x)/d
   if p>q:p,q=q,p
   t0=max(t0,p);t1=min(t1,q)
   if t0>t1:return False
 return True
rows=[]
for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
 if not actor.get_class().get_name().startswith('DinkScreenVolume'):continue
 if actor.get_editor_property('screen_number')!=1:continue
 for c in actor.get_components_by_class(unreal.PrimitiveComponent):
  center,extent,radius=unreal.SystemLibrary.get_component_bounds(c)
  lo=[x-y for x,y in zip(vec(center),vec(extent))];hi=[x+y for x,y in zip(vec(center),vec(extent))]
  row={'component':c.get_path_name(),'center':vec(center),'extent':vec(extent),'visible':prop(c,'visible'),'hidden_in_game':prop(c,'hidden_in_game'),'collision':str(c.get_collision_enabled()),'camera_response':str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA)),'camera_to_pawn_intersects_world_bounds':crosses(lo,hi)}
  if isinstance(c,unreal.StaticMeshComponent):
   mesh=c.get_editor_property('static_mesh');row['mesh']=mesh.get_path_name() if mesh else None
   row['materials']=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
  rows.append(row)
root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()));out=root/'Saved/Playtest/verified-live/house-camera-component-diagnostic.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'read_only':True,'camera':vec(a),'pawn':vec(b),'components':rows},indent=2)+'\n')
unreal.log('QA_HOUSE_CAMERA_COMPONENT_DIAGNOSTIC_DONE '+str(out))
