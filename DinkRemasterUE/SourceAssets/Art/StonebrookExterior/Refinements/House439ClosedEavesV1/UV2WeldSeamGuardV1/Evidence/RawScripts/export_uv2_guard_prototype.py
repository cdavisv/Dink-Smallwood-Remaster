import bpy,json,hashlib,numpy as np
from pathlib import Path
D=Path(__file__).resolve().parents[1];(D/'FBX').mkdir(exist_ok=True);P=Path('<HOME>/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE/SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/Packet/Source/House439_ClosedEaves.blend');sha=hashlib.sha256(P.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(P));source=list(dict.fromkeys([bpy.data.objects['SM_Cottage_Stonebrook_01']]+list(bpy.data.collections['House439_ProductionMineralCandidateV1'].objects)));source=[o for o in source if o.type=='MESH'and not o.name.startswith('UCX_')];tmp=bpy.data.collections.new('TEMP_ASSEMBLY_QA');bpy.context.scene.collection.children.link(tmp);copies=[];records=[];ordinal=0;material_ids={}
for o in source:
 c=o.copy();c.data=o.data.copy();tmp.objects.link(c);copies.append(c);c.hide_set(False);c.hide_viewport=False;c.hide_select=False;bpy.ops.object.select_all(action='DESELECT');c.select_set(True);bpy.context.view_layer.objects.active=c;mod=c.modifiers.new('QA_ExplicitTriangles','TRIANGULATE')
 if hasattr(mod,'keep_custom_normals'):mod.keep_custom_normals=True
 bpy.ops.object.modifier_apply(modifier=mod.name);m=c.data;attr=m.attributes.new(name='QA_CornerOrdinal',type='INT',domain='CORNER');nm=c.matrix_world.to_3x3().inverted().transposed();uv0=m.uv_layers.get('UV0');uv1=m.uv_layers.get('UV1_SharedData');color=m.color_attributes.get('SharedSurfaceData');normcache=[(nm@n.vector).normalized()for n in m.corner_normals];poscache=[c.matrix_world@v.co for v in m.vertices];attr.data.foreach_set('value',np.arange(ordinal,ordinal+len(m.loops),dtype=np.int32))
 for p in m.polygons:
  name=m.materials[p.material_index].name;material_ids.setdefault(name,len(material_ids))
  for li in p.loop_indices:
   pos=poscache[m.loops[li].vertex_index];n=normcache[li];records.append(tuple(pos)+tuple(n)+tuple(uv0.data[li].uv if uv0 else(0,0))+tuple(uv1.data[li].uv if uv1 else(0,0))+tuple(color.data[li].color if color else(0,0,0,0))+(material_ids[name],));ordinal+=1
print('SOURCE_SNAPSHOT_DONE',len(copies),len(records),flush=True);expected=np.array(records,np.float64);bpy.ops.object.select_all(action='DESELECT')
for c in copies:c.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;print('JOIN_DONE',flush=True);m=joined.data;attr=m.attributes['QA_CornerOrdinal'];uv0=m.uv_layers.get('UV0');uv1=m.uv_layers.get('UV1_SharedData');color=m.color_attributes.get('SharedSurfaceData');nm=joined.matrix_world.to_3x3().inverted().transposed();assert np.max(np.abs(np.array(joined.matrix_world)-np.eye(4)))<1e-12
restore=[expected[attr.data[li].value,3:6].tolist()for li in range(len(m.loops))];m.normals_split_custom_set(restore);actual=np.empty_like(expected);ids=[]
for p in m.polygons:
 for li in p.loop_indices:
  idx=attr.data[li].value;ids.append(idx);pos=joined.matrix_world@m.vertices[m.loops[li].vertex_index].co;n=(nm@m.corner_normals[li].vector).normalized();actual[idx]=tuple(pos)+tuple(n)+tuple(uv0.data[li].uv if uv0 else(0,0))+tuple(uv1.data[li].uv if uv1 else(0,0))+tuple(color.data[li].color if color else(0,0,0,0))+(material_ids[m.materials[p.material_index].name],)
assert len(ids)==len(set(ids))==len(expected)and set(ids)==set(range(len(expected)))
err=np.max(np.abs(expected-actual),axis=0);normal_degrees=np.degrees(np.arccos(np.clip(np.sum(expected[:,3:6]*actual[:,3:6],axis=1)/(np.linalg.norm(expected[:,3:6],axis=1)*np.linalg.norm(actual[:,3:6],axis=1)),-1,1)));pass_data=bool(max(err[:3])<1e-5 and max(err[6:])<1e-6 and normal_degrees.max()<.05);m.calc_loop_triangles();r={'scope':'Temporary copy triangulation+one-mesh join only; original source notsaved, no native/FBX/shader interpretation proof','source_sha256_unchanged':sha,'source_mesh_objects':len(source),'triangles':len(m.loop_triangles),'unique_source_corners':len(expected),'joined_UV_layers':[u.name for u in m.uv_layers],'joined_color_layers':[c.name for c in m.color_attributes],'material_roles':list(material_ids),'max_world_position_error_m':float(max(err[:3])),'normal_angle_degrees_p50_p95_max':np.percentile(normal_degrees,[50,95,100]).tolist(),'max_UV0_error':float(max(err[6:8])),'max_UV1_SharedData_error':float(max(err[8:10])),'max_SharedSurfaceData_RGBA_error':float(max(err[10:14])),'material_role_mismatches':int(np.sum(expected[:,14]!=actual[:,14])),'joined_world_TRS':[list(r)for r in joined.matrix_world],'explicit_postjoin_normals_restored':True,'data_join_pass':pass_data};(D/'Evidence/EXPORT_JOIN.json').write_text(json.dumps(r,indent=2));assert hashlib.sha256(P.read_bytes()).hexdigest()==sha;print(json.dumps(r));assert pass_data

# Export disposable assembly plus original six collision hulls; original .blend remains untouched.
from io_scene_fbx import parse_fbx
m.attributes.remove(m.attributes['QA_CornerOrdinal']);m.color_attributes.active_color_name='SharedSurfaceData'
# Remove unused inherited slots only in disposable export; per-face semantic roles stay exact.
used={p.material_index for p in m.polygons};unused=[(i,x.name)for i,x in enumerate(m.materials)if i not in used]
for i,name in reversed(unused):m.materials.pop(index=i)
assert len(m.materials)==len(material_ids)

original_root=bpy.data.objects.get('SM_Cottage_Stonebrook_01')
if original_root!=joined:bpy.data.objects.remove(original_root,do_unlink=True)
joined.name='SM_Cottage_Stonebrook_01';hulls=[o for o in bpy.data.objects if o.type=='MESH'and o.name.startswith('UCX_SM_Cottage_Stonebrook_01')];assert len(hulls)==6
hull_before={o.name:{'p':np.array([tuple(v.co)for v in o.data.vertices]),'TRS':np.array(o.matrix_world),'faces':[tuple(p.vertices)for p in o.data.polygons]}for o in hulls}
def snap(o):
 m=o.data;m.calc_loop_triangles();m.calc_tangents(uvmap='UV0');return {'p':np.array([tuple(v.co)for v in m.vertices]),'loops':np.array([l.vertex_index for l in m.loops]),'UV':{u.name:np.array([tuple(x.uv)for x in u.data])for u in m.uv_layers},'n':np.array([tuple(n.vector)for n in m.corner_normals]),'t':np.array([tuple(l.tangent)for l in m.loops]),'s':np.array([l.bitangent_sign for l in m.loops]),'RGBA':np.array([tuple(c.color)for c in m.color_attributes['SharedSurfaceData'].data]),'roles':[m.materials[p.material_index].name for p in m.polygons],'triangles':len(m.loop_triangles)}
a=snap(joined)
reference_path=Path('<HOME>/Work/DinkQA/House439ExplicitTangentsNativeReference/FROZEN_FBX_GEOMETRY.npz')
assert hashlib.sha256(reference_path.read_bytes()).hexdigest()=='20e969bcd0f4fae11f47d6d224e8063eb802e615263a8304ecd0c16c020d0c3d'
with np.load(reference_path,allow_pickle=False) as reference:
 frozen_uv=np.concatenate([reference['uv0'],reference['uv1']],axis=1).astype('<f4')
original_uv=np.concatenate([a['UV']['UV0'],a['UV']['UV1_SharedData']],axis=1).astype('<f4')
assert np.array_equal(original_uv.view('<u4'),frozen_uv.view('<u4'))
uv_keys,guard_ids=np.unique(original_uv.view('<u4'),axis=0,return_inverse=True)
guard_grid=np.column_stack((guard_ids%1024,guard_ids//1024)).astype(np.float32)
assert np.array_equal(guard_grid[:,0].astype(np.int64)+1024*guard_grid[:,1].astype(np.int64),guard_ids)
assert np.array_equal(np.unique(guard_ids),np.arange(len(uv_keys)))
assert len(m.uv_layers)==2 and m.uv_layers[0].name=='UV0' and m.uv_layers[1].name=='UV1_SharedData'
guard_layer=m.uv_layers.new(name='UV2_WeldSeamGuard');guard_layer.data.foreach_set('uv',guard_grid.reshape(-1))
assert len(m.uv_layers)==3 and m.uv_layers[2].name=='UV2_WeldSeamGuard'
np.savez_compressed(D/'Evidence/UV2_GUARD_ARRAYS.npz',uv_tuple_uint32_keys=uv_keys,corner_guard_id=guard_ids.astype(np.uint32),source_guard_grid=guard_grid)
(D/'Evidence/UV2_GUARD_DEFINITION.json').write_text(json.dumps(dict(profile='house439_uv2_weld_seam_guard_v1',canonical_key='Exact IEEE754 float32 UV0/UV1 bits; signed zero retained',encoding='(denseID %1024,denseID //1024)',corners=len(guard_ids),unique_uv_tuples=len(uv_keys),maximum_id=int(guard_ids.max()),guard_coordinates_integer=True,original_uv_bits_match_frozen_reference=True,original_geometry_reference_sha256='20e969bcd0f4fae11f47d6d224e8063eb802e615263a8304ecd0c16c020d0c3d',source_only=True,no_native_admission=True),indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT');joined.select_set(True)
for o in hulls:o.hide_set(False);o.hide_viewport=False;o.hide_select=False;o.select_set(True)
bpy.context.view_layer.objects.active=joined;fbx=D/'FBX/SM_Cottage_Stonebrook_01.fbx';bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},use_mesh_modifiers=True,mesh_smooth_type='EDGE',use_triangles=True,use_tspace=True,use_custom_props=False,colors_type='LINEAR',prioritize_active_color=True,apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_space_transform=True,bake_anim=False,path_mode='RELATIVE',embed_textures=False,batch_mode='OFF')
# Inspect actual serialized Color0 before importer conversion.
root,version=parse_fbx.parse(str(fbx));objs=next(e for e in root.elems if e.id==b'Objects');geos=[g for g in objs.elems if g.id==b'Geometry'];colored=[]
for g in geos:
 layers=[e for e in g.elems if e.id==b'LayerElementColor'and e.props[0]==0]
 if not layers:continue
 parts={e.id:e.props[0]for e in layers[0].elems}
 if parts[b'Name']!=b'SharedSurfaceData':continue
 assert parts[b'MappingInformationType']==b'ByPolygonVertex'and parts[b'ReferenceInformationType']==b'IndexToDirect';binary=np.array(parts[b'Colors']).reshape(-1,4)[np.array(parts[b'ColorIndex'])];assert binary.shape==a['RGBA'].shape;error=float(np.max(np.abs(binary-a['RGBA'])));colored.append({'geometry':g.props[1].split(b'\x00\x01')[0].decode(errors='replace'),'layer0':'SharedSurfaceData','corners':len(binary),'RGBA_error':error});assert error==0
assert len(colored)==1
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(fbx),use_custom_normals=True,use_image_search=False,colors_type='LINEAR');b=snap(bpy.data.objects['SM_Cottage_Stonebrook_01']);assert a['p'].shape==b['p'].shape and np.array_equal(a['loops'],b['loops'])
def angles(x,y):
 q=np.sum(x*y,axis=1)/(np.linalg.norm(x,axis=1)*np.linalg.norm(y,axis=1));return np.percentile(np.degrees(np.arccos(np.clip(q,-1,1))),[50,95,100]).tolist()
hull_rows=[]
for name,v in hull_before.items():
 o=bpy.data.objects[name];p=np.array([tuple(v.co)for v in o.data.vertices]);hull_rows.append({'name':name,'positions_shape_exact':p.shape==v['p'].shape,'max_position_error_m':float(np.max(np.abs(p-v['p'])))if p.shape==v['p'].shape else None,'max_TRS_error':float(np.max(np.abs(np.array(o.matrix_world)-v['TRS'])))})
r={'scope':'Actual disposable one-mesh full-house FBX plus6UCX export/import and rawColor0 arrays. Not native Unreal shader/material/collision/art acceptance.','triangles_before_after':[a['triangles'],b['triangles']],'max_position_error_m':float(np.max(np.abs(a['p']-b['p']))),'UV_errors':{k:float(np.max(np.abs(v-b['UV'][k])))for k,v in a['UV'].items()},'linear_RGBA_import_error':float(np.max(np.abs(a['RGBA']-b['RGBA']))),'normal_difference_degrees':angles(a['n'],b['n']),'Mikk_difference_degrees':angles(a['t'],b['t']),'zeroT_counts':[int(np.sum(np.linalg.norm(x['t'],axis=1)<1e-10))for x in [a,b]],'bitangent_sign_changes':int(np.sum(a['s']!=b['s'])),'material_roles_exact':a['roles']==b['roles'],'actual_material_slots':[x.name for x in bpy.data.objects['SM_Cottage_Stonebrook_01'].data.materials],'unused_export_slots_removed':[name for i,name in unused],'rawColor0':colored,'collision_hulls':hull_rows,'source_sha256_unchanged':sha,'fbx_sha256':hashlib.sha256(fbx.read_bytes()).hexdigest()}
r['transport_profile']='house439_uv2_weld_seam_guard_v1';r['guard_uv_roundtrip_error']=float(np.max(np.abs(b['UV']['UV2_WeldSeamGuard']-guard_grid)));r['guard_integer_roundtrip_exact']=bool(np.array_equal(b['UV']['UV2_WeldSeamGuard'],guard_grid));assert r['guard_integer_roundtrip_exact'];r['pass']=bool(r['triangles_before_after']==[a['triangles'],a['triangles']]and r['max_position_error_m']<1e-5 and max(r['UV_errors'].values())<1e-6 and r['linear_RGBA_import_error']<.005 and r['normal_difference_degrees'][-1]<.05 and r['Mikk_difference_degrees'][-1]<.05 and r['zeroT_counts']==[0,0]and r['bitangent_sign_changes']==0 and r['material_roles_exact']and all(h['positions_shape_exact']and h['max_position_error_m']<1e-5 and h['max_TRS_error']<1e-6 for h in hull_rows));(D/'Evidence/EXPORT_READBACK.json').write_text(json.dumps(r,indent=2));assert hashlib.sha256(P.read_bytes()).hexdigest()==sha;print('FULL_FBX',json.dumps(r),flush=True);assert r['pass']
