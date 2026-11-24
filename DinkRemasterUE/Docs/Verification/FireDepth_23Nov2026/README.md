# Fire of the burning house: each fire several cards deep (439 and screen 1, vision 1), 23 November 2026

**What changed.** Each fire of the burning house was ONE camera-facing card (rows `fire_fx` = picture 427, the placed
`fire_burst_fx` = 161 and `explosion_fx` = 70 of the room): one picture of a flame, flat from every side, the same
picture on every fire at the same moment. Placed-effect rows take a new key, presentation only:

- `"effect_layers": [[x, y, z, scale, phase_s, mirror], ...]` (`UDinkArtFamilySubsystem::DressPlacedEffect`): further
  cards of the same flipbook attached to the placement's card (x along the card, y towards the viewer, z up, in cm; a
  placement's size factor spreads them too), each with its own size, its own place in the loop (a dynamic material
  instance with a negative `StartTime`) and optionally mirrored. They are children of the placement's card, so they
  face the camera with it and follow its screen and vision rules.
- `families.json`: the three rows carry three layers each: one larger behind, one smaller in front, one far behind.

This is the fire half of the draft "fires in depth, burn marks as decals" (#214), cut out on the coordinator's order
because it is at the bar while #214's roof burn marks were not. **Not in this change:** the burn patches 155 to 157
(they stay master's smouldering cards here; their decals are #214), the hole in the thatch (the burning cottage of
the gore stream), char under the roof fires, shadows from the fire lights.

## Seen in the running game

Frames of the game on this change alone: copy `Saved/FableD`, master `c0e29cac5` + the fireball data of #210 (no code) + this
commit, nothing else in the source tree (capture section `sec_firealone`, 8 frames, `Saved/PhotorealPass/fx5/F_*.png`).

| sheet | what it shows | what I see |
|---|---|---|
| `1997_screen_439_vision_1.png`, `1997_screen_1_vision_1.png` | the 1997 screens | four fires on the cottage roof; in the room fires along the walls, on the table and by the bed |
| `01_before_master.jpg` | master, 17 Nov | each fire one card |
| `02_game_23nov_fires_in_depth.jpg` | top: the 1997 screen 439, then the game at the play camera, from the south and from the south-east; bottom: the 1997 room, the game's room at the play camera, the roof fires close, the cottage from the south-west | **The roof fires read as a burning roof from every side**: along the ridge several sheets of flame stand one behind the other, larger behind and smaller in front, no two at the same place in their loop, with smoke rolling off them; from the south-east and the south-west they keep their body instead of turning into one flat picture. Close up (roof close) the nearer and the farther sheets part as the camera moves. In the room the fires along the walls are deep banks of flame as well (Dink stands in one of them: the capture put him there). At the play camera of 439 the fires stand at the upper edge of the frame: the game's camera, not this change. The small dark patches on the roof are master's smouldering cards of 155 to 157, untouched here |

## How it was proven

- On master `fd676f34d` + this commit, nothing else (copy `Saved/FableD`, its source tree set to the branch, intermediates
  deleted): clean build, 0 warnings, 162 s; the build log shows `DinkArtFamilySubsystem.cpp` compiling.
- `Dink.Art+Dink.Animation+Dink.Gameplay.Probe`: 124/124 passed in 646 s (run `fx5_fire2`). The same three filters on master
  `c0e29cac5` + #210 + this commit, the tree the frames were taken on: 124/124 in 660 s (run `fx5_fire`). Kernel: no fault.
- Probe: the twenty chapter md5s of the run equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master.
- `Dink.Art.Family.PlacedEffectRow` reads two layers of a test row (offset, size, phase, mirror) and drops an entry
  with fewer than five numbers.

## Not checked

- The layers at other frame rates than the capture's; many fires on one screen at once beyond the nine of screen 1.
- The fire lights still cast no shadows, and nothing is charred under the roof fires.
