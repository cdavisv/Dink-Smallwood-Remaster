# Natural shorelines and Dink's water edge (15 November 2026)

Owner direction of 15 Nov (smooth, natural landscape; the physical game follows the drawn objects).

## Change
- `natural_shore` (Scripts/export_import_bundle.py): every water outline (filled and the seven sheet screens) is smoothed in world space with the neighbours' water, bent by a map-position noise, and held outside the 1997 water: 10 px (rounded convex corners) to 25 px past it. Its exact signed distance is the terrain mask alpha; `screens.json` `water_draw` is where the importer lays the water surface (collision keeps `fill_water`).
- Player-only blockers (`ground_classes.json` `water_block`, `UDinkEnvironmentSubsystem::ApplyWaterBlockers`, profile `DinkPlayerBlock` of PR #129, `dink.WaterBlockers`) over drawn water on 1997-walkable ground, so Dink stops at the drawn waterline. The band shrinks on narrow land, keeps away from scripted/brain/warp placements, and is taken back (with the drawn water) wherever it would split a walkable area, close an edge crossing or orphan a placement.
- One mask writer (`naturalise_ground_masks` of PR #146, which this branch is stacked on): the water bed layer (WetSand) lies exactly under the drawn water and a short band up the bank (`wet_bed_follows_shore`); the grass cover keeps out of the drawn water.
- Shoreline field for landforms: `shore_distance_cm`.

## Evidence so far
- `map_river/coast/lake/ford_before_after.jpg`: export-level previews (ground picture + mask alpha, white = waterline), master vs this branch. NOT game frames.
- `connectivity_water.txt`: PR #129's `check_player_blockers.py` on the water band (capsule 6 px, wider than the real one): 0 cut off on 157 screens.
- Export md5s of collision/placements/warps unchanged; unit tests of the export helpers pass.

- `shorelines_in_game.jpg` (running game, offscreen Vulkan, this branch): rows river 634, lake 539, coast 666, coast 383; left the play camera, right from above. The water now ends on rounded, curving banks instead of tile steps; the wet bed follows the waterline. These frames were meant as walks into the water, but Dink did not move (screen scripts held him after the teleport, `move_ignored=1`), so they show the shapes only.

- `walks_stop_at_waterline.jpg` (rebased on master fe342f26, screen scripts on): Dink teleported onto each screen (`dink.Goto`, 10 s for the screen's scripts, three `dink.Skip`), `move_ignored=0`, then walked into the water with `dink.WalkTo` (6 s); rows river 634, lake 539, coast 666, coast 383 (sand bar), coast 752; left the play camera after the walk, right from above. Where he stopped (map px, capsule 28 cm = about 4 px), against the drawn waterline (terrain alpha 0.5) and the 1997 water fill along his path:

  | screen | walk | stopped (centre) | body front | drawn waterline | 1997 fill | without the blockers he would reach |
  |---|---|---|---|---|---|---|
  | 634 river | north | y 285.5 | 281.6 | 282 | 272 | about y 276 (10 px, 72 cm into the drawn water) |
  | 539 lake | north | y 284.2 | 280.3 | 282 | 273 | about y 277 |
  | 666 coast | west | x 541.6 | 537.7 | 534 | 527 | about x 531 |
  | 383 sand bar | north | y 197.6 | 193.7 | 190 | 178 | about y 182 |
  | 752 coast | south | y 296.0 | 299.8 | 298 | 311 | about y 307 |

  The body front ends within 2 px (15 cm) inside to 4 px (27 cm) short of the drawn waterline (the blockers lie on the mask's 6.25 px texel grid); without them he would walk 0.7 to 1.1 m into the drawn water.
- Entry method: all five by teleport with screen scripts ON. Earlier captures with `dink.ScreenScripts 0` froze Dink on marked screens (bug A86, fixed by #137) and are not used.

## Rebased on PR #146 and master (16 Nov 2026, after both reboots)
- Stacked on #146 (natural ground layers): one mask writer, `naturalise_ground_masks` of #146, takes the drawn water
  (`shore_water_cells`), lays the water bed under it (`wet_bed_follows_shore`) and keeps the grass cover out of it;
  `finish_ground_masks` is gone. #146 keeps its water-bed layer from spreading onto land; this branch then lays the bed
  to the drawn waterline. Export: blockers on 157 screens (2,521 rects), drawn water taken back on 121 screens, as before.
- CI fix: `test_visual_only_cache_and_actor_generation_salts` now asserts the bumped salt `visual-ground-water/3` with the
  draw key in the hash (the importer change invalidates the visual cache on purpose).
- `walks_rebased_16nov.jpg`: the same five walks on the rebased tree (master c878e29e + #146 + this, world regenerated):
  Dink stops where he stopped before, to 0.01 px (634 y 285.48, 539 y 284.17, 666 x 541.57, 383 y 197.65, 752 y 295.97),
  at the drawn waterline. Seen in the frames: the banks curve; 666 still shows one right-angled corner of the 1997 outline
  (the 25 px bound).
- `a59_items_273_597.jpg` (bug A59, water drawn over grass where items lie): on 273 the potion lies on grass with no water
  in view; on 597 the potion lies on the lake's grass spit and Dink stands on it, not on the water surface (the spit is
  narrow, sand on both sides).

## Not verified (see the PR)
- A walk-in across a screen edge (only teleport entries were used); the packaged build; surf foam (left out).
