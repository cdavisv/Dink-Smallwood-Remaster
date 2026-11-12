"""Standalone read-only RGB8 PNG decoder, derived from reviewed RoofNativeIntegration/png_source.py; no pixel edits."""
from pathlib import Path
import struct,zlib
def require(condition, message):
    if not condition:
        raise RuntimeError(message)
def png_rgb(path):
    """Decode noninterlaced8-bit RGB PNG using stdlib, so no Pillow dependency in UE."""
    raw = Path(path).read_bytes()
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'Not PNG')
    offset = 8; compressed = bytearray(); header = None
    while offset < len(raw):
        length = struct.unpack_from('>I', raw, offset)[0]; kind = raw[offset+4:offset+8]
        payload = raw[offset+8:offset+8+length]
        require(zlib.crc32(kind + payload) & 0xffffffff == struct.unpack_from('>I', raw, offset+8+length)[0], 'PNG CRC')
        if kind == b'IHDR': header = struct.unpack('>IIBBBBB', payload)
        if kind == b'IDAT': compressed.extend(payload)
        offset += length + 12
        if kind == b'IEND': break
    require(header is not None and header[2]==8 and header[3]in (2,6) and header[4:]==(0,0,0), 'Expected RGB8 noninterlaced PNG')
    width, height = header[:2]; bpp=3 if header[3]==2 else 4; stride = width * bpp; decoded = zlib.decompress(compressed)
    require(len(decoded) == height * (stride + 1), 'PNG payload length')
    output = bytearray(); previous = bytearray(stride)
    for y in range(height):
        start = y*(stride+1); kind = decoded[start]; row = bytearray(decoded[start+1:start+1+stride])
        require(kind <= 4, 'PNG filter')
        if kind:
            for i in range(stride):
                left = row[i-bpp] if i >= bpp else 0; up = previous[i]; upper_left = previous[i-bpp] if i >= bpp else 0
                if kind == 1: prediction = left
                elif kind == 2: prediction = up
                elif kind == 3: prediction = (left + up)//2
                else:
                    p = left+up-upper_left; distances = (abs(p-left), abs(p-up), abs(p-upper_left))
                    prediction = (left, up, upper_left)[distances.index(min(distances))]
                row[i] = (row[i] + prediction) & 255
        output.extend(row); previous = row
    if bpp==4:
        require(all(v==255 for v in output[3::4]),'Unexpected exported alpha')
        output=bytearray(v for i,v in enumerate(output)if i%4!=3)
    return width, height, output
