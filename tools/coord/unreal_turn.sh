#!/usr/bin/env bash
# One Unreal step per call, at most TWO at a time on this machine (v5, 25 Nov 2026; v2 15 Nov, v3 GPU lock 16 Nov, v4 Oops guard 19 Nov).
# Usage: unreal_turn.sh <command> [args...]   (ONE Unreal step: a build, an import, a test run, a capture, a package)
#        unreal_turn.sh --status              (print the queue, the locks and the Unreal processes this script counts)
# Installed copy: DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh (git-ignored); source: tools/coord/unreal_turn.sh.
# Install a new version with tools/coord/install_unreal_turn.sh (it replaces the file by rename, so running callers keep
# reading the old one: never edit the installed file in place, bash reads a running script as it goes).
#
# Lane 1 (MAIN, $LOCK): every kind of step; waits until no Unreal process runs (v1 behaviour; v1 callers queue here).
# Lane 2 ($LOCK2): only non-build steps (not build.sh / package.sh / UBT / RunUAT), and only while a MAIN step is
#   actually running (so a MAIN waiter, which needs zero Unreal processes, is never starved), with >= 10 GB available
#   and the owner's game (DinkRemaster-master) not running.
# EXCLUSIVE steps (v5): package.sh, run_packaged_tests.sh, or DINK_EXCLUSIVE=1 in the environment. They take MAIN, then
#   lane 2 (waiting for a running lane-2 step to end) and the GPU lock, wait until NO Unreal process runs, and hold all
#   three until they end: nothing else starts beside a packaged run (package.sh's own busy check refuses any other
#   UnrealEditor-Cmd, and v4 let a build-lane step in beside one lane-2 step).
# Counted as a running Unreal process (v5): UnrealEditor(-Cmd), the DinkRemaster game, UnrealBuildTool, AutomationTool
#   (dotnet AutomationTool.dll), UnrealPak, and RunUAT.sh. RunUAT under package.sh's bwrap wrapper is exec'd directly, so
#   its process name is "RunUAT.sh", not "bash": v4 did not count it, nor the dotnet AutomationTool it starts.
# Queue (v5): a waiter whose line vanished from the queue file (removed, rewritten, PID reuse) puts it back with its
#   ORIGINAL time, and the queue is kept in time order, so it keeps its place.
#
# KERNEL OOPS GUARD (19 Nov, v4): on 16 Nov 23:15 an Oops in the amdgpu driver left the kernel running damaged; a file was misread
# at 23:34 and the machine froze at 00:39. Once the kernel has oopsed (taint flag D, bit 128) nothing it does is trustworthy:
# refuse every step until the machine is rebooted.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ -n "$DINK_COORD_DIR" ]; then COORD="$DINK_COORD_DIR"
elif [ -f "$HERE/COMMON_RULES.md" ]; then COORD="$HERE"
else COORD="$(cd "$HERE/../.." && pwd)/DinkRemasterUE/Saved/Gate2Coord"; fi
LOCK=${DINK_TURN_LOCK:-/tmp/dink-unreal-turn.lock}
LOCK2=${DINK_TURN_LOCK2:-/tmp/dink-unreal-turn2b.lock}
GPULOCK=${DINK_TURN_GPULOCK:-/tmp/dink-gpu-turn.lock}
Q=${DINK_TURN_QUEUE:-/tmp/dink-unreal-turn.queue}
QL=$Q.lock
procs(){ ps -eo pid=,comm=,args= | awk '$2=="UnrealEditor-Cm" || $2=="UnrealEditor" || $2=="DinkRemaster" || $2=="UnrealPak" || $2=="RunUAT.sh" ||
  ($2=="dotnet" && ($4 ~ /(UnrealBuildTool|AutomationTool)\.dll$/ || $3 ~ /(UnrealBuildTool|AutomationTool)\.dll$/)) ||
  ($2 ~ /^(bash|sh)$/ && ($4 ~ /RunUAT\.sh$/ || $3 ~ /RunUAT\.sh$/))'; }
cnt(){ procs | wc -l; }
if [ "$1" = "--status" ]; then
  echo "queue ($Q):"; [ -f "$Q" ] && while read -r pid ts rest; do printf '  %s %s %s %s\n' "$pid" "$(date -d @"$ts" +%H:%M:%S 2>/dev/null)" "$(kill -0 "$pid" 2>/dev/null && echo live || echo dead)" "$(echo "$rest" | cut -c1-100)"; done < "$Q"
  for l in "$LOCK" "$LOCK2" "$GPULOCK"; do ( flock -n 3 && echo "free  $l" || echo "HELD  $l" ) 3>>"$l"; done
  echo "counted Unreal processes: $(cnt)"; procs | cut -c1-160 | sed 's/^/  /'; exit 0
fi
if [ $(( $(cat /proc/sys/kernel/tainted 2>/dev/null || echo 0) & 128 )) -ne 0 ]; then
  echo "unreal_turn: the kernel has logged an Oops this boot (tainted D). STOP: do not run Unreal, Blender or git writes; tell the coordinator; the machine needs a reboot." >&2
  echo "- $(date '+%d %b %Y, %H:%M') (unreal_turn guard): kernel tainted D (an Oops happened this boot); step refused: $(echo "$*" | cut -c1-80). REBOOT NEEDED." >> "$COORD/COMMON_RULES.md"
  exit 97
fi
owner_game(){ ps -eo args | grep -v -e grep -e unreal_turn | grep -q 'DinkRemaster-master'; }
memok(){ [ "$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)" -ge 10 ]; }
isbuild=0
case "$*" in *build.sh*|*package.sh*|*UnrealBuildTool*|*RunUAT*|*Build.sh*|*run_packaged_tests.sh*) isbuild=1;; esac
excl=0
case "$*" in *package.sh*|*run_packaged_tests.sh*) excl=1;; esac
[ "$DINK_EXCLUSIVE" = 1 ] && { excl=1; isbuild=1; }
T0=$(date +%s)
LINE="$$ $T0 $*"
enqueue(){ ( flock 7; echo "$LINE" >> "$Q"; sort -s -n -k2,2 "$Q" > "$Q.tmp.$$" && mv -f "$Q.tmp.$$" "$Q" ) 7>"$QL"; }
dequeue(){ ( flock 7; if [ -f "$Q" ]; then grep -v "^$$ " "$Q" > "$Q.tmp.$$"; mv -f "$Q.tmp.$$" "$Q"; fi ) 7>"$QL"; }
# Our line must be in the queue while we wait; if it is gone, put it back at its original time (v5).
keepline(){ grep -q "^$$ " "$Q" 2>/dev/null && return; enqueue; echo "$(date '+%d %b %H:%M:%S') pid $$ queue line restored: $(echo "$LINE" | cut -c1-100)" >> "$Q.events"; }
myturn(){ local pid rest; keepline; while read -r pid rest; do if kill -0 "$pid" 2>/dev/null; then [ "$pid" = "$$" ]; return; fi; done < "$Q"; return 0; }
# Display guard (16 Nov): a step that uses an X display (DISPLAY in its environment, or DISPLAY=:N / --private-display :N
# in its arguments) waits until no Unreal/Dink game already runs on that display (two games on one Xvfb crashed together).
MYDISP="$DISPLAY"; for a in "$@"; do case "$a" in DISPLAY=:*) MYDISP="${a#DISPLAY=}";; esac; done
prev=""; for a in "$@"; do [ "$prev" = "--private-display" ] && MYDISP="$a"; prev="$a"; done
disp_busy(){ [ -z "$MYDISP" ] && return 1; local p; for p in $(pgrep -x 'UnrealEditor|UnrealEditor-Cm|DinkRemaster'); do tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -qx "DISPLAY=$MYDISP" && return 0; done; return 1; }
mainfree(){ disp_busy && return 1; c=$(cnt); [ "$c" = 0 ] && return 0; if [ "$c" -le 1 ] && memok && ! flock -n 8 2>/dev/null; then return 0; fi; flock -u 8 2>/dev/null; return 1; }
# GPU lock (16 Nov, v3): both crashes of 16 Nov (08:06, 13:00) were RX 6800 ring timeouts with Unreal rendering; the reset takes the
# desktop session and every agent down. At most ONE GPU-rendering step at a time, in whichever lane. Builds, test.sh and
# import_greybox.sh run with -nullrhi and do not take it. Override: DINK_GPU=0 (no GPU) / DINK_GPU=1 (GPU) in the environment.
isgpu=1; case "$*" in *build.sh*|*package.sh*|*UnrealBuildTool*|*RunUAT*|*Build.sh*|*Scripts/test.sh*|*/test.sh*|*import_greybox.sh*) isgpu=0;; esac
case "$1" in test.sh|./test.sh) isgpu=0;; esac
[ -n "$DINK_GPU" ] && isgpu=$DINK_GPU
[ $excl = 1 ] && isgpu=1   # an exclusive step also keeps every rendered step (and gpu_turn.sh) out
run(){ dequeue; if [ "$isgpu" = 1 ]; then exec 7>"$GPULOCK"; flock 7; fi; "$@" 7>&- 8>&- 9>&-; rc=$?; exec 9>&- 8>&- 7>&- 2>/dev/null; exit $rc; }
exec 9>"$LOCK"
exec 8>"$LOCK2"
enqueue; trap dequeue EXIT
if [ $excl = 1 ]; then
  until myturn; do sleep 1; done; flock 9; flock 8; until ! disp_busy && [ "$(cnt)" = 0 ]; do keepline; sleep 1; done; run "$@"
fi
if [ $isbuild = 1 ]; then
  until myturn; do sleep 1; done; flock 9; until mainfree; do keepline; sleep 0.5; done; run "$@"
fi
while :; do
  if myturn && flock -n 9; then
    until mainfree; do keepline; sleep 0.5; done; exec 8>&-; run "$@"
  fi
  if flock -n 8; then
    # MAIN is held by someone (we failed to get it). Start only while a MAIN step is running.
    if [ "$(cnt)" -ge 1 ] && memok && ! owner_game && ! disp_busy; then sleep 1
      if [ "$(cnt)" -ge 1 ] && memok && ! disp_busy && ! flock -n 9 2>/dev/null; then exec 9>&-; run "$@"; fi
      # got MAIN after all (it was free): use it
      if myturn && flock -n 9 2>/dev/null; then flock -u 8; until mainfree; do keepline; sleep 0.5; done; exec 8>&-; run "$@"; fi
    fi
    flock -u 8
  fi
  sleep 1
done
