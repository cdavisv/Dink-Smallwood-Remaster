"""Prove generated image affects BC only, with exact V3 geometry and non-BC shader inputs retained."""
import bpy,json,hashlib,sys,os,traceback
from pathlib import Path
O=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def value(v):
 if hasattr(v,'__len__')and not isinstance(v,str):return [float(x)for x in v]
 return v if isinstance(v,(str,int,float,bool,type(None)))else str(v)
def tree(socket,stack=None):
 if not socket.is_linked:return {'default':value(getattr(socket,'default_value',None))}
 link=socket.links[0];node=link.from_node;stack=set()if stack is None else stack;assert node.name not in stack;new=stack|{node.name}
 props={k:value(getattr(node,k))for k in ['operation','feature','distance','dimensions','noise_dimensions','voronoi_dimensions','normalize','attribute_name','interpolation_type','clamp','data_type','blend_type','use_clamp','invert']if hasattr(node,k)}
 return {'name':node.name,'kind':node.bl_idname,'output':link.from_socket.identifier,'properties':props,'inputs':{str(i)+':'+s.identifier:tree(s,new)for i,s in enumerate(node.inputs)}}
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));c=bpy.data.collections['SM_Pie_Rustic_01'];meshes={}
 for o in c.objects:
  if o.type!='MESH':continue
  me=o.data;meshes[o.name]={'positions':[list(v.co)for v in me.vertices],'faces':[(list(p.vertices),p.material_index,p.use_smooth)for p in me.polygons],'UV0':[list(d.uv)for d in me.uv_layers.active.data],'corner_normals':[list(n.vector)for n in me.corner_normals],'matrix':[list(r)for r in o.matrix_world],'material_slots':[m.name for m in me.materials],'attributes':{n:[d.value for d in me.attributes[n].data]for n in ['Browning','FruitMask']}}
 mats={}
 for mat in bpy.data.objects['SM_Pie_Rustic_01_LOD0'].data.materials:
  bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');mats[mat.name]={str(i)+':'+s.identifier:tree(s)for i,s in enumerate(bs.inputs)if s.name!='Base Color'}
 return meshes,mats
try:
 baseline=O/'Inputs/V3_Source.blend';current=O/'PhotorealPieV1_Source.blend';assert sha(baseline)=='eb43ac65cce5d84b8880adf5dbef0e69b46f51005748f8e7e4dbe9adae38e8bb';a,ma=snapshot(baseline);b,mb=snapshot(current);assert a==b,'Geometry/UV/normals/materialIDs/attributes changed';assert ma==mb,'A non-BC shader input/dependency changed'
 mat=bpy.data.materials['MI_Pie_PastryFruit_PhotoSource'];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bc=tree(bs.inputs['Base Color']);assert 'GeneratedShortcrust_DIFFUSE_ONLY'in json.dumps(bc);assert all('GeneratedShortcrust_DIFFUSE_ONLY'not in json.dumps(graph)for graph in mb.values())
 ref=O/'Textures/GeneratedShortcrust_Albedo_V1.png';assert sha(ref)=='4b211bc541e2bdced47dc483c3378d03f4f64411823a2052d41537c0c3fe233b';receipt={'passed':True,'source_sha256':sha(current),'frozen_V3_sha256':sha(baseline),'geometry_UV_cornernormals_materialIDs_attributes_all3LODs_exact':True,'all_non_BaseColor_principled_inputs_and_upstream_graphs_exact':True,'generated_image_reaches_pastry_BaseColor_only':True,'no_BC_derived_normal_height_roughness':True,'reference_sha256':sha(ref),'native_imported':False};(O/'reference_only_verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
