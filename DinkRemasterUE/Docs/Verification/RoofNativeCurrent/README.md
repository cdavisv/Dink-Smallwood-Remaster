# Current roof delivery validation

The roof candidate passed its own Editor/Game builds, 187 native tests, fresh saved-asset readback and an actual-input doorway round trip. This proves the candidate on runtime base `5d65ed88`; integration with newer owner decisions and audio acceptance remains pending.

The readback verified 50 packages, 10 meshes, 12 LODs, 48,090 triangles, 312 convex hulls, 25 texture sources and 15 materials, with no imports, saves or protected-input changes. Tangent-Y handedness is still unproven. Native tests include 30 successful cases with HTTP/EOS warnings; the first cold focused readiness timeout remains recorded.

The GPU run used real held W input with scripts enabled and movement unlocked. Exit `1 -> 439` and return `439 -> 1` passed. It produced 26 screenshots and closed the owned game and private display normally; all 12,703 protected inputs remained unchanged.

## Confirmed camera defect

The exterior cottage's `BlockAll` collision retracts the 400 cm camera arm to about 106 cm. A matching Camera-channel sphere sweep reproduced the actual camera position with zero error. [Baseline screenshot](door-camera-before.png) shows Dink's head clipped.

A temporary 80 cm vertical pivot [study](door-camera-height-study.png) keeps the head visible while retaining wall collision. A lateral trial was rejected because it put the camera inside the unlit exterior shell. These are experiments, not a shipped fix. The original numeric camera offset was restored and verified before quitting.

[Interior screenshot](starting-house-interior.png) documents the current starting house. It is not final photoreal art approval. Shared material/source-record compliance, character appearance and exterior quality remain open.

`results.json` records measured results, image hashes and limitations. Detailed raw runs are retained in the coordinating workspace under `DinkQA/RoofNativeDeliveryReadbackPreparationV2` (run `3f40f576a0364003958866dce45ab033`) and `DinkQA/RoofNativeDeliveryGPUPreparation` (run `6db9b610-72fe-43bb-9f25-8c554844c039`). No credentials or private display authority are included here.
