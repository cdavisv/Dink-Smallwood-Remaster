# The armed hand closes round the grip and carries the weapon on guard (art row AN-05), 23 November 2026

SEEN IN THE GAME on 23 November (section "In-game look" at the end, sheet 05); what follows was written before that look, when no rendered Unreal run was allowed on this machine. The pictures are Blender renders on the CPU (Cycles) of the hero's source mesh with each weapon placed by its `hero_weapons.json` row; the numbers are from Blender and from the engine's own headless test.

## What was wrong (master)

- `01_before_open_hand_and_rejected_fist.jpg`, upper row: the armed hand is the idle's half open hand; the grip lies in it loose.
- `04_before_carry_hanging_arm.jpg`, right column: the arm hangs, the blade lies level at the hip and points forward and across the body; the bow lies level with its string across the forearm.
- 1997 (`ref_1997_sword_idle_x4.png`, `ref_1997_bow_idle_x4.png`: `graphics/dink/sword/idle` and `bow/idle`, frame 1 of the four directions): the armed Dink stands ON GUARD. The forearm is raised, the hand at the waist, the blade up and out to his side; the bow stands upright in his left hand. The queue row said "the 1997 pictures carry the sword low and relaxed": they do not.

## What changed

- **Grip pose** (`AnimationPassV1/Tools/rig.py` `GRIP`, `GRIP_THUMB`, `Pose.grip`; clips `Grip_R`, `Grip_L`): per-joint finger angles fitted to the handle where the weapon row puts it (a grip 2.6 to 3.3 cm thick across the palm), the thumb swung out of the palm and laid over the handle.
  The first version of these clips (a fist, curl 0.92; never looked at before today) is REJECTED: `01_...jpg`, lower row. Its last finger joints lay 0.7 to 1.1 cm from the grip's axis, inside a handle of 1.3 to 1.7 cm radius, and the thumb's knuckle lay 1.3 cm from the axis.
  Now every finger joint past the knuckle lies 2.3 to 3.1 cm from the axis (a finger's half thickness off the handle): `02_hand_round_the_grip_sword_axe_bow.jpg` (longsword, axe, wooden bow; three views each).
- **Carry** (`clips_attacks.py` `CARRY`, in the same two clips): the arm on guard, forearm about level at the waist, the blade 61 degrees up, leaning 0.42 outward and 0.23 forward. `03_guard_carry_vs_1997_sword_axe_bow.jpg`: the four 1997 directions above the same four views of the remaster's hero (sword, axe, bow).
- **Runtime** (`UDinkBodyAnimInstance::SetGrip`, called by `DinkHeroWeapons::Apply` for as long as a weapon mesh is in the hand): the last frame of the pose clip goes on the fifteen finger bones of that hand under every clip the body plays, and on that arm (upper arm, forearm, hand, twist bones) while no action plays. An action (cut, bow draw, hurt, cast ...) has its own arm and wrist for as long as it is blended in. Eased over 0.12 s. `dink.Anim.WeaponCarry 0`: the hand only closes. Presentation only; nothing of the simulation is read or changed.

## How it was checked (headless)

- `Dink.Art.HeroWeapon.GripClosesTheHand` (new): the clips close the named hand and leave the other; a posed hero body gets the grip pose's finger tips exactly (under 0.1 cm) on the hand that holds, the idle's on the other; with the longsword, the axe and the bow where their rows put them, every thumb, index, middle, ring and pinky joint 02 and 03 lies 1.9 to 3.4 cm from the grip's axis; on guard the blade's up-component is over 0.75 and the hand 12 cm or more above where it hangs; arming a sword sets the right hand, a bow the left, fists none.
  Engine numbers of that run (cm; x along the grip, r from its axis), the same for the longsword and the axe on `hand_r` and the bow on `hand_l`: thumb_02 r 3.1, thumb_03 r 2.7, index_02 r 2.7, index_03 r 2.3, middle_02 r 2.8, middle_03 r 2.4, ring_02 r 2.7, ring_03 r 2.5, pinky_02 r 2.6, pinky_03 r 2.4. Carry, longsword: blade up-component 0.84 with the grip 105 cm above the ground on guard; 0.29 at 81 cm with `dink.Anim.WeaponCarry 0`.
  The finger distances are, digit for digit, the ones Blender printed for the pictures: the weapon stands in the pictures where the engine puts it. The guard differs a little (Blender 0.875 at 110 cm on the stand pose): in the engine the arm hangs off the playing idle's shoulder.
- On master 9ada93f1a (#160 merged) with this branch and the six other drafts of the stream together (copy `Saved/FableD`; its C++ and plugin sources compared file by file with the tree: equal, no file more): clean build, 0 warnings (284 actions; `DinkBodyAnimInstance.cpp`, `DinkHeroWeapon.cpp`, `DinkHeroWeaponTests.cpp` are in the log); world regenerated; kits and the animation pass imported with `-nullrhi` (35 clips, shared skeleton unchanged); `Dink.Art+Dink.Animation+Dink.Gameplay.Probe` 118/118 passed in 734 s (run `fx3_art_anim_probe5`); the twenty probe md5s equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master. Before #160, on 78867e7b: 118/118 in 1036 s, md5s equal; `Dink.Art.HeroWeapon` alone 2/2.
- NOT built alone on master: this branch's C++ (four files) was compiled and tested only together with the other drafts' C++ (`DinkArtFamilySubsystem.*`, `DinkArtFamilyTests.cpp`); the two sets share no file. The python suite has no test of the changed files (`AnimationPassV1/Tools`); `Scripts/check_public_paths.py` and `Scripts/verify_sources.py --metadata-only` pass.

## Not seen, to look for in the game (line on the pending list)

- Everything, in the game's own light and camera: the hand round each of the six weapons, the guard carry standing, walking and running (the weapon arm does not swing; is that right at a run?), the blend into and out of a cut and a bow draw, the left hand and its bow.
- The bow's string passes close to the forearm in the Blender views (`02_...jpg`, lower row): may touch the sleeve.
- The axe is held at the end of its haft with the head up beside the head: fits a thrown axe, unseen.
- The hand at the grip is the hero's mesh as skinned: finger skin may crease or pass through itself at these angles (the Blender close-ups show none).
- NPCs and Milder do not use this layer (only the hero's weapon subsystem calls it).

## Not done

- 1997 shows a quiver of red-fletched arrows on Dink's back and an arrow across the bow while a bow is armed (`ref_1997_bow_idle_x4.png`). No such mesh exists.
- The bow does not bend with `Bow_Draw`; the axe has no throw clip (AN-06).

## In-game look, 23 November 2026 (rendered work allowed again)

Captured offscreen in the running game on master `430fd81d2` + this change (copy `Saved/FableD`, the integration tree, which also
holds the bow draft: the quiver and the arrow in the bow rows are that draft's), 71 frames `Saved/PhotorealPass/fx3/E_*.png`.

| sheet | what it shows | what I see |
|---|---|---|
| `05_game_23nov_grip_and_guard.jpg` | rows: longsword, claw sword, axe, bow: on guard from the front, the side and behind, two close views of the hand, and `dink.Anim.WeaponCarry 0`; then a cut at quarter speed, the walk, fists, the light sword | the hand is closed round every grip, thumb over the handle, nothing through the fingers at this size (sword and axe close-ups). On guard the forearm is raised and the blade stands up and forward of him as in the 1997 idle pictures (side views); with the carry off the arm hangs and the blade points down, the hand still closed. The cut leaves the guard and comes back without a jump in the frames caught (0.05 s apart at quarter speed). The bow stands upright in the left hand. Fists: open hands |

Seen and NOT of this change: the polished blades read pale green on the grass (they mirror it; the weapons kit's steel). The two close
cameras of the bow rows missed the bow hand (they show his elbow); the walk was caught only from the play camera's distance, where the
carried arm cannot be judged for stiffness.
