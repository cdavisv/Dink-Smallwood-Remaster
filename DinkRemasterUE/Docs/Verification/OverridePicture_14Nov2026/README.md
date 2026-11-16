# Saved editor picture shown on a revisit (14 Nov 2026)

Bug list A77 (A9 on the 14 Nov branch). A placement whose save holds an editor_type 2-5 gets the save's editor_seq / editor_frame on every screen
load (`update_play_changes`, dink.cpp:5773-5832) and is drawn with that picture (`place_sprites_game`: 6036-6054 into the
background for 3/5, 6083ff as a live sprite for 2/4). PR #115 made the simulation follow this; the look did not. This change
(`UDinkGameplay::PresentPlacementPictures`, on every screen entry) gives the placement actor's card the saved picture at that
picture's size and pivot, shows a background-drawn placement again, and looks the family mesh up from the saved picture.
Presentation only: hardness, collision, scripts and the probe are untouched.

## How
- Private copy of master 79597061 (PRs #116-#124 merged, voice packages pulled) plus this branch, rebuilt (`Scripts/build.sh`, 0 warnings).
  World regenerated with the branch's exporter and importer (`--region all`, then `--region stonebrook`), so the saved
  pictures' sprite materials exist (`MI_Sprite_175_04` and the rest of `sync_gameplay_data.saved_picture_keys`).
- Captures: `Scripts/PhotorealQA/run_capture.sh` (offscreen Vulkan, 1280 x 720). The script skips the intro, sends the player
  to the screen with `dink.Goto`, puts a fixed camera on the placement (`dink.CalAnchor`, `dink.CalCam 0 520 420 0 <yaw> 60 55`),
  takes shot 1, runs the placement's own `hit` procedure (`dink.Run bar-sh hit S060_P08`, the script that writes
  `editor_type` / `editor_seq` / `editor_frame`), takes shot 2, leaves for SCR_471, comes back and takes shot 3 from the same
  camera. Nothing was retouched; the JPEGs are the PNG captures at half size with a label bar.
- "master" rows were captured on master 25a1f346 (before this branch's code), the same cameras and script. The "fix off"
  panels were captured on this build with `dink.SavedPicture 0`, which skips `PresentPlacementPictures`: they match the
  master rows, so the review switch gives the old look back.

## Sheets and what I see
| File | Placement | What I see |
|---|---|---|
| `s060_before_after.jpg` | SCR_060 P08, barrel 173/1, `bar-sh` (editor_type 3, 173/6), legacy screen, family `barrel` (oak barrel mesh, not fitted) | Master: the oak barrel on the first visit; after the hit only the dropped heart is left (the sprite's brain 5 kill hid the actor); on the next visit nothing stands there at all. This change: the first two panels are the same; on the next visit the smashed barrel lies flat on the ground, the `barrel_broken` family mesh (`SM_Barrel_Smashed_PR`, splayed staves), looked up from 173/6. |
| `s536_before_after.jpg` | SCR_536 P31, large chest 177/1, `ch1-ap` (editor_type 4, 175/4), legacy screen, no family row (sprite card) | Master: the closed large chest card in all three panels; the potion it drops lies in front of it, but the chest is closed again on the next visit. This change: on the next visit the card shows the open chest picture 175/4 (lid up, dark red). It is drawn at that picture's size from the imported card's baseline (50 x 62 px instead of 60 x 60, pivot 25/50 instead of 40/50: 2 px taller, its centre 10 px to the right), which is what the original does with a frame of another size. The camera is close, so the card is large and its top leaves the frame. |
| `s282_before_after.jpg` | SCR_282 P06, small chest 175/1, `ch1-gh` (editor_type 4, 175/4), tagged (hardness-world) screen | Fix off: the closed small chest card on the next visit. This change: the open chest card (175/4). The three fixed-camera panels of this screen are hidden by a pine, so this sheet is the extra camera (`dink.CalCam 0 260 140 0 -341 60 55`) taken after the return, both with the fix off and on. |
| `s031_before_after.jpg` | SCR_031 P03, barrel 173/1, `bar-gh` (editor_type 3, 173/6), tagged screen, fitted barrel (`families.json` `collision_fit`) | Master and this change are the same: the whole barrel, then the flat barrel card 173/6 after the hit and on the next visit. Fitted barrels already published their released picture (`PublishHardnessFitVisuals`) and this change leaves them alone, as intended. |
| `s060_s536_fix_off.jpg` | SCR_060 P08 and SCR_536 P31 on the next visit with `dink.SavedPicture 0` | Nothing where the barrel was; the closed chest. The master look, on this build. |

## Tests
- `Dink.Gameplay.OverridePicture` + `Dink.Gameplay.EditorTypeSwap` + `Dink.Gameplay.Hardness`: 18/18 (one with warnings, as before).
- `Dink.Art`: 63/63 (1 with warnings). `Dink.Import`: 23/23 (6 with warnings). (Branch on master adf5b1dc, world regenerated.)
- Full `Dink` suite: all pass except `Dink.Animation.NpcShownMotion` (timed out; it also fails in another copy's run and passes in five others: load-flaky, not this change).
- Python: `python3 -m unittest discover -s Scripts/tests` in the private copy: 879 tests OK (adds `test_saved_picture_keys.py`).
- Probe: all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 b4ad88c02c ... Ch20 84f33687af).
- Carried into the presentation-fixes PR (15 Nov 2026): Python `Scripts/tests` 904 OK on the rebase onto 6ef7a590; that PR's run 1 (master da511dbc + both changes) `Dink.Art` + `Dink.Gameplay.OverridePicture` + `Dink.Gameplay.EditorTypeSwap` + `Dink.Gameplay.Probe` 100/100 with the twenty md5s equal (`Docs/Verification/PresentationFixes_15Nov2026/`).

## Not checked
- The look during the visit: the card still does not follow the sprite's animation (the chest card stays closed until the next
  visit, the smashed legacy barrel disappears at the end of its brain 5 animation and comes back on the next visit). Recorded
  in bug list A77 as still open.
- Only one placement of each kind was captured (two chests, two barrels). The other saved pictures (175/6, 177/6, 443/7 and
  444/7 crates, 20/29 burnt tree) are imported and go through the same path but were not captured.
- A packaged build was not run; captures are from the editor game (`-game`). The sprite-card look itself (pixel art, the
  checkerboard ground patch under the chest) is the placeholder art of gate 2, not this change.
- Saves written before this change (editor_seq / editor_frame 0) show the imported picture, by design; not exercised here.
