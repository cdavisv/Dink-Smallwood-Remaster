# C++ stability audit (15 Nov 2026)

A static review of the project's own runtime C++ for crash and corruption risks before the alpha ships, with the fixes
for the certain defects. Reviewed on master `da511dbc`, rebased onto `ce528c62`.

## Scope

- **Read in full or by hot path:** `Plugins/DinkCore` and `Plugins/DinkNarrative` (the two runtime modules, about 32,000
  lines), and `Source/DinkRemaster`. The review gave priority to code that runs every frame or on a screen change, a
  save, a load or a restart:
  - the story, director, gameplay and brain loops;
  - the creature, humanoid and family art presenters;
  - audio;
  - registered hardness;
  - environment decals and grass.
- **Read only where the game calls it:** `Plugins/DinkParity/Source/DinkProbe` (a developer module that is in the
  packaged development build) and Inkpot's `InkPlusPlus` runtime.
- **Not reviewed:** the editor-only `DinkImport` module, the tests, and the rest of the third-party code.
- **What was looked for:**
  - raw `UObject` pointers held across frames or garbage collection;
  - actors and components used after `Destroy` or across world teardown (PIE end, map travel, restart, exit);
  - timers, delegates and lambdas that capture `this`;
  - async loads (there are none in the runtime modules);
  - container references kept across an `Add`, and iteration while the container changes;
  - array indexing fed by data (map.dat, scripts, JSON, saves);
  - division by zero;
  - `check` and `ensure` that data can reach;
  - code off the game thread (only the two animation proxies, which copy their inputs on the game thread);
  - static state that survives a PIE session;
  - Slate widgets (there are none);
  - decal, instanced-mesh and component churn.
- **A13 and A14:** the mechanics QA stream (notes `mechanics-qa_15nov.md`, bug rows A13/A14 on its branch) diagnosed
  both from the core dumps as memory overwritten by someone else, or an unstable machine, with no Dink frame on either
  stack. It has no fix. This audit did not take them over. It did look for their writer in project code (see the end).

## Findings

Certainty:
- **certain:** the defect is in the code, and a concrete game path reaches it (or reaches it as soon as the data allows).
- **plausible:** a real hazard that the shipped data does not reach today.
- **theoretical:** needs malformed data or an impossible state; it was hardened only where the change was trivial.

Line numbers are from master `da511dbc`.

| # | File:line | Risk | Scenario | Certainty | Fixed? |
|---|-----------|------|----------|-----------|--------|
| R1 | `DinkNarrative/.../DinkStorySubsystem.cpp:1473` (`HandlePendingRestart`), `DinkRuntimeHardness.cpp:457` | Softlock; the old world leaks on every restart | (1) Visit any of the 38 registered-hardness screens (`DinkHardnessWorldV1`: SCR_031, 034, 156 ... 404, 408, 409, 417-419, 437, 440, 441 ... 765). (2) Die and choose *Restart game*, or restart from escape.c. (3) Enter that screen again. `UDinkGameplay::HardnessOwners` belongs to the game-instance story and survives `OpenLevel`, so the old world's owner refuses the new world's owner: "another retained body owner exists". The refusal holds the hardness loading gate (`SetIgnoreMoveInput(true)`), so the screen's scripts never run and Dink can never move again. The retained owner's `TStrongObjectPtr` prism components also keep the whole old world alive, which trips LoadMap's stale-world check (an ensure) and leaks a world per restart. | certain | Yes. `HandlePendingRestart` releases the owners (`ShutdownRuntimeHardness`) before `ResetRuntime`. As a defence, admission drops an owner whose world is not the current one instead of refusing the screen. The test `Dink.Gameplay.Restart.DeathMenuCreatesFreshPlayableWorldTwice` now visits SCR_417 before each death and checks after each restart that the screen is admitted and Dink can move. |
| R2 | `DinkNarrative/.../DinkAudioSubsystem.cpp:225` | Fatal error in a packaged game | A `sound:` cue with `repeat` set, for an approved take that is not a loop, made a looping `DuplicateObject` copy of the `USoundWave`. A duplicate is serialized without the cooked flag, and `USoundWave::Serialize` (engine `SoundWave.cpp:1306`) logs `Fatal` when a cooked platform loads uncooked audio. The editor does not take that branch, so tests never saw it. Today every repeat in the 1997 scripts is sound 34 and every `sp_sound` uses 23 or 34, and both are loops. One approval change would turn it into a crash. | certain (latent) | Yes, on master by #138/#144 (a repeat of a non-loop take is replayed; no `DuplicateObject` left). Not touched here. |
| R3 | `DinkCore/.../DinkArtFamilySubsystem.cpp:566, 607`; `DinkCreatureSubsystem.cpp:364` | UObject overwrite: a game-thread stall waiting on the render fence; weak pointers retargeted | `DressScriptSprite` destroys the script sprite's family mesh or effect card, then creates the new one under the same fixed name, either in the same call or on the next picture change. `DestroyComponent` does not rename. `NewObject` finds the garbage object under that name and rebuilds it in place (engine `UObjectGlobals.cpp` ~3565-3720: `ConditionalBeginDestroy`, a spin on `IsReadyForFinishDestroy`, `~UObject`, and the same index and serial). Outside the editor this logs "Gamethread hitch waiting for resource cleanup on a UObject overwrite ... Fix the higher level code". It happens when `sp_seq`, `sp_pseq`, `sp_pframe`, `sp_size` or `sp_brain` moves a dropped heap, a heart or a potion to another mesh, or between a mesh and an effect. `ClassCreature` has the same pattern after a failed `Configure`. | certain (pattern); the stall is measured by the engine, and no crash was traced to it | Yes. The names come from `MakeUniqueObjectName`. Nothing looks these components up by name: they are found by tag or class. |
| R4 | `DinkNarrative/.../DinkStorySubsystem.cpp:443` (`RemoveFinishedInstances`), reached from `:1051` (`ForceOriginalHardnessVision`) | Use after free of a script instance | `force_vision` on a registered-hardness screen re-enters the screen from inside a running script. `EnterScreen` ends every instance not attached to 1000 and frees it (`RemoveFinishedInstances`). If the `force_vision` caller was itself started by another script (`external`, `spawn`, `sp_script`'s `main`, a `hurt` that runs `hit`), the parent's `StepInstance` loop, `RunNow`'s `Outer` and the `external` lambda's `Ctx.Instance` still point at the freed parent, and `SwapOut` writes into it. The shipped scripts call `force_vision` only from `s1-brg2.c` `talk` and `s1-h1-o.c` `main`. Both are top-level instances, and SCR_001 is not a registered screen. | plausible | Yes. Removal is deferred while a script step runs (`CurrentInstanceId != 0`), and `Advance` and `RunUntilIdle` remove the instances after the step. Every reader already skips finished instances, so traces do not change; the probe passes SCR_404's `force_vision` (see below). |
| R5 | `DinkNarrative/.../DinkStorySubsystem.cpp:899-905` (set_callback_random loop) | Array reallocated under a range-for | `StartProcedure` inside the loop appends a new instance whenever `FindInstanceForSprite` does not match the idle instance. That is the case for an instance with `ParentId != 0` or `bEndWithProcedure`, and such instances are never idle, so the shipped data cannot reach it. | theoretical | No. Open PR #141 rewrites this loop (`stop_entire_game`): its author should iterate by index over the count at the start, as `for (int32 i = 0, n = Instances.Num(); i < n; ++i)`. |
| R6 | `DinkCore/.../DinkEnvironmentSubsystem.cpp:275` | Degenerate decal box in the decal pass (the A13 area) | A `decals.*.size_cm` of 0, a negative value or NaN in `environment.json` gave a ground decal an empty, inverted or NaN box. The box stays in the scene for the rest of the session. Shipped values are 90 and 120. Corpse decals were already validated. | theoretical | Yes. Such a row keeps the default size. |
| R7 | `DinkCore/.../DinkArtSubsystem.cpp:403-404, 416, 530` | Null dereference on a malformed art manifest | A `warp_overrides` or `postprocess` entry that is not an object, or a `hide_origins` placement without a card. | theoretical | Yes. Rows that are not objects are skipped, and a missing card is checked. |
| R8 | `DinkCore/.../DinkEnvironmentSubsystem.cpp:2046` | A hang of a frame or more | The grass grid is N x N per cell with N unbounded. A large `density_per_m2` or `dink.GrassDensity` stalls screen entry. | theoretical | Yes. N is clamped to 256. |
| R9 | `DinkCore/.../DinkArtSubsystem.cpp:600, 608` | UObject overwrite of a *live* component | `ApplyCharacters` has no guard against a second `characters.json` row for the same origin. Such a row would rebuild a registered, ticking `UDinkHumanoidComponent` ("AuthoredHumanoid") in place. The manifest has one row today. | theoretical | No. Noted for whoever adds character rows. |
| R10 | `DinkCore/.../Greybox/DinkGreyboxSubsystem.cpp:283-288` | Ensure on a duplicate dynamic binding | `ObserveDoorMovement` compares a weak pointer that is null for a pawn being destroyed, so it could `AddDynamic` twice on the same character (`TMulticastScriptDelegate::AddInternal` ensures). `Pawn::Destroyed` unpossesses first. | theoretical | No. |
| R11 | `DinkNarrative/.../DinkAudioSubsystem.cpp:247` | Map iteration while it could grow | The ambient-sound loop iterates the director's sprite map and calls `HandleCue`, then `GetActor`. For handle 1, `GetActor` can `Sprites.Add(1)`, but only when sprite 1 is missing, and the loop reaches handle 1 only when it exists. | theoretical | No. |
| R12 | `DinkCore/.../DinkCombat.cpp:59` | Integer overflow (undefined behaviour) | A missile strength above about 42.9 million, which only a script or save value could give. | theoretical | No. |
| R13 | `DinkNarrative/.../DinkRuntimeHardness.cpp:924` | Null dereference | `LoadEditorPictures` dereferences `State` after a check on the line before. Its only caller returns early on an invalid state. | theoretical | No. |
| R14 | `DinkNarrative/.../DinkGameplay.cpp:1622-1624` (`PaceScale`) | NaN pace carry | A sprite with speed 0 and a wanted pace of 0 gives 0/0. `PaceCarry` becomes NaN and the brain then thinks on every frame. No crash. | theoretical | No. |
| P1 | `DinkCore/.../Greybox/DinkGreyboxHardness.cpp:106-118` | Hitch, not a crash | The first `draw_hard` on a screen runs about 240,000 synchronous line traces. | performance | No. |
| P2 | `FaceCardsToCamera`, `UpdateLegacyCardVisibility` | Per-frame cost | They iterate all 5,846 placeholder actors every frame, or every 0.25 s. | performance | No. |

### Checked and found sound

The engine-behaviour claims in the table were checked against the engine source of 5.8.4.

- **The director's sprite map.** `TMap<int32, FDinkSprite>` moves its elements on every `Add`. Every
  caller that keeps a `FDinkSprite*` or `&` across something that can run a script finds the sprite again by handle
  afterwards: `RunThroughTagList`, `RunThroughTouchDamageList`, `RunThroughTagListPush`, `ProcessDamage`, `ThinkSprite`
  and `MissileBrain`. A scan of every such reference after `RunProc`, `StartProcedure`, `RunNow`, `HandleFor*`,
  `CreateVirtualSprite`, `ShowText`, `Animate` and `CheckIfMoveIsLegal` found only paths that return or `continue`
  first.
- **Sprite release and reset.** `ReleaseScreenSprites` and `ResetSprites` call `Destroy` on spawned sprite actors while
  they walk the map. No `EndPlay` or `Destroyed` in the project calls back into the director.
- **Script instances.** They are `TUniquePtr`, so addresses are stable. `load_game` is deferred to the next tick,
  `restart_game` to the next `Advance`, and `kill_game` quits through a hook.
- **Timers and delegates.** The `load_game` timer, the hardness world subsystem's lambdas, both console tickers,
  `WarpSuppressed`, the HUD and save delegates, the fact mirrors and the screen-change bindings capture weak pointers or
  are removed in `Deinitialize`/`EndPlay`. The input pre-processor holds a weak story pointer and is unregistered in
  `Deinitialize`. The Ink `OnError` lambda captures the `FDinkInkStory` that owns the `FStory`, and
  `VariableChanged.AddRaw` is removed in its destructor.
- **Late tick functions.** `FDinkHumanoidPresentTickFunction` and `FDinkCreaturePresentTickFunction` check
  `IsValid(Target)` and are unregistered with their owner. Tick prerequisites are added with `AddUnique` and hold a weak
  object.
- **Animation worker threads.** `FDinkCreatureAnimProxy` and the body proxy copy their raw `UAnimSequence*` layers in
  `PreUpdate` on the game thread. The sequences are kept alive by `HeldAssets`, the subsystem's `ClassAssets` and the
  body instance's clip properties. There is no other code off the game thread.
- **Corpse and decal churn.**
  - Corpse meshes and pool decals are created once per kill on one holder actor, with unique names, and destroyed on a
    screen change (`ClearCorpses`).
  - Ground decals are made once per placement per session (`DecalScreens`, and the card is hidden afterwards).
  - Both kinds take a material that was checked to load and a positive box.
  - Nothing creates decals per frame on master. The duck trail of PR #113 is not on master.
- **Data-fed indexing and division.**
  - Inventory slots, font colours, the `Diagonals` table and `RandomModulo` (0 for n ≤ 0) are bounds-checked.
  - The runtime-hardness and foundation sidecars, JSON vectors and the family `Family[0]` index are validated before
    use.
  - Integer divisions take constants or checked divisors.

### A13 and A14: what this audit adds

The A14 core showed eight doubles written over a freed Ink object: three positions about 4 cm apart, at a height of
about 110 cm. No project code keeps a heap history of `FVector` positions:
- `FDinkMotionEstimate` keeps time/path pairs;
- the body smoother and the body dynamics keep one position and one velocity;
- the wall probe's three points live on the stack;
- the warp component's retry map holds unit directions.

No reference into a `TArray<FVector>` is kept across a reallocation. R4 is the one use-after-free found in project code.
It writes script-instance fields (Ink flow names, locals), not positions, and the shipped scripts do not reach it, so it
does not explain A14.

The same holds for A13: R3's overwrite and R6's box are the only things project code does to the scene's components
that could plausibly upset the renderer. Neither is consistent with a SIGILL on a legal instruction.

The coordinator's lead was that the doubles are a sprite moving one 1997 pixel per frame. Checked against the A14 core
(mechanics QA's copy):
- **No other copy.** The eight doubles appear nowhere else in the process: an exact search, and a scan for any
  `(x 25..50, y 1100..1300, z 100..120)` triple. The only other copy of one value is in the crash handler's saved
  register file, where `mi_free` loaded it as a pointer.
- **Not world positions.** The crashed process was a rendered capture (`dink.CaptureScript duck_after.txt`, on SCR_471
  and SCR_374). Every game screen lies hundreds of metres to kilometres from the origin: SCR_374's corners are at
  (884 m, 265 m), SCR_471's at (943 m, 384 m), SCR_001's at (-1851 m, 3918 m). So (0.37 m, 11.9 m, 1.1 m) is a
  position in some local frame: a component-relative location, a position against a screen corner, or a space near the
  origin.
- **What that rules out.** It excludes every candidate that stores world positions:
  - the body smoother (`FDinkBodySmoother::Position`);
  - the creature component's quarter-second speed average (scalars only, on #113's branch as it was then: the
    `DinkCreatureComponent.cpp` of the crashed copy is dated 02:36, before the 03:04 crash);
  - #113's blood drops and flying parts (`StepGore`: world locations; its element references are not kept across an
    `Add`);
  - camera follow;
  - the walk-audit samples (PR #129, not in that build).
- **What is left.** No project code keeps a local-frame position history either. The writer stays unidentified, and
  nothing in #113's code needs a change for A14.

## Dynamic checks

All runs were in a private project copy, through the machine's Unreal queue.

**Reproduction, without the fix.** Base: master `da511dbc`, world regenerated, only the extended test built. Command:
`Scripts/test.sh Dink.Gameplay.Restart`. Result: **0/1 pass**. `DeathMenuCreatesFreshPlayableWorldTwice` fails.
- **Cycle 0, before the first death:** SCR_417 is admitted, and Dink can move there.
- **First restart:** LoadMap reports "Previously active world ... `UEDPIE_0_L_Greybox_World_Joppa` not cleaned up by
  garbage collection". The reference chains lead from `DinkHardnessPrismComponent ... HardnessV1_S417_C001_1` and
  `_C002_1` (refcounted<1>: the retained owner's `TStrongObjectPtr`) through `DinkGreyboxScreen_4` to the old world.
- **Cycle 1, after the restart:** "SCR_417 is a registered original-hardness screen" is false, and "cycle1: SCR_417 was
  never entered". The leaked world still holds SCR_417's level, so the restarted world has no SCR_417 host at all.
  R1 in practice is therefore worse than the refusal the review predicted: the screen's level is missing after a
  restart.
- Log: `Saved/Logs/test_repro_restart.log` of the copy.

**With the fixes.** Base: master `ce528c62` with this branch, world regenerated (`--region all`, then `--region
stonebrook`).
- **Build:** OK, 0 warnings, 105 s.
- **`Dink.Gameplay.Restart`:** 1/1 pass, 38 s. Both cycles admit SCR_417 and Dink moves there. No "not cleaned up by
  garbage collection" error is logged.
- **`Dink.Gameplay.Probe`:** 29/29 pass, 1 with warnings, 631 s. All twenty chapter md5s equal the table in
  `Plugins/DinkParity/Docs/packaged_probe.md`: Ch1 b4ad88c02c ... Ch10 23fd57dfdc, Ch11 0d70cebfcd ... Ch20 84f33687af.
  Ch1 includes SCR_404's `force_vision`, the path R4 changes.

**Not run:**
- the `gc.CollectGarbageEveryFrame 1` targeted run;
- the full Dink suite;
- the packaged probe;
- a soak.
## Not covered

- The editor-only `DinkImport` module, the tests, and third-party code beyond the calls the game makes into Inkpot.
- An ASan build, `-stompmalloc` (too heavy for this machine), and a soak.
- Open PRs: #113, #128/#129 and the 15 Nov fix PRs #137-#146 were read only where they touch the same lines (R2 and R5
  above).
- The rendered or packaged game.
