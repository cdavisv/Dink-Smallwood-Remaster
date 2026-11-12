"""Build the terrain game sets from CC0 scans.  python3 -I build_sets.py [Name ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from tl import *

# original Dink palette, mean sRGB per terrain class (tools/data/tile_classes.csv x tile sheets, weighted by use)
PAL = {'grass': (93, 117, 74), 'grass_rocky': (82, 101, 66), 'path': (139, 130, 115), 'dirt': (153, 108, 68),
       'sand': (227, 203, 156), 'cliff_face': (62, 45, 28), 'wasteland': (82, 102, 101), 'snow': (223, 235, 241),
       'stone_floor': (51, 52, 48), 'cave_floor': (73, 70, 50), 'cave_wall': (120, 113, 91), 'wood_floor': (105, 64, 36),
       'forest_canopy': (39, 52, 18), 'structure_facade': (89, 74, 57), 'gravel': (111, 107, 101)}

R = {}


def recipe(f):
    R[f.__name__] = f
    return f


@recipe
def MeadowTurf():
    T = 2.8
    a = rep(load('Grass004', 1.4), 2)
    b = match_colour(rep(load('Grass001', 1.4), 2, (0.17, 0.39)), a, 0.8)
    c = match_colour(fit(load('leafy_grass', 2.0), T, (0.31, 0.13)), a, 0.55)
    for x in (a, b):
        x['h'] = x['h'] * 2.5      # the lawn scans' displacement is flatter than their normals; a short sward is 2-3 cm
    s = hblend(a, b, cover(fbm(11, 0.5, 0.05, 1.3), 0.42, 0.6), 0.5)
    s = hblend(s, c, cover(fbm(12, 0.30, 0.025, 1.1), 0.20, 0.30) * window(), 1.0, 0.3)
    drift = fbm(13, 1.0, 0.2, 1.6)
    s['bc'] = s['bc'] * (1 + 0.09 * drift[..., None] * np.array([1.0, 0.6, 0.9], np.float32))
    grade(s, PAL['grass'], hue=0.55, mean_luma=96, sat=0.92, contrast=1.05)
    return write_set('MeadowTurf', s, T, ['grass'], seed=1, rough_gain=1.0, rough_bias=0.2,
                     note='ambientCG Grass004 (2x2) height-blended with Grass001 (2x2, shifted) and Poly Haven leafy_grass (true scale, small worn patches with dry blades and leaf litter) under periodic masks; graded toward the original grass palette',
                     weaknesses='no distinct clover leaves; soil shows only inside the worn patches; the 1.4 m lawn period can still be found in the lush areas of a flat-lit 4x4 view; relief is a few centimetres at most by design (3D tufts stand on it)')


@recipe
def WildGrass():
    T = 4.0
    a = rep(load('sparse_grass', 2.0), 2)
    b = match_colour(fit(load('Grass001', 1.4), T, (0.23, 0.41)), a, 0.93)
    c = match_colour(fit(load('leafy_grass', 2.0), T, (0.11, 0.37)), a, 0.85)
    b['h'] = b['h'] * 2.5
    s = hblend(a, b, cover(fbm(21, 0.30, 0.03, 1.1), 0.36, 0.5) * window(), 1.2, 0.5)
    s = hblend(s, c, cover(fbm(22, 0.25, 0.03, 1.1), 0.14, 0.4) * window(), 1.2, 0.4)
    drift = fbm(23, 1.0, 0.2, 1.6)
    s['bc'] = s['bc'] * (1 + 0.10 * drift[..., None] * np.array([1.0, 0.7, 0.8], np.float32))
    grade(s, PAL['grass_rocky'], hue=0.8, mean_luma=82, sat=0.95, contrast=1.05)
    return write_set('WildGrass', s, T, ['grass', 'grass_rocky', 'forest_canopy'], seed=2, status='interim',
                     note='Poly Haven sparse_grass (2x2, long dry-strawed grass) with small patches of ambientCG Grass001 and Poly Haven leafy_grass at true scale, colour-matched; darker and rougher than MeadowTurf',
                     weaknesses='reads as rough pasture rather than knee-high grass: length must come from 3D tufts; the 2 m period of the base scan is findable at 4x4')


@recipe
def EarthPath():
    T = 4.0
    a = rep(load('dirt_floor', 2.07), 2)
    b = rep(load('rocky_trail', 2.0), 2, (0.27, 0.44))
    b = match_colour(b, a, 0.55)
    s = hblend(a, b, cover(fbm(31, 0.6, 0.04, 1.3), 0.38, 0.4), 0.9)
    # footprint / rut scale undulation: dished centre line and shallow hollows, in height, AO and a damp darkening
    und = fbm(32, 0.5, 0.08, 1.8)
    s['h'] = s['h'] + und * 0.006
    damp = smooth(0.3, 1.6, -und)
    s['bc'] = s['bc'] * (1 - 0.16 * damp[..., None])
    s['rough'] = s['rough'] - 0.06 * damp
    s['n'] = s['n'] + (normal_from_height(und * 0.006, T / N) - np.array([0, 0, 1], np.float32))
    grade(s, PAL['path'], hue=0.45, mean_luma=122, sat=0.9, contrast=1.08)
    return write_set('EarthPath', s, T, ['path', 'dirt', 'gravel'], seed=3,
                     note='Poly Haven dirt_floor (2x2, compacted earth with dry crazing) height-blended with rocky_trail (2x2, embedded stones and grit) plus a periodic footprint-scale undulation with damp hollows',
                     weaknesses='no explicit wheel ruts or readable footprints (kept direction-free so it tiles under any path shape); stones are at most a few centimetres')


@recipe
def TransitionDirt():
    T = 2.0
    a = load('dirt', 2.0); a['used'] = [('dirt', 'polyhaven', 1)]
    b = rep(load('rocky_trail', 2.0), 1, (0.37, 0.21))
    b = match_colour(b, a, 0.85)
    s = hblend(a, b, cover(fbm(41, 0.5, 0.04, 1.3), 0.22, 0.35), 1.0)
    grade(s, PAL['dirt'], hue=0.35, mean_luma=92, sat=0.9, contrast=1.1)
    return write_set('TransitionDirt', s, T, ['dirt', 'path', 'grass'], seed=4,
                     note='Poly Haven dirt (fine dark soil) with rocky_trail grit patches; mid-value brown chosen to sit between MeadowTurf and EarthPath in a height-blended edge',
                     weaknesses='plain by design; little relief (about a centimetre)')


@recipe
def ForestFloor():
    T = 3.0
    a = rep(load('forest_leaves_04', 1.5), 2)
    b = fit(load('forrest_ground_03', 2.0), T, (0.19, 0.33))
    c = rep(load('forest_leaves_02', 3.0), 1, (0.41, 0.07))
    c['h'] = c['h'] * 0.45                       # the moss cushions of the scan stand 10 cm proud: too much of a landmark
    c['n'] = c['n'] * np.array([0.6, 0.6, 1.0], np.float32)
    b = match_colour(b, a, 0.75)
    c = match_colour(c, a, 0.3)
    # greener moss: push the yellow-green of the scan toward a deeper green where it is green at all
    g = c['bc']
    green = smooth(0.0, 0.06, g[..., 1] - 0.5 * (g[..., 0] + g[..., 2]) * 1.05)
    c['bc'] = g * (1 - green[..., None]) + g * np.array([0.62, 0.95, 0.55], np.float32) * green[..., None]
    s = hblend(a, c, cover(fbm(52, 0.8, 0.06, 1.4), 0.40, 0.35), 0.8)
    s = hblend(s, b, cover(fbm(51, 0.35, 0.03, 1.2), 0.20, 0.25) * window(), 1.6, 0.5)
    drift = fbm(53, 1.0, 0.25, 1.6)
    s['bc'] = s['bc'] * (1 + 0.12 * drift[..., None])
    grade(s, (92, 78, 48), hue=0.6, mean_luma=74, sat=0.8, contrast=1.05)
    return write_set('ForestFloor', s, T, ['forest_canopy', 'grass'], seed=5,
                     note='Poly Haven forest_leaves_04 (2x2: twigs, needles, leaf litter) blended with forest_leaves_02 (1x: moss, sticks, leaves; relief halved) and small patches of forrest_ground_03 (true scale pine needle mat); desaturated and darkened for shade',
                     weaknesses='no cones; moss is sparse and olive rather than deep green; the litter layer repeats at 1.5 m under the 3 m moss pattern')


@recipe
def DrySand():
    T = 3.0
    src = load('sand_01', 1.5)
    src['h'] = src['h'] * 0.7
    src['n'] = src['n'] * np.array([0.8, 0.8, 1.0], np.float32)
    a = rep(src, 2)
    b = rep(rot90(src), 2, (0.37, 0.21))
    s = hblend(a, b, cover(fbm(64, 0.6, 0.06, 1.4), 0.5, 0.7), 0.5, 0.5)
    drift = fbm(61, 1.0, 0.2, 1.7)
    s['bc'] = s['bc'] * (1 + 0.05 * drift[..., None])
    grade(s, PAL['sand'], hue=0.85, mean_luma=186, sat=0.95, contrast=0.9)
    return write_set('DrySand', s, T, ['sand'], seed=6,
                     note='Poly Haven sand_01 (scuffed dry beach sand with small debris), 2x2, height-blended with a quarter-turned, shifted copy of itself under a 3 m mask so the 1.5 m scan period is broken; relief eased; graded to the original warm sand',
                     weaknesses='one scan only: the same debris cluster appears a few times per tile in two orientations; no wind ripples')


@recipe
def WetSand():
    T = 2.0
    a = load('damp_beach_sand', 2.0); a['used'] = [('damp_beach_sand', 'polyhaven', 1)]
    wet = cover(fbm(71, 1.0, 0.25, 2.0), 0.5, 2.2)
    a['bc'] = a['bc'] * (1 - 0.07 * wet[..., None])
    a['rough'] = a['rough'] * (1 - 0.22 * wet)
    grade(a, PAL['sand'], hue=0.8, mean_luma=120, sat=0.85)
    return write_set('WetSand', a, T, ['sand', 'water'], seed=7, rough_gain=0.8,
                     note='Poly Haven damp_beach_sand with periodic wet sheen patches (darker, lower roughness); same hue as DrySand at lower value so the shoreline blend is only a value and gloss change',
                     weaknesses='very plain; no shells or drainage rills (shells are the 3D scatter)')


@recipe
def ShingleBeach():
    T = 2.16
    a = load('ganges_river_pebbles', 2.16); a['used'] = [('ganges_river_pebbles', 'polyhaven', 1)]
    grade(a, (150, 140, 124), hue=0.5, mean_luma=128, sat=0.9)
    return write_set('ShingleBeach', a, T, ['sand', 'gravel'], seed=8,
                     note='Poly Haven ganges_river_pebbles, warmed slightly toward the sand so pebble banks sit in it',
                     weaknesses='single scan: the few bright white cobbles are repeating landmarks at 4x4; use the Macro mask to tint')


@recipe
def CliffRock():
    T = 2.7
    a = load('rock_face_03', 2.7); a['used'] = [('rock_face_03', 'polyhaven', 1)]
    grade(a, (98, 82, 64), hue=0.75, mean_luma=92, sat=0.8, contrast=1.1)
    return write_set('CliffRock', a, T, ['cliff_face', 'rock_mass'], seed=9,
                     note='Poly Haven rock_face_03 (fractured rock face), moved from orange toward the dark grey-brown of the original cliffs',
                     weaknesses='single scan at 2.7 m: one long straight joint and the large flake near the tile centre repeat on tall cliffs (visible in the 4x4 check); needs the Macro mask and mesh-scale breakup')


for name in list(R):
    pass

if __name__ == '__main__':
    import build_sets2  # noqa: more recipes register themselves
    import build_sets3  # noqa: round 2, replaces earlier recipes of the same name
    want = sys.argv[1:] or list(R)
    for w in want:
        print('==', w)
        R[w]()
    write_manifest()
