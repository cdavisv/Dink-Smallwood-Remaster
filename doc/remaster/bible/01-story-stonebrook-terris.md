# Dink Smallwood content bible — Stonebrook (s1), Terris (s2), system scripts

All files are in `bin/dink/story/`. I read every in-scope `.c` file in full (about 170); nothing was modified.

- There are no `intro*` files; the opening is the mother's dialogue in `s1-h1-m.c`.
- I also peeked at `item-pig.c`, `findduck.c`, `dam-icee.c` and the strings in `../map.dat` to confirm triggers and which scripts are actually placed on the map.
- NPC dialogue carries colour prefixes such as `` `3 `` or `` `# ``; I have stripped them from quotes.

## 1. Plot beats in order

**Stonebrook (story 0 to 6)**
1. **New game** (`start-1.c`, `newgame.c`): Dink spawns in his house with fists only. Mother: "Dink, would you go feed the pigs?" / "What, now?" / "YES, NOW." Sets `&story=1` (`s1-h1-m.c`).
2. **Pig feeding**: pick up the feed sack (`s1-sack.c`) and use it in the pen on map 407 (`item-pig.c`). This spawns Milder Flatstomp's bully cutscene (`s1-bul.c`, music `bullythe.mid`) and sets `&pig_story=1`.
3. **Town is closed**: Guard Renton refuses to open the gate (`s1-gg.c`), and an invisible barrier says "I'd best not venture so far from town. Too dangerous!" while `&story<5` (`s1-nopas.c`). `s1-gate.c` sets vision 1 at story 1 and 5; I infer that is the guard-present state.
4. **Ethel's duck** (`s1-h2-o.c`, `s1-oldd.c`, `findduck.c`): this is mandatory. Mother only advances when `&old_womans_duck>2` and `&pig_story==1`.
5. **Nut errand**: Mother asks for AlkTree nuts, `&story=2`. Hitting the tree drops nuts (`s1-ntree.c`); the first pickup sets `&nuttree=1` and `&story=3` (`s1-nut.c`).
6. **Lyna and Milder** (`s1-bls.c`, `s1-blove.c`): on the way back, Lyna calls Milder "an ass" and leaves; `&nuttree=2`.
7. **House fire**:
   - Outside (`s1-h1-o.c`, story 3): "What, the house, mother nooooo!!!"
   - Inside (`s1-h1-s.c`): "Mother, you can't die... never knew how much I really cared about you until now." Sets `&story=4` and Dink is walked out.
   - Outside again: Ethel, Chealse, a knight and a girl console him; the lines vary by duck state. Fade, `&story=5`.
8. **Letter**: Renton says a letter came (`&letter=1`, `s1-gg.c`). In the burnt house, `s1-ltr.c` plays Aunt Maria Kneedlewood's invitation to Terris. It sets `&letter=2`, `&story=6`, `&s2-map=1` and teleports Dink to map 439.
9. **Toll bridge** (`s1-brg.c`, `s1-brg2.c`): the toll man is present while `&story<=6`; paying 100 gold sets `&story=7`. I could not confirm from the scripts where the bridge sits geographically.

**Optional Stonebrook threads**: Martridge and the Bonca (`&wizard_see` 0 to 4), the SmileStein farm (`&farmer_quest`), the Royal Guard robbery (`&robbed`, `&safe`), and the pushable rock (`s1-roc.c`).

**Terris (story 7 to 8)**
1. **Arrival** (`s2-auntp.c`, `&s2-aunt=0`): Jack says "Who the hell are you?... Git outta my house." Maria welcomes Dink; `&s2-aunt=1`.
2. **Beating cutscene**: entering the upstairs room sets `&s2-aunt=2` (`s2-h2-s.c`). Coming back down plays Jack beating Maria (about 16 punch effects), then `&s2-aunt=3`. Killing Jack (50 HP) gives +100 exp and `&s2-aunt=4` (`s2-jack.c`).
3. **Bar** (`s2-bar.c`, `s2-man2.c`): Milder humiliates Dink in front of the old men (`&s2-milder` 0 to 2).
4. **Cave prisoner** (`s2-cave.c`, `s2-cave2.c`, `&caveguy` 0 to 6): ends with the prisoner's death and the Mordavia scroll. Also sets `&story=7`.
5. **Nadine's daughter and the cult** (`s2-nadp.c`, `s2-cult.c`, `&s2-nad` 0 to 3): rescuing Mary sets `&story=8`.
6. **Thief sting** (`&thief` 0 to 4): optional.

**Later story values visible in this slice** (`poster.c`, `king.c`, `s2-ca-g.c`):
- 9: Milder weds Lyna.
- 10: Dink saves KernSin.
- 11: Windemere famine solved.
- 12: Milder missing in the Darklands; castle guards now admit Dink.
- 13: Dink has met King Daniel.
- 14: Dink is sent to the Darklands.
- 15: Dink returns; the ending speech and credits play.
- 16: post-game.

## 2. Characters

**Stonebrook**
- **Dink Smallwood**: pig farmer's son who insists he is a warrior; attacks furniture. "Why must I attack furniture?" (`s1-h1-4.c`); "WATER MUST DIE!" (`s1-fount.c`).
- **Mother** (unnamed, unkillable): brisk and dry. "You'll get over it." in reply to "I HATE YOU!" (`s1-h1-m.c`).
- **Milder Flatstomp**: village bully, later a knight. "Are you feeding pigs right now?" / "Bawahahahah! See you around, squirt." (`s1-bul.c`).
- **Lyna**: Dink's crush. "I have a mind too, you know." (`s1-blove.c`).
- **Ethel**: old neighbour with a wall of liquor. "You must keep searching for Quackers! I loved him!"; "Kinda funny, my duck and your Mom dead." (`s1-h2-o.c`).
- **Quackers** the duck: "QUACK!!" then "Bite me" / "But fine, I'll go home..." (`s1-oldd.c`).
- **Chealse**: gossiping little girl, spawned half the time at the gate; her sister Aby lives in PortTown. "Whatever, Smallwood!!"; "Hey, watch it pig farmer!!" (`s1-lg.c`).
- **Guard Renton**: "Hardly... go tend your livestock. <chuckle>" (`s1-gg.c`).
- **Mr. SmileStein**: widowed farmer. "Those damn monsters..." (`s1-h3-of.c`). Sign: "SmileStein Farm - We grow it, you eat it." (`s1-farms.c`).
- **Libby SmileStein**: grieving daughter. "DINK!! What the hell's wrong with you??" (`s1-h3-l.c`).
- **Wizard Martridge**: tiny astral magician. "You cannot measure magic by size!"; "DON'T ANGER ME, HUMAN!" (`s1-wiz.c`). Sign: "Private property! Keep out!" (`s1-hsign.c`).
- **Bonca**: cave beast. "Who dares enter my cave?" (`s1-cavem.c`).
- **Farm monster**: "You cannot defeat us Mr. Smallwood, we are too much for you." Dies with "Damn you ... damn .. you." (`s1-fmons.c`).
- **Traveller** (`s1-wand.c`): lore-giver on goblins, PortTown pirates, SunCool pond.
- **Chance Zands** (`s1-wand2.c`): escaped goblin prisoner. "Those guy are dumb as bricks man!"
- **Cobbler/pharmacist** (`s1-boot.c`): "I've never sold one."
- **Toll man** (`s1-brg2.c`): "My kids need to eat."
- **Robbery victim and two rogue Royal Guards** (`s1-rob2.c`, `s1-vic.c`).

**Terris**
- **Aunt Maria Kneedlewood**: Dink's mother's sister, abused wife. "I feel safe with you upstairs." (`s2-auntp.c`).
- **Jack**: "I ain't sent no letter to nobody nohow." (`s2-auntp.c`).
- **Barkeep**: "Get to work you stupid wench!" (`s2-bar.c`).
- **Barmaid**: "Look with your eyes, not with your hands, honey." (`s2-wench.c`).
- **Nathan and a second old man**: tall-tale tellers. "Have you ever seen a dragon cry?"; "Is a bottle of SWINE ok? Bawahahah!" (`s2-man2.c`).
- **Thief**, the "specialist": "Let's just say I help acquire things.." (`s2-ryant.c`).
- **Cave prisoner** (unnamed): "THEN WHAT THE HELL ARE YOU DOING HERE?" (`s2-cave.c`).
- **Cast agents**: "Someone knows. He must die!" (`s2-bar.c`).
- **Old magician**: never gets Dink's name right (Maulwood, Smallwand, BallWood, Tallwood, Smallweed, Brickwood). "Are you high?" (`s2-mdoor.c`, `s2-mh-m.c`).
- **Nadine**: "They don't care. We are poor." (`s2-nadp.c`).
- **Mary**: Nadine's daughter (`s2-culg.c`).
- **Bishop Nelson**: cult leader and slayer shapeshifter. "You see, my girls are more than meets the eye." (`s2-cult.c`).
- **Cult girls Jennifer, Cindy and two unnamed**: "I would do anything for you, DDC." (`s2-cult.c`).
- **Healer** (`s2-healp.c`), **shopkeeper** (`s2-out.c`), **hunter** (`s2-wand.c`).
- **Castle guard**: "It's bigger from the inside." (`s2-ca-g.c`).
- **King Daniel**: "Ahh, the famous Dink Smallwood sense of humor I heard so much about!" (`king.c`).
- **Talking tree**: "I'm tree years old.. HAW HAW HAW!" (`s2-sec2.c`).

**Signs**
- "Condemned Mine - Do Not Enter!" (`s2-ds.c`); "Bjork Dam" (`s2-dams.c`).
- Murkwood Forest "magically sealed shut by decree of King Daniel" (`s2-signe.c`).
- Wanted poster for The Cast (`s2-want.c`).
- "House for Sale: Contact Charlie" (`s2-sale.c`).
- "Welcome to the town of Terris" (`s2-t1s.c`); "South to KernSin" (`s2-t2s.c`); "GoodHeart Castle" (`s1-sign2.c`).
- The King's News poster, issues 43 to 51 (`poster.c`).

## 3. Quests

- **Feed the pigs** (Mother): sack, pen, Milder scene. No reward; gates the story.
- **Find Quackers** (Ethel), tracked by `&old_womans_duck`:
  - 0: not accepted. Refusing ("You're pathetic. Find your own duck.") leaves it at 0, and the duck never spawns.
  - 1: accepted. The duck then appears with a 1-in-4 chance per screen (`findduck.c`).
  - 2: duck sent home. Only the "Yell at it" option works; the polite option just gets "QUACK!!"
  - 3: duck killed in the wild ("Haw haw!").
  - 4: Ethel has thanked Dink.
  - 5: duck killed inside her house after its return ("You little bastard!! Get out!!").
  - States 3 and 5 change Ethel's lines, the fire scene, Chealse's gossip and traveller rumours of "a madman... who stalks and kills the pets". At 3 Dink can confess to Chealse. No material reward.
- **AlkTree nuts** (Mother): leads to the fire. Nuts are inventory items that sell for $2 each in Terris.
- **Martridge's trial** (`s1-magic.c`, `s1-wiz.c`, `s1-mh-m.c`, `s1-cavem.c`, `s1-mh-f.c`):
  - Apparition cutscene, then visit the hidden cabin; "Tell him you're worthy" gives a red potion and `&wizard_see=2`.
  - Kill the Bonca in the west cave (20 HP, 100 exp); `&wizard_see=3`.
  - Martridge is gone; his scroll gives 200 gold, +1 magic and Fireball; `&wizard_see=4`.
- **SmileStein farm** (`s1-h3-of.c`):
  - Offering help sets `&farmer_quest=1`; the alternative choice only reveals he plans to hire a hunter.
  - Killing the talking monster sets `&farmer_quest=2` and gives +40 exp.
  - Reward: the "Not so fast, Smallwood!" blocker (`s1-h3-5.c`) is removed, so Dink can go upstairs to Libby.
- **Libby**: the abuse-accusation dialogue only unlocks if Chealse told rumour 1 (`&gossip=1`). It ends in "comfort" or "apologize"; no reward.
- **Robbery** (`s1-rob.c`, 1-in-5 chance per visit until done): two Royal Guards extort a traveller for 5 gold. Killing a guard sets `&safe=1`; the victim then pays 1 gold and 15 exp.
- **Cave prisoner** (`&caveguy`):
  - 0 to 1: meet him.
  - 2: bar announcement; a Cast agent overhears.
  - 3: old man refuses until `&magic` is 5 or more.
  - 4: Acid Rain learned (`item-ice`).
  - 5: statue destroyed (`dam-icee.c`).
  - 6: Cast agents fireball the prisoner; he hands over the Mordavia scroll (`item-p1`).
  - The failure is scripted and cannot be avoided.
- **Mary and the cult** (`&s2-nad`):
  - 1: learn of the kidnap. 2: offer to help; the rude alternative is "your arms look pointy and stupid."
  - The backyard scene then triggers: four girls become Boncas (20 HP, defence 3), then Nelson becomes a slayer (40 HP, 200 exp).
  - Talk to Mary to escort her home; `&s2-nad=3`, `&story=8`.
  - Fail state: if Mary (20 HP) dies, `&life=0` and the game ends: "The girl has died! I HAVE FAILED!!!!"
- **Thief sting** (`&thief`): 1 asked, 2 joined, 3 lock-picking interrupted by two guards (40 HP each) who attack Dink, 4 other guards thank Dink for "helping us catch this guy". Dink lies that "Tom and Bob" are fine (`&tombob=1`). No reward.
- **Jack**: threaten him, goad him into a fight ("Eat me!"), kill him, or coerce him into beating Maria again.
- **Barkeep "Threaten"**: summons two guards to fight.

## 4. Tone, humour and sensitive content

**Humour types and verbatim examples**
1. Furniture violence: "You smell, therefore you die!!!" (`s1-h2-1.c`); "LITTLE THINGS MUST DIE!" (`s2-na2.c`); "Teaparty!" (`s2-table.c`).
2. Duck cruelty: "I WAS THE ONE WHO KILLED ETHEL'S DUCK!!!!!!!!!" (`s1-lg.c`).
3. Dead-mother gallows humour: "But, if you hadn't killed my duck, your mom might still be alive." (`s1-h1-o.c`).
4. Fourth wall: "'You've won the game, please don't take my throne too!' - King Daniel" (`poster.c`); "Nice, you win the game, then start killing guards? Get 'em!" (`s2-ca-g.c`); "Wow, this loaded game looks so familiar." (`escape.c`).
5. Deflating the hero: "Pretty good... compared to your usual." (`s1-h3-l.c`); "Pig farmer!? What a crock. At least I'm on there though." (`poster.c`).
6. Juvenile bravado: "Can I like create chicks right in front of me and stuff?" (`s1-mh-m.c`); "Forget to remove my foot from your ASS!!" (`s2-cave2.c`).
7. Absurd or pun: "Dead Dragon Carcass" worship; "Your magic is treely useless against me" (`s2-sec2.c`); a Transformers reference flagged in a code comment (`s2-cult.c`).
8. Dark one-liners: "This is for all the kids that fell down you!" (`s2-well1.c`); "Killing guards is fun!" (`s2-ca-g.c`).
9. Dry NPC replies: "And I would like to ask you to leave." (`s1-boot.c`); "Dink .. You've got problems." (`s1-h2-o.c`).

**Content to review for a modern release (exact quotes)**
- **Domestic violence, shown and player-encouraged**:
  - `s2-auntp.c`: "This will learn you to talk back to me!"; menu option "Encourage her to continue getting beaten by Jack"; "Yes, he's good at it. I hope to learn much from him."
  - `s2-auntp.c`, when Dink hits Maria: "Take your beatin' like a man, woman!"; "I hope you like it rough!"
  - `s2-auntp.c`: "You stupid whore." / "I see now I shouldn't have killed Jack. I should have joined forces with him."
  - `s2-jack.c`: option "Coerce Jack into hitting Maria again"; "My bitch wife?"; "Better lay a bit o law into her"; "Get a clue, honey. How do you think I kept my mom in line? Haw!"
- **Incest innuendo**: "What if you traded them in for one big one we could share?" / "I'm your aunt, Dink!" / "And?" (`s2-auntp.c`).
- **Child sexual-abuse insinuation**: "Is your father upset because you won't satisfy him?" (`s1-h3-l.c`); "Mr.SmileStein's bed, I shudder at what happens here." (`s1-h3-3.c`); "Libby's bed, ahh yeah." (`s1-h3-8.c`).
- **Violence against children and women**:
  - Chealse (30 HP) can be killed: "She won't be bothering people any more." (`s1-lg.c`).
  - Hitting Libby: "You know I hate to do this to you baby." (`s1-h3-l.c`).
  - Hitting Nadine: "How does it feel?!" (`s2-nadp.c`).
  - The cult's little girls are killed in monster form; "I agree, crucify the new girl!" (`s2-cult.c`).
- **Religious satire**: Bishop Nelson; "Your blood will flow like the river Jordan."; "Can I interest you in our love gift for December? Only $80!"; "Judgement day has cometh, sinner!" (`s2-cman.c`); "More goat blood?" (`s2-cult.c`).
- **Sexist or sexual lines**:
  - "How much for you?"; "I got three gold jingling in my pocket!" (`s2-wench.c`).
  - "I hear your Mom's a slut." (`s1-wand2.c`).
  - "How 'bout I plow your momma?" (`s2-man2.c`).
  - "waking up with guys you don't even know" (`s1-h2-o.c`).
  - "Hhhmph, chicks!" (`s1-blove.c`).
- **Gay-panic joke**: "How about I touch you right now?" / "Sorry, not into that. But I know this guy named Milder..." (`s2-jack.c`).
- **Drugs**: "Are you high?" (`s2-mdoor.c`); the herb boots (`s1-boot.c`).
- **Profanity**: bastard, ass, damn, hell, "Gawd dammit", "royally screwed".
- **Colonial overtone**: King Daniel "created a special place for [goblins] to live in peace" (`s2-ca-g.c`).
- No racial slurs appear in this slice.
- Not player-facing: a variable named `&bitch` in `s2-h1-s.c`.
- Dated real-world commerce: a phone number and the rtsoft.com URL in `start-3.c` and `king.c`.

## 5. Meaningful choice menus

- **Mother** (`s1-h1-m.c`): pig feeding / father / village / "Get angry for no reason" / report chores.
- **Ethel** (`s1-h2-o.c`): well-being / pet / bottles; then "Agree whole heartedly" / "Barely agree" / "Tell her where she can stick 'Quackers'".
- **Duck** (`s1-oldd.c`): "Tell the duck to go home" does nothing; "Yell at it" works.
- **Chealse** (`s1-lg.c`): flirt / gossip (four random rumours) / Milder / confess duck murder.
- **Renton** (`s1-gg.c`): ask to be let out (always refused).
- **SmileStein** (`s1-h3-of.c`): family / farm (offer help, or ask his plans) / see Libby / farm info.
- **Libby** (`s1-h3-l.c`): coax / comfort / brag; then comfort or apologise.
- **Martridge** (`s1-mh-m.c`): "Tell him you're worthy" / ask about magic.
- **Travellers** (`s1-wand.c`, `s1-wand2.c`): travels / news / AlkTree nuts (story 2 only).
- **Cobbler** (`s1-boot.c`): buy / complain; the complaint differs once the boots are owned.
- **Toll man** (`s1-brg2.c`): pay / argue.
- **Maria** (`s2-auntp.c`): nine state-gated options, including a post-game brag with a polite or rude follow-up.
- **Jack** (`s2-jack.c`): hi / thanks / rude / threaten / coerce.
- **Barkeep** (`s2-bar.c`): gossip / threaten.
- **Barmaid** (`s2-wench.c`): date (she accepts only when `&story>15`) / belittle.
- **Old men** (`s2-man2.c`): impress / convince / argue / chat.
- **Thief** (`s2-ryant.c`): hi / ask what he does / offer help.
- **Nadine** (`s2-nadp.c`): mess / offer / be rude / report / check in.
- **Cult** (`s2-cult.c`): save her / agree to sacrifice / "Use brains and stay hidden". The third is refused ("Nah, I think I'd rather shout something.") and the other two lead to the same fight.
- **Mary** (`s2-culg.c`): four identity lines, cosmetic only.
- **Castle guard** (`s2-ca-g.c`): castle history / King history / audience (reply varies with story 7 to 12+).
- **King** (`king.c`): "Complain about your taxes" / "Offer to help Milder" (sets story 14).
- **Hunter** (`s2-wand.c`): hi / tales.
- **System menus**: `escape.c` (load, restart, quit, help, gamepad remap), `dinfo.c` (death menu), `start-2.c` (load).

## 6. Shops, trainers, prices

| Item | Price | Where |
|---|---|---|
| Hyper Boots (`item-bt`) | 500 gold | Roadside booth (`s1-booth.c`, `s1-boot.c`) |
| Bridge toll | 100 gold | `s1-brg2.c` |
| Longsword (`item-sw1`) | 400 buy, 200 sell | Terris shop (`s2-out.c`) |
| Bomb (`item-bom`) | 20 | Terris shop |
| Nut | sells for 2 | Terris shop |
| Healing | 1 gold per missing HP | Terris healer (`s2-healp.c`) |
| Elixir (`item-eli`) | 25 | Terris healer |
| Beer | "Two gold" (dialogue only) | `s2-wench.c` |

- **Free heal**: the Stonebrook fountain (`s1-fount.c`).
- **Spells**: Fireball from Martridge's scroll; Acid Rain from the Terris old man (needs 5 magic); the Mordavia scroll from the dying prisoner.
- **Ending gift**: three red and three purple potions (`king.c`).
- **Containers** (`bar-*`, `box*`, `ch1-*`, `ch2-*`, `ch3-*`): hit to open. Contents by suffix:
  - `e` empty, `sh` small heart, `gh` gold heart, `h` heart.
  - `f1` food, `m` random medium drop.
  - `sp` strength potion, `dp` defence potion, `ap` and `mp` magic potions.
  - `g` and `pap` gold, `500` 500 gold, `sfb` a spell item I did not trace.

## 7. Global variables (declared in `main.c`)

- `&story`: main progress, 0 to 16 as above.
- `&old_womans_duck`: 0 to 5. `&pig_story`: 0 or 1. `&nuttree`: 0 to 2. `&letter`: 0 to 2.
- `&little_girl`: 2 means Chealse is dead.
- `&farmer_quest`: 0 to 2. `&gossip`, `&mlibby`: Libby dialogue gates.
- `&wizard_see`: 0 to 4. `&wizard_again`: apparition has played.
- `&robbed`, `&safe`: robbery. `&rock_placement`: rock pushed.
- `&s2-aunt`: 0 to 5. `&s2-milder`: 0 to 2. `&thief`: 0 to 4. `&tombob`: set but never read.
- `&caveguy`: 0 to 6. `&s2-nad`: 0 to 3. `&s2-map`: owns the map (`button6.c`).
- `&save_x`, `&save_y`, `&temphold` to `&temp6hold`: scratch values and cross-script sprite handles.
- Used only outside this slice: `&mayor`, `&gobpass`, `&bowlore`, `&snowc`, `&duckgame`, `&s4-duck`, `&s5-jop`, `&s7-boat`.
- Never used anywhere: `&town1`, `&hero`.

## 8. Unfinished, cut or buggy

**Dead scripts (not on the map and not referenced by any script)**
- `s1-eltr.c`: shareware nag. "To get passage on the boat with Death please order the full version."; "Buy me please!"; "My Mom's dead and I need a home."
- `s1-boat.c`: uses `&boat`, which `main.c` never declares.
- `s1-duck.c`: a follower duck.
- `s1-farm2.c`, `s1-slim.c`, `s2-cgirl.c`.
- `start-3.c`: the "info/order" button, commented out in `start.c`. It holds a preorder skit ("This game is only $15?") and a malformed `void click(void) }`. `start-4.c` (quit) has the same brace error but is live.

**Oddities and missing files**
- `s1-ss2.c` is on the map once and just repeats "I've come to get my meat" eight times; it looks like a test or in-joke.
- `map.dat` references scripts with no `.c` file: `s2-307s`, `s2-barp`, `s2-mh-s`, `box-e`.

**Unreachable or cut features**
- `escape.c`: a save-anywhere branch (`&result == 7`) is unreachable because the menu has six options.
- `s2-out.c`: a $400 bow purchase function (`buyb1`) exists but is not on the menu.
- `s2-stat.c`: "We pay good money for slayer claws here", but there is no such sell option.
- `s1-h3-of.c`: SmileStein says "come back and tell me", but there is no report option.
- `s1-mh-m.c`: comment "Warp the Wizard elsewhere" is unimplemented.
- `s2-t2s.c`: comment "//change this".

**Logic bugs**
- `s1-cave.c`: the roar callback condition is inverted, so it never plays (`s1-caves.c` is correct).
- `s1-h1-m.c`: the nut-request cutscene replays on every house entry while story is 2.
- `s1-wand.c` checks `&story == 6` for the fire rumour (comment: "I think story = 5 ???") while `s1-wand2.c` checks 5; a dangling `else` also misfires.
- `s1-fmons.c`: both hit branches say the same line.
- `s1-lg.c`: the told-rumour flags are local, so they reset on each screen visit.
- `s2-sec1.c`: sets `&player_map = 101` but calls `load_screen(131)`.
- `poster.c`: issue 48 is duplicated for story 12 and 13; typo "until get gets to the castle".
- `s2-cult.c`: unused label `start4`.

**Syntax errors**
- `s1-h3-3.c`: `freeeze` / `unfreeeze`.
- `s1-h3-8.c`: a wrong brace, which probably hides two of the three bed lines.
- `s2-cave.c`: `wait(200:`.
- `s2-jack.c`: `sp_target(...):`, and a mismatched quote in `'I guess I just killed your husband."`, so that line may not display.
- `s2-man2.c`: `current_sprite` without `&` on "Fight!!!".
- `s1-wand2.c`: a stray backtick in "Chance `Zands" that may be read as a colour code.
- `s2-auntp.c`: stray closing braces.

**Developer comments worth keeping as lore**
- `s2-mh-m.c`: "SETH!!! ... the guy only walks a few feet to be killed again anyway... Ooops".
- `s1-cavem.c`: "fixed Pap's error here!!!"; the Bonca deliberately targets a live duck "for fun".
- `main.c`: "Time to fight for your right to party."

**Remaster-era additions**: `show_popup` quick-tips in `s1-h1-m.c` and `s1-sack.c` and the version check in `start.c` are not 1997 content.
