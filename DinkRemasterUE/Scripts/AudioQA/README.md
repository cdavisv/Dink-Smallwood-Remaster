# Audio QA tools (15 Nov 2026)

Proof that every sound plays when and where it should, at a sane level, without a crash, in the editor's game and in the
packaged build, and without ever playing on a desk speaker.

| tool | what |
|---|---|
| `audio_coverage.py plan` | a sweep plan (`kind key asset volume seconds`): all approved effects and music takes, the first N spoken lines in story order (from the probe traces) plus every voice once, every footstep and ambience take |
| `audio_coverage.py table` | the coverage table: every 1997 sound id and music cue used by a script or the engine (`bin/dink/story/*.c`, `source/dink/dink.cpp`) -> the remaster's take -> cooked (pak listing) -> heard (recorded RMS in its sweep window) -> played in a gameplay run; loudness per category |
| `run_recorded.sh <out> <steps> [binary]` | a rendered game on the private display :189 with **SDL's disk audio driver**: the device mix is written to `audio.raw` (float32, interleaved) and nothing reaches PulseAudio; a watchdog kills the game if it ever opens a PulseAudio stream. Steps: `console`, `key`, `hold`, `wait`, `waitlog`, `capture`. One Unreal step (run it through `Saved/Gate2Coord/unreal_turn.sh`) |
| `build_mix.py` | `Content/Dink/Data/Audio/mix.json`: per-take gains from measured loudness (ffmpeg ebur128): effects into [-26, -17] LUFS, music at -27 LUFS, outlying voice lines into [-24, -13] LUFS, never past -1 dBFS peak |
| `build_life_data.py` | `Content/Dink/Data/Audio/life_data.json`: the ground class under every 50 px tile of every screen (footsteps), the ambience bed of every screen, the sound of every map.dat warp |
| `prepare_life_takes.py`, `register_life_audio.py`, `import_life_audio.sh` (`synth_life.py`: the old procedural placeholders) | footstep and ambience takes: the generated takes cut and levelled (one footfall per step, beds whole), their loudness and ledger rows, `life.json`, and the editor import into `/Game/Dink/Audio/Life` |

In the game (`DinkAudioLife.cpp`): `dink.AudioQA.Sweep <plan> [gap]`, `dink.AudioQA.Soak <seconds>`, `dink.AudioQA.Stats`.

Why the disk driver: UE 5.8's SDL3 audio opens the server's default sink by name, so `PULSE_SINK` (and
`private_qa_session.py --pulse-sink`) does not route it, and moving its sink-input to a null sink after it appears lets the
first moments reach the speakers. SDL3 in UE is built with the `disk` driver (`SDL_AUDIO_DRIVER=disk`,
`SDL_AUDIO_DISK_OUTPUT_FILE`, `SDL_AUDIO_DISK_TIMESCALE=1`): it is the same mix at the same layer, in real time, with no audio server.

Typical round (each Unreal step is its own `unreal_turn.sh` call):

```bash
python3 -I Scripts/AudioQA/audio_coverage.py plan --out Saved/AudioQA/sweep_plan.tsv --traces Saved/Narrative
Scripts/AudioQA/run_recorded.sh Saved/AudioQA/runB sweep_steps.txt Saved/StagedBuilds/Linux/DinkRemaster/Binaries/Linux/DinkRemaster
python3 -I Scripts/AudioQA/audio_coverage.py table --log Saved/AudioQA/runB/game.log --recording Saved/AudioQA/runB/audio.raw \
    --rate 48000 --channels 2 --listing Saved/AudioQA/pak_listing.txt --out Docs/Verification/AudioQA_15Nov2026
```
