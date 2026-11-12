import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));report=json.loads((ART/'integrated_skin_yoke_report.json').read_text());tiles=[tuple(v) for v in report['new_unique_atlas_tiles']];tileindex={v:i for i,v in enumerate(tiles)};snapshots=[]
pixels=np.empty(4096*4096*4,np.float32);bpy.data.images['T_Dink_WardrobeV3_BC'].pixels.foreach_get(pixels);colors=pixels.reshape(4096,4096,4)[4::8,4::8,:3].copy();del pixels
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mesh=ob.data;skin_count=len(report['lods'][lod]['selected_skin_source_faces']);cap=[];newfaces=set();shirts=set()
 for p in mesh.polygons:
  if p.material_index!=4:continue
  uv=[mesh.uv_layers[0].data[i].uv for i in p.loop_indices];mean=sum(uv,Vector((0,0)))/len(uv);tile=(int(mean.y*4096)//16,int((mean.x-1)*4096)//16);index=tileindex.get(tile,-1)
  if index>=0:
   newfaces.add(p.index)
   if index<skin_count:cap.append(p.index)
  else:
   px=max(0,min(511,int((mean.x-1)*4096)//8));py=max(0,min(511,int(mean.y*4096)//8));r,g,b=colors[py,px]
   if b>r*1.12 and g>r*1.06 and 1.20<p.center.z<1.51:shirts.update(p.vertices)
 snapshots.append({'ob':ob,'mesh':mesh,'cap':cap,'newfaces':newfaces,'shirts':shirts,'skin_count':skin_count,'source_ids':report['lods'][lod]['selected_skin_source_faces']})
rows=[]
for lod,snapshot in enumerate(snapshots):
 ob=snapshot['ob'];old=snapshot['mesh'];source=snapshots[0 if lod>=2 else lod];sourceob=source['ob'];sourcemesh=source['mesh'];source_count=source['skin_count'];capindices=source['cap'];vertices=[tuple(v.co) for v in old.vertices];weights=[[(g.group,g.weight) for g in v.groups] for v in old.vertices];faces=[];materials=[];smooth=[];uvvalues=[];normals=[];groupnames=[g.name for g in ob.vertex_groups];name_to_group={name:i for i,name in enumerate(groupnames)}
 for p in old.polygons:
  if p.index in snapshot['newfaces']:continue
  faces.append(tuple(p.vertices));materials.append(p.material_index);smooth.append(p.use_smooth)
  uvvalues.extend(tuple(old.uv_layers[0].data[i].uv) for i in p.loop_indices);normals.extend(tuple(old.corner_normals[i].vector) for i in p.loop_indices)
 cap_ids=sorted({i for pi in capindices for i in sourcemesh.polygons[pi].vertices});mapping={v:len(vertices)+i for i,v in enumerate(cap_ids)}
 for i in cap_ids:
  vertices.append(tuple(sourcemesh.vertices[i].co));weights.append([(name_to_group[sourceob.vertex_groups[g.group].name],g.weight) for g in sourcemesh.vertices[i].groups])
 edge_use={};cap_tile_centers={}
 for pi in capindices:
  p=sourcemesh.polygons[pi];face=tuple(mapping[i] for i in p.vertices);faces.append(face);materials.append(4);smooth.append(True);uvvalues.extend(tuple(sourcemesh.uv_layers[0].data[i].uv) for i in p.loop_indices);normals.extend(tuple(sourcemesh.corner_normals[i].vector) for i in p.loop_indices)
  mean=sum((sourcemesh.uv_layers[0].data[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.vertices);key=(int(mean.y*4096)//16,int((mean.x-1)*4096)//16);cap_tile_centers[key]=(sum((sourcemesh.vertices[i].co for i in p.vertices),Vector())/len(p.vertices),p.normal.copy())
  for a,b in zip(face,face[1:]+face[:1]):edge_use.setdefault(tuple(sorted((a,b))),[]).append((a,b))
 targets=[i for i in snapshot['shirts'] if old.vertices[i].co.z>1.15 and abs(old.vertices[i].co.x)<.32 and old.vertices[i].normal.dot(Vector((old.vertices[i].co.x,old.vertices[i].co.y+.015,0)))>0];assert targets,('No outer shirt targets',lod)
 seams=[];anchors={}
 for edge,directions in edge_use.items():
  if len(directions)!=1:continue
  a,b=directions[0];mid=(Vector(vertices[a])+Vector(vertices[b]))/2
  if mid.z-.3*mid.y>1.535:continue
  for v in [a,b]:
   if v in anchors:continue
   co=Vector(vertices[v]);eligible=[i for i in targets if old.vertices[i].co.z<co.z-.05];assert eligible,('No lower shirt row',lod,tuple(co));anchors[v]=min(eligible,key=lambda i:(old.vertices[i].co-co).length_squared)
  ta,tb=anchors[a],anchors[b];face=(b,a,ta) if ta==tb else (b,a,ta,tb);co=[Vector(vertices[i]) for i in face];area=sum((co[j]-co[0]).cross(co[j+1]-co[0]).length/2 for j in range(1,len(co)-1))
  if area>1e-8:seams.append(face)
 assert source_count+len(seams)<=len(tiles),('More seam charts required',lod,source_count,len(seams),len(tiles))
 for index,face in enumerate(seams):
  iy,ix=tiles[source_count+index];x=(ix*16+2)/4096+1;y=(iy*16+2)/4096;d=12/4096;faces.append(face);materials.append(4);smooth.append(True)
  if len(face)==4:uvvalues.extend([(x,y),(x+d,y),(x+d,y+d),(x,y+d)])
  else:uvvalues.extend([(x+d/2+d*.45*math.cos(i*math.tau/3),y+d/2+d*.45*math.sin(i*math.tau/3)) for i in range(3)])
  a,b,c=[Vector(vertices[i]) for i in face[:3]];normal=(b-a).cross(c-a).normalized();normals.extend([tuple(normal)]*len(face))
 mesh=bpy.data.meshes.new(old.name+'_Connected');mesh.from_pydata(vertices,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for mat in old.materials:mesh.materials.append(mat)
 for p,mi,sm in zip(mesh.polygons,materials,smooth):p.material_index=mi;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for dst,src in zip(uv.data,uvvalues):dst.uv=src
 mesh.normals_split_custom_set(normals);ob.data=mesh;ob.vertex_groups.clear()
 for name in groupnames:ob.vertex_groups.new(name=name)
 for i,values in enumerate(weights):
  for group,w in values:ob.vertex_groups[group].add([i],w,'REPLACE')
 if lod>=2:
  mesh.calc_loop_triangles();skintris=[t for t in mesh.loop_triangles if mesh.polygons[t.polygon_index].material_index==0];tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[tuple(t.vertices) for t in skintris],all_triangles=True);refs=[]
  highbody=snapshots[0]['mesh']
  for index,high_face_id in enumerate(source['source_ids']):
   key=tiles[index];point,normal=cap_tile_centers.get(key,(highbody.polygons[high_face_id].center.copy(),highbody.polygons[high_face_id].normal.copy()));point=point-normal*.010;near=tree.find_nearest_range(point,.04);valid=[row for row in near if row[1].dot(normal)>0]
   chosen=min(valid or near,key=lambda row:row[3]) if near else tree.find_nearest(point);refs.append(skintris[chosen[2]].polygon_index)
  report['lods'][lod]['selected_skin_source_faces']=refs
 report['lods'][lod]['yoke_geometry_source_lod']=0 if lod>=2 else lod;report['lods'][lod]['connected_shirt_seam_faces']=len(seams);rows.append({'lod':lod,'yoke_geometry_source_lod':0 if lod>=2 else lod,'skin_yoke_faces':len(capindices),'connected_lower_shirt_seams':len(seams),'minimum_anchor_drop_m':.05})
bpy.data.materials['MI_Dink_WardrobeV3'].use_backface_culling=True
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'integrated_skin_yoke_report.json').write_text(json.dumps(report,indent=2)+'\n');(ART/'shared_yoke_lod_report.json').write_text(json.dumps({'scope':'Skin cut-edge skirt connected to actual shirt vertices at least5cm lower. LOD2/3 retain the proven LOD0 Skin-fitted yoke geometry/weights to avoid coarse clipped-edge inversion; all four protected anatomical LODs unchanged. New Wardrobe explicitly one-sided.','lods':rows},indent=2)+'\n');print('SHARED YOKE AND LOWER SEAMS',rows,flush=True)
