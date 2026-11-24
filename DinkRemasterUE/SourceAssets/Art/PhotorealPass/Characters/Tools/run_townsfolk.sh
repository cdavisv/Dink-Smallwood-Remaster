#!/bin/bash
# A townsman of townsfolk.py, every stage in order. Blender on the CPU (DINK_CPU=1 PR_CPU=1 in the environment).
#   run_townsfolk.sh <Name> [stages, comma list; default all] [groom tag]
# stages: outfit  his outfit colour map from the hero's (townsfolk_outfit.py)
#         head    his own face (dink_04_head.py, NPC/<Name>/cfg/head.json)
#         eyes    his eye maps (eye_tex.py)
#         skin    his skin set (dink_05b_skin.py, cfg/skin.json)
#         hair    the strand groom and its cards (hair_groom.py, hair_styles.py '<Name>')
#         pack    the hero's clothes without his pack, the hat and the staff, the gear maps (townsfolk_pack.py)
#         body    texture sets capped (tex_cap.py), then assemble (dink_06_assemble.py, cfg/assemble.json)
#         export  FBX LOD0-3, export report, manifest
set -e
cd "$(dirname "$0")"; CH=$(cd .. && pwd); N=$1; n=$(echo "$N" | tr A-Z a-z); steps=${2:-outfit,head,eyes,skin,hair,pack,body,export}; tag=${3:-t1}
f() { "$@" 2>&1 | grep -E '^\[PR\]|Error|Traceback|line [0-9]+|^eye|^hair|EXPORT|VALIDATION error|townsfolk|manifest|tex_cap' | grep -v rendered | cut -c1-300; return 0; }
st() { case ,$steps, in *,$1,*) return 0;; esac; return 1; }
row() { python3 -I -c "import sys; sys.path.insert(0, '.'); from townsfolk import TOWNSFOLK as T; print(T['$N']['$1'])"; }
st outfit && [ "$(row body 2>/dev/null)" != port ] && f python3 -I townsfolk_outfit.py "$N"
st head && f blender -b -t 4 --python dink_04_head.py -- "$CH/NPC/$N/cfg/head.json"
st eyes && f python3 -I eye_tex.py "$CH/NPC/$N/Textures/T_${N}_PR_Eyes" "$(row iris)" "$(row eye_seed)"
st skin && f blender -b -t 4 --python dink_05b_skin.py -- "$CH/NPC/$N/cfg/skin.json"
st hair && HAIR_SHOTS=${HAIR_SHOTS:-sun05} HAIR_SPP=${HAIR_SPP:-40} f blender -b -t 4 --python hair_groom.py -- "$N" ${HAIR_STEPS:-atlas,save} "$tag"
if [ "$(row body 2>/dev/null)" = port ]; then      # a figure in a robe keeps the clothes of its Unclaimed source
  st pack && { NPC_PORT_ONLY=1 f blender -b -t 4 --python npc_port.py -- "$N" "$CH/NPC/$N/Work"; f blender -b -t 4 --python townsfolk_port_pack.py -- "$N"; }
else
  st pack && f blender -b -t 4 --python townsfolk_pack.py -- "$N"
fi
# textures at the size the play camera can show (tex_cap.py; a stage that bakes at full size is capped again here)
st body && f python3 -I tex_cap.py "$CH/NPC/$N/Textures" ${TEX_CAPS:-Skin=2048 Hair=2048 Outfit=2048 Gear=2048 Eyes=512}
st body && f blender -b -t 4 --python dink_06_assemble.py -- "$CH/NPC/$N/cfg/assemble.json"
st export && { f blender -b -t 4 "$CH/NPC/$N/SK_${N}_Photoreal.blend" --python export_char.py -- "$CH/NPC/$N/Export" "$CH/NPC/$N/export_report.json" character_hero; f python3 -I townsfolk_manifest.py "$N"; }
echo "TOWNSFOLK_DONE $N $steps $(date +%T)"
