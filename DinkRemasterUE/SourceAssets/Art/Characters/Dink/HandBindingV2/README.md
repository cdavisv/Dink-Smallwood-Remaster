# Dink hand binding V2 — isolated candidate

`SK_Dink_Hands` is a separately named corrected-hand candidate for the existing Dink. It does not overwrite `SK_Dink`, its `.blend`, FBXs, textures, materials, skeleton, Physics Asset or runtime mapping. The correction changes skin hands and a smooth wrist seam only. Clothes, face, hair and all positions/weights outside that explicit region remain identical, independently verified across all four original LODs. Existing MI_Dink materials are referenced through `existing_materials`; none are regenerated or saved.

## Why the correction exists

The first hand-keyed fist exposed an oversized palm/index ring. Read-only inspection established that the original character fitter used wrist/elbow/shoulder controls without individual finger landmarks, then transferred Manny weights using nearest polygon interpolation. Native MakeHuman finger joints after that original body fit differ from the fixed reference skeleton by approximately2.3–5.4cm (right index DIP5.42cm, middle DIP5.09cm). Pose-only flexion/adduction removed a protruding finger hook but could not produce a reliable closed fist on that binding.

`hand_landmarks.json` contains the original anatomical joint controls passed through the exact original body-fit function, and the corresponding unchanged reference-rig joints. The correction maps each digit's original centerline and radial skin offsets onto its own reference chain, blends palm displacement and rolls smoothly to zero at the wrist boundary. Explicit sequential hand/phalange weights replace spatial nearest-finger copying. Each affected vertex has at most four weights and no weights from another digit family. Finger geometry and UVs are not replaced with a proxy or separate hand; the existing anatomical skin is fitted in place, retaining the original topology and texture coordinates.

The closed-fist pose now has a compact knuckle/fingerpad silhouette and thumb opposition. Tiny angular thumb-web/knuckle folds remain visible in close inspection; candidate status is intentional. Existing clothing cuff openings and simplified skin surface are outside the hand correction's scope. No gameplay reach, hit moment, collision/stat/save behavior or outfit changes are hidden in this asset.

## Exact preservation evidence

`hand_binding_report.json` records the deterministic construction. `Tools/verify_scope.py` independently reloads the original and candidate, checks every vertex and weight, asserts each change is skin inside the explicit hand/wrist region, and compares all UV coordinates, material slots and all89 rest transforms. It also checks no unweighted vertices, at most four influences and no cross-digit contamination in the changed region. `scope_verification.json` records actual changed vertex IDs and matching outside-region SHA256 pairs:

| LOD | Triangles | Changed hand/wrist vertices | Unchanged outside vertices |
|---|---:|---:|---:|
|0|31688|3298|13247|
|1|15844|1131|7439|
|2|7921|506|4032|
|3|3803|232|2181|

Maximum skin fitting displacement is6.67cm, consistent with the omitted finger-joint fit. All four original LODs are corrected independently; outside geometry is not re-decimated. UVs and all five material slot names are bit-identical. Existing sourceoriginal SHA256 is recorded. No original files are rewritten by the generator or verifier.

Source convention validation has zero errors and eleven inherited topology warnings: intentional separate clothing/hair/eye boundaries, coincident seams and original LOD1/2/3 wire-edge counts1/3/7. Those original edges are retained to avoid broadening this correction into an outside-hand topology change; triangle-only FBXs do not export wire edges as rendered faces. All four LODs have zero near-zero corner normals. The retained source warnings and tiny posed skin folds must not be described as newly perfect production topology.

## Build, export and review

From the Unreal project root:

```
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Characters/Dink/HandBindingV2/Tools/build_hand_binding.py
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Characters/Dink/HandBindingV2/Tools/export_hands.py
ALSOFT_DRIVERS=null blender -b -t 4 --python SourceAssets/Art/Characters/Dink/HandBindingV2/Tools/verify_scope.py
python3 SourceAssets/Art/Characters/Dink/HandBindingV2/Tools/inspect_exports.py
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Characters/Dink/HandBindingV2/Tools/review_gesture.py
python3 SourceAssets/Art/Characters/Dink/HandBindingV2/Tools/prepare_hand_ledger.py
```

The original asset and cached anatomical controls are inputs. `../../Animations/Unarmed/Dink_Fist.blend` supplies the separate own-authored source motion for review; its generator uses this candidate for preview once present. This preview dependency does not change hand construction or the rig. Delivered source checkpoints make either review reproducible. `Previews` includes idle, wind-up, impact, side impact, recoil, closed-hand close-up and a separate open-palm gesture proving digit separation.

`SK_Dink_Hands.blend` remains editable in metres on the exact89-bone rig. Temporary FBX export alone converts geometry/edit-bone coordinates×100, scene0.01/header1cm, identity root, Armature wrapper and no leaf bones. Each of the four FBXs has one mesh and all89 bones. Material graphs are cleared only in the temporary export process; saved source links stay intact and point to existing character textures. No new texture bake is required.

`hand_manifest.json` uses `dink-character-art/1`, Characters-relative source paths, `/Game/Dink/Hero/Refinements`, a `player` candidate mapping, empty placements/materials and explicit five existing-material references. Parent-controlled `Scripts/import_dink_hand_art.sh` selects this local manifest and merges runtime entries only when deliberately invoked. `hand_import_preflight.json` records read-only schema/path/binary-FBX/bounds/material-presence checks and importer syntax checks; it does not claim Unreal import or runtime QA. The live editor/game slot remains parent/collision owned.

## Provenance

Existing body/skin/hair/eyes originate from the documented CC0 MakeHuman pipeline; original project clothes remain unchanged. The per-digit correction, explicit weights and validation tools are original project work. The existing Epic89-bone hierarchy/reference transforms retain Epic terms and are not relabeled CC0. No new third-party model, texture, paid generation or download was used. Shared source ledgers and global character manifests are parent-coordinated; local rows stay candidate pending staged review.

## Later change (9 Nov 2026)

The cuff openings, chest dimples and floating buckle were then fixed in both `SK_Dink.blend` and this candidate by `../DefectFixes_9Nov2026/Tools/fix_hero_defects.py` (see `../../README.md`, "Dink defect fixes"); the hand fit itself is unchanged and `Tools/verify_scope.py` passes again on the fixed pair. `scope_verification.json` now carries the new outside fingerprints; `Export/` was re-exported.
