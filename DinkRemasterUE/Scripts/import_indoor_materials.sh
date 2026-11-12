#!/usr/bin/env bash
# Photoreal pass: lit sprite card and flame materials of the indoor set (Scripts/import_indoor_materials.py). Re-runnable.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_indoor_materials.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_indoor_materials.py" \
  -nullrhi -unattended -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && grep -q 'DINK INDOOR MATERIALS OK:' "$LOG"; then
  grep 'DINK INDOOR MATERIALS OK:' "$LOG" | tail -1 | sed 's/^.*DINK INDOOR/DINK INDOOR/'
  grep 'DINK INDOOR: ' "$LOG" | sed 's/^.*DINK INDOOR: /  warning: /' | sort -u | head -20
else
  echo "INDOOR MATERIALS FAILED (exit $rc): $LOG"
  grep 'LogPython: Error' "$LOG" | head -14
  exit 1
fi
