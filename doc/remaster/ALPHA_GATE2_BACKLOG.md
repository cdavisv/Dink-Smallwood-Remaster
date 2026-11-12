# Alpha gate 2 backlog: origin IDs still open

Generated 2026-11-12 by `DinkRemasterUE/Scripts/gate2_backlog.py` from `Saved/Import/coverage.csv` (6607 rows, importer run of 2026-11-11) and the manifests under `Content/Dink/Data/Art/`, classified by `Scripts/art_coverage.py`. Do not edit by hand; regenerate.

Alpha gate 2 (`doc/remaster/REMASTER_PLAN.md`): every origin ID is final, placeholder or cut with a reason. This list is what is still open: every origin ID whose art state in `Scripts/art_coverage.py` is `placeholder` (no art bound; nothing in the repo records a placeholder as owner-accepted), plus any unclassified ID. Final (bespoke or by family, `Content/Dink/Data/Art/families.json`) and cut (owner decision of 9 Nov 2026) are closed and not listed.

## Summary

| | open |
|---|---:|
| sprite families | 231 |
| origin IDs | 4941 |
| map placements | 4284 |
| screens (ground tile layer) | 639 |
| script warps with their own ID | 18 |
| unclassified IDs | 0 |

Claimed by the Claude photoreal pass (in progress elsewhere, not final): **120 families, 4329 origin IDs, 3683 placements**. Unclaimed: 111 families, 612 origin IDs, 601 placements.

Largest family by origin IDs: `screen ground (tile layer)` (639 IDs, 0 map placements, so it sorts at #231).

Largest families no stream has claimed: `blood_splat` 46, `tree_fruit` 34, `hand_tool_small` 30, `seashell_conch` 29, `burn_hole_decal` 26, `bonca_gray` 21, `slayer` 21, `npc_knight_blue` 18, `dragon` 16, `food_fruit` 15.

Closed for comparison (art_coverage rows): final bespoke 143, final by family 1326, cut 152, placeholder 4986 of 6607 rows.

## How to regenerate

```bash
cd DinkRemasterUE && python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md
```

Run it in the editor's checkout: like `art_coverage.py` it needs the importer's `Saved/Import/coverage.csv` (`Scripts/import_greybox.sh --region all`), `tools/dinkex/out/sequences.json` and the gitignored engine template content under `Content/Characters` (the mother's locomotion). From another worktree add `--project <editor checkout>/DinkRemasterUE`. The photoreal column is a snapshot of `<--photoreal-root>/*/manifest.json` (default: the uncommitted photoreal pass work copy), read-only; regenerate after that pass lands or binds families.

## Backlog by sprite family

Sorted by open map placements. Family is the class id (`tools/data/sprite_classes.csv`, the key `families.json` binds); *what the original shows* gives its name, sprite group, size and the reference sheet in `doc/remaster/reference/`; *sequences* are the original sprite sequences of the open placements. The origin IDs of each family are listed under [Open origin IDs](#open-origin-ids).

| # | family | what the original sprite sheet shows | sequences (open placements) | origin IDs | placements | photoreal pass |
|---:|---|---|---|---:|---:|---|
| 1 | [`beach_pebbles`](#f1-beach-pebbles) | Shell and pebble scatter (beach, 6x4 px) · sheet_lands.png | 92 lands/details/beach- (281) | 281 | 281 | Terrain |
| 2 | [`pebbles`](#f2-pebbles) | Pebble scatter (pebbles, 24x34 px) · sheet_lands.png | 97 lands/rocks/rocks- (214) | 214 | 214 | Terrain |
| 3 | [`int_wall_plaster_side`](#f3-int-wall-plaster-side) | Plaster side wall (edge-on strip) (interior_plaster_kit, 18x100 px) · sheet_inside.png | 31 inside/innwalls/walls/inn- (188) | 188 | 188 | WallKits |
| 4 | [`int_wall_plaster`](#f4-int-wall-plaster) | Plaster wall segment (interior_plaster_kit, 100x100 px) · sheet_inside.png | 31 inside/innwalls/walls/inn- (174) | 174 | 174 | WallKits |
| 5 | [`pillbug`](#f5-pillbug) | Pillbug (pillbug, 47x42 px) · sheet_foes.png | 133 foes/pill/f1-w3- (89), 131 foes/pill/f1-w1- (65) | 154 | 154 | Creatures |
| 6 | [`thorn_bush`](#f6-thorn-bush) | Thorn bramble (graveyard, 102x80 px) · sheet_lands.png | 90 lands/details/grave- (142) | 142 | 142 | Vegetation |
| 7 | [`dungeon_wall_stone`](#f7-dungeon-wall-stone) | Dungeon stone wall segment (dungeon_stone_kit, 100x100 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (139) | 139 | 139 | WallKits |
| 8 | [`pine_forest_edge_strip_vert`](#f8-pine-forest-edge-strip-vert) | Pine forest edge strip (vertical) (trees, 51x377 px) · sheet_lands.png | 32 lands/trees/tree- (123) | 123 | 123 | Vegetation |
| 9 | [`dungeon_wall_stone_side`](#f9-dungeon-wall-stone-side) | Dungeon wall end / side strip (dungeon_stone_kit, 30x100 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (101) | 101 | 101 | WallKits |
| 10 | [`duck`](#f10-duck) | Duck (duck, 31x41 px) · sheet_foes.png | 23 animals/duck/dk3w- (24), 29 animals/duck/dk9w- (18), 24 animals/duck/dk4w- (14), 26 animals/duck/dk6w- (12), 27 animals/duck/dk7w- (12), 21 animals/duck/dk1w- (11) | 92 | 91 | Creatures |
| 11 | [`duck_head`](#f11-duck-head) | Duck head (death sprite) used as set dressing (duck, 15x42 px) · sheet_foes.png | 121 animals/duck/death/dkh1x- (90) | 90 | 90 | Creatures |
| 12 | [`int_wall_plaster_doorjamb`](#f12-int-wall-plaster-doorjamb) | Plaster wall door jamb / end cap (interior_plaster_kit, 18x100 px) · sheet_inside.png | 31 inside/innwalls/walls/inn- (81) | 81 | 81 | WallKits |
| 13 | [`town_wall_stone_window`](#f13-town-wall-stone-window) | Stone ground-floor wall (windows / plain) (town_house_kit, 100x132 px) · sheet_struct.png | 33 struct/outinn/oinn- (80) | 80 | 80 | TownExteriors |
| 14 | [`slime_blue`](#f14-slime-blue) | Slime (blue) (slime, 24x18 px) · sheet_foes.png | 651 foes/puddle/blue/walk/f06w1- (67) | 67 | 67 | Creatures |
| 15 | [`seashell_clam`](#f15-seashell-clam) | Clam shell (beach, 19x14 px) · sheet_lands.png | 92 lands/details/beach- (66) | 66 | 66 | Terrain |
| 16 | [`dungeon_wall_stone_curve`](#f16-dungeon-wall-stone-curve) | Dungeon curved wall (dungeon_stone_kit, 100x150 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (65) | 65 | 65 | WallKits |
| 17 | [`bush_small`](#f17-bush-small) | Bush (bushes, 85x65 px) · sheet_lands.png | 179 lands/shrubs/bush- (57) | 57 | 57 | Vegetation |
| 18 | [`bush_round_medium`](#f18-bush-round-medium) | Bush (bushes, 80x54 px) · sheet_lands.png | 179 lands/shrubs/bush- (56) | 56 | 56 | Vegetation |
| 19 | [`town_roof_flat`](#f19-town-roof-flat) | Shingle roof section (town_house_kit, 100x200 px) · sheet_struct.png | 33 struct/outinn/oinn- (54) | 54 | 54 | TownExteriors |
| 20 | [`jar_vase`](#f20-jar-vase) | Jar / vase / bottle (pottery, 22x31 px) · sheet_items.png | 448 items/cup/cup- (52) | 52 | 52 | Props |
| 21 | [`fern`](#f21-fern) | Fern clump (ground_plants, 65x45 px) · sheet_lands.png | 65 lands/grass/grass- (50) | 50 | 50 | Vegetation |
| 22 | [`starfish`](#f22-starfish) | Starfish (beach, 25x17 px) · sheet_lands.png | 92 lands/details/beach- (47) | 47 | 47 | Terrain |
| 23 | [`tree_stump`](#f23-tree-stump) | Tree stump (trees, 45x33 px) · sheet_lands.png | 32 lands/trees/tree- (47) | 47 | 47 | Vegetation |
| 24 | [`blood_splat`](#f24-blood-splat) | Blood splatter (blood, 39x56 px) · sheet_effects.png | 188 effects/spurt/sprtl- (24), 189 effects/spurt/sprtr- (18), 187 effects/spurt/spurt- (4) | 46 | 46 | - |
| 25 | [`bones`](#f25-bones) | Scattered bones (graveyard, 50x36 px) · sheet_lands.png | 90 lands/details/grave- (46) | 46 | 46 | Props |
| 26 | [`bush_round_large`](#f26-bush-round-large) | Bush (bushes, 116x69 px) · sheet_lands.png | 179 lands/shrubs/bush- (46) | 46 | 46 | Vegetation |
| 27 | [`castle_wall_diag`](#f27-castle-wall-diag) | Castle curtain wall (diagonal run) (castle_kit, 350x463 px) · sheet_struct.png | 67 struct/castle/castl- (46) | 46 | 46 | Structures |
| 28 | [`pine_forest_edge_strip`](#f28-pine-forest-edge-strip) | Pine forest edge strip (horizontal) (trees, 200x95 px) · sheet_lands.png | 32 lands/trees/tree- (40) | 40 | 40 | Vegetation |
| 29 | [`bush_wide`](#f29-bush-wide) | Bush (bushes, 153x84 px) · sheet_lands.png | 179 lands/shrubs/bush- (36) | 36 | 36 | Vegetation |
| 30 | [`int_wall_plaster_corner_l`](#f30-int-wall-plaster-corner-l) | Plaster wall with left corner post (interior_plaster_kit, 100x100 px) · sheet_inside.png | 31 inside/innwalls/walls/inn- (34) | 34 | 34 | WallKits |
| 31 | [`tree_fruit`](#f31-tree-fruit) | Fruit hanging in a tree (food, 7x12 px) · sheet_items.png | 421 items/food/food- (34) | 34 | 34 | - |
| 32 | [`tree_dead_dark`](#f32-tree-dead-dark) | Dead leafless tree (dark) (trees, 243x258 px) · sheet_lands.png | 32 lands/trees/tree- (33) | 33 | 33 | Vegetation |
| 33 | [`int_wall_plaster_corner_r`](#f33-int-wall-plaster-corner-r) | Plaster wall with right corner post (interior_plaster_kit, 100x100 px) · sheet_inside.png | 31 inside/innwalls/walls/inn- (31) | 31 | 31 | WallKits |
| 34 | [`hand_tool_small`](#f34-hand-tool-small) | Small hand tool (hammer, axe, tongs) (tools, 23x22 px) · sheet_items.png | 447 items/tools/tool- (30) | 30 | 30 | - |
| 35 | [`sign_post`](#f35-sign-post) | Signpost (signs, 50x92 px) · sheet_struct.png | 186 struct/landmark/landm- (30) | 30 | 30 | Structures |
| 36 | [`seashell_conch`](#f36-seashell-conch) | Conch shell (beach, 15x15 px) · sheet_lands.png | 92 lands/details/beach- (29) | 29 | 29 | - |
| 37 | [`slime_red`](#f37-slime-red) | Slime (red) (slime, 25x18 px) · sheet_foes.png | 693 foes/puddle/red/walk/f06w3- (17), 691 foes/puddle/red/walk/f06w1- (12) | 29 | 29 | Creatures |
| 38 | [`burn_hole_decal`](#f38-burn-hole-decal) | Burnt hole / scorch mark (damage, 23x20 px) · sheet_struct.png | 158 struct/details/damage/hole- (26) | 26 | 26 | - |
| 39 | [`counter_wood`](#f39-counter-wood) | Wooden shop/bar counter (house_interior, 156x77 px) · sheet_inside.png | 64 inside/details/inacc- (22) | 23 | 22 | Props |
| 40 | [`bridge_wood_deck`](#f40-bridge-wood-deck) | Wooden bridge deck (bridge_wood, 65x88 px) · sheet_struct.png | 58 struct/bridge/brdge- (22) | 22 | 22 | Structures |
| 41 | [`bonca_gray`](#f41-bonca-gray) | Bonca (grey) (bonca, 97x91 px) · sheet_foes.png | 601 foes/bonca/gray/walk/f03w1- (6), 603 foes/bonca/gray/walk/f03w3- (4), 609 foes/bonca/gray/walk/f03w9- (4), 592 foes/bonca/gray/attack/f03a6- (3), 607 foes/bonca/gray/walk/f03w7- (3), 594 foes/bonca/gray/attack/f03a2- (1) | 21 | 21 | - |
| 42 | [`crate`](#f42-crate) | Wooden crate (crates, 64x48 px) · sheet_items.png | 443 items/boxes/boxb1- (21) | 21 | 21 | Props |
| 43 | [`slayer`](#f43-slayer) | Slayer (slayer, 113x105 px) · sheet_foes.png | 632 foes/slayers/attack/f04a2- (7), 641 foes/slayers/walk/f04w1- (6), 634 foes/slayers/attack/f04a4- (4), 643 foes/slayers/walk/f04w3- (1), 649 foes/slayers/walk/f04w9- (1), 647 foes/slayers/walk/f04w7- (1), 636 foes/slayers/attack/f04a6- (1) | 21 | 21 | - |
| 44 | [`support_post_timber`](#f44-support-post-timber) | Timber support post on stone footing (interior_plaster_kit, 47x106 px) · sheet_inside.png | 87 inside/details/table- (21) | 21 | 21 | Props |
| 45 | [`town_wall_gable_end`](#f45-town-wall-gable-end) | Timbered gable end / tower corner (town_house_kit, 92x200 px) · sheet_struct.png | 33 struct/outinn/oinn- (21) | 21 | 21 | TownExteriors |
| 46 | [`door_wood_single`](#f46-door-wood-single) | Wooden door (doors, 24x64 px) · sheet_struct.png | 61 struct/details/door/odor1- (20) | 22 | 20 | Structures |
| 47 | [`cabinet_wood`](#f47-cabinet-wood) | Wooden cabinet / dresser (house_interior, 57x79 px) · sheet_inside.png | 87 inside/details/table- (20) | 20 | 20 | Props |
| 48 | [`castle_tower_round`](#f48-castle-tower-round) | Round castle tower (castle_kit, 193x409 px) · sheet_struct.png | 67 struct/castle/castl- (20) | 20 | 20 | Structures |
| 49 | [`grain_sack`](#f49-grain-sack) | Grain sack (sacks, 50x42 px) · sheet_items.png | 463 items/grain/bag- (19) | 19 | 19 | Props |
| 50 | [`int_wall_plaster_end_r`](#f50-int-wall-plaster-end-r) | Plaster wall, right end trim (interior_plaster_kit, 100x100 px) · sheet_inside.png | 31 inside/innwalls/walls/inn- (19) | 19 | 19 | WallKits |
| 51 | [`flower_small`](#f51-flower-small) | Small flower (garden, 28x35 px) · sheet_lands.png | 66 lands/garden/gardn- (18) | 18 | 18 | Vegetation |
| 52 | [`int_wall_plaster_end_l`](#f52-int-wall-plaster-end-l) | Plaster wall, left end shading (interior_plaster_kit, 100x100 px) · sheet_inside.png | 31 inside/innwalls/walls/inn- (18) | 18 | 18 | WallKits |
| 53 | [`npc_knight_blue`](#f53-npc-knight-blue) | Knight (blue) (npc_knight, 91x125 px) · sheet_people.png | 287 people/knight/blue/c5-w7- (8), 289 people/knight/blue/c5-w9- (8), 281 people/knight/blue/c5-w1- (1), 283 people/knight/blue/c5-w3- (1) | 18 | 18 | - |
| 54 | [`tree_dead_frosted`](#f54-tree-dead-frosted) | Dead leafless tree (frosted / snow) (trees, 164x197 px) · sheet_lands.png | 32 lands/trees/tree- (18) | 18 | 18 | Vegetation |
| 55 | [`bowl`](#f55-bowl) | Bowl (pottery, 17x15 px) · sheet_items.png | 448 items/cup/cup- (17) | 17 | 17 | Props |
| 56 | [`dungeon_pillar`](#f56-dungeon-pillar) | Stone pillar (dungeon_stone_kit, 40x97 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (17) | 17 | 17 | Props |
| 57 | [`fence_rail_ns`](#f57-fence-rail-ns) | Rail fence (north-south) (fence_rail, 26x136 px) · sheet_lands.png | 93 lands/fence/fence- (17) | 17 | 17 | Structures |
| 58 | [`town_roof_slope`](#f58-town-roof-slope) | Shingle roof slope (town_house_kit, 100x150 px) · sheet_struct.png | 33 struct/outinn/oinn- (17) | 17 | 17 | TownExteriors |
| 59 | [`cottage_door`](#f59-cottage-door) | Cottage door (cottage_thatched, 55x89 px) · sheet_struct.png | 63 struct<HOME> (16) | 16 | 16 | Structures |
| 60 | [`cottage_thatched_large`](#f60-cottage-thatched-large) | Thatched stone cottage (cottage_thatched, 334x259 px) · sheet_struct.png | 63 struct<HOME> (16) | 16 | 16 | Structures |
| 61 | [`cottage_thatched_small`](#f61-cottage-thatched-small) | Thatched stone cottage (cottage_thatched, 257x225 px) · sheet_struct.png | 63 struct<HOME> (16) | 16 | 16 | Structures |
| 62 | [`dragon`](#f62-dragon) | Dragon (dragon, 164x188 px) · sheet_foes.png | 202 foes/dragon/f2-w2- (8), 206 foes/dragon/f2-w6- (4), 204 foes/dragon/f2-w4- (3), 208 foes/dragon/f2-w8- (1) | 16 | 16 | - |
| 63 | [`mushroom`](#f63-mushroom) | Mushroom (garden, 30x39 px) · sheet_lands.png | 66 lands/garden/gardn- (16) | 16 | 16 | Vegetation |
| 64 | [`town_roof_dormer`](#f64-town-roof-dormer) | Roof section with dormer window (town_house_kit, 100x200 px) · sheet_struct.png | 33 struct/outinn/oinn- (16) | 16 | 16 | TownExteriors |
| 65 | [`door_wood_wide`](#f65-door-wood-wide) | Wide wooden door (doors, 53x68 px) · sheet_struct.png | 62 struct/details/door/odor2- (15) | 15 | 15 | Structures |
| 66 | [`food_fruit`](#f66-food-fruit) | Fruit (apple / pear / etc.) (food, 17x23 px) · sheet_items.png | 421 items/food/food- (15) | 15 | 15 | - |
| 67 | [`gold_pile`](#f67-gold-pile) | Gold pile (lgold) (gold, 37x19 px) · sheet_items.png | 178 bonuses/coins/coin- (15) | 15 | 15 | - |
| 68 | [`hanging_vines`](#f68-hanging-vines) | Hanging vines (dungeon_stone_kit, 50x114 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (15) | 15 | 15 | Vegetation |
| 69 | [`island_fence_lattice`](#f69-island-fence-lattice) | Lashed pole fence (island_village, 271x76 px) · sheet_struct.png | 424 struct/island/isle- (15) | 15 | 15 | Structures |
| 70 | [`potion_red`](#f70-potion-red) | Red potion (magic) (potions, 19x52 px) · sheet_items.png | 56 bonuses/bottles/botl-r (15) | 15 | 15 | Props |
| 71 | [`town_roof_ridge_cap`](#f71-town-roof-ridge-cap) | Roof ridge / corner cap (town_house_kit, 60x45 px) · sheet_struct.png | 33 struct/outinn/oinn- (15) | 15 | 15 | TownExteriors |
| 72 | [`town_wall_stone_door`](#f72-town-wall-stone-door) | Stone ground-floor wall with door (town_house_kit, 100x132 px) · sheet_struct.png | 33 struct/outinn/oinn- (15) | 15 | 15 | TownExteriors |
| 73 | [`arrow_prop`](#f73-arrow-prop) | Arrow (shop display / stuck in ground) (arrow, 47x30 px) · sheet_effects.png | 25 effects/arrow/arrow- (14) | 14 | 14 | - |
| 74 | [`chest_small`](#f74-chest-small) | Treasure chest (small) (chests, 44x60 px) · sheet_items.png | 175 bonuses/chest/chst1- (14) | 14 | 14 | Props |
| 75 | [`fence_rail_diag_nw`](#f75-fence-rail-diag-nw) | Rail fence diagonal (other) (fence_rail, 77x88 px) · sheet_lands.png | 93 lands/fence/fence- (14) | 14 | 14 | Structures |
| 76 | [`gravestone`](#f76-gravestone) | Engraved gravestone (graveyard, 34x43 px) · sheet_items.png | 446 items/tomb/tomb- (14) | 14 | 14 | Props |
| 77 | [`stone_giant`](#f77-stone-giant) | Stone giant (stone_giant, 104x88 px) · sheet_foes.png | 821 foes/stonegnt/walk/f01w1- (8), 823 foes/stonegnt/walk/f01w3- (3), 816 foes/stonegnt/attack/f01a6- (1), 829 foes/stonegnt/walk/f01w9- (1), 827 foes/stonegnt/walk/f01w7- (1) | 14 | 14 | - |
| 78 | [`crate_small`](#f78-crate-small) | Small wooden crate (crates, 47x44 px) · sheet_items.png | 444 items/boxes/boxb3- (13) | 13 | 13 | Props |
| 79 | [`dragon_statue`](#f79-dragon-statue) | Dragon statue on orb (monuments, 140x167 px) · sheet_struct.png | 159 struct/stone/mdink/monum- (13) | 13 | 13 | - |
| 80 | [`skull`](#f80-skull) | Skull (graveyard, 16x20 px) · sheet_lands.png | 90 lands/details/grave- (13) | 13 | 13 | Props |
| 81 | [`bonca_brown`](#f81-bonca-brown) | Bonca (brown) (bonca, 85x94 px) · sheet_foes.png | 542 foes/bonca/attack/f03a6- (2), 544 foes/bonca/attack/f03a2- (2), 533 foes/bonca/walk/f03w3- (2), 539 foes/bonca/walk/f03w9- (2), 537 foes/bonca/walk/f03w7- (2), 531 foes/bonca/walk/f03w1- (2) | 12 | 12 | - |
| 82 | [`castle_wall_corner`](#f82-castle-wall-corner) | Castle wall corner (castle_kit, 350x505 px) · sheet_struct.png | 67 struct/castle/castl- (12) | 12 | 12 | Structures |
| 83 | [`island_hut_round`](#f83-island-hut-round) | Koka Isle round hut (island_village, 208x178 px) · sheet_struct.png | 424 struct/island/isle- (12) | 12 | 12 | Structures |
| 84 | [`rubble_pile`](#f84-rubble-pile) | Rubble pile (dungeon_stone_kit, 86x33 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (12) | 12 | 12 | Props |
| 85 | [`shelf_bottles`](#f85-shelf-bottles) | Shelf of bottles (shop wall) (house_interior, 154x116 px) · sheet_inside.png | 64 inside/details/inacc- (12) | 12 | 12 | Props |
| 86 | [`shelf_empty`](#f86-shelf-empty) | Wooden shelving (house_interior, 118x103 px) · sheet_inside.png | 459 inner/shelf- (12) | 12 | 12 | Props |
| 87 | [`crate_stack`](#f87-crate-stack) | Stack of crates (crates, 63x70 px) · sheet_items.png | 445 items/boxes/box- (11) | 11 | 11 | Props |
| 88 | [`potion_purple`](#f88-potion-purple) | Purple potion (potions, 19x52 px) · sheet_items.png | 57 bonuses/bottles/botl-p (11) | 11 | 11 | Props |
| 89 | [`slime_green`](#f89-slime-green) | Slime (green) (slime, 26x23 px) · sheet_foes.png | 671 foes/puddle/green/walk/f06w1- (11) | 11 | 11 | Creatures |
| 90 | [`cave_hole_warp`](#f90-cave-hole-warp) | Hole into a cave (warp) (ground_holes, 55x31 px) · sheet_lands.png | 89 lands/details/crack- (10) | 10 | 10 | - |
| 91 | [`fallen_log`](#f91-fallen-log) | Fallen log (forest_floor, 88x47 px) · sheet_lands.png | 91 lands/details/fores- (10) | 10 | 10 | Vegetation |
| 92 | [`island_totem_pole`](#f92-island-totem-pole) | Pole with skull/feather totem (island_village, 27x105 px) · sheet_struct.png | 424 struct/island/isle- (10) | 10 | 10 | Structures |
| 93 | [`save_machine`](#f93-save-machine) | Save machine (save_machine, 120x85 px) · sheet_inter.png | 449 inter/save/save- (10) | 10 | 10 | - |
| 94 | [`stool`](#f94-stool) | Stool (house_interior, 30x29 px) · sheet_inside.png | 461 inner/chair- (10) | 10 | 10 | Props |
| 95 | [`bonca_purple`](#f95-bonca-purple) | Bonca (purple) (bonca, 85x94 px) · sheet_foes.png | 613 foes/bonca/purple/walk/f03w3- (6), 619 foes/bonca/purple/walk/f03w9- (1), 628 foes/bonca/purple/attack/f03a4- (1), 626 foes/bonca/purple/attack/f03a8- (1) | 9 | 9 | - |
| 96 | [`bookcase`](#f96-bookcase) | Bookcase (house_interior, 135x120 px) · sheet_inside.png | 64 inside/details/inacc- (9) | 9 | 9 | - |
| 97 | [`fire_fx`](#f97-fire-fx) | Fire (looping flames) (fire, 78x78 px) · sheet_effects.png | 427 effects/fire/fire1- (9) | 9 | 9 | Props |
| 98 | [`log_cabin_window`](#f98-log-cabin-window) | Log cabin window (log_cabin, 24x28 px) · sheet_struct.png | 59 struct/cabin/cabin- (9) | 9 | 9 | - |
| 99 | [`potion_blue`](#f99-potion-blue) | Blue potion (strength/defense) (potions, 19x52 px) · sheet_items.png | 55 bonuses/bottles/botl-b (8), 75 bonuses/bottles/botl-b (1) | 9 | 9 | Props |
| 100 | [`stairs_wood`](#f100-stairs-wood) | Wooden stairs (stairs, 82x72 px) · sheet_inside.png | 428 inside/stairs/stair- (9) | 9 | 9 | - |
| 101 | [`table_round`](#f101-table-round) | Round table (house_interior, 65x62 px) · sheet_inside.png | 87 inside/details/table- (9) | 9 | 9 | Props |
| 102 | [`tree_dead_dark_tall`](#f102-tree-dead-dark-tall) | Dead leafless tree (tall) (trees, 185x323 px) · sheet_lands.png | 32 lands/trees/tree- (9) | 9 | 9 | Vegetation |
| 103 | [`twig`](#f103-twig) | Fallen twig (forest_floor, 35x27 px) · sheet_lands.png | 91 lands/details/fores- (9) | 9 | 9 | Vegetation |
| 104 | [`bench_short`](#f104-bench-short) | Bench (house_interior, 76x56 px) · sheet_inside.png | 87 inside/details/table- (8) | 8 | 8 | Props |
| 105 | [`dungeon_wall_stone_ivy`](#f105-dungeon-wall-stone-ivy) | Dungeon wall overgrown with ivy (dungeon_stone_kit, 100x118 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (8) | 8 | 8 | WallKits |
| 106 | [`fish`](#f106-fish) | Fish (swimming) (fish, 72x52 px) · sheet_foes.png | 434 animals/fish/fish1/fish1- (8) | 8 | 8 | - |
| 107 | [`gold_coin`](#f107-gold-coin) | Single coin (gold, 4x3 px) · sheet_items.png | 178 bonuses/coins/coin- (8) | 8 | 8 | - |
| 108 | [`ground_crack`](#f108-ground-crack) | Crack in the ground (ground_holes, 88x33 px) · sheet_lands.png | 89 lands/details/crack- (8) | 8 | 8 | - |
| 109 | [`island_torch`](#f109-island-torch) | Bamboo torch / pole (island_village, 85x105 px) · sheet_struct.png | 425 struct/island/torch- (8) | 8 | 8 | Props |
| 110 | [`pig`](#f110-pig) | Pig (pig, 50x56 px) · sheet_foes.png | 41 animals/pig/pg-w1- (5), 43 animals/pig/pg-w3- (2), 49 animals/pig/pg-w9- (1) | 8 | 8 | Creatures |
| 111 | [`shop_sign`](#f111-shop-sign) | Hanging sign (red cross: healer) (signs, 63x76 px) · sheet_inside.png | 458 inside/details/sign- (8) | 8 | 8 | - |
| 112 | [`small_heart`](#f112-small-heart) | Small heart (hearts, 17x17 px) · sheet_items.png | 54 bonuses/heart/smhrt (8) | 8 | 8 | - |
| 113 | [`bridge_wood_rail_plank`](#f113-bridge-wood-rail-plank) | Bridge side rail with planking (bridge_wood, 101x84 px) · sheet_struct.png | 58 struct/bridge/brdge- (7) | 7 | 7 | Structures |
| 114 | [`bridge_wood_rail_rope`](#f114-bridge-wood-rail-rope) | Bridge rope rail (bridge_wood, 101x93 px) · sheet_struct.png | 58 struct/bridge/brdge- (7) | 7 | 7 | Structures |
| 115 | [`cottage_thatched_two_storey`](#f115-cottage-thatched-two-storey) | Two-storey thatched cottage (cottage_thatched, 257x311 px) · sheet_struct.png | 63 struct<HOME> (7) | 7 | 7 | Structures |
| 116 | [`flower_bed_row`](#f116-flower-bed-row) | Planted bed / hedge row (dark) (garden, 217x120 px) · sheet_lands.png | 66 lands/garden/gardn- (7) | 7 | 7 | Vegetation |
| 117 | [`snake_pillar`](#f117-snake-pillar) | Pillar with coiled snake (snake_pillar, 20x72 px) · sheet_inside.png | 82 inside/stnwalls/snake/snakc- (7) | 7 | 7 | - |
| 118 | [`wall_stripe_red`](#f118-wall-stripe-red) | Red wall stripe / banner (built from the health-bar UI art) (signs, 24x17 px) · sheet_inter.png | 450 inter/health/hm-br- (7) | 7 | 7 | - |
| 119 | [`bench_long`](#f119-bench-long) | Long bench (house_interior, 94x24 px) · sheet_inside.png | 87 inside/details/table- (6) | 6 | 6 | Props |
| 120 | [`cottage_thatched_l_shape`](#f120-cottage-thatched-l-shape) | L-shaped thatched cottage (cottage_thatched, 305x324 px) · sheet_struct.png | 63 struct<HOME> (6) | 6 | 6 | Structures |
| 121 | [`dungeon_wall_stone_cracked`](#f121-dungeon-wall-stone-cracked) | Cracked / broken dungeon wall (dungeon_stone_kit, 100x103 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (6) | 6 | 6 | WallKits |
| 122 | [`fence_rail_diag_ne`](#f122-fence-rail-diag-ne) | Rail fence diagonal (fence_rail, 69x90 px) · sheet_lands.png | 93 lands/fence/fence- (6) | 6 | 6 | Structures |
| 123 | [`goblin_soldier`](#f123-goblin-soldier) | Goblin soldier (goblin, 107x130 px) · sheet_foes.png | 809 foes/goblin/soldier/walk/f01w9- (3), 801 foes/goblin/soldier/walk/f01w1- (2), 803 foes/goblin/soldier/walk/f01w3- (1) | 6 | 6 | - |
| 124 | [`golden_heart`](#f124-golden-heart) | Golden heart (max life up) (hearts, 33x33 px) · sheet_items.png | 53 bonuses/heart/gldhrt (6) | 6 | 6 | - |
| 125 | [`pitchfork`](#f125-pitchfork) | Pitchfork (leaning) (tools, 28x108 px) · sheet_items.png | 447 items/tools/tool- (6) | 6 | 6 | - |
| 126 | [`small_fire_fx`](#f126-small-fire-fx) | Small fire on floor (fire, 23x20 px) · sheet_struct.png | 155 struct/details/damage/fire2- (2), 156 struct/details/damage/fire3- (2), 157 struct/details/damage/fire4- (2) | 6 | 6 | Props |
| 127 | [`ground_hole_dark`](#f127-ground-hole-dark) | Dark hole in the ground (ground_holes, 55x73 px) · sheet_lands.png | 89 lands/details/crack- (5) | 10 | 5 | - |
| 128 | [`chimney_stone`](#f128-chimney-stone) | Stone chimney (cottage_thatched, 55x58 px) · sheet_struct.png | 63 struct<HOME> (5) | 5 | 5 | Structures |
| 129 | [`idol_statue_small`](#f129-idol-statue-small) | Small demon idol (dungeon_stone_kit, 44x50 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (5) | 5 | 5 | - |
| 130 | [`island_spear_pole`](#f130-island-spear-pole) | Spear pole (island_village, 26x98 px) · sheet_struct.png | 424 struct/island/isle- (5) | 5 | 5 | - |
| 131 | [`thorn_branch`](#f131-thorn-branch) | Thorn branch (graveyard, 28x25 px) · sheet_lands.png | 90 lands/details/grave- (5) | 5 | 5 | Vegetation |
| 132 | [`weed_sprig`](#f132-weed-sprig) | Small weed sprig (ground_plants, 22x24 px) · sheet_lands.png | 65 lands/grass/grass- (5) | 5 | 5 | Vegetation |
| 133 | [`well_stone`](#f133-well-stone) | Stone well with roof (landmarks, 107x136 px) · sheet_struct.png | 186 struct/landmark/landm- (5) | 5 | 5 | Structures |
| 134 | [`tree_pine_large`](#f134-tree-pine-large) | Pine tree (trees, 128x188 px) · sheet_lands.png | 32 lands/trees/tree- (4) | 7 | 4 | Vegetation |
| 135 | [`npc_knight_silver`](#f135-npc-knight-silver) | Knight (silver) (npc_knight, 110x117 px) · sheet_people.png | 293 people/knight/silver/c5-w3- (2), 299 people/knight/silver/c5-w9- (1), 291 people/knight/silver/c5-w1- (1) | 6 | 4 | - |
| 136 | [`boulder_flat`](#f136-boulder-flat) | Flat boulder (boulders, 72x63 px) · sheet_lands.png | 95 lands/rocks/rock- (4) | 4 | 4 | - |
| 137 | [`bridge_stone`](#f137-bridge-stone) | Stone arch bridge (bridge_stone, 288x212 px) · sheet_struct.png | 186 struct/landmark/landm- (4) | 4 | 4 | Structures |
| 138 | [`cabbage`](#f138-cabbage) | Cabbage (garden crop) (food, 54x46 px) · sheet_items.png | 421 items/food/food- (4) | 4 | 4 | Vegetation |
| 139 | [`cottage_thatched_long`](#f139-cottage-thatched-long) | Thatched stone cottage (cottage_thatched, 332x260 px) · sheet_struct.png | 63 struct<HOME> (4) | 4 | 4 | Structures |
| 140 | [`fish_flopping`](#f140-fish-flopping) | Fish flopping on land (fish, 33x34 px) · sheet_foes.png | 439 animals/fish/flop/fishx- (3), 441 animals/fish/flop/flop2- (1) | 4 | 4 | - |
| 141 | [`goblin_hammer`](#f141-goblin-hammer) | Goblin (hammer) (goblin, 56x109 px) · sheet_foes.png | 763 foes/goblin/hammer/walk/f01w3- (2), 761 foes/goblin/hammer/walk/f01w1- (1), 769 foes/goblin/hammer/walk/f01w9- (1) | 4 | 4 | - |
| 142 | [`island_hut_two_storey`](#f142-island-hut-two-storey) | Two-tier round hut (island_village, 238x265 px) · sheet_struct.png | 424 struct/island/isle- (4) | 4 | 4 | Structures |
| 143 | [`npc_girl`](#f143-npc-girl) | Girl (child) (npc_girl, 53x62 px) · sheet_people.png | 331 people/girl/c03w1- (3), 339 people/girl/c03w9- (1) | 4 | 4 | - |
| 144 | [`npc_knight_red`](#f144-npc-knight-red) | Knight (red) (npc_knight, 91x125 px) · sheet_people.png | 273 people/knight/red/c5-w3- (2), 279 people/knight/red/c5-w9- (1), 277 people/knight/red/c5-w7- (1) | 4 | 4 | - |
| 145 | [`poster_hark`](#f145-poster-hark) | "Hark!" notice (signs, 43x61 px) · sheet_inside.png | 462 inner/poster (4) | 4 | 4 | - |
| 146 | [`teleport_shrine`](#f146-teleport-shrine) | Shrine with stained glass (teleporter) (monuments, 148x155 px) · sheet_struct.png | 159 struct/stone/mdink/monum- (3) | 6 | 3 | - |
| 147 | [`bomb_item`](#f147-bomb-item) | Bomb (items, 26x33 px) · sheet_items.png | 420 items/bomb/bomb- (3) | 3 | 3 | - |
| 148 | [`church`](#f148-church) | Stone church (church, 417x433 px) · sheet_struct.png | 60 struct/church/chrch- (3) | 3 | 3 | - |
| 149 | [`church_stained_glass`](#f149-church-stained-glass) | Stained-glass window (church, 56x94 px) · sheet_struct.png | 60 struct/church/chrch- (3) | 3 | 3 | - |
| 150 | [`dragon_corpse`](#f150-dragon-corpse) | Dead dragon (dragon, 105x122 px) · sheet_foes.png | 212 foes/dragon/f2-x3- (2), 216 foes/dragon/f2-x7- (1) | 3 | 3 | - |
| 151 | [`fallen_branch_forked`](#f151-fallen-branch-forked) | Fallen forked branch (forest_floor, 84x81 px) · sheet_lands.png | 91 lands/details/fores- (3) | 3 | 3 | Vegetation |
| 152 | [`fireplace_brick`](#f152-fireplace-brick) | Brick fireplace (house_interior, 97x114 px) · sheet_inside.png | 64 inside/details/inacc- (3) | 3 | 3 | Props |
| 153 | [`pillbug_corpse`](#f153-pillbug-corpse) | Pillbug death splat (pillbug, 46x35 px) · sheet_foes.png | 141 foes/pill/f1-x1- (2), 143 foes/pill/f1-x3- (1) | 3 | 3 | Creatures |
| 154 | [`rake`](#f154-rake) | Rake (leaning) (tools, 48x95 px) · sheet_items.png | 447 items/tools/tool- (3) | 3 | 3 | - |
| 155 | [`teleport_machine`](#f155-teleport-machine) | Teleport machine (armillary sphere) (monuments, 89x170 px) · sheet_struct.png | 84 struct/teleport/telep- (2) | 3 | 2 | - |
| 156 | [`boulder_large`](#f156-boulder-large) | Large dark boulder (boulders, 103x95 px) · sheet_lands.png | 95 lands/rocks/rock- (2) | 2 | 2 | - |
| 157 | [`boulder_red`](#f157-boulder-red) | Reddish boulder (boulders, 100x79 px) · sheet_lands.png | 95 lands/rocks/rock- (2) | 2 | 2 | - |
| 158 | [`boulder_white_pair`](#f158-boulder-white-pair) | Pair of white boulders (boulders, 80x58 px) · sheet_lands.png | 95 lands/rocks/rock- (2) | 2 | 2 | - |
| 159 | [`burnt_floor_hole`](#f159-burnt-floor-hole) | Burnt hole in floor/roof (large) (damage, 90x69 px) · sheet_struct.png | 158 struct/details/damage/hole- (2) | 2 | 2 | - |
| 160 | [`castle_wall_end`](#f160-castle-wall-end) | Castle wall end (edge-on) (castle_kit, 100x340 px) · sheet_struct.png | 67 struct/castle/castl- (2) | 2 | 2 | Structures |
| 161 | [`cellar_hatch`](#f161-cellar-hatch) | Cellar hatch / ladder (stairs, 35x57 px) · sheet_inside.png | 428 inside/stairs/stair- (2) | 2 | 2 | - |
| 162 | [`chest_large`](#f162-chest-large) | Treasure chest (large) (chests, 60x60 px) · sheet_items.png | 177 bonuses/chest/chst3- (2) | 2 | 2 | Props |
| 163 | [`chest_medium`](#f163-chest-medium) | Treasure chest (chests, 44x55 px) · sheet_items.png | 176 bonuses/chest/chst2- (2) | 2 | 2 | Props |
| 164 | [`church_window_small`](#f164-church-window-small) | Church small window (church, 19x27 px) · sheet_struct.png | 60 struct/church/chrch- (2) | 2 | 2 | - |
| 165 | [`corpse_merchant`](#f165-corpse-merchant) | Dead merchant (npc_merchant, 74x53 px) · sheet_people.png | 385 people/merchant/green/death- (1), 345 people/merchant/death- (1) | 2 | 2 | - |
| 166 | [`duck_corpse`](#f166-duck-corpse) | Dead duck body (duck, 20x30 px) · sheet_foes.png | 127 animals/duck/death/dkh7x- (1), 121 animals/duck/death/dkh1x- (1) | 2 | 2 | Creatures |
| 167 | [`dungeon_wall_stone_arch`](#f167-dungeon-wall-stone-arch) | Dungeon wall with archway (dungeon_stone_kit, 100x129 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (2) | 2 | 2 | WallKits |
| 168 | [`explosion_fx`](#f168-explosion-fx) | Explosion (, 60x61 px) · sheet_effects.png | 70 effects/splode/explo- (2) | 2 | 2 | - |
| 169 | [`fire_burst_fx`](#f169-fire-burst-fx) | Fire burst (atomic explosion frames) (, 93x141 px) · sheet_effects.png | 161 effects/atomic/atomc- (2) | 2 | 2 | - |
| 170 | [`fireball_fx`](#f170-fireball-fx) | Fireball (vertical) (, 32x76 px) · sheet_effects.png | 512 effects/comets/sm-comt2/fbal2- (2) | 2 | 2 | - |
| 171 | [`food_drumstick`](#f171-food-drumstick) | Meat drumstick (food, 28x31 px) · sheet_items.png | 421 items/food/food- (2) | 2 | 2 | - |
| 172 | [`food_pie`](#f172-food-pie) | Pie (food, 24x19 px) · sheet_items.png | 421 items/food/food- (2) | 2 | 2 | Props |
| 173 | [`fountain_spray_fx`](#f173-fountain-spray-fx) | Fountain water spray (fountain, 80x84 px) · sheet_lands.png | 94 lands/garden/spray- (2) | 2 | 2 | - |
| 174 | [`fountain_stone`](#f174-fountain-stone) | Stone fountain (fountain, 102x98 px) · sheet_lands.png | 66 lands/garden/gardn- (2) | 2 | 2 | - |
| 175 | [`hearth_fire`](#f175-hearth-fire) | Fireplace fire (house_interior, 46x55 px) · sheet_inside.png | 86 inside/details/fire- (2) | 2 | 2 | - |
| 176 | [`log_cabin`](#f176-log-cabin) | Log cabin (log_cabin, 322x232 px) · sheet_struct.png | 59 struct/cabin/cabin- (2) | 2 | 2 | - |
| 177 | [`log_cabin_door`](#f177-log-cabin-door) | Log cabin door (log_cabin, 34x69 px) · sheet_struct.png | 59 struct/cabin/cabin- (2) | 2 | 2 | - |
| 178 | [`npc_knight_red_attacking`](#f178-npc-knight-red-attacking) | Knight (red) attack pose (npc_knight, 121x127 px) · sheet_people.png | 712 people/knight/red/attack/c05a2- (2) | 2 | 2 | - |
| 179 | [`npc_merchant_blue`](#f179-npc-merchant-blue) | Merchant (blue) (npc_merchant, 55x93 px) · sheet_people.png | 371 people/merchant/blue/c09w1- (2) | 2 | 2 | - |
| 180 | [`npc_merchant_green`](#f180-npc-merchant-green) | Merchant (green) (npc_merchant, 55x93 px) · sheet_people.png | 381 people/merchant/green/c09w1- (2) | 2 | 2 | - |
| 181 | [`npc_peasant`](#f181-npc-peasant) | Peasant (npc_peasant, 73x121 px) · sheet_people.png | 411 people/peasant2/c11w1- (2) | 2 | 2 | - |
| 182 | [`scythe`](#f182-scythe) | Scythe / hook (tools, 42x78 px) · sheet_items.png | 447 items/tools/tool- (2) | 2 | 2 | - |
| 183 | [`sparkle_fx`](#f183-sparkle-fx) | Sparkle (, 20x20 px) · sheet_effects.png | 165 effects/shiny/shiny- (1), 166 effects/sparks/spark- (1) | 2 | 2 | - |
| 184 | [`spinning_wheel`](#f184-spinning-wheel) | Spinning wheel (tools, 61x87 px) · sheet_items.png | 447 items/tools/tool- (2) | 2 | 2 | - |
| 185 | [`tree_willow`](#f185-tree-willow) | Weeping (willow-like) tree (trees, 169x252 px) · sheet_lands.png | 32 lands/trees/tree- (2) | 2 | 2 | Vegetation |
| 186 | [`tree_willow_large`](#f186-tree-willow-large) | Large weeping tree (trees, 249x300 px) · sheet_lands.png | 32 lands/trees/tree- (2) | 2 | 2 | Vegetation |
| 187 | [`weed_small`](#f187-weed-small) | Small weed / seedling (ground_plants, 20x22 px) · sheet_lands.png | 65 lands/grass/grass- (2) | 2 | 2 | Vegetation |
| 188 | [`axe_item`](#f188-axe-item) | Throwing axe (on ground) (items, 49x31 px) · sheet_effects.png | 85 effects/axe/wpn02- (1) | 1 | 1 | - |
| 189 | [`ballista`](#f189-ballista) | Ballista (siege, 168x143 px) · sheet_struct.png | 429 struct/cataplt/arms- (1) | 1 | 1 | - |
| 190 | [`barrel_broken`](#f190-barrel-broken) | Smashed barrel (barrels, 84x64 px) · sheet_items.png | 173 bonuses/barrels/barel- (1) | 1 | 1 | - |
| 191 | [`boulder_grey_tall`](#f191-boulder-grey-tall) | Tall grey boulder (boulders, 54x77 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 192 | [`burn_damage_decal`](#f192-burn-damage-decal) | Burn damage / scorch with fire (damage, 90x69 px) · sheet_struct.png | 154 struct/details/damage/damag- (1) | 1 | 1 | - |
| 193 | [`cabinet_narrow`](#f193-cabinet-narrow) | Narrow cabinet (side view) (house_interior, 14x67 px) · sheet_inside.png | 87 inside/details/table- (1) | 1 | 1 | Props |
| 194 | [`castle_door`](#f194-castle-door) | Castle door (castle_kit, 63x145 px) · sheet_struct.png | 68 struct/castle/cdoor- (1) | 1 | 1 | - |
| 195 | [`castle_drawbridge`](#f195-castle-drawbridge) | Drawbridge with chains (castle_kit, 149x192 px) · sheet_struct.png | 68 struct/castle/cdoor- (1) | 1 | 1 | - |
| 196 | [`castle_gatehouse`](#f196-castle-gatehouse) | Castle gatehouse block (castle_kit, 335x389 px) · sheet_struct.png | 67 struct/castle/castl- (1) | 1 | 1 | Structures |
| 197 | [`catapult`](#f197-catapult) | Catapult (siege, 261x268 px) · sheet_struct.png | 429 struct/cataplt/arms- (1) | 1 | 1 | - |
| 198 | [`church_door`](#f198-church-door) | Church door (church, 35x82 px) · sheet_struct.png | 60 struct/church/chrch- (1) | 1 | 1 | - |
| 199 | [`corpse_girl`](#f199-corpse-girl) | Dead girl (npc_girl, 58x37 px) · sheet_people.png | 335 people/girl/death- (1) | 1 | 1 | - |
| 200 | [`corpse_knight`](#f200-corpse-knight) | Dead knight (npc_knight, 81x55 px) · sheet_people.png | 275 people/knight/red/death- (1) | 1 | 1 | - |
| 201 | [`corpse_maiden`](#f201-corpse-maiden) | Dead woman (npc_maiden, 63x47 px) · sheet_people.png | 245 people/maiden/red/death- (1) | 1 | 1 | - |
| 202 | [`corpse_mom`](#f202-corpse-mom) | Dead mother (burnt house) (npc_mom, 68x50 px) · sheet_people.png | 355 people/mom/death- (1) | 1 | 1 | - |
| 203 | [`corpse_peasant`](#f203-corpse-peasant) | Dead peasant (npc_peasant, 114x59 px) · sheet_people.png | 415 people/peasant2/death- (1) | 1 | 1 | - |
| 204 | [`corpse_soldier`](#f204-corpse-soldier) | Dead soldier (npc_soldier, 74x57 px) · sheet_people.png | 405 people/soldier/death- (1) | 1 | 1 | - |
| 205 | [`dink_dead`](#f205-dink-dead) | Dink lying dead (cutscene pose) (dink, 104x90 px) · sheet_dink.png | 436 dink/die/ds-x3- (1) | 1 | 1 | - |
| 206 | [`dink_monument_rock`](#f206-dink-monument-rock) | "Dink Smallwood" carved rock (monuments, 189x188 px) · sheet_struct.png | 159 struct/stone/mdink/monum- (1) | 1 | 1 | - |
| 207 | [`dungeon_arch_freestanding`](#f207-dungeon-arch-freestanding) | Freestanding stone archway (dungeon_stone_kit, 84x142 px) · sheet_inside.png | 80 inside/stnwalls/stonw- (1) | 1 | 1 | - |
| 208 | [`food_bread`](#f208-food-bread) | Bread loaf (food, 30x25 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 209 | [`food_cheese`](#f209-food-cheese) | Cheese (food, 21x19 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 210 | [`food_grapes`](#f210-food-grapes) | Grapes (food, 29x30 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 211 | [`food_ham`](#f211-food-ham) | Ham / steak (food, 28x28 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 212 | [`gold_coins_small`](#f212-gold-coins-small) | Few coins (gold, 28x10 px) · sheet_items.png | 178 bonuses/coins/coin- (1) | 1 | 1 | - |
| 213 | [`golden_duck_statue`](#f213-golden-duck-statue) | Golden duck statue (monuments, 103x155 px) · sheet_struct.png | 159 struct/stone/mdink/monum- (1) | 1 | 1 | - |
| 214 | [`heart_pickup`](#f214-heart-pickup) | Heart (health) (hearts, 33x33 px) · sheet_items.png | 52 bonuses/heart/heart (1) | 1 | 1 | - |
| 215 | [`king_on_throne`](#f215-king-on-throne) | King Daniel on throne (seated) (npc_king, 124x119 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 216 | [`npc_gnome_purple`](#f216-npc-gnome-purple) | Gnome / wizard (purple) (npc_gnome, 51x74 px) · sheet_people.png | 561 people/gnome/purple/c13w1- (1) | 1 | 1 | - |
| 217 | [`npc_maiden_blue`](#f217-npc-maiden-blue) | Woman (blue dress) (npc_maiden, 55x83 px) · sheet_people.png | 251 people/maiden/blue/c7-w1- (1) | 1 | 1 | - |
| 218 | [`npc_maiden_brown`](#f218-npc-maiden-brown) | Woman (brown dress) (npc_maiden, 55x83 px) · sheet_people.png | 241 people/maiden/brown/c6-w1- (1) | 1 | 1 | - |
| 219 | [`npc_maiden_red`](#f219-npc-maiden-red) | Woman (red dress) (npc_maiden, 55x83 px) · sheet_people.png | 221 people/maiden/red/c4-w1- (1) | 1 | 1 | - |
| 220 | [`npc_old_man`](#f220-npc-old-man) | Old man (npc_oldman, 67x74 px) · sheet_people.png | 231 people/oldman/c1-w1- (1) | 1 | 1 | - |
| 221 | [`npc_soldier`](#f221-npc-soldier) | Soldier (npc_soldier, 76x93 px) · sheet_people.png | 403 people/soldier/c10w3- (1) | 1 | 1 | - |
| 222 | [`ore_rock_blue`](#f222-ore-rock-blue) | Blue crystal rock (boulders, 44x29 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 223 | [`poster_wanted`](#f223-poster-wanted) | "Wanted" poster (signs, 43x61 px) · sheet_inside.png | 462 inner/poster (1) | 1 | 1 | - |
| 224 | [`scroll_note`](#f224-scroll-note) | Note / paper on floor (, 34x25 px) · sheet_items.png | 422 items/paper/paper- (1) | 1 | 1 | - |
| 225 | [`snake_carving`](#f225-snake-carving) | Small stone snake carving (snake_pillar, 15x13 px) · sheet_inside.png | 81 inside/stnwalls/snake/snakb- (1) | 1 | 1 | - |
| 226 | [`snow_house_door`](#f226-snow-house-door) | House door (snow_house, 43x78 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 227 | [`snow_house_lower`](#f227-snow-house-lower) | House lower walls (snow_house, 381x188 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 228 | [`snow_house_roof`](#f228-snow-house-roof) | House pyramid roof (snow_house, 404x201 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 229 | [`snow_house_timber`](#f229-snow-house-timber) | House timbered upper walls (snow_house, 400x179 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 230 | [`tree_oak_large`](#f230-tree-oak-large) | Broadleaf (oak) tree (trees, 204x270 px) · sheet_lands.png | 32 lands/trees/tree- (1) | 1 | 1 | Vegetation |
| 231 | [`screen ground (tile layer)`](#f231-screen-ground-tile-layer) | tile-layer ground of each screen (grass, sand, water, walls painted into tilesets) · sheet_tiles.png | - | 639 | 0 | Terrain |

## Open origin IDs

Placements as `Snnn: Pnn ...` (screen, then slot), screens as `SCR nnn ...`, script warps by full ID.

<a id="f1-beach-pebbles"></a>
**1. `beach_pebbles`** (281 IDs)  
S257: P10 P11 P12 P13 · S320: P05 P16 · S351: P02 P04 P05 P06 P07 P08 · S352: P01 P02 P03 P04 P05 P07 P08 P09 P10 P11 · S385: P05 · S388: P01 P02 · S417: P09 · S420: P01 P02 P03 P04 · S449: P09 P10 · S452: P01 P04 P05 P07 · S481: P01 P03 P04 P08 · S482: P01 P03 P04 · S483: P05 P06 P07 P08 P09 P10 · S484: P01 P03 P05 P06 P07 · S487: P01 P02 P03 · S488: P06 P07 P08 P09 · S518: P08 · S519: P04 P05 · S520: P01 P05 · S550: P03 P04 P05 · S551: P05 P09 · S582: P04 P05 P06 P07 P08 · S583: P01 P02 P04 P05 P06 P07 · S614: P01 P02 P03 P04 P05 P06 P09 · S615: P01 P05 P06 P07 · S646: P03 P04 P05 P07 · S647: P05 P06 P07 · S678: P01 P02 P03 P04 P05 P06 P09 · S679: P02 · S688: P04 · S699: P04 P05 P06 P07 P08 · S701: P03 P04 P05 P06 P07 P08 P09 P12 · S710: P01 P02 P07 P08 P09 P10 P11 P12 P13 · S711: P01 P04 P05 P06 · S720: P02 · S725: P06 · S727: P03 P06 P07 P08 P09 P10 P11 P12 P13 P14 P16 · S728: P07 P15 P16 P17 · S729: P02 P03 P04 P05 P06 P07 P08 · S730: P01 P02 · S731: P06 P07 P08 P09 · S732: P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 · S733: P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 · S734: P20 P21 P22 P23 P24 P25 P26 P27 P28 P29 · S742: P01 P03 P04 P07 · S743: P04 P05 P06 P07 P08 · S759: P01 P04 P05 · S760: P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 · S761: P01 P02 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 · S762: P14 P15 P16 P19 P20 P21 P22 P23 P24 P25 P26 P27 P28 · S763: P09 P10 P11 P12 P13 P14 P15 P16 P17 · S764: P06 P08 P23 P34 P35 P37 · S765: P06 P10 P11 P18 P20 P29 P30 P31 P34

<a id="f2-pebbles"></a>
**2. `pebbles`** (214 IDs)  
S005: P23 P24 · S066: P25 P26 P27 P28 · S105: P17 P18 · S132: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 · S154: P24 P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 P35 P36 P37 P38 · S164: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 · S165: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 · S166: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 · S170: P09 P10 P11 P12 · S193: P19 P20 P21 P22 · S198: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 · S244: P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 P24 P25 P26 P27 P28 P29 P30 P31 P32 P33 P36 · S261: P24 P31 · S350: P06 P07 · S441: P25 P26 · S469: P12 · S534: P04 P07 P08 P09 · S535: P13 P14 P15 P16 P17 · S537: P07 P08 P09 · S553: P09 P10 P11 P12 · S554: P08 P09 P10 P11 P12 P13 P14 · S555: P06 P07 P08 P09 · S566: P05 P06 P10 P11 P12 P13 P14 P15 · S567: P05 P06 P07 P08 P09 P10 · S585: P06 P07 P08 P09 P10 P11 P12 · S586: P05 P06 P07 P08 P09 P10 P11 · S587: P07 P08 P09 P10 P11 · S617: P02 P03 P04 P05 P06 P07 P08 · S618: P06 P07 P08 · S619: P04 P05 P06 · S671: P66 · S734: P19

<a id="f3-int-wall-plaster-side"></a>
**3. `int_wall_plaster_side`** (188 IDs)  
S002: P07 P08 P09 P10 P14 P15 · S003: P03 P08 P09 P10 P11 P13 P24 P25 P27 · S004: P07 P08 P09 P10 P14 P15 · S005: P08 P09 P10 P11 P12 P13 · S006: P02 P03 P09 P10 P11 P14 · S033: P08 P09 P10 P11 P12 P13 · S034: P08 P09 P10 P11 P12 P19 P23 P24 · S035: P08 P09 P10 P11 P12 P13 · S036: P01 P02 P03 P09 P10 P11 P19 P20 P21 · S037: P07 P08 P09 P10 P14 P15 · S038: P07 P08 P09 P10 P12 P14 · S065: P07 P08 P09 P10 P12 P14 · S066: P07 P08 P09 P10 P12 P14 · S067: P05 P06 P19 P21 P24 P25 · S068: P04 P08 P12 · S097: P06 P07 P08 P09 P10 P11 · S129: P05 P06 P07 P08 P09 P11 · S130: P04 P10 P11 P12 P14 P22 · S161: P10 P11 P12 P13 P14 P15 · S162: P10 P11 P12 P13 P14 P15 · S163: P05 P06 P07 P08 P09 P11 · S193: P02 P09 P10 P12 P15 · S194: P10 P11 P12 P13 P14 P15 · S195: P08 P09 P10 P11 P12 P13 · S196: P10 P11 P12 P13 P14 P15 · S225: P08 P09 P10 P11 P12 P13 · S226: P08 P09 P10 P11 P12 P13 · S228: P10 P11 P12 P13 P14 P15 · S261: P10 P11 P12 P13 P14 P15 · S289: P10 P13 P14 P15 · S290: P10 P11 P12 P13 P14 P15

<a id="f4-int-wall-plaster"></a>
**4. `int_wall_plaster`** (174 IDs)  
S002: P05 P06 · S003: P04 P05 P06 P17 P18 P20 P21 · S004: P05 P06 P11 P12 · S005: P05 P06 P15 P16 · S006: P05 P07 P13 P15 · S033: P05 P06 P15 P16 · S034: P05 P06 P13 P15 P17 P18 P20 P22 · S035: P05 P06 P15 P16 · S036: P05 P06 P07 P14 P15 · S037: P05 P06 P11 P12 · S038: P05 P06 P11 P18 · S065: P05 P06 P11 P13 · S066: P05 P06 P11 P13 · S067: P01 P03 P09 P10 P12 P13 P14 P18 P22 P23 · S068: P02 P05 P06 P10 P13 P14 P19 · S097: P03 P04 P05 P14 P18 P19 P20 · S129: P01 P03 P13 P14 P18 P19 · S130: P01 P03 P05 P06 P08 P13 P18 · S161: P01 P02 P03 P04 P05 P07 P08 · S162: P01 P02 P03 P04 P05 P07 P08 · S163: P01 P03 P13 P14 P18 P19 · S193: P04 P05 P06 P07 P16 P17 · S194: P01 P02 P03 P04 P07 P08 · S195: P05 P06 P15 P16 · S196: P01 P02 P03 P04 P05 P07 P08 · S225: P05 P06 P15 P16 · S226: P05 P06 P15 P16 · S228: P01 P02 P03 P04 P05 P07 P08 · S261: P01 P02 P03 P04 P05 P07 P08 · S289: P01 P02 P03 P05 P07 P08 P18 · S290: P01 P02 P03 P04 P05 P07 P08

<a id="f5-pillbug"></a>
**5. `pillbug`** (154 IDs)  
S026: P07 · S027: P06 P08 · S030: P03 P04 P05 P06 P07 P08 P09 · S064: P08 · S106: P16 P17 · S191: P08 · S223: P07 P08 P09 P10 P11 P12 · S237: P08 P09 · S270: P05 P06 · S274: P18 · S278: P04 P05 · S279: P05 · S301: P05 P06 · S303: P06 · S306: P07 P08 · S309: P06 · S310: P05 · S311: P03 P04 · S334: P07 P11 P12 · S373: P03 P04 · S378: P07 P08 P09 · S395: P04 · S435: P02 · S437: P16 P17 P18 P19 P20 · S457: P04 P05 P06 · S474: P14 · S487: P07 · S488: P10 P11 · S519: P07 · S522: P03 P06 · S526: P04 P05 P06 P07 P08 · S527: P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 · S528: P04 P05 P06 · S550: P08 · S551: P01 P02 P03 · S552: P01 P02 P03 · S563: P03 P04 P05 P06 P07 P08 P09 P10 P11 · S584: P02 P03 · S599: P14 P15 P16 P18 · S608: P01 P02 P03 P04 P05 · S616: P04 P05 P06 · S621: P04 P05 P06 P07 · S624: P02 P06 · S626: P04 P05 P06 P07 · S647: P08 P09 · S648: P02 P03 P04 · S655: P03 P04 P05 P06 · S659: P08 · S666: P05 · S685: P03 P04 P05 P06 · S704: P01 · S715: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 · S735: P03 P04 P05 P06 P07 P08 · S736: P05

<a id="f6-thorn-bush"></a>
**6. `thorn_bush`** (142 IDs)  
S026: P01 P02 P04 P05 · S027: P02 P03 P04 P05 · S028: P02 · S029: P02 · S030: P02 · S031: P02 · S058: P02 P03 P04 P05 · S059: P01 P02 P04 P05 · S060: P02 P03 P04 P05 · S061: P02 P03 P04 P05 P06 · S062: P02 P03 P04 P05 P06 P07 P08 · S063: P02 P03 P04 P05 · S064: P02 P03 P04 P05 · S090: P02 P03 P04 P05 · S091: P02 P03 P04 P05 · S095: P02 P03 P04 P05 · S096: P02 P03 P04 P05 · S122: P01 P02 P03 P04 P05 P06 P07 P08 · S123: P05 · S124: P01 P02 · S125: P01 · S126: P01 · S127: P02 P03 P04 P05 · S128: P02 P03 P04 · S153: P01 · S154: P05 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 · S155: P02 P03 P04 P05 · S156: P02 P03 P04 · S157: P01 P02 P03 · S158: P02 P03 P04 P05 · S159: P02 P03 P04 P05 · S160: P02 P03 P05 · S189: P02 P03 P04 P05 · S190: P02 P03 P04 P05 · S191: P02 P03 P04 P05 · S192: P02 P03 P04 · S222: P02 P03 · S223: P02 P03 P04 P05 P06 · S224: P02 P03 P04 P05 · S254: P02 P03 · S255: P01

<a id="f7-dungeon-wall-stone"></a>
**7. `dungeon_wall_stone`** (139 IDs)  
S073: P01 P02 P05 P07 P08 P09 P16 · S074: P03 P08 P10 P12 P14 · S105: P04 P08 P10 P11 P12 · S106: P01 P02 P04 P06 · S138: P08 P10 P13 · S169: P02 P05 P06 P14 P15 · S170: P05 · S202: P02 · S260: P12 P13 P14 P15 P16 P24 P25 P26 P27 P28 · S385: P09 P10 P11 P12 · S386: P01 P02 P03 P04 P05 P06 · S387: P01 P02 P03 P04 P05 P06 · S388: P08 P09 P10 · S449: P01 P02 · S450: P01 P02 P03 P04 P05 P06 · S451: P01 P02 P04 P05 P06 · S452: P06 P08 P09 · S514: P07 P08 P10 P11 · S515: P02 P03 P07 P12 · S546: P05 P09 P10 · S547: P01 P02 P03 P05 · S577: P05 P09 P10 P11 P12 · S578: P01 P02 P06 P07 · S579: P04 P06 P07 P08 P13 P15 P16 P20 P21 · S609: P02 P05 P06 P07 P08 P09 · S610: P07 P08 P09 P10 P11 · S680: P01 P02 P03 P04 P05 · S681: P04 P05 P06 P07 P08 · S712: P02 P06 P10 P16 · S713: P05 P06 P07 P08 P13

<a id="f8-pine-forest-edge-strip-vert"></a>
**8. `pine_forest_edge_strip_vert`** (123 IDs)  
S144: P01 P02 P03 P05 · S176: P01 P02 P03 P04 · S177: P01 P02 P08 · S184: P01 · S186: P02 P03 · S188: P01 P02 · S208: P01 P04 · S209: P02 P15 P17 · S218: P02 P03 P04 P05 P08 · S220: P01 P02 · S237: P01 · S238: P01 P02 P03 · S239: P01 P02 · S241: P01 · S250: P02 P03 · S251: P02 P03 · S252: P07 · S253: P01 P02 P03 · S269: P01 · S270: P03 P04 · S271: P01 P02 P03 · S273: P03 · S279: P01 · S282: P03 P04 · S283: P01 P03 P05 · S284: P02 P03 · S288: P01 · S301: P01 · S303: P01 P02 · S305: P03 · S311: P01 P02 P05 · S314: P01 · S315: P01 P02 P03 · S316: P01 P02 · S320: P01 · S333: P04 · S334: P01 P03 · S335: P01 P03 · S337: P03 · S343: P01 P02 · S344: P02 P03 · S346: P01 P02 · S347: P01 P02 · S348: P01 P02 · S363: P02 · S364: P01 · S365: P01 · S366: P01 P03 P11 · S367: P07 · S375: P01 · S376: P03 P04 · S378: P02 · S379: P01 · S380: P01 · S395: P01 P02 · S426: P02 · S427: P02 · S560: P01 P02 · S568: P04 · S569: P01 · S600: P02 P03 · S601: P22 P23 · S632: P05 · S633: P01 · S735: P02 · S736: P03 P04 · S766: P01 · S767: P01 · S768: P01 P03

<a id="f9-dungeon-wall-stone-side"></a>
**9. `dungeon_wall_stone_side`** (101 IDs)  
S073: P11 P12 · S074: P01 P04 P05 P06 · S105: P01 P02 P05 P06 · S106: P08 P09 · S137: P03 P04 P06 P07 P08 P09 · S138: P02 P03 P04 P05 P06 P11 · S169: P08 P09 P17 · S170: P01 P02 P03 P04 · S202: P05 P06 P07 P08 P13 P14 P15 P16 P17 P18 · S260: P17 P18 P19 P20 P22 P23 · S385: P04 P07 P08 · S388: P04 P05 P11 · S417: P03 P04 P16 · S420: P05 P06 P07 P08 · S449: P04 P05 · S452: P11 P12 · S514: P02 P03 P04 P05 · S515: P09 P10 P11 · S546: P02 P03 P07 P08 · S547: P07 P08 P09 P10 · S577: P07 P08 · S578: P10 · S579: P09 P10 P11 P18 P19 · S609: P01 · S610: P01 P02 P03 · S680: P07 P08 · S681: P09 P10 P11 · S712: P01 P07 P08 · S713: P02 P03

<a id="f10-duck"></a>
**10. `duck`** (92 IDs)  
S002: P24 · S100: P36 · S161: P33 P34 P35 P36 · S162: P25 · S190: P11 P12 P13 · S194: P26 · S196: P25 · S307: P08 P09 P10 P11 P12 P14 · S374: P06 P07 P08 P09 P10 P11 P12 P13 P14 · S397: P03 P04 P05 P06 P07 · S405: P01 · S440: P02 · S441: P11 · S504: P11 · S521: P04 · S532: P05 P06 P07 · S535: P06 · S536: P03 P04 P05 P06 P07 P08 P12 P13 P14 P17 P18 P19 P20 P21 P22 P23 P24 P25 P27 P30 P32 P33 P35 P38 P39 P40 P41 · S537: P14 · S564: P03 · S570: P02 P03 P04 · S585: P18 · S604: P01 P02 P03 P04 · S652: P03 · S656: P05 P06 · S699: P10 P11 · S700: P04 P06 P09 · S711: P08 P09 · S762: P29 P30 · S764: P13 · SW_s8-duck2_L59@S762_P30

<a id="f11-duck-head"></a>
**11. `duck_head`** (90 IDs)  
S145: P01 P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 P24 P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 P35 P36 P37 P38 P39 P40 P41 P42 P43 P44 P45 P46 P47 P48 P49 P50 P51 P52 P53 P54 P55 P56 P57 P58 P59 P60 P61 P62 P63 P64 P65 P66 P67 P68 P69 P70 P71 P72 P73 P74 P75 P76 P77 P78 P79 P80 P81 P82 P83 P84 P85 P86 P87 P88 P89 P90

<a id="f12-int-wall-plaster-doorjamb"></a>
**12. `int_wall_plaster_doorjamb`** (81 IDs)  
S003: P19 · S005: P01 P02 · S006: P04 P06 · S033: P01 P02 · S034: P01 P02 · S035: P01 P02 · S036: P16 P17 P35 · S038: P15 P17 · S065: P15 P17 · S066: P15 P17 · S067: P08 P11 P16 P17 · S068: P15 P17 · S097: P15 P16 · S129: P10 P12 P16 P17 · S130: P07 P16 P17 P19 · S161: P16 P17 P18 P19 · S162: P16 P17 P18 P19 · S163: P10 P12 P16 P17 · S193: P03 P08 P11 · S194: P16 P17 P18 P19 · S195: P01 P02 · S196: P16 P17 P18 P19 · S225: P01 P02 · S226: P01 P02 · S228: P16 P17 P18 P19 · S261: P16 P17 P18 P19 · S289: P04 P11 P16 P17 · S290: P16 P17 P18 P26

<a id="f13-town-wall-stone-window"></a>
**13. `town_wall_stone_window`** (80 IDs)  
S218: P01 P13 P22 · S219: P05 P06 P08 P09 · S251: P04 P12 · S387: P07 · S388: P16 P17 · S417: P10 P11 P14 P15 P17 · S418: P02 P03 P04 P05 P08 P09 P10 · S419: P03 P04 P05 P06 P08 P09 · S420: P09 P10 P11 P12 · S465: P02 P08 · S466: P02 P03 P10 · S497: P01 P03 P04 · S498: P01 P03 P05 P06 P07 · S499: P05 P06 · S504: P01 P10 · S505: P02 P03 P04 P05 P08 · S506: P02 P04 P05 · S537: P01 P02 P03 · S538: P01 P07 P09 P10 P11 · S539: P02 · S570: P07 P08 · S585: P01 P03 P05 · S586: P01 P02 P12 P13 · S587: P02 P03 P04

<a id="f14-slime-blue"></a>
**14. `slime_blue`** (67 IDs)  
S032: P02 P03 P04 P05 P06 P07 · S064: P06 P07 · S123: P08 P10 · S191: P09 P10 · S347: P08 · S458: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 · S512: P09 P10 P11 P12 · S599: P09 P11 P13 · S633: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 · S652: P01 · S672: P01 P02 P03 P04 P05 P06 P07 P08 P09 · S695: P06 P07 P08 P09 P10 P11 P12 P13 P14 P15

<a id="f15-seashell-clam"></a>
**15. `seashell_clam`** (66 IDs)  
S258: P10 · S351: P01 · S352: P06 · S385: P02 · S417: P07 · S449: P07 · S452: P03 · S481: P05 P06 · S482: P05 P06 · S483: P03 P04 · S484: P04 · S487: P05 P06 · S488: P05 · S518: P01 · S519: P01 · S520: P02 · S550: P01 P07 · S551: P06 · S582: P02 · S583: P03 P08 · S614: P07 · S615: P02 P03 P04 · S646: P01 P06 · S647: P04 · S678: P07 · S688: P03 · S699: P02 P03 · S701: P10 P11 · S710: P06 · S711: P03 · S720: P01 · S725: P04 · S727: P01 P02 P05 · S728: P05 · S730: P03 P04 P05 · S731: P05 · S732: P03 · S733: P01 P02 P03 · S734: P30 · S742: P06 · S743: P03 · S752: P03 · S759: P02 · S761: P05 · S762: P17 P18 · S763: P01 · S764: P10 · S765: P08

<a id="f16-dungeon-wall-stone-curve"></a>
**16. `dungeon_wall_stone_curve`** (65 IDs)  
S073: P03 P04 P10 P13 · S074: P02 P07 P09 · S105: P03 P07 P19 · S106: P07 P14 · S137: P01 P02 P05 · S138: P01 P07 P12 · S169: P07 P16 · S170: P06 · S202: P01 P03 · S260: P11 P21 · S385: P03 · S388: P07 · S417: P01 P02 · S449: P03 · S452: P10 · S514: P01 P06 P09 · S515: P04 P05 P08 · S546: P01 P04 P06 · S547: P04 P06 · S577: P01 P02 P03 P04 P06 · S578: P03 P04 P05 P08 P09 · S579: P01 P02 P03 P12 · S609: P03 P04 · S610: P04 P05 P06 · S680: P06 · S712: P09 P14 · S713: P04

<a id="f17-bush-small"></a>
**17. `bush_small`** (57 IDs)  
S178: P04 P07 · S181: P10 · S182: P07 · S183: P01 · S184: P31 · S210: P03 · S211: P10 · S214: P04 · S218: P06 · S241: P02 · S243: P03 P07 · S246: P02 · S273: P07 · S277: P01 · S310: P04 · S315: P07 · S339: P03 · S366: P06 P19 · S372: P03 · S379: P07 P10 P11 P12 P13 P15 · S381: P04 · S405: P02 · S412: P05 · S427: P04 P05 · S436: P04 · S446: P07 · S458: P02 · S459: P03 · S490: P03 · S492: P03 · S497: P08 · S501: P04 · S504: P05 · S521: P02 · S529: P04 · S555: P10 · S557: P03 · S558: P01 · S561: P06 · S589: P02 · S590: P07 · S598: P04 · S599: P01 · S621: P01 · S681: P02 · S717: P01 · S718: P02 · S749: P01

<a id="f18-bush-round-medium"></a>
**18. `bush_round_medium`** (56 IDs)  
S178: P03 P05 · S180: P03 P04 P15 · S181: P11 · S183: P02 · S184: P13 · S210: P01 · S211: P09 · S212: P01 · S213: P07 · S273: P05 · S278: P01 · S308: P04 · S320: P03 · S399: P04 · S427: P03 · S436: P02 · S441: P27 · S446: P06 · S456: P01 · S457: P01 · S488: P03 · S491: P01 · S492: P02 · S493: P01 · S494: P01 · S499: P03 · S507: P04 · S508: P03 · S526: P02 · S529: P03 · S532: P04 · S559: P02 · S561: P04 · S567: P02 · S570: P06 · S590: P05 · S591: P01 · S598: P05 · S599: P02 · S623: P02 · S653: P01 · S654: P04 · S656: P04 · S681: P03 · S682: P01 · S685: P01 · S686: P02 · S687: P02 · S717: P02 · S718: P01 · S719: P04 · S745: P02 · S766: P02

<a id="f19-town-roof-flat"></a>
**19. `town_roof_flat`** (54 IDs)  
S187: P08 · S219: P02 · S385: P13 P14 P17 · S386: P07 P08 P09 P10 P11 P12 P13 · S387: P08 P09 P10 P11 P12 P13 P14 · S388: P12 P13 · S417: P05 P13 · S418: P07 P11 P12 · S419: P01 P10 · S465: P01 · S466: P01 P05 P06 P07 P08 P09 · S467: P06 · S473: P02 P04 P06 P07 · S474: P20 · S498: P09 · S505: P06 P09 P10 · S506: P07 P24 P30 · S538: P02 P05 · S553: P06 P08 · S555: P03 P04

<a id="f20-jar-vase"></a>
**20. `jar_vase`** (52 IDs)  
S003: P31 P32 · S033: P23 P24 P25 P26 P27 · S034: P40 P46 P47 P48 · S036: P30 P31 P32 P33 P34 · S195: P23 P24 P25 P26 P27 · S225: P23 P24 P25 P26 P27 P31 P32 P33 P34 · S226: P23 P24 P25 P26 P27 P28 P31 P32 P33 · S409: P35 · S663: P07 P08 P09 P10 P11 P12 P13 P14 · S764: P14 P24 P25 P26

<a id="f21-fern"></a>
**21. `fern`** (50 IDs)  
S244: P45 · S273: P01 · S274: P09 · S307: P05 · S308: P05 · S340: P05 · S351: P12 · S366: P18 · S380: P02 · S409: P05 P24 · S427: P09 P10 · S428: P01 · S468: P08 · S476: P02 · S479: P02 · S493: P03 · S565: P02 · S597: P02 · S598: P03 · S617: P10 · S651: P04 · S653: P03 · S666: P01 · S671: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 · S689: P02 · S690: P01 · S692: P01 · S700: P08 P16 P19 · S712: P18 · S715: P13 · S718: P04

<a id="f22-starfish"></a>
**22. `starfish`** (47 IDs)  
S257: P09 · S351: P03 · S385: P01 · S388: P06 · S417: P06 · S449: P06 · S452: P02 · S481: P02 · S482: P02 · S483: P01 P02 · S484: P02 · S487: P04 · S488: P04 · S518: P07 · S519: P03 · S520: P04 · S550: P06 · S551: P04 · S582: P03 · S615: P08 P09 · S647: P02 P03 · S688: P02 · S701: P13 · S710: P04 P05 · S711: P02 · S727: P04 · S728: P01 P02 P04 P06 · S731: P01 P04 · S732: P04 P05 · S742: P05 · S743: P01 P02 · S752: P02 · S759: P03 · S761: P04 · S762: P13 · S763: P08 · S765: P09

<a id="f23-tree-stump"></a>
**23. `tree_stump`** (47 IDs)  
S179: P04 P05 · S180: P02 P09 P10 · S181: P03 P04 P05 · S182: P11 P12 · S184: P08 P09 P27 P29 · S209: P11 P12 · S211: P05 P06 P07 · S212: P04 P05 · S214: P10 · S215: P02 P08 P09 P10 · S216: P07 P12 · S217: P05 · S242: P06 P07 · S243: P02 · S246: P01 · S283: P08 · S307: P02 · S316: P06 · S334: P08 · S503: P01 P02 P03 · S523: P02 P03 · S535: P03 P09 · S605: P04 · S654: P02 · S671: P69

<a id="f24-blood-splat"></a>
**24. `blood_splat`** (46 IDs)  
S060: P06 P07 · S061: P07 P08 · S091: P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 · S094: P02 P03 P04 P05 P06 P07 P08 · S122: P11 P12 P13 · S126: P02 P03 P04 P05 · S154: P22 P39 P40 P41 P42 P43 · S158: P06 · S190: P06 P07 P08 P09 · S191: P06 P07

<a id="f25-bones"></a>
**25. `bones`** (46 IDs)  
S073: P20 · S074: P17 P18 P19 P20 · S098: P01 P02 P05 · S099: P03 P04 P06 · S100: P28 P30 P31 P32 P33 · S105: P20 P21 · S106: P15 · S131: P03 P04 · S137: P12 P13 P14 · S154: P07 · S169: P01 P11 P12 P13 · S257: P02 P03 P05 P06 P07 · S258: P04 P05 P06 P07 P08 P09 · S259: P02 P03 P04 P05 P08 · S760: P06

<a id="f26-bush-round-large"></a>
**26. `bush_round_large`** (46 IDs)  
S177: P05 · S178: P02 · S179: P06 · S181: P08 · S182: P04 P05 · S183: P03 · S184: P30 · S210: P02 · S211: P08 · S212: P03 · S213: P06 · S215: P06 · S216: P13 · S253: P05 · S276: P01 · S285: P01 · S307: P03 · S337: P01 · S399: P07 · S427: P06 · S446: P05 · S490: P02 · S499: P02 · S521: P01 · S526: P01 · S530: P09 · S557: P02 · S558: P02 · S568: P01 · S570: P05 · S590: P06 · S596: P03 · S599: P03 · S622: P01 · S623: P01 · S637: P01 · S654: P03 · S655: P01 · S660: P03 · S662: P02 · S687: P01 · S688: P05 · S719: P03 · S744: P01 · S745: P01

<a id="f27-castle-wall-diag"></a>
**27. `castle_wall_diag`** (46 IDs)  
S014: P01 · S015: P01 P02 P03 · S016: P01 P02 P06 · S017: P01 · S018: P02 · S047: P01 P03 P04 · S048: P01 P02 P03 P04 P06 · S049: P01 P02 · S050: P01 · S070: P01 · S078: P01 · S079: P03 · S080: P01 P02 · S081: P01 · S336: P03 P04 · S367: P01 P04 · S368: P01 P03 P04 · S370: P02 · S399: P01 · S400: P01 P02 · S401: P01 P03 P04 · S402: P02 P07 P08 · S432: P01 · S433: P02 P05

<a id="f28-pine-forest-edge-strip"></a>
**28. `pine_forest_edge_strip`** (40 IDs)  
S186: P01 · S188: P04 · S208: P02 P03 · S209: P09 · S238: P04 P06 · S239: P03 P04 · S251: P05 · S273: P04 · S279: P02 P03 · S280: P01 P02 P03 · S281: P01 P02 P03 · S282: P01 P02 · S283: P02 P04 · S284: P01 · S288: P02 · S303: P03 · S333: P01 P03 · S334: P09 P10 · S335: P04 · S560: P03 · S568: P03 · S735: P01 · S736: P01 P02 · S766: P03 · S767: P02 P03 · S768: P02

<a id="f29-bush-wide"></a>
**29. `bush_wide`** (36 IDs)  
S178: P06 · S180: P05 · S181: P09 · S182: P06 · S212: P02 · S214: P03 · S215: P07 · S242: P08 · S273: P06 · S309: P01 · S405: P03 · S436: P03 · S459: P02 · S493: P02 · S494: P02 · S522: P02 · S524: P01 · S537: P15 · S555: P11 · S556: P01 P06 · S559: P01 · S561: P05 · S567: P04 · S573: P04 · S589: P03 · S591: P03 · S599: P04 · S601: P01 · S621: P02 · S622: P02 · S653: P02 · S658: P01 · S686: P01 · S687: P03 · S750: P01

<a id="f30-int-wall-plaster-corner-l"></a>
**30. `int_wall_plaster_corner_l`** (34 IDs)  
S002: P01 · S003: P01 P26 · S004: P01 · S005: P07 · S006: P01 · S033: P07 · S034: P07 · S035: P07 · S036: P08 · S037: P01 · S038: P01 · S065: P01 · S066: P01 · S067: P04 · S068: P09 P18 · S097: P02 · S129: P04 · S130: P09 · S161: P09 · S162: P09 · S163: P04 · S193: P13 · S194: P09 · S195: P07 · S196: P09 · S225: P07 · S226: P07 · S228: P09 · S261: P09 · S289: P09 P12 · S290: P09

<a id="f31-tree-fruit"></a>
**31. `tree_fruit`** (34 IDs)  
S442: P02 P04 P05 P06 P07 P08 P09 P10 P11 P12 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S474: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P15 P16 P17

<a id="f32-tree-dead-dark"></a>
**32. `tree_dead_dark`** (33 IDs)  
S027: P01 · S031: P01 · S059: P03 · S060: P01 · S061: P01 · S062: P01 · S063: P01 · S064: P01 · S090: P01 · S091: P01 · S095: P01 · S096: P01 · S127: P01 · S155: P01 · S156: P01 · S158: P01 · S159: P01 · S160: P04 · S190: P01 · S191: P01 P12 · S223: P01 · S224: P01 P06 · S237: P02 · S254: P01 · S255: P02 · S271: P06 · S301: P02 · S302: P03 · S335: P07 · S528: P03 · S593: P03

<a id="f33-int-wall-plaster-corner-r"></a>
**33. `int_wall_plaster_corner_r`** (31 IDs)  
S002: P02 · S004: P02 · S005: P04 · S006: P12 · S033: P04 · S034: P04 · S035: P04 · S036: P04 · S037: P02 · S038: P02 · S065: P02 · S066: P02 · S067: P02 · S068: P01 P07 · S097: P01 · S129: P02 · S130: P02 · S161: P06 · S162: P06 · S163: P02 · S193: P14 · S194: P05 · S195: P04 · S196: P06 · S225: P04 · S226: P04 · S228: P06 · S261: P06 · S289: P06 · S290: P06

<a id="f34-hand-tool-small"></a>
**34. `hand_tool_small`** (30 IDs)  
S035: P28 P29 · S196: P28 P32 P33 P34 P35 P36 · S228: P25 P26 P27 P28 P29 P34 P35 P36 P39 · S229: P11 P12 P13 P14 · S261: P27 P28 P29 P30 P32 · S440: P23 P24 P25 · S734: P08

<a id="f35-sign-post"></a>
**35. `sign_post`** (30 IDs)  
S065: P18 · S132: P02 · S184: P11 · S244: P61 · S253: P07 · S315: P04 · S366: P05 · S376: P08 · S403: P03 · S404: P10 · S437: P40 · S451: P08 · S467: P02 · S497: P16 · S499: P11 · S502: P17 · S504: P04 · S529: P01 · S532: P12 · S533: P20 · S568: P07 · S587: P06 P13 · S588: P03 P04 · S590: P08 · S625: P01 · S712: P11 · S748: P04 · S759: P06

<a id="f36-seashell-conch"></a>
**36. `seashell_conch`** (29 IDs)  
S257: P08 · S385: P06 · S388: P03 · S417: P08 · S449: P08 · S481: P07 · S482: P07 · S518: P02 · S519: P02 · S520: P03 · S550: P02 · S551: P07 P08 · S582: P01 · S614: P08 · S646: P02 · S678: P08 · S679: P01 · S710: P03 · S725: P05 · S728: P03 · S729: P01 · S732: P06 · S742: P02 · S752: P04 · S761: P03 P06 · S764: P16 · S765: P15

<a id="f37-slime-red"></a>
**37. `slime_red`** (29 IDs)  
S192: P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S274: P10 · S658: P03 P04 P05 P06 P07 · S660: P04 P05 P06 P07 · S688: P07 P08

<a id="f38-burn-hole-decal"></a>
**38. `burn_hole_decal`** (26 IDs)  
S001: P44 P45 P46 P47 P48 P49 · S005: P25 P26 P27 · S066: P23 P24 · S439: P23 P24 P25 P26 P27 P28 P30 P36 P37 P46 · S533: P21 P22 P23 · S536: P16 P26

<a id="f39-counter-wood"></a>
**39. `counter_wood`** (23 IDs)  
S033: P19 · S034: P26 P27 · S035: P19 · S067: P20 · S070: P11 P12 P20 P21 · S097: P21 P22 · S130: P23 · S162: P32 · S194: P28 · S195: P19 · S196: P31 · S225: P19 · S226: P19 P34 · S228: P33 · S261: P23 · S346: P08 · SW_s2-bar_L104@S034_P27

<a id="f40-bridge-wood-deck"></a>
**40. `bridge_wood_deck`** (22 IDs)  
S416: P01 P02 · S448: P01 P02 P03 P04 P05 P06 P07 · S480: P01 P02 P03 · S512: P01 P02 · S533: P01 P02 P03 P25 · S544: P01 P02 · S701: P01 P02

<a id="f41-bonca-gray"></a>
**41. `bonca_gray`** (21 IDs)  
S027: P10 · S074: P23 · S090: P06 P07 P08 P09 · S137: P18 · S156: P06 · S160: P07 P08 P09 · S170: P13 P14 · S480: P04 P05 · S583: P09 · S632: P11 P12 · S633: P16 · S696: P04 · S715: P01

<a id="f42-crate"></a>
**42. `crate`** (21 IDs)  
S035: P21 · S066: P22 · S129: P20 · S161: P30 · S162: P21 · S194: P06 P21 · S229: P06 P07 P08 · S499: P10 · S538: P17 P18 · S742: P08 P09 P10 P11 P12 P13 P14 P15

<a id="f43-slayer"></a>
**43. `slayer`** (21 IDs)  
S028: P03 P04 · S035: P32 · S106: P18 · S127: P06 · S137: P17 · S138: P16 · S156: P07 · S157: P05 P06 P07 P08 · S166: P25 P26 · S448: P08 P09 · S652: P02 · S663: P04 · S695: P05 · S696: P02 P03

<a id="f44-support-post-timber"></a>
**44. `support_post_timber`** (21 IDs)  
S002: P16 P17 P18 P19 · S033: P21 · S034: P21 P25 · S035: P18 · S036: P24 · S067: P27 · S097: P23 P24 · S195: P21 · S196: P27 · S225: P21 · S226: P21 · S228: P22 · S261: P25 · S289: P20 · S290: P20 P29

<a id="f45-town-wall-gable-end"></a>
**45. `town_wall_gable_end`** (21 IDs)  
S187: P11 · S218: P07 · S219: P04 · S385: P15 · S388: P15 · S417: P12 · S465: P05 · S467: P05 · S472: P04 · S474: P18 P19 · S499: P04 · S506: P06 · S507: P05 · S538: P03 · S539: P03 · S553: P01 P04 · S554: P01 P04 · S555: P01

<a id="f46-door-wood-single"></a>
**46. `door_wood_single`** (22 IDs)  
S188: P10 · S219: P10 · S251: P09 · S274: P07 · S409: P16 · S418: P16 · S419: P02 · S497: P12 · S498: P11 · S499: P07 · S500: P06 · S501: P11 · S506: P20 · S530: P11 · S539: P12 · S585: P14 · S587: P12 · S617: P15 · S619: P09 · S734: P31 · SW_s2-mdoor_L106@S530_P11 · SW_s2-mdoor_L82@S530_P11

<a id="f47-cabinet-wood"></a>
**47. `cabinet_wood`** (20 IDs)  
S003: P15 P16 · S033: P29 · S034: P28 P31 P32 P43 P44 · S035: P20 · S036: P23 P26 · S038: P20 · S067: P26 · S193: P24 · S195: P29 · S225: P29 · S226: P29 · S228: P21 · S290: P21 · S366: P15

<a id="f48-castle-tower-round"></a>
**48. `castle_tower_round`** (20 IDs)  
S018: P01 · S047: P02 · S049: P03 · S050: P02 · S070: P02 · S078: P02 · S079: P01 P04 · S080: P03 · S112: P01 · S336: P01 · S337: P05 · S367: P03 · S368: P07 · S369: P03 · S370: P01 · S399: P03 · S401: P02 · S402: P01 · S433: P01

<a id="f49-grain-sack"></a>
**49. `grain_sack`** (19 IDs)  
S005: P22 · S229: P15 · S539: P06 P07 P08 P09 · S762: P03 P05 P06 · S763: P21 P23 P24 · S764: P11 P17 P18 P19 P20 P21 P22

<a id="f50-int-wall-plaster-end-r"></a>
**50. `int_wall_plaster_end_r`** (19 IDs)  
S002: P03 P22 · S003: P07 · S004: P03 · S005: P14 · S006: P08 · S033: P14 · S034: P14 · S035: P14 · S036: P13 · S037: P03 · S038: P03 · S065: P03 · S066: P03 · S068: P03 · S097: P12 · S195: P14 · S225: P14 · S226: P14

<a id="f51-flower-small"></a>
**51. `flower_small`** (18 IDs)  
S288: P07 · S306: P05 · S309: P02 · S320: P06 P08 · S341: P04 · S343: P03 · S347: P09 · S396: P04 · S398: P02 · S428: P04 · S507: P09 · S520: P07 · S523: P04 · S551: P10 · S563: P12 · S628: P01 P04

<a id="f52-int-wall-plaster-end-l"></a>
**52. `int_wall_plaster_end_l`** (18 IDs)  
S002: P04 P12 · S003: P02 · S004: P04 · S005: P03 · S033: P03 · S034: P03 · S035: P03 · S036: P12 · S037: P04 · S038: P04 · S065: P04 · S066: P04 · S068: P11 · S097: P13 · S195: P03 · S225: P03 · S226: P03

<a id="f53-npc-knight-blue"></a>
**53. `npc_knight_blue`** (18 IDs)  
S070: P13 P14 P15 P16 P17 P18 · S102: P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 · S243: P11 P12

<a id="f54-tree-dead-frosted"></a>
**54. `tree_dead_frosted`** (18 IDs)  
S028: P01 · S029: P01 · S032: P01 · S058: P01 · S123: P03 P04 · S149: P01 P04 · S189: P01 · S192: P01 · S217: P04 · S270: P01 · S271: P05 · S302: P04 · S303: P04 · S333: P08 · S334: P02 P04

<a id="f55-bowl"></a>
**55. `bowl`** (17 IDs)  
S006: P25 · S033: P22 P28 · S034: P38 P39 P45 · S035: P25 · S036: P28 P29 · S195: P22 P28 · S225: P22 P28 · S226: P22 · S261: P33 · S537: P06 · S663: P15

<a id="f56-dungeon-pillar"></a>
**56. `dungeon_pillar`** (17 IDs)  
S138: P15 · S514: P13 P14 · S515: P01 P06 P13 · S536: P60 P61 P62 P63 · S546: P11 P12 · S547: P11 P12 P13 · S712: P04 P05

<a id="f57-fence-rail-ns"></a>
**57. `fence_rail_ns`** (17 IDs)  
S375: P02 P03 · S408: P21 P22 P23 P24 · S409: P08 P41 P52 · S441: P06 P07 P08 P31 · S469: P09 P10 · S536: P28 P42

<a id="f58-town-roof-slope"></a>
**58. `town_roof_slope`** (17 IDs)  
S186: P23 · S187: P10 · S218: P20 · S385: P16 · S388: P14 · S465: P07 · S467: P03 · S472: P06 · S474: P22 · S506: P26 · S507: P07 · S538: P04 · S553: P02 P05 · S554: P03 P06 · S555: P02

<a id="f59-cottage-door"></a>
**59. `cottage_door`** (16 IDs)  
S274: P15 · S350: P08 · S440: P04 · S469: P06 · S497: P07 · S500: P04 · S501: P06 P10 · S530: P04 · S532: P09 · S537: P05 · S617: P14 · S618: P09 · S619: P08 P10 · S734: P03

<a id="f60-cottage-thatched-large"></a>
**60. `cottage_thatched_large`** (16 IDs)  
S409: P12 P14 · S437: P12 P21 · S468: P04 P05 · S469: P02 P05 · S470: P01 P03 · S501: P02 · S587: P05 · S618: P01 P12 · S619: P03 P07

<a id="f61-cottage-thatched-small"></a>
**61. `cottage_thatched_small`** (16 IDs)  
S274: P02 P03 · S469: P01 · S497: P05 P06 · S500: P12 · S501: P01 P03 P05 P09 · S532: P01 P10 · S537: P04 P23 · S619: P02 P11

<a id="f62-dragon"></a>
**62. `dragon`** (16 IDs)  
S074: P21 P22 · S123: P07 · S124: P03 P04 · S127: P07 P08 P09 P10 · S156: P08 · S159: P06 P07 P08 P09 · S160: P06 · S191: P11

<a id="f63-mushroom"></a>
**63. `mushroom`** (16 IDs)  
S244: P62 · S400: P03 · S411: P04 P05 P06 · S460: P04 · S477: P04 · S490: P04 · S520: P08 · S540: P05 · S541: P08 · S552: P05 · S567: P12 · S630: P08 · S636: P02 P03

<a id="f64-town-roof-dormer"></a>
**64. `town_roof_dormer`** (16 IDs)  
S187: P07 P09 · S218: P21 · S219: P01 P03 · S465: P03 · S466: P04 · S472: P10 · S473: P05 P08 · S474: P21 · S498: P08 · S505: P07 · S506: P08 P25 · S538: P06

<a id="f65-door-wood-wide"></a>
**65. `door_wood_wide`** (15 IDs)  
S350: P09 · S440: P06 · S469: P20 · S497: P13 P15 · S498: P10 · S501: P12 · S504: P15 · S505: P01 · S532: P11 · S537: P24 · S538: P21 · S585: P13 · S618: P11 · S619: P12

<a id="f66-food-fruit"></a>
**66. `food_fruit`** (15 IDs)  
S070: P31 P35 P36 P37 · S693: P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17

<a id="f67-gold-pile"></a>
**67. `gold_pile`** (15 IDs)  
S352: P22 P23 P24 P25 P26 P27 P28 P29 P31 P32 P34 P35 P36 P38 P39

<a id="f68-hanging-vines"></a>
**68. `hanging_vines`** (15 IDs)  
S073: P18 · S105: P13 P14 P15 · S106: P10 P11 · S137: P15 P16 · S169: P10 P18 · S202: P10 · S244: P57 P58 P59 P60

<a id="f69-island-fence-lattice"></a>
**69. `island_fence_lattice`** (15 IDs)  
S489: P03 · S711: P07 · S712: P03 · S731: P03 P10 P11 P12 P13 P14 · S732: P02 · S762: P08 P09 · S763: P07 P20 · S764: P09

<a id="f70-potion-red"></a>
**70. `potion_red`** (15 IDs)  
S032: P08 · S166: P24 · S198: P20 P21 · S209: P10 · S214: P02 · S223: P13 · S248: P03 · S352: P19 · S663: P06 · S671: P70 · S681: P14 P15 P16 P17

<a id="f71-town-roof-ridge-cap"></a>
**71. `town_roof_ridge_cap`** (15 IDs)  
S186: P51 · S187: P12 · S385: P18 · S388: P18 · S465: P04 · S467: P04 · S472: P02 · S474: P23 · S506: P23 · S507: P08 · S553: P03 P07 · S554: P02 P05 · S555: P05

<a id="f72-town-wall-stone-door"></a>
**72. `town_wall_stone_door`** (15 IDs)  
S219: P07 · S418: P06 · S419: P07 · S497: P02 · S498: P02 P04 · S499: P01 · S504: P02 · S505: P16 · S506: P03 · S538: P08 · S539: P01 · S585: P02 P04 · S587: P01

<a id="f73-arrow-prop"></a>
**73. `arrow_prop`** (14 IDs)  
S097: P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 · S663: P20 P21 P22 P23

<a id="f74-chest-small"></a>
**74. `chest_small`** (14 IDs)  
S005: P28 · S069: P02 · S101: P02 · S184: P02 · S209: P05 · S276: P04 · S282: P06 · S288: P03 · S395: P03 · S536: P29 · S557: P05 · S671: P65 · S685: P07 · S747: P01

<a id="f75-fence-rail-diag-nw"></a>
**75. `fence_rail_diag_nw`** (14 IDs)  
S409: P19 P20 P21 P42 · S437: P08 P09 P10 P11 P13 P14 P15 P34 · S568: P13 P14

<a id="f76-gravestone"></a>
**76. `gravestone`** (14 IDs)  
S035: P24 · S129: P21 · S163: P20 · S228: P32 · S229: P02 P03 P04 P05 · S274: P13 · S289: P24 · S290: P24 P27 P28 · S734: P10

<a id="f77-stone-giant"></a>
**77. `stone_giant`** (14 IDs)  
S178: P10 P11 · S182: P13 · S183: P12 · S209: P14 P16 · S211: P01 · S212: P08 · S213: P10 · S215: P11 · S242: P15 · S245: P01 P02 · S246: P03

<a id="f78-crate-small"></a>
**78. `crate_small`** (13 IDs)  
S035: P22 · S161: P31 P32 · S162: P29 P30 · S194: P25 · S196: P21 · S261: P21 · S499: P09 P12 · S506: P17 · S538: P19 · S742: P16

<a id="f79-dragon-statue"></a>
**79. `dragon_statue`** (13 IDs)  
S153: P03 · S154: P01 P02 · S170: P15 P16 P17 P18 P19 P20 P21 P22 · S202: P11 P12

<a id="f80-skull"></a>
**80. `skull`** (13 IDs)  
S098: P06 · S099: P01 · S100: P29 · S123: P06 · S131: P02 · S154: P11 · S257: P04 · S258: P01 P02 P03 · S259: P06 P07 · S760: P07

<a id="f81-bonca-brown"></a>
**81. `bonca_brown`** (12 IDs)  
S029: P03 P04 P05 P06 P07 · S100: P35 · S302: P06 P07 · S306: P06 · S562: P03 · S583: P10 · S648: P07

<a id="f82-castle-wall-corner"></a>
**82. `castle_wall_corner`** (12 IDs)  
S016: P04 P05 · S017: P02 P03 · S018: P03 · S070: P04 · S337: P02 P04 · S369: P01 P02 · S370: P04 · S402: P09

<a id="f83-island-hut-round"></a>
**83. `island_hut_round`** (12 IDs)  
S489: P02 · S680: P10 · S681: P12 · S712: P13 · S732: P01 · S748: P01 · S762: P01 · S763: P02 P03 P05 · S764: P02 P03

<a id="f84-rubble-pile"></a>
**84. `rubble_pile`** (12 IDs)  
S073: P17 · S074: P15 · S105: P16 · S106: P12 P13 · S137: P10 · S138: P14 · S170: P07 · S202: P09 · S514: P12 · S578: P11 · S609: P10

<a id="f85-shelf-bottles"></a>
**85. `shelf_bottles`** (12 IDs)  
S002: P11 P20 · S003: P22 · S006: P17 · S033: P18 · S034: P41 P42 · S130: P20 · S194: P27 · S195: P18 · S225: P18 · S226: P18

<a id="f86-shelf-empty"></a>
**86. `shelf_empty`** (12 IDs)  
S005: P21 · S066: P19 P20 · S130: P32 · S161: P26 · S162: P26 P31 · S193: P27 · S196: P22 · S228: P24 · S229: P09 · S261: P22

<a id="f87-crate-stack"></a>
**87. `crate_stack`** (11 IDs)  
S035: P23 · S130: P21 · S194: P29 · S196: P29 · S228: P31 · S274: P14 · S289: P25 · S290: P25 · S500: P14 · S734: P05 P06

<a id="f88-potion-purple"></a>
**88. `potion_purple`** (11 IDs)  
S062: P09 P10 · S159: P10 P11 P12 P13 · S166: P20 · S273: P08 · S352: P17 P21 · S597: P01

<a id="f89-slime-green"></a>
**89. `slime_green`** (11 IDs)  
S546: P13 P14 P15 P16 P17 P18 P19 P20 · S610: P12 P13 P14

<a id="f90-cave-hole-warp"></a>
**90. `cave_hole_warp`** (10 IDs)  
S085: P01 · S112: P02 · S144: P04 · S182: P01 · S209: P01 · S248: P01 · S254: P04 · S483: P11 · S625: P05 · S671: P01

<a id="f91-fallen-log"></a>
**91. `fallen_log`** (10 IDs)  
S244: P06 P12 · S618: P04 · S624: P05 · S650: P04 · S671: P64 · S691: P03 · S728: P08 · S752: P01 · S765: P02

<a id="f92-island-totem-pole"></a>
**92. `island_totem_pole`** (10 IDs)  
S100: P01 · S366: P07 P08 · S684: P01 · S713: P09 · S716: P01 P02 · S762: P10 P11 P12

<a id="f93-save-machine"></a>
**93. `save_machine`** (10 IDs)  
S037: P19 · S213: P01 · S252: P01 · S254: P05 · S344: P01 · S349: P01 · S408: P25 · S569: P02 · S588: P05 · S768: P04

<a id="f94-stool"></a>
**94. `stool`** (10 IDs)  
S070: P07 P08 P09 P10 · S130: P26 P27 P28 P29 P30 P31

<a id="f95-bonca-purple"></a>
**95. `bonca_purple`** (9 IDs)  
S514: P15 P16 · S515: P14 · S547: P14 P16 P17 · S577: P14 P15 · S609: P13

<a id="f96-bookcase"></a>
**96. `bookcase`** (9 IDs)  
S004: P19 · S006: P18 · S038: P13 · S067: P07 P28 P29 P30 · S129: P23 · S161: P21

<a id="f97-fire-fx"></a>
**97. `fire_fx`** (9 IDs)  
S001: P21 P27 P30 P31 P32 · S439: P05 P09 P11 P21

<a id="f98-log-cabin-window"></a>
**98. `log_cabin_window`** (9 IDs)  
S251: P08 · S274: P16 · S409: P11 · S440: P08 P09 · S500: P05 · S501: P07 P08 · S530: P05

<a id="f99-potion-blue"></a>
**99. `potion_blue`** (9 IDs)  
S070: P22 · S122: P14 · S127: P11 · S166: P01 P23 · S243: P01 · S352: P18 · S603: P02 · S750: P02

<a id="f100-stairs-wood"></a>
**100. `stairs_wood`** (9 IDs)  
S003: P28 P29 · S004: P13 · S036: P27 · S037: P13 · S163: P27 P28 · S228: P23 · S229: P01

<a id="f101-table-round"></a>
**101. `table_round`** (9 IDs)  
S004: P17 · S034: P37 · S036: P25 · S037: P17 · S038: P19 · S161: P27 · S163: P22 · S193: P25 · S289: P21

<a id="f102-tree-dead-dark-tall"></a>
**102. `tree_dead_dark_tall`** (9 IDs)  
S026: P03 · S030: P01 · S128: P01 · S160: P01 · S222: P01 · S269: P02 · S271: P04 · S302: P01 · S636: P01

<a id="f103-twig"></a>
**103. `twig`** (9 IDs)  
S244: P10 P11 · S320: P09 · S502: P15 · S618: P03 · S624: P04 · S650: P03 · S760: P04 · S765: P05

<a id="f104-bench-short"></a>
**104. `bench_short`** (8 IDs)  
S006: P21 P22 · S260: P01 P02 P03 P04 P05 P06

<a id="f105-dungeon-wall-stone-ivy"></a>
**105. `dungeon_wall_stone_ivy`** (8 IDs)  
S073: P06 P15 · S074: P11 · S105: P09 · S106: P03 · S169: P03 P04 · S202: P04

<a id="f106-fish"></a>
**106. `fish`** (8 IDs)  
S634: P01 P02 P03 · S665: P03 · S697: P02 P03 P04 · S727: P17

<a id="f107-gold-coin"></a>
**107. `gold_coin`** (8 IDs)  
S505: P15 · S537: P10 P11 P12 P13 · S663: P03 P17 P18

<a id="f108-ground-crack"></a>
**108. `ground_crack`** (8 IDs)  
S005: P19 · S066: P29 · S154: P03 P04 P06 P09 P10 · S193: P23

<a id="f109-island-torch"></a>
**109. `island_torch`** (8 IDs)  
S731: P02 · S762: P02 · S763: P06 P18 P19 · S764: P04 P05 P07

<a id="f110-pig"></a>
**110. `pig`** (8 IDs)  
S031: P04 · S587: P14 · S636: P05 P06 P07 · S694: P01 P02 P03

<a id="f111-shop-sign"></a>
**111. `shop_sign`** (8 IDs)  
S498: P13 P14 · S499: P13 · S504: P17 · S506: P16 · S538: P22 · S539: P05 · S585: P17

<a id="f112-small-heart"></a>
**112. `small_heart`** (8 IDs)  
S101: P03 P04 P05 P06 P07 P08 P09 P10

<a id="f113-bridge-wood-rail-plank"></a>
**113. `bridge_wood_rail_plank`** (7 IDs)  
S404: P01 P04 · S512: P03 P04 P05 · S693: P28 P29

<a id="f114-bridge-wood-rail-rope"></a>
**114. `bridge_wood_rail_rope`** (7 IDs)  
S404: P03 P05 · S512: P06 P07 P08 · S693: P30 P31

<a id="f115-cottage-thatched-two-storey"></a>
**115. `cottage_thatched_two_storey`** (7 IDs)  
S440: P03 P11 · S500: P01 P02 · S586: P04 · S618: P02 P10

<a id="f116-flower-bed-row"></a>
**116. `flower_bed_row`** (7 IDs)  
S437: P01 P02 P03 P04 P05 P06 · S683: P04

<a id="f117-snake-pillar"></a>
**117. `snake_pillar`** (7 IDs)  
S238: P07 P08 P09 P10 P11 · S625: P02 P03

<a id="f118-wall-stripe-red"></a>
**118. `wall_stripe_red`** (7 IDs)  
S097: P35 P36 P37 P38 P39 P40 P41

<a id="f119-bench-long"></a>
**119. `bench_long`** (6 IDs)  
S034: P29 P30 P33 P34 P35 P36

<a id="f120-cottage-thatched-l-shape"></a>
**120. `cottage_thatched_l_shape`** (6 IDs)  
S318: P01 · S349: P04 · S350: P01 P02 · S734: P01 P02

<a id="f121-dungeon-wall-stone-cracked"></a>
**121. `dungeon_wall_stone_cracked`** (6 IDs)  
S073: P14 · S074: P13 · S106: P05 · S138: P09 · S579: P05 P14

<a id="f122-fence-rail-diag-ne"></a>
**122. `fence_rail_diag_ne`** (6 IDs)  
S441: P05 P12 P13 P14 · S469: P07 P08

<a id="f123-goblin-soldier"></a>
**123. `goblin_soldier`** (6 IDs)  
S680: P11 P12 · S712: P15 P17 · S713: P11 P12

<a id="f124-golden-heart"></a>
**124. `golden_heart`** (6 IDs)  
S106: P19 · S157: P09 · S165: P01 · S166: P02 · S352: P20 · S524: P04

<a id="f125-pitchfork"></a>
**125. `pitchfork`** (6 IDs)  
S035: P30 · S196: P39 · S229: P10 · S274: P12 · S440: P21 · S762: P07

<a id="f126-small-fire-fx"></a>
**126. `small_fire_fx`** (6 IDs)  
S001: P35 P36 P38 · S439: P31 P32 P33

<a id="f127-ground-hole-dark"></a>
**127. `ground_hole_dark`** (10 IDs)  
S132: P01 · S180: P01 · S209: P04 · S243: P13 · S277: P02 · SW_s1-hole3_L22@S209_P04 · SW_s1-hole_L21@S132_P01 · SW_s1-hole_L21@S277_P02 · SW_s6-hole2_L22@S180_P01 · SW_s6-hole_L22@S243_P13

<a id="f128-chimney-stone"></a>
**128. `chimney_stone`** (5 IDs)  
S469: P03 P04 · S500: P03 · S530: P10 · S734: P04

<a id="f129-idol-statue-small"></a>
**129. `idol_statue_small`** (5 IDs)  
S074: P16 · S137: P11 · S164: P01 P20 · S579: P22

<a id="f130-island-spear-pole"></a>
**130. `island_spear_pole`** (5 IDs)  
S748: P02 · S762: P04 · S763: P22 · S764: P12 P15

<a id="f131-thorn-branch"></a>
**131. `thorn_branch`** (5 IDs)  
S099: P05 · S123: P01 P02 · S192: P05 P06

<a id="f132-weed-sprig"></a>
**132. `weed_sprig`** (5 IDs)  
S440: P05 · S441: P09 P15 P18 P19

<a id="f133-well-stone"></a>
**133. `well_stone`** (5 IDs)  
S408: P07 · S432: P03 · S497: P09 · S600: P01 · S766: P04

<a id="f134-tree-pine-large"></a>
**134. `tree_pine_large`** (7 IDs)  
S307: P13 · S534: P10 · S659: P06 · S710: P14 · SW_s2-sec1_L37@S307_P13 · SW_s2-sec3_L37@S659_P06 · SW_s3-sec1_L39@S710_P14

<a id="f135-npc-knight-silver"></a>
**135. `npc_knight_silver`** (6 IDs)  
S402: P03 P05 · S408: P04 · S568: P06 · SW_s2-ca-g_L179@S402_P03 · SW_s2-ca-g_L179@S402_P05

<a id="f136-boulder-flat"></a>
**136. `boulder_flat`** (4 IDs)  
S535: P12 · S590: P03 P10 P11

<a id="f137-bridge-stone"></a>
**137. `bridge_stone`** (4 IDs)  
S102: P01 P02 P03 P04

<a id="f138-cabbage"></a>
**138. `cabbage`** (4 IDs)  
S070: P27 P28 P29 P34

<a id="f139-cottage-thatched-long"></a>
**139. `cottage_thatched_long`** (4 IDs)  
S530: P01 P03 · S617: P01 P13

<a id="f140-fish-flopping"></a>
**140. `fish_flopping`** (4 IDs)  
S734: P09 · S760: P01 P02 P03

<a id="f141-goblin-hammer"></a>
**141. `goblin_hammer`** (4 IDs)  
S680: P13 P14 · S712: P12 · S748: P03

<a id="f142-island-hut-two-storey"></a>
**142. `island_hut_two_storey`** (4 IDs)  
S680: P09 · S681: P13 · S763: P04 · S764: P01

<a id="f143-npc-girl"></a>
**143. `npc_girl`** (4 IDs)  
S091: P22 · S122: P10 · S126: P06 P07

<a id="f144-npc-knight-red"></a>
**144. `npc_knight_red`** (4 IDs)  
S149: P05 P09 · S374: P03 P04

<a id="f145-poster-hark"></a>
**145. `poster_hark`** (4 IDs)  
S033: P30 · S195: P30 · S225: P30 · S226: P30

<a id="f146-teleport-shrine"></a>
**146. `teleport_shrine`** (6 IDs)  
S153: P02 · S154: P23 · S253: P06 · SW_s6-warp_L46@S253_P06 · SW_s7-warp_L46@S153_P02 · SW_s7-warp_L46@S154_P23

<a id="f147-bomb-item"></a>
**147. `bomb_item`** (3 IDs)  
S228: P40 P41 P42

<a id="f148-church"></a>
**148. `church`** (3 IDs)  
S187: P02 · S188: P03 P05

<a id="f149-church-stained-glass"></a>
**149. `church_stained_glass`** (3 IDs)  
S188: P07 P08 P09

<a id="f150-dragon-corpse"></a>
**150. `dragon_corpse`** (3 IDs)  
S100: P34 · S158: P07 · S238: P12

<a id="f151-fallen-branch-forked"></a>
**151. `fallen_branch_forked`** (3 IDs)  
S244: P07 · S470: P04 · S502: P16

<a id="f152-fireplace-brick"></a>
**152. `fireplace_brick`** (3 IDs)  
S038: P16 · S129: P24 · S163: P23

<a id="f153-pillbug-corpse"></a>
**153. `pillbug_corpse`** (3 IDs)  
S098: P04 · S100: P25 P26

<a id="f154-rake"></a>
**154. `rake`** (3 IDs)  
S035: P31 · S409: P33 · S734: P07

<a id="f155-teleport-machine"></a>
**155. `teleport_machine`** (3 IDs)  
S154: P08 · S253: P04 · SW_s7-warp_L46@S154_P08

<a id="f156-boulder-large"></a>
**156. `boulder_large`** (2 IDs)  
S277: P03 · S590: P01

<a id="f157-boulder-red"></a>
**157. `boulder_red`** (2 IDs)  
S536: P15 · S590: P04

<a id="f158-boulder-white-pair"></a>
**158. `boulder_white_pair`** (2 IDs)  
S165: P23 · S590: P02

<a id="f159-burnt-floor-hole"></a>
**159. `burnt_floor_hole`** (2 IDs)  
S439: P34 P38

<a id="f160-castle-wall-end"></a>
**160. `castle_wall_end`** (2 IDs)  
S016: P03 · S048: P05

<a id="f161-cellar-hatch"></a>
**161. `cellar_hatch`** (2 IDs)  
S068: P24 P25

<a id="f162-chest-large"></a>
**162. `chest_large`** (2 IDs)  
S098: P07 · S536: P31

<a id="f163-chest-medium"></a>
**163. `chest_medium`** (2 IDs)  
S026: P06 · S284: P04

<a id="f164-church-window-small"></a>
**164. `church_window_small`** (2 IDs)  
S187: P01 P03

<a id="f165-corpse-merchant"></a>
**165. `corpse_merchant`** (2 IDs)  
S092: P01 · S094: P01

<a id="f166-duck-corpse"></a>
**166. `duck_corpse`** (2 IDs)  
S100: P27 · S521: P05

<a id="f167-dungeon-wall-stone-arch"></a>
**167. `dungeon_wall_stone_arch`** (2 IDs)  
S451: P03 · S625: P06

<a id="f168-explosion-fx"></a>
**168. `explosion_fx`** (2 IDs)  
S001: P28 P29

<a id="f169-fire-burst-fx"></a>
**169. `fire_burst_fx`** (2 IDs)  
S001: P33 P41

<a id="f170-fireball-fx"></a>
**170. `fireball_fx`** (2 IDs)  
S366: P09 P14

<a id="f171-food-drumstick"></a>
**171. `food_drumstick`** (2 IDs)  
S070: P23 · S149: P10

<a id="f172-food-pie"></a>
**172. `food_pie`** (2 IDs)  
S070: P24 P25

<a id="f173-fountain-spray-fx"></a>
**173. `fountain_spray_fx`** (2 IDs)  
S260: P30 · S586: P14

<a id="f174-fountain-stone"></a>
**174. `fountain_stone`** (2 IDs)  
S260: P07 · S586: P03

<a id="f175-hearth-fire"></a>
**175. `hearth_fire`** (2 IDs)  
S001: P20 · S163: P24

<a id="f176-log-cabin"></a>
**176. `log_cabin`** (2 IDs)  
S251: P01 · S270: P07

<a id="f177-log-cabin-door"></a>
**177. `log_cabin_door`** (2 IDs)  
S251: P07 · S409: P13

<a id="f178-npc-knight-red-attacking"></a>
**178. `npc_knight_red_attacking`** (2 IDs)  
S241: P03 · S242: P03

<a id="f179-npc-merchant-blue"></a>
**179. `npc_merchant_blue`** (2 IDs)  
S290: P30 · S374: P05

<a id="f180-npc-merchant-green"></a>
**180. `npc_merchant_green`** (2 IDs)  
S164: P02 · S227: P02

<a id="f181-npc-peasant"></a>
**181. `npc_peasant`** (2 IDs)  
S003: P23 · S038: P22

<a id="f182-scythe"></a>
**182. `scythe`** (2 IDs)  
S228: P30 · S440: P22

<a id="f183-sparkle-fx"></a>
**183. `sparkle_fx`** (2 IDs)  
S001: P37 · S045: P01

<a id="f184-spinning-wheel"></a>
**184. `spinning_wheel`** (2 IDs)  
S004: P20 · S035: P26

<a id="f185-tree-willow"></a>
**185. `tree_willow`** (2 IDs)  
S414: P02 · S446: P02

<a id="f186-tree-willow-large"></a>
**186. `tree_willow_large`** (2 IDs)  
S149: P02 · S474: P01

<a id="f187-weed-small"></a>
**187. `weed_small`** (2 IDs)  
S446: P01 P03

<a id="f188-axe-item"></a>
**188. `axe_item`** (1 IDs)  
S170: P08

<a id="f189-ballista"></a>
**189. `ballista`** (1 IDs)  
S196: P30

<a id="f190-barrel-broken"></a>
**190. `barrel_broken`** (1 IDs)  
S193: P26

<a id="f191-boulder-grey-tall"></a>
**191. `boulder_grey_tall`** (1 IDs)  
S601: P08

<a id="f192-burn-damage-decal"></a>
**192. `burn_damage_decal`** (1 IDs)  
S439: P29

<a id="f193-cabinet-narrow"></a>
**193. `cabinet_narrow`** (1 IDs)  
S260: P10

<a id="f194-castle-door"></a>
**194. `castle_door`** (1 IDs)  
S402: P04

<a id="f195-castle-drawbridge"></a>
**195. `castle_drawbridge`** (1 IDs)  
S080: P05

<a id="f196-castle-gatehouse"></a>
**196. `castle_gatehouse`** (1 IDs)  
S080: P04

<a id="f197-catapult"></a>
**197. `catapult`** (1 IDs)  
S489: P01

<a id="f198-church-door"></a>
**198. `church_door`** (1 IDs)  
S188: P06

<a id="f199-corpse-girl"></a>
**199. `corpse_girl`** (1 IDs)  
S222: P04

<a id="f200-corpse-knight"></a>
**200. `corpse_knight`** (1 IDs)  
S157: P04

<a id="f201-corpse-maiden"></a>
**201. `corpse_maiden`** (1 IDs)  
S091: P21

<a id="f202-corpse-mom"></a>
**202. `corpse_mom`** (1 IDs)  
S001: P34

<a id="f203-corpse-peasant"></a>
**203. `corpse_peasant`** (1 IDs)  
S222: P05

<a id="f204-corpse-soldier"></a>
**204. `corpse_soldier`** (1 IDs)  
S086: P01

<a id="f205-dink-dead"></a>
**205. `dink_dead`** (1 IDs)  
S058: P06

<a id="f206-dink-monument-rock"></a>
**206. `dink_monument_rock`** (1 IDs)  
S536: P01

<a id="f207-dungeon-arch-freestanding"></a>
**207. `dungeon_arch_freestanding`** (1 IDs)  
S579: P17

<a id="f208-food-bread"></a>
**208. `food_bread`** (1 IDs)  
S070: P33

<a id="f209-food-cheese"></a>
**209. `food_cheese`** (1 IDs)  
S070: P26

<a id="f210-food-grapes"></a>
**210. `food_grapes`** (1 IDs)  
S070: P30

<a id="f211-food-ham"></a>
**211. `food_ham`** (1 IDs)  
S070: P32

<a id="f212-gold-coins-small"></a>
**212. `gold_coins_small`** (1 IDs)  
S663: P16

<a id="f213-golden-duck-statue"></a>
**213. `golden_duck_statue`** (1 IDs)  
S536: P43

<a id="f214-heart-pickup"></a>
**214. `heart_pickup`** (1 IDs)  
S190: P10

<a id="f215-king-on-throne"></a>
**215. `king_on_throne`** (1 IDs)  
S070: P03

<a id="f216-npc-gnome-purple"></a>
**216. `npc_gnome_purple`** (1 IDs)  
S006: P23

<a id="f217-npc-maiden-blue"></a>
**217. `npc_maiden_blue`** (1 IDs)  
S004: P16

<a id="f218-npc-maiden-brown"></a>
**218. `npc_maiden_brown`** (1 IDs)  
S410: P06

<a id="f219-npc-maiden-red"></a>
**219. `npc_maiden_red`** (1 IDs)  
S122: P09

<a id="f220-npc-old-man"></a>
**220. `npc_old_man`** (1 IDs)  
S002: P23

<a id="f221-npc-soldier"></a>
**221. `npc_soldier`** (1 IDs)  
S410: P07

<a id="f222-ore-rock-blue"></a>
**222. `ore_rock_blue`** (1 IDs)  
S590: P09

<a id="f223-poster-wanted"></a>
**223. `poster_wanted`** (1 IDs)  
S035: P27

<a id="f224-scroll-note"></a>
**224. `scroll_note`** (1 IDs)  
S006: P24

<a id="f225-snake-carving"></a>
**225. `snake_carving`** (1 IDs)  
S625: P04

<a id="f226-snow-house-door"></a>
**226. `snow_house_door`** (1 IDs)  
S149: P07

<a id="f227-snow-house-lower"></a>
**227. `snow_house_lower`** (1 IDs)  
S149: P03

<a id="f228-snow-house-roof"></a>
**228. `snow_house_roof`** (1 IDs)  
S149: P08

<a id="f229-snow-house-timber"></a>
**229. `snow_house_timber`** (1 IDs)  
S149: P06

<a id="f230-tree-oak-large"></a>
**230. `tree_oak_large`** (1 IDs)  
S693: P06

<a id="f231-screen-ground-tile-layer"></a>
**231. `screen ground (tile layer)`** (639 IDs)  
SCR 002 003 004 005 006 010 013 014 015 016 017 018 025 026 027 028 029 030 031 032 033 034 035 036 037 038 045 046 047 048 049 050 057 058 059 060 061 062 063 064 065 066 067 068 069 070 073 074 077 078 079 080 081 082 085 086 089 090 091 092 093 094 095 096 097 098 099 100 101 102 105 106 109 110 111 112 113 114 117 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 137 138 143 144 145 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 169 170 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 202 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 298 299 301 302 303 304 305 306 307 308 309 310 311 312 313 314 315 316 317 318 319 320 324 333 334 335 336 337 338 339 340 341 342 343 344 345 346 347 348 349 350 351 352 353 354 355 356 357 358 359 363 364 365 366 367 368 369 370 371 372 373 374 375 376 377 378 379 380 381 382 383 384 385 386 387 388 389 390 391 395 396 397 398 399 400 401 402 403 404 405 406 408 409 410 411 412 413 414 415 416 417 418 419 420 421 422 423 424 425 426 427 428 429 430 431 432 433 434 435 436 437 440 441 442 443 444 445 446 447 448 449 450 451 452 453 454 455 456 457 458 459 460 461 462 463 464 465 466 467 468 469 470 472 473 474 475 476 477 478 479 480 481 482 483 484 485 486 487 488 489 490 491 492 493 494 495 496 497 498 499 500 501 502 503 504 505 506 507 508 509 510 511 512 514 515 516 517 518 519 520 521 522 523 524 525 526 527 528 529 530 531 532 533 534 535 536 537 538 539 540 541 542 543 544 546 547 548 549 550 551 552 553 554 555 556 557 558 559 560 561 562 563 564 565 566 567 568 569 570 571 572 573 574 575 576 577 578 579 580 581 582 583 584 585 586 587 588 589 590 591 592 593 594 595 596 597 598 599 600 601 602 603 604 605 606 607 608 609 610 611 612 613 614 615 616 617 618 619 620 621 622 623 624 625 626 627 628 629 630 631 632 633 634 635 636 637 638 639 640 646 647 648 649 650 651 652 653 654 655 656 657 658 659 660 661 662 663 664 665 666 667 668 669 670 671 672 678 679 680 681 682 683 684 685 686 687 688 689 690 691 692 693 694 695 696 697 698 699 700 701 702 703 704 710 711 712 713 714 715 716 717 718 719 720 721 722 723 724 725 726 727 728 729 730 731 732 733 734 735 736 742 743 744 745 746 747 748 749 750 751 752 753 754 755 756 757 758 759 760 761 762 763 764 765 766 767 768
