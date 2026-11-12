# Backlit head lines, round 3: cause bisected (12 Nov 2026)

Copy of master bf996885 (`Saved/HeroFix2Work`), private display :189, the same backlit pose as round 2
(`dink.Goto 1 165 160`, `dink.View 0 -10`, `hold w 0.4`, `dink.View 180 -3`, `fov 36`; Dink at map x 184.5-186.3).
Every test change was made at runtime through the console (`set`, `ToggleLight`, cvars) or, for T2, by a temporary
edit of the copy's `characters.json` (restored byte-identical). No asset, material, atlas or lighting file changed.

**Cause:** the lines come from the house's window rect lights (`Content/Dink/Data/Art/stonebrook.json`, e.g.
`Daylight_NorthWall_1`: kind rect, 170 lm, 5000 K, `source_width_cm` 80, `source_height_cm` 130; spawned by
`DinkArtSubsystem.cpp:348` as movable RectLightComponents that cast VSM shadows). With the 130 cm tall source the
VSM/SMRT shadow of that light lets light through along the head mesh's feature lines; with a source 80 cm tall the
lines are gone. Dink's own shadow casting plays no part, and Mother's mesh on the player shows the same lines, so it
is a scene/light setting, not the hero asset. Per the coordinator's rule the lighting was not changed.

| Test (file) | Change at runtime | Result |
|---|---|---|
| T1 (`t1_nanite_skeletal_lod_head_crops.png`, 2nd) | `set SkeletalMeshComponent CastShadow False` + `r.SkinCache.Mode 0/1` to recreate render state (log confirms `CharacterMesh0.CastShadow = False`) | Face stays dark, lines unchanged: not self-shadowing; a distant occluder shadows the face, artefact on the receiver side. |
| Nanite (same sheet) | `r.Nanite 0` | No change. |
| Skeletal LOD (same sheet) | `r.SkeletalMeshForceLOD 0` / `3` (`r.ForceLOD` does not apply to skeletal meshes in 5.8: `SkinnedMeshComponent.cpp:78-90`, round 2's ForceLOD test was void) | LOD0: unchanged. LOD3: lines follow LOD3's coarser feature lines. |
| Which light (`light_toggles_head_crops.png`) | `ToggleLight DirectionalLight` / `RectLight` / `PointLight`; `r.Shadow.Virtual.OnePassProjection 0` | Only rect lights off removes the lines (and the face speckle). Sun, point lights, one-pass projection: no change. |
| Rect light (`rect_light_tests_head_crops.png`) | rect `CastShadows False` | Face fully lit, no lines: it is the rect light's shadow. |
| Source size (`rect_source_height_head_crops.png`) | recreate only / `SourceHeight 80` / `130` again / `SourceWidth 40` x 130 | Lines / **gone** / back / still there: the 130 cm source height triggers them. |
| T2 (`t2_mother_mesh_on_player*.png`) | `characters.json` player mesh = `SK_Mother` (temporary) | Same lines on Mother's cheek, neck and scalp: scene/renderer, not Dink's head. |
| T3, T4, T5 | not run | Cause pinned before them (T5 was conditional on T1 = self-shadow, which it is not). |

Light facts read in the game (`getall`): DirectionalLight_0 movable, source angle 0.5357, CastShadows, bCastRaytracedShadow
True but `r.RayTracing 0`; 2 point lights (radius 18 cm); 6 rect lights 80 x 130 cm, movable, cast shadows; SkyLight movable.
`r.MegaLights.EnableForProject 0` (MegaLights not in use), `r.Shadow.Virtual.OnePassProjection 1`, `r.Lumen.HardwareRayTracing 1`.

## Round 3b: can a renderer setting for local lights remove them? (12 Nov 2026)

Same pose, default 80 x 130 lights, one cvar at a time, each read back in the log after setting and reset after its
frame (`local_vsm_settings_and_heights_head_crops.png`; read-back lines are in the session log). Project defaults read
in the game: `SMRT.RayCountLocal` 8 and `SamplesPerRayLocal` 4 (scalability), `MaxRayAngleFromLight` 0.03,
`ExtrapolateMaxSlopeLocal` 0.05, `TexelDitherScaleLocal` 2, `MaxSlopeBiasLocal` 50, `NormalBias` 0.5, `ScreenRayLength` 0.015.

| Setting | Result |
|---|---|
| `r.Shadow.Virtual.SMRT.ExtrapolateMaxSlopeLocal 0` | Lines unchanged. |
| `r.Shadow.Virtual.SMRT.TexelDitherScaleLocal 0` / `1` | Lines unchanged. |
| `r.Shadow.Virtual.SMRT.MaxSlopeBiasLocal 5` | Lines unchanged. The 15 frame is unusable (the camera had moved into Dink's shoulder); not repeated, since 5 made no difference. |
| `r.Shadow.Virtual.SMRT.RayCountLocal 0` (read back `"0" LastSetBy: Console`) | Lines unchanged. So the round-3 "smrtlocal0" frame without lines was really due to the source height having been left at 80, not to the ray count. |
| `r.Shadow.Virtual.SMRT.MaxRayAngleFromLight 0.01` / `0.06` | Unchanged / unchanged, and 0.06 adds heavy speckle to the face. |
| Rect `SourceHeight` 100 / 115 (80 clean, 130 default) | 100: fainter lines, still visible. 115: lines as at 130. The threshold lies between 80 and 100 cm. |

**How the size reaches the shadow (engine source).** `RectLightSceneProxy.cpp:61-63`: a rect light passes
`SourceRadius = SourceWidth / 2` and `SourceLength = SourceHeight / 2`. The VSM local-light SMRT
(`VirtualShadowMapProjectionSpot.ush:306`) uses only `SourceRadius` for its ray cone, so the height does not enter the
shadow tracing. It enters the light's area shading (`LightColor /= 0.5 * SourceWidth * SourceHeight` and the rect
integral). That fits what the frames show: width 40 still shows lines, and only the height matters.

**Verdict: no renderer setting tried removes the lines.** Nothing was changed in `Config/DefaultEngine.ini`. The
remaining remedy is the light size, i.e. Codex's light data (`source_height_cm` of the window rect lights in
`Content/Dink/Data/Art/stonebrook.json`, 80 cm clean here), and goes to the owner.
