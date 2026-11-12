"""Inspect actual registered opaque graphs; read-only Blender source."""
import bpy,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parents[1];L=D.parents[2]/'SharedMaterials';P=L/'ArchitecturalSurfaces2mV1/SharedArchitecturalSurfaces_Source.blend';before=hashlib.sha256(P.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(P));rows={}
for m in bpy.data.materials:
 if not m.name.startswith('MI_Shared_'):continue
 nodes=[]
 for n in m.node_tree.nodes:
  inputs=[]
  for i,s in enumerate(n.inputs):
   v=getattr(s,'default_value',None)
   if v is not None:
    try:v=list(v)
    except TypeError:
     try:v=float(v)
     except(TypeError,ValueError):v=str(v)
   inputs.append({'index':i,'name':s.name,'value':v,'linked':s.is_linked})
  r={'name':n.name,'type':n.type,'inputs':inputs}
  for prop in ['operation','blend_type','use_clamp','uv_map','layer_name','space','interpolation','extension']:
   if hasattr(n,prop):r[prop]=getattr(n,prop)
  if n.type=='TEX_IMAGE':r['image']={'name':n.image.name,'packed_sha256':hashlib.sha256(bytes(n.image.packed_file.data)).hexdigest(),'colorspace':n.image.colorspace_settings.name}
  nodes.append(r)
 links=[{'from_node':l.from_node.name,'from_socket':list(l.from_node.outputs).index(l.from_socket),'from_name':l.from_socket.name,'to_node':l.to_node.name,'to_socket':list(l.to_node.inputs).index(l.to_socket),'to_name':l.to_socket.name}for l in m.node_tree.links];rows[m.name]={'nodes':nodes,'links':links}
assert before==hashlib.sha256(P.read_bytes()).hexdigest();(D/'OPAQUE_GRAPH_SOURCE.json').write_text(json.dumps({'status':'ACTUAL_REGISTERED_GRAPH_EXTRACTION','source_sha256':before,'materials':rows},indent=2)+'\n');print('OPAQUE_GRAPH_EXTRACTION',len(rows))
