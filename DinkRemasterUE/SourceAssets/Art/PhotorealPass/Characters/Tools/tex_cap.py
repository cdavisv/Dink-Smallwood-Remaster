"""Cap the size of a figure's texture sets (townsfolk that stand several to a screen at the play camera).

    python3 -I tex_cap.py <folder with T_<Name>_PR_*.png> Skin=2048 Hair=2048 Outfit=2048 Gear=1024 Eyes=512

Every PNG of a named set that is larger than its cap is reduced in place by whole-texel averaging (a box filter: each
new texel is the mean of the block it replaces). Colour under an alpha channel is averaged weighted by the alpha, so the
cut-out edge of a hair card does not pick up the colour of the empty texels beside it; the alpha itself is the plain
mean (scaling it up to keep the strands' share above the cut-off also lifted the faint texels at the edge of a tile over
it: card outlines).
Tangent-space normals (_N) are made unit length again. A file at or under its cap is left alone, so a second run
changes nothing; a stage that bakes at full size is simply followed by this step again (the run_*.sh scripts do)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None


def box(a, k):
    h, w = a.shape[:2]
    return a.reshape(h // k, k, w // k, k, -1).mean(axis=(1, 3))


def cap_file(path, cap):
    im = Image.open(path)
    if max(im.size) <= cap or im.size[0] != im.size[1] or im.size[0] % cap: return None
    k = im.size[0] // cap; mode = im.mode
    if mode not in ('RGB', 'RGBA', 'L'): im = im.convert('RGBA' if 'A' in mode else 'RGB'); mode = im.mode
    a = np.asarray(im, np.float32) / 255.0
    if a.ndim == 2: a = a[..., None]
    if mode == 'RGBA':
        al = a[..., 3:4]; sm = box(al, k); rgb = box(a[..., :3] * al, k) / np.maximum(sm, 1e-6)
        rgb = np.where(sm > 1e-6, rgb, box(a[..., :3], k))
        out = np.concatenate([rgb, sm], axis=2)
    else:
        out = box(a, k)
        if path.stem.endswith('_N') and mode == 'RGB':
            n = out * 2 - 1; n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6); out = n * .5 + .5
    out = (np.clip(out, 0, 1) * 255 + .5).astype(np.uint8)
    Image.fromarray(out[..., 0] if mode == 'L' else out, mode).save(path, optimize=True)
    return im.size[0], cap


def main():
    folder = Path(sys.argv[1]); caps = dict(kv.split('=') for kv in sys.argv[2:])
    for path in sorted(folder.glob('T_*_PR_*.png')):
        part = path.stem.split('_PR_')[1].split('_')[0]
        if part in caps:
            done = cap_file(path, int(caps[part]))
            if done: print('tex_cap', path.name, done[0], '->', done[1])


if __name__ == '__main__':
    main()
