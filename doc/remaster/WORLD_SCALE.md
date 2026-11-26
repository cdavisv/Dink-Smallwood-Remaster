# World scale: the original map larger (15 Nov 2026)

Owner's order (15 Nov 2026, 22:00): the original map must be larger than the original: everything expanded, slightly
farther apart; new content is added on top later (another stream). The coordinator chose the ratios. This document is the
design, the measurements behind it, what the change touches, and what is still open.

**Status (23 Nov 2026): behind a switch, OFF.** `tools/analyse/regions.toml` `[world_scale] enlarged = false` keeps the
1997-layout scales of `[scale]`; `true` lays the world out at `[scale_enlarged]` (the owner-approved ratios below). Every
tool, the hero pace, the save relocation and the regeneration recipe (section 12) are in; the committed data is the
switch-off data (identical to before, `hero_pace.json` 1.0 everywhere). The enlarged world was built, imported and run
headless on master 9ada93f1a (section 8): it builds, imports and passes `Dink.PhysicalPlay`, but the layer-off probe's
twenty md5s all move and its chapter 8 stops, and the layer-on probe stops in chapter 12. The cause is structural
(section 11) and needs an owner decision before the switch can go on.

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
| water / terrain / ground masks, `layer_cover.json`, `ground_classes.json`, `ground_colour.json` | pixels | identical except where #150 sized the drawn waterline in cm (row below). `SHORE_PX_CM` (a fixed 4.38 cm/px shore ramp in the export) is not real metres before or after; #150 owns it |
| decals, relief rocks, walk audit, PhotorealQA scripts | measure cm/px at run time or use pixels | follow by themselves |
| player blockers (#129) | mesh hulls | follow the meshes; which meshes get one came from a walk audit at the old scale: rerun `dink.WalkAudit` + `make_player_blockers.py` + `check_player_blockers.py` |
| interiors and warps | pixels; interiors packed 3000 m below the outdoor world | moved by the layout; warps are pixel destinations |
| save games | `PlayerTransform` in absolute world cm (`DinkSaveGame.h:92`); Dink's 1997 pixel and screen in the narrative state | on load, a pawn more than 1 m from Dink's saved pixel (a save from another scale) is stood on that pixel (`UDinkStorySubsystem::RestoreFromSave`, `dink.Save.RelocateToPixel`); within one layout both agree, so the probe's saves and loads are untouched (to be confirmed by the probe run) |
| fast travel | not implemented (`REMASTER_PLAN.md`) | nothing |
| Koka bridge stretch, cobbler's-booth join | regions.toml (factor on the kind scale; join in pixels) | follow |
| detached sheets | `min_gap_m` 1500 absolute | unchanged, gaps still 1500 m |
| `landforms.json` (#153, merged) | screen corners (m) and metre constants (banks, beds, camera cap) over a map-pixel grid | regenerated by `Scripts/export_landforms.py --bundle <new bundle>` (537 screens; walk cells over 20 degrees 20, was 48 at the old scale; camera rays blocked 0). At the old bundle the tool reproduces the committed file (6 atlas texels differ by at most 2 mm). Presentation only: the capsule keeps the flat floor |
| water band and ground masks (#150, merged) | sized in cm (capsule 28 cm, shore range 4 m) over map pixels | follow by the export: 2521 -> 2529 player-only waterline rects, 39 of 644 ground masks differ; the 1997 collision, sprites, ground images and placement pixels stay identical |
| `relaxed_hardboxes.json` (physical play layer #160, merged) | per placement: relaxed or kept (pixels), its drawn footprint `feet` in MAP PIXELS, open tiles | the footprint of a real-size mesh covers fewer pixels at a larger scale and its cover of the (unchanged) 1997 box drops: regenerated from a fresh `dink.PhysAudit` of the new world (headless, `-nullrhi`) by `Scripts/make_relaxed_hardboxes.py` (the old audit reproduces the committed list byte for byte). Hits, touches and creature reach read the drawn world in cm (`AttackReachCm` 85 cm) and need nothing |
| other open PRs on layout data | | rebase onto this and rerun the export / the tools above |

## 7. Proof that the pixels did not move (offline, done; rerun on master 9ada93f1a, 23 Nov 2026)

`python3 -I Scripts/world_scale_measure.py --old <bundle 2.75> --new <bundle 3.6> --pace Content/Dink/Data/Gameplay/hero_pace.json`:
collision.json identical; warps.json pixel fields identical; sprites.json identical; 644/644 ground images identical;
605/644 ground masks identical (39 differ where the #150 drawn waterline is sized in cm; rerun 23 Nov 2026 on master 9ada93f1a); 5,846 placements, pixel fields differ on 0. The analyser's connectivity.json, warps.json,
interiors.json, encounters.json, vision_variants.json and engine_reach.json are byte-identical between the two scales; the
reference-scale layout solved inside the new build reproduces the old layout's 644 centre scales exactly. Run speed in
pixels per second at every screen centre: new / old = 1.0000 (min and max over 644 screens).

## 8. Verification in the game (status, 23 Nov 2026)

Private copy (headless only: the machine's rendered runs are suspended), master 9ada93f1a (landforms #153 and the physical
play layer #160 merged) + this branch with the switch ON, world regenerated at the enlarged scale (analyser, export,
`world_scale_rehash.py`, `world_scale_convert_art.py`, `house_lighting.py --apply`, `assemble_town_houses.py`,
`export_landforms.py`, a fresh headless `dink.PhysAudit` and `make_relaxed_hardboxes.py`):

| check | result |
|---|---|
| clean build | OK, 0 warnings |
| `import_greybox.sh --region all` + `--region stonebrook` | OK (`RuntimeHardnessV1` rebuilt from the re-pinned corners) |
| headless `dink.PhysAudit 1 768` (`-nullrhi`) and the relaxed list | 5,599 origin rows; 506 boxes relaxed on 262 screens (was 456 / 234), 70 kept (66); open tiles identical; drawn footprints in pixels x ratio^2 = 1.08 (median) of the 15 Nov audit |
| `Dink.PhysicalPlay` (layer on in its scope) | 9/9 passed |
| `Dink.Gameplay.Probe`, layer OFF | **0/20 md5 equal**; chapters 1-7 complete with other traces, chapter 8 stops at step 1 (gold for elixirs, SCR_632) |
| `Dink.Gameplay.Probe`, layer ON (Mode 2, class creature art) | chapters 1-11 complete, **chapter 12 stops at step 2 of 5** (the dragons) |
| Python suite (copy) | 1037/1037 |

With the switch OFF (the committed state) the gates are the usual ones and are reported in the PR.
Not run: rendered captures before/after, frame cost, `dink.WalkAudit` (rendered runs suspended on this machine; listed on
`RENDER_PENDING.md` for when the switch goes on).

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

## 10. Blank space: a PROPOSAL for the owner (nothing added)

Owner decision (16 Nov 2026): extra scenery to fill blank space is a later owner decision; this PR proposes, it adds
nothing. Every outdoor screen grows by 1.30-1.93 in area with the same 1997 placements, so open ground per drawn thing
grows by the same factor. Measured on the new bundle (reached outdoor screens, placements that draw something):

- Emptiest single screens (m2 of ground per placement, new; was): SCR_406 Stonebrook village 3115 (2336, one placement on
  the screen), Southern beaches SCR_682 2916, SCR_746 2837 (nothing placed), SCR_684, SCR_747; Windemere marshes SCR_726
  2615 (nothing placed), SCR_602, SCR_571; Cobbler's meadows SCR_317, SCR_382, SCR_383, SCR_575, SCR_607, SCR_639; Koka
  beaches SCR_576, SCR_640, SCR_702-704; Escarpment SCR_247, SCR_249; Murkwood SCR_363, SCR_365; Western woods SCR_425,
  SCR_525; southern dam country SCR_661; Darklands SCR_125. Full list: 30 rows from `bundle_new` (method in the PR).
- Emptiest regions (median m2 per placement): Cobbler's meadows (east_wilds) 1004, snow castle 972, Goodheart castle
  grounds 780, the castle camp 780, the southern beaches 709, Terris wilds 553, Kernsin wilds 535, Murkwood 517.
- Candidates, all scale-independent, decorative and outside every 1997 hardbox and warp (no collision): more ground
  cover and loose stones from the existing environment dressing on the meadows and beaches, driftwood and shells on
  the beaches, reeds on the marsh banks, fallen branches and ferns in Murkwood and the western woods. Each needs a Fable
  art row and the owner's go before anything is placed.

## 11. Why the probe moves at the enlarged scale (needs an owner decision)

The 1997 rules, scripts, hardness, warps and placements are byte-identical at both scales (section 7), but the probe's
traces are not, because **Dink's 1997 pixel is read from his physical pawn** (`UDinkDirector`, the actor's world position
through `DinkLayout::MetresToMapPixel` into the sprite's x/y): his walk, his stops against walls and his warps are physics
in centimetres, mapped back to pixels. Two things change those pixels when the layout grows:

1. **The screens change shape, not just size.** The layout is a rubber sheet that blends the kinds; at the new ratios the
   sheet settles differently. Comparing each screen's edges new / old: on 506 of 644 screens the horizontal and vertical
   ratios differ from the centre ratio by more than 0.1 %, by up to 16 % (SCR_559: 1.48 along the top edge, 1.20 down the
   sides; SCR_613, SCR_525, SCR_603 above 13 %). One speed factor per screen (`hero_pace.json`) keeps the run's pixels per
   second at the centre only; elsewhere and across the axes Dink covers a different number of pixels per frame.
2. **Things measured in centimetres cover fewer pixels**: Dink's 28 cm capsule (5.6 instead of 6.4 pixels indoors), the
   player-only blockers of the real-size meshes, the #150 waterline band, the authored collision of the five hand-made
   screens. Chapter 1 shows the smallest case: every event is the same until Dink leaves his burning house, and the door
   warp of SCR_001 fires one frame (16.7 ms) later because the capsule reaches the warp quad a little later in pixels.
   From there on every time stamp moves, and later chapters' bot routes (made in pixels at the old scale) drift until
   chapter 8's gold run fails.

So "the layer-off probe equals the table" and "the approved per-kind ratios" cannot both hold with today's coupling.
Options for the owner (none is taken here):

- **A. Re-baseline at the enlarged scale.** Keep the ratios; re-tune the bot where it stops (chapter 8 layer off, chapter 12
  layer on) and write a new md5 table, documenting that only Dink's path through physics moved (the 1997 rules do not
  change). Cheapest; it is the re-baseline the parity rule otherwise forbids.
- **B. One ratio for every kind** (an exact similarity of today's layout) and Dink's capsule scaled by the same ratio: every
  collision built from the 1997 hardness then stays the same in pixels. The largest ratio inside all four approved
  intervals is 2.0 / 1.75 = 1.143 (settlement 4.57, wilderness and sea 3.14, dungeon 2.57, interior 2.0), if the
  intervals are read as bounds rather than as the exact new values. The cm-sized player-only blockers, waterline band and
  authored collision would still differ and must be proven harmless by the probe.
- **C. Decouple**: in parity runs move Dink in 1997 pixels (the 1997 engine's own movement) and let the pawn follow. The
  right long-term design for parity at any scale, a large change to the director and the bot, and itself a new table.

Owner decision (23 Nov 2026, "Yes, approved ratios"): **option A**. Branch `world-scale/enable` turns the switch on (section 14).

## 12. Turning it on (recipe, proven 23 Nov 2026 on master 9ada93f1a)

1. `tools/analyse/regions.toml`: `[world_scale] enlarged = true`.
2. `cd tools/analyse && python3 -m analyse build --ir ../dinkex/out --out out` (with `tools/dinkc/out` present; real
   directories, not symlinks). The switch reproduces the 16 Nov enlarged layout byte for byte.
3. Export the new bundle and keep the old one; `world_scale_rehash.py --old --new --write`, `world_scale_convert_art.py
   --old --new --write`, `git lfs pull` the Stonebrook kit FBX, `house_lighting.py --apply`, update the ledger hash of
   `LightingV1/lighting.json` (source-audit checks it), `assemble_town_houses.py` (reads `ImportData/`),
   `export_landforms.py --bundle <new>`.
4. In a project copy: delete `_Generated` and `RuntimeHardnessV1`, import `--region all` and `--region stonebrook`, run
   `dink.PhysAudit 1 768 <dir> quit` headless (`-game -nullrhi`, `dink.PhysicalPlay 0`, `-DinkLandforms=0`), then
   `make_relaxed_hardboxes.py <dir>/phys`.
5. Tests that pin enlarged-scale numbers (the 16 Nov prototype adapted them): `test_house_lighting.py` (window centres, the
   94 cm source width), `test_camera_portal_metadata.py` (SCR_001 corners), `test_town_house_coverage.py` (111 open roof
   cards, was 97), `DinkOutdoorCameraHeadroomTests.cpp` / `DinkOutdoorPortalCameraTests.cpp` (pawn positions on 439 and
   SCR_001). The values are in commit bd4849821 (the 16 Nov prototype head of PR #161).
6. Hero mannerisms (#230) trip a running Dink above `FDinkHeroPhysicality::RunTripSpeed` (world cm/s); with the switch on the run is
   up to 1.39 x 600 cm/s, so check that threshold against the paced run.
7. The probe question of section 11 first.

## 13. Option B tested (23 Nov 2026, branch world-scale/option-b, headless, NOT merged)

Owner: "Test B first". `[scale_enlarged]` = every current scale x 2.0 / 1.75 (settlement 4.571, wilderness and sea 3.143,
dungeon 2.571, interior 2.0), switch on in the branch only. What B changes besides the ratios:
- the analyser writes each screen's pace factor unrounded (`pace_factor_center`); `hero_pace.json` gets `physics_ratio`
  (the one ratio when every kind grows alike, else 1);
- `ADinkGreyboxCharacter` grows Dink's capsule radius by `physics_ratio` (28 -> 32 cm); `DinkPlayerBlockers` grows every
  player-only hull in X/Y by it; the export sizes the #150 waterline band for the capsule in reference pixels;
- `world_scale_convert_art.py`: authored warp triggers (`warp_overrides.extent_cm`) follow the layout in X/Y (they were
  kept in cm: this alone moved chapter 1 by one frame at the SCR_001 door), and `--similarity` grows every authored
  object and run as a whole (furniture, boulders, trees, fences 14 % larger on the five hand-made screens).

Results (build 0 warnings, import, headless `dink.PhysAudit` -> 474 relaxed boxes, `Dink.PhysicalPlay` 9/9):
- The layout is an exact similarity: every screen keeps its shape (edge ratios within 6e-6), one translation per sheet;
  bundle invariants: collision, sprites, ground images, all 644 ground masks, placements and the waterline band (2,521
  rects) identical to the current scale.
- Layer-off probe: **0/20 md5 equal the A41 table**; chapters 1-7 complete, chapter 8 stops at step 1.
- Why (instrumented run of chapter 1, every scripted move of Dink logged): all 32 move starts are at the same pixels in B
  and in the current world except one: arriving on SCR_439 from the burning house the current world reads Dink back at
  x 364.99965 (float residue of the world -> pixel transform), B at 365.00000. The extra 0.00035 px costs one 16.7 ms
  frame on the walk to x 437, every later time stamp moves, and the chained chapters drift from there.
- Proof that nothing else moves him: with the readback rounded to 1/1000 px (an experiment in the copy only), B and the
  current world produce **byte-identical traces in every chapter both ran** (1-10, 13). The A41 table itself depends on
  the residue: the rounded current world matches it on 2 of 20 chapters and its bot stops in chapter 8 (step 9, the
  three knights) as B's does.

So B keeps Dink's physics in 1997 pixels exactly, but no layout change can reproduce the table, whose md5s encode the
floating-point residue of today's coordinates. Any enlargement therefore needs one re-baseline (option A's step), and
the bot re-tuned where it stops; B makes that re-baseline a pure float-rounding change, A (the approved ratios) also
changes Dink's paths through screens of a different shape.

What B costs against the approved ratios (linear size of each screen, B / approved): settlement 0.99, interior 1.00,
dungeon 0.95, sea 0.89 (0.86-0.94), wilderness 0.90 (0.82-0.97); 435 of 644 screens more than 5 % smaller than
approved, 251 more than 10 %; smallest: the wild regions (Darklands, snow castle, fragments 0.87; Koka isle, west seas,
Cobbler's meadows 0.89). Mainland 1757 x 811 m (approved 1902 x 862, current 1537 x 709). On the five hand-made screens
furniture, boulders, trees and fences are 14 % larger than real (`--similarity`); elsewhere objects keep their size.

## 14. Option A: the switch ON (owner decision 23 Nov 2026; branch world-scale/enable)

Owner: "Yes, approved ratios": the approved per-kind ratios of `[scale_enlarged]`, ONE deliberate re-baseline of the probe's md5 table,
the bot re-tuned where it stops. The 1997 rules do not change: only the bot's tactics and the probe's timing move.

Data (regenerated per section 12, headless, private copy): `regions.toml [world_scale] enlarged = true`; analyser and export (the
switch-off bundle reproduces the master export byte for byte); `world_scale_rehash.py` (85 collision_fit hashes, 38 foundations);
`world_scale_convert_art.py` (8 manifests, see below); `house_lighting.py --apply` and the ledger hash of `LightingV1/lighting.json`;
`assemble_town_houses.py`; `export_landforms.py` (537 screens); `hero_pace.json` per screen 1.1416-1.3911. The relaxed hardbox list comes
from a fresh headless `dink.PhysAudit` (5,603 origin rows) through #233's generator (`summarise_phys_audit.py` first for A92, then
`make_relaxed_hardboxes.py --collision <bundle>/collision.json` for A71): 1026 boxes on 284 screens, 96 kept; 1516 open tiles on 265
screens, 72 kept; 520 walls trimmed to their drawn face on 36 screens.

### 14.1 What the enlarged world changed besides the numbers

- **Authored ground tiles (25 Nov 2026).** At the approved ratios the layout is not a similarity: on SCR_471 the local map old -> new is
  A = [[1.16, -0.11], [0, 1.35]] (x grows 1.16, y 1.35, plus a shear). `world_scale_convert_art.py` grew SPACE pieces by the one ratio
  sqrt(det A) = 1.25, so the field tiles of 471 left 60 cm cracks between their rows (sky-blue seams in the game). SPACE pieces now grow
  along their own X and Y by the layout's stretch on that axis (|A d|), runs along X; a similarity (the interiors) keeps the one ratio
  bit for bit. Left: the shear cannot be represented by a tile's scale, so the rows of 471 stand up to 64 cm staggered; one small dark
  notch shows where the dirt bank meets the meadow (rendered check, below).
- **A71 walls.** S713_P06 (and S712's walls) keep their 1997 box at this scale: P06's drawn strip (y 206-213) and P13's (y 222-229) are
  staggered, so freeing both boxes would join the corridor's two sides (the generator's passage rule). `Dink.PhysicalPlay.BlockageRows`
  walks the trimmed P07 beside it instead.
- **Player-only blockers (#129).** A blocker-off `dink.WalkAudit` at both scales gives the same 38 meshes through
  `make_player_blockers.py` (only hull and z values move with the ground under each placement); the committed list (45, drift since
  14 Nov) is kept. `check_player_blockers.py` on the enlarged blocker-on audit: 336 screens, 0 cut off.
- **Interior camera floor framing.** `camera_materials.json` `floor_framing` holds house 1's room rectangle in absolute world cm and was
  not moved by the switch: it lay 14 km from the house, so the camera never panned at the returned door and the bottom corners of the
  frame left the floor. `world_scale_convert_art.py` now moves it with the layout (`Dink.Art.InteriorCamera` passes again).
- **A one-row slit in SCR_190's hardness band.** The band across the west of 190 (y 240-257) is solid for the capsule at the reference
  scale; at this scale the capsule is fewer pixels wide and fits a slit inside it at y 249 (walk audit), reachable only from the screen's
  west edge. Harmless for the story; noted for the art side. **Sealed (26 Nov 2026):** the slit is a closed pocket of the 1997 map (the
  thorn S189_P03 closes it in SCR_189, a low stub at x 200 in SCR_190), so `Content/Dink/Data/Play/sealed_gaps.json` lists it (SCR_189
  x 242-599, SCR_190 x 0-199, y 246-253) and with part Collision on it joins the screen's low collision for Dink's capsule only, as solid
  for him as at the reference scale (`Dink.PhysicalPlay.SealedGaps`). Layer off (the probe) nothing changes: the chapter 17 teleport still
  lands in it there and the md5 table holds.
- **Audit of the whole map (26 Nov 2026, `Scripts/check_capsule_gaps.py`).** Offline, from the export's collision and the two layouts
  (`tools/analyse` with the switch off and on): (a) where the 28 cm capsule fits 1997 walkable ground at the enlarged scale and nowhere at
  the reference: 66 pockets, 41 of them closed (no walk of the 1997 map, point Dink over every screen edge, reaches them); 36 of those are
  sealed in play (`sealed_gaps.json`, 33 screens: the ridge slits of the Darklands rows 1-2 and SCR_223/224, the insides of closed boulder
  outlines), the other 5 are listed for review (scripted hardness or vision variants on SCR_031/278/342; SCR_473's opens in play); 25 open
  pockets (1997 ground behind a gap the capsule never passes) and 5 joins (a slit that joins two reference capsule regions: a way the
  1997 engine's point Dink walked, closed to the reference capsule; SCR_178/179 y 108-110, SCR_160 x 370, SCR_224, SCR_273) are reported,
  not changed. (b) every box Dink meets in play whose contact edge lies more than 1 m from anything drawn (dink.PhysAudit drawn mask), and
  the player-only hulls: 748 rows, mostly the 1997 rule (scripted sprites 209, family meshes the layer does not relax 331, cards 67,
  nothing drawn 69); 70 boxes the passage rule keeps (62 already kept at the reference: PM-07 art rows; new at this scale: the plaster
  walls S033_P06, S034_P18/P20, S130_P03, S195_P06, S225_P06, the dungeon wall S579_P11 and the pine S216_P05, up to 1.45 m); two hulls
  at a screen edge (their mesh drawn on the neighbour). Reports in ~/Work/Restart16Nov/ws-followup-1/audit_*.
- **Tests pinned at the reference scale** (never run with the switch on before): the run speed is 6 m/s times the screen's world-scale
  pace (`PlayableControls`, `StonebrookPlay`); the pure headroom geometry fixture keeps its measured pawn, eye and wall together; house 1's
  camera fixtures stand at the same cm from the returned door (`DoorY`); the pond-bank fixture of 438 finds its row on the geometry.
- **#230 trip threshold.** `RunTripSpeed` 490 cm/s; walk 170 (340 with the boots), paced run 685-835: no change. #228 independent.

### 14.2 Bot re-tune (probe code only; each needed because the bigger world moved the run)

Layer off and on:
- Ch8 step 1 (gold for elixirs): chapter 7's last duel now hurts Dink, so it ends beside the Terris healer, whose `main` idles in
  `wait(500)`; the feud step, its gold already met, waited on that loop. Done when the target is met and only restartable idlers remain
  (`Quiet()`).
- Ch8 knights' loot: the last knight's level-up now opens after the fight step in the layer-off run too; answered "Increase Attack" in
  both runs (#233 did it for the layer-on run only; with Magic, strength 29 makes the arrows 25 against Seth's defense 25).
- Ch11 Jack (DuelFight): a finishing blow from where Dink stands when the least blow (strength / 2 + 1 - defense) kills and the sword
  reaches (Jack at 3 hp stood on Dink, every cell inside his touch box).
- Ch11 feuds: "Get healed" answered four times (a step that heals twice took "Leave" and looped on the healer's menu).
- Ch19 SCR_209 food barrel: a collision_fit barrel is hit on its drawn mesh in cm also with the layer off; the 1997 spot is 2.5 m from
  it at this scale (1.95 m before). After each blow that does not land, one pixel nearer (it lands 5 px nearer).

Layer on only (`LayerAssist` and the guarded steps run only with the physical play layer):
- Ch11 SCR_480 pen: food dropped inside the pen cannot be reached at drawn contact through the fence once both Bongs are dead (the
  pen-stall exit needs a living Bong); with nothing alive the loot is left after 30 s.
- Ch17 SCR_190: the teleport to 60,250 found the one-row slit inside the hardness band (14.1); Dink is set down at 60,262, south of it,
  where the reference scale's teleport put him (68,260).
- The lunge state (`bLunged`, `LungeFrom`, `LungeTo`) lived in the per-frame `FCtx`, so the designed step back after a blow never ran.
  At this scale the dragon fight of ch12 then left Dink 93 cm from the dragon, inside the bot's touch grid, "evading" beside it until
  he died. Kept in `FProbeState` now; a push under 120 cm still returns him (the bot holds still during its blow), and a lunge the foe
  walks into is called off back to the bot's spot.

### 14.3 Gates and the new table

All on master f590bc730 + the branch unless said, headless, private copy (`Saved/WorldScale24Nov`), 25-26 Nov 2026:

| gate | result |
|---|---|
| clean build (editor) | 0 warnings (147 s) |
| game target (`package.sh`, cook without Zen) | PACKAGE OK, 0 warnings, content check 3033/3033 |
| `import_greybox.sh --region all` + `--region stonebrook` | OK |
| headless `dink.PhysAudit` -> relaxed list | 5,603 origin rows; list as in 14 (unchanged by the convert fixes) |
| `Dink.PhysicalPlay` | 10/10 |
| layer-off probe | 20/20 complete; two runs identical on master bc26c8ecf (the table), a third equal on f590bc730 |
| layer-on chained probe (Mode 2, class creature art) | 20/20 complete |
| full `Dink` suite | 413/413 |
| packaged probe (exclusive step, 20 game processes) | 20/20 chapters, PARITY OK 20/20 with the table |
| python suite | 1070 OK (1 skipped) |
| scrub, `check_public_paths.py`, `verify_sources.py --metadata-only`, CI source-audit | clean / 0 / passed / green |
| `tools/lfs_audit.py`, `lfs_private_check.sh` after the push | 0 missing / 0 hits |
| `dink.WalkAudit` + `check_player_blockers.py` | 336 screens, 0 cut off |
| rendered before/after, frame cost | `Docs/Verification/WorldScale_25Nov2026/README.md` |

The new table: Ch1 ca319f4754, Ch2 d9d836afef, Ch3 a797a40812, Ch4 1bb9f4986f, Ch5 085ede4dd4, Ch6 25ea8cd985, Ch7 c3fdfa1869,
Ch8 a20ff963c1, Ch9 1d3a1516cc, Ch10 c44c7280ee, Ch11 2a91042a40, Ch12 42d42beb77, Ch13 1d5dde4638, Ch14 f17e952d2c, Ch15 190fded2bf,
Ch16 bab2842735, Ch17 a4da0466da, Ch18 8154bb7fa9, Ch19 11a71bbf4b, Ch20 be78df8ac3 (`Plugins/DinkParity/Docs/packaged_probe.md`).
Taken on master bc26c8ecf; #246 (console `dink.Goto` only) and #247 (parked placements) merged after it and leave it unchanged (the
third run, on f590bc730). A later PR re-takes it only if it changes what the probe does (rules, physics, collision or the bot).
