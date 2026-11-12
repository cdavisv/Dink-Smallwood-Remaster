#!/usr/bin/env bash
# second half of ingame3.sh after the exposure change: indoor pairs and the in-game cameras again
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; Q=$P/Scripts/PhotorealQA
L=$P/Saved/PhotorealPass/lighting; O=$P/Saved/PhotorealPass/ingame3
mkdir -p $L/tools; cd $L/tools
python3 -I $Q/indoor_script.py $O/indoor --only interior_2,interior_34,dungeon_579,dungeon_73,lava_85 --heroclose > ingame3_indoor.txt
$Q/run_capture.sh $L/tools/ingame3_indoor.txt > /dev/null
grep -o "DINK CAPTURE: fps.*" capture.log | sed 's/DINK CAPTURE: //' > $O/indoor/fps.txt
python3 -I $Q/make_script.py $O --extra --warm 40 > ingame3.txt
$Q/run_capture.sh $L/tools/ingame3.txt > /dev/null
grep -o "DINK CAPTURE: fps.*" capture.log | sed 's/DINK CAPTURE: //' > $P/Saved/PhotorealPass/ingame3_fps.txt
grep -c "Failed to compile\|Material.*error" capture.log >> $P/Saved/PhotorealPass/ingame3_fps.txt
python3 -I $Q/ingame3_sheet.py
echo finished2
