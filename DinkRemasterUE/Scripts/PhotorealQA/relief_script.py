#!/usr/bin/env python3
"""Capture script for the ground relief review (parallax relief of M_Env_Terrain, dink.GroundRelief):
    python3 -I Scripts/PhotorealQA/relief_script.py <out dir> --screens=439,407:300:250,.. [--scales=0,1] [--settle=4]

Per screen (optionally screen:x:y = where the player stands, in map pixels; default the walkable point nearest
the centre) and per view, one shot per relief scale, taken in the same run from the same camera:
  NNN_play_<s>    the play camera (boom 400 cm, pitch -12, looking north), with the frame rate over the settle time
  NNN_feet_<s>    a low camera 1.5 m from the player's feet (the hero in frame: do the feet meet the ground?)
  NNN_close_<s>   a camera 1.1 m above the ground looking down at the ground 2.5 m ahead
  NNN_low_<s>     a camera 30 cm above the ground looking along it (grazing angle)
<s> is the scale times 100 (000 = flat sheet, 100 = as authored). Writes <out dir>/relief.txt for run_capture.sh and
relief_index.json. The script holds absolute paths: written for one run, not committed."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ground_script import hardness, screen_table  # noqa: E402

VIEWS = (('feet', 'dink.CalCam 110 100 45 0 0 12 42 1'), ('close', 'dink.CalCam 0 60 110 0 -250 0 60'), ('low', 'dink.CalCam 0 110 30 0 -160 4 55'))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0]); os.makedirs(out, exist_ok=True)
    opt = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    scales = [float(s) for s in opt.get('scales', '0,1').split(',')]
    settle = float(opt.get('settle', 4))
    table = screen_table()
    lines = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 40', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 't.MaxFPS 0', 'r.VSync 0']
    index = []
    for token in opt['screens'].split(','):
        parts = [int(p) for p in token.split(':')]
        screen = parts[0]
        if len(parts) == 3:
            px, py = parts[1:]
        else:
            hard = hardness(screen)
            free = lambda x, y: all(hard[yy][xx] == 0 for yy in range(max(0, y - 8), min(400, y + 9), 4) for xx in range(max(0, x - 8), min(600, x + 9), 4))
            spots = [(math.hypot(x - 300, y - 230), x, y) for y in range(30, 381, 10) for x in range(30, 571, 10) if free(x, y)]
            px, py = min(spots)[1:] if spots else (300, 230)
        tag = lambda s: '%03d' % round(s * 100)
        shot = lambda kind, s: 'shot %s/%03d_%s_%s.png' % (out, screen, kind, tag(s))
        lines += ['dink.CalCam off', 'dink.Goto %d %d %d' % (screen, px, py), 'dink.CameraDistance 400', 'FOV 0', 'wait 1', 'dink.View -90 -12', 'wait 6', 'dink.Player']
        for s in scales:
            lines += ['dink.GroundRelief %g' % s, 'wait %g' % settle, 'fps %03d_play_%s' % (screen, tag(s)), shot('play', s), 'wait 1']
        lines += ['dink.CalAnchor']
        for kind, cam in VIEWS:
            lines += [cam, 'wait 2']
            for s in scales:
                lines += ['dink.GroundRelief %g' % s, 'wait 1.5', shot(kind, s), 'wait 1']
        o = table[screen]
        index.append({'screen': screen, 'indoor': o['indoor'], 'classes': o['classes'], 'layers': o['layers'], 'player_px': [px, py]})
    lines += ['dink.CalCam off', 'dink.GroundRelief 1', 'wait 1', 'quit']
    open(os.path.join(out, 'relief.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump({'scales': scales, 'screens': index}, open(os.path.join(out, 'relief_index.json'), 'w'), indent=1)
    print('%d screens, %d shots -> %s' % (len(index), sum(1 for l in lines if l.startswith('shot ')), os.path.join(out, 'relief.txt')))


if __name__ == '__main__':
    main()
