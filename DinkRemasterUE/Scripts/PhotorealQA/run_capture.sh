#!/usr/bin/env bash
# Usage: run_capture.sh <ABSOLUTE script file> [extra args]   (offscreen Vulkan, no X display, no input)
# A script kept in this folder names its output as <PROJECT>/Saved/...: the token is replaced by this
# checkout's DinkRemasterUE folder in a copy under Saved/PhotorealPass/lighting/tools before the run.
# Env: UE_ROOT (default ~/UnrealEngine/UE_5.8.4), DINK_RESX, DINK_RESY.
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; Q=$P/Scripts/PhotorealQA
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
S="$1"; shift
mkdir -p "$P/Saved/PhotorealPass/lighting/tools"
LOG=$P/Saved/PhotorealPass/lighting/tools/capture.log
if grep -q "<PROJECT>" "$S" 2>/dev/null; then
  R="$P/Saved/PhotorealPass/lighting/tools/$(basename "$S")"
  sed "s|<PROJECT>|$P|g" "$S" > "$R"; S="$R"
  grep "^shot " "$S" | sed 's|^shot ||; s|/[^/]*$||' | sort -u | while read -r d; do mkdir -p "$d"; done
fi
env -u WAYLAND_DISPLAY -u DISPLAY timeout 1100 "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor" "$P/DinkRemaster.uproject" /Game/Dink/_Generated/Maps/L_Greybox_World \
  -game -vulkan -RenderOffscreen -ResX=${DINK_RESX:-1280} -ResY=${DINK_RESY:-720} -nosplash -unattended -NoCompile -nosound -norhithread -forcerhibypass \
  -ForceDPCVars=r.Vulkan.Submission.UseInterruptThread=0,r.Vulkan.Submission.UseSubmissionThread=0 \
  -ExecCmds="dink.CaptureScript $S" -abslog=$LOG "$@" >/dev/null 2>&1
echo "exit $?"; grep "DINK CAPTURE\|DINK PLAYER\|Fatal\|Error: " $LOG | tail -60
