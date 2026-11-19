# Physical play layer: Dink's collision and touches follow the drawn 3D shapes (design 15 Nov 2026, split 17 Nov 2026)

Coordinator decision on bug A70 (15 Nov 2026, COMMON_RULES; owner confirmed 16 Nov 2026): the 1997 hardboxes, hit boxes and touch boxes are layout-scaled
pixels, about three times the real-size photoreal meshes (`DinkRemasterUE/Docs/Verification/PhysicalMapping_15Nov2026/`), and the
enlarged map (`WORLD_SCALE.md`, feat/world-scale) makes the gap larger. In PLAY, what Dink himself touches follows what is drawn;
the 1997 simulation keeps its boxes for everything else and for parity.

Split (coordinator decision on PR #160, 17 Nov 2026): with hits at drawn contact for both sides (Dink's blows and the creatures'
blows at him) the layer-aware probe bot lost the fights of chapters 1, 8, 12 and 17: contact brawls are a combat-balance change
the owner has not confirmed. So the layer has PARTS. Collision, Touch and Bodies are on in play; Hits and CreatureReach are in the
code and tested but OFF by default, and with them off every hit decision is the 1997 code path. The choice of hit rule is laid out
for the owner in `doc/remaster/COMBAT_REACH_OPTIONS.md`.

## Scope
| who | 1997 boxes (unchanged) | drawn 3D shapes (this layer, play only) |
|---|---|---|
| Dink walking | tile hardness, warps, scripted / pushable sprites, boxes that close a passage | unscripted placements whose drawn mesh has a player blocker (PR #129): Dink walks up to the mesh |
| Dink's attack (sword, fist, range) | by default (part Hits off) | part Hits on: the weapon reach touches the target's drawn body |
| creature blows at Dink | by default (part CreatureReach off) | part CreatureReach on: the reach starts at the front of its drawn body |
| touches on Dink (pickups, touch damage) | when the layer or part Touch is off | part Touch: Dink's body touches the drawn item or body |
| creature bodies against Dink | when the layer or part Bodies is off | part Bodies (A21): a player-only box in each living creature |
| NPCs, creatures, missiles, brains, hardness maps, scripts, `get_hard` | always | never |

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
  `Bodies=1` (section 4), `Hits=0` and `CreatureReach=0` (section 2). Test: `Dink.PhysicalPlay.Parts`.
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

## 2. Dink's attack
- `UDinkGameplay::RunThroughTagList` already has a 3D branch (`UsesAuthoredGeometry` / `AuthoredGeometryMatches`, Hit): a
  capsule of half width `AttackHalfWidthCm x range / 28` swept from the front of Dink's body to the reach above, against the
  target's drawn geometry, with a sight check through walls. It is used today only for authored art and hardness-fit barrels.
- OFF BY DEFAULT (part `Hits`; the creatures' side is part `CreatureReach`). With part Hits on and Dink (sprite 1) attacking, every target with drawn geometry takes the 3D branch: placeholder cards, family
  meshes, authored humanoids, and creature bodies. Creature bodies are skeletal (`UDinkCreatureComponent`): the test uses the
  body's physics bodies when it has them, else its oriented local bounds. Targets with nothing drawn (hidden sprites, text) keep
  the 1997 box. Everything after the match is the existing 1997 code.
- Part `CreatureReach` (off by default): a creature's blow at Dink starts at the front of its own drawn body, in its 1997 facing,
  against Dink's capsule. Without it, and with Hits on, a Bonca out-reached Dink's fist by metres.
- Missiles and Dink's bow arrows keep the 1997 boxes (missiles are simulation; arrows fly as sprites).
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
- A dead creature (brain 0, its corpse), a hidden one, and every creature when the layer is off carry none: the probe (layer
  off under automation) never sees one and its routes do not change.
- Test: `Dink.PhysicalPlay.CreatureBodyBlocksDink`.

## Tests (as built)
- `Dink.PhysicalPlay.Switch`: auto is off under automation, 2 forces on, 0 off; the relaxed list parses and the game's list loads.
- `Dink.PhysicalPlay.Parts`: the ini's defaults (Collision, Touch, Bodies on; Hits, CreatureReach off), each console variable
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
- `Dink.Gameplay.Probe` with the layer forced on (`Mode=2`, default parts): the layer-aware bot (it steps to the drawn item for a
  pickup when its 1997 touch box holds Dink but the drawn item is out of reach) completes all twenty chapters; table in
  `DinkRemasterUE/Docs/Verification/PhysicalPlay_19Nov2026/README.md`.
- `Dink.Gameplay.Probe` with the layer off (default under automation): the twenty md5s equal `packaged_probe.md`.
- Rendered (offscreen game, `DinkRemasterUE/Docs/Verification/PhysicalPlay_19Nov2026/`): pine S215_P05 off/on, gold heart S524_P04
  short of and at the drawn heart, pillbug punches on SCR_438.
- Not written yet: a python test of the passage check in `Scripts/make_relaxed_hardboxes.py`.

## For the world-scale stream
The layer reads distances in the drawn world (cm), so a larger layout scale does not widen hits or touches; the relaxed-box list is
per placement and pixel-based, so it survives a re-layout (regenerate it after the world is re-exported only if hardness or
bindings change). A wider spacing makes 1997 boxes bigger in cm: more boxes pass `RelaxCoverBelow`, and the passage test is in
pixels, so it does not change.
