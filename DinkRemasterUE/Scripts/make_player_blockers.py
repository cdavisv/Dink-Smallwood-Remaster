#!/usr/bin/env python3
"""Write Content/Dink/Data/Art/player_blockers.json from a `dink.WalkAudit` run.

    python3 Scripts/make_player_blockers.py <audit dir> [<audit dir> ...] [--out Content/Dink/Data/Art/player_blockers.json]

The audit (Plugins/DinkNarrative/.../DinkWalkAudit.cpp) writes walk_audit.csv (per drawn mesh: how deep the player's capsule
can stand inside its body-height footprint) and walk_hulls.csv (that footprint's convex hull in the mesh's own space). A
family mesh (families.json: a placement's or an instanced decor's picture) gets a player-only blocker when some placement
of it can be walked into by at least MIN_DEPTH_CM and it looks solid at body height (rocks, trunks, stumps, walls,
furniture, statues); so do the town house kit (its walls are drawn thicker than the houses' hardness) and the authored manifests' elements that have no
collision of their own (DinkArtSubsystem). Left out: meshes with an opening the hull would close (doors, arches, curved wall modules, gates, houses, and
modules of several trees or rocks whose hull would fill the gaps between them),
things one walks over (rugs, corpses, pickups), and the environment layer's rocks and trees, which are fitted to the
collision instead (UDinkEnvironmentSubsystem::ReliefDiscBlocked). Deterministic: same audit, same file.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

MIN_DEPTH_CM = 15.0
KINDS = {"family", "family_instance", "authored"}
SOLID = ("Boulder", "Rock", "Stone", "Stump", "Tree", "Pine", "Oak", "Willow", "Log", "Wall", "Barrel", "Chest", "Crate", "Table",
         "Chair", "Bed", "Bench", "Cabinet", "Counter", "Shelf", "Statue", "Pillar", "Monument", "Gravestone", "Fountain", "Idol",
         "Post", "Rubble", "Sack", "Jar", "Ballista", "Anvil", "Cart", "Well", "Fireplace")
CASTLE = ("SM_Castle_Wall_8m", "SM_Castle_Tower_Round")
OPEN = ("Door", "Arch", "Cottage", "House", "ForestEdge", "Pair", "Curve", "Gate", "Jamb", "Bridge", "Stair", "Rug", "Carpet", "Corpse", "Heart", "Potion", "Machine",
        "Shrine", "Grass", "Fern", "Bush", "Flower")


def mesh_name(path: str) -> str:
    return path.rsplit(".", 1)[-1]


def wanted(path: str, kind: str) -> bool:
    name = mesh_name(path)
    if any(k in name for k in OPEN):
        return False
    if kind in KINDS:
        return any(k in name for k in SOLID)
    # the environment layer: only the town house kit takes blockers (its walls stand on the 1997 house hardness), and the castle's
    # curtain wall and towers of the structure sets (a straight run crosses the notches of the 1997 outline: the walk audit of
    # 16 Nov found the capsule up to 1.1 m inside 46 wall modules). Not the gatehouse: its arch holds the castle door's warp.
    if kind != "environment":
        return False
    return (name.startswith("SM_Town_") and "Roof" not in name) or name in CASTLE


def area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2


# Placements whose blocker would cut off something the player must reach (Scripts/check_player_blockers.py on the audit
# made with the blockers on): the pine S524_P03 stands against the golden heart S524_P04 on the road to KernSin.
SKIP_ORIGINS = ["S524_P03"]


def build(dirs: list[Path]) -> dict:
    deep: dict[str, float] = {}
    # which rows draw a mesh as the blocker will (a family placement or instance, a town module): their hulls are used,
    # not those of the same mesh as an environment relief rock (scaled and sunk, so sliced at another height)
    takes: set[tuple] = set()
    for d in dirs:
        for f in sorted(d.glob("**/walk_audit.csv")):
            for r in csv.DictReader(f.open()):
                if not wanted(r["mesh"], r["kind"]):
                    continue
                takes.add((r["screen"], r["mesh"], r["origin"], r["instance"]))
                if float(r["depth_cm"]) >= MIN_DEPTH_CM:
                    deep[r["mesh"]] = max(deep.get(r["mesh"], 0.0), float(r["depth_cm"]))
    hulls: dict[str, dict] = {}
    for d in dirs:
        for f in sorted(d.glob("**/walk_hulls.csv")):
            for r in csv.DictReader(f.open()):
                if r["mesh"] not in deep or not r["hull"] or (r["screen"], r["mesh"], r["origin"], r["instance"]) not in takes:
                    continue
                poly = [tuple(float(v) for v in p.split(":")) for p in r["hull"].split(";")]
                if len(poly) < 3:
                    continue
                z = (float(r["local_z_low"]), float(r["local_z_high"]))
                best = hulls.get(r["mesh"])
                if best is None or area(poly) > area(best["hull_cm"]):
                    hulls[r["mesh"]] = {"mesh": r["mesh"], "hull_cm": [[round(x, 1), round(y, 1)] for x, y in poly],
                                        "z_cm": [round(z[0], 1), round(z[1], 1)], "max_walk_in_cm": round(deep[r["mesh"]], 1)}
                elif best is not None:
                    best["z_cm"] = [round(min(best["z_cm"][0], z[0]), 1), round(max(best["z_cm"][1], z[1]), 1)]
    return {"schema": "dink-player-blockers/1",
            "about": "Player-only blockers (alpha QA, 14 Nov 2026; owner decision: anything that looks solid at body height stops Dink). "
                     "Per family mesh: the convex hull of its body-height (15-120 cm) cross-section in the mesh's own space, cm before scale, "
                     "and the prism's local Z range. Written by Scripts/make_player_blockers.py from a dink.WalkAudit run; never hand-edit. "
                     "Read by DinkPlayerBlockers (DinkCore): unscripted family placements and instanced decor get a collision-only prism that blocks "
                     "the player capsule and nothing else (NPCs, creatures, missiles, sight, camera and the 1997 hardness are unchanged).",
            "skip_origins": SKIP_ORIGINS,
            "meshes": [hulls[k] for k in sorted(hulls)]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "Content/Dink/Data/Art/player_blockers.json")
    ap.add_argument("--only", default="", help="comma list of mesh names: add or replace only these rows in the existing file "
                                               "(an audit of a few screens must not rewrite the hulls measured on the whole map)")
    a = ap.parse_args(argv)
    table = build(a.dirs)
    if a.only:
        names = set(a.only.split(","))
        old = json.loads(a.out.read_text())
        rows = {m["mesh"]: m for m in old["meshes"]}
        rows.update({m["mesh"]: m for m in table["meshes"] if mesh_name(m["mesh"]) in names})
        old["meshes"] = [rows[k] for k in sorted(rows)]
        table = old
    a.out.write_text(json.dumps(table, indent=1) + "\n")
    print(f"{len(table['meshes'])} meshes -> {a.out}")
    for m in table["meshes"]:
        print(f"  {mesh_name(m['mesh']):40s} walk-in {m['max_walk_in_cm']:6.1f} cm  hull {len(m['hull_cm'])} pts  z {m['z_cm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
