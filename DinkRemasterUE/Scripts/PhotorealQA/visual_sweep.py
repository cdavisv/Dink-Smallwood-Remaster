#!/usr/bin/env python3
"""Whole-world visual sweep: one capture run that visits every screen of the world.

    python3 -I Scripts/PhotorealQA/visual_sweep.py <out dir> [--screens=a,b,..] [--wait=4] [--no-over] [--no-audit]
    DINK_CAPTURE_TIMEOUT=7200 Scripts/PhotorealQA/run_capture.sh <out dir>/sweep.txt

Writes <out dir>/sweep.txt for run_capture.sh and <out dir>/sweep_index.json. Per screen of ImportData/screens.json
(all of them, ordered by layout sheet so consecutive screens are neighbours):
  NNN_play.png  the play camera (boom 400 cm, pitch -12, looking north) from the walkable point nearest the centre
                (dink.Player in the log says where the player really stood; the audit line names the screen)
  NNN_over.png  outdoors: a fixed camera behind the screen's south edge looking north over the whole screen;
                indoors: a camera 2.6 m up against the south wall looking across the room
  audit.jsonl   one `dink.SceneAudit` line per screen (every visible primitive and light; see DinkSceneAudit.cpp)
Then `python3 -I Scripts/PhotorealQA/visual_sweep_report.py <out dir>` runs the detectors and makes the sheets.
Reads ImportData/screens.json and the hardness of Content/Dink/Data/Gameplay/Hardness. The script it writes holds
absolute paths: it is written for one run."""
import json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def hardness(screen):
    path = os.path.join(ROOT, 'Content/Dink/Data/Gameplay/Hardness/SCR_%03d.txt' % screen)
    if not os.path.exists(path): return None
    rows = []
    for line in open(path):
        if line.startswith('#') or line.startswith('vision') or not line.strip(): continue
        row = []
        for tok in line.split():
            n, _, code = tok.partition(':')
            row += [int(code or 0)] * int(n)
        rows.append(row)
        if len(rows) == 400: break
    return rows if len(rows) == 400 else None


def walkable_points(screen, n=4):
    """Up to n walkable map pixels (a 17 px square of hardness 0 around each), nearest the screen centre first and at
    least 80 px apart. The hardness files hold no water fill: a point in filled water is refused by dink.Goto (the
    teleport would overlap the water's blocker), so the capture tries the others in turn."""
    hard = hardness(screen)
    if not hard: return []
    free = lambda x, y: all(hard[yy][xx] == 0 for yy in range(max(0, y - 8), min(400, y + 9), 4) for xx in range(max(0, x - 8), min(600, x + 9), 4))
    spots = sorted((math.hypot(x - 300, y - 230), x, y) for y in range(30, 381, 10) for x in range(30, 571, 10) if free(x, y))
    out = []
    for _, x, y in spots:
        if all(math.hypot(x - a, y - b) >= 80 for a, b in out): out.append((x, y))
        if len(out) == n: break
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0]); os.makedirs(out, exist_ok=True)
    opt = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    wait = float(opt.get('wait') or 4)
    screens = json.load(open(os.path.join(ROOT, 'ImportData/screens.json')))['screens']
    if opt.get('screens'):
        want = [int(x) for x in opt['screens'].split(',')]
        screens = [s for n in want for s in screens if s['screen'] == n]
    else:
        screens.sort(key=lambda s: (s['sheet'], s['row'], s['col'], s['screen']))

    def world(s, x, y):   # map pixel -> Unreal cm (x east, y south)
        c = s['corners']; u, v = x / 600.0, y / 400.0
        top = [c['nw'][i] + (c['ne'][i] - c['nw'][i]) * u for i in (0, 1)]
        bot = [c['sw'][i] + (c['se'][i] - c['sw'][i]) * u for i in (0, 1)]
        return [100.0 * (top[i] + (bot[i] - top[i]) * v) for i in (0, 1)]

    audit = os.path.join(out, 'audit.jsonl')
    if os.path.exists(audit) and 'no-audit' not in opt: os.remove(audit)
    # start on the meadow, let the opening scene begin, skip its lines, then never wait on a frame cap
    lines = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 30', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
             't.MaxFPS 0', 'r.VSync 0', 'dink.Fact lifemax 999', 'dink.Fact life 999']
    index = []
    for s in screens:
        n = s['screen']
        pts = walkable_points(n) or [(300, 230), (150, 300), (450, 300), (300, 100)]
        px, py = pts[0]
        shot = lambda kind: 'shot %s/%03d_%s.png' % (out, n, kind)
        # the least preferred point first: a refused teleport leaves the player where the previous one put him
        gotos = ['dink.Goto %d %d %d' % (n, x, y) for x, y in reversed(pts)]
        lines += ['# screen %d %s %s' % (n, s['region'], s['kind']), 'dink.CalCam off'] + gotos + ['dink.CameraDistance 400', 'FOV 0',
                  'dink.View -90 -12', 'wait %g' % wait, 'dink.Player', shot('play')]
        if 'no-audit' not in opt: lines += ['dink.SceneAudit %s' % audit]
        if 'no-over' not in opt:
            me, ctr = world(s, px, py), world(s, 300, 200)
            half_h = (world(s, 300, 400)[1] - world(s, 300, 0)[1]) / 2.0
            dx, dy = ctr[0] - me[0], ctr[1] - me[1]
            lines += ['dink.CalAnchor']
            if s['indoor']:
                # inside the room: against the south wall, 2.6 m up, looking at the far wall's foot
                lines += ['dink.CalCam %.0f %.0f 260 %.0f %.0f 40 80' % (dx, dy + half_h * 0.9, dx, dy - half_h * 0.6)]
            else:
                lines += ['dink.CalCam %.0f %.0f %.0f %.0f %.0f 0 75' % (dx, dy + half_h + 900, max(2200.0, half_h * 1.4), dx, dy - half_h * 0.15)]
            lines += ['wait 1.5', shot('over')]
        index.append({'screen': n, 'region': s['region'], 'kind': s['kind'], 'sheet': s['sheet'], 'indoor': bool(s['indoor']), 'reached': bool(s['reached']),
                      'name': s.get('name') or '', 'player_px': [px, py], 'candidates': pts, 'walkable': bool(walkable_points(n, 1))})
    lines += ['dink.CalCam off', 'wait 1', 'quit']
    open(os.path.join(out, 'sweep.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump(index, open(os.path.join(out, 'sweep_index.json'), 'w'), indent=1)
    shots = sum(1 for l in lines if l.startswith('shot '))
    est = 70 + len(index) * (wait + 0.5 + (2.0 if 'no-over' not in opt else 0))
    print('%d screens, %d shots, about %.0f s -> %s' % (len(index), shots, est, os.path.join(out, 'sweep.txt')))


if __name__ == '__main__':
    main()
