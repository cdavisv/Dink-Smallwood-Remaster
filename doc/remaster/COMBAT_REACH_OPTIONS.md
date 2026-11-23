# Combat reach: how should blows register in play? (options for the owner, 19 Nov 2026)

Owner question: "1997 ranges or drawn contact?" This page lays out the choices with numbers measured in the game. Nothing here
changes behaviour: PR #160 ships the physical play layer with its hit parts OFF (`Hits`, `CreatureReach`), so today every blow is
decided by the 1997 box test (`RunThroughTagList`, dink.cpp:15460-15527). Walking collision, pickups and creature bodies already
follow the drawn shapes (parts Collision, Touch, Bodies).

## Why it matters
The 1997 boxes are pixels at the layout scale of each region (about 4-10 cm a pixel), while the photoreal creatures are drawn at
real size. A 1997 fist registers when Dink stands within 28 px (plus 5 px slack) of the target's hardbox, in the direction he
faces; a sword (sp_range 40, `item-sw1.c`-`item-sw3.c`) within 40 px. In the photoreal world that is metres from the drawn body.

## Measured: how far from the drawn body a 1997 blow registers
`dink.PhysicalPlayReach` (PR #160) in the rendered game, 19 Nov 2026, master f47439908 + #160. For each live creature: the farthest
spot straight in front of it (four facings) where the 1997 blow box still holds Dink, as the gap between Dink's capsule surface
and the creature's drawn body box (cm). "At Dink" is the other way round: the creature's own blow (its sp_range) against Dink.
Raw lines: `DinkRemasterUE/Docs/Verification/PhysicalPlay_19Nov2026/reach_review.txt` (on the #160 branch).

| creature (screen) | drawn body | Dink's fist | Dink's sword | its blow at Dink |
|---|---|---|---|---|
| pillbug `en-pill` (438) | 1.85 x 1.15 m | 3.7-3.9 m | 4.8-5.0 m | (touch damage only) |
| pillbug `en-pill1` (237) | 1.85 x 1.15 m | 2.3-2.4 m | 3.1-3.2 m | (touch damage only) |
| bonca `en-bonc` (29) | 0.94 x 2.60 m | 2.0-3.5 m | 2.7-4.2 m | 1.9-3.1 m (range 0) |
| bonca `en-bonc1` (302) | 0.94 x 2.60 m | 2.5-3.8 m | 3.3-4.5 m | 2.0-3.0 m |
| goblin soldier `en-gs` (713) | 1.55 x 1.16 m | 3.9-5.0 m | 4.9-6.2 m | 4.2-4.7 m (range 35) |
| hammer goblin `en-gh` (712) | 1.17-1.55 m | 3.9-5.1 m | 4.9-6.3 m | 3.8-4.5 m (range 0) |
| stone giant `en-stg` (178) | 2.10 x 1.85 m | 2.0-6.4 m | 2.7-7.4 m | 4.2-5.3 m (range 60) |
| dragon `s7-drag` (124) | 6.71 x 5.76 m | 0.4-1.9 m | 1.1-2.8 m | (touch damage only) |
| slime `en-slim` (192) | 0.99 x 0.64 m | 2.3-3.1 m | 3.1-3.8 m | (touch damage only) |

The same creature differs by region (pillbug 3.8 m on 438, 2.3 m on 237): the layout scale differs, the drawn size does not.
For comparison, the layer's drawn reach (`authored.ini` `AttackReachCm` 85 x range / 28): fist 0.85 m, sword 1.21 m, in front of
Dink's capsule. The bow is not affected by any option: arrows are missiles that fly as sprites and hit by the 1997 boxes.

## The options
| | rule | what it looks like | probe bot with the layer on (all twenty chapters) |
|---|---|---|---|
| (a) | 1997 boxes for everyone (PR #160 as merged: Hits, CreatureReach off) | Blows land 2-6 m from the drawn body (table). Fights play exactly as 1997 in balance and timing. | **completes 20 of 20** (19 Nov run) |
| (b) | drawn contact for Dink only (Hits on, CreatureReach off) | Dink must close to 0.85 m (fist) / 1.2 m (sword); creatures still hit him from 2-5 m. | **fails**: chapter 1 stops at step 27 of 47 (the Bonca fight in the cave: it out-reaches Dink's fist by metres and kills him; code-collision run it3, 16 Nov). Not run on every chapter. |
| (c) | drawn contact for both sides (Hits and CreatureReach on; the 16 Nov WIP) | Contact brawls: both close to touching. | **fails 4 of 20**: chapters 1 (Jack, step 37), 8 (a goblin kills Dink, step 1), 12 (two dragons, step 3), 17 (duck-bugs, step 3); 3-7, 11, 14-16, 19, 20 complete (run it6/it8, 16 Nov). |
| (d) | middle rule: the 1997 box test AND within a weapon length of the drawn body, for both sides (reach = 85 cm x max(range, 28) / 28: fist 0.85 m, sword 1.21 m, goblin range 35 1.06 m, slayer/Mog 45 1.37 m, giant 60 1.82 m) | 1997 who-hits-first order kept (every blow still needs the 1997 box), but no blow from metres away. | **not built or run yet** (estimate: between (a) and (c); the bot's 1997 positioning would need the pickup-style step-in for blows that (c) already has). |

Touch damage (pillbugs, slimes, dragons) is already drawn in all four (part Touch): it lands when the creature's drawn body touches
Dink (5 cm), and the creature body box stops Dink at its drawn front.

## Recommendation
Ship (a) now (it is what PR #160 does) and, if the owner wants blows to look like contact, build (d) as a new part and prove it the
same way (the probe bot completes all twenty chapters with it on, fights compared in rendered runs). (d) keeps the 1997 balance
between Dink and each creature because both sides keep the 1997 test and both lose the same long reach; (b) breaks that balance
in the creatures' favour and (c) turns fights into brawls the bot already loses in four chapters. The dragon shows the reverse
problem: its drawn body is larger than its 1997 box, so under (b)-(d) its reach is not cut, only the small creatures' is.

## Decision (owner, 19 Nov 2026): (c), drawn contact for both. Built in PR #160 (21 Nov 2026): parts Hits and CreatureReach on;
the layer-on probe bot completes the chapters as listed in `DinkRemasterUE/Docs/Verification/PhysicalPlay_21Nov2026/README.md`.

## Decision needed (owner) (as asked on 19 Nov)
1. Keep (a), 1997 reach for everyone?
2. Or build (d) (a middle rule) and decide after its probe and rendered fights?
3. (b) and (c) are measured and not recommended.
