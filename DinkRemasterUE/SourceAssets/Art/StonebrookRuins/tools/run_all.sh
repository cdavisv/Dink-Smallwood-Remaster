#!/usr/bin/env bash
# Rebuild the Stonebrook fire-ruin kit end to end (run from anywhere). Never launches Unreal.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
KIT="$(dirname "$HERE")"
UE="$(cd "$KIT/../../.." && pwd)"
TOOLS="$UE/../tools/blender"
BL="blender -b --factory-startup -t ${BLENDER_THREADS:-3}"
cd "$UE"
python3 "$HERE/make_textures.py"
$BL -P "$HERE/pose_mother_remains.py"
$BL -P "$HERE/build_ruins.py"
python3 "$TOOLS/dink.py" validate --blend "$KIT/KIT_StonebrookRuins.blend" --report "$KIT/validation.json"
python3 "$TOOLS/dink.py" export_ue --blend "$KIT/KIT_StonebrookRuins.blend" --out "$KIT/Export" --formats fbx --source-root "$UE/SourceAssets/Art" > "$KIT/export_report.json"
$BL -P "$HERE/export_lods.py"
python3 "$HERE/make_manifest.py"
if [ "${SKIP_RENDERS:-0}" != 1 ]; then
  $BL -P "$HERE/render_previews.py" -- burning burnt interior interior_burning compare1 compare2 --samples "${SAMPLES:-64}"
  python3 "$HERE/compose_compare.py"
fi
