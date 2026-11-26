"""Grade for the rendered explosion atlases (167, 70, 161): fire that is orange in the game, and edges without a halo.

The Cycles frames come out pale (a white-hot ball with cream skins) and with a thin veil of light round every shape. In
the game the hot texels are multiplied by the row's glow, so the pale fire clipped to a white blob and the veil drew a
white outline round the smoke. grade() is applied by build_fx_vol.py to every atlas of fire before it is saved:

  * fire texels (warmer than grey, bright) lose green and most of their blue: cream becomes yellow-orange, the core
    stays pale yellow; grey smoke is left alone;
  * the thin veil is cut from the opacity (a soft threshold), and the colour of what is left is spread outwards under
    the transparent texels, so filtering finds fire or smoke there, never white.

  * defringe(): the dark phases' pale skin takes the colour of the shape's inside (17 Nov 2026: the thin pale outline
    round the dark phases seen in the game).

    python3 -I Unclaimed/tools/fx_grade.py Shock Splode Atomic     # once, on atlases rendered before this file existed
"""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
UNC = os.path.dirname(HERE)
GLOW, HOT = 1.6, [0.55, 0.95, 1.0]          # the kit row's glow and thresholds that go with the graded colours


def _box(a, r, axis):
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    return ((np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis) - np.take(c, np.arange(0, n), axis=axis)) / (2 * r + 1)).astype(np.float32)


def _blur(a, r):
    for _ in range(3):
        a = _box(_box(a, r, 0), r, 1)
    return a


def grade(atlas):
    """atlas: H x W x 4 float, straight sRGB-encoded colour + alpha. Returns the graded atlas."""
    rgb, a = atlas[..., :3].astype(np.float32), atlas[..., 3].astype(np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1)
    warm = np.clip((r - b) * 6.0, 0, 1) * np.clip((mx - 0.35) / 0.25, 0, 1)
    fire = np.stack([r, np.power(g, 1.6), np.power(b, 3.2)], -1)
    rgb = rgb * (1 - warm[..., None]) + fire * warm[..., None]
    t = np.clip((a - 0.10) / 0.80, 0, 1)
    a2 = t * t * (3 - 2 * t)
    w = np.clip((a2 - 0.15) / 0.30, 0, 1)
    num = np.stack([_blur(rgb[..., k] * w, 3) for k in range(3)], -1)
    den = _blur(w, 3)[..., None]
    spread = np.where(den > 1e-4, num / np.maximum(den, 1e-4), rgb)
    wide = np.stack([_blur(rgb[..., k] * w, 12) for k in range(3)], -1) / np.maximum(_blur(w, 12)[..., None], 1e-4)
    spread = np.where(den > 1e-4, spread, wide)
    rgb = rgb * w[..., None] + spread * (1 - w[..., None])
    return np.concatenate([np.clip(rgb, 0, 1), a2[..., None]], -1).astype(np.float32)


def defringe(atlas, cols, rows):
    """The dark phases (red-brown fire going out, grey smoke) kept a thin pale skin: the outermost texels of the rendered
    smoke are a veil lit nearly white, and at full opacity they drew a pale line round every dark shape. Per frame: a
    pale, colourless texel near the shape's edge takes the colour of the shape's inside; pale specks that have no inside
    (stray wisps) fade out. Fire's own edge (orange: saturated) is left alone."""
    out = atlas.copy()
    ch, cw = atlas.shape[0] // rows, atlas.shape[1] // cols
    for k in range(cols * rows):
        y0, x0 = (k // cols) * ch, (k % cols) * cw
        f = out[y0:y0 + ch, x0:x0 + cw]
        rgb, a = f[..., :3].copy(), f[..., 3].copy()
        if a.max() < 0.05:
            continue
        mx, mn = rgb.max(-1), rgb.min(-1)
        pale = np.clip((mn - 0.42) / 0.22, 0, 1) * np.clip(1.0 - (mx - mn) / 0.22, 0, 1)
        inside = np.clip((_blur(a, 7) - 0.82) / 0.14, 0, 1)                      # 1 well inside the shape, 0 at its edge and outside
        deep = inside * (1 - pale)                                               # ... and not pale itself
        num = np.stack([_blur(rgb[..., c] * deep, 9) for c in range(3)], -1)
        den = _blur(deep, 9)
        inner = num / np.maximum(den, 1e-4)[..., None]
        has = np.clip(den / 0.06, 0, 1)                                            # is there an inside near this texel at all
        w = (pale * has * (1 - inside))[..., None]                                 # only the skin: a white-hot core is not a fringe
        rgb = rgb * (1 - w) + inner * w
        a = a * (1 - pale * (1 - has) * (1 - inside))                                             # a pale wisp with no body behind it fades out
        f[..., :3] = rgb
        f[..., 3] = a
    return out


def strip(atlas, cols, cell, picks):
    green = np.array((74, 112, 54), np.float32) / 255
    s = np.concatenate([atlas[(k // cols) * cell:(k // cols + 1) * cell, (k % cols) * cell:(k % cols + 1) * cell] for k in picks], 1)[::2, ::2]
    return s[..., :3] * s[..., 3:4] + green * (1 - s[..., 3:4])


def regrade(name, picks):
    folder = [os.path.join(UNC, d, name) for d in os.listdir(UNC) if os.path.isdir(os.path.join(UNC, d, name))][0]
    mp = os.path.join(folder, 'manifest.json')
    m = json.load(open(mp))
    fb = m['flipbook']
    if fb.get('graded') and fb.get('defringed'):
        print(name, 'is graded and defringed already'); return
    tex = os.path.join(folder, 'T_FX_%s_Flipbook.png' % name)
    atlas = np.asarray(Image.open(tex).convert('RGBA'), np.float32) / 255.0
    out = atlas if fb.get('graded') else grade(atlas)
    out = defringe(out, fb['grid'][0], fb['grid'][1])
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA').save(tex, optimize=True)
    cols = fb['grid'][0]; cell = atlas.shape[1] // cols
    Image.fromarray((np.clip(strip(out, cols, cell, picks), 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(folder, 'frames_strip.png'), optimize=True)
    fb['graded'] = True; fb['defringed'] = True; fb['glow'] = GLOW; fb['hot'] = HOT
    json.dump(m, open(mp, 'w'), indent=1)
    print('graded', name, atlas.shape)


if __name__ == '__main__':
    PICKS = {'Shock': (1, 4, 7, 10, 13), 'Splode': (1, 4, 7, 10, 13), 'Atomic': (2, 8, 14, 18, 23, 28)}
    for n in sys.argv[1:]:
        regrade(n, PICKS[n])
