#!/usr/bin/env python3
"""Capture script for the ground-layer outlines (VS-09): per screen the visual sweep's play and over views (same
cameras as Scripts/PhotorealQA/visual_sweep.py, so its frames compare), a high top view of the whole screen, views
across chosen screen borders, and frame-rate samples on one busy screen.

    python3 -I Scripts/PhotorealQA/terrain_layers_script.py <out dir> --screens=59,245,... [--borders=341:342,351:383] [--fps=341]
    <shared>/DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh Scripts/PhotorealQA/run_capture.sh <out dir>/terrain.txt

Shots: NNN_play.png, NNN_over.png, NNN_top.png; border_A_B_play.png (the hero on A next to the shared edge, looking
across it) and border_A_B_over.png (a high camera over the middle of the shared edge); `fps` lines in the capture log
(DINK CAPTURE: fps terrain_NNN_k) after an 8 s settle at the play camera. Reads ImportData/screens.json and the
hardness files, like visual_sweep.py."""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from visual_sweep import ROOT, hardness, walkable_points  # noqa: E402


def world(s, x, y):   # map pixel -> Unreal cm (x east, y south)
    c = s['corners']; u, v = x / 600.0, y / 400.0
    top = [c['nw'][i] + (c['ne'][i] - c['nw'][i]) * u for i in (0, 1)]
    bot = [c['sw'][i] + (c['se'][i] - c['sw'][i]) * u for i in (0, 1)]
    return [100.0 * (top[i] + (bot[i] - top[i]) * v) for i in (0, 1)]


def nearest_walkable(screen, x, y):
    hard = hardness(screen)
    if not hard:
        return None
    free = lambda a, b: all(hard[yy][xx] == 0 for yy in range(max(0, b - 8), min(400, b + 9), 4) for xx in range(max(0, a - 8), min(600, a + 9), 4))
    best = sorted((math.hypot(a - x, b - y), a, b) for b in range(20, 381, 6) for a in range(20, 581, 6) if free(a, b))
    return (best[0][1], best[0][2]) if best else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0]); os.makedirs(out, exist_ok=True)
    opt = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    recs = {s['screen']: s for s in json.load(open(os.path.join(ROOT, 'ImportData/screens.json')))['screens']}
    want = [int(x) for x in (opt.get('screens') or '').split(',') if x]
    borders = [tuple(int(v) for v in b.split(':')) for b in (opt.get('borders') or '').split(',') if b]
    fps_screens = [int(x) for x in (opt.get('fps') or '').split(',') if x]
    lines = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 30', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
             't.MaxFPS 0', 'r.VSync 0', 'dink.Fact lifemax 999', 'dink.Fact life 999']
    shot = lambda name: 'shot %s/%s.png' % (out, name)
    for n in want:
        s = recs[n]
        pts = walkable_points(n) or [(300, 230), (150, 300), (450, 300), (300, 100)]
        px, py = pts[0]
        lines += ['# screen %d' % n, 'dink.CalCam off'] + ['dink.Goto %d %d %d' % (n, x, y) for x, y in reversed(pts)] + [
            'dink.CameraDistance 400', 'FOV 0', 'dink.View -90 -12', 'wait 4', 'dink.Player', shot('%03d_play' % n)]
        me, ctr = world(s, px, py), world(s, 300, 200)
        half_h = (world(s, 300, 400)[1] - world(s, 300, 0)[1]) / 2.0
        width = world(s, 600, 200)[0] - world(s, 0, 200)[0]
        dx, dy = ctr[0] - me[0], ctr[1] - me[1]
        lines += ['dink.CalAnchor', 'dink.CalCam %.0f %.0f %.0f %.0f %.0f 0 75' % (dx, dy + half_h + 900, max(2200.0, half_h * 1.4), dx, dy - half_h * 0.15),
                  'wait 1.5', shot('%03d_over' % n),
                  'dink.CalCam %.0f %.0f %.0f %.0f %.0f 0 75' % (dx, dy + half_h * 0.35, max(2600.0, width * 0.62), dx, dy - half_h * 0.05),
                  'wait 1.5', shot('%03d_top' % n), 'dink.CalCam off']
    for a, b in borders:
        sa, sb = recs[a], recs[b]
        east = (b - a) == 1
        # the shared edge's middle, in screen a's map pixels
        ex, ey = (600, 200) if east else (300, 400)
        stand = nearest_walkable(a, 540 if east else 300, 200 if east else 350)
        if stand is None:
            continue
        sx, sy = stand
        yaw = 0 if east else 90          # look across the edge: east (+X) or south (+Y)
        lines += ['# border %d|%d' % (a, b), 'dink.CalCam off', 'dink.Goto %d %d %d' % (a, sx, sy), 'dink.CameraDistance 400', 'FOV 0',
                  'dink.View %d -12' % yaw, 'wait 4', 'dink.Player', shot('border_%03d_%03d_play' % (a, b))]
        me, edge = world(sa, sx, sy), world(sa, ex, ey)
        dx, dy = edge[0] - me[0], edge[1] - me[1]
        span = (world(sa, 300, 400)[1] - world(sa, 300, 0)[1]) if east else (world(sa, 600, 200)[0] - world(sa, 0, 200)[0])
        lines += ['dink.CalAnchor', 'dink.CalCam %.0f %.0f %.0f %.0f %.0f 0 75' % (dx, dy + 1, max(2600.0, span * 0.62), dx, dy),
                  'wait 1.5', shot('border_%03d_%03d_over' % (a, b)), 'dink.CalCam off']
    for n in fps_screens:
        pts = walkable_points(n) or [(300, 230)]
        for k in range(3):
            lines += ['dink.CalCam off', 'dink.Goto %d %d %d' % (n, pts[0][0], pts[0][1]), 'dink.CameraDistance 400', 'FOV 0', 'dink.View -90 -12',
                      'wait 8', 'fps terrain_%03d_%d' % (n, k)]
    lines += ['dink.CalCam off', 'wait 1', 'quit']
    open(os.path.join(out, 'terrain.txt'), 'w').write('\n'.join(lines) + '\n')
    print('%d shots -> %s' % (sum(1 for l in lines if l.startswith('shot ')), os.path.join(out, 'terrain.txt')))


if __name__ == '__main__':
    main()
