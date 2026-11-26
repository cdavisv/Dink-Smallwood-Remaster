# M_Env_Terrain: edge-aligned mask lookup, mask warp faded at the screen rim (RimFade), 26 November 2026

The second commit of the old branch `art/terrain-layers-material` (15 Nov 2026, 17 lines in `Scripts/import_environment_materials.py`),
which never reached master. art-gore-6 (Fable 5.2, 23 Nov) found it not made moot by the landforms: master's export writes
edge-aligned layer masks (`Scripts/ground_layer_fields.py`, 96 x 64 texels a screen) but `M_Env_Terrain` still samples them at
the plain UV with a warp of 0.012 that does not fade at the rim, so layer outlines can jog by up to about 20 cm at a screen border.
Rebased onto master `6dd60a8c8`, imported, tested and captured mechanically by art-finish-1 (Opus, 26 Nov), who judged no look.
**FRAMES FOR FABLE.**

- The mask lookup maps the UV onto the texel centres (`MaskTexelsX` 96, `MaskTexelsY` 64), so two screens read the same weights
  along their shared border; the warp is halved (`MaskWarp` 0.006, `MaskWarpFine` 0.004) and fades to nothing within
  `MaskRimFade` (0.05 of the screen) of the rim.
- Package: `M_Env_Terrain` only, rebuilt by `Scripts/import_environment_materials.sh` with `DINK_ENV_MATERIALS_ONLY=1` (the run
  re-saved every terrain MI and the water materials; their content did not change and they are not in this change).

| sheet | what it shows |
|---|---|
| `01_frames_for_fable_26nov_screen_edges_before_after.jpg` | the 1997 screens 470, 471, 472, then four border spots (the east edge of 471 and 470, the south edge of 471 and 472), each before (master) and after: play camera, from above (15 m), low from the south and from the east |

The before and after frames are two runs: grass in the wind and Dink's pose differ between them, not only the ground.

Proof in copy `Saved/ArtFinish26Nov` (master `6dd60a8c8` + this change): editor build 0 warnings (no C++), game target 0
warnings, environment material import OK (22 terrain layers, 7 materials), `Dink.Art+Dink.Movement.Landforms` 92/92,
`Dink.Gameplay.Probe` 29/29 with the twenty md5s equal to the world-scale table of `packaged_probe.md` (Ch1 `ca319f4754` ...
Ch20 `be78df8ac3`). Kernel: no Oops.
