import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ART=Path(Path(__file__).resolve().parents[1])
def facekey(mesh,p):return tuple(sorted(tuple(round(x,6) for x in mesh.vertices[i].co) for i in p.vertices))
bpy.ops.wm.open_mainfile(filepath=str(ART/'Tools/Checkpoints/PreIntegrated.blend.snapshot'));hardware=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];m=ob.data;keys={v.index:tuple(round(x,6) for x in v.co) for v in m.vertices};adj={};vf={}
 for p in m.polygons:
  if p.material_index!=4:continue
  kk=[keys[i] for i in p.vertices]
  for a,b in zip(kk,kk[1:]+kk[:1]):adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
  for k in kk:vf.setdefault(k,set()).add(p.index)
 todo=set(adj);chosen=set()
 while todo:
  stack=[next(iter(todo))];comp=set()
  while stack:
   k=stack.pop()
   if k in comp:continue
   comp.add(k);stack.extend(adj[k]-comp)
  todo-=comp;lo=[min(v[i] for v in comp) for i in range(3)];hi=[max(v[i] for v in comp) for i in range(3)];fs={i for k in comp for i in vf[k]};cx=(hi[0]+lo[0])/2
  pack=(.035<abs(cx)<.085 and lo[1]>.20 and lo[2]>1.266 and hi[2]<1.304 and hi[1]-lo[1]<.008 and hi[0]-lo[0]<.034 and hi[2]-lo[2]<.032)
  belt=(lo[2]>.995 and hi[2]<1.053 and hi[1]<-.18 and hi[1]-lo[1]<.02 and hi[0]-lo[0]<.10)
  if pack or belt:chosen|=fs
 rows=[]
 for pi in sorted(chosen):
  p=m.polygons[pi];rows.append({'key':facekey(m,p),'co':[tuple(m.vertices[i].co) for i in p.vertices],'weights':[{ob.vertex_groups[g.group].name:g.weight for g in m.vertices[i].groups} for i in p.vertices],'normals':[tuple(m.corner_normals[i].vector) for i in p.loop_indices]})
 hardware.append(rows);print('SOURCE HARDWARE',lod,len(rows),flush=True)
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));used=np.zeros((512,512),bool);restores=[];lining=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];m=ob.data;existing={facekey(m,p) for p in m.polygons if p.material_index==4};restores.append([r for r in hardware[lod] if r['key'] not in existing])
 m.calc_loop_triangles();tr=[t for t in m.loop_triangles if m.polygons[t.polygon_index].material_index==4 and .35<m.polygons[t.polygon_index].center.z<1.055 and abs(m.polygons[t.polygon_index].center.x)<.27];tree=BVHTree.FromPolygons([v.co for v in m.vertices],[tuple(t.vertices) for t in tr],all_triangles=True);remove=[]
 for p in m.polygons:
  co=p.center
  if p.material_index!=4 or not(.4<co.z<1.05 and abs(co.x)<.24):continue
  center=Vector((0,-.015,co.z)) if co.z>.9 else Vector((.095 if co.x>0 else -.095,-.005,co.z));radial=(co-center).normalized()
  if p.normal.dot(radial)>-.2:continue
  hit,n,fi,d=tree.ray_cast(co+radial*.025,-radial,.04)
  if hit is not None and tr[fi].polygon_index!=p.index and .0003<.025-d<.012 and n.dot(radial)>.2:remove.append(p.index)
 lining.append(remove)
 for p in m.polygons:
  if p.material_index!=4:continue
  uv=[m.uv_layers[0].data[i].uv for i in p.loop_indices];xs=[(v.x-1)*512 for v in uv];ys=[v.y*512 for v in uv];used[max(0,int(min(ys))-1):min(512,int(max(ys))+2),max(0,int(min(xs))-1):min(512,int(max(xs))+2)]=True
for y,x in json.loads((ART/'continuous_shirt_report.json').read_text())['allocated_tiles']:used[y,x]=True
needed=max(map(len,restores));free=np.argwhere(~used);assert len(free)>=needed;tiles=[tuple(map(int,v)) for v in free[:needed]]
for suffix in ['BC','N','ORM']:
 image=bpy.data.images['T_Dink_WardrobeV3_'+suffix];data=np.empty(4096*4096*4,np.float32);image.pixels.foreach_get(data);data=data.reshape(4096,4096,4);color={'BC':(.11,.125,.14,1),'N':(.5,.5,1,1),'ORM':(1,.36,1,1)}[suffix]
 for y,x in tiles:data[y*8:(y+1)*8,x*8:(x+1)*8]=color
 # Fine dielectric cloth/leather grain in the newly authored UV cells only.
 report=json.loads((ART/'continuous_shirt_report.json').read_text())
 for i,(y,x) in enumerate(report['allocated_tiles']):
  blue=i<report['shirt_faces'];yy,xx=np.mgrid[:8,:8];grain=np.sin(xx*2.1+yy*1.3+x*.4+y*.3)
  if suffix=='N':
   block=data[y*8:(y+1)*8,x*8:(x+1)*8];block[:,:,0]=.5+.009*np.sin(xx*2.1+yy*1.3);block[:,:,1]=.5+.009*np.cos(yy*2.4-xx*1.7);block[:,:,2]=.9998
  if suffix=='ORM':data[y*8:(y+1)*8,x*8:(x+1)*8,1]=(.84 if blue else .72)+grain*.025
 image.pixels.foreach_set(data.ravel());image.save()
rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];old=ob.data;verts=[tuple(v.co) for v in old.vertices];weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in old.vertices];faces=[];mis=[];uvs=[];normals=[];smooth=[]
 for p in old.polygons:
  if p.index in set(lining[lod]):continue
  faces.append(tuple(p.vertices));mis.append(p.material_index);smooth.append(p.use_smooth);uvs.extend(tuple(old.uv_layers[0].data[i].uv) for i in p.loop_indices);normals.extend(tuple(old.corner_normals[i].vector) for i in p.loop_indices)
 for row,(y,x) in zip(restores[lod],tiles):
  off=len(verts);verts.extend(row['co']);weights.extend(row['weights']);faces.append(tuple(range(off,len(verts))));mis.append(4);smooth.append(False);n=len(row['co']);normals.extend(row['normals']);uvs.extend([(1+(x*8+4+2.25*math.cos(j*math.tau/n))/4096,(y*8+4+2.25*math.sin(j*math.tau/n))/4096) for j in range(n)])
 mesh=bpy.data.meshes.new(old.name+'_HardwareRestored');mesh.from_pydata(verts,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for material in old.materials:mesh.materials.append(material)
 for p,mi,sm in zip(mesh.polygons,mis,smooth):p.material_index=mi;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for p,v in zip(uv.data,uvs):p.uv=v
 mesh.normals_split_custom_set(normals);names=[g.name for g in ob.vertex_groups];ob.data=mesh;ob.vertex_groups.clear()
 for name in names:ob.vertex_groups.new(name=name)
 for i,values in enumerate(weights):
  for name,w in values.items():ob.vertex_groups[name].add([i],w,'REPLACE')
 rows.append({'lod':lod,'original_hardware_faces_restored':len(restores[lod]),'covered_inward_trouser_lining_faces_removed':len(lining[lod])});print('HARDWARE / LINING',rows[-1],flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'hardware_lining_report.json').write_text(json.dumps({'scope':'Restore exact pre-rebuild pack/belt buckle geometry and weights into dedicated unique metallic atlas cells. Remove covered inward trouser lining faces that cast internal shadows on the outer cloth; no outward trouser faces or protected anatomy altered. Cloth grain added only in newly allocated garment cells.','lods':rows,'hardware_unique_atlas_tiles':tiles},indent=2)+'\n')
