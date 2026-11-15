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

**Most grey cylinders remain**: 33 of the 35 the sweep found are script **people** (the Terris bar wench and drinkers,
the cave guide of `s2-cave`, townsfolk) whose scripts give them a picture but who have no character art; the marker
stands in for a person and must stay until they have art. Queued as Fable row VS-16.

## 3. Tried and dropped: scripted boulders

Binding the existing field boulders to the scripted rocks (`scripted: true` on the five boulder rows of `families.json`)
was built and captured: the boulders are 1.1-1.6 m against 6-7 m cards, so the push rock of 277 uncovers the cave hole
card under it and the Windemere bomb rock (S536_P15) shrinks to a pebble inside its hardbox. Kept as cards, as the
faceting sweep had decided; queued as Fable row VS-15 with the sheet
`../VisualSweep_15Nov2026/scripted_boulders_tried.jpg`.

## Checks

- Build of the private copy (master + this change): 0 warnings.
- `Scripts/test.sh "Dink.Art+Dink.AI.Screenlock+Dink.Gameplay.Probe"` on master `f92915fe` + this change (and the
  boulder rows, since dropped): 95/95 in 638 s. The twenty probe md5s equal `Plugins/DinkParity/Docs/packaged_probe.md`
  (Ch1 b4ad88c02c ... Ch10 23fd57dfdc, Ch11 0d70cebfcd ... Ch20 84f33687af). On master `0f1185b8` + this change the private copy builds (0 warnings); the test run on that tree is queued behind the Unreal lock (result in the PR when it lands).
- The sweep's second capture run (121 screens, `Scripts/PhotorealQA/visual_sweep.py --screens=...`) on the same tree:
  no LockBarrier primitive in any audit, no material/texture warning in the log.
- No binding changed: `art_coverage.py` counts and `ALPHA_GATE2_BACKLOG.md` do not move.

## Not checked

- A fight on a locked screen played through by hand (the slabs' collision is covered by the test, not by play).
- The packaged build.
