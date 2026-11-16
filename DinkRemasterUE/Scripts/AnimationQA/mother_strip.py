"""Write a dink.CaptureScript that films Mother (S001_P26, the only placed humanoid NPC body) walking in her house with a
camera that follows her from her side and from the front (dink.CalAnchorNpc + dink.CalCam before every shot, the player
hidden), in slow motion: the strips the motion audit's over-the-shoulder views could not give (Dink stood in front of her).

  python3 -I Scripts/AnimationQA/mother_strip.py <tag> [--legs 0|1] [--project <DinkRemasterUE folder>]
  Scripts/PhotorealQA/run_capture.sh <project>/Saved/AnimationPass/capture/mother_<tag>.txt
"""
import argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('tag')
ap.add_argument('--project', default=str(Path(__file__).resolve().parents[2]))
ap.add_argument('--legs', type=int, default=None)
a = ap.parse_args()
P = Path(a.project)
cap, frm = P / 'Saved/AnimationPass/capture', P / 'Saved/AnimationPass/frames'
cap.mkdir(parents=True, exist_ok=True)
T = a.tag
L = ['wait 22', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.ScreenScripts 0']
if a.legs is not None:
    L.append(f'dink.Anim.Legs {a.legs}')
L += ['dink.Goto 1 330 250', 'wait 4', 'dink.TimeDilation 0.25']
# (name, camera offset in her frame: x forward, y to her right, z up; target; fov)
for name, cam in (('side', '0 -320 95 0 0 85 45'), ('front', '300 40 200 0 0 80 50'), ('feet', '20 -200 30 0 0 15 40')):
    d = frm / f'{T}_mother_{name}'
    d.mkdir(parents=True, exist_ok=True)
    for i in range(32):
        L += ['dink.CalAnchorNpc 0', f'dink.CalCam {cam}', f'shot {d}/{i:02d}.png']
    L += ['dink.CalCam off', 'dink.TimeDilation 1', 'wait 3', 'dink.TimeDilation 0.25']
L += ['dink.CalCam off', 'dink.TimeDilation 1', 'wait 1', 'quit']
out = cap / f'mother_{T}.txt'
out.write_text('\n'.join(L) + '\n')
print(out, len(L), 'lines')
