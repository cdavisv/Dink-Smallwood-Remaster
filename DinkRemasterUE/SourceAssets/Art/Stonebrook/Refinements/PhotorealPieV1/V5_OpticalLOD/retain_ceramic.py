import bpy,json,hashlib,sys,os,traceback
from pathlib import Path
O=Path(__file__).resolve().parent
try:
 p=O/'Inputs/V4_Export.blend';assert hashlib.sha256(p.read_bytes()).hexdigest()=='92215f62f62097cad6c412e19242b8467a62dcec2be04ba8ce23dbb933c03d6e'
 bpy.ops.wm.open_mainfile(filepath=str(p));lod0=bpy.data.objects['SM_Pie_Rustic_01_LOD0'].data;dish=[p.index for p in lod0.polygons if p.material_index==0];assert len(dish)==860;reports=[]
 for level in [1,2]:
  ob=bpy.data.objects['SM_Pie_Rustic_01_LOD'+str(level)];old=ob.data;food=[p.index for p in old.polygons if p.material_index==1];sources=[(old,i)for i in food]+[(lod0,i)for i in dish]
  coords=[];origins=[];faces=[];normals=[];layers={u.name:[]for u in old.uv_layers};mids=[];smooth=[];lookup={}
  for me,fi in sources:
   poly=me.polygons[fi];face=[];assert len(poly.vertices)==3
   for li in poly.loop_indices:
    vi=me.loops[li].vertex_index;key=(me.name,vi)
    if key not in lookup:lookup[key]=len(coords);coords.append(me.vertices[vi].co.copy());origins.append((me,vi))
    face.append(lookup[key]);normals.append(me.corner_normals[li].vector.copy())
    for name in layers:layers[name].append(me.uv_layers[name].data[li].uv.copy())
   faces.append(face);mids.append(poly.material_index);smooth.append(poly.use_smooth)
  new=bpy.data.meshes.new(old.name+'_OpticalLOD');new.from_pydata(coords,[],faces);new.update()
  for mat in old.materials:new.materials.append(mat)
  for poly,mi,sm in zip(new.polygons,mids,smooth):poly.material_index=mi;poly.use_smooth=sm
  for name,values in layers.items():
   layer=new.uv_layers.new(name=name)
   for dst,value in zip(layer.data,values):dst.uv=value
  for name in ['Browning','FruitMask']:
   attr=new.attributes.new(name,'FLOAT','POINT')
   for dst,(me,vi)in zip(attr.data,origins):dst.value=me.attributes[name].data[vi].value
  new.normals_split_custom_set(normals);new.update();maxangle=max(a.angle(b.vector,0)for a,b in zip(normals,new.corner_normals));assert maxangle<.001
  for face,(me,fi)in zip(new.polygons,sources):
   original=me.polygons[fi];assert face.material_index==original.material_index
   for a,b in zip(face.loop_indices,original.loop_indices):
    assert (new.vertices[new.loops[a].vertex_index].co-me.vertices[me.loops[b].vertex_index].co).length==0
    for name in layers:assert (new.uv_layers[name].data[a].uv-me.uv_layers[name].data[b].uv).length==0
  name=old.name;old.name=name+'_PriorLOD';new.name=name;ob.data=new;bpy.data.meshes.remove(old)
  reports.append(dict(LOD=level,triangles=len(new.polygons),retained_food_triangles=len(food),exact_LOD0_ceramic_triangles=len(dish),max_normal_angle_radians=maxangle,geometry_UV_materialIDs_point_attributes_preserved=True))
 assert [r['triangles']for r in reports]==[3046,2048]
 for image in bpy.data.images:
  if image.type=='IMAGE' and image.users>0:image.filepath='//Textures/'+Path(image.filepath).name
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealPieV1_Export.blend'),relative_remap=False)
 (O/'optical_lod_report.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),LODs=reports,reason='Preserve ceramic silhouette/glaze normals through opticalLOD; food retains previous reductions. No new bake/material/LOD0 changes.'),indent=2));print('OPTICAL_LOD_COMPLETE',flush=True)
except BaseException:traceback.print_exc();os._exit(1)
os._exit(0)
