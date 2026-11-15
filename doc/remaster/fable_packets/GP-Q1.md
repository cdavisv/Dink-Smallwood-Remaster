# GP-Q1: Bonca corpses lying in their blood (grey, brown, purple, Bong, sc-lock)

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q1 (gore audit `doc/remaster/GORE_STORY_PARITY.md` G4, G5) |
| priority (queue) | high |
| estimated size | M (corpse mesh exists on the WIP branch; pool and colour to the 1997 extent) |
| stream | Stream A, monsters, step 2 of that stream |
| kind of work | new art (Blender: corpse rebake, pool) + class corpse rows; half-done branch exists |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

`en-bonc`, `en-bonc1`, `en-boncd`, `s2-cbon` (brown, base_walk 530), `en-bong`, `s7-bong`, `sc-lock` (grey "Bong",
600) and `en-pbon` (purple, 610) all set `sp_base_death(&current_sprite, 550)`. A kill runs `add_kill_sprite`
(`source/dink/dink.cpp:12359-12420`): it adds a brain-5 sprite of sequence 550 + direction (551/553/557/559; an
inactive direction is mirrored, dink.cpp:12391-12403) at the bonca's position and size, which stays until the
screen is drawn again. **All three colours leave the same brown body** (there is only one death set): the
remaster may keep that or tint per colour, but never less blood.

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`551/01`](ref/GP-Q1/551_01.png) | dead bonca, dir 1 | 81 x 61 | 2.02 x 1.52 m |
| [`553/01`](ref/GP-Q1/553_01.png) | dead bonca, dir 3 | 96 x 54 | 2.40 x 1.35 m |
| [`557/01`](ref/GP-Q1/557_01.png) | dead bonca, dir 7 | 92 x 58 | 2.30 x 1.45 m |
| [`559/01`](ref/GP-Q1/559_01.png) | dead bonca, dir 9 | 79 x 62 | 1.98 x 1.55 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q1/strip.png`](ref/GP-Q1/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Death frames 79-96 px wide, 54-62 px tall at 2.5 cm/px x size % (the boncas are placed at 75-100 %; the card of
the live bonca today is 2.0-3.3 m wide): **body and pool together about 2.0-2.4 m long and 1.4-1.6 m deep**; the
pool alone is about 1.3-1.5 times the body's length. The WIP decal is 420 x 340 cm (`creatures.json` WIP rows).

## 3. Where it shows

- **43 placements** on **25 screens**: 27, 29, 74, 90, 98, 100, 137, 156, 160, 170, 302, 306, 480, 514, 515, 547, 562, 577, 583, 609, 632, 633, 648, 696, 715
- by class: `bonca_brown` 12, `bonca_gray` 21, `bonca_purple` 10
- art state today (`art_coverage.py` on master): cut 1, placeholder 42
- card in the game today: 1.98-3.27 m wide, 2.05-2.80 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 43
- origin IDs (first 40 of 43): `S027_P10`, `S029_P03`, `S029_P04`, `S029_P05`, `S029_P06`, `S029_P07`, `S074_P23`, `S090_P06`, `S090_P07`, `S090_P08`, `S090_P09`, `S098_P03`, `S100_P35`, `S137_P18`, `S156_P06`, `S160_P07`, `S160_P08`, `S160_P09`, `S170_P13`, `S170_P14`, `S302_P06`, `S302_P07`, `S306_P06`, `S480_P04`, `S480_P05`, `S514_P15`, `S514_P16`, `S515_P14`, `S547_P14`, `S547_P16`, `S547_P17`, `S562_P03`, `S577_P14`, `S577_P15`, `S583_P09`, `S583_P10`, `S609_P13`, `S632_P11`, `S632_P12`, `S633_P16`
- every killed one, placed or script-made (`sc-lock` spawns on lock screens)

## 4. Start from (existing sources, half-done work)

- WIP branch `art/creature-monsters` (local worktree `DinkGate2Creatures`, see VS-04 packet section 4): source
  `Unclaimed/bonca_gray/Bonca/SM_Bonca_Corpse_PR.fbx` with `T_Bonca_PR_Corpse_BC.png` / `_ORM.png` (posed from the
  death clip, blood composited by `Unclaimed/tools/corpse_blood.py`), the package
  `Content/Dink/Photoreal/Creatures/Bonca/SM_Bonca_Corpse_PR` + `M_Bonca_Corpse_PR`, and corpse entries in the three
  bonca rows of `creatures.json` (sequences 551-559, decal 420 x 340 cm).
- Seen on its sheet (`Docs/Verification/Monsters_14Nov2026/bonca.jpg`, bottom row, looked at for this packet): the
  body lies blood-smeared on a red pool, but the pool is **a compact puddle about the body's length with no thrown
  drops** and the body is tan, while 551/553 show a dark brown body inside a pool clearly larger than it with a ring of
  scattered drops. Grade: less than 1997 on pool extent and splatter.
- Reference recipes: the pillbug carcass (`Creatures/Tools/pillbug.py -- corpse`: blood composited in texture space,
  lobed pool with thrown streaks, decal 620 cm) and the corpse kit pool cards (`Corpses/tools/gore_sheets.py`).

## 5. What to make

Rebake the bonca corpse to 551-559: the dark brown striped body (match VS-04's hide), soaked red over its belly and
flanks, lying in a lobed pool larger than the body plus thrown drops in a ring, the red as saturated as the
picture. Pool as an alpha-tested card on slot 1 *and* as the class decal (the grass carpet hides flat meshes on
grass; the decal stains the blades). Decal size at least the picture's extent at the placement's size.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

1997 (551-559): a dead bonca on its side in a **bright, saturated red pool** (palette red, no brown) that spreads
**beyond the body on every side, about 1.3-1.5 x its length**, with **dozens of separate drops** thrown around it up
to a body-width away; red smeared over the body. It stays until the screen changes. Remaster bar: same or more red,
pool at least the picture's extent (about 2.0 x 1.4 m at 100 %), visible drops, visible on grass at the play camera.

## 7. Import and binding

- Rig and clips: `Unclaimed/tools/export_monster_ue.py` (on the WIP branch) exports mesh + clips in the creature
  convention; the kit's own `SK_*_PR_LOD*.fbx` are refused by the creature import gate ("non-unit reference bone scale").
  Import with the branch's `Scripts/import_photoreal_art.py` creature section (390 new lines on the WIP branch; the
  duck/slime/pig part of it lands with PR #113), e.g. `DINK_PHOTOREAL_ONLY=bonca Scripts/import_photoreal_art.sh`, one
  Unreal step through `unreal_turn.sh`. Then `git add` the packages and `python3 -I Scripts/scrub_private_paths.py --fix
  DinkRemasterUE/Content/Dink/Photoreal/Creatures/<Name>` from the repository root.
- Binding row (`Content/Dink/Data/Art/creatures.json`, list `classes`; format in `IMPORT.md` "Creature classes"):
  ```json
  {"class": "bonca_gray", "mesh": "/Game/Dink/Photoreal/Creatures/<Name>/SK_<Name>_PR.SK_<Name>_PR",
   "locomotion": {"idle": "<AN_Idle>", "gaits": [{"clip": "<AN_Walk>", "speed_cm_s": <from clips.json>}, {"clip": "<AN_Run>", "speed_cm_s": <...>}]},
   "roles": {"walk": {"sequences": [601, 603, 607, 609], "locomotion": true}},
   "corpses": [{"sequences": [551, 553, 557, 559], "mesh": "/Game/Dink/Photoreal/Creatures/<Name>/SM_<Name>_Corpse_PR.SM_<Name>_Corpse_PR",
                "decal": {"material": "<pool decal MI>", "size_cm": [<along>, <across>], "depth_cm": 45}}],
   "materials": {"0": "<MI per colour variant>"}, "scale": <fit to the 1997 card>, "note": "<1997 citation>"}
  ```
  The WIP branch already has these rows: correct them, do not start new ones. A row that names a missing asset binds
  nothing (warning `DINK CREATURE CLASS` in the log) and the sprites keep their cards.
- Coverage: `art_coverage.py` counts class-bound placements `final` (`class-bound:` evidence).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/GP-Q1 --name bonca_corpse \
    --kill 29:300:90 --kill 90:210:198 --kill 514:270:150
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q1/bonca_corpse_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q1/bonca_corpse_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Look at each `*_kill_*_after.png` against [`ref/GP-Q1/strip.png`](ref/GP-Q1/strip.png); one grass screen (90) and one bare one (29).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs the live bonca class of VS-04 (same row). Blocks nothing else. Code stop-gap C1 of the gore audit (1997 death picture on a card for unbound monsters) is not needed once this binds.

## 10. Done when

Every bonca kill leaves the body in a pool at least the extent of 551-559 with thrown drops, on grass and on bare ground; sheet with 1997 frame beside the game frame in the PR evidence.
