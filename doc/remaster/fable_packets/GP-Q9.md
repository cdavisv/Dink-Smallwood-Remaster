# GP-Q9: Explosion, fire and burst effects for script sprites (167, 164, 161, 70, fireball): effect rows instead of a grey marker

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q9 (GORE_STORY_PARITY.md G17) |
| priority (queue) | medium |
| estimated size | M |
| stream | Stream D, ground, water, effects, hero, step 2 of that stream |
| kind of work | effects art (flipbooks exist as sources; Niagara or flipbook cards) + effect rows |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

`create_sprite(..., 167, ...)` appears 44 times in the 1997 scripts (bombs `dam-bom*.c`, fire, Seth's death in
`s7-boss.c` `die`: "EAT IT!" and eight explosions 167, the cult, the dragon fights, the wizards), 161 (atomic fire
pillar) twice, 70 (`splode/explo`) four times, 512 (fireball) once; the engine adds the burst 164 (blood-red ball)
for a killed sprite without a death picture (dink.cpp:12384-12389) and for the duck's second blow (dink.cpp:12732,
brain 7 = play once). 167 is an orange-white fire ring that expands and breaks up; 164 a dark red ball that bursts
into specks; 161 a tall column of fire.

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`167/01`](ref/GP-Q9/167_01.png) | explosion start | 106 x 107 | 2.65 x 2.67 m |
| [`167/04`](ref/GP-Q9/167_04.png) |  | 128 x 131 | 3.20 x 3.27 m |
| [`167/07`](ref/GP-Q9/167_07.png) | fire ring | 147 x 152 | 3.67 x 3.80 m |
| [`167/11`](ref/GP-Q9/167_11.png) |  | 163 x 169 | 4.08 x 4.22 m |
| [`164/07`](ref/GP-Q9/164_07.png) | burst (blood-red ball) | 87 x 72 | 2.17 x 1.80 m |
| [`161/01`](ref/GP-Q9/161_01.png) | fire pillar | 91 x 140 | 2.27 x 3.50 m |
| [`161/17`](ref/GP-Q9/161_17.png) | fire pillar, late | 106 x 63 | 2.65 x 1.57 m |
| [`70/01`](ref/GP-Q9/70_01.png) | explosion | 60 x 61 | 1.50 x 1.52 m |
| [`70/08`](ref/GP-Q9/70_08.png) |  | 89 x 88 | 2.23 x 2.20 m |
| [`512/01`](ref/GP-Q9/512_01.png) | fireball | 32 x 76 | 0.80 x 1.90 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q9/strip.png`](ref/GP-Q9/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

167: 106 x 107 to 165 x 171 px = up to **4.1 x 4.3 m**; 164 up to 2.9 x 3.0 m; 161 91-114 x 63-143 px = up to 2.8 x 3.6 m; 70 up to 2.4 x 2.3 m (2.5 cm/px, effects use the base scale).

## 3. Where it shows

- **6 placements** on **2 screens**: 1, 366
- by class: `explosion_fx` 2, `fire_burst_fx` 2, `fireball_fx` 2
- art state today (`art_coverage.py` on master): placeholder 6
- card in the game today: 0.80-2.33 m wide, 1.52-3.52 m tall (greybox card = picture px x layout or base scale x size%)
- drawn as: actor 6
- origin IDs: `S001_P28`, `S001_P29`, `S001_P33`, `S001_P41`, `S366_P09`, `S366_P14`
- The placed ones are few; nearly all are script-made at run time (`ADinkScriptSpriteActor`).

## 4. Start from (existing sources, half-done work)

- Flipbook sources (master, partial: "flipbook source only"): `Unclaimed/explosion_fx` (`FX_Explosion`, 64 frames,
  fireball cooling to smoke), `Unclaimed/fire_burst_fx` (`FX_Fire_Burst`), `Unclaimed/fireball_fx` (`FX_Fireball`, loops),
  `Unclaimed/hearth_fire`, `Unclaimed/sparkle_fx`.
- The pattern to copy: the gold twinkle effect row on master (`families.json` family `sparkle_fx`: `effect`
  `/Game/Dink/Photoreal/Unclaimed/MI_FX_Sparkle`, `effect_size_cm` 70: a camera-facing card with an 8 x 8 flipbook,
  additive; script-created sprites only), imported via the Unclaimed kit `flipbooks` block (IMPORT.md "Gold twinkle and stumps").
- The grey marker: since PR #132's fix branch, sprites with **no** picture show no marker; 167/164/161 have pictures,
  so they still draw the grey cylinder until an effect row exists (that is also CG-6).
- PR #113 draws its own burst for ducks and pigs (`DinkCreatureGore.cpp`): the 164 row must not double it there (see CG-6).

## 5. What to make

Explosion 167 as a real fire ring with smoke and flash (flipbook card at the picture size, or Niagara with a light); 164 as the blood burst (reuse #113's burst look so they match); 161 fire pillar; 70 small explosion; 512 fireball. One effect row each.

## 6. Gore bar (owner rule: at least the 1997 level, never less)

164 is gore: a **dense dark red ball bursting into specks** (see CG-1). Bar: as red and as large as 164; the fire effects have no gore bar but must not be smaller than the pictures.

## 7. Import and binding

- Unclaimed kit flipbooks: `python3 -I SourceAssets/Art/PhotorealPass/Unclaimed/tools/make_kit_manifest.py`, then
  `DINK_KIT=Unclaimed DINK_KIT_FOLDER=Unclaimed Scripts/import_town_exteriors.sh` (writes `M_FX_Flipbook`, `MI_FX_*`).
  `Content/Dink/Photoreal/Unclaimed/M_Struct_Baked.uasset` is rewritten by any import into that folder: tell the
  coordinator before committing it.
- Row: `{"family": "167 effects/splode/shock-", "effect": "/Game/Dink/Photoreal/Unclaimed/MI_FX_Explosion.MI_FX_Explosion", "effect_size_cm": 420, "fit": "none", "yaw_from_sprite": false, "note": "..."}` (family key as the sprite family of `art_coverage.py`).

## 8. Prove it in the game

Seth's death (`s7-boss`) and a bomb: `dink.Goto` to the boss screen with the story set (check `tools/dinkc/out/facts.csv` for the `&story` value), or place a bomb with the item; shots every 0.05 s for 1 s.

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- CG-6 is part of this row. Coordinate the 164 look with CG-1 (Stream B).

## 10. Done when

No grey marker for 167/164/161/70/512; Seth's death shows eight explosions.
