#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DINK_CHARACTER_MANIFEST=Milder/milder_manifest.json
export DINK_CHARACTER_MERGE_RUNTIME=1
export DINK_CHARACTER_LOG_SUFFIX=_milder
exec "$PROJECT_DIR/Scripts/import_character_art.sh" "$@"
