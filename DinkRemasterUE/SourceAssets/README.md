> Current checkpoint (7Nov2026): listening decisions are applied (44SFX/28music), and the owner confirmed public audio redistribution rights. See Audio/README.md and Audio/REDISTRIBUTION.md. Older generation-stage notes below are historical.

# SourceAssets

Source and raw material for third-party or generated assets. Nothing here is imported into
`Content/` automatically; a person (or a later import step) picks from here deliberately.

## Layout

```
SourceAssets/
  asset_ledger.csv            one row per delivered third-party / generated file (see below)
  Audio/
    SFX/
      delivered/              files exactly as downloaded (128 kbps MP3). Never edit these.
      <slot>_<cue>_<a|b>.wav  engine-ready versions built from delivered/ (44.1 kHz, 16-bit PCM)
      quality_report.csv      measurable checks per delivered file (levels, durations, flags)
    Music/
      delivered/              music MP3s exactly as downloaded. Never edit these.
      <nn>_<cue>.wav          engine-ready versions (44.1 kHz, 16-bit PCM, stereo)
      quality_report.csv      measurable checks per delivered file (levels, loop seam, flags)
      README.md               cue map, prompts, cost, what is not done
    tools/
      prepare_sfx.py          rebuilds every SFX WAV and quality_report.csv from delivered/
      prepare_music.py        same for the music WAVs and report (needs numpy as well)
```

File names: `<slot>_<cue>_<variant>`. `slot` is the original game's `playsound` number, `cue` is
the original file name without `.wav` (for example `01_quack` replaces `QUACK.WAV`), and
`variant` is `a` or `b`.

## The ledger rule

**Every third-party or generated asset gets a row in `asset_ledger.csv` before it is used** in
the game, a level, a build or a release. The row records where the file came from (tool, model,
prompt, parameters, generation id), what it replaces, the licence status, a SHA-256 of the
delivered file, and a status. `status` starts at `candidate`; change it only when a person
decides. If the licence column says redistribution is not confirmed, the asset must not ship.

Columns: `asset_path`, `derived_path`, `kind`, `replaces`, `source`, `tool_model`, `prompt`,
`parameters`, `generation_id`, `flow_id`, `generated_on`, `credits`, `licence`, `sha256`,
`duration_s`, `status`, `notes`.

## Sound effects: two candidates per sound

The 48 replacement sound effects were generated with ElevenLabs (`eleven_text_to_sound_v2`,
prompt influence 0.5). Each sound has **two candidates, `a` and `b`** (96 files). Nobody has
listened to them yet and the measurements in `quality_report.csv` say nothing about whether a
sound is good or fits the game. **A person must choose one by ear** and record the choice (set
the chosen row to an approved status and leave the other as `candidate` or mark it rejected).

The delivered files are **128 kbps MP3** because that is what the generation connector returns;
there is no lossless original. The WAVs are decoded from those MP3s, so they cannot be better
than the MP3 quality.

## How the WAVs are made

`python3 SourceAssets/Audio/tools/prepare_sfx.py` (Python 3 standard library plus `ffmpeg`):

- 44.1 kHz, 16-bit PCM, peak-normalised to -3 dBFS with one constant gain per file.
- One-shots: mono (L+R)/2, leading silence trimmed (first sample reaching -50 dBFS, with 2 ms kept
  before it) so impacts start promptly.
- Loops (slots 23 `fire` and 34 `save`): stereo kept, **not trimmed and not faded**, so the
  seamless loop is not broken. Check the loop point in the engine before relying on it.

The script also rewrites `Audio/SFX/quality_report.csv`. Flags there are measurable only:
effectively silent (peak below -40 dB), duration more than 25% off the requested length, more
than 150 ms of leading silence on a snappy sound (hits, clicks, swings), and clipping (at least
3 decoded samples at or above 0.999 full scale, or any decoded sample above full scale).

## Music

The 28 replacement music cues were generated with ElevenLabs (`eleven_music_v2_5`, instrumental only)
as **new original compositions** described by mood and instrumentation; prompts never name or
imitate an existing song, composer or the original game's tracks. There is **one take per cue**
(28 MP3s, 28 WAVs). The cue map, prompts, credits per cue and loop flags are in
`Audio/Music/README.md`.

The spend was 23,199.84 credits for 1,547 s of audio, about 900 credits per minute of music.
Nobody has listened to any of it. Nothing is imported, and every ledger row says redistribution is NOT
YET CONFIRMED by the owner, so none of it may ship.

Music files are named `<nn>_<cue>.mp3` / `.wav` (no a/b variants). The delivered MP3s are what the
connector returns (48 kHz stereo, about 194 kbps, no lossless original). The WAVs are made by
`python3 SourceAssets/Audio/tools/prepare_music.py`: 44.1 kHz, 16-bit PCM, stereo, peak-normalised to
-3 dBFS with one constant gain, not trimmed and not faded, so a loop is not broken by the conversion.
`Audio/Music/quality_report.csv` has duration, peak, RMS, clipping count and a loop-seam check (first
versus last 50 ms of the file). Like the SFX report it is measurement only. **None of the 19 cues meant
to loop has a clean seam by that check** (11 fade to or from near silence or change level, 8 differ only
by a sample jump), so each needs a loop point or crossfade chosen by ear before it can loop in the engine.

## Review page

`xdg-open SourceAssets/Audio/review.html` opens an offline page (no network, works from `file://`) with
every SFX slot (takes a and b side by side, prompt, clipping/peak flags) and every music cue (delivered MP3,
loop file with a loop checkbox, seam numbers, the weakest-match warning). Pick a / b / neither or
keep / regenerate / needs loop retune and add notes; they are remembered in the browser. "Export choices"
downloads `audio_choices.csv` (`kind,id,choice,note`) and "Import choices" reads it back. A person then
applies that CSV to the ledger's `status` column by hand; the page changes no other file. After files
change, rebuild the page with `python3 SourceAssets/Audio/tools/build_review_page.py` (standard library only).
