#!/usr/bin/env bash
# Pipeline stage 6: import the original world into a walkable greybox (headless).
#
#   Scripts/import_greybox.sh [--region stonebrook|all|<region key>] [--export] [--dry-run] [--data <data repo>]
#
#   --region   which region to import (default stonebrook); "all" builds the whole world.
#              Output map: /Game/Dink/_Generated/Maps/L_Greybox_<Region> (L_Greybox_World for all).
#   --export   re-export the import bundle (ImportData/) from the data repo first. Done
#              automatically when ImportData/bundle.json is missing.
#   --dry-run  load the bundle and report what would be built; writes nothing.
#   --no-test  skip the import tests (Scripts/test.sh Dink.Import) that run after a real import.
#
# Steps: bundle (Scripts/export_import_bundle.py) -> engine template content for the character
# (Scripts/copy_template_content.sh) -> commandlet DinkImportGreybox in a headless editor.
# Logs: Saved/Logs/import_<region>.log; report: Saved/Import/import_<region>.json and
# Saved/Import/coverage.csv. Prints one summary line; exit 0 only on success.
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPROJECT="$PROJECT_DIR/DinkRemaster.uproject"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
EDITOR="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"
REGION="stonebrook"
EXPORT=0
DRYRUN=""
RUNTESTS=1
DATA="$PROJECT_DIR/.."
while [[ $# -gt 0 ]]; do
	case "$1" in
		--region) REGION="$2"; shift 2 ;;
		--region=*) REGION="${1#*=}"; shift ;;
		--export) EXPORT=1; shift ;;
		--dry-run) DRYRUN="-DryRun"; RUNTESTS=0; shift ;;
		--no-test) RUNTESTS=0; shift ;;
		--data) DATA="$2"; shift 2 ;;
		*) echo "IMPORT FAILED: unknown argument $1"; exit 2 ;;
	esac
done
LOG="$PROJECT_DIR/Saved/Logs/import_${REGION}.log"
mkdir -p "$PROJECT_DIR/Saved/Logs"

if [[ ! -x "$EDITOR" ]]; then echo "IMPORT FAILED: editor not found at $EDITOR (set UE_ROOT)"; exit 2; fi
if [[ ! -f "$PROJECT_DIR/Binaries/Linux/libUnrealEditor-DinkImport.so" && ! -f "$PROJECT_DIR/Plugins/DinkImport/Binaries/Linux/libUnrealEditor-DinkImport.so" ]]; then
	echo "IMPORT FAILED: project not built; run Scripts/build.sh first"; exit 2
fi

start=$(date +%s)
if [[ $EXPORT -eq 1 || ! -f "$PROJECT_DIR/ImportData/bundle.json" ]]; then
	python3 "$PROJECT_DIR/Scripts/export_import_bundle.py" --data "$DATA" --out "$PROJECT_DIR/ImportData" || { echo "IMPORT FAILED: bundle export failed"; exit 1; }
fi
"$PROJECT_DIR/Scripts/copy_template_content.sh" >/dev/null || { echo "IMPORT FAILED: template content copy failed"; exit 1; }

ue_start=$(date +%s)
env -u WAYLAND_DISPLAY -u DISPLAY timeout "${DINK_IMPORT_TIMEOUT:-5400}" "$EDITOR" "$UPROJECT" \
	-run=DinkImportGreybox -Region="$REGION" $DRYRUN \
	-unattended -nosplash -nopause -nullrhi -nosound -NoSound -stdout -FullStdOutLogOutput \
	>"$LOG" 2>&1
rc=$?
end=$(date +%s)

line=$(grep -E "DINK IMPORT (OK|FAILED)" "$LOG" | tail -1 | sed 's/^.*\(DINK IMPORT\)/\1/')
if [[ $rc -ne 0 || "$line" != DINK\ IMPORT\ OK* ]]; then
	echo "IMPORT FAILED (editor exit $rc) after $((end - start))s: ${line:-no summary line}. Log: $LOG"
	grep -E "Error:|Fatal|Ensure" "$LOG" | grep -v "LogPython" | head -15
	exit 1
fi
gen="$PROJECT_DIR/Content/Dink/_Generated"
size=$(du -sh "$gen" 2>/dev/null | awk '{print $1}')
assets=$(find "$gen" -name '*.uasset' 2>/dev/null | wc -l)
maps=$(find "$gen" -name '*.umap' 2>/dev/null | wc -l)
echo "$line"
echo "IMPORT OK in $((end - start))s (editor $((end - ue_start))s): _Generated holds $assets assets + $maps maps, $size. Log: $LOG; coverage: Saved/Import/coverage.csv"
if [[ $RUNTESTS -eq 1 ]]; then
	# Tests whose map was not generated pass with a "skipped" warning (e.g. the Stonebrook checks
	# after an --region all run on a clean tree).
	"$PROJECT_DIR/Scripts/test.sh" Dink.Import || { echo "IMPORT FAILED: the import tests failed"; exit 1; }
fi
exit 0
