#!/usr/bin/env python3
"""Offline assembler of structures that the 1997 game draws in several sprites: python3 -I Scripts/assemble_structures.py

Reads ImportData/placements.json and tools/dinkex/out/sequences.json (frame hotspots and hardboxes) and writes
Content/Dink/Data/Art/structure_sets.json in the schema of town_houses.json (dink-town-houses/3), which
UDinkEnvironmentSubsystem shows instead of the sprite cards (dink.TownHouses 0 keeps the cards). Visual only:
hardness, warps, scripts and origin IDs are untouched; a hidden card keeps its actor, its hardbox and its script.

Why not family rows: a family mesh stands at real size under the middle of its card. The remaster lays the outdoor
screens out at 2.75 to 4 times the sprite scale, so a fence sprite is 18 m of ground and a 4.4 m fence module in the
middle of it leaves gaps; a bridge deck would be a third as wide as the ground the player walks on. Here every
piece is laid along the ground line its sprite stands on and scaled along that line to close the run.

What is assembled (each rule names the sprite frames it reads):
  split-rail fence   93 lands/fence/fence-: frame 1 an east-west run, 4 a north-south run seen edge-on, 2 and 5 runs that
                     rise to the right, 3 and 6 runs that fall to the right. The ground line is the frame's hardbox (its
                     middle line, or its diagonal). SM_Fence_SplitRail_4m_PR every 4 m, scaled along the run.
  island fence       424 struct/island/isle- frames 7 (east-west) and 8 (north-south): SM_Island_Fence_Lattice_PR every 4.4 m.
  wooden bridge      58 struct/bridge/brdge-: frames 1-3 are deck pieces of a north-south bridge (the picture is the deck);
                     frames 6, 8, 10 are the far rail of an east-west bridge with the deck boards drawn under it and
                     7, 9, 11 its near rail. Deck modules fill the picture (north-south) or the ground between the
                     two rail lines (east-west); a rope rail stands on each rail line (the far side boarded).
  well               186 struct/landmark/landm- frames 1-3: SM_Well_Stone_PR with SM_Well_ShaftCap_PR (the shaft goes
                     below the ground, which is not cut: the cap closes it with an unlit black disc).
  thatched cottage   63 struct/home: frames 1 (long), 6 (large), 7 and 8 (small), 4 and 5 (two-storey), 10 (L-shaped). The
                     sprite is a house turned 45 degrees; its hardbox is an east-west rectangle. The house stands at real
                     size, square to the screen, its front (south) wall on the hardbox's south line. The door stands on
                     that wall where the warp door sprite (61, 62) or the door picture (63 frames 2, 3) is; the house
                     moves east or west so the door is on its wall. The warp trigger stays where it was, a few metres in
                     front of the wall. Door, chimney and window pictures on such a screen are hidden: the meshes carry
                     their own chimneys and windows.
  island hut         424 struct/island/isle- frames 1-3 (round) and 4-6 (two tiers): the hut at 1.25 x on the middle of its
                     picture, turned so that the doorway looks where the sprite's does (frames differ only in that).

Left to the family rows or to their cards: everything else. Screens and origins that an art manifest dresses
(Content/Dink/Data/Art, schema dink-art/1) are skipped, as the family layer skips them.

The JSON lists per screen `houses` (one per run or structure: id, kind, note, the placements it stands for in `hide`,
and `modules`: mesh package path, px = map pixel of the piece's middle, offset_cm, yaw in Unreal degrees, scale) and
`footprints` (the grass carpet stays out of bridge decks)."""
import collections
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
S = '/Game/Dink/Photoreal/Structures/'
FENCE, LATTICE = S + 'SM_Fence_SplitRail_4m_PR', S + 'SM_Island_Fence_Lattice_PR'
DECK, RAIL_ROPE, RAIL_PLANK = S + 'SM_Bridge_Wood_Deck_PR', S + 'SM_Bridge_Wood_Rail_Rope_PR', S + 'SM_Bridge_Wood_Rail_Plank_PR'
WELL, WELL_CAP = S + 'SM_Well_Stone_PR', S + 'SM_Well_ShaftCap_PR'
COTTAGE_DOOR = S + 'SM_Cottage_Door_PR'            # hinge pivot at x = 0, leaf 1.44 m along +X, face to the south
HUT_ROUND, HUT_TWO, HUT_SCALE = S + 'SM_Island_Hut_Round_PR', S + 'SM_Island_Hut_TwoStorey_PR', 1.25
# class -> (mesh, wall width east-west, wall depth, x of the doorway cut in the front wall or None when the wall is whole); metres
COTTAGE = {'cottage_thatched_small': (S + 'SM_Cottage_Thatched_Small_PR', 7.0, 5.5, None), 'cottage_thatched_large': (S + 'SM_Cottage_Thatched_Large_PR', 10.0, 6.5, None),
           'cottage_thatched_long': (S + 'SM_Cottage_Stonebrook_PR', 18.0, 9.0, 5.3), 'cottage_thatched_two_storey': (S + 'SM_Cottage_Thatched_TwoStorey_PR', 6.6, 6.0, None),
           'cottage_thatched_l_shape': (S + 'SM_Cottage_Thatched_LShape_PR', 9.3, 6.0, None)}
FENCE_PITCH, LATTICE_PITCH, DECK_LEN, DECK_WIDTH, RAIL_LEN = 4.0, 4.4, 2.5, 1.76, 2.5   # metres of run per module / deck width
SNAP_PX = 16.0    # fence ends closer than this (map pixels) are one corner

placements = json.load(open(os.path.join(ROOT, 'ImportData/placements.json')))['placements']
FRAMES = {(q['seq'], f['frame']): f for q in json.load(open(os.path.join(REPO, 'tools/dinkex/out/sequences.json')))['sequences'] for f in q['frames']}


def dressed():
    """screens and origins an art manifest handles (FDinkFamilyPrecedence::AddManifest)"""
    screens, origins = set(), set()
    art = os.path.join(ROOT, 'Content/Dink/Data/Art')
    for fn in sorted(os.listdir(art)):
        if not fn.endswith('.json'):
            continue
        try:
            d = json.load(open(os.path.join(art, fn)))
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get('schema') != 'dink-art/1':
            continue
        for field in ('replacements', 'warp_overrides'):
            origins.update(x['origin'] for x in d.get(field) or [] if isinstance(x, dict) and x.get('origin'))
        origins.update(o for o in d.get('hide_origins') or [] if isinstance(o, str))
        hv = d.get('hide_origins_by_vision')
        for lst in (hv.values() if isinstance(hv, dict) else [hv] if isinstance(hv, list) else []):
            origins.update(o for o in lst or [] if isinstance(o, str))
        for field in ('hide_screen_visuals', 'authored_collision_screens'):
            screens.update(int(x) for x in d.get(field) or [] if isinstance(x, (int, float)))
        if d.get('elements') and isinstance(d.get('screen'), (int, float)):
            screens.add(int(d['screen']))
    return screens, origins


SKIP_SCREENS, SKIP_ORIGINS = dressed()
by_screen = collections.defaultdict(list)
for p in placements:
    if p['screen'] not in SKIP_SCREENS and p['id'] not in SKIP_ORIGINS and p.get('vision', 0) == 0:
        by_screen[p['screen']].append(p)


def unique(ps):
    """the bundle lists some placements twice (a background and a live copy at the same point, sometimes a pixel apart): one piece for both"""
    out = []
    for p in ps:
        twin = next((q for q in out if q['seq'] == p['seq'] and q['frame'] == p['frame'] and abs(q['map_x'] - p['map_x']) <= 2 and abs(q['map_y'] - p['map_y']) <= 2), None)
        if twin:
            twin['_also'].append(p['id'])
        else:
            out.append(dict(p, _also=[]))
    return out


def run_modules(mesh, a, b, mpp, pitch, yaw_add=0.0, z=0.0, scale_y=1.0):
    """modules of `pitch` metres along the ground line a -> b (map pixels), scaled along their own X to close it"""
    dx, dy = (b[0] - a[0]) * mpp[0], (b[1] - a[1]) * mpp[1]
    length = math.hypot(dx, dy)
    if length < 0.3:
        return [], 0.0
    n = max(1, int(round(length / pitch)))
    yaw = math.degrees(math.atan2(dy, dx))
    mods = []
    for i in range(n):
        t = (i + 0.5) / n
        mods.append({'mesh': mesh, 'px': [round(a[0] + (b[0] - a[0]) * t, 2), round(a[1] + (b[1] - a[1]) * t, 2)], 'offset_cm': [0.0, 0.0, round(z, 1)],
                     'yaw': round(yaw + yaw_add, 2), 'scale': [round(length / (n * pitch), 4), round(scale_y, 4), 1.0]})
    return mods, length


def ground_line(p, kind):
    """the ground line of a fence sprite from its hardbox: 'ew' the middle line, 'ns' the middle column, 'rise' / 'fall' a diagonal"""
    hb = FRAMES[(p['seq'], p['frame'])]['hardbox']; x, y = p['map_x'], p['map_y']
    if kind == 'ew':
        m = (hb['top'] + hb['bottom']) / 2.0
        return (x + hb['left'], y + m), (x + hb['right'], y + m)
    if kind == 'ns':
        m = (hb['left'] + hb['right']) / 2.0
        return (x + m, y + hb['top']), (x + m, y + hb['bottom'])
    if kind == 'rise':
        return (x + hb['left'], y + hb['bottom']), (x + hb['right'], y + hb['top'])
    return (x + hb['left'], y + hb['top']), (x + hb['right'], y + hb['bottom'])


def picture(p):
    """map-pixel rectangle (x0, y0, x1, y1) the sprite's picture covers"""
    f = FRAMES[(p['seq'], p['frame'])]; k = p.get('size_percent', 100) / 100.0
    x0, y0 = p['map_x'] - f['origin']['x'] * k, p['map_y'] - f['origin']['y'] * k
    return x0, y0, x0 + f['width'] * k, y0 + f['height'] * k


FENCE_KIND = {1: 'ew', 4: 'ns', 2: 'rise', 5: 'rise', 3: 'fall', 6: 'fall'}
out = {'schema': 'dink-town-houses/3', 'generated_by': 'Scripts/assemble_structures.py',
       'note': 'Structures the 1997 game draws in several sprites, laid along their ground lines: split-rail and island fences, wooden bridges, wells. '
               'Reads ImportData/placements.json and tools/dinkex/out/sequences.json; shown by UDinkEnvironmentSubsystem beside town_houses.json (dink.TownHouses). '
               'Visual only: hardness, warps and scripts are untouched.', 'screens': {}}
total = collections.Counter()
for screen in sorted(by_screen):
    ps = by_screen[screen]; sets = []; footprints = []

    def emit(kind, pieces, mods, note, **extra):
        ids = sorted({i for p in pieces for i in [p['id']] + p.get('_also', [])})
        sets.append(dict({'id': 'S%d_%s%d' % (screen, kind, len(sets) + 1), 'kind': kind, 'note': note, 'modules': mods, 'hide': ids}, **extra))
        total[kind] += 1; total['modules'] += len(mods); total['hidden'] += len(ids)

    # ---- fences: one set per sprite, so a run reads in the JSON as the sprites it came from
    for cls_prefix, seq, mesh, pitch, kinds in (('fence_rail_', 93, FENCE, FENCE_PITCH, FENCE_KIND), ('island_fence_lattice', 424, LATTICE, LATTICE_PITCH, {7: 'ew', 8: 'ns'})):
        pieces = unique([q for q in ps if q['seq'] == seq and (q.get('class_id') or '').startswith(cls_prefix) and q['frame'] in kinds])
        lines = [list(ground_line(p, kinds[p['frame']])) for p in pieces]
        # the hardboxes of neighbouring sprites end a few pixels apart: ends within SNAP_PX of each other become one point, so a run has no gaps or steps
        ends = [(i, j) for i in range(len(lines)) for j in (0, 1)]; done = set()
        for e in ends:
            if e in done:
                continue
            group = [f for f in ends if f not in done and math.hypot(lines[f[0]][f[1]][0] - lines[e[0]][e[1]][0], lines[f[0]][f[1]][1] - lines[e[0]][e[1]][1]) <= SNAP_PX]
            if len(group) > 1 and len({f[0] for f in group}) > 1:
                m = (sum(lines[f[0]][f[1]][0] for f in group) / len(group), sum(lines[f[0]][f[1]][1] for f in group) / len(group))
                for f in group:
                    lines[f[0]][f[1]] = m
            done.update(group)
        for p, (a, b) in zip(pieces, lines):
            mods, length = run_modules(mesh, a, b, (p['scale_x'], p['scale_y']), pitch)
            if mods:
                emit('fence' if seq == 93 else 'lattice', [p], mods, '%s frame %d: %.1f m of ground, %d modules' % (p['class_id'], p['frame'], length, len(mods)), length_m=round(length, 2))

    # ---- wooden bridges
    decks = unique([q for q in ps if q['seq'] == 58 and q['frame'] in (1, 2, 3)])
    for p in decks:                                    # north-south bridge: the picture is the deck
        x0, y0, x1, y1 = picture(p); cx = (x0 + x1) / 2.0
        width = (x1 - x0) * p['scale_x'] * 0.86        # the picture's side beams are part of its width
        mods, length = run_modules(DECK, (cx, y0), (cx, y1), (p['scale_x'], p['scale_y']), DECK_LEN, scale_y=width / DECK_WIDTH)
        emit('deck', [p], mods, 'bridge_wood_deck frame %d: %.1f m long, %.1f m wide' % (p['frame'], length, width), length_m=round(length, 2), width_m=round(width, 2))
        footprints.append({'px': [round(cx, 2), round((y0 + y1) / 2.0, 2)], 'yaw': 0.0,
                           'rect_cm': [round(-50.0 * width - 30.0, 1), round(-50.0 * length - 30.0, 1), round(50.0 * width + 30.0, 1), round(50.0 * length + 30.0, 1)]})
    far = unique([q for q in ps if q['seq'] == 58 and q['frame'] in (6, 8, 10)])
    near = unique([q for q in ps if q['seq'] == 58 and q['frame'] in (7, 9, 11)])
    if far and near:                                   # east-west bridge: the deck lies between the two rail lines
        yf = sum(p['map_y'] for p in far) / len(far); yn = sum(p['map_y'] for p in near) / len(near)
        x0 = min(picture(p)[0] for p in far + near); x1 = max(picture(p)[2] for p in far + near)
        mpp = (far[0]['scale_x'], far[0]['scale_y'])
        width = (yn - yf) * mpp[1]
        deck, length = run_modules(DECK, (x0, (yf + yn) / 2.0), (x1, (yf + yn) / 2.0), mpp, DECK_LEN, scale_y=width / DECK_WIDTH)
        rails = run_modules(RAIL_PLANK, (x0, yf), (x1, yf), mpp, RAIL_LEN)[0] + run_modules(RAIL_ROPE, (x0, yn), (x1, yn), mpp, RAIL_LEN, yaw_add=180.0)[0]
        emit('bridge', far + near, deck + rails, 'east-west wooden bridge: %.1f m long, %.1f m between the rail lines, %d deck and %d rail modules' % (length, width, len(deck), len(rails)),
             length_m=round(length, 2), width_m=round(width, 2))
        footprints.append({'px': [round((x0 + x1) / 2.0, 2), round((yf + yn) / 2.0, 2)], 'yaw': 0.0,
                           'rect_cm': [round(-50.0 * length - 30.0, 1), round(-50.0 * width - 60.0, 1), round(50.0 * length + 30.0, 1), round(50.0 * width + 60.0, 1)]})
    elif far or near:
        total['bridge_rails_without_pair'] += len(far) + len(near)

    # ---- wells
    for p in unique([q for q in ps if q.get('class_id') == 'well_stone']):
        hb = FRAMES[(p['seq'], p['frame'])]['hardbox']
        at = [round(p['map_x'] + (hb['left'] + hb['right']) / 2.0, 2), round(p['map_y'] + (hb['top'] + hb['bottom']) / 2.0, 2)]
        emit('well', [p], [{'mesh': m, 'px': at, 'offset_cm': [0.0, 0.0, 0.0], 'yaw': 0.0, 'scale': [1.0, 1.0, 1.0]} for m in (WELL, WELL_CAP)],
             'well_stone frame %d at the middle of its hardbox, with the shaft cap' % p['frame'])
        footprints.append({'px': at, 'yaw': 0.0, 'rect_cm': [-150.0, -110.0, 150.0, 110.0]})

    # ---- thatched cottages: the house at real size on its hardbox, front wall on the hardbox's south line, a door on that wall where the warp door is
    cottages = unique([q for q in ps if (q.get('class_id') or '').startswith('cottage_thatched')])
    doors = [q for q in ps if q.get('class_id') in ('door_wood_single', 'door_wood_wide', 'cottage_door')]
    used_doors = []
    for p in cottages:
        mesh, W, D, opening = COTTAGE[p['class_id']]
        hb = FRAMES[(p['seq'], p['frame'])]['hardbox']; sx, sy = p['scale_x'], p['scale_y']
        hx, hy = p['map_x'] + (hb['left'] + hb['right']) / 2.0, p['map_y'] + (hb['top'] + hb['bottom']) / 2.0
        south = p['map_y'] + hb['bottom']
        # the door: the warp sprite (61 / 62) first, else the door picture (63 frames 2, 3), within reach of this house's front
        near = sorted((q for q in doors if p['map_x'] + hb['left'] - 45 <= q['map_x'] <= p['map_x'] + hb['right'] + 45 and p['map_y'] + hb['top'] <= q['map_y'] <= south + 75),
                      key=lambda q: (not q['class_id'].startswith('door_wood'), abs(q['map_y'] - south) + 0.3 * abs(q['map_x'] - hx)))
        door = near[0] if near else None
        # The remaster lays these screens out at about four times the sprite scale, so the hardbox (and the door's place on it) is far
        # wider than a real cottage. The house is stretched along its front, at most 1.6 times, toward the hardbox width; a house with a
        # doorway cut in its wall is not stretched. Then it moves east or west only as far as it must for the door to be on its wall.
        scale_x = 1.0 if opening is not None else max(1.0, min(1.6, (hb['right'] - hb['left']) * sx / W))
        half = W * scale_x / 2.0 - 0.9
        cx = 0.0; local = None                         # cx: metres east of the hardbox centre; local: door middle on the wall, from the house middle
        if door:
            d = (door['map_x'] - hx) * sx
            if opening is not None:
                local = opening; cx = d - local
            else:
                # the visible door may stand anywhere over the warp trigger (the door sprite's hardbox), which lets the house stay nearer its hardbox
                dh = FRAMES[(door['seq'], door['frame'])]['hardbox'] if door['class_id'].startswith('door_wood') else {'left': 0, 'right': 0}
                lo, hi = d + dh['left'] * sx + 0.5, d + dh['right'] * sx - 0.5
                lo, hi = (lo, hi) if lo <= hi else (d, d)
                target = max(lo, min(hi, max(-half, min(half, d))))
                local = max(-half, min(half, target)); cx = target - local
        cy = (south - hy) * sy + 0.10 - D / 2.0         # the front wall stands 10 cm south of the hardbox line
        mods = [{'mesh': mesh, 'px': [round(hx, 2), round(hy, 2)], 'offset_cm': [round(100 * cx, 1), round(100 * cy, 1), 0.0], 'yaw': 0.0, 'scale': [round(scale_x, 4), 1.0, 1.0]}]
        hide = [p]
        if door:
            front = D / 2.0
            if p['class_id'] == 'cottage_thatched_l_shape':   # the wing stands forward of the two-storey block: the door goes on the face in front of it
                front = 5.7 if local > 0.1 else 1.6
            leaf_x, leaf_y = (opening - 0.72, front - 0.2) if opening is not None else (local - 0.72, front + 0.06)
            mods.append({'mesh': COTTAGE_DOOR, 'px': [round(hx, 2), round(hy, 2)], 'offset_cm': [round(100 * (cx + leaf_x), 1), round(100 * (cy + leaf_y), 1), 0.0], 'yaw': 0.0, 'scale': [1.0, 1.0, 1.0]})
            used_doors += [q for q in doors if abs(q['map_x'] - door['map_x']) <= 40 and abs(q['map_y'] - door['map_y']) <= 40]
        emit('cottage', hide, mods, '%s frame %d: %s, front x %.2f, %.1f m %s of its hardbox middle%s' % (p['class_id'], p['frame'], mesh.split('/')[-1], scale_x, abs(cx), 'east' if cx >= 0 else 'west',
             ', door at %s' % door['id'] if door else ', no door sprite in reach'), door=door['id'] if door else None)
        footprints.append({'px': [round(hx, 2), round(hy, 2)], 'yaw': 0.0, 'rect_cm': [round(100 * (cx - W * scale_x / 2) - 60, 1), round(100 * (cy - D / 2) - 60, 1), round(100 * (cx + W * scale_x / 2) + 60, 1), round(100 * (cy + D / 2) + 160, 1)]})
    if cottages:
        # what the sprites draw on the houses and the meshes carry themselves: door pictures and warp door cards, chimneys, window pictures
        extra = [q for q in ps if q.get('class_id') in ('chimney_stone', 'cottage_door', 'log_cabin_window') or q in used_doors]
        if extra:
            emit('cottage_parts', unique(extra), [], 'door, chimney and window sprites of the cottages on this screen: the houses carry their own')

    # ---- island huts: the hut at HUT_SCALE on the middle of its picture, turned so that its doorway looks where the sprite's does
    for p in unique([q for q in ps if q.get('class_id') in ('island_hut_round', 'island_hut_two_storey')]):
        x0, y0, x1, y1 = picture(p)
        mesh = HUT_ROUND if p['class_id'] == 'island_hut_round' else HUT_TWO
        yaw = {1: 35.0, 2: 0.0, 3: -35.0, 4: 35.0, 5: 0.0, 6: -35.0}[p['frame']]
        at = [round((x0 + x1) / 2.0, 2), round(p['map_y'] - 14.0, 2)]
        emit('hut', [p], [{'mesh': mesh, 'px': at, 'offset_cm': [0.0, 0.0, 0.0], 'yaw': yaw, 'scale': [HUT_SCALE] * 3}], '%s frame %d, doorway yaw %g' % (p['class_id'], p['frame'], yaw))
        footprints.append({'px': at, 'yaw': 0.0, 'rect_cm': [-420.0, -420.0, 420.0, 520.0]})

    if sets:
        out['screens'][str(screen)] = {'houses': sets, 'footprints': footprints,
                                       'stands_for': {o: h['id'] for h in sets for o in h['hide']}}

dest = os.path.join(ROOT, 'Content/Dink/Data/Art/structure_sets.json')
json.dump(out, open(dest, 'w'), indent=1)
print('structures: %d screens; %s; skipped %d dressed screens -> %s' % (len(out['screens']), ', '.join('%s %d' % kv for kv in sorted(total.items())), len(SKIP_SCREENS), os.path.relpath(dest, ROOT)))
