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

`Scripts/PhotorealQA/cal.sh <tag> [--only oak,pine,willow,bush,grassgrid,carpet,carpetgame,plaster,dungeon] [--var name='cmd;cmd' ...]` rebuilds the Blender review cameras and sun on the empty meadow screen 299 (`dink.CalAnchor`, `dink.CalSpawn`, `dink.CalCam`; `dink.MatParam <material part> <parameter> <value> [g b]` overrides a material parameter live, so one session captures several candidates). `cal_compare.py <tag>` prints mean and percentile RGB of the foliage against the reference render. The values it led to are `FOLIAGE_LOOK` in `Scripts/import_photoreal_art.py`.

## Conventions the importer applies

- Normal maps are OpenGL (green up): green is flipped on import.
- Vegetation meshes import their normals (bent card normals are kept), three explicit LOD files each, vertex colours as the wind weights (R trunk sway, G phase, B leaf flutter, A branch bend), Nanite off.
- Foliage materials: masked, two-sided foliage shading, specular 0.10-0.25, subsurface colour = `_SSS` map x tint x 0.1, crown interior shade (branch-bend vertex alpha, depth in the mesh bounds, inner card faces) in colour, subsurface and AO, alpha clip 0.33 (pine needles 0.25), alpha-coverage-preserving mips. No dithered opacity (it turns crowns to stipple under TSR).
- Wall kit and scatter FBX files import their vertex colours (the 'Grime' weights); the plaster and masonry hand-over to their second texture set is height-aware, as in the kit's Blender material.
- Scatter FBX files hold two plain objects (`_LOD0`, `_LOD1`); they become one mesh with two LODs.
- Hero: imported with its own skeleton, checked against the shared 89-bone rig by the native bind-pose gate, then assigned to the shared skeleton; four LODs; skin uses a subsurface profile (`SP_Dink_PR_Skin`), hair cards use the Hair shading model, masked two-sided with dithered opacity (`hair_material` in the importer; per-character tint and scalars in `HAIR_LOOK`; needs the editor built first, because `UDinkCharacterArtLibrary::ConnectMaterialCustomData` connects the back-light pin; evidence `Docs/Verification/CharacterHair_14Nov2026/`). Morph targets are imported: the hero's build keys `Physique_Scrawny` and `Physique_Brawny` (`Characters/Tools/physique.py`, driven from hero confidence; `dink.HeroConfidence 0..1` shows any stage) must arrive on every LOD or the import stops. The hero's parent materials are compiled for morph targets (without it a shaped body draws black in the game), and before a re-import the mesh is given FBX import data with the importer's settings (a re-import ignores the task's options and `import_lod` leaves Interchange import data behind). The garments were rebuilt on 14 Nov 2026 (armhole rims, collar, pack fit, unfolded shoulder charts: `Docs/Verification/HeroGarments_14Nov2026/`); the mesh keeps its bones, material slots and both shape keys, so only `SK_Dink_Photoreal` and the Outfit and Gear textures were re-imported.
- Mother and Milder: each has a body build baked into its exported mesh (`Characters/Tools/char_07_build.py`, `cfg/tex.env` `BUILD`; Milder `Burly`, Mother `Matron`; `<Name>/build_report.json`), so there is nothing to drive at runtime. Skin instances of all three characters are imported with `NormalStrength 0.6` (evidence `Docs/Verification/CharacterFacesBuilds_14Nov2026/`).

## Captures

The capture and calibration tools live in `Scripts/PhotorealQA/` (see its README); they write only below `Saved/PhotorealPass/`.

`Scripts/PhotorealQA/round.sh <name> [--extra]` renders the fixed review cameras offscreen (no display, no input) into `Saved/PhotorealPass/lighting/<name>/`; `--extra` adds the in-game art cameras. Set `DINK_CAPTURE_DIR` to redirect the output folder.

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
- **Calibration of structures**: `Scripts/PhotorealQA/cal2_script.py` + `cal2_compare.py` (patches in `cal2_patches.json`).
- **Scripted walking in captures**: `dink.WalkTo <mapx> <mapy> [seconds]`.

## Round 6 additions (12 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Photoreal pillbug and its carcass | `DINK_PHOTOREAL_ONLY=pillbug Scripts/import_photoreal_art.sh` | `Creatures/Pillbug/Export`, `Creatures/Pillbug/Textures` | `/Game/Dink/Photoreal/Creatures/Pillbug` (`SK_Pillbug_Photoreal` on the existing pillbug skeleton, `SM_Pillbug_Corpse_PR`); a rig that differs is reported in `import_photoreal.json` (`pillbug.error`), never forced |
| Photoreal hero, Mother and Milder | `DINK_PHOTOREAL_ONLY=hero,mother,milder Scripts/import_photoreal_art.sh` (any subset) | `Characters/<Name>/manifest.json`, `Characters/<Name>/Export`, `Characters/<Name>/Textures` | `/Game/Dink/Photoreal/Characters/<Name>` (`SK_<Name>_Photoreal` on the shared 89-bone skeleton after the native bind-pose gate, four LODs) |
| Vegetation after a finished re-export | `DINK_PHOTOREAL_ONLY=vegetation Scripts/import_photoreal_art.sh` (materials only: add `DINK_PHOTOREAL_FROZEN=1`) | `Vegetation/manifest.json` | re-imports every mesh whose FBX size or time changed; `MI_Veg_Shrub` (the four bushes) is built on the foliage master like the other sets |

- **families.json `span`**: `"width"`, `"height"` (edge-on strips) or `"stretch"`: a wall module is repeated along its own X axis and scaled along X only until it fills that dimension of the layout-scaled card (`span_fill`: mesh of the further modules, `span_end`: the end the main mesh keeps). The wall kits are authored at 0.025 m per pixel; interiors are laid out at 0.0438 to 0.1 m per pixel, so without it every 2.5 m module stood alone in its slot.
- **families.json `scripted: true`** now also on `crate`, `crate_small`, `counter_wood`, `shelf_bottles` (their scripts never move or replace them in a way a placement card would show).
- **Town houses** (`Scripts/assemble_town_houses.py`, schema dink-town-houses/2): runs are cut into houses of 2 to 4 bays with their own eaves height, set-back, depth, bay pattern and chimney; party walls, convex corners (both gables) and concave corners (valley); `footprints` keep the grass carpet out of the houses.
- **Grass** (`environment.json` `grass`): `field_scale` (height) and `field_footprint` of the field patch, `short_reach_cm` (short turf along walls, fence lines, paths and doors), `rank_edge_share`; the apron of a door carries no grass.
- **Indoor set** (`environment.json` `indoor.<look>`): `fill_intensity` / `fill_colour` (even unshadowed fill), `ceiling_cm` / `ceiling_material` / `ceiling_wall_class` (a visible one-sided ceiling, chosen by the walls that stand there), `indoor.ceiling_tile_cm`.
- **Sky light colour**: `environment.json` `sky.tint`; live: `dink.SkyTint r g b`.
- **Mother and Milder**: `dink.PhotorealNPCs` (default 1) shows `SK_Mother_Photoreal` / `SK_Milder_Photoreal` in place of the `SK_Mother` / `SK_Milder` of `characters.json` while the process renders; `-dpcvars=dink.PhotorealNPCs=0` keeps the previous meshes. Hair: the `FLOW` map drives the anisotropy tangent; `masked` in the manifest is read case-insensitively. Their bodies are shown at a smoothed position and facing, re-anchored at the end of every frame after the scripts have moved the actor (`UDinkHumanoidComponent::PresentBody`, 13 Nov 2026; `dink.Npc.LatePresent 0` shows the stutter of the build before); nothing to import for it.
- **Pillbug**: `dink.PhotorealPillbug 0` (command line) keeps `SK_Pillbug`. A killed photoreal pillbug leaves `SM_Pillbug_Corpse_PR` until the player leaves the screen (visual only, read from actor visibility); `dink.PillbugCarcass` lays one beside every pillbug of the screen for review.
- **Props round 2** (`DINK_KIT=Props DINK_KIT_FOLDER=Props Scripts/import_town_exteriors.sh`): baked props take `M_Struct_Baked` (ORM.B is metallic); a material with an `E` map takes `M_Struct_Baked_Glow` (`EmissiveNits` from the manifest x `EmissiveScale`, default 0.1: the project's light scale is far below physical); kind `subsurface` -> `M_Struct_Baked_Wax`, `translucent` -> `M_Struct_Baked_Pane_Glow`. `SM_Chest_Small_Open_PR` is imported and unbound (no opened-chest state is read yet). The tiling props' iron is still dielectric (the `metal` flag of the contract is not wired into `M_Town_Surface`). No flicker on the emissive.
- **Ground decals**: the same import builds `M_Decal_Sheet` and `MI_Decal_BloodSplat_0..3`, `MI_Decal_BurnHole_0..3` from `Props/Decals`; `environment.json` `decals` binds sprite classes to them (`blood_splat`, `burn_hole_decal`): the card is hidden and a deferred decal lies at its ground point. Unscripted placements only; screens and origins an art manifest handles and classes a state swap hides are left alone.

## Fresh checkout: reproducing the look

`Content/Dink/_Generated` and `ImportData` are git-ignored, so a fresh checkout of master needs, from `DinkRemasterUE/`, in this order:

1. `Scripts/build.sh` (0 warnings expected).
2. `Scripts/import_environment_materials.sh` (terrain layers, water, backdrop, fire materials; only needed when `Content/Dink/Materials/Environment` or `Content/Dink/Textures/Environment` are not in the checkout or a Terrain set changed). Both folders are committed. Running it anyway re-saves all 144 packages with this checkout's source paths inside: `git checkout -- Content/Dink/Materials/Environment Content/Dink/Textures/Environment` afterwards, or run `python3 -I Scripts/scrub_private_paths.py --fix` before committing a real change.
3. `python3 -I Scripts/export_ground_colour.py` is NOT needed on a fresh checkout when `Content/Dink/Data/Environment/ground_colour.json` is committed; re-run it after step 4 only if terrain textures or the world export changed.
4. The world export reads the extracted original data, which is git-ignored. On a clone that has never had it, from the repository root: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`, `(cd tools/analyse && python3 -m analyse build --ir ../dinkex/out --out out)`, `(cd tools/dinkc && python3 -m dinkc build --scripts ../../bin/dink/story --map ../../bin/dink/map.dat --dat ../../bin/dink/dink.dat --out out)`. Then `Scripts/import_greybox.sh --region all --export` (writes `ImportData/`, `Content/Dink/_Generated`, `Content/Dink/Data/Environment/layer_cover.json`; runs `Dink.Import`).
5. Only when `Content/Dink/Photoreal` is not in the checkout or an art source changed (all re-runnable, any order):
   `Scripts/import_photoreal_art.sh` (vegetation, scatter, hero, walls), `DINK_PHOTOREAL_ONLY=pillbug Scripts/import_photoreal_art.sh`,
   `Scripts/import_town_exteriors.sh`, `DINK_KIT=Structures/Stonebrook DINK_KIT_FOLDER=Structures Scripts/import_town_exteriors.sh`,
   `DINK_KIT=Props DINK_KIT_FOLDER=Props Scripts/import_town_exteriors.sh`, `Scripts/import_indoor_materials.sh`.
6. `python3 -I Scripts/assemble_town_houses.py` (needs `ImportData/placements.json` from step 4; its output `Content/Dink/Data/Art/town_houses.json` is committed, so this is only needed after a change to the script or the placements).
7. Check: `Scripts/test.sh Dink.Import`, `Scripts/test.sh Dink.Art`, `Scripts/test.sh Dink.Gameplay.Probe`, `python3 -m unittest discover -s Scripts/tests`, `python3 -I Scripts/art_coverage.py`, `python3 -I Scripts/art_standard_check.py`.

## Unclaimed families kit (12 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Static meshes of the unclaimed families that `families.json` binds | `python3 -I SourceAssets/Art/PhotorealPass/Unclaimed/tools/make_kit_manifest.py`, then `DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh` | `Unclaimed/manifest.json` (generated: the meshes a `families.json` row names under `/Game/Dink/Photoreal/Unclaimed`; `--all` lists every importable mesh for a look before binding) | `/Game/Dink/Photoreal/Unclaimed`; report `Saved/PhotorealPass/import_unclaimed.json` |

- **One object per FBX**: these files hold a single object named after the asset and no LOD objects; `import_town_exteriors.py` takes that object as LOD0.
- **Order**: add the `families.json` row, regenerate the manifest, import, then `git add` the new packages and run `python3 -I Scripts/scrub_private_paths.py --fix Content/Dink/Photoreal/Unclaimed` (the importer writes the local project path into texture packages; the scrubber only sees tracked files).
- **What the layer cannot place** (families left unbound, reasons in `Unclaimed/STATUS.md`): things on a table top or shelf, things hung on a wall, pits below the ground, and buildings drawn in several sprites. A family mesh always stands on its lowest point at Z 0 under the card.
- **Gore**: a mesh that is less gory than its sprite is not bound (owner rule: keep all original gore). The clean dead dragon of this kit is a source only: the remains the game shows come from the corpse kit below. The dead knight and the posed bodies stay sprite cards until they are rebuilt with the 1997 gore.
- **Pickups** (hearts, small coin scatter) use `fit: footprint`: a pickup is shown at the size the original draws it, not at the size of the modelled object.
- **Checks and captures**: `Docs/Verification/UnclaimedFamilyBinding_12Nov2026/`.

## Corpse kit (14 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Remains with their gore (so far the torn dragon) | `python3 -I SourceAssets/Art/PhotorealPass/Corpses/tools/make_kit_manifest.py`, then `DINK_KIT=Corpses DINK_KIT_FOLDER=Corpses Scripts/import_town_exteriors.sh` | `Corpses/manifest.json` (generated: the meshes a `families.json` row names under `/Game/Dink/Photoreal/Corpses`; `--all` lists every built asset) | `/Game/Dink/Photoreal/Corpses` with its own masters `M_Struct_Baked` and `M_Struct_Baked_Cut`; report `Saved/PhotorealPass/import_corpses.json` |

- **Why a kit of its own**: a family row places one mesh and nothing else, so the pool of blood a 1997 corpse lies in is part of the mesh: slot 0 is the body with its wounds on one baked atlas, slot 1 an alpha-tested card 6 mm above the ground with the pool, the thrown drops and the mist (`kind: masked`, a material kind added to `import_town_exteriors.py`: the alpha of BC is the opacity mask). `Scripts/tests/test_corpse_kit.py` fails when a body is bound without its pool.
- **Sources**: `Corpses/tools/build_gore.py` reads the rigged dragon of `PhotorealPass/Unclaimed`, poses, cuts and bakes it again (it also holds the rejected first recipes for the knight and the posed bodies) (`Unclaimed/tools/bl.sh ../../Corpses/tools/build_gore.py <name[,name]|people|sheets|all> [preview]`); `tools/gore_sheets.py` paints the pool cards (numpy, no scan). Pull the Unclaimed sources from LFS first.
- **Rows**: bodies use `fit: none` (real size) and `yaw_from_sprite`. Importing this kit never rewrites another kit's packages.
- **The flat card and grass**: the grass carpet hides flat meshes. The dragon of screen 238 lies on grass and shows only flecks of its pool; a pool on grass needs a deferred decal, which a family row cannot place yet.
- **Rows that draw nothing**: screens listed under `hide_screen_visuals` by a `dink-art/1` manifest (1, 439, ...) never take family rows; unscripted `blood_splat` / `burn_hole_decal` actors are taken by the deferred decals of `environment.json` first.
- **Checks and captures**: `Docs/Verification/CorpseGore_14Nov2026/`.

## Faceting sweep (13 Nov 2026)

Owner feedback of 13 Nov 2026: "fix blocky and polygon looking art". What was found and changed is in `Docs/Verification/FacetingSweep_13Nov2026/`.

| What | Command | Reads | Writes |
|---|---|---|---|
| Wall kits after a rebuild (`blender -b -t 4 --python WallKits/tools/wallkit_build.py`) | `DINK_PHOTOREAL_ONLY=walls Scripts/import_photoreal_art.sh` | `WallKits/manifest.json` | the 13 modules of `/Game/Dink/Photoreal/WallKits` |
| Thorn brambles after a re-export (`blender -b -t 4 --python Vegetation/src/export_all.py -- under`) | `DINK_PHOTOREAL_ONLY=vegetation Scripts/import_photoreal_art.sh` | `Vegetation/manifest.json` | `SM_Veg_ThornBush_01/02`, `SM_Veg_ThornBranch_01` (every mesh whose FBX size or time changed is re-imported: restore the files you did not mean to change first) |
| Jars after a rebake (`Props/tools/props_bake.py -- SM_Jar_...`, `props_merge.py`, `props_publish.py`) | `DINK_KIT=Props DINK_KIT_FOLDER=Props Scripts/import_town_exteriors.sh` | `Props/manifest.json` | `/Game/Dink/Photoreal/Props` |
| Unclaimed kit (gold heap, coins, the four boulders) | `python3 -I SourceAssets/Art/PhotorealPass/Unclaimed/tools/make_kit_manifest.py`, then `DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh` | `Unclaimed/manifest.json` | `/Game/Dink/Photoreal/Unclaimed`, **including its master material `M_Struct_Baked`** |

- **A kit's master material takes its default textures from the kit's first asset.** Remove that asset's textures without importing again and the master no longer compiles: the game log says `Failed to compile Material ... Default Material will be used in game` and every mesh of the kit is drawn grey, without colour or normal map. That was the state of the unclaimed kit on master after PR #90 (all 34 props). After removing assets from a kit, run its import again and commit the rebuilt master. `Scripts/tests/test_photoreal_material_references.py` fails when a material under `Content/Dink` names a package that is not in the repository.
- **A material drawn on background placements needs the usage flag "Used with Instanced Static Meshes"** on its base material (the kit importers set it). `MI_Stonebrook_Fieldstone` does not have it, so background boulders bound to `SM_Boulder_Fieldstone_01` were grey; the boulder rows now bind photoreal boulders. The same unit test follows every mesh bound by `families.json`, `town_houses.json`, `structure_sets.json` and the photoreal meshes of `environment.json` to its base materials and fails when the flag is missing. Before binding a mesh from outside `Content/Dink/Photoreal` in a family row, run it.
- **Shading of generated meshes**: the wall kits are smooth shaded with hard edges where faces meet at more than 28 degrees (`shade()` in `wallkit_build.py`); flat shading showed every triangle of the uneven plaster and of the jittered stone faces. Round forms: lathe at least 24 sides for a pickup shown large, 40 to 48 for a pot, and run the profile through a curve (`_smooth_prof` in `Props/tools/props_gen_pots.py`): a profile of straight runs shows as corners in the outline whatever the normals are.
- **A capture of a freshly imported mesh shows the default material until its shaders are compiled.** Spawn the meshes once off camera and wait before the shots.

## Gate 2 static batch 1 (13 Nov 2026)

Evidence: `Docs/Verification/Gate2StaticBatch1_13Nov2026/`.

| What | Command | Reads | Writes |
|---|---|---|---|
| Unclaimed boulders after a rebuild (`Unclaimed/tools/bl.sh build_props.py <names> final`, the five boulder names from the script's table) | `python3 -I SourceAssets/Art/PhotorealPass/Unclaimed/tools/make_kit_manifest.py`, then `DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh` | `Unclaimed/manifest.json` | `/Game/Dink/Photoreal/Unclaimed` (meshes, textures, `M_Struct_Baked`) |
| Stumps and thorn bushes after a re-export (`blender -b -t 4 --python Vegetation/src/export_all.py -- deadwood under`) | `DINK_PHOTOREAL_ONLY=vegetation Scripts/import_photoreal_art.sh` | `Vegetation/manifest.json` | `SM_Veg_Stump_01/02`, `SM_Veg_ThornBush_01/02` |
| Shell clusters and large starfish (`blender -b -t 4 --python Terrain/tools/scatter_clusters.py`) | `DINK_PHOTOREAL_ONLY=scatter Scripts/import_photoreal_art.sh` | `Terrain/manifest.json` | `/Game/Dink/Photoreal/Scatter/SM_ClamShell_Cluster_A/B/C`, `SM_Starfish_Large_A/B`, `MI_Scatter_Clam`, `MI_Scatter_Starfish` |
| Field boulders after an occlusion rebake (`blender -b -t 4 --python Structures/tools/boulder_bake.py`) | `DINK_KIT=Structures/Stonebrook DINK_KIT_FOLDER=Structures Scripts/import_town_exteriors.sh` | `Structures/Stonebrook/manifest.json` | the kit's packages; only `Textures/T_Boulder_Field_A/B/C_PR_ORM` were committed |
| Signposts | same Structures kit import | same | `SM_SignPost_Single/Double/Triple_PR`, `MI_Struct_OakDark` |

- **The kit importer stops when an FBX is newer than the kit's `manifest.json`** ("N FBX files are newer than the manifest ... export in progress, nothing imported"). A bake that re-exports FBX it did not change trips it: put the unchanged FBX back (or finish the export) and touch nothing else. In a chained import the editor still exits 0; read the step lines of the log.
- **Bake occlusion with the mesh alone.** Other objects at the origin (the high-poly source, other LODs, earlier bakes) shadow the mesh and leave black patches on every face out of the sun. `boulder_bake.py` hides them for the pass.
- **What binds at runtime**: `families.json` rows may carry `scale` (after `fit`) and are also used for sprites that scripts create (`create_sprite`): the mesh of the picture's family stands in for the grey marker, without collision.
## Screen grounds in the audit (13 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| What each screen's ground is made of | part of the world export (`Scripts/export_import_bundle.py`, run by `Scripts/import_greybox.sh --export`) | `tools/data/tile_classes.csv`, `terrain_layers.json` | `Content/Dink/Data/Environment/ground_classes.json` (per screen: tile classes, the layer of each, the layers the mask carries, the layers it dropped, water surface) |
| Captures for the review (play camera, 1.1 m above the ground, from above) | `python3 -I Scripts/PhotorealQA/ground_script.py <out dir> [--screens=a,b]`, then `Scripts/PhotorealQA/run_capture.sh <out dir>/ground_<k>.txt` | screens, tile classes, hardness | `NNN_play/close/above.png`, `ground_index.json` |
| Review sheets | `python3 -I Scripts/PhotorealQA/ground_sheet.py <capture dir> <out dir> [--by-class]` | the captures | one JPEG per pair of screens, or per reason a screen was chosen |
| The verdicts and the result as tables | `python3 -I Scripts/PhotorealQA/ground_review_table.py` | `ground_classes.json`, `ground_review.json` | Markdown on stdout |

- **The verdicts are hand-kept data**: `Content/Dink/Data/Environment/ground_review.json`, one verdict per tile class outdoors and indoors, with the screens that were looked at and the reason. After a change to the terrain material, a layer's textures, the grass carpet or the mask, capture the classes it touches again and update the verdicts; never flip a verdict without a capture.
- **One switch**: `rule.count_reviewed_grounds_final` in that file (or `art_coverage.py --ground-rule on|off`). Off, no screen ground counts final by review.
- `ground_classes.json` is generated; a world export that changes it must be committed with it, or the audit judges the old ground.

## Ground fixes (14 Nov 2026): what binds at runtime

- **Terrain material**: `M_Env_Terrain` blends four layers (mask RGB + what they leave = layer D). `terrain_layers.json` per layer: `structured` (boards, flagstones, cobbles, masonry: no UV warp, no variant or far lookup, no detail normal), `drift: false` (no field-scale drift or dry patches: snow), `tile_scale`. Class `structure_facade` outdoors is `@surroundings`: the tile takes the layer of the nearest ordinary ground on its screen. After changing the catalogue: `DINK_ENV_MATERIALS_ONLY=1 Scripts/import_environment_materials.sh`, then a world export and import (`Scripts/import_greybox.sh --region all --export`), and commit `M_Env_Terrain`, the `MI_Env_Terrain_*` instances, `ground_classes.json` and `layer_cover.json` together (scrub the packages first).
- **Generated per screen in `ground_classes.json`** (world export, never hand-edit): `trees` (points on unwalkable forest-canopy tiles), `relief` (points on cliff, rock-mass and cave-wall tiles where nobody can stand, with a clear radius and a tier), `water_tiles` (rects of water tiles on screens whose collision has no water fill).
- **`environment.json`**: `forest` (meshes, interior fill, understory; `dink.Forest`), `relief` (meshes; `dink.Relief` 0/1/2, default 1), `water_tiles` (material, height; `dink.WaterTiles`), `grass.clear_max_height_cm`, `clear_max_span_cm`, `clear_reach_cm` (clearings round low family props, authored props and ground decals; 0 height = off) and `grass.edge_feather`. All visual only, no collision; screens an art manifest dresses are skipped.
- **Snow and ice exposure** (`environment.json` `snow_exposure`, `dink.SnowExposure`): outdoor screens whose tiles are mostly snow or ice get an exposure compensation (0.8 EV at a 60% share, eased), because the automatic exposure meters white ground down to grey. No import step; the shares come from `ground_classes.json`.
- Proof that nothing gameplay moved: the export's `collision.json`, `placements.json` and `warps.json` are byte-identical before and after; unit tests `Scripts/tests/test_ground_export_helpers.py`. Before/after sheets: `python3 -I Scripts/PhotorealQA/ground_compare_sheet.py <before dir> <after dir> <out dir>`.

## Town houses in the audit (13 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Town houses per screen with the accounting (offline, no editor) | `python3 -I Scripts/assemble_town_houses.py` | `ImportData/placements.json` | `Content/Dink/Data/Art/town_houses.json` (schema dink-town-houses/3) |
| Captures of every town screen (play camera, above the south edge, above the north edge; `--close` adds street and roof views per house front) | `python3 -I Scripts/PhotorealQA/town_script.py <out dir> [--close]`, then `Scripts/PhotorealQA/run_capture.sh <out dir>/town.txt` (add `-dpcvars=dink.TownHouses=0` for the sprite cards) | `town_houses.json`, `ImportData`, the hardness files | PNG files in `<out dir>` |
| Review sheets, one per screen | `python3 -I Scripts/PhotorealQA/town_sheet.py <on dir> <off dir> <out dir>` | the captures | `town_<screen>.jpg` |
| Runtime check against the game's own log | `python3 -I Scripts/PhotorealQA/town_log_check.py <game log>` | the `DINK ENV: town houses on screen` lines | exit code 1 when a screen differs from the file |
| Per-placement table | `python3 -I Scripts/art_coverage.py`, then `python3 -I Scripts/PhotorealQA/town_table.py <out.csv>` | `town_houses.json`, `Saved/Import` | the CSV |
| No house body can be walked into (offline) | `python3 -I Scripts/PhotorealQA/town_walk_check.py [--out report.txt]` | `town_houses.json`, `ImportData/collision.json`, `ImportData/placements.json` | exit code 1 when more than 2 m2 of a house core lies in the walkable ground in front of its own wall (30 cm capsule) |

- **What the file says about each card** (schema 3): `buildings` groups the family 33 pictures that touch into the six 1997 buildings; every screen lists `stands_for` (card -> the assembled house that replaces it: a wall card its own run, a roof, dormer, ridge or gable card the nearest house of its building) and `uncovered_m` (cards whose picture did not lie within one kit bay, 2.5 m, of a house body, with the distance). The houses, modules, hide lists and footprints are what schema 2 held.
- **What the audit counts** (`art_coverage.py` `town_house_cards`): a card is final when its own screen hides it, a house with modules stands for it, every kit mesh of that house exists, a house body covers where it stood, and the house is not listed in `REVIEW` of the script (house id -> reason; empty today). 121 of the 218 placements are final (80 window walls, 15 door walls, 21 gable ends, 5 roof cards right behind a deep house); 97 roof cards stay placeholder.
- **Why the roof cards stay open**: the 1997 buildings are 45 to 70 m deep in the stretched settlement layout (walls, a band of upper-storey tiles, roof pictures up to the ridge); the assembled houses are 8 to 15 m deep and stand on the front line. Behind them the ground is open (`structure_facade` tiles drawn as a terrain layer). The cards are hidden and the houses carry complete roofs, so nothing is missing from the street; from behind, the block is not built. A house body that reaches back over that ground turns those cards final without touching the audit.
- **Capture stand points**: the ground behind a wall line (the inside of a 1997 building) has hardness 0 but is closed off; `town_script.py` never stands inside or up to 30 m behind a house body, otherwise the play camera shows a house from within.
- **Checks and captures**: `Docs/Verification/TownHouses_13Nov2026/`.
- **Private project copies**: the built modules carry a library search path relative to the shared checkout's depth, so a copy under `Saved/<name>/DinkRemasterUE` fails to start the game with `Plugin 'DinkParity' failed to load because module 'DinkProbe' could not be loaded`. Until the copy is rebuilt, export `LD_LIBRARY_PATH` with its own `Plugins/*/Binaries/Linux` and `Binaries/Linux` folders.

## Creature classes (13 Nov 2026)

`Content/Dink/Data/Art/creatures.json` has a second list, `classes`: one row binds a sprite class (`tools/data/sprite_classes.csv` `class_id`) to an animated creature, and every placement of that class on every screen, and every sprite a script creates with one of the row's sequences, is shown by it instead of a sprite card. The eleven origin rows (`placements`) keep precedence, as does any origin another `Data/Art` manifest names.

| Class | Mesh | Clips | Corpse | Import |
|---|---|---|---|---|
| `pillbug` (154 placements, sequences 131/133) | `/Game/Dink/Photoreal/Creatures/Pillbug/SK_Pillbug_Photoreal` | `AN_Pillbug_Idle`, `_Walk` (80 cm/s), `_Run` (400 cm/s) of `/Game/Dink/Creatures/Pillbug/Animations` | `SM_Pillbug_Corpse_PR` for death sequences 141/143, with the ground decal `M_Pillbug_BloodPool_Decal` | already imported (`DINK_PHOTOREAL_ONLY=pillbug Scripts/import_photoreal_art.sh`) |

- **Row format**: `class`, `mesh`, `locomotion` (`idle` clip and `gaits`: `clip`, `speed_cm_s` the clip was made for, optional `cycles`; slowest first), `roles` (a name -> `sequences` plus either `"locomotion": true`, an own locomotion object, or a `clip` with optional `loop` and `mesh`), optional `corpses` (`sequences` = base_death + facing, `mesh`, `offset_cm`, `yaw_offset`, `scale`, and `decal`: `material`, `size_cm` [along, across], `depth_cm`), `materials` (slot -> material, for colour variants of one mesh), `scale`, `offset_cm`, `rotation_deg`, `smooth_time_s`, `turn_rate_deg_s`, `blend_time_s`, `stationary_speed_cm_s`, `cull_distance_cm`. A row that does not parse, or names an asset that is missing or on another skeleton, binds nothing and its sprites keep their cards (warning in the log).
- **What the runtime does** (`UDinkCreatureSubsystem`, `UDinkCreatureClassComponent`, `UDinkCreaturePresenter`): at begin play each placement actor of a bound class gets the body and its card's picture is hidden; a script-made sprite gets its body on the frame it appears. At the end of every frame (`TG_PostUpdateWork`: the story moves sprites from a tickable object, after the actor tick groups, so an earlier step would show last frame's position) the presenter reads each sprite's sequence, frame, direction and size and the body follows its actor. The sprite's whole-pixel 60 Hz steps are shown as continuous motion (`FDinkBodySmoother`, the averaging the humanoid bodies use, `smooth_time_s`), the body faces along that motion and, standing, the sprite's direction (`turn_rate_deg_s`), locomotion is a native blend of idle and gaits whose cycle advances by distance over stride (no blend space asset), and a role that is a clip plays over the duration of the sprite sequence it stands for, cross-faded (`blend_time_s`). A kill by damage (`add_kill_sprite`, dink.cpp:12359) leaves the row's corpse where the body stood until the player leaves the screen; a sprite removed by a script leaves nothing, as in the original. A sprite without a death sequence leaves no corpse either; the original plays the blood burst 164 for it (dink.cpp:12384-12389), which is not drawn yet (it comes with the ducks, whose second death is that burst).
- **The pillbug carcass** (rebuilt 13 Nov 2026 on the owner's order "increase the blood, like the 1997"): `Creatures/Tools/pillbug.py -- corpse` (`Tools/bl.sh pillbug.py -- corpse`, about two minutes on the GPU) poses the rig burst open, composites blood across the shell in texture space from the posed world positions (`T_Pillbug_Corpse_BC/_ORM`, about half of the up-facing shell, as sprites 141/143 show it; the body slots are `MI_Pillbug_*_Bloody`), builds a lobed pool with thrown streaks and drops and the viscera (`T_Pillbug_Gore_*`), and renders the gore from straight above into `T_Pillbug_BloodPool_BC` (RGBA, a 4.4 m square). The game lays that picture under the carcass as a deferred decal (45 cm deep), because the grass carpet hides any flat mesh: on grass the blades are stained, on bare ground the modelled pool lies on top of the same outline. The carcass mesh receives no decal. `DINK_PHOTOREAL_ONLY=pillbug Scripts/import_photoreal_art.sh` imports all of it.
- **What it never does**: no collision, no body boxes, no overlap events, no actor tag gameplay reads (`DinkCreature` and `DinkAuthoredArt` stay with the origin rows), no write to a sprite, an actor transform or the random stream. Touch damage, hits, experience, drops, hardness and scripts are the simulation's, as before.
- **Switch**: `dink.CreatureClassArt` 0 = off (cards), 1 = while the process renders (default), 2 = also headless (the automated tests use it). Headless runs keep the cards, like `dink.PhotorealPillbug`. `dink.CreatureClasses` logs every followed body (role, speed, cadence, yaw).
- **Coverage**: `Scripts/art_coverage.py` counts these placements `final` with evidence `class-bound:` (`creature_class_rows`, `creature_class_binding`).
- **Captures**: `Scripts/CreatureQA/make_scripts.py` writes before/after capture scripts for `Scripts/PhotorealQA/run_capture.sh`; results and what was seen: `Docs/Verification/CreatureClassBinding_13Nov2026/`.

## Turning the pass off

Everything is presentation only and off in headless runs (`FApp::CanEverRender()` is false under `-nullrhi`), except the family bindings of `families.json`, which also dress placements headless (no collision, no gameplay). Command-line switches (`-dpcvars=a=0,b=0`):
`dink.PhotorealHero=0`, `dink.PhotorealPillbug=0`, `dink.CreatureClassArt=0` (class-bound creatures), `dink.PhotorealNPCs=0` (Mother and Milder), `dink.TownHouses=0`, `dink.FamilyArt=0` (all family meshes, the old ones included), `dink.EnvMaterials=0`, `dink.IndoorEnv=0`, `dink.IndoorLitCards=0`, `dink.StateSwaps=0`, `dink.GrassDensity=0`, `dink.Wind=0`, `dink.Backdrop=0`, `dink.InteriorExposure=0`. `dink.EnvMeshSwaps=0` is meant to restore the old Stonebrook vegetation and structures but crashed at start in round 6 (segmentation fault): do not rely on it until that is fixed. The sky light tint has no cvar: set `environment.json` `sky.tint` to 1, 1, 1.
