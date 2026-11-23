#!/usr/bin/env python3
"""After a layout-scale change (doc/remaster/WORLD_SCALE.md): re-pin the data that hashes world positions.

  python3 -I Scripts/world_scale_rehash.py --old <bundle at the old scale> --new <bundle at the new scale> [--write]

Two pins hold a placement's or a screen's world position and stop the importer when it moves:
  - families.json collision_fit.origins[*].source_hash (the 85 fitted barrels): the placement record hash, which covers
    `world`, `m_per_px` and the card size;
  - Content/Dink/Data/Gameplay/Hardness/Foundations/SCR_nnn.json: the screen `corners` (metres).
This tool checks that between the two bundles NOTHING of those records changed except the layout fields (world position,
metres per pixel, local scale, card metres, the record hash; for a foundation only the corners), then rewrites the pins
from the new bundle. Without --write it only reports. The native /Game/Dink/RuntimeHardnessV1 meshes are built from the
corners: delete them in the project copy before the import so the importer rebuilds them (it refuses to overwrite).
"""
import argparse, json, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LAYOUT_FIELDS = {"world", "m_per_px", "scale_x", "scale_y", "rot_deg", "size_factor", "card", "hash"}
CARD_LAYOUT_FIELDS = {"width_m", "height_m", "offset_x_m", "offset_z_m"}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def placement_changes(o, n):
    bad = []
    for k in set(o) | set(n):
        if k in LAYOUT_FIELDS:
            if k == "card" and o.get(k) and n.get(k):
                for ck in set(o[k]) | set(n[k]):
                    if ck not in CARD_LAYOUT_FIELDS and o[k].get(ck) != n[k].get(ck):
                        bad.append("card." + ck)
            continue
        if o.get(k) != n.get(k):
            bad.append(k)
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--project", default=str(PROJECT))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    proj = Path(a.project)
    old_pl = {p["id"]: p for p in load(Path(a.old) / "placements.json")["placements"]}
    new_pl = {p["id"]: p for p in load(Path(a.new) / "placements.json")["placements"]}
    old_sc = {s["screen"]: s for s in load(Path(a.old) / "screens.json")["screens"]}
    new_sc = {s["screen"]: s for s in load(Path(a.new) / "screens.json")["screens"]}
    problems = []

    fam_path = proj / "Content/Dink/Data/Art/families.json"
    fam_text = fam_path.read_text(encoding="utf-8")
    fam = json.loads(fam_text)
    rehashed = 0
    for rule in fam.get("collision_fit", {}).get("origins", []):
        oid = rule["origin"]
        o, n = old_pl.get(oid), new_pl.get(oid)
        if o is None or n is None:
            problems.append(f"{oid}: missing from a bundle")
            continue
        if rule["source_hash"] not in (o["hash"], n["hash"]):
            problems.append(f"{oid}: pinned hash matches neither bundle (stale before this change)")
            continue
        bad = placement_changes(o, n)
        if bad:
            problems.append(f"{oid}: non-layout fields changed: {bad}")
            continue
        if rule["source_hash"] != n["hash"]:
            needle = f'"source_hash": "{rule["source_hash"]}"'
            if fam_text.count(needle) != 1:
                problems.append(f"{oid}: pinned hash not found exactly once in the file text")
                continue
            fam_text = fam_text.replace(needle, f'"source_hash": "{n["hash"]}"')
            rule["source_hash"] = n["hash"]
            rehashed += 1

    # the C++ acceptance test freezes the same identities (origin|hash|script|type)
    pins_path = proj / "Plugins/DinkParity/Source/DinkParity/Private/Tests/DinkBarrelRolloutSourcePins.inl"
    pins_text = pins_path.read_text(encoding="utf-8") if pins_path.exists() else ""
    for rule in fam.get("collision_fit", {}).get("origins", []):
        o = old_pl.get(rule["origin"])
        if o and o["hash"] != rule["source_hash"] and f'{rule["origin"]}|{o["hash"]}|' in pins_text:
            pins_text = pins_text.replace(f'{rule["origin"]}|{o["hash"]}|', f'{rule["origin"]}|{rule["source_hash"]}|')

    fdir = proj / "Content/Dink/Data/Gameplay/Hardness/Foundations"
    found = {}
    for f in sorted(fdir.glob("SCR_*.json")):
        d = load(f)
        num = d["screen"]
        o, n = old_sc.get(num), new_sc.get(num)
        if d["corners"] not in (o["corners"], n["corners"]):
            problems.append(f"{f.name}: corners match neither bundle")
            continue
        if o["collision_hash"] != n["collision_hash"] or d["collision_source_hash"] != n["collision_hash"]:
            problems.append(f"{f.name}: collision hash changed")
            continue
        if d["corners"] != n["corners"]:
            d["corners"] = n["corners"]
            found[f] = (json.dumps(d, sort_keys=True, indent=2) + "\n")

    print(f"collision_fit: {rehashed} source hashes to re-pin; foundations: {len(found)} descriptors with new corners; problems: {len(problems)}")
    for p in problems[:40]:
        print("  PROBLEM", p)
    if problems:
        return 1
    if a.write:
        # only the hash strings change: the file keeps its hand-kept layout (other branches edit its rows)
        assert json.loads(fam_text) == fam
        fam_path.write_text(fam_text, encoding="utf-8")
        if pins_text:
            pins_path.write_text(pins_text, encoding="utf-8")
        for f, text in found.items():
            f.write_text(text, encoding="utf-8")
        print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
