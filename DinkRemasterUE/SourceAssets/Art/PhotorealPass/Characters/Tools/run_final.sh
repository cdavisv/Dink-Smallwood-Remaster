#!/bin/bash
cd "$(dirname "$0")"; O="$(cd .. && pwd)"
while pgrep -x blender -a | grep -q "SK_Dink_Photoreal.blend Dink/Review"; do sleep 4; done
f() { "$@" 2>&1 | grep -E '^\[PR\]|Error|Traceback|line [0-9]+|EXPORT|VALIDATION (error|warning (UV|LOOSE|TRIS))|manifest|contact' | grep -v rendered | cut -c1-300; }
f blender -b -t 4 --python dink_04_head.py
f blender -b -t 4 --python dink_05b_skin.py
f blender -b -t 4 --python dink_06_assemble.py
f blender -b -t 4 --python dink_07_physique.py
f blender -b -t 4 "$O/Dink/SK_Dink_Photoreal.blend" --python export_char.py -- "$O/Dink/Export" "$O/Dink/export_report.json" character_hero
f python3 write_manifest.py "$O/Dink" Dink "$O/Dink/manifest_extra.json"
f python3 contact_sheet.py "$O/contact_sheet.png" "Dink Smallwood (SK_Dink_Photoreal):$O/Dink/Review:r3"
echo FINAL_DONE
