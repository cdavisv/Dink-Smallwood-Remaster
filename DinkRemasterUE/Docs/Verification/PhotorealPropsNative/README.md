# Photoreal furniture: native assets and staged gameplay

The Blender table, two bed instances and two chairs are now published in the integration checkout. Publication changed exactly eight mesh references: three asset rows and five runtime instances. Placement transforms, original scripts/IDs and the complex-as-simple collision policy remain unchanged. The 47 authored UCX hulls are retained and verified; they are not the active query collision source.

This is a tested furniture iteration. Final combined lighting, clothing and photoreal visual acceptance remain pending. The selected rendered session used the old exposure ownership and old hero, before the merged house and movement fixes were rebuilt together.

## Current evidence

| Check | Result and scope |
| --- | --- |
| Guarded runtime publication | Eight mesh references only; [author publication receipt](Publication/author_publication.json) |
| Actual door traversal | Real held-W exit and return pass, without route teleports: [exit](Render/actual-exit.json), [return](Render/actual-return.json) |
| Furniture/pickup interaction fixtures | 12/12 pass; teleported setup positions followed by real F/E/W actions, with raw responses in [results](Render/Interactions/results.json) |
| Render freeze | 9,040 recorded files unchanged; [verification](Render/verification.json), [before](Render/before.json), [after](Render/after.json) |
| Runtime identity | Original S001_P22/P23/P24, scripts and new mesh/material paths present; two decorative chairs: [summary](Render/Runtime/furniture_identity_summary.json), [raw readback](Render/Runtime/props-return.json) |
| Earlier postpublication native Art suite | 24/24 pass; **three tests with 46 environmental warning events**, not zero warnings: [raw report](Publication/art24_raw_report.json), [verification](Publication/art24_verification.json) |
| Fresh published-state saved-asset verification | Pass, 85.64s; all 15 packages, geometry/UV/winding, hulls, saved graphs and nine Texture.Source payloads checked: [receipt](CurrentPublishedVerify/receipt.json), [terminal](CurrentPublishedVerify/terminal.json) |
| Native source-filename ownership | All 12 native FBX/PNG getter roles resolve to this checkout's selected source bundle and match its hashes |
| Combined-context fresh published verification | Pass, 83.12s, all five protected scopes unchanged; 15 package hashes and all 12 native source roles checked after merged fixes/rebuild: [receipt](CombinedPublishedVerify/receipt.json), [terminal](CombinedPublishedVerify/terminal.json) |
| Published workflow regressions | 68/68 focused and [184/184 full Python tests](RootChecks/python184.log); [log](CurrentPublishedVerify/pure68.log), [independent review](CurrentPublishedVerify/independent_clone_workflow_review.json) |
| Combined full native suite | **147/147 pass, zero warning/error events**, 432.30s; merged movement and house fixes plus furniture/convex bridge: [verification](CombinedFull147/verification.json), [raw report](CombinedFull147/raw_report.json), [independent report check](CombinedFull147/independent_report_check.json) |
| Combined freeze / isolated saves | **8,884 inputs unchanged**, zero prior save slots inventoried (therefore no old-slot preservation claim) and ten new probe slots in the isolated UserDir: [before](CombinedFull147/before.json), [after](CombinedFull147/after.json) |

The earlier Art warnings are Epic/Google HTTP DNS/timeouts and a global editor FilterBar configuration write rejected with read-only filesystem errno30. No native test failed. This report is separate from the later combined suite.

The final published publisher [`--apply` check](CombinedPublishedVerify/publisher_noop.json) reports already-published state, zero changed references and `writer_scope: none`; it does not republish the scene.

Both published-state verifications use current entry package hashes and preserves them through exit, with unchanged source/tool/config, source art, runtime Data, Content and module scopes. It requires no private author import/publication receipt. Its `scene_data_approval: false` and `writer_scope: none` mean that current Data is protected context, not a new approval of earlier scene/story edits. The owning integration checkout was tested; **a freshly relocated clone has not yet been tested**.

The runtime identity readback establishes original script/origin continuity. It does not establish a new save/load roundtrip. Camera render bounds are not independent physical collision measurements.

## Selected native views

These are explicitly positioned photographic fixtures using the normal player camera, separate from the uninterrupted door routes. [Close-view](Render/CloseViews/receipt.json) and [side-view](Render/SideViews/receipt.json) receipts retain player positions and camera angles.

| Table at gameplay distance | Bed cover |
| --- | --- |
| ![Native table](Render/CloseViews/table-game-distance.png) | ![Native bed cover](Render/CloseViews/bed-cover.png) |

| Bed three-quarter view | Chair side view |
| --- | --- |
| ![Native bed three-quarter](Render/SideViews/bed-three-quarter.png) | ![Native chair side](Render/SideViews/chair-side.png) |

[Actual outside](Render/actual-outside.png) and [actual return](Render/actual-return.png) retain the door-loop render evidence. Lighting differences in this older session must not be presented as acceptance of the later combined exposure fix. Cloth macro filtering and the final combined material grade remain visual review items.

## Historical import checkpoint

The original [checkpoint](checkpoint.json), [import](import.json), [verify](verify.json) and [evidence hashes](evidence_hashes.json) remain byte-for-byte preserved. They document the successful initial import and separate-process verification **before runtime publication**. Their unpublished status, older four-tool hashes, 47-test count and then-remaining work describe that historical state. Use [current summary](current_summary.json) for the later publication/render/current-verification state.

The historical evidence retains the float32 quantization diagnosis, tolerant source-anchored rematching and read-only convex bridge test. Actual matching limits remain 0.01cm position / 0.0001 UV; winding and bijective face/hull coverage are checked. Native geometric fronts and saved normal-import flags are verified separately; the installed Python wrapper does not expose native per-corner shading-normal arrays. Failed import attempts remain preserved in the author's Saved history and are not relabeled as successful imports.

The combined full native suite is now recorded separately above; its 147 states, zero warnings/errors and identical 8,884-entry before/after maps were independently checked. This is NullRHI automation on the merged controls/house fixes plus furniture. Final combined actual-RHI rendering and final hero approval remain pending. See [current summary](current_summary.json) for the remaining checks and exact tool hashes.
