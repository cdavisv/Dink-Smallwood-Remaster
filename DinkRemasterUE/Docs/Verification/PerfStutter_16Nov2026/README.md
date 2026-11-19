# Stutter and frame rate: measured in the packaged game (16 Nov 2026)

Stream perf-stutter (owner: "reduce stuttering... more frame rates on lesser hardware"). Everything new runs behind
`dink.Perf.Fixes` (default 1 in play; 0 = master's code paths), so one package measures before and after.

## What changes
- Measuring: `dink.Perf.Route` (scripted route, per-frame csv, summary json with hitch causes: sync loads, GC, screen change,
  log lines, the costliest `DINK_PERF_SCOPE`s), `DINK_PERF_SCOPE` one-liners at the top of the Dink ticks and screen-entry
  dressing, `Scripts/perf/` (make_route, run_bench editor/packaged with weak-CPU emulation, perf_report).
- Fixes (`dink.Perf.Fixes 1`): a per-screen actor index (`DinkScreenIndex`) instead of whole-world walks on screen change;
  neighbour screens dressed under a per-frame budget (`dink.Perf.NeighbourBudgetMs` 3) with prefetch, the entered screen
  at once; card billboarding only in range; the legacy-card pass on screen change / every 2 s; wall visuals only on a
  physical screen change; burnables found once; a screen grid for ground colour / mask lookups; grass cells under a 2 ms
  budget with their scatter materials preloaded; settled unrendered creature-class bodies skip their tick; wind-swayed
  vegetation keeps cached rest-pose shadows (`dink.Perf.StaticForestShadows`, same policy as world-life's foliage rule).
- First-run quality detection (`DinkFirstRunSettings`): measures the game's own GPU frame time and steps High -> Medium ->
  Low; it replaces `UGameUserSettings::RunHardwareBenchmark`, whose synthetic GPU test hung the RX 6800 twice on 15 Nov.
  **Off by default** (`dink.Perf.AutoDetect 0`): it has not been seen end to end in a packaged first launch yet.
- LOD1/LOD2 generated on three unclaimed set pieces (save machine, teleport machine, dragon statue; A200). The corpse kit's
  LODs came with the Fable monster stream (master), so this branch keeps master's corpse meshes.

## Measured (packaged Linux Development, RX 6800, 2560x1440, the same route; master c878e29e + this branch)
`packaged_fix0_vs_fix1.md` holds every table. Steady frames (standing on each stop):

| level | fixes off: fps / p99 ms / GPU ms | fixes on |
|---|---|---|
| default (auto screen %) | 64.2 / 19.8 / 14.9 | 68.3 / 19.7 / 13.8 |
| Epic | 36.1 / 38.1 / 27.0 (steady frames > 33 ms: 400) | 38.8 / 32.5 / 25.1 (21) |
| High | 72.4 / 16.9 / 13.1 | 79.0 / 15.8 / 12.0 |
| Medium | 109.3 / 12.4 / 8.5 | 127.2 / 10.4 / 7.2 |
| Low | 197.9 / 6.3 / 4.4 | 238.0 / 6.1 / 3.6 |

First lap, arriving on a screen (entry + walk frames): sync package loads 51 -> 15; worst frames: SCR_438 79 ms -> under 33,
coast 650 76 -> 46 ms, dungeon 579 38 -> 51 ms, **Terris 530 77 -> 92 ms** (one `Dink_Env_ApplyNeighbourScreen` call of 58 ms:
a single heavy neighbour screen is dressed in one piece; the budget only spreads whole screens). Frames over 33 ms on arrival
6 -> 9 of about 9,000-10,000. Second lap: worst 34 -> 37 ms. So the steady frame rate rises at every level (mostly GPU: cached
foliage shadows), the sync loads fall, but first-visit hitches are NOT solved: A57 stays open.


## Final-tree run (19 Nov, master f4743990 + this branch; clean build, world regenerated with `--export`)
- Clean build (Intermediate deleted): 262 compile units, this branch's files among them. `Dink.Perf+Dink.Art+Dink.Core.Greybox+
  Dink.World+Dink.Creature+Dink.Gameplay.Probe` 118/118; the twenty probe trace md5s equal the newest table of `packaged_probe.md`.
- Short rendered lap (editor game, default quality, all cores; `dink.Perf.Fixes` 1, then the same route with 0): seven stops
  (SCR_001 vision 1 with #166's fire, 438, 439 vision 1, the pond 471, Terris 530, coast 650, forest 312), a frame 0.5 s after
  arriving and one 9 s later. The first lap found a regression: with the fixes the grass carpet of SCR_438 was MISSING 0.5 s
  after arrival (`lap_19nov_before_grass_fix.jpg`: the 2 ms cap on grass cells), while master had it. Fixed: the near rings
  (about 56 m) keep master's six cells a frame, the cap thins only the far rings. After the fix (`lap_19nov_fixes0_vs_fixes1.jpg`)
  every stop shows the same on arrival with fixes on and off: structures, the placed fires, water, the grass, the forest.
- Two test findings on today's master, fixed here: `Dink.Perf.Tick.Bounded` now allows the flicker lights of placed effect rows
  (#166); the camera-fade foliage variants are loaded at begin play (they were a synchronous load on screen entry).

## Not proven / failed
- Weak-CPU emulation (4 cores, 1080p) did not finish: the packaged game died at Medium+ on coast 650 after a kernel
  general-protection fault in amdgpu (RHIThread, non-canonical address) and a 60 s render-thread hang (A181 class; Master
  log 16 Nov 23:15). The 15 Nov pre-review weak run (75 fps default, 3 frames over 33 ms) is the only weak-CPU number.
- First-run detection not run end to end (hence off by default).
- Medium+ / Low+ presets: measured in this route (80.5 / 186.2 fps) but no scalability-ini change is in this PR.
