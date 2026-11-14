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

---

# Pass 2 (12 Nov 2026, after the owner played pass 1)

Owner: "the initial stance seems odd and the walking looks stiff and strange. also, character default to running when it should be walking. the mom is running and stuttering more. I believe before she was more smooth in movement but was walking at run speed. resolve issues."

Sections 1 to 9 above describe pass 1 as it was merged. Where pass 2 changed something, this part is the current truth.

## P2.1 Root causes

| Complaint | Cause |
|---|---|
| Mother runs and stutters more | Two things. (a) The scripted position itself is stepped: the brains move a sprite one whole pixel (4.4 cm in her house) on 60 Hz engine frames, and those frames do not line up with rendered frames, so a body glued to it stands still on some frames and jumps on others (at 144 fps it stands still on 58% of frames; this was already so before pass 1, hidden by her speed). (b) Pass 1's trailing follower made it worse: her wandering brain kept the script moving at 262 cm/s, the body walked at 125 cm/s until it trailed by 126 cm, then sped up to the script's speed, then slowed again when the script paused: a speed that swung between a walk and a run (deviation about 20 cm/s on top of the 250 cm/s mean in the test below), with the facing turning towards wherever the script had got to. |
| Odd initial stance, stiff strange walk | Pass 1 replaced the template's motion-capture idle, walk and run with clips generated by code. The generated idle (`Idle_Timid` at level 1) stood hunched with the hands hanging in front of the thighs, and the generated walk had a rigid trunk and a steady head. It was not the attack guard and not a stuck blend: it was the authored level-1 stand pose. |
| Runs by default | The pawn's top speed was 600 cm/s unless Shift was held (Shift = walk at 200). |

## P2.2 What changed

### NPC pace at the source (`dink.Npc.HumanPace`)
- `Content/Dink/Data/Gameplay/npc_pace.json` lists classes of sprites (by brain or by script) with a world walking speed per point of `sp_speed` and a cap: townsfolk (brain 16, Mother included) 120 cm/s capped at 170, Milder (`s1-bul`) 135 capped at 200.
- `UDinkGameplay::PaceScale` turns that into the share of the original speed for the sprite's screen (120 / 262.5 = 0.457 in Dink's house, 120 / 593 = 0.20 outdoors): the same world pace indoors and out. It is never above 1.
- Scripted moves (`move`, `move_stop`): `UDinkDirector::StepMove` multiplies the speed by the share. The move ends at the same pixel, later; scripts waiting on it resume then.
- Brain movement (wandering): a paced sprite's brain takes only that share of the 60 Hz frames (`FDinkSprite::PaceCarry`). Everything it does on a frame is taken or skipped together, so the original logic is unchanged, only slower.
- Dink himself (sprite 1) is never paced.
- Modes: 0 original speed; 1 (default) paced in the rendered game, original speed during automated tests and in headless runs; 2 paced everywhere. So human play gets the walking pace and the bot's recorded timings stay as they were.

### Continuous presentation (`FDinkBodySmoother`)
- The trailing follower of pass 1 is removed. The body is shown at a critically damped average of the scripted position (`dink.Npc.SmoothTime`, 0.18 s): steady stepped movement becomes steady motion, starts and stops become ramps of about 0.3 s, and the body trails by speed times the smoothing time (about 20 cm at her walk). There is no catch-up and the body never moves faster than the script. The facing eases at `dink.Npc.TurnRateDeg` and follows the direction of travel while moving.
- The interaction capsule stays on the scripted position.

### Dink walks by default
- Before: 600 cm/s by default, 200 cm/s with Shift. Now, for the player's own input: 170 cm/s by default, 600 cm/s while Left Shift or the left shoulder button is held, with the top speed easing between the two at 900 cm/s per second (`dink.Hero.GaitChangeRate`) and the gait blending with it. `dink.Hero.RunByDefault 1` makes run the default and the key walk.
- Movement that does not come from the player's controls (the bot, `dink.WalkTo`, tests that call `AddMovementInput`) keeps exactly 600 cm/s (`ADinkGreyboxCharacter::IsHumanSteering`).

### Motion-capture locomotion
- `Content/Dink/Data/Art/animation_natural.json` maps idle, walk, run, jump, fall and land of the hero, Mother and Milder to the engine template's motion-capture clips (`MM_Idle`, `MF_Unarmed_Walk_Fwd`, `MF_Unarmed_Jog_Fwd`, `MM_Jump`, `MM_Fall_Loop`, `MM_Land`), played by `UDinkBodyAnimInstance`. The generated locomotion clips of pass 1 are dropped from the runtime (`dink.BodyAnimation 2` plays them, for comparison).
- The walk clip was captured at about 273 cm/s (two gait cycles in 1.5 s), the jog at 600 cm/s (three cycles). Between them the two are mixed in phase and the cadence follows the distance covered. Below the walk clip's speed the walk is mixed with the standing pose and slowed; the mix covers the 2.2nd power of its weight in stride (measured on the posed mesh), and the cadence is set so that cadence times covered stride equals the speed. At Dink's 170 cm/s that is 94% walk at 0.96 cycles per second; at Mother's 120 cm/s 89% walk at 0.75.
- Personality is a light posture layer over the clips, in degrees, mixed by confidence: at level 1 the chest is rounded forward 7, the head lowered 7, each shoulder drawn forward 7; at full confidence nothing. Mother has 2, 2, 3. It is applied to bones in mesh space after the clips.
- The pose's root is always the reference root, so a clip's own travel never moves the mesh off the capsule.
- The template also has motion-capture attacks (`MM_Attack_01` to `03`, `MM_ChargedAttack`). They were measured and not used: their blow lands 0.41 to 1.1 s after the start and they lunge 0.9 to 2.2 m by root motion, while gameplay lands the hit at 175 ms and does not move the pawn. Using them would mean changing gameplay timing.

### Attacks and gestures (still generated clips)
- Fist combo: a wider stance that appears only during the attack (lead foot 30 to 41 cm forward and 7.5 cm out, pelvis dropping 3.5 to 5 cm at contact); `Fist_Swing_Timid` is now a wide arm-led swing (wrist 0.67 m ahead of the chest at contact, was 0.44); `Fist_Jab_Timid` keeps a small flinch with the face on the target.
- `Hurt` is a recoil with a turn away and one loose arm, not a guard.
- New: `Bow_Draw` (held on its last frame while the bow is drawn), `Bow_Release`, `Cast` (open-palm thrust). The bow's `activate_bow` and release and the magic key now play them; before they played nothing (pass 1) or a punch (before pass 1).

## P2.3 Numbers

### Mother's movement (`Dink.Animation.NpcSmoothPresentation`, `Dink.Art.PlayerAction...`)
Speed of the shown body, frame to frame, while the script walks her steadily east (cm/s; "standing still" is the share of rendered frames on which the body did not move at all):

| Rendered at | Before pass 1: body glued, 262 cm/s | Pass 1: trailing follower | Pass 2: 120 cm/s, smoothed |
|---|---|---|---|
| 60 fps | deviation 115, worst change 525, standing still 10% | deviation 20, worst change 7 | deviation 2.9, worst change 6.1, never still |
| 144 fps | deviation 310, worst change 630, standing still 58% | deviation 22, worst change 3 | deviation 2.3, worst change 2.4, never still |
| 47 fps | deviation 92, worst change 206 | deviation 22, worst change 9 | deviation 2.7, worst change 5.7, never still |

(The pass 1 figure is the speed swinging between her walk and the script's speed, on a mean of 250 cm/s. A paced script shown with a glued body would still be stepped: deviation 101 to 247.)

- Her opening walk (43 px, 1.88 m): the script now takes 1.57 s at 120 cm/s (0.72 s at the original speed). Body speed every 0.2 s: 81, 112, 118, 119, 120, 120, 120, 111, 30, 6, 1, 0 cm/s: a ramp up, a constant walk, a ramp down. Peak 120, arrives after 1.95 s, trails the script by at most 20 cm.
- Wandering for 20 s with the pace on (the real brain, in PIE): fastest second 28.3 px = 124 cm/s (original: 60 px = 263 cm/s), straight or diagonal.
- A paced `move_stop` of 43 px ends at its stop pixel after 1.57 s.

### Dink's speeds
| | Before | Now |
|---|---|---|
| Player's input, no key | 600 cm/s (run) | 170 cm/s (walk) |
| Player's input, Left Shift / left shoulder held | 200 cm/s (walk) | 600 cm/s (run), top speed eased at 900 cm/s per second |
| Bot, `dink.WalkTo`, direct movement input | 600 cm/s | 600 cm/s, unchanged |

### Foot sliding in engine (flat-foot test: heel and ball both on the ground in two consecutive 60 Hz frames; cm per frame)
| Speed cm/s | Old blend space: median / mean / net | Pass 2: median / mean / net |
|---|---|---|
| 120 (Mother) | not measured | 0.51 / 0.98 / 0.04 |
| 170 (Dink's walk) | not measured | 0.49 / 0.96 / 0.04 |
| 200 | 0.49 / 1.68 / 1.28 | 0.47 / 0.82 / -0.10 |
| 262.5 | 0.19 / 1.14 / 0.95 | not measured |
| 300 | not measured | 0.29 / 0.30 / -0.27 |
| 600 (run) | 1.15 / 1.08 / 0.10 | 1.14 / 1.14 / 0.26 |

"Net" is the average signed drift: the stride not matching the speed. The old blend space slid about 1 cm per frame net at walking speeds; pass 2 is within 0.3. What remains in the median and mean is the motion capture itself (a real foot is not perfectly still, and the mix with the standing pose at slow speeds adds a little). Pass 1's generated clips measured 0.03 to 0.11 with the stricter test of that time; they were steadier at the foot and worse everywhere else. These numbers were taken before Mother's shorter-step setting and are for the hero's setting.

### Probe (bot) parity
Automated runs use the original NPC speed (see P2.2) and the bot is not a person steering, so nothing the bot meets changes. `Scripts/test.sh Dink.Gameplay.Probe` against plain master: the same 15 of 29 pass, the same 14 fail, and the seven traces that exist have the md5 sums listed in section 5, unchanged. So the preferred outcome holds: human play gets the believable pace, parity runs stay byte-identical. The probe was not run with the pace forced on (`dink.Npc.HumanPace 2`); chapters would then differ in NPC arrival times.

## P2.4 Side by side in the engine

`Scripts/AnimationQA/capture_all.sh <tag> [engine args]` photographs the running game at fixed game-time steps for one animation path; `Scripts/AnimationQA/compare.py` stacks paths. Rows top to bottom: the old path (`dink.BodyAnimation 0`: template blueprint plus the old whole-mesh posture), pass 1 (`2`: generated clips), pass 2 (`1`). All at level 1, the same speeds (walk 170 cm/s, run 600 cm/s).

| File (in `Docs/AnimationPass/`) | What it shows |
|---|---|
| `pass2_compare_idle.png` | Standing, side on, three frames 1 s apart |
| `pass2_compare_walk.png` | Walk at 170 cm/s, 0.05 s per tile |
| `pass2_compare_run.png` | Run at 600 cm/s |
| `pass2_compare_transition.png` | Walk to run, 0.1 s per tile |
| `pass2_compare_start_stop.png` | Pass 2 only: standing, turning and setting off |
| `pass2_compare_mother.png` | Pass 2 only: Mother wandering in her house, 0.5 s per tile |
| `pass2_engine_attack_combo.png` | Pass 2 only: jab, cross, swing, recovery |

Review of these strips:
- Idle: the old path stands with the head bowed well down and the arms hanging forward; pass 1 stands bolt upright with straight arms; pass 2 stands relaxed with the arms at the sides and the head a little down. Pass 2 is the most natural of the three.
- Walk: the old path walks with the head bowed; pass 1 takes small stiff steps with the arms nearly still; pass 2 has a full arm swing, a longer stride and an upright trunk. Pass 2 is the best of the three.
- Run and transition: pass 2 and the old path are the same motion capture and look alike; pass 1 is stiffer. Pass 2 is equal to the old path here, not better, apart from the old whole-mesh wobble being gone, which does not show in still frames.
- Mother: she now crosses the room in small regular steps and stands relaxed between walks.

## P2.5 Tests

- New or rewritten: `Dink.Animation.NpcSmoothPresentation` (steady stepped movement is shown steady at 47, 60 and 144 fps; ramp, hold, ramp of her opening walk; pause, warp, turning), `Dink.Movement.PlayableControls` (direct input keeps 600 cm/s; the player's input walks at 170; Shift runs with an eased change; release walks again; the run-by-default setting; steering ends), `Dink.Art.PlayerAction...` (pace off by default in automation; pace table values; the same world pace indoors and outdoors; Dink never paced; a paced `move_stop` ends at its pixel later; Mother's real brain wandering at the pace; cast and bow clips; foot sliding with the flat-foot test), `Dink.Animation.GaitBlend` (cadence times covered stride equals speed, with the slow-walk law), `Dink.Animation.NaturalClipSurvey` (prints length, cycles, phase and reach of the template clips).

## P2.6 What the last review still faults

- Mother carries her arms away from her body while walking and her stride is long for a woman in a long skirt: the clip is a tall mannequin's walk. The posture layer brings the arms in 12 degrees and her setting shortens the step, and it is still visible. The skirt spreads with each step. A walk captured or authored for her would be the real fix.
- Mother's and Dink's slow walks mix the walk clip with the standing pose; the planted foot wobbles about half a centimetre per frame (no net slide).
- Dink's level-1 posture is a 7 degree round of the chest, head and shoulders on top of a confident mannequin's motion capture: he reads as slightly downcast, not as an awkward farm lad. No restless hands, no uneven step. The personality is thinner than the owner's original brief for hero growth.
- Run and jump are the template's as they always were; nothing was improved there.
- No start, stop or turn-in-place clips: starting and stopping is the walk blending in and out over the acceleration, and the body turns at the capsule's rate.
- Attacks, from the Blender strips of pass 2 (`Strips/hero_attack2/`), not re-captured in the engine after the revision except the combo: the stance is wider but still narrower than a trained one (about 26 cm between the feet from the front); `Fist_Cross_Timid`'s wind-up is exaggerated; `Fist_Swing_Timid` now reads as a haymaker but the off arm is stiff and the legs nearly cross in the catch step; `Hurt` is closer to "whoa" than to a pained flinch; `Bow_Draw` reads as an archer but the string elbow rides very high and there is no bow in the hand; `Cast` is a plain open-palm thrust. `Fist_Cross_Confident` and the final `Hurt` strips were rendered but not looked at.
- Bow, cast, hurt, stumble and jump were not captured in the engine.
- The feet of an attack clip blend from and to the motion-capture stance, whose foot positions differ slightly from the generated stand pose: a small foot shuffle at the start and end of an attack is likely and was not measured.

## P2.7 Not done

- Other townsfolk are still picture cards; they get the pace but not a body.
- The probe with the pace forced on.
- A gamepad stick threshold for running (the left shoulder button is the run key).
- Sword cuts are unchanged placeholders.

# Pass 3 (13 Nov 2026, after the owner played master cb842dd2)

Owner: "improve the mother's stuttered walk."

## P3.1 Root cause

Pass 2's smoother was correct and was still shown wrong. The body's offset from its actor was computed in the component's tick; the scripts move the actor afterwards in the same frame (the story subsystem is a tickable object, ticked after the actor tick groups). The drawn body was therefore the new scripted position plus the previous frame's offset: forward with every scripted pixel, back on the next frame, and a one-frame flip to the new facing at every turn. P2.3's table measured the smoother's own output, not what was drawn, so it showed a deviation of 2.9 cm/s for a walk that was drawn with 297.

## P3.2 What changed

`UDinkHumanoidComponent::PresentBody`, run again from a tick function in `TG_PostUpdateWork`. Nothing else: script, brain, pace and collision are as they were.

## P3.3 Numbers (running game, her own wandering; `Docs/Verification/MotherWalk_13Nov2026/`)

| Rendered at | Before: deviation of the shown speed, frames moving backwards, one-frame facing flips | After |
|---|---|---|
| 60 fps, 45 s | 297.0 cm/s, 32.2%, 12 | 3.3 cm/s, 0.0%, 0 |
| 83 fps, 30 s | 348.6 cm/s, 22.8%, 16 | 4.0 cm/s, 0.0%, 0 |

## P3.4 Test

`Dink.Animation.NpcShownMotion`: the drawn transform at the end of every frame of a PIE session; with `dink.Npc.LatePresent 0` it must find the defect, with the fix it must not.

## P3.5 Not done

Picture-card townsfolk and creature bodies are still glued to the scripted position. The late start of an about-turn (P2.2's rule that the body faces its travel direction above 25 cm/s) is unchanged.
