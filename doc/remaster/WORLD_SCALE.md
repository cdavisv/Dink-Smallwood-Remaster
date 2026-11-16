# World scale: the original map larger (15 Nov 2026)

Owner's order (15 Nov 2026, 22:00): the original map must be larger than the original: everything expanded, slightly
farther apart; new content is added on top later (another stream). The coordinator chose the ratios. This document is the
design, the measurements behind it, what the change touches, and what is still open. Status: **prototype, draft PR**: the
offline pipeline is done and proven; the Unreal checks (import, tests, probe, walk audit, captures, frame cost) are listed
under "Verification" with what has and has not run.

## 1. The change

`tools/analyse/regions.toml` `[scale]` (linear multipliers on the base 0.025 m per 1997 pixel):

| kind | before | after | ratio | metres per pixel after | a screen (600 x 400 px) after |
|---|---|---|---|---|---|
| settlement | 4.0 | 4.6 | 1.150 | 0.115 | 69 x 46 m (was 60 x 40) |
| wilderness, sea | 2.75 | 3.6 | 1.309 | 0.090 | 54 x 36 m (was 41 x 28) |
| dungeon | 2.25 | 2.7 | 1.200 | 0.0675 | 41 x 27 m (was 34 x 23) |
| interior | 1.75 | 2.0 | 1.143 | 0.050 | 30 x 20 m (was 26 x 18) |

The layout is a rubber sheet (screens between kinds blend), so the per-screen ratio runs from 1.142 to 1.391 (median
1.258). The mainland grows from 1413 x 709 m to 1739 x 862 m; outdoor land from 0.61 to 0.92 km²; every settlement by about
15 % per side (Stonebrook 296 x 120 m -> 342 x 138 m, Windemere 351 x 120 m -> 407 x 138 m). The detached sheets keep their
1500 m gap (`min_gap_m` is absolute and stays). The Koka causeway (`[[stretch]]` y x 2) grows with its kind: SCR_727 is
62 x 54 m (was 52 x 41 m).

**The simulation is untouched.** Everything the 1997 engine and the probe read is in pixels and is byte-identical between
the two layouts (proven offline, `Scripts/world_scale_measure.py`, section 7): connectivity, warps, interiors, encounters,
vision variants and engine reach of the analyser; the export's collision rectangles (88,131), sprites, the 644 ground
images and 644 ground masks, and every placement's pixel fields (position, sequence, frame, type, hardness, script,
vision, brain, warp). Only metres change: screen corners, placement world positions and metres per pixel, card metres,
warp trigger quads.

## 2. Measurements (before the change, and what the change does to them)

Medians per object group and screen kind, from the two export bundles (`Scripts/world_scale_measure.py`) and what draws
each group in the game today (`Saved/Import/art_coverage.csv` of master 9cc796b6). Dink is 1.8 m (his mesh; his 1997
idle frames are 96 px). "Card" is the 1997 picture at its placement's scale, "box" the 1997 hardbox at that scale.

| group | drawn today by | real size of what is drawn | 1997 box, town / wild (m) before -> after | verdict |
|---|---|---|---|---|
| Dink, NPCs (humans) | hero mesh; NPC cards at the base 0.025 m/px (2.3 x 2.9 m picture, ~1.8 m figure) | 1.8 m | - | right; unchanged |
| creatures (pillbug, slime, bonca, duck, pig, dragon) | photoreal pillbug and pig meshes (real size), other cards at base scale (1.2 x 1.0 m pillbug picture) | real | - | right; unchanged |
| pickups, effects | cards at base scale, 4 footprint-fit pickup rows | real | - | unchanged |
| trees (pine, oak, willow; 626 of 636 family-bound) | real-size meshes (`fit: none`; anchored on the hardbox centre by #155) | pine slice ~2.5 m wide, 15-20 m tall | 3.7 x 2.3 / 3.2 x 1.9 -> 4.3 x 2.6 / 3.9 x 2.3 | right; unchanged |
| bushes (195), boulders (59), barrels (97), crates (45), sign posts (30), furniture (52) | real-size meshes | bush ~3 m, boulder 1-2 m, barrel 0.84 x 1.01 m, crate 1.2 m, sign post 0.2 m post | barrel 3.6 x 2.1 / 2.8 x 1.7 -> 4.2 x 2.4 / 3.6 x 2.1; crate 5.9 x 2.2 -> 6.8 x 2.5 (town) | right; unchanged |
| fences (18 family, 34 authored, 36 cards) | 4 m split-rail module (1.44 m high), repeated along the box (`span`) | 4.18 x 0.19 x 1.44 m module | 7.2 x 2.9 / 5.4 x 2.5 -> 8.4 x 3.3 / 6.9 x 3.1 | runs follow the box; modules real |
| interior and dungeon walls (884 family-bound) | kit modules spanned along the box | kit at 0.025 m/px (2.5 m bay) | interior 4.2 x 2.4 -> 4.9 x 2.8 | runs follow the box; height real |
| town house fronts (95 wall sprites, 121 placements) | assembled houses (`town_houses.json`): kit bays along the 1997 wall line, real height and 8.1 m depth | kit bay 2.5 m | sprite bay ~11.2 m -> ~12.8 m along the slant | bays were stretched to 2.79 m; now 2.54 m (see 3.3) |
| cottages, island huts, log cabins, church (83) | layout-scale CARDS (placeholders) | 1997 picture 25.0 x 23.8 m (town), 21.9 x 19.3 m (wild) | 6.0 x 2.4 / 17.4 x 4.8 -> 7.0 x 2.7 / 21.8 x 6.4 | placeholder, oversize already; grows with its box |
| doors (53), chests (18) | layout-scale cards (placeholders) | door picture 5.1 x 6.7 m (town) | door 3.0 x 2.3 -> 3.4 x 2.6 | placeholder; grows with its box |
| Dink's cottage on SCR_439 (authored kit, its own collision) | `SM_Cottage_Stonebrook_01` | 18.8 x 10.5 x 7.9 m | - | built to the 0.1 m/px footprint; see 3.4 |

The main earlier finding still holds and is the one this change makes worse: the 1997 boxes are pixels at the layout
scale while the photoreal meshes are real size (#139: blocking placements drawn by a mesh cover their box at a median
linear 0.35, p10 0.19, p90 0.75). The boxes grow by the ratio, the meshes do not: the median becomes about 0.30 in towns
and 0.27 in the wild, i.e. Dink stops another 0.3-0.9 m short of a barrel, bush or tree (section 4).

## 3. Per-family size rule

The rule: **spacing and space follow the layout; things that are already a believable real size keep it.**

1. **Follows the layout (it is the space, or it must close against the 1997 hardness):** terrain, ground sheets, water,
   cliffs, relief, forest canopy, the greybox collision (prisms from the 1997 hardness), warps, wall and fence RUNS
   (`span` families: the run's length), town house fronts (the 1997 wall line), and the unbound layout-scale CARDS
   (placeholders: the 1997 picture stays over its own hardbox and warp; Fable replaces them, they are not meant to be
   their final size).
2. **Real size, unchanged (already right):** Dink, NPCs, creatures, pickups, effects (`BASE_SCALE_CATEGORIES` of the
   export: cards at 0.025 m/px), every family mesh with `fit: none` (140 of 144 rows: trees, bushes, boulders, barrels,
   crates, furniture, sign posts, props), the modules inside runs (kit bay 2.5 m, fence module 4 m, wall height, house
   height and depth), lights, decals (`size_cm`).
3. **Town houses:** a sprite bay used to become four kit bays scaled to close the run (2.79 m each at 0.1 m/px). It now
   takes as many 2.5 m kit bays as fit (`round(length / 2.5 m)`, only once four would stretch by more than 20 %, so the
   old scale gives exactly the old file): median kit bay 2.54 m after (was 2.79 m), doors and windows at their real width.
   `Scripts/assemble_town_houses.py`; at the old bundle it reproduces the committed `town_houses.json` byte for byte.
4. **Hand-authored screens** (SCR_001 Dink's house and its render-only vista, skirt and underfloor; SCR_439 its yard;
   SCR_407 pig pen; SCR_438, SCR_471 fields): their `world_cm` were absolute. `Scripts/world_scale_convert_art.py` moves
   every position through the 1997 pixel it stood on (old corners -> pixel -> new corners). SPACE pieces (floor, walls,
   windows, doorway, roof, ground and field tiles, banks, paths, vista ground, skirt, underfloor, split-rail runs) scale
   in X/Y by the local ratio (1.143 indoors, 1.154 on 439/407/438, 1.25 on 471) so they still meet and still close every
   passage they closed (on these screens they ARE Dink's collision); their height stays. OBJECTS (furniture, barrels,
   candles, basket, chimney, boulders, oaks, pines, grass clumps, feed) keep their real size and only move. The one
   exception is Dink's cottage on 439: it is its own collision and carries the camera portal (`camera_exteriors.json`,
   `DinkCameraPortal::Limit` needs a uniform scale), so it scales uniformly by 1.154 (21.7 x 12.2 x 9.2 m): its door
   stays on its warp and its walls on the 1997 box. Fable queue row WS-01 asks for a real-proportion rebuild.

**Collision against the drawn object: dependency on the play layer (coordinator decision A70, 15 Nov 2026 22:38).**
Dink's physical collision is built from the 1997 hardness through the layout, so it grows with the boxes; the real-size
meshes do not. The boxes are already about 3x the meshes (#139: Dink stops 1-3 m short of trees, a sword hit registers
~3 m short, the gold heart is taken 2 m away) and this change widens that by the ratio (section 2). Decision A70: in PLAY
mode Dink's own collision, his attack hits and his pickups/touches follow the drawn 3D shapes, as a switchable layer
(like `Content/Dink/Data/AI/adaptation.ini`: on for play, off for the parity tests and the probe); the 1997 boxes stay for
NPCs, creatures, missiles, the simulation and parity. The physical-mapping stream builds that layer and writes its design
to `doc/remaster/PHYSICAL_PLAY_LAYER.md` (on its branch). Therefore:
- this PR keeps objects at their real size and does NOT enlarge any object to its box;
- in this PR (before the play layer lands) every object still collides as its 1997 box, scaled: the gap grows as measured
  in section 2 until the layer lands; with the layer, Dink meets the drawn shape and the gap is gone at any scale;
- where a 1997 box closes a corridor and the drawn thing is too small to read as closing it, the answer is art (a PM-xx
  row in `doc/remaster/FABLE_ART_QUEUE.md`), not a bigger object; the play layer's own connectivity check is where those
  corridors are found (the analyser's reach against the 1997 hardness: same reachable set, warps, scripts and items);
- the play layer must measure metres per pixel at run time (as `DinkWalkAudit`, `DinkFamilyAnchor` and the relief do),
  never assume the old scales, so it is correct before and after this change.

## 4. Speeds (owner decision A75)

Monsters move in 1997 pixels (`DinkBrains.cpp`, 60 px/s per point at timing 0), so their world speed is proportional to
the layout scale. The hero's run was a fixed 600 cm/s. A75 (15 Nov): a walking Dink may be slower than monsters, a running
Dink must stay faster than every monster with at least today's margin.

Design: `regions.toml [pace] reference` holds the scales the 6 m/s run was tuned at. The analyser solves the same layout
again at those scales and writes each screen's reference metres per pixel (`pace_m_per_px_reference`); the export writes
`Content/Dink/Data/Gameplay/hero_pace.json`: per screen, new / reference metres per pixel at the screen's centre (644
screens, 1.1416-1.3911), per kind as the fallback (settlement 1.15, wilderness and sea 1.3091, dungeon 1.2, interior
1.1429). `ADinkGreyboxCharacter` multiplies the run and its acceleration and braking by the factor of the screen Dink is on
(`PaceScale()`, cvar `dink.Hero.WorldScalePace`, default 1). The run in pixels per second is therefore exactly what it was
on every screen (at the screen centre), so the margin over every monster and the bot's pixel routes are unchanged. The walk
stays a human 1.7 m/s (`walk_follows_scale = false`). Herb's boots (A43, `set_dink_speed(2)`, fixed on #141 as
`DinkSpeedScale`) multiply on top.

| kind | run cm/s before -> after | run px/s | speed-1 monster cm/s before -> after | run : fastest monster | walk : fastest monster |
|---|---|---|---|---|---|
| settlement | 600 -> 693 | 60.8 = 60.8 | 592 -> 683 | 1.01 = 1.01 | 0.29 -> 0.25 |
| wilderness | 600 -> 765 | 81.0 = 81.0 | 445 -> 566 | 1.35 = 1.35 | 0.38 -> 0.30 |
| sea | 600 -> 770 | 82.6 = 82.6 | 436 -> 559 | 1.38 = 1.38 | 0.39 -> 0.30 |
| dungeon | 600 -> 719 | 106.6 = 106.6 | 338 -> 405 | 1.78 = 1.78 | 0.50 -> 0.42 |
| interior | 600 -> 685 | 137.0 = 137.0 | 263 -> 300 | 2.28 = 2.28 | 0.65 -> 0.57 |

(Medians per kind of each screen's centre metres per pixel. The fastest monsters are speed 1 at timing 0: pillbug, slayer,
goblin soldier, Mog, A75. The ~1.45 the owner quoted is the A75 figure for the nominal 6.875 cm/px wild screen; the median
wild screen is 7.4 cm/px, 1.35. Either way the ratio is unchanged by this PR on every screen.)

Travel time per screen, east-west, median per kind: running is unchanged (settlement 9.9 s, wild 7.4 s, sea 7.3 s, dungeon
5.6 s, interior 4.4 s); walking grows with the screens (settlement 34.8 -> 40.2 s, wild 26.2 -> 33.3 s, sea 25.6 ->
32.9 s, dungeon 19.9 -> 23.8 s, interior 15.5 -> 17.6 s). The run at 7.7 m/s is a sprint (28 km/h); the animation keeps
its stride and raises the cadence above the fastest authored gait (`FDinkGaitBlend::Solve`), so the feet do not slide,
but it will look quick: to be judged in the game.

## 5. Camera, fog, streaming, culling

Nothing there is derived from the layout; all values are fixed centimetres (boom 400 cm, outdoor maximum 650, interior
240/320, FOV 90/70; fog density 0.004, inscattering from 20 m, volumetric fog 90 m, Lumen view 200 m; grass far 38 m, forest
and relief 260 m, creatures 150 m, `dink.BillboardRange` 60 m; environment dressing within 160/220 m of the camera;
every sublevel always loaded). They are human-scale and stay: the camera around a 1.8 m Dink sees the same metres, which is
fewer 1997 pixels of a now larger screen (the intended "bigger world"); a fixed dressing radius covers fewer, larger
screens, so the cost per frame should not rise (to be measured, section 8).

## 6. What is derived from the layout, and what this PR does with it

| item | holds | done |
|---|---|---|
| `world_layout.json`, analyser outputs | metres per screen | rebuilt (`python3 -m analyse build`); tests adapted (settlement/wild contrast 1.2 -> 1.15; SCR_298/299 no longer overlap SCR_333 and stay on the mainland at their grid place, they are unreached islets) |
| export bundle (`Scripts/export_import_bundle.py`) | corners, world, m/px, card metres, warp quads | re-exported; pixel content identical (section 7); writes `hero_pace.json` |
| greybox, importer | built from the bundle | regenerated by `Scripts/import_greybox.sh --region all` + `--region stonebrook` |
| `families.json` `collision_fit` (85 fitted barrels) and `DinkBarrelRolloutSourcePins.inl` | the placement record hash (covers world and m/px) | re-pinned by `Scripts/world_scale_rehash.py` (refuses if anything but layout fields changed) |
| `Hardness/Foundations/SCR_nnn.json` (38) | screen corners | re-pinned by the same tool; the native `/Game/Dink/RuntimeHardnessV1` meshes must be deleted in a project copy before the import (the importer refuses to overwrite) |
| authored manifests (8 files, 1,135 positions) and `LightingV1/lighting.json` | absolute `world_cm` | `Scripts/world_scale_convert_art.py` (section 3.4), then `Scripts/house_lighting.py --apply` derives the daylight rows; `test_house_lighting.py` centres and aperture limits updated |
| `town_houses.json` | px + `offset_cm` from m/px | rebuilt by `Scripts/assemble_town_houses.py` (section 3.3); `test_town_house_coverage.py`: 97 -> 111 roof cards over open ground (the 1997 roofs lie farther behind real-depth houses) |
| water / terrain / ground masks, `layer_cover.json`, `ground_classes.json`, `ground_colour.json` | pixels | identical: no change. `SHORE_PX_CM` (a fixed 4.38 cm/px shore ramp in the export) is not real metres before or after; #150 owns it |
| decals, relief rocks, walk audit, PhotorealQA scripts | measure cm/px at run time or use pixels | follow by themselves |
| player blockers (#129) | mesh hulls | follow the meshes; which meshes get one came from a walk audit at the old scale: rerun `dink.WalkAudit` + `make_player_blockers.py` + `check_player_blockers.py` |
| interiors and warps | pixels; interiors packed 3000 m below the outdoor world | moved by the layout; warps are pixel destinations |
| save games | `PlayerTransform` in absolute world cm (`DinkSaveGame.h:92`); Dink's 1997 pixel and screen in the narrative state | on load, a pawn more than 1 m from Dink's saved pixel (a save from another scale) is stood on that pixel (`UDinkStorySubsystem::RestoreFromSave`, `dink.Save.RelocateToPixel`); within one layout both agree, so the probe's saves and loads are untouched (to be confirmed by the probe run) |
| fast travel | not implemented (`REMASTER_PLAN.md`) | nothing |
| Koka bridge stretch, cobbler's-booth join | regions.toml (factor on the kind scale; join in pixels) | follow |
| detached sheets | `min_gap_m` 1500 absolute | unchanged, gaps still 1500 m |
| open PRs on layout-derived data: #146 terrain layers, #150 water shapes, #153 landforms (`landforms.json` holds corners and m/px constants), #139 physical audit and the A70 play layer, #148 visual sweep (#155, anchors in pixels with measured cm/px, merged 22:38: scale-independent) | | this PR goes after them: rerun the export, `world_scale_rehash.py`, `world_scale_convert_art.py` on their data, regenerate `landforms.json` |

## 7. Proof that the pixels did not move (offline, done)

`python3 -I Scripts/world_scale_measure.py --old <bundle 2.75> --new <bundle 3.6> --pace Content/Dink/Data/Gameplay/hero_pace.json`:
collision.json identical; warps.json pixel fields identical; sprites.json identical; 644/644 ground and 644/644 ground-mask
images identical; 5,846 placements, pixel fields differ on 0. The analyser's connectivity.json, warps.json,
interiors.json, encounters.json, vision_variants.json and engine_reach.json are byte-identical between the two scales; the
reference-scale layout solved inside the new build reproduces the old layout's 644 centre scales exactly. Run speed in
pixels per second at every screen centre: new / old = 1.0000 (min and max over 644 screens).

## 8. Verification in the game (status)

Private copy, master 9cc796b6 + this branch, world regenerated at the new scale. To run, one Unreal step each:
build; `import_greybox.sh --region all` and `--region stonebrook` (after deleting `_Generated` and `RuntimeHardnessV1`);
`Scripts/test.sh Dink.Import+Dink.Art+Dink.Gameplay+Dink.Movement` (the probe's twenty md5s must equal
`packaged_probe.md`); `dink.WalkAudit` before and after (no passage opened or closed against the 1997 hardness); rendered
captures at the play camera of Stonebrook, Windemere, a wilderness screen, a dungeon, an interior and the Koka bridge,
before and after; frame cost on one busy screen. The PR text says which of these ran and with what result.

## 9. Risks

- The probe walks partly by physics (teleports in pixels, but the pawn's capsule is 28 cm, now fewer pixels): a route that
  slid along a wall can end one pixel elsewhere. If an md5 moves, the cause must be found, not re-baselined.
- Invisible walls, far hits and far pickups around real-size props grow (section 2) until the A70 play layer
  (`PHYSICAL_PLAY_LAYER.md`, physical-mapping stream) lands; this PR depends on it for the play feel, not for parity.
- The run is a sprint in the wild (7.7 m/s).
- Placeholder cards of cottages, doors and chests grow 15-31 % with their boxes (they were already oversize).
- Authored screens: their space pieces are stretched 14-25 % in X/Y (floor tiles 2.13 m, field tiles 6.9-7.5 m), the
  cottage of 439 is 15 % larger. Fable rows WS-01..03.
- Every open PR that holds layout-derived data needs its data regenerated after this one (section 6).
- Old saves: the pawn is moved onto Dink's saved pixel (not yet exercised in the game).
