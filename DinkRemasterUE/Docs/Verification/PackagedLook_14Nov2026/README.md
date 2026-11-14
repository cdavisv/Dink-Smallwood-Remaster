# Packaged game vs editor game, rendered (14 Nov 2026)

The question: does the packaged build draw the same thing as the editor build? Since PR #102 it cooks `/Game/Dink/Photoreal`; before that
it held no photoreal art at all. This is not a review of art quality, only of differences between the two builds.

## How
- Build: private copy of master d2754903 plus the alpha-qa round 2 branch. World regenerated (`--region all`, then `--region stonebrook`).
  `Scripts/package.sh` (content check 655/655 string-path assets in the package).
- Both builds ran on the private display `:189` (Xvfb with the real GPU, Vulkan, 1280 x 720).
  - Packaged: `Saved/StagedBuilds/Linux/DinkRemaster/Binaries/Linux/DinkRemaster -windowed`.
  - Editor: `UnrealEditor DinkRemaster.uproject -game`.
- Driven with `Scripts/playtest_desktop.py --private-display :189`: the new game's start, then `dink.Goto 438`, `439`, `26`, `244`. Each
  view was captured from the window about 8 s after arriving.
- `packaged_*.jpg` and `editor_*.jpg` are the same five views (JPEG 85 of the PNG captures).

## What I see
| View | Packaged vs editor |
|------|--------------------|
| 01 start house | Same. Photoreal hero, the Mother, barrels, fireplace, beams and floor are textured in both. |
| 02 screen 438 | Same. Oak, grass, hay bales and distant trees. Dink stands at the screen's centre, where `dink.Goto` puts him, inside the oak's trunk; that is the console's placement, not a build difference. |
| 03 screen 439 | Same. House wall, grass, fence, trees. |
| 04 screen 26 | Same: thorn meshes, the pill bug, and the chest still a sprite card in both (an unbound family, not a packaging fault). |
| 05 screen 244 | Same: boulders, vines, signpost, conifers. |

- Pixel difference between the pairs (share of pixels differing by more than 40/255): 2.1-8.1%.
- I looked at the pairs with the larger differences (02, 05). The differences are clouds, wind-moved foliage and the time of day, not missing content.
- No grey default material, no missing mesh, and no sprite card where the editor shows a mesh.
- The game logs of both runs have no fatal errors.

An earlier pair (round 1, same day) is not in this folder:
- It used the package built before the static stream's batch 1 merged, and showed the same result.
- Its editor half is spoiled: the playtest helper pressed Escape after every console command, which now opens the original's main menu.
  The helper is fixed in the alpha-qa round 2 code PR.

## Not checked
- Interiors other than the start house, dungeons, night or vision variants, NPCs other than the Mother, creatures in motion.
- Performance of the packaged build. Only five views in total.
