#!/usr/bin/env python3
"""Check that a packaged build contains every asset the runtime loads by string path.

The runtime binds most art (families.json, characters.json, creatures.json, environment.json, the
photoreal hero) through package paths written in Content/Dink/Data JSON or in C++ string literals.
The cook cannot see those references; an asset that is not in a cook directory is silently left out
of the package and the game falls back to a sprite card or the mannequin. Found 13 Nov 2026: the
packaged build held none of the 824 /Game/Dink/Photoreal packages.

    python3 -I Scripts/check_package_content.py [--project DIR] [--stage DIR | --listing FILE]

--stage    a Scripts/package.sh stage directory (default <project>/Saved/StagedBuilds); the IoStore
           container (.utoc) is listed with UnrealPak.
--listing  a saved `UnrealPak <utoc> -List` output instead (no engine needed).

A reference counts only when its .uasset/.umap exists under <project>/Content (test fixtures and
optional paths that were never imported are skipped). Exit 0 when every such reference is in the
package, 1 when any is missing (the first ones are listed), 2 on a usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# A package path: /Game/<segments>, optionally followed by .ObjectName or :Subobject.
PACKAGE_RE = re.compile(r"/Game/[A-Za-z0-9_][A-Za-z0-9_/\-]*")
LISTING_RE = re.compile(r'"(?:\.\./)*[^"/]+/Content/([^"]+?)\.(?:uasset|umap)"')
# Source folders whose literals are runtime references (tests and editor tools are not).
SKIP_SOURCE_PARTS = ("Tests", "Test", "Editor", "DinkImport", "DinkProbe", "DinkQA")


def packages_in_text(text: str) -> set[str]:
    out = set()
    for m in PACKAGE_RE.finditer(text):
        path = m.group(0).rstrip("/")
        # "/Game/A/B.B" -> PACKAGE_RE stops at the dot already; strip a trailing "_C" class suffix only
        # when it came after a dot, which the regex does not include, so nothing more to do.
        if path.count("/") >= 3:  # /Game/<dir>/<asset> at least
            out.add(path)
    return out


def referenced_packages(project: Path) -> dict[str, str]:
    """Package path -> first file that references it."""
    refs: dict[str, str] = {}
    data = project / "Content" / "Dink" / "Data"
    for root, _dirs, files in os.walk(data):
        for name in files:
            if not name.endswith((".json", ".csv", ".txt")):
                continue
            p = Path(root) / name
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pkg in packages_in_text(text):
                refs.setdefault(pkg, str(p.relative_to(project)))
    for src_root in [project / "Source"] + sorted((project / "Plugins").glob("*/Source")):
        for root, dirs, files in os.walk(src_root):
            dirs[:] = [d for d in dirs if d not in SKIP_SOURCE_PARTS and not d.endswith("Editor")]
            for name in files:
                if not name.endswith((".cpp", ".h")) or "Test" in name:
                    continue
                p = Path(root) / name
                text = p.read_text(encoding="utf-8", errors="replace")
                for pkg in packages_in_text(text):
                    refs.setdefault(pkg, str(p.relative_to(project)))
    return refs


def exists_on_disk(project: Path, pkg: str) -> bool:
    rel = pkg[len("/Game/"):]
    base = project / "Content" / rel
    return base.with_suffix(".uasset").is_file() or base.with_suffix(".umap").is_file()


def packaged_set(listing_text: str) -> set[str]:
    return {"/Game/" + m.group(1) for m in LISTING_RE.finditer(listing_text)}


def list_stage(stage: Path, unreal_pak: Path) -> str:
    utocs = sorted(stage.glob("Linux/*/Content/Paks/*.utoc"))
    utocs = [u for u in utocs if u.name != "global.utoc"]
    if not utocs:
        raise FileNotFoundError(f"no .utoc under {stage}/Linux/*/Content/Paks")
    text = []
    for u in utocs:
        r = subprocess.run([str(unreal_pak), str(u), "-List"], capture_output=True, text=True,
                           errors="replace", timeout=900)
        text.append(r.stdout)
        text.append(r.stderr)
    return "\n".join(text)


def check(project: Path, listing_text: str) -> tuple[list[tuple[str, str]], int, int]:
    packaged = packaged_set(listing_text)
    refs = referenced_packages(project)
    required = {pkg: src for pkg, src in refs.items() if exists_on_disk(project, pkg)}
    missing = sorted((pkg, src) for pkg, src in required.items() if pkg not in packaged)
    return missing, len(required), len(packaged)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--stage")
    ap.add_argument("--listing")
    ap.add_argument("--unreal-pak", default=os.path.expanduser(
        os.environ.get("UE_ROOT", "~/UnrealEngine/UE_5.8.4")) + "/Engine/Binaries/Linux/UnrealPak")
    args = ap.parse_args(argv)
    project = Path(args.project).resolve()
    if args.listing:
        listing_text = Path(args.listing).read_text(encoding="utf-8", errors="replace")
    else:
        stage = Path(args.stage) if args.stage else project / "Saved" / "StagedBuilds"
        try:
            listing_text = list_stage(stage, Path(args.unreal_pak))
        except (OSError, subprocess.SubprocessError) as e:
            print(f"PACKAGE CONTENT CHECK FAILED: cannot list the package: {e}")
            return 2
    missing, required, packaged = check(project, listing_text)
    if packaged == 0:
        print("PACKAGE CONTENT CHECK FAILED: the listing names no packages")
        return 2
    if missing:
        roots: dict[str, int] = {}
        for pkg, _src in missing:
            root = "/".join(pkg.split("/")[:4])
            roots[root] = roots.get(root, 0) + 1
        print(f"PACKAGE CONTENT CHECK FAILED: {len(missing)} of {required} string-path assets are not in the "
              f"package ({packaged} packages listed). By folder: "
              + ", ".join(f"{k} {v}" for k, v in sorted(roots.items(), key=lambda kv: -kv[1])))
        for pkg, src in missing[:25]:
            print(f"  missing {pkg}  (referenced by {src})")
        return 1
    print(f"PACKAGE CONTENT CHECK OK: all {required} string-path assets are in the package "
          f"({packaged} packages listed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
