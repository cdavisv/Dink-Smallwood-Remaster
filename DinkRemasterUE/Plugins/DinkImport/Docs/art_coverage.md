# Art coverage of every origin ID

Alpha gate condition: **every origin ID is final, placeholder or cut with a reason.** This page is the audit as of **9 November 2026**, produced by `Scripts/art_coverage.py` from `Saved/Import/coverage.csv` (importer run of 6 Nov, 6,607 rows) and the art data on disk on 9 Nov. The per-ID result is `Saved/Import/art_coverage.csv`.

## Result

6,607 coverage rows = 5,846 placements + 644 screens + 116 warps + 1 start. They carry 6,514 unique origin IDs: the 93 sprite warps share their placement's ID, so a warp row and a placement row exist for each of them.

| State | Rows | Share |
|---|---:|---:|
| final | 143 | 2.2% |
| placeholder | 6,459 | 97.8% |
| cut | 5 | 0.1% |

Gate status: not met. Placeholder is a legal state for the gate, so the condition is "every ID has a state"; what the numbers say is that 97.8% of IDs still carry no art.

By row type:

| Type | final | placeholder | cut |
|---|---:|---:|---:|
| placement | 135 | 5,711 | 0 |
| screen | 5 | 639 | 0 |
| warp | 2 | 109 | 5 |
| start | 1 | 0 | 0 |

By art kind:

| art_kind | final | placeholder | cut | total |
|---|---:|---:|---:|---:|
| terrain/screen | 55 | 2,941 | 0 | 2,996 |
| building kit | 58 | 1,535 | 0 | 1,593 |
| prop | 15 | 1,157 | 0 | 1,172 |
| creature | 11 | 581 | 0 | 592 |
| character | 2 | 58 | 0 | 60 |
| other | 0 | 78 | 0 | 78 |
| warp | 2 | 109 | 5 | 116 |

By region:

| Region | final | placeholder | cut | total | final % |
|---|---:|---:|---:|---:|---:|
| stonebrook | 143 | 705 | 1 | 849 | 16.8 |
| edge_of_the_world | 0 | 749 | 0 | 749 | 0.0 |
| terris_wilds | 0 | 556 | 1 | 557 | 0.0 |
| windemere | 0 | 483 | 0 | 483 | 0.0 |
| koka_isle | 0 | 454 | 0 | 454 | 0.0 |
| darklands | 0 | 443 | 0 | 443 | 0.0 |
| terris | 0 | 442 | 0 | 442 | 0.0 |
| kernsin | 0 | 415 | 1 | 416 | 0.0 |
| east_wilds | 0 | 394 | 0 | 394 | 0.0 |
| joppa_isle | 0 | 383 | 0 | 383 | 0.0 |
| windemere_wilds | 0 | 269 | 0 | 269 | 0.0 |
| snow_castle | 0 | 259 | 0 | 259 | 0.0 |
| murkwood | 0 | 184 | 1 | 185 | 0.0 |
| goblin_sanctuary | 0 | 173 | 1 | 174 | 0.0 |
| kernsin_wilds | 0 | 155 | 0 | 155 | 0.0 |
| goodheart_castle | 0 | 136 | 0 | 136 | 0.0 |
| south_coast | 0 | 117 | 0 | 117 | 0.0 |
| west_seas | 0 | 51 | 0 | 51 | 0.0 |
| unattached_interiors | 0 | 47 | 0 | 47 | 0.0 |
| cast_camp | 0 | 43 | 0 | 43 | 0.0 |
| fragments | 0 | 1 | 0 | 1 | 0.0 |

All 143 finals are in Stonebrook, on five screens: 1 (Dink's house), 407 (pig pen), 438 and 471 (fields), 439 (cottage yard).

The 143 finals split into **22 origin-bound** (exact, per ID) and **121 screen-dressing** (per screen, see ambiguity 1). The origin-bound ones are 11 creatures (5 pigs on 407, 6 pillbugs on 438), the mother (S001_P26), 9 prop replacements (S001_P19 fireplace, P22 table, P23/P24 beds, P51 pie, P52 sack; S439_P06/P22 barrels, P45 sack) and the `START` row (the hero). Two warp rows (S001_P25, S439_P13) are final because their host door is.

**Cut (5):** the importer's inactive script-warp markers, which have no placement to walk into and are fired by cutscenes or other scripts: `SW_en-gmog_L68@SCR_680`, `SW_s1-ltr_L36@SCR_001`, `SW_s2-cave2_L154@SCR_578`, `SW_s2-culg_L42@SCR_238` (destination also not imported), `SW_s3-mayor_L140@SCR_067`. The reason is the row's `detail`, copied into `evidence`.

## Backlog: top 40 sprite families still placeholder

A family is one original sprite sequence (`dink.ini` sequence number and path). Counts are placements and screens only; warp rows repeat their host's art and are left out. 176 families remain; these 40 hold 5,773 of 6,350 placeholder placements/screens (90.9%). Several asset families span more than one sequence (pillbug is 160 over two sequences, duck 92 plus 90 gore heads over three), so read "main classes" when sizing a deliverable.

| # | Sprite family (seq path) | art_kind | Placeholder | Final | Main classes (placeholder) |
|--:|---|---|--:|--:|---|
| 1 | 32 lands/trees/tree- | terrain/screen | 906 | 6 | tree_pine_large 251, tree_willow_large 154, tree_willow 134 |
| 2 | screen ground (tile layer) | terrain/screen | 639 | 5 | (639 screens) |
| 3 | 65 lands/grass/grass- | terrain/screen | 557 | 20 | weed_small 268, weed_sprig 144, grass_tall 94 |
| 4 | 31 inside/innwalls/walls/inn- | building kit | 545 | 18 | int_wall_plaster_side 188, int_wall_plaster 174, int_wall_plaster_doorjamb 81 |
| 5 | 92 lands/details/beach- | terrain/screen | 423 | 0 | beach_pebbles 281, seashell_clam 66, starfish 47 |
| 6 | 80 inside/stnwalls/stonw- | building kit | 371 | 0 | dungeon_wall_stone 139, dungeon_wall_stone_side 101, dungeon_wall_stone_curve 65 |
| 7 | 33 struct/outinn/oinn- | building kit | 218 | 0 | town_wall_stone_window 80, town_roof_flat 54, town_wall_gable_end 21 |
| 8 | 97 lands/rocks/rocks- | terrain/screen | 216 | 24 | pebbles 214, rock_mound_small 2 |
| 9 | 90 lands/details/grave- | prop | 206 | 0 | thorn_bush 142, bones 46, skull 13 |
| 10 | 179 lands/shrubs/bush- | terrain/screen | 197 | 0 | bush_small 59, bush_round_medium 56, bush_round_large 46 |
| 11 | 64 inside/details/inacc- | prop | 102 | 4 | counter_wood 62, shelf_bottles 14, bed 14 |
| 12 | 173 bonuses/barrels/barel- | prop | 96 | 2 | barrel 95, barrel_broken 1 |
| 13 | 121 animals/duck/death/dkh1x- | creature | 91 | 0 | duck_head 90, duck_corpse 1 |
| 14 | 133 foes/pill/f1-w3- | creature | 89 | 1 | pillbug 89 |
| 15 | 87 inside/details/table- | prop | 86 | 1 | cabinet_wood 34, support_post_timber 21, table_round 9 |
| 16 | 67 struct/castle/castl- | building kit | 81 | 0 | castle_wall_diag 46, castle_tower_round 20, castle_wall_corner 12 |
| 17 | 95 lands/rocks/rock- | terrain/screen | 73 | 0 | boulder_grey_tall 39, boulder_red 17, boulder_flat 9 |
| 18 | 131 foes/pill/f1-w1- | creature | 71 | 5 | pillbug 71 |
| 19 | 448 items/cup/cup- | prop | 70 | 0 | jar_vase 53, bowl 17 |
| 20 | 63 struct/home/home- | building kit | 70 | 4 | cottage_thatched_small 16, cottage_door 16, cottage_thatched_large 16 |
| 21 | 651 foes/puddle/blue/walk/f06w1- | creature | 67 | 0 | slime_blue 67 |
| 22 | 421 items/food/food- | prop | 63 | 1 | tree_fruit 34, food_fruit 15, cabbage 4 |
| 23 | 93 lands/fence/fence- | building kit | 56 | 34 | fence_rail_ns 18, fence_rail_ew 18, fence_rail_diag_nw 14 |
| 24 | 424 struct/island/isle- | building kit | 46 | 0 | island_fence_lattice 15, island_hut_round 12, island_totem_pole 10 |
| 25 | 447 items/tools/tool- | prop | 44 | 0 | hand_tool_small 31, pitchfork 6, rake 3 |
| 26 | 66 lands/garden/gardn- | terrain/screen | 43 | 0 | flower_small 18, mushroom 16, flower_bed_row 7 |
| 27 | 186 struct/landmark/landm- | prop | 39 | 0 | sign_post 30, well_stone 5, bridge_stone 4 |
| 28 | 58 struct/bridge/brdge- | building kit | 36 | 0 | bridge_wood_deck 22, bridge_wood_rail_plank 7, bridge_wood_rail_rope 7 |
| 29 | 461 inner/chair- | prop | 29 | 0 | chair 19, stool 10 |
| 30 | 158 struct/details/damage/hole- | prop | 28 | 0 | burn_hole_decal 26, burnt_floor_hole 2 |
| 31 | 89 lands/details/crack- | prop | 25 | 0 | cave_hole_warp 11, ground_crack 9, ground_hole_dark 5 |
| 32 | 178 bonuses/coins/coin- | prop | 24 | 0 | gold_pile 15, gold_coin 8, gold_coins_small 1 |
| 33 | 188 effects/spurt/sprtl- | other | 24 | 0 | blood_splat 24 |
| 34 | 23 animals/duck/dk3w- | creature | 24 | 0 | duck 24 |
| 35 | 91 lands/details/fores- | prop | 22 | 0 | fallen_log 10, twig 9, fallen_branch_forked 3 |
| 36 | 443 items/boxes/boxb1- | prop | 21 | 0 | crate 21 |
| 37 | 61 struct/details/door/odor1- | building kit | 20 | 1 | door_wood_single 20 |
| 38 | 463 items/grain/bag- | prop | 19 | 1 | grain_sack 19 |
| 39 | 159 struct/stone/mdink/monum- | building kit | 18 | 0 | dragon_statue 13, teleport_shrine 3, dink_monument_rock 1 |
| 40 | 189 effects/spurt/sprtr- | other | 18 | 0 | blood_splat 18 |

Backlog items that already have source art waiting to be wired (placeholders whose evidence says "source candidate"; 419 placements/screens in all):

- Pillbug: `SourceAssets/Art/Creatures/Pillbug` is imported and bound on screen 438 only; 160 other pillbugs (families 14 and 18) are placeholder. The same holds for the 8 remaining pigs.
- Duck: `SourceAssets/Art/Creatures/Duck` (with a gore variant manifest and `duck_origins.json` listing 184 placements) is source-only, not imported into Unreal. It covers family 13 (the duck gore heads), family 34 and the other duck sequences. Its original gore is kept as authored.
- Screen 440: `Stonebrook440/runtime_manifest_440_draft.json` names 31 IDs plus the screen; not published.
- Screens 439 and 1 burning/burnt states: `StonebrookRuins/*.draft.json` name 20 and 13 IDs (fire effects, burn holes, decals), not published, waiting on vision-gating support.
- VFX source textures (`SourceAssets/Art/VFX`) exist for fire, smoke, blood and hits but are not tied to any origin ID yet (families 33 and 40, fire families).

## Method

### What the runtime actually does

Read from `Plugins/DinkCore/Source/DinkCore/Private/DinkArtSubsystem.cpp`, `DinkCreatureSubsystem.cpp`, `DinkArtContextActor.cpp` and `DinkDirector.cpp` (call sites only). Everything is bound **by origin ID or screen number, never by sprite sequence or frame, and there are no per-family kit mappings**. There is no generic "sequence 32 becomes tree mesh X" table, so a delivered tree does not dress the other 900 trees.

| Mechanism | Data (`Content/Dink/Data/Art/`) | Effect |
|---|---|---|
| `dink-art/1` screen manifest | `stonebrook.json`, `stonebrook_exterior.json`, `pigpen.json`, `stonebrook_fields_438.json`, `stonebrook_fields_471.json`, `stonebrook_refinement_fireplace_v2.json` | `replacements[].origin` swaps one placement's card for a mesh; `hide_origins` hides actor cards; `hide_screen_visuals` hides the screen's ground, volumes and decor instances; `elements` spawn authored meshes at world positions; `warp_overrides` move a door trigger. A manifest with any missing mesh is discarded whole. |
| `dink-art/1` with `context` | `stonebrook_vista_v4.json`, `stonebrook_perimeter_skirt_v1.json`, `stonebrook_underfloor_v1.json` | Render-only context for screen 1. Binds no origin ID. |
| `dink-creatures/1` | `creatures.json` | `placements[].origin` gets a skeletal creature (pig, pillbug), card hidden. |
| `dink-characters/1` | `characters.json` | `placements[].origin` gets a humanoid (mother S001_P26); `player` swaps the hero mesh; `script_profiles` (`s1-bul`, Milder) bind by script name to a spawned actor. |
| not origin bindings | `camera_materials.json`, `hero_actions.json` | camera fade materials, hero fist clip. |

Two runtime paths bind by sprite sequence rather than origin, and neither is a placement: `creatures.json` `food_sequences` 430/431 give thrown grain a wheat mesh, and `ApplyScriptCharacter` keys on the script name. They are not counted as bindings for any origin ID.

Not read as bindings: `SourceAssets/**` (editable sources, ledger, drafts) and `Content/Dink/_Generated` (the importer's greybox output). These only feed the "source candidate" hints in `evidence`.

### Rules, in order, per coverage row

Asset existence means the `/Game/Dink/...` object path resolves to `Content/Dink/.../Name.uasset` (the script also notes a Git LFS pointer; none today). The engine template blendspace `/Game/Characters/.../BS_Idle_Walk_Run` used by the mother is accepted if present but noted as template content, not Codex art.

1. **Placement or `START`, origin-bound** -> `final`: the ID is an actor in `creatures.json` or `characters.json` placements, or in a manifest's `replacements`, and every referenced asset exists. The later manifest wins, as at runtime (the fireplace V2 refinement overrides S001_P19). `START` takes the hero mesh from `characters.json` `player`.
2. **Placement, screen-dressing** -> `final`: its screen has a published manifest with `hide_screen_visuals` and authored elements, and the placement is hidden by it (an actor listed in `hide_origins`, or an instance, which `hide_screen_visuals` hides wholesale), and its category is one a screen kit stands in for. Walls, structure parts, props, furniture, flora, rocks and hazards qualify. NPCs, enemies, animals, effects and "other" do not: they are animated or effect content that a static kit cannot replace, so they stay placeholder, with the note "hidden ... no replacement art (nothing drawn)" (for example the vision-1 fire sprites in the house).
3. **Screen** -> `final` if a published manifest hides its visuals and spawns authored elements (screens 1, 407, 438, 439, 471), else placeholder.
4. **Warp** -> `cut` if the importer made an inactive marker (reason from `detail`); otherwise it **inherits its host placement's state** (sprite warps: the same ID; script warps: the `@S...` suffix), because a warp trigger has no art of its own beyond the door or hole sprite it sits on.
5. Everything else -> `placeholder`. Evidence says whether it is a greybox actor card, instance or hardbox volume, and adds flags: vision-gated, `source candidate: ...`, and `REVIEW-CUT: ...` (below).

`art_kind` comes from the data repo category in `detail`: npc is character; enemy and animal (plus duck and pillbug gore classes) are creature; interior wall, structure and structure part are building kit; furniture, container, prop, pickup and hazard are prop; trees, grass, bushes and rocks are terrain/screen (natural scatter, not a kit); effect and other are other; warp and screen rows are warp and terrain/screen. `sprite_family` is the placement's `dink.ini` sequence (`seq` from `Content/Dink/Data/Gameplay/placements.csv`, name from `tools/dinkex/out/sequences.json`; the committed `placements.csv` is used so the script needs no `ImportData/` bundle).

### Data read

`Saved/Import/coverage.csv`; `Content/Dink/Data/Art/*.json` (13 files); `Content/Dink/Data/Gameplay/placements.csv`; `Content/Dink/**.uasset` existence; `SourceAssets/asset_ledger.csv` (status by asset name); `SourceAssets/Art/**` draft manifests and `Creatures/*` directories (hints only); `tools/dinkex/out/sequences.json` in the data repo (names only; falls back to bare numbers if absent).

## Known ambiguities

1. **Screen-dressing is not a per-ID binding (121 finals).** `hide_origins` and `hide_screen_visuals` say a sprite is hidden; the replacement is a screen-wide set of kit `elements` that carry no origin ID. The audit cannot prove that the S001_P01 wall corner is replaced by a specific wall mesh, only that its screen is dressed and the sprite is gone. The category filter above makes it conservative for effects and creatures, but a hidden prop could in principle be left without art. Treat these as "final by screen" and re-check them by eye when each screen is signed off. If you want strictly per-ID evidence, the finals fall to 22.
2. **"Final" is not "approved".** All 1,832 non-audio rows in `SourceAssets/asset_ledger.csv` are `candidate`; nothing in art is `approved` (only audio is). Every origin-bound final shows `ledger=candidate`. The audit defines final as delivered and bound, as asked, but an owner approval step does not exist yet.
3. **Existence, not rendering.** No engine ran. A bound mesh is only proven to exist; skeleton compatibility of creature and character meshes (checked by the runtime and by `Dink.Art` tests) and actual rendering are not re-verified here.
4. **Stale coverage.** `coverage.csv` is from 6 Nov; the art manifests changed on 7 to 9 Nov. The script warns if a manifest names an origin that coverage lacks (none today), but a re-import changes nothing about art states, so this only matters if placements change.
5. **`START` is a marker, not a sprite.** Marked final because the hero art is bound to the player who spawns there; strictly it is the only row of its kind.
6. **Rows that need a cut-or-cover decision.** Not skipped by the importer, so not `cut` by the stated definition; kept `placeholder` and flagged `REVIEW-CUT` in `evidence` (101 placements/screens): 64 hardness-only proxies (type 2 cards, invisible in play, drawn only as collision hardboxes in the greybox), 33 placements vision-gated by a variable no script ever sets (coverage detail "unknown: no script found"), and 4 empty placements (S162_P37/P38, S194_P37/P38, treatment `not_needed`). They can never become final in a meaningful way, so the gate needs a decision on them.
7. **Warp rows duplicate IDs.** Counting by unique origin ID gives 6,514 IDs, and 93 of them have two rows with possibly different `type`. The CSV key is (`origin_id`, `type`).
8. **Terrain/screen taxonomy.** Trees, grass, bushes and rocks are grouped as terrain/screen (2,996 rows) rather than prop or kit. If the plan treats them as "props" the totals shift between those two columns but not between states.
9. **Instances on dressed screens** (hidden by `hide_screen_visuals` without being listed individually) count as screen-dressing finals only if their category is kit-coverable; all instance placements on the five screens qualify today.

## Rerun

From the project directory (`DinkRemasterUE`, the real path, not the symlink):

```bash
python3 -I Scripts/art_coverage.py
```

Pure standard library, about 0.2 s, read-only except for writing `Saved/Import/art_coverage.csv` (override with `--out`, input with `--coverage`, backlog length with `--top`). The CSV columns are `origin_id,type,screen,region,sprite_family,art_kind,state,evidence`; the output is deterministic. Rerun after any change to `Content/Dink/Data/Art/*.json`, after new assets land under `Content/Dink`, or after a re-import regenerates `coverage.csv`. This page's tables are a snapshot, not regenerated automatically; regenerate them from the script's printed summary when the numbers move.
