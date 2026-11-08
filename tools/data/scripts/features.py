"""Per-tile colour features used to assist (not replace) hand labelling."""
import numpy as np
from PIL import Image
import dinkdata as d

_cache = {}


def _ts(ts):
    if ts not in _cache:
        _cache[ts] = np.asarray(Image.open(d.tileset_path(ts)).convert('RGB')).astype(int)
    return _cache[ts]


def tile_pixels(num):
    ts, cell = d.tile_of(num)
    a = _ts(ts)
    x, y = (cell % 12) * 50, (cell // 12) * 50
    if x + 50 > a.shape[1] or y + 50 > a.shape[0]:
        return None
    return a[y:y + 50, x:x + 50]


def features(num):
    p = tile_pixels(num)
    if p is None:
        return None
    r, g, b = p[..., 0], p[..., 1], p[..., 2]
    mx = p.max(axis=2); mn = p.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    lum = (r * 299 + g * 587 + b * 114) / 1000
    n = float(r.size)
    f = {
        'green': ((g > r) & (g > b) & (sat > 0.15)).sum() / n,
        'blue': ((b > r + 15) & (b >= g) & (sat > 0.15)).sum() / n,
        'sand': ((r > 170) & (g > 150) & (b < g) & (r >= g) & (sat > 0.12)).sum() / n,
        'white': ((lum > 200) & (sat < 0.15)).sum() / n,
        'grey': ((sat < 0.22) & (lum > 25) & (lum <= 200)).sum() / n,
        'brown': ((r > g) & (g > b) & (sat > 0.25) & (lum < 170)).sum() / n,
        'black': (lum <= 25).sum() / n,
        'lum': float(lum.mean()),
    }
    return f


def base_fraction(num, ref_num, thresh=48):
    """Fraction of pixels close (RGB distance) to the mean colour of a reference
    'pure base material' tile. Used to split grass / grass+boulders / rock mass."""
    p = tile_pixels(num)
    ref = tile_pixels(ref_num)
    if p is None or ref is None:
        return None
    m = ref.reshape(-1, 3).mean(axis=0)
    dist = np.sqrt(((p - m) ** 2).sum(axis=2))
    return float((dist < thresh).mean())


def material_fractions(num, refs):
    """refs: {material: [ref tile nums]}. Each pixel is assigned to the material
    whose reference mean colour is nearest; returns {material: fraction}."""
    p = tile_pixels(num)
    if p is None:
        return None
    names = list(refs)
    cents = []
    for m in names:
        px = np.concatenate([tile_pixels(r).reshape(-1, 3) for r in refs[m]])
        cents.append(px.mean(axis=0))
    cents = np.array(cents)
    # light blur to reduce texture noise
    q = p.astype(float)
    q = (q + np.roll(q, 1, 0) + np.roll(q, -1, 0) + np.roll(q, 1, 1) + np.roll(q, -1, 1)) / 5
    dist = ((q[:, :, None, :] - cents[None, None, :, :]) ** 2).sum(axis=3)
    lab = dist.argmin(axis=2)
    return {m: float((lab == i).mean()) for i, m in enumerate(names)}
