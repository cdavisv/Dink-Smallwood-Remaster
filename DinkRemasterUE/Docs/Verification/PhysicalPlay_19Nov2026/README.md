# Physical play layer (bug A70, A21), split into parts: evidence, 19 Nov 2026

## What changed
In play (`dink.PhysicalPlay`, auto = on in a rendering game, off under automation), Dink's walking collision and the touches on
him follow the drawn 3D shapes, and living creatures carry a player-only body box (A21). Coordinator decision of 16 Nov on PR #160:
the layer has PARTS (`physical_play.ini` keys, console variables `dink.PhysicalPlay.<Part>`):

| part | default | what it does |
|---|---|---|
| Collision | on | relaxed 1997 hardboxes (`relaxed_hardboxes.json`): Dink walks up to the drawn tree, rock |
| Touch | on | pickups, touch scripts and touch damage at the drawn item or body |
| Bodies | on | A21: a player-only box in every living creature; never a trap |
| Hits | OFF | Dink's blows land at drawn contact |
| CreatureReach | OFF | creature blows at Dink by the reach of their drawn body |

With Hits and CreatureReach off, every hit decision is the 1997 code path (`RunThroughTagList`, dink.cpp:15460-15527). Those two
parts are tested but stay off until the owner chooses a hit rule (`doc/remaster/COMBAT_REACH_OPTIONS.md`). Design and as-built
notes: `doc/remaster/PHYSICAL_PLAY_LAYER.md`. Also fixed from the Codex review of the earlier head: a class-bound script creature,
drawn only by its skinned body, now counts for touches; touch sight lines also stop at the player-only blockers (a relaxed box is no
longer in the hard-solid mesh). New review command `dink.PhysicalPlayReach` (non-shipping, used for the reach doc).

## How it was proven (private copy, master f47439908 + this branch, clean build, `_Generated` deleted and regenerated with `--export` and stonebrook)
- Build: BUILD OK, 0 warnings, `DinkPhysicalPlay.cpp` and `DinkAuthoredInteraction.cpp` compiled.
- `Scripts/test.sh "Dink.PhysicalPlay+Dink.Gameplay.AuthoredGeometry+Dink.Gameplay.Probe"`: **44/44 passed** (layer off under
  automation; the layer's own tests switch it on). Includes `Dink.PhysicalPlay.Parts` (new), `.HitAtDrawnContact` (Hits off: the 1997
  box decides; Hits on: drawn contact), `.TouchAtDrawnContact`, `.CreatureBodyBlocksDink` (also: Bodies off makes no box) and
  `.RealScreens` (PIE on the generated world: pine S215_P05 stops Dink with the layer off and not on; SCR_438 pillbug own box
  173 x 131 x 55 cm; Hits on lands at contact and misses from 1.5 m; with the default parts its body box stops Dink 116 cm from its
  centre (half length 87 cm) and his blow from there is the 1997 box test and lands).
- Probe, layer OFF: all twenty md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 cc2e12fb5c ... Ch20 be28390b9d;
  `probe_layer_off_chapters.txt`).
- Probe, layer forced ON (`Mode=2`, default parts), `Dink.Gameplay.Probe` 29/29: **every chapter completes** (`probe_layer_on_chapters.txt`).
  The md5s differ from the table (expected: the relaxed boxes, body boxes and drawn touches change Dink's routes and timing):

| ch | steps | ch | steps | ch | steps | ch | steps |
|---|---|---|---|---|---|---|---|
| 1 | 47 of 47 | 6 | 3 of 3 | 11 | 20 of 20 | 16 | 3 of 3 |
| 2 | 6 of 6 | 7 | 4 of 4 | 12 | 5 of 5 | 17 | 4 of 4 |
| 3 | 12 of 12 | 8 | 8 of 8 | 13 | 6 of 6 | 18 | 3 of 3 |
| 4 | 12 of 12 | 9 | 7 of 7 | 14 | 4 of 4 | 19 | 45 of 45 |
| 5 | 3 of 3 | 10 | 6 of 6 | 15 | 3 of 3 | 20 | 5 of 5 |

  The layer-aware bot stepped to the drawn item 26 times, all pickups (gold, potions, hearts; `probe_layer_on_assists.txt`), never for
  a blow (Hits off). DINK PROBE LAYER UNREACHABLE: **0**, so no target the bot needed is out of reach from walkable ground.
  Chapters 1, 8, 12 and 17, lost with drawn hits on both sides, now complete.

## Rendered frames (offscreen game, `capture_script.txt`, log lines in `capture_log_excerpt.txt`), looked at one by one
| sheet | what I see |
|---|---|
| `play_pine_S215.jpg` | Layer OFF: `WalkTo` west along y 78 times out at map x 412.5, at the 1997 box. ON: arrives at x 327, beside the trunk under the canopy, not inside it. |
| `play_boulder_S536.jpg` | Relaxed boulder S536_P09, walking north along x 579. OFF: stops at map y 215.8, 6.5 m short (open grass between him and the rocks). ON: arrives at y 148, next to the drawn boulder. |
| `play_gold_heart_S524.jpg` | Layer ON. At x 142.5, inside the 1997 touch box, a body width short of the drawn heart: nothing. At x 161.7, at the heart: `gheart.c` `touch()` runs (audio cues 10 and 22 in the log); the frame is taken at once, so the heart is still drawn. |
| `play_pillbug_S278.jpg` | Pillbug S278_P04 held (`dink.Npc.Hold 1`), layer ON. Dink's walk at it ends beside its body, not on or inside it (`WalkTo` slid him past it, so this frame does not show a head-on stop; the head-on stop is the RealScreens PIE test). Three punches with the 1997 hit rule: hp 8 -> 5 -> 2 -> dead, the body bursts into its blood. |

## Not checked
- A rendered head-on stop at a creature body, and a rendered creature walking into Dink and letting him go (the SCR_438 bugs never
  came near him in the 8 s of the run): both covered only by `CreatureBodyBlocksDink` (fixture) and RealScreens (PIE).
- Sword hits in a rendered run (the fist only); hits use the 1997 rule, unchanged code.
- Walls and the 38 original-hardness-projection screens (not relaxed by design); the 66 boxes kept by the passage test (Fable row PM-07).
- The full `Dink` suite (only the filter above); the packaged game; a controller; the enlarged world scale (#161).
