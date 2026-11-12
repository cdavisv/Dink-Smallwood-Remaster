"""Compose final BC / N / ORM PNG sets from the raw bakes. usage: post_tex.py <CharDir> <Prefix e.g. T_Dink_PR> [groups...]"""
import sys, json, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
Image.MAX_IMAGE_PIXELS = None
char = Path(sys.argv[1]); prefix = sys.argv[2]; BK = char / 'Work/bake'; TX = char / 'Textures'
meta = json.load(open(BK / 'uvdump.json')); tris = np.load(BK / 'uvdump.npz')
METAL = ('brass', 'iron', 'steel', 'mail')
for g in (sys.argv[3:] or sorted({m['group'] for m in meta.values()})):
    bc = Image.open(BK / f'{g}_BC.png').convert('RGB'); size = bc.size[0]
    n = Image.open(BK / f'{g}_N.png').convert('RGB'); r = Image.open(BK / f'{g}_R.png').convert('L')
    ao = Image.open(BK / f'{g}_AO.png').convert('L').resize((size, size), Image.BICUBIC).filter(ImageFilter.GaussianBlur(.6))
    metal = Image.new('L', (size, size), 0); cover = Image.new('L', (size, size), 0); dm = ImageDraw.Draw(metal); dc = ImageDraw.Draw(cover)
    for name, m in meta.items():
        if m['group'] != g: continue
        T = tris[name]
        for t in T:
            pts = [(t[0] * size, (1 - t[1]) * size), (t[2] * size, (1 - t[3]) * size), (t[4] * size, (1 - t[5]) * size)]
            dc.polygon(pts, fill=255, outline=255)
            if m['fabric'] in METAL: dm.polygon(pts, fill=255, outline=255)
    metal = metal.filter(ImageFilter.MaxFilter(5))
    a = np.asarray(ao, np.float32) / 255; a = np.clip(.25 + .75 * a ** 1.1, 0, 1)
    B = np.asarray(bc, np.float32) / 255; cov = np.asarray(cover) > 0
    mt = np.asarray(metal, np.float32) / 255
    # metals: base colour is reflectance (bake was done dielectric), keep it bright; dielectrics stay inside 30..240 luma
    lum = B @ np.array([.2126, .7152, .0722])
    lo = np.percentile(lum[cov], 1) * 255; hi = np.percentile(lum[cov], 99) * 255
    print(g, 'luma p1/p99 in coverage', round(lo), round(hi))
    floor = 30 / 255
    k = np.where(lum < floor, floor / np.maximum(lum, 1e-3), 1.0); B = np.clip(B * np.minimum(k, 3.0)[..., None], 0, 240 / 255)
    Image.fromarray((B * 255 + .5).astype(np.uint8)).save(TX / f'{prefix}_{g}_BC.png')
    n.save(TX / f'{prefix}_{g}_N.png')
    orm = np.dstack([a, np.asarray(r, np.float32) / 255, mt])
    Image.fromarray((orm * 255 + .5).astype(np.uint8)).save(TX / f'{prefix}_{g}_ORM.png')
    print('wrote', g, size)
