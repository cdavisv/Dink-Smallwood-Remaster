# Blood rework, proven on the dragon remains (14 Nov 2026)

Review of PR #103: the blood read as poster paint (uniformly vivid, flat, a bright rim). This change reworks the
blood every remains of the corpse kit uses (`SourceAssets/Art/PhotorealPass/Corpses/tools/gore_sheets.py`
`blood_sheet`, and the flesh and gut materials in `tools/build_gore.py`) and rebuilds the dragon with it. Visual only;
no C++.

## What changed in the look

- Pool: the middle nearly black-red (17, 1, 1 sRGB in the map; the game's exposure on these screens lifts it to a dark
  red), smooth so it mirrors the sky, no bright line at the rim: the edge dries brown-red and rougher.
- Thrown drops, cast-off lines and mist: thin and drying, brown-red, half rough.
- Round the pool a ragged fringe of earth the blood has soaked into: damp, darker than the dry ground, reddish next
  to the pool. It is part of the alpha-tested card (opaque dark earth), not a blend with the ground.
- Raw muscle and gut are darker (they were candy pink in the game).

## Seen in the game

`blood_before_after_dragon216.jpg`: screen 158 (dry earth, sun), the same two cameras as PR #103's sheets
(`dink.CalCam 0 650 520 0 0 40 60` and `40 300 190 0 0 15 50`), left the look on master, right this change.

- Play camera: a dark wet pool that reads as blood at first glance; the fringe makes it sit in the ground instead of
  on it.
- Close: dark red with a sheen that mirrors the sky and the carcass; the fringe is a soft brown band; drops brown-red.
  In direct sun the shallow parts of the pool are still a clear red, not black.
- The muscle is darker and no longer pink; it is still lumpy.

## The picture-212 row is taken out (screens 100 and 238)

`families.json` loses the `dragon_corpse` row; the row for picture 216 (screen 158) stays. Reasons:

- S100_P34: most of the remains stand inside a greybox wall block; worse than the card (PR #103's lit capture).
- S238_P12: the pool card is under the grass carpet.

A row binds by picture, not by screen, so one cannot go without the other. The static stream's unmerged branch adds
a `screens` field to rows; when it is on master the row comes back as `"screens": [238]`, once the pool shows on grass.

| `art_coverage.py` | before | after |
|---|---:|---:|
| final | 4,914 | 4,912 |
| placeholder | 1,541 | 1,543 |
| cut | 152 | 152 |

## Also in the tool, not used by any asset in this change

`build_gore.py` gains `worn_steel()`, blood runs (`bloody(runs=...)`), the table `FOOT` of sprite footprints (card
widths of `placements.json`), `person_pool(fit_m=...)` and `person2()` (people posed from the rigs, opened, fitted to
the footprint). They belong to the knight and the people, which follow in their own PRs.

## Checks

- `python3 -m unittest Scripts/tests/test_corpse_kit.py`: OK. Full unit suite and `Dink.Art`: see the PR text.
- The kit's master materials are not re-committed: master's copies already point at the dragon's textures.

## Not checked

- The pool on grass or indoors (no bound placement is on either after this change); night lighting.
- The capture was made with the private copy's binaries of master `80ff12f1` (a rebuild on current master failed on a
  start race and is queued again).
- A packaged build; the live play camera.
