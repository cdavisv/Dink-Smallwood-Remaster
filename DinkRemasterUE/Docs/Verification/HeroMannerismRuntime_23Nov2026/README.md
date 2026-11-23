# Hero mannerisms: the runtime for the fifteen clips of PR #218 (23 Nov 2026)

PR #218 (art-people-3) delivers the ART half of the local branch anim/hero-mannerisms (14 Nov): AN_Posture_Timid /
_Confident, AN_RunArms_Timid, AN_Trip_Walk/_Run, AN_Jump_Timid, AN_Botch_Stagger/_Faceplant, four AN_Fidget_*, three
AN_Sword_*_Timid. Nothing played them. This is the C++ half of that branch, brought onto master.

## What it is (from anim/hero-mannerisms, 3-way merged onto master 9ada93f1a)
- FDinkHeroPhysicality: confidence-scaled clumsiness: toe catches at a walk and at a run, botched landings (stagger, or
  flat on his face), idle fidgets, the after-swing wobble; nothing clumsy starts in or within 6 s of a fight; its own
  random stream (never the simulation's).
- UDinkBodyAnimInstance: the additive posture (Posture_Timid/_Confident by confidence), the timid gait layer (arms that
  hang, uneven trunk rock, head bob) and RunArms_Timid at a run; Botch/Trip/Fidget play as actions; old action clips keep
  part of the posture (PostureShareFor); posture_off_s/on_s of a clip (the faceplant) lets it go while he lies.
- ADinkGreyboxCharacter::UpdateMannerisms / PlayBotch, console `dink.Hero.Mannerism <trip|stagger|faceplant|scratch|
  scuff|nose|proud|wobble|jump|jumpclean|jumpstagger|jumpfaceplant>` (review).
- GATED ON THE CLIPS: the layer is on only when the library holds Posture_Timid and Posture_Confident (HasMannerisms);
  without #218 the game is as on master except the confidence-scaled landing chance (LandingStumbleChance .2 -> .3 x
  clumsiness, a Stumble clip as before) and the fight quiet.

## Changes against the 14 Nov branch
- The posture row of animation_natural.json keeps its W (upper arms in, A102 / #217) under the additive posture; the
  clips own only the stoop (X, Y, Z set to 0 when the layer is on). The answer to #218's question "which owns the stoop".
- The mannerisms' own slow-walk cadence power (FDinkMannerMaths::CadencePower) is NOT applied: since #205 the leg
  layer's gait style already gives the lad shorter, quicker steps, and both together made planted feet slide
  (Dink.Animation.Legs.InEngine: 0.252 cm/frame against 0.25). The function stays (tested numbers) for reference.
- RotateInMeshSpace calls follow master's signature; the lean (with the gait roll) feeds master's lean bones.
- The 14 Nov test failure (Dink.Animation.HeroMannerisms 6/7) does not occur on master: 1/1 (see PR text).

## Proof (headless, copy Saved/ArtHooks23Nov: master + this branch + #217's hook branch + #218's clips imported)
- Dink.Animation.HeroMannerisms (rates fall with confidence, fight quiet, catch cadence loses no ground, ...).
- Dink.Animation.HeroMannerismLayerGatedOnClips (on exactly with both posture clips; off without; standing / running
  lad / hero / wall scale).
- Dink.Animation (all, incl. Legs.InEngine), full Dink suite and probe: see the PR text.

## Not checked
- Looks in the rendered game (the 14 Nov sheets were on the old leg-less animation; RENDER_PENDING line added).
- How often the moments come up in real play.
