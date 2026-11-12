"""Shared, dependency-free layout data for the Stonebrook ruin kit.

Imported by the numpy texture synthesiser (system python3) and by the Blender build,
so both agree on stone layout, roof holes, burn marks and fire-emitter positions.

Coordinate frames
-----------------
* COTTAGE frame: the construction frame of tools/build_exterior.py (metres): x east along the
  long front, y toward the BACK (front wall at y=-4.5, Blender front = -Y), z up, sill bottom z=0.
  The delivered meshes keep the original cottage pivot (see build_ruins.py, ORIGINAL_DELTA).
* ROOM frame (interior SCR_001): source pixels, as in Stonebrook/room_layout.json; x 130..470,
  y 100..400 map to 14.875 m x 13.125 m (0.04375 m/px, interior scale 1.75 x 0.025).

Original data provenance: placements and frame metrics below are copied from the deterministic
extractor output tools/dinkex/out (screens/SCR_001.json, SCR_439.json, sequences.json; extracted
from bin/dink on this machine).  x values are MAP pixels (placement x minus the 20 px sidebar).
"""
import math, random

SEED = 31439          # texture/geometry seed for this kit (vision 3+ of screen 439)
ORIGINAL_SEED = 439   # tools/build_exterior.py seed; replayed to reproduce its stone/thatch layout

# ---------------------------------------------------------------------------------------------
# Original sprite frames used by the vision-1/2 effects: (width, height, origin_x, origin_y)
FRAMES = {
    (427, 1): (80, 78, 71, 99), (427, 2): (77, 78, 71, 99), (427, 3): (78, 77, 71, 99),
    (427, 4): (78, 78, 71, 99), (427, 5): (76, 78, 71, 99), (427, 6): (78, 78, 71, 99),
    (154, 1): (90, 69, 60, 50), (155, 1): (23, 20, 15, 15), (156, 1): (23, 23, 15, 18),
    (157, 1): (42, 40, 28, 29), (158, 1): (23, 20, 15, 15), (158, 2): (23, 23, 15, 18),
    (158, 3): (42, 40, 28, 29), (158, 4): (90, 69, 60, 50), (158, 5): (90, 69, 60, 50),
    (161, 4): (93, 141, 57, 123), (161, 14): (88, 140, 57, 123), (70, 1): (60, 61, 44, 47),
    (355, 1): (68, 50, 54, 9),
}
SEQ_NAMES = {427: 'graphics/effects/fire/fire1-', 154: 'struct/details/damage/damag-',
             155: 'struct/details/damage/fire2-', 156: 'struct/details/damage/fire3-',
             157: 'struct/details/damage/fire4-', 158: 'struct/details/damage/hole-',
             161: 'effects/atomic/atomc-', 70: 'effects/splode/explo-', 355: 'people/mom/death-'}
# Remaster emitter archetype per original sequence (VFX are authored in Unreal, not here).
EFFECT_KIND = {427: 'flame_large', 155: 'flame_small', 156: 'flame_small', 157: 'flame_medium',
               154: 'smoulder_damage', 158: 'smoke_vent', 161: 'fire_column', 70: 'burst_oneshot'}

# (id, map_x, y, seq, frame, vision)
SCR439 = [
    ('S439_P05', 328, 127, 427, 1, 1), ('S439_P09', 427, 165, 427, 4, 1), ('S439_P11', 203, 195, 427, 2, 1),
    ('S439_P21', 254, 222, 427, 5, 1), ('S439_P29', 306, 193, 154, 1, 1), ('S439_P31', 284, 106, 155, 1, 1),
    ('S439_P32', 198, 188, 156, 1, 1), ('S439_P33', 371, 147, 157, 1, 1), ('S439_P46', 238, 182, 158, 1, 1),
    ('S439_P23', 309, 101, 158, 2, 2), ('S439_P24', 209, 149, 158, 2, 2), ('S439_P25', 341, 201, 158, 3, 2),
    ('S439_P26', 308, 155, 158, 3, 2), ('S439_P27', 206, 295, 158, 1, 2), ('S439_P28', 144, 223, 158, 1, 2),
    ('S439_P30', 199, 170, 158, 1, 2), ('S439_P34', 372, 154, 158, 4, 2), ('S439_P36', 295, 259, 158, 1, 2),
    ('S439_P37', 367, 246, 158, 1, 2), ('S439_P38', 287, 198, 158, 5, 2),
]
SCR001 = [
    ('S001_P21', 467, 294, 427, 1, 1), ('S001_P27', 389, 88, 427, 3, 1), ('S001_P28', 210, 250, 70, 1, 1),
    ('S001_P29', 286, 182, 70, 1, 1), ('S001_P30', 225, 81, 427, 4, 1), ('S001_P31', 143, 124, 427, 6, 1),
    ('S001_P32', 241, 178, 427, 4, 1), ('S001_P33', 165, 206, 161, 4, 1), ('S001_P34', 194, 141, 355, 1, 1),
    ('S001_P35', 164, 47, 155, 1, 1), ('S001_P36', 421, 34, 156, 1, 1), ('S001_P38', 431, 361, 157, 1, 1),
    ('S001_P41', 436, 200, 161, 14, 1),
    ('S001_P44', 214, 144, 158, 1, 2), ('S001_P45', 134, 260, 158, 1, 2), ('S001_P46', 334, 303, 158, 1, 2),
    ('S001_P47', 438, 219, 158, 3, 2), ('S001_P48', 203, 240, 158, 3, 2), ('S001_P49', 182, 374, 158, 3, 2),
]

# Screen corners (metres, x east, y south) from ImportData/screens.json; used for world_cm.
CORNERS = {
    1: {'nw': (-1851.3391, 3918.4598), 'ne': (-1825.0891, 3918.4598), 'sw': (-1851.3391, 3935.9598), 'se': (-1825.0891, 3935.9598)},
    439: {'nw': (942.9425, 344.4383), 'ne': (1002.0559, 344.7009), 'sw': (943.4547, 384.0304), 'se': (1002.4886, 384.4408)},
}
COTTAGE_SOURCE_PIXEL = (285.0, 248.5)   # exterior_layout.json 'DinksCottage'


def world_cm(screen, px, py):
    c = CORNERS[screen]; u, v = px / 600.0, py / 400.0
    return [100.0 * (c['nw'][i] * (1 - u) * (1 - v) + c['ne'][i] * u * (1 - v) + c['sw'][i] * (1 - u) * v + c['se'][i] * u * v)
            for i in range(2)]


def visual_point(px, py, seq, frame):
    """Where the effect visibly sits in the original frame: flame base, or hole centre."""
    w, h, ox, oy = FRAMES[(seq, frame)]
    left, top = px - ox, py - oy
    if seq in (427, 161, 155, 156, 157):        # flames: base of the flame image
        return left + w * 0.5, top + h * 0.92
    return left + w * 0.5, top + h * 0.5        # holes, damage, bursts: image centre


# ---------------------------------------------------------------------------------------------
# Oblique fit of the original 1997 house sprite (seq 63 frame 1) to the 3D cottage.
# Measured on the sprite: front-left wall foot (250,320); front-right wall foot (432,235) after
# 18 m; back-left wall foot (120,290) after 9 m; wall height 68 px for 3.5 m.  The sprite's
# drawing is a hand-painted pseudo-isometric view, so this is an interpretive correspondence:
# it tells WHICH part of the roof/wall an effect was painted on, not a survey.
SPR_O = (250.0, 320.0)
SPR_EX = (182.0 / 18.0, -85.0 / 18.0)
SPR_EY = (-130.0 / 9.0, -30.0 / 9.0)
SPR_EZ = (0.0, -19.4)


def _solve2(a, b, c):
    det = a[0] * b[1] - a[1] * b[0]
    return ((c[0] * b[1] - c[1] * b[0]) / det, (a[0] * c[1] - a[1] * c[0]) / det)


def sprite_project(x, y, z):
    """Cottage-frame metres -> original screen pixels (inverse of sprite_to_cottage)."""
    a, b = x + 9.0, y + 4.5
    return (SPR_O[0] + SPR_EX[0] * a + SPR_EY[0] * b + SPR_EZ[0] * z,
            SPR_O[1] + SPR_EX[1] * a + SPR_EY[1] * b + SPR_EZ[1] * z)


def sprite_to_cottage(sx, sy):
    """Return (surface, x, y, z, normal) of the visible cottage surface under a screen point."""
    a0, b0 = _solve2(SPR_EX, SPR_EY, (sx - SPR_O[0], sy - SPR_O[1]))
    p0 = (a0 - 9.0, b0 - 4.5, 0.0)
    dx, dy = _solve2(SPR_EX, SPR_EY, (-SPR_EZ[0], -SPR_EZ[1]))   # null direction with dz = 1
    hits = []
    k = 3.75 / 5.0
    # front slope z = 3.5 + k*(y+5), y in [-5,0]
    den = 1 - k * dy
    z = (3.5 + k * (p0[1] + 5)) / den
    y = p0[1] + z * dy; x = p0[0] + z * dx
    if -5.0 <= y <= 0 and -9.4 <= x <= 9.4:
        n = (0.0, -k, 1.0); hits.append(('roof_front', x, y, z, n))
    # back slope z = 3.5 + k*(5-y), y in [0,5]
    den = 1 + k * dy
    z = (3.5 + k * (5 - p0[1])) / den
    y = p0[1] + z * dy; x = p0[0] + z * dx
    if 0 <= y <= 5.0 and -9.4 <= x <= 9.4:
        n = (0.0, k, 1.0); hits.append(('roof_back', x, y, z, n))
    # walls (vertical planes)
    for name, axis, val, n in [('wall_front', 1, -4.5, (0, -1, 0)), ('wall_back', 1, 4.5, (0, 1, 0)),
                               ('wall_west', 0, -9.0, (-1, 0, 0)), ('wall_east', 0, 9.0, (1, 0, 0))]:
        d = dy if axis == 1 else dx
        if abs(d) < 1e-9:
            continue
        z = (val - p0[axis]) / d
        x = p0[0] + z * dx; y = p0[1] + z * dy
        if 0 <= z <= 3.5 and -9.0 <= x <= 9.0 and -4.5 <= y <= 4.5:
            hits.append((name, x, y, z, n))
    if not hits:
        return ('ground', p0[0], p0[1], 0.0, (0, 0, 1))
    s, x, y, z, n = max(hits, key=lambda h: h[3])
    L = math.sqrt(sum(c * c for c in n))
    return (s, x, y, z, tuple(c / L for c in n))


# The sprite paints a hipped roof: its front slope is the quad below, its west hip the triangle
# (110,182)-(222,117)-(250,252).  Roof points are mapped by inverse-bilinear quad coordinates
# (u along the eave, t up the slope) onto the 3D gable roof; wall points use the oblique fit above.
SPR_ROOF = {'E0': (250.0, 252.0), 'E1': (442.0, 157.0), 'R0': (222.0, 117.0), 'R1': (310.0, 82.0)}
SPR_WEST_WALL = [(110.0, 182.0), (250.0, 252.0), (250.0, 320.0), (120.0, 290.0)]
SPR_FRONT_WALL = [(250.0, 252.0), (442.0, 157.0), (432.0, 235.0), (250.0, 320.0)]


def _inside(poly, p):
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _quad_uv(p):
    E0, E1, R0, R1 = (SPR_ROOF[k] for k in ('E0', 'E1', 'R0', 'R1'))
    u, t = .5, .5
    for _ in range(30):
        f = [(1 - t) * ((1 - u) * E0[i] + u * E1[i]) + t * ((1 - u) * R0[i] + u * R1[i]) - p[i] for i in range(2)]
        du = [(1 - t) * (E1[i] - E0[i]) + t * (R1[i] - R0[i]) for i in range(2)]
        dt = [((1 - u) * R0[i] + u * R1[i]) - ((1 - u) * E0[i] + u * E1[i]) for i in range(2)]
        su, st = _solve2(du, dt, (-f[0], -f[1]))
        u += su; t += st
    return u, t


def _wall_hit(sx, sy, axis, val, name, n):
    a0, b0 = _solve2(SPR_EX, SPR_EY, (sx - SPR_O[0], sy - SPR_O[1]))
    p0 = (a0 - 9.0, b0 - 4.5)
    dx, dy = _solve2(SPR_EX, SPR_EY, (-SPR_EZ[0], -SPR_EZ[1]))
    d = dy if axis == 1 else dx
    z = (val - p0[axis]) / d
    x = max(-8.8, min(8.8, p0[0] + z * dx)); y = max(-4.3, min(4.3, p0[1] + z * dy))
    if axis == 0: x = val
    else: y = val
    return (name, x, y, max(.3, min(3.3, z)), n)


def sprite_to_cottage_roofaware(sx, sy):
    if _inside(SPR_WEST_WALL, (sx, sy)):
        return _wall_hit(sx, sy, 0, -9.0, 'wall_west', (-1.0, 0.0, 0.0))
    if _inside(SPR_FRONT_WALL, (sx, sy)):
        return _wall_hit(sx, sy, 1, -4.5, 'wall_front', (0.0, -1.0, 0.0))
    u, t = _quad_uv((sx, sy))
    if not (-0.6 <= u <= 1.05 and -0.05 <= t <= 1.6):
        return sprite_to_cottage(sx, sy)
    # hip + front slope together span the 3D gable roof from west to east
    x = max(-9.0, min(9.0, -9.4 + 18.8 * (u + 0.45) / 1.45))
    k = 3.75 / 5.0
    if t <= 1.0:
        tt = max(0.03, t)
        y, z = -5 + 5 * tt, 3.5 + 3.75 * tt
        n = (0.0, -k, 1.0); s = 'roof_front'
    else:
        y = min(3.5, (t - 1.0) * 6.0); z = 7.25 - k * y
        n = (0.0, k, 1.0); s = 'roof_back'
    L = math.sqrt(sum(c * c for c in n))
    return (s, x, y, z, tuple(c / L for c in n))


def exterior_effects():
    out = []
    for pid, px, py, seq, frame, vision in SCR439:
        vx, vy = visual_point(px, py, seq, frame)
        surf, x, y, z, n = sprite_to_cottage_roofaware(vx, vy)
        out.append({'id': pid, 'source_pixel': [px, py], 'visual_pixel': [round(vx, 1), round(vy, 1)],
                    'seq': seq, 'frame': frame, 'vision': vision, 'surface': surf,
                    'cottage_m': (x, y, z), 'normal': n, 'sprite_width_px': FRAMES[(seq, frame)][0]})
    return out


def roof_holes(state):
    """Burnt-through thatch openings in the cottage frame: (x, y, radius, rim)."""
    holes = []
    for e in exterior_effects():
        if not e['surface'].startswith('roof'):
            continue
        w = e['sprite_width_px']
        x, y, _ = e['cottage_m']
        if state == 'burnt' and e['vision'] == 2 and e['seq'] == 158:
            r = {23: .55, 42: 1.05, 90: 1.95}[w]
            holes.append((x, y, r, r * 0.65 + .35))
        if e['vision'] == 1 and e['seq'] in (158, 154):
            # The vision-1 opening/damage also exists after the fire (it only grew).
            r = .5 if e['seq'] == 158 else .75
            if state == 'burnt':
                r *= 1.5
            holes.append((x, y, r, r * .6 + .3))
    return holes


def roof_scorches(state):
    """Charred-but-standing thatch around burning points (x, y, radius)."""
    out = []
    for e in exterior_effects():
        if e['vision'] == 1 and e['surface'].startswith('roof') and e['seq'] in (427, 155, 156, 157):
            out.append((e['cottage_m'][0], e['cottage_m'][1], 1.25 if e['seq'] == 427 else .8))
    return out


def wall_burns():
    """Burn marks painted on walls in the original vision 2 (front/back/side, x-or-y, z, r)."""
    out = []
    for e in exterior_effects():
        if e['vision'] == 2 and e['surface'].startswith('wall'):
            x, y, z = e['cottage_m']
            out.append((e['surface'], x, y, max(.55, min(z, 2.8)), .55))
    return out


# ---------------------------------------------------------------------------------------------
# Replay of build_exterior.py's random stream, so the ruin's stones and thatch bundles sit
# exactly where the intact cottage's do (same seed, same call order).
DOOR_X = 5.3
WINDOWS_X = [-7.5, -3, 1.5, 7.5]


def cottage_layout():
    rnd = random.Random(ORIGINAL_SEED)
    stones = {'front': [], 'back': []}
    for face_y, key in [(-4.5, 'front'), (4.5, 'back')]:
        for course in range(4):
            z = .25 + course * .29
            x = -9.0
            while x < 8.95:
                width = min(rnd.uniform(.65, 1.15), 9 - x)
                cx = x + width / 2
                if face_y > 0 or abs(cx - DOOR_X) > 1.0:
                    stones[key].append((cx, z, width - .02, .275))
                x += width
    side_stones = [(-4.05 + i * .9, .25 + c * .29, .87, .275) for c in range(4) for i in range(10)]
    bundles = []
    for side in [-1, 1]:
        for row in range(18):
            t = (row + .5) / 18; y = side * (5 - t * 5); z = 3.5 + t * 3.75 + .06
            for col in range(86):
                x = -9.25 + col * .215 + (.09 if row % 2 else 0) + rnd.uniform(-.04, .04)
                a = (x, y - side * .32, z + .23); b = (x, y + side * .36, z - .27 + rnd.uniform(-.025, .025))
                bundles.append((side, row, col, a, b))
    return {'stones': stones, 'side_stones': side_stones, 'bundles': bundles}


def openings(face):
    """Openings of a facade in its own horizontal coordinate: (centre, half_width, bottom, top)."""
    out = [(x, .58, 1.66, 2.90) for x in WINDOWS_X if abs(x - DOOR_X) >= 1.8]
    if face == 'front':
        out.append((DOOR_X, .75, .22, 2.51))
    return out


# ---------------------------------------------------------------------------------------------
# Interior (SCR_001) effect placement in room source pixels + height.
ROOM = {'x0': 130.0, 'x1': 470.0, 'y0': 100.0, 'y1': 400.0, 'm_per_px': 0.04375, 'height_m': 3.5}


def interior_effects():
    out = []
    for pid, px, py, seq, frame, vision in SCR001:
        vx, vy = visual_point(px, py, seq, frame)
        surface, sx, sy, h = 'floor', vx, vy, 0.0
        if vy < ROOM['y0'] + 4:                      # painted on the north wall face
            surface, sy, h = 'wall_north', ROOM['y0'] + 4, min(3.1, (ROOM['y0'] - vy) / 27.7 + .3)
        elif vy > 300 and not (255 < vx < 345):       # the drawn south wall band
            surface, sy, h = 'wall_south', ROOM['y1'] - 4, max(.4, (ROOM['y1'] - vy) / 100.0 * 3.5)
        elif vx < ROOM['x0'] + 10:
            surface, sx, h = 'wall_west', ROOM['x0'] + 4, .6
        elif vx > ROOM['x1'] - 10:
            surface, sx = 'floor', ROOM['x1'] - 14
        sx = min(max(sx, ROOM['x0'] + 4), ROOM['x1'] - 4)
        out.append({'id': pid, 'source_pixel': [px, py], 'visual_pixel': [round(vx, 1), round(vy, 1)],
                    'placement_pixel': [round(sx, 1), round(sy, 1)], 'height_cm': round(h * 100, 1),
                    'seq': seq, 'frame': frame, 'vision': vision, 'surface': surface})
    return out


def room_m(px, py):
    """Room source pixel -> metres from the NW inner corner (x east, y south)."""
    return ((px - ROOM['x0']) * ROOM['m_per_px'], (py - ROOM['y0']) * ROOM['m_per_px'])


# ---------------------------------------------------------------------------------------------
# Realism pass 2: random-bond fieldstone rubble for the ruin variants (replaces the intact kit's
# four regular courses inside the same wall envelope: z 0.11..1.26 m, 0.5 m thick).
def rubble_layout(seed=SEED + 77):
    """{'front'|'back'|'west'|'east': [(c, z, w, h, proud, spall)]} with c the facade-horizontal
    centre (x for front/back, y for sides).  Irregular course heights, varied stone lengths,
    occasional split stones and pinning stones; joints 2-5 cm (mortar visible behind)."""
    rnd = random.Random(seed)
    out = {}
    spans = {'front': [(-9.0, DOOR_X - .85), (DOOR_X + .85, 9.0)], 'back': [(-9.0, 9.0)],
             'west': [(-4.55, 4.55)], 'east': [(-4.55, 4.55)]}
    for face, segs in spans.items():
        stones = []
        z = .13
        while z < 1.24:
            h = rnd.uniform(.16, .33)
            if 1.255 - (z + h) < .12:
                h = 1.255 - z
            for (a, b) in segs:
                x = a + (rnd.uniform(0, .25) if rnd.random() < .5 else 0)
                while x < b - .05:
                    w = min(rnd.uniform(.28, 1.05) * (0.75 + h * 1.2), b - x)
                    if b - (x + w) < .18:
                        w = b - x
                    j = rnd.uniform(.02, .05)
                    cz = z + h / 2 + rnd.uniform(-.015, .015)
                    proud = rnd.uniform(-.02, .035)
                    if h > .26 and rnd.random() < .22 and w > .45:      # two stacked smaller stones
                        h1 = h * rnd.uniform(.4, .6)
                        stones.append((x + w / 2, z + h1 / 2, w - j, h1 - .025, proud, 0))
                        stones.append((x + w / 2 + rnd.uniform(-.05, .05), z + h1 + (h - h1) / 2, w - j - rnd.uniform(0, .1), h - h1 - .025, rnd.uniform(-.02, .03), 0))
                    else:
                        stones.append((x + w / 2, cz, w - j, h - j, proud, 0))
                    if rnd.random() < .18 and w > .5:                    # small pinning stone in the joint
                        stones.append((x + w + .02, cz + rnd.uniform(-.05, .05), .09, .08, rnd.uniform(0, .02), 0))
                    x += w
            z += h
        out[face] = stones
    return out


def spall_mask(face, c, z):
    """True where heat spalled the stone face (near openings, low on the front)."""
    for (oc, hw, ob, ot) in (openings(face) if face in ('front', 'back') else []):
        if abs(c - oc) < hw + .9 and z > .5:
            return True
    return False


# Ground-scorch scatter around the burnt cottage (cottage construction frame, patch centres):
# (asset, size_m, cx, cy, yaw_deg, scale).  Concentrated under the openings and along the front.
GROUND_SCORCH = [
    ('SM_Decal_Scorch_Ground_3m_01', 3.0, 5.3, -6.1, 20, 1.0),     # in front of the doorway
    ('SM_Decal_Scorch_Ground_2m_01', 2.0, 2.0, -5.6, 75, 1.0),
    ('SM_Decal_Scorch_Ground_2m_02', 2.0, -3.1, -5.5, 140, 1.1),   # under the window by P36
    ('SM_Decal_Scorch_Ground_1m5_01', 1.5, -7.4, -5.3, 10, 1.0),
    ('SM_Decal_Scorch_Ground_1m5_01', 1.5, 7.6, -5.4, 250, 1.2),
    ('SM_Decal_Scorch_Ground_2m_01', 2.0, -10.2, -1.5, 300, 1.0),  # west gable foot
    ('SM_Decal_Scorch_Ground_3m_01', 3.0, -1.0, 6.0, 190, 1.0),    # behind, under the back-slope openings
    ('SM_Decal_Scorch_Ground_2m_02', 2.0, 10.1, 2.0, 35, .9),
    ('SM_Decal_Scorch_Ground_1m5_01', 1.5, 3.9, 5.7, 120, 1.0),
]


def decal_pivot(cx, cy, size, yaw_deg, scale):
    """Min-corner pivot (Blender frame) for a kit_floor decal centred at (cx, cy)."""
    h = size * scale / 2; a = math.radians(yaw_deg)
    return (cx - (h * math.cos(a) - h * math.sin(a)), cy - (h * math.sin(a) + h * math.cos(a)))
