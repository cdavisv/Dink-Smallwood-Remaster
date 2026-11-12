# Interior gable recess source candidate

This additive source candidate repairs the starting-house roof's dark triangular plaster/timber junction slivers in matched Blender views. Root visually accepted the off-tree recess20mm study as a source candidate. It is not imported, activated or accepted natively. The existing InteriorRoofSharedV1 source, FBXs, references and open native issue remain unchanged.

`InteriorRoof_GableRecess20mmCandidate.blend` is the exact accepted editable source (SHA785af1ffefcba86aa8ffd3232973b7f99a67758f9c045a6c8964b9d4c97dd3df). It derives from the existing [InteriorRoofSharedV1 source](../InteriorRoofSharedV1/InteriorRoof_Shared2mCandidate.blend), SHA5c87f7f4b295ea7c34057f7aa5548e55c9a3db9efedda748e66b91347f7fe745. The original and rejected35MB control are referenced, not duplicated here. All binaries remain Git LFS assets.

Only four gable end slabs change:102selected cap vertices include9fixed exterior vertices;93vertices per gable actually move in X, at most20mm, all above worldZ3.5m. The room-side plaster recedes behind existing timber caps while the exterior faces and world bounds stay fixed. Authored cap normals follow the positive-depth inverse-transpose transform. No beams or materials are hidden. The original architectural silhouette, shared oak/lime look, UVs, topology, material slots, object transforms and all312UCX remain exact. The eight roof meshes retain17322triangles; no new degenerate or reversed triangles were found.

Matched camera/light/24sample CPU images are in `Review/`: before/after gable and junction crop.28inward-facing near-coplanar triangle pairs became0; summed overlap area6.418m2 became0 (pair sums, not union area). All16384 sampled gable rays retain exactly8752opaque hits. Outward/other inherited coplanarity and duplicate-face warnings are not globally fixed. Discrete rays do not certify manifold watertightness or native collision.

`Evidence/CANDIDATE_RECEIPT.json` preserves the exact original off-tree receipt, including historical QA paths and rejected-control references; those are provenance, not operational dependencies. Compact original measurement records are also retained. `Evidence/SOURCE_VALIDATION.json` records actual relocated reopening and portable regeneration:328mesh signatures and all22packed image payloads/sizes/color spaces agree; no linked libraries or unpacked file images are required. Historic image filename strings are retained inside packed data. No private path is needed to open this blend.

## Portable source recipe

Hydrate the original source's LFS object before regeneration. Run Blender5.2.2 CPU against the project root and a NEW empty disposable output directory outside the project/bundle:

```sh
blender -b -noaudio -t 2 --python Scripts/repair_gable.py -- --project-root /path/to/DinkRemasterUE --output /tmp/gable-repair/Candidate.blend
blender -b -noaudio -t 2 --python Scripts/repair_gable.py -- --inspect /tmp/gable-repair/Candidate.blend --report /tmp/gable-repair-check.json
```

The recipe pins the original5c87payload, changes only the bounded cap coordinates/normals, checks unrelated mesh/UCX signatures and refuses overwritten or protected outputs. It contains no Unreal operation or export. The actual portable regeneration reloaded with exactly the selected candidate's328mesh signatures and packed image bytes. Its binary hash differs because it retains original scene lights/cameras rather than the review setup; no false binary-reproduction claim is made.

The first portability check refused before save because its assertion confused selected102 with moved93; the corrected check retains both counts. Failure log hashes remain in SOURCE_VALIDATION. Two initial read-only inspection processes completed then remained in futex wait, including one with-noaudio; only exact verified owned PIDs were stopped. The cause is unproven. Recipe exits after synchronous writes to avoid that observed shutdown wait.

No Content, Data, runtime manifest, material registry, Engine, native package or collision policy changes are delivered. Unchanged UCX may extend20mm inward of recessed plaster above3.5m; later native ownership, export, package reload, geometry/collision and rendered validation must be separately reviewed. The Blender improvement does not establish the native artifact's cause or fix, global art completion, final performance or gameplay acceptance.
