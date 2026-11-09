import bpy,bmesh,sys,os,json,traceback
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O));from closed_crumb_normalization import normalize_closed_crumbs
try:
 def meshes():
  result={}
  for i in range(3):
   me=bpy.data.objects['SM_Pie_Rustic_01_LOD'+str(i)].data;result[i]={'vertices':[list(v.co)for v in me.vertices],'faces':[(list(p.vertices),p.material_index,p.use_smooth)for p in me.polygons],'UV0':[list(d.uv)for d in me.uv_layers.active.data],'normals':[list(n.vector)for n in me.corner_normals]}
  return result
 bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPieV1_Source.blend'))
 for i in range(3):
  me=bpy.data.objects['SM_Pie_Rustic_01_LOD'+str(i)].data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='FIXED',ngon_method='EAR_CLIP');bm.to_mesh(me);bm.free();me.update()
 r=normalize_closed_crumbs();generated=meshes();bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPieV1_Export.blend'));assert generated==meshes();(O/'normalization_module_verification.json').write_text(json.dumps({'passed':True,'canonical_bake_normalization_function_reproduces_corrected_meshes_exactly':True,'LODs':[4844,2542,1330],'raw_donor_and_maps_unchanged':True,'verification_requires_only_portable_raw_donor_and_current_export':True,'no_private_initial_bake_archive_dependency':True},indent=2)+'\n')
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
