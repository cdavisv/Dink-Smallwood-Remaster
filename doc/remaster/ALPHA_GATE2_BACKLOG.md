# Alpha gate 2 backlog: origin IDs still open

Generated 2026-11-12 by `DinkRemasterUE/Scripts/gate2_backlog.py` from `Saved/Import/coverage.csv` (6607 rows, importer run of 2026-11-12) and the manifests under `Content/Dink/Data/Art/`, classified by `Scripts/art_coverage.py`. Do not edit by hand; regenerate.

Alpha gate 2 (`doc/remaster/REMASTER_PLAN.md`): every origin ID is final, placeholder or cut with a reason. This list is what is still open: every origin ID whose art state in `Scripts/art_coverage.py` is `placeholder` (no art bound; nothing in the repo records a placeholder as owner-accepted), plus any unclassified ID. Final (bespoke or by family, `Content/Dink/Data/Art/families.json`) and cut (owner decision of 9 Nov 2026) are closed and not listed.

## Summary

| | open |
|---|---:|
| sprite families | 152 |
| origin IDs | 2438 |
| map placements | 1786 |
| screens (ground tile layer) | 639 |
| script warps with their own ID | 13 |
| unclassified IDs | 0 |

Claimed by the Claude photoreal pass (in progress elsewhere, not final): **70 families, 2014 origin IDs, 1369 placements**. Unclaimed: 82 families, 424 origin IDs, 417 placements.

Largest family by origin IDs: `screen ground (tile layer)` (639 IDs, 0 map placements, so it sorts at #152).

Largest families no stream has claimed: `blood_splat` 46, `tree_fruit` 34, `burn_hole_decal` 26, `bonca_gray` 21, `slayer` 21, `npc_knight_blue` 18, `dragon` 16, `arrow_prop` 14, `stone_giant` 14, `bonca_brown` 12.

Closed for comparison (art_coverage rows): final bespoke 143, final by family 3829, cut 152, placeholder 2483 of 6607 rows.

## How to regenerate

```bash
cd DinkRemasterUE && python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md
```

Run it in the editor's checkout: like `art_coverage.py` it needs the importer's `Saved/Import/coverage.csv` (`Scripts/import_greybox.sh --region all`), `tools/dinkex/out/sequences.json` and the gitignored engine template content under `Content/Characters` (the mother's locomotion). From another worktree add `--project <editor checkout>/DinkRemasterUE`. The photoreal column is a snapshot of `<--photoreal-root>/*/manifest.json` (default: the uncommitted photoreal pass work copy), read-only; regenerate after that pass lands or binds families.

## Backlog by sprite family

Sorted by open map placements. Family is the class id (`tools/data/sprite_classes.csv`, the key `families.json` binds); *what the original shows* gives its name, sprite group, size and the reference sheet in `doc/remaster/reference/`; *sequences* are the original sprite sequences of the open placements. The origin IDs of each family are listed under [Open origin IDs](#open-origin-ids).

| # | family | what the original sprite sheet shows | sequences (open placements) | origin IDs | placements | photoreal pass |
|---:|---|---|---|---:|---:|---|
| 1 | [`pillbug`](#f1-pillbug) | Pillbug (pillbug, 47x42 px) | seq 133 (89), seq 131 (65) | 154 | 154 | Creatures |
| 2 | [`thorn_bush`](#f2-thorn-bush) | Thorn bramble (graveyard, 102x80 px) | seq 90 (138) | 138 | 138 | Vegetation |
| 3 | [`duck`](#f3-duck) | Duck (duck, 31x41 px) | seq 23 (24), seq 29 (18), seq 24 (14), seq 26 (12), seq 27 (12), seq 21 (11) | 92 | 91 | Creatures |
| 4 | [`duck_head`](#f4-duck-head) | Duck head (death sprite) used as set dressing (duck, 15x42 px) | seq 121 (90) | 90 | 90 | Creatures |
| 5 | [`town_wall_stone_window`](#f5-town-wall-stone-window) | Stone ground-floor wall (windows / plain) (town_house_kit, 100x132 px) | seq 33 (80) | 80 | 80 | TownExteriors |
| 6 | [`slime_blue`](#f6-slime-blue) | Slime (blue) (slime, 24x18 px) | seq 651 (67) | 67 | 67 | Creatures |
| 7 | [`seashell_clam`](#f7-seashell-clam) | Clam shell (beach, 19x14 px) | seq 92 (66) | 66 | 66 | Terrain |
| 8 | [`town_roof_flat`](#f8-town-roof-flat) | Shingle roof section (town_house_kit, 100x200 px) | seq 33 (54) | 54 | 54 | TownExteriors |
| 9 | [`starfish`](#f9-starfish) | Starfish (beach, 25x17 px) | seq 92 (47) | 47 | 47 | Terrain |
| 10 | [`blood_splat`](#f10-blood-splat) | Blood splatter (blood, 39x56 px) | seq 188 (24), seq 189 (18), seq 187 (4) | 46 | 46 | - |
| 11 | [`castle_wall_diag`](#f11-castle-wall-diag) | Castle curtain wall (diagonal run) (castle_kit, 350x463 px) | seq 67 (46) | 46 | 46 | Structures |
| 12 | [`tree_fruit`](#f12-tree-fruit) | Fruit hanging in a tree (food, 7x12 px) | seq 421 (34) | 34 | 34 | - |
| 13 | [`sign_post`](#f13-sign-post) | Signpost (signs, 50x92 px) | seq 186 (30) | 30 | 30 | Structures |
| 14 | [`slime_red`](#f14-slime-red) | Slime (red) (slime, 25x18 px) | seq 693 (17), seq 691 (12) | 29 | 29 | Creatures |
| 15 | [`burn_hole_decal`](#f15-burn-hole-decal) | Burnt hole / scorch mark (damage, 23x20 px) | seq 158 (26) | 26 | 26 | - |
| 16 | [`bridge_wood_deck`](#f16-bridge-wood-deck) | Wooden bridge deck (bridge_wood, 65x88 px) | seq 58 (22) | 22 | 22 | Structures |
| 17 | [`bonca_gray`](#f17-bonca-gray) | Bonca (grey) (bonca, 97x91 px) | seq 601 (6), seq 603 (4), seq 609 (4), seq 592 (3), seq 607 (3), seq 594 (1) | 21 | 21 | - |
| 18 | [`slayer`](#f18-slayer) | Slayer (slayer, 113x105 px) | seq 632 (7), seq 641 (6), seq 634 (4), seq 643 (1), seq 649 (1), seq 647 (1), seq 636 (1) | 21 | 21 | - |
| 19 | [`town_wall_gable_end`](#f19-town-wall-gable-end) | Timbered gable end / tower corner (town_house_kit, 92x200 px) | seq 33 (21) | 21 | 21 | TownExteriors |
| 20 | [`door_wood_single`](#f20-door-wood-single) | Wooden door (doors, 24x64 px) | seq 61 (20) | 22 | 20 | Structures |
| 21 | [`castle_tower_round`](#f21-castle-tower-round) | Round castle tower (castle_kit, 193x409 px) | seq 67 (20) | 20 | 20 | Structures |
| 22 | [`npc_knight_blue`](#f22-npc-knight-blue) | Knight (blue) (npc_knight, 91x125 px) | seq 287 (8), seq 289 (8), seq 281 (1), seq 283 (1) | 18 | 18 | - |
| 23 | [`fence_rail_ns`](#f23-fence-rail-ns) | Rail fence (north-south) (fence_rail, 26x136 px) | seq 93 (17) | 17 | 17 | Structures |
| 24 | [`town_roof_slope`](#f24-town-roof-slope) | Shingle roof slope (town_house_kit, 100x150 px) | seq 33 (17) | 17 | 17 | TownExteriors |
| 25 | [`cottage_door`](#f25-cottage-door) | Cottage door (cottage_thatched, 55x89 px) | seq 63 (16) | 16 | 16 | Structures |
| 26 | [`cottage_thatched_large`](#f26-cottage-thatched-large) | Thatched stone cottage (cottage_thatched, 334x259 px) | seq 63 (16) | 16 | 16 | Structures |
| 27 | [`cottage_thatched_small`](#f27-cottage-thatched-small) | Thatched stone cottage (cottage_thatched, 257x225 px) | seq 63 (16) | 16 | 16 | Structures |
| 28 | [`dragon`](#f28-dragon) | Dragon (dragon, 164x188 px) | seq 202 (8), seq 206 (4), seq 204 (3), seq 208 (1) | 16 | 16 | - |
| 29 | [`town_roof_dormer`](#f29-town-roof-dormer) | Roof section with dormer window (town_house_kit, 100x200 px) | seq 33 (16) | 16 | 16 | TownExteriors |
| 30 | [`door_wood_wide`](#f30-door-wood-wide) | Wide wooden door (doors, 53x68 px) | seq 62 (15) | 15 | 15 | Structures |
| 31 | [`island_fence_lattice`](#f31-island-fence-lattice) | Lashed pole fence (island_village, 271x76 px) | seq 424 (15) | 15 | 15 | Structures |
| 32 | [`potion_red`](#f32-potion-red) | Red potion (magic) (potions, 19x52 px) | seq 56 (15) | 15 | 15 | Props |
| 33 | [`town_roof_ridge_cap`](#f33-town-roof-ridge-cap) | Roof ridge / corner cap (town_house_kit, 60x45 px) | seq 33 (15) | 15 | 15 | TownExteriors |
| 34 | [`town_wall_stone_door`](#f34-town-wall-stone-door) | Stone ground-floor wall with door (town_house_kit, 100x132 px) | seq 33 (15) | 15 | 15 | TownExteriors |
| 35 | [`arrow_prop`](#f35-arrow-prop) | Arrow (shop display / stuck in ground) (arrow, 47x30 px) | seq 25 (14) | 14 | 14 | - |
| 36 | [`chest_small`](#f36-chest-small) | Treasure chest (small) (chests, 44x60 px) | seq 175 (14) | 14 | 14 | Props |
| 37 | [`fence_rail_diag_nw`](#f37-fence-rail-diag-nw) | Rail fence diagonal (other) (fence_rail, 77x88 px) | seq 93 (14) | 14 | 14 | Structures |
| 38 | [`stone_giant`](#f38-stone-giant) | Stone giant (stone_giant, 104x88 px) | seq 821 (8), seq 823 (3), seq 816 (1), seq 829 (1), seq 827 (1) | 14 | 14 | - |
| 39 | [`bonca_brown`](#f39-bonca-brown) | Bonca (brown) (bonca, 85x94 px) | seq 542 (2), seq 544 (2), seq 533 (2), seq 539 (2), seq 537 (2), seq 531 (2) | 12 | 12 | - |
| 40 | [`castle_wall_corner`](#f40-castle-wall-corner) | Castle wall corner (castle_kit, 350x505 px) | seq 67 (12) | 12 | 12 | Structures |
| 41 | [`island_hut_round`](#f41-island-hut-round) | Koka Isle round hut (island_village, 208x178 px) | seq 424 (12) | 12 | 12 | Structures |
| 42 | [`potion_purple`](#f42-potion-purple) | Purple potion (potions, 19x52 px) | seq 57 (11) | 11 | 11 | Props |
| 43 | [`slime_green`](#f43-slime-green) | Slime (green) (slime, 26x23 px) | seq 671 (11) | 11 | 11 | Creatures |
| 44 | [`cave_hole_warp`](#f44-cave-hole-warp) | Hole into a cave (warp) (ground_holes, 55x31 px) | seq 89 (10) | 10 | 10 | - |
| 45 | [`island_totem_pole`](#f45-island-totem-pole) | Pole with skull/feather totem (island_village, 27x105 px) | seq 424 (10) | 10 | 10 | Structures |
| 46 | [`bonca_purple`](#f46-bonca-purple) | Bonca (purple) (bonca, 85x94 px) | seq 613 (6), seq 619 (1), seq 628 (1), seq 626 (1) | 9 | 9 | - |
| 47 | [`fire_fx`](#f47-fire-fx) | Fire (looping flames) (fire, 78x78 px) | seq 427 (9) | 9 | 9 | Props |
| 48 | [`log_cabin_window`](#f48-log-cabin-window) | Log cabin window (log_cabin, 24x28 px) | seq 59 (9) | 9 | 9 | - |
| 49 | [`potion_blue`](#f49-potion-blue) | Blue potion (strength/defense) (potions, 19x52 px) | seq 55 (8), seq 75 (1) | 9 | 9 | Props |
| 50 | [`stairs_wood`](#f50-stairs-wood) | Wooden stairs (stairs, 82x72 px) | seq 428 (9) | 9 | 9 | - |
| 51 | [`fish`](#f51-fish) | Fish (swimming) (fish, 72x52 px) | seq 434 (8) | 8 | 8 | - |
| 52 | [`gold_coin`](#f52-gold-coin) | Single coin (gold, 4x3 px) | seq 178 (8) | 8 | 8 | - |
| 53 | [`ground_crack`](#f53-ground-crack) | Crack in the ground (ground_holes, 88x33 px) | seq 89 (8) | 8 | 8 | - |
| 54 | [`island_torch`](#f54-island-torch) | Bamboo torch / pole (island_village, 85x105 px) | seq 425 (8) | 8 | 8 | Props |
| 55 | [`pig`](#f55-pig) | Pig (pig, 50x56 px) | seq 41 (5), seq 43 (2), seq 49 (1) | 8 | 8 | Creatures |
| 56 | [`bridge_wood_rail_plank`](#f56-bridge-wood-rail-plank) | Bridge side rail with planking (bridge_wood, 101x84 px) | seq 58 (7) | 7 | 7 | Structures |
| 57 | [`bridge_wood_rail_rope`](#f57-bridge-wood-rail-rope) | Bridge rope rail (bridge_wood, 101x93 px) | seq 58 (7) | 7 | 7 | Structures |
| 58 | [`cottage_thatched_two_storey`](#f58-cottage-thatched-two-storey) | Two-storey thatched cottage (cottage_thatched, 257x311 px) | seq 63 (7) | 7 | 7 | Structures |
| 59 | [`wall_stripe_red`](#f59-wall-stripe-red) | Red wall stripe / banner (built from the health-bar UI art) (signs, 24x17 px) | seq 450 (7) | 7 | 7 | - |
| 60 | [`cottage_thatched_l_shape`](#f60-cottage-thatched-l-shape) | L-shaped thatched cottage (cottage_thatched, 305x324 px) | seq 63 (6) | 6 | 6 | Structures |
| 61 | [`fence_rail_diag_ne`](#f61-fence-rail-diag-ne) | Rail fence diagonal (fence_rail, 69x90 px) | seq 93 (6) | 6 | 6 | Structures |
| 62 | [`goblin_soldier`](#f62-goblin-soldier) | Goblin soldier (goblin, 107x130 px) | seq 809 (3), seq 801 (2), seq 803 (1) | 6 | 6 | - |
| 63 | [`small_fire_fx`](#f63-small-fire-fx) | Small fire on floor (fire, 23x20 px) | seq 155 (2), seq 156 (2), seq 157 (2) | 6 | 6 | Props |
| 64 | [`ground_hole_dark`](#f64-ground-hole-dark) | Dark hole in the ground (ground_holes, 55x73 px) | seq 89 (5) | 10 | 5 | - |
| 65 | [`chimney_stone`](#f65-chimney-stone) | Stone chimney (cottage_thatched, 55x58 px) | seq 63 (5) | 5 | 5 | Structures |
| 66 | [`shop_sign`](#f66-shop-sign) | Hanging sign (red cross: healer) (signs, 63x76 px) | seq 458 (5) | 5 | 5 | - |
| 67 | [`weed_sprig`](#f67-weed-sprig) | Small weed sprig (ground_plants, 22x24 px) | seq 65 (5) | 5 | 5 | Vegetation |
| 68 | [`well_stone`](#f68-well-stone) | Stone well with roof (landmarks, 107x136 px) | seq 186 (5) | 5 | 5 | Structures |
| 69 | [`tree_pine_large`](#f69-tree-pine-large) | Pine tree (trees, 128x188 px) | seq 32 (4) | 7 | 4 | Vegetation |
| 70 | [`npc_knight_silver`](#f70-npc-knight-silver) | Knight (silver) (npc_knight, 110x117 px) | seq 293 (2), seq 299 (1), seq 291 (1) | 6 | 4 | - |
| 71 | [`boulder_flat`](#f71-boulder-flat) | Flat boulder (boulders, 72x63 px) | seq 95 (4) | 4 | 4 | - |
| 72 | [`bridge_stone`](#f72-bridge-stone) | Stone arch bridge (bridge_stone, 288x212 px) | seq 186 (4) | 4 | 4 | Structures |
| 73 | [`cottage_thatched_long`](#f73-cottage-thatched-long) | Thatched stone cottage (cottage_thatched, 332x260 px) | seq 63 (4) | 4 | 4 | Structures |
| 74 | [`fish_flopping`](#f74-fish-flopping) | Fish flopping on land (fish, 33x34 px) | seq 439 (3), seq 441 (1) | 4 | 4 | - |
| 75 | [`food_fruit`](#f75-food-fruit) | Fruit (apple / pear / etc.) (food, 17x23 px) | seq 421 (4) | 4 | 4 | - |
| 76 | [`goblin_hammer`](#f76-goblin-hammer) | Goblin (hammer) (goblin, 56x109 px) | seq 763 (2), seq 761 (1), seq 769 (1) | 4 | 4 | - |
| 77 | [`island_hut_two_storey`](#f77-island-hut-two-storey) | Two-tier round hut (island_village, 238x265 px) | seq 424 (4) | 4 | 4 | Structures |
| 78 | [`npc_girl`](#f78-npc-girl) | Girl (child) (npc_girl, 53x62 px) | seq 331 (3), seq 339 (1) | 4 | 4 | - |
| 79 | [`npc_knight_red`](#f79-npc-knight-red) | Knight (red) (npc_knight, 91x125 px) | seq 273 (2), seq 279 (1), seq 277 (1) | 4 | 4 | - |
| 80 | [`poster_hark`](#f80-poster-hark) | "Hark!" notice (signs, 43x61 px) | seq 462 (4) | 4 | 4 | - |
| 81 | [`bomb_item`](#f81-bomb-item) | Bomb (items, 26x33 px) | seq 420 (3) | 3 | 3 | - |
| 82 | [`cabinet_wood`](#f82-cabinet-wood) | Wooden cabinet / dresser (house_interior, 57x79 px) | seq 87 (3) | 3 | 3 | Props |
| 83 | [`church`](#f83-church) | Stone church (church, 417x433 px) | seq 60 (3) | 3 | 3 | - |
| 84 | [`church_stained_glass`](#f84-church-stained-glass) | Stained-glass window (church, 56x94 px) | seq 60 (3) | 3 | 3 | - |
| 85 | [`dragon_corpse`](#f85-dragon-corpse) | Dead dragon (dragon, 105x122 px) | seq 212 (2), seq 216 (1) | 3 | 3 | - |
| 86 | [`fireplace_brick`](#f86-fireplace-brick) | Brick fireplace (house_interior, 97x114 px) | seq 64 (3) | 3 | 3 | Props |
| 87 | [`pillbug_corpse`](#f87-pillbug-corpse) | Pillbug death splat (pillbug, 46x35 px) | seq 141 (2), seq 143 (1) | 3 | 3 | Creatures |
| 88 | [`boulder_large`](#f88-boulder-large) | Large dark boulder (boulders, 103x95 px) | seq 95 (2) | 2 | 2 | - |
| 89 | [`boulder_red`](#f89-boulder-red) | Reddish boulder (boulders, 100x79 px) | seq 95 (2) | 2 | 2 | - |
| 90 | [`burnt_floor_hole`](#f90-burnt-floor-hole) | Burnt hole in floor/roof (large) (damage, 90x69 px) | seq 158 (2) | 2 | 2 | - |
| 91 | [`castle_wall_end`](#f91-castle-wall-end) | Castle wall end (edge-on) (castle_kit, 100x340 px) | seq 67 (2) | 2 | 2 | Structures |
| 92 | [`cellar_hatch`](#f92-cellar-hatch) | Cellar hatch / ladder (stairs, 35x57 px) | seq 428 (2) | 2 | 2 | - |
| 93 | [`chest_large`](#f93-chest-large) | Treasure chest (large) (chests, 60x60 px) | seq 177 (2) | 2 | 2 | Props |
| 94 | [`chest_medium`](#f94-chest-medium) | Treasure chest (chests, 44x55 px) | seq 176 (2) | 2 | 2 | Props |
| 95 | [`church_window_small`](#f95-church-window-small) | Church small window (church, 19x27 px) | seq 60 (2) | 2 | 2 | - |
| 96 | [`corpse_merchant`](#f96-corpse-merchant) | Dead merchant (npc_merchant, 74x53 px) | seq 385 (1), seq 345 (1) | 2 | 2 | - |
| 97 | [`duck_corpse`](#f97-duck-corpse) | Dead duck body (duck, 20x30 px) | seq 127 (1), seq 121 (1) | 2 | 2 | Creatures |
| 98 | [`explosion_fx`](#f98-explosion-fx) | Explosion (, 60x61 px) | seq 70 (2) | 2 | 2 | - |
| 99 | [`fire_burst_fx`](#f99-fire-burst-fx) | Fire burst (atomic explosion frames) (, 93x141 px) | seq 161 (2) | 2 | 2 | - |
| 100 | [`fireball_fx`](#f100-fireball-fx) | Fireball (vertical) (, 32x76 px) | seq 512 (2) | 2 | 2 | - |
| 101 | [`food_pie`](#f101-food-pie) | Pie (food, 24x19 px) | seq 421 (2) | 2 | 2 | Props |
| 102 | [`fountain_spray_fx`](#f102-fountain-spray-fx) | Fountain water spray (fountain, 80x84 px) | seq 94 (2) | 2 | 2 | - |
| 103 | [`hearth_fire`](#f103-hearth-fire) | Fireplace fire (house_interior, 46x55 px) | seq 86 (2) | 2 | 2 | - |
| 104 | [`log_cabin`](#f104-log-cabin) | Log cabin (log_cabin, 322x232 px) | seq 59 (2) | 2 | 2 | - |
| 105 | [`log_cabin_door`](#f105-log-cabin-door) | Log cabin door (log_cabin, 34x69 px) | seq 59 (2) | 2 | 2 | - |
| 106 | [`npc_knight_red_attacking`](#f106-npc-knight-red-attacking) | Knight (red) attack pose (npc_knight, 121x127 px) | seq 712 (2) | 2 | 2 | - |
| 107 | [`npc_merchant_blue`](#f107-npc-merchant-blue) | Merchant (blue) (npc_merchant, 55x93 px) | seq 371 (2) | 2 | 2 | - |
| 108 | [`npc_merchant_green`](#f108-npc-merchant-green) | Merchant (green) (npc_merchant, 55x93 px) | seq 381 (2) | 2 | 2 | - |
| 109 | [`npc_peasant`](#f109-npc-peasant) | Peasant (npc_peasant, 73x121 px) | seq 411 (2) | 2 | 2 | - |
| 110 | [`sparkle_fx`](#f110-sparkle-fx) | Sparkle (, 20x20 px) | seq 165 (1), seq 166 (1) | 2 | 2 | - |
| 111 | [`table_round`](#f111-table-round) | Round table (house_interior, 65x62 px) | seq 87 (2) | 2 | 2 | Props |
| 112 | [`tree_willow`](#f112-tree-willow) | Weeping (willow-like) tree (trees, 169x252 px) | seq 32 (2) | 2 | 2 | Vegetation |
| 113 | [`tree_willow_large`](#f113-tree-willow-large) | Large weeping tree (trees, 249x300 px) | seq 32 (2) | 2 | 2 | Vegetation |
| 114 | [`weed_small`](#f114-weed-small) | Small weed / seedling (ground_plants, 20x22 px) | seq 65 (2) | 2 | 2 | Vegetation |
| 115 | [`boulder_grey_tall`](#f115-boulder-grey-tall) | Tall grey boulder (boulders, 54x77 px) | seq 95 (1) | 1 | 1 | - |
| 116 | [`boulder_white_pair`](#f116-boulder-white-pair) | Pair of white boulders (boulders, 80x58 px) | seq 95 (1) | 1 | 1 | - |
| 117 | [`burn_damage_decal`](#f117-burn-damage-decal) | Burn damage / scorch with fire (damage, 90x69 px) | seq 154 (1) | 1 | 1 | - |
| 118 | [`bush_round_large`](#f118-bush-round-large) | Bush (bushes, 116x69 px) | seq 179 (1) | 1 | 1 | Vegetation |
| 119 | [`bush_round_medium`](#f119-bush-round-medium) | Bush (bushes, 80x54 px) | seq 179 (1) | 1 | 1 | Vegetation |
| 120 | [`bush_small`](#f120-bush-small) | Bush (bushes, 85x65 px) | seq 179 (1) | 1 | 1 | Vegetation |
| 121 | [`castle_door`](#f121-castle-door) | Castle door (castle_kit, 63x145 px) | seq 68 (1) | 1 | 1 | - |
| 122 | [`castle_drawbridge`](#f122-castle-drawbridge) | Drawbridge with chains (castle_kit, 149x192 px) | seq 68 (1) | 1 | 1 | - |
| 123 | [`castle_gatehouse`](#f123-castle-gatehouse) | Castle gatehouse block (castle_kit, 335x389 px) | seq 67 (1) | 1 | 1 | Structures |
| 124 | [`church_door`](#f124-church-door) | Church door (church, 35x82 px) | seq 60 (1) | 1 | 1 | - |
| 125 | [`corpse_girl`](#f125-corpse-girl) | Dead girl (npc_girl, 58x37 px) | seq 335 (1) | 1 | 1 | - |
| 126 | [`corpse_knight`](#f126-corpse-knight) | Dead knight (npc_knight, 81x55 px) | seq 275 (1) | 1 | 1 | - |
| 127 | [`corpse_maiden`](#f127-corpse-maiden) | Dead woman (npc_maiden, 63x47 px) | seq 245 (1) | 1 | 1 | - |
| 128 | [`corpse_mom`](#f128-corpse-mom) | Dead mother (burnt house) (npc_mom, 68x50 px) | seq 355 (1) | 1 | 1 | - |
| 129 | [`corpse_peasant`](#f129-corpse-peasant) | Dead peasant (npc_peasant, 114x59 px) | seq 415 (1) | 1 | 1 | - |
| 130 | [`corpse_soldier`](#f130-corpse-soldier) | Dead soldier (npc_soldier, 74x57 px) | seq 405 (1) | 1 | 1 | - |
| 131 | [`dink_dead`](#f131-dink-dead) | Dink lying dead (cutscene pose) (dink, 104x90 px) | seq 436 (1) | 1 | 1 | - |
| 132 | [`food_bread`](#f132-food-bread) | Bread loaf (food, 30x25 px) | seq 421 (1) | 1 | 1 | - |
| 133 | [`food_cheese`](#f133-food-cheese) | Cheese (food, 21x19 px) | seq 421 (1) | 1 | 1 | - |
| 134 | [`food_drumstick`](#f134-food-drumstick) | Meat drumstick (food, 28x31 px) | seq 421 (1) | 1 | 1 | - |
| 135 | [`food_grapes`](#f135-food-grapes) | Grapes (food, 29x30 px) | seq 421 (1) | 1 | 1 | - |
| 136 | [`food_ham`](#f136-food-ham) | Ham / steak (food, 28x28 px) | seq 421 (1) | 1 | 1 | - |
| 137 | [`king_on_throne`](#f137-king-on-throne) | King Daniel on throne (seated) (npc_king, 124x119 px) | seq 421 (1) | 1 | 1 | - |
| 138 | [`npc_gnome_purple`](#f138-npc-gnome-purple) | Gnome / wizard (purple) (npc_gnome, 51x74 px) | seq 561 (1) | 1 | 1 | - |
| 139 | [`npc_maiden_blue`](#f139-npc-maiden-blue) | Woman (blue dress) (npc_maiden, 55x83 px) | seq 251 (1) | 1 | 1 | - |
| 140 | [`npc_maiden_brown`](#f140-npc-maiden-brown) | Woman (brown dress) (npc_maiden, 55x83 px) | seq 241 (1) | 1 | 1 | - |
| 141 | [`npc_maiden_red`](#f141-npc-maiden-red) | Woman (red dress) (npc_maiden, 55x83 px) | seq 221 (1) | 1 | 1 | - |
| 142 | [`npc_old_man`](#f142-npc-old-man) | Old man (npc_oldman, 67x74 px) | seq 231 (1) | 1 | 1 | - |
| 143 | [`npc_soldier`](#f143-npc-soldier) | Soldier (npc_soldier, 76x93 px) | seq 403 (1) | 1 | 1 | - |
| 144 | [`ore_rock_blue`](#f144-ore-rock-blue) | Blue crystal rock (boulders, 44x29 px) | seq 95 (1) | 1 | 1 | - |
| 145 | [`poster_wanted`](#f145-poster-wanted) | "Wanted" poster (signs, 43x61 px) | seq 462 (1) | 1 | 1 | - |
| 146 | [`snow_house_door`](#f146-snow-house-door) | House door (snow_house, 43x78 px) | seq 96 (1) | 1 | 1 | - |
| 147 | [`snow_house_lower`](#f147-snow-house-lower) | House lower walls (snow_house, 381x188 px) | seq 96 (1) | 1 | 1 | - |
| 148 | [`snow_house_roof`](#f148-snow-house-roof) | House pyramid roof (snow_house, 404x201 px) | seq 96 (1) | 1 | 1 | - |
| 149 | [`snow_house_timber`](#f149-snow-house-timber) | House timbered upper walls (snow_house, 400x179 px) | seq 96 (1) | 1 | 1 | - |
| 150 | [`thorn_branch`](#f150-thorn-branch) | Thorn branch (graveyard, 28x25 px) | seq 90 (1) | 1 | 1 | Vegetation |
| 151 | [`tree_oak_large`](#f151-tree-oak-large) | Broadleaf (oak) tree (trees, 204x270 px) | seq 32 (1) | 1 | 1 | Vegetation |
| 152 | [`screen ground (tile layer)`](#f152-screen-ground-tile-layer) | tile-layer ground of each screen (grass, sand, water, walls painted into tilesets) · sheet_tiles.png | - | 639 | 0 | Terrain |

## Open origin IDs

Placements as `Snnn: Pnn ...` (screen, then slot), screens as `SCR nnn ...`, script warps by full ID.

<a id="f1-pillbug"></a>
**1. `pillbug`** (154 IDs)  
S026: P07 · S027: P06 P08 · S030: P03 P04 P05 P06 P07 P08 P09 · S064: P08 · S106: P16 P17 · S191: P08 · S223: P07 P08 P09 P10 P11 P12 · S237: P08 P09 · S270: P05 P06 · S274: P18 · S278: P04 P05 · S279: P05 · S301: P05 P06 · S303: P06 · S306: P07 P08 · S309: P06 · S310: P05 · S311: P03 P04 · S334: P07 P11 P12 · S373: P03 P04 · S378: P07 P08 P09 · S395: P04 · S435: P02 · S437: P16 P17 P18 P19 P20 · S457: P04 P05 P06 · S474: P14 · S487: P07 · S488: P10 P11 · S519: P07 · S522: P03 P06 · S526: P04 P05 P06 P07 P08 · S527: P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 · S528: P04 P05 P06 · S550: P08 · S551: P01 P02 P03 · S552: P01 P02 P03 · S563: P03 P04 P05 P06 P07 P08 P09 P10 P11 · S584: P02 P03 · S599: P14 P15 P16 P18 · S608: P01 P02 P03 P04 P05 · S616: P04 P05 P06 · S621: P04 P05 P06 P07 · S624: P02 P06 · S626: P04 P05 P06 P07 · S647: P08 P09 · S648: P02 P03 P04 · S655: P03 P04 P05 P06 · S659: P08 · S666: P05 · S685: P03 P04 P05 P06 · S704: P01 · S715: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 · S735: P03 P04 P05 P06 P07 P08 · S736: P05

<a id="f2-thorn-bush"></a>
**2. `thorn_bush`** (138 IDs)  
S026: P01 P02 P04 P05 · S027: P02 P03 P04 P05 · S028: P02 · S029: P02 · S030: P02 · S031: P02 · S058: P02 P03 P04 P05 · S059: P01 P02 P04 P05 · S060: P02 P03 P04 P05 · S061: P02 P03 P04 P05 P06 · S062: P02 P03 P04 P05 P06 P07 P08 · S063: P02 P03 P04 P05 · S064: P02 P03 P05 · S090: P02 P03 P04 P05 · S091: P02 P03 P04 P05 · S095: P02 P03 P04 P05 · S096: P02 P03 P05 · S122: P01 P02 P03 P04 P05 P06 P07 P08 · S123: P05 · S124: P01 P02 · S125: P01 · S126: P01 · S127: P02 P03 P04 P05 · S128: P02 P03 P04 · S153: P01 · S154: P12 P13 P14 P15 P16 P18 P19 P20 P21 · S155: P02 P03 P04 P05 · S156: P02 P03 P04 · S157: P01 P02 P03 · S158: P02 P03 P04 P05 · S159: P02 P03 P04 P05 · S160: P02 P03 P05 · S189: P02 P03 P04 P05 · S190: P02 P03 P04 P05 · S191: P02 P03 P04 P05 · S192: P02 P03 P04 · S222: P02 P03 · S223: P02 P03 P04 P05 P06 · S224: P02 P03 P04 P05 · S254: P02 P03 · S255: P01

<a id="f3-duck"></a>
**3. `duck`** (92 IDs)  
S002: P24 · S100: P36 · S161: P33 P34 P35 P36 · S162: P25 · S190: P11 P12 P13 · S194: P26 · S196: P25 · S307: P08 P09 P10 P11 P12 P14 · S374: P06 P07 P08 P09 P10 P11 P12 P13 P14 · S397: P03 P04 P05 P06 P07 · S405: P01 · S440: P02 · S441: P11 · S504: P11 · S521: P04 · S532: P05 P06 P07 · S535: P06 · S536: P03 P04 P05 P06 P07 P08 P12 P13 P14 P17 P18 P19 P20 P21 P22 P23 P24 P25 P27 P30 P32 P33 P35 P38 P39 P40 P41 · S537: P14 · S564: P03 · S570: P02 P03 P04 · S585: P18 · S604: P01 P02 P03 P04 · S652: P03 · S656: P05 P06 · S699: P10 P11 · S700: P04 P06 P09 · S711: P08 P09 · S762: P29 P30 · S764: P13 · SW_s8-duck2_L59@S762_P30

<a id="f4-duck-head"></a>
**4. `duck_head`** (90 IDs)  
S145: P01 P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 P24 P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 P35 P36 P37 P38 P39 P40 P41 P42 P43 P44 P45 P46 P47 P48 P49 P50 P51 P52 P53 P54 P55 P56 P57 P58 P59 P60 P61 P62 P63 P64 P65 P66 P67 P68 P69 P70 P71 P72 P73 P74 P75 P76 P77 P78 P79 P80 P81 P82 P83 P84 P85 P86 P87 P88 P89 P90

<a id="f5-town-wall-stone-window"></a>
**5. `town_wall_stone_window`** (80 IDs)  
S218: P01 P13 P22 · S219: P05 P06 P08 P09 · S251: P04 P12 · S387: P07 · S388: P16 P17 · S417: P10 P11 P14 P15 P17 · S418: P02 P03 P04 P05 P08 P09 P10 · S419: P03 P04 P05 P06 P08 P09 · S420: P09 P10 P11 P12 · S465: P02 P08 · S466: P02 P03 P10 · S497: P01 P03 P04 · S498: P01 P03 P05 P06 P07 · S499: P05 P06 · S504: P01 P10 · S505: P02 P03 P04 P05 P08 · S506: P02 P04 P05 · S537: P01 P02 P03 · S538: P01 P07 P09 P10 P11 · S539: P02 · S570: P07 P08 · S585: P01 P03 P05 · S586: P01 P02 P12 P13 · S587: P02 P03 P04

<a id="f6-slime-blue"></a>
**6. `slime_blue`** (67 IDs)  
S032: P02 P03 P04 P05 P06 P07 · S064: P06 P07 · S123: P08 P10 · S191: P09 P10 · S347: P08 · S458: P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 · S512: P09 P10 P11 P12 · S599: P09 P11 P13 · S633: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 · S652: P01 · S672: P01 P02 P03 P04 P05 P06 P07 P08 P09 · S695: P06 P07 P08 P09 P10 P11 P12 P13 P14 P15

<a id="f7-seashell-clam"></a>
**7. `seashell_clam`** (66 IDs)  
S258: P10 · S351: P01 · S352: P06 · S385: P02 · S417: P07 · S449: P07 · S452: P03 · S481: P05 P06 · S482: P05 P06 · S483: P03 P04 · S484: P04 · S487: P05 P06 · S488: P05 · S518: P01 · S519: P01 · S520: P02 · S550: P01 P07 · S551: P06 · S582: P02 · S583: P03 P08 · S614: P07 · S615: P02 P03 P04 · S646: P01 P06 · S647: P04 · S678: P07 · S688: P03 · S699: P02 P03 · S701: P10 P11 · S710: P06 · S711: P03 · S720: P01 · S725: P04 · S727: P01 P02 P05 · S728: P05 · S730: P03 P04 P05 · S731: P05 · S732: P03 · S733: P01 P02 P03 · S734: P30 · S742: P06 · S743: P03 · S752: P03 · S759: P02 · S761: P05 · S762: P17 P18 · S763: P01 · S764: P10 · S765: P08

<a id="f8-town-roof-flat"></a>
**8. `town_roof_flat`** (54 IDs)  
S187: P08 · S219: P02 · S385: P13 P14 P17 · S386: P07 P08 P09 P10 P11 P12 P13 · S387: P08 P09 P10 P11 P12 P13 P14 · S388: P12 P13 · S417: P05 P13 · S418: P07 P11 P12 · S419: P01 P10 · S465: P01 · S466: P01 P05 P06 P07 P08 P09 · S467: P06 · S473: P02 P04 P06 P07 · S474: P20 · S498: P09 · S505: P06 P09 P10 · S506: P07 P24 P30 · S538: P02 P05 · S553: P06 P08 · S555: P03 P04

<a id="f9-starfish"></a>
**9. `starfish`** (47 IDs)  
S257: P09 · S351: P03 · S385: P01 · S388: P06 · S417: P06 · S449: P06 · S452: P02 · S481: P02 · S482: P02 · S483: P01 P02 · S484: P02 · S487: P04 · S488: P04 · S518: P07 · S519: P03 · S520: P04 · S550: P06 · S551: P04 · S582: P03 · S615: P08 P09 · S647: P02 P03 · S688: P02 · S701: P13 · S710: P04 P05 · S711: P02 · S727: P04 · S728: P01 P02 P04 P06 · S731: P01 P04 · S732: P04 P05 · S742: P05 · S743: P01 P02 · S752: P02 · S759: P03 · S761: P04 · S762: P13 · S763: P08 · S765: P09

<a id="f10-blood-splat"></a>
**10. `blood_splat`** (46 IDs)  
S060: P06 P07 · S061: P07 P08 · S091: P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 · S094: P02 P03 P04 P05 P06 P07 P08 · S122: P11 P12 P13 · S126: P02 P03 P04 P05 · S154: P22 P39 P40 P41 P42 P43 · S158: P06 · S190: P06 P07 P08 P09 · S191: P06 P07

<a id="f11-castle-wall-diag"></a>
**11. `castle_wall_diag`** (46 IDs)  
S014: P01 · S015: P01 P02 P03 · S016: P01 P02 P06 · S017: P01 · S018: P02 · S047: P01 P03 P04 · S048: P01 P02 P03 P04 P06 · S049: P01 P02 · S050: P01 · S070: P01 · S078: P01 · S079: P03 · S080: P01 P02 · S081: P01 · S336: P03 P04 · S367: P01 P04 · S368: P01 P03 P04 · S370: P02 · S399: P01 · S400: P01 P02 · S401: P01 P03 P04 · S402: P02 P07 P08 · S432: P01 · S433: P02 P05

<a id="f12-tree-fruit"></a>
**12. `tree_fruit`** (34 IDs)  
S442: P02 P04 P05 P06 P07 P08 P09 P10 P11 P12 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S474: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P15 P16 P17

<a id="f13-sign-post"></a>
**13. `sign_post`** (30 IDs)  
S065: P18 · S132: P02 · S184: P11 · S244: P61 · S253: P07 · S315: P04 · S366: P05 · S376: P08 · S403: P03 · S404: P10 · S437: P40 · S451: P08 · S467: P02 · S497: P16 · S499: P11 · S502: P17 · S504: P04 · S529: P01 · S532: P12 · S533: P20 · S568: P07 · S587: P06 P13 · S588: P03 P04 · S590: P08 · S625: P01 · S712: P11 · S748: P04 · S759: P06

<a id="f14-slime-red"></a>
**14. `slime_red`** (29 IDs)  
S192: P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S274: P10 · S658: P03 P04 P05 P06 P07 · S660: P04 P05 P06 P07 · S688: P07 P08

<a id="f15-burn-hole-decal"></a>
**15. `burn_hole_decal`** (26 IDs)  
S001: P44 P45 P46 P47 P48 P49 · S005: P25 P26 P27 · S066: P23 P24 · S439: P23 P24 P25 P26 P27 P28 P30 P36 P37 P46 · S533: P21 P22 P23 · S536: P16 P26

<a id="f16-bridge-wood-deck"></a>
**16. `bridge_wood_deck`** (22 IDs)  
S416: P01 P02 · S448: P01 P02 P03 P04 P05 P06 P07 · S480: P01 P02 P03 · S512: P01 P02 · S533: P01 P02 P03 P25 · S544: P01 P02 · S701: P01 P02

<a id="f17-bonca-gray"></a>
**17. `bonca_gray`** (21 IDs)  
S027: P10 · S074: P23 · S090: P06 P07 P08 P09 · S137: P18 · S156: P06 · S160: P07 P08 P09 · S170: P13 P14 · S480: P04 P05 · S583: P09 · S632: P11 P12 · S633: P16 · S696: P04 · S715: P01

<a id="f18-slayer"></a>
**18. `slayer`** (21 IDs)  
S028: P03 P04 · S035: P32 · S106: P18 · S127: P06 · S137: P17 · S138: P16 · S156: P07 · S157: P05 P06 P07 P08 · S166: P25 P26 · S448: P08 P09 · S652: P02 · S663: P04 · S695: P05 · S696: P02 P03

<a id="f19-town-wall-gable-end"></a>
**19. `town_wall_gable_end`** (21 IDs)  
S187: P11 · S218: P07 · S219: P04 · S385: P15 · S388: P15 · S417: P12 · S465: P05 · S467: P05 · S472: P04 · S474: P18 P19 · S499: P04 · S506: P06 · S507: P05 · S538: P03 · S539: P03 · S553: P01 P04 · S554: P01 P04 · S555: P01

<a id="f20-door-wood-single"></a>
**20. `door_wood_single`** (22 IDs)  
S188: P10 · S219: P10 · S251: P09 · S274: P07 · S409: P16 · S418: P16 · S419: P02 · S497: P12 · S498: P11 · S499: P07 · S500: P06 · S501: P11 · S506: P20 · S530: P11 · S539: P12 · S585: P14 · S587: P12 · S617: P15 · S619: P09 · S734: P31 · SW_s2-mdoor_L106@S530_P11 · SW_s2-mdoor_L82@S530_P11

<a id="f21-castle-tower-round"></a>
**21. `castle_tower_round`** (20 IDs)  
S018: P01 · S047: P02 · S049: P03 · S050: P02 · S070: P02 · S078: P02 · S079: P01 P04 · S080: P03 · S112: P01 · S336: P01 · S337: P05 · S367: P03 · S368: P07 · S369: P03 · S370: P01 · S399: P03 · S401: P02 · S402: P01 · S433: P01

<a id="f22-npc-knight-blue"></a>
**22. `npc_knight_blue`** (18 IDs)  
S070: P13 P14 P15 P16 P17 P18 · S102: P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 · S243: P11 P12

<a id="f23-fence-rail-ns"></a>
**23. `fence_rail_ns`** (17 IDs)  
S375: P02 P03 · S408: P21 P22 P23 P24 · S409: P08 P41 P52 · S441: P06 P07 P08 P31 · S469: P09 P10 · S536: P28 P42

<a id="f24-town-roof-slope"></a>
**24. `town_roof_slope`** (17 IDs)  
S186: P23 · S187: P10 · S218: P20 · S385: P16 · S388: P14 · S465: P07 · S467: P03 · S472: P06 · S474: P22 · S506: P26 · S507: P07 · S538: P04 · S553: P02 P05 · S554: P03 P06 · S555: P02

<a id="f25-cottage-door"></a>
**25. `cottage_door`** (16 IDs)  
S274: P15 · S350: P08 · S440: P04 · S469: P06 · S497: P07 · S500: P04 · S501: P06 P10 · S530: P04 · S532: P09 · S537: P05 · S617: P14 · S618: P09 · S619: P08 P10 · S734: P03

<a id="f26-cottage-thatched-large"></a>
**26. `cottage_thatched_large`** (16 IDs)  
S409: P12 P14 · S437: P12 P21 · S468: P04 P05 · S469: P02 P05 · S470: P01 P03 · S501: P02 · S587: P05 · S618: P01 P12 · S619: P03 P07

<a id="f27-cottage-thatched-small"></a>
**27. `cottage_thatched_small`** (16 IDs)  
S274: P02 P03 · S469: P01 · S497: P05 P06 · S500: P12 · S501: P01 P03 P05 P09 · S532: P01 P10 · S537: P04 P23 · S619: P02 P11

<a id="f28-dragon"></a>
**28. `dragon`** (16 IDs)  
S074: P21 P22 · S123: P07 · S124: P03 P04 · S127: P07 P08 P09 P10 · S156: P08 · S159: P06 P07 P08 P09 · S160: P06 · S191: P11

<a id="f29-town-roof-dormer"></a>
**29. `town_roof_dormer`** (16 IDs)  
S187: P07 P09 · S218: P21 · S219: P01 P03 · S465: P03 · S466: P04 · S472: P10 · S473: P05 P08 · S474: P21 · S498: P08 · S505: P07 · S506: P08 P25 · S538: P06

<a id="f30-door-wood-wide"></a>
**30. `door_wood_wide`** (15 IDs)  
S350: P09 · S440: P06 · S469: P20 · S497: P13 P15 · S498: P10 · S501: P12 · S504: P15 · S505: P01 · S532: P11 · S537: P24 · S538: P21 · S585: P13 · S618: P11 · S619: P12

<a id="f31-island-fence-lattice"></a>
**31. `island_fence_lattice`** (15 IDs)  
S489: P03 · S711: P07 · S712: P03 · S731: P03 P10 P11 P12 P13 P14 · S732: P02 · S762: P08 P09 · S763: P07 P20 · S764: P09

<a id="f32-potion-red"></a>
**32. `potion_red`** (15 IDs)  
S032: P08 · S166: P24 · S198: P20 P21 · S209: P10 · S214: P02 · S223: P13 · S248: P03 · S352: P19 · S663: P06 · S671: P70 · S681: P14 P15 P16 P17

<a id="f33-town-roof-ridge-cap"></a>
**33. `town_roof_ridge_cap`** (15 IDs)  
S186: P51 · S187: P12 · S385: P18 · S388: P18 · S465: P04 · S467: P04 · S472: P02 · S474: P23 · S506: P23 · S507: P08 · S553: P03 P07 · S554: P02 P05 · S555: P05

<a id="f34-town-wall-stone-door"></a>
**34. `town_wall_stone_door`** (15 IDs)  
S219: P07 · S418: P06 · S419: P07 · S497: P02 · S498: P02 P04 · S499: P01 · S504: P02 · S505: P16 · S506: P03 · S538: P08 · S539: P01 · S585: P02 P04 · S587: P01

<a id="f35-arrow-prop"></a>
**35. `arrow_prop`** (14 IDs)  
S097: P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 · S663: P20 P21 P22 P23

<a id="f36-chest-small"></a>
**36. `chest_small`** (14 IDs)  
S005: P28 · S069: P02 · S101: P02 · S184: P02 · S209: P05 · S276: P04 · S282: P06 · S288: P03 · S395: P03 · S536: P29 · S557: P05 · S671: P65 · S685: P07 · S747: P01

<a id="f37-fence-rail-diag-nw"></a>
**37. `fence_rail_diag_nw`** (14 IDs)  
S409: P19 P20 P21 P42 · S437: P08 P09 P10 P11 P13 P14 P15 P34 · S568: P13 P14

<a id="f38-stone-giant"></a>
**38. `stone_giant`** (14 IDs)  
S178: P10 P11 · S182: P13 · S183: P12 · S209: P14 P16 · S211: P01 · S212: P08 · S213: P10 · S215: P11 · S242: P15 · S245: P01 P02 · S246: P03

<a id="f39-bonca-brown"></a>
**39. `bonca_brown`** (12 IDs)  
S029: P03 P04 P05 P06 P07 · S100: P35 · S302: P06 P07 · S306: P06 · S562: P03 · S583: P10 · S648: P07

<a id="f40-castle-wall-corner"></a>
**40. `castle_wall_corner`** (12 IDs)  
S016: P04 P05 · S017: P02 P03 · S018: P03 · S070: P04 · S337: P02 P04 · S369: P01 P02 · S370: P04 · S402: P09

<a id="f41-island-hut-round"></a>
**41. `island_hut_round`** (12 IDs)  
S489: P02 · S680: P10 · S681: P12 · S712: P13 · S732: P01 · S748: P01 · S762: P01 · S763: P02 P03 P05 · S764: P02 P03

<a id="f42-potion-purple"></a>
**42. `potion_purple`** (11 IDs)  
S062: P09 P10 · S159: P10 P11 P12 P13 · S166: P20 · S273: P08 · S352: P17 P21 · S597: P01

<a id="f43-slime-green"></a>
**43. `slime_green`** (11 IDs)  
S546: P13 P14 P15 P16 P17 P18 P19 P20 · S610: P12 P13 P14

<a id="f44-cave-hole-warp"></a>
**44. `cave_hole_warp`** (10 IDs)  
S085: P01 · S112: P02 · S144: P04 · S182: P01 · S209: P01 · S248: P01 · S254: P04 · S483: P11 · S625: P05 · S671: P01

<a id="f45-island-totem-pole"></a>
**45. `island_totem_pole`** (10 IDs)  
S100: P01 · S366: P07 P08 · S684: P01 · S713: P09 · S716: P01 P02 · S762: P10 P11 P12

<a id="f46-bonca-purple"></a>
**46. `bonca_purple`** (9 IDs)  
S514: P15 P16 · S515: P14 · S547: P14 P16 P17 · S577: P14 P15 · S609: P13

<a id="f47-fire-fx"></a>
**47. `fire_fx`** (9 IDs)  
S001: P21 P27 P30 P31 P32 · S439: P05 P09 P11 P21

<a id="f48-log-cabin-window"></a>
**48. `log_cabin_window`** (9 IDs)  
S251: P08 · S274: P16 · S409: P11 · S440: P08 P09 · S500: P05 · S501: P07 P08 · S530: P05

<a id="f49-potion-blue"></a>
**49. `potion_blue`** (9 IDs)  
S070: P22 · S122: P14 · S127: P11 · S166: P01 P23 · S243: P01 · S352: P18 · S603: P02 · S750: P02

<a id="f50-stairs-wood"></a>
**50. `stairs_wood`** (9 IDs)  
S003: P28 P29 · S004: P13 · S036: P27 · S037: P13 · S163: P27 P28 · S228: P23 · S229: P01

<a id="f51-fish"></a>
**51. `fish`** (8 IDs)  
S634: P01 P02 P03 · S665: P03 · S697: P02 P03 P04 · S727: P17

<a id="f52-gold-coin"></a>
**52. `gold_coin`** (8 IDs)  
S505: P15 · S537: P10 P11 P12 P13 · S663: P03 P17 P18

<a id="f53-ground-crack"></a>
**53. `ground_crack`** (8 IDs)  
S005: P19 · S066: P29 · S154: P03 P04 P06 P09 P10 · S193: P23

<a id="f54-island-torch"></a>
**54. `island_torch`** (8 IDs)  
S731: P02 · S762: P02 · S763: P06 P18 P19 · S764: P04 P05 P07

<a id="f55-pig"></a>
**55. `pig`** (8 IDs)  
S031: P04 · S587: P14 · S636: P05 P06 P07 · S694: P01 P02 P03

<a id="f56-bridge-wood-rail-plank"></a>
**56. `bridge_wood_rail_plank`** (7 IDs)  
S404: P01 P04 · S512: P03 P04 P05 · S693: P28 P29

<a id="f57-bridge-wood-rail-rope"></a>
**57. `bridge_wood_rail_rope`** (7 IDs)  
S404: P03 P05 · S512: P06 P07 P08 · S693: P30 P31

<a id="f58-cottage-thatched-two-storey"></a>
**58. `cottage_thatched_two_storey`** (7 IDs)  
S440: P03 P11 · S500: P01 P02 · S586: P04 · S618: P02 P10

<a id="f59-wall-stripe-red"></a>
**59. `wall_stripe_red`** (7 IDs)  
S097: P35 P36 P37 P38 P39 P40 P41

<a id="f60-cottage-thatched-l-shape"></a>
**60. `cottage_thatched_l_shape`** (6 IDs)  
S318: P01 · S349: P04 · S350: P01 P02 · S734: P01 P02

<a id="f61-fence-rail-diag-ne"></a>
**61. `fence_rail_diag_ne`** (6 IDs)  
S441: P05 P12 P13 P14 · S469: P07 P08

<a id="f62-goblin-soldier"></a>
**62. `goblin_soldier`** (6 IDs)  
S680: P11 P12 · S712: P15 P17 · S713: P11 P12

<a id="f63-small-fire-fx"></a>
**63. `small_fire_fx`** (6 IDs)  
S001: P35 P36 P38 · S439: P31 P32 P33

<a id="f64-ground-hole-dark"></a>
**64. `ground_hole_dark`** (10 IDs)  
S132: P01 · S180: P01 · S209: P04 · S243: P13 · S277: P02 · SW_s1-hole3_L22@S209_P04 · SW_s1-hole_L21@S132_P01 · SW_s1-hole_L21@S277_P02 · SW_s6-hole2_L22@S180_P01 · SW_s6-hole_L22@S243_P13

<a id="f65-chimney-stone"></a>
**65. `chimney_stone`** (5 IDs)  
S469: P03 P04 · S500: P03 · S530: P10 · S734: P04

<a id="f66-shop-sign"></a>
**66. `shop_sign`** (5 IDs)  
S498: P13 P14 · S504: P17 · S538: P22 · S539: P05

<a id="f67-weed-sprig"></a>
**67. `weed_sprig`** (5 IDs)  
S440: P05 · S441: P09 P15 P18 P19

<a id="f68-well-stone"></a>
**68. `well_stone`** (5 IDs)  
S408: P07 · S432: P03 · S497: P09 · S600: P01 · S766: P04

<a id="f69-tree-pine-large"></a>
**69. `tree_pine_large`** (7 IDs)  
S307: P13 · S534: P10 · S659: P06 · S710: P14 · SW_s2-sec1_L37@S307_P13 · SW_s2-sec3_L37@S659_P06 · SW_s3-sec1_L39@S710_P14

<a id="f70-npc-knight-silver"></a>
**70. `npc_knight_silver`** (6 IDs)  
S402: P03 P05 · S408: P04 · S568: P06 · SW_s2-ca-g_L179@S402_P03 · SW_s2-ca-g_L179@S402_P05

<a id="f71-boulder-flat"></a>
**71. `boulder_flat`** (4 IDs)  
S535: P12 · S590: P03 P10 P11

<a id="f72-bridge-stone"></a>
**72. `bridge_stone`** (4 IDs)  
S102: P01 P02 P03 P04

<a id="f73-cottage-thatched-long"></a>
**73. `cottage_thatched_long`** (4 IDs)  
S530: P01 P03 · S617: P01 P13

<a id="f74-fish-flopping"></a>
**74. `fish_flopping`** (4 IDs)  
S734: P09 · S760: P01 P02 P03

<a id="f75-food-fruit"></a>
**75. `food_fruit`** (4 IDs)  
S070: P31 P35 P36 P37

<a id="f76-goblin-hammer"></a>
**76. `goblin_hammer`** (4 IDs)  
S680: P13 P14 · S712: P12 · S748: P03

<a id="f77-island-hut-two-storey"></a>
**77. `island_hut_two_storey`** (4 IDs)  
S680: P09 · S681: P13 · S763: P04 · S764: P01

<a id="f78-npc-girl"></a>
**78. `npc_girl`** (4 IDs)  
S091: P22 · S122: P10 · S126: P06 P07

<a id="f79-npc-knight-red"></a>
**79. `npc_knight_red`** (4 IDs)  
S149: P05 P09 · S374: P03 P04

<a id="f80-poster-hark"></a>
**80. `poster_hark`** (4 IDs)  
S033: P30 · S195: P30 · S225: P30 · S226: P30

<a id="f81-bomb-item"></a>
**81. `bomb_item`** (3 IDs)  
S228: P40 P41 P42

<a id="f82-cabinet-wood"></a>
**82. `cabinet_wood`** (3 IDs)  
S003: P15 P16 · S366: P15

<a id="f83-church"></a>
**83. `church`** (3 IDs)  
S187: P02 · S188: P03 P05

<a id="f84-church-stained-glass"></a>
**84. `church_stained_glass`** (3 IDs)  
S188: P07 P08 P09

<a id="f85-dragon-corpse"></a>
**85. `dragon_corpse`** (3 IDs)  
S100: P34 · S158: P07 · S238: P12

<a id="f86-fireplace-brick"></a>
**86. `fireplace_brick`** (3 IDs)  
S038: P16 · S129: P24 · S163: P23

<a id="f87-pillbug-corpse"></a>
**87. `pillbug_corpse`** (3 IDs)  
S098: P04 · S100: P25 P26

<a id="f88-boulder-large"></a>
**88. `boulder_large`** (2 IDs)  
S277: P03 · S590: P01

<a id="f89-boulder-red"></a>
**89. `boulder_red`** (2 IDs)  
S536: P15 · S590: P04

<a id="f90-burnt-floor-hole"></a>
**90. `burnt_floor_hole`** (2 IDs)  
S439: P34 P38

<a id="f91-castle-wall-end"></a>
**91. `castle_wall_end`** (2 IDs)  
S016: P03 · S048: P05

<a id="f92-cellar-hatch"></a>
**92. `cellar_hatch`** (2 IDs)  
S068: P24 P25

<a id="f93-chest-large"></a>
**93. `chest_large`** (2 IDs)  
S098: P07 · S536: P31

<a id="f94-chest-medium"></a>
**94. `chest_medium`** (2 IDs)  
S026: P06 · S284: P04

<a id="f95-church-window-small"></a>
**95. `church_window_small`** (2 IDs)  
S187: P01 P03

<a id="f96-corpse-merchant"></a>
**96. `corpse_merchant`** (2 IDs)  
S092: P01 · S094: P01

<a id="f97-duck-corpse"></a>
**97. `duck_corpse`** (2 IDs)  
S100: P27 · S521: P05

<a id="f98-explosion-fx"></a>
**98. `explosion_fx`** (2 IDs)  
S001: P28 P29

<a id="f99-fire-burst-fx"></a>
**99. `fire_burst_fx`** (2 IDs)  
S001: P33 P41

<a id="f100-fireball-fx"></a>
**100. `fireball_fx`** (2 IDs)  
S366: P09 P14

<a id="f101-food-pie"></a>
**101. `food_pie`** (2 IDs)  
S070: P24 P25

<a id="f102-fountain-spray-fx"></a>
**102. `fountain_spray_fx`** (2 IDs)  
S260: P30 · S586: P14

<a id="f103-hearth-fire"></a>
**103. `hearth_fire`** (2 IDs)  
S001: P20 · S163: P24

<a id="f104-log-cabin"></a>
**104. `log_cabin`** (2 IDs)  
S251: P01 · S270: P07

<a id="f105-log-cabin-door"></a>
**105. `log_cabin_door`** (2 IDs)  
S251: P07 · S409: P13

<a id="f106-npc-knight-red-attacking"></a>
**106. `npc_knight_red_attacking`** (2 IDs)  
S241: P03 · S242: P03

<a id="f107-npc-merchant-blue"></a>
**107. `npc_merchant_blue`** (2 IDs)  
S290: P30 · S374: P05

<a id="f108-npc-merchant-green"></a>
**108. `npc_merchant_green`** (2 IDs)  
S164: P02 · S227: P02

<a id="f109-npc-peasant"></a>
**109. `npc_peasant`** (2 IDs)  
S003: P23 · S038: P22

<a id="f110-sparkle-fx"></a>
**110. `sparkle_fx`** (2 IDs)  
S001: P37 · S045: P01

<a id="f111-table-round"></a>
**111. `table_round`** (2 IDs)  
S004: P17 · S037: P17

<a id="f112-tree-willow"></a>
**112. `tree_willow`** (2 IDs)  
S414: P02 · S446: P02

<a id="f113-tree-willow-large"></a>
**113. `tree_willow_large`** (2 IDs)  
S149: P02 · S474: P01

<a id="f114-weed-small"></a>
**114. `weed_small`** (2 IDs)  
S446: P01 P03

<a id="f115-boulder-grey-tall"></a>
**115. `boulder_grey_tall`** (1 IDs)  
S601: P08

<a id="f116-boulder-white-pair"></a>
**116. `boulder_white_pair`** (1 IDs)  
S590: P02

<a id="f117-burn-damage-decal"></a>
**117. `burn_damage_decal`** (1 IDs)  
S439: P29

<a id="f118-bush-round-large"></a>
**118. `bush_round_large`** (1 IDs)  
S446: P05

<a id="f119-bush-round-medium"></a>
**119. `bush_round_medium`** (1 IDs)  
S446: P06

<a id="f120-bush-small"></a>
**120. `bush_small`** (1 IDs)  
S446: P07

<a id="f121-castle-door"></a>
**121. `castle_door`** (1 IDs)  
S402: P04

<a id="f122-castle-drawbridge"></a>
**122. `castle_drawbridge`** (1 IDs)  
S080: P05

<a id="f123-castle-gatehouse"></a>
**123. `castle_gatehouse`** (1 IDs)  
S080: P04

<a id="f124-church-door"></a>
**124. `church_door`** (1 IDs)  
S188: P06

<a id="f125-corpse-girl"></a>
**125. `corpse_girl`** (1 IDs)  
S222: P04

<a id="f126-corpse-knight"></a>
**126. `corpse_knight`** (1 IDs)  
S157: P04

<a id="f127-corpse-maiden"></a>
**127. `corpse_maiden`** (1 IDs)  
S091: P21

<a id="f128-corpse-mom"></a>
**128. `corpse_mom`** (1 IDs)  
S001: P34

<a id="f129-corpse-peasant"></a>
**129. `corpse_peasant`** (1 IDs)  
S222: P05

<a id="f130-corpse-soldier"></a>
**130. `corpse_soldier`** (1 IDs)  
S086: P01

<a id="f131-dink-dead"></a>
**131. `dink_dead`** (1 IDs)  
S058: P06

<a id="f132-food-bread"></a>
**132. `food_bread`** (1 IDs)  
S070: P33

<a id="f133-food-cheese"></a>
**133. `food_cheese`** (1 IDs)  
S070: P26

<a id="f134-food-drumstick"></a>
**134. `food_drumstick`** (1 IDs)  
S070: P23

<a id="f135-food-grapes"></a>
**135. `food_grapes`** (1 IDs)  
S070: P30

<a id="f136-food-ham"></a>
**136. `food_ham`** (1 IDs)  
S070: P32

<a id="f137-king-on-throne"></a>
**137. `king_on_throne`** (1 IDs)  
S070: P03

<a id="f138-npc-gnome-purple"></a>
**138. `npc_gnome_purple`** (1 IDs)  
S006: P23

<a id="f139-npc-maiden-blue"></a>
**139. `npc_maiden_blue`** (1 IDs)  
S004: P16

<a id="f140-npc-maiden-brown"></a>
**140. `npc_maiden_brown`** (1 IDs)  
S410: P06

<a id="f141-npc-maiden-red"></a>
**141. `npc_maiden_red`** (1 IDs)  
S122: P09

<a id="f142-npc-old-man"></a>
**142. `npc_old_man`** (1 IDs)  
S002: P23

<a id="f143-npc-soldier"></a>
**143. `npc_soldier`** (1 IDs)  
S410: P07

<a id="f144-ore-rock-blue"></a>
**144. `ore_rock_blue`** (1 IDs)  
S590: P09

<a id="f145-poster-wanted"></a>
**145. `poster_wanted`** (1 IDs)  
S035: P27

<a id="f146-snow-house-door"></a>
**146. `snow_house_door`** (1 IDs)  
S149: P07

<a id="f147-snow-house-lower"></a>
**147. `snow_house_lower`** (1 IDs)  
S149: P03

<a id="f148-snow-house-roof"></a>
**148. `snow_house_roof`** (1 IDs)  
S149: P08

<a id="f149-snow-house-timber"></a>
**149. `snow_house_timber`** (1 IDs)  
S149: P06

<a id="f150-thorn-branch"></a>
**150. `thorn_branch`** (1 IDs)  
S192: P05

<a id="f151-tree-oak-large"></a>
**151. `tree_oak_large`** (1 IDs)  
S693: P06

<a id="f152-screen-ground-tile-layer"></a>
**152. `screen ground (tile layer)`** (639 IDs)  
SCR 002 003 004 005 006 010 013 014 015 016 017 018 025 026 027 028 029 030 031 032 033 034 035 036 037 038 045 046 047 048 049 050 057 058 059 060 061 062 063 064 065 066 067 068 069 070 073 074 077 078 079 080 081 082 085 086 089 090 091 092 093 094 095 096 097 098 099 100 101 102 105 106 109 110 111 112 113 114 117 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 137 138 143 144 145 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 169 170 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 202 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 237 238 239 240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 298 299 301 302 303 304 305 306 307 308 309 310 311 312 313 314 315 316 317 318 319 320 324 333 334 335 336 337 338 339 340 341 342 343 344 345 346 347 348 349 350 351 352 353 354 355 356 357 358 359 363 364 365 366 367 368 369 370 371 372 373 374 375 376 377 378 379 380 381 382 383 384 385 386 387 388 389 390 391 395 396 397 398 399 400 401 402 403 404 405 406 408 409 410 411 412 413 414 415 416 417 418 419 420 421 422 423 424 425 426 427 428 429 430 431 432 433 434 435 436 437 440 441 442 443 444 445 446 447 448 449 450 451 452 453 454 455 456 457 458 459 460 461 462 463 464 465 466 467 468 469 470 472 473 474 475 476 477 478 479 480 481 482 483 484 485 486 487 488 489 490 491 492 493 494 495 496 497 498 499 500 501 502 503 504 505 506 507 508 509 510 511 512 514 515 516 517 518 519 520 521 522 523 524 525 526 527 528 529 530 531 532 533 534 535 536 537 538 539 540 541 542 543 544 546 547 548 549 550 551 552 553 554 555 556 557 558 559 560 561 562 563 564 565 566 567 568 569 570 571 572 573 574 575 576 577 578 579 580 581 582 583 584 585 586 587 588 589 590 591 592 593 594 595 596 597 598 599 600 601 602 603 604 605 606 607 608 609 610 611 612 613 614 615 616 617 618 619 620 621 622 623 624 625 626 627 628 629 630 631 632 633 634 635 636 637 638 639 640 646 647 648 649 650 651 652 653 654 655 656 657 658 659 660 661 662 663 664 665 666 667 668 669 670 671 672 678 679 680 681 682 683 684 685 686 687 688 689 690 691 692 693 694 695 696 697 698 699 700 701 702 703 704 710 711 712 713 714 715 716 717 718 719 720 721 722 723 724 725 726 727 728 729 730 731 732 733 734 735 736 742 743 744 745 746 747 748 749 750 751 752 753 754 755 756 757 758 759 760 761 762 763 764 765 766 767 768
