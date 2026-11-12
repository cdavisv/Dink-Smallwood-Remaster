#!/usr/bin/env bash
# Photoreal pass: import the town-house kit (materials per the manifest integration contract, 14 modules)
# into /Game/Dink/Photoreal/TownExteriors (Scripts/import_town_exteriors.py). Re-runnable.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_town.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_town_exteriors.py" \
  -nullrhi -unattended -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && grep -q 'DINK TOWN IMPORT OK:' "$LOG"; then
  grep 'DINK TOWN IMPORT OK:' "$LOG" | tail -1 | sed 's/^.*DINK TOWN/DINK TOWN/'
  grep 'DINK TOWN: ' "$LOG" | sed 's/^.*DINK TOWN: /  warning: /' | sort -u | head -20
else
  echo "TOWN IMPORT FAILED (exit $rc): $LOG"
  grep 'LogPython: Error' "$LOG" | head -14
  exit 1
fi
