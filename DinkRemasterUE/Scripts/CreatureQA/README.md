# Creature class captures

Capture scripts for the class-bound creatures (`Content/Dink/Data/Art/creatures.json` `classes`). Run one with
`Scripts/PhotorealQA/run_capture.sh <ABSOLUTE path of the script>`: offscreen, no input, output under
`Saved/PhotorealPass/creatures/`. The same script with `-dpcvars=dink.CreatureClassArt=0` as an extra argument gives the
"before" set (sprite cards): `make_scripts.py` writes both variants with their own output folders.

- `make_scripts.py`: writes the scripts (play camera, close camera, walk strips, kill and carcass, crowd with frame time)
  for a class from its screens. `python3 -I Scripts/CreatureQA/make_scripts.py --help`.
- `sheet.py`: lays captures out as labelled before/after sheets for `Docs/Verification/`.
