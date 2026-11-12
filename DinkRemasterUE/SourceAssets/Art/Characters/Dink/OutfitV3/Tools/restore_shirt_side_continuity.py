import bpy,json,math
from pathlib import Path
from mathutils import Vector
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3');bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));cache=json.loads((ART/'Tools/Checkpoints/ContinuousShirtGeometry.json').read_text());r=json.loads((ART/'continuous_shirt_report.json').read_text());assert len(cache['faces'])==r['shirt_faces'];tiles={tuple(v):i for i,v in enumerate(r['allocated_tiles'])};rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];old=ob.data;present=set();shirtids=set()
 for p in old.polygons:
  if p.material_index!=4:continue
  uv=sum((old.uv_layers[0].data[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.vertices);index=tiles.get((int(uv.y*4096)//8,int((uv.x-1)*4096)//8),-1)
  if 0<=index<r['shirt_faces']:present.add(index);shirtids.update(p.vertices)
 empty_tiles=sorted(set(range(r['shirt_faces']))-present);existing_face_keys={tuple(sorted(tuple(round(v,6) for v in old.vertices[i].co) for i in p.vertices)) for p in old.polygons if p.material_index==4};missing=[f for f,face in enumerate(cache['faces']) if sum(cache['vertices'][i][2] for i in face)/len(face)<1.275 and abs(sum(cache['vertices'][i][0] for i in face)/len(face))<.21 and tuple(sorted(tuple(round(v,6) for v in cache['vertices'][i]) for i in face)) not in existing_face_keys];assert missing and len(missing)<=len(empty_tiles),(len(missing),len(empty_tiles));tile_for_face=dict(zip(missing,empty_tiles))
 verts=[tuple(v.co) for v in old.vertices];weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in old.vertices];faces=[tuple(p.vertices) for p in old.polygons];mis=[p.material_index for p in old.polygons];smooth=[p.use_smooth for p in old.polygons];uvs=[tuple(v.uv) for v in old.uv_layers[0].data];normals=[tuple(v.vector) for v in old.corner_normals];existing={tuple(round(v,6) for v in old.vertices[i].co):i for i in shirtids};mapping={};shared=0
 for idx in sorted({v for f in missing for v in cache['faces'][f]}):
  point=Vector(cache['vertices'][idx]);key=tuple(round(v,6) for v in point)
  if key in existing:mapping[idx]=existing[key];shared+=1
  else:
   # Gradually tuck only hidden interior torso vertices; the existing side seam stays exact.
   co=point.copy();amount=max(0,min(1,(1.275-co.z)/.09));co.y*=1-.40*amount;co.x*=1-.12*amount;mapping[idx]=len(verts);verts.append(tuple(co));weights.append(cache['weights'][idx])
 for index in missing:
  src=cache['faces'][index];face=tuple(mapping[i] for i in src);faces.append(face);mis.append(4);smooth.append(True);iy,ix=r['allocated_tiles'][tile_for_face[index]];n=len(face);uvs.extend([(1+(ix*8+4+2.25*math.cos(j*math.tau/n))/4096,(iy*8+4+2.25*math.sin(j*math.tau/n))/4096) for j in range(n)]);a,b,c=[Vector(verts[i]) for i in face[:3]];normal=(b-a).cross(c-a).normalized();normals.extend([tuple(normal)]*n)
 mesh=bpy.data.meshes.new(old.name+'_ClosedSides');mesh.from_pydata(verts,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for mat in old.materials:mesh.materials.append(mat)
 for p,mi,sm in zip(mesh.polygons,mis,smooth):p.material_index=mi;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for p,v in zip(uv.data,uvs):p.uv=v
 mesh.normals_split_custom_set(normals);names=[g.name for g in ob.vertex_groups];ob.data=mesh;ob.vertex_groups.clear()
 for name in names:ob.vertex_groups.new(name=name)
 for i,values in enumerate(weights):
  for name,w in values.items():ob.vertex_groups[name].add([i],w,'REPLACE')
 rows.append({'lod':lod,'restored_continuous_torso_faces':len(missing),'exact_shared_side_boundary_vertices':shared})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'shirt_side_continuity_report.json').write_text(json.dumps({'scope':'Restore the deterministic generated torso faces removed by the earlier hidden-waist trim. Existing side boundary vertices are shared exactly; lower hidden interior vertices tuck inside the jerkin. New shirt only; protected anatomy/materials/rig unchanged.','lods':rows},indent=2)+'\n')
