#!/usr/bin/env bash
# Run the Unreal automation tests headless (no display, no GPU) and report pass/fail.
#
#   Scripts/test.sh               run every test whose path starts with "Dink"
#   Scripts/test.sh Dink.Core.Combat   run a subset (any automation filter)
#   DINK_TEST_RUN=my_run Scripts/test.sh Dink.Art   isolated log/report for concurrent clients
#
# Needs a built editor target (Scripts/build.sh). Env: UE_ROOT (default ~/UnrealEngine/UE_5.8.4).
# Outputs: Saved/Logs/test.log (full editor log) and Saved/Automation/Report/index.json (+ index.html).
# Prints one summary line. Exit 0 only if the editor exited 0, the report exists, at least one
# test ran, and none failed.
set -uo pipefail

FILTER="${1:-Dink}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPROJECT="$PROJECT_DIR/DinkRemaster.uproject"
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
EDITOR="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"
LOG_DIR="$PROJECT_DIR/Saved/Logs"
LOG="$LOG_DIR/test.log"
REPORT_DIR="$PROJECT_DIR/Saved/Automation/Report"
ENGINE_LOG_NAME="DinkTest.log"
DINK_RUN_SUFFIX="${DINK_TEST_RUN:-}"
if [[ -n "$DINK_RUN_SUFFIX" ]]; then
	# Never let a caller turn the report cleanup below into a path traversal, or
	# silently collide with the legacy default report directory.
	if [[ ! "$DINK_RUN_SUFFIX" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$ || "${DINK_RUN_SUFFIX,,}" == "report" ]]; then
		echo "TESTS FAILED: DINK_TEST_RUN must be 1-64 letters/digits/_/-, start with a letter or digit, and cannot be Report"
		exit 2
	fi
	LOG="$LOG_DIR/test_${DINK_RUN_SUFFIX}.log"
	REPORT_DIR="$PROJECT_DIR/Saved/Automation/$DINK_RUN_SUFFIX"
	ENGINE_LOG_NAME="DinkTest_${DINK_RUN_SUFFIX}.log"
fi
TIMEOUT_SECS="${DINK_TEST_TIMEOUT:-1800}"

if [[ ! -x "$EDITOR" ]]; then
	echo "TESTS FAILED: editor not found at $EDITOR (set UE_ROOT)"
	exit 2
fi
if [[ ! -f "$PROJECT_DIR/Binaries/Linux/libUnrealEditor-DinkRemaster.so" ]]; then
	echo "TESTS FAILED: project not built; run Scripts/build.sh first"
	exit 2
fi
mkdir -p "$LOG_DIR"
rm -rf "$REPORT_DIR"

start=$(date +%s)
# - "Automation RunTests <filter>; Quit": the automation command line queues Quit after the tests
#   and exits with 0 on success, non-zero on any test failure. (-TestExit=... always exits 1.)
# - WAYLAND_DISPLAY/DISPLAY are unset so the headless editor does not query the desktop session;
#   with them set, every frame logs "Querying IsUsingWayland before SDL is initialized" and every
#   test is reported as "succeeded with warnings".
env -u WAYLAND_DISPLAY -u DISPLAY timeout "$TIMEOUT_SECS" "$EDITOR" "$UPROJECT" \
	-ExecCmds="Automation RunTests $FILTER; Quit" \
	-ReportExportPath="$REPORT_DIR" \
	-nullrhi -unattended -nosplash -nopause -nosound -NoSound \
	-stdout -FullStdOutLogOutput -log="$ENGINE_LOG_NAME" \
	>"$LOG" 2>&1
rc=$?
secs=$(( $(date +%s) - start ))

summary=$(python3 - "$REPORT_DIR/index.json" <<'PY'
import json, sys
path = sys.argv[1]
try:
    with open(path, encoding="utf-8-sig") as f:
        d = json.load(f)
except Exception as e:  # missing or unreadable report
    print(f"NOREPORT 0 0 0 0 {e.__class__.__name__}")
    sys.exit(0)
tests = d.get("tests", [])
failed = [t["fullTestPath"] for t in tests if t.get("state") == "Fail"]
print("OK", len(tests), d.get("succeeded", 0) + d.get("succeededWithWarnings", 0),
      d.get("failed", 0), d.get("succeededWithWarnings", 0), " ".join(failed))
PY
)
read -r status total passed failed warned failed_names <<<"$summary"

if [[ "$status" != "OK" ]]; then
	echo "TESTS FAILED (editor exit $rc) in ${secs}s: no report at $REPORT_DIR/index.json; see $LOG"
	grep -E "Error:|Fatal|TEST COMPLETE" "$LOG" | head -10
	exit 1
fi
if [[ $rc -eq 0 && "$failed" -eq 0 && "$total" -gt 0 ]]; then
	echo "TESTS PASSED: $passed/$total passed, 0 failed ($warned with warnings) [filter '$FILTER'] in ${secs}s; report: $REPORT_DIR/index.html"
	exit 0
fi
echo "TESTS FAILED (editor exit $rc): $passed/$total passed, $failed failed [filter '$FILTER'] in ${secs}s. Failed: ${failed_names:-none listed}. Log: $LOG"
grep -E "Result=\{Fail\}" "$LOG" | head -20
exit 1
