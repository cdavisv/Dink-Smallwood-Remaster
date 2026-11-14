# Faces, skin and builds of the Mother and Milder (14 November 2026)

The previous review called the three photoreal characters' faces "mannequin-like", the weakest art in the game, and
the owner asked for realistic builds. This folder records what the running game showed, what changed and what it
shows now. Sheets 01 to 03 are captures of the game (`Scripts/PhotorealQA/run_capture.sh`; the Mother in her house
on screen 1, Milder by the pond on screen 407); sheets 90 and 91 are Blender review renders, added only because the
build is easier to compare on a neutral ground.

## What the game showed

- **Skin.** The pore and crease relief that looks right in the Blender renders read as orange peel on the Mother's
  face and as goose flesh on her neck under the game's sun and window light (top row of sheet 01). That, more than
  the shape of the face, is what made the heads look like painted mannequins.
- **Builds.** All three stand on the same template skeleton with much the same frame. Milder, the village braggart
  who became a knight, had the arms and shoulders of the pig farmer he bullies (top row of sheet 02).
- **Milder's mail skirt** had a pale torn rectangle on the seat: its bake rays missed the detailed sheet in two bands.

## What changed

- `Characters/Tools/physique.py`: two builds beside the hero's, as displacement fields in rest space applied to every
  layer and every LOD alike: **Burly** (broad shoulders, deep chest, thick neck, arms and legs, and thick through the
  waist) and **Matron** (a little heavy at the waist, belly and seat, fuller upper arms; shoulders and neck as
  modelled, because the bodice's seam and neckline sit on them).
- `Characters/Tools/char_07_build.py` (new) bakes a build into the assembled character after `dink_06_assemble`;
  `run_char.sh` runs it when `cfg/tex.env` has `BUILD="<name> <strength>"`. Milder: `Burly 1.0`. Mother: `Matron 1.0`.
  Report: `<Name>/build_report.json`. The hero keeps his two shape keys.
- Skin: `cfg/skin.json` micro relief and normal gain down (Mother 1.6 -> 1.0 and 0.24 -> 0.15, age 1.2 -> 1.0;
  Milder 1.6 -> 1.05 and 0.24 -> 0.17, more stubble); the importer sets `NormalStrength 0.6` on every skin instance.
- `Characters/Tools/char_05_bake.py`: the mail skirt bakes from a subdivided copy of itself (`SELF_HI`).
- `Characters/Tools/hair_styles.py`: the Mother has 3 loose wisps at the temples instead of 8 (in the game a loose
  strand across the cheek is a thin dark line on the face).
- Hair material (answers the review of the hair PR): coverage below `AlphaCut` 0.3 is no hair (a card of sparse strands
  averaged to a few per cent in the small mips and the dither drew it as a ghost sheet over Milder's head and a stipple
  halo round the hero's); the opaque cap under the cards is shaded darker (`CapShade` 0.6; the pale cap showed between
  Milder's cards as scalp); only the cap casts shadows (`CardShadow` 0). The Mother keeps cap shade 1 and card shadows.
- Milder's crown: 1.35 times the cards, 0.62 of the width, lying closer to the head.
- The Mother's skin tint (0.78, 0.72, 0.69) (`SKIN_LOOK`); brow hairs painted into the skin albedo under the brow cards (`brow_paint`).
- **Hero build**: `KEY_STRENGTH['Brawny'] = 0.55` (owner: "a little stronger, not He-Man"). The full field put 9 cm on the
  upper arm and 12 cm on the chest; the key now carries 55% of it. `Physique_Scrawny` is unchanged. Both keys on all four LODs.
- Rebuilt: the hero's FBX (shape keys), skin and hair textures; Mother's and Milder's FBX, skin, hair and gear textures, `.blend` sources. Imported: all three meshes with their textures and materials.

## What the game shows now

Top rows: the state of the hair PR (#104). Bottom rows: this PR.

| Sheet | Shows | What I see |
|---|---|---|
| `01_mother_before_and_now.png` | Front quarter in window sun, profile, back | The orange peel and the pitted neck are gone and the profile reads as a person's skin with freckles. In direct window sun (first tile) her face is still pale and flat. **The bun is unchanged: it still reads as a paper rosette.** |
| `02_milder_before_and_now.png` | Front, back, head from two sides | Burly: broad shoulders, thick upper arms, deep chest, heavy waist. The ghost sheet over his head is gone. His crop is dense short hair with fine strands instead of dark dashes on a pale scalp. The torn rectangle on his mail is down to a ragged line. |
| `03_hero_before_and_now.png` | Head from two sides (before: crown and play camera); bottom right: the body at `dink.HeroConfidence 0` and `1` | The stipple halo round his head is gone. At confidence 0 he is a narrow, lanky lad; at 1 his shoulders, chest and arms are fuller without bulk. His brows are still a thin drawn line. |
| `90_...`, `91_...` | Blender review renders of the two NPC builds before and after | Supplementary, on a neutral ground. |

## Still open (seen, not fixed)

- **The Mother's bun**: needs to be modelled as wound hair volume; nothing in this PR changes it.
- **Brows**: the painted brow hairs did not change what the game shows: the hero's and the Mother's are a thin line, Milder's heavy.
- **Faces**: the bone structure of all three faces is as on master. This PR changes skin shading and bodies, not faces. The hero's face was not looked at close up in this round (my two face shots were aimed at the back of the heads).
- The Mother's face in direct window sun; a wet streak below her eye in profile; two fine wisps on her temple.
- Milder: smooth grey gloves that read as rubber; the ragged line on the mail; bare shoulder between collar and pauldron.

## Not checked

- LOD 1 to 3 of the builds and of the hair changes. Walks with the new builds. The hero between confidence 0 and 1, and his build keys during attacks. The packaged game.
