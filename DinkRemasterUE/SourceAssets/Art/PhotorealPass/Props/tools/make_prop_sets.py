"""Tiling BC/N/ORM/H sets for the props, with the Terrain set library (Terrain/tools/tl.py), same set.json contract.
python3 -I make_prop_sets.py [Name ...]   -> Props/Sets/<Name>/"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
PP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PP, 'Terrain', 'tools'))
import numpy as np
import tl
from tl import *
tl.TERRAIN = os.path.join(PP, 'Props', 'Sets')


def one(aid, size, span=0.0015):
    """tl.load for the Poly Haven sets that came as separate _rough / _ao files (no _arm): height scaled to `span` metres"""
    import glob
    d = glob.glob(os.path.join(tl.TP, '*', aid))[0]; fs = glob.glob(d + '/*')
    pick = lambda k: [f for f in fs if k in os.path.basename(f)][0]
    if not [f for f in fs if '_rough_' in os.path.basename(f)]:
        s = load(aid, size); s['used'] = [(aid, s['source'], 1)]; return s
    S = {'id': aid, 'source': os.path.basename(os.path.dirname(d)), 'size_m': size}
    S['bc'] = srgb2lin(tl._open(pick('_diff'), 'RGB'))
    n = tl._open(pick('_nor_gl'), 'RGB') * 2 - 1; S['n'] = n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9)
    S['ao'] = tl._open(pick('_ao_'), 'L'); S['rough'] = tl._open(pick('_rough_'), 'L')
    h = tl._open(pick('_disp'))
    h = h[..., 0] if h.ndim == 3 else h
    S['h'] = (h - h.mean()) / (h.max() - h.min() + 1e-9) * span
    S['used'] = [(aid, S['source'], 1)]; return S


def flatten(S, sigma=220, amount=0.75):
    S['bc'] = np.clip(S['bc'], 0.0, None); l = luma(S['bc']); lo = gblur(l, sigma)
    S['bc'] = S['bc'] * ((l.mean() / np.maximum(lo, 1e-4)) ** amount)[..., None]; return S


def Hessian():
    a = flatten(one('hessian_230', 0.3), 200, 0.7)
    # handling: darker greasy patches, paler rubbed threads on the high weave
    h = a['h']; hn = (h - h.min()) / (h.max() - h.min() + 1e-9)
    st = fbm(11, 0.25, 0.03, 1.3)
    a['bc'] = a['bc'] * (1 - 0.16 * np.clip(st, 0, 1))[..., None] * (0.86 + 0.28 * smooth(0.4, 0.8, hn))[..., None]
    a['rough'] = np.clip(a['rough'] * 0.2 + 0.78 + 0.06 * st, 0, 1)
    grade(a, (150, 128, 92), hue=0.85, mean_luma=120, sat=0.85, contrast=1.08)
    return write_set('Hessian', a, 0.3, ['prop_cloth'], seed=201, status='interim',
                     note='Poly Haven hessian_230 (jute sackcloth) flattened, rubbed pale on the high threads, greasy handling patches, graded to a dull jute; sack colours (olive, madder red) are material tints',
                     weaknesses='0.3 m scan period: repeats on a 0.9 m sack are hidden only by folds and vertex-colour dirt')


def Linen():
    a = flatten(one('rough_linen', 0.4), 200, 0.7)
    st = fbm(21, 0.3, 0.04, 1.3)
    a['bc'] = a['bc'] * (1 - 0.08 * np.clip(st, 0, 1))[..., None]
    a['rough'] = np.clip(a['rough'] * 0.25 + 0.72, 0, 1)
    grade(a, (196, 188, 168), hue=0.9, mean_luma=176, sat=0.6, contrast=1.05)
    return write_set('Linen', a, 0.4, ['prop_cloth'], seed=202, status='interim',
                     note='Poly Haven rough_linen flattened and graded to unbleached linen; blanket and ticking colours are material tints',
                     weaknesses='one scan; no printed or woven pattern')


def Earthenware():
    # wheel-thrown glazed earthenware: fine horizontal throwing rings (rows of the set run round the pot), glaze pooling, pinholes,
    # crazing; the glaze is worn through to the biscuit where the rust mask of Poly Haven rusty_metal_02 says so
    s = one('rusty_metal_02', 0.5)
    x_ = s['bc'][..., 0] - s['bc'][..., 2]; lo_, hi_ = np.percentile(x_, [86, 97]); wear = smooth(float(lo_), float(hi_), x_)        # only the rustiest tenth is worn through
    rings = fbm(31, 0.5, 0.004, 1.0, aniso=(1.0, 0.04)) * 0.00014 + fbm(32, 0.08, 0.01, 1.2) * 0.00004
    pin = np.clip(fbm(33, 0.006, 0.002, 1.0) - 0.9, 0, 1) * 3
    craze = np.clip(1 - np.abs(fbm(34, 0.03, 0.004, 1.4)) * 90, 0, 1) * 0.3        # hairline crazing only
    pool = fbm(35, 0.3, 0.03, 1.4)
    base = np.array([0.56, 0.55, 0.53], np.float32) * (1 + 0.07 * pool)[..., None] * (1 - 0.35 * craze)[..., None] * (1 - 0.5 * np.clip(pin, 0, 1))[..., None]
    bisc = np.array([0.50, 0.33, 0.22], np.float32) * (0.75 + 0.5 * luma(s['bc'])[..., None] * 2)
    k = (wear * 0.5)[..., None]
    s['bc'] = (base * (1 - k) + bisc * k).astype(np.float32)
    s['h'] = (rings - wear * 0.00012 - pin * 0.00006).astype(np.float32)
    s['n'] = normal_from_height(s['h'], 0.5 / N).astype(np.float32)
    s['rough'] = np.clip(0.1 + 0.6 * wear + 0.1 * craze + 0.06 * pool + 0.3 * np.clip(pin, 0, 1), 0.05, 1).astype(np.float32)
    s['ao'] = np.ones_like(wear)
    return write_set('Earthenware', s, 0.5, ['prop_ceramic'], seed=203, status='interim',
                     note='glazed earthenware: procedural throwing rings, glaze pooling, pinholes and crazing on a pale neutral glaze (the glaze colour is the material tint); worn through to red biscuit where the rust mask of Poly Haven rusty_metal_02 places it',
                     weaknesses='procedural apart from the wear mask; dielectric glaze, no clear-coat layer')


R = {f.__name__: f for f in (Hessian, Linen, Earthenware)}
for n in (sys.argv[1:] or list(R)):
    R[n]()
