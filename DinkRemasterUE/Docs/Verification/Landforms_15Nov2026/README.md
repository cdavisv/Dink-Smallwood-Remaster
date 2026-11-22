# Landforms, 15 Nov 2026: real height under the flat ground sheets (first batch, draft)

Owner direction of 15 Nov 2026: "real shape to the landscape". This pass gives the world height. It is code and data only: `Scripts/export_landforms.py` and `UDinkLandformsSubsystem`; the design is in `DinkRemasterUE/AGENTS.md`.

## Sheets
All sheets are play-camera or oblique views from `Scripts/PhotorealQA/landforms_script.py`. Each pairs the flat ground (`-DinkLandforms=0`) with landforms on, using the world-wide data v1 in a private copy at 97b5a385 / ae175fbb plus this branch.

| Sheet | What I see |
|---|---|
| `heightfield_overview_world.png` | Hillshade of the exported heightfield (v1). Blue is below 0, pink is high. |
| `cliff_before_after.jpg` | 526: smooth grassy hills and mounds rise where the 1997 rock is unreachable. Near the play camera the ground stays low. |
| `river_before_after.jpg` | 463 and 462: the river reads glassier; the banks are subtle. |
| `coast_before_after_v1.jpg` | 640: **worse in v1**. The bed fell away at the shore, so the shallow turquoise was lost and the water is dark right to the edge. Data v2 adds a 2 m shelf at -4 cm; v2 has not been captured yet. |
| `forest_before_after.jpg` | 281 and 366: little change. The trees stand on gently raised canopy ground. |
| `town_edge_before_after.jpg` | 432 and 434: the town edge stays flat and the well stands on the ground. |
| `border_walk_before_after.jpg` | 462 to 463 across a screen border: no step at the border. On 463 Dink still stands on the water surface at x 20, because that drawn water is not on a "water" tile class there (open). |
| `fords_after_v1_0.40m.jpg` | 635 and 465: Dink wades. It was too deep at 0.40 m (hip-deep on 635); v2 uses 0.25 m and has not been captured. |

## Numbers
- Offline checks (v2, world-wide):
  - Walkable slope: p99 5.1 deg, max 25 deg.
  - Walkable heights: -0.25 m (fords) to 0.64 m.
  - Play-camera sight rays blocked: 0 of 6.77 M.
  - Shared-edge steps: 0 mm.
- `dink.LandformsAudit` (v1, world-wide): 0 of 2656 placement actors off the ground. 251 of 1171 decor instances report no lift (open).
- Frame cost (fps lines, editor game, offscreen 1280x720, same views):
  - Before: 38.9 to 83 fps.
  - After: comparable (ford views 87 to 93 fps).
  - No controlled measurement was made.

## 16 Nov 2026 (after both reboots): rebased on master bd6d227a, the three open problems

Sheet `after_v2_16nov.jpg` (committed 32-screen data v2, landforms on, looked at), rows left to right: ford 635 at the
play camera and close (Dink shin-deep, 0.25 m) | ford 465 (shin-deep beside the house; the pond is an opaque olive green:
water material, not this change) and coast 640 (the shallow turquoise shelf is back) | coast 608 and cliff 526 (now taken
on 526: the earlier "cliff" frames were the 608 overview, the script left the overview camera on) | 526 back view (a
grassy rise behind the field) and the walk north into the river on 463 (stops on the bank) | 463 from above and the
walk east from the cliff screen.

1. **Decor "lift 0" (251, then 205 rows)**: the rows were family-art meshes (`FamilyArt_Decor_*`) that the family layer
   makes when a screen is first dressed (`UDinkArtFamilySubsystem::ApplyScreen`), after the landforms had set everything
   else on the ground at BeginPlay, at the flat ground. Fix: `UDinkLandformsSubsystem::SnapScreenDecor`, called at the end
   of `ApplyScreen`, lifts every instanced mesh and player-only blocker of that screen not lifted yet (refactored out of
   `SnapPlacedActors` as `LiftScreenDecor`). Audit with the committed data: 129 placement actors, 0 off; 1 decor instance,
   0 off. With the world-wide data v2 (533 screens; 667, 699, 671, 149 visited so the family layer dressed them): **2656 placement actors, 0 off; 1195 decor instances, 0 off** (was 205 off).
2. **Walk on water on 463**: not a walk. The capture teleported Dink to map (40, 300) on 463, which is inside the river's
   1997 water fill (`fill_water` 0-600 x 161-308), so he stood on the fill's top; the same happens on the flat master. A
   real walk north from the bank (63, 345) stops at map y 329 (the low hardness of the bank, 324-326) with the ground 3.8 cm
   under him: he cannot reach the water. The capture now places its border shots on land.
3. **Probe with landforms ON**: now testable: `Scripts/test.sh` takes `DINK_TEST_EXTRA_ARGS="-DinkLandforms=1"` (only
   `-Name` / `-Name=value` words). Results:
   - committed data (32 screens): `Dink.Gameplay.Probe` 29/29, all twenty md5s equal the table (landforms active: the log
     shows the 32 screens and 111 placement actors set on the ground). But the probe crosses only 2 of the 32 screens
     (248, 524), so this proves little.
   - world-wide data v2 (533 screens, not committed): 29/29 passed, but Ch2-Ch20 md5s DIFFER (Ch1 equal). First
     divergence, Ch2 on SCR_238 (the cult scene): the script's `move_stop 1 4 470 1` of Dink ends 8 frames earlier
     (`StepMove` moves the sprite in map pixels from where Dink stands; on relief the bot's Dink had stood elsewhere,
     because his own footing is the physical ground). So with landforms on, the probe's Dink walks differently; the 1997
     simulation (hardness, NPCs, creatures, missiles) is not touched, but the player's position is. Parity runs therefore
     keep landforms OFF (as decided for the player-only collision of A21: play mode only). Turning them on for the probe
     needs a decision (accept a re-baselined "landforms" probe, or make Dink's footing 2D-exact on relief).
- Suites with landforms off in automation: `Dink.Movement+Dink.Art+Dink.Import+Dink.Gameplay` 213/213 (the first run
  crashed in the engine's garbage collector, mimalloc / Teds RemoveRow, during a family-art test's world teardown; the
  retry passed), all twenty md5s equal the table (#141's re-baseline).
- Not done: water-shapes integration (once #150 lands, the banks should slope to 0 at the drawn waterline from
  `shore_distance_cm`, not at the 1997 outline, or the land covers the 10-25 px band of drawn water); batch 2 (world data).

## 16 Nov 2026, evening (stream terrain-2): a VISUAL layer, footing exact

Coordinator decision of 16 Nov 2026: landforms are a visual height layer; the simulation (2D position, hardness, scripted
moves, timing, every collision result) must be identical with them on and off. What changed:

- The ground mesh has **no collision** at all. The player's capsule keeps walking on the importer's flat floor against the
  unchanged 1997 collision, so his XY is the flat world's bit for bit; only his drawn body (mesh) and the camera boom rise
  by the height under the capsule (`ADinkGreyboxCharacter`, player pawn only). The ford floor lowering, the pawn lift in
  `Tick` and the height added to GotoScreen / warps / the probe's Goto are gone.
- Other actors are drawn on the ground (placements at BeginPlay, script sprites in `SyncActorToSprite` / `SpawnSpriteActor`),
  but their invisible collision (shape components, hidden meshes, player-only blockers, warp boxes) is held at the flat
  height (`DinkLandforms::KeepCollisionFlat`); script warp triggers are not lifted; the greybox screens' player-only blockers
  are not lifted. Queries between a flat body and a lifted visible target (`AuthoredGeometryMatches`,
  `FittedMissileMatches`) are made in the target's frame.
- Structure sets and town houses (#184: cottages, castle walls, fences, bridges, wells) are drawn at the height under each
  module; the exporter levels every building footprint (+1.2 m) at its mean height, bridge decks over water at 0.
- Banks and beds follow the drawn waterline of #150 (ground mask alpha = signed distance from it), not the 1997 outline.
- Data: world-wide (533 screens) instead of the 32-screen test region.

Why it is exact: the only thing the simulation reads back from the 3D world is the player pawn's XY
(`UDinkGameplay::SyncDinkFromActor` -> `UDinkDirector::SyncSpriteFromActor`), plus warp overlaps and the authored-geometry
queries. The capsule's movement inputs (its collision world, its Z, the frame step) are now the flat world's; warp boxes
and blockers did not move; the authored queries are translated rigidly. The first divergence of the previous draft
(Ch2, SCR_238, `move_stop 1 4 470 1` ending 8 frames early) came from the capsule standing on the relief mesh.

### Results (19 Nov 2026, master f4743990 + this commit, private copy built clean, world regenerated with --export)
- **Probe with landforms ON and the world-wide data** (`DINK_TEST_EXTRA_ARGS="-DinkLandforms=1"`, 533 screens, 1773
  placement actors and 692 decor instances lifted): `Dink.Gameplay.Probe` 29/29, **all twenty md5s equal the table** of
  `packaged_probe.md` (Ch1 cc2e12fb5c ... Ch20 be28390b9d). Run twice: on 5ccf38dd (16 Nov 23:50) and on f4743990 (19 Nov 10:16).
  This is the proof that the layer is visual only.
- `Dink.Movement.Landforms.Data` and `.VisualOnly` pass. `.ScriptedMoveAcrossRelief`: the editor's PIE step is not
  bit-deterministic (two FLAT runs of the same walk from the same start differ by float noise in every frame), so the
  test compares the hill run with the flat run against the flat runs' own spread, and requires the capsule's height to
  equal the flat floor's on every frame; the first version demanded bit equality and failed on that noise (rewritten test: `Dink.Movement.Landforms` 3/3 on the final head).
- OFF suites: `Dink.Movement+Dink.Art+Dink.Import+Dink.Gameplay` 216/217 with all twenty md5s equal the table; the one failure was the first version of `ScriptedMoveAcrossRelief` (bit equality between PIE runs), rewritten; `Dink.Movement.Landforms` 3/3 on the final head.
- Data: `export_landforms.py` on the regenerated bundle reproduces the committed `landforms.json`/`.png` byte for byte.
  Checks: walkable heights -0.245 .. 0.638 m, 48 walkable cells steeper than 20 deg (bridge/ford edges on 693, 727, 759
  and older cells), play-camera sight rays blocked 0 of 6.77 M, seams 0 mm.
- `dink.LandformsAudit` (capture): 2656 placement actors on 533 screens, 0 off the ground by more than 2 cm; 1204 decor
  instances, 0 off; 211 collision primitives held flat; 0 visible colliding geometry lifted.
- Unit tests: `test_landforms_export.py` 8/8.

### Sheets of 19 Nov (left: landforms off, right: on; play camera twice, then from above)
| Sheet | What I see |
|---|---|
| `sheet_ford_635_coast_640.jpg` | 635: Dink wades shin-deep (his capsule is on the floor, his drawn body below the surface); banks slope into the ford and a low rise stands behind it. 640: the bank meets the drawn waterline; the shallow shelf is there, the water a little deeper turquoise; a wider sand bank shows. No floating objects. The drawn water outline itself still has stepped corners (#150's shape, not this change). |
| `sheet_cottage_274_hillcottage_318.jpg` | 274: cottage, door, fence and tree on the ground; the door's threshold slab shows a few cm above the grass on the right (the footprint pad is levelled at its mean). 318: fences and the cottage stand on the ground; the path and grass follow the rise. |
| `sheet_castle_399_castle_367.jpg` | Walls and tower stand on the ground; on 367 the bottom course of the wall shows a little more (ground lower there). No gaps under the walls seen. |

Look first: `sheet_ford_635_coast_640.jpg`, then the cottage sheet.


## Not verified
- Placed fire (#166, screen 439) and people (#168/#199) on raised ground: 439 and the towns are settlement screens and stay flat; not captured on a relief screen. Moving NPCs' play-only body blockers (A21) ride with the drawn body (play mode only).
- Border seams at screen edges in the new frames (data seams are 0 mm).
- The probe and the suites on the final commit.
- Landforms-on parity: the probe hung with landforms on, so landforms are now OFF in automation and parity runs (see the PR).
- The v2 data in game.
- Screen 438 (authored ford).
