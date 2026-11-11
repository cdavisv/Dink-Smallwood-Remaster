# Photoreal broken barrel V2 — source candidate

Root visually accepted the low radial debris and jagged fracture as a **source art candidate**. No native, final-art, collision or gameplay acceptance is claimed. No Content/Data/runtime bindings or existing sources were changed.

Original identity: `barrel_broken`, sequence173/frame6, `barel-06.bmp`. The original `bar-gh.c` persists173/6 after a hit. Sequence174 is a palette variant, not the broken state. References retain exact original173/1 and173/6 pixels and archive/BMP provenance. The family remains unbound.

The packed editable `PhotorealBrokenBarrelV2_Source.blend` contains28 debris pieces:18 curved staves with uneven longitudinal fibre tips, six head/bung components and four opened forged straps. They retain original barrel scale and the flat radial broken silhouette. Target geometry totals9,624triangles (above6,000soft target, below20,000hard cap), footprint103.491×121.467cm, height18.863cm, minimum floor clearance1mm. Decorative overlaps are deliberate; no rigid-body-settled/intersection-free claim is made. No collider is included.

All target material slots are exactly `MI_Shared_OakLonggrain2m`, `MI_Shared_OakEndgrain2m` and `MI_Stonebrook_WroughtIron`. Full node types/properties/default inputs, links and packed texture/color-space signatures match the pinned shared library and original shared-iron graph. No private bake or material exception is proposed. The hidden intact private-material review object and unused private data were removed from this delivery copy; V1 remains only in the historical comparison image/QA archive.

`Previews/V1_private_material_before.png` and `V2_shared_material_after.png` have identical camera, lighting, scale and floor. V2_top is the inspection view. These are actual Blender CPU renders, not game captures. Removal of unused review data changes the Blend binary but preserves every accepted target position/transform/topology/UV/grain/normal/material signature exactly. The file reopens independently with all file images packed and no linked libraries.

**The raw generic guide has2errors and remains a failure report.** See POLICY_INTERPRETATION.md for exact existing policy quotes and a proposed role-qualified validator clarification. No fakeUCX, semantic reclassification, UV shrinking, tolerance change or hidden error filtering was used. Root reviewed the explicit ART_STANDARD precedence and cleared source-only archival publication with both raw findings disclosed. A role-qualified export/native validation contract remains unresolved; this source-publication decision is not export readiness or activation approval. Source geometry checks pass; no full-guide/native acceptance follows from that.

## Portable reproduction

The existing intact parent (SHA0fcb284a...,41,714,054bytes) and shared library (SHAbcff2725...,8,601,889bytes) are already tracked/ledgered on master2a18d7c and are not duplicated here. Hydrate those exact LFS objects:

```sh
git lfs pull --include='DinkRemasterUE/SourceAssets/Art/Stonebrook/Refinements/PhotorealBarrelV1/PhotorealBarrelV1_Source.blend,DinkRemasterUE/SourceAssets/Art/SharedMaterials/OakLime2mV1/Shared2m_LibraryCandidate.blend'
blender -b -noaudio -t 2 --python DinkRemasterUE/SourceAssets/Art/Stonebrook/Refinements/PhotorealBrokenBarrelV2/Scripts/build_broken_barrel.py -- --project-root "$PWD/DinkRemasterUE" --output /tmp/broken-barrel-v2-new
blender -b -noaudio -t 2 --python DinkRemasterUE/SourceAssets/Art/Stonebrook/Refinements/PhotorealBrokenBarrelV2/Scripts/finalize_source.py -- --project-root "$PWD/DinkRemasterUE" --input /tmp/broken-barrel-v2-new/PhotorealBrokenBarrelV2_Source.blend --output /tmp/broken-barrel-v2-new/Clean/PhotorealBrokenBarrelV2_Source.blend
```

Use a nonexistent disposable output outside the project. The first step also renders the intact reference in the disposable output; the second removes that private-material review object and unused data. Only the Clean source is the delivery equivalent. No FBX, Unreal invocation, package save, import, activation or project write is performed. The actual two-step reproduction closed0; all28 target geometry/transform/UV/grain/normal/material slots and all three complete material graphs match the accepted selection/delivery. Blend file hashes differ across saves and are recorded separately, never asserted binary-identical. Evidence paths describe original QA origins; the recipes have no machine-specific path dependency.

The source candidate inherits the original Dink/project-authored coopered oak/iron and generated-oak provenance. Nothing is relabeled CC0. Native export/import/material bindings, original script/drop/save/reentry behavior, no-collision/no-navigation, player-camera art and performance remain untested for this broken asset. All old/frozen sources and stage failures remain preserved.
