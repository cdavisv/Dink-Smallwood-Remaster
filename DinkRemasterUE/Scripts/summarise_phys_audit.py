#!/usr/bin/env python3
"""Summarise a dink.PhysAudit run (phys_origins.csv, phys_warps.csv, phys_tiles.csv, phys_screens.csv, phys_drawn_mask.csv)
into per-category counts, distributions and ranked mismatch lists (physical mapping audit, 15 Nov 2026).

    python3 -I Scripts/summarise_phys_audit.py <audit dir> [--walk-mask <walk_mask.csv>] [--out <report dir>]

Categories (README of Docs/Verification/PhysicalMapping_15Nov2026):
  1 invisible walls      stamped sprite hardboxes / solid tile hardness with nothing drawn within the tolerance
  2 hardbox vs mesh      placements that block: hardbox rectangle against the footprint of the meshes that draw them
  3 creatures and NPCs   the 1997 hit box (hardbox + run_through_tag_list's reach) against the drawn body
  4 pickups and warps    touch box (hardbox + 2 px + capsule margin) against the mesh; warp trigger against the door
  6 terrain              tiles drawn as water/cliff that the capsule can stand on, open tiles it cannot (walk mask)
  7 standing inside      live sprites whose feet are inside another placement's drawn body
The 1997 numbers: run_through_tag_list (source/dink/dink.cpp:15460-15527, ported in UDinkGameplay::RunThroughTagList):
target hardbox grown by 5 px (10 px at the bottom), then by Dink's range towards the attacker (40 px with any sword,
item-sw1/2/3.c:42; 28 bare-handed) and 10 px to each side (range + range / 6 vertically). Touch: hardbox + 2 px + the capsule radius in pixels (dink.cpp:15629-15651 plus the remaster's capsule margin, UDinkGameplay::RunThroughTouchDamageList).
"""
import argparse
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict

TOL_CM = 40.0
CAPSULE_CM = 28.0  # ADinkGreyboxCharacter capsule radius
SWORD_CM = 85.0  # authored.ini AttackReachCm at range 0 (fists); AuthoredGeometryMatches scales it by range / 28
SWORD_RANGE = 40  # item-sw1.c / item-sw2.c / item-sw3.c:42 sp_range(1, 40): every sword
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))

BLOCKED_TERRAIN = {'water', 'cliff_face', 'rock_mass', 'chasm', 'lava', 'cave_wall', 'void', 'structure_facade'}
OPEN_TERRAIN = {'grass', 'path', 'sand', 'stone_floor', 'cave_floor', 'gravel', 'dirt', 'wood_floor', 'snow', 'wasteland', 'grass_rocky', 'ice'}


def rle_decode(mask):
    """'12F3B..' -> list of chars."""
    out, n = [], ''
    for ch in mask:
        if ch.isdigit():
            n += ch
        else:
            out.extend(ch * int(n or '1'))
            n = ''
    return out


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def num(r, k, default=0.0):
    try:
        return float(r.get(k, default) or default)
    except ValueError:
        return default


def attack_gaps(box, body, cm, rng=SWORD_RANGE):
    """1997 hit region vs the drawn body, per approach side, in cm.

    box = (l, t, r, b) hardbox in map px, body = (l, t, r, b) drawn body in map px, rng = Dink's sp_range (40 with any sword,
    item-sw1/2/3.c:42; 0 bare-handed). run_through_tag_list (dink.cpp:15460-15527) grows the target's box by 5 px (10 at the
    bottom), then by amount = range (28 when 0) towards the attacker and amounty = range + range / 6 (36 when 0) vertically.
    The visible reach is the capsule radius plus the authored sword reach (85 cm at range 0, scaled by range / 28 as
    UDinkGameplay::AuthoredGeometryMatches does). far_hit > 0: a hit registers with the sword that far short of the body;
    miss > 0: the sword visibly lands that deep in the body and the hit does not register.
    Returns {side: (far_hit_cm, miss_cm)} for sides W (Dink west of the target, facing east, dir 6), E (dir 4), N (dir 2), S (dir 8).
    """
    l, t, r, b = box
    bl, bt, br, bb = body
    amount = 28 if rng == 0 else rng
    amounty = 36 if rng == 0 else rng + rng // 6
    reach = (CAPSULE_CM + SWORD_CM * (rng / 28.0 if rng > 0 else 1.0)) / cm
    reg = {'W': l - 5 - amount, 'E': r + 5 + amount, 'N': t - 5 - amounty, 'S': b + 10 + amounty}
    vis = {'W': bl - reach, 'E': br + reach, 'N': bt - reach, 'S': bb + reach}
    out = {}
    for side in 'WENS':
        sign = -1 if side in 'WN' else 1  # outward direction
        d = (reg[side] - vis[side]) * sign  # > 0: registered limit lies farther out than the sword reaches
        out[side] = (max(0.0, d) * cm, max(0.0, -d) * cm)
    return out


def touch_gaps(box, own, cm):
    """Touch rectangle (hardbox + 2 px + capsule margin) vs the drawn pickup (bbox), cm. far: picked up with the capsule that far
    from the mesh; miss: the capsule's centre can stand that deep over the mesh without the touch."""
    l, t, r, b = box
    m = 2 + math.ceil(CAPSULE_CM / cm)
    reg = (l - m, t - m, r + m, b + m)
    cap = CAPSULE_CM / cm
    vis = (own[0] - cap, own[1] - cap, own[2] + cap, own[3] + cap)
    far = max(vis[0] - reg[0], vis[1] - reg[1], reg[2] - vis[2], reg[3] - vis[3], 0.0) * cm
    # the centre over the mesh itself but outside the touch rectangle
    miss = max(reg[0] - own[0], reg[1] - own[1], own[2] - reg[2], own[3] - reg[3], 0.0) * cm
    return far, miss


def load_tiles(repo=REPO):
    """screen -> 96 terrain classes (12 x 8 tiles of 50 px), from tools/dinkex/out and tools/data/tile_classes.csv."""
    classes = {}
    tc = os.path.join(repo, 'tools', 'data', 'tile_classes.csv')
    for r in read_csv(tc):
        classes[int(r['tile_num'])] = r['terrain']
    screens, neighbours = {}, {}
    sd = os.path.join(repo, 'tools', 'dinkex', 'out', 'screens')
    if not os.path.isdir(sd):
        return screens, neighbours
    for name in os.listdir(sd):
        if not name.startswith('SCR_'):
            continue
        with open(os.path.join(sd, name), encoding='utf-8') as f:
            d = json.load(f)
        screens[d['screen']] = [classes.get(t['num'], '?') for t in d['tiles']]
        neighbours[d['screen']] = d.get('neighbours', {})
    return screens, neighbours


def cell_distance(drawn_cells, rows=134, cols=200, limit=80):
    """Chamfer-free BFS distance (in 3 px cells, 4-neighbour) from every cell to the nearest drawn ('D') cell, capped at limit."""
    import numpy as np
    d = np.full((rows, cols), limit, dtype=np.int16)
    cur = np.zeros((rows, cols), dtype=bool)
    flat = np.array([c == 'D' for c in drawn_cells[:rows * cols]] + [False] * max(0, rows * cols - len(drawn_cells)), dtype=bool)
    cur = flat.reshape(rows, cols)
    d[cur] = 0
    seen = cur.copy()
    for step in range(1, limit):
        grow = np.zeros_like(cur)
        grow[1:, :] |= cur[:-1, :]
        grow[:-1, :] |= cur[1:, :]
        grow[:, 1:] |= cur[:, :-1]
        grow[:, :-1] |= cur[:, 1:]
        grow &= ~seen
        if not grow.any():
            break
        d[grow] = step
        seen |= grow
        cur = grow
    return d


def contact_gaps(repo, screen, drawn_cells, cm):
    """Per hardness owner on a screen: the pixels of its stamp that touch walkable 1997 ground (4-neighbour code 0), and how far
    each lies from anything drawn (cm, beyond the audit's 40 cm tolerance; 0 = drawn within it). Owner 0 = tile hardness
    (codes 1-3). Uses tools/dinkex/out/hardness/SCR_nnn.png and _owner.png (vision 0)."""
    import numpy as np
    from PIL import Image
    base = os.path.join(repo, 'tools', 'dinkex', 'out', 'hardness', f'SCR_{screen:03d}')
    if not os.path.exists(base + '.png'):
        return {}
    code = np.array(Image.open(base + '.png'), dtype=np.int16)
    owner = np.array(Image.open(base + '_owner.png'), dtype=np.int16) if os.path.exists(base + '_owner.png') else np.zeros_like(code)
    free = code == 0
    nb = np.zeros_like(free)
    nb[1:, :] |= free[:-1, :]
    nb[:-1, :] |= free[1:, :]
    nb[:, 1:] |= free[:, :-1]
    nb[:, :-1] |= free[:, 1:]
    contact = (~free) & nb & (code != 200)
    dist = cell_distance(drawn_cells)
    ys, xs = np.nonzero(contact)
    gaps = dist[np.minimum(ys // 3, 133), np.minimum(xs // 3, 199)].astype(float) * 3 * cm
    out = {}
    for y, x, g in zip(ys, xs, gaps):
        k = int(owner[y, x]) if code[y, x] >= 100 else 0
        out.setdefault(k, []).append((int(x), int(y), g, int(code[y, x])))
    return out


_HARD = {}


def hard_png(screen, repo=None):
    """1997 hardness codes of a screen (tools/dinkex/out/hardness/SCR_nnn.png, vision 0), or None."""
    if screen not in _HARD:
        from PIL import Image
        path = os.path.join(repo or _REPO[0], 'tools', 'dinkex', 'out', 'hardness', f'SCR_{screen:03d}.png')
        _HARD[screen] = Image.open(path).load() if os.path.exists(path) else None
    return _HARD[screen]


_REPO = [REPO]
_REACH = {}


def reach97(screen, classes=None):
    """5 px cells (120 x 80) of the largest 4-connected walkable region of the 1997 hardness (code 0, not on a void, water or
    cliff tile: interiors are islands in void that is hardness 0 too): where Dink can be."""
    if screen not in _REACH:
        h = hard_png(screen)
        if h is None:
            _REACH[screen] = None
            return None
        free = [[h[x * 5 + 2, y * 5 + 2] == 0 and not (classes and classes[min(7, y // 10) * 12 + min(11, x // 10)] in BLOCKED_TERRAIN)
                 for x in range(120)] for y in range(80)]
        label = [[0] * 120 for _ in range(80)]
        sizes = {}
        n = 0
        for y0 in range(80):
            for x0 in range(120):
                if not free[y0][x0] or label[y0][x0]:
                    continue
                n += 1
                stack = [(x0, y0)]
                label[y0][x0] = n
                c = 0
                while stack:
                    x, y = stack.pop()
                    c += 1
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < 120 and 0 <= ny < 80 and free[ny][nx] and not label[ny][nx]:
                            label[ny][nx] = n
                            stack.append((nx, ny))
                sizes[n] = c
        big = max(sizes, key=sizes.get) if sizes else 0
        _REACH[screen] = [[label[y][x] == big for x in range(120)] for y in range(80)]
    return _REACH[screen]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('audit')
    ap.add_argument('--walk-mask')
    ap.add_argument('--out')
    ap.add_argument('--repo', default=REPO, help='checkout whose tools/dinkex/out (generated, untracked) holds the 1997 screens')
    a = ap.parse_args(argv)
    _REPO[0] = a.repo
    _HARD.clear()
    rows = read_csv(os.path.join(a.audit, 'phys_origins.csv'))
    warps = read_csv(os.path.join(a.audit, 'phys_warps.csv'))
    tiles = read_csv(os.path.join(a.audit, 'phys_tiles.csv'))
    screens = read_csv(os.path.join(a.audit, 'phys_screens.csv'))
    drawn = {int(r['screen']): rle_decode(r['mask']) for r in read_csv(os.path.join(a.audit, 'phys_drawn_mask.csv'))}
    out = a.out or a.audit
    os.makedirs(out, exist_ok=True)
    # screens the audit cannot judge: nothing drawn at all, or the whole map hard (the teleport did not land, or a script
    # filled the screen): listed, left out of the rankings
    unreliable = {int(r['screen']) for r in screens if int(num(r, 'drawn_items')) == 0 or int(num(r, 'solid_tile_px')) >= 200000
                  or r.get('player_on_screen', '1') == '0'}
    lines = []
    P = lines.append
    P(f'# Physical mapping audit: {len(screens)} screens, {len(rows)} placement/sprite rows, {len(warps)} warps, {len(tiles)} bare tile blobs')
    P('')
    mism = []  # (category, severity cm, screen, subject, detail)

    def has_box(r):
        return num(r, 'box_r') >= num(r, 'box_l') and num(r, 'box_b') >= num(r, 'box_t') and not (num(r, 'box_r') == -21 and num(r, 'box_l') == -20)

    def box(r):
        return (num(r, 'box_l'), num(r, 'box_t'), num(r, 'box_r'), num(r, 'box_b'))

    def own_box(r):
        if int(num(r, 'body_px')):
            return (num(r, 'body_l'), num(r, 'body_t'), num(r, 'body_r'), num(r, 'body_b'))
        return (num(r, 'own_l'), num(r, 'own_t'), num(r, 'own_r'), num(r, 'own_b'))

    def drawn_kind(r):
        k = set((r.get('kinds') or '').split('+')) - {''}
        if not k and not int(num(r, 'body_px')):
            return 'none'
        if k == {'card'}:
            return 'card'
        if 'skeletal' in k:
            return 'body'
        return 'mesh'

    # ---- 1 invisible walls ----
    tile_classes, neighbours = load_tiles(a.repo)
    if not tile_classes:
        print(f'note: no tools/dinkex/out/screens under {a.repo}: terrain checks skipped (pass --repo)', file=sys.stderr)

    def terrain_share(r):
        """Share of the hardbox rectangle drawn as a barrier by the terrain (water, cliff, wall tiles) or by anything drawn
        (phys_drawn_mask, 3 px cells): a hardbox there is not invisible even when no mesh of its own stands on it."""
        s = int(r['screen'])
        l, t, rr, b = (int(num(r, k)) for k in ('box_l', 'box_t', 'box_r', 'box_b'))
        dm, tc = drawn.get(s), tile_classes.get(s)
        n = barrier = seen = 0
        for y in range(max(0, t) // 3 * 3, min(399, b) + 1, 3):
            for x in range(max(0, l) // 3 * 3, min(599, rr) + 1, 3):
                n += 1
                cls = tc[min(7, y // 50) * 12 + min(11, x // 50)] if tc else '?'
                i = (y // 3) * 200 + x // 3
                d = bool(dm and i < len(dm) and dm[i] == 'D')
                barrier += cls in BLOCKED_TERRAIN
                seen += d or cls in BLOCKED_TERRAIN
        return (barrier / n, seen / n) if n else (0.0, 0.0)

    # Invisible walls are measured where Dink meets them: the stamp's pixels that touch walkable 1997 ground (contact), and how
    # far each lies from anything drawn. The inside of a thick hardbox is never reached and does not count.
    cm_of = {int(r['screen']): num(r, 'cm_per_px') for r in screens}
    contacts = {}
    for scr in sorted(drawn):
        contacts[scr] = contact_gaps(a.repo, scr, drawn[scr], cm_of.get(scr, 6.875))

    def gap_stats(lst):
        g = sorted(x[2] for x in lst)
        bare = sum(1 for x in g if x > 0)
        return len(g), (bare / len(g) if g else 0.0), (g[min(len(g) - 1, int(0.9 * len(g)))] if g else 0.0)

    c1 = Counter()
    for r in rows:
        if int(num(r, 'stamped_px')) <= 0:
            continue
        scr = int(r['screen'])
        try:
            n_idx = int(r['origin'].split('_P')[1]) if r['origin'].startswith(f'S{scr:03d}_P') else -1
        except (IndexError, ValueError):
            n_idx = -1
        lst = contacts.get(scr, {}).get(n_idx, [])
        c1['checked'] += 1
        n, frac, p90 = gap_stats(lst)
        if n < 10 or frac < 0.3 or p90 < TOL_CM:
            c1['ok'] += 1
            continue
        barrier, seen = terrain_share(r)
        if barrier >= 0.6:
            c1['ok: on water/cliff/wall terrain tiles'] += 1
            c1['ok'] += 1
            continue
        dk = drawn_kind(r)
        hard_only = r['type'] == '2'
        why = {'none': 'nothing of its own drawn (screen-dressed or missing)', 'card': 'only its card is drawn'}.get(dk, 'its mesh does not reach the hardbox edge')
        if hard_only:
            why = 'hardness-only placement (invisible in 1997 too)'
        c1['mismatched'] += 1
        c1['why: ' + why] += 1
        mism.append(('1 invisible wall (hardbox)', p90 * frac * math.sqrt(n) / (3.0 if hard_only else 1.0), scr, r['origin'],
                     f"Dink stops up to {p90 + TOL_CM:.0f} cm (p90) from anything drawn on {frac:.0%} of its {n} px contact edge; {why}; "
                     f"class {r['class']}, type {r['type']}, seq {r['seq']}.{r['frame']}, mesh {r['mesh'] or '-'}, kinds {r['kinds'] or '-'}"))
    ct = Counter()
    for scr, owners in contacts.items():
        tc = tile_classes.get(scr)
        by_tile = defaultdict(list)
        for x, y, g, code in owners.get(0, []):
            by_tile[(min(11, x // 50), min(7, y // 50))].append((x, y, g, code))
        for (tx, ty), lst in by_tile.items():
            ct['tiles checked'] += 1
            cls = tc[ty * 12 + tx] if tc else '?'
            n, frac, p90 = gap_stats(lst)
            if n < 10 or frac < 0.5 or p90 < TOL_CM:
                ct['ok'] += 1
                continue
            if cls in BLOCKED_TERRAIN or cls in ('forest_canopy',):
                ct[f'ok: drawn by the terrain as {cls}'] += 1
                ct['ok'] += 1
                continue
            # a shore or cliff-top tile: the drawn barrier (water sheet, cliff) is on the next tile, which the mesh audit does
            # not see (water is a flat sheet, cliffs are terrain relief)
            near = {tc[ny * 12 + nx] for nx in range(max(0, tx - 1), min(12, tx + 2)) for ny in range(max(0, ty - 1), min(8, ty + 2))} if tc else set()
            edge = near & (BLOCKED_TERRAIN | {'forest_canopy'})
            if edge:
                ct[f"ok: next to {'/'.join(sorted(edge))} (shore, cliff or wall edge)"] += 1
                ct['ok'] += 1
                continue
            low = sum(1 for x in lst if x[3] == 2) > n / 2
            ct['mismatched'] += 1
            ct[f"why: {'low (2)' if low else 'solid'} tile hardness on open {cls}"] += 1
            mism.append((f"1 invisible wall (tile {'low' if low else 'solid'})", p90 * frac * math.sqrt(n) * 0.6, scr, f'tile {tx},{ty}',
                         f"{cls} tile: Dink stops up to {p90 + TOL_CM:.0f} cm (p90) from anything drawn on {frac:.0%} of {n} px of contact edge"))
    P('## 1 Invisible walls (contact edges: stamp pixels next to walkable 1997 ground)')
    P(f"Sprite hardboxes: checked {c1['checked']}, OK {c1['ok']}, mismatched {c1['mismatched']}")
    for k, v in sorted(c1.items()):
        if k.startswith('why') or k.startswith('ok:'):
            P(f'  - {k[5:] if k.startswith("why") else k}: {v}')
    P(f"Tile hardness, per 50 px tile with contact edges: checked {ct['tiles checked']}, OK {ct['ok']}, mismatched {ct['mismatched']}")
    for k, v in sorted(ct.items()):
        if k.startswith('why') or k.startswith('ok:'):
            P(f'  - {k[5:] if k.startswith("why") else k}: {v}')
    P(f'(bare tile blobs from phys_tiles.csv, >= 30 px with nothing drawn within {TOL_CM:.0f} cm: {len(tiles)})')
    P('')

    # ---- 2 hardbox vs mesh (blocking props) ----
    c2 = Counter()
    offs, scales = [], []
    by_mesh = defaultdict(list)
    for r in rows:
        if r['class'] not in ('background', 'sprite_prop', 'scripted_prop') or not has_box(r) or int(num(r, 'stamped_px')) <= 0:
            continue
        dk = drawn_kind(r)
        c2['checked'] += 1
        c2['drawn: ' + dk] += 1
        if dk != 'mesh':
            continue
        cm = num(r, 'cm_per_px')
        l, t, rr, b = box(r)
        bw, bh = (rr - l + 1), (b - t + 1)
        off = math.hypot(num(r, 'offset_x'), num(r, 'offset_y')) * cm
        scale = math.sqrt(max(1.0, num(r, 'own_px')) / max(1.0, bw * bh))
        offs.append(off)
        scales.append(scale)
        cover, over = num(r, 'cover_own'), num(r, 'overhang_own')
        lim = max(TOL_CM, 0.3 * max(bw, bh) * cm)
        ok = cover >= 0.7 and off <= lim and over <= 0.5
        by_mesh[r['mesh']].append((ok, off, cover, over, scale))
        if ok:
            c2['ok'] += 1
            continue
        c2['mismatched'] += 1
        why = []
        if off > lim:
            why.append(f'offset {off:.0f} cm ({num(r, "offset_x") * cm:+.0f},{num(r, "offset_y") * cm:+.0f})')
        if cover < 0.7:
            why.append(f'hardbox covered {cover:.0%}')
        if over > 0.5:
            why.append(f'mesh {over:.0%} outside the hardbox (scale {scale:.2f})')
        sev = max(off - lim, 0) + (1 - cover) * max(bw, bh) * cm + max(0, over - 0.5) * max(bw, bh) * cm
        mism.append(('2 hardbox vs mesh', sev, int(r['screen']), r['origin'], f"{r['mesh']}: {'; '.join(why)}; box {bw:.0f}x{bh:.0f} px at {cm:.1f} cm/px, kinds {r['kinds']}"))
    P('## 2 Sprite hardboxes vs meshes (placements that block)')
    P(f"checked {c2['checked']} (drawn by a mesh {c2['drawn: mesh']}, card only {c2['drawn: card']}, body {c2['drawn: body']}, nothing {c2['drawn: none']}); of the meshes OK {c2['ok']}, mismatched {c2['mismatched']}")
    if offs:
        so, ss = sorted(offs), sorted(scales)
        q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))]
        P(f'centre offset (cm): median {q(so, .5):.0f}, p90 {q(so, .9):.0f}, p99 {q(so, .99):.0f}, max {so[-1]:.0f}')
        P(f'footprint/hardbox linear scale: p10 {q(ss, .1):.2f}, median {q(ss, .5):.2f}, p90 {q(ss, .9):.2f}')
    P('Meshes with the most mismatched placements (mesh: mismatched/placements, median offset cm, median cover):')
    worst = sorted(by_mesh.items(), key=lambda kv: -sum(1 for x in kv[1] if not x[0]))[:15]
    for m, v in worst:
        bad = sum(1 for x in v if not x[0])
        if bad:
            P(f'  - {m}: {bad}/{len(v)}, offset {sorted(x[1] for x in v)[len(v) // 2]:.0f}, cover {sorted(x[2] for x in v)[len(v) // 2]:.2f}')
    P('')

    # ---- 3 creatures and NPCs ----
    c3 = Counter()
    by_seq = defaultdict(list)
    for r in rows:
        if r['class'] not in ('creature', 'npc') or not int(num(r, 'live')):
            continue
        c3['checked'] += 1
        if int(num(r, 'authored')):
            c3['3D hit (authored body, AuthoredGeometryMatches)'] += 1
            continue
        dk = drawn_kind(r)
        if dk in ('none',) or not has_box(r):
            c3['no body or no hardbox'] += 1
            continue
        if dk == 'card':
            c3['card only (picture)'] += 1
            continue
        cm = num(r, 'cm_per_px')
        g = attack_gaps(box(r), own_box(r), cm)
        far = max(v[0] for v in g.values())
        miss = max(v[1] for v in g.values())
        bl, bt, br, bb = own_box(r)
        l, t, rr, b = box(r)
        coff = math.hypot((bl + br) / 2 - (l + rr) / 2, (bt + bb) / 2 - (t + b) / 2) * cm
        name = (r['mesh'] or r['script'] or f"seq {r['seq']}")
        by_seq[name].append((far, miss, coff))
        if far <= TOL_CM and miss <= TOL_CM and coff <= max(TOL_CM, 0.5 * max(rr - l, b - t) * cm):
            c3['ok'] += 1
        else:
            c3['mismatched'] += 1
            mism.append(('3 creature hit box vs body', max(far, miss, coff), int(r['screen']), r['origin'],
                         f"{name} (brain {r['brain']}, script {r['script'] or '-'}): hit registers {far:.0f} cm short of the body, "
                         f"visible sword contact missed by up to {miss:.0f} cm, body centre {coff:.0f} cm from the hardbox centre; "
                         + ' '.join(f"{s}:{v[0]:.0f}/{v[1]:.0f}" for s, v in g.items())))
    P('## 3 Creatures and NPCs: 1997 hit box vs the drawn body (Dink with a sword: sp_range 40)')
    P(f"live creature/NPC sprites checked {c3['checked']}: OK {c3['ok']}, mismatched {c3['mismatched']}, "
      f"3D hit (authored) {c3['3D hit (authored body, AuthoredGeometryMatches)']}, card only {c3['card only (picture)']}, no body/box {c3['no body or no hardbox']}")
    P('By body (sprites, median far-hit cm, median missed-contact cm, median centre offset cm):')
    for name, v in sorted(by_seq.items(), key=lambda kv: -len(kv[1]))[:25]:
        f = sorted(x[0] for x in v)[len(v) // 2]
        m = sorted(x[1] for x in v)[len(v) // 2]
        o = sorted(x[2] for x in v)[len(v) // 2]
        P(f'  - {name}: {len(v)}, far {f:.0f}, miss {m:.0f}, offset {o:.0f}')
    P('')

    # ---- 4 pickups, warps ----
    c4 = Counter()
    for r in rows:
        if r['class'] != 'pickup' or not int(num(r, 'live')):
            continue
        c4['checked'] += 1
        if int(num(r, 'authored')):
            c4['3D touch (authored)'] += 1
            continue
        dk = drawn_kind(r)
        if dk == 'none' or not has_box(r):
            c4['no mesh or no box'] += 1
            continue
        if dk == 'card':
            c4['card only'] += 1
            continue
        far, miss = touch_gaps(box(r), own_box(r), num(r, 'cm_per_px'))
        if far <= TOL_CM and miss <= TOL_CM:
            c4['ok'] += 1
        else:
            c4['mismatched'] += 1
            mism.append(('4 pickup touch box', max(far, miss), int(r['screen']), r['origin'],
                         f"{r['mesh']} ({r['script']}): picked up {far:.0f} cm from the mesh, stands {miss:.0f} cm over it without the touch"))
    cw = Counter()
    for w in warps:
        if not int(num(w, 'enabled')):
            continue
        cw['checked'] += 1
        cm = num(w, 'cm_per_px')
        gap = num(w, 'gap_px', -1)
        if int(num(w, 'own_px')) <= 0:
            cw['no own mesh (screen-dressed or card)'] += 1
            if num(w, 'box_cover') < 0.3:
                cw['mismatched'] += 1
                mism.append(('4 warp trigger', num(w, 'drawn_near_px') * cm, int(w['screen']), w['warp'],
                             f"{w['kind']} trigger with nothing drawn on {1 - num(w, 'box_cover'):.0%} of it (nearest drawn {num(w, 'drawn_near_px') * cm:.0f} cm)"))
            else:
                cw['ok'] += 1
            continue
        if gap * cm > TOL_CM:
            cw['mismatched'] += 1
            mism.append(('4 warp trigger', gap * cm, int(w['screen']), w['warp'], f"{w['kind']} trigger {gap * cm:.0f} cm from its drawn door"))
        else:
            cw['ok'] += 1
    P('## 4 Pickups (touch box) and warps (trigger vs door)')
    P(f"pickups checked {c4['checked']}: OK {c4['ok']}, mismatched {c4['mismatched']}, 3D touch (authored) {c4['3D touch (authored)']}, card only {c4['card only']}, no mesh/box {c4['no mesh or no box']}")
    P(f"warps (enabled triggers) checked {cw['checked']}: OK {cw['ok']}, mismatched {cw['mismatched']} (no own mesh {cw['no own mesh (screen-dressed or card)']})")
    P('')

    # ---- 6 terrain: walk mask vs drawn terrain ----
    if a.walk_mask:
        c6 = Counter()
        masks = {}
        with open(a.walk_mask, encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 3 and parts[0].isdigit():  # walk_mask.csv with or without its header
                    masks[int(parts[0])] = (int(parts[1]), rle_decode(parts[2]))
        for s, (step, m) in sorted(masks.items()):
            if s not in tile_classes:
                continue
            cols = (600 + step - 1) // step
            dm = drawn.get(s)
            for ti, cls in enumerate(tile_classes[s]):
                tx, ty = ti % 12, ti // 12
                free = tot = drawn_n = 0
                for yy in range(ty * 50 // step, min((ty * 50 + 50) // step, len(m) // cols)):
                    for xx in range(tx * 50 // step, (tx * 50 + 50) // step):
                        i = yy * cols + xx
                        if i < len(m):
                            tot += 1
                            free += m[i] == 'F'
                            if dm and i < len(dm):
                                drawn_n += dm[i] == 'D'
                if not tot:
                    continue
                ff = free / tot
                h97 = hard_png(s)
                rr = reach97(s, tile_classes.get(s))
                f97 = (sum(1 for y in range(ty * 10, ty * 10 + 10) for x in range(tx * 10, tx * 10 + 10) if rr[y][x]) / 100.0) if rr else 1.0
                c6['tiles'] += 1
                if cls in ('water', 'lava', 'chasm') and ff > 0.3:
                    f97 = (sum(1 for y in range(ty * 50 + 2, ty * 50 + 50, 5) for x in range(tx * 50 + 2, tx * 50 + 50, 5) if h97[x, y] == 0) / 100.0) if h97 else 1.0
                    if ff <= f97 + 0.1:
                        c6[f'{cls} drawn, walkable no more than the 1997 hardness 0 allows (as 1997)'] += 1
                        mism.append(('6 terrain (as 1997)', ff * 5, s, f'tile {tx},{ty}', f'{cls} tile, {ff:.0%} walkable for the capsule; 1997 hardness 0 on {f97:.0%} of it'))
                    else:
                        c6[f'{cls} drawn, walkable where 1997 blocks'] += 1
                        mism.append(('6 terrain', ff * 25, s, f'tile {tx},{ty}', f'{cls} tile, {ff:.0%} walkable for the capsule; 1997 free on only {f97:.0%}'))
                elif cls in OPEN_TERRAIN and ff < 0.4 and drawn_n / tot < 0.3:
                    if f97 >= 0.9:
                        c6[f'open {cls} drawn, walkable in 1997 (largest region), blocked in the remaster with nothing drawn'] += 1
                        mism.append(('6 terrain', (1 - ff) * 25, s, f'tile {tx},{ty}', f'{cls} tile, 1997 walkable (largest region) on {f97:.0%}, only {ff:.0%} walkable for the capsule and {drawn_n / tot:.0%} drawn on'))
                    else:
                        c6[f'open {cls} drawn, blocked or out of reach in 1997'] += 1
        P('## 6 Terrain tiles: drawn class vs where the capsule can stand')
        P(f"tiles checked {c6['tiles']}")
        for k, v in sorted(c6.items()):
            if k != 'tiles':
                P(f'  - {k}: {v}')
        # screen edges: where the 1997 hardness lets Dink cross (both sides free at the edge pixels), the capsule must be able to
        # stand within the last 12 px on both sides (walk mask); and the other way round
        hard_cache = {}

        def hard1997(scr):
            if scr not in hard_cache:
                path = os.path.join(a.repo, 'tools', 'dinkex', 'out', 'hardness', f'SCR_{scr:03d}.png')
                hard_cache[scr] = None
                if os.path.exists(path):
                    from PIL import Image
                    hard_cache[scr] = Image.open(path).load()
            return hard_cache[scr]
        ce = Counter()
        for s, (step, m) in masks.items():
            cols = (600 + step - 1) // step
            rowsn = len(m) // cols
            nb = neighbours.get(s, {})
            for side, other in (('right', nb.get('right')), ('down', nb.get('down'))):
                if not other or other not in masks:
                    continue
                om = masks[other][1]
                ha, hb = hard1997(s), hard1997(other)
                ta, tb = tile_classes.get(s), tile_classes.get(other)
                if ha is None or hb is None or not ta or not tb:
                    continue
                k = 12 // step + 1
                if side == 'right':
                    cells = range(rowsn)
                    fa = lambda i: any(m[i * cols + c] == 'F' for c in range(cols - k, cols))
                    fb = lambda i: any(om[i * cols + c] == 'F' for c in range(k))
                    ga = lambda i: all(ha[x, min(399, i * step + 1)] == 0 for x in range(580, 600)) and ta[min(7, (i * step) // 50) * 12 + 11] in OPEN_TERRAIN
                    gb = lambda i: all(hb[x, min(399, i * step + 1)] == 0 for x in range(0, 20)) and tb[min(7, (i * step) // 50) * 12] in OPEN_TERRAIN
                else:
                    cells = range(cols)
                    fa = lambda i: any(m[r * cols + i] == 'F' for r in range(rowsn - k, rowsn))
                    fb = lambda i: any(om[r * cols + i] == 'F' for r in range(k))
                    ga = lambda i: all(ha[min(599, i * step + 1), y] == 0 for y in range(380, 400)) and ta[84 + min(11, (i * step) // 50)] in OPEN_TERRAIN
                    gb = lambda i: all(hb[min(599, i * step + 1), y] == 0 for y in range(0, 20)) and tb[min(11, (i * step) // 50)] in OPEN_TERRAIN
                lost = sum(1 for i in cells if ga(i) and gb(i) and not (fa(i) and fb(i)))
                both = sum(1 for i in cells if ga(i) and gb(i))
                ce['edges'] += 1
                ce['crossable in 1997'] += both > 0
                if lost >= 4:
                    ce['mismatched: 1997 crossing blocked'] += 1
                    mism.append(('4 screen-edge exit', lost * step * 6.9, s, f'{side} edge to SCR_{other:03d}',
                                 f'{lost} of {both} edge cells (3 px) where 1997 crosses are blocked for the capsule on one side'))
        P(f"screen edges checked {ce['edges']} ({ce['crossable in 1997']} crossable in 1997): 1997 crossing blocked {ce['mismatched: 1997 crossing blocked']} (cells: 20 px of 1997 hardness 0 and open terrain on both sides; capsule free within 12 px of the edge on both sides)")
        P('')

    # ---- 7 standing inside geometry ----
    c7 = Counter()
    for r in rows:
        if r['class'] not in ('creature', 'npc', 'pickup', 'scripted_prop') or not int(num(r, 'live')):
            continue
        c7['checked'] += 1
        inside = r.get('inside_other') or ''
        if inside:
            c7['mismatched'] += 1
            mism.append(('7 standing inside', 30.0 + 10 * inside.count('|'), int(r['screen']), r['origin'],
                         f"{r['class']} {r['mesh'] or r['script']} at ({r['sprite_x']},{r['sprite_y']}) inside the drawn body of {inside}"
                         + ('' if r['capsule_blocked'] != '1' else '; a capsule cannot stand there')))
        else:
            c7['ok'] += 1
    P('## 7 Live sprites standing inside another drawn body')
    P(f"checked {c7['checked']}: OK {c7['ok']}, inside {c7['mismatched']}")
    P('')

    if unreliable:
        P(f"## Not judged: {len(unreliable)} screens with nothing drawn, the whole map hard or the player not on the screen: {', '.join(f'SCR_{x:03d}' for x in sorted(unreliable))}")
        P('')
    mism = [m for m in mism if m[2] not in unreliable]
    mism.sort(key=lambda m: -m[1])
    P('## Worst per category (top 8 each)')
    for cat in sorted({m[0] for m in mism}):
        P(f'### {cat} ({sum(1 for m in mism if m[0] == cat)})')
        for c, sev, s, subj, det in [m for m in mism if m[0] == cat][:8]:
            P(f'- SCR_{s:03d} {subj}: {det}')
    P('')
    P('## Worst 40 mismatches (all categories)')
    for c, sev, s, subj, det in mism[:40]:
        P(f'- [{c}] SCR_{s:03d} {subj}: {det}')
    with open(os.path.join(out, 'phys_summary.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    with open(os.path.join(out, 'phys_mismatches.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['category', 'severity', 'screen', 'subject', 'detail'])
        for m in mism:
            w.writerow([m[0], f'{m[1]:.1f}', m[2], m[3], m[4]])
    # the first 100 of each category: small enough to keep with the evidence
    with open(os.path.join(out, 'phys_mismatches_top.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['category', 'severity', 'screen', 'subject', 'detail'])
        for cat in sorted({m[0] for m in mism}):
            for m in [m for m in mism if m[0] == cat][:100]:
                w.writerow([m[0], f'{m[1]:.1f}', m[2], m[3], m[4]])
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
