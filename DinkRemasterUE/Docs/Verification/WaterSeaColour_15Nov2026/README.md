# Water colour from sea to pond across screens; stale worlds keep their water (15 November 2026)

Follow-up of PR #126 (water banks) and of the visual sweep's row 9 (sea drawn in pond olive). Visual only: the world export's `collision.json`, `placements.json` and `warps.json` are byte-identical before and after (md5 `4621771a435c`, `2a59cd90fa3d`, `4659aa549a18`, the values of #126).

## What was wrong

- The review of #126 read the seam beside 633 as the shore sheet taking pond colours next to sea water. It is not: the importer coloured 634 and 665 (the filled water next to 633's sheet) as pond too (their `MI_Water_SCR_*` carried no sea parameters). The blue-green in that frame is 666, which has a dry-sand layer, so the importer made it sea: a seam between two filled screens.
- The importer coloured each screen on its own (sea when the screen is kind `sea` or its mask has DrySand or ShingleBeach). Open sea drawn with wet sand only was pond-olive: 424, 480, 576, 608, the south coast 720-724 and 750-758. Map-wide, 31 screen edges had filled sea water against filled pond water.
- `mark_sea_water` (#126) also looked one screen west of a screen at the start of a row, which is the east end of the row above (385 looked at 384).
- A world generated before #126 (or a screen without a terrain mask) drew no water at all on the seven water-tile screens and logged nothing: the shore material finds the shoreline in the mask's alpha, and such a mask has none.

## Change

- World export (`water_sea_weights`): one sea weight per screen with water, 0 (pond) to 1 (sea). Seeds are the importer's old rule and open water (90 or more of 96 tiles). Water one screen away from a seed is sea, two screens away half, further away pond. A screen whose water joins two sea screens is sea. No step between joined screens is bigger than half. Screens join when their water fills meet across the shared edge, or when one of them is a runtime sheet. Neighbours never wrap across a row end. The 1997 tiles cannot tell sea from river: the south coast uses the lake tileset 8. So the rule works on the map's water graph. Result: 150 screens are sea, 9 half (314, 315, 412, 427, 442, 443, 477, 635, 661) and 51 pond. 0 hard seams remain (31 before).
- Importer: `MI_Water_SCR_*` blends Absorption, Scattering and ScumAmount from `M_Env_WaterShore`'s pond defaults to the sea values by `screens.json` `water_sea`. A bundle without the field falls back to the old rule.
- Runtime water sheets read `ground_classes.json` `water_sea` and blend the same way. A water-tile screen whose mask is missing, or whose mask has no alpha channel, logs `DINK ENV: water tiles on screen N: ... Regenerate the world (Scripts/import_greybox.sh --region all).` once. It then draws the old rectangle sheets (`environment.json` `water_tiles.fallback_material` = `M_Env_Water`, 9 cm). An opaque alpha is built as BC1, which has no alpha channel.

## Sheets (running game, offscreen Vulkan, play camera and the review's camera above the hero)

- `633_666_estuary_before_after.jpg`
  - Top left: 633 from above on master (#126 frame). Olive sheet, olive 634/665, blue-green 666 in the corner with straight seams.
  - Top right: after. 633's sheet, 634, 665 and 666 are one blue-green body and the colour seam is gone. Still there: the straight tile step where the sheet meets the rim, and a pale striped band at the rim between the sheet and 634.
  - Bottom left: 666 from above. The whole estuary is one colour.
  - Bottom right: 635, the river upstream. It is at half weight, and half still reads close to pond, so a softer straight step remains against 634 (diagonal edge, left). Another remains against 603 at the top (pond). **Open.**
- `open_sea_before_after.jpg`: 424, 480, 576, 608, 720 and 753. Before is the visual sweep's frame on master `f92915fe`: pond-olive open sea. After is this branch: blue-green, the same as the sea screens beside them. The cameras differ: the sweep's frame against this run's above view.
- `244_465_ponds_after.jpg`: 244 and 465 from above, before (#126) and after. Both are inland ponds: the importer and the sheet both stay pond, so nothing changes. Still there: a shade step and a straight edge where the sheet meets the next screen's water (465's west end against 464, 244's south rim against 276). Each screen's depth comes from its own shoreline. With the straight rim this is Fable row WB-1 plus a cross-screen shore distance (code). Also: 465 at the play camera after, and the sea-shore sheet of 385 from above.
- `stale_world_fallback.jpg`: the same build on the world from 12 Nov (before the water banks). 633, 465 and 244 draw the old rectangle sheets instead of nothing. The log has the warning for 244, 385, 465, 494 and 633, the five water-tile screens the run passed. These frames were taken with the build of the first commit (sheet fallback and the old per-screen sea rule). The fallback code did not change after it.

## Checks run

- `python3 -m unittest discover -s Scripts/tests`: 889 tests OK. New: `SeaWaterTests` in `test_ground_export_helpers.py` (the importer's rule, no row wrap, fills meeting at an edge, open sea to river fade, coast between two sea screens, no step above half, the 633 and 465 sheets, what `mark_sea_water` writes).
- Build of master `0bf319c9` plus this change (rebased since onto `0f1185b8`, which adds docs and the review-only scene audit): 0 warnings. World regenerated (`import_greybox.sh --region all`, then `--region stonebrook`). `Dink.Art+Dink.Import`: 87/87 passed.
- `Dink.Gameplay.Probe`: 29/29 passed (one engine teardown warning in `ProbeLoadOracle.StockProjection`). All twenty trace md5s equal the `packaged_probe.md` table (Ch1 b4ad88c02c ... Ch10 23fd57dfdc, Ch11 0d70cebfcd ... Ch20 84f33687af).
- `MI_Water_SCR_*` after the import: sea parameters on 424, 480, 576, 608, 720, 753, 634, 665, 666, 635 and 314. None on 464 and 276 (pond).

## Not checked

- 736, 494 and 438 were not captured this time. The packaged build was not run.
- The half weight was not tuned (a non-linear blend would make it read halfway).
- Screens with filled water but no terrain mask take the shared `MI_DinkWater` and ignore the weight.
