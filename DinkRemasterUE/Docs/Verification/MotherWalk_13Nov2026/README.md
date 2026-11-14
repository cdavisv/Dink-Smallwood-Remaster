# The Mother's stuttering walk: cause, fix, proof (13 November 2026)

Owner, after playing a build of master `cb842dd2`: "improve the mother's stuttered walk". Animation pass 2 (PR #89)
had smoothed the scripted position and reported the stutter gone; this folder records what was still wrong, with
numbers from the running game, and what the fix changes.

## What was wrong

Her body is drawn at a smoothed position and facing (`FDinkBodySmoother`), applied as an offset from her actor.
`UDinkHumanoidComponent` worked that offset out in its own tick, in the first tick group of the frame. Her script
and her brain run later in the same frame (`UDinkStorySubsystem` is a tickable object: the engine ticks those after
the actor tick groups) and move and turn the actor then. So every frame was drawn as **this frame's scripted
position plus last frame's offset**:

- **Position.** Her brain steps her one whole pixel (6.2 cm on a diagonal in her house) on some 60 Hz frames and
  not on others (the human pace takes 46% of them). On a frame with a step the body jumped the whole step forward
  with the actor; on the next frame the offset caught up and pulled it back. At 60 fps the shown speed along her
  walk ran +490, -250, +120 cm/s in a three-frame pattern around a mean of 120.
- **Facing.** At every turn the body took the script's new facing for exactly one frame (a flip of up to 180
  degrees), went back to the old facing on the next, and only then eased round.

The smoothing maths was right, which is why `Dink.Animation.NpcSmoothPresentation` (a test of the maths alone)
passed. The mesh swap (`dink.PhotorealNPCs`) is not involved: the same component carries either mesh. The path is
not re-planned, the walk cycle does not flicker (13 starts and stops against the script's 12), and the foot slide
numbers of pass 2 stand.

## The fix (presentation only)

`UDinkHumanoidComponent` has a second tick function in `TG_PostUpdateWork`, after the tickable objects and before
the frame is drawn. It puts the body on the smoothed position and facing again, against the actor's transform as
the scripts left it (`PresentBody`). A jump of the actor beyond the warp distance takes the body along at once.
Nothing in the script, the sprite simulation, the brain, the pace or the collision is touched.
`dink.Npc.LatePresent 0` switches the second step off, for comparison only.

## Numbers from the running game

Recorded with the new console command `dink.Npc.Trace <seconds> [file] [frame folder]` (one CSV row per rendered
frame: sprite pixel, direction, brain action, actor and body position and facing, speeds, gait phase), new game,
opening talk skipped, her own wandering, offscreen Vulkan. Reports by `Scripts/AnimationQA/npc_trace_report.py`,
charts by `npc_trace_plot.py`. "Steady walking" is every frame at least 0.6 s after her script last changed what
she does (the first 0.6 s is the eased start or turn).

| | Before (master `cb842dd2`) | After |
|---|---|---|
| 60 fps, 45 s, 1001 steady walking frames: shown speed along her walk | mean 119.8 cm/s, deviation **297.0**, from -256 to +493 | mean 119.8 cm/s, deviation **3.3**, from 101 to 125 |
| ... frames on which the body moves backwards | **32.2%** | **0.0%** |
| ... worst change of speed between two frames | 743 cm/s (median 373) | 18 cm/s (median 2) |
| ... frames turning faster than the 300 deg/s limit | **12** (fastest 10,798 deg/s: 180 degrees in one frame) | **0** (fastest 300) |
| ... walk cycle starts and stops / the script's | 13 / 12 | 13 / 12 |
| 83 fps (uncapped), 30 s, about 1200 steady frames: deviation | **348.6** | **4.0** |
| ... frames moving backwards | **22.8%** | **0.0%** |
| ... frames turning faster than the limit | **16** | **0** |

## Files

- `walk_before_after_60fps.png`, `walk_before_after_83fps.png`: per rendered frame, the speed of the shown body
  along her walk over a steady stretch of 149 frames, and how far the body has turned through one scripted
  about-turn. Red is master, green is the fix. The saw-tooth and the one-frame spike to 180 degrees are the
  stutter; the green lines are what is drawn now.
- `frames_before_after.png`: nine consecutive rendered frames (1/60 s apart, `-benchmark -fps=60`, pictures saved by
  `dink.Npc.Trace` with a frame folder) around a scripted turn as she sets off, cropped to her and enlarged; top the
  old behaviour (`dink.Npc.LatePresent 0`), bottom the fix, same session and seed. Top: she stands three-quarters
  away from the camera, shows her front for the turn frame, is turned away again on the next and then eases round.
  Bottom: she eases round from the first frame. (She is small in the picture and the anti-aliasing carries each
  frame into the next, so the flip covers two pictures; the yellow label is the facing in the trace row.) The
  frame traces repeat the numbers of the table: deviation 296.3 against 3.4 cm/s, 32.0% against 0.0% of steady
  frames moving backwards. The position stutter itself (4 to 6 cm) is too small to see in stills at this distance;
  the charts show it.
- `trace_before_60fps.csv`, `trace_after_60fps.csv`: the two 60 fps recordings behind the table.

## Tests

- New: `Dink.Animation.NpcShownMotion` (a PIE session of the real map, 60 Hz steps). It reads the Mother's body
  transform at the end of every frame and requires: no backward frame and a deviation under 8 cm/s during a steady
  scripted move and during her own wandering; every turn within the turn rate; no more walk-cycle starts and stops
  than her brain's plus two. It first runs her wandering with `dink.Npc.LatePresent 0` and requires the measure to
  find the old defect there, so the test cannot go blind. Its numbers on this branch: a scripted move of 70 px, 117
  steady frames, shown speed 119.9 cm/s with a deviation of 0.2 and no backward frame; a scripted about-turn at
  300 deg/s; 25 s of wandering with the step off: 176 of 546 steady frames backwards, deviation 298.5 cm/s, a turn
  of 10,800 deg/s; with the step on: 0 of 536 backwards, deviation 3.3 cm/s, fastest turn 300 deg/s, 7 walk-cycle
  starts and stops against the brain's 8.
- `Dink.Animation` 6/6, `Dink.Movement` 10/10 (one editor run, 35 s), `Dink.Art` 58/58 (86 s); `Scripts/build.sh` clean, 0 warnings; `python3 -m unittest discover -s Scripts/tests` 825 tests OK. The Unreal suites ran on master `cb842dd2` plus this change; the branch was then rebased over PR #96 (art, one import script and one Python test, no C++), after which the Python tests were run again.
- Parity: `Dink.Gameplay.Probe` 29/29 in 527 s on a world regenerated by the current importer (`--region all`, then
  `--region stonebrook`); the twenty chapter trace md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1
  `b4ad88c02c` ... Ch20 `cc16518259`, all twenty compared). One test of that filter, `ProbeLoadOracle.StockProjection`,
  passes with an engine warning (`LogSpawn: UWorld::DestroyActor: World has no context`); it does not touch this code.

## Other NPCs

- **Milder** (`s1-bul`, a script-spawned sprite) uses the same component, so he gets the same step. His walk-in
  (after the pig feed on screen 407) was not recorded for this PR: the capture that traces it was still queued for
  the shared editor when the PR opened. The automated test runs on the Mother only.
- **Townsfolk that are still picture cards and the creature bodies** (`UDinkCreatureComponent`) are glued to the
  scripted position, with no smoothing at all: they move in whole pixels on 60 Hz frames, which is even at 60 fps
  and uneven at any other frame rate (pass 2 measured a glued body at a deviation of 115 to 310 cm/s). That is not
  changed here: the cards are placeholders that gate 2 replaces, and the creature bodies belong to the creature
  session, to which it has been reported. `FDinkBodySmoother` plus the end-of-frame step is the remedy for both.

## Not checked, not changed

- Not seen on a display by a person: the recordings are offscreen renders (60 fps capped and about 83 fps uncapped).
  Frame rates above 83 were not recorded; the maths test covers 47, 60 and 144.
- The packaged build was not run.
- A scripted about-turn still starts about 0.1 s late (the body keeps its travel direction until the smoothed speed
  has fallen below 25 cm/s) and then takes 0.6 s; over the 45 s recording she travels 34 cm of 2,475 cm backwards
  relative to her facing and 141 cm sideways, during turns. Unchanged by this fix.
- Her walk clip is still the tall mannequin's (pass 2, P2.6): arms away from the body, a long stride for a long skirt.
