import bpy,bmesh,math,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART.parent/'HandBindingV2/SK_Dink_Hands.blend'))
ob=bpy.data.objects['SK_Dink_Hands_LOD0'];m=ob.data;origco=[v.co.copy() for v in m.vertices];origweights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in m.vertices]
shirtpolys=list(m.polygons)[9834:13139];shirtids=sorted({i for p in shirtpolys for i in p.vertices});rank={i:j for j,i in enumerate(shirtids)}
refcoords=[v.copy() for v in origco];m.calc_loop_triangles();shirttris=[tuple(t.vertices) for t in m.loop_triangles if 9834<=t.polygon_index<13139];skintris=[tuple(t.vertices) for t in m.loop_triangles if m.polygons[t.polygon_index].material_index==0 and 1.38<m.polygons[t.polygon_index].center.z<1.61];shirtbvh=BVHTree.FromPolygons(refcoords,shirttris,all_triangles=True);skinbvh=BVHTree.FromPolygons(refcoords,skintris,all_triangles=True)
# Build a genuinely filled anatomical garment volume; remeshing the original thin shell loses sleeves.
bpy.ops.object.select_all(action='DESELECT')
parts=[]
def ellipsoid(center,radii,direction=None):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=center);part=bpy.context.object;part.scale=radii
 if direction is not None:part.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parts.append(part)
ellipsoid((0,.0,1.265),(.176,.135,.285))
for side in [-1,1]:
 ellipsoid((side*.175,.012,1.435),(.105,.108,.105))
 ellipsoid((side*.185,.005,1.345),(.080,.100,.135))
 a=Vector((side*.190,.02557,1.43583));b=Vector((side*.35007,.01907,1.20892));c=Vector((side*.47768,-.15699,1.04467))
 for start,end,radius in [(a,b,.068),(b,c,.057)]:
  axis=end-start;ellipsoid((start+end)/2,(radius,radius,axis.length/2+.045),axis)
bpy.ops.object.select_all(action='DESELECT')
for part in parts:part.select_set(True)
work=parts[0];bpy.context.view_layer.objects.active=work;bpy.ops.object.join();mesh=work.data
# A closed collar volume joins the torso before remeshing, replacing every old neck fragment.
verts=[];faces=[];N=48
for z in [1.43,1.57]:
 for i in range(N):
  a=i*math.tau/N;verts.append((.105*math.cos(a),.015+.103*math.sin(a),z))
faces.extend([tuple(reversed(range(N))),tuple(range(N,2*N))])
for i in range(N):j=(i+1)%N;faces.append((i,j,N+j,N+i))
neckmesh=bpy.data.meshes.new('NeckVolume');neckmesh.from_pydata(verts,[],faces);neck=bpy.data.objects.new('NeckVolume',neckmesh);bpy.context.collection.objects.link(neck);bpy.ops.object.select_all(action='DESELECT');neck.select_set(True);work.select_set(True);bpy.context.view_layer.objects.active=work;bpy.ops.object.join();bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
rem=work.modifiers.new('ConnectedVoxelSurface','REMESH');rem.mode='VOXEL';rem.voxel_size=.012;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
sm=work.modifiers.new('SewnSurfaceSmooth','SMOOTH');sm.factor=.7;sm.iterations=4;bpy.ops.object.modifier_apply(modifier=sm.name)
dec=work.modifiers.new('WardrobeOnlyBudget','DECIMATE');dec.ratio=min(1,3800/max(1,len(work.data.polygons)));bpy.ops.object.modifier_apply(modifier=dec.name)
# Trim a precise tilted ellipse through the joined collar volume.
verts=[];faces=[]
for z in [1.545,1.85]:
 for i in range(N):
  a=i*math.tau/N;y=.015+.074*math.sin(a);verts.append((.077*math.cos(a),y,z+.3*y))
faces.extend([tuple(reversed(range(N))),tuple(range(N,2*N))])
for i in range(N):j=(i+1)%N;faces.append((i,j,N+j,N+i))
cm=bpy.data.meshes.new('NeckOpening');cm.from_pydata(verts,[],faces);cut=bpy.data.objects.new('NeckOpening',cm);bpy.context.collection.objects.link(cut)
bo=work.modifiers.new('CleanNeckOpening','BOOLEAN');bo.operation='DIFFERENCE';bo.solver='EXACT';bo.object=cut;bpy.ops.object.modifier_apply(modifier=bo.name);bpy.data.objects.remove(cut,do_unlink=True)
bm=bmesh.new();bm.from_mesh(work.data);floor=[f for f in bm.faces if abs(f.calc_center_median().z-.3*f.calc_center_median().y-1.545)<.00015 and f.normal.z<-.5];bmesh.ops.delete(bm,geom=floor,context='FACES_ONLY');bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,1.012),plane_no=(0,0,1),clear_inner=True,clear_outer=False);bm.to_mesh(work.data);bm.free()
# Waist and forearm ends disappear beneath the vest and red bracers.
bm=bmesh.new();bm.from_mesh(work.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,1.073),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
for side in [-1,1]:
 a=Vector((side*.35007,.01907,1.20892));c=Vector((side*.47768,-.15699,1.04467));axis=(c-a).normalized();center=a.lerp(c,.30);region=[v for v in bm.verts if side*v.co.x>.30 and v.co.z<1.30];geom=set(region)
 for v in region:geom.update(v.link_edges);geom.update(v.link_faces)
 bmesh.ops.bisect_plane(bm,geom=list(geom),dist=1e-7,plane_co=center,plane_no=axis,clear_outer=True,clear_inner=False)
bm.to_mesh(work.data);bm.free()
def transfer(point,tree,tris):
 near,normal,face,dist=tree.find_nearest(point);tri=tris[face];a,b,c=[refcoords[i] for i in tri];fac=barycentric_transform(near,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));vals={}
 for i,f in zip(tri,fac):
  for name,w in origweights[i].items():vals[name]=vals.get(name,0)+w*max(0,f)
 vals=sorted(vals.items(),key=lambda row:-row[1])[:4];total=sum(w for _,w in vals);return near,normal,dist,{name:w/total for name,w in vals}
newweights=[]
for v in work.data.vertices:
 point=v.co.copy();near,n,d,w=transfer(point,shirtbvh,shirttris)
 # Project from a limb-aware volume center onto the OUTERMOST source shirt surface.
 if abs(point.x)>.19 and point.z<1.48:
  side=1 if point.x>0 else -1;segments=[(Vector((side*.190,.02557,1.43583)),Vector((side*.35007,.01907,1.20892))),(Vector((side*.35007,.01907,1.20892)),Vector((side*.47768,-.15699,1.04467)))]
  centers=[]
  for a,b in segments:
   f=max(0,min(1,(point-a).dot(b-a)/(b-a).length_squared));centers.append(a+(b-a)*f)
  center=min(centers,key=lambda c:(c-point).length_squared)
 else:center=Vector((0,.0,min(1.46,max(1.04,point.z))))
 radial=(point-center).normalized()
 if point.z<1.51 and radial.length>.5:
  hit,hn,fi,hd=shirtbvh.ray_cast(point+radial*.20,-radial,.40)
  if hit is not None and (hit-point).length<.035:v.co=point.lerp(hit+radial*.004,.35)
 sn,snrm,sd,sw=transfer(v.co,skinbvh,skintris)
 if sd<.055 and v.co.z>1.39:
  side=(v.co-sn).dot(snrm)
  if side<.013:v.co+=snrm*(.013-side)
  w=sw
 newweights.append(w)
# Smooth positional ripples without changing the neck seam, then refit the immutable Skin envelope.
bm=bmesh.new();bm.from_mesh(work.data);bmesh.ops.smooth_vert(bm,verts=[v for v in bm.verts if not v.is_boundary],factor=.25,use_axis_x=True,use_axis_y=True,use_axis_z=True);bm.to_mesh(work.data);bm.free()
for v in work.data.vertices:
 sn,n,d,w=transfer(v.co,skinbvh,skintris)
 if d<.055 and v.co.z>1.39:
  side=(v.co-sn).dot(n)
  if side<.012:v.co+=n*(.012-side)
  newweights[v.index]=w
# Keep the hidden torso inside the leather vest, with a gradual armhole transition.
for v in work.data.vertices:
 co=v.co;amount=max(0,min(1,(1.40-co.z)/.10))*max(0,min(1,(.21-abs(co.x))/.045));co.x*=1-.12*amount;co.y*=1-.30*amount
# Smooth transferred cloth weights over the new connected topology to avoid isolated armpit folds.
adj=[set() for v in work.data.vertices]
for edge in work.data.edges:
 a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
for iteration in range(6):
 result=[]
 for i,values in enumerate(newweights):
  co=work.data.vertices[i].co;sn,n,d,sw=transfer(co,skinbvh,skintris)
  if d<.024 and co.z>1.43:result.append(values);continue
  merged={k:w*.5 for k,w in values.items()};neighbors=adj[i]
  for j in neighbors:
   for k,w in newweights[j].items():merged[k]=merged.get(k,0)+w*.5/max(1,len(neighbors))
  kept=sorted(merged.items(),key=lambda row:-row[1])[:4];total=sum(w for _,w in kept);result.append({k:w/total for k,w in kept})
 newweights=result
work.data.update();shirtco=[v.co.copy() for v in work.data.vertices];shirtfaces=[tuple(p.vertices) for p in work.data.polygons];print('CLEAN SHIRT',len(shirtco),len(shirtfaces),flush=True)
# Preserve this generated surface and exact transferred weights across all protected anatomical LODs.
clothbvh=BVHTree.FromPolygons(shirtco,shirtfaces,all_triangles=False)
wardco=list(shirtco);wardfaces=list(shirtfaces);wardweights=list(newweights);wardtypes=['blue']*len(wardfaces)
def cloth_point(point):
 co,n,fi,d=clothbvh.find_nearest(point);p=shirtfaces[fi];a,b,c=[shirtco[i] for i in p[:3]];f=barycentric_transform(co,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));vals={}
 for i,t in zip(p[:3],f):
  for name,w in newweights[i].items():vals[name]=vals.get(name,0)+max(0,t)*w
 vals=sorted(vals.items(),key=lambda row:-row[1])[:4];total=sum(w for _,w in vals);return co,n,{k:w/total for k,w in vals}
# Smooth centerline rails provide a sewn leather silhouette, without per-edge nearest-surface zigzags.
for side in [-1,1]:
 base=len(wardco);segments=32;width=.034;rail=[]
 for j in range(segments+1):
  t=math.pi*j/segments;x=side*(.14+.035*math.sin(t));y=-.158*math.cos(t);z=1.38+.167*math.sin(t);p,n,w=cloth_point(Vector((x,y,z)));rail.append(p)
 for iteration in range(8):rail=[v if i in [0,segments] else v*.5+(rail[i-1]+rail[i+1])*.25 for i,v in enumerate(rail)]
 rowweights=[cloth_point(p)[2] for p in rail]
 for iteration in range(4):
  result=[]
  for j,values in enumerate(rowweights):
   merged={}
   for k in [max(0,j-1),j,min(segments,j+1)]:
    for name,w in rowweights[k].items():merged[name]=merged.get(name,0)+w/3
   kept=sorted(merged.items(),key=lambda row:-row[1])[:4];total=sum(w for _,w in kept);result.append({name:w/total for name,w in kept})
  rowweights=result
 for j,p in enumerate(rail):
  tangent=(rail[min(segments,j+1)]-rail[max(0,j-1)]).normalized();normal=Vector((1,0,0)).cross(tangent).normalized();widthaxis=tangent.cross(normal).normalized();edges=[p+widthaxis*edge*width/2 for edge in [-1,1]];lift=0
  for edge in edges:
   q,n,w=cloth_point(edge);lift=max(lift,(q-edge).dot(normal))
  for layer in [0,1]:
   for edge in edges:
    point=edge+normal*(lift+.002+layer*.003);q,n,w=cloth_point(point);wardco.append(point);wardweights.append(rowweights[j])
 for j in range(segments):
  a=base+j*4;b=a+4
  for f in [(a+2,b+2,b+3,a+3),(a+1,b+1,b,a),(a,b,b+2,a+2),(a+3,b+3,b+1,a+1)]:wardfaces.append(tuple(reversed(f)));wardtypes.append('brown')
 for f in [(base,base+2,base+3,base+1),(base+segments*4,base+segments*4+1,base+segments*4+3,base+segments*4+2)]:wardfaces.append(tuple(reversed(f)));wardtypes.append('brown')
print('NEW GARMENT',len(wardco),len(wardfaces),flush=True)
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'))
size=4096;tile=8;grid=size//tile;images={s:bpy.data.images['T_Dink_WardrobeV3_'+s] for s in ['BC','N','ORM']};raw=np.empty(size*size*4,np.float32);images['BC'].pixels.foreach_get(raw);bc=raw.reshape(size,size,4);sample=bc[4::8,4::8,:3].copy();del raw,bc
report=json.loads((ART/'integrated_skin_yoke_report.json').read_text());oldtiles={tuple(t) for t in report['new_unique_atlas_tiles']};remove_sets=[];used=np.zeros((grid,grid),bool)
for lod in range(4):
 mesh=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'].data;remove=set();keys={v.index:tuple(round(x,6) for x in v.co) for v in mesh.vertices};adj={};vf={}
 for p in mesh.polygons:
  if p.material_index!=4:continue
  pts=[mesh.uv_layers[0].data[i].uv for i in p.loop_indices];mean=sum(pts,Vector((0,0)))/len(pts);ix=max(0,min(grid-1,int((mean.x-1)*size)//tile));iy=max(0,min(grid-1,int(mean.y*size)//tile));r,g,b=sample[iy,ix];oldtile=(int(mean.y*size)//16,int((mean.x-1)*size)//16)
  if oldtile in oldtiles or (b>r*1.12 and g>r*1.06 and p.center.z>.98):remove.add(p.index)
  kk=[keys[i] for i in p.vertices]
  for a,b in zip(kk,kk[1:]+kk[:1]):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
  for k in kk:vf.setdefault(k,set()).add(p.index)
 todo=set(adj)
 while todo:
  stack=[next(iter(todo))];comp=set()
  while stack:
   k=stack.pop()
   if k in comp:continue
   comp.add(k);stack.extend(adj[k]-comp)
  todo-=comp;lo=[min(k[i] for k in comp) for i in range(3)];hi=[max(k[i] for k in comp) for i in range(3)];fs={i for k in comp for i in vf[k]}
  if hi[2]>1.45 and lo[2]>1.25 and hi[2]-lo[2]>.05 and hi[0]-lo[0]<.29 and (lo[0]>0 or hi[0]<0):remove|=fs
 remove_sets.append(remove)
 for p in mesh.polygons:
  if p.material_index!=4 or p.index in remove:continue
  pts=[mesh.uv_layers[0].data[i].uv for i in p.loop_indices];xs=[(v.x-1)*size/tile for v in pts];ys=[v.y*size/tile for v in pts];used[max(0,int(min(ys))-1):min(grid,int(max(ys))+2),max(0,int(min(xs))-1):min(grid,int(max(xs))+2)]=True
free=np.argwhere(~used);assert len(free)>len(wardfaces),(len(free),len(wardfaces));allocated=[tuple(map(int,row)) for row in free[:len(wardfaces)]];donors={}
for kind,mask in [('blue',(sample[:,:,2]>sample[:,:,0]*1.5)&(sample[:,:,1]>sample[:,:,0]*1.25)),('brown',(sample[:,:,0]>sample[:,:,2]*1.8)&(sample[:,:,0]>sample[:,:,1]*1.25)&(sample[:,:,0]<sample[:,:,1]*2)&(sample[:,:,0]>.04))]:
 options=np.argwhere(mask);assert len(options),kind;donors[kind]=tuple(map(int,options[len(options)//2]))
for suffix,image in images.items():
 arr=np.empty(size*size*4,np.float32);image.pixels.foreach_get(arr);arr=arr.reshape(size,size,4);blocks={kind:arr[y*tile:(y+1)*tile,x*tile:(x+1)*tile].copy() for kind,(y,x) in donors.items()}
 for (y,x),kind in zip(allocated,wardtypes):arr[y*tile:(y+1)*tile,x*tile:(x+1)*tile]=blocks[kind]
 image.pixels.foreach_set(arr.ravel());image.save()
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];old=ob.data;verts=[tuple(v.co) for v in old.vertices];weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in old.vertices];faces=[];mis=[];uvs=[];normals=[];smooth=[]
 for p in old.polygons:
  if p.index in remove_sets[lod]:continue
  faces.append(tuple(p.vertices));mis.append(p.material_index);smooth.append(p.use_smooth);uvs.extend(tuple(old.uv_layers[0].data[i].uv) for i in p.loop_indices);normals.extend(tuple(old.corner_normals[i].vector) for i in p.loop_indices)
 offset=len(verts);verts.extend(tuple(v) for v in wardco);weights.extend(wardweights)
 for face,(iy,ix) in zip(wardfaces,allocated):
  faces.append(tuple(offset+i for i in face));mis.append(4);smooth.append(True);x=1+(ix*tile+1.5)/size;y=(iy*tile+1.5)/size;d=5/size
  uvs.extend([(x+d*.5+d*.45*math.cos(j*math.tau/len(face)),y+d*.5+d*.45*math.sin(j*math.tau/len(face))) for j in range(len(face))]);normal=(wardco[face[1]]-wardco[face[0]]).cross(wardco[face[2]]-wardco[face[0]]).normalized();normals.extend([tuple(normal)]*len(face))
 mesh=bpy.data.meshes.new(old.name+'_ContinuousShirt');mesh.from_pydata(verts,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for mat in old.materials:mesh.materials.append(mat)
 for p,mi,sm in zip(mesh.polygons,mis,smooth):p.material_index=mi;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for p,v in zip(uv.data,uvs):p.uv=v
 mesh.normals_split_custom_set(normals);names=[g.name for g in ob.vertex_groups];ob.data=mesh;ob.vertex_groups.clear()
 for name in names:ob.vertex_groups.new(name=name)
 for i,values in enumerate(weights):
  for name,w in values.items():ob.vertex_groups[name].add([i],w,'REPLACE')
 print('LOD REPLACED',lod,len(remove_sets[lod]),'tris',sum(len(p.vertices)-2 for p in mesh.polygons),flush=True)
bpy.data.materials['MI_Dink_WardrobeV3'].use_backface_culling=True
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'continuous_shirt_report.json').write_text(json.dumps({'shirt_vertices':len(shirtco),'shirt_faces':len(shirtfaces),'new_garment_faces':len(wardfaces),'allocated_tiles':allocated,'donors':donors,'replaced_faces_per_lod':[len(r) for r in remove_sets],'scope':'Only wardrobe shirt and shoulder bands replaced; immutable protected anatomy and all89 restbones retained. Continuous remeshed source shirt, clean ellipse neckline, Skin normal envelope12mm, nearest source/Skin weights top4. Four anatomy LODs retain full new shirt detail pending visual gate.'},indent=2)+'\n')
