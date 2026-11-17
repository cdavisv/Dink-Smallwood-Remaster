#!/usr/bin/env python3
"""Write a dink.Perf.Route benchmark route (stream perf-stutter, 15 Nov 2026).

  python3 -I Scripts/perf/make_route.py out.txt                       # standard route, Epic lap x2 + High/Medium/Low laps
  python3 -I Scripts/perf/make_route.py out.txt --levels 3            # one scalability level only
  python3 -I Scripts/perf/make_route.py out.txt --quick               # shorter waits (smoke test)
  python3 -I Scripts/perf/make_route.py out.txt --extra "r.ScreenPercentage 50"   # console lines before the laps

The standard stops are the heaviest screen of each kind in the 644-screen visual sweep
(Docs/Verification/VisualSweep_15Nov2026/detectors.csv `prims`) plus the busiest combat screen of
placements.csv: each stop is a teleport ('entry', cold the first time), a steady stretch, and one walk across
a screen edge into the neighbour (real play: the neighbour is dressed by the same code path as a walk).
Lap 1 shows first-use costs (shaders, PSOs, mesh/texture streaming, dressing); lap 2 the same screens warm.
"""
import argparse
from pathlib import Path

# (label, screen, x, y, walk target or None). Map pixels: 600 x 400 per screen; x > 600 is the east neighbour,
# y < 0 the north one (screen - 32).
STOPS = [
    ("stonebrook_interior_001", 1, 300, 220, None),
    ("stonebrook_exterior_438", 438, 300, 200, (660, 200)),     # densest settlement -> 439
    ("forest_312", 312, 300, 200, (660, 200)),                  # dense pine forest -> 313
    ("coast_650", 650, 300, 200, (660, 200)),                   # south coast, water + shore (heaviest wilderness) -> 651
    ("town_terris_530", 530, 300, 200, (300, -60)),             # Terris town -> 498
    ("cave_098", 98, 300, 200, None),                           # Stonebrook cave
    ("dungeon_579", 579, 300, 200, None),                       # terris_wilds dungeon, 9 lights
    ("combat_pillbugs_527", 527, 300, 200, None),               # 10 en-pill pillbugs chase the hero
]
# extra stops a route can pick with --stops (not in the standard lap)
EXTRA_STOPS = [
    ("willows_446", 446, 300, 200, None),                       # willow-heavy screen: family-art trees in the wind
]
HARD = Path(__file__).resolve().parents[2] / "Content/Dink/Data/Gameplay/Hardness"


def hardness(screen):
    """The screen's 1997 hardness (vision 0) as rows of 600 ints, 0 = walkable; None when absent (same decoding as
    Scripts/check_player_blockers.py)."""
    f = HARD / f"SCR_{screen:03d}.txt"
    if not f.exists():
        return None
    rows, started = [], False
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("vision"):
            if started:
                break
            started = line.split()[1] == "0"
            continue
        if line.startswith("tiles"):
            break
        if not started:
            continue
        row = []
        for t in line.split():
            if ":" in t:
                n, c = t.split(":")
                row += [int(c)] * int(n)
            else:
                row += [0] * int(t)
        rows.append(row)
    return rows[:400] if len(rows) >= 400 else None


def free(grid, x, y, r):
    """True when every pixel within r of (x, y) is walkable."""
    if grid is None:
        return True
    for yy in range(max(0, y - r), min(400, y + r + 1), 3):
        for xx in range(max(0, x - r), min(600, x + r + 1), 3):
            if grid[yy][xx]:
                return False
    return True


def spawn_point(screen, want=(300, 200), r=22):
    """The walkable point nearest to `want` with a clear disc of r px (teleports fail into hardness)."""
    g = hardness(screen)
    best = None
    for y in range(r, 400 - r, 6):
        for x in range(r, 600 - r, 6):
            d = (x - want[0]) ** 2 + (y - want[1]) ** 2
            if (best is None or d < best[0]) and free(g, x, y, r):
                best = (d, x, y)
    return (best[1], best[2]) if best else want


def crossing(screen, prefer="east", r=18):
    """(start, target) map pixels for a straight walk over one edge of the screen (preferred direction first, then
    the others) on a band that is walkable on both sides; None when no edge has one."""
    here = hardness(screen)
    if here is None:
        return None
    dirs = [prefer] + [d for d in ("east", "north", "west", "south") if d != prefer]
    for d in dirs:
        other = {"east": screen + 1, "west": screen - 1, "north": screen - 32, "south": screen + 32}[d]
        there = hardness(other)
        if there is None:
            continue
        horizontal = d in ("east", "west")
        span = 400 if horizontal else 600
        for v in sorted(range(r, span - r, 4), key=lambda v: abs(v - span // 2)):
            if d == "east":
                ok = all(free(here, x, v, r) for x in range(520, 600 - r, 8)) and all(free(there, x, v, r) for x in range(r, 90, 8))
                if ok: return (540, v), (680, v)
            elif d == "west":
                ok = all(free(here, x, v, r) for x in range(r, 80, 8)) and all(free(there, x, v, r) for x in range(510, 600 - r, 8))
                if ok: return (60, v), (-80, v)
            elif d == "north":
                ok = all(free(here, v, y, r) for y in range(r, 80, 8)) and all(free(there, v, y, r) for y in range(320, 400 - r, 8))
                if ok: return (v, 60), (v, -80)
            else:
                ok = all(free(here, v, y, r) for y in range(320, 400 - r, 8)) and all(free(there, v, y, r) for y in range(r, 80, 8))
                if ok: return (v, 340), (v, 480)
    return None


LEVELS = {-1: "default", 3: "epic", 2: "high", 1: "medium", 0: "low"}   # -1: the settings a fresh install starts with


GPU_CSV = False   # --gpu-csv: one csvprofile capture (GPU pass timings) around each steady stretch


def lap(out, tag, steady, entry, walk, shots=None):
    for label, screen, x, y, target in STOPS:
        x, y = spawn_point(screen, (x, y))
        out.append(f"segment {tag}:entry:{label}")
        out.append(f"goto {screen} {x} {y}")
        out.append(f"wait {entry}")
        out.append(f"segment {tag}:steady:{label}")
        if GPU_CSV:
            out.append("csvprofile start")
        out.append(f"wait {steady}")
        if GPU_CSV:
            out.append("csvprofile stop")
        if shots:
            out.append(f"segment {tag}:shot:{label}")
            out.append(f"shot {shots}/{tag}_{label}.png")
            out.append("wait 1")
        if target:
            # walk across the screen edge: teleport just inside it on a band walkable on both sides, then walk over
            cross = crossing(screen, "east" if target[0] > 600 else "north")   # else whichever edge is open
            if cross:
                (sx, sy), (tx, ty) = cross
                out.append(f"segment {tag}:walk:{label}")
                out.append(f"goto {screen} {sx} {sy}")
                out.append("wait 1")
                out.append(f"walk {tx} {ty} 6")
                out.append(f"wait {entry}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--levels", default="-1,3,2,1,0", help="comma list of scalability levels (-1 = untouched start settings); the first gets two laps")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--extra", action="append", default=[], help="console line run before the laps (repeatable)")
    ap.add_argument("--quit", action="store_true", help="quit the game when the route ends")
    ap.add_argument("--gc-test", action="store_true", help="after the first level's laps: natural GCs every 6 s, full then incremental")
    ap.add_argument("--gpu-csv", action="store_true", help="per steady stretch: a csvprofile capture with GPU pass timings (Scripts/perf/gpu_breakdown.py)")
    ap.add_argument("--csv", action="store_true", help="csvprofile start/stop around the laps (Saved/Profiling/CSV)")
    ap.add_argument("--stops", default="", help="comma list of stop labels to keep (default: all)")
    ap.add_argument("--shots", default="", help="directory: one screenshot per stop on the first lap of each level")
    ap.add_argument("--level-extra", action="append", default=[],
                    help="LEVEL:NAME:cvar value;cvar value  - an extra lap at scalability LEVEL with these console lines (proposals)")
    a = ap.parse_args()
    steady, entry, walk = (3, 2, 4) if a.quick else (10, 4, 8)
    out = ["# dink.Perf.Route standard route (Scripts/perf/make_route.py)", "t.MaxFPS 0", "r.VSync 0",
           "dink.ScreenInfo 0", "wait 25"]
    out += a.extra
    global GPU_CSV
    GPU_CSV = a.gpu_csv
    if GPU_CSV:
        out += ["r.GPUCsvStatsEnabled 1", "r.GPUStatsEnabled 1"]
    if a.stops:
        keep = set(a.stops.split(","))
        STOPS[:] = [s for s in STOPS + EXTRA_STOPS if s[0] in keep]
    if a.csv:
        out.append("csvprofile start")
    levels = [int(v) for v in a.levels.split(",") if v != ""]
    for i, level in enumerate(levels):
        name = LEVELS.get(level, f"sg{level}")
        # the switch itself rebuilds every mesh draw command (~100 ms): its own segment, never counted as a stop
        out.append(f"segment {name}:switch:level")
        if level >= 0:
            out.append(f"scalability {level}")
        out.append("wait 3")
        name = LEVELS.get(level, f"sg{level}")
        lap(out, f"{name}1", steady, entry, walk, a.shots or None)
        if i == 0:
            lap(out, f"{name}2", steady, entry, walk)
            # a forced full garbage collection on the last stop: its cost is the periodic GC hitch of a long session
            for n in range(2):
                out.append(f"segment {name}2:gc:forced{n}")
                out.append("obj gc")
                out.append("wait 2")
            if a.gc_test:
                # natural (time-based) collections every 6 s on a dressed outdoor screen: the engine's default reachability
                # pass, then the incremental one (gc.AllowIncrementalReachability, experimental in 5.8)
                out += ["goto 438 300 200", "wait 4", f"segment {name}2:gcnat:full", "gc.TimeBetweenPurgingPendingKillObjects 6", "wait 20",
                        f"segment {name}2:gcnat:incremental", "gc.AllowIncrementalReachability 1", "gc.AllowIncrementalGather 1",
                        "gc.IncrementalReachabilityTimeLimit 0.003", "wait 20",
                        "gc.AllowIncrementalReachability 0", "gc.AllowIncrementalGather 0", "gc.TimeBetweenPurgingPendingKillObjects 61.1"]
    for spec in a.level_extra:
        level, name, lines = spec.split(":", 2)
        out.append(f"segment {name}:switch:level")
        out.append(f"scalability {level}")
        out += [l.strip() for l in lines.split(";") if l.strip()]
        out.append("wait 3")
        lap(out, f"{name}1", steady, entry, walk, a.shots or None)
    if a.csv:
        out.append("csvprofile stop")
        out.append("wait 3")
    out.append("end")
    if a.quit:
        out.append("quit")
    open(a.out, "w").write("\n".join(out) + "\n")
    print(f"wrote {a.out}: {len(out)} lines, levels {levels}")


if __name__ == "__main__":
    main()
