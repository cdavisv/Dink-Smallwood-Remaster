# Corpse kit: remains bound with their gore (14 Nov 2026)

The owner's rule: keep all the original gore and dark comedy. PR #90 left the dead dragon and the dead knight as sprite
cards because the meshes were cleaner than the 1997 pictures, and the posed human bodies could not be imported at all.
This step rebuilds them with the gore inside the mesh (`SourceAssets/Art/PhotorealPass/Corpses/`) and binds them in
`Content/Dink/Data/Art/families.json`. Visual only: collision, hardboxes, scripts and origin IDs are untouched, and no
C++ changed.

## Result

| | before | after |
|---|---:|---:|
| `art_coverage.py` final | 4,335 | 4,346 |
| placeholder | 2,120 | 2,109 |
| cut | 152 | 152 |

11 placements of 8 families turned from placeholder to final (ledger: 149 -> 141 open families, 2,075 -> 2,064 IDs).
10 rows were added to `families.json`; they use 9 meshes, imported into `/Game/Dink/Photoreal/Corpses`
(`DINK_KIT=Corpses DINK_KIT_FOLDER=Corpses Scripts/import_town_exteriors.sh`: 18 materials, 9 modules, 0 warnings).

| Family | 1997 picture | Placement (screen) | Mesh |
|---|---|---|---|
| `corpse_knight` | 275 | S157_P04 | `SM_Corpse_Knight_PR` |
| `dragon_corpse` | 212 | S100_P34, S238_P12 | `SM_Dragon_Corpse_PR` |
| `dragon_corpse` | 216 | S158_P07 | `SM_Dragon_Corpse_PR`, turned 180 degrees |
| `corpse_merchant` | 345 (blue) | S094_P01 | `SM_Corpse_Merchant_PR` |
| `corpse_merchant` | 385 (green) | S092_P01 | `SM_Corpse_Merchant_Green_PR` |
| `corpse_girl` | 335 | S222_P04 | `SM_Corpse_Girl_PR` |
| `corpse_peasant` | 415 | S222_P05 | `SM_Corpse_Peasant_PR` |
| `corpse_maiden` | 245 | S091_P21 | `SM_Corpse_Maiden_PR` |
| `corpse_soldier` | 405 | S086_P01 (scripted) | `SM_Corpse_Soldier_PR` |
| `dink_dead` | 436 frame 16 | S058_P06 (scripted) | `SM_Dink_Dead_PR` |

## What a mesh of the kit is

One static mesh, two material slots. Slot 0 is the body on one baked 2048 px atlas: the posed source of
`PhotorealPass/Unclaimed`, soaked in blood and gashed (people), run through by the snapped halberd (knight), or cut open
with ribs, backbone, raw muscle, entrails, a torn-off wing and thrown chunks (dragon, built at the size of the sprite,
not of the living dragon). Slot 1 is an alpha-tested card 6 mm above the ground with the pool, the thrown drops and
the mist. A family row places one mesh and nothing else, so the pool has to be in the mesh: a companion decal would
never be drawn. `Scripts/tests/test_corpse_kit.py` fails when a body is bound without its pool card.

## How it was judged

Every row was captured in the running game, offscreen (`Scripts/PhotorealQA/run_capture.sh`, 1280x720): `dink.Goto`
to the placement, `dink.CalAnchor 0 0`, then two fixed cameras with `dink.CalCam`, one at about the play camera
(6.5 m back, 5.2 m up; the sheets crop its middle 2.2 times) and one close (3 m back, 1.9 m up). The same script ran
first with master's `families.json` for the "before" columns. The first column of every row is the 1997 picture
(`ImportData/sprites/<seq>_<frame>.png`, enlarged, on green). Nothing was retouched.

| File | What it shows |
|---|---|
| `before_after_1_knight_dragon.jpg` | The knight (157), the dragon of picture 216 (158) and of picture 212 on grass (238) and in the dark (100). |
| `before_after_2_people.jpg` | Both merchants, the girl, the peasant, the woman in red, the soldier, Dink. |
| `first_palette_red_paint.jpg` | The same two close cameras with the first blood colours (left, not shipped) and the ones in this change (right). |
| `tried_and_left_unbound.jpg` | The mother (screen 1), three blood sprays and two burn holes with trial rows: "after" is what those rows drew. |

What I see, picture by picture:

- **Knight (275).** 1997: dark armour on its back in a pool wider than the body, the pole standing in the chest, the
  halberd head beside him, drops round the pool. Game: the same elements, the pool lobed and wet with a dark middle,
  drops and cast-off lines round it. The armour is the source knight's: smooth and clean apart from baked streaks, it
  reads a little like a toy next to the ground. More gore than the card it replaces (which shows a strip of the
  picture); the pool is in the mesh.
- **Dragon (216, 212).** 1997: a carcass torn open, red flesh in blocks, one wing off, the tail arched, drops thrown.
  Game: hide torn open over a rib cage and backbone, raw muscle, loops of gut, a wing lying beside it, chunks thrown
  clear, a wide pool. The muscle is lumpy rather than anatomical (a displaced mass, no muscle groups), and the wing
  panels are flat. On the dry earth of screen 158 the whole of it shows.
  **On the grass of screen 238 the pool card is hidden by the grass carpet**: flecks of red between the blades is all
  that is left of it; the body, the ribs and the thrown flesh show. Picture 212 has flesh and drops but no pool, so I
  judged this not less gory than the picture; it is less than the mesh has. Screen 100 is nearly black in both columns
  (a dark screen): the remains are there, I could not judge them.
- **People.** 1997: bodies red from head to foot in a pool, drops round them. Game: clothes and skin soaked and wet,
  slashes on chest and belly, each in its pool. The slashes are relief on the surface, not cuts into the body: no bone
  or organs on the people. The woman in red and the soldier lie with a sharp-edged frozen skirt hem / jerkin flaps
  from the posed source. The pool of the woman in red lies mostly to one side of her.
  Dink (436) is the least bloody, as his picture is: blood on chest and face, the pool under him.
- **Size.** Bodies keep their real size (`fit: none`): a person is about 1.8 m in a pool of about 3 m, the knight in
  3.2 m, the dragon remains about 2.6 m in a 4.9 m card. Against the sprite cards in the "before" column they are the
  same order of size or larger; the cards themselves stand half sunk in the ground, so this was judged by eye, not
  measured.
- **Blood colour.** These screens are exposed bright. The first palette was right in the Blender render and too light
  in the game; the second is darker (pool middle about 90 of 255 on screen, rim lighter). In direct sun the thin rim is
  still a vivid red.

## Left unbound

- **`corpse_mom`** (S001_P34, screen 1, vision 1). A trial row drew nothing: the card stays (sheet, first row).
  Screen 1 is a dressed screen. Row and asset were taken out again.
- **`blood_splat`** (46 placements) and **`burn_hole_decal`** (26) as family cards. Tried with alpha-tested ground
  cards: the blood came out as one small flat splat, smaller and plainer than the 1997 spray it replaces; the burn-hole
  rows drew nothing (where a burn hole shows in the game it is already a deferred decal of `environment.json`). Not
  better than the sprite, so not bound; cards and rows were removed. These two families belong to the deferred decals.

## Checks

- `python3 -m unittest discover -s Scripts/tests`: 847 tests, OK (with the new `test_corpse_kit.py`).
- `Scripts/test.sh Dink.Art`: 58/58 passed (private copy, rebuilt from this branch's source, kit imported).
- `Scripts/scrub_private_paths.py --check`, `tools/lfs_audit.py HEAD`, `Scripts/verify_sources.py --metadata-only`: results in the PR text.
- The probe was not run: no C++ and no gameplay data changed (family rows are presentation only).

## Not checked

- Screen 100 (dragon, picture 212): too dark in the capture to judge.
- The scripted placements (soldier on 86, Dink on 58) were looked at standing; their scripts (talk, then the sprite is
  removed) were not played.
- The live play camera with the player walking round the remains: not looked at. Captures are
  from the editor's game mode in a private copy whose generated world is of 12 Nov.
- A packaged build: `Scripts/package.sh` cooks `Content/Dink/Photoreal` since PR #102, so the kit should be in it, but no package was made here.
- Night or interior lighting other than screen 86.
