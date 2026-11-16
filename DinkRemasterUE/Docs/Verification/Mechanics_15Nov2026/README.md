# Mechanics QA: the 1997 feel under the photoreal presentation (15 November 2026)

Audit of the hero's input, the attack, missiles, monsters and the presentation against `source/dink/dink.cpp` (RTDink,
locked at 60 Hz: dink.cpp:17300-17318), and of the crash reports of the private copies of 13-15 Nov. Bug list rows
A72-A76 (new) and A6, A13, A14, A15 (updated) in `doc/remaster/ALPHA_BUG_LIST.md`.

## Mechanics checked

| Mechanic | 1997 (dink.cpp) | Remaster before | Remaster now |
|---|---|---|---|
| Walk speed | 3 px a frame, 180 px/s (17304-17318, move() 13557, human_brain 15013-15036) | player keys 170 cm/s (17 px/s in towns, 25 in the wild, 39 indoors); run key 600 cm/s (60 / 87 / 137 px/s); bot and scripts 600 | unchanged (owner decision of 12 Nov, "Animation pass 2"); measured, A75/A76 |
| Start / stop | full speed on the key's first frame, stands on the frame it is released | walk: 95 % of 170 cm/s after 0.19 s, stops in 0.10 s over 7 cm; run: 95 % of 600 cm/s after 0.65 s | unchanged (owner gait decisions); numbers here |
| Diagonal | 2 + 2 px against 3: 0.943 of straight (15044-15070) | 1.000 | 0.943 for a key or d-pad diagonal (sticks keep their magnitude) |
| Facing for attack / spell / bow | dir set on the key's frame (changedir, 15013-15070), read at once by `use` (14812-14820) | the pawn's forward vector, turning at 300 deg/s: up to 0.6 s late after a reversal | the previous frame's key direction at once (the attack key is read before that frame's keys, 14812 before 15013); the pawn turns to it on that frame; player keys turn at 900 deg/s; nothing recorded while a menu or freeze ignores move input (14744-14757) |
| Moving during a punch / spell | none: `sp_nocontrol` (item-fst.c, item-fb.c) until the sequence ends (14742, 16958), 400 ms for the fists | walked / ran through it | stands still for the sequence (`EDinkPlayerHold::Rooted`) |
| Moving with the bow drawn | none; the keys turn him (process_bow, 14568-14598, 14761-14766), a diagonal holds 100 ms against a single key, no key no turn | walked; aim from the pawn's forward vector | turns only (`TurnOnly`), with process_bow's 100 ms diagonal hold |
| Melee damage | (str / 2) + rand % ((str + 1) / 2) + 1 (15567), then - defense, a 0 becomes 1 half the time (hurt_thing 6656-6667) | same (`DinkRules::MeleeBaseDamage`, `ApplyDefense`) | same |
| Melee reach | hardbox + 5/10 px, + 28 px ahead (36 up/down), `sp_range` widens (run_through_tag_list 15460-15530) | same (`RunThroughTagList`) | same |
| Hit timing | the attack sequence's hit frame: 175 ms for the fists, 400 ms lock | same (`Dink.Gameplay.PlayerAction` tests) | same |
| Hit flash / knockback | none (hurt_thing and the brains only change hitpoints; no push) | none | none |
| Damage numbers | white number over the monster, 1 s rising (draw_damage 12339-12356; brains 9, 10, 16, 3, pig 13369, Dink 14699); yellow experience 30 px higher (add_exp 623-644) | not shown (DinkBrains.cpp: "not ported") | shown (`UDinkFloatingNumbers`), presentation only |
| Monster speed | 1 px a think; think every `sp_timing` ms: pillbug / slayer 60 px/s, bonca / stone giant 30, hammer goblin / dragon 15 | same in pixels: 4.1 m/s for a pillbug in the wild (6.9 cm/px), 6 m/s in a town | unchanged; ratio to Dink reported (A75, owner decision) |
| Bow draw | 7 power a 60 Hz frame after the first status tick, 500 = full (14600-14612) | same (`Dink.Gameplay.Bow.*`) | same |
| Push | starts against hardness other than low (13525-13537) after 600 ms | same since round 2 (A5) | same; #129's player-only blockers are only on unscripted placements, so pushable rocks (scripted) are untouched |
| Missiles vs doors | a map.dat warp's hardbox reads 0 for sprites (get_hard 569-575) | fixed in round 1 (A2) | same |
| Creature play rate (A6) | - | stale by one frame, jittery | fixed on PR #113's branch, not on master |

## Measured (test `Dink.Mechanics.HeroInputParity`, PIE, Stonebrook map, yard of screen 439)

First run (`mech1`, private copy at master 0bf319c9 + this branch, world of 283cd155, 15 Nov 12:42):

| Item | Result |
|---|---|
| M1 walk from a standstill | top 170.0 cm/s, 95 % after 0.192 s; stops in 0.100 s over 7.3 cm (1997: full speed on the first frame, stops on the frame) |
| M3 key diagonal | 160.3 cm/s = 0.943 of the straight walk (1997: 0.943) |
| M4 reverse and punch on the same frame | passed: the punch took the new keys' dir at once, Dink was held (`Rooted`), the walk stopped on the press (0.0 cm/s), drift during the punch 0.0 cm, the keys walked again after the 400 ms |
| M2 run, M5 bow, M6 fed movement, M7 numbers | not measured in that run: the test drove the run key with `SetRunKeyHeld` (the pawn polls the real key each frame, so it stayed a walk) and pressed attack twice without a release (the attack gate takes that for an OS repeat, so the bow was never drawn). Both are test-harness errors, fixed in the test (a real key event; a release after the punch). The re-run is queued behind the machine's Unreal lock. |

Whole suite on the PR head (master ec86f1e6 + this branch, built 0 warnings, world regenerated with this importer:
`--region all --export`, then `--region stonebrook`), 15 Nov 17:30-17:47: **285/286 passed** in 1,023 s. The one failure
is this test's run phase: it ran north for 2 s and reached the yard's fence, so the speed at its end was 0 (the top
speed was reached: 95 % of 600 cm/s after 0.648 s). Every other phase passed: M3 159.9 cm/s = 0.941 of straight, M4
(punch on the reversal frame, 0.0 cm drift, walks again after), M5 (bow: turns, does not walk), M6 (fed movement keeps
the 300 deg/s turn and the forward-vector facing, not rooted), M7 (a 4-point hit shows "4" for one second). The run
phase now stops at its top speed (about 5 m); re-run queued.

**Current head** (master ce528c62 + this branch, private copy, 15 Nov 21:24-21:31): build OK, 0 warnings;
`Dink.Mechanics+Dink.Movement+Dink.Input+Dink.Gameplay.Bow+Dink.Gameplay.PlayerAction` **21/21 passed**, including
`Dink.Mechanics.HeroInputParity` with M5b (process_bow's 100 ms diagonal hold, no key no turn). Numbers of that run:
walk 95 % after 0.198 s, stops in 0.098 s over 7.3 cm; run 600 cm/s, 95 % after 0.652 s, stops in 0.177 s over 37.1 cm;
key diagonal 0.943; punch hold drift 0.0 cm.

Re-run with the review fixes (head 69657673 on 49627fc9 in the private copy, 15 Nov 19:5x): `Dink.Mechanics.HeroInputParity`
**1/1 passed**: M1 walk 170 cm/s, 95 % after 0.192 s, stops in 0.100 s over 7.3 cm; M2 run 600 cm/s, 95 % after
0.642 s, stops in 0.183 s over 37.4 cm; M3 key diagonal 160.3 cm/s = 0.943; M4 punch on the frame after the reversal
key takes the new dir, 0.0 cm drift; the same-frame press takes the previous dir; keys under ignored move input record
and turn nothing; M5 bow turns, does not walk; M6 fed movement unchanged; M7 numbers for a monster (4) and for Dink (3),
gone after 1 s.

Probe (`Dink.Gameplay.Probe`, in that suite): all twenty chapter traces equal the table in
`Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 b4ad88c02c ... Ch10 23fd57dfdc, Ch11 0d70cebfcd ... Ch20 84f33687af).

## Rendered checks (private display :189, `-nosound`)

Second run (15 Nov 21:1x, editor game of the private copy at master 6ef7a590 + this branch; before it, in the same
Unreal step: build OK 0 warnings, `Dink.Mechanics+Dink.Movement+Dink.Input` **15/15 passed**). Life raised before
entering SCR_030 (three pillbugs, strength 3). Looked at every frame (`s0*`, `m0*`); kept here:

- `scr30_damage_numbers.jpg`: after the bot-path punches (`dink.Attack`) white **2** and **3** float over the pillbugs
  that were hit (strength 3: 2-3 damage, several bugs in the box at once, as run_through_tag_list does), and Dink's own
  **8**s (pillbug touch damage) rise over him in a column, older ones higher. Readable at the play camera, with a dark
  shadow. Dink's numbers start well above his head (the top of the pawn's bounds plus 15 cm, then an 80 cm rise); the
  1997 number starts on the sprite's upper third: a placement tune, not changed.
- `scr30_dink_damage_numbers.jpg`: Dink facing west after a tap of A, the pillbugs left of him, two 8s over him.
- `scr30_walk_east_then_punch.jpg`: holding D (east) and pressing F: Dink faces east with the fists up, standing (the
  frame does not show motion; the hold is measured by the test, M4).
- `first_run_dead_on_arrival.jpg`: the first run (19:4x): Dink entered SCR_030 at level 1 before his life was raised
  and died at once; the death menu covers every key-driven frame of that run, which is why it was repeated. The pillbug
  bodies overlap Dink's body and each other in both runs (sent to the physical-mapping stream).

Not seen in a frame: the bow's turn on the spot and the punch on the frame after a reversal (both only in the test).

A15 (see also A57), screen entries in the rendered editor game of the first run (master 49627fc9 + this branch;
`dink.CaptureScript`, longest frame within 4 s after each `dink.Goto`,
uncapped, about 70-85 fps):

| Screen | pass 1 (first entry) | pass 2 (again) |
|---|---|---|
| 439 | 201.7 ms | 43.6 ms |
| 471 | 41.1 | 19.6 |
| 30 | 15.1 | 15.6 |
| 64 | 108.6 | 14.2 |
| 239 | 31.0 | 18.7 |
| 278 | 129.2 | 107.9 |
| 97 | 55.0 | 15.6 |
| 1 | 18.5 | 18.5 |
| 432 | 47.0 | 21.2 |
| 624 | 44.2 | 24.3 |
| 537 | 39.9 | 25.9 |
| 156 | 118.6 | 109.3 |

Most first-entry hitches go on a second entry (editor-only work on first use: mesh compile waits, shader and DDC work);
278 and 156 keep about 110 ms on every entry, which is per-entry work (dressing, spawning), not first use. The packaged
build was not timed (no package of this branch; Unreal lock).

## Crashes and ensures of 13-15 Nov (all private copies)

Read from every private copy's `Saved/Crashes` and from systemd-coredump (`coredumpctl list --since 2026-11-12`); cores
opened with gdb against the engine's `.debug` files. All nine are rendered editor games (`UnrealEditor ... -game`); none
has a Dink function in the faulting thread. Headless test and import runs (`UnrealEditor-Cmd`) left no core from 13 Nov on
(the last, 12 Nov, was a test's own bug, `FDinkScriptCharacterProfileTest`); the many `dotnet` SIGABRT cores are
UnrealBuildTool processes, not the game.

| When (PST) | Copy | Fault | What the core / report shows |
|---|---|---|---|
| 13 Nov 22:14 | Gate2Ground | SIGSEGV in `_Unwind_Backtrace` | the crash handler itself faulted while walking a stack |
| 13 Nov 22:20 | Gate2Ground | SIGSEGV, Renderer +0x22a7ae0 | null write in the renderer during a capture on SCR_624 |
| 14 Nov 00:46 | Gate2Static | SIGSEGV `USkeletalMesh::ComputeActiveClothingAssets` | A9 (mitigated in round 2) |
| 14 Nov 03:00 | Gate2Ground | SIGILL at `DecalRendering::BuildRelevantDecalList` +0 | A13: the bytes at the faulting address are `55 41 57` (push rbp; push r15), a legal instruction |
| 14 Nov 03:04 | Gate2Creatures | SIGSEGV `mi_free` from `Ink::FObject::~FObject` at exit | A14: bytes 16-80 of a live Ink object overwritten with eight doubles (a use-after-free write by someone else) |
| 14 Nov 04:00 | Gate2Creatures | SIGSEGV `FScene::InvalidatePathTracedOutput` (render thread) | no report folder (the handler crashed in `_Unwind_Backtrace`) |
| 13 Nov 22:32 | Gate2Characters | SIGSEGV `GetPerTrackCompressionPoseTranslations_avx512skx` | animation decompression |
| 14 Nov 16:16 | DinkGroundRelief | SIGSEGV `TBitArray::GetData` in `Nanite::FRenderer::PrepareRasterizerPasses` (virtual shadow maps) | |
| 14 Nov 19:18 | Gate2Static | SIGSEGV `FSharedReferencer` dtor in `Chaos::FPBDRigidsSolver::ApplyCVars` | physics thread |

Reading: crashes in five unrelated engine subsystems, a SIGILL on a valid push and a live object overwritten by stray
doubles are the signature of heap corruption or of an unstable machine (CPU or RAM; Ryzen 5 7600X, no machine-check
events in the kernel log), not of a decal, an Ink or an animation setting. Nothing in the project's code was found that
writes positions through a stale pointer (searched: element references held across array growth, raw buffer writes);
the writer is not identified. Next tools: an ASan build of the project modules run with `-ansimalloc` (the engine
modules stay uninstrumented), or a memory test of the machine by the owner. `-stompmalloc` is compiled in but needs a
page per allocation, which does not fit 30 GB with the editor.

Ensures: the only ensure in the logs of the last two days is `Scalability.ini can only set ECVF_Scalability console
variables ('dink.GrassDensity'='1.0' is ignored)`, 40 times in the packaged probe logs of 14 Nov (every start). Fixed:
`dink.GrassDensity` is `ECVF_Scalability`, so the effects-quality levels of `Config/DefaultScalability.ini` now apply.


## Not checked

- A gamepad stick (analog): only keys and the d-pad were reasoned about; the diagonal rule applies to |x| = |y| = 1 only.
- Monster sprite cards and missiles are moved in the simulation's 60 Hz pixel steps (`UDinkDirector::SyncActorToSprite`);
  humanoids and class creatures are smoothed (`FDinkBodySmoother`), cards are not. At render rates other than 60 Hz they
  step. Not changed (a presentation-only smoothing needs a present tick after the story subsystem, as the humanoids
  have); open.
- The camera's outdoor headroom lift and the spring arm's collision pull-in are applied per frame without easing
  (`UDinkInteriorCameraComponent::UpdateOutdoorHeadroom`); looked at in code only, beyond the frames above.
- `dink.Monster.PaceCmPerSpeed` (A75's review switch) was built and is off by default; not played with it on.
- Death and respawn, magic, push and missiles were checked by reading the ported code against dink.cpp and by the
  existing tests (`Dink.Gameplay.*`, `Dink.Input.*`), not by new measurements.
