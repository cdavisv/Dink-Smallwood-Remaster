# Physical play layer: review fixes, drawn contact for both, invisible blockages (21 Nov 2026, PR #160)

Owner order: "make sure to fix hitboxes and invisible blockages in the game". Owner decision 19 Nov 2026: hits at DRAWN CONTACT for
both Dink and the creatures (option (c), `doc/remaster/COMBAT_REACH_OPTIONS.md`). The layer-off probe keeps the 1997 rule.
All proof here is HEADLESS (machine rule of 21 Nov: no rendered Unreal processes). No rendered captures were made for this
round. The 19 Nov captures (`../PhysicalPlay_19Nov2026/`) show the pine, boulder, heart and pillbug before this round.

## What changed
| item | change | proof |
|---|---|---|
| review 1 (A21 on all creatures) | body boxes on every class-bound creature too (`UDinkCreatureClassComponent`); not people (brain 16), not `nohit`, not a placement row whose authored Pawn boxes already stop Dink; resized only on a > 4 cm change | `Dink.PhysicalPlay.RealScreens` (4): the SCR_278 class pillbug carries a box, stops Dink, bites him from there, reaches him |
| review 2 (safe pocket, fireball) | `get_hard` keeps a relaxed box only inside its drawn footprint (`feet`, relaxed_hardboxes.json schema 2), for missiles, brains and the push test | `Dink.PhysicalPlay.Switch` (PlayHardness), `RealScreens` (S215_P05: get_hard 0 in the box, 105 at the trunk; 105 everywhere with the layer off) |
| review 3 (sight trace) | the touch trace against player-only hulls is simple (convex hulls answer simple queries only) and skips creature body boxes | code (`AuthoredGeometryMatches`); no dedicated test |
| review 4, 5, 8 | creature reach: depth along the facing, overlap counts, body-wide, sight from the body centre, Dink's capsule as the target; placement rows keep their authored boxes as the body | `RealScreens` (4), probe |
| Hits + CreatureReach | ON by default (`physical_play.ini`); creatures start their blow and stop closing in at drawn reach (`pill_brain`, `process_target`); a moving creature (brain != 0) never keeps its 1997 box | `Dink.PhysicalPlay.Parts`, `HitAtDrawnContact`, probe layer on |
| P1 grass_rocky | 1420 tiles on 250 screens freed in play (low collision rebuilt; original-hardness screens: tile base patched on every source load); 67 kept by the passage rule (`kept_tiles`) | `Dink.PhysicalPlay.Blockages`: SCR_408 walk east from x 150 reaches x 312 (stopped at 208 before); SCR_408 -> 409 at y 289 reaches x 177 (inside the ring x 4-62 before) |
| P2 / A54 | `stonebrook.json` WickerBasket moved from 70 cm south of the feed sack to the room's south-east corner (map 452,332) | `Blockages`: walking north from (448,200) takes the sack |
| A66 | in play, the talk fallback also answers an authored character within 200 cm of its body (never its old 3.5 m origin range) | `Blockages`: from in front of her the talk rule finds the mother and the talk key starts her talk (the failure was NOT reproduced headless: Dink stopped 53 cm from her actor there) |

## Probe
Copy `Saved/Collision21Nov` = master 11290aa3e + this branch, world regenerated (`rm -rf Content/Dink/_Generated`, `import_greybox.sh
--region all --export`, stonebrook), build 0 warnings.
- Layer OFF (automation default): `Dink.Gameplay.Probe` 29/29, all twenty md5s EQUAL the newest `packaged_probe.md` table
  (`probe_layer_off_hashes.txt`, `probe_layer_off_chapters.txt`). Also equal on the two earlier bases (9d044b61b old table,
  a00ec71a0 #140 table) during the work.
- Layer ON (`Mode=2`, every part on: drawn contact for both; `dink.CreatureClassArt=2` so class creatures are drawn by their bodies
  as in play): `probe_layer_on_chapters.txt`. Chained full run on 11290aa3e: 18 of 20 complete (1-11, 14-20); chapter 12 (the two
  dragons) failed at step 3 (Dink killed, mostly by the dragons' cast fireballs, 1997 missiles) and chapter 13 was then blocked by
  the missing save. Chapters 12 and 13 run one at a time from layer-off saves: chapter 13 6 of 6; chapter 12 again 2 of 5 (step 3, the dragons). Chapter 12 also completed in the
  one-at-a-time run on a00ec71a0 (5 of 5), so the dragon fight is luck-dependent under the new rule.
- Under (c) on 19 Nov the bot failed chapters 1, 8, 12, 17. Causes found and fixed:
  - GAME: creatures stopped closing in at their 1997 `sp_distance` (50-60 px, metres in the drawn world) and so never swung, or
    swung at air; now they close to drawn reach (`process_target`) and start the blow there (`pill_brain`).
  - GAME: a moving creature with hard 0 (the cave Bonca) kept its 1997 touch box 40 cm off its drawn body; now only still targets
    keep the 1997 box.
  - BOT: it waited at the 1997 spacing inside a long foe's drawn reach (Bonca 2.6 m), struck while the foe swung and lunged into
    touch range. It now waits outside the drawn reach, strikes between swings, lunges 65 cm off foes with touch damage, dodges a
    swinging foe or a touching body (a dragon walking into Dink), grows touch boxes by the drawn body in DuelFight/KiteAndCast,
    opens a duel/squad gate after 8 quiet s (foes that never swing from the 1997 spacing), wakes a stuck chaser (Jack) and gives
    fights twice their timeout with the layer on. All of this is gated on the layer: layer-off traces are unchanged.
- `DINK PROBE LAYER UNREACHABLE` (no free spot beside the drawn body; real-player defects): `probe_layer_on_unreachable.txt`. Most:
  SCR_190 duck-bugs and their gold against the screen's south-east corner, SCR_157 a slayer and a heart, SCR_680 S680_P08,
  SCR_536 S536_P33. Chapter 19 passed in this run but failed once (a00ec71a0, duck-bugs in the corner, 400 s) and passed once.
- Full `Dink` suite: 393/393 passed (`Scripts/test.sh Dink`, 1055 s, 18 with warnings) on the final code. On a00ec71a0, `Dink.Movement.Landforms.ScriptedMoveAcrossRelief` failed once in the full suite (0.1 cm, 81 vs 79 frames) and passed alone (3/3).

## Not checked / left
- Rendered checks: none this round (machine rule). Needed: pine/boulder/heart/pillbug and a Bonca/goblin fight at drawn contact,
  SCR_408/409 and the house (sack, mother) by hand.
- A66 not reproduced headless; the fallback is a mitigation; recheck by hand.
- Review finding 6 (perf): first entry of a relaxed or open-tile screen reads the baked mask with line traces: 30-114 ms measured
  headless (`baked ... collision read` log lines); a trimesh is cooked on every entry. Not optimised.
- Review finding 7 (burnt relaxed stump keeps the tree's hull / walk-through) and finding 9 (save inside a relaxed box loaded with
  Collision off): not handled.
- PM-07 (66 corridor-closing boxes kept) and the new PM-08 (67 grass_rocky tiles kept by the passage rule): Fable rows, no art here.
- A94 shores, A20 (SCR_471 pond, no ground), A92/A93 (tile hardness with nothing drawn / blocked open ground beyond grass_rocky),
  A71 interior walls: not started (the open-tile mechanism of this PR is the tool for A92 once a terrain class is judged open).
- `relaxed_hardboxes.json` footprints come from the 15 Nov dink.PhysAudit (the run of PR #155's world); a
  fresh audit needs a rendered game run.
