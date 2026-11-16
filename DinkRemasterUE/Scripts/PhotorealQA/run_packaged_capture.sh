#!/usr/bin/env bash
# Usage: run_packaged_capture.sh <stage dir> <ABSOLUTE capture script> [extra game args]
# Runs a dink.CaptureScript (rendering_set.py writes one) in the PACKAGED game of <stage dir> (package.sh output:
# <stage>/Linux/DinkRemaster), offscreen Vulkan, no X display, no sound, with the engine's normal render and RHI
# threads (unlike run_capture.sh's editor game), so the `fps` lines are the shipped frame cost.
# Log: <stage>/Linux/DinkRemaster/Saved/Logs/DinkPackagedCapture.log. Env: DINK_CAPTURE_TIMEOUT (seconds, default 3000).
STAGE="$(cd "$1" && pwd)"; S="$2"; shift 2
GAME="$STAGE/Linux/DinkRemaster/Binaries/Linux/DinkRemaster"
[[ -x "$GAME" ]] || { echo "no packaged game at $GAME"; exit 2; }
env -u WAYLAND_DISPLAY -u DISPLAY SDL_AUDIODRIVER=dummy timeout ${DINK_CAPTURE_TIMEOUT:-3000} "$GAME" \
  -vulkan -RenderOffscreen -ResX=2560 -ResY=1440 -nosplash -unattended -nosound -NoSound \
  -ForceDPCVars=r.Vulkan.Submission.UseInterruptThread=0,r.Vulkan.Submission.UseSubmissionThread=0 \
  -ExecCmds="dink.CaptureScript $S" -log=DinkPackagedCapture.log "$@" >/dev/null 2>&1
rc=$?
LOG="$STAGE/Linux/DinkRemaster/Saved/Logs/DinkPackagedCapture.log"
echo "exit $rc"; grep "DINK CAPTURE: fps\|Fatal\|Error: " "$LOG" | tail -60
