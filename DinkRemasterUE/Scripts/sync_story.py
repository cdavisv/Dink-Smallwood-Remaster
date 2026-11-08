#!/usr/bin/env python3
"""Bring the converted Ink story (data repo tools/dinkink/out) into the project.

Usage:
    python3 Scripts/sync_story.py [--data <path to Dink-Smallwood-Remaster>] [--rebuild] [--check]

Copies into Content/Dink/Data/Story/ (staged into packages by DirectoriesToAlwaysStageAsUFS=Dink/Data,
see Config/DefaultGame.ini; nothing here is a .uasset):

    dink.json                 the whole story compiled by inklecate (ink JSON format 21)
    names.csv                 DinkC name -> Ink name (knots, entry points, globals, script locals)
    director_vocabulary.csv   every director command with args, blocking flag and usage counts
    story_manifest.json       data repo commit, inklecate version, sha256 of each file

Steps:
  1. --rebuild: run the converter first (python3 -m dinkink build --ast ../dinkc/out --out out).
     Without it the existing out/ is used; a missing out/ also triggers the converter.
  2. If any out/ink/*.ink is newer than out/json/dink.json, the story is recompiled with inklecate
     into a temporary directory (out/ is never modified by this script except through step 1).
  3. The JSON is checked (inkVersion 21, root container present, every knot of names.csv present).
  4. Files are copied only when their content changed; the manifest is rewritten only when a hash
     changed, so a re-run with unchanged input leaves the project byte-identical.

--check: do everything except writing; exit 1 if the project copy is out of date.
Reads the data repo only. The game never reads the data repo at run time.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
DEST = HERE / "Content" / "Dink" / "Data" / "Story"
EXPECTED_INK_VERSION = 21  # inklecate 1.2.1 writes 21; Inkpot's InkPlusPlus reads 18..21
COPIED = ("names.csv", "director_vocabulary.csv")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_commit(repo: pathlib.Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%h"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", "tools/dinkink", "tools/dinkc"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return out + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def inklecate_version() -> str:
    """inklecate prints no version; the install directory is named after it (~/.local/share/inklecate/v1.2.1)."""
    exe = shutil.which("inklecate")
    if not exe:
        return "not found"
    for part in reversed(pathlib.Path(exe).resolve().parts):
        if part.startswith("v") and part[1:2].isdigit():
            return part
    return "unknown"


def compile_story(ink_dir: pathlib.Path) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "dink.json"
        r = subprocess.run(["inklecate", "-o", str(out), str(ink_dir / "dink.ink")], capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            sys.exit(f"inklecate failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return out.read_bytes()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=pathlib.Path, default=HERE.parent)
    ap.add_argument("--rebuild", action="store_true", help="run the dinkink converter first")
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if out of date")
    args = ap.parse_args()

    tool = args.data / "tools" / "dinkink"
    out = tool / "out"
    if not tool.is_dir():
        print(f"data repo not found: {tool}", file=sys.stderr)
        return 2
    if args.rebuild or not (out / "json" / "dink.json").exists():
        if args.check:
            print("converter output missing; run without --check", file=sys.stderr)
            return 1
        print("running the dinkink converter ...")
        r = subprocess.run([sys.executable, "-m", "dinkink", "build", "--ast", "../dinkc/out", "--out", "out"], cwd=tool)
        if r.returncode != 0:
            print("converter failed (does tools/dinkc/out exist? see the data repo AGENTS.md)", file=sys.stderr)
            return r.returncode

    json_path = out / "json" / "dink.json"
    ink_files = sorted((out / "ink").glob("*.ink"))
    newest_ink = max(p.stat().st_mtime for p in ink_files)
    if newest_ink > json_path.stat().st_mtime:
        print("out/ink is newer than out/json/dink.json: recompiling with inklecate")
        story_bytes = compile_story(out / "ink")
    else:
        story_bytes = json_path.read_bytes()

    # Validate.
    text = story_bytes.decode("utf-8-sig")
    story = json.loads(text)
    version = story.get("inkVersion")
    if version != EXPECTED_INK_VERSION:
        print(f"unexpected inkVersion {version} (expected {EXPECTED_INK_VERSION})", file=sys.stderr)
        return 1
    root = story.get("root")
    if not isinstance(root, list) or not root or not isinstance(root[-1], dict):
        print("story has no root container", file=sys.stderr)
        return 1
    named = root[-1]
    with (out / "names.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    knots = [r["ink"] for r in rows if r["kind"] == "knot"]
    missing = [k for k in knots if k not in named]
    if missing:
        print(f"{len(missing)} knots of names.csv are not in the story: {missing[:10]}", file=sys.stderr)
        return 1
    entries = sum(1 for r in rows if r["kind"] == "entry")
    # Engine-bug intent stays behind CONST fix_<script>_l<line> = false (DESIGN.md 9); a reviewer flips
    # one deliberately in the data repo, never by accident here.
    fix_true = []
    fixes = 0
    for ink in ink_files:
        for line in ink.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*CONST\s+(fix_\w+)\s*=\s*(\w+)", line)
            if m:
                fixes += 1
                if m.group(2) != "false":
                    fix_true.append(f"{ink.name}: {m.group(1)} = {m.group(2)}")
    if fix_true:
        print("fix switches that are not false (engine behaviour must stay live):\n  " + "\n  ".join(fix_true), file=sys.stderr)
        return 1

    files = {"dink.json": story_bytes}
    for name in COPIED:
        files[name] = (out / name).read_bytes()

    manifest = {
        "generated_by": "Scripts/sync_story.py (do not hand-edit anything in this directory)",
        "data_repo_commit": git_commit(args.data),
        "inklecate": inklecate_version(),
        "ink_version": version,
        "knots": len(knots),
        "entry_points": entries,
        "fix_switches_all_false": fixes,
        "files": {name: sha256(data) for name, data in sorted(files.items())},
    }
    manifest_path = DEST / "story_manifest.json"
    old_manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if old_manifest.get("files") == manifest["files"]:
        manifest = old_manifest  # nothing changed: keep the file byte-identical
    files["story_manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()

    changed = []
    for name, data in files.items():
        dest = DEST / name
        if not dest.exists() or dest.read_bytes() != data:
            changed.append(name)
    if args.check:
        print("story is up to date" if not changed else f"out of date: {', '.join(changed)}")
        return 0 if not changed else 1

    DEST.mkdir(parents=True, exist_ok=True)
    for name in changed:
        (DEST / name).write_bytes(files[name])
    print(f"STORY SYNC OK: {len(knots)} knots, {entries} entry points, inkVersion {version}, "
          f"{fixes} fix switches all false, data repo {manifest['data_repo_commit']}; {len(changed)} file(s) written to {DEST.relative_to(HERE)}"
          + (f" ({', '.join(changed)})" if changed else " (no change)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
