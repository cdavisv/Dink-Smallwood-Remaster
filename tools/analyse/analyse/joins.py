"""Designed joins (regions.toml [[join]]): owner decisions that change the 1997 map data.

A join opens a doorway between two neighbouring screens. Each side names void tiles that become
floor (a tile number used elsewhere on the same screen) and a rectangle of map pixels that becomes
walkable (hardness 0): the passage. The free (hardness-0) pixels of those tiles within JAMB_PX of
the passage become code 1 (solid), so the passage is walled off from the void around the rooms;
the rest of the void is left as it was (the 1997 engine's sequence breaks through it stay). The patch is applied to the
build's in-memory IR (tile records and hardness images) before any analysis; tools/dinkex/out is
never written. `resolve` checks the table against the data and stops the build (SystemExit) on any
violation; `check_crossings` stops it when the join does not yield a walkable crossing.

Scripts/export_import_bundle.py (DinkRemasterUE) reads the resolved joins from connectivity.json
`designed_joins` and applies the same patch (`apply_patch` semantics) to the greybox.
"""

import copy

import numpy as np

from .ir import W, H, TILE, WALKABLE, SOLID, WARP, screen_id, col_row

TILES_X = W // TILE


def _fail(join_id, msg):
    raise SystemExit("regions.toml [[join]] %s: %s" % (join_id, msg))


def _shared_edge(a, b):
    """Edge of screen a that it shares with grid neighbour b, or None."""
    ca, ra = col_row(a)
    cb, rb = col_row(b)
    if ra == rb and cb == ca + 1:
        return "right"
    if ra == rb and cb == ca - 1:
        return "left"
    if ca == cb and rb == ra + 1:
        return "down"
    if ca == cb and rb == ra - 1:
        return "up"
    return None


def _touches(edge, rect):
    x0, y0, x1, y1 = rect
    return {"right": x1 == W, "left": x0 == 0, "down": y1 == H, "up": y0 == 0}[edge]


def resolve(ir, table):
    """Validate every [[join]] against the IR. Returns resolved joins (JSON-ready dicts)."""
    from .connectivity import tile_group
    tc = ir.tile_classes
    out = []
    seen_tiles = set()
    for j in table.get("join", []):
        jid = j.get("id") or "(no id)"
        for key in ("id", "decided", "reason", "screens", "side"):
            if key not in j:
                _fail(jid, "missing %r" % key)
        screens = list(j["screens"])
        if len(screens) != 2 or len(set(screens)) != 2:
            _fail(jid, "screens must name two different screens, got %r" % (screens,))
        for n in screens:
            if n not in ir.screens:
                _fail(jid, "SCR_%03d is not a used screen" % n)
        a, b = screens
        if _shared_edge(a, b) is None:
            _fail(jid, "%s and %s are not grid neighbours" % (screen_id(a), screen_id(b)))
        if ir.indoor(a) != ir.indoor(b):
            _fail(jid, "%s and %s are not both indoor or both outdoor" % (screen_id(a), screen_id(b)))
        sides = j["side"]
        if sorted(s.get("screen") for s in sides) != sorted(screens):
            _fail(jid, "needs exactly one [[join.side]] per screen of %r" % (screens,))
        rsides = []
        for s in sides:
            n = s["screen"]
            other = b if n == a else a
            edge = _shared_edge(n, other)
            used_nums = {}
            for t in ir.screens[n]["tiles"]:
                used_nums.setdefault(t["num"], t)
            tiles = []
            if not s.get("tiles"):
                _fail(jid, "%s: no tiles" % screen_id(n))
            for item in s["tiles"]:
                if len(item) != 3:
                    _fail(jid, "%s: tile entries are [col, row, tile], got %r" % (screen_id(n), item))
                c, r, num = (int(v) for v in item)
                if not (0 <= c < TILES_X and 0 <= r < H // TILE):
                    _fail(jid, "%s: tile (%d, %d) is outside the 12 x 8 grid" % (screen_id(n), c, r))
                if (n, c, r) in seen_tiles:
                    _fail(jid, "%s: tile (%d, %d) named twice" % (screen_id(n), c, r))
                seen_tiles.add((n, c, r))
                old = ir.screens[n]["tiles"][r * TILES_X + c]
                og = tile_group(tc.get(old["num"]))
                if og != "void":
                    _fail(jid, "%s tile (%d, %d) is tile %d (%s, group %s), not void: a join may only floor "
                          "over void" % (screen_id(n), c, r, old["num"],
                                         (tc.get(old["num"]) or {}).get("terrain", "unclassified"), og))
                if num not in used_nums:
                    _fail(jid, "%s tile (%d, %d): tile %d is not used on this screen" % (screen_id(n), c, r, num))
                ng = tile_group(tc.get(num))
                if ng != "land":
                    _fail(jid, "%s tile (%d, %d): replacement tile %d is %s, not floor" % (screen_id(n), c, r, num, ng))
                tiles.append({"col": c, "row": r, "from": old["num"], "to": num,
                              "from_terrain": (tc.get(old["num"]) or {}).get("terrain"),
                              "to_terrain": (tc.get(num) or {}).get("terrain")})
            rect = [int(v) for v in s.get("open", [])]
            if len(rect) != 4:
                _fail(jid, "%s: open must be [x0, y0, x1, y1]" % screen_id(n))
            x0, y0, x1, y1 = rect
            if not (0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H):
                _fail(jid, "%s: open %r is not a rectangle inside the 600 x 400 map" % (screen_id(n), rect))
            if not _touches(edge, rect):
                _fail(jid, "%s: open %r does not reach its %s edge (shared with %s)" % (screen_id(n), rect, edge, screen_id(other)))
            # every pixel of the passage on floor (after the change)
            new_num = {(t["col"], t["row"]): t["to"] for t in tiles}
            for r in range(y0 // TILE, (y1 - 1) // TILE + 1):
                for c in range(x0 // TILE, (x1 - 1) // TILE + 1):
                    num = new_num.get((c, r), ir.screens[n]["tiles"][r * TILES_X + c]["num"])
                    if tile_group(tc.get(num)) != "land":
                        _fail(jid, "%s: open %r covers tile (%d, %d) (tile %d), which is not floor" % (
                            screen_id(n), rect, c, r, num))
            for v in ir.visions(n):
                h = ir.raw_hardness(n, v)
                if (h[y0:y1, x0:x1] == WARP).any():
                    _fail(jid, "%s: open %r covers warp hardness (code 200) in vision %d" % (screen_id(n), rect, v))
            rsides.append({"screen": screen_id(n), "screen_number": n, "edge": edge, "tiles": tiles, "open": rect})
        out.append({"id": j["id"], "decided": str(j["decided"]), "decided_by": j.get("decided_by", "owner"),
                    "reason": j["reason"], "screens": [screen_id(n) for n in screens],
                    "screen_numbers": screens, "sides": rsides})
    return out


def tile_mask(side):
    m = np.zeros((H, W), bool)
    for t in side["tiles"]:
        m[t["row"] * TILE:(t["row"] + 1) * TILE, t["col"] * TILE:(t["col"] + 1) * TILE] = True
    return m


JAMB_PX = 2


def apply_patch(hard, side):
    """The join's hardness rule on one image: the passage walkable; every free pixel of the floored
    tiles within JAMB_PX of the passage solid (the jambs, which wall it off from the void around
    the rooms; the rest of the void stays as it was). Returns (patched copy, opened px, closed px)."""
    x0, y0, x1, y1 = side["open"]
    out = hard.copy()
    opened = np.zeros(hard.shape, bool)
    opened[y0:y1, x0:x1] = True
    ring = np.zeros(hard.shape, bool)
    ring[max(0, y0 - JAMB_PX):min(H, y1 + JAMB_PX), max(0, x0 - JAMB_PX):min(W, x1 + JAMB_PX)] = True
    closed = tile_mask(side) & (hard == WALKABLE) & ring & ~opened
    n_open = int((opened & (hard != WALKABLE)).sum())
    out[opened] = WALKABLE
    out[closed] = SOLID
    return out, n_open, int(closed.sum())


def install(ir, joins):
    """Patch the IR in memory: tile records (number, tileset cell, source rect) and the hardness
    images of every vision. Adds per-side statistics (pixels opened/closed, hardboxes cut)."""
    for j in joins:
        for side in j["sides"]:
            n = side["screen_number"]
            tiles = ir.screens[n]["tiles"]
            by_num = {}
            for t in tiles:
                by_num.setdefault(t["num"], t)
            for t in side["tiles"]:
                i = t["row"] * TILES_X + t["col"]
                old = tiles[i]
                tmpl = by_num[t["to"]]
                new = copy.deepcopy(tmpl)
                for k in ("id", "index", "col", "row", "x", "y"):
                    new[k] = old[k]
                new["designed_join"] = j["id"]
                new["replaces"] = old["num"]
                tiles[i] = new
            ir.hard_patches.setdefault(n, []).append(side)
            # statistics on vision 0 (the patch is the same for every vision)
            raw = ir.raw_hardness(n, 0)
            owner = ir.owner(n, 0)
            x0, y0, x1, y1 = side["open"]
            box = raw[y0:y1, x0:x1]
            own = owner[y0:y1, x0:x1][box == 100]
            idx = sorted({int(v) for v in own.tolist()})
            by_index = {p["index"]: p["id"] for p in ir.screens[n]["placements"]}
            side["cut_hardboxes"] = [by_index.get(i, "index %d" % i) for i in idx]
            _, side["opened_px"], side["closed_px"] = apply_patch(raw, side)
    ir.drop_cache()


def check_crossings(joins, crossings):
    """Attach the walkable crossings each join produced; stop the build when there is none."""
    for j in joins:
        a, b = sorted(j["screen_numbers"])
        cs = [c for c in crossings if (c["a"], c["b"]) == (a, b) and c["walkable"]]
        if not cs:
            raise SystemExit("regions.toml [[join]] %s: no walkable crossing between SCR_%03d and SCR_%03d after the "
                             "patch (check the open rectangles line up on the shared edge)" % (j["id"], a, b))
        j["crossings"] = [{"a": screen_id(c["a"]), "b": screen_id(c["b"]), "dir": c["dir"],
                           "a_component": "%s#%d" % (screen_id(c["a"]), c["a_comp"]),
                           "b_component": "%s#%d" % (screen_id(c["b"]), c["b_comp"]),
                           "axis": c["axis"], "from": c["from"], "to": c["to"], "length": c["length"],
                           "reached": bool(c.get("reached"))} for c in cs]
    return joins
