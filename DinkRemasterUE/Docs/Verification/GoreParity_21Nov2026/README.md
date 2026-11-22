# Gore parity (PR #140): review fixes and the probe re-baseline (21 Nov 2026)

Follows `../GoreParity_15Nov2026/README.md` (the captures of the gore layers). Everything here was run HEADLESS
(`-nullrhi` builds, automation and probe) in a private copy `Saved/Gore21Nov` = master 7bc37ca1f + this branch, world
regenerated from scratch (`rm -rf Content/Dink/_Generated`, `import_greybox.sh --region all --export`, `--region stonebrook`).
No rendered game was started (machine rule after the 20 Nov kernel Oopses), so no new frames.

## What changed since the 15 Nov state

- Codex review findings on b0b3dcd65 (all six):
  - spawned class-bound kills: whether a creature class draws the corpse is decided while the sprite lives (was already in the
    branch: `FSeen::bCreatureDraws`);
  - `dink.DeathFall` runs independently of `dink.CorpseCards` (already in the branch);
  - `dink.CorpseCards 0` now removes every card (explosions too) and forgets the living sprites, so a kill made while it is off
    leaves nothing later (`UDinkCorpsePresenter::Suppress`);
  - `dink.HitBlood 0` clears the decals and consumes the blood serial, so hits made while it is off never appear later
    (`UDinkBloodPresenter::Suppress`);
  - the blood decal lies at the event's own pixel (where random_blood drew it), not at the hit sprite's later actor position;
  - a corpse card honours the picture's registration point: it stands on the middle of the picture's bottom row once the dink.ini
    offset is on the sprite's point, scaled by the sprite's size (`CardFootPx`, get_box D:3164-3260). Picture 645 (94 x 67, origin
    62,28) now stands 15 px west and 39 px south of the slayer's point, as 1997 draws it.
  Test `Dink.Gore.OffSwitches.ClearAndConsume` (new) and the card-foot assertion in `Dink.Gore.CorpseCard.KilledSlayerLeavesItsPicture`.
- Probe re-baseline (owner decision A25: the 1997 random_blood draw, the headless duck's bleed and human_brain's hurt-sound draw
  are in the simulation, so every chapter from the first fight on has a new trace). The bot's tactics were fixed where the new
  random stream broke a chapter; nothing in the game rules changed for the probe:
  - Ch8: Mog's step is hands off once Mog is dead (a fireball cast in the frame of his `load_screen(489)` pulled Dink's sprite back
    onto 680 through SyncDinkFromActor); up to four elixirs (this stream ends chapter 7 with 128 gold, two went in Mog's duel);
    SquadFight plans on the bare walkable ground when its own rules wall Dink in (he stood at the south edge in a knight's touch,
    touch 5 every 400 ms), its evade leaves a coming touch, and its kite prefers the open middle and, when charged, a row or
    column with a knight in it (fireballs finished the last two knights, who had stopped fighting).
  - Ch11: a fenced survivor in SCR_480's pen with no line at it (a Bong against the top edge) is left with its loot after 20 s
    without a hit point lost; the next round comes back.
  - Ch15: a level-up that opens in the loot step after the fight is answered "Increase Attack" (it took "Increase Magic"; one
    strength short, item-b1's arrows did 0 against Seth's defense 25 in chapter 20).
  - Ch19: a drop lying within 50 px of a thing that hurts by touch (SCR_156's thorn bush, touch 15) is left (`SafeDrops`).
  - Discovery mode `DINK_PROBE_SEEDS=1` (each chapter from the master seed save) was used to find the failures: 19/20 before the
    chapter-8 fixes.

## Proof

- `Scripts/build.sh`: BUILD OK, 0 warnings (clean intermediates at the start of the day; the build after the rebase compiled the
  master files that changed, e.g. DinkGreyboxSubsystem.cpp, and this branch's DinkCorpsePresenter.cpp / DinkGameplay.cpp).
- `Scripts/test.sh Dink.Gore`: 11/11 (warnings only `DestroyActor: World has no context` at test teardown).
- `Scripts/test.sh Dink.Gameplay.Probe` (saves deleted first, chained from a new game): 29/29, all twenty chapters complete,
  `&story` 16 at the end of chapter 20. Run on master 9d044b61b + branch and on master 7bc37ca1f + rebased branch.
- `Scripts/test.sh Dink` (full suite, master 7bc37ca1f + branch): 383/383 in 1025 s; its probe chapters again gave the same twenty md5s.
- Twenty md5s, identical in all three runs (the new table in `Plugins/DinkParity/Docs/packaged_probe.md`):
  Ch1 63c006c4c0, Ch2 b2e258c5c8, Ch3 80900b0e93, Ch4 3d675ccbae, Ch5 feed0cabe0, Ch6 0cf3be48b3, Ch7 01ac8b0b86, Ch8 aa03a84772,
  Ch9 d2702b28d8, Ch10 3ae72a786e, Ch11 2f777bf3d5, Ch12 7955dee2bf, Ch13 04ef7b1e78, Ch14 961becb5cf, Ch15 24c8599d7f,
  Ch16 1ff0ee43c6, Ch17 341f81a0f7, Ch18 20f045e7e2, Ch19 fb9c69e245, Ch20 174759fb0b.
- Kernel log: no Oops / BUG / general protection fault this boot.

## Not checked

- No rendered frames of the review fixes (registration-point card placement, off switches): visual check PENDING.
- Packaged build and `run_packaged_tests.sh` were not run for this PR (PIE only).
- Open owner question, not decided here: human_brain's hurt-sound `rand() % 2` (D:14706) stays drawn as the 15 Nov decision has it.
