#!/usr/bin/env bash
# Reuse the validated importer for the cottage yard and its Blender assets.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DINK_ART_SOURCE="$PROJECT_DIR/SourceAssets/Art/StonebrookExterior"
export DINK_ART_MANIFEST=exterior_manifest.json
export DINK_ART_LAYOUT=exterior_layout.json
export DINK_ART_LOG_SUFFIX=_exterior
exec "$PROJECT_DIR/Scripts/import_stonebrook_art.sh" "$@"
