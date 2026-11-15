# Water banks: a shoreline instead of a rectangle (14 November 2026)

Seven screens have water tiles but no water fill in the collision (a ford or pond the player can stand in, or water that hardness outlines close): 244, 385, 438, 465, 494, 633, 736. The ground-fixes PR laid a water sheet over the tile rectangles; it ended on straight tile edges with no bank.

Change, visual only (the export's `collision.json`, `placements.json`, `warps.json` are byte-identical, md5 4621771a435c):

- World export: `natural_water_shape()` rounds the water tiles off and bends their outline with low-frequency noise (the middle of the tiles always stays water, so a river is never cut; within 40 px of the screen's rim the tile outline holds so water meets the next screen). Its signed distance goes into the terrain mask's alpha, exactly as for water that has a fill: the ground darkens wet toward the waterline, and the grass carpet stays out of the water.
- Runtime: one sheet per screen with the shore material `M_Env_WaterShore` reading that mask: clear at the bank, deeper away from it, nothing on land. Screens that are a sea shore or touch one (`ground_classes.json` `water_sea`) take the sea's colours instead of silty pond water.

## What I saw (running game)

- `465_dry_bed_rectangle_river.jpg`: screen 465 at the play camera. Left: master before the ground fixes (a dry sand bed). Middle: the first sheet (a straight-edged slab). Right: now, a silty river with a sand bank on the near side, reflections of the willows, the hero on the bank. Reads as a river.
- `465_above_494_pond.jpg`: 465 from above (banks wander, the river keeps its width) and the pond of 494 at the play camera and from above: a small pond with a muddy rim.
- `385_736_sea_shore.jpg`: the sea behind the harbour wall of 385 (foam line on the sand, blue-green water) and the shore of 736.
- `633_244_rim_defect.jpg`: **what is not right.** Where the drawn water reaches the screen's rim it keeps the tile outline, so 633 (left) and 244 (middle; right is the earlier rectangle for comparison) end in straight steps at their southern edge, and on 633 and at the west end of 465 the sheet meets the next screen's water on a visible colour seam (olive pond water against the sea's blue-green, or deeper olive).

- `recapture_on_master_adf5b1dc.jpg`: the same screens captured again from the running game after the rebase onto master `adf5b1dc` (PRs #117 to #124 merged in between). Upper row: 465 at the play camera (river, bank, hero), the harbour wall and sea of 385 from above, 465 from above, 633 from above (the rim defect: the olive sheet ends on a straight step against the blue-green sea). Lower row: the pond of 494 from above, the sea shore of 736 from above, the Stonebrook fields 471 and 438 at the play camera. Nothing changed against the sheets above. (The frames of this run were written one shot late under machine load, so the panels are described by what they show, not by their file names.)

## Bug list A16: single-layer water on Nanite meshes

The stream and pond sheets of the Stonebrook fields (`SM_Fields_471_Water_*`, `SM_Fields_438_Water_*`) are Nanite meshes and take `M_Env_Water` (single-layer water) through the environment material table in `DinkArtSubsystem.cpp`. The component was already marked `bDisallowNanite`, but AFTER `SetMaterial`, and `SetMaterial` audits the component's Nanite materials at once (PSO precache), so every sheet logged "Invalid material [M_Env_Water] used on Nanite static mesh" (170 lines per mesh in the alpha QA soak log). The flag is now set before the material. Game log of the capture run above (it enters 471 and 438): 0 such lines.

Not looked at: screen 438 (dressed by an art manifest: its pond is authored art and this layer skips the screen). 385 and 736 were not seen with the hero at the waterline (385's water lies behind the wall).

Verdict: the condition `water_without_surface` stays **failed** in `ground_review.json` for the rim defect; the audit counts do not move. 465, 494, 385 and 736 would pass on their own.

Next step for the rim: shape the water across screen borders (one mask for the neighbouring screens together) and take the neighbour's water colour.
