# Dink remaster continuity

Updated 8 November 2026. The full goal remains active: realistic Blender art for the playable starting house, fitted collision, traversable exits and verified visuals. Lighting, the new hero and shared exterior are unfinished.

## Worktree and ownership

Primary integration: `/home/davisc/Work/DinkPhotorealArtIntegration`, branch `art/photoreal-barrel-native`. Base is merged PR13 (`2adc5ea3f89f2a368fc3f945c25270ca937b7acd`). Local evidence commits `fc04285` and `234a57f` precede the pending native barrel changes. Check actual Git status before relying on this record.

No root private renderer is running: game171912 quit normally, display171906 stopped. The movement session also released its later exact-corner probe. Revalidate before using private display `:189`; launch receipts are in `/home/davisc/Work/DinkQA/Tools/game.json`.

Protected user games: older SurfaceDelivery remains frozen. Movement owner game153304 uses `/home/davisc/Work/DinkPhotorealVisualQA`; do not send input/signals or rebuild/edit its loaded assets/modules. Engine installation is read-only. Other sessions use isolated worktrees; preserve their files.

## Merged deliveries

- PR8: source-only photoreal table, bed and chair.
- PR10: clumsy movement/lower hop, merge `3b5653c4f396983b14efd82a5439ff915ea89745`.
- PR11: indoor exposure ownership and fitted perimeter floor rim, merge `f31d243477ee75070113f7f38029113bd606f993`.
- PR12: native photoreal furniture, merge `64d57e8f3a1ce36a2d687ac44be311e5cc4e4a1b`. Combined native147/147 and184Python passed. Exactly8mesh strings changed; transforms/scripts and complex-as-simple collision preserved. RealW exit/return and12interaction fixtures passed. All21new LFS objects cold-fetched and verified.
- PR13: barrel source, merge `2adc5ea3f89f2a368fc3f945c25270ca937b7acd`. Source commit `0bccface...`;24LFS files cold-fetched/verified. Source worktree `/home/davisc/Work/DinkPhotorealBarrelSources` is separate.

## Pending native barrel iteration

Source: `SourceAssets/Art/Stonebrook/Refinements/PhotorealBarrelV1`. Source SHA `0fcb284a168aaa0d4508d3cfbc1be682b79c54c7b85ef1c499bde1778f2371c6`; repository handoff SHA `fa0805fa7fa5064cccc924e4b28c32408d69e6797d7e8dc3d5cb88d126badc57`. The copied checker portability correction is documented; consumed art bytes are unchanged.

Reviewed tools originated in `/home/davisc/Work/DinkQA/BarrelImportDevelopment`;83pure guards pass. Independent review: `/home/davisc/Work/DinkQA/PhotorealSessions/barrel_import_review.json`. The reviewed importer is self-contained and adds module pins and safe indexed geometry guards.

Actual reviewed runs under `Saved/BarrelReviewed`:

- Attempt01 preflight:20.196s, pass, no protected changes.
- Attempt02 import:54.742s, pass, only5new packages.
- Attempt03 independent saved verify:42.565s, pass, all scopes unchanged.
- Publication: exactly3mesh strings, one asset row and two decorative barrels; semantic reversal matches the prior document exactly.
- Full147:147/147, zero warnings,545.190s; all8,956inputs unchanged. Ten prior probe saves unchanged and ten new isolated slots. Precise save scope is not an exhaustive owner-save claim.
- Python:267/267 pass. Sequential source audit passes1,990binaries/262Python/22shell/1,414ledger rows. The first audit overlapped synthetic temporary test fixtures and failed on those fake tools; both reports are retained.
- Render: game171912/display171906 closed normally. Explicit photo/setup fixtures followed by realW sweeps stop at map164.017/120 and depart to254.506/120. All6,914pins unchanged. This is bounded collision coverage, not every direction.
- Attempt04 fresh published verify passed44.173s, all scopes unchanged; no native process remains. Published package hashes and4native source paths retained.

Geometry:16,648triangles; maximum source position error3.815e-6cm and UV error2.98e-8. One retained UCXbox75×75×100cm,8vertices match exactly. Original native baseline confirmed10,472triangles/two materials. Variable iron metallic B0..240 is intentional; AO R255. Four source filename roles resolve to this selected bundle. Complex-as-simple remains the active query policy; retained UCX is not the active query source.

Five candidate ledger rows append to1,409prior rows; all prior raw bytes and483audio rows remain unchanged. Commit/PR/review/merge of this native iteration is still pending. Evidence: `Docs/Verification/PhotorealBarrelNative`.

### Earlier concurrent import preserved

Other art task `01a1bc9f-a893-7951-ad79-4bffc4914cb8` independently created three untracked tools and five packages in this checkout. It confirmed ownership, ceased writes and explicitly allowed archival/reimport. Its receipts are NOT approval of the reviewed tools. Exact5packages+3tools+1test were SHA-checked and preserved in `Saved/BarrelReviewed/PriorContinuationCandidate` and external `/home/davisc/Work/DinkQA/BarrelNative/ContinuationCandidateArchive_20261108`, then only those exact unpublished files were removed. Fresh reviewed import followed. Historical docs are preserved separately.

## Combined render and relocation evidence

`Docs/Verification/CombinedHouseRender` records actualW exit/return in the combined furniture/controls/exposure build. First driver was interrupted after initial steps; replacement resumed the same game at its actual position, no teleport/restart. Game148811/display146588 closed normally;6,909pins unchanged. Old hero and dark room center remain unfinished.

`Docs/Verification/PhotorealPropsNative/RelocatedClone`: independent ordinary LFS checkout `/home/davisc/Work/DinkQA/RelocatedPropsClone`, detached7a22c2f, built own modules135s/143actions/0warnings. Twelve native source paths resolve to its own bundle;15packages match Git;3,422recorded inputs unchanged. Default/--apply publisher writes nothing across3,815files, with no private author receipts or ImportData. Outer wrapper did not record exitcode/time; native pass receipt/internal guards/normal shutdown prove the bounded check, not an invented outer result.

## Lighting and camera work

An earlier private game146595 crashed after `r.Lumen.Visualize1`: core/log show Radeon Vulkan compute-pipeline creation for `FVisualizeLumenSceneCS`. Preserve `Saved/CombinedLighting/crash_diagnosis.json`; frozen diagnostic console image is INVALID coverage. No engine/driver fix is established. Actual metadata: r.RayTracing0, Lumen hardware preference1, TraceMeshSDFs0, default exposure bias+1, sky intensity1/realtime captured/lower hemisphere black. This does not prove SDF/card coverage or cause of darkness.

Barrel close fixture map178/120,yaw180,pitch-25 reproduces old cutaway wall disappearance/outside-floor blue strip. Movement session tested exact fixture with opaque walls: solid wall/window frame, no exposed blue floor; NPC placement is not pixel-identical. Its worktree `/home/davisc/Work/DinkContinuityFix` owns camera-default-opaque and optional early-posture API. Finalv5packet under `Saved/Continuity/Delivery` supersedes v3/v4,13files/8,941pins. Ownership observedABA P2 fixed; focused2/2 pass. Fullv5 and independent final review remain pending. Do not merge a superseded packet.

Optional posture requires an actual compatible89rig local additive clip and postprocess AnimBP; source APIs/weights alone are not bone-pose acceptance. TargetSkeleton/class checks, ownership restore, freeze/warp behavior and SingleNode+postprocess evaluation need final integration proof.

## Active Blender sessions

Hero: `/home/davisc/Work/DinkQA/PhotorealSessions/Hero/HANDOFF.md`. V122 clean waist checkpoint SHA `d5325a78edba3244043a0807b52c44ee470cf503a1009e3a9a523d4e1a4606fb`,140self+140shirt+140belt cases pass;89rest/non-jerkin fields preserved. It is not final art. Owner direction: timid/sad/aloof/goofy early Dink, slouch/head down, gangly/less muscular and real garments. New fixed-rig slimming/additive pose V124 direction approved, but skin-tight outfit rejected. V128 relaxed sleeves/trousers approved for fitting iteration; waist/boot fit, coherent UVs, real cloth construction/PBR and all mixed pose gates remain outstanding. No new hero export/native approval. Preserve base35poses/89rest and immutable checkpoints; never substitute material weave for actual garment volume.

Shared exterior: `/home/davisc/Work/DinkQA/PhotorealSessions/SharedStonebrookVista/HANDOFF.md`. Canonical actual439yard is shared with an interior render-only view using visual door-front planes, yaw0/scale1, exterior-minus-interior `[281461.1459297,-356225.6558019,0]`cm. Warp/capsule centers have measured offsets and remain unchanged. Protect actual439/438/471ground and add only render-only neighbor skins beyond it. Baseline floating trees/void are diagnosed; V4source study adds coverage and a reference-guided two-tier neighbor house. V3 rejected inward normals/blocked door ray;V4audit reports closed fronts/15of15clear rays. It is not guide/export/native/promotion-ready or final photoreal art. Interior room14.875×13.125m differs from cottage18×9m; state-specific self-cottage visibility must remain explicit.

Independent other art session owns QA-only Basket source/provisional bake, currentV4. It must not edit root/Hero/Barrel/shared-vista concurrently. No basket native approval.

## Next actions

1. Finish Attempt04, no-op publisher check and barrel final docs/review; commit/push/PR/review/merge this bounded iteration.
2. Review final camera/posture packet and raw full suite; integrate only a frozen accepted packet, then test combined actual camera/door behavior.
3. Finish realistic loose clothing/slim body/additive clip, import and test actual bone playback/collision/visuals.
4. Finish canonical shared exterior artwork, geometry/door/collider audits, guide/export/native/screenshots.
5. Calibrate lighting from evidence and continue remaining original house art. The broad goal is incomplete.

Shared-account instructions: `/home/davisc/Work/CodexSharedAccess/README.md`. Do not remove shared runtime storage. Update this record after substantial completion or stopping; always revalidate processes, branch and files before resuming.

Known source-tool issue: frozen barrel bake recipe retains removed Blender NodeLink wrappers while restoring shaders. Current textures are independently verified; do not overwrite them. A corrected successor recipe and real Blender restoration regression are being prepared work-only in DinkQA/BarrelBakeRecipeFix by the separate basket/art session. Preserve original source hashes and distinguish any future recipe revision.

## Independent basket source publication packet — 8 November 2026

Own worktree /home/davisc/Work/DinkBasketSourceDelivery, branch art/photoreal-basket-source, base7930e7b921ec6f52f4c44f31fb59e5b7c4c741a6. Source/export iteration approved by coordinating root after actualFBXfront/handle review; no native acceptance.57newsourcepayloadfiles include all44reviewed payloads, full originalKIT/wicker inputs, labelledoriginalroomcontext and metadata. AddeddecorativeWickerBasket must not be confused with grainpickupS001_P52. One canonical roundtrip recipe blank-line trailing space removed; exact original archivedZIP, AST-equivalence proven, no artbinary differences.

Source945ddda9...;19680tris;2kBC/N/ORM; completeUVaudit0overlap/truncationfalse,821px/m. OriginalauthoredUCX andbounds/pivot preserved; activecomplexquery/camera/game acceptance stillpending. Standalonecopy uses onlyitsowncopiedInputs/Pipeline, UV andpackedsource/exportreopeningPASS. Original1414ledgerrows/483audiorows rawbytespreserved; new57remaincandidate. See Docs/Verification/PhotorealBasketSource for review/copy/ledger/portable/roundtrip/audit receipts. No Content/nativecode/runtime changes. Local commit requested byroot; no push or PR untilrootreview. Fresh source audit/terminalproof below should be consulted before final approval.

Separate QAonly FeedSack source/export is NOT approvedfinal: root requests one bounded coarserjute/slub/panelvariation/seam/basewear/shoulderfacet/tieend pass. Candle source draft remains under /home/davisc/Work/DinkQA/PhotorealSessions/Candle with no sourceguide/render/native approval. Do not promote them from builder success. RootArtIntegration/Hero/Barrel/SharedVista and all user games untouched by this worktree.

Basket source finalchecks: fullsourceaudit PASS2023binaryfiles/279Python/22shell/1471ledger,0missing/hasherrors/secrets; old1414/audio483rawprefixunchanged. Standalone copiedbaseline UV/packedsource+export and canonicalactualFBXroundtrip PASS; optional originalKIT baseline authoring rebuilt matching frozenV4geometry/topology/attributes. Gitwhitespacecheck clean. Allpublishedsourcepayloads unchanged afterchecks. No native suite claimed.
