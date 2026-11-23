"""Compose final BC / N / ORM PNG sets from the raw bakes. usage: post_tex.py <CharDir> <Prefix e.g. T_Dink_PR> [groups...]"""
import os, sys, json, numpy as np
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
    # Texels the bake never reached keep the image's generated grey (128, 128, 128): a rolled lip that has no high-poly
    # counterpart (the saw-toothed pale rim of Milder's greaves in the game), a coarse low-poly chord further from the
    # high-poly than the ray length. Inside the charts they take the colour and roughness of the nearest baked texel.
    raw = np.asarray(bc, np.uint8); missed = (raw == 128).all(2) & (np.asarray(cover) > 0)
    if missed.any():
        n0 = int(missed.sum()); col = raw.astype(np.float32); rgh = np.asarray(r, np.float32); todo = missed.copy(); valid = ~todo & (np.asarray(cover) > 0)
        for _ in range(96):
            if not todo.any(): break
            acc = np.zeros_like(col); accr = np.zeros_like(rgh); cnt = np.zeros(todo.shape, np.float32)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                v = np.roll(valid, (dy, dx), (0, 1)); acc += np.roll(col, (dy, dx), (0, 1)) * v[..., None]; accr += np.roll(rgh, (dy, dx), (0, 1)) * v; cnt += v
            got = todo & (cnt > 0)
            col[got] = acc[got] / cnt[got][:, None]; rgh[got] = accr[got] / cnt[got]; valid |= got; todo &= ~got
        bc = Image.fromarray((col + .5).astype(np.uint8)); r = Image.fromarray((rgh + .5).astype(np.uint8))
        print(g, 'texels the bake missed, filled from their neighbours:', n0, 'left', int(todo.sum()))
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
    rough = np.asarray(r, np.float32) / 255
    if os.environ.get('METAL_ROUGH'):
        # "gain,offset" for the metal parts only (cfg/tex.env). Milder's plate baked at 0.4: in the game his gauntlets and pauldrons
        # mirrored the meadow bright green from behind (16 Nov 2026); worn field steel is a satin 0.6.
        gain, offset = (float(v) for v in os.environ['METAL_ROUGH'].split(','))
        rough = rough * (1 - mt) + np.clip(rough * gain + offset, 0, 1) * mt
    if os.environ.get('METAL_K'):
        # "k": the metal parts keep this share of their metalness (cfg/tex.env). Even at a satin roughness Milder's plate, all
        # reflection and no body colour, took the whole colour of the meadow from behind (green vambraces, 16 Nov 2026); worn,
        # oiled field steel has a grey of its own under the reflection.
        mt = mt * float(os.environ['METAL_K'])
    orm = np.dstack([a, rough, mt])
    Image.fromarray((orm * 255 + .5).astype(np.uint8)).save(TX / f'{prefix}_{g}_ORM.png')
    print('wrote', g, size)
