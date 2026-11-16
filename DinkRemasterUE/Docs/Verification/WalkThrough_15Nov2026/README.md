# Walk-through: Dink no longer walks into rocks, trunks and furniture (15 Nov 2026)

Bug list A18 (the owner's "you can walk through rocks and things like that"). Code stream, alpha QA. Private project copy,
editor game (offscreen Vulkan, `-game`), master 283cd155 plus this branch.

## Files
- `walk_in_before_after.jpg`: four rendered captures each side. Dink is teleported next to the thing (`dink.Goto` to a free
  pixel) and walked into it with `dink.WalkTo` (5 s of real movement input). Before: he stands inside the red boulder S244_P02,
  wholly inside an instanced boulder (only his hair shows), inside the trunk of the oak S274_P01 and inside a barrel. After:
  he stops at the rock and at the bark; the barrel S063_P06 is scripted and still walked into (residual).
- `confirm_walks_before.txt`, `confirm_walks_after.txt`: the `DINK WALK` lines of those runs (arrived = inside; timed out = stopped;
  in order: SCR_188 x2, 177, 181, 244 x2, 274, 026, 154, 073, 063, 122, then after only 439, the doors and the gold heart).
  SCR_188/177 are void artefacts (below); SCR_181 now arrives under the pine's limbs next to its trunk, which is the intent;
  SCR_073 (curved dungeon wall) and 063 (scripted barrel) are residual.
  After, also: walking from the street into the town doors next to the new wall blockers still warps (SCR_498 to 34,
  SCR_585 to 97, SCR_538 to 196), and the gold heart S524_P04 is still reached (its neighbour pine S524_P03 is in `skip_origins`).
- `audit_before.txt`, `audit_after.txt`: `dink.WalkAudit 1 768` summaries (`Scripts/summarise_walk_audit.py`): drawn meshes the capsule centre
  can stand 20 cm or more inside, by mesh. Before (master + the audit alone): 1,283 of 40,126 meshes on 558 screens. After: 109
  (of 39,891: relief rocks and forest trunks on open ground are no longer drawn), all in the residual list below.
- `connectivity_after.txt`: `Scripts/check_player_blockers.py` on the after audit: the seven flagged screens are town house
  interiors behind doors that are still reached from the street (walked into above on SCR_498, 585 and 538: the warp fires;
  SCR_497, 499 and 505 are the same house kit; the four door warps there that nobody had walked are walked below) and
  S539_P02 on SCR_539. S539_P02 is not a duck: it is brain 0, picture seq 33 frame 2 (`graphics\struct\outinn`, a piece of
  the outdoor inn) that carries `s4-duck.c`, whose `main` only sets its hitpoints; nothing there is a target to reach. (The
  duck pen is SCR_536.) The gold heart S524_P04 is
  no longer flagged (`skip_origins`).
- Trees: a tree's blocker is its trunk, a 12-sided prism of the narrowest cross-section between 20 and 140 cm (radius
  23-53 cm). A first table that took the whole body-height slice of pines (low limbs, 9-26 m2) stopped the probe on SCR_632
  (chapter 11) and moved chapters 4, 19 and 20; with trunks the probe's twenty traces equal the table.

## After review (15 Nov 2026, afternoon; master 0bf319c9 plus this branch, world regenerated)
- NPC and creature moves: `UDinkGameplay::AuthoredActorMoveBlocked` (its sweep and three overlap tests) and the probe's load
  ground trace now pass `DinkCollision::IgnorePlayerBlockers()`. Measured in `Dink.PlayerBlockers.BlocksOnlyThePlayer` (a real
  blocker in a throwaway world): without response params a Pawn sweep and overlap on simple collision do hit the blocker; on
  complex collision (what the NPC moves use) they did not, because the blocker has only convex geometry. So the NPC moves were
  not stopped by the blockers before either; the responses make that independent of the trace mode. A capsule with the
  player's responses is stopped at the blocker's face. Every other query in the project was checked: Visibility, Camera and
  projectile traces pass (the profile ignores them), object-type queries do not ask for the channel, component sweeps name
  their component, and the player's own head-clearance sweep keeps the blockers on purpose.
- The door warps the connectivity check flagged and nobody had walked, rendered (offscreen editor game, `dink.Goto` below the
  door, `dink.WalkTo` into it): S498_P11 warps to 35 and S499_P07 to 33 (two approaches each); S585_P14 warps to 225 when
  walked into the drawn door (from the right, at map x 516, Dink stops at the wall beside the door); SCR_497 in vision 0 runs
  the locked door S497_P13 (`s2-tdoor.c`: Dink is put back to y 140) and in vision 1 (`dink.Vision 497 1`) S497_P15 warps
  to 68 (two approaches). No blocker change was needed.
  Sheet: `doors_after_review.jpg` (where each walk arrives); every walk line: `confirm_walks_after_review.txt` (the PR's earlier
  confirmation walks were repeated in the same run and gave the same results: Dink stops at each boulder and trunk).
- `walk_mask.csv` now starts with a fresh header on each run (`screen,step,mask`), like the other outputs; the checker skips it.

## Residual (not fixed here)
- `SM_Wall_Dungeon_Curve` (up to 44 cm), forest-edge strips `SM_Veg_PineForestEdge_*` (the audit measures them as one trunk:
  up to 78 cm, really between the trunks of the strip), town `SM_Town_Wall_Door`
  (29 cm): a convex blocker would close the curve, the gaps between the trees or the doorway. Art requests (UCX pieces).
- Scripted barrels (8, up to 42 cm): the fitted barrel lifecycle (`DinkFamilyCollisionFit`) checks the barrel actor's
  components; left alone.
- Pickups (gold and red hearts) and the two teleport machines are walked onto by design.
- The relief rocks on the north strips of SCR_177/184/188 that a teleported Dink "walked into" stand in voids the importer
  closes with hardness prisms; no walking player gets there (a teleport lands inside the prism, whose inside the capsule does
  not touch). The audit now counts the inside of a prism as blocked.

## Not checked
- The packaged build (the blockers are runtime components: no asset changed).
- Every screen in a rendered game: the audit measured all of them, the rendered walks cover the cases named above.
