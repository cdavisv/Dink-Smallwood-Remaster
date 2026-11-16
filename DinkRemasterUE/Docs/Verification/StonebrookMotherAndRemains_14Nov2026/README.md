# The mother and the burn holes of the starting house, Milder and the dead Dink (14 Nov 2026, look pass 15/16 Nov 2026)

Owner's rule: the remaster keeps all 1997 gore; blood and remains show at least what the 1997 picture shows. Every game frame
here is a screenshot of the running game (`Scripts/PhotorealQA/run_capture.sh`, private copy, 16 Nov 2026 04:30), with the
1997 picture beside it and the 14 Nov version of the same asset for comparison. The private copy ran master `6ef7a590` data
with editor binaries built from `ec86f1e6` plus PR #147 (nothing in this change is code). Visions were set with `dink.Vision`.

## What is bound

| Origin | 1997 picture | How | Mesh |
|---|---|---|---|
| `S001_P34` mother's body (vision 1, `s1-h1-s.c:3-6`: `&story == 3`) | 355 | `replacements` row in `Content/Dink/Data/Art/stonebrook.json` | `SM_Corpse_Mother_PR` |
| `S001_P44`, `P45`, `P46` burn holes (vision 2, `s1-h1-s.c:30/41`: `&story > 3`) | 158 frame 1 | `replacements` rows | `SM_Burn_Hole_A_PR`, `_B_PR` |
| `S001_P47`, `P48`, `P49` burn holes (vision 2) | 158 frame 3 | `replacements` rows | `SM_Burn_Hole_C_PR` |
| `S086_P01` Milder dead (script `s7-mil`) | 405 | `families.json` row `corpse_soldier` (`scripted`) | `SM_Corpse_Soldier_PR` |
| `S058_P06` the body that "sort of looks like me" (script `s7-dink`) | 436 frame 16 | `families.json` row `dink_dead` (`scripted`) | `SM_Dink_Dead_PR` |

Screen 1 is dressed by its own manifest (`hide_screen_visuals`), where family rows and the ground decals of `environment.json`
draw nothing; a replacement only swaps the placement actor's card mesh, so the original vision rule (`dink.cpp:6031`) still
decides when they show. `Scripts/art_coverage.py`: placeholder placements 1167 -> 1158 (these nine).

## The colour decision (15 Nov look pass)

The 14 Nov bodies and pools were kept dark because bright red had read as paint on sunlit dry earth. Beside picture 355 in the
room that was too dark: the mother read as a charred shape in a near-black pool. Now (`tools/build_gore.py`: `vivid`, `pool_rgb`)
the blood on the mother and Milder runs from deep to a saturated red, the mother's charring is reduced to patches, and the pools
of the mother, Milder and the dead Dink are a bright wet red with a dark middle. Judged in the game frames: the mother's pool
now has the red of 355 and her body is dark red from head to foot; Milder's pool is readable as red at the game's own (dark)
exposure on screen 86, where the 14 Nov pool was black.

## Sheets and what I see in them

- `mother_screen1.jpg`: 1997 picture, the card, the 14 Nov body, the new body at the play camera, close and from above. A
  body lying where the card lay, opened chest and belly, in a bright red pool with thrown drops; blood on the ground 1.79 m2
  against 0.69 m2 of red in the picture, 2.15 m wide against a 1.70 m card. Last frame: the room at vision 2 as played.
- `burn_holes_screen1.jpg`: the holes are now burnt through (`gore_sheets.scorch_sheet(through=True)`): a dark void, the far
  wall of the planks painted under the north rim, a raised charred rim. They read as holes from the close and top cameras.
- `soldier_dink.jpg`: Milder at the game's exposure and at +3; the dead Dink with the knees drawn up as frame 16
  (`knees=` in his recipe), pool 3.09 m2 against 0.74 m2.
- `picture_decals_sheet.jpg`: the decal atlases of `Corpses/Decals` drawn from the 1997 pictures (187 / 188 / 189, 158), now a
  bright spray with fine drops and burnt-through burns. This is the texture, NOT the game: they are imported
  (`MI_Decal_Blood1997A/B_0..3`, `MI_Decal_Burn1997_0..3`) and not yet bound.

## What still looks wrong

- Every pool has a pale grey outline on the plank floor and on dry earth (the "soaked fringe" colour of the sheet is damp
  earth): on wood it reads as a light rim round the blood. Not fixed here.
- The mother's body itself is darker than the bright red of 355 (the pool carries the red); her face cannot be read at the play
  camera. The fire around her is still the 1997 pixel flames.
- Burn holes: in direct sun the void is dark grey-brown with a sheen, not the flat black of 1997; the depth is painted for the
  play camera, so from the side it is flat. `S001_P45` lies half under the wall.
- Dead Dink: the hips lift a little with the knees; the pool lies partly beside the body and has gaps.
- The room at vision 2 shows nothing else of the fire, as 1997.

## Not checked

- `S001_P49` could again not be brought into view (the cameras end up inside the wall): bound by the same row as `P47`/`P48`, not seen.
- The play-camera frames of the burn holes look into walls or the roof on this interior; only close and top views are usable.
- The fire sequence as played (before, burning, after) was NOT captured: my frames for story 1 and 3 came out outdoors.
- `Dink.Art` and the gameplay probe on this state: see the PR text.
- The original shrinks the dead Dink away after `talk` (brain 12): not exercised with the mesh.
