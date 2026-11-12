#!/usr/bin/env bash
# cal.sh <tag> [cal_script args]: calibration captures (1200x800, the Blender review framing) into Saved/PhotorealPass/lighting/cal
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; Q=$P/Scripts/PhotorealQA
L=$P/Saved/PhotorealPass/lighting; N=$1; shift
mkdir -p $L/cal $L/tools
python3 -I $Q/cal_script.py $L/cal $N "$@" > $L/tools/cal_$N.txt
$Q/run_capture.sh $L/tools/cal_$N.txt | grep -o "exit.*\|Fatal.*\|DINK CAL.*" | sort | uniq -c | head -20
