"""Scan map.dat/dink.dat/hard.dat/dink.ini and write the machine-derived inputs
for the classification tables:

  out/tile_usage.csv    one row per tile num used in map.dat
  out/sprite_usage.csv  one row per (seq, frame) placed in map.dat
  out/placements.csv    every active placement (screen, index, x, y, seq, frame, ...)

Usage: python3 scan_map.py
"""
import csv
import os
import re
import struct
from collections import Counter, defaultdict

import numpy as np

import dinkdata as d

OUT = os.path.join(d.REPO, 'tools', 'data', 'out')


def scan_tiles():
    data, index = d.read_hard_index()
    blocks = {}

    def blk(b):
        if b not in blocks:
            blocks[b] = np.frombuffer(data, dtype=np.uint8, count=2601,
                                      offset=b * 2608).reshape(51, 51)[:50, :50]
        return blocks[b]

    use = Counter()
    screens = defaultdict(set)
    indoor_use = Counter()
    solid = Counter()
    low = Counter()
    alt_used = Counter()
    for n, rec, indoor in d.iter_screens():
        for i in range(96):
            o = d.TILE_OFF + i * d.TILE_SZ
            num, _prop, althard = struct.unpack('<3i', rec[o:o + 12])
            use[num] += 1
            screens[num].add(n)
            if indoor:
                indoor_use[num] += 1
            h = althard if althard > 0 else (index[num] if num < len(index) else 0)
            if althard > 0:
                alt_used[num] += 1
            if 0 <= h < 800:
                a = blk(h)
                solid[num] += int(((a != 0) & (a != 2)).sum())
                low[num] += int((a == 2).sum())
    rows = []
    for num in sorted(use):
        ts, cell = d.tile_of(num)
        n = use[num]
        rows.append({
            'tile_num': num, 'tileset': ts, 'cell': cell, 'use_count': n,
            'screen_count': len(screens[num]),
            'indoor_use': indoor_use[num],
            'animated': 'water' if 896 <= num <= 1023 else ('fire' if 2304 <= num <= 2431 else ''),
            'hard_solid_pct': round(100.0 * solid[num] / (n * 2500), 1),
            'hard_low_pct': round(100.0 * low[num] / (n * 2500), 1),
            'althard_uses': alt_used[num],
            'example_screens': ' '.join(str(s) for s in sorted(screens[num])[:6]),
        })
    return rows


_script_cache = {}


def script_flags(name):
    """Gameplay hints read from a placement's DinkC script (.c source)."""
    if not name:
        return set()
    if name in _script_cache:
        return _script_cache[name]
    path = os.path.join(d.DINK, 'story', name + '.c')
    flags = set()
    if os.path.exists(path):
        src = open(path, 'rb').read().decode('latin1').lower()
        for proc in ('talk', 'hit', 'push', 'touch', 'die', 'use'):
            if re.search(r'void\s+%s\s*\(' % proc, src):
                flags.add(proc)
        if re.search(r'sp_seq\s*\(\s*&missile_target\s*,\s*20\s*\)', src):
            flags.add('burnable')
        if 'dam-bom' in src:
            flags.add('bombable')
    else:
        flags.add('script_missing')
    _script_cache[name] = flags
    return flags


def frame_size(seqs, seq, frame):
    src = d.frame_source(seqs, seq, frame)
    if src is None:
        return '', ''
    label, data, _ = src
    w, h = struct.unpack('<ii', data[18:26])
    return label, '%dx%d' % (w, abs(h))


def scan_sprites():
    seqs = d.read_dink_ini()
    P = d.all_placements()
    by = defaultdict(list)
    for p in P:
        by[(p.seq, p.frame)].append(p)
    rows = []
    for (seq, frame), ps in by.items():
        tc = Counter(p.type for p in ps)
        label, size = frame_size(seqs, seq, frame)
        scripts = Counter(p.script for p in ps if p.script)
        brains = Counter(p.brain for p in ps)
        fl = Counter()
        for p in ps:
            fl.update(script_flags(p.script))
        scr = sorted({p.screen for p in ps})
        rows.append({
            'seq': seq, 'frame': frame, 'placement_count': len(ps),
            'type0_background': tc.get(0, 0), 'type1_live': tc.get(1, 0),
            'type2_hardness_only': tc.get(2, 0),
            'source_file': label.replace(os.sep, '/'), 'pixel_size': size,
            'black_key': int(bool(seqs.get(seq) and seqs[seq].black)),
            'screen_count': len(scr),
            'warp_count': sum(1 for p in ps if p.prop == 1),
            'hard_count': sum(1 for p in ps if p.hard == 0),
            'scripts': ' '.join('%s:%d' % kv for kv in scripts.most_common(6)),
            'script_flags': ' '.join('%s:%d' % kv for kv in sorted(fl.items())),
            'vision_count': sum(1 for p in ps if p.vision),
            'brains': ' '.join('%d:%d' % kv for kv in sorted(brains.items())),
            'example_screens': ' '.join(str(s) for s in scr[:8]),
        })
    rows.sort(key=lambda r: (-r['placement_count'], r['seq'], r['frame']))
    return rows, P


def write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    t = scan_tiles()
    write(os.path.join(OUT, 'tile_usage.csv'), t)
    s, P = scan_sprites()
    write(os.path.join(OUT, 'sprite_usage.csv'), s)
    write(os.path.join(OUT, 'placements.csv'), [p._asdict() for p in P])
    print('tiles: %d distinct nums, %d cells' % (len(t), sum(r['use_count'] for r in t)))
    print('sprites: %d (seq,frame) pairs, %d placements, %d seqs'
          % (len(s), sum(r['placement_count'] for r in s), len({r['seq'] for r in s})))


if __name__ == '__main__':
    main()
