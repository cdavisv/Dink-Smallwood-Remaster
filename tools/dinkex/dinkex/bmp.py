"""Minimal BMP helpers.

Sizes are read straight from the header (cheap, no Pillow) because the whole
sequence table needs thousands of them.  Pixel conversion uses Pillow.
"""

import io
import struct

import numpy as np
from PIL import Image


def bmp_size(data):
    """Return (width, height) of a BMP from its header; height is absolute."""
    if data[:2] != b"BM" or len(data) < 26:
        raise ValueError("not a BMP")
    hdr = struct.unpack_from("<I", data, 14)[0]
    if hdr == 12:   # OS/2 core header
        w, h = struct.unpack_from("<HH", data, 18)
    else:
        w, h = struct.unpack_from("<ii", data, 18)
    return w, abs(h)


# Colour keys are matched on the RGB value of the pixel, not on a palette
# index: all shipped sprite BMPs share one palette in which index 0 is white
# and index 255 is black, but the 13 loose tiles/sNN.bmp (the BLACK-keyed
# Dink sprites) carry their own palettes, so RGB is the robust choice.
KEY_RGB = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


def load_rgb(data):
    """BMP bytes -> (H, W, 3) uint8 array."""
    im = Image.open(io.BytesIO(data))
    im.load()
    return np.asarray(im.convert("RGB"), dtype=np.uint8)


def to_rgba(data, key):
    """BMP bytes -> RGBA PIL image; pixels equal to the key colour get alpha 0.

    key: 'white', 'black' or 'none'.
    """
    rgb = load_rgb(data)
    alpha = np.full(rgb.shape[:2], 255, dtype=np.uint8)
    if key in KEY_RGB:
        r, g, b = KEY_RGB[key]
        alpha[(rgb[..., 0] == r) & (rgb[..., 1] == g) & (rgb[..., 2] == b)] = 0
    out = np.dstack([rgb, alpha])
    return Image.fromarray(out)
