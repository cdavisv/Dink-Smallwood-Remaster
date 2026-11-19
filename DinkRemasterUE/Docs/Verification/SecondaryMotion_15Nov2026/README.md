# Secondary motion: hair, the Mother's skirt, hit jolt (15 Nov 2026)

Stream hair-cloth-physics. Code: `Plugins/DinkCore/Source/DinkCore/{Public,Private}/DinkSecondaryMotion.*`,
materials: `Scripts/import_photoreal_art.py` (`hair_motion`, `skirt_motion`), tests: `Dink.Physics.*`
(`Plugins/DinkParity/.../Tests/DinkSecondaryMotionTests.cpp`), capture tools: `Scripts/AnimationQA/secondary_capture.py`,
`secondary_strip.py`, offline checks: `Scripts/PhysicsQA/`.

## What the characters have (inventory)

| | Dink (`SK_Dink_Photoreal`) | Mother (`SK_Mother_Photoreal`) | Milder (`SK_Milder_Photoreal`) |
|---|---|---|---|
| bones | the 89 mannequin bones, nothing else | same | same |
| hair | short crop: opaque cap shell + lock cards + wisps, one Hair slot (also brows and lashes) | drawn back into a bun: cap shell + thin/wisp cards + a modelled bun core | very short crop, same build |
| vertex data | one UV set, no vertex colour (the groom's shell order `hl` is not exported) | same | same |
| root-to-tip | the atlas layout (`Characters/Tools/hairlib.py` `tile_rect`): 32 narrow lock tiles, root at the top | same | same |
| garments | shirt, jerkin, trousers, gear (pack, belt) | dress: bodice, puffed sleeves, floor-length gathered skirt with authored skinning to thighs and calves | armour, tabard, mail skirt to mid-thigh |
| clothing data | none | none | none |

No mesh carries hair, skirt, apron or pouch bones and none carries Chaos clothing data. The pig (`SK_Pig`) is the only
rig with loose-part bones (`ear_l`, `ear_r`, `jaw`, `tail_01..03`).

## Approach and why

- **Hair**: a damped spring per character on the game thread (head acceleration, head turn rate, wind) writes a tip offset
  and a yaw lag into custom primitive data; the hair material turns it into a world position offset weighted from root to
  tip along each lock card. The opaque cap, brows and lashes and the wide tiles (the Mother's bun core) never move; a
  sphere about the head centre stops any offset going into the scalp; the Mother's bun holds the cards drawn into it
  (`HairPinCentre`). No bones are needed, it costs a few microseconds on the CPU and a few dozen ALU per hair vertex.
  A per-strand simulation (Groom) or bone chains would need new hair geometry or skinning (Fable) and are not worth it
  for short crops whose real tips move millimetres.
- **Skirt**: below the hips the skinned skirt is replaced by its bind shape carried by the pelvis (a bell), pushed out
  where a leg would come through it (hip-knee-ankle sampled at nine points; below a contact the fabric hangs, above it it
  runs straight to the waist), lifted by the length the push takes up, and swung behind the hips by a spring. The
  skinned skirt followed whichever thigh or calf each vertex was weighted to, so the hem tore between the forward and the
  trailing leg.
- **Cloth (Chaos)**: not used. No mesh has clothing data (painting it is an art step), it would cost a simulation per
  body, and the editor crash once blamed on cloth (a bad-pointer read in HasActiveClothingAssets) was not a cloth
  simulation: it matches the machine-wide memory faults of 13-16 Nov.
- **Hit jolt**: a spring on spine_03, neck_01 and head (40/30/30 per cent), kicked by a hit, added after the body
  animation; never the root, pelvis, legs or capsule.

## Offline checks (Blender-free: FBX read with numpy, linear blend skinning as the engine does)

`offline/skirt_bell_offline.jpg`, `.json`: Mother's LOD0, synthetic leg poses, skirt edges below the knee.

| pose | skinned: max / p99 stretch, edges > 1.25 | bell: max / p99, edges > 1.25 | leg or shoe vertices outside the skirt (bell) |
|---|---|---|---|
| idle | 1.00 / 1.00, 0 | 1.00 / 1.00, 0 | 0 |
| walk contact (hip 28 / -14, knee 6 / 30) | 6.66 / 4.87, 286 | 1.71 / 1.50, 153 | 0 |
| hurry stride (38 / -22, 10 / 45) | 8.64 / 6.55, 344 | 2.38 / 1.94, 457 | 9 of 680 |
| knee up (45, knee 70) | 4.45 / 3.33, 316 | 1.74 / 1.48, 96 | 0 |
| side step (18 / -6 abduction) | 3.87 / 3.18, 252 | 1.60 / 1.38, 76 | 35 of 706 |

`offline/hair_weight_sheet.jpg`, `.json`: which hair vertices move (red) and which stay (blue).

## In the running game (16 and 19 Nov 2026, master bd6d227a5 and f4743990 with #186's leg layer, #196's creature one-shots and world life + this branch; private copy, offscreen)

Pairs are the same instant with the part switched off (top) and on (bottom), in slow motion.
- `10_mother_skirt_off_on_ingame.jpg`: off, the skinned skirt flares and stretches sideways and forward with each thigh and
  calf (the torn hem of the owner's "stuttered walk" look); on, it hangs as a bell from the hips and swings a little behind
  them; no leg came through it in these 20 pairs; nothing explodes or flickers. (The same on 84e045b0 before #186.)
- `11_hero_hair_off_on_ingame.jpg`, `12_hero_hair_run_start.jpg`: Dink's short crop barely moves (millimetres at the tips,
  as designed for a crop); no card leaves the scalp, no clipping, no popping when he starts to run.
- `13_hero_hit_jolt.jpg`: a hit tips the head and chest a little and they settle in about a third of a second.
- `14_mother_bun_holds.jpg`: the Mother's bun stays pinned while she turns her head.
- Not seen: Milder's capture (his crop is shorter than Dink's), wind on the hair outdoors in a strong gust, the pig's and
  pillbug's loose parts (creature hook) in a rendered capture.

## Tests and probe (19 Nov 2026, master f4743990 + this branch, world regenerated with `--export`, character materials regenerated from the merged importer)
- `Dink.Physics+Dink.Report.PhysicsConstraints+Dink.Animation+Dink.Creature+Dink.Input+Dink.World`: 38/38.
- Full `Dink`: 357/357. Probe: all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md`.
- The vegetation parents (`M_Veg_Foliage`, `M_Veg_Bark`) and `MPC_Dink_World` regenerated from the merged importer are byte-identical to master's, so only the hair and the Mother's outfit materials change.
- Not checked: packaged build; Milder and the creature loose parts in a rendered capture; the Mother's new bob (art-people-3 rebuilds her hair; the contract holds, `HairPinRadius` 0 pins nothing).
