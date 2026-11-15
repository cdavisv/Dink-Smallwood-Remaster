# The Mother's face, brows and bun; the hero's second face pass (14 November 2026)

Second PR of the faces round. Sheets 01 and 02 are captures of the running game (the Mother in her house on screen 1,
the hero by day on screen 438); top rows are master after #114, bottom rows this PR. Sheet 90 is a Blender review
render of the bun, added because the game's only view of it is in a patch of window sun.

## What changed

**Mother**
- **Bun**: the wound ribbons are gone. At any affordable segment count they were polygons with bright edges (the
  "paper rosette"). The bun is now the modelled core alone, shaped as a coil with two spiral ridges and painted with
  strands that run round it (`hair_styles.py` `bun_strips=0`, `bun_ribbons=False`, `bun_core_res`, `bun_coil`).
- **Brows**: in the game her brow was a thin dark line. That line was the brow *shadow* painted into the skin in the
  hair's dark colour, under fair cards that bleach in her window light. The shadow is nearly off (`skin.json`
  `brow_shadow` 0.06, `brow_paint` 0) and the brow cards are darker, denser and arched.
- **Skin**: relief back up half way (`micro` 1.3, `nrm_k` 0.19; #108 had flattened it to wax), more redness and broken
  capillaries, the wet lid margin at a quarter (`rim_wet`: it read as a wet streak under her eye).
- **Face**: under-eye bags, jowls, hollower cheeks, a deeper nasolabial fold, cheekbones, mouth corners lifted a little.
- **Hair**: darker tint and less scatter (`HAIR_LOOK`), against the bleaching in window sun.

**Hero** (the coordinator's review of #114: the brows gave him a scowl; push further to gawky)
- Brows lighter, thinner, the inner third raised (`hair_groom.py` `inner_up`).
- Ears at 19 degrees, a slack lower jaw, an overbite, an Adam's apple, a slightly longer and narrower face.
- `Physique_Scrawny`: narrower, more sloping shoulders (cap -21 mm, drop -17 mm, traps -10 mm).

**All three**: eye roughness capped at 0.045 and specular 0.9, for a wet highlight.

## What the game shows now

| Sheet | What I see |
|---|---|
| `01_mother_before_and_now.png` | Her brow is a brow with some body instead of a drawn line, and it is arched. The bun is a smooth rounded bun instead of a rosette of flat bands; in the sun patch it is still paler than the hair on her head. Her hair is a shade darker. **Her skin in direct window sun is still bleached and flat**: the relief and colour changes do not show there; in the shadowed front view the face has a little more form. The face-shape changes are barely visible in these four views. |
| `02_hero_before_and_now.png` | The receding chin and slack jaw show in the three-quarter view, the ears stand out, the shoulders at confidence 0 are narrower and slope. **The brows are thinner and their inner ends are a little higher, but in the game they are still dark.** No wet eye highlight is visible. |
| `90_blender_bun.png` | The bun in Blender: a wound coil in the hair's colour. |

## Still open

- Mother: skin in window sun (this is as much the exposure of her room as her skin); the face still reads as a
  smooth mask rather than a weathered woman in her forties; lashes; the bun's colour in sun.
- Hero: brows still too dark in the game; no eye highlight; the neck.
- Milder and the NPC families: not started.

## Not checked

LOD 1 to 3. A walk with the new builds. The Mother's and the hero's faces in any clip. The packaged game.
