import bpy,bmesh,numpy as np,json,hashlib,sys,os,traceback
from pathlib import Path
Q=Path(__file__).resolve().parent
SRC=Path('/home/artist/Work/DinkQA/PhotorealBrokenBarrelAsymmetricV4Variant/PhotorealBrokenBarrelV4_AsymmetricComposition.blend')
PIN='d91d35d37225aeec36a5795197dcc5ec1b425b7bb2cfb7c6c2e1fe00650bee8c'
MATS=['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def angle(a,b):
 a=a.astype(float);b=b.astype(float);a/=np.linalg.norm(a,axis=-1,keepdims=True);b/=np.linalg.norm(b,axis=-1,keepdims=True)
 return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=-1),np.sum(a*b,axis=-1)))
try:
 assert sha(SRC)==PIN
 bpy.ops.wm.open_mainfile(filepath=str(SRC),load_ui=False,use_scripts=False)
 bpy.context.preferences.filepaths.save_version=0
 parts=sorted(bpy.data.collections['V4_AsymmetricRigidVariant_Editable'].objects,key=lambda o:o.name);assert len(parts)==25
 bpy.context.view_layer.update();vertices=[];faces=[];uvs=[];normals=[];roles=[];rows=[];source_positions=[]
 for o in parts:
  assert o.type=='MESH' and not o.modifiers and o.matrix_world.to_3x3().determinant()>0
  me=o.data;me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume(signed=True)>0;bm.free()
  offset=len(vertices);vs=[tuple(o.matrix_world@v.co)for v in me.vertices];vertices+=vs
  nm=o.matrix_world.to_3x3().inverted().transposed();uv=me.uv_layers.active
  for t in me.loop_triangles:
   faces.append(tuple(offset+i for i in t.vertices));uvs.extend([tuple(uv.data[l].uv)for l in t.loops]);normals.extend([tuple((nm@me.corner_normals[l].vector).normalized())for l in t.loops]);roles.append(MATS.index(me.materials[t.material_index].name));source_positions.extend([vs[i]for i in t.vertices])
  rows.append({'piece':o.name,'triangles':len(me.loop_triangles),'source_matrix_world':[list(r)for r in o.matrix_world]})
 assert len(faces)==15680
 # New scene contains only one proposed render mesh, no comparison geometry or collision.
 scene=bpy.data.scenes.new('BrokenBarrelV4_LOD0_ExportOnly');bpy.context.window.scene=scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 me=bpy.data.meshes.new('SM_Barrel_Broken_CurvedV4_LOD0');me.from_pydata(vertices,[],faces);me.update()
 for n in MATS:me.materials.append(bpy.data.materials[n])
 layer=me.uv_layers.new(name='UVMap')
 for l,u in zip(layer.data,uvs):l.uv=u
 for p,m in zip(me.polygons,roles):p.material_index=m;p.use_smooth=True
 for edge in me.edges:edge.use_edge_sharp=True
 me.normals_split_custom_set(normals)
 o=bpy.data.objects.new(me.name,me);scene.collection.objects.link(o);bpy.context.view_layer.update()
 N=np.array([tuple(n.vector)for n in me.corner_normals],np.float32);UV=np.array(uvs,np.float32);P=np.array(source_positions,np.float32).reshape(-1,3,3)
 errors=angle(np.array(normals,np.float32),N);assert np.isfinite(errors).all()
 bm=bmesh.new();bm.from_mesh(me);closed=all(e.is_manifold for e in bm.edges);vol=bm.calc_volume(signed=True);areas=[f.calc_area()for f in bm.faces];bm.free()
 assert closed and vol>0 and min(areas)>1e-12
 for a in [P,N,UV]:assert np.isfinite(a).all()
 uvtri=UV.reshape(-1,3,2);a=uvtri[:,1]-uvtri[:,0];b=uvtri[:,2]-uvtri[:,0];uvarea=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0]);assert (uvarea>1e-12).all()
 me.calc_tangents(uvmap='UVMap');T=np.array([tuple(l.tangent)for l in me.loops],np.float32);B=np.array([tuple(l.bitangent)for l in me.loops],np.float32)
 assert np.isfinite(T).all()and np.isfinite(B).all()and (np.linalg.norm(T,axis=-1)>0).all()and (np.linalg.norm(B,axis=-1)>0).all()
 np.savez_compressed(Q/'PREEXPORT.npz',position=P,uv=UV.reshape(-1,3,2),normal=N.reshape(-1,3,3),material=np.array(roles,np.uint16),tangent=T.reshape(-1,3,3),bitangent=B.reshape(-1,3,3))
 imgs={n.image.name:n.image for m in MATS for n in bpy.data.materials[m].node_tree.nodes if n.type=='TEX_IMAGE'};assert len(imgs)==9
 imagefacts={n:{'packed_sha256':hashlib.sha256(bytes(i.packed_file.data)).hexdigest(),'size':list(i.size),'colorspace':i.colorspace_settings.name,'alpha_mode':i.alpha_mode}for n,i in imgs.items()}
 receipt={'source':str(SRC),'source_sha256':PIN,'pieces':rows,'triangles':len(faces),'vertices':len(vertices),'materials':MATS,'packed_maps':imagefacts,'source_to_temporary_union_codec_max_normal_angle_degrees':float(errors.max()),'normal_gate_degrees':.05,'normal_gate_pass':bool(errors.max()<=.05),'closed':closed,'positive_signed_volume_m3':vol,'bounds_m':{'min':P.min((0,1)).tolist(),'max':P.max((0,1)).tolist(),'size':np.ptp(P.reshape(-1,3),axis=0).tolist()},'source_file_unchanged':sha(SRC)==PIN,'pivot_m':[0,0,0],'frame':'Blender metres; Y forward / Z up; header100cm, node identity; UE importer converts metres to cm and handedness','guide_soft_6000_exceeded':True,'guide_hard_20000_exceeded':False,'export_ready':False}
 (Q/'EXPORT_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
 # Preserve source normals directly in the serialized ByPolygonVertex channel.
 # Blender's custom-normal codec is not used as an authoring approximation.
 from io_scene_fbx import export_fbx_bin
 old_normal_writer=export_fbx_bin.elem_data_single_float64_array
 old_index_writer=export_fbx_bin.elem_data_single_int32_array
 old_string_writer=export_fbx_bin.elem_data_single_string_unicode
 def string_writer(parent,name,data):
  if name in {b'FileName',b'Filename',b'RelativeFilename'}:data=os.path.basename(data)
  return old_string_writer(parent,name,data)
 export_fbx_bin.elem_data_single_string_unicode=string_writer
 desired=np.array(normals,np.float32)
 def normal_writer(parent,name,data):
  return old_normal_writer(parent,name,desired.reshape(-1).astype(np.float64) if name==b'Normals' else data)
 def index_writer(parent,name,data):
  return old_index_writer(parent,name,np.arange(len(desired),dtype=np.int32) if name==b'NormalsIndex' else data)
 export_fbx_bin.elem_data_single_float64_array=normal_writer
 export_fbx_bin.elem_data_single_int32_array=index_writer
 np.savez_compressed(Q/'SOURCE_TRIANGLES.npz',position=P,uv=UV.reshape(-1,3,2),normal=desired.reshape(-1,3,3),material=np.array(roles,np.uint16))
 receipt['temporary_union_codec_normal_angle_degrees']=float(errors.max())
 receipt['normal_gate_pass']=None
 receipt['normal_serialization']='Original transformed source normals injected into installed public exporter array writer; identity NormalsIndex; independent binary verification required'
 receipt['tangent_basis']='Omitted: no claim that temporary union codec tangents preserve authored basis; native Mikk generation remains untested'
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 bpy.ops.export_scene.fbx(filepath=str(Q/'SM_Barrel_Broken_CurvedV4_LOD0.fbx'),use_selection=True,object_types={'MESH'},use_mesh_modifiers=True,mesh_smooth_type='FACE',use_triangles=False,use_tspace=False,colors_type='LINEAR',use_custom_props=False,apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_space_transform=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',embed_textures=False)
 # Save inspectable union without hidden archived/context object datablocks.
 for obj in list(bpy.data.objects):
  if obj!=o:bpy.data.objects.remove(obj,do_unlink=True)
 for s in list(bpy.data.scenes):
  if s!=scene:bpy.data.scenes.remove(s)
 bpy.ops.wm.save_as_mainfile(filepath=str(Q/'BrokenBarrelCurvedV4_ExportOnly.blend'))
 receipt['fbx_sha256']=sha(Q/'SM_Barrel_Broken_CurvedV4_LOD0.fbx');receipt['union_blend_sha256']=sha(Q/'BrokenBarrelCurvedV4_ExportOnly.blend');receipt['source_file_unchanged']=sha(SRC)==PIN
 (Q/'EXPORT_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'exported':True,'max_normal_angle':float(errors.max()),'tris':len(faces)}));sys.stdout.flush();os._exit(0)
except BaseException:traceback.print_exc();sys.stderr.flush();os._exit(1)
