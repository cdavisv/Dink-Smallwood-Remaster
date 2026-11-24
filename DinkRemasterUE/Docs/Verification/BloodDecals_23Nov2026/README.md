# Placed blood as picture decals, on the raised ground (GP-Q6), 23 November 2026

Branch `art/blood-picture-decals`, one commit on master e37f11e42. **Seen in the running game on 23 November 2026**
(four capture rounds; sheet `blood_ingame.jpg`). The placement code ran in the game for the first time in round 1.

## What was wrong

- The 1997 map places 46 blood splats (sequences 187 to 189; screens 60, 61, 91, 94, 122, 126, 154, 158, 190, 191). All are
  background placements (editor type 0), which the greybox draws as instances. `ApplyDecals` replaced actor placements only,
  so every one of them was still the standing pixel card.
- The decals drawn from those very pictures (`Corpses/Decals`, `MI_Decal_Blood1997A_0..3`, `B_0..3`) have been in the tree
  since 16 November, but no row bound them.
- Since the landforms (#153) a decal lay at the height of its holder's own point with a box 40 cm deep. All 46 splats are on
  screens with relief; under 15 of them the ground differs by more than 15 cm across the decal's footprint, up to 1.2 m
  (measured from `landforms.png`).

## What changed

- `environment.json` `decals.blood_splat.pictures`: the eight placed frames (187/1, 187/2, 187/3, 188/2, 188/4, 189/1,
  189/2, 189/4) each name the decal drawn from that picture.
- `UDinkEnvironmentSubsystem::ApplyDecals`:
  - background placements: a decor component (one sprite frame of one screen) is hidden and one decal per instance is laid,
    when every instance in it is an unscripted placement of one decal class that no art manifest and no state swap handles;
  - a picture decal takes the square of its card x 1.15 (`CardDecalSquare`, from #140) and is not turned, so the drops lie
    where the 1997 picture had them; it is never smaller than the card (0.60 m to 3.91 m across here);
  - `DecalGroundFit`: every ground decal (blood and burn) lies on the landforms' ground under its own middle and its box is
    18 cm deep plus the largest height difference under its footprint (at most 90 cm). The card is taken back to the flat
    floor first (`DinkLandforms::ActorLiftCm`; new const accessor `UDinkLandformsSubsystem::DecorLiftCm`);
  - instance decals open the grass carpet (`OpenGrassUnder`, from #140);
  - since the first look in the game: a ground decal is TILTED onto the slope. `DecalGroundFit` gives the normal of the
    plane through the ground at the footprint's four edge middles (at most 50 degrees from upright) and measures the box
    depth from that plane; projected straight down, the drops of `S094_P06` on a bank were drawn out into streaks.
- The sheets `Corpses/Decals/T_Decal_Blood1997A/B` are drawn again in the one blood look of the remains
  (`Corpses/tools/gore_sheets.py`, `blood_sheet(look='fresh', **FRESH_1997)`; PR #216 carries the identical file): the
  bright 1997 red only as a thin film at the edge of every drop, a darker body, deep crimson where a splat is thick,
  domed wet cores, the outline bent and frayed so no rounded square of a 1997 pixel is left. Area per cell is still at
  least the picture's (`decals.json`).
- `Scripts/art_coverage.py` `env_decal_cards` mirrors the rule: those placements count as final.
- `Corpses/tools/review_decals.py`: the review renders below.

No new art asset. The simulation is not touched (visual only; the probe traces are equal to master's).

## What I saw in the game (`blood_ingame.jpg`; `Scripts/PhotorealQA/run_capture.sh`, 960x540, 14 placements x four cameras)

Copy of master `6e3d4f991` + this change (with #215 and #216), clean build, corpse kit imported headless; four rounds on
23 November (frames `gore3/blood`, `gore4/blood2`, `gore4/blood4` of the capture copy; the third round was skipped).

- **The placement code works.** Every round the game's log (`Saved/PhotorealPass/lighting/tools/capture.log`) holds
  `DINK ENV: N ground decals on screen S` with 2 / 2 / 15 / 7 / 3 / 4 / 6 / 1 / 4 / 2 on screens 60 / 61 / 91 / 94 / 122 /
  126 / 154 / 158 / 190 / 191 = all 46 splats (and 3 + 2 burn decals on 533 / 536), no crash line, kernel taint 0.
- **Where they lie**: on the ground, none floating and none sunk (side views), each a little south of its placement's
  point, where its card stood. The band of drops runs east-west with the fine spray north of it, as the sheet has it:
  not turned by 90 degrees any more (the 16 November fault). East and west cannot be told apart by eye on pictures this
  symmetric; they follow from the decal's own axes (U = local Z = east, V = local Y = south after the pitch of -90).
- **Round 1 fault, relief**: `S094_P06` lies on a bank; projected straight down its drops were drawn out into streaks.
  With the tilt (rounds 2 to 4) they are round drops lying on the slope (row 3 of the sheet).
- **Round 1 fault, colour**: one flat bright poster red beside the darker hit blood and corpse pools. Rounds 2 and 3
  (body sRGB 132 and 100) were still clipped to that red by the sun. Round 4, in this change (thin 128 / body 80 /
  deep 38): crimson splats with a brighter rim on every drop, dark where they are thick (the two large 187 splats of
  screen 94), the same family as the hit-blood star and the pool of the corpse beside them.
- At the play camera (row 1, left) a splat is a small red mark on the ground of the size of its 1997 picture; close up
  it is drops and sprays, not a cut-out of pixels.
- Grass: all 46 splats lie on the bare earth of the Darklands screens, so the clearing of an instance decal is not seen
  in these frames; the burn decal of 536 (an actor decal, master's behaviour) keeps its clearing in the grass.

Before the game was allowed (Blender, Cycles on the CPU): `blood_vs_1997.jpg` shows the FIRST sheets beside the eight
pictures; `game_16Nov_old_base_blood.jpg` the only earlier game frames (16 November, old base, turned by 90 degrees).

## What I rejected

- **Burn holes (158) as picture decals** (`burn_pictures_not_taken.jpg`): the `Burn1997` sheets are flat grey-black blots,
  rounded lobes where 158 has rays, no char and no embers. The rows are not in this change; burn holes keep the class cells
  of `Props/Decals` that master shows (rows 2 and 4 of the sheet).
- **Ground holes as decals (VS-08)** (`hole_sheets_rejected.jpg`): the sheets drawn on 15/16 November for the cracks
  (89/1-4), the pit (89/9) and the cave mouths (89/10). The crack is a thin dark ribbon without the brown rock walls of the
  picture, the pit a grey-black blob (a lit black decal is grey: a decal cannot take the ground's specular away), the cave
  mouth a flat dark rhombus with faint stripes that reads as a mat lying on the grass. The camera is a free third-person
  boom, so painted depth cannot hold. None of it is in this change (no sheets, no rows, no importer change). What they
  need: the `pit` material (parallax, no specular; in the game on mesh cards since #198) on something that follows the
  ground, or an opening in the landforms mesh. Relief under the 25 hole placements is up to 1.2 m, so flat cards would
  float or be buried.

## Below the bar, known

- The drops are soft rounded blobs with sprays drawn by rule, not photographed spatter with tails.
- From a very low camera (60 cm) a splat is a pale glossy film of sky; the game's camera does not go that low.
- On the steep sunlit bank of screen 94 some drops show a pale rim.
- 512 px per cell: the largest placements (3.9 m) show 0.8 cm texels.
- Known limit: a decal on the screen actor does not follow `dink.Landforms 0` switched at run time.
- Found on the way, not this change's art: the burn cell on screen 536 (master's `Props/Decals` class cell) reads as a
  pale grey cracked slab on the grass (`gore3/blood/burn536_top.png`); told to the effect stream in the Master log.
- `dink.Goto` onto a splat that lies on a bank (S094_P06) puts Dink under the raised ground with the game camera below
  the surface (a capture artefact of teleporting onto unwalkable ground; told to the code side).

## Tests

Headless, 23 November 2026, in one private copy = master `e37f11e42` + the three gore changes together (this one, #215 and #216),
each as its one commit: every tracked source, data and kit package file of the tested tree equals the copy (0 differ), the
packages are the committed ones and every other package of the two kits equals master's.

- Binaries: clean build (`Intermediate` removed) of master `6e3d4f991` + these trees, 0 warnings; `e37f11e42` changes no
  C++ against that (0 files), and the C++ of the tested tree equals the built one (0 files differ).
- Kit imports, headless (`-nullrhi`): Corpses `DINK TOWN IMPORT OK: 26 materials, 15 modules, 0 warnings`,
  Structures/Stonebrook `DINK TOWN IMPORT OK: 9 materials, 15 modules, 0 warnings`.
- `Scripts/test.sh Dink.Art`: 81/81 passed. `Scripts/test.sh Dink.Gore`: 11/11 passed.
- `Scripts/test.sh Dink.Gameplay.Probe`: 29/29 passed; all twenty chapter md5s equal the table of
  `Plugins/DinkParity/Docs/packaged_probe.md` on master (Ch1 cff64df9d1 .. Ch20 b27010b31e).
- `python3 -m unittest discover -s Scripts/tests`: 1051 tests OK (in the copy).
- `scrub_private_paths.py --check` clean, `check_public_paths.py` 0 flagged, `verify_sources.py --metadata-only` passed.
- Kernel log: 0 Oops in all rendered and headless runs of the day.
- `Dink.Art.PictureDecal.*` (in the 81): the card square, the ground fit incl. the tilt onto a bank and its cap at a cliff, every
  decal material of `environment.json` loads as a deferred decal.
- Art coverage with the decal rule (run on 78867e7bc + the first version of this change): final 5670 / placeholder 785 / cut 152;
  master then 5616 / 839 / 152 (the 46 splats, 7 burn-hole actors that were decals already, 1 burn-hole instance).
- What the headless tests do NOT run: the environment layer returns early when nothing can render, so the placement code of
  `ApplyDecals` itself is exercised only by the rendered captures above (four rounds, 46 decals each).

## Not checked

The world was not regenerated for this run (the copy's generated world dates from master `9ada93f1a`; the equal probe
traces show it plays as master's). The full `Dink` suite. Windows, Shipping, a packaged build.
