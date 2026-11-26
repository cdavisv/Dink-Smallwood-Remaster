# Explosion cards without the pale outline (161, 167, 70), 23 November 2026

In the game (sheet `01_fire_burst_161.jpg` of `EffectCards_16Nov2026`, frames 19, 22, 23) a thin pale line ran round the
red-brown and grey phases of the bomb's burst. Cause, found in the atlas: the outermost texels of the rendered smoke are
a veil lit nearly white, at full opacity after the earlier grade.

`Unclaimed/tools/fx_grade.py` `defringe()`: per frame, a pale colourless texel near the shape's edge takes the colour of
the shape's inside; a pale wisp with no body behind it fades out; fire's own orange edge and its white-hot heart are
left alone. Applied to the three atlases; `build_fx_vol.py` applies it to new renders.

| sheet | what it shows | what I see |
|---|---|---|
| `01_before_161_dark_phases_as_the_material_shows_them.png` | six frames of 161 before, composited as the flipbook material shades them over grass | a white fringe round the red-brown and the grey frames, white specks above the second frame |
| `02_after_161_167_70.png` | after: 161, 167 and 70, six frames each, same shading | the dark phases end in smoke grey; the fire frames are unchanged. A first version also repainted the white-hot heart (rings inside the fire): rejected, the pass now touches the skin only |

## Not checked

- Sheets 01 and 02 are composites of the atlas; the game frames of 23 Nov are sheets 03 and 04 at the end (161 seen, 167 and 70 not caught).
- The smoke phase is unlit: in the dark of the Darklands it reads as a black shape (Seth's explosion on SCR_086).

## In-game look, 23 November 2026 (rendered work allowed again)

Captured offscreen in the running game on master `430fd81d2` + this change (copy `Saved/FableD`, the integration tree of the
effect drafts): `dam-bom main` (161) and the two spells cast north on screen 439, slowed (frames `Saved/PhotorealPass/fx2/C_fx_*.png`).

| sheet | what it shows | what I see |
|---|---|---|
| `03_game_23nov_161_bomb_burst.jpg` | 161, the bomb, frames 16 to 27 at full size | white-yellow flash, orange fireball, then the dark red phase and thin grey smoke, gone four frames later. No bright cream skin round the dark red phase (the fault this draft is about); what rings the ball in frames 19 and 22 is thin grey smoke |
| `04_game_23nov_161_167_70_play_camera.jpg` | every third frame at the play camera: 161 (row 1), the hellfire cast (row 2), the fireball cast (row 3) | 161 as above. **167 and 70 were NOT caught**: both spells flew north out of the picture without striking anything, so their explosions never played in these frames. Their atlases went through the same defringe (sheet 02), but in the game only 161 has been seen |

## Second in-game look, 23 November 2026 evening (art-fx-5): 167 and 70 with something to hit

The first look cast both spells from a spot where the game had not let go of Dink yet, so nothing flew. This time: `get-sfb` /
`get-fb`, two `dink.Skip`, the spell armed, Dink at (300, 385) on screen 439 facing north, `dink.Magic`: the missile crosses the
fence (low hardness) and strikes the cottage wall 2.5 to 3.5 m north of him. Captured on master `fd676f34d` + this change (copy
`Saved/FableD`, integration tree), twice: at 0.4 of the speed with the play camera (`Saved/PhotorealPass/fx5/X_*.png`, 216 frames)
and at a tenth of the speed from the east and the south-east (`fx5/Y_*.png`, 104 frames; one frame is 0.06 s of game time).

| sheet | what it shows | what I see |
|---|---|---|
| `05_game_23nov_167_and_70_slowed.jpg` | the 1997 pictures 167 and 70 above the game's frames at a tenth of the speed | **167 (hellfire)**: a white-yellow burst about 2 m across, then yellow, orange with darker clefts, a dark orange-red cloud, gone after 0.35 s. The bright frames have no outline. **In the last two frames a thin pale grey line still runs round the dark orange lobes**, and a small pale puff stands off the top: no longer the cream skin of master, but still a light rim against grass. It also is a lumpy cloud, where 1997's 167 opens into a RING of fire (not this draft's subject: the atlas was like that before). **70 (fireball)**: the ball flies in, a yellow-white burst, an orange-red ball with veins, a dark red crackle **with a pale grey haze round it**, then a blue-grey smoke puff for two frames. It follows the 1997 picture (burst, pale ball, dark red ragged rim) and adds the smoke; the smoke is unlit (the same grey in any light) |
| `06_game_23nov_167_and_70_play_camera.jpg` | the play camera at 0.4 of the speed: 167 (top) and 70 (bottom), four frames each | at the game's distance and speed each explosion is one or two frames: a fire cloud beyond Dink, for 70 then a grey puff. The rim cannot be made out here |

**Judgement of the three.** 161: at the bar (first look). 167 and 70: the bright phases are at the bar; the dark last frames
keep a thin pale grey rim that shows only slowed down and close up. Better than master in every frame, not yet clean.

Still open: the thin grey rim of the last dark frames of 167 and 70 (the defringe ends in smoke grey; it should end in the
lobe's own dark red, or the rim's alpha should fall faster); 167 as a ring; the smoke phase takes no light from the scene.

## 26 November 2026: rebased onto master 6dd60a8c8, headless proof, frames for Fable (art-finish-1, Opus)

Mechanical only: the branch was replayed as one commit onto master `6dd60a8c8` (world scale on); no texture, material or look
was changed and no look was judged here. **Frames for Fable.**

Proof in copy `Saved/ArtFinish26Nov` (master `6dd60a8c8` + this change): clean editor build 0 warnings, game target 0 warnings
(no C++ in this change), `Dink.Art+Dink.Animation` 105/105, `Dink.Gameplay.Probe` 29/29 with the twenty md5s equal to the
world-scale table of `packaged_probe.md` (Ch1 `ca319f4754` ... Ch20 `be78df8ac3`). Kernel: no Oops.

| sheet | what it shows |
|---|---|
| `07_frames_for_fable_26nov_161.jpg` | the 1997 pictures of 161 beside the bomb's burst on SCR_439: the play camera at 0.2 of the speed (art-fx-2's script), and close from the east and the south-east at 0.1 of the speed (the whole burst) |
| `08_frames_for_fable_26nov_167_70_close.jpg` | the 1997 pictures of 167 and 70 beside the spells cast north on SCR_439, close from the south-east and the east at 0.1 of the speed (art-fx-5's script) |

Captured with `dink.TimeDilation`; frames picked by a colour count (the burst's frames), not by eye. At the play camera, art-fx-2's first
script again sent 167 and 70 out of the picture without a strike (as on 23 Nov); art-fx-5's play/side/close script of 23 Nov
shows no strike either on the enlarged world (the missile flies past the frame): only the south-east and east close-ups of
sheet 08 hold parts of the two bursts. A capture of 167 and 70 at the play camera still has to be framed for the new scale.
