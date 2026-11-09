from pathlib import Path
import bpy,json,hashlib,sys,os,collections,math
from mathutils import Vector
sys.dont_write_bytecode=True;O=Path(__file__).resolve().parent;source=O/'SharedGroundGameV2.blend';pin=hashlib.sha256(source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source));sys.path.insert(0,str(O/'Tools'));from dinkasset import fbxparse
manifest=json.loads((O/'ExportV2/manifest.json').read_text());prep=json.loads((O/'asset_preparation_v2.json').read_text());terrain={r['asset']:r for r in prep['terrain_assets']};reeds={r['asset']:r for r in prep['reed_clusters']};rows=[];perlod=[]
def canonical(points,uvs,normals):
 keys=[tuple(tuple(round(x,6)for x in points[(j+i)%3])for i in range(3))for j in range(3)];j=min(range(3),key=lambda i:keys[i]);return keys[j],[uvs[(j+i)%3]for i in range(3)],[normals[(j+i)%3]for i in range(3)]
def prove(path,names):
 version,nodes=fbxparse.parse(str(path));by={n.name:n for n in nodes};objects=by['Objects'].children;modelid={n.props[0]:n.props[1].split('\x00')[0]for n in objects if n.name=='Model'and n.props[2]=='Mesh'};geomof={c.props[1]:modelid[c.props[2]]for c in by['Connections'].children if c.name=='C'and len(c.props)>=3 and c.props[0]=='OO'and c.props[2]in modelid};results=[]
 for geom in [n for n in objects if n.name=='Geometry']:
  name=geomof[geom.props[0]];assert name in names;ob=bpy.data.objects[name];me=ob.data;me.calc_loop_triangles();expected=collections.defaultdict(list);tag=me.attributes.get('SourceSurface')
  for tri in me.loop_triangles:
   ps=[tuple(me.vertices[i].co)for i in tri.vertices];uvs=[tuple(me.uv_layers.active.data[li].uv)for li in tri.loops];ns=[tuple(me.corner_normals[li].vector)for li in tri.loops];key,u,n=canonical(ps,uvs,ns);expected[key].append((u,n,me.polygons[tri.polygon_index].material_index,tag.data[tri.polygon_index].value if tag else -1))
  vv=geom.first('Vertices').props[0];verts=[vv[i:i+3]for i in range(0,len(vv),3)];polys=[];cur=[]
  for x in geom.first('PolygonVertexIndex').props[0]:
   cur.append(x if x>=0 else -x-1)
   if x<0:polys.append(cur);cur=[]
  assert all(len(p)==3 for p in polys);nl=geom.first('LayerElementNormal');nn=nl.first('Normals').props[0];normals=[nn[i:i+3]for i in range(0,len(nn),3)];nr=nl.first('ReferenceInformationType').props[0];assert nl.first('MappingInformationType').props[0]=='ByPolygonVertex'
  if nr=='IndexToDirect':normals=[normals[i]for i in nl.first('NormalsIndex').props[0]]
  else:assert nr=='Direct'
  ul=geom.first('LayerElementUV');uu=ul.first('UV').props[0];uvs=[uu[i:i+2]for i in range(0,len(uu),2)];ui=ul.first('UVIndex').props[0];ml=geom.first('LayerElementMaterial');mats=ml.first('Materials').props[0]
  if ml.first('MappingInformationType').props[0]=='AllSame':mats=mats*len(polys)
  assert len(ui)==len(polys)*3 and len(mats)==len(polys);maxuv=0;maxn=0;mindot=1;top=0;bottom=0;top_minz=1;bottom_maxz=-1
  for fi,poly in enumerate(polys):
   ps=[verts[i]for i in poly];u=[uvs[ui[fi*3+j]]for j in range(3)];n=normals[fi*3:fi*3+3];key,cu,cn=canonical(ps,u,n);assert expected[key],(path,name,fi,'oriented triangle missing');index=min(range(len(expected[key])),key=lambda k:sum(abs(cu[i][j]-expected[key][k][0][i][j])for i in range(3)for j in range(2)));eu,en,mat,kind=expected[key].pop(index);assert mat==mats[fi];maxuv=max(maxuv,max(abs(cu[i][j]-eu[i][j])for i in range(3)for j in range(2)));maxn=max(maxn,max(abs(cn[i][j]-en[i][j])for i in range(3)for j in range(3)));cross=(Vector(ps[1])-Vector(ps[0])).cross(Vector(ps[2])-Vector(ps[0]));assert cross.length>1e-10;cross.normalize()
   for norm in n:
    norm=Vector(norm);assert all(math.isfinite(x)for x in norm)and abs(norm.length-1)<1e-5;mindot=min(mindot,cross.dot(norm))
   if kind==0:top+=1;top_minz=min(top_minz,cross.z);assert cross.z>0
   if kind==1:bottom+=1;bottom_maxz=max(bottom_maxz,cross.z);assert cross.z<0
  assert not any(expected.values());assert maxuv<1e-5 and maxn<1e-5 and mindot>.9999;results.append({'model':name,'triangles':len(polys),'oriented_source_triangle_bijection':True,'UV_max_error':maxuv,'authored_normal_max_error':maxn,'minimum_front_dot':mindot,'actual_TOP_triangles':top,'actual_BOTTOM_triangles':bottom,'TOP_min_positive_z':top_minz if top else None,'BOTTOM_max_negative_z':bottom_maxz if bottom else None})
 assert {x['model']for x in results}==set(names);s=fbxparse.inspect(str(path));assert s['unit_scale_factor']==100 and s['up_axis']==[2,1]and s['front_axis']==[1,-1]
 for m in s['models'].values():
  if m['type']=='Mesh':assert m['translation']==[0,0,0]and m['rotation']==[0,0,0]and m['scaling']==[1,1,1]
 return {'file':str(path.relative_to(O)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'unit_cm':100,'all_models_identity':True,'models':results}
for asset in manifest['assets']:
 name=asset['name'];names=[name]if name in terrain else[name+'_LOD'+str(i)for i in range(3)];rows.append(prove(O/'ExportV2'/asset['files']['fbx'],names))
# PerLOD native files for everyreedcluster, since FBXsiblings alone do not create an actualnativeLODchain.
dest=O/'ReedLOD';dest.mkdir(exist_ok=True)
for root in reeds:
 for level in range(3):
  ob=bpy.data.objects[root+'_LOD'+str(level)];old=ob.location.copy();hidden=ob.hide_get();bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob;ob.location=(0,0,0);p=dest/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(p),use_selection=True,object_types={'MESH'},use_mesh_modifiers=True,mesh_smooth_type='FACE',use_triangles=True,use_tspace=False,use_custom_props=False,colors_type='NONE',apply_unit_scale=True,global_scale=1,apply_scale_options='FBX_SCALE_ALL',axis_forward='Y',axis_up='Z',bake_space_transform=False,use_space_transform=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',embed_textures=False);ob.location=old;ob.hide_set(hidden);perlod.append(prove(p,[ob.name]))
assert hashlib.sha256(source.read_bytes()).hexdigest()==pin;assert len(rows)==142 and len(perlod)==42;assert sum(m['actual_TOP_triangles']for r in rows for m in r['models'])==3305;r={'status':'Actual142FBXassets +42separatereedLODfiles proved against real sourcevertices/UVs/normals/materialIDs','source_sha256':pin,'asset_files':rows,'reed_perLOD_files':perlod,'actual_top_triangles':3305,'actual_models':sum(len(x['models'])for x in rows),'native_imported':False,'rawterrainpolicyexceptions':'128COLLISION_MISSING+2SCALE_RANGEretained, exportforcedonlyforauthorizedterrainclasspolicy'};(O/'actual_fbx_proof_v2.json').write_text(json.dumps(r,indent=2)+'\n');print('SHAREDGROUND_ALL_FBX_PROOFS_PASS',len(rows),len(perlod),flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
