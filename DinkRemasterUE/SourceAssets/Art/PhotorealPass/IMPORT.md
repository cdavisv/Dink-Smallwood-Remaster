# Photoreal pass: importing into Unreal

All commands run from `DinkRemasterUE/`, headless, and are re-runnable. A re-export from an art agent is picked up by file size and modification time; nothing else is re-imported.

| What | Command | Reads | Writes |
|---|---|---|---|
| Terrain layers, water, backdrop and fire materials | `Scripts/import_environment_materials.sh` (`DINK_ENV_MATERIALS_ONLY=1` rebuilds the material graphs without touching textures) | `Terrain/manifest.json`, `Environment/terrain_layers.json` | `/Game/Dink/Materials/Environment`, `/Game/Dink/Textures/Environment` |
| Vegetation, scatter stones, photoreal hero | `Scripts/import_photoreal_art.sh` (`DINK_PHOTOREAL_ONLY=vegetation,scatter,hero` limits it) | `Vegetation/manifest.json`, `Terrain/manifest.json` (`scatter_meshes`; the allowed names are `SCATTER_ALLOW` in the script), `Characters/Dink/manifest.json` | `/Game/Dink/Photoreal/{Vegetation,Scatter,Characters/Dink}`; report `Saved/PhotorealPass/import_photoreal.json` |
| Town-house kit (materials from the manifest's `integration` contract, 14 modules; refuses while an FBX is newer than the manifest) | `Scripts/import_town_exteriors.sh` | `TownExteriors/manifest.json` | `/Game/Dink/Photoreal/TownExteriors`; report `Saved/PhotorealPass/import_town.json` |
| Ground colour grid for trunk feet | `python3 -I Scripts/export_ground_colour.py` (after a world export or a terrain texture change) | `ImportData/screens.json`, `ImportData/ground_mask`, `Terrain/*/T_Terrain_*_BC.png` | `Content/Dink/Data/Environment/ground_colour.json` |
| World (ground masks, per-screen terrain and water instances, sky, backdrop) | `Scripts/import_greybox.sh --region all --export` | the two above, `tools/data/tile_classes.csv` | `/Game/Dink/_Generated`, `Content/Dink/Data/Environment/layer_cover.json` |

Order after a terrain change: environment materials, then the world. Vegetation, scatter and hero are independent of the world import: they are bound at runtime.

## What binds the imports at runtime

- **Sprite families:** `Content/Dink/Data/Art/families.json`. A row's `mesh` is the family's mesh; optional `variants` lists further meshes and each placement picks one by a stable hash of its origin ID (visual only, no collision). Check with `python3 -I Scripts/art_coverage.py` and `python3 -I Scripts/art_standard_check.py`.
- **Grass scatter:** `Content/Dink/Data/Environment/environment.json` (`grass.meshes`, density, scale, radius). Console: `dink.GrassDensity <multiplier>`.
- **Hero:** `SK_Dink_Photoreal` replaces the manifest's player mesh while `dink.PhotorealHero` is 1 (the default) and the process renders; `-dpcvars=dink.PhotorealHero=0` on the command line restores the previous hero. Same skeleton, animation blueprint, capsule and sockets. Headless tests always use the mesh of `characters.json`.
- **Wind:** vegetation materials read the `Wind` scalar of `/Game/Dink/Photoreal/Vegetation/MPC_Dink_Environment`; `dink.Wind 0` stills it.
- **Terrain and water on authored meshes:** `dink.EnvMaterials 0` (command line) restores the authored materials.

- **Sequence-and-frame family rows:** a `families.json` row whose family starts with a sequence number may carry `frame`: it binds that one picture and wins over class rows (curved dungeon wall per corner, half strip, left and right door jambs). `anchor_front` (0..1) stands a deep module's front edge on the sprite's bottom edge.
- **Indoor set:** `environment.json` `indoor` (UDinkEnvironmentSubsystem): hidden shadow-casting shell, black inward backdrop, lights at fire sprites, lamps or wall torches, fixed exposure, dungeon fog. Console: `dink.IndoorEnv 0|1`, `dink.IndoorLight <x>`, `dink.IndoorEV <ev>`. Screens of `skip_screens` and screens an art manifest dresses keep their own lighting.
- **Burnable pines:** `environment.json` `burnable`: dry pine before, burnt pine under the fire card while the DinkC script plays the burn sequence, the card alone once the script swaps the picture.
- **Trunk feet:** bark materials blend their foot (UVMask) toward `GroundColour`, custom primitive data 0-2, written by the family layer from `ground_colour.json`.
- **Texture import caps:** `Content/Dink/Data/Art/texture_import_caps.json` (read by the importer and by `Scripts/art_standard_check.py`).

## Calibration against the Cycles review renders

`Saved/PhotorealPass/lighting/tools/cal.sh <tag> [--only oak,pine,willow,bush,grassgrid,carpet,carpetgame,plaster,dungeon] [--var name='cmd;cmd' ...]` rebuilds the Blender review cameras and sun on the empty meadow screen 299 (`dink.CalAnchor`, `dink.CalSpawn`, `dink.CalCam`; `dink.MatParam <material part> <parameter> <value> [g b]` overrides a material parameter live, so one session captures several candidates). `cal_compare.py <tag>` prints mean and percentile RGB of the foliage against the reference render. The values it led to are `FOLIAGE_LOOK` in `Scripts/import_photoreal_art.py`.

## Conventions the importer applies

- Normal maps are OpenGL (green up): green is flipped on import.
- Vegetation meshes import their normals (bent card normals are kept), three explicit LOD files each, vertex colours as the wind weights (R trunk sway, G phase, B leaf flutter, A branch bend), Nanite off.
- Foliage materials: masked, two-sided foliage shading, specular 0.10-0.25, subsurface colour = `_SSS` map x tint x 0.1, crown interior shade (branch-bend vertex alpha, depth in the mesh bounds, inner card faces) in colour, subsurface and AO, alpha clip 0.33 (pine needles 0.25), alpha-coverage-preserving mips. No dithered opacity (it turns crowns to stipple under TSR).
- Wall kit and scatter FBX files import their vertex colours (the 'Grime' weights); the plaster and masonry hand-over to their second texture set is height-aware, as in the kit's Blender material.
- Scatter FBX files hold two plain objects (`_LOD0`, `_LOD1`); they become one mesh with two LODs.
- Hero: imported with its own skeleton, checked against the shared 89-bone rig by the native bind-pose gate, then assigned to the shared skeleton; four LODs; skin uses a subsurface profile (`SP_Dink_PR_Skin`), hair is masked two-sided with dithered opacity.

## Captures

`Saved/PhotorealPass/lighting/tools/round.sh <name> [--extra]` renders the fixed review cameras offscreen (no display, no input) into `Saved/PhotorealPass/lighting/<name>/`; `--extra` adds the in-game art cameras. Set `DINK_CAPTURE_DIR` to redirect the output folder.

## Round 5 additions (12 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Stonebrook structures (cottage, burnt cottage, fence, well, boulders) | `DINK_KIT=Structures/Stonebrook DINK_KIT_FOLDER=Structures Scripts/import_town_exteriors.sh` | `Structures/Stonebrook/manifest.json` | `/Game/Dink/Photoreal/Structures` |
| Props kit (36 meshes, light props included) | `DINK_KIT=Props DINK_KIT_FOLDER=Props Scripts/import_town_exteriors.sh` | `Props/manifest.json` (`assets`, FBX paths from the repository root) | `/Game/Dink/Photoreal/Props`; report `Saved/PhotorealPass/import_props.json` |
| Only vegetation that is not imported yet (a partial re-export is in progress) | `DINK_PHOTOREAL_ONLY=vegetation DINK_PHOTOREAL_FROZEN=1 Scripts/import_photoreal_art.sh` | `Vegetation/manifest.json` | new meshes and textures only; materials are rebuilt |
| Lit sprite card and flame materials of the indoor set | `Scripts/import_indoor_materials.sh` | - | `/Game/Dink/Photoreal/WallKits/M_Env_SpriteLit`, `M_Env_Flame` |
| Town houses per screen (offline, no editor) | `python3 -I Scripts/assemble_town_houses.py` | `ImportData/placements.json` | `Content/Dink/Data/Art/town_houses.json` |

- **LOD sections are mapped by slot name** in `import_town_exteriors.py` and in `import_scatter` (scatter stones, wall kits). Each LOD object of a kit FBX lists its materials in its own order; copied by index, LOD1/LOD2 showed other materials at a distance (oak as rope, plaster as oak).
- **Grass roles** (`environment.json` `grass`): `preferred_meshes` Tall = the field, `short_meshes` where worn, grazed or at the carpet's brink, `dry_meshes` in drifts (`dry_share`), `rank_meshes` within `rank_reach_cm` of fences, walls, trunks, boulders and pond rims; wear within `wear_reach_cm` of warps (doors) and authored earth paths; `accent_cluster` is the drift threshold of weeds and flowers. `MI_Veg_MeadowGrass_Scatter` is the carpet twin of the new patches. Wind has travelling gusts.
- **Indoor set**: `indoor.lit_card_material` relights static sprite cards and follows animated ones frame by frame (`dink.IndoorLitCards 0` turns it off); `indoor.props` puts `SM_Prop_Lantern_Hanging_01` at interior lamps and `SM_Prop_Torch_Wall_01` at dungeon wall lamps, each with a flame card (`indoor.flame_material`).
- **State swaps** (`environment.json` `state_swaps`): the swapped-in cottage of screen 439 shows `SM_Cottage_Stonebrook_PR_Burnt` while a placement gated by `&vision` 2 is shown (after the fire); `dink.StateSwaps 0` turns it off. Read-only.
- **Town houses**: `dink.TownHouses 0` (command line) keeps the sprite cards.
- **Calibration of structures**: `Saved/PhotorealPass/lighting/tools/cal2_script.py` + `cal2_compare.py` (patches in `cal2_patches.json`).
- **Scripted walking in captures**: `dink.WalkTo <mapx> <mapy> [seconds]`.
