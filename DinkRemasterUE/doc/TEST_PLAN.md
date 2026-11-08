# Test plan: Stonebrook pre-production build (7 Nov 2026)

What this build claims, how each claim is checked, and what only a person can judge. Automated
results are filled in at the bottom after each run; the manual sections are a checklist to
play through with the editor or the packaged game, ticking boxes and noting the screen number
(`dink.Where`) of anything wrong.

## 1. Scope

- **In:** the whole original world as a greybox, Stonebrook with authored art (house, yard, Dink,
  mother), the converted story (377 scripts), gameplay rules, creature brains, locked fights,
  save/load, approved sound effects and music.
- **Out (not built yet):** animation, corpses, inventory and escape menus, thorn barriers, voice,
  the packaged game, Steam Deck, Windows.

## 2. Automated layers (run first, every time)

| Layer | Command | Checks | Pass bar |
|---|---|---|---|
| Build | `Scripts/build.sh` | editor target compiles | 0 warnings |
| Full suite | `Scripts/test.sh` | Core 35, Gameplay 35, Art 19, Narrative 15, AI 12, Import 12, Audio 2 | all pass, 0 warnings except the offline HTTP check |
| Converter | `cd ../tools/dinkink && python3 -m unittest discover -s tests` | DinkC to Ink | 25 pass, inklecate 0 errors |
| Story smoke run | `dink.SmokeRun` or `Dink.Narrative.Smoke.AllEntryPoints` | every entry point runs | 930 entries, 0 errors, only the 27 known idle loops capped |
| Play-through probe | `Dink.Gameplay.Probe.Stonebrook` | new game to the cult ambush with real interactions | 47 of 47 steps, identical trace each run |
| Re-import drift | `Scripts/import_greybox.sh --region all` twice | generated world is deterministic | second run: drift 0 |

A failure here stops the manual plan: fix it first.

## 3. Manual plan A: first ten minutes (30 min)

Open `L_Greybox_World`, press Play, new game. Keys: WASD, mouse, E talk, Space skip, F attack, Q cast.

- [ ] Mother's opening scene plays, text readable at your window size, Space skips lines, Dink is released at the end.
- [ ] Talk to her (E): menu opens, 1-9 and arrows work, chosen option's line matches the original.
- [ ] Walk onto the feed sack: it vanishes and `dink.Inventory` lists it. Leave and re-enter the house: still gone.
- [ ] Front door lands you in the yard (SCR_439) facing away from the door; the house reads as the same building from outside.
- [ ] Pig pen (`dink.Goto 407`): `dink.Arm item-pig`, F in the pen: pigs react, the bully scene plays through.
- [ ] Ethel's duck quest end to end (SCR_002, woods 440/441).
- [ ] AlkTree (SCR_474): punch until a nut drops, pick it up.
- [ ] House fire scene, villagers, gravedigger's letter: `dink.Fact story` reaches 6.
- [ ] Save (`dink.Save 1`), quit to editor, Play again, load (`dink.Load 1`): same screen, facts, inventory.

## 4. Manual plan B: combat and creatures (20 min)

- [ ] Pillbugs (`dink.Goto 278`): they close on you, never walk through walls; 3-4 punches kill one; ~1 in 3 drops a heart; heart heals by touch.
- [ ] Bonca (`dink.Goto 29`): it chases and swings; with the adaptation layer on you see the red wind-up sphere and can step out of the swing; at most two creatures attack at once.
- [ ] Set `Enabled=0` in `Content/Dink/Data/AI/adaptation.ini`, reload: attacks land without wind-up (Classic).
- [ ] Locked fight (`dink.Goto 302`): grey slabs block the open edges, screen line says `[EXITS LOCKED]`, slabs drop and the "secret" cue plays when the last Bonca dies.
- [ ] Martridge's cave Bonca (SCR_100): beatable with fists at starting stats by keeping distance.
- [ ] Fireball (`dink.ArmMagic item-fb`, Q): charges in 5 s at magic 2, flies where you face, stops at walls.
- [ ] Touch damage: stand in a pillbug: life drops once per 0.4 s, not every frame.
- [ ] Die: `dink.Fact life 1`, take a hit: `dinfo` death handling runs once.

## 5. Manual plan C: world and scale (45 min, the greybox's real question)

Teleport across the map and note screen numbers.

- [ ] Stonebrook at x4 feels like a village, not a field; house interiors at x1.75 are not cramped with the camera.
- [ ] Wilderness runs (Stonebrook to the toll bridge 404, Terris, the goblin lands): where are the dead stretches?
- [ ] Sightlines: from the mainland shore, can you see Joppa, the Darklands or the snow isle? (They should be lost in fog.)
- [ ] Cliffs and shorelines: do the 1 m outline prisms read as cliffs, or as arbitrary walls?
- [ ] Sprite cards turn to face you within 60 m and never show edge-on; `dink.Billboard 0` to compare.
- [ ] Other interiors (not Dink's house) have the plain wall slabs on their closed edges and no view into the sky.
- [ ] Every interior door and cave entrance warps both ways; note any that drop you inside hardness (you cannot move).
- [ ] Performance: `stat fps` with everything loaded; note anything under 60 on the RX 6800.

## 6. Manual plan D: audio (10 min)

- [ ] Approved sound effects play on their cues: quack, pig, punch, sword pickup, level-up, secret, save machine hum, fire loop seamless.
- [ ] Music changes per screen volume (village 104, interior 105, wilderness 1007) and stops where the original stops (screens 188, 253).
- [ ] Nothing from the original audio files plays anywhere (licence rule).

## 7. Story parity spot checks (15 min)

Pick five conversations at random from `Saved/Narrative/smoke_report.txt` and compare every line and option on screen with the `.c` file in `bin/dink/story/`. Record any difference other than the known U+00A0 spacing rule. Also check two of the 66 items in `tools/dinkink/out/review_queue.csv` behave as the engine did (not as the author wrote).

## 8. Reporting

For each failed box: screen number, what you did, what happened, what you expected, a screenshot
(`Saved/Screenshots/`). Put the notes in `Saved/Playtest/notes_<date>.md`. Anything that is a
guessed constant (move speed 60 px/s per speed point, fade 600 ms, talk range 3.5 m, wind-up
450 ms) is a tuning note, not a bug.

## 9. Automated results log

| Date | Build | Suite | Notes |
|---|---|---|---|
| 7 Nov 2026 | BUILD OK, 0 warnings | 133/133 passed, 0 failed, 0 warnings, 763 s (slow: ran beside another session's editors) | after the screen-name re-import; suite then had Core 35, Gameplay 35, Art 19, Narrative 15, AI 12, Import 12, Audio 2 plus newer tests |
