# Run H (16 Nov 2026, 11:09-11:14, inside Dink's house): regenerated effects cued by play, found in the recording (Scripts/AudioQA/cue_proof.py)

| asset | cue | log time (s after device open) | onset in recording (s) | match | RMS dBFS | floor (1 s before) dBFS | peak dBFS | heard |
|---|---|---|---|---|---|---|---|---|
| SFX_44_bow1 | game, sprite 0, pitch 1.000 | 112.4 | 113.73 | 0.652 | -28.4 | -33.8 | -9.9 | yes |
| SFX_44_bow1 | game, sprite 0, pitch 1.000 | 116.5 | 117.83 | 0.676 | -28.5 | -40.4 | -7.6 | yes |
| SFX_48_axe | game, sprite 0, pitch 0.590 | 123.2 | 124.77 | 0.732 | -27.1 | -17.4 | -5.8 | NO |
| SFX_48_axe | game, sprite 0, pitch 0.590 | 126.8 | 128.22 | 0.773 | -27.5 | -17.1 | -5.3 | NO |

Axe: the strike lands on the tail of the throw's own swing (sound 8 at 8000 Hz, item-axe.c:17, played 0.5 s before), so the 'floor' of the second before is louder than the strike; RMS of the 100 ms before the onset -10.9 / -13.1 dBFS against -22.6 / -23.4 over 300 ms from it. The axe is identified by waveform match (0.73, 0.77 against the take resampled to pitch 0.59), not by a level step. Bow: -59.7 / -53.7 dBFS in the 100 ms before each release, -27.9 dBFS over 300 ms from it. Punch: five fist attacks (at the mother from her east side, at the round table from the north) landed on nothing, so no sound 9 was cued.
