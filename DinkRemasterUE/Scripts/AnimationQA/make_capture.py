"""Write dink.CaptureScript files that photograph the hero's animation in the running game at
fixed game-time steps (slow motion), for contact strips of what the engine really shows.

  python3 -I Scripts/AnimationQA/make_capture.py            # writes Saved/AnimationPass/capture/*.txt
  Scripts/PhotorealQA/run_capture.sh <ABS path of one .txt> # offscreen, no display, no input
  python3 -I Scripts/AnimationQA/strip.py <name>            # tiles the frames into Saved/AnimationPass/<name>_engine.png

A `shot` line costs half a second of real time, so with `dink.TimeDilation 0.1` consecutive shots are 0.05 s
of game time apart. Output stays under Saved/ (git-ignored).
"""
from pathlib import Path
project = Path(__file__).resolve().parents[2]
out = project / 'Saved/AnimationPass/capture'
out.mkdir(parents=True, exist_ok=True)
START = ['wait 22', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.ScreenScripts 0',
         'dink.Goto 438 300 200', 'wait 2', 'dink.CameraDistance 420', 'wait 1']


def shots(name, count):
    rows = []
    for i in range(count):
        rows.append('shot %s/Saved/AnimationPass/frames/%s/%02d.png' % (project, name, i))
    return rows


def write(name, body):
    (project / 'Saved/AnimationPass/frames' / name).mkdir(parents=True, exist_ok=True)
    (out / (name + '.txt')).write_text('\n'.join(START + body + ['dink.TimeDilation 1', 'wait 1', 'quit']) + '\n')


# Side-on: the pawn faces east after dink.Goto; the camera looks north across him.
write('attack_combo', ['dink.View -90 -8', 'wait 2', 'dink.TimeDilation 0.1', 'dink.Attack'] + shots('attack_combo', 8) +
      ['dink.Attack'] + shots('attack_combo_b', 8) + ['dink.Attack'] + shots('attack_combo_c', 16))
write('run', ['dink.View -90 -8', 'wait 1', 'dink.WalkTo 590 200 8', 'wait 1.0', 'dink.TimeDilation 0.1'] + shots('run', 14))
write('idle', ['dink.View 160 -6', 'wait 3'] + shots('idle', 6))
print('wrote', sorted(p.name for p in out.glob('*.txt')))
