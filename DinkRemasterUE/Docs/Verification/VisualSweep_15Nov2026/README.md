# Visual sweep of the whole world (15 Nov 2026)

Owner's order: "check for issues, visual problems ... double check visuals". Every screen of the world (644: all
regions, interiors, dungeons, the sea and the three parked fragments) was captured in the real game at the play
camera and from above, scene-audited, run through automatic detectors, and looked at by eye, sheet by sheet. Fable
(art design) was at its limit, so this is triage: what needs Blender or new art is queued in
`doc/remaster/FABLE_ART_QUEUE.md` (rows VS-01 to VS-16); the small non-Blender fixes are in a separate PR.

Tree: master `f92915fe` (PR #126 water banks merged), private project copy rebuilt, world regenerated with
`import_greybox.sh --region all --export` then `--region stonebrook`. One capture run, offscreen Vulkan 1280x720,
`dink.ScreenScripts` on (screens run their scripts as a player would see them), 76 minutes.

## How it was done

1. `python3 -I Scripts/PhotorealQA/visual_sweep.py <out>` writes one capture script for all 644 screens, ordered by
   layout sheet: per screen `dink.Goto` to the walkable point nearest the centre (hardness 0 in a 17 px square),
   the play camera (boom 400 cm, pitch -12, looking north), a frame `NNN_play.png`, one `dink.SceneAudit` line, and a
   fixed camera over the whole screen `NNN_over.png` (outdoors from behind the south edge, indoors 2.6 m up at the
   south wall). `DINK_CAPTURE_TIMEOUT=5400 Scripts/PhotorealQA/run_capture.sh <out>/sweep.txt` runs it in one step.
2. `dink.SceneAudit <file>` (new, `Plugins/DinkCore/Source/DinkCore/Private/Greybox/DinkSceneAudit.cpp`, review only)
   writes every visible primitive of the player's screen: actor class, origin ID, mesh, materials and base materials,
   empty or engine-default texture parameters, bounds, the first surfaces a downward trace under it hits, per static
   mesh the LOD0 vertex/triangle counts, the share of hard-shaded vertices and the share of facet-angle vertices
   (normals 8 to 55 degrees apart), and every light of the screen.
3. `python3 -I Scripts/PhotorealQA/visual_sweep_report.py <out> --log=<game log>` runs the detectors and writes
   `detectors.csv` (per screen), `findings.json` (per hit), `meshes.csv` (every mesh seen), `log_findings.txt` (material,
   texture, Nanite and Dink warnings of the game log) and the contact sheets: frame luma (dark / blown), magenta,
   engine default material (WorldGrid, default, basic shape), empty textures, the grey script-sprite marker, sprite
   cards next to photoreal meshes, props floating above or sunk into what lies under them, coplanar flat meshes
   (z-fighting candidates), faceted meshes.
4. Every contact sheet in `sheets/` was looked at (`play_NN.jpg` and `over_NN.jpg`, 20 screens each, the order of the
   table below), and doubtful screens at full size; each screen got a grade: **OK** (nothing wrong a player would
   notice), **minor** (visible but small, or only from above), **defect** (a player at the play camera sees it clearly).

## Result

| grade | screens |
|---|---:|
| OK | 238 |
| minor | 308 |
| defect | 96 |
| not captured (teleport refused, see below) | 2 |
| **total** | **644** |

Detectors over the 627 screens captured in the full run: grey engine-default primitives on 58 screens (all of them either the
screenlock slabs, 29 screens, or the `create_sprite` marker cylinder, 31 screens); empty or default textures 0; magenta 0;
the game log of the whole run has **no** `Failed to compile Material`, no `missing usage flag`, no `Default Material
will be used`, no texture error and no Nanite material warning (only one engine VSM queue overflow line); 14 screens
with a dark play frame (mean luma below 0.10, all caves/dungeons and two capture points inside a house); 6 coplanar
candidates (pig pen paths on 407 and pebble decor on 244, neither shows flicker in the frames); 1 floating prop (a candle
on screen 1, standing on a shelf that has no collision: not a defect). Faceting: the full run measured the hard-vertex
share only (`meshes.csv`; it is 1.0 for every flat-shaded kit piece, which is mostly boxy planks and terrain tiles); the
facet-angle share was added to the audit afterwards and is measured on the screens of the fix PR's capture.
Nothing faceted was seen by eye at the play camera beyond what earlier sweeps fixed.

### The 20 worst, most visible first

| # | what | where | evidence | status |
|---:|---|---|---|---|
| 1 | Stonebrook cottage north of Dink's house is a 31 m 1997 card (`cottage_thatched_two_storey` S440_P11): pixel roof over the play view | 440 | `frames/440_play.jpg` | Fable queue VS-01 |
| 2 | Stonebrook cottage card (S409_P12, 25 m) next to the 3D cottage; camera inside its blurred pixels | 409 | `frames/409_play.jpg` | VS-01 |
| 3 | Grey engine-default screenlock slabs (WorldGrid cubes 1.6 m high along the open edges) on every locked fight screen; the original draws a pulsing red frame, no wall | 29 screens (26, 27, 32, 64, 90, 91, 123, 126, 156, 157, 160, 190, 191, 223, 270, 301-303, 334 ...) | `frames/026_*.jpg`, `090_*.jpg` | fixed in the fix PR |
| 4 | Goodheart castle walls and towers are 46-50 m cards with pixel bricks | 368-370, 399-401, 432, 433 | `frames/368_*.jpg`, `401_*.jpg` | VS-02 |
| 5 | Play camera inside a pine crown (boom passes into the foliage; nothing but needles in view) | 20 forest screens: 134, 240, 241, 272, 311-313, 333, 335, 343, 345, 348, 363, 502, 535, 560, 767, 768 ... | `frames/312_play.jpg`, `343_play.jpg` | code (camera), not art: reported |
| 6 | Scripted boulders still on cards: the Windemere rock the bomb removes (S536_P15), the rocks blocking the Kernsin road (590), the push rocks S277_P03 and S601_P08 | 536, 590, 277, 601, 535 | `frames/536_play.jpg`, `590_play.jpg`, `277_play.jpg` | Fable queue VS-15: binding the existing field boulders was tried and dropped (they are a fifth of the card and uncover the cave hole under the 277 push rock) |
| 7 | Small treasure chests are pixel cards up to 4.5 m, filling the view in dark rooms | 069, 101, 282, 395, 536, 557 (+ 5, 184, 209, 276, 288, 671, 685, 747) | `frames/069_play.jpg`, `395_play.jpg`, `557_play.jpg` | binding job (mesh exists, opened state needs wiring): reported |
| 8 | Terris, Windemere, Kernsin and Koka cottages as cards beside 3D cottages | 501, 530, 532, 617-619, 734 | `frames/501_*.jpg`, `530_*.jpg`, `617_*.jpg`, `619_*.jpg`, `734_*.jpg` | VS-01 |
| 9 | Sea drawn in pond olive, or olive sheets over the cyan sea with a straight seam | 424, 456, 480, 576, 608 (whole sheet); 720-724, 750-758 (south coast all olive); seams on ~40 more | `frames/424_*.jpg`, `456_*.jpg`, `480_*.jpg`, `720_*.jpg`, `753_*.jpg` | water follow-up of PR #126 (another agent is on `mark_sea_water`): reported |
| 10 | Dragons are big pixel cards | 123, 124, 127, 156, 159, 160, 191 | `frames/127_play.jpg`, `159_play.jpg` | VS-03 |
| 11 | Goblin sanctuary: two-storey hut cards with blue pixels beside the 3D round huts | 680, 681, 763, 764 | `frames/680_*.jpg`, `681_*.jpg`, `763_*.jpg` | VS-05 |
| 12 | The church is one 43 m card; its window cards float black | 187, 188 | `frames/188_*.jpg` | VS-06 |
| 13 | Grey cylinder markers of `create_sprite` sprites: almost all stand in for script people without art (the Terris bar wench and drinkers, the s2-cave guide, Windemere townsfolk ...); a few are sprites with no picture at all | 34 (5), 162, 193, 579 and 27 more screens (35 markers) | `frames/034_*.jpg` | pictureless ones hidden in the fix PR (2 of 35); the rest are Fable queue VS-16 |
| 14 | Ground layers keep the 1997 tile edges: pale rectangles, dashed dirt strips, stair-step sand coasts | ~120 outdoor screens | `frames/059_*.jpg`, `245_*.jpg`, `341_*.jpg`, `383_*.jpg` | VS-09 |
| 15 | Cave and ground holes are black spiky upright cards | 144 (the snow isle hole), 180, 483 (+ 9) | `frames/180_*.jpg`, `144_play.jpg`, `483_play.jpg` | VS-08 |
| 16 | Kernsin fountain spray is a blue pixel card | 586 | `frames/586_play.jpg` | VS-11 |
| 17 | Monsters on cards: stone giants, boncas, slayers, the orange creature of 238 | see VS-04 | `frames/090_play.jpg`, `238_play.jpg` | VS-04 |
| 18 | Dark figures (dynamic sprite cards) in the Stonebrook interiors and a card in the fireplace | 2, 4, 5, 38 | `frames/002_play.jpg`, `004_play.jpg`, `038_play.jpg` | VS-14 |
| 19 | Caves and dungeons very dark and bare | 98-101, 131, 164-166, 257-259 | `frames/098_play.jpg`, `164_play.jpg` | VS-13 (light level: non-Blender, not done) |
| 20 | Snow castle: pixel walls with a dither band, bare snow planes | 15-17, 48-50, 79-81; snow isle | `frames/015_*.jpg`, `048_*.jpg`, `079_*.jpg` | VS-02, VS-12 (off the story path) |

### Not art (reported, not queued for Fable)

- **Camera inside pine crowns** (row 5): the third-person boom does not collide with foliage and the occlusion fade
  (`DinkCameraOcclusion`) fades only houses. A code change (fade or shorten for foliage) for the camera owner.
- **`chest_small` binding** (row 7): `SM_Chest_Small_PR` and `SM_Chest_Small_Open_PR` are imported and unbound because
  the opened state is not read (`IMPORT.md`, props round 2). PR A9 (override picture) made revisited chests show the
  saved picture; a `frame` row per picture (closed 175/1, open) with `scripted: true` is the likely binding, but it
  needs an in-game check of the open animation: not done here.
- **Water colour** (row 9): see PR #126's README; a fix of `mark_sea_water` is in another agent's hands. The south
  coast (720-724, 750-758) being olive everywhere may be the same rule (no sand layer next to it).
- **Capture points inside buildings** (439 Dink's house body, 498, 506): the walkable point nearest the centre lies
  inside an assembled house (hardness 0 inside the 1997 wall line); not something a player sees.

### Not captured

In the full run 17 screens were not captured: 025, 145, 382, 402, 462, 469, 471, 472, 476, 507, 512, 629, 635, 661,
697, 747, 748. The teleport was refused (the point lies in filled water, whose blocker the hardness files do not show,
or the screen has no hardness file) and the player stayed on the previous screen. `visual_sweep.py` now tries up to
four points per screen; the second run (the fix PR's, same tree plus the fixes, which change none of these screens'
art) captured 15 of them (`sheets/recaptured_fix_run.jpg`, graded in the table). **145 and 402 are still not
captured** (every point refused).

## What was not checked

- Close-ups of single props (the sweep is play camera plus overview); faceting by the new facet share only on the
  fix PR's screens.
- Animation, creatures in motion, blood and gore against 1997 (other streams), night/vision variants (`&vision` other
  than the default at entry), story-state variants of a screen (burning house etc.).
- The packaged build (this is the editor game, which the packaged build matched in earlier checks).

## Files

| file | what |
|---|---|
| `sheets/play_NN.jpg`, `sheets/over_NN.jpg` | the 33 + 33 contact sheets, 20 screens each in the table's order; label: screen, region, kind, detector marks (D default material, S script marker, F floating, K sunk, Z coplanar) |
| `frames/NNN_play.jpg`, `frames/NNN_over.jpg` | full frames (960x540) of the screens named above |
| `detectors.csv`, `findings.json`, `meshes.csv`, `log_findings.txt` | detector output of the run |
| `sheets/recaptured_fix_run.jpg` | the 15 screens the full run missed, captured in the second run (play camera above, overview below) |
| `scripted_boulders_tried.jpg` | master against the existing field boulders bound to the scripted rocks (tried, dropped: Fable queue VS-15) |

## Per-screen grades

Sheet = contact sheet number. "cards N" counts sprite cards in the scene audit (many are hidden by the camera fade or
out of view); "grey default-material prims" are the lock slabs or the script marker.

| screen | region | kind | sheet | grade | what I saw | detectors |
|---:|---|---|---:|---|---|---|
| 025 | darklands | wilderness | 1 | minor | bare dark ground plane (recaptured in the fix run) |  |
| 026 | darklands | wilderness | 1 | defect | grey lock slabs | grey default-material prims 3, cards 1 |
| 027 | darklands | wilderness | 1 | defect | grey lock slabs | grey default-material prims 3, cards 1 |
| 028 | darklands | wilderness | 1 | minor | pixel creature cards (slayers) | cards 2 |
| 029 | darklands | wilderness | 1 | OK |  | cards 5 |
| 030 | darklands | wilderness | 1 | OK | pillbugs |  |
| 031 | darklands | wilderness | 1 | OK |  | cards 1 |
| 032 | darklands | wilderness | 1 | defect | grey lock slabs | grey default-material prims 2, cards 6 |
| 057 | darklands | wilderness | 1 | OK |  |  |
| 058 | darklands | wilderness | 1 | minor | rectangular dirt patch | cards 1 |
| 059 | darklands | wilderness | 1 | minor | dashed dirt strip (tile blobs) |  |
| 060 | darklands | wilderness | 1 | minor | dashed dirt strip | cards 2 |
| 061 | darklands | wilderness | 1 | minor | dashed strip | cards 2 |
| 062 | darklands | wilderness | 1 | minor | dashed strip |  |
| 063 | darklands | wilderness | 1 | minor | dashed strip |  |
| 064 | darklands | wilderness | 1 | defect | grey lock slabs | grey default-material prims 3, cards 2 |
| 089 | darklands | wilderness | 1 | OK |  |  |
| 090 | darklands | wilderness | 1 | defect | grey lock slabs | grey default-material prims 4, cards 4 |
| 091 | darklands | wilderness | 1 | defect | grey lock slabs | grey default-material prims 4, cards 16 |
| 092 | darklands | wilderness | 1 | OK |  |  |
| 093 | darklands | wilderness | 2 | OK |  |  |
| 094 | darklands | wilderness | 2 | minor | red pixel bits on ground | cards 7 |
| 095 | darklands | wilderness | 2 | OK |  |  |
| 096 | darklands | wilderness | 2 | OK |  |  |
| 121 | darklands | wilderness | 2 | OK |  |  |
| 122 | darklands | wilderness | 2 | minor | blocky dirt patches | cards 3 |
| 123 | darklands | wilderness | 2 | defect | grey lock slabs | grey default-material prims 4, cards 3 |
| 124 | darklands | wilderness | 2 | minor | dragons partly card? blocky dirt | cards 2 |
| 125 | darklands | wilderness | 2 | OK |  |  |
| 126 | darklands | wilderness | 2 | defect | grey lock slabs | grey default-material prims 4, cards 6 |
| 127 | darklands | wilderness | 2 | defect | pixelated dragon wing cards, large | script markers 1, cards 4 |
| 128 | darklands | wilderness | 2 | OK |  |  |
| 154 | darklands | wilderness | 2 | minor | rectangular dirt patches | cards 11, coplanar 3 |
| 155 | darklands | wilderness | 2 | minor | blocky patches |  |
| 156 | darklands | wilderness | 2 | defect | grey lock slabs | grey default-material prims 3, cards 3 |
| 157 | darklands | wilderness | 2 | defect | grey lock slabs | grey default-material prims 4, cards 4 |
| 158 | darklands | wilderness | 2 | minor | dashed strip | cards 1 |
| 159 | darklands | wilderness | 2 | defect | pixelated dragon card huge in foreground | cards 4 |
| 160 | darklands | wilderness | 2 | defect | grey lock slabs | grey default-material prims 3, cards 4 |
| 189 | darklands | wilderness | 2 | OK |  |  |
| 190 | darklands | wilderness | 3 | defect | grey lock slabs | grey default-material prims 4, cards 7 |
| 191 | darklands | wilderness | 3 | defect | grey lock slabs | grey default-material prims 4, cards 5 |
| 192 | darklands | wilderness | 3 | OK |  | cards 18 |
| 221 | darklands | wilderness | 3 | OK |  |  |
| 222 | darklands | wilderness | 3 | OK |  |  |
| 223 | darklands | wilderness | 3 | defect | grey lock slabs | grey default-material prims 4 |
| 224 | darklands | wilderness | 3 | OK |  |  |
| 254 | darklands | wilderness | 3 | OK |  | cards 1 |
| 255 | darklands | wilderness | 3 | OK |  |  |
| 256 | darklands | wilderness | 3 | minor | rectangular plank-floor patches in dirt (tile shapes) |  |
| 010 | fragments | wilderness | 3 | OK |  |  |
| 298 | west_seas | wilderness | 3 | OK |  |  |
| 299 | west_seas | wilderness | 3 | OK |  |  |
| 001 | stonebrook | interior | 3 | OK |  | floating 1 |
| 002 | stonebrook | interior | 3 | defect | dark pixelated sprite card figure (bottom right) | cards 1 |
| 003 | stonebrook | interior | 3 | OK |  | cards 4 |
| 004 | stonebrook | interior | 3 | defect | purple/blue pixel card object | cards 2 |
| 005 | terris_wilds | interior | 3 | defect | black pixel splat card on floor | cards 3 |
| 006 | edge_of_the_world | interior | 3 | minor | over camera black (camera outside room); play OK | cards 1 |
| 033 | terris | interior | 3 | OK |  | grey default-material prims 1, script markers 1, cards 1 |
| 034 | terris | interior | 4 | defect | grey script cylinder (fixed by FIX marker) | grey default-material prims 5, script markers 5 |
| 035 | terris | interior | 4 | minor | small creature card near spinning wheel | grey default-material prims 1, script markers 1, cards 2 |
| 036 | terris | interior | 4 | OK |  | grey default-material prims 1, script markers 1, cards 1 |
| 037 | terris | interior | 4 | OK |  | cards 1 |
| 038 | terris | interior | 4 | defect | pixel card figure in fireplace | cards 2 |
| 065 | terris | interior | 4 | OK |  |  |
| 066 | terris | interior | 4 | OK |  | grey default-material prims 1, script markers 1, cards 3 |
| 067 | kernsin | interior | 4 | OK |  | grey default-material prims 1, script markers 1 |
| 068 | terris | interior | 4 | OK |  | grey default-material prims 1, script markers 1, cards 2 |
| 069 | terris_wilds | dungeon | 4 | defect | huge pixelated chest card in front of camera; dark room | cards 1, dark 0.071 |
| 070 | goodheart_castle | interior | 4 | defect | King on throne = big pixel card; pixelated wall cards (story path) | cards 19 |
| 102 | goodheart_castle | interior | 4 | OK | knights | cards 10 |
| 073 | snow_castle | dungeon | 4 | OK |  | grey default-material prims 1, script markers 1 |
| 074 | snow_castle | dungeon | 4 | OK |  | script markers 1, cards 2 |
| 105 | snow_castle | dungeon | 4 | OK |  |  |
| 106 | snow_castle | dungeon | 4 | OK |  | grey default-material prims 3, cards 1 |
| 137 | snow_castle | dungeon | 4 | OK |  | grey default-material prims 3, cards 2 |
| 138 | snow_castle | dungeon | 4 | OK |  | grey default-material prims 3, cards 1 |
| 169 | snow_castle | dungeon | 4 | OK |  |  |
| 170 | snow_castle | dungeon | 4 | minor | small green card at edge | grey default-material prims 3, cards 2 |
| 202 | snow_castle | dungeon | 5 | OK |  |  |
| 085 | darklands | dungeon | 5 | OK | lava | grey default-material prims 1, script markers 1, cards 1 |
| 086 | darklands | dungeon | 5 | minor | grass floor in lava cave | cards 1 |
| 097 | kernsin | interior | 5 | OK |  | grey default-material prims 1, script markers 1, cards 17 |
| 098 | stonebrook | dungeon | 5 | minor | very dark cave, bare grey wall band | cards 2, dark 0.086 |
| 099 | stonebrook | dungeon | 5 | minor | very dark, bare | dark 0.097 |
| 100 | stonebrook | dungeon | 5 | minor | very dark | cards 6, dark 0.082 |
| 131 | stonebrook | dungeon | 5 | minor | dark bare |  |
| 101 | terris_wilds | dungeon | 5 | defect | huge pixelated chest card; dark | cards 1, dark 0.080 |
| 129 | kernsin | interior | 5 | OK |  | grey default-material prims 1, script markers 1, cards 1 |
| 130 | kernsin | interior | 5 | OK |  | grey default-material prims 1, script markers 1 |
| 132 | windemere | dungeon | 5 | minor | dark; signpost+tree indoors (data) | cards 1, coplanar 1, dark 0.076 |
| 133 | unattached_interiors | interior | 5 | OK |  |  |
| 134 | unattached_interiors | interior | 5 | defect | play camera inside tree canopy | dark 0.080 |
| 161 | kernsin | interior | 5 | OK |  | grey default-material prims 1, script markers 1, cards 4 |
| 162 | windemere | interior | 5 | defect | grey script cylinder (fixed by FIX marker) | grey default-material prims 1, script markers 1, cards 1 |
| 163 | joppa_isle | dungeon | 5 | OK |  | grey default-material prims 3, script markers 3, cards 3 |
| 257 | joppa_isle | dungeon | 5 | minor | dark empty |  |
| 258 | joppa_isle | dungeon | 5 | minor | dark empty |  |
| 259 | joppa_isle | dungeon | 5 | minor | dark empty |  |
| 164 | edge_of_the_world | dungeon | 6 | minor | dark cave, bare walls | cards 1, coplanar 4, dark 0.078 |
| 165 | edge_of_the_world | dungeon | 6 | minor | dark | coplanar 3, dark 0.077 |
| 166 | edge_of_the_world | dungeon | 6 | minor | dark | cards 2, dark 0.078 |
| 193 | stonebrook | interior | 6 | defect | grey script cylinder (fixed by FIX marker) | grey default-material prims 1, script markers 1, cards 1 |
| 194 | windemere_wilds | interior | 6 | OK |  | grey default-material prims 1, script markers 1, cards 1 |
| 195 | windemere | interior | 6 | OK |  | grey default-material prims 1, script markers 1, cards 1 |
| 196 | windemere | interior | 6 | OK |  | grey default-material prims 1, script markers 1, cards 1 |
| 197 | unattached_interiors | interior | 6 | OK |  |  |
| 198 | edge_of_the_world | dungeon | 6 | minor | dark | dark 0.088 |
| 225 | kernsin | interior | 6 | OK |  | grey default-material prims 1, script markers 1, cards 1 |
| 226 | joppa_isle | interior | 6 | OK |  | cards 1 |
| 227 | goblin_sanctuary | dungeon | 6 | minor | dark | cards 1, dark 0.084 |
| 228 | joppa_isle | interior | 6 | OK |  | cards 4 |
| 229 | joppa_isle | interior | 6 | OK |  | cards 1 |
| 260 | edge_of_the_world | interior | 6 | OK |  | cards 1 |
| 261 | edge_of_the_world | interior | 6 | OK |  | grey default-material prims 1, script markers 1 |
| 289 | koka_isle | interior | 6 | OK |  | grey default-material prims 1, script markers 1 |
| 290 | koka_isle | interior | 6 | OK |  | cards 1 |
| 514 | terris_wilds | dungeon | 6 | OK |  | grey default-material prims 2, cards 2 |
| 515 | terris_wilds | dungeon | 6 | OK |  | grey default-material prims 2, cards 1 |
| 546 | terris_wilds | dungeon | 7 | OK |  | cards 8 |
| 547 | terris_wilds | dungeon | 7 | minor | purple pixel creature cards (slimes?) | grey default-material prims 3, cards 3 |
| 577 | terris_wilds | dungeon | 7 | OK |  | grey default-material prims 2, cards 2 |
| 578 | terris_wilds | dungeon | 7 | OK |  |  |
| 579 | terris_wilds | dungeon | 7 | minor | script cylinder (fixed); flame plane cards | grey default-material prims 1, script markers 1 |
| 609 | terris_wilds | dungeon | 7 | minor | dark | grey default-material prims 2, cards 1, dark 0.099 |
| 610 | terris_wilds | dungeon | 7 | OK |  | cards 3 |
| 385 | joppa_isle | settlement | 7 | OK |  | cards 5 |
| 386 | joppa_isle | settlement | 7 | minor | light gaps between town wall segments |  |
| 387 | joppa_isle | settlement | 7 | minor | light gaps between wall segments |  |
| 388 | joppa_isle | settlement | 7 | OK |  |  |
| 417 | joppa_isle | settlement | 7 | OK |  | cards 6 |
| 418 | joppa_isle | settlement | 7 | OK |  | cards 9 |
| 419 | joppa_isle | settlement | 7 | minor | odd plaster panel next to stone wall at play camera | cards 8 |
| 420 | joppa_isle | settlement | 7 | OK |  | cards 3 |
| 449 | joppa_isle | settlement | 7 | OK |  |  |
| 450 | joppa_isle | settlement | 7 | OK |  |  |
| 451 | joppa_isle | settlement | 7 | OK |  |  |
| 452 | joppa_isle | settlement | 7 | OK |  |  |
| 481 | joppa_isle | settlement | 7 | minor | tile-shaped sand/sea outline |  |
| 482 | joppa_isle | settlement | 8 | OK |  |  |
| 483 | joppa_isle | settlement | 8 | defect | dark pixelated card on beach | cards 1 |
| 484 | joppa_isle | settlement | 8 | OK |  |  |
| 117 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 120 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 144 | edge_of_the_world | wilderness | 8 | defect | pixelated brown/white card next to Dink | cards 1 |
| 145 | edge_of_the_world | wilderness | 8 | not captured | (goto failed, shows 144) | not captured |
| 149 | edge_of_the_world | wilderness | 8 | defect | huge pixelated card fills top-left of play view | cards 6 |
| 150 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 151 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 152 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 153 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 176 | edge_of_the_world | wilderness | 8 | minor | pine branches across play camera |  |
| 177 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 178 | edge_of_the_world | wilderness | 8 | minor | pine branch across play camera | cards 2 |
| 179 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 180 | edge_of_the_world | wilderness | 8 | defect | black spiky upright card (hole?) - near-black prop | cards 1 |
| 181 | edge_of_the_world | wilderness | 8 | OK |  |  |
| 182 | edge_of_the_world | wilderness | 8 | OK |  | cards 2 |
| 183 | edge_of_the_world | wilderness | 8 | OK |  | cards 1 |
| 184 | edge_of_the_world | wilderness | 9 | OK |  | cards 1 |
| 185 | edge_of_the_world | wilderness | 9 | minor | rectangular light grass patches |  |
| 186 | edge_of_the_world | settlement | 9 | minor | play camera inside pine trunk/branches; black window cards float (over) |  |
| 187 | edge_of_the_world | settlement | 9 | minor | black church-window cards floating (60_02/60_09) seen from above | cards 2 |
| 188 | edge_of_the_world | settlement | 9 | defect | church = 43 m 1997 card (seq 60) dithered by camera fade across play view; window cards | cards 7 |
| 208 | edge_of_the_world | wilderness | 9 | minor | pine branches over camera |  |
| 209 | edge_of_the_world | wilderness | 9 | OK |  | cards 5 |
| 210 | edge_of_the_world | wilderness | 9 | OK |  |  |
| 211 | edge_of_the_world | wilderness | 9 | OK |  | cards 1 |
| 212 | edge_of_the_world | wilderness | 9 | OK |  | cards 1 |
| 213 | edge_of_the_world | wilderness | 9 | OK |  | cards 1 |
| 214 | edge_of_the_world | wilderness | 9 | OK |  |  |
| 215 | edge_of_the_world | wilderness | 9 | OK |  | cards 1 |
| 216 | edge_of_the_world | wilderness | 9 | OK |  |  |
| 217 | edge_of_the_world | wilderness | 9 | OK |  |  |
| 218 | edge_of_the_world | settlement | 9 | minor | play camera inside pine | cards 1 |
| 219 | edge_of_the_world | settlement | 9 | OK |  | cards 5 |
| 220 | edge_of_the_world | settlement | 9 | OK |  |  |
| 237 | murkwood | wilderness | 9 | OK |  | grey default-material prims 2 |
| 238 | murkwood | wilderness | 9 | defect | big orange pixelated creature card (red dragon?) next to Dink | cards 1 |
| 239 | murkwood | wilderness | 10 | minor | pine near camera |  |
| 240 | edge_of_the_world | wilderness | 10 | defect | play camera inside pine canopy (nothing visible) |  |
| 241 | edge_of_the_world | wilderness | 10 | defect | play camera inside pine canopy |  |
| 242 | edge_of_the_world | wilderness | 10 | OK |  | cards 1 |
| 243 | edge_of_the_world | wilderness | 10 | OK |  |  |
| 244 | edge_of_the_world | wilderness | 10 | OK |  | coplanar 2 |
| 245 | edge_of_the_world | wilderness | 10 | minor | rectangular pale grass patches | cards 2 |
| 246 | edge_of_the_world | wilderness | 10 | minor | rectangular pale grass patches | cards 1 |
| 247 | edge_of_the_world | wilderness | 10 | minor | rectangular pale grass patches |  |
| 248 | edge_of_the_world | wilderness | 10 | OK |  | cards 1 |
| 249 | edge_of_the_world | wilderness | 10 | minor | rect patches |  |
| 250 | edge_of_the_world | settlement | 10 | OK |  |  |
| 251 | edge_of_the_world | settlement | 10 | defect | big pixelated card (seen in over) next to houses | cards 4 |
| 252 | edge_of_the_world | settlement | 10 | minor | rect patches |  |
| 253 | edge_of_the_world | settlement | 10 | OK |  |  |
| 269 | murkwood | wilderness | 10 | OK |  |  |
| 270 | murkwood | wilderness | 10 | defect | grey lock slabs | grey default-material prims 4, cards 1 |
| 271 | murkwood | wilderness | 10 | OK |  |  |
| 272 | terris_wilds | wilderness | 10 | defect | play camera inside pine canopy |  |
| 273 | terris_wilds | wilderness | 10 | OK |  |  |
| 274 | terris_wilds | wilderness | 11 | defect | play view filled by pixelated stone card next to 3D cottage | cards 6 |
| 275 | terris_wilds | wilderness | 11 | OK |  |  |
| 276 | stonebrook | wilderness | 11 | minor | olive flat pond water | cards 1 |
| 277 | stonebrook | wilderness | 11 | defect | huge pixelated boulder card in front of camera (rock s1-roc?) | cards 2 |
| 278 | stonebrook | wilderness | 11 | OK |  |  |
| 279 | stonebrook | wilderness | 11 | OK |  |  |
| 280 | stonebrook | wilderness | 11 | OK |  |  |
| 281 | stonebrook | wilderness | 11 | OK |  |  |
| 282 | stonebrook | wilderness | 11 | defect | huge pixelated red/white card (chest?) fills view | cards 1 |
| 283 | stonebrook | wilderness | 11 | OK |  |  |
| 284 | east_wilds | wilderness | 11 | minor | pine sapling in front of camera | cards 1 |
| 285 | east_wilds | wilderness | 11 | OK |  |  |
| 286 | east_wilds | wilderness | 11 | OK |  |  |
| 287 | east_wilds | wilderness | 11 | OK |  |  |
| 288 | east_wilds | wilderness | 11 | OK |  | cards 1 |
| 301 | murkwood | wilderness | 11 | defect | grey lock slabs | grey default-material prims 3 |
| 302 | murkwood | wilderness | 11 | defect | grey lock slabs | grey default-material prims 4, cards 2 |
| 303 | murkwood | wilderness | 11 | defect | grey lock slabs | grey default-material prims 4 |
| 304 | terris_wilds | wilderness | 11 | minor | camera in pine |  |
| 305 | terris_wilds | wilderness | 11 | OK |  |  |
| 306 | terris_wilds | wilderness | 12 | minor | rect patches | cards 1 |
| 307 | terris_wilds | wilderness | 12 | OK |  | cards 6 |
| 308 | stonebrook | wilderness | 12 | minor | olive pond |  |
| 309 | stonebrook | wilderness | 12 | OK |  |  |
| 310 | stonebrook | wilderness | 12 | minor | rect patches |  |
| 311 | stonebrook | wilderness | 12 | defect | play camera inside pine (trunk+branch fill view) |  |
| 312 | stonebrook | wilderness | 12 | defect | play camera inside pine canopy |  |
| 313 | stonebrook | wilderness | 12 | defect | play camera inside pine canopy |  |
| 314 | stonebrook | wilderness | 12 | OK |  |  |
| 315 | stonebrook | wilderness | 12 | OK |  |  |
| 316 | east_wilds | wilderness | 12 | OK |  |  |
| 317 | east_wilds | wilderness | 12 | minor | rect patches |  |
| 318 | east_wilds | wilderness | 12 | minor | rect patches |  |
| 319 | east_wilds | wilderness | 12 | OK |  |  |
| 320 | east_wilds | wilderness | 12 | OK |  |  |
| 324 | west_seas | wilderness | 12 | minor | tile-shaped sand islands |  |
| 333 | murkwood | wilderness | 12 | defect | play camera inside pine canopy |  |
| 334 | murkwood | wilderness | 12 | defect | grey lock slabs | grey default-material prims 4 |
| 335 | murkwood | wilderness | 12 | defect | play camera inside pine |  |
| 336 | goodheart_castle | settlement | 12 | OK |  |  |
| 337 | goodheart_castle | settlement | 13 | minor | rect patches |  |
| 338 | goodheart_castle | settlement | 13 | OK |  |  |
| 339 | goodheart_castle | settlement | 13 | minor | rect patches |  |
| 340 | stonebrook | wilderness | 13 | minor | olive pond |  |
| 341 | stonebrook | wilderness | 13 | minor | rect patches |  |
| 342 | stonebrook | wilderness | 13 | OK |  |  |
| 343 | stonebrook | wilderness | 13 | defect | play camera inside pine |  |
| 344 | stonebrook | wilderness | 13 | minor | pine branches over camera |  |
| 345 | stonebrook | wilderness | 13 | defect | play camera inside pine |  |
| 346 | stonebrook | wilderness | 13 | minor | pine branch in view |  |
| 347 | stonebrook | wilderness | 13 | minor | cyan water-colour seam square (over) | cards 1 |
| 348 | east_wilds | wilderness | 13 | defect | play camera inside pine canopy |  |
| 349 | east_wilds | wilderness | 13 | OK |  |  |
| 350 | east_wilds | wilderness | 13 | defect | play view against cobbler booth + pixelated wood card at right | cards 4 |
| 351 | east_wilds | wilderness | 13 | OK |  |  |
| 352 | east_wilds | wilderness | 13 | minor | olive water-colour seam rectangle; tile-shaped sand |  |
| 353 | west_seas | sea | 13 | OK |  |  |
| 354 | west_seas | sea | 13 | OK |  |  |
| 355 | west_seas | sea | 13 | OK |  |  |
| 356 | west_seas | sea | 13 | minor | tile-shaped sand islands |  |
| 357 | west_seas | sea | 14 | OK |  |  |
| 358 | west_seas | sea | 14 | OK |  |  |
| 359 | west_seas | sea | 14 | OK |  |  |
| 363 | murkwood | wilderness | 14 | defect | play camera inside pine |  |
| 364 | murkwood | wilderness | 14 | minor | script marker in audit (not seen at this camera) | grey default-material prims 1, script markers 1 |
| 365 | murkwood | wilderness | 14 | OK |  |  |
| 366 | murkwood | wilderness | 14 | minor | pine near camera | cards 4 |
| 367 | murkwood | wilderness | 14 | OK |  |  |
| 368 | goodheart_castle | settlement | 14 | defect | castle wall: pixelated stone-brick card/texture (story path) | cards 2 |
| 369 | goodheart_castle | settlement | 14 | defect | castle wall pixelated (story path) | cards 2 |
| 370 | goodheart_castle | settlement | 14 | defect | castle wall pixelated, camera against it | cards 1 |
| 371 | goodheart_castle | settlement | 14 | minor | rect patches |  |
| 372 | goodheart_castle | settlement | 14 | minor | olive pond |  |
| 373 | stonebrook | wilderness | 14 | minor | rect patches |  |
| 374 | stonebrook | settlement | 14 | minor | rect patches | cards 8 |
| 375 | stonebrook | settlement | 14 | OK |  |  |
| 376 | stonebrook | settlement | 14 | OK |  | grey default-material prims 1, script markers 1 |
| 377 | stonebrook | settlement | 14 | OK |  |  |
| 378 | stonebrook | settlement | 14 | minor | cyan/olive river colour seam |  |
| 379 | stonebrook | wilderness | 14 | minor | cyan/olive river colour seam |  |
| 380 | east_wilds | wilderness | 15 | minor | olive river, pine near camera |  |
| 381 | east_wilds | wilderness | 15 | minor | olive river with cyan seam corner |  |
| 382 | east_wilds | wilderness | 15 | minor | tile-shaped sand/sea (recaptured) |  |
| 383 | east_wilds | wilderness | 15 | minor | tile-shaped sand/sea maze |  |
| 384 | koka_isle | wilderness | 15 | minor | tile-shaped sand/sea |  |
| 389 | west_seas | sea | 15 | OK |  |  |
| 390 | west_seas | sea | 15 | OK |  |  |
| 391 | west_seas | sea | 15 | OK |  |  |
| 395 | murkwood | wilderness | 15 | defect | huge pixelated red/white chest card | cards 1 |
| 396 | murkwood | wilderness | 15 | OK |  |  |
| 397 | murkwood | wilderness | 15 | OK |  | grey default-material prims 1, script markers 1, cards 5 |
| 398 | murkwood | wilderness | 15 | OK |  |  |
| 399 | murkwood | wilderness | 15 | minor | castle tower pixel-brick texture | cards 1 |
| 400 | goodheart_castle | settlement | 15 | defect | castle wall pixelated card (story path) | cards 2 |
| 401 | goodheart_castle | settlement | 15 | defect | castle wall huge pixel card fills right half (story path) | cards 1 |
| 402 | goodheart_castle | settlement | 15 | not captured | (teleport refused, shows 102) | not captured |
| 403 | goodheart_castle | settlement | 15 | minor | rect patches |  |
| 404 | goodheart_castle | settlement | 15 | OK |  | grey default-material prims 1, script markers 2, cards 4 |
| 405 | stonebrook | wilderness | 15 | OK |  | cards 1 |
| 406 | stonebrook | settlement | 15 | OK |  |  |
| 407 | stonebrook | settlement | 16 | OK |  | coplanar 86 |
| 408 | stonebrook | settlement | 16 | OK |  | grey default-material prims 1, script markers 1, cards 6 |
| 409 | stonebrook | settlement | 16 | defect | play camera inside huge blurry pixel card next to 3D cottage (Stonebrook, story path) | cards 11 |
| 410 | stonebrook | settlement | 16 | minor | cyan/olive water seam |  |
| 411 | stonebrook | wilderness | 16 | minor | olive pond |  |
| 412 | east_wilds | wilderness | 16 | minor | olive river |  |
| 413 | east_wilds | wilderness | 16 | minor | cyan/olive seam |  |
| 414 | east_wilds | wilderness | 16 | minor | tile-shaped sand |  |
| 415 | east_wilds | wilderness | 16 | minor | tile-shaped sand |  |
| 416 | koka_isle | wilderness | 16 | minor | tile-shaped sand | cards 1 |
| 421 | west_seas | sea | 16 | OK |  |  |
| 422 | west_seas | sea | 16 | OK |  |  |
| 423 | west_seas | sea | 16 | minor | olive/cyan sea seam at edge |  |
| 424 | kernsin_wilds | wilderness | 16 | defect | sea drawn olive (pond colour) next to cyan sea: seam across screen |  |
| 425 | kernsin_wilds | wilderness | 16 | minor | tile-shaped sand |  |
| 426 | kernsin_wilds | wilderness | 16 | minor | olive water |  |
| 427 | murkwood | wilderness | 16 | minor | olive water |  |
| 428 | murkwood | wilderness | 16 | minor | olive water |  |
| 429 | murkwood | wilderness | 16 | minor | olive water |  |
| 430 | murkwood | wilderness | 16 | minor | rect patches |  |
| 431 | murkwood | wilderness | 17 | minor | rect patches |  |
| 432 | terris_wilds | wilderness | 17 | minor | castle wall pixel-brick texture; well ok | cards 1 |
| 433 | terris_wilds | wilderness | 17 | minor | castle wall pixel-brick texture | cards 1 |
| 434 | terris_wilds | wilderness | 17 | OK |  |  |
| 435 | terris_wilds | wilderness | 17 | OK |  |  |
| 436 | terris_wilds | wilderness | 17 | minor | olive river |  |
| 437 | stonebrook | wilderness | 17 | OK |  | cards 8 |
| 438 | stonebrook | settlement | 17 | OK |  |  |
| 439 | stonebrook | settlement | 17 | minor | capture point inside Dink's house body: camera in dark interior (check walk-in) | dark 0.046 |
| 440 | stonebrook | settlement | 17 | defect | huge pixelated card (bark/rock) over the play view, Stonebrook (story path) | cards 6 |
| 441 | stonebrook | settlement | 17 | OK |  | cards 8 |
| 442 | stonebrook | settlement | 17 | minor | rect patches | cards 17 |
| 443 | stonebrook | wilderness | 17 | OK |  |  |
| 444 | east_wilds | wilderness | 17 | OK |  |  |
| 445 | east_wilds | wilderness | 17 | minor | rect patches |  |
| 446 | east_wilds | wilderness | 17 | OK |  | cards 1 |
| 447 | east_wilds | wilderness | 17 | OK |  |  |
| 448 | koka_isle | wilderness | 17 | minor | olive water rectangle over cyan sea (seam) | cards 8 |
| 453 | west_seas | sea | 17 | OK |  |  |
| 454 | west_seas | sea | 17 | OK |  |  |
| 455 | west_seas | sea | 18 | minor | olive rectangle in cyan sea (seam) |  |
| 456 | kernsin_wilds | wilderness | 18 | defect | olive trapezoid sheet over cyan sea (seam), visible from shore |  |
| 457 | kernsin_wilds | wilderness | 18 | minor | olive/cyan seam corner |  |
| 458 | kernsin_wilds | wilderness | 18 | minor | blue flower ring at feet (card?) | cards 13 |
| 459 | kernsin_wilds | wilderness | 18 | minor | rect patches |  |
| 460 | kernsin_wilds | wilderness | 18 | minor | rect patches |  |
| 461 | kernsin_wilds | wilderness | 18 | minor | olive water, tile-shaped edges |  |
| 462 | kernsin_wilds | wilderness | 18 | minor | olive water, rect patches (recaptured) |  |
| 463 | terris_wilds | wilderness | 18 | minor | olive water |  |
| 464 | terris | settlement | 18 | minor | olive water, rect patches |  |
| 465 | terris | settlement | 18 | minor | olive river (known rim seam 465) |  |
| 466 | terris | settlement | 18 | minor | olive river |  |
| 467 | terris | settlement | 18 | minor | rect patches |  |
| 468 | terris | settlement | 18 | minor | right-angle river |  |
| 469 | stonebrook | wilderness | 18 | minor | right-angle olive water (recaptured) | cards 9 |
| 470 | stonebrook | wilderness | 18 | minor | right-angle olive river |  |
| 471 | stonebrook | wilderness | 18 | minor | right-angle olive pond (recaptured) |  |
| 472 | stonebrook | wilderness | 18 | minor | olive river (recaptured) |  |
| 473 | stonebrook | wilderness | 18 | minor | rect patches |  |
| 474 | stonebrook | wilderness | 18 | OK |  | cards 16 |
| 475 | stonebrook | wilderness | 19 | minor | olive river |  |
| 476 | east_wilds | wilderness | 19 | minor | olive river (recaptured) |  |
| 477 | east_wilds | wilderness | 19 | minor | olive river |  |
| 478 | east_wilds | wilderness | 19 | minor | olive/cyan seam |  |
| 479 | east_wilds | wilderness | 19 | minor | olive trapezoid over cyan sea |  |
| 480 | koka_isle | wilderness | 19 | defect | olive sheet over cyan sea across the Koka isle screen; red pixel bits | cards 4 |
| 485 | west_seas | sea | 19 | OK |  |  |
| 486 | west_seas | sea | 19 | OK |  |  |
| 487 | west_seas | sea | 19 | minor | olive seam corner |  |
| 488 | cast_camp | settlement | 19 | minor | olive seam at sea top |  |
| 489 | cast_camp | settlement | 19 | minor | tile-shaped cobble rectangle |  |
| 490 | cast_camp | settlement | 19 | minor | rect patches |  |
| 491 | kernsin_wilds | wilderness | 19 | minor | rect patches |  |
| 492 | kernsin_wilds | wilderness | 19 | OK |  |  |
| 493 | kernsin_wilds | wilderness | 19 | minor | rect patches |  |
| 494 | kernsin_wilds | wilderness | 19 | minor | olive pond |  |
| 495 | terris_wilds | wilderness | 19 | minor | pine sapling at camera |  |
| 496 | terris | settlement | 19 | minor | rect patches |  |
| 497 | terris | settlement | 19 | OK |  | cards 8 |
| 498 | terris | settlement | 19 | minor | capture point inside a Terris house (camera against inner walls) | cards 10 |
| 499 | terris | settlement | 20 | OK |  | cards 4 |
| 500 | terris | settlement | 20 | minor | olive pond | cards 6 |
| 501 | windemere | settlement | 20 | defect | Windemere cottage wall pixelated card with dithered edge beside 3D cottages (story path) | cards 10 |
| 502 | windemere | settlement | 20 | defect | play camera inside pine |  |
| 503 | windemere | settlement | 20 | OK |  |  |
| 504 | windemere | settlement | 20 | OK |  | cards 5 |
| 505 | windemere | settlement | 20 | minor | rect patches | cards 9 |
| 506 | windemere | settlement | 20 | minor | capture point inside a Windemere long house (camera against inner walls) | cards 4 |
| 507 | windemere_wilds | wilderness | 20 | minor | olive river (recaptured) |  |
| 508 | east_wilds | wilderness | 20 | minor | olive river |  |
| 509 | east_wilds | wilderness | 20 | OK |  |  |
| 510 | east_wilds | wilderness | 20 | minor | rect patches |  |
| 511 | east_wilds | wilderness | 20 | minor | olive/cyan seam |  |
| 512 | koka_isle | wilderness | 20 | minor | olive sheet over cyan sea (recaptured) | cards 11 |
| 516 | west_seas | sea | 20 | OK |  |  |
| 517 | west_seas | sea | 20 | OK |  |  |
| 518 | west_seas | sea | 20 | OK |  |  |
| 519 | west_seas | sea | 20 | OK |  |  |
| 520 | cast_camp | settlement | 20 | minor | rect patches |  |
| 521 | cast_camp | settlement | 20 | minor | red pixel blob beside Dink (card?) | cards 2 |
| 522 | cast_camp | settlement | 21 | minor | rect patches |  |
| 523 | kernsin_wilds | wilderness | 21 | minor | rect patches |  |
| 524 | kernsin_wilds | wilderness | 21 | minor | rect patches |  |
| 525 | kernsin_wilds | wilderness | 21 | minor | tree trunk near camera |  |
| 526 | kernsin_wilds | wilderness | 21 | minor | rect patches |  |
| 527 | terris_wilds | wilderness | 21 | minor | rect patches |  |
| 528 | terris | settlement | 21 | minor | rect patches |  |
| 529 | terris | settlement | 21 | OK |  |  |
| 530 | terris | settlement | 21 | defect | camera against pixelated cottage card (thatch + stone pixels), Terris (story path) | cards 6 |
| 531 | terris | settlement | 21 | OK |  |  |
| 532 | terris | settlement | 21 | minor | pixelated stone card corner at right | cards 7 |
| 533 | windemere | settlement | 21 | minor | wood pixel card at left; olive water | cards 2 |
| 534 | windemere | settlement | 21 | OK |  | cards 1 |
| 535 | windemere | settlement | 21 | defect | play camera inside pine | cards 2 |
| 536 | windemere | settlement | 21 | defect | red/white pixel chest card at right; unknown yellow blob filling foreground; Windemere square (story path) | cards 32 |
| 537 | windemere | settlement | 21 | OK |  | cards 11 |
| 538 | windemere | settlement | 21 | OK |  | cards 6 |
| 539 | windemere_wilds | wilderness | 21 | minor | straight-edged olive pond | cards 3 |
| 540 | east_wilds | wilderness | 21 | minor | olive pond |  |
| 541 | east_wilds | wilderness | 21 | OK |  |  |
| 542 | east_wilds | wilderness | 22 | minor | rect patches |  |
| 543 | east_wilds | wilderness | 22 | minor | olive/cyan sea seam |  |
| 544 | koka_isle | wilderness | 22 | minor | olive sheet over sea at Koka bridge | cards 2 |
| 548 | west_seas | sea | 22 | OK |  |  |
| 549 | west_seas | sea | 22 | OK |  |  |
| 550 | kernsin_wilds | wilderness | 22 | OK |  |  |
| 551 | kernsin_wilds | wilderness | 22 | minor | tile-shaped sand |  |
| 552 | kernsin | settlement | 22 | minor | rect patches |  |
| 553 | kernsin | settlement | 22 | OK |  |  |
| 554 | kernsin | settlement | 22 | OK |  |  |
| 555 | kernsin | settlement | 22 | OK |  |  |
| 556 | kernsin | settlement | 22 | minor | rect patches |  |
| 557 | kernsin | wilderness | 22 | defect | red/white pixel chest card | cards 1 |
| 558 | kernsin | wilderness | 22 | minor | rect patches |  |
| 559 | terris_wilds | wilderness | 22 | minor | rect patches |  |
| 560 | terris_wilds | wilderness | 22 | defect | play camera inside pine |  |
| 561 | terris_wilds | wilderness | 22 | OK |  |  |
| 562 | terris_wilds | wilderness | 22 | minor | rect patches | cards 1 |
| 563 | terris_wilds | wilderness | 22 | minor | rect patches |  |
| 564 | terris_wilds | wilderness | 22 | OK |  | cards 1 |
| 565 | windemere | settlement | 23 | minor | olive pond, right-angle shape |  |
| 566 | windemere | settlement | 23 | OK |  |  |
| 567 | windemere | settlement | 23 | minor | dashed dirt strip |  |
| 568 | windemere | settlement | 23 | OK |  | cards 3 |
| 569 | windemere | settlement | 23 | OK |  |  |
| 570 | windemere | settlement | 23 | minor | right-angle olive pond | cards 3 |
| 571 | windemere_wilds | wilderness | 23 | minor | right-angle olive pond |  |
| 572 | east_wilds | wilderness | 23 | minor | olive water |  |
| 573 | east_wilds | wilderness | 23 | OK |  |  |
| 574 | east_wilds | wilderness | 23 | OK |  |  |
| 575 | east_wilds | wilderness | 23 | minor | olive/cyan seam |  |
| 576 | koka_isle | wilderness | 23 | defect | olive sheet over cyan sea across screen (Koka) |  |
| 580 | west_seas | sea | 23 | OK |  |  |
| 581 | west_seas | sea | 23 | OK |  |  |
| 582 | kernsin_wilds | wilderness | 23 | OK |  |  |
| 583 | kernsin_wilds | wilderness | 23 | minor | rect patches | cards 2 |
| 584 | kernsin | settlement | 23 | OK |  |  |
| 585 | kernsin | settlement | 23 | OK |  | cards 7 |
| 586 | kernsin | settlement | 23 | defect | fountain water = blue pixel sprite card spray beside 3D basin (Kernsin town) | grey default-material prims 1, script markers 1, cards 2 |
| 587 | kernsin | settlement | 23 | OK |  | cards 5 |
| 588 | kernsin | settlement | 24 | OK |  |  |
| 589 | kernsin | wilderness | 24 | minor | rect patches |  |
| 590 | kernsin | wilderness | 24 | defect | huge pixelated boulder cards blocking the road fill the play view (Kernsin road) | cards 7 |
| 591 | terris_wilds | wilderness | 24 | minor | rect patches |  |
| 592 | terris_wilds | wilderness | 24 | OK |  |  |
| 593 | terris_wilds | wilderness | 24 | minor | rect patches |  |
| 594 | terris_wilds | wilderness | 24 | minor | rect patches |  |
| 595 | terris_wilds | wilderness | 24 | minor | rect patches |  |
| 596 | terris_wilds | wilderness | 24 | minor | rect patches |  |
| 597 | terris_wilds | wilderness | 24 | minor | right-angle olive pond |  |
| 598 | terris_wilds | wilderness | 24 | minor | rect patches |  |
| 599 | windemere_wilds | wilderness | 24 | minor | bush right at the camera | cards 3 |
| 600 | windemere_wilds | wilderness | 24 | OK |  | cards 1 |
| 601 | windemere_wilds | wilderness | 24 | defect | pixelated dark boulder card (stone circle centre) beside barrel | cards 1 |
| 602 | windemere_wilds | wilderness | 24 | minor | olive water |  |
| 603 | windemere_wilds | wilderness | 24 | minor | olive water |  |
| 604 | east_wilds | wilderness | 24 | minor | olive water | cards 4 |
| 605 | east_wilds | wilderness | 24 | minor | rect patches |  |
| 606 | east_wilds | wilderness | 24 | minor | rect patches |  |
| 607 | east_wilds | wilderness | 24 | minor | olive/cyan seam |  |
| 608 | koka_isle | wilderness | 25 | defect | olive sheet over cyan sea (Koka) |  |
| 611 | west_seas | sea | 25 | OK |  |  |
| 612 | west_seas | sea | 25 | OK |  |  |
| 613 | west_seas | sea | 25 | OK |  |  |
| 614 | kernsin_wilds | wilderness | 25 | OK |  |  |
| 615 | kernsin_wilds | wilderness | 25 | minor | tile-shaped sand |  |
| 616 | kernsin | settlement | 25 | minor | rect patches |  |
| 617 | kernsin | settlement | 25 | defect | camera against pixelated cottage cards (Kernsin) | cards 4 |
| 618 | kernsin | settlement | 25 | minor | pixelated cottage card corner | cards 6 |
| 619 | kernsin | settlement | 25 | defect | camera inside blurry pixel cottage card (Kernsin) | cards 6 |
| 620 | kernsin | settlement | 25 | OK |  |  |
| 621 | kernsin | wilderness | 25 | OK |  |  |
| 622 | kernsin | wilderness | 25 | minor | rect patches |  |
| 623 | terris_wilds | wilderness | 25 | OK |  |  |
| 624 | terris_wilds | wilderness | 25 | minor | rect patches |  |
| 625 | terris_wilds | wilderness | 25 | minor | dark pixel card at left edge | cards 1 |
| 626 | terris_wilds | wilderness | 25 | minor | rect patches |  |
| 627 | terris_wilds | wilderness | 25 | minor | rect patches |  |
| 628 | terris_wilds | wilderness | 25 | minor | olive water |  |
| 629 | terris_wilds | wilderness | 25 | minor | right-angle olive water (recaptured) |  |
| 630 | terris_wilds | wilderness | 26 | minor | rect patches |  |
| 631 | windemere_wilds | wilderness | 26 | minor | rect patches |  |
| 632 | windemere_wilds | wilderness | 26 | OK |  | cards 2 |
| 633 | windemere_wilds | wilderness | 26 | minor | blue pixel bits at feet; known rim seam 633 | cards 15 |
| 634 | windemere_wilds | wilderness | 26 | minor | right-angle olive river | cards 3 |
| 635 | windemere_wilds | wilderness | 26 | minor | olive water (recaptured) |  |
| 636 | east_wilds | wilderness | 26 | minor | olive river | cards 2 |
| 637 | east_wilds | wilderness | 26 | minor | rect patches |  |
| 638 | east_wilds | wilderness | 26 | minor | rect patches, tile-shaped sand |  |
| 639 | east_wilds | wilderness | 26 | minor | tile-shaped sand/sea |  |
| 640 | koka_isle | wilderness | 26 | minor | olive sheet seam over sea |  |
| 646 | goblin_sanctuary | settlement | 26 | OK |  |  |
| 647 | goblin_sanctuary | settlement | 26 | OK |  |  |
| 648 | goblin_sanctuary | settlement | 26 | minor | rect patches | cards 1 |
| 649 | goblin_sanctuary | settlement | 26 | minor | rect patches |  |
| 650 | south_coast | wilderness | 26 | OK |  |  |
| 651 | south_coast | wilderness | 26 | minor | rect patches |  |
| 652 | south_coast | wilderness | 26 | minor | rect patches | cards 3 |
| 653 | south_coast | wilderness | 26 | minor | rect patches |  |
| 654 | south_coast | wilderness | 26 | minor | rect patches |  |
| 655 | terris_wilds | wilderness | 27 | minor | rect patches |  |
| 656 | terris_wilds | wilderness | 27 | minor | rect patches | cards 2 |
| 657 | terris_wilds | wilderness | 27 | minor | rect patches |  |
| 658 | terris_wilds | wilderness | 27 | minor | rect patches | cards 5 |
| 659 | terris_wilds | wilderness | 27 | OK |  |  |
| 660 | terris_wilds | wilderness | 27 | minor | olive river, rect patches | cards 4 |
| 661 | terris_wilds | wilderness | 27 | minor | olive water (recaptured) |  |
| 662 | terris_wilds | wilderness | 27 | minor | dashed dirt strip |  |
| 663 | windemere_wilds | wilderness | 27 | minor | orange pixel arrow cards in flight | cards 8 |
| 664 | windemere_wilds | wilderness | 27 | minor | rect patches |  |
| 665 | windemere_wilds | wilderness | 27 | minor | olive water | cards 1 |
| 666 | windemere_wilds | wilderness | 27 | minor | cyan/olive water seam |  |
| 667 | windemere_wilds | wilderness | 27 | minor | rect patches |  |
| 668 | east_wilds | wilderness | 27 | minor | tile-shaped sand |  |
| 669 | east_wilds | wilderness | 27 | minor | tile-shaped sand |  |
| 670 | east_wilds | wilderness | 27 | minor | olive/cyan seam |  |
| 671 | east_wilds | wilderness | 27 | minor | olive sheet over sea around islet; red chest card | cards 2 |
| 672 | koka_isle | wilderness | 27 | minor | black pixel bits on sand | cards 9 |
| 678 | goblin_sanctuary | settlement | 27 | OK |  |  |
| 679 | goblin_sanctuary | settlement | 27 | OK |  |  |
| 680 | goblin_sanctuary | settlement | 28 | defect | goblin hut = pixelated thatched hut card with blue pixels (goblin sanctuary, story path) | cards 6 |
| 681 | goblin_sanctuary | settlement | 28 | defect | camera inside pixelated goblin hut card | cards 1 |
| 682 | south_coast | wilderness | 28 | OK |  |  |
| 683 | south_coast | wilderness | 28 | minor | rect patches |  |
| 684 | south_coast | wilderness | 28 | minor | rect patches |  |
| 685 | south_coast | wilderness | 28 | minor | rect patches | cards 1 |
| 686 | south_coast | wilderness | 28 | minor | rect patches |  |
| 687 | terris_wilds | wilderness | 28 | minor | rect patches |  |
| 688 | terris_wilds | wilderness | 28 | minor | right-angle olive pond | cards 2 |
| 689 | terris_wilds | wilderness | 28 | minor | right-angle olive pond |  |
| 690 | terris_wilds | wilderness | 28 | minor | right-angle olive pond |  |
| 691 | terris_wilds | wilderness | 28 | minor | olive river |  |
| 692 | terris_wilds | wilderness | 28 | minor | olive river |  |
| 693 | terris_wilds | wilderness | 28 | defect | pixelated tree card (leaves) at top right over the river | cards 5 |
| 694 | terris_wilds | wilderness | 28 | minor | square dirt patch | cards 3 |
| 695 | windemere_wilds | wilderness | 28 | minor | rect patches | cards 11 |
| 696 | windemere_wilds | wilderness | 28 | minor | rect patches | cards 3 |
| 697 | windemere_wilds | wilderness | 28 | minor | tile-shaped pond (recaptured) |  |
| 698 | windemere_wilds | wilderness | 28 | minor | tile-shaped water outline |  |
| 699 | windemere_wilds | wilderness | 28 | OK |  | cards 2 |
| 700 | koka_isle | wilderness | 29 | minor | tile-shaped sand/sea | cards 3 |
| 701 | koka_isle | wilderness | 29 | minor | tile-shaped sand/sea | cards 2 |
| 702 | koka_isle | wilderness | 29 | minor | olive square sheet in cyan sea |  |
| 703 | koka_isle | wilderness | 29 | minor | olive square sheet in sea |  |
| 704 | koka_isle | wilderness | 29 | minor | olive square sheet in sea |  |
| 710 | goblin_sanctuary | settlement | 29 | OK |  |  |
| 711 | goblin_sanctuary | settlement | 29 | OK |  | cards 2 |
| 712 | goblin_sanctuary | settlement | 29 | OK |  | cards 5 |
| 713 | goblin_sanctuary | settlement | 29 | OK |  | cards 3 |
| 714 | south_coast | wilderness | 29 | OK |  |  |
| 715 | south_coast | wilderness | 29 | OK |  | cards 1 |
| 716 | south_coast | wilderness | 29 | minor | rect patches | cards 2 |
| 717 | south_coast | wilderness | 29 | minor | rect patches |  |
| 718 | south_coast | wilderness | 29 | minor | rect patches |  |
| 719 | south_coast | wilderness | 29 | minor | rect patches |  |
| 720 | south_coast | wilderness | 29 | minor | olive sea (south coast drawn as pond colour) |  |
| 721 | south_coast | wilderness | 29 | minor | olive sea |  |
| 722 | south_coast | wilderness | 29 | minor | olive sea |  |
| 723 | south_coast | wilderness | 29 | minor | olive sea |  |
| 724 | south_coast | wilderness | 29 | minor | olive sea |  |
| 725 | windemere_wilds | wilderness | 30 | minor | olive water |  |
| 726 | windemere_wilds | wilderness | 30 | minor | tile-shaped sand/sea |  |
| 727 | koka_isle | wilderness | 30 | minor | tile-shaped sand |  |
| 728 | koka_isle | wilderness | 30 | minor | tile-shaped sand |  |
| 729 | koka_isle | wilderness | 30 | minor | tile-shaped sand/sea |  |
| 730 | koka_isle | wilderness | 30 | minor | tile-shaped sand/sea |  |
| 731 | koka_isle | wilderness | 30 | minor | tile-shaped sand/sea |  |
| 732 | koka_isle | wilderness | 30 | minor | tile-shaped sand/sea |  |
| 733 | koka_isle | wilderness | 30 | minor | tile-shaped sand/sea |  |
| 734 | koka_isle | wilderness | 30 | defect | camera inside pixelated cottage card (Koka, cobbler route S734_P31) | cards 6 |
| 735 | koka_isle | wilderness | 30 | OK |  |  |
| 736 | koka_isle | wilderness | 30 | OK |  |  |
| 742 | goblin_sanctuary | settlement | 30 | minor | tile-shaped sand/sea |  |
| 743 | goblin_sanctuary | settlement | 30 | minor | tile-shaped sand |  |
| 744 | goblin_sanctuary | settlement | 30 | minor | olive/green water edge |  |
| 745 | goblin_sanctuary | settlement | 30 | OK |  |  |
| 746 | south_coast | wilderness | 30 | OK |  |  |
| 747 | south_coast | wilderness | 30 | defect | chest_small pixel card fills the play view (recaptured) | cards 1 |
| 748 | south_coast | wilderness | 30 | OK | (recaptured) | cards 2 |
| 749 | south_coast | wilderness | 30 | OK |  |  |
| 750 | south_coast | wilderness | 31 | minor | olive sea |  |
| 751 | south_coast | wilderness | 31 | minor | olive sea |  |
| 752 | south_coast | wilderness | 31 | minor | olive sea |  |
| 753 | south_coast | wilderness | 31 | minor | olive sea |  |
| 754 | south_coast | wilderness | 31 | minor | olive sea |  |
| 755 | south_coast | wilderness | 31 | minor | olive sea |  |
| 756 | south_coast | wilderness | 31 | minor | olive sea |  |
| 757 | windemere_wilds | wilderness | 31 | minor | olive sea, cyan seam |  |
| 758 | windemere_wilds | wilderness | 31 | minor | olive/cyan seam |  |
| 759 | koka_isle | wilderness | 31 | OK |  |  |
| 760 | koka_isle | wilderness | 31 | minor | tile-shaped sand | cards 3 |
| 761 | koka_isle | wilderness | 31 | minor | tile-shaped sand |  |
| 762 | koka_isle | wilderness | 31 | minor | goblin hut pixel-card edge at left | cards 8 |
| 763 | koka_isle | wilderness | 31 | defect | goblin hut pixelated card at camera (blue pixels) | cards 6 |
| 764 | koka_isle | wilderness | 31 | minor | goblin hut card blue pixels; pixel duck card in sky | cards 7 |
| 765 | koka_isle | wilderness | 31 | OK |  |  |
| 766 | koka_isle | wilderness | 31 | defect | pixelated dark card at left (well/mine?) next to 3D well | cards 1 |
| 767 | koka_isle | wilderness | 31 | defect | play camera inside pine |  |
| 768 | koka_isle | wilderness | 31 | defect | play camera inside pine |  |
| 013 | snow_castle | wilderness | 31 | minor | snow castle: bare white plane only |  |
| 014 | snow_castle | wilderness | 32 | minor | bare snow plane; dirt path stripes |  |
| 015 | snow_castle | wilderness | 32 | defect | snow castle wall: pixelated brick wall card with dither checker band | cards 3 |
| 016 | snow_castle | wilderness | 32 | defect | snow castle wall pixelated | cards 3 |
| 017 | snow_castle | wilderness | 32 | defect | snow castle wall pixelated | cards 2 |
| 018 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 045 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 046 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 047 | snow_castle | wilderness | 32 | minor | bare snow plane, hard snow/ice colour block | cards 2 |
| 048 | snow_castle | wilderness | 32 | defect | snow castle wall pixelated, dither band | cards 2 |
| 049 | snow_castle | wilderness | 32 | defect | snow castle wall pixelated | cards 2 |
| 050 | snow_castle | wilderness | 32 | minor | castle tower pixelated | cards 1 |
| 077 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 078 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 079 | snow_castle | wilderness | 32 | defect | snow castle wall pixelated, dither band | cards 2 |
| 080 | snow_castle | wilderness | 32 | defect | snow castle wall pixelated | cards 5 |
| 081 | snow_castle | wilderness | 32 | minor | castle wall corner pixelated |  |
| 082 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 109 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 110 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 111 | snow_castle | wilderness | 32 | minor | bare snow plane |  |
| 112 | snow_castle | wilderness | 33 | minor | dark spiky creature/prop card on snow | cards 1 |
| 113 | snow_castle | wilderness | 33 | minor | bare snow plane |  |
| 114 | snow_castle | wilderness | 33 | minor | bare snow plane |  |
| 143 | snow_castle | wilderness | 33 | minor | bare snow plane |  |

