import bpy,sys,json,math
from pathlib import Path
ART=Path('/home/artist/Repos/Dink-Smallwood/DinkRemasterUE/SourceAssets/Art/Characters/Dink/OutfitV3')
sys.path.insert(0,'/home/artist/Repos/Dink-Smallwood/Dink-Smallwood-Remaster/tools/blender')
from dinkasset.validate import uv_stats
bpy.ops.wm.open_mainfile(filepath=str(ART/'SK_Dink_OutfitV3.blend'))
rows=[]
for lod in range(4):
 ob=bpy.data.objects[f'SK_Dink_OutfitV3_LOD{lod}'];source=ob.data;polys=[p for p in source.polygons if p.material_index==4];ids=sorted({i for p in polys for i in p.vertices});mapping={v:i for i,v in enumerate(ids)}
 mesh=bpy.data.meshes.new('WardrobeModuloOneAudit');mesh.from_pydata([source.vertices[i].co for i in ids],[],[[mapping[v] for v in p.vertices] for p in polys]);uv=mesh.uv_layers.new(name='ModuloOne')
 for dst,src in zip(mesh.polygons,polys):
  for a,b in zip(dst.loop_indices,src.loop_indices):
   u,v=source.uv_layers[0].data[b].uv;uv.data[a].uv=(u-1,v)
 stats=uv_stats(mesh,max_pairs=10000000)
 zero=[p.index for p in mesh.polygons if p.area<1e-8]
 rows.append({'lod':lod,'wardrobe_modulo_one_uv_stats':stats,'zero_area_wardrobe_faces':zero})
 print('WARDROBE UV',lod,stats,'ZERO',zero,flush=True)
 assert not stats['truncated'] and stats['overlap_ratio']<1e-7 and not stats['degenerate_tris'] and not stats['tris_out_of_range'] and not zero
 bpy.data.meshes.remove(mesh)
report={'passed':True,'contract':'Wardrobe1002 minus one equals unique nonoverlapping 0..1 charts; regular Texture2D repeat. Full UV_RANGE warning is intentional and retained. No global validator changes.','lods':rows}
(ART/'wardrobe_uv_verification.json').write_text(json.dumps(report,indent=2)+'\n')
