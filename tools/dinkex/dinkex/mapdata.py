"""Parsers for ``dink.dat`` (world index) and ``map.dat`` (screen records).

Layouts: bible 04 section 1, verified against the shipped files.  All
integers are little-endian int32, ``bool`` is one byte, natural alignment.
"""

import os
import struct
from dataclasses import dataclass, field

from . import (SCREEN_COUNT, SCREENS_X, TILES_PER_SCREEN, TILES_PER_SET, TILES_X, TILE)

MAP_INFO_SIZE = 11488
SMALL_MAP_SIZE = 31280
TILE_SIZE = 80
SPRITE_SIZE = 220
SPRITE_BASE = 8020          # sprite[0] offset in small_map; indices 1..99 used
SPRITE_SLOTS = 101          # sprite[101]
ENGINE_SPRITE_MAX = 99      # place_sprites_game loops h1 = 1..99 (D:5966-5985)

_cstr_cache = {}


def cstr(b):
    """NUL-terminated latin-1 string (raw case preserved)."""
    return b.split(b"\0", 1)[0].decode("latin1")


@dataclass
class WorldIndex:
    name: str
    loc: list        # 769 ints, 1-based record in map.dat, 0 = none
    music: list      # 769
    indoor: list     # 769
    v: list
    s: str

    def used_screens(self):
        return [n for n in range(1, SCREEN_COUNT + 1) if self.loc[n] > 0]


def read_dink_dat(path):
    with open(path, "rb") as f:
        d = f.read()
    if len(d) < MAP_INFO_SIZE:
        raise ValueError("dink.dat is %d bytes, expected %d" % (len(d), MAP_INFO_SIZE))
    return WorldIndex(
        name=cstr(d[0:20]),
        loc=list(struct.unpack_from("<769i", d, 20)),
        music=list(struct.unpack_from("<769i", d, 20 + 769 * 4)),
        indoor=list(struct.unpack_from("<769i", d, 20 + 2 * 769 * 4)),
        v=list(struct.unpack_from("<40i", d, 20 + 3 * 769 * 4)),
        s=cstr(d[20 + 3 * 769 * 4 + 160: 20 + 3 * 769 * 4 + 240]),
    )


def music_info(raw, sound_dir_lookup=None):
    """Interpret a ``music[]`` value the way check_midi does (D:5309-5334).

    0 = nothing; -1 = stop; >1000 plays (N-1000).mid; otherwise N.mid.  The
    engine then prefers ``sound/N.ogg`` over ``sound/N.mid`` when it exists
    (PlayMidi, D:5237-5285).  ``sound_dir_lookup`` maps lower-case file name
    to real relative path (or None to skip file resolution).
    Note: the real code also falls through to the "N.mid" branch for -1
    (it would try to play "-1.mid", which does not exist); we report 'stop'.
    """
    if raw == 0:
        return {"raw": raw, "action": "none", "name": None, "file": None}
    if raw == -1:
        return {"raw": raw, "action": "stop", "name": None, "file": None}
    n = raw - 1000 if raw > 1000 else raw
    name = "%d.mid" % n
    file = None
    if sound_dir_lookup is not None:
        for cand in ("%d.ogg" % n, name):
            if cand in sound_dir_lookup:
                file = "sound/" + sound_dir_lookup[cand]
                break
    return {"raw": raw, "action": "play", "name": name, "file": file}


TILE_FMT = struct.Struct("<4iBB2x15i")      # 80 bytes
assert TILE_FMT.size == TILE_SIZE

# sprite_placement, 220 bytes (bible 04 section 1, dink.h)
SPRITE_HEAD = struct.Struct("<6i?3x")         # x,y,seq,frame,type,size,active (+pad) @0..28
assert SPRITE_HEAD.size == 28


def parse_tile(rec):
    num, prop, althard, more2, more3, more4, *buff = TILE_FMT.unpack(rec)
    return {
        "num": num, "property": prop, "althard": althard, "more2": more2,
        "more3": more3, "more4": more4, "buff": buff,
    }


def parse_sprite(rec):
    """Decode one 220-byte sprite_placement into a dict with every field."""
    x, y, seq, frame, typ, size, active = SPRITE_HEAD.unpack_from(rec, 0)
    rotation, special, brain = struct.unpack_from("<3i", rec, 28)
    script = cstr(rec[40:53])
    hit = cstr(rec[53:66])
    die = cstr(rec[66:79])
    talk = cstr(rec[79:92])
    (speed, base_walk, base_idle, base_attack, base_hit, timer, que, hard,
     alt_l, alt_t, alt_r, alt_b, prop, warp_map, warp_x, warp_y, parm_seq,
     base_die, gold, hitpoints, strength, defense, exp, sound, vision, nohit,
     touch_damage) = struct.unpack_from("<27i", rec, 92)
    buff = list(struct.unpack_from("<5i", rec, 200))
    return {
        "active": active, "x": x, "y": y, "seq": seq, "frame": frame, "type": typ, "size": size,
        "rotation": rotation, "special": special, "brain": brain,
        "script": script, "hit": hit, "die": die, "talk": talk,
        "speed": speed, "base_walk": base_walk, "base_idle": base_idle,
        "base_attack": base_attack, "base_hit": base_hit, "timer": timer, "que": que,
        "hard": hard, "alt": {"left": alt_l, "top": alt_t, "right": alt_r, "bottom": alt_b},
        "prop": prop, "warp_map": warp_map, "warp_x": warp_x, "warp_y": warp_y,
        "parm_seq": parm_seq, "base_die": base_die, "gold": gold, "hitpoints": hitpoints,
        "strength": strength, "defense": defense, "exp": exp, "sound": sound,
        "vision": vision, "nohit": nohit, "touch_damage": touch_damage, "buff": buff,
    }


@dataclass
class ScreenRecord:
    record: int                 # 1-based record number in map.dat
    name: str
    tiles: list                 # 96 dicts
    v: list
    s: str
    sprites: dict               # index (0..100) -> dict (only active ones)
    editor_hard_flags: list     # raw map.dat slots1..99, including inactive records
    sprite_slots_total: int
    script: str                 # base script (raw case)
    random: str
    load: str
    buffer_nonzero: bool


def parse_screen(blk, record):
    if len(blk) != SMALL_MAP_SIZE:
        raise ValueError("record %d is %d bytes, expected %d" % (record, len(blk), SMALL_MAP_SIZE))
    tiles = [parse_tile(blk[20 + t * TILE_SIZE: 20 + (t + 1) * TILE_SIZE]) for t in range(TILES_PER_SCREEN)]
    sprites = {}
    for i in range(SPRITE_SLOTS):
        off = SPRITE_BASE + i * SPRITE_SIZE
        rec = blk[off: off + SPRITE_SIZE]
        if rec[24]:   # active byte
            sprites[i] = parse_sprite(rec)
    return ScreenRecord(
        record=record, name=cstr(blk[0:20]), tiles=tiles,
        v=list(struct.unpack_from("<40i", blk, 7780)), s=cstr(blk[7940:8020]),
        sprites=sprites, editor_hard_flags=[struct.unpack_from("<i",blk,SPRITE_BASE+i*SPRITE_SIZE+120)[0] for i in range(1,ENGINE_SPRITE_MAX+1)], sprite_slots_total=SPRITE_SLOTS,
        script=cstr(blk[30240:30253]), random=cstr(blk[30253:30266]), load=cstr(blk[30266:30279]),
        buffer_nonzero=any(blk[30279:31280]),
    )


class MapDat:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        if len(self.data) % SMALL_MAP_SIZE:
            raise ValueError("map.dat size %d is not a multiple of %d" % (len(self.data), SMALL_MAP_SIZE))
        self.count = len(self.data) // SMALL_MAP_SIZE

    def record(self, k):
        """Parse record k (1-based)."""
        if not 1 <= k <= self.count:
            raise IndexError("map.dat has %d records, asked for %d" % (self.count, k))
        o = (k - 1) * SMALL_MAP_SIZE
        return parse_screen(self.data[o: o + SMALL_MAP_SIZE], k)


# Tile index maths (D:6774-6797) ------------------------------------------------

def tile_set_and_cell(num):
    """Raw tile number -> (tileset 1-based, cell index 0..127)."""
    return num // TILES_PER_SET + 1, num % TILES_PER_SET


def tile_source_rect(cell):
    """Cell index within a tileset -> (x, y, w, h) in tsNN.bmp (12 cells per row)."""
    return (cell % TILES_X) * TILE, (cell // TILES_X) * TILE, TILE, TILE


def screen_col_row(n):
    return (n - 1) % SCREENS_X, (n - 1) // SCREENS_X
