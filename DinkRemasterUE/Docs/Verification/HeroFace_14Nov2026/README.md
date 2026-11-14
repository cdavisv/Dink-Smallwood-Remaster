# The hero's face: front close-ups, brows, a gawkier lad (14 November 2026)

First PR of the faces round. The earlier face shots of this stream were aimed at the backs of the heads, so the round
started with front close-ups of all three characters in the running game (17 shots, `Scripts/PhotorealQA/run_capture.sh`:
the Mother in her house, the hero in his house and by day on screen 438, Milder by the pond on screen 407). Top rows
of the sheets: master after #108. Bottom rows: this PR.

## Verdict on master, against "a photo of a person"

- **Hero**: the best of the three; a believable soft-featured lad with freckles. Faults: brows thinned to a ragged line
  with an orange glint at the inner end, lashes only at the inner corner of the eye, too regular and handsome for a
  gawky pig farmer, a thin neck at confidence 0.
- **Mother**: waxy and flat; her brow is a single drawn line; no lashes; she bleaches in window sun.
- **Milder**: the weakest: a wide flat face, heavy brows, lash smudges under the eyes, an odd mouth.

## What changed

- **Brows and lashes** (all three characters, `Scripts/import_photoreal_art.py` `hair_material`): the bottom quarter of the
  hair atlas is the brow and lash band. There the coverage cut is a fifth of the scalp hair's (the cut of #108 removed
  the single fine hairs: brows became a line and lashes vanished), and specular, scatter and back-light are damped
  (`BrowSpecular` 0.15; the scalp hair's lobes lit the inner end of a brow orange in the sun).
- **Hero's brows**: a wider, denser strand groom (`hair_styles.py` `brow=dict(th=.0056, n=800)`).
- **Hero's face** (`Dink/cfg/head.json`): ears set further out (14 degrees), and seven shaping operations: a weaker,
  receding chin, narrower jaw angles, fuller cheeks, a rounder nose tip, a longer upper lip, a lower lip that hangs a
  little, heavier upper lids. The largest displacement is 3 mm.
- **Hero's neck**: `physique.NECK['Scrawny']` from (-6, -4) mm to (-1, 0) mm of radius.
- Rebuilt and imported: the hero's mesh (both shape keys on all four LODs), skin and hair textures; the hair materials
  of all three characters. No bone, slot or key name changes.

## What the game shows now

| Sheet | Shows | What I see |
|---|---|---|
| `01_hero_before_and_now.png` | Day front, day three-quarter, house front, bust at `dink.HeroConfidence 0` | His brows are brows: dense, with single hairs at the edges, and the orange glint on them is gone. Lashes line the upper lid. The mouth hangs slightly open and the chin is softer: he reads younger and a little vacant. The change of face shape is small; he is still closer to handsome than to gawky. The neck looks much the same in the bust shot. |
| `02_hero_side_and_play_camera.png` | Day profile, house three-quarter and profile, play camera | Ears stand out more in profile. At the play camera nothing reads differently. |
| `03_mother_milder_brows_before_and_now.png` | The Mother and Milder, front and three-quarter | The Mother's brow is darker and a little fuller, but still close to a line. Milder's brows are fuller (they were already heavy). Their faces are otherwise unchanged: their own PRs come next. |

## Still open

- Hero: a small orange glint remains on the fringe above the brows (scalp hair, not the brows); eyes have no wet
  highlight; skin in the orange window light of his house is saturated; the face needs a stronger push to gawky; the
  neck at confidence 0.
- Mother and Milder: everything in the verdict above except the brows' density.

## Not checked

- LOD 1 to 3 of the face and brows. The face in motion (talk, hurt, death clips). The packaged game.
