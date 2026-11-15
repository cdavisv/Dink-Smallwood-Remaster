# Voice playback in the game (14 November 2026)

Owner report: in a new game the Mother's lines show as text but nobody speaks.
Cause: the 2,088 approved ElevenLabs recordings were never imported and no code
played them. Fix: `Scripts/import_voice.sh` and `UDinkAudioSubsystem`'s voice
tracker (UE `AGENTS.md`, "Voice lines play in the game").

## Evidence
- `import_summary.json`: all 2,088 approved lines of 29 voices imported, largest
  difference between imported and ledger duration 0.2 microseconds.
- `game_log_voice.txt`: the voice lines of the game log of a new game: the table
  loads 2,088 lines and the opening scene plays `s1-h1-m.main.008` (Mother,
  positional), `.009` (Dink, 2D) and `.010` (Mother, positional) with their texts.
- `opening_recording.mp3`: 36.5 s of the game's own audio stream from start-up
  (music and voices; 64 kbps mono copy of the recorded WAV). `opening_scene.png`:
  the scene at the end of the recording (private Xvfb display).
- `match_scores.txt`: `match_voice.py` (normalised cross-correlation of the
  recording against each source clip, 16 kHz mono): 0.926 at 16.94 s, 0.884 at
  19.86 s, 0.917 at 22.76 s; the control (`s1-h1-m.main.001`, a line that is not
  spoken in this scene) 0.057. The clip spacing (2.92 s, 2.90 s) matches the log
  (2.916 s, 2.912 s). Scores are below 1 because the music plays under the
  voices and the Mother is heard through distance attenuation.
- Tests (private project copy, master 42587b4f plus this change): `Dink.Audio`
  3/3; full `Dink` suite 265/265 (4 warnings, none from audio: an Epic HTTP
  request, missing QA meshes, a refused hardness fit, actors without a world
  context); all 29 `Dink.Gameplay.Probe*` tests pass, so the story timing is
  unchanged.

## How it was recorded
`private_qa_session.py start --audio --pulse-sink dink_voice_qa` on a temporary
PulseAudio null sink, recorded with `parecord` from its monitor. The first run
showed that `--pulse-sink` does not route the game (UE's SDL3 mixer opens the
default device by name; that run played on the speakers and the recording was
silent). The run above used `move_game_stream.py`, which moves the game's own
sink-input to the null sink the moment it appears (and mutes it if it cannot),
so nothing reached the speakers.

## Not verified
- Only the opening scene was listened to by machine. The other 2,085 lines are
  checked by the import (hash, duration) and the tracker unit test, not by ear.
- Loudness balance between voices, music and effects, and the attenuation
  distances (9 m box, 35 m falloff), are first guesses.
- Not run in a packaged build.
