"""`analyse build`: run stages 3 and 4 and write every output."""

import csv
import json
import os
import re
import time
from collections import Counter, defaultdict

import numpy as np

from . import engine as EN
from . import graph as G
from . import interiors as I
from . import layout as LY
from . import regions as RG
from . import render as RD
from . import warps as WP
from .connectivity import ScreenComps, find_crossings, node_id
from .ir import IR, W, H, TILE, col_row, screen_id
from .scripts import Scripts, removable_map, placed_scripts, script_screens

SCHEMA = "analyse/1"


def r4(x):
    return round(float(x), 4)


class World:
    """Everything the build computes, kept in memory for the tests."""


def analyse(ir_dir, table_path, story_dir=None, classes_dir=None, dinkc_dir=None, log=print):
    t0 = time.time()
    w = World()
    ir = IR(ir_dir, story_dir=story_dir, classes_dir=classes_dir)
    if not ir.tile_classes:
        raise SystemExit("tile_classes.csv not found under %s (needed to tell land from water)" % ir.classes_dir)
    table = RG.load_table(table_path)
    lay = table["layout"]
    scripts = Scripts(ir.story_dir)
    w.ir, w.table, w.scripts = ir, table, scripts

    # --- connectivity ------------------------------------------------------
    removable = removable_map(ir, scripts)
    comps = {}
    for n in ir.used:
        comps[n] = ScreenComps(ir, n, removable[n].keys())
        comps[n].drop_image()
    ir.drop_cache()
    crossings, wraps = find_crossings(ir, comps, lay["min_crossing_px"])
    log("components: %d on %d screens, %d edge crossings (%.1f s)" % (
        sum(c.count for c in comps.values()), len(comps), len(crossings), time.time() - t0))
    warps = WP.sprite_warps(ir, comps)
    swarps = WP.script_warps(ir, comps, scripts)
    WP.link_returns(ir, warps, swarps)
    st = lay["start"]
    start = G.start_node(ir, comps, st["screen"], st["x"], st["y"])
    reached = G.reach(comps, crossings, warps, swarps, start)
    reached_sprite_only = G.reach(comps, crossings, warps, swarps, start, use_script_warps=False)
    engine_seen = EN.engine_reach(comps, crossings, wraps, warps, swarps, start)
    dry_seen = EN.engine_reach(comps, crossings, wraps, warps, swarps, start, barrier=EN.DRY)
    uf = G.walk_groups(comps, crossings)
    group_of = {}
    for n, sc in comps.items():
        for k in range(1, sc.count + 1):
            group_of[(n, k)] = uf.find((n, k))
    for c in crossings:
        c["walkable"] = G.walkable_crossing(c)
        c["reached"] = c["walkable"] and (c["a"], c["a_comp"]) in reached
    bodies, comp_wkind = G.water_bodies(ir, comps, crossings, lay["river_width_px"])
    w.comps, w.crossings, w.wraps, w.warps, w.swarps = comps, crossings, wraps, warps, swarps
    w.start, w.reached, w.group_of, w.removable = start, reached, group_of, removable
    w.reached_sprite_only, w.bodies, w.comp_wkind = reached_sprite_only, bodies, comp_wkind
    w.engine_seen = w.reached_engine = engine_seen
    w.dry_seen = w.reached_dry = dry_seen

    # --- regions (outdoor) ---------------------------------------------------
    area_of = RG.assign_outdoor(ir, table)
    missing = [n for n, a in area_of.items() if a is None]
    if missing:
        raise SystemExit("regions.toml leaves outdoor screens unassigned: %s" % missing)
    region_of = {n: a["region"] for n, a in area_of.items()}

    # --- interiors -----------------------------------------------------------
    sets, links = I.interior_sets(ir, crossings, warps, swarps, reached)
    interiors = I.describe(ir, sets, warps, swarps, region_of, table, scripts)
    w.interiors = interiors
    region_names = {a["region"]: a["name"] for a in table["area"]}

    # --- per-screen table ----------------------------------------------------
    rows = []
    screen_kind, screen_sheet = {}, {}
    int_of = {n: it for it in interiors for n in it["screen_numbers"]}
    same_region_links = Counter()
    for c in crossings:
        if c["reached"] and region_of.get(c["a"]) and region_of.get(c["a"]) == region_of.get(c["b"]):
            same_region_links[c["a"]] += 1
            same_region_links[c["b"]] += 1
    for n in ir.used:
        s = ir.screens[n]
        ev = RG.screen_evidence(ir, scripts, n)
        sc = comps[n]
        land = [k for k in range(1, sc.count + 1) if sc.terrain_class(k) not in G.BARRIER]
        rk = [k for k in land if (n, k) in reached]
        main_k = max(rk or land or [0], key=lambda k: sc.area[k] if k else 0)
        grp = node_id(*group_of[(n, main_k)]) if main_k else None
        if s["indoor"]:
            it = int_of[n]
            region = it["region"] or "unattached_interiors"
            kind = it["kind"]
            sub = it["name"]
            sheet = "interior:" + it["id"]
            pos = ["interior set %s" % it["id"]]
            if it["has_outdoor_entrance"]:
                pos.append("door from " + ",".join(e["from"] for e in it["entrances"]
                                                   if e["outdoor"] and isinstance(e["from"], str)))
            neg = [] if it["region"] else ["no outdoor door or exit"]
            conf = "high" if it["has_outdoor_entrance"] else ("medium" if it["region"] else "low")
            rname = region_names.get(region, region.replace("_", " ").title())
        else:
            a = area_of[n]
            region, kind, sub, sheet, rname = a["region"], a["kind"], a["sub_area"], a["sheet"], a["name"]
            conf, pos, neg = RG.judge(a, ev, table["area"])
            if not pos and not neg:
                if same_region_links[n]:
                    pos = ["walk-linked to %d same-region crossing(s)" % same_region_links[n]]
                    conf = "medium"
                elif not rk:
                    pos = ["table cell only; no reached walkable space"]
                    conf = "medium" if kind == "sea" else "low"
                else:
                    pos = ["table cell only"]
                    conf = "low"
        screen_kind[n] = kind
        screen_sheet[n] = sheet
        c_, r_ = col_row(n)
        land_px = sum(int(sc.group_px[k][0]) for k in range(1, sc.count + 1))
        vstates = vision_states(ir, scripts, n)
        rows.append({
            "screen": n, "id": screen_id(n), "col": c_, "row": r_, "indoor": bool(s["indoor"]),
            "region": region, "region_name": rname, "sub_area": sub, "kind": kind, "sheet": sheet,
            "music": s["music"]["raw"], "prefixes": ev["prefixes"], "signs": ev["signs"],
            "walk_group": grp, "reached": bool(rk),
            "reach_level": ("design" if rk else "engine_dry" if any((n, k) in dry_seen for k in range(1, sc.count + 1))
                            else "engine_wading" if any((n, k) in engine_seen for k in range(1, sc.count + 1)) else "none"),
            "reached_without_script_warps": any((n, k) in reached_sprite_only for k in rk),
            "evidence": pos, "contradictions": neg, "confidence": conf,
            "land_fraction": round(_land_fraction(ir, n), 3), "vision_states": vstates,
        })
    w.naming_warnings = RG.state_name_warnings(rows)
    for msg in w.naming_warnings:
        log("naming warning: " + msg)
    w.rows = rows
    w.screen_kind, w.screen_sheet = screen_kind, screen_sheet
    log("regions: %d screens, %d regions, %d interior sets" % (
        len(rows), len({r["region"] for r in rows}), len(interiors)))

    # --- layout --------------------------------------------------------------
    reached_screens = {n for n, _ in reached} | {n for n, _ in engine_seen}   # never park a screen the engine reaches
    try:
        L = LY.build(ir, table, screen_kind, screen_sheet, interiors, reached=reached_screens)
    except LY.LayoutError as e:
        raise SystemExit("layout: %s" % e)
    w.layout = L
    for n in L.displaced:
        screen_sheet[n] = L.sheet_of[n]
        for r in rows:
            if r["screen"] == n:
                r["sheet"] = L.sheet_of[n]
    if L.displaced:
        log("layout: parked %d unreached screen(s) overlapping reached ones on the %s sheet: %s" % (
            len(L.displaced), LY.PARK_SHEET, ", ".join(screen_id(n) for n in sorted(L.displaced))))
    bad = [n for n in ir.used if not L.is_convex(n)]
    if bad:
        raise SystemExit("layout produced non-convex screens %s; reduce scale contrast or stretch" % bad)
    seams = []
    for c in crossings:
        if c["walkable"] and screen_sheet[c["a"]] != screen_sheet[c["b"]]:
            seams.append(c)
    w.seams = seams
    log("layout: %d sheets, %d walkable crossings cut between sheets (%d reached)" % (
        len(set(screen_sheet.values())), len(seams), sum(1 for c in seams if c["reached"])))
    w.elapsed = time.time() - t0
    return w


def _land_fraction(ir, n):
    from .connectivity import tile_group
    tc = ir.tile_classes
    g = [tile_group(tc.get(t["num"])) for t in ir.screens[n]["tiles"]]
    return sum(1 for x in g if x == "land") / len(g)


# ---------------------------------------------------------------------------
def write_all(w, out, dinkc_dir=None, log=print):
    os.makedirs(out, exist_ok=True)
    ir, comps, L = w.ir, w.comps, w.layout
    lay = w.table["layout"]
    rows_by = {r["screen"]: r for r in w.rows}

    # connectivity.json
    groups = defaultdict(list)
    for node in w.reached:
        groups[w.group_of[node]].append(node)
    entered = defaultdict(list)
    for wp in w.warps:
        if wp.get("dst_comp"):
            g = w.group_of[(wp["dst_screen"], wp["dst_comp"])]
            if not any(w.group_of.get((wp["src_screen"], k)) == g for k in wp["src_comps"]):
                entered[g].append(wp["id"])
    for wp in w.swarps:
        if wp.get("dst_comp"):
            entered[w.group_of[(wp["dst_screen"], wp["dst_comp"])]].append(wp["id"])
    start_group = w.group_of[w.start]
    walk_groups = []
    for g, nodes in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        scr = sorted({n for n, _ in nodes})
        sprite_ok = any(nd in w.reached_sprite_only for nd in nodes)
        walk_groups.append({
            "id": node_id(*g), "screens": [screen_id(n) for n in scr], "screen_count": len(scr),
            "components": len(nodes), "area_px": int(sum(comps[n].area[k] for n, k in nodes)),
            "contains_start": g == start_group, "entered_by": sorted(set(entered.get(g, []))),
            "warp_only": g != start_group, "reached_without_script_warps": sprite_ok,
            "regions": sorted({rows_by[n]["region"] for n in scr}),
        })
    # pockets: unreached land, grouped by walk group
    pocket_groups = defaultdict(list)
    for n, sc in comps.items():
        for k in range(1, sc.count + 1):
            if (n, k) in w.reached or sc.terrain_class(k) != "land":
                continue
            pocket_groups[w.group_of[(n, k)]].append((n, k))
    pockets = []
    small = 0
    for g, nodes in pocket_groups.items():
        area = int(sum(comps[n].area[k] for n, k in nodes))
        if area < lay["min_pocket_px"]:
            small += 1
            continue
        scr = sorted({n for n, _ in nodes})
        # scripted / pickup placements standing in the pocket
        inside = []
        for n, k in nodes:
            lab = comps[n].labels
            for p in ir.screens[n]["placements"]:
                x, y = p["map_x"], p["map_y"]
                if 0 <= x < W and 0 <= y < H and lab[y, x] == k and (p["has_script"] or p["is_warp"]):
                    inside.append("%s:%s" % (p["id"], p["script"] or "warp"))
        cls = Counter(comps[n].terrain_class(k) for n, k in nodes).most_common(1)[0][0]
        pockets.append({"id": node_id(*g), "screens": [screen_id(n) for n in scr], "area_px": area,
                        "class": cls, "regions": sorted({rows_by[n]["region"] for n in scr}),
                        "scripted_placements": sorted(inside)[:20],
                        "kind": "secret_candidate" if inside else "dead_space"})
    pockets.sort(key=lambda p: -p["area_px"])
    for c in comps.values():
        c.drop_image()
    leaks = [c for c in w.crossings if not c["walkable"] and
             ((c["a_class"] == "land") != (c["b_class"] == "land")) and
             ((c["a"], c["a_comp"]) in w.reached or (c["b"], c["b_comp"]) in w.reached)]
    screen_links = []
    for (a, b), cs in sorted(_by_pair(w.crossings).items()):
        wk = [c for c in cs if c["walkable"]]
        screen_links.append({"a": screen_id(a), "b": screen_id(b), "dir": cs[0]["dir"],
                             "walkable": bool(wk), "reached": any(c["reached"] for c in wk),
                             "walkable_px": sum(c["length"] for c in wk),
                             "needs_obstacle_removal": bool(wk) and all(c["needs_obstacle_removal"] for c in wk),
                             "vision_dependent": any(not c["open_all_visions"] for c in wk)})
    grid_nonlinks = []
    for n in ir.used:
        c, r = col_row(n)
        for m, d in ((n + 1, "right"), (n + 32, "down")):
            if m in ir.screens and ((d == "right" and c < 31) or d == "down"):
                if not any(x["walkable"] for x in _by_pair(w.crossings).get((n, m), [])):
                    grid_nonlinks.append([screen_id(n), screen_id(m)])
    comp_rows = {}
    for n, sc in comps.items():
        lst = []
        for k in range(1, sc.count + 1):
            if sc.area[k] < 50:
                continue
            cx, cy = sc.centroid(k)
            lst.append({"k": k, "area_px": int(sc.area[k]), "class": sc.terrain_class(k),
                        "water_kind": w_kind if (w_kind := _wk(w, n, k)) else None,
                        "bbox": [int(v) for v in sc.bbox[k]], "centroid": [round(cx, 1), round(cy, 1)],
                        "reached": (n, k) in w.reached, "walk_group": node_id(*w.group_of[(n, k)]),
                        "split_by_obstacles": sc.split_by_obstacles.get(k, 1)})
        comp_rows[screen_id(n)] = lst
    conn = {
        "schema": SCHEMA + "/connectivity",
        "rules": {"walkable": "hardness code 0; codes 1, 2 (low), 3, 100, 200 block",
                  "permissive_mask": "walkable in any vision variant, with removable sprite hardboxes cleared",
                  "removable_hardboxes": "scripts that die / redraw or clear their own hardness / deactivate, "
                                         "or a map brain other than 0 and 15",
                  "crossing": "walkable on both sides of the shared edge, pixel for pixel, run >= %d px" % lay["min_crossing_px"],
                  "player_space": "components whose terrain class is not water, canopy or void (tools/data/tile_classes.csv)",
                  "start": lay["start"]},
        "counts": {"screens": len(comps), "components": sum(c.count for c in comps.values()),
                   "crossings": len(w.crossings), "walkable_crossings": sum(c["walkable"] for c in w.crossings),
                   "reached_components": len(w.reached), "reached_screens": len({n for n, _ in w.reached}),
                   "unreached_used_screens": len(set(ir.used) - {n for n, _ in w.reached}),
                   "walk_groups_reached": len(walk_groups), "pockets": len(pockets),
                   "pockets_below_threshold": small, "edge_leaks": len(leaks),
                   "removable_hardboxes": sum(len(v) for v in w.removable.values())},
        "start_component": node_id(*w.start),
        "walk_groups": walk_groups,
        "pockets": pockets,
        "unreached_screens": [screen_id(n) for n in sorted(set(ir.used) - {n for n, _ in w.reached})],
        "screen_links": screen_links,
        "grid_neighbours_not_walk_linked": grid_nonlinks,
        "crossings": [_crossing_json(c) for c in w.crossings],
        "wrap_crossings": [_crossing_json(c) for c in w.wraps],
        "edge_leaks": [_crossing_json(c) for c in leaks],
        "water_bodies": w.bodies,
        "components": comp_rows,
    }
    _dump(os.path.join(out, "connectivity.json"), conn)
    w.conn = conn

    # warps.json
    def wj(x):
        d = {k: v for k, v in x.items() if k not in ("src_comps",)}
        if "src_comps" in x:
            d["src_components"] = [node_id(x["src_screen"], k) for k in x["src_comps"]]
        d["dst_component"] = node_id(x["dst_screen"], x["dst_comp"]) if x.get("dst_comp") else None
        if x["source"] == "sprite":
            d["src_region"] = rows_by[x["src_screen"]]["region"]
        if x["dst_screen_exists"]:
            d["dst_region"] = rows_by[x["dst_screen"]]["region"]
        d["one_way"] = not x["has_return_warp"] and not _walk_back(w, x)
        return d
    _dump(os.path.join(out, "warps.json"), {
        "schema": SCHEMA + "/warps", "counts": {"sprite_warps": len(w.warps), "script_warps": len(w.swarps),
                                                "kinds": dict(Counter(x["kind"] for x in w.warps + w.swarps))},
        "notes": ["x/y and dst_x/dst_y are map pixels (placement x and warp_x minus the 20 px side bar).",
                  "anim_seq is parm_seq: the sequence the warp sprite plays before the fade (doors).",
                  "script warps come from a text scan for `&player_map = N;` (tools/dinkc has the full AST). "
                  "`triggers` says which engine procedure starts the warp (main = screen load, touch/push/talk = the "
                  "player, die/hit = combat); kind `cutscene` = no player-started trigger.",
                  "dst_valid = dst_screen_exists and dst_in_bounds (x 0..599, y 0..399). dst_engine says what the "
                  "engine does with the destination (in_range, off_screen_entrance, edge_crosses, edge_clamped); "
                  "dst_component is found from the clamped point."],
        "sprite_warps": [wj(x) for x in w.warps], "script_warps": [wj(x) for x in w.swarps]})

    # interiors.json
    _dump(os.path.join(out, "interiors.json"), {
        "schema": SCHEMA + "/interiors", "count": len(w.interiors),
        "indoor_screens": sum(len(i["screens"]) for i in w.interiors),
        "interiors": [{**{k: v for k, v in i.items() if k != "screen_numbers"},
                       "settlement": i["region"] if i["region"] in _settlement_regions(w) else None}
                      for i in w.interiors]})

    # regions.csv
    with open(os.path.join(out, "regions.csv"), "w", newline="", encoding="utf-8") as fh:
        cols = ["id", "screen", "col", "row", "indoor", "region", "region_name", "sub_area", "kind", "sheet",
                "confidence", "evidence", "contradictions", "prefixes", "music", "signs", "walk_group",
                "reached", "reach_level", "reached_without_script_warps", "land_fraction", "vision_states"]
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for r in w.rows:
            d = {k: r[k] for k in cols}
            for k in ("evidence", "contradictions", "prefixes", "signs"):
                d[k] = "; ".join(str(x) for x in r[k])
            d["indoor"] = int(r["indoor"]); d["reached"] = int(r["reached"])
            d["reached_without_script_warps"] = int(r["reached_without_script_warps"])
            wr.writerow(d)

    # world_layout.json + summary numbers
    summary = layout_summary(w)
    w.summary = summary
    base = lay["base_m_per_px"]
    scr_out = []
    for n in ir.used:
        P = L.corners[n]
        r = rows_by[n]
        tiles = []
        for t in ir.screens[n]["tiles"]:
            p = L.to_world(n, t["x"] + TILE / 2, t["y"] + TILE / 2)
            tiles.append([r4(p[0]), r4(p[1])])
        pls = []
        for p in ir.screens[n]["placements"]:
            q = L.to_world(n, p["map_x"], p["map_y"])
            s = L.local_scale(n, p["map_x"], p["map_y"])
            pls.append({"id": p["id"], "x": r4(q[0]), "y": r4(q[1]), "m_per_px": r4(s["m_per_px"]),
                        "scale_x": r4(s["x"]), "scale_y": r4(s["y"]), "rot_deg": r4(s["rot_deg"]),
                        "size_factor": r4(s["m_per_px"] / base)})
        sc = L.local_scale(n, W / 2, H / 2)
        scr_out.append({"id": screen_id(n), "screen": n, "sheet": L.sheet_of[n], "region": r["region"],
                        "kind": r["kind"], "displaced": L.displaced.get(n),
                        "corners": {"nw": [r4(P[0][0]), r4(P[0][1])], "ne": [r4(P[1][0]), r4(P[1][1])],
                                    "sw": [r4(P[2][0]), r4(P[2][1])], "se": [r4(P[3][0]), r4(P[3][1])]},
                        "center": [r4(v) for v in L.to_world(n, W / 2, H / 2)],
                        "m_per_px_center": r4(sc["m_per_px"]), "scale_factor_center": r4(sc["m_per_px"] / base),
                        "area_m2": round(L.quad_area(n), 2),
                        "tile_centers": tiles, "placements": pls})
    _dump(os.path.join(out, "world_layout.json"), {
        "schema": SCHEMA + "/world_layout",
        "transform": "bilinear per screen from corners nw, ne, sw, se: u=x/600, v=y/400 (map pixels, "
                     "placement x minus 20); P=(1-u)(1-v)nw+u(1-v)ne+(1-u)v sw+uv se. Metres, x east, y south.",
        "inverse": "Newton on the same map (analyse.layout.Layout.to_local); locate() finds the screen.",
        "base_m_per_px": base, "base_evidence": summary["base_evidence"],
        "scale": w.table["scale"], "sheet_shift_m": {k: [r4(v) for v in s] for k, s in L.sheet_shift.items()},
        "summary": summary, "screens": scr_out}, expand=0)

    # encounters.json / vision_variants.json
    _dump(os.path.join(out, "engine_reach.json"), EN.report(w))
    _dump(os.path.join(out, "encounters.json"), encounters(w, dinkc_dir))
    _dump(os.path.join(out, "vision_variants.json"), vision_variants(w))
    _dump(os.path.join(out, "summary.json"), {"schema": SCHEMA + "/summary", **summary,
                                              "connectivity_counts": conn["counts"],
                                              "seams_cut_between_sheets": [_crossing_json(c) for c in w.seams]})

    # pngs
    RD.render_connectivity(ir, comps, w.reached, w.group_of, w.comp_wkind, w.crossings, w.warps, w.swarps,
                           os.path.join(out, "connectivity.png"), lay["min_pocket_px"])
    for c in comps.values():
        c.drop_image()
    RD.render_regions(ir, w.rows, os.path.join(out, "regions.png"))
    RD.render_layout(ir, L, w.rows, summary, os.path.join(out, "layout_preview.png"))
    log("wrote %s" % ", ".join(sorted(os.listdir(out))))


def _wk(w, n, k):
    return w.comp_wkind.get((n, k))


def _by_pair(crossings):
    d = defaultdict(list)
    for c in crossings:
        d[(c["a"], c["b"])].append(c)
    return d


def _crossing_json(c):
    return {"a": screen_id(c["a"]), "b": screen_id(c["b"]), "dir": c["dir"],
            "a_component": node_id(c["a"], c["a_comp"]), "b_component": node_id(c["b"], c["b_comp"]),
            "axis": c["axis"], "from": c["from"], "to": c["to"], "length": c["length"],
            "a_class": c["a_class"], "b_class": c["b_class"], "walkable": c.get("walkable"),
            "reached": c.get("reached"), "open_vision0": c["open_vision0"],
            "open_all_visions": c["open_all_visions"], "needs_obstacle_removal": c["needs_obstacle_removal"]}


def _walk_back(w, x):
    """Can the player get back from a warp's destination to its source without it?"""
    if not x.get("dst_comp"):
        return False
    src = [(x["src_screen"], k) for k in x["src_comps"]] if x["source"] == "sprite" else \
        [(s, k) for s in x["src_screens"] for k in range(1, w.comps[s].count + 1)]
    start = (x["dst_screen"], x["dst_comp"])
    others = [y for y in w.warps if y is not x]
    sw = [y for y in w.swarps if y is not x]
    seen = G.reach(w.comps, w.crossings, others, sw, start)
    return any(s in seen for s in src)


def _settlement_regions(w):
    return {a["region"] for a in w.table["area"] if a["kind"] == "settlement"}


def layout_summary(w):
    ir, L, rows = w.ir, w.layout, w.rows
    lay = w.table["layout"]
    by = {r["screen"]: r for r in rows}
    area = lambda ns: sum(L.quad_area(n) for n in ns) / 1e6
    land = lambda ns: sum(L.quad_area(n) * by[n]["land_fraction"] for n in ns) / 1e6
    outdoor = [n for n in ir.used if not ir.indoor(n)]
    main = [n for n in outdoor if L.sheet_of[n] == "mainland"]
    main_land = [n for n in main if by[n]["land_fraction"] > 0.25 and by[n]["kind"] != "sea"]
    box = LY.bbox_of([p for n in main_land for p in L.corners[n]])
    sizes = {}
    for reg in sorted({r["region"] for r in rows if r["kind"] == "settlement"}):
        ns = [r["screen"] for r in rows if r["region"] == reg and r["kind"] == "settlement"]
        b = LY.bbox_of([p for n in ns for p in L.corners[n]])
        sizes[reg] = {"screens": len(ns), "width_m": round(b[2] - b[0], 1), "height_m": round(b[3] - b[1], 1),
                      "area_m2": round(area(ns) * 1e6, 0)}
    per_region = {}
    for reg in sorted({r["region"] for r in rows}):
        ns = [r["screen"] for r in rows if r["region"] == reg]
        per_region[reg] = {"screens": len(ns), "area_km2": round(area(ns), 4), "land_km2": round(land(ns), 4)}
    sheets = {}
    for s in sorted(set(L.sheet_of.values())):
        if s.startswith("interior:"):
            continue
        ns = [n for n in ir.used if L.sheet_of[n] == s]
        b = LY.bbox_of([p for n in ns for p in L.corners[n]])
        sheets[s] = {"screens": len(ns), "bbox_m": [round(v, 1) for v in b],
                     "shift_m": [round(v, 1) for v in L.sheet_shift[s]]}
    gaps = {}
    mb = sheets["mainland"]["bbox_m"]
    for s, v in sheets.items():
        if s != "mainland":
            gaps[s] = round(LY.rect_gap(np.array(v["bbox_m"]), np.array(mb)), 1)
    hero = [96, 97, 97, 96]
    return {
        "base_evidence": {"hero_idle_frame_px": hero, "hero_m": 1.8, "hero_m_per_px": round(1.8 / 96.5, 4),
                          "door_open_frame_px": 64, "door_m": 2.2, "door_m_per_px": round(2.2 / 64, 4),
                          "geometric_mean_m_per_px": round(((1.8 / 96.5) * (2.2 / 64)) ** 0.5, 4),
                          "chosen": lay["base_m_per_px"]},
        "screen_size_m": {k: [round(W * lay["base_m_per_px"] * v, 2), round(H * lay["base_m_per_px"] * v, 2)]
                          for k, v in w.table["scale"].items()},
        "area_km2": {"outdoor_total": round(area(outdoor), 4), "outdoor_land": round(land(outdoor), 4),
                     "mainland_total": round(area(main), 4), "mainland_land": round(land(main), 4),
                     "dressed_reached_land": round(land([n for n in outdoor if by[n]["reached"]]), 4),
                     "interiors": round(area([n for n in ir.used if ir.indoor(n)]), 5)},
        "mainland": {"width_m": round(box[2] - box[0], 1), "height_m": round(box[3] - box[1], 1),
                     "run_ew_s": round((box[2] - box[0]) / 6.0, 1), "run_ns_s": round((box[3] - box[1]) / 6.0, 1),
                     "run_diag_s": round(float(np.hypot(box[2] - box[0], box[3] - box[1])) / 6.0, 1)},
        "settlements": sizes, "regions": per_region, "sheets": sheets, "sheet_gap_to_mainland_m": gaps,
        "layout_overlaps": [{"area_m2": a, "a": screen_id(x), "b": screen_id(y)} for a, x, y in LY.overlaps(L.corners)],
        "displaced_screens": {screen_id(n): d for n, d in sorted(L.displaced.items())},
    }


def encounters(w, dinkc_dir):
    ir, scripts = w.ir, w.scripts
    placed = placed_scripts(ir)
    source = "text scan of bin/dink/story (provisional)"
    calls = {}
    path = os.path.join(dinkc_dir, "calls.csv") if dinkc_dir else None
    if path and os.path.exists(path):
        source = "tools/dinkc/out/calls.csv (parsed AST)"
        with open(path, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["name"] == "screenlock":
                    calls.setdefault(r["script"], []).append(
                        {"procedure": r["procedure"], "line": int(r["line"]), "arg": r["args"]})
    else:
        for s in scripts.screenlock_scripts():
            calls[s] = [{"procedure": None, "line": None, "arg": "1"}]
    by_screen = defaultdict(list)
    unplaced = []
    for s, cl in sorted(calls.items()):
        locks = any(c["arg"].strip() == "1" for c in cl)
        scr, how = script_screens(ir, scripts, s, placed)
        if not scr:
            unplaced.append(s)
        for n in scr:
            by_screen[n].append({"script": s, "how": how, "locks": locks, "calls": cl})
    out = []
    for n in sorted(by_screen):
        enemies = [p["id"] + ":" + (p["script"] or "brain%d" % p["brain"]) for p in ir.screens[n]["placements"]
                   if (p["script"] or "").startswith("en-") or p["brain"] in (9, 10) or
                   any(e["script"] == p["script"] for e in by_screen[n])]
        r = next(x for x in w.rows if x["screen"] == n)
        out.append({"screen": screen_id(n), "region": r["region"], "sub_area": r["sub_area"],
                    "scripts": by_screen[n], "locking": any(e["locks"] for e in by_screen[n]),
                    "enemy_placements": enemies,
                    "provisional": source.startswith("text") or all(e["how"] != "placed" for e in by_screen[n])})
    return {"schema": SCHEMA + "/encounters", "source": source,
            "screenlock_scripts": sorted(calls), "scripts_not_on_any_screen": unplaced,
            "screens": out, "count": len(out)}


def vision_setters(ir, scripts, n):
    """{script: {"values": [...], "how": ...}} for every script that can run while screen n is loaded
    and gives `&vision` a value (`&vision = N` or `force_vision(N)`).

    The engine zeroes `&vision` in load_map and draws a screen with the placements of the current
    vision, so only a script that runs on that screen counts: the screen's base, random and load
    scripts, the scripts of its placements, and everything they start (`spawn`, `external`,
    `sp_script`), transitively. A script elsewhere cannot set it for this screen (a script that
    outlives a screen change and sets `&vision` later does not exist in the shipped data: every
    assigning script is on a screen's own script list)."""
    running = scripts.running_with(ir.scripts_on(n))
    out = {}
    for s, how in running.items():
        vals = scripts.vision_values(s)
        if vals:
            out[s] = {"values": vals, "how": how}
    return out


def vision_states(ir, scripts, n):
    """Text for regions.csv: the vision variants of a screen, e.g. '1: 13 placements (s1-h1-s); 2: 6
    placements (s1-h1-s)'. Vision 0 is the screen's normal state and the one its name describes."""
    gated = defaultdict(int)
    for p in ir.screens[n]["placements"]:
        if p["vision"]:
            gated[p["vision"]] += 1
    if not gated:
        return ""
    found = vision_setters(ir, scripts, n)
    parts = []
    for v in sorted(gated):
        who = sorted(s for s, d in found.items() if v in d["values"])
        parts.append("%d: %d placements (%s)" % (v, gated[v], ",".join(who) if who else "never set"))
    return "; ".join(parts)


def vision_variants(w):
    ir, scripts = w.ir, w.scripts
    out = []
    never = []
    for n in ir.used:
        gated = [p for p in ir.screens[n]["placements"] if p["vision"]]
        if not gated:
            continue
        sets = defaultdict(list)
        for p in gated:
            sets[p["vision"]].append({"id": p["id"], "seq": p["seq"], "frame": p["frame"], "kind": p["kind"],
                                      "script": p["script"] or None, "has_hardness": p["has_hardness"],
                                      "is_warp": p["is_warp"]})
        found = vision_setters(ir, scripts, n)
        setters = {s: d["values"] for s, d in sorted(found.items())}
        set_by = {str(v): sorted(s for s, d in found.items() if v in d["values"]) for v in sorted(sets)}
        unset = [int(v) for v, who in set_by.items() if not who]
        affected = [_crossing_json(c) for c in w.crossings
                    if n in (c["a"], c["b"]) and c["walkable"] and not c["open_all_visions"]]
        r = next(x for x in w.rows if x["screen"] == n)
        rec = {"screen": screen_id(n), "region": r["region"], "base_script": ir.screens[n]["base_script"],
               "visions": {str(v): sets[v] for v in sorted(sets)}, "vision_setting_scripts": setters,
               "vision_setter_reached_by": {s: d["how"] for s, d in sorted(found.items())},
               "vision_set_by": set_by, "visions_never_set": unset,
               "hardness_variants": ir.screens[n]["hardness"].get("vision_variants", {}),
               "crossings_closed_in_some_vision": affected}
        if unset:
            never.append((screen_id(n), unset))
        out.append(rec)
    return {"schema": SCHEMA + "/vision_variants",
            "notes": ["vision_setting_scripts: scripts that run while the screen is loaded (base/random/load script, "
                      "placement scripts, and every script they spawn, call with external or attach with sp_script, "
                      "transitively) and assign &vision or call force_vision.",
                      "visions_never_set: gated placements whose vision value no such script assigns; the engine "
                      "resets &vision to 0 on every screen load, so these placements are never drawn in the shipped game."],
            "screens": out, "screen_count": len(out),
            "placement_count": sum(len(v) for s in out for v in s["visions"].values()),
            "screens_with_unset_visions": len(never),
            "never_set": [{"screen": sid, "visions": v} for sid, v in never]}


def _dump(path, obj, expand=1):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1 if expand else None, ensure_ascii=False, default=_default)
        fh.write("\n")


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))
