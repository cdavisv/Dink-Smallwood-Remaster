#!/usr/bin/env bash
# Import the Stonebrook440 kit (SourceAssets/Art/Stonebrook440: the two-storey house and its yard props) into
# /Game/Dink/Kits/Stonebrook440 with Scripts/import_stonebrook_art.py. Meshes, materials and textures only: the kit's own
# layout (layout_440.json) asks for authored collision on screen 440 and is NOT published; the house and the yard are placed
# by Scripts/assemble_structures.py (structure_sets.json), which leaves the 1997 hardness as it is. Re-runnable. One Unreal step.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$PROJECT_DIR/SourceAssets/Art/Stonebrook440"
python3 -I - "$SRC" <<'PY' || exit 2
import json, sys
src = sys.argv[1]
m = json.load(open(src + '/art_manifest.json'))
for name, a in m['assets'].items():      # the importer's field names
    a['class'] = {'building': 'building', 'prop': 'prop', 'prop_small': 'prop_small'}.get(a.get('cls'), 'prop')
    a['collision_mode'] = 'complex'
# Seen in the game (16 Nov 2026): the baked thatch is a pale cream in the sun of Stonebrook, the 1997 roofs of 440 are golden straw.
m['materials']['MI_S440_Thatch']['base_tint'] = [1.2, 0.92, 0.5]
json.dump(m, open(src + '/import_manifest.json', 'w'), indent=1)
json.dump({'schema': 'dink-art/1', 'screen': 440, 'replacements': [], 'elements': [], 'hide_origins': [], 'hide_screen_visuals': [],
           'authored_collision_screens': []}, open(src + '/import_layout.json', 'w'), indent=1)
PY
DINK_ART_SOURCE="$SRC" DINK_ART_MANIFEST=import_manifest.json DINK_ART_LAYOUT=import_layout.json DINK_ART_OUTPUT_NAME=stonebrook440_import \
DINK_ART_INSTANCED_USAGE=1 DINK_ART_MATERIAL_FOLDER=/Game/Dink/Materials/Stonebrook440 DINK_ART_TEXTURE_FOLDER=/Game/Dink/Textures/Stonebrook440 DINK_ART_LOG_SUFFIX=_440 \
  "$PROJECT_DIR/Scripts/import_stonebrook_art.sh"
rc=$?
# the importer always writes a runtime manifest; this kit has none (see above)
rm -f "$PROJECT_DIR/Content/Dink/Data/Art/stonebrook440_import.json" "$SRC/import_manifest.json" "$SRC/import_layout.json"
exit $rc
