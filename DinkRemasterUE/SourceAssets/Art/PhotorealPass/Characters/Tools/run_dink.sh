#!/bin/bash
# usage: run_dink.sh <first stage number> ; runs the Dink pipeline from that stage on
cd "$(dirname "$0")"; O="$(cd .. && pwd)"; from=${1:-1}; to=${TO:-99}
run() { n=$1; shift; if [ "$n" -ge "$from" ] && [ "$n" -le "$to" ]; then echo "=== stage $n: $*"; "$@" 2>&1 | grep -E '^\[PR\]|Error|Out of memory|Cycles device|Traceback|line [0-9]+|^wrote|luma|EXPORT|UV PER|VALIDATION (error|warning (UV|TRIS))' | grep -v 'rendered\|Saved' | cut -c1-400; fi; }
run 1 blender -b -t 4 --python dink_01_base.py
run 2 blender -b -t 4 --python dink_02a_bodyvol.py
run 2 blender -b -t 4 --python dink_02_garments.py -- norender
run 3 blender -b -t 4 --python dink_03_gear.py -- norender
run 4 blender -b -t 4 --python dink_04_head.py -- "$O/Dink/cfg/head.json"
run 5 blender -b -t 4 --python dink_05b_skin.py -- "$O/Dink/cfg/skin.json"
run 5 blender -b -t 4 --python hair_groom.py -- Dink ${HAIR_STEPS:-atlas,save} ${2:-r1}
run 6 blender -b -t 4 --python dink_05_bake.py
run 7 python3 -I post_tex.py "$O/Dink" T_Dink_PR
run 8 blender -b -t 4 --python dink_06_assemble.py -- "$O/Dink/cfg/assemble.json"
run 9 blender -b -t 4 --python render_review.py -- Dink/SK_Dink_Photoreal.blend Dink/Review ${2:-r1} ${3:-body,face,hands,poses} 96
run 10 blender -b -t 4 "$O/Dink/SK_Dink_Photoreal.blend" --python export_char.py -- "$O/Dink/Export" "$O/Dink/export_report.json" character_hero
echo PIPELINE_DONE
