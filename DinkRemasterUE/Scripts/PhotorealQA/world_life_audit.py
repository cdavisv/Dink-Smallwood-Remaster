#!/usr/bin/env python3
"""World-life audit (stream world-alive, 15 Nov 2026): what moves and what stands still, before and after the layer.

    python3 -I Scripts/PhotorealQA/world_life_audit.py <out dir> [--screens=a,b,..] [--passes=0,1] [--no-interact]
    DINK_CAPTURE_TIMEOUT=3600 Scripts/PhotorealQA/run_capture.sh <out dir>/audit.txt
    python3 -I Scripts/PhotorealQA/world_life_motion.py <out dir>        (motion maps, strips, table)

Per screen and pass (pass 0 = `dink.World.Life 0`: master's look; pass 1 = the layer on) at the play camera (boom
400 cm, pitch -12, north): three frames about 0.65 s apart (P<pass>_<NNN>_0..2.png), then closer (boom 220 cm, pitch
-22) two frames (..._c0, _c1). Then interaction strips (pass 1, and the walk also in pass 0): Dink walking through
the meadow and over the earth path of 407, the review-only effects of `dink.World.Demo` (burst, barrel, fire,
fireball), the placed fires of 439 and the torches of 763, chimneys of 469, a barrel hit on 63, the pushable rock of
277; and `fps` lines on the busy town screen 466 with the layer off and on. `dink.World.Stats 1` logs DINK WORLD lines.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import visual_sweep  # noqa: E402  (walkable_points, ROOT)

SCREENS = [
    # stonebrook (village, outskirts, house, cave)
    407, 408, 374, 440, 276, 279, 277, 1, 98,
    # terris (town, bar, wilds, cave)
    466, 464, 34, 272, 304, 514,
    # forest, beaches, coast
    237, 270, 384, 448, 650, 682, 298,
    # windemere and marshes, kernsin, castle
    501, 534, 507, 599, 586, 552, 369, 336, 70,
    # joppa, snow, darklands, goblins, edge, east wilds, camps
    385, 257, 13, 47, 73, 28, 127, 85, 646, 680, 763, 186, 218, 284, 316, 424, 488, 439, 469,
]


def soak(out, seconds):
    """A soak: the layer on, walking and warping over busy screens, effects every lap, DINK WORLD lines every 2 s."""
    lines = ['wait 22', 'dink.Goto 299 300 200', 'wait 30', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
             'dink.Fact lifemax 999', 'dink.Fact life 999', 'dink.World.Life 1', 'dink.World.Stats 1', 'dink.CameraDistance 400', 'dink.View -90 -12']
    lap = [(407, 150, 300, 470, 300), (466, 200, 250, 420, 250), (439, 200, 300, 400, 300), (237, 250, 250, 400, 250), (384, 250, 250, 400, 250),
           (586, 200, 280, 420, 280), (369, 250, 300, 400, 300), (28, 250, 250, 400, 250), (763, 250, 250, 400, 250)]
    t, i = 0.0, 0
    while t < seconds:
        n, x0, y0, x1, y1 = lap[i % len(lap)]
        pts = visual_sweep.walkable_points(n) or [(x0, y0)]
        lines += ['dink.Goto %d %d %d' % (n, pts[0][0], pts[0][1]), 'wait 2', 'dink.WalkTo %d %d 6' % (x1, y1), 'wait 3',
                  'dink.World.Demo burst 250', 'wait 1', 'dink.World.Demo barrel 250', 'wait 1', 'dink.World.Demo fireball 250', 'wait 2',
                  'dink.World.Demo fire 300', 'wait 6', 'fps soak_%03d_%d' % (n, i)]
        if i % 6 == 0: lines += ['shot %s/soak_%02d.png' % (out, i)]
        t += 15.5; i += 1
    lines += ['wait 15', 'shot %s/soak_end.png' % out, 'dink.World.Stats 0', 'quit']
    open(os.path.join(out, 'soak.txt'), 'w').write('\n'.join(lines) + '\n')
    print('soak: %d laps, about %.0f s -> %s' % (i, t + 70, os.path.join(out, 'soak.txt')))


def focus(out):
    """Second, short capture after tuning: the interactions the full audit could not show, at the play camera."""
    shot = lambda name: 'shot %s/%s.png' % (out, name)
    ready = ['dink.Skip', 'wait 0.3', 'dink.Skip', 'wait 0.3', 'dink.Skip', 'wait 0.3', 'dink.Arm 1', 'dink.Inventory']
    lines = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 30', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
             't.MaxFPS 0', 'r.VSync 0', 'dink.Fact lifemax 999', 'dink.Fact life 999', 'dink.World.Stats 1', 'dink.CalCam off']
    # walk 408 west to east along the clear row y 210: earth path (dust) then meadow (bend), layer off then on
    for life in (0, 1):
        lines += ['# walk 408 life %d' % life, 'dink.World.Life %d' % life, 'dink.Goto 408 80 210'] + ready + [
                  'dink.CameraDistance 300', 'dink.View -60 -20', 'wait 2', 'dink.WalkTo 520 210 8']
        for i in range(12):
            lines += [shot('F%d_walk408_%02d' % (life, i)), 'wait 0.05']
        lines += ['wait 3']
    # close look at the feet (16 Nov): the same walk at a low near camera, layer off then on, for the dust and the bend
    for life in (0, 1):
        lines += ['# close walk 408 life %d' % life, 'dink.World.Life %d' % life, 'dink.Goto 408 80 210'] + ready + [
                  'dink.CameraDistance 200', 'dink.View -60 -30', 'wait 2', 'dink.WalkTo 520 210 8']
        for i in range(10):
            lines += [shot('C%d_walk408_%02d' % (life, i)), 'wait 0.1']
        lines += ['wait 3']
    lines += ['dink.World.Life 1', 'wait 1']
    # demos at a closer play camera
    lines += ['# demos', 'dink.Goto 408 300 210'] + ready + ['dink.CameraDistance 320', 'dink.View -90 -15', 'wait 2']
    for kind in ('burst', 'fireball', 'barrel', 'dust'):
        lines += ['dink.World.Demo %s 220' % kind, 'wait 0.05', shot('F_demo_%s_0' % kind), shot('F_demo_%s_1' % kind), 'wait 0.5', shot('F_demo_%s_2' % kind), 'wait 2.5']
    lines += ['dink.World.Demo fire 220', 'wait 3', shot('F_demo_fire_0'), 'wait 0.2', shot('F_demo_fire_1'), 'wait 9',
              'dink.World.Demo bigfire 450', 'wait 3', shot('F_demo_bigfire_0'), 'wait 0.3', shot('F_demo_bigfire_1'), 'wait 10']
    # placed torches and the hearth
    # stand south of a torch (16 Nov: the old point did not frame one): S763_P19 (470,222), S764_P04 (132,200), S764_P05 (260,321)
    def near(n, x, y):
        pts = visual_sweep.walkable_points(n, 60) or [(x, y + 60)]
        south = [p for p in pts if p[1] > y + 30] or pts
        return min(south, key=lambda p: (p[0] - x) ** 2 + (p[1] - y - 70) ** 2)
    for n, tx, ty, tag in ((763, 470, 222, 'torch763'), (764, 132, 200, 'torch764'), (764, 260, 321, 'torch764b'), (1, 300, 230, 'hearth001')):
        x, y = near(n, tx, ty)
        lines += ['# %s' % tag, 'dink.Goto %d %d %d' % (n, x, y)] + ready + [
                  'dink.CameraDistance 320', 'dink.View -90 -15', 'wait 4', shot('F_%s_0' % tag), 'wait 0.3', shot('F_%s_1' % tag)]
        if n != 1:
            lines += ['wait 6', 'dink.CameraDistance 300', 'dink.View -90 -12', 'wait 2', shot('F_%s_night_like' % tag)]
    # barrel on 63 (bar-sh at 324,313): from the south, walk into it (faces north), hit
    lines += ['# barrel 63', 'dink.Goto 63 324 345'] + ready + ['dink.CameraDistance 300', 'dink.View -90 -18', 'wait 2', 'dink.WalkTo 324 328 0.8', 'wait 1',
              'dink.Player', 'dink.Attack', 'wait 0.3', shot('F_barrel63_0'), 'wait 0.2', shot('F_barrel63_1'), 'wait 0.5', shot('F_barrel63_2'), 'wait 1.5',
              'dink.Attack', 'wait 0.5', shot('F_barrel63_3'), 'wait 3', shot('F_barrel63_4')]
    # the pushable rock of 277 (s1-roc at 265,180; hardness rows 180-194): lean on it from the south
    # s1-roc push(): strength 4 or more, Dink facing east (dir 6) moves the rock to x 350 (move_stop); stand west of it
    lines += ['# rock 277', 'dink.Fact strength 6', 'dink.Goto 277 192 186'] + ready + ['dink.CameraDistance 340', 'dink.View -90 -15', 'wait 2',
              'dink.WalkTo 340 186 14']
    for i in range(16):
        lines += ['wait 0.7', shot('F_rock277_%02d' % i)]
    lines += ['dink.Player', 'wait 1', 'dink.World.Stats 0', 'quit']
    open(os.path.join(out, 'focus.txt'), 'w').write('\n'.join(lines) + '\n')
    print('focus: %d shots -> %s' % (sum(1 for l in lines if l.startswith('shot ')), os.path.join(out, 'focus.txt')))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0]); os.makedirs(out, exist_ok=True)
    opt = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    if opt.get('soak'):
        return soak(out, float(opt['soak']))
    if 'focus' in opt:
        return focus(out)
    screens = [int(x) for x in opt['screens'].split(',')] if opt.get('screens') else SCREENS
    passes = [int(x) for x in (opt.get('passes') or '0,1').split(',')]
    info = {s['screen']: s for s in json.load(open(os.path.join(visual_sweep.ROOT, 'ImportData/screens.json')))['screens']}
    shot = lambda name: 'shot %s/%s.png' % (out, name)
    lines = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 30', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
             't.MaxFPS 0', 'r.VSync 0', 'dink.Fact lifemax 999', 'dink.Fact life 999', 'dink.World.Stats 1', 'dink.CalCam off']
    index = []

    def goto(n, pts=None):
        pts = pts or visual_sweep.walkable_points(n) or [(300, 230), (150, 300), (450, 300), (300, 100)]
        return ['dink.Goto %d %d %d' % (n, x, y) for x, y in reversed(pts)]

    for p in passes:
        lines += ['# ---- pass %d' % p, 'dink.World.Life %d' % p, 'wait 1']
        for n in screens:
            s = info.get(n)
            if not s: continue
            tag = 'P%d_%03d' % (p, n)
            lines += ['# screen %d %s %s' % (n, s['region'], s['kind'])] + goto(n) + ['dink.CameraDistance 400', 'FOV 0', 'dink.View -90 -12', 'wait 3', 'dink.Player',
                      shot(tag + '_0'), 'wait 0.15', shot(tag + '_1'), 'wait 0.15', shot(tag + '_2'),
                      'dink.CameraDistance 220', 'dink.View -90 -22', 'wait 1', shot(tag + '_c0'), 'wait 0.2', shot(tag + '_c1')]
            if p == passes[0]:
                index.append({'screen': n, 'region': s['region'], 'kind': s['kind'], 'indoor': bool(s['indoor']), 'name': s.get('name') or ''})
        if 'no-interact' in opt: continue
        # walk through the meadow and over the path (both passes: grass bend and footstep dust are the difference)
        lines += ['# walk 407 pass %d' % p] + goto(407, [(150, 300)]) + ['dink.CameraDistance 300', 'dink.View -60 -18', 'wait 2', 'dink.WalkTo 470 300 6']
        for i in range(8):
            lines += [shot('P%d_walk407_%d' % (p, i)), 'wait 0.1']
        lines += ['wait 2']
        # busy screen frame rate
        lines += ['# fps 466 pass %d' % p] + goto(466) + ['dink.CameraDistance 400', 'dink.View -90 -12', 'wait 4', 'wait 6', 'fps P%d_466' % p, 'wait 6', 'fps P%d_466b' % p]
        lines += goto(407) + ['dink.CameraDistance 400', 'dink.View -90 -12', 'wait 4', 'wait 6', 'fps P%d_407' % p]
        if p != 1: continue
        # GPU shadow cost (perf-stutter's ShadowDepths finding) at Epic and High, the layer off and on: the pine forest 312,
        # the family-art trees of 438, the coast 650
        lines += ['# gpu', 'r.GPUCsvStatsEnabled 1']
        for n in (312, 438, 650):
            lines += goto(n) + ['dink.CameraDistance 400', 'dink.View -90 -12', 'wait 3']
            for level in (3, 2):
                for life in (0, 1):
                    lines += ['scalability %d' % level, 'dink.World.Life %d' % life, 'wait 4', 'csvprofile start', 'wait 8', 'csvprofile stop',
                              'fps gpu%03d_q%d_life%d' % (n, level, life), 'wait 2']
        lines += ['scalability 3', 'dink.World.Life 1', 'wait 2']
        # review-only effects ahead of Dink at the play camera
        lines += ['# demos'] + goto(407, [(300, 250)]) + ['dink.CameraDistance 400', 'dink.View -90 -12', 'wait 2']
        for kind in ('burst', 'barrel', 'fireball', 'dust'):
            lines += ['dink.World.Demo %s 250' % kind, 'wait 0.05', shot('demo_%s_0' % kind), shot('demo_%s_1' % kind), 'wait 0.6', shot('demo_%s_2' % kind), 'wait 2']
        lines += ['dink.World.Demo fire 250', 'wait 3', shot('demo_fire_0'), shot('demo_fire_1'), 'dink.CameraDistance 220', 'dink.View -90 -22', 'wait 0.5', shot('demo_fire_c'),
                  'dink.CameraDistance 400', 'dink.View -90 -12', 'wait 9',
                  'dink.World.Demo bigfire 400', 'wait 3', shot('demo_bigfire_0'), 'wait 0.3', shot('demo_bigfire_1'), 'wait 10']
        # placed fires, torches, chimneys
        for n, tag in ((439, 'fire439'), (763, 'torch763'), (469, 'chimney469'), (1, 'hearth001')):
            lines += ['# %s' % tag] + goto(n) + ['dink.CameraDistance 400', 'dink.View -90 -12', 'wait 4', shot(tag + '_0'), 'wait 0.2', shot(tag + '_1'),
                      'dink.CameraDistance 220', 'dink.View -90 -22', 'wait 1', shot(tag + '_c')]
        # barrel on 63 (bar-sh at 324,313): walk up to it from the south and hit it
        lines += ['# barrel 63'] + goto(63, [(324, 352)]) + ['dink.CameraDistance 300', 'dink.View -90 -18', 'wait 2', 'dink.WalkTo 324 336 1.5', 'wait 1.6',
                  'dink.Attack', 'wait 0.35', shot('barrel63_0'), 'wait 0.25', shot('barrel63_1'), 'wait 0.6', shot('barrel63_2'), 'wait 2', 'dink.Attack', 'wait 0.6', shot('barrel63_3'), 'wait 3']
        # the pushable rock of 277 (s1-roc at 265,180): lean on it from the south
        lines += ['# rock 277'] + goto(277, [(265, 222)]) + ['dink.CameraDistance 300', 'dink.View -90 -18', 'wait 2', 'dink.WalkTo 265 150 6']
        for i in range(6):
            lines += ['wait 0.6', shot('rock277_%d' % i)]
        lines += ['wait 1']
    lines += ['dink.World.Stats 0', 'wait 1', 'quit']
    open(os.path.join(out, 'audit.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump(index, open(os.path.join(out, 'audit_index.json'), 'w'), indent=1)
    print('%d screens x %d passes, %d shots -> %s' % (len(index), len(passes), sum(1 for l in lines if l.startswith('shot ')), os.path.join(out, 'audit.txt')))


if __name__ == '__main__':
    main()
