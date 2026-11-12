import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mesh=ob.data;keys={v.index:tuple(round(x,6) for x in v.co) for v in mesh.vertices};adj={};vf={};kv={}
 for face in mesh.polygons:
  if face.material_index!=4:continue
  kk=[keys[v] for v in face.vertices]
  for a,b in zip(kk,kk[1:]+kk[:1]):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
  for v,k in zip(face.vertices,kk):vf.setdefault(k,set()).add(face.index);kv.setdefault(k,set()).add(v)
 todo=set(adj);collar=set();shirt=set()
 while todo:
  stack=[next(iter(todo))];component=set()
  while stack:
   k=stack.pop()
   if k in component:continue
   component.add(k);stack.extend(adj[k]-component)
  todo-=component;lo=[min(v[i] for v in component) for i in range(3)];hi=[max(v[i] for v in component) for i in range(3)];faces={i for k in component for i in vf[k]}
  if .30<hi[0]-lo[0]<.45 and lo[2]>1.46 and hi[2]<1.56:collar|={i for k in component for i in kv[k]}
  if hi[0]-lo[0]>.7 and .8<lo[2]<1.05 and hi[2]>1.45:shirt|=faces
 assert collar and shirt,('Collar/shirt identification',lod,len(collar),len(shirt))
 mesh.calc_loop_triangles();tris=[tuple(t.vertices) for t in mesh.loop_triangles if t.polygon_index in shirt];surface=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],tris,all_triangles=True);weightcache={i:[(g.group,g.weight) for g in mesh.vertices[i].groups] for tri in tris for i in tri};changed=0
 for i in collar:
  v=mesh.vertices[i];co=v.co.copy()
  if co.y<=.012:continue
  t=max(0,min(1,(co.z-1.492)/.039));back=max(0,min(1,(co.y-.012)/.04));back=back*back*(3-2*back)
  if t>.99:continue
  co.z-=.058*(1-t)*back;co.y+=.012*(1-t)*back;point,normal,face,dist=surface.find_nearest(co)
  if t<.10:co=co.lerp(point+normal*.003,back)
  v.co=co;tri=tris[face];a,b,c=[mesh.vertices[j].co for j in tri];factors=barycentric_transform(point,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));values={}
  for j,factor in zip(tri,factors):
   for group,w in weightcache[j]:values[group]=values.get(group,0)+w*max(0,factor)
  total=sum(values.values())
  if total>1e-8:
   old={g.group:g.weight for g in v.groups};blend=max(0,min(1,(.8-t)/.7))*back;new={g:old.get(g,0)*(1-blend)+values.get(g,0)/total*blend for g in set(old)|set(values)};new=sorted(new.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in new)
   for group in ob.vertex_groups:group.remove([i])
   for group,w in new:ob.vertex_groups[group].add([i],w/total,'REPLACE')
  changed+=1
 mesh.update();rows.append({'lod':lod,'rear_collar_vertices_fitted_to_shirt':changed})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'back_collar_report.json').write_text(json.dumps(rows,indent=2)+'\n');print('BACK COLLAR CLOSED',rows,flush=True)
