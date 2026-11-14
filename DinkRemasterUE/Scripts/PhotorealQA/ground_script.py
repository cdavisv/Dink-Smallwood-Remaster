#!/usr/bin/env python3
"""Capture scripts for the screen-ground review:
    python3 -I Scripts/PhotorealQA/ground_script.py <out dir> [--screens=a,b,..] [--per-run=N]

Chooses the review screens from the data (see pick()) or takes --screens, and writes <out dir>/ground_<k>.txt for
run_capture.sh (one run holds at most --per-run screens, default 30: run_capture.sh stops a run after 1100 s) plus
<out dir>/ground_index.json (screen, why it was chosen, tile classes, layers, where the player stands). Per screen:
  NNN_play    the play camera (boom 400 cm, pitch -12, looking north) from the walkable point nearest the centre
  NNN_close   a camera 1.1 m above the ground at the same point, looking down at the ground 2.5 m ahead
  NNN_above   a fixed camera above the screen's south edge looking north over the whole screen
Reads ImportData/screens.json, tools/dinkex/out/screens, tools/data/tile_classes.csv, terrain_layers.json and the
hardness of Content/Dink/Data/Gameplay/Hardness. The scripts hold absolute paths: written for one run, not committed."""
import collections, csv, json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.dirname(ROOT)
RELIEF = ('cliff_face', 'rock_mass', 'cave_wall', 'chasm', 'forest_canopy', 'structure_facade', 'void')


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


def screen_table():
    """screen -> {kind, indoor, region, classes {tile class: tiles}, layers [names the importer uses], dropped {layer: tiles}}"""
    tiles = {int(r['tile_num']): r for r in csv.DictReader(open(os.path.join(DATA, 'tools/data/tile_classes.csv')))}
    cat = json.load(open(os.path.join(ROOT, 'SourceAssets/Art/PhotorealPass/Environment/terrain_layers.json')))
    table = {}
    for s in json.load(open(os.path.join(ROOT, 'ImportData/screens.json')))['screens']:
        scr = json.load(open(os.path.join(DATA, 'tools/dinkex/out/screens/SCR_%03d.json' % s['screen'])))
        cm = dict(cat['classes'])
        if s['indoor']: cm.update(cat.get('classes_indoor', {}))
        classes, layers = collections.Counter(), collections.Counter()
        for t in scr['tiles']:
            row = tiles.get(t['num']); terrain = row['terrain'] if row else '?'
            classes[terrain] += 1
            parts = [p for p in ((row or {}).get('blend_classes') or '').split('|') if p in cm]
            if row and row.get('is_transition') == '1' and len(parts) == 2 and cm[parts[0]] != cm[parts[1]]:
                layers[cm[parts[0]]] += 0.5; layers[cm[parts[1]]] += 0.5
            else:
                layers[cm.get(terrain, 'UNMAPPED')] += 1
        used = [l['name'] for l in s.get('ground_layers') or []]
        table[s['screen']] = {'kind': s['kind'], 'indoor': bool(s['indoor']), 'region': s['region'], 'classes': dict(classes), 'layer_tiles': dict(layers), 'layers': used,
                              'dropped': {l: v for l, v in layers.items() if l not in used}, 'water_rects': s['rect_counts'].get('fill_water', 0), 'corners': s['corners']}
    return table


def pick(table, per=3):
    """Review screens: per layer and per relief tile class the `per` screens with the largest share, one per region;
    every screen whose layer set is used by no other screen; the worst dropped-layer screens; water without a water
    surface; the known doubts."""
    why = collections.OrderedDict()
    def add(n, reason): why.setdefault(n, []).append(reason)
    def spread(key, label):
        ranked = [n for n in sorted(table, key=lambda n: (-key(table[n]), n)) if key(table[n]) > 0]
        seen, got = set(), []
        for n in ranked:      # one per region first, then the next largest wherever they are
            if len(got) < per and table[n]['region'] not in seen: seen.add(table[n]['region']); got.append(n)
        got += [n for n in ranked if n not in got][:per - len(got)]
        for n in got: add(n, label)
    for layer in sorted({l for o in table.values() for l in o['layers']}):
        spread(lambda o, layer=layer: o['layer_tiles'].get(layer, 0) if layer in o['layers'] else 0, 'layer ' + layer)
    for cls in RELIEF:
        spread(lambda o, cls=cls: o['classes'].get(cls, 0), 'tile class ' + cls)
    spread(lambda o: o['classes'].get('water', 0) if o['kind'] == 'sea' else 0, 'sea')
    spread(lambda o: o['classes'].get('water', 0) if o['kind'] != 'sea' and o['water_rects'] else 0, 'inland or shore water')
    spread(lambda o: o['classes'].get('water', 0) if not o['water_rects'] else 0, 'water tiles without a water surface')
    spread(lambda o: sum(o['dropped'].values()), 'a layer dropped by the three-layer limit')
    sets = collections.Counter(tuple(sorted(o['layers'])) for o in table.values())
    for n in sorted(table):
        if sets[tuple(sorted(table[n]['layers']))] == 1: add(n, 'layer set no other screen has')
    for n in (153, 257, 385): add(n, 'known doubt')
    return why


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = os.path.abspath(args[0]); os.makedirs(out, exist_ok=True)
    opt = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    table = screen_table()
    why = pick(table)
    if 'screens' in opt: why = collections.OrderedDict((int(x), why.get(int(x), ['asked for'])) for x in opt['screens'].split(','))
    per_run = int(opt.get('per-run', 30))

    def world(screen, x, y):
        c = table[screen]['corners']; u, v = x / 600.0, y / 400.0
        top = [c['nw'][i] + (c['ne'][i] - c['nw'][i]) * u for i in (0, 1)]
        bot = [c['sw'][i] + (c['se'][i] - c['sw'][i]) * u for i in (0, 1)]
        return [100.0 * (top[i] + (bot[i] - top[i]) * v) for i in (0, 1)]

    index, runs = [], []
    head = ['wait 22', 'dink.Goto 299 300 200', 'dink.View -90 -12', 'wait 40', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 'dink.Skip', 'wait 1', 't.MaxFPS 0', 'r.VSync 0']
    order = sorted(why)
    for k in range(0, len(order), per_run):
        lines = list(head)
        for screen in order[k:k + per_run]:
            hard = hardness(screen)
            free = lambda x, y: all(hard[yy][xx] == 0 for yy in range(max(0, y - 8), min(400, y + 9), 4) for xx in range(max(0, x - 8), min(600, x + 9), 4))
            spots = [(math.hypot(x - 300, y - 230), x, y) for y in range(30, 381, 10) for x in range(30, 571, 10) if free(x, y)]
            px, py = min(spots)[1:] if spots else (300, 230)
            me, ctr = world(screen, px, py), world(screen, 300, 200)
            half_h = (world(screen, 300, 400)[1] - world(screen, 300, 0)[1]) / 2.0
            dx, dy = ctr[0] - me[0], ctr[1] - me[1]
            shot = lambda kind: 'shot %s/%03d_%s.png' % (out, screen, kind)
            lines += ['dink.CalCam off', 'dink.Goto %d %d %d' % (screen, px, py), 'dink.CameraDistance 400', 'FOV 0', 'wait 1', 'dink.View -90 -12', 'wait 6', 'dink.Player', 'wait 1', shot('play'), 'wait 1',
                      'dink.CalAnchor', 'dink.CalCam 0 60 110 0 -250 0 60', 'wait 3', shot('close'), 'wait 1',
                      'dink.CalCam %.0f %.0f %.0f %.0f %.0f 0 75' % (dx, dy + half_h + 900, max(2200.0, half_h * 1.4), dx, dy - half_h * 0.15), 'wait 3', shot('above'), 'wait 1']
            o = table[screen]
            index.append({'screen': screen, 'why': why[screen], 'kind': o['kind'], 'indoor': o['indoor'], 'region': o['region'], 'classes': o['classes'], 'layers': o['layers'],
                          'dropped': o['dropped'], 'water_rects': o['water_rects'], 'player_px': [px, py], 'walkable': bool(spots)})
        lines += ['dink.CalCam off', 'wait 1', 'quit']
        name = os.path.join(out, 'ground_%d.txt' % (len(runs) + 1))
        open(name, 'w').write('\n'.join(lines) + '\n'); runs.append(name)
    json.dump(index, open(os.path.join(out, 'ground_index.json'), 'w'), indent=1)
    print('%d screens in %d runs -> %s' % (len(index), len(runs), out))
    reasons = collections.Counter(r for row in index for r in row['why'])
    for r, n in sorted(reasons.items()): print('  %-50s %d' % (r, n))


if __name__ == '__main__':
    main()
