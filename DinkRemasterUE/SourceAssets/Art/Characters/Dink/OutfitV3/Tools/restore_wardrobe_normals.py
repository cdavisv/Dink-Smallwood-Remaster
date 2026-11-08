import bpy,json,math
from mathutils import Vector
from pathlib import Path
ART=Path('/home/davisc/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 mesh=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'].data;mesh.update();normals=[tuple(n.vector) for n in mesh.corner_normals];sums={};keys={}
 for face in mesh.polygons:
  if face.material_index!=4:continue
  vertices=[mesh.vertices[i].co for i in face.vertices]
  for index,li in enumerate(face.loop_indices):
   p=vertices[index];key=tuple(round(v,6) for v in p);a=(vertices[index-1]-p).normalized();b=(vertices[(index+1)%len(vertices)]-p).normalized();angle=math.acos(max(-1,min(1,a.dot(b))));sums[key]=sums.get(key,Vector())+face.normal*angle;keys[li]=key
 for li,key in keys.items():
  if sums[key].length>1e-8:normals[li]=tuple(sums[key].normalized())
 mesh.normals_split_custom_set(normals);rows.append({'lod':lod,'wardrobe_normal_weld_positions':len(sums),'protected_corner_normals_preserved':len(normals)-len(keys)})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'wardrobe_normals_report.json').write_text(json.dumps({'scope':'Restore smooth wardrobe shading across UV chart vertex splits; protected current normals retained exactly; no geometry/UV/weights/material changes','lods':rows},indent=2)+'\n');print('WARDROBE NORMALS RESTORED',rows,flush=True)
