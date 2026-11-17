# Hero weapon meshes in the hand (art row DS-04, bug A203), 16 November 2026

Captured in the game (offscreen `run_capture.sh`, screen 439, daylight) from a private copy on master `6ef7a590` plus this
branch, with the review command `dink.Hero.Hold <mesh> <bone> <x y z pitch yaw roll>`. The first capture's cameras stand
behind the hero (the calibration frame's +X is behind him and +Y is his left), so most frames show his back.

| sheet | what it shows | what I see |
|---|---|---|
| `icons_1997.png` | the 1997 item pictures 438/6, 7, 8, 12, 13, 20, 21 (6x) | the reference for shape and colour |
| `01_claw_sword_variants_A_to_E.jpg` | the claw sword on `hand_r` in five transforms (rows A to E; columns: from behind, a hand close-up that caught the empty left hand, from his right side) | A, B and C: the blade leaves the thumb side of the fist and points forward at hip height. D and E (pitch -90): the blade points backward out of the little-finger side: wrong |
| `02_claw_sword_A_and_C_close.jpg` | A (left) and C (right) enlarged | the grip lies in the palm under the fingers, guard just ahead of the index finger, pommel behind the little finger. A has the claws on the knuckle side (the leading edge of a cut), C on the wrist side. **A is the transform** |
| `03_longsword_lightsword_axe_in_hand.jpg` | longsword, light sword and axe with transform A; the play camera | all three sit in the palm the same way; the steel reads pale grey in the game's light (the blue of the Blender renders was the review sky); at the play camera the sword in the idle hand points at the camera and is barely visible |
| `04_slash_and_chop_frames.jpg` | `Sword_Slash_1` (ten frames, from behind) and `Sword_Chop` (eight frames, from his left) at a tenth of the speed, longsword, transform A | the fist is closed round the grip and the blade follows the cut; in the chop the blade rises from the thumb side and comes down in front of him |
| `05_bow_variants_idle.jpg` | the wooden bow on `hand_l` in four transforms, the blue bow, two `Bow_Draw` frames | idle: the bow is carried level at his side by the grip (A). The two draw frames are framed too low to show the bow: **the bow at full draw is not verified** |

| `06_all_six_from_the_front.jpg` | second capture, cameras in front of him: longsword, claw sword, light sword, axe on `hand_r`; wooden and blue bow on `hand_l` | each grip is in the hand, blade or haft out of the thumb side, pointing forward and down in the idle pose; the bows are carried level by the grip with the string uppermost. The light sword's blade is a flat white shape: its glow (45 nits) clips in daylight, lowered to 6 in the source afterwards |
| `07_all_six_hand_close.jpg` | the same, close on the hand | guard, studs, grip binding and pommel read as bone, bronze, silver and leather. The blue bow is a smooth blue-grey pipe here: its surface was reworked afterwards (stained wood with grain and sinew bindings; re-import queued, not in these frames) |
| `08_bow_at_full_draw_variants_A_to_D.jpg` | `Bow_Draw` held, wooden bow in four transforms (pairs: three-quarter front, his left side) | A (top left pair): the bow stands upright in the left fist, its back away from him and the string on his side. C (bottom left) has the bow bent towards him. **A is the transform.** The string stays straight and the right hand draws nothing (rigid mesh) |
| `09_slash_and_chop_from_front_and_side.jpg` | `Sword_Slash_1` with the longsword from the front, `Sword_Chop` with the claw sword from his left, a tenth of the speed; the play camera with the claw sword and the light sword | the sword stays in the closed fist through both cuts. In the low frames of the chop the blade is hard to see from the side: the clip turns the thumb side of the fist across the body there (a clip matter, not the attach). At the play camera the idle sword is a thin line |
| `10_all_six_and_the_light_sword_at_0_9_nits.jpg` | third capture (16 Nov evening, master `bd6d227a` plus this branch): each of the six from the front and close on the hand; the light sword at the play camera by day, and in a room | all six sit in the hand as in sheets 06 and 07. The light sword's blade is now a blade: pale polished steel with its fuller and edge, where the first import (45 nits, then 6) was a flat white shape; at 0.9 nits it keeps a faint cool glow in the dim room and none by day. The blue bow shows its reworked surface: blue-grey stained wood, no longer a smooth pipe. The idle hand is still open round every grip |

## Result

- Swords and axe: bone `hand_r`, relative location (-7, 3, -0.5) cm, rotation pitch 90, yaw 0, roll 90. Verified in the idle
  pose and in two attack clips.
- Bows: bone `hand_l`, relative location (7, -3, 0.5) cm, rotation pitch -90, yaw 0, roll 90. Verified carried and at
  full draw (`Bow_Draw` held).
- The capture log confirms the frame the transform was derived from: `thumb_01_r` at (-1.99, 1.36, 2.58) in `hand_r`
  (reference pose), the Blender bone frame with Y negated.

## Not checked, still wrong

- The light sword's glow was judged by day and in one room, not at night or in a cave.
- The idle hand is open, so the grip is held by a loose hand until the fist closes in an attack; a closed-fist pose while
  armed is animation code. The runtime attach by item is code (A203 stays open for it).
- The bows are rigid and strung at rest: nothing bends with `Bow_Draw`. No arrow mesh.
- `Sword_Chop`: in its low frames the blade lies across the body rather than forward (wrist turn of the clip).
