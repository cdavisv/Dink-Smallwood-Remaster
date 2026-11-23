# The Mother: her 1997 hair, brows as hairs, a softer face, a clean neckline (SP-07), 23 Nov 2026

The owner, 13 Nov 2026: "improve hair". Review of #156 (16 Nov): her brow reads as a drawn line, the hairline is hard,
the hair is a cap, the face smooth; the first brow rebuild of 16 Nov was two dark bars in the game and was rejected.

## In the running game, 23 Nov 2026 (rendered Unreal allowed again by the owner at 11:40)

Three rounds on screen 1, ten fixed cameras each (the game's own camera, face, three-quarter, side, back, bust, whole
figure front and back, from above behind); frames of the last round in this folder, the earlier ones in the stream's
copy (`Saved/FableC/.../Saved/CharQA/mo1`, `mo2`, `mo3`).

- `10_game_1997_and_round3.jpg`: the 1997 pictures above the game's own camera, the whole figure, the bust, the face,
  the side by the fire and the back of the head in the window sun (round 3).
- `11_game_round1_then_round3.jpg`: round 1 (this PR as first pushed) against round 3, the same cameras.

**Round 1** (the PR as first pushed). At the game's own camera she reads as the 1997 mother: blond bob, red dress.
Close up it failed, and the coordinator's review of the frames named it: the hair read as **straw thatch** (wide flat
strips with hard square ends in parallel bands), bleached almost white in the window sun; the skin of **chest and neck
had a coarse sandy grain**, much stronger than the face; the lips were pale.

**What was changed for it.**
- Hair (`hair_styles.py` `Mother`, `bob_shells`): the cards one sees are a fifth narrower (`wv`), every card narrows to a
  point (`tp`), the locks are rolled out of their common plane (`rl`), the tiles' strands end at varied lengths
  (`rag_k` 2.4: feathered tips instead of a cut edge), twice the colour variation from strand to strand and from card
  to card, the albedo a tenth darker. LOD0 34,898 triangles (cap 35,000).
- The game's hair look (`import_photoreal_art.py` `HAIR_LOOK` `Mother`): tint (1.0, .95, .8) -> (.98, .86, .62),
  `TipLight` 1.0 -> .6, `Scatter` .6 -> .45, `Specular` .25 -> .12, `StrandVariation` .12 -> .22.
- Chest and neck (`dink_05b_skin.py`, new key `micro_lo` [z0, z1, share]): the fine relief of the skin set is drawn
  per texel, and neck and chest lie on few texels of the sheet, so pores and furrows came out several times their size
  below the jaw. It now fades to 22 % between the jaw and the collar bones; the hands keep theirs.
- Lips: new key `lip_pct` (which share of the mouth zone counts as lip) [55, 92] -> [38, 78], `lip_k` 1.8.
- LOD chain (`dink_06_assemble.py`, new key `lod_body`): the decimate share counted the whole mesh but may not collapse
  hair cards, so her LOD2 and LOD3 kept 48 triangles of skin under 10,900 of hair. The share is now of the body:
  LOD1-3 body 55 / 32 / 18 % of LOD0's. Which LOD the game's camera shows was not measured.

**Round 3, my judgment.** At the game's camera: the 1997 mother. Close: the bob is strands with feathered ends and a
ragged nape, golden by the fire and in shade; in the direct window sun the back of the head is still a pale straw
blond, but it keeps its strands and its shadows (it no longer goes to a white sheet). The chest and neck are smooth.
The lips have a little colour.

**Still below the bar.**
- At the temples in the face frame the outer cards still lie in parallel steps (finer than before).
- The face is still stern: a heavy brow shadow in the hard side light and a firm jaw; the 1997 mother is round and
  soft. Not changed in this round (the face is a head-stage change with a new groom).
- The brows read as a thin dark line at one metre.
- The lips are still paler than the red mouth of the pictures.
- The back neckline of the dress keeps master's notch (frame from above).
- The forehead shows its pores in the hard sun at half a metre.

## Against the 1997 pictures 351 to 359 (`00_mother_1997.png`)

The 1997 Mother has a full head of golden hair to the jaw with a fringe, the ears covered, and a red mouth. The tight
bun over a painted cap was the remaster's own, and the cap was what read as a helmet with a ruled hair line. She now
wears the hair of her pictures.

| Part | Master | Now |
|---|---|---|
| Hair | bun core + a painted cap + 610 thin cards | a bob: groom kind `long` cut at the jaw (`hair_styles.py` 'Mother', `bob_shells`): 270 wide under cards, 262 over them, loose locks, a fringe to the brows, wisps at the hair line, 150 cards that close the nape, locks combed over the parting; the hair stands 1 to 2 cm off the skull (`puff`) and turns under at the tips |
| Hair line | a ruled edge all round | covered by the fringe in front; short wisps at the temples and the nape |
| Brows | a 6 mm band of 400 hairs 5 px wide (two bars in the game) or the fair version (not seen in the game) | a 4 mm band of 360 single hairs 2.2 px wide, mid brown, a little darker than her hair, skin between them |
| Face | jowl and cheek blobs along the normals (they pushed the mouth bag through the cheek: bright specks at the mouth corners in the game), a wide thin mouth turned down | translations and scales only: a broader, softer lower face, fuller lips, level mouth corners, a slightly heavy outer lid; her years are in the skin set (age 1.7, lines) |
| Neckline | chest striped with neck rings, a sunk patch with a ragged edge and a kinked flap of skin; a flake of skin on the shoulder of the dress in the first try | neck rings stop where the neck meets the chest and are weaker (`neck_lo`, `neck_k`); skin sinks only where cloth really covers it (`skin_tuck_cover`); the coarse chest skin the opening shows is relaxed (`skin_relax`) |
| In-game hair look | tint .72/.67/.6, bun pinned | tint 1.0/.95/.8, scatter .6, depth shade .7; `HairPinRadius` 0 (no bun: nothing pinned; agreed with stream motion, Master log 19 Nov) |

LOD0 34,912 triangles (cap 35,000). Vertex counts per LOD changed; the layout contract of the hair and cloth code is
kept (cap on u < .5 / v <= .5, brow and lash band, lock cards on the narrow tiles root at the top, UV 0, 89 bones;
skirt and Outfit slot untouched).

The green matron (`NPC/MatronGreen`, pictures 360, made by scripts only) is a twin of the Mother and gets the same
hair in her greying tint.

## What I saw before the game could be run (Blender, Cycles on the CPU; first version of this PR)

- `01_mother_1997_before_after.jpg`: the pictures, master, this change, same cameras and lights (face, three-quarter, back,
  side, whole figure, and from the height and angle of the play camera behind her). After: a full head of dark-golden
  hair to the jaw with a fringe, the ears covered, the outline broken by loose locks: the silhouette of the pictures from
  every side, and at play-camera height a golden head where master shows a pale cap with a knot. The face is softer and
  rounder, the mouth level; she reads as a kindly woman of about fifty, no longer as worried or stern.
- `02_neckline_before_after.jpg`: master's chest stripes, sunk patch and skin flap; after, a plain chest with a few age
  spots and one faint ring at the base of the neck; the hair reaches the collar behind.
- `03_close_up_game16Nov_then_now.jpg`: the rejected game frame of 16 Nov (dark bar brows, cap, ruled hair line), the fair
  brows of that day (Blender), and this change in the pipeline's sun close-up: single brow hairs over the lid, a fringe
  with strands, the parting mostly covered. The brows are light in Cycles; in the game the hair tint multiplies them.
- Review renders in the source tree: `SourceAssets/Art/PhotorealPass/Characters/Mother/Review/bob1_*.png`.

## Rejected and rebuilt on the way

- First bob (b1): shaggy, card ends as straight spikes, a dark gap down the back of the head (the middle parting ran on
  to the nape): the parting now closes towards the back (`part_back`), every guide is combed smooth (`guide_smooth`),
  the back is closed by its own shell.
- Curl at the tips .9: the card normals turned down and the hem went black; now .25.
- Brows at 280 hairs, `brow_dark` .42: hardly there in the sun close-up; at .34 the colour equals the "two dark bars"
  of 16 Nov once the brighter hair tint is counted in; settled at 360 hairs, .45.
- LOD0 35,698 triangles with the parting locks: cards cut to stay under the cap.
- `skin_tuck_cover` by a ray along the normal only: a flake of skin lay on the shoulder of the dress; cloth within 8 mm
  on either side now counts as cover.

## Below bar / not done / not checked

- Seen in the running game on 23 Nov 2026: see the section at the top (what is still below the bar is listed there). Not looked at there: the hair's motion under #201 while she walks, the green matron twin.
- In Cycles the hair tips at the nape render near black (the tile's tip texels sit beside the next row's roots in
  Blender's material); the maidens show the same in Blender and not in the game. To be judged in the game.
- Her lips: see the section at the top (`lip_pct`); still paler than the pictures' red mouth.
- The back neckline of the dress keeps master's notch; the bob covers most of it.
- The skin of the forehead shows its pores in a sun close-up (micro 1.3 -> 1.1); chest and neck: cured, see the top.
- The green matron was not rendered.

## Tests and probe

Headless, copy `Saved/FableC`, master 78867e7b + this change + the other two branches of the stream (armpit row #217, Mother, Milder: tested together), build `BUILD OK ... 0 warnings`, world regenerated with `--export` after `rm -rf Content/Dink/_Generated`, imports `-nullrhi` with 0 warnings (`DINK PHOTOREAL IMPORT OK`):
- `Dink.Animation+Dink.Art+Dink.Movement`: TESTS PASSED 101/101 (5 with warnings) in 147 s.
- `Dink.Gameplay.Probe`: TESTS PASSED 29/29 in 714 s; all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 cff64df9d1 ... Ch20 b27010b31e).

**Repeated on master 6e3d4f991 on 23 Nov 2026** (copy `Saved/FableC`; this PR as it now stands together with the stream's other drafts #217, #219, #220, #223): clean build `BUILD OK: DinkRemasterEditor Linux Development in 167s (Result: Succeeded; 0 warnings)`; world regenerated; imports `-nullrhi` with 0 warnings; `Dink.Animation+Dink.Art+Dink.Movement`: TESTS PASSED 107/107 (5 with warnings) in 129 s; `Dink.Gameplay.Probe`: TESTS PASSED 29/29 (1 with warnings) in 561 s; all twenty chapter md5s equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master (Ch1 cff64df9d1 ... Ch20 b27010b31e). Kernel log: 0 Oops.
