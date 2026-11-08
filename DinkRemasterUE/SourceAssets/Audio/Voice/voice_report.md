# Voice report

- Source lines: 2125; distinct (script, spk) pairs: 377; distinct voices: 29.
- voices.csv counts only voiced lines (kind dialogue, object, narration); `system` lines are excluded there and have an empty `voice` and empty `tts_text` in voice_lines.csv. voice_cast.csv counts every line in the pair.

## Lines per kind

| kind | lines | chars |
|---|---|---|
| dialogue | 1975 | 63283 |
| object | 96 | 3756 |
| narration | 21 | 735 |
| system | 33 | 712 |

## Lines per voice (voiced lines only)

| voice | lines | chars |
|---|---|---|
| dink | 811 | 24371 |
| man_middle | 263 | 7841 |
| merchant | 100 | 4009 |
| narrator | 99 | 3680 |
| woman_middle | 85 | 2814 |
| man_old | 74 | 2287 |
| girl | 71 | 2424 |
| guard | 64 | 2621 |
| wizard_old | 43 | 1616 |
| christina | 39 | 1352 |
| duck | 39 | 925 |
| zands | 38 | 1747 |
| martridge | 38 | 1408 |
| traveller | 37 | 1557 |
| goblin | 33 | 907 |
| man_young | 31 | 888 |
| woman_young | 30 | 853 |
| woman_old | 30 | 920 |
| milder | 29 | 1002 |
| villain | 27 | 680 |
| king | 23 | 910 |
| nelson | 21 | 706 |
| mother | 16 | 611 |
| seth | 15 | 462 |
| ghost | 13 | 384 |
| monster | 9 | 290 |
| tree | 7 | 247 |
| mog | 5 | 217 |
| dragon | 2 | 45 |

## Stage-direction tokens and mapping

| token | occurrences | action | lines |
|---|---|---|---|
| `<Casts explosion>` | 1 | line is a spell-cast caption: kind system, never voiced | s7-boss.attack.001 |
| `<Casts greater harm>` | 2 | line is a spell-cast caption: kind system, never voiced | s7-boss.attack.002, s7-drag.attack.001 |
| `<Casts harm>` | 2 | line is a spell-cast caption: kind system, never voiced | en-drag.attack.001, sc-drag.attack.001 |
| `<N>` | 6 | kept (runtime number placeholder; line is system, never voiced) | 1gold.touch.001, gold200.touch.001, lgold.touch.001, mgold.touch.001, sgold.touch.001, xlgold.touch.001 |
| `<begins to tear up>` | 1 | tts tag [begins to tear up] | s1-h2-o.talk.021 |
| `<bursts into tears>` | 1 | tts tag [bursts into tears] | s2-jack.die.003 |
| `<casts explosion>` | 1 | line is a spell-cast caption: kind system, never voiced | s7-mil.talk.032 |
| `<chortles>` | 1 | tts tag [chortles] | s1-h2-o.talk.009 |
| `<chuckle>` | 2 | tts tag [chuckles] | s1-gg.hit.002, s1-gg.talk.009 |
| `<giggles>` | 1 | tts tag [giggles] | s7-girl.hit.001 |
| `<grins evilly at you>` | 1 | whole line is a non-vocal action caption: kind system, never voiced (voice director may re-add as an animation cue) | s7-mil.talk.035 |
| `<groan>` | 1 | tts tag [groans] | s7-mil.talk.004 |
| `<grumble>` | 1 | tts tag [grumbles] | s2-jack.talk.004 |
| `<laugh>` | 1 | tts tag [laughs] | s1-h1-m.talk.011 |
| `<presses button under the counter>` | 1 | whole line is a non-vocal action caption: kind system, never voiced (voice director may re-add as an animation cue) | s2-bar.talk.004 |
| `<shiver>` | 2 | tts tag [shivers] | s1-cave.noise.001, s1-caves.noise.001 |
| `<sniff>` | 1 | tts tag [sniffs] | s1-h3-l.talk.011 |
| `<sob>` | 2 | tts tag [sobs] | s2-auntp.main.008, s2-jack.talk.024 |

Other text rules applied: runs of two or more spaces collapse to one (including after `!` and `?`, not only after a full stop); `*word*` loses its asterisks (only `*HATE*` occurs in voiced text; `* ... *` banner lines are system); ALL-CAPS words kept; no word added, changed or removed. No `<sigh>` occurs in this data, but the mapping `<sigh>` to `[sighs]` is implemented.

## System lines (never voiced)

33 lines: gold pickups, potion/stat notice, `* ... *` banners, spell captions, "Magic resisted.", game messages, the debug line in s3-chick, two action captions.

## Pairs attributed with low confidence (best guess is the assigned character)

| script | spk | best guess | voice | why |
|---|---|---|---|---|
| s1-brg2 | `current_sprite` | toll man | man_middle | toll man: role from bible, no name |
| s1-h1-o | `s1_h1_o__person2` | Lyna | woman_young | variable person2 is a girl sprite (colour 4 = Lyna elsewhere); best guess Lyna |
| s1-h1-o | `s1_h1_o__person1` | Ethel | woman_old | variable person1 is the old lady sprite; Ethel by context |
| s1-h1-o | `s1_h1_o__person3` | Milder Flatstomp | milder | variable person3 is the silver knight sprite; best guess Milder |
| s1-h3-5 | `s1_h3_5__man` | Mr. SmileStein | man_middle | unnamed man; colour matches Mr. SmileStein |
| s2-bar | `s2_bar__crap` | Cast agent / bar thug | villain | sprite var is a created sprite reused for two different characters |
| s2-fight | `current_sprite` | dying fighter | man_middle | script is an empty death handler; no name in source, gender guessed |
| s2-healp | `temphold` | healer | merchant | healer: gender not stated |
| s2-mdoor | `s2_mdoor__me` | old magician | wizard_old | unnamed old magician in Terris; distinct from Martridge per bible |
| s2-qgirl | `current_sprite` | girl | girl | unnamed girl |
| s2-wench | `temphold` | barkeep | man_middle | temphold in s2-wench is inherited from the bar script (the barkeep); best guess |
| s3-larry | `current_sprite` | Robinson Cabinets owner | man_middle | owner is not named in the source (script name larry) |
| s3-peeps | `current_sprite` | parade spectator | woman_middle | several different spectator sprites share this script; gender mixed, one voice assigned |
| s4-healp | `temphold` | healer | merchant | healer: gender not stated |
| s4-md2 | `current_sprite` | voice behind a door 1 | man_middle | speaker unseen; gender guessed from colour/lines |
| s4-md3 | `current_sprite` | voice behind a door 2 | woman_middle | speaker unseen; "My children are starving" suggests a mother |
| s4-mdoor | `temp1hold` | voice behind a door 3 | man_middle | temp1hold is sprite 7 (an unseen door occupant); gender unknown |
| s4-not | `temp4hold` | starving father | man_middle | temp4hold; colour matches the starving father |
| s4-st1p | `current_sprite` | Jill | merchant | Jill: gender not stated, bible refers to the shop only |
| s5-end | `temp3hold` | Gwen | girl | temp3hold colour 13 shared with mother; guess Gwen |
| s5-end | `temp2hold` | Joppa mother | woman_middle | temp2hold colour 13 matches the mother; guess |
| treeduck | `current_sprite` | magical tree-duck | duck | sprite spawns a tree/duck; identity guessed |

Also worth a listen-check: scripts where one sprite variable is reused (`s2-bar` `crap`: Cast agent and bar thug), and `s3-peeps` where several different spectator sprites share one script.

Preview note: the `dragon` voice has only two lines in the whole game (45 characters), so its preview_text is below the 150-character minimum and is simply both lines.

## Ten longest lines

| id | chars | text |
|---|---|---|
| s2-mdoor.talk.009 | 88 | he was imprisoned by agents of the Cast and that the lock can only be broken with magic! |
| s2-signe.talk.001 | 82 | Danger! Murkwood Forest - Has been magically sealed shut by decree of King Daniel. |
| s2-ca-g.talk.011 | 80 | No.  After the war was won he created a special place for them to live in peace. |
| s4-end.main.021 | 80 | No.. there is a perfect explanation, you see, the friction seemed to cook and... |
| poster.talk.025 | 79 | taught them proper agricultural procedure he learned pig farming in Stonebrook. |
| s2-man2.main.015 | 79 | Yup.  I raised him from when he was a pup.  He would do anything I told him to. |
| poster.talk.008 | 78 | Also in the news:  A pig farmer named Dink Smallwood found a lost Terris girl. |
| s2-ca-g.talk.009 | 78 | It was his strategic brilliance that stopped the Great Goblin invasion of '23. |
| s2-ca-g.talk.016 | 78 | I've never heard of you.  Please, go back to your village and play hero there. |
| s2-mdoor.talk.006 | 76 | Young Maulwood, people get trapped in places they shouldn't go all the time. |
