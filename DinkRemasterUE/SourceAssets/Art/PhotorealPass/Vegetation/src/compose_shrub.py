"""python3 -I compose_shrub.py : work/shrub_atlas_* -> Export/Textures/T_Veg_Shrub_{BC,N,ORM,SSS}.png, then grade the tiles
(column 0 of rows 0-1 sunlit, column 3 of rows 0-1 dark interior) so a bush gets value depth from its own texture."""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from texlib import *
import compose_atlas
compose_atlas.compose('Shrub', 'shrub_atlas', 1.5)
OUT = os.path.join(HERE, '..', 'Export', 'Textures')
s2l = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
GRADE = {(0, 0): (0.98, 0.96, 0.74), (0, 3): (0.40, 0.50, 0.52), (1, 0): (0.96, 0.96, 0.76), (1, 3): (0.42, 0.52, 0.54),
         (0, 1): (0.74, 0.80, 0.78), (0, 2): (0.64, 0.72, 0.70), (1, 1): (0.74, 0.80, 0.78), (1, 2): (0.64, 0.72, 0.72),
         (2, 0): (0.62, 0.70, 0.68), (2, 1): (0.62, 0.70, 0.68), (3, 0): (0.78, 0.80, 0.76), (3, 1): (0.78, 0.80, 0.76), (3, 2): (0.70, 0.76, 0.72), (3, 3): (0.70, 0.76, 0.72)}
for suf, mode in (('BC', 'RGBA'), ('SSS', 'RGB')):
    p = f'{OUT}/T_Veg_Shrub_{suf}.png'; a = np.asarray(Image.open(p).convert(mode)).astype(np.float64) / 255
    rgb = s2l(a[..., :3]); h, w = rgb.shape[:2]; q = h // 4
    for (r, c), m in GRADE.items():
        t = rgb[r * q:(r + 1) * q, c * q:(c + 1) * q]
        if m[0] < 0.6: g = t.mean(-1, keepdims=True); t = g + (t - g) * 0.8
        rgb[r * q:(r + 1) * q, c * q:(c + 1) * q] = t * np.array(m)
    save_rgb(p, srgb8(np.clip(rgb, 0, 1)), lin8(a[..., 3]) if mode == 'RGBA' else None)
print('shrub graded')
