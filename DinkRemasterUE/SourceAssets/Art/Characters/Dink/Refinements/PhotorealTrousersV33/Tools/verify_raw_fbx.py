"""Read actual binary payloads independently of Blender's FBX importer."""
import json,gzip,math,hashlib,sys,struct
from pathlib import Path
import fbxparse
D=Path(__file__).resolve().parents[1];source=json.load(gzip.open(D/'Export/source_geometry_capture.json.gz','rt'));authority=json.loads((D/'Evidence/Authority/canonical89_reference_fbx.json').read_text())['bones'];export=json.loads((D/'Export/export_receipt.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(a,b))/(sum(x*x for x in a)*sum(x*x for x in b))**.5))))
def key(ids,mat):return min(tuple(ids[i:]+ids[:i])for i in range(3)),mat
def matrix(array):return[[array[c*4+r]for c in range(4)]for r in range(4)]
def mul(a,b):return[[sum(a[r][k]*b[k][c]for k in range(4))for c in range(4)]for r in range(4)]
def values(layer,field,indexfield,width,total):
 assert layer.first('MappingInformationType').props[0]=='ByPolygonVertex';raw=layer.first(field).props[0];ix=layer.first(indexfield);ix=ix.props[0]if ix else list(range(total));assert len(ix)==total;return[raw[i*width:(i+1)*width]for i in ix]
reports=[]
for entry in export['FBX']:
 file=D/'Export'/entry['path'];version,top=fbxparse.parse(file);objs=next(n for n in top if n.name=='Objects');cons=next(n for n in top if n.name=='Connections');cs=[n.props for n in cons.children];models={n.props[0]:n for n in objs.children if n.name=='Model'};names={i:n.props[1].split('\x00')[0]for i,n in models.items()};bones={i:n for i,n in models.items()if n.props[2]=='LimbNode'};parents={a:b for kind,a,b,*_ in cs if kind=='OO'and a in models and b in models};canonical={names[i]:{'parent':names[parents[i]]if parents.get(i)in bones else None,'Properties70':[[p.props[0],p.props[1:]]for p in n.first('Properties70').children]}for i,n in bones.items()};assert canonical==authority,('Canonical89Metadata',entry['role']);assert len(bones)==89
 geo={n.props[0]:n for n in objs.children if n.name=='Geometry'};gp={a:b for kind,a,b,*_ in cs if kind=='OO'and a in geo and b in models};materials={n.props[0]:n.props[1].split('\x00')[0]for n in objs.children if n.name=='Material'};deformers={n.props[0]:n for n in objs.children if n.name=='Deformer'};rows=[]
 for gid,g in geo.items():
  name=names[gp[gid]];a=source['meshes'][name];raw=g.first('Vertices').props[0];assert len(raw)==len(a['positions_m'])*3;poserr=max(abs(raw[i*3+k]/100-p[k])for i,p in enumerate(a['positions_m'])for k in range(3));assert poserr<1e-6,(name,'Position',poserr)
  poly=g.first('PolygonVertexIndex').props[0];normals=values(g.first('LayerElementNormal'),'Normals','NormalsIndex',3,len(poly));uv={u.first('Name').props[0]:values(u,'UV','UVIndex',2,len(poly))for u in g.find('LayerElementUV')};expectedUV=set(a['triangles'][0]['UV']);assert set(uv)==expectedUV,(name,'UVLayers',list(uv),expectedUV)
  mats=[materials[x]for kind,x,y,*_ in cs if kind=='OO'and y==gp[gid]and x in materials];ml=g.first('LayerElementMaterial');mi=ml.first('Materials').props[0];mode=ml.first('MappingInformationType').props[0];assert mode in ['AllSame','ByPolygon'];bucket={}
  for t in a['triangles']:bucket.setdefault(key(t['vertices'],t['material']),[]).append(t)
  face=[];corners=[];pidx=0;maxUV={u:0. for u in uv};maxN=0.;matched=0
  for j,v in enumerate(poly):
   face.append(v if v>=0 else-v-1);corners.append(j)
   if v>=0:continue
   assert len(face)==3;mat=mats[mi[0]if mode=='AllSame'else mi[pidx]];pidx+=1;ts=bucket[key(face,mat)];assert ts,(name,'TriangleOrMaterial',face,mat);t=ts.pop();ids=t['vertices'];shift=next(i for i in range(3)if ids[i:]+ids[:i]==face)
   for k,c in enumerate(corners):
    sk=(k+shift)%3;maxN=max(maxN,angle(normals[c],t['normals'][sk]))
    for u in uv:maxUV[u]=max(maxUV[u],max(abs(x-y)for x,y in zip(uv[u][c],t['UV'][u][sk])))
   matched+=1;face=[];corners=[]
  assert matched==len(a['triangles'])and all(not x for x in bucket.values());assert max(maxUV.values())<1e-7,(name,'UV',maxUV);assert maxN<.05,(name,'RawNormalFrame',maxN)
  skins=[i for i,n in deformers.items()if n.props[2]=='Skin'and any(k=='OO'and x==i and y==gid for k,x,y,*_ in cs)];assert len(skins)==1;clusters=[i for k,i,y,*_ in cs if k=='OO'and y==skins[0]and i in deformers];weights=[{}for _ in a['weights']];linkerr=0.;axiserr=0.;binderr=0.
  for cid in clusters:
   cluster=deformers[cid];bid=next(x for k,x,y,*_ in cs if k=='OO'and y==cid and x in bones);bone=names[bid];link=matrix(cluster.first('TransformLink').props[0]);trans=matrix(cluster.first('Transform').props[0]);expected=source['bones89'][bone]['matrix_world_m'];linkerr=max(linkerr,max(abs(link[r][3]-expected[r][3]*100)for r in range(3)));axiserr=max(axiserr,max(abs(link[r][c]-expected[r][c])for r in range(3)for c in range(3)));product=mul(link,trans);binderr=max(binderr,max(abs(product[r][c]-(1 if r==c else 0))for r in range(4)for c in range(4)));indices=cluster.first('Indexes');ww=cluster.first('Weights')
   if indices:
    assert ww and len(indices.props[0])==len(ww.props[0])
    for i,w in zip(indices.props[0],ww.props[0]):
     if w>0:weights[i][bone]=w
  maxW=max(abs(weights[i].get(b,0)-a['weights'][i].get(b,0))for i in range(len(weights))for b in weights[i].keys()|a['weights'][i].keys());assert maxW<1e-6 and all(len(w)<=4 and abs(sum(w.values())-1)<1e-5 for w in weights);assert linkerr<.001 and axiserr<2e-5 and binderr<.001,(name,'BindMatrices',linkerr,axiserr,binderr)
  rows.append({'mesh':name,'controlpoints':len(weights),'oriented_triangles_materials_matched':matched,'UV_layers':list(uv),'UV_component_max_error':maxUV,'named_weight_max_error':maxW,'max_influences':max(map(len,weights)),'raw_normal_vs_source_max_angle_degrees':maxN,'source_position_max_error_m':poserr,'skin_clusters':len(clusters),'link_joint_max_error_cm':linkerr,'link_axis_component_max_error':axiserr,'link_times_transform_identity_max_error':binderr})
 assert set(x['mesh']for x in rows)==set(entry['mesh_names']);header=fbxparse.inspect(file);assert abs(header['unit_scale_factor']-1.0)<1e-6;reports.append({'file':entry['path'],'sha256':sha(file),'binary_version':version,'UnitScaleFactor_cm':header['unit_scale_factor'],'actual89_names_parents_allProperties70_exact_reference':True,'meshes':rows,'triangle_total':sum(r['oriented_triangles_materials_matched']for r in rows)});print('RAW_FBX_PASS',entry['role'],reports[-1]['triangle_total'],flush=True)
# glTF preview is geometry-only; skin/size/accessor counts inspected, not shader fidelity.
file=D/'Export'/export['GLB']['path'];blob=file.read_bytes();assert blob[:4]==b'glTF';length,kind=struct.unpack_from('<II',blob,12);g=json.loads(blob[20:20+length]);assert len(g.get('skins',[]))==1 and len(g['skins'][0]['joints'])==89 and not g.get('materials')and not g.get('animations');tri=0;uvsets=set()
for mesh in g['meshes']:
 for prim in mesh['primitives']:tri+=g['accessors'][prim['indices']]['count']//3;uvsets.update(k for k in prim['attributes']if k.startswith('TEXCOORD_'))
assert tri==20620;result={'status':'ACTUAL_RAW_FBX_GEOMETRY_SKIN_UV_BIND89_PASS_NORMALS_MEASURED','scope':'Independent binary arrays/skin clusters/metadata, not native importer or runtime acceptance. Source is metre capture, export is cm. All sourceUVs including metric UV1/2 checked, no phase correction assumed.','FBX':reports,'GLB':{'file':file.name,'joints':89,'triangles':tri,'UV_semantics':sorted(uvsets),'materials':0,'animations':0,'qualification':'Geometry-only skin preview; OSL/stitch/weave/native shading intentionally absent'}}
print(json.dumps({'status':result['status'],'FBX_files':len(reports),'GLB':result['GLB']}),flush=True)
args=sys.argv[1:]
if '--report'in args:
 path=Path(args[args.index('--report')+1]).resolve()
 if(D/'SHA256SUMS.json').exists():assert not path.is_relative_to(D),'Frozen packet report must be outside'
 path.write_text(json.dumps(result,indent=2)+'\n')
