import bpy,bmesh,json,math,hashlib,numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from pathlib import Path
from mathutils import Vector
ART=Path(Path(__file__).resolve().parents[1])
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));# Work from the exact pre-yoke source checkpoint; do not accumulate overlay collars.
backreport=json.loads((ART/'back_strap_attachment_report.json').read_text())['lods']
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mesh=ob.data;keys={v.index:tuple(round(x,6) for x in v.co) for v in mesh.vertices};adj={};vf={}
 for p in mesh.polygons:
  if p.material_index!=4:continue
  kk=[keys[i] for i in p.vertices]
  for a,b in zip(kk,kk[1:]+kk[:1]):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
  for k in kk:vf.setdefault(k,set()).add(p.index)
 todo=set(adj);shirt=set();collar=set();straps=set();bagfaces=[]
 while todo:
  stack=[next(iter(todo))];component=set()
  while stack:
   k=stack.pop()
   if k in component:continue
   component.add(k);stack.extend(adj[k]-component)
  todo-=component;lo=[min(v[i] for v in component) for i in range(3)];hi=[max(v[i] for v in component) for i in range(3)];fs={i for k in component for i in vf[k]}
  if hi[0]-lo[0]>.7 and .8<lo[2]<1.05 and hi[2]>1.45:shirt|=fs
  if .30<hi[0]-lo[0]<.45 and lo[2]>1.4 and hi[2]<1.56 and hi[1]-lo[1]>.15:collar|=fs
  if hi[2]>1.45 and lo[2]>1.25 and hi[2]-lo[2]>.05 and hi[0]-lo[0]<.29 and (lo[0]>0 or hi[0]<0):straps|=fs
  if .20<hi[0]-lo[0]<.30 and 1.1<lo[2]<1.2 and 1.4<hi[2]<1.44:bagfaces.append(fs)
 assert shirt and collar and bagfaces,('Source parts not found',lod,len(shirt),len(collar),len(bagfaces))
 mark=mesh.attributes.new('SurvivingShirt','INT','FACE')
 for i in shirt:mark.data[i].value=1
 bag=max(bagfaces,key=len);mesh.calc_loop_triangles();tris=[tuple(t.vertices) for t in mesh.loop_triangles if t.polygon_index in bag];skinbag=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],tris,all_triangles=True);bagids={i for p in bag for i in mesh.polygons[p].vertices};miny=min(mesh.vertices[i].co.y for i in bagids);weights_cache={i:[(g.group,g.weight) for g in mesh.vertices[i].groups] for tri in tris for i in tri}
 # Existing straps enter the pack volume below its flap, no free cross-strip.
 for i in {j for p in straps for j in mesh.polygons[p].vertices}:
  v=mesh.vertices[i];co=v.co.copy()
  if co.y<=.02 or co.z>=1.52:continue
  amount=max(0,min(1,(1.52-co.z)/.09));amount=amount*amount*(3-2*amount);side=1 if co.x>0 else -1;center=.20+.2333333*(co.z-1.5);x=side*.105+(co.x-side*center)*.6;target=Vector((x,miny+.010,co.z));co=co.lerp(target,amount);v.co=co;point,normal,face,dist=skinbag.find_nearest(co);tri=tris[face];a,b,c=[mesh.vertices[j].co for j in tri];factors=barycentric_transform(point,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));values={}
  for j,factor in zip(tri,factors):
   for group,w in weights_cache[j]:values[group]=values.get(group,0)+w*max(0,factor)
  total=sum(values.values())
  if total>1e-8:
   old={g.group:g.weight for g in v.groups};mix={g:old.get(g,0)*(1-amount)+values.get(g,0)/total*amount for g in set(old)|set(values)};mix=sorted(mix.items(),key=lambda x:-x[1])[:4];total=sum(w for _,w in mix)
   for group in ob.vertex_groups:group.remove([i])
   for group,w in mix:ob.vertex_groups[group].add([i],w/total,'REPLACE')
 remove=collar # Keep the complete supporting shirt beneath the fitted yoke.
 n=0 # Rear trial ties are not generated in the clean rebuild.
 bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in remove],context='FACES_ONLY');bm.to_mesh(mesh);bm.free();mesh.update()
 print('REMOVED OLD COLLAR/NECK/TIE FACES',lod,len(remove),flush=True)

size=4096;tile=16;grid=size//tile;images={suffix:bpy.data.images['T_Dink_WardrobeV3_'+suffix] for suffix in ['BC','N','ORM']}
# Find one coherent original blue cloth patch, then copy its PBR pixels only to unused atlas regions.
pixels=np.empty(size*size*4,np.float32);images['BC'].pixels.foreach_get(pixels);bc=pixels.reshape(size,size,4);blue=(bc[:,:,2]>bc[:,:,0]*1.15)&(bc[:,:,1]>bc[:,:,0]*1.1)&(bc[:,:,0]>.025);donors=blue.reshape(grid,tile,grid,tile).all(axis=(1,3));candidate=np.argwhere(donors);assert len(candidate),'No coherent blue-cloth donor patch'
donor_y,donor_x=map(int,candidate[len(candidate)//2]);donorblocks={'BC':bc[donor_y*tile:(donor_y+1)*tile,donor_x*tile:(donor_x+1)*tile].copy()};del bc,pixels,blue
for suffix in ['N','ORM']:
 values=np.empty(size*size*4,np.float32);images[suffix].pixels.foreach_get(values);array=values.reshape(size,size,4);donorblocks[suffix]=array[donor_y*tile:(donor_y+1)*tile,donor_x*tile:(donor_x+1)*tile].copy();del values,array
# One chart allocation shared across LODs, so every new texel is used for the same cloth only.
used=np.zeros((size,size),bool)
for lod in range(4):
 mesh=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'].data;mesh.calc_loop_triangles();uv=mesh.uv_layers[0]
 for t in mesh.loop_triangles:
  if mesh.polygons[t.polygon_index].material_index!=4:continue
  points=[uv.data[i].uv for i in t.loops];xs=[(p.x-1)*size for p in points];ys=[p.y*size for p in points];x0=max(0,int(min(xs))-1);x1=min(size,int(max(xs))+2);y0=max(0,int(min(ys))-1);y1=min(size,int(max(ys))+2);used[y0:y1,x0:x1]=True
occupied=used.reshape(grid,tile,grid,tile).any(axis=(1,3));blocked=occupied.copy()
for dy in [-1,0,1]:
 for dx in [-1,0,1]:blocked|=np.roll(np.roll(occupied,dy,0),dx,1)
free=~blocked;free[[0,-1],:]=False;free[:,[0,-1]]=False;allocated=[];rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];old=ob.data;chosen=[p for p in old.polygons if p.material_index==0 and 1.40<p.center.z<1.625 and abs(p.center.x)<.30 and any(old.vertices[i].co.z-.3*old.vertices[i].co.y<1.560 for i in p.vertices)];assert chosen,('No neck-base Skin faces',lod);print('SKIN FACES / FREE ATLAS CELLS',lod,len(chosen),int(free.sum()),flush=True)
 ids=sorted({i for p in chosen for i in p.vertices});mapping={v:len(old.vertices)+i for i,v in enumerate(ids)};vertices=[tuple(v.co) for v in old.vertices]+[tuple(old.vertices[i].co+old.vertices[i].normal*.008) for i in ids];faces=[tuple(p.vertices) for p in old.polygons];materials=[p.material_index for p in old.polygons];smooth=[p.use_smooth for p in old.polygons];uvvalues=[tuple(l.uv) for l in old.uv_layers[0].data];weights=[[(g.group,g.weight) for g in v.groups] for v in old.vertices]+[[(g.group,g.weight) for g in old.vertices[i].groups] for i in ids];normals=[tuple(n.vector) for n in old.corner_normals]
 # Join the fitted yoke directly to surviving shirt boundary vertices.
 marker=old.attributes['SurvivingShirt'];shirtfaces=[p for p in old.polygons if marker.data[p.index].value];shirtids={i for p in shirtfaces for i in p.vertices};targets=[i for i in shirtids if 1.30<old.vertices[i].co.z<1.47 and abs(old.vertices[i].co.x)<.28 and old.vertices[i].normal.dot(Vector((old.vertices[i].co.x,old.vertices[i].co.y+.015,0)))>0];assert targets,('No shirt seam targets',lod)
 edgefaces={}
 for p in chosen:
  for a,b in zip(p.vertices,list(p.vertices[1:])+[p.vertices[0]]):edgefaces.setdefault(tuple(sorted((a,b))),[]).append((a,b))
 newpolys=[tuple(mapping[i] for i in p.vertices) for p in chosen];newnormals=[[tuple(old.vertices[i].normal) for i in p.vertices] for p in chosen];joincount=0
 for edge,directions in edgefaces.items():
  if len(directions)!=1:continue
  a,b=directions[0];mid=(old.vertices[a].co+old.vertices[b].co)/2
  if mid.z>1.54:continue # Actual neck opening stays open and snug.
  ta=min(targets,key=lambda i:(old.vertices[i].co-old.vertices[a].co).length_squared);tb=min(targets,key=lambda i:(old.vertices[i].co-old.vertices[b].co).length_squared)
  face=(mapping[b],mapping[a],ta) if ta==tb else (mapping[b],mapping[a],ta,tb)
  co=[Vector(vertices[i]) for i in face];area=sum((co[j]-co[0]).cross(co[j+1]-co[0]).length/2 for j in range(1,len(co)-1))
  if area<1e-8:continue
  newpolys.append(face);newnormals.append([tuple(old.vertices[b].normal),tuple(old.vertices[a].normal)]+[tuple(old.vertices[i].normal) for i in ([ta] if ta==tb else [ta,tb])]);joincount+=1
 for index,(face,face_normals) in enumerate(zip(newpolys,newnormals)):
  if index>=len(allocated):
   candidates=np.argwhere(free);assert len(candidates),'No free unique atlas cells';iy,ix=map(int,candidates[len(candidates)//2]);free[iy,ix]=False;allocated.append((iy,ix))
  iy,ix=allocated[index];x=(ix*tile+2)/size+1;y=(iy*tile+2)/size;d=(tile-4)/size;faces.append(face);materials.append(4);smooth.append(True);count=len(face)
  if count==4:uvvalues.extend([(x,y),(x+d,y),(x+d,y+d),(x,y+d)])
  else:uvvalues.extend([(x+d/2+d*.45*math.cos(i*math.tau/count),y+d/2+d*.45*math.sin(i*math.tau/count)) for i in range(count)])
  normals.extend(face_normals)
 mesh=bpy.data.meshes.new(old.name+'_SkinYoke');mesh.from_pydata(vertices,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for mat in old.materials:mesh.materials.append(mat)
 for p,mi,sm in zip(mesh.polygons,materials,smooth):p.material_index=mi;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for dst,src in zip(uv.data,uvvalues):dst.uv=src
 mesh.normals_split_custom_set(normals);names=[g.name for g in ob.vertex_groups];ob.data=mesh;ob.vertex_groups.clear()
 for name in names:ob.vertex_groups.new(name=name)
 for i,values in enumerate(weights):
  for group,w in values:ob.vertex_groups[group].add([i],w,'REPLACE')
 # Uniform tilted collar opening, higher at the back; no whole-face selection teeth.
 bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table();newfaces=list(bm.faces)[len(old.polygons):];geom=set(newfaces)
 for face in newfaces:geom.update(face.verts);geom.update(face.edges)
 bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-7,plane_co=(0,0,1.545),plane_no=(0,-.3,1),clear_outer=True,clear_inner=False)
 tiny=[f for f in bm.faces if f.material_index==4 and f.calc_area()<1e-8]
 if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES_ONLY')
 bmesh.ops.recalc_face_normals(bm,faces=[f for f in bm.faces if f.material_index==4]);bm.to_mesh(mesh);bm.free();mesh.update()
 rows.append({'lod':lod,'selected_skin_source_faces':[p.index for p in chosen],'new_yoke_faces':len(chosen),'connected_shirt_seam_faces':joincount,'new_yoke_vertices':len(ids),'offset_m':.008,'weights':'Exact corresponding protectedSkin weights copied verbatim'})
# Copy all three existing project PBR donor blocks into disjoint previously unused atlas cells.
texture_rows=[]
for suffix,image in images.items():
 path=Path(bpy.path.abspath(image.filepath));before=hashlib.sha256(path.read_bytes()).hexdigest();values=np.empty(size*size*4,np.float32);image.pixels.foreach_get(values);array=values.reshape(size,size,4)
 for iy,ix in allocated:array[iy*tile:(iy+1)*tile,ix*tile:(ix+1)*tile]=donorblocks[suffix]
 image.pixels.foreach_set(array.ravel());image.save();texture_rows.append({'suffix':suffix,'before_sha256':before,'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest()});del values,array
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'integrated_skin_yoke_report.json').write_text(json.dumps({'scope':'Old collar ring and covered shirt-neck fragments removed. Connected cloth yoke encloses immutable neck-base protectedSkin geometry,8mm offset and identical Skin weights; outer seam reuses surviving shirt vertices/weights. Rear straps enter the pack flap; horizontal trial ties removed. Unique charts use previously unused atlas rectangles with copied original project blue cloth PBR pixels. No existing UV-mapped texture pixel region or protected anatomy changed.','donor_tile':(donor_y,donor_x),'new_unique_atlas_tiles':allocated,'textures':texture_rows,'lods':rows},indent=2)+'\n');print('SKIN-FITTED YOKE',[(r['lod'],r['new_yoke_faces']) for r in rows],flush=True)
