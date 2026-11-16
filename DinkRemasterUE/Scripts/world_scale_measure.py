#!/usr/bin/env python3
"""World-scale measurements (doc/remaster/WORLD_SCALE.md): two export bundles, one per layout scale, compared.

  python3 -I Scripts/world_scale_measure.py --old <bundle dir at the old scale> --new <bundle dir at the new scale>
         [--families Content/Dink/Data/Art/families.json] [--mesh-bounds <json: mesh path -> [x, y, z] cm>] [--md out.md]

What it prints (Markdown):
  1. per screen kind: metres per pixel (centre of the screens, median), screen size, run/walk seconds across a screen;
  2. per object group and kind: the 1997 picture (card) at layout scale, the 1997 hardbox in metres, and what draws the
     object today (the family mesh's real size when --mesh-bounds is given), old and new scale;
  3. invariants that must hold: collision rectangles (pixels), ground and mask images, warps in pixels identical.
Offline: reads JSON only. No Unreal.
"""
import argparse, collections, json, math, os, statistics, sys, hashlib

GROUPS = [
    ("cottage / house", lambda c, k: c.startswith(("cottage_thatched", "island_hut", "log_cabin")) or c == "church"),
    ("town wall bay (house front)", lambda c, k: c.startswith("town_wall_stone")),
    ("door", lambda c, k: c in ("door_wood_single", "door_wood_wide", "cottage_door")),
    ("tree (pine/oak/willow)", lambda c, k: c in ("tree_pine_large", "tree_oak_large", "tree_willow_large", "tree_willow")),
    ("bush", lambda c, k: c in ("bush_small", "bush_round_medium", "bush_round_large", "bush_wide")),
    ("boulder", lambda c, k: c.startswith("boulder_")),
    ("fence", lambda c, k: c.startswith("fence_rail")),
    ("chest", lambda c, k: c.startswith("chest_")),
    ("barrel", lambda c, k: c == "barrel"),
    ("crate", lambda c, k: c in ("crate", "crate_small", "crate_stack")),
    ("sign post", lambda c, k: c == "sign_post"),
    ("bed / table / counter", lambda c, k: c in ("bed", "table_long", "table_round", "counter_wood")),
    ("interior / dungeon wall", lambda c, k: k == "interior_wall"),
    ("NPC (humans)", lambda c, k: k == "npc" and not c.startswith(("corpse", "dink_dead"))),
    ("pillbug / slime / bonca", lambda c, k: k == "enemy" and c.startswith(("pillbug", "slime", "bonca"))),
    ("dragon / stone giant", lambda c, k: k == "enemy" and c.startswith(("dragon", "stone_giant"))),
    ("duck / pig", lambda c, k: c in ("duck", "pig")),
]
KINDS = ["settlement", "wilderness", "sea", "dungeon", "interior"]
SCREEN_PX = (600, 400)
RUN_CM_S, WALK_CM_S = 600.0, 170.0


def load(d, name):
    with open(os.path.join(d, name), encoding="utf-8") as f:
        return json.load(f)


def med(v):
    return statistics.median(v) if v else float("nan")


def fmt(x, n=1):
    return "-" if x != x else f"{x:.{n}f}"


def file_md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--families", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Content/Dink/Data/Art/families.json"))
    ap.add_argument("--mesh-bounds", default="")
    ap.add_argument("--pace", default="", help="hero_pace.json of the new scale (run factor per kind)")
    ap.add_argument("--md", default="")
    a = ap.parse_args(argv)

    out = []
    p = out.append
    scr = {v: {s["screen"]: s for s in load(getattr(a, v), "screens.json")["screens"]} for v in ("old", "new")}
    pls = {v: {q["id"]: q for q in load(getattr(a, v), "placements.json")["placements"]} for v in ("old", "new")}
    fam = {r["family"]: r for r in json.load(open(a.families, encoding="utf-8"))["families"]}
    bounds = json.load(open(a.mesh_bounds)) if a.mesh_bounds else {}
    pace_doc = json.load(open(a.pace)) if a.pace else {}
    pace = pace_doc.get("run", {})
    pace_screens = pace_doc.get("screens", {})

    # 1. per kind
    p("### Screens per kind (centre metres per pixel, median over the kind's screens)\n")
    p("| kind | screens | cm/px old -> new | screen old (m) | screen new (m) | ratio | run E-W old -> new (s) | walk E-W old -> new (s) |")
    p("|---|---|---|---|---|---|---|---|")
    ratio_by_kind = {}
    for k in KINDS:
        ids = [n for n, s in scr["old"].items() if s["kind"] == k]
        if not ids:
            continue
        o = med([100 * scr["old"][n]["m_per_px_center"] for n in ids])
        nw = med([100 * scr["new"][n]["m_per_px_center"] for n in ids])
        r = med([scr["new"][n]["m_per_px_center"] / scr["old"][n]["m_per_px_center"] for n in ids])
        ratio_by_kind[k] = r
        # run seconds across the screen: per screen (its own pace factor), median over the kind
        run_new_s = med([SCREEN_PX[0] * 100 * scr["new"][n]["m_per_px_center"] / (RUN_CM_S * float(pace_screens.get(str(n), pace.get(k, 1.0)))) for n in ids])
        run_old_s = med([SCREEN_PX[0] * 100 * scr["old"][n]["m_per_px_center"] / RUN_CM_S for n in ids])
        p(f"| {k} | {len(ids)} | {o:.3f} -> {nw:.3f} | {SCREEN_PX[0]*o/100:.1f} x {SCREEN_PX[1]*o/100:.1f} | "
          f"{SCREEN_PX[0]*nw/100:.1f} x {SCREEN_PX[1]*nw/100:.1f} | {r:.3f} | {run_old_s:.1f} -> {run_new_s:.1f} | "
          f"{SCREEN_PX[0]*o/WALK_CM_S:.1f} -> {SCREEN_PX[0]*nw/WALK_CM_S:.1f} |")
    rs = [scr["new"][n]["m_per_px_center"] / scr["old"][n]["m_per_px_center"] for n in scr["old"]]
    p(f"\nPer-screen ratio new/old: min {min(rs):.3f}, median {med(rs):.3f}, max {max(rs):.3f} (rubber-sheet screens between kinds lie between the kind ratios).\n")

    # 2. per group
    p("### Objects: 1997 picture and hardbox at layout scale, and what draws them (medians)\n")
    p("Card = the 1997 picture at the placement's scale (`card.width_m x height_m`; npc/enemy/animal/pickup/effect cards use the base 0.025 m/px "
      "and do not follow the layout). Box = the 1997 hardbox (x by y extent) at the placement's scale. Mesh = the bound family mesh's bounds "
      "(real size, `fit: none`), when known.\n")
    p("| group | kind | n | card old (m) | card new (m) | box old (m) | box new (m) | drawn by | mesh (m) |")
    p("|---|---|---|---|---|---|---|---|---|")
    for gname, pred in GROUPS:
        rows = collections.defaultdict(list)
        for pid, q in pls["old"].items():
            if pred(q["class_id"], q["category"]):
                rows[scr["old"][q["screen"]]["kind"]].append(pid)
        for k in KINDS:
            ids = rows.get(k)
            if not ids:
                continue
            def card(v, f):
                vals = [pls[v][i]["card"][f] for i in ids if pls[v][i].get("card")]
                return med(vals)
            def box(v, axis):
                vals = []
                for i in ids:
                    q = pls[v][i]
                    h = q.get("hardness")
                    if h and h.get("rect"):
                        x0, y0, x1, y1 = h["rect"]
                        vals.append((x1 - x0 if axis == 0 else y1 - y0) * (q["scale_x"] if axis == 0 else q["scale_y"]))
                return med(vals)
            modes = collections.Counter(pls["old"][i].get("card", {}).get("scale_mode", "-") for i in ids if pls["old"][i].get("card"))
            cls = collections.Counter(pls["old"][i]["class_id"] for i in ids)
            frow = None
            for c, _ in cls.most_common():
                if c in fam:
                    frow = fam[c]
                    break
            drawn = "card (%s)" % "/".join(sorted(modes)) if frow is None else "mesh fit %s%s" % (frow.get("fit", "none"), " span " + frow["span"] if frow.get("span") else "")
            mesh = "-"
            if frow is not None and frow.get("mesh") in bounds:
                b = bounds[frow["mesh"]]
                mesh = f"{b[0]/100:.1f} x {b[1]/100:.1f} x {b[2]/100:.1f}"
            p(f"| {gname} | {k} | {len(ids)} | {fmt(card('old','width_m'))} x {fmt(card('old','height_m'))} | {fmt(card('new','width_m'))} x {fmt(card('new','height_m'))} | "
              f"{fmt(box('old',0))} x {fmt(box('old',1))} | {fmt(box('new',0))} x {fmt(box('new',1))} | {drawn} | {mesh} |")

    # 3. invariants
    p("\n### Invariants (pixels): must be identical\n")
    for name in ("collision.json", "warps.json", "sprites.json"):
        same = file_md5(os.path.join(a.old, name)) == file_md5(os.path.join(a.new, name))
        if name == "warps.json" and not same:
            wo = [{k: v for k, v in w.items() if k not in ("world", "dest_world", "hash", "src_world", "dst_world", "trigger_quad")} for w in load(a.old, name)["warps"]]
            wn = [{k: v for k, v in w.items() if k not in ("world", "dest_world", "hash", "src_world", "dst_world", "trigger_quad")} for w in load(a.new, name)["warps"]]
            p(f"- {name}: world positions differ (expected), pixel fields {'identical' if wo == wn else 'DIFFER'}")
        else:
            p(f"- {name}: {'identical' if same else 'DIFFERENT'}")
    for d in ("ground", "ground_mask"):
        do, dn = os.path.join(a.old, d), os.path.join(a.new, d)
        fo, fn = sorted(os.listdir(do)), sorted(os.listdir(dn))
        diff = [f for f in fo if f not in fn or file_md5(os.path.join(do, f)) != file_md5(os.path.join(dn, f))]
        p(f"- {d}/: {len(fo)} images, {len(diff)} differ")
    keys = ("map_x", "map_y", "seq", "frame", "type", "hardness", "script", "vision", "brain", "is_warp")
    pd = [i for i in pls["old"] if any(pls["old"][i].get(k) != pls["new"].get(i, {}).get(k) for k in keys)]
    p(f"- placements: {len(pls['old'])} old, {len(pls['new'])} new; pixel fields ({', '.join(keys)}) differ on {len(pd)}")
    text = "\n".join(out) + "\n"
    if a.md:
        open(a.md, "w", encoding="utf-8").write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
