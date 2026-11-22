# DinkC parity A40 + A44 (21 Nov 2026)

What changed:
- A40: `UDinkStorySubsystem::KillReturningStuff`, as kill_returning_stuff (dink.cpp:5049-5070). It ends a script's
  set_callback_random timer on wait (8043), the say_stop family (7916, 7948, 7973), say_xy (7997), and before the engine runs
  `talk`, `hit` or `damage` (14217, 14266, 14277, 14415, 15541, 15582, hurt 9968). Test `Dink.Parity.DinkC.CallbackEndsOnWaitSayAndHit`.
- A44: `stop_entire_game(1)` (10099-10108). While a menu is up, no brain, move, touch damage or wait runs, but kill timers and texts do;
  it clears on the first frame without a menu (17414-17444). Test `Dink.Parity.DinkC.StopEntireGamePausesSprites`.
- The probe bot was re-tuned for the new random stream. Only probe code changed (see packaged_probe.md, the 21 Nov A40 + A44 entry).

How it was proven (headless, private copy Saved/Gore21Nov whose sources equal master 7eccb89ff + the branch, file for file;
the world was regenerated on 21 Nov):
- `Scripts/build.sh` from clean intermediates: BUILD OK, 0 warnings, in 137 s.
- `Scripts/test.sh Dink`: 385/386. The one failure, `Dink.Narrative.Director.Vocabulary`, came from the A44 commit's
  `load_screen` row in `director_status.csv`, which described behaviour the code does not have. The csv was regenerated from the
  vocabulary and the test then passed alone (1/1). Tests include the A40 and A44 parity tests.
- `Scripts/test.sh Dink.Gameplay.Probe` (saves deleted first, chained from a new game): 29/29, all twenty chapters complete,
  `&story` 16. The twenty md5s were identical inside the suite run. Table in `Plugins/DinkParity/Docs/packaged_probe.md`.
- The md5s all moved from #140's table. That is the intended fix: A40 ends callback timers from chapter 1 on (fewer `rand()` draws),
  and A44 pauses the world under every level-up menu.
- Kernel log clean.

Not done:
- A41 (`create_sprite` uses add_sprite_dumb's defaults). It is held back on local branch `wip/dinkc-all-21nov`: with it Jack
  (chapter 1) and the cult girls (chapter 2) chase at 2-3x the pace and the bot loses those fights. That needs its own re-tune.
- No rendered frames (machine rule); no packaged run.
