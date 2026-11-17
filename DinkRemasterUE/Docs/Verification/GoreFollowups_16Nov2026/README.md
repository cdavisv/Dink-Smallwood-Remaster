# Gore follow-ups to the starting-house remains (PR #175), 16 November 2026

Follow-ups the coordinator asked for when #175 was merged, plus the frames that were missing. Art, data and one importer
material kind; no gameplay code, no collision, no script change.

## What changed

| item | before | now |
|---|---|---|
| burn holes, picture 158 (`S001_P44`-`P49`, screen 1 vision 2) | a flat alpha-tested sheet; in the sun it rendered as a dark grey patch that read as spilled tar | holes burnt THROUGH: black void, the charred cut face of the far side of the planks, alligator char, ash, burn tongues, scorch fading into the boards, modelled splinters over the rim and charcoal lumps round it |
| `S001_P49` | lay on the floor about 1 m inside the south wall | stands on the room face of the south wall, left of the door, where the 1997 screen draws it: new upright asset `SM_Burn_Hole_Wall_PR` with soot climbing the plaster |
| the Mother, picture 355 (`S001_P34`, vision 1) | darker than 1997, pale rim round the pool | the brightest red on the screen, no pale rim |
| dead Dink, picture 436/16 (`S058_P06`) | stepped pool outline, pool beside him | bright pool under him with a natural outline |
| pools of soldier, merchant, girl, peasant, maiden, knight | pale damp fringe | no fringe, matt edge |
| the Joppa mother, picture 365 | no asset | `SM_Corpse_Mother_Joppa_PR` and its `families.json` row (shows nothing until killed people's pictures take family rows: code item C1 of the Master log) |

### Why the first burn holes were grey

The texture was already black. The kit's baked master material had no Specular pin, so Unreal used 0.5: four per cent of
the sun and the sky is reflected whatever the base colour is, and beside sunlit boards that is a mid grey. A void needs
specular 0, not only a black texture.

### How the hole is made

- `Corpses/tools/gore_sheets.py` `pit_sheet` (2048 px): the outline of the 1997 blotch (lobes and burn tongues); the void
  follows the cracks of the char (whole blocks have fallen in); `ORM.b` is the void mask (not metallic); the BC inside the
  void is what lies below the floor (black, a few dull embers: the brown-red heart of the 1997 picture); alpha is the cover
  and falls off through the scorch.
- `Corpses/tools/build_gore.py` `pit_card`: the card plus thin charred wedges standing over the rim and blocks of charcoal
  on and round it, all coloured from charred texels of the sheet. `wall=` stands it upright with a soot plume.
- `Scripts/import_town_exteriors.py`, baked material kind `pit` (master `M_Struct_Baked_Pit` in the kit's own folder,
  `/Game/Dink/Photoreal/Corpses`): inside the void the shader walks the view ray through the plank thickness (`PitWallUV`)
  and draws the charred cut face where the ray leaves the void, otherwise the BC of the void read `PitFloorUV` deeper;
  the void has specular 0; the cover is dithered per frame so the scorch fades instead of ending in a cut. Depths come from
  the kit row's `pit` block (`make_kit_manifest.py` passes it through).

### P49: on the wall, as 1997

The 1997 screen (`screen001_vision2_1997.png`) draws `S001_P49` on the front wall face left of the door, about 0.8 m
above the ground line. In the 3D room that wall is the south wall (modules `SouthWall_Left*`, centre line y 393595.98 cm,
38 cm thick, posts to 19 cm, plaster about 18 cm on the room side). The row now places `SM_Burn_Hole_Wall_PR` on that
face between two posts (`offset_cm [55.4, 95.2, 0]` from the placement's ground point: 55 cm towards the door so that
the holes sit in one plaster panel, 95 cm south onto the wall). The outside face of the wall is not dressed: screen 1 is
an interior sheet and nothing stands outside it.

## What I saw in the game (frames looked at by the author, a Fable 5.2 art agent)

Sheets (1997 picture at the left, nearest-neighbour, on the 1997 floor or ground colour; game frames beside it):

- `burn_holes.jpg`. Row 1 is BEFORE (capture c3 of this branch's first version): picture 158 on screen 1 vision 2 as
  a flat dark grey sheet in the sun. Rows 2-5 are AFTER, `S001_P44`-`P48`: a black void in sun and in shade; from the low
  camera the far side shows a lit band (the cut face of the planks) and the embers below shift against the rim as the
  view moves; the rim is matt charred wood broken into blocks with ash in some cracks; burn tongues run out as in the
  1997 picture; thin splinters stand over the rim, charcoal lies round it; the scorch fades into the boards. From the
  room cameras (`room2_from_north`) each reads as a hole in the floor, not as a stain. The 1997 outline and its
  brown-red heart are kept; the black area is not smaller than the picture's (unit test).
- `p49_wall.jpg`. `S001_P49` on the room face of the south wall between two posts, left of the door as seen from
  outside (1997's view), soot climbing above it. The wall is in shade, so the hole is a black blot with tongues and the
  rim detail does not show; that is also what the 1997 picture is.
- `bodies.jpg`. The frames that missed their subjects in the last capture:
  - Knight `S157_P04` (picture 275, screen 157; the old script aimed at `S731_P02`, which is picture 425): on his back in
    steel plate, the snapped shaft standing in his chest, the halberd head in the blood, pool and drops round him, no
    pale fringe. Against 275: body, shaft, head of the weapon and extent are there; the pool is a darker red than the
    picture's bright red, the halberd head is red where 1997 has blue steel, and close up the armour is smooth simple forms.
  - Dragon `S158_P07` (picture 216, screen 158): torn carcass with ribs and raw flesh, tail arched up, one wing up
    and one on the ground, pool and thrown pieces. Against 216 it is BELOW the picture: 1997 is mostly a red mass of
    open flesh with one grey-green wing; here the tan hide and two clean green wings dominate and the red is the
    smaller part. Not changed in this PR; it goes with the 212 remains (queue row GP-Q7).
  - Mother `S001_P34` (355) and dead Dink `S058_P06` (436/16): as accepted from capture c3 (brightest red on screen 1,
    no silver rim; bright pool under him with a natural outline).

## Still below the bar

- Burn holes in a macro view: the char blocks are a regular cell pattern and read as scales; the far cut face has one
  colour ramp and no texture of its own; the scorch fades by a per-frame dither that shows as fine grain when the
  camera is within about a metre. Nothing is cut out of the floor or wall mesh: seen from below floor level the card is flat.
- `S001_P49`: only the room face is dressed.
- Dragon 216: less red than the picture (above). Knight: pool darker than 275, smooth armour close up.
- The burnt room itself is unchanged apart from the holes, as in 1997 (burnt wall and floor modules exist in the
  StonebrookRuins kit; binding them would go beyond 1997 and needs a small state-swap hook: Master log, 15:45).

## Not checked

- Windows and Shipping builds; a packaged build (the kit folder is cooked with the rest of `/Game/Dink/Photoreal`).
- The dither with anti-aliasing methods other than the project's default (TSR).
- Screen 439's roof holes (pictures 158 frames 1-5 on the burnt cottage) do not use these meshes and were not touched.

## Frames and sheets

- `burn_holes.jpg`, `p49_wall.jpg`, `bodies.jpg`: capture c5 of 16 Nov 2026 17:40 (offscreen game, 1280 x 720,
  `Scripts/PhotorealQA/run_capture.sh`; private copy on master `ce4f7055` + this branch, built clean). The kit sources
  have not changed since; the same sources were imported again for the test run below.
- `c3_starting_house.jpg`, `c3_bodies.jpg`: capture c3 of 14:00 (the first version of this branch), kept for what was
  accepted from it (Mother, dead Dink, the pools of soldier, merchant, girl and peasant without the pale fringe). Its
  burn-hole frames are the rejected flat sheet.
- `screen001_vision2_1997.png`: the 1997 screen 1 in vision 2, drawn from the original data (reference only).
- Cameras: `dink.Goto <screen> <x> <y>` on the placement, `dink.Vision 1 2` with `&story` 5 for the burnt room,
  `dink.CalAnchor 0 0`, then `dink.CalCam` offsets (close `40 300 190`, low from the south `0 430 150`, macro
  `25 120 70`; the wall hole from inside `55 -330 150` looking at `55 100 95`). The play camera of an interior is above
  the roof, so the room is shown from cameras inside it.

## Tests (run on master `25ebcd0a` + this branch; private copy synced to it, `Intermediate` deleted, built clean in 131 s, world regenerated with `import_greybox.sh --region all --export` and `--region stonebrook`, corpse kit imported)

- `Scripts/test.sh Dink.Art`: 70/70 passed (5 with warnings).
- `Scripts/test.sh Dink.Gameplay.Probe`: 29/29 passed; all twenty chapter trace md5s equal the table of
  `Plugins/DinkParity/Docs/packaged_probe.md` on that master (the table of PR #141: Ch1 cc2e12fb5c, Ch2 bc267a0dfc,
  Ch3 bbd401167c, Ch4 8740518c57, Ch5 d987c043f6, Ch6 2df37e4a27, Ch7 a16d1d23b8, Ch8 764e9d330f, Ch9 dd1e2662fa,
  Ch10 23fd57dfdc, Ch11 f69c75447b, Ch12 3540ee8dd7, Ch13 ce2e8979e1, Ch14 20dc28bd96, Ch15 9f32c71ded,
  Ch16 f719041788, Ch17 c8b5b537a6, Ch18 e9b93c613a, Ch19 8c362880f0, Ch20 be28390b9d).
- Corpse kit import: `DINK TOWN IMPORT OK: 26 materials, 15 modules, 0 warnings`.
- `python3 -m unittest discover -s Scripts/tests`: 998 tests OK (in the private copy, 25ebcd0a + branch); new test
  `test_a_burn_hole_is_a_pit_with_a_void_and_its_depths` (kit rows ask for the `pit` material with its two depths; the
  void is black and not smaller than the black of picture 158).
- `Scripts/art_coverage.py` on the fresh export: final 5576, placeholder 879, cut 152 before and after (the burn holes
  and the Mother were bound already; the Joppa mother row has no placement).
- Rebased afterwards onto the master named in the PR; merged in between: #167 stairs, #150 shorelines, #194 tables and
  chests, #157 weapons, #196 creature one-shots. None of them touches this branch's importer hunk, the corpse kit,
  `stonebrook.json` or the probe table; shared with them are only `AGENTS.md`, `IMPORT.md` and `families.json`
  (own sections and rows). Not re-run on that tip.
