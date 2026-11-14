# Alpha bug list (alpha QA, code stream)

Started 14 Nov 2026 on master `8ba0e903`. Engineering defects found by the alpha QA pass: a baseline of every
automated suite, a check of the packaged build, and a code audit of movement, physics, animation and their
plumbing. Art defects are reported to the art streams, not fixed here. Gameplay changes are made only to
match the 1997 original (`source/dink/dink.cpp` citation and a test); anything else is the owner's decision.

Severity: **S1** blocks the alpha gate or breaks a shipped build; **S2** wrong gameplay or visible defect a
tester will hit; **S3** minor, rare or cosmetic.

## Baseline (master 8ba0e903, private copy, world regenerated with `--region all` then `--region stonebrook`)

| Suite | Result | Notes |
|-------|--------|-------|
| `Scripts/build.sh` | OK, 0 warnings | 114 s |
| `Scripts/import_greybox.sh --region all`, `--region stonebrook` | OK | 644 screens / 61 screens; `Dink.Import` 23/23 after each |
| Whole `Dink` automation suite | **261/261 pass**, 0 fail, 3 with warnings | 1,081 s. Warnings (all pass): `BarrelRollout.ScriptedHits.S161_P24` (marked draw_hard_sprite refused, expected by that test), `Hardness.FittedLifecycle` (a deliberately missing mesh), `ProbeLoadOracle.StockProjection` (DestroyActor without a world context) |
| of which `Dink.Gameplay.Probe` | 22/22 | all twenty chapter traces equal the table in `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 b4ad88c02c ... Ch20 cc16518259) |
| of which `Dink.Animation` / `Dink.Movement` | 6/6 / 10/10 | |
| of which `Dink.Art.*` | 58/58 | `Dink.Art.InteriorCamera.FadesAndRestoresPhysicalHouse`, which failed on an earlier master, passes |
| Python unit tests (`Scripts/tests`) | 833/833 | 187 s |
| `Scripts/package.sh` | not run on bare master (the run hit A8); the package of 13 Nov (5d12e469, same `package.sh`) lacks all photoreal art (A1) | with PR #102: OK, content check 655/655, 6,974 packages, 1.82 GB ucas |
| `Scripts/run_packaged_tests.sh` | not run on bare master (see above) | with PR #102: 20/20 chapters pass, 20/20 `PARITY OK`, both before and after the parity fixes below |

## After the fixes (master 8ba0e903 + PR #102 + this PR, world regenerated)

| Suite | Result |
|-------|--------|
| Whole `Dink` suite | 263/263 (the two new tests added; 3 with the same warnings) in 895 s |
| Package | OK, content check 655/655 |
| Packaged probe | 20/20 pass, 20/20 `PARITY OK` |
| Probe hashes | Ch1-Ch10 unchanged. Ch11-Ch20 moved; the cause is in `Plugins/DinkParity/Docs/packaged_probe.md`, found by testing one change at a time on Ch11: A2 (the bow-shop keeper on SCR_097 may enter the exit door's box, so the random sequence shifts) and A3 (the stump of a tree burnt on SCR_632 is stamped on the next visit instead of the tree). Both match the original. |


## Defects

| # | Sev | Area | Defect | Repro | Status |
|---|-----|------|--------|-------|--------|
| A1 | S1 | Packaging | The packaged build contains none of the 824 `/Game/Dink/Photoreal` packages. The runtime loads the photoreal hero (`SK_Dink_Photoreal`), characters, creatures, the wind parameter collection, town exteriors and every photoreal family binding by string path, which the cook cannot follow, and `Scripts/package.sh`'s cook-directory list lacked `Dink/Photoreal`. A packaged game falls back to sprite cards and the mannequin. | `UnrealPak <stage>/Linux/DinkRemaster/Content/Paks/DinkRemaster-Linux.utoc -List` on the 13 Nov 01:39 package: 8,716 lines, 0 under `Dink/Photoreal`; `python3 -I Scripts/check_package_content.py --listing <that listing>` lists 162 bound assets missing. | Fixed in PR #102: `Dink/Photoreal` cooked; `Scripts/check_package_content.py` (run by `package.sh`, exit 4) fails a package that lacks any asset named by `Content/Dink/Data` JSON or runtime C++ literals; unit tests `Scripts/tests/test_check_package_content.py`. |
| A2 | S2 | Physics / parity | Monsters, people and missiles stopped at a map.dat warp's hardbox (a door). `get_hard` (dink.cpp:569-575) reads a stamped hardbox whose placement has `prop != 0` as 0 for every sprite; only Dink warps there (special_block, 16906-16911). | A fireball or arrow aimed through a doorway stops at the door; a chasing monster cannot follow Dink's path across a door's box. | Fixed in this PR (`UDinkGameplay::CheckIfMoveIsLegal`); test `Dink.Gameplay.Prop.SpritesCrossMapWarpHardbox`; `Dink.AI.People.VillagerWandersInBounds` now applies the same get_hard rule. Moves probe Ch11-20 (see above). `GetHard` itself keeps the stamped code: the pawn's greybox models the warp as a solid box with a trigger, and the probe's routing relies on it. |
| A3 | S2 | Physics / parity | Saved editor_type 1-5 hardness was not applied when a screen loads (pitfall 77). place_sprites_game runs update_play_changes first (dink.cpp:5974, 5786-5811): a barrel made flat for good (type 3) is soft on every later visit, a type 4/5 placement is hard. The remaster stamped map.dat's flags again, in `GetHard` and in the greybox collision, and a hard placement removed before the visit (type 1) stayed solid in the pawn's collision after any draw (its box was missing from the diff base). | Smash a barrel whose script saves editor_type 3 (bar-gh.c), leave the screen and come back: Dink and monsters are blocked by an invisible barrel. | Fixed in this PR (`UDinkGameplay::ApplyLoadedPlayChanges`, `BuildLoadedCodes`, greybox diff base = the baked map); tests `Dink.Gameplay.Hardness.SoftSpriteLetsDinkThrough`, `Dink.Gameplay.Hardness.GreyboxCollisionFollows`. Legacy (untagged) screens only; tagged screens have their own path. Load-time stamps use both saved pictures (`EffectiveHardnessPicture`). Still open: a type 2-5 live/background swap does not change whether the placement becomes a sprite (legacy `EnterScreenPlacements` reads map.dat's type), and draws during a visit still read the override's single Variant. |
| A4 | S3 | Input | "Bow input binding missing" was reported. Not reproduced: F / Left Ctrl go through `FDinkNarrativeInputProcessor` to `InputAttackPressed` / `InputAttackReleased`, which draw and release the bow. The note in AGENTS.md ("Not built: the human input binding") is stale. | - | Test added: `Dink.Gameplay.Bow.AttackKeyDrawsAndShoots` drives the bow through the game's key path. No gamepad button is bound to attack, talk, magic or menus (keyboard only): open, owner decision on controls. |
| A5 | S3 | Physics / parity | Push starts against any obstacle: `UDinkStorySubsystem::UpdatePlayerPush` takes "input but almost no velocity" as pushing; the original starts a push only against hardness other than 2 (low), dink.cpp:13525-13537. | Walk into a low fence or water edge for 0.6 s next to a pushable rock. | Open. |
| A6 | S3 | Animation | Creature locomotion speed is measured in `UDinkCreatureComponent::TickComponent`, which ticks before the story subsystem moves the actor (one frame stale), from whole-pixel scripted positions: the blend-space speed and play rate jitter. Same class as the Mother's stutter fixed in PR #97 (gate2_characters_notes §1). | Watch a pig or duck walk at 60 fps; record `SpeedCmS`. | Open; reported to gate2-creatures (owns the component). |
| A8 | S3 | Tooling | `Scripts/package.sh` refused to run whenever any process's command line merely mentioned `UnrealEditor-Cmd`, `UnrealBuildTool`, `RunUAT` or `AutomationTool` (`pgrep -f`): another session's waiting gate loop blocked every package. | Start a shell loop whose arguments name `UnrealEditor-Cmd`, then `Scripts/package.sh`: "an editor ... is already running". | Fixed in PR #102: matched by process name, as the machine's gate does. |
| A7 | S3 | Gameplay (3D rule) | `AuthoredActorMoveBlocked` (DinkAuthoredInteraction.cpp) blocks humanoid and creature bodies with a 3D sweep where the 1997 hardness would let them pass. This is a remaster rule, not the original's. | - | Owner decision (recorded, not changed). |


