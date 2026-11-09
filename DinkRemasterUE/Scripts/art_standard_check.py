#!/usr/bin/env python3
"""Check art against SourceAssets/Art/ART_STANDARD.md; exit 1 on any violation.

    cd <project dir>            # DinkRemasterUE
    python3 -I Scripts/art_standard_check.py [--all] [--json out.json]

Pure Python 3 standard library, read-only. The material library, triangle budgets and texture caps are read from
the tables of ART_STANDARD.md, so the page is the single source of the numbers.

Inputs:
  SourceAssets/Art/**/*manifest*.json, *report*.json, validation*.json   source and export records: class,
        materials / material_slots, LOD0 triangles (tris, triangles, triangles_per_lod, candidate_triangles, LOD
        reports), texture sizes (export manifest `textures[].size`, or the PNG files a manifest names), families
  Content/Dink/Data/Art/*.json            which meshes are delivered (referenced at runtime), and families.json
  Content/Dink/**.uasset                  whether a referenced mesh exists

Violations (per source asset; an asset is a name inside one source package, e.g. Stonebrook/Refinements/
PhotorealBarrelV1:SM_Barrel_Oak_01):
  material   a static mesh uses a material that is not in the library (characters, creatures and their parts are exempt)
  budget     LOD0 triangles over the class hard cap (over the soft target only: a warning)
  texture    a texture edge over the class cap (the lower family-scatter cap for a mesh a families.json row binds)
  family     a delivered mesh declares no sprite family (no `families` in its manifest, no families.json row);
             screen-fitted terrain (SM_*_<n>_Land/Bank/Water_*, SM_Vista*, SM_Ground_*, SM_Path_*) and meshes used
             only by render-only `context` manifests are exempt
  missing    a mesh referenced by a runtime manifest has no .uasset
Warnings (not violations): LOD0 triangles between the soft target and the hard cap.
Notes: undeclared class, no triangle count found, delivered mesh with no source record.
"""
import argparse
import collections
import json
import os
import re
import struct
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ART = os.path.join(PROJECT, "SourceAssets", "Art")
DATA_ART = os.path.join(PROJECT, "Content", "Dink", "Data", "Art")
STANDARD = os.path.join(ART, "ART_STANDARD.md")

NAME_RE = re.compile(r"^(SM|SK)_[A-Za-z0-9_]+$")
LOD_RE = re.compile(r"_LOD(\d+)$")
GAME_MESH_RE = re.compile(r"^/Game/[^\s\"']*/(SM|SK)_[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)?$")
TERRAIN_RE = re.compile(r"^SM_(Vista|Ground_|Path_)|^SM_[A-Za-z0-9]+_\d{3}_(Land|Bank|Water)_")
SKELETAL_CLASSES = {"character_hero", "character_humanoid", "creature_quadruped", "creature"}
REPORT_FILE_RE = re.compile(r"(manifest|report|validation)[^/]*\.json$", re.I)


def rel(path):
    return os.path.relpath(path, PROJECT)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# --- the standard's tables -------------------------------------------------------------------------------------------

def read_standard(path):
    """-> (library set, {class: (soft target, hard cap)}, {class: (max edge, max edge as family scatter)})."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    sections = re.split(r"^## ", text, flags=re.M)

    def section(title):
        for s in sections:
            if s.lower().startswith(title.lower()):
                return s
        sys.exit("ART_STANDARD.md has no section '%s'" % title)

    def rows(s):
        for line in s.splitlines():
            if line.startswith("| `"):
                yield [c.strip() for c in line.strip().strip("|").split("|")]

    def num(cell):
        return int(cell.replace(",", "").strip())

    library = {r[0].strip("`") for r in rows(section("2. Shared material library"))}
    budgets = {r[0].strip("`"): (num(r[1]), num(r[2])) for r in rows(section("3. Triangle budgets"))}
    caps = {r[0].strip("`"): (num(r[1]), num(r[2])) for r in rows(section("4. Texture resolution"))}
    if not library or not budgets or not caps:
        sys.exit("ART_STANDARD.md tables could not be read")
    shared = read_json(os.path.join(ART, "SharedMaterials", "manifest.json"))
    if isinstance(shared, dict) and isinstance(shared.get("materials"), dict):
        library |= {"MI_Shared_" + n for n in shared["materials"]}
    return library, budgets, caps


# --- source records ----------------------------------------------------------------------------------------------------

def package_of(relpath):
    """Source package of a JSON under SourceAssets/Art: the refinement folder, Creatures/<x>, Characters/<x>, or the kit."""
    parts = relpath.replace(os.sep, "/").split("/")[:-1]
    if "Refinements" in parts:
        i = parts.index("Refinements")
        return "/".join(parts[:i + 2])
    if parts and parts[0] == "Creatures" and len(parts) > 1:
        return "/".join(parts[:2])
    return parts[0] if parts else "."


def png_size(path):
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
            return struct.unpack(">II", head[16:24])
    except OSError:
        pass
    return None


def lod0_of(value):
    """tris value: int, or {LODn: int} / {<name>_LODn: int} -> LOD0 count."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        items = [(k, v) for k, v in value.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        for k, v in items:
            m = re.search(r"LOD(\d+)$", str(k))
            if m and int(m.group(1)) == 0:
                return int(v)
        if items:
            return int(max(v for _, v in items))
    return None


class Asset:
    def __init__(self, package, name):
        self.package, self.name = package, name
        self.cls = None
        self.materials = {}       # priority -> set; 2 = export material_slots, 1 = manifest materials
        self.tris = None
        self.tex = None
        self.tex_from = ""
        self.families = set()
        self.files = set()
        self.content_paths = set()
        self.role = None

    @property
    def key(self):
        return "%s:%s" % (self.package, self.name)

    def material_set(self):
        if not self.materials:
            return set()
        return self.materials[max(self.materials)]


def harvest(record, name, lod, asset, json_dir):
    if lod not in (None, 0):
        return
    cls = record.get("class") or record.get("cls") or record.get("dink_class")
    if isinstance(cls, str) and not asset.cls:
        asset.cls = cls
    if isinstance(record.get("role"), str):
        asset.role = record["role"]
    slots = record.get("material_slots")
    if isinstance(slots, list) and slots:
        names = {s if isinstance(s, str) else (s.get("material") or s.get("name")) for s in slots if isinstance(s, (str, dict))}
        asset.materials.setdefault(2, set()).update(n for n in names if n)
    mats = record.get("materials")
    if isinstance(mats, list) and mats and all(isinstance(m, str) for m in mats):
        asset.materials.setdefault(1, set()).update(mats)
    tri = None
    for key in ("tris", "tris_lod0", "triangles_per_lod", "tris_per_lod", "candidate_triangles"):
        if key in record:
            t = lod0_of(record[key])
            if t is not None:
                tri = max(tri or 0, t)
    if "triangles" in record and isinstance(record["triangles"], (int, float)) and not isinstance(record["triangles"], bool):
        tri = max(tri or 0, int(record["triangles"]))
    if tri is not None:
        asset.tris = max(asset.tris or 0, tri)
    tex = record.get("textures")
    edges = []
    if isinstance(tex, list):
        for t in tex:
            if isinstance(t, dict) and isinstance(t.get("size"), list) and t["size"]:
                edges.append((max(t["size"]), "export manifest"))
    elif isinstance(tex, dict):
        for p in tex.values():
            if isinstance(p, str) and p.lower().endswith(".png"):
                size = png_size(os.path.join(json_dir, p))
                if size:
                    edges.append((max(size), p))
    for edge, src in edges:
        if asset.tex is None or edge > asset.tex:
            asset.tex, asset.tex_from = edge, src
    fam = record.get("families") or record.get("dink_families")
    if isinstance(fam, list):
        asset.families.update(str(f) for f in fam)
    elif isinstance(fam, str):
        asset.families.add(fam)
    if isinstance(record.get("content_path"), str):
        asset.content_paths.add(record["content_path"].split(".")[0])


def walk_records(node, parent_key, out):
    if isinstance(node, dict):
        name = None
        for k in ("name", "mesh", "asset", "blend_collection", "object"):
            v = node.get(k)
            if isinstance(v, str) and NAME_RE.match(v):
                name = v
                break
        if name is None and isinstance(parent_key, str) and NAME_RE.match(parent_key):
            name = parent_key
        if name:
            m = LOD_RE.search(name)
            out.append((LOD_RE.sub("", name), int(m.group(1)) if m else None, node))
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                walk_records(v, k, out)
    elif isinstance(node, list):
        for v in node:
            walk_records(v, None, out)


def load_sources():
    assets = {}
    unnamed = collections.defaultdict(list)  # package -> [tris] from report tops without an asset name
    files = 0
    for dirpath, dirnames, filenames in os.walk(ART):
        dirnames.sort()
        for fn in sorted(filenames):
            if not REPORT_FILE_RE.search(fn):
                continue
            path = os.path.join(dirpath, fn)
            data = read_json(path)
            if data is None:
                continue
            files += 1
            r = os.path.relpath(path, ART)
            pkg = package_of(r)
            recs = []
            walk_records(data, None, recs)
            for name, lod, record in recs:
                a = assets.get((pkg, name))
                if a is None:
                    a = assets[(pkg, name)] = Asset(pkg, name)
                a.files.add(r)
                harvest(record, name, lod, a, dirpath)
            if isinstance(data, dict) and isinstance(data.get("candidate_triangles"), int) and not any(NAME_RE.match(str(data.get(k, ""))) for k in ("name", "mesh")):
                unnamed[pkg].append((data["candidate_triangles"], r))
    for pkg, items in unnamed.items():
        names = [a for (p, _), a in assets.items() if p == pkg]
        if len(names) == 1:
            for tri, r in items:
                names[0].tris = max(names[0].tris or 0, tri)
                names[0].files.add(r)
    return assets, files


# --- runtime deliveries ----------------------------------------------------------------------------------------------------

def load_deliveries():
    """-> {package path: set(uses)}, families.json mesh packages, parsed family rows, render-only context files."""
    delivered = collections.defaultdict(set)
    context_files = set()
    family_meshes = collections.defaultdict(list)
    family_rows = []
    if not os.path.isdir(DATA_ART):
        return delivered, family_meshes, family_rows, context_files

    def strings(node, field, out):
        if isinstance(node, dict):
            for k, v in node.items():
                strings(v, k, out)
        elif isinstance(node, list):
            for v in node:
                strings(v, field, out)
        elif isinstance(node, str) and GAME_MESH_RE.match(node):
            out.append((field, node))

    for fn in sorted(os.listdir(DATA_ART)):
        if not fn.lower().endswith(".json"):
            continue
        data = read_json(os.path.join(DATA_ART, fn))
        if not isinstance(data, dict):
            continue
        if data.get("schema") == "dink-art-families/1":
            for row in data.get("families") or []:
                if isinstance(row, dict) and isinstance(row.get("mesh"), str):
                    pkg = row["mesh"].split(".")[0]
                    family_meshes[pkg].append(str(row.get("family")))
                    family_rows.append(row)
                    delivered[pkg].add("families.json")
            continue
        if "context" in data:
            context_files.add(fn)
        found = []
        strings(data, None, found)
        for field, path in found:
            if field in ("source", "skeleton", "reference_skeleton"):
                continue
            delivered[path.split(".")[0]].add(fn)
    return delivered, family_meshes, family_rows, context_files


def match_source(pkg_path, by_name):
    """Best source asset for a delivered package path, by exact content_path, then by shared folder names."""
    name = pkg_path.rsplit("/", 1)[-1]
    cands = by_name.get(name, [])
    if not cands:
        return None
    folders = set(pkg_path.split("/")[3:-1])  # after /Game/Dink
    best, best_score = None, None
    for a in cands:
        if pkg_path in a.content_paths:
            return a
        parts = set(a.package.split("/"))
        score = len(parts & folders) - len(parts - folders)
        if best_score is None or score > best_score:
            best, best_score = a, score
    return best


def assumed_class(a):
    if a.cls:
        return a.cls, False
    if a.name.startswith("SK_"):
        if a.package.startswith("Creatures"):
            return "creature", True
        if a.package == "Characters/Dink" or a.name == "SK_Dink":
            return "character_hero", True
        return "character_humanoid", True
    return None, True


# --- check ---------------------------------------------------------------------------------------------------------------

def check(args):
    library, budgets, caps = read_standard(STANDARD)
    assets, files = load_sources()
    delivered, family_meshes, family_rows, context_files = load_deliveries()
    by_name = collections.defaultdict(list)
    for a in assets.values():
        by_name[a.name].append(a)

    delivered_by_asset = collections.defaultdict(set)
    notes = []
    violations = collections.defaultdict(list)  # key -> [(kind, text)]
    warnings = []
    rows_extra = []
    for pkg_path, uses in sorted(delivered.items()):
        uasset = os.path.join(PROJECT, "Content", pkg_path[len("/Game/"):] + ".uasset")
        exists = os.path.isfile(uasset)
        a = match_source(pkg_path, by_name)
        if a is not None:
            delivered_by_asset[a.key].add(pkg_path)
        if not exists:
            key = a.key if a else pkg_path
            violations[key].append(("missing", "%s has no %s" % (pkg_path, rel(uasset))))
            if a is None:
                rows_extra.append((key, "?", "yes", "-", "-"))
        elif a is None:
            notes.append("delivered %s (%s) has no source record under SourceAssets/Art" % (pkg_path, ", ".join(sorted(uses))))

    family_pkgs = set(family_meshes)
    checked = 0
    for key in sorted(assets, key=lambda k: (k[0].lower(), k[1].lower())):
        a = assets[key]
        if a.name.startswith("SM_") and not a.cls and a.tris is None and not a.material_set():
            continue  # a name mentioned in passing (a placement row, a collision note), not an asset record
        checked += 1
        cls, guessed = assumed_class(a)
        if guessed and cls:
            notes.append("%s declares no class; checked as %s" % (a.key, cls))
        elif cls is None:
            notes.append("%s declares no class; budget and caps not checked" % a.key)
        if cls and cls not in budgets:
            notes.append("%s has class %s, which the standard does not list" % (a.key, cls))
        # Characters and creatures (their rigs and the static parts made from them, e.g. the duck's gore head) own their materials.
        rig_owned = a.name.startswith("SK_") or cls in SKELETAL_CLASSES or a.package.split("/")[0] in ("Characters", "Creatures")
        if not rig_owned:
            bad = sorted(m for m in a.material_set() if m not in library)
            if bad:
                violations[a.key].append(("material", "not in the library: " + ", ".join(bad)))
        if cls in budgets:
            if a.tris is None:
                notes.append("%s: no LOD0 triangle count in its reports" % a.key)
            elif a.tris > budgets[cls][1]:
                violations[a.key].append(("budget", "%s LOD0 triangles > %s hard cap %s" % (format(a.tris, ","), cls, format(budgets[cls][1], ","))))
            elif a.tris > budgets[cls][0]:
                warnings.append("%s: %s LOD0 triangles > %s soft target %s (hard cap %s)" % (
                    a.key, format(a.tris, ","), cls, format(budgets[cls][0], ","), format(budgets[cls][1], ",")))
        paths = delivered_by_asset.get(a.key, set())
        scatter = bool(paths & family_pkgs)
        if cls in caps and a.tex:
            cap = caps[cls][1] if scatter else caps[cls][0]
            if a.tex > cap:
                violations[a.key].append(("texture", "%d px texture > %s %scap %d" % (a.tex, cls, "family-scatter " if scatter else "", cap)))
        render_only = paths and all(delivered[p] <= context_files for p in paths)
        if paths and not a.families and not (paths & family_pkgs) and not TERRAIN_RE.search(a.name) and not render_only:
            violations[a.key].append(("family", "delivered (%s), declares no sprite family" % ", ".join(sorted(paths))))
    return assets, delivered_by_asset, violations, warnings, notes, rows_extra, files, checked, library, budgets, caps, family_rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--all", action="store_true", help="print every asset, not only those with violations")
    ap.add_argument("--json", help="also write the result as JSON (project relative)")
    ap.add_argument("--notes", action="store_true", help="print every note")
    args = ap.parse_args()
    assets, delivered, violations, warnings, notes, extra, files, checked, library, budgets, caps, family_rows = check(args)

    table = []
    for key in sorted(assets, key=lambda k: (k[0].lower(), k[1].lower())):
        a = assets[key]
        v = violations.get(a.key, [])
        if not v and not args.all:
            continue
        cls, _ = assumed_class(a)
        budget = budgets.get(cls, (None, None))[1] if cls else None
        cap = caps.get(cls, ("-", "-"))[0] if cls else "-"
        table.append([a.key, cls or "?", "yes" if a.key in delivered else "no",
                      "%s/%s" % (format(a.tris, ",") if a.tris is not None else "-", format(budget, ",") if budget else "-"),
                      "%s/%s" % (a.tex or "-", cap),
                      "; ".join("%s: %s" % kv for kv in v) or "ok"])
    for key, cls, dl, tri, tex in extra:
        table.append([key, cls, dl, tri, tex, "; ".join("%s: %s" % kv for kv in violations.get(key, []))])

    header = ["asset (package:name)", "class", "delivered", "tris/hard cap", "tex/cap", "violations"]
    if table:
        widths = [min(max(len(str(r[i])) for r in table + [header]), 70 if i == 0 else 200) for i in range(len(header))]
        print("  ".join(h.ljust(w) for h, w in zip(header, widths[:-1])) + "  " + header[-1])
        for r in table:
            print("  ".join(str(c).ljust(w) for c, w in zip(r[:-1], widths[:-1])) + "  " + r[-1])
        print()
    kinds = collections.Counter(k for v in violations.values() for k, _ in v)
    grouped = collections.Counter()
    for v in violations.values():
        for k, text in v:
            grouped[(k, re.sub(r"\(/Game/[^)]*\)", "(...)", re.sub(r"[\d,]+ LOD0", "N LOD0", text)))] += 1
    print("By violation (assets):")
    for (k, text), n in sorted(grouped.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %4d  %-8s %s" % (n, k, text))
    print()
    print("Checked %d source assets from %d JSON files under SourceAssets/Art; %d delivered meshes matched; library %d materials; %d family bindings." % (
        checked, files, len(delivered), len(library), len(family_rows)))
    print("Violations: %d assets, %s" % (len(violations), ", ".join("%s %d" % kv for kv in sorted(kinds.items())) or "none"))
    print("Warnings (over the soft target, under the hard cap): %d" % len(warnings))
    for w in warnings:
        print("WARNING:", w)
    shown = notes if args.notes else notes[:15]
    for n in shown:
        print("NOTE:", n)
    if len(notes) > len(shown):
        print("NOTE: ... %d more (--notes)" % (len(notes) - len(shown)))
    if args.json:
        out = {"violations": {k: [{"kind": a, "detail": b} for a, b in v] for k, v in sorted(violations.items())},
               "counts": dict(kinds), "warnings": warnings, "notes": notes, "checked": checked}
        with open(os.path.join(PROJECT, args.json), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
            f.write("\n")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
