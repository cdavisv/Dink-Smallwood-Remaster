#!/bin/bash
# usage: run_char.sh <Name> <first stage> [last stage] [tag] [review sets] [samples] ; generalised pipeline for the non-hero characters
cd "$(dirname "$0")"; O="$(cd .. && pwd)"; N=$1; n=$(echo $N | tr A-Z a-z); from=${2:-1}; to=${3:-99}; tag=${4:-r1}; sets=${5:-body,face,game,overcast}; smp=${6:-48}
. "$O/$N/cfg/tex.env"
run() { s=$1; shift; if [ "$s" -ge "$from" ] && [ "$s" -le "$to" ]; then echo "=== stage $s: $*" | cut -c1-200; "$@" 2>&1 | grep -E '^\[PR\]|Error|Out of memory|Cycles device|Traceback|line [0-9]+|^wrote|luma|EXPORT|UV PER|VALIDATION (error|warning (UV|TRIS|LOOSE))|manifest|^eye|^hair|^band' | grep -v 'Photoreal.*Saved' | grep -v rendered | cut -c1-600; fi; }
run 1 blender -b -t 4 --python char_01_base.py -- $N norender
run 2 blender -b -t 4 --python ${n}_02_build.py -- norender
run 3 blender -b -t 4 --python dink_04_head.py -- "$O/$N/cfg/head.json"
run 4 python3 -I eye_tex.py "$O/$N/Textures/T_${N}_PR_Eyes" "$IRIS_RGB" $EYE_SEED
run 5 blender -b -t 4 --python dink_05b_skin.py -- "$O/$N/cfg/skin.json"
run 5 blender -b -t 4 --python hair_groom.py -- $N ${HAIR_STEPS:-atlas,save} $tag
run 6 blender -b -t 4 --python char_05_bake.py -- $N
run 7 python3 -I post_tex.py "$O/$N" T_${N}_PR
run 8 blender -b -t 4 --python dink_06_assemble.py -- "$O/$N/cfg/assemble.json"
if [ -n "$BUILD" ]; then run 8 blender -b -t 4 --python char_07_build.py -- $N $BUILD; fi   # the body build (cfg/tex.env BUILD="<name> <strength>"); assembling rebuilds the meshes, so it is baked in every time
run 9 blender -b -t 4 --python render_review.py -- $N/SK_${N}_Photoreal.blend $N/Review $tag $sets $smp
run 10 blender -b -t 4 "$O/$N/SK_${N}_Photoreal.blend" --python export_char.py -- "$O/$N/Export" "$O/$N/export_report.json" character_humanoid
run 10 python3 -I write_manifest.py "$O/$N" $N "$O/$N/manifest_extra.json"
echo PIPELINE_DONE $N
