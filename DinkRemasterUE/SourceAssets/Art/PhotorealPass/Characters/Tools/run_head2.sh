#!/bin/bash
cd "$(dirname "$0")"; O="$(cd .. && pwd)"
L=$1; while ! grep -q PIPELINE_DONE "$L"; do sleep 5; done
f() { "$@" 2>&1 | grep -E '^\[PR\]|Error|Traceback|line [0-9]+|EXPORT|UV PER|VALIDATION (error|warning (UV|TRIS))|manifest' | grep -v rendered | cut -c1-900; }
f blender -b -t 4 --python dink_04_head.py
f blender -b -t 4 --python dink_05b_skin.py
f blender -b -t 4 --python dink_06_assemble.py
f blender -b -t 4 --python render_review.py -- Dink/SK_Dink_Photoreal.blend Dink/Review r6 body,face,game,overcast,lods 48
f blender -b -t 4 "$O/Dink/SK_Dink_Photoreal.blend" --python export_char.py -- "$O/Dink/Export" "$O/Dink/export_report.json" character_hero
echo HEAD2_DONE
