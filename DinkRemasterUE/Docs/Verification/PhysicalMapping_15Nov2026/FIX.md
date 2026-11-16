# Physical mapping fix: family meshes stand on their 1997 hardbox (15 Nov 2026)

Follows the audit (`README.md` in this folder, PR #139, bug row "meshes not on their hardbox"). Presentation only: hardness,
hit boxes, touch boxes, scripts and warps are unchanged; the meshes move to where the 1997 engine already blocks.

## Change
- `families.json` "anchor": "hardbox" (new, `DinkCore/DinkFamilyAnchor.*`, hooks in `UDinkArtFamilySubsystem::DressActor` and
  `DressInstances`): the mesh stands on the centre of the placement's 1997 hardbox (frames.csv, relative to the sprite point
  recovered from the card: the card centre is `(width / 2 - origin x)` scaled picture pixels east of it) instead of on the
  card's ground point, the middle of the 1997 picture. Rows: pines, oaks, willows, dead trees, bushes, thorn bushes and coils,
  boulders, crates, grain sacks, furniture (beds, tables, cabinets, counters, bookcases), signposts, save machine, shrine,
  fountain, dungeon and snake pillars, golden duck, fallen log (41 rows). PR #129's player-only blockers follow the mesh, as
  they are made from its transform.
- "span": "width" on `fence_rail_ew` and `pine_forest_edge_strip`: the module repeats along the card instead of standing once in
  the middle of a 17-18 m box.
- Mode "hardbox_inner" (a thin wall module against the hardbox face towards the screen's middle) is in the code and its test but
  bound to no row: measured on the interior and dungeon walls it made things worse (the plaster walls' contact gap median went
  from 158 to 198 cm): the screen's middle is not the room side for every wall. A rule that probes the walkable side is the
  follow-up. Interior walls are unchanged.
- Test `Dink.Art.Family.Anchor` (parse, target pixel, inner face, frames.csv reader).

## Measured (dink.PhysAudit before / after, all 644 screens, same copy and world)
Category 2, blocking placements drawn by a mesh (1,973): OK 183 -> 306; centre offset median 56 -> 32 cm, p90 151 -> 118 cm
(after-run rows for the 41 anchored families, before-run rows for everything else, which did not change).
Per family, median offset of the mesh from its hardbox (cm) and hardbox cover:
| family | placements | offset | cover |
|---|---|---|---|
| tree_pine_large | 188 | 147 -> 26 | 0.15 -> 0.16 |
| tree_oak_large | 56 | 170 -> 113 | 0.34 -> 0.62 |
| tree_dead_frosted | 15 | 154 -> 35 | 0.11 -> 0.78 |
| thorn bushes (141) and grave thorn coils (80) | 221 | 54-61 -> 17-23 | 0.67 -> 0.82 |
| bushes (small, round large, wide) | 134 | 49-67 -> 10-14 | 0.24-0.28 -> 0.26-0.30 |
| boulder_grey_tall / boulder_red | 41 | 124-129 -> 6-7 | 0.14-0.21 -> 0.18-0.22 |
| crates (31), cabinets (18), counters (16), beds (13), tables (16), bookcases (9) | 103 | 33-94 -> 2-3 | up to 0.92 |
| signposts | 38 | 83-92 -> 10-11 | 0.16 -> 0.17 |
| fence_rail_ew (anchor + span) | 13 | 74 -> 7 | 0.11 -> 0.46 |
| pine_forest_edge_strip (anchor + span) | 13 | 25 -> 30 | 0.18 -> 0.30 |
Invisible-wall hardboxes flagged (contact edge) among trees 400 -> 379, bushes 165 -> 163, furniture 105 -> 93. The cover stays
low where the box is several times the real-size mesh (the layout-scale finding, owner decision): this fix removes the offset,
not the size difference.

## Rendered (looked at)
`after_anchor_fence_pine.jpg`: per row before walked in | after walked in | after from above with prisms | after from above.
The fence of 441 now runs along its whole box (the prism lies along the drawn rails); the pine of 214 and the bush of 211 are
shown from the play camera. The after-run's camera framing differs from the before-run (Dink's facing after the walk) and the
overhead view at 9 m is too close to show the props: these captures do not show the anchored props well; the numbers above
are the evidence. The push of the rock S277_P03 was tried again (Dink started west of the rock box) and did not happen: Dink did
not move (cause not found); category 5 rests on the measured actor positions (all 3,947 live sprite actors within 20 cm of
their sprite point).

## Not checked
The interior / dungeon wall rule (left unbound, see above); vision variants; the packaged build.
