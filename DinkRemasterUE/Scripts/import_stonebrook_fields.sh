#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCREEN="${1:-471}"
if [[ "$SCREEN" != 471 && "$SCREEN" != 438 ]]; then
  echo 'Usage: Scripts/import_stonebrook_fields.sh [471|438]'
  exit 2
fi
export DINK_ART_SOURCE="$PROJECT_DIR/SourceAssets/Art/StonebrookFields"
export DINK_ART_MANIFEST=art_manifest.json
export DINK_ART_LAYOUT="fields_${SCREEN}_layout.json"
export DINK_ART_OUTPUT_NAME="stonebrook_fields_${SCREEN}"
export DINK_ART_LOG_SUFFIX="_fields_${SCREEN}"
export DINK_ART_USED_ASSETS_ONLY=1
export DINK_ART_MATERIAL_FOLDER=/Game/Dink/Materials/StonebrookFields
export DINK_ART_TEXTURE_FOLDER=/Game/Dink/Textures/StonebrookFields
exec "$PROJECT_DIR/Scripts/import_stonebrook_art.sh"
