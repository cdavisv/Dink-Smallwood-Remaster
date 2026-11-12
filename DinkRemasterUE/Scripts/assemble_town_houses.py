#!/usr/bin/env python3
"""Offline town-house assembler: python3 -I Scripts/assemble_town_houses.py

Reads ImportData/placements.json and writes Content/Dink/Data/Art/town_houses.json, which UDinkEnvironmentSubsystem
(dink.TownHouses) shows instead of the sprite cards of family 33. Visual only: hardness, warps and scripts are untouched.

What the sprites are: isometric (2:1) town houses. Wall frames 1-17 stand on a ground line that rises to the right
(slant A, face looking south-east), frames 18-46 on one that falls to the right (slant B, face south-west). A sprite
bay is 100 px of map x (128 px picture), about 11 m in the remaster's stretched world; a kit bay is 2.5 m. So:
  - consecutive wall sprites on one ground line are a RUN; each run is one house front;
  - each sprite bay becomes four kit bays (two for a 64 px corner piece), scaled along the wall to close the run exactly;
  - the door bay goes where the warp trigger is (else second bay of the door sprite); window and blank sprites
    give window and plain bays;
  - a back row turned 180 degrees, roof bays on both rows (one dormer per dormer sprite, Slope and Slope_B
    alternating), ridge caps, whole gable ends plus verges where the run ends inside the screen, a chimney on the
    upper end, corner quoins at the front corners;
  - the house is a true rectangle behind the wall line (the sprite's end wall is drawn at 53 degrees to the front
    in map space; a rectangle cannot follow both lines: the FRONT follows the hardness, the end wall deviates);
  - depth: 8.1 m per gable-end sprite found at the run's ends (5.51 m kit depth scaled, clamped 1.0-1.9);
  - every placement of the town classes on an assembled screen is hidden (roof columns, extra gable slices included).
Round 6 (12 Nov 2026): a run is no longer one terrace. It is cut into HOUSES of 2-4 kit bays (stable hash of screen,
run and house), each with its own eaves height (z scale 0.93-1.13), set-back from the hardness line (0-35 cm, never
forward), depth (x0.94-1.08), bay pattern (window left/right, plain, door where the warp is) and chimney; a full gable
wall of the taller house stands at every party wall (plus its verge when the ridges differ), a quoin at every step.
Houses next to a screen edge or a corner keep the neutral values so wings and neighbouring screens meet.
At a convex corner each wing also gets its gable wall and verge (hidden inside the other wing below its roof; above it
they close what would show as an open roof end); the bay that runs into any corner is plain.
Corners where two runs meet: both wings get the same depth; at a convex corner (the point toward the camera) walls run
0.29 m and roofs 0.48 m past the corner so jetties and eaves close; at a concave corner both roofs and back rows run
half a house depth past it, which closes the wedge between the wings with a true valley.
The JSON also lists `footprints` per screen (run origin px, yaw, rect_cm x0,y0,x1,y1 in the run frame): the grass
carpet stays out of them and wears short in front of them.
The JSON lists per house: slant, bays (sprite origin -> kit bays), door bay, roof modules, gable ends, depth scale,
then the flat module list the runtime instances (px = map pixel of the run's left end, offset_cm in world X east /
Y south / Z up, yaw in Unreal degrees, scale)."""
import json, math, os, collections, zlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A_WALL = {1, 2, 3, 5, 6, 11, 14, 15, 16, 17}
NARROW = {2, 11, 18, 19}
DOOR = {3, 5, 6, 21, 23, 33, 34, 38, 39}
BLANK = {17, 46, 36, 42}
GABLE_A, GABLE_B = {7, 10}, {24}
BAY, DEPTH, RIDGE_Y, RIDGE_Z = 250.0, 551.0, 275.5, 735.0
WALL_PAST, ROOF_PAST = 29.0, 48.0      # cm past a convex corner: jetty and eaves overhang x tan(26.6 deg)
ZS = (0.93, 1.0, 1.07, 1.13); SETBACK = (0.0, 18.0, 35.0); DSY = (0.94, 1.0, 1.08)
def H(*key): return zlib.crc32(':'.join(str(k) for k in key).encode())
def U(*key): return (H(*key) & 0xFFFFFF) / float(0x1000000)
placements = json.load(open(os.path.join(ROOT, 'ImportData/placements.json')))['placements']
by_screen = collections.defaultdict(list)
for p in placements:
    by_screen[p['screen']].append(p)
out = {'schema': 'dink-town-houses/2', 'generated_by': 'Scripts/assemble_town_houses.py', 'note': __doc__.split('\n\n')[1].replace('\n', ' '), 'screens': {}}
total = collections.Counter()
def centre(p):
    mpp = p['m_per_px']; c = p['card']
    return (p['map_x'] + c['offset_x_m'] / mpp, p['map_y'] - c['offset_z_m'] / mpp - 32.0)
for screen in sorted(by_screen):
    town = [p for p in by_screen[screen] if (p.get('class_id') or '').startswith('town_') and p['seq'] == 33]
    walls = [p for p in town if p['class_id'] in ('town_wall_stone_window', 'town_wall_stone_door')]
    if not walls:
        # roofs and gable slices of houses whose walls stand on the screen below: the 3D houses carry their own roofs
        if town:
            out['screens'][str(screen)] = {'houses': [{'id': f'S{screen}_roofs_only', 'note': 'no wall sprites on this screen: cards of houses assembled on the neighbouring screen', 'modules': [], 'hide': sorted(p['id'] for p in town)}]}
            total['hidden'] += len(town)
        continue
    warps = [p for p in by_screen[screen] if p.get('is_warp') and p.get('hardness')]
    runs = []
    for slant in 'AB':
        dy = -0.5 if slant == 'A' else 0.5
        bays = sorted((p for p in walls if (p['frame'] in A_WALL) == (slant == 'A')), key=lambda p: centre(p)[0])
        seen = set()     # the bundle lists some placements twice (a background and a live copy): one bay each
        bays = [p for p in bays if not ((round(centre(p)[0]), round(centre(p)[1])) in seen or seen.add((round(centre(p)[0]), round(centre(p)[1]))))]
        mine = []
        for p in bays:
            cx, cy = centre(p); half = 25.0 if p['frame'] in NARROW else 50.0
            for r in mine:
                ex, ey = r['end']
                if abs((cx - half) - ex) < 16 and abs((cy - half * dy) - ey) < 16:
                    r['bays'].append(p); r['end'] = (cx + half, cy + half * dy); break
            else:
                mine.append({'slant': slant, 'dy': dy, 'start': (cx - half, cy - half * dy), 'end': (cx + half, cy + half * dy), 'bays': [p]})
        runs += mine
    # geometry of each run in map pixels: unit direction, body normal (behind the wall), yaw
    for i, r in enumerate(runs):
        r['index'] = i
        r['yaw'] = math.degrees(math.atan2(r['dy'], 1.0))
        c, s = math.cos(math.radians(r['yaw'])), math.sin(math.radians(r['yaw']))
        r['dir'], r['normal'] = (c, s), (s, -c)
        r['cm'] = 100.0 * sum(p['m_per_px'] for p in r['bays']) / len(r['bays'])
        r['length'] = math.hypot(r['end'][0] - r['start'][0], r['end'][1] - r['start'][1]) * r['cm']
        gables = [p for p in town if p['class_id'] == 'town_wall_gable_end' and p['frame'] in (GABLE_A if r['slant'] == 'A' else GABLE_B)]
        near = lambda pt: sum(1 for g in gables if math.hypot(g['map_x'] - pt[0], g['map_y'] - pt[1]) < 260)
        r['ng'] = max(near(r['start']), near(r['end']), 1)
        r['sy'] = max(1.0, min(1.9, 810.0 * r['ng'] / DEPTH))
        r['join'] = {}
    # corners: which end of which run meets another run, and whether the corner is convex (the other wing's wall lies on my body side)
    parent = list(range(len(runs)))
    def find(i):
        while parent[i] != i: i = parent[i]
        return i
    for r in runs:
        for k in ('start', 'end'):
            for q in runs:
                if q is r: continue
                for k2 in ('start', 'end'):
                    if math.hypot(r[k][0] - q[k2][0], r[k][1] - q[k2][1]) < 30:
                        away = q['dir'] if k2 == 'start' else (-q['dir'][0], -q['dir'][1])
                        r['join'][k] = 'convex' if away[0] * r['normal'][0] + away[1] * r['normal'][1] > 0 else 'concave'
                        parent[find(r['index'])] = find(q['index'])
    for r in runs:      # wings of one building: one depth
        r['sy'] = max(q['sy'] for q in runs if find(q['index']) == find(r['index']))
    houses, footprints = [], []
    for r in runs:
        slant, yaw, length, sy0 = r['slant'], r['yaw'], r['length'], r['sy']
        (sx_, sy_), (ex, ey) = r['start'], r['end']
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        key = (screen, slant, round(sx_), round(sy_))
        # kit bays, left to right: what each sprite shows, varied by hash; the door bay stands where the warp trigger is
        kinds, review = [], []
        for p in r['bays']:
            n = 2 if p['frame'] in NARROW else 4
            window = 0.3 if p['frame'] in BLANK else 0.62
            k = []
            for j in range(n):
                u = U(p['id'], j, 'bay')
                k.append('SM_Town_Wall_Plain' if u > window else 'SM_Town_Wall_Window_L' if u < window * 0.5 else 'SM_Town_Wall_Window_R')
            if p['frame'] not in BLANK and all(x == 'SM_Town_Wall_Plain' for x in k): k[H(p['id'], 'w') % n] = 'SM_Town_Wall_Window_L'
            if p['frame'] in DOOR:
                i = 1
                if warps:
                    cx, cy = centre(p)
                    w = min(warps, key=lambda q: abs((q['hardness']['rect'][0] + q['hardness']['rect'][2]) / 2 - cx) + abs(q['hardness']['rect'][3] - cy))
                    wx = (w['hardness']['rect'][0] + w['hardness']['rect'][2]) / 2
                    if abs(wx - cx) < 70: i = max(0, min(n - 1, int((wx - (cx - 50.0)) / 25.0)))
                k[i] = 'SM_Town_Wall_Door'
            review.append({'origin': p['id'], 'frame': p['frame'], 'kit_bays': k})
            kinds += k
        # the bay that runs into a corner is plain: a window there is cut by the other wing's quoins
        if 'start' in r['join'] and kinds[0] != 'SM_Town_Wall_Door': kinds[0] = 'SM_Town_Wall_Plain'
        if 'end' in r['join'] and kinds[-1] != 'SM_Town_Wall_Door': kinds[-1] = 'SM_Town_Wall_Plain'
        n = len(kinds); sx = length / (n * BAY)
        inside = lambda pt, k: 25 < pt[0] < 575 and 25 < pt[1] < 395 and k not in r['join']
        end_kind = {k: r['join'].get(k) or ('gable' if inside(r[k], k) else 'edge') for k in ('start', 'end')}
        # cut the run into houses of 2-4 bays
        sizes, left = [], n
        while left > 0:
            size = 2 + H(*key, len(sizes), 'size') % 3
            if left - size == 1: size += 1 if size < 4 else -1
            size = min(size, left)
            if left <= 4 and left - size not in (0, 2, 3, 4): size = left
            sizes.append(size); left -= size
        mods = []
        def add(mesh, lx, ly, lz=0.0, rel=0.0, scale=(1, 1, 1)):
            mods.append({'mesh': mesh, 'px': [round(sx_, 2), round(sy_, 2)], 'offset_cm': [round(lx * c - ly * s, 1), round(lx * s + ly * c, 1), round(lz, 1)],
                         'yaw': round(yaw + rel, 2), 'scale': [round(v, 4) for v in scale]})
        dormers = sum(1 for p in town if p['class_id'] == 'town_roof_dormer' and ((p['frame'] in (13,)) == (slant == 'A')) and sx_ - 60 < p['map_x'] < ex + 60)
        dormer_at = set(sorted(range(n), key=lambda i: H(*key, i, 'dormer'))[:dormers])
        plan, first, prev = [], 0, None
        for hi_, size in enumerate(sizes):
            last = hi_ == len(sizes) - 1
            anchored = (hi_ == 0 and end_kind['start'] != 'gable') or (last and end_kind['end'] != 'gable')
            zi = H(*key, hi_, 'z') % len(ZS)
            if prev is not None and ZS[zi] == prev['zs']: zi = (zi + 1) % len(ZS)
            h = {'first': first, 'size': size, 'zs': 1.0 if anchored else ZS[zi], 'setback': 0.0 if anchored else SETBACK[H(*key, hi_, 'sb') % len(SETBACK)],
                 'sy': sy0 if anchored else sy0 * DSY[H(*key, hi_, 'd') % len(DSY)], 'x0': first * BAY * sx, 'x1': (first + size) * BAY * sx}
            plan.append(h); prev = h; first += size
        for hi_, h in enumerate(plan):
            last = hi_ == len(plan) - 1
            zs, sb, syh = h['zs'], h['setback'], h['sy']
            lo_kind = end_kind['start'] if hi_ == 0 else 'party'
            hi_kind = end_kind['end'] if last else 'party'
            past = lambda kind, convex, concave: convex if kind == 'convex' else concave if kind == 'concave' else 0.0
            # front wall row (a convex corner: a little past the corner, so the jetties of both wings close)
            w0, w1 = h['x0'] - past(lo_kind, WALL_PAST, 0.0), h['x1'] + past(hi_kind, WALL_PAST, 0.0)
            wsx = (w1 - w0) / (h['size'] * BAY)
            for j in range(h['size']):
                k = kinds[h['first'] + j]; x = w0 + j * BAY * wsx
                add(k, x, -sb, scale=(wsx, 1, zs))
                if k == 'SM_Town_Wall_Door': add('SM_Town_Door_Studded', x + 73.0 * wsx, 2.5 - sb, scale=(wsx, 1, zs))
            # roof rows and back row (a concave corner: half a depth past the corner, both wings: a valley)
            r0, r1 = h['x0'] - past(lo_kind, ROOF_PAST, 0.5 * DEPTH * syh), h['x1'] + past(hi_kind, ROOF_PAST, 0.5 * DEPTH * syh)
            nr = max(1, int(round((r1 - r0) / (BAY * sx)))); rsx = (r1 - r0) / (nr * BAY)
            roofs = []
            for j in range(nr):
                x = r0 + j * BAY * rsx
                bay = h['first'] + min(h['size'] - 1, max(0, int((x + 0.5 * BAY * rsx - h['x0']) / (BAY * sx))))
                v = H(*key, hi_, j, 'roof') % 2
                roof = 'SM_Town_Roof_Dormer' if bay in dormer_at and h['x0'] <= x + 0.5 * BAY * rsx <= h['x1'] and not any(m == 'SM_Town_Roof_Dormer' and b == bay for m, b in roofs) else ('SM_Town_Roof_Slope', 'SM_Town_Roof_Slope_B')[(j + v) % 2]
                roofs.append((roof, bay))
                add(roof, x, -sb, scale=(rsx, syh, zs))
                add(('SM_Town_Roof_Slope_B', 'SM_Town_Roof_Slope')[(j + v) % 2], x + BAY * rsx, -DEPTH * syh - sb, rel=180.0, scale=(rsx, syh, zs))
                add('SM_Town_Wall_Plain' if H(*key, hi_, j, 'back') % 3 else 'SM_Town_Wall_Window_L', x + BAY * rsx, -DEPTH * syh - sb, rel=180.0, scale=(rsx, 1, zs))
            caps = int(math.ceil((r1 - r0) / 150.0))
            for j in range(caps):
                add('SM_Town_Roof_RidgeCap', r0 + j * (r1 - r0) / caps, -RIDGE_Y * syh - sb, RIDGE_Z * zs, scale=((r1 - r0) / (caps * 150.0), 1, 1))
            # ends: a whole gable wall where the house ends in the open, at the screen edge (no verge: the neighbour screen
            # continues) and at a party wall when this house is the taller (or as tall and deeper) of the two
            def end(side, kind, other):
                x = h['x0'] if side == 'left' else h['x1']
                wall = kind in ('gable', 'edge', 'convex') or (kind == 'party' and (zs, syh, side == 'left') > (other['zs'], other['sy'], side != 'left'))
                verge = kind in ('gable', 'convex') or (kind == 'party' and wall and zs - other['zs'] > 0.03)
                quoin = kind in ('gable', 'convex') or (kind == 'party' and (sb < other['setback'] or (sb == other['setback'] and wall)))
                if side == 'left':
                    if wall: add('SM_Town_Wall_GableEnd', x, -DEPTH * syh - sb, rel=90.0, scale=(syh, 1, zs))
                    if verge: add('SM_Town_Roof_Verge', x, -DEPTH * syh - sb, rel=90.0, scale=(syh, 1, zs))
                    if quoin: add('SM_Town_Corner_Quoin', x, -sb, scale=(1, 1, zs))
                else:
                    if wall: add('SM_Town_Wall_GableEnd', x, -sb, rel=-90.0, scale=(syh, 1, zs))
                    if verge: add('SM_Town_Roof_Verge', x, -sb, rel=-90.0, scale=(syh, 1, zs))
                    if quoin: add('SM_Town_Corner_Quoin', x, -sb, rel=-90.0, scale=(1, 1, zs))
                return wall
            ends = []
            if end('left', lo_kind, plan[hi_ - 1] if hi_ else None): ends.append('left')
            if end('right', hi_kind, plan[hi_ + 1] if not last else None): ends.append('right')
            # one chimney per house, on the ridge just inside one end (an end with a wall of its own first)
            side = (ends or ['left', 'right'])[H(*key, hi_, 'chimney') % len(ends or [0, 1])]
            if lo_kind in ('convex', 'concave') and side == 'left': side = 'right'
            if hi_kind in ('convex', 'concave') and side == 'right': side = 'left'
            outside = 12.0 if (side == 'left' and lo_kind == 'gable') or (side == 'right' and hi_kind == 'gable') else -45.0
            if side == 'right': add('SM_Town_Chimney_Stack', h['x1'] + outside, -RIDGE_Y * syh - sb, rel=-90.0, scale=(1, 1, zs))
            else: add('SM_Town_Chimney_Stack', h['x0'] - outside, -RIDGE_Y * syh - sb, rel=90.0, scale=(1, 1, zs))
            h.update({'ends': ends, 'chimney': side, 'roofs': [m for m, _ in roofs], 'rect': [min(w0, r0), -DEPTH * syh - sb - 30.0, max(w1, r1), -sb + 30.0]})
            footprints.append({'px': [round(sx_, 2), round(sy_, 2)], 'yaw': round(yaw, 2), 'rect_cm': [round(v, 1) for v in h['rect']]})
        houses.append({'id': f'S{screen}_{slant}{len(houses) + 1}', 'slant': slant, 'yaw': round(yaw, 2), 'start_px': [round(sx_, 1), round(sy_, 1)], 'end_px': [round(ex, 1), round(ey, 1)],
                       'length_m': round(length / 100.0, 2), 'kit_bays': n, 'bay_scale': round(sx, 3), 'depth_scale': round(sy0, 3), 'gable_sprites_at_end': r['ng'], 'ends': end_kind,
                       'door_bays': [i for i, k in enumerate(kinds) if k == 'SM_Town_Wall_Door'], 'bays': review,
                       'houses': [{'bays': [h['first'], h['first'] + h['size'] - 1], 'length_m': round((h['x1'] - h['x0']) / 100.0, 2), 'z_scale': h['zs'], 'setback_cm': h['setback'], 'depth_m': round(DEPTH * h['sy'] / 100.0, 2),
                                   'gable_walls': h['ends'], 'chimney': h['chimney'], 'roof_bays_front': h['roofs']} for h in plan],
                       'modules': mods, 'hide': []})
        total['runs'] += 1; total['houses'] += len(plan); total['modules'] += len(mods)
    if houses:
        houses[0]['hide'] = sorted(p['id'] for p in town)   # every family 33 card of the screen (lowest roof sprite and the rest alike)
        total['hidden'] += len(town)
        out['screens'][str(screen)] = {'houses': houses, 'footprints': footprints}
dest = os.path.join(ROOT, 'Content/Dink/Data/Art/town_houses.json')
json.dump(out, open(dest, 'w'), indent=1)
print(f"town houses: {len(out['screens'])} screens, {total['runs']} runs cut into {total['houses']} houses, {total['modules']} modules, {total['hidden']} sprite cards hidden -> {dest}")
for s in ('506', '498', '418'):
    for r in out['screens'].get(s, {}).get('houses', []):
        print(' ', r['id'], r['slant'], r['start_px'], r['end_px'], r['length_m'], 'm', r['kit_bays'], 'bays x', r['bay_scale'], 'depth x', r['depth_scale'], 'doors', r['door_bays'], 'ends', r['ends'])
        for h in r.get('houses', []): print('     house bays', h['bays'], h['length_m'], 'm  z x', h['z_scale'], ' set back', h['setback_cm'], 'cm  depth', h['depth_m'], 'm  walls', h['gable_walls'], ' chimney', h['chimney'])
