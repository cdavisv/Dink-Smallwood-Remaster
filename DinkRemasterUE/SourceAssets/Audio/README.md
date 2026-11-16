# Reviewed game audio

The owner's exported listening review is retained as `approved_choices.csv`, with its SHA256, every decision and the original notes in `review_decisions.json`. The review selects 44 sound-effect takes and retains all 28 music cues. Punch (09), bow (44), axe (48) and bird (49) were rejected; both takes stay in the source archive and their notes remain available for replacement work. No rejected take is imported or selected for playback. No new audio generations were purchased to apply these decisions.

**Regenerated replacements (16 Nov 2026).** Punch, bow, axe and bird were regenerated (24 takes, 84 credits; spec, prompts, measurements and picks in `SFX/redo_15Nov2026.json`, listening sheet `Docs/Verification/AudioQA_15Nov2026/redo_takes.md`). The spec's `picks` (09_punch_e, 44_bow1_i, 48_axe_i, 49_bird1_c) are applied by `apply_choices.py` on top of the owner's export, which stays unchanged with its original hash; the runtime manifest lists them under `redo`; no effect is left without a take: 48 effects, 76 approved assets. The picks were made by measurement and spectrogram and are not yet heard by the owner; to change one, edit `picks` and rerun `apply_choices.py` and the import.

`tools/apply_choices.py` validates the complete review against the asset ledger and engine WAV files before updating anything. Selected ledger rows become `approved`, alternatives become `not_selected`, and rejected rows become `rejected`. Artistic approval does not rewrite the existing source/licence metadata. Delivered MP3s and prepared WAVs remain unchanged.

```bash
python3 SourceAssets/Audio/tools/apply_choices.py --choices /path/audio_choices.csv --check
python3 SourceAssets/Audio/tools/apply_choices.py --choices /path/audio_choices.csv
Scripts/import_approved_audio.sh
```

`selection_manifest.json` records the 75 approved source hashes, durations, looping flags and intended Unreal assets. The import bridge checks PCM16, 44.1 kHz, channel count, source hash and duration, saves the SoundWaves, and publishes `Content/Dink/Data/Audio/approved.json` only after all imports pass. Import receipts live in `Saved/Audio/import_report.json`; the complete log is `Saved/Logs/import_audio.log`.

Music aliases preserve filename extensions: `5.ogg` is Terris, while `5.mid` is the story cue. Original screen music IDs and named script cues resolve to the approved themes. Screen-specific entries disambiguate the Edge of the World uses of music105; a fresh game starts with the approved home theme on screen1. Music loops use the nineteen prepared seam-checked WAVs in `Music/loops`, rather than directly looping the generated originals. The listening review retained the compositions; it does not separately document a musical loop-wrap audition.

The offline `review.html` remains available for future listening decisions. Regenerate its presentation with `python3 SourceAssets/Audio/tools/build_review_page.py`; browser storage and CSV export/import retain the review workflow.

`UDinkAudioSubsystem` plays approved screen and script music, positional sound effects, repeat sounds and active `sp_sound` loops. Original `FDinkAudioStub` cue text/order stays intact for parity; its optional callback performs playback. Original speed22050 maps to pitch1.0, and engine sprite1000 means an unpositioned sound. The subsystem stops inactive/offscreen loops, avoids restarting the same music asset, and restores saved script music without appending a journal cue. `dink.Audio` prints read-only diagnostics.

Headless checks: `DINK_TEST_RUN=audio_review Scripts/test.sh Dink.Audio`. The asset check verifies actual imported duration/loop flags and source WAV metadata; the cue test verifies aliases, future approved replacements, no-sprite handles, pitch and journal/save behavior. A real audio device test passed: a5.95s stereo capture from only the verified game PID confirms approved music and real F-key swing playback; rejected punch9 remained unplayed. Receipts and PCM are in `Saved/Playtest/evidence/audio-private-final`. `Scripts/private_qa_session.py start --audio --pulse-sink <owned-test-sink>` enables an isolated rendered/audio session while the default remains silent.

## Mix, life layer and audio QA (15-16 Nov 2026)

- **Loudness:** `Content/Dink/Data/Audio/mix.json` (`Scripts/AudioQA/build_mix.py`) holds a gain per approved effect and music take and per outlying voice line, measured from the takes (ffmpeg ebur128): effects in [-26, -17] LUFS with a -4 dBFS peak ceiling (a mono effect panned to one speaker gains 3 dB), music at -27 LUFS, voice lines outside [-24, -13] LUFS moved to the edge. The takes are untouched. A master limiter holds the output under -1.5 dBFS (digital peak detector, 5 ms look-ahead: the engine's default analog detector let peaks through, `Dink.Audio.MasterLimiterHoldsCeiling`).
- **3D:** effects are attenuated from Dink on the 1997 curve (-24 dB at 600 px, dink.cpp:6368-6389) and panned from the camera (`FDinkAudioMix`, `UDinkAudioLifeSubsystem`).
- **1997 engine sounds:** status-bar ticks, hurt grunts, talk-menu clicks and warp sounds are reproduced from the game state by `UDinkAudioLifeSubsystem` (DinkAudioLife.cpp).
- **Life layer:** footsteps by the 1997 tile class and ambience beds per screen (`Content/Dink/Data/Audio/life_data.json`, `life.json`; sources in `Life/`, procedural placeholders until generated takes replace them, `Scripts/AudioQA/synth_life.py`, `register_life_audio.py`, `import_life_audio.sh`). Switch: `dink.Audio.Life`.
- **Rejected effects:** 9, 44, 48 and 49 were regenerated on 16 Nov 2026 (see above). 48 is the thrown axe's hit sound (`item-axe.c:128-129`, `sp_attack_hit_sound`; the engine plays it, dink.cpp:14282-14359).
- **QA:** `Scripts/AudioQA/README.md` (recorded runs through SDL's disk driver, never the speakers; coverage table in `Docs/Verification/AudioQA_15Nov2026`).
