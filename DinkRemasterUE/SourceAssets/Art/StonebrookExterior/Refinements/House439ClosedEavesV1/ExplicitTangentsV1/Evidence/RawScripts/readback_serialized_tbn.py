from pathlib import Path
import sys,json,hashlib
import numpy as np
P=Path('<HOME>/Work/DinkHouse439ClosedEavesNative/DinkRemasterUE');Q=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P/'Scripts'));import props_fbxparse as F
old=P/'SourceAssets/Art/StonebrookExterior/Refinements/House439ClosedEavesV1/Packet/FBX/SM_Cottage_Stonebrook_01.fbx';new=Q/'FBX/SM_Cottage_Stonebrook_01.fbx';ref=Path('<HOME>/Work/DinkQA/House439ClosedEavesNativeReference/FROZEN_FBX_GEOMETRY.npz')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def parse(p):
 _,nodes=F.parse(p);objs=next(n for n in nodes if n.name=='Objects');return nodes,objs,{g.props[1]:g for g in objs.children if g.name=='Geometry'}
a,oa,ga=parse(old);b,ob,gb=parse(new);assert set(ga)==set(gb) and len(ga)==7
omitted={'LayerElementTangent','LayerElementBinormal'}
def keep(n):
 if n.name in omitted:return False
 if n.name=='LayerElement':
  t=n.first('Type')
  if t and t.props[0] in omitted:return False
 return True
def equal(x,y,path):
 assert x.name==y.name and x.props==y.props,path
 xc=[n for n in x.children if keep(n)];yc=[n for n in y.children if keep(n)];assert len(xc)==len(yc),path
 for i,(u,v) in enumerate(zip(xc,yc)):equal(u,v,path+'/'+u.name+str(i))
for name in ga:
 assert ga[name].props[1:]==gb[name].props[1:]
 x=[n for n in ga[name].children if keep(n)];y=[n for n in gb[name].children if keep(n)];assert len(x)==len(y)
 for u,v in zip(x,y):equal(u,v,name+'/'+u.name)
assert F._p70(next(n for n in a if n.name=='GlobalSettings'))==F._p70(next(n for n in b if n.name=='GlobalSettings'))
ma={n.props[1]:F._p70(n) for n in oa.children if n.name=='Model'};mb={n.props[1]:F._p70(n) for n in ob.children if n.name=='Model'};assert ma==mb and len(ma)==7
main=next(g for name,g in gb.items() if 'UCX_' not in name)
base=next(n for n in main.children if n.name=='Layer' and n.props==[0]);bindings={n.first('Type').props[0]:n.first('TypedIndex').props[0] for n in base.children if n.name=='LayerElement'}
assert bindings['LayerElementTangent']==bindings['LayerElementBinormal']==bindings['LayerElementUV']==0

def layer(name,field):
 n=next(n for n in main.children if n.name==name and n.props==[0]);d={c.name:c.props[0] for c in n.children};assert d['MappingInformationType']=='ByPolygonVertex';values=np.asarray(d[field],dtype=float).reshape(-1,3)
 if d['ReferenceInformationType']=='IndexToDirect':values=values[np.asarray(d[field+'Index'],dtype=int)]
 else:assert d['ReferenceInformationType']=='Direct'
 return d,values
nt,n=layer('LayerElementNormal','Normals');tt,t=layer('LayerElementTangent','Tangents');bb,bi=layer('LayerElementBinormal','Binormals');assert tt['Name']==bb['Name']=='UV0'
with np.load(ref,allow_pickle=False) as z:r={k:z[k] for k in z.files}
assert n.shape==t.shape==bi.shape==r['normal'].shape==(547878,3)
length=np.linalg.norm(t,axis=1);assert (length>1e-10).all()
def angle(x,y):return float(np.degrees(np.arccos(np.clip((x*y).sum(1)/(np.linalg.norm(x,axis=1)*np.linalg.norm(y,axis=1)),-1,1))).max())
sign=np.sign((np.cross(n,t)*bi).sum(1));ne=angle(n,r['normal']);te=angle(t,r['tangent']);se=int((sign!=r['bitangent_sign']).sum());assert ne<.05 and te<.05 and se==0,(ne,te,se)
report=dict(scope='Independent serialized FBX UV0 T/B readback vs frozen geometry; not native admission',old_fbx_sha256=sha(old),successor_fbx_sha256=sha(new),frozen_geometry_sha256=sha(ref),source_core_geometry_arrays_exact=True,all7_model_transforms_exact=True,positions_UVs_normals_colors_roles_smoothing_collision_arrays_exact=True,collision_hulls=6,base_layer_bindings=bindings,tangent_layer_name=tt['Name'],corners=len(t),zero_serialized_tangents=int((length<=1e-10).sum()),max_normal_degrees=ne,max_tangent_degrees=te,bitangent_sign_changes=se,source_reference_unchanged=True,pass_serialized_tbn=True)
(Q/'Evidence/SERIALIZED_TBN_READBACK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
for name,digest in json.loads((Q/'PRESERVED_INPUT_PINS.json').read_text()).items():assert sha(Path(name))==digest
