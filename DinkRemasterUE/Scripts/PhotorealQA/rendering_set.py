#!/usr/bin/env python3
"""Fixed review set of the rendering pass (15 Nov 2026): 16 frames at the play camera plus a close-up of Dink,
each with its frame timings, captured once per variant in ONE game session.

    python3 -I Scripts/PhotorealQA/rendering_set.py <out dir> [--variant name 'cmd;cmd' ...] [--only a,b] [--settle 5] [--measure 3] [--res 2560x1440]
    DINK_RESX=2560 DINK_RESY=1440 DINK_CAPTURE_TIMEOUT=3000 Scripts/PhotorealQA/run_capture.sh <out dir>/set.txt

Writes <out dir>/set.txt. Every variant first runs its console commands (cvars, dink.EnvPost ...), then visits the
same frames; frames go to <out dir>/<variant>/<name>.png and the log gets one line per frame:
`DINK CAPTURE: fps <variant>/<name> <fps> (... frames) game <ms> render <ms> gpu <ms> (max <ms>)` measured over the
`--measure` seconds after a `--settle` wait at the spot (so teleport streaming is not in the number).
`python3 -I Scripts/PhotorealQA/rendering_table.py <capture.log>` turns those lines into a table.
Without --variant the set is captured once as variant `base`. The play camera is the game's: boom 400 cm, pitch -12,
looking north, from the walkable point nearest the screen centre (as visual_sweep.py). Commands of one variant stay set
for the next variants unless those set them back.
Reads ImportData/screens.json and Content/Dink/Data/Gameplay/Hardness (hardness picks the walkable points)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from visual_sweep import walkable_points  # noqa: E402

# name, screen, yaw, pitch, boom cm (the play camera unless a close-up)[, fixed map point]. Without a fixed point the
# point comes from the hardness (439's centre is inside the cottage and 471's centre point is refused: fixed points).
FRAMES = [
    ('01_house_interior', 1, -90, -12, 400),
    ('02_house_yard', 439, -90, -12, 400, (300, 385)),
    ('03_stonebrook_village', 406, -90, -12, 400),
    ('04_pond_yard', 471, -90, -12, 400, (215, 125)),
    ('05_river_fields', 381, -90, -12, 400),
    ('06_castle_moat', 404, -90, -12, 400),
    ('07_forest_murkwood', 397, -90, -12, 400),
    ('08_coast', 383, -90, -12, 400),
    ('09_terris', 466, -90, -12, 400),
    ('10_windemere', 534, -90, -12, 400),
    ('11_kernsin', 586, -90, -12, 400),
    ('12_goodheart_castle', 369, -90, -12, 400),
    ('13_darklands', 28, -90, -12, 400),
    ('14_dungeon', 579, -90, -12, 400),
    ('15_snowfield', 47, -90, -12, 400),
    ('16_castle_hall', 402, -90, -12, 400),
    ('17_dink_closeup', 439, 0, -4, 200, (300, 385)),
]


def main():
    argv = sys.argv[1:]
    out = os.path.abspath(argv[0]); os.makedirs(out, exist_ok=True)
    variants, only, settle, measure, res = [], None, 5.0, 3.0, '2560x1440'
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == '--variant': variants.append((argv[i + 1], [c.strip() for c in argv[i + 2].split(';') if c.strip()])); i += 3; continue
        if a == '--only': only = argv[i + 1].split(','); i += 2; continue
        if a == '--settle': settle = float(argv[i + 1]); i += 2; continue
        if a == '--measure': measure = float(argv[i + 1]); i += 2; continue
        if a == '--res': res = argv[i + 1]; i += 2; continue
        raise SystemExit('unknown argument %s' % a)
    variants = variants or [('base', [])]
    lines = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 30', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1',
             # -ResX/-ResY do not reach the offscreen game viewport (it stays 1280x720): set the size here
             'r.SetRes %sw' % res, 'wait 2',
             't.MaxFPS 0', 'r.VSync 0', 'dink.Fact lifemax 999', 'dink.Fact life 999',
             # the effective resolution settings go into the log
             'r.ScreenPercentage', 'r.ScreenPercentage.Default', 'r.ScreenPercentage.Default.Desktop.Mode', 'sg.ResolutionQuality',
             'sg.ShadowQuality', 'sg.GlobalIlluminationQuality', 'r.AntiAliasingMethod']
    for vname, cmds in variants:
        os.makedirs(os.path.join(out, vname), exist_ok=True)
        lines += ['# variant %s' % vname] + cmds
        for name, screen, yaw, pitch, boom, *fixed in FRAMES:
            if only and not any(o in name for o in only): continue
            pts = fixed or walkable_points(screen) or [(300, 230)]
            gotos = ['dink.Goto %d %d %d' % (screen, x, y) for x, y in reversed(pts)]
            lines += ['# %s' % name, 'dink.CalCam off'] + gotos + ['dink.CameraDistance %d' % boom, 'FOV %d' % (0 if boom >= 400 else 40),
                      'dink.View %d %d' % (yaw, pitch), 'wait %g' % settle, 'dink.Player', 'wait %g' % measure,
                      'fps %s/%s' % (vname, name), 'shot %s/%s/%s.png' % (out, vname, name)]
    lines += ['wait 1', 'quit']
    open(os.path.join(out, 'set.txt'), 'w').write('\n'.join(lines) + '\n')
    n = sum(1 for l in lines if l.startswith('shot '))
    print('%d variants, %d shots, about %.0f s -> %s' % (len(variants), n, 70 + n * (settle + measure + 1.5), os.path.join(out, 'set.txt')))


if __name__ == '__main__':
    main()
