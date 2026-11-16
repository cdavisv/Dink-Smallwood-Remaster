#!/usr/bin/env bash
# Import the footstep and ambience-bed WAVs (Content/Dink/Data/Audio/life.json `import`) into /Game/Dink/Audio/Life.
# One Unreal step: run it through Saved/Gate2Coord/unreal_turn.sh. Log: Saved/Logs/import_life_audio.log.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_life_audio.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/AudioQA/import_life_audio.py" -nullrhi -unattended \
  -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && grep -q 'DINK LIFE AUDIO IMPORT OK:' "$LOG"; then grep 'DINK LIFE AUDIO IMPORT OK:' "$LOG" | tail -1
else echo "LIFE AUDIO IMPORT FAILED (exit $rc): $LOG"; grep -A10 -E 'Traceback|Error:|Exception' "$LOG" | tail -40; exit 1; fi
