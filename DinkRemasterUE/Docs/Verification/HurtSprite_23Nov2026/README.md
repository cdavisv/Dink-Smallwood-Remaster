# dink.HurtSprite: hurt a script-made sprite for a capture (23 Nov 2026)

Asked by the Fable gore streams (Master log 16 Nov 21:50, 23 Nov 09:15): `dink.Hurt` takes only a placement origin, so a
sprite a script makes (Mog of `s3-mog` on SCR_680, whose remains are picture 785) cannot be killed in a capture.

## What changed
- Console `dink.HurtSprite <S680_P12 | handle | script | nearest> <damage>` (DinkNarrativeConsole.cpp). Review only.
- `UDinkGameplay::FindReviewSprite`: a placement origin, a handle, a script name (the live sprite carrying it; the one
  nearest Dink on his screen first; case-insensitive as DinkC) or `nearest` (the live sprite with hitpoints nearest Dink).
- `UDinkGameplay::ReviewBlow`: the tail of `RunThroughTagList` for attacker 1 (run_through_tag_list, D:15520-15590) on one
  target with the given damage instead of the strength roll: hit sound, `target` set on an attacking sprite, `last_hit` 1,
  `hurt_thing`, `random_blood` when it hurt, then the sprite's `hit` with `&enemy_sprite` 1 (so Mog's brain turns, and the
  kill follows on his brain's next think, leaving the corpse as a real blow does). A nohit sprite with a script only gets
  its `hit`; one without a script is not hit.
- Nothing in play or in the probe calls it: the twenty probe md5s cannot move.

Capture recipe for Mog's remains: on SCR_680 after `gobpass` (Mog made by s3-mog): `dink.HurtSprite s3-mog 500`
(or `dink.Sprites` for his handle, then `dink.HurtSprite <handle> 500`).

## Proof
- Test `Dink.Narrative.Review.HurtSpriteFindsScriptMadeSprites` (script name, case, handle, `nearest`, a dead sprite
  skipped, origin, Dink never a target; the blow's pending damage, last_hit 1, exactly one blood event, nohit rule).
- Build 0 warnings, full Dink suite and probe: see the PR text.

## Not checked
- The command in a rendered game (no rendered Unreal on this machine at the moment); Mog's remains themselves are art.
