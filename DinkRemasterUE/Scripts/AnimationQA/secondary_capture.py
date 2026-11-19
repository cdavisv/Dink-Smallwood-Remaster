"""dink.CaptureScript files for the secondary motion (hair, Mother's skirt, hit jolt) in the running game.

  python3 -I Scripts/AnimationQA/secondary_capture.py            # writes Saved/SecondaryMotion/capture/*.txt
  Scripts/PhotorealQA/run_capture.sh <ABS path of one .txt>      # offscreen, no display, no input, no sound
  python3 -I Scripts/AnimationQA/secondary_strip.py <name>       # tiles the frames (Saved/SecondaryMotion/<name>.jpg)

Before/after pairs come from the same run: two shots in a row with the part switched off and on, in slow motion
(dink.TimeDilation), so the pose between them hardly changes. Output stays under Saved/ (git-ignored).
"""
from pathlib import Path

project = Path(__file__).resolve().parents[2]
out = project / 'Saved/SecondaryMotion/capture'
out.mkdir(parents=True, exist_ok=True)
FRAMES = project / 'Saved/SecondaryMotion/frames'
START = ['wait 22', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Secondary.Report']


def shots(name, count, toggle=None, before=()):
    """count shots; with toggle (a console variable) every shot is a pair: off, then on. before: commands run ahead of
    each shot or pair (re-aim a camera on a walking body)."""
    rows = []
    for i in range(count):
        rows += list(before)
        if toggle:
            rows += ['%s 0' % toggle, 'shot %s/%s/%02d_off.png' % (FRAMES, name, i), '%s 1' % toggle, 'shot %s/%s/%02d_on.png' % (FRAMES, name, i)]
        else:
            rows.append('shot %s/%s/%02d.png' % (FRAMES, name, i))
    return rows


def write(name, body):
    (out / (name + '.txt')).write_text('\n'.join(START + body + ['dink.TimeDilation 1', 'dink.Secondary.Report', 'wait 1', 'quit']) + '\n')


# Hero, outdoors (screen 438; map x runs east). A fixed close camera from the side at his start point (dink.CalCam,
# world axes after dink.CalAnchor), then the play camera (dink.CalCam off).
HERO = ['dink.ScreenScripts 0', 'dink.Goto 438 300 200', 'wait 2', 'dink.CalAnchor', 'dink.CalCam 30 -230 165 30 0 158 34 1', 'wait 2']
write('hero_hair', HERO + [
    '# idle in the wind, real time', 'fps idle_close'] + shots('hero_idle_wind', 6) + [
    '# hit jolt, slow motion', 'dink.TimeDilation 0.1', 'dink.Secondary.Hit 1'] + shots('hero_hit', 10) + [
    'dink.TimeDilation 1', 'wait 2', '# run start, slow motion', 'dink.Hero.Gait 2', 'dink.TimeDilation 0.1', 'dink.WalkTo 590 200 8'] + shots('hero_run_start', 10) + [
    'dink.TimeDilation 1', 'wait 1.2', '# turn round and run back past the camera, slow motion', 'dink.TimeDilation 0.1', 'dink.WalkTo 250 200 8'] + shots('hero_turn', 14) + [
    'dink.TimeDilation 1', 'wait 2', 'dink.Goto 438 300 200', 'wait 2', '# before/after at the same instant, start of a run',
    'dink.TimeDilation 0.05', 'dink.WalkTo 590 200 8', 'wait 0.3'] + shots('hero_ab', 4, 'dink.Hair.Physics') + [
    'dink.TimeDilation 1', 'wait 2', '# play camera', 'dink.CalCam off', 'wait 1', 'dink.WalkTo 300 200 8', 'dink.TimeDilation 0.2'] +
    shots('hero_play', 6) + ['dink.TimeDilation 1', 'wait 3', 'fps play_camera'])
# Mother in her house: her own wandering. Legs from the side, before/after pairs (skinned skirt / bell).
MOTHER = ['dink.Goto 1 330 250', 'wait 3', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 4']
write('mother_skirt', MOTHER + [
    'dink.TimeDilation 0.25'] + shots('mother_skirt_ab', 10, 'dink.Garment.Physics', ('dink.CalAnchorNpc 0', 'dink.CalCam 0 -260 80 0 0 70 38')) +
    shots('mother_head', 6, None, ('dink.CalAnchorNpc 0', 'dink.CalCam 60 -130 165 0 0 158 30')) + [
    'dink.TimeDilation 1', 'dink.CalCam off', 'wait 1'] + shots('mother_play', 4, 'dink.Garment.Physics') + ['fps mother_room'])
# Milder: the pig-feeding cutscene of screen 407 (item-pig.c spawns him with s1-bul when &pig_story is 0).
write('milder', ['dink.ScreenScripts 0', 'dink.Goto 407 300 250', 'wait 2', 'dink.Run item-pig use', 'wait 3', 'dink.Skip', 'wait 4',
                 'dink.TimeDilation 0.3'] + shots('milder_head', 8, None, ('dink.CalAnchorNpc 0', 'dink.CalCam 140 -60 165 0 0 160 30 1')) + [
    'dink.TimeDilation 1'] + ['dink.Skip', 'wait 1.5'] * 8 + ['dink.TimeDilation 0.3'] + shots('milder_leave', 6, None, ('dink.CalAnchorNpc 0', 'dink.CalCam 0 -300 120 0 0 100 40 1')) + [
    'dink.CalCam off'])
print('wrote', sorted(p.name for p in out.glob('*.txt')))
