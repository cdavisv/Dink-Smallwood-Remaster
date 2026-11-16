# The Mother's age and brows, brow colour, Milder's forearms, gloves and mail (14 and 15 November 2026)

Sheets 01 and 02 are captures of the running game (the Mother in her house on screen 1, the hero on screen 438, Milder
by the pond on screen 407): top rows master after #121, bottom rows this change. Sheet 90 is a Blender review render,
because the capture of this round did not frame Milder's hands and the back of his mail skirt.

## What changed

**Mother** (the order was: skin with age; the bleaching in her window is the room's exposure, measured in #121's round)
- Age lines that survive the play of light in her room: `skin.json` `age` 1.3 with the new `line_k` 1.8 (how dark the
  lines and the under-eye are in the base colour; at 1 they vanished), more redness and broken capillaries, more sun.
- The brow lines were evenly spaced straight lines, a ladder: `fore_period`, `fore_warp`, `fore_k` (new keys in
  `dink_05b_skin.py`; the defaults leave the hero and Milder as they were) make them fewer, bent and fainter.
- Lashes darker (`lash_rgb`), skin tint a step darker (`SKIN_LOOK`).
- Brows (15 Nov): they met low over the nose in one dark V and made her stern. The inner ends now start further from the
  middle and are raised (`hair_styles.py` Mother `brow`: new `x0`, `inner_up`; thinner, a little more arch). Only the
  brow cards and the brow rows of her hair atlas change: the hair-motion check of the physics stream
  (`Scripts/PhysicsQA/hair_check.py` of `phys/hair-cloth`) counts the same hair, moving and static vertices as on master.

**Brows of the hero and Milder**: the brow band of the hair material has no scatter and no back-light (#114), so a brow
of the hair's own colour read much darker than the hair above it. New scalar `BrowGain` on the band's base colour
(hero 1.6, Milder 1.5, Mother 1).

**Milder**
- Forearms: `physique.py` `Burly` `lowerarm` (+6 mm at the belly of the forearm). They were a boy's under his shoulders.
- Gloves: brown leather instead of pale grey (`skin.json` `glove`), which read as rubber.
- Mail skirt: the pale torn patches on the seat were bake misses. The mail bakes from a subdivided copy of itself, and
  that copy pulls up to a centimetre away from the coarse folds: at 14 mm the rays missed it in patches. Rays are now
  30 mm for that sheet (`char_05_bake.py`). Shorter rays, tried first, made more holes.

**Importer**: the character block became `import_character(name, source folder, content folder)`; nothing else moves.

## What the game shows

| Sheet | What I see |
|---|---|
| `01_mother_before_and_now.png` | Top row master, bottom row this change; front, three-quarter, profile, play camera. Front: the brows no longer join in a V over the nose, there is skin between them and the look is tired rather than angry; crow's feet, a line under each eye and a hint of the fold beside the nose show; the skin is a shade darker and less waxy. Three-quarter: fine lines at the eye in the sun. Profile and play camera: no visible change. **It is a modest step.** Her brow is still a thin dark line rather than hairs, she is still bleached and flat where the window sun hits her, the hairline is a hard edge and the hair a smooth shell, and her lashes are a smudge. |
| `02_brows_and_forearms_before_and_now.png` | Hero: brows a mid brown close to his hair instead of near black. Milder: brows lighter, still heavy bars; forearms fuller between elbow guard and gauntlet. |
| `90_blender_milder_before_and_now.png` | Blender, not the game: brown gloves, the seat of the mail whole. |
| `03_milder_hands_and_skirt_in_game.jpg` (16 Nov) | The game, by the pond of screen 407 (re-import of these sources in the review copy). Front: brown leather hands under steel gauntlets, forearms as thick as the gauntlet cuffs, the mail skirt whole and reading as mail. Back: the seat of the skirt shows no pale torn patch in the strip that is visible; **a mossy rock stands between the camera and him and hides most of the skirt and his legs**, so the back is proven only for its upper third. Seen and not fixed here: the edge of each knee cop is jagged, the gauntlets turn bright green from behind (polished metal mirroring the grass: too little roughness), a pale patch sits on his right shoulder beside the pauldron, the fingers are stiff and close together. |

## Checked

- `Dink.Art+Dink.Animation+Dink.Movement`: 79/79 passed on a re-import of these sources (review copy, C++ of 14 Nov,
  `10d92f1b`), and 82/82 passed with the re-imported packages on a build of master `f3771058` (15 Nov), both on
  16 Nov before the machine restarted. The packages in this pull request are the ones seen in the sheets; the tested
  ones are a second import of the same sources. Rebased onto master `3a7b4451` on 16 Nov: only the `AGENTS.md` section
  moved, no package or source of this change is touched by master.
- Unit tests, `verify_sources.py`, whole-tree scrub, LFS audit: see the pull request.
- Hair contract of the physics stream: only the Mother's brow cards changed (the static brow band); `hair_check.py`
  gave the same hair, moving and static vertex counts as master.

## Not checked, still wrong

- Milder's mail skirt from behind is framed only in part (sheet 03: a rock hides it); the lower back of the skirt is
  seen in Blender only.
- The probe was not run for this change (no C++, gameplay data or world content).
- Mother: bleaching in window sun (room exposure, not hers), brows that read as a drawn line, a hard hairline, lashes,
  a face that is still smoother than a woman of her years. Below alpha in a close-up; at the play camera she reads as a
  woman in a red dress with her hair up.
- Hero: under the hanging lamps of the lamp-lit interiors (screens 2, 102, 290) his hair goes pale pink-grey; not
  touched here.
- Milder: bare shoulder between collar and pauldron, bare upper arms, flat wide face in full sun.
