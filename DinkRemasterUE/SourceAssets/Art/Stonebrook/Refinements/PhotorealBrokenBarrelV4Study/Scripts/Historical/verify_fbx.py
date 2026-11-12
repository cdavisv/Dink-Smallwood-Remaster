from pathlib import Path
import sys,json,hashlib,numpy as np
from collections import Counter
sys.path.insert(0,str(Path.home()/'Work/DinkPhotorealBrokenBarrelSourceDelivery/tools/blender'))
from dinkasset import fbxparse
Q=Path(__file__).resolve().parent;p=Q/'SM_Barrel_Broken_CurvedV4_LOD0.fbx';version,top=fbxparse.parse(str(p));nodes={x.name:x for x in top};objs=nodes['Objects'];geoms=objs.find('Geometry');models=objs.find('Model');assert len(geoms)==len(models)==1
g=geoms[0];v=np.array(g.first('Vertices').props[0],np.float32).reshape(-1,3);idx=np.array(g.first('PolygonVertexIndex').props[0],np.int64).reshape(-1,3);assert np.all(idx[:,:2]>=0)and np.all(idx[:,2]<0);idx=np.where(idx<0,-idx-1,idx);P=v[idx]
def channel(layer,key,width,index):
 n=g.first(layer);assert n.first('MappingInformationType').props[0]=='ByPolygonVertex';x=np.array(n.first(key).props[0],np.float32).reshape(-1,width)
 if n.first('ReferenceInformationType').props[0]=='IndexToDirect':x=x[np.array(n.first(index).props[0],np.int64)]
 else:assert n.first('ReferenceInformationType').props[0]=='Direct'
 return x.reshape(-1,3,width)
N=channel('LayerElementNormal','Normals',3,'NormalsIndex');UV=channel('LayerElementUV','UV',2,'UVIndex');M=np.array(g.first('LayerElementMaterial').first('Materials').props[0],np.uint16);src=np.load(Q/'SOURCE_TRIANGLES.npz');exact={k:bool(np.array_equal(a,src[k]))for k,a in {'position':P,'normal':N,'uv':UV,'material':M}.items()};assert all(exact.values()),exact
edges=Counter(tuple(sorted((int(t[i]),int(t[(i+1)%3]))))for t in idx for i in range(3));assert all(c==2 for c in edges.values())
assert all(np.isfinite(a).all()for a in [v,N,UV]);norms=np.linalg.norm(N.astype(float),axis=-1);assert (norms>0).all()
areas=np.linalg.norm(np.cross(P[:,1].astype(float)-P[:,0],P[:,2].astype(float)-P[:,0]),axis=-1)/2;assert (areas>1e-12).all()
vol=float(np.sum(np.sum(P[:,0].astype(float)*np.cross(P[:,1].astype(float),P[:,2].astype(float)),axis=-1))/6);assert vol>0
info=fbxparse.inspect(str(p));assert info['unit_scale_factor']==100
props=fbxparse._p70(models[0]);print(props);assert props.get('Lcl Scaling',[1,1,1])==[1,1,1];assert props.get('Lcl Translation',[0,0,0])==[0,0,0];assert props.get('Lcl Rotation',[0,0,0])==[0,0,0]
settings=fbxparse._p70(nodes['GlobalSettings']);assert settings['UpAxis']==2 and settings['UpAxisSign']==1 and settings['FrontAxis']==1 and settings['FrontAxisSign']==-1
mats=[n.props[1].split('\x00')[0]for n in objs.find('Material')];assert mats==['MI_Shared_OakLonggrain2m','MI_Shared_OakEndgrain2m','MI_Stonebrook_WroughtIron'],mats
videos=[{'name':n.props[1],'filename':n.first('Filename').props[0] if n.first('Filename') else None,'embedded':bool(n.first('Content'))}for n in objs.find('Video')];assert not any(r['embedded']for r in videos);assert all(r['filename']==Path(r['filename']).name for r in videos)
assert all('UCX'not in str(n.props)and 'LODGroup'not in str(n.props)for n in objs.children)
assert not g.first('LayerElementTangent')and not g.first('LayerElementBinormal')
r={'PASS':True,'serialized_closed_edge_count_two':True,'serialized_positive_signed_volume_m3':vol,'finite_positions_UV_normals':True,'min_triangle_area_m2':float(areas.min()),'fbx_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'binary_version':version,'single_mesh_single_node':True,'triangles':len(P),'source_to_serialized_float32_channels_exact':exact,'source_to_serialized_normal_angle_degrees':0,'material_slots':mats,'node_properties':props,'global_settings':settings,'bounds_m':{'min':P.min((0,1)).tolist(),'max':P.max((0,1)).tolist()},'external_basename_texture_references_no_embedded_pixels':videos,'no_UCX_or_LOD_siblings':True,'tangent_basis_omitted_generate_native_Mikk_pending':True,'scope':'Independent stdlib binary parser validates serialized channels, not Blender custom-normal codec or native importer'}
(Q/'SERIALIZED_FBX_CHECK.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'PASS':True,'exact':exact,'materials':mats}))
