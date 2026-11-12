#!/usr/bin/env python3
"""Alpha gate 2 backlog: every origin ID still open, grouped by sprite family.

Read-only. Uses the classification of Scripts/art_coverage.py unchanged (same inputs, same
rules) and prints, or writes with --out, a Markdown report: one row per sprite family that
still has an open origin ID, sorted by how many map placements are open.

    cd <project dir>            # DinkRemasterUE
    python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md

Open means: state "placeholder" (no art binding yet; nothing in the repo records a
placeholder as owner-accepted), or unclassified (a placement in
Content/Dink/Data/Gameplay/placements.csv that the coverage report lacks, or a coverage row
whose state is none of final/placeholder/cut). Final (bespoke or by family) and cut rows are
closed.

Family: the class id of the placement (Data/Art/families.json and UDinkArtFamilySubsystem
bind by class id first, then by sequence), else the sprite sequence when no class id is
known. Screens form one family, "screen ground (tile layer)". A script warp is listed with
its host; a sprite warp shares its placement's ID and is not counted twice.

Photoreal pass column: the top-level manifest.json of each stream under the Claude photoreal
pass work copy (--photoreal-root) is read; a family counts as claimed when a "families" or
"family" entry names its class id ("inventory" sections list what is missing and are not
claims, nor is a clause saying the asset was not built; the terrain-set manifest claims the
screen ground). Claimed is "in progress
elsewhere", never final.
"""
import argparse
import collections
import csv
import datetime
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import art_coverage  # noqa: E402

SCREEN_FAMILY = "screen ground (tile layer)"
OPEN_STATES = ("placeholder", "unclassified")
DEFAULT_PHOTOREAL = os.path.expanduser(
    "~/Work/DinkPhotorealPassClaude/Dink-Smallwood-Remaster/DinkRemasterUE/SourceAssets/Art/PhotorealPass")
# Original graphics directory -> reference sheet in doc/remaster/reference (animals are on the
# foes sheet, bonuses on the items sheet, the start-menu art on the interface sheet).
SHEET_BY_DIR = {
    "dink": "sheet_dink.png", "effects": "sheet_effects.png", "foes": "sheet_foes.png",
    "animals": "sheet_foes.png", "inside": "sheet_inside.png", "inner": "sheet_inside.png",
    "inter": "sheet_inter.png", "startme": "sheet_inter.png", "items": "sheet_items.png",
    "bonuses": "sheet_items.png", "lands": "sheet_lands.png", "people": "sheet_people.png",
    "struct": "sheet_struct.png", "tiles": "sheet_tiles.png",
}
CLAIM_KEYS = ("families", "family")
TOKEN_RE = re.compile(r"[a-z][a-z0-9_]*")
CLAUSE_RE = re.compile(r"[;,]")
# A clause of a claim string that says the asset was not made is not a claim ("island_spear_pole NOT built").
NEGATED_RE = re.compile(r"\bnot built\b|\bno own module\b|\bnot (?:yet )?(?:made|modelled|done)\b", re.I)


def sheet_for(sprite_family):
    """'92 lands/details/beach-' -> 'sheet_lands.png'; '' when no sheet is known."""
    if sprite_family == SCREEN_FAMILY:
        return SHEET_BY_DIR["tiles"]
    m = re.match(r"^\d+ (?:graphics/)?([^/]+)/", sprite_family or "")
    return SHEET_BY_DIR.get(m.group(1), "") if m else ""


def load_sprite_classes(path):
    """sprite_classes.csv -> ({(seq, frame): row}, {class_id: row})."""
    by_frame, by_class = {}, {}
    if not os.path.isfile(path):
        return by_frame, by_class
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by_frame[(int(r["seq"]), int(r["frame"]))] = r
            by_class.setdefault(r["class_id"], r)
    return by_frame, by_class


def load_placements(path):
    """placements.csv -> {origin: (seq, frame)}."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["origin"]] = (int(r["seq"]), int(r["frame"]))
    return out


def claim_strings(node, inside_claim=False):
    """Every string under a 'families'/'family' key, skipping 'inventory' subtrees (dict keys count too)."""
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "inventory":
                continue
            claim = inside_claim or k in CLAIM_KEYS
            if inside_claim:
                found.append(str(k))
            found.extend(claim_strings(v, claim))
    elif isinstance(node, list):
        for v in node:
            found.extend(claim_strings(v, inside_claim))
    elif isinstance(node, str) and inside_claim:
        found.append(node)
    return found


def load_photoreal_claims(root, known_classes):
    """-> ({family: sorted stream names}, notes). Reads <root>/*/manifest.json only."""
    claims = collections.defaultdict(set)
    notes = []
    if not root or not os.path.isdir(root):
        notes.append("photoreal pass root %s not found: no claims read" % root)
        return {}, notes
    for path in sorted(glob.glob(os.path.join(root, "*", "manifest.json"))):
        stream = os.path.basename(os.path.dirname(path))
        d = art_coverage.read_json(path)
        if not isinstance(d, dict):
            notes.append("photoreal manifest %s unreadable, skipped" % path)
            continue
        if str(d.get("schema", "")).startswith("dink-terrain-sets"):
            claims[SCREEN_FAMILY].add(stream)
        for s in claim_strings(d):
            for clause in CLAUSE_RE.split(s):
                if NEGATED_RE.search(clause):
                    continue
                for tok in TOKEN_RE.findall(clause.lower()):
                    if tok in known_classes:
                        claims[tok].add(stream)
    return {k: sorted(v) for k, v in claims.items()}, notes


def family_key(rec, placement_frames, by_frame):
    """Group key of one coverage placement row: class id, else the sprite sequence."""
    cls = rec.get("_cls") or ""
    if not cls:
        sf = placement_frames.get(rec["origin_id"])
        if sf and sf in by_frame:
            cls = by_frame[sf]["class_id"]
    return cls or rec.get("sprite_family") or "-"


def build_backlog(rows, placement_frames, by_frame):
    """art_coverage rows -> (groups, totals). Each group: family, ids, placements, screens, sequences, states."""
    place = {r["origin_id"]: r for r in rows if r["type"] == "placement"}
    groups = {}

    def group(key):
        if key not in groups:
            groups[key] = {"family": key, "ids": set(), "placements": 0, "screens": 0,
                           "sequences": collections.Counter(), "states": collections.Counter(),
                           "closed": collections.Counter()}
        return groups[key]

    keys = {}
    for r in rows:
        if r["type"] == "placement":
            keys[r["origin_id"]] = family_key(r, placement_frames, by_frame)
        elif r["type"] == "screen":
            keys[r["origin_id"]] = SCREEN_FAMILY
    unclassified_states = collections.Counter()
    for r in rows:
        state = r["state"] if r["state"] in ("final", "placeholder", "cut") else "unclassified"
        if state == "unclassified":
            unclassified_states[r["state"]] += 1
        t, oid = r["type"], r["origin_id"]
        if t == "warp" and oid in place:
            continue  # a sprite warp shares its placement's ID and art
        if t in ("placement", "screen"):
            key = keys[oid]
        elif t == "warp":
            host = oid.split("@", 1)[1] if "@" in oid else ""
            key = keys.get(host, "script warp")
        else:
            key = r.get("sprite_family") or t
        g = group(key)
        if state not in OPEN_STATES:
            g["closed"][state] += 1
            continue
        g["ids"].add(oid)
        g["states"][state] += 1
        if t == "placement":
            g["placements"] += 1
            g["sequences"][r.get("sprite_family") or "-"] += 1
        elif t == "screen":
            g["screens"] += 1
    covered = {r["origin_id"] for r in rows}
    missing = sorted(o for o in placement_frames if o not in covered)
    for oid in missing:
        sf = placement_frames[oid]
        key = by_frame[sf]["class_id"] if sf in by_frame else "seq %d" % sf[0]
        g = group(key)
        g["ids"].add(oid)
        g["states"]["unclassified"] += 1
        g["placements"] += 1
        g["sequences"]["%d" % sf[0]] += 1
    open_groups = [g for g in groups.values() if g["ids"]]
    open_groups.sort(key=lambda g: (-g["placements"], -len(g["ids"]), g["family"]))
    totals = {
        "families": len(open_groups),
        "ids": sum(len(g["ids"]) for g in open_groups),
        "placements": sum(g["placements"] for g in open_groups),
        "screens": sum(g["screens"] for g in open_groups),
        "unclassified": sum(g["states"]["unclassified"] for g in open_groups),
        "unclassified_states": dict(unclassified_states),
        "missing_from_coverage": missing,
    }
    return open_groups, totals


def describe(g, by_class):
    """What the original sprite sheet shows for this family."""
    if g["family"] == SCREEN_FAMILY:
        return "tile-layer ground of each screen (grass, sand, water, walls painted into tilesets) · sheet_tiles.png"
    meta = by_class.get(g["family"])
    sheets = []
    for sf, _ in g["sequences"].most_common():
        s = sheet_for(sf)
        if s and s not in sheets:
            sheets.append(s)
    text = ""
    if meta:
        text = "%s (%s, %s px)" % (meta["name"], meta["family"], meta["pixel_size"]) if meta.get("pixel_size") else meta["name"]
    return " · ".join(x for x in [text] + sheets if x) or "-"


def compact_ids(ids):
    """['S001_P03', 'S001_P04', 'S002_P01'] -> 'S001: P03 P04 · S002: P01'; screens and warps listed as they are."""
    by_screen = collections.OrderedDict()
    other = []
    for oid in sorted(ids):
        m = re.match(r"^(S\d{3})_(P\d{2})$", oid)
        if m:
            by_screen.setdefault(m.group(1), []).append(m.group(2))
        else:
            other.append(oid)
    parts = ["%s: %s" % (s, " ".join(ps)) for s, ps in by_screen.items()]
    scr = [o for o in other if re.match(r"^SCR_\d{3}$", o)]
    rest = [o for o in other if o not in scr]
    if scr:
        parts.append("SCR " + " ".join(o[4:] for o in scr))
    parts.extend(rest)
    return " · ".join(parts)


def anchor(i, family):
    return "f%d-%s" % (i, re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-"))


def render(groups, totals, claims, by_class, meta):
    """-> Markdown text."""
    claimed = [g for g in groups if g["family"] in claims]
    L = []
    L.append("# Alpha gate 2 backlog: origin IDs still open")
    L.append("")
    L.append("Generated %s by `DinkRemasterUE/Scripts/gate2_backlog.py` from %s. Do not edit by hand; regenerate." % (
        meta["date"], meta["source"]))
    L.append("")
    L.append("Alpha gate 2 (`doc/remaster/REMASTER_PLAN.md`): every origin ID is final, placeholder or cut with a reason. "
             "This list is what is still open: every origin ID whose art state in `Scripts/art_coverage.py` is "
             "`placeholder` (no art bound; nothing in the repo records a placeholder as owner-accepted), plus any "
             "unclassified ID. Final (bespoke or by family, `Content/Dink/Data/Art/families.json`) and cut (owner "
             "decision of 9 Nov 2026) are closed and not listed.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("| | open |")
    L.append("|---|---:|")
    L.append("| sprite families | %d |" % totals["families"])
    L.append("| origin IDs | %d |" % totals["ids"])
    L.append("| map placements | %d |" % totals["placements"])
    L.append("| screens (ground tile layer) | %d |" % totals["screens"])
    L.append("| script warps with their own ID | %d |" % (totals["ids"] - totals["placements"] - totals["screens"]))
    L.append("| unclassified IDs | %d |" % totals["unclassified"])
    L.append("")
    cp = sum(g["placements"] for g in claimed)
    ci = sum(len(g["ids"]) for g in claimed)
    L.append("Claimed by the Claude photoreal pass (in progress elsewhere, not final): **%d families, %d origin IDs, "
             "%d placements**. Unclaimed: %d families, %d origin IDs, %d placements." % (
                 len(claimed), ci, cp, totals["families"] - len(claimed), totals["ids"] - ci, totals["placements"] - cp))
    L.append("")
    biggest = max(groups, key=lambda g: (len(g["ids"]), g["placements"])) if groups else None
    if biggest is not None and biggest is not groups[0]:
        L.append("Largest family by origin IDs: `%s` (%d IDs, %d map placements, so it sorts at #%d)." % (
            biggest["family"], len(biggest["ids"]), biggest["placements"], groups.index(biggest) + 1))
        L.append("")
    unclaimed = [g for g in groups if g["family"] not in claims][:10]
    if unclaimed:
        L.append("Largest families no stream has claimed: %s." % ", ".join(
            "`%s` %d" % (g["family"], g["placements"]) for g in unclaimed))
        L.append("")
    L.append("Closed for comparison (art_coverage rows): %s." % meta["closed"])
    if meta.get("notes"):
        L.append("")
        for n in meta["notes"]:
            L.append("- Note: %s" % n)
    L.append("")
    L.append("## How to regenerate")
    L.append("")
    L.append("```bash")
    L.append("cd DinkRemasterUE && python3 -I Scripts/gate2_backlog.py --out ../doc/remaster/ALPHA_GATE2_BACKLOG.md")
    L.append("```")
    L.append("")
    L.append("Run it in the editor's checkout: like `art_coverage.py` it needs the importer's "
             "`Saved/Import/coverage.csv` (`Scripts/import_greybox.sh --region all`), `tools/dinkex/out/sequences.json` "
             "and the gitignored engine template content under `Content/Characters` (the mother's locomotion). From "
             "another worktree add `--project <editor checkout>/DinkRemasterUE`. The photoreal column is a snapshot of "
             "`<--photoreal-root>/*/manifest.json` (default: the uncommitted photoreal pass work copy), read-only; "
             "regenerate after that pass lands or binds families.")
    L.append("")
    L.append("## Backlog by sprite family")
    L.append("")
    L.append("Sorted by open map placements. Family is the class id (`tools/data/sprite_classes.csv`, the key "
             "`families.json` binds); *what the original shows* gives its name, sprite group, size and the reference "
             "sheet in `doc/remaster/reference/`; *sequences* are the original sprite sequences of the open "
             "placements. The origin IDs of each family are listed under [Open origin IDs](#open-origin-ids).")
    L.append("")
    L.append("| # | family | what the original sprite sheet shows | sequences (open placements) | origin IDs | placements | photoreal pass |")
    L.append("|---:|---|---|---|---:|---:|---|")
    for i, g in enumerate(groups, 1):
        seqs = ", ".join("%s (%d)" % kv for kv in g["sequences"].most_common()) or "-"
        claim = ", ".join(claims.get(g["family"], [])) or "-"
        L.append("| %d | [`%s`](#%s) | %s | %s | %d | %d | %s |" % (
            i, g["family"], anchor(i, g["family"]), describe(g, by_class).replace("|", "/"), seqs.replace("|", "/"),
            len(g["ids"]), g["placements"], claim))
    L.append("")
    L.append("## Open origin IDs")
    L.append("")
    L.append("Placements as `Snnn: Pnn ...` (screen, then slot), screens as `SCR nnn ...`, script warps by full ID.")
    L.append("")
    for i, g in enumerate(groups, 1):
        L.append('<a id="%s"></a>' % anchor(i, g["family"]))
        L.append("**%d. `%s`** (%d IDs)  " % (i, g["family"], len(g["ids"])))
        L.append(compact_ids(g["ids"]))
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", default=art_coverage.PROJECT,
                    help="DinkRemasterUE project to read (default: this script's); the gitignored engine template "
                         "content under Content/Characters must be present, as in the editor's checkout")
    ap.add_argument("--coverage", default=os.path.join("Saved", "Import", "coverage.csv"),
                    help="importer coverage report (project relative or absolute)")
    ap.add_argument("--data-repo", help="repo holding tools/dinkex/out/sequences.json and tools/data/sprite_classes.csv "
                                        "(default: the project's parent)")
    ap.add_argument("--photoreal-root", default=DEFAULT_PHOTOREAL, help="PhotorealPass folder of the photoreal work copy")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="date printed in the report")
    ap.add_argument("--out", help="Markdown file to write (default: stdout)")
    args = ap.parse_args(argv)
    art_coverage.PROJECT = os.path.abspath(args.project)
    args.data_repo = os.path.abspath(args.data_repo or os.path.dirname(art_coverage.PROJECT))
    art_coverage.DATA_REPO = args.data_repo

    rows, _manifests, _assets, _ledger, notes, cov_path = art_coverage.classify(args)
    placement_frames = load_placements(os.path.join(art_coverage.PROJECT, "Content", "Dink", "Data", "Gameplay", "placements.csv"))
    by_frame, by_class = load_sprite_classes(os.path.join(args.data_repo, "tools", "data", "sprite_classes.csv"))
    groups, totals = build_backlog(rows, placement_frames, by_frame)
    known = set(by_class) | {g["family"] for g in groups}
    claims, claim_notes = load_photoreal_claims(args.photoreal_root, known)

    states = collections.Counter(r["state"] for r in rows)
    fam_final = sum(1 for r in rows if art_coverage.is_family_final(r))
    closed = "final bespoke %d, final by family %d, cut %d, placeholder %d of %d rows" % (
        states["final"] - fam_final, fam_final, states["cut"], states["placeholder"], len(rows))
    cov_name = os.path.relpath(cov_path, art_coverage.PROJECT)
    if cov_name.startswith(".."):
        cov_name = os.path.basename(cov_path)
    stamp = "`%s` (%d rows, importer run of %s)" % (cov_name, len(rows), datetime.date.fromtimestamp(
        os.path.getmtime(cov_path)).isoformat())
    meta = {"date": args.date, "source": "%s and the manifests under `Content/Dink/Data/Art/`, classified by `Scripts/art_coverage.py`" % stamp,
            "closed": closed,
            "notes": [n for n in notes if "absent from coverage" in n] + claim_notes +
                     (["%d placements of placements.csv are missing from coverage.csv (unclassified)" % len(totals["missing_from_coverage"])]
                      if totals["missing_from_coverage"] else [])}
    text = render(groups, totals, claims, by_class, meta)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    sys.stderr.write("open: %d families, %d origin IDs, %d placements; photoreal-claimed families %d\n" % (
        totals["families"], totals["ids"], totals["placements"], sum(1 for g in groups if g["family"] in claims)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
