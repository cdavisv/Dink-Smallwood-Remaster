# Dink's death clip `Death_436` in the game (art row GP-Q8), 16 November 2026

The clip was re-keyed on 16 November: the sixteen 1997 pictures of sequence 436 show a forward collapse (doubled over,
onto his knees, face down with his back and pack uppermost and his feet in the air behind him), not a fall onto his
back. Captured offscreen on screen 439 from a private copy (master plus this branch and the stream's other art
branches) with `dink.Hero.Play Death_436 hold`; nothing triggers the clip on a real death yet.

| sheet | what it shows | what I see |
|---|---|---|
| `1997_436_strip.png` | six of the sixteen 1997 frames of sequence 436 (2x): 1, 4, 8, 12, 14, 16 | hit, doubled over, on his knees, pitching forward, face down with the feet up, the red pool under chest and head |
| `01_death_436_play_camera.jpg` | the play camera, nine frames 0.37 s apart: the clip from its start, then the held end | 00 doubled over, hands at his belly; 01 on his knees and pitching forward, right arm thrown ahead; 02 chest and face down, heels kicked up; 03 to held: he does not move again: face down, back and pack uppermost, shins half raised, right arm stretched past his head. This is 436/12 to 436/16 without the pool. He reads at once at the play camera |
| `02_death_436_side_and_above.jpg` | from his side (three frames of the fall), from behind and above, straight down (grass and a plank floor) | the knees take the ground under where he stood and the body goes down ahead of them; from above he lies straight, one arm out, about 1.3 m in front of the spot he stood on (the cameras were aimed at that spot, so he lies at the frame's edge) |

The Blender strip `SourceAssets/Art/Characters/Animations/AnimationPassV1/Strips/hero_death/Death_436.png` shows the
clip every 0.1 s from the side and from above.

## How it was checked

- `Dink.Art`, `Dink.Animation` and the probe: the lines are in the pull request.
- `animation_pass.json` entry and the imported `AN_Death_436` come from `Scripts/import_animation_pass.sh` with
  `DINK_ANIM_ONLY=Death_436`; no other clip's file changed.

## Not checked, still wrong

- No blood: the pool of 436/16 belongs to the death presentation (PR #140), which this clip is not wired to. No real
  death was played, so the hand-over to the limp body, the 3 s wait and the menu were not seen.
- Only three frames of the fall itself were caught in the game (a clip does not follow the capture's time dilation);
  the Blender strip shows the rest.
- He ends in front of the capsule: the pool belongs about 1.3 m ahead of the capsule's feet, and a wall close in front
  of him would cut the body (no collision for the lying body; that is the death presentation's).
- Long grass hides his hands and face. The raised shins are stiff: they do not sag after the fall.
