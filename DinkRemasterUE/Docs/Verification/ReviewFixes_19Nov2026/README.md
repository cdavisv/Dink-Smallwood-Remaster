# Fixes from the review of the 16 Nov merges (19 Nov 2026)

Codex stopped reviewing at its usage limit from about PR #157 on, so most of the 33 PRs merged on 16 Nov 2026 had no
automated review. A read-only review of their C++ as it stands on master f47439908 (#141, #150, #157, #158, #165, #166,
#168, #183-#188, #192, #193, #195-#197) found twelve defects; none crashes or moves the probe. This branch fixes all
twelve. Bug rows A340-A351 in `doc/remaster/ALPHA_BUG_LIST.md`.

| Row | Review | PR | Fix | Proof |
|---|---|---|---|---|
| A340 | R1 | #196 | The dragon's attack clip plays when its own ATTACK runs (its `attack_wait` jumps forward: en-drag.c attack() sets sp_attack_wait, casts harm, makes a brain-7 spark) instead of whenever any missile appears near it; new trigger `cast` in `creatures.json`. The `missile` trigger now skips Dink's missiles (brain_parm 1). | `Dink.Creature.OneShots.AttackTriggers` (dragon part) |
| A341 | R2 | #196 | A slime bites only when its own touch damage cost Dink life (Dink's last_hit is its sprite and his touch immunity just started, dink.cpp:15639-15660), not on any loss of life near it. | `Dink.Creature.OneShots.AttackTriggers` (slime part) |
| A342 | R3 | #196 | One-shots cross-fade instead of hard cuts: a cut shot fades out under the new one (0.12 s or its blend-out); a fidget fades out when the body walks off; the dying copy keeps the overlays of its kill frame and fades them with its layers. | `Dink.Creature.OneShots.Player` (repeat hit: held 0.926, strongest 0.799 in the first frame of the restart, the cut one gone after 0.12 s; walk-off fade) |
| A343 | R4 | #196 | Each body seeds its own one-shot stream from its actor's name (stable across runs; never the simulation's stream). | `Dink.Creature.OneShots.Player` (first fidget at frame 464 for one duck, 396 for its neighbour, 464 again for the first) |
| A344 | R5 | #192 | A208 duplicates count as one object only while they show the same picture; otherwise the copy on Dink's screen draws its own picture and the others are hidden (never destroyed) and given back exactly. | `Dink.Art.Family.DuplicatePictureChange.DroppedCopy`; capture 01 |
| A345 | R6 | #192 | Same rule: once the kept copy's picture changes, the dropped copy's screen still draws its object. | `Dink.Art.Family.DuplicatePictureChange.KeptCopy` (capture not reproduced, see below) |
| A346 | R7 | #185 | `ProcessKeyDown` observes the screen before the attack key's 0.3 s menu guard (Slate delivers keys before the world ticks). | `Dink.Narrative.Presentation.AttackKeyMenuGuard` |
| A347 | R8 | #185 | Closing the map by key or click runs on only the script that showed it (`UDinkStorySubsystem::CloseShownBitmap`, ThinkShowBmp dink.cpp:16722-16740); a say_stop line keeps its text, voice and wait. | `Dink.Narrative.Presentation.ShowBmpMapKeepsLine` |
| A348 | R9 | #183/#187 | The master limiter is removed from the shared audio device in `UDinkAudioLifeSubsystem::Deinitialize` (it stacked one per restart_game). | code only (needs a real audio device) |
| A349 | R10 | #165 | `Dink.Expanded.Murkwood.Play` restores the DinkExpanded switch on every early return. | code only (the failure path needs an unloadable world) |
| A350 | R11 | #166 | Family-tagged children of a card (a placed fire's flicker light and smoke plume, a script effect's glow) follow the card's visibility, both ways. | `Dink.Art.Family.EffectFollowsCard`; capture 03 |
| A351 | R12 | #193 | `DinkWorldLife::IsFamilyEffect` reads the family tag and bHiddenInGame, not the visible flag that the off-screen hiding clears. | `Dink.World.Life.FamilyEffectOwnedOffScreen`; capture 03 |

Changed: `DinkCreatureEvents.*`, `DinkCreatureOneShots.*`, `DinkCreatureClassComponent.*` (GetOverlays, per-body seed),
`creatures.json` (dragon trigger), `DinkFamilyDuplicates.*`, `DinkArtFamilySubsystem.*`, `DinkGreyboxSubsystem.cpp`,
`DinkWorldLifeSubsystem.cpp`, `DinkNarrativeInput.cpp`, `DinkStorySubsystem.*`, `DinkAudioLife.cpp`,
`DinkExpandedPlayTests.cpp`; tests in `DinkCreatureOneShotTests.cpp`, `DinkTitleMenuTests.cpp`, `DinkArtFamilyTests.cpp`,
`DinkFamilyDuplicatesTests.cpp`, `DinkWorldLifeTests.cpp` (the escape-menu test now sets the 0.3 s guard to 0, as the
header says tests do; the guard has its own test). `AGENTS.md`: the A208 picture rule and the stale `_Generated` pitfall.

## How it was proven

Private copy `Saved/ReviewFixes19Nov` (master f47439908 plus this branch, no Intermediate, no `_Generated`), clean
build, world `import_greybox.sh --region all --export` then `--region stonebrook`:

- Build: BUILD OK, 0 warnings (142 s clean).
- Full `Dink` suite: 350/351; the one failure was an assertion of the new duck walk-off test (it walked off after the
  fidget had ended, so both weights read 0); the test was fixed and the targeted run
  `Dink.Creature.OneShots+Dink.Art.Family+Dink.World.Life+Dink.Narrative.Presentation` passed every test of this branch
  (31/32: `Dink.Art.Family.BarrelCookedGameSurface` refuses a second run in one copy while the full run's
  `Saved/Automation/BarrelCookGame.*` exist, AGENTS.md; it passed in the full run).
- Probe: all twenty chapter traces equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 cc2e12fb5c ... Ch20 be28390b9d).
- Python unit tests: 1019 OK.
- Offline syntax check of every changed .cpp before the build (`Scripts/syntax_check.py` of the audio stream).

Master itself, same recipe in `Saved/AuditMaster19Nov`: suite 351/351, probe twenty chapters equal, unit 1019 OK,
`scrub_private_paths.py --check` clean (23,234 files), `tools/lfs_audit.py` 0 of 13,787 objects missing.

## Captures (1280x720, offscreen Vulkan, master copy before / this branch after; looked at)

- `01_r5_burnt_pine_217.jpg`: fireball at S217_P01 on 217, then 216 and back to 217. Before: the burnt tree never
  appears. After: the burnt tree stands at the seam (log: `Family duplicates: S217_P01 draws the object of S216_P04
  S217_P01 now (the copy of the current screen, its own picture)`), and on 216 the kept copy draws its green pine again
  (`S216_P04 draws ... now (the kept copy)`). The big green pine left of the burnt trunk is another tree.
- `03_r11_r12_fire_offscreen.jpg`: the burning cottage of 439 (story 3) seen from 438, 440, 407 and 471. Before: smoke
  columns, a glowing light and a second fire on the ground beside a roof with no flames. After: none of it.
- `02_r6_kept_copy_burnt.jpg`: NOT a proof: the fireball from (520, 372) on 216 did not burn S216_P04 in either run, so
  before and after are the same. A345 rests on its test.

## Not checked

- The burning cottage seen ON 439 after the fix (the on-screen shot framed Dink's boot): that the fires still show there
  rests on `Dink.Art.Family.EffectFollowsCard` (shown again when the card returns).
- R6 in the game (above); the dragon and slime triggers in the game (tests only); the limiter (A348) and the Expanded
  failure path (A349) by running them.
- Packaged build.

## Also found on 19 Nov (not a code defect)

A private copy reflinked from the shared checkout carries its old `Content/Dink/_Generated`, and `--region all` keeps
existing immutable barrel targets: on such a world every barrel hit is refused ("original hardness placement phase
refused: missing/mismatched immutable imported card/picture baseline"), twelve barrel tests fail and the probe hangs at
Ch19 step 8 (S209_P13) with no timeout. `rm -rf Content/Dink/_Generated` before the import (now in AGENTS.md).

Owner question left open (bug list): 1997 `human_brain` draws `rand()%2` for Dink's hurt sound on every damage frame
(dink.cpp:14704); the port does not.
