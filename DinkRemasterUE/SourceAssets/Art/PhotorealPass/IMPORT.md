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
- Hero: imported with its own skeleton, checked against the shared 89-bone rig by the native bind-pose gate, then assigned to the shared skeleton; four LODs; skin uses a subsurface profile (`SP_Dink_PR_Skin`), hair is masked two-sided with dithered opacity. Morph targets are imported: the hero's build keys `Physique_Scrawny` and `Physique_Brawny` (`Characters/Tools/physique.py`, driven from hero confidence; `dink.HeroConfidence 0..1` shows any stage) must arrive on every LOD or the import stops. The hero's parent materials are compiled for morph targets (without it a shaped body draws black in the game), and before a re-import the mesh is given FBX import data with the importer's settings (a re-import ignores the task's options and `import_lod` leaves Interchange import data behind).

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
- **Gore**: a mesh that is less gory than its sprite is not bound (owner rule: keep all original gore). The dead dragon and the dead knight stay sprite cards for that reason; `Unclaimed/STATUS.md` says what each source lacks.
- **Pickups** (hearts, small coin scatter) use `fit: footprint`: a pickup is shown at the size the original draws it, not at the size of the modelled object.
- **Checks and captures**: `Docs/Verification/UnclaimedFamilyBinding_12Nov2026/`.

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

## Turning the pass off

Everything is presentation only and off in headless runs (`FApp::CanEverRender()` is false under `-nullrhi`), except the family bindings of `families.json`, which also dress placements headless (no collision, no gameplay). Command-line switches (`-dpcvars=a=0,b=0`):
`dink.PhotorealHero=0`, `dink.PhotorealPillbug=0`, `dink.PhotorealNPCs=0` (Mother and Milder), `dink.TownHouses=0`, `dink.FamilyArt=0` (all family meshes, the old ones included), `dink.EnvMaterials=0`, `dink.IndoorEnv=0`, `dink.IndoorLitCards=0`, `dink.StateSwaps=0`, `dink.GrassDensity=0`, `dink.Wind=0`, `dink.Backdrop=0`, `dink.InteriorExposure=0`. `dink.EnvMeshSwaps=0` is meant to restore the old Stonebrook vegetation and structures but crashed at start in round 6 (segmentation fault): do not rely on it until that is fixed. The sky light tint has no cvar: set `environment.json` `sky.tint` to 1, 1, 1.
