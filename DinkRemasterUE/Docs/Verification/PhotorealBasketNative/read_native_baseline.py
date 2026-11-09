import unreal,json,hashlib,os
from pathlib import Path
root=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
rows=[]
for name in ['SM_Basket_Wicker_01','SM_FeedSack_Jute_01']:
 package='/Game/Dink/Kits/Stonebrook/'+name
 path=root/'Content/Dink/Kits/Stonebrook'/(name+'.uasset');before=hashlib.sha256(path.read_bytes()).hexdigest()
 mesh=unreal.load_asset(package);assert isinstance(mesh,unreal.StaticMesh)
 d=mesh.get_static_mesh_description(0);body=mesh.get_editor_property('body_setup');b=mesh.get_bounds()
 rows.append({'name':name,'package_sha256':before,'triangles':d.get_triangle_count(),'vertices':d.get_vertex_count(),'materials':[mesh.get_material(i).get_path_name() for i in range(len(mesh.get_editor_property('static_materials')))],'bounds_cm':[2*b.box_extent.x,2*b.box_extent.y,2*b.box_extent.z],'collision_trace_flag':str(body.get_editor_property('collision_trace_flag')),'aggregate_geometry':body.get_editor_property('agg_geom').export_text()})
 assert hashlib.sha256(path.read_bytes()).hexdigest()==before
(root/'Saved/BasketReviewed/native_baseline.json').write_text(json.dumps({'passed':True,'pid':os.getpid(),'project':str(root),'read_only':True,'rows':rows},indent=2)+'\n')
unreal.log('BASKET_NATIVE_BASELINE_PASS')
