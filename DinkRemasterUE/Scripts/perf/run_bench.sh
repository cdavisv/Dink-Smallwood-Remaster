#!/usr/bin/env bash
# Run a dink.Perf.Route benchmark in the rendered game, offscreen Vulkan (no X display, nothing on screen, audio
# into SDL's dummy driver so nothing reaches a speaker). One call = one game process = ONE Unreal step: wrap it in
# Saved/Gate2Coord/unreal_turn.sh on the shared machine.
#
#   run_bench.sh editor   <project dir (has DinkRemaster.uproject)> <route file> <out dir> [extra game args]
#   run_bench.sh packaged <stage dir (package.sh output)>           <route file> <out dir> [extra game args]
#
# Writes <out dir>/bench_summary.json, bench_frames.csv, game.log, env.txt (machine load before the run).
# Env: DINK_RESX / DINK_RESY (default 1920x1080), DINK_CPUS (taskset cpu list such as 0-3: weak-CPU emulation,
#   also passes -corelimit), DINK_TRACE=1 (Unreal Insights trace <out dir>/bench.utrace: cpu,gpu,frame,loadtime,
#   bookmark + named stat events; costs frame time, so keep timing runs and trace runs apart), DINK_NOSOUND=1,
#   DINK_FIXES=0|1 (dink.Perf.Fixes from process start: 0 = master code paths), DINK_DPC=cvar=value,... (more cvars),
#   DINK_AUTODETECT=1 (let the first-run quality detection run; off by default so it never changes levels mid-route),
#   DINK_COLD=1 (first run after an install: fresh driver shader cache, no saved Vulkan pipeline cache),
#   DINK_TIMEOUT (seconds, default 2700), UE_ROOT.
# Make the route with Scripts/perf/make_route.py (add --quit) and the tables with Scripts/perf/perf_report.py.
set -uo pipefail
MODE="$1"; BASE="$(cd "$2" && pwd)"; ROUTE="$(realpath "$3")"; OUT="$4"; shift 4
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
RESX="${DINK_RESX:-1920}"; RESY="${DINK_RESY:-1080}"
DPC=r.Vulkan.Submission.UseInterruptThread=0,r.Vulkan.Submission.UseSubmissionThread=0
ENVS=()
[[ -n "${DINK_FIXES:-}" ]] && DPC+=,dink.Perf.Fixes=$DINK_FIXES
[[ -n "${DINK_DPC:-}" ]] && DPC+=,$DINK_DPC
if [[ "${DINK_COLD:-0}" == 1 ]]; then
  # first run after an install: empty driver shader cache (this process only) and no saved Vulkan pipeline cache
  rm -rf "$OUT/mesa_cold"; mkdir -p "$OUT/mesa_cold"; ENVS+=(MESA_SHADER_CACHE_DIR="$OUT/mesa_cold"); DPC+=,r.Vulkan.PipelineCacheLoad=0
fi
ARGS=(-vulkan -RenderOffscreen -windowed -forceres -ResX=$RESX -ResY=$RESY -nosplash -unattended -NoVerifyGC
  -ForceDPCVars=$DPC
  "-ExecCmds=dink.Perf.Route $ROUTE $OUT/bench" -abslog="$OUT/game.log")
[[ "${DINK_NOSOUND:-0}" == 1 ]] && ARGS+=(-nosound)
# the first-run quality detection would change levels under the route; DINK_AUTODETECT=1 lets it run (to see what it picks)
if [[ "${DINK_AUTODETECT:-0}" == 1 ]]; then DPC+=,dink.Perf.AutoDetect=1; else ARGS+=(-NoDinkAutoDetect); fi
[[ "${DINK_TRACE:-0}" == 1 ]] && ARGS+=(-trace=cpu,gpu,frame,loadtime,bookmark -statnamedevents "-tracefile=$OUT/bench.utrace")
PREFIX=()
if [[ -n "${DINK_CPUS:-}" ]]; then
  N=$(taskset -c "$DINK_CPUS" nproc); PREFIX=(taskset -c "$DINK_CPUS"); ARGS+=(-corelimit=$N)
fi
case "$MODE" in
  editor)   BIN=("$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" "$BASE/DinkRemaster.uproject" /Game/Dink/_Generated/Maps/L_Greybox_World -game -NoCompile) ;;
  packaged) BIN=("$BASE/Linux/DinkRemaster/Binaries/Linux/DinkRemaster") ;;
  *) echo "mode must be editor or packaged"; exit 2 ;;
esac
# every run starts from the settings a fresh install has: the game saves the last scalability level it ran with
# (GameUserSettings.ini), and the previous route ended on Low
case "$MODE" in
  editor)   USER_INI_DIR="$BASE/Saved/Config" ;;
  packaged) USER_INI_DIR="$BASE/Linux/DinkRemaster/Saved/Config" ;;
esac
find "$USER_INI_DIR" -name GameUserSettings.ini -exec mv {} {}.previous \; 2>/dev/null
# another rendered game (an editor game or a packaged game: lane 2 of the shared lock can start one beside ours) skews
# every number and, on a shared X display, can crash both: wait up to DINK_WAIT_GAMES seconds (default 1800) for none
games(){ ps -eo comm= | awk '$1=="UnrealEditor" || $1=="DinkRemaster"' | wc -l; }
waited=0
while [ "$(games)" != 0 ] && [ $waited -lt "${DINK_WAIT_GAMES:-1800}" ]; do sleep 10; waited=$((waited + 10)); done
echo "waited ${waited}s for other rendered games; $(games) still running at start" > "$OUT/games_before.txt"
{ date -Is; echo "mode $MODE base $BASE res ${RESX}x$RESY cpus ${DINK_CPUS:-all} args $*"; uptime;
  ps -eo pcpu,rss,comm --sort=-pcpu | head -8; free -m | head -2; } > "$OUT/env.txt"
start=$(date +%s)
# machine load while the route runs: other Unreal processes (lane-2 neighbours, owner games) skew every number
( echo "t,load1,unreal_procs,mem_avail_mb,rendered_games"; while :; do
    n=$(ps -eo comm,args | awk '$1=="UnrealEditor-Cm" || $1=="UnrealEditor" || $1=="DinkRemaster" || ($1=="dotnet" && $3 ~ /UnrealBuildTool/)' | wc -l)
    echo "$(( $(date +%s) - start )),$(cut -d' ' -f1 /proc/loadavg),$n,$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo),$(games)"; sleep 5; done ) > "$OUT/load.csv" &
SAMPLER=$!
env -u WAYLAND_DISPLAY -u DISPLAY SDL_AUDIODRIVER=dummy "${ENVS[@]}" timeout "${DINK_TIMEOUT:-2700}" "${PREFIX[@]}" "${BIN[@]}" "${ARGS[@]}" "$@" >/dev/null 2>&1
rc=$?
kill $SAMPLER 2>/dev/null
{ echo "exit $rc after $(( $(date +%s) - start ))s"; uptime; } >> "$OUT/env.txt"
echo "exit $rc after $(( $(date +%s) - start ))s"
grep -h "DINK PERF: wrote\|Fatal\|Unhandled\|Error: " "$OUT/game.log" | tail -12
rm -rf "$OUT/mesa_cold"
[[ -f "$OUT/bench_summary.json" ]] || { echo "no summary written"; exit 3; }
exit 0
