# Shared photoreal PBR material library

Sixteen seamlessly tileable terrain, building and dungeon materials for regions beyond Stonebrook (Terris, Windemere, Joppa, wilderness, caves and dungeons, the snow isle, beaches and the Darklands). All are original procedural work (Python, numpy and Pillow only; no downloaded images, no generative image models). Status: art candidates, human art approval pending. Nothing here is imported into Unreal and `asset_ledger.csv` is untouched: the proposed rows are in `ledger_rows_proposed.csv`.

## Files

Per material `X`, at 2048 px (`Textures/2048/`, master) and 1024 px (`Textures/1024/`, 2x box-filtered from the master with the normal rebuilt from the filtered height):

| File | Content | Colour space |
|---|---|---|
| `T_Shared_X_BC.png` | base colour, RGBA 8-bit, alpha opaque | sRGB |
| `T_Shared_X_N.png` | tangent-space normal, **OpenGL** (green up), same as the Stonebrook kit; flip green on Unreal import and use the reduced XY strength (about 0.35) the existing bridge uses | linear |
| `T_Shared_X_ORM.png` | R = ambient occlusion (height-cavity bake), G = roughness, B = metallic (always 0, all non-metals) | linear mask |
| `T_Shared_X_H.png` | height, 16-bit greyscale; 0..65535 spans `height_range_m` in the manifest (metres, so displacement or parallax can be scaled physically) | linear |

Other outputs: `manifest.json` (files, colour spaces, tile size in metres, texel density, height range, albedo and seam stats, SHA-256, intended region and tile classes), `Previews/X_preview.png` (left: lit 2x2 repeat of the 1024 tile; right: lit sphere, albedo crop, normal crop), `contact_sheet.png` (all lit), `tiling_check.png` (every tile rolled by half so the wrap seams cross at the centre of each cell), `repeat_check_2x2.png` (albedo repeated 2x2), `albedo_report.json`, `ledger_rows_proposed.csv` (128 rows, exact ledger columns; 2048 masters have a proposed `Content/Dink/Textures/Shared/` derived path, 1024 variants have none), `tools/`.

## Materials

Texel columns are millimetres per pixel at 2048 / 1024. Tile size is the real-world edge of one repeat. Albedo columns are luma on the saved 2048 BC.

| Material | Tile | mm/px | Albedo luma | Intended region |
|---|---|---|---|---|
| CobbleStreet | 2 m | 0.98 / 1.95 | 34-209 (mean 94), max channel 222 | Terris, Windemere, Joppa Isle and Goodheart Castle street paving |
| DirtRoadRuts | 3 m | 1.47 / 2.93 | 33-174 (mean 84), max channel 203 | Cart roads between towns: Terris wilds, Windemere wilds, KernSin wilds, South coast road |
| ForestFloor | 2 m | 0.98 / 1.95 | 32-123 (mean 63), max channel 158 | Murkwood and the cult woods, forest_canopy under-layer, Terris wilds |
| WetSand | 2 m | 0.98 / 1.95 | 33-226 (mean 94), max channel 238 | South coast, Joppa Isle shoreline, West Seas beaches, Koka Isle shore |
| BeachPebbles | 1 m | 0.49 / 0.98 | 33-233 (mean 114), max channel 238 | Shingle beaches and sand/gravel transitions on the South coast, Koka Isle and Joppa |
| MossyCaveRock | 2 m | 0.98 / 1.95 | 34-232 (mean 118), max channel 238 | Cave walls and floors: Hellfire cave, Joppa tunnel, Edge of the World caves |
| DungeonMasonry | 2 m | 0.98 / 1.95 | 33-172 (mean 83), max channel 180 | Snow castle, Goodheart Castle hall, Goblin Sanctuary and other dungeon wall faces |
| DungeonFlagstone | 2 m | 0.98 / 1.95 | 32-236 (mean 92), max channel 237 | Castle, dungeon and cellar floors |
| DarklandsSoil | 2 m | 0.98 / 1.95 | 32-161 (mean 65), max channel 174 | Darklands wasteland ground |
| SnowFresh | 2 m | 0.98 / 1.95 | 200-236 (mean 224), max channel 238 | Snow castle isle open ground |
| SnowTrampled | 2 m | 0.98 / 1.95 | 102-230 (mean 201), max channel 234 | Snow castle isle paths, doorways and gate approaches |
| CliffRock | 4 m | 1.95 / 3.91 | 32-222 (mean 103), max channel 238 | Cliff faces everywhere: mainland cliffs, Edge of the World plateau, East Wilds |
| TimberPlanks | 2 m | 0.98 / 1.95 | 32-196 (mean 90), max channel 211 | Weathered plank cladding and floors for Terris, Windemere and Joppa buildings, docks, bar interior |
| RoofSlate | 2 m | 0.98 / 1.95 | 32-179 (mean 73), max channel 189 | Slate roofs: Goodheart Castle, Terris town hall and well-off houses |
| RoofShingles | 2 m | 0.98 / 1.95 | 32-208 (mean 90), max channel 231 | Wooden shingle roofs: Windemere and Joppa houses, Terris outbuildings |
| BrickWall | 2 m | 0.98 / 1.95 | 32-195 (mean 98), max channel 238 | Terris and Windemere brick town buildings and chimneys |

Region choices follow `tools/analyse/regions.toml` and the terrain classes in `tools/data/tile_classes.csv` (path, gravel, dirt, sand, snow, cliff_face, cave_wall/cave_floor, stone_floor, wasteland, structure_facade, wood_floor, forest_canopy); the per-material `tile_classes` field is in the manifest. Not covered, by design: lava (needs emission), water and ice (need translucency and a dedicated material), grass (Stonebrook Meadow exists), chasm.

## Regenerate

From the repository root or the Unreal project directory (about 10-15 minutes, single process):

```bash
python3 DinkRemasterUE/SourceAssets/Art/SharedMaterials/tools/build_shared_materials.py            # all 16, previews, sheets, manifest, ledger rows, audit
python3 DinkRemasterUE/SourceAssets/Art/SharedMaterials/tools/build_shared_materials.py --only BrickWall,SnowFresh
python3 DinkRemasterUE/SourceAssets/Art/SharedMaterials/tools/build_shared_materials.py --check     # re-audit PNGs on disk (albedo range), exit 1 on failure
```

Each material has a fixed seed (`sm_materials.REGISTRY`, 2101-2116). Output is deterministic: two full runs gave identical PNG hashes. `sm_lib.py` is the toolkit (periodic FFT noise, wrapped Voronoi, oriented splats, ragged-row layouts, height-to-normal, cavity AO), `sm_materials.py` the recipes, `sm_preview.py` the numpy GGX preview renderer.

## Method and checks

- Tileability is structural: all noise is FFT-filtered (periodic), warps and lookups wrap, and every layout (brick courses, planks, shingles, masonry, Voronoi grids) closes exactly over the tile. A real bug of this kind (butt joints at the wrap) was found and fixed during review with the half-rolled sheet; the current `tiling_check.png` shows no seam at the centre crosses. The numeric `seam_ratio_*` values in the manifest are only indicative: for course-based materials the wrap edge is itself a course boundary, so the wrap difference legitimately exceeds the average neighbour difference.
- Albedo gate (`--check`, run on the saved 8-bit PNGs): no luma below 30, no channel above 240, for both sizes. Result: PASS for all 32 files (minimum luma 32.1, maximum channel 238; darkest materials are ForestFloor, RoofSlate, DarklandsSoil with 2 percent or less of pixels within 2 luma of the floor). The recipes target plausible ranges (fresh snow 200-236, brick, stone and soil 32-215) and a smooth soft-knee limiter in `fit_albedo` enforces the floor and ceiling; it never clips hard.
- Macro plus micro variation in every material (per-unit colour and height variation, mottling, grime, wear, moss or lichen where plausible, millimetre grain in the normal), roughness varied with wetness, wear and material.

## Revision 2 (realism pass, 8 Nov 2026)

- **CliffRock, MossyCaveRock:** the Voronoi "jigsaw" is gone. Rock is now built from beds of random thickness (cliff 13 beds of 0.10-0.80 m, cave 10), each cut by oblique, skewed joints into angular blocks (`bedded_blocks`), with joint gaps that open and close along their length, extra straight oblique crack sets (integer-vector joint planes), per-bed recess and erosion rounding (soft beds round off, hard beds stay crisp), chipped corners that show paler fresh fracture, and per-bed rock types (13 beds draw from 9 strata colours, so a 2x2 repeat no longer shows one dominant band). The cave also has calcite veins, quartz flecks and pitting; moss is now driven by height curvature, a cavity (AO-like) term and up-facing slope, so it fills crevices and sits on top surfaces.
- **DarklandsSoil:** a dry cracked crust with straight-sided plates (low warp), narrow irregular cracks, a hairline secondary crack network, curled and chipped plate edges, surface crazing and blistering, ash settled in cracks, hollows and wind streaks, and angular scoria cinders (small and large clinkers, dark to oxide-red, glassy roughness).
- **DungeonFlagstone:** laminae, quartz and mica flecks, dark grains, iron blooms, chipped joint edges, and walking-path wear (two worn paths that run through the tile: lighter, polished, dished, lower roughness; dusty and grimy elsewhere).
- **RoofSlate:** cleavage laminae with terraced delamination steps, mica and quartz flecks, thin straight quartz veins, iron stain, chipped and spalled free edges showing paler fresh rock, muted palette.
- **WetSand:** two sharp-crested ripple trains blended by a low-frequency mask, drainage rills, wet/dry now derived from height (crests dry, troughs stay wet) instead of free blotches, whole bivalves with growth rings, angular shell fragments, each in a small sand pile.

## Quality notes (honest)

- These read as lit, photographic-style surfaces in the previews, but they are procedural: expect to see the generator in places. Strongest: CobbleStreet, BeachPebbles, BrickWall, TimberPlanks, ForestFloor, DirtRoadRuts, SnowTrampled, RoofSlate, CliffRock.
- Remaining weak spots: MossyCaveRock reads pale (wet limestone albedo around 118 mean) and its extra oblique cracks are slightly too uniformly dark; CliffRock joints are straight but still more regular than a real cliff, and its bed colours are fairly saturated; DarklandsSoil plates are still a recognisable Voronoi family of similar size (large-scale size variation is limited); DungeonFlagstone and DungeonMasonry joints wobble slightly and the flags have a regular brick-like layout; WetSand shells are small sprites with simple ribs and the dry patches still have a similar size; mineral flecks are millimetre scale and soften at 1024.
- Height is baked into ORM AO only as a cavity term, not a full ray-traced AO; macro occlusion in Unreal will come from lighting.
- Previews are a numpy approximation (one directional light, GGX specular, no shadows), not Unreal renders. Nothing was verified in the engine. Snow previews clip because the preview exposure is fixed.
- BC/N/ORM are RGBA with opaque alpha to match the existing Stonebrook textures; H is 16-bit greyscale.
- Size: `Textures/2048` is about 411 MB and the whole texture set 527 MB (PNG). Consider keeping only the 1024 variants in Git LFS until a region actually needs 2048.
- Suggested real-world scale in Unreal: world tile = `tile_size_m` x 100 cm; the original game's 50 px tile is 1.25 m before region scaling (see `regions.toml`), so a 2 m material covers about 1.6 original tiles.
