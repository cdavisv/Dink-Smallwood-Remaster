"""Duck atlas repair: texels where every baked pass came back zero (base colour black, roughness 0, AO 0) although the ray hit, are filled from their neighbours.
Eyes are kept (their roughness is 0.03, not 0). Applied to the clean and the bloody sets. usage: python3 -I fix_duck_black.py"""
import numpy as np
from pathlib import Path
from PIL import Image
T = Path(__file__).resolve().parents[1] / 'Duck/Textures'
L = lambda n: np.asarray(Image.open(T / n).convert('RGB'), dtype=np.float64) / 255.0
bc = L('T_Duck_Atlas_BC.png'); orm = L('T_Duck_Atlas_ORM.png')
bad = (bc.sum(-1) < .05) & (orm[..., 1] < 4 / 255) & (orm[..., 0] < .2)
# only texels with baked neighbours close by (inside the islands), not the empty background
near = np.zeros_like(bad)
good = (bc.sum(-1) > .3)
for r in (1, 2, 4, 8, 12):
    for dy, dx in ((0, r), (0, -r), (r, 0), (-r, 0)): near |= np.roll(good, (dy, dx), (0, 1))
bad &= near; print('repairing texels', int(bad.sum()))
names = ['T_Duck_Atlas_BC.png', 'T_Duck_Atlas_N.png', 'T_Duck_Atlas_ORM.png', 'T_Duck_Atlas_SSS.png', 'T_Duck_Atlas_Bloody_BC.png', 'T_Duck_Atlas_Bloody_ORM.png']
imgs = {n: L(n) for n in names}; m = (~bad & good).astype(np.float64); todo = bad.copy()
for _ in range(40):
    cnt = np.zeros_like(m); acc = {n: np.zeros_like(v) for n, v in imgs.items()}
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        rm = np.roll(m, (dy, dx), (0, 1)); cnt += rm
        for n, v in imgs.items(): acc[n] += np.roll(v * m[..., None], (dy, dx), (0, 1))
    fill = todo & (cnt > 0)
    if not fill.any(): break
    for n, v in imgs.items(): v[fill] = acc[n][fill] / cnt[fill][:, None]
    m = np.maximum(m, fill); todo &= ~fill
for n, v in imgs.items(): Image.fromarray((np.clip(v, 0, 1) * 255 + .5).astype(np.uint8)).save(T / n)
print('left unrepaired', int(todo.sum()))
