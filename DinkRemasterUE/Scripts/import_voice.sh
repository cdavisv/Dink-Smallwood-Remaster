#!/usr/bin/env bash
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_voice.log"
mkdir -p "$PROJECT_DIR/Saved/Logs" "$PROJECT_DIR/Saved/Audio"
# Imports the approved voice lines listed in SourceAssets/asset_ledger.csv (see import_voice.py).
# The MP3s are Git LFS objects: git lfs pull --include "DinkRemasterUE/SourceAssets/Audio/Voice/**" first.
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_voice.py" -nullrhi -unattended \
  -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && rg -q 'DINK VOICE IMPORT OK:' "$LOG"; then
  rg 'DINK VOICE IMPORT OK:' "$LOG" | tail -1
else
  echo "VOICE IMPORT FAILED (exit $rc): $LOG"
  rg -A10 'Traceback|Error:|Exception' "$LOG" | tail -45
  exit 1
fi
