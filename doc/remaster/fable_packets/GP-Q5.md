# GP-Q5: Finish and push the starting house's mother, burn holes, Milder and the dead Dink

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q5 (GORE_STORY_PARITY.md G11, G12, G14) |
| priority (queue) | high |
| estimated size | S (made, tested on 14 Nov; rebase, recheck, look, push) |
| stream | Stream B, gore and remains, step 1 of that stream |
| kind of work | mostly NOT new art: the meshes exist; rebase, re-run, one look judgement (mother darker than 1997), push |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

- **Mother** `S001_P34`, picture 355, vision 1 (`bin/dink/story/s1-h1-s.c:3-6`, `&story == 3`; drawn when its vision is 0
  or the screen's, dink.cpp:6031): a body lying in the burning house, red from head to foot, in a red pool.
- **Burn holes** `S001_P44`-`P49`, picture 158 frames 1 and 3, vision 2 (`s1-h1-s.c:30/41`, `&story > 3`): charred
  planks around a black hole (frame 3 = two holes).
- **Milder** `S086_P01`, 405 (script `s7-mil`): the soldier opened up in a pool.
- **The dead Dink** `S058_P06`, 436 frame 16 (script `s7-dink`, "sort of looks like me"): Dink on his back, knees drawn up, small pool.

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`355/01`](ref/GP-Q5/355_01.png) | the mother's burnt body | 68 x 50 | 1.70 x 1.25 m |
| [`158/01`](ref/GP-Q5/158_01.png) | burn hole | 23 x 20 | 0.57 x 0.50 m |
| [`158/03`](ref/GP-Q5/158_03.png) | burn hole, two holes | 42 x 40 | 1.05 x 1.00 m |
| [`405/01`](ref/GP-Q5/405_01.png) | Milder dead | 74 x 57 | 1.85 x 1.43 m |
| [`436/16`](ref/GP-Q5/436_16.png) | the dead Dink (last death frame) | 104 x 90 | 2.60 x 2.25 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q5/strip.png`](ref/GP-Q5/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

These are background/scripted placements at the layout scale of their screens: the mother's card is **1.70 x 1.25 m**
(68 x 50 px), the burn-hole cards 1.0-1.8 m; at the 2.5 cm/px base the mother's picture is 1.70 x 1.25 m too (interior
scale 1.75 x 2.5 cm = 4.4 cm/px applies to walls, not to her card). Meshes are real size (`fit: none`).

## 3. Where it shows

- **9 placements** on **3 screens**: 1, 58, 86
- by class: `burn_hole_decal` 6, `corpse_mom` 1, `corpse_soldier` 1, `dink_dead` 1
- art state today (`art_coverage.py` on master): placeholder 9
- card in the game today: 1.01-2.60 m wide, 0.88-2.25 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 9
- origin IDs: `S001_P34`, `S001_P44`, `S001_P45`, `S001_P46`, `S001_P47`, `S001_P48`, `S001_P49`, `S058_P06`, `S086_P01`

## 4. Start from (existing sources, half-done work)

- Branch `art/stonebrook-mother-burnholes`, ONE clean commit `d404721d` on `adf5b1dc` (local worktree
  `DinkUnclaimedImport`; its WIP history is on a local backup branch that must never be pushed). Private copy
  `Saved/CorpseGore` of the shared checkout. Holds: `Content/Dink/Data/Art/stonebrook.json` replacement rows (7) and
  asset entries, `families.json` rows `corpse_soldier` and `dink_dead` (scripted), the corpse-kit sources
  `Corpses/Burn_Hole_{A,B,C}/`, the rebuilt Mother body, `Corpses/Decals` (atlases drawn from 187-189 and 158 by
  `tools/build_decals.py`, imported but unused), `Scripts/tests/test_corpse_kit.py` lines, and the evidence
  `Docs/Verification/StonebrookMotherAndRemains_14Nov2026/` (README + four sheets, written and looked at by its author).
- Already run on it (14 Nov, 21:23): `Dink.Art` 63/63, probe 29/29 (the md5 comparison with `packaged_probe.md` was
  the next step and is not recorded), unit 879 OK, scrub clean, history check 0; coverage final 4918 -> 4927.
- Its own weaknesses list: burn holes dark grey in sun and flat (a stain, not a hole), hard cut edge; the mother's head
  and arms very dark (face unreadable at the play camera), **darker than the bright red of 1997**; Milder is a dark
  shape at the game's exposure; the dead Dink stiff (forearm off the ground, legs straight where 436/16 has knees up);
  `S001_P49` never in view.

## 5. What to make

1. Rebase `d404721d` onto current `origin/master` (conflicts expected only in `AGENTS.md`, `families.json`,
   `IMPORT.md`, the ledger): no Blender needed for that.
2. Fable look pass (Blender only if you decide to change them): the mother's red toward the brighter, more saturated red of
   355 (the author chose darker because bright red "read as paint" in the game: judge in the game, not in Cycles);
   burn holes burnt *through* (dark void, charred plank ends) rather than a stain; dead Dink's knees drawn up as 436/16.
3. Re-capture, compare probe md5s, push, PR.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

355: the mother is **a body red from head to foot lying in a bright red pool** (68 x 50 px). 405: Milder **opened, red,
in a pool**. 436/16: Dink on his back **with a red pool under his body**. Measured on the branch: the mother's blood
covers 1.79 m2 against 0.69 m2 of red in the picture, Milder 1.99 against 0.65, dead Dink 3.13 against 0.74: extent
is above 1997; the open point is the colour (darker than 1997).

## 7. Import and binding

- Corpse kit: `python3 -I SourceAssets/Art/PhotorealPass/Corpses/tools/make_kit_manifest.py`, then
  `DINK_KIT=Corpses DINK_KIT_FOLDER=Corpses Scripts/import_town_exteriors.sh` (writes `/Game/Dink/Photoreal/Corpses`,
  report `Saved/PhotorealPass/import_corpses.json`). `make_kit_manifest.py` on the branch also lists meshes named by
  `replacements` rows of `dink-art/1` manifests.
- Binding: screen 1 is dressed (`stonebrook.json` `hide_screen_visuals`), so family rows draw nothing there; the mother and
  holes are `replacements` rows of `stonebrook.json` (a replacement swaps the placement actor's card mesh, vision still
  gates it). Milder and the dead Dink are `families.json` rows with `"scripted": true`.

## 8. Prove it in the game

The branch's capture script is `gen_cap.py` of its author's scratch (archived; recreate from the README): `dink.Goto 1`,
`dink.Vision 1` (mother) and `dink.Vision 2` (holes), `dink.Goto 86` (Milder), `dink.Goto 58` (dead Dink), close and play
cameras, `Scripts/PhotorealQA/run_capture.sh <abs script>` through `unreal_turn.sh`. Note: `dink.Vision` without the
story value leaves the living mother standing in the room at vision 2 (capture artefact).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Blocks GP-Q6 and GP-Q10: the atlases `MI_Decal_Blood1997*` / `MI_Decal_Burn1997` are imported by this commit.
- Independent of Stream A. Push it first in Stream B.

## 10. Done when

PR open with the four sheets refreshed on current master, probe md5s equal to the table, the colour decision written in the README.
