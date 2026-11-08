#!/usr/bin/env python3
"""Regenerate Content/Dink/Data/Facts/dink_globals.csv from the data repo.

Usage:
    python3 Scripts/regen_globals.py [path/to/Dink-Smallwood-Remaster]

The data repo defaults to ../Dink-Smallwood-Remaster (sibling of this project).
It must already contain tools/dinkc/out/globals.json and facts.csv; build them with
    cd <data repo>/tools/dinkc && python3 -m dinkc build --scripts ../../bin/dink/story \
        --map ../../bin/dink/map.dat --dat ../../bin/dink/dink.dat --out out
This script only reads the data repo. The UE project never reads it at runtime.
"""
import csv
import json
from remaster_paths import default_data_repo

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
OUT = HERE / "Content" / "Dink" / "Data" / "Facts" / "dink_globals.csv"


def main() -> int:
    data_repo = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else default_data_repo(HERE)
    out_dir = data_repo / "tools" / "dinkc" / "out"
    globals_json = out_dir / "globals.json"
    facts_csv = out_dir / "facts.csv"
    if not globals_json.exists() or not facts_csv.exists():
        print(f"missing {globals_json} or {facts_csv}; run the dinkc build first (see docstring)", file=sys.stderr)
        return 1

    commit = "unknown"
    try:
        commit = subprocess.run(["git", "-C", str(data_repo), "log", "-1", "--format=%h"],
                                capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass

    globals_ = json.loads(globals_json.read_text())
    with facts_csv.open(newline="") as f:
        engine_bound = {r["variable"]: r["engine_bound"] for r in csv.DictReader(f)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as out:
        out.write("# Initial values of the 63 global variables of the original Dink Smallwood (1997),\n")
        out.write("# from the make_global_int calls in story/main.c. Names are the DinkC names without '&'.\n")
        out.write("# kind: engine = read/written by the original engine itself (stats, player_map, ...); story = script-only.\n")
        out.write("# GENERATED - do not hand-edit. Regenerate with Scripts/regen_globals.py (see AGENTS.md).\n")
        out.write(f"# source: Dink-Smallwood-Remaster tools/dinkc/out/globals.json (data repo commit {commit})\n")
        w = csv.writer(out, lineterminator="\n")
        w.writerow(["name", "initial", "kind", "script", "line"])
        for name, decls in globals_.items():
            if len(decls) != 1:
                print(f"warning: {name} declared {len(decls)} times; using the first", file=sys.stderr)
            d = decls[0]
            kind = "engine" if engine_bound.get(name) == "1" else "story"
            w.writerow([name.lstrip("&"), d["initial"], kind, d["script"], d["line"]])
    print(f"wrote {len(globals_)} globals to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
