import bpy,json,sys,os,hashlib,traceback,math
from pathlib import Path
O=Path(__file__).resolve().parent;S=O.parent;BASE=O/'Inputs/V4_Source.blend'
try:
 def snapshot(path):
  bpy.ops.wm.open_mainfile(filepath=str(path));objects={};materials={}
  for ob in bpy.data.objects:
   if ob.type!='MESH':continue
   me=ob.data;objects[ob.name]={'matrix':[list(row)for row in ob.matrix_world],'vertices':[list(v.co)for v in me.vertices],'polygons':[list(p.vertices)for p in me.polygons],'normals':[list(n.vector)for n in me.corner_normals],'slots':[m.name if m else None for m in me.materials],'attributes':{a.name:[list(x.vector)for x in a.data]if a.data_type=='FLOAT_VECTOR'else[float(x.value)for x in a.data]for a in me.attributes if a.name in ['ReedMetric','ReedSeed']}}
  for mat in bpy.data.materials:
   if not mat.node_tree:continue
   nodes=[]
   for n in mat.node_tree.nodes:
    inputs={}
    for v in n.inputs:
     if not hasattr(v,'default_value'):continue
     value=v.default_value
     if isinstance(value,(int,float,str,bool)):inputs[v.identifier]=value
     elif hasattr(value,'__len__'):inputs[v.identifier]=list(value)
    nodes.append({'name':n.name,'type':n.bl_idname,'inputs':inputs,'operation':getattr(n,'operation',None),'attribute_name':getattr(n,'attribute_name',None),'image':n.image.name if hasattr(n,'image')and n.image else None,'ramp':[(e.position,list(e.color))for e in n.color_ramp.elements]if hasattr(n,'color_ramp')else None})
   materials[mat.name]={'nodes':nodes,'links':[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier)for l in mat.node_tree.links]}
  return {'objects':objects,'materials':materials}
 before=snapshot(BASE);after=snapshot(O/'PhotorealBasketV1_Source.blend');assert before==after,'Non-UV asset state differs'
 sys.path.insert(0,str(O/'Pipeline'));from dinkasset.validate import uv_stats,validate_scene
 me=bpy.data.objects['SM_Basket_Wicker_01'].data;stats=uv_stats(me,max_pairs=10000000);assert not stats['truncated'],'Still incomplete overlap audit';assert stats['overlapping_tris']==stats['degenerate_tris']==stats['tris_out_of_range']==0,stats
 bpy.context.window.scene=bpy.data.scenes['BasketSource'];guide=validate_scene(only=['SM_Basket_Wicker_01']);assert guide['summary']['errors']==0
 (O/'guide_validation.json').write_text(json.dumps(guide,indent=2)+'\n')
 r={'passed':True,'source_state_except_UV_unchanged':True,'state_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),'all_mesh_positions_topology_normals_materials_attributes_and_transforms_checked':True,'complete_UV_overlap_stats':stats,'density_px_per_m':2048*math.sqrt(stats['uv_area']/stats['area_3d']),'guide_summary':guide['summary'],'source_sha256':hashlib.sha256((O/'PhotorealBasketV1_Source.blend').read_bytes()).hexdigest()}
 (O/'uv_verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.stdout.flush();sys.stderr.flush();os._exit(0)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
