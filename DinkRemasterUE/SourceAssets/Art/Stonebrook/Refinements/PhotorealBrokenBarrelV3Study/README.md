# Broken barrel V3 — inactive LOD0 source study

This versioned study retains the exact frozen Blender source `bf95cae9…` and five actual CPU presentation renders. Original identity is `barrel_broken`, sequence173/frame6; `bar-gh.c` persists that picture after breaking. Sequence174 is a palette variant. Existing original references and V2 shared-material policy remain at `../PhotorealBrokenBarrelV2/References` and `POLICY_INTERPRETATION.md`; they are referenced, not duplicated or changed.

Open `portable.source.blend`, collection `V3_Editable_SplitStaves_SharedPBR`. The36 editable pieces total9,928 triangles and measure1.03491×1.23787×0.19663m, with minimumZ approximately1mm. Four staves have real longitudinal splits, four small fibre tips, three overlaps are less regular and one iron strap end is bent. All36 meshes reopen closed/manifold with positive volume, finite positions/UV/corner normals and no zero-area triangles. Decorative intersections are intentional; no collision or physical settling proof follows.

Every proposed piece uses only `MI_Shared_OakLonggrain2m`, `MI_Shared_OakEndgrain2m` and `MI_Stonebrook_WroughtIron`. These three graphs and nine packed PBR map bytes match the preferred V2 source exactly. Existing project-relative library references are `SourceAssets/Art/SharedMaterials/manifest.json` and `SourceAssets/Art/Stonebrook/art_manifest.json`. No library, registry, private bake or material was authored here. The frozen file also retains hidden old28-piece/V2LOD archives and a hidden REVIEW_ONLY intact comparison with its pre-existing private parent materials. That comparison is not proposed broken-pile material or an export object; preserving the frozen source does not approve those context materials for production.

The immediate source parent is the off-tree preferred multi-node V2 study `9d97fee5…`; its unchanged28-piece archive is embedded in this file and independently matches that parent. The published V2 source `42ff8227…` is an earlier ancestor, not asserted byte/array identical to the derived multi-node parent. No extra large parent file is needed to reopen or reconstruct this V3 geometry. `Evidence/READY.json` preserves the original QA freeze, including rejected first-pass fingerprints; those rejected binaries are not duplicated here.

## Portable geometry reproduction

Use Blender5.2.2 and a new disposable output outside this bundle:

```sh
taskset -c 0,1 nice -n 10 blender -b -noaudio -t 2 --python Scripts/reproduce_geometry.py -- --output /tmp/broken-v3-new
taskset -c 0,1 nice -n 10 blender -b -noaudio -t 2 --python Scripts/verify_portable.py -- --output /tmp/broken-v3-baseline.json
taskset -c 0,1 nice -n 10 blender -b -noaudio -t 2 --python Scripts/verify_portable.py -- --input /tmp/broken-v3-new/PhotorealBrokenBarrelV3_Refinement.blend --output /tmp/broken-v3-reproduced.json --compare /tmp/broken-v3-baseline.json
```

Run from this bundle. The recipe reads the pinned self-contained source, removes only the proposed V3 objects in memory, and reconstructs them from the embedded unchanged original28 archive using the actual authoring operations. It saves only a fresh disposable output; it does not rerender or overwrite the five frozen images. Relocated reopening and actual reconstruction/reopening closed0 on CPU affinity0,1; all36 per-object geometry/transform/topology/UV/normal/material-slot signatures, three material graphs and nine map bytes compare exactly. Blend save hashes differ and are recorded honestly. No linked libraries or unpacked file images are required. Raw authoring scripts under Evidence describe original QA origins and are historical, not portable entry points.

## Limits and policy

This is an **inactive LOD0-only study, not final photoreal art**. The pile still reads as straight flat boards and the fractures remain too planar/uniform. The hidden V2LOD1/2 are historical comparisons, not V3 reductions.9,928triangles exceeds the prop6,000soft target but stays below20,000hard cap. No new LODs, FBX/exports, native material/UV/TBN import, game-camera, cook, performance or gameplay validation is claimed.

The prior generic-guide UV-overlap and missing-UCX findings remain failures, openly preserved in the V2 archive. ART_STANDARD explicitly takes precedence and requires shared tiling materials (§2) and visual-only family dressing (§5); this source archive does not invent UCX, shrink UVs, change class, waive a gate or implement a validator policy. Role-qualified export/native acceptance remains unresolved. Source publication only does not activate the family or change collision/navigation, runtime scripts, current art, Data, Content, audio, registries, caches or native stages. Original sources and all old ledger bytes remain unchanged.
