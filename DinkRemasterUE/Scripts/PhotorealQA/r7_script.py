#!/usr/bin/env python3
"""r7_script.py <tag> [name parts...]: capture script of the round-7 review cameras (grass clearings and edges,
interior floor and light, foliage in the game, five frame-rate cameras). Shots go to
<PROJECT>/Saved/PhotorealPass/round7/<tag>/; run the output with run_capture.sh (it replaces <PROJECT>)."""
import sys
tag = sys.argv[1]; only = sys.argv[2:]
# name, screen, map x, map y, boom cm, yaw, pitch, frame-rate camera
CAMS = [
    ('g01_tools_440_game', 440, 440, 345, 400, -90, -12, True),
    ('g02_tools_440_close', 440, 440, 330, 220, -90, -30, False),
    ('g03_tools_440_above', 440, 440, 300, 600, -90, -60, False),
    ('g04_rake_409_close', 409, 190, 325, 240, -90, -30, False),
    ('g05_mushroom_567_close', 567, 399, 362, 200, -90, -30, False),
    ('g06_pebbles_567_close', 567, 110, 140, 220, -90, -30, False),
    ('g07_pitchfork_274_close', 274, 144, 292, 240, -90, -28, False),
    ('g08_path_274_game', 274, 144, 320, 400, -90, -10, False),
    ('g09_path_274_above', 274, 144, 300, 700, -90, -50, False),
    ('g10_path_502_above', 502, 261, 100, 700, -90, -50, False),
    ('g11_path_502_low', 502, 261, 100, 300, 0, -8, False),
    ('g12_shore_604_low', 604, 300, 330, 300, -90, -4, True),
    ('g13_meadow_440_above_far', 440, 300, 200, 900, -90, -70, False),
    ('i01_bar_34_lantern', 34, 300, 260, 400, 180, 12, False),
    ('i02_bar_34_game', 34, 300, 260, 400, -90, -25, True),
    ('i03_bar_34_floor', 34, 300, 260, 300, 0, -50, False),
    ('i04_house_2_game', 2, 300, 250, 400, -90, -25, False),
    ('i05_house_36_game', 36, 300, 250, 400, -90, -20, False),
    ('i06_bookstore_67_game', 67, 300, 250, 400, 180, -15, False),
    ('i07_dungeon_579_torches', 579, 300, 240, 400, 0, 4, True),
    ('i08_castle_70_game', 70, 300, 250, 400, -90, -20, False),
    ('f01_pines_183', 183, 300, 330, 400, -90, -3, False),
    ('f02_oaks_664', 664, 300, 280, 400, -80, -3, False),
    ('f03_town_418_street', 418, 250, 300, 250, -150, 2, True),
]
print('wait 22\ndink.Goto 471 215 125\ndink.View 10 5\nwait 40\ndink.Skip\nwait 1\ndink.Skip\nwait 1\ndink.Skip\nwait 1\nt.MaxFPS 0\nr.VSync 0')
for name, screen, x, y, boom, yaw, pitch, fps in CAMS:
    if only and not any(part in name for part in only):
        continue
    print(f'dink.Goto {screen} {x} {y}\ndink.CameraDistance {boom}\nFOV 0\nwait 1\ndink.View {yaw} {pitch}\nwait 7\ndink.Player\nwait 2')
    if fps:
        print(f'fps {name}')
    print(f'shot <PROJECT>/Saved/PhotorealPass/round7/{tag}/{name}.png\nwait 1')
print('quit')
