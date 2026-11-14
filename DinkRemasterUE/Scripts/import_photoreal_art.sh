#!/usr/bin/env bash
# Photoreal pass: import vegetation, scatter stones and the photoreal hero into /Game/Dink/Photoreal
# (Scripts/import_photoreal_art.py). Re-runnable; DINK_PHOTOREAL_ONLY=vegetation,scatter,hero limits it.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_photoreal.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_photoreal_art.py" \
  -nullrhi -unattended -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && grep -q 'DINK PHOTOREAL IMPORT OK:' "$LOG"; then
  grep 'DINK PHOTOREAL IMPORT OK:' "$LOG" | tail -1 | sed 's/^.*DINK PHOTOREAL/DINK PHOTOREAL/'
  # no warning is not a failure (pipefail would otherwise return grep's 1)
  grep 'DINK PHOTOREAL: ' "$LOG" | sed 's/^.*DINK PHOTOREAL: /  warning: /' | sort -u | head -20 || true
else
  echo "PHOTOREAL IMPORT FAILED (exit $rc): $LOG"
  grep 'LogPython: Error' "$LOG" | head -14
  exit 1
fi
