"""Writes the A208 capture script for one run (before = -DPCVars=dink.FamilyDuplicates=0 at launch, after = default).
Usage: make_capture_script.py <run name> <absolute shot dir> <script file>"""
import sys
run, OUT, DEST = sys.argv[1], sys.argv[2], sys.argv[3]
L = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 30', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
     't.MaxFPS 0', 'r.VSync 0', 'dink.Fact lifemax 999', 'dink.Fact life 999']
# (name, screen, stand points (the last that works wins), anchor origin (the kept copy), play camera, wide camera, note)
PLAY, WIDE = '0 1500 700 0 0 450 70 1', '0 3600 2600 0 0 0 60 1'
SPOTS = [
    ('pine_209', 209, [(150, 300), (300, 230)], 'S209_P08', PLAY, WIDE, 'tree_pine_large S209_P08 (262,124) kept; S177_P04 (262,524 on 177) dropped'),
    ('strip_218', 218, [(300, 300), (470, 360), (470, 300)], 'S218_P08', PLAY, WIDE, 'pine_forest_edge_strip_vert S218_P08 (434,189) kept; S186_P02 dropped'),
    ('dead_223', 223, [(300, 200), (330, 395)], 'S223_P01', PLAY, WIDE, 'tree_dead_dark S223_P01 (395,362) kept; S191_P12 and S255_P02 dropped'),
    ('dungeon_073', 73, [(500, 320)], 'S073_P01', '0 700 900 0 0 150 75 1', '0 1200 1800 0 0 0 70 1', 'dungeon_wall_stone S073_P01 (578,229) kept; S074_P08 dropped'),
    ('willow_451', 451, [(300, 300), (181, 260)], 'S451_P07', PLAY, WIDE, 'tree_willow_large four copies: S451_P07 (181,110) kept; S419_P12, S418_P01, S450_P07 dropped'),
    ('oak_440', 440, [(300, 200), (560, 140)], 'S408_P08', PLAY, WIDE, 'tree_oak_large S408_P08 (572,436 on 408) kept (36 px out); S409_P51, S376_P09 dropped'),
    ('twopines_217', 217, [(300, 300), (95, 220)], 'S217_P02', PLAY, WIDE, 'S217_P02 = S185_P02 (one object, exact pixel); S216_P02 is 15 px away in 1997: kept as a second pine'),
    ('willow_446', 446, [(160, 230)], 'S446_P02', PLAY, WIDE, 'tree_willow S446_P02/S414_P02 (scripted s1-h1-4: master leaves both as cards)'),
]
for name, scr, stands, anchor, play, wide, note in SPOTS:
    L += [f'# {note}']
    L += [f'dink.Goto {scr} {x} {y}' for x, y in stands]
    L += ['wait 4', 'dink.Player', f'dink.CalAnchorOrigin {anchor}', f'dink.CalCam {play}', 'wait 2', f'fps {name}', f'shot {OUT}/{name}_play.png',
          f'dink.CalCam {wide}', 'wait 2', f'shot {OUT}/{name}_wide.png', 'dink.CalCam off', f'dink.SceneAudit {OUT}/audit.jsonl']
# Edge walk 209 -> 177 -> 209 beside the pine (S209_P08 at 209 (262,124) = 177 (262,524)), seen from a fixed camera east of it.
L += ['# edge walk', 'dink.Goto 209 150 300', 'dink.Goto 209 300 230', 'wait 4', 'dink.CalAnchorOrigin S209_P08', 'dink.CalCam 1800 900 1100 0 0 200 70 1',
      'wait 2', f'shot {OUT}/walk_n00.png', 'dink.WalkTo 340 -150 8']
for i in range(1, 10):
    L += ['wait 0.4', f'shot {OUT}/walk_n{i:02d}.png']
L += ['dink.WalkTo 340 300 3']
for i in range(10, 14):
    L += ['wait 0.4', f'shot {OUT}/walk_n{i:02d}.png']
L += ['wait 1', 'dink.Player', f'dink.SceneAudit {OUT}/audit_walk.jsonl', 'dink.WalkTo 340 560 8']
for i in range(1, 12):
    L += ['wait 0.4', f'shot {OUT}/walk_s{i:02d}.png']
L += ['wait 1', 'dink.Player', f'dink.SceneAudit {OUT}/audit_walk.jsonl', 'dink.CalCam off', 'wait 1', 'quit']
open(DEST, 'w').write('\n'.join(L) + '\n')
print(len(L))
