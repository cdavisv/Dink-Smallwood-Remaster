import bpy,json,math,hashlib,os,sys,traceback
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
try:
 def inspect(path,tail_count):
  bpy.ops.wm.open_mainfile(filepath=str(path));ob=bpy.data.objects['SM_FeedSack_Jute_01'];me=ob.data
  parent=list(range(len(me.vertices)))
  def find(i):
   while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
   return i
  for edge in me.edges:
   a,b=map(find,edge.vertices);parent[a]=b
  groups={}
  for v in me.vertices:groups.setdefault(find(v.index),[]).append(v.index)
  body=max(groups,key=lambda k:len(groups[k]));body_faces=[p for p in me.polygons if find(p.vertices[0])==body];triangles=[];byedge={};angles=[]
  for p in body_faces:
   for edge in p.edge_keys:byedge.setdefault(tuple(sorted(edge)),[]).append(p.index)
  for ids in byedge.values():
   if len(ids)!=2:continue
   a,b=[me.polygons[i]for i in ids];center=(a.center+b.center)/2
   if .45<center.z<.61:angles.append(math.degrees(a.normal.angle(b.normal)))
  me.calc_loop_triangles()
  for t in me.loop_triangles:
   if find(t.vertices[0])==body:triangles.append(list(t.vertices))
  bvh=BVHTree.FromPolygons([v.co for v in me.vertices],triangles,all_triangles=True)
  tails=[verts for verts in groups.values()if len(verts)==tail_count];assert len(tails)==2,len(tails)
  signed=[]
  for ids in tails:
   distances=[]
   for i in ids:
    point=me.vertices[i].co;near,normal,index,d=bvh.find_nearest(point);distances.append((point-near).dot(normal))
   signed.append({'vertices':len(ids),'min_signed_clearance_m':min(distances),'vertices_inside_body':sum(d<-.0001 for d in distances),'mean_signed_clearance_m':sum(distances)/len(distances)})
  params={m.name:{key:float(next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs[key].default_value)for key in ['IOR','Specular IOR Level']}for m in me.materials}
  return {'materials':params,'slot_count':len(me.materials),'body_vertices':len(groups[body]),'shoulder_adjacent_face_angle_p95_deg':sorted(angles)[int(.95*(len(angles)-1))],'shoulder_max_adjacent_angle_deg':max(angles),'tail_clearances':signed,'triangles':len(me.loop_triangles)}
 before=inspect(O/'Inputs/V2_Source.blend',102);after=inspect(O/'PhotorealFeedSackV1_Source.blend',126)
 assert before['materials']==after['materials']and after['slot_count']==2
 assert after['triangles']==19644 and after['triangles']<=20000
 result={'source_sha256':hashlib.sha256((O/'PhotorealFeedSackV1_Source.blend').read_bytes()).hexdigest(),'material_slots_IOR_and_specular_unchanged':True,'before':before,'after':after,'limits':['Dihedral numbers are bounded geometry measurements, not universal visual approval','Signed clearances measure original cloth body, not knot/seam contacts or universal mesh intersections','Native/query/camera acceptance pending']}
 (O/'finish_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.stdout.flush();sys.stderr.flush();os._exit(0)
except BaseException:
 traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
