"""Walkable components per screen, edge crossings between screens, and the
world-wide walk graph.

Walkable = hardness code 0. Codes 1, 2 (low: water, fences), 3, 100 and 200
all stop the player. A screen with vision-gated placements is labelled on the
*permissive* mask (walkable in any of its vision variants); each crossing also
records whether it is open in vision 0 and in every variant.

A screen change happens when the player walks off an edge onto a neighbour
that has a map record (engine: did_player_cross_screen). We count a crossing
where the edge pixels are walkable on both sides along a run of at least
`min_crossing_px` pixels (default 4), matched pixel for pixel (x for up/down,
y for left/right). The engine also wraps: walking off the left edge of a
column-0 screen loads screen-1, which is the previous row's column 31. Those
are reported separately as `wrap_crossings` and are not used for layout.
"""

import numpy as np

from .ir import W, H, GRID_W, GRID_H, TILE, WALKABLE, screen_id, col_row, screen_of
from .labels import label

# terrain (tools/data/tile_classes.csv) -> component class
TERRAIN_GROUP = {
    "water": "water",
    "forest_canopy": "canopy",
    "void": "void",
    "chasm": "void",
    "lava": "blocked",
    "rock_mass": "blocked",
    "cave_wall": "blocked",
    "structure_facade": "blocked",
}
GROUPS = ["land", "water", "canopy", "void", "blocked"]


def tile_group(row):
    if row is None:
        return "land"
    t = row["terrain"]
    if t in TERRAIN_GROUP:
        return TERRAIN_GROUP[t]
    if t == "cliff_face" or row["walkable_hint"] == "no":
        # cliff ridges are drawn as outlines too: their insides are hardness 0
        return "blocked"
    return "land"


class ScreenComps:
    """Components of one screen's permissive walk mask."""

    def __init__(self, ir, n, removable=()):
        """`removable`: placement indices whose sprite hardbox can be removed in
        play (breakable barrels, bombable rocks, burnable trees, pushable rocks,
        killable monsters). Their pixels count as walkable in `perm`; `plain`
        is the same mask with them solid."""
        self.n = n
        self.visions = ir.visions(n)
        removable = np.array(sorted(removable), dtype=np.int64)
        masks, plains = [], []
        for v in self.visions:
            h = ir.hardness(n, v)
            plain = h == WALKABLE
            m = plain
            if len(removable):
                o = ir.owner(n, v)
                m = plain | ((h == 100) & np.isin(o, removable))
            masks.append(m)
            plains.append(plain)
        self.base = masks[0]
        self.all_open = np.logical_and.reduce(masks)
        self.perm = np.logical_or.reduce(masks)
        self.plain = np.logical_or.reduce(plains)
        lab, cnt = label(self.perm)
        self.count = cnt
        self._packed = np.packbits(self.perm.ravel())
        self._lab = lab
        # per-component stats
        flat = lab.ravel()
        self.area = np.bincount(flat, minlength=cnt + 1)
        ys, xs = np.indices(lab.shape)
        self.sum_x = np.bincount(flat, weights=xs.ravel(), minlength=cnt + 1)
        self.sum_y = np.bincount(flat, weights=ys.ravel(), minlength=cnt + 1)
        # terrain group per pixel via tile grid
        tc = ir.tile_classes
        groups = np.array([GROUPS.index(tile_group(tc.get(t["num"]))) for t in ir.screens[n]["tiles"]])
        tidx = (ys // TILE) * (W // TILE) + (xs // TILE)
        gimg = groups[tidx]
        gc = np.bincount(flat * len(GROUPS) + gimg.ravel(), minlength=(cnt + 1) * len(GROUPS))
        self.group_px = gc.reshape(cnt + 1, len(GROUPS))
        # bbox
        self.bbox = np.zeros((cnt + 1, 4), int)
        if cnt:
            nz = flat > 0
            lf = flat[nz]
            xf = xs.ravel()[nz]
            yf = ys.ravel()[nz]
            x0 = np.full(cnt + 1, W); y0 = np.full(cnt + 1, H)
            x1 = np.zeros(cnt + 1, int); y1 = np.zeros(cnt + 1, int)
            np.minimum.at(x0, lf, xf); np.minimum.at(y0, lf, yf)
            np.maximum.at(x1, lf, xf + 1); np.maximum.at(y1, lf, yf + 1)
            self.bbox = np.stack([x0, y0, x1, y1], 1)
        # perimeter (4-neighbour boundary pixel count), used for mean width
        m = self.perm
        inner = m.copy()
        inner[1:, :] &= m[:-1, :]; inner[:-1, :] &= m[1:, :]
        inner[:, 1:] &= m[:, :-1]; inner[:, :-1] &= m[:, 1:]
        boundary = m & ~inner
        self.perimeter = np.bincount(flat[boundary.ravel()], minlength=cnt + 1)
        self.edge_labels = {
            "left": lab[:, 0].copy(), "right": lab[:, W - 1].copy(),
            "up": lab[0, :].copy(), "down": lab[H - 1, :].copy(),
        }
        self.edge_base = {
            "left": self.base[:, 0].copy(), "right": self.base[:, W - 1].copy(),
            "up": self.base[0, :].copy(), "down": self.base[H - 1, :].copy(),
        }
        self.edge_plain = {
            "left": self.plain[:, 0].copy(), "right": self.plain[:, W - 1].copy(),
            "up": self.plain[0, :].copy(), "down": self.plain[H - 1, :].copy(),
        }
        # components that are split when removable obstacles stay in place
        plab, pcnt = label(self.plain)
        pa = np.bincount(plab.ravel(), minlength=pcnt + 1)
        big = np.nonzero(pa >= 400)[0]
        big = big[big > 0]
        self.split_by_obstacles = {}
        if len(big):
            pl = plab.ravel().astype(np.int64)
            sel = np.isin(pl, big)
            keys = np.unique(flat[sel].astype(np.int64) * 65536 + pl[sel])
            per = {}
            for key in keys.tolist():
                per.setdefault(key >> 16, []).append(key & 0xFFFF)
            self.split_by_obstacles = {k: len(v) for k, v in per.items() if len(v) > 1}
        self.edge_all = {
            "left": self.all_open[:, 0].copy(), "right": self.all_open[:, W - 1].copy(),
            "up": self.all_open[0, :].copy(), "down": self.all_open[H - 1, :].copy(),
        }

    @property
    def labels(self):
        if self._lab is None:
            perm = np.unpackbits(self._packed)[: W * H].reshape(H, W).astype(bool)
            self._lab, _ = label(perm)
        return self._lab

    def drop_image(self):
        """Free the full-size arrays (keep stats, edges and a packed mask)."""
        self._lab = None
        self.base = self.all_open = self.perm = self.plain = None

    def terrain_class(self, k):
        g = self.group_px[k]
        return GROUPS[int(np.argmax(g))]

    def centroid(self, k):
        a = max(self.area[k], 1)
        return (self.sum_x[k] / a, self.sum_y[k] / a)


def node_id(n, k):
    return "%s#%d" % (screen_id(n), k)


def find_crossings(ir, comps, min_run):
    """All grid-neighbour crossings plus engine wrap crossings."""
    out = []
    wraps = []
    for n in ir.used:
        c, r = col_row(n)
        pairs = []
        if c + 1 < GRID_W and (n + 1) in comps:
            pairs.append(("right", "left", n + 1, out))
        if r + 1 < GRID_H and (n + GRID_W) in comps:
            pairs.append(("down", "up", n + GRID_W, out))
        if c == GRID_W - 1 and (n + 1) in comps:
            pairs.append(("right", "left", n + 1, wraps))       # engine pmap+1 wrap
        for ea, eb, m, sink in pairs:
            A, B = comps[n], comps[m]
            la, lb = A.edge_labels[ea], B.edge_labels[eb]
            both = (la > 0) & (lb > 0)
            if not both.any():
                continue
            # split into runs where both labels stay constant
            idx = np.nonzero(both)[0]
            brk = np.nonzero((np.diff(idx) != 1) | (np.diff(la[idx]) != 0) | (np.diff(lb[idx]) != 0))[0]
            starts = np.concatenate([[idx[0]], idx[brk + 1]])
            ends = np.concatenate([idx[brk], [idx[-1]]])
            for s0, e in zip(starts.tolist(), ends.tolist()):
                length = e - s0 + 1
                if length < min_run:
                    continue
                ka, kb = int(la[s0]), int(lb[s0])
                base_open = bool((A.edge_base[ea][s0:e + 1] & B.edge_base[eb][s0:e + 1]).any())
                all_open = bool((A.edge_all[ea][s0:e + 1] & B.edge_all[eb][s0:e + 1]).any())
                plain_open = bool((A.edge_plain[ea][s0:e + 1] & B.edge_plain[eb][s0:e + 1]).any())
                sink.append({
                    "a": n, "b": m, "dir": ea, "a_comp": ka, "b_comp": kb,
                    "from": int(s0), "to": int(e + 1), "length": int(length),
                    "axis": "y" if ea == "right" else "x",
                    "open_vision0": base_open, "open_all_visions": all_open,
                    "needs_obstacle_removal": not plain_open,
                    "a_class": A.terrain_class(ka), "b_class": B.terrain_class(kb),
                })
    return out, wraps


class UnionFind:
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        p.setdefault(x, x)
        root = x
        while p[root] != root:
            root = p[root]
        while p[x] != root:
            p[x], x = root, p[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.p[rb] = ra
            else:
                self.p[ra] = rb
