# Animation pass: hero and NPC movement, melee attacks (12 Nov 2026)

Owner feedback after a test build: "dink's mom moves to fast, dinks movements are odd and still what codex had done. Go back through dink's goofy, aloof mannerisms and remodel them to be more realistic. also improve his attacks. It's like a quick little jab and if you hold it the attack gets spammed."

This file records what existed, what caused each complaint, what changed and what is still weak. Paths are relative to `DinkRemasterUE/`.

## 1. What existed (master e3dc25a7)

### Hero
- `Plugins/DinkCore/Source/DinkCore/Public/Greybox/DinkGreyboxCharacter.h` (`ADinkGreyboxCharacter`): the engine third-person character. Runs at 600 cm/s, walks at 200 cm/s (Shift), jump velocity 280 to 340 cm/s by confidence.
- Animation: the engine template's animation blueprint `ABP_Unarmed` and blend space `BS_Idle_Walk_Run` (Epic mannequin clips, copied by `Scripts/copy_template_content.sh`, git-ignored). No project-authored locomotion.
- Hero growth (PR #47/#48), `Public/DinkHeroPhysicality.h`: confidence from level, strength and defense. It drove the look by rotating and offsetting the WHOLE MESH every frame: a hunch pitch, a side-to-side sway with unequal left/right beats, a "flop" and a "boing-boing" bounce while running, shoulders lagging corners, a lurch on stops, a pinwheeling takeoff flail, landing stumbles and a 1.6 s faceplant ("pratfall"). `Public/DinkBodyDynamics.h` added a spring lean, also on the whole mesh. This is the "odd, goofy" motion: the legs played a clean mannequin run while the body was rocked like a board on top of it, and rotating the mesh about its origin lifts and drags the feet.
- Mesh width scale 0.86 to 1.0 with confidence and the jump tuning are part of hero growth and were kept.

### Attacks
- Input: `Plugins/DinkNarrative/Source/DinkNarrative/Private/DinkNarrativePresentation.cpp`, a Slate input pre-processor. F or Left Ctrl called `UDinkGameplay::PlayerAttack()` on every key-down event that Slate did not flag as a repeat. There was no key-up handling at all.
- `UDinkGameplay::PlayerAttack()` (`Private/DinkGameplay.cpp`) runs the armed item's DinkC `use`. For fists (`bin/dink/story/item-fst.c`): `sp_seq(1, 100 + dir)`, `sp_nocontrol(1, 1)`. `OnSequenceSet` schedules the hit at the special frame of the sequence (`HitFrameDelayMs`: 75 + 100 = 175 ms; the sequence is 400 ms long) and asked the art layer to play a clip.
- The original engine ignores the attack key while `nocontrol` is set, that is until the 400 ms sequence has played. The remaster records `nocontrol` but never modelled it for the pawn ("nocontrol is not modelled for the pawn" in `DinkGameplay.cpp`). So nothing limited how often an attack could start.
- Clip: one 0.4 s clip, `AN_Dink_Fist` (`SourceAssets/Art/Characters/Animations/Unarmed`), played by `UDinkPlayerActionComponent` by switching the whole mesh from the animation blueprint to a single-node player and back. The feet were keyed still, the legs froze if he was running, and the switch popped with no blend. The same clip played for every weapon, and also when casting a spell, because the sword and the fireball scripts set the same sequence numbers.
- Sword (`item-sw1.c` and others), bow (`item-b1.c`, `activate_bow`) and magic (`item-fb.c`) exist in gameplay. No sword, bow or casting animation existed and no weapon mesh is attached to the hand.

### NPCs
- `UDinkHumanoidComponent` (`Public/DinkHumanoidComponent.h`): a skeletal mesh on the original script actor, driven by `BS_Idle_Walk_Run` with the observed speed as the blend parameter and a play rate of `clamp(speed / max, 1, 3)`.
- Only two NPCs have skeletal bodies: Mother (placement `S001_P26`) and Milder (script profile `s1-bul`), listed in `Content/Dink/Data/Art/characters.json`. Every other townsperson is still a picture card.
- Speed mapping: `UDinkDirector::StepMove` and the brains move sprites in screen pixels: `sp_speed` 1 is 60 px/s (1 px per 60 Hz frame); `sp_timing` gates how often a brain thinks; `move()`/`move_stop()` end at a pixel coordinate. Pixels become centimetres through the screen's layout quad (`DinkLayout`). Dink's house is laid out at 4.375 cm per pixel, the outdoor screens at about 9.9 cm per pixel.

### Rig, clips, sources
- One skeleton for Dink, Mother and Milder: the Epic-compatible mannequin skeleton, 89 bones used by the meshes (161 in the skeleton asset). `bind_pose_differences` is empty for all three.
- `Scripts/hero_source_history.py` and `Scripts/verify_sources.py`: the hero's mesh sources are pinned by hash and admit exactly one later revision per accepted path. This pass adds new paths only (`SourceAssets/Art/Characters/Animations/AnimationPassV1`) and does not touch any pinned file.

### Tests that pinned the old behaviour
- `Dink.Movement.ClumsyHero`, `ClumsyTransitions`, `ClumsyFrameRates`, `HeroGrowth` (numbers of the whole-mesh wobble, flail and pratfall), `Dink.Movement.WallClearance`, `Dink.Art.PlayerAction.ApprovedFistTimingSaveAndLocomotion` (the single-node fist clip). All were rewritten for the new behaviour; see section 5.
- `Dink.Gameplay.Probe.*` (the bot): calls `PlayerAttack()` directly and records every event in a trace.

## 2. Root causes

| Complaint | Cause |
|---|---|
| Holding the attack key spams attacks | No rule existed. `PlayerAttack` restarts the attack on every key-down, the original's 400 ms `nocontrol` lock was never modelled, and the only protection was Slate's repeat flag. Any key-down that arrives without that flag restarts the clip from frame 0, and each restart also cancels the pending hit, so a fast spam animates without landing a blow. Which path let repeats through on the owner's machine was not reproduced here (X11 delivers auto-repeat as release+press pairs, which a toolkit must pair up to flag; that is the likely one); the fix does not depend on it. |
| "A quick little jab" | One 0.4 s clip with still feet and a 75 ms wind-up, hard-switched in and out with no blend, the same for every press and every weapon. |
| Dink's movements are odd | Whole-mesh rocking, bouncing and tipping on top of mannequin clips (see Hero above), not bone-level motion. |
| Mother moves too fast | The script speed is original (60 px/s) but the house is laid out 1.75 times larger than the picture, so 60 px/s is 262 cm/s: a sprint across a kitchen. Her body was glued to that position. On top of it the blend space played a walk/run mix at its own cadence (play rate 1 below its top speed), so her feet slid. Outdoors `sp_speed` 1 is about 590 cm/s. |

## 3. What changed

### A. Attacks
- Input rule (`FDinkAttackGate`, `Public/DinkGameplay.h`; `UDinkGameplay::InputAttackPressed/Released`): **one attack per press. A held key never repeats, at any cadence.** While Dink is locked in an attack (the attack sequence's own length, 400 ms, which is the original's `nocontrol` lock) a press is remembered, one deep, and starts the next attack the moment the lock ends: this is how the combo is chained. The key's release now reaches gameplay too (it lets a drawn bow go, which the keyboard could not do before). A key-down that follows a key-up of the same key within 40 ms is treated as an unflagged auto-repeat.
- `PlayerAttack()`, `PlayerAttackPress()` and the `dink.Attack` console command are unchanged and ungated: the probe bot produces exactly the events it did.
- Gameplay parity: damage, the hit moment (175 ms after the attack starts), reach and script-visible state are unchanged. What changes for a human player: attacks can start at most once per 400 ms, as in the 1997 game. Before, a player could restart the attack on every key press (which cancelled the pending hit when faster than 175 ms). Nothing else.
- Animation: `UDinkPlayerActionComponent` now only chooses a clip and plays it on the body animation instance: `Fist_Jab`, `Fist_Cross`, `Fist_Swing` in turn when attacks follow each other within `dink.Attack.ComboWindowMs` (950 ms from start to start), else the jab again; `Sword_Slash_1`, `Sword_Slash_2`, `Sword_Chop` when a sword script is armed. Each exists as a timid and a confident clip, mixed by hero confidence. The clip blends in over 70 ms, plays on the whole body when standing and on the upper body over the running legs when moving, and is interrupted by the next attack with a short cross-fade. A spell cast and the bow no longer play a punch (they play nothing: no clip exists yet).
- Tunables: `dink.Attack.LockMs` (0 = the sequence's own length), `dink.Attack.BufferPress`, `dink.Attack.ComboWindowMs`, `dink.Attack.BlendInMs`, `dink.Attack.BlendOutMs`.

### B. Hero locomotion and mannerisms
- `UDinkBodyAnimInstance` (`Public/DinkBodyAnimInstance.h`): a native animation instance with no blueprint. Idle, shuffle (90 cm/s), walk (200 cm/s) and run (600 cm/s) are blended by speed and kept in phase; the cycle advances by distance covered over the blended stride, so cadence times stride equals the movement speed at every blend weight. Timid and confident variants of every clip are mixed by confidence. Falling blends to an airborne loop; landing plays a land clip scaled by impact.
- `FDinkHeroPhysicality` no longer moves the mesh. It keeps confidence, the physique scale, a small trunk lean into accelerations, stops and corners (applied to two spine bones), landing impact and the stumble timer. The takeoff flail and the pratfall are gone. A running stumble is now the `Stumble` clip (a toe catch and recovery on the upper body), at a level-1 rate of 0.008 per second of flat-out running (it was 0.035), with a 12 s cooldown, fading to none with confidence. The landing stumble chance went from 0.45 to 0.2.
- A hit that costs life plays `Hurt` (a flinch) when no attack is playing.
- Movement speeds, the capsule, the camera and the jump are unchanged.

### C. NPCs
- `FDinkVisualFollower` (`Public/DinkHumanoidComponent.h`): the body follows the scripted position at the pace of her walk clip (125 cm/s for Mother, 140 cm/s for Milder) with eased starts and stops and an eased facing (300 degrees per second). The scripted position, its timing and its interaction capsule are untouched. The body may trail by up to `dink.Npc.MaxVisualLagCm` (180 cm); beyond 70% of that she speeds up, and at the limit she matches the script's speed with a hurry/run clip whose stride fits it.
- Trade-off: Mother's opening walk (1.88 m, 0.72 s in the script) now takes her body about 1.7 s at a walking pace. On longer scripted walks, and whenever her wandering brain keeps moving, the lag limit is reached and she hurries at the scripted 262 cm/s: a brisk scurry with matching steps instead of a slide. Making her wander slowly everywhere would need the scripted speed itself to change, which changes script timing and the bot's traces; that is an owner decision and was not done.
- Mother and Milder use the `NpcF_*` and `NpcM_*` clips through `"animation_set"` in `characters.json`; the blend space remains the fallback (`dink.BodyAnimation 0`).

## 4. Clips

Source and rebuild instructions: `SourceAssets/Art/Characters/Animations/AnimationPassV1/README.md`. Strips: `SourceAssets/Art/Characters/Animations/AnimationPassV1/Strips/` (`hero_loco`, `hero_attack`, `mother_loco`, `milder_loco`). Per-clip numbers are in `animation_manifest.json` next to them.

| Family | Clips |
|---|---|
| Hero locomotion | `Idle_Timid`, `Idle_Confident` (8 s), `Shuffle` (0.9 m/s), `Walk_Timid`, `Walk_Confident` (2.0 m/s), `Run_Timid`, `Run_Confident` (6.0 m/s), `Jump_Start` (imported, not used by the runtime), `Fall`, `Land` |
| Hero attacks | `Fist_Jab_*`, `Fist_Cross_*`, `Fist_Swing_*` (timid and confident), `Sword_Slash_1`, `Sword_Slash_2`, `Sword_Chop` |
| Hero reactions | `Hurt`, `Stumble` |
| NPC | `NpcF_Idle`, `NpcF_Walk` (1.25 m/s), `NpcF_Hurry` (2.6 m/s), `NpcM_Idle`, `NpcM_Walk` (1.4 m/s), `NpcM_Run` (5.9 m/s) |

## 5. Numbers

### Foot sliding
Planted-foot drift: the heel and ball contact points of the posed foot, in the ground frame of a body travelling at the given speed; a point counts while it is on the ground in two consecutive frames.

Source clips (Blender, per clip, from `animation_manifest.json`): locomotion loops 0.17 to 0.55 cm/s maximum, mean at most 0.008 cm per frame, 0 IK clamps, loop seam 0. Attack clips 1.8 to 8.6 cm/s maximum (31.7 cm/s on `Fist_Swing_Confident`, a heel swivelling on the ball of the foot), `Fist_Swing_Timid` has 2 arm IK clamps of about 1 cm.

In engine (`Dink.Art.PlayerAction.ComboHitTimingInputAndFootSlide`: a bare mesh with the runtime's animation instance, 60 Hz, height-only contact test, cm per frame):

| Speed cm/s | Old blend space, mean / max | New, timid | New, half | New, confident |
|---|---|---|---|---|
| 45 | not measured | 0.19 / 2.2 | 0.22 / 2.4 | 0.25 / 2.8 |
| 90 (shuffle) | not measured | 0.03 / 1.0 | 0.06 / 1.4 | 0.06 / 1.5 |
| 150 | not measured | 0.14 / 2.4 | 0.14 / 2.1 | 0.18 / 2.7 |
| 200 (walk) | 2.60 / 11.1 | 0.08 / 1.7 | 0.10 / 1.6 | 0.11 / 1.4 |
| 262.5 (Mother, scripted) | 2.24 / 14.4 | n/a | n/a | n/a |
| 300 | not measured | 0.58 / 2.2 | 0.51 / 2.0 | 0.54 / 1.8 |
| 450 | not measured | 0.95 / 5.5 | 0.98 / 5.0 | 0.92 / 4.4 |
| 600 (run) | 1.01 / 3.7 | 0.41 / 3.5 | 0.41 / 3.0 | 0.32 / 2.3 |

The old hero figures are the blend space alone; the whole-mesh sway, bounce and offsets that used to be added on top of it are not in that number. The maxima of the new clips are single frames at toe-off and heel strike, where the height-only test still counts a point that has begun to pivot. Speeds between walk and run (300, 450) mix a walk with a run and slide about 0.5 to 1 cm per frame: the pawn only passes through them while accelerating.

### Attack key (same test, real gameplay in PIE)
- Key held for 3 s with auto-repeat key-downs: exactly 1 hit, at 175 ms.
- Pressing and releasing every 100 ms for 2 s: 6 hits at 0.18, 0.59, 1.00, 1.41, 1.82, 2.23 s (one per 400 ms lock plus one tick).
- `PlayerAttack()` twice in a row still restarts at once (the bot's path).

### Mother (`Dink.Animation.NpcFollower`)
- Her opening walk: script 1.88 m in 0.72 s at 262.5 cm/s. Body: peak 125 cm/s, arrives after 1.72 s, trails by at most 116 cm.
- A long scripted walk at 262.5 cm/s: the body trails by 174 cm and then matches the script's speed.

### Probe (bot) parity
`Scripts/test.sh Dink.Gameplay.Probe` on master e3dc25a7 and on this branch, same generated world: 15 of 29 pass in both, the same 14 fail (chapters 7 onward, the known barrel script order problem), and the seven traces that exist have identical md5 sums:

```
c88f756f9eca6a575bd18dea7c915d87  probe_ch2_trace.txt
838adfb3ab9ddde16781862dc36fbb66  probe_ch3_trace.txt
54d8a76e0ad6ca4d24318bb27f165515  probe_ch4_trace.txt
61b022530fff55f70de8d61091ab9550  probe_ch5_trace.txt
a1c2c99e24e2afcbda07abc44560e095  probe_ch6_trace.txt
39138a86db848df0fe5ea89187db9ff6  probe_ch7_trace.txt
b4ad88c02cde75bbe46ed9a705a82649  stonebrook_probe_trace.txt
```

## 6. Tests

- New: `Dink.Animation.AttackGate` (no repeat on hold, one buffered press, lock), `Dink.Animation.Combo`, `Dink.Animation.GaitBlend` (cadence times stride equals speed at every weight), `Dink.Animation.NpcFollower`.
- Rewritten: `Dink.Art.PlayerAction.ComboHitTimingInputAndFootSlide` (clip choice, the 175 ms hit across save and load, the attack key in real gameplay, `sp_speed` 1 = 60 px/s, Mother's body, in-engine foot sliding), `Dink.Movement.ClumsyHero`, `ClumsyTransitions`, `ClumsyFrameRates`, `HeroGrowth` (lean, stumble rate, confidence; no mesh wobble).
- Adjusted: `Dink.Movement.WallClearance` (fixture offset 22 cm), `Dink.Art.HumanoidPresentation.OptionalPlayerMeshKeepsAnimationAndCapsule`, the script character restore test (body animation instead of the blend space play rate).

## 7. Reviewing motion

- Source strips: `SourceAssets/Art/Characters/Animations/AnimationPassV1/Strips/` (rebuild with `Tools/build.py -- --strips`).
- In engine: `python3 -I Scripts/AnimationQA/make_capture.py`, then `Scripts/PhotorealQA/run_capture.sh <absolute path of Saved/AnimationPass/capture/attack_combo.txt>`, then `python3 -I Scripts/AnimationQA/strip.py attack_combo 500,150,780,520`. The capture uses the new review command `dink.TimeDilation 0.1`, so consecutive shots are about 0.05 s of game time apart. `Docs/AnimationPass/engine_attack_combo.png` (jab, cross, swing and recovery of a level-1 Dink, about 0.05 s per tile) and `engine_run.png` are from such a run.

## 8. What the last review still faults

Nothing here should be called finished animation. These are clean, physically consistent procedural clips; the last look at the strips faulted:

- All attacks: the feet stay close together and the knees bent, a crouched shuffle and not a planted fighting stance; weight transfer shows in the pelvis and trunk more than in the legs. The 100 ms of anticipation that the fixed 175 ms hit leaves is very short and may barely register at speed.
- `Fist_Jab_Confident`: clean line, trunk nearly upright, looks posed. `Fist_Jab_Timid`: in engine the ducked, turned-away head at contact looks odd, not just timid.
- `Fist_Swing_Timid` is the weakest clip: at the hit frame the arm is folded across the chest (wrist only 0.44 m ahead), an elbow-led flail and not a wide haymaker, with a cartoonish wind-up. `Fist_Swing_Confident` is a short-range hook.
- Sword cuts: placeholders. One review round, no blade in the hand (no sword mesh is attached in the game), wrist not cocked.
- Walks: the torso is a stiff block, the stance knee never fully straightens, the pelvis drops about 6 cm at double support (the price of 0.8 m steps at 2 m/s), the head is steady to the point of looking mechanical; the timid walk reads dejected as much as timid.
- Runs: the lead leg reaches far ahead with a nearly straight knee (overstriding), forearms sit across the chest, the trunk is stiff; timid and confident differ in posture more than in rhythm.
- Idles: very quiet, close to a held pose with slow drift; no finger life.
- `NpcF_Hurry`: a jog-speed gait in a long skirt cannot look calm; the hem still stretches at the forward leg. Mother's arms hang with little life in `NpcF_Walk`.
- `Hurt` looks like a boxing guard more than a flinch; `Stumble` has a trace of "reaching zombie" and plays on the upper body only (the legs keep running).
- Engine strips exist only for the attack combo and the run; walk, idle, jump, hurt, stumble and the NPC clips were reviewed in Blender only. The timid/confident blend at intermediate confidence was measured for sliding but not looked at.

## 9. Not done

- Bow and magic: no clips (they now play nothing instead of a punch). The bow's draw and release work from the keyboard for the first time (key release reaches gameplay) but have no animation.
- Turn-in-place clips, start and stop clips, strafes (not used by the game), pushing, picking up and talking gestures.
- `Jump_Start` is imported but not played: the jump is an instant launch and a crouch after leaving the ground would look wrong.
- Other townsfolk are still picture cards; only Mother and Milder have bodies.
- The scripted NPC speed itself (60 px/s per `sp_speed` point in rooms laid out 1.75 times larger than the picture) is unchanged; see the trade-off in section 3C.
- A sword mesh in the hand.
