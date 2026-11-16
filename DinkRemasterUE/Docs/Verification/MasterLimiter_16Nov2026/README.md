# Master limiter on the device output (bug A164), 16 Nov 2026

## What was wrong
`UDinkAudioLifeSubsystem::EnsureLimiter` added a peak limiter at -1.5 dBFS to the main submix. Recorded runs showed it had no effect:
- runs C and E had different limiter settings but gave identical output peaks;
- the soak reached 0 dBFS (see `../AudioQA_15Nov2026/limiter_runC_before.txt` and `limiter_runE_after.txt`).

The effect was on the device path, but it was not running the limiter's values (UE 5.8.4 source):

1. `USubmixEffectDynamicsProcessorPreset::SetSettings` calls `UpdateSettings`, which writes only the preset's thread-safe `SettingsCopy`
   (`Engine/Classes/Sound/SoundEffectBase.h`, macro `EFFECT_PRESET_METHODS`).
2. `UAudioMixerBlueprintLibrary::AddMasterSubmixEffect` (`AudioMixer/Private/AudioMixerBlueprintLibrary.cpp:86-98`) makes the instance with
   `USoundEffectPreset::CreateInstance`, which calls `AddEffectInstance` (`Engine/Private/SoundEffectPreset.cpp:36-45`). For the first
   instance of a preset that runs `Init()`, which is `SettingsCopy = Settings`.
3. `Settings`, the property, was never set. It held the engine defaults (`AudioMixerSubmixEffectDynamicsProcessor.h`): a **compressor**
   at -6 dB, ratio 1.5, 10 dB knee, 10 ms attack, 3 ms look-ahead, analog detector. `OnPresetChanged` read those defaults
   (`AudioMixerSubmixEffectDynamicsProcessor.cpp:89-150`).

So every run since the limiter was added played through a mild default compressor, whatever values the code set. The main
submix's dry path (`DryLevelModulation` default -96 dB) and the effect-chain fade were checked and are not involved.

## Fix
- `FDinkAudioMix::MakeLimiterPreset` sets `Preset->Settings` and calls `SetSettings` with the same values (`DinkAudioLife.cpp`).
- The log line now prints the settings the instance actually uses:
  `Audio: master limiter at -1.5 dBFS (type 1, attack 0.0 ms, look-ahead 0.0 ms, release 80 ms, analog 0)`.
  Type 1 is Limiter; before the fix it was type 0, Compressor.
- The brickwall values of #183 are kept: zero attack, no look-ahead, digital detector, 80 ms release.
- Pitfall 84 in `DinkRemasterUE/AGENTS.md`.

## Proof
- **Test** `Dink.Audio.MasterLimiterPresetHoldsCeiling` (new). It builds the preset, makes the instance the way
  `AddMasterSubmixEffect` does (`CreateInstance`, `SetEnabled`) and runs `FSoundEffectSubmix::ProcessAudio` (which applies the preset)
  on 6 channels in 1024-frame blocks with +6 dBFS hits and a tone.
  - Output -1.50 dBFS with `MakeLimiterPreset`.
  - +6.00 dBFS with the old SetSettings-only preset, whose instance ran type 0 (compressor) at -6.0 dB. This half pins the defect.
- **Tests on the build** (master 84e045b0 + this branch, 133 s, 0 warnings): `Dink.Audio+Dink.Gameplay.Probe` 39/39 passed in 552 s.
  All twenty probe chapter md5s equal `Plugins/DinkParity/Docs/packaged_probe.md` (ch1 b4ad88c02c .. ch20 84f33687af).
- **Recorded run F1** (`Scripts/AudioQA/run_recorded.sh`, SDL disk driver: the device mix written to a file, never played; `steps_runF1.txt`).
  The opening scene (the fire loop beside Dink, the mother's scene), the menu closed, then `dink.AudioQA.Soak 300`:
  a random approved effect every 80 ms, music every 15 s, sea/wind bed; up to 175 sounds playing at once.
  - `levels_runF1.txt` (same tool and windows as runs C and E) and `levels_all_runF1.txt` (all six channels).
  - Peak **-1.50 dBFS in every 30 s window**: exactly 0.8414232 = -1.49971 dBFS against a ceiling of 0.8413951, 0.0003 dB over by float
    rounding. No sample is 0.001 dB over, and **no sample reaches 0 dBFS**.
  - Soak RMS (front pair) -7.3 to -9.4 dBFS, as hot as run E's -8.0 to -9.5, so the limiter was driven as hard as there.

| | run C (15 Nov settings, ran as default compressor) | run E (brickwall settings, ran as default compressor) | run F1 (fix) |
|---|---|---|---|
| opening 0-30 s peak | -0.53 dBFS | -0.53 dBFS | -1.50 dBFS |
| soak, samples >= 0 dBFS per 30 s | 333 - 4,126 | 24 - 2,612 | 0 |
| soak peak | 0.00 dBFS (clamped) | 0.00 dBFS (clamped) | -1.50 dBFS |

- Captures from run F1 (looked at): `runF1_01_intro.jpg` (opening scene, fire beside Dink), `runF1_02_house.jpg`, `runF1_03_soak_mid.jpg`,
  `runF1_04_after_soak.jpg`.

## Not checked
- Nobody has listened to run F1. A zero-attack limiter driven this hard by the soak (up to 6,600 samples per 30 s at the ceiling)
  distorts low frequencies while it limits. In normal play the opening has 1-4 samples per 30 s at the ceiling.
- Packaged build: not run (the code path is the same as in the editor's -game mode).
- Full `Dink` suite: not run. Only `Dink.Audio` and the probe: the change touches only the limiter preset and a test.
- In `runF1_03_soak_mid.jpg` the camera sits right behind Dink's head inside the house. That is camera framing, unrelated to audio,
  and is not filed here.
