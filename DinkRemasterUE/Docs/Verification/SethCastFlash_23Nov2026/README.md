# Seth's cast flash: the CastFlash material parameter (SP-06, 23 Nov 2026)

1997: while s7-boss casts (s7-boss.c:46-66) Seth's standing picture 580 flickers frame 1 / frame 2 / 1 / 2 / 1 (200 ms each),
and frame 2 shows his face and hands lit red. The Fable people stream (art-people-3, Master log 23 Nov 09:25) asked for a
scalar `CastFlash` 0..1 driven at his cast; the materials that read it are art and come with the Seth second-pass PR.

## What changed (code and one data row)
- Class rows (creatures.json `classes`) may carry `flash`: {"parameter", "pseq", "pframe", "rise_s", "fall_s"}
  (FDinkCreatureFlash, parsed and refused like the other row keys).
- The class body (UDinkCreatureClassComponent) eases the level towards 1 while its sprite stands still (sp_seq 0) on that
  picture and frame, towards 0 otherwise, and sets it with SetScalarParameterValueOnMaterials when it changes. The
  presenter now hands over sp_pframe (FDinkCreatureSpriteState::PFrame).
- Seth's row gets `flash` {CastFlash, 580, 2, 0.08 s up, 0.25 s down} through Scripts/bind_people_classes.py (`FLASH`;
  `--check` is clean after the regeneration). A material without the parameter ignores it, so nothing shows until the
  art PR gives M_Seth_PR_Skin (and the crest's hair material) the parameter. Note for that PR: the parameter reaches the
  materials of the skeletal mesh component only; a groom or a separate hair component would need its own hook.
- Presentation only: never written to the sprite; the probe md5s cannot move.

## Proof
- `Dink.Art.CreatureClass.FlashRowsAndEasing`: parsing, refusal without a parameter, easing (half way at half the rise,
  frame 1 lets it fall, an animating sequence never flashes), the shipped Seth row.
- `Dink.Art.CreatureClass.SethCastFlashFollowsHisPicture`: Seth's class body dressed on a script sprite of picture 580,
  driven through the s7-boss flicker: 0 standing, 1 after 200 ms of frame 2, < 0.3 after 200 ms of frame 1, 0 again
  0.3 s after the cast, never while walking.
- Build 0 warnings, full Dink suite and probe: see the PR text.

## Not checked
- The look (needs the art's material parameter and a rendered game).
