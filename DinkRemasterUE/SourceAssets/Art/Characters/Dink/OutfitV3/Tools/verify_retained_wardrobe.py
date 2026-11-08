import bpy,json,hashlib,struct
from pathlib import Path
ART=Path('/home/davisc/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3');bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];m=ob.data;h=hashlib.sha256();count=0
 for p in m.polygons:
  if p.material_index!=4:continue
  h.update(struct.pack('<I?',len(p.vertices),p.use_smooth));count+=1
  for i,loop in zip(p.vertices,p.loop_indices):
   v=m.vertices[i];h.update(struct.pack('<3f2f',*v.co,*m.uv_layers[0].data[loop].uv))
   for name,w in sorted((ob.vertex_groups[g.group].name,g.weight) for g in v.groups):h.update(name.encode()+b'\0'+struct.pack('<f',w))
 rows.append({'lod':lod,'faces':count,'wardrobe_position_weight_face_uv_hash':h.hexdigest()})
assert len({r['wardrobe_position_weight_face_uv_hash'] for r in rows})==1,rows
(ART/'retained_wardrobe_verification.json').write_text(json.dumps({'passed':True,'candidate_sha256':hashlib.sha256((ART/'SK_Dink_OutfitV3.blend').read_bytes()).hexdigest(),'scope':'Independent reload proves all four LODs have byte-exact same verified Wardrobe face ordering/winding, positions, named weights, smooth flags and per-corner UVs. Four anatomical LODs independently frozen by scope_verification.json.','lods':rows},indent=2)+'\n');print('RETAINED WARDROBE ALL4 EXACT PASS',rows)
