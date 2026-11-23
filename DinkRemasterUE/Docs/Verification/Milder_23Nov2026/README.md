# Milder: collar, pauldrons, greave straps, knee cops, plate (SP-07), 23 Nov 2026

Review follow-ups of #156 and the look of 16 Nov (art-people-2): the padded collar is a crumpled knot with holes behind
the neck, brown tabard leather comes through both pauldrons, the upper greave strap zigzags through the greave and the
greave backs carry dark ragged teeth, the knee cops show from behind as dark discs, the vambraces mirror the meadow
bright green from behind. Knee cops from the front and the bare shoulder top were fixed on the branch before.

## In the running game, 23 Nov 2026 (rendered Unreal allowed again by the owner at 11:40)

Screen 407 after `item-pig use` (the scene that makes Milder). Frames in this folder; all rounds in the stream's copy
(`Saved/FableC/.../Saved/CharQA/mi1`, `mi2`, `mi3`). The first round's whole-figure cameras looked into a boulder and
its "play" frame showed Dink before Milder had come; the later rounds use raised quarter views at the game's distance.

- `10_game_1997_and_game.jpg`: the 1997 soldier pictures 401-409 (Milder is drawn with them) above the game: two
  views at the game's distance, the whole figure, the shoulders from the front, the face, the knees.
- `11_game_back_armholes.jpg`: the fault below.

**My judgment against 1997.** At the game's distance he reads as the same man from the front and from behind: steel
pauldrons, vambraces, knee cops and greaves, a mail skirt, the brown leather tabard with its baldric, the blue collar,
brown hair. The plate reads as plate from there. Close: the face and the brows (single hairs) hold, the collar lies
smooth behind the neck, the pauldrons are whole, the knee cops have their straps, the greave straps and backs are clean.
**The vambraces are not green in the game**: the steel is a neutral grey on grass, in sun and in shade (`METAL_K` .82
stays). No black slits show at the collar band at these distances.

**Below the bar.**
- **The tabard's armholes at the back are ragged.** With the arms hanging (the figure is built in an A pose) the leather
  round both armholes, under the pauldrons, is torn into dark jagged shapes with smeared texture, and skin shows between
  them (`11_game_back_armholes.jpg`; from the game's distance it is a dark notch beside each pauldron). Cause: the
  tabard's shoulder caps reach over the shoulder joint onto the upper arm and their triangles are stretched between the
  collar bone and the arm. Tried on 23 Nov: hanging the armhole rim from the collar bones at assembly
  (`arm_to_clavicle` {"Tabard": 0.75}, as the countryman's jerkin has it), seen in the game (`mi2`): not better, the
  shreds only change shape. Not in this PR. The cure is in `milder_02_build.py`: cut the tabard's armhole back to the
  shoulder point (or let the pauldron's leather carry the cap as a piece of its own, rigid with the pauldron) and bake
  again.
- Between knee cop and greave the brown hose shows as a band from behind (acceptable to me: it is where the 1997
  figure shows leg).

## Causes found (all in `Characters/Tools/milder_02_build.py`) and what changed

| Seen | Cause | Change |
|---|---|---|
| Collar: a crumpled patch with holes behind the neck | (1) the neck band's radius was measured once at z 1.53 and capped at 8.5 cm, so the foot of the band lay 3 cm inside the trapezius and was thrown out again through the skin; (2) the cape rows were snapped to the nearest point of tabard + body volume (not the skin) and folded over the tabard's rolled neck edge; (3) the bake source was laid at 288 x 96 with the same few relaxing passes, kept its folds and baked them into the normal map of a game mesh that was smooth | `ring_r(z)` per row of the band; the cape is laid on tabard, body volume AND skin, relaxed and cleared in turns; game mesh and bake source read ONE 72 x 24 control grid (`cowl_lay`); the band's foot meets the cape's inner row |
| Tabard through the pauldrons | the tabard stands a centimetre off the body, the dome (76 / 88 mm) lay in it | dome 85 / 97 mm; under the plate (and only there) leather and collar are pressed to 7 / 5 mm below the steel, never under what they lie on |
| Greave strap zigzag | the strap was a band of ONE radius on a sloping calf: 4.3 mm inside the greave at one edge (measured) | `ring_strap` casts three rays across its width, 24 sides, never under the raw radius |
| Dark teeth on the greave backs | the coarse game plate cut through the boot top and the folds of the hose between its rows | the greave takes the widest radius of its neighbourhood (`smooth_tube(dilate=...)`): a shell, not a skin |
| Knee cops as dark discs from behind | the wings wrapped 89 degrees round the knee and stood off the leg behind its widest part | wings to 72 degrees, the cop fitted on its middle rows in width and depth apart; a strap round the back of the knee holds it |
| Green vambraces from behind | all reflection, no body colour: even satin plate took the whole colour of the meadow | the plate keeps 82 % of its metalness (`METAL_K` in `cfg/tex.env`, `post_tex.py`) |
| Brows | - | the unshipped g5 brows of 15 Nov (thinner, arched, lifted at the nose) taken in (`hair_styles.py` 'Milder') |

The soldier (`NPC/Soldier`) is a twin of Milder and gets the same harness.

## What I saw before the game could be run (Blender, Cycles on the CPU)

- `01_collar_pauldrons_knees_before_after.jpg`: master above, this change below, same cameras and lights. Knees from
  behind: master's strap is a zigzag of leather teeth and the greave carries dark teeth under its rim; after, two whole
  straps lie on smooth greaves and a strap passes behind each knee. Neck from behind: master's collar is a knot with
  holes over a black notch, leather stands through both pauldrons in patches; after, a pleated mantle lies flat over the
  shoulders down to below the notch and the pauldrons are whole plates. From above in front: master's collar is torn at
  the shoulder; after, it is whole.
- `02_body_play_camera_before_after.jpg`: front, back, from play-camera height behind him, and the back close with the
  mail skirt: the mantle and the larger pauldrons read at once at play-camera height; the back of the mail skirt is whole.
- Review renders in the source tree: `SourceAssets/Art/PhotorealPass/Characters/Milder/Review/g7_*.png`.

## Below bar / not done / not checked

- Seen in the running game on 23 Nov 2026: see the section at the top.
- In motion the plates are rigid and the cloth under them is skinned: the rest pose is clean, a raised arm was not posed.
- Still wrong in the renders: three or four short black slits where the neck band meets the cape in front; the tabard's
  armhole edge beside the pauldrons is ragged leather; from straight behind a slim dark crescent of each knee cop's
  inside still shows beside the knee; the knee cops are large (grown 1.3 to clear the hose).
- Rejected on the way: g3 pressed the leather beside the plates too (skin came through in patches); g4 laid the bake
  source on its own grid (the knot stayed in the normal map); g6 widened the mantle behind (the tabard came through it)
  and cut the knee strap to 14 sides (notched).
- LOD0 34,964 triangles (cap 35,000): 36 to spare.
- The soldier twin was not rendered.

## Tests and probe

Headless, copy `Saved/FableC`, master 78867e7b + this change + the other two branches of the stream (armpit row #217, Mother, Milder: tested together), build `BUILD OK ... 0 warnings`, world regenerated with `--export` after `rm -rf Content/Dink/_Generated`, imports `-nullrhi` with 0 warnings (`DINK PHOTOREAL IMPORT OK`):
- `Dink.Animation+Dink.Art+Dink.Movement`: TESTS PASSED 101/101 (5 with warnings) in 147 s.
- `Dink.Gameplay.Probe`: TESTS PASSED 29/29 in 714 s; all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 cff64df9d1 ... Ch20 b27010b31e).

**Repeated on master 6e3d4f991 on 23 Nov 2026** (copy `Saved/FableC`; this PR as it now stands together with the stream's other drafts #217, #219, #220, #223): clean build `BUILD OK: DinkRemasterEditor Linux Development in 167s (Result: Succeeded; 0 warnings)`; world regenerated; imports `-nullrhi` with 0 warnings; `Dink.Animation+Dink.Art+Dink.Movement`: TESTS PASSED 107/107 (5 with warnings) in 129 s; `Dink.Gameplay.Probe`: TESTS PASSED 29/29 (1 with warnings) in 561 s; all twenty chapter md5s equal the table of `Plugins/DinkParity/Docs/packaged_probe.md` on master (Ch1 cff64df9d1 ... Ch20 b27010b31e). Kernel log: 0 Oops.
