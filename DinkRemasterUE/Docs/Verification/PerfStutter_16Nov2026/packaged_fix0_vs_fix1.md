## fixes_off

packaged build, Vulkan on AMD Radeon RX 6800 (RADV NAVI21), viewport 2560x1440, 6 cores (10 workers). Frame times in ms; game/render/RHI are the thread times `stat unit` shows, GPU the GPU frame time.

Dink switches at the end of the run: `dink.Anim.FootLock=1`, `dink.Anim.GroundAdapt=1`, `dink.Anim.Legs=1`, `dink.Anim.LookAt=1`, `dink.Anim.Style=1`, `dink.Audio.Life=1`, `dink.Forest=1`, `dink.GrassDensity=0`, `dink.Perf.AutoDetect=1`, `dink.Perf.AutoDetectTargetMs=13.5`, `dink.Perf.Fixes=0`, `dink.Perf.NeighbourBudgetMs=3`, `dink.Perf.StaticForestShadows=1`, `dink.Relief=1`

Machine during the run: load average 0.6-8.4, up to 1 Unreal processes (1 = this game alone), min 20052 MB available.

### Per lap (steady = standing on each stop; entry/walk = arriving)

| lap / part | fps | avg ms | p50 | p95 | p99 | max | >33 ms | >100 ms | game | render | RHI | GPU | draws | prims | sync loads | frames with an undressed screen in view | in-view screens dressed after the entry frame |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| default1 steady | 64.2 | 15.6 | 15.9 | 19.4 | 19.8 | 22 | 0 | 0 | 2.1 | 6.8 | 15.1 | 14.9 | 744 | 17951 | 0 | 0 | 0 |
| default1 entry | 63.3 | 15.8 | 16.1 | 19.6 | 21.9 | 79 | 5 | 0 | 2.6 | 7.3 | 15.3 | 15.1 | 764 | 21642 | 50 | 0 | 0 |
| default1 walk | 61.2 | 16.3 | 15.6 | 18.9 | 20.0 | 30 | 0 | 0 | 2.2 | 5.2 | 15.9 | 15.7 | 900 | 17716 | 1 | 0 | 0 |
| default2 steady | 63.9 | 15.6 | 16.1 | 19.6 | 20.0 | 22 | 0 | 0 | 2.1 | 6.8 | 15.2 | 15.0 | 937 | 20070 | 0 | 0 | 0 |
| default2 entry | 63.0 | 15.9 | 16.2 | 19.7 | 21.4 | 34 | 1 | 0 | 2.5 | 7.2 | 15.4 | 15.3 | 958 | 24807 | 10 | 0 | 0 |
| default2 walk | 62.9 | 15.9 | 15.7 | 18.6 | 19.1 | 33 | 0 | 0 | 2.2 | 7.1 | 15.4 | 15.3 | 1287 | 21751 | 0 | 0 | 0 |
| default2 gc | 57.8 | 17.3 | 17.1 | 18.4 | 18.7 | 21 | 0 | 0 | 2.3 | 5.0 | 16.7 | 16.7 | 1208 | 15108 | 0 | 0 | 0 |
| epic1 steady | 36.1 | 27.7 | 28.5 | 37.7 | 38.1 | 46 | 400 | 0 | 2.2 | 15.2 | 27.2 | 27.0 | 914 | 19263 | 0 | 0 | 0 |
| epic1 entry | 35.3 | 28.4 | 29.3 | 37.8 | 40.0 | 62 | 229 | 0 | 2.8 | 17.4 | 27.9 | 27.7 | 970 | 29337 | 10 | 0 | 0 |
| epic1 walk | 36.1 | 27.7 | 27.4 | 34.4 | 35.2 | 43 | 321 | 0 | 2.3 | 17.3 | 27.2 | 27.0 | 1280 | 22137 | 0 | 0 | 0 |
| high1 steady | 72.4 | 13.8 | 14.3 | 16.5 | 16.9 | 22 | 0 | 0 | 2.3 | 10.0 | 13.3 | 13.1 | 867 | 19155 | 0 | 0 | 0 |
| high1 entry | 71.6 | 14.0 | 14.4 | 16.7 | 19.0 | 28 | 0 | 0 | 2.5 | 9.7 | 13.4 | 13.3 | 874 | 22656 | 10 | 0 | 0 |
| high1 walk | 72.2 | 13.9 | 13.7 | 15.6 | 16.0 | 19 | 0 | 0 | 2.2 | 13.1 | 13.3 | 13.2 | 1163 | 21848 | 0 | 0 | 0 |
| medium1 steady | 109.3 | 9.1 | 9.3 | 11.8 | 12.4 | 14 | 0 | 0 | 2.3 | 8.7 | 8.5 | 8.5 | 789 | 18092 | 0 | 0 | 0 |
| medium1 entry | 108.1 | 9.3 | 9.3 | 12.0 | 13.1 | 20 | 0 | 0 | 2.5 | 8.4 | 8.6 | 8.5 | 797 | 20559 | 10 | 0 | 0 |
| medium1 walk | 104.6 | 9.6 | 9.4 | 11.2 | 12.9 | 28 | 0 | 0 | 2.5 | 8.8 | 8.8 | 8.8 | 1057 | 19557 | 0 | 0 | 0 |
| low1 steady | 197.9 | 5.1 | 5.0 | 5.9 | 6.3 | 16 | 0 | 0 | 2.2 | 3.4 | 4.2 | 4.4 | 479 | 7966 | 0 | 0 | 0 |
| low1 entry | 197.8 | 5.1 | 5.0 | 5.8 | 6.4 | 13 | 0 | 0 | 2.2 | 3.4 | 4.2 | 4.4 | 479 | 7913 | 10 | 0 | 0 |
| low1 walk | 184.9 | 5.4 | 5.3 | 6.0 | 6.7 | 15 | 0 | 0 | 2.0 | 4.0 | 4.7 | 4.8 | 682 | 8832 | 0 | 0 | 0 |

### Per stop, lap default and default1 (steady | arrival max ms, hitches > 33 ms)

| stop | lap | fps | p95 | p99 | game | render | GPU | draws | prims | arrival max | arrival >33 | arrival sync loads |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stonebrook_interior_001 | default1 | 62.9 | 16.5 | 16.9 | 2.0 | 15.9 | 15.2 | 458 | 25396 | 18 | 0 | 0 |
| stonebrook_exterior_438 | default1 | 62.9 | 16.8 | 17.0 | 2.1 | 1.5 | 15.2 | 868 | 18623 | 79 | 1 | 34 |
| forest_312 | default1 | 51.5 | 19.9 | 20.1 | 2.0 | 8.8 | 18.8 | 578 | 15988 | 37 | 1 | 1 |
| coast_650 | default1 | 58.3 | 17.6 | 17.8 | 2.1 | 2.5 | 16.5 | 801 | 15225 | 76 | 1 | 3 |
| town_terris_530 | default1 | 62.5 | 16.5 | 16.8 | 2.0 | 3.7 | 15.4 | 1283 | 16980 | 77 | 1 | 3 |
| cave_098 | default1 | 89.5 | 11.6 | 11.8 | 2.0 | 11.2 | 10.6 | 217 | 12108 | 17 | 0 | 0 |
| dungeon_579 | default1 | 69.0 | 15.0 | 15.4 | 2.1 | 3.1 | 13.9 | 786 | 24403 | 38 | 1 | 10 |
| combat_pillbugs_527 | default1 | 57.2 | 18.5 | 18.8 | 2.2 | 5.9 | 16.8 | 1201 | 15994 | 29 | 0 | 0 |

### Dink game-thread costs (DINK_PERF_SCOPE), lap default steady average and worst frame anywhere

| scope | ms per frame | calls per frame | worst frame ms |
|---|---|---|---|
| Dink_Creature_Tick | 0.000 | 0.0 | 4.1 |
| Dink_CreatureClass_Tick | 0.000 | 0.0 | 4.4 |
| Dink_InteriorCamera_Tick | 0.000 | 0.0 | 2.8 |
| Dink_Character_Tick | 0.000 | 0.0 | 1.8 |
| Dink_Humanoid_Tick | 0.000 | 0.0 | 3.1 |
| Dink_Gameplay_Tick | 0.000 | 0.0 | 5.0 |
| Dink_Director_Tick | 0.000 | 0.0 | 5.4 |
| Dink_Story_Tick | 0.000 | 0.0 | 5.7 |
| Dink_Env_UpdateGrass | 0.000 | 0.0 | 18.8 |
| Dink_Env_UpdateIndoor | 0.000 | 0.0 | 2.0 |
| Dink_Env_Tick | 0.000 | 0.0 | 71.6 |
| Dink_Greybox_LegacyCards | 0.000 | 0.0 | 6.2 |
| Dink_Greybox_RefreshScreen | 0.000 | 0.0 | 6.3 |
| Dink_Greybox_FaceCards | 0.000 | 0.0 | 3.3 |
| Dink_Greybox_Tick | 0.000 | 0.0 | 6.7 |
| Dink_Audio_Tick | 0.000 | 0.0 | 0.7 |
| Dink_Env_UpdateCorpses | 0.000 | 0.0 | 0.0 |
| Dink_Env_UpdateBurnables | 0.000 | 0.0 | 0.0 |
| Dink_Env_StateSwaps | 0.000 | 0.0 | 0.5 |
| Dink_Env_DressedCheck | 0.000 | 0.0 | 0.1 |
| Dink_Env_BuildGrassCell | 0.000 | 0.0 | 18.8 |
| Dink_Env_GatherGrassClears | 0.000 | 0.0 | 4.2 |
| Dink_Env_GatherGrassSources | 0.000 | 0.0 | 3.4 |
| Dink_Env_FindBurnables | 0.000 | 0.0 | 0.3 |
| Dink_Env_ApplyNeighbours | 0.000 | 0.0 | 63.1 |
| Dink_Family_DressInstances | 0.000 | 0.0 | 10.5 |
| Dink_Family_DressActor | 0.000 | 0.0 | 20.2 |
| Dink_Family_ApplyScreen | 0.000 | 0.0 | 22.8 |

### Hitches over 33 ms: 964 (worst 25 with causes)

| segment | frame ms | game | render | GPU | GC ms | screen change | sync loads | PSO precache | top scopes | log |
|---|---|---|---|---|---|---|---|---|---|---|
| high:switch:level | 279 | 115.5 | 15.1 | 35.1 | 0 |  |  | 0 | Dink_Env_Tick 17.9 ms; Dink_Env_UpdateGrass 17.8 ms; Dink_Env_BuildGrassCell 11.1 ms |  |
| medium:switch:level | 265 | 127.6 | 2.0 | 15.1 | 0 |  |  | 0 | Dink_Env_Tick 11.0 ms; Dink_Env_UpdateGrass 11.0 ms; Dink_Env_BuildGrassCell 4.8 ms |  |
| low:switch:level | 190 | 107.0 | 9.6 | 9.5 | 0 |  |  | 0 | Dink_Env_Tick 5.5 ms; Dink_Env_UpdateGrass 5.5 ms; Dink_Greybox_Tick 1.2 ms |  |
| default1:entry:stonebrook_exterior_438 | 79 | 78.0 | 16.0 | 15.1 | 0 | yes | 20: M_CameraFade_VegBark_v1, M_CameraFade_VegFoliage_v1, SM_Bridge_Wood_Deck_PR, SM_Bridge_Wood_Rail_Plank_PR | 0 | Dink_Env_Tick 70.5 ms; Dink_Env_ApplyNeighbours 63.1 ms; Dink_Family_ApplyScreen 13.9 ms | LogStreaming: FlushAsyncLoading(849): 1 QueuedPackages, 0 AsyncPackages |
| default1:entry:town_terris_530 | 77 | 76.5 | 8.8 | 16.9 | 0 | yes | 3: SM_Castle_Wall_8m, SM_Castle_Tower_Round, SM_Castle_Gatehouse | 0 | Dink_Env_Tick 71.6 ms; Dink_Env_ApplyNeighbours 58.7 ms; Dink_Family_ApplyScreen 12.5 ms | LogStreaming: FlushAsyncLoading(888): 1 QueuedPackages, 1 AsyncPackages |
| default1:entry:coast_650 | 76 | 74.9 | 1.2 | 12.9 | 0 | yes | 3: SM_Island_Hut_TwoStorey_PR, SM_Island_Fence_Lattice_PR, SM_Island_Hut_Round_PR | 0 | Dink_Env_Tick 69.8 ms; Dink_Env_ApplyNeighbours 51.7 ms; Dink_Family_ApplyScreen 21.1 ms | LogStreaming: FlushAsyncLoading(884): 1 QueuedPackages, 0 AsyncPackages |
| epic1:entry:forest_312 | 62 | 3.3 | 50.3 | 62.6 | 0 |  |  | 0 | Dink_Env_Tick 1.1 ms; Dink_Env_UpdateGrass 1.1 ms; Dink_Env_BuildGrassCell 1.1 ms |  |
| epic1:entry:forest_312 | 62 | 4.5 | 52.0 | 62.3 | 0 |  |  | 0 | Dink_Env_Tick 2.3 ms; Dink_Env_UpdateGrass 2.3 ms; Dink_Env_BuildGrassCell 2.3 ms |  |
| epic1:entry:forest_312 | 59 | 4.0 | 42.5 | 58.1 | 0 |  |  | 0 | Dink_Env_Tick 2.0 ms; Dink_Env_UpdateGrass 2.0 ms; Dink_Env_BuildGrassCell 2.0 ms |  |
| epic1:entry:forest_312 | 59 | 4.8 | 44.9 | 57.7 | 0 |  |  | 0 | Dink_Env_Tick 1.8 ms; Dink_Env_UpdateGrass 1.7 ms; Dink_Env_BuildGrassCell 1.7 ms |  |
| medium:switch:level | 58 | 32.4 | 260.8 | 15.1 | 0 |  |  | 0 | Dink_Env_Tick 6.0 ms; Dink_Env_UpdateGrass 6.0 ms; Dink_Env_BuildGrassCell 6.0 ms |  |
| epic1:entry:forest_312 | 58 | 4.6 | 44.2 | 58.1 | 0 |  |  | 0 | Dink_Env_Tick 2.5 ms; Dink_Env_UpdateGrass 2.4 ms; Dink_Env_BuildGrassCell 2.4 ms |  |
| epic1:steady:forest_312 | 46 | 1.9 | 32.8 | 37.4 | 0 |  |  | 0 |  |  |
| epic1:steady:forest_312 | 44 | 4.5 | 27.8 | 37.4 | 0 |  |  | 0 |  |  |
| epic1:walk:forest_312 | 43 | 3.7 | 28.3 | 41.7 | 0 |  |  | 0 | Dink_Env_Tick 1.5 ms; Dink_Env_UpdateGrass 1.5 ms; Dink_Env_BuildGrassCell 1.5 ms |  |
| low:switch:level | 43 | 5.7 | 183.3 | 9.5 | 0 |  |  | 0 |  |  |
| high:switch:level | 43 | 10.8 | 3.3 | 35.1 | 0 |  |  | 0 | Dink_Env_Tick 6.6 ms; Dink_Env_UpdateGrass 6.6 ms; Dink_Env_BuildGrassCell 6.6 ms |  |
| epic1:entry:combat_pillbugs_527 | 43 | 11.4 | 29.9 | 40.3 | 0 |  |  | 0 | Dink_Env_Tick 9.0 ms; Dink_Env_UpdateGrass 9.0 ms; Dink_Env_BuildGrassCell 8.9 ms |  |
| epic1:steady:forest_312 | 42 | 3.1 | 23.9 | 40.7 | 0 |  |  | 0 | Dink_Greybox_Tick 1.3 ms; Dink_Greybox_RefreshScreen 1.1 ms; Dink_Greybox_LegacyCards 1.0 ms |  |
| epic1:walk:forest_312 | 42 | 3.8 | 28.7 | 42.2 | 0 |  |  | 0 | Dink_Env_Tick 1.9 ms; Dink_Env_UpdateGrass 1.9 ms; Dink_Env_BuildGrassCell 1.9 ms |  |
| epic1:entry:forest_312 | 41 | 2.2 | 25.3 | 38.5 | 0 |  |  | 0 |  |  |
| epic1:entry:forest_312 | 40 | 4.3 | 27.3 | 39.1 | 0 |  |  | 0 | Dink_Env_Tick 2.2 ms; Dink_Env_UpdateGrass 2.2 ms; Dink_Env_BuildGrassCell 2.2 ms |  |
| epic1:entry:forest_312 | 40 | 6.0 | 26.0 | 39.5 | 0 |  |  | 0 | Dink_Env_Tick 2.8 ms; Dink_Env_UpdateGrass 2.8 ms; Dink_Env_BuildGrassCell 2.8 ms |  |
| epic1:entry:forest_312 | 40 | 2.2 | 25.9 | 38.7 | 0 |  |  | 0 |  |  |
| epic1:entry:forest_312 | 40 | 5.2 | 26.4 | 39.7 | 0 |  |  | 0 | Dink_Env_Tick 3.1 ms; Dink_Env_UpdateGrass 3.1 ms; Dink_Env_BuildGrassCell 3.0 ms |  |

### Synchronous package loads during the route: 51 packages

- `/Game/Dink/Camera/Vegetation/M_CameraFade_VegBark_v1`
- `/Game/Dink/Camera/Vegetation/M_CameraFade_VegFoliage_v1`
- `/Game/Dink/Photoreal/Structures/SM_Bridge_Wood_Deck_PR`
- `/Game/Dink/Photoreal/Structures/SM_Bridge_Wood_Rail_Plank_PR`
- `/Game/Dink/Photoreal/Structures/SM_Bridge_Wood_Rail_Rope_PR`
- `/Game/Dink/Photoreal/Structures/SM_Well_Stone_PR`
- `/Game/Dink/Photoreal/Structures/SM_Well_ShaftCap_PR`
- `/Game/Dink/Photoreal/Structures/SM_Cottage_Thatched_Large_PR`
- `/Game/Dink/Kits/Stonebrook440/SM_House_Stonebrook_TwoStorey_01`
- `/Game/Dink/Kits/Stonebrook440/SM_Woodpile_Split_01`
- `/Game/Dink/Kits/Stonebrook440/SM_WaterTrough_Oak_01`
- `/Game/Dink/Kits/Stonebrook440/SM_ChoppingBlock_Axe_01`
- `/Game/Dink/Kits/Stonebrook440/SM_Wheelbarrow_Oak_01`
- `/Game/Dink/Kits/Stonebrook440/SM_HayBale_01`
- `/Game/Dink/Kits/Stonebrook440/SM_Axe_Felling_01`
- `/Game/Dink/Kits/Stonebrook440/SM_Tongs_Iron_01`
- `/Game/Dink/Kits/Stonebrook440/SM_Hatchet_01`
- `/Game/Dink/Photoreal/Structures/SM_Cottage_Thatched_Small_PR`
- `/Game/Dink/Photoreal/Structures/SM_Cottage_Door_PR`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Wall_Window_R`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Wall_Window_L`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Wall_Plain`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Roof_Slope_B`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Roof_Slope`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Roof_RidgeCap`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Wall_GableEnd`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Roof_Verge`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Corner_Quoin`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Chimney_Stack`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Wall_Door`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Door_Studded`
- `/Game/Dink/Photoreal/Vegetation/MI_Veg_MeadowGrass_Scatter`
- `/Game/Dink/Photoreal/Vegetation/MI_Veg_GroundCover_Scatter`
- `/Engine/BasicShapes/Plane`
- `/Game/Dink/Photoreal/TownExteriors/SM_Town_Roof_Dormer`
- `/Game/Dink/Photoreal/Structures/SM_Island_Hut_TwoStorey_PR`
- `/Game/Dink/Photoreal/Structures/SM_Island_Fence_Lattice_PR`
- `/Game/Dink/Photoreal/Structures/SM_Island_Hut_Round_PR`
- `/Game/Dink/Photoreal/Structures/SM_Castle_Wall_8m`
- `/Game/Dink/Photoreal/Structures/SM_Castle_Tower_Round`
- `/Game/Dink/Photoreal/Structures/SM_Castle_Gatehouse`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_01`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_02`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_03`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_04`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_05`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_06`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_07`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_08`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_09`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_10`

## fixes_on

packaged build, Vulkan on AMD Radeon RX 6800 (RADV NAVI21), viewport 2560x1440, 6 cores (10 workers). Frame times in ms; game/render/RHI are the thread times `stat unit` shows, GPU the GPU frame time.

Dink switches at the end of the run: `dink.Anim.FootLock=1`, `dink.Anim.GroundAdapt=1`, `dink.Anim.Legs=1`, `dink.Anim.LookAt=1`, `dink.Anim.Style=1`, `dink.Audio.Life=1`, `dink.Forest=1`, `dink.GrassDensity=0`, `dink.Perf.AutoDetect=1`, `dink.Perf.AutoDetectTargetMs=13.5`, `dink.Perf.Fixes=1`, `dink.Perf.NeighbourBudgetMs=3`, `dink.Perf.StaticForestShadows=1`, `dink.Relief=1`

Machine during the run: load average 2.6-9.3, up to 2 Unreal processes (1 = this game alone; OTHER UNREAL PROCESSES RAN BESIDE IT, numbers are skewed), min 16579 MB available.

### Per lap (steady = standing on each stop; entry/walk = arriving)

| lap / part | fps | avg ms | p50 | p95 | p99 | max | >33 ms | >100 ms | game | render | RHI | GPU | draws | prims | sync loads | frames with an undressed screen in view | in-view screens dressed after the entry frame |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| default1 steady | 68.3 | 14.7 | 15.8 | 17.4 | 19.7 | 31 | 0 | 0 | 2.0 | 6.4 | 13.3 | 13.8 | 744 | 17803 | 0 | 0 | 0 |
| default1 entry | 67.4 | 14.8 | 15.9 | 17.9 | 24.1 | 92 | 5 | 0 | 2.4 | 7.4 | 13.4 | 13.9 | 748 | 21053 | 15 | 0 | 0 |
| default1 walk | 64.3 | 15.6 | 15.7 | 16.9 | 18.5 | 33 | 0 | 0 | 1.9 | 8.8 | 14.5 | 14.7 | 925 | 16795 | 0 | 0 | 0 |
| default2 steady | 68.5 | 14.6 | 16.0 | 17.5 | 18.2 | 28 | 0 | 0 | 1.9 | 7.1 | 13.5 | 13.8 | 906 | 19735 | 0 | 0 | 0 |
| default2 entry | 67.2 | 14.9 | 16.2 | 18.2 | 20.6 | 37 | 2 | 0 | 2.3 | 7.0 | 13.6 | 14.1 | 928 | 24042 | 10 | 0 | 0 |
| default2 walk | 63.3 | 15.8 | 15.9 | 17.6 | 19.0 | 31 | 0 | 0 | 2.4 | 8.9 | 14.4 | 14.8 | 1272 | 21522 | 0 | 0 | 0 |
| default2 gc | 60.0 | 16.7 | 16.6 | 18.0 | 19.5 | 23 | 0 | 0 | 2.1 | 2.9 | 16.0 | 15.9 | 1390 | 26588 | 0 | 0 | 0 |
| default2 gcnat | 59.5 | 16.8 | 16.8 | 17.4 | 17.8 | 20 | 0 | 0 | 1.7 | 1.7 | 16.2 | 16.1 | 1568 | 26233 | 0 | 0 | 0 |
| epic1 steady | 38.8 | 25.8 | 28.4 | 31.5 | 32.5 | 38 | 21 | 0 | 1.7 | 18.8 | 25.1 | 25.1 | 899 | 19434 | 0 | 0 | 0 |
| epic1 entry | 37.9 | 26.4 | 29.0 | 33.3 | 37.7 | 63 | 60 | 0 | 2.0 | 19.1 | 25.8 | 25.7 | 935 | 28193 | 10 | 0 | 0 |
| epic1 walk | 37.1 | 27.0 | 27.4 | 30.2 | 32.1 | 45 | 9 | 0 | 1.7 | 23.3 | 26.3 | 26.2 | 1265 | 21122 | 0 | 0 | 0 |
| high1 steady | 79.0 | 12.7 | 13.5 | 15.3 | 15.8 | 21 | 0 | 0 | 1.6 | 10.7 | 11.8 | 12.0 | 835 | 18801 | 0 | 0 | 0 |
| high1 entry | 78.0 | 12.8 | 13.6 | 15.5 | 17.0 | 28 | 0 | 0 | 1.8 | 10.4 | 12.0 | 12.1 | 843 | 21814 | 10 | 0 | 0 |
| high1 walk | 73.8 | 13.5 | 13.7 | 14.5 | 15.2 | 21 | 0 | 0 | 1.7 | 13.1 | 12.9 | 12.8 | 1149 | 21669 | 0 | 0 | 0 |
| medium1 steady | 127.2 | 7.9 | 8.5 | 9.9 | 10.4 | 12 | 0 | 0 | 1.6 | 6.7 | 6.9 | 7.2 | 755 | 17548 | 0 | 0 | 0 |
| medium1 entry | 124.9 | 8.0 | 8.5 | 10.3 | 13.4 | 21 | 0 | 0 | 1.8 | 6.6 | 7.0 | 7.3 | 757 | 19522 | 10 | 0 | 0 |
| medium1 walk | 114.2 | 8.8 | 8.7 | 9.7 | 10.2 | 16 | 0 | 0 | 1.6 | 8.0 | 8.2 | 8.1 | 1041 | 19475 | 0 | 0 | 0 |
| low1 steady | 238.0 | 4.2 | 4.8 | 5.7 | 6.1 | 15 | 0 | 0 | 1.4 | 2.9 | 3.3 | 3.6 | 440 | 7964 | 0 | 0 | 0 |
| low1 entry | 237.7 | 4.2 | 4.8 | 5.7 | 6.1 | 13 | 0 | 0 | 1.4 | 2.9 | 3.3 | 3.6 | 441 | 7946 | 10 | 0 | 0 |
| low1 walk | 186.1 | 5.4 | 5.4 | 5.9 | 6.3 | 10 | 0 | 0 | 1.5 | 4.6 | 4.7 | 4.8 | 665 | 8600 | 0 | 0 | 0 |
| epic751 steady | 55.5 | 18.0 | 19.8 | 21.6 | 22.5 | 37 | 1 | 0 | 2.0 | 10.7 | 16.7 | 17.2 | 904 | 19584 | 0 | 0 | 0 |
| epic751 entry | 54.6 | 18.3 | 19.9 | 23.0 | 25.3 | 43 | 3 | 0 | 2.3 | 10.5 | 17.0 | 17.5 | 921 | 25459 | 10 | 0 | 0 |
| epic751 walk | 52.7 | 19.0 | 19.2 | 21.1 | 22.3 | 33 | 0 | 0 | 2.0 | 13.7 | 18.0 | 18.2 | 1270 | 21529 | 0 | 0 | 0 |
| mediumplus1 steady | 80.5 | 12.4 | 13.3 | 15.1 | 15.6 | 21 | 0 | 0 | 1.7 | 12.3 | 11.4 | 11.8 | 760 | 17445 | 0 | 0 | 0 |
| mediumplus1 entry | 78.9 | 12.7 | 13.6 | 15.5 | 17.4 | 24 | 0 | 0 | 2.0 | 12.1 | 11.5 | 12.0 | 774 | 21019 | 10 | 0 | 0 |
| mediumplus1 walk | 76.0 | 13.2 | 12.9 | 15.1 | 15.7 | 21 | 0 | 0 | 1.7 | 13.1 | 12.5 | 12.5 | 1038 | 19066 | 0 | 0 | 0 |
| lowplus1 steady | 186.2 | 5.4 | 5.9 | 7.0 | 7.7 | 14 | 0 | 0 | 1.5 | 3.0 | 4.3 | 4.7 | 602 | 7842 | 0 | 0 | 0 |
| lowplus1 entry | 186.5 | 5.4 | 5.9 | 7.0 | 8.8 | 17 | 0 | 0 | 1.6 | 2.9 | 4.3 | 4.7 | 595 | 7780 | 10 | 0 | 0 |
| lowplus1 walk | 156.2 | 6.4 | 6.3 | 7.2 | 8.0 | 11 | 0 | 0 | 1.6 | 4.1 | 5.6 | 5.7 | 807 | 8526 | 0 | 0 | 0 |

### Per stop, lap default and default1 (steady | arrival max ms, hitches > 33 ms)

| stop | lap | fps | p95 | p99 | game | render | GPU | draws | prims | arrival max | arrival >33 | arrival sync loads |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stonebrook_interior_001 | default1 | 62.9 | 16.5 | 16.9 | 1.5 | 15.9 | 15.2 | 458 | 25282 | 18 | 0 | 0 |
| stonebrook_exterior_438 | default1 | 62.9 | 16.9 | 17.2 | 1.6 | 2.0 | 15.2 | 866 | 19217 | 28 | 0 | 4 |
| forest_312 | default1 | 60.7 | 17.1 | 17.5 | 1.5 | 16.4 | 15.7 | 592 | 15602 | 44 | 1 | 1 |
| coast_650 | default1 | 58.9 | 19.4 | 23.6 | 1.9 | 4.9 | 16.0 | 830 | 15746 | 46 | 1 | 0 |
| town_terris_530 | default1 | 61.7 | 17.5 | 18.1 | 2.1 | 4.3 | 15.3 | 1274 | 16081 | 92 | 2 | 0 |
| cave_098 | default1 | 101.8 | 11.8 | 13.4 | 2.6 | 3.8 | 8.9 | 239 | 12115 | 24 | 0 | 0 |
| dungeon_579 | default1 | 76.8 | 14.3 | 15.9 | 2.2 | 2.2 | 12.2 | 812 | 24506 | 51 | 1 | 10 |
| combat_pillbugs_527 | default1 | 60.3 | 19.5 | 22.8 | 2.0 | 4.0 | 15.7 | 1206 | 15588 | 21 | 0 | 0 |

### Dink game-thread costs (DINK_PERF_SCOPE), lap default steady average and worst frame anywhere

| scope | ms per frame | calls per frame | worst frame ms |
|---|---|---|---|
| Dink_Creature_Tick | 0.000 | 0.0 | 4.1 |
| Dink_CreatureClass_Tick | 0.000 | 0.0 | 4.0 |
| Dink_InteriorCamera_Tick | 0.000 | 0.0 | 2.1 |
| Dink_Character_Tick | 0.000 | 0.0 | 5.1 |
| Dink_Humanoid_Tick | 0.000 | 0.0 | 3.0 |
| Dink_Gameplay_Tick | 0.000 | 0.0 | 2.1 |
| Dink_Director_Tick | 0.000 | 0.0 | 2.5 |
| Dink_Story_Tick | 0.000 | 0.0 | 9.5 |
| Dink_Env_UpdateGrass | 0.000 | 0.0 | 13.8 |
| Dink_Env_UpdateIndoor | 0.000 | 0.0 | 3.7 |
| Dink_Env_Tick | 0.000 | 0.0 | 78.9 |
| Dink_Greybox_FaceNearbyCards | 0.000 | 0.0 | 1.7 |
| Dink_Greybox_Tick | 0.000 | 0.0 | 8.9 |
| Dink_Audio_Tick | 0.000 | 0.0 | 2.0 |
| Dink_Env_UpdateCorpses | 0.000 | 0.0 | 0.1 |
| Dink_Env_UpdateBurnables | 0.000 | 0.0 | 0.1 |
| Dink_Env_StateSwaps | 0.000 | 0.0 | 0.1 |
| Dink_Greybox_LegacyCards | 0.000 | 0.0 | 3.2 |
| Dink_Greybox_RefreshScreen | 0.000 | 0.0 | 8.9 |
| Dink_Env_DressedCheck | 0.000 | 0.0 | 0.4 |
| Dink_Env_BuildGrassCell | 0.000 | 0.0 | 6.2 |
| Dink_Env_PreloadScatter | 0.000 | 0.0 | 0.3 |
| Dink_Env_GatherGrassClears | 0.000 | 0.0 | 9.0 |
| Dink_Env_GatherGrassSources | 0.000 | 0.0 | 9.3 |
| Dink_Env_FindBurnables | 0.000 | 0.0 | 0.0 |
| Dink_Env_ApplyNeighbourScreen | 0.000 | 0.0 | 58.5 |
| Dink_Env_DrainNeighbours | 0.000 | 0.0 | 58.5 |
| Dink_Family_DressInstances | 0.000 | 0.0 | 12.1 |
| Dink_Family_DressActor | 0.000 | 0.0 | 15.5 |
| Dink_Family_ApplyScreen | 0.000 | 0.0 | 27.7 |

### Hitches over 33 ms: 183 (worst 25 with causes)

| segment | frame ms | game | render | GPU | GC ms | screen change | sync loads | PSO precache | top scopes | log |
|---|---|---|---|---|---|---|---|---|---|---|
| epic751:shot:coast_650 | 521 | 2.1 | 20.6 | 20.1 | 0 |  |  | 0 |  |  |
| mediumplus:switch:level | 521 | 195.7 | 7.5 | 21.8 | 0 |  |  | 0 | Dink_Env_Tick 13.8 ms; Dink_Env_UpdateGrass 13.8 ms; Dink_Env_BuildGrassCell 2.2 ms | LogConsoleManager: Setting the console variable 'r.ScreenPercentage' with 'SetByScalabilit |
| default1:shot:coast_650 | 498 | 2.1 | 0.1 | 16.1 | 0 |  |  | 0 |  |  |
| epic751:shot:combat_pillbugs_527 | 497 | 2.6 | 7.8 | 20.9 | 0 |  |  | 0 |  |  |
| epic1:shot:combat_pillbugs_527 | 476 | 1.8 | 9.9 | 29.5 | 0 |  |  | 0 |  |  |
| epic1:shot:stonebrook_exterior_438 | 474 | 1.8 | 29.8 | 28.7 | 0 |  |  | 0 |  |  |
| epic751:shot:town_terris_530 | 473 | 2.1 | 3.0 | 18.9 | 0 |  |  | 0 |  |  |
| epic1:shot:stonebrook_interior_001 | 471 | 1.7 | 29.5 | 28.7 | 0 |  |  | 0 |  |  |
| epic1:shot:coast_650 | 471 | 1.7 | 31.4 | 30.7 | 0 |  |  | 0 |  |  |
| epic1:shot:town_terris_530 | 453 | 1.6 | 28.1 | 27.8 | 0 |  |  | 0 |  |  |
| epic1:shot:forest_312 | 449 | 1.7 | 29.2 | 29.5 | 0 |  |  | 0 |  |  |
| epic1:shot:dungeon_579 | 440 | 1.8 | 2.8 | 23.1 | 0 |  |  | 0 |  |  |
| epic751:shot:dungeon_579 | 434 | 2.2 | 2.8 | 15.3 | 0 |  |  | 0 |  |  |
| epic751:shot:stonebrook_interior_001 | 432 | 1.6 | 19.6 | 19.6 | 0 |  |  | 0 |  |  |
| default1:shot:town_terris_530 | 428 | 2.0 | 4.3 | 15.3 | 0 |  |  | 0 |  |  |
| epic751:shot:stonebrook_exterior_438 | 426 | 1.6 | 2.9 | 20.0 | 0 |  |  | 0 |  |  |
| default1:shot:stonebrook_exterior_438 | 422 | 1.7 | 0.2 | 15.7 | 0 |  |  | 0 |  |  |
| high1:shot:stonebrook_interior_001 | 421 | 1.7 | 16.1 | 14.5 | 0 |  |  | 0 |  |  |
| high1:shot:stonebrook_exterior_438 | 412 | 1.8 | 14.2 | 13.8 | 0 |  |  | 0 |  |  |
| epic751:shot:forest_312 | 411 | 1.5 | 21.3 | 20.5 | 0 |  |  | 0 |  |  |
| mediumplus1:shot:combat_pillbugs_527 | 410 | 1.8 | 13.4 | 12.9 | 0 |  |  | 0 |  |  |
| default1:shot:stonebrook_interior_001 | 409 | 1.5 | 15.3 | 14.9 | 0 |  |  | 0 |  |  |
| high1:shot:combat_pillbugs_527 | 408 | 1.5 | 0.3 | 13.0 | 0 |  |  | 0 |  |  |
| mediumplus1:shot:stonebrook_exterior_438 | 406 | 1.9 | 13.7 | 13.3 | 0 |  |  | 0 |  |  |
| mediumplus1:shot:stonebrook_interior_001 | 406 | 1.7 | 15.0 | 14.1 | 0 |  |  | 0 |  |  |

### Synchronous package loads during the route: 15 packages

- `/Game/Dink/Camera/Vegetation/M_CameraFade_VegBark_v1`
- `/Game/Dink/Camera/Vegetation/M_CameraFade_VegFoliage_v1`
- `/Game/Dink/Photoreal/Vegetation/MI_Veg_MeadowGrass_Scatter`
- `/Game/Dink/Photoreal/Vegetation/MI_Veg_GroundCover_Scatter`
- `/Engine/BasicShapes/Plane`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_01`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_02`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_03`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_04`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_05`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_06`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_07`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_08`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_09`
- `/Game/Dink/_Generated/Sprites/MI_Sprite_373_10`

## Comparison (steady frames of every lap, per lap)

| lap | fixes_off fps / p99 / GPU | fixes_on fps / p99 / GPU |
|---|---|---|
| default | - | - |
| default1 | 64.2 / 19.8 / 14.9 | 68.3 / 19.7 / 13.8 |
| default2 | 63.9 / 20.0 / 15.0 | 68.5 / 18.2 / 13.8 |
| epic | - | - |
| epic1 | 36.1 / 38.1 / 27.0 | 38.8 / 32.5 / 25.1 |
| high | - | - |
| high1 | 72.4 / 16.9 / 13.1 | 79.0 / 15.8 / 12.0 |
| medium | - | - |
| medium1 | 109.3 / 12.4 / 8.5 | 127.2 / 10.4 / 7.2 |
| low | - | - |
| low1 | 197.9 / 6.3 / 4.4 | 238.0 / 6.1 / 3.6 |
| epic75 | - | - |
| epic751 | - | 55.5 / 22.5 / 17.2 |
| mediumplus | - | - |
| mediumplus1 | - | 80.5 / 15.6 / 11.8 |
| lowplus | - | - |
| lowplus1 | - | 186.2 / 7.7 / 4.7 |

| arrivals (entry + walk) | fixes_off max ms / >33 ms / sync loads | fixes_on max ms / >33 ms / sync loads |
|---|---|---|
| default | - | - |
| default1 | 79 / 5 / 51 | 92 / 5 / 15 |
| default2 | 34 / 1 / 10 | 37 / 2 / 10 |
| epic | - | - |
| epic1 | 62 / 550 / 10 | 63 / 69 / 10 |
| high | - | - |
| high1 | 28 / 0 / 10 | 28 / 0 / 10 |
| medium | - | - |
| medium1 | 28 / 0 / 10 | 21 / 0 / 10 |
| low | - | - |
| low1 | 15 / 0 / 10 | 13 / 0 / 10 |
| epic75 | - | - |
| epic751 | - | 43 / 3 / 10 |
| mediumplus | - | - |
| mediumplus1 | - | 24 / 0 / 10 |
| lowplus | - | - |
| lowplus1 | - | 17 / 0 / 10 |
