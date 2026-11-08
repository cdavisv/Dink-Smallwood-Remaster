# The probe in a packaged game (done 7 Nov 2026)

Goal (alpha gate): "Bot completes &story 0-16 on a packaged build." The bot is the automation test family
`Dink.Gameplay.Probe.*` (`Plugins/DinkParity/Source/DinkProbe/Private/DinkProbeTests.cpp`). This note began as a design written from
the code on the morning of 7 Nov 2026; it was then carried out, and it now says what was done, what the design got wrong, and how
the packaged run is kept identical to the editor's.

**Result.** `Scripts/package.sh` cooks and packages the `DinkRemaster` game target (Linux, Development) and
`Scripts/run_packaged_tests.sh` runs the probe chapters in the packaged game, one process per chapter, headless. Each chapter's
event trace is byte-identical to the editor's PIE trace (md5, first 10 digits; the probe prints it and writes `*_trace.txt`).

**Update, 7 Nov 2026 night (after the `sp_script` parity fix, AGENTS.md pitfall 53): nine chapters, all `PARITY OK`.** `Scripts/package.sh` (28 s, incremental cook) then
`Scripts/run_packaged_tests.sh`; the chapters 7-9 were packaged for the first time (the script's default chapter list now ends with `Ch9Windemere`). Every hash moved with the fix (the
mains of the scripts `sp_script` attaches now run in the caller's turn) and PIE and packaged moved together:

| Chapter | PIE trace md5 | Packaged trace md5 | Events |
|---|---|---|---|
| 1 `Ch1Stonebrook` (47 steps) | b3760d52d7 | b3760d52d7 | 4338 |
| 2 `Ch2Terris` | a5cfdf70bc | a5cfdf70bc | 3092 |
| 3 `Ch3Roads` | e9fce770bc | e9fce770bc | 430 |
| 4 `Ch4Gold` | cd1b3bf820 | cd1b3bf820 | 2121 |
| 5 `Ch5Bow` | 6c709d1069 | 6c709d1069 | 120 |
| 6 `Ch6Goblins` | 9e87080221 | 9e87080221 | 462 |
| 7 `Ch7Sanctuary` | 7cc6e2fe93 | 7cc6e2fe93 | 2589 |
| 8 `Ch8Knights` | 6697a02e52 | 6697a02e52 | 1443 |
| 9 `Ch9Windemere` | 0ea9677ee2 | 0ea9677ee2 | 344 |

The earlier table (before the fix, kept for history; chapter 7 was not packaged then):

| Chapter | PIE trace md5 | Packaged trace md5 |
|---|---|---|
| 1 `Ch1Stonebrook` (47 steps) | 50091fcc80 | 50091fcc80 |
| 2 `Ch2Terris` | 103b0331f1 | 103b0331f1 |
| 3 `Ch3Roads` | e0b643193a | e0b643193a |
| 4 `Ch4Gold` | 230f594539 | 230f594539 |
| 5 `Ch5Bow` | 6c709d1069 | 6c709d1069 |
| 6 `Ch6Goblins` | 6d33d4a177 (7471375e32 after a healer step another agent added to chapter 6 at 13:05; PIE and packaged agree on that too) | 6d33d4a177 (7471375e32, same source) |

**Update, 7 Nov 2026 late night (after the `external`/`spawn` parity fix, AGENTS.md pitfall 56): ten chapters, all `PARITY OK`.** `Scripts/package.sh` (51 s, incremental cook) then `Scripts/run_packaged_tests.sh` (its default chapter list now ends with `ChAJoppa`, the chapter 10 whose test name sorts after `Ch9Windemere`). Chapters 2, 4, 7, 8 and 9 moved with the fix (1, 3, 5, 6 did not), chapter 9 now includes the 27 ducks and chapter 10 is new; PIE and packaged agree on every one:

| Chapter | PIE trace md5 | Packaged trace md5 | Events |
|---|---|---|---|
| 1 `Ch1Stonebrook` (47 steps) | b3760d52d7 | b3760d52d7 | 4338 |
| 2 `Ch2Terris` | 253e6f7268 | 253e6f7268 | 3092 |
| 3 `Ch3Roads` | e9fce770bc | e9fce770bc | 430 |
| 4 `Ch4Gold` | d431e6780f | d431e6780f | 2121 |
| 5 `Ch5Bow` | 6c709d1069 | 6c709d1069 | 120 |
| 6 `Ch6Goblins` | 9e87080221 | 9e87080221 | 462 |
| 7 `Ch7Sanctuary` | d50e5111f6 | d50e5111f6 | 2589 |
| 8 `Ch8Knights` | 28406402c0 | 28406402c0 | 1443 |
| 9 `Ch9Windemere` (6 steps: + the ducks) | 1db62e4adb | 1db62e4adb | 2323 |
| 10 `ChAJoppa` (7 steps) | c532805f11 | c532805f11 | 442 |

The first `package.sh` of the night **failed to compile** (`redefinition of 'Inside'`, `'NAME_Main'`): adaptive unity bundled DinkNarrative files differently once the project was committed in the fork. `Source/DinkRemaster.Target.cs` now switches unity builds off, like the editor target (pitfall 61); the staged build that run left behind was the old one (its parity lines were stale hashes, not a real difference).

(The gate itself, `&story 16`, still needs the remaining chapters authored: `probe_route.md`; the probe now stops at the Joppa dragons, route step 36: a kit (strength 20+) the run does not have, AGENTS.md "Where the probe stops, and why".)

## 1. What was changed

* **New module `DinkProbe`** (`Plugins/DinkParity/Source/DinkProbe/`, type `DeveloperTool`, deps `Core, CoreUObject, Engine, DinkCore,
  DinkNarrative, InkPlusPlus`, plus `UnrealEd` only `if (Target.bBuildEditor)`). `DinkProbeTests.cpp` moved there from `DinkParity`
  (the file's code is unchanged except the points below). `DeveloperTool` modules are built when `bBuildDeveloperTools` is true: the
  editor and a Development/DebugGame game, never Shipping/Test (`ModuleDescriptor.cpp`; no automation tests exist there anyway).
  `Developer` (no "Tool") would be editor/program only; `Runtime` would ship the probe.
* **`DinkParity` stays editor-only** (`DinkParity.uplugin`: module type `Editor`; it depends on `UnrealEd`). `DinkRemaster.uproject`:
  the `TargetAllowList: ["Editor"]` was removed from the `DinkParity` plugin entry, so the game target builds `DinkProbe` and skips
  `DinkParity` by module type. `DinkImport`, `PythonScriptPlugin`, `ModelingToolsEditorMode` keep their allow-lists.
* **`DinkTestHelpers.h` was not moved.** The probe used only its `DINK_TEST_FLAGS` macro, which is now defined (under `#ifndef`) at the
  top of `DinkProbeTests.cpp`; the other 28 test files still include the original in `DinkParity`.
* **`DinkProbeTests.cpp`:** `Editor.h`, `FileHelpers.h`, `Tests/AutomationEditorCommon.h` behind `#if WITH_EDITOR`; `ProbeWorld()` (the PIE world
  in the editor, the one `EWorldType::Game` context in a game) replaces `GEditor->PlayWorld`; `RunChapterTest` has a `#if !WITH_EDITOR`
  branch (no `LoadMap`, no PIE: checks `FPackageName::DoesPackageExist(WorldMap)` and that the running world is the world map, and
  makes a missing map an **error**, never a skip); the two repeat tests (two PIE sessions in one process) exist only in the editor;
  the trace writer lower-cases the event kind (section 4); one `AddInfo` says at which story clock the probe began.
  Not touched: every `FProbeCommand` step, tactic, constant and the report format.
* **`DinkProbeHold.{h,cpp}` + `DinkProbeModule.cpp`** (new): the packaged start-up alignment of section 3, active only in a game started
  with `-DinkProbeHold`.
* **`DinkStorySubsystem.cpp`** (outside the probe, no behaviour change): the event texts built from FNames are lower-cased
  (`Script.ToString().ToLower()` etc., four places; section 4).
* **Scripts:** `package.sh` (see section 2), `run_packaged_tests.sh` (`-DinkProbeHold`, `Automation ...; Now; Quit`, report path).
  `Config/DefaultGame.ini` only had its comment updated.

A wrapper (the probe stays an automation test) was kept instead of a `dink.Probe <n>` console driver: the same class runs in both worlds,
so parity follows from shared code, and `index.json`, the exit code (0 on success, 255 on failure) and `Scripts/test.sh`'s contract are
the same. The two repeatability tests became "two process runs and the same md5" (the parity check, and two packaged runs gave
identical hashes).

## 2. The cook and the package (what it tripped over)

`Scripts/package.sh`: RunUAT `BuildCookRun`, `-clientconfig=Development -cook -stage -pak -iostore -compressed`, one map to cook
(`L_Greybox_World`; its nine sublevels are cooked by reference), `-cookdir=` for the content that is only loaded by string path.
Measured on the dev machine: **cook of 5,189 packages 22 s from an empty `Saved/Cooked`** (42 s in the first, failing run; the design expected a long
shader compile: the shaders came out of the shared DDC), UAT total 40 s from an empty `Saved/Cooked`, 30-65 s incremental; stage `Saved/StagedBuilds`
1.5 GB (`Content/Paks`: 575 MB `.ucas`, 11 MB `.pak` with the raw `Dink/Data`; binary 300 MB + 296 MB `.debug`/`.sym`).

1. **`-SkipCookingEditorContent` made the cook fail** (exit 25, `Error_UnknownCookFailure`, 16 "Content is missing from cook" errors): the
   engine's *Landmass* plugin (loaded by the cook commandlet as a startup package; not ours) has two materials that reference
   `/Engine/EditorMaterials/*` and `/Engine/EditorResources/S_Terrain`. Fix: the flag is gone from `package.sh` (cooking those few
   editor packages costs seconds). Nothing of ours is involved; no Codex file was touched.
2. **`-cookdir=` with absolute directories works** (UAT splits at `+` and hands the cook one `-CookDir=` per directory). The string-loaded
   content cooked and loads: the packaged game logs `DINK ART OK`, `DINK CHARACTER ART OK`, `DINK CREATURE ART OK` (Kits, Creatures, NPC, Hero
   meshes found through `LoadObject`). `Input` was added to the directory list (the pawn's soft references to `/Game/Input/*`).
3. **`Dink/Data` staging works**: 644 hardness files, the story, the CSVs and the Art/Audio JSON are in `DinkRemaster-Linux.pak` and read through
   the pak platform file with plain `FFileHelper` calls (as `DirectoriesToAlwaysStageAsUFS` promised; `IFileManager::FindFiles` on
   `Data/Art/*.json` also works there). The cooked assets are in `.utoc/.ucas`, so loose `.umap` files do not exist in the package:
   hence the `DoesPackageExist` check.
4. The git-ignored generated map was present; `package.sh` still refuses to run without it.
5. **Preflight too wide:** `pgrep 'Binaries/Linux/UnrealEditor'` also matched the other agent's visible playtest game
   (`UnrealEditor ... -game` of `~/Work/DinkPlaytestStage`), a different project. It now stops for headless editors/UBT/UAT anywhere and for an
   editor or game of *this* project only.
6. **`package.sh`'s "is the story in the pak" check always warned**: `grep -q` closed the pipe, `UnrealPak -List` died of SIGPIPE and `pipefail`
   reported failure. The listing is captured first now.
7. **The shared Zen server can be restarted by another agent's editor** while UAT reads its oplog ("Reading oplog from Zen..." hangs for
   ever, no error). One run hung that way; kill the UAT and rerun when no other editor is starting.
8. Not a problem here: Inkpot has no content, `DinkExpanded` is disabled, `DinkImport` is allow-listed to the editor, nothing links it; the
   `.umap` imports of `/Script/UnrealEd` did not matter. `BuildConfiguration=PPBC_Shipping` in `DefaultGame.ini` only affects the editor's Package
   menu (it would remove the automation tests).

## 3. Start-up alignment (why plain "run it in a game" gave a different trace)

The first packaged run passed its tests but its trace differed from PIE's (md5 `dddf03c204`, 2,775 events, and chapter 1 stopped at step
36: it was not the same game). Everything below was found by comparing the traces and by logging the story and greybox ticks; the
fix is packaging/runtime plumbing in the DinkProbe module, nothing in the gameplay, brain, director, story or probe-tactic code.

1. **Case.** `FName` display case is preserved only in editor builds (`WITH_CASE_PRESERVING_NAME`). In a cooked game `FName("main")` shows as the engine's
   own `Main`, `"game"` as `Game`, `"start"`, `"cmd"`, `"say"`... The trace (kind column, `script.proc` in `idle`/`end` lines, say-call and command
   names) printed `Game`, `Start`, `newgame.Main`. Fix: lower-case those strings where they are written (the kind in the probe's writer; four
   `ToString().ToLower()` in `DinkStorySubsystem.cpp`). In the editor they were all lower case already, so the PIE traces are unchanged
   (verified: the six md5s).
2. **The test started 300 frames late.** The automation controller waits 5 s of ticker time (`DefaultDelayTimer` in
   `AutomationCommandline.cpp`; frames are 1/60 s under `-UseFixedTimeStep`) before it looks for workers, and the world ticked all that time:
   the new game's scene was 5 s old when the probe began. `Automation RunTests X; Now; Quit` (the `Now` sub-command zeroes the timer; a
   separate `Automation Now` is an unknown command) starts it at engine frame 5. (`-UseFixedTimeStep -FPS=60` give the game 1/60 s frames from its
   first tick: confirmed, the first story tick is `dt = 0.016666668`.)
3. **The probe must begin right after the world's first frame** (PIE: story clock 16.667 ms, world time 0.016667 s; the new game then starts at 33.333 ms).
   The hold: `-DinkProbeHold` makes `FCoreDelegates::OnFEngineLoopInitComplete` (before the first tick) pause the world
   (`SetGamePaused`), and the probe's first `Update` releases it, so the probe's second `Update` comes after exactly one world frame.
4. **Tick order.** In PIE the story subsystem ticks before the greybox subsystem in each frame (a screen change is seen by the story two
   frames after the probe's teleport); in the game process it is the other way round (one frame), so every later timestamp was one frame early
   and the floating-point phase of the story clock moved, which moved the draws of the one shared `rand()` (the first visible divergence: the
   `findduck` roll). Cause (read from `Tickable.cpp`, consistent with the logs): `UGameInstance::InitializeStandalone` creates a throwaway
   default world first; its greybox subsystem's place in the engine's tickable list is reused by the real world's greybox, ahead of the story.
   Fix in the hold: while the world is paused, take both subsystems out of the tickable list (`SetTickableTickType(Never)`) and put them back
   story first. (A first idea, hiding the pawn from the greybox for the first frame, was not tried once the tick order was understood.)
5. The loaded-chapter gate (`GetNowMs() > 10000`, "the previous PIE session's world") needed no change: with the hold the clock is small.
6. **Where the files go:** `FPaths::ProjectSavedDir()` is `<stage>/Linux/DinkRemaster/Saved` (the build is not "installed"): `SaveGames/probe_chN.sav`,
   `Narrative/*`, `Automation/Report_<chapter>/index.json`, `Logs/DinkPackagedTest.log`. The staged Saved folder is separate from the project's,
   so PIE and packaged runs cannot overwrite each other. The report's HTML template is not staged ("Failed to load test report html
   template - No report will be generated" is logged as an error by the controller and is harmless; `index.json` is written).

Checks that hold: `Automation RunTests` finds the `DeveloperTool` module's tests in a Development game; exit code 0 on success and 255 on
failure (seen with the first, failing runs); `-ReportExportPath` writes `index.json`.

## 4. Proving parity (what `run_packaged_tests.sh` does)

One game process per chapter (a packaged process has one GameInstance for its life; chapter N loads `probe_ch<N-1>.sav` from the staged Saved
folder, as in the editor). After the chapters it compares `md5sum` of each packaged `*_trace.txt` with the editor's in `Saved/Narrative`
(`DINK_PIE_TRACE_DIR`) and prints `PARITY OK`/`PARITY DIFF` with the first differing line. A "skipped" test counts as a failure in
the packaged run. To debug a divergence: diff the two traces with the time column removed and lower-cased (the early differences are
usually case or a one-frame offset), then look at the first behavioural line.

## 5. Where this does not go yet

* The two repeat tests (`Repeatable`, `RepeatableChapter`) are editor-only; packaged repeatability is two runs with equal md5s.
* Only `L_Greybox_World` is cooked; the Stonebrook-only fallback of the editor probe does not exist in the package.
* The other test files (import, art, audio, narrative PIE tests) are `DinkParity`: editor only.
* A Shipping package has no automation tests by design.
* The design note's first version said chapter 4's hash was `0b98f37de3` (an older run; it is `230f594539`), expected a long first cook
  (it was 22-42 s), expected a 10,000 ms story-clock gate to need relaxing (it did not), and listed five edits to the probe file (it took the
  start-up alignment too). All of this is corrected above.
