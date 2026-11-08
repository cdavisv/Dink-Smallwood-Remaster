import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ART=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[];reference_belt=None
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mesh=ob.data;keys={v.index:tuple(round(x,6) for x in v.co) for v in mesh.vertices};adj={};vf={}
 for p in mesh.polygons:
  if p.material_index!=4:continue
  kk=[keys[i] for i in p.vertices]
  for a,b in zip(kk,kk[1:]+kk[:1]):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
  for k in kk:vf.setdefault(k,set()).add(p.index)
 todo=set(adj);shirt=set();belt=set();jerkin=set()
 while todo:
  stack=[next(iter(todo))];comp=set()
  while stack:
   k=stack.pop()
   if k in comp:continue
   comp.add(k);stack.extend(adj[k]-comp)
  todo-=comp;lo=[min(v[i] for v in comp) for i in range(3)];hi=[max(v[i] for v in comp) for i in range(3)];fs={i for k in comp for i in vf[k]};width=hi[0]-lo[0]
  if width>.7 and .8<lo[2]<1.05 and hi[2]>1.45:shirt|=fs
  if .30<width<.35 and .98<lo[2]<1.02 and hi[2]<1.08:belt|=fs
  if width>.35 and lo[2]>.95 and hi[2]<1.45:jerkin|=fs
 assert shirt and jerkin and (belt or reference_belt),('Binding targets',lod,len(shirt),len(belt),len(jerkin))
 mesh.calc_loop_triangles();source={}
 for name,faces in [('shirt',shirt),('belt',belt)]:
  if not faces and name=='belt':source[name]=reference_belt;continue
  tris=[tuple(t.vertices) for t in mesh.loop_triangles if t.polygon_index in faces];tree=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],tris,all_triangles=True);cache={i:[(g.group,g.weight) for g in mesh.vertices[i].groups] for tri in tris for i in tri};source[name]=(tris,tree,cache,{i:mesh.vertices[i].co.copy() for tri in tris for i in tri})
 if lod==0:reference_belt=source['belt']
 changed=0;hem=0;sidecount=0
 for i in {j for p in jerkin for j in mesh.polygons[p].vertices}:
  v=mesh.vertices[i];p=v.co.copy();target=None
  if p.z<1.12:
   p.z=1.055+(p.z-1.01)*(1.12-1.055)/(1.12-1.01);target='belt';hem+=1
  elif abs(p.x)>.17 and p.z>1.27:
   amount=max(0,min(1,(abs(p.x)-.17)/.05))*max(0,min(1,(p.z-1.27)/.07));p.x-=math.copysign(.005*amount,p.x);p.z-=.015*amount;target='shirt';sidecount+=1
  if target is None:continue
  v.co=p;tris,tree,cache,coordinates=source[target];point,n,face,d=tree.find_nearest(p);tri=tris[face];a,b,c=[coordinates[j] for j in tri];factors=barycentric_transform(point,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));values={}
  for j,factor in zip(tri,factors):
   for group,w in cache[j]:values[group]=values.get(group,0)+w*max(0,factor)
  values=sorted(values.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in values)
  if total>1e-8:
   for group in ob.vertex_groups:group.remove([i])
   for group,w in values:ob.vertex_groups[group].add([i],w/total,'REPLACE')
  changed+=1
 mesh.update();rows.append({'lod':lod,'jerkin_vertices_bound_to_actual_shirt_armhole_field':sidecount,'hem_vertices_placed_above_belt_and_bound_to_belt_field':hem})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'jerkin_binding_report.json').write_text(json.dumps({'scope':'Wardrobe-only armhole binding follows the original shirt rather than torso-filtered weights; smooth lower hem placed at1.055m just above original1.052m belt and follows its exact interpolated weights. Anatomy/UV/material graphs untouched.','lods':rows},indent=2)+'\n');print('JERKIN BINDING FINISHED',rows,flush=True)
