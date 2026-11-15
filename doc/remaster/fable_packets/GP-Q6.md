# GP-Q6: Blood splats and burn holes on background screens as decals at least the size of each 1997 card

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q6 (GORE_STORY_PARITY.md G9, G10) |
| priority (queue) | medium |
| estimated size | M (code and sheets exist on three unpushed branches; finish, size from card, look) |
| stream | Stream B, gore and remains, step 2 of that stream |
| kind of work | decal art (sheets from the 1997 pictures, partly Blender/numpy) + finishing three code branches |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

46 blood splats are placed as background pictures (187 `spurt`, 188 `sprtl`, 189 `sprtr`, the same pictures the
engine's `random_blood` draws at a hit, dink.cpp:6675-6700) on screens 60, 61, 91, 94, 122, 126, 154, 158, 190, 191,
at size 100-243 %. Burn holes 158 and the burning floor 154 lie on 1, 5, 66, 439, 533, 536. Today every one is the
1997 picture on a card at its own size (G9: at least 1997 as a card; G10: actor burn holes of 5/66/533/536 are a
fixed 120 cm decal on master = **less than 1997**, fixed by F2 of `fix/gore-story-parity`).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`187/01`](ref/GP-Q6/187_01.png) | spurt, first frame | 32 x 18 | 0.80 x 0.45 m |
| [`187/03`](ref/GP-Q6/187_03.png) | spurt, last frame | 39 x 56 | 0.97 x 1.40 m |
| [`188/04`](ref/GP-Q6/188_04.png) | spurt left, last | 39 x 56 | 0.97 x 1.40 m |
| [`189/04`](ref/GP-Q6/189_04.png) | spurt right, last | 51 x 56 | 1.27 x 1.40 m |
| [`158/04`](ref/GP-Q6/158_04.png) | burn hole, large | 90 x 69 | 2.25 x 1.73 m |
| [`158/05`](ref/GP-Q6/158_05.png) | burn hole, large | 90 x 69 | 2.25 x 1.73 m |
| [`154/01`](ref/GP-Q6/154_01.png) | burning floor | 90 x 69 | 2.25 x 1.73 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q6/strip.png`](ref/GP-Q6/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Splats are `base` scale (2.5 cm/px x size %): 0.37-2.37 m wide, 0.30-3.40 m tall; the largest are `S091_P08`/`P09`
(about 2.0 x 2.8 m and 2.4 x 3.4 m). Burn cards are 1.0-8.9 m (screen 439's are up to 8.9 m; 533/536 are 2.2 x 2.0 m
and 4.0 x 3.9 m). Rule from the queue: **never a fixed size below the card**: a decal's square side >= the card's
longer side (x 1.15 as F2 does).

## 3. Where it shows

- **75 placements** on **16 screens**: 1, 5, 60, 61, 66, 91, 94, 122, 126, 154, 158, 190, 191, 439, 533, 536
- by class: `blood_splat` 46, `burn_damage_decal` 1, `burn_hole_decal` 26, `burnt_floor_hole` 2
- art state today (`art_coverage.py` on master): placeholder 75
- card in the game today: 0.37-8.87 m wide, 0.30-6.82 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 28, instance 47
- origin IDs (first 40 of 75): `S001_P44`, `S001_P45`, `S001_P46`, `S001_P47`, `S001_P48`, `S001_P49`, `S005_P25`, `S005_P26`, `S005_P27`, `S060_P06`, `S060_P07`, `S061_P07`, `S061_P08`, `S066_P23`, `S066_P24`, `S091_P06`, `S091_P07`, `S091_P08`, `S091_P09`, `S091_P10`, `S091_P11`, `S091_P12`, `S091_P13`, `S091_P14`, `S091_P15`, `S091_P16`, `S091_P17`, `S091_P18`, `S091_P19`, `S091_P20`, `S094_P02`, `S094_P03`, `S094_P04`, `S094_P05`, `S094_P06`, `S094_P07`, `S094_P08`, `S122_P11`, `S122_P12`, `S122_P13`
- full list with card sizes: `doc/remaster/gore_story_parity/gore_placements.csv`

## 4. Start from (existing sources, half-done work)

The decal work is a chain of unpushed local branches (all on `adf5b1dc`, 14 Nov; each carries WIP commits with private
paths: scrub and squash before any push):
1. `art/gate2-static-decals` (local worktree `DinkGate2Static`, tip `fb0a6403`; backup on GitHub
   `wip-backup/14Nov/art/gate2-static-decals` at `3e103007`): deferred decals on **background (instance)
   placements**, blood as sprays of drops, burn darker; `UDinkEnvironmentSubsystem::ApplyDecals` +
   `environment.json` `decals` rows, `Props/tools/decals.py`, `Props/Decals/T_Decal_BloodSplat_*`, `T_Decal_BurnHole_*`,
   `Scripts/tests/test_env_decal_coverage.py`, audit rules in `art_coverage.py`.
2. `art/gate2-static-ground-holes` (same worktree, now checked out there, tip `43237586`, on top of 1): `fit: card`
   decals (over the ground rectangle of the placement's own picture), `scripted: true`, keys `<seq>:<frame>`; new
   sheets GroundCrack, GroundPit, CaveSteps, StairWell (428:2, 428:4), CellarHatch (428:5) in `Props/tools/decals.py`.
3. `art/blood-decals-1997` (local worktree `DinkCorpseDecals`, tip `7fbe207c`, stacked on 1 at `fb0a6403`): a decal per
   1997 picture frame **sized from the card** (`pictures`, `PictureDecalSquare`), `DinkPictureDecalTests.cpp`; uses the
   atlases `MI_Decal_Blood1997A/B_0..3`, `MI_Decal_Burn1997_0..3` that GP-Q5's branch imports. Not built, not seen.

The integration of 1 + 2 + the structure and mount branches (`integ/gate2-static-local`, worktree `DinkGate2StaticInteg`)
passed `Dink.Art` 64/64 and the probe 29/29 on 14 Nov in private copy `Saved/Gate2Static`, captures under
`Saved/Gate2Static/cap/{w_before,w_after,r2_after}` of the shared checkout (git-ignored).
Also unmerged and overlapping: `fix/gore-story-parity` (local worktree `DinkGoreParity`, open work of the gore audit):
F2 sizes the decal that replaces an **actor** card from that card (`CardDecalSquare`, burn holes of 5/66/533/536 become
1.2-4.6 m) and adds the hit blood (`UDinkBloodPresenter`, `environment.json` `hit_blood`). Whoever merges second
rebases onto the other; there must be one card-size rule, not two.

Looked at for this packet (`ref/GP-Q6/existing_work_14nov.jpg`, frames of the 14 Nov integration captures): the blood
of `S091_P14` reads as sprays of red drops of about the picture's spread (good), the darker tint of round 2 reads
brown-maroon; the burn decal of `S533_P21` on grass reads as **a grey metal plate with a star pattern**, not a burn;
`S005_P25` indoors is barely visible from the play camera.

## 5. What to make

1. Finish the decal branches in order 1 -> 3 (rebase on master, build, capture): blood decals per 1997 frame from the
   `Blood1997` atlases, each sized from its own card; burns per frame from `Burn1997`.
2. Fable: the burn sheet must read as charred wood/soot with a black hole and glowing ember edges where 154 shows
   flames (not grey metal); blood red as saturated as 187-189 (keep the round-1 red, not the round-2 maroon).
3. Screen 439's 14 holes are hidden by the burnt-cottage state swap: look there once (not looked at by the audit).

## 6. Gore bar (owner rule: at least the 1997 level, never less)

187/188/189 last frames: **a spray of separate bright red droplets** spread over 39-51 x 56 px (1.0-1.3 m wide and up
to 1.4 m long at 100 %, up to 2.4 x 3.4 m on screen 91), no single pool. Bar: same droplet spread and red, at least
the card's extent for every placement, visible on grass (decals stain the grass blades; a flat mesh is hidden by the carpet).

## 7. Import and binding

- Props decal sheets: `Props/tools/decals.py` -> `Props/Decals/T_Decal_*`, imported with
  `DINK_KIT=Props DINK_KIT_FOLDER=Props Scripts/import_town_exteriors.sh` (manifest `Props/manifest.json` decal block).
- Corpse-kit atlases: GP-Q5's `Corpses/Decals` (corpse kit import command in GP-Q5).
- Binding: `Content/Dink/Data/Environment/environment.json` `decals` rows (class rows, `<seq>:<frame>` rows,
  `fit: card`, `scripted`), read by `UDinkEnvironmentSubsystem::ApplyDecals`; `art_coverage.py` decal rule.

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (`visual_sweep.py` came with PR #132):
```bash
python3 -I Scripts/PhotorealQA/visual_sweep.py "$PWD/Saved/PhotorealPass/fable/GP-Q6/after" --screens=60,91,94,122,154,190,5,66,533,536
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q6/after/sweep.txt"
python3 -I Scripts/PhotorealQA/visual_sweep_report.py "$PWD/Saved/PhotorealPass/fable/GP-Q6/after"   # sheets + detectors
```
Before frames for the same screens are in `DinkRemasterUE/Docs/Verification/VisualSweep_15Nov2026/frames/` (LFS:
`git lfs pull --include "DinkRemasterUE/Docs/Verification/VisualSweep_15Nov2026/**"`). 

Plus close views of `S091_P08`/`P09` (largest splats) and the burn holes of 533/536: the branch author's `caps.py` views `blood_<id>` / `burn_<id>` (play + close) are the model.

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs GP-Q5 (atlases). Shares `environment.json` and `decals.py` with VS-08 and GP-Q10 (same stream, same order). Coordinate with the owner of `fix/gore-story-parity` (one card-size rule).

## 10. Done when

All 46 splats and the 29 burn pictures are decals at least their card size, red and charred as 1997, seen at play and close cameras; Dink.Art, probe, unit tests pass.
