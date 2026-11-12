"""Tiling BC/N/ORM/H sets for the exterior structures, from CC0 scans, with the Terrain set library (Terrain/tools/tl.py).
python3 -I make_sets.py [Name ...]   -> Structures/Sets/<Name>/ (same set.json contract as Terrain/)"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
PP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PP, 'Terrain', 'tools'))
import numpy as np
import tl
from tl import *
tl.TERRAIN = os.path.join(PP, 'Structures', 'Sets')


def one(aid, size):
    s = load(aid, size); s['used'] = [(aid, s['source'], 1)]; return s


def flatten(S, sigma=220, amount=0.75):
    S['bc'] = np.clip(S['bc'], 0.0, None); l = luma(S['bc']); lo = gblur(l, sigma)
    S['bc'] = S['bc'] * ((l.mean() / np.maximum(lo, 1e-4)) ** amount)[..., None]; return S


def OakWeathered():
    a = flatten(rot90(one('old_planks_02', 2.0)), 200, 0.6)       # grain along U, boards as rows
    # silver the raised grain, darken the checks and board joints
    h = a['h']; hn = (h - h.min()) / (h.max() - h.min() + 1e-9)
    hi = smooth(0.55, 0.85, hn)[..., None]; lo = (1 - smooth(0.15, 0.45, hn))[..., None]
    l = luma(a['bc'])[..., None]
    a['bc'] = a['bc'] * (1 - 0.45 * hi) + (l * np.array([1.12, 1.10, 1.06], np.float32)) * 0.45 * hi * 1.25
    a['bc'] = a['bc'] * (1 - 0.45 * lo)
    a['rough'] = np.clip(a['rough'] + 0.08 * hi[..., 0], 0, 1)
    grade(a, (118, 102, 84), hue=0.8, mean_luma=92, sat=0.62, contrast=1.12)
    return write_set('OakWeathered', a, 2.0, ['structure_facade'], seed=71, status='interim',
                     note='Poly Haven old_planks_02 quarter-turned (grain along U, boards as rows), raised grain silvered, checks and joints darkened, graded to a grey-brown weathered oak',
                     weaknesses='sawn boards, not hewn baulks: adze facets, checks and pegs come from the geometry')


def Thatch():
    s = one('thatch_roof_angled', 0.54)
    a = rep(s, 2); a['used'] = [('thatch_roof_angled', 'polyhaven', 2)]
    b = rep(s, 2, (0.37, 0.19))
    m = cover(fbm(81, 0.5, 0.05, 1.3, aniso=(1.0, 0.35)), 0.5, 0.6)
    a = hblend(a, b, m, 0.5, 0.5); a['used'] = [('thatch_roof_angled', 'polyhaven', 2)]
    a['h'] = a['h'] * 1.0
    # streaks down the slope: darker, wetter runs and paler bleached runs
    st = fbm(82, 0.9, 0.04, 1.2, aniso=(0.12, 1.0))
    a['bc'] = a['bc'] * (1 + 0.22 * st[..., None] * np.array([1.0, 0.9, 0.7], np.float32))
    grade(a, (168, 132, 70), hue=0.9, mean_luma=112, sat=0.95, contrast=1.1)
    return write_set('Thatch', a, 1.08, ['structure_facade'], seed=72, status='interim',
                     note='Poly Haven thatch_roof_angled (0.54 m scan of weathered water-reed thatch, stalks down V) 2x2, blended with a shifted copy under an anisotropic mask, slope streaks, graded to the dull gold of the original roofs (weathered grey and fresh straw are vertex-colour blends in the material)',
                     weaknesses='0.54 m scan period is findable close up; butt ends of the courses are geometry, not texture')


def Fieldstone():
    a = flatten(one('old_stone_wall', 2.0), 200, 0.6)
    grade(a, (150, 143, 122), hue=0.75, mean_luma=128, sat=0.8, contrast=1.08)
    return write_set('Fieldstone', a, 2.0, ['structure_facade'], seed=73, status='interim',
                     note='Poly Haven old_stone_wall (random rubble in lime mortar), flattened, graded to the pale grey-buff of the original cottage walls',
                     weaknesses='one scan at its true 2 m period')


def CastleAshlar():
    a = flatten(one('rock_wall_08', 1.8), 200, 0.6)
    a = selfblend(a, 1, 93, quarter_turns=0, shift=(0.43, 0.27), frac=0.45, soft=0.5); a['used'] = [('rock_wall_08', 'polyhaven', 1)]
    st = fbm(91, 1.0, 0.1, 1.5, aniso=(0.25, 1.0))
    a['bc'] = a['bc'] * (1 + 0.10 * st[..., None] * np.array([1.0, 0.85, 0.6], np.float32))
    a['h'] = a['h'] * 1.83; a['n'] = normal_from_height(a['h'], 3.3 / N).astype(np.float32)
    grade(a, (116, 118, 100), hue=0.8, mean_luma=104, sat=0.85, contrast=1.1)
    return write_set('CastleAshlar', a, 3.3, ['structure_facade'], seed=74, status='interim',
                     note='Poly Haven rock_wall_08 (coursed squared blocks, worn arrises, lost mortar) height-blended with a shifted copy of itself to break its period, laid 1.83x larger than life (tile 3.3 m) so its 0.3 m blocks stand at the 0.55 m courses of the original castle; relief and normals rescaled to match; faint ochre run-off streaks; graded grey-green',
                     weaknesses='enlarged scan: texel density 620 px/m and the stone grain is 1.8x coarse close up; one scan')


def WroughtIron():
    s = one('rusty_metal_02', 1.0)
    l = luma(s['bc']); rust = smooth(0.3, 0.6, s['bc'][..., 0] - s['bc'][..., 2])      # orange areas
    ham = fbm(95, 0.06, 0.012, 1.2) * 0.0006 + fbm(96, 0.4, 0.1, 1.5) * 0.0004
    base = np.array([0.028, 0.026, 0.025], np.float32) * (1 + 0.35 * fbm(97, 0.2, 0.01, 1.1))[..., None]
    rc = np.array([0.16, 0.065, 0.028], np.float32) * (0.6 + 0.8 * l[..., None])
    k = (rust * 0.35)[..., None]
    s['bc'] = (base * (1 - k) + rc * k).astype(np.float32)
    s['h'] = (ham + rust * 0.0002).astype(np.float32)
    s['n'] = normal_from_height(s['h'], 1.0 / N).astype(np.float32)
    s['rough'] = (0.42 + 0.4 * rust + 0.1 * fbm(98, 0.1, 0.01, 1.2)).astype(np.float32)
    s['ao'] = np.ones_like(l)
    return write_set('WroughtIron', s, 1.0, ['structure_facade'], seed=75, status='interim',
                     note='forge-black iron: procedural hammered relief and scale, rust patches placed by the rust mask of Poly Haven rusty_metal_02',
                     weaknesses='dielectric black oxide (metallic 0); no pitting')


def FieldBoulder():
    a = flatten(one('rock_face', 2.0), 160, 0.8)
    b = match_colour(fit(load('rock_face_04', 2.0), 2.0, (0.3, 0.2)), a, 0.9)
    a = hblend(a, b, cover(fbm(101, 0.6, 0.05, 1.3), 0.4, 0.5), 0.6); a['used'] = [('rock_face', 'polyhaven', 1), ('rock_face_04', 'polyhaven', 1)]
    grade(a, (128, 124, 112), hue=0.85, mean_luma=112, sat=0.7, contrast=1.05)
    return write_set('FieldBoulder', a, 2.0, ['structure_facade'], seed=76, status='interim',
                     note='Poly Haven rock_face height-blended with rock_face_04, flattened, graded to a weathered grey field stone',
                     weaknesses='projected by dominant axis on the boulders: seams hide under moss and smooth shading only partly')


R = {f.__name__: f for f in (FieldBoulder, OakWeathered, Thatch, Fieldstone, CastleAshlar, WroughtIron)}
for n in (sys.argv[1:] or list(R)):
    R[n]()
