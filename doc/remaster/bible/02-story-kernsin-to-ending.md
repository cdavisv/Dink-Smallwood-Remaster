# Dink Smallwood content bible: regions s3–s8, sc-, and misc scripts

All 128 prefixed files plus the 12 named misc files were read in full. Everything is in `bin/dink/story/`. To answer "is this script used?" I also string-searched `map.dat` and peeked at three out-of-slice files (`en-gmog.c`, `en-drag.c`, `king.c`) because slice scripts hand off to them.

## 1. Plot beats in order

Key globals: `&story`, `&mayor` (KernSin quest), `&gobpass`, `&s4-duck`, `&s5-jop`, `&s7-boat`, `&snowc`, `&duckgame`, `&bowlore`. A designer comment in `s3-1st.c` documents `&story` 6–10.

- **Gate to sector 3 (`&story < 8`)**: rocks block the way (`s3-block.c` sets `&vision = 1`). The sign reads "KernSin is closed until preparation is complete." (`s3-sign1.c`). `&story` 8 is set by the earlier cult quest, outside this slice.
- **Entering sector 3 (`&story == 8`, `s3-1st.c`)**: Dink hides and overhears two Cast knights planning to raid the town during the festival, with "Mog" and "Joon the bowman" as go-betweens. Sets `&story = 9`.
- **KernSin parade quest (`&mayor` 0–7)**:
  - 0→1: tell Christina, the painter in the town square, about the assault (`s3-chick.c`).
  - 1→2: she leads Dink to Hiram's Bookstore (`s3-st1o.c`).
  - 2→3: the Mayor, inside the bookstore, demands proof (`s3-mayor.c`).
  - At 3, Christina passes on a rumor about the Goblin Sanctuary.
  - The goblin gate guard only opens if Dink is wielding a bow (`item-b1`) and `&mayor == 3`; he mistakes Dink for Joon. Sets `&gobpass = 1` (`s3-gobg.c`).
  - Killing every goblin on the screen spawns Mog (`s3-gh.c`, `s3-gs.c` → `s3-mog.c`).
  - Mog's death (`en-gmog.c`): he begs, reveals the Cast camp, sets `&gobpass = 5`, warps to map 489.
  - `s3-camp.c`: scripted sneak into the tent. `s3-camps.c`: Dink leaves with the scroll, is ambushed by four knights, the leader exits, and Dink fights three in a screenlock. `&mayor = 4` is set as the fight starts.
  - 4→5: show the scroll to the Mayor; warp to map 586.
  - `s3-tc.c` parade cutscene (`lovin.mid`): Christina thanks Dink. Sets `&story = 10`, `&mayor = 6`.
  - 6→7: a lone worker says the parade is over (`s3-loser.c`).
- **Windemere (`&story >= 10`)**: the bridge is repaired (`s4-1st.c`, `s4-sign1.c`). The town starves because it tithes food to sacred ducks.
  - Hitting the talking tree gives a hint about a cracked rock near the Duck Idol (`s4-tree.c`).
  - Bombing that rock sets `&s4-duck = 1` (`s4-rock.c`).
  - Killing every duck in the enclosure runs `s4-end.c` (via `s4-duck.c` `duckdie`): the townsfolk discover duck tastes good. Sets `&s4-duck = 2`, `&story = 11`.
- **Joppa Isle (`s5-`)**: the scripts do not show how travel there is unlocked.
  - First visit: the town is deserted (`&s5-jop` 0→1, `s5-jops.c`).
  - The basement scene with the hiding parents sets `&s5-jop = 2` (`s5-base.c`, `s5-guy.c`).
  - Back in town: daughter Gwen appears, two dragons arrive, and Dink must protect father, mother and daughter (`s5-fguy.c`).
  - When both dragons die, `en-drag.c` spawns `s5-end.c`: sets `&story = 12`, `&s5-jop = 4`.
- **King (out of slice, `king.c`)**: `&story` 12→13→14 when Dink offers to help Milder.
- **Edge of the World (`s6-`)**: the church shopkeeper says Milder is in the darklands and the portal is close. The ancients' machine ("Press the red button", `s6-warp.c`) warps to map 154.
- **Darklands (`s7-`)**: screenlocked monster rooms, a boat that sails off on first entry (`s7-hell.c`, `s7-boat.c`), and ghosts of a mother and child.
- **Milder and Seth (`s7-mil.c`)**: Milder is dying and says the Cast were a front. After a two-option choice, Seth appears, kills Milder with an explosion, and the boss fight starts (`s7-boss.c`).
- **Seth's death**: Dink says "Too bad I had to kill him, he seemed likable enough." and "I must now get back to Goodheart Castle and inform the King." Sets `&story = 15`. `s7-warp.c` returns to map 253.
- **Ending (`king.c`)**: at `&story == 15` the King hears the news, a congratulations and credits crawl plays, six potions spawn, and `&story = 16`.
- **Post-game reactions (`&story > 14`)**: `s6-g1.c`, `s6-g2.c`, `s6-st1p.c`, `sc-wiz.c`.

## 2. Named characters and NPCs

**Sector 3: KernSin and surroundings**

| Who | Where | Role and personality | Characteristic line (file) |
|---|---|---|---|
| Cast knights | Road and camp | Conspirators | "Our business doesn't need to be told to the dead.." (`s3-camps.c`) |
| Christina | Town square | Painter, Mayor's daughter, earnest | "For the big parade happening soon, what else silly?"; when hit: "Guards, guards, tis a bloodbath!" (`s3-chick.c`) |
| Mayor | Hiram's Bookstore | Pompous, cautious | "Yes, without it my hands are tied." (`s3-mayor.c`) |
| Bookstore clerk | Hiram's Bookstore | Prim | "Magic?  No such thing."; when hit: "Oh my golly gosh, please don't hurt me mister..." (`s3-st1p.c`) |
| Arturous | Bow shop | Smug salesman | "That hurts and all, but you could be doing much more damage with a bow!" (`s3-st2p.c`) |
| Robinson Cabinets owner and daughter Promise | Furniture shop | Henpecked father, spoiled child | "DADDY!!!!!!!!!" / "I SAID NOW!!"; when hit: "Hey, stop that, you'll hurt the wood." (`s3-larry.c`) |
| Duck freak | House | Hyperactive, rehearsing a duck parade act | "he has issues."; if ducks are dead: "My ducks!!!!!!!! ALL DEAD!!!!!!! DAMN YOU!" (`s3-freak.c`) |
| Grumpy homeowner | House | Three random intrusion skits | "YES, now get the HELL OUT!!" (`s3-bh.c`) |
| Bow-lore man | Hidden beach hut | Trainer | "Hello, friend.  I will teach you bow lore for $1500 gold." (`s3-bowl.c`) |
| Goblin George | Own house outside the sanctuary | Pacifist who wants to live with humans | "george is hoomankind."; sign: "welkam to george huse" (`s3-gob.c`, `s3-gsign.c`) |
| Goblin gate guard | Sanctuary gate | Suspicious | "no bow?!!! un not joon! leev!!" (`s3-gobg.c`) |
| Goblins | Sanctuary | Speak gibberish | "Hoglim dack byork!" (`s3-gh.c`, `s3-gs.c`) |
| Mog | Sanctuary | Goblin king, fluent | "Who dares wake the mighty Mog, king of Goblins?" (`s3-mog.c`) |
| Parade crowd | Town square | Cheerful | "Not a very long parade was it..." (`s3-peeps.c`) |
| Worker | Town square after parade | Deadpan | "I don't know man, I just work here." (`s3-loser.c`) |

**Sector 4: Windemere**

| Who | Where | Role and personality | Characteristic line (file) |
|---|---|---|---|
| Paranoid man | House 1 | Fireballs Dink on entry | "We all worship the duck here." (`s4-h1p.c`) |
| Starving family (mom, dad, girl) | House 2 | Meek | Girl: "I don't like the ducks."; mom when hit: "Please, don't beat a starving woman!" (`s4-h2p1.c`–`s4-h2p3.c`) |
| Voices behind doors | Locked houses | Hostile or desperate | "I hate you." (`s4-mdoor.c`); "Do you have food?" (`s4-md2.c`) |
| Altar guard | Duck altar | Solemn | "You can pray to the duck from here." (`s4-dg.c`) |
| Jill | Pawn shop | Devout, broke | "The ducks ... the ducks ..." (`s4-st1p.c`) |
| Furrier | Fur shop | Outsider, sensible | "Hides from dead things." (`s4-st2p.c`) |
| Blistering Pete | Weapons shop | Ex-pirate in hiding | "Don't challenge me boy, I'll give you a wooden leg!!" (`s4-st3p.c`) |
| Healer | Healer's shop | Polite | "Please don't wreck the place, thanks." (`s4-healp.c`) |
| Talking tree | East of town | Hint-giver | "Please sir, don't hurt me, the talking tree of the east!" (`s4-tree.c`) |
| Man, daughter Kelly, guard | Duck enclosure cutscene | Outraged, then converted | "THIS GUY KILLED THE BLESSED FOWL!" (`s4-end.c`) |

**Sectors 5–8 and the snow castle**

| Who | Where | Role and personality | Characteristic line (file) |
|---|---|---|---|
| Father, mother, daughter Gwen | Joppa | Besieged family | "Protect the women, Smallwood!" (`s5-fguy.c`) |
| Dragons | Joppa | Vengeful | "Run from us no more, humans." (`s5-fguy.c`) |
| Axe seller | Joppa weapons shop | Dry | "So, hitting the owner of a weapons store huh?" (`s5-st1p.c`) |
| Church shopkeeper | Edge of the World | Grave | "It is an abomination of nature.  I will not speak of it." (`s6-st1p.c`) |
| Two guards (one calls the other Tom) | Edge of the World | Supportive | "Testing out your weapons?  They work a-ok, trust me." (`s6-g1.c`) |
| Hellfire man | Cave | Nihilist | "Life isn't supposed to make sense." (`s6-vend.c`) |
| Ghost mother | Darklands | Menacing | "LOOK UPON MY DEFORMED FACE!" (`s7-mom.c`) |
| Ghost girl | Darklands | Eerie | "Would you like to see me take my head off?" (`s7-girl.c`) |
| Milder Flatstomp | Darklands | Dying rival knight | "..you are more of a knight than I ever was, dink..." (`s7-mil.c`) |
| Seth | Darklands | Ancient one, final boss | "I am the beginning and the end." (`s7-mil.c`) |
| Giant ducks | Koka Isle | Friendly, run duck fights | "Hi, we are the giant ducks of Koka Isle."; "Hey man, don't make me put you in the arena!" (`s8-duck.c`, `s8-duck4.c`) |
| Bow-maker | Koka Isle | Craftsman | "I am working on the most powerful bow in the world!" (`s8-guy.c`) |
| Wizard | Snow castle | Still fighting a war that ended 100 years ago | "The war, the goblin war!" (`sc-wiz.c`) |

The wizard carries the main lore: the Smallwood line was exiled, and the ancients "can draw and feed upon magic from your family."

**Signs and talkable objects**
- Signs: "Hiram's Bookstore"; "East to Terris"; "Goblin Sanctuary - Humans keep out to avoid incidents."; the duck tax decree, which becomes "Super-Fry Chicken opening soon." (`s4-sign3.c`); "Duck Worship Center", which becomes "Dink Worship Center" (`s4-dsign.c`); "Joppa Isle - the Island of Dragons"; "'Please be careful when using this machine.' - the ancient ones." (`s6-sign5.c`); "Blistering Pete waz here" (`s8-sign.c`).
- Objects: fountain ("Ah, cool and refreshing.", `s3-fount.c`); statue ("What a lovely stone!", `s4-stat.c`); satellite dish ("Wow, they have a dish.", `s8-dish.c`); well (`s8-well.c`); Dink lookalike ("That... sort of looks like me.", `s7-dink.c`).

## 3. Quests and side-quests

1. **Save the KernSin parade** (Christina, then the Mayor).
   - Steps as in section 1. The $1000 bow is effectively mandatory.
   - Reward: none scripted beyond story progress and the bridge to Windemere.
   - Variants: provoking the gate guard ("Incite an 'incident'") starts a fight but does not open the gate. Parade spectators can be attacked; they turn hostile and say "This Dink guy is no hero, he was behind the attack!", and when all are dead Dink says "Now, THAT'S entertainment!" (`s3-peeps.c`).
   - Killing the freak's ducks changes his dialogue permanently for that screen.
2. **Goblin George** (optional): talking to him yields the hint that killing guards summons Mog. He can be killed permanently; Dink says "Let that be a clear message to his people.  Haw!" (`s3-gob.c`).
3. **Windemere famine** (no giver).
   - Tree hint, bomb the rock (bombs are $20 at Pete's), kill all ducks.
   - Reward: none material. Every NPC gains gratitude lines, and the stairs in house 2 open (`s4-h2.c`).
4. **Joppa dragons** (father).
   - Escort fight. If any of the three family members dies, Dink's life is set to 0 ("Noooo!  The girl has died!  I HAVE FAILED!!!!!!!", `s5-fd.c`).
   - Reward: `&story = 12` and the Joppa axe shop opens (`s5-st1.c`). `s5-heals.c` also switches `&vision` at `&story >= 12`; from its name it is a healer screen, but that is my inference.
   - The twist is that the town was built on the dragons' nest.
5. **Rescue Milder** (King, out of slice): Edge of the World, warp, darklands, Seth.
6. **Side content**:
   - Bow lore training (`s3-bowl.c`).
   - Hellfire spell (`s6-vend.c`).
   - FlameBow, available at `&story >= 14` (`s8-guy.c`).
   - Duck-fight gambling (`s8-da.c`).
   - Snow castle lore (`sc-wiz.c`).
   - Bomb-rock gold hearts (`s4-sec1.c`, `s5-sec1.c`).
   - A burnable secret tree with stairs to map 227 (`s3-sec1.c`).
   - A healing and wishing fountain (`s6-fount.c`).
   - Hittable jumping fish worth 50–100 exp (`fish1.c`).
   - `findduck.c`: Ethel's duck from an earlier region has a 25% chance per visit to appear.

## 4. Regions

- **`s3-` KernSin**: temperate town with a fountain square, Hiram's Bookstore, the bow shop ("The best in bows"), Robinson Cabinets, two houses, and a hidden beach hut. Around it are George's house, the Goblin Sanctuary (walled camp, Mog as boss), and the secret Cast camp (tent, three-knight ambush).
- **`s4-` Windemere**: depressed village of duck cultists. It has the duck altar and enclosure, Jill's pawn shop, the furrier, Blistering Pete's, a healer, locked houses, and the talking apple tree.
- **`s5-` Joppa Isle**: "Island of Dragons". An abandoned town with a hiding basement, the dragon fight, and the axe shop.
- **`s6-` Edge of the World village**: church that doubles as a shop, two guards at the darklands approach, pit holes that warp to maps 182 and 166, the hellfire cave, and the ancients' warp machine.
- **`s7-` Darklands**: a hellscape (the script is literally `s7-hell.c`) with its own music. Screenlocked rooms hold boncas, pillbugs, slayers, blue slimes, dragons, killer ducks and "crazy girls". Also the ghosts, Milder, Seth, and the return warp.
- **`s8-` Koka Isle**: giant talking ducks, the duck-fight arena (map 731), the FlameBow smith, a well and a dish.
- **`sc-` Secret snow castle**: the name comes from the comment in `sc-ent.c`. Screenlocked gauntlet of boncas, pillbugs, slayers and dragons, with the wizard at the end.

## 5. Tone and humor

Types of joke: Dink as a cocky, amoral jerk; hit-reaction one-liners; puns; anticlimax; religious satire; pidgin dialect; pop-culture and developer in-jokes; dark reversals.

Verbatim examples:
1. "'Sign' me up.. for DESTRUCTION! Haw haw!" (`s3-sign1.c`)
2. "I can't read, damnit!" (`s3-sign3.c`)
3. "I'm gonna rock your world!" (`s3-rock.c`)
4. "Let me show you MY version of politics, friend!" (`s3-mayor.c`)
5. "Things tend to light on fire, and people I know just die. :'(" (`s3-larry.c`)
6. "Note to self:  Don't come here next year." (`s3-freak.c`)
7. "Hey old man, the funeral house called ..." / "they're ready for you now!" (`s3-bh.c`)
8. "Sir, your daughter is eating our god." (`s4-end.c`)
9. "IT TASTES GREAT!" / "LESS FILLING TOO!" (`s4-end.c`; a beer-ad slogan)
10. "It sure is easy to be deified these days." (`s4-dsign.c`)
11. "THESE PEOPLE JUST DON'T GET IT!" (`s4-stat.c`)
12. "So basically, I just killed two innocent Dragons for protecting their own?" (`s5-end.c`)
13. "I want to draw blood, not water!" (`s8-well.c`)
14. "Watch Conan O'brien!" (Seth at under 6 HP, `s7-boss.c`)
15. "I'm a bottle, not a duck.  Even though I sound like one.  Funny, eh?" (`duck.c`)

**Content to review for a modern release (unsanitized)**
- **Profanity**: "..you little bitch...if I only had the strength to..." (`s7-mil.c`); "Sell me something else you bastard!" (`s6-vend.c`); frequent "damn" and "hell" (`s3-1st.c`, `s3-bh.c`, `s4-h1p.c`).
- **Sexual innuendo**:
  - To the dying Milder about his girlfriend: "Tell her?  I'll SHOW her love... moohahahha!" (`s7-mil.c`).
  - "I've come for your daughter." (`s3-bh.c`).
  - "She's your daughter??  Is she single?" (`s3-mayor.c`).
  - "Oh, you will baby, you will..." (`s3-tc.c`).
- **Violence against children**:
  - `s7-dgirl.c` is a hostile enemy using the little-girl sprite (100 HP) that shouts "FOOD!" and must be killed to unlock the screen.
  - The ghost child says "Last thing I remember is that group of knights.. and blood." (`s7-girl.c`).
  - The guard says of Kelly: "I guess we have to kill her too." (`s4-end.c`).
  - The Windemere girl can be hit ("No mister!", `s4-h2p3.c`), and Gwen can be killed (`s5-fd.c`).
- **Beating starving or helpless people**: "Not the fists, not the fists!!" (`s4-h2p1.c`); "First feed us, then beat us, is that how it is with you?" (`s4-h2p2.c`).
- **Religious satire**: the whole Windemere arc is a starvation cult resolved by killing and eating its gods, e.g. "I MUST AVENGE THE WINGED GODDESS!" (`s4-end.c`). Seth's "I am the beginning and the end." (`s7-mil.c`) echoes scripture, and Dink's battle cry is "FOR GOD, THE CROWN AND ALL THAT IS GOOD".
- **Ethnic-coded goblins**:
  - Goblins speak broken-English pidgin.
  - The main quest requires massacring a sanctuary that asks humans to keep out.
  - Dink can taunt the guard with "King Daniel basically crushed you all like tiny bugs." (`s3-gobg.c`).
  - Dink's line after murdering the pacifist George is quoted in section 3.
- **Animal cruelty**: betting on duck fights ("we like our games here bloody", `s8-da.c`), and a mandatory duck slaughter.
- **Civilian massacre played as a joke**: `s3-peeps.c`.
- **Copyright and real-world references**: `spice.c` is an unfinished Spice Girls encounter and contains pasted song lyrics. Other references are Conan O'Brien, the beer slogan, "Super-Fry Chicken", and developer names (boss Seth, "Robinson Cabinets", and credits in `king.c`).

## 6. Dialog menus

- **Christina** (`s3-chick.c`): Say hi / Ask what she does / Tell her about the planned assault (`&mayor == 0`) / See what's happened since (3) / Show her the Scroll (4) / Leave.
- **Mayor** (`s3-mayor.c`): Say hi / Tell him about the planned assault (sets 3); at 3, "Show him the proof" is always rebuffed; at 4, "Show him the scroll with the plans" triggers the parade.
- **Bookstore clerk** (`s3-st1p.c`): bookstore / Magic / next town / news; the last two change at `&mayor >= 6`.
- **Arturous** (`s3-st2p.c`): Ask about Bows (gives the bow-lore hint once you own one) / Buy.
- **Robinson Cabinets** (`s3-larry.c`): Ask about the store / See what's for sale (triggers the Promise skit).
- **Duck freak** (`s3-freak.c`): Ask why he's running / Ask about the ducks (duck-follow demo) / Ask about the parade (`&mayor > 5`).
- **George** (`s3-gob.c`): name / why he's out here / the Sanctuary (Mog hint).
- **Goblin guard** (`s3-gobg.c`): Ask the Goblin guard to let you in / Incite an 'incident'.
- **Windemere**:
  - Altar guard (`s4-dg.c`): what he's guarding / getting in.
  - Paranoid man (`s4-h1p.c`): Ask what's up / Ask about the town; he refuses to talk further after the second.
  - House 2 mom and girl (`s4-h2p1.c`, `s4-h2p3.c`).
  - Door (`s4-md3.c`): Ask to come in.
  - Jill (`s4-st1p.c`): news → what's for sale → sell menu.
  - Furrier (`s4-st2p.c`), Pete (`s4-st3p.c`: store → Pete's backstory → buy), healer (`s4-healp.c`).
- **Joppa** (`s5-end.c`): "Pshaw, twasn't nuthin!" / "I saved all of you, actually." The script comment says "just for fun"; it has no effect.
- **Edge of the World**: fountain (`s6-fount.c`): Take a drink (full heal, free) / Drop in a coin (−1 gold, flavor only). Church shop: Say hi / See what she has. Warp machines: Press the red button.
- **Milder** (`s7-mil.c`): "Refuse to leave without him" / "Take his advice". Only the dialogue differs; the outcome is identical.
- **Koka Isle**: giant duck (`s8-duck2.c`): Go ahead and play / Not yet. Arena (`s8-da.c`): Bet 50 / 100 / 200 / Stop, then duck 1 or duck 2.

## 7. Shops, trainers and prices

| Location | Seller | Item | Price | File |
|---|---|---|---|---|
| KernSin | Arturous | Bow and arrows (`item-b1`) | $1000 | `s3-st2p.c` |
| Beach hut near KernSin | Bow-lore man | Bow lore (triple damage "when it works") | $1500 | `s3-bowl.c` |
| Windemere | Blistering Pete | Longsword | $400 | `s4-st3p.c` |
| Windemere | Blistering Pete | Bomb | $20 | `s4-st3p.c` |
| Windemere | Blistering Pete | Clawsword | $2000 | `s4-st3p.c` |
| Windemere | Healer | Heal | $1 per missing HP | `s4-healp.c` |
| Windemere | Healer | Elixir | $100 | `s4-healp.c` |
| Joppa (after `&story > 11`) | Axe seller | Throwing Axe | $3000 | `s5-st1p.c` |
| Edge of the World | Church shopkeeper | Light Sword | $4000 | `s6-st1p.c` |
| Edge of the World | Church shopkeeper | Massive Bow | $5000 | `s6-st1p.c` |
| Cave | Hellfire man | Hellfire magic (`item-sfb`) | $1500 | `s6-vend.c` |
| Koka Isle (`&story >= 14`) | Bow-maker | FlameBow | $25,000 | `s8-guy.c` |

- **Jill's pawn shop buys only** (`s4-st1p.c`): Longsword $200, nut $2, Clawsword $1000, slayer claw $150. She never sells anything.
- **The furrier sells nothing** (`s4-st2p.c`).
- **Duck fights** (`s8-da.c`): even-money bets of 50, 100 or 200.

## 8. Bosses and set pieces

- **Cast ambush** (`s3-camps.c`, `s3-dorks.c`): three knights in a screenlock, 150 exp each. Both scripts set stats: `s3-dorks.c` has HP 100, defense 6, strength 12; `s3-camps.c` then sets HP 40. Which wins depends on engine call order, so I can't state the final HP with certainty.
- **Goblin Sanctuary**: guard HP 80, defense 6, strength 25 (`s3-gobg.c`); goblins HP 40 and 60 (`s3-gh.c`, `s3-gs.c`). Mog (`en-gmog.c`) has HP 50, defense 4, strength 20 in a screenlock, and his death is scripted.
- **Joppa dragons** (`s5-fguy.c`, `en-drag.c`): two dragons. The escort targets are father HP 100, mother HP 50, daughter HP 50; any death is a game over.
- **Darklands rooms** (all screenlocked except the dragons):

| Enemy | HP | Other stats | File |
|---|---|---|---|
| Bonca | 40 | strength 10 | `s7-bong.c` |
| Pillbug | 50 | touch damage 25 | `s7-pill.c` |
| Slayer | 100 | defense 5, strength 20 | `s7-slay.c` |
| Blue slime | 50 | touch damage 17 | `s7-slimb.c` |
| Killer duck | 50 | touch damage 25 | `s7-duck.c` |
| Crazy girl | 100 | touch damage 20, speed 3 | `s7-dgirl.c` |
| Dragon | 80 | defense 8, casts "greater harm" for 30 | `s7-drag.c` |

- **Seth** (`s7-boss.c`):
  - HP 300, defense 25, touch damage 30. Gives 10,000 exp on death.
  - Attacks every 2–4 seconds. Half the time it is a telegraphed "<Casts explosion>" (a bomb at Dink's position). Otherwise it is "<Casts greater harm>" for 30 damage.
  - Greater harm is resisted when `random(40,1)` is not greater than `&magic`, so a magic stat of 40 or more makes Dink immune.
  - His speed rises as HP falls: below 270, 200, 100 and 15.
  - He has 12 HP-banded taunts, from "You are just like me you know, Dink." down to "MOTHER!!!!!!!!!!".
  - On death: six explosions, Dink says "EAT IT!", and Dink's life is refilled.
- **Snow castle**: `sc-lock.c`, `sc-pill.c`, `sc-slay.c` and `sc-drag.c` clone the darklands enemies; the `sc-` dragon casts "harm" for 20 instead of 30.
- **Wizard** (`sc-wiz.c`): cannot be killed; he teleports when hit ("Bad idea ...").

## 9. Unfinished, cut or buggy

- **Not placed in `map.dat` and not called by any script** (string search, so treat as probable rather than certain):
  - `spice.c`: the Spice Girls scene; its variables are never assigned.
  - `treeduck.c`: a tree that says "I feel magical!" and spawns a duck when hit.
  - `water.c`: "Yum, water!"
  - `fire.c`, `thes.c` (empty), `sc-ent.c`, `s4-gs.c`.
  - `s3-ch1.c`: an invisible chest holding a potion.
  - `duck.c`: no exact match found.
  - `s6-chur.c` is placed but empty.
- **Stubs and hacks**:
  - `s3-chick.c` prints "** FIXING BUG.. RESETTING GOBLIN VILLAGE **" and resets `&gobpass`.
  - The Mayor's proof check is a stub (comment "//Check to see if he did").
  - `&mayor = 4` is granted before the ambush is won.
  - The furrier's shop has only a comment ("//Let Dink buy stuff ...").
  - Jill promises stock that never arrives.
  - Music cues are commented out (`Sneaky.mid`, `planning.mid`, `Urgent.mid`).
  - `s3-gh.c` notes "we don't have the death graphics yet".
- **Syntax and logic bugs**:
  - Missing brace so `attack` nests inside `die` (`s3-dorks.c`, `s3-gh.c`, `s3-gs.c`).
  - Missing comma in Christina's introduction line.
  - `reutrn;` typo, so both hit lines play (`s4-h2p2.c`).
  - Stray `f` character and a missing `return` in `hit` (`s4-st3p.c`).
  - `goto mainloop` with no such label (`s4-st1p.c`, `s4-st3p.c`).
  - Unclosed parenthesis in `s4-sign3.c`.
  - `&prom` used before it is declared (`s3-larry.c`).
  - `s8-duck2.c` forces `&talker = 1`, so its first branch is dead; that branch also has Dink speaking the duck's line.
  - `s8-da.c`: "Congradulations!", and "You can't bet that much." is spoken by the wrong sprite.
  - Speaker colors are inconsistent in `s6-vend.c` and `s4-st2p.c`.
  - In `s6-st1p.c` and `s8-duck3.c` Dink speaks the hit reaction ("Hahaha!!", "Yeah, this is fun!").
  - `emake.c` rolls `random(3,1)`, so food type 4 is unreachable.
  - `make.c`: `spotion` makes an `rpotion`, `lheart` makes an `sheart`, and `foodduck` meat has its pickup script commented out.
  - After Seth kills Milder, talking to the body still gives "Milder, wake up!  Help me fight this guy!" (`s7-mil.c`).
- **Not in this slice**: `&story` 12→14 and the ending live in `king.c`; the dragon stats for Joppa live in `en-drag.c`.
