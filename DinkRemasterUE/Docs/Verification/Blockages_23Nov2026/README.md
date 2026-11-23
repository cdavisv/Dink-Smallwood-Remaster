# Invisible blockages: A71 walls, A92 painted rocks, A20 pond teleport, P8 the King; A93 and A94 measured (23 Nov 2026)

Owner's order: "fix hitboxes and invisible blockages in the game". Rows of `doc/remaster/ALPHA_BUG_LIST.md` (A20, A71 interior walls,
A92, A93, A94) and of the 20 Nov playtest (`Playtest_20Nov2026/README.md`: P8, A61, A62). Headless only (machine rule of 21 Nov 2026:
no rendered Unreal work); every in-game look below is on `RENDER_PENDING.md`.

## What changed
- **A71 (physical play layer, play only)**: interior and dungeon wall modules drawn on one thin strip of a thick 1997 wall box (door
  jambs, corner posts, partitions, dungeon walls; Dink stopped 1.1-5.4 m short in the test walks) keep their box in Dink's collision
  only inside the drawn strip. `Scripts/make_relaxed_hardboxes.py` lists them (`relaxed_hardboxes.json` "trimmed": 248 walls on 37
  screens, 11 kept by the passage rule) with a passage rule that treats the export's water and void fills as nobody's ground; at each
  screen entry `UDinkGameplay::MeasureWallStrip` measures the strip on the wall meshes as they stand (their lowest 1.2 m of vertices),
  and `SyncGreyboxHardness` / `PlayHardness` keep the box there. The 15 Nov audit's slices were 5-115 cm off today's modules, so the
  runtime measurement is the one used. `doc/remaster/PHYSICAL_PLAY_LAYER.md`, section "Invisible-blockage rows".
- **A92 (layer, play only)**: 96 more open tiles: the audit's invisible LOW tile walls whose pieces are blobs of at most 60 px (painted
  rocks), with no shortcut rule. Lines (fences, hedges, ledges, banks) and solid tiles stay for art row PM-05.
- **A20 (both modes)**: `UDinkGreyboxSubsystem::GotoScreen` places a teleport whose spot is a hole (nothing under it to 20 m, not inside
  anything: SCR_471's authored pond) on the nearest pixel of that screen with a floor and room for the capsule.
- **P8 (layer, part Bodies)**: a still class-bound body that is solid in 1997 (brain 0, `sp_hard` 0: the seated King, S070_P03) gets
  the drawn-body box too.

## Measured, nothing to change in code
- **A94** (`a94_shore_contact.txt`): the export's natural shorelines (master since 16 Nov) already end the drawn water where Dink
  stops. The exporter's own functions (`shaped_water_window`, `water_band_blockers`) rerun on every water screen: the shore-band low
  pixels Dink can touch from dry 1997 ground lie at the drawn waterline (20,457 at 0 px, 6 at 1-3 px, none further). Drawn water over
  1997-walkable ground is player-blocked (157 screens) or drawn back to the 1997 line (470, 697, 701, 468, 469, 476, 478: the whole band).
  The 15 Nov captures (`PhysicalMapping_15Nov2026/before_water_shores.jpg`) predate that change. The water bands belong to the
  environment layer, which headless runs do not build, so a headless walk cannot show them: rendered walk on RENDER_PENDING.
- **A93** (`a93_tiles.txt`): 1,008 of the audit's 1,227 tiles are export fills (open sea, void, canopy interiors: 1997 hardness 0
  that tools/analyse never reaches; the audit took the largest hardness-0 region, which on a sea screen is the sea), 189 are shore
  tiles 20-50 % fill, 29 are open tiles in play now, 1 other (SCR_408 tile 8,1, the P1 screen). No blockage of reachable ground found.
  The 349 screen-edge cells of the row were not re-checked.
- **A62** (camera, not fixed): reproduced headless: in the north-east corner of SCR_001 by the sack the spring arm is pushed to 54 of
  240 cm, the camera 18 cm from Dink's head (room centre: full arm). A fix (lift or swing the camera when the arm is compressed) changes
  the player's camera and needs a rendered look: proposal on RENDER_PENDING.
- **A61** (camera): headless, entering Ethel's house the arm is full (250 cm) and the camera channel sees Dink's head from 0.2 s on;
  what the partition does to the picture needs a rendered look (RENDER_PENDING).

## Tests (headless)
- `Dink.PhysicalPlay.BlockageRows` (new, PIE on the generated world): A20, A71 (four walls, layer off and on), A92 (SCR_126 rock, off
  and on), P8 (the King with his class-bound body), A62/A61 camera numbers.
- `Dink.PhysicalPlay.RealScreens` finding 5: a trimmed wall's box stays inside its strip.
- `Scripts/tests/test_make_relaxed_hardboxes.py`: strip and box of a wall row, the passage rule (partition, short strip, void), audit tiles.


## Not checked
- Rendered looks (all of the above); original-hardness projection screens (34, 161, 162, 194, 196 ...) keep their wall boxes.
- The generator reads the 15 Nov dink.PhysAudit run (as the relaxed list always has); a new audit after art changes may move rows.

## Gates (headless, rebased on master 6e3d4f991, copy Saved/Collision21Nov, 23 Nov 2026)
- Clean build (Intermediate removed): 0 warnings.
- `Dink.PhysicalPlay`: 10/10 (BlockageRows, RealScreens, Blockages and the rest).
- Layer-off probe (`Dink.Gameplay.Probe`, the automation default): 29/29, all twenty md5s equal `packaged_probe.md` (A41 table), twice
  (g2 and d1). Layer off, the 1997 path is untouched: every change is in part Collision / Bodies of the layer, or in `GotoScreen` for a
  spot with no floor at all.
- Full `Dink` suite: 404/405; the one failure is `Dink.Movement.Landforms.ScriptedMoveAcrossRelief`, the suite-only flake collision-3
  saw on 21 Nov (rerun alone: see the PR).
- Layer-on chained probe (`probe_on.sh`, Mode 2, class art on): 19/20. Chapter 20 (the Seth bow duel) dies in the chained run, the same
  way twice (md5 71e934a314): from chapter 4 on the layer-on routes differ from #160's run (more ground is open), and the chained bot
  reaches Seth with less to heal with (life 0/95 at the stop). From the layer-off saves, chapter 20 with this code passes 5/5 under the
  layer. `Repeatable` fails under the layer as before (layer-on runs are not deterministic).
- Python: `test_make_relaxed_hardboxes.py` 7/7; scrub clean; LFS audit 0 missing.
