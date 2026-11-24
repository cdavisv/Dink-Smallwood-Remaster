#!/bin/bash
# The maiden (NPC/Maiden, base of the twins MaidenBlue / Brown / Red), every stage in order. Blender on the CPU
# (DINK_CPU=1 PR_CPU=1 in the environment).   run_maiden.sh [stages, comma list; default all] [groom tag]
# stages: head, skin, hair, body (assemble + the neckline comb of char_07_build at strength 0), export (FBX, report, manifest),
#         trim (the trim mask and the twins' dress maps)
set -e
cd "$(dirname "$0")"; CH=$(cd .. && pwd); M=$CH/NPC/Maiden; steps=${1:-head,skin,hair,body,export,trim}; tag=${2:-m2}
f() { "$@" 2>&1 | grep -E '^\[PR\]|Error|Traceback|line [0-9]+|^eye|^hair|EXPORT|VALIDATION error|manifest|recoloured|variants|tex_cap' | grep -v rendered | cut -c1-300; }
st() { case ,$steps, in *,$1,*) return 0;; esac; return 1; }
st head && f blender -b -t 4 --python dink_04_head.py -- "$M/cfg/head.json"
st skin && f blender -b -t 4 --python dink_05b_skin.py -- "$M/cfg/skin.json"
st hair && HAIR_SHOTS=${HAIR_SHOTS:-sun05} HAIR_SPP=${HAIR_SPP:-40} f blender -b -t 4 --python hair_groom.py -- Maiden ${HAIR_STEPS:-atlas,save} "$tag"
st body && f python3 -I tex_cap.py "$M/Textures" ${TEX_CAPS:-Skin=2048 Hair=2048}
st body && { f blender -b -t 4 --python dink_06_assemble.py -- "$M/cfg/assemble.json"; f blender -b -t 4 --python char_07_build.py -- NPC/Maiden Matron 0; }
st export && { f blender -b -t 4 "$M/SK_Maiden_Photoreal.blend" --python export_char.py -- "$M/Export" "$M/export_report.json" character_humanoid; f python3 -I maiden_manifest.py; }
st trim && { f blender -b -t 4 --python maiden_trim.py; f python3 -I npc_variants.py; }
echo "MAIDEN_DONE $steps $(date +%T)"
