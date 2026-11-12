"""Grade the oak leaf atlas tiles so the crown gets value variation: tile (0,1) sunlit yellow-green, tile (1,0) dark blue-green interior.
Recomposes from the render passes first, so it is repeatable. python3 -I make_oak_variation.py"""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from texlib import *
import compose_atlas
compose_atlas.compose('OakLeaves', 'oak_atlas', 1.3)
OUT = os.path.join(HERE, '..', 'Export', 'Textures')
s2l = lambda a: np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
for suf, mode in (('BC', 'RGBA'), ('SSS', 'RGB')):
    p = f'{OUT}/T_Veg_OakLeaves_{suf}.png'; a = np.asarray(Image.open(p).convert(mode)).astype(np.float64) / 255
    rgb = s2l(a[..., :3]); h, w = rgb.shape[:2]
    rgb[:h // 2, w // 2:] *= np.array([1.30, 1.18, 0.78])          # sunlit: lighter, yellower
    d = rgb[h // 2:, :w // 2]; g = d.mean(-1, keepdims=True)
    rgb[h // 2:, :w // 2] = (g + (d - g) * 0.8) * np.array([0.50, 0.60, 0.62])   # interior: darker, bluer
    rgb[:h // 2, :w // 2] *= np.array([0.88, 0.92, 0.9]); rgb[h // 2:, w // 2:] *= np.array([0.80, 0.86, 0.80])
    out = srgb8(np.clip(rgb, 0, 1))
    save_rgb(p, out, lin8(a[..., 3]) if mode == 'RGBA' else None)
# leaf sheen was patched in round 1: keep roughness at 0.62
p = f'{OUT}/T_Veg_OakLeaves_ORM.png'; a = np.asarray(Image.open(p)).copy().astype(float); a[..., 1] = np.clip(a[..., 1], 150, 255); Image.fromarray(a.astype('uint8')).save(p)
print('oak variation ok')
