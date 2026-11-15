# CG-5: Pig anatomy: shoulder blades, spine line, thinner legs

| | |
|---|---|
| queue row | PR #113 review (coordinator, 15 Nov) |
| priority (queue) | 2 (review) |
| estimated size | M |
| stream | Stream B, gore and remains, step 11 of that stream |
| kind of work | new art (Blender: pig body rework, keep rig and clips) |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

Pigs (41-49, 1997 farm pigs; `pig_brain` dink.cpp:13366-13382) in the Stonebrook pen (407) and 636.

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`41/01`](ref/CG-5/41_01.png) | pig walk | 50 x 56 | 1.25 x 1.40 m |
| [`41/03`](ref/CG-5/41_03.png) | pig walk | 49 x 54 | 1.23 x 1.35 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/CG-5/strip.png`](ref/CG-5/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

49-50 x 54-56 px: about 1.25 x 1.4 m on its card at 100 % (a farm pig is about 1.2-1.5 m long).

## 3. Where it shows

- **13 placements** on **5 screens**: 31, 407, 587, 636, 694
- by class: `pig` 13
- art state today (`art_coverage.py` on master): final 5, placeholder 8
- card in the game today: 1.25-1.40 m wide, 1.30-1.40 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 13
- origin IDs: `S031_P04`, `S407_P02`, `S407_P05`, `S407_P06`, `S407_P07`, `S407_P11`, `S587_P14`, `S636_P05`, `S636_P06`, `S636_P07`, `S694_P01`, `S694_P02`, `S694_P03`

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
- `live_duck_and_pig.jpg`, `SourceAssets/Art/PhotorealPass/Creatures/Pig/Review/r11_*.png`: still reads as **a barrel on thick legs** (#113 rebuilt it "as one rounded barrel").

## 5. What to make

Sculpt a real pig: shoulder blades and hips under the skin, spine line, belly sag, thinner legs with hocks, ears; skin with bristles (the bristle atlas exists, `gen_bristle_atlas.py`).

## 7. Import and binding

`DINK_PHOTOREAL_ONLY=duck,slime,pig Scripts/import_photoreal_art.sh` (creature section of `import_photoreal_art.py`
that #113 brings; one Unreal step through `unreal_turn.sh`), scrub the new packages, rows in `creatures.json`
(`duck`, `pig`, `slime_*` only: the monster rows belong to Stream A, which pushes first).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/CG-5 --name pig \
    --play 407:258:174 --close 407:258:174
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-5/pig_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-5/pig_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs PR #113 merged. `creatures.json` is shared with Stream A (monster rows): rebase after Stream A's PR and touch only these rows.

## 10. Done when

The pig reads as a pig at 1 m and the play camera; walk clip still fits.
