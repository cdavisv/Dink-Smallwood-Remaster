#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
mkdir -p "$PROJECT_DIR/Saved/Logs"
LOG="$PROJECT_DIR/Saved/Logs/camera_foliage_materials.log"
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
 "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
 -script="$PROJECT_DIR/Scripts/import_camera_foliage_materials.py" -nullrhi -unattended \
 -nosound -nosplash -nopause -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rg 'DINK CAMERA FOLIAGE MATERIALS (CHECK PASS|READY)' "$LOG"
