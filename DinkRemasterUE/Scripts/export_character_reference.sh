#!/usr/bin/env bash
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
export DINK_REFERENCE_DIR="${DINK_REFERENCE_DIR:-/tmp/dink-character-reference}"
mkdir -p "$DINK_REFERENCE_DIR"
LOG="$DINK_REFERENCE_DIR/export_reference.log"
# Skeletal FBX export reads CPU-skinned render data even with baking disabled.
# NullRHI asserts in UE 5.8.4; use offscreen GPU resources.
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/export_character_reference.py" \
  -AllowCommandletRendering -RenderOffscreen -unattended -nocrashreports \
  -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && rg -q 'DINK REFERENCE EXPORT OK' "$LOG"; then
  echo "REFERENCE EXPORT OK: $DINK_REFERENCE_DIR"
else
  echo "REFERENCE EXPORT FAILED (exit $rc): $LOG"
  rg -A8 'Traceback|Error:|Assertion' "$LOG" | tail -35
  exit 1
fi
