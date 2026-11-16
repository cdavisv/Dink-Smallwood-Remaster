# Fence runs: north-south and diagonal split rails, photoreal east-west fence (A201, A206, A55, PQ-Q2)

15-16 Nov 2026, art-wiring-audit sub-agent. Data only (`Content/Dink/Data/Art/families.json`); no C++, no new art, no Blender.

## What changed
- New sequence-and-frame rows for sprite sequence 93 (`lands/fence/fence-`), all with `SM_Fence_SplitRail_4m_PR`
  (the photoreal split rail made for all four fence classes; bounds 4.44 x 0.39 x 1.41 m, pivot at the ground centre;
  its material is flagged for instanced meshes, and S441_P31 is a background, instanced placement) and `anchor` `hardbox`
  (PR #155: the run stands on the centre of the 1997 hardbox):
  - frame 4 `fence_rail_ns`: `yaw_offset` 90, `span` `height`;
  - frames 3 and 6 `fence_rail_diag_nw`: `yaw_offset` 26, `span` `width` (slope of the hardbox centres of the chains on 409, 437, 568);
  - frames 2 and 5 `fence_rail_diag_ne`: `yaw_offset` -22, `span` `width` (hardbox centres of the chains on 407, 441, 469).
    35 degrees (the step between the placements' ground points) was tried first: on 441 the pieces were staggered.
- A206: the `fence_rail_ew` row's `mesh` only, `StonebrookExterior/SM_Fence_SplitRail_4m_01` -> `Photoreal/Structures/SM_Fence_SplitRail_4m_PR`
  (family art never gets `environment.json` `mesh_swaps`). `span`/`anchor` on that row are PR #155's, unchanged.
- `Scripts/tests/test_photoreal_material_references.py`: the old kit fence leaves `ACTOR_ONLY_FAMILY_MESHES` (no row binds it).

## Outcome per angle (in-game fit)
| angle | frames | outcome |
|---|---|---|
| east-west | 1 | already bound (span + anchor, PR #155); now the photoreal fence (A206) |
| north-south | 4 | bound: 3D rails along the 1997 line, standing on the ground, joined to the east-west and diagonal runs. Residual (A211, code): a run is as long as its card is tall (13.4 m against about 7.4-8.9 m of ground), so it reaches 2-3 m past a corner (441: S441_P06 crosses both north-east runs; small T-ends on 408, 409, 469) The two parallel rails at the 409/441 border are the cross-screen copy S409_P08 + S441_P31 (A208), not this row. S375_P02/P03 are hidden (pig pen, below). |
| north-west diagonal | 3, 6 | bound: continuous chains on 409, 437, 568 that meet the east-west and north-south runs |
| north-east diagonal | 2, 5 | bound at 22 degrees: continuous on 441 and 469 |

PQ-Q2 (new art) keeps no angle.

## Sheets (left: before = master families.json, identical to PR #155's; right: after)
`scr408_before_after.jpg`, `scr409_before_after.jpg`, `scr437_before_after.jpg`, `scr441_before_after.jpg` (north-east at 22 degrees),
`scr469_before_after.jpg` (before: the visual sweep's frames of 15 Nov, other camera), `scr536_before_after.jpg`, `scr568_before_after.jpg`.
`play*` = play camera (400 cm, pitch -12) or a side view; `top*` = fixed camera 18-30 m above the fence (`dink.CalCam`).
Captures: `Scripts/PhotorealQA/run_capture.sh` (offscreen editor game, DISPLAY unset, not Xvfb :189), 1920x1080.
SCR_409's `play_diag` frame was dropped: that camera stands inside the cottage card (S409_P12, A55).

## Measured
- `Scripts/art_coverage.py` (coverage.csv of the shared checkout, families.json of master 3a7b4451 before / this branch after):
  final 5,240 -> 5,275, placeholder 1,215 -> 1,180 (+35: north-south 15, north-west 14, north-east 6). S375_P02 and S375_P03 stay
  placeholder: hidden (see below), not dressed.
- `Scripts/test.sh Dink.Art+Dink.Import+Dink.Gameplay.Probe`: 119/119 on 15 Nov (private copy: master 6ef7a590 build + overlay to PR #155's head
  f5c222bf + these rows; the north-east rows were at 35 degrees in that run, presentation only), re-run on 16 Nov with the pig pen hide: 119/119 (781 s, 1 with warnings), the twenty probe md5s again equal the baseline.
  f5c222bf's families.json differs from master's only in rows master added since (chests, corpses): no fence row, so the fence proof holds.
- Probe trace md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (all twenty).

## Screen 375's two pieces stood inside SCR_407's pig pen (review of PR #180)
S375_P02 (136, 601) and S375_P03 (473, 602) are north-south pieces below SCR_375's play area (1997 never draws them). SCR_375 lies directly
north of SCR_407 and the family layer dresses it as 407's neighbour, so with the frame-4 row both became 13.4 m split rails inside the pig
pen: the west one doubled PenWestUpper about 13 cm away and reached about 1.8 m into the west gate, the east one doubled PenEast. They are
now in `pigpen.json` `hide_origins` (also in `SourceAssets/Art/PigPen/pigpen_layout.json` and `generate_layout.py`): the card is hidden and
the family layer leaves the origin to the manifest (`hide_origins` matches origin ids world-wide: DinkArtSubsystem looks the id up among all
placement actors, FDinkFamilyPrecedence adds it to its origin set). `scr407_pen_before_after.jpg`: left with the rows but without the hide, right after.
Looked at (16 Nov, private copy, captures `cap_pen_pre.txt` / `cap_pen_post.txt`): without the hide the west pen fence is doubled by a
second split rail a few centimetres inside it, which runs on across the west gate opening, and the east fence is doubled the same
way; with the hide each side has its single rail and the west gate is open (`scr407_pen_before_after.jpg`: top view, the west
gate from outside at the play camera, the east side; `scr407_pen_edges_top.jpg`: the west and east edges of the top view, cropped).

## Not checked
The packaged build; vision 1 placements (S409_P09 is vision 1, never shown); SCR_663; S469_P10's rail, which runs 5-8 m onto screen 501
(the A208 cross-screen pattern, like the parallel rails of S409_P08 + S441_P31 at the 409/441 border); the close-up look of the east-west fence's overlapping runs with the photoreal posts (seen once on 409: crossed posts where two runs overlap,
as the 1997 pieces overlap); the render-only vista's old fence (A207, not this change).
