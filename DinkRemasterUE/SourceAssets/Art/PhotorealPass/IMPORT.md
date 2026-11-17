# Photoreal pass: importing into Unreal

All commands run from `DinkRemasterUE/`, headless, and are re-runnable. A re-export from an art agent is picked up by file size and modification time; nothing else is re-imported.

| What | Command | Reads | Writes |
|---|---|---|---|
| Terrain layers, water, backdrop and fire materials | `Scripts/import_environment_materials.sh` (`DINK_ENV_MATERIALS_ONLY=1` rebuilds the material graphs without touching textures) | `Terrain/manifest.json`, `Environment/terrain_layers.json` | `/Game/Dink/Materials/Environment`, `/Game/Dink/Textures/Environment` |
| Vegetation, scatter stones, photoreal hero | `Scripts/import_photoreal_art.sh` (`DINK_PHOTOREAL_ONLY=vegetation,scatter,hero` limits it) | `Vegetation/manifest.json`, `Terrain/manifest.json` (`scatter_meshes`; the allowed names are `SCATTER_ALLOW` in the script), `Characters/Dink/manifest.json` | `/Game/Dink/Photoreal/{Vegetation,Scatter,Characters/Dink}`; report `Saved/PhotorealPass/import_photoreal.json` |
| Town-house kit (materials from the manifest's `integration` contract, 14 modules; refuses while an FBX is newer than the manifest) | `Scripts/import_town_exteriors.sh` | `TownExteriors/manifest.json` | `/Game/Dink/Photoreal/TownExteriors`; report `Saved/PhotorealPass/import_town.json` |
| Ground colour grid for trunk feet | `python3 -I Scripts/export_ground_colour.py` (after a world export or a terrain texture change) | `ImportData/screens.json`, `ImportData/ground_mask`, `Terrain/*/T_Terrain_*_BC.png` | `Content/Dink/Data/Environment/ground_colour.json` |
| World (ground masks, per-screen terrain and water instances, sky, backdrop) | `Scripts/import_greybox.sh --region all --export` | the two above, `tools/data/tile_classes.csv` | `/Game/Dink/_Generated`, `Content/Dink/Data/Environment/layer_cover.json` |

Ground-layer outlines (15 Nov 2026, VS-09): the world export rebuilds every outdoor screen's terrain-mask weights in world space with the screens round it (`Scripts/ground_layer_fields.py`, called by `naturalise_ground_masks` in `export_import_bundle.py`): rounded, noise-bent outlines that stay within half a tile of the 1997 ones, feathered, the same on both sides of a screen border. Mask texels are edge-aligned (texel 0 on the west edge, texel 95 on the east edge), so the material's clamped lookup shows the same weights on both sides of a border. After a change run the export and the world import, then `export_ground_colour.py`. Look at outlines without the game: `python3 -I Scripts/PhotorealQA/ground_mask_mosaic.py ImportData out.png <screen>`; border steps over the whole world: `python3 -I Scripts/PhotorealQA/ground_mask_seams.py ImportData`.

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
- Brows and lashes: `BrowGain` (hair material, per character in `HAIR_LOOK`) multiplies the base colour of the brow and lash band, which has no scatter or back-light and so reads darker than the hair (hero 1.6, Milder 1.5). The Mother's age lines are in her skin maps (`skin.json` `age`, `line_k`, `fore_*`); evidence `Docs/Verification/MotherAgeBrowsMilder_14Nov2026/`.

## Captures

The capture and calibration tools live in `Scripts/PhotorealQA/` (see its README); they write only below `Saved/PhotorealPass/`.

`Scripts/PhotorealQA/round.sh <name> [--extra]` renders the fixed review cameras offscreen (no display, no input) into `Saved/PhotorealPass/lighting/<name>/`; `--extra` adds the in-game art cameras. Set `DINK_CAPTURE_DIR` to redirect the output folder.

## Pine and oak shading values (round 7, 14 Nov 2026)

`FOLIAGE_LOOK` in `Scripts/import_photoreal_art.py` (tint, specular, crown shade, crown occlusion, translucency), set from `Scripts/PhotorealQA/cal.sh` against the Cycles review renders:

- **PineNeedles** (also the dry pine): crown shade 0.35 -> 0.80, crown occlusion 0.20 -> 0.70, translucency 0.10 -> 0.35, back shade 0.6 -> 1.0 (needle cards only; leaf cards keep 0.6). The three darkening terms stacked: the pine's median luminance was 25 against 56 in the reference; it is 50 now.
- **OakLeaves**: tint 0.45, 0.50, 0.26 -> 0.33, 0.37, 0.17, specular 0.06 -> 0.03, crown shade 0.22 -> 0.70, crown occlusion 0.08 -> 0.60, translucency 0.10 -> 0.08: a darker leaf with a lighter crown interior, so the sunlit 95th percentile falls from 144 to 109 (reference 81) while the median stays at 17 (22).
- Bushes are unchanged: their numbers already sit near the reference; what reads as heaps of large leaf cards is in the meshes (the Cycles render shows it too).
- Applied with `DINK_PHOTOREAL_ONLY=vegetation DINK_PHOTOREAL_FROZEN=1 Scripts/import_photoreal_art.sh` (materials only); it re-saves every vegetation material and re-imports meshes whose export is newer: commit only `MI_Veg_PineNeedles`, `MI_Veg_PineNeedlesDry`, `MI_Veg_OakLeaves` and restore the rest.

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
| Remains with their gore (the torn dragon, the knight, five people) | `python3 -I SourceAssets/Art/PhotorealPass/Corpses/tools/make_kit_manifest.py`, then `DINK_KIT=Corpses DINK_KIT_FOLDER=Corpses Scripts/import_town_exteriors.sh` | `Corpses/manifest.json` (generated: the meshes a `families.json` row names under `/Game/Dink/Photoreal/Corpses`; `--all` lists every built asset) | `/Game/Dink/Photoreal/Corpses` with its own masters `M_Struct_Baked` and `M_Struct_Baked_Cut`; report `Saved/PhotorealPass/import_corpses.json` |

- **Why a kit of its own**: a family row places one mesh and nothing else, so the pool of blood a 1997 corpse lies in is part of the mesh: slot 0 is the body with its wounds on one baked atlas, slot 1 an alpha-tested card 6 mm above the ground with the pool, the thrown drops and the mist (`kind: masked`, a material kind added to `import_town_exteriors.py`: the alpha of BC is the opacity mask). `Scripts/tests/test_corpse_kit.py` fails when a body is bound without its pool.
- **Sources**: `Corpses/tools/build_gore.py` reads the rigged dragon of `PhotorealPass/Unclaimed`, poses, cuts and bakes it again (it also holds the rejected first recipes for the knight and the posed bodies) (`Unclaimed/tools/bl.sh ../../Corpses/tools/build_gore.py <name[,name]|people|sheets|all> [preview]`); `tools/gore_sheets.py` paints the pool cards (numpy, no scan). Pull the Unclaimed sources from LFS first.
- **Rows**: bodies use `fit: none` (real size) and `yaw_from_sprite`. Importing this kit never rewrites another kit's packages.
- **The flat card and grass**: the grass carpet hides flat meshes. The dragon of screen 238 lies on grass and shows only flecks of its pool; a pool on grass needs a deferred decal, which a family row cannot place yet.
- **Rows that draw nothing**: screens listed under `hide_screen_visuals` by a `dink-art/1` manifest (1, 439, ...) never take family rows; unscripted `blood_splat` / `burn_hole_decal` actors are taken by the deferred decals of `environment.json` first.
- **Dressed screens**: the mother's body and the burn holes of screen 1 are `replacements` rows of `Content/Dink/Data/Art/stonebrook.json` (origin, mesh, `offset_cm` = the card's `offset_x_m`), with their `assets` sizes; the kit manifest lists meshes that such rows name.
- **Decal sheets**: `python3 -I Corpses/tools/build_decals.py` writes `Corpses/Decals` (three 2 x 2 atlases, one 1997 picture frame per cell: blood 187 / 188 / 189, burn holes 158); the kit import makes `/Game/Dink/Photoreal/Corpses/M_Decal_Sheet` and `MI_Decal_<Set>_0..3` from the manifest's `decals`. Not bound by `environment.json` yet.
- **Checks and captures**: `Docs/Verification/CorpseGore_14Nov2026/`, `Docs/Verification/StonebrookMotherAndRemains_14Nov2026/`.

- **Review follow-ups, 16 Nov 2026**: every kit asset rebuilt with `blood_sheet(keep_fringe=False)` (no pale damp ring), a matt
  pool edge and brighter people; the burn holes as kind `pit` (`pit_sheet` + `pit_card`: void mask in `ORM.b`, depths in the kit row's `pit` block,
  master `M_Struct_Baked_Pit`; `Burn_Hole_Wall` stands upright for `S001_P49`);
  `Dink_Dead` with `pool_under`, `pool_fill` and the padded, noise-bent `sprite_red` stamp (the picture's red as one natural
  pool under the body). `SM_Corpse_Mother_Joppa_PR` (365) is new; its `families.json` row waits for code item C1. Rebuild one
  asset: `Unclaimed/tools/bl.sh ../../Corpses/tools/build_gore.py <Name>`; then `git add` the outputs, run
  `Scripts/scrub_private_paths.py --fix` on the folder (it only sees tracked files), and import the kit.

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

## Gold twinkle and stumps (14 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Effect flipbooks of the unclaimed kit (the gold twinkle) | `python3 -I SourceAssets/Art/PhotorealPass/Unclaimed/tools/make_kit_manifest.py`, then `DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh` | `Unclaimed/manifest.json` `flipbooks` | `/Game/Dink/Photoreal/Unclaimed/M_FX_Flipbook`, `MI_FX_Sparkle`, `Textures/T_FX_Sparkle_Flipbook` |
| Stumps after a re-export (`blender -b -t 4 --python Vegetation/src/export_all.py -- deadwood`; put back the FBX of the log, branch and twigs, which the export rewrites unchanged) | `DINK_PHOTOREAL_ONLY=vegetation Scripts/import_photoreal_art.sh` | `Vegetation/manifest.json` | `SM_Veg_Stump_01/02` |

- **What binds at runtime**: a `families.json` row with `effect` (a material) and `effect_size_cm` instead of `mesh` is drawn on a camera-facing card for sprites that scripts create.

## Fire of the burning house: FableF kit (16 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Wall of flame (427, placed 161 and 70), its smoke column and the three burn patches (155, 156, 157) | `python3 -I SourceAssets/Art/PhotorealPass/FableF/tools/make_kit_manifest.py`, then `DINK_KIT=FableF DINK_KIT_FOLDER=FableF Scripts/import_town_exteriors.sh` | `FableF/manifest.json` `flipbooks` | `/Game/Dink/Photoreal/FableF/M_FX_Flipbook_Blend`, `MI_FX_Fire_Wall`, `MI_FX_Smoke_Plume`, `MI_FX_Embers_A/B/C`, `Textures/T_FX_*_Flipbook` |
| Rebuild the fire | `blender -b --factory-startup -t 4 --python SourceAssets/Art/PhotorealPass/FableF/tools/build_fire_fx.py -- Fire_Wall --res 150 --cache <scratch>` (set `DINK_FIRE_CPU=1` if the GPU back end faults on the volume). Stages: `sim`, `render` (HDR flame frames, kept in the cache), `atlas` (colour, opacity, smoke and sparks by `tools/fire_encode.py`: seconds, no simulation), `beauty`, `compact` | the script | `FableF/fire_fx/Fire_Wall` |
| Rebuild the smoke column | `python3 -I SourceAssets/Art/PhotorealPass/FableF/tools/build_smoke_plume.py` (no Blender) | the script | `FableF/smoke_fx/Smoke_Plume` |
| Rebuild the burn patches | `... build_fire_fx.py -- Fire_Wall --cache <scratch> --stage compact`, then `python3 -I SourceAssets/Art/PhotorealPass/FableF/tools/build_burn_patch.py <scratch>/compact_256.npy` (no Blender) | the scripts | `FableF/small_fire_fx/Embers_*` |

- **Own kit folder**: stream F's sources live in `PhotorealPass/FableF` and import into `/Game/Dink/Photoreal/FableF`, so the import never rewrites the Unclaimed kit's `M_Struct_Baked` or its manifest.
- **A flipbook row may say `"blend": "translucent"`** (manifest `flipbooks`): its instance hangs off `M_FX_Flipbook_Blend` (unlit, translucent, alpha = opacity; pixels brighter than `Hot.x` glow by the glow factor). Without it the row is additive (`M_FX_Flipbook`), as before.
- **What binds at runtime**: a `families.json` effect row with `"effect_placed": true` also draws on PLACED sprites, on manifest-dressed screens too (screens 1 and 439): `UDinkArtFamilySubsystem::DressPlacedEffect` gives the sprite's own upright card the effect material, grows it by 1 / `effect_fit` about the middle of its bottom edge, stands it on the ground (`effect_ground`: a picture drawn above its sort point stands that far north), sinks it by `effect_sink` and adds the `effect_light` point light (no shadows). The card keeps facing the camera and keeps its vision and current-screen rules. Rows without `effect_placed` behave as before (script sprites only).
- **Hearth fire and fountain spray (16 Nov 2026)** ride the same path from the FableF kit: `FableF/hearth_fire/Hearth` (sequence 86: `blender -b --factory-startup -t 4 --python FableF/tools/build_fire_fx.py -- Hearth --cache <Fire_Wall cache> --stage atlas`, the compact fire cut from the wall of flame's frames) and `FableF/fountain_spray_fx/Fountain_Spray` (sequence 94: `python3 -I FableF/tools/build_fountain_spray.py`, no Blender). `python3 -I FableF/tools/make_kit_manifest.py`, then `DINK_KIT=FableF DINK_KIT_FOLDER=FableF Scripts/import_town_exteriors.sh` writes `MI_FX_Hearth`, `MI_FX_Fountain_Spray` and their textures. The hearth row is `"scripted": true` (S001_P20 carries a script) and S001_P20 left the Stonebrook room's `hide_origins`; the fountain row lifts its card onto the bowl with `offset_cm`.
- **Stairs (428)**: `blender -b --factory-startup -t 4 --python SourceAssets/Art/PhotorealPass/FableF/tools/build_stairs.py -- all final` writes `FableF/stairs_wood/Stair_Flight_L/_R` (frames 1, 3: the flight up in a ground-floor corner), `Stair_Well_L/_R` (frames 2, 4: the railed opening of the upper floor) and `FableF/cellar_hatch/Door_Barred` (frame 5); the same kit import brings them in as `/Game/Dink/Photoreal/FableF/SM_*_PR` with one baked material each (`M_Struct_Baked` of that folder). Bound by five sequence-frame rows of `families.json` (frames 1 and 2 also on their scripted placements: `s1-h3-5` and `s4-not` never change the picture). The flights and the barred doors carry `offset_cm` per placement: their 1997 points lie in the wall band of the picture, 1.8 to 3 m behind the drawn wall, so without it they stood hidden behind the wall; the flights are drawn at 0.77 (the picture's 3.4 m, a 2.7 m storey) with their back on the north wall and their top in the corner. The script reuses the board builder, bake and review scene of `Unclaimed/tools` without changing them.
- **Own kit folder**: stream F's sources live in `PhotorealPass/FableF` and import into `/Game/Dink/Photoreal/FableF`, so the import never rewrites the Unclaimed kit's `M_Struct_Baked` or its manifest.
- **A flipbook row may say `"blend": "translucent"`** (manifest `flipbooks`): its instance hangs off `M_FX_Flipbook_Blend` (unlit, translucent, alpha = opacity; pixels brighter than `Hot.x` glow by the glow factor). Without it the row is additive (`M_FX_Flipbook`), as before.
- **What binds at runtime**: a `families.json` effect row with `"effect_placed": true` also draws on PLACED sprites, on manifest-dressed screens too (screens 1 and 439): `UDinkArtFamilySubsystem::DressPlacedEffect` gives the sprite's own upright card the effect material, grows it by 1 / `effect_fit` about the middle of its bottom edge, stands it on the ground (`effect_ground`: a picture drawn above its sort point stands that far north), sinks it by `effect_sink` and adds the `effect_light` point light (no shadows). The card keeps facing the camera and keeps its vision and current-screen rules. Rows without `effect_placed` behave as before (script sprites only).
- **The flames' foot and ends** are made in `tools/fire_encode.py` (`foot_px`, `foot_soft`: the flames thin towards the floor from a height that wanders along the fire; `ends_px`: the wall's two ends thin out behind a boundary that wanders with height). With them the row's `effect_sink` stays near 0.02; a floor that cuts an opaque flame shows a ruler line. `--stage atlas` re-encodes from the cached frames in about 25 s.
- **The kit import runs `-nullrhi`**: under `Saved/Gate2Coord/unreal_turn.sh` export `DINK_GPU=0` for that step so it does not wait for the GPU lock.
- **Own kit folder**: these sources live in `PhotorealPass/FableF` and import into `/Game/Dink/Photoreal/FableF`, so the import never rewrites the Unclaimed kit's `M_Struct_Baked` or its manifest.
- **Flipbook rows** (manifest `flipbooks`): `"blend": "translucent"` hangs the instance off `M_FX_Flipbook_Blend` (unlit, translucent, alpha = opacity; texels brighter than `Hot.x` glow by `glow`; `"hot": [lo, hi, base]` sets the thresholds), anything else off the additive `M_FX_Flipbook`. `"loop": false` plays once and holds the last frame from the card's `StartTime`; `"camera_offset_cm"` draws the card that much nearer the camera. A kit builds only the masters its rows use.
- **A material that fails to compile is silent in the import log.** After a change to the masters look for `Failed to compile Material` in the log of a rendered run (`Saved/PhotorealPass/lighting/tools/capture.log`).
- **What binds at runtime**: a `families.json` effect row with `"effect_placed": true` also draws on PLACED sprites, on manifest-dressed screens too (screens 1 and 439): `UDinkArtFamilySubsystem::DressPlacedEffect` gives the sprite's own upright card the effect material, grows it by 1 / `effect_fit` about the middle of its bottom edge, stands it on the ground (`effect_ground`: a picture drawn above its sort point stands that far north), sinks it by `effect_sink`, moves and sizes it by the row's `offset_cm` for that placement (roof and wall fires), adds the `effect_plume` smoke card where the row names the placement, and adds the `effect_light` point light (no shadows; `effect_light_flicker` makes it waver). The card keeps facing the camera and keeps its vision and current-screen rules. Rows without `effect_placed` behave as before (script sprites only).
- **Audit**: `art_coverage.py` counts actor placements of an `effect_placed` row as final by family (`placed_fx`), also on dressed screens; `hide_origins` still wins (S001_P21 was taken out of the Stonebrook room's list so its fire draws).

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
| What each screen's ground is made of | part of the world export (`Scripts/export_import_bundle.py`, run by `Scripts/import_greybox.sh --export`) | `tools/data/tile_classes.csv`, `terrain_layers.json` | `Content/Dink/Data/Environment/ground_classes.json` (per screen: tile classes, the layer of each, the layers the mask carries, the layers it dropped, water surface, `water_sea` 0 pond .. 1 sea, which `screens.json` also carries for the importer's water instances) |
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
- **Water without a water fill** (seven screens): the export shapes a shoreline (`natural_shore`, the same as every other water screen since 15 Nov 2026), writes its distance into the terrain mask alpha and flags sea shores (`water_sea`); the runtime draws one `M_Env_WaterShore` sheet per screen with that mask (`environment.json` `water_tiles`, `dink.WaterTiles`). A change needs a world export and import (the masks), no material rebuild.
- **Natural shorelines** (15 Nov 2026): every water outline is smoothed in world space and drawn 10-25 px past the 1997 one (`natural_shore`); the importer lays the water surface over `screens.json` `water_draw`; `ground_classes.json` `water_block` are player-only blockers over the drawn water on 1997-walkable ground (`dink.WaterBlockers`). A change needs a world export and import only.
- **Water across screen borders** (15 Nov 2026): the terrain mask alpha (shore distance) is measured with the world-adjacent neighbours' water round each screen and stored edge to edge (texel 0 on x = 0, texel 95 on x = 600), so both screens of a border hold the same value there (`shore_alpha`). The sea colour is nine weights per water screen (`water_sea_patch`: corners, edge middles, centre; joined screens share their edge values) that `M_Env_WaterShore` blends by the screen UV (`SeaNW` .. `SeaSE`; pond `Absorption`/`Scattering`/`ScumAmount` to sea `SeaAbsorption`/`SeaScattering`, blended geometrically). A change to the material needs `DINK_ENV_MATERIALS_ONLY=1 Scripts/import_environment_materials.sh` (keep only `M_Env_WaterShore.uasset`), then a world export and import.
- **Snow and ice exposure** (`environment.json` `snow_exposure`, `dink.SnowExposure`): outdoor screens whose tiles are mostly snow or ice get an exposure compensation (0.8 EV at a 60% share, eased), because the automatic exposure meters white ground down to grey. No import step; the shares come from `ground_classes.json`.
- Proof that nothing gameplay moved: the export's `collision.json`, `placements.json` and `warps.json` are byte-identical before and after; unit tests `Scripts/tests/test_ground_export_helpers.py`. Before/after sheets: `python3 -I Scripts/PhotorealQA/ground_compare_sheet.py <before dir> <after dir> <out dir>`.

## Meadow ground under the grass carpet (round 7, 14 Nov 2026)

- `environment.json` `grass.ground_tint` (linear r, g, b) multiplies the meadow layer (`grass.layer`) of every terrain instance toward the colour of the grass that stands on it: greybox grounds, authored meadow meshes and the backdrop get a dynamic instance with `Tint<A|B|C|D>` set for the slots that carry that layer (`UDinkEnvironmentSubsystem::TintMeadowGround`, once, a few seconds after the start; nothing in headless runs). Other layers of the same screen (RockyGrass, earth, sand) keep their colour.
- `M_Env_Terrain` gained the vector parameters `TintA` to `TintD` (white = unchanged). After a material rebuild (`DINK_ENV_MATERIALS_ONLY=1 Scripts/import_environment_materials.sh`) keep `M_Env_Terrain.uasset` and restore the other re-saved packages unless they changed too.
- `-dpcvars=dink.GroundTint=0` keeps the scan's own colour. Evidence: `Docs/Verification/PhotorealRound7/README_ground_tint.md` (`ground_tint_*`).

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

## Interior light (round 7, 14 Nov 2026)

Runtime only (`UDinkEnvironmentSubsystem::BuildIndoor`, nothing of it in headless runs), values in `environment.json` `indoor.<look>`:

- `ceiling_lamp_light` false: the ceiling planes sit on lighting channel 1, which only the even fill lights. The lamps, fires and the ambient point (channel 0) no longer burn an inverse-square disc into the boards 0.85 m above a lantern. Leave the key out or set it true for the old behaviour.
- `lamp_source_cm`: source radius of the shadowed lamps and fires (interior 14, dungeon 10; was fixed at 6): softer shadow edges.
- Interior look: lamps 26 cd (was 18) as the warm key, the fill lower and cooler (0.2 of 0.80, 0.87, 1.0; was 0.26 of 1.0, 0.88, 0.72), ambient 0.6 (was 1.0), so corners fall off toward cool. Evidence and what is still wrong: `Docs/Verification/PhotorealRound7/`.
- Captures: `Scripts/PhotorealQA/r7_script.py <tag> [name parts]` writes the round-7 camera script (interiors `i0`, grass `g`, foliage `f`; shots under `Saved/PhotorealPass/round7/<tag>/`).

## Creature classes (13 Nov 2026)

`Content/Dink/Data/Art/creatures.json` has a second list, `classes`: one row binds a sprite class (`tools/data/sprite_classes.csv` `class_id`) to an animated creature, and every placement of that class on every screen, and every sprite a script creates with one of the row's sequences, is shown by it instead of a sprite card. The eleven origin rows (`placements`) keep precedence, as does any origin another `Data/Art` manifest names.

| Class | Mesh | Clips | Corpse | Import |
|---|---|---|---|---|
| `pillbug` (154 placements, sequences 131/133) | `/Game/Dink/Photoreal/Creatures/Pillbug/SK_Pillbug_Photoreal` | `AN_Pillbug_Idle`, `_Walk` (80 cm/s), `_Run` (400 cm/s) of `/Game/Dink/Creatures/Pillbug/Animations` | `SM_Pillbug_Corpse_PR` for death sequences 141/143, with the ground decal `M_Pillbug_BloodPool_Decal` | already imported (`DINK_PHOTOREAL_ONLY=pillbug Scripts/import_photoreal_art.sh`) |
| `duck` (106 placements, sequences 21-29; headless 111-119) | `/Game/Dink/Photoreal/Creatures/Duck/SK_Duck_PR`, headless role `SK_Duck_Headless_PR` | `AN_Duck_Idle`, `_Walk`, `_Run`, `_Scurry` (800 cm/s); headless `_HeadlessRun`, `_HeadlessScurry` | none: the first hit throws `SM_Duck_HeadFlying_PR`, which lands as `SM_Duck_Head_PR` in a puddle decal; the second hit is a `bursts` row (sequence 164) | `DINK_PHOTOREAL_ONLY=duck Scripts/import_photoreal_art.sh` |
| `slime_blue`, `slime_green`, `slime_red` (sequences 651/653, 671/673, 691/693) | `/Game/Dink/Photoreal/Creatures/Slime/SK_Slime_PR`, colours by `materials` | `AN_Slime_Idle`, `_Walk` (250 cm/s) | `SM_Slime_Splat_<Colour>` with `M_SlimeSplat_<Colour>_Decal` for death sequences 661/663, 681/683, 701/703 | `DINK_PHOTOREAL_ONLY=slime Scripts/import_photoreal_art.sh` |
| `pig` (the placements without an origin row, sequences 41-49) | `/Game/Dink/Photoreal/Creatures/Pig/SK_Pig_Photoreal` on the existing pig skeleton | `AN_Pig_Idle`, `_Walk` (90 cm/s), `_Run` (400 cm/s) of `/Game/Dink/Creatures/Pig/Animations` | none: a `bursts` row (pig_brain turns the pig into sequence 164) | `DINK_PHOTOREAL_ONLY=pig Scripts/import_photoreal_art.sh` |

- **Row format**: `class`, `mesh`, `locomotion` (`idle` clip and `gaits`: `clip`, `speed_cm_s` the clip was made for, optional `cycles`; slowest first), `roles` (a name -> `sequences` plus either `"locomotion": true`, an own locomotion object, or a `clip` with optional `loop` and `mesh`), optional `corpses` (`sequences` = base_death + facing, `mesh`, `offset_cm`, `yaw_offset`, `scale`, and `decal`: `material`, `size_cm` [along, across], `depth_cm`), `materials` (slot -> material, for colour variants of one mesh), `scale`, `offset_cm`, `rotation_deg`, `smooth_time_s`, `turn_rate_deg_s`, `blend_time_s`, `stationary_speed_cm_s`, `cull_distance_cm`. A row that does not parse, or names an asset that is missing or on another skeleton, binds nothing and its sprites keep their cards (warning in the log).
- **What the runtime does** (`UDinkCreatureSubsystem`, `UDinkCreatureClassComponent`, `UDinkCreaturePresenter`): at begin play each placement actor of a bound class gets the body and its card's picture is hidden; a script-made sprite gets its body on the frame it appears. At the end of every frame (`TG_PostUpdateWork`: the story moves sprites from a tickable object, after the actor tick groups, so an earlier step would show last frame's position) the presenter reads each sprite's sequence, frame, direction and size and the body follows its actor. The sprite's whole-pixel 60 Hz steps are shown as continuous motion (`FDinkBodySmoother`, the averaging the humanoid bodies use, `smooth_time_s`), the body faces along that motion and, standing, the sprite's direction (`turn_rate_deg_s`), locomotion is a native blend of idle and gaits whose cycle advances by distance over stride (no blend space asset), and a role that is a clip plays over the duration of the sprite sequence it stands for, cross-faded (`blend_time_s`). A kill by damage (`add_kill_sprite`, dink.cpp:12359) leaves the row's corpse where the body stood until the player leaves the screen; a sprite removed by a script leaves nothing, as in the original. A sprite without a death sequence leaves no corpse either; the original plays the blood burst 164 for it (dink.cpp:12384-12389), which is not drawn yet (it comes with the ducks, whose second death is that burst).
- **The pillbug carcass** (rebuilt 13 Nov 2026 on the owner's order "increase the blood, like the 1997"): `Creatures/Tools/pillbug.py -- corpse` (`Tools/bl.sh pillbug.py -- corpse`, about two minutes on the GPU) poses the rig burst open, composites blood across the shell in texture space from the posed world positions (`T_Pillbug_Corpse_BC/_ORM`, about half of the up-facing shell, as sprites 141/143 show it; the body slots are `MI_Pillbug_*_Bloody`), builds a lobed pool with thrown streaks and drops and the viscera (`T_Pillbug_Gore_*`), and renders the gore from straight above into `T_Pillbug_BloodPool_BC` (RGBA, a 4.4 m square). The game lays that picture under the carcass as a deferred decal (45 cm deep), because the grass carpet hides any flat mesh: on grass the blades are stained, on bare ground the modelled pool lies on top of the same outline. The carcass mesh receives no decal. `DINK_PHOTOREAL_ONLY=pillbug Scripts/import_photoreal_art.sh` imports all of it.
- **Gore rows** (14 Nov 2026; the owner's rule: keep all of the 1997 gore). A role may carry `gore`: `bone`, a fountain (`drops_per_second`, `drop_speed_cm_s`, `spread_deg`, `drop_size_cm`), a `trail` decal (`material`, `every_cm`, `size_cm`) and a `severed` part thrown when the sprite enters the role from another one (`flying` mesh, `landed` mesh, `decal`, `decal_size_cm`, `speed_cm_s`, `drops`). A row may carry `bursts` (`sequences`, `brain`, `drops`, `drop_speed_cm_s`, `drop_size_cm`, `decal`: `material`, `size_cm`; the core of sequence 164: `blobs` (up to 2,000), `blob_size_cm`, `radius_cm`, `duration_s`, `feathers`, with the row's `blood_blob` and `feather` meshes): the blood shown when the kill path turns the sprite into sequence 164 (`FDinkSprite::bBurstKill`, set only by `UDinkGameplay::ProcessDamage`; a sprite a script removes bursts not). Both need the row's `blood_drop` mesh. Runtime: `DinkCreatureGore.cpp` (`EmitBlood`, `AddBloodDecal`, `ThrowPart`, `Burst`, `StepGore`); at most 3,000 particles (fountains stop at 500) and 96 stains (the oldest is moved at the cap), all gone when the screen is left. Materials: `M_BloodDrop`, `M_BloodBlob` (matt dark red, 15 Nov 2026), `M_Feather`, the decals `M_BloodBurst_Decal` / `M_BloodPuddle_Decal`, built by the `duck` section; the slime splatter decals take an optional colour `tint` and `opacity_gain` in `decal_material` (red: brown-red as 701/703). Sources: `Creatures/Tools/gore_fx.py` (`SM_BloodDrop`, `T_BloodBurst_BC`, `T_BloodPuddle_BC`, `SM_Duck_HeadFlying`, the slime splatter), `Creatures/Tools/duck_scurry.py` (the 800 cm/s gaits). The duck: first hit = the head flies off and lies in its pool, the body runs on with blood spraying from the neck and leaves a trail (dink.cpp duck_brain 12745-12775, sprite sequences 111-129); second hit = the burst of sequence 164 (12728-12740). `dink.Hurt <origin> <damage>` is a review command for captures of these.
- **Pig**: `Creatures/Tools/pig.py` was changed on 14 Nov 2026 after the review "the body is lumpy" (calmer surface noise, shallower hollows and neck folds, one rounded rump). The five Stonebrook pigs keep their origin rows; `dink.PhotorealPig` (default 1) gives them the same mesh while the process renders.
- **What it never does**: no collision, no body boxes, no overlap events, no actor tag gameplay reads (`DinkCreature` and `DinkAuthoredArt` stay with the origin rows), no write to a sprite, an actor transform or the random stream. Touch damage, hits, experience, drops, hardness and scripts are the simulation's, as before.
- **Switch**: `dink.CreatureClassArt` 0 = off (cards), 1 = while the process renders (default), 2 = also headless (the automated tests use it). Headless runs keep the cards, like `dink.PhotorealPillbug`. `dink.CreatureClasses` logs every followed body (role, speed, cadence, yaw).
- **Coverage**: `Scripts/art_coverage.py` counts these placements `final` with evidence `class-bound:` (`creature_class_rows`, `creature_class_binding`).
- **Captures**: `Scripts/CreatureQA/make_scripts.py` writes before/after capture scripts for `Scripts/PhotorealQA/run_capture.sh`; results and what was seen: `Docs/Verification/CreatureClassBinding_13Nov2026/`.

## Monsters: bonca, slayer, stone giant (15 Nov 2026)

The rigged monsters of `Unclaimed/` had no clips and were bound nowhere (cards). Now each is a creature class
(`creatures.json` `classes`: `bonca_gray`, `bonca_brown`, `bonca_purple`, `slayer`, `stone_giant`), with its corpse.

- **Sources** (Blender, `Unclaimed/tools/bl.sh <script>`; pull `ThirdParty/polyhaven/{forrest_ground_01,rock_boulder_dry}`
  from LFS first): `build_bonca.py final` (the hide is baked as a code: detail, stripe, leg, and painted three times:
  grey with near-white stripes 601, brown with orange stripes 531, violet with lilac stripes 611; white eye),
  `build_slayer.py final` (teal chitin plates, open jaw, the whip tail level behind it, 4.3 m), `build_giant.py final`
  (brown bedded sandstone, eye stones in sockets, hardened skin weights). Then the clips, which the build wipes:
  `clips_bonca.py build review export`, `clips_monsters.py <slayer|giant> build review export` (Idle, Walk, Run, Attack,
  Hit, Death; `clips.json` holds the measured gait speeds; the same run freezes the last frame of the death clip as
  `SM_<Name>_Corpse_PR.fbx`, centred, and for the giant breaks it at the joints into ten blocks piled as a heap),
  `python3 -I corpse_blood.py` (soaked corpse skin, `T_<Name>_PR_BloodPool_BC.png`: a lobed pool with runs and about
  150 thrown drops, and the giant's `T_Stone_Giant_PR_Grit_BC.png`), and `export_monster_ue.py <bonca|slayer|giant>`
  (`Export/`, the creature importer's convention; the kit's own `SK_*_LOD*.fbx` are refused by its gate).
- **Import**: `DINK_PHOTOREAL_ONLY=monsters Scripts/import_photoreal_art.sh` (or any of `bonca,slayer,giant`) ->
  `/Game/Dink/Photoreal/Creatures/{Bonca,Slayer,StoneGiant}`: `SK_<Name>_PR` with its own skeleton, `AN_<Name>_<Clip>`,
  `MI_<Name>_PR`, `MI_Bonca_Brown_PR`, `MI_Bonca_Purple_PR`, `SM_<Name>_Corpse_PR`, and the ground decals
  `M_Bonca_BloodPool_Decal`, `M_Slayer_BloodPool_Decal`, `M_Stone_Giant_Grit_Decal`.
- **Rows**: walk sequences are a locomotion role (idle, walk, run by measured speed); the attack sequences (bonca
  54x/59x/62x, slayer 63x, giant 81x) play `AN_<Name>_Attack` over the sprite sequence's own duration.
- **Deaths are what 1997 does**: no monster has a hit or death animation; a kill swaps the sprite for its corpse picture
  (`add_kill_sprite`, dink.cpp:12359: `base_death` + direction, or `base_walk` + 5 for a sprite without one, which
  `FDinkCreatureClassBinding::CorpseFor` now follows). Bonca 551-559: the brown body soaked red in its pool (all three
  colours leave the brown body, as the original's one death set), decal 6.8 x 5.3 m. Slayer 645: the body with its tail
  curled, in its pool, decal 6.4 x 5.0 m. Stone giant 825: the heap of its stones on dark grit, no blood (the picture has
  none). The Hit and Death clips are authored and, since 16 Nov 2026, played as presentation-only one-shots (see below).
- **One-shots (coordinator decision of 16 Nov 2026, reversible by the owner)**: 1997 has no hit or death animation; the
  remaster plays the authored clips over what the sprite shows, driven by simulation events (`one_shots` in each class row of
  `creatures.json`, `DinkCreatureOneShots.h`): a hit that costs life plays `Hit`; a kill still leaves the corpse, its blood pool
  and the hit blood at once (add_kill_sprite's moment), and a copy of the body plays `Death` from its last pose, wearing the
  corpse's blood-soaked material where the corpse is that body frozen; the corpse mesh is shown when the clip ends, moved on the
  ground by the export's death-last-frame-minus-corpse offset (`align_cm`, inside its pool). `dink.Creature.OneShots 0` restores
  the 1997 instant swap exactly (`dink.Creature.DeathClips 0` only the deaths). Owner decision of 16 Nov 2026: no creature
  hit or death clip is withheld. The stone giant's heap is reshaped against its death pose (broken into blocks), so its
  hand-over is a visible cut until a transition is authored (Fable queue). Slimes play `AN_Slime_Death` before the splat (the
  splat's stain is on the ground at the kill, its mesh shows at the clip's end). The duck: `AN_Duck_Hit` as the first hit
  beheads it (head-pop gore unchanged), `AN_Duck_HeadlessDeath` (`burst_death`) when the headless body is hit again: it falls
  and the burst of sequence 164 comes where it lies; `AN_Duck_Death` has no 1997 event (a duck always loses its head first)
  and is shown by `dink.Creature.ShowDeath duck` only.

## Monster: dragon (16 Nov 2026)

Class row `dragon` (16 placements). `Unclaimed/tools/bl.sh build_dragon.py final` (brown hide, thin pale wing skins between
finger spars, open jaw), then `clips_monsters.py dragon build review export` and `export_monster_ue.py dragon`; import with
`DINK_PHOTOREAL_ONLY=dragon Scripts/import_photoreal_art.sh` -> `/Game/Dink/Photoreal/Creatures/Dragon` (two-sided
material for the wings). Walk 201-209 is a locomotion role; there is no attack sequence (it spits fire while it treads),
so `AN_Dragon_Attack` plays as an upper-body one-shot (from `spine_02`) over the walk when its fireball (a missile sprite)
appears beside it, and `AN_Dragon_Hit` as above (one-shots, `dink.Creature.OneShots`). `AN_Dragon_Death` plays (owner decision of 16 Nov 2026:
no death withheld); since the dragon's own remains (below) are its death pose torn, the dying body wears their blood from the
kill and they take over at the clip's end, moved by the export's offset (`corpse.json`, `align_cm`); the tears and the
collapsed wing appear at that moment (the remains are reshaped). A kill leaves the corpse kit's `SM_Dragon_Corpse_PR` (212-218) at corpse
`scale` 1.7, so the remains are about two thirds of the live dragon's width, as 212/216 against 202.
## Hero weapons (15 Nov 2026, art row DS-04, bug A203)

Six hand-held meshes for the hero, kit `PhotorealPass/HeroWeapons` (built by `HeroWeapons/tools/build_weapons.py`, one baked
BC / N / ORM set each, the light sword also E): `SM_Hero_Sword_Long_PR` (item-sw1, 1997 picture 438/7), `SM_Hero_Sword_Claw_PR`
(item-sw2, 438/20), `SM_Hero_Sword_Light_PR` (item-sw3, 438/21), `SM_Hero_Bow_Wood_PR` (item-b1 and item-b3: 438/8 and 438/13
show the same bow, b3 only adds the flame arrow), `SM_Hero_Bow_Blue_PR` (item-b2, 438/12), `SM_Hero_Axe_PR` (item-axe, 438/6).

    HeroWeapons/tools/bl.sh all final                       # Blender: sources, bakes, FBX, per-asset manifest
    python3 -I HeroWeapons/tools/build_weapons.py --manifest  # kit manifest.json
    DINK_KIT=HeroWeapons DINK_KIT_FOLDER=Hero/Weapons Scripts/import_town_exteriors.sh   # -> /Game/Dink/Photoreal/Hero/Weapons

Grip convention (every mesh): origin at the grip centre, +X along the blade or haft to the tip (a bow: along its upper limb),
the blade's flats on +Z and -Z. Attach: swords and axe on bone `hand_r`, relative location (-7, 3, -0.5) cm, rotation pitch 90, yaw 0, roll 90 (seen in the game in the idle pose and in `Sword_Slash_1` / `Sword_Chop`: the blade leaves the thumb side of the fist, the claws of the claw sword are on the knuckle side); bows on `hand_l`, location (7, -3, 0.5), rotation pitch -90, yaw 0, roll 90, string hand `hand_r` (seen carried at his side and at full draw with `Bow_Draw`).
Nothing binds them at runtime yet: no families.json row, no attach by item (code, bug A203). `dink.Hero.Hold <mesh path | off>
[bone] [x y z pitch yaw roll]` (review only, not in shipping builds) puts one in the hero's hand for a capture.
## Structure sets (14 Nov 2026)

| What | Command | Reads | Writes |
|---|---|---|---|
| Bridge, island and cottage meshes | `DINK_KIT=Structures/Misc DINK_KIT_FOLDER=Structures Scripts/import_town_exteriors.sh` | `Structures/Misc/manifest.json` | `/Game/Dink/Photoreal/Structures/SM_Bridge_Wood_*_PR`, `SM_Island_*_PR`, `SM_Cottage_Thatched_*_PR` |
| Castle kit | `DINK_KIT=Structures/Castle DINK_KIT_FOLDER=Structures Scripts/import_town_exteriors.sh` | `Structures/Castle/manifest.json` | `/Game/Dink/Photoreal/Structures/SM_Castle_Wall_8m`, `SM_Castle_Tower_Round`, `SM_Castle_Gatehouse`, `MI_Struct_CastleAshlar`, `Textures/T_Terrain_CastleAshlar_*` |
| The two-storey house and its yard props (Stonebrook440 kit) | `Scripts/import_stonebrook440.sh` | `SourceAssets/Art/Stonebrook440/art_manifest.json`, `Export/LODs/*.fbx`, `Textures/` | `/Game/Dink/Kits/Stonebrook440/SM_*`, `/Game/Dink/Materials/Stonebrook440/MI_*`, `/Game/Dink/Textures/Stonebrook440/T_*` (no runtime manifest: the kit's layout is not published) |
| The sets | `python3 -I Scripts/assemble_structures.py` (in a tree with `ImportData/` and `tools/dinkex/out`), then `python3 -I Scripts/PhotorealQA/structure_walk_check.py` | placements, collision, screens, sequences | `Content/Dink/Data/Art/structure_sets.json` |

- **What binds at runtime**: `structure_sets.json` beside `town_houses.json` (same loader, same switch `dink.TownHouses`). A set hides the cards it names and shows its modules; nothing else changes.

## Monsters: goblins (16 Nov 2026)

Class rows `goblin_hammer` (761-769, attack 751-759), `goblin_soldier` (801-809, attack 791-799) and `goblin_horned` (Mog,
781-789, attack 771-779 and 780; script-made, no placement). `Unclaimed/tools/bl.sh build_goblin.py all final` (needs the
`rusty_metal_02` scan from LFS): a bare body, garments as separate shells with hems, and gear that is rigid in the game mesh
(helmet on `head`, weapon on `hand_r`, shield on `lowerarm_l`). Then per goblin `clips_monsters.py goblin_<kit> build review
export` (the knight's pose functions; the dead goblin's weapon comes to lie beside him), `export_monster_ue.py goblin_<kit>`,
and `python3 -I corpse_blood.py`. Import: `DINK_PHOTOREAL_ONLY=goblins Scripts/import_photoreal_art.sh` ->
`/Game/Dink/Photoreal/Creatures/Goblin{Hammer,Horned,Soldier}` (hit and death clips are delivered with the walk and attack
clips; the creature one-shots play them: a hit that costs life plays `Hit`, a kill plays `Death` into the corpse, which is that
body frozen, moved by `corpse.json`'s offset, `align_cm`). A kill leaves `base_walk + 5` (765 / 785 / 805): the body on
its back, drenched, in a pool with thrown drops (`M_Goblin_<Kit>_BloodPool_Decal`, corpse `scale` = the row's `scale`).
`corpse_blood.py` (all monster corpses, the bonca's and the slayer's too): a pool is dark where the blood stands (from a
hand's width inside the rim, and in blotches) and bright only at its thin rim, with runs and drops in the drying tone; the
blood on a body is as dark as its pool and tacky rather than glossy. A pool on grass only reddens the grass (the carpet
does not open under corpse decals yet). To see a goblin corpse in a capture send `dink.Run <its script> hit <origin>` before
`dink.Hurt <origin> 900`: `dink.Hurt` does not run `hit`, and the goblins' `hit` is what makes them brain 9.

## Dragon remains (16 Nov 2026)

A killed dragon no longer leaves the corpse kit's tan dragon but its own remains: `clips_monsters.py dragon build export`
freezes the death pose and tears it (`tear`: at the neck, the root of the wing under the body, one hip and half way down the
tail; the tear faces take the raw flesh painted into the corner of `T_Dragon_PR_Corpse_BC.png`; the trunk is set down on its
spine and ribs, the torn wing is collapsed flat, every thrown piece is laid on its thinnest axis, and the upper wing still
stands from the carcass, bloodied, as picture 212 has it), `corpse_blood.py`
soaks about three quarters of the brown hide, keeps the standing wing's skin pale away from its root (`corpse_wing_uv.json`,
written by `tear`) and writes `T_Dragon_PR_BloodPool_BC.png`; the importer makes `SM_Dragon_Corpse_PR`,
`M_Dragon_Corpse_PR` and `M_Dragon_BloodPool_Decal` in `/Game/Dink/Photoreal/Creatures/Dragon`. The placed 216 card keeps the
kit asset (`families.json`). Every monster corpse gets three LODs at import (`corpse_lods`: 100 / 50 / 25 % of the triangles,
switching at about 10 m and 20 m); `corpse.json` beside each source gives where the corpse lies against the death clip's last
frame.

## Explosion, fire and blood-burst effects (16 Nov 2026, art rows GP-Q9 and CG-6)

Sprites that scripts and the engine create with the pictures 167 (explosion), 164 (blood burst), 161 (fire burst), 70 (small
explosion) and 512 (falling fireball) drew the grey script-sprite marker. Each now has an effect row in `families.json`
(`"effect"`, as the gold twinkle): a camera-facing card with a flipbook.

- Sources: `Unclaimed/explosion_fx/Shock` (167), `Unclaimed/explosion_small_fx/Splode` (70), `Unclaimed/fire_burst_fx/Atomic`
  (161), `Unclaimed/blood_burst_fx/Blood_Burst` (164), built by `Unclaimed/tools/build_fx_vol.py` (numpy fields -> OpenVDB ->
  Cycles volume render; the blood burst is 4,200 mesh drops in a red mist); 512 uses the older `fireball_fx/Fireball` loop.
  `blender -b --factory-startup -t 4 --python Unclaimed/tools/build_fx_vol.py -- all` (about 25 minutes), then
  `python3 -I Unclaimed/tools/make_kit_manifest.py` and the Unclaimed kit import
  (`DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh`).
- A flipbook's manifest gives `grid`, `fps` (= frames / life of the 1997 sprite), `loop`, `glow` and `ue_blend`. `ue_blend: alpha`
  goes to the new master `M_FX_Flipbook_Blend` (translucent, unlit; texels brighter than mid grey glow by `Grid.a`, dark ones keep
  their colour: smoke, blood); everything else stays on the additive `M_FX_Flipbook`. Both masters have the scalars `StartTime`
  (world seconds; `UDinkArtFamilySubsystem::DressScriptSprite` sets it on a dynamic instance when the card appears), `OneShot`
  (1 = play once and hold the last frame) and `CameraOffset` (cm towards the camera, 0 by default).
- After the render `build_fx_vol.py` grades every one-shot fire atlas with `tools/fx_grade.py` (orange fire, no veil of light round the shapes, colour spread under the transparent texels) and writes `glow` 1.6 and `hot` [0.55, 0.95, 1.0] into the manifest; `make_kit_manifest.py` passes `hot` on to the kit row. Atlases rendered before the tool existed were graded once with `python3 -I Unclaimed/tools/fx_grade.py Shock Splode Atomic` (the manifest's `graded` flag stops a second pass).
- The build chooses the GPU by itself (`pplib`, `build_fx_vol.py`): set `DINK_CPU=1`, or run it through `Saved/Gate2Coord/gpu_turn.sh`. The kit import runs `-nullrhi` (`DINK_GPU=0` under `unreal_turn.sh`).
- The tool also renders loops (`loop: true`: every noise field climbs a whole number of its periods over the loop, so it closes); the hearth fire of the follow-up change uses that.
- Missiles (16 Nov 2026): the fireball spell (502, 504, 506, 508) and hellfire (512 to 518) fly as `MI_FX_Fireball` (south, north) and
  `MI_FX_Fireball_W` / `_E` (west, east). The two side copies are kit rows with `"roll"` (0.75, 0.25: the flipbook scalar `Roll` turns
  the picture inside its square card), listed as `flipbook.variants` in `fireball_fx/Fireball/manifest.json` (`build_fx.py` writes
  them); `make_kit_manifest.py` emits a variant only when a `families.json` row names its material. No second texture, no rebuild of the
  frames: after changing a roll run `make_kit_manifest.py` and the Unclaimed kit import (`-nullrhi`: under `unreal_turn.sh` set `DINK_GPU=0`).
- The card lives exactly as long as the sprite (frames x frame delay of `dink.ini`): 167 0.42 s, 164 0.70 s, 161 1.30 s,
  70 0.60 s. Effect rows dress script-created sprites only; placed effect sprites (screens 1 and 366) keep their cards.
## People: townsfolk, guards, the gnome wizard, the King, Seth (16 Nov 2026)

| What | Command | Source | Unreal |
|---|---|---|---|
| Port the Unclaimed people onto the mannequin rig | `cd SourceAssets/Art/PhotorealPass/Characters/Tools && blender -b -t 4 --python npc_port.py -- all` | `Unclaimed/<family>/<Name>/SK_<Name>_PR.blend` (26-bone rig, same bone names) | writes `Characters/NPC/<Name>/Export/*.fbx`, `manifest.json` (points at the Unclaimed textures), filler maps |
| Colour twins, Seth's outfit map | `python3 -I npc_variants.py` | the Mother's, Milder's and the hero's outfit maps, the Unclaimed knight's and merchant's maps | `Characters/NPC/variants.json`, recoloured outfit maps |
| Seth | `blender -b -t 4 ../Dink/SK_Dink_Photoreal.blend --python seth_build.py`, then `blender -b -t 4 ../NPC/Seth/SK_Seth_Photoreal.blend --python export_char.py -- <abs>/NPC/Seth/Export <abs>/NPC/Seth/export_report.json character_hero`, then `python3 -I seth_manifest.py` | the hero's blend and texture sets | `Characters/NPC/Seth` (own mesh, the hero's textures shared) |
| Import | `DINK_PHOTOREAL_ONLY=npcs Scripts/import_photoreal_art.sh` (the hero, the Mother and Milder must be imported: twins are copies of them, Seth uses the hero's textures) | `Characters/NPC/*/manifest.json`, `variants.json` | `/Game/Dink/Photoreal/Characters/NPC/<Name>/SK_<Name>_Photoreal` |
| Bind | `python3 -I Scripts/bind_people_classes.py` | manifests' and twins' `placement_scale`, the walk bases in the script's table, `bin/dink/dink.ini` | `classes` rows of `Content/Dink/Data/Art/creatures.json` |

- **What binds at runtime.** One class row per 1997 walk base (`DinkCreatureClass.h`): every placement of that sprite class on every screen and every sprite a script makes or dresses with the walk pictures (`create_sprite`, `sp_base_walk`) is shown by the figure, with the mannequin's idle, walk and jog by measured speed. Presentation only: no body, no collision, no actor tag, off in headless runs; talk, hit and touch keep the 1997 boxes. `dink.CreatureClassArt 0` shows the cards again. The Mother stays the origin row of `characters.json` she was.
- **Why not origin rows.** A `characters.json` placement row gives the actor a drawn body that replaces the 1997 talk, hit and touch boxes (1.5 m reach); the story probe failed on the gravedigger with it. See `AGENTS.md`.
- **Standing figures** face as their picture: the direction is the last digit of the sequence (the guards of the throne room are 287 and 289). The King's row turns him 45 degrees to face the hall (421 reads as direction 1).
- **Sizes**: a ported mesh is carried to the mannequin's joints, so every one is about 1.8 m in the file; the row's `scale` (the manifest's `placement_scale`) gives the girl, the gnome and the old man their height back and makes Seth 1.3 times a man. Gait speeds are scaled with it.
- **Colour twins** are copies of an imported mesh with instances of the base's material instances (another base colour map and/or `Tint`): the three maidens (with a younger skin set, `NPC/Maiden`) and the woman in green are the Mother's, the soldier is Milder's; red, silver and gold knights share the blue knight's mesh; green, red and purple townsmen the blue merchant's. **When a base was re-imported, remove the twins' folders (`Content/Dink/Photoreal/Characters/NPC/<Twin>`) before the import**: the importer stops and says so.
- **The King** (`NPC/King`, S070_P03) is the Unclaimed set piece whole, on the root bone: he sits and does not animate.
- **No deaths here.** A killed person leaves the 1997 death picture (base + 5) as before; the bodies are the corpse kit's rows.

## Turning the pass off

Everything is presentation only and off in headless runs (`FApp::CanEverRender()` is false under `-nullrhi`), except the family bindings of `families.json`, which also dress placements headless (no collision, no gameplay). Command-line switches (`-dpcvars=a=0,b=0`):
`dink.PhotorealHero=0`, `dink.PhotorealPillbug=0`, `dink.CreatureClassArt=0` (class-bound creatures), `dink.PhotorealNPCs=0` (Mother and Milder), `dink.TownHouses=0`, `dink.FamilyArt=0` (all family meshes, the old ones included), `dink.EnvMaterials=0`, `dink.IndoorEnv=0`, `dink.IndoorLitCards=0`, `dink.StateSwaps=0`, `dink.GrassDensity=0`, `dink.GroundTint=0`, `dink.Wind=0`, `dink.Backdrop=0`, `dink.InteriorExposure=0`. `dink.EnvMeshSwaps=0` is meant to restore the old Stonebrook vegetation and structures but crashed at start in round 6 (segmentation fault): do not rely on it until that is fixed. The sky light tint has no cvar: set `environment.json` `sky.tint` to 1, 1, 1.
