"""Actual FBX importer readback; raw binary proof remains a separate gate."""
import bpy,json,gzip,hashlib,math,collections,sys
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
D=Path(__file__).resolve().parents[1];source=json.load(gzip.open(D/'Export/source_geometry_capture.json.gz','rt'));exp=json.loads((D/'Export/export_receipt.json').read_text());rows=[]
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(a,b))/(sum(x*x for x in a)*sum(x*x for x in b))**.5))))
def key(ids,mat):return min(tuple(ids[i:]+ids[:i])for i in range(3)),mat
for entry in exp['FBX']:
 file=D/'Export'/entry['path'];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(file),use_custom_normals=True,automatic_bone_orientation=False,ignore_leaf_bones=False,use_anim=False);arm=next(o for o in bpy.data.objects if o.type=='ARMATURE');assert len(arm.data.bones)==89 and set(arm.data.bones.keys())==set(source['bones89']);jerr=0.;axiserr=0.
 for b in arm.data.bones:
  expected=source['bones89'][b.name];assert(b.parent.name if b.parent else None)==expected['parent'];world=arm.matrix_world@b.matrix_local;jerr=max(jerr,max(abs(world[r][3]-expected['matrix_world_m'][r][3])for r in range(3)))
  for c in range(3):
   aa=Vector([world[r][c]for r in range(3)]).normalized();bb=Vector([expected['matrix_world_m'][r][c]for r in range(3)]).normalized();axiserr=max(axiserr,max(abs(x-y)for x,y in zip(aa,bb)))
 assert jerr<1e-5 and axiserr<2e-5,(entry['role'],'Rig',jerr,axiserr);meshes=[o for o in bpy.data.objects if o.type=='MESH'];assert set(o.name for o in meshes)==set(entry['mesh_names']);mr=[]
 for ob in meshes:
  name=ob.name;a=source['meshes'][name];m=ob.data;m.calc_loop_triangles();assert len(m.loop_triangles)==len(a['triangles']);assert set(u.name for u in m.uv_layers)==set(a['triangles'][0]['UV']);kd=KDTree(len(a['positions_m']))
  for i,p in enumerate(a['positions_m']):kd.insert(p,i)
  kd.balance()
  def canon(p):
   q,i,d=kd.find(p);assert d<1e-5,(name,'Position',d);return min(j for v,j,dist in kd.find_range(q,2e-6)),d
  ca=[canon(Vector(p))[0]for p in a['positions_m']];cb=[];pe=0.
  for v in m.vertices:i,d=canon(ob.matrix_world@v.co);cb.append(i);pe=max(pe,d)
  bucket=collections.defaultdict(list)
  for t in a['triangles']:bucket[key([ca[i]for i in t['vertices']],t['material'])].append(t)
  ww=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}for v in m.vertices];uvmax={u.name:0. for u in m.uv_layers};wmax=0.;nmax=0.;matched=0;normalmat=ob.matrix_world.to_3x3().inverted().transposed()
  for t in m.loop_triangles:
   ids=[cb[i]for i in t.vertices];mat=m.materials[t.material_index].name;candidates=bucket[key(ids,mat)];found=None
   for q in candidates:
    qi=[ca[i]for i in q['vertices']]
    for shift in range(3):
     if qi[shift:]+qi[:shift]!=ids:continue
     order=[(j+shift)%3 for j in range(3)];ue={u.name:max(abs(x-y)for j,l in enumerate(t.loops)for x,y in zip(u.data[l].uv,q['UV'][u.name][order[j]]))for u in m.uv_layers};we=max(abs(ww[t.vertices[j]].get(b,0)-a['weights'][q['vertices'][order[j]]].get(b,0))for j in range(3)for b in ww[t.vertices[j]].keys()|a['weights'][q['vertices'][order[j]]].keys())
     if max(ue.values())<1e-5 and we<1e-5:found=(q,order,ue,we);break
    if found:break
   assert found,(name,'OrientedTriangleMaterialUVNamedWeights');q,order,ue,we=found;candidates.remove(q);matched+=1;wmax=max(wmax,we)
   for u,v in ue.items():uvmax[u]=max(uvmax[u],v)
   for j,l in enumerate(t.loops):nmax=max(nmax,angle((normalmat@m.corner_normals[l].vector).normalized(),q['normals'][order[j]]))
  assert all(not q for q in bucket.values());assert all(len(w)<=4 and abs(sum(w.values())-1)<1e-4 for w in ww);mr.append({'mesh':name,'oriented_triangles_material_UV_allchannels_namedweights_matched':matched,'source_vertices':len(a['positions_m']),'imported_vertices':len(m.vertices),'position_max_error_m':pe,'UV_component_max_error':uvmax,'named_weight_max_error':wmax,'Blender_reencoded_corner_normal_max_angle_degrees':nmax,'max_influences':max(map(len,ww))})
 rows.append({'file':entry['path'],'actual_imported_bone_count':89,'bone_names_parents_exact':True,'world_joint_center_max_error_m':jerr,'normalized_rest_axis_component_max_error':axiserr,'armature_object_scale':list(arm.scale),'meshes':mr});print('ACTUAL_IMPORT_PASS',entry['role'],jerr,axiserr,flush=True)
result={'status':'ACTUAL_BLENDER_FBX_IMPORT_GEOMETRY_SKIN_ALLUV89_PASS_NORMALS_MEASURED','scope':'Separate importer observation, not native UE/built tangents/normal render or shared161Skeleton acceptance. Blender cm importer retains.01Armature scale, compare physical joints and normalized axes rather than claiming source basis magnitudes exact. Last-bone tail display length is an importer convention, original source tail lengths remain pinned separately.','source_sha256':source['source_sha256'],'FBX':rows,'normal_qualification':'Source/raw binary normal gate is separate. Blender importer re-encodes fans and may show larger angles; do not claim universal normal roundtrip PASS.'}
args=sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[];assert '--report'in args;report=Path(args[args.index('--report')+1]).resolve()
if(D/'SHA256SUMS.json').exists():assert not report.is_relative_to(D),'Frozen packet report must be outside'
report.write_text(json.dumps(result,indent=2)+'\n')
