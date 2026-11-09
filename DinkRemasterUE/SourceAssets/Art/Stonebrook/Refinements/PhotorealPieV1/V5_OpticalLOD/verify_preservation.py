import bpy,json,math,hashlib,os,traceback
from pathlib import Path
O=Path(__file__).resolve().parent
try:
 def graph(m):
  nodes=[]
  for n in m.node_tree.nodes:
   inputs=[]
   for ss in n.inputs:
    if hasattr(ss,'default_value'):
     v=ss.default_value;inputs.append((ss.identifier,list(v)if hasattr(v,'__len__') else v))
   nodes.append(dict(name=n.name,type=n.bl_idname,inputs=inputs,image=hashlib.sha256(bytes(n.image.packed_file.data)).hexdigest()if n.type=='TEX_IMAGE'and n.image else None))
  return dict(nodes=nodes,links=[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier)for l in m.node_tree.links])
 def capture():
  result=[]
  for level in range(3):
   ob=bpy.data.objects['SM_Pie_Rustic_01_LOD'+str(level)];me=ob.data;faces=[]
   for p in me.polygons:
    row=[]
    for li in p.loop_indices:
     vi=me.loops[li].vertex_index
     row.append(dict(pos=list(me.vertices[vi].co),uv={u.name:list(u.data[li].uv)for u in me.uv_layers},normal=list(me.corner_normals[li].vector),attributes={k:me.attributes[k].data[vi].value for k in ['Browning','FruitMask']}))
    faces.append(dict(material=p.material_index,smooth=p.use_smooth,corners=row))
   result.append(dict(faces=faces,transform=[list(r)for r in ob.matrix_world],materials=[graph(m)for m in me.materials]))
  return result
 bpy.ops.wm.open_mainfile(filepath=str(O/'Inputs/V4_Export.blend'));old=capture()
 bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPieV1_Export.blend'));new=capture();assert old[0]==new[0],'LOD0 must be exact';rows=[]
 for level in [1,2]:
  a=old[level];b=new[level];assert a['transform']==b['transform'];assert a['materials']==b['materials']
  food=[f for f in a['faces']if f['material']==1];dish=[f for f in old[0]['faces']if f['material']==0];expected=food+dish;assert len(expected)==len(b['faces']);angle=0
  from mathutils import Vector
  for aa,bb in zip(expected,b['faces']):
   assert aa['material']==bb['material']and aa['smooth']==bb['smooth']
   for ca,cb in zip(aa['corners'],bb['corners']):
    for key in ['pos','uv','attributes']:assert ca[key]==cb[key],(level,key)
    angle=max(angle,Vector(ca['normal']).angle(Vector(cb['normal']),0))
  assert angle<.001
  rows.append(dict(LOD=level,food_corner_positions_UV_attributes_materials_exact=True,full_LOD0_dish_corner_positions_UV_attributes_exact=True,max_normal_angle_radians=angle))
 (O/'preservation.json').write_text(json.dumps(dict(passed=True,LOD0_all_mesh_corner_data_and_material_graphs_exact=True,nonLOD_material_graphs_and_packed_image_bytes_exact=True,LODs=rows),indent=2));print('PRESERVATION_PASS',flush=True)
except BaseException:traceback.print_exc();os._exit(1)
os._exit(0)
