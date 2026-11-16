"""Write one dink.CaptureScript that audits character motion in the running game: a numeric bone trace
(dink.Motion.Trace) of the hero through every locomotion state, turn, attack and reaction at three confidences,
Mother wandering in her house, the pigs in their pen and the pillbugs of screen 30, plus slow-motion picture
strips at the play camera and close up (side, front, three-quarter).

  python3 -I Scripts/AnimationQA/motion_audit.py <tag> [--project <DinkRemasterUE folder>] [--quick]
  Scripts/PhotorealQA/run_capture.sh <project>/Saved/AnimationPass/capture/motion_<tag>.txt
  python3 -I Scripts/AnimationQA/motion_report.py <project>/Saved/AnimationPass/motion/<tag>_*.csv

Traces land in Saved/AnimationPass/motion/<tag>_<part>.csv, frames in Saved/AnimationPass/frames/<tag>_<strip>/NN.png.
Every timing below is game time; a `shot` holds the script for 0.5 s of real time.
"""
import argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('tag')
ap.add_argument('--project', default=str(Path(__file__).resolve().parents[2]))
ap.add_argument('--quick', action='store_true', help='confidence 0 only, fewer strips')
ap.add_argument('--strips-only', action='store_true', help='picture strips only (no traces, no NPC/creature parts)')
ap.add_argument('--legs', type=int, default=None, help='dink.Anim.Legs for the whole run (0 = the clips as they are, the before state)')
a = ap.parse_args()
P = Path(a.project)
cap = P / 'Saved/AnimationPass/capture'
mot = P / 'Saved/AnimationPass/motion'
frm = P / 'Saved/AnimationPass/frames'
for d in (cap, mot, frm):
    d.mkdir(parents=True, exist_ok=True)
T = a.tag
L = ['wait 22', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.ScreenScripts 0']
if a.legs is not None:
    L.append(f'dink.Anim.Legs {a.legs}')


def shots(name, n, view=None):
    (frm / f'{T}_{name}').mkdir(parents=True, exist_ok=True)
    out = [f'dink.View {view}'] if view else []
    return out + [f'shot {frm}/{T}_{name}/{i:02d}.png' for i in range(n)]


def hero_course(c):
    """About 40 s of game time on the flat yard of screen 438: every hero state once."""
    g = 'dink.Goto 438 300 200'
    return [
        f'dink.HeroConfidence {c}', g, 'dink.Hero.Gait 0', 'wait 2.5',            # idle
        'dink.Hero.Gait 1', 'dink.WalkTo 520 200 5', 'wait 4.0', 'wait 1.5',       # start, walk, stop
        'dink.WalkTo 470 200 3', 'wait 2.5',                                       # 180 reversal at a walk
        'dink.WalkTo 471 214 2', 'wait 1.2', 'dink.WalkTo 469 214 2', 'wait 1.2',  # small turns near the spot
        'dink.WalkTo 469 200 2', 'wait 1.2',
        'dink.Hero.Gait 2', 'dink.WalkTo 640 200 4', 'wait 3.0',                   # start into a run
        'dink.WalkTo 420 200 4', 'wait 3.0', 'wait 1.5',                           # reversal at a run, stop
        'dink.Hero.Gait 1', 'dink.WalkTo 520 200 3', 'wait 0.6', 'dink.Hero.Gait 2', 'wait 1.2', 'dink.Hero.Gait 1', 'wait 1.5',  # walk/run/walk
        'wait 1',
        'dink.Hero.Gait 0', 'dink.Attack', 'wait 0.45', 'dink.Attack', 'wait 0.45', 'dink.Attack', 'wait 1.4',  # fist combo
        'dink.Hero.Play Sword_Slash_1', 'wait 1.0', 'dink.Hero.Play Sword_Slash_2', 'wait 1.0', 'dink.Hero.Play Sword_Chop', 'wait 1.2',
        'dink.Hero.Play Bow_Draw hold', 'wait 1.2', 'dink.Hero.Play Bow_Release', 'wait 1.0',
        'dink.Hero.Play Cast', 'wait 1.2', 'dink.Hero.Play Hurt', 'wait 1.2', 'dink.Hero.Play Stumble', 'wait 1.5',
        'dink.Hero.Play jump', 'wait 2.0',
        'dink.Hero.Gait 1', 'dink.WalkTo 560 200 3', 'wait 0.8', 'dink.Attack', 'wait 2.4',   # punch while walking
        'dink.Hero.Gait 2', 'dink.WalkTo 300 200 4', 'wait 1.0', 'dink.Hero.Play jump', 'wait 2.0',  # running jump
        'dink.Hero.Gait 0', 'wait 1']


confs = [] if a.strips_only else (['0'] if a.quick else ['0', '0.5', '1'])
for c in confs:
    L += ['dink.HeroConfidence ' + c, 'dink.Goto 438 300 200', 'dink.CameraDistance 420', 'wait 2',
          f'dink.Motion.Trace 50 {mot}/{T}_hero_c{c.replace(".", "")}.csv 800'] + hero_course(c) + ['wait 2']

# Picture strips: close up (side, front, three-quarter) and at the play camera, in slow motion.
def strip_block(c, name, setup, n, view, dil='0.1', dist='300'):
    # dink.WalkTo times out in REAL seconds and survives a dink.Goto to the same screen: give every walk of a block a
    # timeout that ends with the block, or it keeps walking (or, with dink.Hero.Gait 0, running) into the next one.
    real = sum(float(x.split()[1]) for x in setup if x.startswith('wait ')) + 0.5 * n + 0.3
    setup = [' '.join(x.split()[:3] + [f'{real:.1f}']) if x.startswith('dink.WalkTo') else x for x in setup]
    return ([f'dink.HeroConfidence {c}', 'dink.Goto 438 300 200', 'dink.Hero.Gait 0', f'dink.CameraDistance {dist}', f'dink.View {view}', 'wait 1.5']
            + setup + [f'dink.TimeDilation {dil}'] + shots(f'{name}_c{c.replace(".", "")}', n) + ['dink.TimeDilation 1', 'wait 0.5'])


for c in (['0'] if a.quick else ['0', '1']):
    L += strip_block(c, 'idle_side', ['wait 1'], 4, '-90 -6', dil='1')
    L += strip_block(c, 'idle_front', ['wait 1'], 3, '180 -6', dil='1')
    L += strip_block(c, 'walk_side', ['dink.Hero.Gait 1', 'dink.WalkTo 560 200 20', 'wait 2.0'], 16, '-90 -8')
    L += strip_block(c, 'walk_front', ['dink.Hero.Gait 1', 'dink.WalkTo 560 200 20', 'wait 2.0'], 12, '90 -8')
    L += strip_block(c, 'walk_34', ['dink.Hero.Gait 1', 'dink.WalkTo 560 200 20', 'wait 2.0'], 12, '-135 -10')
    L += strip_block(c, 'run_side', ['dink.Hero.Gait 2', 'dink.WalkTo 640 200 20', 'wait 1.2'], 12, '-90 -8')
    L += strip_block(c, 'start_side', ['dink.Hero.Gait 1', 'dink.WalkTo 420 200 20'], 14, '-90 -8', dil='0.15')
    L += strip_block(c, 'reverse_side', ['dink.Hero.Gait 1', 'dink.WalkTo 360 200 3', 'wait 1.5', 'dink.WalkTo 420 200 6'], 16, '-90 -8', dil='0.12')
    L += strip_block(c, 'turn_34', ['dink.WalkTo 299 212 2'], 12, '-135 -14', dil='0.1')
    L += strip_block(c, 'combo_side', ['dink.Attack'], 8, '-90 -8') + ['dink.TimeDilation 0.1', 'dink.Attack'] + shots(f'combo_b_c{c.replace(".", "")}', 8) + ['dink.TimeDilation 1', 'wait 1']
    L += strip_block(c, 'jump_side', ['dink.Hero.Play jump'], 16, '-90 -8', dil='0.15')
    L += strip_block(c, 'hurt_34', ['dink.Hero.Play Hurt'], 10, '-135 -8')
    L += strip_block(c, 'stumble_side', ['dink.Hero.Gait 2', 'dink.WalkTo 640 200 20', 'wait 1.0', 'dink.Hero.Play Stumble'], 12, '-90 -8')
    L += strip_block(c, 'bow_34', ['dink.Hero.Play Bow_Draw hold'], 6, '-135 -8') + ['dink.TimeDilation 0.1', 'dink.Hero.Play Bow_Release'] + shots(f'bowrel_c{c.replace(".", "")}', 6) + ['dink.TimeDilation 1']
    L += strip_block(c, 'cast_34', ['dink.Hero.Play Cast'], 10, '-135 -8')
    L += strip_block(c, 'play_walk', ['dink.Hero.Gait 1', 'dink.WalkTo 560 200 20', 'wait 1.5'], 4, '-90 -35', dil='1', dist='900')

# Mother: wandering in Dink's house (screen 1), traced and photographed.
if not a.strips_only:
  L += ['dink.HeroConfidence -1', 'dink.Hero.Gait 0', 'dink.Goto 1 330 250', 'dink.CameraDistance 420', 'wait 2', 'dink.View 180 -4',
      f'dink.Motion.Trace 48 {mot}/{T}_mother.csv 1500', 'wait 2'] + shots('mother_play', 24) + \
     ['dink.Hero.Gait 1', 'dink.WalkTo 330 20 3', 'wait 3', 'dink.WalkTo 600 250 4', 'wait 4', 'dink.WalkTo 330 250 4', 'wait 1'] + shots('hero_wall', 4) + ['dink.CameraDistance 260', 'wait 1'] + shots('mother_close', 20) + ['wait 14']
# Pigs in their pen (screen 407).
if not a.strips_only:
  L += ['dink.Goto 407 300 300', 'dink.CameraDistance 600', 'wait 3', 'dink.View -90 -20', f'dink.Motion.Trace 20 {mot}/{T}_pigs.csv 2500', 'wait 1'] + shots('pigs', 16) + ['wait 10']
# Pillbugs (screen 30): they walk up and bite; Dink punches.
if not a.strips_only:
  L += ['dink.Goto 30 100 300', 'dink.CameraDistance 700', 'wait 2', 'dink.View -90 -25', f'dink.Motion.Trace 20 {mot}/{T}_pillbugs.csv 3000', 'wait 1'] + shots('pillbugs', 12) + \
     ['dink.WalkTo 216 191 5', 'wait 3', 'dink.Attack', 'wait 0.6', 'dink.Attack', 'wait 0.6', 'dink.Attack', 'wait 0.6'] + shots('pillbug_fight', 8) + ['wait 6']
L += ['dink.TimeDilation 1', 'wait 1', 'quit']
out = cap / f'motion_{T}.txt'
out.write_text('\n'.join(L) + '\n')
n = sum(1 for x in L if x.startswith('shot '))
print(out, len(L), 'lines', n, 'shots')
