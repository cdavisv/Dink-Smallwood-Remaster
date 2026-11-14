# Creature classes: the duck with its gore, slimes, pig (14 Nov 2026)

Second creature batch, on top of the pillbug (`Docs/Verification/CreatureClassBinding_13Nov2026/`). Five rows are added
to `classes` in `Content/Dink/Data/Art/creatures.json`: `duck`, `slime_blue`, `slime_green`, `slime_red`, `pig`.
Presentation only: collision, hardness, scripts, hits and the random stream are untouched; the layer is off in headless
runs.

## Result

| `art_coverage.py --coverage <whole-world report>` | before (with the pillbug batch) | after |
|---|---:|---:|
| final | 4,914 | 5,121 |
| placeholder | 1,541 | 1,334 |
| cut | 152 | 152 |

The total moved by 207 rows; the audit lists 206 class-bound placements (duck 91, blue slime 67, red slime 29,
green slime 11, pig 8). I did not trace the one row of difference. The running game logs `DINK CREATURE CLASS ART OK: 367 placements of 6 classes shown by their creature
(duck 92, pillbug 160, slime_green 11, slime_red 29, slime_blue 67, pig 8)`.

## The 1997 gore, and what stands for it

The remaster's simulation keeps the duck's state (a headless flag, base walk 110) and draws nothing of what the 1997
frames paint. The presentation layer draws it, with its own random numbers:

| 1997 (dink.cpp, sprite sequences) | Here |
|---|---|
| First hit: a head sprite flies off along the duck's direction, lands in a pool and stays until the screen is left (duck_brain 12745-12775, sequences 121-129) | `SM_Duck_HeadFlying_PR` is thrown from the neck, spins, and lands as `SM_Duck_Head_PR` with a puddle decal |
| The body runs on headless; every frame of sequences 111-119 shows blood spraying from the neck | `SK_Duck_Headless_PR` (bloody stump), a fountain of blood drops from the neck bone that keeps the body's speed, and stains on the ground along the way |
| Second hit: the burst of sequence 164 and the duck is gone (12728-12740) | 160 drops thrown up and out, and a burst stain on the ground |
| A killed slime leaves the splatter of sequences 661/663, 681/683, 701/703 | blobs of its gel and a splatter decal of its colour |
| A killed pig becomes the burst of sequence 164 (pig_brain 13367-13382) | 260 drops and a burst stain |

Nothing is less bloody than the sprite. The owner's order of 13 Nov 2026 for the duck was "have it spray a fountain
from the neck".

## How it was captured

Offscreen game, `Scripts/CreatureQA/make_scripts.py --hurt`: a review blow (`dink.Hurt`) on a named placement, the game
slowed to a tenth, the camera aimed at the creature again before every shot (`dink.CalAnchorOrigin`), because a duck
covers 6 to 8.5 m a second. Times in the labels are game time.

## Sheets and what I see in them

- `duck_1_first_blow.jpg`: the head leaves the neck and flies up (white head, yellow bill, red at the cut). The body
  runs on with a bloody stump, wings working; a plume of drops rises from the neck and arcs behind it.
- `duck_2_second_blow_and_live.jpg`: the burst (drops in the air), the stain it leaves on grass (rust red on the
  blades) and on bare ground (a red splash with thrown drops; that picture is from an earlier run with a glossier
  stain), and live ducks at the close and at the play camera.
- `slime_pig.jpg`: blue and red slimes around the hero with the splatter of a killed one, green slimes in an interior,
  and the stain of a killed pig.
- `pig.jpg`: the pig at the play and close camera on SCR_636 (class row) and in the Stonebrook pen on SCR_407 (origin
  rows, the same mesh through `dink.PhotorealPig`).

## Found on the way and fixed

- Ducks were specks at the play camera at their modelled 0.51 m. The 1997 duck is 31 px long beside a hero of about
  65 px; the row's `scale` is 1.5 (0.77 m).
- The run clips cover half a metre a second, a duck here moves 6 to 8.5. `Duck_Scurry` and `Duck_HeadlessScurry`
  (`Creatures/Tools/duck_scurry.py`) are declared for 800 cm/s.
- Ground decals coloured the hero's legs to the knee. They are sunk 25 cm now (soles and grass tips only). This also
  applies to the pillbug's pool.
- Stains with roughness 0.12 mirrored the sky on grass blades and read grey; they are 0.5 now.
- The slime splatter blobs rendered black with the living slime's atlas; they have their own gel material per colour.
- The pig's body was calmed after the review "lumpy" (`pig.py`: less surface noise, shallower hollows and neck folds,
  one rounded rump). Blender renders before and after: `Creatures/Pig/Review/final_*.png` and `r9_*.png`.
- QA item A6: `UDinkCreatureComponent` (the origin rows) measured its speed a frame late and from whole pixels. It
  ticks in `TG_PostUpdateWork` now and drives the animation with a quarter-second average.

## Weaknesses that stay

- The blood drops are flat bright red flakes in sunlight; the stains on grass are weak (a rust tint on the blades).
- The duck's feather cards give its outline a jagged, pixel-stepped edge at this capture size.
- The slime gel is opaque and its colours are pale beside the sprites (lilac, salmon, mustard). The see-through
  material of the source notes is not built.
- At 6 to 8 m/s every small creature here scurries; that is the 1997 speed at this world scale.
- A headless duck that a script removes (not the second hit) would also burst; no such script was found.
- One pig placement has duck_brain; hit once it would turn into a headless duck in 1997. Here it stays a pig.

## Not done, not checked

- The 90 `duck_head` placements on SCR_145 and the `duck_corpse` placement are not bound.
- No before pictures from the game for this batch (the 1997 sprites are on the sheets instead).
- The A6 change was built and passes the tests; it was not measured with a trace or judged in a picture.
- The living green slime outdoors, the slimes' attack, and the head lying in its pool at rest were not looked at.
- Smoothness was judged from stills. No video, no packaged build.
- Tests: `Dink.Art.CreatureClass` 5/5, `Dink.Gameplay.Probe` 29/29 with the twenty hashes of the table of PR #107,
  `Dink.Art` 64/64, `Dink.Animation` 6/6 (night of 14 Nov, on master `80ff12f1`); `Dink.Art.CreatureClass` 5/5 again
  on master `d2754903`. The probe was not repeated after the last two small changes (stain roughness, drop colour:
  importer only) or on the newest master.
