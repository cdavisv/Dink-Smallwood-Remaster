"""Composite the CC0 MakeHuman brow and lash alpha cards into the bottom band of a hair atlas, tinted to the hair.
usage: hair_band.py <atlas prefix> <brow png> <lash png> <brow r,g,b> <lash r,g,b>"""
import sys, numpy as np
from PIL import Image
pre, brow, lash = sys.argv[1:4]; bc_ = [np.array([float(x) for x in a.split(',')]) / 255 for a in sys.argv[4:6]]
bc = np.asarray(Image.open(pre + '_BC.png').convert('RGBA'), np.float32) / 255; bc = bc.copy()
H, W = bc.shape[:2]; bh = H // 4
lash_only = len(sys.argv) > 6 and sys.argv[6] == 'lashonly'
for k, (path, col) in enumerate(((brow, bc_[0]), (lash, bc_[1]))):
    if lash_only and k == 0: continue
    im = Image.open(path).convert('RGBA').resize((W // 2, bh), Image.LANCZOS); a = np.asarray(im, np.float32) / 255
    lum = a[..., :3].mean(2); lum = lum / max(lum[a[..., 3] > .3].mean(), 1e-3) if (a[..., 3] > .3).any() else lum
    out = np.dstack([col[None, None, :] * np.clip(.6 + .5 * lum, .4, 1.4)[..., None], np.clip(a[..., 3] * (1.5 if k == 0 else 1.9), 0, 1)])
    out[..., :3] = np.where(a[..., 3:4] > .02, out[..., :3], col[None, None, :])
    bc[H - bh:, k * (W // 2):(k + 1) * (W // 2)] = out
Image.fromarray((np.clip(bc, 0, 1) * 255 + .5).astype(np.uint8), 'RGBA').save(pre + '_BC.png')
for suf, fillv in (('_N', (128, 128, 255)), ('_ORM', (255, 150, 0))):
    im = Image.open(pre + suf + '.png').convert('RGB'); im.paste(fillv, (W // 2 if lash_only else 0, H - bh, W, H)); im.save(pre + suf + '.png')
print('band done')
