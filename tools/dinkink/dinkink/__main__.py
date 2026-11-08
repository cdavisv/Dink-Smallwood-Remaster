import argparse
import sys

from .build import build


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dinkink", description="DinkC AST -> Ink conversion")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="convert all scripts and compile them")
    b.add_argument("--ast", default="../dinkc/out", help="tools/dinkc output directory")
    b.add_argument("--out", default="out")
    b.add_argument("--no-file-check", action="store_true",
                   help="compile only the root file, not each script on its own")
    b.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        s = build(a.ast, a.out, compile_files=not a.no_file_check, jobs=a.jobs)
        ok = s["root_compiles"] and s["files_failed"] == 0
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
