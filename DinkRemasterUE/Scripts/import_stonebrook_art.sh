#!/usr/bin/env bash
# Import Blender FBX + BC/ORM/normal maps and publish runtime art manifest atomically.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_art${DINK_ART_LOG_SUFFIX:-}.log"
ART_SOURCE="${DINK_ART_SOURCE:-$PROJECT_DIR/SourceAssets/Art/Stonebrook}"
ART_MANIFEST="${DINK_ART_MANIFEST:-art_manifest.json}"
mkdir -p "$PROJECT_DIR/Saved/Logs"
if [[ ! -f "$ART_SOURCE/$ART_MANIFEST" ]]; then
  echo 'ART IMPORT FAILED: build the Blender kit first (see SourceAssets/Art/Stonebrook/README.md)'
  exit 2
fi
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_stonebrook_art.py" \
  -nullrhi -unattended -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && rg -q 'DINK ART IMPORT OK:' "$LOG"; then
  rg 'DINK ART IMPORT OK:' "$LOG" | tail -1
else
  echo "ART IMPORT FAILED (exit $rc): $LOG"
  rg -A12 'Traceback|Error:|Exception' "$LOG" | tail -45
  exit 1
fi
