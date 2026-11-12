#!/bin/bash
# final pass for the three characters: all stages that changed, review renders, export, manifests, contact sheet
cd "$(dirname "$0")"; O="$(cd .. && pwd)"
export HAIR_STEPS=atlas,strands,cards,save HAIR_SHOTS=sun2m,sun05,ovc05,back
MT=${MT:-r7}; LT=${LT:-r5}; DT=${DT:-r8}
[ -z "$SKIP_MOTHER" ] && ./run_char.sh Mother ${MFROM:-1} 10 $MT body,close,game 48
[ -z "$SKIP_MILDER" ] && ./run_char.sh Milder ${LFROM:-2} 10 $LT body,close,game 48
if [ -z "$SKIP_DINK" ]; then
  TO=5 ./run_dink.sh ${DFROM:-5} $DT
  ./run_dink.sh 8 $DT body,close,game
  python3 -I write_manifest.py "$O/Dink" Dink "$O/Dink/manifest_extra.json"
fi
python3 -I contact_sheet.py "$O/contact_sheet.png" "Dink Smallwood (SK_Dink_Photoreal):$O/Dink/Review:$DT" "Dink's mother (SK_Mother_Photoreal):$O/Mother/Review:$MT" "Milder Flatstomp (SK_Milder_Photoreal):$O/Milder/Review:$LT"
echo ALL_FINAL_DONE
