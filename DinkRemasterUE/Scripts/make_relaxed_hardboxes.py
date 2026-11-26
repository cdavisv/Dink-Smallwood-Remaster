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
import re
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


def read_audit_tiles(audit, share):
    """A92: screen -> tile cells the dink.PhysAudit summary (phys_mismatches.csv) lists as an invisible wall of low tile hardness (on
    open grass, sand, snow, stone floors) with nothing drawn on at least `share` of the tile's contact edge."""
    path = os.path.join(audit, 'phys_mismatches.csv')
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            # low (2) only: a painted rock, ledge or boulder line like grass_rocky's (projectiles cross it in 1997 too); a solid tile
            # line (a fence, a wall base, a structure outline under a sprite) stays for the art row PM-05 to draw
            if not r['category'].startswith('1 invisible wall (tile low'):
                continue
            m = re.search(r'on (\d+)% of', r['detail'])
            t = re.match(r'tile (\d+),(\d+)', r['subject'])
            if not m or not t or int(m.group(1)) < share * 100:
                continue
            out.setdefault(int(r['screen']), set()).add(int(t.group(2)) * 12 + int(t.group(1)))
    return out


BLOB_MAX_PX = 60


def tile_is_blobs(repo, screen, cell, cache={}):
    """A92: every piece of hard tile pixels (codes 1-3, 8-connected, followed into the neighbouring tiles) that reaches into the tile
    is a blob no wider and no taller than BLOB_MAX_PX: a painted rock or boulder, not a line (a fence, hedge, ledge or bank)."""
    from PIL import Image
    if screen not in cache:
        path = os.path.join(repo, 'tools', 'dinkex', 'out', 'hardness', f'SCR_{screen:03d}.png')
        cache.clear()
        cache[screen] = Image.open(path).load() if os.path.exists(path) else None
    px = cache[screen]
    if px is None:
        return False
    hard = lambda x, y: 0 <= x < 600 and 0 <= y < 400 and px[x, y] in (1, 2, 3)
    tx, ty = (cell % 12) * 50, (cell // 12) * 50
    seen = set()
    for y0 in range(ty, ty + 50):
        for x0 in range(tx, tx + 50):
            if (x0, y0) in seen or not hard(x0, y0):
                continue
            stack, l, t, r, b = [(x0, y0)], x0, y0, x0, y0
            seen.add((x0, y0))
            while stack:
                x, y = stack.pop()
                l, t, r, b = min(l, x), min(t, y), max(r, x), max(b, y)
                if r - l > BLOB_MAX_PX or b - t > BLOB_MAX_PX:
                    return False
                for nx in (x - 1, x, x + 1):
                    for ny in (y - 1, y, y + 1):
                        if (nx, ny) not in seen and hard(nx, ny):
                            seen.add((nx, ny))
                            stack.append((nx, ny))
    return True


def read_fills(path):
    """screen -> 3 px cells of the export's water and void fills (collision.json fill_water, fill_solid): 1997 hardness 0 that the
    remaster closes for everyone (open sea, canopy interiors, the black void round rooms)."""
    with open(path, encoding='utf-8') as f:
        coll = json.load(f)['screens']
    out = {}
    for sid, c in coll.items():
        cells = set()
        for l, t, r, b in (c.get('fill_water') or []) + (c.get('fill_solid') or []):
            for y in range(max(0, t) // CELL, min(GH, (b + CELL - 1) // CELL)):
                for x in range(max(0, l) // CELL, min(GW, (r + CELL - 1) // CELL)):
                    if l <= x * CELL + 1 < r and t <= y * CELL + 1 < b:
                        cells.add((x, y))
        out[int(sid[4:])] = cells
    return out


WALL_MESHES = ('Wall_Plaster', 'Wall_Dungeon')


def wall_candidates(rows, screen):
    """A71: interior and dungeon wall modules (family meshes, unscripted, no warp) whose drawn body-height footprint is a thin strip:
    the wall is drawn on one line of its thick 1997 box (often the room-side face, but door jambs, corner posts and short modules
    stand inside it). -> [(placement, trim rect l, t, r, b inclusive map px)]: the drawn strip, run on along its length to the box's
    ends so the wall line stays closed where the module is drawn shorter than its box."""
    out = []
    for r in rows:
        if r['kinds'] not in ('family', 'family_instance') or not any(w in r['mesh'] for w in WALL_MESHES):
            continue
        if r['script'] or r['warp'] == '1' or r['type'] == '2' or int(r['stamped_px']) <= 0 or not r['origin'].startswith(f'S{screen:03d}_P'):
            continue
        l, t, rr, b = (float(r[k]) for k in ('own_l', 'own_t', 'own_r', 'own_b'))
        bl, bt, br, bb = (float(r[k]) for k in ('box_l', 'box_t', 'box_r', 'box_b'))
        if rr <= l and b <= t:
            continue
        w, h = rr - l, b - t
        if min(w, h) > 0.35 * max(w, h) or max(w, h) < 10:
            continue  # not a straight strip (a curve, an arch, a post): its box stays
        if w >= h:   # runs east-west: the drawn rows, the box's columns
            rect = (max(0, int(bl)), int(t), min(599, int(br) - 1), max(int(b), int(t) + 2))
        else:        # runs north-south
            rect = (int(l), max(0, int(bt)), max(int(rr), int(l) + 2), min(399, int(bb) - 1))
        box = (max(0, int(bl)), max(0, int(bt)), min(599, int(br) - 1), min(399, int(bb) - 1))
        out.append((int(r['origin'].split('_P')[1]), rect, box, (int(l), int(t), int(rr), int(b))))
    return out


def wall_joints(n, walls, trimmed_screen):
    """A71 at the enlarged scale (26 Nov 2026): where a wall's drawn strip and the strip of a trimmed wall whose box overlaps it along the
    same line are staggered (SCR_713: P06 drawn at y 206-213, P13 at y 222-229, boxes overlapping at x 246-271), trimming both opens the
    slot between the two strips. The joint keeps, whoever's box owns the pixels there: each wall's drawn strip over the overlap (as far as
    its module is drawn) and a plug three pixels wide across the slot where the two modules meet. Rects in map pixels, inclusive."""
    by_n = {w[0]: w for w in walls}
    me = by_n.get(n)
    if me is None:
        return []
    _, (sl, st, sr, sb), (bl, bt, br, bb), (ol, ot, orr, ob) = me
    along_x = sr - sl >= sb - st
    out = []
    for v, (vsl, vst, vsr, vsb), (vbl, vbt, vbr, vbb), (vol, vot, vorr, vob) in walls:
        if v == n or str(v) not in trimmed_screen or (vsr - vsl >= vsb - vst) != along_x:
            continue
        if along_x:
            lo, hi = max(bl, vbl), min(br, vbr)          # the boxes' overlap along the line
            if hi < lo or max(bt, vbt) > min(bb, vbb) or not (vst > sb or vsb < st):
                continue  # no overlap, or the two strips line up (no slot between them)
            west = ol <= vol                               # this wall is drawn west of the other
            meet = (orr + vol) / 2.0 if west else (vorr + ol) / 2.0
            m = int(round(min(max(meet, lo), hi)))
            mine = (lo, st, min(hi, orr), sb) if west else (max(lo, ol), st, hi, sb)
            theirs = (max(lo, vol), vst, hi, vsb) if west else (lo, vst, min(hi, vorr), vsb)
            plug = (m - 1, min(sb, vsb), m + 1, max(st, vst))
        else:
            lo, hi = max(bt, vbt), min(bb, vbb)
            if hi < lo or max(bl, vbl) > min(br, vbr) or not (vsl > sr or vsr < sl):
                continue
            north = ot <= vot
            meet = (ob + vot) / 2.0 if north else (vob + ot) / 2.0
            m = int(round(min(max(meet, lo), hi)))
            mine = (sl, lo, sr, min(hi, ob)) if north else (sl, max(lo, ot), sr, hi)
            theirs = (vsl, max(lo, vot), vsr, hi) if north else (vsl, lo, vsr, min(hi, vob))
            plug = (min(sr, vsr), m - 1, max(sl, vsl), m + 1)
        for r in (mine, theirs, plug):
            if r[2] >= r[0] and r[3] >= r[1]:
                out.append(tuple(int(x) for x in r))
    return out


def rect_cells(rects):
    """3 px cells touched by map-pixel rects (inclusive)."""
    out = set()
    for l, t, r, b in rects:
        for y in range(max(0, t) // CELL, min(GH - 1, b // CELL) + 1):
            for x in range(max(0, l) // CELL, min(GW - 1, r // CELL) + 1):
                out.add((x, y))
    return out


def trim_walls(screen, walls, free, owners, fill_cells, relaxed, feet, trimmed, kept, joints=None):
    """Trims each wall box to its drawn strip when no passage opens: on the 1997 hardness at 3 px less the export's fills (nobody walks
    the void or the sea), every 4-connected piece of the freed box cells touches at most one walkable region (a room on each side of a
    partition stays two rooms: the strip still parts them). A wall that fails only because its strip and a trimmed neighbour's are
    staggered is trimmed with a joint (wall_joints) when the joint closes the slot: the joint's rects go to `joints` (kept solid for
    Dink in play whoever's box owns the pixel)."""
    fill_cells = fill_cells or set()
    ground = [[free[y][x] and (x, y) not in fill_cells for x in range(GW)] for y in range(GH)]
    lab, sizes = label_free(ground)
    owner_of = {c: o for o, cs in owners.items() for c in cs}
    for n, (l, t, r, b), box, _own in walls:
        keep = lambda x, y: x * CELL + CELL > l and x * CELL <= r and y * CELL + CELL > t and y * CELL <= b
        cells = [(x, y) for x, y in owners.get(n, []) if not keep(x, y)]
        if not cells:
            continue
        bad, useful, pieces = freed_pieces_test(cells, lab, sizes)
        joint = []
        if bad and joints is not None:
            joint = wall_joints(n, walls, trimmed.get(str(screen), {}))
            if joint:
                jcells = rect_cells(joint)
                # the joint stands for everyone's box under it: cells another trimmed wall freed are walls again
                trial = [row[:] for row in ground]
                for x, y in jcells:
                    if owner_of.get((x, y)) is not None:
                        trial[y][x] = False
                tlab, tsizes = label_free(trial)
                tcells = [c for c in cells if c not in jcells]
                tbad, tuseful, tpieces = freed_pieces_test(tcells, tlab, tsizes)
                if not tbad and tuseful:
                    ground, lab, sizes, cells, pieces, bad, useful = trial, tlab, tsizes, tcells, tpieces, False, True
                else:
                    joint = []
        if bad:
            kept.append({'origin': f'S{screen:03d}_P{n:02d}', 'mesh': 'wall', 'reason': 'passage: a freed piece of the wall box joins two walkable regions'})
            continue
        if not useful:
            continue  # nobody can reach the freed part: nothing to gain
        for piece in pieces:
            k = None
            for x, y in piece:
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < GW and 0 <= ny < GH and lab[ny][nx] and sizes.get(lab[ny][nx], 0) >= MIN_REGION:
                        k = lab[ny][nx]
            if k is None:
                continue
            for x, y in piece:
                ground[y][x] = True
                lab[y][x] = k
                sizes[k] += 1
        relaxed.setdefault(str(screen), []).append(n)
        feet.setdefault(str(screen), {})[str(n)] = [l, t, r, b]
        trimmed.setdefault(str(screen), {})[str(n)] = list(box)
        if joint:
            joints.setdefault(str(screen), []).extend([list(j) for j in joint])


def freed_pieces_test(cells, lab, sizes):
    """The 4-connected pieces of freed cells; bad = a piece touches two walkable regions, useful = a piece touches exactly one."""
    # pieces of the freed cells
    todo, pieces = set(cells), []
    while todo:
        seed = todo.pop()
        piece, stack = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in todo:
                    todo.discard(q)
                    piece.append(q)
                    stack.append(q)
        pieces.append(piece)
    bad, useful = False, False
    for piece in pieces:
        touched = set()
        for x, y in piece:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < GW and 0 <= ny < GH and lab[ny][nx] and sizes.get(lab[ny][nx], 0) >= MIN_REGION:
                    touched.add(lab[ny][nx])
        bad |= len(touched) >= 2
        useful |= len(touched) == 1
    return bad, useful, pieces


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
    ap.add_argument('--audit-tiles', type=float, default=0.9,
                    help='A92: also open the tiles the audit lists as invisible low walls (phys_mismatches.csv category 1, tile low) when nothing is '
                         'drawn on at least this share of their contact edge; 0 = off')
    ap.add_argument('--collision', default=None,
                    help='A71: the export\'s collision.json (ImportData/collision.json of a generated copy): its water and void fills are '
                         'nobody\'s ground in the wall passage test. Without it no wall is trimmed')
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
    relaxed, kept, feet, open_tiles, kept_tiles, trimmed, joints = {}, [], {}, {}, [], {}, {}
    audit_tiles = read_audit_tiles(a.audit, a.audit_tiles) if a.audit_tiles > 0 else {}
    fills = read_fills(a.collision) if a.collision else None
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
        # A92: the audit's other low tiles; these open only where they join nothing (no shortcut rule: a long low line can be an
        # undrawn fence or hedge that routes the player, art row PM-05)
        audit_only = set() if screen in skip_screens else audit_tiles.get(screen, set()) - cells_open
        if audit_only:
            audit_only = {c for c in audit_only if tile_is_blobs(a.repo, screen, c)}
        cells_open |= audit_only
        walls = wall_candidates(rows.get(screen, []), screen) if fills is not None else []
        if not cands and not cells_open and not walls:
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
                # (A92's audit tiles: no shortcut at all, only the pocket inside a blob's own outline)
                bad = len(base) >= 2 if cell in audit_only else not world.same(screen, base)
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
        # walls (A71), after the boxes and tiles so that their results do not depend on this step
        if walls:
            trim_walls(screen, walls, free, owners, fills.get(screen), relaxed, feet, trimmed, kept, joints)
    out = {
        'schema': 'dink-relaxed-hardboxes/2',
        'about': 'Placements whose 1997 hardbox the player may enter while the physical play layer is on (doc/remaster/PHYSICAL_PLAY_LAYER.md); '
                 'made by Scripts/make_relaxed_hardboxes.py from a dink.PhysAudit run; never hand-edit. The drawn mesh keeps its player-only blocker.',
        'screens': {k: sorted(v) for k, v in sorted(relaxed.items(), key=lambda kv: int(kv[0]))},
        'kept': kept,
        'feet': {k: v for k, v in sorted(feet.items(), key=lambda kv: int(kv[0]))},
        'open_tiles': {k: sorted(v) for k, v in sorted(open_tiles.items(), key=lambda kv: int(kv[0]))},
        'kept_tiles': kept_tiles,
        'trimmed': {k: v for k, v in sorted(trimmed.items(), key=lambda kv: int(kv[0]))},
        'joints': {k: v for k, v in sorted(joints.items(), key=lambda kv: int(kv[0]))},
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
        f.write('\n')
    print(f'{a.out}: {sum(len(v) for v in relaxed.values())} boxes relaxed on {len(relaxed)} screens, {len(kept)} kept (passage); '
          f'{sum(len(v) for v in open_tiles.values())} open tiles on {len(open_tiles)} screens, {len(kept_tiles)} kept (passage); '
          f'{sum(len(v) for v in trimmed.values())} walls trimmed to their drawn face on {len(trimmed)} screens, '
          f'{sum(len(v) for v in joints.values())} joint rects on {len(joints)} screens')
    return 0


if __name__ == '__main__':
    sys.exit(main())
