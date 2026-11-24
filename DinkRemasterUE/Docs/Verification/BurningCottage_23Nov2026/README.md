# The burning state of the Stonebrook cottage, screen 439 vision 1 (DS-01), 23 November 2026

**Seen in the running game on 23 November 2026** (three capture rounds; sheet `burning_cottage_ingame.jpg`). The first
round showed nothing of this change and the second showed a fault that is fixed here; both are told below.

## What it is

1997 shows the starting house burning (`s1-h1-o.c`: `&story` 3-4 sets `&vision` 1): four fires on the roof and picture
154 (`S439_P29`), a large hole burnt into the roof with glowing laths. Master draws the fires (PR #166) on an intact roof.

- `SM_Cottage_Stonebrook_PR_Burning` (`Structures/tools/stonebrook_build.py`, `cottage(m, burning=True)`): the same
  fieldstone cottage as `SM_Cottage_Stonebrook_PR` (built from the same random stream, so the swap changes only what
  burns), with an opening eaten into the front slope right of the middle, where the 1997 screen has it (0.49 to 0.71 of the
  eaves, from about a metre above the eaves to the ridge). The thatch is cut back in 84 bundles of straw about 6 cm wide that end at unequal
  heights along a wandering outline, so the opening is ragged; charred rafters, laths and the bared ridge pole cross it; under it is the
  burnt-out room itself (charred floor, the inner faces of the walls, two cross walls stepped under the roof, fallen
  timbers), not a painted void.
- `Content/Dink/Data/Environment/environment.json`: one `state_swaps` row, screen 439 vision 1, from the intact cottage to
  this mesh, hiding the `burn_hole_decal` cards it models. Vision 2 (the burnt-out ruin) is unchanged on master.
- Division agreed in the Master log (16 Nov 22:00) with the effects stream: the hole and its timbers are this mesh;
  flames, burn patches 155-157 and the char under the roof fires are theirs.

## What I saw in the game (`burning_cottage_ingame.jpg`, 1997 screen at the top left)

Copy of master `6e3d4f991` + this change (and the two blood changes #216, #224), clean build, Stonebrook kit imported
headless, `Scripts/PhotorealQA/run_capture.sh` at 960x540, `dink.Fact story 3`, `dink.Vision 439 1`.

- Round 1 (12:56, frames `fableB/ds01b`): the roof was intact in every frame. Cause: the copy carried another branch's
  `environment.json`, so the vision-1 `state_swaps` row of this change was missing. Nothing could be judged. (What looked
  odd behind the ridge in the frame from the north is the woven ridge of the thatch and the pond south of the cottage.)
- Round 2 (13:42, `gore4/ds01c`), with the row: the swap works. The opening sits where 1997 has it, right of the middle of
  the front slope, the fires of #166 burn round it, and it reads as a hole into a dark room with charred rafters across
  it, not as a panel. **Fault:** its edge was a staircase of blocks (thirty strips 18 cm wide with level tops).
- Round 3 (14:29, `gore4/ds01d`), the mesh in this change: the edge is now 84 bundles of straw with a wandering outline.
  At the game's camera (top right: Dink south-east of the house, `dink.View -135 -14`) and at play distance the opening
  is a ragged dark hole in a burning roof; close up the black straw at its edge, the rafters, the laths and the dark of
  the room show. From straight above the bundles' square ends can still be told.

## Below the bar, known

- No glow inside: 1997's picture 154 has orange glowing laths. The kit's materials have no emissive; all light comes from
  the fire effects, so the inside is black by day.
- The opening is a notch that widens up to the bared ridge pole; 1997's is a rounder hole below the ridge.
- Close up and from above the ragged edge is made of bundles with square ends, not torn straw; the scorch on the thatch
  round the opening is faint in the game's sun.
- The room below is plain charred surfaces.
- The fires, the burn marks 155-157 and any char under the roof fires belong to the effect stream (#214); a fire card that
  stands over the opening hangs in the air above it (roof numbers for that stream: Master log 23 Nov 11:05).

## Tests

Headless, 23 November 2026, in one private copy = master `e37f11e42` + the three gore changes together (this one, #216 and #224),
each as its one commit: every tracked source, data and kit package file of the tested tree equals the copy (0 differ), the
packages are the committed ones and every other package of the two kits equals master's.

- Binaries: clean build (`Intermediate` removed) of master `6e3d4f991` + these trees, 0 warnings; `e37f11e42` changes no
  C++ against that (0 files), and the C++ of the tested tree equals the built one (0 files differ).
- Kit imports, headless (`-nullrhi`): Corpses `DINK TOWN IMPORT OK: 26 materials, 15 modules, 0 warnings`,
  Structures/Stonebrook `DINK TOWN IMPORT OK: 9 materials, 15 modules, 0 warnings`.
- `Scripts/test.sh Dink.Art`: 81/81 passed. `Scripts/test.sh Dink.Gore`: 11/11 passed.
- `Scripts/test.sh Dink.Gameplay.Probe`: 29/29 passed; all twenty chapter md5s equal the table of
  `Plugins/DinkParity/Docs/packaged_probe.md` on master (Ch1 cff64df9d1 .. Ch20 b27010b31e).
- `python3 -m unittest discover -s Scripts/tests`: 1051 tests OK (in the copy).
- `scrub_private_paths.py --check` clean, `check_public_paths.py` 0 flagged, `verify_sources.py --metadata-only` passed.
- Kernel log: 0 Oops in all rendered and headless runs of the day.
- `burning_cottage.jpg` is the earlier sheet: master in the game, the rejected first mesh in the game (17 Nov), Blender renders.

## Not checked

The world was not regenerated for this run (the copy's generated world dates from master `9ada93f1a`; the equal probe
traces show it plays as master's). The full `Dink` suite. Windows, Shipping, a packaged build.
