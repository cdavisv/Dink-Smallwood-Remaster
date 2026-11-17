"""Seth's outfit maps (NPC/Seth/Textures/T_Seth_PR_Outfit_BC/N/ORM) from the hero's baked outfit set.

The 1997 pictures (pose, seth1w-9w) show a dark red jerkin over sleeves and a collar of speckled slate blue, which reads
as a mail shirt, and dark blue-grey trousers. The hero's leather jerkin is turned dark red, his olive trousers slate
blue, and his linen shirt becomes riveted mail: rings in the colour map, the normal map and the roughness / metal map
(the hero's cloth folds stay underneath).

    python3 -I seth_outfit.py [ring pitch in texels, default 18]"""
import sys
import numpy as np
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
CHARS = Path(__file__).resolve().parent.parent
SRC = CHARS / 'Dink/Textures'; DST = CHARS / 'NPC/Seth/Textures'
PITCH = float(sys.argv[1]) if len(sys.argv) > 1 else 18.0
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
JERKIN, TROUSERS = (0.56, 0.045, 0.055), (0.10, 0.17, 0.25)
MAIL_HI, MAIL_GAP = np.array([0.36, 0.42, 0.52], np.float32), np.array([0.035, 0.04, 0.05], np.float32)


def load(name):
    return np.asarray(Image.open(SRC / name).convert('RGB'), np.float32) / 255.0


def is_leather(a): return (a[..., 0] - a[..., 2] - 0.06) * 10.0 * (a[..., 0] > a[..., 1] + 0.015)       # the hero's brown jerkin
def is_olive(a): return (np.minimum(a[..., 0], a[..., 1]) - a[..., 2] - 0.05) * 10.0 * (a[..., 1] > a[..., 0] - 0.05)   # his trousers
def is_shirt(a): return (a[..., 2] - a[..., 0] - 0.04) * 10.0                                          # his blue shirt


def rings(size, pitch):
    """Height 0..1 of a mail weave: two interleaved lattices of rings, the rows of one lying over the other."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    h = np.zeros((size, size), np.float32)
    row = pitch * 0.62; radius = pitch * 0.47; wire = pitch * 0.15
    for k, lift in ((0, 0.0), (1, 0.35)):
        v = y / row - k * 0.5
        j = np.round(v); dy = (v - j) * row
        u = x / pitch - 0.5 * (j % 2) - k * 0.25
        dx = (u - np.round(u)) * pitch
        t = (np.hypot(dx, dy * 1.25) - radius) / wire
        ring = np.sqrt(np.clip(1.0 - t * t, 0.0, 1.0)) * (0.65 + lift) + 0.12 * (dx / pitch) * (1 if k else -1) * (np.abs(t) < 1)
        h = np.maximum(h, ring)
    return np.clip(h / h.max(), 0.0, 1.0)


bc = load('T_Dink_PR_Outfit_BC.png'); size = bc.shape[0]
lum = (bc @ LUMA)[..., None]
out = bc.copy()
for pick, target, gain in ((is_leather, JERKIN, 3.3), (is_olive, TROUSERS, 3.8)):
    m = np.clip(pick(bc), 0, 1)[..., None]
    out = out * (1 - m) + m * (bc * 0.12 + 0.88 * np.clip(lum * gain, 0, 1.2) * np.array(target, np.float32))
mail = np.clip(is_shirt(bc), 0, 1)
h = rings(size, PITCH)
rng = np.random.default_rng(580)
shade = np.clip(lum[..., 0] / max(float(lum[mail > 0.5].mean()), 1e-3), 0.45, 1.5)           # the shirt's baked folds and occlusion stay
steel = (MAIL_GAP[None, None, :] + (MAIL_HI - MAIL_GAP)[None, None, :] * (h ** 0.8)[..., None]) * shade[..., None]
steel *= (1.0 + rng.normal(0, 0.035, (size, size)).astype(np.float32))[..., None]
out = out * (1 - mail[..., None]) + steel * mail[..., None]
DST.mkdir(parents=True, exist_ok=True)
Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(DST / 'T_Seth_PR_Outfit_BC.png', optimize=True)

n = load('T_Dink_PR_Outfit_N.png') * 2.0 - 1.0            # OpenGL (+Y up)
gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5; gy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * 0.5      # image rows run down
k = 2.2 * mail
n[..., 0] -= gx * k; n[..., 1] -= gy * k
n /= np.linalg.norm(n, axis=2, keepdims=True)
Image.fromarray(((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)).save(DST / 'T_Seth_PR_Outfit_N.png', optimize=True)

orm = load('T_Dink_PR_Outfit_ORM.png')
orm[..., 0] = orm[..., 0] * (1 - mail) + mail * orm[..., 0] * (0.55 + 0.45 * h)             # occlusion between the rings
orm[..., 1] = orm[..., 1] * (1 - mail) + mail * (0.62 - 0.26 * h)                           # worn ring tops are smoother
orm[..., 2] = orm[..., 2] * (1 - mail) + mail * 0.55 * (h > 0.08)                           # steel, dulled: full metal goes black under a dark sky
Image.fromarray((np.clip(orm, 0, 1) * 255 + 0.5).astype(np.uint8)).save(DST / 'T_Seth_PR_Outfit_ORM.png', optimize=True)
print('seth outfit', size, 'px, ring pitch', PITCH, 'texels, mail share', round(float(mail.mean()), 3))
