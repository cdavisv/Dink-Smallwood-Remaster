"""Group indoor screens into interior sets and attach them to outdoor doors."""

from collections import Counter

from .connectivity import UnionFind
from .graph import walkable_crossing
from .ir import screen_id
from .warps import dominant_floor


def interior_sets(ir, crossings, warps, swarps, reached=None):
    """Indoor screens joined by reached walkable crossings or indoor-to-indoor warps.
    Unreached components (the void around a room, cave rock) never join rooms."""
    indoor = [n for n in ir.used if ir.indoor(n)]
    uf = UnionFind()
    for n in indoor:
        uf.find(n)
    links = []
    for c in crossings:
        if ir.indoor(c["a"]) and ir.indoor(c["b"]) and walkable_crossing(c) and \
                (reached is None or (c["a"], c["a_comp"]) in reached):
            uf.union(c["a"], c["b"])
            links.append(("walk", c["a"], c["b"]))
    for w in warps:
        if w["dst_screen_exists"] and ir.indoor(w["src_screen"]) and ir.indoor(w["dst_screen"]):
            uf.union(w["src_screen"], w["dst_screen"])
            links.append(("warp", w["src_screen"], w["dst_screen"]))
    groups = {}
    for n in indoor:
        groups.setdefault(uf.find(n), []).append(n)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: g[0]), links


def describe(ir, sets, warps, swarps, region_of, table, scripts):
    out = []
    names = table.get("interior", [])
    for i, screens in enumerate(sets):
        sset = set(screens)
        entrances, exits = [], []
        for w in warps:
            if not w["dst_screen_exists"]:
                continue
            if w["dst_screen"] in sset and w["src_screen"] not in sset:
                entrances.append({"warp": w["id"], "from": screen_id(w["src_screen"]), "kind": w["kind"],
                                  "outdoor": not ir.indoor(w["src_screen"])})
            if w["src_screen"] in sset and w["dst_screen"] not in sset:
                exits.append({"warp": w["id"], "to": screen_id(w["dst_screen"]), "kind": w["kind"],
                              "outdoor": not ir.indoor(w["dst_screen"])})
        for w in swarps:
            if not w["dst_screen_exists"]:
                continue
            if w["dst_screen"] in sset and not (set(w["src_screens"]) & sset):
                entrances.append({"warp": w["id"], "from": [screen_id(s) for s in w["src_screens"]],
                                  "kind": w["kind"], "outdoor": all(not ir.indoor(s) for s in w["src_screens"]) and bool(w["src_screens"])})
            if set(w["src_screens"]) & sset and w["dst_screen"] not in sset:
                exits.append({"warp": w["id"], "to": screen_id(w["dst_screen"]), "kind": w["kind"],
                              "outdoor": not ir.indoor(w["dst_screen"])})
        # settlement / region: outdoor screens of door entrances first, else exits
        votes = Counter()
        for e in entrances:
            if e["outdoor"] and isinstance(e["from"], str):
                votes[region_of.get(int(e["from"][4:]))] += 2
        for e in exits:
            if e["outdoor"]:
                votes[region_of.get(int(e["to"][4:]))] += 1
        votes.pop(None, None)
        region = votes.most_common(1)[0][0] if votes else None
        floors = Counter(dominant_floor(ir, n) for n in screens)
        floor = floors.most_common(1)[0][0]
        base = sorted({ir.screens[n]["base_script"] for n in screens if ir.screens[n]["base_script"]})
        rec = {"id": "INT_%03d" % screens[0], "screens": [screen_id(n) for n in screens],
               "screen_numbers": screens, "rooms": len(screens), "entrances": entrances, "exits": exits,
               "region": region, "floor": floor, "base_scripts": base,
               "has_outdoor_entrance": any(e["outdoor"] for e in entrances),
               "name": None, "kind": None}
        for ent in names:
            if sset & set(ent["screens"]):
                rec["name"] = ent.get("name")
                rec["kind"] = ent.get("kind")
                if ent.get("region"):
                    rec["region"] = ent["region"]
        if rec["kind"] is None:
            rec["kind"] = "dungeon" if floor == "cave_floor" or len(screens) >= 4 else "interior"
        if rec["name"] is None:
            tag = ", ".join(base) if base else "no base script"
            rec["name"] = "%s room%s (%s)" % (len(screens), "s" if len(screens) > 1 else "", tag)
        out.append(rec)
    return out
