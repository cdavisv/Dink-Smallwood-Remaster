import bpy,json,hashlib
from pathlib import Path
from collections import Counter
from io_scene_fbx import parse_fbx
root=Path(__file__).resolve().parents[1];source=root/'Source/House439_ClosedEaves.blend';bpy.ops.wm.open_mainfile(filepath=str(source))
objects=list(dict.fromkeys([bpy.data.objects['SM_Cottage_Stonebrook_01']]+list(bpy.data.collections['House439_ProductionMineralCandidateV1'].objects)));objects=[o for o in objects if o.type=='MESH' and not o.name.startswith('UCX_')]
counts=Counter();object_roles={}
for o in objects:
 roles=Counter()
 for f in o.data.polygons:
  name=o.data.materials[f.material_index].name;roles[name]+=len(f.vertices)-2;counts[name]+=len(f.vertices)-2
 object_roles[o.name]=dict(roles)
export=json.loads((root/'Evidence/EXPORT_READBACK.json').read_text());roles=[]
for slot,name in enumerate(export['actual_material_slots']):
 mat=bpy.data.materials[name];nodes=mat.node_tree.nodes;stack=[n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output];seen=set();images=[];normal_strength=[]
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  if n.type=='TEX_IMAGE' and n.image:
   im=n.image;path=Path(bpy.path.abspath(im.filepath));images.append({'node':n.name,'image':im.name,'relative_path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'colorspace':im.colorspace_settings.name})
  if n.type=='NORMAL_MAP':normal_strength.append({'node':n.name,'space':n.space,'uv_map':n.uv_map,'default_strength':n.inputs['Strength'].default_value,'strength_links':[{'node':l.from_node.name,'socket':l.from_socket.name} for l in n.inputs['Strength'].links]})
  for socket in n.inputs:
   stack.extend(l.from_node for l in socket.links)
 roles.append({'export_slot':slot,'source_material':name,'triangles':counts[name],'connected_images':images,'normal_maps':normal_strength,'source_graph_only':True,'native_destination':None,'native_rebind_requires_current_manifest_inventory':True})
fbx=root/'FBX/SM_Cottage_Stonebrook_01.fbx';tree,version=parse_fbx.parse(str(fbx));settings=next(x for x in tree.elems if x.id==b'GlobalSettings');props=next(x for x in settings.elems if x.id==b'Properties70');frame={}
for prop in props.elems:
 if prop.id==b'P':
  key=prop.props[0].decode(errors='replace')
  if key in ('UpAxis','UpAxisSign','FrontAxis','FrontAxisSign','CoordAxis','CoordAxisSign','UnitScaleFactor','OriginalUnitScaleFactor'):frame[key]=prop.props[-1]
coords=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
render_bounds=[list(min(q[i] for q in coords) for i in range(3)),list(max(q[i] for q in coords) for i in range(3))]
report={'assembled_render_bounds_m':render_bounds,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'fbx_sha256':hashlib.sha256(fbx.read_bytes()).hexdigest(),'fbx_version':version,'fbx_frame':frame,'export_world_TRS':json.loads((root/'Evidence/EXPORT_JOIN.json').read_text())['joined_world_TRS'],'roles':roles,'source_object_roles':object_roles,'native_requirements':['Preserve current-master PR59 lighting and PR60 fireplace/chimney/material bindings','Inventory fresh current native role destinations before staging; no old AB Data overlay','Roof source Normal Map Strength uses SharedSurfaceData.R; explicit native carrier support required','Source OpenGL +Y normal maps need appropriate native green-channel handling; do not reinterpret color maps','Use approved normal/Mikk edge-smoothing exporter; face-smoothing failure retained'],'native_import_executed':False}
(root/'Evidence/ROLE_BINDINGS_AND_FRAME.json').write_text(json.dumps(report,indent=2)+'\n');print('roles',len(roles),'objects',len(objects),'connected images',len({x['sha256'] for r in roles for x in r['connected_images']}),'frame',frame)
