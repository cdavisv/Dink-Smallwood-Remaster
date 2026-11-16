#!/usr/bin/env python3
"""Move hand-authored screen dressing to a new layout scale (doc/remaster/WORLD_SCALE.md).

  python3 -I Scripts/world_scale_convert_art.py --old <bundle at the old scale> --new <bundle at the new scale> [--write]

The dink-art/1 manifests in Content/Dink/Data/Art that hold ABSOLUTE positions (`world_cm` of elements, lights,
warp_overrides, postprocess; stonebrook.json, stonebrook_exterior.json, pigpen.json, stonebrook_fields_438/471.json and
the render-only context of screen 1: vista, perimeter skirt, underfloor) were laid out on their screen at the old
metres per pixel. Every position goes through the 1997 pixel it stood on: old corners -> map pixel (inverse bilinear,
Newton) -> new corners. So everything keeps its place relative to the 1997 hardness, the warps and the other dressing.

Size rule (WORLD_SCALE.md, "per-family size rule"):
  - SPACE pieces: the floor, walls, windows, doorways, roofs, ground and field tiles, banks, paths, the vista ground,
    the skirt and underfloor, the split-rail fence runs and the authored cottage of 439. They are the room, the ground or
    a run that must close against the 1997 hardness; on authored-collision screens they ARE Dink's collision. Their X/Y
    scale is multiplied by the local linear ratio of the two layouts (new / old metres per pixel at that point), so they
    still meet and still close every passage exactly as before. Their height (Z scale) is kept, except for the authored
    cottage of 439 (its own collision, with a camera portal that needs a uniform scale): it grows as a whole.
  - OBJECTS: furniture, barrels, candles, baskets, chimneys, boulders, trees, grass clumps, feed: real size, moved only.
Postprocess volumes grow in X/Y with the ratio (they cover the room); light radii and warp trigger extents are kept.
Without --write it prints what would change. The mesh `offset_cm` of `replacements` are relative to their origin
placement and stay.
"""
import argparse, json, math, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SPACE = ("SM_Floor_", "SM_Wall_", "SM_Window_", "SM_Doorway_", "SM_IndoorRoof_", "SM_Ground_", "SM_Fields_",
         "SM_Path_", "SM_VistaGround_", "SM_Stonebrook_PerimeterSkirt", "SM_Underfloor_", "SM_Fence_SplitRail")
UNIFORM = ("SM_Cottage_Stonebrook",)


def bilinear(c, u, v):
    nw, ne, sw, se = c["nw"], c["ne"], c["sw"], c["se"]
    return [(1 - u) * (1 - v) * nw[i] + u * (1 - v) * ne[i] + (1 - u) * v * sw[i] + u * v * se[i] for i in (0, 1)]


def jac(c, u, v):
    nw, ne, sw, se = c["nw"], c["ne"], c["sw"], c["se"]
    du = [(1 - v) * (ne[i] - nw[i]) + v * (se[i] - sw[i]) for i in (0, 1)]
    dv = [(1 - u) * (sw[i] - nw[i]) + u * (se[i] - ne[i]) for i in (0, 1)]
    return du, dv


def inverse(c, x, y):
    u, v = 0.5, 0.5
    for _ in range(40):
        p = bilinear(c, u, v)
        du, dv = jac(c, u, v)
        det = du[0] * dv[1] - du[1] * dv[0]
        ex, ey = x - p[0], y - p[1]
        su = (ex * dv[1] - ey * dv[0]) / det
        sv = (du[0] * ey - du[1] * ex) / det
        u, v = u + su, v + sv
        if abs(su) < 1e-12 and abs(sv) < 1e-12:
            break
    return u, v


def linear_ratio(co, cn, u, v):
    def area(c):
        du, dv = jac(c, u, v)
        return abs(du[0] * dv[1] - du[1] * dv[0])
    return math.sqrt(area(cn) / area(co))


def convert_point(co, cn, world_cm):
    u, v = inverse(co, world_cm[0] / 100.0, world_cm[1] / 100.0)
    x, y = bilinear(cn, u, v)
    return [x * 100.0, y * 100.0] + list(world_cm[2:]), linear_ratio(co, cn, u, v), (u * 600.0, v * 400.0)


def is_space(mesh):
    name = mesh.rsplit("/", 1)[-1]
    return name.startswith(SPACE)


def convert_manifest(d, old_sc, new_sc, report):
    screen = d.get("screen")
    co, cn = old_sc[screen]["corners"], new_sc[screen]["corners"]
    if co == cn:
        return False
    for e in d.get("elements", []):
        if "world_cm" not in e:
            continue
        e["world_cm"], r, px = convert_point(co, cn, e["world_cm"])
        if e.get("mesh", "").rsplit("/", 1)[-1].startswith(UNIFORM):
            # one authored building that is its own collision and carries a camera portal (camera_exteriors.json,
            # DinkCameraPortal::Limit needs a uniform scale): it grows as a whole, its door stays on its warp
            e["scale"] = [v * r for v in e.get("scale", [1, 1, 1])]
            report["space"] += 1
        elif is_space(e.get("mesh", "")):
            sc = list(e.get("scale", [1, 1, 1]))
            e["scale"] = [sc[0] * r, sc[1] * r] + sc[2:]
            report["space"] += 1
        else:
            report["object"] += 1
        report["ratio"].append(r)
    for key in ("lights", "warp_overrides"):
        for e in d.get(key, []):
            e["world_cm"], r, _ = convert_point(co, cn, e["world_cm"])
            report[key] += 1
    pp = d.get("postprocess")
    for e in (pp if isinstance(pp, list) else [pp] if isinstance(pp, dict) else []):
        e["world_cm"], r, _ = convert_point(co, cn, e["world_cm"])
        if "extent_cm" in e:
            e["extent_cm"] = [e["extent_cm"][0] * r, e["extent_cm"][1] * r] + list(e["extent_cm"][2:])
        report["postprocess"] += 1
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--project", default=str(PROJECT))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
    old_sc = {s["screen"]: s for s in load(Path(a.old) / "screens.json")["screens"]}
    new_sc = {s["screen"]: s for s in load(Path(a.new) / "screens.json")["screens"]}
    art = Path(a.project) / "Content/Dink/Data/Art"
    changed = 0
    for path in sorted(art.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        if '"world_cm"' not in text:
            continue
        d = json.loads(text)
        if d.get("schema") != "dink-art/1" or d.get("screen") not in old_sc:
            print(f"SKIP {path.name}: world_cm but not a dink-art/1 screen manifest")
            continue
        report = {"space": 0, "object": 0, "lights": 0, "warp_overrides": 0, "postprocess": 0, "ratio": []}
        # run once per scale change, on manifests laid out at --old: a point already at the new scale is refused
        probe = next((e["world_cm"] for e in d.get("elements", []) if "world_cm" in e), None)
        if probe is not None and d.get("screen") in old_sc:
            u, v = inverse(old_sc[d["screen"]]["corners"], probe[0] / 100.0, probe[1] / 100.0)
            un, vn = inverse(new_sc[d["screen"]]["corners"], probe[0] / 100.0, probe[1] / 100.0)
            if old_sc[d["screen"]]["corners"] != new_sc[d["screen"]]["corners"] and abs(un - 0.5) + abs(vn - 0.5) < abs(u - 0.5) + abs(v - 0.5) - 0.05:
                print(f"SKIP {path.name}: looks converted already (its first element sits nearer the new screen's middle)")
                continue
        if not convert_manifest(d, old_sc, new_sc, report):
            continue
        rs = report.pop("ratio")
        print(f"{path.name} (screen {d['screen']}): {report}, linear ratio {min(rs or [1]):.4f}..{max(rs or [1]):.4f}")
        changed += 1
        if a.write:
            indent = 2 if text.startswith("{\n  ") else None
            path.write_text(json.dumps(d, indent=indent) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    print(f"{changed} manifests {'written' if a.write else 'to convert'}")
    # The starting house's lighting profile (Scripts/house_lighting.py) pins the six runtime window rows of stonebrook.json
    # and holds absolute practical-light points: take the converted window rows, move the points, then let
    # `python3 -I Scripts/house_lighting.py --apply` derive the daylight rows of the manifest again.
    prof_path = Path(a.project) / "SourceAssets/Art/Stonebrook/LightingV1/lighting.json"
    if prof_path.exists():
        prof_text = prof_path.read_text(encoding="utf-8")
        prof = json.loads(prof_text)
        man = json.loads((art / prof["owner_manifest"]).read_text(encoding="utf-8"))
        co, cn = old_sc[prof["screen"]]["corners"], new_sc[prof["screen"]]["corners"]
        rows = {e["name"]: e for e in man["elements"]}
        moved = 0
        for b in prof["windows"]:
            new_row = rows[b["expected_runtime"]["name"]]
            if b["expected_runtime"] != new_row:
                b["expected_runtime"] = new_row
                moved += 1
        if moved:
            for key in ("practical_points", "legacy_lights"):
                for e in prof.get(key, []):
                    e["world_cm"], _, _ = convert_point(co, cn, e["world_cm"])
            print(f"{prof_path.name}: {moved} window rows re-pinned, practical and legacy light points moved")
            if a.write:
                prof_path.write_text(json.dumps(prof, indent=2) + ("\n" if prof_text.endswith("\n") else ""), encoding="utf-8")
        else:
            print(f"{prof_path.name}: window rows already match the manifest (nothing moved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
