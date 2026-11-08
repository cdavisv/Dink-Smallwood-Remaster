#!/usr/bin/env bash
# Render evidence images of a generated greybox map with the GPU but no display:
# a top-down orthographic view of the region's outdoor screens and a few eye-level views.
#
#   Scripts/capture_greybox.sh [--region stonebrook|all|<region>]
#
# Runs the DinkGreyboxCapture commandlet with -AllowCommandletRendering -RenderOffscreen (NOT
# -nullrhi), so it needs a working Vulkan driver. The first run compiles the project's shaders
# (slow; later runs use the DDC). Output: Saved/Import/Captures/<region>_top.png, <region>_eye_N.png.
# Log: Saved/Logs/capture_<region>.log.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
EDITOR="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"
REGION="stonebrook"
[[ "${1:-}" == "--region" ]] && REGION="${2:-stonebrook}"
[[ "${1:-}" == --region=* ]] && REGION="${1#*=}"
LOG="$PROJECT_DIR/Saved/Logs/capture_${REGION}.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"
start=$(date +%s)
env -u WAYLAND_DISPLAY -u DISPLAY timeout "${DINK_CAPTURE_TIMEOUT:-5400}" "$EDITOR" "$PROJECT_DIR/DinkRemaster.uproject" \
	-run=DinkGreyboxCapture -Region="$REGION" -AllowCommandletRendering -RenderOffscreen \
	-unattended -nosplash -nopause -nosound -stdout -FullStdOutLogOutput >"$LOG" 2>&1
rc=$?
line=$(grep -E "DINK CAPTURE (OK|FAILED)" "$LOG" | tail -1 | sed 's/^.*\(DINK CAPTURE\)/\1/')
echo "${line:-DINK CAPTURE FAILED: no summary line} (editor exit $rc, $(( $(date +%s) - start ))s). Log: $LOG"
[[ $rc -eq 0 && "$line" == DINK\ CAPTURE\ OK* ]]
