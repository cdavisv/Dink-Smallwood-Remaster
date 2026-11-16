# Motion realism: feet that stay planted, stride warp, gait styles (16 Nov 2026)

Branch `anim/motion-realism`. Owner's order of 15 Nov: fix the characters' physical movement (hips, joints), match it to
their personality; older feedback: the mother's stuttered walk, Dink's arms around the armpit.

## What changed (presentation only; the sprite, hardness, timing and scripts are untouched)
- Leg layer in `UDinkBodyAnimInstance` (new `DinkFootPlacement.h/.cpp`): two-bone soft IK, per-foot contact lock (a foot the
  clip sets down is pinned where it lands, let go with a 0.12 s blend when the clip lifts it), pivot steps when Dink turns
  on the spot, foot placement on the visible ground, look-at for NPCs (`DinkHumanoidComponent`).
- **Stride warp** (the cause of the skating): the slow-walk cadence law (`slow_cadence_power`) plays the mannequin walk at a
  cadence that leaves the stance foot travelling back 15-20 % faster than the body. The layer measures the stance foot's
  speed under the body and scales the step length so it equals the body's speed (smoothed, 0.6-1.6, walking only; a run is
  left to its capture: warping it doubled its slide).
- Shorter steps fold the stance knee: the hips rise by up to 2.8 cm to keep the stance leg as straight as the clip's.
- Gait styles from `animation_natural.json` `style` (`FDinkGaitStyle`): timid Dink short, quick, slightly uneven steps, knees
  together; confident Dink the capture's stride; Mother short and narrow under her skirt; Milder wide with a chest swagger.
  Style stride and uneven steps fade out between 3 and 4.5 m/s (nothing holds a run's feet).
- No new pins at run speed; standing <-> walking is a blend in time (no 56 cm foot jump on arrival); the frame is pushed
  to the animation proxy after NativeUpdateAnimation (it was one frame late).
- Tools: `dink.Motion.Trace` (bone trace CSV), `Scripts/AnimationQA/motion_audit.py` / `motion_report.py` (numbers),
  `mother_strip.py` (a camera that follows Mother, the player hidden), `sheet.py`.
- Cvars: `dink.Anim.Legs 0` is master's behaviour (used for every "before"), `dink.Anim.FootLock`, `dink.Anim.GroundAdapt`,
  `dink.Anim.Style`, `dink.Anim.LookAt`.

## Numbers (in-engine test `Dink.Animation.Legs.InEngine`, hero walking straight on flat ground, cm per frame at 60 Hz)
| | layer off (master) | layer on |
|---|---|---|
| walk 120 cm/s, planted slide median / mean | 0.51 / 0.52 | 0.06 / 0.12 |
| walk 170 cm/s | 0.50 / 0.51 | 0.08-0.09 / 0.14-0.16 |
| run 600 cm/s | 1.06-1.15 / 0.82-1.04 | 1.02-1.06 / 0.84-0.87 |
In the game (motion trace of the capture run, `motion_report.py`, same course before and after):
- Hero walk, planted slide median 0.31-0.35 -> 0.00 cm/frame; standing: the largest foot jump 33-38 cm (a pop when he
  stops) -> 3.7-5.5 cm.
- Mother walk median 0.59 -> 0.00, slow walk 0.93 -> 0.00; standing, largest foot jump 20 -> 1.8 cm.
- Knees: the layer bends the walking knee deeper than master (shorter steps under the same hips). Round 7 build: hero
  walk median 37-42 vs 32-34 degrees, Mother 44 vs 31. With the hip rise (this head, final strips and trace): hero still 38-42
  (no change in game), Mother 38 vs 31 and her pelvis bob 5.6 -> 3.8 cm. The hero's deeper knee is still there: see Still wrong.

## Sheets (all from the running game, private copy, offscreen capture, 1280x720 frames)
- `01_walk_side_before_after.jpg`: hero walking, side, confident (c1) and timid (c0). A skate of 0.3-0.5 cm per frame is
  not visible by eye in still strips at this size: the numbers above carry it. What the strips do show: after, the steps are
  shorter (the warp), the timid walk becomes a short shuffling step; in this build the knees are bent more than before (see Numbers), which reads slightly
  crouched for the confident walk.
- `02_run_side_before_after.jpg`: run, side: the same gait, no visible difference (the layer leaves a run alone by design).
- `03_attack_and_turn_timid_before_after.jpg`: timid punch combo and a turn: the punch is the clip's in both; on the turn
  the feet step instead of spinning on the spot.
- `05_walk_side_before_final_head.jpg`: master against this head (hip rise in): the steps are still shorter and the knees
  still a little bent for confident Dink; for timid Dink the short bent-knee step suits him.
- `04_mother_side_before_after.jpg`: Mother walking in her house, camera following her: the gait reads the same at this
  size; her feet are under the skirt, so the stutter is judged from the trace numbers above, not the picture.

## Still wrong (seen, not fixed here)
- Confident Dink walks with shorter steps and 4-8 degrees more knee bend than the capture (the price of the stride warp
  that stops the skate; the hip rise did not reach him in game). A bigger cure is a walk clip captured at his speed (AN-02)
  or cadence instead of stride for the confident walk (row A101 stays open).
- Confident Dink walks with shorter steps and 4-8 degrees more knee bend than the capture (the price of the stride warp
  that stops the skate; the hip rise did not reach him in game). A bigger cure is a walk clip captured at his speed (AN-02)
  or cadence instead of stride for the confident walk (row A101 stays open).
- Dink's arms hang away from the trunk (an open armpit) in the idle, walk and turn: that is the clip's pose on his narrow
  shoulders, not the leg layer. Fable row AN-01 (re-key or retarget the arm pose for Dink's proportions).
- Mother's skirt stretches forward and back with her legs: stream hair-cloth (secondary motion) and Fable SP rows.
- Every humanoid still walks on the one mannequin walk capture; personality is layered (style), not authored. Fable row
  AN-02 (authored walk cycles: timid Dink, Mother).
- Feet brushing the floor at touchdown ("skims", > 4 cm/frame within 1.5 cm of the floor) are the capture's own and as
  many with the layer as without (counted apart in the test).

## Tests and probe
- Targeted `Dink.Animation+Dink.Art.PlayerAction+Dink.Art.HumanoidPresentation+Dink.Movement`: TESTS PASSED 27/27.
- Full `Dink`: TESTS PASSED 323/323 (8 with warnings) in 956 s, on master 84e045b0 + this branch, world regenerated with
  `--export`.
- Probe: all twenty chapter trace md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (ch1 b4ad88c02c .. ch20 84f33687af).
- Not checked: packaged build, frame cost in the rendered game (the layer is a few hundred float operations per body per
  frame, worker thread), slopes and stairs in game (only the flat test course and the house floor).
