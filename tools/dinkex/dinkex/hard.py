"""``hard.dat`` and the engine's collision-map build.

``struct hardness { ts_block tile[800]; int32 index[8000]; }`` where a
``ts_block`` is 2608 bytes: ``uint8 px[51][51]`` indexed [x][y] (only 0..49
are used), ``bool used``, ``int32 hold``.  The index starts at byte 2,086,400.

Traps (all handled exactly as the engine does):

* The shipped file is 2,107,392 bytes, 11,008 short of the struct.  All 800
  tile blocks are present but only the first 5,248 (= 41 x 128) of the 8,000
  index entries.  The engine memset()s the struct before a short read
  (D:326), so missing index entries read as 0, i.e. "use hardness tile 0".
* 106 of the 5,248 present index entries are out of range (negative or >= 800).
  fill_whole_hard (D:654-681) refuses to write such a tile and leaves the
  hit-map unchanged for that whole 50x50 cell (it ``goto skip``s on the very
  first pixel).  The hit-map is never cleared between screens, so "unchanged"
  means "whatever the previous screen left there".  For reproducible output
  we start every screen from 0 and report the affected cells.
* ``tile.althard > 0`` overrides the index (``realhard``, D:648).
"""

import struct

import numpy as np

from . import PLAY_W, PLAY_H, TILE, TILES_X, TILES_PER_SCREEN, SPRITE_X_OFFSET

BLOCK_BYTES = 2608
BLOCK_COUNT = 800
INDEX_COUNT = 8000
INDEX_OFFSET = BLOCK_COUNT * BLOCK_BYTES        # 2,086,400
FULL_SIZE = INDEX_OFFSET + INDEX_COUNT * 4      # 2,118,400

# Pixel codes of the hardness PNGs written by the extractor.
CODE_WALKABLE = 0
CODE_SOLID = 1          # tile hardness 1
CODE_LOW = 2            # tile hardness 2 ("low": water, fences; missiles/flyers pass)
CODE_OTHER = 3          # any other non-zero tile value (a single block holds one "3")
CODE_SPRITE = 100       # hardbox stamped by a placed sprite (engine value 100+index)
CODE_WARP = 200         # hardbox of a placement whose prop != 0 (warp trigger)

CODE_NAMES = {
    CODE_WALKABLE: "walkable",
    CODE_SOLID: "solid (tile hardness 1)",
    CODE_LOW: "low (tile hardness 2; projectiles and flyers cross)",
    CODE_OTHER: "other non-zero tile hardness (blocks)",
    CODE_SPRITE: "sprite hardbox, blocks",
    CODE_WARP: "sprite hardbox with prop != 0 (warp trigger)",
}


class HardDat:
    def __init__(self, data):
        self.file_size = len(data)
        self.short_by = max(0, FULL_SIZE - len(data))
        # Zero-fill a short read exactly like the memset'd engine buffer.
        buf = data[:FULL_SIZE].ljust(FULL_SIZE, b"\0")
        blocks = np.frombuffer(buf, dtype=np.uint8, count=INDEX_OFFSET).reshape(BLOCK_COUNT, BLOCK_BYTES)
        px = blocks[:, : 51 * 51].reshape(BLOCK_COUNT, 51, 51)     # [block][x][y]
        # Keep the used 50x50 area, transposed to [block][y][x] for images.
        self.tiles = np.ascontiguousarray(px[:, :TILE, :TILE].transpose(0, 2, 1))
        self.index = np.frombuffer(buf, dtype="<i4", count=INDEX_COUNT, offset=INDEX_OFFSET).copy()
        self.index_entries_in_file = max(0, min(INDEX_COUNT, (len(data) - INDEX_OFFSET) // 4))
        self.used_flags_nonzero = int(blocks[:, 2601].any())

    @classmethod
    def from_file(cls, path):
        with open(path, "rb") as f:
            return cls(f.read())

    def lookup(self, num, althard):
        """realhard(): return (hardness_tile_id, source, valid).

        source is 'althard', 'index', or 'index_beyond_file' (entry missing from
        the short file, reads as 0).  valid is the engine's 0 <= id < 800 test.
        """
        if althard > 0:
            hid, src = althard, "althard"
        else:
            if 0 <= num < INDEX_COUNT:
                hid = int(self.index[num])
                src = "index" if num < self.index_entries_in_file else "index_beyond_file"
            else:
                # g_hmap.index[num] would read past the table (undefined in C++);
                # no shipped tile does this.
                hid, src = 0, "index_out_of_table"
        return hid, src, 0 <= hid < BLOCK_COUNT


def tile_cell_origin(t):
    """Tile index 0..95 -> (x, y) of its top-left pixel in the 600x400 map."""
    return (t % TILES_X) * TILE, (t // TILES_X) * TILE


def build_tile_layer(hard, tiles):
    """fill_whole_hard(): returns (hitmap uint8[400][600], skipped_tile_indices)."""
    hit = np.zeros((PLAY_H, PLAY_W), dtype=np.uint8)
    skipped = []
    for t in range(TILES_PER_SCREEN):
        tl = tiles[t]
        hid, _src, valid = hard.lookup(tl["num"], tl["althard"])
        if not valid:
            skipped.append(t)
            continue
        x0, y0 = tile_cell_origin(t)
        hit[y0:y0 + TILE, x0:x0 + TILE] = hard.tiles[hid]
    return hit, skipped


def placement_rank(sprites):
    """Order in which place_sprites_game visits placements (D:5966-6000).

    ``sprites``: dict index -> placement dict.  Repeatedly picks the not yet
    taken active placement with the smallest ``que`` (or ``y`` when que is 0);
    ties go to the lower index.  Only indices 1..99 are considered.  Entries
    with a key of 20000 or more are never ranked (the engine's start value).
    """
    cand = {i: s for i, s in sprites.items() if 1 <= i <= 99 and s["active"]}
    order = []
    taken = set()
    for _ in range(1, 100):
        best, best_i = 20000, None
        for i in sorted(cand):
            if i in taken:
                continue
            s = cand[i]
            key = s["que"] if s["que"] != 0 else s["y"]
            if key < best:
                best, best_i = key, i
        if best_i is None:
            break
        taken.add(best_i)
        order.append(best_i)
    return order


def stamp_rect(sprite, hardbox):
    """add_hardness() target rectangle in 600x400 map coordinates, clipped.

    Returns (x0, y0, x1, y1) with x1, y1 exclusive, or None if empty.
    The engine writes hit-map columns/rows 0..600 / 0..400 inclusive (it skips
    only xx-20 > 600 and yy > 400); the extra column and row lie outside the
    600x400 play field and are dropped here.
    """
    x0 = sprite["x"] + hardbox["left"] - SPRITE_X_OFFSET
    x1 = sprite["x"] + hardbox["right"] - SPRITE_X_OFFSET
    y0 = sprite["y"] + hardbox["top"]
    y1 = sprite["y"] + hardbox["bottom"]
    cx0, cx1 = max(x0, 0), min(x1, PLAY_W)
    cy0, cy1 = max(y0, 0), min(y1, PLAY_H)
    if cx0 >= cx1 or cy0 >= cy1:
        return None
    return cx0, cy0, cx1, cy1


def build_hitmap(hard, screen_tiles, sprites, hardbox_of, vision=0):
    """Rebuild the engine's collision map for one screen.

    hardbox_of(sprite_dict) -> {'left','top','right','bottom'} or None.
    Returns (codes uint8[400][600], owner uint8[400][600], info dict).
    ``codes`` uses the CODE_* values; ``owner`` holds the placement index of the
    last sprite that stamped each pixel (0 = tile layer only).
    """
    tiles_hit, skipped = build_tile_layer(hard, screen_tiles)
    codes = np.where(tiles_hit > 3, CODE_OTHER, tiles_hit).astype(np.uint8)
    owner = np.zeros_like(codes)
    stamps = []
    for i in placement_rank(sprites):
        s = sprites[i]
        if s["vision"] != 0 and s["vision"] != vision:
            continue
        if s["hard"] != 0:          # inverted flag: 0 = HAS hardness
            continue
        hb = hardbox_of(s)
        if hb is None:
            stamps.append({"placement": i, "rect": None, "reason": "no_pic"})
            continue
        r = stamp_rect(s, hb)
        stamps.append({"placement": i, "rect": list(r) if r else None,
                       "reason": None if r else "empty_or_outside"})
        if r is None:
            continue
        x0, y0, x1, y1 = r
        codes[y0:y1, x0:x1] = CODE_WARP if s["prop"] != 0 else CODE_SPRITE
        owner[y0:y1, x0:x1] = i
    return codes, owner, {"skipped_tiles": skipped, "stamps": stamps}
