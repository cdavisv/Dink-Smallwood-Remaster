#!/usr/bin/env bash
# Photoreal pass: import terrain layer textures and build the master terrain and water materials
# (Scripts/import_environment_materials.py). Run before Scripts/import_greybox.sh.
#   DINK_ENV_MATERIALS_ONLY=1  rebuild the material graphs only (skip texture re-import)
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
LOG="$PROJECT_DIR/Saved/Logs/import_environment.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
python3 "$PROJECT_DIR/SourceAssets/Art/PhotorealPass/Environment/build_environment_textures.py" >/dev/null || { echo 'ENV IMPORT FAILED: support textures'; exit 1; }
env -u DISPLAY -u WAYLAND_DISPLAY "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" \
  "$PROJECT_DIR/DinkRemaster.uproject" -run=pythonscript \
  -script="$PROJECT_DIR/Scripts/import_environment_materials.py" \
  -nullrhi -unattended -nocrashreports -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
if [[ $rc -eq 0 ]] && grep -q 'DINK ENV IMPORT OK:' "$LOG"; then
  grep 'DINK ENV IMPORT OK:' "$LOG" | tail -1 | sed 's/^.*DINK ENV/DINK ENV/'
else
  echo "ENV IMPORT FAILED (exit $rc): $LOG"
  grep 'LogPython: Error' "$LOG" | head -14
  exit 1
fi
