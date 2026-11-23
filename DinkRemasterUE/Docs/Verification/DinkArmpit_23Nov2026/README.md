# Dink's arms at the trunk (A102 / AN-01), 23 Nov 2026

The owner, 13 Nov 2026: "dinks arms look odd around the arm pit". Cause (stream motion, PR #186): the engine mannequin's
idle, walk and jog captures carry the arms for the mannequin's broad shoulders; on Dink's narrow trunk the elbows hang
8 to 9 cm off his waist and the hands 10 cm off his thighs, an A-shape from the front and from behind.

## In the running game, 23 Nov 2026 (rendered Unreal allowed again by the owner at 11:40)

Three runs of the same 157 fixed-camera shots (`capArmw0`, `capArmw6`, `capArmw9`; frames in the stream's copy,
`Saved/FableC/.../Saved/CharQA/armw0`, `armw6`, `armw9`): W 0 (master), W 6 (this PR's first value, before the fade
existed) and **W 9 on master 6e3d4f991, where PR #226 lets W give way to the run and to action clips** (this version).

- `10_game_1997_and_W9.jpg`: the 1997 pictures above the game at W 9: the game's own camera, standing front and back,
  walking towards and away, running.
- `11_game_idle_walk_W0_W6_W9.jpg`: standing (timid front and back, confident front) and walking, the three values.
- `12_game_run_W0_W6_W9.jpg`: the run from the front, six frames each.

**What I see.** W 0: the A-shape of the complaint, elbows and hands well off the trunk, from the front and from
behind. W 6: the arms come in, a clear gap stays. **W 9: the arms hang beside the trunk and the hands beside the
thighs, standing and walking, timid and confident; no hand in a thigh, no pinched shoulder.** The run at W 9 with the
fade looks like master's run (the fade leaves 2.7 degrees of the 9): the hands swing apart and none lies on the belly;
at W 6 without the fade the forward hand came to the middle of the chest.

**Not seen.** The capture script's sections for the fist combo, the sword, the cast and the death show an empty
field in all three runs (their cameras miss him), so the actions were not looked at. By #226's rule W is zero while an
action clip plays at full weight, which is master's pose; its engine test (`Dink.Animation.Posture.ArmFadeInEngine`)
measures that. A weapon in the hand (#202, #222) was not looked at with the new arm carriage.

## What changed

One data row: `Content/Dink/Data/Art/animation_natural.json`, `posture.Hero`, fourth value (W, the upper arms brought
in towards the trunk, degrees; `DinkBodyAnimInstance.cpp` turns each upper arm about its joint in mesh space):
timid `[7, 7, 7, 0]` -> `[7, 7, 7, 9]`, confident `[0, 0, 0, 0]` -> `[0, 0, 0, 9]` (6 in this PR's first version; 9 since PR #226 fades W in the run and under action clips). No mesh, weight or clip changed.
The Mother (NpcF) has had 12 since #186.

Tools added (no C++): `Scripts/AnimationQA/arm_clearance.py` (measures elbow, wrist and hand against the trunk on the
game's own bone traces with any W applied the way the game applies it), `trunk_profile.py` (the trunk of a character
from its Blender source), `trace_pose.py` (poses the character in Blender from a trace frame and renders it on the CPU),
`Scripts/tests/test_arm_clearance.py`.

## How the first value (6) was chosen, before the fade and before the game could be run

1. **In the game, 16 Nov 2026** (rendered captures on f4743990's content, before rendering was stopped on this
   machine): W 0 against W 11 (timid) / 10 (confident), walking towards the camera, away from it and running.
   `01_game_16Nov_walk_run_W0_vs_W11.jpg`: with 11 the arms hang at the trunk in the idle and the walk and the A-shape is
   gone, from the front and from behind. **Rejected for the run**: the jog capture carries the bent forearms high and
   in; with the upper arms 11 degrees in, both hands lie on the belly and one passes in front of the mouth
   (`01b_game_16Nov_zoom_W11.jpg`, first three frames). One value serves every gait and every action, so it cannot be 11.
2. **Measured on the game's bone traces** (stream motion's `dink.Motion.Trace` run of 19 Nov, hero at confidence 0 and
   1, 4,067 frames each; `clearance_timid.txt`, `clearance_confident.txt`; centimetres between the surfaces):

   | timid | W 0 | W 6 | W 8 | W 11 |
   |---|---|---|---|---|
   | idle: elbow off the waist (mean) | 8.8 | 6.4 | 5.6 | 4.4 |
   | idle: hand off the thigh (least) | 9.8 | 3.5 | 1.4 | -1.8 (in the thigh in 46 % of frames) |
   | walk: hand off the thigh (least) | 10.9 | 4.5 | 2.4 | -0.8 |
   | run: wrist off the belly (least) | 1.7 | -0.4 (1.1 % of frames) | -1.6 (2.3 %) | -2.9 (4.0 %) |
   | run: hands apart (least) | 31.2 | 23.2 | 20.2 | 15.8 |

   Confident at W 6: idle elbow 9.1 -> 6.7, hand 9.1 -> 2.6; run wrist 3.7 -> 1.1 (never in the trunk).
3. **Looked at in Blender** (Cycles on the CPU; the hero's source posed from trace frames, each traced bone aimed at its
   traced child, W applied as the game does; the W 11 run reproduces the hands-on-the-belly frame of the game, which
   is what makes the reconstruction worth trusting): `02_blender_idle_walk_timid_W0_W6.jpg`, `03_blender_run_timid_W0_W6_W11.jpg`,
   `04_blender_actions_timid_W0_W6.jpg`, `05_blender_confident_W0_W6.jpg`.

W 6 is the largest value at which the hands stay off the thighs in the idle and the walk with room to spare and the run
keeps its hands apart; at 8 the running hands nearly meet in front of the belt (sheet 03 was rendered at 8 first).

## What I saw at W 6 in Blender (first version)

- Idle and walk, front and back, timid and confident: the arms hang beside the trunk, the hands beside the thighs; a
  narrow gap stays between elbow and waist (6 cm against 9), which a relaxed arm has. No arm in the trunk, no pinched
  shoulder: the turn is 6 degrees at the joint and the shoulder cap keeps its shape in the renders.
- Run: the hands swing 4 cm nearer each other than on master; at the one nearest frame a wrist brushes the belly by the
  model's count (0.4 cm, 2 of 174 frames).
- Fists, sword, cast: the clips hold the hands in front of the belly at the wind-up already on master; W 6 brings them
  about 5 cm nearer each other there (sheet 04: in the fist swing's wind-up the hands overlap). **Below bar, and not
  curable by data**: see the code need.

## Code need (asked for on 23 Nov 09:15; delivered the same day as PR #226)

The posture row is applied whole in every state (`DinkBodyAnimInstance.cpp`, after the action blend). Wanted: W (only W,
not the chest and head values) scaled by `1 - action weight` and by about `1 - 0.7 * run blend`. Then W can go to 9 or
10 for the idle and the walk (elbow 5 cm, hand 1 cm off the thigh) without touching the run and the attacks. A test can
read `arm_clearance.py`'s numbers.

## Not seen, not checked

- Seen in the running game on 23 Nov 2026: see the section at the top.
- The Blender poses carry no twist (hand and forearm roll are the rest pose's), no cloth or hair motion, and the death
  clip `Death_436` and the turn were not posed (the trace has no death; the turn frames are walk frames).
- A weapon in the hand (#202) was not looked at with the new arm carriage.
- Found on the way, not changed: from behind at 7 m Dink's hair ends high; the back of his head up to ear level is bare
  pale skin (frames 01, rows 3 and 4). Queue row AN-07.

## Tests and probe

Headless, copy `Saved/FableC`, master 78867e7b + this row + the Mother and Milder branches (tested together): build `BUILD OK ... 0 warnings`; world regenerated with `--export` after `rm -rf Content/Dink/_Generated`.
- `Dink.Animation+Dink.Art+Dink.Movement`: TESTS PASSED 101/101 (5 with warnings) in 147 s.
- `Dink.Gameplay.Probe`: TESTS PASSED 29/29 in 714 s; all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 cff64df9d1 ... Ch20 b27010b31e).
- `Scripts/tests/test_arm_clearance.py`: 3 OK.

**Repeated on master 6e3d4f991 on 23 Nov 2026** (copy `Saved/FableC`; this PR as it now stands together with the stream's other drafts #217, #219, #220, #223): clean build `BUILD OK: DinkRemasterEditor Linux Development in 167s (Result: Succeeded; 0 warnings)`; world regenerated; imports `-nullrhi` with 0 warnings; `Dink.Animation+Dink.Art+Dink.Movement`: TESTS PASSED 107/107 (5 with warnings) in 129 s; `Dink.Gameplay.Probe`: TESTS PASSED 29/29 (1 with warnings) in 561 s; all twenty chapter md5s equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master (Ch1 cff64df9d1 ... Ch20 b27010b31e). Kernel log: 0 Oops.
