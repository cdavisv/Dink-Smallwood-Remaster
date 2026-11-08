#!/usr/bin/env bash
# Run the automation tests inside the PACKAGED game (Scripts/package.sh) headless and report pass/fail.
#
#   Scripts/run_packaged_tests.sh                       filter "Dink.Gameplay.Probe"
#   Scripts/run_packaged_tests.sh Dink.Gameplay.Probe.Ch1Stonebrook
#   Scripts/run_packaged_tests.sh /path/to/stage Dink   first argument may be a stage directory
#
# Run 7 Nov 2026: all nine probe chapters (Ch1-Ch9; six of them on the first run of the day) give the editor's PIE trace md5s (Plugins/DinkParity/Docs/packaged_probe.md). The game gets
# -DinkProbeHold (DinkProbe module: pauses the world until the probe starts and puts the story ahead of the greybox in the tick list,
# as in PIE) and `Automation ...; Now; Quit` (without `Now` the automation controller waits 5 s = 300 frames before the test starts).
#
# Env (all optional):
#   DINK_STAGE_DIR        stage directory given to package.sh (default Saved/StagedBuilds)
#   DINK_PACKAGE_TARGET   game target / binary name (default DinkRemaster)
#   DINK_TEST_TIMEOUT     seconds (default 1800; the whole probe is ~4 min in PIE)
#   DINK_KEEP_SAVES=1     keep the staged build's Saved/SaveGames and Saved/Narrative from a previous run
#                         (default: delete probe_ch*.sav and probe_* reports there first, so chapter 1
#                         starts from a new game and a stale slot cannot satisfy chapter 2)
#   DINK_PIE_TRACE_DIR    where the editor's PIE traces are, for the parity check (default Saved/Narrative)
#   DINK_PER_CHAPTER=0    run the whole "Dink.Gameplay.Probe" filter in ONE game process. Default (1): one
#                         process per chapter (DINK_PROBE_CHAPTERS), because a packaged game cannot start a
#                         second fresh GameInstance the way a second PIE session does; chapters hand over
#                         through Saved/SaveGames/probe_chN.sav on disk, as they do in the editor.
#   DINK_PROBE_CHAPTERS   chapter test names in order (default: Ch1Stonebrook .. Ch9Windemere)
#   DINK_SAVED_DIR        where the packaged game's Saved folder is (default <stage>/Linux/<target>/Saved; verified 7 Nov 2026: the staged Saved folder is used;
#                         FPaths::ShouldSaveToUserDir() would move it to ~/.config/Epic/<project> for an "installed" build)
#   DINK_NOW_CMD          default "Now; " (see above); set to "" to get the controller's 5 s delay back
#   DINK_RUN_TAG          internal: set by the per-chapter loop (log/report suffix)
#
# Outputs (inside the staged project dir, <stage>/Linux/<target>/Saved): Logs/DinkPackagedTest.log,
# Automation/Report/index.json, Narrative/probe_*; the full stdout is Saved/Logs/packaged_test.log here.
# Prints one TESTS PASSED / TESTS FAILED line (+ a trace md5 / parity line per probe chapter).
# Exit 0 only if the game exited 0, the report exists, at least one test ran, none failed and none
# was skipped (a skipped probe is a pass in the editor, a failure here: it means the map or the
# Saved folder was not found).
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARITY_ONLY=0
if [[ "${1:-}" == "--parity-only" ]]; then PARITY_ONLY=1; shift; fi
STAGE="${DINK_STAGE_DIR:-$PROJECT_DIR/Saved/StagedBuilds}"
if [[ $# -gt 0 && -d "$1" ]]; then
	STAGE="$1"
	shift
fi
FILTER="${1:-Dink.Gameplay.Probe}"
TARGET="${DINK_PACKAGE_TARGET:-DinkRemaster}"
TIMEOUT_SECS="${DINK_TEST_TIMEOUT:-1800}"
PIE_TRACE_DIR="${DINK_PIE_TRACE_DIR:-$PROJECT_DIR/Saved/Narrative}"
LOG_DIR="$PROJECT_DIR/Saved/Logs"
TAG="${DINK_RUN_TAG:-}"
LOG="$LOG_DIR/packaged_test${TAG:+_$TAG}.log"

STAGE="$(cd "$STAGE" 2>/dev/null && pwd)" || { echo "TESTS FAILED: stage directory not found (run Scripts/package.sh, or set DINK_STAGE_DIR)"; exit 2; }
STAGED_PROJECT="$STAGE/Linux/$TARGET"
GAME="$STAGED_PROJECT/Binaries/Linux/$TARGET"
SAVED_DIR="${DINK_SAVED_DIR:-$STAGED_PROJECT/Saved}"
REPORT_DIR="$SAVED_DIR/Automation/Report${TAG:+_$TAG}"
NARRATIVE_DIR="$SAVED_DIR/Narrative"
SAVES_DIR="$SAVED_DIR/SaveGames"

# ---- probe traces: md5 of each chapter's trace, compared with the editor's PIE trace ----
# (Ch1's file is stonebrook_probe_trace.txt, chapter N's is probe_chN_trace.txt.) Sets PARITY_BAD.
parity() {
	local pkg name pkg_md5 pie pie_md5
	PARITY_BAD=0
	for pkg in "$NARRATIVE_DIR"/stonebrook_probe_trace.txt "$NARRATIVE_DIR"/probe_ch*_trace.txt; do
		[[ -f "$pkg" ]] || continue
		name="$(basename "$pkg")"
		pkg_md5="$(md5sum "$pkg" | cut -c1-10)"
		pie="$PIE_TRACE_DIR/$name"
		if [[ -f "$pie" ]]; then
			pie_md5="$(md5sum "$pie" | cut -c1-10)"
			if [[ "$pkg_md5" == "$pie_md5" ]]; then
				echo "PARITY OK   $name md5 $pkg_md5 == PIE"
			else
				echo "PARITY DIFF $name md5 packaged $pkg_md5 / PIE $pie_md5 (first differing line: $(diff "$pkg" "$pie" | head -1))"
				PARITY_BAD=1
			fi
		else
			echo "PARITY ?    $name md5 $pkg_md5 (no PIE trace at $pie)"
		fi
	done
}

if [[ $PARITY_ONLY -eq 1 ]]; then parity; exit 0; fi

# ---- default for the probe: one game process per chapter, then one parity check ----
if [[ "$FILTER" == "Dink.Gameplay.Probe" && "${DINK_PER_CHAPTER:-1}" != "0" && -z "$TAG" ]]; then
	chapters=(${DINK_PROBE_CHAPTERS:-Ch1Stonebrook Ch2Terris Ch3Roads Ch4Gold Ch5Bow Ch6Goblins Ch7Sanctuary Ch8Knights Ch9Windemere})
	overall=0
	first=1
	for c in "${chapters[@]}"; do
		keep="${DINK_KEEP_SAVES:-}"
		[[ $first -eq 1 ]] || keep=1
		DINK_RUN_TAG="$c" DINK_KEEP_SAVES="$keep" DINK_SKIP_PARITY=1 "${BASH_SOURCE[0]}" "$STAGE" "Dink.Gameplay.Probe.$c" || overall=1
		first=0
		[[ $overall -eq 0 ]] || break   # a failed chapter leaves no slot for the next one
	done
	"${BASH_SOURCE[0]}" --parity-only "$STAGE" || true
	if [[ $overall -eq 0 ]]; then
		echo "TESTS PASSED: all probe chapters (${chapters[*]}) passed, one packaged game process each"
	else
		echo "TESTS FAILED: a probe chapter failed (see the lines above); later chapters were not run"
	fi
	exit $overall
fi

if [[ ! -x "$GAME" ]]; then
	echo "TESTS FAILED: packaged game not found at $GAME (run Scripts/package.sh)"
	exit 2
fi
mkdir -p "$LOG_DIR"
rm -rf "$REPORT_DIR"
if [[ -z "${DINK_KEEP_SAVES:-}" ]]; then
	# Only inside the staged build: never touch the project's own Saved/.
	rm -f "$SAVES_DIR"/probe_ch*.sav "$NARRATIVE_DIR"/probe_* "$NARRATIVE_DIR"/stonebrook_probe* 2>/dev/null
fi

start=$(date +%s)
# - "Automation RunTests <filter>; Quit": exits 0 on success and 255 on any failure or no match
#   (-TestExit="Automation Test Queue Empty" always exits 1 on Linux, AGENTS.md "Linux problems" 1).
# - WAYLAND_DISPLAY/DISPLAY unset (AGENTS.md "Linux problems" 2); -nullrhi: no GPU, no window.
# - -unattended -nopause -nosplash -nosound -NoSound: no dialogs, no audio device.
# - -stdout -FullStdOutLogOutput -log=...: the log also goes to stdout, captured below.
# - -ReportExportPath: the same index.json the editor run writes (an absolute path in the stage).
# - -UseFixedTimeStep -FPS=60: LaunchEngineLoop.cpp:2460/4727. The editor probe switches to a fixed
#   60 Hz step before PIE starts; a packaged game has been ticking (real-time) since process start,
#   so the new game's first frames would run on wall-clock steps and the trace could not match PIE.
env -u WAYLAND_DISPLAY -u DISPLAY timeout "$TIMEOUT_SECS" "$GAME" \
	-ExecCmds="Automation RunTests $FILTER; ${DINK_NOW_CMD-Now; }Quit" \
	-ReportExportPath="$REPORT_DIR" \
	-nullrhi -unattended -nosplash -nopause -nosound -NoSound \
	-UseFixedTimeStep -FPS=60 -DinkProbeHold \
	-stdout -FullStdOutLogOutput -log=DinkPackagedTest.log \
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
    print(f"NOREPORT 0 0 0 0 0 {e.__class__.__name__}")
    sys.exit(0)
tests = d.get("tests", [])
failed = [t["fullTestPath"] for t in tests if t.get("state") == "Fail"]
skipped = []
for t in tests:
    for e in t.get("entries", []):
        ev = e.get("event", {}) if isinstance(e, dict) else {}
        if "skipped" in str(ev.get("message", "")).lower():
            skipped.append(t["fullTestPath"])
            break
print("OK", len(tests), d.get("succeeded", 0) + d.get("succeededWithWarnings", 0),
      d.get("failed", 0), d.get("succeededWithWarnings", 0), len(skipped),
      " ".join(failed + ["SKIPPED:" + s for s in skipped]))
PY
)
read -r status total passed failed warned skipped bad_names <<<"$summary"

if [[ "$status" != "OK" ]]; then
	echo "TESTS FAILED (game exit $rc) in ${secs}s: no report at $REPORT_DIR/index.json; see $LOG"
	grep -E "Error:|Fatal|TEST COMPLETE|LogAutomation.*(no tests|No tests)" "$LOG" | head -10
	exit 1
fi
PARITY_BAD=0
if [[ -z "${DINK_SKIP_PARITY:-}" ]]; then parity; fi
if [[ $rc -eq 0 && "$failed" -eq 0 && "$skipped" -eq 0 && "$total" -gt 0 ]]; then
	echo "TESTS PASSED: $passed/$total passed, 0 failed ($warned with warnings) [packaged, filter '$FILTER'] in ${secs}s; report: $REPORT_DIR/index.json"
	[[ $PARITY_BAD -eq 0 ]] || echo "NOTE: tests passed but a trace differs from the PIE one (PARITY DIFF above): the package is not a faithful run yet"
	exit 0
fi
echo "TESTS FAILED (game exit $rc): $passed/$total passed, $failed failed, $skipped skipped [packaged, filter '$FILTER'] in ${secs}s. Bad: ${bad_names:-none listed}. Log: $LOG"
grep -E "Result=\{Fail\}" "$LOG" | head -20
exit 1
