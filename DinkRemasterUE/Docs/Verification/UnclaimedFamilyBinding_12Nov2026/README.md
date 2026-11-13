# Unclaimed families: import and family binding (12 Nov 2026)

The static meshes under `SourceAssets/Art/PhotorealPass/Unclaimed/` were sources only. This step imports the ones that
can be bound and binds them in `Content/Dink/Data/Art/families.json`. Visual only: collision, hardboxes, scripts and
origin IDs are untouched.

## Result

| | before | after |
|---|---:|---:|
| `art_coverage.py` final | 3,785 | 3,976 |
| placeholder | 2,670 | 2,479 |
| cut | 152 | 152 |

191 rows turned from placeholder to final: 187 placements of 34 families and 4 script warps hosted by them.
43 rows were added to `families.json`; they use 36 meshes, imported into `/Game/Dink/Photoreal/Unclaimed`
(`DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh`, 36 materials, 0 warnings).

Placements per family: hand_tool_small 30, seashell_conch 29, gold_pile 15, dragon_statue 13, food_fruit 11,
save_machine 10, bookcase 9, small_heart 8, snake_pillar 7, golden_heart 6, pitchfork 6, idol_statue_small 5,
island_spear_pole 5, dragon_corpse 3, rake 3, shop_sign 3, teleport_shrine 3, fountain_stone 2, scythe 2,
spinning_wheel 2, teleport_machine 2, and one each for axe_item, ballista, barrel_broken, boulder_white_pair, catapult,
corpse_knight, dink_monument_rock, food_drumstick, gold_coins_small, golden_duck_statue, heart_pickup, scroll_note,
snake_carving.

## How it was judged

Every candidate was bound in a trial `families.json` and captured in the real game, offscreen
(`Scripts/PhotorealQA/run_capture.sh`, 1280x720): the player is sent to the screen with `dink.Goto`, `dink.CalAnchor`
puts the origin on the placement and `dink.CalCam` gives two fixed cameras, one at about the height of the play camera
(6.5 m back, 5.2 m up) and one close. The same cameras were then captured with master's `families.json` for the
"before" column. Vision-gated placements were shown with `dink.Vision`. Nothing was retouched.

| File | What it shows |
|---|---|
| `before_after_1_small_props.jpg` | Conch, hand tools, fallen fruit, ham, gold heap, coin scatter, the three hearts. |
| `before_after_2_furniture_statues.jpg` | Bookcase, dragon statue, save machine, snake pillar, idol, fountain, spinning wheel, teleport machine, ballista, duck statue. |
| `before_after_3_outdoor_and_remains.jpg` | Healer's sign, spear pole, dragon and knight remains, burst barrel, throwing axe, pitchfork, rake, scythe, snake carving, boulder pair. |
| `after_only_vision_gated.jpg` | Catapult, the "Dink Smallwood" rock, teleport shrine, the letter on the floor (after only). |
| `pickup_touch_small_heart.jpg` | A small heart before and after the hero walks onto it. |
| `tried_and_left_unbound.jpg` | Trial bindings that were rejected, with the reason. These rows are NOT in `families.json`. |

## What I see

- **Large things are a clear gain.** A bound statue, machine, bookcase or fountain replaces a sprite card that the
  layout scale had blown up to 5 to 18 m with a mesh at its real size.
- **Small things get much smaller.** The original draws small objects two to four times too big so they can be read.
  At real size a 14 cm shell or a tool on the floor is easy to miss from the play camera. That is the convention of
  every earlier row (`fit: none`).
- **Outdoors, flat tools vanish in the grass.** Five hand tools and six farm tools (pitchfork, rake, scythe) lie on
  grass screens; the grass carpet covers them completely. Indoors they read correctly.
- **Pickups are scaled to the sprite.** The three heart families and the small coin scatter use `fit: footprint`, so a
  heart is 0.4 to 0.8 m as the original draws it. At 11 cm it could not be seen, and a pickup has to be found. The
  coins then show their ten-sided rims close up.
- **Static where the original animates:** save machine, teleport machine, hearts.
- **Weak meshes that were bound anyway** because they read correctly at the play camera: the gold heap (a dome close
  up), the idol and the duck statue (fused forms), the dragon remains (not torn apart), the burst barrel (no hoops),
  the snake carving (reads as a snake, not as stone). The pale dragon statue is not the blue-grey of the sprite.

## Left unbound, and why

The family layer stands a mesh on its lowest point at Z 0 under the card. That rules out:

- **Table tops and shelves:** fruit, bread, cheese, grapes, steak and one ham on the tables of screen 70; the bombs on a shop shelf.
- **Walls:** both posters, the red stripe of screen 97, ten arrows on display in the bow shop.
- **Below ground:** the cave hole, a pit whose shaft would stand on the ground as a box.
- **Crowns of trees:** the 34 tree fruit.
- **Buildings drawn in several sprites:** church, log cabin, snow house, castle door and drawbridge, with their doors,
  windows and stained glass. A real-size mesh leaves the door and window cards floating beside it; they need a
  per-screen assembly like the town houses.

Also unbound: the stairs (two of four pictures are floor openings), the cellar hatch (hidden by a wall module), the
single coin (4 mm thick; `Dink.Art.Family.ManifestMeshesExist` wants every side above 1 cm), the ore rock (scripted,
like every bombable rock), four of the five shop sign pictures (other emblems), and the boulder classes an earlier row
already binds. Not importable by the kit importer at all: the eight posed human bodies and the king on his throne
(hair, skin and eye materials), the 18 rigged assets, 18 decal sets and 6 flipbooks. Per family:
`SourceAssets/Art/PhotorealPass/Unclaimed/STATUS.md`, column "in game".

## Checks

All in a worktree of master dd60127d, with a reflink copy of the shared checkout's built project and world import.

- `Scripts/build.sh`: BUILD OK, 0 warnings.
- Import: `DINK TOWN IMPORT OK`, 0 warnings (first run with all 74 importable meshes; the 38 that no row uses were removed again).
- `Scripts/test.sh Dink.Art.Family`: 12/12. `Scripts/test.sh Dink.Art`: 58/58, 0 warnings.
- `python3 -m unittest discover -s Scripts/tests`: 822 tests OK.
- **Probe traces do not move.** `Scripts/test.sh Dink.Gameplay.Probe` was run with master's `families.json` and with
  the final one in the same checkout: 15/29 both times with the same fourteen failures (the regression already on
  master, not part of this change), and the seven traces that exist have identical md5 sums:
  Ch1 `b4ad88c02cde`, Ch2 `c88f756f9eca`, Ch3 `838adfb3ab9d`, Ch4 `54d8a76e0ad6`, Ch5 `61b022530fff`,
  Ch6 `a1c2c99e24e2`, Ch7 `39138a86db84`.
- **A scripted pickup still vanishes when touched** (`pickup_touch_small_heart.jpg`): the hero is walked onto a small
  heart of screen 101 with `dink.WalkTo`; its mesh is gone afterwards and the second heart is still there. The same
  walk onto a gold heap was blocked before it reached the heap, so gold is not shown.
- `python3 -I Scripts/scrub_private_paths.py --check`: clean after `--fix` on the 114 new texture packages.

## Not checked

Frame rate, the packaged build, the touch of a gold heap, and the screens 153 and 257/385: screen 153 renders as an
empty void in these captures and the two beach screens render very dark, with or without this change.
