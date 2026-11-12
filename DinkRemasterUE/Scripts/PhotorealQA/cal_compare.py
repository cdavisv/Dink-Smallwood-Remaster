#!/usr/bin/env python3
"""cal_compare.py <tag> [shots...]: foliage statistics of the engine captures (cal/<tag>_<shot>.png, central 3:2 crop)
against the Blender review renders. Foliage = pixels of the shot's rectangle that are neither sky nor ground-plane
colour (green dominant over blue). Prints mean RGB, luminance percentiles, saturation and the green/red ratio."""
import sys, os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); CAL = os.path.join(HERE, '..', '..', 'Saved', 'PhotorealPass', 'lighting', 'cal')
REV = os.path.join(HERE, '../../SourceAssets/Art/PhotorealPass/Vegetation/Review')
REF = {'oak': ('SM_Veg_Oak_Large_01_game.png', (0.12, 0.0, 0.9, 0.42)), 'pine': ('SM_Veg_Pine_Large_01_game.png', (0.25, 0.0, 0.78, 0.4)),
       'willow': ('SM_Veg_Willow_01_game.png', (0.1, 0.0, 0.9, 0.6)), 'bush': ('SM_Veg_Bush_close.png', (0.0, 0.2, 1.0, 0.9)),
       'grassgrid': ('GrassPatch_carpet_close.png', (0.0, 0.45, 1.0, 1.0)), 'carpet': ('GrassPatch_carpet_close.png', (0.0, 0.45, 1.0, 1.0)),
       'carpetgame': ('GrassPatch_carpet_game.png', (0.2, 0.35, 0.8, 0.95))}
def load(path, crop32):
    im = Image.open(path).convert('RGB')
    if crop32:
        w, h = im.size; cw = int(h * 1.5); im = im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    return im
def stats(im, rect, sky_only_exclude):
    w, h = im.size
    a = np.asarray(im.crop((int(rect[0] * w), int(rect[1] * h), int(rect[2] * w), int(rect[3] * h)))).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = ~((b > g) & (b > r * 0.95))          # not sky
    if not sky_only_exclude: m &= (g > b * 1.15)
    p = a[m]
    lum = p @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mx, mn = p.max(1), p.min(1); sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-4), 0)
    return dict(n=int(m.sum()), cover=float(m.mean()), mean=(p.mean(0) * 255).round(0).tolist(), lum=[round(float(np.percentile(lum, q)) * 255) for q in (5, 25, 50, 75, 95)],
                sat=round(float(sat.mean()), 3), g_r=round(float(p[:, 1].mean() / max(p[:, 0].mean(), 1e-4)), 3))
import glob
tag = sys.argv[1]; shots = sys.argv[2:] or list(REF)
for s in shots:
    ref_name, rect = REF[s]
    engs = sorted(glob.glob(os.path.join(CAL, f'{tag}_{s}.png')) + glob.glob(os.path.join(CAL, f'{tag}_{s}_*.png')))
    if not engs: continue
    a = stats(load(os.path.join(REV, ref_name), False), rect, False)
    print(f'{s:10s} {"ref":12s} cover {a["cover"]:.2f} mean {a["mean"]} lum5/25/50/75/95 {a["lum"]} sat {a["sat"]} g/r {a["g_r"]}')
    for eng in engs:
        b = stats(load(eng, True), rect, False)
        print(f'{"":10s} {os.path.basename(eng)[len(tag) + len(s) + 2:-4] or "eng":12s} cover {b["cover"]:.2f} mean {b["mean"]} lum5/25/50/75/95 {b["lum"]} sat {b["sat"]} g/r {b["g_r"]}')
