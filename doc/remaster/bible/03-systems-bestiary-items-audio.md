# Dink Smallwood (1997) gameplay-systems data for the 3D remaster

All nine sections are covered from the scripts, `dink.ini`, `dink.dat`/`map.dat` and `dink.cpp`. Nothing in the repo was modified. Region names are the only inferred content and are marked as such.

Paths: scripts are in `bin/dink/story/`, the engine is `source/dink/dink.cpp`.

DinkC `random(a,b)` returns `b .. b+a-1` (dink.cpp:8808); all ranges below use that.

## 1. Player stats and progression

| Item | Value | Source |
|---|---|---|
| Starting stats | strength 3, defense 0, magic 0, life 10/10, level 1, gold 0, exp 0 | main.c |
| Start state | Fists armed; position (334,161) facing 4; base_walk 70, base_attack 100 | start-1.c, newgame.c |
| Inventory | 16 item slots, 8 magic slots | dink.cpp:18-19 |
| Move speed | `set_dink_speed(3)` = 3 px/frame; 2 = 6 px/frame; 1 = 12 px/frame | dink.cpp:17311 |
| Melee damage | `S/2 + rand(1..(S+1)/2) − target defense` (integer division); if ≤0, 50% chance of 1 | dink.cpp:15567, 6656 |
| Missile damage | `trunc(S/2 + rand[0,S/2) + 1) − defense`, minimum 0, no pity point; S=1 gives `1 − defense` | dink.cpp:14363 |
| Defense | Flat subtraction from melee, touch damage and scripted `hurt()`; 400 ms no-touch window after a touch hit | dink.cpp:15672 |
| Magic stat | Every 100 ms `magic_level += magic` until `magic_cost`; casting zeroes it. Recharge seconds = cost / (10 × magic) | dink.cpp:5935 |
| Magic resist | Dragon and Seth spells are resisted when `random(40,1) ≤ magic`, so resist chance = magic/40 | en-drag.c, s7-boss.c |
| XP to next level | `100 × level²`, capped at 99,999; exp is reduced by the threshold on level-up | dink.cpp:235, 5869 |
| Level-up reward | +1 to one of Attack / Defense / Magic (player choice) and +3 max life; no heal | lraise.c |
| Max level | 32; a further level-up sets exp to 0 and says "What a gyp!" | lraise.c |
| Death | Life < 1 runs `dinfo.c`: death anim seq 436, 3 s wait, menu Load / Restart / Quit. No respawn or penalty | dinfo.c |
| Saving | Talk to the save machine (seq 449, looping sound 34): 10 slots, no heal. Placed on 10 screens: 37, 213, 252, 254, 344, 349, 408, 569, 588, 768 | savebot.c, map.dat |

- XP thresholds run 100, 400, 900 … 96,100 (level 31→32), totalling 1,041,600.
- `savetop.c` is only the decorative top of the save machine (seq 84).

## 2. Weapons

Item icons are seq 438 with the frame shown.

| Script | Name | Bonus / damage | Behaviour | Source and price |
|---|---|---|---|---|
| item-fst (f1) | Fists | none | 4-direction punch, seq 100+dir, hit frame 3 | Start |
| item-sw1 (f7) | Longsword | +4 strength | distance 50, range 40, hit sound 10 | $400 at s2-out and s4-st3p; sells $200 |
| item-sw2 (f20) | Clawsword | +13 strength | as above | $2000 at s4-st3p; sells $1000 |
| item-sw3 (f21) | Light Sword | +25 strength | as above | $4000 at s6-st1p |
| item-axe (f6) | Throwing Axe | projectile strength 15, or strength−10 if strength > 25 | 8-direction thrown missile (seq 85), speed 6, infinite ammo | $3000 at s5-st1p |
| item-b1 (f8) | Bow | arrow strength = `floor(power/100) × max(1, floor(strength/5))` | Hold to charge, power 0–500 (+7 per ≥10 ms), no shot under 100; 8 directions; arrows stick in walls | $1000 at s3-st2p |
| item-b2 (f12) | Massive Bow | +8 strength while armed | Same as Bow | $5000 at s6-st1p |
| item-b3 (f13) | FlameBow | +15 strength while armed | Same as Bow, fire sound | $25,000 at s8-guy |
| item-bom (f3) | Bomb | explosion strength 8, range 30 | Consumable; fuse about 3.0 s; explosion seq 161 | $20 at s2-out and s4-st3p |
| item-bt (f22) | Hyper Boots | none | Occupies the weapon slot; speed 2 (double), punches like fists | $500 at s1-boot |
| item-pig (f2) | Pig feed | none | Throws seed (seq 430/431, anim 520+dir); quest trigger on screen 407 | s1-sack |
| item-nut (f19) | Nut | +2 life | Consumable | s1-nut; sells $2 |
| item-eli (f9) | Elixer | +20 life | Consumable | $25 at s2-healp, $100 at s4-healp |

- **Bow lore** ($1500, s3-bowl, sets `&bowlore`): triples arrow strength on 1/3 of Bow shots and 1/2 of Massive Bow shots. On the FlameBow every shot is tripled.
- `s2-out.c` contains a $400 bow purchase routine that is not offered in its menu.
- A "slayer claw" (`item-cl`, sells $150 in s4-st1p) has no script and no `add_item`, so it is unobtainable.

## 3. Magic

| Script | Name | Cost | Effect | Source |
|---|---|---|---|---|
| item-fb | Fireball | 100 | Missile strength 10, speed 6, range 10, 8 directions; burns trees (seq 32 frame 1 becomes seq 20) | Martridge's letter, s1-mh-f (also +1 magic, +200 gold); `get-fb.c` scroll pickup |
| item-ice | Acid Rain | 1000 | Missile strength 6; on impact becomes a stationary hazard (seq 94, touch damage 4) for 5 s; frees the prisoner on screen 579 | s2-mh-m, requires magic ≥ 5 |
| item-sfb | Hellfire | 2000 | Missile strength 40, range 20, 4 directions only; pierces enemies (stops only on walls or brain 0/6 sprites); burns trees | $1500 at s6-vend, or a scroll from the ch2-sfb chest (get-sfb) |
| item-p1 | Mordavia scroll | 200 | Quest spell; only does anything on screen 366 | s2-cave2 |

Example recharge times: Fireball at magic 1 takes 10 s; Hellfire at magic 10 takes 20 s.

## 4. Consumables and pickups

| Script | Effect |
|---|---|
| sheart, sfood | +3 life |
| heart | Full heal |
| gheart | +10 max life (no heal) |
| rpotion | +1 strength |
| bpotion | +1 defense |
| ppotion | +1 magic |
| apotion ("Megapotion") | +1 strength, defense and magic; in 4 chests (ch1-ap, ch2-ap, ch3-ap, s3-ch1) |
| 1gold | 1 gold |
| sgold | 2–11 |
| mgold | 5–34 |
| lgold | 50–74 |
| xlgold | 50–99 (not used by any drop table) |
| gold200 | 50–199 (misnamed) |
| papgold | 200 |
| gold500 | 500 |
| s6-fount | Free full heal |

Drop tables in `emake.c`:

| Table | Result |
|---|---|
| small | 1/3 small heart, otherwise nothing |
| medium | 1/20 small heart, 1/20 full heart, 1/20 food, 17/20 mgold |
| large | 1/20 full heart, 1/20 food, 18/20 lgold |
| xlarge | 1/20 full heart, 1/20 food, 18/20 gold200 |

- The "full heart" drop uses the small-heart sprite (seq 54).
- The food roll is `random(3,1)`, so food type 4 never drops.
- `s1-slim.c` calls `external("ranstuff","small")`; that script does not exist, so it drops nothing.

## 5. Bestiary

Speed is px per move and timing is ms between moves. Brain 9 monsters wander diagonally, chase their target and melee if they have a base_attack. "Lock" means `screenlock` until all brain-9 (or brain-10) monsters on the screen are dead, then sound 43 plays.

| Script | Creature (base_walk) | HP | Str | Touch | Def | XP | Spd / timing | Brain | Notes | Drop | Screens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| en-pill | Pillbug (130) | 8 | – | 1 | 0 | 5 | 1 | 9 | touch only | small | 36 |
| en-pill1 | Pillbug | 15 | – | 3 | 0 | 10 | 2 | 9 | lock | small | 237, 270, 301, 303, 334 |
| en-pill2 | Pillbug | 30 | – | 8 | 0 | 40 | 3 | 9 | | medium | 10 |
| en-pillf | Pillbug | 35 | – | 4 | 0 | 50 | 3 | 9 | | medium | 395 |
| s7-pill, sc-pill | Pillbug | 50 | – | 25 | 0 | 100 | 2 / 10 | 9 | lock | large | 5 + 1 |
| s1-fmons | Pillbug | 30 | – | 3 | 0 | 30 (+40) | 1, bursts to 9 | 10 (editor) | talks; farmer quest | – | 437 |
| en-slimg | Green puddle (670) | 13 | – | 3 | 0 | 3 | 1 / 10 | 9 | timing 0 when hit; not placed on any screen | – | 0 |
| en-slim | Red puddle (690) | 15 | – | 6 | 0 | 8 | 1 / 20 | 9 | | small | 8 |
| en-slimb | Blue puddle (650) | 25 | – | 3 | 0 | 14 | 1 / 10 | 9 | | small | 7 |
| s7-slimb | Blue puddle | 50 | – | 17 | 0 | 75 | 2 (1 after hit) | 9 | lock | medium | 4 |
| en-bonc | Bonca (530) | 20 | 8 | 4 | 3 | 30 | 1 / 33 | 9 | melee, attack wait 0–4 s | medium | 29, 306, 562, 648 |
| en-bonc1 | Bonca | 20 | 8 | 5 | 3 | 40 | 1 / 33 | 9 | lock | medium | 302 |
| en-boncd | Bonca | 20 | 8 | 4 | 3 | 30 | 1 / 33 | 9 | targets other brain-9 monsters | medium | 583 |
| s2-cbon | Bonca | 20 | 8 | 4 | 3 | 20 | 1 / 33 | 9 | | medium | scripted |
| s1-slim | Bonca graphics | 20 | 18 | 3 | 0 | 10 | 1 / 33 | 9 | | none | scripted |
| s1-cavem | Bonca graphics | 20 | 4 | 2 | 0 | 100 | – | 9 | plays battle.mid | – | 100 |
| en-pbon | Purple bonca (610) | 30 | 8 | 5 | 3 | 25 | 1 / 0 | 9 | lock | medium | 514, 515, 547, 577, 609 |
| en-bong, s7-bong, sc-lock | Gray bonca (600) | 40 | 10 | 5 | 0 | 120 | 2 / 0 | 9 | range 30, attack wait 0–2 s; targets other monsters; s7/sc versions lock | large | 6 + 4 + 3 |
| en-slay, s7-slay, sc-slay | Slayer (640) | 100 | 20 | 10 | 5 | 200 | 1 / 0 | 9 | range 45; s7/sc versions lock | xlarge | 7 + 3 + 3 |
| s2-cslay | Slayer | 40 | 15 | 5 | 5 | 200 | 1 / 66 | 9 | scripted cave fight | – | scripted |
| en-gh, s3-gh | Hammer goblin (760) | 40 | 15 | 10 | 2 (1) | 150 | 1 / 66 | 16, then 9 when hit | neutral until hit | – | 712, 680 |
| en-gs, s3-gs | Goblin soldier (800) | 60 | 20 | 8 | 2 | 150 | 1 / 0 | 16, then 9 | range 35 | – | 713, 680 |
| s3-gobg | Goblin guard (800) | 80 | 25 | 10 | 6 | 150 | 1 | 0, then 9 | | – | 712 |
| en-gmog | Horned goblin "Mog" (780) | 50 | 20 | 8 | 4 | 150 | 1 | 16, then 9 | death runs a cutscene to screen 489 and sets `&gobpass=5` | – | scripted |
| en-stg | Stone giant (820) | 40 | 35 | 25 | 18 | 400 | 1 / 33 | 9 | range 60 | xlarge | 11 (178–246) |
| en-drag, s7-drag, sc-drag | Dragon (200) | 80 | – | 10 | 8 | 400 | 1 / 66 | 10 | every 3–8 s casts "harm": 20 damage at any range, resistible; targets Dink 1 in 9, otherwise a random brain-16 NPC; en-drag locks | xlarge | 7 + 1 |
| s7-boss | Seth (green gnome, 580) | 300 | – | 30 | 25 | 0 (+10,000 on death) | 1 to 5 | 10 | see below | – | scripted |
| s7-dgirl | Crazy girl (330) | 100 | – | 20 | 0 | 300 | 3 / 0 | 9 | lock | large | 91, 126 |
| s7-duck | Evil duck (20) | 50 | – | 25 | 0 | 100 | 1 / 10 | 9 | lock | large | 190 |
| s3-dorks | Scripted humans | 100 | 12 | 5 | 6 | 150 | – | 9 | | large | scripted |
| s2-bar, s2-ryan3 | Silver knights (290, attack 720) | 40 | 10 | 2 | 0 | – | – | – | | – | scripted |
| s3-camps | Gold knights (300, attack 740) | 40 | 10 | 6 | 8 | – | 1 | 9 | lock | – | scripted |
| s2-ca-g | Knight (290) | 100 | 50 | – | – | – | 3 | 9 | | – | 402 |
| fish1 | Fish (434) | 25 | – | – | – | 50–149 | – | 9, frozen | surfaces every 0–6 s | – | 634, 665, 697, 727 |
| pdie | Giant pig | 2000 (editor) | – | – | – | 5000 | – | 4 | | – | 31 |
| thorn | Hazard | – | – | 15 | – | – | – | 0 | | – | 41 |

**Seth (s7-boss.c):** attacks every 2–6 s. Half the time he casts an explosion at Dink's position (dam-bom2: strength 25, range 30); otherwise "greater harm" for 30 damage, resistible. His speed rises to 2, 3, 4 and 5 as HP falls below 270, 200, 100 and 15. On death Dink is healed and `&story=15`.

Regions (inferred from script prefixes, not read from data): s1 Stonebrook, s2 Terris, s3 Windemere/goblin lands, s4 KernSin, s5 Joppa, s6 Edge of the World, s7 Darklands, sc secret cave.

## 6. Brain types

Dispatch is at dink.cpp:16858-16880.

| Brain | Meaning |
|---|---|
| 0 | None; only scripted moves or follow |
| 1 | Player |
| 2 | Bounce (unused by scripts) |
| 3 | Duck: wanders, quacks; a hit makes it a headless runner |
| 4 | Pig: wanders, oinks |
| 5 | Play sequence once, then stamp the last frame into the background (corpses, blood) |
| 6 | Loop sequence forever |
| 7 | Play once, then delete |
| 8 | Text sprite |
| 9 | Monster: diagonal wander, chases its target, melee when within `distance` and it has a base_attack, calls script `ATTACK`; dies to base_death+dir |
| 10 | Dragon/boss: cardinal wander, never melees, calls script `ATTACK` whenever attack_wait expires |
| 11 | Missile: flies, damages with its strength, runs script `damage` |
| 12 | Scale to `brain_parm` percent, then delete (pickup shrink/grow) |
| 13 | Mouse cursor (title screen) |
| 14 | Button |
| 15 | Shadow: follows the sprite in `brain_parm` |
| 16 | Peaceful NPC: wander and idle, killable |
| 17 | Missile that expires at the end of its sequence (explosions) |

`map.dat` sprite counts by brain: 0 ×5639, 3 ×116, 4 ×18, 6 ×30, 9 ×31, 10 ×7, 16 ×5. Most monsters get their brain from their script.

## 7. Animation inventory (dink.ini)

There are about 400 sequences. The direction is the last digit of the sequence number (1/3/7/9 diagonal, 2/4/6/8 cardinal). Frame counts were read from the `dir.ff` archives.

| Family | Sequences | Directions × frames (delay ms) |
|---|---|---|
| Dink idle | 12–18 | 4 cardinal × 4 (250) |
| Dink walk | 71–79 | 8 × 8 (43) |
| Dink punch | 102–108 | 4 × 5 (75); hit frame 3 |
| Dink sword set (swapped in on arm) | walk, idle, hit | walk 8 dir, idle 4 dir, hit 4 × 6 |
| Dink bow set (swapped in on arm) | walk, idle, draw 101–109 | walk 8 dir, idle 4 dir, draw 8 × 6 |
| Dink push | 312–318 | 4 × 10 |
| Dink magic cast | 322–328 | 4 × 5 (30) |
| Dink seed throw | 522–528 | 4 × 3 (150) |
| Dink die | 436 | 16 frames |
| Dink crawl | 452 | 18 frames |
| Pillbug | walk 131/133, death 141/143 | 2 dir × 5; death 1 frame |
| Puddle (blue 650, green 670, red 690) | walk, death (+10) | 2 dir × 6; death 1 frame |
| Bonca (530; gray 600, purple 610) | walk, attack 540/590/620, death 550 | walk 4 diag × 10; attack 4 cardinal × 5, hit frame 5; death 4 × 1 (shared) |
| Slayer | walk 640, attack 630, death 645 | 4 diag × 10; 4 cardinal × 6, hit frame 5; 1 frame |
| Goblins (hammer 760/750, horns 780/770, soldier 800/790) | walk, attack, death (+5) | 4 diag × 10; 4 cardinal × 6, hit frame 6; 1 frame. Horns also has a spin attack, seq 780, 6 frames |
| Stone giant | walk 820, attack 810, death 825 | 4 diag × 10; 4 cardinal × 5, hit frame 5; 1 frame |
| Dragon | walk 202–208, death 212/216 | 4 cardinal × 7; 1 frame |
| Spike | idle 831/833, walk 841/843 | 2 dir × 8; no script uses it |
| Knights (red 270, blue 280, silver 290, gold 300) | walk, death (+5), attack 710/730/720/740 | 4 diag × 10 (100); 1 frame; 4 cardinal × 6 |
| NPCs | maiden 220/240/250, oldman 230, girl 330, merchant 340/370/380/390, mom 350/360, soldier 400, peasant 410 | walk only, 4 diag × 10 (100), plus 1 death frame (oldman has none) |
| Gnomes | 560/570/580 | walk only, 4 diag × 10 (75) |
| Fairy | 261/263 | 2 dir × 10 |
| Boatman | 426 | 16 frames |
| Duck | walk 21–29, headless 111–119, head 121–129 | 6 dir × 4; 4 × 4; 4 × 4 |
| Pig | 41–49 | 4 diag × 6 |
| Fish | 434/435, flop 440/441 | 7 frames; 4 frames |

Effects, with frame counts:

| Effect | Seq | Frames |
|---|---|---|
| Tree fire | 20 | 29 |
| Arrow | 25 | 8 |
| Explosion | 70 | 15 |
| Axe | 85 | 10 |
| Acid spray | 94 | 10 |
| Bomb blast | 161 | 26 |
| Acid Rain projectile | 163 | 6 |
| Magic poof | 164 | 14 |
| Gold sparkle | 165 | 6 |
| Spark | 166 | 10 |
| Shockwave | 167 | 14 |
| Whirl | 168 | 16 |
| Stars | 169/170 | 6 |
| Blood | 187–189 | 3–4 |
| Seed | 430/431 | 4 |
| Shadow | 432 | 3 |
| Splash | 433 | 3 |
| Fireball | 502–508 | 4 dir × 5 |
| Hellfire | 512–518 | 4 dir × 16 |

- The slayer scripts set base_death to 680, which is actually the green puddle's death sequence.
- `graphics/dink/fall` and `graphics/dink/morph` exist on disk but are not loaded by `dink.ini`.

## 8. Audio

Sound effects, as loaded in `start.c`:

| # | File | Trigger |
|---|---|---|
| 1 | QUACK | ducks (engine) |
| 2–5 | PIG1–4 | pigs (engine) |
| 6 | BURN | explosions, tree burn |
| 7 | OPEN | no script use found |
| 8 | SWING | all melee swings and axe throw |
| 9 | PUNCH | default hit sound (engine) |
| 10 | SWORD2 | pickups, sword hit, level-up |
| 12 | WSCREAM | women hit |
| 13 | PICKER | seed throw; XP counter tick (engine) |
| 14 | GOLD | gold counter (engine) |
| 15/16 | GRUNT1/2 | Dink hurt (engine) |
| 17 | SEL1 | spell cast, FlameBow |
| 18 | ESCAPE | missile impact, menus |
| 19 | NONO | denial |
| 20/21 | SEL2/3 | title button hover |
| 22 | HIGH2 | heal, stat gain |
| 23 | FIRE | fire loop |
| 24 | SPELL1 | scripted magic, boss death |
| 27/28 | SNARL2/3 | slayer and goblin attack / hurt |
| 29 | HURT1 | bonca hurt |
| 30 | HURT2 | pillbug hurt |
| 31 | ATTACK1 | bonca attack, boss casts |
| 32 | CAVEENT | cave entry |
| 33 | LEVEL | level-up |
| 34 | SAVE | save machine loop, warps |
| 35 | SPLASH | fish |
| 36 | SWORD1 | knight fights |
| 37 | BHIT | barrel/box break, arrow hit |
| 38 | SQUISH | slimes |
| 39 | STAIRS | secret stairs |
| 40 | STEPS | s3-1st |
| 41 | ARROW | arrow lands |
| 42 | FLYBY | s2-fgate, s8-da, s4-h1p |
| 43 | SECRET | screen unlock, secrets |
| 44 | BOW1 | bow release |
| 45 | KNOCK | door |
| 46/47 | DRAG1/2 | dragon and Seth hurt / dragon attack |
| 48 | AXE | axe hit |
| 49 | BIRD1 | Seth taunt |

Sounds 11, 25 and 26 are loaded but not used by any script.

Scripted music (`playmidi`):

| Track | Where |
|---|---|
| 1003.mid | title (start.c) |
| battle.mid | s1-cavem, s1-rob2, s2-bar, s2-ryan3 |
| wanderer.mid | s1-mh-o, s1-wiz, after the cave fight |
| insper.mid | s1-h1-o, s1-caves |
| bullythe.mid | s1-bul, s2-man2 |
| love.mid | s1-vic, s2-culg |
| lovin.mid | s3-tc |
| denube.mid | s2-cult |
| caveexpl.mid | sc-ent |
| 5.mid | s1-h1-m |
| 1004 (4.mid) | s2-cave2, s3-1st, s3-camps, s7-mil |
| 1009 | s3-mog, s5-fguy |
| 1011 | king.c |
| 1006, 1018 | s7-hell |
| 1015 | s7-mil |

Per-screen music is stored in `dink.dat`. A value N plays `N.mid`, values over 1000 play `(N−1000).mid`, 0 keeps the current track and −1 stops music; `.ogg` versions are preferred.

| Value | Screens |
|---|---|
| 0 | 488 screens |
| 1007 | 46 screens, 26–224 (the s7 thorn area) |
| 1016 | 28 screens (right column and bottom row, 384–768) |
| 1010 | 12 screens (257–259, 514–610; purple bonca caves) |
| 1002 | 10 screens (238–334) |
| 106 | 12 screens (501–568, 727) |
| 105 | 11 scattered screens (probably interiors) |
| 104 | 6 screens (407–441, start village) |
| 100 | 6 screens (624–658) |
| 1 | 9 screens (467–532) |
| 107 | 4 screens (74, 105, 169, 202) |
| 103 | 3, 35 |
| 102 | 37 |
| 101 | 73 |
| 1005 | 34 |
| 1008 | 419, 451 |
| 1012 | 70, 102 |
| 1013 | 260 |
| −1 | 188, 253 |

## 9. Economy

| Item or service | Price |
|---|---|
| Bridge toll | 100 |
| Hyper Boots | 500 |
| Longsword | 400 (sells 200) |
| Bomb | 20 |
| Elixer | 25, or 100 in s4 |
| Healer | 1 gold per missing HP |
| Bow | 1000 |
| Bow lore | 1500 |
| Hellfire | 1500 |
| Clawsword | 2000 (sells 1000) |
| Throwing Axe | 3000 |
| Light Sword | 4000 |
| Massive Bow | 5000 |
| FlameBow | 25,000 |
| Fountain coin | 1 |
| Duck betting (s8-da) | 50 / 100 / 200 |
| Nut | sells 2 |

Average gold per drop is about 19.5 (mgold), 62 (lgold) and 124.5 (gold200).

Balance observations:
- **Bows dominate.** Arrow strength multiplies with strength/5, bow items add strength, and bow lore triples it. With effective strength 40, a FlameBow arrow has strength 5 × 8 × 3 = 120 at range.
- **Defense is a flat subtraction**, and it also applies to boss spells. High defense trivialises touch damage, which tops out at 30.
- **Magic is doubly valuable**: it sets recharge rate and gives magic/40 resistance to dragon and Seth spells.
- **Stat growth is scarce**: only +1 per level and 31 level-ups, so potions and Megapotions matter a lot.
- **Weak or dead content**: bombs (strength 8) are utility only; the Throwing Axe ignores strength below 26; en-slimg, the Spike enemy, xlgold and the slayer claw are effectively unused.
- **The pig on screen 31** gives 5000 XP for 2000 HP.

Supporting files:
- `doc/remaster/reference/sequences.txt`: the full per-sequence listing with frame counts and delays.
- `tools/dinkex/`: the extractor that now produces the same data (`out/sequences.json`, `out/screens/`); the two one-off scripts used for this report were folded into it.
