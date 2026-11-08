#!/usr/bin/env bash
# Compile the DinkRemasterEditor target (Linux, Development) with the engine's build tool.
#
#   Scripts/build.sh            incremental build
#   Scripts/build.sh -Clean     pass extra args straight to UnrealBuildTool (here: clean first)
#
# Env: UE_ROOT (default ~/UnrealEngine/UE_5.8.4).
# Full log: Saved/Logs/build.log. Prints one summary line; exit code is UBT's (0 = success).
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPROJECT="$PROJECT_DIR/DinkRemaster.uproject"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
BUILD_SH="$UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh"
LOG_DIR="$PROJECT_DIR/Saved/Logs"
LOG="$LOG_DIR/build.log"

if [[ ! -x "$BUILD_SH" ]]; then
	echo "BUILD FAILED: engine build tool not found at $BUILD_SH (set UE_ROOT)"
	exit 2
fi
mkdir -p "$LOG_DIR"

start=$(date +%s)
"$BUILD_SH" DinkRemasterEditor Linux Development -Project="$UPROJECT" -WaitMutex -NoHotReloadFromIDE "$@" >"$LOG" 2>&1
rc=$?
secs=$(( $(date +%s) - start ))

errors=$(grep -cE ': (fatal )?error' "$LOG" || true)
warnings=$(grep -cE ': warning' "$LOG" || true)
result=$(grep -E '^Result: ' "$LOG" | tail -1)

if [[ $rc -eq 0 ]]; then
	echo "BUILD OK: DinkRemasterEditor Linux Development in ${secs}s (${result:-no result line}; ${warnings} warnings) log: $LOG"
else
	echo "BUILD FAILED (exit $rc) in ${secs}s: ${errors} errors, ${warnings} warnings (${result:-no result line}). First errors:"
	grep -E ': (fatal )?error' "$LOG" | head -20
	echo "full log: $LOG"
fi
exit $rc
