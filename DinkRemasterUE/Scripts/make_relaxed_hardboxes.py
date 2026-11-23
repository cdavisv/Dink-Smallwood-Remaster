#!/usr/bin/env python3
"""Which 1997 sprite hardboxes Dink may walk into in play (physical play layer, doc/remaster/PHYSICAL_PLAY_LAYER.md).

    python3 -I Scripts/make_relaxed_hardboxes.py <phys audit dir> --repo <checkout with tools/dinkex/out> [--out Content/Dink/Data/Play/relaxed_hardboxes.json]

A placement's box is RELAXED (the player's collision drops it; the drawn mesh's player-only blocker of PR #129 still stops Dink)
when: it is drawn by a family mesh that has a player blocker (Content/Dink/Data/Art/player_blockers.json), is unscripted, not a
warp and not a hardness-only placement, its drawn footprint covers less than --cover of the box (dink.PhysAudit cover_own), and
relaxing it opens no passage: on the 1997 hardness (3 px cells), the box cells outside the drawn footprint must touch at most one
walkable region of the screen. Boxes are taken one at a time, each test seeing the ones relaxed before it.
Everything the layer does not relax keeps the 1997 box (pixels, presentation of hardness unchanged).

Schema 2 (21 Nov 2026) adds, per relaxed placement, its drawn footprint ("feet": the audit's own_l/t/r/b, map pixels): in play the
1997 hardness the simulation reads keeps a relaxed box only there (review of PR #160, finding 2). And "open_tiles": tile cells
(row * 12 + col) whose 1997 tile hardness is a painted boulder the remaster draws as open ground (terrain grass_rocky of
tools/data/tile_classes.csv: playtest 20 Nov P1), freed by the same passage test (all the cell's hard pixels at once)."""
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
        return None, None, None
    code = Image.open(base + '.png').load()
    owner = Image.open(base + '_owner.png').load()
    free = [[code[min(599, x * CELL + 1), min(399, y * CELL + 1)] == 0 for x in range(GW)] for y in range(GH)]
    owners = {}
    tilehard = {}
    for y in range(GH):
        for x in range(GW):
            px, py = min(599, x * CELL + 1), min(399, y * CELL + 1)
            if code[px, py] == 100:
                owners.setdefault(owner[px, py], []).append((x, y))
            elif code[px, py] in (1, 2, 3):
                tilehard.setdefault((py // 50) * 12 + px // 50, []).append((x, y))
    return free, owners, tilehard


class World:
    """Which walkable regions of the 1997 map join across screen edges (32 x 24 screens; a region is (screen, label) on the
    3 px grid of the base hardness). Two regions in one world component are reachable from each other on foot in 1997, so a tile
    that joins them only shortens a way; regions touching a warp are their own component (never merged)."""
    def __init__(self, repo, screens):
        self.parent = {}
        self.labels = {}
        grids = {}
        for n in screens:
            free, _, _ = screen_grids(repo, n)
            if free is None:
                continue
            lab, _ = label_free(free)
            grids[n] = lab
        self.labels = grids
        for n, lab in grids.items():
            col = (n - 1) % 32
            east, south = n + 1, n + 32
            if col < 31 and east in grids:
                other = grids[east]
                for y in range(GH):
                    if lab[y][GW - 1] and other[y][0]:
                        self.union((n, lab[y][GW - 1]), (east, other[y][0]))
            if south in grids:
                other = grids[south]
                for x in range(GW):
                    if lab[GH - 1][x] and other[0][x]:
                        self.union((n, lab[GH - 1][x]), (south, other[0][x]))

    def find(self, k):
        self.parent.setdefault(k, k)
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb

    def same(self, screen, base_labels):
        roots = {self.find((screen, k)) for k in base_labels}
        return len(roots) <= 1


def open_tile_cells(repo, screen, open_classes, tile_classes):
    """Tile cells of the screen whose tile's terrain is one the remaster draws as open ground (grass_rocky)."""
    path = os.path.join(repo, 'tools', 'dinkex', 'out', 'screens', f'SCR_{screen:03d}.json')
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8') as f:
        scr = json.load(f)
    return {t['row'] * 12 + t['col'] for t in scr.get('tiles') or [] if tile_classes.get(int(t['num'])) in open_classes}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('audit')
    ap.add_argument('--repo', default=REPO)
    ap.add_argument('--blockers', default=os.path.join(HERE, '..', 'Content', 'Dink', 'Data', 'Art', 'player_blockers.json'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Content', 'Dink', 'Data', 'Play', 'relaxed_hardboxes.json'))
    ap.add_argument('--cover', type=float, default=0.7)
    ap.add_argument('--tile-classes', default=None, help='tools/data/tile_classes.csv (default: under --repo)')
    ap.add_argument('--open-terrain', default='grass_rocky', help='comma list of tile terrains drawn as open ground')
    ap.add_argument('--skip-screens', default='', help='comma list of screens left out of open tiles')
    a = ap.parse_args(argv)
    tile_classes = {}
    with open(a.tile_classes or os.path.join(a.repo, 'tools', 'data', 'tile_classes.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            tile_classes[int(r['tile_num'])] = r['terrain']
    open_classes = set(a.open_terrain.split(','))
    skip_screens = {int(x) for x in a.skip_screens.split(',') if x}
    with open(a.blockers, encoding='utf-8') as f:
        bj = json.load(f)
    blocked = {m['mesh'].split('.')[-1] for m in bj['meshes']}
    skip = set(bj.get('skip_origins', []))
    rows = {}
    with open(os.path.join(a.audit, 'phys_origins.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.setdefault(int(r['screen']), []).append(r)
    relaxed, kept, feet, open_tiles, kept_tiles = {}, [], {}, {}, []
    world = World(a.repo, sorted({int(fn[4:7]) for fn in os.listdir(os.path.join(a.repo, 'tools', 'dinkex', 'out', 'screens'))
                                  if fn.startswith('SCR_') and fn.endswith('.json') and fn[4:7].isdigit()}))
    screens_all = sorted(set(rows) | {int(fn[4:7]) for fn in os.listdir(os.path.join(a.repo, 'tools', 'dinkex', 'out', 'screens'))
                                       if fn.startswith('SCR_') and fn.endswith('.json') and fn[4:7].isdigit()})
    for screen in screens_all:
        cands = []
        for r in rows.get(screen, []):
            # walls are left out: their placement rule is still open (FIX.md of PhysicalMapping_15Nov2026)
            if r['kinds'] not in ('family', 'family_instance') or r['mesh'] not in blocked or r['origin'] in skip or 'Wall' in r['mesh']:
                continue
            if r['script'] or r['warp'] == '1' or r['type'] == '2' or int(r['stamped_px']) <= 0 or not r['origin'].startswith(f'S{screen:03d}_P'):
                continue
            if float(r['cover_own']) >= a.cover:
                continue
            cands.append(r)
        cells_open = set() if screen in skip_screens else open_tile_cells(a.repo, screen, open_classes, tile_classes)
        if not cands and not cells_open:
            continue
        free, owners, tilehard = screen_grids(a.repo, screen)
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
            feet.setdefault(str(screen), {})[str(n)] = [int(float(r[k])) for k in ('own_l', 'own_t', 'own_r', 'own_b')]
        # open tiles: a painted boulder's hardness, all hard cells of the tile at once, under the same passage test
        base_lab = world.labels.get(screen)
        for cell in sorted(cells_open):
            cells = tilehard.get(cell, [])
            if not cells:
                continue
            bad, touched = opens_passage(cells, lab, sizes)
            if bad and base_lab is not None:
                # the regions it joins, as 1997 labels: a shortcut between regions the 1997 map already joins on foot (through
                # neighbouring screens) is no passage; a region that touches a warp or none of the others stays apart
                base = set()
                for x, y in cells:
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < GW and 0 <= ny < GH and base_lab[ny][nx]:
                            base.add(base_lab[ny][nx])
                # an enclosed pocket (touches no screen edge: the inside of a painted boulder's outline) with no scripted placement
                # in it joins nothing a player could walk between in 1997
                edge = {base_lab[y][x] for y in range(GH) for x in (0, GW - 1)} | {base_lab[y][x] for x in range(GW) for y in (0, GH - 1)}
                scripted = {base_lab[min(GH - 1, max(0, int(float(r['sprite_y'])) // CELL))][min(GW - 1, max(0, int(float(r['sprite_x'])) // CELL))]
                            for r in rows.get(screen, []) if r['script']}
                base = {k for k in base if k in edge or k in scripted}
                bad = not world.same(screen, base)
            if bad:
                kept_tiles.append({'screen': screen, 'cell': cell, 'reason': 'passage: the tile closes a way between %d walkable regions' % len(touched)})
                continue
            k = next(iter(touched)) if touched else None
            if k is None:
                # an enclosed boulder (no walkable neighbour): nothing to free for anyone, but harmless: free it as its own region
                n_lab = max(sizes) + 1 if sizes else 1
                sizes[n_lab] = 0
                k = n_lab
            for x, y in cells:
                free[y][x] = True
                lab[y][x] = k
                sizes[k] += 1
            open_tiles.setdefault(str(screen), []).append(cell)
    out = {
        'schema': 'dink-relaxed-hardboxes/2',
        'about': 'Placements whose 1997 hardbox the player may enter while the physical play layer is on (doc/remaster/PHYSICAL_PLAY_LAYER.md); '
                 'made by Scripts/make_relaxed_hardboxes.py from a dink.PhysAudit run; never hand-edit. The drawn mesh keeps its player-only blocker.',
        'screens': {k: sorted(v) for k, v in sorted(relaxed.items(), key=lambda kv: int(kv[0]))},
        'kept': kept,
        'feet': {k: v for k, v in sorted(feet.items(), key=lambda kv: int(kv[0]))},
        'open_tiles': {k: sorted(v) for k, v in sorted(open_tiles.items(), key=lambda kv: int(kv[0]))},
        'kept_tiles': kept_tiles,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    print(f'{a.out}: {sum(len(v) for v in relaxed.values())} boxes relaxed on {len(relaxed)} screens, {len(kept)} kept (passage); '
          f'{sum(len(v) for v in open_tiles.values())} open tiles on {len(open_tiles)} screens, {len(kept_tiles)} kept (passage)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
