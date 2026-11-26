# Physical play layer: Dink's collision and touches follow the drawn 3D shapes (design 15 Nov 2026, split 17 Nov 2026)

Coordinator decision on bug A70 (15 Nov 2026, COMMON_RULES; owner confirmed 16 Nov 2026): the 1997 hardboxes, hit boxes and touch boxes are layout-scaled
pixels, about three times the real-size photoreal meshes (`DinkRemasterUE/Docs/Verification/PhysicalMapping_15Nov2026/`), and the
enlarged map (`WORLD_SCALE.md`, feat/world-scale) makes the gap larger. In PLAY, what Dink himself touches follows what is drawn;
the 1997 simulation keeps its boxes for everything else and for parity.

Split (coordinator decision on PR #160, 17 Nov 2026): the layer has PARTS (Collision, Touch, Bodies, Hits, CreatureReach).
OWNER DECISION 19 Nov 2026 (option (c) of `doc/remaster/COMBAT_REACH_OPTIONS.md`): drawn contact for BOTH sides, so all five
parts are ON in play (21 Nov 2026). With the layer off (the probe, the parity tests) every hit decision is the 1997 code path.

## Scope
| who | 1997 boxes (unchanged) | drawn 3D shapes (this layer, play only) |
|---|---|---|
| Dink walking | tile hardness, warps, scripted / pushable sprites, boxes that close a passage | unscripted placements whose drawn mesh has a player blocker (PR #129): Dink walks up to the mesh |
| Dink's attack (sword, fist, range) | layer or part Hits off | part Hits (on): the weapon reach touches the target's drawn body |
| creature blows at Dink | layer or part CreatureReach off | part CreatureReach (on): its drawn reach meets Dink's capsule; it starts the blow there |
| missiles at Dink | layer or part CreatureReach off | part CreatureReach (on): the missile meets Dink's capsule, grown by its `sp_range` (22 Nov 2026) |
| touches on Dink (pickups, touch damage) | when the layer or part Touch is off | part Touch: Dink's body touches the drawn item or body |
| creature bodies against Dink | when the layer or part Bodies is off | part Bodies (A21): a player-only box in each living creature |
| NPCs, creatures, missiles at anyone but Dink, brains, hardness maps, scripts | always | never |
| `get_hard` (missiles, brains, pushes) | layer or part Collision off; every box but a relaxed one, every tile but an open one | part Collision: a relaxed box only inside its drawn footprint, an open tile's painted boulder nowhere (`PlayHardness`) |

Only WHEN a hit or touch lands changes. What it does is the 1997 path unchanged: `RunThroughTagList` / `RunThroughTouchDamageList`
(dink.cpp:15460-15527, 15629-15651) run the same damage formula, the same `rand()` draws in the same order, the same `hit` /
`touch` procedures and the same deaths. The layer only answers "does this target count" differently.

## Switch
`dink.PhysicalPlay` (console variable) with the settings file `Content/Dink/Data/Play/physical_play.ini`, in the style of
`Content/Dink/Data/AI/adaptation.ini` and `dink.NpcHumanPace`:
- 0 off (the 1997 boxes for Dink too), 1 auto (default: on in a game that renders and is not an automation test), 2 on.
- Auto is OFF in every automation test and in the probe, so `Dink.Gameplay.Probe` and the parity tests run the original rules and
  the twenty md5s of `packaged_probe.md` stay equal with the layer off. The layer's own tests switch it to 2 for their scope.
- Parts, each a key of the ini and a console variable `dink.PhysicalPlay.<Part>` (-1 the ini, 0 off, 1 on), all inert while
  the layer is off: `Collision=1` (relaxed hardboxes, section 1), `Touch=1` (section 3, also talk and push at drawn geometry),
  `Bodies=1` (section 4), `Hits=1` and `CreatureReach=1` (section 2, owner decision 19 Nov 2026). Test: `Dink.PhysicalPlay.Parts`.
- A target whose 1997 box still stops Dink (solid and not relaxed: a chest, a scripted rock, a sign) keeps the 1997 hit and touch
  rule even with its part on: Dink cannot reach its smaller drawn body.
- The file holds the numbers: `RelaxCoverBelow` (a box is relaxed when its drawn mesh covers less of it than this, default 0.7),
  `ReachScale` (default 1: the 3D reach of a range is `AttackReachCm x range / 28`, `AttackReachCm` 85 cm from `authored.ini`, i.e.
  the 1997 fist range 28 px and sword range 40 px at the drawn scale of Dink: 85 cm and 121 cm in front of his capsule),
  `TouchReachCm` (pickups, default the authored `PickupReachCm` 30), `ContactReachCm` (touch damage, default 5).

## 1. Dink's collision (walking)
- Today the player capsule blocks on `DinkHardSolid` (the importer's per-screen trimesh: ground quad plus a 3 m prism per rectangle
  of solid pixels, tile and sprite hardness together; `DinkGreyboxHardness.cpp` rebuilds it when a script redraws hardness), on
  `DinkHardLow`, and on PR #129's player-only blockers (`DinkPlayerBlock`, drawn mesh hulls).
- With the layer on, the player capsule ignores `DinkHardSolid` and instead blocks on a per-screen PLAYER solid mesh on the
  player-only channel: the same construction (`MergeRects` + prisms + the ground quad) from the screen's current solid mask
  minus the pixels stamped by RELAXED placements (code 100 + n). NPC and creature sweeps (A7), traces and the simulation keep the
  normal mesh. When a script redraws hardness (`ApplyScreenSolidChanges`), the player mesh is rebuilt from the same changes.
- AS BUILT (differs from the design above): the relaxed pixels are dropped from the screen's `DinkHardSolid` mesh itself
  (`SyncGreyboxHardness` on screen entry), not from a separate player mesh. The 3D sweeps of NPC and creature bodies
  (`AuthoredActorMoveBlocked`) therefore no longer see a relaxed box either; their moves are still decided by the 1997 pixel
  hardness, which is unchanged, so they walk as in 1997. Sight traces of touches no longer meet the relaxed box: they also test
  the player-only blockers (the drawn hull), so nothing is collected through a tree or a rock (Codex review of PR #160).
- RELAXED placements are listed per screen in `Content/Dink/Data/Play/relaxed_hardboxes.json`, made offline by
  `Scripts/make_relaxed_hardboxes.py` from a `dink.PhysAudit` run and the 1997 hardness. A placement is relaxed only if all hold:
  unscripted (scripts move, kill and redraw their sprites), not a warp (`prop`) and not a hardness-only placement; drawn by a
  family mesh that carries a player blocker (so something drawn still stops Dink); its drawn footprint covers less than
  `RelaxCoverBelow` of its hardbox; and relaxing it opens no passage: on the 1997 hardness at 3 px, the walkable region that
  touches the box after relaxing (box pixels minus the mesh hull, plus the blocker hulls) must not join two regions that are
  separate in 1997. Boxes that fail the passage test stay (the drawn thing is smaller than a corridor-closing box): they are
  listed in the file with the reason and get a Fable row (PM-xx) to draw them to the box.
- Warps, pushes, touches and sprite brains do not read the player mesh, so nothing in the 1997 rules moves; Dink's sprite point can
  now stand inside a relaxed box, where 1997 never put it. The only 1997 rule that reads Dink's own pixel against sprite hardness
  is the push test (`BlockingHardnessAhead`, push procedures): relaxed boxes belong to unscripted placements, which have no push.

- First list (from the dink.PhysAudit run of PR #155's world): 456 boxes relaxed on 234 screens, 66 kept for the passage
  test (Fable row PM-07). Walls are left out until their placement rule is settled (`PhysicalMapping_15Nov2026/FIX.md`). Screens
  whose collision is the original-hardness projection (`RequiresOriginalHardnessScreen`, 38 screens) are not relaxed: that path
  does not go through `SyncGreyboxHardness`.

- REVIEW FIX (21 Nov 2026, review of PR #160 finding 2): dropping a relaxed box from Dink's collision only left the 1997 hardness
  the simulation reads (`get_hard`: missiles, brains, the push test) holding the whole box, so Dink stood inside a box enemies and
  his own fireball could not enter (a safe pocket; the fireball spawned 30 px ahead died at once). Now, with part Collision on,
  `UDinkGameplay::PlayHardness` keeps a relaxed box in `get_hard` only inside its drawn footprint (`feet` of
  `relaxed_hardboxes.json` schema 2: the dink.PhysAudit body-height slice of its mesh, map pixels). Test: `Dink.PhysicalPlay.Switch`
  (PlayHardness) and `Dink.PhysicalPlay.RealScreens` (get_hard at the pine S215_P05: 0 in the box, 105 at the trunk; 105 off).
- OPEN TILES (21 Nov 2026, playtest 20 Nov P1): the grass_rocky tiles' painted boulders keep a 1997 hardness outline (mostly low,
  code 2) where the remaster draws open ground (an invisible wall at SCR_408 (208,239), a closed invisible ring on SCR_409).
  `open_tiles` of `relaxed_hardboxes.json` lists the tile cells (row * 12 + col) freed in play: for Dink (the screen's low
  collision is rebuilt without them, `UDinkGreyboxSubsystem::ApplyScreenLowChanges`; on original-hardness projection screens the
  tile base of every source load drops them, `LoadPlayHardnessSource`) and for `get_hard`. A tile is freed unless it joins two
  walkable regions that the 1997 map does not already join on foot (through neighbouring screens); enclosed pockets (the inside of
  a boulder's outline) with no scripted placement do not count. 1420 tiles on 250 screens freed, 67 kept (`kept_tiles`).
  Test: `Dink.PhysicalPlay.Blockages`.

- SEALED GAPS (26 Nov 2026, world scale follow-up): `Content/Dink/Data/Play/sealed_gaps.json` lists rectangles of 1997 walkable ground
  (map pixels, inclusive) inside a hardness outline that Dink's capsule could not enter at the reference scale and fits at the enlarged
  one (fewer pixels per 28 cm). With part Collision on they join the screen's low collision (`SyncGreyboxLowHardness`, Dink's capsule only;
  `get_hard`, brains and missiles keep 0 there). Only closed pockets no walk of the 1997 map reaches are listed (reviewed findings of
  `Scripts/check_capsule_gaps.py`). First row: the one-row slit of SCR_189/190 (WORLD_SCALE.md 14.1); then the 36 closed pockets the
  check finds (33 screens). The check exits 1 when a closed pocket it could seal is not in the list. Test: `Dink.PhysicalPlay.SealedGaps`
  (every sealed screen, layer on: no free capsule cell inside a sealed rect).

## 2. Dink's attack
- `UDinkGameplay::RunThroughTagList` already has a 3D branch (`UsesAuthoredGeometry` / `AuthoredGeometryMatches`, Hit): a
  capsule of half width `AttackHalfWidthCm x range / 28` swept from the front of Dink's body to the reach above, against the
  target's drawn geometry, with a sight check through walls. It is used today only for authored art and hardness-fit barrels.
- ON in play since the owner's decision of 19 Nov 2026 (part `Hits`; the creatures' side is part `CreatureReach`). With part Hits on and Dink (sprite 1) attacking, every target with drawn geometry takes the 3D branch: placeholder cards, family
  meshes, authored humanoids, and creature bodies. Creature bodies are skeletal (`UDinkCreatureComponent`): the test uses the
  body's physics bodies when it has them, else its oriented local bounds. Targets with nothing drawn (hidden sprites, text) keep
  the 1997 box. Everything after the match is the existing 1997 code.
- Part `CreatureReach` (on in play since 19 Nov 2026): a creature's blow at Dink starts at the front of its own drawn body, in its 1997 facing,
  against Dink's capsule. Without it, and with Hits on, a Bonca out-reached Dink's fist by metres.
- Part CreatureReach as built (21 Nov 2026, review of PR #160 finding 5 and its switch-on list): `UDinkGameplay::CreatureReachMatches`.
  A creature's blow lands when Dink's CAPSULE (never a held item's mesh) meets the region in front of its drawn body
  (`CreatureDrawnBody`: the union of its authored body boxes, else its skinned body's own box): from its back to its front face
  plus `AttackReachCm x max(range, 28) / 28` along its 1997 facing, as wide as the body plus `AttackHalfWidthCm` each side. The
  depth is the body's support along the facing (a Bonca turned sideways no longer swings 80 cm past its front), Dink overlapping
  the body counts, and a wide body reaches across its whole front. Sight runs from the body's centre (raised off the ground), and
  stops at solid hardness and the drawn hulls, not at other creatures.
- Approach (review: creatures stopped at their 1997 `sp_distance`, 50-60 px, metres in the drawn world, and swung at air): with
  part CreatureReach a creature targeting Dink starts its blow (`pill_brain`) and stops closing in (`process_target`) when its
  drawn reach meets him (`CreatureReachesDink`). Layer off: the 1997 distances.
- The rule "a target whose 1997 box still stops Dink keeps the 1997 hit and touch" now holds only for still targets (brain 0): a
  creature's 1997 box moves with it and stops no one (the cave Bonca, hard 0, bit Dink by its 1997 touch box).
- Missiles at Dink (22 Nov 2026, drawn contact for both): with part CreatureReach on, `missile_brain`'s overlap test for Dink
  (`UDinkGameplay::MissileHitsTarget`) is his capsule against the missile's point, grown by its `sp_range` in cm, not his 1997 box
  (28 x 18 px plus the range: about twice the drawn Dink, so a fireball passing beside him on screen still burnt him). Without a
  capsule or the screen's corners, and with the layer or the part off, the 1997 box. Test `Dink.PhysicalPlay.MissileAtDrawnDink`.
  Missiles at anyone else, and Dink's bow arrows, keep the 1997 boxes (arrows fly as sprites). The Joppa dragons' `harm` is no
  missile: en-drag.c `attack` calls `hurt(&kcrap, 20)` on its target wherever it stands (no range, no box, the same in 1997).
- With both parts off (the default), Bodies on: a creature's body box stops Dink at its drawn front, and from there the 1997 fist
  box must still reach it (`Dink.PhysicalPlay.RealScreens` checks this on the SCR_438 pillbug).

## 3. Touches on Dink
- `RunThroughTouchDamageList` likewise: with the layer on, a sprite with `touch_damage` counts when Dink's capsule, grown by
  `TouchReachCm` for pickups (`touch_damage -1`) or `ContactReachCm` for touch damage, touches its drawn geometry (the existing
  Touch branch, elevated pickups included). A class-bound script creature, drawn only by its skinned body (its markers hidden),
  counts by that body (Codex review of PR #160). The notouch timer, the order and the procedures are unchanged.

## 4. Creature bodies (bug A21, owner decision 16 Nov 2026)
- With the layer on, every living creature body (an actor tagged `DinkCreature` whose sprite is active, has a brain and is drawn)
  carries a player-only blocker (`UDinkGameplay::UpdateCreatureBodyBlockers`, every gameplay tick): a box of profile
  `DinkPlayerBlock` in the drawn body's own frame (it turns with the body), the body's bounds less 3 cm a side and at least
  1.2 m tall, not a step (`CanCharacterStepUpOn` no). Dink cannot stand on or inside a pillbug, and he stays within the
  layer's touch reach of it (`ContactReachCm` 5), so walking up to a biting creature still gets him bitten.
- Only the player capsule meets it: the creature's moves, its 1997 touch and hit boxes, missiles and the simulation are
  unchanged, so a creature still reaches and bites Dink.
- Never a trap: while Dink is inside a body (it walked into him) that body's blocker is off until he is clear of it.
- Which creatures (21 Nov 2026, review finding 1): the placement rows of creatures.json (tag `DinkCreature`) AND every class-bound
  creature (`UDinkCreatureClassComponent`: placed and script-made foes, ducks, pigs), not people (brain 16) and not a creature that
  is `nohit` (a still cut-scene body must not seal a doorway). A placement row whose authored body boxes (Pawn profile) already
  stop Dink at its drawn body gets no second box (review finding 4: the larger skinned box kept Dink out of its touch). The box
  follows its body's bounds only when they change by more than 4 cm (finding 8: no physics shape rebuilt every tick).
- A dead creature (brain 0, its corpse), a hidden one, and every creature when the layer is off carry none: the probe (layer
  off under automation) never sees one and its routes do not change.
- Test: `Dink.PhysicalPlay.CreatureBodyBlocksDink`.

## Tests (as built)
- `Dink.PhysicalPlay.Switch`: auto is off under automation, 2 forces on, 0 off; the relaxed list parses and the game's list loads.
- `Dink.PhysicalPlay.Parts`: the ini's defaults (all five parts on; the code's defaults match), each console variable
  turns its part on or off, a part is inert with the layer off, and with Touch off the 1997 box collects food again.
- `Dink.PhysicalPlay.HitAtDrawnContact` (fixture world): a drawn prop 4 m away whose 1997 box holds Dink is hit with the layer off
  and with the layer on and part Hits off (the default), and not with Hits on; moved to the reach it is hit on, and the 1997 `hit` procedure runs; facing away does not hit; with no drawn
  attacker the 1997 box decides.
- `Dink.PhysicalPlay.TouchAtDrawnContact` (fixture world): food drawn 4 m away is not collected through its 1997 box with the layer
  on, is collected at drawn contact (the 1997 `touch` procedure: life 5 -> 8), and is collected through the box with the layer off.
- `Dink.PhysicalPlay.CreatureBodyBlocksDink` (fixture world): no blocker with the layer off; on, a pillbug-sized body stops a
  swept capsule at its drawn front, lets go of Dink when it walked into him, blocks again when he is clear, and is removed for
  brain 0, when part Bodies is off and when the layer goes off.
- `Dink.PhysicalPlay.RealScreens` (PIE on the generated world): the relaxed pine S215_P05 stops Dink with the layer off and not
  with it on; the SCR_438 pillbug's own box is pillbug-sized, part Hits lands the fist at drawn contact and not from 1.5 m; with
  the default parts its body box stops Dink and his blow from there is the 1997 box test and lands.
- `Dink.Gameplay.Probe` with the layer forced on (`Mode=2`, default parts incl. Hits and CreatureReach, class art on headless:
  `dink.CreatureClassArt=2`): the layer-aware bot (steps to the drawn body for a pickup or a blow, waits outside a foe's drawn
  reach, strikes between its swings): table in `DinkRemasterUE/Docs/Verification/PhysicalPlay_21Nov2026/README.md`.
- `Dink.PhysicalPlay.Blockages` (PIE, layer on): P1 (SCR_408 open ground, SCR_408 -> 409 out of the old ring), P2 (the feed sack
  from the south), A66 (talk to the mother from in front of her).
- `Dink.Gameplay.Probe` with the layer off (default under automation): the twenty md5s equal `packaged_probe.md`.
- Rendered (offscreen game, `DinkRemasterUE/Docs/Verification/PhysicalPlay_19Nov2026/`): pine S215_P05 off/on, gold heart S524_P04
  short of and at the drawn heart, pillbug punches on SCR_438.
- Not written yet: a python test of the passage check in `Scripts/make_relaxed_hardboxes.py`.

## For the world-scale stream
The layer reads distances in the drawn world (cm), so a larger layout scale does not widen hits or touches; the relaxed-box list is
per placement and pixel-based, so it survives a re-layout (regenerate it after the world is re-exported only if hardness or
bindings change). A wider spacing makes 1997 boxes bigger in cm: more boxes pass `RelaxCoverBelow`, and the passage test is in
pixels, so it does not change.

## Review of 22 Nov 2026 (head 0b71c27b2) and what changed
- Finding 1 (pickups unreachable): `UDinkGameplay::PickupUnreachableInPlay`. A pickup (`touch_damage -1`) that no capsule spot can
  reach (16 directions, against its drawn body and half its pickup reach off, each spot free of blocking geometry with nothing solid
  between it and the pickup) is collected by its 1997 touch box, as without the layer. `Dink.PhysicalPlay.Blockages` walks at
  `bpotion` S166_P23 and `gheart` S157_P09 and must collect both.
- Finding 2 (landforms): the A21 body box carries `DinkLandforms::FlatTag` and is built in the flat frame (the drawn body's lift taken
  off); `CreatureReachMatches` takes the drawn body down to the flat floor for its height test and its sight line.
- Finding 3 (sight): a creature's blow at Dink needs the same sight line as Dink's blow at it (his capsule's centre to the closest point
  of its drawn body). Where that line is blocked, `process_target` stops the creature at its 1997 `sp_distance`.
- Finding 4 (entry cost): each entry logs `DINK PHYSICAL PLAY ENTRY: screen N collision X ms` (headless, the 16 screens with the
  most relaxed boxes: 34-81 ms, worst SCR_503 81 ms, SCR_632 75 ms). Not cached yet; a rendered figure is still to be taken.
- Finding 5 (stale data): at every entry `CheckRelaxedBlockers` keeps the 1997 box of a relaxed placement with no player-only hull
  over its drawn footprint (logged `S632_P02 keeps its 1997 box`). `RealScreens` checks this on the 16 screens with most relaxed boxes.
- Finding 6: stronger tests (P1 must pass on SCR_408 itself; the SCR_278 bite through the touch list; the creature held by brains off,
  not `sp_freeze`).
- Finding 7: no body box on a frozen creature, nor on a harmless one (no touch damage, no attack, not targeting Dink: ducks, pigs).
- Nits: code defaults equal the ini (all parts on); stale "off by default" comments fixed; the A66 talk fallback needs part Touch,
  Dink's screen and no wall; the body-box "inside" test is a circle against the box; an original-hardness screen relaxes nothing.
- Missiles at Dink: see section 2 (`MissileHitsTarget`).
- Review of the delta (23 Nov 2026): A) the 1997 fallback for an unreachable drawn target never applies through a wall: something
  solid (Visibility) or a drawn hull between Dink's capsule and the target's drawn point refuses it (a mesh or hull whose bounds hold
  that point, the potion in its decoration, does not count; low hardness ignores Visibility, so a ditch does not either). Test
  `Dink.PhysicalPlay.NoFallbackThroughWalls`. B) `FDinkDrawnBody::LiftCm` is the lift of the component the body came from (0 for
  flat-held authored body boxes); `CreatureReachMatches` lowers the body by it, not by the actor's lift. Not testable headless: the
  landforms are off under automation (`-DinkLandforms=1` only).

## Invisible-blockage rows (23 Nov 2026, A71, A92, A94, A20, P8)
- A71, walls (`relaxed_hardboxes.json` "trimmed", schema 2 extended): interior and dungeon wall modules (`SM_Wall_Plaster_*`,
  `SM_Wall_Dungeon_*`, family meshes, unscripted, no warp) are drawn on one thin strip of their thick 1997 wall box: often its
  room-side face, but door jambs, corner posts, partitions and the dungeon walls stand inside it (Dink stopped up to 2.2 m short;
  dungeon walls of 713 5 m). Such a wall has no player-only hull (PR #129 leaves walls out); instead, with part Collision on, Dink's
  solid collision keeps its box only inside the drawn strip, run on along the wall to the box's ends so the wall line stays closed
  (`SyncGreyboxHardness`, `IsTrimmedForPlayer`), and `get_hard` keeps the same strip (`PlayHardness`, its `feet`). Passage rule: on the
  1997 hardness at 3 px less the export's water and void fills (nobody walks the void round a room), every 4-connected piece of the
  freed box cells touches at most one walkable region (a partition's two rooms stay two). The strip is measured again at each entry on
  the wall mesh as the world stands (`MeasureWallStrip`: the module whose plan overlaps the box most, its extent across the wall; the
  15 Nov audit's slices are 5-115 cm off today's modules); a wall with no module across its box keeps the box. The passage rule holds
  for a strip anywhere across the box, since it always runs the box's whole length. 248 walls on 37 screens; 11 kept for the passage rule.
  Original-hardness projection screens (34, 161, 162, 194, 196 among them) keep their wall boxes, as every relaxed box there.
- A92, audit tiles: the tiles the dink.PhysAudit summary lists as an invisible LOW wall (`phys_mismatches.csv`, nothing drawn on at
  least 90 % of the contact edge) open like the grass_rocky tiles, but only when every piece of hard tile pixels reaching into the tile
  is a blob of at most 60 px (a painted rock), and with no shortcut rule (only the pocket inside a blob's own outline is excused).
  Lines (fences, hedges, ledges, banks) and solid tiles stay for the art row PM-05: they may route the player. 96 more open tiles.
- A94: nothing to change in play: the export's natural shorelines (AGENTS.md, 15 Nov 2026) already end the drawn water where Dink
  stops (player-only water bands) or draw it back to the 1997 line; measured on every water screen (evidence folder) and walked in
  `Dink.PhysicalPlay.BlockageRows`.
- A20 (both modes, not part of the layer): `UDinkGreyboxSubsystem::GotoScreen` places a teleport whose spot has no floor at all (nothing
  the player capsule meets from 1.5 m above the screen's level to 20 m below, and not inside anything: SCR_471's authored pond) on the
  nearest pixel of that screen with a floor and room for the capsule. Every spot with a floor, a wall or a prism is placed as before.
- P8 / A354: part Bodies also gives a still, class-bound body that is solid in 1997 (brain 0, `sp_hard` 0) its drawn-body box when its
  class is listed in `physical_play.ini` `StillBodies` (today `king_on_throne`, the seated King of the ending: his 1997 box is smaller
  than the drawn King and throne). Not every still body: a cut-scene body elsewhere must not stand in Dink's way.
- Test `Dink.PhysicalPlay.BlockageRows` (PIE, real world): A20, A71 (four walls, layer off and on), A92 (two rocks), A94 (four shores),
  P8, and measurements for A93 (walk mask against the 1997 hardness), A62 and A61 (camera). Python: `Scripts/tests/test_make_relaxed_hardboxes.py`.
