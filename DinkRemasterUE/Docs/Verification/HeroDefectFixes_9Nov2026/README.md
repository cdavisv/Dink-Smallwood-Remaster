# Hero defect fixes: in-game after-shots (11 Nov 2026)

The owner reported four defects on Dink on 9 Nov 2026 with three in-game screenshots: head and shoulder through an
interior wall, odd wrists, nipples showing through the shirt, a floating belt buckle. The fixes were merged as PR #51
(`SourceAssets/Art/Characters/README.md`, "Dink defect fixes"; `Dink.Movement.WallClearance`) and until now had only
been checked in Blender renders and a headless test. These are frames from the running game.

**How they were taken.** Master 3f5de35, `Scripts/build.sh` BUILD OK, greybox re-imported, then the real game
(`-game`, 1280x720) on the private display: `Scripts/private_qa_session.py start` (private Xvfb :189 with XTest input,
GPU-rendered: the log names `AMD Radeon RX 6800 (RADV NAVI21)`, not `-nullrhi`). Driven with
`Scripts/playtest_desktop.py --private-display :189`: `dink.Goto 1 x y` places Dink in his house (SCR_001), a short real
`hold w` turns the body, `dink.View yaw pitch` and the engine's `fov` aim the camera, `capture` reads the window back.
The two crops come from one `HighResShot 3840x2160` of the `front_sunlit.png` pose. No image was retouched.

| File | Pose | What it shows |
|---|---|---|
| `wall_side_from_north.png` | map (139.8, 164.7): W held into the west wall until the capsule stops; camera yaw 90, fov 70 | The whole face in profile in front of the plaster, nose at the wall. The head no longer enters the wall. |
| `wall_over_shoulder.png` | map (139.8, 175), camera yaw 235, pitch -20 | The owner's first screenshot again: head and both shoulders in front of the wall. |
| `wall_side_while_pushing.png` | same spot, camera yaw 270, fov 38, captured 1.5 s into a 3 s push (A held: a strafe west) | The same pose as at rest: pushing does not carry the head into the wall. |
| `front_sunlit.png` | map (149, 162) facing east in the sun patch, camera yaw 180, fov 60 | The owner's second screenshot again, lit from the front. |
| `front_upper_body_crop_from_4k.png` | crop of the 4K shot of that pose | Shirt chest, collar, belt. The lit side of the chest is smooth. In the raking light of the shadow side a faint crease remains at his right chest; see below. |
| `belt_buckle_and_cuffs_crop_from_4k.png` | crop of the 4K shot | The buckle sits on the belt with no gap. Both turned cuffs close round the forearm; no slot above the wrist. |
| `window_side.png` | map (152, 237.8) facing south beside the west wall, camera yaw 180, fov 60 | The owner's third screenshot again: side-on by the window wall, head clear of the wall plane. Dark: this stretch of wall is in shadow at the scene's sun angle. |
| `observation_backlit_seam_lines.png` | map (186.8, 160) facing east, backlit, camera yaw 180, fov 36 | Not one of the four defects: thin bright lines on the face and scalp when Dink is backlit. |

## Verdict per defect

1. **Head and shoulder through walls: fixed in play.** At rest and while pushing, the head stays in front of the wall.
   The margin is small: the nose and brow sit at the plaster, so a different wall thickness or a stronger stumble pose
   could still touch. Only this one wall was tried.
2. **Wrists: fixed.** The cuffs hug the forearm on both arms in the 4K crop.
3. **Nipples through the shirt: fixed on the lit side; a faint crease is left on his right chest** in raking light
   (`front_upper_body_crop_from_4k.png`, left of the placket, a third of the way down). It does not read as a nipple
   at game distance (`front_sunlit.png`), but it is there.
4. **Belt buckle: fixed.** No gap between buckle and belt.

## Seen on the way, not part of this fix

- **Bright seam lines on the head when backlit** (`observation_backlit_seam_lines.png`): thin white lines along the
  jaw, the face and the scalp. They look like light showing through seams between the head's parts. Whether the
  9 Nov re-export caused them or they predate it was not checked; no before frame under the same backlight exists.
- **Shadow banding beside the collar placket** and **speckled shadow noise on the sunlit face**
  (`front_upper_body_crop_from_4k.png`): renderer shadow artefacts, not geometry.
- The camera's shoulder offset keeps Dink left of centre, so a narrow `fov` loses him from the frame; use `fov` 36 or
  wider, or crop a `HighResShot`.

Raw frames of the whole session (25 files, including the 4K sources) are in the git-ignored
`Saved/Playtest/evidence/hero-aftershots/` of the checkout that took them.
