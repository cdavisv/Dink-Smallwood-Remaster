#!/usr/bin/env bash
# Bug A200: generated LOD1/LOD2 (50 % / 25 %) on the bound single-LOD kit meshes (corpses, dragon statue,
# save and teleport machines), changed in place, Nanite off (Scripts/add_kit_lods.py). Re-runnable.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/add_kit_lods.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/add_kit_lods.py" \
  -nullrhi -unattended -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && grep -q 'DINK KIT LODS OK:' "$LOG"; then
  grep 'DINK KIT LODS' "$LOG" | sed 's/^.*DINK KIT LODS/DINK KIT LODS/' | sort -u
else
  echo "KIT LODS FAILED (exit $rc): $LOG"
  grep 'LogPython: Error\|DINK KIT LODS' "$LOG" | head -20
  exit 1
fi
