# CG-6: The grey chequered cylinder where a duck dies is the burst sprite 164: give 164 its effect (with GP-Q9)

| | |
|---|---|
| queue row | PR #113 review (coordinator, 15 Nov) |
| priority (queue) | 2 (review) |
| estimated size | S |
| stream | Stream D, ground, water, effects, hero, step 3 of that stream |
| kind of work | effect row (from GP-Q9) + one code decision; not a separate asset |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

The duck's second blow runs `add_sprite(x, y, 7, 164, 1)` (dink.cpp:12732, brain 7: play once and vanish). The #113 README calls the cylinder "an unbound sprite that the duck's script creates": it is this engine-made 164 sprite, drawn as the grey script-sprite marker because 164 has no effect row.

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`164/01`](ref/CG-6/164_01.png) |  | 62 x 41 | 1.55 x 1.02 m |
| [`164/07`](ref/CG-6/164_07.png) |  | 87 x 72 | 2.17 x 1.80 m |
| [`164/14`](ref/CG-6/164_14.png) |  | 115 x 118 | 2.88 x 2.95 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/CG-6/strip.png`](ref/CG-6/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

As GP-Q9 / CG-1 (164 up to 2.9 x 3.0 m).

## 3. Where it shows

Every duck killed by the second blow (screens 536, 374 in the #113 sheets) and every killed sprite without a death picture.

## 4. Start from (existing sources, half-done work)

- #113 already draws a burst for the duck (`DinkCreatureGore.cpp`, `bBurstKill`). Decision for the code owner: either the 164 sprite draws nothing where a class body burst was drawn, or the class burst is dropped and the 164 effect row draws it everywhere (one look).
- Evidence: `Docs/Verification/CreatureGore_14Nov2026/gore_2_duck_burst.jpg` (#113).

## 5. What to make

Nothing beyond GP-Q9's 164 effect; then hide the marker for 164 under a class burst (code) or bind the row.

## 7. Import and binding

See GP-Q9.

## 8. Prove it in the game

From `DinkRemasterUE/` of your private copy (offline, writes two scripts):
```bash
python3 -I Scripts/CreatureQA/make_scripts.py --out Saved/PhotorealPass/fable/CG-6 --name duck_burst \
    --kill 536:258:174
# then ONE Unreal step per call, through the lock of the shared checkout:
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-6/duck_burst_after.txt"
<shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh "$PWD/Saved/PhotorealPass/fable/CG-6/duck_burst_before.txt" -dpcvars=dink.CreatureClassArt=0
```
The `<screen>:<x>:<y>` points are walkable map points (hardness 0 in a 17 px square) computed for this packet from
`Content/Dink/Data/Gameplay/Hardness`; `--kill` swings at whatever comes at the player with strength 60. Sheets: `Scripts/CreatureQA/sheet.py` (see `Scripts/CreatureQA/README.md`).

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- PR #113 merged; GP-Q9's 164 effect.

## 10. Done when

No grey cylinder in any duck-kill shot.
