import bpy,bmesh,json
from pathlib import Path
ART=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3');report=json.loads((ART/'strap_attachment_report.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'))
for row in report['lods']:
 ob=bpy.data.objects[f"SK_Dink_OutfitV3_LOD{row['lod']}"];bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=list(bm.faces)[-row['continuous_leather_join_quads']:],context='FACES_ONLY');unused=[v for v in bm.verts if not v.link_faces and v.index>=len(ob.data.vertices)-row['new_join_vertices']];bmesh.ops.delete(bm,geom=unused,context='VERTS');bm.to_mesh(ob.data);bm.free()
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
