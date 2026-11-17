"""Write one dink.CaptureScript that photographs the creature one-shots (DinkCreatureOneShots.h) in the running game:
for each class a screen where it is placed, Dink walks up and hits it (the flinch), then kills it (the death clip and the
hand-over to the corpse), in slow motion, close up and at the play camera; the duck stands (its fidgets); a dragon is
watched while it spits fire, then hit and killed; the duck's head-pop and its headless fall into the burst. Dink is made strong and hard to kill for the run (dink.Fact), nothing else changes.

  python3 -I Scripts/AnimationQA/creature_audit.py <tag> [--project <DinkRemasterUE folder>] [--oneshots 0|1]
  Scripts/PhotorealQA/run_capture.sh <project>/Saved/AnimationPass/capture/creatures_<tag>.txt
"""
import argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('tag')
ap.add_argument('--project', default=str(Path(__file__).resolve().parents[2]))
ap.add_argument('--oneshots', type=int, default=None)
a = ap.parse_args()
P = Path(a.project)
cap, mot, frm = P / 'Saved/AnimationPass/capture', P / 'Saved/AnimationPass/motion', P / 'Saved/AnimationPass/frames'
for d in (cap, mot, frm):
    d.mkdir(parents=True, exist_ok=True)
T = a.tag
# Screen scripts stay on: a monster's main gives it its brain and hit points (en-bong: brain 9, 40 hp); without it a hurt
# never kills.
L = ['wait 22', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
     'dink.Fact lifemax 999', 'dink.Fact life 999']
if a.oneshots is not None:
    L.append(f'dink.Creature.OneShots {a.oneshots}')


def shots(name, n):
    (frm / f'{T}_{name}').mkdir(parents=True, exist_ok=True)
    return [f'shot {frm}/{T}_{name}/{i:02d}.png' for i in range(n)]


# (class, screen, placement x, y): Dink is put 70 px to the left of the creature; creatures are held (dink.Npc.Hold 1) and
# hurt through the simulation's own damage path (dink.Creature.Hurt, review only: at the play camera Dink's 1997 reach
# seldom lands on a held creature, bug A70), first a light hit (the flinch), then the kill (the death clip, the corpse).
CASES = [('bonca_gray', 480, 291, 157), ('slayer', 28, 394, 93), ('stone_giant', 178, 337, 93), ('bonca_purple', 514, 334, 188),
         ('slime_red', 192, 194, 209), ('dragon', 124, 194, 157), ('goblin_hammer', 712, 370, 179)]
for name, screen, x, y in CASES:
    gx = max(20, x - 70)
    # A goblin is brain 0 until its script's hit runs (en-gh: sp_brain 9); run it first, as a blow would.
    pre = ['dink.Run en-gh hit S712_P12'] if name.startswith('goblin') else []
    L += [f'dink.Goto {screen} {gx} {y}', 'dink.Npc.Hold 1'] + pre + [ 'dink.CameraDistance 520', 'dink.View -90 -18', 'wait 2.5',
          f'dink.Motion.Trace 14 {mot}/{T}_{name}.csv 1200',
          # a fixed camera on the creature: 70 map px east of Dink (about 6.9 cm per px outdoors), from the south-west, above
          'dink.CalAnchor 480 0', 'dink.CalCam -420 520 330 0 0 90 50 1',
          'dink.TimeDilation 0.15', f'dink.Creature.Hurt {name} 1'] + shots(f'{name}_hit', 10) + \
         ['dink.TimeDilation 1', 'wait 1.2', 'dink.TimeDilation 0.2', f'dink.Creature.Hurt {name} 9999'] + shots(f'{name}_death', 20) + \
         ['dink.TimeDilation 1', 'wait 1', 'dink.CalCam off', 'dink.CameraDistance 260', 'dink.View -60 -25', 'wait 0.5'] + shots(f'{name}_corpse_close', 2) + \
         ['dink.CameraDistance 900', 'dink.View -90 -35', 'wait 0.5'] + shots(f'{name}_corpse_play', 1) + ['dink.Npc.Hold 0', 'wait 1']
# The duck (screen 161, four die5 ducks; S161_P34 at 197,166), held: it fidgets; its own death clip as a review copy beside
# it (no 1997 event kills a duck with its head on); the first hit beheads it (flinch, head-pop, neck spray), the second hit
# on the headless body: it falls, then the burst of sequence 164.
L += ['dink.Goto 161 127 166', 'dink.Npc.Hold 1', 'dink.CameraDistance 420', 'dink.View -90 -15', 'wait 3',
      # a fixed camera on the duck, 70 map px east of Dink (about 4.4 cm per px indoors), low, from the south-west
      'dink.CalAnchor 300 0', 'dink.CalCam -160 200 110 0 0 25 50 1',
      f'dink.Motion.Trace 20 {mot}/{T}_duck.csv 800', 'wait 1'] + shots('duck_idle', 20) + \
     ['dink.TimeDilation 0.25', 'dink.Creature.ShowDeath duck'] + shots('duck_owndeath', 12) + \
     ['dink.TimeDilation 1', 'wait 2', 'dink.TimeDilation 0.15', 'dink.Creature.Hurt duck 1'] + shots('duck_headpop', 14) + \
     ['dink.TimeDilation 1', 'wait 1.5', 'dink.TimeDilation 0.2', 'dink.Creature.Hurt duck 1'] + shots('duck_burstdeath', 24) + \
     ['dink.TimeDilation 1', 'wait 1'] + shots('duck_after_close', 2) + ['dink.CalCam off', 'dink.Npc.Hold 0', 'wait 1']
# A dragon left alone (screen 124): it walks and spits fire at Dink (the attack one-shot).
L += ['dink.Goto 124 60 200', 'dink.CameraDistance 1200', 'dink.View -90 -25', 'wait 2', f'dink.Motion.Trace 25 {mot}/{T}_dragon_fire.csv 3000', 'wait 1'] + shots('dragon_fire', 20) + ['wait 2']
L += ['dink.Fact strength 3', 'dink.TimeDilation 1', 'wait 1', 'quit']
out = cap / f'creatures_{T}.txt'
out.write_text('\n'.join(L) + '\n')
print(out, len(L), 'lines', sum(1 for x in L if x.startswith('shot ')), 'shots')
