#!/usr/bin/env python3
"""World-scale audit of what Dink's capsule meets (26 Nov 2026, ws-followup-1; doc/remaster/WORLD_SCALE.md 14.1). Headless, offline.

    python3 -I Scripts/check_capsule_gaps.py --collision <bundle>/collision.json --layout-ref <analyse off>/world_layout.json \
        --layout-new <analyse on>/world_layout.json [--phys <dink.PhysAudit dir>] [--out <report dir>]

(a) CAPSULE GAPS. The importer builds every screen's collision from the 1997 hardness (collision.json: solid, low, sprite and warp
rects plus the water and void fills); Dink's capsule (28 cm) covers fewer map pixels when the layout grows, so 1997 walkable ground
too narrow for it at the reference scale can fit it at the enlarged one. For both layouts (each screen's own local metres per pixel,
x and y apart: the layout is a rubber sheet) the check marks where the capsule centre may stand (no collision pixel within 28 cm),
joins screens across shared edges, and compares:
  - POCKET: an enlarged-scale capsule region that holds no reference-scale capsule cell (Dink could not stand anywhere in it before).
    "closed" when its 1997 walkable component (point Dink, as the 1997 engine moves him) holds no reference capsule cell either: no walk
    of the 1997 map reaches it, only a teleport or a scripted set-down; such a pocket is sealed for the capsule in play
    (Content/Dink/Data/Play/sealed_gaps.json). An "open" pocket is 1997 ground behind a gap the capsule never passes.
  - JOIN: a slit of new capsule ground that joins two reference-scale capsule regions: a way the reference world closed to the capsule.
    The 1997 engine moves Dink as a point, so every such way is a 1997 way (point Dink walked it); listed for review, not sealed.
(b) INVISIBLE WALLS FOR THE PLAYER (with --phys): for every placement box Dink still meets in play with the physical play layer on
(a box the layer does not relax, the drawn strip of a trimmed wall run on to its box's ends plus its joints; relaxed boxes are left to
their drawn mesh's player-only blocker), the contact edge (box pixels next to 1997 walkable ground) is measured against the drawn
mask of the same dink.PhysAudit run (phys_drawn_mask.csv): a box whose contact edge reaches more than --limit-cm from anything drawn
is listed, by why the layer keeps it.

Exit status 1 when (a) finds a closed pocket that sealed_gaps.json does not seal (the one fix this check asks for); everything else is
a report (capsule_gaps.md / capsule_gaps.csv / invisible_walls.csv in --out)."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
W, H = 600, 400
CAPSULE_CM = 28.0
MIN_REGION_PX = 400     # a reference capsule region smaller than this is a nook, not a region a join matters for
MIN_POCKET_PX = 4       # enlarged capsule pocket at least this many centre pixels
# scripts of sprites that may close a sealed pocket: checked by hand (thorn: sp_hitpoints 0, no hit or die procedure: it never goes)
REVIEWED_EDGE_SCRIPTS = {'thorn'}


def label_components(mask: np.ndarray):
    """4-connected labelling via row runs + union-find (as export_import_bundle.label_components). (labels int32, count)."""
    h, w = mask.shape
    padded = np.zeros((h, w + 2), dtype=np.int8)
    padded[:, 1:-1] = mask
    d = np.diff(padded, axis=1)
    parent: list[int] = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    rows, prev = [], []
    for y in range(h):
        starts = np.flatnonzero(d[y] == 1).tolist()
        ends = np.flatnonzero(d[y] == -1).tolist()
        cur, j = [], 0
        for s, e in zip(starts, ends):
            rid = len(parent)
            parent.append(rid)
            while j < len(prev) and prev[j][1] <= s:
                j += 1
            k = j
            while k < len(prev) and prev[k][0] < e:
                ra, rb = find(rid), find(prev[k][2])
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
                k += 1
            cur.append((s, e, rid))
        rows.append(cur)
        prev = cur
    labels = np.zeros((h, w), dtype=np.int32)
    remap: dict[int, int] = {}
    for y, cur in enumerate(rows):
        for s, e, rid in cur:
            labels[y, s:e] = remap.setdefault(find(rid), len(remap) + 1)
    return labels, len(remap)


class UnionFind:
    def __init__(self):
        self.p: dict = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def load_layout(path):
    """screen -> (sheet, 2x2 local metres per pixel at the screen's centre: columns d/dx, d/dy)."""
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    out = {}
    for s in d['screens']:
        c = {k: np.array(v, dtype=float) for k, v in s['corners'].items()}
        dx = ((c['ne'] - c['nw']) + (c['se'] - c['sw'])) / 2.0 / W
        dy = ((c['sw'] - c['nw']) + (c['se'] - c['ne'])) / 2.0 / H
        out[int(s['screen'])] = (s.get('sheet', ''), np.array([[dx[0], dy[0]], [dx[1], dy[1]]]))
    return out


LOW_SCREENS: set = set()


def blocked_masks(collision_path):
    """screen -> bool[400, 600]: every collision rect of the export (exclusive right/bottom). Fills LOW_SCREENS with the screens that
    have a low collision mesh (low or water-fill rects): a seal joins that mesh, so a screen without one cannot take a seal."""
    coll = json.loads(Path(collision_path).read_text(encoding='utf-8'))['screens']
    out = {}
    LOW_SCREENS.clear()
    for sid, classes in coll.items():
        if classes.get('low') or classes.get('fill_water'):
            LOW_SCREENS.add(int(sid[4:]))
        m = np.zeros((H, W), dtype=bool)
        for rects in classes.values():
            for l, t, r, b in rects:
                m[max(0, t):min(H, b), max(0, l):min(W, r)] = True
        out[int(sid[4:])] = m
    return out


def disc_offsets(J, radius_m):
    """Integer offsets (dx, dy) of collision pixels that touch a capsule of radius_m whose centre is at a pixel centre: the nearest point
    of the pixel's square to the centre, mapped through the local Jacobian J (metres per pixel), lies within the radius."""
    inv = np.linalg.inv(J)
    reach = int(math.ceil(max(abs(inv[0]).sum(), abs(inv[1]).sum()) * radius_m)) + 2
    offs = []
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            nx = 0.0 if abs(dx) <= 0.5 else (dx - 0.5 if dx > 0 else dx + 0.5)
            ny = 0.0 if abs(dy) <= 0.5 else (dy - 0.5 if dy > 0 else dy + 0.5)
            if np.hypot(*(J @ np.array([nx, ny]))) < radius_m:
                offs.append((dx, dy))
    return offs, reach


def neighbours(n):
    """Grid neighbours of screen n (32 columns): west, east, north, south."""
    col = (n - 1) % 32
    return {'w': n - 1 if col > 0 else None, 'e': n + 1 if col < 31 else None, 'n': n - 32 if n > 32 else None, 's': n + 32}


def padded_blocked(n, blocked, layout, pad):
    """The screen's collision with a margin taken from its neighbours on the same sheet; elsewhere the edge is a wall."""
    P = np.ones((H + 2 * pad, W + 2 * pad), dtype=bool)
    P[pad:pad + H, pad:pad + W] = blocked[n]
    sheet = layout[n][0]
    nb = neighbours(n)
    for side, m in nb.items():
        if m is None or m not in blocked or layout.get(m, ('?',))[0] != sheet:
            continue
        o = blocked[m]
        if side == 'w':
            P[pad:pad + H, :pad] = o[:, W - pad:]
        elif side == 'e':
            P[pad:pad + H, pad + W:] = o[:, :pad]
        elif side == 'n':
            P[:pad, pad:pad + W] = o[H - pad:, :]
        else:
            P[pad + H:, pad:pad + W] = o[:pad, :]
    # corners: through the diagonal neighbour when both edges are shared (else a wall)
    for (cy, cx, dn) in ((0, 0, -33), (0, 1, -31), (1, 0, 31), (1, 1, 33)):
        m = n + dn
        if m in blocked and layout.get(m, ('?',))[0] == sheet and abs(((m - 1) % 32) - ((n - 1) % 32)) == 1:
            o = blocked[m]
            ys = slice(0, pad) if cy == 0 else slice(pad + H, None)
            xs = slice(0, pad) if cx == 0 else slice(pad + W, None)
            oy = slice(H - pad, H) if cy == 0 else slice(0, pad)
            ox = slice(W - pad, W) if cx == 0 else slice(0, pad)
            P[ys, xs] = o[oy, ox]
    return P


def capsule_fit(n, blocked, layout, radius_m):
    """bool[400, 600]: pixel centres where the capsule touches no collision pixel."""
    offs, reach = disc_offsets(layout[n][1], radius_m)
    P = padded_blocked(n, blocked, layout, reach)
    hit = np.zeros((H, W), dtype=bool)
    for dx, dy in offs:
        hit |= P[reach + dy:reach + dy + H, reach + dx:reach + dx + W]
    return ~hit


def world_components(masks, layout, any_sheet=False):
    """Labels per screen plus a union-find over (screen, label) across shared edges of screens on the same sheet (the remaster's
    physics), or of any grid neighbours (any_sheet: the 1997 engine walks off every edge onto the next screen of the grid)."""
    labels, uf = {}, UnionFind()
    for n, m in masks.items():
        labels[n], _ = label_components(m)
    for n, lab in labels.items():
        nb = neighbours(n)
        for side in ('e', 's'):
            m = nb[side]
            if m not in labels or (not any_sheet and layout.get(m, ('?',))[0] != layout[n][0]):
                continue
            a = lab[:, W - 1] if side == 'e' else lab[H - 1, :]
            b = labels[m][:, 0] if side == 'e' else labels[m][0, :]
            for i in np.flatnonzero((a > 0) & (b > 0)):
                uf.union((n, int(a[i])), (m, int(b[i])))
    return labels, uf


def load_sealed(path):
    out = {}
    if path and Path(path).exists():
        for s, rows in json.loads(Path(path).read_text(encoding='utf-8')).get('screens', {}).items():
            out[int(s)] = [tuple(r['rect']) for r in rows]
    return out


def authored_screens(art_dir):
    out = set()
    for f in Path(art_dir).glob('*.json'):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict):
            out |= {int(x) for x in d.get('authored_collision_screens') or []}
    return out


def rows_to_rects(mask):
    """Rectangles (l, t, r, b inclusive) covering a bool mask: runs per row, extended down while a run repeats exactly."""
    rects, open_ = [], {}
    for y in range(mask.shape[0]):
        nxt = {}
        xs = np.flatnonzero(np.diff(np.concatenate(([0], mask[y].astype(np.int8), [0]))))
        for s, e in zip(xs[0::2].tolist(), xs[1::2].tolist()):
            k = (s, e)
            if k in open_:
                rects[open_[k]][3] = y
                nxt[k] = open_[k]
            else:
                rects.append([s, y, e - 1, y])
                nxt[k] = len(rects) - 1
        open_ = nxt
    return rects


class PlayData:
    """What the physical play layer opens around a pocket (relaxed boxes, open tiles) and where 1997 warps land."""
    def __init__(self, repo, relaxed_path):
        self.repo = Path(repo)
        rel = json.loads(Path(relaxed_path).read_text(encoding='utf-8')) if relaxed_path and Path(relaxed_path).exists() else {}
        self.relaxed = {int(k): set(v) for k, v in rel.get('screens', {}).items()}
        self.open_tiles = {int(k): set(v) for k, v in rel.get('open_tiles', {}).items()}
        self.landings, self.scripts, self.visions = {}, {}, set()
        sdir = self.repo / 'tools' / 'dinkex' / 'out' / 'screens'
        for fn in sorted(sdir.glob('SCR_*.json')) if sdir.exists() else []:
            scr = json.loads(fn.read_text(encoding='utf-8'))
            if (scr.get('hardness') or {}).get('vision_variants'):
                self.visions.add(int(scr['screen']))
            for p in scr.get('placements') or []:
                if p.get('script'):
                    self.scripts[(int(scr['screen']), int(p['id'].split('_P')[1]))] = p['script']
                if p.get('is_warp') and p.get('warp_map'):
                    self.landings.setdefault(int(p['warp_map']), []).append((int(p['warp_x']) - 20, int(p['warp_y']), p['id']))
        fdir = HERE.parent / 'Content' / 'Dink' / 'Data' / 'Gameplay' / 'Hardness' / 'Foundations'
        self.original = {int(fn.stem[4:]) for fn in fdir.glob('SCR_*.json')} if fdir.exists() else set()
        self._img = {}

    def images(self, n):
        if n not in self._img:
            from PIL import Image
            base = self.repo / 'tools' / 'dinkex' / 'out' / 'hardness' / f'SCR_{n:03d}'
            self._img[n] = (np.array(Image.open(str(base) + '.png')), np.array(Image.open(str(base) + '_owner.png'))) if Path(str(base) + '.png').exists() else (None, None)
        return self._img[n]

    def opens_in_play(self, n, comp):
        """The 1997 component's edge holds a relaxed box or an open tile's hardness on screen n: in play the pocket is open ground."""
        code, owner = self.images(n)
        if code is None:
            return False
        ring = np.zeros_like(comp)
        ring[1:, :] |= comp[:-1, :]
        ring[:-1, :] |= comp[1:, :]
        ring[:, 1:] |= comp[:, :-1]
        ring[:, :-1] |= comp[:, 1:]
        ring &= ~comp
        ys, xs = np.nonzero(ring)
        for x, y in zip(xs.tolist(), ys.tolist()):
            c = int(code[y, x])
            if 100 < c < 200 and int(owner[y, x]) in self.relaxed.get(n, set()):
                return True
            if c in (1, 2, 3) and (y // 50) * 12 + x // 50 in self.open_tiles.get(n, set()):
                return True
        return False

    def edge_scripts(self, n, comp):
        """Scripts of the sprites whose boxes close the component on screen n (a script may move or remove its sprite)."""
        code, owner = self.images(n)
        if code is None:
            return set()
        ring = np.zeros_like(comp)
        ring[1:, :] |= comp[:-1, :]
        ring[:-1, :] |= comp[1:, :]
        ring[:, 1:] |= comp[:, :-1]
        ring[:, :-1] |= comp[:, 1:]
        sel = ring & ~comp & (code > 100) & (code < 200)
        return {self.scripts[(n, int(o))] for o in np.unique(owner[sel]).tolist() if (n, int(o)) in self.scripts}

    def landing_in(self, n, comp, margin=6):
        for x, y, pid in self.landings.get(n, []):
            if comp[max(0, y - margin):y + margin + 1, max(0, x - margin):x + margin + 1].any():
                return pid
        return None


def audit_gaps(blocked, ref, new, radius_m, skip=frozenset(), sealed=None, play=None):
    """(a): pockets and joins. Returns a list of finding dicts; a closed pocket gets 'seal' (its 1997 component as rects per screen)
    unless the play layer opens its edge or a 1997 warp lands in it."""
    sealed = sealed or {}
    screens = sorted(n for n in blocked if n in ref and n in new and n not in skip)
    fit_r = {n: capsule_fit(n, blocked, ref, radius_m) for n in screens}
    fit_n = {n: capsule_fit(n, blocked, new, radius_m) for n in screens}
    walk = {n: ~blocked[n] for n in screens}
    lab_r, uf_r = world_components(fit_r, ref)
    lab_n, uf_n = world_components(fit_n, new)
    lab_w, uf_w = world_components(walk, new, any_sheet=True)
    # sizes of the reference capsule regions (world-wide)
    size_r: dict = {}
    for n in screens:
        ids, cnt = np.unique(lab_r[n][lab_r[n] > 0], return_counts=True)
        for i, c in zip(ids.tolist(), cnt.tolist()):
            k = uf_r.find((n, i))
            size_r[k] = size_r.get(k, 0) + c
    # 1997 point components that hold a reference capsule cell
    w_has_ref = set()
    for n in screens:
        m = fit_r[n]
        for i in np.unique(lab_w[n][m]).tolist():
            if i:
                w_has_ref.add(uf_w.find((n, i)))
    # per enlarged capsule region: its pixels per screen
    regions: dict = {}
    for n in screens:
        ids = np.unique(lab_n[n][lab_n[n] > 0]).tolist()
        for i in ids:
            regions.setdefault(uf_n.find((n, i)), []).append((n, i))
    findings = []
    for key, parts in regions.items():
        ref_ids, npx, bbox = set(), 0, {}
        for n, i in parts:
            m = lab_n[n] == i
            npx += int(m.sum())
            for j in np.unique(lab_r[n][m]).tolist():
                if j:
                    ref_ids.add(uf_r.find((n, j)))
            ys, xs = np.nonzero(m)
            bbox[n] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        if not ref_ids:
            if npx < MIN_POCKET_PX:
                continue
            wids = set()
            for n, i in parts:
                for j in np.unique(lab_w[n][lab_n[n] == i]).tolist():
                    if j:
                        wids.add(uf_w.find((n, j)))
            closed = not (wids & w_has_ref)
            is_sealed = True
            for n, i in parts:
                cover = np.zeros((H, W), dtype=bool)
                for l, t_, r, b in sealed.get(n, []):
                    cover[max(0, t_):b + 1, max(0, l):r + 1] = True
                is_sealed &= bool(cover[lab_n[n] == i].all())
            f = {'kind': 'pocket', 'closed': closed, 'sealed': is_sealed, 'px': npx, 'screens': bbox, 'note': ''}
            if closed:
                # the whole 1997 component (point Dink's walkable pixels), on every screen it spans
                comp = {}
                for m in screens:
                    sel = [j for j in np.unique(lab_w[m]).tolist() if j and uf_w.find((m, j)) in wids]
                    if sel:
                        comp[m] = np.isin(lab_w[m], sel)
                if play is not None:
                    opened = [m for m, c in comp.items() if play.opens_in_play(m, c)]
                    landed = [play.landing_in(m, c) for m, c in comp.items()]
                    landed = [p for p in landed if p]
                    scripts = set().union(*(play.edge_scripts(m, c) for m, c in comp.items())) - REVIEWED_EDGE_SCRIPTS
                    special = [m for m in comp if m in play.original or m in play.visions]
                    nolow = [m for m in comp if m not in LOW_SCREENS]
                    if opened:
                        f['note'] = 'opens in play (relaxed box or open tile on its edge: SCR %s)' % ','.join(map(str, opened))
                    elif nolow:
                        f['note'] = 'no low collision mesh to seal it on (SCR %s)' % ','.join(map(str, nolow))
                    elif special:
                        f['note'] = 'screen with scripted hardness or vision variants (SCR %s): review by hand' % ','.join(map(str, special))
                    elif scripts:
                        f['note'] = 'closed by scripted sprites (%s): review by hand' % ','.join(sorted(scripts))
                    elif landed:
                        f['note'] = 'a 1997 warp lands in it (%s)' % ','.join(landed)
                    else:
                        f['seal'] = {m: rows_to_rects(c) for m, c in comp.items()}
            findings.append(f)
            continue
        big = [k for k in ref_ids if size_r.get(k, 0) >= MIN_REGION_PX]
        if len(big) < 2:
            continue
        # the slits: new capsule pixels of this region (not reference capsule ground) next to two or more of its big reference regions
        for n, i in parts:
            m = (lab_n[n] == i) & ~fit_r[n]
            if not m.any():
                continue
            pl, pn = label_components(m)
            for p in range(1, pn + 1):
                pm = pl == p
                ring = np.zeros_like(pm)
                ring[1:, :] |= pm[:-1, :]
                ring[:-1, :] |= pm[1:, :]
                ring[:, 1:] |= pm[:, :-1]
                ring[:, :-1] |= pm[:, 1:]
                touched = {uf_r.find((n, j)) for j in np.unique(lab_r[n][ring & fit_r[n]]).tolist() if j}
                touched = {k for k in touched if size_r.get(k, 0) >= MIN_REGION_PX}
                if len(touched) >= 2:
                    ys, xs = np.nonzero(pm)
                    findings.append({'kind': 'join', 'closed': False, 'sealed': False, 'px': int(pm.sum()),
                                     'screens': {n: (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))},
                                     'joins': sorted(size_r[k] for k in touched)})
    return findings


# ---------------------------------------------------------------- (b) invisible walls for the player in play

def load_mask3(path):
    out = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            p = line.strip().split(',')
            if len(p) != 3 or not p[0].isdigit():
                continue
            cells = []
            for k, c in re.findall(r'(\d+)([A-Z])', p[2]):
                cells.extend([c == 'D'] * int(k))
            n = int(p[0])
            gw = W // int(p[1])
            gh = len(cells) // gw
            out[n] = np.array(cells[:gw * gh], dtype=bool).reshape(gh, gw)
    return out


def farthest_from_drawn(cpts, pts, J):
    """Metres from the farthest of the points cpts (map px) to its nearest drawn 3 px cell centre pts, less half a cell; inf if none."""
    if len(pts) == 0:
        return float('inf'), np.full(len(cpts), np.inf)
    best = np.full(len(cpts), np.inf)
    for i in range(0, len(pts), 2048):
        dpx = cpts[:, None, :] - pts[None, i:i + 2048, :]
        dm = np.hypot(dpx[..., 0] * J[0, 0] + dpx[..., 1] * J[0, 1], dpx[..., 0] * J[1, 0] + dpx[..., 1] * J[1, 1])
        best = np.minimum(best, dm.min(axis=1))
    half = 1.5 * float(np.hypot(*J[:, 0]))
    best = np.maximum(0.0, best - half)
    return float(best.max()), best


def audit_blockers(blockers_csv, drawn, new, limit_m, skip=frozenset()):
    """(b) the player-only blockers themselves (PR #129 hulls, as a blocker-on dink.WalkAudit wrote them: walk_blockers.csv polygon_px):
    a hull is the convex hull of its mesh's body-height slice, so a concave mesh (an L of fence, a ring of rocks) can hold hull pixels
    far from anything drawn."""
    from PIL import Image, ImageDraw
    out = []
    with open(blockers_csv, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            n = int(r['screen'])
            if r.get('enabled') != '1' or n in skip or n not in drawn or n not in new or not r['polygon_px']:
                continue
            poly = [tuple(float(v) for v in p.split(':')) for p in r['polygon_px'].split(';')]
            img = Image.new('1', (W, H), 0)
            ImageDraw.Draw(img).polygon(poly, fill=1)
            m = np.array(img, dtype=bool)
            if not m.any():
                continue
            ys, xs = np.nonzero(drawn[n])
            pts = np.stack([xs * 3 + 1.5, ys * 3 + 1.5], axis=1)
            cy, cx = np.nonzero(m)
            dmax, best = farthest_from_drawn(np.stack([cx + 0.5, cy + 0.5], axis=1), pts, new[n][1])
            if dmax > limit_m:
                out.append({'screen': n, 'origin': r['actor'], 'mesh': r['mesh'].split('.')[-1], 'kinds': 'player blocker', 'script': '',
                            'why': 'player-only blocker hull (PR #129)', 'max_m': round(dmax, 2) if dmax != float('inf') else -1,
                            'far_px': int((best > limit_m).sum()), 'contact_px': int(m.sum()), 'box': [round(min(p[0] for p in poly)), round(min(p[1] for p in poly)),
                                                                                                     round(max(p[0] for p in poly)), round(max(p[1] for p in poly))]})
    return out


def audit_walls(phys, relaxed_path, repo, new, limit_m, skip=frozenset()):
    from PIL import Image
    rows = {}
    with open(Path(phys) / 'phys_origins.csv', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['origin'].startswith('S%03d_P' % int(r['screen'])) and int(r['stamped_px'] or 0) > 0:
                rows.setdefault(int(r['screen']), []).append(r)
    drawn = load_mask3(Path(phys) / 'phys_drawn_mask.csv')
    rel = json.loads(Path(relaxed_path).read_text(encoding='utf-8'))
    relaxed = {int(k): set(v) for k, v in rel.get('screens', {}).items()}
    feet = {int(k): {int(n): v for n, v in d.items()} for k, d in rel.get('feet', {}).items()}
    trimmed = {int(k): {int(n): v for n, v in d.items()} for k, d in rel.get('trimmed', {}).items()}
    joints = {int(k): v for k, v in rel.get('joints', {}).items()}
    kept = {k['origin']: k['reason'] for k in rel.get('kept', [])}
    out = []
    for n in sorted(rows):
        if n in skip or n not in drawn or n not in new:
            continue
        base = Path(repo) / 'tools' / 'dinkex' / 'out' / 'hardness' / f'SCR_{n:03d}'
        if not base.with_suffix('.png').exists():
            continue
        code = np.array(Image.open(str(base) + '.png'))
        owner = np.array(Image.open(str(base) + '_owner.png'))
        free = code == 0
        near_free = np.zeros_like(free)
        near_free[1:, :] |= free[:-1, :]
        near_free[:-1, :] |= free[1:, :]
        near_free[:, 1:] |= free[:, :-1]
        near_free[:, :-1] |= free[:, 1:]
        J = new[n][1]
        d3 = drawn[n]
        ys, xs = np.nonzero(d3)
        pts = np.stack([xs * 3 + 1.5, ys * 3 + 1.5], axis=1) if len(xs) else np.zeros((0, 2))
        for r in rows[n]:
            p = int(r['origin'].split('_P')[1])
            mine = (owner == p) & (code >= 100) & (code < 200)
            why = 'kept: ' + (kept.get(r['origin']) or ('scripted' if r['script'] else 'not a layer candidate (%s)' % (r['kinds'] or 'nothing drawn')))
            if p in relaxed.get(n, set()):
                keep = np.zeros_like(mine)
                if p in trimmed.get(n, {}):
                    l, t, rr, b = feet[n][p]
                    keep[max(0, t):b + 1, max(0, l):rr + 1] = True
                    for jl, jt, jr, jb in joints.get(n, []):
                        keep[max(0, jt):jb + 1, max(0, jl):jr + 1] = True
                    why = 'trimmed wall (drawn strip run on to the box ends)'
                else:
                    continue  # a relaxed box: its drawn mesh's player-only hull stops Dink
                mine &= keep
            contact = mine & near_free
            if not contact.any():
                continue
            cy, cx = np.nonzero(contact)
            dmax, best = farthest_from_drawn(np.stack([cx + 0.5, cy + 0.5], axis=1), pts, J)
            if dmax > limit_m:
                far = int((best > limit_m).sum())
                out.append({'screen': n, 'origin': r['origin'], 'mesh': (r['mesh'] or '').split('.')[-1], 'kinds': r['kinds'], 'script': r['script'],
                            'why': why, 'max_m': round(dmax, 2) if dmax != float('inf') else -1, 'far_px': far, 'contact_px': int(contact.sum()),
                            'box': [r['box_l'], r['box_t'], r['box_r'], r['box_b']]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--collision', required=True, help='the enlarged export\'s collision.json (ImportData/collision.json)')
    ap.add_argument('--layout-ref', required=True, help='world_layout.json of tools/analyse with [world_scale] enlarged = false')
    ap.add_argument('--layout-new', required=True, help='world_layout.json with enlarged = true (the game\'s)')
    ap.add_argument('--capsule-cm', type=float, default=CAPSULE_CM)
    ap.add_argument('--sealed', default=str(HERE.parent / 'Content' / 'Dink' / 'Data' / 'Play' / 'sealed_gaps.json'))
    ap.add_argument('--art', default=str(HERE.parent / 'Content' / 'Dink' / 'Data' / 'Art'), help='manifests naming the authored-collision screens (skipped)')
    ap.add_argument('--phys', default=None, help='(b) a dink.PhysAudit directory of the enlarged world (phys_origins.csv, phys_drawn_mask.csv)')
    ap.add_argument('--relaxed', default=str(HERE.parent / 'Content' / 'Dink' / 'Data' / 'Play' / 'relaxed_hardboxes.json'))
    ap.add_argument('--repo', default=str(HERE.parent.parent), help='checkout with tools/dinkex/out (hardness and owner images, for (b))')
    ap.add_argument('--blockers', default=None, help='(b) walk_blockers.csv of a blocker-on dink.WalkAudit of the enlarged world (player-only hulls)')
    ap.add_argument('--limit-cm', type=float, default=100.0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--suggest', default=None, help='write the seal rows for the unsealed closed pockets to this json (for review)')
    a = ap.parse_args(argv)
    skip = frozenset(authored_screens(a.art))
    blocked = blocked_masks(a.collision)
    ref, new = load_layout(a.layout_ref), load_layout(a.layout_new)
    sealed = load_sealed(a.sealed)
    play = PlayData(a.repo, a.relaxed)
    findings = audit_gaps(blocked, ref, new, a.capsule_cm / 100.0, skip, sealed, play)
    pockets = [f for f in findings if f['kind'] == 'pocket']
    joins = [f for f in findings if f['kind'] == 'join']
    unsealed_closed = [f for f in pockets if f['closed'] and not f['sealed'] and 'seal' in f]
    if a.suggest:
        rows, seen = {}, set()
        for f in sorted(unsealed_closed, key=lambda f: -f['px']):
            where = '; '.join('SCR_%03d x %d-%d y %d-%d' % (n, b[0], b[2], b[1], b[3]) for n, b in sorted(f['screens'].items()))
            for n, rects in sorted(f['seal'].items()):
                for r in rects:
                    if (n, tuple(r)) in seen:
                        continue
                    seen.add((n, tuple(r)))
                    rows.setdefault(str(n), []).append({'rect': r, 'why': 'closed pocket of the 1997 map (check_capsule_gaps.py): the capsule fits it at the enlarged scale (%s), nowhere at the reference' % where})
        Path(a.suggest).write_text(json.dumps({'screens': rows}, indent=1) + '\n', encoding='utf-8')
    walls = audit_walls(a.phys, a.relaxed, a.repo, new, a.limit_cm / 100.0, skip) if a.phys else []
    if a.phys and a.blockers:
        walls += audit_blockers(a.blockers, load_mask3(Path(a.phys) / 'phys_drawn_mask.csv'), new, a.limit_cm / 100.0, skip)
    lines = [f'# Capsule gaps and invisible walls at the enlarged world scale (check_capsule_gaps.py)', '',
             f'Screens checked {len(blocked) - len(skip & set(blocked))} (authored collision skipped: {sorted(skip)}); capsule {a.capsule_cm:.0f} cm.', '',
             f'## (a) capsule gaps: {len(pockets)} pockets ({sum(f["closed"] for f in pockets)} closed, {sum(f["sealed"] for f in pockets)} sealed), {len(joins)} joins', '']
    for f in sorted(pockets, key=lambda f: (not f['closed'], -f['px'])):
        lines.append('- POCKET %s%s %d px: %s%s' % ('closed' if f['closed'] else 'open', ' SEALED' if f['sealed'] else '', f['px'],
                                                   '; '.join('SCR_%03d x %d-%d y %d-%d' % (n, b[0], b[2], b[1], b[3]) for n, b in sorted(f['screens'].items())),
                                                   (' -- ' + f['note']) if f.get('note') else ''))
    for f in sorted(joins, key=lambda f: -f['px']):
        (n, b), = f['screens'].items()
        lines.append('- JOIN %d px: SCR_%03d x %d-%d y %d-%d joins reference regions of %s px' % (f['px'], n, b[0], b[2], b[1], b[3], f['joins']))
    if a.phys:
        lines += ['', f'## (b) boxes Dink meets in play reaching more than {a.limit_cm:.0f} cm from anything drawn: {len(walls)}', '']
        by = {}
        for w in walls:
            by.setdefault(w['why'], []).append(w)
        for why, ws in sorted(by.items(), key=lambda kv: -len(kv[1])):
            lines.append(f'### {why}: {len(ws)}')
            for w in sorted(ws, key=lambda w: -w['max_m'])[:40]:
                lines.append('- %s %s (%s) up to %s m, %d of %d contact px beyond' % (w['origin'], w['mesh'] or '-', w['kinds'] or '-',
                                                                                    w['max_m'] if w['max_m'] >= 0 else 'inf (nothing drawn)', w['far_px'], w['contact_px']))
            lines.append('')
    text = '\n'.join(lines) + '\n'
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        Path(a.out, 'capsule_gaps.md').write_text(text, encoding='utf-8')
        with open(Path(a.out, 'capsule_gaps.csv'), 'w', newline='', encoding='utf-8') as fh:
            wr = csv.writer(fh)
            wr.writerow(['kind', 'closed', 'sealed', 'px', 'screen', 'l', 't', 'r', 'b', 'joins'])
            for f in findings:
                for n, b in sorted(f['screens'].items()):
                    wr.writerow([f['kind'], int(f['closed']), int(f['sealed']), f['px'], n, *b, ' '.join(map(str, f.get('joins', [])))])
        if a.phys:
            with open(Path(a.out, 'invisible_walls.csv'), 'w', newline='', encoding='utf-8') as fh:
                wr = csv.DictWriter(fh, fieldnames=['screen', 'origin', 'mesh', 'kinds', 'script', 'why', 'max_m', 'far_px', 'contact_px', 'box'])
                wr.writeheader()
                for w in walls:
                    wr.writerow(dict(w, box=' '.join(map(str, w['box']))))
    print(text if not a.out else text[:4000])
    if unsealed_closed:
        print(f'FAIL: {len(unsealed_closed)} closed pocket(s) the layer could seal are not in {a.sealed}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
