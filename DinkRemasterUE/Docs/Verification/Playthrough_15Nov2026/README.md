# Playthrough QA, 15 Nov 2026: the whole story rendered (bot) and its opening, a Windemere fragment and the ending by hand

Owner's order: "make sure the game is playable from end to end. Do bug testing." The headless probe already proves the simulation
reaches `&story` 16. This pass plays the game the way a player sees it: a rendered window (private Xvfb display, audio on SDL's
dummy device, nothing on the speakers), keys sent to the game window, and a look at every capture.

Tested build: master `283cd155` + PR #126 (water banks, master `f92915fe`) + PR #129 (walk-through blockers) + PR #130 (load
unfreeze) + PR #128 (item screen, dialogue box), merged locally; world regenerated (`import_greybox.sh --region all --export`, then
`--region stonebrook`). `Scripts/test.sh Dink.Gameplay.Probe`: 29/29, all twenty chapter md5s equal to the 14 Nov table in
`Plugins/DinkParity/Docs/packaged_probe.md`.

## How it was driven

* **Beat captures** (new, `DinkProbe/Private/DinkBeatCapture.cpp`): `-DinkBeatShots=<dir>` or `dink.BeatShots <dir>` takes a
  screenshot with the UI at every story beat: a change of `&story`, the first arrival on a screen, a load, a menu, the item screen,
  a locked fight (screenlock), a level-up, Dink's death, a script error, every probe step done, and every 60 s. It logs
  `DINK BEAT`, `DINK CUE` (every `playsound` / `playmidi` a script asks for) and `DINK HITCH` (frames over 200 ms). It reads the
  game and writes nothing into it. `dink.Sprites` lists the live sprites of Dink's screen (for driving).
* **Hand-driven sessions** (editor `-game`, rendered on `:189`): XTest key presses into the game window. Movement is held W with the
  camera turned (`dink.View`) or `dink.WalkTo` (movement input through CharacterMovement: real collision, real warps). Talking is
  E, menus are Up/Down/Enter, the item screen is Enter / cursor keys / F, attack F, magic Q, the main menu Esc. `dink.Goto`
  (teleport) is used only where a session says so, and every use is listed below.
* **Rendered probe** (packaged Development build on `:189`, `-UseFixedTimeStep -FPS=60`, one process per chapter, beat captures
  on): the probe's own route for all twenty chapters, so the story's later beats are seen rendered where hand-driving every fight
  (Seth takes 41-51 bow shots) is impractical.

## Rendered probe: all twenty chapters in the packaged game, audio on (`r_overview_1..4.jpg`, `beats.tsv`)

Package of the tested build plus this stream's fixes (#138's crash fix and its follow-up included), `Scripts/package.sh` OK, content
check 2769/2769. Each chapter one packaged process on `:189`, windowed 1280x720, SDL dummy audio, `-UseFixedTimeStep -FPS=60
-DinkProbeHold -DinkBeatShots=<dir>`, chapters handing over through their saves. 16:49-17:14 PT, 527 beat screenshots (all
listed in `beats.tsv` with kind, screen, `&story`, life, gold and the frame name; every other story/step beat is on the overview
sheets). **Every chapter passed** (`Result={Success}`, the probe's own end condition per chapter), so the rendered game with
audio reaches `&story` 15 and the King's ending (`&story` 16 is set by the King's last line as the process quits; chapter 20's
last step is "the King ... &story 16" done). No fatal error, no crash, no core dump. The first attempt at 14:30 (the package
of 12:15, without the fix) died in chapter 1 entering SCR_036: that is A58 / PR #138.

| Chapter | Result | trace md5 | steps | beats | `&story` changes | hitches > 200 ms | audio (played / requested sfx cues) | log |
|---|---|---|---|---|---|---|---|---|
| Ch1Stonebrook | Success | b4ad88c02c | 47 | 89 | 0_to_1, 1_to_2, 2_to_3, 3_to_4, 4_to_5, 5_to_6, 6_to_7 | 5 (max 365 ms) | 75/65 sfx/cues, 23 voice, 23 music | 0 fatal, 1 ensure, 23 error lines |
| Ch2Terris | Success | bc267a0dfc | 6 | 19 | 0_to_7, 7_to_8 | 0 (max 0 ms) | 111/108 sfx/cues, 6 voice, 7 music | 0 fatal, 1 ensure, 23 error lines |
| Ch3Roads | Success | bbd401167c | 12 | 24 | 0_to_8 | 0 (max 0 ms) | 13/9 sfx/cues, 4 voice, 4 music | 0 fatal, 1 ensure, 23 error lines |
| Ch4Gold | Success | eceee9516a | 12 | 21 | 0_to_8 | 0 (max 0 ms) | 145/143 sfx/cues, 6 voice, 4 music | 0 fatal, 1 ensure, 23 error lines |
| Ch5Bow | Success | d987c043f6 | 3 | 8 | 0_to_8 | 0 (max 0 ms) | 3/1 sfx/cues, 4 voice, 3 music | 0 fatal, 1 ensure, 23 error lines |
| Ch6Goblins | Success | 2df37e4a27 | 3 | 9 | 0_to_8 | 0 (max 0 ms) | 28/26 sfx/cues, 3 voice, 3 music | 0 fatal, 1 ensure, 23 error lines |
| Ch7Sanctuary | Success | a16d1d23b8 | 4 | 11 | 0_to_8 | 3 (max 306 ms) | 46/44 sfx/cues, 4 voice, 3 music | 0 fatal, 1 ensure, 23 error lines |
| Ch8Knights | Success | 764e9d330f | 8 | 26 | 0_to_8 | 1 (max 326 ms) | 182/177 sfx/cues, 7 voice, 6 music | 0 fatal, 1 ensure, 23 error lines |
| Ch9Windemere | Success | dd1e2662fa | 7 | 13 | 0_to_10, 10_to_11 | 1 (max 217 ms) | 173/99 sfx/cues, 4 voice, 4 music | 0 fatal, 1 ensure, 23 error lines |
| ChAJoppa | Success | 23fd57dfdc | 6 | 15 | 0_to_11 | 2 (max 758 ms) | 12/9 sfx/cues, 5 voice, 4 music | 0 fatal, 1 ensure, 23 error lines |
| ChBKit | Success | 9c66f178e5 | 20 | 35 | 0_to_11 | 4 (max 741 ms) | 225/222 sfx/cues, 6 voice, 4 music | 0 fatal, 1 ensure, 23 error lines |
| ChCDragons | Success | 79c8ce55f9 | 5 | 15 | 0_to_11, 11_to_12 | 1 (max 322 ms) | 81/56 sfx/cues, 3 voice, 5 music | 0 fatal, 1 ensure, 23 error lines |
| ChDCastle | Success | 98a2e17ba0 | 6 | 16 | 0_to_12, 12_to_13, 13_to_14 | 0 (max 0 ms) | 11/7 sfx/cues, 4 voice, 4 music | 0 fatal, 1 ensure, 23 error lines |
| ChEEdge | Success | f1ddbaab7b | 4 | 12 | 0_to_14 | 0 (max 0 ms) | 13/11 sfx/cues, 3 voice, 5 music | 0 fatal, 1 ensure, 23 error lines |
| ChFDarklands | Success | 7e3dbbd0b1 | 3 | 11 | 0_to_14 | 2 (max 309 ms) | 76/59 sfx/cues, 4 voice, 5 music | 0 fatal, 1 ensure, 23 error lines |
| ChGSlayers | Success | 48e797069a | 3 | 11 | 0_to_14 | 0 (max 0 ms) | 134/97 sfx/cues, 4 voice, 5 music | 0 fatal, 1 ensure, 23 error lines |
| ChHDucks | Success | 4277c65c35 | 4 | 12 | 0_to_14 | 0 (max 0 ms) | 49/38 sfx/cues, 4 voice, 5 music | 0 fatal, 1 ensure, 23 error lines |
| ChISeth | Success | d33886b797 | 3 | 10 | 0_to_14 | 0 (max 0 ms) | 6/4 sfx/cues, 4 voice, 4 music | 0 fatal, 1 ensure, 23 error lines |
| ChJBowLore | Success | 45b399bac8 | 45 | 68 | 0_to_14 | 1 (max 218 ms) | 179/153 sfx/cues, 7 voice, 5 music | 0 fatal, 1 ensure, 23 error lines |
| ChKSeth | Success | 84f33687af | 5 | 19 | 0_to_14, 14_to_15 | 0 (max 0 ms) | 156/200 sfx/cues, 17 voice, 5 music | 0 fatal, 1 ensure, 23 error lines |

Trace md5s equal the editor's table for 18 chapters; Ch4 (`eceee9516a`, table `8740518c57`) and Ch11 (`9c66f178e5`, table
`0d70cebfcd`) differ in a few probe position notes only (Dink one pixel off for a moment in a fight; A65); the next chapters,
loaded from their saves, have the table's md5s. The "23 error lines" of every chapter log are that one ensure: its message and its callstack lines (`LogOutputDevice: Error:`), plus `LogAutomationController: Error: Failed to load test report html template` (the packaged build has no report template; the probe's results are its log and traces). The ensure is the scalability variable (A64, fixed); no other error line. Sound cues
requested but not played are the four slots the owner rejected (A56): chapter 20's 44 missing are the bow's draw (slot 44). 20
hitches over 200 ms in the whole run, median 287 ms, the worst 758 ms and 741 ms on entering the Joppa basement (SCR_229)
(A57).

Seen in the frames (looked at as contact sheets, every chapter): the story beats play in order with the dialogue box, menus,
bubbles and captions; photoreal hero, mother, Milder; the gore of kills (pillbug, slayer, Bonca) in blood pools. Defects in the
frames: the AlkTree nut, the cult's girls (SCR_238) and Seth are grey cylinders (A53); water drawn over grass where potions lie
(SCR_273, SCR_597, SCR_603: A59); "The best in bows" still on screen at the goblin gate (A60); interiors floating on the empty
interior plane when the camera is behind a wall (A61); pixel cards everywhere the visual sweep listed them (chests, cottages,
castle walls, fences, the King); the camera inside a card or a wall at several probe stand-by points (healers' houses, chests):
those are the probe's teleports into tight spots, not walking paths.


## Hand-driven sessions

### Session A: a new game in Stonebrook (`a_stonebrook_newgame.jpg`, `a_scr408_fence_ns_cards.jpg`)

New Game (no save), 501 s, 47 captures + 27 beat shots. What was done and seen:

| Beat | How | Seen |
|---|---|---|
| Opening: Dink's house, the mother walks in (`&story` 1, music `5.mid`) | no input, 6 frames over 12 s | the interior, fireplace light, the mother walking; no text (the mother speaks only when talked to, as in 1997) |
| Talk to the mother | WalkTo beside her, E | **no conversation**: the log says `talk: no sprite by the original rule from Dink at 230,165 dir 4`; her body overlaps Dink's (frames 007/008) |
| The food on the table (`sfood`) | WalkTo | life already full (10/10): no change, no "Yum!" checked |
| The sack of pig feed (S001_P52) | WalkTo to it | **not picked up**: Dink stops 93 cm (about 21 px) short; the inventory keeps only the fists |
| Item screen | Enter, Right, F, Enter | opens, pauses, cursor moves, closes; panels and stats draw (frames 011-014) |
| Out of the door (S001_P25) to SCR_439 | WalkTo into the doorway | screen change, exterior camera at once (frame 015) |
| North to the pig pen (SCR_407) | WalkTo north | walked back into the house door just north of the arrival point (as in 1997); taken on by `dink.Goto 407` (teleport 1) |
| Throw the feed | F | no feed armed (sack not taken), so a punch; a pig walks through Dink (frame 022) |
| East to SCR_408 | WalkTo east | stopped by the fence on 407 at x 472; `dink.Goto 408` (teleport 2) |
| Save machine (S408_P25) | E, "Save your game", slot 1 | menu box, slot list, save written, `cmd save_game 1` beat; slot lines read "Slot N - Saved game" (1997: "Slot N - H:MM - Level L") |
| Ethel's door (SCR_409 S409_P16) | WalkTo north into the door | not entered by this script's walk (session D walked in fine); the cottage is a pixel card (frame 030) |
| Fists on the pillbugs of SCR_278 | `dink.Goto 278` (teleport 3), punches | no kill in 30 s of naive punching (exp 0) |
| Death | life set to 1 (console), pillbugs bite | death menu (dinfo.c: Load / Restart / Quit); **Dink stands upright** next to it (frame 036; 1997 shows him crumple into a pool of blood, sequence 436) |
| Death menu "Load", slot 1 | keys | loaded at the save machine on SCR_408; Dink walks (moves 15 px on a W hold) |
| Esc menu "Load", slot 1 (A19) | Esc, keys | loaded; Dink walks (A19 fixed) |
| Push the rock S277_P03 (`s1-roc`) | `dink.Goto 277` (teleport 4), held W east into it | at strength 3: "It's too heavy for me. If I was a little stronger..."; strength set to 4 (console): it moves (`&rock_placement` 1) and Dink walks on into the cave behind it (SCR_131, "Smells damp in here.") |

### Session B: Windemere from the probe's chapter-8 save (`b_windemere_shop_bomb.jpg`)

`probe_ch8.sav` copied to slot 2 and loaded from the Esc menu (162 s): Dink in Blistering Pete's (SCR_196), `&story` 10, 251 gold.

| Beat | How | Seen |
|---|---|---|
| Load from the Esc menu | Esc, "Load", slot 2 | Pete's shop interior; Dink walks after the load; the white duck in the shop (frame 003) is the 1997 placement S196_P25 (`die5`, brain 3), not a stray |
| Shop: "See what's for sale", "Bomb - $20" | WalkTo Pete, E, menus by keys | the store menu and the price list in the dialogue box; gold 251 -> 231, the bomb in item slot 5 |
| Item screen | Enter, cursor | items fists, pig feed, nut, bow, bomb; magic fireball, acid rain, magic shield |
| The cracked rock of SCR_536 (S536_P15) | `dink.Goto 536 413 120` (teleport), quick-arm key 5, F, walk away | the bomb is placed, explodes, `&s4-duck` 1 (the duck pen opens); the rock and the two chests are big pixel sprite cards (A22); the camera dips into the chest card after the explosion (frame 011) |
| A chest's potion (S536_P31) | two punches from 25 px below the card | no potion appeared; not repeated by hand (no Unreal turn was left); the probe's chapter 9 punches the same chests from 12 px and gets both potions (strength +1 each, rendered run) |
| Bow at a duck | quick-arm 4, held F 1.6 s toward a duck | the duck moved; no hit seen |
| Fireball (Q) at a duck | item screen magic panel, Q | no hit seen (aiming by camera yaw at wandering ducks is not reliable) |

### Session C: the ending from the probe's chapter-19 save (`c_milder_king_credits.jpg`)

`probe_ch19.sav` (before the healer, Milder and Seth) copied to slot 3 and loaded from the Esc menu (215 s).

| Beat | How | Seen |
|---|---|---|
| Load at the Windemere healer's (SCR_195) | Esc, "Load", slot 3 | the camera shows only a plaster wall for at least 10 s after the load: the save stands Dink inside the west wall (probe artefact, see Physical mapping) |
| Milder (SCR_086 `s7-mil`) | `dink.Goto 86` (teleport), WalkTo, E | his lines in the dialogue box and speech bubbles; the menu "Refuse to leave without him / Take his advice" (picked by Space as the first option: Refuse) |
| Seth | - | not reached in this session (the menu was answered "Refuse"); see the rendered probe and session E |
| The King (SCR_070 `king`) | `&story` 15 set by console (Seth's `die` sets it), `dink.Goto 70` (teleport), WalkTo, E | the whole ending by input, nothing skipped: "SMALLWOOD HAS RETURNED!", the report, "CONGRATULATIONS!", "YOU HAVE FINISHED THE GAME.", every credit line through "Thanks for playing - Seth", "And now, food for my hungry hero!", six potions created, `&story` 16. The King and his six knights are 1997 pixel cards (Dink stands in front of a 3 m card); credits draw as captions at the bottom |

### Session D: focused checks (`d_checks.jpg`)

New Game, 168 s. The feed sack from four sides with the player blockers on: from the south (448,200) Dink stops at 462,156 and gets nothing; from the west (380,130) he reaches it and the feed is in slot 2. Ethel's door on SCR_409 walked into from 368,345: warps into SCR_002 with blockers on and off (session A's miss was the script's own walk). On arrival in Ethel's house the view is black for at least 1 s with her greeting in the box (the fade-in; checked again in session F). A fist fight by input on SCR_278 (life raised by console to 60): one pillbug killed (exp 0 -> 10), its body left in a pool of blood. The camera clips into Dink's head and shoulder in the north-east corner of his house while he presses toward the sack (frames sack_b1_0/1).

### Session E: after a load, Milder and Seth (`e_load_slots_and_milder.jpg`, `e_seth_grey_cylinder.jpg`)

`probe_ch19.sav` loaded from the Esc menu, whose slot lines now read "Slot 1 - 0:04 - Level 1", "Slot 2 - 0:19 - Level 4", "Slot 3 - 0:42 - Level 6" (A51 fixed). After the load the camera shows only a plaster wall for 12 s: the save stands Dink inside the healer's west wall (a probe stand-by artefact, see Physical mapping). Milder (SCR_086) by E: all his lines, the menu, "Take his advice", Seth's entrance and his lines, all in the dialogue box and bubbles. **Seth is a grey checkered cylinder** with a red wireframe debug sphere over him when he winds up (A53, A52). Seth killed Dink (life 95 -> 0 in about 10 s while the script aimed the bow): Dink's body went limp on the ground with a blood pool spreading under it (this stream's trial death picture; PR #140 carries Dink's death fall now) and the death menu came up.

### Session F: the mother, the sack from the south, Ethel's arrival, death in daylight (`f_checks.jpg`)

New Game, 142 s, with this stream's trial death picture and the audio fixes. **Talking to the mother by E failed three times**: Dink walked up to her
(24 px east of her, facing west, held W toward her; then from the south-east): `talk: no sprite by the original rule from Dink at
187,197 dir 4` with the mother at 143,196, and no conversation started; on the third try she had wandered off and E read the bed
("This is my bed. So clean and neat! Mom must have made it."). Milder, Pete, the save machine and the King all answered E in
the other sessions (A66). The sack from the south: Dink stops at 462,156 again, nothing taken (A54). Ethel's house on arrival:
the camera sits behind a dark partition, Ethel's greeting in the box; one step in shows the room (A61 family). **Death among the
pillbugs of SCR_278: the limp body vanished** (only the blood pool stays, frames death_0..5): the ragdoll was thrown or sank.
The fallback that answers it (the body ignores creatures, a body that drifts or sinks is laid down at the feet) went to PR #140, which carries Dink's death fall. Death menu "Load", slot "Slot 1 - 0:04 - Level 1": back at the save machine, Dink walks.

## Physical mapping (owner's request of 15 Nov: hitboxes, collisions and objects match what is drawn)

Noted by eye at every beat of the sessions (the systematic all-screens measurement is the physical-mapping stream's).

| Where | What a player sees | Frame | Verdict |
|---|---|---|---|
| SCR_001, the feed sack S001_P52 (448,130) | walking at it from the south (448,200) or south-west Dink stops 26 px / 21 px short with nothing drawn between him and the sack, and it is not picked up; from the west (380,130) it is taken at once | `d_checks.jpg` (sack_b1_0/1) | defect A54 (pickup not taken / invisible stop) |
| SCR_001, the mother | E in front of her (24-28 px, facing her) starts no conversation; her body passes into Dink's when she walks beside him | `a_stonebrook_newgame.jpg` (frame 007) | known: A7 (3D sweeps for NPC moves, owner decision) / A21 |
| SCR_407, the pigs | a pig walks through Dink | `a_stonebrook_newgame.jpg` (frame 022) | known: A21 (creatures have no player collision) |
| SCR_278, pillbugs | a pillbug's body overlaps Dink's legs while it bites | `a_stonebrook_newgame.jpg` (frames 036-038) | known: A21 |
| SCR_278, a punch | the punch that killed the pillbug landed with Dink's fist at its body (no hit from a distance seen); the kill left its blood pool | `d_checks.jpg` (fist_kill) | as drawn |
| SCR_001 door S001_P25, SCR_409 door S409_P16 (Ethel) | both warp as Dink's body reaches the doorway; on SCR_439 the house door is just north of the arrival point, so walking north re-enters the house (as 1997) | `d_checks.jpg`, session A log | as drawn |
| SCR_277, the rock S277_P03 | the push needs Dink pressed against the card's base; at strength 4 it slides east and the hole behind it warps Dink into the cave | `a_stonebrook_newgame.jpg` (frames 045-046) | as 1997; the rock is a card (art) |
| SCR_195, the healer's west wall | the probe's chapter-19 save stands Dink at 78,212, inside the west wall (1997 hardness rect 85-133); after a load the camera shows only the wall for 12 s and Dink can walk further west into the void | `e_load_slots_and_milder.jpg` | a probe artefact (its stand-by put him there), not reachable by walking; noted for the probe |
| SCR_273, SCR_597, SCR_603: the magic potions | the potions lie on 1997 grass (S273_P08 tile 41, S597_P01 tile 915), but water is drawn there: Dink stands on the water surface with his shadow on it to take them | `r_ch1_water_over_grass.jpg` | defect A59 |
| SCR_408, the north-south fence | the fence's collision is the 1997 rail; the drawn card is a 3 m upright post beside it | `a_scr408_fence_ns_cards.jpg` | art (PQ-Q2) |
| SCR_086, Seth | his attacks and bombs hit Dink from a 60 cm grey cylinder; no body to judge | `e_seth_grey_cylinder.jpg` | art (A53, PQ-Q1) |

Not exercised by hand: sword hits (the longsword was not armed in a session), bow hits on a still target, the chests' potions.

## Defects found

All are rows of `doc/remaster/ALPHA_BUG_LIST.md` (Playthrough QA section) or of `doc/remaster/FABLE_ART_QUEUE.md` (PQ rows).

| Row | Sev | What | State |
|---|---|---|---|
| A58 | S1 | the packaged game crashes on entering SCR_036 (Terris) with audio on: a repeating cue duplicated a cooked SoundWave | fixed, PR #138 (own PR) |
| A53 | S1 | script-made sprites without art are grey cylinders: Seth (the final boss), the first quest's nut, the cult's girls | art (PQ-Q1); code queue: the 1997 picture on a card instead of the cylinder |
| A28 | S2 | Dink stands upright when he dies (gore audit row) | PR #140 carries Dink's death fall; this stream's limp-body version (seen below) was handed to it and is not in this PR |
| A52 | S2 | a red wireframe debug sphere over every attacker that winds up | fixed: `dink.TelegraphMarker` default 0 (`Dink.AI.TelegraphMarkerOffByDefault`) |
| A55 | S2 | pixel cards on the main route (N-S fences by the first save machine, Ethel's cottage, the push rock, the King and his knights, 536's rock and chests) | art (PQ-Q2, Q4-Q6, VS-01) |
| A56 | S2 | four sound cues silent (punch hit 9, bow draw 44, axe 48, bird 49): both takes rejected by the owner | owner: new takes |
| A59 | S2 | physical mapping: water drawn over grass where potions lie (SCR_273, 597, 603); Dink walks on it | open (terrain/water mask) |
| A61 | S2 | interiors float on the empty interior plane when the camera is behind a wall | open |
| A57 | S2 | screen-entry hitches, worst 758 ms (Joppa basement, packaged) | open |
| A51 | S3 | slot lines "Saved game" instead of 1997's "Slot N - H:MM - Level L" | fixed (`Dink.Save.SlotInfoAsOriginal`), seen in game |
| A54 | S3 | physical mapping: the feed sack cannot be reached from the south | open |
| A66 | S2 | talking to the mother by E fails in front of her (SCR_001) | open |
| A60 | S3 | a `say_xy` text survives the screen change ("The best in bows" at the goblin gate; dink.cpp:7977, 6160-6186) | open (probe re-baseline needed) |
| A62 | S3 | the camera presses into Dink in his house's north-east corner | open |
| A67 | S2 | the camera enters big pixel cards (the 536 chest after the bomb, by hand; the fire card, chest cards in the probe's stand-bys) | open |
| A68 | S3 | the probe's healer stand-by leaves Dink inside a west wall (SCR_195, SCR_033) | open (probe) |
| A69 | S3 | about 1 s of black entering Ethel's house | open |
| A63 | S3 | black backs of town-roof cards fill the view on SCR_474 | art |
| A64 | S3 | an ensure at every packaged start: `dink.GrassDensity` not a scalability variable | fixed (`Dink.Config.ScalabilityCVars`) |
| A65 | S3 | rendered packaged Ch4/Ch11 traces differ from the editor's by a pixel in two probe notes | open |


## Not exercised

* Combat by hand beyond the fists: the longsword was never armed in a session; the bow and the fireball were fired at wandering ducks and missed (no hit, no miss on visible contact could be judged). The probe's sword, bow and magic fights were seen only as rendered beats.
* Eating: the food on the table was walked onto at full life (no "Yum!" checked). Drinking: potions were taken by the probe in the rendered run (stat raises in its log), by hand only the rock push and the bomb.
* Hand play of chapters 2-19 (the probe played them rendered); the ending was played by hand from a chapter-19 save with `&story` 15 set by the console (Seth's 300 hp were not fought down by hand).
* Gamepad, mouse (left click attack), window resizing, the map (M), Esc's Help / Restart / Quit / gamepad entries, options and audio levels (audio ran on SDL's dummy device: cues are checked in the log, never heard).
* A packaged New Game played by keys (the hand sessions ran in the editor `-game`; the packaged game ran the probe).
* The owner's packaged build (`DinkRemaster-master`) was not touched.

