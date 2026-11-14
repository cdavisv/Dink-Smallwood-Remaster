# Blood extent: never less than the 1997 pictures (14 Nov 2026)

Review of PRs #111 and #112: the knight and the people were right in realism and size, but their blood covered less
ground than the 1997 pictures (owner's rule: keep all the original gore). This change gives the knight, the girl, both
merchants and the peasant a pool and thrown drops that cover at least the red of their picture, and soaks their clothes
in patches. Visual only; no C++, no row changed.

## How the extent is taken from the picture

- `gore_sheets.py` `sprite_red()` reads the clearly red pixels of the picture (`ImportData/sprites/<seq>_<frame>.png`).
  Those PNGs are stretched to power-of-two canvases, so the scale comes from the card of the placement
  (`placements.json` `card.width_m` x `card.height_m`: tables `FOOT` and `FOOT_H` in `build_gore.py`), not from pixel
  counts. The picture looks down at an angle; its height is laid on the ground 1.3 times deeper.
- `blood_sheet(stamp=...)` lays that shape on the ground as pool; `person_pool(fit_m=..., sprite=...)` adds the pool
  that hugs the body and 150 thrown drops, cast-off lines and mist up to 0.24 m (more for cast-off lines) beyond it.
- Clothes: `bloody(drench=0.17, spatter=0.63)` soaks them in patches; the knight gets more runs down the plates.
- `Scripts/tests/test_corpse_kit.py` now requires, from each asset's manifest, blood area on the ground >= the
  picture's red area, and blood width <= 1.6 x the card width.

| Asset | blood on the ground | red of the picture | blood width incl. drops | card width |
|---|---:|---:|---:|---:|
| Knight (275) | 2.01 m2 | 0.40 m2 | 2.40 m | 2.02 m |
| Girl (335) | 1.37 m2 | 0.45 m2 | 1.94 m | 1.45 m |
| Merchant, blue (345) | 1.97 m2 | 0.63 m2 | 2.33 m | 1.85 m |
| Merchant, green (385) | 1.76 m2 | 0.47 m2 | 2.20 m | 1.85 m |
| Peasant (415) | 2.44 m2 | 0.66 m2 | 2.88 m | 2.85 m |

The blood is three to five times the red area of the picture because the pool also runs under and round a body of
real proportions, and its width passes the card by the thrown drops. The bodies themselves are unchanged in size.

## Seen in the game

`blood_extent_before_after.jpg`: the five placements at the play camera and close, master on the left of each pair.

- Each now lies in a pool wider and longer than the body, in the shape of its picture's red, with drops and smears
  round it; clothes and steel carry dark soaked patches and still show their colours.
- Short of the pictures, plainly: the 1997 red is bright and nearly covers the bodies; here the blood is the dark wet
  look of PR #110 and the bodies are soaked in patches, not all over.

## Not in this change

- **The woman in red (245):** her rebuild for this change baked with missing skin textures (LFS pointers after a
  rebase; magenta arms in the capture). Rebuilt with the textures; waiting for its turn at the editor to be captured
  again. Master keeps her small pool until then.
- The soldier, Dink and the mother: unchanged (not bound).
- The knight's doll-like proportions (ball head, short limbs): the source harness; not changed.

## Checks

- `Scripts/test.sh Dink.Art`: 63/63 passed in the private copy with these assets imported (it also held the woman in
  red's faulty rebuild, which is not in this change).
- `python3 -m unittest Scripts/tests/test_corpse_kit.py`: OK. Full suite: see the PR text.
- The kit's master materials are not re-committed.

## Not checked

Night, a packaged build, the live play camera. The private copy's generated world is of 12 Nov.
