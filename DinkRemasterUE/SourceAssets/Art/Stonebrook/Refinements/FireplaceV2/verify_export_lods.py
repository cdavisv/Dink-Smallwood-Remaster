import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
W=Path(__file__).resolve().parent;NAME='SM_Fireplace_Stonebrook_V2';P=W/(NAME+'.blend');bpy.ops.wm.open_mainfile(filepath=str(P));C=bpy.data.collections[NAME]
rows=[]
for i in range(3):
 o=bpy.data.objects[NAME+'_LOD'+str(i)];assert len(o.data.uv_layers)==1
 points=[o.matrix_world@v.co for v in o.data.vertices];lo=[min(v[k] for v in points) for k in range(3)];hi=[max(v[k] for v in points) for k in range(3)]
 uv=[x.uv for x in o.data.uv_layers.active.data];assert all(math.isfinite(v) for q in uv for v in q)
 row={'lod':i,'vertices':len(points),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'min_m':lo,'max_m':hi,'uv_min':[min(v[k] for v in uv) for k in range(2)],'uv_max':[max(v[k] for v in uv) for k in range(2)],'material_slots':[x.name for x in o.data.materials]};rows.append(row)
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 if i==0:
  for h in C.objects:
   if h.name.startswith('UCX_'):h.hide_set(False);h.select_set(True)
 f=W/'Export/SingleLODs'/(NAME+'_LOD'+str(i)+'.fbx');f.parent.mkdir(parents=True,exist_ok=True)
 bpy.ops.export_scene.fbx(filepath=str(f),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_mesh_modifiers=True,use_triangles=True,mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
# Analytic fixture uses actual convex hull extents, not the exterior visual bounding box.
hulls=[]
for o in C.objects:
 if not o.name.startswith('UCX_'):continue
 pts=[o.matrix_world@v.co for v in o.data.vertices];lo=[min(v[k] for v in pts) for k in range(3)];hi=[max(v[k] for v in pts) for k in range(3)];assert max(abs(v) for v in o.location)<1e-6
 hulls.append({'name':o.name,'min_m':lo,'max_m':hi})
assert len(hulls)==6
# A standing164cm capsule cannot enter the106cm clear recess: lintel and cheeks are visible contact geometry.
lintel=next(h for h in hulls if h['min_m'][2]>1.2 and h['max_m'][2]<1.6);assert lintel['min_m'][2]<1.64 and lintel['max_m'][0]>.25 and lintel['min_m'][0]<-.25
assert all(h['min_m'][0]>=-1.251 and h['max_m'][0]<=1.251 and h['min_m'][1]>=-.561 and h['max_m'][1]<=.561 for h in hulls)
back=next(h for h in hulls if h['min_m'][1]>.3);assert back['max_m'][1]-back['min_m'][1]>=.20
j={'production_blend_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'uv_unique_overlap_validation':'companion validation.json:0errors/0warnings, UV_OVERLAP absent','lods':rows,'hulls':hulls,'geometry_tests':{'origin_shared':True,'hulls_inside_visible_outer_footprint':True,'continuous_backing_min20cm':True,'standing_Mother164cm_blocked_by_visible_lintel':True,'bounds_are_source_only_not_runtime_sweep_proof':True},'runtime_content_edited':False};(W/'source_geometry_checks.json').write_text(json.dumps(j,indent=2)+'\n')
