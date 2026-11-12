#!/bin/bash
# quick head iteration on the existing outfit bake. usage: run_head.sh <tag> <sets>
cd "$(dirname "$0")"
f() { "$@" 2>&1 | grep -E '^\[PR\]|Error|Traceback|line [0-9]+' | grep -v rendered | cut -c1-240; }
f blender -b -t 4 --python dink_04_head.py
f blender -b -t 4 --python dink_05b_skin.py
f blender -b -t 4 --python dink_06_assemble.py
f blender -b -t 4 --python render_review.py -- Dink/SK_Dink_Photoreal.blend Dink/Review $1 $2 ${3:-40}
echo HEAD_DONE
