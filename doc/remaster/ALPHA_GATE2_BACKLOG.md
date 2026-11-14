# Alpha gate 2 backlog: origin IDs still open

Generated 2026-11-14 by `DinkRemasterUE/Scripts/gate2_backlog.py` from `Saved/Import/coverage.csv` (6607 rows, importer run of 2026-11-14) and the manifests under `Content/Dink/Data/Art/`, classified by `Scripts/art_coverage.py`. Do not edit by hand; regenerate.

Alpha gate 2 (`doc/remaster/REMASTER_PLAN.md`): every origin ID is final, placeholder or cut with a reason. This list is what is still open: every origin ID whose art state in `Scripts/art_coverage.py` is `placeholder` (no art bound; nothing in the repo records a placeholder as owner-accepted), plus any unclassified ID. Final (bespoke or by family, `Content/Dink/Data/Art/families.json`) and cut (owner decision of 9 Nov 2026) are closed and not listed.

## Summary

| | open |
|---|---:|
| sprite families | 134 |
| origin IDs | 1496 |
| map placements | 1180 |
| screens (ground tile layer) | 303 |
| script warps with their own ID | 13 |
| unclassified IDs | 0 |

Claimed by the Claude photoreal pass (in progress elsewhere, not final): **53 families, 1075 origin IDs, 766 placements**. Unclaimed: 81 families, 421 origin IDs, 414 placements.

Largest family by origin IDs: `screen ground (tile layer)` (303 IDs, 0 map placements, so it sorts at #134).

Largest families no stream has claimed: `blood_splat` 46, `tree_fruit` 34, `burn_hole_decal` 26, `bonca_gray` 21, `slayer` 21, `npc_knight_blue` 18, `dragon` 16, `arrow_prop` 14, `stone_giant` 14, `bonca_brown` 12.

Closed for comparison (art_coverage rows): final bespoke 754, final by family 4160, cut 152, placeholder 1541 of 6607 rows.

## How to regenerate

```bash
cd DinkRemasterUE && python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md
```

Run it in the editor's checkout: like `art_coverage.py` it needs the importer's `Saved/Import/coverage.csv` (`Scripts/import_greybox.sh --region all`), `tools/dinkex/out/sequences.json` and the gitignored engine template content under `Content/Characters` (the mother's locomotion). From another worktree add `--project <editor checkout>/DinkRemasterUE`. The photoreal column is a snapshot of `<--photoreal-root>/*/manifest.json` (default: the uncommitted photoreal pass work copy), read-only; regenerate after that pass lands or binds families.

## Backlog by sprite family

Sorted by open map placements. Family is the class id (`tools/data/sprite_classes.csv`, the key `families.json` binds); *what the original shows* gives its name, sprite group, size and the reference sheet in `doc/remaster/reference/`; *sequences* are the original sprite sequences of the open placements. The origin IDs of each family are listed under [Open origin IDs](#open-origin-ids).

| # | family | what the original sprite sheet shows | sequences (open placements) | origin IDs | placements | photoreal pass |
|---:|---|---|---|---:|---:|---|
| 1 | [`duck`](#f1-duck) | Duck (duck, 31x41 px) · sheet_foes.png | 23 animals/duck/dk3w- (24), 29 animals/duck/dk9w- (18), 24 animals/duck/dk4w- (14), 26 animals/duck/dk6w- (12), 27 animals/duck/dk7w- (12), 21 animals/duck/dk1w- (11) | 92 | 91 | Creatures |
| 2 | [`duck_head`](#f2-duck-head) | Duck head (death sprite) used as set dressing (duck, 15x42 px) · sheet_foes.png | 121 animals/duck/death/dkh1x- (90) | 90 | 90 | Creatures |
| 3 | [`slime_blue`](#f3-slime-blue) | Slime (blue) (slime, 24x18 px) · sheet_foes.png | 651 foes/puddle/blue/walk/f06w1- (67) | 67 | 67 | Creatures |
| 4 | [`town_roof_flat`](#f4-town-roof-flat) | Shingle roof section (town_house_kit, 100x200 px) · sheet_struct.png | 33 struct/outinn/oinn- (52) | 52 | 52 | TownExteriors |
| 5 | [`blood_splat`](#f5-blood-splat) | Blood splatter (blood, 39x56 px) · sheet_effects.png | 188 effects/spurt/sprtl- (24), 189 effects/spurt/sprtr- (18), 187 effects/spurt/spurt- (4) | 46 | 46 | - |
| 6 | [`castle_wall_diag`](#f6-castle-wall-diag) | Castle curtain wall (diagonal run) (castle_kit, 350x463 px) · sheet_struct.png | 67 struct/castle/castl- (46) | 46 | 46 | Structures |
| 7 | [`tree_fruit`](#f7-tree-fruit) | Fruit hanging in a tree (food, 7x12 px) · sheet_items.png | 421 items/food/food- (34) | 34 | 34 | - |
| 8 | [`slime_red`](#f8-slime-red) | Slime (red) (slime, 25x18 px) · sheet_foes.png | 693 foes/puddle/red/walk/f06w3- (17), 691 foes/puddle/red/walk/f06w1- (12) | 29 | 29 | Creatures |
| 9 | [`burn_hole_decal`](#f9-burn-hole-decal) | Burnt hole / scorch mark (damage, 23x20 px) · sheet_struct.png | 158 struct/details/damage/hole- (26) | 26 | 26 | - |
| 10 | [`bridge_wood_deck`](#f10-bridge-wood-deck) | Wooden bridge deck (bridge_wood, 65x88 px) · sheet_struct.png | 58 struct/bridge/brdge- (22) | 22 | 22 | Structures |
| 11 | [`bonca_gray`](#f11-bonca-gray) | Bonca (grey) (bonca, 97x91 px) · sheet_foes.png | 601 foes/bonca/gray/walk/f03w1- (6), 603 foes/bonca/gray/walk/f03w3- (4), 609 foes/bonca/gray/walk/f03w9- (4), 592 foes/bonca/gray/attack/f03a6- (3), 607 foes/bonca/gray/walk/f03w7- (3), 594 foes/bonca/gray/attack/f03a2- (1) | 21 | 21 | - |
| 12 | [`slayer`](#f12-slayer) | Slayer (slayer, 113x105 px) · sheet_foes.png | 632 foes/slayers/attack/f04a2- (7), 641 foes/slayers/walk/f04w1- (6), 634 foes/slayers/attack/f04a4- (4), 643 foes/slayers/walk/f04w3- (1), 649 foes/slayers/walk/f04w9- (1), 647 foes/slayers/walk/f04w7- (1), 636 foes/slayers/attack/f04a6- (1) | 21 | 21 | - |
| 13 | [`door_wood_single`](#f13-door-wood-single) | Wooden door (doors, 24x64 px) · sheet_struct.png | 61 struct/details/door/odor1- (20) | 22 | 20 | Structures |
| 14 | [`castle_tower_round`](#f14-castle-tower-round) | Round castle tower (castle_kit, 193x409 px) · sheet_struct.png | 67 struct/castle/castl- (20) | 20 | 20 | Structures |
| 15 | [`npc_knight_blue`](#f15-npc-knight-blue) | Knight (blue) (npc_knight, 91x125 px) · sheet_people.png | 287 people/knight/blue/c5-w7- (8), 289 people/knight/blue/c5-w9- (8), 281 people/knight/blue/c5-w1- (1), 283 people/knight/blue/c5-w3- (1) | 18 | 18 | - |
| 16 | [`fence_rail_ns`](#f16-fence-rail-ns) | Rail fence (north-south) (fence_rail, 26x136 px) · sheet_lands.png | 93 lands/fence/fence- (17) | 17 | 17 | Structures |
| 17 | [`cottage_door`](#f17-cottage-door) | Cottage door (cottage_thatched, 55x89 px) · sheet_struct.png | 63 struct/home/home- (16) | 16 | 16 | Structures |
| 18 | [`cottage_thatched_large`](#f18-cottage-thatched-large) | Thatched stone cottage (cottage_thatched, 334x259 px) · sheet_struct.png | 63 struct/home/home- (16) | 16 | 16 | Structures |
| 19 | [`cottage_thatched_small`](#f19-cottage-thatched-small) | Thatched stone cottage (cottage_thatched, 257x225 px) · sheet_struct.png | 63 struct/home/home- (16) | 16 | 16 | Structures |
| 20 | [`dragon`](#f20-dragon) | Dragon (dragon, 164x188 px) · sheet_foes.png | 202 foes/dragon/f2-w2- (8), 206 foes/dragon/f2-w6- (4), 204 foes/dragon/f2-w4- (3), 208 foes/dragon/f2-w8- (1) | 16 | 16 | - |
| 21 | [`town_roof_dormer`](#f21-town-roof-dormer) | Roof section with dormer window (town_house_kit, 100x200 px) · sheet_struct.png | 33 struct/outinn/oinn- (16) | 16 | 16 | TownExteriors |
| 22 | [`door_wood_wide`](#f22-door-wood-wide) | Wide wooden door (doors, 53x68 px) · sheet_struct.png | 62 struct/details/door/odor2- (15) | 15 | 15 | Structures |
| 23 | [`island_fence_lattice`](#f23-island-fence-lattice) | Lashed pole fence (island_village, 271x76 px) · sheet_struct.png | 424 struct/island/isle- (15) | 15 | 15 | Structures |
| 24 | [`town_roof_slope`](#f24-town-roof-slope) | Shingle roof slope (town_house_kit, 100x150 px) · sheet_struct.png | 33 struct/outinn/oinn- (15) | 15 | 15 | TownExteriors |
| 25 | [`arrow_prop`](#f25-arrow-prop) | Arrow (shop display / stuck in ground) (arrow, 47x30 px) · sheet_effects.png | 25 effects/arrow/arrow- (14) | 14 | 14 | - |
| 26 | [`chest_small`](#f26-chest-small) | Treasure chest (small) (chests, 44x60 px) · sheet_items.png | 175 bonuses/chest/chst1- (14) | 14 | 14 | Props |
| 27 | [`fence_rail_diag_nw`](#f27-fence-rail-diag-nw) | Rail fence diagonal (other) (fence_rail, 77x88 px) · sheet_lands.png | 93 lands/fence/fence- (14) | 14 | 14 | Structures |
| 28 | [`stone_giant`](#f28-stone-giant) | Stone giant (stone_giant, 104x88 px) · sheet_foes.png | 821 foes/stonegnt/walk/f01w1- (8), 823 foes/stonegnt/walk/f01w3- (3), 816 foes/stonegnt/attack/f01a6- (1), 829 foes/stonegnt/walk/f01w9- (1), 827 foes/stonegnt/walk/f01w7- (1) | 14 | 14 | - |
| 29 | [`town_roof_ridge_cap`](#f29-town-roof-ridge-cap) | Roof ridge / corner cap (town_house_kit, 60x45 px) · sheet_struct.png | 33 struct/outinn/oinn- (14) | 14 | 14 | TownExteriors |
| 30 | [`bonca_brown`](#f30-bonca-brown) | Bonca (brown) (bonca, 85x94 px) · sheet_foes.png | 542 foes/bonca/attack/f03a6- (2), 544 foes/bonca/attack/f03a2- (2), 533 foes/bonca/walk/f03w3- (2), 539 foes/bonca/walk/f03w9- (2), 537 foes/bonca/walk/f03w7- (2), 531 foes/bonca/walk/f03w1- (2) | 12 | 12 | - |
| 31 | [`castle_wall_corner`](#f31-castle-wall-corner) | Castle wall corner (castle_kit, 350x505 px) · sheet_struct.png | 67 struct/castle/castl- (12) | 12 | 12 | Structures |
| 32 | [`island_hut_round`](#f32-island-hut-round) | Koka Isle round hut (island_village, 208x178 px) · sheet_struct.png | 424 struct/island/isle- (12) | 12 | 12 | Structures |
| 33 | [`slime_green`](#f33-slime-green) | Slime (green) (slime, 26x23 px) · sheet_foes.png | 671 foes/puddle/green/walk/f06w1- (11) | 11 | 11 | Creatures |
| 34 | [`cave_hole_warp`](#f34-cave-hole-warp) | Hole into a cave (warp) (ground_holes, 55x31 px) · sheet_lands.png | 89 lands/details/crack- (10) | 10 | 10 | - |
| 35 | [`island_totem_pole`](#f35-island-totem-pole) | Pole with skull/feather totem (island_village, 27x105 px) · sheet_struct.png | 424 struct/island/isle- (10) | 10 | 10 | Structures |
| 36 | [`bonca_purple`](#f36-bonca-purple) | Bonca (purple) (bonca, 85x94 px) · sheet_foes.png | 613 foes/bonca/purple/walk/f03w3- (6), 619 foes/bonca/purple/walk/f03w9- (1), 628 foes/bonca/purple/attack/f03a4- (1), 626 foes/bonca/purple/attack/f03a8- (1) | 9 | 9 | - |
| 37 | [`fire_fx`](#f37-fire-fx) | Fire (looping flames) (fire, 78x78 px) · sheet_effects.png | 427 effects/fire/fire1- (9) | 9 | 9 | Props |
| 38 | [`log_cabin_window`](#f38-log-cabin-window) | Log cabin window (log_cabin, 24x28 px) · sheet_struct.png | 59 struct/cabin/cabin- (9) | 9 | 9 | - |
| 39 | [`stairs_wood`](#f39-stairs-wood) | Wooden stairs (stairs, 82x72 px) · sheet_inside.png | 428 inside/stairs/stair- (9) | 9 | 9 | - |
| 40 | [`fish`](#f40-fish) | Fish (swimming) (fish, 72x52 px) · sheet_foes.png | 434 animals/fish/fish1/fish1- (8) | 8 | 8 | - |
| 41 | [`gold_coin`](#f41-gold-coin) | Single coin (gold, 4x3 px) · sheet_items.png | 178 bonuses/coins/coin- (8) | 8 | 8 | - |
| 42 | [`ground_crack`](#f42-ground-crack) | Crack in the ground (ground_holes, 88x33 px) · sheet_lands.png | 89 lands/details/crack- (8) | 8 | 8 | - |
| 43 | [`island_torch`](#f43-island-torch) | Bamboo torch / pole (island_village, 85x105 px) · sheet_struct.png | 425 struct/island/torch- (8) | 8 | 8 | Props |
| 44 | [`pig`](#f44-pig) | Pig (pig, 50x56 px) · sheet_foes.png | 41 animals/pig/pg-w1- (5), 43 animals/pig/pg-w3- (2), 49 animals/pig/pg-w9- (1) | 8 | 8 | Creatures |
| 45 | [`bridge_wood_rail_plank`](#f45-bridge-wood-rail-plank) | Bridge side rail with planking (bridge_wood, 101x84 px) · sheet_struct.png | 58 struct/bridge/brdge- (7) | 7 | 7 | Structures |
| 46 | [`bridge_wood_rail_rope`](#f46-bridge-wood-rail-rope) | Bridge rope rail (bridge_wood, 101x93 px) · sheet_struct.png | 58 struct/bridge/brdge- (7) | 7 | 7 | Structures |
| 47 | [`cottage_thatched_two_storey`](#f47-cottage-thatched-two-storey) | Two-storey thatched cottage (cottage_thatched, 257x311 px) · sheet_struct.png | 63 struct/home/home- (7) | 7 | 7 | Structures |
| 48 | [`wall_stripe_red`](#f48-wall-stripe-red) | Red wall stripe / banner (built from the health-bar UI art) (signs, 24x17 px) · sheet_inter.png | 450 inter/health/hm-br- (7) | 7 | 7 | - |
| 49 | [`cottage_thatched_l_shape`](#f49-cottage-thatched-l-shape) | L-shaped thatched cottage (cottage_thatched, 305x324 px) · sheet_struct.png | 63 struct/home/home- (6) | 6 | 6 | Structures |
| 50 | [`fence_rail_diag_ne`](#f50-fence-rail-diag-ne) | Rail fence diagonal (fence_rail, 69x90 px) · sheet_lands.png | 93 lands/fence/fence- (6) | 6 | 6 | Structures |
| 51 | [`goblin_soldier`](#f51-goblin-soldier) | Goblin soldier (goblin, 107x130 px) · sheet_foes.png | 809 foes/goblin/soldier/walk/f01w9- (3), 801 foes/goblin/soldier/walk/f01w1- (2), 803 foes/goblin/soldier/walk/f01w3- (1) | 6 | 6 | - |
| 52 | [`small_fire_fx`](#f52-small-fire-fx) | Small fire on floor (fire, 23x20 px) · sheet_struct.png | 155 struct/details/damage/fire2- (2), 156 struct/details/damage/fire3- (2), 157 struct/details/damage/fire4- (2) | 6 | 6 | Props |
| 53 | [`ground_hole_dark`](#f53-ground-hole-dark) | Dark hole in the ground (ground_holes, 55x73 px) · sheet_lands.png | 89 lands/details/crack- (5) | 10 | 5 | - |
| 54 | [`chimney_stone`](#f54-chimney-stone) | Stone chimney (cottage_thatched, 55x58 px) · sheet_struct.png | 63 struct/home/home- (5) | 5 | 5 | Structures |
| 55 | [`shop_sign`](#f55-shop-sign) | Hanging sign (red cross: healer) (signs, 63x76 px) · sheet_inside.png | 458 inside/details/sign- (5) | 5 | 5 | - |
| 56 | [`well_stone`](#f56-well-stone) | Stone well with roof (landmarks, 107x136 px) · sheet_struct.png | 186 struct/landmark/landm- (5) | 5 | 5 | Structures |
| 57 | [`tree_pine_large`](#f57-tree-pine-large) | Pine tree (trees, 128x188 px) · sheet_lands.png | 32 lands/trees/tree- (4) | 7 | 4 | Vegetation |
| 58 | [`npc_knight_silver`](#f58-npc-knight-silver) | Knight (silver) (npc_knight, 110x117 px) · sheet_people.png | 293 people/knight/silver/c5-w3- (2), 299 people/knight/silver/c5-w9- (1), 291 people/knight/silver/c5-w1- (1) | 6 | 4 | - |
| 59 | [`boulder_flat`](#f59-boulder-flat) | Flat boulder (boulders, 72x63 px) · sheet_lands.png | 95 lands/rocks/rock- (4) | 4 | 4 | - |
| 60 | [`bridge_stone`](#f60-bridge-stone) | Stone arch bridge (bridge_stone, 288x212 px) · sheet_struct.png | 186 struct/landmark/landm- (4) | 4 | 4 | Structures |
| 61 | [`cottage_thatched_long`](#f61-cottage-thatched-long) | Thatched stone cottage (cottage_thatched, 332x260 px) · sheet_struct.png | 63 struct/home/home- (4) | 4 | 4 | Structures |
| 62 | [`fish_flopping`](#f62-fish-flopping) | Fish flopping on land (fish, 33x34 px) · sheet_foes.png | 439 animals/fish/flop/fishx- (3), 441 animals/fish/flop/flop2- (1) | 4 | 4 | - |
| 63 | [`food_fruit`](#f63-food-fruit) | Fruit (apple / pear / etc.) (food, 17x23 px) · sheet_items.png | 421 items/food/food- (4) | 4 | 4 | - |
| 64 | [`goblin_hammer`](#f64-goblin-hammer) | Goblin (hammer) (goblin, 56x109 px) · sheet_foes.png | 763 foes/goblin/hammer/walk/f01w3- (2), 761 foes/goblin/hammer/walk/f01w1- (1), 769 foes/goblin/hammer/walk/f01w9- (1) | 4 | 4 | - |
| 65 | [`island_hut_two_storey`](#f65-island-hut-two-storey) | Two-tier round hut (island_village, 238x265 px) · sheet_struct.png | 424 struct/island/isle- (4) | 4 | 4 | Structures |
| 66 | [`npc_girl`](#f66-npc-girl) | Girl (child) (npc_girl, 53x62 px) · sheet_people.png | 331 people/girl/c03w1- (3), 339 people/girl/c03w9- (1) | 4 | 4 | - |
| 67 | [`npc_knight_red`](#f67-npc-knight-red) | Knight (red) (npc_knight, 91x125 px) · sheet_people.png | 273 people/knight/red/c5-w3- (2), 279 people/knight/red/c5-w9- (1), 277 people/knight/red/c5-w7- (1) | 4 | 4 | - |
| 68 | [`poster_hark`](#f68-poster-hark) | "Hark!" notice (signs, 43x61 px) · sheet_inside.png | 462 inner/poster (4) | 4 | 4 | - |
| 69 | [`bomb_item`](#f69-bomb-item) | Bomb (items, 26x33 px) · sheet_items.png | 420 items/bomb/bomb- (3) | 3 | 3 | - |
| 70 | [`cabinet_wood`](#f70-cabinet-wood) | Wooden cabinet / dresser (house_interior, 57x79 px) · sheet_inside.png | 87 inside/details/table- (3) | 3 | 3 | Props |
| 71 | [`church`](#f71-church) | Stone church (church, 417x433 px) · sheet_struct.png | 60 struct/church/chrch- (3) | 3 | 3 | - |
| 72 | [`church_stained_glass`](#f72-church-stained-glass) | Stained-glass window (church, 56x94 px) · sheet_struct.png | 60 struct/church/chrch- (3) | 3 | 3 | - |
| 73 | [`fireplace_brick`](#f73-fireplace-brick) | Brick fireplace (house_interior, 97x114 px) · sheet_inside.png | 64 inside/details/inacc- (3) | 3 | 3 | Props |
| 74 | [`pillbug_corpse`](#f74-pillbug-corpse) | Pillbug death splat (pillbug, 46x35 px) · sheet_foes.png | 141 foes/pill/f1-x1- (2), 143 foes/pill/f1-x3- (1) | 3 | 3 | Creatures |
| 75 | [`boulder_large`](#f75-boulder-large) | Large dark boulder (boulders, 103x95 px) · sheet_lands.png | 95 lands/rocks/rock- (2) | 2 | 2 | - |
| 76 | [`boulder_red`](#f76-boulder-red) | Reddish boulder (boulders, 100x79 px) · sheet_lands.png | 95 lands/rocks/rock- (2) | 2 | 2 | - |
| 77 | [`burnt_floor_hole`](#f77-burnt-floor-hole) | Burnt hole in floor/roof (large) (damage, 90x69 px) · sheet_struct.png | 158 struct/details/damage/hole- (2) | 2 | 2 | - |
| 78 | [`castle_wall_end`](#f78-castle-wall-end) | Castle wall end (edge-on) (castle_kit, 100x340 px) · sheet_struct.png | 67 struct/castle/castl- (2) | 2 | 2 | Structures |
| 79 | [`cellar_hatch`](#f79-cellar-hatch) | Cellar hatch / ladder (stairs, 35x57 px) · sheet_inside.png | 428 inside/stairs/stair- (2) | 2 | 2 | - |
| 80 | [`chest_large`](#f80-chest-large) | Treasure chest (large) (chests, 60x60 px) · sheet_items.png | 177 bonuses/chest/chst3- (2) | 2 | 2 | Props |
| 81 | [`chest_medium`](#f81-chest-medium) | Treasure chest (chests, 44x55 px) · sheet_items.png | 176 bonuses/chest/chst2- (2) | 2 | 2 | Props |
| 82 | [`church_window_small`](#f82-church-window-small) | Church small window (church, 19x27 px) · sheet_struct.png | 60 struct/church/chrch- (2) | 2 | 2 | - |
| 83 | [`corpse_merchant`](#f83-corpse-merchant) | Dead merchant (npc_merchant, 74x53 px) · sheet_people.png | 385 people/merchant/green/death- (1), 345 people/merchant/death- (1) | 2 | 2 | - |
| 84 | [`duck_corpse`](#f84-duck-corpse) | Dead duck body (duck, 20x30 px) · sheet_foes.png | 127 animals/duck/death/dkh7x- (1), 121 animals/duck/death/dkh1x- (1) | 2 | 2 | Creatures |
| 85 | [`explosion_fx`](#f85-explosion-fx) | Explosion (, 60x61 px) · sheet_effects.png | 70 effects/splode/explo- (2) | 2 | 2 | - |
| 86 | [`fire_burst_fx`](#f86-fire-burst-fx) | Fire burst (atomic explosion frames) (, 93x141 px) · sheet_effects.png | 161 effects/atomic/atomc- (2) | 2 | 2 | - |
| 87 | [`fireball_fx`](#f87-fireball-fx) | Fireball (vertical) (, 32x76 px) · sheet_effects.png | 512 effects/comets/sm-comt2/fbal2- (2) | 2 | 2 | - |
| 88 | [`food_pie`](#f88-food-pie) | Pie (food, 24x19 px) · sheet_items.png | 421 items/food/food- (2) | 2 | 2 | Props |
| 89 | [`fountain_spray_fx`](#f89-fountain-spray-fx) | Fountain water spray (fountain, 80x84 px) · sheet_lands.png | 94 lands/garden/spray- (2) | 2 | 2 | - |
| 90 | [`hearth_fire`](#f90-hearth-fire) | Fireplace fire (house_interior, 46x55 px) · sheet_inside.png | 86 inside/details/fire- (2) | 2 | 2 | - |
| 91 | [`log_cabin`](#f91-log-cabin) | Log cabin (log_cabin, 322x232 px) · sheet_struct.png | 59 struct/cabin/cabin- (2) | 2 | 2 | - |
| 92 | [`log_cabin_door`](#f92-log-cabin-door) | Log cabin door (log_cabin, 34x69 px) · sheet_struct.png | 59 struct/cabin/cabin- (2) | 2 | 2 | - |
| 93 | [`npc_knight_red_attacking`](#f93-npc-knight-red-attacking) | Knight (red) attack pose (npc_knight, 121x127 px) · sheet_people.png | 712 people/knight/red/attack/c05a2- (2) | 2 | 2 | - |
| 94 | [`npc_merchant_blue`](#f94-npc-merchant-blue) | Merchant (blue) (npc_merchant, 55x93 px) · sheet_people.png | 371 people/merchant/blue/c09w1- (2) | 2 | 2 | - |
| 95 | [`npc_merchant_green`](#f95-npc-merchant-green) | Merchant (green) (npc_merchant, 55x93 px) · sheet_people.png | 381 people/merchant/green/c09w1- (2) | 2 | 2 | - |
| 96 | [`npc_peasant`](#f96-npc-peasant) | Peasant (npc_peasant, 73x121 px) · sheet_people.png | 411 people/peasant2/c11w1- (2) | 2 | 2 | - |
| 97 | [`sparkle_fx`](#f97-sparkle-fx) | Sparkle (, 20x20 px) · sheet_effects.png | 165 effects/shiny/shiny- (1), 166 effects/sparks/spark- (1) | 2 | 2 | - |
| 98 | [`tree_willow`](#f98-tree-willow) | Weeping (willow-like) tree (trees, 169x252 px) · sheet_lands.png | 32 lands/trees/tree- (2) | 2 | 2 | Vegetation |
| 99 | [`tree_willow_large`](#f99-tree-willow-large) | Large weeping tree (trees, 249x300 px) · sheet_lands.png | 32 lands/trees/tree- (2) | 2 | 2 | Vegetation |
| 100 | [`boulder_grey_tall`](#f100-boulder-grey-tall) | Tall grey boulder (boulders, 54x77 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 101 | [`boulder_white_pair`](#f101-boulder-white-pair) | Pair of white boulders (boulders, 80x58 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 102 | [`burn_damage_decal`](#f102-burn-damage-decal) | Burn damage / scorch with fire (damage, 90x69 px) · sheet_struct.png | 154 struct/details/damage/damag- (1) | 1 | 1 | - |
| 103 | [`castle_door`](#f103-castle-door) | Castle door (castle_kit, 63x145 px) · sheet_struct.png | 68 struct/castle/cdoor- (1) | 1 | 1 | - |
| 104 | [`castle_drawbridge`](#f104-castle-drawbridge) | Drawbridge with chains (castle_kit, 149x192 px) · sheet_struct.png | 68 struct/castle/cdoor- (1) | 1 | 1 | - |
| 105 | [`castle_gatehouse`](#f105-castle-gatehouse) | Castle gatehouse block (castle_kit, 335x389 px) · sheet_struct.png | 67 struct/castle/castl- (1) | 1 | 1 | Structures |
| 106 | [`church_door`](#f106-church-door) | Church door (church, 35x82 px) · sheet_struct.png | 60 struct/church/chrch- (1) | 1 | 1 | - |
| 107 | [`corpse_girl`](#f107-corpse-girl) | Dead girl (npc_girl, 58x37 px) · sheet_people.png | 335 people/girl/death- (1) | 1 | 1 | - |
| 108 | [`corpse_knight`](#f108-corpse-knight) | Dead knight (npc_knight, 81x55 px) · sheet_people.png | 275 people/knight/red/death- (1) | 1 | 1 | - |
| 109 | [`corpse_maiden`](#f109-corpse-maiden) | Dead woman (npc_maiden, 63x47 px) · sheet_people.png | 245 people/maiden/red/death- (1) | 1 | 1 | - |
| 110 | [`corpse_mom`](#f110-corpse-mom) | Dead mother (burnt house) (npc_mom, 68x50 px) · sheet_people.png | 355 people/mom/death- (1) | 1 | 1 | - |
| 111 | [`corpse_peasant`](#f111-corpse-peasant) | Dead peasant (npc_peasant, 114x59 px) · sheet_people.png | 415 people/peasant2/death- (1) | 1 | 1 | - |
| 112 | [`corpse_soldier`](#f112-corpse-soldier) | Dead soldier (npc_soldier, 74x57 px) · sheet_people.png | 405 people/soldier/death- (1) | 1 | 1 | - |
| 113 | [`dink_dead`](#f113-dink-dead) | Dink lying dead (cutscene pose) (dink, 104x90 px) · sheet_dink.png | 436 dink/die/ds-x3- (1) | 1 | 1 | - |
| 114 | [`food_bread`](#f114-food-bread) | Bread loaf (food, 30x25 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 115 | [`food_cheese`](#f115-food-cheese) | Cheese (food, 21x19 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 116 | [`food_drumstick`](#f116-food-drumstick) | Meat drumstick (food, 28x31 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 117 | [`food_grapes`](#f117-food-grapes) | Grapes (food, 29x30 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 118 | [`food_ham`](#f118-food-ham) | Ham / steak (food, 28x28 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 119 | [`king_on_throne`](#f119-king-on-throne) | King Daniel on throne (seated) (npc_king, 124x119 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 120 | [`npc_gnome_purple`](#f120-npc-gnome-purple) | Gnome / wizard (purple) (npc_gnome, 51x74 px) · sheet_people.png | 561 people/gnome/purple/c13w1- (1) | 1 | 1 | - |
| 121 | [`npc_maiden_blue`](#f121-npc-maiden-blue) | Woman (blue dress) (npc_maiden, 55x83 px) · sheet_people.png | 251 people/maiden/blue/c7-w1- (1) | 1 | 1 | - |
| 122 | [`npc_maiden_brown`](#f122-npc-maiden-brown) | Woman (brown dress) (npc_maiden, 55x83 px) · sheet_people.png | 241 people/maiden/brown/c6-w1- (1) | 1 | 1 | - |
| 123 | [`npc_maiden_red`](#f123-npc-maiden-red) | Woman (red dress) (npc_maiden, 55x83 px) · sheet_people.png | 221 people/maiden/red/c4-w1- (1) | 1 | 1 | - |
| 124 | [`npc_old_man`](#f124-npc-old-man) | Old man (npc_oldman, 67x74 px) · sheet_people.png | 231 people/oldman/c1-w1- (1) | 1 | 1 | - |
| 125 | [`npc_soldier`](#f125-npc-soldier) | Soldier (npc_soldier, 76x93 px) · sheet_people.png | 403 people/soldier/c10w3- (1) | 1 | 1 | - |
| 126 | [`ore_rock_blue`](#f126-ore-rock-blue) | Blue crystal rock (boulders, 44x29 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 127 | [`poster_wanted`](#f127-poster-wanted) | "Wanted" poster (signs, 43x61 px) · sheet_inside.png | 462 inner/poster (1) | 1 | 1 | - |
| 128 | [`snow_house_door`](#f128-snow-house-door) | House door (snow_house, 43x78 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 129 | [`snow_house_lower`](#f129-snow-house-lower) | House lower walls (snow_house, 381x188 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 130 | [`snow_house_roof`](#f130-snow-house-roof) | House pyramid roof (snow_house, 404x201 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 131 | [`snow_house_timber`](#f131-snow-house-timber) | House timbered upper walls (snow_house, 400x179 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 132 | [`thorn_branch`](#f132-thorn-branch) | Thorn branch (graveyard, 28x25 px) · sheet_lands.png | 90 lands/details/grave- (1) | 1 | 1 | Vegetation |
| 133 | [`tree_oak_large`](#f133-tree-oak-large) | Broadleaf (oak) tree (trees, 204x270 px) · sheet_lands.png | 32 lands/trees/tree- (1) | 1 | 1 | Vegetation |
| 134 | [`screen ground (tile layer)`](#f134-screen-ground-tile-layer) | tile-layer ground of each screen (grass, sand, water, walls painted into tilesets) · sheet_tiles.png | - | 303 | 0 | Terrain |

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

<a id="f83-corpse-merchant"></a>
**83. `corpse_merchant`** (2 IDs)  
S092: P01 · S094: P01

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

<a id="f107-corpse-girl"></a>
**107. `corpse_girl`** (1 IDs)  
S222: P04

<a id="f108-corpse-knight"></a>
**108. `corpse_knight`** (1 IDs)  
S157: P04

<a id="f109-corpse-maiden"></a>
**109. `corpse_maiden`** (1 IDs)  
S091: P21

<a id="f110-corpse-mom"></a>
**110. `corpse_mom`** (1 IDs)  
S001: P34

<a id="f111-corpse-peasant"></a>
**111. `corpse_peasant`** (1 IDs)  
S222: P05

<a id="f112-corpse-soldier"></a>
**112. `corpse_soldier`** (1 IDs)  
S086: P01

<a id="f113-dink-dead"></a>
**113. `dink_dead`** (1 IDs)  
S058: P06

<a id="f114-food-bread"></a>
**114. `food_bread`** (1 IDs)  
S070: P33

<a id="f115-food-cheese"></a>
**115. `food_cheese`** (1 IDs)  
S070: P26

<a id="f116-food-drumstick"></a>
**116. `food_drumstick`** (1 IDs)  
S070: P23

<a id="f117-food-grapes"></a>
**117. `food_grapes`** (1 IDs)  
S070: P30

<a id="f118-food-ham"></a>
**118. `food_ham`** (1 IDs)  
S070: P32

<a id="f119-king-on-throne"></a>
**119. `king_on_throne`** (1 IDs)  
S070: P03

<a id="f120-npc-gnome-purple"></a>
**120. `npc_gnome_purple`** (1 IDs)  
S006: P23

<a id="f121-npc-maiden-blue"></a>
**121. `npc_maiden_blue`** (1 IDs)  
S004: P16

<a id="f122-npc-maiden-brown"></a>
**122. `npc_maiden_brown`** (1 IDs)  
S410: P06

<a id="f123-npc-maiden-red"></a>
**123. `npc_maiden_red`** (1 IDs)  
S122: P09

<a id="f124-npc-old-man"></a>
**124. `npc_old_man`** (1 IDs)  
S002: P23

<a id="f125-npc-soldier"></a>
**125. `npc_soldier`** (1 IDs)  
S410: P07

<a id="f126-ore-rock-blue"></a>
**126. `ore_rock_blue`** (1 IDs)  
S590: P09

<a id="f127-poster-wanted"></a>
**127. `poster_wanted`** (1 IDs)  
S035: P27

<a id="f128-snow-house-door"></a>
**128. `snow_house_door`** (1 IDs)  
S149: P07

<a id="f129-snow-house-lower"></a>
**129. `snow_house_lower`** (1 IDs)  
S149: P03

<a id="f130-snow-house-roof"></a>
**130. `snow_house_roof`** (1 IDs)  
S149: P08

<a id="f131-snow-house-timber"></a>
**131. `snow_house_timber`** (1 IDs)  
S149: P06

<a id="f132-thorn-branch"></a>
**132. `thorn_branch`** (1 IDs)  
S192: P05

<a id="f133-tree-oak-large"></a>
**133. `tree_oak_large`** (1 IDs)  
S693: P06

<a id="f134-screen-ground-tile-layer"></a>
**134. `screen ground (tile layer)`** (303 IDs)  
SCR 002 003 004 005 006 013 014 015 016 017 018 025 026 027 028 029 030 031 032 033 034 035 036 037 038 045 046 047 048 049 050 057 058 059 060 061 062 063 064 065 066 067 068 069 077 078 079 080 081 082 085 086 089 090 092 093 094 095 096 097 098 099 100 101 109 110 111 112 113 114 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 143 145 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 177 178 179 180 181 182 183 184 185 188 189 190 192 193 194 195 196 197 198 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 241 242 243 244 245 246 247 248 249 250 251 252 254 255 256 257 258 259 260 261 273 274 275 276 277 278 279 280 281 283 284 285 286 287 288 289 290 302 309 310 316 317 318 319 320 339 340 341 342 343 348 349 371 373 374 375 377 385 396 397 410 426 427 428 430 431 432 442 444 445 458 459 460 461 465 490 491 492 493 494 495 496 505 510 520 523 524 525 526 527 528 531 532 534 535 540 542 552 557 558 559 562 563 564 565 566 567 573 579 589 590 591 593 594 595 596 598 606 616 620 621 622 623 624 625 627 630 631 633 637 648 649 652 653 654 655 657 662 664 667 683 684 685 686 687 694 696 713 717 718 719 735 736 749 750 765 766 767
