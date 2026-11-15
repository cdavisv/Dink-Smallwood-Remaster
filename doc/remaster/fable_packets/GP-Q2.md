# GP-Q2: Slayer corpse (645) and stone giant corpse (825)

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q2 (GORE_STORY_PARITY.md G4) |
| priority (queue) | high |
| estimated size | M (slayer corpse exists on the WIP branch; stone giant corpse has no blood by design) |
| stream | Stream A, monsters, step 3 of that stream |
| kind of work | new art (Blender: corpse rebake) + class corpse rows; half-done branch exists |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

`en-slay`, `s7-slay`, `sc-slay` set `sp_base_walk(640)`; their `sp_base_death(680)` line is commented out
(`en-slay.c:14`), so a kill takes the `base_walk + 5` branch of `add_kill_sprite` (dink.cpp:12374-12383) and leaves
**645**, one picture for every direction, at the slayer's size. `en-stg` has `base_walk 820` and no death: it leaves
**825**. Both stay until the screen changes.

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`645/01`](ref/GP-Q2/645_01.png) | dead slayer | 94 x 67 | 2.35 x 1.68 m |
| [`825/01`](ref/GP-Q2/825_01.png) | dead stone giant | 106 x 67 | 2.65 x 1.68 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q2/strip.png`](ref/GP-Q2/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

645 is 94 x 67 px, 825 is 106 x 67 px: at 2.5 cm/px x 100 % about **2.35 x 1.7 m** (slayer with pool) and **2.65 x
1.7 m** (stone giant). Slayers are placed at 75-100 %, stone giants up to 140 % (cards 1.9-4.5 m wide).

## 3. Where it shows

- **35 placements** on **25 screens**: 28, 35, 106, 127, 137, 138, 156, 157, 166, 178, 182, 183, 209, 211, 212, 213, 215, 242, 245, 246, 448, 652, 663, 695, 696
- by class: `slayer` 21, `stone_giant` 14
- art state today (`art_coverage.py` on master): placeholder 35
- card in the game today: 1.92-4.47 m wide, 1.78-3.50 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 35
- origin IDs: `S028_P03`, `S028_P04`, `S035_P32`, `S106_P18`, `S127_P06`, `S137_P17`, `S138_P16`, `S156_P07`, `S157_P05`, `S157_P06`, `S157_P07`, `S157_P08`, `S166_P25`, `S166_P26`, `S178_P10`, `S178_P11`, `S182_P13`, `S183_P12`, `S209_P14`, `S209_P16`, `S211_P01`, `S212_P08`, `S213_P10`, `S215_P11`, `S242_P15`, `S245_P01`, `S245_P02`, `S246_P03`, `S448_P08`, `S448_P09`, `S652_P02`, `S663_P04`, `S695_P05`, `S696_P02`, `S696_P03`

## 4. Start from (existing sources, half-done work)

- WIP branch `art/creature-monsters` (see VS-04 section 4): `Unclaimed/slayer/Slayer/SM_Slayer_Corpse_PR.fbx` +
  `T_Slayer_PR_Corpse_BC/ORM.png`, corpse row 645 with a 480 x 380 cm decal; `Unclaimed/stone_giant/Stone_Giant/
  SM_Stone_Giant_Corpse_PR.fbx`, corpse row 825 with no decal. Death clips "raised until the lowest bone end clears
  the ground". No sheet of the slayer or giant corpse was made (only bonca, dragon, knight sheets exist): not seen.

## 5. What to make

- Slayer: the body on its back/side with legs curled, cracked chitin, soaked red, in a pool with drops (645).
- Stone giant: a broken heap of sandstone limbs, **no blood** (825 has none), dark grit and dust around it.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

645: the slayer lies in a **bright red pool larger than its body with splashes and drops**, red over the legs and
spikes; 825: **no blood**, the stone body broken into pieces with dark grit (a stone giant that bled would be a
change, not parity). Bar: slayer pool at least the picture's 2.35 x 1.7 m at 100 % with drops; the giant stays bloodless.

## 7. Import and binding

- Rig and clips: `Unclaimed/tools/export_monster_ue.py` (on the WIP branch) exports mesh + clips in the creature
  convention; the kit's own `SK_*_PR_LOD*.fbx` are refused by the creature import gate ("non-unit reference bone scale").
  Import with the branch's `Scripts/import_photoreal_art.py` creature section (390 new lines on the WIP branch; the
  duck/slime/pig part of it lands with PR #113), e.g. `DINK_PHOTOREAL_ONLY=slayer,stone_giant Scripts/import_photoreal_art.sh`, one
  Unreal step through `unreal_turn.sh`. Then `git add` the packages and `python3 -I Scripts/scrub_private_paths.py --fix
  DinkRemasterUE/Content/Dink/Photoreal/Creatures/<Name>` from the repository root.
- Binding row (`Content/Dink/Data/Art/creatures.json`, list `classes`; format in `IMPORT.md` "Creature classes"):
  ```json
  {"class": "slayer", "mesh": "/Game/Dink/Photoreal/Creatures/<Name>/SK_<Name>_PR.SK_<Name>_PR",
   "locomotion": {"idle": "<AN_Idle>", "gaits": [{"clip": "<AN_Walk>", "speed_cm_s": <from clips.json>}, {"clip": "<AN_Run>", "speed_cm_s": <...>}]},
   "roles": {"walk": {"sequences": [641, 643, 647, 649], "locomotion": true}, "attack": {"sequences": [631, 633, 637, 639], "clip": "<AN_Attack>"}},
   "corpses": [{"sequences": [645], "mesh": "/Game/Dink/Photoreal/Creatures/<Name>/SM_<Name>_Corpse_PR.SM_<Name>_Corpse_PR",
                "decal": {"material": "<pool decal MI>", "size_cm": [<along>, <across>], "depth_cm": 45}}],
   "materials": {"0": "<MI per colour variant>"}, "scale": <fit to the 1997 card>, "note": "<1997 citation>"}
  ```
  The WIP branch already has these rows: correct them, do not start new ones. A row that names a missing asset binds
  nothing (warning `DINK CREATURE CLASS` in the log) and the sprites keep their cards.
- Coverage: `art_coverage.py` counts class-bound placements `final` (`class-bound:` evidence).

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/GP-Q2 --name slayer_giant_corpse \
    --kill 157:216:84 --kill 28:426:108 --kill 178:324:84
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q2/slayer_giant_corpse_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/GP-Q2/slayer_giant_corpse_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Needs VS-04 (live classes). The corpse lookup for `base_walk + 5` is the WIP presenter fix (`CorpseFor`): keep its test lines.

## 10. Done when

Slayer and stone giant kills leave 645/825 equivalents; slayer pool at least the picture extent; sheets in the PR.
