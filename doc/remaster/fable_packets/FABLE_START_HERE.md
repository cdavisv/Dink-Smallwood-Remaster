# Fable art work: start here (prepared 15 Nov 2026 for the Fable 5.2 sessions from 21:00 PT)

Every row of `doc/remaster/FABLE_ART_QUEUE.md` (GP-Q1..Q10 from the gore audit, VS-01..14 from the visual sweep) and the
review rows CG-1..CG-6 (PR #113, duck/slime/pig) and WB-1 (PR #126, water banks) has a work packet here: `<row-id>.md`
with the 1997 frames (`ref/<row-id>/`, extracted from the original graphics, plus `strip.png`), real size, every
placement it covers, the exact sources and **unpushed half-done branches** to start from, import command and binding
row, capture commands, gore bar, dependencies and size. 31 packets. Read your stream's packets in order.

## Rules (all of them bind every stream)

1. **Fable 5.2 only.** Art design and every Blender step happen only in a Claude Fable 5.2 session (owner rule). If your
   system prompt names another model, do no art judgement and tell the coordinator. Code-only parts of a packet
   (marked "NOT Blender" / "not art") may be done by any model.
2. **Unreal lock.** Every Unreal step (build, import, test run, capture, game) runs through
   `<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh <command...>`, one step per call, never a chain, from your
   own private project copy (`<shared>/DinkRemasterUE/Saved/<Name>/DinkRemasterUE`, reflink copy without `Saved/`, rebuilt
   if C++ changed, `_Generated` regenerated: `rm -rf Content/Dink/_Generated` keeping `RuntimeHardnessV1`, then
   `Scripts/import_greybox.sh --region all --export` and `--region stonebrook`). Never build or commit in the shared
   checkout. Rendered checks only offscreen (`run_capture.sh`) or on a private Xvfb display; the game never plays
   through the owner's speakers (SDL dummy audio or move/mute its sink-input at once). Never touch
   `DinkRemaster-master` (the owner's build). `<shared>` = the shared checkout named in `COMMON_RULES.md`.
3. **Blender limit.** At most three `blender` processes on the machine (`pgrep -xc blender` < 3 before you start), one
   per session, `blender -b -t 4 --python x.py`, Cycles on the GPU per `PhotorealPass/CYCLES_GPU.md`. Pull LFS sources
   first (`git lfs pull --include <paths>`): a 132-byte pointer read as a texture gives garbage. CC0 downloads only from
   Poly Haven and ambientCG, logged in `PhotorealPass/ThirdParty/downloads.csv`; no generative image models.
4. **Gore rule.** Keep all 1997 gore and dark comedy at least at the 1997 level; never sanitise, soften or shrink. A
   mesh, pool or burst with less red, smaller extent or fewer drops than its 1997 picture is a defect and is not bound.
   Each gore packet has a "Gore bar" section: put the 1997 frame beside your game frame in the PR evidence.
5. **Squash and scrub before push.** Never push WIP history. Start every PR branch from current `origin/master`, copy the
   finished files in (from the old worktrees too: read them, do not work inside them), then
   `python3 -I DinkRemasterUE/Scripts/scrub_private_paths.py --fix <paths>` (paths relative to the repository root) and
   `--check` (whole tree), `python3 -I tools/lfs_audit.py HEAD` (0 missing), the old-history check of `COMMON_RULES.md`
   (prints 0), one or a few clean commits, author/committer the GitHub no-reply address,
   `git -c core.hooksPath=/dev/null commit`, no AI co-author line. Importers and Blender write home paths into
   `.uasset`, `.fbx`, `.blend`, `.png`. PR body ends with the Claude Code line. Do not merge; the coordinator merges.
6. Gameplay, collision, hardness, scripts, warps and probe traces stay as they are (presentation only). Before each PR:
   `Scripts/test.sh Dink.Art`, the probe (twenty md5s of `Plugins/DinkParity/Docs/packaged_probe.md` equal), unit tests,
   `art_coverage.py` before/after, evidence under `DinkRemasterUE/Docs/Verification/<Topic>_<date>/` with a README that
   says what you looked at and what you did not check. Write a dated line in the Master log of `COMMON_RULES.md` when you
   take a stream and when you open a PR; keep a notes file as `COMMON_RULES.md` says.

## Four streams (no two on the same asset or source files)

| stream | packets, in order | owns (files nobody else edits) | starts from |
|---|---|---|---|
| **A, monsters** | VS-04 + GP-Q1 + GP-Q2 (first PR: bonca, slayer, stone giant with corpses), VS-03 (dragon), GP-Q3 (goblins) | `creatures.json` monster rows, `Unclaimed/{bonca_gray,slayer,stone_giant,dragon,goblin_*,npc_knight_blue}`, `Unclaimed/tools/{clips_*,corpse_blood,export_monster_ue}.py`, `/Game/Dink/Photoreal/Creatures/{Bonca,Slayer,StoneGiant,Dragon,Knight,Goblin*}` | unpushed `art/creature-monsters` (worktree `DinkGate2Creatures`) |
| **B, gore and remains** | GP-Q5, GP-Q6, VS-08, GP-Q10, GP-Q7, GP-Q4 (people), then after PR #113 merges: CG-1, CG-2, CG-3, CG-4, CG-5 | `PhotorealPass/Corpses/**`, `Props/Decals/**` + `Props/tools/decals.py`, `environment.json` `decals`/`hit_blood` keys, `/Game/Dink/Photoreal/Corpses`, `Creatures/{Duck,Pig,Slime,Gore}` + `Creatures/Tools` | `art/stonebrook-mother-burnholes` `d404721d`, `art/gate2-static-decals`, `art/gate2-static-ground-holes`, `art/blood-decals-1997` |
| **C, structures** | VS-01 + VS-02 Goodheart + VS-05 + VS-14 bridges/wells (first PR: the structure sets), VS-06 church, VS-07 chest, VS-10, VS-02 snow castle + VS-12 snow isle, rest of VS-14 | `Scripts/assemble_structures.py`, `structure_sets.json`, `Scripts/PhotorealQA/structure_walk_check.py`, `PhotorealPass/Structures/**`, `/Game/Dink/Photoreal/Structures`, `Unclaimed/{church*,log_cabin*,snow_house_*,gold_coin,shop_sign}`, `Props/Chest_*` | unpushed `art/gate2-static-structures` (worktree `DinkGate2StaticStruct`), `art/gate2-static-modes` + `art/gate2-static-nuttree` (worktree `DinkGate2StaticModes`) |
| **D, ground, water, effects, hero** | GP-Q8 (Dink's death clip), GP-Q9 + CG-6 (explosions, burst 164), VS-11 (fountain), WB-1 (water rim), VS-09 (ground edges), VS-13 (caves) | `Characters/Animations/AnimationPassV1/**` (death clip only), `hero_actions.json`, `Unclaimed/{explosion_fx,fire_burst_fx,fireball_fx,fountain_spray_fx,hearth_fire}`, `export_import_bundle.py` mask code, `M_Env_Terrain` / `terrain_layers.json`, `environment.json` `indoor`/`water_tiles` keys, `WallKits/**` | master; `anim/hero-mannerisms` (worktree `DinkHeroMannerisms`) for the faceplant clip as a model |

**Shared registry files** (several streams append to them): `families.json`, `environment.json`, `creatures.json`
(A: monster rows; B: duck/slime/pig rows only, after A's first PR), `IMPORT.md`, `AGENTS.md`, `art_coverage.py`,
`doc/remaster/ALPHA_GATE2_BACKLOG.md`, `FABLE_ART_QUEUE.md`. Edit only your own rows/keys/sections, rebase onto
`origin/master` right before pushing, and whoever pushes second resolves. `Content/Dink/Photoreal/Unclaimed/M_Struct_Baked.uasset`
is rewritten by any Unclaimed kit import: tell the coordinator before committing it.

**Suggested order across the streams** (gore and story path first): A1 (bonca/slayer/giant + corpses) | B1 GP-Q5 (small,
nearly done) then B2 GP-Q6 | C1 structure sets (VS-01/02/05/14) | D1 GP-Q8 if `fix/playthrough-qa` has merged, else
D2 GP-Q9. Then each stream continues down its list. Big items: VS-04, VS-02 snow castle, VS-09, VS-12 (L).

## Outside dependencies (not Fable work, watch them)

- PR #113 (duck, slime, pig; an Opus agent is finishing it today): CG-1..CG-6, GP-Q7 duck parts, and the creature import
  section A uses. `fix/gore-story-parity` (hit blood, card-sized actor decals): GP-Q6, GP-Q10. `fix/playthrough-qa`
  (death collapse stop-gap and its test): GP-Q8. `fix/water-sea-colour`: WB-1, VS-09. The people port of the
  characters stream (`art/mother-age-lines` `de6d412a` committed locally, people PR stacked on it): VS-14's figures.
- Code that art cannot replace: gore-audit C1 (present kill sprites of unbound/brain-16 sprites) is needed before
  GP-Q4's people corpses can show; CG-6 needs one code decision (who draws the 164 burst for a class creature).

## Rows that are already done or are not (Blender) art

- **GP-Q5**: made, `Dink.Art` 63/63 and probe 29/29 on 14 Nov; only rebase, recheck, one colour judgement, push.
- **VS-01, VS-02 (Goodheart), VS-05, VS-14 bridges and wells**: assembled from existing meshes on the unpushed
  structures branch (57 screens, tested in an integration copy); finishing is mostly code and a look pass. Not covered:
  log cabin of 251, snow castle, bridge deck of 533, totem poles.
- **VS-14 dark figures of interiors 2 and 4**: the old man and the woman are bound as 3D people on the characters
  stream's unpushed people branch. Arrows of 663: unpushed mounted-rows branch.
- **VS-07 small chest**: a binding job (meshes exist); only the medium chest needs a model.
- **VS-10**: nut tree done on an unpushed branch; the talking oak S693_P06 is a binding question; S766_P04 is a well (VS-14).
- **GP-Q7**: pillbug corpses and duck parts are bindings of existing meshes; only the dragon 212 remains are new.
- **GP-Q4**: four of five people's bodies exist in the corpse kit; the blocker is code C1; only the Joppa mother 365 is new.
- **WB-1, VS-09**: world-export mask code, no Blender (needs a look judgement). **VS-13** light level: `environment.json`
  values, no Blender (any model); only the wall dressing is art.
- **CG-6**: the grey cylinder is the engine's burst sprite 164 without an effect row: part of GP-Q9.

## Where the unpushed work lives

Branch and worktree names are given in each packet; the worktrees sit in the usual work folder beside the others named in
`COMMON_RULES.md`, the private copies under `<shared>/DinkRemasterUE/Saved/` (`Gate2Static`, `Gate2Creatures`,
`CorpseGore`). Absolute paths and the captures of those branches are listed in the git-ignored
`<shared>/DinkRemasterUE/Saved/Gate2Coord/FABLE_LOCAL_PATHS.md`. Several of those branches exist only on this machine:
take a stream over by copying its files into your own clean branch early, so nothing is lost.
