import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ART=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));r=json.loads((ART/'continuous_shirt_report.json').read_text());tiles={tuple(v):i for i,v in enumerate(r['allocated_tiles'])};rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];m=ob.data;shirtfaces=[];bandfaces=[];others=[];groupnames=[g.name for g in ob.vertex_groups]
 for p in m.polygons:
  if p.material_index!=4:continue
  uv=sum((m.uv_layers[0].data[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.vertices);index=tiles.get((int(uv.y*4096)//8,int((uv.x-1)*4096)//8),-1)
  if 0<=index<r['shirt_faces']:shirtfaces.append(p)
  elif index>=r['shirt_faces']:bandfaces.append(p)
  else:others.append(p)
 def weights(i):return {g.group:g.weight for g in m.vertices[i].groups}
 def assign(i,values):
  for group in ob.vertex_groups:group.remove([i])
  kept=sorted(values.items(),key=lambda q:-q[1])[:4];total=sum(w for _,w in kept)
  for group,w in kept:ob.vertex_groups[group].add([i],w/total,'REPLACE')
 edgeuse={}
 for p in shirtfaces:
  for a,b in zip(p.vertices,list(p.vertices[1:])+[p.vertices[0]]):edgeuse[tuple(sorted((a,b)))]=edgeuse.get(tuple(sorted((a,b))),0)+1
 boundary={i for edge,count in edgeuse.items() if count==1 for i in edge};cuffcount=0
 for side in [-1,1]:
  a=Vector((side*.35007,.01907,1.20892));c=Vector((side*.47768,-.15699,1.04467));axis=(c-a).normalized();bracerids={i for p in others if side*p.center.x>.32 and 1.00<p.center.z<1.24 for i in p.vertices};assert bracerids,('No bracer source',lod,side)
  ts={i:(m.vertices[i].co-a).dot(axis) for i in bracerids};lo=min(ts.values());top=[i for i,t in ts.items() if t<lo+.009]
  cuff=[i for i in boundary if side*m.vertices[i].co.x>.30 and m.vertices[i].co.z<1.30]
  for i in cuff:
   p=m.vertices[i].co.copy();center=a+axis*(p-a).dot(axis);radial=(p-center).normalized();candidate=max(top,key=lambda j:(m.vertices[j].co-(a+axis*ts[j])).dot(radial));v=m.vertices[candidate];m.vertices[i].co=v.co-radial*.003+axis*.006;assign(i,weights(candidate));cuffcount+=1
 # Find the existing compact pack's front surface; no geometry is moved on the pack itself.
 packfaces=[p for p in others if abs(p.center.x)<.135 and p.center.y>.13 and 1.15<p.center.z<1.43];assert packfaces,('No pack',lod)
 packids={i for p in packfaces for i in p.vertices};fronty=min(m.vertices[i].co.y for i in packids);m.calc_loop_triangles();packtris=[tuple(t.vertices) for t in m.loop_triangles if t.polygon_index in {p.index for p in packfaces}];tree=BVHTree.FromPolygons([v.co for v in m.vertices],packtris,all_triangles=True);reference={i:weights(i) for i in packids};bandcount=0
 for i in {i for p in bandfaces for i in p.vertices}:
  v=m.vertices[i];p=v.co.copy()
  if p.y<.025 or p.z>1.49:continue
  amount=max(0,min(1,(1.49-p.z)/.085));amount=amount*amount*(3-2*amount);side=1 if p.x>0 else -1;target=Vector((p.x-side*.035,fronty+.007,p.z));v.co=p.lerp(target,amount);point,n,fi,d=tree.find_nearest(target);tri=packtris[fi];a,b,c=[m.vertices[j].co for j in tri];f=barycentric_transform(point,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));values={}
  for j,factor in zip(tri,f):
   for group,w in reference[j].items():values[group]=values.get(group,0)+max(0,factor)*w
  total=sum(values.values());values={g:w/total for g,w in values.items()};old=weights(i);mixed={g:old.get(g,0)*(1-amount)+values.get(g,0)*amount for g in set(old)|set(values)};assign(i,mixed);bandcount+=1
 rows.append({'lod':lod,'cuff_boundary_vertices_fitted_inside_bracer':cuffcount,'rear_strap_vertices_fitted_inside_pack_front':bandcount,'pack_front_y_m':fronty})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'continuous_contacts_report.json').write_text(json.dumps({'scope':'Only new wardrobe vertices/weights changed. Sleeve boundary vertices enter original bracer rim by6mm along forearm and3mm inward with exact bracer weights. Rear strap ends enter existing pack front7mm with its interpolated weights. Existing anatomy, bracer/pack geometry, allfour protected materials and rig unchanged.','lods':rows},indent=2)+'\n')
