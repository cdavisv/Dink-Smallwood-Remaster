# A101: confident Dink keeps the capture's stride (19 Nov 2026)

Branch `anim/gait-cadence`. After #186 the stride warp (which stops the planted foot skating) shortened every walking step,
so confident Dink walked with short steps on a knee folded 4 degrees deeper than the capture (row A101).

## What changed (presentation only)
- `FDinkGaitStyle::CadenceShare` (`animation_natural.json` `style` `cadence_share`): the share of the warp's correction
  taken by the cadence (the clip's full stride, played slower) instead of the step length. Hero timid 0 (his short, quick
  shuffle stays), confident 1, Mother 0.5, Milder 1. Interpolated by Dink's confidence like the other style values.
- The proxy splits the measured target T (body speed over the planted foot's speed at the uncorrected cadence) into a
  stride factor T^(1-share) and a cadence factor T^share; the game thread multiplies the gait cadence by the latter
  (walking only, < 320 cm/s, one frame late through the leg telemetry).
- Test `Dink.Animation.Legs.InEngine` logs the median drawn knee flexion with the layer off and on and asserts a confident
  walk's knee within 4 degrees of the clip's (at 120 cm/s the walk is half blended with the standing pose).

## Numbers
| | layer off (the capture) | #186 (master) | this branch |
|---|---|---|---|
| test, confident 170 cm/s: median knee / planted slide mean | 34.3 deg / 0.52 cm/frame | (not logged) | 35.6 deg / 0.13 |
| test, confident 120 cm/s | 31.1 / 0.52 | | 34.6 / 0.10 |
| test, timid 170 cm/s (unchanged by design) | 34.3 / 0.51 | | 40.3 / 0.13 |
| in game, hero confident walk: median knee / slide median | 33.5 / 0.35 | 37.8 / 0.00 | 35.7 / 0.00 |
| in game, hero timid walk | 32.4 / 0.31 | 41.6 / 0.00 | 41.7 / 0.00 |
| in game, Mother walk: knee / slide / pelvis bob | 31.2 / 0.59 / 5.6 cm | 37.6 / 0.00 / 3.8 | 36.3 / 0.00 / 3.7 |

## Sheet (`01_walk_side_legsoff_186_a101.jpg`, running game, side, confident unless marked)
Rows: the capture with the leg layer off; #186; this branch; this branch timid. Seen: this branch's confident walk takes the
capture's long strides with legs as straight as the first row's, where #186's steps were short and bent; the timid row keeps
the short shuffling step. A skate is not visible by eye in stills; the numbers carry it (slide stays 0.00 median).

## Tests and probe (master f4743990 + this branch)
- `Dink.Animation+Dink.Art.PlayerAction+Dink.Art.HumanoidPresentation+Dink.Movement`: 27/27.
- Full `Dink`: 351/351. Probe: all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md`.

## Still wrong / not checked
- Timid Dink's knee is still 7-9 degrees deeper than the capture (by design: short steps), and the Mother's 5 degrees.
- Not checked: packaged build; slopes and stairs.
