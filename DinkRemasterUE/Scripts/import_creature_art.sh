#!/usr/bin/env bash
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_creatures${DINK_CREATURE_LOG_SUFFIX:-}.log"
CREATURE_MANIFEST="${DINK_CREATURE_MANIFEST:-Pig/pig_manifest.json}"
mkdir -p "$PROJECT_DIR/Saved/Logs" "$PROJECT_DIR/Saved/Art"
if [[ ! -f "$PROJECT_DIR/SourceAssets/Art/Creatures/$CREATURE_MANIFEST" ]]; then
  echo 'CREATURE IMPORT FAILED: build/export the selected creature source first'
  exit 2
fi
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_creature_art.py" -nullrhi -unattended \
  -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && rg -q 'DINK CREATURE IMPORT OK:' "$LOG"; then
  rg 'DINK CREATURE IMPORT OK:' "$LOG" | tail -1
else
  echo "CREATURE IMPORT FAILED (exit $rc): $LOG"
  rg -A10 'Traceback|Error:|Exception' "$LOG" | tail -45
  exit 1
fi
