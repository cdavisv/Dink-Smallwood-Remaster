# Goblins as creature classes; the dragon's own remains; pools; corpse LODs (16 Nov 2026)

Fable packet GP-Q3 and the follow-ups recorded on the monster and dragon changes of 15/16 Nov. Presentation only: no
collision, hardness, script, warp or origin ID changes.

## What changed

- `creatures.json` class rows `goblin_hammer` (4 placements), `goblin_soldier` (6 placements) and `goblin_horned` (Mog,
  made by `s3-mog`, no placement). The three bodies were rebuilt (`build_goblin.py`): a bare olive body, garments as
  separate shells, rigid gear (helmet, weapon, shield), a horned kit for Mog. Walk and attack are bound; hit and death
  clips are delivered for the creature one-shots.
- A killed goblin leaves `base_walk + 5` (765 / 785 / 805, dink.cpp:12371-12383): the body on its back, drenched, the
  weapon beside it, with a pool decal.
- A killed dragon leaves its own remains (`/Game/Dink/Photoreal/Creatures/Dragon/SM_Dragon_Corpse_PR`) instead of the
  corpse kit's tan dragon: the brown body of the death pose torn at the neck, a wing root, a hip and the tail, lying on
  the ground, the wing under the body torn off flat, the other still raised with its pale skin bloodied from the root, as
  picture 212 has it. The placed 216 card keeps the kit asset.
- Pool pictures of every monster corpse (`corpse_blood.py`): dark where the blood stands (a hand's width inside the rim
  and in blotches), bright only at the thin rim, drops and runs in the drying tone; decal roughness 0.30. Blood on the
  bodies is as dark as the pool they lie in.
- Three LODs on every monster corpse at import (100 / 50 / 25 % of the triangles).
- The stone giant's stone is a step darker (`build_giant.py`).

`art_coverage.py` with this copy's whole-world coverage report and master ff517892 data: final 5,501 -> 5,511,
placeholder 954 -> 944, cut 152 (the ten goblin placements). `doc/remaster/ALPHA_GATE2_BACKLOG.md` is NOT regenerated in
this change: the copy's coverage report predates the structure-set change on master and shows one row (`npc_mom`)
differently from master's ledger; `goblin_hammer` and `goblin_soldier` leave the ledger with the next regeneration on a
fresh export (it follows with the gore follow-up change).

## Found on the way (said in the Master log for the code streams; nothing of it is changed here)

- The first capture left no goblin corpse. `dink.Hurt` does not run a sprite's `hit`; a real blow does, and the goblins'
  `hit` is what makes them brain 9. The captures therefore send `dink.Run <script> hit <origin>` before the killing blow.
  A goblin killed by its very FIRST blow still leaves nothing (the presenter's last reading is brain 16): code item.
- The pool decal of a corpse lying in grass is almost invisible from the play camera (only blade tips take it): the grass
  carpet opens over the placed ground decals but not over corpse decals. Code item.
- The dragon's death pose rests on the wing under the body; once that wing was torn off and flattened the carcass hung
  0.9 m in the air (the "piece standing up" of the earlier capture). `tear` now sets the trunk down on its spine and ribs.

## Seen in the running game (private copy, captures on master 41e80f73 + this change; every frame opened and looked at)

`goblins_alive.jpg`
- Play camera, SCR_680 and SCR_713: an olive goblin soldier a head taller than Dink in a scale coat with shoulder plates,
  helmet, round wooden shield on the forearm and a long bill; hammer goblins in a leather jerkin and skullcap with a war
  hammer. They read as 801 and 761. Before: the 1997 pictures on cards.
- Mog (781), spawned by `s3-mog` after the four goblins of 680 were killed with `&gobpass` 1: a bigger goblin with a
  horned helmet and a club, chasing Dink.
- Close up the limbs are simple smooth forms and the faces have little detail: fine at the play camera, not close up.

`goblins_killed.jpg`
- 765 / 805 in the game: the body on its back, drenched dark red with the green skin showing in places, hammer or bill
  and shield lying on or beside it. On the earth of SCR_713 the pool reads as blood (dark where it stands, bright thin
  rim, runs and thrown drops) and is wider than the picture's. On the grass of SCR_680 the same pool only reddens the
  grass round the body: clear from above, weak from the play camera. That is less than 765 shows and is the code item
  above (grass clearing under corpse decals), not something a texture can fix.
- At about 15 m and 26 m (second and third LOD) the corpses hold their silhouette; no popping artefact seen in stills.

`dragon_remains_and_pools.jpg`
- Before (07:20 import): trunk in the air, a piece upright, flat paint-red pools.
- After, SCR_124: the carcass lies on the ground, dark red with the brown hide showing, tail end and a leg thrown
  clear, one wing torn off flat, the other raised with pale skin and blood running from the arm, as 212; the pool is
  about as long as the remains with a dark middle, bright rim and drops.
- Bonca (551) and slayer (645) with the new pools and darker soaked bodies.
- Stone giant heap (825): the tumbled limbs read at every distance; no blood, as the picture.

## Rejected and rebuilt in this change

- Pools that were one bright red (read as paint in the sun): rebuilt twice, see `corpse_blood.py` `stand`.
- Dragon remains that were soaked red all over including both wings, with the trunk off the ground.
- Corpse bodies at 0.54 red with a lacquer gloss: darkened to the pool's tone and made tacky.

## Still below the bar

- Goblin anatomy close up (smooth limbs, plain faces and hands); their dead bodies are the same forms.
- Pool on grass (code item). The dragon's wing skins are flat panels with hard edges, also in the remains.
- The stone giant is still paler and more orange than 821 / 825 (khaki-grey with dark joints); its grit decal does not
  show on grass.
- Follow-ups of the earlier review not touched here: bonca face and mouth, slayer skin (orange / teal against the darker
  armoured 641).

## Tests

- Private copy on master 84e045b0 + this change (one commit), binaries built there (0 warnings); rebased afterwards onto ff517892 (#184 structure sets, #187 audio limiter: no file in common but the ledger; tests not re-run on it), world regenerated with
  `import_greybox.sh --region all --export` and `--region stonebrook` on 5d8a4a1f + this change (no exporter or importer
  change on master since; `Dink.Import` 23/23).
- `Scripts/test.sh Dink.Art`: 69/69 passed (16 Nov, 12:56).
- `Scripts/test.sh Dink.Gameplay.Probe`: 29/29 passed (16 Nov, 13:23); the twenty trace md5s equal
  `Plugins/DinkParity/Docs/packaged_probe.md`: Ch1 b4ad88c02c, Ch2 bc267a0dfc, Ch3 bbd401167c, Ch4 8740518c57,
  Ch5 d987c043f6, Ch6 2df37e4a27, Ch7 a16d1d23b8, Ch8 764e9d330f, Ch9 dd1e2662fa, Ch10 23fd57dfdc, Ch11 0d70cebfcd,
  Ch12 79c8ce55f9, Ch13 98a2e17ba0, Ch14 f1ddbaab7b, Ch15 7e3dbbd0b1, Ch16 48e797069a, Ch17 4277c65c35, Ch18 d33886b797,
  Ch19 45b399bac8, Ch20 84f33687af.
- Python unit tests (`python3 -m unittest discover -s Scripts/tests`, in the copy on 41e80f73 + this change): 959 run,
  one failure, `test_present_lfs_files_hold_no_private_data`, because the copy holds the unscrubbed imports and Blender
  exports; in the tree of this change `scrub_private_paths.py --check` is clean (whole tree) and
  `lfs_private_check.sh` finds 0 private hits in 272 LFS files. Not re-run on the final master.
- The captures were taken on 41e80f73 + this change (alive goblins, Mog, the giant heap: capture A7) and
  after the last texture pass (kills: capture A8); the art files are the ones tested above.

## Not checked

- Mog's remains (785): he was seen alive but not killed (`dink.Hurt` takes only an origin ID; he is script-made). The
  mesh is built and previewed like the other two.
- Goblins on SCR_712 and SCR_748, goblin fights at full speed, the hit / death / attack one-shots (another change plays
  them), the packaged build.
- LOD switches were looked at in stills at two distances, not in motion.
