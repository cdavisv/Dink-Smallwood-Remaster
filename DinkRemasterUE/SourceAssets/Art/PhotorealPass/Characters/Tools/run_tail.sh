#!/bin/bash
# head + skin + assemble + review + export, without re-baking the outfit. usage: run_tail.sh <tag> <sets>
cd "$(dirname "$0")"; O="$(cd .. && pwd)"
f() { "$@" 2>&1 | grep -E '^\[PR\]|Error|Traceback|line [0-9]+|EXPORT|VALIDATION|manifest' | grep -v rendered | cut -c1-300; }
f blender -b -t 4 --python dink_04_head.py
f blender -b -t 4 --python dink_05b_skin.py
f blender -b -t 4 --python dink_06_assemble.py
f blender -b -t 4 "$O/Dink/SK_Dink_Photoreal.blend" --python export_char.py -- "$O/Dink/Export" "$O/Dink/export_report.json" character_hero
f blender -b -t 4 --python render_review.py -- Dink/SK_Dink_Photoreal.blend Dink/Review $1 $2
echo TAIL_DONE
