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
| north-south | 4 | bound: 3D rails along the 1997 line, standing on the ground, joined to the east-west and diagonal runs. Residual (A211, code): a run is as long as its card is tall (13.4 m against about 7.4-8.9 m of ground), so it reaches 2-3 m past a corner (441: S441_P06 crosses both north-east runs; small T-ends on 408, 409, 469) and where stacked pieces drift in x two parallel rails show for a few metres (409). |
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
- `Scripts/art_coverage.py` (coverage.csv of the shared checkout): final 5,124 -> 5,161, placeholder 1,331 -> 1,294
  (+37: north-south 17, north-west 14, north-east 6). Unchanged: 407 and 439 (screens dressed by the Stonebrook manifest).
- `Scripts/test.sh Dink.Art+Dink.Import+Dink.Gameplay.Probe`: 119/119 (private copy: master 6ef7a590 build + overlay to PR #155's head
  f5c222bf + these rows; the north-east rows were at 35 degrees in that run, presentation only).
- Probe trace md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (all twenty).

## Not checked
The packaged build; vision 1 placements (S409_P09 is vision-gated and was not counted); screens 375 (two north-south pieces, bound, not looked at)
and 663; the close-up look of the east-west fence's overlapping runs with the photoreal posts (seen once on 409: crossed posts where two runs overlap,
as the 1997 pieces overlap); the render-only vista's old fence (A207, not this change). The `fence_rail_ew` row's note still says the other
angles stay unbound (only its `mesh` was to change here).
