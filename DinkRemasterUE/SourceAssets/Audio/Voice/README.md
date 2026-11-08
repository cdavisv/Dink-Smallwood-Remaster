> Update7Nov2026: the owner confirmed redistribution rights for public GitHub publication; see ../REDISTRIBUTION.md. Earlier unconfirmed-rights notes below describe the prior checkpoint.

# Voice lines (started 7 Nov 2026)

Spoken dialogue for the remaster, generated with ElevenLabs through the owner's
connector. Nothing here ships until the owner confirms the ElevenLabs plan's
redistribution terms for a free fan game: every row in `../../asset_ledger.csv`
for a voice file carries status `candidate` until then.

## Source of the lines
- The text is the 1997 script, verbatim, as converted into Ink
  (`Content/Dink/Data/Story/dink.json`): 2,125 unique spoken lines, 68,486
  characters, 377 distinct (script, speaker) pairs. 812 lines are Dink's.
- Each Ink line carries tags `id:<script>.<block>.<n>`, `say:<say form>`,
  `spk:<speaker expression>` (`1` = Dink, `current_sprite` = the script's own
  sprite, else a sprite variable of the script), `col:<text colour>`.
- `voice_lines.csv` (here, once the cast map is done) is the line table joined
  with character, voice archetype and kind (`dialogue`, `object`, `system`,
  `narration`). `system` lines (`* HYPER BOOTS BOUGHT *`, `I found <N> gold.`)
  are never voiced. Six lines interpolate a number at runtime and are marked
  `dynamic`.
- `tts_text` is the line prepared for text to speech: the same words, with the
  script's stage directions in angle brackets (`<shiver>`, `<chuckle>`) turned
  into ElevenLabs v4 audio tags (`[shivers]`, `[chuckles]`). The on-screen text
  stays the original. No word is ever added, removed or changed.

## Voices
- Every voice is designed from a text description (`eleven_ttv_v3`), never
  cloned from a recording, and never described by reference to a real person.
  The description and the verbatim preview line are kept per voice in
  `voices.csv` and in the ledger. Stock "premade" and "professional" library
  voices are not used: they are other people's voices under their own terms.
- The owner picks one of the three previews per voice; only then is it saved to
  the workspace library and used for lines.
- Cost (measured 7 Nov 2026, `eleven_v4`): 1 credit per character of text, so
  one take of the whole script is about 68,500 credits (about 12 USD at the
  quoted rate); two takes per line double that. Designing a voice costs a
  separate, small amount per round of three previews.

## Files
- `voice_cast.csv` (377 script/speaker pairs -> character, voice, kind),
  `voices.csv` (29 voices with casting note and verbatim preview text),
  `voice_lines.csv` (all 2,125 lines with character, voice, kind, `tts_text`),
  `voice_report.md` (counts, stage-direction map, the 29 low-confidence pairs);
  `tools/build_cast.py` regenerates them from the Ink data.
- `voice_designs.json` and `previews/`: every design round (description,
  verbatim preview text, the three preview ids and files, the owner's choice).
  `voice_review.html` plays them all, plus the pilot lines.
- `voices_saved.csv`: the saved library voices (voice -> ElevenLabs voice id).
- Manifests per batch: `pilot_dink_manifest.json` (10 lines, 288 credits),
  `dink_batch_01_manifest.json` (60, 1,545), `dink_batch_02_manifest.json`
  (174, 5,336: with these Dink's Stonebrook dialogue is 244 of 245 lines),
  `cast_batch_01_manifest.json` (Martridge, Milder, Mother, King, Seth, Mog:
  115 lines, 4,193 credits; its rows were merged into the ledger from
  `ledger_rows_cast_batch_01.merged.csv`). Ledger on 7 Nov 2026: 359 voice
  lines, 11,362 credits, all `candidate`.
- A line that is only a stage direction (`<groan>` -> `[groans]`, s7-mil.talk.004;
  `<chortle>` -> `[chortles]`, s1-h2-o.talk.009)
  fails to generate: ElevenLabs needs words. Such lines stay unvoiced (the
  on-screen text still shows) unless a vocalisation is decided later.
- `<voice>/<line id>.mp3`: generated lines, one folder per voice, named by the
  Ink line id so the runtime can look a line up by id.
- Import into the game is the audio import pipeline's job
  (`Scripts/import_approved_audio.py`, `UDinkAudioSubsystem`); this folder only
  holds sources and provenance.
