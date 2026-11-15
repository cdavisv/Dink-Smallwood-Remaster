# GP-Q4: Killed people's corpses (Jack, the Joppa family, the cult girl) and dragon corpses for killed dragons

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q4 (GORE_STORY_PARITY.md G4) |
| priority (queue) | high |
| estimated size | M (people: meshes exist for four of five; code needed to show them; dragons: in Stream A) |
| stream | Stream B, gore and remains, step 6 of that stream |
| kind of work | people: one new body (the Joppa mother 365) + reuse of the corpse kit; the rest is CODE (show kill sprites of brain-16 people); dragons: see VS-03 |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

People the player may kill have no `base_death`, so `add_kill_sprite` leaves `base_walk + 5` (dink.cpp:12374-12383):
`s2-jack` (walk 340, created by `s2-auntp`, screen 36) -> **345**; the Joppa family of screen 419 (`s5-jops` creates
them): `s5-fmom` (360) -> **365**, `s5-fguy` (410) -> **415**, `s5-fd` (220) -> **225**; `s7-dgirl` (330, placed on
91 and 126) -> **335**. Dragons: 212/216 (VS-03).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`345/01`](ref/GP-Q4/345_01.png) | Jack (merchant death) | 74 x 53 | 1.85 x 1.32 m |
| [`365/01`](ref/GP-Q4/365_01.png) | Joppa mother | 68 x 50 | 1.70 x 1.25 m |
| [`415/01`](ref/GP-Q4/415_01.png) | Joppa father (peasant) | 114 x 59 | 2.85 x 1.48 m |
| [`225/01`](ref/GP-Q4/225_01.png) | Joppa daughter (maiden red) | 63 x 47 | 1.57 x 1.18 m |
| [`335/01`](ref/GP-Q4/335_01.png) | girl, s7-dgirl | 58 x 37 | 1.45 x 0.93 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q4/strip.png`](ref/GP-Q4/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Death pictures 58-114 px wide, 37-59 px tall: 1.45-2.85 m x 0.9-1.5 m at 2.5 cm/px x 100 % (body plus pool; 415 includes the pole).

## 3. Where it shows

- **3 placements** on **2 screens**: 91, 126
- by class: `npc_girl` 3
- art state today (`art_coverage.py` on master): placeholder 3
- card in the game today: 1.32-1.43 m wide, 1.55-1.55 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 3
- origin IDs: `S091_P22`, `S126_P06`, `S126_P07`
- Jack (screen 36) and the Joppa family (screen 419) are script-made, not placed

## 4. Start from (existing sources, half-done work)

- Corpse kit on master (`PhotorealPass/Corpses`, `/Game/Dink/Photoreal/Corpses`, bound to placed cards by
  `families.json`): `SM_Corpse_Merchant_PR` (row `345 people/merchant/death-`: the same picture as Jack's corpse),
  `SM_Corpse_Peasant_PR` (415), `SM_Corpse_Maiden_PR` (225, crimson dress), `SM_Corpse_Girl_PR` (335). Evidence
  `Docs/Verification/CorpsePeople_14Nov2026/`, `CorpseBloodExtent_14Nov2026/`.
- Missing: **365, the Joppa mother in her brown dress** (the corpse-kit mother of GP-Q5 is the burnt mother 355, a
  different picture). Make it from the Mother character (`Characters/Mother`, `Corpses/tools/build_gore.py` people recipe).
- Why nothing shows today (gore audit G4): the presenter leaves corpses only for class-bound brains 9/10;
  brain-16 kills are not handled and an unbound kill sprite is not drawn. That is **code** (gore-audit code queue C1:
  present the kill sprite by its picture's family row or card until the screen changes), for an Opus stream.

## 5. What to make

Build the 365 body (brown dress, red, in a pool) in the corpse kit; ask the coordinator for the C1 code change so the kill sprites 345/365/415/225/335 take the existing family rows.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

345/365/415/225/335: each body **soaked red lying in a red pool with drops**, 335 (the girl) mangled pink-red. Bar: the corpse-kit level of PRs #111/#112/#119 (pool at least the picture's red extent).

## 7. Import and binding

Corpse kit import (GP-Q5 section 7); a `families.json` row `365 people/mom/death-` like the 345 row.

## 8. Prove it in the game

Kill Jack on 36 and the Joppa family on 419 (`dink.Goto 36` / `dink.Goto 419`, `dink.Attack` with `dink.Fact strength 60`), shots after each kill; this needs the C1 code first.

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- Blocked by code C1 (not art) for any in-game proof. Dragon half: VS-03 (Stream A).

## 10. Done when

Killing any of the five leaves its photoreal body in a pool until the screen changes.
