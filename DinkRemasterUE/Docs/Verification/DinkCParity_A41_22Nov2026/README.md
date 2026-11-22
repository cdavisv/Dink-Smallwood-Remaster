# DinkC parity A41 (22 Nov 2026)

What changed:
- A41: `create_sprite` uses add_sprite_dumb's defaults (dink.cpp:9041-9051, 3089-3135): speed 0, timing 0, base_* -1
  (`UDinkDirector::InitDumbSprite`, in both create_sprite paths). Before, the remake gave add_sprite's (speed 1, timing 33, bases 0):
  hit Chealse froze for good (base_attack 0), script fireballs without `sp_timing` flew at half speed, created chasers walked at a third
  to half of the 1997 pace. Test `Dink.Parity.DinkC.CreateSpriteUsesAddSpriteDumb`.
- The 1997 rule is kept as it is. The probe bot's route and tactics were adapted (probe code only):
  - Jack (s2-jack, created by s2-auntp) is fought at the end of chapter 11 with the longsword, not in chapter 1: at timing 0 he chases
    at 120 px/s straight and 170 px/s on diagonals (Dink 180), and SCR_036 has no loop a level-2 Dink can kite him round. Nothing in the
    story reads `&s2-aunt` 4.
  - Mary (s2-culg) is talked to from her north side: her scene walks Dink 700 px south while the screen fades.
  - Feuds heal in Terris below 40 % life.
  - Chapter 4 collects 1140 gold (was 1060) so chapter 8 can buy four elixirs for Mog and the knights without fighting: its feud screens
    are still empty then, and waiting 5 minutes would bring the sanctuary goblins back (editor_type 6), after which the last goblin's
    death does not spawn Mog (s3-gs.c:64-71).

How it was proven (headless, private copy Saved/Gore21Nov whose sources equal master 11290aa3e + the branch, file for file):
- `Scripts/build.sh` from clean intermediates: BUILD OK, 0 warnings, in 138 s.
- `Scripts/test.sh Dink.Gameplay.Probe` (saves deleted first, chained from a new game): 29/29, twenty chapters, `&story` 16.
- `Scripts/test.sh Dink`: 387/387, with the probe inside it. All twenty md5s are the same as in the run before. Table in
  `Plugins/DinkParity/Docs/packaged_probe.md`.
- Kernel log clean.

Not done:
- No rendered frames (machine rule); no packaged run.
