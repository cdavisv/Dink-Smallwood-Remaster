# Hero mannerism clips: fifteen clips, seen playing in the game through the runtime (23 Nov 2026)

The local branch `anim/hero-mannerisms` (13-14 Nov 2026) held two halves: fifteen clips made by code in Blender (art)
and a C++ layer that plays them. The C++ half is on master since PR #230 ("Hero mannerism runtime"); this change is the
art half. **The runtime is gated on these clips** (`Posture_Timid` and `Posture_Confident` in the library): merging this
change switches the mannerism layer ON in the game.

## What is in it

- `SourceAssets/Art/Characters/Animations/AnimationPassV1/Tools/clips_mannerisms.py` (the source of the clips), two
  small edits in `build.py` and `clips.py`, the README section, strips in `Strips/hero_manner/`, fifteen
  `Export/A_*.fbx`, their manifest and ledger rows.
- Imported headless: fifteen `Content/Dink/Hero/Animations/Pass1/AN_*.uasset`, their rows in
  `Content/Dink/Data/Art/animation_pass.json`.
- Clips: `Posture_Timid`, `Posture_Confident`, `RunArms_Timid` (additive poses), `Trip_Walk`, `Trip_Run`, `Jump_Timid`,
  `Botch_Stagger`, `Botch_Faceplant`, `Fidget_Scratch`, `Fidget_Scuff`, `Fidget_Nose`, `Fidget_Proud`,
  `Sword_Slash_1_Timid`, `Sword_Slash_2_Timid`, `Sword_Chop_Timid`.
- **Changed after the first look in the game:** `Fidget_Scuff`. The fidgets, botches and trips play under the FULL
  timid stoop (19 degrees of spine, 25 of neck and head at confidence 0); the scuff had a nod of 30 degrees of its own
  and the game showed the head hanging at about 80 degrees, bent double. Its own nod is 9 degrees now (and 6 at the
  end, 2 more of spine instead of 7); re-exported, re-imported, seen again (sheet 03, second row). New review makers
  `Preview_<clip>_C0`: a clip with the stoop mixed in as the game does it, as a Blender strip in 15 s.

## In the running game

Copy `Saved/FableC` = master c0e29cac5 + this change + PR #223 (townsfolk), clean build. Console: `dink.HeroConfidence
<0..1>`, `dink.Hero.Mannerism <kind>`, `dink.Hero.Play <clip>` (the timid cuts, played without a sword in his hand).
Two captures: `mn1` (313 frames, the field of screen 438: every command logged "played"; **my close cameras showed him
from chest to knee only and the grass hides the feet**) and `mn2` (279 frames, the whole figure on the plank floor of
Libby's house, screen 4; `Fidget_Scuff` as re-authored). Frames: the copy's `Saved/CharQA/mn1`, `mn2`.

| Clip | Reads as meant | A limb through the body | Feet | Verdict |
|---|---|---|---|---|
| `Posture_Timid` / `Posture_Confident` | yes: at 0 a stooped boy with his head down, at 1 upright; also while walking (02, 06b) | none seen | n/a | at the bar |
| `RunArms_Timid` | a gawky lope with long hanging arms (06, one side view at confidence 0) | none seen | n/a | reads; NOT compared with the run at confidence 1 from the same camera (those frames show him standing: a fault of my script) |
| `Trip_Walk` | yes: a lurch with both arms thrown out, then he stops (06b) | none seen | legs are the walking legs | at the bar |
| `Trip_Run` | yes: a deeper lurch, arms out, caught in three steps (06) | none seen | as above | at the bar |
| `Jump_Timid` | yes: a small hop with knees up and arms clutched in (04b) | none seen | n/a (in the air) | at the bar |
| `Botch_Stagger` | yes: two lunging catch steps and back (04, 04b) | none seen | end where they began | at the bar |
| `Botch_Faceplant` | at the game's distance yes: down flat, a beat, up, back on his spot (04, 04b). **Close up no** (07): while he lies his chest is propped a hand off the floor on his fists and his shins point up, like a push-up; the clip itself lies flat with boots down (strip below the frames) | none seen | end where they began | below the bar close up; see "For the code side" |
| `Fidget_Scratch` | yes: weight on one leg, a long scratch of the backside (03, 03b) | none seen (the hand goes behind the hip under the pack) | planted | at the bar |
| `Fidget_Scuff` | yes after the change: head bowed, a hand at the back of the neck, a toe ground into the floor (03) | none seen | the left stays, the right steps out and back | at the bar |
| `Fidget_Nose` | yes: the nose wiped along the forearm, a look to see who saw, hand on hip (03, 03b) | none seen | planted | at the bar from chest to knee; the whole figure from the front was hidden by a cabinet in front of my east camera |
| `Fidget_Proud` | weakly: fists close and open, shoulders roll; it is a small movement (03b) | none seen | not seen (chest to knee only) | reads only if one knows what to look for |
| `Sword_Slash_1_Timid`, `Sword_Slash_2_Timid` | yes: the cut carries him round and he catches himself (05) | none seen from the side at 4 m; in the first capture's close frame of slash 1 the left upper arm lies hard against the chest during the turn | step during the cut, end where they began | at the bar without a sword in the hand; not seen armed |
| `Sword_Chop_Timid` | yes: he folds over the cut to the knees and comes up (05) | none seen | as above | at the bar; not seen armed |

**Feet at a walk** (06b, 06c: a fixed camera, frames 0.1 s apart): the planted foot stays on its plank within the
frame's resolution (about 3 cm) at confidence 0 and 1. The exact measure is the engine test
`Dink.Animation.Legs.InEngine` (in the test run below).

## For the code side (not changed here)

- `Botch_Faceplant`: between `posture_off_s` and `posture_on_s` the game does not show the clip's pose: trunk raised
  about 12 degrees about the knees and shins lifted (sheet 07, game frames above the clip's own strip). Something
  procedural still acts on a full-body action while he lies (leg layer, lean or the posture row's W: I did not find
  out which).
- How often the moments come up in real play was not judged; every moment here was forced by console.

## Headless proof

Copy `Saved/FableC` = master c0e29cac5 + this change (all fifteen clips imported, `Fidget_Scuff` as re-authored) + PR #223
(townsfolk; tested together because the copy held both), 23 Nov 2026, 17:27-18:43:
- Clean build (`Intermediate/Build` and `Plugins/*/Intermediate` deleted first): `BUILD OK: DinkRemasterEditor Linux Development in 148s (Result: Succeeded; 0 warnings)`.
- `DINK_ANIM_ONLY=Fidget_Scuff Scripts/import_animation_pass.sh` (`-nullrhi`): `DINK ANIMATION PASS IMPORT OK: 1 clips imported, 51 listed, shared skeleton unchanged` (51 = master's 35 + these 15 + #223's one).
- World regenerated (`import_greybox.sh --region all --export --no-test`, then `--region stonebrook`): IMPORT OK.
- `Dink.Animation+Dink.Art+Dink.Movement` WITH THE MANNERISM LAYER ON (the clips are in the library): TESTS PASSED 108/108 (5 with warnings) in 128 s; this set holds `Dink.Animation.HeroMannerisms`, `HeroMannerismLayerGatedOnClips` and `Legs.InEngine`.
- `Dink.Gameplay.Probe` with the layer on: TESTS PASSED 29/29 (1 with warnings) in 556 s; all twenty chapter md5s equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master (Ch1 cff64df9d1 ... Ch20 b27010b31e): the mannerisms change no gameplay value.
- Source audit as CI runs it: `scrub_private_paths.py --fix` on the real LFS files (`git lfs checkout` of the 66 changed paths first, 0 pointers left) then `--check` clean over the whole tree, `check_public_paths.py` 0 flagged, `verify_sources.py --metadata-only` passed (the scrub rewrites `A_Fidget_Scuff.fbx`: manifest and ledger carry the scrubbed file's sha256).
- Kernel log: 0 Oops.

**Not proven:** this change alone on a master without #223, and anything on fd676f34d: master moved to fd676f34d (#234)
while the tests ran; the commit is rebased onto it (one conflict, in `AGENTS.md`: both sections kept) and was not built
or tested there.

## Not done, not checked

- The cuts with a sword in the hand (with #222's grip layer); `Fidget_Proud` and `Fidget_Nose` as whole figures from
  the front; the run at confidence 1 beside the run at 0; anything at the play camera's own distance in the field
  beyond the first capture's small figures.
- The strips in `Strips/hero_manner/` show the old first hero model (13 Nov); only `Fidget_Scuff.png` is new.
