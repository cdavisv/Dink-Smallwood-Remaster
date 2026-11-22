"""Write a dink.CaptureScript that films Dink with each weapon armed (bug A203): standing, walking and attacking, close up
and at the play camera, in slow motion, then with the hand emptied (fists) as the before.

  python3 -I Scripts/AnimationQA/weapon_capture.py <tag> [--project <DinkRemasterUE folder>]
  Scripts/PhotorealQA/run_capture.sh <project>/Saved/AnimationPass/capture/weapons_<tag>.txt
"""
import argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('tag')
ap.add_argument('--project', default=str(Path(__file__).resolve().parents[2]))
a = ap.parse_args()
P = Path(a.project)
cap, frm = P / 'Saved/AnimationPass/capture', P / 'Saved/AnimationPass/frames'
cap.mkdir(parents=True, exist_ok=True)
T = a.tag
L = ['wait 22', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.ScreenScripts 0',
     'dink.Fact lifemax 999', 'dink.Fact life 999', 'dink.Goto 438 300 200', 'wait 2']


def shots(name, n):
    d = frm / f'{T}_{name}'
    d.mkdir(parents=True, exist_ok=True)
    return [f'shot {d}/{i:02d}.png' for i in range(n)]


for item in ('item-fst', 'item-sw1', 'item-sw2', 'item-sw3', 'item-axe', 'item-b1', 'item-b2'):
    n = item.replace('item-', '')
    L += [f'dink.Hero.GiveWeapon {item}', 'wait 1', 'dink.CameraDistance 240', 'dink.View -60 -10', 'wait 1'] + shots(f'{n}_idle', 2) + \
         ['dink.CameraDistance 420', 'dink.View -90 -12', 'dink.TimeDilation 0.2', 'dink.WalkTo 420 200 3'] + shots(f'{n}_walk', 6) + \
         ['dink.TimeDilation 1', 'wait 1.5', 'dink.View -90 -8', 'dink.TimeDilation 0.15', 'dink.Attack'] + shots(f'{n}_attack', 10) + \
         ['dink.TimeDilation 1', 'wait 1.5', 'dink.Goto 438 300 200', 'wait 1']
L += ['dink.TimeDilation 1', 'wait 1', 'quit']
out = cap / f'weapons_{T}.txt'
out.write_text('\n'.join(L) + '\n')
print(out, len(L), 'lines', sum(1 for x in L if x.startswith('shot ')), 'shots')
