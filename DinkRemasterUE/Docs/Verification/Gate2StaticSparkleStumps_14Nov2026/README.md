# Gold twinkle and stumps (14 November 2026)

Two follow-ups from the review of static batch 1 (PR #105). Visual only: collision, hardness, scripts and origin IDs
are untouched.

Sheets are from the running game (private project copy, offscreen, 1280 x 720). "before" is static batch 1 as merged,
"after" is this change.

| Sheet | Shows | Seen |
|---|---|---|
| `gold_twinkle_before_after.jpg` | the gold heaps of screen 352 from the play camera and close; gold and a heart dropped by `make.c` | Before: heaps and nothing above them (batch 1 hid the grey marker of the twinkle sprite). After: warm four-point glints twinkle in the air over each heap, as the 1997 game shows a sparkle on gold. The dropped gold and heart are small in the grass in both. |
| `stumps_before_after.jpg` | both stump meshes alone on bare ground, and the stump of screen 179 from the play camera and close | Before: the roots are flat, straight wedges that are part of the trunk surface. After: five or six separate thick roots leave the trunk at a shoulder, run half buried over the soil, taper and dive under it; some fork. In the grass of screen 179 the long roots show from the play camera. |

## What is not right yet

- The roots cross the trunk surface without a welded seam and wear the trunk's bark wrapped round them; close up the
  join is a crease.
- The twinkle is sixteen glints at fixed places in a 70 cm square, drawn flat towards the camera; it is not tied to
  the heap's shape or to a light.
- The two placed sparkles of the map (S001_P37, S045_P01) keep their cards: effect rows are used for sprites that
  scripts create.
- Dropped pickups are still small in tall grass. The grass clearings are gathered when a grass cell is built, so a
  pickup dropped later would need the cell rebuilt; that belongs to the grass builder and is not done here.

## Tests

See the pull request text.

## Not checked

- The 46 stump placements other than S179_P05.
- Gold dropped by a killed enemy in play (the sheet uses `make.c`, which runs the same gold scripts).
- A packaged build.
