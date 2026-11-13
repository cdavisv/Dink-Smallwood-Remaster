# Hero build in the running game: scrawny, farmhand, brawny (12 Nov 2026)

Owner request: "I want to make sure the design of him improving physically changes over time", then "Yes, design it".
The photoreal hero now carries two shape keys, `Physique_Scrawny` and `Physique_Brawny`, driven from hero confidence
(design and numbers: `SourceAssets/Art/PhotorealPass/Characters/Dink/manifest.json` `physique`, UE `AGENTS.md`
"Hero build").

**How the frames were taken.** Private work copy of master 92ba5277 (animation pass 2 included) plus this change, the real game (`-game`,
1280x720, offscreen Vulkan on the RX 6800) through `Scripts/PhotorealQA/run_capture.sh` with the script that
`Scripts/PhotorealQA/hero_build.py script` writes: outdoor spot `dink.Goto 438 300 200`, then for each of
`dink.HeroConfidence 0`, `0.45` and `1` five fixed cameras (`dink.CalCam`). `hero_build.py sheet` tiles the frames
with a label strip. Nothing was retouched.

| File | What it shows |
|---|---|
| `hero_build_front.png` | Whole body from the front at the three builds. |
| `hero_build_threeq.png` | Three-quarter view. |
| `hero_build_side.png` | Side view. |
| `hero_build_back.png` | Back view with the pack. |
| `hero_build_torso.png` | Torso close-up from the front. |

**What I see.**
- The three builds read as the same person: narrow shoulders, thin arms and legs at confidence 0; today's body at
  0.45; a deep chest, thick arms, neck and thighs at 1. Head, hair, hands and feet are the same size in all three.
- No layer shows through another at any of the three builds (shirt under jerkin, trousers under the jerkin skirt,
  bracers, belt, pack straps).
- The dropped head and rounded shoulders at confidence 0 are the posture layer of animation pass 2, not part of the
  shape keys.
- Present in all three builds, so not caused by this change: the pack stands a little off the back in the side
  view, and a thin lace sticks out at the collar.

**Two faults the first captures showed, both fixed before these frames** (the Blender renders and the headless
tests had been clean):
1. The shape keys did not reach Unreal at all: a re-import over the existing mesh ignored the import task's options
   and dropped morph targets. The importer now refuses a hero without its declared keys on every LOD and sets the
   mesh's stored import options before a re-import.
2. With the keys imported, the brawny build drew black and the scrawny build drew the shirt through the jerkin: the
   hero's materials were not compiled for morph targets. The importer now sets that usage flag and
   `Dink.Movement.HeroBuildShapes` checks it on every material slot.

**Tests.** In the work copy after a fresh build and hero import: `Dink.Movement` 10 of 10 (`HeroGrowth`,
`HeroBuildShapes`, `PlayableControls` cover the build) and `Dink.Art` 58 of 58.

**Not checked.** The packaged build, the frame cost of the morph targets, the builds during attacks, jumps and
walking, and LOD1 to LOD3 by eye (the test checks that their shape data exists and is the right size).
