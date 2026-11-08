"""Command line: python3 -m dinkc build --scripts DIR --map map.dat --dat dink.dat --out out
                python3 -m dinkc parse FILE.c        (print one AST as JSON)
"""

import argparse
import json
import os
import sys

from . import build as B
from . import parser, source


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dinkc", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="parse all scripts and write every table")
    b.add_argument("--scripts", required=True, help="bin/dink/story directory")
    b.add_argument("--map", required=True, help="bin/dink/map.dat")
    b.add_argument("--dat", required=True, help="bin/dink/dink.dat")
    b.add_argument("--out", required=True, help="output directory (created)")
    b.add_argument("--no-d-check", action="store_true",
                   help="skip decoding .d files to compare them with the .c files")
    p = sub.add_parser("parse", help="print the AST of one .c file")
    p.add_argument("file")
    args = ap.parse_args(argv)

    if args.cmd == "parse":
        name = os.path.splitext(os.path.basename(args.file))[0].lower()
        ast = parser.parse_script(name, source.load_c(args.file))
        json.dump(ast, sys.stdout, indent=1)
        sys.stdout.write("\n")
        return 0

    for path in (args.scripts, args.map, args.dat):
        if not os.path.exists(path):
            print("dinkc: not found: %s" % path, file=sys.stderr)
            return 2
    s = B.build(args.scripts, args.map, args.dat, args.out, check_d=not args.no_d_check)
    print("dinkc build: %(scripts)d scripts, %(parse_failures)d failures, "
          "%(procedures)d procedures, %(dialog_lines)d dialog lines, %(choices)d choices "
          "(%(choice_options)d options), %(globals)d globals, %(fact_rows)d fact rows, "
          "%(calls)d calls, %(diagnostics)d diagnostics in %(seconds)ss" % s)
    print("diagnostics by code: " + ", ".join("%s=%d" % kv
                                              for kv in s["diagnostics_by_code"].items()))
    print("script kinds: " + ", ".join("%s=%d" % kv for kv in s["script_kinds"].items()))
    print("wrote %s" % os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
