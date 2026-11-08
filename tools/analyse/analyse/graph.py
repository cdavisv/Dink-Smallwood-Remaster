"""World walk graph: reachability, walk groups, pockets, water bodies."""

from collections import deque

from .connectivity import UnionFind, node_id
from .ir import W, H, GRID_W, GRID_H, col_row, screen_id


def start_node(ir, comps, start_screen, sx, sy):
    from .warps import nearest_walkable
    nw = nearest_walkable(comps[start_screen].labels, sx, sy, 80)
    return (start_screen, nw[0])


BARRIER = ("water", "canopy", "void")


def walkable_crossing(c, barrier=BARRIER):
    """A crossing counts as player movement only between player-space classes."""
    return c["a_class"] not in barrier and c["b_class"] not in barrier


def reach(comps, crossings, warps, swarps, start, use_script_warps=True, use_wraps=None, barrier=BARRIER):
    """Breadth-first search over components. Crossings into a component whose class is in
    `barrier` are dropped (the design's player space: water, canopy and void are out; the
    engine only looks at hardness, so `barrier=()` keeps them); `use_wraps` adds the engine's
    row-wrap crossings (off the right edge of column 31 onto column 0 of the next row)."""
    adj = {}
    crossings = [c for c in crossings if walkable_crossing(c, barrier)]
    for c in crossings:
        a, b = (c["a"], c["a_comp"]), (c["b"], c["b_comp"])
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    for c in use_wraps or []:
        a, b = (c["a"], c["a_comp"]), (c["b"], c["b_comp"])
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    for w in warps:
        if w.get("dst_comp"):
            for k in w["src_comps"]:
                adj.setdefault((w["src_screen"], k), []).append((w["dst_screen"], w["dst_comp"]))
    screen_out = {}
    if use_script_warps:
        for w in swarps:
            if w.get("dst_comp"):
                for s in w["src_screens"]:
                    screen_out.setdefault(s, []).append((w["dst_screen"], w["dst_comp"]))
    seen = {start: None}
    fired = set()
    q = deque([start])
    while q:
        u = q.popleft()
        nxt = list(adj.get(u, []))
        if u[0] in screen_out and u[0] not in fired:
            fired.add(u[0])
            nxt += screen_out[u[0]]
        for v in nxt:
            if v not in seen:
                seen[v] = u
                q.append(v)
    return seen


def walk_groups(comps, crossings):
    uf = UnionFind()
    for n, sc in comps.items():
        for k in range(1, sc.count + 1):
            uf.find((n, k))
    for c in crossings:
        if walkable_crossing(c):
            uf.union((c["a"], c["a_comp"]), (c["b"], c["b_comp"]))
    return uf


def open_edges(ir, n):
    """Edges of screen n with no neighbour screen (grid border or unused cell)."""
    c, r = col_row(n)
    out = []
    if c == 0 or (n - 1) not in ir.screens: out.append("left")
    if c == GRID_W - 1 or (n + 1) not in ir.screens: out.append("right")
    if r == 0 or (n - GRID_W) not in ir.screens: out.append("up")
    if r == GRID_H - 1 or (n + GRID_W) not in ir.screens: out.append("down")
    return out


def water_bodies(ir, comps, crossings, river_width_px):
    uf = UnionFind()
    water = []
    for n, sc in comps.items():
        for k in range(1, sc.count + 1):
            if sc.terrain_class(k) == "water":
                water.append((n, k))
                uf.find((n, k))
    for c in crossings:
        if c["a_class"] == "water" and c["b_class"] == "water":
            uf.union((c["a"], c["a_comp"]), (c["b"], c["b_comp"]))
    bodies = {}
    for node in water:
        bodies.setdefault(uf.find(node), []).append(node)
    out = []
    comp_kind = {}
    for root in sorted(bodies):
        nodes = bodies[root]
        area = sum(int(comps[n].area[k]) for n, k in nodes)
        touches_open = False
        for n, k in nodes:
            for e in open_edges(ir, n):
                if (comps[n].edge_labels[e] == k).any():
                    touches_open = True
        screens = sorted({n for n, _ in nodes})
        kind = "sea" if touches_open else "lake"
        if area < 2000:
            kind = "puddle"
        for n, k in nodes:
            sc = comps[n]
            width = 2.0 * sc.area[k] / max(sc.perimeter[k], 1)
            ck = kind
            if kind != "puddle" and width < river_width_px:
                ck = "river"
            comp_kind[(n, k)] = ck
        out.append({"id": node_id(*root), "kind": kind, "area_px": area, "screens": screens,
                    "components": len(nodes), "touches_open_edge": touches_open})
    out.sort(key=lambda b: -b["area_px"])
    return out, comp_kind
