# Snow and ice: exposure compensation (14 November 2026)

The ground review failed `snow` and `ice`: the textures are near white (albedo 0.86 to 0.9) but the automatic exposure meters a screen full of white ground down to middle grey, so snow read as grey rippled sand (120, 153) and ice as trampled mud (13, 109).

Change (visual only, no gameplay data): `UDinkEnvironmentSubsystem` owns a second unbound post-process component, `EnvSnowExposure` (priority 15: above the authored exposure volumes, below the interior set). On an outdoor screen whose share of snow and ice tiles (`ground_classes.json`) reaches `full_share` it adds `bias_ev` to the automatic exposure, proportionally less from `min_share` up, eased at 0.8 EV per second when the hero changes screen. Values in `environment.json` `snow_exposure` (0.8 EV, 0.6, 0.25); `dink.SnowExposure` multiplies it (0 = off). 31 outdoor screens qualify.

Captures from the running game at the play camera; upper row `dink.SnowExposure 0` (as on master), lower row 1:

- `snow_120_153_ice_13_109.jpg`: snow screens 120 and 153, ice screens 13 and 109. Upper: grey. Lower: no longer grey: bright, but a flat streaked plane (see the verdict below); the ice screens are pale trodden ground. The sky is a little lighter, not washed out.
- `snow_80_149_16_meadow_10.jpg`: 80 and 149 (already white in sun, a little brighter now, no clipping on the lit snow), 16 (42% snow: a partial compensation, the cobbles keep their tone) and the meadow 10 (no snow: identical).

**Verdicts stay failed.** The compensation removes the grey, and that is all it does. In review the lower row still reads as a pale cracked salt flat or dried mud: a dead-flat plane with streaky crack lines, no drifts, no softness, no blue in the shadows, no sparkle; the ice screens are not ice at all. `snow` and `ice` remain `fail` in `ground_review.json` with that reason, and no screen ground turns final through this change. Follow-up: real snow and ice materials (soft wind-drift relief, granular sparkle, blue shadows; a smooth translucent ice sheet with depth cracks, frost and sky reflection), judged again on 120, 153, 13 and 109.

Not checked: the transition while walking from a meadow screen onto snow (the easing is in the code, no capture of it); snow under the grey-walled castle interiors (indoor screens are excluded); night lighting.
