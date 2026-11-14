# Alpha gate 2 backlog: origin IDs still open

Generated 2026-11-14 by `DinkRemasterUE/Scripts/gate2_backlog.py` from `Saved/Import/coverage.csv` (6607 rows, importer run of 2026-11-12) and the manifests under `Content/Dink/Data/Art/`, classified by `Scripts/art_coverage.py`. Do not edit by hand; regenerate.

Alpha gate 2 (`doc/remaster/REMASTER_PLAN.md`): every origin ID is final, placeholder or cut with a reason. This list is what is still open: every origin ID whose art state in `Scripts/art_coverage.py` is `placeholder` (no art bound; nothing in the repo records a placeholder as owner-accepted), plus any unclassified ID. Final (bespoke or by family, `Content/Dink/Data/Art/families.json`) and cut (owner decision of 9 Nov 2026) are closed and not listed.

## Summary

| | open |
|---|---:|
| sprite families | 130 |
| origin IDs | 1492 |
| map placements | 1176 |
| screens (ground tile layer) | 303 |
| script warps with their own ID | 13 |
| unclassified IDs | 0 |

Claimed by the Claude photoreal pass (in progress elsewhere, not final): **53 families, 1075 origin IDs, 766 placements**. Unclaimed: 77 families, 417 origin IDs, 410 placements.

Largest family by origin IDs: `screen ground (tile layer)` (303 IDs, 0 map placements, so it sorts at #130).

Largest families no stream has claimed: `blood_splat` 46, `tree_fruit` 34, `burn_hole_decal` 26, `bonca_gray` 21, `slayer` 21, `npc_knight_blue` 18, `dragon` 16, `arrow_prop` 14, `stone_giant` 14, `bonca_brown` 12.

Closed for comparison (art_coverage rows): final bespoke 754, final by family 4164, cut 152, placeholder 1537 of 6607 rows.

## How to regenerate

```bash
cd DinkRemasterUE && python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md
```

Run it in the editor's checkout: like `art_coverage.py` it needs the importer's `Saved/Import/coverage.csv` (`Scripts/import_greybox.sh --region all`), `tools/dinkex/out/sequences.json` and the gitignored engine template content under `Content/Characters` (the mother's locomotion). From another worktree add `--project <editor checkout>/DinkRemasterUE`. The photoreal column is a snapshot of `<--photoreal-root>/*/manifest.json` (default: the uncommitted photoreal pass work copy), read-only; regenerate after that pass lands or binds families.

## Backlog by sprite family

Sorted by open map placements. Family is the class id (`tools/data/sprite_classes.csv`, the key `families.json` binds); *what the original shows* gives its name, sprite group, size and the reference sheet in `doc/remaster/reference/`; *sequences* are the original sprite sequences of the open placements. The origin IDs of each family are listed under [Open origin IDs](#open-origin-ids).

| # | family | what the original sprite sheet shows | sequences (open placements) | origin IDs | placements | photoreal pass |
|---:|---|---|---|---:|---:|---|
| 1 | [`duck`](#f1-duck) | - | seq 23 (24), seq 29 (18), seq 24 (14), seq 26 (12), seq 27 (12), seq 21 (11) | 92 | 91 | Creatures |
| 2 | [`duck_head`](#f2-duck-head) | - | seq 121 (90) | 90 | 90 | Creatures |
| 3 | [`slime_blue`](#f3-slime-blue) | - | seq 651 (67) | 67 | 67 | Creatures |
| 4 | [`town_roof_flat`](#f4-town-roof-flat) | - | seq 33 (52) | 52 | 52 | TownExteriors |
| 5 | [`blood_splat`](#f5-blood-splat) | - | seq 188 (24), seq 189 (18), seq 187 (4) | 46 | 46 | - |
| 6 | [`castle_wall_diag`](#f6-castle-wall-diag) | - | seq 67 (46) | 46 | 46 | Structures |
| 7 | [`tree_fruit`](#f7-tree-fruit) | - | seq 421 (34) | 34 | 34 | - |
| 8 | [`slime_red`](#f8-slime-red) | - | seq 693 (17), seq 691 (12) | 29 | 29 | Creatures |
| 9 | [`burn_hole_decal`](#f9-burn-hole-decal) | - | seq 158 (26) | 26 | 26 | - |
| 10 | [`bridge_wood_deck`](#f10-bridge-wood-deck) | - | seq 58 (22) | 22 | 22 | Structures |
| 11 | [`bonca_gray`](#f11-bonca-gray) | - | seq 601 (6), seq 603 (4), seq 609 (4), seq 592 (3), seq 607 (3), seq 594 (1) | 21 | 21 | - |
| 12 | [`slayer`](#f12-slayer) | - | seq 632 (7), seq 641 (6), seq 634 (4), seq 643 (1), seq 649 (1), seq 647 (1), seq 636 (1) | 21 | 21 | - |
| 13 | [`door_wood_single`](#f13-door-wood-single) | - | seq 61 (20) | 22 | 20 | Structures |
| 14 | [`castle_tower_round`](#f14-castle-tower-round) | - | seq 67 (20) | 20 | 20 | Structures |
| 15 | [`npc_knight_blue`](#f15-npc-knight-blue) | - | seq 287 (8), seq 289 (8), seq 281 (1), seq 283 (1) | 18 | 18 | - |
| 16 | [`fence_rail_ns`](#f16-fence-rail-ns) | - | seq 93 (17) | 17 | 17 | Structures |
| 17 | [`cottage_door`](#f17-cottage-door) | - | seq 63 (16) | 16 | 16 | Structures |
| 18 | [`cottage_thatched_large`](#f18-cottage-thatched-large) | - | seq 63 (16) | 16 | 16 | Structures |
| 19 | [`cottage_thatched_small`](#f19-cottage-thatched-small) | - | seq 63 (16) | 16 | 16 | Structures |
| 20 | [`dragon`](#f20-dragon) | - | seq 202 (8), seq 206 (4), seq 204 (3), seq 208 (1) | 16 | 16 | - |
| 21 | [`town_roof_dormer`](#f21-town-roof-dormer) | - | seq 33 (16) | 16 | 16 | TownExteriors |
| 22 | [`door_wood_wide`](#f22-door-wood-wide) | - | seq 62 (15) | 15 | 15 | Structures |
| 23 | [`island_fence_lattice`](#f23-island-fence-lattice) | - | seq 424 (15) | 15 | 15 | Structures |
| 24 | [`town_roof_slope`](#f24-town-roof-slope) | - | seq 33 (15) | 15 | 15 | TownExteriors |
| 25 | [`arrow_prop`](#f25-arrow-prop) | - | seq 25 (14) | 14 | 14 | - |
| 26 | [`chest_small`](#f26-chest-small) | - | seq 175 (14) | 14 | 14 | Props |
| 27 | [`fence_rail_diag_nw`](#f27-fence-rail-diag-nw) | - | seq 93 (14) | 14 | 14 | Structures |
| 28 | [`stone_giant`](#f28-stone-giant) | - | seq 821 (8), seq 823 (3), seq 816 (1), seq 829 (1), seq 827 (1) | 14 | 14 | - |
| 29 | [`town_roof_ridge_cap`](#f29-town-roof-ridge-cap) | - | seq 33 (14) | 14 | 14 | TownExteriors |
| 30 | [`bonca_brown`](#f30-bonca-brown) | - | seq 542 (2), seq 544 (2), seq 533 (2), seq 539 (2), seq 537 (2), seq 531 (2) | 12 | 12 | - |
| 31 | [`castle_wall_corner`](#f31-castle-wall-corner) | - | seq 67 (12) | 12 | 12 | Structures |
| 32 | [`island_hut_round`](#f32-island-hut-round) | - | seq 424 (12) | 12 | 12 | Structures |
| 33 | [`slime_green`](#f33-slime-green) | - | seq 671 (11) | 11 | 11 | Creatures |
| 34 | [`cave_hole_warp`](#f34-cave-hole-warp) | - | seq 89 (10) | 10 | 10 | - |
| 35 | [`island_totem_pole`](#f35-island-totem-pole) | - | seq 424 (10) | 10 | 10 | Structures |
| 36 | [`bonca_purple`](#f36-bonca-purple) | - | seq 613 (6), seq 619 (1), seq 628 (1), seq 626 (1) | 9 | 9 | - |
| 37 | [`fire_fx`](#f37-fire-fx) | - | seq 427 (9) | 9 | 9 | Props |
| 38 | [`log_cabin_window`](#f38-log-cabin-window) | - | seq 59 (9) | 9 | 9 | - |
| 39 | [`stairs_wood`](#f39-stairs-wood) | - | seq 428 (9) | 9 | 9 | - |
| 40 | [`fish`](#f40-fish) | - | seq 434 (8) | 8 | 8 | - |
| 41 | [`gold_coin`](#f41-gold-coin) | - | seq 178 (8) | 8 | 8 | - |
| 42 | [`ground_crack`](#f42-ground-crack) | - | seq 89 (8) | 8 | 8 | - |
| 43 | [`island_torch`](#f43-island-torch) | - | seq 425 (8) | 8 | 8 | Props |
| 44 | [`pig`](#f44-pig) | - | seq 41 (5), seq 43 (2), seq 49 (1) | 8 | 8 | Creatures |
| 45 | [`bridge_wood_rail_plank`](#f45-bridge-wood-rail-plank) | - | seq 58 (7) | 7 | 7 | Structures |
| 46 | [`bridge_wood_rail_rope`](#f46-bridge-wood-rail-rope) | - | seq 58 (7) | 7 | 7 | Structures |
| 47 | [`cottage_thatched_two_storey`](#f47-cottage-thatched-two-storey) | - | seq 63 (7) | 7 | 7 | Structures |
| 48 | [`wall_stripe_red`](#f48-wall-stripe-red) | - | seq 450 (7) | 7 | 7 | - |
| 49 | [`cottage_thatched_l_shape`](#f49-cottage-thatched-l-shape) | - | seq 63 (6) | 6 | 6 | Structures |
| 50 | [`fence_rail_diag_ne`](#f50-fence-rail-diag-ne) | - | seq 93 (6) | 6 | 6 | Structures |
| 51 | [`goblin_soldier`](#f51-goblin-soldier) | - | seq 809 (3), seq 801 (2), seq 803 (1) | 6 | 6 | - |
| 52 | [`small_fire_fx`](#f52-small-fire-fx) | - | seq 155 (2), seq 156 (2), seq 157 (2) | 6 | 6 | Props |
| 53 | [`ground_hole_dark`](#f53-ground-hole-dark) | - | seq 89 (5) | 10 | 5 | - |
| 54 | [`chimney_stone`](#f54-chimney-stone) | - | seq 63 (5) | 5 | 5 | Structures |
| 55 | [`shop_sign`](#f55-shop-sign) | - | seq 458 (5) | 5 | 5 | - |
| 56 | [`well_stone`](#f56-well-stone) | - | seq 186 (5) | 5 | 5 | Structures |
| 57 | [`tree_pine_large`](#f57-tree-pine-large) | - | seq 32 (4) | 7 | 4 | Vegetation |
| 58 | [`npc_knight_silver`](#f58-npc-knight-silver) | - | seq 293 (2), seq 299 (1), seq 291 (1) | 6 | 4 | - |
| 59 | [`boulder_flat`](#f59-boulder-flat) | - | seq 95 (4) | 4 | 4 | - |
| 60 | [`bridge_stone`](#f60-bridge-stone) | - | seq 186 (4) | 4 | 4 | Structures |
| 61 | [`cottage_thatched_long`](#f61-cottage-thatched-long) | - | seq 63 (4) | 4 | 4 | Structures |
| 62 | [`fish_flopping`](#f62-fish-flopping) | - | seq 439 (3), seq 441 (1) | 4 | 4 | - |
| 63 | [`food_fruit`](#f63-food-fruit) | - | seq 421 (4) | 4 | 4 | - |
| 64 | [`goblin_hammer`](#f64-goblin-hammer) | - | seq 763 (2), seq 761 (1), seq 769 (1) | 4 | 4 | - |
| 65 | [`island_hut_two_storey`](#f65-island-hut-two-storey) | - | seq 424 (4) | 4 | 4 | Structures |
| 66 | [`npc_girl`](#f66-npc-girl) | - | seq 331 (3), seq 339 (1) | 4 | 4 | - |
| 67 | [`npc_knight_red`](#f67-npc-knight-red) | - | seq 273 (2), seq 279 (1), seq 277 (1) | 4 | 4 | - |
| 68 | [`poster_hark`](#f68-poster-hark) | - | seq 462 (4) | 4 | 4 | - |
| 69 | [`bomb_item`](#f69-bomb-item) | - | seq 420 (3) | 3 | 3 | - |
| 70 | [`cabinet_wood`](#f70-cabinet-wood) | - | seq 87 (3) | 3 | 3 | Props |
| 71 | [`church`](#f71-church) | - | seq 60 (3) | 3 | 3 | - |
| 72 | [`church_stained_glass`](#f72-church-stained-glass) | - | seq 60 (3) | 3 | 3 | - |
| 73 | [`fireplace_brick`](#f73-fireplace-brick) | - | seq 64 (3) | 3 | 3 | Props |
| 74 | [`pillbug_corpse`](#f74-pillbug-corpse) | - | seq 141 (2), seq 143 (1) | 3 | 3 | Creatures |
| 75 | [`boulder_large`](#f75-boulder-large) | - | seq 95 (2) | 2 | 2 | - |
| 76 | [`boulder_red`](#f76-boulder-red) | - | seq 95 (2) | 2 | 2 | - |
| 77 | [`burnt_floor_hole`](#f77-burnt-floor-hole) | - | seq 158 (2) | 2 | 2 | - |
| 78 | [`castle_wall_end`](#f78-castle-wall-end) | - | seq 67 (2) | 2 | 2 | Structures |
| 79 | [`cellar_hatch`](#f79-cellar-hatch) | - | seq 428 (2) | 2 | 2 | - |
| 80 | [`chest_large`](#f80-chest-large) | - | seq 177 (2) | 2 | 2 | Props |
| 81 | [`chest_medium`](#f81-chest-medium) | - | seq 176 (2) | 2 | 2 | Props |
| 82 | [`church_window_small`](#f82-church-window-small) | - | seq 60 (2) | 2 | 2 | - |
| 83 | [`dragon_corpse`](#f83-dragon-corpse) | - | seq 212 (2) | 2 | 2 | - |
| 84 | [`duck_corpse`](#f84-duck-corpse) | - | seq 127 (1), seq 121 (1) | 2 | 2 | Creatures |
| 85 | [`explosion_fx`](#f85-explosion-fx) | - | seq 70 (2) | 2 | 2 | - |
| 86 | [`fire_burst_fx`](#f86-fire-burst-fx) | - | seq 161 (2) | 2 | 2 | - |
| 87 | [`fireball_fx`](#f87-fireball-fx) | - | seq 512 (2) | 2 | 2 | - |
| 88 | [`food_pie`](#f88-food-pie) | - | seq 421 (2) | 2 | 2 | Props |
| 89 | [`fountain_spray_fx`](#f89-fountain-spray-fx) | - | seq 94 (2) | 2 | 2 | - |
| 90 | [`hearth_fire`](#f90-hearth-fire) | - | seq 86 (2) | 2 | 2 | - |
| 91 | [`log_cabin`](#f91-log-cabin) | - | seq 59 (2) | 2 | 2 | - |
| 92 | [`log_cabin_door`](#f92-log-cabin-door) | - | seq 59 (2) | 2 | 2 | - |
| 93 | [`npc_knight_red_attacking`](#f93-npc-knight-red-attacking) | - | seq 712 (2) | 2 | 2 | - |
| 94 | [`npc_merchant_blue`](#f94-npc-merchant-blue) | - | seq 371 (2) | 2 | 2 | - |
| 95 | [`npc_merchant_green`](#f95-npc-merchant-green) | - | seq 381 (2) | 2 | 2 | - |
| 96 | [`npc_peasant`](#f96-npc-peasant) | - | seq 411 (2) | 2 | 2 | - |
| 97 | [`sparkle_fx`](#f97-sparkle-fx) | - | seq 165 (1), seq 166 (1) | 2 | 2 | - |
| 98 | [`tree_willow`](#f98-tree-willow) | - | seq 32 (2) | 2 | 2 | Vegetation |
| 99 | [`tree_willow_large`](#f99-tree-willow-large) | - | seq 32 (2) | 2 | 2 | Vegetation |
| 100 | [`boulder_grey_tall`](#f100-boulder-grey-tall) | - | seq 95 (1) | 1 | 1 | - |
| 101 | [`boulder_white_pair`](#f101-boulder-white-pair) | - | seq 95 (1) | 1 | 1 | - |
| 102 | [`burn_damage_decal`](#f102-burn-damage-decal) | - | seq 154 (1) | 1 | 1 | - |
| 103 | [`castle_door`](#f103-castle-door) | - | seq 68 (1) | 1 | 1 | - |
| 104 | [`castle_drawbridge`](#f104-castle-drawbridge) | - | seq 68 (1) | 1 | 1 | - |
| 105 | [`castle_gatehouse`](#f105-castle-gatehouse) | - | seq 67 (1) | 1 | 1 | Structures |
| 106 | [`church_door`](#f106-church-door) | - | seq 60 (1) | 1 | 1 | - |
| 107 | [`corpse_mom`](#f107-corpse-mom) | - | seq 355 (1) | 1 | 1 | - |
| 108 | [`corpse_soldier`](#f108-corpse-soldier) | - | seq 405 (1) | 1 | 1 | - |
| 109 | [`dink_dead`](#f109-dink-dead) | - | seq 436 (1) | 1 | 1 | - |
| 110 | [`food_bread`](#f110-food-bread) | - | seq 421 (1) | 1 | 1 | - |
| 111 | [`food_cheese`](#f111-food-cheese) | - | seq 421 (1) | 1 | 1 | - |
| 112 | [`food_drumstick`](#f112-food-drumstick) | - | seq 421 (1) | 1 | 1 | - |
| 113 | [`food_grapes`](#f113-food-grapes) | - | seq 421 (1) | 1 | 1 | - |
| 114 | [`food_ham`](#f114-food-ham) | - | seq 421 (1) | 1 | 1 | - |
| 115 | [`king_on_throne`](#f115-king-on-throne) | - | seq 421 (1) | 1 | 1 | - |
| 116 | [`npc_gnome_purple`](#f116-npc-gnome-purple) | - | seq 561 (1) | 1 | 1 | - |
| 117 | [`npc_maiden_blue`](#f117-npc-maiden-blue) | - | seq 251 (1) | 1 | 1 | - |
| 118 | [`npc_maiden_brown`](#f118-npc-maiden-brown) | - | seq 241 (1) | 1 | 1 | - |
| 119 | [`npc_maiden_red`](#f119-npc-maiden-red) | - | seq 221 (1) | 1 | 1 | - |
| 120 | [`npc_old_man`](#f120-npc-old-man) | - | seq 231 (1) | 1 | 1 | - |
| 121 | [`npc_soldier`](#f121-npc-soldier) | - | seq 403 (1) | 1 | 1 | - |
| 122 | [`ore_rock_blue`](#f122-ore-rock-blue) | - | seq 95 (1) | 1 | 1 | - |
| 123 | [`poster_wanted`](#f123-poster-wanted) | - | seq 462 (1) | 1 | 1 | - |
| 124 | [`snow_house_door`](#f124-snow-house-door) | - | seq 96 (1) | 1 | 1 | - |
| 125 | [`snow_house_lower`](#f125-snow-house-lower) | - | seq 96 (1) | 1 | 1 | - |
| 126 | [`snow_house_roof`](#f126-snow-house-roof) | - | seq 96 (1) | 1 | 1 | - |
| 127 | [`snow_house_timber`](#f127-snow-house-timber) | - | seq 96 (1) | 1 | 1 | - |
| 128 | [`thorn_branch`](#f128-thorn-branch) | - | seq 90 (1) | 1 | 1 | Vegetation |
| 129 | [`tree_oak_large`](#f129-tree-oak-large) | - | seq 32 (1) | 1 | 1 | Vegetation |
| 130 | [`screen ground (tile layer)`](#f130-screen-ground-tile-layer) | tile-layer ground of each screen (grass, sand, water, walls painted into tilesets) · sheet_tiles.png | - | 303 | 0 | Terrain |

## Open origin IDs

Placements as `Snnn: Pnn ...` (screen, then slot), screens as `SCR nnn ...`, script warps by full ID.

<a id="f1-duck"></a>
**1. `duck`** (92 IDs)  
S002: P24 · S100: P36 · S161: P33 P34 P35 P36 · S162: P25 · S190: P11 P12 P13 · S194: P26 · S196: P25 · S307: P08 P09 P10 P11 P12 P14 · S374: P06 P07 P08 P09 P10 P11 P12 P13 P14 · S397: P03 P04 P05 P06 P07 · S405: P01 · S440: P02 · S441: P11 · S504: P11 · S521: P04 · S532: P05 P06 P07 · S535: P06 · S536: P03 P04 P05 P06 P07 P08 P12 P13 P14 P17 P18 P19 P20 P21 P22 P23 P24 P25 P27 P30 P32 P33 P35 P38 P39 P40 P41 · S537: P14 · S564: P03 · S570: P02 P03 P04 · S585: P18 · S604: P01 P02 P03 P04 · S652: P03 · S656: P05 P06 · S699: P10 P11 · S700: P04 P06 P09 · S711: P08 P09 · S762: P29 P30 · S764: P13 · SW_s8-duck2_L59@S762_P30

<a id="f2-duck-head"></a>
**2. `duck_head`** (90 IDs)  
S145: P01 P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 P24 P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 P35 P36 P37 P38 P39 P40 P41 P42 P43 P44 P45 P46 P47 P48 P49 P50 P51 P52 P53 P54 P55 P56 P57 P58 P59 P60 P61 P62 P63 P64 P65 P66 P67 P68 P69 P70 P71 P72 P73 P74 P75 P76 P77 P78 P79 P80 P81 P82 P83 P84 P85 P86 P87 P88 P89 P90

<a id="f3-slime-blue"></a>
**3. `slime_blue`** (67 IDs)  
S032: P02 P03 P04 P05 P06 P07 · S064: P06 P07 · S123: P08 P10 · S191: P09 P10 · S347: P08 · S458: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 · S512: P09 P10 P11 P12 · S599: P09 P11 P13 · S633: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 · S652: P01 · S672: P01 P02 P03 P04 P05 P06 P07 P08 P09 · S695: P06 P07 P08 P09 P10 P11 P12 P13 P14 P15

<a id="f4-town-roof-flat"></a>
**4. `town_roof_flat`** (52 IDs)  
S187: P08 · S219: P02 · S385: P13 P14 P17 · S386: P07 P08 P09 P10 P11 P12 P13 · S387: P08 P09 P10 P11 P12 P13 P14 · S388: P12 P13 · S417: P05 P13 · S418: P07 P11 P12 · S419: P01 P10 · S465: P01 · S466: P01 P05 P06 P07 P08 P09 · S467: P06 · S473: P02 P04 P06 P07 · S474: P20 · S498: P09 · S505: P06 P09 P10 · S506: P07 P30 · S538: P05 · S553: P06 P08 · S555: P03 P04

<a id="f5-blood-splat"></a>
**5. `blood_splat`** (46 IDs)  
S060: P06 P07 · S061: P07 P08 · S091: P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 · S094: P02 P03 P04 P05 P06 P07 P08 · S122: P11 P12 P13 · S126: P02 P03 P04 P05 · S154: P22 P39 P40 P41 P42 P43 · S158: P06 · S190: P06 P07 P08 P09 · S191: P06 P07

<a id="f6-castle-wall-diag"></a>
**6. `castle_wall_diag`** (46 IDs)  
S014: P01 · S015: P01 P02 P03 · S016: P01 P02 P06 · S017: P01 · S018: P02 · S047: P01 P03 P04 · S048: P01 P02 P03 P04 P06 · S049: P01 P02 · S050: P01 · S070: P01 · S078: P01 · S079: P03 · S080: P01 P02 · S081: P01 · S336: P03 P04 · S367: P01 P04 · S368: P01 P03 P04 · S370: P02 · S399: P01 · S400: P01 P02 · S401: P01 P03 P04 · S402: P02 P07 P08 · S432: P01 · S433: P02 P05

<a id="f7-tree-fruit"></a>
**7. `tree_fruit`** (34 IDs)  
S442: P02 P04 P05 P06 P07 P08 P09 P10 P11 P12 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S474: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P15 P16 P17

<a id="f8-slime-red"></a>
**8. `slime_red`** (29 IDs)  
S192: P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S274: P10 · S658: P03 P04 P05 P06 P07 · S660: P04 P05 P06 P07 · S688: P07 P08

<a id="f9-burn-hole-decal"></a>
**9. `burn_hole_decal`** (26 IDs)  
S001: P44 P45 P46 P47 P48 P49 · S005: P25 P26 P27 · S066: P23 P24 · S439: P23 P24 P25 P26 P27 P28 P30 P36 P37 P46 · S533: P21 P22 P23 · S536: P16 P26

<a id="f10-bridge-wood-deck"></a>
**10. `bridge_wood_deck`** (22 IDs)  
S416: P01 P02 · S448: P01 P02 P03 P04 P05 P06 P07 · S480: P01 P02 P03 · S512: P01 P02 · S533: P01 P02 P03 P25 · S544: P01 P02 · S701: P01 P02

<a id="f11-bonca-gray"></a>
**11. `bonca_gray`** (21 IDs)  
S027: P10 · S074: P23 · S090: P06 P07 P08 P09 · S137: P18 · S156: P06 · S160: P07 P08 P09 · S170: P13 P14 · S480: P04 P05 · S583: P09 · S632: P11 P12 · S633: P16 · S696: P04 · S715: P01

<a id="f12-slayer"></a>
**12. `slayer`** (21 IDs)  
S028: P03 P04 · S035: P32 · S106: P18 · S127: P06 · S137: P17 · S138: P16 · S156: P07 · S157: P05 P06 P07 P08 · S166: P25 P26 · S448: P08 P09 · S652: P02 · S663: P04 · S695: P05 · S696: P02 P03

<a id="f13-door-wood-single"></a>
**13. `door_wood_single`** (22 IDs)  
S188: P10 · S219: P10 · S251: P09 · S274: P07 · S409: P16 · S418: P16 · S419: P02 · S497: P12 · S498: P11 · S499: P07 · S500: P06 · S501: P11 · S506: P20 · S530: P11 · S539: P12 · S585: P14 · S587: P12 · S617: P15 · S619: P09 · S734: P31 · SW_s2-mdoor_L106@S530_P11 · SW_s2-mdoor_L82@S530_P11

<a id="f14-castle-tower-round"></a>
**14. `castle_tower_round`** (20 IDs)  
S018: P01 · S047: P02 · S049: P03 · S050: P02 · S070: P02 · S078: P02 · S079: P01 P04 · S080: P03 · S112: P01 · S336: P01 · S337: P05 · S367: P03 · S368: P07 · S369: P03 · S370: P01 · S399: P03 · S401: P02 · S402: P01 · S433: P01

<a id="f15-npc-knight-blue"></a>
**15. `npc_knight_blue`** (18 IDs)  
S070: P13 P14 P15 P16 P17 P18 · S102: P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 · S243: P11 P12

<a id="f16-fence-rail-ns"></a>
**16. `fence_rail_ns`** (17 IDs)  
S375: P02 P03 · S408: P21 P22 P23 P24 · S409: P08 P41 P52 · S441: P06 P07 P08 P31 · S469: P09 P10 · S536: P28 P42

<a id="f17-cottage-door"></a>
**17. `cottage_door`** (16 IDs)  
S274: P15 · S350: P08 · S440: P04 · S469: P06 · S497: P07 · S500: P04 · S501: P06 P10 · S530: P04 · S532: P09 · S537: P05 · S617: P14 · S618: P09 · S619: P08 P10 · S734: P03

<a id="f18-cottage-thatched-large"></a>
**18. `cottage_thatched_large`** (16 IDs)  
S409: P12 P14 · S437: P12 P21 · S468: P04 P05 · S469: P02 P05 · S470: P01 P03 · S501: P02 · S587: P05 · S618: P01 P12 · S619: P03 P07

<a id="f19-cottage-thatched-small"></a>
**19. `cottage_thatched_small`** (16 IDs)  
S274: P02 P03 · S469: P01 · S497: P05 P06 · S500: P12 · S501: P01 P03 P05 P09 · S532: P01 P10 · S537: P04 P23 · S619: P02 P11

<a id="f20-dragon"></a>
**20. `dragon`** (16 IDs)  
S074: P21 P22 · S123: P07 · S124: P03 P04 · S127: P07 P08 P09 P10 · S156: P08 · S159: P06 P07 P08 P09 · S160: P06 · S191: P11

<a id="f21-town-roof-dormer"></a>
**21. `town_roof_dormer`** (16 IDs)  
S187: P07 P09 · S218: P21 · S219: P01 P03 · S465: P03 · S466: P04 · S472: P10 · S473: P05 P08 · S474: P21 · S498: P08 · S505: P07 · S506: P08 P25 · S538: P06

<a id="f22-door-wood-wide"></a>
**22. `door_wood_wide`** (15 IDs)  
S350: P09 · S440: P06 · S469: P20 · S497: P13 P15 · S498: P10 · S501: P12 · S504: P15 · S505: P01 · S532: P11 · S537: P24 · S538: P21 · S585: P13 · S618: P11 · S619: P12

<a id="f23-island-fence-lattice"></a>
**23. `island_fence_lattice`** (15 IDs)  
S489: P03 · S711: P07 · S712: P03 · S731: P03 P10 P11 P12 P13 P14 · S732: P02 · S762: P08 P09 · S763: P07 P20 · S764: P09

<a id="f24-town-roof-slope"></a>
**24. `town_roof_slope`** (15 IDs)  
S186: P23 · S187: P10 · S218: P20 · S385: P16 · S388: P14 · S465: P07 · S467: P03 · S472: P06 · S474: P22 · S507: P07 · S553: P02 P05 · S554: P03 P06 · S555: P02

<a id="f25-arrow-prop"></a>
**25. `arrow_prop`** (14 IDs)  
S097: P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 · S663: P20 P21 P22 P23

<a id="f26-chest-small"></a>
**26. `chest_small`** (14 IDs)  
S005: P28 · S069: P02 · S101: P02 · S184: P02 · S209: P05 · S276: P04 · S282: P06 · S288: P03 · S395: P03 · S536: P29 · S557: P05 · S671: P65 · S685: P07 · S747: P01

<a id="f27-fence-rail-diag-nw"></a>
**27. `fence_rail_diag_nw`** (14 IDs)  
S409: P19 P20 P21 P42 · S437: P08 P09 P10 P11 P13 P14 P15 P34 · S568: P13 P14

<a id="f28-stone-giant"></a>
**28. `stone_giant`** (14 IDs)  
S178: P10 P11 · S182: P13 · S183: P12 · S209: P14 P16 · S211: P01 · S212: P08 · S213: P10 · S215: P11 · S242: P15 · S245: P01 P02 · S246: P03

<a id="f29-town-roof-ridge-cap"></a>
**29. `town_roof_ridge_cap`** (14 IDs)  
S186: P51 · S187: P12 · S385: P18 · S388: P18 · S465: P04 · S467: P04 · S472: P02 · S474: P23 · S507: P08 · S553: P03 P07 · S554: P02 P05 · S555: P05

<a id="f30-bonca-brown"></a>
**30. `bonca_brown`** (12 IDs)  
S029: P03 P04 P05 P06 P07 · S100: P35 · S302: P06 P07 · S306: P06 · S562: P03 · S583: P10 · S648: P07

<a id="f31-castle-wall-corner"></a>
**31. `castle_wall_corner`** (12 IDs)  
S016: P04 P05 · S017: P02 P03 · S018: P03 · S070: P04 · S337: P02 P04 · S369: P01 P02 · S370: P04 · S402: P09

<a id="f32-island-hut-round"></a>
**32. `island_hut_round`** (12 IDs)  
S489: P02 · S680: P10 · S681: P12 · S712: P13 · S732: P01 · S748: P01 · S762: P01 · S763: P02 P03 P05 · S764: P02 P03

<a id="f33-slime-green"></a>
**33. `slime_green`** (11 IDs)  
S546: P13 P14 P15 P16 P17 P18 P19 P20 · S610: P12 P13 P14

<a id="f34-cave-hole-warp"></a>
**34. `cave_hole_warp`** (10 IDs)  
S085: P01 · S112: P02 · S144: P04 · S182: P01 · S209: P01 · S248: P01 · S254: P04 · S483: P11 · S625: P05 · S671: P01

<a id="f35-island-totem-pole"></a>
**35. `island_totem_pole`** (10 IDs)  
S100: P01 · S366: P07 P08 · S684: P01 · S713: P09 · S716: P01 P02 · S762: P10 P11 P12

<a id="f36-bonca-purple"></a>
**36. `bonca_purple`** (9 IDs)  
S514: P15 P16 · S515: P14 · S547: P14 P16 P17 · S577: P14 P15 · S609: P13

<a id="f37-fire-fx"></a>
**37. `fire_fx`** (9 IDs)  
S001: P21 P27 P30 P31 P32 · S439: P05 P09 P11 P21

<a id="f38-log-cabin-window"></a>
**38. `log_cabin_window`** (9 IDs)  
S251: P08 · S274: P16 · S409: P11 · S440: P08 P09 · S500: P05 · S501: P07 P08 · S530: P05

<a id="f39-stairs-wood"></a>
**39. `stairs_wood`** (9 IDs)  
S003: P28 P29 · S004: P13 · S036: P27 · S037: P13 · S163: P27 P28 · S228: P23 · S229: P01

<a id="f40-fish"></a>
**40. `fish`** (8 IDs)  
S634: P01 P02 P03 · S665: P03 · S697: P02 P03 P04 · S727: P17

<a id="f41-gold-coin"></a>
**41. `gold_coin`** (8 IDs)  
S505: P15 · S537: P10 P11 P12 P13 · S663: P03 P17 P18

<a id="f42-ground-crack"></a>
**42. `ground_crack`** (8 IDs)  
S005: P19 · S066: P29 · S154: P03 P04 P06 P09 P10 · S193: P23

<a id="f43-island-torch"></a>
**43. `island_torch`** (8 IDs)  
S731: P02 · S762: P02 · S763: P06 P18 P19 · S764: P04 P05 P07

<a id="f44-pig"></a>
**44. `pig`** (8 IDs)  
S031: P04 · S587: P14 · S636: P05 P06 P07 · S694: P01 P02 P03

<a id="f45-bridge-wood-rail-plank"></a>
**45. `bridge_wood_rail_plank`** (7 IDs)  
S404: P01 P04 · S512: P03 P04 P05 · S693: P28 P29

<a id="f46-bridge-wood-rail-rope"></a>
**46. `bridge_wood_rail_rope`** (7 IDs)  
S404: P03 P05 · S512: P06 P07 P08 · S693: P30 P31

<a id="f47-cottage-thatched-two-storey"></a>
**47. `cottage_thatched_two_storey`** (7 IDs)  
S440: P03 P11 · S500: P01 P02 · S586: P04 · S618: P02 P10

<a id="f48-wall-stripe-red"></a>
**48. `wall_stripe_red`** (7 IDs)  
S097: P35 P36 P37 P38 P39 P40 P41

<a id="f49-cottage-thatched-l-shape"></a>
**49. `cottage_thatched_l_shape`** (6 IDs)  
S318: P01 · S349: P04 · S350: P01 P02 · S734: P01 P02

<a id="f50-fence-rail-diag-ne"></a>
**50. `fence_rail_diag_ne`** (6 IDs)  
S441: P05 P12 P13 P14 · S469: P07 P08

<a id="f51-goblin-soldier"></a>
**51. `goblin_soldier`** (6 IDs)  
S680: P11 P12 · S712: P15 P17 · S713: P11 P12

<a id="f52-small-fire-fx"></a>
**52. `small_fire_fx`** (6 IDs)  
S001: P35 P36 P38 · S439: P31 P32 P33

<a id="f53-ground-hole-dark"></a>
**53. `ground_hole_dark`** (10 IDs)  
S132: P01 · S180: P01 · S209: P04 · S243: P13 · S277: P02 · SW_s1-hole3_L22@S209_P04 · SW_s1-hole_L21@S132_P01 · SW_s1-hole_L21@S277_P02 · SW_s6-hole2_L22@S180_P01 · SW_s6-hole_L22@S243_P13

<a id="f54-chimney-stone"></a>
**54. `chimney_stone`** (5 IDs)  
S469: P03 P04 · S500: P03 · S530: P10 · S734: P04

<a id="f55-shop-sign"></a>
**55. `shop_sign`** (5 IDs)  
S498: P13 P14 · S504: P17 · S538: P22 · S539: P05

<a id="f56-well-stone"></a>
**56. `well_stone`** (5 IDs)  
S408: P07 · S432: P03 · S497: P09 · S600: P01 · S766: P04

<a id="f57-tree-pine-large"></a>
**57. `tree_pine_large`** (7 IDs)  
S307: P13 · S534: P10 · S659: P06 · S710: P14 · SW_s2-sec1_L37@S307_P13 · SW_s2-sec3_L37@S659_P06 · SW_s3-sec1_L39@S710_P14

<a id="f58-npc-knight-silver"></a>
**58. `npc_knight_silver`** (6 IDs)  
S402: P03 P05 · S408: P04 · S568: P06 · SW_s2-ca-g_L179@S402_P03 · SW_s2-ca-g_L179@S402_P05

<a id="f59-boulder-flat"></a>
**59. `boulder_flat`** (4 IDs)  
S535: P12 · S590: P03 P10 P11

<a id="f60-bridge-stone"></a>
**60. `bridge_stone`** (4 IDs)  
S102: P01 P02 P03 P04

<a id="f61-cottage-thatched-long"></a>
**61. `cottage_thatched_long`** (4 IDs)  
S530: P01 P03 · S617: P01 P13

<a id="f62-fish-flopping"></a>
**62. `fish_flopping`** (4 IDs)  
S734: P09 · S760: P01 P02 P03

<a id="f63-food-fruit"></a>
**63. `food_fruit`** (4 IDs)  
S070: P31 P35 P36 P37

<a id="f64-goblin-hammer"></a>
**64. `goblin_hammer`** (4 IDs)  
S680: P13 P14 · S712: P12 · S748: P03

<a id="f65-island-hut-two-storey"></a>
**65. `island_hut_two_storey`** (4 IDs)  
S680: P09 · S681: P13 · S763: P04 · S764: P01

<a id="f66-npc-girl"></a>
**66. `npc_girl`** (4 IDs)  
S091: P22 · S122: P10 · S126: P06 P07

<a id="f67-npc-knight-red"></a>
**67. `npc_knight_red`** (4 IDs)  
S149: P05 P09 · S374: P03 P04

<a id="f68-poster-hark"></a>
**68. `poster_hark`** (4 IDs)  
S033: P30 · S195: P30 · S225: P30 · S226: P30

<a id="f69-bomb-item"></a>
**69. `bomb_item`** (3 IDs)  
S228: P40 P41 P42

<a id="f70-cabinet-wood"></a>
**70. `cabinet_wood`** (3 IDs)  
S003: P15 P16 · S366: P15

<a id="f71-church"></a>
**71. `church`** (3 IDs)  
S187: P02 · S188: P03 P05

<a id="f72-church-stained-glass"></a>
**72. `church_stained_glass`** (3 IDs)  
S188: P07 P08 P09

<a id="f73-fireplace-brick"></a>
**73. `fireplace_brick`** (3 IDs)  
S038: P16 · S129: P24 · S163: P23

<a id="f74-pillbug-corpse"></a>
**74. `pillbug_corpse`** (3 IDs)  
S098: P04 · S100: P25 P26

<a id="f75-boulder-large"></a>
**75. `boulder_large`** (2 IDs)  
S277: P03 · S590: P01

<a id="f76-boulder-red"></a>
**76. `boulder_red`** (2 IDs)  
S536: P15 · S590: P04

<a id="f77-burnt-floor-hole"></a>
**77. `burnt_floor_hole`** (2 IDs)  
S439: P34 P38

<a id="f78-castle-wall-end"></a>
**78. `castle_wall_end`** (2 IDs)  
S016: P03 · S048: P05

<a id="f79-cellar-hatch"></a>
**79. `cellar_hatch`** (2 IDs)  
S068: P24 P25

<a id="f80-chest-large"></a>
**80. `chest_large`** (2 IDs)  
S098: P07 · S536: P31

<a id="f81-chest-medium"></a>
**81. `chest_medium`** (2 IDs)  
S026: P06 · S284: P04

<a id="f82-church-window-small"></a>
**82. `church_window_small`** (2 IDs)  
S187: P01 P03

<a id="f83-dragon-corpse"></a>
**83. `dragon_corpse`** (2 IDs)  
S100: P34 · S238: P12

<a id="f84-duck-corpse"></a>
**84. `duck_corpse`** (2 IDs)  
S100: P27 · S521: P05

<a id="f85-explosion-fx"></a>
**85. `explosion_fx`** (2 IDs)  
S001: P28 P29

<a id="f86-fire-burst-fx"></a>
**86. `fire_burst_fx`** (2 IDs)  
S001: P33 P41

<a id="f87-fireball-fx"></a>
**87. `fireball_fx`** (2 IDs)  
S366: P09 P14

<a id="f88-food-pie"></a>
**88. `food_pie`** (2 IDs)  
S070: P24 P25

<a id="f89-fountain-spray-fx"></a>
**89. `fountain_spray_fx`** (2 IDs)  
S260: P30 · S586: P14

<a id="f90-hearth-fire"></a>
**90. `hearth_fire`** (2 IDs)  
S001: P20 · S163: P24

<a id="f91-log-cabin"></a>
**91. `log_cabin`** (2 IDs)  
S251: P01 · S270: P07

<a id="f92-log-cabin-door"></a>
**92. `log_cabin_door`** (2 IDs)  
S251: P07 · S409: P13

<a id="f93-npc-knight-red-attacking"></a>
**93. `npc_knight_red_attacking`** (2 IDs)  
S241: P03 · S242: P03

<a id="f94-npc-merchant-blue"></a>
**94. `npc_merchant_blue`** (2 IDs)  
S290: P30 · S374: P05

<a id="f95-npc-merchant-green"></a>
**95. `npc_merchant_green`** (2 IDs)  
S164: P02 · S227: P02

<a id="f96-npc-peasant"></a>
**96. `npc_peasant`** (2 IDs)  
S003: P23 · S038: P22

<a id="f97-sparkle-fx"></a>
**97. `sparkle_fx`** (2 IDs)  
S001: P37 · S045: P01

<a id="f98-tree-willow"></a>
**98. `tree_willow`** (2 IDs)  
S414: P02 · S446: P02

<a id="f99-tree-willow-large"></a>
**99. `tree_willow_large`** (2 IDs)  
S149: P02 · S474: P01

<a id="f100-boulder-grey-tall"></a>
**100. `boulder_grey_tall`** (1 IDs)  
S601: P08

<a id="f101-boulder-white-pair"></a>
**101. `boulder_white_pair`** (1 IDs)  
S590: P02

<a id="f102-burn-damage-decal"></a>
**102. `burn_damage_decal`** (1 IDs)  
S439: P29

<a id="f103-castle-door"></a>
**103. `castle_door`** (1 IDs)  
S402: P04

<a id="f104-castle-drawbridge"></a>
**104. `castle_drawbridge`** (1 IDs)  
S080: P05

<a id="f105-castle-gatehouse"></a>
**105. `castle_gatehouse`** (1 IDs)  
S080: P04

<a id="f106-church-door"></a>
**106. `church_door`** (1 IDs)  
S188: P06

<a id="f107-corpse-mom"></a>
**107. `corpse_mom`** (1 IDs)  
S001: P34

<a id="f108-corpse-soldier"></a>
**108. `corpse_soldier`** (1 IDs)  
S086: P01

<a id="f109-dink-dead"></a>
**109. `dink_dead`** (1 IDs)  
S058: P06

<a id="f110-food-bread"></a>
**110. `food_bread`** (1 IDs)  
S070: P33

<a id="f111-food-cheese"></a>
**111. `food_cheese`** (1 IDs)  
S070: P26

<a id="f112-food-drumstick"></a>
**112. `food_drumstick`** (1 IDs)  
S070: P23

<a id="f113-food-grapes"></a>
**113. `food_grapes`** (1 IDs)  
S070: P30

<a id="f114-food-ham"></a>
**114. `food_ham`** (1 IDs)  
S070: P32

<a id="f115-king-on-throne"></a>
**115. `king_on_throne`** (1 IDs)  
S070: P03

<a id="f116-npc-gnome-purple"></a>
**116. `npc_gnome_purple`** (1 IDs)  
S006: P23

<a id="f117-npc-maiden-blue"></a>
**117. `npc_maiden_blue`** (1 IDs)  
S004: P16

<a id="f118-npc-maiden-brown"></a>
**118. `npc_maiden_brown`** (1 IDs)  
S410: P06

<a id="f119-npc-maiden-red"></a>
**119. `npc_maiden_red`** (1 IDs)  
S122: P09

<a id="f120-npc-old-man"></a>
**120. `npc_old_man`** (1 IDs)  
S002: P23

<a id="f121-npc-soldier"></a>
**121. `npc_soldier`** (1 IDs)  
S410: P07

<a id="f122-ore-rock-blue"></a>
**122. `ore_rock_blue`** (1 IDs)  
S590: P09

<a id="f123-poster-wanted"></a>
**123. `poster_wanted`** (1 IDs)  
S035: P27

<a id="f124-snow-house-door"></a>
**124. `snow_house_door`** (1 IDs)  
S149: P07

<a id="f125-snow-house-lower"></a>
**125. `snow_house_lower`** (1 IDs)  
S149: P03

<a id="f126-snow-house-roof"></a>
**126. `snow_house_roof`** (1 IDs)  
S149: P08

<a id="f127-snow-house-timber"></a>
**127. `snow_house_timber`** (1 IDs)  
S149: P06

<a id="f128-thorn-branch"></a>
**128. `thorn_branch`** (1 IDs)  
S192: P05

<a id="f129-tree-oak-large"></a>
**129. `tree_oak_large`** (1 IDs)  
S693: P06

<a id="f130-screen-ground-tile-layer"></a>
**130. `screen ground (tile layer)`** (303 IDs)  
SCR 002 003 004 005 006 013 014 015 016 017 018 025 026 027 028 029 030 031 032 033 034 035 036 037 038 045 046 047 048 049 050 057 058 059 060 061 062 063 064 065 066 067 068 069 077 078 079 080 081 082 085 086 089 090 092 093 094 095 096 097 098 099 100 101 109 110 111 112 113 114 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 143 145 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 177 178 179 180 181 182 183 184 185 188 189 190 192 193 194 195 196 197 198 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 241 242 243 244 245 246 247 248 249 250 251 252 254 255 256 257 258 259 260 261 273 274 275 276 277 278 279 280 281 283 284 285 286 287 288 289 290 302 309 310 316 317 318 319 320 339 340 341 342 343 348 349 371 373 374 375 377 385 396 397 410 426 427 428 430 431 432 442 444 445 458 459 460 461 465 490 491 492 493 494 495 496 505 510 520 523 524 525 526 527 528 531 532 534 535 540 542 552 557 558 559 562 563 564 565 566 567 573 579 589 590 591 593 594 595 596 598 606 616 620 621 622 623 624 625 627 630 631 633 637 648 649 652 653 654 655 657 662 664 667 683 684 685 686 687 694 696 713 717 718 719 735 736 749 750 765 766 767
