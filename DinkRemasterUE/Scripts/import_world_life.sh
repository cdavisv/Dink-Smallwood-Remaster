#!/usr/bin/env bash
# World life assets (MPC_Dink_World, M_WorldLife_Lit/Glow) and the vegetation parents with the shared wind node
# (Scripts/import_world_life.py). DINK_WORLD_LIFE_SKIP_VEG=1 builds only /Game/Dink/WorldLife.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_world_life.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_world_life.py" \
  -nullrhi -unattended -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && grep -q 'DINK WORLD LIFE IMPORT OK:' "$LOG"; then
  grep 'DINK WORLD LIFE IMPORT OK:' "$LOG" | tail -1 | sed 's/^.*DINK WORLD/DINK WORLD/'
  grep -E 'DINK PHOTOREAL IMPORT OK:|Failed to compile|\[SM6\].*error' "$LOG" | sed 's/^.*\(DINK PHOTOREAL\)/\1/' | sort -u | head -12 || true
else
  echo "WORLD LIFE IMPORT FAILED (exit $rc): $LOG"
  grep -E 'LogPython: Error|Error: ' "$LOG" | head -14
  exit 1
fi
