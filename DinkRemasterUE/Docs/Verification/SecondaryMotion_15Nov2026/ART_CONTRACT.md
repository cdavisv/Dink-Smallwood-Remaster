# Secondary motion: what it reads from the character art (contract, 15 Nov 2026)

Owner: stream hair-cloth-physics (branch `phys/hair-cloth`). Code `DinkCore/DinkSecondaryMotion.*`, materials
`Scripts/import_photoreal_art.py` (`hair_motion`, `skirt_motion`, `HAIR_LOOK`, `SKIRTS`). Any change to card count, UV
layout, bone names or skirt skinning of Dink, Mother or Milder: write it in the Master log of COMMON_RULES.md first and
tell this stream; the checks in `Scripts/PhysicsQA/` (`hair_check.py`, `skirt_check.py`) re-run on the new FBX in seconds.

## Hair (material `M_<Name>_PR_Hair`, slot `MI_<Name>_PR_Hair`)

Read per vertex, nothing else:
- **UV channel 0 only** (no vertex colour is read; none is exported today). Engine v runs DOWN the atlas (v_engine =
  1 - v_blender). Layout is `Characters/Tools/hairlib.py` `tile_rect` / `CAP_RECT`:
  - **cap shell** = u < 0.5 and v_engine <= 0.5 (Blender cap rect u 0-0.5, v 0.5-1): never moves.
  - **brow and lash band** = v_engine > 0.75 (Blender v < 0.25): never moves.
  - **wide tiles** 32-35 = u < 0.5 and 0.5 < v_engine <= 0.75: never moves (Dink's dense under-layer, the Mother's bun core
    uses tile 32).
  - **narrow lock tiles** 0-31 = u >= 0.5, v_engine <= 0.75: 2 rows of 16, each 0.375 tall, ROOT AT THE TOP of the tile.
    Root-to-tip t = (v_engine - row * 0.375) / 0.375; weight = kind * t^1.5 with kind by tile index (hair_groom.py `NT`
    default order: 0-8 dense 0.3, 9-18 mid 0.55, 19-25 thin 0.8, 26-29 wisp and 30-31 fly 1.0). A vertex exactly on the
    row seam (v_engine = 0.375) gets 0.2.
- **PreSkinnedPosition** (bind pose, mesh space, engine axes = Blender x, -y, z) for the pin only.
- **Bun pin**: instance parameters `HairPinCentre` (vector, bind-pose mesh space, cm) and `HairPinRadius` (cm): hair within
  the radius does not move, fading over the next 4 cm. Mother today: centre (-0.13, -9.99, 165.72), radius 5.5 (the bun
  core's centroid, radius 4.6 + 1). A moved, resized or new bun must update these in `HAIR_LOOK['Mother']`.
- Material parameters owned: `HairMotion` (1), `HairMotionMaxCm` (2), `HairMotionSeam` (0.2), `HairPinCentre`,
  `HairPinRadius`, and the CPD-backed `HairTip`, `HairHead`.

What keeps working if the art changes: any card count, any lock shape, as long as cards stay on the narrow tiles with the
root at the top of the tile and the cap/brow/wide regions keep their meaning. What breaks it: moving the cap, brows or
bun core onto the narrow tiles (they would sway), cards with the root at the bottom of a tile (they would swing at the
scalp), a new tile kind order, or a second UV set used instead of channel 0. Preferred future (queue row SP-01): export
the shell order `hl` and root-to-tip as vertex colour R and G, then the material reads those instead of the atlas.

## Skirt (material `M_Mother_PR_Outfit` only; `SKIRTS = {'Mother'}`)

- Reads **PreSkinnedPosition** (bind pose) and the skinned position. Below the hips (smoothstep from 2 cm above the
  hip joints to 55% of the way down to the knees, bind-pose height) the skinned skirt is replaced by its bind shape
  carried by the pelvis and pushed out by the legs. So the bind-pose skirt must be the hanging rest shape (as now: legs
  slightly apart, hem clear of the shoes), and the skirt must stay in the Outfit slot; anything else of the Outfit slot
  below the hips also follows the bell (nothing today: arms, hands and belt are other slots or above the hips).
- Bones read: `pelvis`, `thigh_l/r`, `calf_l/r`, `foot_l/r` (mannequin names). Leg radii are instance parameters
  `SkirtKneeRadius` (7), `SkirtAnkleRadius` (6), `SkirtClearance` (1.5), `SkirtSpread` (2.5), `SkirtTopCm` (2),
  `SkirtFull` (0.55), `SkirtMotion` (1).
- Skinning: below the hips the skin weights are ignored (except in the blend band). Leg weights in the blend band fight
  the bell; the cleanest source is skirt weights on the pelvis only below the hips (queue row SP-02), which also stops
  the tearing wherever the material is not used (corpse pose, previews). New skirt bones would replace the bell; tell
  this stream first.

## Custom primitive data (all character skeletal mesh components)

UDinkSecondaryMotionSubsystem writes floats 0-35 every frame on the bodies it tracks (by mesh asset name: SK_Dink_Photoreal,
SK_Mother_Photoreal, SK_Milder_Photoreal, SK_Dink, SK_Dink_Hands, SK_Mother, SK_Milder, SK_Pillbug(_Photoreal), SK_Pig).
No other material of these meshes may use custom primitive data:
- 0-2 hair tip offset, 3 hair yaw lag (rad), 4-6 head centre, 7 hair weight (component space, mesh units)
- 8-11 pelvis-rigid rotation (quaternion; all zero = skirt off), 12-14 its translation, 15-17 hip L, 18-20 knee L,
  21-23 ankle L, 24-26 hip R, 27-29 knee R, 30-32 ankle R, 33-35 skirt sway (read as aligned float4s at 8, 12, ... 32)

## Bones

The hair and skirt need no bones beyond the 89 mannequin bones. Creature loose parts read these bone names (renaming them
switches the motion off): pillbug `antenna_01_l`, `antenna_02_l`, `antenna_01_r`, `antenna_02_r`, `tail`; pig `ear_l`,
`ear_r`, `tail_01`-`tail_03`. The hit jolt turns `spine_03`, `neck_01`, `head`.
