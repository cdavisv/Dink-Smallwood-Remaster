"""Register shared material identities in a new cottage source; leave geometry/UVs exact.
Usage: blender ... --python build_source.py -- --donor /path/to/reviewed.blend
Glass physical mapping qualification remains pending; no native admission.
"""
import bpy,json,hashlib,numpy as np,sys
from pathlib import Path
D=Path(__file__).resolve().parents[1];L=D.parents[2]/'SharedMaterials';donor=Path(sys.argv[sys.argv.index('--donor')+1]).resolve() if '--donor' in sys.argv else D/'Provenance/ReviewedGeometry_Source.blend';donor_sha=hashlib.sha256(donor.read_bytes()).hexdigest();registry=json.loads((L/'manifest.json').read_text())['materials'];aliases=json.loads((L/'ArchitecturalSurfaces2mV1/registry.json').read_text())['source_material_aliases'];aliases['MI_House439_OpticalGlass_SourceV21']='MI_Shared_ThinWavyGlass2m'
assert donor_sha=='140622758031f459fc2b00f0886dd2e141ef6ab9d23dc85df67368bad283d089','Reviewed donor bytes differ'
bpy.ops.wm.open_mainfile(filepath=str(donor))
def packed(collection,prop,width,dtype=np.float32):
 a=np.empty(len(collection)*width,dtype=dtype);collection.foreach_get(prop,a);return hashlib.sha256(a.tobytes()).hexdigest()
def snapshot():
 rows={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  m=o.data;r={'TRS':[list(x)for x in o.matrix_world],'vertex_positions':packed(m.vertices,'co',3),'loop_indices':packed(m.loops,'vertex_index',1,np.int32),'polygon_starts':packed(m.polygons,'loop_start',1,np.int32),'polygon_sizes':packed(m.polygons,'loop_total',1,np.int32),'material_indices':packed(m.polygons,'material_index',1,np.int32),'corner_normals':packed(m.corner_normals,'vector',3),'UV':{x.name:packed(x.data,'uv',2)for x in m.uv_layers},'colors':{x.name:packed(x.data,'color',4)for x in m.color_attributes},'material_roles':[aliases.get(x.name,x.name)if x else None for x in m.materials],'modifiers':[(x.name,x.type)for x in o.modifiers]};rows[o.name]=r
 return rows
before=snapshot();sources={}
for new in aliases.values():
 key=new.removeprefix('MI_Shared_');entry=registry[key];path=L/entry['source'];sources.setdefault(path,[]).append(new)
for path,names in sources.items():
 with bpy.data.libraries.load(str(path),link=False)as(a,b):b.materials=names
for old,new in aliases.items():
 original=bpy.data.materials[old];registered=bpy.data.materials[new];original.user_remap(registered);bpy.data.materials.remove(original)
after=snapshot();assert before==after,'Mesh/UV/N/TRS/color/material semantics changed'
# Normalize actual image paths to the registered resource; pixels stay packed and exact.
allowed={x['sha256']:L/x['file']for key in [v.removeprefix('MI_Shared_')for v in aliases.values()]for var in registry[key].get('variants',{'Default':{'textures':registry[key]['textures']}}).values()for x in var['textures'].values()}
for new in aliases.values():
 for node in bpy.data.materials[new].node_tree.nodes:
  if node.type!='TEX_IMAGE':continue
  im=node.image;assert im.packed_file;sha=hashlib.sha256(bytes(im.packed_file.data)).hexdigest();path=allowed[sha];assert hashlib.sha256(path.read_bytes()).hexdigest()==sha;im.filepath=bpy.path.relpath(str(path),start=str(D))
out=D/'House439_SharedExterior_Source.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True);bpy.ops.wm.open_mainfile(filepath=str(out));reopened=snapshot();assert before==reopened;assert hashlib.sha256(donor.read_bytes()).hexdigest()==donor_sha
r={'status':'PASS_material_identity_swap_all_mesh_data_exact','donor_sha256_unchanged':donor_sha,'source_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'mesh_objects_checked':len(before),'material_aliases':aliases,'original_mesh_snapshot':before,'reopened_exact':True,'glass_mapping_qualification':'Actual glass triangle metrics prove mainpanes2m/UV, slightbevelanisotropy; Root explicitly accepted keeping originalUV0/sampler0. Existing UVs preserved exactly.','native_status':'No UE execution or final appearance approval'};(D/'SOURCE_EQUIVALENCE.json').write_text(json.dumps(r,indent=2)+'\n');print('SOURCE_EQUIVALENCE_PASS',len(before))
