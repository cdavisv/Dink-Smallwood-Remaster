# Physical mapping audit: is what the player sees what physically happens? (15 Nov 2026)

The owner's order of 15 Nov: "make sure that the physical aspects of the game are mapped to the actual objects". The simulation
is the 1997 engine's (hardness in map pixels, the sprite hardbox of the picture a sprite shows, hit and touch tests against that
box: `source/dink/dink.cpp` run_through_tag_list 15460-15527, run_through_touch_damage_list 15629-15651, ported in
`UDinkGameplay`), presented in 3D. This audit puts the drawn 3D world back into map pixels and compares, on all 644 screens.
Audit only: nothing in this PR changes the game. Fixes follow in a second PR (branch `fix/physical-mapping`).

## How it was measured
- `dink.PhysAudit <first> <last> <out dir> [quit]` (new, `DinkNarrative/Private/DinkPhysicalAudit.cpp`) visits each screen
  (teleport to a free pixel, art applied) and writes, per placement and per live sprite: the 1997 hardbox (the live sprite's
  current picture, else the placement's), the pixels it stamps into the screen's hardness now, the footprint of the meshes that
  draw that origin (their triangles sliced at body height, 15-120 cm above the ground, trunks 15-60 cm, foliage materials left
  out, holes filled; skeletal bodies by their bounds; family instances matched to their origin by the decor card they replace),
  the overlap of the two, whether the sprite's feet are inside another origin's drawn body, warp trigger boxes against the drawn
  door, and a 3 px mask of where anything is drawn within the 40 cm tolerance. `Dink.PhysAudit.Compare` tests the mask maths.
- `Scripts/summarise_phys_audit.py` classifies and ranks (`--walk-mask` adds the terrain and screen-edge checks from a
  `dink.WalkAudit` walk mask; `--repo` points at a checkout with `tools/dinkex/out`, the 1997 hardness, owner and tile data).
  Invisible walls are measured on the contact edge only: stamp pixels next to walkable 1997 ground, i.e. where Dink actually
  stops; the inside of a thick hardbox is never reached. Its unit tests check the reach arithmetic against the dink.cpp numbers.
- `Scripts/phys_audit_shots.py` / `phys_audit_sheet.py` make the rendered spot-check script (Dink put south of the subject: `_0`;
  walked towards its middle for 4 s: `_1`; the hardness prisms shown with `dink.GreyboxBlockers 1`: `_2`) and the contact sheets.
  The script actually run is `capture_script_before.txt` (paths replaced by `<shots>`; its last part is the push of S277_P03).
- Run: private project copy, master 7cd12fe4 + PR #129 (walk-through blockers) + this audit, world regenerated, offscreen editor
  game (`-game -RenderOffscreen`), 644 screens in 8 minutes. The walk mask is the one of PR #129's own audit (`after8`, same
  collision). 11 screens are not judged (nothing drawn, or the whole map hard): 145, 298, 402, 404, 416, 418, 468, 721-724.

## Results (`phys_summary.md`, ranked lists `phys_mismatches_top.csv`: the first 100 of each category)
| category | checked | OK | mismatched | notes |
|---|---|---|---|---|
| 1 invisible walls, sprite hardboxes (contact edge) | 2,457 | 686 | 1,771 | 1,545 meshes that do not reach their hardbox edge, 115 card only, 96 nothing of their own drawn, 15 hardness-only placements (invisible in 1997 too) |
| 1 invisible walls, tile hardness (per 50 px tile) | 14,381 | 11,207 | 3,174 | OK: drawn by the terrain (cliff, rock, water, wall, canopy) or on a shore / cliff edge. Mismatched: low (2) or solid tile hardness on open grass, sand, snow, stone floors with nothing drawn |
| 2 hardbox vs mesh (blocking placements drawn by a mesh) | 1,973 | 183 | 1,790 | footprint / hardbox linear scale median 0.35 (p10 0.19, p90 0.75); centre offset median 56 cm, p90 151 cm |
| 3 creatures / NPCs, 1997 hit box vs body (Dink with a sword, sp_range 40) | 518 | 0 | 160 | 306 are cards (the 1997 picture: same mapping as 1997), 9 authored humanoids use 3D hit geometry (`AuthoredGeometryMatches`), 43 no body or box; pillbugs: the hit registers median 326 cm short of the body |
| 4 pickups, touch box vs mesh | 106 | 0 | 65 | 26 cards, 1 authored (3D touch); gold heart S524_P04 picked up 199 cm from the mesh, gold piles of SCR_352 185 cm |
| 4 warps, trigger vs drawn door | 110 | 63 | 47 | most of the 47 are dungeon-floor exits (seq 87) with nothing drawn at the opening |
| 4 screen edges (1997 crossable cells blocked for the capsule) | 921 crossable | 572 | 349 | |
| 5 pushables / destructibles | 3,947 live sprites | 3,947 | 0 | every live sprite's actor stands within 20 cm of its sprite point, so a script that moves a sprite moves its mesh; rendered push of S277_P03: see below |
| 6 terrain tiles (walk mask vs drawn class) | 61,824 | | 1,352 + 28 | 1,352 open tiles walkable in 1997 (largest region) but blocked with nothing drawn; 28 water tiles walkable where 1997 blocks; 214 water/lava tiles walkable as in 1997 (hardness 0 there) |
| 7 live sprites standing inside another drawn body | 993 | 962 | 31 | |

## The main finding: 1997 boxes at layout scale, photoreal meshes at real size
The 1997 hardboxes, hit boxes and touch boxes are pixels scaled by the region's layout scale (settlements x4, wilderness x2.75,
dungeons x2.25, interiors x1.75 of 0.025 m: 4.4-10 cm per pixel), while the photoreal meshes are bound at their real size
(`families.json` fit "none", by design). The hardbox of a barrel is 3.0 x 1.7 m around a 1 m barrel, a pine's 7.9 x 3.1 m around a
2.5 m wide trunk-and-branch slice, a large bush's 10 x 3 m around a 3 m bush, a crate's 5.7 x 2.2 m around a 1.2 m crate, a
signpost's 2.4 x 1.8 m around a 20 cm post. So, with 1997 rules unchanged:
- Dink stops 1-3 m short of most props and trees (category 1 and 2);
- a sword hit on a pillbug registers when the sword is about 3 m short of the body (category 3; every sword sets sp_range 40, item-sw1/2/3.c:42, which grows the 1997 hit box to 45 px in front of the target: 3-4.5 m at 6.9-10 cm per pixel);
- pickups are collected from up to 2 m away (category 4).
Transforms cannot close this without props several times their real size. It is an owner decision (options in the PR text):
fit the visual to the box (bigger props, or clusters drawn to the box: Fable art, queued as PM rows), or a remaster rule
(3D hit/touch against the drawn body as humanoids already have), which changes gameplay and the probe.

## Fixable by placement (fix PR)
The meshes are also not centred on their hardbox: they stand at the card's ground point, the middle of the 1997 picture, while
the hardbox lies where the picture's trunk, base or wall face is. Median offsets: pines 147 cm (west of the trunk box), oaks 170,
dead trees 154-160, signposts 83-92, the grey and red boulders 124-129, crates 50, interior walls 50 (and drawn in the middle of
a 2.1 m thick 1997 wall top, so Dink stops about 1 m short of a plaster wall in every house). Fences (17 m box, one 4 m module)
and the horizontal forest-edge strips (18 m box, one 7 m strip) are drawn once instead of along their box.

## Rendered spot checks (looked at, one by one)
Offscreen editor game, play camera. Each row: Dink put on a free 1997 pixel south of the subject | after walking towards the
middle of its hardbox for 4 s | the same with the hardness prisms shown (`dink.GreyboxBlockers 1`: tan solid, blue low).
Captions in `sheet_captions.csv`. The play camera is low; the fix PR adds overhead views of the same spots.
Defects in these sheets, marked in their captions: 701 column 3 is blank (the camera inside a prism); the 352 row's first column
is a stale frame of 524 (taken before the teleport was drawn); in the 193 and 034 rows columns 1 and 2 are equal (Dink was already
against the box and did not move); the pillbug row has no box (live sprites have no hardness prism; its hit box is not drawn).
- `before_invisible_walls.jpg`: the save machine S588_P05 and the Kernsin fountain S586_P03 stop Dink metres short of the drawn
  mesh (prism beside him, mesh further on); in the houses of 193 and 34 the wall and furniture prisms cover open floor in front of
  the drawn walls; on 250 a solid tile line runs across open sand; on 211 low tile lines (blue) cross open grass.
- `before_water_shores.jpg`: the clearest mapping defect. On 470, 746, 671, 382 and 701 Dink stands in drawn water (pond or sea)
  and the 1997 low hardness that edges the water lies further on, on the drawn dry bank or beach: he wades where water is drawn
  and is stopped by an invisible low wall on dry sand. The audit's tile check counts low hardness next to water tiles as drawn
  (2,914 tiles "next to water"): these captures show that count is not proof; the drawn water's outline does not follow the
  1997 water edge (bug A94).
- `before_props.jpg`: the fence S441_P03 is one 4 m module while its box runs on along the line; the grey boulder S536_P34 stands
  beside its box; pines (214), the barrel field (734) and the pine over the gold heart (524) show boxes far from the drawn trunk
  or barrel; a low tile line crosses the meadow of 352.
- `before_other.jpg`: the dungeon exit S227_P01 has nothing drawn at the exit and still warps (walking south lands Dink on 710);
  the lava floor of 85 is walkable as in 1997 (hardness 0 there); the snow isle (151) has its solid line at the drawn edge;
  the pillbug S488_P11 (a live sprite, no prism) is drawn several times smaller than its 1997 box; the forest-edge strip 251.
- Not usable: SCR_748 (the teleport was refused: the capture shows the previous screen); S253_P06 is the teleport shrine:
  walking into it warps to 154, as it should.
- Push (category 5): every live sprite's actor is within 20 cm of its sprite point (3,947 sprites), so a script that moves a
  sprite moves its mesh. The rendered push of the rock S277_P03 is in the fix PR (the first attempt put Dink inside the rock's
  box and he fell through the hole behind it: a teleport artefact, not a walk).

## Not checked
- Vision variants other than the one a fresh game shows (the audit enters each screen at story start), states after scripts
  (burnt trees, opened chests, smashed barrels; not re-measured here).
- Missiles in flight (fireball and arrow paths) were not traced; they use the same hardboxes (category 3 numbers apply) and stop
  at hardness (category 1).
- The packaged build. The command is compiled out of shipping builds; in a cooked development build the meshes may lack the CPU vertex data the slice reads (the footprint would fall back to bounds boxes): not tested.
