# Ground layers with natural outlines (VS-09), 15 November 2026

Owner direction of 15 Nov 2026: smooth, natural, photoreal landscape; the 1997 50 px tile steps are a technical artefact.
This change covers the LAND ground layers of the terrain mask (grass, rocky grass, dirt, paths, sand, farmland, snow,
rock patches). Water outlines and the mask's alpha (water shapes) and height (landforms) are other streams' work.

## What changed

- World export (`Scripts/export_import_bundle.py`, new `Scripts/ground_layer_fields.py`): every outdoor screen's
  layer weights are rebuilt in world space with its world-adjacent neighbours: blurred (rounded corners, rows of tiles
  joined), thin lines lifted against their own peak, bent by value noise in global map pixels, the winning layer
  allowed to differ from the 1997 tile only within 25 px (half a tile) of a 1997 layer boundary, then feathered.
  Indoor floors keep their tile weights. Mask texels are edge-aligned (texel 0 on the screen's west edge, texel 95 on
  its east edge).
- `M_Env_Terrain` is unchanged: its clamped mask lookup shows the edge texels exactly on the border, and inside a
  screen it reads the edge-aligned texels at most half a texel (3 px) off. Its small mask warp (0.012 UV) still acts up
  to the rim; fading it out there is a material follow-up (not in this PR).
- `export_ground_colour.py` now counts the fourth layer (it stopped with an error on every four-layer screen).

## Numbers

- Export: collision, placements, warps, sprites, samples byte-identical to master (md5 4621771a435c, 2a59cd90fa3d,
  4659aa549a18, 532a8099af84, df64b9232156). 570 outdoor screens with natural outlines, 74 indoor kept.
- Borders between outdoor screens whose layer weights step by more than 0.15 anywhere along the edge
  (`Scripts/PhotorealQA/ground_mask_seams.py`, `border_seams.txt`): master 568 of 1,040, this branch 44
  (mean largest step 0.453 -> 0.029). The 44 left are screens whose own tiles carry five layers, so one is folded
  on one side (rocky grass drawn as meadow, wet sand as dry sand). A neighbour's sliver never takes a channel from a
  screen's own layer (a layer of the screen's own tile classes is never folded while the screen has four or fewer of them; checked over every screen by a unit test). Water alpha byte-equal to master
  (#147's shore distance) on all 644 masks.
- Art coverage unchanged: 4,917 final / 1,538 placeholder / 152 cut, no row changes state.
- Unit tests: `Scripts/tests/test_ground_layer_fields.py` (15) and the export helper tests pass; the full Scripts suite (902) passed on the first version.

## Sheets

- `masks/mask_NNN.jpg`: the terrain masks of a 3 x 3 block of screens round NNN as flat layer colours, master left,
  this branch right (blue = water from the alpha). No game needed; shows the outline change and the borders.
- `sheets/terrain_NNN.jpg` (22 screens) and `sheets/terrain_border_A_B.jpg` (3 borders): in-game frames, master
  (top row) against this branch (bottom row), play camera / oblique / straight down. Before: a private copy of master
  a610d506 with its own world; after: the same copy with this branch's world imported (`import_greybox --region all`).
  Taken 16 Nov 2026 03:00-05:15 PT, looked at one by one on 16 Nov.

## Connectivity (coordinator review of 16 Nov 2026)

The first version broke 341's winding path into blobs: the blur thins a path that is one tile wide (or drawn on
transition tiles, where the path's colour split rarely wins a cell) below the winner threshold where it turns. Now
(`Scripts/ground_layer_fields.py`):
- A 1997 region of a layer is the cells it wins plus, for every layer but the screen's ground, the cells where its tile
  weight is at least 0.25 and it is the strongest feature (`region_sources`); the ground is what the features leave (a
  path across a meadow divides it, as the tiles draw it).
- After the winners are chosen, `keep_connected` checks every region per layer (8-connected): a region that the
  smoothing split (or wiped out, 16 cells or more) gets a neck along its 1997 centreline (Zhang-Suen skeleton,
  about 20 px wide, inside the 1997 region, so within the outline) and pieces that still do not touch it go; two
  regions the smoothing joined are cut apart where the cells nearest to each meet. Thin features first; a later neck
  does not paint over an earlier one. The same check runs again on the written weights after feathering and the
  channel fold (`connected_weights`: a changed texel's winner is raised 0.05 above the others).
- The water bed (WetSand, drawn under the 1997 water tiles) never spreads onto land: on 726 it had come out as a
  dark patch at the west tip of the sand (21 land texels on the old branch, 0 now).
- Export report (world, this head): regions split by the smoothing 348 -> 0 and joined 258 -> 77 in the work
  windows; in the WRITTEN masks split 131 -> 1 (SCR_477 MeadowTurf, the ground) and joined 121 -> 36 (mostly the
  ScorchedSoil ledge rows of 28-64 and 154-159 running together into strips, and some meadow pieces).
- Cost: the necks and cuts are decided per screen, so borders that step by more than 0.15 went from 44 to 105 of 1,040
  (mean largest step 0.029 -> 0.054; steps over 0.5: 28 -> 36); a world-consistent version is a follow-up.
- Tests: `ConnectivityTests` (an L-turn and an S-turn one tile wide stay one path on four map positions, two paths a
  tile apart stay two, a path on transition tiles with 40 % weight stays one path, the neck stays inside the path).

- New sheets with the fix (16 Nov 2026 after the second reboot; after = this head's world, before = master):
  `sheets/terrain_341.jpg`: the dirt path now runs as one path from the barrel to the south edge (over and top
  views; master's tile-cross cracks stay gone); `sheets/terrain_726.jpg`: the sand tip is clean, the dark patch is gone;
  `sheets/terrain_318.jpg`: the turning path stays one path and the broken dirt strip west of it joins into one strip;
  `sheets/terrain_685.jpg`: both winding paths stay continuous; `sheets/terrain_border_341_342.jpg`: the border patch
  still runs across in one rounded shape. The other 20 sheets show the first version (before this fix); the fix only
  touches cells where a region split or joined. (685 play: a pillbug walked under Dink and its damage numbers show:
  live creatures, not this change.)

Why 430, 694 and 489 keep their rectangles and 060/061 their ledge blobs: no outline may move more than 25 px (half a
tile) from the 1997 one (`MAX_SHIFT_PX`, the owner-direction bound), so a field of several tiles only rounds its
corners. Lifting it needs a larger bound for patches away from paths, water and placements (a deviation the coordinator
or owner would decide), or patch-interior noise. Kept as rows.

## In-game frames (what I see)

- Borders: `terrain_border_341_342` is the clearest proof: on master the dirt patch stops on a straight north-south
  line at the screen border; on this branch it runs across it with one rounded outline. `border_351_383` and
  `border_383_384` (sand / grass / water) show no step at the border on either side; the water's own stair-step
  outline there is unchanged (water shapes, PR #150).
- Patches: rocky-grass squares and single dirt tiles become rounded, irregular patches (059, 060, 122, 341, 342,
  350, 414, 489); rows of single-tile blobs (060, 061 north edge, 245) join into irregular strips that no longer
  repeat every 50 px; the long road edge on 245/246 and the sand/grass edge on 726 wave instead of running straight.
  The tile-cross crack lines on the 341 dirt (master, play view) are gone. No floating patch, no visible seam, no
  stretched texture in any frame.
- Still wrong (follow-ups, not regressions unless said):
  - 341: the winding dirt path of master is broken into separate blobs on this branch (the path no longer reads
    as one path). The 25 px clamp and the blur thin a one-tile-wide path below the winner threshold where it
    turns. Regression in look; candidate for the next pass (keep `structured` paths connected).
  - 430 and 694: large rectangles (the rocky-grass block with its stepped dirt core on 430, the 4 x 3 tile dirt
    field on 694) keep their rectangle: only their corners round, because no outline may move more than 25 px.
    489's cobble field keeps its L shape with long straight sides for the same reason.
  - 277 and 245 (west edge of the top view): small squarish patches with straight sides remain.
  - 726: a darker brown patch appears at the west tip of the sand (after only): a folded wet-sand / rocky-grass
    layer drawn with the neighbour's colour.
  - Ledge lines on cliff transition tiles (060/061) still read as rows of blobs, not as a continuous strip.
- Not this change (seen in the same frames, existing on master): water edges in tile steps with a white dashed
  line along the 1997 outline (693, 726, 384: A59-type, water shapes PR #150), pixelated sprite cards at the play
  camera (277 boulder, 350 house and door, 693 tree), two long thin rods across 409's top view, Dink placed on the
  water surface by the capture's teleport (456, border 383/384). 312 (camera inside the pine crowns) and 409 play
  (camera inside a mesh) show no ground and prove nothing.
- Frame cost: not measured beyond the fps lines of the capture runs (no change in material work).

## Tests and probe

- Pre-reboot run X3 (copy of a610d506 + this branch, world imported from this branch's export):
  `Dink.Art+Dink.Import+Dink.Gameplay.Probe` 116/116 passed (1 with warnings). All twenty probe trace md5s equal
  `Plugins/DinkParity/Docs/packaged_probe.md`: Ch1 b4ad88c02c, Ch2 bc267a0dfc ... Ch10 23fd57dfdc, Ch11 0d70cebfcd ...
  Ch20 84f33687af.
- After the rebase onto master 3a7b4451c the export of this branch is byte-identical to the tested one in every
  terrain mask, the ground pictures and screens.json (only master's own sprites.json change, the saved pictures).
- Final head (master c878e29e + this commit; world and Stonebrook imported from this export in a synced copy, 16 Nov
  14:00-14:16): `Dink.Art+Dink.Import+Dink.Gameplay.Probe` **121/121 passed** (6 with warnings), all twenty probe md5s
  equal `packaged_probe.md` (Ch1 b4ad88c02c ... Ch20 84f33687af, the same list as above). The test ran on 84e045b0 + this
  commit; the rebase onto c878e29e touched only AGENTS.md (no exporter or terrain change).

## Not done / not checked
- On the rebased head (master 3a7b4451c + this commit), a private copy synced to every tracked file of that tree,
  built (0 warnings), world and Stonebrook imported with this branch's export (16 Nov 2026, 09:09-10:04 PT):
  `Dink.Art+Dink.Import+Dink.Gameplay.Probe` **121/121 passed** (6 with warnings). All twenty probe trace md5s equal
  `packaged_probe.md`: Ch1 b4ad88c02c, Ch2 bc267a0dfc, Ch3 bbd401167c, Ch4 8740518c57, Ch5 d987c043f6, Ch6 2df37e4a27,
  Ch7 a16d1d23b8, Ch8 764e9d330f, Ch9 dd1e2662fa, Ch10 23fd57dfdc, Ch11 0d70cebfcd, Ch12 79c8ce55f9, Ch13 98a2e17ba0,
  Ch14 f1ddbaab7b, Ch15 7e3dbbd0b1, Ch16 48e797069a, Ch17 4277c65c35, Ch18 d33886b797, Ch19 45b399bac8, Ch20 84f33687af.

- Frame cost not measured; the grass carpet along the new outlines only seen in the play views above.
- Ledge lines drawn on cliff transition tiles (212-246, 59-61, 341) read as rows of rock blobs, not continuous strips.
- `M_Env_Terrain`'s mask warp still acts up to the screen rim (follow-up branch art/terrain-layers-material: edge-aligned lookup, warp faded at the rim; needs a material rebuild).
- Sand/water stair steps (383, 415, 416, 447, 727-731, 759-764) are the water outline, not this change.
