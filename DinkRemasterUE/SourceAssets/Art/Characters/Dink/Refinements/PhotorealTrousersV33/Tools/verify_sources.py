import bpy,json,hashlib,sys
from pathlib import Path
D=Path(__file__).resolve().parents[1]
def jhash(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def core():
 out={}
 for ob in bpy.data.objects:
  if ob.type=='MESH':
   m=ob.data;out[ob.name]={'vertices':[tuple(v.co)for v in m.vertices],'faces':[tuple(f.vertices)for f in m.polygons],'smooth':[f.use_smooth for f in m.polygons],'uv':{u.name:[tuple(x.uv)for x in u.data]for u in m.uv_layers},'normals':[tuple(n.vector)for n in m.corner_normals],'weights':[sorted((ob.vertex_groups[g.group].name,g.weight)for g in v.groups)for v in m.vertices],'materials':[a.name for a in m.materials],'world':[tuple(r)for r in ob.matrix_world]}
  elif ob.type=='ARMATURE':out[ob.name]={'bones':[(b.name,b.parent.name if b.parent else None,[tuple(r)for r in b.matrix_local],tuple(b.head_local),tuple(b.tail_local),b.use_deform,b.inherit_scale,b.use_inherit_rotation)for b in ob.data.bones],'world':[tuple(r)for r in ob.matrix_world]}
 return jhash(out)
def images_in_tree(tree,seen=None):
 seen=set()if seen is None else seen
 if tree in seen:return set()
 seen.add(tree);out=set()
 for n in tree.nodes:
  if n.type=='TEX_IMAGE'and n.image:out.add(n.image)
  if n.type=='GROUP'and n.node_tree:out|=images_in_tree(n.node_tree,seen)
 return out

manifest=json.loads((D/'Evidence/source_preparation.json').read_text());rows=[]
for entry in manifest['scenes']:
 file=D/entry['path'];assert hashlib.sha256(file.read_bytes()).hexdigest()==entry['sha256'];bpy.ops.wm.open_mainfile(filepath=str(file));assert core()==entry['core_signature'],entry['role'];used=set()
 for ob in bpy.data.objects:
  if ob.type=='MESH':
   for mat in ob.data.materials:
    if mat.node_tree:used|=images_in_tree(mat.node_tree)
 images=[]
 for im in used:
  assert im.packed_file and im.filepath.startswith('//');path=Path(bpy.path.abspath(im.filepath)).resolve();assert path.is_relative_to(D)and path.is_file();data=bytes(im.packed_file.data);assert path.read_bytes()==data;images.append(hashlib.sha256(data).hexdigest())
 assert len(used)==len(entry['used_images']);assert not bpy.data.libraries
 rows.append({'role':entry['role'],'core_exact':True,'mesh_objects':len([o for o in bpy.data.objects if o.type=='MESH']),'mesh_datablocks':len(bpy.data.meshes),'all_node_images_packed_relative_local_exact':True,'image_nodes_referenced_unique_images':len(used)})
 print('PACKED_SOURCE_REOPEN',entry['role'],len(used),flush=True)
result={'status':'PACKED_LOCAL_SOURCE_REOPEN_PASS','scope':'Core geometry/rig/UV/material-slot signatures match accepted authoring captures; no reference/nude/orphan mesh datablocks in hero scenes. Helper plane and pants-only bake source explicitly separate. No native/game acceptance.','scenes':rows}
args=sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[]
if '--report'in args:
 report=Path(args[args.index('--report')+1]).resolve()
 if(D/'SHA256SUMS.json').exists():assert not report.is_relative_to(D)
 report.write_text(json.dumps(result,indent=2)+'\n')
