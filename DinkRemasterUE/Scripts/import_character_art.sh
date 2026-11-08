#!/usr/bin/env bash
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_characters${DINK_CHARACTER_LOG_SUFFIX:-}.log"
CHARACTER_MANIFEST="${DINK_CHARACTER_MANIFEST:-character_manifest.json}"
mkdir -p "$PROJECT_DIR/Saved/Logs" "$PROJECT_DIR/Saved/Art"
if [[ ! -f "$PROJECT_DIR/SourceAssets/Art/Characters/$CHARACTER_MANIFEST" ]]; then
  echo 'CHARACTER IMPORT FAILED: build/export SourceAssets/Art/Characters first'
  exit 2
fi
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_character_art.py" -nullrhi -unattended \
  -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && rg -q 'DINK CHARACTER IMPORT OK:' "$LOG"; then
  rg 'DINK CHARACTER IMPORT OK:' "$LOG" | tail -1
else
  echo "CHARACTER IMPORT FAILED (exit $rc): $LOG"
  rg -A10 'Traceback|Error:|Exception' "$LOG" | tail -45
  exit 1
fi
