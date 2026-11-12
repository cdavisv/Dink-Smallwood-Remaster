#!/usr/bin/env python3
"""cal2_compare.py <tag> [shots...] [--pairs]: patch statistics of the engine captures (cal2/<tag>_<shot>[_var].png, central
1300:850 crop) against the Cycles review frames. Patches are rectangles in frame fractions, the same in both images.
Prints per patch: mean sRGB, luminance, saturation and the linear ratio to the 'ground' patch (exposure-free).
--pairs writes cal2/<tag>_<shot>_pair.jpg (reference | engine) for looking."""
import sys, os, glob
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); CAL = os.path.join(HERE, '..', '..', 'Saved', 'PhotorealPass', 'lighting', 'cal2')
REV = os.path.abspath(os.path.join(HERE, '../../SourceAssets/Art/PhotorealPass/Structures/review'))
REF = {  # shot: (reference frame, {patch: (x0, y0, x1, y1)})
 'Cottage_gameplay': ('sb6/Cottage_gameplay.png', {}), 'Cottage_roof': ('sb6/Cottage_roof.png', {}), 'Cottage_door': ('sb6/Cottage_door.png', {}),
 'Yard_gameplay': ('sb6/Yard_gameplay.png', {}), 'Yard_eye': ('sb6/Yard_eye.png', {}), 'Boulders_gameplay': ('sb6/Boulders_gameplay.png', {}),
 'House_gameplay': ('town4/House_gameplay.png', {}), 'House_street': ('town4/House_street.png', {}), 'House_roof': ('town4/House_roof.png', {}),
 'Burnt_gameplay': ('sb6/Burnt_gameplay.png', {}),
}
PATCH = os.path.join(HERE, 'cal2_patches.json')
if os.path.exists(PATCH):
    import json
    for k, v in json.load(open(PATCH)).items():
        if k in REF: REF[k] = (REF[k][0], v)
def load(path, crop):
    im = Image.open(path).convert('RGB')
    if crop:
        w, h = im.size; cw = int(round(h * 1300 / 850)); im = im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    return im
def lin(a): return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
def stat(im, r):
    w, h = im.size
    a = np.asarray(im.crop((int(r[0] * w), int(r[1] * h), int(r[2] * w), int(r[3] * h)))).astype(np.float64).reshape(-1, 3) / 255.0
    m = a.mean(0); lum = a @ np.array([0.2126, 0.7152, 0.0722]); mx, mn = a.max(1), a.min(1)
    return dict(mean=(m * 255).round(0).astype(int).tolist(), lum=round(float(lum.mean()) * 255), p5=round(float(np.percentile(lum, 5)) * 255), p95=round(float(np.percentile(lum, 95)) * 255),
                sat=round(float(((mx - mn) / np.maximum(mx, 1e-4)).mean()), 3), lin=lin(m))
args = [a for a in sys.argv[1:] if not a.startswith('--')]; tag = args[0]; shots = args[1:] or list(REF)
for s in shots:
    ref_name, patches = REF[s]
    engs = sorted(glob.glob(os.path.join(CAL, f'{tag}_{s}.png')) + [f for f in glob.glob(os.path.join(CAL, f'{tag}_{s}_*.png'))])
    if not engs: continue
    ref = load(os.path.join(REV, ref_name), False)
    if '--pairs' in sys.argv:
        e = load(engs[0], True).resize(ref.size, Image.LANCZOS); pair = Image.new('RGB', (ref.width * 2 + 8, ref.height)); pair.paste(ref, (0, 0)); pair.paste(e, (ref.width + 8, 0))
        pair.resize((pair.width * 5 // 8, pair.height * 5 // 8), Image.LANCZOS).save(os.path.join(CAL, f'{tag}_{s}_pair.jpg'), quality=88)
    if not patches: continue
    rows = [('ref', ref)] + [(os.path.basename(e)[len(tag) + len(s) + 2:-4] or 'eng', load(e, True)) for e in engs]
    g = {n: stat(im, patches['anchor'])['lin'] if 'anchor' in patches else None for n, im in rows}
    for p, r in patches.items():
        for n, im in rows:
            st = stat(im, r); ratio = (st['lin'] / g[n]).round(2).tolist() if g[n] is not None else ''
            print(f"{s:18s} {p:12s} {n:8s} mean {st['mean']} lum {st['lum']} p5/95 {st['p5']}/{st['p95']} sat {st['sat']} /anchor {ratio}")
