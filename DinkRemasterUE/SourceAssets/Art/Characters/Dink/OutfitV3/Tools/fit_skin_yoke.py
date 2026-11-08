import bpy,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
ART=Path('/home/davisc/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));size=4096;tile=16;grid=size//tile;images={suffix:bpy.data.images['T_Dink_WardrobeV3_'+suffix] for suffix in ['BC','N','ORM']}
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
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];old=ob.data;chosen=[p for p in old.polygons if p.material_index==0 and 1.44<p.center.z<1.548 and p.center.y>.0 and abs(p.center.x)<.185];assert chosen,('No neck-base Skin faces',lod)
 ids=sorted({i for p in chosen for i in p.vertices});mapping={v:len(old.vertices)+i for i,v in enumerate(ids)};vertices=[tuple(v.co) for v in old.vertices]+[tuple(old.vertices[i].co+old.vertices[i].normal*.008) for i in ids];faces=[tuple(p.vertices) for p in old.polygons];materials=[p.material_index for p in old.polygons];smooth=[p.use_smooth for p in old.polygons];uvvalues=[tuple(l.uv) for l in old.uv_layers[0].data];weights=[[(g.group,g.weight) for g in v.groups] for v in old.vertices]+[[(g.group,g.weight) for g in old.vertices[i].groups] for i in ids];normals=[tuple(n.vector) for n in old.corner_normals]
 for index,p in enumerate(chosen):
  if index>=len(allocated):
   candidates=np.argwhere(free);assert len(candidates),'No free unique atlas cells';iy,ix=map(int,candidates[len(candidates)//2]);free[max(0,iy-1):iy+2,max(0,ix-1):ix+2]=False;allocated.append((iy,ix))
  iy,ix=allocated[index];x=(ix*tile+2)/size+1;y=(iy*tile+2)/size;d=(tile-4)/size;faces.append(tuple(mapping[i] for i in p.vertices));materials.append(4);smooth.append(True)
  count=len(p.vertices)
  if count==4:uvvalues.extend([(x,y),(x+d,y),(x+d,y+d),(x,y+d)])
  else:
   uvvalues.extend([(x+d/2+d*.45*math.cos(i*math.tau/count),y+d/2+d*.45*math.sin(i*math.tau/count)) for i in range(count)])
  normals.extend(tuple(old.vertices[i].normal) for i in p.vertices)
 mesh=bpy.data.meshes.new(old.name+'_SkinYoke');mesh.from_pydata(vertices,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for mat in old.materials:mesh.materials.append(mat)
 for p,mi,sm in zip(mesh.polygons,materials,smooth):p.material_index=mi;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for dst,src in zip(uv.data,uvvalues):dst.uv=src
 mesh.normals_split_custom_set(normals);names=[g.name for g in ob.vertex_groups];ob.data=mesh;ob.vertex_groups.clear()
 for name in names:ob.vertex_groups.new(name=name)
 for i,values in enumerate(weights):
  for group,w in values:ob.vertex_groups[group].add([i],w,'REPLACE')
 rows.append({'lod':lod,'immutable_skin_faces_covered':[p.index for p in chosen],'new_yoke_faces':len(chosen),'new_yoke_vertices':len(ids),'offset_m':.008,'weights':'Exact corresponding protectedSkin weights copied verbatim'})
# Copy all three existing project PBR donor blocks into disjoint previously unused atlas cells.
texture_rows=[]
for suffix,image in images.items():
 path=Path(bpy.path.abspath(image.filepath));before=hashlib.sha256(path.read_bytes()).hexdigest();values=np.empty(size*size*4,np.float32);image.pixels.foreach_get(values);array=values.reshape(size,size,4)
 for iy,ix in allocated:array[iy*tile:(iy+1)*tile,ix*tile:(ix+1)*tile]=donorblocks[suffix]
 image.pixels.foreach_set(array.ravel());image.save();texture_rows.append({'suffix':suffix,'before_sha256':before,'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest()});del values,array
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'skin_yoke_fit_report.json').write_text(json.dumps({'scope':'New cloth yoke encloses only immutable neck-base protectedSkin geometry,8mm offset and identical Skin weights. Unique charts use previously unused atlas rectangles with copied original project blue cloth PBR pixels. No existing UV-mapped texture pixel region or protected anatomy changed.','donor_tile':(donor_y,donor_x),'new_unique_atlas_tiles':allocated,'textures':texture_rows,'lods':rows},indent=2)+'\n');print('SKIN-FITTED YOKE',[(r['lod'],r['new_yoke_faces']) for r in rows],flush=True)
