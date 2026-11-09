import unreal,json,os
from pathlib import Path
root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
world=next(w for w in unreal.ObjectIterator(unreal.World)if unreal.GameplayStatics.get_player_pawn(w,0));pawn=unreal.GameplayStatics.get_player_pawn(world,0);cap=pawn.get_component_by_class(unreal.CapsuleComponent)
def qa_basket_trace(label):
 start=pawn.get_actor_location();end=unreal.Vector(start.x+300,start.y,start.z)
 rows=[]
 for complex_trace in [False,True]:
  hit=unreal.SystemLibrary.capsule_trace_single(world,start,end,cap.get_scaled_capsule_radius(),cap.get_scaled_capsule_half_height(),unreal.TraceTypeQuery.ECC_VISIBILITY,complex_trace,[pawn],unreal.DrawDebugTrace.NONE,True)
  props={}
  if hit:
   for key in ['time','distance','location','impact_point','normal','impact_normal','component','hit_object_handle','blocking_hit','start_penetrating']:
    try:props[key]=str(hit.get_editor_property(key))
    except Exception as error:props[key]={'unavailable':str(error)}
  rows.append({'trace_complex':complex_trace,'hit_text':hit.export_text()if hit else None,'properties':props})
 result={'pid':os.getpid(),'start':str(start),'end':str(end),'radius':cap.get_scaled_capsule_radius(),'half_height':cap.get_scaled_capsule_half_height(),'traces':rows}
 (root/'Saved/BasketReviewed/Render'/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n');unreal.log('QA_BASKET_TRACE '+label)
