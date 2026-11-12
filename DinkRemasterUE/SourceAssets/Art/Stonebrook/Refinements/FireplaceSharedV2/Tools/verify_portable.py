"""Reopen relocated packed sources and independently decode target FBX buffers.
Run with Blender --python Tools/verify_portable.py -- --project-root ROOT --out JSON.
Does not save scenes, render, run Unreal, or change source/FBX resources.
"""
import bpy,json,hashlib,struct,sys,argparse,math,os
from pathlib import Path
import numpy as np
D=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(D/'Tools'));from graph_fingerprint import graph
import fbxparse as F
p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--replay-library',type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);P=a.project_root;L=P/'SourceAssets/Art/SharedMaterials';source=D/'Fireplace_SharedContractV2.blend';original=P/'SourceAssets/Art/Stonebrook/Refinements/RoofChimneyV12d/ExportV12d_Run01/Source/RoofChimney_ArtistRepair_v12d.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(value):return json.loads(json.dumps(value))
def scene(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));r={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  m=o.data;r[o.name]=dict(p=[tuple(v.co)for v in m.vertices],edges=[tuple(e.vertices)for e in m.edges],faces=[tuple(p.vertices)for p in m.polygons],normals=[tuple(v.vector)for v in m.corner_normals],smooth=[p.use_smooth for p in m.polygons],matrix=[tuple(x)for x in o.matrix_world],mods=[(x.name,x.type,x.show_render,x.show_viewport)for x in o.modifiers])
  if not o.name.startswith(('SM_Chimney','SM_Fireplace')):r[o.name].update(uv=[[tuple(q.uv)for q in u.data]for u in m.uv_layers],materials=[x.name if x else None for x in m.materials])
 return r
before=scene(original);after=scene(source);assert before==after
expected=json.load(open(D/'Evidence/V2/SHARED_CONTRACT.json'))['graphs'];sourcegraphs={n:canonical(graph(bpy.data.materials[n]))for n in expected};assert sourcegraphs==expected
roles=['MI_Shared_LimeMortar2m','MI_Shared_Soot2m','MI_Shared_FieldstoneCoursed2m'];mineralgraphs={n:canonical(graph(bpy.data.materials[n]))for n in roles}
# Active target dependencies packed, not author-path lookups.
images={}
for o in bpy.data.objects:
 if o.type=='MESH'and o.name.startswith(('SM_Fireplace','SM_Chimney')):
  for mat in o.data.materials:
   for n in mat.node_tree.nodes:
    if n.type=='TEX_IMAGE':assert n.image and n.image.packed_file;images[n.image.name]=dict(size=list(n.image.size),packed_sha256=hashlib.sha256(n.image.packed_file.data).hexdigest())
def layer(node,field,width,count):
 data=np.array(node.first(field).props[0]).reshape(-1,width)
 if node.first('ReferenceInformationType').props[0]=='IndexToDirect':data=data[node.first(field+'Index').props[0]]
 if node.first('MappingInformationType').props[0]=='AllSame':data=np.repeat(data[:1],count,axis=0)
 assert len(data)==count;return data
fbxrows=[]
for path in sorted((D/'FBX').glob('*.fbx')):
 o=bpy.data.objects[path.stem];m=o.data;m.calc_tangents(uvmap='UV0');_,nodes=F.parse(path);top={n.name:n for n in nodes};objects={n.props[0]:n for n in top['Objects'].children};model=next(n for n in objects.values()if n.name=='Model'and n.props[1].split('\x00')[0]==o.name);g=next(objects[c.props[1]]for c in top['Connections'].children if len(c.props)>2 and c.props[0]=='OO'and c.props[2]==model.props[0]and c.props[1]in objects and objects[c.props[1]].name=='Geometry');count=len(m.loops)
 pos=np.array(g.first('Vertices').props[0]).reshape(-1,3);assert np.array_equal(pos,np.array([tuple(v.co)for v in m.vertices]));uv_errors={}
 for i,name in enumerate(['UV0','UV1_SharedData','UVMap']):
  node=next(x for x in g.children if x.name=='LayerElementUV'and x.props[0]==i);data=layer(node,'UV',2,count);ref=np.array([tuple(q.uv)for q in m.uv_layers[name].data]);uv_errors[name]=float(abs(data-ref).max());assert uv_errors[name]==0
 color=layer(g.first('LayerElementColor'),'Colors',4,count)if g.first('LayerElementColor').first('ReferenceInformationType').props[0]=='Direct'else None
 if color is None:
  node=g.first('LayerElementColor');color=np.array(node.first('Colors').props[0]).reshape(-1,4)[node.first('ColorIndex').props[0]]
 cref=np.array([tuple(c.color)for c in m.color_attributes['SharedSurfaceData'].data]);cerr=float(abs(color-cref).max());assert cerr==0
 n=layer(g.first('LayerElementNormal'),'Normals',3,count);t=layer(g.first('LayerElementTangent'),'Tangents',3,count);b=layer(g.first('LayerElementBinormal'),'Binormals',3,count);rn=np.array([tuple(x.vector)for x in m.corner_normals]);rt=np.array([tuple(x.tangent)for x in m.loops]);rs=np.array([x.bitangent_sign for x in m.loops]);rb=np.cross(rn,rt)*rs[:,None];errors={}
 for name,data,ref in [('N',n,rn),('T',t,rt),('B',b,rb)]:
  assert np.isfinite(data).all();valid=np.linalg.norm(ref,axis=1)>1e-8;assert np.array_equal(~valid,np.linalg.norm(data,axis=1)<1e-8);errors[name]=float(np.degrees(np.arccos(np.clip(np.sum(data[valid]*ref[valid],axis=1)/(np.linalg.norm(data[valid],axis=1)*np.linalg.norm(ref[valid],axis=1)),-1,1))).max());assert errors[name]<.05
 zero=np.flatnonzero(np.linalg.norm(t,axis=1)<1e-8).tolist();assert zero==([3003,3007,3148,3238,3252]if'Chimney'in o.name else[])
 fbxrows.append(dict(name=o.name,positions_exact=True,UV_errors=uv_errors,RGBA_error=cerr,valid_frame_max_angles=errors,retained_zero_TB_corners=zero,sha256=sha(path)))
# Read actual current shared libraries in this checkout, not author files.
checks={}
for path,names in [(L/'ArchitecturalSurfaces2mV1/SharedArchitecturalSurfaces_Source.blend',['MI_Shared_FieldstoneSeed2m','MI_Shared_IronLead2m']),(L/'OakLime2mV1/Shared2m_LibraryCandidate.blend',['MI_Shared_OakLonggrain2m']),(L/'MineralMasonry2mV1/SharedMineralMasonry_Source.blend',roles)]:
 bpy.ops.wm.open_mainfile(filepath=str(path))
 for name in names:checks[name]=canonical(graph(bpy.data.materials[name]))==(mineralgraphs[name]if name in roles else expected[name]);assert checks[name]
if a.replay_library:
 bpy.ops.wm.open_mainfile(filepath=str(a.replay_library))
 for name in roles:assert canonical(graph(bpy.data.materials[name]))==mineralgraphs[name]
# Full generic reuse reopens with the same packed graph contracts.
bpy.ops.wm.open_mainfile(filepath=str(D/'SharedContract_LibraryReuse2m4m.blend'))
assert len([o for o in bpy.data.objects if o.type=='MESH'])==14
for name,want in {**expected,**mineralgraphs}.items():assert canonical(graph(bpy.data.materials[name]))==want
report=dict(status='PASS_SOURCE_WITH_RETAINED_ZERO_FRAME_QUALIFICATION',scope='Relocated local-source read-only Blender5.2.2+actualbinaryFBX; noUE/native/game',objects_exact=len(before),UCX_exact=sum(n.startswith('UCX_')for n in before),roof8_exact=sum(n.startswith('SM_IndoorRoof')for n in before),shared_graphs_exact=checks,active_packed_images=images,FBX=fbxrows,source_sha256=sha(source),generic_reuse_graphs_exact=True,replayed_generic_library_exact=bool(a.replay_library),original_sha256=sha(original))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print('PORTABLE_PASS',flush=True)

os._exit(0)
