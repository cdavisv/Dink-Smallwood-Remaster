# Reviewed game audio

The owner's exported listening review is retained as `approved_choices.csv`, with its SHA256, every decision and the original notes in `review_decisions.json`. The review selects 44 sound-effect takes and retains all 28 music cues. Punch (09), bow (44), axe (48) and bird (49) were rejected; both takes stay in the source archive and their notes remain available for replacement work. No rejected take is imported or selected for playback. No new audio generations were purchased to apply these decisions.

`tools/apply_choices.py` validates the complete review against the asset ledger and engine WAV files before updating anything. Selected ledger rows become `approved`, alternatives become `not_selected`, and rejected rows become `rejected`. Artistic approval does not rewrite the existing source/licence metadata. Delivered MP3s and prepared WAVs remain unchanged.

```bash
python3 SourceAssets/Audio/tools/apply_choices.py --choices /path/audio_choices.csv --check
python3 SourceAssets/Audio/tools/apply_choices.py --choices /path/audio_choices.csv
Scripts/import_approved_audio.sh
```

`selection_manifest.json` records the 72 approved source hashes, durations, looping flags and intended Unreal assets. The import bridge checks PCM16, 44.1 kHz, channel count, source hash and duration, saves the SoundWaves, and publishes `Content/Dink/Data/Audio/approved.json` only after all imports pass. Import receipts live in `Saved/Audio/import_report.json`; the complete log is `Saved/Logs/import_audio.log`.

Music aliases preserve filename extensions: `5.ogg` is Terris, while `5.mid` is the story cue. Original screen music IDs and named script cues resolve to the approved themes. Screen-specific entries disambiguate the Edge of the World uses of music105; a fresh game starts with the approved home theme on screen1. Music loops use the nineteen prepared seam-checked WAVs in `Music/loops`, rather than directly looping the generated originals. The listening review retained the compositions; it does not separately document a musical loop-wrap audition.

The offline `review.html` remains available for future listening decisions. Regenerate its presentation with `python3 SourceAssets/Audio/tools/build_review_page.py`; browser storage and CSV export/import retain the review workflow.

`UDinkAudioSubsystem` plays approved screen and script music, positional sound effects, repeat sounds and active `sp_sound` loops. Original `FDinkAudioStub` cue text/order stays intact for parity; its optional callback performs playback. Original speed22050 maps to pitch1.0, and engine sprite1000 means an unpositioned sound. The subsystem stops inactive/offscreen loops, avoids restarting the same music asset, and restores saved script music without appending a journal cue. `dink.Audio` prints read-only diagnostics.

Headless checks: `DINK_TEST_RUN=audio_review Scripts/test.sh Dink.Audio`. The asset check verifies actual imported duration/loop flags and source WAV metadata; the cue test verifies aliases, future approved replacements, no-sprite handles, pitch and journal/save behavior. A real audio device test passed: a5.95s stereo capture from only the verified game PID confirms approved music and real F-key swing playback; rejected punch9 remained unplayed. Receipts and PCM are in `Saved/Playtest/evidence/audio-private-final`. `Scripts/private_qa_session.py start --audio --pulse-sink <owned-test-sink>` enables an isolated rendered/audio session while the default remains silent.
