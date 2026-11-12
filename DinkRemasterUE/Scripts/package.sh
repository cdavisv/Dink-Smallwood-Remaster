#!/usr/bin/env bash
# Cook and package the game target (Linux, Development) with RunUAT BuildCookRun.
#
#   Scripts/package.sh                        stage to Saved/StagedBuilds
#   Scripts/package.sh /abs/or/rel/dir        stage to that directory (result: <dir>/Linux/...)
#   Scripts/package.sh [dir] -CookAll         anything after the directory goes straight to RunUAT
#
# First run 7 Nov 2026 (see Plugins/DinkParity/Docs/packaged_probe.md): 40 s from an empty Saved/Cooked (cook 22 s, shaders came from the DDC),
# 30-65 s when only code changed; stage ~1.5 GB (Content/Paks: 575 MB .ucas + 11 MB .pak of raw Dink/Data; binary 300 MB + 296 MB debug files).
#
# Linux Vulkan packaging also needs Python 3 and bubblewrap for the reviewed
# ShaderPrint workaround; it overlays one temporary header without Engine host edits.
# Needs: an imported greybox (Scripts/import_greybox.sh --region all: GameDefaultMap is the
# git-ignored L_Greybox_World), Content/Characters (Scripts/copy_template_content.sh), and a built
# editor (Scripts/build.sh): the cook runs UnrealEditor-Cmd, and by default UAT is told NOT to
# rebuild the editor target so it cannot disturb an editor another agent is using.
#
# Env (all optional):
#   UE_ROOT                 engine (default ~/UnrealEngine/UE_5.8.4)
#   DINK_PACKAGE_TARGET     game target (default DinkRemaster)
#   DINK_PACKAGE_CONFIG     Development (default) or DebugGame. Never Shipping: it has no automation tests.
#   DINK_PACKAGE_MAPS       '+'-separated maps to cook (default /Game/Dink/_Generated/Maps/L_Greybox_World;
#                           its streaming sublevels are cooked by reference)
#   DINK_COOK_DIRS          '+'-separated extra content dirs (absolute) to cook. Default: every existing one
#                           of Dink/{Kits,Props,Foliage,Camera,Refinements,Audio,Creatures,NPC,Hero,Materials,Textures,_Generated/Sprites}, Characters and Input:
#                           the runtime loads these by string path from Data/Art and Data/Audio JSON,
#                           which the cook cannot see (including runtime-selected sprite frames). Set to "none" to disable.
#   DINK_COMPILE_EDITOR=1   let UAT build the editor target too (default: -nocompileeditor)
#   DINK_ALLOW_CONCURRENT=1 run even though an editor / UBT / UAT process is already running
#
# Log: Saved/Logs/package.log. Prints one PACKAGE OK / PACKAGE FAILED line. Exit code is UAT's
# (2 = preflight failed, 3 = UAT succeeded but the binary is missing).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPROJECT="$PROJECT_DIR/DinkRemaster.uproject"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
RUN_UAT="$UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh"
UNREAL_PAK="$UE_ROOT/Engine/Binaries/Linux/UnrealPak"
TARGET="${DINK_PACKAGE_TARGET:-DinkRemaster}"
CONFIG="${DINK_PACKAGE_CONFIG:-Development}"
MAPS="${DINK_PACKAGE_MAPS:-/Game/Dink/_Generated/Maps/L_Greybox_World}"
LOG_DIR="$PROJECT_DIR/Saved/Logs"
LOG="$LOG_DIR/package.log"

fail() { echo "PACKAGE FAILED: $*"; exit 2; }

# ---- arguments: optional stage directory first, the rest is passed to RunUAT ----
STAGE="$PROJECT_DIR/Saved/StagedBuilds"
if [[ $# -gt 0 && "$1" != -* ]]; then
	STAGE="$1"
	shift
fi
mkdir -p "$STAGE"
STAGE="$(cd "$STAGE" && pwd)"   # RunUAT needs an absolute path
EXTRA_ARGS=("$@")

# ---- preflight ----
[[ -x "$RUN_UAT" ]] || fail "RunUAT not found at $RUN_UAT (set UE_ROOT)"
[[ -f "$UPROJECT" ]] || fail "project not found at $UPROJECT"
[[ "$CONFIG" != "Shipping" && "$CONFIG" != "Test" ]] || fail "DINK_PACKAGE_CONFIG=$CONFIG compiles automation tests out; use Development"
[[ -f "$PROJECT_DIR/Binaries/Linux/libUnrealEditor-DinkRemaster.so" ]] || fail "editor target not built (the cook runs the editor); run Scripts/build.sh first"
[[ -f "$PROJECT_DIR/Content/Dink/Data/Story/dink.json" ]] || fail "Content/Dink/Data/Story/dink.json missing (Scripts/sync_story.py): the story is not a uasset and is staged as raw data"
[[ -f "$PROJECT_DIR/Content/Dink/Data/Facts/dink_globals.csv" ]] || fail "Content/Dink/Data/Facts/dink_globals.csv missing (Scripts/regen_globals.py)"

# GameDefaultMap (Config/DefaultEngine.ini) and every map we are told to cook must exist on disk:
# the greybox is git-ignored and generated.
DEFAULT_MAP="$(sed -n 's/^GameDefaultMap=//p' "$PROJECT_DIR/Config/DefaultEngine.ini" | tail -1 | tr -d '\r')"
DEFAULT_MAP="${DEFAULT_MAP%%.*}"
declare -a MAP_LIST=()
IFS='+' read -r -a MAP_LIST <<<"$MAPS"
declare -a MAPS_TO_CHECK=("${MAP_LIST[@]}")
[[ -n "$DEFAULT_MAP" ]] && MAPS_TO_CHECK+=("$DEFAULT_MAP")
for m in "${MAPS_TO_CHECK[@]}"; do
	m="${m%%.*}"
	file="$PROJECT_DIR/Content/${m#/Game/}.umap"
	[[ -f "$file" ]] || fail "map $m not found ($file). The greybox is generated: run Scripts/import_greybox.sh --region all"
done

# Busy = a headless editor/test/cook, UBT or UAT anywhere, or an editor/game of THIS project (another agent's visible
# playtest game of a different project directory, e.g. ~/Work/DinkPlaytestStage, does not use our Content/Saved/DDC).
if [[ -z "${DINK_ALLOW_CONCURRENT:-}" ]]; then
	busy="$(pgrep -af 'UnrealEditor-Cmd|UnrealBuildTool|RunUAT|AutomationTool' || true)"
	busy_here="$(pgrep -af 'Binaries/Linux/UnrealEditor' | grep -F "$UPROJECT" || true)"
	if [[ -n "$busy$busy_here" ]]; then
		fail "an editor, UnrealBuildTool or AutomationTool process is already running; the machine cannot hold two (DINK_ALLOW_CONCURRENT=1 to override): $(echo "$busy$busy_here" | head -1 | cut -c1-160)"
	fi
fi

# Characters (the template mannequin) is git-ignored and referenced by soft path from ADinkGreyboxCharacter.
[[ -d "$PROJECT_DIR/Content/Characters" ]] || echo "WARNING: Content/Characters missing (Scripts/copy_template_content.sh): the player pawn will have no mesh"

# The probe lives in the DinkProbe module (DeveloperTool, DinkParity plugin); the plugin must not be allow-listed to the editor.
if grep -A3 '"Name": "DinkParity"' "$UPROJECT" | grep -q '"Editor"'; then
	echo "NOTE: DinkParity is allow-listed to the editor in DinkRemaster.uproject: this package will contain no Dink.* automation tests (see Plugins/DinkParity/Docs/packaged_probe.md)"
fi

# ---- the extra cook directories ----
declare -a COOK_DIRS=()
if [[ "${DINK_COOK_DIRS:-}" != "none" ]]; then
	if [[ -n "${DINK_COOK_DIRS:-}" ]]; then
		IFS='+' read -r -a COOK_DIRS <<<"$DINK_COOK_DIRS"
	else
		for d in Dink/Kits Dink/Props Dink/Foliage Dink/Camera Dink/Refinements Dink/Audio Dink/Creatures Dink/NPC Dink/Hero Dink/Materials Dink/Textures Dink/_Generated/Sprites Characters Input; do
			if [[ -d "$PROJECT_DIR/Content/$d" ]]; then COOK_DIRS+=("$PROJECT_DIR/Content/$d"); fi
		done
	fi
fi

join_plus() { local IFS='+'; echo "$*"; }

mkdir -p "$LOG_DIR"

# - BuildCookRun runs UBT (-build), the cook commandlet (-cook), then stages and paks (-stage -pak).
# - -clientconfig=Development, not Shipping: WITH_DEV_AUTOMATION_TESTS and the AutomationController
#   module only exist in non-Shipping/Test configurations, and DeveloperTool modules need
#   bBuildDeveloperTools (also true only outside Shipping/Test).
# - -target=<game target>, no -server: one Game target, no dedicated server.
# - -pak -iostore -compressed: the project sets bUseIoStore=True; assets go to .utoc/.ucas, the
#   files staged as UFS (Dink/Data: story JSON, CSVs, hardness txt) go to the .pak.
# - -MapsToCook: the generated world map (cooks its sublevels by reference). GameDefaultMap is
#   cooked regardless.
# - -cookdir: content only reachable through string paths in Data/Art, Data/Audio JSON and
#   LoadObject calls (see DINK_COOK_DIRS).
# - -nocompileeditor: do not rebuild UnrealEditor targets (another agent may be running one);
#   build the editor first with Scripts/build.sh.
# - -ubtargs=-WaitMutex: queue behind another UBT instead of failing.
# - NO -SkipCookingEditorContent: the engine's Landmass plugin (loaded by the editor as a startup package, not ours) has
#   materials that reference /Engine/EditorMaterials and /Engine/EditorResources; with that flag the cook ends with 16
#   "Content is missing from cook" errors (first run, 7 Nov 2026: exit 25). Cooking the few editor-content packages
#   it needs costs seconds.
# - -prereqs is absent (Windows redistributables); -package/-archive are not used:
#   -stagingdirectory is the output.
# - WAYLAND_DISPLAY/DISPLAY unset like build.sh/test.sh (neither the build nor the cooker needs a display).
UAT_ARGS=(
	BuildCookRun
	-project="$UPROJECT"
	-noP4 -utf8output -unattended -NoSplash
	-platform=Linux -targetplatform=Linux
	-target="$TARGET" -clientconfig="$CONFIG"
	-build -cook -stage -pak -iostore -compressed
	-stagingdirectory="$STAGE"
	-MapsToCook="$(join_plus "${MAP_LIST[@]}")"
	-ubtargs=-WaitMutex
)
if [[ ${#COOK_DIRS[@]} -gt 0 ]]; then UAT_ARGS+=("-cookdir=$(join_plus "${COOK_DIRS[@]}")"); fi
if [[ "${DINK_COMPILE_EDITOR:-0}" != "1" ]]; then UAT_ARGS+=(-nocompileeditor); fi
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then UAT_ARGS+=("${EXTRA_ARGS[@]}"); fi

echo "package: $TARGET Linux $CONFIG -> $STAGE (log: $LOG)"
start=$(date +%s)
rc=0
env -u WAYLAND_DISPLAY -u DISPLAY python3 "$PROJECT_DIR/Scripts/shaderprint_vulkan_workaround.py" --engine "$UE_ROOT/Engine" -- "$RUN_UAT" "${UAT_ARGS[@]}" >"$LOG" 2>&1 || rc=$?
secs=$(( $(date +%s) - start ))

ERR_RE='(: |^)(fatal )?error|Error: |LogCook: Error'
errors=$(grep -cE "$ERR_RE" "$LOG" || true)
warnings=$(grep -cE ': warning|Warning: ' "$LOG" || true)
uat_result=$(grep -E 'AutomationTool exiting with ExitCode=|^BUILD (SUCCESSFUL|FAILED)' "$LOG" | tail -1 || true)

BIN="$STAGE/Linux/$TARGET/Binaries/Linux/$TARGET"
if [[ $rc -eq 0 && ! -x "$BIN" ]]; then
	rc=3
	uat_result="UAT reported success but $BIN is missing"
fi

if [[ $rc -eq 0 ]]; then
	# Best-effort check that the raw data really went into a pak (verified 7 Nov 2026).
	staged_note="staged data not checked (UnrealPak missing)"
	if [[ -x "$UNREAL_PAK" ]]; then
		staged_note="WARNING: Dink/Data/Story/dink.json NOT found in any pak"
		for pak in "$STAGE/Linux/$TARGET/Content/Paks/"*.pak; do
			[[ -f "$pak" ]] || continue
			# (capture first: grep -q closing the pipe early would make UnrealPak die of SIGPIPE and pipefail report failure)
			listing="$("$UNREAL_PAK" "$pak" -List 2>&1 || true)"
			if grep -q 'Dink/Data/Story/dink.json' <<<"$listing"; then
				staged_note="Dink/Data staged in $(basename "$pak")"
				break
			fi
		done
	fi
	echo "PACKAGE OK: $TARGET Linux $CONFIG in ${secs}s (${uat_result:-no result line}; ${warnings} warnings; $staged_note) binary: $BIN log: $LOG"
else
	echo "PACKAGE FAILED (exit $rc) in ${secs}s: ${errors} errors, ${warnings} warnings (${uat_result:-no result line}). First errors:"
	grep -E "$ERR_RE" "$LOG" | head -20 || true
	echo "full log: $LOG"
fi
exit $rc
