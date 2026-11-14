# Creature class binding: the pillbug on every placement (13 Nov 2026)

Before this change a creature was bound per origin ID only (11 placements in Stonebrook). Every other creature
placement showed its sprite card, and a sprite made by a script (a carcass, for instance) showed the greybox cylinder.
`Content/Dink/Data/Art/creatures.json` now has a `classes` list; its first row binds the sprite class `pillbug`.
Presentation only: collision, hardness, scripts, hits, touch and the random stream are untouched.

## Result

| `art_coverage.py --coverage <whole-world report>` | before | after |
|---|---:|---:|
| final | 4,760 | 4,914 |
| placeholder | 1,695 | 1,541 |
| cut | 152 | 152 |

154 rows turned from placeholder to final: the pillbug placements that no other manifest names. The running game
logs `DINK CREATURE CLASS ART OK: 160 placements of 1 classes shown by their creature (pillbug 160)`; the six more are
rows the audit counts as cut that still have an actor.

## How it was captured

Offscreen game (`Scripts/PhotorealQA/run_capture.sh`) with the scripts `Scripts/CreatureQA/make_scripts.py` writes.
"Before" is the same script with `-dpcvars=dink.CreatureClassArt=0`. Screens: SCR_527 (day, grass), SCR_030
(Darklands, bare ground), SCR_648, SCR_715 (the largest crowd), SCR_106 (interior).

## Sheets and what they show

- `before_after_1_live.jpg`: SCR_527 at the play camera and at the close camera. Before: a pixelated card. After: the
  animated pillbug with plates, legs and antennae, lit and shadowed by the scene.
- `walk_strip_close.jpg`: six shots 0.25 s apart at the close camera. The legs are in a different phase of the gait in
  every shot and the bodies turn towards their path. Bugs pass through the hero, as the sprites do.
- `before_after_2_kill.jpg`: kills on SCR_527. Before: the greybox cylinder of the script-made carcass sprite. After:
  the burst carcass with its blood pool; the pool is a decal, so it also stains the grass blades. One carcass is one bug:
  the live bug at the left of the upper right picture gives the size.
- `before_after_3_carcass_crowd.jpg`: kills on SCR_030 (bare ground: the pool with thrown streaks), the crowd on
  SCR_715, and a crop of a live bug.
- `overview_screens.jpg`: a fixed camera above SCR_527, 030, 648 and 715: every bug of the screen is the creature
  wherever its brain has taken it.

## Numbers from the capture logs

- Crowd on SCR_715, same run pair: 45.1 fps with cards, 43.3 fps with creatures (10 s each, machine shared with other
  jobs; a later quiet run gave 83 fps with creatures).
- Shown speed of the bugs: 0 to 15.2 m/s, leg cadence up to 10.1 cycles per second. The original moves a sprite 60
  pixels per second per speed point, which is 4.1 m/s per point at this world scale; the fastest bugs (`en-pill2`,
  speed 3, diagonal) are a blur of legs. This is the 1997 speed, not a defect of the binding.

## Carcass size (review of 14 Nov 2026)

The first version drew the carcass at the size the mesh was modelled: 4.0 m across with its pool, the shell heap about
3 m, against a live bug of 1.78 m. It read as several bugs piled up. The 1997 carcass sprite (sequences 141/143) is
46x35 pixels and the walking sprite 49x40, so the remains are the size of the bug. The corpse row now has `scale` 0.55
(shell heap about 1.6 m) and its decal 620 cm, so the pool keeps a reach of 3.4 m; the amount of blood is unchanged.
The kill sheets above are from the corrected row.

## Left as it is, and not checked

- SCR_106 (interior): both camera positions ended behind a wall, so no bug of that screen was seen in a picture. The log
  lists its bugs as followed.
- Motion was judged from stills 0.25 s apart and from the logged speed and cadence. No video was reviewed, so
  frame-to-frame smoothness was not seen by eye; `Dink.Art.CreatureClass` tests the smoothing maths.
- The dark green pixelated card on SCR_715 in the overview is another sprite class, outside this change.
- The carcass was made bloodier than the first version on the owner's order of 13 Nov 2026. Its bright pool reads a
  little flat where sunlight hits it.
- A packaged build was not made (`Scripts/package.sh` default cook dirs may lack `Content/Dink/Photoreal`).

## Tests (private project copy)

- 14 Nov 2026, this branch on master `80ff12f1` (with the next creature batch on top of it in the same build):
  `Scripts/test.sh Dink.Gameplay.Probe` 29/29, and all twenty trace hashes equal the table re-baselined by PR #107
  (`Plugins/DinkParity/Docs/packaged_probe.md`): Ch1 b4ad88c02c, Ch2 bc267a0dfc, Ch3 bbd401167c, Ch4 8740518c57,
  Ch5 d987c043f6, Ch6 2df37e4a27, Ch7 a16d1d23b8, Ch8 764e9d330f, Ch9 dd1e2662fa, Ch10 23fd57dfdc, Ch11 0d70cebfcd,
  Ch12 79c8ce55f9, Ch13 98a2e17ba0, Ch14 f1ddbaab7b, Ch15 7e3dbbd0b1, Ch16 48e797069a, Ch17 4277c65c35,
  Ch18 d33886b797, Ch19 45b399bac8, Ch20 84f33687af. `Dink.Art` 64/64, `Dink.Animation` 6/6.
  Master has since taken PR #103 and #106 (corpse kit, ground); the probe was not run again on top of them.
- The same-screen restore fix (review of 14 Nov) was built on master `d2754903`; its test lines in `Dink.Art.CreatureClass` are reported in the PR.
- `python3 -m unittest discover -s Scripts/tests`: OK. `verify_sources.py --metadata-only`: passed.
  `Scripts/check_public_paths.py`: 0 files flagged.
- The layer is off in headless runs, so the probe cannot see it; `Dink.Art.CreatureClass.SimulationIdenticalWithAndWithoutTheLayer`
  compares every sprite property frame by frame with the layer forced on.
