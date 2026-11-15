# GP-Q7: Remaining placed corpse cards: dragon 212, pillbug corpses, duck bodies, the 90 duck heads of screen 145

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q7 (GORE_STORY_PARITY.md G14) |
| priority (queue) | medium |
| estimated size | S-M (mostly bindings of existing meshes; one new remains: dragon 212) |
| stream | Stream B, gore and remains, step 5 of that stream |
| kind of work | mostly bindings (not art) + one new remains mesh (dragon 212, Blender, corpse kit) |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

Placed pictures (background or scripted placements, not kills): the torn dragon 212 (`S100_P34`, `S238_P12`; the
"orange creature of 238" of VS-04 is this), pillbug corpses 141/143 (`S098_P04`, `S100_P25`, `S100_P26`), duck
bodies 127 (`S100_P27`, `S521_P05`), duck heads 121 (90 on screen 145, the duck-head field).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`212/01`](ref/GP-Q7/212_01.png) | dragon remains | 105 x 122 | 2.62 x 3.05 m |
| [`141/01`](ref/GP-Q7/141_01.png) | pillbug corpse | 46 x 35 | 1.15 x 0.88 m |
| [`143/01`](ref/GP-Q7/143_01.png) | pillbug corpse | 44 x 36 | 1.10 x 0.90 m |
| [`121/04`](ref/GP-Q7/121_04.png) | duck head on the ground | 20 x 30 | 0.50 x 0.75 m |
| [`127/04`](ref/GP-Q7/127_04.png) | headless duck body | 35 x 32 | 0.88 x 0.80 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q7/strip.png`](ref/GP-Q7/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Base scale (2.5 cm/px x size %): 212 about 2.6 x 3.0 m, pillbug corpse 1.1 x 0.9 m, duck head 0.4-0.5 m, duck body 0.9 x 0.8 m at 100 %.

## 3. Where it shows

- **98 placements** on **6 screens**: 98, 100, 145, 158, 238, 521
- by class: `dragon_corpse` 3, `duck_corpse` 2, `duck_head` 90, `pillbug_corpse` 3
- art state today (`art_coverage.py` on master): final 1, placeholder 97
- card in the game today: 1.08-2.62 m wide, 0.88-3.05 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 2, instance 96
- origin IDs (first 40 of 98): `S098_P04`, `S100_P25`, `S100_P26`, `S100_P27`, `S100_P34`, `S145_P01`, `S145_P02`, `S145_P03`, `S145_P04`, `S145_P05`, `S145_P06`, `S145_P07`, `S145_P08`, `S145_P09`, `S145_P10`, `S145_P11`, `S145_P12`, `S145_P13`, `S145_P14`, `S145_P15`, `S145_P16`, `S145_P17`, `S145_P18`, `S145_P19`, `S145_P20`, `S145_P21`, `S145_P22`, `S145_P23`, `S145_P24`, `S145_P25`, `S145_P26`, `S145_P27`, `S145_P28`, `S145_P29`, `S145_P30`, `S145_P31`, `S145_P32`, `S145_P33`, `S145_P34`, `S145_P35`

## 4. Start from (existing sources, half-done work)

- Dragon 216 remains are bound on master (corpse kit `Corpses/Dragon_Corpse`, `families.json` row `216 foes/dragon/f2-x7-`,
  PR #103/#110). 212 has no remains of its own: build it with `Corpses/tools/build_gore.py` (reads the rigged dragon
  of `Unclaimed/dragon`; `Unclaimed/tools/bl.sh ../../Corpses/tools/build_gore.py <name> [preview]`).
- Pillbug corpse: `SM_Pillbug_Corpse_PR` + `M_Pillbug_BloodPool_Decal` on master (class corpse): a `families.json`
  row per picture (`141`/`143` with `frame`) binds the placed ones; the pool must come as a decal on grass.
- Duck head and body: `SM_Duck_Head_PR`, `SK_Duck_Headless_PR` of PR #113 (unmerged); the head's pool is CG-3.

## 5. What to make

Build the 212 remains (head, neck and one wing torn off, raw flesh, pool card); then bind all seven placed cards and the 90 heads by `families.json` rows (pools as decals where on grass).

## 6. Gore bar (owner rule: at least the 1997 level, never less)

212: torn flesh red at the tears, red under it; 141/143: the shell burst open in a red pool; 121/127: head and body in red. Bar: each at least its picture's red and extent.

## 7. Import and binding

Corpse kit import (GP-Q5 section 7); `families.json` rows (`family` = `<seq> <path>` key as the 216 row, optional `frame`, `fit: none`, `yaw_from_sprite`). Screens listed under `hide_screen_visuals` of a `dink-art/1` manifest never take family rows (check 145 and 100).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (`visual_sweep.py` came with PR #132):
```bash
python3 -I Scripts/PhotorealQA/visual_sweep.py "$PWD/Saved/PhotorealPass/fable/GP-Q7/after" --screens=100,238,98,521,145
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q7/after/sweep.txt"
python3 -I Scripts/PhotorealQA/visual_sweep_report.py "$PWD/Saved/PhotorealPass/fable/GP-Q7/after"   # sheets + detectors
```
Before frames for the same screens are in `DinkRemasterUE/Docs/Verification/VisualSweep_15Nov2026/frames/` (LFS:
`git lfs pull --include "DinkRemasterUE/Docs/Verification/VisualSweep_15Nov2026/**"`). 

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Duck parts need PR #113 merged. Stream A uses the 212 remains for dragon kills (VS-03): build it early in Stream B or tell Stream A to bind 216 only.

## 10. Done when

No corpse picture of G14 left on a card; Dink.Art + probe pass.
