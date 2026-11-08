import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
ART=Path('/home/davisc/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));records=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mesh=ob.data;bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table();todo={f for f in bm.faces if f.material_index==4};remove=[];smoothed=0
 while todo:
  seed=next(iter(todo));stack=[seed];component=set()
  while stack:
   face=stack.pop()
   if face in component:continue
   component.add(face)
   for vertex in face.verts:
    stack.extend(f for f in vertex.link_faces if f.material_index==4 and f not in component)
  todo-=component;verts={v for f in component for v in f.verts};low=[min(v.co[i] for v in verts) for i in range(3)];hi=[max(v.co[i] for v in verts) for i in range(3)]
  if len(component)<100 and low[2]>1.44 and hi[2]<1.56 and hi[0]-low[0]<.075 and hi[1]-low[1]<.075 and abs((low[0]+hi[0])/2)<.19:remove.extend(component)
  if hi[0]-low[0]>.7 and .8<low[2]<1.05 and hi[2]>1.45:
   region=[v for v in verts if v.co.z>1.435 and abs(v.co.x)<.20 and -.13<v.co.y<.13]
   for iteration in range(10):
    values={v:v.co.lerp(sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges),.4) for v in region if v.link_edges}
    for v,co in values.items():v.co=co
   smoothed=len(region)
 bmesh.ops.delete(bm,geom=list(set(remove)),context='FACES_ONLY');bm.to_mesh(mesh);bm.free();mesh.update();records.append({'lod':lod,'removed_collar_fragment_faces':len(set(remove)),'smoothed_shirt_opening_vertices':smoothed})
print('COLLAR CLEANUP',records,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'collar_cleanup_report.json').write_text(json.dumps({'scope':'Wardrobe-only old trim fragment cleanup and shirt opening relaxation; protected anatomy untouched, unique UVs retained','lods':records},indent=2)+'\n')
