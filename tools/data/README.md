# tools/data: hand classification tables (pipeline stage 2)

Two tables that say what every used tile and every placed sprite of the
original Dink Smallwood world *is*, so the Unreal importer (stage 6) can turn
tiles into landscape layers / water and placed sprites into 3D actors.

| File | Rows | Key |
|---|---:|---|
| `tile_classes.csv` | 1,450 | one row per tile num used in `map.dat` (61,824 cells = 644 screens x 96) |
| `sprite_classes.csv` | 559 | one row per placed (seq, frame), sorted by placement count (5,846 active placements, 178 sequences) |

Both tables were produced by **looking at the art**: every tileset and every
placed frame was rendered as a labelled contact sheet and viewed; ambiguous
sprites were checked in rendered screens and against their DinkC script. The
labels live in two hand-written Python files (`scripts/tile_labels.py`,
`scripts/sprite_labels.py`); the CSVs are regenerated from them plus a fresh
scan of `bin/dink/`. Edit the label files, not the CSVs.

## Regenerating

```
cd tools/data
python3 scripts/build_tables.py          # scan bin/dink + labels -> both CSVs
python3 -m unittest discover -s tests    # coverage / vocabulary / count checks
python3 scripts/summary.py               # the summary tables below (markdown)
```

Review aids (all write to `out/`, which is git-ignored):

| Script | Output |
|---|---|
| `scripts/scan_map.py` | `out/tile_usage.csv`, `out/sprite_usage.csv`, `out/placements.csv` (machine-derived inputs; `build_tables.py` calls the same functions) |
| `scripts/tile_sheets.py [ts...]` | `out/tiles/tsNN.png`: tileset at 2x, each cell labelled with its cell index and use count; unused cells dimmed |
| `scripts/tile_overlay.py [ts...]` | `out/tiles/tsNN_labels.png`: same, with the current terrain label (white high, yellow medium, red low confidence) |
| `scripts/sprite_sheets.py [seq...]` | `out/sprites/all_N.png` (every placed frame) or `seqNNN_1.png`, labelled `seq.frame n=count WxH` |
| `scripts/render_screen.py N...` | `out/screens/sNNN.png`: one screen (tiles + depth-sorted sprites), each sprite tagged `index:seq.frame` (yellow live, cyan background, magenta hardness-only) |

`scripts/dinkdata.py` is a small self-contained reader for `dink.dat`,
`map.dat`, `hard.dat`, `dink.ini` and `dir.ff` (stdlib + Pillow/numpy). It does
not import `tools/dinkex`. `scripts/features.py` holds the colour helpers used
by the semi-automatic tile rules.

## How the tile table was made

Each used tileset (33 of 41) was viewed. What a sheet depicts (grass with
boulders, a shoreline, a cliff, ...) was decided by eye and written as one
rule set per sheet in `tile_labels.py`:

* **hand rules** list cell ranges (cliffs, water banks, floors, forest, facades);
* **auto rules** are used for sheets that are blends of known materials. Reference
  cells for each material are picked by hand, each pixel is assigned to the nearest
  reference colour, and the cell is labelled from those fractions (for boulder
  sheets: rock fraction under a threshold = base ground, over a second threshold
  = `rock_mass`, between = rocky). The resulting overlays were reviewed and wrong
  cells corrected (`OVERRIDES`). The fractions are kept in `notes`.

Columns: `tile_num, tileset, cell, use_count, screen_count, indoor_use, terrain,
is_transition (0/1), blend_classes ("primary|secondary" when is_transition),
walkable_hint, animated (water|fire|""), hard_solid_pct, hard_low_pct,
confidence, notes`.

`walkable_hint` is the **intended 3D walkability** of the terrain class (and
`partial` for a blend of walkable and non-walkable classes). It is *not* read
from `hard.dat`: original tile hardness is drawn as thin outlines (a shore has a
1-px "low" line, open sea and forest-canopy tiles are hardness-free inside), so
`hard_solid_pct` / `hard_low_pct` (mean over all uses, with per-tile `althard`
overrides applied) are given only as evidence. True reachable areas need the
stage-3 flood fill.

### Terrain vocabulary

| terrain | walkable | meaning |
|---|---|---|
| grass | yes | Open meadow grass (incl. flower-speckled variants). |
| grass_rocky | partial | Grass with painted boulders; place rock meshes on it. |
| rock_mass | no | Dense boulder pile / outcrop core painted into tiles; impassable. |
| gravel | yes | Bare stony clearing (no road edges). |
| path | yes | Gravel road / town path with defined edges. |
| dirt | yes | Bare brown earth / mud plot. |
| sand | yes | Beach or dune sand. |
| water | no | Open water (river, lake, sea). Depth is not encoded in the tiles. |
| ice | yes | Frozen water around the snow island (probable; could be cold sea). |
| snow | yes | Snow ground. |
| lava | no | Fire pit / burning ground (animated fire tiles). |
| cliff_face | no | Vertical earth/rock cliff or ridge wall; needs real elevation in 3D. |
| forest_canopy | no | Dense forest roof seen from above; impassable tree mass. |
| wasteland | yes | Grey-blue barren ground of the Darklands. |
| chasm | no | Black bottomless pit in the Darklands. |
| cave_floor | yes | Cave dungeon floor. |
| cave_wall | no | Cave rock wall / spiky rock mass. |
| wood_floor | yes | Interior plank floor. |
| stone_floor | yes | Castle / dungeon flagstones (incl. cracked variants). |
| structure_facade | no | Building wall and roof painted into the tile layer (big buildings). |
| void | no | Solid black outside interior rooms. |

Water: `water` covers rivers, lakes and sea alike. The animated family
(ts08, nums 896-1023, frames in ts09-ts13) is used for rivers **and** the south
bay; ts14/ts15 static water is used along the west and east coasts. Depth is not
encoded anywhere, so river/lake/sea and shallow/deep are a stage-3 region
decision, not a tile property.

## How the sprite table was made

All 559 placed frames were viewed on contact sheets (`out/sprites/all_*.png`).
Where the picture alone was ambiguous (arrows, duck heads, red bars, fruit,
posts, holes) the screens using them were rendered and the attached script read.
`sprite_labels.py` holds one default entry per sequence plus per-frame
overrides. Machine columns come from the scan; hand columns from the labels.

Columns:

| column | source | meaning |
|---|---|---|
| seq, frame | scan | |
| placement_count, type0_background, type1_live, type2_hardness_only | scan | placement counts by editor type |
| screen_count, example_screens | scan | where it is used (first 8 screens) |
| source_file, pixel_size | `dink.ini` + `dir.ff` | frame bitmap (`dir.ff:name` when packed), after `SET_FRAME_FRAME` aliasing |
| class_id | hand | stable snake_case id; same object from another angle or a colour variant shares the class_id or at least the family |
| category | hand | see vocabulary |
| name | hand | human name |
| family | hand | building / kit / creature family that ties frames together |
| treatment | hand | suggested 3D treatment |
| original_view | hand | 2D facts that matter in 3D (one facing only, roof piece, one of 4 fence angles, animation frame, ...) |
| gameplay_flags | hand | inferred gameplay role (burnable, bombable, pushable, door/warp, pickup, breakable, talk) |
| script_flags | scan | procedures found in the attached scripts (`talk hit push touch die use`) plus `burnable` (script sets `&missile_target` to seq 20, tree fire) and `bombable` (script checks `dam-bom*`), as `flag:placements` |
| scripts | scan | attached script names with counts |
| warp_count | scan | placements with `prop = 1` (warp) |
| confidence, notes | hand | |

### Category vocabulary

`structure` (whole building or landmark), `structure_part` (wall/roof/door/kit
piece of an outdoor structure, bridges, fences), `interior_wall`, `furniture`,
`prop`, `flora_tree`, `flora_bush`, `flora_grass` (grass, weeds, flowers, crops,
vines), `rock`, `npc` (incl. corpses of NPCs), `enemy`, `animal`, `pickup`,
`container` (breakable/openable loot holders), `effect`, `ui`, `hazard`
(thorns, holes), `other`.

### Treatment vocabulary

| treatment | meaning |
|---|---|
| bespoke | unique hero asset modelled for Dink (identity creatures, unique buildings, landmarks) |
| modular_kit | piece of a modular building/interior/fence/bridge kit; the importer should map it to a kit piece |
| sourced | take from CC0 / Fab libraries and adapt (boulders, generic humans, goblins, pig) |
| pcg_scatter | placed procedurally by PCG (trees, bushes, grass, pebbles, shells, bones); the original positions are only a density hint |
| generated | individual generic prop, AI-generated or quick-modelled then cleaned (furniture, barrels, signs, food) |
| vfx | Niagara / material effect (fire, explosions, blood, sparkles) |
| not_needed | nothing to build |

## Summary

### Terrain classes (tile table)

| terrain | tile rows | of which transitions | cells placed | % of world cells |
|---|---:|---:|---:|---:|
| grass | 239 | 77 | 21683 | 35.1 |
| water | 99 | 26 | 9169 | 14.8 |
| cliff_face | 183 | 119 | 4336 | 7.0 |
| sand | 106 | 70 | 3812 | 6.2 |
| wasteland | 156 | 14 | 3152 | 5.1 |
| forest_canopy | 24 | 4 | 3086 | 5.0 |
| stone_floor | 76 | 0 | 2974 | 4.8 |
| grass_rocky | 94 | 0 | 2387 | 3.9 |
| wood_floor | 4 | 0 | 1731 | 2.8 |
| path | 53 | 24 | 1714 | 2.8 |
| void | 4 | 0 | 1676 | 2.7 |
| ice | 20 | 11 | 1370 | 2.2 |
| snow | 79 | 8 | 1108 | 1.8 |
| cave_floor | 48 | 20 | 1009 | 1.6 |
| chasm | 28 | 7 | 910 | 1.5 |
| cave_wall | 8 | 4 | 527 | 0.9 |
| structure_facade | 104 | 0 | 465 | 0.8 |
| rock_mass | 67 | 0 | 450 | 0.7 |
| lava | 23 | 13 | 128 | 0.2 |
| gravel | 19 | 15 | 89 | 0.1 |
| dirt | 16 | 12 | 48 | 0.1 |

Grouped into outdoor biomes: temperate meadow/forest (grass, grass_rocky,
forest_canopy, gravel, path, dirt), coast (sand, water), river/lake (water),
escarpment and ridges (cliff_face, rock_mass), Darklands (wasteland, chasm),
snow (snow, ice), caves (cave_floor, cave_wall), fire pit (lava); plus interior
floors (wood_floor, stone_floor, void) and tile-painted big buildings
(structure_facade, ts34/35: upper storeys of the big town buildings on
screens 385-420, 465-506 and 538; town names not verified).

### Sprite categories and 3D treatments

| category | (seq,frame) rows | distinct class_ids | placements |
|---|---:|---:|---:|
| flora_tree | 13 | 10 | 912 |
| interior_wall | 32 | 15 | 902 |
| rock | 35 | 11 | 606 |
| flora_grass | 25 | 7 | 578 |
| structure_part | 99 | 41 | 576 |
| prop | 103 | 36 | 557 |
| enemy | 67 | 13 | 380 |
| flora_bush | 6 | 6 | 256 |
| furniture | 28 | 14 | 211 |
| hazard | 8 | 3 | 152 |
| container | 6 | 6 | 149 |
| animal | 14 | 4 | 117 |
| structure | 29 | 20 | 115 |
| pickup | 28 | 18 | 103 |
| other | 4 | 3 | 96 |
| effect | 28 | 11 | 77 |
| npc | 34 | 24 | 59 |

| treatment | (seq,frame) rows | distinct class_ids | placements |
|---|---:|---:|---:|
| pcg_scatter | 77 | 30 | 2420 |
| modular_kit | 113 | 43 | 1429 |
| generated | 173 | 78 | 1228 |
| bespoke | 106 | 45 | 510 |
| sourced | 61 | 34 | 178 |
| vfx | 28 | 11 | 77 |
| not_needed | 1 | 1 | 4 |

| confidence | tile rows | tile cells | sprite rows | placements |
|---|---:|---:|---:|---:|
| high | 1029 | 48587 | 516 | 5610 |
| medium | 388 | 12661 | 39 | 228 |
| low | 33 | 576 | 4 | 8 |

242 distinct class_ids in 68 families.

### Environment art backlog: class_ids needing bespoke or modular-kit work

Identity creatures (duck, pillbug, bonca, slayer, dragon, Dink, mom, king) are
listed too because the plan makes them bespoke; the rest is environment art.

| treatment | family | class_id | category | example name | placements | seq.frame |
|---|---|---|---|---|---:|---|
| bespoke | bonca | bonca_brown | enemy | Bonca (brown) | 12 | 531.1 531.5 533.1 537.1 539.1 542.1 542.5 544.1 544.4 |
| bespoke | bonca | bonca_gray | enemy | Bonca (grey) | 21 | 592.1 594.1 601.1 603.1 603.8 607.1 609.1 |
| bespoke | bonca | bonca_purple | enemy | Bonca (purple) | 10 | 611.1 613.1 613.3 613.4 613.6 619.1 626.1 628.1 |
| bespoke | bridge_stone | bridge_stone | structure | Stone arch bridge | 4 | 186.4 186.5 |
| bespoke | church | church | structure | Stone church | 3 | 60.1 |
| bespoke | church | church_door | structure_part | Church door | 1 | 60.7 |
| bespoke | church | church_stained_glass | structure_part | Stained-glass window | 3 | 60.4 60.5 60.6 |
| bespoke | church | church_window_small | structure_part | Church small window | 2 | 60.2 60.9 |
| bespoke | cottage_thatched | chimney_stone | structure_part | Stone chimney | 6 | 63.11 63.12 63.13 |
| bespoke | cottage_thatched | cottage_thatched_l_shape | structure | L-shaped thatched cottage | 6 | 63.10 |
| bespoke | cottage_thatched | cottage_thatched_large | structure | Thatched stone cottage | 16 | 63.6 |
| bespoke | cottage_thatched | cottage_thatched_long | structure | Thatched stone cottage | 6 | 63.1 |
| bespoke | cottage_thatched | cottage_thatched_small | structure | Thatched stone cottage | 16 | 63.7 63.8 |
| bespoke | cottage_thatched | cottage_thatched_two_storey | structure | Two-storey thatched cottage | 7 | 63.4 63.5 |
| bespoke | dink | dink_dead | npc | Dink lying dead (cutscene pose) | 1 | 436.16 |
| bespoke | dragon | dragon | enemy | Dragon | 16 | 202.1 202.6 202.7 204.1 206.1 208.1 |
| bespoke | dragon | dragon_corpse | enemy | Dead dragon | 3 | 212.1 216.1 |
| bespoke | duck | duck | animal | Duck | 92 | 21.1 23.1 24.1 26.1 27.1 29.1 |
| bespoke | dungeon_stone_kit | idol_statue_small | prop | Small demon idol | 5 | 80.24 |
| bespoke | fountain | fountain_stone | structure | Stone fountain | 2 | 66.23 66.24 |
| bespoke | ground_holes | cave_hole_warp | structure_part | Hole into a cave (warp) | 11 | 89.10 |
| bespoke | island_village | island_hut_round | structure | Koka Isle round hut | 12 | 424.1 424.2 424.3 |
| bespoke | island_village | island_hut_two_storey | structure | Two-tier round hut | 4 | 424.4 424.6 |
| bespoke | landmarks | well_stone | structure | Stone well with roof | 5 | 186.1 186.2 |
| bespoke | log_cabin | log_cabin | structure | Log cabin | 2 | 59.1 |
| bespoke | log_cabin | log_cabin_door | structure_part | Log cabin door | 2 | 59.2 |
| bespoke | log_cabin | log_cabin_window | structure_part | Log cabin window | 9 | 59.3 |
| bespoke | monuments | dink_monument_rock | structure | "Dink Smallwood" carved rock | 1 | 159.4 |
| bespoke | monuments | dragon_statue | structure | Dragon statue on orb | 13 | 159.5 159.6 |
| bespoke | monuments | golden_duck_statue | structure | Golden duck statue | 1 | 159.8 |
| bespoke | monuments | teleport_machine | structure | Teleport machine (armillary sphere) | 2 | 84.1 |
| bespoke | monuments | teleport_shrine | structure | Shrine with stained glass (teleporter) | 3 | 159.7 |
| bespoke | npc_king | king_on_throne | npc | King Daniel on throne (seated) | 1 | 421.31 |
| bespoke | npc_mom | npc_mom | npc | Dink's mother | 1 | 351.1 |
| bespoke | pillbug | pillbug | enemy | Pillbug | 166 | 131.1 131.2 131.3 131.4 131.5 133.1 133.2 133.3 133.4 |
| bespoke | save_machine | save_machine | structure | Save machine | 10 | 449.1 |
| bespoke | siege | ballista | structure | Ballista | 1 | 429.4 |
| bespoke | siege | catapult | structure | Catapult | 1 | 429.1 |
| bespoke | slayer | slayer | enemy | Slayer | 21 | 632.1 632.4 634.1 636.1 641.1 643.1 647.1 649.1 |
| bespoke | snake_pillar | snake_carving | prop | Small stone snake carving | 1 | 81.1 |
| bespoke | snake_pillar | snake_pillar | structure_part | Pillar with coiled snake | 7 | 82.1 |
| bespoke | snow_house | snow_house_door | structure_part | House door | 1 | 96.10 |
| bespoke | snow_house | snow_house_lower | structure_part | House lower walls | 1 | 96.1 |
| bespoke | snow_house | snow_house_roof | structure_part | House pyramid roof | 1 | 96.3 |
| bespoke | snow_house | snow_house_timber | structure_part | House timbered upper walls | 1 | 96.2 |
| modular_kit | bridge_wood | bridge_wood_deck | structure_part | Wooden bridge deck | 22 | 58.1 58.2 58.3 |
| modular_kit | bridge_wood | bridge_wood_rail_plank | structure_part | Bridge side rail with planking | 7 | 58.6 58.8 58.10 |
| modular_kit | bridge_wood | bridge_wood_rail_rope | structure_part | Bridge rope rail | 7 | 58.7 58.9 58.11 |
| modular_kit | castle_kit | castle_door | structure_part | Castle door | 1 | 68.1 |
| modular_kit | castle_kit | castle_drawbridge | structure_part | Drawbridge with chains | 1 | 68.6 |
| modular_kit | castle_kit | castle_gatehouse | structure_part | Castle gatehouse block | 1 | 67.5 |
| modular_kit | castle_kit | castle_tower_round | structure_part | Round castle tower | 20 | 67.1 67.2 67.3 67.4 |
| modular_kit | castle_kit | castle_wall_corner | structure_part | Castle wall corner | 12 | 67.8 |
| modular_kit | castle_kit | castle_wall_diag | structure_part | Castle curtain wall (diagonal run) | 46 | 67.6 67.7 67.9 |
| modular_kit | castle_kit | castle_wall_end | structure_part | Castle wall end (edge-on) | 2 | 67.12 |
| modular_kit | cottage_thatched | cottage_door | structure_part | Cottage door | 17 | 63.2 63.3 |
| modular_kit | doors | door_wood_single | structure_part | Wooden door | 21 | 61.1 |
| modular_kit | doors | door_wood_wide | structure_part | Wide wooden door | 15 | 62.1 |
| modular_kit | dungeon_stone_kit | dungeon_arch_freestanding | interior_wall | Freestanding stone archway | 1 | 80.25 |
| modular_kit | dungeon_stone_kit | dungeon_pillar | interior_wall | Stone pillar | 17 | 80.27 80.28 |
| modular_kit | dungeon_stone_kit | dungeon_wall_stone | interior_wall | Dungeon stone wall segment | 139 | 80.1 80.2 80.3 80.4 80.12 80.14 80.15 |
| modular_kit | dungeon_stone_kit | dungeon_wall_stone_arch | interior_wall | Dungeon wall with archway | 2 | 80.16 |
| modular_kit | dungeon_stone_kit | dungeon_wall_stone_cracked | interior_wall | Cracked / broken dungeon wall | 6 | 80.20 |
| modular_kit | dungeon_stone_kit | dungeon_wall_stone_curve | interior_wall | Dungeon curved wall | 65 | 80.7 80.8 80.9 80.10 |
| modular_kit | dungeon_stone_kit | dungeon_wall_stone_ivy | interior_wall | Dungeon wall overgrown with ivy | 8 | 80.18 80.19 |
| modular_kit | dungeon_stone_kit | dungeon_wall_stone_side | interior_wall | Dungeon wall end / side strip | 101 | 80.5 80.6 |
| modular_kit | fence_rail | fence_rail_diag_ne | structure_part | Rail fence diagonal | 8 | 93.2 93.5 |
| modular_kit | fence_rail | fence_rail_diag_nw | structure_part | Rail fence diagonal (other) | 17 | 93.3 93.6 |
| modular_kit | fence_rail | fence_rail_ew | structure_part | Rail fence (east-west, long) | 33 | 93.1 |
| modular_kit | fence_rail | fence_rail_ns | structure_part | Rail fence (north-south) | 32 | 93.4 |
| modular_kit | interior_plaster_kit | int_wall_plaster | interior_wall | Plaster wall segment | 180 | 31.26 31.27 31.28 31.29 31.30 |
| modular_kit | interior_plaster_kit | int_wall_plaster_corner_l | interior_wall | Plaster wall with left corner post | 35 | 31.22 |
| modular_kit | interior_plaster_kit | int_wall_plaster_corner_r | interior_wall | Plaster wall with right corner post | 32 | 31.21 |
| modular_kit | interior_plaster_kit | int_wall_plaster_doorjamb | interior_wall | Plaster wall door jamb / end cap | 85 | 31.35 31.36 |
| modular_kit | interior_plaster_kit | int_wall_plaster_end_l | interior_wall | Plaster wall, left end shading | 18 | 31.20 |
| modular_kit | interior_plaster_kit | int_wall_plaster_end_r | interior_wall | Plaster wall, right end trim | 19 | 31.19 |
| modular_kit | interior_plaster_kit | int_wall_plaster_side | interior_wall | Plaster side wall (edge-on strip) | 194 | 31.23 |
| modular_kit | interior_plaster_kit | support_post_timber | structure_part | Timber support post on stone footing | 21 | 87.10 |
| modular_kit | island_village | island_fence_lattice | structure_part | Lashed pole fence | 15 | 424.7 424.8 |
| modular_kit | stairs | cellar_hatch | structure_part | Cellar hatch / ladder | 2 | 428.5 |
| modular_kit | stairs | stairs_wood | structure_part | Wooden stairs | 9 | 428.1 428.2 428.3 428.4 |
| modular_kit | town_house_kit | town_roof_dormer | structure_part | Roof section with dormer window | 16 | 33.13 33.31 33.32 |
| modular_kit | town_house_kit | town_roof_flat | structure_part | Shingle roof section | 54 | 33.12 33.29 33.30 |
| modular_kit | town_house_kit | town_roof_ridge_cap | structure_part | Roof ridge / corner cap | 15 | 33.8 33.25 |
| modular_kit | town_house_kit | town_roof_slope | structure_part | Shingle roof slope | 17 | 33.9 33.26 33.27 |
| modular_kit | town_house_kit | town_wall_gable_end | structure_part | Timbered gable end / tower corner | 21 | 33.7 33.10 33.24 |
| modular_kit | town_house_kit | town_wall_stone_door | structure_part | Stone ground-floor wall with door | 15 | 33.3 33.5 33.6 33.21 33.23 33.33 33.34 33.38 33.39 |
| modular_kit | town_house_kit | town_wall_stone_window | structure_part | Stone ground-floor wall (windows / plain) | 80 | 33.1 33.2 33.11 33.14 33.15 33.16 33.17 33.18 33.19 33.35 33.36 33.37 33.40 33.41 33.42 33.43 33.44 33.45 33.46 |

### Low-confidence rows

* **Tiles: 33 low, 388 medium** (of 1,450; 576 and 12,661 cells). Low rows are
  almost all auto-labelled cells whose material fractions sit on a threshold:
  ridge sheets (ts05, ts24, ts29) and the ice/snow/ridge and pit sheets (ts30,
  ts25), where shading on plain ground is close to the ridge colour. Plus
  `ts11` cell 60 (one use of a water-animation frame cell as grass, likely an
  editor slip) and one darkened shore cell on ts15. Medium rows are mostly the
  remaining auto-labelled blend cells (shorelines, ridges, Darklands) and the
  cracked-flagstone variants. Getting one of these wrong only shifts a blend
  edge by one 50 px cell.
* **Sprites: 4 low, 39 medium** (of 559; 8 and 228 placements). Low:
  `450.1-3 wall_stripe_red` (health-bar UI art placed as a background strip in
  the bow shop, screen 97; purpose unclear) and `81.1 snake_carving` (15x13,
  brain 6, screen 625). Medium: food/fruit identities, a few small hand tools,
  hanging-sign emblems, `87.10 support_post_timber`, `80.20` cracked wall,
  `446 gravestone`, `95.8` blue crystal rock, `512.1` vertical fireball,
  `421.31` king, `121.1` duck heads.

### Against the plan's asset counts (REMASTER_PLAN.md section 6)

* **Building kits (plan: 13).** Building/structure families found: town house
  kit (seq 33 + tile facades ts34/35), thatched cottage (63), log cabin (59),
  church (60), castle (67/68), snow-region house (96), Koka Isle huts (424),
  dungeon stone kit (80), interior plaster kit (31 + 87.10 posts + doors/stairs),
  cave (tiles ts40 only, no sprites), wooden bridge (58), stone bridge (186.4/5),
  rail fence (93). That is 13 if bridges and fence count as kits, so the number
  holds, but note: the **town kit is half in the tile layer** (upper timbered
  storeys and roofs of the big town buildings are painted in
  ts34/ts35 and must be rebuilt by hand from those screens), cottages/church/
  cabin/snow house/huts are **whole single-view sprites** (bespoke buildings in
  ~6 footprints rather than kits), and doors (61, 62, 63.2/3, 59.2, 96.10, 60.7,
  68) are a shared door set.
* **Props (plan: about 150).** Distinct placed prop-like class_ids (prop,
  furniture, container, pickup, rock) = 85; adding flora (23) and hazards (3)
  gives 111. Frames that are only variants are already merged. 150 remains a
  fair budget once script-spawned items, inventory items and per-region variants
  (snow/Darklands boulders) are added, but the map alone needs fewer.
* **Biomes (plan: 8).** Matches: meadow/forest, coast, river/lake, escarpment,
  Darklands, snow/ice, caves, fire pit; interiors are floors, not biomes.
* **Save machines:** 10 placements of 449.1, matching section 3.
* **Burnable trees:** 3 placements (seq 32 frame 1 with s2-sec1, s2-sec3,
  s3-sec1; their `die` turns the tree into tree fire, seq 20, and reveals a hole).
  The fourth secret-script tree, s2-sec2, only jokes that magic is useless.
  **Bombable:** 3 rock placements (95.3 s4-rock, 95.5 s4-sec1) and one starfish
  (92.1 s5-sec1). **Pushable:** s1-roc / s3-rock boulders (95.1, 95.3, 95.4,
  95.10), the idol 80.24 (s2-idol) and s1-h1-4 house props.

### Open questions for a human

1. **Red strip on screen 97** (seq 450, health-bar art as background with a
   fountain talk script): banner, trim or editor marker? Check in the HD engine.
2. **ts30 blue around the snow island**: ice (walkable) or icy sea? Labelled
   `ice`; the original hardness will tell (stage 3).
3. **Water depth / body type** is not in the tiles; decide river/lake/sea per
   region in `regions.toml`.
4. **Tile-painted buildings** (ts34/35 facades with seq 33 ground floors):
   confirm these become one bespoke town block per screen group rather than a
   generic kit.
5. **Screen 145** (90 duck heads on a black void) and **screen 1** (burning
   house with placed fire effects): keep as a secret room / cutscene set, or cut?
6. **Pine forest edge strips** (32.8-32.10) and `forest_canopy` tiles: the 3D
   forest wall should be PCG pines plus blocking; confirm the forest interior is
   meant to be impassable (original tile hardness inside the canopy is empty,
   only the edge strips carry hardness).
7. **Dead-NPC sprites** placed as static corpses (245, 275, 335, ...): the
   content policy in plan section 5 says "no added gore"; decide how they show.
8. **seq 0 placements** on screens 162/194 (4 empty live sprites): editor junk
   or invisible script anchors? They have no script, so probably junk.

## Facts found while doing this

* Tile source rects always use a 12-column grid, even for tilesets narrower than
  600 px (ts01 is 400 px wide, so its cells 8-11 of each row do not exist).
* Original tile hardness is outline-based: shore tiles carry a thin low-hardness
  (2) line, open water and forest-canopy interiors are hardness 0.
* No placed sequence is redefined in `dink.ini` (only 102-108 are), so the last
  `load_sequence` line per seq is unambiguous for map sprites.
* Active placements use editor slots 1..96 only.
* 14 placements are type 0 (background) with a script attached; background
  sprites never run scripts.
