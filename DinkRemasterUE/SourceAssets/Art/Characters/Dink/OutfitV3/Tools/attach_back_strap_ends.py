import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ART=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));size=4096
pixels=np.empty(size*size*4,np.float32);bpy.data.images['T_Dink_WardrobeV3_BC'].pixels.foreach_get(pixels);colors=pixels.reshape(size,size,4)[4::8,4::8,:3].copy();del pixels
rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];old=ob.data;keys={v.index:tuple(round(x,6) for x in v.co) for v in old.vertices};vf={};adj={}
 for face in old.polygons:
  if face.material_index!=4:continue
  kk=[keys[v] for v in face.vertices]
  for a,b in zip(kk,kk[1:]+kk[:1]):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
  for k in kk:vf.setdefault(k,set()).add(face.index)
 todo=set(adj);straps=set();vestparts=[]
 while todo:
  stack=[next(iter(todo))];component=set()
  while stack:
   k=stack.pop()
   if k in component:continue
   component.add(k);stack.extend(adj[k]-component)
  todo-=component;lo=[min(v[i] for v in component) for i in range(3)];hi=[max(v[i] for v in component) for i in range(3)];faces={i for k in component for i in vf[k]}
  if hi[2]>1.45 and lo[2]>1.25 and hi[2]-lo[2]>.05 and hi[0]-lo[0]<.29 and (lo[0]>0 or hi[0]<0):straps|=faces
  if .20<hi[0]-lo[0]<.30 and 1.10<lo[2]<1.20 and 1.40<hi[2]<1.44:vestparts.append(faces)
 vest=max(vestparts,key=len);bagverts={i for p in vest for i in old.polygons[p].vertices};bagminy=min(old.vertices[i].co.y for i in bagverts);bagmaxz=max(old.vertices[i].co.z for i in bagverts);old.calc_loop_triangles();tris=[tuple(t.vertices) for t in old.loop_triangles if t.polygon_index in vest];surface=BVHTree.FromPolygons([v.co for v in old.vertices],tris,all_triangles=True)
 # Allocate distinct8x8pixel charts only in unused, already brown atlas regions.
 used=np.zeros((size,size),bool);uv=old.uv_layers[0]
 for t in old.loop_triangles:
  if old.polygons[t.polygon_index].material_index!=4:continue
  points=[uv.data[i].uv for i in t.loops];xs=[(p.x-1)*size for p in points];ys=[p.y*size for p in points];x0=max(0,int(min(xs))-1);x1=min(size,int(max(xs))+2);y0=max(0,int(min(ys))-1);y1=min(size,int(max(ys))+2);used[y0:y1,x0:x1]=True
 tiles=used.reshape(512,8,512,8).any(axis=(1,3));blocked=tiles.copy()
 for dy in [-1,0,1]:
  for dx in [-1,0,1]:blocked|=np.roll(np.roll(tiles,dy,0),dx,1)
 free=~blocked;free[[0,-1],:]=False;free[:,[0,-1]]=False;free&=(colors[:,:,0]>colors[:,:,1]*1.18)&(colors[:,:,1]>colors[:,:,2]*1.18)&(colors[:,:,0]>.01)
 edges={}
 for pi in straps:
  p=old.polygons[pi]
  for li,lj in zip(p.loop_indices,list(p.loop_indices[1:])+[p.loop_indices[0]]):
   a=old.loops[li].vertex_index;b=old.loops[lj].vertex_index;ca=old.vertices[a].co;cb=old.vertices[b].co
   if abs(ca.z-1.43)>2e-5 or abs(cb.z-1.43)>2e-5 or (ca.y+cb.y)/2<=.02 or (ca-cb).length<1e-5:continue
   key=tuple(sorted((keys[a],keys[b])));edges.setdefault(key,(a,b,li,lj))
 # One broad sewn termination patch per side covers the continuous strap bundle.
 grouped={-1:[],1:[]}
 for a,b,li,lj in edges.values():
  grouped[1 if old.vertices[a].co.x>0 else -1].extend([(a,li),(b,lj)])
 edges={}
 for side,points in grouped.items():
  if not points:continue
  a,li=min(points,key=lambda v:old.vertices[v[0]].co.x);b,lj=max(points,key=lambda v:old.vertices[v[0]].co.x)
  edges[side]=(a,b,li,lj)
 vertices=[tuple(v.co) for v in old.vertices];faces=[tuple(p.vertices) for p in old.polygons];materials=[p.material_index for p in old.polygons];smooth=[p.use_smooth for p in old.polygons];uvvalues=[tuple(l.uv) for l in uv.data];weights=[[(g.group,g.weight) for g in v.groups] for v in old.vertices];normals=[tuple(n.vector) for n in old.corner_normals];bottoms={}
 for key,(a,b,li,lj) in edges.items():
  targets=[]
  for index in [a,b]:
   coord=old.vertices[index].co;cachekey=keys[index]
   if cachekey not in bottoms:
    side=1 if coord.x>0 else -1;targetx=side*.1075+(-.0125 if index==a else .0125);point,normal,face,dist=surface.find_nearest(Vector((targetx,bagminy+.008,bagmaxz-.003)));tri=tris[face];pa,pb,pc=[old.vertices[i].co for i in tri];factors=barycentric_transform(point,pa,pb,pc,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));values={}
    for i,factor in zip(tri,factors):
     for g in old.vertices[i].groups:values[g.group]=values.get(g.group,0)+g.weight*max(0,factor)
    values=sorted(values.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in values)
    if total<1e-8:values=weights[index];total=sum(w for _,w in values)
    bottoms[cachekey]=len(vertices);vertices.append(tuple(point+normal*.001));weights.append([(g,w/total) for g,w in values])
   targets.append(bottoms[cachekey])
  sourceuv=uv.data[li].uv;px=max(0,min(size-1,int((sourceuv.x-1)*size)));py=max(0,min(size-1,int(sourceuv.y*size)));target=colors[py//8,px//8];distance=np.sum((colors-target)**2,axis=2);distance[~free]=np.inf;iy,ix=np.unravel_index(np.argmin(distance),distance.shape)
  assert np.isfinite(distance[iy,ix]),'No unused brown atlas tile left'
  free[max(0,iy-1):iy+2,max(0,ix-1):ix+2]=False
  x=(ix*8+1)/size+1;y=(iy*8+1)/size;d=6/size
  faces.append((a,b,targets[1],targets[0]));materials.append(4);smooth.append(True);uvvalues.extend([(x,y+d),(x+d,y+d),(x+d,y),(x,y)]);normals.extend([(0,1,0)]*4)
 mesh=bpy.data.meshes.new(old.name+'_Joined');mesh.from_pydata(vertices,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for mat in old.materials:mesh.materials.append(mat)
 for p,mi,sm in zip(mesh.polygons,materials,smooth):p.material_index=mi;p.use_smooth=sm
 layer=mesh.uv_layers.new(name='UVMap')
 for dst,src in zip(layer.data,uvvalues):dst.uv=src
 groupnames=[g.name for g in ob.vertex_groups];mesh.normals_split_custom_set(normals);ob.data=mesh;ob.vertex_groups.clear()
 for name in groupnames:ob.vertex_groups.new(name=name)
 for index,values in enumerate(weights):
  for group,w in values:ob.vertex_groups[group].add([index],w,'REPLACE')
 rows.append({'lod':lod,'continuous_leather_join_quads':len(edges),'new_join_vertices':len(vertices)-len(old.vertices),'new_unique_atlas_charts':len(edges)})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'back_strap_attachment_report.json').write_text(json.dumps({'scope':'Continuous leather termination joins cut edge to vest surface with interpolated vest weights; unique atlas charts reuse only previously unused brown texture pixels; no texture changes or new slots','lods':rows},indent=2)+'\n');print('BACK STRAP ENDS ATTACHED',rows,flush=True)
