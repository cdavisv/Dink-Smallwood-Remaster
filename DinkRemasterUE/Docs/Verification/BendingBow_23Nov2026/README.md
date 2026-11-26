# The bow that bends, its arrow and the quiver (art row AN-05, 23 November 2026)

DRAFT. **Seen in the running game on 23 November** (rendered work was allowed again that afternoon): the section "In-game look"
below has the frames. It was built before that from Blender Cycles renders on the CPU, with the game's parts assembled in Blender by
the same arithmetic the game runs, next to the 1997 pictures; those sheets (00 to 04) stay as the record of how it was judged.

## What 1997 shows (ref_1997_*.png, from `bin/dink/graphics/dink/bow/{idle,hit}/dir.ff`)

- Armed with a bow, Dink carries it with an arrow across it and wears a tall brown quiver of red-fletched arrows on his back, the
  feathers standing above his head (`ref_1997_bow_idle.png`, four directions, six pictures each).
- While the attack key is held the bow is upright at arm's length, the arrow level, and over six pictures the string comes back
  to his face while the stave bends from a shallow curve to a deep one (`ref_1997_bow_hit.png`).

## What master has

- One static bow mesh, strung and at rest, in the left hand. No arrow, no quiver. The string and limbs never move.
- NEVER LOOKED AT BEFORE, found here: the body clips `Bow_Draw` / `Bow_Release` were made before any bow was in the hand. With
  the bow placed by its row at the held last frame of `Bow_Draw`, the stave leaned 64 degrees from upright and pointed 52 degrees at
  the sky, and the string hand was 39 cm up the limb and 32 cm behind the grip (`00_before_draw_pose_master.jpg`, top row).

## What this draft makes

1. **The bow bends.** Each bow is cut into a middle part, six segments a limb and two string halves
   (`HeroWeapons/tools/build_bow_parts.py`; no new bake, the parts use the bow's own UVs and textures). `UDinkHeroBowSubsystem`
   turns each segment a little more than the one before so that the string, tied to both tips, keeps its length, and stretches the
   two string halves from the tips to the string hand.
2. **The string follows the hand**, not the bow's power: the body reaches full draw in 0.5 s, the power in 1.2 s.
3. **An arrow** (`SM_Hero_Arrow_PR`, 0.80 m, red vanes) rides on the string, its shaft past the left of the stave; it is away for
   0.45 s after a shot that left (1997: last power >= 100).
4. **A quiver** (`SM_Hero_Quiver_PR`) of eight red-fletched arrows on his back (bone `spine_03`) while a bow is armed.
5. **The draw pose is re-authored** so that the bow is upright (7 degree cant), points where Dink faces, the bow arm is nearly
   straight and the string fingers are ON the string's line, at the right cheek.

## Pictures (all Blender Cycles, CPU; the game's parts assembled by `bow_solve`'s arithmetic = `DinkHeroBow::Solve`)

| sheet | what it shows | what I see |
|---|---|---|
| `ref_1997_bow_hit.png`, `ref_1997_bow_idle.png` | the 1997 pictures: the draw in directions 2, 4, 6, 8 (six pictures each); the carried bow in four directions | the bow upright at arm's length, bending deeper as the string comes to his face; a level arrow with red feathers; a tall brown quiver on his back, a red plume of feathers above his head |
| `00_before_draw_pose_master.jpg` | MASTER: `Bow_Draw` with the one-piece bow placed by its row | the bow lies across his face pointing up and forward, the string hand beside the bow hand: the clip was made without a bow |
| `01_draw_1997_and_now.jpg` | 1997 direction 4 and 6 above six frames of the new draw, from his back side and his chest side, camera raised as in 1997 | reads as the same act: bow upright, limbs bending further each frame, the string a V to the hand at his cheek, the arrow level, the quiver's red feathers behind his head. Different from 1997: his bow is a short deep recurve, ours the kit's 1.30 m self bow (shallower at rest); 1997 crouches in the first two pictures, ours stands |
| `02_carried_1997_and_now.jpg` | 1997's four carried pictures; ours with draft #222's guard carry; ours on master alone | with #222: bow upright at his left side, arrow across it pointing forward, quiver and red plume over his shoulder, as 1997. On master alone the arrow points at the ground from a hanging hand: do not merge without #222. The plume is smaller than 1997's (which is as tall as his head): a first quiver with war-arrow feathers was thinner still and was rebuilt larger |
| `03_full_draw_close.jpg` | full draw close: bow hand, string hand, whole bow, the quiver on the back | the shaft lies on the bow hand's knuckle and the head stands clear ahead of it; the limb above the grip bends without a kink (six segments: with four there was a visible angle above the binding, rejected); the fingers hook the string beside the jaw, the red vanes just below it |
| `04_arrow_and_quiver_baked_meshes.jpg` | the game meshes with their baked textures (the kit's own review renders) | arrow: pale ash shaft, three red vanes bound at both ends, dark nock, steel leaf head. Quiver: dark brown leather tube with two darker bands, a stitched seam, eight arrows |

## In-game look, 23 November 2026

Captured offscreen in the running game on master `430fd81d2` + the integration tree of the effect drafts (copy `Saved/FableD`: it
holds draft #222 too, so the carried bow is on guard), 82 frames `Saved/PhotorealPass/fx4/F_*.png` (script `gen_capF.py`). No
console command holds the attack key, so the draw was played with `dink.Hero.Play Bow_Draw hold` at a fifth of the speed and
`dink.Hero.BowDraw -2` (the string follows the hand as it does while the bow is drawn).

| sheet | what it shows | what I see |
|---|---|---|
| `05_game_23nov_draw_full_draw_release.jpg` | row 1: the draw from his chest side, seven of fourteen frames; row 2: from his back side; row 3: full draw close, two frames of the release, the walk | the same act as the 1997 pictures: the bow comes up, the string hand takes the string, the limbs bend further each frame, the hand reaches the cheek, the arrow is level, the quiver's red feathers stand behind his head. After the release the bow is straight again |
| `06_game_23nov_close.jpg` | top: the quiver from behind, full draw from his back side and from his chest side; bottom: the string hand at the cheek, the quiver from behind in the carry, the carried bow from the front | the string runs into the closed string hand and the vanes lie under it at the jaw; the limbs bend smoothly, no joint shows; the arrow's head is clear of the bow hand. In THESE frames the quiver lay across the left side of his backpack (the game's Dink wears one; the Blender source used for the fitting does not), its foot partly in the pack's side pocket: moved afterwards, sheet 08 |
| `07_game_23nov_carried_and_fixed_draws.jpg` | carried from four sides, the quiver close, then the bow at fixed draws of 0, 14, 28, 42 and 54 cm (`dink.Hero.BowDraw <cm>`), the blue bow | carried upright in the left hand with the arrow across it (draft #222's carry); at the fixed draws the limbs bend and the string and arrow come back in step. Three of these cameras stand too close and cut his head off |

After the coordinator's review of these frames the quiver was moved clear of the backpack and captured again (three tries, the row is
`bows.worn` in `hero_weapons.json`): 10 cm straight back it hung free in the air beside the pack; further to his right it hung free
behind it; the third place lays it on the pack's outer face:

| sheet | what it shows | what I see |
|---|---|---|
| `08_game_23nov_quiver_on_the_backpack.jpg` | the quiver at its final place from behind, from behind left, from both sides, from above, and in the full draw | it lies across the outer face of the backpack, mouth at his right shoulder, its lower band on the pack; it no longer cuts into the pack and does not hang free. In the full draw the drawing elbow passes beside the feathers |

Named faults after the FIRST look (the strap and the fist are answered in the second look below): there was no strap; the string hand was a fist round the string, not three
hooked fingers; a real shot with the attack key held (the arrow leaving, the arrow away for 0.45 s) was not captured; the walk and
run with the quiver were seen only from the play camera's distance.

## Second in-game look, 23 November 2026 evening (art-fx-5): strap, string hand, the attack key

Captured offscreen in the game on master `fd676f34d` + this change (copy `Saved/FableD`, the integration tree of the effect
drafts, HeroWeapons kit and the two clips re-imported; capture section `sec_bow`, 117 frames, `Saved/PhotorealPass/fx5/W_*.png`).

| sheet | what it shows | what I see |
|---|---|---|
| `09_game_23nov_strapped_quiver_and_string_hand.jpg` | top: the carried bow from behind, the quiver's lower strap with its buckle, the strap running on to the pack, the quiver from the side; bottom: the clip at full draw, the string hand at the cheek, the string hand close, the same hand in the Blender source | **The quiver is lashed to the pack**: two dark straps go round the tube, each with a bronze buckle on the outer side, and their ends run on to the pack and end in it (the lower one across the pack's flap). **The string hand is no fist any more**: index, middle and ring finger are hooked on the string at their last joints, the knuckles nearly straight, the string leaving the finger tips towards the bow's tips; at the game's distance it reads as a hand drawing a string. Close up the fingers are still rather closed and the thumb lies on them |
| `10_game_23nov_attack_key_tap.jpg` | `dink.Attack` with the bow armed, slowed to a quarter: the frame before, the first frame from both sides, the next frame | **A held shot could still not be captured**: `dink.Attack` presses and lets go in the same tick (no console command holds the key), so the game aborts the draw at once. What it shows is a FAULT of a tap: for one frame the body stands in the draw pose (bow raised, bow arm out, string hand behind the head) while the bow is at rest, unbent, its string not at the hand; the next frame he stands again. No arrow was seen leaving |

What changed for this look: `rig.HOOK` and `Pose.hook` (state key `a_hook`, the string hand of `Bow_Draw` / `Bow_Release`;
`STRING_FINGERS` and `hero_weapons.json` `bows.string_fingers` are now the last joints of index, middle and ring finger), both
clips re-exported and re-imported; the quiver's source gained two lashing straps with buckles (`build_weapons.py quiver`), baked
and re-imported. Still open: a shot with the key held (needs `PlayerAttackPress` / `PlayerAttackRelease` behind a console
command, asked of the code side again); the tap's one frame of draw pose over a resting bow; the straps end inside the pack,
they do not go round it; no baldric.

## Rejected on the way

- A first draw pose with the string at the middle of the face: the string hand was inside the head. With the hand under the chin
  the wrist is so near its own shoulder that the elbow can only go up behind the neck (it read as an arm wrapped round the head).
  Kept: the right cheek, 12 cm to the chest side; there the forearm lies behind the arrow.
- A first quiver: a pale, featureless tube (it read as a cardboard roll). Darkened, two strap bands, a seam with stitches.
- A morphing or skinned bow: it needs an import path the kit importer does not have, and nothing of it could have been checked
  without a rendered game. Rigid parts can be checked by numbers (the test below).

## Headless proof

On master `430fd81d2` + the integration tree (the six open effect drafts and this one together, copy `Saved/FableD`): clean build,
0 warnings (`DinkHeroBow.cpp` and `DinkHeroBowTests.cpp` compile in the log); HeroWeapons kit import OK (8 materials, 38 modules,
0 warnings); `Bow_Draw` and `Bow_Release` imported. `Dink.Art.HeroBow.BendsWithTheDraw` ran there once: every check passed but one
bound of my own (at rest the arrow's point stands 9.9 cm aside, because the shaft leans 7 degrees round the stave over the 15 cm
brace height; the bound was 6 cm and is now 12). The engine's numbers equal the Blender tool's: bend 25.0 degrees at a 42 cm draw,
38.1 at 56 cm, string 126.36 of 126.36 cm at every draw. `Dink.Art.HeroWeapon` 2/2.

NOT yet done when this was pushed, results follow in a PR comment: the test with the corrected bound, and
`Dink.Art+Dink.Animation+Dink.Gameplay.Probe` with the twenty probe md5s on master `6e3d4f991`; this draft built ALONE on master.
CI source audits run locally on the branch: `check_public_paths.py` 0 flagged, `verify_sources.py --metadata-only` passes (the
asset ledger rows of the two clips carry their new hashes).

## NOT checked, and known weak points

- **In the game, not yet**: a shot with the attack key held; whether the string stays in the fingers at full speed (the subsystem
  reads the pose of the last evaluated frame: up to a frame behind, about 2 cm at the fastest part of the pull; at a fifth of the
  speed it held); the quiver in the run; the bow hand's wrist, cocked 32 degrees to the little-finger side at full draw and up to 47
  degrees for a few frames on the way.
- **The carried bow depends on draft #222** (closed hand and guard carry). On master alone the bow hangs level across the thighs
  from an open hand and the arrow points at the ground (`02_idle...`, second row); with #222 it is upright at his side with the
  arrow forward, as 1997 has it (third row). Merge #222 first or with this.
- **The quiver's straps end inside the pack** (two lashing straps with buckles, part of the quiver mesh); no baldric crosses the
  chest. A hero without the pack would show the strap ends hanging.
- The arrow count in the quiver never changes; item-b3's flame arrow is the same arrow (the flame is an effect).
- The release: the string is back in two frames; no vibration, no follow-through of the limbs.
- `Bow_Release` still starts from the full-draw pose whatever the draw was (as before): a tap shows a one-frame jump.
- The wrist key `a_dev` is new in the clip tool; only the two bow clips use it. All other clips export byte-identical poses
  (not re-exported here).

## 26 November 2026: rebased onto master 6dd60a8c8, held shot captured, headless proof (art-finish-1, Opus)

Mechanical only: the branch was replayed as one commit onto master `6dd60a8c8` (world scale on; only the `DinkRemasterUE/AGENTS.md`
section conflicted, both kept). No mesh, texture, clip or look was changed and none was judged here. **Frames for Fable.**

The held shot now exists (`dink.AttackHold [s]`, #252): art-fx-5's bow capture was run again with every `dink.Attack` tap
replaced by `dink.AttackHold 1.5` at 0.25 of the speed (the game logs "key down for 1.50 s, the bow is drawn" four times).

| sheet | what it shows |
|---|---|
| `11_frames_for_fable_26nov_held_shot.jpg` | the 1997 bow pictures, then the held shot from the play camera, the chest side, the back and wide, eight frames each from draw to release |
| `12_frames_for_fable_26nov_close.jpg` | the 1997 carried bow, then the carried bow and the quiver close, the held full draw (string hand, face) close, and the release at 0.2 of the speed |

Proof in copy `Saved/ArtFinish26Nov` (master `6dd60a8c8` + this change): clean editor build 0 warnings (`DinkHeroBow.cpp` and its
test compiled), game target 0 warnings, `Dink.Art.HeroBow+Dink.Art.HeroWeapon+Dink.Gameplay.Bow+Dink.Animation` 27/27,
`Dink.Gameplay.Probe` 29/29 with the twenty md5s equal to the world-scale table (Ch1 `ca319f4754` ... Ch20 `be78df8ac3`).
Kernel: no Oops. Draft #222 (closed hand and guard carry) is on master since 23 Nov.
