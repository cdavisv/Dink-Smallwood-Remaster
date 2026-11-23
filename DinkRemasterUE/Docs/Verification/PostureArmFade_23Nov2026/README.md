# Posture W gives way to actions and the run (A102 code hook, 23 Nov 2026)

The posture row's fourth value W (animation_natural.json `posture.<set>`, the upper arms brought in towards the trunk)
was applied whole in every state. At W 11 the idle and walk were right in the game (16 Nov) but the jog's bent forearms
and the attack wind-ups laid both hands on the belly, so draft art PR #217 ships W 6 and asked for this hook.

## What changed
- UDinkBodyAnimInstance: W x (1 - X * action weight) x (1 - Y * run share), where the action weight is the strongest
  action clip's weight this frame and the run share is the run gaits' (every gait but the slowest, the walk) part of the
  base pose. X, Y default to 1.0 and 0.7 (the numbers #217 asked for). Only W; chest, head and shoulders unchanged.
- `posture.<set>.arm_fade: [action, run]` in animation_natural.json overrides them per body set (Hero, NpcF, NpcM);
  `[0, 0]` restores the old behaviour. Read by UDinkArtSubsystem::GetAnimationArmFade, set on the hero (character) and
  on NPC bodies (UDinkHumanoidComponent) every frame like the posture itself.
- NpcF (the Mother, W 12) gets the default fade as well: the same hands-on-belly reason in her hurry.
- With this, #217's row can go to W 9-11 for the idle and the walk; the run keeps 0.3 of it.
- Presentation only (anim graph); the probe md5s cannot move.

## Proof
- `Dink.Animation.Posture.ArmFadeRule`: the factor's numbers (0 / full action, 0.3 at a full run, clamping, [0,0]).
- `Dink.Animation.Posture.ArmFadeInEngine`: the hero mesh with the real clip library, W 10: standing and walking
  (150 cm/s) W whole; jogging at 600 cm/s W 3.00 (factor 0.300); back to a stand W whole; during the Land action W
  under 2; after it whole; fade [0,0] keeps W 10 in the jog; W moves the upper arm.
- Build 0 warnings, full Dink suite and probe: see the PR text.

## Not checked
- The look in the rendered game (RENDER_PENDING: #217's capture lines, run with this PR and W raised).
- arm_clearance.py (#217's tool) does not model the fade yet: it measures the run at the full row value.
