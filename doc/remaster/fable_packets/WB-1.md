# WB-1: Water shape across screen borders: straight tile steps where the drawn water reaches a screen rim (633, 244, 465 west)

| | |
|---|---|
| queue row | PR #126 review (coordinator, 15 Nov); open condition `water_without_surface` in `ground_review.json` |
| priority (queue) | medium (review) |
| estimated size | M |
| stream | Stream D, ground, water, effects, hero, step 5 of that stream |
| kind of work | NOT Blender: world-export mask code (`natural_water_shape`) + a look judgement |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

1997 draws water as 50 px tiles; the remaster bends the tile outline into a shoreline (`natural_water_shape`, PR #126) except within 40 px of a screen rim, where the tile outline is kept so the water meets the next screen.

## 2. Real-world size

Wilderness screens are about 41 x 28 m (6.9 cm/px); a tile step is 50 px = 3.4 m.

## 3. Where it shows

Screens 633, 244 (south edge), 465 (west end); the seven no-fill water screens are 244, 385, 438, 465, 494, 633, 736.

Evidence: `DinkRemasterUE/Docs/Verification/WaterBanks_14Nov2026/633_244_rim_defect.jpg` and `recapture_on_master_adf5b1dc.jpg`, README "Next step for the rim: shape the water across screen borders (one mask for the neighbouring screens together) and take the neighbour's water colour".

## 4. Start from (existing sources, half-done work)

- `Scripts/export_import_bundle.py`: `natural_water_shape()`, `signed_shore_distance()`, `terrain_mask()`,
  `mark_sea_water()` (master after #126).
- `fix/water-sea-colour` (local worktree `DinkWaterFollowup`, commit `349c6a1f`, unmerged): `mark_sea_water` takes the
  colour of adjacent drawn water, no row wrap, runtime fallback; its finding: the colour seam at 633 is an importer seam
  between filled screens (bug A22, open), what remains at 633/244/465 is the depth seam and this rim shape.

## 5. What to make

Shape the shoreline on a mask that spans the screen and its neighbours (or match the outline on both sides of the rim), so the bank bends across the border; keep the river width and collision byte-identical (the export's collision md5 must not change).

## 7. Import and binding

- `Scripts/import_greybox.sh --region all --export` (masks), then `--region stonebrook`; no material rebuild (IMPORT.md "Water without a water fill").

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (`visual_sweep.py` came with PR #132):
```bash
python3 -I Scripts/PhotorealQA/visual_sweep.py "$PWD/Saved/PhotorealPass/fable/WB-1/after" --screens=633,244,465,666,634
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/WB-1/after/sweep.txt"
python3 -I Scripts/PhotorealQA/visual_sweep_report.py "$PWD/Saved/PhotorealPass/fable/WB-1/after"   # sheets + detectors
```
Before frames for the same screens are in `DinkRemasterUE/Docs/Verification/VisualSweep_15Nov2026/frames/` (LFS:
`git lfs pull --include "DinkRemasterUE/Docs/Verification/VisualSweep_15Nov2026/**"`). 

Also the over/above views of #126 (`WaterBanks_14Nov2026` README lists them).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- After `fix/water-sea-colour` merges (same file `export_import_bundle.py`). Shares the mask code with VS-09: do WB-1 first, VS-09 builds on it.

## 10. Done when

No straight step at the rims of 633/244/465; `water_without_surface` re-graded; collision/placements/warps md5 unchanged.
