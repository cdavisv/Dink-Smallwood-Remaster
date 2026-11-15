# GP-Q10: Hit blood: a spray from the 1997 spurt pictures (and a short airborne spurt) instead of the generic splat atlas

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q10 |
| priority (queue) | low |
| estimated size | S |
| stream | Stream B, gore and remains, step 4 of that stream |
| kind of work | decal/effect art (sheet from 187-189, optional small Niagara or flipbook spurt) |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

Every damaging hit calls `random_blood` (dink.cpp:6675-6700): one of 187/188/189 played once at the victim (brain 5,
D:15741-15768), then drawn into the background until the screen is redrawn. Paths: melee both ways (D:14398-14403),
missiles (D:15567), touch damage (D:15672), DinkC `hurt` (D:9953).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`187/01`](ref/GP-Q10/187_01.png) | spurt | 32 x 18 | 0.80 x 0.45 m |
| [`187/02`](ref/GP-Q10/187_02.png) | spurt | 21 x 12 | 0.53 x 0.30 m |
| [`187/03`](ref/GP-Q10/187_03.png) | spurt | 39 x 56 | 0.97 x 1.40 m |
| [`188/01`](ref/GP-Q10/188_01.png) | left | 51 x 27 | 1.27 x 0.68 m |
| [`188/02`](ref/GP-Q10/188_02.png) | left | 38 x 29 | 0.95 x 0.72 m |
| [`188/03`](ref/GP-Q10/188_03.png) | left | 35 x 42 | 0.88 x 1.05 m |
| [`188/04`](ref/GP-Q10/188_04.png) | left | 39 x 56 | 0.97 x 1.40 m |
| [`189/04`](ref/GP-Q10/189_04.png) | right | 51 x 56 | 1.27 x 1.40 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q10/strip.png`](ref/GP-Q10/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Last frames 39 x 56 / 39 x 56 / 51 x 56 px: about 1.0-1.3 m x 1.4 m at 2.5 cm/px; the presenter already uses 161 cm for 187/188 (longer side x 1.15).

## 3. Where it shows


## 4. Start from (existing sources, half-done work)

- `fix/gore-story-parity` (local worktree `DinkGoreParity`, unmerged; evidence `Docs/Verification/GoreParity_15Nov2026/`):
  `UDinkGameplay::NoteBlood` + `UDinkBloodPresenter` lay a decal under the hit sprite, materials
  `MI_Decal_BloodSplat_0..3` (`environment.json` `hit_blood`), `dink.HitBlood 0` turns it off.
- Atlases from the 1997 pictures already exist: `MI_Decal_Blood1997A/B_0..3` (GP-Q5's commit `d404721d`, `Corpses/Decals`,
  `tools/build_decals.py`).

## 5. What to make

Point `hit_blood` at per-picture cells of the 1997 atlases (187 -> A, 188/189 -> B with their left/right lean) and, optionally, a 0.25 s airborne spurt at the wound (flipbook card or a small Niagara system) that lands as the decal.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

187-189: **a burst of bright red droplets thrown to one side (188 left, 189 right) or up (187)**, leaving a spray on the ground. Bar: every damaging hit leaves a visible red spray of at least that extent until the screen changes.

## 7. Import and binding

Decal materials as in GP-Q5/GP-Q6; binding is `environment.json` `hit_blood` (keys of the gore-parity PR).

## 8. Prove it in the game

Fight capture: `python3 -I Scripts/CreatureQA/make_scripts.py ... --kill 29:<x>:<y>` (GP-Q1 has walkable points) and look at each hit frame; the gore-parity README has its own capture list.

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs `fix/gore-story-parity` merged and GP-Q5 (atlases). Same `environment.json` as GP-Q6.

## 10. Done when

Hits leave the 1997 spray shapes; sheet beside 187-189 in the PR.
