import bpy,json,hashlib,math,sys,os
from pathlib import Path
O=Path(__file__).resolve().parent
try:
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();path=O/'PhotorealCandleV1_Export.blend';pin=sha(path);bpy.ops.wm.open_mainfile(filepath=str(path));prefix='SM_Candle_Iron_01';srcs={i:bpy.data.objects[prefix+'_LOD'+str(i)].data.copy()for i in range(3)}
 optics={m.name:{k:list(bs.inputs[k].default_value)if k=='Subsurface Radius'else bs.inputs[k].default_value for k in ['IOR','Specular IOR Level','Subsurface Weight','Subsurface Scale','Subsurface Radius']}for m in bpy.data.objects[prefix+'_LOD0'].data.materials for bs in m.node_tree.nodes if bs.type=='BSDF_PRINCIPLED'}
 fbx=O/'Export/Game/Dink/Props/Stonebrook/PhotorealCandleV1/SM_Candle_Iron_01.fbx';before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(fbx),use_custom_normals=True);added=set(bpy.data.objects)-before;meshes=[o for o in added if o.type=='MESH'];assert len(meshes)==3;assert not any(o.name.startswith('UCX_')for o in added);reports=[]
 for level,src in srcs.items():
  ob=next(o for o in meshes if o.name.split('.')[0]==prefix+'_LOD'+str(level));me=ob.data;me.transform(ob.matrix_world);ob.matrix_world.identity();assert len(me.polygons)==len(src.polygons)==[4870,2434,1218][level];assert len(me.materials)==2
  tris=[];index={}
  for p in src.polygons:
   assert len(p.vertices)==3;row=[(src.vertices[src.loops[i].vertex_index].co.copy(),src.uv_layers.active.data[i].uv.copy(),src.corner_normals[i].vector.copy())for i in p.loop_indices];idx=len(tris);tris.append((row,p.material_index))
   for pos,uv,n in row:index.setdefault(tuple(round(float(v)*1e5)for v in pos),set()).add(idx)
  used=set();maxpos=maxuv=maxangle=0;mindot=1
  for p in me.polygons:
   assert len(p.vertices)==3;row=[(me.vertices[me.loops[i].vertex_index].co.copy(),me.uv_layers.active.data[i].uv.copy(),me.corner_normals[i].vector.copy())for i in p.loop_indices];key=tuple(round(float(v)*1e5)for v in row[0][0]);candidates=set()
   for x in [-1,0,1]:
    for y in [-1,0,1]:
     for z in [-1,0,1]:candidates.update(index.get((key[0]+x,key[1]+y,key[2]+z),[]))
   match=None
   for i in candidates-used:
    original,mat=tris[i]
    for shift in range(3):
     sr=original[shift:]+original[:shift];pd=max((a[0]-b[0]).length for a,b in zip(row,sr));ud=max((a[1]-b[1]).length for a,b in zip(row,sr))
     if pd<1e-5 and ud<1e-5:match=(i,sr,pd,ud,mat);break
    if match:break
   assert match is not None,(level,p.index);i,sr,pd,ud,mat=match;assert p.material_index==mat;used.add(i);maxpos=max(maxpos,pd);maxuv=max(maxuv,ud)
   nf=(row[1][0]-row[0][0]).cross(row[2][0]-row[0][0]).normalized();sf=(sr[1][0]-sr[0][0]).cross(sr[2][0]-sr[0][0]).normalized();mindot=min(mindot,nf.dot(sf))
   for a,b in zip(row,sr):maxangle=max(maxangle,a[2].angle(b[2],0))
  assert len(used)==len(tris)and mindot>.999 and maxangle<.001
  reports.append({'LOD':level,'triangles':len(me.polygons),'max_position_delta_m':maxpos,'max_UV_delta':maxuv,'minimum_front_dot':mindot,'max_normal_angle_radians':maxangle,'all_material_ids_preserved':True,'slots':2})
 assert sha(path)==pin
 (O/'roundtrip_receipt.json').write_text(json.dumps({'passed':True,'export_sha256':pin,'FBX_sha256':sha(fbx),'LODs':reports,'authored_UCX_count':0,'baked_Blender_material_optics':optics,'limits':'Actual Blender FBX geometry/UV/normal/materialID roundtrip. Wax SSS retained in baked Blender shader; FBX/native SSS/flame/LOD-distance acceptance still unproven. LOD2 small sourceUVoverlap remains qualified.'},indent=2)+'\n')
except BaseException:
 import traceback;traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
