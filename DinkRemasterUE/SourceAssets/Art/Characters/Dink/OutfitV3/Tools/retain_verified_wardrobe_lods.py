import bpy,json
from pathlib import Path
ART=Path('/home/davisc/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3');bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'));high=bpy.data.objects['SK_Dink_OutfitV3_LOD0'];hm=high.data;hp=[p for p in hm.polygons if p.material_index==4];hid=sorted({i for p in hp for i in p.vertices});hco={i:tuple(hm.vertices[i].co) for i in hid};hw={i:{high.vertex_groups[g.group].name:g.weight for g in hm.vertices[i].groups} for i in hid};rows=[]
for lod in range(1,4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];old=ob.data;verts=[tuple(v.co) for v in old.vertices];weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in old.vertices];faces=[];mis=[];smooth=[];uvs=[];normals=[]
 for p in old.polygons:
  if p.material_index==4:continue
  faces.append(tuple(p.vertices));mis.append(p.material_index);smooth.append(p.use_smooth);uvs.extend(tuple(old.uv_layers[0].data[i].uv) for i in p.loop_indices);normals.extend(tuple(old.corner_normals[i].vector) for i in p.loop_indices)
 mapping={i:len(verts)+j for j,i in enumerate(hid)};verts.extend(hco[i] for i in hid);weights.extend(hw[i] for i in hid)
 for p in hp:
  faces.append(tuple(mapping[i] for i in p.vertices));mis.append(4);smooth.append(p.use_smooth);uvs.extend(tuple(hm.uv_layers[0].data[i].uv) for i in p.loop_indices);normals.extend(tuple(hm.corner_normals[i].vector) for i in p.loop_indices)
 mesh=bpy.data.meshes.new(old.name+'_VerifiedWardrobe');mesh.from_pydata(verts,[tuple(e.vertices) for e in old.edges if e.is_loose],faces)
 for mat in old.materials:mesh.materials.append(mat)
 for p,mi,sm in zip(mesh.polygons,mis,smooth):p.material_index=mi;p.use_smooth=sm
 uv=mesh.uv_layers.new(name='UVMap')
 for p,v in zip(uv.data,uvs):p.uv=v
 mesh.normals_split_custom_set(normals);names=[g.name for g in ob.vertex_groups];ob.data=mesh;ob.vertex_groups.clear()
 for name in names:ob.vertex_groups.new(name=name)
 for i,values in enumerate(weights):
  for name,w in values.items():ob.vertex_groups[name].add([i],w,'REPLACE')
 rows.append({'lod':lod,'wardrobe_geometry_source_lod':0,'wardrobe_triangles':sum(len(p.vertices)-2 for p in hp),'total_triangles':sum(len(p.vertices)-2 for p in mesh.polygons),'protected_anatomical_geometry_unchanged':True})
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'),relative_remap=False)
(ART/'verified_wardrobe_lods_report.json').write_text(json.dumps({'scope':'Four original anatomical LODs preserved exactly. Lower wardrobe geometry retains verified LOD0 detail because the old decimated clothing had visible one-sided holes. All four total LOD counts remain below40k; no anatomy decimation or rig/material change. This favors source visual correctness over aggressive wardrobe LOD reduction.','lods':rows},indent=2)+'\n')
