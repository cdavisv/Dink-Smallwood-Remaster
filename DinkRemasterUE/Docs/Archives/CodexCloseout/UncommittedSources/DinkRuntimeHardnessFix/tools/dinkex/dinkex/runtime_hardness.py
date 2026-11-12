"""Additive lossless tile/stamp source packet; never recover base from composed PNGs."""
from .hard import build_tile_layer, placement_rank, stamp_rect
from . import PLAY_W, PLAY_H

SCHEMA = 'dinkex.runtime-hardness/1'


def runtime_layers(hard, tiles, sprites, hardbox_of, vision=0):
    if type(vision) is not int or not -(2**31) <= vision < 2**31:
        raise ValueError('vision must be an original signed int32')
    base, skipped = build_tile_layer(hard, tiles)
    if base.shape != (PLAY_H, PLAY_W) or (base > 3).any():
        raise ValueError('tile base must be explicit 600x400 codes 0..3')
    rows = []
    for row in base:
        runs = []
        for value in row:
            code = int(value)
            if runs and runs[-1][1] == code:
                runs[-1][0] += 1
            else:
                runs.append([1, code])
        rows.append(runs)
    stamps = []
    for index in placement_rank(sprites):
        s = sprites[index]
        if s['hard'] != 0 or s['vision'] not in (0, vision):
            continue
        hb = hardbox_of(s)
        rect = stamp_rect(s, hb) if hb is not None else None
        if rect is not None:
            stamps.append({'owner': index, 'code': 100 + index,
                           'rect': list(rect), 'warp': s['prop'] != 0})
    return {'schema': SCHEMA, 'width': PLAY_W, 'height': PLAY_H,
            'vision': vision, 'tile_base_rle': rows, 'ordered_stamps': stamps,
            'skipped_tile_indices': skipped,
            'skipped_tile_policy': 'canonical-zero-initial-screen; historical extractor limitation'}


def decode_runtime_layers(packet, *, expected_vision=None):
    """Strict admission check, yielding base bytes + ordered stamps for a consumer.

    Skipped invalid hard.dat cells require original previous-screen state; the
    initial canonical-zero exporter is NOT sufficient proof for those screens.
    """
    if (packet.get('schema') != SCHEMA
            or type(packet.get('width')) is not int or packet['width'] != PLAY_W
            or type(packet.get('height')) is not int or packet['height'] != PLAY_H):
        raise ValueError('unsupported runtime hardness schema/dimensions')
    vision = packet.get('vision')
    if type(vision) is not int or not -(2**31) <= vision < 2**31:
        raise ValueError('vision must be an original signed int32')
    if expected_vision is not None and (type(expected_vision) is not int or vision != expected_vision):
        raise ValueError('vision does not match consumer screen state')
    if packet.get('skipped_tile_indices') != []:
        raise ValueError('skipped tile cells need explicit previous-screen state')
    rows = packet.get('tile_base_rle')
    if not isinstance(rows, list) or len(rows) != PLAY_H:
        raise ValueError('missing explicit tile base')
    base = bytearray()
    for row in rows:
        decoded = bytearray()
        if not isinstance(row, list):
            raise ValueError('invalid tile RLE row')
        for run in row:
            if (not isinstance(run, list) or len(run) != 2
                    or any(type(v) is not int for v in run)
                    or not 1 <= run[0] <= PLAY_W or not 0 <= run[1] <= 3
                    or len(decoded) + run[0] > PLAY_W):
                raise ValueError('invalid tile RLE run')
            decoded.extend([run[1]] * run[0])
        if len(decoded) != PLAY_W:
            raise ValueError('incomplete tile RLE row')
        base.extend(decoded)
    stamps = packet.get('ordered_stamps')
    if not isinstance(stamps, list):
        raise ValueError('missing ordered stamps')
    owners = set()
    for stamp in stamps:
        if not isinstance(stamp, dict):
            raise ValueError('invalid owner stamp')
        owner, code, rect = stamp.get('owner'), stamp.get('code'), stamp.get('rect')
        if (type(owner) is not int or not 1 <= owner <= 99 or owner in owners
                or type(code) is not int or code != 100 + owner or type(stamp.get('warp')) is not bool
                or not isinstance(rect, list) or len(rect) != 4
                or any(type(v) is not int for v in rect)
                or not (0 <= rect[0] < rect[2] <= PLAY_W and 0 <= rect[1] < rect[3] <= PLAY_H)):
            raise ValueError('invalid owner stamp')
        owners.add(owner)
    return bytes(base), stamps
