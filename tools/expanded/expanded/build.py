"""python3 -m expanded build: content packs -> Plugins/DinkExpanded/Content/Data.

Reads   Plugins/DinkExpanded/Packs/<pack>/pack.toml and story/*.c
        Content/Dink/Data/{Gameplay,Facts,Story} (the 1997 tables and story the project ships)
        bin/dink/story, map.dat, dink.dat (the 1997 scripts, through tools/dinkc and tools/dinkink)
        tools/analyse/out (optional: which 1997 land is reached by design)
Writes  Plugins/DinkExpanded/Content/Data/
          packs.json                     the registry DinkExpanded loads
          Gameplay/placements.csv        the packs' placements, 1997 header, origin S<screen>_P<index>
          Gameplay/screens.csv           the packs' screens and base scripts
          Gameplay/Hardness/SCR_nnn.txt  the packs' screens' hardness (vision 0)
          Story/dink.json, names.csv     the 1997 story plus the packs' knots and VARs
          lines.csv                      every pack line (all DRAFT until the owner approves)
          manifest.json                  inputs' hashes, counts
Nothing else is written. --check writes nothing and exits 1 when the output is out of date.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import tempfile

from . import packs as P
from . import story as S

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PROJECT = os.path.join(REPO, "DinkRemasterUE")
SCHEMA = "dink-expanded/1"


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def hardness_text(screen, solids):
    grid = [[0] * P.W for _ in range(P.H)]
    for x0, y0, x1, y1 in solids:
        for y in range(y0, y1):
            row = grid[y]
            for x in range(x0, x1):
                row[x] = 1
    lines = ["# SCR_%03d hardness (DinkExpanded pack screen; tools/expanded from pack.toml solids; never hand-edit)" % screen, "vision 0"]
    for row in grid:
        toks = []
        x = 0
        while x < P.W:
            c = row[x]
            n = 1
            while x + n < P.W and row[x + n] == c:
                n += 1
            toks.append("%d:%d" % (n, c) if c else "%d" % n)
            x += n
        lines.append(" ".join(toks))
    return "\n".join(lines) + "\n"


def placement_rows(header, pack):
    rows = []
    for pl in pack.placements:
        r = {h: "0" for h in header}
        r.update({
            "origin": "S%03d_P%02d" % (pl["screen"], pl["index"]), "screen": pl["screen"], "index": pl["index"], "type": 1,
            "x": pl["x"] + P.BAR, "y": pl["y"], "seq": pl["seq"], "frame": pl["frame"], "size": pl["size"], "vision": 0,
            "brain": pl["brain"], "script": pl["script"], "hitpoints": pl["hitpoints"], "strength": pl["strength"],
            "defense": pl["defense"], "exp": pl["exp"], "nohit": pl["nohit"], "touch_damage": pl["touch_damage"],
            "speed": pl["speed"], "timing": pl["timing"], "base_walk": pl["base_walk"], "base_idle": pl["base_idle"],
            "base_attack": pl["base_attack"], "base_hit": 0, "base_die": pl["base_die"],
            # map.dat's hard: 0 = the sprite's hardbox is hard, 1 = not (the editor's convention).
            "hard": 0 if pl["hard"] else 1, "sound": 0, "que": 0, "prop": 0, "warp_map": 0,
        })
        rows.append([str(r[h]) for h in header])
    return rows


def build(packs_dir, out_dir, analyse_out, check=False, keep_work=None):
    base = P.Base(PROJECT, os.path.join(REPO, "bin", "dink", "story"), analyse_out)
    packs = P.find_packs(packs_dir)
    problems = P.check_against_base(packs, base)
    if problems:
        raise P.PackError("pack rules:\n  " + "\n  ".join(problems))
    files = {}
    files["packs.json"] = json.dumps({"schema": SCHEMA, "packs": [p.runtime() for p in packs]}, indent=1) + "\n"
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(base.placement_header)
    for p in packs:
        w.writerows(placement_rows(base.placement_header, p))
    files["Gameplay/placements.csv"] = buf.getvalue()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["screen", "base_script"])
    for p in packs:
        for s in p.screens:
            w.writerow([s["screen"], s["base_script"]])
    files["Gameplay/screens.csv"] = buf.getvalue()
    for p in packs:
        for s in p.screens:
            files["Gameplay/Hardness/SCR_%03d.txt" % s["screen"]] = hardness_text(s["screen"], s["solids"])

    story_dir = os.path.join(PROJECT, "Content", "Dink", "Data", "Story")
    with open(os.path.join(story_dir, "dink.json"), encoding="utf-8-sig") as fh:
        base_json = fh.read()
    with open(os.path.join(story_dir, "names.csv"), newline="") as fh:
        base_names = fh.read()
    lines = []
    knots = []
    vars_ = []
    if any(p.scripts for p in packs):
        work = keep_work or tempfile.mkdtemp(prefix="dinkexpanded_")
        ink_out = S.convert(os.path.join(REPO, "bin", "dink", "story"), packs, work, os.path.join(REPO, "bin", "dink"))
        review = [r for r in S.pack_review(ink_out, packs) if r.get("priority") in ("high", "medium")]
        if review:
            raise S.StoryError("the converter flags the pack scripts (new code must be clean):\n  " +
                               "\n  ".join("%s:%s %s %s" % (r["script"], r["line"], r["code"], r["engine_behaviour"]) for r in review))
        with open(os.path.join(ink_out, "json", "dink.json"), encoding="utf-8-sig") as fh:
            sup_json = fh.read()
        with open(os.path.join(ink_out, "names.csv"), newline="") as fh:
            sup_names = fh.read()
        merged, knots, vars_ = S.merge(base_json, sup_json, packs)
        files["Story/dink.json"] = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
        files["Story/names.csv"], _ = S.merged_names(base_names, sup_names, packs)
        lines = S.pack_lines(ink_out, packs)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "kind", "script", "procedure", "speaker", "colour", "text", "status"])
    by_number = {p.number: p for p in packs}
    for r in lines:
        p = by_number.get(int(r["script"][1])) if r["script"][:1] == "x" and r["script"][1:2].isdigit() else None
        status = "approved by the owner %s" % p.approved if p is not None and not p.draft and p.approved else "draft, owner to approve"
        w.writerow([r["id"], r["kind"], r["script"], r["procedure"], r["speaker"], r["colour"], r["text"], status])
    files["lines.csv"] = buf.getvalue()
    manifest = {
        "schema": SCHEMA,
        "packs": {p.id: {"number": p.number, "screens": [s["screen"] for s in p.screens], "scripts": p.scripts,
                         "placements": len(p.placements), "joins": [j["id"] for j in p.joins], "draft": p.draft} for p in packs},
        "base_story_sha256": sha(base_json),
        "base_names_sha256": sha(base_names),
        "pack_knots": sorted(knots), "pack_vars": sorted(vars_), "lines": len(lines),
        "files": {k: sha(v) for k, v in sorted(files.items())},
    }
    files["manifest.json"] = json.dumps(manifest, indent=1, sort_keys=True) + "\n"

    stale = []
    for rel, text in sorted(files.items()):
        path = os.path.join(out_dir, rel)
        old = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                old = fh.read()
        if old != text:
            stale.append(rel)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text)
    # Files a removed pack left behind.
    for root, _dirs, names in os.walk(out_dir):
        for n in names:
            rel = os.path.relpath(os.path.join(root, n), out_dir)
            if rel not in files and not n.startswith("."):
                stale.append(rel + " (left over)")
                if not check:
                    os.remove(os.path.join(root, n))
    return packs, stale, manifest


def main(argv=None):
    ap = argparse.ArgumentParser(prog="expanded")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="validate the packs and write Plugins/DinkExpanded/Content/Data")
    b.add_argument("--packs", default=os.path.join(PROJECT, "Plugins", "DinkExpanded", "Packs"))
    b.add_argument("--out", default=os.path.join(PROJECT, "Plugins", "DinkExpanded", "Content", "Data"))
    b.add_argument("--analyse", default=os.path.join(REPO, "tools", "analyse", "out"),
                   help="tools/analyse output (optional; adds the reached-by-design check of join anchors)")
    b.add_argument("--check", action="store_true", help="write nothing; exit 1 if the output is out of date")
    b.add_argument("--keep-work", help="keep the converter's work directory here")
    a = ap.parse_args(argv)
    try:
        packs, stale, manifest = build(a.packs, a.out, a.analyse, a.check, a.keep_work)
    except (P.PackError, S.StoryError) as e:
        print("EXPANDED BUILD FAILED: %s" % e)
        return 1
    print("%d pack(s): %s; %d pack knot(s), %d pack VAR(s), %d line(s)%s" % (
        len(packs), ", ".join("%s (x%d, %d screens)" % (p.id, p.number, len(p.screens)) for p in packs) or "none",
        len(manifest["pack_knots"]), len(manifest["pack_vars"]), manifest["lines"],
        "" if os.path.isdir(a.analyse) else "; tools/analyse/out missing: reach check skipped"))
    if a.check:
        if stale:
            print("OUT OF DATE: " + ", ".join(stale))
            return 1
        print("up to date")
    else:
        print("wrote %d file(s) to %s" % (len(stale), a.out) if stale else "unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
