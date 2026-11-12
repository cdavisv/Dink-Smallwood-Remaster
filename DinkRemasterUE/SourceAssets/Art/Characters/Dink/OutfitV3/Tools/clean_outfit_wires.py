import bpy,bmesh,json
from pathlib import Path
ART=Path('<HOME>/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART.parent/'HandBindingV2/SK_Dink_Hands.blend'))
sourcewires=[]
for lod in range(4):
 mesh=bpy.data.objects[f'SK_Dink_Hands_LOD{lod}'].data;sourcewires.append({tuple(sorted(e.vertices)) for e in mesh.edges if e.is_loose})
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];mapping=json.loads(ob['protected_original_vertex_indices']);bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bm.verts.index_update();oldids={v:mapping[v.index] for v in bm.verts if v.index<len(mapping)}
 remove=[e for e in bm.edges if not e.link_faces and (not all(v in oldids for v in e.verts) or tuple(sorted(oldids[v] for v in e.verts)) not in sourcewires[lod])]
 bmesh.ops.delete(bm,geom=remove,context='EDGES');unused=[v for v in bm.verts if not v.link_faces and not v.link_edges];bmesh.ops.delete(bm,geom=unused,context='VERTS')
 retained=[oldids[v] for v in bm.verts if v in oldids];bm.to_mesh(ob.data);bm.free();ob['protected_original_vertex_indices']=json.dumps(retained)
 rows.append({'lod':lod,'removed_new_wardrobe_wires':len(remove),'preserved_original_wires':len(sourcewires[lod])})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'wire_cleanup_report.json').write_text(json.dumps(rows,indent=2)+'\n');print('WIRE CLEANUP',rows,flush=True)
