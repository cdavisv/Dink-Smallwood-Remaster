#!/usr/bin/env python3
"""Bring the original game's per-frame and per-placement gameplay data into the project.

Usage:
    python3 Scripts/sync_gameplay_data.py [--data <path to Dink-Smallwood-Remaster>] [--check]

Reads the data repo's tools/dinkex/out (sequences.json, screens/SCR_nnn.json; run
`cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out` there if missing) and
writes into Content/Dink/Data/Gameplay/ (staged like the story by DirectoriesToAlwaysStageAsUFS=Dink/Data):

    frames.csv        seq,frame,delay_ms,special,left,top,right,bottom,loop,empty,width,height
                      every frame of dink.ini: animation delay, the "special" (hit) flag that makes
                      a sprite's attack land (dink.cpp D:16971), and the picture's hardbox relative to
                      the sprite position, which the hit, touch, push and missile tests use (getpic());
                      loop = SET_FRAME_FRAME <seq> <frame> -1 (the animation wraps to frame 1 there),
                      empty = a slot with no picture (the animation ends there, like the slot after the last);
                      width/height = the picture's size (getpic()'s box, which the pig and bounce brains
                      keep inside the screen).
    Hardness/SCR_nnn.txt  the screen's 600x400 hardness map as the engine builds it on load (tools/dinkex
                      hardness/SCR_nnn[_vV].png + _owner.png), one block per &vision value: tile codes 1
                      (solid), 2 (low: missiles and flyers cross), 3 (other), and 100+index where placement
                      `index` stamped its hardbox (the engine's own value, D:6136; warp boxes included). The
                      brains (walkers, missiles) test their path against it. Format: "vision V" then 400
                      rows of run-length tokens, "N" = N pixels of 0, "N:C" = N pixels of code C.
                      A last block "tiles" (same format) is the tile layer alone (fill_whole_hard, D:654,
                      from bin/dink/hard.dat through tools/dinkex's HardDat; tile values above 3 read 3):
                      what draw_hard_sprite (fill_hardxy, D:597) and draw_hard_map put back under a hardbox.
    placements.csv    one row per map.dat placement: origin (S001_P26), type (0 background, 1 live
                      sprite, 2 hardness only), engine x (with the 20 px bar) and y, seq/frame, size,
                      vision, and the sprite fields place_sprites_game copies onto a live sprite
                      (brain, script, hitpoints, strength, defense, exp, nohit, touch_damage, speed,
                      timing, base_walk/idle/attack/hit/die, hard, sound, que: the draw order that also
                      orders the hardbox stamps, D:5966 and fill_back_sprites D:6832).
    screens.csv       screen,base_script: the script whose `main` runs when the screen loads (headless
                      screen entry uses it when there is no ADinkScreenVolume)
    gameplay_manifest.json   data repo commit and sha256 of each file

Deterministic: same input, byte-identical output; unchanged files are not rewritten.
--check: exit 1 if the project copy is out of date, write nothing. The game never reads the data repo.
"""
from __future__ import annotations

from remaster_paths import default_data_repo

import argparse
import csv
import hashlib
import io
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
DEST = HERE / "Content" / "Dink" / "Data" / "Gameplay"

FRAME_COLS = ["seq", "frame", "delay_ms", "special", "left", "top", "right", "bottom", "loop", "empty", "width", "height"]
PLACEMENT_COLS = ["origin", "screen", "index", "type", "x", "y", "seq", "frame", "size", "vision", "brain",
                  "script", "hitpoints", "strength", "defense", "exp", "nohit", "touch_damage", "speed", "timing",
                  "base_walk", "base_idle", "base_attack", "base_hit", "base_die", "hard", "sound", "que"]


def git_commit(repo: pathlib.Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%h"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", "tools/dinkex"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return out + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def to_csv(cols, rows) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode()


def frames(dinkex: pathlib.Path):
    seqs = json.loads((dinkex / "sequences.json").read_text())["sequences"]
    rows = []
    for q in sorted(seqs, key=lambda q: q["seq"]):
        for f in q["frames"]:
            hb = f.get("hardbox") or {"left": 0, "top": 0, "right": 0, "bottom": 0}
            rows.append({"seq": q["seq"], "frame": f["frame"], "delay_ms": f.get("delay_ms", 0) or 0,
                         "special": 1 if f.get("is_hit_frame") or f.get("special") else 0,
                         "left": hb["left"], "top": hb["top"], "right": hb["right"], "bottom": hb["bottom"],
                         "loop": 1 if f.get("loop_to_start") else 0, "empty": 1 if f.get("empty") else 0,
                         "width": f.get("width") or 0, "height": f.get("height") or 0})
    return rows


def screens(dinkex: pathlib.Path):
    rows = []
    for path in sorted((dinkex / "screens").glob("SCR_*.json")):
        d = json.loads(path.read_text())
        rows.append({"screen": d["screen"], "base_script": (d.get("base_script") or "").lower()})
    rows.sort(key=lambda r: r["screen"])
    return rows


def rle_rows(codes):
    """400 lines of run-length tokens ("N" free, "N:C" code C) for a 400x600 code array."""
    import numpy as np
    lines = []
    for row in codes:
        edges = np.flatnonzero(np.diff(row)) + 1
        starts = np.concatenate(([0], edges))
        ends = np.concatenate((edges, [len(row)]))
        lines.append(" ".join(f"{e - b}" if row[b] == 0 else f"{e - b}:{row[b]}" for b, e in zip(starts, ends)))
    return lines


def tile_layers(data: pathlib.Path, dinkex: pathlib.Path):
    """{screen stem: 400x600 int array}: fill_whole_hard's tile layer (D:654-681) of every screen, without placements.

    Built with the data repo's own reader (tools/dinkex/dinkex/hard.py: HardDat, build_tile_layer) from bin/dink/hard.dat
    and the screen's tiles (num, althard) in tools/dinkex/out/screens; values above 3 read 3, as in the hardness PNGs."""
    import numpy as np
    sys.path.insert(0, str(data / "tools" / "dinkex"))
    try:
        from dinkex import hard as hardmod
    finally:
        sys.path.pop(0)
    hard_dat = hardmod.HardDat.from_file(str(data / "bin" / "dink" / "hard.dat"))
    out = {}
    for path in sorted((dinkex / "screens").glob("SCR_*.json")):
        d = json.loads(path.read_text())
        tiles = [{"num": t["num"], "althard": t["althard"]} for t in sorted(d["tiles"], key=lambda t: t["index"])]
        hit, _skipped = hardmod.build_tile_layer(hard_dat, tiles)
        out[path.stem] = np.where(hit > 3, 3, hit).astype(np.int32)
    return out


def hardness(dinkex: pathlib.Path, tiles=None):
    """{"Hardness/SCR_nnn.txt": bytes}: every screen's hardness map per vision value, run-length coded, then its tile layer."""
    import numpy as np
    from PIL import Image
    out = {}
    hard = dinkex / "hardness"
    for base in sorted(hard.glob("SCR_[0-9][0-9][0-9].png")):
        stem = base.stem
        variants = [(0, base)] + sorted(
            (int(p.stem.split("_v")[1]), p) for p in hard.glob(stem + "_v*.png") if not p.stem.endswith("_owner"))
        lines = [f"# {stem} hardness (Scripts/sync_gameplay_data.py from tools/dinkex/out/hardness; never hand-edit)"]
        for vision, path in variants:
            codes = np.array(Image.open(path)).astype(np.int32)
            owner = np.array(Image.open(path.with_name(path.stem + "_owner.png"))).astype(np.int32)
            stamped = codes >= 100
            if tiles is not None and stem in tiles and not np.array_equal(codes[~stamped], tiles[stem][~stamped]):
                sys.exit(f"{stem} vision {vision}: the tile layer differs from the hardness map outside the hardboxes")
            codes[stamped] = 100 + owner[stamped]
            lines.append(f"vision {vision}")
            lines.extend(rle_rows(codes))
        if tiles is not None and stem in tiles:
            lines.append("tiles")
            lines.extend(rle_rows(tiles[stem]))
        out[f"Hardness/{stem}.txt"] = ("\n".join(lines) + "\n").encode()
    return out


def placements(dinkex: pathlib.Path):
    rows = []
    for path in sorted((dinkex / "screens").glob("SCR_*.json")):
        d = json.loads(path.read_text())
        for p in d["placements"]:
            row = {k: p.get(k, 0) for k in PLACEMENT_COLS}
            row.update({"origin": p["id"], "screen": d["screen"], "index": p["index"],
                        "script": (p.get("script") or "").lower()})
            rows.append(row)
    rows.sort(key=lambda r: (r["screen"], r["index"]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=pathlib.Path, default=default_data_repo(HERE))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    dinkex = args.data / "tools" / "dinkex" / "out"
    if not (dinkex / "sequences.json").exists():
        sys.exit(f"{dinkex}/sequences.json missing: run `cd {args.data}/tools/dinkex && python3 -m dinkex extract "
                 f"--data ../../bin/dink --out out` first")
    f_rows, p_rows, s_rows = frames(dinkex), placements(dinkex), screens(dinkex)
    files = {"frames.csv": to_csv(FRAME_COLS, f_rows), "placements.csv": to_csv(PLACEMENT_COLS, p_rows),
             "screens.csv": to_csv(["screen", "base_script"], s_rows)}
    files.update(hardness(dinkex, tile_layers(args.data, dinkex)))
    manifest = {"source": "tools/dinkex/out (sequences.json, screens/, hardness/); bin/dink/hard.dat (tile layers)",
                "data_repo_commit": git_commit(args.data),
                "files": {n: hashlib.sha256(b).hexdigest() for n, b in sorted(files.items())},
                "counts": {"frames": len(f_rows), "placements": len(p_rows), "screens": len(s_rows),
                           "hardness_files": sum(1 for n in files if n.startswith("Hardness/"))}}
    manifest_path = DEST / "gameplay_manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if old.get("files") == manifest["files"]:
        manifest = old
    files["gameplay_manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    changed = [n for n, b in files.items() if not (DEST / n).exists() or (DEST / n).read_bytes() != b]
    if args.check:
        print("GAMEPLAY DATA " + ("OUT OF DATE: " + ", ".join(changed) if changed else "CURRENT"))
        return 1 if changed else 0
    DEST.mkdir(parents=True, exist_ok=True)
    for n in changed:
        (DEST / n).parent.mkdir(parents=True, exist_ok=True)
        (DEST / n).write_bytes(files[n])
    print(f"GAMEPLAY DATA SYNC OK: {len(f_rows)} frames, {len(p_rows)} placements, data repo "
          f"{manifest['data_repo_commit']}; {len(changed)} file(s) written to {DEST.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
