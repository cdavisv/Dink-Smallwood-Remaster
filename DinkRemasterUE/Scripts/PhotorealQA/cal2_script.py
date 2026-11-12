#!/usr/bin/env python3
"""cal2_script.py <outdir> <tag> [--only a,b] [--pre 'cmd;cmd'] [--var name='cmd;cmd' ...] -> capture script for the
non-foliage calibration pairs: the Blender review assemblies of Structures/tools/sb_final_asm.json, sb_boulders.json and
TownExteriors/tools/review_asm.json rebuilt in the engine on the empty meadow screen 299 with the review sun (Nishita,
elevation 40, sun_rotation -150 = light travelling toward Blender (+0.5, +0.866) = Unreal yaw 30). Reference frames are
1300 x 850: the engine frame is 16:9 with the same vertical field of view, compared on its central 1300:850 crop."""
import sys, math, json, os
out, tag = sys.argv[1], sys.argv[2]
arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
pre = [c.strip() for c in (arg('--pre') or '').split(';') if c.strip()]
only = arg('--only').split(',') if arg('--only') else None
variants = [(a.split('=', 1)[0], [c.strip() for c in a.split('=', 1)[1].split(';') if c.strip()]) for i, a in enumerate(sys.argv) if i > 0 and sys.argv[i - 1] == '--var'] or [('', [])]
PP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../SourceAssets/Art/PhotorealPass'))
def fov(lens): return round(2 * math.degrees(math.atan(18.0 / lens * (850.0 / 1300.0) * (16.0 / 9.0))), 2)
def cam(c): l, t = c['loc'], c['tgt']; return 'dink.CalCam %d %d %d %d %d %d %s' % (l[1] * 100, l[0] * 100, l[2] * 100, t[1] * 100, t[0] * 100, t[2] * 100, fov(c.get('lens', 32)))
def item(folder, it): n, x, y, z, yaw = it; return f'dink.CalSpawn /Game/Dink/Photoreal/{folder}/{n}.{n} {y * 100:.1f} {x * 100:.1f} {z * 100:.1f} {90 - yaw:.0f} 1'
SHOTS = {}
def add(spec, folder, prefix, names=None):
    for a in json.load(open(os.path.join(PP, spec)))['assemblies']:
        for c in a['cams']:
            SHOTS[f"{prefix}{a['name']}_{c['name']}"] = ([item(folder, it) for it in a['items']], c)
add('Structures/tools/sb_final_asm.json', 'Structures', '')
try: add('Structures/tools/sb_boulders.json', 'Structures', '')
except Exception: pass
add('TownExteriors/tools/review_asm.json', 'TownExteriors', '')
if '--list' in sys.argv: print('\n'.join(SHOTS)); sys.exit(0)
L = ['wait 22', 'dink.Goto 471 215 125', 'dink.View 10 5', 'wait 40', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 't.MaxFPS 0', 'r.VSync 0', 'dink.Goto 299 300 200', 'wait 3', 'dink.Player',
     'dink.EnvPost sunyaw 30', 'dink.EnvPost sunpitch -40', 'dink.Wind 0', 'dink.GrassDensity 0']
last = None
for name, (items, c) in SHOTS.items():
    if only and name not in only: continue
    if items != last: L += ['dink.CalAnchor 0 0'] + items; last = items
    L += [cam(c), 'wait 2'] + pre
    for vname, cmds in variants:
        L += cmds + ['wait 6', f"shot {out}/{tag}_{name}{'_' + vname if vname else ''}.png", 'wait 1']
L += ['quit']
print('\n'.join(L))
