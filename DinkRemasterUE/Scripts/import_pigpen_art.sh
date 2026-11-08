#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DINK_ART_SOURCE="$PROJECT_DIR/SourceAssets/Art/PigPen"
export DINK_ART_MANIFEST=art_manifest.json
export DINK_ART_LAYOUT=pigpen_layout.json
export DINK_ART_OUTPUT_NAME=pigpen
export DINK_ART_LOG_SUFFIX=_pigpen
exec "$PROJECT_DIR/Scripts/import_stonebrook_art.sh" "$@"
