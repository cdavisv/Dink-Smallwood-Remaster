# CG-2: Red slime splatter: wider scatter of brown-red chunks (701/703), see-through gel

| | |
|---|---|
| queue row | PR #113 review (coordinator, 15 Nov) |
| priority (queue) | 2 (review) |
| estimated size | S |
| stream | Stream B, gore and remains, step 8 of that stream |
| kind of work | art (splatter mesh/decal, slime material) |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

Slimes (puddles) killed leave 661/663 (blue), 681/683 (green/olive), 701/703 (red) until the screen changes: a scatter of gel chunks, brown-red for the red slime.

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`693/01`](ref/CG-2/693_01.png) | red slime alive | 25 x 18 | 0.62 x 0.45 m |
| [`701/01`](ref/CG-2/701_01.png) | red slime death | 26 x 23 | 0.65 x 0.57 m |
| [`703/01`](ref/CG-2/703_01.png) | red slime death | 26 x 23 | 0.65 x 0.57 m |
| [`661/01`](ref/CG-2/661_01.png) | blue slime death | 26 x 23 | 0.65 x 0.57 m |
| [`681/01`](ref/CG-2/681_01.png) | green slime death | 26 x 23 | 0.65 x 0.57 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/CG-2/strip.png`](ref/CG-2/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

26 x 23 px: about 0.65 x 0.58 m at 100 %; the #113 decal is 230 cm (red slime: 320 cm in the WIP parameters).

## 3. Where it shows

- **107 placements** on **19 screens**: 32, 64, 123, 191, 192, 274, 347, 458, 512, 546, 599, 610, 633, 652, 658, 660, 672, 688, 695
- by class: `slime_blue` 67, `slime_green` 11, `slime_red` 29
- art state today (`art_coverage.py` on master): placeholder 107
- card in the game today: 0.60-0.65 m wide, 0.45-0.57 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 107
- origin IDs (first 40 of 107): `S032_P02`, `S032_P03`, `S032_P04`, `S032_P05`, `S032_P06`, `S032_P07`, `S064_P06`, `S064_P07`, `S123_P08`, `S123_P10`, `S191_P09`, `S191_P10`, `S192_P07`, `S192_P08`, `S192_P09`, `S192_P10`, `S192_P11`, `S192_P12`, `S192_P13`, `S192_P14`, `S192_P15`, `S192_P16`, `S192_P17`, `S192_P18`, `S192_P19`, `S192_P20`, `S192_P21`, `S192_P22`, `S192_P23`, `S274_P10`, `S347_P08`, `S458_P03`, `S458_P04`, `S458_P05`, `S458_P06`, `S458_P07`, `S458_P08`, `S458_P09`, `S458_P10`, `S458_P11`
- class names of the slimes in `sprite_classes.csv` may differ; the class rows of #113 bind sequences 651-703

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
- `gore_3_slime_and_pig.jpg`: the red slime's splash is a **small orange-red spot**, smaller and lighter than 701; the committed `MI_Slime_Red_PR` pointed at the old peach texture (fixed by the creatures-113 agent with `T_Slime_*_Opaque_BC`).

## 5. What to make

Splatter of separate brown-red gel chunks over the 701 extent (not one spot), translucent gel (subsurface) for the living slime as the source notes describe.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

701/703: **a scatter of brown-red chunks** over about 0.65 x 0.58 m (x size %). Bar: at least that scatter and colour.

## 7. Import and binding

`DINK_PHOTOREAL_ONLY=duck,slime,pig Scripts/import_photoreal_art.sh` (creature section of `import_photoreal_art.py`
that #113 brings; one Unreal step through `unreal_turn.sh`), scrub the new packages, rows in `creatures.json`
(`duck`, `pig`, `slime_*` only: the monster rows belong to Stream A, which pushes first).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/CG-2 --name slime_red \
    --kill 192:300:300
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-2/slime_red_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-2/slime_red_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs PR #113 merged. `creatures.json` is shared with Stream A (monster rows): rebase after Stream A's PR and touch only these rows.

## 10. Done when

Red slime kill frame beside 701 shows the same spread and colour.
