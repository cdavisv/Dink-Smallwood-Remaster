# analyse: stages 3 (analyse) and 4 (layout) of the remaster pipeline

Reads the stage-1 IR from `tools/dinkex/out`, the stage-2 tile classes from
`tools/data/tile_classes.csv`, the DinkC sources in `bin/dink/story` (plain
text) and, when present, `tools/dinkc/out/calls.csv`. Works out what the
player can really reach, how the warps join it, which region each screen
belongs to, and where every screen, tile and placement goes in one continuous
3D world. Python 3.14, stdlib + numpy + Pillow. Never writes outside
`tools/analyse/`.

```
cd tools/analyse
python3 -m analyse build --ir ../dinkex/out --out out   # ~24 s, 16 MB
python3 -m unittest discover -s tests                   # 49 tests, ~14 s
```

Options: `--table regions.toml`, `--story ../../bin/dink/story`,
`--classes ../data`, `--dinkc ../dinkc/out` (all default to those paths).
`out/` is git-ignored. `regions.toml` is the hand-tuned, tracked table.

## Method

### 1. Walkable components (`connectivity.py`, `labels.py`)

Per screen, a pixel is walkable when its hardness code is 0 (codes 1, 2
"low", 3, 100 sprite hardbox and 200 warp trigger all stop the player). Two
relaxations make the mask *permissive*, i.e. "walkable at some point in the
game":

- a screen with vision-gated placements is walkable where **any** vision
  variant is walkable (crossings record whether they are open in vision 0 and
  in every variant);
- hardboxes of **removable** sprites are cleared: placements whose script dies,
  calls `draw_hard_map`/`draw_hard_sprite`, clears its own hardness or
  deactivates itself (barrels, boxes, bombable rocks, burnable trees, the
  pushable rock), and placements with a moving or fighting map brain. Thorns
  (`thorn.c`: touch damage, 0 hit points) are permanent. 133 hardboxes are
  removable. Each component also records `split_by_obstacles` (how many
  pieces it falls into with the obstacles left in).

Components are 4-connected (run-length labelling plus min-label propagation in
numpy; checked against a flood fill in the tests). Each is classified by the
pixel-weighted terrain of the tiles under it (`tile_classes.csv`): **land**,
**water** (`water`), **canopy** (`forest_canopy`), **void** (`void`, `chasm`)
or **blocked** (`lava`, `rock_mass`, `cave_wall`, `structure_facade`, any
`cliff_face`, anything `walkable_hint = no`). This matters because the original
draws tile hardness as outlines: open sea, forest canopy and the inside of
cliff ridges are hardness 0. Water, canopy and void are never player space.

### 2. Crossings and reachability (`graph.py`)

A screen change happens when the player walks off an edge onto a neighbour
that has a map record (`did_player_cross_screen`, which also wraps: off the
left of column 0 loads screen-1 on the row above). A crossing is counted where
the shared edge is walkable on both sides, pixel for pixel, for a run of at
least `min_crossing_px` (4) and neither side is water, canopy or void.

Reachability is a breadth-first search from the new-game spot (screen 1,
x 314, y 161 in map pixels) over crossings, sprite warps (walk into the
trigger hardbox; source = components touching the trigger, destination = the
component at `warp_x-20, warp_y`) and script warps (`&player_map = N;` plus
the following `sp_x/sp_y(1, …)`; they fire from every component of the
screens the script runs on, found by placement or one level of `"name"`
mentions). A second search without script warps shows what needs them.

*Walk groups* are the connected sets under crossings alone. Everything except
the start's group is entered only by a warp.

**Design reach and engine reach** (`engine.py`, added 7 Nov 2026). The search
above is the *design* reach: water, canopy and void are not player space and
the row wrap is ignored. The engine knows neither rule. It tests one hardness
pixel per step (`get_hard_play`, `dink.cpp` D:548) and `did_player_cross_screen`
(D:14049) carries Dink over every edge where the next map record exists, from
column 31 onto column 0 of the next row (`pmap + 1`) and from column 0 back.
`engine_reach.json` repeats the search without the terrain filter: `engine_dry`
keeps out open water only (cliff faces, forest interiors, the black void round
interior rooms count as ground; row wrap on), `engine_wading` lets water in too.
Every screen gets `reach_level` in `regions.csv`: `design`, `engine_dry`,
`engine_wading` or `none`. A screen above `design` is a sequence break: playable,
but no designed route leads to it. Components are 4-connected. The engine
checks only the destination pixel of a diagonal step, so real movement is
8-connected, but 1 px shoreline outlines then leak into open sea everywhere; the
4-connected result is the conservative reading and is what the tables use.
`graph.reach(..., barrier=, use_wraps=)` takes the class filter and the wrap
list; the routes in `engine_reach.json` name every step (crossing, wrap, warp)
and the removable sprites that open a component (`opens_when_removed`).

### 3. Warps (`warps.py`)

Kind from the sprite and context: seq 61/62 (`struct/details/door`) door;
seq 64/87 (interior wall strips) `exit` (or `interior_door` if it leads
indoors); seq 428 stairs; seq 89 frame 10 (`lands/details/crack`) `hole`,
`cave_mouth` (outdoor into a cave-floor interior), `hole_exit`/`cave_exit`.
Script warps are `pit` (`*-hole*`), `teleport_machine` (`s6-warp`), `teleport`
(`s7-warp`), `cutscene` or `script_transition`. The split is by what starts the
warp: each `&player_map = N;` is placed in its procedure (`void` line to the next
`void` line, as the engine runs it) and traced through local calls
(`enter();` inside `talk`) to the engine entry procedures. `main` (the screen
loads), `die` and the combat procedures fire without the player walking into or
talking to anything: `cutscene` (`s2-cave2` L154, `s1-ltr`, `s2-bar`, `en-gmog`).
`touch`, `push` and `talk` are the player: `script_transition`. Each script warp
records `proc`, `entry_procs`, `triggers` and `player_triggered`.

*Destinations are validated.* The engine does no range check on `sp_x/sp_y`: the
warp sets `&player_map`, loads the screen and puts Dink at (x, y). On the next
frame `did_player_cross_screen` sends him over any edge he is past (to pmap
-1/+1/-32/+32 if that map record exists) or clamps him to it, unless
`dink_can_walk_off_screen(1)` made it return at once. Every warp carries
`dst_screen_exists`, `dst_in_bounds` (x 0..599, y 0..399), `dst_valid` (both)
and `dst_engine.outcome`: `in_range`, `off_screen_entrance`, `edge_crosses`,
`edge_clamped`. The one off-map destination is `SW_s2-culg_L42` (screen 66, y 480):
the script sets the flag at L37, so Dink stands below the map and the script
walks him up (`move_stop(1, 8, 353, 1)`, L59) as the freed girl's escort; the
component is found from the point clamped to y 399. `return_warps` lists warps on the
destination screen that lead back (nearest to the arrival point first);
`one_way` is true when there is neither a return warp nor a walking route back.

### 4. Interiors (`interiors.py`)

Indoor screens are grouped by reached walkable crossings and indoor-to-indoor
warps (unreached components such as the black void around a room never join
rooms). Each set gets its entrances/exits, the region of its outdoor door
(entrances weigh 2, exits 1), a kind (`dungeon` for cave floors or 4+ rooms)
and a name from `[[interior]]` in the table or from its base scripts.

### 5. Regions (`regions.py`)

`regions.toml` `[[area]]` entries assign every outdoor screen (explicit
`screens` first, then `cells` rectangles in file order). Indoor screens take
the region of their interior set. A screen is named for its normal state, vision 0;
placements gated on a vision value are the other states (SCR_001: 1 burning,
2 burnt), listed in the `vision_states` column, and the build warns if a
sub-area name describes one (`regions.state_name_warnings`). The build scores each assignment with the
evidence on the screen: placement/base script prefixes (`s1` Stonebrook,
`s2` Terris and around, `s3` KernSin and goblin lands, `s4` Windemere, `s5`
Joppa, `s6` Edge of the World, `s7` Darklands, `s8` Koka, `sc` snow castle),
per-screen music, sign texts, and walk links to same-region screens.
`high` = supporting evidence and nothing against; `medium` = mixed, or
geography plus walk links; `low` = only contradicting evidence, or a table
cell with nothing to back it. The in-game map (`ingame_map.png`, 20 px per
screen) was used to place the label positions by hand.

### 6. Layout (`layout.py`)

**Base scale.** The hero idle frames are 96-97 px tall (1.8 m → 1.87 cm/px);
the open door frame (seq 62) is 64 px (2.2 m → 3.44 cm/px). Dink's sprites have
big heads, so the hero overstates and doors understate; the geometric mean is
2.53 cm/px. `base_m_per_px = 0.025`. Kind multipliers (REMASTER_PLAN §3):
settlement 4.0 (screen 60 × 40 m), wilderness and sea 2.75 (41.25 × 27.5 m),
dungeon 2.25 (33.75 × 22.5 m), interior 1.75 (26.25 × 17.5 m).

**Schemes considered.**

1. *Rectilinear rubber sheet*: each grid column a width, each row a height.
   Continuous for free and trivially invertible, but scale is per column and
   per row, not per region: making Stonebrook 4× also widens every wilderness
   screen above and below it, and a settlement column crossing a wilderness
   row gives anisotropic screens. It cannot express "settlements bigger than
   the countryside around them".
2. *Per-region affine blocks with blended borders*: each region its own scale
   and offset, with transition bands. Matches the plan's wording, but two
   regions with different scales disagree about the length of their shared
   border (a 600 px edge is 60 m on one side and 41 m on the other), so the
   blend has to deform screens anyway, the bands need hand placement, and the
   inverse becomes piecewise with special cases.
3. **Chosen: lattice rubber sheet (free-form mesh warp).** Every grid corner of
   a sheet has one world position; each screen maps bilinearly from its four
   corners. Option 1 is the special case where corners stay on straight
   rows and columns; option 2's blend falls out of a solve instead of being
   hand-drawn.

**Maths.** For screen *n* with corners P00 (nw), P10 (ne), P01 (sw), P11 (se)
and map pixel (x, y), with u = x/600, v = y/400:

    P(x, y) = (1-u)(1-v)·P00 + u(1-v)·P10 + (1-u)v·P01 + uv·P11

Neighbouring screens of a sheet share the two corners of their common edge, and
along that edge the map is linear in the shared pixel coordinate, so the two
sides agree exactly. Corner positions solve, per axis, the weighted linear
least-squares system

    for every screen n (target w_n = 600·base·k_n·sx, h_n = 400·base·k_n·sy, weight ω_n):
      ω_n (x10 - x00 - w_n) = 0,  ω_n (x11 - x01 - w_n) = 0,  ω_n (x01 - x00) = 0,  ω_n (x11 - x10) = 0
      ω_n (y01 - y00 - h_n) = 0,  ω_n (y11 - y10 - h_n) = 0,  ω_n (y10 - y00) = 0,  ω_n (y11 - y01) = 0
    for every vertex v: 1e-3 · (P_v - nominal_v) = 0

where k_n is the kind scale, (sx, sy) an optional `[[stretch]]`, ω_n the kind
weight (settlement 4, wilderness 1, sea 0.5) and nominal_v the vertex at
wilderness scale. Where neighbours ask for different sizes the shared edge
settles between them, weighted, so a settlement keeps its 60 × 40 m screens
and the wilderness screens around it become trapezoids that absorb the
change. The tiny pull towards nominal only fixes the translation of grid
pieces that touch nothing. The Jacobian gives every placement a local scale
(`m_per_px`, `scale_x`, `scale_y`, `rot_deg`). Inverse: Newton on the same
map (`Layout.to_local`), 1e-9 m convergence; `Layout.locate` finds the screen
for a world point. All 644 quads are convex (checked by build and tests).

**Sheets.** A sheet is a landmass laid out as one rubber sheet; its screens
are named in the table. `mainland` stays where it is. Every other sheet is
pushed, as a whole, along its `direction` until its bounding box is
`min_gap_m` = **1,500 m** from every sheet placed before it, then `offset` is
added. The bible's review puts greybox sight lines at about 500 m with height
fog; 1.5 km is three times that, so a detached region is past the fog horizon
from anywhere on the mainland even where no relief blocks the view. Interior
sets are one sheet each, packed in rows 3 km south of the world, 40 m apart.
A walkable crossing between screens on different sheets would break
continuity; the build lists such "seams" and a test requires that none of
them is reachable.

**No overlaps.** A grid piece that touches no other screen stays at its nominal
position, and the neighbouring scale changes can run over it (SCR_299 "Islets"
on SCR_333, Murkwood, by 557 m²; SCR_298 is its grid neighbour). After every
solve `layout.overlaps` clips all quad pairs; when two overlap, the unreached
one is parked with its unreached grid piece on the `fragments` sheet, flagged
in `world_layout.json` (`displaced`: `from_sheet`, `overlapped`) and in
`summary.json` (`displaced_screens`, `layout_overlaps`, empty), and the layout is
solved again. Reached means reached by design or by the engine. Two reached
screens that overlap, or an unreached piece that holds a reached screen, stop
the build (`LayoutError`). Result: SCR_298 and SCR_299 parked, no other pair
overlapped (SCR_299 also grazed SCR_365 by 0.2 m²).

**Costs of this scheme.** Transition screens are trapezoids, so tile grids,
landscape weight maps and straight roads crossing them bend slightly (the
importer must sample the bilinear map, not assume rectangles); the solve is
global within a sheet, so changing one region's scale moves every vertex of
that sheet a little (deterministically); and a screen holding ground from two
landmasses (Darklands slivers next to the Edge plateau) can only go with one
of them.

## Tuning `regions.toml`

- `[layout]`: `base_m_per_px`, `min_crossing_px`, `min_pocket_px`,
  `river_width_px`, `weight` per kind, `min_gap_m`, interior packing, `start`.
- `[scale]`: multiplier per kind.
- `[sheets.<name>]`: `anchor = "fixed"` or `direction = [dx, dy]` (x east,
  y south) plus `offset = [x, y]` metres. Sheets are placed in file order.
- `[[stretch]]`: extra x/y factors for grid cells (used to turn the Koka bridge
  into a causeway: row 22, cols 22-31, y × 2).
- `[[area]]`: `region`, `name`, `sub_area`, `kind` (settlement, wilderness,
  sea), `sheet`, `cells` ([col0, row0, col1, row1] inclusive), `screens`,
  and expected evidence `prefixes`, `music`, `signs`.
- `[[interior]]`: `screens` (any screen of the set), `name`, optional `kind`
  and `region`.

The build stops if an outdoor screen is unassigned or a quad goes non-convex.
After editing, rerun the build and the tests, check `regions.png`, the low
confidence rows of `regions.csv`, and `summary.json` → `seams_cut_between_sheets`.

## Outputs (`out/`)

| File | Content |
|---|---|
| `connectivity.json` | rules; counts; `start_component`; `walk_groups` (reached; screens, area, `entered_by` warps, `warp_only`, `reached_without_script_warps`, regions); `pockets` (unreached land ≥ `min_pocket_px`, with scripted placements inside → `secret_candidate` or `dead_space`); `unreached_screens`; `screen_links` (per grid pair: walkable, reached, px, `needs_obstacle_removal`, `vision_dependent`); `grid_neighbours_not_walk_linked`; `crossings`, `wrap_crossings`, `edge_leaks` (reached land meeting water/canopy/void at a screen edge); `water_bodies` (sea/lake/puddle); `components` per screen (`k`, area, class, `water_kind` sea/lake/river, bbox, centroid, reached, walk group, `split_by_obstacles`). Component IDs are `SCR_nnn#k`. |
| `connectivity.png` | world at 1/5 scale: reached land tinted per walk group, red = unreached land, blues = sea/lake/river, white edge ticks = reached crossings, yellow = sprite warps, magenta = script warps. |
| `warps.json` | `sprite_warps` (93) and `script_warps` (19): id, source screen/position, `src_components`, destination screen/position/component, `dst_screen_exists`, `dst_in_bounds`, `dst_valid`, `dst_engine`, `anim_seq` (parm_seq), sound, vision, trigger, kind (script warps also `proc`, `entry_procs`, `triggers`, `player_triggered`), `return_warps`, `has_return_warp`, `one_way`, src/dst region. Positions are map pixels. |
| `interiors.json` | 47 interior sets: id `INT_nnn`, screens, rooms, entrances, exits, region, `settlement` (if that region is a settlement), floor, base scripts, kind, name. |
| `regions.csv` | one row per used screen: region, name, sub_area, kind, sheet, confidence, evidence, contradictions, prefixes, music, signs, walk group, reached (design), `reach_level` (design / engine_dry / engine_wading / none), reached without script warps, land fraction, `vision_states`. |
| `engine_reach.json` | design vs engine reach (see method 2): counts, screens reached only by the engine, the wrap crossings in the dry reach, and per region the screen counts and a step-by-step route to its largest land component that the design does not reach. |
| `regions.png` | regions over the tile map; white frames settlements, red frames dungeons, red ticks low confidence. |
| `world_layout.json` | transform description, base scale evidence, `sheet_shift_m`, `summary`, and per screen: sheet, region, kind, corners `nw/ne/sw/se`, center, scale, area, 96 `tile_centers`, and every placement by origin ID with world x/y, `m_per_px`, `scale_x/y`, `rot_deg`, `size_factor` (local scale ÷ base); `displaced` is null, or says which sheet a parked screen came from and what it overlapped. |
| `layout_preview.png` | the transformed world to scale with labels and scale bars; top: everything (detached sheets, packed interiors), bottom: mainland detail. |
| `encounters.json` | screens where a `screenlock` script runs (source: `tools/dinkc/out/calls.csv` when present, else text scan), with `how` (`placed` or `via:<spawner>`), whether it locks, enemy placements; `provisional` only for indirect ones. |
| `vision_variants.json` | the 37 screens / 164 vision-gated placements grouped by vision value; `vision_setting_scripts` (scripts that run while the screen is loaded, base/random/load script, placement scripts and everything they `spawn`, `external` or `sp_script`, transitively, that assign `&vision` or call `force_vision`), `vision_set_by` per value, `visions_never_set`, the hardness variant images, and crossings closed in some vision. Top level: `never_set` (16 screens, 17 values: no script sets them, so the shipped game never draws those placements, because the engine zeroes `&vision` in `load_map`). |
| `summary.json` | layout numbers (areas, settlement sizes, sheets, gaps, run times), connectivity counts, seams. |

## Findings (from the shipped data, 5 Nov 2026)

### Numbers

- 2,814 walkable components on 644 screens; 1,671 walkable crossings; 680
  components on **498 screens are reachable** from a new game; 146 used
  screens are never reached (sea-only screens, the sealed east, most of the
  snowfield, the northern snow ledge, three orphan rooms, screen 10).
- Layout: outdoor 0.895 km² (0.613 km² land); mainland 0.768 km² (0.519 km²
  land); reached land to dress 0.524 km²; interiors 0.045 km².
- Mainland 1,413 × 709 m: straight run **236 s east-west, 118 s north-south**
  at 6 m/s (264 s on the diagonal).
- Settlements (bounding boxes): Stonebrook 296 × 120 m (15 screens), Terris
  293 × 120 m (15), Goodheart Castle 296 × 119 m (14), KernSin 296 × 120 m
  (15), Windemere 351 × 120 m (18), Edge of the World village 239 × 120 m (10),
  Goblin Sanctuary 241 × 160 m (16), Joppa 240 × 160 m (16), Cast camp
  180 × 79 m (6).
- Detached sheets: Joppa (west), Darklands (north-east), snow castle isle
  (north) each exactly 1,500 m from the mainland; the `fragments` sheet
  (orphan screen 10 and the parked islets SCR_298/299) is 2.2 km away.

### Regions (screens; outdoor + indoor)

Terris wilds 66, Stonebrook 61 (15 settlement), Edge of the World 56, East
Wilds 56, Darklands 52, Koka Isle 36, Snow castle isle 34 (9 castle rooms),
West Seas 33, South coast 32, Windemere wilds 28, KernSin 27, Murkwood 27,
Terris 24, KernSin wilds 24, Joppa Isle 23, Windemere 22, Goblin Sanctuary 17,
Goodheart Castle 16, Cast camp 6, unattached interiors 3, orphan fragment 1.
By kind: 415 wilderness, 125 settlement, 30 sea, 38 interior, 36 dungeon.
Confidence: 231 high, 288 medium, 125 low (mostly unreached sea/east-wilds
screens with no evidence either way).

### How the true regions connect

- **Mainland** (one walk group of 335 screens incl. the south coast, the
  Koka beaches and the Cast camp fields) holds Stonebrook, Goodheart Castle,
  Terris, Windemere, KernSin, Goblin Sanctuary and Koka.
- **Edge of the World plateau** (42 screens) is *not* walk-connected to the
  lowlands: the escarpment is solid. It is entered by the pit
  `s6-hole` on SCR_243 (guards at the cliff foot) landing on SCR_182, by cave
  exits SCR_164/165/198 and by the Darklands return machine. It stays on the
  mainland sheet: it is one landmass, just higher.
- **Joppa Isle** is reached by a tunnel: door SCR_537 (Windemere) → cellar
  SCR_163 → stairs → SCR_259/258/257 → exit SCR_483 on Joppa. The scripts
  never say how Joppa is reached; this is it.
- **Darklands** only via the ancients' machine (`s6-warp`, SCR_253 →
  SCR_154), back via `s7-warp`. The hellfire cave (SCR_085/086) is entered
  from SCR_254 in the Darklands.
- **Snow castle isle** is reached by the hole on SCR_144 (Edge plateau) →
  SCR_112; the castle (9 rooms, SCR_073…202) by the door on SCR_080.
- **Koka Isle is not an island**: a walkable bridge between two solid rails
  joins the mainland beach SCR_727 to SCR_759. It is kept on the mainland
  sheet with its channel row stretched ×2.

### Surprises

- **East Wilds, no designed entrance** (checked against the engine 7 Nov
  2026): 56 screens (cols 27-31, rows 8-20). No sprite warp, script warp or
  `&player_map` assignment lands there except the booth door S289_P19, and no
  grid edge is open from reached ground: a river about 80 px wide (shoreline
  outline, hardness 2 and 1, no gap at pixel level) runs down columns 25/26, a
  second water channel cuts the meadows at rows 11/12, and the cliff face of
  rows 7-8 has a closed foot outline. SCR_290 (door from Koka, SCR_734) and
  SCR_289 (door to SCR_350) are side by side but their rooms are not joined. The
  engine still has two routes in, both sequence breaks (`engine_reach.json`):
  (1) dry: push the rock S277_P03 (`s1-roc`, needs `&strength` 4, it moves east)
  to open the cliff-foot outline on SCR_277 (the hole S277_P02 beside it is a
  pit to the cave, SCR_131, but the gap is wide enough to pass it), walk the
  hardness-0 cliff face east through SCR_246-252 and 284-288, leave SCR_288
  by its right edge: the row wrap loads SCR_289, the booth's west room, on its
  black void, whose east-wall door S289_P19 (609, 167) lands on SCR_350
  (351, 241): 15 more screens, the booth room and the meadows of rows 8-11; (2)
  wading: the shoreline outline is cut at some screen edges (`edge_leaks`), the
  sea inside is hardness 0 and the row wrap carries it round the world, so 24
  more screens (rows 12-20) are reachable on foot through water; nine stay
  closed (SCR_509/510, 541/542, 573/574, 605/606, 637). Contains `s1-h1-4` placements on SCR_414/446, a save
  machine on SCR_349 and the cobbler (`s1-booth`/`s1-boot`). The design reach
  still says 8 of 56 (cliff and coast fragments).
- **Grid neighbours that are not connected**: 240 of 1,184 grid-adjacent
  pairs share no walkable edge. Indoor blocks are packed in the top-left
  (54 screens) with only void between them; the Darklands, snowfield and
  Joppa all touch mainland or sea screens on the grid.
- **Big unreached pockets**: most of the snowfield (25 screens, 5.2 M px),
  the East Wilds (several groups, ~9 M px), the northern snow ledge
  (SCR_120/149-153, which even holds an `s7-warp` placement on SCR_153),
  areas in the cave blocks (SCR_069…198) and inside the Darklands. 405 land
  pockets ≥ 1,500 px are listed; those with scripted placements are tagged
  `secret_candidate`.
- **Interiors with no entrance**: SCR_133, SCR_134, SCR_197 (no warp in or
  out); SCR_132 has only an exit (to SCR_534, Windemere) and `s1-hole`, so it
  is a **one-way** room. The other one-way link is the cult guard
  `s2-culg` teleport SCR_238 → SCR_066.
- **Edge leaks**: 10 places where reached land meets hardness-0 water,
  canopy or void across a screen edge (the outline stops at the screen
  border), e.g. SCR_466→467 water, SCR_250→282 canopy, SCR_228/229 void. The
  original lets Dink step onto those pixels; the remaster should not.
- Row wrap: 24 wrap crossings exist; the design reach ignores them. One
  matters: SCR_288 (cliff face, reached) onto SCR_289 (the booth's void), rows 17-399.
  Every one of the 93
  sprite warps is triggered by walking into its hardbox and lands within
  5 px of walkable ground (all 0 px in practice).
- **Screens shared by two landmasses**: SCR_188/189/221 hold both Edge
  village and Darklands ground; 189 and 221 were assigned to the Darklands
  because their reachable ground is Darklands. 22 unreached walkable
  crossings are cut between sheets (listed in `summary.json`), none reached.
- `s3-` is KernSin and goblins, `s4-` Windemere (the bible correction holds).
  Music 1016 marks Koka *and* the east coast strip (col 31 rows 11-21), which
  is how that strip was assigned.

### Open questions for a human

1. East Wilds: restore a designed way in (and where: the booth door
   S289_P19 and the river at SCR_443/444 are the natural places), or cut it? It
   is 0.07 km² of finished-looking map with a save machine, and the engine
   already lets players in by the cliff, the row wrap and the sea; a cut must
   also close those (the rock S277_P03, the wrap SCR_288 to SCR_289, the leaks).
2. Koka: keep the bridge (data) or move Koka out to sea as the plan says
   (needs the bridge cut, i.e. a new warp or ferry)?
3. The snowfield: is the unreached 80% scenery, or was there meant to be a
   path from the castle door?
4. Rooms SCR_133/134/197 and the one-way SCR_132: cut or wire up?
5. Edge plateau: the plan's "relief hides the north" works because the
   plateau is reached only by pits and caves; confirm the escarpment should
   stay unclimbable.
6. The base scale (2.5 cm/px) and kind multipliers give a small world
   (mainland run under 4 minutes). Tune on the greybox; the table is built
   for it.
7. Region names for the wilderness stretches (Terris wilds, Windemere wilds,
   KernSin wilds, South coast, Murkwood) are mine, not the game's.

## Limits

- Script effects beyond the rules above are not modelled (invisible barriers
  such as `s1-nopas`, `sp_hard` toggles on story state, gates opened by
  dialogue). The permissive mask may over-connect where a removable obstacle
  never actually goes away, and under-connect where a script opens a solid
  tile.
- Script warps come from a text scan; their source screens come from
  placement or one level of string mention. Engine reach is hardness only:
  it ignores stat gates (the rock needs `&strength` 4), touch damage and
  story-state barriers, and clears every removable hardbox like the design reach.
- Terrain classes are per 50 px tile, so components are classified by
  plurality of tile pixels, not by the art pixel.
