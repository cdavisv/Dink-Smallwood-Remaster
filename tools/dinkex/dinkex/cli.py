"""Command line: ``python3 -m dinkex <command>``."""

import argparse
import json
import os
import sys

from . import __version__
from .extract import ALL_STEPS, Extractor


def cmd_extract(a):
    steps = ALL_STEPS if not a.only else tuple(s.strip() for s in a.only.split(",") if s.strip())
    bad = [s for s in steps if s not in ALL_STEPS]
    if bad:
        print("unknown step(s): %s (choose from %s)" % (", ".join(bad), ", ".join(ALL_STEPS)), file=sys.stderr)
        return 2
    log = (lambda m: None) if a.quiet else (lambda m: print(m, flush=True))
    ex = Extractor(a.data, a.out, steps, log=log)
    summary = ex.run()
    print(json.dumps({k: summary[k] for k in summary if k in (
        "screens_used", "screens_indoor", "active_placements", "warp_placements",
        "distinct_placement_scripts", "distinct_screen_base_scripts", "bmp_frames_total",
        "sequences_defined", "max_placements_on_one_screen", "seconds") if k in summary}, indent=1))
    print("wrote %s" % os.path.abspath(a.out))
    return 0


def cmd_unff(a):
    """Dump every BMP reachable under a data dir (archives and loose) into a flat tree."""
    from . import ff as ffmod
    n = 0
    for root, _d, files in os.walk(a.src):
        rel = os.path.relpath(root, a.src)
        for f in sorted(files):
            p = os.path.join(root, f)
            low = f.lower()
            if low.endswith(".ff"):
                data, entries = ffmod.read_ff(p)
                for e in entries:
                    if not e.name.endswith(".bmp"):
                        continue
                    dst = os.path.join(a.out, rel)
                    os.makedirs(dst, exist_ok=True)
                    with open(os.path.join(dst, e.name), "wb") as o:
                        o.write(data[e.offset:e.offset + e.size])
                    n += 1
            elif low.endswith(".bmp"):
                dst = os.path.join(a.out, rel)
                os.makedirs(dst, exist_ok=True)
                with open(p, "rb") as i, open(os.path.join(dst, low), "wb") as o:
                    o.write(i.read())
                n += 1
    print("extracted %d BMPs to %s" % (n, a.out))
    return 0


def cmd_facts(a):
    """Print the headline numbers without writing any output files."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ex = Extractor(a.data, tmp, steps=("screens", "hardness"))
        s = ex.run()
    keys = ("screens_used", "screens_indoor", "active_placements", "warp_placements",
            "distinct_placement_scripts", "distinct_screen_base_scripts",
            "max_placements_on_one_screen", "bmp_frames_total", "sequences_defined")
    print(json.dumps({k: s[k] for k in keys}, indent=1))
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_data = os.path.normpath(os.path.join(here, "..", "..", "bin", "dink"))
    p = argparse.ArgumentParser(prog="dinkex", description="Extract Dink Smallwood data to a neutral IR.")
    p.add_argument("--version", action="version", version="dinkex " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="extract everything (or --only some steps)")
    e.add_argument("--data", default=default_data, help="game data dir (default: bin/dink)")
    e.add_argument("--out", default="out", help="output dir (default: ./out)")
    e.add_argument("--only", help="comma list of steps: " + ",".join(ALL_STEPS))
    e.add_argument("--quiet", action="store_true")
    e.set_defaults(fn=cmd_extract)

    u = sub.add_parser("unff", help="dump all BMPs from .ff archives and loose files to a directory")
    u.add_argument("src")
    u.add_argument("out")
    u.set_defaults(fn=cmd_unff)

    f = sub.add_parser("facts", help="print headline counts (no files written)")
    f.add_argument("--data", default=default_data)
    f.set_defaults(fn=cmd_facts)

    a = p.parse_args(argv)
    return a.fn(a)
