# GP-Q8: Dink's death clip for sequence 436 (he crumples and lies dead), held until the menu choice

| | |
|---|---|
| queue row | `doc/remaster/FABLE_ART_QUEUE.md` GP-Q8 (GORE_STORY_PARITY.md G16) |
| priority (queue) | high |
| estimated size | M |
| stream | Stream D, ground, water, effects, hero, step 1 of that stream |
| kind of work | new animation (Blender, clip by code in the animation pass) + a hero_actions row |

Rules for every packet: `FABLE_START_HERE.md` (Fable 5.2 only, Unreal lock, Blender limit, gore rule, squash and scrub before push).

## 1. The 1997 reference

`bin/dink/story/dinfo.c` `die()`: `freeze(1)`, `sp_seq(1, 436)` (line 10), `sp_base_idle(1, -1)`, `wait(3000)`, then
`sp_nohit`, `sp_brain(1, 0)` and the restart/load menu. Sequence 436 (16 frames, `dink.ini`) shows Dink staggering,
folding at the knees, falling backwards and lying on his back with his knees drawn up and a small pool under him
(436/16 is also the "dead Dink" picture of screen 58).

| 1997 picture (seq/frame) | what | px | real size at 2.5 cm/px x 100% |
|---|---|---|---|
| [`436/01`](ref/GP-Q8/436_01.png) | death, start | 43 x 96 | 1.07 x 2.40 m |
| [`436/04`](ref/GP-Q8/436_04.png) |  | 52 x 97 | 1.30 x 2.42 m |
| [`436/08`](ref/GP-Q8/436_08.png) |  | 57 x 101 | 1.43 x 2.52 m |
| [`436/12`](ref/GP-Q8/436_12.png) |  | 73 x 94 | 1.82 x 2.35 m |
| [`436/14`](ref/GP-Q8/436_14.png) |  | 85 x 93 | 2.12 x 2.33 m |
| [`436/16`](ref/GP-Q8/436_16.png) | dead, held | 104 x 90 | 2.60 x 2.25 m |

All copied frames side by side (2x, nearest neighbour, on 1997 grass green): [`ref/GP-Q8/strip.png`](ref/GP-Q8/strip.png).
Extracted from the original graphics with `tools/dinkex` (`tools/dinkex/out/sprites/<seq>/<frame>.png`; on a clone without
`out/`: `(cd tools/dinkex && python3 -m dinkex extract --data ../../bin/dink --out out)`). Reference only: never copy pixels into textures.

## 2. Real-world size

Frames 43 x 96 (standing) to 104 x 90 px (lying): the hero rig at its own scale (1.8 m); the lying pose about 2.1 m long. Timing: 16 frames over the sequence's frame delay (`dink.ini`), then 3 s still before the menu.

## 3. Where it shows

The hero, every death (any screen).

## 4. Start from (existing sources, half-done work)

- Clip pipeline: `SourceAssets/Art/Characters/Animations/AnimationPassV1/` (README there; clips are code:
  `Tools/clips_attacks.py` has `Hurt` and `Stumble`, `Tools/rig.py` IK and foot roll), imported by
  `Scripts/import_animation_pass.sh` into `/Game/Dink/Hero/Animations/Pass1`, published in
  `Content/Dink/Data/Art/animation_pass.json`.
- Closest existing motion: `Botch_Faceplant` of the unpushed hero-mannerisms branch (local worktree
  `DinkHeroMannerisms`, branch `anim/hero-mannerisms`, 7 WIP commits; `Tools/clips_mannerisms.py`, 15 new clips,
  evidence `Docs/Verification/HeroMannerisms_14Nov2026/`): "goes down full length, lies for a beat" (forwards, not
  backwards, and he gets up again).
- Code stop-gap in flight: `fix/playthrough-qa` (local worktree `DinkPlaythroughQA`, commit `7ee9044b`): "Dink's death
  picture: limp body and blood pool" in `DinkGreyboxCharacter` + test `Dink.Movement.DeathCollapse` (2870c97d:
  "death test on the photoreal hero"). The clip should replace the limp fall, keeping that test's trigger.
- Hero actions: `Content/Dink/Data/Art/hero_actions.json` maps sequences to clips (`sequences`, `animation`,
  `duration_s`, `loop`); today only the fist (102-108).

## 5. What to make

A `Death_436` clip: stagger, knees give, fall onto the back (hips first, shoulders, head), settle with knees drawn up as 436/16; last frame held; no foot sliding. Blood pool under him as 436/16 (the stop-gap's pool or a decal).

## 6. Gore bar (owner rule: at least the 1997 level, never less)

436/16: Dink **on his back in a red pool** under his torso. Bar: at least that pool, visible at the play camera.

## 7. Import and binding

- `ALSOFT_DRIVERS=null blender -b -t 4 --python SourceAssets/Art/Characters/Animations/AnimationPassV1/Tools/build.py -- --export --only Death_436`
  (after adding the clip to the clip table), then `DINK_ANIM_ONLY=Death_436 Scripts/import_animation_pass.sh` (one
  Unreal step), then `python3 -I Scripts/scrub_private_paths.py --fix` on `Export/` (it rewrites the manifest hashes).
- Binding: a `hero_actions.json` row `{"sequences": [436], "animation": "/Game/Dink/Hero/Animations/Pass1/AN_Death_436.AN_Death_436", "duration_s": <16 frames>, "loop": false}` (hold the last frame: check `UDinkBodyAnimInstance` for a hold flag; add one in code if missing).

## 8. Prove it in the game

Run `Dink.Movement.DeathCollapse` (from `fix/playthrough-qa`) and a capture: `dink.Goto 29 <x> <y>`, `dink.Fact life 1`, let a bonca hit him (or `dink.Fact life 0` if the story's `die` fires on it: check), shots every 0.1 s for 2 s and at 3 s.

Then, before the PR (each Unreal step through `unreal_turn.sh`): `Scripts/test.sh Dink.Art`, the probe `Scripts/test.sh Dink.Gameplay.Probe` (the twenty md5s of
`Plugins/DinkParity/Docs/packaged_probe.md` must stay equal), `python3 -m unittest discover -s Scripts/tests`,
`python3 -I Scripts/art_coverage.py` before/after, and look at every frame yourself, at the play camera and close up.

## 9. Depends on, blocks

- After `fix/playthrough-qa` merges (the stop-gap and its test). Independent of Streams A-C.

## 10. Done when

Dink falls and lies as 436 with a pool, held until the menu; probe unchanged (presentation only).
