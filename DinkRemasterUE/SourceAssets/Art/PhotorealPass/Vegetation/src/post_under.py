"""Grade the understory atlas after composing: the grass-clump row (v 0.3-0.5) is toned down to a meadow green. python3 -I post_under.py"""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from texlib import *
import compose_atlas
compose_atlas.compose('Understory', 'under_atlas', 1.5)
OUT = os.path.join(HERE, '..', 'Export', 'Textures')
s2l = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
for suf, mode in (('BC', 'RGBA'), ('SSS', 'RGB')):
    p = f'{OUT}/T_Veg_Understory_{suf}.png'; a = np.asarray(Image.open(p).convert(mode)).astype(np.float64) / 255
    rgb = s2l(a[..., :3]); h = rgb.shape[0]; r0, r1 = int(h * 0.5), int(h * 0.7)
    g = rgb[r0:r1]; yellow = np.clip((g[..., 0] - g[..., 1] * 0.8) * 6, 0, 1)[..., None]      # dry blades stay straw, green ones go darker
    rgb[r0:r1] = g * (np.array([0.42, 0.52, 0.46]) * (1 - yellow) + np.array([0.62, 0.55, 0.42]) * yellow)
    save_rgb(p, srgb8(np.clip(rgb, 0, 1)), lin8(a[..., 3]) if mode == 'RGBA' else None)
print('understory graded')
