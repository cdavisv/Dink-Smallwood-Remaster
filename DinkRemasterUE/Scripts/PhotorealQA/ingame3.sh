#!/usr/bin/env bash
# ingame3.sh: the final review set of the 12 Nov 2026 integration round into Saved/PhotorealPass/ingame3:
# the in-game cameras of ingame2, the calibration pairs (engine | Blender reference), indoor before/after, town kit test house.
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; Q=$P/Scripts/PhotorealQA
L=$P/Saved/PhotorealPass/lighting; O=$P/Saved/PhotorealPass/ingame3
mkdir -p $O/cal $O/indoor
mkdir -p $L/tools; cd $L/tools
$Q/cal.sh final --only oak,pine,willow,bush,grassgrid,carpet,carpetgame,plaster,dungeon,town,townclose,townback
python3 -I $Q/cal_compare.py final > $O/cal/numbers.txt
python3 -I $Q/indoor_script.py $O/indoor --only interior_2,interior_34,dungeon_579,dungeon_73,lava_85 --heroclose > ingame3_indoor.txt
$Q/run_capture.sh $L/tools/ingame3_indoor.txt | grep -o "fps.*\|exit.*\|Fatal.*" > $O/indoor/fps.txt
python3 -I $Q/make_script.py $O --extra --warm 40 > ingame3.txt
$Q/run_capture.sh $L/tools/ingame3.txt | grep -o "fps.*\|exit.*\|Fatal.*" > $P/Saved/PhotorealPass/ingame3_fps.txt
grep -c "Failed to compile\|Material.*error" capture.log >> $P/Saved/PhotorealPass/ingame3_fps.txt
echo done > $O/done.txt
