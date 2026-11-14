# Screen grounds: in-game review and the audit rule (13 November 2026)

644 coverage rows are "screen ground (tile layer)": the 12 x 8 tiles of each screen. Until now `Scripts/art_coverage.py` called every one of them placeholder ("greybox ground mesh") unless an art manifest dresses the screen (5 screens, so 639 were open), although every screen has drawn the photoreal terrain material since PR #86. This folder is the evidence for counting part of them final, and the list of what is not.

## The rule (one switch; the owner decides whether it stays on)

A screen ground counts **final** when all of this holds (`screen_ground_state()` in `Scripts/art_coverage.py`):

1. the screen instances the photoreal terrain material (none keeps the 1997 painted ground) and every tile has a terrain layer;
2. the master material and the BC, N, ORM and H textures of every layer the screen's mask carries exist;
3. no layer was dropped by the three-layer mask (those tiles are drawn as an unrelated layer);
4. **every tile class on the screen passed the in-game review**, outdoors or indoors as the screen is. A class nobody looked at does not pass;
5. water tiles have a water surface;
6. the review holds no finding against that one screen.

The verdicts are data, kept by hand: `Content/Dink/Data/Environment/ground_review.json`. What a screen is made of is written by the world export: `Content/Dink/Data/Environment/ground_classes.json`.

**The switch:** `ground_review.json` `rule.count_reviewed_grounds_final` (`true` in this PR). Set it to `false`, or run `art_coverage.py --ground-rule off`, and no ground counts final by review: the audit is then exactly what it was before.

| `art_coverage.py` | final | placeholder | cut |
|---|---:|---:|---:|
| rule off (as on master `8ba0e903`) | 4,093 | 2,362 | 152 |
| rule on (this PR's default) | 4,335 | 2,120 | 152 |

242 screen grounds turn final; 397 stay placeholder, each with its reasons in the audit CSV.

What the rule does and does not claim: it generalises from the screens that were looked at to every screen made of the same tile classes. The 242 final screens are made only of grass, stony turf, earth path, cobbles, sand, shingle, scorched soil and water outdoors, and flagstones or cave floor indoors. 54 screens were captured and looked at (list below); about fourteen of them are among the 242. If the owner wants a ground final only after that screen itself was looked at, switch the rule off.

## How it was looked at

`Scripts/PhotorealQA/ground_script.py` picks screens from the data: per terrain layer and per relief tile class the screens with the largest share, every screen whose layer set no other screen has, the worst dropped-layer screens, water tiles without a surface, known doubts (82 screens). Per screen three captures from the running game (private copy of master's world): the play camera, a camera 1.1 m above the ground, and a view from above the south edge. `Scripts/PhotorealQA/ground_sheet.py --by-class` lays them out: `sheets/` (28 sheets, one per reason a screen was chosen; each row is one screen, three views, labelled with its tile classes and layers).

54 of the 82 screens were captured (the third capture run crashed in the renderer on screen 624 and the editor was not free again). Not captured: 320, 353, 354, 355, 369, 370, 385, 386, 387, 388, 407, 418, 419, 424, 433, 667, 694, 710, 713, 714, 721, 734, 735, 736, 757, 762, 766. So not looked at: the open-sea screens, the TransitionDirt layer (class `dirt`, stays "not reviewed"), the town yards of Kernsin and Terris, and the worst dropped-layer screens (those are placeholder by condition 3 anyway).

Screen 498's capture stands inside a house shell (the stand point lay behind a wall line); it was not used for a verdict.

## Verdicts

| Tile class | Where | Screens | Verdict | Looked at (screens) | Why |
|---|---|---:|---|---|---|
| void | indoor | 36 | fail | 33, 133 | the black outside of a room is drawn as warped masonry floor |
| wood_floor | indoor | 32 | fail | 4, 33, 34, 67 | wood grain metres wide instead of boards (plank scale, with the interior work of the photoreal-pass session) |
| stone_floor | indoor | 21 | pass | 70, 73, 514 | dark flagstones under the lantern light |
| cave_floor | indoor | 16 | pass | 69, 98, 257 | wet dark rock floor under the cave light |
| cave_wall | indoor | 16 | fail | 99, 132, 258 | cave walls are the same flat floor, the room ends at a plain grey box |
| grass | indoor | 3 | fail | 86 | a flat lawn photograph without blades, lit by the cave light |
| lava | indoor | 2 | fail | 85, 86 | a glowing line pattern on flat black that repeats visibly, no relief, no molten body |
| cliff_face | indoor | 1 | not reviewed | | no screen of it was captured |
| grass | outdoor | 399 | pass | 10, 299, 438, 510, 624 | bladed turf carpet over the meadow layer, reads as a real meadow at the play camera and at 1.1 m |
| grass_rocky | outdoor | 295 | pass | 445, 510, 624 | short stony turf between the tall grass, the carpet edge beside it is a hard line (feathering is in the ground-fixes work) |
| water | outdoor | 210 | pass | 489, 510, 519 | where a water surface is drawn: rippled translucent water with a shallow band (the condition water_without_surface covers the rest) |
| cliff_face | outdoor | 173 | fail | 244, 278, 285 | a cliff painted in the 1997 tiles is drawn as a flat brown rock floor |
| sand | outdoor | 102 | pass | 519 | wind-marked dry sand, wet band at the waterline |
| forest_canopy | outdoor | 76 | fail | 218, 240, 272, 312 | closed forest in the 1997 tiles is bare leaf litter with no trees |
| rock_mass | outdoor | 76 | fail | 445, 510, 596 | rock outcrops drawn as flat, tile-shaped slabs of rock texture |
| path | outdoor | 74 | pass | 531, 536, 586 | trodden earth with stones, holds at the play camera. Known defects: the grass carpet ends on a hard saw-tooth line, and the detail warp smears the texture in places at 1.1 m (536) |
| wasteland | outdoor | 50 | pass | 91, 191, 223 | cracked scorched soil, holds at the play camera. Known defect: the detail warp swirls the cracks at 1.1 m |
| chasm | outdoor | 34 | fail | 57, 89, 121, 256 | the chasm is a flat rock floor one can see across |
| structure_facade | outdoor | 29 | fail | 465, 505, 586 | ground under the 1997 building pictures is drawn as wall masonry laid flat (a yellow yard of giant blocks behind the houses) |
| stone_floor | outdoor | 25 | pass | 16, 48 | worn cobbles with relief and dirt in the joints |
| snow | outdoor | 23 | fail | 80, 120, 149, 153 | white in sunlight (80, 149) but grey-beige with dark scribbled ripples under the overcast sky of 120 and 153: reads as rippled sand |
| ice | outdoor | 21 | fail | 13, 82, 109 | drawn as grey trampled mud, nothing reads as ice or snow |
| gravel | outdoor | 4 | pass | 489 | river shingle with relief |
| dirt | outdoor | 3 | not reviewed | | no screen of it was captured |
| void | outdoor | 2 | fail | 145, 256 | warped masonry floor where the 1997 screen is black |

Condition `water_without_surface`: **fail** (438, 465). The pond of 438 is an empty pit with a green floor and the river of 465 a dry sand bed.

## What I saw, sheet by sheet

- `layer_MeadowTurf`, `layer_RockyGrass`, `water_tiles_without_a_water_surface` (438): the meadow is the best ground in the game: bladed grass with seed heads, colour variation, believable at the play camera and at 1.1 m. From above, the blade shadows read as dark flecks.
- `layer_EarthPath`, `layer_ScorchedSoil`: good at the play camera. At 1.1 m the detail warp smears and swirls the texture in places (536, 191, 223). The grass carpet ends on a hard saw-tooth line beside paths.
- `layer_CobbleStreet`, `layer_ShingleBeach` (in `layer_set_no_other_screen_has_1`), `layer_DrySand`: stones and sand with real relief; the sea of 519 has a shallow band and ripples.
- `layer_DungeonFlagstone`, `layer_CaveFloor`: convincing floors. The cave rooms themselves end at plain grey box walls (not ground; `cave_wall` fails).
- `layer_Snow`, `known_doubt` (153), `layer_SnowTrampled`: snow is white in sun (80, 149) and grey-beige "rippled sand" under the dark sky of 120 and 153; the ice screens are grey trampled mud. Both fail.
- `tile_class_cliff_face`, `tile_class_rock_mass`, `tile_class_chasm`, `tile_class_forest_canopy`, `tile_class_structure_facade`, `tile_class_void`, `tile_class_cave_wall`: things the 1997 tiles paint standing up (cliffs, rock, forest, building fronts, cave walls) or dropping away (chasms) are drawn as a flat texture on the ground. All fail; they are the bulk of the 397.
- `layer_PlankFloor`: the floor shows wood grain metres wide, not boards. Fails; the plank scale is with the photoreal-pass session's interior work.
- `layer_LavaCrust`: a bright line pattern on flat black, visibly repeating from above. Fails. The grass inside that dungeon (86) is a flat lawn photograph. Fails.

Seen in passing, not ground: pixelated sprite cards still in these views (castle walls on 16, 48, 80, the king on 70, thorn hedges on 91, 191, 223, the duck and boulder cards on 536, the fountain's blocky water on 586).

## Why 397 stay placeholder

    Screen grounds: 5 final by screen-dressing, 242 final by reviewed terrain layers, 397 placeholder
       173 screens: tile class cliff_face (outdoor)
        76 screens: tile class rock_mass (outdoor)
        76 screens: tile class forest_canopy (outdoor)
        49 screens: layer RockyGrass is not drawn, the mask carries 3 layers
        37 screens: layer CliffRock is not drawn, the mask carries 3 layers
        35 screens: tile class void (indoor)
        34 screens: tile class chasm (outdoor)
        31 screens: tile class wood_floor (indoor)
        29 screens: tile class structure_facade (outdoor)
        23 screens: tile class snow (outdoor)
        21 screens: tile class ice (outdoor)
        16 screens: tile class cave_wall (indoor)
        13 screens: layer EarthPath is not drawn, the mask carries 3 layers
        10 screens: layer WetSand is not drawn, the mask carries 3 layers
         6 screens: water tiles without a water surface
         6 screens: layer DrySand is not drawn, the mask carries 3 layers
         6 screens: layer ForestFloor is not drawn, the mask carries 3 layers
         5 screens: layer MeadowTurf is not drawn, the mask carries 3 layers
         5 screens: layer DungeonMasonry is not drawn, the mask carries 3 layers
         3 screens: tile class grass (indoor)
         3 screens: layer ShingleBeach is not drawn, the mask carries 3 layers
         2 screens: layer SnowTrampled is not drawn, the mask carries 3 layers
         2 screens: tile class lava (indoor)
         2 screens: tile class void (outdoor)
         2 screens: tile class dirt (outdoor)
         1 screens: tile class cliff_face (indoor)

A screen can have several reasons. The ground-fixes work (fourth mask layer, forest on canopy tiles, yards behind house fronts, water surfaces, relief rock) addresses most of them and is reviewed again in its own PR.

## Not checked

- 28 of the 82 chosen screens (above); every final screen that was not itself captured.
- Night, rain or other lighting than each region's default.
- Performance.
- `Dink.Art` and the other editor suites: see the PR text for what ran.
