# A80: the magic potion of the SCR_069 chest (16 Nov 2026)

Bug A80 (S2): after the punch that opens the small chest S069_P02 (`ch1-mp`), the magic potion it drops was not
collected, also with Dink "standing on it" (`Docs/Verification/PresentationFixes_15Nov2026/`, run 2).

## Cause: QA coordinates, not the game
The console tools that drove that run speak MAP pixels: `dink.Goto`, `dink.WalkTo`, `dink.Player` and `dink.Sprites`
(`UDinkDirector::PixelToWorld` subtracts 20). map.dat, `placements.csv` and DinkC's `sp_x` speak ENGINE pixels, which
include the 20 px status bar (dink.cpp D:494-498, the hit map is written at `x - 20`). The run took the chest's
map.dat x (323) as a map pixel, so Dink stood at engine x 343 at the punch and 348 at the "standing on it" step: 20 and
25 px east of the potion at engine 323,204.

What the original does there (all lines `source/dink/dink.cpp`):
- `make.mpotion`: `&save_y += 1; create_sprite(&save_x, &save_y, 6, 178, 4); sp_script(&crap, "ppotion")`.
  `add_sprite_dumb` (D:3089) gives frame 0 and the picture 178/4; `ppotion` main sets touch damage -1, `sp_seq 57`
  (no `sp_frame`) and brain 6.
- The forward animator starts a frame-0 sequence at frame 1 (D:17008-17015); `getpic` (D:443-453) is then 57/n, whose
  hardbox (dink.ini `botl-p 57 ... -12 -9 9 7`) is the same on all 14 frames.
- `run_through_touch_damage_list` (D:15629-15680) runs `touch` while Dink's point is inside that box + 2 px
  (D:15645-15648): engine x 309..334, y 193..213 for the potion at 323,204. Engine x 343 and 348 are outside; the
  remaster adds Dink's capsule radius in pixels (5 px on SCR_069: x 304..339) and is outside as well.
- The other two chests of the run worked by width alone: the gold of 557 (178/4, -20..27) and the golden heart of 282
  (53, -22..24) reach 20 px east of their chest; the potion (-12..9) does not.

The remaster's touch path for this potion is the 1997 one (`UDinkGameplay::Animate`, `GetHardbox`,
`RunThroughTouchDamageList`): no gameplay change is made.

## Test
`Dink.Gameplay.Touch.ChestMagicPotion` (`DinkGameplayTests.cpp`, headless, the real scripts): enter SCR_069, punch the
chest from the reporting run's spot (engine 343,214), the potion appears at 323,204 with touch -1, brain 6, sequence 57
running and the 57 hardbox; at 343,214 and at 348,206 it is not collected (as in 1997); in front of the open chest
(323,210, just south of the chest's hardness rows 189-208 that `add_hardness` stamps, where the 1997 Dink stops) `&magic` goes 0 -> 1 once and the potion
shrinks away (brain 12).

## Rendered check on SCR_069 (16 Nov 2026)
Private copy at master `0b0a39ed` + this branch (test-only), built (`Scripts/build.sh`, 0 warnings), world from the
presentation-fixes copy (regenerated, same importer). One `Scripts/PhotorealQA/run_capture.sh` run (offscreen Vulkan,
`-nosound`, no X display), script `run1_capture.txt`, log excerpt `run1_log.txt`, frames `run1_sheet.jpg`
(left to right: the reporting run's spot after the punch; walking north at the potion's map x; in front of the chest).
- `dink.Sprites` before the punch: the chest S069_P02 at map 303,203 (engine 323,203).
- Part 1, the reporting run's driving: `dink.WalkTo 323 207` stops at map 323,214 (engine 343): the punch opens the
  chest (`S069_P02 follows its animation to 175/3`), `dink.Sprites` lists `ppotion brain=6 map=303,204`, magic stays 0.
  The frame shows Dink beside the chest and the purple flask at its front: 20 px (about 1.1 m) west of him.
- Part 2: walk south, west to map x 303, then north into the chest: sound 10 plays, `magic = 1`, the potion is gone
  from `dink.Sprites`; Dink stops at map 303,214 (the chest's hardness, his 28 cm capsule), inside the potion's touch
  box. The middle frame shows the flask at his feet, the last one the open chest without it.

## Same pattern elsewhere (scan of `bin/dink/story`)
Every script that drops a pickup through `external("make", ...)` or `external("emake", ...)`, with the picture the
item's main leaves and its hardbox (`frames.csv`). The pickups that set `sp_seq` without `sp_frame` (frame 0, as
`ppotion`) all go the same way as 069's potion: none is a game defect.

| Drop (item script) | Picture, hardbox | Callers and placements |
|---|---|---|
| magic potion (`ppotion`, make.mpotion, y + 1) | 57 from frame 1, -12 -9 9 7 | `ch1-mp` S069_P02 |
| strength potion (`rpotion`, make.rpotion / spotion, y + 1) | 56 from frame 1, -12 -9 9 7 | `ch1-sp` S184_P02, S209_P05; `bar-sp` S177_P03; `box2-sp` S742_P16 |
| defense potion (`bpotion`, make.dpotion, y + 1) | 55 from frame 1, -12 -9 9 7 | `bar-dp` S156_P05 |
| all-potion (`apotion`, make.apotion) | 75 from frame 1, -12 -9 9 7 | `ch1-ap` S395_P03, S536_P31; `ch3-ap` S536_P29; `ch2-ap`, `s3-ch1` (no placement) |
| small heart (`sheart`) | 54/1, -8 -8 10 4 | `bar-sh` (S060, S063, S096 ...), emake small/medium of the monsters |
| food (`sfood`) | 421/n, -19 -3 7 3 | `bar-f1`, `s4-duck` |
| gold (`mgold`, `papgold`, `gold500`) | 178/4, -20 -14 27 14 | `ch1-g` S288_P03, `ch1-pap` S005_P28 S557_P05 S747_P01, `ch2-500` S026_P06 |
| golden heart, heart (`gheart`, `heart`) | 53/1 -22 -12 24 10; 52/1 -25 -11 24 11 | `ch1-gh`, `ch2-gh`, `ch3-h`, `bar-gh`, `s4-sec1`, `s5-sec1`, emake large/xlarge |

The probe already collects three of the frame-0 potions in PIE (`DinkProbeTests.cpp`: the `apotion` of S536_P31,
S536_P29 and S395_P03, and placed `ppotion`s on 273, 597, 352) and its twenty traces are unchanged. A QA run that walks
to a placement's map.dat x as a map pixel misses every pickup whose box does not reach 20 px east (the potions, the
small heart, the food); gold and the large hearts reach it. AGENTS.md pitfall 83 records the two frames.

## Tests (same build)
`Scripts/test.sh "Dink.Gameplay.Touch+Dink.Gameplay.Probe"`: 32/32 passed, 0 failed (1 with warnings: the known
`ProbeLoadOracle.StockProjection` world-context log) in 551 s. `Dink.Gameplay.Touch.ChestMagicPotion` passes; the twenty
probe trace md5s equal the table in `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 b4ad88c02c ... Ch20 84f33687af):
no runtime file is changed, so nothing could move them.

## Not checked
- The other chests and barrels of the table in a rendered game (the same touch path; the headless test and the probe
  cover the frame-0 potions).
- The packaged build.
