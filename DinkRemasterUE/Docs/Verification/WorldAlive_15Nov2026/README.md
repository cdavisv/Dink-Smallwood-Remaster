# World life: shared wind, walk-through bend, fire, missiles, breaks, dust (15-16 Nov 2026)

Stream world-alive (session of the motion/physics coordinator). Owner's order: "the whole world seems alive", physics
right everywhere. Presentation only: no hardness, sprite position, hit/touch box or script state changes; the layer is off
in a process that cannot render (tests, the probe).

## What runs

- `UDinkWorldLifeSubsystem` (DinkCore): one `AWindDirectionalSource` and `/Game/Dink/WorldLife/MPC_Dink_World`
  (`WindDir`, `WindGust`, `Push0..3`, `WorldLife`) written every frame; regional wind from
  `Content/Dink/Data/Environment/world_life.json` (20 regions, eased over 4 s, still indoors and on Low foliage, gust
  field travel integrated on the CPU); walk-through bend of grass, crops and bush tips (Dink and the three nearest moving
  creatures/people, lowest 1.5 m of a mesh, never bark); a CPU particle pool (two instanced-plane components,
  `M_WorldLife_Lit` / `M_WorldLife_Glow`, six custom floats per instance) and eight pooled point lights; footstep dust on
  bare ground (tinted by `ground_colour.json`), chimney smoke, pollen, fires of placements (world_life.json `fire`); the
  foliage shadow policy (wind-swayed vegetation left at Auto gets Rigid VSM invalidation).
- `UDinkWorldLifePresenter` (DinkNarrative, TG_PostUpdateWork, read only like the creature presenter): fire on burning
  sprites, fireball glow/trail/light (the grey marker hidden only while drawn), blasts 70/161/167/171 (never 164, the
  creature layer's blood burst), barrel staves and dust on the seq-173 break, dust and grit while pushing.
- Foliage: `M_Veg_Foliage` / `M_Veg_Bark` rebuilt with the shared node of `Scripts/world_life_wind.py`
  (`Scripts/import_world_life.sh`); `WorldLife` 0 (its asset default, `dink.World.Life 0`) is exactly the sway before
  this change.
- Console: `dink.World.Life`, `dink.World.Wind`, `dink.World.Particles`, `dink.World.StaticFoliageShadows`,
  `dink.World.Stats`, `dink.World.Demo <burst|bigburst|barrel|fire|bigfire|fireball|dust>` (review only).

## Audit (16 Nov, 04:10-04:29, offscreen Vulkan 1280x720, private copy on master 49627fc9 + this branch)

`Scripts/PhotorealQA/world_life_audit.py`: 50 screens of every region at the play camera and closer, three frames
~0.65 s apart, pass 0 = `dink.World.Life 0` (master's look), pass 1 = on. `world_life_motion.py` makes the motion maps
(`audit/motion_00..04.jpg`: frame, moving pixels in red, per pass; `motion.csv`). All frames were looked at.

What moves on master already: the vegetation sway (one direction, strength 1 everywhere), the sea surface, clouds,
creatures and Dink. What stood dead still or was wrong (bug rows A140-A148 of `doc/remaster/ALPHA_BUG_LIST.md`):
missiles and blasts as grey marker cylinders (A140), fires with no smoke/embers/light and torches as bare poles (A141),
barrel breaks, pushes and footsteps with no debris or dust (A142), one wind everywhere and no walk-through response
(A143), tree shadows re-rendered every frame (A144); not this stream's: Dink standing on the pond surface on 469 (A145),
439 near black (A146), the s1-roc rock as a pixel card (A147), the KernSin fountain a static card (A148).

## Measured

| what | layer off | layer on |
|---|---|---|
| fps, Terris town 466 (two windows of 6 s) | 81.0 / 80.5 | 80.6 / 81.3 |
| fps, Stonebrook pig pen 407 | 80.2 | 80.6 |
| ShadowDepths ms, 312 pine forest, Epic / High | 13.91 / 4.90 | 13.88 / 4.90 |
| ShadowDepths ms, 438, Epic / High | 2.58 / 1.70 | 2.23 / 1.56 |
| ShadowDepths ms, 650 coast, Epic / High | 2.22 / 1.09 | 1.33 / 0.72 |
| layer CPU tick (game thread), whole audit | - | mean 0.10 ms, max 2.5 ms (290 samples) |
| screen-change scan (whole-world actor walk) | - | median 1.1 ms, max 6.2 ms (139 scans) |

GPU numbers: `r.GPUCsvStatsEnabled 1` + `csvprofile` windows of 8 s, `Scripts/PhotorealQA/world_life_gpu.py`; 1280x720
offscreen, so absolute values are lower than perf-stutter's packaged 1440p; compare off/on only.

## Focused capture after tuning (16 Nov, 07:26, `world_life_audit.py --focus`, `focus/`)

The full audit showed the first values too weak or too white (glows saturating, fire smoke blown away at once, a 35 cd
torch light invisible by day, pollen glowing at night); they were retuned and this capture checks them. Frames looked at:

- Fireball (`focus/strip_F_demo_fireball.jpg`): a warm ball with an ember trail and a moving light pool, then the
  impact burst. Reads as a fireball at the play camera.
- Blast (`strip_F_demo_burst.jpg`): a warm flash and sparks, then dark-grey smoke drifting down the wind.
- Fire (`strip_F_demo_fire.jpg`): a flickering warm light pool and a smoke plume leaning down the wind; the flame
  glow itself sits in the 40 cm meadow grass and is barely visible (flame art: WA-04).
- Barrel: a REAL 1997 hit on 63 (bar-sh: fists armed, walk into it, `dink.Attack`): the hit and break cues play
  (sound 9, 37) and the presenter emits the break (16 staves + 5 dust, the emitted count +21 in the same frame
  window); the staves fall behind Dink at this camera (`strip_F_barrel63.jpg`; the demo `strip_F_demo_barrel.jpg`
  shows them clearly).
- Walk 408 west to east over a bare patch and meadow, layer off (`strip_F0_walk408.jpg`) and on (`F1`):
  `walk_compare.jpg` crops the same frames at full size. **Not visible**: footstep dust on that pale patch (puffs were
  emitted, about 2.5 a second, too faint against it) and the grass parting at Dink's feet (no difference a viewer would
  notice in these crops). Both need stronger values or a closer review; they are reported as unverified, not working.
- Rock 277: Dink leans on s1-roc from the south for 5.6 s (`strip_F_rock277.jpg`); the 1997 rock did not move in that
  time (s1-roc wants a longer push), so the sliding-rock dust was not exercised; the lean dust is not visible.
- Torches 763/764: found (8 fires, 7 lights on 763 in the log), but the capture point did not frame a torch.

## Second focus capture after the restart (16 Nov, 17:30, `focus16/`)

Private copy on master 84e045b0 + this branch, world regenerated with `--export`, vegetation parents rebuilt by
`Scripts/import_world_life.sh` and the camera-fade variants (`M_CameraFade_Veg*_v1`) regenerated from them
(`Scripts/import_camera_foliage_materials.sh`, after deleting the old variants, which were copies of the pre-wind parents).
Tuning before it: walk-through push eased (`f(2-f)` instead of `f^2`, 52 cm instead of 38) and wider (radius 120 cm / 85 cm
for creatures); footstep dust 3 puffs per stride, alpha 0.55, tinted a little darker and warmer than its ground.
Frames looked at:
- `rock_feet.jpg`, `rock277.jpg`: s1-roc on 277 pushed for real (strength 6, from the west, `dink.WalkTo`): the rock card moves
  east and the hole shows; a brown footstep puff is visible at Dink's back foot on the bare earth (frame 03). No extra dust at
  the foot of the sliding rock is visible. The rock is still the 1997 pixel card (A147, PQ-Q4).
- `close_walk.jpg`, `feet_crop.jpg`: the same walk on 408 at a near camera, layer off (left) and on (right). On the PALE patch
  of 408 the footstep puffs (about 2.7 a second, 15-20 alive, `DINK WORLD` lines) still do not read; the grass parting at
  Dink's feet is not visible in these frames either (he is on the bare patch in most of them).
- `torches.jpg`: the island torches of 763/764 framed from the south: a warm light pool at the pole and thin dark smoke at its
  top; no flame (art row WA-04). Hearth on 001 lit. Seen in passing, not this stream: Dink standing in the shallow water on
  764 (A145 family), pixel-card huts (art).
- `demos.jpg`: the review demos still draw (dust, burst, fireball with its light).
Tests on that copy: `Dink.World+Dink.Art.CameraFoliage+Dink.Gameplay.Probe` 39/39, the twenty probe md5s equal.

Soak after it (same copy, `world_life_audit.py --soak` 600 s, 39 laps over ten busy screens with burst, barrel,
fireball and fire demos every lap, offscreen 1280x720): about 604 s, at most 256 particles and 8 lights at once,
33,149 emitted, non-finite 0, layer tick mean 0.052 ms / p95 0.077 ms / max 1.0 ms; fps per lap min 55.8, median 83.2,
longest frame 40.7 ms. Actor count on screen arrival: 6,215 -> 6,383 during the first lap (first visits dress
neighbours), then 6,377-6,413 for the remaining 30 laps with no upward trend, so no leak; the report script's
first-vs-last rule says FAILED only because it compares a screen's first (undressed) visit.

## Fire of PR #166 (family effect rows) and this layer (16 Nov, 21:27, `fire166/`)

#166 draws the burning house itself (effect_placed rows for 427 and 155-157, embers, flicker lights) on SCR_001 and
SCR_439 vision 1. This layer now yields wherever a family effect row draws a sprite (`DinkWorldLife::IsFamilyEffect`: a
placeholder whose card carries `DinkFamilyArt`, or a script sprite with `ScriptEffectTag`): no world-life fire, smoke or
light there; it keeps fireballs, blasts, burning creatures and placed fires without a row (the hearth of SCR_001, class
`hearth_fire`, until a family row draws it). Capture on master 64b84d1a + this PR, `dink.World.Life 1` then `0`, same spots:
- SCR_001 vision 1 (`room_life1/0.jpg`): the frames match; world-life counts 1 fire (the hearth) and 0 lights of its own.
- SCR_439 vision 1 (`cottage_life1/0.jpg`): the frames match; world-life counts 0 fires and 0 lights.
So no doubled flames, smoke or lights. Tests on that tree: `Dink.World+Dink.Art+Dink.Gameplay.Probe` 107/107, the twenty
probe md5s equal the newest table of `packaged_probe.md` (#141 re-baseline).

## Not checked / still wrong

- Footstep dust: seen on darker bare earth (277), not on the pale patch of 408. Grass bend: written to the MPC, not seen to read on screen in any frame so far.
- Torch flames and fire flame cores: need flame art (WA-04); today smoke, embers and light only.
- Arrows and axes still draw the grey marker (WA-01).
- Birds, butterflies, fish rings: not built (WA-05 art first).
- Splashes and ripples in shallow water: not built (Dink never enters water in the 1997 rules; no water query the
  layer could use without touching the water stream's code).
- Sword-hit sparks: not built (no presentation hook for a sword hit landing on stone without touching DinkGameplay).
- The screen-change scan walks every actor (median 1.1 ms, max 6.2 ms); switch to perf-stutter's per-screen index
  once it is on master.
