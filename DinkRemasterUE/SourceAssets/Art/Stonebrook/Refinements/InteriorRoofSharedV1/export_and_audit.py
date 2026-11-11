"""Saved candidate -> FBX payload. Independent binary decode of actual P/UV/N/T/B."""
import bpy,numpy as np,json,hashlib,gzip,os,sys
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O));import fbxparse as F
P=O/'InteriorRoof_Shared2mCandidate.blend';OUT=O/'FBX';OUT.mkdir(exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(P));s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def layer(g,name,field,index,width,count):
 n=g.first(name);assert n is not None,(g.props,name);a=n.first(field).props[0];arr=np.array(a).reshape(-1,width);mode=n.first('ReferenceInformationType').props[0]
 if mode=='IndexToDirect':arr=arr[n.first(index).props[0]]
 else:assert mode=='Direct'
 mapping=n.first('MappingInformationType').props[0]
 if mapping=='AllSame':arr=np.repeat(arr[:1],count,axis=0)
 else:assert mapping=='ByPolygonVertex',mapping
 assert len(arr)==count;return arr
def snapshot(o,basis=False):
 m=o.data;r=dict(p=np.array([v.co[:]for v in m.vertices]),poly=[list(p.vertices)for p in m.polygons])
 if basis:
  m.calc_tangents(uvmap=m.uv_layers.active.name);n=np.array([n.vector[:]for n in m.corner_normals]);t=np.array([l.tangent[:]for l in m.loops]);sign=np.array([l.bitangent_sign for l in m.loops]);r.update(uv=np.array([u.uv[:]for u in m.uv_layers.active.data]),n=n,t=t,b=np.cross(n,t)*sign[:,None],sign=sign,matnames=[m.name for m in m.materials],matindices=[p.material_index for p in m.polygons])
 return r
def angle(a,b):
 aa=np.linalg.norm(a,axis=1);bb=np.linalg.norm(b,axis=1);assert min(aa)>1e-5 and min(bb)>1e-5
 return np.percentile(np.degrees(np.arccos(np.clip(np.sum(a*b,axis=1)/(aa*bb),-1,1))),[50,95,100]).tolist()
proposal=json.loads((O/'Proofs/OriginalUCXProposal.json').read_text());rows=[];manifest=[];allraw={};originalsource=sha(P)
for spec in proposal['packet_files']:
 name=spec['source_object']
 if not name.startswith('SM_IndoorRoof'):continue
 original=bpy.data.objects[name];hulls=[bpy.data.objects[n]for n in spec['source_inventory']['UCX_names']];copies=[];renamed=[];data=[];refs={}
 try:
  bpy.ops.object.select_all(action='DESELECT')
  for ob in [original]+hulls:
   refs[ob.name]=snapshot(ob,ob==original);desired=ob.name;ob.name='__REFERENCE_'+desired;renamed.append((ob,desired));dup=ob.copy();dup.data=ob.data.copy();data.append(dup.data);dup.name=desired;assert dup.name==desired;dup.location=(0,0,0);s.collection.objects.link(dup);dup.hide_viewport=False;dup.hide_select=False;dup.hide_set(False);dup.select_set(True);copies.append(dup)
  bpy.context.view_layer.objects.active=copies[0];bpy.context.view_layer.update();path=OUT/(name+'.fbx')
  bpy.ops.export_scene.fbx(filepath=str(path),check_existing=False,use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='OFF',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE',use_custom_props=False,bake_space_transform=False,use_space_transform=True)
 finally:
  for dup in copies:bpy.data.objects.remove(dup,do_unlink=True)
  for m in data:
   if m.users==0:bpy.data.meshes.remove(m)
  for ob,n in renamed:ob.name=n
 _,top=F.parse(path);top={n.name:n for n in top};settings=F._p70(top['GlobalSettings']);assert settings['UnitScaleFactor']==1.;objects={n.props[0]:n for n in top['Objects'].children};conn=top['Connections'].children;models=[n for n in objects.values()if n.name=='Model'];assert {n.props[1].split('\x00')[0]for n in models}==set(refs)
 hull_count=0
 for model in models:
  mn=model.props[1].split('\x00')[0];ref=refs[mn];props=F._p70(model);assert max(abs(x)for x in props.get('Lcl Translation',[0,0,0]))<1e-8;assert max(abs(x-100)for x in props['Lcl Scaling'])<1e-6;assert max(abs(x-y)for x,y in zip(props['Lcl Rotation'],[0,0,180]))<1e-4
  g=next(objects[c.props[1]]for c in conn if len(c.props)>2 and c.props[0]=='OO'and c.props[2]==model.props[0]and c.props[1]in objects and objects[c.props[1]].name=='Geometry');vertices=np.array(g.first('Vertices').props[0]).reshape(-1,3);polys=[];cur=[]
  for x in g.first('PolygonVertexIndex').props[0]:
   cur.append(x if x>=0 else -x-1)
   if x<0:polys.append(cur);cur=[]
  assert not cur;assert np.array_equal(vertices,ref['p']);assert polys==ref['poly']
  if mn!=name:hull_count+=1;continue
  count=len(polys)*3;uv=layer(g,'LayerElementUV','UV','UVIndex',2,count);n=layer(g,'LayerElementNormal','Normals','NormalsIndex',3,count);t=layer(g,'LayerElementTangent','Tangents','TangentsIndex',3,count);b=layer(g,'LayerElementBinormal','Binormals','BinormalsIndex',3,count)
  assert all(np.isfinite(a).all()for a in [vertices,uv,n,t,b]);hand=np.sign(np.sum(np.cross(n,t)*b,axis=1));nd=angle(n,ref['n']);td=angle(t,ref['t']);bd=angle(b,ref['b']);ud=float(abs(uv-ref['uv']).max());sign_changes=int((hand!=ref['sign']).sum())
  mats=[objects[c.props[1]].props[1].split('\x00')[0]for c in conn if len(c.props)>2 and c.props[0]=='OO'and c.props[2]==model.props[0]and c.props[1]in objects and objects[c.props[1]].name=='Material'];mi=g.first('LayerElementMaterial');ids=mi.first('Materials').props[0]
  if mi.first('MappingInformationType').props[0]=='AllSame':ids=ids*len(polys)
  expected=[ref['matnames'][i]for i in ref['matindices']];assert [mats[i]for i in ids]==expected
  row=dict(name=name,triangles=len(polys),actual_binary_fields=['positions','oriented_polygons','UV','normal','tangent','binormal'],max_UV_delta=ud,N_angle_deg_p50_p95_max=nd,T_angle_deg_p50_p95_max=td,B_angle_deg_p50_p95_max=bd,bitangent_sign_changes=sign_changes,geometry_positions_indices_exact=True,material_roles_exact=True,source_and_payload_all_finite=True,serialized_handedness_values=sorted(set(hand.tolist())),frame_pass=bool(ud<1e-6 and max(nd+td+bd)<.05 and sign_changes==0));rows.append(row)
  allraw[name]={k:v.tolist()if isinstance(v,np.ndarray)else v for k,v in dict(vertices=vertices,polys=polys,UV=uv,N=n,T=t,B=b).items()}
 manifest.append(dict(name=name,file='FBX/'+path.name,sha256=sha(path),triangles=len(refs[name]['poly']),UCX=hull_count));print('BINARY_FRAME',json.dumps(rows[-1]),flush=True)
 assert hull_count==len(hulls)
assert len(rows)==8 and all(r['frame_pass']for r in rows);assert sha(P)==originalsource
(O/'BINARY_FBX_FRAME_REPORT.json').write_text(json.dumps(dict(passed=True,scope='Independent actual binary FBX decoding vs saved Blender corner fields. T/B serialized with use_tspace=True, not inferred from normals or borrowed CPU signs. Header cm/model100/Rz180 explicit. Native engine interpretation not run.',source_sha256=originalsource,parser_sha256=sha(O/'fbxparse.py'),rows=rows),indent=2)+'\n')
(O/'export_manifest.json').write_text(json.dumps(dict(status='SOURCE_ONLY_ROOT_REVIEW_PENDING',source='InteriorRoof_Shared2mCandidate.blend',source_sha256=originalsource,FBX=manifest,render_triangles=sum(r['triangles']for r in manifest),UCX=sum(r['UCX']for r in manifest),textures='../../../SharedMaterials/manifest.json',native_run=False),indent=2)+'\n')
(O/'ACTUAL_BINARY_FBX_CORNERS.json.gz').write_bytes(gzip.compress(json.dumps(allraw,separators=(',',':')).encode(),mtime=0));sys.stdout.flush();os._exit(0)
