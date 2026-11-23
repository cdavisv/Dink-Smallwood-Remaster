# Chest lid states (175, 176, 177), 23 November 2026

What an opened chest and its next visit show in the game, and the six states that replace the single open mesh.

**Where the frames come from.** Sheets 01 to 04 are frames of the RUNNING game, captured offscreen on 16 Nov 23:33
(master `6bcfdf60`: BEFORE) and 17 Nov 00:31 (the same master plus this change as it stood then: AFTER), before
rendered work was stopped on the machine. Each chest: play camera, a fixed close camera anchored on the placement,
`dink.Run <script> hit <origin>` (the script's own `hit`), frames during the opening, then a visit to the neighbour
screen and back. Sheet 05 is a Blender render (Cycles, CPU) of the final meshes. Two changes are later than the last
game frame of 17 Nov (the darkened inside, the frame-1 fix described under sheet 04): both were SEEN in the game on 23 Nov, sheets 06 and 07 below.

| sheet | what it shows | what I see |
|---|---|---|
| `1997_175_176_177.png` | the 1997 frames (5x): 175, 176, 177, six frames each | shut, ajar, a third open, two thirds, up, leaning back; 175 seen from the front right, 176 from the front, 177 from the front left; dark inside, the bands show in the lid |
| `01_before_master_hit_and_revisit.jpg` | master: three chests shut, hit, open, next visit, one camera per chest | the hit DOES bring the open mesh and the next visit DOES show it (never the 1997 card). Wrong: the lid pops from shut to fully open in one step; on the next visit the chest stands beside where it stood (536 P31: about 0.9 m; 26 P06 and 98 P07: 0.2 to 0.4 m): the mesh stood on the middle of the picture of the moment, and the scripts open a 177 chest with the pictures of 175 |
| `02_after_17nov_opening_and_revisit.jpg` | this change: a 175, a 176 and a 177 chest | shut chests turned as their 1997 picture; the lid ajar in the first frame of the 175 chest, then up; the next visit stands on the same spot, turned the same way, lid up |
| `03_after_17nov_play_camera_and_side.jpg` | play camera shut and on the next visit; open chests from the side | at the play camera the chest is a small banded box beside Dink, open on the return; from the side the lid leans back past upright |
| `04_after_17nov_the_one_frame_turn.jpg` | the defect that capture found | `ch2-500` plays the pictures of 177 on its 176 chest: for the first frame of the hit (177 frame 1, still shut) the chest turned to 177's angle, then turned back. Fixed after this capture (frame 1 rows carry `stands_as` too); pinned by `test_chest_family_rows.py`, not seen in the game |
| `05_blender_six_states_dark_inside.png` | Blender: the shut Props chest and the five new states, sun and sky | lid at 13, 44, 74, 96 and 110 degrees as the six 1997 frames; the inside of body and lid dark, the rim boards light |

## Still below the bar, not checked

- The opening itself lasts about a third of a second; the capture caught two of its states per chest (the game runs
  the sprite in real time). All six are in the Blender sheet and in the rows.
- The darkened inside and the frame-1 fix were seen in the game on 23 Nov (sheets 06 and 07).
- Nothing lies in an open chest; the loot appears at its foot as in 1997.
- The hasp hangs with the lid; there is no key, lock click or hinge creak (sound is the script's).
- On landforms (#153) the chest's height comes from the screen decor snap; not looked at.

## In-game look, 23 November 2026 (rendered work allowed again)

Captured offscreen in the running game on master `430fd81d2` + this change (copy `Saved/FableD`, the integration tree of the
effect drafts), capture section `chest` (98 frames, `Saved/PhotorealPass/fx2/D_chest*.png`): seven chests, each shut, hit by its
own script (`dink.Run <script> hit <origin>`), four frames of the opening, open, then a visit to the neighbour screen and back.

| sheet | what it shows | what I see |
|---|---|---|
| `06_game_23nov_seven_chests_hit_and_revisit.jpg` | the close camera on all seven chests (rows): shut, four frames from the hit, open, next visit | every chest opens where it stands and stays turned as it was shut, the 176 chests (26 P06, 284 P04) and the 177 chests (536 P31, 98 P07) included: the one-frame turn of 17 Nov is gone. Lid states caught: shut, ajar (536 P31, 282 P06), three quarters (5 P28), up and leaning back; the next visit shows the open chest on the same spot. The inside is dark brown, darker than the outside boards, in sun and indoors |
| `07_game_23nov_play_camera_side_front.jpg` | three chests at the play camera (shut, open, next visit), from the side and from the front | at the play camera the chest is a small banded box that is open after the hit and on the return; from the side the lid leans back past upright, the inside reads dark |

Seen and NOT of this change: the chests of screens 282 and 284 look bleached pink in full sun, shut as well as open (the Props chest's
material under that light); the 44 degree state was not caught by any of the seven bursts (it is one 1997 frame, about 75 ms).
