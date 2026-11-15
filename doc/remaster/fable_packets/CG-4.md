# CG-4: Fountain drops shaped as drops, not dark leaf-like flakes

| | |
|---|---|
| queue row | PR #113 review (coordinator, 15 Nov) |
| priority (queue) | 2 (review) |
| estimated size | S |
| stream | Stream B, gore and remains, step 10 of that stream |
| kind of work | art (`SM_BloodDrop` mesh and `M_BloodDrop`) |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

The headless duck (111-119) runs with a dense red mass spraying from the neck; 1 in 100 frames it bleeds a `random_blood` (dink.cpp:12798-12802).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`111/01`](ref/CG-4/111_01.png) | headless duck spraying | 31 x 41 | 0.78 x 1.02 m |
| [`111/02`](ref/CG-4/111_02.png) |  | 32 x 42 | 0.80 x 1.05 m |
| [`111/03`](ref/CG-4/111_03.png) |  | 31 x 42 | 0.78 x 1.05 m |
| [`111/04`](ref/CG-4/111_04.png) |  | 32 x 43 | 0.80 x 1.07 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/CG-4/strip.png`](ref/CG-4/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Drops are centimetres; the plume about as large against the body as in 111/113 (31-32 x 41-43 px frames).

## 3. Where it shows


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
- `gore_1_duck_head_and_fountain.jpg`: the drop mesh reads as **dark leaves** at the play camera.

## 5. What to make

Elongated droplet mesh (stretched along velocity), wet specular, bright red; optional motion-stretch in the material.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

111/113: a **dense red plume** from the neck. Bar: as dense and red; drops must read as liquid.

## 7. Import and binding

`DINK_PHOTOREAL_ONLY=duck,slime,pig Scripts/import_photoreal_art.sh` (creature section of `import_photoreal_art.py`
that #113 brings; one Unreal step through `unreal_turn.sh`), scrub the new packages, rows in `creatures.json`
(`duck`, `pig`, `slime_*` only: the monster rows belong to Stream A, which pushes first).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/CG-4 --name duck_fountain \
    --close 536:258:174 --kill 536:258:174
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-4/duck_fountain_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-4/duck_fountain_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs PR #113 merged. `creatures.json` is shared with Stream A (monster rows): rebase after Stream A's PR and touch only these rows.

## 10. Done when

Fountain reads as liquid blood at the play camera and close up.
