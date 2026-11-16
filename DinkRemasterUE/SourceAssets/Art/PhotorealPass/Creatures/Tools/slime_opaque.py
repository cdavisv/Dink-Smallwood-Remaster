#!/usr/bin/env python3
"""Opaque-gel base colours for the slimes (T_Slime_<Colour>_Opaque_BC.png).

The baked T_Slime_<Colour>_BC textures were made for a see-through gel that is not built: drawn opaque they are pale
(lilac, salmon, mustard). The 1997 sprites are dark: blue-black with pale spots (651/653), olive-yellow with blue spots
(671/673), dark brown-red with pale blue spots (691/693). This remaps each texture's value range onto the sprite's body
colour and turns its light specks into the pale blue spots. Pure Python (Pillow, numpy); no Blender.

usage: python3 -I slime_opaque.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

TEX = Path(__file__).resolve().parents[1] / 'Slime' / 'Textures'
# dark and mid body colour (sRGB 0..1) read off the sprites, and the spot colour
LOOK = {'Blue': ((.03, .035, .10), (.10, .13, .30), (.70, .78, .86)),
        'Green': ((.16, .13, .02), (.40, .34, .06), (.45, .66, .92)),
        'Red': ((.07, .015, .012), (.24, .05, .035), (.60, .80, .95))}
# (the first version, twice as bright, drew the red slime tomato red in the game's daylight)


def main():
    for colour, (dark, mid, spot) in LOOK.items():
        im = np.asarray(Image.open(TEX / f'T_Slime_{colour}_BC.png').convert('RGB'), dtype=np.float32) / 255.0
        lum = im @ np.array((.3, .59, .11), dtype=np.float32)
        lo, hi = np.percentile(lum, 4), np.percentile(lum, 90)
        t = np.clip((lum - lo) / max(hi - lo, 1e-4), 0, 1)[..., None]
        body = np.array(dark) * (1 - t) + np.array(mid) * t
        sat = im.max(axis=2) - im.min(axis=2)
        speck = np.clip((lum - np.percentile(lum, 97.5)) / .06, 0, 1) * np.clip(1.4 - sat * 4, 0, 1)   # the bright, colourless flecks
        out = body * (1 - speck[..., None]) + np.array(spot) * speck[..., None]
        Image.fromarray((np.clip(out, 0, 1) * 255 + .5).astype(np.uint8)).save(TEX / f'T_Slime_{colour}_Opaque_BC.png')
        print(colour, 'mean', [round(float(v), 3) for v in out.reshape(-1, 3).mean(axis=0)], 'specks', round(float(speck.mean()), 4))


if __name__ == '__main__':
    main()
