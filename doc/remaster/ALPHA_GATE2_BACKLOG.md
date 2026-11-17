# Alpha gate 2 backlog: origin IDs still open

Generated 2026-11-16 by `DinkRemasterUE/Scripts/gate2_backlog.py` from `Saved/Import/coverage.csv` (6607 rows, importer run of 2026-11-16) and the manifests under `Content/Dink/Data/Art/`, classified by `Scripts/art_coverage.py`. Do not edit by hand; regenerate.

Alpha gate 2 (`doc/remaster/REMASTER_PLAN.md`): every origin ID is final, placeholder or cut with a reason. This list is what is still open: every origin ID whose art state in `Scripts/art_coverage.py` is `placeholder` (no art bound; nothing in the repo records a placeholder as owner-accepted), plus any unclassified ID. Final (bespoke or by family, `Content/Dink/Data/Art/families.json`) and cut (owner decision of 9 Nov 2026) are closed and not listed.

## Summary

| | open |
|---|---:|
| sprite families | 70 |
| origin IDs | 815 |
| map placements | 504 |
| screens (ground tile layer) | 303 |
| script warps with their own ID | 8 |
| unclassified IDs | 0 |

Claimed by the Claude photoreal pass (in progress elsewhere, not final): **26 families, 591 origin IDs, 285 placements**. Unclaimed: 44 families, 224 origin IDs, 219 placements.

Largest family by origin IDs: `screen ground (tile layer)` (303 IDs, 0 map placements, so it sorts at #70).

Largest families no stream has claimed: `blood_splat` 46, `tree_fruit` 34, `burn_hole_decal` 20, `arrow_prop` 14, `cave_hole_warp` 10, `fish` 8, `gold_coin` 8, `ground_crack` 8, `ground_hole_dark` 5, `shop_sign` 5.

Closed for comparison (art_coverage rows): final bespoke 1375, final by family 4240, cut 152, placeholder 840 of 6607 rows.

## How to regenerate

```bash
cd DinkRemasterUE && python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md
```

Run it in the editor's checkout: like `art_coverage.py` it needs the importer's `Saved/Import/coverage.csv` (`Scripts/import_greybox.sh --region all`), `tools/dinkex/out/sequences.json` and the gitignored engine template content under `Content/Characters` (the mother's locomotion). From another worktree add `--project <editor checkout>/DinkRemasterUE`. The photoreal column is a snapshot of `<--photoreal-root>/*/manifest.json` (default: the uncommitted photoreal pass work copy), read-only; regenerate after that pass lands or binds families.

## Backlog by sprite family

Sorted by open map placements. Family is the class id (`tools/data/sprite_classes.csv`, the key `families.json` binds); *what the original shows* gives its name, sprite group, size and the reference sheet in `doc/remaster/reference/`; *sequences* are the original sprite sequences of the open placements. The origin IDs of each family are listed under [Open origin IDs](#open-origin-ids).

| # | family | what the original sprite sheet shows | sequences (open placements) | origin IDs | placements | photoreal pass |
|---:|---|---|---|---:|---:|---|
| 1 | [`duck_head`](#f1-duck-head) | Duck head (death sprite) used as set dressing (duck, 15x42 px) · sheet_foes.png | 121 animals/duck/death/dkh1x- (90) | 90 | 90 | Creatures |
| 2 | [`town_roof_flat`](#f2-town-roof-flat) | Shingle roof section (town_house_kit, 100x200 px) · sheet_struct.png | 33 struct/outinn/oinn- (52) | 52 | 52 | TownExteriors |
| 3 | [`blood_splat`](#f3-blood-splat) | Blood splatter (blood, 39x56 px) · sheet_effects.png | 188 effects/spurt/sprtl- (24), 189 effects/spurt/sprtr- (18), 187 effects/spurt/spurt- (4) | 46 | 46 | - |
| 4 | [`tree_fruit`](#f4-tree-fruit) | Fruit hanging in a tree (food, 7x12 px) · sheet_items.png | 421 items/food/food- (34) | 34 | 34 | - |
| 5 | [`castle_wall_diag`](#f5-castle-wall-diag) | Castle curtain wall (diagonal run) (castle_kit, 350x463 px) · sheet_struct.png | 67 struct/castle/castl- (26) | 26 | 26 | Structures |
| 6 | [`burn_hole_decal`](#f6-burn-hole-decal) | Burnt hole / scorch mark (damage, 23x20 px) · sheet_struct.png | 158 struct/details/damage/hole- (20) | 20 | 20 | - |
| 7 | [`town_roof_dormer`](#f7-town-roof-dormer) | Roof section with dormer window (town_house_kit, 100x200 px) · sheet_struct.png | 33 struct/outinn/oinn- (16) | 16 | 16 | TownExteriors |
| 8 | [`town_roof_slope`](#f8-town-roof-slope) | Shingle roof slope (town_house_kit, 100x150 px) · sheet_struct.png | 33 struct/outinn/oinn- (15) | 15 | 15 | TownExteriors |
| 9 | [`arrow_prop`](#f9-arrow-prop) | Arrow (shop display / stuck in ground) (arrow, 47x30 px) · sheet_effects.png | 25 effects/arrow/arrow- (14) | 14 | 14 | - |
| 10 | [`town_roof_ridge_cap`](#f10-town-roof-ridge-cap) | Roof ridge / corner cap (town_house_kit, 60x45 px) · sheet_struct.png | 33 struct/outinn/oinn- (14) | 14 | 14 | TownExteriors |
| 11 | [`door_wood_single`](#f11-door-wood-single) | Wooden door (doors, 24x64 px) · sheet_struct.png | 61 struct/details/door/odor1- (11) | 11 | 11 | Structures |
| 12 | [`castle_tower_round`](#f12-castle-tower-round) | Round castle tower (castle_kit, 193x409 px) · sheet_struct.png | 67 struct/castle/castl- (10) | 10 | 10 | Structures |
| 13 | [`cave_hole_warp`](#f13-cave-hole-warp) | Hole into a cave (warp) (ground_holes, 55x31 px) · sheet_lands.png | 89 lands/details/crack- (10) | 10 | 10 | - |
| 14 | [`fish`](#f14-fish) | Fish (swimming) (fish, 72x52 px) · sheet_foes.png | 434 animals/fish/fish1/fish1- (8) | 8 | 8 | - |
| 15 | [`gold_coin`](#f15-gold-coin) | Single coin (gold, 4x3 px) · sheet_items.png | 178 bonuses/coins/coin- (8) | 8 | 8 | - |
| 16 | [`ground_crack`](#f16-ground-crack) | Crack in the ground (ground_holes, 88x33 px) · sheet_lands.png | 89 lands/details/crack- (8) | 8 | 8 | - |
| 17 | [`door_wood_wide`](#f17-door-wood-wide) | Wide wooden door (doors, 53x68 px) · sheet_struct.png | 62 struct/details/door/odor2- (7) | 7 | 7 | Structures |
| 18 | [`island_fence_lattice`](#f18-island-fence-lattice) | Lashed pole fence (island_village, 271x76 px) · sheet_struct.png | 424 struct/island/isle- (7) | 7 | 7 | Structures |
| 19 | [`castle_wall_corner`](#f19-castle-wall-corner) | Castle wall corner (castle_kit, 350x505 px) · sheet_struct.png | 67 struct/castle/castl- (6) | 6 | 6 | Structures |
| 20 | [`ground_hole_dark`](#f20-ground-hole-dark) | Dark hole in the ground (ground_holes, 55x73 px) · sheet_lands.png | 89 lands/details/crack- (5) | 10 | 5 | - |
| 21 | [`shop_sign`](#f21-shop-sign) | Hanging sign (red cross: healer) (signs, 63x76 px) · sheet_inside.png | 458 inside/details/sign- (5) | 5 | 5 | - |
| 22 | [`tree_pine_large`](#f22-tree-pine-large) | Pine tree (trees, 128x188 px) · sheet_lands.png | 32 lands/trees/tree- (4) | 7 | 4 | Vegetation |
| 23 | [`boulder_flat`](#f23-boulder-flat) | Flat boulder (boulders, 72x63 px) · sheet_lands.png | 95 lands/rocks/rock- (4) | 4 | 4 | - |
| 24 | [`bridge_stone`](#f24-bridge-stone) | Stone arch bridge (bridge_stone, 288x212 px) · sheet_struct.png | 186 struct/landmark/landm- (4) | 4 | 4 | Structures |
| 25 | [`bridge_wood_deck`](#f25-bridge-wood-deck) | Wooden bridge deck (bridge_wood, 65x88 px) · sheet_struct.png | 58 struct/bridge/brdge- (4) | 4 | 4 | Structures |
| 26 | [`fish_flopping`](#f26-fish-flopping) | Fish flopping on land (fish, 33x34 px) · sheet_foes.png | 439 animals/fish/flop/fishx- (3), 441 animals/fish/flop/flop2- (1) | 4 | 4 | - |
| 27 | [`food_fruit`](#f27-food-fruit) | Fruit (apple / pear / etc.) (food, 17x23 px) · sheet_items.png | 421 items/food/food- (4) | 4 | 4 | - |
| 28 | [`poster_hark`](#f28-poster-hark) | "Hark!" notice (signs, 43x61 px) · sheet_inside.png | 462 inner/poster (4) | 4 | 4 | - |
| 29 | [`bomb_item`](#f29-bomb-item) | Bomb (items, 26x33 px) · sheet_items.png | 420 items/bomb/bomb- (3) | 3 | 3 | - |
| 30 | [`church`](#f30-church) | Stone church (church, 417x433 px) · sheet_struct.png | 60 struct/church/chrch- (3) | 3 | 3 | - |
| 31 | [`church_stained_glass`](#f31-church-stained-glass) | Stained-glass window (church, 56x94 px) · sheet_struct.png | 60 struct/church/chrch- (3) | 3 | 3 | - |
| 32 | [`pillbug_corpse`](#f32-pillbug-corpse) | Pillbug death splat (pillbug, 46x35 px) · sheet_foes.png | 141 foes/pill/f1-x1- (2), 143 foes/pill/f1-x3- (1) | 3 | 3 | Creatures |
| 33 | [`boulder_large`](#f33-boulder-large) | Large dark boulder (boulders, 103x95 px) · sheet_lands.png | 95 lands/rocks/rock- (2) | 2 | 2 | - |
| 34 | [`boulder_red`](#f34-boulder-red) | Reddish boulder (boulders, 100x79 px) · sheet_lands.png | 95 lands/rocks/rock- (2) | 2 | 2 | - |
| 35 | [`burnt_floor_hole`](#f35-burnt-floor-hole) | Burnt hole in floor/roof (large) (damage, 90x69 px) · sheet_struct.png | 158 struct/details/damage/hole- (2) | 2 | 2 | - |
| 36 | [`castle_wall_end`](#f36-castle-wall-end) | Castle wall end (edge-on) (castle_kit, 100x340 px) · sheet_struct.png | 67 struct/castle/castl- (2) | 2 | 2 | Structures |
| 37 | [`church_window_small`](#f37-church-window-small) | Church small window (church, 19x27 px) · sheet_struct.png | 60 struct/church/chrch- (2) | 2 | 2 | - |
| 38 | [`dragon_corpse`](#f38-dragon-corpse) | Dead dragon (dragon, 105x122 px) · sheet_foes.png | 212 foes/dragon/f2-x3- (2) | 2 | 2 | - |
| 39 | [`duck_corpse`](#f39-duck-corpse) | Dead duck body (duck, 20x30 px) · sheet_foes.png | 127 animals/duck/death/dkh7x- (1), 121 animals/duck/death/dkh1x- (1) | 2 | 2 | Creatures |
| 40 | [`fence_rail_ns`](#f40-fence-rail-ns) | Rail fence (north-south) (fence_rail, 26x136 px) · sheet_lands.png | 93 lands/fence/fence- (2) | 2 | 2 | Structures |
| 41 | [`fireball_fx`](#f41-fireball-fx) | Fireball (vertical) (, 32x76 px) · sheet_effects.png | 512 effects/comets/sm-comt2/fbal2- (2) | 2 | 2 | - |
| 42 | [`food_pie`](#f42-food-pie) | Pie (food, 24x19 px) · sheet_items.png | 421 items/food/food- (2) | 2 | 2 | Props |
| 43 | [`log_cabin`](#f43-log-cabin) | Log cabin (log_cabin, 322x232 px) · sheet_struct.png | 59 struct/cabin/cabin- (2) | 2 | 2 | - |
| 44 | [`npc_knight_red`](#f44-npc-knight-red) | Knight (red) (npc_knight, 91x125 px) · sheet_people.png | 273 people/knight/red/c5-w3- (1), 279 people/knight/red/c5-w9- (1) | 2 | 2 | - |
| 45 | [`sparkle_fx`](#f45-sparkle-fx) | Sparkle (, 20x20 px) · sheet_effects.png | 165 effects/shiny/shiny- (1), 166 effects/sparks/spark- (1) | 2 | 2 | - |
| 46 | [`tree_willow`](#f46-tree-willow) | Weeping (willow-like) tree (trees, 169x252 px) · sheet_lands.png | 32 lands/trees/tree- (2) | 2 | 2 | Vegetation |
| 47 | [`tree_willow_large`](#f47-tree-willow-large) | Large weeping tree (trees, 249x300 px) · sheet_lands.png | 32 lands/trees/tree- (2) | 2 | 2 | Vegetation |
| 48 | [`boulder_grey_tall`](#f48-boulder-grey-tall) | Tall grey boulder (boulders, 54x77 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 49 | [`boulder_white_pair`](#f49-boulder-white-pair) | Pair of white boulders (boulders, 80x58 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 50 | [`burn_damage_decal`](#f50-burn-damage-decal) | Burn damage / scorch with fire (damage, 90x69 px) · sheet_struct.png | 154 struct/details/damage/damag- (1) | 1 | 1 | - |
| 51 | [`castle_drawbridge`](#f51-castle-drawbridge) | Drawbridge with chains (castle_kit, 149x192 px) · sheet_struct.png | 68 struct/castle/cdoor- (1) | 1 | 1 | - |
| 52 | [`castle_gatehouse`](#f52-castle-gatehouse) | Castle gatehouse block (castle_kit, 335x389 px) · sheet_struct.png | 67 struct/castle/castl- (1) | 1 | 1 | Structures |
| 53 | [`church_door`](#f53-church-door) | Church door (church, 35x82 px) · sheet_struct.png | 60 struct/church/chrch- (1) | 1 | 1 | - |
| 54 | [`food_bread`](#f54-food-bread) | Bread loaf (food, 30x25 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 55 | [`food_cheese`](#f55-food-cheese) | Cheese (food, 21x19 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 56 | [`food_drumstick`](#f56-food-drumstick) | Meat drumstick (food, 28x31 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 57 | [`food_grapes`](#f57-food-grapes) | Grapes (food, 29x30 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 58 | [`food_ham`](#f58-food-ham) | Ham / steak (food, 28x28 px) · sheet_items.png | 421 items/food/food- (1) | 1 | 1 | - |
| 59 | [`island_hut_round`](#f59-island-hut-round) | Koka Isle round hut (island_village, 208x178 px) · sheet_struct.png | 424 struct/island/isle- (1) | 1 | 1 | Structures |
| 60 | [`log_cabin_door`](#f60-log-cabin-door) | Log cabin door (log_cabin, 34x69 px) · sheet_struct.png | 59 struct/cabin/cabin- (1) | 1 | 1 | - |
| 61 | [`log_cabin_window`](#f61-log-cabin-window) | Log cabin window (log_cabin, 24x28 px) · sheet_struct.png | 59 struct/cabin/cabin- (1) | 1 | 1 | - |
| 62 | [`ore_rock_blue`](#f62-ore-rock-blue) | Blue crystal rock (boulders, 44x29 px) · sheet_lands.png | 95 lands/rocks/rock- (1) | 1 | 1 | - |
| 63 | [`poster_wanted`](#f63-poster-wanted) | "Wanted" poster (signs, 43x61 px) · sheet_inside.png | 462 inner/poster (1) | 1 | 1 | - |
| 64 | [`snow_house_door`](#f64-snow-house-door) | House door (snow_house, 43x78 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 65 | [`snow_house_lower`](#f65-snow-house-lower) | House lower walls (snow_house, 381x188 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 66 | [`snow_house_roof`](#f66-snow-house-roof) | House pyramid roof (snow_house, 404x201 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 67 | [`snow_house_timber`](#f67-snow-house-timber) | House timbered upper walls (snow_house, 400x179 px) · sheet_struct.png | 96 struct/building/build- (1) | 1 | 1 | - |
| 68 | [`thorn_branch`](#f68-thorn-branch) | Thorn branch (graveyard, 28x25 px) · sheet_lands.png | 90 lands/details/grave- (1) | 1 | 1 | Vegetation |
| 69 | [`tree_oak_large`](#f69-tree-oak-large) | Broadleaf (oak) tree (trees, 204x270 px) · sheet_lands.png | 32 lands/trees/tree- (1) | 1 | 1 | Vegetation |
| 70 | [`screen ground (tile layer)`](#f70-screen-ground-tile-layer) | tile-layer ground of each screen (grass, sand, water, walls painted into tilesets) · sheet_tiles.png | - | 303 | 0 | Terrain |

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

<a id="f4-tree-fruit"></a>
**4. `tree_fruit`** (34 IDs)  
S442: P02 P04 P05 P06 P07 P08 P09 P10 P11 P12 P15 P16 P17 P18 P19 P20 P21 P22 P23 · S474: P02 P03 P04 P05 P06 P07 P08 P09 P10 P11 P12 P13 P15 P16 P17

<a id="f5-castle-wall-diag"></a>
**5. `castle_wall_diag`** (26 IDs)  
S014: P01 · S015: P01 P02 P03 · S016: P01 P02 P06 · S017: P01 · S018: P02 · S047: P01 P03 P04 · S048: P01 P02 P03 P04 P06 · S049: P01 P02 · S050: P01 · S070: P01 · S078: P01 · S079: P03 · S080: P01 P02 · S081: P01

<a id="f6-burn-hole-decal"></a>
**6. `burn_hole_decal`** (20 IDs)  
S005: P25 P26 P27 · S066: P23 P24 · S439: P23 P24 P25 P26 P27 P28 P30 P36 P37 P46 · S533: P21 P22 P23 · S536: P16 P26

<a id="f7-town-roof-dormer"></a>
**7. `town_roof_dormer`** (16 IDs)  
S187: P07 P09 · S218: P21 · S219: P01 P03 · S465: P03 · S466: P04 · S472: P10 · S473: P05 P08 · S474: P21 · S498: P08 · S505: P07 · S506: P08 P25 · S538: P06

<a id="f8-town-roof-slope"></a>
**8. `town_roof_slope`** (15 IDs)  
S186: P23 · S187: P10 · S218: P20 · S385: P16 · S388: P14 · S465: P07 · S467: P03 · S472: P06 · S474: P22 · S507: P07 · S553: P02 P05 · S554: P03 P06 · S555: P02

<a id="f9-arrow-prop"></a>
**9. `arrow_prop`** (14 IDs)  
S097: P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 · S663: P20 P21 P22 P23

<a id="f10-town-roof-ridge-cap"></a>
**10. `town_roof_ridge_cap`** (14 IDs)  
S186: P51 · S187: P12 · S385: P18 · S388: P18 · S465: P04 · S467: P04 · S472: P02 · S474: P23 · S507: P08 · S553: P03 P07 · S554: P02 P05 · S555: P05

<a id="f11-door-wood-single"></a>
**11. `door_wood_single`** (11 IDs)  
S188: P10 · S219: P10 · S251: P09 · S418: P16 · S419: P02 · S498: P11 · S499: P07 · S506: P20 · S539: P12 · S585: P14 · S587: P12

<a id="f12-castle-tower-round"></a>
**12. `castle_tower_round`** (10 IDs)  
S018: P01 · S047: P02 · S049: P03 · S050: P02 · S070: P02 · S078: P02 · S079: P01 P04 · S080: P03 · S112: P01

<a id="f13-cave-hole-warp"></a>
**13. `cave_hole_warp`** (10 IDs)  
S085: P01 · S112: P02 · S144: P04 · S182: P01 · S209: P01 · S248: P01 · S254: P04 · S483: P11 · S625: P05 · S671: P01

<a id="f14-fish"></a>
**14. `fish`** (8 IDs)  
S634: P01 P02 P03 · S665: P03 · S697: P02 P03 P04 · S727: P17

<a id="f15-gold-coin"></a>
**15. `gold_coin`** (8 IDs)  
S505: P15 · S537: P10 P11 P12 P13 · S663: P03 P17 P18

<a id="f16-ground-crack"></a>
**16. `ground_crack`** (8 IDs)  
S005: P19 · S066: P29 · S154: P03 P04 P06 P09 P10 · S193: P23

<a id="f17-door-wood-wide"></a>
**17. `door_wood_wide`** (7 IDs)  
S497: P13 P15 · S498: P10 · S504: P15 · S505: P01 · S538: P21 · S585: P13

<a id="f18-island-fence-lattice"></a>
**18. `island_fence_lattice`** (7 IDs)  
S489: P03 · S731: P03 P10 P11 P12 P13 P14

<a id="f19-castle-wall-corner"></a>
**19. `castle_wall_corner`** (6 IDs)  
S016: P04 P05 · S017: P02 P03 · S018: P03 · S070: P04

<a id="f20-ground-hole-dark"></a>
**20. `ground_hole_dark`** (10 IDs)  
S132: P01 · S180: P01 · S209: P04 · S243: P13 · S277: P02 · SW_s1-hole3_L22@S209_P04 · SW_s1-hole_L21@S132_P01 · SW_s1-hole_L21@S277_P02 · SW_s6-hole2_L22@S180_P01 · SW_s6-hole_L22@S243_P13

<a id="f21-shop-sign"></a>
**21. `shop_sign`** (5 IDs)  
S498: P13 P14 · S504: P17 · S538: P22 · S539: P05

<a id="f22-tree-pine-large"></a>
**22. `tree_pine_large`** (7 IDs)  
S307: P13 · S534: P10 · S659: P06 · S710: P14 · SW_s2-sec1_L37@S307_P13 · SW_s2-sec3_L37@S659_P06 · SW_s3-sec1_L39@S710_P14

<a id="f23-boulder-flat"></a>
**23. `boulder_flat`** (4 IDs)  
S535: P12 · S590: P03 P10 P11

<a id="f24-bridge-stone"></a>
**24. `bridge_stone`** (4 IDs)  
S102: P01 P02 P03 P04

<a id="f25-bridge-wood-deck"></a>
**25. `bridge_wood_deck`** (4 IDs)  
S533: P01 P02 P03 P25

<a id="f26-fish-flopping"></a>
**26. `fish_flopping`** (4 IDs)  
S734: P09 · S760: P01 P02 P03

<a id="f27-food-fruit"></a>
**27. `food_fruit`** (4 IDs)  
S070: P31 P35 P36 P37

<a id="f28-poster-hark"></a>
**28. `poster_hark`** (4 IDs)  
S033: P30 · S195: P30 · S225: P30 · S226: P30

<a id="f29-bomb-item"></a>
**29. `bomb_item`** (3 IDs)  
S228: P40 P41 P42

<a id="f30-church"></a>
**30. `church`** (3 IDs)  
S187: P02 · S188: P03 P05

<a id="f31-church-stained-glass"></a>
**31. `church_stained_glass`** (3 IDs)  
S188: P07 P08 P09

<a id="f32-pillbug-corpse"></a>
**32. `pillbug_corpse`** (3 IDs)  
S098: P04 · S100: P25 P26

<a id="f33-boulder-large"></a>
**33. `boulder_large`** (2 IDs)  
S277: P03 · S590: P01

<a id="f34-boulder-red"></a>
**34. `boulder_red`** (2 IDs)  
S536: P15 · S590: P04

<a id="f35-burnt-floor-hole"></a>
**35. `burnt_floor_hole`** (2 IDs)  
S439: P34 P38

<a id="f36-castle-wall-end"></a>
**36. `castle_wall_end`** (2 IDs)  
S016: P03 · S048: P05

<a id="f37-church-window-small"></a>
**37. `church_window_small`** (2 IDs)  
S187: P01 P03

<a id="f38-dragon-corpse"></a>
**38. `dragon_corpse`** (2 IDs)  
S100: P34 · S238: P12

<a id="f39-duck-corpse"></a>
**39. `duck_corpse`** (2 IDs)  
S100: P27 · S521: P05

<a id="f40-fence-rail-ns"></a>
**40. `fence_rail_ns`** (2 IDs)  
S375: P02 P03

<a id="f41-fireball-fx"></a>
**41. `fireball_fx`** (2 IDs)  
S366: P09 P14

<a id="f42-food-pie"></a>
**42. `food_pie`** (2 IDs)  
S070: P24 P25

<a id="f43-log-cabin"></a>
**43. `log_cabin`** (2 IDs)  
S251: P01 · S270: P07

<a id="f44-npc-knight-red"></a>
**44. `npc_knight_red`** (2 IDs)  
S149: P05 P09

<a id="f45-sparkle-fx"></a>
**45. `sparkle_fx`** (2 IDs)  
S001: P37 · S045: P01

<a id="f46-tree-willow"></a>
**46. `tree_willow`** (2 IDs)  
S414: P02 · S446: P02

<a id="f47-tree-willow-large"></a>
**47. `tree_willow_large`** (2 IDs)  
S149: P02 · S474: P01

<a id="f48-boulder-grey-tall"></a>
**48. `boulder_grey_tall`** (1 IDs)  
S601: P08

<a id="f49-boulder-white-pair"></a>
**49. `boulder_white_pair`** (1 IDs)  
S590: P02

<a id="f50-burn-damage-decal"></a>
**50. `burn_damage_decal`** (1 IDs)  
S439: P29

<a id="f51-castle-drawbridge"></a>
**51. `castle_drawbridge`** (1 IDs)  
S080: P05

<a id="f52-castle-gatehouse"></a>
**52. `castle_gatehouse`** (1 IDs)  
S080: P04

<a id="f53-church-door"></a>
**53. `church_door`** (1 IDs)  
S188: P06

<a id="f54-food-bread"></a>
**54. `food_bread`** (1 IDs)  
S070: P33

<a id="f55-food-cheese"></a>
**55. `food_cheese`** (1 IDs)  
S070: P26

<a id="f56-food-drumstick"></a>
**56. `food_drumstick`** (1 IDs)  
S070: P23

<a id="f57-food-grapes"></a>
**57. `food_grapes`** (1 IDs)  
S070: P30

<a id="f58-food-ham"></a>
**58. `food_ham`** (1 IDs)  
S070: P32

<a id="f59-island-hut-round"></a>
**59. `island_hut_round`** (1 IDs)  
S489: P02

<a id="f60-log-cabin-door"></a>
**60. `log_cabin_door`** (1 IDs)  
S251: P07

<a id="f61-log-cabin-window"></a>
**61. `log_cabin_window`** (1 IDs)  
S251: P08

<a id="f62-ore-rock-blue"></a>
**62. `ore_rock_blue`** (1 IDs)  
S590: P09

<a id="f63-poster-wanted"></a>
**63. `poster_wanted`** (1 IDs)  
S035: P27

<a id="f64-snow-house-door"></a>
**64. `snow_house_door`** (1 IDs)  
S149: P07

<a id="f65-snow-house-lower"></a>
**65. `snow_house_lower`** (1 IDs)  
S149: P03

<a id="f66-snow-house-roof"></a>
**66. `snow_house_roof`** (1 IDs)  
S149: P08

<a id="f67-snow-house-timber"></a>
**67. `snow_house_timber`** (1 IDs)  
S149: P06

<a id="f68-thorn-branch"></a>
**68. `thorn_branch`** (1 IDs)  
S192: P05

<a id="f69-tree-oak-large"></a>
**69. `tree_oak_large`** (1 IDs)  
S693: P06

<a id="f70-screen-ground-tile-layer"></a>
**70. `screen ground (tile layer)`** (303 IDs)  
SCR 002 003 004 005 006 013 014 015 016 017 018 025 026 027 028 029 030 031 032 033 034 035 036 037 038 045 046 047 048 049 050 057 058 059 060 061 062 063 064 065 066 067 068 069 077 078 079 080 081 082 085 086 089 090 092 093 094 095 096 097 098 099 100 101 109 110 111 112 113 114 120 121 122 123 124 125 126 127 128 129 130 131 132 133 134 143 145 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 177 178 179 180 181 182 183 184 185 188 189 190 192 193 194 195 196 197 198 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 241 242 243 244 245 246 247 248 249 250 251 252 254 255 256 257 258 259 260 261 273 274 275 276 277 278 279 280 281 283 284 285 286 287 288 289 290 302 309 310 316 317 318 319 320 339 340 341 342 343 348 349 371 373 374 375 377 385 396 397 410 426 427 428 430 431 432 442 444 445 458 459 460 461 465 490 491 492 493 494 495 496 505 510 520 523 524 525 526 527 528 531 532 534 535 540 542 552 557 558 559 562 563 564 565 566 567 573 579 589 590 591 593 594 595 596 598 606 616 620 621 622 623 624 625 627 630 631 633 637 648 649 652 653 654 655 657 662 664 667 683 684 685 686 687 694 696 713 717 718 719 735 736 749 750 765 766 767
