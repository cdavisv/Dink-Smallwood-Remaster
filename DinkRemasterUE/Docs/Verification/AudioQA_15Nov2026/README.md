# Audio QA, 15-16 Nov 2026

What changed, how it was proven, and what is not proven.

Every recorded run used SDL's disk audio driver (`Scripts/AudioQA/run_recorded.sh`). The device mix went to a file, and
nothing played on a speaker or reached PulseAudio. A recording is float32 at 48 kHz on 6 channels (5.1). Runs A, A2 and
B are from 15-16 Nov, before the regenerated effects. Runs C to H are from 16 Nov.

## Files here

| file | what |
|---|---|
| `COVERAGE.md`, `coverage_*.csv` | Run B, the packaged game, 15-16 Nov. Every approved effect, music take, 217 voice lines and every footstep and ambience take heard, each matched to its source by waveform. It predates the regenerated effects: it still lists 9, 44 and 49 as rejected. |
| `redo_takes.md` | The 24 regenerated takes of 9 punch, 44 bow, 48 axe and 49 bird: LUFS, peaks, clipping, verdict, the picks and why. |
| `redo_spectrogram_*.png` | Spectrograms of the picks and the bird alternatives. |
| `clips/redo_*_pick.ogg`, `clips/redo_*_runnerup*.ogg` | **For the owner to listen to:** each pick and its runner-up, as the game imports them. |
| `clips/runA_opening_scene_before_fixes.ogg` | 76 s of the opening scene before the mix fixes (run A, 16 Nov). |
| `cue_runH.md` | Run H: the regenerated bow and axe cued by play in Dink's house, found in the recording. |
| `cue_runM.md`, `clips/runM_fist_hits_in_play.ogg` | Run M: eight fist hits in play on the AlkTree, each heard in the recording. |
| `cue_runL.md` | Run L: the generated footsteps and ambience beds in play (SCR_001 wood, SCR_439 grass, a screen per bed) and all 32 life takes in a sweep, found in the recording. |
| `clips/life_*.ogg` | **For the owner to listen to:** the four takes of each footstep surface, the first 12 s of each bed. |
| `limiter_runC_before.txt`, `limiter_runE_after.txt` | Output level per 30 s with the 15 Nov limiter settings (run C) and the brickwall settings (run E). |

## Proven

- **Owner approval (16 Nov 2026, ~12:55 PT, owner decision 12):** the four regenerated effects `09_punch_e`, `44_bow1_i`,
  `48_axe_i` and `49_bird1_c` are approved.

- **The four regenerated effects play in the game.**
  - Each one was played through the audio subsystem (`dink.AudioQA.Sweep`) and found in the recording by
    cross-correlation with its source take (`Scripts/AudioQA/cue_proof.py`).
  - Run C (9, 44, 49): match 1.000, 0.965 and 0.992.
  - Run D (all four): match 0.997 (punch), 0.965 (bow), 0.998 (axe) and 0.992 (bird).
  - In run D their RMS was -23.2, -32.9, -30.7 and -23.4 dBFS, 14 to 74 dB above the second before.
- **Bow and axe in actual play (run H, inside the house).** Details in `cue_runH.md`.
  - Bow: two releases (`item-b1.c:19`) cued `SFX_44_bow1` at pitch 1.0. Both were found in the recording: match 0.65
    and 0.68, RMS -28 dBFS against about -57 dBFS in the 100 ms before.
  - Axe: two throws (`item-axe.c`) struck and cued `SFX_48_axe` at pitch 0.59, the 13000 Hz the script sets. Both were
    found by waveform: match 0.73 and 0.77 against the pitched-down take. The strike lands on the tail of the throw's
    own swing, so it is not a clean level step.
- **A fist hit in play (run M, 16 Nov).** Eight punches at the AlkTree (S474_P01), the probe's fist target. Each cued
  `SFX_09_punch` on the attack's hit frame, and each was found in the recording at its own onset (match 0.41 to 0.46,
  -14.5 dBFS over 0.45 s). Five nuts fell, as the tree's script does. Details in `cue_runM.md`.
- **Footsteps and ambience beds (run L, 16 Nov).** Details in `cue_runL.md`.
  - All 32 generated takes play: the sweep finds each one by waveform (match 0.89 to 1.000).
  - In play: wood steps in the house are found 19 times of 24 cues. The cave and wind beds are found under the screen
    music (match 0.70 and 0.47).
  - Grass steps outside overlap too densely to separate one by one, and the quieter sea and meadow beds are masked by
    music for the correlation.
- **Tests on the final tree** (world regenerated with `--region all` and `--region stonebrook` each time):
  - origin/master 41e80f73 plus this branch: full `Dink` suite 311 of 312.
  - origin/master 5d8a4a1f (rebased) plus this branch: 309 of 312.
  - None of the failures touches audio, and this branch changes no art, sprite or import code:
    - `Dink.Gameplay.OverridePicture.RevisitShowsSavedPicture` (both runs) expects the sprite material
      `MI_Sprite_175_04`, which the world import never produces. The shared checkout at master has only
      `MI_Sprite_175_01` too.
    - `Dink.Art.Family.ScriptSpriteShowsFamilyMesh` (5d8a4a1f only) is #148's new test. It expects Seth's init-sequence
      pictures (580/581), which the bundle takes from the extracted 1997 data (`export_sprite_pictures.py`).
    - `Dink.Art.Family.BarrelCookedGameSurface` (5d8a4a1f only, second run in the same copy) failed on "preserve prior
      target surface capture". It passed on the first run; this is the known stale `Saved/Automation/BarrelCookGame.*`
      trap.
  - `Dink.Audio` (9 tests, including `MasterLimiterHoldsCeiling`) passes.
- **Probe:** all twenty chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (Ch1 b4ad88c02c ... Ch20
  84f33687af) on every test run of 16 Nov.

## Not proven

- **Seth's bird line in actual play** is not shown in a recording. It comes only at the end of the game (`s7-boss.c:185-186`);
  the probe plays that fight, but headless. The bird take itself plays (runs C and D sweeps), and the cue path is script
  `playsound`, which the bow above also uses.
- **Earlier fist attempts and what they taught** (the hit is proven by run M above):
  - On SCR_030 and SCR_474 the screen's pillbugs killed Dink (10 life); `dinfo.die` and the death menu held him, which
    first looked like `dink.Goto` freezing him.
  - `dink.Npc.Hold 1` freezes Dink as well as the NPCs.
  - In run C the bow sat in slot 3 behind pig food.
  - In runs H and I, eleven punches at the photoreal round table and the mother hit nothing: both use authored-geometry
    hits (`DinkAuthoredInteraction.cpp`), which those console drives did not satisfy.
- **The master limiter (bug A164, reopened).**
  - Runs C and E give the same output peaks to the sample, so the limiter added to the main submix has no measurable
    effect on the device output.
  - In play, only single samples pass -1.5 dBFS (worst -0.53, no clipping).
  - The soak's dense random mix clamps at 0 dBFS.
  - The processor settings are right: `Dink.Audio.MasterLimiterHoldsCeiling`.
  - **Fixed 16 Nov 2026:** the preset never applied those settings (the instance ran the engine's default compressor);
    cause, fix and recorded proof in `../MasterLimiter_16Nov2026/README.md`.
- **Owner listening to the footsteps and ambience beds.** They were generated on 16 Nov (47 takes, 757 credits) and picked by measurement and spectrogram; clips are `clips/life_Step_<surface>_all4.ogg` (the four takes of each surface) and `clips/life_Bed_<name>_first12s.ogg`.
