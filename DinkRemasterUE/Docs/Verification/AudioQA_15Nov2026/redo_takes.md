# Regenerated effects 9 (punch), 44 (bow), 48 (axe), 49 (bird): takes, measurements, picks (16 Nov 2026)

The owner's listening review rejected both takes of four effects. Punch, bow and bird were regenerated first; the axe was
added by owner decision at 08:40 the same morning. Measured on the delivered MP3s, punch was -50.4 and
-42.2 LUFS, the bow -53.9 and -41.2 LUFS, and the bird -5.8 LUFS with peaks above full scale. Regeneration spec, prompts and
every generation id: `SourceAssets/Audio/SFX/redo_15Nov2026.json`. Ledger: one row per take in `SourceAssets/asset_ledger.csv`.

- **Tool:** ElevenLabs `eleven_text_to_sound_v2`, flow `S9G2dfsEEOV1Jl8tMqUG`, three variations per run, 16 Nov 2026.
- **Cost:** 24 takes, 84 credits (3 per 1 s take, 7 per 2 s take, as charged by the connector).
- **Rules (from the spec):** reject a take whose sample peak is below -12 dBFS or that clips (3 or more samples at or above
  full scale, or any sample over 1.0). The keepers are prepared with `tools/prepare_sfx.py`: mono, leading silence trimmed,
  cut to the spec's length with a 15 ms fade, peak at -3 dBFS.
- **Measurements:** ffmpeg `ebur128=peak=true` for integrated LUFS and true peak, plus a float decode for sample peak and
  clipped samples. All measurements are on the delivered MP3s.

**How the picks were made.** Nobody has listened to these takes yet. The picks rest on the measurements above, the
50 ms RMS envelope and the spectrograms in this folder. The owner should listen to `09_punch_e`, `44_bow1_i` and
`48_axe_i` and `49_bird1_c`, and to the bird alternatives `d` and `e`, before calling them final. Clips of each pick and
runner-up are in `clips/` (see the end of this sheet).

## All takes

| take | round | LUFS | sample peak dBFS | true peak dBTP | clipped samples | credits | verdict | why |
|---|---|---|---|---|---|---|---|---|
| `09_punch_c` | 1 | -44.3 | -18.66 | -18.7 | 0 | 3 | rejected | too quiet (peak -18.7 dBFS < -12) |
| `09_punch_d` | 1 | -16.4 | +0.19 | +0.2 | 3 | 3 | rejected | clips (3 samples at/above full scale) |
| `09_punch_e` | 1 | -26.2 | -3.67 | -3.6 | 0 | 3 | **picked** | inside the rules |
| `44_bow1_c` | 1 | -43.9 | -25.99 | -25.8 | 0 | 3 | rejected | too quiet (peak -26.0 dBFS) |
| `44_bow1_d` | 1 | -52.3 | -38.48 | -38.5 | 0 | 3 | rejected | too quiet (peak -38.5 dBFS) |
| `44_bow1_e` | 1 | -45.9 | -32.12 | -31.9 | 0 | 3 | rejected | too quiet (peak -32.1 dBFS) |
| `44_bow1_f` | 2 | -15.0 | +1.77 | +2.4 | 108 | 3 | rejected | clips |
| `44_bow1_g` | 2 | -12.8 | +1.11 | +1.3 | 22 | 3 | rejected | clips |
| `44_bow1_h` | 2 | -13.8 | +1.38 | +1.4 | 55 | 3 | rejected | clips |
| `44_bow1_i` | 3 | -19.5 | -0.35 | -0.3 | 0 | 3 | **picked** | inside the rules |
| `44_bow1_j` | 3 | -17.3 | +0.37 | +0.4 | 3 | 3 | rejected | clips |
| `44_bow1_k` | 3 | -14.0 | +0.40 | +0.4 | 5 | 3 | rejected | clips |
| `48_axe_c` | 1 | -8.4 | +1.24 | +1.3 | 78 | 3 | rejected | clips |
| `48_axe_d` | 1 | -13.7 | +0.74 | +0.8 | 35 | 3 | rejected | clips |
| `48_axe_e` | 1 | -12.8 | +0.87 | +0.9 | 16 | 3 | rejected | clips |
| `48_axe_f` | 2 | -14.6 | +0.77 | +0.8 | 110 | 3 | rejected | clips |
| `48_axe_g` | 2 | -10.0 | +0.85 | +0.9 | 56 | 3 | rejected | clips |
| `48_axe_h` | 2 | -14.1 | +1.06 | +1.1 | 230 | 3 | rejected | clips |
| `48_axe_i` | 3 | -22.8 | -2.75 | -2.7 | 0 | 3 | **picked** | inside the rules |
| `48_axe_j` | 3 | -50.8 | -27.79 | -27.8 | 0 | 3 | rejected | too quiet (peak -27.8 dBFS) |
| `48_axe_k` | 3 | -43.9 | -21.60 | -21.6 | 0 | 3 | rejected | too quiet (peak -21.6 dBFS) |
| `49_bird1_c` | 1 | -10.0 | -0.25 | -0.2 | 0 | 7 | **picked** | inside the rules |
| `49_bird1_d` | 1 | -12.0 | -0.39 | -0.4 | 0 | 7 | kept | inside the rules |
| `49_bird1_e` | 1 | -15.6 | -0.86 | -0.9 | 0 | 7 | kept | inside the rules |

### Why the bow took three rounds

1. **Round 1** used the spec prompt. All three takes came back as a soft twang (peaks -26 to -38 dBFS), which is the same
   fault as the rejected originals.
2. **Round 2** asked for "a loud, close-up archery shot ... at full volume". All three takes clipped.
3. **Round 3** dropped "full volume" and used prompt influence 0.6 (round-3 prompt in the spec). One take of three, `i`,
   passed the rules.

### The axe

Sound 48 is not called by any script with `playsound`. `item-axe.c:128-129` makes it the thrown axe's
`sp_attack_hit_sound` at 13000 Hz, and the engine plays it when the axe missile strikes something
(dink.cpp:14282-14287, 14306-14311, 14354-14359), pitched down to 0.59.

1. **Round 1** asked for a heavy, close, punchy metal impact. All three takes clipped.
2. **Round 2** used cleaner wording at influence 0.6, which is what fixed the bow. All three clipped again.
3. **Round 3** asked for a hatchet hitting a post "a few metres away" at influence 0.4. One take, `i`, passed the rules;
   the other two came back near-silent.

## Prepared WAVs (what the game imports, before the mix gain)

| WAV | length | LUFS | peak |
|---|---|---|---|
| `09_punch_e.wav` | 0.45 s | -27.2 | -3.0 dBFS |
| `44_bow1_i.wav` | 0.70 s | -25.0 | -3.0 dBFS |
| `48_axe_i.wav` | 0.50 s (51 ms leading silence trimmed) | -25.6 | -3.0 dBFS |
| `49_bird1_c.wav` | 1.80 s (48 ms leading silence trimmed) | -14.6 | -3.0 dBFS |
| `49_bird1_d.wav` | 1.80 s | -16.4 | -3.0 dBFS |
| `49_bird1_e.wav` | 1.80 s | -19.9 | -3.0 dBFS |

`Content/Dink/Data/Audio/mix.json` (`Scripts/AudioQA/build_mix.py`) then moves each effect into the [-26, -17] LUFS window,
under a -4 dBFS peak ceiling. Not one of the trims removes more than 0.01 % of a take's energy.

## The picks

- **`09_punch_e`.** It is the only round-1 punch inside the rules. It is one broadband slap transient (up to 16 kHz) in the
  first 50 ms over a low thud, falling below -50 dB by 0.2 s. A faint low tone of about 600 Hz stays at about -60 dB to
  0.9 s, and the 0.45 s cut removes most of it. Sound 9 is the default hit for fists and most monsters
  (dink.cpp:14284, 14308, 14356, 15551).
- **`44_bow1_i`.** It is the only bow take in three rounds that is neither near-silent nor clipped. It has a soft 80 ms
  string pull, a broadband snap at 0.08-0.15 s, and a short whoosh. Script `item-b1.c` also plays it at 14050 Hz for the
  power shot (pitch 0.64), which makes it a lower, heavier release.
- **`48_axe_i`.** It is the only axe take in three rounds inside the rules. It is one broadband impact at 0.07-0.15 s with a
  woody low-mid body (0.7-1 kHz) and a decay below -48 dB by 0.25 s. The game plays it at 13000 Hz (pitch 0.59), a lower,
  heavier hit.
- **`49_bird1_c`.** It has two cries at once with slow pitch glides (2 to 4.5 kHz) over 1.3 s, the most like birds
  "calling" of the three. Seth's line in `s7-boss.c:185-186` plays it: "Listen to the birds.. even they are calling for
  your heart."
  - **`d`** is chirps with two broadband bursts (0.3 s, 0.7 s).
  - **`e`** is a regular trill at about 10 Hz that reads as mechanical in the spectrogram.
  - Both alternatives are prepared and ledgered `not_selected`. To change the pick, edit `picks` in the spec and run
    `apply_choices.py`.

Spectrograms (log magnitude, 0-16 kHz): `redo_spectrogram_punch_e_bow_i.png`, `redo_spectrogram_axe_i.png`,
`redo_spectrogram_bird_c_d_e.png`.

## Wiring

- **Picks:** the spec's `picks` section holds them. `tools/apply_choices.py` applies them on top of the owner's retained
  export `approved_choices.csv`, which is unchanged and keeps its original hash.
- **Manifest:** `selection_manifest.json` and the runtime `approved.json` now hold 48 effects (44 from the review plus the
  4 regenerated ones). `rejected` is empty, and a new `redo` list holds the four replacements.
- **Ledger:** the picked rows are `approved` with the note "Audio QA pick ... owner listening pending". The owner's rejected
  `a`/`b` rows stay `rejected`.
- **Import:** `Scripts/import_approved_audio.sh`.

## Clips to listen to (prepared WAVs as imported, Ogg Vorbis q6)

These are the takes at the level the game imports them (-3 dBFS peak), before the mix gain and before 3D panning. Where
no other take passed the rules, the runner-up is the take that broke them least: the fewest clipped samples. Its clipping
is baked in, so listen for distortion on the attack.

| effect | pick | runner-up |
|---|---|---|
| 9 punch | `clips/redo_09_punch_e_pick.ogg` | `clips/redo_09_punch_d_runnerup_rejected_clips.ogg` (3 clipped samples) |
| 44 bow | `clips/redo_44_bow1_i_pick.ogg` | `clips/redo_44_bow1_j_runnerup_rejected_clips.ogg` (3 clipped samples) |
| 48 axe | `clips/redo_48_axe_i_pick.ogg` | `clips/redo_48_axe_e_runnerup_rejected_clips.ogg` (16 clipped samples) |
| 49 bird | `clips/redo_49_bird1_c_pick.ogg` | `clips/redo_49_bird1_d_runnerup.ogg` (inside the rules) |
