#!/bin/bash
# Run one Blender batch job at a time (shared machine: one `blender -b -t 4` per agent).
# usage: tools/bl.sh build_<family>.py [args...]
# HOME points at a scratch folder so no user path ends up inside the saved .blend files.
HERE="$(cd "$(dirname "$0")" && pwd)"
LOCK="${TMPDIR:-/tmp}/dink_unclaimed_blender.lock"
export HOME="${TMPDIR:-/tmp}/dink_unclaimed_home"; mkdir -p "$HOME"
exec flock "$LOCK" blender -b --factory-startup -t 4 --python "$HERE/$1" -- "${@:2}"
