# Dink Smallwood content bible

Reference material for the remaster, compiled on 5 Nov 2026 by reading all 380 DinkC scripts in `bin/dink/story/`, the engine source in `source/dink/`, and the data files in `bin/dink/`. The plan these support is [`../REMASTER_PLAN.md`](../REMASTER_PLAN.md).

Each file is a research report and is organised by what was read, not by topic. Use the table below to find a topic.

## Files

| File | Covers |
|---|---|
| [01-story-stonebrook-terris.md](01-story-stonebrook-terris.md) | Stonebrook and Terris (`s1-`, `s2-`), system scripts, King, posters. `&story` 0-8 |
| [02-story-kernsin-to-ending.md](02-story-kernsin-to-ending.md) | KernSin, goblins, Windemere, Joppa, Edge of the World, Darklands, Koka Isle, snow castle (`s3-` to `s8-`, `sc-`). `&story` 8-16 |
| [03-systems-bestiary-items-audio.md](03-systems-bestiary-items-audio.md) | Player stats, weapons, magic, pickups, drop tables, bestiary, enemy behaviour types, animation inventory, sound and music cues, economy |
| [04-engine-and-file-formats.md](04-engine-and-file-formats.md) | Byte layouts of `dink.dat`, `map.dat`, `hard.dat`, `.ff`, `dink.ini`, saves; world, collision and combat rules; the DinkC interpreter; UI layout; debug hooks |
| [05-architecture-and-scope-review.md](05-architecture-and-scope-review.md) | Independent review of the remaster design: Unreal architecture, conversion pipeline, third-person risks, effort estimate, milestone gates |

## Topic index

| Topic | Where |
|---|---|
| Plot in order | 01 §1, 02 §1 |
| Characters and their lines | 01 §2, 02 §2 |
| Quests and side quests | 01 §3, 02 §3 |
| Regions | 02 §4 |
| Dialog menus | 01 §5, 02 §6 |
| Shops and prices | 01 §6, 02 §7, 03 §9 |
| Quest variables | 01 §7 |
| Bosses and set pieces | 02 §8 |
| Bestiary | 03 §5 |
| Weapons, magic, items | 03 §2-4 |
| Animation inventory | 03 §7, `../reference/sequences.txt` |
| Sound and music cues | 03 §8 |
| Tone and humour | 01 §4, 02 §5 |
| Sensitive-content register (exact quotes with files) | 01 §4 "Content to review", 02 §5 "Content to review" |
| Unfinished, cut and buggy content | 01 §8, 02 §9 |
| File formats | 04 §1 |
| Combat and movement rules | 04 §2-3 |

## Corrections

Checked against the scripts and engine after the reports were written. Where a report disagrees with this list, this list is right.

1. **Region prefixes.** `s3-` is KernSin and the goblin lands; `s4-` is Windemere. The closing "Regions" line of 03 §5 has these two swapped.
2. **Bow charge rate.** The bow gains 7 power per tick with ticks at least 10 ms apart, which at the engine's 60 Hz step is 7 per frame, so a full charge of 500 takes about 1.2 seconds (`source/dink/dink.cpp`, `process_bow`). 04 §3 says "per 100 ms", which is the diagonal-aim hold time, not the charge rate.
3. **Renderer.** 04 §5 says there is no shader pipeline. The Windows and HTML5 builds do enable one (`RT_SHADER_PIPELINE_AVAILABLE` in `windows_vs2017/winRTDink.vcxproj` and `html5/build_release.bat`); the code lives in the Proton SDK, not this repo. It does not affect the remaster.
4. **Interpreter.** 04 §8 argues for embedding a DinkC interpreter. The plan does not: fan-made add-ons cannot run in a 3D world in any case, so scripts are converted once and checked against the original game.
5. **Colour keys.** 04 §1 infers that sprite transparency is by palette index (255 white, 0 black). In the shipped art white is index 0 and black is 255, and the loose `tiles/sNN.bmp` sprites use different palettes, so the extractor keys on RGB.
6. **Frame count.** The 3,569 sprite frames are 3,447 in 142 `.ff` archives plus 122 loose BMPs. Three archives also contain a bogus entry named `dir.ff`, which is not a frame.
7. **`hard.dat` traps are real but never hit.** The file is short and 106 index entries are out of range, but no tile placed in the shipped map reaches either.
8. **Counts from the full parser** (`tools/dinkc`). There are 2,125 spoken lines, 115 dialog menus with 359 options, 934 procedures and 63 global variables (all declared in `main.c`). 20 scripts call `screenlock` (a 21st only has it commented out) and there are 87 live `goto`s in 21 files. Earlier figures of "about 2,500 lines", 21 and 88 were estimates or plain text counts.
9. **Missing scripts.** `map.dat` names five scripts with no `.c` file: `s2-307s`, `s2-barp`, `s2-mh-s`, `box-e` and `big`. 01 §8 lists four. `s1-h1-1c` exists only as a compiled `.d`.
10. **Lines the engine never shows.** Because of source errors, the 1997 engine silently drops some lines: "Long live the ducks." (`s4-sign3.c:17`, missing parenthesis), "I guess I just killed your husband." (`s2-jack.c:171`, stray `'`), Christina's "Hello Dink, I'm Christina." (`s3-chick.c:42`, missing comma), the wait in `s2-cave.c:117`, and bed lines 2 and 3 in `s1-h3-8.c` sit inside the wrong `if` (a `{` typed for `}` at line 13). `sp_prop` (`s5-end.c`, `s5-fguy.c`) is not an engine command and does nothing. The rule is what a 1997 player saw, with author-intent fixes behind switches that are off, with one exception decided by the owner on 9 Nov 2026 (OD2 in `doc/remaster/verbatim_review.md`): the four pure typos (Long live the ducks, Jack's husband line, Christina's reply, the two bed lines) **are spoken in the remaster**. Everything else on the engine-never-runs list stands: the `s2-cave.c:117` wait and every other switched intent stay as the engine ran them, and the SCR_419 door's `sp_prop` calls stay off (OD1 gave `sp_prop` a meaning in the director, the switches stay false). `tools/dinkc/out/diagnostics.json` lists every case; `tools/dinkink/DESIGN.md` section 9 lists the switches.
11. **Missile damage.** The base game uses the integer formula `S/2 + rand()%(S/2) + 1 - defense`, with strength 1 special-cased as `1 - defense`. The float formula in 03 §1 only applies when a script opts into the HD engine's "latest fixes" level. The 50% chance of 1 point applies to melee, touch and scripted `hurt()`, never to missiles.
12. **Magic recharge.** The exact in-game time is `ceil(cost / magic)` steps of 100 ms, so 100 cost at magic 3 is 3.4 s, not the nominal 3.33 s.
13. **Respawning sprites.** Types 6, 7 and 8 use one timestamp per screen, set when the player leaves it, and are checked only when the screen loads. Any override also clears the placement's script.
14. **Full-heart drop.** 03 §4 says the full heart uses the small-heart sprite (seq 54). It is created with seq 54, but `heart.c`'s `main` switches it to seq 52 at once, so the player sees the full-heart animation.
15. **Sound effect count.** `start.c` loads 48 distinct effects into slots 1-49 (slot 25 repeats CAVEENT, and slot 11 is SELECT). The plan's "58 effects" was an estimate; seven more files in `bin/dink/sound` are never loaded by the scripts.

## Spot checks passed

Prices for the bow (1000), throwing axe (3000), light sword (4000), massive bow (5000), FlameBow (25,000) and bridge toll (100); Seth's 300 HP, 25 defense, 30 touch damage and 10,000 exp; starting stats (strength 3, defense 0, magic 0, life 10); +3 max life per level and the level-32 cap; the 5,000-exp pig; 21 scripts using `screenlock`; four quoted lines found verbatim in their cited files.
