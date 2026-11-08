> Update7Nov2026: the owner confirmed redistribution rights for public GitHub publication; see ../REDISTRIBUTION.md. Earlier unconfirmed-rights notes below describe the prior checkpoint.

# Music drafts

Replacement music for the remaster: **new, original compositions** generated with ElevenLabs
(`eleven_music_v2_5`, instrumental only), described by mood and instrumentation. No prompt names or
imitates any existing song, composer, artist or the original game's tracks. The "replaces" column
below is for the ledger only.

## Status: all 28 cues retained in the owner’s listening review

All 28 drafts were generated on 2026-11-07 in flow `M1M41vE6pzKeEkQYmpi5`, one generation per cue
(`generations_count=1`, `instrumental=true`, `lyrics_type=instrumental`). Total spend:
**23199.84 credits** for 1547 s (25.8 min) of audio, about 15.0 credits per second or
about 900 credits per minute. Cue 01 was generated first as a cost probe (1349.7 credits);
the rest followed after the owner approved the full spend. No generation failed and none had to be retried.

Credits per generation are exactly linear in length: 60 s = 899.8, 90 s = 1349.7, 20 s = 299.93,
15 s = 224.95, 12 s = 179.96 (about 14.997 credits per second). The up-front `estimate_only` figure
for cue 01 was 2475 credits, about 1.8x what was actually charged (1349.7), so do not trust the
estimate for budgeting.

| nn | cue | replaces (original cue / dink.dat value / region) | length | loop flag | credits |
|----|-----|----------------------------------------------------|--------|-----------|---------|
| 01 | title | 1003.mid, start.c (title screen) | 90 s | one-shot | 1349.7 |
| 02 | stonebrook_village | dink.dat 104 (Stonebrook village, 6 screens) | 60 s | loop (seam: NOT clean) | 899.8 |
| 03 | home_interior | dink.dat 105 (interiors) | 60 s | loop (seam: NOT clean) | 899.8 |
| 04 | terris_town | dink.dat 1 and 1005/102/103 (Terris) | 60 s | loop (seam: NOT clean) | 899.8 |
| 05 | overworld_wilds | dink.dat 100 (open country) | 60 s | loop (seam: NOT clean) | 899.8 |
| 06 | wonder | wanderer.mid / Mystery.mid cues (wizard and apparition scenes) | 60 s | loop (seam: NOT clean) | 899.8 |
| 07 | battle | battle.mid (locked fights) | 60 s | loop (seam: NOT clean) | 899.8 |
| 08 | cave | caveexpl.mid and dink.dat 1010 (cave screens) | 60 s | loop (seam: NOT clean) | 899.8 |
| 09 | villain | bullythe.mid (the bully and thugs) | 60 s | loop (seam: NOT clean) | 899.8 |
| 10 | love | love.mid / lovin.mid | 60 s | loop (seam: NOT clean) | 899.8 |
| 11 | sorrow_resolve | insper.mid (after the house fire; the caves) | 90 s | one-shot | 1349.7 |
| 12 | murkwood | dink.dat 1002 (haunted forest) | 60 s | loop (seam: NOT clean) | 899.8 |
| 13 | windemere_port | dink.dat 106 (port town) | 60 s | loop (seam: NOT clean) | 899.8 |
| 14 | royal_court | dink.dat 1011/1012 (the king, Goodheart Castle) | 60 s | loop (seam: NOT clean) | 899.8 |
| 15 | goblin_lands | dink.dat 1004/1009 (goblin camps and sanctuary) | 60 s | loop (seam: NOT clean) | 899.8 |
| 16 | darklands | dink.dat 1007 (Darklands, 46 screens) | 60 s | loop (seam: NOT clean) | 899.8 |
| 17 | koka_isle | dink.dat 1016 (arena island) | 60 s | loop (seam: NOT clean) | 899.8 |
| 18 | snow_castle | dink.dat 107/101 (snow castle) | 60 s | loop (seam: NOT clean) | 899.8 |
| 19 | edge_of_the_world | dink.dat 1013/105 (plateau) | 60 s | loop (seam: NOT clean) | 899.8 |
| 20 | joppa_isle | dink.dat 1008 (Joppa isle) | 60 s | loop (seam: NOT clean) | 899.8 |
| 21 | final_approach | dink.dat 1015/1006/1018 (s7-mil, s7-hell) | 90 s | loop (seam: NOT clean) | 1349.7 |
| 22 | waltz | denube.mid in the cult scene (original used a public-domain waltz; this is a new original waltz) | 60 s | one-shot | 899.8 |
| 23 | stinger_creepy | creepy.mid | 12 s | one-shot | 179.96 |
| 24 | stinger_sneaky | Sneaky.mid | 15 s | one-shot | 224.95 |
| 25 | stinger_urgent | Urgent.mid | 15 s | one-shot | 224.95 |
| 26 | stinger_planning | planning.mid | 20 s | one-shot | 299.93 |
| 27 | stinger_mystery_x | xfiles.mid | 15 s | one-shot | 224.95 |
| 28 | story | story.mid and 5.mid (narration/flashback) | 60 s | one-shot | 899.8 |
| | **total** | | 1547 s | | **23199.84** |

The loop flag is the cue's intended use (`CUES` in `../tools/prepare_music.py`): 02-10, 12-21 are meant
to loop; 01, 11, 22-28 are one-shots (title, the sorrow cue, the waltz, stingers, story). Cue 21 was
asked for 90 s "then loop". "seam" is the measured file-edge check described below.

## Loop seams: none of the 19 loop cues is clean by measurement

The model was asked for music that loops "seamlessly with no fade-out", but it does not guarantee it.
`quality_report.csv` compares the first and last 50 ms of each file. **0 of 19 loop cues pass.**
- Edge level problems (the file fades to or from near silence, or the head and tail RMS differ by more than
  6 dB): cues 02, 04, 05, 06, 09, 12, 13, 17, 19, 20, 21.
- Only a sample jump over 0.10 of full scale between the last and first sample (levels match): cues
  03, 07, 08, 10, 14, 15, 16, 18. That check is strict (a seam at a non-zero-crossing always jumps), so these may
  loop acceptably with a short crossfade; it still needs a person to listen.
- The check cannot tell whether a loop is musically bar-aligned; it only looks at the file edges.
Practical consequence: the plain WAVs must not be used as loops. Use the derived files in `loops/` (see
"Loop files"), which pass the seam check but still need an ear check. The WAVs themselves are deliberately
not trimmed or faded, so nothing has been hidden.

## Loop files (`loops/<nn>_<cue>_loop.wav`)

The 19 loop cues each have a derived loop file: 44.1 kHz, 16-bit PCM, stereo, peak -3 dBFS. They are built
from the engine-ready `<nn>_<cue>.wav` (never from `delivered/`, which is untouched) by
`prepare_music.py`, and are **derived files, not new generations**, so they are not in the asset ledger.
Details are in the script docstring; in short:

1. Leading and trailing near-silence (below -45 dBFS RMS over 20 ms windows) and any monotonic fade-in or
   fade-out ramp at the ends are trimmed (cues 02, 05, 06, 09, 12, 17, 19 and 21 lost between 0.2 s and 8 s
   in total; 21 the most, 8.0 s at the tail, and 06 also 1.8 s at the head).
2. A tempo is estimated from the onset-strength autocorrelation (numpy only) and refined with a comb fit. The loop
   start is a beat near the beginning (nudged by a few ms to a low-jump sample) and the loop end is a whole
   number of 3- or 4-beat bars later, near the end, aligned to the head by envelope correlation, so both cut
   points have the same beat phase. With no clear autocorrelation peak (cues 12 and 16) it falls back to
   zero-crossing points with the smallest 100 ms spectral difference.
3. The last 1.0 s of the file is an equal-power crossfade of the tail with the audio that originally came just
   before the start point. The last sample of the file is therefore the sample that really preceded the
   first one: no click and no level step when it wraps. Play it with the engine's normal loop flag; no
   engine-side crossfade is needed.
4. The same file-edge seam check as `quality_report.csv` is re-run on the loop files and written to
   `loop_report.csv` (trims, tempo, loop points, seam level difference, sample jump, pass/fail, notes).
   **All 19 pass.**

**What this does and does not tell you.** The seam is technically clean (levels match within 6 dB, no sample
jump, nothing near silence). Musical continuity has **not been checked by ear**: the tempo and bar guesses
are statistical, the tempo of ambient cues is low confidence (flagged in `loop_report.csv` notes), and a
bar-aligned cut can still land mid-phrase or mid-note. Cues 02, 05, 09, 10, 18, 19, 20 and 21 have the weakest
spectral/envelope match between tail and head in the report notes (a rising build such as 21, or a slow cue
whose pulse is unclear) and are the first to listen to. Loops are 43 to 60 s long (the rest of each 60 or 90 s
cue is trimmed away).

| cue | tempo (bpm) | loop start - end (s) | length (s) | trimmed head / tail (ms) | seam level diff (dB) | seam jump (FS) | method | result |
|---|---|---|---|---|---|---|---|---|
| 02_stonebrook_village | 144.0 | 1.242 - 58.743 | 57.501 | 0 / 1100 | 0.16 | 0.0010 | tempo | pass |
| 03_home_interior | 72.0 | 2.508 - 59.178 | 56.670 | 0 / 0 | 1.72 | 0.0002 | tempo | pass |
| 04_terris_town | 126.0 (low conf.) | 7.844 - 53.557 | 45.713 | 0 / 0 | 0.99 | 0.0020 | tempo | pass |
| 05_overworld_wilds | 100.0 (low conf.) | 10.212 - 58.214 | 48.002 | 0 / 440 | 1.02 | 0.0004 | tempo | pass |
| 06_wonder | 78.0 | 11.149 - 54.187 | 43.038 | 1760 / 4800 | 0.08 | 0.0003 | tempo | pass |
| 07_battle | 112.0 (low conf.) | 5.893 - 57.325 | 51.431 | 0 / 0 | 0.07 | 0.0007 | tempo | pass |
| 08_cave | 136.0 | 1.329 - 57.770 | 56.441 | 0 / 0 | 0.31 | 0.0001 | tempo | pass |
| 09_villain | 124.0 (low conf.) | 4.367 - 58.071 | 53.704 | 480 / 1580 | 1.99 | 0.0001 | tempo | pass |
| 10_love | 72.0 (low conf.) | 7.505 - 54.998 | 47.492 | 0 / 0 | 1.05 | 0.0004 | tempo | pass |
| 12_murkwood | none | 11.300 - 57.504 | 46.204 | 700 / 0 | 0.34 | 0.0047 | zero-crossing | pass |
| 13_windemere_port | 92.0 (low conf.) | 7.502 - 51.845 | 44.343 | 0 / 0 | 3.63 | 0.0028 | tempo | pass |
| 14_royal_court | 96.0 (low conf.) | 8.157 - 58.168 | 50.011 | 0 / 0 | 1.28 | 0.0005 | tempo | pass |
| 15_goblin_lands | 120.0 | 2.501 - 58.500 | 55.999 | 0 / 0 | 0.69 | 0.0007 | tempo | pass |
| 16_darklands | none | 2.963 - 50.084 | 47.121 | 0 / 0 | 0.18 | 0.0043 | zero-crossing | pass |
| 17_koka_isle | 132.0 (low conf.) | 7.718 - 53.169 | 45.451 | 0 / 200 | 0.32 | 0.0001 | tempo | pass |
| 18_snow_castle | 72.0 | 5.004 - 58.331 | 53.327 | 0 / 0 | 1.37 | 0.0029 | tempo | pass |
| 19_edge_of_the_world | 129.9 (low conf.) | 2.272 - 59.117 | 56.844 | 20 / 640 | 0.78 | 0.0002 | tempo | pass |
| 20_joppa_isle | 144.0 (low conf.) | 5.000 - 51.693 | 46.694 | 0 / 0 | 0.26 | 0.0001 | tempo | pass |
| 21_final_approach | 72.0 (low conf.) | 10.826 - 70.804 | 59.978 | 0 / 7960 | 0.59 | 0.0000 | tempo | pass |

Rebuild: `python3 SourceAssets/Audio/tools/prepare_music.py --loops-only` (needs numpy only; about 10 s;
rewrites `loops/` and `loop_report.csv` from the existing engine-ready WAVs). A full
`prepare_music.py` run re-converts the MP3s first and then rebuilds the loops; `--no-loops` skips them.

## Prompts used

Every prompt was sent with `instrumental=true`, `lyrics_type=instrumental` and the duration shown.
Loop cues carry the phrase "no fade-out, written to loop seamlessly" in the prompt.

- **01_title** (90 s): Cinematic orchestral main theme, heroic with a wry, playful comic edge. Bright brass fanfare and sweeping strings, light woodwind flourishes, mid tempo, steady march-like pulse. Starts modestly and builds in energy to a confident, triumphant finish.
- **02_stonebrook_village** (60 s): Gentle pastoral folk, plucked lute and recorder or flute carrying a simple singable melody, light hand percussion, unhurried relaxed tempo, warm acoustic production. Even energy throughout with no big build and no fade-out, written to loop seamlessly.
- **03_home_interior** (60 s): Soft intimate chamber piece, gentle harp arpeggios with a solo woodwind melody, warm and cosy, slow tempo, close and quiet production. Even, calm energy with no fade-out, written to loop seamlessly.
- **04_terris_town** (60 s): Lively market-town folk dance with fiddle melody, droning hurdy-gurdy, tambourine and stomping foot percussion, bouncy medium tempo, cheerful and bustling, acoustic production. Steady energy with no fade-out, written to loop seamlessly.
- **05_overworld_wilds** (60 s): Airy exploration theme, light strings and woodwinds over a steady travelling rhythm of soft percussion and pizzicato, hopeful and open, moderate tempo, spacious orchestral production. Even energy with no fade-out, written to loop seamlessly.
- **06_wonder** (60 s): Mysterious, shimmering ambient texture of glass harmonica and celesta, slow and floating, suspended open harmony that never fully resolves, soft sustained pads, hushed and magical. Even energy with no fade-out, written to loop seamlessly.
- **07_battle** (60 s): Driving orchestral combat music, thunderous taiko-style drums, relentless low brass ostinato, stabbing strings, fast aggressive tempo, powerful cinematic production. Constant high intensity with no fade-out, written to loop seamlessly.
- **08_cave** (60 s): Dark ambient dungeon atmosphere, sparse dripping-water-like percussion textures, deep low drones, a hesitant sparse plucked motif far apart, slow and cavernous with long reverb. Even low energy with no fade-out, written to loop seamlessly.
- **09_villain** (60 s): Menacing but slightly comic march, lumbering bassoon and tuba melody, snare drum rolls and rim clicks, pompous swaggering moderate tempo, tongue-in-cheek orchestral production. Steady energy with no fade-out, written to loop seamlessly.
- **10_love** (60 s): Tender, slightly cheesy romantic theme in a slow waltz feel, expressive solo oboe melody over lush warm strings and soft harp, gently swaying three-beat rhythm, sentimental. Even energy with no fade-out, written to loop seamlessly.
- **11_sorrow_resolve** (90 s): Sombre solo cello alone in a slow, mournful melody, gradually joined by a full string orchestra that turns quietly resolute and dignified, slow tempo, warm and sad but ending with calm determination.
- **12_murkwood** (60 s): Eerie haunted forest ambience, slightly detuned strings, breathy flutes drifting in and out, distant muffled drums, slow and unsettling with sparse movement. Even low energy with no fade-out, written to loop seamlessly.
- **13_windemere_port** (60 s): Breezy coastal folk, singing accordion melody with strummed mandolin, gentle rolling shuffle rhythm on brushed drums and upright bass, sunny and relaxed medium-slow tempo, acoustic production. Steady energy with no fade-out, written to loop seamlessly.
- **14_royal_court** (60 s): Stately regal fanfare and processional, bold brass choir, rolling timpani, grand pipe organ, dignified moderate tempo, ceremonial and majestic. Steady noble energy with no fade-out, written to loop seamlessly.
- **15_goblin_lands** (60 s): Tribal and rough, pounding frame drums, shrill bone-flute-like whistles, growling low bowed strings, stomping medium tempo, raw and menacing but playful. Steady energy with no fade-out, written to loop seamlessly.
- **16_darklands** (60 s): Oppressive dark ambient soundscape, deep sub-bass drones, metallic scrapes and distant clanks, slow choir-like pads, no melody and no beat, heavy and bleak. Even low energy with no fade-out, written to loop seamlessly.
- **17_koka_isle** (60 s): Exotic island arena music, bright marimba melody over deep log drums and shakers, bright upbeat rhythmic groove at medium-fast tempo, festive and energetic. Steady energy with no fade-out, written to loop seamlessly.
- **18_snow_castle** (60 s): Cold crystalline theme, delicate glockenspiel melody with high shimmering strings, music-box feel, slow tempo, icy and still. Even gentle energy with no fade-out, written to loop seamlessly.
- **19_edge_of_the_world** (60 s): Vast and lonely, wide sustained orchestral string and wind pads with a solo French horn calling a slow melody across empty space, very slow tempo, acoustic orchestral sound only, no synthesizers. Even energy with no fade-out, written to loop seamlessly.
- **20_joppa_isle** (60 s): Quiet fishing-village theme, fingerpicked acoustic guitar with a soft low whistle melody, slow tempo, humble and peaceful, intimate acoustic production. Even calm energy with no fade-out, written to loop seamlessly.
- **21_final_approach** (90 s): Relentless, ominous orchestral build with a dark choir, heavy pounding percussion, low brass and strings in a steadily rising tension, slow-moving harmony climbing higher, intense and foreboding, then holding at a sustained dark intensity ready to loop.
- **22_waltz** (60 s): Original Viennese-style concert waltz for full orchestra, elegant sweeping string melody in three-four time with the classic oom-pah-pah accompaniment, graceful woodwind and horn countermelodies, flowing rubato, ballroom elegance.
- **23_stinger_creepy** (12 s): Short unsettling orchestral stinger, dissonant high string clusters and sliding glissandi swelling uneasily, one-shot cue that ends on a sudden hush.
- **24_stinger_sneaky** (15 s): Short comic tiptoeing cue, quiet staccato pizzicato strings and light bassoon creeping along in a playful sneaking rhythm, one-shot cue with a cheeky final note.
- **25_stinger_urgent** (15 s): Short urgent alarm cue, fast frantic repeating string figures with sharp brass hits and driving snare, very fast tempo, tense and pressing, one-shot cue ending on a loud brass chord.
- **26_stinger_planning** (20 s): Short thoughtful scheming cue, wandering solo clarinet over light plucked pizzicato strings, mischievous and pondering, slow-medium tempo, one-shot cue that resolves with a knowing little flourish.
- **27_stinger_mystery_x** (15 s): Short eerie investigative cue, a lone whistled melody over soft sustained string pads and a slow muted pulse, cool and mysterious, acoustic sounds only with no synthesizers, one-shot cue fading into stillness.
- **28_story** (60 s): Warm narrative underscore, gentle solo piano with soft sustained strings, slow tempo, reflective and tender, storybook atmosphere, gradually opening up and settling gently.

Generation ids, node ids and session ids are in `SourceAssets/asset_ledger.csv` (columns
`generation_id`, `notes`).

## Files

- `delivered/<nn>_<cue>.mp3` (28): exactly as downloaded. Never edit. The connector returns 48 kHz
  stereo at about 194 kbps; there is no lossless original.
- `<nn>_<cue>.wav` (28): engine-ready, 44.1 kHz, 16-bit PCM, stereo, peak -3 dBFS, no trim or fade.
- `loops/<nn>_<cue>_loop.wav` (19) and `loop_report.csv` (19 rows): derived seamless loop files, see "Loop files".
- `quality_report.csv` (28 rows): duration, peak, RMS, clipping count and the loop-seam check. No
  duration deviation and no clipped samples in any file; the only flags are the 19 loop seams.
- Rebuild everything with `python3 SourceAssets/Audio/tools/prepare_music.py` (needs numpy and ffmpeg).

## Cost per minute, for future work

About **900 credits per minute** of generated music (about 15 per second), billed linearly by length,
roughly USD 0.98 per minute at the 16.36 cents billed per 60 s. Examples: a 30 s loop is about 450
credits, a 15 s stinger about 225, a 4-minute track about 3,600. Regenerating a cue costs the same
again, and each take is one generation unless `generations_count` is raised.

## Not yet done

- The owner retained all 28 cues in `../approved_choices.csv` on 7 Nov 2026. Technical measurements alone do not establish artistic quality; the owner’s exported choices are the approval record.
- The 19 loop files in `loops/` pass the technical seam check but nobody has listened to a loop wrap; the
  loop points are automatic, not hand-picked.
- All 28 approved cues are imported into `Content/Dink/Audio/Music`; the runtime selection is in `Content/Dink/Data/Audio/approved.json`. Nineteen use the prepared loop WAVs. See `../README.md` for the import and playback workflow.
- Licence unconfirmed: every ledger row says "ElevenLabs plan terms - redistribution NOT YET CONFIRMED
  by owner", status `candidate`. None of these may ship until the owner confirms the plan terms allow it.
- One take per cue, so there is no a/b choice; weak cues need regenerating (same cost again).
- No similarity check against existing music has been done. The prompts name no artist, song or
  composer, but that does not prove the output resembles nothing; a person should listen with that in mind.
- The waltz (22) is meant to stand in for a public-domain waltz in the cult scene; the prompt asks for an
  original, unnamed Viennese style only.
