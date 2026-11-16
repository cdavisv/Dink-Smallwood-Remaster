# DinkC parity fixes A43, A45, A47 (PR #141): evidence, 16 Nov 2026

## What changed
- A43 `set_dink_speed` scales Dink's top speed (Herb's boots; dink.cpp:7563-7575, 17311-17321); load/restart resets it (load_game 1423).
- A45 brains, people and missiles treat a map.dat warp's hardbox (a door) as hard: `check_if_move_is_legal` reads `get_hard`
  (dink.cpp:13503, 527-546); only Dink's walk reads `get_hard_play` (548-580). Reverts A2's rule, which came from a mis-citation.
- A47 `script_attach(n)` sets the instance's sprite, which `&current_sprite` reads (8075-8087; sp_* on 1000 do nothing, 5396-5403);
  `external` passes the attached sprite (11335). Owner decision of 16 Nov 2026: s1-mh-f.c alone keeps its sprite, so Martridge's scroll
  shrinks away as written (`UDinkStorySubsystem::CurrentSpriteField`; DINKC_PARITY.md "Owner-approved deviations").
- Probe tactic (no game change): chapter 19 visits the Darklands until Dink is level 6, not only until the gold is there.
- Bug list bookkeeping: A4, A7, A9, A13, A14, A47, A76 closed; A75 records the owner decision of 15 Nov.

## How it was proven (private copy, master 84e045b0 + this branch; world regenerated with `--region all --export`, `--region stonebrook`)
- `Scripts/build.sh`: OK, 0 warnings.
- `Dink.Parity.DinkC.*` + `Dink.Gameplay.Prop.*` 6/6 (targeted, earlier base 3a7b4451c).
- Full `Dink` suite: 320/320 on master 84e045b0 + this branch (311/311 on master 5d8a4a1f + this branch).
- `Dink.Gameplay.Probe` twice on each of two bases: all twenty md5s equal between runs; the table and every moved chapter's dink.cpp reason
  are in `Plugins/DinkParity/Docs/packaged_probe.md`.

## Not checked
- No captures: nothing here changes a picture except Ch1's dam-icee ice (a sprite that keeps brain 0 instead of 12, as in 1997); the boots'
  speed and the door bounces are checked by the tests and the probe traces, not looked at in a rendered game.
- Packaged build: not run for this PR (the packaged end-to-end run on master is a separate step).
- A50 (bow-shop softlock) and the held fixes A40, A41, A44 are separate PRs.
