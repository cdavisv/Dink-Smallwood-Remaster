# Alpha gate 2 backlog: origin IDs still open

Generated 2026-11-16 by `DinkRemasterUE/Scripts/gate2_backlog.py` from `Saved/Import/coverage.csv` (6607 rows, importer run of 2026-11-15) and the manifests under `Content/Dink/Data/Art/`, classified by `Scripts/art_coverage.py`. Do not edit by hand; regenerate.

Alpha gate 2 (`doc/remaster/REMASTER_PLAN.md`): every origin ID is final, placeholder or cut with a reason. This list is what is still open: every origin ID whose art state in `Scripts/art_coverage.py` is `placeholder` (no art bound; nothing in the repo records a placeholder as owner-accepted), plus any unclassified ID. Final (bespoke or by family, `Content/Dink/Data/Art/families.json`) and cut (owner decision of 9 Nov 2026) are closed and not listed.

## Summary

| | open |
|---|---:|
| sprite families | 120 |
| origin IDs | 1195 |
| map placements | 880 |
| screens (ground tile layer) | 303 |
| script warps with their own ID | 12 |
| unclassified IDs | 0 |

Claimed by the Claude photoreal pass (in progress elsewhere, not final): **47 families, 854 origin IDs, 546 placements**. Unclaimed: 73 families, 341 origin IDs, 334 placements.

Largest family by origin IDs: `screen ground (tile layer)` (303 IDs, 0 map placements, so it sorts at #120).

Largest families no stream has claimed: `blood_splat` 46, `tree_fruit` 34, `burn_hole_decal` 26, `npc_knight_blue` 18, `dragon` 16, `arrow_prop` 14, `cave_hole_warp` 10, `log_cabin_window` 9, `stairs_wood` 9, `fish` 8.

Closed for comparison (art_coverage rows): final bespoke 1037, final by family 4178, cut 152, placeholder 1240 of 6607 rows.

## How to regenerate

```bash
cd DinkRemasterUE && python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md
```

Run it in the editor's checkout: like `art_coverage.py` it needs the importer's `Saved/Import/coverage.csv` (`Scripts/import_greybox.sh --region all`), `tools/dinkex/out/sequences.json` and the gitignored engine template content under `Content/Characters` (the mother's locomotion). From another worktree add `--project <editor checkout>/DinkRemasterUE`. The photoreal column is a snapshot of `<--photoreal-root>/*/manifest.json` (default: the uncommitted photoreal pass work copy), read-only; regenerate after that pass lands or binds families.

## Backlog by sprite family

Sorted by open map placements. Family is the class id (`tools/data/sprite_classes.csv`, the key `families.json` binds); *what the original shows* gives its name, sprite group, size and the reference sheet in `doc/remaster/reference/`; *sequences* are the original sprite sequences of the open placements. The origin IDs of each family are listed under [Open origin IDs](#open-origin-ids).

| # | family | what the original sprite sheet shows | sequences (open placements) | origin IDs | placements | photoreal pass |
|---:|---|---|---|---:|---:|---|
| 1 | [`duck_head`](#f1-duck-head) | Duck head (death sprite) used as set dressing (duck, 15x42 px) | seq 121 (90) | 90 | 90 | Creatures |
| 2 | [`town_roof_flat`](#f2-town-roof-flat) | Shingle roof section (town_house_kit, 100x200 px) | seq 33 (52) | 52 | 52 | TownExteriors |
| 3 | [`blood_splat`](#f3-blood-splat) | Blood splatter (blood, 39x56 px) | seq 188 (24), seq 189 (18), seq 187 (4) | 46 | 46 | - |
| 4 | [`castle_wall_diag`](#f4-castle-wall-diag) | Castle curtain wall (diagonal run) (castle_kit, 350x463 px) | seq 67 (46) | 46 | 46 | Structures |
| 5 | [`tree_fruit`](#f5-tree-fruit) | Fruit hanging in a tree (food, 7x12 px) | seq 421 (34) | 34 | 34 | - |
| 6 | [`burn_hole_decal`](#f6-burn-hole-decal) | Burnt hole / scorch mark (damage, 23x20 px) | seq 158 (26) | 26 | 26 | - |
| 7 | [`bridge_wood_deck`](#f7-bridge-wood-deck) | Wooden bridge deck (bridge_wood, 65x88 px) | seq 58 (22) | 22 | 22 | Structures |
| 8 | [`door_wood_single`](#f8-door-wood-single) | Wooden door (doors, 24x64 px) | seq 61 (20) | 22 | 20 | Structures |
| 9 | [`castle_tower_round`](#f9-castle-tower-round) | Round castle tower (castle_kit, 193x409 px) | seq 67 (20) | 20 | 20 | Structures |
| 10 | [`npc_knight_blue`](#f10-npc-knight-blue) | Knight (blue) (npc_knight, 91x125 px) | seq 287 (8), seq 289 (8), seq 281 (1), seq 283 (1) | 18 | 18 | - |
| 11 | [`fence_rail_ns`](#f11-fence-rail-ns) | Rail fence (north-south) (fence_rail, 26x136 px) | seq 93 (17) | 17 | 17 | Structures |
| 12 | [`cottage_door`](#f12-cottage-door) | Cottage door (cottage_thatched, 55x89 px) | seq 63 (16) | 16 | 16 | Structures |
| 13 | [`cottage_thatched_large`](#f13-cottage-thatched-large) | Thatched stone cottage (cottage_thatched, 334x259 px) | seq 63 (16) | 16 | 16 | Structures |
| 14 | [`cottage_thatched_small`](#f14-cottage-thatched-small) | Thatched stone cottage (cottage_thatched, 257x225 px) | seq 63 (16) | 16 | 16 | Structures |
| 15 | [`dragon`](#f15-dragon) | Dragon (dragon, 164x188 px) | seq 202 (8), seq 206 (4), seq 204 (3), seq 208 (1) | 16 | 16 | - |
| 16 | [`town_roof_dormer`](#f16-town-roof-dormer) | Roof section with dormer window (town_house_kit, 100x200 px) | seq 33 (16) | 16 | 16 | TownExteriors |
| 17 | [`door_wood_wide`](#f17-door-wood-wide) | Wide wooden door (doors, 53x68 px) | seq 62 (15) | 15 | 15 | Structures |
| 18 | [`island_fence_lattice`](#f18-island-fence-lattice) | Lashed pole fence (island_village, 271x76 px) | seq 424 (15) | 15 | 15 | Structures |
| 19 | [`town_roof_slope`](#f19-town-roof-slope) | Shingle roof slope (town_house_kit, 100x150 px) | seq 33 (15) | 15 | 15 | TownExteriors |
| 20 | [`arrow_prop`](#f20-arrow-prop) | Arrow (shop display / stuck in ground) (arrow, 47x30 px) | seq 25 (14) | 14 | 14 | - |
| 21 | [`fence_rail_diag_nw`](#f21-fence-rail-diag-nw) | Rail fence diagonal (other) (fence_rail, 77x88 px) | seq 93 (14) | 14 | 14 | Structures |
| 22 | [`town_roof_ridge_cap`](#f22-town-roof-ridge-cap) | Roof ridge / corner cap (town_house_kit, 60x45 px) | seq 33 (14) | 14 | 14 | TownExteriors |
| 23 | [`castle_wall_corner`](#f23-castle-wall-corner) | Castle wall corner (castle_kit, 350x505 px) | seq 67 (12) | 12 | 12 | Structures |
| 24 | [`island_hut_round`](#f24-island-hut-round) | Koka Isle round hut (island_village, 208x178 px) | seq 424 (12) | 12 | 12 | Structures |
| 25 | [`cave_hole_warp`](#f25-cave-hole-warp) | Hole into a cave (warp) (ground_holes, 55x31 px) | seq 89 (10) | 10 | 10 | - |
| 26 | [`island_totem_pole`](#f26-island-totem-pole) | Pole with skull/feather totem (island_village, 27x105 px) | seq 424 (10) | 10 | 10 | Structures |
| 27 | [`fire_fx`](#f27-fire-fx) | Fire (looping flames) (fire, 78x78 px) | seq 427 (9) | 9 | 9 | Props |
| 28 | [`log_cabin_window`](#f28-log-cabin-window) | Log cabin window (log_cabin, 24x28 px) | seq 59 (9) | 9 | 9 | - |
| 29 | [`stairs_wood`](#f29-stairs-wood) | Wooden stairs (stairs, 82x72 px) | seq 428 (9) | 9 | 9 | - |
| 30 | [`fish`](#f30-fish) | Fish (swimming) (fish, 72x52 px) | seq 434 (8) | 8 | 8 | - |
| 31 | [`gold_coin`](#f31-gold-coin) | Single coin (gold, 4x3 px) | seq 178 (8) | 8 | 8 | - |
| 32 | [`ground_crack`](#f32-ground-crack) | Crack in the ground (ground_holes, 88x33 px) | seq 89 (8) | 8 | 8 | - |
| 33 | [`island_torch`](#f33-island-torch) | Bamboo torch / pole (island_village, 85x105 px) | seq 425 (8) | 8 | 8 | Props |
| 34 | [`bridge_wood_rail_plank`](#f34-bridge-wood-rail-plank) | Bridge side rail with planking (bridge_wood, 101x84 px) | seq 58 (7) | 7 | 7 | Structures |
| 35 | [`bridge_wood_rail_rope`](#f35-bridge-wood-rail-rope) | Bridge rope rail (bridge_wood, 101x93 px) | seq 58 (7) | 7 | 7 | Structures |
| 36 | [`cottage_thatched_two_storey`](#f36-cottage-thatched-two-storey) | Two-storey thatched cottage (cottage_thatched, 257x311 px) | seq 63 (7) | 7 | 7 | Structures |
| 37 | [`wall_stripe_red`](#f37-wall-stripe-red) | Red wall stripe / banner (built from the health-bar UI art) (signs, 24x17 px) | seq 450 (7) | 7 | 7 | - |
| 38 | [`cottage_thatched_l_shape`](#f38-cottage-thatched-l-shape) | L-shaped thatched cottage (cottage_thatched, 305x324 px) | seq 63 (6) | 6 | 6 | Structures |
| 39 | [`fence_rail_diag_ne`](#f39-fence-rail-diag-ne) | Rail fence diagonal (fence_rail, 69x90 px) | seq 93 (6) | 6 | 6 | Structures |
| 40 | [`goblin_soldier`](#f40-goblin-soldier) | Goblin soldier (goblin, 107x130 px) | seq 809 (3), seq 801 (2), seq 803 (1) | 6 | 6 | - |
| 41 | [`small_fire_fx`](#f41-small-fire-fx) | Small fire on floor (fire, 23x20 px) | seq 155 (2), seq 156 (2), seq 157 (2) | 6 | 6 | Props |
| 42 | [`ground_hole_dark`](#f42-ground-hole-dark) | Dark hole in the ground (ground_holes, 55x73 px) | seq 89 (5) | 10 | 5 | - |
| 43 | [`chimney_stone`](#f43-chimney-stone) | Stone chimney (cottage_thatched, 55x58 px) | seq 63 (5) | 5 | 5 | Structures |
| 44 | [`shop_sign`](#f44-shop-sign) | Hanging sign (red cross: healer) (signs, 63x76 px) | seq 458 (5) | 5 | 5 | - |
| 45 | [`well_stone`](#f45-well-stone) | Stone well with roof (landmarks, 107x136 px) | seq 186 (5) | 5 | 5 | Structures |
| 46 | [`tree_pine_large`](#f46-tree-pine-large) | Pine tree (trees, 128x188 px) | seq 32 (4) | 7 | 4 | Vegetation |
| 47 | [`npc_knight_silver`](#f47-npc-knight-silver) | Knight (silver) (npc_knight, 110x117 px) | seq 293 (2), seq 299 (1), seq 291 (1) | 6 | 4 | - |
| 48 | [`boulder_flat`](#f48-boulder-flat) | Flat boulder (boulders, 72x63 px) | seq 95 (4) | 4 | 4 | - |
| 49 | [`bridge_stone`](#f49-bridge-stone) | Stone arch bridge (bridge_stone, 288x212 px) | seq 186 (4) | 4 | 4 | Structures |
| 50 | [`cottage_thatched_long`](#f50-cottage-thatched-long) | Thatched stone cottage (cottage_thatched, 332x260 px) | seq 63 (4) | 4 | 4 | Structures |
| 51 | [`fish_flopping`](#f51-fish-flopping) | Fish flopping on land (fish, 33x34 px) | seq 439 (3), seq 441 (1) | 4 | 4 | - |
| 52 | [`food_fruit`](#f52-food-fruit) | Fruit (apple / pear / etc.) (food, 17x23 px) | seq 421 (4) | 4 | 4 | - |
| 53 | [`goblin_hammer`](#f53-goblin-hammer) | Goblin (hammer) (goblin, 56x109 px) | seq 763 (2), seq 761 (1), seq 769 (1) | 4 | 4 | - |
| 54 | [`island_hut_two_storey`](#f54-island-hut-two-storey) | Two-tier round hut (island_village, 238x265 px) | seq 424 (4) | 4 | 4 | Structures |
| 55 | [`npc_girl`](#f55-npc-girl) | Girl (child) (npc_girl, 53x62 px) | seq 331 (3), seq 339 (1) | 4 | 4 | - |
| 56 | [`npc_knight_red`](#f56-npc-knight-red) | Knight (red) (npc_knight, 91x125 px) | seq 273 (2), seq 279 (1), seq 277 (1) | 4 | 4 | - |
| 57 | [`poster_hark`](#f57-poster-hark) | "Hark!" notice (signs, 43x61 px) | seq 462 (4) | 4 | 4 | - |
| 58 | [`bomb_item`](#f58-bomb-item) | Bomb (items, 26x33 px) | seq 420 (3) | 3 | 3 | - |
| 59 | [`cabinet_wood`](#f59-cabinet-wood) | Wooden cabinet / dresser (house_interior, 57x79 px) | seq 87 (3) | 3 | 3 | Props |
| 60 | [`church`](#f60-church) | Stone church (church, 417x433 px) | seq 60 (3) | 3 | 3 | - |
| 61 | [`church_stained_glass`](#f61-church-stained-glass) | Stained-glass window (church, 56x94 px) | seq 60 (3) | 3 | 3 | - |
| 62 | [`fireplace_brick`](#f62-fireplace-brick) | Brick fireplace (house_interior, 97x114 px) | seq 64 (3) | 3 | 3 | Props |
| 63 | [`pillbug_corpse`](#f63-pillbug-corpse) | Pillbug death splat (pillbug, 46x35 px) | seq 141 (2), seq 143 (1) | 3 | 3 | Creatures |
| 64 | [`boulder_large`](#f64-boulder-large) | Large dark boulder (boulders, 103x95 px) | seq 95 (2) | 2 | 2 | - |
| 65 | [`boulder_red`](#f65-boulder-red) | Reddish boulder (boulders, 100x79 px) | seq 95 (2) | 2 | 2 | - |
| 66 | [`burnt_floor_hole`](#f66-burnt-floor-hole) | Burnt hole in floor/roof (large) (damage, 90x69 px) | seq 158 (2) | 2 | 2 | - |
| 67 | [`castle_wall_end`](#f67-castle-wall-end) | Castle wall end (edge-on) (castle_kit, 100x340 px) | seq 67 (2) | 2 | 2 | Structures |
| 68 | [`cellar_hatch`](#f68-cellar-hatch) | Cellar hatch / ladder (stairs, 35x57 px) | seq 428 (2) | 2 | 2 | - |
| 69 | [`chest_large`](#f69-chest-large) | Treasure chest (large) (chests, 60x60 px) | seq 177 (2) | 2 | 2 | Props |
| 70 | [`chest_medium`](#f70-chest-medium) | Treasure chest (chests, 44x55 px) | seq 176 (2) | 2 | 2 | Props |
| 71 | [`church_window_small`](#f71-church-window-small) | Church small window (church, 19x27 px) | seq 60 (2) | 2 | 2 | - |
| 72 | [`dragon_corpse`](#f72-dragon-corpse) | Dead dragon (dragon, 105x122 px) | seq 212 (2) | 2 | 2 | - |
| 73 | [`duck_corpse`](#f73-duck-corpse) | Dead duck body (duck, 20x30 px) | seq 127 (1), seq 121 (1) | 2 | 2 | Creatures |
| 74 | [`explosion_fx`](#f74-explosion-fx) | Explosion (, 60x61 px) | seq 70 (2) | 2 | 2 | - |
| 75 | [`fire_burst_fx`](#f75-fire-burst-fx) | Fire burst (atomic explosion frames) (, 93x141 px) | seq 161 (2) | 2 | 2 | - |
| 76 | [`fireball_fx`](#f76-fireball-fx) | Fireball (vertical) (, 32x76 px) | seq 512 (2) | 2 | 2 | - |
| 77 | [`food_pie`](#f77-food-pie) | Pie (food, 24x19 px) | seq 421 (2) | 2 | 2 | Props |
| 78 | [`fountain_spray_fx`](#f78-fountain-spray-fx) | Fountain water spray (fountain, 80x84 px) | seq 94 (2) | 2 | 2 | - |
| 79 | [`hearth_fire`](#f79-hearth-fire) | Fireplace fire (house_interior, 46x55 px) | seq 86 (2) | 2 | 2 | - |
| 80 | [`log_cabin`](#f80-log-cabin) | Log cabin (log_cabin, 322x232 px) | seq 59 (2) | 2 | 2 | - |
| 81 | [`log_cabin_door`](#f81-log-cabin-door) | Log cabin door (log_cabin, 34x69 px) | seq 59 (2) | 2 | 2 | - |
| 82 | [`npc_knight_red_attacking`](#f82-npc-knight-red-attacking) | Knight (red) attack pose (npc_knight, 121x127 px) | seq 712 (2) | 2 | 2 | - |
| 83 | [`npc_merchant_blue`](#f83-npc-merchant-blue) | Merchant (blue) (npc_merchant, 55x93 px) | seq 371 (2) | 2 | 2 | - |
| 84 | [`npc_merchant_green`](#f84-npc-merchant-green) | Merchant (green) (npc_merchant, 55x93 px) | seq 381 (2) | 2 | 2 | - |
| 85 | [`npc_peasant`](#f85-npc-peasant) | Peasant (npc_peasant, 73x121 px) | seq 411 (2) | 2 | 2 | - |
| 86 | [`sparkle_fx`](#f86-sparkle-fx) | Sparkle (, 20x20 px) | seq 165 (1), seq 166 (1) | 2 | 2 | - |
| 87 | [`tree_willow`](#f87-tree-willow) | Weeping (willow-like) tree (trees, 169x252 px) | seq 32 (2) | 2 | 2 | Vegetation |
| 88 | [`tree_willow_large`](#f88-tree-willow-large) | Large weeping tree (trees, 249x300 px) | seq 32 (2) | 2 | 2 | Vegetation |
| 89 | [`boulder_grey_tall`](#f89-boulder-grey-tall) | Tall grey boulder (boulders, 54x77 px) | seq 95 (1) | 1 | 1 | - |
| 90 | [`boulder_white_pair`](#f90-boulder-white-pair) | Pair of white boulders (boulders, 80x58 px) | seq 95 (1) | 1 | 1 | - |
| 91 | [`burn_damage_decal`](#f91-burn-damage-decal) | Burn damage / scorch with fire (damage, 90x69 px) | seq 154 (1) | 1 | 1 | - |
| 92 | [`castle_door`](#f92-castle-door) | Castle door (castle_kit, 63x145 px) | seq 68 (1) | 1 | 1 | - |
| 93 | [`castle_drawbridge`](#f93-castle-drawbridge) | Drawbridge with chains (castle_kit, 149x192 px) | seq 68 (1) | 1 | 1 | - |
| 94 | [`castle_gatehouse`](#f94-castle-gatehouse) | Castle gatehouse block (castle_kit, 335x389 px) | seq 67 (1) | 1 | 1 | Structures |
| 95 | [`church_door`](#f95-church-door) | Church door (church, 35x82 px) | seq 60 (1) | 1 | 1 | - |
| 96 | [`corpse_mom`](#f96-corpse-mom) | Dead mother (burnt house) (npc_mom, 68x50 px) | seq 355 (1) | 1 | 1 | - |
| 97 | [`corpse_soldier`](#f97-corpse-soldier) | Dead soldier (npc_soldier, 74x57 px) | seq 405 (1) | 1 | 1 | - |
| 98 | [`dink_dead`](#f98-dink-dead) | Dink lying dead (cutscene pose) (dink, 104x90 px) | seq 436 (1) | 1 | 1 | - |
| 99 | [`food_bread`](#f99-food-bread) | Bread loaf (food, 30x25 px) | seq 421 (1) | 1 | 1 | - |
| 100 | [`food_cheese`](#f100-food-cheese) | Cheese (food, 21x19 px) | seq 421 (1) | 1 | 1 | - |
| 101 | [`food_drumstick`](#f101-food-drumstick) | Meat drumstick (food, 28x31 px) | seq 421 (1) | 1 | 1 | - |
| 102 | [`food_grapes`](#f102-food-grapes) | Grapes (food, 29x30 px) | seq 421 (1) | 1 | 1 | - |
| 103 | [`food_ham`](#f103-food-ham) | Ham / steak (food, 28x28 px) | seq 421 (1) | 1 | 1 | - |
| 104 | [`king_on_throne`](#f104-king-on-throne) | King Daniel on throne (seated) (npc_king, 124x119 px) | seq 421 (1) | 1 | 1 | - |
| 105 | [`npc_gnome_purple`](#f105-npc-gnome-purple) | Gnome / wizard (purple) (npc_gnome, 51x74 px) | seq 561 (1) | 1 | 1 | - |
| 106 | [`npc_maiden_blue`](#f106-npc-maiden-blue) | Woman (blue dress) (npc_maiden, 55x83 px) | seq 251 (1) | 1 | 1 | - |
| 107 | [`npc_maiden_brown`](#f107-npc-maiden-brown) | Woman (brown dress) (npc_maiden, 55x83 px) | seq 241 (1) | 1 | 1 | - |
| 108 | [`npc_maiden_red`](#f108-npc-maiden-red) | Woman (red dress) (npc_maiden, 55x83 px) | seq 221 (1) | 1 | 1 | - |
| 109 | [`npc_mom`](#f109-npc-mom) | Dink's mother (npc_mom, 59x88 px) | seq 351 (1) | 1 | 1 | - |
| 110 | [`npc_old_man`](#f110-npc-old-man) | Old man (npc_oldman, 67x74 px) | seq 231 (1) | 1 | 1 | - |
| 111 | [`npc_soldier`](#f111-npc-soldier) | Soldier (npc_soldier, 76x93 px) | seq 403 (1) | 1 | 1 | - |
| 112 | [`ore_rock_blue`](#f112-ore-rock-blue) | Blue crystal rock (boulders, 44x29 px) | seq 95 (1) | 1 | 1 | - |
| 113 | [`poster_wanted`](#f113-poster-wanted) | "Wanted" poster (signs, 43x61 px) | seq 462 (1) | 1 | 1 | - |
| 114 | [`snow_house_door`](#f114-snow-house-door) | House door (snow_house, 43x78 px) | seq 96 (1) | 1 | 1 | - |
| 115 | [`snow_house_lower`](#f115-snow-house-lower) | House lower walls (snow_house, 381x188 px) | seq 96 (1) | 1 | 1 | - |
| 116 | [`snow_house_roof`](#f116-snow-house-roof) | House pyramid roof (snow_house, 404x201 px) | seq 96 (1) | 1 | 1 | - |
| 117 | [`snow_house_timber`](#f117-snow-house-timber) | House timbered upper walls (snow_house, 400x179 px) | seq 96 (1) | 1 | 1 | - |
| 118 | [`thorn_branch`](#f118-thorn-branch) | Thorn branch (graveyard, 28x25 px) | seq 90 (1) | 1 | 1 | Vegetation |
| 119 | [`tree_oak_large`](#f119-tree-oak-large) | Broadleaf (oak) tree (trees, 204x270 px) | seq 32 (1) | 1 | 1 | Vegetation |
| 120 | [`screen ground (tile layer)`](#f120-screen-ground-tile-layer) | tile-layer ground of each screen (grass, sand, water, walls painted into tilesets) · sheet_tiles.png | - | 303 | 0 | Terrain |

## Open origin IDs

Placements as `Snnn: Pnn ...` (screen, then slot), screens as `SCR nnn ...`, script warps by full ID.

<a id="f1-duck-head"></a>
**1. `duck_head`** (90 IDs)  
S145: P01 P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22 P23 P24 P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 P35 P36 P37 P38 P39 P40 P41 P42 P43 P44 P45 P46 P47 P48 P49 P50 P51 P52 P53 P54 P55 P56 P57 P58 P59 P60 P61 P62 P63 P64 P65 P66 P67 P68 P69 P70 P71 P72 P73 P74 P75 P76 P77 P78 P79 P80 P81 P82 P83 P84 P85 P86 P87 P88 P89 P90

<a id="f2-town-roof-flat"></a>
**2. `town_roof_flat`** (52 IDs)  
S187: P08 · S219: P02 · S385: P13 P14 P17 · S386: P07 P08 P09 P10 P11 P12 P13 · S387: P08 P09 P10 P11 P12 P13 P14 · S388: P12 P13 · S417: P05 P13 · S418: P07 P11 P12 · S419: P01 P10 · S465: P01 · S466: P01 P05 P06 P07 P08 P09 · S467: P06 · S473: P02 P04 P06 P07 · S474: P20 · S498: P09 · S505: P06 P09 P10 · S506: P07 P30 · S538: P05 · S553: P06 P08 · S555: P03 P04

<a id="f3-blood-splat"></a>
**3. `blood_splat`** (46 IDs)  
S060: P06 P07 · S061: P07 P08 · S091: P06 P07 P08 P09 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 · S094: P02 P03 P04 P05 P06 P07 P08 · S122: P11 P12 P13 · S126: P02 P03 P04 P05 · S154: P22 P39 P40 P41 P42 P43 · S158: P06 · S190: P06 P07 P08 P09 · S191: P06 P07

<a id="f4-castle-wall-diag"></a>
**4. `castle_wall_diag`** (46 IDs)  
S014: P01 · S015: P01 P02 P03 · S016: P01 P02 P06 · S017: P01 · S018: P02 · S047: P01 P03 P04 · S048: P01 P02 P03 P04 P06 · S049: P01 P02 · S050: P01 · S070: P01 · S078: P01 · S079: P03 · S080: P01 P02 · S081: P01 · S336: P03 P04 · S367: P01 P04 · S368: P01 P03 P04 · S370: P02 · S399: P01 · S400: P01 P02 · S401: P01 P03 P04 · S402: P02 P07 P08 · S432: P01 · S433: P02 P05

<a id="f5-tree-fruit"></a>
**5. `tree_fruit`** (34 IDs)  
S442: P02 P04 P05 P06 P07 P08 P09 P10 P11 P12 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S474: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P15 P16 P17

<a id="f6-burn-hole-decal"></a>
**6. `burn_hole_decal`** (26 IDs)  
S001: P44 P45 P46 P47 P48 P49 · S005: P25 P26 P27 · S066: P23 P24 · S439: P23 P24 P25 P26 P27 P28 P30 P36 P37 P46 · S533: P21 P22 P23 · S536: P16 P26

<a id="f7-bridge-wood-deck"></a>
**7. `bridge_wood_deck`** (22 IDs)  
S416: P01 P02 · S448: P01 P02 P03 P04 P05 P06 P07 · S480: P01 P02 P03 · S512: P01 P02 · S533: P01 P02 P03 P25 · S544: P01 P02 · S701: P01 P02

<a id="f8-door-wood-single"></a>
**8. `door_wood_single`** (22 IDs)  
S188: P10 · S219: P10 · S251: P09 · S274: P07 · S409: P16 · S418: P16 · S419: P02 · S497: P12 · S498: P11 · S499: P07 · S500: P06 · S501: P11 · S506: P20 · S530: P11 · S539: P12 · S585: P14 · S587: P12 · S617: P15 · S619: P09 · S734: P31 · SW_s2-mdoor_L106@S530_P11 · SW_s2-mdoor_L82@S530_P11

<a id="f9-castle-tower-round"></a>
**9. `castle_tower_round`** (20 IDs)  
S018: P01 · S047: P02 · S049: P03 · S050: P02 · S070: P02 · S078: P02 · S079: P01 P04 · S080: P03 · S112: P01 · S336: P01 · S337: P05 · S367: P03 · S368: P07 · S369: P03 · S370: P01 · S399: P03 · S401: P02 · S402: P01 · S433: P01

<a id="f10-npc-knight-blue"></a>
**10. `npc_knight_blue`** (18 IDs)  
S070: P13 P14 P15 P16 P17 P18 · S102: P05 P06 P07 P08 P09 P10 P11 P12 P13 P14 · S243: P11 P12

<a id="f11-fence-rail-ns"></a>
**11. `fence_rail_ns`** (17 IDs)  
S375: P02 P03 · S408: P21 P22 P23 P24 · S409: P08 P41 P52 · S441: P06 P07 P08 P31 · S469: P09 P10 · S536: P28 P42

<a id="f12-cottage-door"></a>
**12. `cottage_door`** (16 IDs)  
S274: P15 · S350: P08 · S440: P04 · S469: P06 · S497: P07 · S500: P04 · S501: P06 P10 · S530: P04 · S532: P09 · S537: P05 · S617: P14 · S618: P09 · S619: P08 P10 · S734: P03

<a id="f13-cottage-thatched-large"></a>
**13. `cottage_thatched_large`** (16 IDs)  
S409: P12 P14 · S437: P12 P21 · S468: P04 P05 · S469: P02 P05 · S470: P01 P03 · S501: P02 · S587: P05 · S618: P01 P12 · S619: P03 P07

<a id="f14-cottage-thatched-small"></a>
**14. `cottage_thatched_small`** (16 IDs)  
S274: P02 P03 · S469: P01 · S497: P05 P06 · S500: P12 · S501: P01 P03 P05 P09 · S532: P01 P10 · S537: P04 P23 · S619: P02 P11

<a id="f15-dragon"></a>
**15. `dragon`** (16 IDs)  
S074: P21 P22 · S123: P07 · S124: P03 P04 · S127: P07 P08 P09 P10 · S156: P08 · S159: P06 P07 P08 P09 · S160: P06 · S191: P11

<a id="f16-town-roof-dormer"></a>
**16. `town_roof_dormer`** (16 IDs)  
S187: P07 P09 · S218: P21 · S219: P01 P03 · S465: P03 · S466: P04 · S472: P10 · S473: P05 P08 · S474: P21 · S498: P08 · S505: P07 · S506: P08 P25 · S538: P06

<a id="f17-door-wood-wide"></a>
**17. `door_wood_wide`** (15 IDs)  
S350: P09 · S440: P06 · S469: P20 · S497: P13 P15 · S498: P10 · S501: P12 · S504: P15 · S505: P01 · S532: P11 · S537: P24 · S538: P21 · S585: P13 · S618: P11 · S619: P12

<a id="f18-island-fence-lattice"></a>
**18. `island_fence_lattice`** (15 IDs)  
S489: P03 · S711: P07 · S712: P03 · S731: P03 P10 P11 P12 P13 P14 · S732: P02 · S762: P08 P09 · S763: P07 P20 · S764: P09

<a id="f19-town-roof-slope"></a>
**19. `town_roof_slope`** (15 IDs)  
S186: P23 · S187: P10 · S218: P20 · S385: P16 · S388: P14 · S465: P07 · S467: P03 · S472: P06 · S474: P22 · S507: P07 · S553: P02 P05 · S554: P03 P06 · S555: P02

<a id="f20-arrow-prop"></a>
**20. `arrow_prop`** (14 IDs)  
S097: P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 · S663: P20 P21 P22 P23

<a id="f21-fence-rail-diag-nw"></a>
**21. `fence_rail_diag_nw`** (14 IDs)  
S409: P19 P20 P21 P42 · S437: P08 P09 P10 P11 P13 P14 P15 P34 · S568: P13 P14

<a id="f22-town-roof-ridge-cap"></a>
**22. `town_roof_ridge_cap`** (14 IDs)  
S186: P51 · S187: P12 · S385: P18 · S388: P18 · S465: P04 · S467: P04 · S472: P02 · S474: P23 · S507: P08 · S553: P03 P07 · S554: P02 P05 · S555: P05

<a id="f23-castle-wall-corner"></a>
**23. `castle_wall_corner`** (12 IDs)  
S016: P04 P05 · S017: P02 P03 · S018: P03 · S070: P04 · S337: P02 P04 · S369: P01 P02 · S370: P04 · S402: P09

<a id="f24-island-hut-round"></a>
**24. `island_hut_round`** (12 IDs)  
S489: P02 · S680: P10 · S681: P12 · S712: P13 · S732: P01 · S748: P01 · S762: P01 · S763: P02 P03 P05 · S764: P02 P03

<a id="f25-cave-hole-warp"></a>
**25. `cave_hole_warp`** (10 IDs)  
S085: P01 · S112: P02 · S144: P04 · S182: P01 · S209: P01 · S248: P01 · S254: P04 · S483: P11 · S625: P05 · S671: P01

<a id="f26-island-totem-pole"></a>
**26. `island_totem_pole`** (10 IDs)  
S100: P01 · S366: P07 P08 · S684: P01 · S713: P09 · S716: P01 P02 · S762: P10 P11 P12

<a id="f27-fire-fx"></a>
**27. `fire_fx`** (9 IDs)  
S001: P21 P27 P30 P31 P32 · S439: P05 P09 P11 P21

<a id="f28-log-cabin-window"></a>
**28. `log_cabin_window`** (9 IDs)  
S251: P08 · S274: P16 · S409: P11 · S440: P08 P09 · S500: P05 · S501: P07 P08 · S530: P05

<a id="f29-stairs-wood"></a>
**29. `stairs_wood`** (9 IDs)  
S003: P28 P29 · S004: P13 · S036: P27 · S037: P13 · S163: P27 P28 · S228: P23 · S229: P01

<a id="f30-fish"></a>
**30. `fish`** (8 IDs)  
S634: P01 P02 P03 · S665: P03 · S697: P02 P03 P04 · S727: P17

<a id="f31-gold-coin"></a>
**31. `gold_coin`** (8 IDs)  
S505: P15 · S537: P10 P11 P12 P13 · S663: P03 P17 P18

<a id="f32-ground-crack"></a>
**32. `ground_crack`** (8 IDs)  
S005: P19 · S066: P29 · S154: P03 P04 P06 P09 P10 · S193: P23

<a id="f33-island-torch"></a>
**33. `island_torch`** (8 IDs)  
S731: P02 · S762: P02 · S763: P06 P18 P19 · S764: P04 P05 P07

<a id="f34-bridge-wood-rail-plank"></a>
**34. `bridge_wood_rail_plank`** (7 IDs)  
S404: P01 P04 · S512: P03 P04 P05 · S693: P28 P29

<a id="f35-bridge-wood-rail-rope"></a>
**35. `bridge_wood_rail_rope`** (7 IDs)  
S404: P03 P05 · S512: P06 P07 P08 · S693: P30 P31

<a id="f36-cottage-thatched-two-storey"></a>
**36. `cottage_thatched_two_storey`** (7 IDs)  
S440: P03 P11 · S500: P01 P02 · S586: P04 · S618: P02 P10

<a id="f37-wall-stripe-red"></a>
**37. `wall_stripe_red`** (7 IDs)  
S097: P35 P36 P37 P38 P39 P40 P41

<a id="f38-cottage-thatched-l-shape"></a>
**38. `cottage_thatched_l_shape`** (6 IDs)  
S318: P01 · S349: P04 · S350: P01 P02 · S734: P01 P02

<a id="f39-fence-rail-diag-ne"></a>
**39. `fence_rail_diag_ne`** (6 IDs)  
S441: P05 P12 P13 P14 · S469: P07 P08

<a id="f40-goblin-soldier"></a>
**40. `goblin_soldier`** (6 IDs)  
S680: P11 P12 · S712: P15 P17 · S713: P11 P12

<a id="f41-small-fire-fx"></a>
**41. `small_fire_fx`** (6 IDs)  
S001: P35 P36 P38 · S439: P31 P32 P33

<a id="f42-ground-hole-dark"></a>
**42. `ground_hole_dark`** (10 IDs)  
S132: P01 · S180: P01 · S209: P04 · S243: P13 · S277: P02 · SW_s1-hole3_L22@S209_P04 · SW_s1-hole_L21@S132_P01 · SW_s1-hole_L21@S277_P02 · SW_s6-hole2_L22@S180_P01 · SW_s6-hole_L22@S243_P13

<a id="f43-chimney-stone"></a>
**43. `chimney_stone`** (5 IDs)  
S469: P03 P04 · S500: P03 · S530: P10 · S734: P04

<a id="f44-shop-sign"></a>
**44. `shop_sign`** (5 IDs)  
S498: P13 P14 · S504: P17 · S538: P22 · S539: P05

<a id="f45-well-stone"></a>
**45. `well_stone`** (5 IDs)  
S408: P07 · S432: P03 · S497: P09 · S600: P01 · S766: P04

<a id="f46-tree-pine-large"></a>
**46. `tree_pine_large`** (7 IDs)  
S307: P13 · S534: P10 · S659: P06 · S710: P14 · SW_s2-sec1_L37@S307_P13 · SW_s2-sec3_L37@S659_P06 · SW_s3-sec1_L39@S710_P14

<a id="f47-npc-knight-silver"></a>
**47. `npc_knight_silver`** (6 IDs)  
S402: P03 P05 · S408: P04 · S568: P06 · SW_s2-ca-g_L179@S402_P03 · SW_s2-ca-g_L179@S402_P05

<a id="f48-boulder-flat"></a>
**48. `boulder_flat`** (4 IDs)  
S535: P12 · S590: P03 P10 P11

<a id="f49-bridge-stone"></a>
**49. `bridge_stone`** (4 IDs)  
S102: P01 P02 P03 P04

<a id="f50-cottage-thatched-long"></a>
**50. `cottage_thatched_long`** (4 IDs)  
S530: P01 P03 · S617: P01 P13

<a id="f51-fish-flopping"></a>
**51. `fish_flopping`** (4 IDs)  
S734: P09 · S760: P01 P02 P03

<a id="f52-food-fruit"></a>
**52. `food_fruit`** (4 IDs)  
S070: P31 P35 P36 P37

<a id="f53-goblin-hammer"></a>
**53. `goblin_hammer`** (4 IDs)  
S680: P13 P14 · S712: P12 · S748: P03

<a id="f54-island-hut-two-storey"></a>
**54. `island_hut_two_storey`** (4 IDs)  
S680: P09 · S681: P13 · S763: P04 · S764: P01

<a id="f55-npc-girl"></a>
**55. `npc_girl`** (4 IDs)  
S091: P22 · S122: P10 · S126: P06 P07

<a id="f56-npc-knight-red"></a>
**56. `npc_knight_red`** (4 IDs)  
S149: P05 P09 · S374: P03 P04

<a id="f57-poster-hark"></a>
**57. `poster_hark`** (4 IDs)  
S033: P30 · S195: P30 · S225: P30 · S226: P30

<a id="f58-bomb-item"></a>
**58. `bomb_item`** (3 IDs)  
S228: P40 P41 P42

<a id="f59-cabinet-wood"></a>
**59. `cabinet_wood`** (3 IDs)  
S003: P15 P16 · S366: P15

<a id="f60-church"></a>
**60. `church`** (3 IDs)  
S187: P02 · S188: P03 P05

<a id="f61-church-stained-glass"></a>
**61. `church_stained_glass`** (3 IDs)  
S188: P07 P08 P09

<a id="f62-fireplace-brick"></a>
**62. `fireplace_brick`** (3 IDs)  
S038: P16 · S129: P24 · S163: P23

<a id="f63-pillbug-corpse"></a>
**63. `pillbug_corpse`** (3 IDs)  
S098: P04 · S100: P25 P26

<a id="f64-boulder-large"></a>
**64. `boulder_large`** (2 IDs)  
S277: P03 · S590: P01

<a id="f65-boulder-red"></a>
**65. `boulder_red`** (2 IDs)  
S536: P15 · S590: P04

<a id="f66-burnt-floor-hole"></a>
**66. `burnt_floor_hole`** (2 IDs)  
S439: P34 P38

<a id="f67-castle-wall-end"></a>
**67. `castle_wall_end`** (2 IDs)  
S016: P03 · S048: P05

<a id="f68-cellar-hatch"></a>
**68. `cellar_hatch`** (2 IDs)  
S068: P24 P25

<a id="f69-chest-large"></a>
**69. `chest_large`** (2 IDs)  
S098: P07 · S536: P31

<a id="f70-chest-medium"></a>
**70. `chest_medium`** (2 IDs)  
S026: P06 · S284: P04

<a id="f71-church-window-small"></a>
**71. `church_window_small`** (2 IDs)  
S187: P01 P03

<a id="f72-dragon-corpse"></a>
**72. `dragon_corpse`** (2 IDs)  
S100: P34 · S238: P12

<a id="f73-duck-corpse"></a>
**73. `duck_corpse`** (2 IDs)  
S100: P27 · S521: P05

<a id="f74-explosion-fx"></a>
**74. `explosion_fx`** (2 IDs)  
S001: P28 P29

<a id="f75-fire-burst-fx"></a>
**75. `fire_burst_fx`** (2 IDs)  
S001: P33 P41

<a id="f76-fireball-fx"></a>
**76. `fireball_fx`** (2 IDs)  
S366: P09 P14

<a id="f77-food-pie"></a>
**77. `food_pie`** (2 IDs)  
S070: P24 P25

<a id="f78-fountain-spray-fx"></a>
**78. `fountain_spray_fx`** (2 IDs)  
S260: P30 · S586: P14

<a id="f79-hearth-fire"></a>
**79. `hearth_fire`** (2 IDs)  
S001: P20 · S163: P24

<a id="f80-log-cabin"></a>
**80. `log_cabin`** (2 IDs)  
S251: P01 · S270: P07

<a id="f81-log-cabin-door"></a>
**81. `log_cabin_door`** (2 IDs)  
S251: P07 · S409: P13

<a id="f82-npc-knight-red-attacking"></a>
**82. `npc_knight_red_attacking`** (2 IDs)  
S241: P03 · S242: P03

<a id="f83-npc-merchant-blue"></a>
**83. `npc_merchant_blue`** (2 IDs)  
S290: P30 · S374: P05

<a id="f84-npc-merchant-green"></a>
**84. `npc_merchant_green`** (2 IDs)  
S164: P02 · S227: P02

<a id="f85-npc-peasant"></a>
**85. `npc_peasant`** (2 IDs)  
S003: P23 · S038: P22

<a id="f86-sparkle-fx"></a>
**86. `sparkle_fx`** (2 IDs)  
S001: P37 · S045: P01

<a id="f87-tree-willow"></a>
**87. `tree_willow`** (2 IDs)  
S414: P02 · S446: P02

<a id="f88-tree-willow-large"></a>
**88. `tree_willow_large`** (2 IDs)  
S149: P02 · S474: P01

<a id="f89-boulder-grey-tall"></a>
**89. `boulder_grey_tall`** (1 IDs)  
S601: P08

<a id="f90-boulder-white-pair"></a>
**90. `boulder_white_pair`** (1 IDs)  
S590: P02

<a id="f91-burn-damage-decal"></a>
**91. `burn_damage_decal`** (1 IDs)  
S439: P29

<a id="f92-castle-door"></a>
**92. `castle_door`** (1 IDs)  
S402: P04

<a id="f93-castle-drawbridge"></a>
**93. `castle_drawbridge`** (1 IDs)  
S080: P05

<a id="f94-castle-gatehouse"></a>
**94. `castle_gatehouse`** (1 IDs)  
S080: P04

<a id="f95-church-door"></a>
**95. `church_door`** (1 IDs)  
S188: P06

<a id="f96-corpse-mom"></a>
**96. `corpse_mom`** (1 IDs)  
S001: P34

<a id="f97-corpse-soldier"></a>
**97. `corpse_soldier`** (1 IDs)  
S086: P01

<a id="f98-dink-dead"></a>
**98. `dink_dead`** (1 IDs)  
S058: P06

<a id="f99-food-bread"></a>
**99. `food_bread`** (1 IDs)  
S070: P33

<a id="f100-food-cheese"></a>
**100. `food_cheese`** (1 IDs)  
S070: P26

<a id="f101-food-drumstick"></a>
**101. `food_drumstick`** (1 IDs)  
S070: P23

<a id="f102-food-grapes"></a>
**102. `food_grapes`** (1 IDs)  
S070: P30

<a id="f103-food-ham"></a>
**103. `food_ham`** (1 IDs)  
S070: P32

<a id="f104-king-on-throne"></a>
**104. `king_on_throne`** (1 IDs)  
S070: P03

<a id="f105-npc-gnome-purple"></a>
**105. `npc_gnome_purple`** (1 IDs)  
S006: P23

<a id="f106-npc-maiden-blue"></a>
**106. `npc_maiden_blue`** (1 IDs)  
S004: P16

<a id="f107-npc-maiden-brown"></a>
**107. `npc_maiden_brown`** (1 IDs)  
S410: P06

<a id="f108-npc-maiden-red"></a>
**108. `npc_maiden_red`** (1 IDs)  
S122: P09

<a id="f109-npc-mom"></a>
**109. `npc_mom`** (1 IDs)  
S001: P26

<a id="f110-npc-old-man"></a>
**110. `npc_old_man`** (1 IDs)  
S002: P23

<a id="f111-npc-soldier"></a>
**111. `npc_soldier`** (1 IDs)  
S410: P07

<a id="f112-ore-rock-blue"></a>
**112. `ore_rock_blue`** (1 IDs)  
S590: P09

<a id="f113-poster-wanted"></a>
**113. `poster_wanted`** (1 IDs)  
S035: P27

<a id="f114-snow-house-door"></a>
**114. `snow_house_door`** (1 IDs)  
S149: P07

<a id="f115-snow-house-lower"></a>
**115. `snow_house_lower`** (1 IDs)  
S149: P03

<a id="f116-snow-house-roof"></a>
**116. `snow_house_roof`** (1 IDs)  
S149: P08

<a id="f117-snow-house-timber"></a>
**117. `snow_house_timber`** (1 IDs)  
S149: P06

<a id="f118-thorn-branch"></a>
**118. `thorn_branch`** (1 IDs)  
S192: P05

<a id="f119-tree-oak-large"></a>
**119. `tree_oak_large`** (1 IDs)  
S693: P06

<a id="f120-screen-ground-tile-layer"></a>
**120. `screen ground (tile layer)`** (303 IDs)  
SCR 002 003 004 005 006 013 014 015 016 017 018 025 026 027 028 029 030 031 032 033 034 035 036 037 038 045 046 047 048 049 050 057 058 059 060 061 062 063 064 065 066 067 068 069 077 078 079 080 081 082 085 086 089 090 092 093 094 095 096 097 098 099 100 101 109 110 111 112 113 114 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 143 145 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 177 178 179 180 181 182 183 184 185 188 189 190 192 193 194 195 196 197 198 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 241 242 243 244 245 246 247 248 249 250 251 252 254 255 256 257 258 259 260 261 273 274 275 276 277 278 279 280 281 283 284 285 286 287 288 289 290 302 309 310 316 317 318 319 320 339 340 341 342 343 348 349 371 373 374 375 377 385 396 397 410 426 427 428 430 431 432 442 444 445 458 459 460 461 465 490 491 492 493 494 495 496 505 510 520 523 524 525 526 527 528 531 532 534 535 540 542 552 557 558 559 562 563 564 565 566 567 573 579 589 590 591 593 594 595 596 598 606 616 620 621 622 623 624 625 627 630 631 633 637 648 649 652 653 654 655 657 662 664 667 683 684 685 686 687 694 696 713 717 718 719 735 736 749 750 765 766 767
