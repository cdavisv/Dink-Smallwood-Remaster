"""Command line: python3 -m analyse build --ir ../dinkex/out --out out"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="analyse", description="Dink remaster stages 3 (analyse) and 4 (layout)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="run the analysis and write every output")
    b.add_argument("--ir", default=os.path.join(REPO, "tools", "dinkex", "out"), help="tools/dinkex output")
    b.add_argument("--out", default=os.path.join(HERE, "out"))
    b.add_argument("--table", default=os.path.join(HERE, "regions.toml"))
    b.add_argument("--story", default=os.path.join(REPO, "bin", "dink", "story"), help="DinkC scripts")
    b.add_argument("--classes", default=os.path.join(REPO, "tools", "data"), help="tile/sprite class tables")
    b.add_argument("--dinkc", default=os.path.join(REPO, "tools", "dinkc", "out"), help="tools/dinkc output (optional)")
    a = ap.parse_args(argv)
    from .build import analyse, write_all
    t = time.time()
    w = analyse(a.ir, a.table, story_dir=a.story, classes_dir=a.classes)
    write_all(w, a.out, dinkc_dir=a.dinkc if os.path.isdir(a.dinkc) else None)
    s = w.summary
    print("area: outdoor %.3f km2 (land %.3f), mainland land %.3f km2, interiors %.4f km2" % (
        s["area_km2"]["outdoor_total"], s["area_km2"]["outdoor_land"], s["area_km2"]["mainland_land"],
        s["area_km2"]["interiors"]))
    print("mainland %.0f x %.0f m; straight run E-W %.0f s, N-S %.0f s at 6 m/s" % (
        s["mainland"]["width_m"], s["mainland"]["height_m"], s["mainland"]["run_ew_s"], s["mainland"]["run_ns_s"]))
    for k, v in s["settlements"].items():
        print("  %-20s %2d screens  %6.0f x %4.0f m" % (k, v["screens"], v["width_m"], v["height_m"]))
    print("gaps to mainland (m): %s" % s["sheet_gap_to_mainland_m"])
    print("done in %.1f s" % (time.time() - t))
    return 0
