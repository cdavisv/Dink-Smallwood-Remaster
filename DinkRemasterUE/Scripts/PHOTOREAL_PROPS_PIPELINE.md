# Portable photoreal props workflow

The pipeline imports three Blender-authored furniture meshes, three baked materials and nine textures, and changes exactly eight mesh references after guarded verification. Native import, independent saved-package verification and fresh read-only verification of the published stage have passed. See `Docs/Verification/PhotorealPropsNative` for historical and current evidence. The native source filename getter matched all twelve selected source files in the authoring stage; a fresh relocated clone remains a separate portability check. Rendered door exit/return and 12 interaction cases passed, with combined lighting and hero acceptance still pending.

Run native commands only in an owned isolated checkout whose game is stopped. Runtime files are `import_photoreal_props.py`, `publish_photoreal_props.py`, `props_contract.py`, and the unchanged `props_fbxparse.py`. The existing editor-only read-only DinkImport convex bridge remains required; this revision changes no C++.

## State and trust origin

| Operation | House references | Candidate packages | Required private receipt |
|---|---|---|---|
| preflight | exact all-old eight references | empty, including allowed sidecars | none |
| import | exact all-old eight references | empty, including allowed sidecars | none |
| verify before publication | exact all-old eight references | all fifteen saved packages | successful matching import receipt |
| fresh verify after publication | exact all-new eight references | all fifteen saved packages | none |

Mixed old/new references, missing rows, wrong identities and additional matching references are rejected. Three asset rows, three replacements (`S001_P22/P23/P24`) and two decorative elements (`Chair1/Chair2`) remain the exact contract.

Published verification uses `verification_basis: published_entry_state`, `publication_state: published`, `scene_data_approval: false`, and `writer_scope: none`. The complete candidate package/optional-sidecar set and hashes come from the **entry Content inventory before native objects load**. Every candidate mesh, material and texture is then independently inspected against the selected frozen source: oriented/bijective actual-delta matching and geometric fronts, physical bounds/pivots/material indices, native transformed hulls/closed indices/convexity, Nanite/fallback settings, every direct saved material graph including hidden pins, native Texture.Source pixel identity, color/normal/ORM flags and resolved source filenames. All three old kit baselines still load read-only and must pass original geometry/material/collision checks.

Candidate entry hashes are retained, never replaced with freshly observed exit bytes. Complete candidate set/hash comparisons occur at entry, after loaded inspections and as the final guard, together with source/tool/current Data/protected Content checks. An addition, deletion or modification during inspection fails even if the editor still holds the old loaded object.

Unpublished verification continues to require and bind the successful import receipt. Source/tool/Data/old-package/native baseline comparisons and exact import candidate bytes remain unchanged; this path cannot silently fall back to a current-state baseline if the import receipt is missing.

## Native invocation

Use the existing private owned-project NullRHI commandlet arrangement. Set `DINK_PROPS_MODE=verify` and `DINK_PROPS_SOURCE=<selected own source bundle>`. The default receipt is `Saved/Art/photoreal_props_verify.json`; `DINK_PROPS_REPORT` may select another path under project Saved. `DINK_PROPS_IMPORT_RECEIPT` is needed only for the unpublished all-old chain. In the published branch it is neither opened nor resolved, and no private publication receipt is read.

The fifteen packages remain three meshes in `/Game/Dink/Props/Stonebrook/PhotorealPropsV1`, three materials in `/Game/Dink/Materials/Stonebrook/PhotorealPropsV1` and nine textures in `/Game/Dink/Textures/Stonebrook/PhotorealPropsV1`. Optional `.uexp`/`.ubulk` files are allowed only for those stems and are included in hash inventories. Content must remain an owned real tree rather than symlinked shared Content.

The importer reads the selected bundle's actual current `final_handoff.json` and all manifest-bound consumed payloads. No old author handoff hash or Work path is hardcoded. `prepare_photoreal_props_plan.py --source <bundle> --out <plan.json>` performs a pure source audit and emits package/source/tool plans; it does not emit a native pass.

## Native source filename portability

The mesh and texture `AssetImportData.extract_filenames()` **native getter** is used for three FBX and nine PNG source records. Installed UE5.8.4 `AssetImportData.cpp` routes `K2_ExtractFilenames` through `ResolveImportFilename`, resolving stored filenames relative to the asset package or configured source folder and returning absolute filenames. `AssetImportData.h` explicitly documents resolved/absolute getter output.

Each resolved native filename must identify exactly the selected bundle's expected file and its manifest-bound SHA256. Stored relative text is not compared naively with an absolute filename. A still-relative getter result, matching basename, matching bytes in the old author checkout, missing/extra source files, or source hash drift is rejected. The code does not guess a working directory or substitute the selected file when the native getter disagrees. The authoring-stage native check established actual getter ownership for all twelve source records. Relocated-clone execution is recorded separately and must pass without changing stored asset data or guessing source locations.

`native_source_filenames` contains twelve source-relative file roles, resolved own-source paths and hashes. The publisher rechecks this proof against the selected bundle along with the complete asset verification receipt.

## Publisher behavior

Run `publish_photoreal_props.py --project <owned project> --source <same bundle> --verification <fresh verify receipt>` to check. For a fresh-published receipt, both the default command and `--apply` are **zero-write checks**: target bytes remain identical, no lock/temp/output/publication receipt is created, and no private Saved receipt is required. Results report `already_published: true`, `applied: false`, `changed_mesh_references: 0`, and `writer_scope: none`.

Fresh-published checks require an explicit published-entry receipt, exact all-new current references, current house semantic and byte hashes, unchanged complete runtime Data/Content sets, unchanged source/tools, old baseline packages and all current candidate package hashes. House transforms/story/PP/data files, assets, source pixels or code changed **after verification** are rejected. A stale published verification cannot authorize a later controlled merge: root runs full fresh native asset verification again against the new context.

The existing unpublished authoring chain still changes only eight mesh strings after successful import→verify. It retains its atomic target write, source/tool/Data/package guards, exact old semantic baseline, private publication receipt and byte-bound idempotence. The fresh-published trust origin cannot be relabeled to publish an all-old or mixed scene.

## Asset verification is not scene approval

A fresh verification pins current Data as a protected **context**, including legitimate reviewed PP/skirt merges. It does not review or approve story content, transformed scene layout, lighting policy, scripts, saves or arbitrary pre-entry edits. Its explicit `scene_data_approval: false` and no-writer scope are essential: fresh-published publication checks never write that context or create authority to alter it. Those edits retain their own review and native acceptance gates. This separation permits normal clones and later approved merges without depending on a private author's Saved folder or laundering scene edits through an art receipt.

## Preserved native contracts and tests

Legacy FBX header factor100/import scale1, source normals with generated MikkTSpace tangents, one baked slot/polygon group0, Nanite/full fallback, unchanged complex-as-simple query policy, retained authored hulls18/16/13, direct BC/N/ORM+specular.35 graphs, BCsRGB/Ngreenflip/ORMlinear with neutralR255/B0 remain intact. Geometry matching is cyclic and bijective within the established0.01cm/0.0001UV actual limits, with geometric-front agreement; hull/vertex matching uses the same0.01cm limit. The read-only native bridge returns actual GetTransform/local+mesh-space vertices/indices. Native per-corner shading-normal attributes remain unexposed; saved import/build flags and actual geometric fronts are separately checked.

Run `python3 -m unittest discover -s Scripts/tests -p 'test_photoreal_props_*.py' -v` from the project directory. The68 tests include normal published clones without any private Saved tree, zero-write repeated checks/applies, partial-state refusal, unpublished missing-import refusal, both entry/exit package drift, source/tool/Data/package tamper, mixed identities, scene-context/no-writer semantics, native-getter filename ownership, all previous publication guards and numerical/winding/convex matching regressions. Fixtures are synthetic and need no LFS/native assets. Python compilation and the pure source audit are separate checks. Fresh-published native verification and source filename ownership passed in the authoring stage; scene and relocated-clone acceptance retain their own evidence and limits.
