# Structure sets: cottages, the two-storey house of 440, Goodheart castle, island huts, bridges, wells, fence runs, the bone pole (15 and 16 November 2026)

Queue rows VS-01, VS-02 (Goodheart), VS-05, the bridges and wells of VS-14, and DS-03. Presentation only: hardness, warps,
scripts and origin IDs are untouched; a hidden card keeps its actor, its hardbox and its script.

Every frame is from the running game (offscreen `run_capture.sh`, the framing of `Scripts/PhotorealQA/visual_sweep.py` plus
one play shot in front of each cottage door), build = master `3a7b4451` + this branch, 16 November. Each sheet row is one
screen: the 1997 screen composed from the original graphics, the play camera on master (visual sweep of 15 Nov), the play
camera after, and a camera over the screen after. 56 screens carry a set (57 before master hid the two rails of 375); 66 were captured (170 frames) and every one was
looked at; three shorter captures followed the fixes (see "Not checked" for their bases), 229 frames in all.

| Sheet | Screens | What I see |
|---|---|---|
| `house_440.jpg` | 440, 500, 618 | The 31 m card is gone. The Stonebrook440 kit house stands on the closed ground of the 1997 outline: drystone rubble walls, two tiers of thick rounded thatch with a rolled eave, a double oak door with ring handles on the warp trigger, Dink a head lower than the lintel, two barrels as in 1997. It reads as the 1997 house. Trough, woodpile, chopping block, wheelbarrow and hay bales stand on the ground in the yard. Rows 1 and 2 are the second capture (thatch tinted to the 1997 golden straw); row 3 left is the first capture with the kit's own pale thatch, then the mirrored house of 500 at its door and the house of 618 from above. See "Still wrong" for the two fence styles. |
| `castle_gate_402.jpg` | 402, 433, 368, 401, 400 | Third capture, after the wall ends were closed. The gatehouse where the castle door's warp is, with one of the 1997 guard cards beside it (the guards are another change); the joints of 433; the wall of 368 with its ribs; the castle from the courtyard of 401; 400 from above. |
| `cottages_1..4.jpg` | 274, 350, 497, 501, 530, 532, 537, 734, 318, 409, 617, 619 | Stone cottages with thatch, shuttered windows, plank doors and chimneys in fenced yards instead of 25 to 31 m cards. 350 and 734 are the L-shaped house of their pictures; 501 reads as a hamlet of three. On 409, 617 and 619 the sweep's standing point lies inside the closed ground of the house and the play frame shows a wall from the inside or from a metre away: that point cannot be walked to; the camera over the screen shows the house. |
| `castle_1..3.jpg` | 368, 369, 370, 400, 401, 433, 432, 336, 367 | A crenellated ashlar curtain wall with round towers along the 1997 hardness outline instead of 46 to 50 m cards; from the courtyard of 401 it is a castle. The gatehouse of 402 is an arched recess with a torch bracket where the door's warp is. |
| `island_1..3.jpg` | 680, 712, 762, 763, 764, 748, 100, 713, 716 | Round and two-tier daub huts with domed palm thatch, painted bands and tusk door posts, in lashed-fence pens; lattice fences; the bone pole where the pixel poles stood. The huts are the best match to their pictures in this change. |
| `bridges_wells_1..3.jpg` | 404, 512, 693, 416, 448, 544, 408, 600, 766 | Plank decks with rope and board rails over the walkway of the hardness; stone wells, the roofed one with its windlass on 600 and 766. |
| `repeated_houses_501_764.jpg` | 501, 764 | What the walk audit found and its fix. Top: the first capture, where the cottages of 501 and a hut of 764 stand twice (the copy 9 m beside the house), and Dink, sent to the lane between the yards, stands inside the second cottage. Bottom: after the fix, three cottages in three yards, the lane open, one hut per pen. The sheets above show the fixed state for these screens. |
| `torch_pole_blender.jpg` | - | The rebuilt `SM_Island_TorchPole_PR` beside 424 frame 18 / 425 frame 1 (Blender render) and cropped from the game (screens 762 and 100). |

## Decisions taken by eye

- **DS-03**: the Stonebrook440 kit house (`SM_House_Stonebrook_TwoStorey_01`: 13.3 x 10.8 m, 11.6 m to the ridge) is used
  for every `cottage_thatched_two_storey` (440, 500 mirrored, 586/618) instead of `SM_Cottage_Thatched_TwoStorey_PR` (8.3 m,
  straight hipped roof). In the game it fills the 1997 outline far better, has the two thatch tiers of the picture and a
  door the size of Dink.
- The kit's thatch is a pale cream in the sun of Stonebrook (first capture of 16 Nov); the 1997 roofs are golden straw.
  `import_stonebrook440.sh` now gives `MI_S440_Thatch` a `base_tint` (1.2, 0.92, 0.5): `house_440.jpg` shows both.
- `island_totem_pole` (424 frame 18) and `island_torch` (425 frame 1) are one 1997 picture; the delivered three-tined
  cane pole was not it. The pole was rebuilt after the picture.

## Found and fixed on the way

- The first capture drew the 440 kit with the grey default material: its materials lacked the usage flag for instanced
  meshes (`DINK_ART_INSTANCED_USAGE=1` in `import_stonebrook440.sh`; `test_photoreal_material_references.py` failed on it
  and passes on the re-imported packages).
- `Scripts/import_town_exteriors.sh` exited 1 after a clean import ("DINK TOWN IMPORT OK ... 0 warnings"): its last
  command was a `grep` for warning lines under `pipefail`. Fixed (`|| true`).
- A dark slit stood on each side of the gatehouse of 402: the walls now end inside it (one slit is left, see below).
- The wall module has no end faces: every run now gets a 2.5 m piece of the same wall turned across each end, inside
  the wall's thickness. They read as shallow ribs (buttresses) where two runs meet.
- A castle picture stayed on screen 432 (no wall module fell on that screen, and cards are hidden per screen); a lone
  2.5 m of rail in mid-bridge on 404 read as a shelf; wall joints showed as dark lines on 433 (10 cm overlap).

## Walk audit in the game (`walk_audit.txt`)

`dink.WalkAudit 187 766` over the whole outdoor map, read by the new `Scripts/PhotorealQA/structure_walk_verdict.py`
(a walk-in counts where its deepest standing point lies on ground the player can reach).

- First run: 58 set meshes could be walked into. 50 castle wall modules (up to 1.1 m: a straight run crosses the
  notches of the 1997 outline), the 4 towers (4.6 m), the gatehouse (its doorway: meant), and **a cottage on 501 and a
  hut on 764 that stood a second time on open ground**. Dink was put on the points and looked at from above: he stood
  inside the wall and inside the second cottage.
- Cause of the second houses: the 1997 map repeats a building that crosses a screen edge on both screens, and the
  runtime maps a set's pixel through its own screen's sheared quadrilateral, so a pixel off the screen lands metres
  from the neighbour's ground (9 m for that cottage, which stood in the lane between two yards). `assemble_structures.py`
  now reads an off-screen pixel through the screen it lies on, finds a repeated building by its 1997 spot (15 twins,
  were 10) and rewrites the pixel of every off-screen module (104).
- Castle: player-only blockers for `SM_Castle_Wall_8m` and `SM_Castle_Tower_Round` (`player_blockers.json`, written by
  `make_player_blockers.py --only`; they block the player's capsule and nothing else, as master's blockers do).
- Second run, with both: 2 rows left, the gatehouse doorway and a 32 cm brush past a hut wall on 763.
  `check_player_blockers.py` on the same run: the castle blockers cut nothing off (its 13 lines on 7 screens are
  master's town-house blockers, the same as in `WalkThrough_15Nov2026`).

## Still wrong (seen in these frames)

- **Yards that 1997 does not draw (owner decision of 16 Nov 2026: keep the fences for now).** A real-size cottage or
  hut covers a third of its 1997 hardness, so each stands in a fenced yard along the outline that stops the player
  (otherwise he is stopped 5 to 10 m from the wall by nothing). The owner decided: use the fences for now; the houses may
  be made somewhat larger; the layout stays the 1997 map at an enlarged rate, and what fills the space that scaling
  leaves is decided later (candidate spots go into the art queue, row SP-03; no new scenery in this change). Still seen:
  on the island (762 to 764) the pens of neighbouring huts and the lattice sprites cross and read cluttered; around 440
  the yard's dark lashed rails meet the pale split rails of the 1997 fence.
- **Castle wall**: it follows the simplified hardness outline in straight runs that meet at kinks, and each 8 m module
  shows as a panel (a seam every 8 m, clear in the play frames of 368 and 369). Where two runs were moved in by different
  amounts, the step between them is a narrow recess that stands black in shadow (`castle_gate_402.jpg`: one left of the
  gatehouse of 402, one on 433), although the run ends are closed now. The kit's corner and end pieces are not imported;
  a straight wall along the 1997 picture's line needs player blockers for `SM_Castle_Wall_8m`. Both belong to a castle
  follow-up.
- The generic cottages have straight, pale grey-gold roofs (`MI_Struct_Thatch`, shared with master's other thatch) where
  the 1997 thatch is deep, rounded and golden, and they stand square to the screen where the picture shows the house
  turned 45 degrees.
- The bone pole is 2.6 m (real size); the 1997 card is 5.9 m at the settlement scale, so it reads small on the wide sand
  of 762. Its bone is a cool grey-white, the picture's is ivory. The crystal does not glow.
- The wells without a roof (349, 416) are knee-high rings in a wide field: real size against a 4 m picture.
- Screens 251 (log cabin), 533 (bridge), 693 (the talking oak) and 663 (arrows) still show 1997 cards: not part of this
  change. The hall behind the castle door (the sweep's "402" frame) lies in 1997 wall cards: not part of it either.

## Not checked

- Night, rain and the low scalability levels; the packaged build (the kit folders are inside the default cook dirs of
  `Scripts/package.sh`, not cooked here).
- Walking into every door by hand: the door position is checked offline against the warp trigger, the door shots
  show Dink standing at it, and `check_player_blockers.py` finds no door cut off by this change.
- The first capture (170 frames) was made before the rebase onto master `41e80f73` (that commit adds character
  packages and no code); the second (the 440 house after its tint) and the third (castle) after it; the fourth (the
  screens of the repeated houses: 469, 501, 732, 764, 437, 468, 763, 440) on the final base, master `84e045b0`. In its
  door shot of 469 Dink, put on the door, is inside the house: the door stands on its warp.
