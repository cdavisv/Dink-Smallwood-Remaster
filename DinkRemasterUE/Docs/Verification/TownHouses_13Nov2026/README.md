# Town houses in the gate 2 audit (13 November 2026)

What this folder proves: which of the 218 placements of the town-house kit (sprite family 33) show an assembled
photoreal house in the game instead of their sprite card, and which do not.

## Result

| | before | after |
|---|---:|---:|
| `art_coverage.py` final | 3,972 | 4,093 |
| placeholder | 2,483 | 2,362 |
| cut | 152 | 152 |
| family 33 placements final | 0 of 218 | 121 of 218 |

- **Final (121):** all 80 window walls, all 15 door walls, all 21 gable ends, and 5 roof cards that lay right behind a house.
- **Still placeholder (97):** 52 flat roof sections, 16 dormers, 15 roof slopes and 14 ridge caps. Their cards are hidden
  and the houses carry complete roofs, so from the street nothing is missing. They are not counted because nothing
  stands where those pictures were: the 1997 buildings are 45 to 70 m deep in the stretched town layout, the
  assembled houses 8 to 15 m, and the ground behind the houses is open (see "What is left").
- The ledger `doc/remaster/ALPHA_GATE2_BACKLOG.md` is regenerated: 152 -> 149 open families, 2,438 -> 2,317 open origin
  IDs, 1,786 -> 1,665 open placements.

## The rule (`Scripts/art_coverage.py`, `town_house_cards()`)

A family 33 card is final when, and only when:
1. its own screen's entry in `Content/Dink/Data/Art/town_houses.json` hides it (the game hides cards per screen);
2. the file names an assembled house for it (`stands_for`: a wall card names the house built from its own wall run, a
   roof, dormer, ridge or gable card the nearest house of its 1997 building) and that house has modules;
3. every kit mesh of that house exists in the project;
4. a house body covers ground the card's picture covered: some part of the picture (for a wall, its ground line) lay
   over a house body or within one kit bay (2.5 m) of it;
5. the house is not listed as failed in the in-game review (`REVIEW` in `Scripts/assemble_town_houses.py`; empty today).

The game reads the same file (`UDinkEnvironmentSubsystem::LoadTownHouses`, `ApplyTownHouses`, switch `dink.TownHouses`).
Unit test: `Scripts/tests/test_town_house_coverage.py`.

## What was run and looked at

| File | What it is |
|---|---|
| `sheets/town_<screen>.jpg` (36) | Per town screen: left the sprite cards (`dink.TownHouses 0`), right the assembled houses, at the play camera, from above the south edge and from above the north edge. Real game, offscreen, 1280 x 720. |
| `close/<screen>_close_<k>.jpg`, `<screen>_roof_<k>.jpg` | Street-level view 7 m in front of a house front, and its roof from just above, for the nine house fronts of screens 219, 418, 498, 506 and 585. |
| `roof_corners.jpg` | Crops of four roof junctions (570, 498, 585, 419) from the south views. |
| `town_house_placements.csv` | One row per placement: class, card or instance, hidden or not, the house and building that stand for it, covered or how far the nearest house body is, audit state. |
| `town_log_check.txt` | The game's own log of the houses-on run against the file: 36 screens, 2,563 modules placed, 0 of unknown mesh, 218 cards hidden. |
| `town_walk_check.txt` | Offline check that no house body can be walked into from the street in front of it. |

Commands are in `SourceAssets/Art/PhotorealPass/IMPORT.md`, section "Town houses in the audit".

The sprite-card run logged no `town houses on screen` line (no screen was dressed), the houses-on run 36.

## What I see

Every one of the 36 sheets was looked at (all 216 captures), plus the 18 close views.

**Against the sprite cards.** A wall card at the play camera is one blurred picture about 10 m wide; roof cards stand
upright behind it like fans; from above they are flat boards with gaps and the sky between them. The assembled rows
have a stone ground floor with quoins, leaded windows, studded doors with a lantern, a jettied timber storey on joist
ends, shingle roofs with ridge caps, chimneys and the odd dormer; house height, depth and setback change along a row.
On every screen that has wall cards the houses are better than the cards, at the play camera and from above. At 7 m
(`close/`) the stone courses, timbers and shingles are modelled, not painted flat; I saw no faceted or blocky module.

**No assembly fault that breaks a house:** no floating or missing roof, no gap in a wall row, no flicker of two
surfaces in one plane at these distances, doors in the bays where the door cards stood, backs complete (walls and
roofs) where a camera gets behind a row.

**Defects, not fixed here:**
1. **Roof junctions where two rows meet** (`roof_corners.jpg`; 11 convex corners and 1 concave: 219, 251, 417, 419,
   498, 505, 537, 538, 570, 585, 587 and 418). Each row keeps its own gable verge, which pokes through the other
   row's roof as a saw-tooth seam with dark gaps beside it; on 498 the corner is open enough to see into. Seen from
   above and from behind; from the street it shows as a jagged hip line against the sky (537, 251). The kit has 13
   meshes and none is a hip or valley piece: closing these needs two new roof modules, not a data change.
2. **The yard behind every row** is wall masonry laid flat (a yellow floor of giant blocks). Screen ground, see below.
3. **Screens with roof cards only** (186, 187, 385, 386, 467, 472, 473, 474, 507, 553, 554, 555): with the houses on,
   nothing stands on the screen where the cards were; the roofs are on the houses of the neighbouring screen. Right
   for the street, and the reason those cards stay placeholder.
4. The "roof and back" close views sit just above the shingles (the camera position was set for a lower house), so
   they show the roof surface and its module seams, not the back wall. The backs are in the north views of the sheets.

**Per screen** (houses on the right of each sheet):

| Screen | Building | Cards final / placeholder | Play camera shows | What I see |
|---:|---|---|---|---|
| 186 | B1 | 0 / 2 | roof cards only | Cards: two shingle pictures standing upright, pixelated at the play camera. Houses: nothing on this screen (the house is on 218, its roof and gable show at the screen edge). Ground where the cards stood: bare soil. |
| 187 | B1 | 1 / 5 | behind the row | Cards: a roof picture across the frame. Houses: the back of the row of 219 beyond the grass; nothing stands on this screen. |
| 218 | B1 | 4 / 2 | front | Row of three houses on grass: stone ground floor with quoins, leaded windows, jettied timber storey, shingle roof. Cards: a blurred wall picture and a checkered card edge. |
| 219 | B1 | 6 / 3 | front | Door bay with a studded door and lantern, windows either side; the door stands where the door card stood. Cards: one blurred picture across the whole frame. From the north the backs are complete. |
| 251 | B1 | 2 / 0 | front, corner | Corner block with dormers and chimneys reads as one building. The hip where the two rows meet is jagged (see defects). A thatched hut card of another family stands pixelated in the foreground of the south view. |
| 385 | B2 | 1 / 5 | yard behind the row | Cards: roof pictures standing upright in the walled yard. Houses: the play camera stands in the yard and sees the backs of the row of 417 (complete back walls and roofs); nothing stands on this screen itself. |
| 386 | B2 | 0 / 7 | roof cards only | Cards: five shingle pictures standing upright across the square. Houses: nothing on this screen; the rows of 418 and 419 close the view from the north. The ground where the cards stood is the masonry yard (see defects). |
| 387 | B2 | 1 / 7 | yard behind the row | From the yard: the backs of the houses of 418 and 419 in one long row, roofs stepping in height. Cards: two shingle pictures filling the frame. The two houses on this screen's south edge are part of that row. |
| 388 | B2 | 3 / 4 | gable end | The east end of the row: timber-framed gable wall between stone quoins, seen from beside it. Cards: one blurred wall picture. From the north the row and its roofs are complete. |
| 417 | B2 | 6 / 2 | front | Row along the castle wall on setts; windows, plain bays with tie plates, two roof heights. Cards: blurred wall pictures with a gap between them. |
| 418 | B2 | 8 / 3 | front, concave corner | Two rows meet in a concave corner around the square, door on the left, barrels in front. The valley between the two roofs is closed. Cards: wall pictures tilted against each other, roof pictures standing behind. |
| 419 | B2 | 7 / 2 | front, corner | Row with a gable end toward the camera and two barrels; the convex corner at the west has the jagged hip. |
| 420 | B2 | 4 / 0 | front | Row of five against the east castle wall; roofs step in height. Cards: three blurred pictures. |
| 465 | B3 | 3 / 4 | gable end and back | West end of the row from the river bank: gable wall, and the back wall with windows running away. Cards: two pictures floating above the grass. |
| 466 | B3 | 3 / 7 | backs across the pond | The whole row from behind, across the pond (the capture stands on the water: the pond has hardness 0 inside its outline). Cards: roof pictures standing in the water. |
| 467 | B3 | 1 / 3 | roof cards only | Cards: a shingle picture filling the left half of the frame. Houses: nothing on this screen; the roofs of 499 show at the south edge. |
| 472 | B4 | 1 / 3 | roof cards only | Cards: a wall picture and a roof picture at the pond. Houses: nothing on this screen (pond, fences, trees). |
| 473 | B4 | 0 / 6 | roof cards only | Cards: two shingle pictures filling the frame. Houses: the backs of the row of 505 across the water; nothing stands on this screen. |
| 474 | B4 | 2 / 4 | roof cards only | Cards: a shingle picture standing beside the willow. Houses: nothing here; the row of 506 shows across the river from above. |
| 497 | B3 | 4 / 0 | front | Row of five with a door and a barrel, seen along its length. Cards: two blurred pictures. A thatched hut and a well of other families stay as cards. |
| 498 | B3 | 7 / 2 | front, corner | Long row seen along the street; doors and windows line up bay by bay. From above the corner where the two rows meet is open (see defects). |
| 499 | B3 | 4 / 0 | front | End of the row with door and windows, willow behind. Cards: two blurred pictures with a gap. |
| 504 | B4 | 3 / 0 | front | Row of three on bare earth; the wide door at the right is the door card's bay. Shop sign brackets of another family stay as cards. |
| 505 | B4 | 6 / 4 | front | Along the front of the row: plain bays with tie plates, quoins, jetty, the far houses stepping down. Cards: a blurred wall picture and a gable slice. The chair is another family's prop. |
| 506 | B4 | 8 / 4 | front, close | Close to the wall: stone courses, quoins, a leaded window and the jetty read at arm's length; barrels and a crate in front. Cards: three pictures at different angles. |
| 507 | B4 | 1 / 2 | roof cards only | Cards: a shingle picture across the left of the frame. Houses: nothing on this screen (pond and meadow). |
| 537 | B4 | 3 / 0 | front, corner | Convex corner toward the camera, two rows running away; the hip at the corner is jagged against the sky (see defects). A thatched hut card stays. |
| 538 | B4 | 9 / 2 | front | Door bay head on: studded door in a stone surround with a lantern, leaded windows, jetty above. Cards: one blurred picture and a slice. From above, the corner of the two rows is jagged (see defects). |
| 539 | B4 | 3 / 0 | front | House end at the pond: door, windows, barrel. Cards: one door picture and a narrow gable slice. |
| 553 | B5 | 2 / 6 | yard behind the row | Cards: roof pictures standing in the square. Houses: the backs of the row of 585 across bare earth; nothing stands on this screen. |
| 554 | B5/B6 | 2 / 4 | roof cards only | Cards: two shingle slices at the frame edges. Houses: nothing here (bare square); from the north the rows of 585 and 586 show. |
| 555 | B6 | 1 / 4 | roof cards only | Cards: a roof picture and a wall slice. Houses: nothing on this screen in the play frame; from the north the row of 587 shows. |
| 570 | B4 | 2 / 0 | two houses at the north edge | The play camera looks over the yard where the roof cards stood; the two houses of this screen are seen in the south and north views (V-shaped pair, jagged hip). Cards: two roof pictures standing in the frame. |
| 585 | B5 | 5 / 0 | front, corner | Corner block with three doors on bare earth. Cards: one blurred picture across the frame. A duck card (creature) in the foreground. |
| 586 | B5/B6 | 4 / 0 | fronts at both edges | Square with the fountain; house ends at the left and right edges. Cards: none in the play frame. The fountain is a grey faceted bowl with blocky blue water (another family). |
| 587 | B6 | 4 / 0 | front | Row with door and windows behind the signpost. Cards: two blurred pictures. |

## Houses and the player

The kit houses have no collision of their own; the player is stopped by the 1997 hardness, as before. The ground
behind a wall line (the inside of a 1997 building) has hardness 0, so a house body that stands there is only right
when that ground cannot be reached.

- `Scripts/PhotorealQA/town_walk_check.py` (collision export, 30 cm capsule): for each of the 38 house rows (wall
  runs, cut into 118 houses) the walkable ground 3 m in front of its wall is taken as its street; no house core lies
  in its street (largest overlap 0.4 m2, wall thickness at a corner). A door's warp takes the player away, so a door
  is not a way in.
- Five of the first play-camera captures (screens 388, 465, 466, 505, 538) were taken from inside a house: the capture
  script teleported the player to the nearest point with hardness 0, which was enclosed ground behind the wall line.
  `town_script.py` now stands on the street side; those screens and seven others whose stand point moved were shot again
  with and without the houses. On screens whose houses face the next screen the stand point is beside or behind the
  row (388, 465), in the yard (385, 387, 553) or on a pond (466, 472, 473: the water has hardness 0 inside its outline
  and a capture can be put there; a player cannot walk there).
- Not checked: a walk in the running game against the house fronts, and whether the walled yard behind the castle-town
  row (screens 385 to 388, about 11,000 m2 of walkable ground in one piece) can be reached some other way. The west end
  of house row `S417_B2` stands past the end of the 1997 wall line, on the yard side.

## What is left, and what would close it

1. **97 roof cards.** A house body that reaches back over the ground the roof pictures covered turns them final
   without touching the audit: the file's `uncovered_m` shrinks as bodies grow. That means building the six 1997
   buildings as blocks 45 to 70 m deep (courtyard blocks, or rows back to back) instead of single rows on the front
   line. It is a design job, not a data fix: the blocks must not hide the player from the play camera, and the roofs
   of 55 m wide blocks need valleys the kit does not have yet.
2. **The yard behind the houses.** The tiles under the old roof pictures (`structure_facade`) are drawn as wall masonry
   laid flat: a yellow floor of giant blocks behind every row, seen from above and from the far side, not from the
   street. This is the screen ground, handled in the screen-ground work (tiles behind house fronts take the
   surrounding ground layer).
3. Seen in passing, not family 33 (reported to the coordinator): the fountain on 586 is a grey faceted bowl with blocky blue water; thatched hut cards on 251, 497 and 537, shop sign brackets on 498 and 504 and a well on 497 are still pixelated sprite cards; a duck card on 585.

## Not checked

- No automation test can see the houses: the environment layer does not run headless. The runtime evidence is the
  game log of a rendered run (`town_log_check.txt`).
- Door positions against their warps were judged by eye in the close views only, not measured.
- The captures are of a world generated on 12 November; the houses come from `town_houses.json`, which this change
  regenerates with the same houses, modules and hide lists (only the accounting is new).
