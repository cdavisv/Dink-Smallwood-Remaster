# GP-Q7, part 1: the knight's pool in the red of picture 275, as blood (23 November 2026)

Follow-up of PR #198, where the knight's pool was judged darker than its 1997 picture. One corpse-kit asset: the pool
sheet of `SM_Corpse_Knight_PR` (`Corpses/tools/build_gore.py`, `knight()`); body, shaft and halberd head are unchanged.
No data row, no code. **Seen in the running game on 23 November 2026** (sheet `knight_275_ingame.jpg`).

## The blood look (`Corpses/tools/gore_sheets.py`, `blood_sheet(look='fresh', **FRESH_1997)`)

The first version of this change gave the pool one bright red (thin 196 / body 162 / deep 108, sRGB). In the game it
was the red of the picture, but flat: a poster red with a cut-out outline that read as spilled paint (review of the
frames of 17 and 23 November). What is in this change:

- thickness drives colour, roughness and height together: a thin film at every edge keeps the bright 1997 red, the body
  of the pool is darker, the thick middle deep crimson with clots; every thrown drop has a bright rim and a darker,
  domed, wet core; mist is a stain;
- the outline is bent by a few centimetres and frayed, so no straight side or rounded square of a 1997 pixel is left in
  the red that is laid down from picture 275;
- the numbers are set by the running game, not by a render: in the sun of screen 157 a pool body at sRGB 162, 132 and
  100 was drawn as the same clipped red each time (rounds 1 to 3), so the set is thin 128 / body 80 / deep 38, a little
  above the hit-blood sheets that read as blood in the same frames;
- the pool is never smaller than before: 2.02 m2 against 0.40 m2 of red in the picture (2.60 m across with its drops).

The same look is used by the placed blood splats (PR #224 carries the identical `gore_sheets.py`), so pools and splats match.
`DINK_POOL_ONLY=1` rebuilds the pool sheet alone (same body, same card, no bake; 20 s).

## What I saw (`knight_275_ingame.jpg`; 1997 picture at the left of each row)

Copy of master `6e3d4f991` + this change (with #215 and #224), clean build, corpse kit imported headless,
`Scripts/PhotorealQA/run_capture.sh` at 960x540 on screen 157, four rounds on 23 November (frames `fableB/q7c`,
`gore4/q7d`, `gore4/q7e`, `gore4/q7f` of the capture copy).

- Rows 1 and 2, the pool in this change (round 4): at the play camera it is the bright red pool of picture 275 under and
  round the knight, with its drops thrown round it. At the mid and close cameras it has depth: bright at the thin
  edges, darker in the body, deep crimson with clots where it is thick beside the harness; small wet glints in the sun
  and the dark mirror of the halberd in it. Its outline is irregular; none of the rounded squares that the enlarged
  1997 pixels left in the first sheets.
- Row 3, how it got there, close camera: round 1 = one bright red (flat, the fault named in review); rounds 2 and 3 =
  the new look with body 132 and 100, still clipped to one red by the sun; round 4 = body 80.

`knight_275.jpg` is the earlier sheet: master's dark pool (16 Nov) and the first bright version in the game (17 Nov).

## Below the bar, known

- Still a very saturated red in full sun (as 275 is); in the body's shadow it is dark crimson.
- Smooth armour close up; the halberd head is bloodied red where 1997 has blue steel.
- `Corpse_Knight/render_beauty.png` and `render_close.png` (Blender) still show the first bright pool: only the pool sheet was
  rebuilt, the asset was not rendered again.
- The pool is an alpha-tested card: its outline is a cut edge, frayed but not soaking into the dirt.
- The dragon remains (`S158_P07`, picture 216) are NOT in this PR. Their redder rebuild (v3) was seen in the game on
  23 November and rejected: with the hide soaked red no dragon is left to see. Its LODs, authored in the FBX, import
  cleanly (local branch).

## Tests

Headless, 23 November 2026, in one private copy = master `e37f11e42` + the three gore changes together (this one, #215 and #224),
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
- This change commits only the three pool texture packages of the knight; mesh, materials and body textures are master's
  (#198's), and the 81/81 above is with every other corpse package as on master.

## Not checked

The world was not regenerated for this run (the copy's generated world dates from master `9ada93f1a`; the equal probe
traces show it plays as master's). The full `Dink` suite. Windows, Shipping, a packaged build.
