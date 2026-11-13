# Animation pass 1: hero and NPC clips, authored by code

**Since pass 2 (12 Nov 2026) the runtime plays only the action clips from here** (fist combo, sword cuts, `Hurt`, `Stumble`, `Bow_Draw`, `Bow_Release`, `Cast`). Idle, walk, run, jump, fall and land come from the engine template's motion capture (`Content/Dink/Data/Art/animation_natural.json`). The generated locomotion and idle clips below are still built and imported so that `dink.BodyAnimation 2` can show them for comparison. The pass 2 strips of the revised and new action clips are in `Strips/hero_attack2/`.

Thirty clips for the shared 89-bone rig (Dink, Mother, Milder): locomotion, idles, jump, the fist combo, sword cuts, a hurt flinch and a stumble. Nothing is keyed by hand in a `.blend`: the Python under `Tools/` is the source, the FBX files under `Export/` are what Unreal imports, and `Strips/` holds the contact strips the clips were reviewed from.

The motion is original project work (procedural keyframes: analytic two-bone IK, heel/flat/ball foot roll, pelvis and spine rotation). No motion capture and no third-party animation is used. The rig is the project's existing Epic-compatible skeleton; the preview meshes are the project's existing characters.

## Rebuild

From `DinkRemasterUE/`:

```
ALSOFT_DRIVERS=null blender -b -t 4 --python SourceAssets/Art/Characters/Animations/AnimationPassV1/Tools/build.py -- --export
ALSOFT_DRIVERS=null blender -b -t 4 --python SourceAssets/Art/Characters/Animations/AnimationPassV1/Tools/build.py -- --strips --tag loco --only Walk_Timid,Walk_Confident
ALSOFT_DRIVERS=null blender -b -t 4 --python SourceAssets/Art/Characters/Animations/AnimationPassV1/Tools/build.py -- --strips --character mother --tag loco --only NpcF_Walk
Scripts/import_animation_pass.sh
```

`--export` writes `Export/A_<clip>.fbx` (armature only, centimetres) and `animation_manifest.json` (per clip: frames, speed, stride, planted-foot drift, IK clamps, events, FBX hash). `--strips` renders side and front views every few frames with travelling ground posts and red marks under planted sole points (Pillow is needed for the tiling, with the system Python). `Scripts/import_animation_pass.sh` imports the FBX files to `/Game/Dink/Hero/Animations/Pass1` and publishes `Content/Dink/Data/Art/animation_pass.json`, which the runtime reads; it refuses to continue if the shared skeleton changes.

## Files

| File | What it is |
|---|---|
| `Tools/rig.py` | Kinematics on the rig in armature space: FK, two-bone IK, aiming, foot roll about heel and ball, spine and head helpers, fingers |
| `Tools/gait.py` | Parametric walk and run cycles; the planted foot travels backwards at exactly the clip speed |
| `Tools/clips_locomotion.py` | `stand_pose`, walks, runs, shuffle, idles, jump/fall/land, NPC clips |
| `Tools/attack_tools.py`, `Tools/clips_attacks.py` | Keyed body states for the fist combo, sword cuts, hurt and stumble |
| `Tools/build.py`, `Tools/compose_strip.py` | Measure, render strips, export |

## Contracts the runtime relies on

- Root at the origin, in place, no root motion; the character faces -Y in Blender (+Y in the Unreal mesh).
- Locomotion loops start at the left heel strike, so the runtime can blend them in phase. `speed_m_s` and `stride_m` in the manifest are what makes the feet stick: the runtime advances the cycle by distance covered over the blended stride.
- Every attack has its contact pose at 0.175 s (the original hit frame) and is back near a guard by 0.4 s (the original lock). These times are documentary: gameplay keeps its own clock and the clips carry no notifies.
- `_Timid` and `_Confident` variants of a clip are blended by the hero's confidence.

## Known weaknesses (from the last review of the strips)

See `Docs/AnimationPass/NOTES.md` for the full list. In short: these are clean procedural cycles, not motion capture. Trunks are stiff, runs overstride, the fighting stance is narrow and crouched, the timid haymaker is weak at contact, idles are very quiet, and the sword cuts are placeholders that have not had a full review.
