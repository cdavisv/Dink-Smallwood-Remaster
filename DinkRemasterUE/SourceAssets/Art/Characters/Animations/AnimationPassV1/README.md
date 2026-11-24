# Animation pass 1: hero and NPC clips, authored by code

**Since pass 2 (12 Nov 2026) the runtime plays only the action clips from here** (fist combo, sword cuts, `Hurt`, `Stumble`, `Bow_Draw`, `Bow_Release`, `Cast`). Idle, walk, run, jump, fall and land come from the engine template's motion capture (`Content/Dink/Data/Art/animation_natural.json`). The generated locomotion and idle clips below are still built and imported so that `dink.BodyAnimation 2` can show them for comparison. The pass 2 strips of the revised and new action clips are in `Strips/hero_attack2/`.

Thirty clips for the shared 89-bone rig (Dink, Mother, Milder): locomotion, idles, jump, the fist combo, sword cuts, a hurt flinch and a stumble. Nothing is keyed by hand in a `.blend`: the Python under `Tools/` is the source, the FBX files under `Export/` are what Unreal imports, and `Strips/` holds the contact strips the clips were reviewed from.

The motion is original project work (procedural keyframes: analytic two-bone IK, heel/flat/ball foot roll, pelvis and spine rotation). No motion capture and no third-party animation is used. The rig is the project's existing Epic-compatible skeleton; the preview meshes are the project's existing characters.

## Hero mannerisms (clips of 13 Nov 2026; played in the game by the mannerism runtime since 23 Nov 2026)

`Tools/clips_mannerisms.py` adds fifteen clips for the hero's growth arc (strips in `Strips/hero_manner/`):

| Clip | What it is |
|---|---|
| `Posture_Timid`, `Posture_Confident` | ADDITIVE poses: each bone's rotation away from the rest pose. The runtime applies them in the bone's own frame over whatever is playing, mixed by confidence (`Preview_Posture` shows 0, 0.25, 0.5, 0.75, 1 on the stand). Timid: rounded upper back, neck and head forward and down, shoulders in and up, arms turned in, slack elbows, pigeon toes. Confident: chest lifted, shoulders back, chin level. |
| `RunArms_Timid` | Additive: elbows out and forearms dangling, shown only while an unsure Dink runs. |
| `Trip_Walk`, `Trip_Run` | A toe catch (upper body over the walking legs): lurch, arms out, and at a walk a look back at the ground. |
| `Jump_Timid` | The flailing hop; mixed by confidence with the motion-capture jump. |
| `Botch_Stagger`, `Botch_Faceplant` | Botched landings: two lunging catch steps, or flat on his face, a beat, up again and the dirt slapped off. The feet end where they began. |
| `Fidget_Scratch`, `Fidget_Scuff`, `Fidget_Nose`, `Fidget_Proud` | Standing about: a scratch of the backside, a toe ground into the dirt with a hand at the neck, the nose wiped on a sleeve; the hero squares his shoulders and looks over the land. |
| `Sword_Slash_1_Timid`, `Sword_Slash_2_Timid`, `Sword_Chop_Timid` | The three cuts over-swung: contact still at 0.175 s, then the blade carries him round and he catches himself. Paired with the plain `Sword_*` clips by confidence. |

Build only these with `--only` (a full `--export` would rewrite every FBX and its hash):

```
ALSOFT_DRIVERS=null blender -b -t 4 --python SourceAssets/Art/Characters/Animations/AnimationPassV1/Tools/build.py -- --export --strips --tag manner --only Posture_Timid,Posture_Confident,RunArms_Timid,Trip_Walk,Trip_Run,Jump_Timid,Botch_Stagger,Botch_Faceplant,Fidget_Scratch,Fidget_Scuff,Fidget_Nose,Fidget_Proud,Sword_Slash_1_Timid,Sword_Slash_2_Timid,Sword_Chop_Timid,Preview_Posture
```

`Preview_*` names are review strips and are never exported. `Preview_<clip>_C0` shows an action clip under the timid stoop as the game mixes it at confidence 0 (the sword cuts keep 0.4 of it): the fidgets, botches and trips are authored for that sum (`Fidget_Scuff`: its own nod is 9 degrees, not 30).

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
- `Grip_R` and `Grip_L` (family `hero_pose`) are POSES: the runtime uses only their last frame, on the finger bones of the hand that holds a weapon and, while no action plays, on that arm (`UDinkBodyAnimInstance::SetGrip`). The finger angles (`rig.py` `GRIP`) are fitted to the handle where `Content/Dink/Data/Art/hero_weapons.json` puts the weapon; the arm (`clips_attacks.py` `CARRY`) is the guard of the armed Dink's 1997 idle pictures. Rebuild both after changing either, and check with `Dink.Art.HeroWeapon.GripClosesTheHand`.

## Known weaknesses (from the last review of the strips)

See `Docs/AnimationPass/NOTES.md` for the full list. In short: these are clean procedural cycles, not motion capture. Trunks are stiff, runs overstride, the fighting stance is narrow and crouched, the timid haymaker is weak at contact, idles are very quiet, and the sword cuts are placeholders that have not had a full review.
