#!/usr/bin/env bash
# A rendered game on the private display :189 whose sound is RECORDED, never played: SDL's disk audio driver writes the exact
# device mix (interleaved float32) to a file, so nothing reaches PulseAudio or the speakers. A watchdog kills the game at once if
# a PulseAudio stream of its process ever appears. One Unreal step: run it through Saved/Gate2Coord/unreal_turn.sh.
#
#   Scripts/AudioQA/run_recorded.sh <out dir> <steps file> [game binary]
#
# The steps file has one step per line:  console <command> | key <key> | hold <key> <seconds> | wait <seconds> |
#   waitlog <regex> <timeout s> | capture <name>
# Without a game binary the project's editor runs in -game mode (Scripts/private_qa_session.py); with one (a packaged
# DinkRemaster), that binary runs on the same display. Outputs in <out dir>: audio.raw, game.log, steps.log, captures, format.txt.
set -uo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"; STEPS="$2"; GAME_BIN="${3:-}"
LOG="$OUT/game.log"; RAW="$OUT/audio.raw"; SLOG="$OUT/steps.log"
: >"$SLOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$SLOG"; }
drive() { python3 "$PROJECT_DIR/Scripts/playtest_desktop.py" --private-display :189 "$@" >>"$SLOG" 2>&1; }
export SDL_AUDIO_DRIVER=disk SDL_AUDIODRIVER=disk SDL_AUDIO_DISK_OUTPUT_FILE="$RAW" SDL_AUDIO_DISK_TIMESCALE=1
rm -f "$RAW" "$LOG"
if [[ -z "$GAME_BIN" ]]; then
  START=$(python3 "$PROJECT_DIR/Scripts/private_qa_session.py" start --audio --log "$LOG" 2>&1) || { say "start failed: $START"; exit 2; }
  echo "$START" >>"$SLOG"
  # :189 is shared: a game someone else started there is not ours to drive or record
  if grep -q 'already running' <<<"$START"; then say "another game is already on :189: abort"; exit 3; fi
  GAME_PID=$(python3 -c "import sys,json;sys.path.insert(0,'$PROJECT_DIR/Scripts');import private_qa_session as p;print(json.load(open(p.TOOLS/'game.json'))['game_pid'])")
else
  if ! python3 "$PROJECT_DIR/Scripts/private_qa_session.py" inspect 2>/dev/null | grep -q 'no private game'; then say "another game is already on :189 (or the display cannot be inspected): abort"; exit 3; fi
  AUTH=$(python3 -c "import sys;sys.path.insert(0,'$PROJECT_DIR/Scripts');import private_qa_session as p;p.ensure_display();print(p.AUTH)")
  env -u WAYLAND_DISPLAY DISPLAY=:189 XAUTHORITY="$AUTH" SDL_VIDEODRIVER=x11 MESA_VK_WSI_DEBUG=sw \
    "$GAME_BIN" -sdlvideodriver=x11 -windowed -ResX=1280 -ResY=720 -nosplash -unattended -abslog="$LOG" >"$OUT/game.stdout.log" 2>&1 &
  GAME_PID=$!
fi
if [[ -z "${GAME_PID:-}" ]] || ! kill -0 "$GAME_PID" 2>/dev/null; then say "no live game pid ($GAME_PID): abort"; exit 2; fi
say "game pid $GAME_PID, audio -> $RAW (SDL disk driver)"
# Watchdog: a PulseAudio stream of the game's process means the disk driver was not used: kill it before it is heard.
( while kill -0 "$GAME_PID" 2>/dev/null; do
    if pactl -f json list sink-inputs 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);sys.exit(0 if any(str(s.get('properties',{}).get('application.process.id'))=='$GAME_PID' for s in d) else 1)"; then
      kill -9 "$GAME_PID"; echo "WATCHDOG: the game opened a PulseAudio stream; killed" >>"$SLOG"; fi
    sleep 0.2; done ) &
WATCH=$!
waitlog() { local re="$1" t="$2" i=0; while (( i < t*2 )); do grep -qE "$re" "$LOG" 2>/dev/null && return 0; kill -0 "$GAME_PID" 2>/dev/null || return 2; sleep 0.5; i=$((i+1)); done; return 1; }
waitlog 'Audio life:|LogDinkAudioLife' 240 || say "no audio-life line yet"
waitlog 'DINK SCREEN|Entered screen|screen 1\b|OnScreenEntered|LogDinkNarrative' 120 || true
sleep 8
while IFS= read -r line; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  kill -0 "$GAME_PID" 2>/dev/null || { say "game exited before: $line"; break; }
  cmd=${line%% *}; arg=${line#* }
  say "$line"
  case "$cmd" in
    console) drive console "$arg" ;;
    key) drive key "$arg" ;;
    hold) drive hold ${arg% *} ${arg##* } ;;
    wait) sleep "$arg" ;;
    waitlog) re=${arg% *}; t=${arg##* }; waitlog "$re" "$t" || say "  (timeout or exit waiting for $re)" ;;
    capture) drive capture "$OUT/$arg.png" ;;
    *) say "unknown step $cmd" ;;
  esac
done <"$STEPS"
say "steps done; stopping"
if [[ -z "$GAME_BIN" ]]; then python3 "$PROJECT_DIR/Scripts/private_qa_session.py" stop-game >>"$SLOG" 2>&1; else kill "$GAME_PID" 2>/dev/null; fi
for i in $(seq 1 60); do kill -0 "$GAME_PID" 2>/dev/null || break; sleep 0.5; done
kill -9 "$GAME_PID" 2>/dev/null; kill "$WATCH" 2>/dev/null
grep -E 'LogAudioMixer|AudioMixerSDL|SDL.*audio|Audio Device' "$LOG" | head -20 >"$OUT/format.txt"
ls -la "$RAW" | tee -a "$SLOG"
grep -c WATCHDOG "$SLOG" >/dev/null && grep WATCHDOG "$SLOG"
say "RECORDED RUN DONE"
