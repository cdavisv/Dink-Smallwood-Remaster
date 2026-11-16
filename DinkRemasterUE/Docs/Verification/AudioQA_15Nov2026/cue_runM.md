# Run M (16 Nov 2026, 15:16-15:18): fist hits in play

The probe's own fist target: the AlkTree S474_P01 (`s1-ntree`) on SCR_474, Dink west of its hardbox facing east (`DinkProbeTests.cpp:3917-3921`). Dink was given 500 life first: in runs D, E and G the screen's pillbugs killed him (10 life), and `dinfo.die` and the death menu held him, which first looked like `dink.Goto` freezing him. Eight attacks with fists; every one cued `SFX_09_punch` at pitch 1.0 about 170 ms after the swing (the attack's hit frame, `DinkGameplay.cpp:910`), and five nuts fell (`s1-nut`, the tree's hit script).

Each cue found in the recording by cross-correlation with `09_punch_e`: the first within +-2 s, the others within +-0.4 s of the same log-to-recording offset (1.54 s). The punch lands on the tail of the swing (sound 8 at 8000 Hz, `item-fst.c`), so the 0.3 s before holds the swing, not silence.

| punch | log time (s) | onset (s) | match | RMS 0.45 s dBFS | 0.3 s before dBFS | peak dBFS |
|---|---|---|---|---|---|---|
| 1 | 113.46 | 115.00 | 0.440 | -14.5 | -20.3 | -10.1 |
| 2 | 115.90 | 117.18 | 0.458 | -14.5 | -20.0 | -9.7 |
| 3 | 118.33 | 119.64 | 0.407 | -13.5 | -18.2 | -4.8 |
| 4 | 120.76 | 122.09 | 0.458 | -14.5 | -20.1 | -9.7 |
| 5 | 130.04 | 131.46 | 0.458 | -14.5 | -20.2 | -10.3 |
| 6 | 132.45 | 133.91 | 0.427 | -14.6 | -20.7 | -10.1 |
| 7 | 141.74 | 143.27 | 0.458 | -14.5 | -20.2 | -10.0 |
| 8 | 144.17 | 145.73 | 0.457 | -14.5 | -20.0 | -9.1 |

distinct onsets: 8 of 8; offset log->recording 1.54 s

Listen: `clips/runM_fist_hits_in_play.ogg` (11.5 s of the recording from just before the first punch, downmixed to stereo: punches 1 to 4).
