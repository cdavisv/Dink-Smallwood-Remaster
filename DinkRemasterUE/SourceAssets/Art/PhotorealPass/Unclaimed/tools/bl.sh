#!/bin/bash
# Run one Blender batch job at a time (shared machine: one `blender -b -t 4` per agent).
# usage: tools/bl.sh build_<family>.py [args...]
# HOME points at a scratch folder so no user path ends up inside the saved .blend files.
# Waits (up to 30 min) until at least 6 GB of memory is available before starting, because other heavy jobs share the machine.
HERE="$(cd "$(dirname "$0")" && pwd)"
LOCK="${TMPDIR:-/tmp}/dink_unclaimed_blender.lock"
export HOME="${TMPDIR:-/tmp}/dink_unclaimed_home"; mkdir -p "$HOME"
exec flock "$LOCK" bash -c 'n=0; while [ "$(awk "/MemAvailable/ {print int(\$2/1048576)}" /proc/meminfo)" -lt 6 ] && [ $n -lt 180 ]; do sleep 10; n=$((n+1)); done; exec blender -b --factory-startup -t 4 --python "$0" -- "$@"' "$HERE/$1" "${@:2}"
