# Creature classes: the duck with its gore, slimes, pig (14 and 15 Nov 2026)

Second creature batch, on top of the pillbug (`Docs/Verification/CreatureClassBinding_13Nov2026/`). Five rows are added
to `classes` in `Content/Dink/Data/Art/creatures.json`: `duck`, `slime_blue`, `slime_green`, `slime_red`, `pig`.
Presentation only: collision, hardness, scripts, hits and the random stream are untouched; the layer is off in headless
runs. Class bodies add no collision; the 1997 creatures do not stop Dink either (they hurt on touch).

The first version of this batch was sent back because the blood covered less than the 1997 frames (the owner's rule:
keep all the original gore). Every sheet here therefore puts the 1997 frames (from `tools/dinkex/out/sprites`, enlarged,
on green) above frames of the running game.

## Result

| `art_coverage.py` (whole-world importer report, 6,607 rows) | master `0bf319c9` | after |
|---|---:|---:|
| final | 4,918 | 5,125 |
| placeholder | 1,537 | 1,330 |
| cut | 152 | 152 |

Class-bound placements: duck 91, blue slime 67, red slime 29, green slime 11, pig 8. The running game logs
`DINK CREATURE CLASS ART OK: 367 placements of 6 classes` (pillbug 160, pig 8, slime_blue 67, duck 92, slime_red 29,
slime_green 11).

## The 1997 gore, and what stands for it

The remaster's simulation keeps the duck's state (a headless flag, base walk 110) and draws nothing of what the 1997
frames paint. The presentation layer draws it, with its own random numbers:

| 1997 (dink.cpp, sprite sequences) | Here |
|---|---|
| First hit: a head sprite flies off along the duck's direction, lands in a pool and stays until the screen is left (duck_brain 12745-12775, sequences 121-129) | `SM_Duck_HeadFlying_PR` is thrown from the neck, spins, and lands as `SM_Duck_Head_PR` lying in a dark red pool (modelled, plus an 80 cm puddle decal) |
| The body runs on headless; every frame of sequences 111-119 shows blood spraying from the neck | `SK_Duck_Headless_PR` (bloody stump), a fountain of dark drops from the neck bone that keeps the body's speed, and stains along the way at uneven gaps |
| Second hit: the burst of sequence 164 (12728-12740): a ball of fine drops that starts small and dense, grows to 83 px across (beside a 31 px duck) and thins | 1,100 gobbets and 260 thrown drops that fill a ball growing to 2.1 m across (the duck is 0.77 m), rain down within the second the sequence lasts, 60 feathers that drift down and stay, and a stain |
| A killed slime leaves the splatter of sequences 661/663, 681/683, 701/703 | blobs of its gel and a splatter decal of its colour, 3.2 m across |
| A killed pig becomes the burst of sequence 164 (pig_brain 13367-13382) | the same ball, 1,800 gobbets and 400 drops, 2.1 m across, and a stain |

Only the kill path shows a burst: `UDinkGameplay::ProcessDamage` marks the sprite (`bBurstKill`) where the engine turns it
into sequence 164. A duck or pig that a script removes (`sp_active 0`, `sp_kill`) leaves no blood, as in 1997.
The 1997 burst leaves nothing on the ground when it ends; here a stain and the feathers stay until the screen is left.
The owner's order of 13 Nov 2026 for the duck was "have it spray a fountain from the neck".

## How it was captured

Offscreen game (`Scripts/PhotorealQA/run_capture.sh`) on master `0bf319c9` plus this branch, world regenerated, packages
re-imported. `Scripts/CreatureQA/make_scripts.py --hurt` / `--track`: a review blow (`dink.Hurt`, which goes through the
brain's own damage path) on a named placement, the game slowed to a tenth (a fifth for the gait strips), the camera aimed
at the creature again before every shot (`dink.CalAnchorOrigin`), because a duck covers 6 to 8.5 m a second.

## Sheets and what I see in them

- `gore_1_duck_head_and_fountain.jpg` (first blow): the head leaves the neck and flies off; the headless body runs on with a
  red stump; dark red drops spray from the neck and arc back over it, on earth (SCR_536) and on grass (SCR_374); stains
  lie along its path at uneven gaps. The spray is as large against the body as in 111/113 and denser. The drops read as
  dark red leaves close up (queued, CG-4).
- `gore_4_duck_head_in_pool.jpg`: the head lands and lies in a dark red pool three to four times its own size, as frame
  121/04 shows it (seen on bare earth, SCR_536; on grass the head landed outside the camera and was not seen).
- `gore_2_duck_burst.jpg` (second blow): a dense dark red ball of gobbets where the duck was, as wide as the duck at first,
  then two to three duck lengths across, falling and thinning over the second the sequence lasts, white feathers among
  it; on earth a large pool and feathers stay, on grass a faint stain and feathers. At or above the 1997 level. In the
  first frame on SCR_536 the gobbets are grey for one frame (the re-imported material compiling its shader on first use
  in an editor game; a cooked game has it compiled). The grey chequered cylinder is the unbound sprite the duck's death
  script makes (queued, CG-6).
- `gore_3_slime_and_pig.jpg`: the pig burst before (14 Nov: sparse pink beads, a heap low on the ground) and after: a
  red ball that grows to about 2 m and rains down, as dense in its middle frames as 164 and as wide; the droplets are
  still brighter red beads where 164 is maroon and black specks (queued, CG-1). The red slime's splatter before (a
  small orange-red blot) and after (a brown-red heap of gel on a terracotta splash about the size of the living slime,
  as 701/703 are), with the hero away from the slimes. Blue (SCR_633): a dark blue stain on the grass blades about the size of the slime, its gel hidden in the grass (below the scattered chunks of 661 in how much shows). A green slime that runs `en-slim` (SCR_546) now dies into the red-brown 701 as in 1997; it fell at the foot of a wall and is mostly hidden in that shot.
- `live_duck_and_pig.jpg`: the living duck white with legs stepping on the earth of the duck pen; the pig in the
  Stonebrook pen (origin row, muddy) and the class-bound farm pig on SCR_636 walking.

## Review of 15 Nov 2026: what was wrong and what was done

- **Gore packages missing from the branch** (`SM_BloodBlob`, `SM_Feather`, `M_BloodBlob`, `M_Feather`, the opaque slime
  colours): the class loader refuses a whole row when a gore asset is missing, so on a clean checkout no duck, pig or
  slime gore showed. All packages of the four folders are now committed, re-imported from the sources on this branch.
- **Burst on any removal**: the presenter burst for every class sprite that went inactive with a matching picture and
  brain. Now only for the kill path (see above); test `Dink.Art.CreatureClass.BurstOnlyOnAKillAndStainsReused`.
- **Gore instances cleared and re-added every frame**: they are moved in place now; only the difference in count is added
  or removed.
- **Blood trail**: a decal every 38 cm, and at the 96-stain cap one destroyed and one made per stain (about 20 a second;
  bug A13 is a crash in the decal pass). At the cap the oldest stain is moved now.
- **Pig burst lighter and pinker than 164, less solid in its middle frames** (parameters only, no new art): 1,800 gobbets
  of 5.5 cm (were 1,200 of 5.0), 400 drops, the ball's middle at 0.85 of its radius so that the ground no longer cuts its
  lower half, `M_BloodBlob` matt and saturated (roughness 0.62, specular 0.15; was 0.38 / 0.3, whose sunlit highlights
  read pink).
- **Slime splatter small and orange-red against 701/703** (parameters only): the splatter decals of all three colours
  are 3.2 m (were 2.3 m), their colour is pulled to the mean of the 1997 splatter sprite (ratio of the linear means,
  darkened a third for the remaster's sunlight) and the thin outer spatter is made solid (`decal_material(tint=,
  opacity_gain=)`); the red gel blobs are brown-red. `MI_Slime_Red_PR` uses `T_Slime_Red_Opaque_BC`.
- **The severed head in its pool was never captured**: it is now (sheet 4).

## Weaknesses that stay (new art queued in `doc/remaster/FABLE_ART_QUEUE.md`)

- Pig burst (CG-1): size, density and timing are at the 1997 level; the droplets are smooth beads of a brighter red than
  the maroon and near-black specks of 164.
- Slime splatter (CG-2): the decal picture is one central blot with thin spatter; 661/681/701 are chunks scattered over
  the whole area. On sunlit earth the red splash reads terracotta rather than 701's brown. The gel is opaque.
- Fountain drops look like dark leaves close up (CG-4); the pig is still a barrel on thick legs (CG-5); the grey cylinder
  at a duck's death (CG-6).
- The stain a burst leaves is strong on earth and faint in tall grass (ground decals reach only 20 cm above the ground so
  that they do not paint the hero's legs).
- At 6 to 8 m/s every small creature here scurries; that is the 1997 speed at this world scale.
- One pig placement has duck_brain; hit once it would turn into a headless duck in 1997. Here it stays a pig.

## Not done, not checked

- Tests ran on master `0bf319c9` plus this branch; the branch was then rebased onto `6ef7a590` and NOT rebuilt or
  re-tested there. The last change (`BindClasses` clears gore first) was built and passed `Dink.Art` 66/66 on `0bf319c9`.
- The green slimes that run `en-slim` (11 on SCR_546/610) and the one blue with `en-slim` die into 701/703 in 1997; their
  rows now carry that corpse (data only). Seen once: the green slime S546_P15 left the 701 corpse (log and sheet 3), partly hidden by a wall.
- The duck's head in its pool on grass; the slimes' attack; the living green slime outdoors.
- The 90 `duck_head` placements of SCR_145 and the `duck_corpse` cards are not bound (GP-Q7).
- Motion judged from stills; no video, no packaged build. A13 (the decal-pass crash) was not reproduced; the decal churn
  is gone, whether that was its cause is not known.
- Tests: `Scripts/test.sh Dink` 281/281 (3 with warnings, all outside this work) in 1,039 s, which includes
  `Dink.Art.CreatureClass` 6/6 with the new `BurstOnlyOnAKillAndStainsReused` and all 29 probe tests; the twenty probe
  trace md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 b4ad88c02c ... Ch20 84f33687af). Python unit tests
  883 OK in the private copy.
