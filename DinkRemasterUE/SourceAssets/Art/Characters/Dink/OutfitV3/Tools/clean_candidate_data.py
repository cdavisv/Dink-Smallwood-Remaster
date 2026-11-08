import bpy,bmesh,json
from pathlib import Path
ART=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];count=len(json.loads(ob['protected_original_vertex_indices']));bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bm.verts.index_update();loose=[v for v in bm.verts if v.index>=count and not v.link_faces]
 bmesh.ops.delete(bm,geom=loose,context='VERTS');bm.to_mesh(ob.data);bm.free();ob.data.update();rows.append({'lod':lod,'removed_unused_wardrobe_vertices':len(loose)})
for image in list(bpy.data.images):
 if not image.users and image.name.startswith('T_Dink_WardrobeV3_'):bpy.data.images.remove(image)
mat=bpy.data.materials['MI_Dink_WardrobeV3']
for node in mat.node_tree.nodes:
 if node.type=='TEX_IMAGE':node.image.name=Path(node.image.filepath).stem
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'data_cleanup_report.json').write_text(json.dumps({'scope':'Remove only unused wardrobe geometry, keep inherited protected wires; normalize new texture names only','lods':rows},indent=2)+'\n');print('CANDIDATE CLEANED',rows,flush=True)
