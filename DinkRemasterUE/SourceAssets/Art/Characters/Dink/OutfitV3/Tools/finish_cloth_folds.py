import bpy,json,math
from pathlib import Path
from mathutils import Vector
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));r=json.loads((ART/'continuous_shirt_report.json').read_text());tiles={tuple(v):i for i,v in enumerate(r['allocated_tiles'])};rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];m=ob.data;shirt=[]
 for p in m.polygons:
  if p.material_index!=4:continue
  uv=sum((m.uv_layers[0].data[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.vertices);i=tiles.get((int(uv.y*4096)//8,int((uv.x-1)*4096)//8),-1)
  if 0<=i<r['shirt_faces']:shirt.append(p)
 edges={}
 for p in shirt:
  for a,b in zip(p.vertices,list(p.vertices[1:])+[p.vertices[0]]):edges[tuple(sorted((a,b)))]=edges.get(tuple(sorted((a,b))),0)+1
 boundary={i for e,n in edges.items() if n==1 for i in e};ids={i for p in shirt for i in p.vertices};maximum=0;moved=0
 for i in ids-boundary:
  co=m.vertices[i].co;disp=Vector((0,0,0))
  for side in [-1,1]:
   a=Vector((side*.190,.02557,1.43583));b=Vector((side*.35007,.01907,1.20892));c=Vector((side*.47768,-.15699,1.04467));axis=(c-b).normalized();inside=((a-b).normalized()+(c-b).normalized()).normalized();axial=(co-b).dot(axis);center=b+axis*axial;radial=(co-center).normalized();distance=(co-b).length
   if side*co.x>.26 and distance<.125:
    compression=.25+.75*max(0,radial.dot(inside));amount=.0022*math.sin(axial*math.tau/.027+radial.dot(Vector((0,1,0)))*.7)*math.exp(-(distance/.075)**2)*compression;disp+=radial*amount
  if abs(co.x)<.14 and 1.425<co.z<1.515:
   angle=math.atan2(co.y-.015,co.x);radial=Vector((co.x,co.y-.015,0)).normalized();amount=.0010*math.cos(angle*11+(co.z-1.47)*95)*math.exp(-((co.z-1.47)/.046)**2);disp+=radial*amount
  if disp.length>1e-6:co+=disp;moved+=1;maximum=max(maximum,disp.length)
 rows.append({'lod':lod,'new_cloth_vertices_with_small_elbow_collar_folds':moved,'maximum_displacement_m':maximum,'contact_and_neck_boundary_vertices_unchanged':len(boundary)})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'cloth_fold_report.json').write_text(json.dumps({'scope':'Small sewn-cloth compression folds, maximum2.2mm, only on new shirt. Existing cuff/neck boundaries, leather bands, all protected anatomy/weights/UV/materials and rig unchanged.','lods':rows},indent=2)+'\n')
