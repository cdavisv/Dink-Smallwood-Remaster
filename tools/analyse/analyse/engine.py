"""Engine reach: everything the original engine lets the player walk to, by hardness alone.

`graph.reach` answers "where can the player go as designed": it keeps water, forest canopy and
void out of player space and ignores the row wrap. The engine knows none of that. It tests one
hardness pixel per step (get_hard_play, dink.cpp D:548), so any pixel with code 0 is standable
and `did_player_cross_screen` (D:14049) carries Dink over every screen edge where the next map
record exists, wrapping from column 31 to column 0 of the next row. `engine_reach` is the same
search without the terrain filter and with the wrap, over the same permissive components, warps
and script warps. A screen reached this way but not by design is a sequence break: it is
playable, but no designed route leads to it.
"""

from collections import defaultdict

from . import graph as G
from .connectivity import node_id
from .ir import screen_id


DRY = ("water",)      # hardness-free ground that is not open water: cliff faces, forest interiors, black void
WADING = ()           # everything with hardness 0, open water included


def engine_reach(comps, crossings, wraps, warps, swarps, start, barrier=WADING):
    """Search with the engine's rules: hardness only (plus the row wrap). `barrier=DRY` leaves
    open water out, which separates routes that need no wading from the ones that do."""
    return G.reach(comps, crossings, warps, swarps, start, use_wraps=wraps, barrier=barrier)


def route(seen, node):
    out = []
    while node is not None:
        out.append(node)
        node = seen[node]
    return out[::-1]


def edge_kind(a, b, crossings, wraps, warps, swarps):
    """How the search got from component a to component b: crossing, wrap, warp or script_warp."""
    wrap_pairs = {((c["a"], c["a_comp"]), (c["b"], c["b_comp"])) for c in wraps}
    wrap_pairs |= {(q, p) for p, q in wrap_pairs}
    if (a, b) in wrap_pairs:
        return "wrap", None
    for wp in warps:
        if wp.get("dst_comp") and (wp["dst_screen"], wp["dst_comp"]) == b and a[0] == wp["src_screen"] and a[1] in wp["src_comps"]:
            return "warp", wp["id"]
    for sw in swarps:
        if sw.get("dst_comp") and (sw["dst_screen"], sw["dst_comp"]) == b and a[0] in sw["src_screens"]:
            return "script_warp", sw["id"]
    return "crossing", None


def describe(w, seen, target):
    """Route from the last component the design reaches to `target`, step by step."""
    path = route(seen, target)
    first = 0
    for i, node in enumerate(path):
        if node in w.reached:
            first = i
    path = path[first:]
    steps = []
    for i, node in enumerate(path):
        n, k = node
        sc = w.comps[n]
        step = {"component": node_id(n, k), "class": sc.terrain_class(k), "area_px": int(sc.area[k]),
                "by_design": node in w.reached}
        if i:
            kind, ident = edge_kind(path[i - 1], node, w.crossings, w.wraps, w.warps, w.swarps)
            step["via"] = kind
            if ident:
                step["via_id"] = ident
        if sc.split_by_obstacles.get(k, 1) > 1:
            step["opens_when_removed"] = sorted(
                "%s:%s" % (p["id"], w.removable[n][p["index"]]) for p in w.ir.screens[n]["placements"]
                if p["index"] in w.removable[n])
        steps.append(step)
    return steps


def report(w):
    """engine_reach.json content. Needs w.reached_engine / w.engine_seen from analyse()."""
    ir = w.ir
    by_region = defaultdict(lambda: {"screens": set(), "design": set(), "dry": set(), "wading": set()})
    rows = {r["screen"]: r for r in w.rows}
    for n in ir.used:
        by_region[rows[n]["region"]]["screens"].add(n)
    for key, nodes in (("design", w.reached), ("dry", w.reached_dry), ("wading", w.reached_engine)):
        for n, k in nodes:
            by_region[rows[n]["region"]][key].add(n)
    design_screens = {n for n, _ in w.reached}
    dry_screens = {n for n, _ in w.reached_dry}
    wading_screens = {n for n, _ in w.reached_engine}
    regions = {}
    for name, rg in sorted(by_region.items()):
        rec = {"screens": len(rg["screens"]), "reached_by_design": len(rg["design"]),
               "reached_engine_dry": len(rg["dry"]), "reached_engine_wading": len(rg["wading"]),
               "engine_only_dry": [screen_id(n) for n in sorted(rg["dry"] - rg["design"])],
               "engine_only_wading": [screen_id(n) for n in sorted(rg["wading"] - rg["dry"])]}
        for label, seen, nodes in (("dry", w.dry_seen, w.reached_dry), ("wading", w.engine_seen, w.reached_engine)):
            if not (rg[label] - rg["design"]):
                continue
            # the biggest land component this level reaches and the design does not
            best = None
            for n, k in nodes:
                if (n, k) in w.reached or rows[n]["region"] != name:
                    continue
                sc = w.comps[n]
                if sc.terrain_class(k) != "land":
                    continue
                if best is None or sc.area[k] > w.comps[best[0]].area[best[1]]:
                    best = (n, k)
            if best:
                rec["route_to_largest_land_" + label] = {"target": node_id(*best), "steps": describe(w, seen, best)}
        regions[name] = rec
    wraps_used = []
    pairs = {((c["a"], c["a_comp"]), (c["b"], c["b_comp"])): c for c in w.wraps}
    for (a, b), c in pairs.items():
        if a in w.dry_seen and b in w.dry_seen:
            wraps_used.append({"a": screen_id(c["a"]), "b": screen_id(c["b"]), "from": c["from"], "to": c["to"],
                               "a_class": c["a_class"], "b_class": c["b_class"],
                               "a_reached_by_design": a in w.reached})
    return {
        "schema": "analyse/1/engine_reach",
        "rules": {
            "design_reach": "walkable crossings between player-space components (not water, canopy, void), "
                            "sprite warps, script warps; no row wrap",
            "engine_dry": "every edge crossing whose pixels are free on both sides except into open water, plus the row "
                          "wrap (right edge of column 31 -> column 0 of the next row, did_player_cross_screen), "
                          "sprite warps and script warps; components are 4-connected permissive masks. Cliff faces, "
                          "forest interiors and the black void around interior rooms count as ground",
            "engine_wading": "the same with open water too: the shoreline outline is cut at some screen edges "
                             "(`edge_leaks` in connectivity.json), and the sea inside it is hardness 0",
            "sequence_break": "a screen the engine reaches and the design does not",
            "diagonal_note": "the engine tests the destination pixel of each diagonal step only, so 8-connected "
                             "free space is what Dink really moves through; shoreline outlines are 1 px lines and "
                             "leak into open sea when read that way, so the report uses 4-connected components."},
        "counts": {"reached_by_design_screens": len(design_screens), "reached_engine_dry_screens": len(dry_screens),
                   "reached_engine_wading_screens": len(wading_screens),
                   "engine_only_dry_screens": len(dry_screens - design_screens),
                   "engine_only_wading_screens": len(wading_screens - dry_screens)},
        "engine_only_dry_screens": [screen_id(n) for n in sorted(dry_screens - design_screens)],
        "engine_only_wading_screens": [screen_id(n) for n in sorted(wading_screens - dry_screens)],
        "wrap_crossings_in_dry_reach": wraps_used,
        "regions": regions,
    }
