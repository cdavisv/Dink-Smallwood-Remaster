from pathlib import Path
import sys,json,hashlib,numpy as np
P=Path('<HOME>/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE');Q=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P/'Scripts'));import props_fbxparse as F
old=Path('<HOME>/Work/DinkQA/House439ExplicitTangentsV1/FBX/SM_Cottage_Stonebrook_01.fbx');new=Q/'FBX/SM_Cottage_Stonebrook_01.fbx';ref=Path('<HOME>/Work/DinkQA/House439ExplicitTangentsNativeReference/FROZEN_FBX_GEOMETRY.npz');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def parse(p):
 _,nodes=F.parse(p);objects=next(n for n in nodes if n.name=='Objects');return nodes,objects,{g.props[1]:g for g in objects.children if g.name=='Geometry'}
a,oa,ga=parse(old);b,ob,gb=parse(new);assert set(ga)==set(gb) and len(ga)==7
main_names=[name for name in ga if name.startswith('SM_Cottage_Stonebrook_01_Mesh')];assert len(main_names)==1
main_name=main_names[0]
skip={'LayerElementUV','LayerElementTangent','LayerElementBinormal','Layer'}
def keep(n):return not(n.name in skip and n.props==[2])
reevaluated=[]
def angle(x,y):
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(x,y),axis=1),np.sum(x*y,axis=1)))
def same(x,y,path,allow_base_tbn=False):
 assert x.name==y.name,path
 if allow_base_tbn and x.name in ['Tangents','Binormals']:
  old_array=np.asarray(x.props[0],float).reshape(-1,3);new_array=np.asarray(y.props[0],float).reshape(-1,3)
  assert old_array.shape==new_array.shape==(547878,3),(path,old_array.shape,new_array.shape)
  delta=float(np.abs(old_array-new_array).max());assert delta<=5.960464477539063e-8
  reevaluated.append(dict(array=x.name,components_differ=int((old_array!=new_array).sum()),max_scalar_difference=delta,max_angle_vs22a2_degrees=float(angle(old_array,new_array).max())))
 else:assert x.props==y.props,path
 xc=[n for n in x.children if keep(n)];yc=[n for n in y.children if keep(n)];assert len(xc)==len(yc),path
 allow_children=x.name in ['LayerElementTangent','LayerElementBinormal'] and x.props==[0] and path.startswith(main_name+'/')
 for i,(u,v) in enumerate(zip(xc,yc)):same(u,v,path+'/'+u.name+str(i),allow_children)
for name in ga:
 assert ga[name].props[1:]==gb[name].props[1:]
 x=[n for n in ga[name].children if keep(n)];y=[n for n in gb[name].children if keep(n)];assert len(x)==len(y)
 for u,v in zip(x,y):same(u,v,name+'/'+u.name)
assert F._p70(next(n for n in a if n.name=='GlobalSettings'))==F._p70(next(n for n in b if n.name=='GlobalSettings'))
assert {n.props[1]:F._p70(n) for n in oa.children if n.name=='Model'}=={n.props[1]:F._p70(n) for n in ob.children if n.name=='Model'}
main=gb[main_name]
def values(kind,index,data_name,columns):
 node=next(n for n in main.children if n.name==kind and n.props==[index]);d={n.name:n.props[0] for n in node.children};assert d['MappingInformationType']=='ByPolygonVertex';v=np.asarray(d[data_name],float).reshape(-1,columns)
 if d['ReferenceInformationType']=='IndexToDirect':v=v[np.asarray(d[data_name+'Index'],int)]
 else:assert d['ReferenceInformationType']=='Direct'
 return d,v
uvs=[values('LayerElementUV',i,'UV',2) for i in [0,1,2]];assert [x[0]['Name'] for x in uvs]==['UV0','UV1_SharedData','UV2_WeldSeamGuard'];original=np.concatenate([uvs[0][1],uvs[1][1]],axis=1).astype('<f4')
with np.load(ref,allow_pickle=False) as z:frozen=np.concatenate([z['uv0'],z['uv1']],axis=1).astype('<f4');assert np.array_equal(original.view('<u4'),frozen.view('<u4'))
keys,ids=np.unique(original.view('<u4'),axis=0,return_inverse=True);expected=np.column_stack([ids%1024,ids//1024]).astype(np.float32);actual=uvs[2][1];assert actual.shape==(547878,2) and np.array_equal(actual,expected);assert np.array_equal(actual[:,0].astype(np.int64)+1024*actual[:,1].astype(np.int64),ids);assert len(keys)==137348
base=next(n for n in main.children if n.name=='Layer' and n.props==[0]);bindings={n.first('Type').props[0]:n.first('TypedIndex').props[0] for n in base.children if n.name=='LayerElement'};assert bindings['LayerElementUV']==bindings['LayerElementTangent']==bindings['LayerElementBinormal']==0
nt,normals=values('LayerElementNormal',0,'Normals',3)
tt,tangents=values('LayerElementTangent',0,'Tangents',3)
bt,binormals=values('LayerElementBinormal',0,'Binormals',3)
with np.load(ref,allow_pickle=False) as z:
    normal_angle=float(angle(normals,z['normal']).max());tangent_angle=float(angle(tangents,z['tangent']).max())
    reference_b=np.cross(z['normal'],z['tangent'])*z['bitangent_sign'][:,None]
    binormal_angle=float(angle(binormals,reference_b).max())
    signs=np.sign(np.sum(np.cross(normals,tangents)*binormals,axis=1));sign_changes=int((signs!=z['bitangent_sign']).sum())
zero_counts={name:int((np.linalg.norm(a,axis=1)<=1e-10).sum()) for name,a in [('N',normals),('T',tangents),('B',binormals)]}
assert normal_angle<.05 and tangent_angle<.05 and sign_changes==0 and not any(zero_counts.values())
for name,digest in json.loads((Q/'PRESERVED_INPUT_PINS.json').read_text()).items():assert sha(Path(name))==digest
r=dict(scope='Independent serialized3UV QA proof; no project/native admission',profile='house439_uv2_weld_seam_guard_v1',predecessor_fbx_sha256=sha(old),prototype_fbx_sha256=sha(new),original_geometry_reference_sha256=sha(ref),corners=len(actual),unique_uv_tuples=len(keys),guard_uv2_name=uvs[2][0]['Name'],guard_grid_integer_exact=True,same_tuple_same_guard_and_distinct_tuple_distinct_guard=True,minimum_distinct_guard_separation=1.0,native_weld_uv_epsilon=1/1024,all_original_geometry_UV01_N_RGBA_material_smoothing_winding_and_six_UCX_arrays_exact=True,base_T_B_bitidentical=False,base_T_B_reevaluation=reevaluated,max_normal_vs_frozen_degrees=normal_angle,max_tangent_vs_frozen_degrees=tangent_angle,max_binormal_vs_frozen_degrees=binormal_angle,bitangent_sign_changes=sign_changes,base_zero_vector_counts=zero_counts,original_point05_normal_tangent_gate_unchanged=True,all_model_transforms_and_axis_units_exact=True,base_layer0_bindings=bindings,legacy_two_uv_project_validator_unchanged=True,native_acceptance=False)
(Q/'Evidence/SERIALIZED_UV2_GUARD_READBACK_V2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
