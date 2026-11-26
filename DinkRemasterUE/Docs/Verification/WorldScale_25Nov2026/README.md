# World scale ON: rendered check (25 Nov 2026, world-scale-5)

RENDER_PENDING world-scale line. Before = `Saved/Blockages6` (reference scale, #233's head); after = the enlarged world of branch
`world-scale/enable` (copy `Saved/WorldScale25Nov`). `Scripts/PhotorealQA/run_capture.sh` through `Gate2Coord/unreal_turn.sh`, 1280x720,
the play camera, Dink teleported with `dink.Goto` to the same 1997 pixel on each screen. Each `pair_*.jpg` is before (left) / after
(right); `pair2_*` were taken after the `world_scale_convert_art.py` fix (section 14.1 of `doc/remaster/WORLD_SCALE.md`).

## What a player would notice

- **SCR_471 (Stonebrook pond, authored screen):** before the fix a long sky-blue crack ran between the field-tile rows with stretched
  side faces (`pair_05_pond_SCR471.jpg`). Fixed (the tiles follow the layout per axis, `pair2_05_pond_SCR471.jpg`). LEFT: one small dark
  rectangular notch where the dirt bank meets the meadow, bottom right of that frame (the rows stand up to 64 cm staggered: the
  layout's shear, which a tile's scale cannot follow). Art-side follow-up.
- **Dink's size:** he reads the same on every screen (same camera, same 1997 pixel); houses, fences, trees and the pigs keep their real
  size, so screens look emptier and wider, as approved.
- **Floating props:** none seen on these screens. **Gaps at screen edges:** none seen except the 471 notch above.
- **SCR_439 at 320,220:** the spot is in the dark walled yard behind Dink's burnt house in both worlds (mean luminance 10 before, 1 after:
  darker, not judged further); the yard from 300,330 reads fine (`pair2_12_yard_SCR439.jpg`).

## Frame cost (fps / GPU ms; other agents ran headless tests on the machine meanwhile, so fps is noisy, GPU ms is the steadier number)

| shot | before fps / GPU ms | after fps / GPU ms |
|---|---|---|
| 01_house_SCR001 | 81.0 / 12.07 | 82.5 / 11.86 |
| 02_stonebrook_SCR439 | 96.5 / 9.88 | 96.6 / 9.88 |
| 03_stonebrook_SCR438 | 83.6 / 11.54 | 85.9 / 11.32 |
| 04_stonebrook_SCR407 | 86.9 / 10.92 | 87.1 / 10.71 |
| 05_pond_SCR471 | 84.2 / 11.09 | 80.6 / 10.99 |
| 06_wild_SCR474 | 83.9 / 11.12 | 76.7 / 10.96 |
| 07_windemere_SCR534 | 84.7 / 10.98 | 65.6 / 11.78 |
| 08_terris_SCR465 | 87.0 / 10.90 | 77.7 / 10.78 |
| 09_cave_SCR098 | 114.1 / 6.50 | 97.7 / 7.78 |
| 10_koka_bridge_SCR727 | 86.8 / 9.71 | 63.7 / 11.67 |
| 11_koka_bridge_SCR759 | 79.1 / 9.84 | 81.7 / 9.85 |
| settle_439 | 72.7 / 10.91 | 65.6 / 11.59 |
| busy_439_10s | 89.3 / 10.13 | 78.3 / 10.66 |

Busy screen (439, 10 s): GPU 10.13 -> 10.66 ms (+5 %). The two outliers (Windemere 534 and the Koka causeway 727: GPU +0.8 / +2.0 ms)
draw more open ground and distance at the bigger layout.

## dink.WalkAudit at the enlarged scale (headless, -nullrhi, 1 768)

- Blockers on: 5,438 meshes measured, 140 with walk-in >= 20 cm (105 >= 40 cm). `check_player_blockers.py`: 336 screens, 0 cut off.
- Blockers off, both scales: 5,937 rows enlarged / 5,633 reference; walk-in >= 20 cm 746 / 640. `make_player_blockers.py` gives the same
  38 meshes at both scales, so `player_blockers.json` stays as it is.
