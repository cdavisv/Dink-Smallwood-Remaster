"""A townsman's outfit colour map (NPC/<Name>/Textures/T_<Name>_PR_Outfit_BC.png) from the hero's baked outfit set.

The hero's leather jerkin, linen shirt and wool trousers are turned to the colours of the figure's 1997 pictures
(townsfolk.py `outfit`); light, dark, folds and occlusion of the bake stay. The normal and the roughness map are the
hero's own files (cfg/assemble.json `tex_override`, and the manifest refers to them where they are).

    python3 -I townsfolk_outfit.py <Name>"""
import sys
import numpy as np
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, str(Path(__file__).resolve().parent))
from townsfolk import TOWNSFOLK
CHARS = Path(__file__).resolve().parent.parent
NAME = sys.argv[1]; ROW = TOWNSFOLK[NAME]['outfit']
DST = CHARS / 'NPC' / NAME / 'Textures'
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def is_leather(a): return (a[..., 0] - a[..., 2] - 0.06) * 10.0 * (a[..., 0] > a[..., 1] + 0.015)       # the hero's brown jerkin
def is_olive(a): return (np.minimum(a[..., 0], a[..., 1]) - a[..., 2] - 0.05) * 10.0 * (a[..., 1] > a[..., 0] - 0.05)   # his trousers
def is_shirt(a): return (a[..., 2] - a[..., 0] - 0.01) * 30.0                                          # his blue shirt, every thread of it: a soft mask leaves a grey mix of blue and the new colour


bc = np.asarray(Image.open(CHARS / 'Dink/Textures/T_Dink_PR_Outfit_BC.png').convert('RGB'), np.float32) / 255.0
lum = (bc @ LUMA)[..., None]; out = bc.copy(); share = {}
mean_lum = {}; worn = np.zeros(lum.shape, np.float32)
for part, pick in (('jerkin', is_leather), ('shirt', is_shirt), ('trousers', is_olive)):
    if part not in ROW: continue
    target, gain = ROW[part]
    m = np.clip(pick(bc), 0, 1)[..., None]; share[part] = round(float(m.mean()), 3)
    mean_lum[part] = float((lum * m).sum() / max(float(m.sum()), 1.0))
    k = 1.0
    if gain is None:      # this part takes the jerkin's brightness: with the jerkin's colour the two read as one garment. The pale linen keeps its folds at a lower contrast (k)
        gain = ROW['jerkin'][1] * mean_lum['jerkin'] / mean_lum[part]; k = 0.75; share[part + '_gain'] = round(gain, 3)
    shade = np.clip(mean_lum[part] * gain * (lum / mean_lum[part]) ** k, 0, 1.2)
    hi = mean_lum[part] * gain * 1.8; shade = np.minimum(shade, hi + (shade - hi) * 0.25)      # the worn edges of the hero's leather stay edges, not bright orange piping
    out = out * (1 - m) + m * (bc * 0.12 + 0.88 * shade * np.array(target, np.float32))
    if part != 'trousers': worn = np.maximum(worn, m)
if ROW.get('mottle'):      # an old coat: worn paler in broad patches, darker in others (the 1997 coat is mottled, not one flat brown)
    def hash2(a, b, s): h = np.sin(a * 127.1 + b * 311.7 + s * 74.7) * 43758.5453; return h - np.floor(h)
    def vnoise(n, cells, s):
        y, x = np.mgrid[0:n, 0:n].astype(np.float32) * (cells / n); xi, yi = np.floor(x), np.floor(y); fx, fy = x - xi, y - yi; fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
        return (hash2(xi, yi, s) * (1 - fx) + hash2(xi + 1, yi, s) * fx) * (1 - fy) + (hash2(xi, yi + 1, s) * (1 - fx) + hash2(xi + 1, yi + 1, s) * fx) * fy
    n = bc.shape[0]; f = (vnoise(n, 9, 3) * .5 + vnoise(n, 23, 5) * .3 + vnoise(n, 61, 7) * .2 - .5)[..., None] * 2 * ROW['mottle']
    pale = np.array([1.0, 1.03, 1.10], np.float32)      # worn cloth loses its red first
    out = out * (1 - worn) + worn * out * (1 + f) * pale ** np.clip(f * 2, 0, 1)
DST.mkdir(parents=True, exist_ok=True)
Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(DST / f'T_{NAME}_PR_Outfit_BC.png', optimize=True)
print('townsfolk outfit', NAME, bc.shape[0], 'px, shares', share)
