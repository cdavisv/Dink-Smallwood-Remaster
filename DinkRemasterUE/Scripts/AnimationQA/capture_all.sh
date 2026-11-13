#!/usr/bin/env bash
# Capture every animation state in the running game for one animation path and tile the strips.
#   Scripts/AnimationQA/capture_all.sh <tag> [engine args]     e.g.  capture_all.sh old -dpcvars=dink.BodyAnimation=0
# Strips land in Saved/AnimationPass/<tag>_<state>_engine.png. Offscreen; one game run per state.
set -uo pipefail
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAG="$1"; shift
python3 -I "$P/Scripts/AnimationQA/make_capture.py" "$TAG" >/dev/null
for S in ${DINK_CAPTURE_STATES:-idle walk run transition start_stop attack_combo mother}; do
  mkdir -p "$P/Saved/AnimationPass/frames"
  for d in $(grep -o "frames/${TAG}_[a-z_]*" "$P/Saved/AnimationPass/capture/$S.txt" | sort -u); do mkdir -p "$P/Saved/AnimationPass/$d"; done
  "$P/Scripts/PhotorealQA/run_capture.sh" "$P/Saved/AnimationPass/capture/$S.txt" "$@" | grep -c "shot" | sed "s/^/$TAG $S shots: /"
  case $S in
    idle) CROP=440,120,840,560;; mother) CROP=240,100,1040,620;; attack_combo) CROP=500,150,780,520;; *) CROP=340,150,940,520;;
  esac
  python3 -I "$P/Scripts/AnimationQA/strip.py" "${TAG}_$S" "$CROP" 300 | sed "s|$P/||"
done
