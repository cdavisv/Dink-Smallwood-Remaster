#!/usr/bin/env python3
"""Which 1997 sprite hardboxes Dink may walk into in play (physical play layer, doc/remaster/PHYSICAL_PLAY_LAYER.md).

    python3 -I Scripts/make_relaxed_hardboxes.py <phys audit dir> --repo <checkout with tools/dinkex/out> [--out Content/Dink/Data/Play/relaxed_hardboxes.json]

A placement's box is RELAXED (the player's collision drops it; the drawn mesh's player-only blocker of PR #129 still stops Dink)
when: it is drawn by a family mesh that has a player blocker (Content/Dink/Data/Art/player_blockers.json), is unscripted, not a
warp and not a hardness-only placement, its drawn footprint covers less than --cover of the box (dink.PhysAudit cover_own), and
relaxing it opens no passage: on the 1997 hardness (3 px cells), the box cells outside the drawn footprint must touch at most one
walkable region of the screen. Boxes are taken one at a time, each test seeing the ones relaxed before it.
Everything the layer does not relax keeps the 1997 box (pixels, presentation of hardness unchanged)."""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
CELL = 3
GW, GH = 200, 134
MIN_REGION = 30  # cells: smaller walkable pockets do not count as a region


def label_free(free):
    """4-connected labels of free cells (list of lists of bool); returns (labels, sizes)."""
    lab = [[0] * GW for _ in range(GH)]
    sizes = {}
    n = 0
    for y0 in range(GH):
        for x0 in range(GW):
            if not free[y0][x0] or lab[y0][x0]:
                continue
            n += 1
            stack = [(x0, y0)]
            lab[y0][x0] = n
            c = 0
            while stack:
                x, y = stack.pop()
                c += 1
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < GW and 0 <= ny < GH and free[ny][nx] and not lab[ny][nx]:
                        lab[ny][nx] = n
                        stack.append((nx, ny))
            sizes[n] = c
    return lab, sizes


def relax_cells(owner_cells, foot):
    """The cells a relaxed box frees: its own stamped cells outside the drawn footprint box (l, t, r, b in cells)."""
    l, t, r, b = foot
    return [(x, y) for x, y in owner_cells if not (l <= x <= r and t <= y <= b)]


def opens_passage(cells, lab, sizes):
    """True when the freed cells (taken together with their own connectivity) touch two or more walkable regions."""
    touched = set()
    for x, y in cells:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < GW and 0 <= ny < GH:
                k = lab[ny][nx]
                if k and sizes.get(k, 0) >= MIN_REGION:
                    touched.add(k)
    return len(touched) >= 2, touched


def screen_grids(repo, screen):
    from PIL import Image
    base = os.path.join(repo, 'tools', 'dinkex', 'out', 'hardness', f'SCR_{screen:03d}')
    if not os.path.exists(base + '.png') or not os.path.exists(base + '_owner.png'):
        return None, None
    code = Image.open(base + '.png').load()
    owner = Image.open(base + '_owner.png').load()
    free = [[code[min(599, x * CELL + 1), min(399, y * CELL + 1)] == 0 for x in range(GW)] for y in range(GH)]
    owners = {}
    for y in range(GH):
        for x in range(GW):
            px, py = min(599, x * CELL + 1), min(399, y * CELL + 1)
            if code[px, py] == 100:
                owners.setdefault(owner[px, py], []).append((x, y))
    return free, owners


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('audit')
    ap.add_argument('--repo', default=REPO)
    ap.add_argument('--blockers', default=os.path.join(HERE, '..', 'Content', 'Dink', 'Data', 'Art', 'player_blockers.json'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Content', 'Dink', 'Data', 'Play', 'relaxed_hardboxes.json'))
    ap.add_argument('--cover', type=float, default=0.7)
    a = ap.parse_args(argv)
    with open(a.blockers, encoding='utf-8') as f:
        bj = json.load(f)
    blocked = {m['mesh'].split('.')[-1] for m in bj['meshes']}
    skip = set(bj.get('skip_origins', []))
    rows = {}
    with open(os.path.join(a.audit, 'phys_origins.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.setdefault(int(r['screen']), []).append(r)
    relaxed, kept = {}, []
    for screen in sorted(rows):
        cands = []
        for r in rows[screen]:
            # walls are left out: their placement rule is still open (FIX.md of PhysicalMapping_15Nov2026)
            if r['kinds'] not in ('family', 'family_instance') or r['mesh'] not in blocked or r['origin'] in skip or 'Wall' in r['mesh']:
                continue
            if r['script'] or r['warp'] == '1' or r['type'] == '2' or int(r['stamped_px']) <= 0 or not r['origin'].startswith(f'S{screen:03d}_P'):
                continue
            if float(r['cover_own']) >= a.cover:
                continue
            cands.append(r)
        if not cands:
            continue
        free, owners = screen_grids(a.repo, screen)
        if free is None:
            continue
        lab, sizes = label_free(free)
        # biggest boxes first: they matter most and see the fewest earlier relaxations
        cands.sort(key=lambda r: -int(r['stamped_px']))
        for r in cands:
            n = int(r['origin'].split('_P')[1])
            foot = tuple(int(float(r[k]) // CELL) for k in ('own_l', 'own_t', 'own_r', 'own_b'))
            cells = relax_cells(owners.get(n, []), foot)
            if not cells:
                continue
            bad, touched = opens_passage(cells, lab, sizes)
            if bad:
                kept.append({'origin': r['origin'], 'mesh': r['mesh'], 'reason': 'passage: the box closes a way between %d walkable regions' % len(touched)})
                continue
            if not touched:
                continue
            k = next(iter(touched))
            for x, y in cells:
                free[y][x] = True
                lab[y][x] = k
                sizes[k] += 1
            relaxed.setdefault(str(screen), []).append(n)
    out = {
        'schema': 'dink-relaxed-hardboxes/1',
        'about': 'Placements whose 1997 hardbox the player may enter while the physical play layer is on (doc/remaster/PHYSICAL_PLAY_LAYER.md); '
                 'made by Scripts/make_relaxed_hardboxes.py from a dink.PhysAudit run; never hand-edit. The drawn mesh keeps its player-only blocker.',
        'screens': {k: sorted(v) for k, v in sorted(relaxed.items(), key=lambda kv: int(kv[0]))},
        'kept': kept,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    print(f'{a.out}: {sum(len(v) for v in relaxed.values())} boxes relaxed on {len(relaxed)} screens, {len(kept)} kept (passage)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
