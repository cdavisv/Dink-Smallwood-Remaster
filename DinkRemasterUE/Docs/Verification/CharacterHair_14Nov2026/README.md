# Hair of the hero, the Mother and Milder in the running game (14 November 2026)

Owner: "improve hair"; later "make sure ... hair looks good". On master the hair cards were drawn with a default-lit,
alpha-tested material and an importer tint that bleached them: the Mother's hair read as straw shingles and her bun
as a faceted spiral (top row of sheet 01). Every picture here is a capture of the game
(`Scripts/PhotorealQA/run_capture.sh`; the Mother in her house on screen 1, the hero in the house and by day on
screen 438, Milder by the pond on screen 407).

## What changed

- **Material** (`Scripts/import_photoreal_art.py` `hair_material`): the hair cards use the engine's **Hair shading
  model** (two highlight lobes along the strand, light through the hair), masked, two-sided, dithered. Strand
  direction comes from the atlas's FLOW map, root-to-tip, strand-to-strand and depth shading from its MSK map. The
  model's back-light pin is not reachable from Python, so `UDinkCharacterArtLibrary::ConnectMaterialCustomData`
  (DinkImport plugin, editor only) connects it. `DINK_HAIR_MODEL=lit` builds the previous material for comparison.
- **Calibration** (`HAIR_LOOK` in the importer, set after two rounds of captures): hero tint (2.4, 1.5, 1.1) and
  scatter 0.8, so he is red-brown by day instead of near black; Mother tint (0.8, 0.76, 0.7), no root-to-tip shading
  (it drew every painted strand of her pulled-back hair as a separate shingle), scatter 0.5; Milder tint
  (0.85, 0.8, 0.75), flatter root and depth shading, lower scatter and specular. The old tint (1.4, 1.2, 1.05) is gone.
- **Hero groom** (`Characters/Tools/hair_styles.py`, `hair_groom.py`, `hairlib.py`): a feathered fringe; the opaque
  cap stops short of the tips, so the fringe and the outline are free strands on cards.
- **Mother's cards**: over her painted cap the cards are thin and wisp tiles, narrower and tapered. The dense tiles
  read as overlapping planks with square ends. Her bun's coils have 28 segments instead of 18 and a rounder core.
- **Mother's and Milder's garments** (they are rebuilt with the hair): `garlib.clear_of_skin` ignores the cut edge of
  skin that has been removed under clothes (measured against it, the Mother's shoulder yoke stood up as two flaps
  and her neckline gaped in the first rebuild of this branch); the bodice's openings are not cut again after the
  decimation (`PR_BOD_RECUT`, default none); Milder's tabard gets the unfolded shoulder charts of the hero's jerkin.
- Rebuilt: the three characters' FBX, hair atlases, `.blend` sources; Mother's and Milder's Outfit and Gear sets.
  Imported: the three meshes, their textures and materials. Skeleton and bone names unchanged; the hero keeps both
  shape keys on all four LODs.

## What the game shows now

| Sheet | Shows | What I see |
|---|---|---|
| `01_mother_master_and_now.png` | Top: master. Bottom: this PR (side, back, front quarter; the capture camera's angle convention changed between the two runs, so the views do not match exactly) | The shingles are gone: her hair reads as fair hair drawn back, with strands and a soft hairline. The bun is a rounder coil but still reads as flat wound bands, paler than the rest; close up it is not convincing. In window light the top of her head still bleaches. |
| `02_hero.png` | House (orange window light), by day from three sides, crown from above, play camera | A cropped head of hair with a feathered edge, red-brown by day and at the play camera. Close up a stipple halo surrounds the silhouette (the dithered fly-away cards). |
| `03_milder.png` | By day, front quarter, back, other front quarter | A rough short crop that reads as hair from the back. From the front it is patchy: pale areas between dark dashes (the lifted cards shadow the cap in full sun). Not at the bar close up. |
| `04_first_look_and_calibrated.png` | Top: the first import of the new material, before calibration. Bottom: now | Hero from near black to brown; Milder's dashes reduced, not gone; the bun from an 18-sided spiral to a coil. |

## Still open

- Mother: the bun (above); two or three loose wisps cross her temple and cheek as thin dark lines in close-up.
- Milder: patchy from the front in full sun.
- Hero: the stipple halo close up; in the orange window light of his house the hair goes bright orange.
- Brows and lashes share the hair material; Milder's brows are heavy.
- Skin (orange-peel relief on the Mother) and the builds are the next PR, not this one.

## Not checked

- Master "before" captures of the hero and Milder (only the Mother's exist). Hair in motion beyond the walk shots.
  Night, rain and interior scenes other than the two houses. LOD 1 to 3 of the hair. The packaged game.

## Tests

See the PR text (they were run on the tree of this PR; the in-engine suite ran in the private project copy).
