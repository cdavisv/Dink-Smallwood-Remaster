# Dink Smallwood UE5 remaster: architecture, pipeline and scope critique

Nothing was created or modified. The figures below come from reading `dink.h`, grepping `dink.cpp` and the 380 scripts, and parsing `dink.dat`/`map.dat` in memory; my counts match yours (644 screens, 74 indoor, 5,846 placements, 93 warps, 191 placed scripts).

## 0. Where I disagree with your leanings

| # | Verdict | Why |
|---|---|---|
| 1 | Agree on locking 5.8; treat Lumen/Nanite on Deck as unproven | Never migrate to UE6 mid-project. Prove a Deck frame budget before any art is built on it. |
| 2 | Uniform 4× is wrong | 570 outdoor screens × 60 × 40 m is about 1.37 km² to dress, with an average of 9 props per 2,400 m². Use a per-region scale: about 2.5–3× in wilderness, 4× in settlements, about 1.5–2× in interiors. |
| 3 | Agree, and it is the best idea in the plan | Add a layout stage, because grid adjacency is not real adjacency (see B). |
| 4 | Half agree | No runtime DinkC interpreter is right. Rebuilding every cutscene by hand in Sequencer is the expensive route: `move_stop` appears 216 times in 53 scripts. Shipping the HD engine as "Classic Edition" has a licence problem. |
| 5 | Skip GAS; State Trees yes; motion matching for the hero only | GAS's main payoffs (prediction, replication) are worth nothing in single-player. |
| 6 | MetaHuman is a trap here | See D. |
| 7 | One public demo, then at most three "Act" drops | Every public release creates save-compatibility and support obligations. |
| 8 | Fine | Use a host with LFS locking (Forgejo/Gitea) and keep `.blend` sources in a separate LFS repo. |

**Classic Edition licence problem.** `LICENSE.md` clause 5c says some sound effects have unclear redistribution status. Clause 5d authorises the complete media package only for the official app. Clause 2 requires an in-app attribution if you ship its source. The cheaper route is to link to the official free HD release rather than bundle it.

## A. Architecture

**Key insight from the source.** The original save (`player_info` in `dink.h`) is only player stats, inventory, the global variables, and `spmap[769]`. `spmap` holds per-screen, per-sprite overrides: `editor_type` 1–8, where 6/7/8 respawn after 5/3/1 minutes (`fix_dead_sprites` in `dink.cpp`). If you copy that model, the world is a pure function of facts plus overrides, and you never serialise actors.

**Modules** (project plugins, so the base game builds without the expansion):

| Plugin | Type | Contents |
|---|---|---|
| `DinkCore` | C++ runtime | Facts, world state, screen cells, stats/actions, inventory, interaction, save |
| `DinkNarrative` | C++ runtime | Ink wrapper, director command runner, barks, conversation and stage cameras |
| `DinkImport` | Editor (C++ shell + Python) | JSON to actors/assets, validators, commandlets |
| `DinkParity` | Dev-only | Automation tests, coverage reports |
| `DinkExpanded` | Content plugin | All non-original content, off for parity builds |

**Content layout.** `/Game/Dink/{Core,Hero,NPC,Enemies,Kits,Biomes,Items,Magic,UI,Audio,Cine,Data}`, `/Game/Dink/World/{Overworld,Interiors/<Region>}`, and `/Game/Dink/_Generated/` (importer-owned, never hand-edited).

**Core classes:**

| Concern | Class | Notes |
|---|---|---|
| Facts | `UDinkFactSubsystem` (GameInstance) + `UDinkFactRegistry` | `TMap<FName,int32>` keyed by original names (`story`, `old_womans_duck`, `s2-nad`…). `FDinkFactCondition{Fact,Op,Value}` is reused by Ink, State Trees and spawn rules. |
| World overrides | `UDinkWorldStateSubsystem` | `TMap<FDinkOriginId, {State, Timestamp}>`; a 1:1 port of `editor_type`. |
| Screen cells | `UDinkScreenSubsystem` + `ADinkScreenVolume` | Keeps the screen as a logical unit: enter/exit events drive spawn reset, per-screen music, `&vision` variants and locks. |
| Traceability | `UDinkOriginComponent` | `S{screen:03}_P{sprite:03}`, script name, source hash, on every imported actor. |
| Interaction | `IDinkInteractable` + `UDinkReactionComponent` + `UDinkReactionSet` | Verbs mirror the DinkC handlers (157 `hit`, 142 `talk`, 68 `die`, 41 `touch`, 4 `push`). Reaction sets resolve through GameplayTag inheritance, so any hittable prop gets a one-liner by default. |
| Combat | `UDinkStatsComponent`, `UDinkAction`, `DinkCombat::ResolveDamage` | Port the original damage formula into one C++ function. |
| Definitions | `UDinkItemDefinition`, `UDinkMagicDefinition`, `UDinkEnemyDefinition`, `UDinkLootTable` | PrimaryDataAssets. Enemy stat blocks come straight from `en-*.c`. |
| Inventory | `UDinkInventoryComponent` | 16 + 8 slots, referenced by PrimaryAssetId. |
| AI | `ADinkEnemyCharacter` + 4 State Trees | The brain IDs in `dink.cpp` reduce to wander (duck/pig/people), chase (9/10) and bespoke boss. |
| Save | `UDinkSaveGame` | Version, facts, overrides, stats, inventory, screen and transform. Add a migration function from day one. |
| Cutscenes | `UDinkDirectorSubsystem` | Latent commands: Freeze, MoveTo(marker), Say, Wait, PlayMontage, Fade, Spawn, SetFact, CutTo(rig), PlaySequence. |

**Blueprint vs C++.**
- **C++:** rules and data (subsystems, data-asset types, save, combat maths, importer, command runner, component bases).
- **Blueprint:** composition and presentation (specific enemies and props, AnimBPs, widgets, VFX hookup, one-off puzzles and bosses).
- **Rule:** no Blueprint-to-Blueprint hard references; go through interfaces, tags or subsystems.
- **Uncertain:** I believe Live Coding is still Windows-only, which makes C++ iteration slower on Linux. That is another reason to keep tunables in data.

**GAS.** Not worth it. Three stats, 16 items, 8 spells and about 15 enemies need roughly 1–2 weeks of custom component-plus-action code, against 4–8 weeks to become fluent in GAS. Adopt GameplayTags regardless. Reverse this only if you already know GAS.

**Motion matching.** Use the Game Animation Sample as a black box for hero locomotion and layer combat as montages; do not extend its database. NPCs and enemies get plain blendspaces.

## B. Conversion pipeline

| Stage | Output | Automation |
|---|---|---|
| 0. Pin | Repo commit + sha256 of `bin/dink/*` | Full |
| 1. Extract (pure Python) | `ir/screens/SCR_nnn.json`, `sequences.json`, composited walkability PNG per screen, sprite reference PNGs, `scripts/*.ast.json` | Full. Write a real DinkC parser, not regexes: there are 88 `goto`s in 22 files, script-local ints, and conditional choice lines such as `(&old_womans_duck == 3)"…"`. |
| 2. Classify | `tile_classes.csv`, `sprite_classes.csv`, script kinds | Hand tables, auto-checked. There are 559 distinct seq/frame pairs in 178 sequences; the top 100 cover 74% of placements. |
| 3. Analyse | Edge-connectivity graph, warp graph, fact read/write table, lock list, vision variants | Full |
| 4. Layout | `regions.toml` (scale, offset, rotation per region) → `world_layout.json` | Table by hand, transform automatic |
| 5. Transpile | Ink drafts with command tags, enemy/item/shop JSON, bark tables, shot lists | Draft automatic, human pass required |
| 6. UE import | Landscape weights, blockers, placeholder actors, warps, spawners, screen volumes, cutscene markers | Full and idempotent. Adopted actors are never overwritten, but drift is reported. |
| 7. Report | `coverage.csv`: every origin ID and script → greybox / adopted / final / cut (with reason) | Full |

**Findings that change the design:**

- **Regions are not separated on the grid.** Outdoor screens form one 567-screen blob by grid adjacency (plus fragments of 2 and 1). Islands and the Darklands are separated only by hardness and water, so in third person you would see across them. Stage 3 must derive true regions from `hard.dat` edge walkability, and stage 4 must be able to move regions apart.
- **Interiors are packed together.** Indoor screens cluster as 54/9/9/2 on the grid, so unrelated houses sit side by side. The same edge analysis separates single rooms from multi-screen dungeons.
- **Most enemy data is in scripts.** Only 207 placements carry a brain in `map.dat`; the rest set it in `main()` via `sp_brain`. Enemy identity has to come from the script AST.
- **State variants are small.** `&vision` affects 164 sprites on 37 screens. Map these to a per-actor fact condition rather than duplicate levels.
- **Decoration is separable.** 1,658 placements are type 0, which I read as background-stamped decoration (uncertain). They are candidates for PCG seeds or instanced meshes.

**Must be hand-authored.** Elevation (the original is flat; cliffs are just tiles), all final art, combat tuning, dialogue polish, and about ten hero cutscenes.

**Cheaper cutscene route.** Emit Ink with tags such as `# move npc M_S412_03` and run them through the director. The default camera is an auto-generated "stage cam" framing the original screen bounds from a high three-quarter angle. That guarantees the blocking works and nods to the original view. Reserve Sequencer for the intro, the house fire, the King, Seth and the ending.

**Parity testing, in order of value:**
1. ID coverage from `coverage.csv`.
2. Generated fact-transition tests: trigger verb X on origin Y and assert the fact writes that the AST predicts.
3. A scripted teleport bot that drives `story` from 0 to 16.
4. Optional: instrument the HD engine to log variable writes as an oracle.

**Uncertain:** Inkpot's `.ink` import on a Linux editor. The fallback is compiling to JSON offline with `inklecate`. Spike this in pre-production.

## C. Third-person conversion risks

| Risk | Mitigation |
|---|---|
| Scale | Per-region scale table and fixed metrics (hero 1.8 m, doors 1.2 × 2.2 m, lanes ≥ 3 m). Tune on greybox against a target of something interesting every 20 s or less of running. |
| Sightlines | You can see about 500 m instead of one screen. Use relief, tree-lines, the escarpment and fog as occluders. Fill the 124 unused grid slots with sea or mountain. Re-check every secret that relied on being off-screen. |
| Sparse content | Shrink the wilderness, add PCG flora, one landmark per 3×3 screens, and tag-driven hit reactions on every prop class. Do not lean on expanded content to fix emptiness. |
| Screen-lock arenas | `screenlock` is called from 21 scripts. Auto-generate an `ADinkEncounterVolume` at the screen bounds with a diegetic barrier (portcullis, thorns, magic fog), enemy leashing, and unlock on tagged deaths. |
| Interiors and camera | A 12×8-tile room at 4× would be 60 × 40 m. Use the interior scale, 3.5 m ceilings, a shortened spring arm with shoulder offset, and dither-fade on occluding walls. Build from one modular 2 m kit. |
| 8-direction enemies | Touch-damage enemies have no telegraph, and off-camera hits feel unfair. Use navmesh movement, 0.3–0.5 s wind-ups, attack tokens (at most 2 attackers), soft lock-on, and off-screen indicators. Keep the stat ratios and re-tune the absolutes. |
| Bow and magic | The original fires in 8 facings. Add a hold-to-aim shoulder mode with a reticle and keep the charge; quick-cast goes to the lock target; add an assist cone for gamepad and Deck. |
| Burnable trees, bombable rocks | Among thousands of PCG trees, the scripted ones must read differently (dead or dry trees, cracked rocks). |
| Cutscene blocking | Scripts move sprites by pixel on a fully visible flat stage. Convert every move target to a world marker and use the stage cam as default. |
| Screen-load semantics | `main()` re-runs and locals reset on each screen entry; the gossip memory in `s1-lg.c` depends on this. Emulate it with screen-volume enter/exit and record each deliberate deviation. |

## D. Scope reality check

Person-months for one experienced generalist on the base game only. Treat these as ±30%.

| Discipline | As specified | With the cuts below |
|---|---|---|
| Pipeline and tools | 3 | 2.5 |
| Gameplay systems | 8 | 6 |
| UI, input, Deck | 3 | 2.5 |
| Script, dialogue and quest conversion | 5 | 3.5 |
| Cutscenes | 6 | 2.5 |
| Environment kits, props, biomes | 14 | 7 |
| World assembly and lighting (644 screens) | 12 | 7 |
| Characters (hero, NPCs, ~15 enemies, animals) | 12 | 6 |
| Animation | 8 | 4.5 |
| VFX | 2 | 1.5 |
| Audio | 3 | 2 |
| Performance, QA, parity, packaging | 7 | 5 |
| Overhead | 2 | 1.5 |
| **Total** | **~85** | **~52** |

That is roughly four to seven years full-time, and several times longer on evenings. The Stonebrook slice alone is about 9–12 months because it front-loads the systems.

**Top five project killers:**
1. **Art volume at a "realistic" bar.** Environment plus characters is over half the budget.
2. **A world that is dull in third person**, discovered only after the art is built.
3. **Licence and name.** Seth Robinson declining, an audio taint, or pack assets that cannot sit in a public repo. Get his answer in writing before any public demo.
4. **Linux toolchain friction.** Uncertain items: editor behaviour under Hyprland/Wayland, Fab and MetaHuman tooling on Linux, and Windows packaging from a Linux host (I believe this is unsupported, which would mean a Windows VM or machine).
5. **Burnout and creep.** Starting expanded content before base parity.

**MetaHuman.** Avoid it. The authoring tools are Windows-centric (uncertain for 5.8). The characters are heavy for a Deck with ten NPCs on screen. Most importantly, photoreal faces delivering 2,500 unvoiced lines with no facial animation look dead and fight the comedy. Use stylised-realistic humans on one Manny-compatible skeleton instead:
- two adult bodies plus a child from MPFB2 in Blender (CC0 output, Linux-native);
- about 11 modular outfits, head morphs and tint parameters, which is the original's recolour trick in 3D;
- text dialogue with grunts, and voice only for Dink's barks.

**Biggest savings for the least loss of identity:**
- Per-region scale: roughly halves the terrain to dress.
- Director plus stage cam instead of Sequencer for most scenes.
- One humanoid rig for hero, NPCs and goblins; one quadruped rig for pig and bonca; slimes and spike driven by shader or vertex animation.
- CC0 sources (Poly Haven, ambientCG) plus Fab freebies for rock, foliage and surfaces. Spend bespoke Blender time only on identity pieces: Dink, ducks, pillbug, bonca, slayer, dragon, Seth, the save machine, and the 13 building kits as modular sets.
- Music: re-render the public-domain compositions with CC0 instruments rather than composing.

## E. Milestone gates

| Gate | Exit criteria |
|---|---|
| Pre-production | Written permission, or a fallback title, decided. UE 5.8 builds and packages for Linux, and a Windows package exists by a documented route. The Deck holds the target frame time on a test scene with final-quality lighting and 10 characters. The importer regenerates the whole greybox in one command, with 100% of the 5,846 placements and 93 warps carrying origin IDs. All 380 scripts parse to AST with zero errors. The Ink round trip works on Linux. Greybox run-throughs of three regions have fixed `regions.toml`. |
| Vertical slice (Stonebrook) | Every Stonebrook screen and script is "final" in `coverage.csv`. The `story` 0→N path passes the automated bot. Save/load survives a version bump. One of each is at final quality: biome, building kit, NPC outfit, enemy, spell, weapon, shop, locked arena, interior, director cutscene, Sequencer cutscene. Measured hours per screen and per character re-baseline the schedule. The demo runs 30 minutes on Deck without a crash. |
| Alpha | The bot completes `story` 0→16 on a packaged build. 100% of origin IDs are adopted or cut with a reason. All fact-transition tests pass. Every item, spell and enemy exists as a data asset. Placeholder art is allowed but tracked. No original audio remains in the build. |
| Beta | Zero placeholder assets in base content. The performance budget is met in every region on Deck. A full licence audit covers every shipped asset. Alpha saves load. `DinkExpanded` contains its first layer, and the parity suite still passes with it disabled. Ten outside testers have finished the game. |
| Launch | Zero open crash or progression blockers. Windows and Linux packages are built from a tagged commit by script. Credits and attributions are complete. The save format is frozen. Controller-only and keyboard-only completion are both verified. |

### Critical Files for Implementation
- source/dink/dink.h
- source/dink/dink.cpp
- bin/dink/map.dat
- bin/dink/story/main.c
- LICENSE.md
