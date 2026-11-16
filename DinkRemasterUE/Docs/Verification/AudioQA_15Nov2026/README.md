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
| `limiter_runC_before.txt`, `limiter_runE_after.txt` | Output level per 30 s with the 15 Nov limiter settings (run C) and the brickwall settings (run E). |

## Proven

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

- **Owner listening.** The picks were made by measurement and spectrogram only. Clips are in `clips/`.
- **A fist hit and Seth's bird line in actual play** are not shown in a recording. Console drives kept leaving Dink
  frozen or missing:
  - `dink.Goto` leaves Dink frozen on arrival (SCR_030, SCR_474).
  - `dink.Npc.Hold 1` freezes Dink as well as the NPCs.
  - Punches at the photoreal table use the mesh's authored bounds and missed.
  - In run C the bow sat in slot 3 behind pig food.
  - In runs H and I, eleven punches landed on nothing: five, then three with Dink walked into the round table's edge from the north, then three where his mother stands. The photoreal table and the mother use authored-geometry hits (`DinkAuthoredInteraction.cpp`), which these console drives did not satisfy. A fist hit needs a hand-driven session, or a test that drives `UDinkGameplay::PlayerAttack` against a target with a 1997 hardbox.
  - The cue path is the same one every other approved effect uses: the `attack_hit_sound` cue for hits
    (`DinkGameplay.cpp:910`, `DinkBrains.cpp:1149-1153`; the axe's strike above used it), script `playsound` for the bird (the bow above went through it).
  - Seth's bird line is reached only at the end of the game. The probe plays that fight, but headless.
- **The master limiter (bug A164, reopened).**
  - Runs C and E give the same output peaks to the sample, so the limiter added to the main submix has no measurable
    effect on the device output.
  - In play, only single samples pass -1.5 dBFS (worst -0.53, no clipping).
  - The soak's dense random mix clamps at 0 dBFS.
  - The processor settings are right: `Dink.Audio.MasterLimiterHoldsCeiling`.
  - **Fixed 16 Nov 2026:** the preset never applied those settings (the instance ran the engine's default compressor);
    cause, fix and recorded proof in `../MasterLimiter_16Nov2026/README.md`.
- **Footsteps and ambience beds** are still procedural placeholders (AU-01, AU-02).
