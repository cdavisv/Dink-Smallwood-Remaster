# Probe route: Terris arrival (&story 7) to the final scene (&story 16)

> **Status 7 Nov 2026: the probe has played steps 1-12 (Act A, chapter 2), the roads and the Mayor's errand (Act B steps 6, 17-19 and the
> chests/heart of steps 4-5, chapter 3), a gold loop (chapter 4), the bow and the goblin gate (steps 15, 16, 20, chapter 5) and one of the
> four goblins (step 21, chapter 6); it stops at the other three goblins of SCR_680 (step 21); see section 8.**

Written 7 Nov 2026 for the automated play-through (`Dink.Gameplay.Probe.*`, `Plugins/DinkParity/Source/DinkParity/Private/Tests/DinkProbeTests.cpp`).
Everything here was read from the original scripts (`bin/dink/story/*.c` in the data repo `Dink-Smallwood-Remaster`), the original engine
(`source/dink/dink.cpp`, cited `D:n`) and the extracted map data (`tools/dinkex/out/screens/SCR_nnn.json`). Where this document and
`doc/remaster/bible/*.md` disagree, the script wins (disagreements are listed in section 7). `tools/analyse/out/*.json` was used only
for screen-to-screen hop lists (advisory). Nothing was run in Unreal; the damage and recharge numbers are computed from the original
formulas with a small Monte Carlo (section 2.5), not measured in the remaster.

Script citations are `file.c:line` (lines of `bin/dink/story/`). Placement ids are `Snnn_Pnn`. "engine px" are the original's 640x480
coordinates (20 px side bar included), the same space as `create_sprite`/`sp_x` and the probe's `Goto`.

## 0. Conventions

- A step has the shape `where / actor / do / needs / result / fight / hazards`. `fight` appears only when the step has one.
- `&result` in a script is the **source position** of the option in its `choice_start()` list, not its position among the visible
  options (options whose condition is false are hidden, the others keep their numbers: `s2-nadp.c:30-37`, `king.c:137-141`,
  `s3-chick.c:25-32`). The probe answers by option **text**, so quote it exactly as listed below.
- A menu option that the probe does not name falls back to the **last** option (`DinkProbeTests.cpp`, `FProbeCommand::Update`). Several menus
  on this route have a harmful last option or a loop (section 5, trap 1); every step that opens a menu names its answers.
- "teleport" means `dink.Goto` / the probe's `Goto(Screen, X, Y)`; "walk hops" are screen-to-screen lists (`tools/analyse` link graph,
  advisory) for anyone who wants to walk it for real.
- `D:n` = `source/dink/dink.cpp:n`. `AGENTS.md` = `DinkRemasterUE/AGENTS.md`.

### 0.1 Facts and formulas used everywhere (verified)

| Rule | Value | Source |
|---|---|---|
| Start values | strength 3, defense 0, magic 0, life/lifemax 10, level 1, exp 0 | `main.c:8-23` |
| Exp to leave level L | `100*L*L` (cap 99999); on level-up `exp -= that`, `lraise` runs | `D:235-243`, `D:5843-5870` |
| Level-up menu | title "YOU ARE NOW LEVEL &level", options "Increase Attack" / "Increase Defense" / "Increase Magic"; `&lifemax += 3` each level; **life is not refilled** | `lraise.c:15-40` |
| Dink melee damage (and monster melee on Dink) | `S/2 + rand()%((S+1)/2) + 1`, minus target defense; if the result is below 1 it becomes 1 with probability 1/2, else 0 (`hurt_thing`) | `D:15567`, `D:6650-6667` |
| Missile damage (fireball, arrow, bomb, hellfire) | `S/2 + rand()%(S/2) + 1 - defense`, clamped at 0; `S==1` is `1 - defense`; **no pity point** | `D:14363-14394` (the float branch is only for scripts that opt in; none of the base game does) |
| Scripted `hurt(sprite, n)` (dragon/Seth "harm") | `hurt_thing`: `n - defense`, pity as melee | `D:9937-9970`, `D:6650-6667` |
| Touch damage | `touch_damage - defense` with pity, then 400 ms `notouch` | `D:15629-15680`; AGENTS.md "Gameplay rules" |
| Spell recharge | every 100 ms while `&update_status==1`: `&magic_level += &magic` up to `&magic_cost`; so `ceil(cost/magic)` steps of 100 ms | `D:5935-5940`, `D:17346`; `&update_status` is set to 1 only by `s1-h1-m.c:68` and `escape.c:70`, set to 0 by `dinfo.c:4` |
| Fireball | cost 100, missile strength 10, range 10, flying | `item-fb.c:156`, `:121-125` |
| Arrow | `S_arrow = floor(power/100) * max(1, floor(&strength/5))`; with `&bowlore==1` and a hit of the lottery, `*3`; power below 100 fires nothing | `item-b1.c:13-15, 70-97`; `item-b2.c:70-97`; `item-b3.c:67-91` |
| Bow charge | `activate_bow` blocks the script; holding the attack key adds 7 power per 10 ms tick up to 500 (a full draw is about 1.2 s at 60 Hz, the first 100 power about 0.25 s); releasing runs the script on | `D:9397-9408`, `D:14564-14612` |
| Weapon bonuses (on `arm`, removed on `disarm`) | longsword +4 (`item-sw1.c:32,44`), clawsword +13 (`item-sw2.c:32,44`), massive sword +25 (`item-sw3.c:32,44`), massive bow +8 (`item-b2.c:117,124`), FlameBow +15 (`item-b3.c:111,118`); the bow `item-b1` has none; swords set `sp_range(1,40)` (sw2 `:42`, sw3 `:42`) | as cited |
| Bow lottery with `&bowlore==1` | b1: `random(3,1)==1` triples (1/3); b2: `random(2,1)==1` (1/2); b3: the `random(1,1)` result is never tested, so **every** shot is tripled | `item-b1.c:82-93`, `item-b2.c:82-90`, `item-b3.c:79-84` |
| Potions | red `rpotion` +1 strength (`rpotion.c:21`), blue `bpotion` +1 defense (`bpotion.c:13`), purple `ppotion` +1 magic (`ppotion.c:13`), all-potion `apotion` +1 magic, +1 strength, +1 defense (`apotion.c:17-19`), gold heart `gheart` +10 lifemax, no heal (`gheart.c:15`), small heart +3 life (`sheart.c:14`), full heart sets life to lifemax (`heart.c:15`) | as cited |
| Gold pickups | `mgold` random(30,5) = 5..34; `lgold` random(25,50) = 50..74; `gold200` random(150,50) = 50..199; `papgold` +200; `gold500` +500; `1gold` +1 | `mgold.c:27`, `lgold.c:26`, `gold200.c:26`, `papgold.c:14`, `gold500.c:27`, `1gold.c:13` |
| Drop tables (`emake.c`) | medium: 1/20 small heart, 1/20 full heart, 1/20 food, 17/20 `mgold`; large: 1/20 full heart, 1/20 food, 18/20 `lgold`; xlarge: 1/20 full heart, 1/20 food, 18/20 `gold200`; small: 1/3 small heart, else nothing | `emake.c:3-69, 72-130, 133-190, 194-206` |
| Respawn | a placement killed by a script that calls `editor_type(&hold, 6)` returns 5 min after the player last left its screen (7 = 3 min, 8 = 1 min; type 1 = never) | `D:6040-6140`; AGENTS.md "Respawn clock" |
| Screenlock | Dink cannot leave the screen until `screenlock(0)`; warps still work | `D:10083-10095`, `D:14053` |

### 0.2 Starting state (end of probe step 36, `Saved/Narrative/stonebrook_probe.txt`)

`&story 7`, `&s2-aunt 3`, level 2, exp 0, life 10/13, strength 4, defense 0, magic 2 (scroll +1 and the probe's one level-up "Increase Magic"),
gold 100, fists armed (the probe armed the fireball, magic slot 1), standing on SCR_036 (Maria's house). Fireball cost 100 so a charge takes
`ceil(100/2)=50` steps = 5.0 s. **Recommendation:** answer the level-up menu with "Increase Attack" from here on (section 2.4); magic only
matters for the dragons' and Seth's "harm" resist roll and for spell recharge.

## 1. The route in one page

Minimum path (every item is required by a script check; the line is in the step):

1. Terris: Nadine twice (`&s2-nad 2`), the cult in SCR_238 (kill four girls and Bishop Nelson, `screenlock`), Mary (`&story 8`).
2. KernSin: SCR_589 scene (`&story 9`, skippable), bow (1000 gold, **armed**), Christina, the Mayor, the goblin gate guard
   (`&gobpass 1`), four goblins then Mog on SCR_680, the Cast camp scene, the three knights on SCR_521, the Mayor again with the scroll
   (`&story 10`).
3. Windemere: bomb (20 gold) for the cracked rock, kill all 27 ducks in the enclosure (`&story 11`).
4. Joppa: basement scene, then protect the family from two dragons (`&story 12`).
5. Castle: guard "Request an audience with King Daniel", King "Offer to help Milder" (`&story 13`, `14`).
6. Edge of the World pit, ancients' machine to the Darklands (SCR_154), five locked rooms, Milder, Seth (`&story 15`).
7. Machine back, King (`&story 16`, credits).

Skipped optional content (none of it is read by a later script on the path unless noted): Stonebrook leftovers (SmileStein farm, Royal
Guard robbery, Boots booth `s1-boot.c`, rock `s1-roc`); **the prisoner's cave / Acid Rain / Mordavia scroll** (probe steps 38-41:
`&caveguy` only gates cosmetic reads in `s2-crock.c:3`, `s2-idol.c:3`, `s2-mdoor.c` and writes `&story = 7` which is already 7 at
`s2-cave2.c:148`); the bar's Milder scene and thief sting (`&s2-milder`, `&thief`); Terris healer/shop except as a convenience;
Goblin George (`s3-gob.c`); Windemere's other houses and shops; Joppa's axe shop and healer; the Hellfire teacher (`s6-vend.c`,
1500 gold); the massive sword / massive bow at the Edge church (`s6-st1p.c:26-39, 63-76`, 4000 / 5000 gold; **used in the Seth kit
table, 2.6 and step 53**); Koka Isle (duck arena `s8-da.c`, FlameBow 25,000 gold `s8-guy.c:47-77`) and the snow castle (`sc-*`); the
sealed "East Wilds" treasure screen SCR_352 (15 `lgold` + potions; unreachable on foot per `connectivity.json`, UNVERIFIED).

The one hard blocker is **Seth** (hp 300, defense 25): see 2.6. The cult, goblins, knights, dragons and the Darklands rooms are winnable only
by kiting / ranged play or by far higher stats than the route hands out; see 2.5.

## 2. Resource budget

### 2.1 Gold

Fixed gold on or near the path (all `type 1` placements, never respawn):

| Source | Amount | Where / placement | Script |
|---|---|---|---|
| after the toll | 100 | (start) | `s1-brg2.c:45` (-100) |
| chest `ch1-pap` | +200 | SCR_005 Terris-wilds house (door `S274_P07` on SCR_274, hops 500>468>436>404>372>340>308>276>274), `S005_P28` | `papgold.c:14` |
| chest `ch1-pap` | +200 | SCR_557 KernSin east gate, `S557_P05` (on the road 586>554>555>556>557) | `papgold.c:14` |
| chest `ch1-pap` | +200 | SCR_747 south coast, `S747_P01` (586>587>619>651>683>715>747; SCR_715 holds 11 pill bugs, see 2.7) | `papgold.c:14` |
| `1gold` x4 | +4 | SCR_537 Windemere `S537_P10-13` | `1gold.c:13` |

Drops (expected values, `emake.c`): a medium monster pays 0.85 x 19.5 = 16.6 gold, large 0.9 x 62 = 55.8, xlarge 0.9 x 124.5 = 112. On the route:
four cult girls medium (66, `s2-cbon.c:60`), three knights large (167, `s3-dorks.c:45`), Joppa dragons xlarge (224, `en-drag.c:126`), Darklands
bong large, slayers xlarge, ducks large (SCR_156 + 157 + 190 = 56 + 112 + 448 + 168 = 784 expected; `s7-bong.c:100`, `s7-slay.c:65`, `s7-duck.c:55`).
Goblins, Mog, Nelson and Jack drop nothing (`s3-gh.c`, `s3-gs.c`, `en-gmog.c`, `s2-cslay.c`, `s2-jack.c` have no `emake`).

Required spending: bow **1000** (`s3-st2p.c:45,55`), bomb **20** (`s4-st3p.c:121,134`). By the numbers for Seth, bow lore **1500**
(`s3-bowl.c:38,47`) and for the short kits the massive bow **5000** (`s6-st1p.c:63,75`). Optional: longsword 400 (`s4-st3p.c:36,49`,
`s2-out.c`), clawsword 2000 (`s4-st3p.c:157,169`), Terris healer 1 gold per missing life (`s2-healp.c`, "You are injured!  It will cost
$&amount gold to heal you.", option "Get healed"), elixir 25 (Terris) / 100 (Windemere) (`tools/dinkc/out/shops.json`).

Ledger without any grinding (expected values):

| Point | Income | Gold after |
|---|---|---|
| Arrive Terris | | 100 |
| + three `papgold` chests | +600 | 700 |
| + cult girls' drops | +66 | 766 |
| **Bow shop: needs 1000** | **shortfall about 234 (range 170-300); played: 724 at the end of chapter 3, 276 short** | |
| after the bow, knights | +167 | about 0 + 167 |
| bomb, 1gold x4 | -20, +4 | about 150 |
| Joppa dragons | +224 | about 375 |
| Darklands rooms before Seth | +784 | about 1160 |
| bow lore 1500 (before the machine) | | **shortfall about 340** |
| massive bow 5000 (kit B) | | shortfall about 4,500 more |

So the minimum path needs a **gold grind of about 250 before the bow** and about 350 more for bow lore; the Seth kits in 2.6 need far more.

### 2.2 Experience and levels (no grinding)

Exp thresholds (`100*L^2`): L2 400, L3 900, L4 1600, L5 2500, L6 3600, L7 4900, L8 6400, L9 8100, L10 10,000. Starting at level 2, exp 0, the
cumulative total needed is L3 400, L4 1300, L5 2900, L6 5400, L7 9000, L8 14,000, L9 20,400, L10 28,500.

Required-fight exp: Jack +100 (optional, `s2-jack.c:176`), four cult girls 4x20 (`s2-cbon.c:10`) + Nelson 200 (`s2-cslay.c:43`) = 280, goblins
2x`s3-gs` 150 + 2x`s3-gh` 150 (`s3-gs.c:12`, `s3-gh.c:10`) + Mog 150 (`en-gmog.c:12`) = 750, knights 3x150 (`s3-dorks.c:11`) = 450, Joppa dragons
2x400 (`en-drag.c:16`) = 800, Darklands SCR_156 bong 120 + slayer 200 (+ dragon 400 optional), SCR_157 4x200, SCR_190 3x100.
Windemere ducks give 0 (`s4-duck.c` sets no `sp_exp`). Total on the minimum path: **3700 (3800 with Jack)**.

| After | Cumulative exp | Level reached |
|---|---|---|
| Jack + cult | 380 | 2 |
| goblins + Mog | 1130 | 3 (during the goblin fight) |
| knights | 1580 | 4 |
| Joppa | 2380 | 4 |
| SCR_156 | 2700 | 4 |
| SCR_157 | 3500 | 5 |
| SCR_190 | 3800 | 5 |

Seth gives no exp at the moment of the kill (`s7-boss.c:19` sets 0; `:247` `add_exp(10000, ...)` runs in `die`, after the fight, and does not
matter for the route). The route as written therefore reaches level 5: only **three** level-up points (L3, L4, L5) arrive on the path.

### 2.3 Permanent stat pickups on or beside the path (all placements, `type 1`, once only)

| Pickup | Where | Gain | Notes |
|---|---|---|---|
| `gheart` | `S524_P04` SCR_524 (180,199), on the road Terris to KernSin (523>524>525) | lifemax +10 | no heal |
| `rpotion` x4 | `S681_P14-17` SCR_681 (332-418, 334-339) right of the goblin screen SCR_680 | strength +4 | SCR_681 is a walkable neighbour of SCR_680 (`connectivity.json`); take them **before** the bow |
| `rpotion` | `S663_P06` SCR_663 Windemere wilds | strength +1 | after story 10 |
| chest `box2-sp` | `S742_P16` SCR_742 goblin sanctuary | strength +1 | assumed to call `make.rpotion` like `ch1-sp.c:26` (the file `box2-sp.c` was not opened) |
| `apotion` | chest `ch1-ap` `S395_P03` SCR_395 Murkwood; chests `ch1-ap` `S536_P31` (179,162) and `ch3-ap` `S536_P29` (433,161) SCR_536 Windemere; sprite `S750_P02` SCR_750 south coast | +1 strength +1 defense +1 magic each (x4) | `ch1-ap.c:26`, `ch3-ap.c:26` call `make.apotion` |
| `ppotion` | `S273_P08` SCR_273, `S597_P01` SCR_597, chest `ch1-mp` `S069_P02` SCR_069 (castle rear dungeon) | magic +1 each (x3) | |
| `bpotion` | `S603_P02` SCR_603 Windemere wilds, `S070_P22` SCR_070 King's hall, barrel `bar-dp` `S156_P05` SCR_156 (287,191) | defense +1 each (x3) | |
| chest `ch1-gh` | `S101_P02` SCR_101 castle rear dungeon (8 small hearts `S101_P03-10` beside it) | lifemax +10 | |
| `gheart` | `S157_P09` SCR_157 (267,161), inside the locked slayer room | lifemax +10 | |
| `rpotion`, `apotion`, `gheart`, `bpotion` | `S166_*`, `S198_*`, `S209_*`, `S214_P02`, `S243_P01`, `S248_P03`, chests `S184_P02`, `S209_P05`, barrel `S177_P03` | various | Edge of the World plateau, behind `en-stg` golems (hp 40, defense 18, strength 35, touch 25); not used |

Totals if everything above that is on the route is collected: strength = 4 held + 4 (S681) + 1 (S663) + 1 (S742) + 4 (four apotions) = **14**;
defense = 4 (apotions) + 3 (bpotions) = **7**; magic = 2 held + 4 (apotions) + 3 (ppotions) = **9**; lifemax = 13 + 30 (three gold hearts) = **43**.
Level-ups add +3 lifemax and one point each (three on the route).

### 2.4 Stat plan used in the steps

All three route level-ups go to **Attack** (strength 14 from pickups + 3 = 17). Defense 7, magic 9, lifemax 52 at the Seth door
(plus whatever is ground out, 2.7); with the three level-ups lifemax is 43 + 9 = 52. Add +4 strength if the 400-gold longsword is armed (`item-sw1.c:44`); it costs the same as 24 pill-bug
kills' gold and is the cheapest melee upgrade.

### 2.5 What the fixed fights need (pessimistic model)

Method: a Monte Carlo (`python`, 150-300 runs per cell, the exact `hurt_thing` formula, Dink swings every 0.45 s, every enemy attacks about every
0.5-4.5 s with `random(4000,0)` waits (`s2-cbon.c:71`) and touches every 0.4 s) in **toe-to-toe** contact. This is the worst case; kiting beats
it where an enemy's reach is shorter than Dink's (the probe found 54 px works against `s1-cavem`; it is **unverified** for every enemy below).

Expected net damage per Dink hit (melee with pity, then missiles without):

| Dink S | def 0 | def 3 | def 5 | def 6 | def 8 | def 25 |
|---|---|---|---|---|---|---|
| melee 4 (fists now) | 3.5 | 0.76 | 0.5 | 0.5 | 0.5 | 0.5 |
| melee 8 | 6.5 | 3.5 | 1.6 | 1.0 | 0.5 | 0.5 |
| melee 12 | 9.5 | 6.5 | 4.5 | 3.5 | 1.8 | 0.5 |
| melee 16 | 12.5 | 9.6 | 7.4 | 6.5 | 4.5 | 0.5 |
| melee 20 | 15.5 | 12.4 | 10.5 | 9.5 | 7.5 | 0.7 |
| melee 32 | 24.4 | 21.5 | 19.5 | 18.5 | 16.5 | 2.0 |
| fireball (S 10) | 8.0 | 5.0 | 3.0 | 2.0 | 0.6 | 0.0 |
| arrow S 15 | 11.0 | 8.0 | 6.0 | 5.0 | 3.0 | 0.0 |
| arrow S 20 | 15.5 | 12.5 | 10.5 | 9.5 | 7.5 | 0.0 |
| arrow S 30 | 23.0 | 20.0 | 18.0 | 17.0 | 15.0 | 1.0 |
| arrow S 45 | 33.5 | 30.5 | 28.5 | 27.5 | 25.5 | 8.6 |

Minimum strength for an 80% win toe-to-toe, by (defense / lifemax) the character has:

| Fight | D0/L13 | D0/L22 | D3/L30 | D5/L40 | D8/L50 | D12/L70 |
|---|---|---|---|---|---|---|
| Jack (50 hp, touch 10) | 38 | 24 | 12 | 6 | 4 | 4 |
| Cult (4 girls + Nelson, all at once) | none | none | 36 | 20 | 14 | 10 |
| Goblins + Mog, one at a time | none | none | none | none | 26 | 10 |
| Knights x3 | none | none | 34 | 20 | 14 | 12 |
| Joppa dragons (touch only, 2 at once) | none | none | none | 38 | 18 | 14 |
| SCR_156 bong + slayer | none | none | 56 | 32 | 16 | 10 |
| SCR_157 four slayers | none | none | none | none | none | 32 |
| SCR_190 three ducks (touch 25) | none | none | none | none | none | 54 |

With the **natural route stats** (section 2.4: strength 8-17, defense 2-7, lifemax 23-52) the toe-to-toe win rates are 0% for the cult, goblins,
Joppa and SCR_157/190, 0-2% for the knights at strength 14-18 and 40% for SCR_156 at strength 17. So **every locked fight is a kiting or ranged
fight**, or needs the grind of 2.7. Kiting is plausible because most chasers are slow (`s2-cbon.c:7-9` speed 1 at timing 33 = 30 px/s,
`s3-camps.c` knights speed 1 timing 0 = 60 px/s) while Dink walks at `set_dink_speed(3)` (`main.c:79`), but the cast/shot animations freeze Dink
(`sp_nocontrol(1,1)`, `item-fb.c:26`; the bow blocks while drawn).

### 2.6 Seth (hp 300, defense 25, touch 30, `s7-boss.c:21-23`)

- Seth casts every `random(4000,2000)` ms (`:32`): half the time a bomb (`dam-bom2`, explosion strength 25 on Dink's position 0.8 s after the
  wind-up, `:41-75`, `dam-bom2.c:10`, dodgeable), half the time "greater harm" `hurt(Dink, 30)` (`:87`) unless `random(40,1) <= &magic` (`:76,82`).
- Melee is hopeless (net 2.0 per swing at strength 32, touch 30 per 0.4 s). Fireball and hellfire cannot be used: fireball 0.0 net; hellfire (S 40,
  `item-sfb.c:65`, cost 2000, `:91`) is 6.0 net, 50 casts x `ceil(2000/magic)` x 100 ms (magic 9: 22 s each).
- Arrows (mean seconds / arrows to kill, full draw 1.2 s + 0.4 s, every arrow hits):

| Strength (before bow bonus) | b1 (no lore) | b1 + lore | b2 + lore | b3 + lore |
|---|---|---|---|---|
| 15 | never | 170 s / 107 | 49 s / 30 | 12 s / 7 |
| 20 | never | 72 s / 45 | 33 s / 20 | 10 s / 6 |
| 25 | never | 50 s / 31 | 24 s / 15 | 8 s / 5 |
| 30 | 484 s / 303 | 34 s / 21 | 19 s / 12 | 7 s / 4 |
| 40 | 81 s / 51 | 20 s / 13 | 13 s / 8 | 6 s / 4 |

- Seth's "harm" alone costs (expected life lost, bombs and touch excluded; rows time T, cells defense/magic):

| T | D0 M2 | D0 M10 | D10 M10 | D20 M10 | D20 M20 | D28 M10 |
|---|---|---|---|---|---|---|
| 30 s | 115 | 86 | 59 | 30 | 20 | 6 |
| 60 s | 222 | 173 | 116 | 58 | 40 | 12 |
| 120 s | 443 | 345 | 230 | 114 | 75 | 23 |

**Verdict.** At the natural route stats (strength 17, defense 7, magic 9, lifemax about 52) the b1 bow with bow lore needs about 166 s, during which
Seth's harm alone removes about 330 life: **the route cannot win the Seth fight without grinding**. Two kits are realistic: **kit A** b1 + lore
with strength about 25 (51 s) and defense about 20, lifemax about 80; **kit B** massive bow (+8) + lore with strength about 22 and defense about 10 (about 22 s,
about 35 life of harm). Kit B costs 6500 gold in total and about 5 more levels (25,500 exp); kit A needs 8 more strength and 13 more defense, which is
far more exp than the cap allows. See 2.7 for the grind estimate. There is no armour in the game: defense comes only from potions and level-ups.

### 2.7 Grinding points and estimates

Respawning enemies on or near the path (all `editor_type 6` = 5 min):

| Spot | Enemies | Per full sweep | Notes |
|---|---|---|---|
| SCR_715 south coast (586>587>619>651>683>715) | 11 `en-pill2` (30 hp, speed 3, touch 8, **no melee**, exp 40, medium drop) + 1 `en-bong` (40 hp, defense 0, str 10, touch 5, exp 120, large drop) | exp 560, gold about 238 | `en-pill2.c:5-11,35`, `en-bong.c:8-22`; fast swarm, 8 touch per contact |
| SCR_457 / 488 / 522 (KernSin wilds / camp road) | 2 / 2 / 1 `en-pill2` | exp 200, gold 83 | 522 is 2 hops from SCR_586 |
| SCR_583 | 1 `en-bong` + 1 `en-boncd` | exp 150, gold about 72 | 3 hops from SCR_586 |
| SCR_648 | 1 `en-bonc` + 2 `en-pill2` | exp 110, gold about 50 | |
| SCR_157 (Darklands) | 4 `s7-slay` (100 hp, def 5, str 20, touch 10, exp 200, xlarge) | exp 800, gold about 450 | locked room; respawns 5 min after you leave; best exp/gold on the path |
| SCR_190 (Darklands) | 3 `s7-duck` (50 hp, touch 25, exp 100, large) | exp 300, gold about 170 | |

Estimates (assuming the probe can win each sweep, which 2.5 says it cannot toe-to-toe):

- **Gold before the bow:** about 250 -> **1-2 sweeps of SCR_715** (or 3 of SCR_522/457/488), 5-10 min game time each (the clear plus the 5 min
  respawn). The 200-gold chests do not respawn.
- **Bow lore (1500 total, 340 short):** 1-2 more sweeps of SCR_715 before Joppa, or 1 sweep of SCR_157 after.
- **Seth kit B (6500 gold, 25,500 exp):** about 30 sweeps of SCR_157 (each worth 450 gold and 800 exp), about 150 game minutes (37 min wall clock at
  `slomo 4`), if the probe wins the sweep with arrows; it is **not** a realistic target for an unattended run. Recommended: end the probe before step 52
  with a report ("Seth reached, needs kit B") and make steps 52-54 a separate, explicitly long test.

### 2.8 Save machines (`savebot.c`, menu "Save your game", then slot lines "&savegameinfo" x10 and "Nevermind")

SCR_037 `S037_P19` (Maria's room), SCR_588 `S588_P05` (KernSin, beside the bookstore), SCR_569 `S569_P02` (Windemere), SCR_252 `S252_P01` (Edge village,
next to the machine screen), SCR_254 `S254_P05` (Darklands, before the hole to Seth). None in Joppa or at the cult (SCR_238) or goblins (SCR_680).
The slot lines are the literal text `&savegameinfo`; answer by option index, not text (`savebot.c:30-41`). `&result < 11` saves (`:46-48`).

## 3. The steps

Numbering continues the probe's idea of a flat list but restarts at 1 for this document. Probe steps 33-41 (Terris arrival, upstairs room,
Maria beaten, arm fireball, Jack, prisoner's cave, bar, teacher, Acid Rain) are the previous run; steps 33-36 are step 1 here, step 37 is step 2
here, steps 38-41 are skipped (section 1).

### Act A. Terris and preparation (&story 7 -> 8): 12 steps

1. Baseline: Terris arrival done (probe steps 33-36)
   where: SCR_036 Maria's house (indoor), actor: screen base `s2-aunt` (`s2-aunt.c:6-8` creates Maria at (290,250) with `s2-auntp`)
   do: nothing; check the facts
   needs: `&story == 7` (`s1-brg2.c:47`), `&s2-aunt == 3` (`s2-auntp.c:129`), gold 100 (200 from `s1-mh-f.c`, minus 100 toll, `s1-brg2.c:45`)
   result: Jack (created by `s2-auntp.c:12-13` at (160,150), script `s2-jack`) is alive with 50 hp (`s2-auntp.c:29`, `s2-jack.c:9-12`), brain 16 (`s2-jack.c:18`);
   Maria's talk menu (`s2-auntp.c:202-213`) is cosmetic from here on
   hazards: Maria's door warp `S036_P18` (321,384) -> SCR_500 (255,358) triggers at map y 342+ (probe step 33 note); stairs warp `S036_P27` (547,8) -> SCR_037

2. [OPTIONAL] Kill Jack for 100 exp
   where: SCR_036, actor: Jack (no placement; created at runtime, script `s2-jack.c`)
   do: stand 130 px away, fireball along his row (probe step 37) or hit him; he is peaceful until struck
   needs: `&s2-aunt >= 3` so he has 50 hp (`s2-jack.c:9-12`); fireball armed (`dink.ArmMagic 1`)
   result: `&exp += 100` (`s2-jack.c:176`), `&s2-aunt 3 -> 4` (`s2-jack.c:177`); `die` also freezes Maria `&temp2hold` (`:167`)
   fight: `s2-jack.c`: 50 hp, defense 0 (unset), **no strength** (no melee), brain 16 until hit; `hit` (`:154-161`) says "`6Oh, NOW YOU'VE DONE IT!",
   sets touch_damage 10, speed 2, brain 9, `sp_target(1)` (`:157-160`). Net fireball damage 8.0 (10-S missile, defense 0): 7 hits at magic 2 = 7 x 5.0 s = 35 s of charge
   hazards: his touch is 10 per 400 ms (life 13 = 2 contacts); toe-to-toe needs strength 38 at defense 0 (2.5 table); `die` line 171 has mismatched quotes
   (`diagnostics.json`: the 1997 engine shows nothing or garbage for "I guess I just killed your husband."); the previous run stalled here with 150 s of
   cast-blocked waits (`item-fb.use` blocked on `wait(100)`); **nothing later reads `&s2-aunt == 4`**, so skipping is safe

3. Save in Maria's room (optional, recommended before the cult)
   where: SCR_037 (up the stairs `S036_P27`), actor: `S037_P19` `savebot.c` at (403,264)
   do: talk; menu "Save your game"; then answer the slot menu by index (lines read "&savegameinfo"); "Nevermind" is the last option
   needs: none
   result: `save_game(&result)` (`savebot.c:48`), "`%Game saved" (`:49`)
   hazards: SCR_037's `s2-h2-s.c:3-9` only fires at `&s2-aunt == 1`; the stairs back `S037_P13` (461,174) -> SCR_036 (488,92)

4. [PREP, any time after story 7] Terris-wilds cluster: 200 gold and a magic potion
   where: SCR_274 door `S274_P07` (289,270) -> SCR_005 (320,287); SCR_273 `S273_P08` (294,320). Hops 500>468>436>404>372>340>308>276>275>274>273
   actor: chest `S005_P28` `ch1-pap.c` (477,212); sprite `S273_P08` `ppotion.c`
   do: in SCR_005 hit the chest (it opens, drops `papgold`), touch the drop; in SCR_273 stand on the potion
   needs: nothing (`type 1`, vision 0)
   result: `&gold += 200` (`papgold.c:14`; chest opens via `make.papgold`, `ch1-pap.c:23`), `&magic += 1` (`ppotion.c:13`)
   hazards: SCR_005's base script `s2-h1-s.c` is only a random line; the drop must be touched before it vanishes (brain 12 shrink about 0.3 s);
   `editor_type` 4 on the chest keeps it open (`ch1-ap.c:13-21` pattern) so it never pays twice

5. [PREP] KernSin road: gold heart and a second 200-gold chest
   where: SCR_524 `S524_P04` (180,199); SCR_557 `S557_P05` (241,193). Hops 586>554>555>556>557 and 523>524>525 (road from Terris)
   actor: `gheart.c` sprite; chest `ch1-pap.c`
   do: touch the heart; hit the chest, touch the coins
   needs: none
   result: `&lifemax += 10` (`gheart.c:15`, no heal), `&gold += 200` (`papgold.c:14`)
   hazards: wandering monsters on these screens were not enumerated; the road is open ground (check `dinkex` placements before relying on it)

6. [PREP] Four strength potions in the goblin village (before the bow)
   where: SCR_681 `S681_P14-17` at (418,339) (389,334) (361,334) (332,335); hops 586>585>584>616>648>680>681 (SCR_680 holds the sleeping goblins)
   actor: `rpotion.c` sprites
   do: walk SCR_648 -> SCR_680 -> SCR_681 without touching the goblins; stand on each potion
   needs: nothing; **do not hit any goblin** (a hit turns it hostile)
   result: `&strength += 1` x4 (`rpotion.c:21`) = strength 8
   hazards: goblins on SCR_680 are brain 16 wanderers (`s3-gs.c:6`, `s3-gh.c:6`) with touch damage 8-10 (`s3-gs.c:17`, `s3-gh.c:16`); a touch still hurts while they
   are peaceful; SCR_680 is reachable from the north (`connectivity.json` link 648-680) with the gate on SCR_712 closed

7. [PREP + GRIND G1] South coast: 200-gold chest, all-potion, and the gold grind
   where: SCR_715 (11 `en-pill2` + 1 `en-bong`), SCR_747 chest `S747_P01` (332,193), SCR_750 `S750_P02` (174,200). Hops 586>587>619>651>683>715>747 and 586>587>588>589>590>622>654>686>718>750
   actor: monsters `en-pill2.c`, `en-bong.c`; chest `ch1-pap.c`; sprite `apotion.c`
   do: sweep SCR_715 (fireball/fists, kite); chest + potion in 747 / 750; repeat the sweep after 5 min away until gold reaches the bow money (step 15)
   needs: kiting capability (2.5); 5 min between sweeps
   result: per sweep exp 560, gold about 238 expected (`en-pill2.c:7,40` medium, `en-bong.c:15,100` large); +200 gold (`papgold.c:14`); +1 strength +1 defense +1 magic (`apotion.c:17-19`)
   fight: `en-pill2`: brain 9, speed 3, hp 30, touch 8, **no strength / base_attack** (`en-pill2.c:5-11`), 50% starts targeting Dink (`:17-20`), `hit` retargets (`:24-30`),
   `die` sets `editor_type 6` and calls `emake.medium` (`:31-42`). `en-bong`: hp 40, defense 0, strength 10, touch 5, speed 2, range 30, distance 50 (`en-bong.c:8-22`)
   hazards: **grind point**: expected 1-2 sweeps for the missing 250 gold (2.1); the swarm of speed-3 touch-8 bugs kills a life-13 Dink in 2 contacts;
   `en-bong.c:5` comment "can't get out of screen until this dude is DEAD" but the script never calls `screenlock` (calls.csv); respawn 5 min (`editor_type 6`)

8. [PREP] Murkwood all-potion chest
   where: SCR_395 chest `S395_P03` (339,215), `ch1-ap.c`. Hops 586>554>522>490>458>426>427>395 (an `en-pillf` lives on this screen: hp 35, touch 4, exp 50, `en-pillf.c`)
   actor: chest
   do: hit the chest, touch the potion
   needs: none
   result: `&magic += 1`, `&strength += 1`, `&defense += 1` (`apotion.c:17-19`; `ch1-ap.c:26` calls `make.apotion`)
   hazards: `en-pillf` (medium drop, 35 hp, exp 50) can be killed for exp; the other all-potion chests are in Windemere (step 29) and SCR_750 (step 7)

9. Talk to Nadine: ask why her house is a mess (&s2-nad 0 -> 1)
   where: SCR_066 (hops 500>499>498>497 then door `S497_P12` -> SCR_066 (299,387)), actor: runtime sprite from `s2-nad.c:6-8` at (290,250), script `s2-nadp.c`
   do: walk up to her and talk; menu answers in order: "Ask Nadine why her house is such a mess"
   needs: `&s2-nad == 0` (`s2-nadp.c:31`)
   result: `&s2-nad 0 -> 1` (`s2-nadp.c:74`)
   hazards: Nadine walks (brain 16, `s2-nadp.c:21`); the menu hides non-matching options but keeps indexes (`&result == 1` here); at `&s2-nad == 0` the only other option is "Leave"

10. Talk to Nadine again: offer to find Mary (&s2-nad 1 -> 2)
    where: SCR_066, actor: same
    do: talk; "Offer to find Nadine's girl" (the other visible option is "Be rude to Nadine" = result 3, which does nothing, `s2-nadp.c:96-106`)
    needs: `&s2-nad == 1` (`s2-nadp.c:32`)
    result: `&s2-nad 1 -> 2` (`s2-nadp.c:93`)
    hazards: **the cult scene only runs while `&s2-nad == 2`** (`s2-cult.c:6-18`); with any other value SCR_238 just says "What a lovely backyard." / "Ah, the memories."

11. The cult: kill four girls and Bishop Nelson (screenlock)
    where: SCR_238 (walk hops 500>468>436>404>372>340>339>338>337>336>335>303>271>239>238), actor: screen base `s2-cult.c` (spawns the girls at (265,176) (383,179) (229,278) (393,278) via `s2-cg1-4`, Nelson at (329,450) `s2-cult.c:77-91`)
    do: enter the screen; the scene runs (Dink walks to x 583, `s2-cult.c:52`); the choice menu "A girl is about to die in a cult ritual.  What do you do?": answer
    "Say something to the effect that you are going to save her" (option 1) or "Agree that Mary should be sacrificed" (option 2); **never** "Use brains and stay hidden" (option 3 loops forever, `s2-cult.c:133-143`);
    then fight; stay out of Mary's line of fire
    needs: `&s2-nad == 2` (`s2-cult.c:6`); stats per 2.5 (or kiting); save first (SCR_037)
    result: `screenlock(1)` at `s2-cult.c:187`; four girls die (+20 exp each, medium drop each), then Nelson is attached to `s2-cslay` (`s2-cbon.c:47-52`) and dies (+200 exp, `screenlock(0)` `s2-cslay.c:73`); `playsound(43)`
    fight: **girls** (`s2-cbon.c`): brain 9, speed 1, timing 33, distance 50, hp 20, defense 3, strength 8, touch 4, exp 20 (`:6-18`); `hit` re-targets Dink (`:34-42`); attack wait `random(4000,0)` (`:71-72`);
    `die` pays `emake.medium` (`:60`). **Nelson** (`s2-cslay.c:5-56`): after "Not bad.. not bad at all." he becomes brain 9, speed 1, timing 66, distance 70, range 60, hp 40, defense 5, strength 15, touch 5, exp 200, base_attack 630 (`:38-51`);
    **Mary** (`s2-cult.c:193-194` -> `s2-culg.c:4`): hp 20; if she dies `&life = 0` and "The girl has died! I HAVE FAILED!!!!" (`s2-culg.c:108-112`) so no fireball/arrow may cross her
    hazards: the fight has no heart drops except 1/20 + 1/20 + 1/20 per girl; toe-to-toe is hopeless below strength 36 at defense 3 (2.5), so kite: Nelson reach 60-70; `s2-cult.c:75` `start4` label is unused;
    `screenlock` makes `dink.Goto` away from SCR_238 illegal until the last `die`; the probe must not "fight" before `s2-cslay` finishes its `freeze(1)` scene (`s2-cslay.c:6-29`)

12. Talk to Mary: rescue complete (&story 8)
    where: SCR_238 then warp to SCR_066 (320,480), actor: Mary (runtime sprite, script `s2-culg.c`, hp 20)
    do: after Nelson dies talk to her (walk next to her); menu: any of "A friend of the land." / "A hero, in other words, your magic man." / "Your worst nightmare." / "The leader of another and more sadistic cult"; the probe default (last) is fine
    needs: **no brain-9 sprite left on the screen** (`get_sprite_with_this_brain(9, ...) == 0`, `s2-culg.c:13`); until then she only says "Help me!" etc. (`:91-98`)
    result: `&s2-nad 2 -> 3` (`s2-culg.c:78`), **`&story 7 -> 8`** (`s2-culg.c:79`); Dink is warped to SCR_066 by script (`:42-47`, `fade_down`/`fade_up`); `dink_can_walk_off_screen(1)` then `(0)` (`:37`, `:85`)
    hazards: `move(1, 2, 700, 1)` walks Dink off the bottom edge during the scene (`:38`); a plain `Goto` of the probe would skip it, so do not teleport during this talk; `&story 8` is what un-rocks KernSin (`s3-block.c:3`)

### Act B. KernSin and the goblin lands (&story 8 -> 10): 13 steps

13. Eavesdrop on two Cast knights (&story 8 -> 9, skippable)
    where: SCR_589 (walk hops 500>499>498>497>496>495>494>493>525>557>589), actor: screen base `s3-1st.c` (creates two knights at (-30,130), (-30,210))
    do: enter the screen from the west/north; the scene freezes Dink and walks him (`s3-1st.c:35-92`)
    needs: `&story == 8` at screen load (`s3-1st.c:11`)
    result: `&story 8 -> 9` (`s3-1st.c:93`)
    hazards: timed scene about 15 s (`wait` lengths 400-1000 ms, `move_stop`); if the screen is entered at story 7 or from a teleport after the check, nothing happens and story stays 8: harmless because `s3-tc.c:285` sets 10 without reading 9 (`s4-1st.c:3` uses `<= 9` for "bridge out")

14. Save in KernSin
    where: SCR_588 (hops 586>587>588), actor: `S588_P05` `savebot.c` at (259,207)
    do: as step 3
    needs: none
    result: game saved
    hazards: none

15. Buy the bow
    where: SCR_097 (door `S585_P13` on SCR_585 -> SCR_097 (299,328); hops 586>585), actor: salesman Arturous, runtime sprite from `s3-st2.c:10-18` at (300,130), script `s3-st2p.c`
    do: talk; menu "Buy a Bow and some arrows for $1000" (option 2; "Ask about Bows" is option 1)
    needs: **gold >= 1000** (`s3-st2p.c:45`); `free_items() >= 1` (`:31-43`, otherwise the menu "You are carrying too much." with option "Ok")
    result: `&gold -= 1000` (`:55`), `add_item("item-b1", 438, 8)` (`:64`)
    hazards: **gold grind point** (2.1: shortfall about 250); `goto buy` at `:123` re-enters the purchase from the talk menu (labels are file-wide); hitting him says "That hurts and all, but you could be doing much more damage with a bow!" (`:25`)

16. Arm the bow
    where: anywhere, actor: inventory (`dink.Arm item-b1`; the bow was added as the item in slot with icon frame 8)
    do: arm `item-b1` (the probe's `ArmItemSlot`)
    needs: bow owned; the goblin guard checks `compare_weapon("item-b1") == 1` (`s3-gobg.c:80-82`), i.e. the **armed** weapon
    result: `arm` loads the bow walk/idle sequences (`item-b1.c:120-155`); no strength change
    hazards: arming the fireball (magic) does not change the armed weapon; fists must be re-armed for melee; each shot needs `activate_bow` + a held key, see 0.1

17. Christina at the fountain square: tell her about the assault (&mayor 0 -> 1)
    where: SCR_586, actor: Christina, runtime sprite created at (300,130) by `s3-tc.c:312-320` (script `s3-chick.c`); only exists while `&mayor` is 0, 3 or 4 (`s3-tc.c:9-19, 291-310`)
    do: talk; "Tell her about the planned assault" (option 3, visible only at `&mayor == 0`, `s3-chick.c:28`)
    needs: `&mayor == 0`; **`&gobpass != 5` or `&mayor != 0`** (else the "** FIXING BUG.. RESETTING GOBLIN VILLAGE **" branch resets `&gobpass = 0`, `s3-chick.c:11-19`)
    result: `&mayor 0 -> 1` (`s3-chick.c:101`); she walks off and deactivates (`:102-120`)
    hazards: the other options "Say hi" / "Ask what she does" do nothing; she is `hit`-able and yells (`:171-191`)

18. Walk into the bookstore street: the girl leads you (&mayor 1 -> 2)
    where: SCR_587 (right of 586), actor: screen base `s3-st1o.c` (creates the girl at (29,320))
    do: enter SCR_587 from SCR_586; scene about 8 s
    needs: `&mayor == 1` at load (`s3-st1o.c:3`)
    result: `&mayor 1 -> 2` (`s3-st1o.c:38`)
    hazards: Dink is frozen and walked by script (`:16-30`); do not teleport out until `unfreeze` (`:40`)

19. Tell the Mayor (&mayor 2 -> 3)
    where: SCR_067 Hiram's Bookstore (door `S587_P12` (275,134) on SCR_587 -> SCR_067 (323,321)), actor: Mayor, runtime sprite at (400,280) from `s3-st1.c:25-33` (**only created when `&mayor` is 2 or 4**, `:18`, `:35`), script `s3-mayor.c`
    do: talk; menu "Tell him about the planned assault" (option 2; "Say hi" = 1, "Leave" = 3)
    needs: `&mayor == 2` (`s3-mayor.c:12`)
    result: `&mayor 2 -> 3` (`s3-mayor.c:64`)
    hazards: at `&mayor == 3` the Mayor is **not** in the shop (nobody to talk to), and "Show him the proof" would only say "No you didn't you liar!" (`:89-98`)

20. The goblin gate guard (&gobpass 0 -> 1)
    where: SCR_712 (hops 586>585>584>616>648>680>712; SCR_712 is the south entrance of SCR_680), actor: `S712_P17` `s3-gobg.c` at (294,342); screen base `s3-gobs.c`
    do: **with the bow armed** talk; menu "Ask the Goblin guard to let you in" (option 1, visible while `&gobpass == 0`); never "Incite an 'incident'" (option 2, `:115-127`)
    needs: bow armed (`compare_weapon("item-b1") == 1`, `s3-gobg.c:80-82`) **and `&mayor == 3`** (`:84`: "hmm.. are yoo joon?? coom beck lader! too erly" otherwise)
    result: `&gobpass 0 -> 1` (`:98`), gate sprite `sp(3)` removed (`:100-103`), `playsound(43)`; re-opened on every later load by `s3-gobs.c:3-14`
    fight (only if provoked): guard hp 80, defense 6, strength 25, touch 10, exp 150 (`s3-gobg.c:11-16`), `hit` -> brain 9 + touch 10 (`:30-39`); avoid
    hazards: the gate only needs the armed bow for the check; after that unarm freely

21. Kill the four goblins, one at a time (Mog is spawned by the last)
    where: SCR_680 goblin sanctuary: `S680_P11` `s3-gs` (230,353), `S680_P12` `s3-gs` (410,262), `S680_P13` `s3-gh` (488,331), `S680_P14` `s3-gh` (357,364)
    actor: goblins (brain 16 wanderers until hit)
    do: pull and kill each separately (each `hit` makes only that goblin hostile, `s3-gs.c:32-40`, `s3-gh.c:32-40`); the last death starts Mog
    needs: `&gobpass == 1` (`s3-gh.c:62`, `s3-gs.c:63`); bow/fireball; stats per 2.5
    result: +150 exp each (`s3-gs.c:12`, `s3-gh.c:10`) = 600 exp (L3 at 400); `editor_type 6` on each (`:58-60`, `:59-61`); when no brain-9 **and** no brain-16 sprite remains on the screen: `spawn("s3-mog")` (`s3-gs.c:71`, `s3-gh.c:70`)
    fight: `s3-gs` x2: hp 60, defense 2, strength 20, touch 8, distance 50, range 35, timing 0 (`s3-gs.c:6-18`); `s3-gh` x2: hp 40, defense 1, strength 15, touch 10, distance 50, timing 66 (`s3-gh.c:6-17`);
    arrows/fireball net damage vs defense 1-2 is high (arrow S 15: 11.0 / 8.0 at def 0 / 3), so ranged kills each in 4-8 shots
    hazards: killing order is free but **both** `s3-gh` and `s3-gs` must die, and nothing else brain 9/16 may linger on SCR_680 (e.g. a wandering `en-bonc` from SCR_648 does not come in); touch damage 8-10 hits while goblins are still peaceful

22. Mog (screenlock)
    where: SCR_680 at (317,301), actor: runtime sprite created by `s3-mog.c:10-13` with script `en-gmog.c`
    do: the scene runs (dialogue); then fight until he dies
    needs: step 21 done; save first (SCR_588)
    result: `screenlock(1)` (`s3-mog.c:30`); on death `screenlock(0)` (`en-gmog.c:47`), "`4Please..." and "I will tell you where the secret Cast camp is..." (`:58-60`), `fade_down` (`:62`), **`&gobpass 1 -> 5`** (`:64`), warp to SCR_489 (226,386) (`:68-75`), +150 exp
    fight: `en-gmog.c`: hp 50, defense 4, strength 20, touch 8, range 45, distance 50, speed 1, timing 0, base_attack 770 (`:6-18`); `hit` -> brain 9 + target (`:34-41`); attack wait `random(4000,0)` (`:81`)
    hazards: `die` runs `fade_down` + `wait(2000)` + `script_attach(1000)` + `kill_this_task` (`:62-75`): a cutscene that must not be interrupted; Mog's strength 20 is 8-15 net per bite at defense 0-3

23. The Cast camp: sneak scene, walk off the bottom of the screen
    where: SCR_489 (arrive at (226,386)) then SCR_521 (neighbour below), actor: screen base `s3-camp.c`
    do: nothing; the scene is scripted (Dink frozen, `s3-camp.c:17-67`), ends with `move(1, 2, 410, 1)` + `fade_down()`; the next screen's base `s3-camps.c` calls `fade_up()` (`:57`)
    needs: `&mayor == 3` and `&gobpass >= 5` (`s3-camp.c:3-6`, `s3-camps.c:3-9`)
    result: `&vision = 1` on SCR_489 (`s3-camp.c:19`); Dink arrives on SCR_521
    hazards: **scripted `move` carries Dink over the screen edge** (SCR_489 -> SCR_521, `D:14049` crossing code must run for a scripted mover); a `Goto` during the scene would orphan the `fade_down`; if the remake fails to cross, the screen stays black

24. The ambush: three Cast knights (screenlock)
    where: SCR_521, actor: runtime knights from `s3-camps.c:16-50` at (490,-30) (310,-30) (210,470), script `s3-dorks.c`
    do: fight after the dialogue; the leader exits (`:93-94`)
    needs: `&mayor == 3` and `&gobpass >= 5`; save beforehand if possible (SCR_588 is the nearest machine)
    result: `screenlock(1)` (`s3-camps.c:92`), **`&mayor 3 -> 4`** at the start of the fight (`:122`), +150 exp each, `emake.large` each (`s3-dorks.c:45`), `screenlock(0)` + `playsound(43)` when the last brain-9 dies (`:36-41`)
    fight: effective stats (`s3-dorks.c:6-11` run when `sp_script` attaches, `D:8143-8175`, and **override** `s3-camps.c:99-107`; hp is set afterwards, `:111-113`): hp 40, defense 6, strength 12, touch 5, exp 150, distance 62, range 50, base_attack 740, target Dink; `hit` re-targets (`s3-dorks.c:26-31`)
    hazards: bible 02 says 40 hp / no more; the script's own defense 8/strength 10 lines are dead (overridden), so the real values are defense 6 / strength 12; fireball net 2.0, arrow S 15 net 5.0 vs defense 6; toe-to-toe needs strength 34 at defense 3 (2.5)

25. Mayor again: show the scroll (&mayor 4 -> 5), the parade cutscene (&story 10)
    where: SCR_067 (Mayor present again at `&mayor == 4`, `s3-st1.c:35-47`), then warp to SCR_586 (266,80), actor: Mayor, script `s3-mayor.c`; the cutscene is `s3-tc.c`
    do: talk; menu "Show him the scroll with the plans" (option 2; "Say hello" = 1); watch the parade
    needs: `&mayor == 4` (`s3-mayor.c:102`)
    result: `&mayor 4 -> 5` (`s3-mayor.c:134`), warp to SCR_586 (`:140-147`); `s3-tc.c` runs (`:19-289`): **`&story 9 -> 10`** (`:285`), **`&mayor 5 -> 6`** (`:286`), Dink unfrozen
    hazards: the cutscene is about 40 s of `wait`/`move_stop` and 40+ preloads; Christina is not created again (`s3-tc.c:291-310` makes the "loser" at `&mayor == 6`, whose talk sets 7, `s3-loser.c:22`, cosmetic)

### Act C. Windemere (&story 10 -> 11): 7 steps

26. Walk to Windemere
    where: SCR_533 bridge screen (hops 586>554>522>523>524>525>526>527>528>529>530>531>532>533>534>535>536), actor: screen base `s4-1st.c`
    do: walk/teleport to SCR_536
    needs: `&story >= 10` (`s4-1st.c:3-9`: vision 1 "bridge out" at 9 or less)
    result: Windemere reachable; SCR_536 is the duck enclosure (base `s4-ducks.c`)
    hazards: the east side of KernSin (SCR_590+) opens at story 8 (`s3-block.c:3`); Windemere's houses are locked/hostile (`s4-mdoor.c`, `s4-h1p.c` fires at Dink)

27. Buy the bomb at Blistering Pete's (and optionally a sword)
    where: SCR_196 (hops 536>537>538 then door `S538_P21` (262,333) -> SCR_196 (297,339)), actor: Pete, runtime sprite (234,168)/(401,215) from `s4-st3.c:12-25`, script `s4-st3p.c`
    do: talk; menu (the first option is "Ask about the store" or "Ask about Pete"): "See what's for sale"; then "Bomb - $20"; optional "Longsword - $400" or "Clawsword - $2000"
    needs: gold >= 20 (`s4-st3p.c:121-134`); `free_items() >= 1` (`:105`)
    result: `&gold -= 20`, `add_item("item-bom", 438, 3)` (`:134-135`); longsword `-400` / `item-sw1` (`:36,49-50`); clawsword `-2000` / `item-sw2` (`:157,169-170`)
    hazards: the script ends after a purchase (`goto mainloop` has no label, `diagnostics.json`), so talk again for a second item; line 224 has a stray "f"; the sword is worth +4 (`item-sw1.c:44`) or +13 (`item-sw2.c:44`) strength only while **armed**, and Joppa's dragons need strength 20+ (2.5) so the 400-gold longsword is the cheapest way over that line

28. Save in Windemere and heal if needed
    where: SCR_569 `S569_P02` (370,212) (hops 536>537>569); healer SCR_195 `S195_P19` (door `S506_P20`, hops 536>504>505>506)
    do: save as step 3; healer: talk, "Get healed" (price = missing life, `s4-healp.c:115-143`) or "Buy a bottle of elixer for $100"
    needs: gold for healing
    result: game saved / life = lifemax
    hazards: the elixir price is 100 here and 25 in Terris (`shops.json`)

29. Two all-potion chests in the enclosure
    where: SCR_536 `S536_P31` ch1-ap (179,162) and `S536_P29` ch3-ap (433,161) (vision 0: always present)
    actor: chests
    do: hit each chest, touch the potion that drops
    needs: none
    result: two `apotion`: `&magic += 2`, `&strength += 2`, `&defense += 2` (`apotion.c:17-19`; `ch1-ap.c:26`, `ch3-ap.c:26`)
    hazards: the enclosure's 27 ducks (brain 3) are in vision 1 and are harmless (touch 0); chests are `type 1` placements, open once (`editor_type 4`)

30. Bomb the cracked rock (&s4-duck 0 -> 1)
    where: SCR_536 rock `S536_P15` `s4-rock.c` at (413,63) (vision 1)
    actor: the bomb (`item-bom.c`): arm it, then press the attack key next to the rock
    do: `dink.Arm item-bom`; stand within 30 px of the rock; attack key; **walk 60+ px away before the 3.0 s fuse ends**
    needs: bomb owned; `&s4-duck == 0`
    result: `item-bom.c:6-8` `spawn("dam-bom")` then `kill_cur_item()` (the bomb leaves the inventory); `dam-bom.c` drops a bomb sprite at Dink's position, fuse = 5x500 + 100 + 100 + 50 + 50 + 12x20 = 3040 ms, then explosion brain 17, range 30, strength 8, script `dam-bomn` (`dam-bom.c:100-105`); the rock's `hit` sees `compare_sprite_script(&missle_source, "dam-bomn")` (`s4-rock.c:3`) -> **`&s4-duck 0 -> 1`** (`:24`), rock and cracks removed (`:10-19`)
    hazards: the explosion (strength 8) may hurt Dink (net 5-8 minus defense) - UNVERIFIED whether the engine spares the thrower; one bomb is enough only if it lands in range: buy two if unsure; the rock must be the **hit** target: `&missle_source` has to be the explosion sprite

31. Kill all 27 ducks (&s4-duck 1 -> 2, &story 11)
    where: SCR_536 enclosure, ducks `S536_P03-P41` (27 placements, brain 3, script `s4-duck.c`, hp 5)
    actor: ducks (headless body keeps running)
    do: hit each duck twice (first hit: `die`, head off; second: `duckdie`); fists/sword/bow; walk the whole enclosure
    needs: `&s4-duck == 1` (the enclosure is open)
    result: each `duckdie` drops `make.foodduck` (food sprites, `s4-duck.c:10-22`); when `get_sprite_with_this_brain(3, ...) == 0` (`:17`) `spawn("s4-end")` -> **`&s4-duck = 2`, `&story = 11`** (`s4-end.c:6-7`), the cutscene (Kelly, the guard) about 25 s (`:35-117`)
    hazards: the last duck's death starts the cutscene: do not teleport during it; headless ducks respawn only per `editor_type`, none set; food drops are +3 life (`sfood.c:12`) and the scene has 0 exp (`s4-duck.c` sets none)

32. [OPTIONAL PICKUPS] Windemere wilds and the sanctuary village
    where: SCR_663 `S663_P06` rpotion (352,77); SCR_603 `S603_P02` bpotion (53,300); SCR_742 `S742_P16` chest `box2-sp` (460,153) (hops 586>585>584>583>582>614>646>678>710>742 for 742)
    do: touch / hit each
    needs: none (663 and 603 are in the marshes south-east of Windemere, 603 via 537>538>539>571>603)
    result: +1 strength (`rpotion.c:21`), +1 defense (`bpotion.c:13`), +1 strength (`box2-sp.c:29` -> `make.spotion` = `rpotion`, `make.c:41-47`)
    hazards: SCR_663 also has 3 `1gold` + 1 `sgold` (trivial gold); the screens have `en-slay` (100 hp, defense 5, strength 20, touch 10, exp 200, `en-slay.c`) wandering: avoid

### Act D. Joppa Isle (&story 11 -> 12): 5 steps

33. Walk to Joppa and arrive in town (&s5-jop 0 -> 1)
    where: door `S537_P24` (410,256) on SCR_537 -> SCR_163 (321,301); stairs `S163_P27` (179,163) -> SCR_259 (554,197); 259>258>257; exit `S257_P01` -> SCR_483 (346,150); 483>451>419
    actor: SCR_163 base `s4-h2.c`; SCR_419 base `s5-jops.c`
    do: walk the tunnel; on SCR_419 wait for the line
    needs: **`&story > 10`** so the stairs exist (`s4-h2.c:3-9`: vision 2; at 1 the stairs sprite `S163_P27` is hidden and `s4-not.c` blocks)
    result: `&s5-jop 0 -> 1`, "Weird.  This town looks deserted." (`s5-jops.c:3-8`)
    hazards: the `S163_P27` stairs have vision 2: `dink.Goto` into SCR_163 must happen after `&story >= 11`; SCR_259/258/257 are a cave corridor

34. The basement: the hiding parents (&s5-jop 1 -> 2)
    where: door `S419_P02` (425,234) on SCR_419 -> SCR_228 (320,287); stairs `S228_P23` (129,173) -> SCR_229 (466,138); SCR_229 base `s5-base.c`
    actor: father `s5-guy.c` (330,290), mother `s5-mom` (115,160), created by `s5-base.c:5-11`
    do: walk in; the scene plays (about 12 s)
    needs: `&s5-jop == 1` at load (`s5-base.c:3`, `s5-guy.c:17`)
    result: `&s5-jop 1 -> 2` (`s5-guy.c:58`); both parents leave
    hazards: Dink is frozen (`s5-guy.c:21`); the barrels `bar-e`/`bar-sh` in SCR_229 are free hearts

35. Back up: the family and the two dragons arrive
    where: SCR_228 via stairs `S229_P01` (534,52) -> SCR_228 (184,135); door/exit `S228_P20` (313,388) -> SCR_419 (422,264); SCR_419 base `s5-jops.c`
    actor: `s5-fguy` father (560,330), `s5-fmom` (400,310), `s5-fd` daughter Gwen (40,320) created by `s5-jops.c:10-23`
    do: arrive on SCR_419; the scene plays (about 15 s); then the fight begins
    needs: `&s5-jop == 2` (`s5-jops.c:10`); fireball/bow/sword ready; **save first (none in Joppa: use SCR_569 or SCR_037)**
    result: two dragons created at (300,480) and (670,300) and assigned `en-drag` (`s5-fguy.c:48-89`); `screenlock(1)` (`en-drag.c:11`); `playmidi("1009")`
    hazards: the whole family must **survive** (see 36)

36. Kill both dragons while the family lives
    where: SCR_419, actor: `en-drag.c` x2 (runtime sprites)
    do: kill both fast; heal not available
    needs: strength 20+ melee, or arrows with strength 30+ (2.5); each dragon takes damage through defense 8
    result: +400 exp each (`en-drag.c:16`), `emake.xlarge` each (`:126`), `editor_type 6` (`:121`); when no brain-10 sprite is left and `&life > 0`: `spawn("s5-end")` (`:110-116`)
    fight: `en-drag.c`: brain 10, timing 66, speed 1, hp 80, defense 8, touch 10, callback `target` every 500-2000 ms (`:12-29`); `target` picks Dink with prob 1/9, else a random brain-16 sprite (the family) (`:36-52`); `attack` casts "harm" `hurt(target, 20)` every `random(5000,3000)` ms (`:67,76-81`), against Dink only when `random(40,1) > &magic` (`:70-76`; magic 9 resists 22%), against NPCs always (`:73-74`); `hit` re-targets the attacker (`:99-104`)
    family: father hp 100 (`s5-fguy.c:20`), mother 50 (`s5-fmom.c:8`), Gwen 50 (`s5-fd.c:8`); if any dies `&life = 0` (`s5-fguy.c:95-103`, `s5-fmom.c:21-29`, `s5-fd.c:24-32`)
    hazards: **the real constraint is time**: my Monte Carlo of the dragons' attack timing gives P(family survives) = 94% if both dragons are dead within 5 s and 10 s, 76% at 8 s / 16 s, 59% at 10 s / 20 s, 40% at 12 s / 24 s, 18% at 15 s / 30 s, 0% beyond 25 s / 50 s; that needs about 8 net damage per second on 160 hp of defense-8 flesh: melee strength 20+ (15 net per hit at S 24 = 23 dps), not fireballs (0.6 net) or b1 arrows below strength 25 (7.5 net per 1.6 s); dragon touch 10 minus defense 7 = 3 per 400 ms

37. Joppa epilogue (&story 12)
    where: SCR_419, actor: father `s5-fguy.c`, script `s5-end.c`
    do: watch; menu "Pshaw, twasn't nuthin!" or "I saved all of you, actually." (either)
    needs: both dragons dead and `&life > 0` (`en-drag.c:113`)
    result: `screenlock(0)` (`s5-end.c:9`), **`&story 11 -> 12`**, **`&s5-jop = 4`** (`:36-37`), the door `sp(2)` opened (`:32-33`); +1 healer on SCR_226 (`s5-heals.c:5`: vision 2 at story 12)
    hazards: `s5-fguy.c:6` calls the nonexistent `sp_prop` (does nothing in the engine); heart/gold drops of the dragons spawn at their death spots (pick up quickly)

### Act E. Bow lore, the castle, the Edge of the World (&story 12 -> 14): 8 steps

38. [BY THE NUMBERS FOR SETH] Bow lore: burn the secret tree, learn it for 1500 gold
    where: SCR_710 tree `S710_P14` `s3-sec1.c` (348,311) (hops 586>585>584>583>582>614>646>678>710; SCR_710's south neighbour is SCR_742), then SCR_227 (indoor) `S227_P02` `s3-bowl.c` (326,209)
    actor: the tree, then the old man
    do: arm the fireball, stand in line with the tree, cast; when it burns (`s3-sec1.c:9-27`) step onto the stump (`touch`, `:31-45`, warp to SCR_227 (515,383)); in SCR_227 talk; menu "Learn bow lore" (option 1 while `&bowlore == 0`)
    needs: a charged fireball (`dam-fire.c` runs `s3-sec1`'s `die` through `is_script_attached` / `run_script_by_number`, `dam-fire.c:35-39`, calls.csv) hitting a sprite with seq 32 frame 1; `&gold >= 1500` (`s3-bowl.c:38`); `&bowlore == 0` (`:32`)
    result: `&bowlore 0 -> 1` (`s3-bowl.c:46`), `&gold -= 1500` (`:47`), "`4* YOU LEARN BOW LORE *"; from now b1 arrows triple 1 time in 3 (`item-b1.c:82-93`)
    hazards: **gold grind point** (2.1: about 340 short at this stage); the fireball must hit the tree sprite itself (not just its shadow); `dam-fire` pre-checks `sp_pseq(&missile_target) == 32`; the stump touch is `touch_damage -1` (`s3-sec1.c:24`); the hut is also joined to the Joppa tunnel (SCR_259 below it)

39. The castle guard: ask for an audience
    where: SCR_402 (hops 500>468>436>404>403>402), actor: `S402_P05` `s2-ca-g.c` (321,219) or `S402_P03` (134,324); base script `s2-ca-o.c`
    do: talk; menu "Request an audience with King Daniel" (option 3; options 1, 2 are history lines, 4 "Leave")
    needs: `&story > 11` (`s2-ca-g.c:144-150`); at 11 or below he says no (`:84-140`)
    result: "`2Hello, Smallwood.  Of course you may see the King!" / "GUARD, OPEN THE GATE!" then `enter()` (`:172-187`): gate sprite `sp(4)` seq 68, `wait(1000)`, `fade_down`, `&player_map = 102`, Dink to (314,349), `fade_up`
    hazards: guards have hp 100, strength 50 (`:8-9`) and attack (`:6-7`); **never hit them**: `hit` (`:21-34`) makes them chase at speed 3; the castle has no save machine

40. The King: help Milder (&story 12 -> 13 -> 14)
    where: SCR_102 (arrival) then north to SCR_070 hall, actor: `S070_P03` `king.c` (333,192); free `bpotion` `S070_P22` (66,214) in the same hall
    do: walk 102 -> 070; talk; the first talk at story 12 says the greeting and sets 13 (`king.c:124-135`); then the menu: choose "Offer to help Milder" (option 2; "Complain about your taxes" = 1; "Leave" = 3)
    needs: `&story == 12` (or 13 when the first talk was interrupted); menu options show only at `&story == 13` (`:137-141`)
    result: **`&story 12 -> 13`** (`king.c:134`) then **`&story 13 -> 14`** (`:189`); take the `bpotion`: `&defense += 1`
    hazards: if the probe picks "Leave" the first time, talk again (story stays 13, the menu returns); `s6-holes.c:3` needs `&story > 13`, so 14 is required before the Edge; do not hit the King (`:200-207` only jokes)

41. The castle's rear dungeon: magic potion, gold-heart chest, hearts
    where: SCR_070 north 069 > 101: `S069_P02` chest `ch1-mp` (323,203), `S101_P02` chest `ch1-gh` (320,202), eight `S101_P03-10` `sheart` sprites; exit `S101_P01` (519,409) -> SCR_307 (458,270)
    actor: chests and sprites
    do: hit both chests, touch the potion/heart drops and the small hearts
    needs: none (`type 1`, vision 0)
    result: `&magic += 1` (`ch1-mp.c:25` -> `make.mpotion` -> `ppotion.c:13`), `&lifemax += 10` (`ch1-gh.c:25` -> `gheart.c:15`), +3 life per `sheart` (`sheart.c:14`)
    hazards: gold hearts do not heal; use the small hearts for life; there is no monster on these two screens

42. Edge of the World entrance: the guards and the pit appear at `&story > 13`
    where: SCR_243 (hops 307>275>243), actor: screen base `s6-holes.c`; guards `S243_P12` `s6-g1` (397,323) and `S243_P11` `s6-g2` (545,325); pit `S243_P13` (472,303)
    do: walk in
    needs: `&story > 13` so `&vision = 1` (`s6-holes.c:3-6`)
    result: the vision-1 placements (guards, pit) exist; `bpotion` `S243_P01` also sits here
    hazards: the guards (`s6-g1.c`, `s6-g2.c`) are talk-only; the pit is **not** drawn at story 13 or less

43. Touch the pit
    where: SCR_243 `S243_P13` `s6-hole.c` (472,303), actor: the pit
    do: stand on it (touch -1 script, `s6-hole.c:4`)
    needs: pit present (step 42)
    result: `touch` (`:9-30`): Dink frozen at (472,330), fall animation seq 452, `wait(2000)`, `fade_down`, `&player_map = 182`, Dink to (401,283), `fade_up`, `kill_this_task`
    hazards: a timed scene (2 s + fades); the plateau SCR_182 holds an `en-stg` golem `S182_P13` (213,301) (hp 40, **defense 18, strength 35, touch 25**, exp 400, `en-stg.c:6-18`) and SCR_183 another (`S183_P12`, 332,178); the next screens are 183 > 184 > 185 > 186 > 187 > 188 > 220 > 252 > 253

44. Skip the golems: teleport to the machine's village and save
    where: SCR_252 (savebot `S252_P01` (253,175)), then SCR_253, actor: save machine
    do: `dink.Goto 252`, save as step 3, walk right to SCR_253
    needs: the pit step done so the plateau is "visited" (nothing checks it)
    result: game saved
    hazards: this skips five screens of golems with touch 25 (a life-52 Dink survives two contacts at defense 7); the alternative walk 243>244>...>253 passes `en-stg` on SCR_245 (2) and SCR_246 (1) (`dinkex` placements)

45. The ancients' machine to the Darklands
    where: SCR_253 `S253_P06` `s6-warp.c` (263,353) (nohit 1), actor: the machine
    do: talk; menu "Press the red button" (option 1; "Leave" = 2)
    needs: none
    result: spinner `sp(4)` speeds up over about 6 s (`s6-warp.c:13-38`), `playsound(21)`, `sp_nodraw(1,1)`, `fade_down`, `&player_map = 154`, Dink to (329,279), `load_screen(154)`, `freeze(1)`, `fade_up`, `wait(1000)`, `unfreeze` (`:40-56`)
    hazards: about 7.5 s of `wait`s with Dink frozen and invisible; do not `Goto` during it; the spinner is editor sprite number 4 (`sp(4)`)

### Act F. The Darklands (&story 14 -> 15): 9 steps

All Darklands screens have `thorn` sprites (touch 15, hard, `thorn.c:3-4`; 154: nine of them, 155: four, 156: three, 157: three, 158: four, 190: four, 222: two, 254: two) that hurt for 15 minus defense per 400 ms on contact.

46. Arrive and walk east
    where: SCR_154 (arrival (329,279)) > SCR_155, actor: none (machine `S154_P23` (225,279) is the way back)
    do: walk right, around the thorns
    needs: step 45
    result: none
    hazards: thorns at (431,126) (238,49) (519,122) (122,215) (519,223) (265,313) (404,308) (468,309) (230,310) on 154 and (555,173) (150,101) (307,351) (507,93) on 155

47. SCR_156: bong, slayer (and a dragon), barrel potion (screenlock)
    where: SCR_156: `S156_P06` `s7-bong` (337,100), `S156_P07` `s7-slay` (206,152), `S156_P08` `s7-drag` (316,228), barrel `S156_P05` `bar-dp` (287,191)
    actor: the three monsters, the barrel
    do: enter; kill the bong and the slayer (the dragon is optional); hit the barrel
    needs: stats per 2.5; save first (SCR_252, SCR_254 is later)
    result: `screenlock(1)` on arrival (`s7-bong.c:7`, `s7-slay.c:6`); bong +120 exp + `emake.large` (`s7-bong.c:16,100`), slayer +200 exp + `emake.xlarge` (`s7-slay.c:13,65`); the lock releases when no **brain 9** sprite is left (`s7-bong.c:83-87`, `s7-slay.c:45-49`); the barrel gives `&defense += 1` (`bar-dp.c:30` -> `make.dpotion` -> `bpotion.c:13`)
    fight: **bong** speed 2, timing 0, distance 50, range 30, hp 40, defense 0, strength 10, touch 5 (`s7-bong.c:9-23`); **slayer** speed 1, timing 0, distance 60, range 45, hp 100, defense 5, strength 20, touch 10 (`s7-slay.c:6-20`); **dragon** `s7-drag.c`: brain 10, hp 80, defense 8, touch 10, exp 400, harm `hurt(target, 30)` with a magic resist roll (`:11-20, 58-96, 106-116`), targets Dink with prob 1/2 else a brain-9 monster (`:35-52`)
    hazards: the dragon (brain 10) does **not** count for the unlock, so you can leave it alive, but it still casts "greater harm" 30 at you every 3-8 s while you are on the screen; toe-to-toe vs bong + slayer needs strength 32 at defense 5 / lifemax 40 (2.5); respawn 5 min after leaving

48. SCR_157: four slayers and a gold heart (screenlock)
    where: SCR_157: `S157_P05-08` `s7-slay` at (253,113) (187,186) (349,152) (286,213); gold heart `S157_P09` (267,161)
    actor: the slayers
    do: kill all four (they all lock the screen); touch the heart afterwards
    needs: stats per 2.5; this is the hardest required room (toe-to-toe needs strength 32 at defense 12 / lifemax 70)
    result: +200 exp each (800), `emake.xlarge` each; the lock releases with the last brain-9 death (`s7-slay.c:45-49`); `&lifemax += 10` (`gheart.c:15`)
    fight: as step 47 slayer (hp 100, defense 5, strength 20 (8-15 net per bite at defense 0-7), touch 10, range 45)
    hazards: four at once; respawn 5 min; the best grind spot (2.7); `dink.Goto` is not possible while locked

49. SCR_158 > SCR_190: three duck-bugs and a full heart (screenlock)
    where: SCR_190: `S190_P11-13` `s7-duck` at (338,226) (238,213) (339,142); full heart `S190_P10` `heart.c` (260,120)
    actor: the `s7-duck` monsters
    do: walk through SCR_158, kill the three, touch the heart afterwards
    needs: none else
    result: +100 exp each, `emake.large` each, lock releases when no brain 9 remains (`s7-duck.c:36-40`); the heart sets `&life = &lifemax` (`heart.c:15`)
    fight: `s7-duck.c:5-13`: speed 1, timing 10, hp 50, touch 25, **no strength, no defense**; after death the body turns brain 5 (`:58`) and shows up as a corpse
    hazards: touch 25 minus defense 7 = 18 per 400 ms: a 52-life Dink dies in 3 contacts; melee is out (needs strength 54 at defense 12, 2.5), shoot with the bow (arrow S 15 net 11 vs defense 0: 5 arrows each) from range

50. SCR_222 > SCR_254: barrels and the save machine
    where: SCR_222 barrels `S222_P06` (310,194) `S222_P07` (348,211) `S222_P08` (309,255) `bar-sh`; SCR_254 savebot `S254_P05` (352,88)
    actor: barrels, machine
    do: hit the barrels (+3 life each, `bar-sh.c:30` -> `sheart`), save at SCR_254
    needs: none
    result: life, game saved
    hazards: SCR_222 is not locked; SCR_254 has two thorns

51. Down the hole to Milder
    where: SCR_254 `S254_P04` (491,288), a `hole` warp -> SCR_085 (191,332); then walk right to SCR_086 (base script of 085 `s7-hell.c`)
    actor: the hole (type 1 warp placement)
    do: step on the hole; on SCR_085 walk east
    needs: none
    result: SCR_085 base `s7-hell.c:3-22`: music by `get_burn()`, and at `&s7-boat == 0` a boat appears at (726,287) and sails left (`s7-boat.c:4-6`), `&s7-boat 0 -> 1` (`s7-hell.c:21`)
    hazards: Dink falls with a fade; the exit hole back is `S085_P01` (142,341) -> SCR_254 (481,235); the boat's `hit` says "Come back here!" and loops (`s7-boat.c:9-15`)

52. Talk to Milder (the scene hands over to Seth)
    where: SCR_086 `S086_P01` `s7-mil.c` (349,223) (nohit 1), actor: Milder
    do: talk; menu "Refuse to leave without him" or "Take his advice" (either; `s7-mil.c:59-62`); skip all dialogue
    needs: `&story == 14` (at 15 it only says "Poor Milder.", `:22-26`)
    result: the explosion and Seth (sprite at (320,150), seq 580) appear (`:93-127`); `sp_script(&temp1hold, "s7-boss")` (`:137`), `unfreeze(1)` (`:138`): the fight starts at once
    hazards: about 30 s of dialogue with `say_stop_xy`; `&fighting` is a local of `main` (`:4`) so a second talk during the fight says "Milder, wake up!  Help me fight this guy!" (`:28-31`)

53. Seth (the stat wall)
    where: SCR_086, actor: runtime sprite, script `s7-boss.c`
    do: ranged only: arm the bow, stay out of the cardinal lines, draw to full power (about 1.2 s) and fire; dodge the bomb's 0.8 s wind-up; do not touch Seth
    needs: see 2.6 (strength about 22+ with the massive bow and bow lore, or about 25 with b1 and bow lore, defense about 10-20, lifemax 60-80); no heal in the room
    result: `die` (`:239-309`): `&story 14 -> 15` (`:304`), `&life = &lifemax` (`:300`), "Too bad I had to kill him, he seemed likable enough." / "I must now get back to Goodheart Castle and inform the King." (`:297-302`), `add_exp(10000, ...)` (`:247`), `sp_kill` (`:307`)
    fight: `s7-boss.c:15-25`: brain 10, timing 33, speed 1, hp 300, defense 25, touch 30, target Dink; `attack` every `random(4000,2000)` ms (`:32`): 50% bomb (`freeze`, 500 + 4x200 ms wind-up, `spawn("dam-bom2")`, explosion at Dink's position, strength 25, range 30, `:41-75`, `dam-bom2.c:3-10`), 50% "greater harm" `hurt(target, 30)` unless `random(40,1) <= &magic` (`:76-102`); `hit` speeds Seth up at hp < 270 (2), < 200 (3), < 100 (4), < 15 (5) and half the time returns before a taunt (`:105-237`)
    hazards: **the route cannot win this at its natural stats** (2.6); `&life` hitting 0 runs `dinfo.c:3-39` ("Load a previously saved game" / "Restart game" / "Quit to Windows"), and Seth's `die` is only reached if he dies first

54. Seth is dead: the exit is open
    where: SCR_086, actor: none
    do: wait for the scene (about 7 s of `wait`s) to end and Dink to be unfrozen
    needs: step 53
    result: `&story == 15` (`s7-boss.c:304`)
    hazards: `die` calls `script_attach(1000)` and `kill_this_task` (`:293, 308`); Dink's life is restored to full (`:300`)

### Act G. The ending (&story 15 -> 16): 2 steps

55. Return through the machine
    where: SCR_154 `S154_P23` `s7-warp.c` (225,279), then SCR_253 (327,378)
    do: **teleport to SCR_154** (`dink.Goto 154`), talk to the machine; menu "Press the red button" (option 1)
    needs: `&story == 15`
    result: `&player_map = 253`, Dink to (327,378) (`s7-warp.c:44-56`)
    hazards: walking back 086 > 085 > 254 > 222 > 190 > 158 > 157 > 156 > 155 > 154 (`S085_P01` exit hole) re-enters the locked rooms: monsters killed with `editor_type 6` return 5 min after the player last left their screen (`D:6040-6140`), and Seth's fight alone lasts minutes, so SCR_190/157/156 will be full again (each locks). `Goto` 154 avoids them; the machine sprite `S153_P02` at x=825 on SCR_153 is off the screen (data quirk), the usable machine is `S154_P23`

56. The King: the ending (&story 16)
    where: SCR_070 (`dink.Goto 070`; the real walk is the whole Edge/castle trip), actor: `S070_P03` `king.c`
    do: talk; skip all dialogue and the credits (15 `say_stop_xy` lines with `wait(300)` each)
    needs: `&story == 15` (`king.c:5`)
    result: "`%SMALLWOOD HAS RETURNED!" ... "Thanks for playing - Seth" (`:8-46`), six potions spawn at (273,264) (336,264) (401,264) rpotion x3 and (273,302) (336,302) (401,302) ppotion x3 (`:51-98`), **`&story 15 -> 16`** (`:102`)
    hazards: the credits use `say_stop_xy(..., 20, 380)` which are text overlays, not speech bubbles: the probe's `SkipDialogue` must clear them; afterwards talking again gives "`%Ahh, my favorite subject!" (`:108-113`); the potions are `touch` pickups (+3 strength, +3 magic)

## 4. Engine behaviours the route depends on

| Behaviour | Where it matters | Script lines / engine lines | Implemented in the remaster? (check) |
|---|---|---|---|
| `move_stop` / `move(sprite, dir, until, nohard)`: scripts pass 1, so the move **ignores hardness** and the script blocks until the target coordinate | every cutscene (steps 12, 13, 18, 23, 34, 35, 52, 56); cult girls, Nelson, camp scene | `D:8588-8610`, `D:13489-13491`; `s2-culg.c:38`, `s3-camp.c:44-66`, `s2-cult.c:52` | AGENTS.md: scripted moves ignore hardness ("Scripted `move`/`move_stop` stay the director's ... no hardness"): yes |
| `move(1, dir, 410/700, 1)` carries **Dink across a screen edge** | steps 12, 23 | `s2-culg.c:38`, `s3-camp.c:66` | verified 7 Nov 2026 (Ch2 step 6 and Ch7 step 7: SCR_489 -> SCR_521) |
| `screenlock(1/0)` | steps 11, 22, 24, 36, 47-49 | `s2-cult.c:187`, `s2-cslay.c:73`, `s3-mog.c:30`, `en-gmog.c:47`, `s3-camps.c:92`, `s3-dorks.c:39`, `en-drag.c:11`, `s5-end.c:9`, `s7-*.c`; `D:10083-10095`, `D:14053` | yes (AGENTS.md "Locked fights"); warps are not refused |
| `fade_down` / `fade_up`, `fill_screen`, `load_screen(n)`, `&player_map = n`, `sp_x(1,..)` warps | steps 12, 22, 25, 39, 43, 45, 55 | `s2-culg.c:41-56`, `en-gmog.c:62-74`, `s3-mayor.c:138-146`, `s2-ca-g.c:176-186`, `s6-hole.c:21-28`, `s6-warp.c:44-56`, `s7-warp.c:44-56`, `s2-cave2.c:151-161` | UNVERIFIED for each warp-by-script (the probe's `Goto` is not the same code path) |
| `wait(n)` lengths (blocking the script, not the game) | cutscenes: Maria 2 s waits, cult about 20 s, parade about 40 s, ducks about 25 s, machine 6-7 s, Seth intro about 30 s, credits about 15 x 300 ms | e.g. `s6-warp.c:18-53`, `s4-end.c`, `s3-tc.c`, `king.c:9-98` | UNVERIFIED lengths against the original; `slomo 4` shortens them 4x |
| `sp_brain(sprite, n)` switches (16 -> 9 on `hit`, 9 -> 12 shrink-and-vanish, 10) | goblins, Jack, guard, dragons | `s3-gs.c:34`, `s3-gh.c:34`, `s2-jack.c:162`, `en-gmog.c:36`, `s3-gobg.c:32`, `dam-icee.c:48` | implemented ports of brains 0-16 (AGENTS.md) |
| `kill_this_task` | fades and warps end their script; `main`s that never return (`s2-cave2`, `en-gmog.die`) | `s6-hole.c:29`, `en-gmog.c:75`, `s6-warp.c:58`, `s3-mayor.c:147` | yes (director) |
| `spawn("name")` runs a script attached to 1000 | Mog, `s4-end`, `s5-end`, `dam-bom`, `dam-bom2` | `s3-gh.c:70`, `s3-gs.c:71`, `s4-duck.c:20`, `en-drag.c:115`, `item-bom.c:6`, `s7-boss.c:69`; `D:8181-8203` | verified for Mog (`s3-gs.c:71`, Ch7 step 5, 7 Nov 2026); the others UNVERIFIED (calls.csv lists 7 uses) |
| `get_sprite_with_this_brain(n, current)` counts **other** active sprites with that brain on the screen | Mary's talk gate, Mog spawn, every unlock, Jack, Joppa | `s2-culg.c:13`, `s3-gh.c:64-66`, `s7-*.c`, `en-drag.c:110`, `s4-duck.c:17`; `D:9201` | verified for brain 9 (Mary's gate in chapter 2; `en-bong.c`/`en-boncd.c` `main` target the other monster, chapter 4: the pair fights itself); the brain 16 half of the goblins' Mog test is not played |
| `compare_weapon("item-b1")`, `count_item`, `free_items` | steps 15, 16, 20, 27 | `s3-gobg.c:80`, `s3-st2p.c:31,82`, `s4-st3p.c:105` | **verified** (chapter 5): `free_items() >= 1` lets Arturous sell, the armed bow makes the guard say "ashee yoo hav bough. GATS OPAN!" (&gobpass 1); the refusal with another weapon armed is not played |
| `activate_bow` / `get_last_bow_power` (two-phase, key-hold) | steps 53 and every arrow | `item-b1.c:5-15`; `D:9397-9420`, `D:14564-14612` | UNVERIFIED (probe has no "hold attack" action) |
| `is_script_attached` + `run_script_by_number(.., "DIE")` on a burnt tree | step 38 (bow lore hut) | `dam-fire.c:35-39`, `s3-sec1.c:9-27` | UNVERIFIED |
| `sp_script(sprite, "x")` runs `x`'s `main` **immediately**, so lines set before it are overridden | knights' real stats, cult girls, Seth | `D:8143-8175`; `s3-camps.c:96-116` vs `s3-dorks.c:3-21`; `s2-cult.c:200-220` | the original does (`dink.cpp:8164-8171`); **the remake does NOT** (it starts main after the caller yields): the knights end with hp 100 (AGENTS.md pitfall 53). Original values: defense 6 / strength 12 / touch 5 / hp 40 |
| `editor_type(&hold, 6)` respawn clock; `editor_type 1` permanent; `editor_type 4` chest stays open | grinds, chests, potions | `s7-slay.c:59`, `en-pill2.c:35`, `ch1-ap.c:13-21`, `gheart.c:24-28`; `D:6040-6140` | **verified** (chapter 4): the Bongs killed on SCR_583/480/632 are back 302 s of game time after Dink left (`respawn S480_P04` in the trace), the clock running at 8x time dilation; the survivors are recreated at full hitpoints on every entry |
| Random drops via `emake` and `random(range, base)` | gold ledger, hearts | `emake.c`, `mgold.c:27`, `lgold.c:26`, `gold200.c:26`; `D` `rand() % range + base` | yes (seeded stream) |
| `say_stop_xy` text overlays | credits, Milder's lines | `king.c:20-46`, `s7-mil.c:39-129` | UNVERIFIED (skippable overlay) |
| `sp_nocontrol(1,1)` during spell/attack animations | fireball cast, arrow recovery | `item-fb.c:26`, `item-ice.c:24` | UNVERIFIED |
| `&update_status` gates spell recharge and level-ups | everything with magic or exp | `D:5836-5870, 17346`; set 1 by `s1-h1-m.c:68`, `escape.c:70`; set 0 by `dinfo.c:4` | yes (StatusTick) |
| `set_callback_random("target", lo, hi)` re-targeting timer | dragons, bong, Seth is not (`s7-boss` has none) | `en-drag.c:29`, `s7-drag.c:28`, `s7-bong.c:47`, `en-bong.c:46` | UNVERIFIED |
| `hurt(sprite, n)` through defense with pity, runs the victim's `hit` | dragon/Seth harm, NPC deaths | `D:9937-9970`; `en-drag.c:81`, `s7-boss.c:87` | UNVERIFIED (dragons' `hurt` on brain-16 NPCs must trigger `die` -> `&life = 0`) |
| `busy`, `sp_prop` | `busy` is only in `s8-duck2.c`; `sp_prop` (`s5-fguy.c:6,9`) is not an engine command | `diagnostics.json` | not needed on the route |
| `dink_can_walk_off_screen(1)` | the Mary escort | `s2-culg.c:37, 85` | UNVERIFIED |
| Dink walk speed `set_dink_speed(3)` | kiting arithmetic | `main.c:79` | AGENTS.md: Dink walks in original pixel steps |

## 5. Known traps

1. **The last-option default.** Menus where "last option" is wrong: the cult menu (`s2-cult.c:122-131`, last = "Use brains and stay hidden" loops forever, `:133-143`); the King's menu (last = "Leave", the first talk then leaves story at 13, `king.c:137-141`); Pete's shop menu (last = "Leave" leaves nothing bought); every `choice_start` with a hidden option. Name the answer in every step that has a menu.
2. **Result numbering is by source position, not by visible position.** "Offer to find Nadine's girl" is `&result == 2` even though it is the first visible option at `&s2-nad == 1` (`s2-nadp.c:30-37, 77-94`); "Show the scroll" in `s3-mayor.c` is option 2, but option 1 is "Say hello".
3. **NPCs that exist only in some states.** The Mayor is created only when `&mayor` is 2 or 4 (`s3-st1.c:18, 35`); Christina only when `&mayor` is 0, 3 or 4 (`s3-tc.c:9-19`); the pit and guards at SCR_243 only at `&story > 13` (`s6-holes.c:3`); the Windemere stairs only at `&story > 10` (`s4-h2.c:3-9`); the rock and ducks are vision-1 placements until `&s4-duck == 2`.
4. **Menus that change with facts.** `s3-chick.c` (3 variable options), `s2-auntp.c` (9 options by `&s2-aunt`), `s2-nadp.c`, `s3-gobg.c` (option 1 disappears at `&gobpass != 0`), `king.c`, `s3-bowl.c` (option 1 at `&bowlore == 0`), `s8-guy.c`.
5. **Scenes that need Dink in the right spot / frozen.** Mary only listens when no brain-9 sprite is left (`s2-culg.c:13`); the scroll scene at SCR_489 needs `&mayor == 3` and `&gobpass >= 5` (`s3-camp.c:3-6`); the bow check is the **armed** weapon (`s3-gobg.c:80`); the bomb must explode within 30 px of the rock (`dam-bom.c:100`) with `&missle_source` = the explosion.
6. **Locked screens before a warp.** SCR_238 (cult), SCR_680 (Mog), SCR_521 (knights), SCR_419 (dragons), SCR_156/157/190 (slayers, ducks) refuse to let Dink leave until the last brain-9/10 sprite dies. `dink.Goto` must not be used on them.
7. **Items that must be armed before use.** Bow (guard), fireball (burning the tree, killing Jack), bomb (`item-bom.c:6-8`: `use` consumes it), fists/sword (melee). Arming the fireball leaves the weapon unchanged; the swords add strength only while armed (`item-sw1.c:44`).
8. **Recharge rule.** `ceil(cost/magic)` x 100 ms: fireball cost 100: magic 2 = 5.0 s, magic 9 = 1.2 s (12 steps); Acid Rain cost 1000, hellfire 2000. `&update_status` must be 1 or nothing recharges (it is set by `s1-h1-m.c:68` after the first mother talk).
9. **Gold that cannot be re-earned quickly.** The three 200-gold chests, the potions and gold hearts are one-time (`editor_type 1/4`); only monsters respawn.
10. **Hitting friends.** Mary (hp 20) and the Joppa family die easily and set `&life = 0` (`s2-culg.c:110`, `s5-fguy.c:101`, `s5-fmom.c:27`, `s5-fd.c:30`); castle guards (hp 100, strength 50, `s2-ca-g.c:8-9`) and Christina/the gate guard turn hostile when struck.
11. **Fights that continue after the "last" kill.** The goblins spawn Mog only if **no brain 9 or 16** remains on SCR_680 (`s3-gh.c:64-66`); Windemere's `s4-end` needs all brain-3 ducks, including headless bodies (`s4-duck.c:17`); Joppa's `s5-end` needs `&life > 0` (`en-drag.c:113`).
12. **Death.** `&life < 1` runs `dinfo.c` (menu "Load a previously saved game" / "Restart game" / "Quit to Windows"); a probe that dies should load the last save, not restart.
13. **The Seth room has no heals** and the way back crosses the respawned locked rooms (step 55: teleport).
14. **Respawn after a long stay.** Anything killed with `editor_type 6` (goblins, slayers, ducks, pill bugs, the Windemere ducks are not) is back after 5 min away.

## 6. `&story` values 7..16 and step counts

| &story | Set by | Line | Condition / note |
|---|---|---|---|
| 7 | `s1-brg2.c` (toll) | 47 | pay 100 gold (also `s2-cave2.c:148`, redundant, optional prisoner quest) |
| 8 | `s2-culg.c` (Mary) | 79 | after the cult fight, `&s2-nad` 2 -> 3 at `:78` |
| 9 | `s3-1st.c` (SCR_589 eavesdrop) | 93 | only if `&story == 8` at load; skippable |
| 10 | `s3-tc.c` (parade) | 285 | `&mayor == 5`; `&mayor = 6` at `:286` |
| 11 | `s4-end.c` (ducks) | 7 | after the last duck; `&s4-duck = 2` at `:6` |
| 12 | `s5-end.c` (Joppa) | 36 | after both dragons; `&s5-jop = 4` at `:37` |
| 13 | `king.c` (first talk) | 134 | `&story == 12` |
| 14 | `king.c` ("Offer to help Milder") | 189 | `&story == 13` |
| 15 | `s7-boss.c` (`die`) | 304 | Seth dead |
| 16 | `king.c` (talk at 15) | 102 | the credits scene; the last value written anywhere (`facts.csv`) |

Per act: **A 12 steps** (steps 1-12, 5 of them preparation/optional), **B 13 steps** (13-25), **C 7 steps** (26-32, 1 optional), **D 5 steps** (33-37),
**E 8 steps** (38-45), **F 9 steps** (46-54), **G 2 steps** (55-56): **56 steps**; the minimum path alone (dropping steps 2, 3, 4-8, 14, 28, 32, 38, 41, 44, and the
optional heals) is about 40 steps; every step that needs the gold grind or the Seth kit is marked.

## 7. Disagreements with the bible, and what could not be verified

Bible vs script (script wins):

- Bible 01 section 1 item "Cave prisoner ... ends with the death and the Mordavia scroll. Also sets `&story=7`" is right but the step is **not on the route**: `&story` is already 7.
- Bible 02 section 3 says the bow is "effectively mandatory": confirmed (it is `compare_weapon("item-b1")`, `s3-gobg.c:80`), and the mayor check at `:84` is also required.
- Bible 02 gives the knights no stats; the script's attached `s3-dorks` overrides `s3-camps` (hp 40, defense 6, strength 12, touch 5, exp 150).
- Bible 01 says "Killing Jack (50 HP) gives +100 exp and `&s2-aunt=4`": confirmed (`s2-jack.c:176-177`); Jack's hit is a touch of 10, he has no melee strength.
- Bible 02 says Joppa's reward "opens the Joppa axe shop": `s5-st1.c:4` tests `&story > 11` (confirmed by `facts.csv`), unrelated to the route.
- Bible 02 section 1 says "Mog's death ... warps to map 489": confirmed (`en-gmog.c:68-71`), and the camp sneak (`s3-camp.c`) sets nothing but ends faded.
- The bible's list of potions is by suffix only; placement ids and counts here come from `tools/dinkex/out/screens/*.json`.

Not verified (flagged "UNVERIFIED" above): the geometry of every kite (reach vs `sp_distance` / `sp_range`); how many screens of the Edge plateau a real
walk crosses safely; whether the bomb explosion hurts the thrower; the item-slot count behind `free_items()`; the unopened scripts `box2-sp.c`, `bar-dp.c` beyond the `external`
lines; the exact attack cadence and animation lengths of the monsters (the Monte Carlo uses `random(4000,0)` + 0.5 s); whether `SCR_680` is walkable from the north with the gate shut
(`connectivity.json` says yes; the data is advisory because `tools/analyse` is being edited); the hop lists in the steps (same source); SCR_352 reachability; the Terris healer's and
Windemere healer's exact price lines (`s2-healp.c`, `s4-healp.c`, read from `shops.json` and a partial read); the Hellfire and massive-sword/bow timing for Seth (kits B and C are computed, not
played); the probe's current implementation of every blocked-script check named in section 4.

## 8. What the probe has run (7 Nov 2026, `Dink.Gameplay.Probe.Ch1Stonebrook` .. `Ch7Sanctuary`)

| Route step | Chapter / step | Result |
|---|---|---|
| 1 baseline (&story 7) | Ch1 steps 1-47, Ch2 load | Ch2 loads Ch1's save: 0 of 122 state lines differ |
| 9, 10 Nadine (&s2-nad 2) | Ch2 steps 1-2 | menus answered by text ("Ask Nadine why her house is such a mess", "Offer to find Nadine's girl") |
| 11 the cult | Ch2 steps 3-5 | menu "Say something to the effect that you are going to save her"; four girls + Nelson killed with fireballs and fists, kited (`KiteFight`), 84 s, no damage, `screenlock(0)` on Nelson's death |
| 12 Mary (&story 8) | Ch2 step 6 | talk; `move(1, 2, 700, 1)`, `fade_down`, `&player_map = 66; load_screen(66)`, Dink at y 480, `move_stop`s, `&story 8`; Dink ends in Nadine's house (SCR_066) |
| 5 gold heart | Ch3 step 1 | SCR_524 `gheart`: lifemax +10 |
| 4 chest | Ch3 steps 2-3 | SCR_005 `ch1-pap`: a punch opens it, the coins fall at Dink's feet (+200) |
| 5 chest, 7 chest | Ch3 steps 4-7 | SCR_557 and SCR_747 the same (+400); gold 724 at the end of the chapter (the drops and fixes of later runs moved it from 731) |
| 6 strength potions | Ch3 step 8 | SCR_681 x4 (teleported to; SCR_680's goblins untouched): strength 8 |
| 17 Christina, 18 girl, 19 Mayor | Ch3 steps 9-11 | &mayor 1, 2, 3 |
| (grind) | Ch4 steps 1-12 | gold 724 -> 1072 without a hit: SCR_583 (Bong + Boncd feud), SCR_480 (two Bongs in a low-hardness pen, shot across the fence), SCR_632 (two Bongs), a 302 s wait at 8x in Arturous's shop, a second round (see AGENTS.md "Chapter 4, the gold") |
| 15 the bow, 16 arm it | Ch5 steps 1-2 | menu \"Buy a Bow and some arrows for $1000\": gold 1072 -> 72, `item-b1` in slot 4; `ArmItemSlot`: `arm item-b1` |
| 20 the gate guard | Ch5 step 3 | SCR_712 talk, \"Ask the Goblin guard to let you in\": &gobpass 1 |
| 21 goblins | Ch6 step 2; Ch7 steps 1-5 | S680_P13 (`s3-gh`) pulled by a fireball and killed (Ch6); S680_P14 (gh), S680_P11 (gs), S680_P12 (gs) killed in melee with `DuelFight` (AGENTS.md \"`DuelFight`\"), a Terris healer visit (`s2-healp`, \"Get healed\", 1 gold per missing life) after each of the first two; the last death starts Mog (`spawn`, `s3-gs.c:71`); +150 exp each |
| 22 Mog | Ch7 step 6 | `s3-mog` scene (`screenlock(1)`), `en-gmog` killed with `DuelFight` (50 hp, 25 s of game time, no `hit` taken that matters), his death: `fade_down`, `&gobpass 1 -> 5`, warp to SCR_489 |
| 23 the Cast camp | Ch7 steps 7-8 | SCR_489 `s3-camp.c`: Dink frozen, scripted walk, `move(1, 2, 410, 1)` crosses the south edge to SCR_521 (the crossing code runs for a scripted mover), `fade_down`; SCR_521 `s3-camps.c`: `fade_up`, `move_stop` walks, the dialogue (skipped), 18 s of game time to the scene's start |
| 24 the ambush | Ch7 step 8 (to the first blow) | `screenlock(1)`, three knights `s3-dorks` created and `unfreeze`d, `&mayor 3 -> 4`: verified. **The fight is not played: the stop.** The remake's knights have 100 hp (`sp_script` starts main instead of running it, AGENTS.md pitfall 53), the original's 40; see AGENTS.md \"Where the probe stops, and why\" for what was tried (kiting, an orbit) and the numbers |
| 25 the Mayor, the parade | not reached | |

Verified in the remaster by these runs (section 4 rows): `move`/`move_stop` with nohard 1 across the map's edge and into the exit
door's warp (the warp must NOT fire: the director now keeps `bMoveNoHard`, `UDinkGreyboxSubsystem::WarpSuppressed`); a nohard 0
`move_stop` into a door DOES warp (s1-h1-s.c, chapter 1); `&player_map = N; load_screen()` (s2-cave2.c, s2-culg.c); `sp_x/sp_y` past
the map (the pawn no longer falls: gravity is off while Dink is frozen); `screenlock` with five chasers and its unlock by the last
`die`; `get_sprite_with_this_brain` (Mary only talks when no brain-9 sprite is left); `sp_script(sprite, "x")` running `x`'s `main` at
once (Nelson turns into a slayer where he stands, holding Dink for the scene); `kill_this_task`; the level-up menu in a fight.
Verified since: `compare_weapon` (the armed bow), `free_items`, the respawn clock under time dilation, `hit`-only-that-one for a goblin (`s3-gh.c:32`: the other three stayed peaceful), brain-9 feuds. Verified since (7 Nov, evening): `spawn("s3-mog")` (Mog's scene starts when the last brain-9/16 sprite of SCR_680 dies), `move(1, dir, n, 1)` from SCR_489 over the screen's edge to SCR_521 and `fade_up` there, the camp scene's walk and dialogue, the ambush scene up to the first blow (`screenlock`, `&mayor 4`, three `sp_script`ed knights). Still UNVERIFIED: `activate_bow`, the ambush fight, the Mayor's scroll and the parade. **Found wrong in the remake:** `sp_script` does not run `main` at once (row 749 of section 4 said it did; the knights have 100 hp, not 40; AGENTS.md pitfall 53).

Corrections to this document found by the runs: the cult girls hit each other (the melee rule hits every sprite in reach); after
`s2-culg` the Mary scene leaves `&s2-nad 3` and Dink in SCR_066, not SCR_238; the three `papgold` chests and the cult's drops leave Dink 724 gold at the end of chapter 3 (the old figures 731, 808 and 773 came from runs
before later fixes), so the bow needs 276 more; a large drop (`lgold`) is 50-74 gold, a medium one (`mgold`) 5-34 (the table in 2.1 has
16.6 and 55.8 per medium and large drop on average).

**Gold, the real shortfall:** 276 at the end of chapter 3; chapter 4 earns 348 in two rounds (13 + 61 + 65 + 67, then 14 + 58 + 70). The pill
bugs (speed 180 px/s) were not needed: the Bongs kill each other.
