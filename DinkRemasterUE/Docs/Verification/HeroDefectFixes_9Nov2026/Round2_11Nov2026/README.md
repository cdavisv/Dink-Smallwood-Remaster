# Hero defect fixes, round 2: in-game frames (11-12 Nov 2026)

Owner request (11 Nov 2026): fix the faint crease left on Dink's right chest and the bright seam-like lines on his
head when he is backlit (both seen in the 11 Nov after-shots one folder up). Result: **chest crease fixed; head lines
diagnosed, not fixed.** Source changes and the diagnosis: `SourceAssets/Art/Characters/README.md`, section "Dink
defect fixes, round 2 (11 Nov 2026)".

**How the frames were taken.** Private reflinked copy of master 95621dd (`Saved/HeroFix2Work`), `Scripts/build.sh`
BUILD OK, the real game (`-game`, 1280x720) on the private display (`Scripts/private_qa_session.py`, Xvfb :189, RX 6800),
driven with `Scripts/playtest_desktop.py --private-display :189`. Poses as on 11 Nov: backlit = `dink.Goto 1 165 160`,
`dink.View 0 -10`, `hold w 0.4` (Dink ends at map x 185-186), `dink.View 180 -3`, `fov 36`; sunlit front = `dink.Goto 1 146 162`,
`dink.View 0 -10`, `hold w 0.15`, `dink.View 180 -4`, `fov 60`. Crops come from `HighResShot 3840x2160` of the same pose.
"Before" is the copy's 9 Nov content; "after" is the same copy with SK_Dink and SK_Dink_Hands re-imported from
`SourceAssets/Art/Characters/Dink/DefectFixes_11Nov2026/` (materials and atlas untouched). Nothing was retouched; the
diagnostic sheets are plain crops of whole frames with a label strip.

| File | What it shows |
|---|---|
| `before_front_sunlit.png`, `after_front_sunlit.png` | Sunlit front pose, whole frame, before and after. |
| `before_front_upper_body_crop_from_4k.png`, `after_front_upper_body_crop_from_4k.png` | 4K crops of those poses. Before: the short dark tick on his right chest (screen left of the placket, a third of the way down). After: gone. |
| `compare_chest_crop_from_4k.png` | The chest of both crops side by side. Left: the crease. Right: smooth cloth on both sides of the placket. The dark banding beside the placket and the speckle on the face are unchanged renderer shadow artefacts (noted on 11 Nov), not geometry. |
| `before_backlit.png`, `after_backlit.png`, `compare_backlit_head.png`, `*_backlit_head_crop_from_4k.png` | Backlit pose. The lines on the scalp, cheek, jaw and neck are there before and after: **not fixed**. |
| `prefix_e417231_backlit.png`, `compare_backlit_head_9Nov_vs_e417231.png` | The pre-PR #51 player mesh (e417231 `SK_Dink_Hands.uasset`, swapped in temporarily) in the same pose: the same lines in the same places, so they **predate the 9 Nov re-export**. |
| `diag1_head_crops.png` | Lines stay with `r.ForceLOD 0`, `ShowFlag.Specular 0` (face lines stay, scalp lines go: they are specular on the hair), `ShowFlag.Translucency 0`, `r.MipMapLODBias -4`; gone with `r.Shadow.Virtual.Enable 0` (that frame has no shadows at all); `viewmode unlit` shows no line (no crack, the background never shows through). |
| `diag2_head_crops.png` | World-normal buffer smooth (no normal seam); `ShowFlag.DirectLighting 0` removes them (they are direct light); unchanged with contact shadows off, SMRT ray count 0, VSM normal bias 0 or 3, VSM resolution bias -2, `r.SkinCache.RecomputeTangents 0`, Lumen off. |
| `diag3_head_crops.png` | `ShowFlag.DynamicShadows 0` lights the face fully, no lines; **VSM off with cascaded shadow maps: face shadowed, no lines** (the lines are specific to virtual shadow maps); unchanged with early-Z off, skin cache off, VSM cache off, slope extrapolation 0. |
| `test_padded_atlas_head_crops.png` | Test: atlas fully edge-padded (every texel outside the UV islands filled, island texels identical), re-imported: lines unchanged, so not a texture-border effect. Reverted. |
| `test_no_head_uv_seams_head_crops.png` | Test variant: every head UV collapsed onto one skin texel (so no UV seam and no vertex split on the head): the cheek and jaw lines stay (more lines show on the now skin-coloured hair cap). The lines are not caused by the UV seams as such. Reverted. |
| `test_seam_vertex_snap_head_crops.png` | Test variant: seam vertices snapped to a local surface fit (<= 2.5 mm): the scalp loop is fainter, the face lines are unchanged. Not adopted. |

**Verdicts.**
1. **Chest crease: fixed in play** (`compare_chest_crop_from_4k.png`), both sides now shade alike.
2. **Backlit head lines: not fixed.** They predate 9 Nov. They are direct light that the virtual shadow maps let through
   on the head under grazing light; no texture, material, normal, LOD, crack or UV-seam cause survived the tests above.
   Working explanation: VSM self-shadowing resolves the facets of the low-poly decimated head (its sharpest edge chains
   run along the UV-seam loops the decimator kept), which smooth normals otherwise hide. A denser head (LOD0 rebuilt from
   the undecimated source, or a gentler head decimation) is the next thing to try, checked in this same pose.
