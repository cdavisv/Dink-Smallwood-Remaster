#!/usr/bin/env python3
"""GPU pass costs per stop and level from a dink.Perf.Route run made with make_route.py --gpu-csv.

  python3 -I Scripts/perf/gpu_breakdown.py RUN_DIR CSV_DIR [--top 14] [--out gpu.md]

RUN_DIR holds game.log (run_bench.sh); CSV_DIR is the game's Saved/Profiling/CSV. Each `csvprofile stop` in the log is
matched to the segment it ran in and to the CSV file written then; the table lists, per stop and level, the mean ms of
the GPU passes (category GPU, `r.GPUCsvStatsEnabled 1`), largest first, plus the frame and GPU totals.
"""
import argparse
import csv
import os
import re
from collections import defaultdict


def mean_columns(path):
    rows = list(csv.reader(open(path, encoding="utf-8", errors="replace")))
    if len(rows) < 3:
        return {}, 0
    head = rows[0]
    # UE CSV profiler: header row, one row per frame (first column = events, often empty), the header again and a
    # metadata row at the end
    data = [r for r in rows[1:] if len(r) == len(head) and r != head and not r[0].startswith("[")]
    out = {}
    for i, name in enumerate(head):
        vals = []
        for r in data:
            try:
                vals.append(float(r[i]))
            except ValueError:
                pass
        if vals:
            out[name] = sum(vals) / len(vals)
    return out, len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("csvdir")
    ap.add_argument("--top", type=int, default=14)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    seg, labels = None, []
    for line in open(os.path.join(a.run, "game.log"), errors="replace"):
        m = re.search(r"DINK PERF: segment (\S+)", line)
        if m:
            seg = m.group(1)
        if "DINK PERF: exec csvprofile stop" in line and seg:
            labels.append(seg)
    files = sorted((os.path.join(a.csvdir, f) for f in os.listdir(a.csvdir) if f.endswith(".csv")), key=os.path.getmtime)[-len(labels):] if labels else []
    md = ["| stop | level | frame ms | GPU total ms | top GPU passes (ms) |", "|---|---|---|---|---|"]
    per_pass = defaultdict(dict)
    for label, path in zip(labels, files):
        cols, n = mean_columns(path)
        lap, _, stop = (label.split(":") + ["", ""])[:3]
        gpu = {k.split("/", 1)[1]: v for k, v in cols.items() if k.startswith("GPU/") and k not in ("GPU/Total", "GPU/Idle", "GPU/Unaccounted")}
        total = cols.get("GPUTime", cols.get("GPU/Total", sum(gpu.values())))
        top = sorted(gpu.items(), key=lambda kv: -kv[1])[: a.top]
        md.append(f"| {stop} | {lap} | {cols.get('FrameTime', 0):.1f} | {total:.1f} | " + ", ".join(f"{k} {v:.2f}" for k, v in top) + " |")
        for k, v in gpu.items():
            per_pass[k][f"{stop}:{lap}"] = v
    text = "\n".join(md) + "\n"
    if a.out:
        open(a.out, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
