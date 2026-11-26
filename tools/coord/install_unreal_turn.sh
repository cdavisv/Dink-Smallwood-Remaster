#!/usr/bin/env bash
# Install tools/coord/unreal_turn.sh as DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh (the copy every agent calls).
# The old file is kept as unreal_turn.prev.sh and replaced by RENAME: bash reads a running script as it goes, so editing the
# installed file in place would break the steps that are waiting in it right now. Usage: tools/coord/install_unreal_turn.sh [coord dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$(cd "$HERE/../.." && pwd)/DinkRemasterUE/Saved/Gate2Coord}"
mkdir -p "$DEST"
bash -n "$HERE/unreal_turn.sh"
[ -f "$DEST/unreal_turn.sh" ] && cp -p "$DEST/unreal_turn.sh" "$DEST/unreal_turn.prev.sh"
cp "$HERE/unreal_turn.sh" "$DEST/.unreal_turn.new.$$"
chmod +x "$DEST/.unreal_turn.new.$$"
mv -f "$DEST/.unreal_turn.new.$$" "$DEST/unreal_turn.sh"
echo "installed $DEST/unreal_turn.sh ($(sha256sum "$DEST/unreal_turn.sh" | cut -c1-12)); previous kept as unreal_turn.prev.sh"
