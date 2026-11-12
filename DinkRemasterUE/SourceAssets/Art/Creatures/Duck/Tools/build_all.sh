#!/usr/bin/env bash
# Regenerate the whole duck deterministically (seed 1997). Run from any directory.
set -euo pipefail
cd "$(dirname "$0")/.."
B="blender -b --factory-startup -t 3"
rm -f duck_manifest.json Working/Duck_Working.blend
$B --python Tools/build_duck.py     2>&1 | grep -E "DUCK|Error|Traceback" || true
test -s Working/Duck_Working.blend
$B --python Tools/texture_duck.py   2>&1 | grep -E "READY|Error|Traceback" || true
$B --python Tools/export_duck.py    2>&1 | grep -E "DUCK|Error|Traceback" || true
test -s duck_manifest.json
python3 Tools/inspect_exports.py
python3 ../../../../../tools/blender/dink.py --summary validate --blend "$PWD/SK_Duck.blend" > duck_validation_cli.txt || true
if [ "${DUCK_SKIP_RENDERS:-0}" != 1 ]; then
  $B --python Tools/render_duck.py -- SK_Duck.blend 2>&1 | grep -E "DUCK|Error|Traceback" || true
  python3 Tools/make_sheets.py
  if [ -f Working/v2/SK_Duck.blend ]; then
    [ -f Working/v2_game/preview_duck_game_distance.png ] || $B --python Tools/render_duck.py -- Working/v2/SK_Duck.blend --only game --out Working/v2_game 2>&1 | grep -E "DUCK|Error|Traceback" || true
    python3 Tools/compare_versions.py
  fi
fi
python3 Tools/duck_origins.py
python3 Tools/prepare_duck_ledger.py
test -s SK_Duck.blend && test -s Export/SK_Duck_LOD2.fbx && test -s Export/A_Duck_Death.fbx
echo "DUCK BUILD ALL DONE"
