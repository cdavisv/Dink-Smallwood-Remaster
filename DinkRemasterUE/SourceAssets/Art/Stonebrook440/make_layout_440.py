"""Draft SCR_440 placement layout (original screen pixels) + runtime-manifest draft + checks.

    python3 make_layout_440.py          # host Python 3 (numpy, Pillow); run after build_440.py

Reads art_manifest.json (this directory), ImportData/screens.json + placements.json and the original
hardness PNG from tools/dinkex/out.  Writes layout_440.json (schema dink-art/1, like
StonebrookExterior/exterior_layout.json), runtime_manifest_440_draft.json (world_cm/offset_cm the
existing importer would publish) and layout_checks_440.json.  Nothing outside this directory is written.

Coordinates: source_pixel = original map pixel (map_x = screen x - 20, y), world = bilinear blend of the
screen corners (metres, x east, y south), as in Scripts/import_stonebrook_art.py.  Unreal rotators are
[pitch, yaw, roll] degrees.  Imported meshes have Unreal local Y = -Blender Y.
"""
import json, math, random
from pathlib import Path
import numpy as np
from PIL import Image

ART = Path(__file__).resolve().parent
UE = ART.parents[2]; REPO = UE.parent
SCREEN = 440
man = json.loads((ART / 'art_manifest.json').read_text())
screens = {s['screen']: s for s in json.loads((UE / 'ImportData/screens.json').read_text())['screens']}
placements = {p['id']: p for p in json.loads((UE / 'ImportData/placements.json').read_text())['placements']}
rnd = random.Random(440)


def corners(scr):
    c = screens[scr]['corners']; return [np.array(c[k]) for k in ('nw', 'ne', 'se', 'sw')]


def world(px, py, scr=SCREEN):
    nw, ne, se, sw = corners(scr); u, v = px / 600, py / 400
    return nw * (1 - u) * (1 - v) + ne * u * (1 - v) + se * u * v + sw * (1 - u) * v


def pixel(w, scr=SCREEN):
    p = np.array([300., 200.])
    for _ in range(10):
        f = world(*p, scr); J = np.column_stack((world(p[0] + 1, p[1], scr) - f, world(p[0], p[1] + 1, scr) - f))
        p -= np.linalg.solve(J, f - np.asarray(w))
    return [round(float(p[0]), 3), round(float(p[1]), 3)]


# ----------------------------------------------------------------------------- Unreal rotation helpers
def rot_matrix(pitch, yaw, roll):
    """FRotationMatrix rows = transformed X, Y, Z axes (row-vector convention, v' = v @ M)."""
    P, Y, R = map(math.radians, (pitch, yaw, roll))
    SP, CP, SY, CY, SR, CR = math.sin(P), math.cos(P), math.sin(Y), math.cos(Y), math.sin(R), math.cos(R)
    return np.array([[CP * CY, CP * SY, SP],
                     [SR * SP * CY - CR * SY, SR * SP * SY + CR * CY, -SR * CP],
                     [-(CR * SP * CY + SR * SY), CY * SR - CR * SP * SY, CR * CP]])


def matrix_to_rotator(M):
    X, Yax, Z = M
    pitch = math.degrees(math.atan2(X[2], math.hypot(X[0], X[1])))
    yaw = math.degrees(math.atan2(X[1], X[0]))
    SY = rot_matrix(pitch, yaw, 0)[1]
    roll = math.degrees(math.atan2(np.dot(Z, SY), np.dot(Yax, SY)))
    return [round(pitch, 4), round(yaw, 4), round(roll, 4)]


def ue_corners(name):
    a = man['assets'][name]; mn, mx = a['bounds_min_m'], a['bounds_max_m']
    pts = np.array([[x, y, z] for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])])
    pts[:, 1] *= -1                       # FBX import mirrors Blender Y
    return pts


LEAN_REPORT = []


def lean(name, base_world_xy, wall_x_fn, spin_deg, tilt_deg):
    """Lean a tool, modelled upright, against the east wall.  Real contact test: every convex-hull vertex
    of the tool's LOD0 (art_manifest hull_points_m) is transformed with the Unreal rotator and the tool
    is slid west until its first vertex touches the measured displaced stone surface wall_x_fn(y, z)."""
    Rz = rot_matrix(0, spin_deg, 0); Ry = rot_matrix(tilt_deg, 0, 0)
    M = Rz @ Ry                            # spin about the tool's own vertical, then tilt about world Y
    rot = matrix_to_rotator(M)
    assert np.allclose(rot_matrix(*rot), M, atol=1e-6)
    pts = np.array(man['assets'][name]['hull_points_m'], float); pts[:, 1] *= -1     # FBX Y mirror
    c = pts @ M
    z = -c[:, 2].min()
    Y = base_world_xy[1] + c[:, 1]; Z = c[:, 2] + z
    walls = np.array([wall_x_fn(y, zz) for y, zz in zip(Y, Z)])
    x = float(np.max(walls - c[:, 0]))
    gaps = c[:, 0] + x - walls
    LEAN_REPORT.append({'mesh': name, 'tilt_deg': tilt_deg, 'spin_deg': spin_deg, 'hull_points': len(pts),
                        'min_gap_cm': round(float(gaps.min()) * 100, 3), 'points_within_5mm': int((gaps < .005).sum()),
                        'contact_height_m': round(float(Z[np.argmin(gaps)]), 3), 'foot_to_wall_m': round(float(x + c[np.argmin(c[:, 2]), 0] - walls.min()), 3)})
    return [x, base_world_xy[1]], z, rot


# ----------------------------------------------------------------------------- layout
layout = {'schema': 'dink-art/1', 'screen': SCREEN, 'draft': True,
          'hide_screen_visuals': [SCREEN], 'hide_origins': [], 'authored_collision_screens': [SCREEN],
          'asset_paths': {}, 'replacements': [], 'elements': [], 'lights': [], 'warp_overrides': []}
reuse = {'SM_Barrel_Oak_01': '/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01',
         'SM_Ground_Meadow_20m_01': '/Game/Dink/Kits/StonebrookExterior/SM_Ground_Meadow_20m_01',
         'SM_Fence_SplitRail_4m_01': '/Game/Dink/Kits/StonebrookExterior/SM_Fence_SplitRail_4m_01',
         'SM_Oak_Stonebrook_01': '/Game/Dink/Kits/StonebrookExterior/SM_Oak_Stonebrook_01',
         'SM_Boulder_Fieldstone_01': '/Game/Dink/Kits/StonebrookExterior/SM_Boulder_Fieldstone_01',
         'SM_Grass_Meadow_01': '/Game/Dink/Kits/StonebrookExterior/SM_Grass_Meadow_01'}
layout['asset_paths'].update(reuse)
for n, a in man['assets'].items():
    layout['asset_paths'][n] = a['ue_path']


def element(name, mesh, px, py, z_cm=0.0, rot=(0, 0, 0), scale=(1, 1, 1), collision=True, note=None):
    e = {'name': name, 'mesh': mesh, 'source_pixel': [round(px, 3), round(py, 3)], 'height_cm': round(z_cm, 2),
         'rotation_deg': [round(r, 4) for r in rot], 'scale': list(scale), 'collision': collision}
    if note:
        e['note'] = note
    layout['elements'].append(e)


def replacement(origin, mesh, px, py, z_cm=0.0, rot=(0, 0, 0), note=None):
    r = {'origin': origin, 'mesh': mesh, 'source_pixel': [round(px, 3), round(py, 3)], 'height_cm': round(z_cm, 2),
         'rotation_deg': [round(v, 4) for v in rot], 'scale': [1, 1, 1]}
    if note:
        r['note'] = note
    layout['replacements'].append(r)


# meadow ground tiles over the screen AABB (identical recipe to screen 439)
cs = corners(SCREEN); mn = np.min(cs, 0) - .02; mx = np.max(cs, 0) + .02
tw, td = (mx[0] - mn[0]) / 3, (mx[1] - mn[1]) / 2
for row in range(2):
    for col in range(3):
        px, py = pixel([mn[0] + (col + .5) * tw, mn[1] + (row + .5) * td])
        element('Meadow_%d_%d' % (col, row), 'SM_Ground_Meadow_20m_01', px, py, -9.8, scale=(tw / 20, td / 20, 1))

# --- house: the door's outer face centre sits on the original warp trigger (S440_P06 hard box [295,263,330,293])
H = man['assets']['SM_House_Stonebrook_TwoStorey_01']; hinfo = H['house']
door_b = hinfo['door_local_m']                         # Blender local, pivot = footprint centre
door_ue = np.array([door_b[0], -door_b[1]])            # Unreal local (front = +Y = south)
door_target_px = (312.5, 290.0)
door_world = world(*door_target_px)
house_world = door_world - door_ue
house_px = pixel(house_world)
element('House440', 'SM_House_Stonebrook_TwoStorey_01', house_px[0], house_px[1], -3.0,
        note='taller two-storey house (home-04, S440_P03/P11); sunk 3 cm into the meadow; door on the original trigger')
layout['warp_overrides'].append({'origin': 'S440_P06', 'source_pixel': list(door_target_px), 'height_cm': 150, 'extent_cm': [65, 35, 150],
                                 'note': 'centred on the door face: half in the 46 cm recess, half outside (same extent as S439_P13)'})
W1, D1 = hinfo['footprint_m']
shift = hinfo.get('pivot_shift_m', [0, 0, 0]); rel = hinfo['east_wall_relief']; relg = np.array(rel['max_outward_m'])
def east_wall_x(Y, Z):
    """World x of the displaced east-wall stone surface at world (Y, Z): measured skin relief grid."""
    y_b = -(Y - house_world[1]) + shift[1]; z_b = Z + .03 + shift[2]
    iy = int(np.clip((y_b - rel['y0']) / rel['cell'], 0, relg.shape[0] - 1)); iz = int(np.clip(z_b / rel['cell'], 0, relg.shape[1] - 1))
    d = relg[max(iy - 1, 0):iy + 2, max(iz - 1, 0):iz + 2].max() if z_b < relg.shape[1] * rel['cell'] else .06
    return house_world[0] + rel['x_face'] - shift[0] + d
east_wall_x_plane = east_wall_x(house_world[1], 1.0)
west_wall_x = house_world[0] - W1 / 2 - .07
hy = house_world[1]

# --- original live/background placements replaced by 3D props (origin IDs, scripts and saves retained)
replacement('S440_P14', 'SM_Barrel_Oak_01', 352, 315, note='bar-sh barrel, original pixel')
replacement('S440_P15', 'SM_Barrel_Oak_01', 259, 272, note='bar-sh barrel, original pixel (west of the house)')
lean_rows = [('S440_P21', 'SM_Pitchfork_Ash_01', hy + 0.85, -90, 10), ('S440_P22', 'SM_Scythe_Ash_01', hy + 1.55, -90, 8)]
for origin, mesh, wy, spin, tilt in lean_rows:
    xy, z, rot = lean(mesh, [0, wy], east_wall_x, spin, tilt)
    p = pixel(xy)
    replacement(origin, mesh, p[0], p[1], z * 100, rot, note='leaning on the east wall (original leant on the right-hand face)')
for mesh, wy, spin, tilt in (('SM_Shovel_Ash_01', hy + 2.65, -90, 11), ('SM_Hoe_Ash_01', hy + 3.25, -90, 10)):
    xy, z, rot = lean(mesh, [0, wy], east_wall_x, spin, tilt)
    p = pixel(xy)
    element(mesh.replace('SM_', '').replace('_01', '') + 'Lean', mesh, p[0], p[1], z * 100, rot, note='new dressing, leaning on the east wall')
ground_tools = [('S440_P23', 'SM_Axe_Felling_01', 418, 316, 205), ('S440_P24', 'SM_Tongs_Iron_01', 461, 302, 40), ('S440_P25', 'SM_Hatchet_01', 463, 287, 120)]
for origin, mesh, px, py, yaw in ground_tools:
    replacement(origin, mesh, px, py, 0.0, (0, yaw, 0), note='lying on the ground at the original pixel')

# --- new yard dressing (no original identity)
wp = pixel([east_wall_x_plane + .26, hy - 2.55])
element('Woodpile', 'SM_Woodpile_Split_01', wp[0], wp[1], 0, (0, 90, 0), note='firewood stacked against the east wall, north of its window')
cb = pixel(world(440, 300)); element('ChoppingBlock', 'SM_ChoppingBlock_Axe_01', cb[0], cb[1], 0, (0, 160, 0))
element('Wheelbarrow', 'SM_Wheelbarrow_Oak_01', 478, 252, 0, (0, 205, 0))
element('HayBale_A', 'SM_HayBale_01', 512, 262, 0, (0, 12, 0), note='at the original tall-grass clump S440_P26')
element('HayBale_B', 'SM_HayBale_01', 513, 262.5, 36.0, (0, 96, 0), note='stacked crosswise on HayBale_A (bale height 36 cm)')
element('HayBale_C', 'SM_HayBale_01', 527, 280, 0, (0, -24, 0))
element('WaterTrough', 'SM_WaterTrough_Oak_01', 232, 252, 0, (0, 90, 0))

# --- reused exterior kit: fence (continuous with screen 439's south run), oak, painted rocks, grass
f439 = world(586, 366, 439)
x = f439[0] + 4.0; k = 0
while True:
    py = 366.0
    px = pixel([x, world(300, py)[1]])[0]
    if px - 20 > 600:
        break
    element('FenceSouth%d' % k, 'SM_Fence_SplitRail_4m_01', px, py)
    x += 4.0; k += 1
element('Oak_P12', 'SM_Oak_Stonebrook_01', 572, 36, 0, (0, 40, 0), scale=(1.05, 1.05, 1.05), note='original oak S440_P12')
element('Boulder_A', 'SM_Boulder_Fieldstone_01', 107, 189, -6, (0, 25, 0), scale=(1.0, .95, .85), note='tile-painted low rock (original Low hardness)')
element('Boulder_B', 'SM_Boulder_Fieldstone_01', 86, 216, -6, (0, 118, 0), scale=(.8, .8, .75), note='tile-painted low rock (original Low hardness)')

weeds = ['S440_P07', 'S440_P10', 'S440_P13', 'S440_P17', 'S440_P26', 'S440_P27', 'S440_P28', 'S440_P29', 'S440_P30', 'S440_P31', 'S440_P33']
for o in weeds:
    p = placements[o]
    if o == 'S440_P26':
        continue        # hay bales stand there now
    element('Grass_' + o, 'SM_Grass_Meadow_01', p['map_x'], p['map_y'], 0, (0, rnd.uniform(0, 360), 0), (1.1, 1.1, 1.1), collision=False)
hx0, hy0 = pixel(house_world - np.array([W1 / 2 + 1.0, D1 / 2 + 1.0])); hx1, hy1 = pixel(house_world + np.array([W1 / 2 + 1.0, D1 / 2 + 1.5]))
keep_clear = [(hx0, hy0, hx1, hy1), (395, 225, 540, 330), (215, 235, 285, 300), (330, 300, 375, 330), (95, 95, 125, 115), (70, 175, 125, 230)]
for i in range(85):
    px, py = rnd.uniform(5, 595), rnd.uniform(8, 352)
    if any(a <= px <= c and b <= py <= d for a, b, c, d in keep_clear):
        continue
    s = rnd.uniform(.7, 1.3)
    element('Grass%03d' % i, 'SM_Grass_Meadow_01', px, py, 0, (0, rnd.uniform(0, 360), 0), (s, s, s), collision=False)
for i in range(16):         # along the fence foot, where mowers never reach
    px = rnd.uniform(5, 595); s = rnd.uniform(.9, 1.4)
    element('FenceGrass%02d' % i, 'SM_Grass_Meadow_01', px, rnd.uniform(358, 372), 0, (0, rnd.uniform(0, 360), 0), (s, s, s), collision=False)

layout['hide_origins'] = sorted(['S440_P03', 'S440_P04', 'S440_P06', 'S440_P08', 'S440_P09', 'S440_P11', 'S440_P12',
                                 'S440_P01', 'S440_P16', 'S440_P18', 'S440_P19', 'S440_P20'] + weeds)
layout['untouched_origins'] = {'S440_P02': 'Quackers (s1-oldd, vision 2): built separately, left live and visible',
                               'S440_P05': 'background weed with bar-sh outside the 600 px map (x=633): not drawn, untouched'}
layout['notes'] = [
    'Draft for the coordinating agent: not imported, not published to Content/Dink/Data/Art.',
    'The existing importer hard-codes warp_overrides per screen; S440_P06 needs the row in warp_overrides here.',
    'Leaning tools use full Unreal rotators [pitch, yaw, roll] computed for FRotationMatrix; Blender preview emulates the same transform.',
    'House is axis aligned like the SCR_439 cottage; its door face centre is on the original S440_P06 trigger.']
(ART / 'layout_440.json').write_text(json.dumps(layout, indent=2) + '\n')

# ----------------------------------------------------------------------------- runtime manifest draft
def world_cm(px, py, z_cm=0.0):
    w = world(px, py); return [float(w[0] * 100), float(w[1] * 100), float(z_cm)]


rt = {'schema': 'dink-art/1', 'screen': SCREEN, 'draft': True, 'assets': [], 'source': 'SourceAssets/Art/Stonebrook440/art_manifest.json',
      'replacements': [], 'elements': [], 'hide_origins': [], 'hide_screen_visuals': [SCREEN], 'authored_collision_screens': [SCREEN],
      'preserve_low_collision_screens': [], 'lights': [], 'warp_overrides': []}
for n, a in man['assets'].items():
    rt['assets'].append({'mesh': a['ue_path'] + '.' + n, 'expected_size_cm': [d * 100 for d in a['dimensions_m']],
                         'expected_lods': a['expected_lods'], 'bounds_tolerance_cm': 1.0})
mesh_path = lambda m: layout['asset_paths'][m] + '.' + m
replaced = set()
for r in layout['replacements']:
    src = placements[r['origin']]
    if src['representation'] != 'instance':
        w = world_cm(*r['source_pixel'], r['height_cm'])
        rt['replacements'].append({'origin': r['origin'], 'mesh': mesh_path(r['mesh']),
                                   'offset_cm': [w[0] - src['world'][0] * 100, w[1] - src['world'][1] * 100, w[2]],
                                   'rotation_deg': r['rotation_deg'], 'scale': r['scale']})
        replaced.add(r['origin'])
    else:   # background instances become plain elements (importer rule)
        rt['elements'].append({'name': r['origin'], 'mesh': mesh_path(r['mesh']), 'world_cm': world_cm(*r['source_pixel'], r['height_cm']),
                               'rotation_deg': r['rotation_deg'], 'scale': r['scale'], 'collision': True, 'camera_occluder': False})
for e in layout['elements']:
    cls = man['assets'].get(e['mesh'], {}).get('cls', '')
    rt['elements'].append({'name': e['name'], 'mesh': mesh_path(e['mesh']), 'world_cm': world_cm(*e['source_pixel'], e['height_cm']),
                           'rotation_deg': e['rotation_deg'], 'scale': e['scale'], 'collision': e['collision'],
                           'camera_occluder': cls in ('kit_wall', 'kit_ceiling', 'kit_piece')})
rt['hide_origins'] = [o for o in layout['hide_origins'] if o not in replaced]
for w in layout['warp_overrides']:
    rt['warp_overrides'].append({'origin': w['origin'], 'world_cm': world_cm(*w['source_pixel'], w['height_cm']), 'extent_cm': w['extent_cm']})
(ART / 'runtime_manifest_440_draft.json').write_text(json.dumps(rt, indent=2) + '\n')

# ----------------------------------------------------------------------------- checks against the original data
hard = np.array(Image.open(REPO / 'tools/dinkex/out/hardness/SCR_440.png'))
def code_hist(x0, y0, x1, y1):
    sub = hard[max(int(y0), 0):min(int(y1) + 1, 400), max(int(x0), 0):min(int(x1) + 1, 600)]
    vals, cnt = np.unique(sub, return_counts=True)
    return {int(v): int(c) for v, c in zip(vals, cnt)}
fx0, fy0 = pixel(house_world - np.array([W1 / 2, D1 / 2])); fx1, fy1 = pixel(house_world + np.array([W1 / 2, D1 / 2]))
house_solid = (hard == 1)
fp = np.zeros_like(house_solid); fp[int(fy0):int(fy1) + 1, int(fx0):int(fx1) + 1] = True
orig_house_solid = house_solid.copy(); orig_house_solid[:, :230] = False; orig_house_solid[330:, :] = False
checks = {
    'house_source_pixel': house_px, 'house_world_m': [float(v) for v in house_world],
    'door_face_world_m': [float(v) for v in door_world], 'door_target_px': door_target_px,
    'original_warp_stamp_px': [295, 263, 330, 293],
    'door_inside_original_trigger': bool(295 <= door_target_px[0] <= 330 and 263 <= door_target_px[1] <= 293),
    'lower_footprint_px': [fx0, fy0, fx1, fy1],
    'footprint_codes_px': code_hist(fx0, fy0, fx1, fy1),
    'footprint_fraction_inside_original_solid_or_sprite': float((fp & ((hard == 1) | (hard == 100) | (hard == 200))).sum() / fp.sum()),
    'original_house_solid_px_now_open_ground': int((orig_house_solid & ~fp).sum()),
    'original_house_solid_px': int(orig_house_solid.sum()),
    'east_wall_world_x_m': east_wall_x_plane, 'leaning_tool_contact': LEAN_REPORT, 'west_wall_world_x_m': west_wall_x,
    'fence_segments': k, 'fence_first_center_px': layout['elements'][[e['name'] for e in layout['elements']].index('FenceSouth0')]['source_pixel'],
    'element_count': len(layout['elements']), 'replacement_count': len(layout['replacements']),
    'notes': ['The original roof-projected tile outline covers ~25 x 20 m; the 11 x 8.5 m stone footprint lies inside it and the remaining band '
              'becomes walkable yard under the eaves, the same deliberate policy as screen 439 (README).']}
for e in layout['elements'] + layout['replacements']:
    if e['mesh'] in man['assets'] and e['mesh'] != 'SM_House_Stonebrook_TwoStorey_01':
        d = man['assets'][e['mesh']]['dimensions_m']; r = max(d[0], d[1]) / 2 / .0988
        px, py = e['source_pixel']
        checks.setdefault('prop_ground_codes', {})[e.get('name', e.get('origin'))] = code_hist(px - r, py - r, px + r, py + r)
(ART / 'layout_checks_440.json').write_text(json.dumps(checks, indent=2) + '\n')
print('layout written:', len(layout['elements']), 'elements', len(layout['replacements']), 'replacements; house px', house_px,
      'door in trigger', checks['door_inside_original_trigger'], 'footprint in original solid %.2f' % checks['footprint_fraction_inside_original_solid_or_sprite'])
