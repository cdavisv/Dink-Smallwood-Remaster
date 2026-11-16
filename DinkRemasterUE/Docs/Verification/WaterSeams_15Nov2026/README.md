# Water seams: sea colour and shore depth run on across screen borders (15 November 2026)

Follow-up of PR #135 (water colour from sea to pond). Visual only: the world export's `collision.json`, `placements.json`
and `warps.json` are byte-identical before and after (md5 `4621771a435c`, `2a59cd90fa3d`, `4659aa549a18`).

## What was wrong

- The sea weight was one number per screen. The nine half-weight river screens (314, 315, 412, 427, 442, 443, 477, 635,
  661) took a linear blend of the pond and sea coefficients. The pond's scattering is up to seven times the sea's, so half
  still read close to pond-olive, and each of them kept a straight step at its screen edges (634|635, 603|635).
- Each screen's shore distance (the terrain mask alpha, which gives the water its depth and the bank its wetness) was
  measured against that screen's own water only. Where a pond or river crossed a border, one side saw a bank the other did
  not, so the depth stepped along the border (465|464, 244|276, and 99 wet borders map-wide).

## Change

- Sea weight at nine points per water screen (`water_sea_patch` = corners, edge middles, centre; `water_sea_patches` in
  `Scripts/export_import_bundle.py`). The middle of an edge to a joined screen holds the mean of the two weights, a corner
  the mean of the joined screens round it, so two joined screens hold the same values along their whole shared edge.
  `M_Env_WaterShore` blends the nine smoothly by the screen UV (scalar parameters `SeaNW` .. `SeaSE`) and goes from pond
  (`Absorption`, `Scattering`, `ScumAmount`) to sea (`SeaAbsorption`, `SeaScattering`, no scum) geometrically. The
  importer writes the nine into `MI_Water_SCR_*` (hash `water-mi/6`); the runtime water sheets read them from
  `ground_classes.json`. An older bundle or world without the patch gets one weight everywhere, as before.
- Shore distance across borders (`shore_alpha`): measured on the screen's 64 x 96 water grid with 12 texels of the
  neighbours' grids round it. Only neighbours that lie against the screen in the world layout count (`world_neighbours`:
  they share the corners in tools/analyse's layout; indoor and moved screens do not). The texels hold the distance at
  points spread from edge to edge (texel 0 on x = 0, texel 95 on x = 600), so both screens hold the same value on their
  border.
- Measured on the exported masks: wet borders with an alpha step above 0.15 went from 99 to 0. Two borders keep 0.05
  (298|299 and 117|149, where the diagonal screen of a corner is not in the layout). Between screens whose water joins,
  the nine sea weights agree on every shared edge (all 210 water screens checked, including the 9 half screens and their
  neighbours).

## Sheets (running game, offscreen Vulkan; master frames are PR #135's own captures on the build that became master e803790d, same cameras)

- `635_634_half_weight_before_after.jpg`: 635 from above and at the play camera. Master: a straight diagonal colour seam
  against 634 (left, blue-green against olive) and a straight horizontal one against 603 (top). This branch: one body of
  water whose colour runs from the estuary's blue-green to the pond's olive with no line anywhere.
- `465_244_pond_rims_before_after.jpg`: 465 against 464 (west) at the play camera and from above; 244 against 276
  (south). Master: a darker, deeper-looking block on the far side of each border with a straight shade edge. This branch:
  the depth is the same on both sides. Still there: a thin pale line exactly on the border (465|464 diagonal in the play
  frame, 244|276 horizontal from above). That is ground between the end of one screen's water surface and the next
  screen's (the collision's water fill stops a few pixels short of the edge), not colour or depth; the natural-shoreline
  PR (fix/water-shapes) lays the water surface over the drawn shape and closes it.
- `coast_seams_before_after.jpg`: 633, 666, 576 and 720 from above. Master: straight cuts where sand or wet bank meets
  the next screen's water (633's sheet corner, the diagonal at 666's sand spit, the square sand patch at 576's corner).
  This branch: the wet bank follows the water across the border.
- `after_only_seams.jpg`: this branch only, at cameras master has no frame for: 634|635 from above and at the play camera,
  244|276 from the south side, 575|576, and the half-weight screens 427, 477 and 661 from above. No straight colour step
  is visible; at 427 the blue channel of 426 meets the olive body behind a tree.

## Checks

- `python3 -m unittest discover -s Scripts/tests`: see the PR description for the count. New tests in
  `test_ground_export_helpers.py`: the nine weights agree along every joined edge and fall back to the screen's own
  weight toward water it does not join; the capped shore distance equals the exact one; neighbours must lie against the
  screen in the world; a pond across a border has one depth on both sides.
- Build (0 warnings), material rebuild, world regenerated (`import_greybox.sh --region all --export`, then
  `--region stonebrook`), captures above, `Dink.Art+Dink.Import+Dink.Gameplay.Probe` (result in the PR description).

## Not checked

- The packaged build.
- The camera at 697 (the 665|697 coast seam) did not move there (the frame repeated 576), so that seam was not captured.
- Screens with filled water but no terrain mask use the shared `MI_DinkWater` (none on the current world).
