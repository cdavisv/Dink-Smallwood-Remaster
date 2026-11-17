# Murkwood Deep (DinkExpanded pack 3), 16 November 2026

Owner decision 15 (16 Nov 2026): the pack is approved as drafted (lines of `doc/remaster/EXPANDED_CONTENT.md` section 6,
the names Old Burt, the Murk boar, The Thin Place, the entry at the west treeline of the 1997 Murkwood clearing, the unused
map slots). The switch stays OFF by default.

## Frames (`murkwood_greybox_frames.jpg`, rendered game with `-DinkExpanded=1`, 1280x720 offscreen, looked at)
Rows, left to right: SCR_301 (1997 clearing, the west treeline, two 1997 pillbugs of its locked fight) | 332 The Thin
Place at the play camera; 332 from above | 331 Burt's Camp (Old Burt as a grey placeholder cylinder); 331 from above (the
camp block and Burt) | 267 The Boar's Wallow at the play camera | 267 from above (the boar as a red placeholder sphere) |
300 Seal Stones at the play camera.
- What it looks like: a greybox slice, as built: flat green ground, brown slab walls on the pack's edges and solids,
  placeholder shapes for Burt and the boar. Art is FABLE_ART_QUEUE rows EX-01..EX-04.
- Wrong / not seen: on 300 the camera stands inside a large wooden mesh (the seal-stone placement drawn by a 1997 family
  binding at full size); the walk through the join was not captured: on SCR_301 the pillbugs' 1997 locked fight
  (`screenlock`) holds Dink and closes the join, as every exit is closed (the route is walked by the PIE test
  `Dink.Expanded.Murkwood.Play` instead).

## Tests (private copy synced to master c878e29e + this commit, built, world imported)
- Switch OFF: `Dink.Narrative+Dink.Expanded+Dink.Gameplay.Probe` 65/65; the twenty probe md5s equal `packaged_probe.md`.
- Switch ON (`DINK_EXPANDED=1`): the same filter 65/65, including `Dink.Expanded.Murkwood.Play` (in by the join, The Thin
  Place's base script, across the pack edge into Burt's Camp, out to the 1997 return point), `.Quest` (Old Burt, the boar,
  the leg, the reward through the merged story and the 1997 director), `.SaveLoadsWithPacksOff` and `Dink.Expanded.Save`
  (a save inside a pack loads at the join's 1997 return point).
- `tools/expanded/probe_parity.py`: PROBE PARITY OK, 20 chapters, ON equals OFF.
- Text: the 30 lines in `Plugins/DinkExpanded/Content/Data/lines.csv` (what the game loads) equal the section 6 table
  word for word (script check); their status is now "approved by the owner 16 Nov 2026".
