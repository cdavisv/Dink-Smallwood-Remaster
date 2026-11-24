# Townsfolk second pass, part 1: the countryman, the old man and the maidens (23 Nov 2026)

Queue rows SP-04 (the ported townsfolk need real heads, skin, groomed hair and hands) and SP-09 (the maidens' trim, face
and neckline). The figures the player meets first in Stonebrook: Ethel of SCR_002, whom 1997 draws with the old man's
pictures (`npc_old_man`), the countryman of SCR_003 and SCR_038 (`npc_peasant`) and Libby of SCR_004
(`npc_maiden_blue`; the brown and red twins change with her).

**Status: DRAFT; seen in the running game on 23 Nov 2026** (the owner allowed rendered Unreal again at 11:40). The
first version of this PR (10:50) was judged from Blender only and listed what was below the bar; the second (14:30)
worked that list off and added what the game's frames showed; the review of those frames passed the old man and the
countryman and sent the maiden back: at one metre the hair on her head was a lattice of crossed card planks. **This
third version re-grooms her hair (section "The maiden's hair, re-groomed") and is re-cut on master e37f11e42** (which
holds #217, #219 and #220). The old man and the countryman are unchanged since the second version.

## What changed since the first version

**Triangles and textures: the three figures now cost what a main character costs.** Townsfolk stand several to a screen.

| LOD0 triangles | first version | now | cap |
|---|---|---|---|
| countryman | 58,738 | 33,739 | 35,000 |
| old man | 39,614 | 31,032 | 35,000 |
| maiden (and her three twins) | 34,568 | 34,754 (33,950 before the hair was re-groomed) | 35,000 |

- Countryman: decimate shares on his clothes, boots, belt, hat and cuffs (`NPC/Peasant/cfg/assemble.json`), the backs of
  the eyeballs and the scalp under the hair cap removed, the hero's fingered hands at 45 % (new key `skin_decimate`
  `{"hands": share}` in `dink_06_assemble.py`; the head is not touched), fewer and slightly wider hair cards.
  **Rejected:** `hidden_cull` on him: it took the brim of his hat (two skins 4 mm apart cover each other).
- Old man: hands at 45 %, eye backs, thinner hair, a beard of fewer cards on a body of its own (below).
- **The LOD chain was not sane and is now.** `dink_06_assemble.py` gave the decimate modifier a share of the WHOLE mesh,
  but the modifier may not collapse hair cards, so on a figure whose hair is a third of the mesh the body took the whole
  cut: the old man's LOD2 and LOD3 had 0 triangles of skin, 31 of habit and 44 of shoes under 14,486 and 11,102 of hair;
  the maiden's and the Mother's LOD2 had 48 triangles of skin. New key `lod_body`: the share is of the body.
  LOD1-3 now: countryman 20,713 / 15,050 / 10,114, old man 20,880 / 16,091 / 11,830, maiden 24,094 / 18,327 / 12,026 (hair thins by card layer only, as before, so the
  lower LODs are hair-heavy). **Not measured: which LOD the game's camera shows** (the LOD screen sizes are the
  engine's defaults for imported LODs and are not exposed to the editor's Python).
- Textures (`Characters/Tools/tex_cap.py`, a step of `run_townsfolk.sh` and `run_maiden.sh`): skin and hair sets
  4096 -> 2048, the countryman's outfit colour map 4096 -> 2048, eyes 1024 -> 512, by whole-texel averaging (colour
  under an alpha channel weighted by the alpha, normals made unit length again). A first version that scaled the alpha
  up to keep the strands' share was withdrawn (it can lift tile-edge texels over the cut-off).

| content folder (packages) | first version | now |
|---|---|---|
| NPC/Peasant | 161 MB | 68 MB |
| NPC/OldMan | 153 MB | 66 MB |
| NPC/Maiden | 103 MB | 43 MB |
| NPC/MaidenBlue, MaidenBrown, MaidenRed | 16 MB each | 19 MB each |
| the six together | 465 MB | 234 MB |

**The old man stoops** (1997 bends him double over his cane). New standing clip `AN_Stoop_Stand`
(`AnimationPassV1/Tools/clips_people.py`: knees bent, hips back, the back rounded 50 degrees forward, the head held
level, the right fist closed on the cane where it stands on the root bone; he breathes, shifts his weight and looks up
once in eight seconds) and `STAND_IDLE` in `Scripts/bind_people_classes.py`: the class row `npc_old_man` idles in it.
His walk is the shared one: **he straightens when he walks** (a stoop in every state is a posture row for his body
set, which is the motion code's).
- `build.py` renders its contact strips with Cycles on the CPU when `DINK_CPU` is set (they were Workbench renders).
- **Forearms:** an under-sleeve cuff per arm (`townsfolk.py` `undersleeve`, `townsfolk_port_pack.py`): a short tube
  of the sleeve's own cloth from the heel of the hand into the sleeve, rigid on the forearm. The first one reached the
  elbow and came out through the bent sleeve as a pale peg in the game; it is 8.5 cm now and takes one texel of cloth.
- **The beard's dark gaps** were three things. (1) No card faced the viewer under the chin: `hairlib.py` shaded and
  turned a card by the nearest skin's normal, and under the chin that is the throat, which looks down; a beard now
  gives its own forward normal (`shade_n`). (2) The thinning tips of the under layer left holes: a `core` layer of
  broad dense cards, shorter and closer to the chest, fills the body and the sides (`hair_groom.py`, `hair_styles.py`
  `OldMan` `core`). (3) Most of the BLACK in the Blender sheets was not the art at all: Cycles returns black where a
  ray crosses more than eight transparent card layers (its default bounce limit); the review renders now use 64.

**The countryman's coat** is one sleeved coat: the hero's jerkin and the sleeves of his shirt in the same weathered
brown (`townsfolk.py` `outfit`: a part with the gain `None` takes the jerkin's brightness; `mottle` wears the cloth
unevenly; worn edges no longer come out as bright piping), the leather cuffs with them, the bracer laces gone.
**A neck cloth** (`props.scarf`, `townsfolk_pack.py`): a rolled cloth wound once round the neck over the collar,
knotted at the throat, two ends on the chest, painted as coarse undyed weave in a free rectangle of the gear atlas. In
the game's first frames the coat's collar came out through it in a pose: the coat's faces inside the roll are removed
and the roll stands 7 mm off the cloth. **A weathered face** (`cfg/skin.json`: age 1.3 -> 2.0, a deeper tan, sun,
broken capillaries, more lines; `cfg/head.json`: hollower cheeks, heavier brow, bags under the eyes).

## The maiden's hair, re-groomed (third version)

**Cause of the lattice** (read from `hair_groom.py` `guide_long` and `hairlib.py` `ribbon`, and visible in the Blender
looks exactly as in the game): (1) the long groom was a march in 3 cm steps that was turned by kicks: a pull behind
the shoulder that acted from the shoulder up to above the ear, a tuck, and `torso_push`, which threw any point inside
the torso box onto the back in one step. That gave horizontal planks round the nape and zigzag locks at the ear.
(2) Each long card had seven segments, the first at 2, 8, 16 and 27 cm from the root: three straight chords across a
skull of 9 cm radius. (3) The cards were 2.7 to 3.8 cm wide with square ends, drawn hard-edged by the game's masked hair.

**The cure** (`hair_styles.py` `Maiden`: key `drape`, shells `mane_shells`; the Mother's bob and every other style are untouched):
- `guide_drape` (`hair_groom.py`): a lock is a combed path in two smooth parts. On the skull it lies on the head and
  follows one flow (sideways from the parting, then down and a little back; in front of the ears back over the ear)
  in 8 mm steps, until the skull turns under or the height of the ear lobe. From there it eases onto its own place in
  the curtain on her back and hangs to the waist. The place follows the angle of the lock's root round the head, so
  the mane is as wide as her shoulders and evenly thick. What keeps a lock clear of neck, shoulders and the torso box
  is spread along the lock before it is applied (a push on single points left a kink at each).
- A measure: the sharpest turn between two guide points (1.8 cm apart), per guide. First try 488 of 1,200 guides
  over 30 degrees; now 6 (median 16.4, 99th percentile 24.4 degrees; the skull's own curve is 11.5).
- Cards (`mane_shells`): wide mane cards rooted on the lower half of the head, full-length locks from the whole
  scalp, and over the skull short narrow SHINGLES (1.0 to 2.2 cm wide, a hand long) that run with the flow, narrow
  to a point and overlap like roof tiles; a fringe and wisps as before. `ribbon` got `adapt` (segments where the path
  bends: a chord may leave the guide by 1.4 mm, so many short segments over the skull and few on the straight
  fall), `root_w` (a card starts narrow on the crown) and `card_n` (a hanging card faces away from the body; by the
  nearest skin's normal it lay flat over a shoulder and showed as a line). The tile strands end ragged (`rag_k` 2.0).
- Hair triangles 10,264 -> 11,068; the figure stays under the cap (34,754).
- **Rejected on the way** (Blender looks, never imported): the lock's place in the curtain by the angle at which it
  LEFT the head (the locks crowd at the nape: a narrow tail with bare edges); the parting open down the back of the
  head (a hollow); front hair let fall in front of the ear and then drawn to the back (kinked locks on the cheek).
- Earlier, second version, for the record: `fan`, `z_end`, wider cards and a little `puff` gave the mass of pictures
  221-259 but not a clean head; a full stand-off from the skull and smoothed guides were rejected (planks off the
  crown, a lock across her face).

## In the running game, 23 Nov 2026

Screens 2, 3 and 4, each figure from the four sides at 2.7 m and at 1 m, once on arrival and once six seconds later,
and from above (`dink.CalAnchorOrigin S002_P23 / S003_P23 / S004_P16`: a class figure is not a humanoid NPC body, so the
first capture script's `dink.CalAnchorNpc 0` photographed the Mother instead). Two rounds: `t3` (57 frames), then the
fixes named above, then `t4` (57 frames: the old man and the countryman as they are in this commit). The maiden's
new hair: `md1`, `md2` (badly framed: she walks, and an anchor taken once per pass drifts a metre from her head; two
frames were taken from inside her hair and are no view a player has) and `md3` (45 frames: the anchor taken again
before every frame; 2.7 m from four sides, the head from eight sides at 0.95 m and from above, three passes).
Sheets, each with the 1997 pictures on top:

- `10_game_old_man.jpg`, `11_game_countryman.jpg` (round `t4`), `12_game_maiden.jpg` (round `md3`).
- All frames: the stream's copy, `Saved/FableC/.../Saved/CharQA/t3`, `t4`, `md1`, `md2`, `md3`.

**The old man: at the bar at the game's distance, with named faults close up.** He stands bent over his cane as the
1997 figure does, his right fist on it, grey hair and a full grey beard over the brown habit; the beard has no dark
gaps in the game. Faults: when he walks he straightens (see above); the cape of his cowl lifts off his bent back as
a ragged dark edge across the shoulder blades (the swept habit of the Unclaimed source under a 50 degree bend); the
cane's top stands a hand above his fist (the port's cane is 1.32 m); hair and beard are a cool white in the shop's
warm light (the `HAIR_LOOK` tint was left as it was); the beard is rigid on the head bone.

**The countryman: at the bar at the game's distance and close.** One brown coat with sleeves and cuffs, a pale cloth
knotted at the neck, the straw hat as the disc of the pictures from above, dark olive trousers, the pole; a weathered
face with stubble, dark hair going grey under the brim. Faults: the armhole of the hero's jerkin is still there as a
shoulder seam, with a thin blue line of the hero's shirt along the coat's neck edge; the coat ends at the jerkin's belt
line; the neck cloth reads blue-grey in the room's light and its ends do not swing; the pole glides beside him when he
walks.

**The maiden: at the bar at the game's distance and at one metre.** From 2.7 m she is the 1997 maiden: the mane as
wide as her shoulders down to the waist, the dark blue dress with white bands at the sleeves and the neck. At 0.95 m,
from the eight sides and from above (`12_game_maiden.jpg`, two bottom rows), the hair on her head is combed strands
that run from the parting over the head and back over the ear into the mane: no plank crosses another, no kinked
lock, the back of the head closed. Faults that remain: her brows read as a dark drawn arc over paler hairs (not
touched here); the fringe is short spikes over a high forehead; at one metre some of the mane's wide cards show as
flat bands; the temple shows a little scalp before the ear; the hair is rigid on head and spine (it does not swing).

## Below the bar, not done, not checked

- The faults named figure by figure above.
- Which LOD the game's camera shows; the lower LODs are hair-heavy (hair thins by layers only).
- The twins' own dress colour maps are 2048 (checked: `T_Maiden{Blue,Brown,Red}_PR_Outfit_BC.png`, 2.1 MB each; an earlier line here said 4096 and was wrong). What is 4096 is the Mother's dress normal and ORM maps, which the maidens sample by reference (`NPC/Maiden/manifest.json`: `../../Mother/Textures/T_Mother_PR_Outfit_*`); they have no copy of their own. A twin's 19 MB is its copy of the mesh.
- `SM_Corpse_Peasant_PR` (not this stream's) was made beside the old smock figure: the living man and his corpse may
  no longer match in dress.
- The brown and the red maiden were not captured (S410_P06 is vision-gated); they share everything but the dress map.

## Headless proof

Copy `Saved/FableC` = master e37f11e42 + exactly this change (the copy was synced from the PR's own worktree after the
scrub, so it held the files of the commit and no other draft), 23 Nov 2026, 16:23-17:26:
- Clean build (`Intermediate/Build` and `Plugins/*/Intermediate` deleted first): `BUILD OK: DinkRemasterEditor Linux Development in 182s (Result: Succeeded; 0 warnings)`.
- World regenerated (`rm -rf Content/Dink/_Generated`, `import_greybox.sh --region all --export --no-test`: IMPORT OK, 10089 assets + 7 maps; `--region stonebrook`: IMPORT OK).
- No import between the look and the tests: the maiden's packages in this commit are the ones the game showed in round `md3` (imported 15:32 with `DINK_PHOTOREAL_ONLY=npcs`, `-nullrhi`, IMPORT OK, 0 warnings), with the private paths scrubbed out.
- `Dink.Animation+Dink.Art+Dink.Movement`: TESTS PASSED 107/107 (5 with warnings) in 134 s.
- `Dink.Gameplay.Probe`: TESTS PASSED 29/29 (1 with warnings) in 554 s; all twenty chapter md5s equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master (Ch1 cff64df9d1 ... Ch20 b27010b31e).
- Source audit as CI runs it: `check_public_paths.py` 0 flagged, `verify_sources.py --metadata-only` passed, `scrub_private_paths.py --check` clean over the whole tree (23,523 files).
- Kernel log: 0 Oops.

**After that proof master moved to c0e29cac5** (#212 chests, #211 fountain, #222 grip and carry, the last with C++).
This commit is rebased onto it; git merged `AGENTS.md`, `FABLE_ART_QUEUE.md`, `animation_pass.json` and
`animation_manifest.json` without a conflict (different rows), and no file of this change's art is touched by those
three. The build, tests and probe above were NOT repeated on c0e29cac5 before this push; a run on c0e29cac5 together
with #218's clips follows as a comment on the PR.

`animation_manifest.json`, `animation_pass.json` and `AnimationPassV1/Tools/build.py` are also touched by #218 (the
mannerism clips): different rows and hunks; if git reports a conflict in the two JSON files, keep both sets of rows.
