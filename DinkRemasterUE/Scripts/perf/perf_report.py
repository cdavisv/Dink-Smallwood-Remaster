#!/usr/bin/env python3
"""Markdown tables from dink.Perf.Route runs (stream perf-stutter, 15 Nov 2026).

  python3 -I Scripts/perf/perf_report.py RUN_DIR [RUN_DIR ...] [--names a,b] [--out report.md]

RUN_DIR holds bench_summary.json + bench_frames.csv (Scripts/perf/run_bench.sh). With two or more runs the
level table compares them side by side (first = before). Segment labels are <level><lap>:<kind>:<stop>
(Scripts/perf/make_route.py): kind steady = standing on the screen, entry = the seconds after a teleport,
walk = walking across a screen edge into the neighbour.
"""
import argparse
import csv
import json
import os
from collections import defaultdict


def pct(values, p):
    if not values:
        return 0.0
    v = sorted(values)
    r = p * (len(v) - 1)
    lo = int(r)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (r - lo)


def mean(values):
    return sum(values) / len(values) if values else 0.0


def load(run):
    summary = json.load(open(os.path.join(run, "bench_summary.json")))
    frames = list(csv.DictReader(open(os.path.join(run, "bench_frames.csv"))))
    # routes made before the 'switch' segments: a scalability change ran at the end of the segment before it, then
    # "wait 3"; those seconds (the draw-command rebuild of the switch) are not the stop's own cost
    current, polluted = None, set()
    for line in summary.get("route", "").splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("segment "):
            current = line[8:].strip()
        elif line.startswith("scalability ") and current and ":switch:" not in current:
            polluted.add(current)
    if polluted:
        # the switch ran 3 s ("wait 3") before the segment ended: drop the segment's last 3.2 s
        end = {}
        for f in frames:
            if f["segment"] in polluted:
                end[f["segment"]] = max(end.get(f["segment"], 0.0), float(f["t"]))
        drop = {i for i, f in enumerate(frames) if f["segment"] in end and float(f["t"]) > end[f["segment"]] - 3.2}
        dropped_t = {round(float(frames[i]["t"]), 3) for i in drop}
        frames = [f for i, f in enumerate(frames) if i not in drop]
        summary["hitches"] = [h for h in summary.get("hitches", []) if round(h["t"], 3) not in dropped_t]
    for f in frames:
        for k in ("frame_ms", "game_ms", "render_ms", "rhi_ms", "gpu_ms", "gc_ms"):
            f[k] = float(f[k])
        for k in ("draws", "prims", "sync_loads", "screen"):
            f[k] = int(f[k])
        f["pending_in_view"] = int(f.get("pending_in_view") or 0)
        f["late_in_view"] = int(f.get("late_in_view_dressed") or 0)
        parts = f["segment"].split(":")
        f["lap"], f["kind"], f["stop"] = (parts + ["", "", ""])[:3]
    return summary, frames


def stats(frames):
    ms = [f["frame_ms"] for f in frames]
    if not ms:
        return None
    return {
        "frames": len(ms), "fps": 1000.0 / mean(ms), "avg": mean(ms), "p50": pct(ms, .5), "p95": pct(ms, .95),
        "p99": pct(ms, .99), "max": max(ms), "h33": sum(m > 33.4 for m in ms), "h50": sum(m > 50 for m in ms),
        "h100": sum(m > 100 for m in ms), "game": mean([f["game_ms"] for f in frames]),
        "render": mean([f["render_ms"] for f in frames]), "rhi": mean([f["rhi_ms"] for f in frames]),
        "gpu": mean([f["gpu_ms"] for f in frames]), "gpu95": pct([f["gpu_ms"] for f in frames], .95),
        "draws": mean([f["draws"] for f in frames]), "prims": mean([f["prims"] for f in frames]),
        "sync": sum(f["sync_loads"] for f in frames), "gc": sum(f["gc_ms"] > 0 for f in frames),
        "undressed": sum(f["pending_in_view"] > 0 for f in frames),
        "late": sum(f["late_in_view"] for f in frames),
    }


COLS = [("fps", "%.1f"), ("avg", "%.1f"), ("p50", "%.1f"), ("p95", "%.1f"), ("p99", "%.1f"), ("max", "%.0f"),
        ("h33", "%d"), ("h100", "%d"), ("game", "%.1f"), ("render", "%.1f"), ("rhi", "%.1f"), ("gpu", "%.1f"),
        ("draws", "%.0f"), ("prims", "%.0f"), ("sync", "%d"), ("undressed", "%d"), ("late", "%d")]
HEAD = "| fps | avg ms | p50 | p95 | p99 | max | >33 ms | >100 ms | game | render | RHI | GPU | draws | prims | sync loads | frames with an undressed screen in view | in-view screens dressed after the entry frame |"


def row(label, s):
    if not s:
        return f"| {label} |" + " |" * len(COLS)
    return f"| {label} | " + " | ".join(fmt % s[k] for k, fmt in COLS) + " |"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--names", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    names = a.names.split(",") if a.names else [os.path.basename(os.path.normpath(r)) for r in a.runs]
    data = [load(r) for r in a.runs]
    md = []
    for name, (summary, frames) in zip(names, data):
        md.append(f"## {name}\n")
        md.append(f"{summary.get('build')} build, {summary.get('rhi')} on {summary.get('adapter')}, viewport "
                  f"{summary.get('viewport', '?')}, {summary.get('cores')} cores ({summary.get('worker_threads')} workers). "
                  f"Frame times in ms; game/render/RHI are the thread times `stat unit` shows, GPU the GPU frame time.\n")
        ds = summary.get("dink_settings", {})
        keys = [k for k in sorted(ds) if any(k.lower().startswith(p) for p in ("dink.perf.", "dink.anim.", "dink.hair", "dink.world", "dink.audio", "dink.grassdensity", "dink.forest", "dink.relief"))]
        if keys:
            md.append("Dink switches at the end of the run: " + ", ".join(f"`{k}={ds[k]}`" for k in keys) + "\n")
        load_path = os.path.join(a.runs[names.index(name)], "load.csv")
        if os.path.exists(load_path):
            rows = list(csv.DictReader(open(load_path)))
            if rows:
                procs = max(int(r["unreal_procs"]) for r in rows)
                games = max(int(r.get("rendered_games") or 0) for r in rows)
                if games > 1:
                    md.append(f"**ANOTHER RENDERED GAME RAN BESIDE THIS ONE ({games} games at once): GPU and frame numbers are not clean.**\n")
                md.append(f"Machine during the run: load average {min(float(r['load1']) for r in rows):.1f}-{max(float(r['load1']) for r in rows):.1f}, "
                          f"up to {procs} Unreal processes (1 = this game alone{'; OTHER UNREAL PROCESSES RAN BESIDE IT, numbers are skewed' if procs > 1 else ''}), "
                          f"min {min(int(r['mem_avail_mb']) for r in rows)} MB available.\n")
        laps = []
        for f in frames:
            if f["lap"] not in laps:
                laps.append(f["lap"])
        md.append("### Per lap (steady = standing on each stop; entry/walk = arriving)\n")
        md.append("| lap / part " + HEAD)
        md.append("|---" * (len(COLS) + 1) + "|")
        for lap in laps:
            for kind in ("steady", "entry", "walk", "gc", "gcnat"):   # "switch" (level changes) and "shot" frames are left out
                sel = [f for f in frames if f["lap"] == lap and f["kind"] == kind]
                if sel:
                    md.append(row(f"{lap} {kind}", stats(sel)))
        md.append("")
        md.append(f"### Per stop, lap {laps[0]} and {laps[1] if len(laps) > 1 else '-'} (steady | arrival max ms, hitches > 33 ms)\n")
        md.append("| stop | lap | fps | p95 | p99 | game | render | GPU | draws | prims | arrival max | arrival >33 | arrival sync loads |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        stops = []
        for f in frames:
            if f["stop"] and f["stop"] not in stops:
                stops.append(f["stop"])
        for stop in stops:
            for lap in laps[:2]:
                s = stats([f for f in frames if f["lap"] == lap and f["stop"] == stop and f["kind"] == "steady"])
                e = stats([f for f in frames if f["lap"] == lap and f["stop"] == stop and f["kind"] in ("entry", "walk")])
                if not s:
                    continue
                md.append(f"| {stop} | {lap} | {s['fps']:.1f} | {s['p95']:.1f} | {s['p99']:.1f} | {s['game']:.1f} | {s['render']:.1f} | "
                          f"{s['gpu']:.1f} | {s['draws']:.0f} | {s['prims']:.0f} | {e['max'] if e else 0:.0f} | {e['h33'] if e else 0} | {e['sync'] if e else 0} |")
        md.append("")
        # scopes: frame-weighted over the steady segments of the first lap, and their worst single frame anywhere
        scope_ms = defaultdict(float)
        scope_max = defaultdict(float)
        scope_calls = defaultdict(float)
        nframes = 0
        for seg in summary["segments"]:
            parts = seg["label"].split(":")
            for k, v in seg.get("scopes", {}).items():
                scope_max[k] = max(scope_max[k], v["max_frame_ms"])
            if len(parts) < 2 or parts[0] != laps[0] or parts[1] != "steady":
                continue
            nframes += seg["frames"]
            for k, v in seg.get("scopes", {}).items():
                scope_ms[k] += v["ms_per_frame"] * seg["frames"]
                scope_calls[k] += v["calls_per_frame"] * seg["frames"]
        if scope_max:
            md.append(f"### Dink game-thread costs (DINK_PERF_SCOPE), lap {laps[0]} steady average and worst frame anywhere\n")
            md.append("| scope | ms per frame | calls per frame | worst frame ms |")
            md.append("|---|---|---|---|")
            for k in sorted(scope_max, key=lambda k: -scope_ms[k] / max(nframes, 1)):
                md.append(f"| {k} | {scope_ms[k] / max(nframes, 1):.3f} | {scope_calls[k] / max(nframes, 1):.1f} | {scope_max[k]:.1f} |")
            md.append("")
        hitches = sorted(summary.get("hitches", []), key=lambda h: -h["frame_ms"])
        md.append(f"### Hitches over 33 ms: {len(hitches)} (worst 25 with causes)\n")
        md.append("| segment | frame ms | game | render | GPU | GC ms | screen change | sync loads | PSO precache | top scopes | log |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for h in hitches[:25]:
            loads = h.get("sync_loads", [])
            load_txt = f"{len(loads)}: " + ", ".join(p.rsplit("/", 1)[-1] for p in loads[:4]) if loads else ""
            log = "; ".join(l.replace("|", "/")[:90] for l in h.get("log", [])[:2])
            md.append(f"| {h['segment']} | {h['frame_ms']:.0f} | {h['game_ms']:.1f} | {h['render_ms']:.1f} | {h['gpu_ms']:.1f} | "
                      f"{h['gc_ms']:.0f} | {'yes' if h['screen_changed'] else ''} | {load_txt} | {h.get('pso_precache', 0)} | "
                      f"{'; '.join(h.get('scopes', [])[:3])} | {log} |")
        md.append("")
        loads = []
        for seg in summary["segments"]:
            for p in seg.get("sync_load_packages", []):
                if p not in loads:
                    loads.append(p)
        md.append(f"### Synchronous package loads during the route: {len(loads)} packages\n")
        for p in loads[:60]:
            md.append(f"- `{p}`")
        md.append("")
    if len(data) > 1:
        md.append("## Comparison (steady frames of every lap, per lap)\n")
        md.append("| lap | " + " | ".join(f"{n} fps / p99 / GPU" for n in names) + " |")
        md.append("|---" * (len(names) + 1) + "|")
        laps = []
        for _, frames in data:
            for f in frames:
                if f["lap"] not in laps:
                    laps.append(f["lap"])
        for lap in laps:
            cells = []
            for _, frames in data:
                s = stats([f for f in frames if f["lap"] == lap and f["kind"] == "steady"])
                cells.append(f"{s['fps']:.1f} / {s['p99']:.1f} / {s['gpu']:.1f}" if s else "-")
            md.append(f"| {lap} | " + " | ".join(cells) + " |")
        md.append("")
        md.append("| arrivals (entry + walk) | " + " | ".join(f"{n} max ms / >33 ms / sync loads" for n in names) + " |")
        md.append("|---" * (len(names) + 1) + "|")
        for lap in laps:
            cells = []
            for _, frames in data:
                s = stats([f for f in frames if f["lap"] == lap and f["kind"] in ("entry", "walk")])
                cells.append(f"{s['max']:.0f} / {s['h33']} / {s['sync']}" if s else "-")
            md.append(f"| {lap} | " + " | ".join(cells) + " |")
        md.append("")
    text = "\n".join(md)
    if a.out:
        open(a.out, "w").write(text)
        print(f"wrote {a.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
