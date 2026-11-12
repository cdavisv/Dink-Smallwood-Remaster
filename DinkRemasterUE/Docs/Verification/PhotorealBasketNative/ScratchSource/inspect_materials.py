from pathlib import Path
import bpy,json,hashlib,os
root=Path(Path.home()/'Work/DinkBasketSourceDelivery/DinkRemasterUE/SourceAssets/Art/Stonebrook/Refinements/PhotorealBasketV1')
out=Path(Path.home()/'Work/DinkQA/BasketImportDevelopment')
rows=[]
for obj in bpy.data.objects:
 if obj.type!='MESH' or not obj.name.startswith('SM_Basket_Wicker_01') or obj.name.startswith('UCX_'):continue
 slots=[]
 for mat in obj.data.materials:
  nodes=[]
  for n in mat.node_tree.nodes if mat and mat.use_nodes else []:
   if n.type!='BSDF_PRINCIPLED':continue
   vals={}
   for key in ['IOR','Specular IOR Level','Specular Tint','Metallic','Coat Weight','Coat Tint','Transmission Weight','Subsurface Weight','Sheen Weight','Emission Strength','Thin Film Thickness','Alpha']:
    sock=n.inputs.get(key)
    if sock is None:continue
    val=sock.default_value
    vals[key]={'default':list(val)if hasattr(val,'__len__')else float(val),'linked':sock.is_linked,'links':[{'from_node':l.from_node.name,'from_socket':l.from_socket.name}for l in sock.links]}
   nodes.append({'node':n.name,'values':vals})
  slots.append({'material':mat.name if mat else None,'principled':nodes})
 rows.append({'object':obj.name,'materials':slots})
report={'blend':bpy.data.filepath,'sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'blender':bpy.app.version_string,'objects':rows,'no_blend_save_performed':True}
name=Path(bpy.data.filepath).stem;(out/(name+'_material_readback.json')).write_text(json.dumps(report,indent=2)+'\n');print('MATERIAL_READBACK',name,len(rows),flush=True);os._exit(0)
