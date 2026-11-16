# Presentation fixes of the visual sweep (15 Nov 2026)

Three defects of the whole-world sweep (`Docs/Verification/VisualSweep_15Nov2026/`, worst-20 rows 5, 7 and 19) that need
no Blender: the play camera inside pine crowns (bug A78), the small treasure chest drawn as a pixel card up to 4.5 m
(rows in `families.json`, with the carried saved-picture fix A77), and very dark caves (A79, VS-13). Presentation only:
hardness, collision, scripts and the twenty probe traces are untouched (see Tests).

## How it was run
- Private project copy: master `da511dbc` plus this change, built (`Scripts/build.sh`, 0 warnings). World: the copy of the
  visual sweep's regenerated world (master `f92915fe` importer) plus the six saved-picture sprite assets the carried
  A77 importer builds (175/4, 175/6, 177/6, 20/29, 443/7, 444/7), taken from that branch's own import.
- Fade materials: `Scripts/import_camera_foliage_materials.sh` (editor commandlet): `DINK CAMERA FOLIAGE MATERIALS READY`.
- One capture run (`Scripts/PhotorealQA/run_capture.sh`, offscreen Vulkan 1280 x 720, `-nosound`), script made by a
  scratch generator: play camera (boom 400 cm, pitch -12) at the sweep's capture points.
  - Camera: per screen `dink.CameraFoliageFade 0` (old look) then `1`, looking north and looking east; a walk across the
    wood of 343 with eight frames at 0.5 s.
  - Chests 282 (`ch1-gh`), 557 (`ch1-pap`), 069 (`ch1-mp`): Dink 26 px south of the chest, `dink.WalkTo` into it,
    `dink.Attack` (the fist, the game's own hit), frames during and after the opening, then off to screen 299 and back.
  - Light: the json values are the old ones x 2.5 and -0.5 EV, so `dink.IndoorLight 0.4` + `dink.IndoorEV 0.5` is exactly
    the old look ("before"); "after" is the new json; "alt16" is 1.6 x brighter still, for comparison.
- Every frame of the run was looked at on the sheets; the frames under `frames/` at full size.

## 1. Camera inside pine crowns (A78)
`sheet_cam_a.jpg`, `sheet_cam_b.jpg` (312, 343, 134 / 240, 272, 535; columns: old north, new north, old east, new east),
`frames/cam_312_*`, `frames/cam_343_*`.
- Old: on all six screens the frame is needles and branches; Dink is hidden or a sliver (312, 272, 535 east, 240 east).
- New: the crowns between the camera and Dink are gone, Dink stands clear in the wood, the trunks and the crowns
  around and behind him stay, and their shadows stay on the ground (the shadow pass keeps the whole tree). No stipple
  is left at full fade (`frames/cam_312_on.jpg`). 134 (dark interior with a canopy) shows Dink.
- Walk (`sheet_cam_walk.jpg`): the camera distance stays at 400 cm in every frame (no pumping: the boom is never
  shortened for foliage). Frames 4-7 (Dink stopped at the wood's west edge) still show low branches of a crown in front
  of him with Dink visible through them: that crown's branches reach past the cylinder the fade uses
  (0.8 x the mean half extent). Not changed; a wider radius fades more of the wood around Dink.

## 2. Small treasure chest
`sheet_chest_282.jpg`, `sheet_chest_557.jpg`, `sheet_chest_069.jpg` (closed play / closed close-up / 0.45 s after the
punch / open / open close-up / after walking into it / next visit / next visit close-up).
- The chest is `SM_Chest_Small_PR` at 1.25 x (about 1.2 x 0.65 m), front edge on the sprite's foot; beside Dink
  (1.8 m) it reads as a large chest, not a 4.5 m card.
- The punch opens it at once: the game log has `S282_P06 follows its animation to 175/2 ... 175/3 (SM_Chest_Small_Open_PR)`
  within 0.1 s of the hit and the frame 0.45 s after the punch shows the lid up (282, 557, 069).
- The loot appears: the purple potion of 069 stands in front of the open chest; 557 shows the gold in it.
  The next visit shows the open chest on all three (the saved 175/4 or 175/6, A77).
- Collecting the loot: run 2 below.

## 3. Caves and dungeons (A79)
`sheet_light_a.jpg`, `sheet_light_b.jpg` (69, 73 lit reference, 98-101, 164, 166, 227, 257, 609; before / after / alt16).
Mean frame luma before -> after: 69 0.078 -> 0.152, 98 0.081 -> 0.164, 99 0.096 -> 0.190, 100 0.082 -> 0.163,
101 0.078 -> 0.155, 164 0.076 -> 0.156, 166 0.081 -> 0.156, 227 0.086 -> 0.156, 257 0.108 -> 0.188, 609 0.100 -> 0.194;
the torch-lit snow-castle room 73 0.166 -> 0.305 with its torch pool not blown out. The floor relief, the bones and
pickups now read; walls stay grey-dark, the room still dark at its far end. alt16 was not taken (it flattens the mood).

## Tests
- Run 1 (master da511dbc + change): `Dink.Art` + `Dink.Gameplay.OverridePicture` + `Dink.Gameplay.EditorTypeSwap` +
  `Dink.Gameplay.Probe`: 100/100 passed (1 with warnings) in 605 s; the twenty probe md5s equal the table
  (Ch1 b4ad88c02c ... Ch20 84f33687af). New: `Dink.Art.CameraFoliage.Geometry`, `Dink.Art.CameraFoliage.Variants`.
- Python `Scripts/tests` in the copy: 889/889 (new `test_chest_family_rows.py`).
- Run 2 (master 9cc796b6 + this change, built 0 warnings; the branch was then rebased on 9a37e580, whose family-anchor
  change to `DinkArtFamilySubsystem.cpp` merged cleanly and passes the offline syntax check): the same test filter
  102/102 passed (6 with warnings) in 628 s; the twenty probe md5s equal the table again.

## Run 2: collecting what a chest drops
`run2_loot_sheet.jpg`, `run2_loot_log.txt` (facts printed before the punch, after walking into the chest from the
south, and after walking at the drop point from the east). Same build as the run-2 tests.
- 557 (`papgold`): gold 0 -> 200 at the punch (Dink stands in reach as the chest opens). Collected.
- 282 (`gheart`): lifemax 10 -> 20 at the punch (sounds 10 and 22). Collected.
- 069 (`mpotion` -> `ppotion`): magic stays 0 and no sound 10, also with Dink standing on the drop point (map 328,206;
  the potion is at 323,204). Neither the chest's hardness nor a player blocker is in the way (chests have no player
  blocker: they are scripted). The potion itself is not touchable: bug A80, open, not a presentation defect; its
  first suspect is the touch test of a script sprite that animates its own `sp_seq`.
- The family mesh change at the punch now happens once per opening (175/3); before, every later frame of the same
  mesh rebuilt the component and the log showed a game-thread hitch warning for each.

## Not checked
- A80 (the magic potion of 069) is not fixed here.
- The packaged build (the variants are cooked from `Dink/Camera`; not run).
- Other forest screens of the sweep list than the six above; night/vision variants; a gamepad-rotated camera.
- Chests other than 282, 557, 069; the large chest of 536 (shows the small chest's pictures as its script plays 175).
- `chest_medium` (176) and `chest_large` (177) keep their cards (VS-07).
