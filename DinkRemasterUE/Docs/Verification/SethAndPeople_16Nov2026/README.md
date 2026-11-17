# Seth as the villain, and the people's close-ups (16 Nov 2026)

Queue rows SP-06 (Seth, follow-up of PQ-Q1), SP-04 (eyes without an iris), SP-05 (knights), SP-09 (maidens' hair).
Art, data and tools only: no C++ changed.

## 1. Seth, the last enemy (`s7-boss`, made by Milder's scene `s7-mil` on SCR_086)

He was in the game as a first model: the hero's body with the hero kit's young face grown 1.8 times, the hero's hair
cards turned up, bare hands, arms at his sides. His 1997 pictures (`graphics/effects/magic/pose` = sequence 580 and
`seth1w..9w` = 581-589) show an older, harder face under a tall swept crest of brown hair, a dark red jerkin over
speckled slate-blue sleeves, dark gloves, and in the standing picture crossed arms over a wide stance.

| Part | Before | Now |
|---|---|---|
| Face | the hero's sculpted face, grown | his own head stage (`NPC/Seth/cfg/head.json`): a long narrow jaw, hollow cheeks, a heavier brow lowered over half-closed lids, a longer nose, a thin mouth pulled up on one side; the eyes look down at his visitor (`gaze`) |
| Skin | the hero's set, tinted pale | his own set (`cfg/skin.json`): age lines, stubble, sallow; dark leather gloves painted on the hands |
| Eyes | the hero's blue-grey | dark brown (`eye_tex.py`) |
| Hair | the hero's cards turned up | a groom of his own, new kind `crest`: the top hair stands from a high hair line and is brushed back to a ridge above the skull |
| Sleeves | the hero's shirt recoloured | the shirt as riveted mail (colour, normal, roughness and metal maps, `seth_outfit.py`); the jerkin a deeper red, the trousers a darker slate |
| Standing | the mannequin idle, arms hanging | clip `Seth_Pose` by code (`AnimationPassV1/Tools/clips_people.py`): arms crossed, feet wide apart; the role `pose` (picture 580) of his class row |

The 1997 head size (a quarter of his height) is kept. No animation hook was needed: a class role already takes its
own locomotion set, so picture 580 plays the crossed arms and the walking pictures 581-589 keep the mannequin walk.

## 2. People close-ups

- **Eyes without an iris (SP-04): the cause was skin weights**, not the material, the UVs or a bake. The Unclaimed
  sources weight the skin of the face partly to the neck (a quarter at eye level) while the eyeballs are all head.
  When the mannequin's clips turn or nod the head, the eyeball travels behind the lids: measured on the ported
  merchant, a 15 degree nod moves the eyeball 9.3 mm against the lid opening (an iris is 12 mm across), so the iris
  went under the lid and a pale ball showed. `npc_port.py` now makes everything within 7 cm of an eye head-only,
  fading to the source weights at 12 cm: 1 mm. Merchant, girl, peasant, old man and gnome wizard were ported again.
- **Maidens (SP-09)**: the three colour twins were copies of the Mother with her bun. They are now twins of a base
  figure of their own, `NPC/Maiden`: the Mother's body and dress without her stout build, a head stage of her own,
  the young skin set, and long loose yellow hair with a fringe (new groom kind `long`; the brown maiden's hair is
  tinted auburn, as picture 241).
- **Knights (SP-05)**: a body under the plates (`npc_port.py` `add_body`: tubes, joint balls and a lofted trunk in the
  harness's own mail) so that one no longer looks through the joints, and the idle clip `Guard_Stand`, which closes
  the right fist on the halberd. The shaft still stands on the root bone; the clip places the wrist on it every
  frame, so the hand does not slide while he breathes.

## Sheets (game frames from the rendered game; 1997 pictures beside them)

| Sheet | What it shows |
|---|---|
| `01_seth_pose_1997_before_after.jpg` | the 1997 pictures 580 (pose) and 581 (walking); the first model on master; Seth now, same camera, during Milder's scene on SCR_086 |
| `02_seth_close_up_before_after.jpg` | the camera of the talk: before; now head, face, three-quarter, side, crossed arms |
| `03_seth_play_camera_before_after.jpg` | play camera: he appears behind Milder's body, Dink, Milder and Seth from the side, two frames of the talk |
| `04_seth_crest_and_arms.jpg` | the 1997 walking pictures from four sides beside the crest from behind and the arms from his right |
| `05_seth_fight.jpg` | the fight: he walks on the mannequin clips, his explosion is still the 1997 picture card |
| `10_people_eyes_before_after.jpg` | merchant, girl, peasant, old man, gnome wizard: before (no iris) and now |
| `11_maidens_1997_before_after.jpg` | 1997 pictures 251 and 221; before (the Mother with her bun); now the blue maiden of SCR_004 and the wench of the bar of Terris (SCR_034) |
| `12_knights_before_after.jpg` | 1997 picture 287; before (halberd beside the hand); now the guards of the throne room (SCR_070) and the silver knight of SCR_408; throne room and hall at the play camera |
| `20_blender_sources.jpg` | source renders: Seth in the pose clip, his face, the maiden, the knight's fist on the shaft |

## What I saw

**Seth, against pictures 580-589.** At the play camera he now reads as the 1997 figure: feet apart, arms crossed
high on the chest, dark gloves, a deep red jerkin over slate-blue sleeves, dark trousers, a head a quarter of his
height under a tall swept crest. In the close-up of the talk the face is a hard older man's: lined forehead, heavy
straight brows, half-closed lids, a thin mouth pulled to one side, stubble shadow on jaw and lip; the mail of the
sleeves reads as a fine mesh, the right glove grips the left upper arm. From behind the crest stands above the pack as
in `seth7w`/`seth9w`. Below the 1997 picture or below bar: the crest is a smooth wave, the picture's is more ragged and
has fuller sides (his temples are short, skin shows above the ear in profile); the jerkin has no puffed shoulder
caps; the gloves have no cuffs of their own; in the fight he walks with the mannequin's plain walk; in the sheet's
talk frame his head is turned in the clip, so he looks past the camera; frame `06_dialogue_10` shows a white
rectangle beside Dink (a script sprite card, not from this change: reported in the Master log).

**Eyes, SP-04.** Every ported figure now shows iris and pupil in the game, looking ahead. The faces themselves stay
plain and smooth, the girl has an adult's face made small, the beards of the old man and the gnome are clay-like
slabs: below bar in a close-up, fine at the play camera.

**Maidens, against pictures 221-259.** Long yellow hair with a fringe down the back to the waist, as the pictures;
from behind it reads right at once. From the front, in the window back-light of SCR_004, it is a dull straw blonde
and the top is thin; the face is the Mother's head stage with her worried brow, which does not suit a maid; the
dress has no white collar and cuffs. The brown maiden (S410_P06) is vision-gated and was not in the frame: her auburn
tint is NOT seen in the game.

**Knights, against picture 287.** The guards hold their halberds: the right arm is bent and the gauntlet closed on
the shaft, at the play camera of the throne room and close. No look through the joints from the angles captured. The
harness is still smooth swept plate without straps or wear and reads as toy armour close up; the blue is near black
in the dim hall.

## Rejected and rebuilt on the way

- Seth's first crest was a rounded dome like a bowl cut, the second a spiky flame; the third is a swept wave (tips
  brushed back, locks of nearly one length).
- Dark red strokes at his mouth corners and a blotch on the jaw: the inside of the mouth pushed out through the
  cheek by face operations along the vertex normals. Cheek hollows are now translations.
- White of the eye outside the outer corners: the face was lengthened about a point below the eyes while the eyeballs
  stay where they are. It is lengthened about the eye line now.
- In the first game frames his eyes were rolled up under the lowered lids and his hair read grey under the dim sky
  of SCR_086: the eyes now look down 13 degrees, the lids are eased, the hair tint is a warm brown with less gloss.
- The maiden's first hair stood off the head like a mane, the second slid in strands down her sleeves; it is now
  combed onto the skull, tucked behind the shoulders and fanned over the back. In the first game frames it read
  dark from the front in window back-light: brighter tint, less depth shading.
- The knight's fist first reached across to the wrong side (sign of the shaft's x) and then could not reach a shaft
  36 cm out: the shaft stands 30 cm out now.

## Proof

All Unreal steps ran in a private copy, one step per turn. The branch was rebased three times while master moved
(097c0699, 5ccf38dd, 280f7bd1, then 15c980de for the push); the last full proof is on **master 5ccf38dd (#196) + this change**:

- Build: `BUILD OK` (17 s incremental); the log shows the files #196 changed compiling (`DinkCreatureClassComponent`,
  `DinkCreatureOneShots`, `DinkCreaturePresenter`, `DinkCreatureSubsystem`, their tests): the code that plays class figures.
- Frames: every game frame of the sheets is from that tree (capture after the build): the pose role and the guards'
  idle play with #196's one-shot layer in.
- `Dink.Art+Dink.Animation+Dink.Movement`: **92/92 passed** (5 with warnings, as on master).
- `Dink.Gameplay.Probe`: **29/29 passed**; all twenty chapter md5s equal to `Plugins/DinkParity/Docs/packaged_probe.md` of that master (the table is the same on 280f7bd1).
- On master 097c0699 + this change, with the world regenerated (`import_greybox.sh --region all --export`, then
  stonebrook): the same filter 92/92 twice (before and after the maiden's hair cards were cut to the triangle cap) and
  `Dink.Gameplay.Probe` 29/29 with all twenty chapter md5s equal to `Plugins/DinkParity/Docs/packaged_probe.md`.
- Python unit tests (`Scripts/tests`): **1019 OK** (1 skipped) on the pushed tree (280f7bd1 + this change).
- `verify_sources.py --metadata-only` passed, `Scripts/check_public_paths.py` 0 files flagged, `scrub_private_paths.py
  --check` clean, `tools/lfs_audit.py` 0 missing, `lfs_private_check.sh` 0 hits.
- `art_coverage.py` on the copy's importer report: final 1652 / placeholder 4927 / cut 28 for master and for this
  branch alike (no binding added or removed: the same class ids and pictures).
- The Unreal tests were NOT re-run after the rebases onto 280f7bd1 and 15c980de (#158, #197, #179, #198, #195, #193,
  #192 merged meanwhile; none of them touches a file of this change except the shared docs and data tables, which
  merged without conflict).
- Measured in Blender for the eyes: head pitch 15 degrees moves the eyeball against the lid opening by 9.27 mm before
  and 0.97 mm after (merchant; girl 1.44, old man 1.01, peasant 0.97, gnome 2.12 after).

## Not done, not checked

- Not seen in the game: the brown maiden, the red knights of 374/402 and the gold knights with the new idle, a walking
  knight (he lets go of the shaft), the old man's staff and the peasant's pole (they still stand beside the hand:
  only the knights have the hold), LODs 1 to 3 of the new meshes, Seth's pose seam when he starts to walk.
- Not done: Seth's red flash while he casts (needs a material hook), a walk of his own, glove cuffs; the plain faces,
  hair and hands of the ported people; the knights' plate surface; a carried-halberd walk and attack clips for the
  knights; the maidens' collar and cuffs and a face of their own; hair motion (the maiden's hair and Seth's crest are
  skinned cards; nothing of the hair-cloth work is bound to them).
- Triangles: Seth LOD0 66,906 (class `character_hero`, as the hero), Maiden LOD0 under the 35,000 cap after two cuts
  of her hair cards.
