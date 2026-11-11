"""Fresh source readback; optional --finalize removes transient render floor only.
Optional --reference BLEND records/comparers frozen authored geometry independent of materials.
"""
import bpy,json,math,os,sys,argparse,hashlib,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--finalize',action='store_true');p.add_argument('--reference',type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
P=Path(__file__).resolve().parents[1]
def shapes():
 out={}
 for ob in bpy.data.collections['SM_ThornBramble_01'].objects:
  h=hashlib.sha256();me=ob.data
  for v in me.vertices:h.update(struct.pack('<fff',*v.co))
  for f in me.polygons:h.update(struct.pack('<II',len(f.vertices),f.material_index));h.update(struct.pack('<'+'I'*len(f.vertices),*f.vertices))
  for uv in me.uv_layers[0].data:h.update(struct.pack('<ff',*uv.uv))
  out[ob.name]=h.hexdigest()
 return out
if a.reference:
 bpy.ops.wm.open_mainfile(filepath=str(a.reference));golden=shapes();(P/'FrozenV9GeometryIdentity.json').write_text(json.dumps({'source_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),'geometry_uv_materialindex_sha256':golden},indent=2)+'\n')
else:golden=json.load(open(P/'FrozenV9GeometryIdentity.json'))['geometry_uv_materialindex_sha256']
bpy.ops.wm.open_mainfile(filepath=str(P/'ThornBramble_SharedSourceV1.blend'))
if a.finalize:
 bpy.data.collections['SM_ThornBramble_01']['dink_source']='Original procedural study9073; originalgrave-07.bmp guide; registered shared bark2m/broadleaftrim source candidate; native pending'
 for ob in list(bpy.data.objects):
  if ob.type=='MESH' and any(m and m.name=='QA_Ground' for m in ob.data.materials):bpy.data.objects.remove(ob,do_unlink=True)
 if bpy.data.materials.get('QA_Ground'):bpy.data.materials.remove(bpy.data.materials['QA_Ground'])
 for im in bpy.data.images:
  if im.packed_file:im.filepath='//../../../SharedMaterials/ThornBarkBroadleafV1/Textures/'+Path(im.filepath).name
 bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.file_preview_type='NONE';bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThornBramble_SharedSourceV1.blend'))
assert shapes()==golden,'Frozen geometry/UV/material-slot-index mismatch'
C=bpy.data.collections['SM_ThornBramble_01'];assert len(C.objects)==3;rows=[]
for ob in sorted(C.objects,key=lambda o:o.name):
 me=ob.data;me.calc_loop_triangles();assert len(me.uv_layers)==1 and len(me.materials)==2;assert tuple(ob.scale)==(1,1,1);assert all(math.isfinite(c) for v in me.vertices for c in v.co);assert min(v.co.z for v in me.vertices)==0;assert all(math.isfinite(c) for uv in me.uv_layers[0].data for c in uv.uv);assert len(me.loop_triangles)<=25000
 assert [m.name for m in me.materials]==['MI_Shared_ThornBark2m','MI_Shared_BroadleafTrimV1']
 areas=[(me.vertices[t.vertices[1]].co-me.vertices[t.vertices[0]].co).cross(me.vertices[t.vertices[2]].co-me.vertices[t.vertices[0]].co).length*.5 for t in me.loop_triangles];assert min(areas)>1e-12
 edges={}
 for f in me.polygons:
  for edge in f.edge_keys:edges.setdefault(tuple(sorted(edge)),[]).append(f.material_index)
 wood=sum(len(m)==1 and m[0]==0 for m in edges.values());leaf=sum(len(m)==1 and m[0]==1 for m in edges.values());nm=sum(len(m)>2 for m in edges.values());assert wood==0 and nm==0
 rows.append({'name':ob.name,'triangles':len(me.loop_triangles),'dimensions_m':list(ob.dimensions),'minZ':min(v.co.z for v in me.vertices),'min_triangle_area_m2':min(areas),'degenerate_at_1e12':0,'woody_boundary_edges':wood,'intentional_leaf_boundary_edges':leaf,'edges_over_2_faces':nm,'materials':[m.name for m in me.materials]})
packed={}
for im in bpy.data.images:
 if im.packed_file:
  path=P.parents[2]/'SharedMaterials/ThornBarkBroadleafV1/Textures'/Path(im.filepath).name;assert hashlib.sha256(im.packed_file.data).digest()==hashlib.sha256(path.read_bytes()).digest();packed[im.name]={'sha256':hashlib.sha256(im.packed_file.data).hexdigest(),'colorspace':im.colorspace_settings.name}
assert len(packed)==6
r={'status':'SOURCE_CHECK_PASS_not_export_native_or_visual_acceptance','frozen_v9_geometry_uv_materialindex_exact':True,'meshes':rows,'packed_images':packed,'LOD0_soft_target_warning':True,'studio_floor_removed_after_review_renders':True};(P/'SourceCheck.json').write_text(json.dumps(r,indent=2)+'\n');print('SOURCE_CHECK_PASS',flush=True);os._exit(0)
