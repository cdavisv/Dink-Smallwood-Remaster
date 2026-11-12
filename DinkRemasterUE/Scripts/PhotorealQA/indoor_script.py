#!/usr/bin/env python3
"""indoor_script.py <outdir> [--var name=cmd;cmd ...]: indoor screens with the indoor set off (before) and on (after),
or one capture per variant with the set on. Cameras as the in-game review cameras 20-24."""
import sys
out = sys.argv[1]
variants = [(a.split('=', 1)[0], [c.strip() for c in a.split('=', 1)[1].split(';') if c.strip()]) for i, a in enumerate(sys.argv) if i > 0 and sys.argv[i - 1] == '--var']
CAMS = [('interior_2', 2, 300, 220, -90, -8), ('interior_34', 34, 300, 220, 180, -8), ('dungeon_579', 579, 300, 240, -90, -6), ('dungeon_260', 260, 300, 220, -45, -6), ('lava_85', 85, 300, 200, -90, -10),
        ('dungeon_73', 73, 300, 250, -90, -25), ('dungeon_138', 138, 300, 250, -90, -25),
        ('hero_439', 439, 300, 385, 0, -4, 200, 30), ('hero_side_439', 439, 300, 385, -70, -4, 200, 30)]
only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
L = ['wait 22', 'dink.Goto 471 215 125', 'dink.View 10 5', 'wait 40', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 't.MaxFPS 0', 'r.VSync 0']
for name, s, x, y, yaw, pitch, *rest in CAMS:
    boom, fov = rest if rest else (400, 0)
    if only and not any(o in name for o in only): continue
    L += [f'dink.Goto {s} {x} {y}', f'dink.CameraDistance {boom}', f'FOV {fov}', 'wait 1', f'dink.View {yaw} {pitch}']
    if variants:
        for vname, cmds in variants:
            L += cmds + ['wait 6', f'shot {out}/indoor_{name}_{vname}.png', 'wait 1']
    else:
        L += ['dink.IndoorEnv 0', 'wait 7', f'shot {out}/indoor_{name}_before.png', 'wait 1', 'dink.IndoorEnv 1', 'wait 7', f'fps indoor_{name}', f'shot {out}/indoor_{name}_after.png', 'wait 1']
if '--topdown' in sys.argv:
    for s in (73, 138):
        L += [f'dink.Goto {s} 300 200', 'dink.IndoorEnv 0', 'wait 2', 'dink.CalAnchor 0 0', 'dink.CalCam 0 0 3200 1 0 0 85', 'wait 7', f'shot {out}/topdown_{s}.png', 'wait 1', 'dink.CalCam off', 'dink.IndoorEnv 1']
if '--heroclose' in sys.argv:
    hv = variants or [('a', [])]
    L += ['dink.Goto 439 300 385', 'dink.View 0 -4', 'wait 3', 'dink.CalAnchor 0 0']
    for cam, c in (('front', 'dink.CalCam -95 30 168 0 0 160 40 1'), ('gameplay', 'dink.CalCam -200 60 180 0 0 120 60 1')):
        L += [c, 'wait 2']
        for vname, cmds in hv:
            L += cmds + ['wait 5', f'shot {out}/heroclose_{cam}_{vname}.png', 'wait 1']
    L += ['dink.CalCam off']
L += ['quit']
print('\n'.join(L))
