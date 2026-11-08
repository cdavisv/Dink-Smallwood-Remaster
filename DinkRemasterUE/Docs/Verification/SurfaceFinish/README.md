# Starting-house oak floor and closed sky seams

The old floor showed oversized wavy grain and thin blue sky through real gaps between boards. The new Blender oak surface uses finer irregular grain and matte microrelief. A separate dark sheet beneath the boards covers those gaps. It has no collision, navigation, overlap events or camera-occluder tag and is visible only in the owning interior.

| Check | Evidence |
| --- | --- |
| Native editor suite | [139/139, zero warnings,436seconds](native-full.json); [8,835 input pins](native-input-pins.json) unchanged through final rendering |
| Saved native assets | [Floor copy](floor-saved-verify.json) preserves all geometry/UV/triangle groups/nail metadata/collision/Nanite; [underfloor](underfloor-saved-verify.json) has24vertices/44triangles,0collision, no nav, correct contour/dimensions |
| Saved shader recipe | [Eight real Unreal mutations rejected](shader-mutations.json), including reused nodes on WPO/emissive; [native hidden-input test](native-inspector-test.txt) passes |
| Portable publication guards | [91 Python tests](python-tests.txt), including20 source/Data/package drift and idempotence controls |
| Real doorway movement | [Actual exit](Rendered/AfterFinal/actual-exit.json), [actual return](Rendered/AfterFinal/actual-return.json), [receipt](Rendered/AfterFinal/receipt.json) |
| Underfloor runtime policy | [Hidden outside](Rendered/AfterFinal/actual-outside-underfloor.json), [visible inside](Rendered/AfterFinal/actual-return-underfloor.json), no collision/nav/overlaps/hidden shadows/GI |
| Camera and seams | [Matched numeric camera contracts; both floor ROI blue counts become0](seam-comparison.json). Before380/726, oak-only341/762, final0/0. No image edits, global light/exposure or camera-component setters |
| Exterior camera | [400cm after the real exit](Rendered/AfterFinal/outdoor-after-exit-camera.json) |
| Build/cook | [Linux Development package,0warnings,62seconds](package-verification.json); [seven actual IoStore packages](container-verification.json) |
| Packaged runtime | [Ten chapter runs](packaged-tests.txt), [all ten traces byte-identical to this editor run](packaged-parity.json); [NullRHI boot loads both context actors and both new meshes](packaged-smoke.txt) |
| Source delivery | [Full audit:1,874 raw binaries,1,240 ledger rows,0missing/hash/credential issues](source-audit-final.json); [all prior ledger Git bytes preserved](ledger-preservation.json) |
| Review | [Original two P2 findings](review-findings.json), [fixes and final reviewed source hashes](review-resolution.json) |

![Final room](Rendered/AfterFinal/door-room.png)

The actual keyboard exit passed before a read-only runtime reader hit unavailable Python navigation aliases. It was corrected to native reflected names, and the same owned game resumed outdoors without restart or teleport. The keyboard return then passed. Only subsequent photographic fixtures use explicit `dink.Goto`; view changes use normal yaw/pitch controls. The original exit receipt is preserved. The earlier baseline likewise retained its routes across a missing camera-output-directory correction. These are reader/controller errors, not reproduced gameplay faults.

Three phases are retained in `Rendered/Before`, `Rendered/AfterOakOnly` and `Rendered/AfterFinal`. The middle phase is photographic only and makes no real-route claim. All numerical pawn/camera/FOV/arm/offset/framing values match for both paired indoor views; NPC positions and animation phases can vary normally. The blue-pixel count uses the same floor-only ROI and thresholds recorded in the comparison JSON, supplemented by a camera ray that missed the original floor and hit the exported underfloor.

The source workflow and reproducible Blender/native commands are in [the floor guide](../../../Scripts/FLOOR_SURFACE_PIPELINE.md). Both source handoffs are immutable snapshots of authoring; imported/runtime acceptance is recorded here. The underfloor source guide has one explicit collision-missing exception because collision must remain absent, with zero other source errors/warnings.

`RecordedTools` archives the exact machine-local QA drivers. The canonical reusable movement routes remain under `Scripts/Playtest`. Tests and editor-game GPU rendering prove the listed scope; packaged GPU rendering and wider-world/clothing/furniture art are not claimed. New source/art remains candidate status. All earlier art/audio ledger bytes are preserved.
