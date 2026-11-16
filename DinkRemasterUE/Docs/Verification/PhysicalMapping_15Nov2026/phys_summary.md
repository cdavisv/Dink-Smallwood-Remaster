# Physical mapping audit: 644 screens, 5592 placement/sprite rows, 115 warps, 3525 bare tile blobs

## 1 Invisible walls (contact edges: stamp pixels next to walkable 1997 ground)
Sprite hardboxes: checked 2457, OK 686, mismatched 1771
  - ok: on water/cliff/wall terrain tiles: 261
  - hardness-only placement (invisible in 1997 too): 15
  - its mesh does not reach the hardbox edge: 1545
  - nothing of its own drawn (screen-dressed or missing): 96
  - only its card is drawn: 115
Tile hardness, per 50 px tile with contact edges: checked 14381, OK 11207, mismatched 3174
  - ok: drawn by the terrain as cave_wall: 26
  - ok: drawn by the terrain as cliff_face: 3175
  - ok: drawn by the terrain as forest_canopy: 330
  - ok: drawn by the terrain as lava: 20
  - ok: drawn by the terrain as rock_mass: 275
  - ok: drawn by the terrain as structure_facade: 5
  - ok: drawn by the terrain as void: 44
  - ok: drawn by the terrain as water: 74
  - ok: next to cave_wall (shore, cliff or wall edge): 397
  - ok: next to chasm (shore, cliff or wall edge): 168
  - ok: next to chasm/cliff_face (shore, cliff or wall edge): 36
  - ok: next to cliff_face (shore, cliff or wall edge): 1082
  - ok: next to cliff_face/forest_canopy (shore, cliff or wall edge): 24
  - ok: next to cliff_face/rock_mass (shore, cliff or wall edge): 4
  - ok: next to cliff_face/water (shore, cliff or wall edge): 18
  - ok: next to forest_canopy (shore, cliff or wall edge): 378
  - ok: next to forest_canopy/rock_mass (shore, cliff or wall edge): 15
  - ok: next to forest_canopy/water (shore, cliff or wall edge): 13
  - ok: next to lava (shore, cliff or wall edge): 32
  - ok: next to rock_mass (shore, cliff or wall edge): 745
  - ok: next to rock_mass/water (shore, cliff or wall edge): 2
  - ok: next to structure_facade (shore, cliff or wall edge): 52
  - ok: next to structure_facade/water (shore, cliff or wall edge): 19
  - ok: next to void (shore, cliff or wall edge): 19
  - ok: next to water (shore, cliff or wall edge): 2914
  - low (2) tile hardness on open grass: 539
  - low (2) tile hardness on open grass_rocky: 813
  - low (2) tile hardness on open snow: 14
  - low (2) tile hardness on open wasteland: 217
  - solid tile hardness on open cave_floor: 8
  - solid tile hardness on open grass: 649
  - solid tile hardness on open grass_rocky: 14
  - solid tile hardness on open gravel: 2
  - solid tile hardness on open ice: 87
  - solid tile hardness on open path: 160
  - solid tile hardness on open sand: 36
  - solid tile hardness on open snow: 149
  - solid tile hardness on open stone_floor: 486
(bare tile blobs from phys_tiles.csv, >= 30 px with nothing drawn within 40 cm: 3525)

## 2 Sprite hardboxes vs meshes (placements that block)
checked 2336 (drawn by a mesh 1973, card only 151, body 0, nothing 212); of the meshes OK 183, mismatched 1790
centre offset (cm): median 56, p90 151, p99 270, max 443
footprint/hardbox linear scale: p10 0.19, median 0.35, p90 0.75
Meshes with the most mismatched placements (mesh: mismatched/placements, median offset cm, median cover):
  - SM_Wall_Plaster_Straight_A: 329/329, offset 50, cover 0.39
  - SM_Veg_Pine_Medium_01: 105/105, offset 144, cover 0.13
  - SM_Wall_Plaster_Straight_B: 85/85, offset 44, cover 0.39
  - SM_Veg_Willow_Large_01: 74/85, offset 101, cover 0.58
  - SM_Veg_ThornBush_02: 69/80, offset 61, cover 0.67
  - SM_Veg_Pine_Large_01: 63/63, offset 141, cover 0.16
  - SM_Barrel_Oak_01: 58/80, offset 36, cover 0.36
  - SM_Veg_Bush_Small_01: 55/55, offset 49, cover 0.28
  - SM_Veg_Bush_Round_Medium_01: 55/55, offset 27, cover 0.28
  - SM_Veg_Willow_01: 53/82, offset 73, cover 0.69
  - SM_Veg_Bush_Round_Large_01: 44/44, offset 68, cover 0.27
  - SM_Wall_Plaster_DoorJamb_R: 41/41, offset 48, cover 0.31
  - SM_Wall_Plaster_DoorJamb_L: 38/38, offset 51, cover 0.31
  - SM_Veg_ThornBush_01: 38/61, offset 53, cover 0.66
  - SM_Veg_Oak_Large_01: 38/41, offset 151, cover 0.35

## 3 Creatures and NPCs: 1997 hit box vs the drawn body (Dink with a sword: sp_range 40)
live creature/NPC sprites checked 518: OK 0, mismatched 160, 3D hit (authored) 9, card only 306, no body/box 43
By body (sprites, median far-hit cm, median missed-contact cm, median centre offset cm):
  - SK_Pillbug_Photoreal: 149, far 326, miss 0, offset 78
  - SM_Save_Machine_PR: 10, far 682, miss 0, offset 86
  - SM_Snake_Carving_PR: 1, far 311, miss 0, offset 6

## 4 Pickups (touch box) and warps (trigger vs door)
pickups checked 106: OK 0, mismatched 65, 3D touch (authored) 1, card only 26, no mesh/box 14
warps (enabled triggers) checked 110: OK 63, mismatched 47 (no own mesh 69)

## 6 Terrain tiles: drawn class vs where the capsule can stand
tiles checked 61824
  - lava drawn, walkable no more than the 1997 hardness 0 allows (as 1997): 128
  - open cave_floor drawn, blocked or out of reach in 1997: 6
  - open grass drawn, blocked or out of reach in 1997: 1233
  - open grass drawn, walkable in 1997 (largest region), blocked in the remaster with nothing drawn: 831
  - open grass_rocky drawn, blocked or out of reach in 1997: 78
  - open grass_rocky drawn, walkable in 1997 (largest region), blocked in the remaster with nothing drawn: 33
  - open gravel drawn, blocked or out of reach in 1997: 2
  - open ice drawn, blocked or out of reach in 1997: 43
  - open path drawn, blocked or out of reach in 1997: 48
  - open sand drawn, blocked or out of reach in 1997: 183
  - open sand drawn, walkable in 1997 (largest region), blocked in the remaster with nothing drawn: 484
  - open snow drawn, blocked or out of reach in 1997: 72
  - open stone_floor drawn, blocked or out of reach in 1997: 170
  - open wasteland drawn, blocked or out of reach in 1997: 34
  - open wasteland drawn, walkable in 1997 (largest region), blocked in the remaster with nothing drawn: 4
  - open wood_floor drawn, blocked or out of reach in 1997: 161
  - water drawn, walkable no more than the 1997 hardness 0 allows (as 1997): 112
  - water drawn, walkable where 1997 blocks: 2
screen edges checked 1188 (921 crossable in 1997): 1997 crossing blocked 349 (cells: 20 px of 1997 hardness 0 and open terrain on both sides; capsule free within 12 px of the edge on both sides)

## 7 Live sprites standing inside another drawn body
checked 993: OK 962, inside 31

## Not judged: 11 screens with nothing drawn, the whole map hard or the player not on the screen: SCR_145, SCR_298, SCR_402, SCR_404, SCR_416, SCR_418, SCR_468, SCR_721, SCR_722, SCR_723, SCR_724

## Worst per category (top 8 each)
### 1 invisible wall (hardbox) (1770)
- SCR_748 S748_P01: Dink stops up to 703 cm (p90) from anything drawn on 96% of its 519 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.1, mesh SM_DinkCard, kinds card
- SCR_588 S588_P05: Dink stops up to 717 cm (p90) from anything drawn on 100% of its 376 px contact edge; its mesh does not reach the hardbox edge; class npc, type 1, seq 449.4, mesh SM_Save_Machine_PR, kinds family
- SCR_569 S569_P02: Dink stops up to 680 cm (p90) from anything drawn on 100% of its 376 px contact edge; its mesh does not reach the hardbox edge; class npc, type 1, seq 449.5, mesh SM_Save_Machine_PR, kinds family
- SCR_762 S762_P01: Dink stops up to 615 cm (p90) from anything drawn on 96% of its 502 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.3, mesh SM_DinkCard, kinds card
- SCR_763 S763_P20: Dink stops up to 622 cm (p90) from anything drawn on 92% of its 530 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.7, mesh SM_DinkCard, kinds card
- SCR_253 S253_P06: Dink stops up to 626 cm (p90) from anything drawn on 100% of its 430 px contact edge; its mesh does not reach the hardbox edge; class scripted_prop, type 1, seq 159.7, mesh SM_Shrine_Glass_PR, kinds family
- SCR_764 S764_P02: Dink stops up to 584 cm (p90) from anything drawn on 94% of its 483 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.3, mesh SM_DinkCard, kinds card
- SCR_586 S586_P03: Dink stops up to 687 cm (p90) from anything drawn on 90% of its 340 px contact edge; its mesh does not reach the hardbox edge; class scripted_prop, type 1, seq 66.24, mesh SM_Fountain_Stone_PR, kinds family
### 1 invisible wall (tile low) (1573)
- SCR_470 tile 4,1: grass_rocky tile: Dink stops up to 1813 cm (p90) from anything drawn on 100% of 242 px of contact edge
- SCR_470 tile 5,0: grass_rocky tile: Dink stops up to 1493 cm (p90) from anything drawn on 100% of 344 px of contact edge
- SCR_445 tile 1,7: grass_rocky tile: Dink stops up to 1370 cm (p90) from anything drawn on 100% of 358 px of contact edge
- SCR_474 tile 0,0: grass_rocky tile: Dink stops up to 1660 cm (p90) from anything drawn on 100% of 172 px of contact edge
- SCR_474 tile 1,1: grass_rocky tile: Dink stops up to 1159 cm (p90) from anything drawn on 100% of 358 px of contact edge
- SCR_552 tile 4,0: grass_rocky tile: Dink stops up to 1179 cm (p90) from anything drawn on 100% of 344 px of contact edge
- SCR_221 tile 9,1: wasteland tile: Dink stops up to 1566 cm (p90) from anything drawn on 100% of 179 px of contact edge
- SCR_343 tile 0,1: grass_rocky tile: Dink stops up to 1454 cm (p90) from anything drawn on 100% of 197 px of contact edge
### 1 invisible wall (tile solid) (1560)
- SCR_151 tile 4,0: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- SCR_151 tile 7,0: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- SCR_151 tile 3,2: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- SCR_151 tile 8,2: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- SCR_151 tile 4,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- SCR_151 tile 5,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- SCR_151 tile 6,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- SCR_151 tile 7,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
### 2 hardbox vs mesh (1790)
- SCR_188 S188_P04: SM_Veg_PineForestEdge_H_01: hardbox covered 14%; box 206x33 px at 10.0 cm/px, kinds family_instance
- SCR_251 S251_P05: SM_Veg_PineForestEdge_H_01: hardbox covered 14%; box 206x33 px at 9.9 cm/px, kinds family
- SCR_283 S283_P04: SM_Veg_PineForestEdge_H_01: hardbox covered 17%; box 206x33 px at 9.4 cm/px, kinds family
- SCR_282 S282_P01: SM_Veg_PineForestEdge_H_01: hardbox covered 18%; box 206x33 px at 9.4 cm/px, kinds family
- SCR_283 S283_P02: SM_Veg_PineForestEdge_H_01: hardbox covered 17%; box 206x33 px at 9.4 cm/px, kinds family
- SCR_282 S282_P02: SM_Veg_PineForestEdge_H_01: hardbox covered 18%; box 206x33 px at 9.4 cm/px, kinds family
- SCR_441 S441_P03: SM_Fence_SplitRail_4m_01: hardbox covered 11%; box 176x24 px at 9.9 cm/px, kinds family
- SCR_441 S441_P02: SM_Fence_SplitRail_4m_01: hardbox covered 11%; box 176x24 px at 9.9 cm/px, kinds family
### 3 creature hit box vs body (160)
- SCR_252 S252_P01: SM_Save_Machine_PR (brain 6, script savebot): hit registers 746 cm short of the body, visible sword contact missed by up to 0 cm, body centre 89 cm from the hardbox centre; W:726/0 E:746/0 N:648/0 S:520/0
- SCR_408 S408_P25: SM_Save_Machine_PR (brain 6, script savebot): hit registers 745 cm short of the body, visible sword contact missed by up to 0 cm, body centre 89 cm from the hardbox centre; W:726/0 E:745/0 N:647/0 S:519/0
- SCR_588 S588_P05: SM_Save_Machine_PR (brain 6, script savebot): hit registers 744 cm short of the body, visible sword contact missed by up to 0 cm, body centre 89 cm from the hardbox centre; W:724/0 E:744/0 N:646/0 S:518/0
- SCR_569 S569_P02: SM_Save_Machine_PR (brain 6, script savebot): hit registers 723 cm short of the body, visible sword contact missed by up to 0 cm, body centre 88 cm from the hardbox centre; W:704/0 E:723/0 N:636/0 S:510/0
- SCR_344 S344_P01: SM_Save_Machine_PR (brain 6, script savebot): hit registers 682 cm short of the body, visible sword contact missed by up to 0 cm, body centre 86 cm from the hardbox centre; W:663/0 E:682/0 N:540/0 S:417/0
- SCR_488 S488_P11: SK_Pillbug_Photoreal (brain 9, script en-pill2): hit registers 602 cm short of the body, visible sword contact missed by up to 0 cm, body centre 203 cm from the hardbox centre; W:305/0 E:434/0 N:602/0 S:266/0
- SCR_213 S213_P01: SM_Save_Machine_PR (brain 6, script savebot): hit registers 574 cm short of the body, visible sword contact missed by up to 0 cm, body centre 74 cm from the hardbox centre; W:557/0 E:574/0 N:467/0 S:360/0
- SCR_552 S552_P02: SK_Pillbug_Photoreal (brain 9, script en-pill): hit registers 540 cm short of the body, visible sword contact missed by up to 0 cm, body centre 99 cm from the hardbox centre; W:340/0 E:440/0 N:540/0 S:420/0
### 4 pickup touch box (65)
- SCR_524 S524_P04: SM_Heart_Gold_PR (gheart): picked up 199 cm from the mesh, stands 0 cm over it without the touch
- SCR_352 S352_P38: SM_Gold_Pile_PR (lgold): picked up 185 cm from the mesh, stands 0 cm over it without the touch
- SCR_352 S352_P36: SM_Gold_Pile_PR (lgold): picked up 185 cm from the mesh, stands 0 cm over it without the touch
- SCR_352 S352_P35: SM_Gold_Pile_PR (lgold): picked up 185 cm from the mesh, stands 0 cm over it without the touch
- SCR_352 S352_P34: SM_Gold_Pile_PR (lgold): picked up 185 cm from the mesh, stands 0 cm over it without the touch
- SCR_352 S352_P29: SM_Gold_Pile_PR (lgold): picked up 185 cm from the mesh, stands 0 cm over it without the touch
- SCR_352 S352_P28: SM_Gold_Pile_PR (lgold): picked up 185 cm from the mesh, stands 0 cm over it without the touch
- SCR_352 S352_P27: SM_Gold_Pile_PR (lgold): picked up 185 cm from the mesh, stands 0 cm over it without the touch
### 4 screen-edge exit (346)
- SCR_187 right edge to SCR_188: 42 of 50 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
- SCR_382 right edge to SCR_383: 39 of 59 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
- SCR_602 right edge to SCR_603: 37 of 75 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
- SCR_426 right edge to SCR_427: 30 of 63 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
- SCR_597 down edge to SCR_629: 29 of 112 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
- SCR_629 down edge to SCR_661: 28 of 84 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
- SCR_635 right edge to SCR_636: 27 of 82 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
- SCR_665 down edge to SCR_697: 27 of 82 edge cells (3 px) where 1997 crosses are blocked for the capsule on one side
### 4 warp trigger (45)
- SCR_227 S227_P01: exit trigger with nothing drawn on 100% of it (nearest drawn 1461 cm)
- SCR_069 S069_P01: exit trigger with nothing drawn on 100% of it (nearest drawn 1444 cm)
- SCR_101 S101_P01: exit trigger with nothing drawn on 100% of it (nearest drawn 1129 cm)
- SCR_131 S131_P01: exit trigger with nothing drawn on 100% of it (nearest drawn 1074 cm)
- SCR_132 S132_P19: exit trigger with nothing drawn on 100% of it (nearest drawn 739 cm)
- SCR_165 S165_P19: exit trigger with nothing drawn on 100% of it (nearest drawn 735 cm)
- SCR_166 S166_P19: exit trigger with nothing drawn on 100% of it (nearest drawn 733 cm)
- SCR_164 S164_P19: exit trigger with nothing drawn on 100% of it (nearest drawn 722 cm)
### 6 terrain (1322)
- SCR_320 tile 11,2: grass tile, 1997 walkable (largest region) on 100%, only 0% walkable for the capsule and 8% drawn on
- SCR_767 tile 7,3: grass tile, 1997 walkable (largest region) on 100%, only 0% walkable for the capsule and 9% drawn on
- SCR_671 tile 2,4: grass tile, 1997 walkable (largest region) on 100%, only 0% walkable for the capsule and 0% drawn on
- SCR_426 tile 1,2: grass tile, 1997 walkable (largest region) on 100%, only 1% walkable for the capsule and 0% drawn on
- SCR_470 tile 4,2: grass tile, 1997 walkable (largest region) on 100%, only 1% walkable for the capsule and 0% drawn on
- SCR_507 tile 5,2: grass tile, 1997 walkable (largest region) on 96%, only 1% walkable for the capsule and 0% drawn on
- SCR_690 tile 10,2: grass tile, 1997 walkable (largest region) on 100%, only 1% walkable for the capsule and 0% drawn on
- SCR_603 tile 4,6: grass tile, 1997 walkable (largest region) on 100%, only 1% walkable for the capsule and 0% drawn on
### 6 terrain (as 1997) (236)
- SCR_085 tile 1,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
- SCR_085 tile 2,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
- SCR_085 tile 3,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
- SCR_085 tile 4,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
- SCR_085 tile 5,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
- SCR_085 tile 6,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
- SCR_085 tile 7,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
- SCR_085 tile 8,1: lava tile, 100% walkable for the capsule; 1997 hardness 0 on 100% of it
### 7 standing inside (31)
- SCR_001 S001_P20: npc s1-h1-2 at (289,114) inside the drawn body of S001_P19; a capsule cannot stand there
- SCR_034 H34: scripted_prop s2-man1 at (70,280) inside the drawn body of S034_P29
- SCR_034 H35: scripted_prop s2-man2 at (70,220) inside the drawn body of S034_P28; a capsule cannot stand there
- SCR_034 H36: scripted_prop s2-ryant at (540,248) inside the drawn body of S034_P31; a capsule cannot stand there
- SCR_066 H2: npc s2-nadp at (264,256) inside the drawn body of S066_P21
- SCR_122 S122_P01: scripted_prop SM_Veg_ThornBush_02 at (169,141) inside the drawn body of S122_P05
- SCR_137 S137_P18: creature SM_DinkCard at (166,81) inside the drawn body of S137_P14
- SCR_229 S229_P07: scripted_prop SM_Crate_Large_PR at (326,287) inside the drawn body of S229_P08; a capsule cannot stand there

## Worst 40 mismatches (all categories)
- [1 invisible wall (tile low)] SCR_470 tile 4,1: grass_rocky tile: Dink stops up to 1813 cm (p90) from anything drawn on 100% of 242 px of contact edge
- [1 invisible wall (tile low)] SCR_470 tile 5,0: grass_rocky tile: Dink stops up to 1493 cm (p90) from anything drawn on 100% of 344 px of contact edge
- [1 invisible wall (tile low)] SCR_445 tile 1,7: grass_rocky tile: Dink stops up to 1370 cm (p90) from anything drawn on 100% of 358 px of contact edge
- [1 invisible wall (hardbox)] SCR_748 S748_P01: Dink stops up to 703 cm (p90) from anything drawn on 96% of its 519 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.1, mesh SM_DinkCard, kinds card
- [1 invisible wall (hardbox)] SCR_588 S588_P05: Dink stops up to 717 cm (p90) from anything drawn on 100% of its 376 px contact edge; its mesh does not reach the hardbox edge; class npc, type 1, seq 449.4, mesh SM_Save_Machine_PR, kinds family
- [1 invisible wall (tile low)] SCR_474 tile 0,0: grass_rocky tile: Dink stops up to 1660 cm (p90) from anything drawn on 100% of 172 px of contact edge
- [1 invisible wall (tile low)] SCR_474 tile 1,1: grass_rocky tile: Dink stops up to 1159 cm (p90) from anything drawn on 100% of 358 px of contact edge
- [1 invisible wall (tile low)] SCR_552 tile 4,0: grass_rocky tile: Dink stops up to 1179 cm (p90) from anything drawn on 100% of 344 px of contact edge
- [1 invisible wall (hardbox)] SCR_569 S569_P02: Dink stops up to 680 cm (p90) from anything drawn on 100% of its 376 px contact edge; its mesh does not reach the hardbox edge; class npc, type 1, seq 449.5, mesh SM_Save_Machine_PR, kinds family
- [1 invisible wall (hardbox)] SCR_762 S762_P01: Dink stops up to 615 cm (p90) from anything drawn on 96% of its 502 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.3, mesh SM_DinkCard, kinds card
- [1 invisible wall (hardbox)] SCR_763 S763_P20: Dink stops up to 622 cm (p90) from anything drawn on 92% of its 530 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.7, mesh SM_DinkCard, kinds card
- [1 invisible wall (tile low)] SCR_221 tile 9,1: wasteland tile: Dink stops up to 1566 cm (p90) from anything drawn on 100% of 179 px of contact edge
- [1 invisible wall (hardbox)] SCR_253 S253_P06: Dink stops up to 626 cm (p90) from anything drawn on 100% of its 430 px contact edge; its mesh does not reach the hardbox edge; class scripted_prop, type 1, seq 159.7, mesh SM_Shrine_Glass_PR, kinds family
- [1 invisible wall (tile low)] SCR_343 tile 0,1: grass_rocky tile: Dink stops up to 1454 cm (p90) from anything drawn on 100% of 197 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 4,0: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 7,0: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 3,2: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 8,2: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 4,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 5,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 6,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 7,3: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 4,0: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 7,0: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 3,2: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 8,2: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 4,3: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 5,3: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 6,3: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 7,3: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 4,1: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 99 px of contact edge
- [1 invisible wall (tile solid)] SCR_151 tile 7,1: snow tile: Dink stops up to 1925 cm (p90) from anything drawn on 100% of 99 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 4,1: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 99 px of contact edge
- [1 invisible wall (tile solid)] SCR_150 tile 7,1: snow tile: Dink stops up to 1924 cm (p90) from anything drawn on 100% of 99 px of contact edge
- [1 invisible wall (tile low)] SCR_406 tile 7,0: grass_rocky tile: Dink stops up to 1048 cm (p90) from anything drawn on 100% of 344 px of contact edge
- [1 invisible wall (hardbox)] SCR_764 S764_P02: Dink stops up to 584 cm (p90) from anything drawn on 94% of its 483 px contact edge; only its card is drawn; class sprite_prop, type 1, seq 424.3, mesh SM_DinkCard, kinds card
- [1 invisible wall (tile solid)] SCR_153 tile 4,0: snow tile: Dink stops up to 1884 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_153 tile 7,0: snow tile: Dink stops up to 1884 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_153 tile 3,2: snow tile: Dink stops up to 1884 cm (p90) from anything drawn on 100% of 100 px of contact edge
- [1 invisible wall (tile solid)] SCR_153 tile 8,2: snow tile: Dink stops up to 1884 cm (p90) from anything drawn on 100% of 100 px of contact edge
