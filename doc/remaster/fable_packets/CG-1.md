# CG-1: Pig burst: darker red droplets, denser ball in the middle frames (sequence 164)

| | |
|---|---|
| queue row | PR #113 review (coordinator, 15 Nov); rows CG-1..CG-6 go into `FABLE_ART_QUEUE.md` with #113 |
| priority (queue) | 1 (review) |
| estimated size | S |
| stream | Stream B, gore and remains, step 7 of that stream |
| kind of work | effect art (gore_fx.py drops and material) + parameters |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

A killed pig plays the burst 164 (pig_brain, dink.cpp:13367-13382; also any killed sprite without a death picture, dink.cpp:12384-12389, and the duck's second blow, dink.cpp:12732). 164 grows from a tight dark red ball (frames 1-7) to a wide spray of dark red and black specks (8-14).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`164/01`](ref/CG-1/164_01.png) | burst start | 62 x 41 | 1.55 x 1.02 m |
| [`164/04`](ref/CG-1/164_04.png) |  | 75 x 56 | 1.88 x 1.40 m |
| [`164/07`](ref/CG-1/164_07.png) | dense ball | 87 x 72 | 2.17 x 1.80 m |
| [`164/10`](ref/CG-1/164_10.png) |  | 100 x 91 | 2.50 x 2.27 m |
| [`164/14`](ref/CG-1/164_14.png) | thinning | 115 x 118 | 2.88 x 2.95 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/CG-1/strip.png`](ref/CG-1/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

164 frames are 62 x 41 to 115 x 118 px: up to **2.9 x 3.0 m** at 2.5 cm/px; #113 bursts at 2.1 m (2.7 duck lengths for the duck).

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
- `gore_3_slime_and_pig.jpg` (seen by the #113 review): the pig's ball reads **pink-red and lighter** than the dark 1997 ball in its middle frames.

## 5. What to make

Darker, more saturated drop material (`M_BloodBlob` / `M_BloodDrop`), more drops in the ball's core for frames 4-9 of the timing, keep the 2.1-2.9 m spread.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

164: a **dense, dark red ball** (frame 7: solid red-black mass), then a **wide spray of dark red specks** up to 2.9 x 3.0 m. Bar: at least that density and darkness, no pink.

## 7. Import and binding

`DINK_PHOTOREAL_ONLY=duck,slime,pig Scripts/import_photoreal_art.sh` (creature section of `import_photoreal_art.py`
that #113 brings; one Unreal step through `unreal_turn.sh`), scrub the new packages, rows in `creatures.json`
(`duck`, `pig`, `slime_*` only: the monster rows belong to Stream A, which pushes first).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/CG-1 --name pig_burst \
    --kill 407:258:174 --kill 636:258:174
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-1/pig_burst_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-1/pig_burst_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs PR #113 merged. `creatures.json` is shared with Stream A (monster rows): rebase after Stream A's PR and touch only these rows.

## 10. Done when

Pig burst frames side by side with 164/04-14 read as dark as 1997.
