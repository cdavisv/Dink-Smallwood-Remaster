#!/usr/bin/env bash
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_animation_pass.log"
if [[ ! -f "$PROJECT_DIR/SourceAssets/Art/Characters/Animations/AnimationPassV1/animation_manifest.json" ]]; then
  echo 'ANIMATION PASS IMPORT FAILED: source manifest missing'
  exit 2
fi
mkdir -p "$PROJECT_DIR/Saved/Logs" "$PROJECT_DIR/Saved/Art"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_animation_pass.py" -nullrhi -unattended \
  -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && rg -q 'DINK ANIMATION PASS IMPORT OK:' "$LOG"; then
  rg 'DINK ANIMATION PASS IMPORT OK:' "$LOG" | tail -1
else
  echo "ANIMATION PASS IMPORT FAILED (exit $rc): $LOG"
  rg -A10 'Traceback|Error:|Exception' "$LOG" | tail -45
  exit 1
fi
