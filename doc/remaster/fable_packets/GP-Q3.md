# GP-Q3: Goblins: live classes and their corpses (hammer goblin 765, horned goblin 785, goblin soldier 805)

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q3 (GORE_STORY_PARITY.md G4) + the goblin part of VS-04 and VS-05 |
| priority (queue) | high |
| estimated size | M (rigs exist, no clips, no corpses) |
| stream | Stream A, monsters, step 5 of that stream |
| kind of work | new art (Blender: body rework, clips, corpses) + class rows; no WIP for goblins |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

Goblin sanctuary and Mog (story path: probe chapter with the goblins). Scripts and what a kill leaves
(`add_kill_sprite`, `base_walk + 5`, dink.cpp:12374): `en-gh`, `s3-gh`, `s3-gob` (hammer goblin, walk 760; `en-gh`'s
`sp_base_death(780)` is commented out) -> **765**; `en-gs`, `s3-gs`, `s3-gobg` (soldier, 800) -> **805**; `en-gmog`
(Mog, spawned by `s3-mog`, horned goblin 780) -> **785**. Green-skinned, helmeted goblins in leather and mail:
hammer (761), horned with spiked club (781), soldier with a bill and round shield (801).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`761/01`](ref/GP-Q3/761_01.png) | hammer goblin walk | 76 x 107 | 1.90 x 2.67 m |
| [`781/01`](ref/GP-Q3/781_01.png) | horned goblin walk | 108 x 135 | 2.70 x 3.38 m |
| [`801/01`](ref/GP-Q3/801_01.png) | goblin soldier walk | 107 x 130 | 2.67 x 3.25 m |
| [`765/01`](ref/GP-Q3/765_01.png) | dead hammer goblin | 73 x 58 | 1.82 x 1.45 m |
| [`785/01`](ref/GP-Q3/785_01.png) | dead horned goblin | 79 x 63 | 1.98 x 1.57 m |
| [`805/01`](ref/GP-Q3/805_01.png) | dead goblin soldier | 119 x 67 | 2.98 x 1.68 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q3/strip.png`](ref/GP-Q3/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Walk frames 56-107 x 107-138 px; death 73-119 x 58-67 px. At 2.5 cm/px x size %: goblins stand **2.7-3.5 m** on their
cards today (1.4-2.7 m wide); a dead goblin with weapon and pool is **1.8-3.0 m long**.

## 3. Where it shows

- **10 placements** on **4 screens**: 680, 712, 713, 748
- by class: `goblin_hammer` 4, `goblin_soldier` 6
- art state today (`art_coverage.py` on master): placeholder 10
- card in the game today: 1.40-2.67 m wide, 2.50-3.45 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 10
- origin IDs: `S680_P11`, `S680_P12`, `S680_P13`, `S680_P14`, `S712_P12`, `S712_P15`, `S712_P17`, `S713_P11`, `S713_P12`, `S748_P03`

## 4. Start from (existing sources, half-done work)

- Rigged sources on master: `Unclaimed/goblin_soldier/...` (`SK_Goblin_Soldier_PR`, scale coat, helmet, shield, bill)
  and `Unclaimed/goblin_hammer/...` (`SK_Goblin_Hammer_PR`, same body, tunic, skullcap, war hammer). STATUS: partial,
  "fused blob body with painted-on clothing, gear skinned by nearest bone, no animation clips". No horned-goblin
  variant exists.
- No goblin work on `art/creature-monsters`; reuse its `clips_monsters.py`, `corpse_blood.py` and `export_monster_ue.py`.

## 5. What to make

Rebuild the goblin body (separate garments and armour over a body, rigid gear on its own bone), three variants
(hammer, horned with spiked club = Mog, soldier with bill and shield), walk/idle/attack clips, and three corpses in
pools posed as 765/785/805 (weapon dropped beside the body).

## 6. Gore bar (owner rule: at least the 1997 level, never less)

765/785/805: each goblin lies **drenched red in a red pool with drops**; the soldier (805) sprawls with his bill
beside him and the pool runs the length of his body. Bar: as much red as the pictures, pool at least the picture
extent (1.8-3.0 m), drops visible.

## 7. Import and binding

- Rig and clips: `Unclaimed/tools/export_monster_ue.py` (on the WIP branch) exports mesh + clips in the creature
  convention; the kit's own `SK_*_PR_LOD*.fbx` are refused by the creature import gate ("non-unit reference bone scale").
  Import with the branch's `Scripts/import_photoreal_art.py` creature section (390 new lines on the WIP branch; the
  duck/slime/pig part of it lands with PR #113), e.g. `DINK_PHOTOREAL_ONLY=goblin Scripts/import_photoreal_art.sh`, one
  Unreal step through `unreal_turn.sh`. Then `git add` the packages and `python3 -I Scripts/scrub_private_paths.py --fix
  DinkRemasterUE/Content/Dink/Photoreal/Creatures/<Name>` from the repository root.
- Binding row (`Content/Dink/Data/Art/creatures.json`, list `classes`; format in `IMPORT.md` "Creature classes"):
  ```json
  {"class": "goblin_soldier", "mesh": "/Game/Dink/Photoreal/Creatures/<Name>/SK_<Name>_PR.SK_<Name>_PR",
   "locomotion": {"idle": "<AN_Idle>", "gaits": [{"clip": "<AN_Walk>", "speed_cm_s": <from clips.json>}, {"clip": "<AN_Run>", "speed_cm_s": <...>}]},
   "roles": {"walk": {"sequences": [801, 803, 807, 809], "locomotion": true}},
   "corpses": [{"sequences": [805], "mesh": "/Game/Dink/Photoreal/Creatures/<Name>/SM_<Name>_Corpse_PR.SM_<Name>_Corpse_PR",
                "decal": {"material": "<pool decal MI>", "size_cm": [<along>, <across>], "depth_cm": 45}}],
   "materials": {"0": "<MI per colour variant>"}, "scale": <fit to the 1997 card>, "note": "<1997 citation>"}
  ```
  The WIP branch already has these rows: correct them, do not start new ones. A row that names a missing asset binds
  nothing (warning `DINK CREATURE CLASS` in the log) and the sprites keep their cards.
- Coverage: `art_coverage.py` counts class-bound placements `final` (`class-bound:` evidence).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/GP-Q3 --name goblins \
    --play 680:354:264 --close 680:354:264 --kill 680:354:264 --play 713:114:108
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q3/goblins_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q3/goblins_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Same files as VS-04 (after it). VS-05 (goblin sanctuary huts) is Stream C and independent.

## 10. Done when

Goblins of 680/712/713/748 and Mog are class-bound; kills leave the three corpses in pools; sheets in the PR.
