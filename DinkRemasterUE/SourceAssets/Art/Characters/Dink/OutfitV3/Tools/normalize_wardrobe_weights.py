import bpy,json
from pathlib import Path
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];protected=len(json.loads(ob['protected_original_vertex_indices']));changed=0
 for vertex in ob.data.vertices:
  if vertex.index<protected:continue
  values=sorted(((g.group,g.weight) for g in vertex.groups if g.weight>1e-8),key=lambda v:-v[1])[:4];total=sum(w for _,w in values)
  assert total>1e-8,('Unweighted wardrobe',lod,vertex.index)
  if len(vertex.groups)<=4 and abs(total-1)<1e-6:continue
  for group in ob.vertex_groups:group.remove([vertex.index])
  for group,w in values:ob.vertex_groups[group].add([vertex.index],w/total,'REPLACE')
  changed+=1
 rows.append({'lod':lod,'normalized_wardrobe_vertices':changed})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'weight_cleanup_report.json').write_text(json.dumps(rows,indent=2)+'\n');print('WARDROBE TOP4',rows,flush=True)
