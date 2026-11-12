"""Lossless depth-bound PNG samples; legacy png_rgb remains strictly RGB8."""
from pathlib import Path
import struct,zlib
def require(condition, message):
    if not condition:
        raise RuntimeError(message)
def png_rgb(path):
    """Legacy strict8-bit return shape; never silently admits16-bit samples."""
    return png_rgb_profile(path, expected_bit_depth=8)

def png_format(path):
    """Read IHDR format for receipts; sample decoding still verifies every chunk."""
    with Path(path).open('rb') as stream: raw=stream.read(33)
    require(len(raw)==33 and raw[:8]==b'\x89PNG\r\n\x1a\n' and raw[8:16]==b'\x00\x00\x00\rIHDR','PNG IHDR')
    require(zlib.crc32(raw[12:29])&0xffffffff==struct.unpack('>I',raw[29:33])[0],'PNG CRC')
    w,h,bits,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',raw[16:29])
    return dict(width=w,height=h,bit_depth=bits,color_type=color,compression=compression,filter=filtering,interlace=interlace)

def png_rgb_profile(path, expected_bit_depth):
    """Exact RGB bytes at the declared8/16 depth;16-bit words stay big endian.

    RGB and opaque RGBA are equivalent only at the SAME explicitly bound depth.
    No gamma, scaling, quantization, byte swapping or8/16 normalization occurs.
    """
    require(type(expected_bit_depth)is int and expected_bit_depth in(8,16),'Explicit PNG depth8 or16 required')
    raw = Path(path).read_bytes()
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'Not PNG')
    offset = 8; compressed = bytearray(); header = None; ended=False
    while offset < len(raw):
        require(offset+12<=len(raw),'Truncated PNG chunk')
        length = struct.unpack_from('>I', raw, offset)[0]; kind = raw[offset+4:offset+8]
        require(offset+length+12<=len(raw),'Truncated PNG chunk payload')
        payload = raw[offset+8:offset+8+length]
        require(zlib.crc32(kind + payload) & 0xffffffff == struct.unpack_from('>I', raw, offset+8+length)[0], 'PNG CRC')
        if kind == b'IHDR':
            require(header is None and length==13 and offset==8,'PNG IHDR')
            header = struct.unpack('>IIBBBBB', payload)
        if kind == b'IDAT': compressed.extend(payload)
        offset += length + 12
        if kind == b'IEND':
            require(length==0,'PNG IEND');ended=True;break
    require(ended,'Missing PNG IEND')
    require(header is not None and header[2]==expected_bit_depth and header[3]in (2,6) and header[4:]==(0,0,0), 'Expected RGB'+str(expected_bit_depth)+' noninterlaced PNG')
    width, height = header[:2]; require(width>0 and height>0,'PNG dimensions')
    sample_bytes=expected_bit_depth//8;channels=3 if header[3]==2 else 4;bpp=channels*sample_bytes;stride = width * bpp;decoded = zlib.decompress(compressed)
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
    if channels==4:
        opaque=(1<<expected_bit_depth)-1;rgb=bytearray()
        for i in range(0,len(output),bpp):
            require(int.from_bytes(output[i+3*sample_bytes:i+bpp],'big')==opaque,'Unexpected exported alpha')
            rgb.extend(output[i:i+3*sample_bytes])
        output=rgb
    return width, height, output
