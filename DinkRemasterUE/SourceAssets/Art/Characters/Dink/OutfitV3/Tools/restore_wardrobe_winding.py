import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
ART=Path('/home/davisc/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
def facekey(mesh,p):
 uv=mesh.uv_layers[0]
 return tuple(sorted(tuple(round(x,6) for x in mesh.vertices[mesh.loops[i].vertex_index].co)+tuple(round(x,8) for x in uv.data[i].uv) for i in p.loop_indices))
bpy.ops.wm.open_mainfile(filepath=str(ART/'Tools/Checkpoints/PreIntegrated.blend.snapshot'));expected=[]
for lod in range(4):
 mesh=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'].data;expected.append({facekey(mesh,p):tuple(p.normal) for p in mesh.polygons if p.material_index==4})
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mesh=ob.data;wrong=[];matched=0
 for p in mesh.polygons:
  if p.material_index!=4:continue
  old=expected[lod].get(facekey(mesh,p))
  if old is None:continue
  matched+=1
  if p.normal.dot(Vector(old))<-.5:wrong.append(p.index)
 bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table();bmesh.ops.reverse_faces(bm,faces=[bm.faces[i] for i in wrong]);bm.to_mesh(mesh);bm.free();rows.append({'lod':lod,'existing_wardrobe_faces_matched_by_exact_geometry_UV':matched,'global_recalc_winding_regressions_restored':len(wrong)})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'winding_restoration_report.json').write_text(json.dumps({'scope':'Restore exact pre-integration wardrobe face winding by geometry+UV identity; protected anatomical faces never selected. New integrated yoke faces retained.','lods':rows},indent=2)+'\n');print('WINDING RESTORED',rows,flush=True)
