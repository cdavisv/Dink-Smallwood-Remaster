"""Write Vegetation/manifest.json from work/stats_*.json, and Vegetation/contact_sheet.png from Review/ renders."""
import json, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, '..')
TEXSETS = {
 'MI_Veg_PineBark': ('T_Veg_PineBark', ['BC', 'N', 'ORM'], ['polyhaven/pine_bark']),
 'MI_Veg_OakBark': ('T_Veg_OakBark', ['BC', 'N', 'ORM'], ['polyhaven/jolcham_oak_bark_01']),
 'MI_Veg_WillowBark': ('T_Veg_WillowBark', ['BC', 'N', 'ORM'], ['polyhaven/bark_willow']),
 'MI_Veg_PineNeedles': ('T_Veg_PineNeedles', ['BC', 'N', 'ORM', 'SSS'], []),
 'MI_Veg_OakLeaves': ('T_Veg_OakLeaves', ['BC', 'N', 'ORM', 'SSS'], ['ambientcg/LeafSet016']),
 'MI_Veg_WillowLeaves': ('T_Veg_WillowLeaves', ['BC', 'N', 'ORM', 'SSS'], []),
 'MI_Veg_GroundCover': ('T_Veg_GroundCover', ['BC', 'N', 'ORM', 'SSS'], ['ambientcg/Foliage003', 'ambientcg/LeafSet020', 'ambientcg/LeafSet022']),
 'MI_Veg_Deadwood': ('T_Veg_Deadwood', ['BC', 'N', 'ORM'], ['polyhaven/pine_bark']),
 'MI_Veg_DeadwoodEnd': ('T_Veg_DeadwoodEnd', ['BC', 'N', 'ORM'], ['ambientcg/TreeEnd003']),
 'MI_Veg_PineBarkDry': ('T_Veg_PineBarkDry', ['BC', 'N', 'ORM'], ['polyhaven/pine_bark']),
 'MI_Veg_PineNeedlesDry': ('T_Veg_PineNeedlesDry', ['BC', 'N', 'ORM', 'SSS'], []),
 'MI_Veg_CharredBark': ('T_Veg_CharredBark', ['BC', 'N', 'ORM'], ['polyhaven/pine_bark']),
 'MI_Veg_DarkBark': ('T_Veg_DarkBark', ['BC', 'N', 'ORM'], ['polyhaven/bark_willow']),
 'MI_Veg_FrostBark': ('T_Veg_FrostBark', ['BC', 'N', 'ORM'], ['polyhaven/jolcham_oak_bark_01']),
 'MI_Veg_Understory': ('T_Veg_Understory', ['BC', 'N', 'ORM', 'SSS'], ['ambientcg/LeafSet022']),
 'MI_Veg_Understory_Frost': ('T_Veg_Understory', ['BC', 'N', 'ORM', 'SSS'], ['ambientcg/LeafSet022']),
 'MI_Terrain_TransitionDirt_Tilled': (None, [], []),
 'MI_Veg_MeadowGrass': ('T_Veg_MeadowGrass', ['BC', 'N', 'ORM', 'SSS'], []),
 'MI_Veg_Shrub': ('T_Veg_Shrub', ['BC', 'N', 'ORM', 'SSS'], ['ambientcg/LeafSet022', 'ambientcg/LeafSet029']),
}
MATNOTE = {'MI_Veg_MeadowGrass': 'NEW material (12 Nov): meadow grass atlas, 2048^2 = 1.6 m square, tiles in src/meadow_layout.py; masked two-sided foliage with _SSS like MI_Veg_GroundCover; mip generation should preserve alpha coverage (threshold 0.33) or thin blades vanish with distance', 'MI_Veg_Shrub': 'NEW material (12 Nov): shrub leaf-spray atlas for the four bushes, 4 x 4 tiles of 0.5 m (two leaf types, graded light / mid / dark tiles, bare twig sprays); masked two-sided foliage with _SSS',
           'MI_Veg_Understory_Frost': 'instance of MI_Veg_Understory with base colour multiplied by about (2.6, 2.8, 3.2) (hoar frost on bare twigs), no subsurface',
           'MI_Terrain_TransitionDirt_Tilled': 'the terrain agent\'s TransitionDirt set (PhotorealPass/Terrain/TransitionDirt), 2 m world tile, tinted about (0.5, 0.44, 0.4) for damp tilled soil; UVs are world-scale and wrap'}
FAM = {
 'SM_Veg_Pine_Large_01': (['tree_pine_large'], 'SM_Pine_Stonebrook_V3'), 'SM_Veg_Pine_Medium_01': (['tree_pine_large'], 'SM_Pine_Stonebrook_V3 (size variant)'),
 'SM_Veg_Pine_Storm_01': (['tree_pine_large'], 'SM_Pine_Stonebrook_V3 (damaged variant)'),
 'SM_Veg_PineForestEdge_H_01': (['pine_forest_edge_strip'], None), 'SM_Veg_PineForestEdge_V_01': (['pine_forest_edge_strip_vert'], None),
 'SM_Veg_Oak_Large_01': (['tree_oak_large'], 'SM_Oak_Stonebrook_01'), 'SM_Veg_Oak_Large_02': (['tree_oak_large'], 'SM_Oak_Stonebrook_01 (variant)'),
 'SM_Veg_Willow_01': (['tree_willow'], 'SM_Oak_Stonebrook_01 (stand-in binding)'), 'SM_Veg_Willow_Large_01': (['tree_willow_large'], 'SM_Oak_Stonebrook_01 (stand-in binding)'),
 'SM_Veg_Grass_Meadow_01': (['grass_tall'], 'SM_Grass_Meadow_01'), 'SM_Veg_Grass_Meadow_02': (['grass_tall'], 'SM_Grass_Meadow_01'), 'SM_Veg_Grass_Meadow_03': (['grass_tall'], 'SM_Grass_Meadow_01'),
 'SM_Veg_Weed_Small_01': (['weed_small'], 'SM_Grass_Meadow_01 (stand-in binding)'), 'SM_Veg_Weed_Small_02': (['weed_small'], 'SM_Grass_Meadow_01 (stand-in binding)'),
 'SM_Veg_Weed_Sprig_01': (['weed_sprig'], None), 'SM_Veg_Flowers_01': (['flower_small', 'flower_bed_row'], None), 'SM_Veg_Flowers_02': (['flower_small', 'flower_bed_row'], None),
 'SM_Veg_Mushroom_01': (['mushroom'], None), 'SM_Veg_Mushroom_02': (['mushroom'], None),
 'SM_Veg_Stump_01': (['tree_stump'], None), 'SM_Veg_Stump_02': (['tree_stump'], None), 'SM_Veg_FallenLog_01': (['fallen_log'], None),
 'SM_Veg_FallenBranch_Forked_01': (['fallen_branch_forked'], None), 'SM_Veg_TwigCluster_01': (['twig'], None),
 'SM_Veg_Pine_Dry_01': (['tree_pine_large (scripted burnable trees: s2-sec1, s2-sec3, s3-sec1 secret scripts)'], None),
 'SM_Veg_Pine_Burnt_01': (['tree_pine_large after burning (tree fire seq 20 end state)'], None),
 'SM_Veg_DeadTree_Dark_01': (['tree_dead_dark'], None), 'SM_Veg_DeadTree_DarkTall_01': (['tree_dead_dark_tall'], None), 'SM_Veg_DeadTree_Frosted_01': (['tree_dead_frosted'], None),
 'SM_Veg_Bush_Small_01': (['bush_small'], None), 'SM_Veg_Bush_Round_Medium_01': (['bush_round_medium'], None), 'SM_Veg_Bush_Round_Large_01': (['bush_round_large'], None), 'SM_Veg_Bush_Wide_01': (['bush_wide'], None),
 'SM_Veg_ThornBush_01': (['thorn_bush'], None), 'SM_Veg_ThornBush_02': (['thorn_bush'], None), 'SM_Veg_ThornBranch_01': (['thorn_branch'], None),
 'SM_Veg_Fern_01': (['fern'], None), 'SM_Veg_Fern_02': (['fern'], None), 'SM_Veg_HangingVines_01': (['hanging_vines'], None), 'SM_Veg_HangingVines_02': (['hanging_vines'], None),
 'SM_Veg_GrassPatch_Dense_01': (['(meadow grass scatter, no sprite class)'], None), 'SM_Veg_GrassPatch_Dense_02': (['(meadow grass scatter, no sprite class)'], None), 'SM_Veg_GrassPatch_Dense_03': (['(meadow grass scatter, no sprite class)'], None),
 'SM_Veg_Cabbage_01': (['cabbage'], None),
 'SM_Veg_GrassPatch_Tall_01': ([], None),
 'SM_Veg_GrassPatch_Tall_02': ([], None),
 'SM_Veg_GrassPatch_Tall_03': ([], None),
 'SM_Veg_GrassPatch_Short_01': ([], None),
 'SM_Veg_GrassPatch_Short_02': ([], None),
 'SM_Veg_GrassPatch_Dry_01': ([], None),
 'SM_Veg_FlowerBed_Row_01': (['flower_bed_row'], None),
}
CARPET = 'engine grass carpet only: bound to NO sprite family. Instance it on grass terrain with random yaw and uniform scale 0.8-1.25 at about 0.5 m spacing with 0.2 m jitter (roots fill a 0.6-0.68 m square, the leaning tips overhang to about 1.2-1.4 m, so neighbours interlock); no collision; LOD2 is two crossed quads for the far field'
USAGE = {'SM_Veg_GrassPatch_Tall_01': CARPET, 'SM_Veg_GrassPatch_Tall_02': CARPET, 'SM_Veg_GrassPatch_Tall_03': CARPET,
         'SM_Veg_GrassPatch_Short_01': CARPET + '; grazed turf 6-12 cm for yards, path edges and pasture', 'SM_Veg_GrassPatch_Short_02': CARPET + '; grazed turf 6-12 cm, with some dry blades',
         'SM_Veg_GrassPatch_Dry_01': CARPET + '; straw-coloured, for dry / late-summer or scorched ground',
         'SM_Veg_GrassPatch_Dense_01': 'kept for compatibility; superseded for the carpet by SM_Veg_GrassPatch_Tall_01..03', 'SM_Veg_GrassPatch_Dense_02': 'kept for compatibility; superseded by SM_Veg_GrassPatch_Tall_01..03', 'SM_Veg_GrassPatch_Dense_03': 'kept for compatibility; superseded by SM_Veg_GrassPatch_Tall_01..03'}
GEN = {'meadow': 'src/veg_meadow.py', 'pine': 'src/veg_pine.py', 'broadleaf': 'src/veg_broadleaf.py', 'ground': 'src/veg_ground.py', 'deadwood': 'src/veg_deadwood.py', 'under': 'src/veg_under.py'}
def main():
    weak = json.load(open(os.path.join(HERE, 'weaknesses.json')))
    assets = []
    for g in ('pine', 'broadleaf', 'ground', 'deadwood', 'under', 'meadow'):
        st = json.load(open(os.path.join(V, 'work', f'stats_{g}.json')))
        for name, s in st.items():
            tex = []; tp = []
            for m in s['materials']:
                base, sufs, third = TEXSETS[m]; tp += third
                if base is None: tp.append('in-repo: PhotorealPass/Terrain/TransitionDirt'); continue
                for sf in sufs:
                    f = f'Export/Textures/{base}_{sf}.png'; im = Image.open(os.path.join(V, f)); tex.append(dict(file=f, size=list(im.size), material=m, role=sf))
            fam, sup = FAM[name]
            assets.append(dict(name=name, **{'class': 'prop' if g == 'deadwood' else 'foliage'}, dimensions_m=s['dimensions_m'], lod0_triangles=s['lods'][0]['triangles'],
                               lods=s['lods'], materials=s['materials'], textures=tex, families=fam, supersedes=sup, source_blend=f'Blend/VEG_{g}.blend', generator=GEN[g],
                               pivot='base_center', two_sided=[m for m in s['materials'] if 'Needles' in m or 'Leaves' in m or 'GroundCover' in m or 'MeadowGrass' in m or 'Shrub' in m or 'Understory' in m],
                               third_party=sorted(set(tp)),
                               material_exception='new foliage library materials MI_Veg_* (per-species bark bands and rendered leaf/needle atlases); the shared library had only MI_Stonebrook_OakLeaf / Oak timber, which is what made every tree read as the same stylised oak',
                               **({'usage': USAGE[name]} if name in USAGE else {}),
                               known_weaknesses=list(dict.fromkeys(weak.get(name, []) + weak.get('_' + next((k for k in ('dead', 'bush') if ('DeadTree' in name and k == 'dead') or ('Bush_' in name and k == 'bush')), g), [])))))
    man = dict(schema='dink-photoreal-vegetation/2', date='2026-11-12', pivot_note='trees and stumps: pivot at ground level at the trunk, mesh continues 0.18 m BELOW the pivot (buttress roots dive into the soil) so they sit on uneven terrain; hanging vines: pivot on the floor under them, strands hang from 2.8 m', uv_mask='second UV channel UVMask on trees and stumps: U = ground blend weight (1 at/below ground, 0 from 0.9 m up) for soil / moss darkening of the bark material; V unused', validation='work/fbx_validation.json: every FBX re-imported, triangles and size compared, non-manifold / zero-area / loose-vertex counts', unit='metre', fbx='one file per LOD (FBX_SCALE_ALL, apply_unit_scale, -Y forward, Z up, vertex colours exported LINEAR)',
               materials={m: dict(texture_set=v[0], maps=v[1], third_party=v[2], note=MATNOTE.get(m, ''), blend_mode='masked two-sided foliage (subsurface colour = _SSS)' if 'SSS' in v[1] else 'opaque',
                                  normal='OpenGL (green up); flip green on import like the rest of the library', orm='R AO, G roughness, B metallic(0)') for m, v in TEXSETS.items()},
               bark_uv_bands='bark sets are 1024x2048 with three V bands: 0-0.25 trunk base (moss/soil, not tiling in V), 0.25-0.75 trunk body, 0.75-1 limb bark; meshes split UVs at band repeats so V never leaves 0-1; U runs 0-1 around a limb and 0-2 around the thick broadleaf trunks, so the texture address mode must be WRAP in U (V can be clamp or wrap)',
               wind_vertex_colour=dict(attribute='Wind', R='trunk sway weight, linear in height (0 ground, 1 top)', G='per-branch phase 0-1', B='leaf flutter weight (0 at twig attach / wood, 1 at free card edge or blade tip)', A='branch bend weight (0 at trunk, 1 at limb tip); 0 on ground cover'),
               card_normals='card vertex normals are bent toward the outward direction from the crown centre (custom split normals in the FBX); import with normals = Import, do not recompute',
               alpha='BC alpha is coverage with colour dilated past the edge; use masked with opacity clip about 0.33 (pine needles tolerate 0.25)',
               assets=assets)
    json.dump(man, open(os.path.join(V, 'manifest.json'), 'w'), indent=1)
    print('manifest', len(assets), 'assets')
def sheet(items, cols=8, cell=(380, 380)):
    rows = (len(items) + cols - 1) // cols
    W = Image.new('RGB', (cols * cell[0], rows * (cell[1] + 26)), (24, 24, 24)); d = ImageDraw.Draw(W)
    for i, (label, f) in enumerate(items):
        x = (i % cols) * cell[0]; y = (i // cols) * (cell[1] + 26)
        p = os.path.join(V, 'Review', f)
        if os.path.exists(p):
            im = Image.open(p).convert('RGB'); im.thumbnail(cell, Image.LANCZOS); W.paste(im, (x + (cell[0] - im.width) // 2, y + (cell[1] - im.height) // 2))
        d.text((x + 6, y + cell[1] + 6), label, fill=(230, 230, 230))
    W.save(os.path.join(V, 'contact_sheet.png')); print('sheet', W.size)
if __name__ == '__main__':
    if 'manifest' in sys.argv: main()
    if 'sheet' in sys.argv:
        items = json.load(open(os.path.join(HERE, 'sheet_items.json'))); sheet(items)
