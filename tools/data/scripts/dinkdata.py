"""Minimal, self-contained readers for the original Dink Smallwood data.

Stdlib + Pillow only. Independent of tools/dinkex on purpose.
Byte layouts follow doc/remaster/bible/04-engine-and-file-formats.md section 1.
"""
import io
import os
import struct
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DINK = os.path.join(REPO, 'bin', 'dink')

MAP_REC = 31280
SPR_OFF = 8020
SPR_SZ = 220
TILE_OFF = 20
TILE_SZ = 80

Placement = namedtuple('Placement', 'screen index x y seq frame type size brain script '
                       'hard prop warp_map vision que')


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def cstr(b):
    return b.split(b'\0')[0].decode('latin1')


def read_dink_dat(base=DINK):
    d = _read(os.path.join(base, 'dink.dat'))
    loc = struct.unpack('<769i', d[20:20 + 769 * 4])
    music = struct.unpack('<769i', d[3096:3096 + 769 * 4])
    indoor = struct.unpack('<769i', d[6172:6172 + 769 * 4])
    return loc, music, indoor


def iter_screens(base=DINK):
    """Yield (screen_number, record_bytes, indoor) for every used screen."""
    loc, _music, indoor = read_dink_dat(base)
    m = _read(os.path.join(base, 'map.dat'))
    for n in range(1, 769):
        if loc[n] <= 0:
            continue
        blk = m[(loc[n] - 1) * MAP_REC: loc[n] * MAP_REC]
        if len(blk) < MAP_REC:
            continue
        yield n, blk, indoor[n]


def screen_tiles(blk):
    """96 tile nums, row-major 12x8."""
    out = []
    for i in range(96):
        o = TILE_OFF + i * TILE_SZ
        out.append(struct.unpack('<i', blk[o:o + 4])[0])
    return out


def screen_script(blk):
    return cstr(blk[30240:30253]).lower()


def screen_placements(n, blk):
    """Active sprite placements of one screen (all 101 slots scanned)."""
    out = []
    for i in range(101):
        o = SPR_OFF + i * SPR_SZ
        sp = blk[o:o + SPR_SZ]
        if not sp[24]:
            continue
        x, y, seq, frame, typ, size = struct.unpack('<6i', sp[0:24])
        brain = struct.unpack('<i', sp[36:40])[0]
        script = cstr(sp[40:53]).lower()
        que = struct.unpack('<i', sp[116:120])[0]
        hard = struct.unpack('<i', sp[120:124])[0]
        prop, warp_map = struct.unpack('<2i', sp[140:148])
        vision = struct.unpack('<i', sp[188:192])[0]
        out.append(Placement(n, i, x, y, seq, frame, typ, size, brain, script,
                             hard, prop, warp_map, vision, que))
    return out


def all_placements(base=DINK):
    out = []
    for n, blk, _ in iter_screens(base):
        out.extend(screen_placements(n, blk))
    return out


# ---------------------------------------------------------------- dink.ini

class Seq:
    def __init__(self, num, prefix, flags):
        self.num = num
        self.prefix = prefix.replace('\\', '/')
        self.flags = flags  # set of BLACK/NOTANIM/LEFTALIGN
        self.alias = {}      # frame -> (seq, frame)
        self.xoff = self.yoff = None  # sequence-wide origin, if given
        self.info = {}       # frame -> (xoff, yoff) from SET_SPRITE_INFO

    @property
    def black(self):
        return 'BLACK' in self.flags


def read_dink_ini(base=DINK):
    """Return {seq: Seq}. Later load_sequence lines for the same seq replace
    earlier ones (that is the state the map editor saw)."""
    seqs = {}
    aliases = []
    infos = []
    for raw in _read(os.path.join(base, 'dink.ini')).decode('latin1').splitlines():
        line = raw.strip()
        if not line or line.startswith('//') or line.startswith(';'):
            continue
        t = line.split()
        k = t[0].lower()
        if k in ('load_sequence', 'load_sequence_now') and len(t) >= 3:
            try:
                num = int(t[2])
            except ValueError:
                continue
            flags = {x.upper() for x in t[3:] if x.upper() in ('BLACK', 'NOTANIM', 'LEFTALIGN')}
            sq = Seq(num, t[1], flags)
            nums = []
            for x in t[3:]:
                try:
                    nums.append(int(x))
                except ValueError:
                    break
            if len(nums) >= 3:
                sq.xoff, sq.yoff = nums[1], nums[2]
            seqs[num] = sq
        elif k == 'set_frame_frame' and len(t) >= 5:
            aliases.append(tuple(int(x) for x in t[1:5]))
        elif k == 'set_sprite_info' and len(t) >= 5:
            infos.append(tuple(int(x) for x in t[1:5]))
    for s, f, ss, sf in aliases:
        if s in seqs:
            seqs[s].alias[f] = (ss, sf)
    for s, f, xo, yo in infos:
        if s in seqs:
            seqs[s].info[f] = (xo, yo)
    return seqs


def frame_origin(seqs, seq, frame, w, h):
    """Depth-dot origin of a frame (engine defaults per bible section 1)."""
    s = seqs.get(seq)
    if s is not None:
        if frame in s.info:
            return s.info[frame]
        if s.xoff is not None and 'NOTANIM' not in s.flags:
            return s.xoff, s.yoff
    return w - w // 2 + w // 6, h - h // 4 - h // 30


# ---------------------------------------------------------------- .ff

_ff_cache = {}


def read_ff(path):
    """{lowercase name: bytes} for one dir.ff."""
    if path in _ff_cache:
        return _ff_cache[path]
    data = _read(path)
    count = struct.unpack('<i', data[:4])[0]
    recs = []
    for i in range(count):
        o = 4 + i * 17
        off = struct.unpack('<i', data[o:o + 4])[0]
        name = cstr(data[o + 4:o + 17]).lower()
        recs.append((off, name))
    out = {}
    for i in range(len(recs) - 1):
        off, name = recs[i]
        if not name:
            continue
        nxt = recs[i + 1][0]
        if nxt == 0 and i + 2 < len(recs):
            nxt = recs[i + 2][0]
        out[name] = data[off:nxt]
    _ff_cache[path] = out
    return out


def _listdir_ci(d):
    try:
        return {f.lower(): f for f in os.listdir(d)}
    except FileNotFoundError:
        return {}


def find_dir_ci(base, rel):
    cur = base
    for part in rel.split('/'):
        if not part:
            continue
        m = _listdir_ci(cur).get(part.lower())
        if m is None:
            return None
        cur = os.path.join(cur, m)
    return cur


def frame_source(seqs, seq, frame, base=DINK, _depth=0):
    """Return (source_label, bmp_bytes, black_key) or None. Follows SET_FRAME_FRAME."""
    s = seqs.get(seq)
    if s is None or _depth > 4:
        return None
    if frame in s.alias and s.alias[frame][0] > 0:
        ss, sf = s.alias[frame]
        return frame_source(seqs, ss, sf, base, _depth + 1)
    d, _, stem = s.prefix.rpartition('/')
    fname = ('%s%02d.bmp' % (stem, frame)).lower()
    ddir = find_dir_ci(base, d)
    if ddir is None:
        return None
    loose = _listdir_ci(ddir)
    if fname in loose:
        p = os.path.join(ddir, loose[fname])
        return os.path.relpath(p, base), _read(p), s.black
    if 'dir.ff' in loose:
        ff = read_ff(os.path.join(ddir, loose['dir.ff']))
        if fname in ff:
            return os.path.relpath(os.path.join(ddir, 'dir.ff'), base) + ':' + fname, ff[fname], s.black
    return None


def load_frame_rgba(seqs, seq, frame, base=DINK):
    """(PIL RGBA image, source label) with the colour key made transparent."""
    from PIL import Image
    src = frame_source(seqs, seq, frame, base)
    if src is None:
        return None, None
    label, data, black = src
    im = Image.open(io.BytesIO(data)).convert('RGB')
    import numpy as np
    a = np.asarray(im).copy()
    key = 0 if black else 255
    mask = np.all(a == key, axis=2)
    alpha = np.where(mask, 0, 255).astype('uint8')
    rgba = np.dstack([a, alpha])
    return Image.fromarray(rgba, 'RGBA'), label


def tileset_path(ts, base=DINK):
    d = os.path.join(base, 'tiles')
    names = _listdir_ci(d)
    return os.path.join(d, names.get('ts%02d.bmp' % ts, 'ts%02d.bmp' % ts))


def tile_of(num):
    return num // 128 + 1, num % 128


# ---------------------------------------------------------------- hard.dat

def read_hard_index(base=DINK):
    """(blocks_bytes, index list). index[tile_num] -> hardness block id."""
    data = _read(os.path.join(base, 'hard.dat'))
    off = 800 * 2608
    n = (len(data) - off) // 4
    index = list(struct.unpack('<%di' % n, data[off:off + n * 4]))
    return data, index


def tile_hardness(num, hard=None, base=DINK):
    """Counts of hardness values (0 walk, 1 solid, 2 low, other) over the 50x50 cell."""
    import numpy as np
    data, index = hard or read_hard_index(base)
    if num >= len(index):
        return None
    b = index[num]
    if not (0 <= b < 800):
        return None
    blk = np.frombuffer(data, dtype=np.uint8, count=2601, offset=b * 2608).reshape(51, 51)[:50, :50]
    return {v: int((blk == v).sum()) for v in (0, 1, 2)} | {'other': int(((blk > 2)).sum())}
