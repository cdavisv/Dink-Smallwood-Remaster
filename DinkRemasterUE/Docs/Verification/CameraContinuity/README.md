# Opaque architecture and camera continuity

The camera previously replaced foreground walls and whole cottage surfaces with fading materials. Normal play now keeps architecture opaque and lets the existing spring-arm probe retract against its authored collision. Historical cutaway behavior remains an explicit comparison option; its material/collision ownership and restoration tests are retained. Original wall materials, physical collision, placement and gameplay rules remain unchanged.

The integration also supplies optional native posture policy/override ownership and a strict shared-context visibility API. These are runtime contracts; **no new hero model, garment, additive clip/graph, canonical landscape or exterior composition assets are delivered here**. Root-private combined render acceptance is pending.

## Independently checked integration

| Check | Result and scope |
| --- | --- |
| Exact source integration | All16files match frozen camera/posturev5 and contextv2 hashes: [source map](RootNative/all16_source_match.json) |
| Root editor build | Succeeded, zero compiler warnings;18actions,24.52s build-log time (25s rounded elapsed): [receipt](EditorBuild/verification.json), [log](EditorBuild/build.log) |
| Root full native suite | **151/151 pass, zero warnings/errors,442.61s** after merged native barrels plus both patches: [raw report](RootNative/Full151/raw_report.json), [verification](RootNative/Full151/verification.json) |
| Root full freeze | All8,963recorded source/tools/art/ledger/Content/ImportData/config/module inputs unchanged: [before](RootNative/Full151/before.json), [after](RootNative/Full151/after.json), [independent check](RootNative/independent_check.json) |
| Scoped saves |20inventoried prior probe slots retain hashes;10new chapter slots stay in the fresh test UserDir. This is not an exhaustive owner-save inventory. |
| Standalone Development game build | Succeeded, zero compiler warnings,65s; all7editor module bytes remain unchanged: [verification](GameBuild/verification.json), [log](GameBuild/build.log) |
| Root private exact-corner/game views | **Pass**: exact corner and room views, real W door exit/return, normal shutdown and6,920unchanged inputs: [status](RootRender/status.json). Author images below are distinct evidence. |

The standalone result is a **build** check: it does not establish cooking, packaging, standalone runtime, a new animation graph, or actual authored bone playback. The full8,963freeze covers the native run; the later game build has its own seven-editor-module check and intentionally generates game output.

[Current summary](current_summary.json) retains precise test counts, warning events, packet hashes and remaining gates. [Independent camera/posture review](Review/camera_posture_review.json) and [context review](Review/context_group_review.json) found no blocking issues in the final frozen packets. No new native/GPU runs were performed by those reviewers.

## Author evidence kept separate

| Author check | Result |
| --- | --- |
| Camera/posturev5 full suite |150/150pass, zero failures, **one successful test with one HTTP timeout warning**,452s;8,941inputs unchanged according to the [author final receipt](Author/CameraPostureV5/final-verification.json) |
| Separate context-combined suite |151/151pass, zero warnings,444s;8,942inputs unchanged: [raw report](Author/ContextGroupV2/combined151_raw_report.json), [final receipt](Author/ContextGroupV2/final-verification.json) |
| Posture ownership/mood focus |2/2pass, zero warnings: [raw report](Author/Focused/posture2_raw_report.json) |
| Actual-pawn policy and solid walls |1/1pass, zero warnings: [raw report](Author/Focused/lifecycle1_raw_report.json) |
| Original/shared context focus |2/2pass, zero warnings: [raw report](Author/Focused/context2_raw_report.json) |

The camera/posturev5 warning is exactly one `LogHttp` timeout fetching Google's `generate_204`, in successful `Dink.Narrative.Smoke.AllEntryPoints`. It is retained in the [raw150report](Author/CameraPostureV5/full150_raw_report.json), not relabeled as zero-warning. The later author combined151 and root151 results are separate zero-warning runs.

The [13filev5 patch](Author/CameraPostureV5/camera-posture.patch) and [3filecontextv2 patch](Author/ContextGroupV2/context-screen-set.patch) retain their own delivery metadata and input maps. The later context build changes two actor source files, one new test and two linked modules; the earlier8,941map is not presented as a current post-context module inventory.

## Author visual and door evidence

These photographic viewpoints use explicit console fixture setup. Their [held-W exit](Author/Render/exit.json) and [return](Author/Render/return.json) use actual player input and contain no route teleports. Their scene Content still has the **older barrel** and older hero. They do not prove current root-combined barrel appearance or final art quality.

| Solid house wall | Exterior cottage |
| --- | --- |
| ![Author interior east](Author/Render/interior-east.png) | ![Author cottage east](Author/Render/cottage-east.png) |

| Exact previously fading north corner | Actual returned doorway |
| --- | --- |
| ![Opaque north corner fixture](Author/Render/north-corner-opaque-v5.png) | ![Author actual return](Author/Render/returned.png) |

The exact corner is screen1,map178/120,yaw180,pitch−25. Its [native readback](Author/Render/corner-v5-readback.json) reports cutaway false, fading0 and physical probe true; the broader [native policy readback](Author/Render/native-readback.json) also reports managed0. Early Python attempts to read a protected transient field failed and remain visible in [the visual receipt](Author/Render/visual-receipt.json); those errors are not passing checks. Subsequent native `getall` reads provide the successful policy evidence.

## Runtime policy and limits

Optional posture installation requires a subclass of the native posture parent and an exact compatible target skeleton. Its owner component records the raw previous override, including null, writes through Unreal's native setter and restores only its own override. A latched foreign replacement remains unowned even if another system later selects the old managed class; the observed-ABA regression checks this. The actual-pawn test covers accumulation, zero-delta pause, input freeze, a500cmobserved warp and unpossession. Story/attack/airborne weight selection is separately tested. No authored additive graph is loaded, so these tests do not establish final bone deformation, cloth fit, the rendered timid stance or new character dimensions. Warp detection remains an observed displacement heuristic.

The optional `screen_set` API accepts1–32unique numeric integer IDs in1–768, includes its owner, and rejects gameplay/collision/warp/hide/light/postprocess ownership fields. Cached and physical screen IDs must each be members; they may differ during a covered crossing. Missing pawn/cache/physical volume hides the context. The old owner-only branch preserves actual cached/physical volume identity, including duplicate-number volume transitions, and clearing the group restores that old policy. Render-only NoCollision/no-overlap/no-nav/no-hidden-shadow/GI behavior and teardown callbacks/timer remain intact.

Screen membership is not a geometry deduplication or coordinate-validation system. It is also not an automatic outdoor-type filter: an interior is excluded when it is absent from the declared group. No authored shared-world assets are included by this API patch.

Canonical exterior artwork will use ordinary persistent world geometry, emitting **new deltas only**. Screen1interior will use its own owner-only derived copy. The optional screen-set API is tested independently; no canonical exterior asset completion is claimed by it.

## Preserved corrections and remaining work

[Historical receipts](Historical/superseded_runs.json) retain source paths/hashes and small summaries rather than giant cancelled logs. Thev1NullRHIArt fixture crashed by dereferencing its destroyed camera during cleanup; moving the historical opt-in assignment into its validated phase fixed that fixture. Thev2Art run passed27/28and failed its old85managed-occluder expectation under the new default0policy; the final perimeter test retains its render-only/nonoccluder assertions with policy-aware counts. Supersededv3/v4runs were stopped before final verification and are not successes. Earlier ownership/parity reviews are retained and their corrections are present in the accepted packets.

Root combined exact-corner/current-barrel/room screenshots and real W door exit/return now pass, with normal shutdown and6,920unchanged inputs. The route begins at the explicitly documented room photo fixture; it contains no route teleports. Initial protected Python property access failed; native getall provides successful policy readback. New hero body/clothing/additive animation and canonical landscape assets need their separate source/native/render acceptance. Lighting and remaining starting-house art are unfinished. Commit/LFS/PR delivery of this bounded iteration follows the root render gate; no whole-game photoreal or driver-stability completion is claimed.

## Root combined render

![Exact fixed corner](RootRender/opaque-north-corner-root.png)

![Returned through actual doorway](RootRender/returned.png)

[Exit](RootRender/exit.json) and [return](RootRender/return.json) record real held-W input. Both native readbacks retain cutaway false, managed/fading zero and spring-arm collision true. New hero, complete landscape and final lighting remain separate outstanding work.
