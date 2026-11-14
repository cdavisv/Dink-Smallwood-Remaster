# Pine and oak shading (14 November 2026)

Change: `FOLIAGE_LOOK` in `Scripts/import_photoreal_art.py`, `MI_Veg_PineNeedles`, `MI_Veg_PineNeedlesDry`, `MI_Veg_OakLeaves` (see `IMPORT.md`, "Pine and oak shading values"). Material values only.

| Sheet | What it shows |
|---|---|
| `foliage_calibration_pine_oak_before_after_reference.jpg` | calibration scene (screen 299, Blender review camera and sun): before, after, Cycles reference; pine on top, oak below |
| `foliage_pines183_game_before_after.jpg` | screen 183 at the play camera |
| `foliage_oaks664_game_before_after.jpg` | screen 664 at the play camera |

`cal_compare.py`, luminance percentiles 5/25/50/75/95 of the foliage pixels (0..255):

| | reference | before | after |
|---|---|---|---|
| pine | 13 / 33 / 56 / 82 / 108 | 5 / 13 / 25 / 70 / 118 | 24 / 36 / 50 / 91 / 141 |
| oak | 5 / 13 / 22 / 36 / 81 | 2 / 8 / 17 / 34 / 144 | 3 / 8 / 17 / 32 / 109 |
| bush (unchanged values) | 4 / 26 / 99 / 149 / 165 | 8 / 30 / 84 / 169 / 188 | 12 / 35 / 92 / 158 / 178 |

The "before" row was captured without the meadow tint and the "after" row with it; the statistic counts green-dominant pixels, so the greener ground moves it a little (the bush row shows how much).

What the last look still faults:

- Pines: no longer black on the shaded side, but flatter than the Cycles render (less depth between the boughs) and their sunlit highlights are brighter than the reference (141 against 108).
- Oaks: sunlit highlights still above the reference (109 against 81); the crown interior is still darker than the reference's median.
- Bushes: unchanged. They read as heaps of large leaf cards in the Cycles render as well: that is in the meshes (asset side), as are the pines' sparse, angular boughs.
