# Art coverage of every origin ID

Alpha gate condition: **every origin ID is final, placeholder or cut with a reason.** This page is the audit as of **9 November 2026**, produced by `Scripts/art_coverage.py` from `Saved/Import/coverage.csv` (importer run of 6 Nov, 6,607 rows) and the art data on disk on 9 Nov, including the sprite-family bindings of `Content/Dink/Data/Art/families.json`. The per-ID result is `Saved/Import/art_coverage.csv`.

## Result

6,607 coverage rows = 5,846 placements + 644 screens + 116 warps + 1 start. They carry 6,514 unique origin IDs: the 93 sprite warps share their placement's ID, so a warp row and a placement row exist for each of them.

| State | Rows | Share |
|---|---:|---:|
| final bespoke | 143 | 2.2% |
| final by family | 1,326 | 20.1% |
| placeholder | 4,986 | 75.5% |
| cut | 152 | 2.3% |
| **final, both** | **1,469** | **22.2%** |

**Final bespoke** is art bound to that ID or its screen by the art manifests (origin-bound or screen-dressing, below). **Final by family** is a placement that `Content/Dink/Data/Art/families.json` dresses through its sprite family (one mesh per family, fitted to the card, visual only; `UDinkArtFamilySubsystem`), on screens and IDs the manifests leave alone. The report keeps the two apart.

Gate status: not met. Placeholder is a legal state for the gate, so the condition is "every ID has a state"; what the numbers say is that 75.5% of IDs still carry no art. The 152 `cut` rows are the 5 inactive script-warp markers plus, by owner decision on 9 Nov 2026, 101 placements that can never meaningfully become final (64 hardness-only collision proxies, 33 placements gated by a vision variable no script ever sets, 4 empty placements) and the 46 warp triggers hosted on such proxies.

By row type:

| type | final bespoke | final by family | placeholder | cut | total |
|---|---:|---:|---:|---:|---:|
| placement | 135 | 1,326 | 4,284 | 101 | 5,846 |
| screen | 5 | 0 | 639 | 0 | 644 |
| warp | 2 | 0 | 63 | 51 | 116 |
| start | 1 | 0 | 0 | 0 | 1 |

By art kind:

| art_kind | final bespoke | final by family | placeholder | cut | total |
|---|---:|---:|---:|---:|---:|
| building kit | 58 | 18 | 1,515 | 2 | 1,593 |
| character | 2 | 0 | 54 | 4 | 60 |
| creature | 11 | 0 | 573 | 8 | 592 |
| other | 0 | 0 | 74 | 4 | 78 |
| prop | 15 | 135 | 958 | 64 | 1,172 |
| terrain/screen | 55 | 1,173 | 1,749 | 19 | 2,996 |
| warp | 2 | 0 | 63 | 51 | 116 |

By region:

| region | final bespoke | final by family | placeholder | cut | total | final % |
|---|---:|---:|---:|---:|---:|---:|
| stonebrook | 143 | 211 | 467 | 28 | 849 | 41.7 |
| edge_of_the_world | 0 | 166 | 565 | 18 | 749 | 22.2 |
| terris_wilds | 0 | 148 | 397 | 12 | 557 | 26.6 |
| windemere | 0 | 156 | 314 | 13 | 483 | 32.3 |
| koka_isle | 0 | 43 | 432 | 6 | 481 | 8.9 |
| darklands | 0 | 12 | 430 | 1 | 443 | 2.7 |
| terris | 0 | 51 | 370 | 21 | 442 | 11.5 |
| kernsin | 0 | 33 | 368 | 15 | 416 | 7.9 |
| east_wilds | 0 | 185 | 178 | 4 | 367 | 50.4 |
| joppa_isle | 0 | 23 | 350 | 10 | 383 | 6.0 |
| windemere_wilds | 0 | 103 | 160 | 6 | 269 | 38.3 |
| snow_castle | 0 | 1 | 254 | 4 | 259 | 0.4 |
| murkwood | 0 | 46 | 135 | 4 | 185 | 24.9 |
| goblin_sanctuary | 0 | 13 | 158 | 3 | 174 | 7.5 |
| kernsin_wilds | 0 | 34 | 121 | 0 | 155 | 21.9 |
| goodheart_castle | 0 | 22 | 107 | 7 | 136 | 16.2 |
| south_coast | 0 | 26 | 91 | 0 | 117 | 22.2 |
| west_seas | 0 | 1 | 50 | 0 | 51 | 2.0 |
| unattached_interiors | 0 | 44 | 3 | 0 | 47 | 93.6 |
| cast_camp | 0 | 8 | 35 | 0 | 43 | 18.6 |
| fragments | 0 | 0 | 1 | 0 | 1 | 0.0 |

**East Wilds and the booth (9 Nov 2026, owner decision):** the cobbler's booth is one interior since `tools/analyse` regions.toml `[[join]] cobbler_booth_doorway` (a doorway between SCR_290, the Koka room, and SCR_289, whose door S289_P19 leads to the East Wilds). SCR_289 and its 27 rows moved from `east_wilds` to `koka_isle` with the booth (east_wilds 394 -> 367 rows, koka_isle 454 -> 481; totals unchanged). The East Wilds' placeholders are now legitimately reachable content, not sealed-off scenery: 22 of its 55 screens (the meadows of rows 8-11, SCR_352's treasure, the SCR_349 save machine) are reached by design through the booth; the 24 river/coast screens of rows 12-20 are still reached only by wading in the 1997 engine and 9 by nothing.

All 143 bespoke finals are in Stonebrook, on five screens: 1 (Dink's house), 407 (pig pen), 438 and 471 (fields), 439 (cottage yard). The 1,326 family finals are spread over every region but the one-placement `fragments`.

The 143 bespoke finals split into **22 origin-bound** (exact, per ID), **119 screen-dressing** (per screen, see ambiguity 1) and 2 warp rows. The origin-bound ones are 11 creatures (5 pigs on 407, 6 pillbugs on 438), the mother (S001_P26), 9 prop replacements (S001_P19 fireplace, P22 table, P23/P24 beds, P51 pie, P52 sack; S439_P06/P22 barrels, P45 sack) and the `START` row (the hero). Two warp rows (S001_P25, S439_P13) are final because their host door is. No warp row is final by family: no bound family hosts a sprite warp.

Family bindings in `families.json` (18 rows, all meshes imported) and the placements each turned final:

| Family (class id) | Sprite family | Mesh | Placements now final |
|---|---|---|---:|
| `weed_small` | 65 lands/grass/grass- | `SM_Grass_Meadow_01` | 262 |
| `tree_pine_large` | 32 lands/trees/tree- | `SM_Pine_Stonebrook_V3` | 247 |
| `tree_willow_large` | 32 lands/trees/tree- | `SM_Oak_Stonebrook_01` | 151 |
| `weed_sprig` | 65 lands/grass/grass- | `SM_Grass_Meadow_01` | 135 |
| `tree_willow` | 32 lands/trees/tree- | `SM_Oak_Stonebrook_01` | 132 |
| `tree_oak_large` | 32 lands/trees/tree- | `SM_Oak_Stonebrook_01` | 96 |
| `barrel` | 173 bonuses/barrels/barel- | `SM_Barrel_Oak_01` | 95 |
| `grass_tall` | 65 lands/grass/grass- | `SM_Grass_Meadow_01` | 90 |
| `boulder_grey_tall` | 95 lands/rocks/rock- | `SM_Boulder_Fieldstone_01` | 35 |
| `chair` | 461 inner/chair- | `SM_Chair_Oak_01` | 19 |
| `fence_rail_ew` | 93 lands/fence/fence- | `SM_Fence_SplitRail_4m_01` | 18 |
| `boulder_red` | 95 lands/rocks/rock- | `SM_Boulder_Fieldstone_01` | 15 |
| `bed` | 64 inside/details/inacc- | `SM_Bed_Oak_01` | 14 |
| `table_long` | 87 inside/details/table- | `SM_Table_Oak_01` | 7 |
| `boulder_flat` | 95 lands/rocks/rock- | `SM_Boulder_Fieldstone_01` | 5 |
| `boulder_large` | 95 lands/rocks/rock- | `SM_Boulder_Fieldstone_01` | 2 |
| `rock_mound_small` | 97 lands/rocks/rocks- | `SM_Boulder_Fieldstone_01` | 2 |
| `boulder_white` | 95 lands/rocks/rock- | `SM_Boulder_Fieldstone_01` | 1 |
| **all** | | | **1,326** |

Left unbound on purpose (the mesh would read wrong): pebbles and beach pebbles (a boulder where the sprite is walk-over scatter), dead trees, stumps and the forest-edge strips (a single leafy tree), round tables, benches, cabinets, posts and stools (the oak table's rectangle, a chair's back), ferns, flowers and bushes (a grass clump), north-south and diagonal fences (a projected depth a uniform scale cannot fit), the white boulder pair and the blue ore rock, the broken barrel, thorn bushes, bones and skulls. Scripted pines, rocks, grass and tables keep their cards too (the plan wants burnable trees dry and bombable rocks cracked); scripted barrels, beds and chairs are dressed.

**Cut (5):** the importer's inactive script-warp markers, which have no placement to walk into and are fired by cutscenes or other scripts: `SW_en-gmog_L68@SCR_680`, `SW_s1-ltr_L36@SCR_001`, `SW_s2-cave2_L154@SCR_578`, `SW_s2-culg_L42@SCR_238` (destination also not imported), `SW_s3-mayor_L140@SCR_067`. The reason is the row's `detail`, copied into `evidence`.

## Backlog: top 40 sprite families still placeholder

A family is one original sprite sequence (`dink.ini` sequence number and path). Counts are placements and screens only; warp rows repeat their host's art and are left out; "Final" counts bespoke and family finals together. 174 families remain; these 40 hold 4,387 of 4,923 placeholder placements/screens (89.1%). Several asset families span more than one sequence (pillbug is 154 over two sequences, duck 92 plus 90 gore heads over three), so read "main classes" when sizing a deliverable.

| # | Sprite family (seq path) | art_kind | Placeholder | Final | Main classes (placeholder) |
|--:|---|---|--:|--:|---|
| 1 | screen ground (tile layer) | terrain/screen | 639 | 5 |  |
| 2 | 31 inside/innwalls/walls/inn- | building kit | 545 | 18 | int_wall_plaster_side 188, int_wall_plaster 174, int_wall_plaster_doorjamb 81 |
| 3 | 92 lands/details/beach- | terrain/screen | 423 | 0 | beach_pebbles 281, seashell_clam 66, starfish 47 |
| 4 | 80 inside/stnwalls/stonw- | building kit | 371 | 0 | dungeon_wall_stone 139, dungeon_wall_stone_side 101, dungeon_wall_stone_curve 65 |
| 5 | 32 lands/trees/tree- | terrain/screen | 279 | 632 | pine_forest_edge_strip_vert 123, tree_stump 47, pine_forest_edge_strip 40 |
| 6 | 33 struct/outinn/oinn- | building kit | 218 | 0 | town_wall_stone_window 80, town_roof_flat 54, town_wall_gable_end 21 |
| 7 | 97 lands/rocks/rocks- | terrain/screen | 214 | 26 | pebbles 214 |
| 8 | 90 lands/details/grave- | prop | 206 | 0 | thorn_bush 142, bones 46, skull 13 |
| 9 | 179 lands/shrubs/bush- | terrain/screen | 195 | 0 | bush_small 57, bush_round_medium 56, bush_round_large 46 |
| 10 | 121 animals/duck/death/dkh1x- | creature | 91 | 0 | duck_head 90, duck_corpse 1 |
| 11 | 133 foes/pill/f1-w3- | creature | 89 | 1 | pillbug 89 |
| 12 | 67 struct/castle/castl- | building kit | 81 | 0 | castle_wall_diag 46, castle_tower_round 20, castle_wall_corner 12 |
| 13 | 63 struct<HOME> | building kit | 70 | 4 | cottage_thatched_small 16, cottage_door 16, cottage_thatched_large 16 |
| 14 | 448 items/cup/cup- | prop | 69 | 0 | jar_vase 52, bowl 17 |
| 15 | 651 foes/puddle/blue/walk/f06w1- | creature | 67 | 0 | slime_blue 67 |
| 16 | 131 foes/pill/f1-w1- | creature | 65 | 5 | pillbug 65 |
| 17 | 87 inside/details/table- | prop | 65 | 8 | support_post_timber 21, cabinet_wood 20, table_round 9 |
| 18 | 421 items/food/food- | prop | 62 | 1 | tree_fruit 34, food_fruit 15, cabbage 4 |
| 19 | 65 lands/grass/grass- | terrain/screen | 57 | 507 | fern 50, weed_sprig 5, weed_small 2 |
| 20 | 424 struct/island/isle- | building kit | 46 | 0 | island_fence_lattice 15, island_hut_round 12, island_totem_pole 10 |
| 21 | 64 inside/details/inacc- | prop | 46 | 18 | counter_wood 22, shelf_bottles 12, bookcase 9 |
| 22 | 447 items/tools/tool- | prop | 43 | 0 | hand_tool_small 30, pitchfork 6, rake 3 |
| 23 | 66 lands/garden/gardn- | terrain/screen | 43 | 0 | flower_small 18, mushroom 16, flower_bed_row 7 |
| 24 | 186 struct/landmark/landm- | prop | 39 | 0 | sign_post 30, well_stone 5, bridge_stone 4 |
| 25 | 93 lands/fence/fence- | building kit | 37 | 52 | fence_rail_ns 17, fence_rail_diag_nw 14, fence_rail_diag_ne 6 |
| 26 | 58 struct/bridge/brdge- | building kit | 36 | 0 | bridge_wood_deck 22, bridge_wood_rail_plank 7, bridge_wood_rail_rope 7 |
| 27 | 158 struct/details/damage/hole- | prop | 28 | 0 | burn_hole_decal 26, burnt_floor_hole 2 |
| 28 | 178 bonuses/coins/coin- | prop | 24 | 0 | gold_pile 15, gold_coin 8, gold_coins_small 1 |
| 29 | 188 effects/spurt/sprtl- | other | 24 | 0 | blood_splat 24 |
| 30 | 23 animals/duck/dk3w- | creature | 24 | 0 | duck 24 |
| 31 | 89 lands/details/crack- | prop | 23 | 0 | cave_hole_warp 10, ground_crack 8, ground_hole_dark 5 |
| 32 | 91 lands/details/fores- | prop | 22 | 0 | fallen_log 10, twig 9, fallen_branch_forked 3 |
| 33 | 443 items/boxes/boxb1- | prop | 21 | 0 | crate 21 |
| 34 | 61 struct/details/door/odor1- | building kit | 20 | 1 | door_wood_single 20 |
| 35 | 463 items/grain/bag- | prop | 19 | 1 | grain_sack 19 |
| 36 | 159 struct/stone/mdink/monum- | building kit | 18 | 0 | dragon_statue 13, teleport_shrine 3, dink_monument_rock 1 |
| 37 | 189 effects/spurt/sprtr- | other | 18 | 0 | blood_splat 18 |
| 38 | 29 animals/duck/dk9w- | creature | 18 | 0 | duck 18 |
| 39 | 693 foes/puddle/red/walk/f06w3- | creature | 17 | 0 | slime_red 17 |
| 40 | 56 bonuses/bottles/botl-r | prop | 15 | 0 | potion_red 15 |

Backlog items that already have source art waiting to be wired (placeholders whose evidence says "source candidate"; 393 placements/screens in all):

- Pillbug: `SourceAssets/Art/Creatures/Pillbug` is imported and bound on screen 438 only; 160 other pillbugs (families 14 and 18) are placeholder. The same holds for the 8 remaining pigs.
- Duck: `SourceAssets/Art/Creatures/Duck` (with a gore variant manifest and `duck_origins.json` listing 184 placements) is source-only, not imported into Unreal. It covers family 13 (the duck gore heads), family 34 and the other duck sequences. Its original gore is kept as authored.
- Screen 440: `Stonebrook440/runtime_manifest_440_draft.json` names 31 IDs plus the screen; not published.
- Screens 439 and 1 burning/burnt states: `StonebrookRuins/*.draft.json` name 20 and 13 IDs (fire effects, burn holes, decals), not published, waiting on vision-gating support.
- VFX source textures (`SourceAssets/Art/VFX`) exist for fire, smoke, blood and hits but are not tied to any origin ID yet (families 33 and 40, fire families).

## Method

### What the runtime actually does

Read from `Plugins/DinkCore/Source/DinkCore/Private/DinkArtSubsystem.cpp`, `DinkCreatureSubsystem.cpp`, `DinkArtContextActor.cpp`, `DinkArtFamilySubsystem.cpp` and `DinkDirector.cpp` (call sites only). The art manifests bind **by origin ID or screen number**. The family layer (`UDinkArtFamilySubsystem`, `families.json`) binds **by sprite family** (a `sprite_classes.csv` class id, else the `dink.ini` sequence) for whatever the manifests leave greybox: at screen activation each such placement gets the family mesh as a collisionless child component fitted to its card, and the card is hidden. Collision, hardness, origin IDs and scripts do not change.

| Mechanism | Data (`Content/Dink/Data/Art/`) | Effect |
|---|---|---|
| `dink-art/1` screen manifest | `stonebrook.json`, `stonebrook_exterior.json`, `pigpen.json`, `stonebrook_fields_438.json`, `stonebrook_fields_471.json`, `stonebrook_refinement_fireplace_v2.json` | `replacements[].origin` swaps one placement's card for a mesh; `hide_origins` hides actor cards; `hide_screen_visuals` hides the screen's ground, volumes and decor instances; `elements` spawn authored meshes at world positions; `warp_overrides` move a door trigger. A manifest with any missing mesh is discarded whole. |
| `dink-art/1` with `context` | `stonebrook_vista_v4.json`, `stonebrook_perimeter_skirt_v1.json`, `stonebrook_underfloor_v1.json` | Render-only context for screen 1. Binds no origin ID. |
| `dink-creatures/1` | `creatures.json` | `placements[].origin` gets a skeletal creature (pig, pillbug), card hidden. |
| `dink-characters/1` | `characters.json` | `placements[].origin` gets a humanoid (mother S001_P26); `player` swaps the hero mesh; `script_profiles` (`s1-bul`, Milder) bind by script name to a spawned actor. |
| `dink-art-families/1` | `families.json` | `families[]`: `family` (class id or sequence) -> `mesh`, `fit`, `yaw_from_sprite`, `scripted`. Dresses every placement of that family whose screen and ID no manifest above handles; per row, the mesh must exist or the cards stay. Visual only. |
| not origin bindings | `camera_materials.json`, `hero_actions.json` | camera fade materials, hero fist clip. |

Two runtime paths bind by sprite sequence rather than origin, and neither is a placement: `creatures.json` `food_sequences` 430/431 give thrown grain a wheat mesh, and `ApplyScriptCharacter` keys on the script name. They are not counted as bindings for any origin ID.

Not read as bindings: `SourceAssets/**` (editable sources, ledger, drafts) and `Content/Dink/_Generated` (the importer's greybox output). These only feed the "source candidate" hints in `evidence`.

### Rules, in order, per coverage row

Asset existence means the `/Game/Dink/...` object path resolves to `Content/Dink/.../Name.uasset` (the script also notes a Git LFS pointer; none today). The engine template blendspace `/Game/Characters/.../BS_Idle_Walk_Run` used by the mother is accepted if present but noted as template content, not Codex art.

1. **Placement or `START`, origin-bound** -> `final`: the ID is an actor in `creatures.json` or `characters.json` placements, or in a manifest's `replacements`, and every referenced asset exists. The later manifest wins, as at runtime (the fireplace V2 refinement overrides S001_P19). `START` takes the hero mesh from `characters.json` `player`.
2. **Placement, screen-dressing** -> `final`: its screen has a published manifest with `hide_screen_visuals` and authored elements, and the placement is hidden by it (an actor listed in `hide_origins`, or an instance, which `hide_screen_visuals` hides wholesale), and its category is one a screen kit stands in for. Walls, structure parts, props, furniture, flora, rocks and hazards qualify. NPCs, enemies, animals, effects and "other" do not: they are animated or effect content that a static kit cannot replace, so they stay placeholder, with the note "hidden ... no replacement art (nothing drawn)" (for example the vision-1 fire sprites in the house).
3. **Screen** -> `final` if a published manifest hides its visuals and spawns authored elements (screens 1, 407, 438, 439, 471), else placeholder. Since 13 Nov 2026 a second way, grade `ground-layers`, behind one switch (`Content/Dink/Data/Environment/ground_review.json` `rule.count_reviewed_grounds_final`, or `--ground-rule on|off`): the screen draws the photoreal terrain material with every layer texture present, the mask dropped no layer, every tile class on it has verdict `pass` in `ground_review.json` (the in-game review, outdoors and indoors separately; a class not looked at does not pass), water tiles have a water surface and the review holds no finding against that screen. `screen_ground_state()`; what each screen is made of is `ground_classes.json`, written by the world export; evidence and sheets in `Docs/Verification/GroundReview_13Nov2026/`. The placeholder evidence lists every reason.
4. **Placement, family-bound** -> `final` (graded "final by family"), checked after the cut rules so a cut placement stays cut: `families.json` has a row for its class id (else its sequence) whose mesh exists; its screen is not dressed (`hide_screen_visuals`, `authored_collision_screens`, or a manifest with `elements`) and its ID is not handled (`replacements`, `hide_origins`, `hide_origins_by_vision`, `warp_overrides`, creature and character `placements`), read from the raw manifests as the C++ does; it is not hardness-only and has a picture; it has no script unless the row says `scripted: true`. An instance (background decor) counts only if every instance of its sprite frame on that screen is bound to the same row, because the runtime swaps a whole decor component or none. Evidence: `family-bound: <family> -> <mesh>`.
5. **Warp** -> `cut` if the importer made an inactive marker (reason from `detail`); otherwise it **inherits its host placement's state** (sprite warps: the same ID; script warps: the `@S...` suffix), because a warp trigger has no art of its own beyond the door or hole sprite it sits on.
6. Everything else -> `placeholder`. Evidence says whether it is a greybox actor card, instance or hardbox volume, and adds flags: vision-gated and `source candidate: ...`.

`art_kind` comes from the data repo category in `detail`: npc is character; enemy and animal (plus duck and pillbug gore classes) are creature; interior wall, structure and structure part are building kit; furniture, container, prop, pickup and hazard are prop; trees, grass, bushes and rocks are terrain/screen (natural scatter, not a kit); effect and other are other; warp and screen rows are warp and terrain/screen. `sprite_family` is the placement's `dink.ini` sequence (`seq` from `Content/Dink/Data/Gameplay/placements.csv`, name from `tools/dinkex/out/sequences.json`; the committed `placements.csv` is used so the script needs no `ImportData/` bundle).

### Data read

`Saved/Import/coverage.csv`; `Content/Dink/Data/Art/*.json` (14 files, `families.json` included); `Content/Dink/Data/Gameplay/placements.csv`; `Content/Dink/**.uasset` existence; `SourceAssets/asset_ledger.csv` (status by asset name); `SourceAssets/Art/**` draft manifests and `Creatures/*` directories (hints only); `tools/dinkex/out/sequences.json` in the data repo (names only; falls back to bare numbers if absent).

## Known ambiguities

1. **Screen-dressing is not a per-ID binding (119 finals, plus the 2 warp rows whose host doors they hide).** `hide_origins` and `hide_screen_visuals` say a sprite is hidden; the replacement is a screen-wide set of kit `elements` that carry no origin ID. The audit cannot prove that the S001_P01 wall corner is replaced by a specific wall mesh, only that its screen is dressed and the sprite is gone. The category filter above makes it conservative for effects and creatures, but a hidden prop could in principle be left without art. Treat these as "final by screen" and re-check them by eye when each screen is signed off. If you want strictly per-ID evidence, the bespoke finals fall to 22.
2. **"Final" is not "approved".** All 1,832 non-audio rows in `SourceAssets/asset_ledger.csv` are `candidate`; nothing in art is `approved` (only audio is). Every origin-bound final shows `ledger=candidate`. The audit defines final as delivered and bound, as asked, but an owner approval step does not exist yet.
3. **Existence, not rendering.** No engine ran. A bound mesh is only proven to exist; skeleton compatibility of creature and character meshes (checked by the runtime and by `Dink.Art` tests) and actual rendering are not re-verified here.
4. **Stale coverage.** `coverage.csv` is from 6 Nov; the art manifests changed on 7 to 9 Nov. The script warns if a manifest names an origin that coverage lacks (none today), but a re-import changes nothing about art states, so this only matters if placements change.
5. **`START` is a marker, not a sprite.** Marked final because the hero art is bound to the player who spawns there; strictly it is the only row of its kind.
6. **Cut by owner decision (9 Nov 2026).** Placements the importer did not skip but that can never meaningfully become final are `cut`, with the reason in `evidence`: 64 hardness-only proxies (type 2 cards, invisible in play, drawn only as collision hardboxes in the greybox), 33 placements vision-gated by a variable no script ever sets (coverage detail "unknown: no script found"), and 4 empty placements (S162_P37/P38, S194_P37/P38, treatment `not_needed`); the 46 warp triggers hosted on such proxies inherit the state. The owner took this decision on 9 Nov 2026 after the first audit; the greybox keeps drawing the hardboxes, nothing in play changes.
7. **Warp rows duplicate IDs.** Counting by unique origin ID gives 6,514 IDs, and 93 of them have two rows with possibly different `type`. The CSV key is (`origin_id`, `type`).
8. **Terrain/screen taxonomy.** Trees, grass, bushes and rocks are grouped as terrain/screen (2,996 rows) rather than prop or kit. If the plan treats them as "props" the totals shift between those two columns but not between states.
9. **Instances on dressed screens** (hidden by `hide_screen_visuals` without being listed individually) count as screen-dressing finals only if their category is kit-coverable; all instance placements on the five screens qualify today.
10. **Family finals are stand-ins by design.** A family row puts one mesh on every placement of the family: the willows get the oak, the red boulders the grey fieldstone, all chairs take a stable per-origin yaw whatever their frame. They are "final" in the audit's sense (delivered and bound), not owner-approved per placement. Every seed row uses `fit: none`: the mesh stands at real size at the card's ground point, like the player and the dressed screens, while the greybox card and its hardbox are layout-scaled (1.75x interiors to 4x settlements), so a real-size barrel sits inside a larger invisible hardbox until the screen gets authored collision. `footprint` (fit the card) is opt-in per row.

## Rerun

From the project directory (`DinkRemasterUE`, the real path, not the symlink):

```bash
python3 -I Scripts/art_coverage.py
```

Pure standard library, about 0.2 s, read-only except for writing `Saved/Import/art_coverage.csv` (override with `--out`, input with `--coverage`, backlog length with `--top`). The CSV columns are `origin_id,type,screen,region,sprite_family,art_kind,state,evidence`; the output is deterministic. Rerun after any change to `Content/Dink/Data/Art/*.json` (`families.json` included), after new assets land under `Content/Dink`, or after a re-import regenerates `coverage.csv`. This page's tables are a snapshot, not regenerated automatically; regenerate them from the script's printed summary when the numbers move.
