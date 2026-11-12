import bpy,json,hashlib,struct,sys,os
from pathlib import Path
Q=Path(__file__).resolve().parents[1]
def geometry(o):
 me=o.data;h=hashlib.sha256()
 for v in me.vertices:h.update(struct.pack('<3f',*v.co))
 for p in me.polygons:h.update(struct.pack('<ii?',len(p.vertices),p.material_index,p.use_smooth));h.update(struct.pack('<'+'i'*len(p.vertices),*p.vertices))
 for layer in me.uv_layers:
  h.update(layer.name.encode())
  for d in layer.data:h.update(struct.pack('<2f',*d.uv))
 for n in me.corner_normals:h.update(struct.pack('<3f',*n.vector))
 h.update('|'.join(m.name for m in me.materials).encode());return h.hexdigest()
source=Q/'portable.source.blend';pin='ee159f2d54a0431e6d8fa67541df5b3a370b85ccf4e42e3ea80bdacfe4c0faa5'
assert hashlib.sha256(source.read_bytes()).hexdigest()==pin
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
obs=list(bpy.data.collections['V4_AsymmetricRigidVariant_Editable'].objects);bpy.context.view_layer.update()
expected=json.loads((Q/'Evidence/Composition/VARIANT_RECEIPT.json').read_bytes())
assert len(obs)==25 and {o.name:geometry(o)for o in obs}==expected['geometry_fingerprints']
triangles=0
for o in obs:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
assert triangles==15680
names=['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron']
graphs={};images={}
for name in names:
 m=bpy.data.materials[name];assert m.use_nodes
 graphs[name]={'nodes':sorted((n.name,n.bl_idname)for n in m.node_tree.nodes),'links':sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier)for l in m.node_tree.links)}
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE':
   i=n.image;assert i is not None and i.packed_file
   images[i.name]={'sha256':hashlib.sha256(bytes(i.packed_file.data)).hexdigest(),'colorspace':i.colorspace_settings.name,'size':list(i.size)}
assert len(graphs)==3 and len(images)==9
result={'source_sha256':pin,'relocated_reopened':True,'geometry_fingerprints_exact':True,'objects':25,'triangles':triangles,'graphs':graphs,'packed_images':images,'rendered':False,'saved_source':False}
args=sys.argv[sys.argv.index('--')+1:];assert len(args)==2 and args[0]=='--receipt'
out=Path(args[1]).resolve();assert not out.exists() and Q not in out.parents
out.write_text(json.dumps(result,indent=2)+'\n');print('RELOCATED_SOURCE_PASS',str(out));sys.stdout.flush();os._exit(0)
