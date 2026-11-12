# Stonebrook fire ruins (story 3+)

Burning and burnt states of Dink's house: screen 439 (cottage exterior, vision 1 = burning, vision 2 =
burnt) and the burnt interior modules for SCR_001 (vision 2; vision 1 keeps the intact modules and adds
fire emitters). Original project art: deterministic Blender geometry plus numpy/Pillow procedural textures,
seed 31439. No downloaded meshes or images and no generative image models. Ledger status: **candidate**.
Nothing here has been imported into Unreal. Unreal was not launched at any point.

## Realism pass 2 (owner-approved) and grim content

- **Masonry.** Both cottage states now use random-bond rubble instead of four regular courses (`ruin_common.rubble_layout`):
  - varied course heights and stone lengths, with stacked and pinning stones and per-vertex irregular faces;
  - a recessed lime-mortar core showing mortar loss;
  - burnt state only: calcined whole stones, heat-spalled faces near the openings, and soot streaks washed down from the sills.

  Stones stay inside the intact wall envelope. Collision is the intact cottage's six hulls, unchanged.
- **Burnt roof.** The discrete reed tubes (which read as shingles) are replaced by one charred, matted, sagging thatch mass (`thatch_mass` in `build_ruins.py`):
  - clumping, dips between the rafters, and slumping towards the openings;
  - torn, drooping edges with loose straw hanging into the holes;
  - matted clumps lying on the surface;
  - charred hazel wattle woven over the laths, exposed under the openings.

  The burning state keeps the intact reed bundles.
- **Separate burning-state facades.** `MI_Ruin_FacadeFrontBack_Burning` and `MI_Ruin_FacadeSides_Burning` have clean limewash. Soot is only above the openings that vent fire (door, front windows at x = 1.5 / 7.5, back window at −3) and under the burning roof sections. The burnt facades add a general smoke film and soot that holds below 2 m, plus a foot-of-wall grime band.
- **Ground scorch.** The 6 m slab is replaced by four small feathered masked patches: `SM_Decal_Scorch_Ground_3m_01`, `_2m_01`, `_2m_02` and `_1m5_01`. Each has stochastic edge coverage, singed grass, burnt stubble, partial char, downwind ash drift, and 2 cm of height relief. They are scattered as nine patches (`ruin_common.GROUND_SCORCH`).
- **The mother's body (owner decision: keep the original's grim content).** The 1997 vision-1 interior shows the mother dead on the floor of the burning room: S001_P34, seq 355 `people/mom/death-`, a red body in a spread of blood droplets. `s1-h1-s` has Dink cry "Mother noooooo!" over her.
  - `SM_Mother_Remains_Fire_01` reproduces her. It is a static, posed copy of `Characters/SK_Mother.blend` (opened read-only), made by `tools/pose_mother_remains.py`: face down, head turned on the cheek, an arm flung out, a leg drawn up, the skirt settled by weight.
  - Her LOD1–3 become this prop's LOD0–2 (16k / 8k / 3.9k triangles).
  - It uses a smoke, scorch and blood pass on a 2048 copy of her atlas (`T_RuinMother_Atlas_*`).
  - It is class `foliage` only for the validator profile: non-Nanite, open hair/cloth surfaces, authored LOD chain.
  - `SM_Decal_Blood_Floor_01` is the blood pool with cast-off droplets (masked; tacky, half-dried sheen).
  - Both are vision 1 only, as in the original. In vision 2 the body is gone.
  - Provenance: the CC0 MakeHuman anatomy and project wardrobe of the mother (see `Characters/README.md`).
  - The exterior screens contain no grim imagery. Their dark comedy (Ethel: "if you hadn't killed my duck, your mom might still be alive") is script dialogue and is untouched.

## Contents

| Asset | Class | Size (m) | LOD0/1/2 tris | Notes |
|---|---|---|---|---|
| `SM_Cottage_Stonebrook_Burning_01` | building | 18.83 × 10.55 × 7.93 | 169,932 / 84,966 / 42,482 | Vision 1. Mostly intact thatch with two openings, scorched rings around the eight original fire points, and 12 `SOCKET_` empties. |
| `SM_Cottage_Stonebrook_Burnt_01` | building | 18.88 × 10.60 × 7.93 | 162,286 / 81,143 / 40,571 | Vision 2. Nine burnt-through openings from the original sprites plus two remaster openings on the back slope. Also: broken and split rafters, charred battens, ash floor, collapse mounds, and fallen thatch and timbers inside. 11 optional `SOCKET_Smoulder_` empties. |
| `SM_Door_Cottage_Fallen_01` | kit_piece | 1.33 × 2.22 × 0.10 | 3,316 / … | A ledged plank door, burnt from the top, lying face up. |
| `SM_Debris_AshPile_Large_01` / `_Small_01` | kit_piece | 2.62 × 2.11 × 0.60 / 1.19 × 0.90 × 0.28 | 3,546 / 1,594 | Ash, charcoal, charred timber and collapsed thatch. The ember mask is in `T_Ruin_AshEmber_E`. |
| `SM_Decal_Scorch_Ground_3m_01` / `_2m_01` / `_2m_02` / `_1m5_01` | kit_floor | 3 / 2 / 2 / 1.5 m square | 1,440 each | Feathered masked burn patches, one quadrant of `T_Ruin_ScorchGround` each. |
| `SM_Mother_Remains_Fire_01` | foliage (static prop) | 1.11 × 1.81 × 0.38 | 16,082 / 8,040 / 3,859 | The mother's body, SCR_001 vision 1 (S001_P34). |
| `SM_Decal_Blood_Floor_01` | kit_floor | 2 × 2 | 672 | Blood pool and droplets under the body (vision 1). |
| `SM_Wall_Limewash_Burnt_2m_01`, `SM_Window_Limewash_Burnt_2m_01`, `SM_Doorway_Limewash_Burnt_4m_01` | kit_wall / kit_piece | same grid footprint as the intact modules | 1.7k–2.2k | Twins of the interior modules. Limewash has a smoke-layer line, soot gradient and spalls. Timbers are charred. |
| `SM_Floor_Oak_Burnt_2m_01..04` | kit_floor | 2 × 2 × 0.11 | 1,088 | Four UV variants (quadrants of a 4 m sheet) break up the repetition. |
| `SM_Ceiling_Oak_Burnt_2m_01`, `SM_Ceiling_Oak_BurntHole_2m_01` | kit_ceiling | 2 × 2 × 0.2 | 2.3k | Charred boards and joist. The Hole variant is burnt through (y 0.4–1.6 m). |
| `SM_Decal_Scorch_Floor_01`, `SM_Decal_Scorch_Wall_01` | kit_floor / kit_wall | 1.5 × 1.5 / 1.5 × 2.0 | 672 | Replace the original seq-158 "hole" sprites (P44–P49). |

Materials (BC sRGB, N OpenGL so flip green in Unreal, ORM linear; normal strength 0.38 in Blender):

- `MI_Ruin_FacadeFrontBack` and `MI_Ruin_FacadeSides` (4096²): height-mapped facade atlases. U is the horizontal metre and V is the absolute height, so soot can follow the architecture:
  - smoke tongues below the eaves, fans above each window and the door, and burn-through marks at the original P27/P28/P36/P37 positions;
  - calcined, crazed and spalled fieldstone beside the door and windows;
  - soot crowning the chimney.
- `MI_Ruin_Timber` (2048²): an atlas. U < 0.5 is alligatored char (wandering longitudinal checks, wider tilted transverse cracks, domed blocks, silvery sheen). U ≥ 0.5 is scorched oak, with char patches that follow the blocks.
- `MI_Ruin_Thatch` (2048²): an atlas. U < 0.5 is weathered, smoke-stained reed and U ≥ 0.5 is charred reed.
- `MI_Ruin_AshEmber` (2048², with an `E` ember mask): the emissive intensity defaults to 0. Suggested value for the burning state: about 6.
- `MI_RuinInt_PlasterSoot` and `MI_RuinInt_FloorAsh`.
- `MI_Ruin_ScorchGround`, `MI_RuinInt_ScorchFloor` and `MI_RuinInt_ScorchWall`: **masked**, with BC alpha as the opacity mask and clip at 0.5.

## How it matches the 1997 screens

- **Footprint.** `hardness/SCR_001*.png` and `SCR_439*.png` for visions 1 and 2 are byte-identical to vision 0 (0 differing pixels). Every vision-1/2 sprite is `hard=1`, which means no hardness. Both cottage variants therefore carry the intact cottage's **six UCX hulls copied verbatim** from `KIT_StonebrookExterior.blend`, plus its exact pivot (construction offset x = +0.015 m) and identical bounds. The interior twins reuse the intact modules' hull boxes. Debris, decals and the fallen door are visual only (`collision: false` in the drafts); the door lies east of the walk-in corridor.
- **Positions.** `tools/ruin_common.py` embeds the vision-1/2 placements of SCR_439 and SCR_001 (from `tools/dinkex/out`, with frame origins). The 1997 house sprite is a hand-painted hipped roof in pseudo-isometric view, so it cannot be inverted exactly. Instead, exterior effect points are mapped by:
  - inverse-bilinear coordinates on the sprite's roof quad, for points on the roof;
  - an oblique fit measured on the sprite (front 18 m, side 9 m, wall height 68 px), for points on the walls.

  The two big vision-2 holes (P34, P38) land east and centre-west on the front slope, as in the original. The small holes, the vision-1 hole (P46) and the damage patch (P29) follow. `Previews/compare_vision1.png` and `compare_vision2.png` put the original screen beside an orthographic render along the fitted view direction. This is an interpretive correspondence, not a survey.
- **Interior.** Effects use room source pixels. Fires painted on the north wall band are lifted to the wall face at a height read from the drawn wall (27.7 px/m). The mother's death pose (P34, seq 355) is listed for reference only and is not an emitter.

## Fire emitters

`fire_emitters.json` is the deliverable. Each emitter has an origin ID, original sequence/frame, effect kind, `local_ue_cm` (static-mesh socket space, +Y = cottage front), `world_cm` and a scale hint. The burning cottage also carries the sockets as `SOCKET_Fire_01..08`, `SOCKET_Smoke_01`, `SOCKET_Smoke_Chimney` and `SOCKET_Fire_Door_01/02` empties. They are present in its LOD0 FBX (12 socket nodes verified with the FBX parser).

Remaster additions are flagged `remaster_addition`: the chimney smoke, and door fire visible through the open doorway. Burnt-state `SOCKET_Smoulder_*` are `optional` and `default_enabled: false`, because the 1997 vision 2 shows no fire. Previews: `exterior_burning.png`, `exterior_burnt.png`, `interior_burnt.png`, `interior_burning.png` (vision 1 with the mother's body), `remains_neutral_light.png` (the body and blood under neutral light, to check colour), and `compare_vision1/2.png`. Preview fire and smoke in the PNGs are Blender volume shaders only; Niagara work is out of scope.

## Draft runtime manifests (not published)

`stonebrook_ruins_exterior_439.draft.json` and `stonebrook_ruins_interior_001.draft.json` follow `Content/Dink/Data/Art/stonebrook_exterior.json`, with world transforms derived from the live manifests (read-only). They add **proposed** fields that `UDinkArtSubsystem` does not read today:

- `vision`, `replaces`, `emitters` and `hide_origins_by_vision`;
- light `vision`/`flicker`.

The art runtime has no vision gating, so publishing these as-is would show every state at once. Runtime support is needed first.

The interior vision-2 draft swaps all 147 module elements for their burnt twins at identical transforms, and adds six decals. Furniture is left to the interior-props work.

## Rebuild

```bash
SourceAssets/Art/StonebrookRuins/tools/run_all.sh    # textures → build → validate → export → per-LOD FBX → manifests → previews
SKIP_RENDERS=1 SAMPLES=64 BLENDER_THREADS=3 ...      # optional switches
```

Steps: `make_textures.py` (it also needs `Characters/Textures/T_Mother_Atlas_*`, read-only), `pose_mother_remains.py` (writes `Working/MotherRemains_posed.blend`), then (python3: numpy + Pillow, about 80 s), `build_ruins.py` (Blender 5.2.2, about 15 s; it opens the exterior kit read-only for its hulls and pivot), then `dink.py validate`, then `dink.py export_ue --formats fbx` (FBX_SCALE_ALL, apply_unit_scale=True, UnitScaleFactor 100). After that, `export_lods.py` writes `Export/.../<Asset>_LOD{0,1,2}.fbx`, one render mesh per file. UCX and sockets go in LOD0 only, because combined sibling LODs merge in Unreal. Finally `make_manifest.py` and `render_previews.py` (+ `compose_compare.py`).

## Results

- `validation.json`: 22/22 assets pass, 0 errors. The warnings are:
  - building triangle target exceeded (below the 200k hard maximum);
  - open boundaries on the joined building pieces;
  - degenerate UVs on tiny end caps and nail heads;
  - kit_piece/kit_floor triangle targets slightly exceeded.
- `export_report.json`: 22 exported, 0 rejected. `lod_export.json`: 66 per-LOD FBX files, unit scale factor 100.

## Known limits and unverified

- Nothing has been imported into Unreal, so none of the following is checked:
  - sizes, materials and the masked decal blend;
  - whether `SOCKET_` empties become static-mesh sockets (CONVENTIONS §14 item 4);
  - how Nanite treats the 160k-triangle cottages and the masked decals.
- Vision gating for art manifests does not exist yet. The draft manifests are proposals.
- Interior wall twins are 0.356 m / 0.408 m deep instead of 0.38 / 0.42, because charring rounds the braces. Pivots follow the intact rule (bounds-centred thickness), so they can sit about 1 cm off the intact wall line. The 2.0 × 3.5 m footprint and the hulls are identical.
- Quality: the burnt-out roof, charred timber, window voids, interior soot line and ash read well in Blender previews. These are weaker:
  - The roof inherits the intact cottage's thick reed-tube geometry, which reads slightly like shingles.
  - The fieldstone is still a regular rectangular coursing.
  - Facade soot below about 2 m is light under bright sun.
  - Ground scorch decals can look like flat puddles at distance.
  - Preview flames are coarse volume cones. They are placeholders for real VFX and not part of the asset.
- The burnt roof mass is slightly larger than the intact cottage's bounds (18.88 × 10.60 m vs 18.83 × 10.55 m) because of edge jitter and the loose straw. The pivot and collision hulls are identical.
- The mother remains are a re-posed and squashed skinned mesh: the stiff, leg-skinned skirt is flattened by a height compression rather than simulated cloth, so the hem reads as a sheet up close. Blood staining on her atlas is UV-agnostic patches. The pose and blood should be reviewed in the game camera.
- Preview fires are still volume placeholders.
