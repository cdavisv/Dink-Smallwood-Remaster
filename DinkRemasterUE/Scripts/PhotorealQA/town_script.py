#!/usr/bin/env python3
"""Capture script for the town-house screens: python3 -I Scripts/PhotorealQA/town_script.py <out dir> [--close] [--screens a,b,..]

Writes <out dir>/town.txt for run_capture.sh. Per screen of Content/Dink/Data/Art/town_houses.json:
  NNN_play    the play camera (boom 400 cm, pitch -12) from a walkable point on the street side of the houses (never
              inside or behind an assembled house body), looking at them
  NNN_south   a fixed camera above the screen's south edge looking north over the whole screen
  NNN_north   the same from the north edge (the backs of the houses and the ground the hidden roof cards stood on)
--close adds, per house front, a street-level view from 7 m in front (NNN_close_<k>) and a view of its roof and back
from 9 m up behind it (NNN_roof_<k>); --only-close leaves the three screen views out.
Run it twice, once with `-dpcvars=dink.TownHouses=0`, to get the sprite cards for comparison (dink.TownHouses is read
when a screen comes into range). Reads ImportData/screens.json, ImportData/placements.json and the hardness of
Content/Dink/Data/Gameplay/Hardness. Paths in the script are absolute: it is written for one run, not committed."""
import json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def hardness(screen):
    rows = []
    for line in open(os.path.join(ROOT, 'Content/Dink/Data/Gameplay/Hardness/SCR_%03d.txt' % screen)):
        if line.startswith('#') or line.startswith('vision') or not line.strip(): continue
        row = []
        for tok in line.split():
            n, _, code = tok.partition(':')
            row += [int(code or 0)] * int(n)
        rows.append(row)
        if len(rows) == 400: break
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0]); os.makedirs(out, exist_ok=True)
    close = '--close' in sys.argv or '--only-close' in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith('--screens='): only = {int(x) for x in a.split('=')[1].split(',')}
    screens = {s['screen']: s for s in json.load(open(os.path.join(ROOT, 'ImportData/screens.json')))['screens']}
    placements = json.load(open(os.path.join(ROOT, 'ImportData/placements.json')))['placements']
    town = json.load(open(os.path.join(ROOT, 'Content/Dink/Data/Art/town_houses.json')))['screens']

    def world(screen, x, y):   # map pixel -> Unreal cm (x east, y south)
        c = screens[screen]['corners']; u, v = x / 600.0, y / 400.0
        top = [c['nw'][i] + (c['ne'][i] - c['nw'][i]) * u for i in (0, 1)]
        bot = [c['sw'][i] + (c['se'][i] - c['sw'][i]) * u for i in (0, 1)]
        return [100.0 * (top[i] + (bot[i] - top[i]) * v) for i in (0, 1)]

    mpp = {}
    for p in placements: mpp.setdefault(p['screen'], p['m_per_px'])
    gpx = lambda screen, x, y: ((screen - 1) % 32 * 600 + x, (screen - 1) // 32 * 400 + y)   # town-wide map pixel
    bodies = []
    for key, row in town.items():
        for f in row.get('footprints') or []:
            ox, oy = gpx(int(key), *f['px']); a = math.radians(f['yaw'])
            bodies.append((ox, oy, math.cos(a), math.sin(a), mpp[int(key)] * 100.0, f['rect_cm']))

    def street(screen, x, y):
        """False for a point inside an assembled house body or up to 30 m straight behind one: the ground behind the
        wall line is the inside of the 1997 building. Its hardness is 0, so a capture can be teleported there, but no
        player walks there (the wall line and the door warps close it), and a view from there shows the houses from within."""
        gx, gy = gpx(screen, x, y)
        for ox, oy, c, s, cm, (x0, y0, x1, y1) in bodies:
            lx, ly = ((gx - ox) * c + (gy - oy) * s) * cm, (-(gx - ox) * s + (gy - oy) * c) * cm
            if x0 - 100 <= lx <= x1 + 100 and y0 - 3000 <= ly <= y1 + 100: return False
        return True

    lines = ['wait 22', 'dink.Goto 506 300 360', 'dink.View -90 -12', 'wait 40', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 't.MaxFPS 0', 'r.VSync 0']
    index = []
    for key in sorted(town, key=int):
        screen = int(key)
        if only and screen not in only: continue
        cards = [p for p in placements if p['screen'] == screen and p['seq'] == 33]
        walls = [p for p in cards if p['class_id'].startswith('town_wall_stone')] or cards
        cx = sum(p['map_x'] for p in walls) / len(walls); cy = sum(p['map_y'] for p in walls) / len(walls)
        hard = hardness(screen)
        free = lambda x, y: all(hard[yy][xx] == 0 for yy in range(max(0, y - 8), min(400, y + 9), 4) for xx in range(max(0, x - 8), min(600, x + 9), 4))
        target = (min(570, max(30, cx)), min(380, max(30, cy + 120)))
        spots = [(math.hypot(x - target[0], y - target[1]), x, y) for y in range(30, 381, 10) for x in range(30, 571, 10) if free(x, y) and street(screen, x, y)]
        if not spots:     # nothing on the street side: any free point
            spots = [(math.hypot(x - target[0], y - target[1]), x, y) for y in range(30, 381, 10) for x in range(30, 571, 10) if free(x, y)]
        if not spots:
            lines.append('# screen %d: no walkable point' % screen); px, py = 300, 380
        else:
            _, px, py = min(spots)
        me = world(screen, px, py); at = world(screen, cx, cy)
        yaw = math.degrees(math.atan2(at[1] - me[1], at[0] - me[0]))
        if math.hypot(at[0] - me[0], at[1] - me[1]) < 300: yaw = -90.0
        views = '--only-close' not in sys.argv
        if not views and not any(h.get('modules') for h in town[key]['houses']): continue
        lines += ['dink.CalCam off', 'dink.Goto %d %d %d' % (screen, px, py), 'dink.CameraDistance 400', 'FOV 0', 'wait 1', 'dink.View %.0f -12' % yaw, 'wait 6', 'dink.Player', 'wait 1']
        if views: lines += ['shot %s/%03d_play.png' % (out, screen), 'wait 1']
        lines += ['dink.CalAnchor']
        ctr = world(screen, 300, 200); half_h = (world(screen, 300, 400)[1] - world(screen, 300, 0)[1]) / 2.0
        dx, dy = ctr[0] - me[0], ctr[1] - me[1]
        if views:
            lines += ['dink.CalCam %.0f %.0f %.0f %.0f %.0f 0 70' % (dx, dy + half_h + 1500, 2800, dx, dy - 400), 'wait 3', 'shot %s/%03d_south.png' % (out, screen), 'wait 1',
                      'dink.CalCam %.0f %.0f %.0f %.0f %.0f 0 70' % (dx, dy - half_h - 1500, 2800, dx, dy + 400), 'wait 3', 'shot %s/%03d_north.png' % (out, screen), 'wait 1']
        index.append({'screen': screen, 'player_px': [px, py], 'yaw': round(yaw), 'cards': len(cards)})
        if close:
            for k, run in enumerate(h for h in town[key]['houses'] if h.get('modules')):
                (sx, sy), (ex, ey) = run['start_px'], run['end_px']
                a, b = world(screen, sx, sy), world(screen, ex, ey)
                mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; d = [b[0] - a[0], b[1] - a[1]]; n = math.hypot(*d) or 1.0
                front = [-d[1] / n, d[0] / n]   # the street side of a run (the house body lies on the other side)
                if front[1] < 0: front = [-front[0], -front[1]]
                eye = [mid[0] + front[0] * 700 - me[0], mid[1] + front[1] * 700 - me[1]]
                lines += ['dink.CalCam %.0f %.0f 170 %.0f %.0f 330 60' % (eye[0], eye[1], mid[0] - me[0], mid[1] - me[1]), 'wait 3', 'shot %s/%03d_close_%d.png' % (out, screen, k + 1), 'wait 1']
                # the roof and the back of the same run, from 9 m above the ground 13 m behind the wall line
                back = [mid[0] - front[0] * 1300 - me[0], mid[1] - front[1] * 1300 - me[1]]
                lines += ['dink.CalCam %.0f %.0f 900 %.0f %.0f 450 60' % (back[0], back[1], mid[0] - front[0] * 400 - me[0], mid[1] - front[1] * 400 - me[1]), 'wait 3',
                          'shot %s/%03d_roof_%d.png' % (out, screen, k + 1), 'wait 1']
    lines += ['dink.CalCam off', 'wait 1', 'quit']
    open(os.path.join(out, 'town.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump(index, open(os.path.join(out, 'town_index.json'), 'w'), indent=1)
    print('%d screens, %d shots -> %s' % (len(index), sum(1 for l in lines if l.startswith('shot ')), os.path.join(out, 'town.txt')))


if __name__ == '__main__':
    main()
