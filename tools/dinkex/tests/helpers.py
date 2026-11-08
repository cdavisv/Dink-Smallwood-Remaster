import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.dirname(HERE)
DATA = os.path.normpath(os.path.join(TOOL, "..", "..", "bin", "dink"))


def make_bmp8(w, h, pixel=0, palette=None):
    """A tiny valid 8-bit uncompressed BMP (palette defaults: 0=white, 255=black)."""
    pal = palette or {0: (255, 255, 255), 255: (0, 0, 0), 1: (10, 20, 30)}
    table = b"".join(bytes((pal.get(i, (0, 0, 0))[2], pal.get(i, (0, 0, 0))[1], pal.get(i, (0, 0, 0))[0], 0)) for i in range(256))
    stride = (w + 3) & ~3
    pix = bytes([pixel]) * (stride * h)
    off = 14 + 40 + 1024
    hdr = b"BM" + struct.pack("<IHHI", off + len(pix), 0, 0, off)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 8, 0, len(pix), 2835, 2835, 0, 0)
    return hdr + info + table + pix


def make_ff(entries):
    """entries: list of (name, bytes). Returns bytes of a dir.ff with sentinel."""
    count = len(entries) + 1
    off = 4 + count * 17
    recs = b""
    body = b""
    for name, data in entries:
        recs += struct.pack("<i13s", off + len(body), name.encode().ljust(13, b"\0"))
        body += data
    recs += struct.pack("<i13s", off + len(body), b"\0" * 13)
    return struct.pack("<i", count) + recs + body
