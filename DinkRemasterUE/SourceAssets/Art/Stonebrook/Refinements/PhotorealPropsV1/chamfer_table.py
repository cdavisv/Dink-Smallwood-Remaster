import bpy,bmesh,math,json,random,os,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'PhotorealPropsV1.blend'));name='SM_Table_Oak_01';ob=bpy.data.objects[name];me=ob.data
# Flush breadboard dowels move inboard before the broad original-art corner cuts.
adj=[set()for _ in me.vertices]
for e in me.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
unseen=set(range(len(me.vertices)))
while unseen:
 stack=[unseen.pop()];ids=[]
 while stack:
  i=stack.pop();ids.append(i)
  for j in adj[i]:
   if j in unseen:unseen.remove(j);stack.append(j)
 lo=[min(me.vertices[i].co[k]for i in ids)for k in range(3)];hi=[max(me.vertices[i].co[k]for i in ids)for k in range(3)];center=[(lo[k]+hi[k])/2 for k in range(3)]
 if lo[2]>.89 and hi[0]-lo[0]<.04 and hi[1]-lo[1]<.04 and abs(center[1])>.55:
  for i in ids:me.vertices[i].co.y-=math.copysign(.12,center[1])
cut=1.325+.749-.22
for obj in [ob]+[o for o in bpy.data.collections[name].objects if o.name.startswith('UCX_')]:
 bm=bmesh.new();bm.from_mesh(obj.data)
 for sx,sy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
  normal=Vector((sx,sy,0));result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=normal*(cut/2),plane_no=normal,clear_outer=True,clear_inner=False)
  edges=[e for e in result['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_boundary]
  if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
# Recompute grain attributes for all clipped connected timber solids, including new end faces.
adj=[set()for _ in me.vertices]
for e in me.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
unseen=set(range(len(me.vertices)));rng=random.Random(72026)
while unseen:
 stack=[unseen.pop()];ids=set()
 while stack:
  i=stack.pop();ids.add(i)
  for j in adj[i]:
   if j in unseen:unseen.remove(j);stack.append(j)
 lo=[min(me.vertices[i].co[k]for i in ids)for k in range(3)];hi=[max(me.vertices[i].co[k]for i in ids)for k in range(3)];dims=[hi[k]-lo[k]for k in range(3)];axis=max(range(3),key=lambda k:dims[k])
 if dims[0]<.05 and dims[1]<.05 and dims[2]<.02:axis=2
 other=[k for k in range(3)if k!=axis];seed=rng.random()
 for p in me.polygons:
  if p.vertices[0]not in ids:continue
  across=min(other,key=lambda k:abs(p.normal[k]));mask=max(0,min(1,(abs(p.normal[axis])-.72)/.23))
  for l in p.loop_indices:
   v=me.vertices[me.loops[l].vertex_index].co;cross=v[across]-lo[across];along=v[axis]-lo[axis]
   for attr,val in [('OakFurniturePhoto',(cross+.16*seed,along/2+.17*seed,seed)),('OakFurniturePhysical',(cross,along,seed)),('OakFurnitureEnd',(v[other[0]]-(lo[other[0]]+hi[other[0]])/2+.023,v[other[1]]-(lo[other[1]]+hi[other[1]])/2+.011,0))]:me.attributes[attr].data[l].vector=val
   me.attributes['OakFurnitureEndMask'].data[l].value=mask
bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008,area_weight=.2);bpy.ops.object.mode_set(mode='OBJECT')
r=json.loads((O/'geometry_report.json').read_text());a=r['assets'][name];a['candidate_vertices']=len(me.vertices);a['candidate_triangles']=sum(len(p.vertices)-2 for p in me.polygons);a['corner_chamfer_m']=.22;a['candidate_bounds_m']=[[min(v.co[k]for v in me.vertices)for k in range(3)],[max(v.co[k]for v in me.vertices)for k in range(3)]];r['final_review_corrections'].append('Original87_09 broad22cm tabletop/breadboard chamfers with clipped matching convex hulls and inboard dowels');(O/'geometry_report.json').write_text(json.dumps(r,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PhotorealPropsV1.blend'));print('TABLE_CHAMFERED',a['candidate_triangles'],flush=True);sys.stdout.flush();sys.stderr.flush();os._exit(0)
