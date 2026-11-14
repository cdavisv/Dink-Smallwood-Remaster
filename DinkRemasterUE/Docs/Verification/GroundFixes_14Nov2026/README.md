# Ground fixes: what the game draws on the tiles that failed the ground review (14 November 2026)

Follows `../GroundReview_13Nov2026/`. Everything here is visual: no collision, hardness, script, warp or origin ID changes. The world export gives byte-identical `collision.json`, `placements.json`, `warps.json`, `sprites.json` and `samples.json` before and after.

Captures are from the running game in a private copy (rebuilt C++, terrain materials rebuilt, world regenerated from nothing): 36 screens, three views each. `sheets/ground_NNN.jpg`: upper row before (master `8ba0e903`), lower row after; play camera, 1.1 m above the ground, from above the south edge. Screens without a "before" row were not captured on master.

## What changed, and what I saw

| Change | Switch | Sheets | Verdict after looking |
|---|---|---|---|
| Fourth terrain layer (mask RGB + remainder); a fifth folds into a layer of its own family | none (material) | 352, 385, 531, 320 | Works: 115 screens no longer lose a layer. 352 shows wet sand, dry sand, turf and stony turf together. On 531 the layer that returns is 3 tiles of flat rock (class `rock_mass`): correct to the data, still a flat slab. |
| Trees on the unwalkable forest-canopy tiles (2,590 points on 73 screens; every edge tree, 55% of the interior) | `dink.Forest 0/1` | 240, 272, 218; horizons of 438, 465, 505, 586 | Good. From inside: trunks, boughs, dappled litter. From the meadows a closed tree line where there was an empty horizon. The capture camera stands between the trees on 240, 272, 218 (boughs across the lens): a player cannot get there. |
| Tiles behind house fronts take the surrounding ground layer | none (export) | 505, 465, 586 | Good: turf behind the Windemere houses instead of a yard of giant yellow blocks. 419's capture stands inside a house shell and proves nothing. |
| Structured layers (boards, flagstones, cobbles, masonry) stay straight and at one scale; plank boards 18 cm | none (material) | 004, 034, 016, 385 | Good: the house floors read as boards. Cobbles unchanged in character, straight courses. |
| Water sheet over water tiles that have no water fill in the collision (7 screens) | `dink.WaterTiles 0/1` | `water_465_before_flat_translucent.jpg`, 244 | Partly. First try (opaque `M_Env_WaterFlat`, middle picture): a teal slab the hero walks on. Now `M_Env_Water` 9 cm above the bed (right picture): murky green shallows he wades through. Still a rectangle with straight edges and no bank. The condition stays **failed** in the review. |
| Relief rock on cliff, rock-mass and cave-wall tiles | `dink.Relief 0/1/2` (default 1) | `relief_184_251.jpg`, 244, 445, 596, 057, 099 | Small. Tier 1 places a boulder only where the 1997 hardness blocks a whole disc: 149 points on the 101 screens that have any. Those boulders look right (184, 251). The cliffs and outcrops themselves (244, 278, 445, 596) are as flat as before. Classes `cliff_face`, `rock_mass`, `chasm`, `cave_wall` stay **failed**. |
| Grass clearings round low props and decals | `grass.clear_max_height_cm` 0 = off | none | Runs (the game log reports 118 to 458 clearings as screens come into view). **Not proven by a capture**: the low props I aimed at (pitchforks on 274 and 440) are still sprite cards, so nothing shows a small mesh uncovered. |
| Feathered carpet edge | `grass.edge_feather` 0..1 | 278, 531 | Modest: the carpet thins and steps down toward paths; the line is still readable at 1.1 m. |
| No field-scale dry drift on snow | none (material) | 080, 120, 016 | The beige patches are gone from above. Snow still reads grey under the play camera. |

## Forest and the play camera (review finding, fixed)

`forest_play_camera_before_after.jpg`: screens 144, 239, 269, 282 and 218 at the play camera, the hero on open ground beside the forest. Upper row: the first version kept a tree only 8 px (about 55 cm) clear of walkable ground, so boughs hung across the camera (144, 239, 269). Lower row: the export now keeps every tree 40 px (about 2.8 m) from walkable ground and out of a 110 px corridor south of it, where the camera boom hangs (`FOREST_CLEAR_PX`, `FOREST_CAMERA_PX` in `Scripts/export_import_bundle.py`; 2,954 -> 2,590 trees; unit test). The hero is clear on all four and the forest is still closed behind him. 218 (right) and the sheets of 240, 272, 176, 208 are taken from spots inside the forest that the collision closes off: a capture can be teleported there, a player cannot walk there. Not handled: a tree on the screen to the south of walkable ground at a screen's southern edge (the rule looks at one screen).

## Snow and ice: cause found, not fixed

`snow_exposure_experiment.jpg`: screens 120 (snow), 13 (ice) and 80 at exposure bias +0.8 (left) and +1.5 (right), set with `dink.EnvPost bias`. The textures are near white (mean albedo 0.86 to 0.9); the automatic exposure meters a screen full of snow down to middle grey. At +0.8 EV both read as snow. A per-screen exposure compensation on snow screens is the fix; it is not in this PR.

## Black dashes on the turf from above

In the top-down panes the meadow shows short black dashes. They are the grass cards and their shadows seen edge-on from straight above, in the cells near the camera. At the play camera and at 1.1 m (010, 320, 438) there are none. Nothing changed.

## Audit

`ground_review.json` verdicts after this look: `forest_canopy`, `structure_facade` (outdoor) and `wood_floor` (indoor) now pass; no screen loses a layer.

| `art_coverage.py` | final | placeholder | cut |
|---|---:|---:|---:|
| master `80ff12f1`, rule off | 4,421 | 2,034 | 152 |
| master `80ff12f1`, rule on | 4,663 | 1,792 | 152 |
| this PR, rule on | 4,757 | 1,698 | 152 |

    Screen grounds: 5 final by screen-dressing, 336 final by reviewed terrain layers, 303 placeholder
       173 screens: tile class cliff_face (outdoor)
        76 screens: tile class rock_mass (outdoor)
        35 screens: tile class void (indoor)
        34 screens: tile class chasm (outdoor)
        23 screens: tile class snow (outdoor)
        21 screens: tile class ice (outdoor)
        16 screens: tile class cave_wall (indoor)
         6 screens: water tiles without a water surface
         3 screens: tile class grass (indoor)
         2 screens: tile class lava (indoor)
         2 screens: tile class void (outdoor)
         2 screens: tile class dirt (outdoor)
         1 screens: tile class cliff_face (indoor)

## Owner question: raised cliffs and rock

Making cliff and rock tiles stand up properly (a cliff wall, an outcrop one cannot see over) needs geometry where the 1997 hardness lets the player walk: hardness on those tiles is drawn as outlines only, and the remaster keeps cliff faces as open ground. Collision is untouched here. Options: (a) visual-only rock that the player can walk through (wrong to the eye), (b) collision that follows the rock (changes 1997 walkability: the owner's decision), (c) `dink.Relief 2`, which also fills enclosed pockets no walking player can enter (308 more points; not reviewed in the game, off by default).

## Not checked

- Grass clearings on a small bound prop (see above). Performance of 2,954 more tree instances (no frame-time measurement; each mesh is one instanced component per screen with a cull distance).
- `dink.Relief 2`, `dink.Forest 0`, `dink.WaterTiles 0` were not captured.
- Water sheets on 385, 494, 633, 736 (only 465 and 244 looked at). Screen 438 is dressed by a manifest and keeps its dry pond.
- Night or other lighting; the packaged game.
