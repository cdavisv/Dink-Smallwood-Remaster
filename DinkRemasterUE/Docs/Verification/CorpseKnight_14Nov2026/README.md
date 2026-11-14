# The dead knight as worn steel, at the picture's footprint (14 Nov 2026)

Review of PR #103 rejected the first knight: one glossy red all over, a plastic toy, and too large. This is the
rebuild (`SourceAssets/Art/PhotorealPass/Corpses/Corpse_Knight`, recipe `knight()` in `tools/build_gore.py`),
bound as `corpse_knight` (picture 275, S157_P04). Visual only; no C++. Stacked on the blood rework (PR #110).

## What it is

- The plate harness of `Unclaimed/npc_knight_blue` with its **silver** base colour, worn by rule (`worn_steel()`):
  grime and rust-brown in patches, bright scratches, dull uneven roughness, dents as a bump.
- Blood where it would be (`bloody(runs=...)`): welling round the halberd wound in the chest, run down the plates
  from it in streaks, soaked where the harness lies in the pool, a few thrown spots. No overall tint.
- The snapped shaft standing in the chest and the halberd head in the blood, as picture 275 has them.
- The pool card with the blood of PR #110.

## Size, measured

`placements.json` gives the card of S157_P04 as 81 x 55 px = **2.02 m** wide. The build prints
`FIT knight extent 1.72 m -> scale 1.000` (the harness is 1.72 m long, so it is not scaled) and
`FOOTPRINT pool incl. drops 1.88 m, sprite card 2.02 m`. The mesh's bounding box is 2.4 m because the card keeps a
transparent margin. The first version was 3.2 m with its pool.

## Seen in the game

`knight_before_after.jpg`: screen 157, play camera and close; the sprite card before, the rejected first version, and
this one.

- It reads as a dead man in steel lying in a dark pool, the shaft in his chest, blood down the breastplate.
- Short of the picture: the 1997 pool spreads wider on the head side than the footprint rule lets this one; the
  steel is lighter and cleaner than the grey-brown of the picture, and the wear is fine detail that mostly
  disappears at the play camera. The plates are the source's swept shapes: no straps, rivets or mail, nobody inside.

| `art_coverage.py` | before (PR #110) | after |
|---|---:|---:|
| final | 4,912 | 4,913 |
| placeholder | 1,543 | 1,542 |

## Checks and what was not checked

- `python3 -m unittest Scripts/tests/test_corpse_kit.py`: OK. Full suite and `Dink.Art`: see the PR text.
- The kit's master materials are not re-committed.
- The capture used the private copy's binaries of master `80ff12f1`. Not looked at: night, a packaged build, the live
  play camera.
