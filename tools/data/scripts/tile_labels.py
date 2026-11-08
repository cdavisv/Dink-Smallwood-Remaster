"""Hand classification of tile cells (pipeline stage 2).

Every tileset that map.dat uses was viewed as a labelled contact sheet
(scripts/tile_sheets.py -> out/tiles/tsNN.png). What each sheet depicts was
decided by eye and is written below as one rule per sheet:

  * 'cells' rules list cell ranges by hand.
  * 'auto' rules are for sheets that are blends of known materials (grass with
    boulders, sand/water shorelines, ...). The materials and their reference
    cells are picked by hand; each pixel is then assigned to the nearest
    reference colour (features.material_fractions) and the cell is labelled from
    those fractions. The result was re-checked against overlay sheets
    (scripts/tile_overlay.py -> out/tiles/tsNN_labels.png) and wrong cells are
    corrected in the sheet's 'override' list.

Output of label(num): dict(terrain, transition, confidence, notes).
"""
from features import material_fractions

# Terrain vocabulary. walkable is the intended 3D walkability of the class,
# NOT taken from hard.dat (original tile hardness is mostly thin outlines).
TERRAIN = {
    'grass':            ('yes', 'Open meadow grass (incl. flower-speckled variants).'),
    'grass_rocky':      ('partial', 'Grass with painted boulders; place rock meshes on it.'),
    'rock_mass':        ('no', 'Dense boulder pile / outcrop core painted into tiles; impassable.'),
    'gravel':           ('yes', 'Bare stony clearing (no road edges).'),
    'path':             ('yes', 'Gravel road / town path with defined edges.'),
    'dirt':             ('yes', 'Bare brown earth / mud plot.'),
    'sand':             ('yes', 'Beach or dune sand.'),
    'water':            ('no', 'Open water (river, lake, sea). Depth is not encoded in the tiles.'),
    'ice':              ('yes', 'Frozen water around the snow island (probable; could be cold sea).'),
    'snow':             ('yes', 'Snow ground.'),
    'lava':             ('no', 'Fire pit / burning ground (animated fire tiles).'),
    'cliff_face':       ('no', 'Vertical earth/rock cliff or ridge wall; needs real elevation in 3D.'),
    'forest_canopy':    ('no', 'Dense forest roof seen from above; impassable tree mass.'),
    'wasteland':        ('yes', 'Grey-blue barren ground of the Darklands.'),
    'chasm':            ('no', 'Black bottomless pit in the Darklands.'),
    'cave_floor':       ('yes', 'Cave dungeon floor.'),
    'cave_wall':        ('no', 'Cave rock wall / spiky rock mass.'),
    'wood_floor':       ('yes', 'Interior plank floor.'),
    'stone_floor':      ('yes', 'Castle / dungeon flagstones (incl. cracked variants).'),
    'structure_facade': ('no', 'Building wall and roof painted into the tile layer (big buildings).'),
    'void':             ('no', 'Solid black outside interior rooms.'),
}

T = lambda ts, c: (ts - 1) * 128 + c  # noqa: E731


def rng(*parts):
    out = []
    for p in parts:
        if isinstance(p, int):
            out.append(p)
        else:
            a, b = p
            out.extend(range(a, b + 1))
    return out


# ------------------------------------------------------------------ rules
# Each sheet: dict(desc=..., rules=[...]) evaluated in order, first match wins.
# rule kinds:
#   ('cells', [cells], terrain, other, confidence, note)
#   ('auto_boulder', refs, base, rocky, mass, lo, hi, confidence, note)
#       rock fraction < lo -> base, >= hi -> mass, else rocky
#   ('auto_blend', refs{material: (terrain, [ref cells])}, min_second, confidence, note)

SHEETS = {
    1: dict(desc='mixed base sheet: grass, gravel clearing, wood floor, void, pine forest', rules=[
        ('cells', [0, 40, 41, 60, 61], 'grass', '', 'high', ''),
        ('cells', rng((13, 16)), 'gravel', '', 'high', 'stony clearing centre'),
        ('cells', rng((1, 5), 12, 17, (24, 29), 48, 49), 'gravel', 'grass', 'high', 'gravel clearing edge'),
        ('cells', [6, 7, 18, 19], 'wood_floor', '', 'high', 'interior plank floor'),
        ('cells', [30, 31, 42, 43], 'void', '', 'high', 'black fill around interior rooms'),
        ('cells', rng((52, 55), (64, 67), (72, 79), (88, 91)), 'forest_canopy', '', 'high', 'pine forest roof'),
        ('cells', rng((84, 87)), 'forest_canopy', 'grass', 'high', 'forest edge: trunks over grass'),
    ]),
    2: dict(desc='grass with painted boulders and outcrops', rules=[
        ('auto_boulder', {'base': [T(2, 0), T(2, 19)], 'rock': [T(2, 15), T(2, 25), T(2, 76)]},
         'grass', 'grass_rocky', 'rock_mass', 0.08, 0.6, 'high', 'boulder sheet'),
    ]),
    3: dict(desc='grass with boulders and one large rock mound', rules=[
        ('auto_boulder', {'base': [T(3, 24), T(3, 26)], 'rock': [T(3, 51), T(3, 63), T(3, 64)]},
         'grass', 'grass_rocky', 'rock_mass', 0.08, 0.6, 'high', 'boulder/mound sheet'),
    ]),
    4: dict(desc='grass with a boulder cluster', rules=[
        ('auto_boulder', {'base': [T(4, 0), T(4, 5)], 'rock': [T(4, 28), T(4, 26)]},
         'grass', 'grass_rocky', 'rock_mass', 0.08, 0.6, 'high', 'boulder sheet'),
    ]),
    5: dict(desc='low earth ridges (ring and C shapes) on grass', rules=[
        ('auto_boulder', {'base': [T(5, 26), T(5, 38), T(5, 62)], 'rock': [T(5, 14), T(5, 15), T(5, 2)]},
         'grass', 'cliff_face', 'cliff_face', 0.22, 0.7, 'medium',
         'low ridge; small step in 3D. mixed cells are grass|cliff_face'),
    ]),
    6: dict(desc='main escarpment cliff: grass top, tall cliff body, gravel path at foot', rules=[
        ('cells', rng((0, 9)), 'cliff_face', 'grass', 'high', 'cliff top lip with grass above'),
        ('cells', rng((12, 21), (24, 33), (36, 45), (48, 57)), 'cliff_face', '', 'high', 'escarpment wall'),
        ('cells', rng((60, 67)), 'cliff_face', 'path', 'high', 'cliff foot with gravel path and grass below'),
        ('cells', [68, 69], 'path', 'grass', 'medium', 'gravel path around a grass hump at cliff foot'),
    ]),
    7: dict(desc='escarpment with a gravel pass cut through it', rules=[
        ('cells', [0, 1, 2, 3, 12, 15, 24, 27], 'cliff_face', 'grass', 'high', 'cliff lip / side with grass'),
        ('cells', [13, 14, 25, 26, 36, 37, 38, 39, 48, 49, 50, 51, 60, 63, 72, 75], 'cliff_face', '', 'high', 'cliff wall'),
        ('cells', [61, 62, 73, 74], 'path', 'cliff_face', 'high', 'gravel pass through the cliff'),
        ('cells', [84, 85, 86, 87], 'path', 'grass', 'high', 'pass exit onto grass'),
    ]),
    8: dict(desc='animated water (frame 1): lake with grass banks, islet', rules=[
        ('cells', [26, 27, 38, 39, 6, 7, 8, 9], 'water', '', 'high', 'animated water'),
        ('cells', [0, 5, 60, 65], 'grass', '', 'medium', 'bank corner, almost all grass'),
        ('cells', [1, 2, 3, 4, 12, 24, 36, 48, 17, 29, 41, 53, 61, 62, 63, 64], 'grass', 'water', 'high', 'grass bank above water'),
        ('cells', [13, 14, 15, 16, 25, 28, 37, 40, 49, 50, 51, 52], 'water', 'grass', 'high', 'water against bank'),
        ('cells', [19, 20, 31, 32], 'grass', 'water', 'high', 'grass islet in water'),
        ('cells', [18, 21, 30, 33, 42, 43, 44, 45], 'water', 'grass', 'medium', 'water around islet'),
    ]),
    9: dict(desc='animated water frame 2 (cells used directly as static water)', rules=[
        ('cells', [26, 27, 38, 39], 'water', '', 'high', 'static water (outside the animated range)'),
    ]),
    11: dict(desc='animated water frame 4', rules=[
        ('cells', [60], 'grass', '', 'low', 'single use; dark grass corner of a water frame sheet, likely an editor slip'),
    ]),
    14: dict(desc='sea and beach shoreline', rules=[
        ('auto_blend', {'water': ('water', [T(14, 0), T(14, 13)]), 'sand': ('sand', [T(14, 2), T(14, 15)])},
         0.10, 'high', 'shoreline sheet'),
    ]),
    15: dict(desc='sea / sand / flowered grass mixes, sand islet, shadowed corner', rules=[
        ('cells', [72, 73, 74, 75, 84, 85, 86, 87], 'sand', 'water', 'low',
         'darkened (shadow-faded) shore cells, 1-2 uses each'),
        ('cells', [28, 29, 30, 31], 'grass', 'water', 'high', 'grass bank with small cliff above water'),
        ('cells', [49, 61], 'grass', 'water', 'medium', 'grass with small bank against water'),
        ('auto_blend', {'water': ('water', [T(15, 0), T(15, 56)]), 'sand': ('sand', [T(15, 8), T(15, 44)]),
                        'grass': ('grass', [T(15, 4), T(15, 36), T(15, 50)])},
         0.10, 'medium', 'flowered grass / sand / sea mix'),
    ]),
    16: dict(desc='sand and flowered grass blends (dunes into meadow)', rules=[
        ('auto_blend', {'sand': ('sand', [T(16, 11), T(16, 44)]), 'grass': ('grass', [T(16, 60), T(16, 73)])},
         0.12, 'high', 'sand/meadow blend'),
    ]),
    17: dict(desc='bare dirt plot with grass banks', rules=[
        ('cells', [26, 27, 38, 39], 'dirt', '', 'high', 'dirt plot'),
        ('cells', [13, 14, 15, 16, 25, 28, 37, 40, 49, 50, 51, 52], 'dirt', 'grass', 'high', 'dirt plot edge'),
        ('cells', [0, 1, 2, 3, 4, 5, 12, 17, 24, 29, 36, 41, 48, 53, 60, 61, 62, 63, 64, 65], 'grass', 'dirt', 'high', 'bank around dirt plot'),
    ]),
    19: dict(desc='animated fire pit (frame 1) with mossy banks', rules=[
        ('cells', [14, 15, 26, 27, 38, 39, 6, 7, 8, 9], 'lava', '', 'high', 'animated fire'),
        ('cells', [2, 3, 25, 37, 50, 51, 28, 40, 52, 18, 21, 30, 33], 'lava', 'grass', 'high', 'fire against bank'),
        ('cells', [24, 36, 29, 41, 53, 62, 63, 64, 65, 19, 20, 31, 32], 'grass', 'lava', 'high', 'mossy bank beside fire'),
    ]),
    24: dict(desc='Darklands ground with ridge rings', rules=[
        ('auto_boulder', {'base': [T(24, 26), T(24, 38)], 'rock': [T(24, 14), T(24, 15), T(24, 31)]},
         'wasteland', 'cliff_face', 'cliff_face', 0.22, 0.7, 'medium',
         'Darklands ridge; mixed cells are wasteland|cliff_face'),
    ]),
    25: dict(desc='Darklands ground with a black pit ringed by rock', rules=[
        ('auto_blend', {'ground': ('wasteland', [T(25, 0), T(25, 60)]), 'rim': ('cliff_face', [T(25, 2), T(25, 3)]),
                        'pit': ('chasm', [T(25, 27), T(25, 39)])},
         0.12, 'medium', 'pit sheet'),
    ]),
    26: dict(desc='Darklands ground with boulders and outcrops', rules=[
        ('auto_boulder', {'base': [T(26, 0), T(26, 12)], 'rock': [T(26, 15), T(26, 25), T(26, 76)]},
         'wasteland', 'wasteland', 'rock_mass', 0.08, 0.6, 'high',
         'boulders on Darklands ground (scatter rock meshes)'),
    ]),
    27: dict(desc='Darklands ground with small boulders', rules=[
        ('auto_boulder', {'base': [T(27, 1), T(27, 12)], 'rock': [T(27, 6), T(27, 17), T(27, 44)]},
         'wasteland', 'wasteland', 'rock_mass', 0.08, 0.6, 'high', 'boulders on Darklands ground'),
    ]),
    28: dict(desc='Darklands ground with a boulder cluster', rules=[
        ('auto_boulder', {'base': [T(28, 0), T(28, 5)], 'rock': [T(28, 28), T(28, 26)]},
         'wasteland', 'wasteland', 'rock_mass', 0.08, 0.6, 'high', 'boulders on Darklands ground'),
    ]),
    29: dict(desc='snow with rock ridge rings', rules=[
        ('auto_boulder', {'base': [T(29, 26), T(29, 38)], 'rock': [T(29, 29), T(29, 41)]},
         'snow', 'cliff_face', 'cliff_face', 0.1, 0.7, 'medium', 'snow ridge; mixed cells are snow|cliff_face'),
    ]),
    30: dict(desc='snow, rock ridge and frozen lake / ice', rules=[
        ('auto_blend', {'snow': ('snow', [T(30, 0), T(30, 60)]), 'rock': ('cliff_face', [T(30, 14), T(30, 15)]),
                        'ice': ('ice', [T(30, 26), T(30, 39)])},
         0.12, 'medium', 'ice/snow/ridge sheet; the blue is read as ice (streaked, pale)'),
    ]),
    31: dict(desc='snow with boulders', rules=[
        ('auto_boulder', {'base': [T(31, 32), T(31, 44)], 'rock': [T(31, 45)]},
         'snow', 'snow', 'rock_mass', 0.08, 0.6, 'high', 'boulders on snow'),
    ]),
    32: dict(desc='snow with boulders', rules=[
        ('auto_boulder', {'base': [T(32, 15), T(32, 16), T(32, 17)], 'rock': [T(32, 4), T(32, 33)]},
         'snow', 'snow', 'rock_mass', 0.08, 0.6, 'high', 'boulders on snow'),
    ]),
    33: dict(desc='snow with a boulder cluster', rules=[
        ('auto_boulder', {'base': [T(33, 0), T(33, 5)], 'rock': [T(33, 28), T(33, 26)]},
         'snow', 'snow', 'rock_mass', 0.08, 0.6, 'high', 'boulders on snow'),
    ]),
    34: dict(desc='half-timbered wall with shingle roof (large tile-drawn building)', rules=[
        ('cells', rng((0, 7), (48, 53)), 'structure_facade', '', 'high', 'roof eave over timbered wall'),
        ('cells', rng((12, 19), (24, 31), (36, 43), (60, 65), (72, 77), (84, 89)), 'structure_facade', '', 'high', 'timbered wall (some with windows)'),
    ]),
    35: dict(desc='half-timbered wall with shingle roof, other facing', rules=[
        ('cells', rng((0, 7), (48, 51)), 'structure_facade', '', 'high', 'roof eave over timbered wall'),
        ('cells', rng((12, 19), (24, 31), (36, 43), (60, 63), (72, 75), (84, 87)), 'structure_facade', '', 'high', 'timbered wall (some with windows)'),
    ]),
    36: dict(desc='blue-grey flagstones (snow castle interior)', rules=[
        ('cells', [0, 1, 12, 13], 'stone_floor', '', 'medium', 'broken/rubbled flagstones'),
        ('cells', rng((2, 5), (14, 17), (26, 29), (38, 41)), 'stone_floor', '', 'high', 'flagstones'),
    ]),
    37: dict(desc='blue-grey flagstones (castle interiors)', rules=[
        ('cells', [26, 27, 38, 39], 'stone_floor', '', 'medium', 'broken/rubbled flagstones'),
        ('cells', rng((0, 5), (12, 17), 24, 25, 36, 37), 'stone_floor', '', 'high', 'flagstones'),
    ]),
    38: dict(desc='brown flagstones (dark)', rules=[
        ('cells', rng((2, 5), (14, 17), (26, 29), (38, 41)), 'stone_floor', '', 'high', 'flagstones'),
    ]),
    39: dict(desc='brown flagstones (courtyards, castle)', rules=[
        ('cells', [26, 27, 38, 39], 'stone_floor', '', 'medium', 'broken/rubbled flagstones'),
        ('cells', rng((0, 5), (12, 17), 24, 25, 36, 37), 'stone_floor', '', 'high', 'flagstones'),
    ]),
    40: dict(desc='cave: rugged floor with spiky rock walls', rules=[
        ('cells', [54, 55, 66, 67], 'cave_wall', '', 'high', 'solid spiky cave rock'),
        ('cells', [0, 5, 60, 65], 'cave_wall', 'cave_floor', 'high', 'room corner'),
        ('cells', [1, 2, 3, 4, 12, 24, 36, 48, 17, 29, 41, 53, 61, 62, 63, 64], 'cave_floor', 'cave_wall', 'high',
         'floor along the room wall'),
        ('cells', [19, 20, 31, 32], 'cave_floor', 'cave_wall', 'medium', 'floor around a rock pillar'),
        ('cells', rng((13, 16), (25, 28), (37, 40), (49, 52), (6, 9), 18, 21, 30, 33, (42, 45)), 'cave_floor', '',
         'high', 'cave floor'),
    ]),
    41: dict(desc='gravel road with grass corners and grass islands', rules=[
        ('cells', [42, 43, 55, 66, 67], 'grass', '', 'low', 'darkened cell (unused shading variant)'),
        ('auto_blend', {'path': ('path', [T(41, 4), T(41, 5), T(41, 16)]), 'grass': ('grass', [T(41, 30), T(41, 31), T(41, 0)])},
         0.2, 'high', 'road sheet'),
    ]),
}

# Per-cell corrections after reviewing the overlay sheets: tile_num -> (terrain, other, conf, note)
OVERRIDES = {
    T(2, 27): ('rock_mass', '', 'high', 'centre of the big outcrop; lighter rock texture fooled the colour split'),
}


def _apply(rule, num, cell):
    kind = rule[0]
    if kind == 'cells':
        _, cells, terr, other, conf, note = rule
        if cell in cells:
            return terr, other, conf, note
        return None
    if kind == 'auto_boulder':
        _, refs, base, rocky, mass, lo, hi, conf, note = rule
        f = material_fractions(num, refs)
        r = f['rock']
        if r < lo:
            terr, other = base, ''
        elif r >= hi:
            terr, other = mass, ''
        else:
            terr = rocky
            other = base if rocky != base and rocky in ('cliff_face',) else ''
        c = conf
        if abs(r - lo) < 0.03 or abs(r - hi) < 0.06:
            c = 'medium' if conf == 'high' else 'low'
        return terr, other, c, '%s (rock %.0f%%)' % (note, 100 * r)
    if kind == 'auto_blend':
        _, refs, min2, conf, note = rule
        f = material_fractions(num, {m: v[1] for m, v in refs.items()})
        order = sorted(f, key=lambda m: -f[m])
        a = order[0]
        terr = refs[a][0]
        other = ''
        c = conf
        if len(order) > 1 and f[order[1]] >= min2 and refs[order[1]][0] != terr:
            other = refs[order[1]][0]
            if abs(f[order[0]] - f[order[1]]) < 0.1:
                c = 'medium' if conf == 'high' else 'low'
        mix = ' '.join('%s %.0f%%' % (m, 100 * f[m]) for m in order if f[m] >= 0.02)
        return terr, other, c, '%s (%s)' % (note, mix)
    raise ValueError(kind)


def label(num):
    ts, cell = num // 128 + 1, num % 128
    if num in OVERRIDES:
        terr, other, conf, note = OVERRIDES[num]
        return dict(terrain=terr, transition=other, confidence=conf, notes='hand override: ' + note)
    sheet = SHEETS.get(ts)
    if sheet is None:
        return None
    for rule in sheet['rules']:
        r = _apply(rule, num, cell)
        if r:
            terr, other, conf, note = r
            return dict(terrain=terr, transition=other, confidence=conf,
                        notes=('%s; %s' % (sheet['desc'], note)).strip('; '))
    return None
