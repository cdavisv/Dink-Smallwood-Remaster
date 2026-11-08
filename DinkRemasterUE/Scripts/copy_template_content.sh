#!/usr/bin/env bash
# Copy the engine's third-person template content that the greybox character uses into the
# project (never referenced in place, never modified in the engine):
#   Templates/TemplateResources/High/Characters/Content/Mannequins -> Content/Characters/Mannequins
#   Templates/TemplateResources/High/Input/Content                 -> Content/Input
# These are the mount points the TP_ThirdPerson template uses (SharedContentPacks), so the assets'
# internal references (/Game/Characters/..., /Game/Input/...) stay valid. The copies are
# git-ignored (engine content, identical on every UE 5.8.4 install); rerun this to restore them.
# Pistol/Rifle/Death animation sets are not needed by ABP_Unarmed and are skipped.
#
#   Scripts/copy_template_content.sh [--force]
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
SRC="$UE_ROOT/Templates/TemplateResources/High"
if [[ ! -d "$SRC/Characters/Content/Mannequins" ]]; then
	echo "COPY FAILED: template content not found under $SRC"
	exit 2
fi
if [[ "${1:-}" != "--force" && -f "$PROJECT_DIR/Content/Characters/Mannequins/Meshes/SKM_Manny_Simple.uasset" && -f "$PROJECT_DIR/Content/Input/IMC_Default.uasset" ]]; then
	echo "COPY OK: template content already present (use --force to recopy)"
	exit 0
fi
mkdir -p "$PROJECT_DIR/Content/Characters" "$PROJECT_DIR/Content/Input"
rsync -a --delete --exclude 'Anims/Pistol/' --exclude 'Anims/Rifle/' --exclude 'Anims/Death/' \
	"$SRC/Characters/Content/Mannequins/" "$PROJECT_DIR/Content/Characters/Mannequins/"
rsync -a --delete "$SRC/Input/Content/" "$PROJECT_DIR/Content/Input/"
n=$(find "$PROJECT_DIR/Content/Characters" "$PROJECT_DIR/Content/Input" -name '*.uasset' | wc -l)
size=$(du -sh "$PROJECT_DIR/Content/Characters" "$PROJECT_DIR/Content/Input" | awk '{print $1}' | paste -sd+)
echo "COPY OK: $n template assets ($size) into Content/Characters and Content/Input"
