# Monsters as creature classes: bonca (three hides), slayer, stone giant, and what a kill leaves (15 Nov 2026)

Fable packets VS-04 (bonca, slayer, stone giant; not the goblins, not the fish), GP-Q1 (bonca corpses) and GP-Q2 (slayer
and stone giant corpses). Presentation only: hardness, scripts, brains, damage and the probe are untouched. One C++
change follows the original: a sprite without `base_death` leaves `base_walk + 5` (dink.cpp:12371-12383), which the
slayer (645) and the stone giant (825) need.

## What changed

| | before (master) | now |
|---|---|---|
| bonca brown / grey / purple (43 placements, 42 counted) | sprite cards | `SK_Bonca_PR` with three painted hides (brown with orange tiger stripes, grey with near-white, violet with lilac), white eye, idle / walk / run by measured speed, the bite on the attack sequences |
| slayer (21) | sprite cards | `SK_Slayer_PR`: teal chitin plates, open jaw with teeth, scythe arms, the whip tail level behind it (4.3 m snout to tip) |
| stone giant (14) | sprite cards | `SK_Stone_Giant_PR`: brown bedded sandstone, eye stones in sockets, a mouth cleft, hardened skin weights |
| a killed bonca | nothing (the card vanished) | the brown striped body soaked red, in a lobed pool with runs and about 150 thrown drops (ground decal 6.8 x 5.3 m; the pool itself about 3.4 m, 1.5 times the body) |
| a killed slayer | nothing | the body with its tail curled round, soaked red, in its pool with drops (decal 6.4 x 5.0 m) |
| a killed stone giant | nothing | a heap of ten blocks of its own stone on dark grit; no blood (825 has none) |

`art_coverage.py` (private copy, whole-world coverage report of 15 Nov): final 5,125 -> 5,201, placeholder 1,330 -> 1,254 (on master of 16 Nov after the rebase: 5,139 -> 5,215),
cut 152 (bonca_gray 21, slayer 21, stone_giant 14, bonca_brown 12, bonca_purple 9).

## Sheets (every frame is from the running game unless it says "source")

- `bonca.jpg`: the 1997 frames over the game. Row 2: brown boncas of SCR_029 at the play camera. Row 3: close (brown,
  purple in the cave of SCR_514). Row 4: killed brown (SCR_029), grey (SCR_090), purple (SCR_514).
- `before_after_play.jpg`: the play camera with the class art off (`-dpcvars=dink.CreatureClassArt=0`: the 1997 pictures on
  cards) and on, on SCR_029, SCR_157, SCR_178 and SCR_514; and what a killed bonca left before (its gold, nothing else)
  and leaves now.
- `whole_screen_and_giant_heap.jpg`: from above on the rebuilt binary: brown boncas (SCR_029), grey boncas alive (SCR_090,
  SCR_160), slayers (SCR_028, SCR_157), stone giants in the darkened stone (SCR_178), and the killed giant's heap.
- `slayer_giant_killed.jpg` (rebuilt binary): 645 and 825 over the game: slayers killed on SCR_028 and SCR_157 (the body on
  its side, tail curled, soaked red over the teal, in a bright pool wider than the body with drops and runs), and the
  stone giant's heap on SCR_178.
- `slayer_giant_live.jpg`: slayers on SCR_157 and SCR_028, the stone giant on SCR_178, play camera and close. These are
  from the first import: the giant in them is the paler stone, before it was darkened (see below).
- `source_bonca_three_hides.jpg`, `source_slayer.jpg`, `source_stone_giant.jpg`: Cycles renders of the game meshes
  (source, not the game). `source_corpses_preview.jpg`: the three corpses on their ground pictures (source, flat light).

## What I saw

- Bonca: at the play camera the brown ones read as dark animals with orange stripes across the back and red-brown legs,
  as 531; the violet one with lilac stripes reads in the cave light of 514. Close up the hide has plates and scale
  cells and folds; the white eye is there. The killed ones lie soaked in a bright red pool that reaches past the body on
  every side with drops and runs all round: more than 551-559, not less. All three colours leave the brown body, as the
  original's one death set does.
- Slayer: teal with rust blotches, plated, the tail level behind it, scythes; at the play camera it is a low, long
  animal as 641.
- Stone giant: knuckle-walking stone ape with strata and joints, a face with sockets and a mouth.

## What still looks wrong (below alpha)

- All three are still sculpts from a joint graph, not anatomy: no muscle, tendon or joint structure; decimated game
  meshes without edge loops at the joints; automatic skin weights. They pass at the play camera, not at 1 m.
- Bonca: the face is soft and seal-like, the mouth cannot open (no jaw bone), the same stripe layout on all three
  colours; the brown reads mid-brown in sunlight, lighter than the near-black of 531.
- Slayer: the jaw hangs open but does not move; legs are not segmented beyond the plate texture; no wet eye highlight.
- Stone giant: one skin with hardened weights, not separate rocks: seams still bend at the shoulders and hips.
- Pools are a flat decal: bright and glossy, no thickness, and they do not follow the body's facing beyond the yaw.
- The stone giant still reads pale in full sun (tan, lighter than 821) although its stone was darkened; its remains are
  blocks that overlap each other rather than a tidy heap, and the grit decal under them does not show through grass.
- The grey bonca is seen alive only from above (SCR_090, SCR_160), not close.
- Clips are authored poses (idle, walk, run, attack), not motion capture; the attack is one lunge for every direction.

## Not checked / not done

- `Dink.Art`: 66/66 passed (16 Nov, on the rebuilt binary: master 6ef7a590 + the duck/slime/pig change + this change;
  the `CorpseFor` test lines are in it). Python unit tests: 903 OK in the private copy.
- `Dink.Gameplay.Probe`: 29/29 passed (16 Nov, same binary) and the twenty trace md5s equal the current table of
  `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 b4ad88c02c ... Ch20 84f33687af).
- The binary of the frames: `bonca.jpg`, `slayer_giant_live.jpg` and `before_after_play.jpg` were taken on the build of
  15 Nov noon (master + the duck/slime/pig change), `whole_screen_and_giant_heap.jpg` and `slayer_giant_killed.jpg` on the rebuilt one (master
  6ef7a590 + the duck/slime/pig change + this change). Neither is today's master.
- Goblins (GP-Q3) and the fish (VS-04) are not in this change: they stay on cards. The dragon is the next change.
- Not looked at: every other screen of the 57 (only 28, 29, 90, 157, 178, 514), fights in motion at full speed, the
  packaged build, frame time with many of them on screen.
