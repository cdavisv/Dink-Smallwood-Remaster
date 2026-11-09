"""Portable read-only Blender/source/FBX audit. Reports outside the frozen bundle only."""
from pathlib import Path
import argparse,sys,os,json,hashlib,collections,math,importlib.util,tempfile
sys.dont_write_bytecode=True
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--report');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[]);B=Path(args.bundle).resolve();handoff=json.loads((B/'HANDOFF.json').read_text())
 for rel,sha in handoff['files_sha256'].items():
  f=B/rel;assert f.is_file()and not f.is_symlink()and f.resolve().is_relative_to(B),rel;assert hashlib.sha256(f.read_bytes()).hexdigest()==sha,rel
 source=B/handoff['source_file'];fbx=B/handoff['FBX_file'];bpy.ops.wm.open_mainfile(filepath=str(source));ob=bpy.data.objects['SM_Shared_House440_01'];me=ob.data;assert sum(o.type=='MESH'for o in bpy.context.scene.objects)==1;assert len(me.uv_layers)==1;assert all(abs(v-1)<1e-8 for v in ob.scale);assert all(abs(v)<1e-8 for v in ob.rotation_euler);me.calc_loop_triangles();assert len(me.loop_triangles)==114354
 bm=bmesh.new();bm.from_mesh(me);assert all(e.is_manifold for e in bm.edges);assert all(f.calc_area()>=1e-8 for f in bm.faces);bm.free();uv=me.uv_layers.active;degenerate=0
 for t in me.loop_triangles:
  a,b,c=[uv.data[i].uv for i in t.loops];assert all(math.isfinite(v)for q in[a,b,c]for v in q);area=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5;degenerate+=area<1e-10
 assert degenerate==0
 materials=[];images={}
 for mat in me.materials:
  bs=next(n for n in mat.node_tree.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled');normal=next(n for n in mat.node_tree.nodes if n.bl_idname=='ShaderNodeNormalMap');assert abs(normal.inputs['Strength'].default_value-1)<1e-8;entry={'name':mat.name,'IOR':bs.inputs['IOR'].default_value,'specular_IOR_level':bs.inputs['Specular IOR Level'].default_value,'transmission':bs.inputs['Transmission Weight'].default_value,'normal_strength':1}
  assert abs(entry['IOR']-1.5)<1e-8 and entry['transmission']==0
  for node in mat.node_tree.nodes:
   if node.bl_idname!='ShaderNodeTexImage' or not node.image:continue
   im=node.image;assert im.packed_file and im.filepath.startswith('//Textures/'),(im.name,im.filepath);role=im.name.rsplit('_',1)[-1];assert im.colorspace_settings.name==('sRGB'if role=='BC'else'Non-Color');images[im.name]={'role':role,'size':list(im.size),'packed':True,'colorspace':im.colorspace_settings.name,'file':im.filepath}
  materials.append(entry)
 assert len(materials)==5 and len(images)==15
 parser_path=B/'Tools/dinkasset/fbxparse.py';spec=importlib.util.spec_from_file_location('payload_fbxparse',parser_path);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser);meta=parser.inspect(str(fbx));assert meta['unit_scale_factor']==100;models=[x for x in meta['models'].values()if x['type']=='Mesh'];assert len(models)==1;model=models[0];assert model['translation']==[0,0,0]and model['rotation']==[0,0,0]and model['scaling']==[1,1,1];_,nodes=parser.parse(str(fbx));objects=next(n for n in nodes if n.name=='Objects');g=next(n for n in objects.children if n.name=='Geometry');raw=g.first('Vertices').props[0];verts=[tuple(raw[i:i+3])for i in range(0,len(raw),3)];polys=[];cur=[]
 for i in g.first('PolygonVertexIndex').props[0]:
  cur.append(i if i>=0 else-i-1)
  if i<0:polys.append(cur);cur=[]
 assert not cur and all(len(t)==3 for t in polys);un=g.first('LayerElementUV');ud=un.first('UV').props[0];ud=[tuple(ud[i:i+2])for i in range(0,len(ud),2)];uvals=[ud[i]for i in un.first('UVIndex').props[0]];mids=g.first('LayerElementMaterial').first('Materials').props[0]
 def key(ps,ts,mid):
  co=[tuple(round(float(x),6)for x in p)+tuple(round(float(x),5)for x in t)for p,t in zip(ps,ts)];return(mid,min(tuple(co[i:]+co[:i])for i in range(3)))
 expected=collections.Counter(key([me.vertices[i].co for i in t.vertices],[uv.data[i].uv for i in t.loops],t.material_index)for t in me.loop_triangles);actual=collections.Counter(key([verts[j]for j in t],uvals[i*3:i*3+3],mids[i])for i,t in enumerate(polys));assert expected==actual
 norm=g.first('LayerElementNormal');nd=norm.first('Normals').props[0];nd=[tuple(nd[i:i+3])for i in range(0,len(nd),3)];ni=norm.first('NormalsIndex');normals=[nd[i]for i in ni.props[0]]if ni else nd;mindot=1
 for i,t in enumerate(polys):
  a,b,c=[Vector(verts[j])for j in t];front=(b-a).cross(c-a).normalized()
  for raw in normals[i*3:i*3+3]:
   n=Vector(raw);assert all(math.isfinite(v)for v in n)and .999<n.length<1.001;mindot=min(mindot,front.dot(n))
 # Compare actual exported authored corner normals numerically, not just their unit length.
 def normalkey(ps,ts,ns,mid):
  co=[tuple(round(float(x),6)for x in p)+tuple(round(float(x),5)for x in t)for p,t in zip(ps,ts)];index=min(range(3),key=lambda j:tuple(co[j:]+co[:j]));return(mid,tuple(co[index:]+co[:index])),tuple(tuple(map(float,n))for n in(ns[index:]+ns[:index]))
 source_normals=collections.defaultdict(list);actual_normals=collections.defaultdict(list)
 for t in me.loop_triangles:
  k,n=normalkey([me.vertices[i].co for i in t.vertices],[uv.data[i].uv for i in t.loops],[me.corner_normals[i].vector for i in t.loops],t.material_index);source_normals[k].append(n)
 for i,t in enumerate(polys):
  k,n=normalkey([verts[j]for j in t],uvals[i*3:i*3+3],normals[i*3:i*3+3],mids[i]);actual_normals[k].append(n)
 max_authored_normal_difference=0
 for k,entries in source_normals.items():
  assert len(entries)==len(actual_normals[k])
  for e,a in zip(sorted(entries),sorted(actual_normals[k])):max_authored_normal_difference=max(max_authored_normal_difference,max(abs(x-y)for p,q in zip(e,a)for x,y in zip(p,q)))
 assert max_authored_normal_difference<1e-5
 assert mindot>0
 body=BVHTree.FromPolygons([v.co for v in me.vertices],[list(p.vertices)for p in me.polygons]);door=Vector(handoff['placement']['door_local_game_m']);rays=[body.ray_cast(door+Vector((x,-1,z)),Vector((0,1,0)),1.5)[0]is None for x in[-.8,-.4,0,.4,.8]for z in[.4,1.3,2.25]];assert all(rays)
 # Independent relocated copy with deliberately nonexistent external paths; never save caller source.
 with tempfile.TemporaryDirectory(prefix='dink-house-packed-')as directory:
  for im in bpy.data.images:
   if im.source=='FILE':im.filepath='//MISSING_INPUTS/'+im.name
  relocated=Path(directory)/'Packed.blend';bpy.ops.wm.save_as_mainfile(filepath=str(relocated));bpy.ops.wm.open_mainfile(filepath=str(relocated));assert all(im.packed_file and len(im.pixels)>0 for im in bpy.data.images if im.source=='FILE')
 for rel,sha in handoff['files_sha256'].items():assert hashlib.sha256((B/rel).read_bytes()).hexdigest()==sha,rel
 report={'status':'PASS read-only portable source/actualFBX proof; NOT native/game acceptance','triangles':114354,'geometry_oriented_UV_material_missing':0,'extra':0,'UV_layers':1,'UV_degenerate':0,'UV_policy':'Intentional shared physical tiles, not unique/no-overlap','front_normal_min_dot':mindot,'maximum_actual_authored_corner_normal_difference':max_authored_normal_difference,'door_clear':sum(rays),'door_samples':len(rays),'materials':materials,'images':images,'packed_missing_path_reopen':True,'input_hashes_retained':True}
 if args.report:
  out=Path(args.report).resolve();assert not out.is_relative_to(B),'Report must be outside frozen source bundle';out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items()if k not in ['materials','images']}),flush=True);sys.stdout.flush();sys.stderr.flush()
if __name__=='__main__':
 code=0
 try:main()
 except BaseException:
  import traceback;traceback.print_exc();code=1
 sys.stdout.flush();sys.stderr.flush();os._exit(code)
