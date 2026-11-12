#!/usr/bin/env bash
# round.sh <name> [make_script args]: capture all cameras into Saved/PhotorealPass/lighting/<name> and build a sheet
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; Q=$P/Scripts/PhotorealQA
L=$P/Saved/PhotorealPass/lighting; N=$1; shift
O=${DINK_CAPTURE_DIR:-$L/$N}
mkdir -p $O $L/tools
python3 -I $Q/make_script.py $O "$@" > $L/tools/$N.txt
$Q/run_capture.sh $L/tools/$N.txt | grep -o "fps.*\|exit.*\|Fatal.*"
grep -c "Failed to compile\|Material.*error" $L/tools/capture.log
python3 - <<PY
from PIL import Image
import glob
fs=sorted(glob.glob('$O/*.png'))
W,H=640,360
sheet=Image.new('RGB',(W*5,H*((len(fs)+4)//5)))
for i,f in enumerate(fs): sheet.paste(Image.open(f).convert('RGB').resize((W,H)),((i%5)*W,(i//5)*H))
sheet.save('$L/tools/${N}_sheet.jpg',quality=88)
PY
