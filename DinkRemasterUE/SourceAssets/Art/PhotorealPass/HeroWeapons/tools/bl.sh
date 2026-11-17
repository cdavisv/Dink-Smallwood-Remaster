#!/bin/bash
# Run the hero weapon build in Blender (one batch job, four threads; HOME on a scratch folder so no user path gets into the .blend).
# usage: HeroWeapons/tools/bl.sh <name,name|all> [review|final]
HERE="$(cd "$(dirname "$0")" && pwd)"
export HOME="${DINK_SCRATCH_HOME:-${TMPDIR:-/tmp}/dink_weapons_home}"; mkdir -p "$HOME"
exec env ALSOFT_DRIVERS=null blender -b --factory-startup -t 4 --python "$HERE/build_weapons.py" -- "$@"
