# Visual sweep fixes (15 Nov 2026)

The non-Blender fixes from the whole-world visual sweep (`../VisualSweep_15Nov2026/`, PR #132). Presentation only:
no collision, hardness, script or story change; probe traces unchanged.

## 1. Screenlock slabs: block, but are not drawn

`ADinkScreenVolume::SetLockBarriers` raised a 1.6 m slab of the engine's `/Engine/BasicShapes/Cube` along every open
edge of a locked fight screen and **showed** it: grey WorldGrid walls with no material (the sweep's audit found them on
29 screens: 26, 27, 32, 64, 90, 91, 106, 123, 126, 137, 138, 156, 157, 160, 170, 190, 191, 223, 237, 270, 301-303, 334,
514, 515, 547, 577, 609). The original draws no wall there: `drawscreenlock` (`source/dink/dink.cpp:16769-16787`,
called at 17483-17485) frames the whole game area with a pulsing red border and the lock icon. The slabs now keep
their collision (Dink, monsters and missiles are still held on the screen) and are hidden, without shadow.
Test: `Dink.AI.Screenlock.BarrierBlocksExits` asserts the slabs still block a walker and a projectile and are not drawn.
Evidence: `lock_slabs_before_after.jpg` (026 and 123/190 from above, 090 at the play camera; the creatures on 090 differ
because the fight is live). Not done: a remaster version of the red frame (a UI item).

## 2. `create_sprite` sprites without a picture: no grey marker

A sprite a script makes with `create_sprite(x, y, brain, 0, 0)` and never gives a picture (touch, hardness and warp
helpers) is never drawn by the original: `getpic` returns 0 for `pseq` 0 and `draw_sprite_game` returns when
`getpic < 1` (`dink.cpp:443-445, 5498`). The remaster drew the grey placeholder cylinder for it. `PresentScriptSprite`
now hides the marker while the sprite has no picture and shows it again when a script gives it one (sequence > 0 and no
family mesh). Test lines in `Dink.Art.Family.ScriptSpriteShowsFamilyMesh`. Evidence: `pictureless_marker_before_after.jpg`
(364, 408: the small grey cylinder in the overview is gone).

33 of the 35 grey cylinders the sweep found were script **people** (the Terris bar wench and drinkers, the cave guide of
`s2-cave`, townsfolk) whose scripts give them a picture but who have no character art: since section 4 they are drawn as
their 1997 picture on a card; real character art stays Fable row VS-16.

## 3. Tried and dropped: scripted boulders

Binding the existing field boulders to the scripted rocks (`scripted: true` on the five boulder rows of `families.json`)
was built and captured: the boulders are 1.1-1.6 m against 6-7 m cards, so the push rock of 277 uncovers the cave hole
card under it and the Windemere bomb rock (S536_P15) shrinks to a pebble inside its hardbox. Kept as cards, as the
faceting sweep had decided; queued as Fable row VS-15 with the sheet
`../VisualSweep_15Nov2026/scripted_boulders_tried.jpg`.

## 4. Script sprites with a 1997 picture: drawn as that picture (A53), Seth included

A sprite a script creates whose picture has no family mesh (script people, effects, Seth) showed the grey placeholder cylinder.
`UDinkArtFamilySubsystem::DressScriptSprite` now puts its 1997 picture on a camera-facing card (true size 0.025 m per pixel
times `sp_size`, origin pixel on the ground point) and hides the marker. `Content/Dink/Data/Art/sprite_pictures.json`
(`Scripts/export_sprite_pictures.py`) lists the 2,770 pictures; the bundle imports every one of them (regenerate the world with
`--export` after merging). `script_sprite_cards_before_after.jpg`: 162 (the grey cylinder is now the 1997 picture), 193 (the
woman in red), 034 (the bar person behind the counter); 579 unchanged at the play camera.

Seth (16 Nov 2026): `s7-mil.c:9-13` loads his pose into 580 (not in dink.ini) and his walks over dink.ini's green gnome in
581/583/587/589 with `init("load_sequence_now ...")`. `figure_out` reloads an active sequence from such a line
(`dink.cpp:2343-2366`: ReadFromLoadSequenceString, FreeSequence, ReloadSequence), so in 1997 those are Seth's frames, never
the gnome's. The exporter now reads the story's init lines (hero sequences excepted) and writes their frames from the 1997
archive as `init_<file>_<frame>` (34 frames: pose 2, four walks of 8); the director's `init` command and a loaded game
register the line (`RegisterInitSequencePicture`), and a card of that sequence then shows the init frame and no family mesh
of the old picture. Tests: `Dink.Art.Family.ScriptSpriteShowsFamilyMesh` (init lines for 580 and 581: cards with
`MI_Sprite_init_pose_01` / `MI_Sprite_init_seth1w_01`, no marker, no gnome; a hero line is ignored),
`Scripts/tests/test_sprite_pictures.py` (init line parsing, the committed keys and pose origin 41,129). The gameplay side of
the same lines (Seth's walk keeps the gnome's hardbox) is bug A96, not changed here.
In the game (capture of 16 Nov: SCR_086, `dink.Run s7-mil talk`, "Refuse to leave without him", the lines skipped):
`seth_scr086_card.jpg` right: Seth appears (`create_sprite(320, 150, 0, 580, 1)`, `s7-mil.c:97`) as his 1997 pose, arms
crossed, on a card about 4 m tall; Milder lies in his pool beside him; no grey cylinder (the scene audit lists the
`ScriptPictureCard` with `MI_Sprite_init_pose_01`). NOT seen in a frame: his walk cards (s7-boss walks on base 580; the first
capture's frames of the walk faced away from him), the cast pose while he fights, the death. Seth is still a flat 1997
picture: the model is Fable row PQ-Q1, the arena (grey slab walls, lava band) PQ-Q6.

## Checks

- 16 Nov 2026, the final tree (this branch rebased on master `3a7b4451c`, private copy built from it): build OK, 0 warnings;
  `import_greybox.sh --region all --export` (2,775 sprites exported, 34 of them `init_*`) and `--region stonebrook` OK,
  `Dink.Import` 23/23 each; `Scripts/test.sh "Dink.Art+Dink.AI.Screenlock+Dink.Gameplay.Probe+Dink.Input.FreezeReleasedByReset+Dink.Narrative.Director"`
  **107/107** (678 s, 6 with warnings); **the twenty probe md5s equal the current baseline of `Plugins/DinkParity/Docs/packaged_probe.md`**
  (Ch1 b4ad88c02c ... Ch10 23fd57dfdc, Ch11 0d70cebfcd ... Ch20 84f33687af).
- `python3 -m unittest discover -s Scripts/tests`: 962/963 in the private copy; the one failure, `test_art_wiring_audit.OwnerIds`,
  reads `doc/remaster/ALPHA_BUG_LIST.md` that a private copy does not have, and passes in the worktree (41/41 for that file).
- Capture `cards5` (24 screens: lock screens and the people screens 34, 33, 35, 36, 162, 193, 579 ...) at the play camera and
  from above: no grey slab, the people are 1997 picture cards (sheet `script_sprite_cards_before_after.jpg`).
- 15 Nov: fixes 1-2 on master `f92915fe`: 95/95 and the probe md5s equal; the sweep's second capture run (121 screens): no
  LockBarrier primitive in any audit, no material/texture warning.
- No binding changed: `art_coverage.py` counts and `ALPHA_GATE2_BACKLOG.md` do not move.

## Not checked

- A fight on a locked screen played through by hand (the slabs' collision is covered by the test, not by play).
- The packaged build.
