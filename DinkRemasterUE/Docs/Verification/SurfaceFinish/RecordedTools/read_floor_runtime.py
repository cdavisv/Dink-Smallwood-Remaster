import unreal,json
from pathlib import Path
qa_fs_world=next(w for w in unreal.ObjectIterator(unreal.World) if unreal.GameplayStatics.get_player_pawn(w,0))
def qa_fs_read(label):
 rows=[]
 for a in unreal.GameplayStatics.get_all_actors_of_class(qa_fs_world,unreal.Actor):
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   m=c.static_mesh
   if m and m.get_name()=='SM_Floor_Oak_2m_01':
    rows.append({'actor':a.get_name(),'component':c.get_name(),'mesh':m.get_path_name(),'materials':[c.get_material(i).get_path_name() for i in range(c.get_num_materials())],'transform':str(c.get_world_transform()),'collision':str(c.get_collision_enabled()),'profile':str(c.get_collision_profile_name())})
 assert len(rows)==56,len(rows)
 out=Path(Path.home()/'Work/DinkQA/SurfaceNative')/QA_FLOOR_PHASE
 (out/(label+'-floor.json')).write_text(json.dumps(rows,indent=2)+'\n')
 unreal.log('QA_FLOOR_READ '+label)
unreal.log('QA_FLOOR_READER_READY')
def qa_fu_read(label,expected_visible):
 matches=[]
 for a in unreal.GameplayStatics.get_all_actors_of_class(qa_fs_world,unreal.Actor):
  for c in a.get_components_by_class(unreal.StaticMeshComponent):
   if c.static_mesh and c.static_mesh.get_name()=='SM_Underfloor_Stonebrook_V1':matches.append((a,c))
 assert len(matches)==1,len(matches)
 a,c=matches[0]
 r={'actor':a.get_path_name(),'class':a.get_class().get_name(),'actor_hidden':a.get_editor_property('hidden'),'component_visible':c.is_visible(),'mesh':c.static_mesh.get_path_name(),'material':c.get_material(0).get_path_name(),'collision':str(c.get_collision_enabled()),'profile':str(c.get_collision_profile_name()),'overlap':c.get_editor_property('bGenerateOverlapEvents'),'navigation':c.get_editor_property('bCanEverAffectNavigation'),'mesh_navigation':c.static_mesh.get_editor_property('bHasNavigationData'),'hidden_shadow':c.get_editor_property('bCastHiddenShadow'),'hidden_GI':c.get_editor_property('bAffectIndirectLightingWhileHidden'),'transform':str(c.get_world_transform()),'expected_visible':expected_visible}
 out=Path(Path.home()/'Work/DinkQA/SurfaceNative')/QA_FLOOR_PHASE
 (out/(label+'-underfloor.json')).write_text(json.dumps(r,indent=2)+'\n')
 assert r['class']=='DinkArtContextActor' and r['actor_hidden']==(not expected_visible),r
 assert c.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION and r['profile']=='NoCollision',r
 assert not any(r[k] for k in ['overlap','navigation','mesh_navigation','hidden_shadow','hidden_GI']),r
 if expected_visible:assert r['component_visible'],r
 unreal.log('QA_UNDERFLOOR_PASS '+label)
