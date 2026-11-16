# Dragon as a creature class (16 Nov 2026)

Fable packet VS-03. Stacked on the bonca / slayer / stone giant change (same importer section and tools). Presentation only.

## What changed

- `creatures.json` class row `dragon` (16 placements; walk 201-209 as a locomotion role; the original has no attack
  sequence, it spits fire while it treads). `SK_Dragon_PR` rebuilt: the brown hide of 202 (the first build was
  orange-tan), pale plated belly, wings as thin skins between finger spars in a pale green-grey with a scalloped
  trailing edge (they were 12 mm dark green slabs), the lower jaw hanging open with its own teeth.
- A kill leaves the corpse kit's torn dragon (`SM_Dragon_Corpse_PR`, sprites 212-218) at **scale 1.7**: at scale 1 it lay
  as a small heap beside the live dragon; the 1997 remains are about two thirds of the live dragon's width.

## Seen in the running game (`dragon.jpg`, rebuilt binary)

- Play camera, SCR_124: a brown dragon taller than Dink with raised green wings and a long tail; reads as 202.
- From above, SCR_160: the same among grey boncas.
- Killed: torn remains with ribs and red flesh in a dark pool with pieces thrown round it, a wing standing; about as
  wide as the live dragon's body and tail root.

## What still looks wrong (below alpha)

- The wing skins are flat panels: no folds, no translucency (the game material is opaque and two-sided), and in the
  game they read darker green than the source render and than the pale green-grey of 202.
- The remains are the corpse kit's older tan dragon: its hide is lighter and more orange than the rebuilt brown body.
  Only one remains mesh exists (made for 216); the torn head-and-neck of 212 is packet GP-Q7.
- A joint-graph sculpt, not anatomy; no wing-finger joints, lids, tongue or mouth lining; the jaw does not move.
- No fire-breath pose: the fireball is a script sprite (GP-Q9).

## Not checked / not run

- `Dink.Art` 66/66 and `Dink.Gameplay.Probe` 29/29 (twenty md5s equal to `packaged_probe.md`) passed on 16 Nov in the
  private copy that already held this row and these packages (binary: master 6ef7a590 + the duck/slime/pig change + the
  first monster change; not re-run after the rebase onto today's master). Python unit tests 903 OK with this row.
- Not looked at: the other dragon screens, the dragon fight at full speed, the packaged build.
- `source_dragon.jpg` is a Cycles render of the game mesh (source, not the game).
