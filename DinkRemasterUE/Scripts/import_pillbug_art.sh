#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DINK_CREATURE_MANIFEST=Pillbug/pillbug_manifest.json
export DINK_CREATURE_LOG_SUFFIX=_pillbug
exec "$PROJECT_DIR/Scripts/import_creature_art.sh" "$@"
