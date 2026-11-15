# CG-3: Severed duck head: its blood pool larger than the head (121/04)

| | |
|---|---|
| queue row | PR #113 review (coordinator, 15 Nov) |
| priority (queue) | 2 (review) |
| estimated size | S |
| stream | Stream B, gore and remains, step 9 of that stream |
| kind of work | art (modelled pool on `SM_Duck_Head_PR`, puddle decal size) |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

First blow on a duck (duck_brain, dink.cpp:12723-12775): the head (121) flies off and lands in blood (121/04), the body runs on headless spraying (111-119).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`121/01`](ref/CG-3/121_01.png) | head flying | 15 x 42 | 0.38 x 1.05 m |
| [`121/02`](ref/CG-3/121_02.png) |  | 17 x 38 | 0.42 x 0.95 m |
| [`121/03`](ref/CG-3/121_03.png) |  | 15 x 31 | 0.38 x 0.78 m |
| [`121/04`](ref/CG-3/121_04.png) | head landed in blood | 20 x 30 | 0.50 x 0.75 m |
| [`111/01`](ref/CG-3/111_01.png) | headless duck | 31 x 41 | 0.78 x 1.02 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/CG-3/strip.png`](ref/CG-3/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

121/04 is 20 x 30 px: 0.5 x 0.75 m at 2.5 cm/px; the pool is wider than the head. #113: `M_BloodPuddle_Decal` 80 cm.

## 3. Where it shows

- **182 placements** on **32 screens**: 2, 100, 145, 161, 162, 190, 194, 196, 307, 374, 397, 405, 409, 440, 441, 504, 521, 532, 535, 536, 537, 564, 570, 585, 604, 652, 656, 699, 700, 711, 762, 764
- by class: `duck` 92, `duck_head` 90
- art state today (`art_coverage.py` on master): cut 1, placeholder 181
- card in the game today: 0.72-1.86 m wide, 0.90-3.01 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 92, instance 90
- origin IDs (first 40 of 182): `S002_P24`, `S100_P36`, `S145_P01`, `S145_P02`, `S145_P03`, `S145_P04`, `S145_P05`, `S145_P06`, `S145_P07`, `S145_P08`, `S145_P09`, `S145_P10`, `S145_P11`, `S145_P12`, `S145_P13`, `S145_P14`, `S145_P15`, `S145_P16`, `S145_P17`, `S145_P18`, `S145_P19`, `S145_P20`, `S145_P21`, `S145_P22`, `S145_P23`, `S145_P24`, `S145_P25`, `S145_P26`, `S145_P27`, `S145_P28`, `S145_P29`, `S145_P30`, `S145_P31`, `S145_P32`, `S145_P33`, `S145_P34`, `S145_P35`, `S145_P36`, `S145_P37`, `S145_P38`

## 4. Start from (existing sources, half-done work)

- PR #113 (`art/creature-ducks`) is being finished by an Opus agent today in local worktree `DinkCreatures113` (branch
  `creatures-113-work`, pushed as `art/creature-ducks`); its round-4 packages came from worktree `DinkGate2Creatures`.
  Wait for #113 to merge, then work on master. Review that queued these rows: coordinator's PR review of #113
  (15 Nov, 11:50).
- Sources: `SourceAssets/Art/PhotorealPass/Creatures/` (`Tools/gore_fx.py`, `pig.py`, `duck.py`, `slime_opaque.py`,
  `crlib.py`, `bl.sh`), packages `/Game/Dink/Photoreal/Creatures/{Duck,Pig,Slime,Gore}`, rows `duck`, `pig`,
  `slime_*` of `creatures.json`, runtime `DinkCreatureGore.cpp`.
- Evidence of #113: `Docs/Verification/CreatureGore_14Nov2026/` (`gore_1_duck_head_and_fountain.jpg`,
  `gore_2_duck_burst.jpg`, `gore_3_slime_and_pig.jpg`, `gore_4_duck_head_in_pool.jpg`, `live_duck_and_pig.jpg`).
- `gore_4_duck_head_in_pool.jpg`: the head lies in a pool; the review asks for the pool to be clearly larger than the head as in 121/04.

## 5. What to make

Pool around the landed head at least twice its width, saturated red, as decal (grass) and modelled pool (bare ground).

## 6. Gore bar (owner rule: at least the 1997 level, never less)

121/04: the head **in a red pool larger than itself**. Bar: same.

## 7. Import and binding

`DINK_PHOTOREAL_ONLY=duck,slime,pig Scripts/import_photoreal_art.sh` (creature section of `import_photoreal_art.py`
that #113 brings; one Unreal step through `unreal_turn.sh`), scrub the new packages, rows in `creatures.json`
(`duck`, `pig`, `slime_*` only: the monster rows belong to Stream A, which pushes first).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/CG-3 --name duck_head \
    --kill 536:258:174 --kill 374:258:174
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-3/duck_head_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-3/duck_head_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs PR #113 merged. `creatures.json` is shared with Stream A (monster rows): rebase after Stream A's PR and touch only these rows.

## 10. Done when

Landed head frames show the pool wider than the head on 536 and 374.
