#!/bin/bash
# card-hair pass, 12 Nov: Milder (skin on), Mother (from base: neckline skin margin), Dink (from garments: collar); logs to ../_run_c.log
cd "$(dirname "$0")"; O="$(cd .. && pwd)"
export HAIR_STEPS=atlas,strands,cards,save HAIR_SHOTS=sun2m,sun05,ovc05,back,crown HAIR_SPP=96
MT=${MT:-r9}; LT=${LT:-r7}; DT=${DT:-r9}
[ -z "$SKIP_MILDER" ] && ./run_char.sh Milder ${LFROM:-5} 10 $LT body,close,game 96
[ -z "$SKIP_MOTHER" ] && ./run_char.sh Mother ${MFROM:-1} 10 $MT body,close,game 96
if [ -z "$SKIP_DINK" ]; then
  ./run_dink.sh ${DFROM:-2} $DT body,close,game,poses
  python3 -I write_manifest.py "$O/Dink" Dink "$O/Dink/manifest_extra.json"
fi
python3 -I contact_sheet.py "$O/contact_sheet.png" "Dink Smallwood (SK_Dink_Photoreal):$O/Dink/Review:$DT" "Dink's mother (SK_Mother_Photoreal):$O/Mother/Review:$MT" "Milder Flatstomp (SK_Milder_Photoreal):$O/Milder/Review:$LT"
echo ALL_C_DONE
