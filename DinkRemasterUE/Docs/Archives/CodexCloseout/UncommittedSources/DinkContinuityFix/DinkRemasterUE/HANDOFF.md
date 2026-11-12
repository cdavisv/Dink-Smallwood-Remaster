# Camera, doorway continuity and early Dink follow-up

Active worktree `<HOME>/Work/DinkContinuityFix`, branch `fix/camera-world-continuity`, base `2adc5ea`. Created for the owner's reports after testing visible originalQA game153304. That game and the originalQA modules/assets remain untouched.

Requested: solid walls/house when approaching; consistent detailed landscape across the door; timid/sad/aloof/goofy early Dink, poor posture/head down, gangly rather than muscular, distinct garments.

Findings: DinkInteriorCameraComponent replaces each whole tagged static-mesh component's materials with opacity variants, ignores Camera collision, then fades it to zero. The exterior cottage is one component, so approaching it can fade the whole house. Interior VistaV4 is a render-only owner-screen1 composition at detached interior coordinates; the real yard is439 at another location. Hiding its context outside is intentional under the old design and explains the scenery mismatch. Merely retaining visibility cannot join those separate coordinate spaces.

Ownership: this checkout owns runtime camera/continuity investigation. Existing root art session owns Hero source body/garments/native promotion; new direction relayed. Hero candidate source/handoff `<HOME>/Work/DinkQA/PhotorealSessions/Hero/HANDOFF.md`. Root active art integration checkout is separate and must not be edited here. No GPU lease assumed. Generated maps/template content/ImportData symlink to integration's existing fixtures; all authored Content/Data and source code are local, not symlinked. Do not alter fixture symlink targets.

Validation and final implementation pending. Read project AGENTS.md for required build/full suite and preserved original gameplay/collision rules.

## Camera implementation checkpoint

Normal play now leaves tagged wall/cottage materials and camera collision responses untouched. `bEnableWallCutaway` is transient and defaults false; explicit historical ownership/restore regressions opt in to preserve that test coverage, while a new actual-map `Dink.Art.Camera.WallsRemainSolid` checks default opaque walls/cottage at four yaws each. That check passes1/1 with0warnings; build passes with0warnings. Full Art/full suite and actual rendered close-wall acceptance still pending.

Root session accepted canonical439 exterior/source authoring and deriving interior1 vista composition from actual door frames (not simply retaining the detached backdrop). Existing per-owner render-only context factory can instantiate the two authored coordinate frames without runtime relocation heuristics. Collision-bearing near-yard terrain must come from real authored ground; horizon-only dressing may stay render-only. No new context Data has been published here.

Root owns hero slimmer-body/real-garment source plus actual head/neck/spine posture source plan. Their existing89rig/35pose authorities remain protected; no muscularity/garment fix claimed from runtime mesh tilt alone. User direction: early Dink timid/sad/aloof/goofy, gangly, head somewhat down, slouched; preserve responsive movement and original gameplay.

## Posture runtime contract

New `UDinkEarlyPostureAnimInstance` is the optional native parent of a post-process animation blueprint. `PostureWeight` is read by an InputPose→ApplyAdditive(local clip)→Output graph. Early story<=2 target1, story<7 .7, later .3; attack multiplies.35 and airborne.5. Freeze/death/observedwarp zero transient weight, ordinary changes smooth5/s. Optional `characters.json` player.posture_class loads a compatible subclass without replacing the locomotion or action instance. Existing1.2degree mesh baseline hunch is compensated when this postprocess is installed. These source changes are NOT yet built or published; no native posture clip/class is present, so no actual bone-pose change is claimed yet. Root source/native session has the exact graph/clip contract and owns actual slimmer-body/garment/clip publication.

## Intermediate test failure

`opaque_walls_art` was interrupted by a test-fixture SIGSEGV after the historical outdoor camera fixture deliberately destroyed its component. A newly added unconditional cutaway-opt-in assignment dereferenced that null pointer in cleanup. Core161371 and symbolized log point to FOutdoorCameraPIE line54. The assignment now runs only insidePhase0 after TestNotNull. Not a gameplay crash; owner game untouched. Receipt Saved/Continuity/crash-diagnosis.json. Pending rebuild after own private renderer closes. First read-only visual observer attempted protected transient property Python access; camera images remain valid but those readbacks are errors, not passes. Use native console getall readback instead.

## Latest frozen validation run

Runtime build passes0warnings. Art v2 passed27/28; sole remaining failure was the old perimeter-skirt assertion hardcoded to85 managed fade surfaces, nowcorrect0. The assertion now follows the explicit policy; original skirt-no-occluder/no-collision/owner-only checks remain. Earlier historical-outdoor comparison test null-access crash is fixed. Preserve both failed receipts rather than citing them as complete.

Full final suite label `opaque_posture_full_v3` is running. Frozen patch/input pins in Saved/Continuity/Delivery now contain11files (including updated perimeter regression) and8939inputs. The older SHA6eed packet is superseded. Visual close-wall screenshot review passed interior/exterior, actualW exit andreturn bothPASS; final native-readback.json confirms cutawayFalse,fading0,managed0,CameraProbeTrue. First per-fixture Python reads failed on protected debug property and are explicitly excluded from evidence. Private game161822 and Xvfb161815 quit normally, GPUlease released. No new hero or canonical-yard assets have been published here.

## Final v4 runtime snapshot

Review found optional posture override lifecycle issue: an omitted/invalid posture_class on compatible mesh reapply could retain the prior override. New UDinkPostureComponent now captures the exact raw prior override (reflection read only, native setter for changes), restores only still-owned state on disable, preserves external replacements, and restores old mesh independently on retarget. Native override-ownership tests pass2/2 with0warnings. New actual-pawn NativeUpdate lifecycle assertions within WallsRemainSolid pass1/1 with0warnings: early weightbuild, zero-delta pause, actual PCfreeze,500cm observedwarp reset, unpossess reset. This does not claim additive bone evaluation without the future authored graph.

Final frozen packet v4 contains13files and8941inputs, now running `opaque_posture_full_v4`. All earlier10/11file packet hashes are superseded. Root owns actual animation graph builder/import and body/clothes/shared-landscape assets. Defaultopaque-policy rendered evidence predates the optional-posture ownership code but camera runtime itself is unchanged. No compiled library has been replaced while a game from this checkout was alive; originalQA owner game153304 remains frozen. Root currently holds GPU189 for its separate barrel probe.

## Final v5 ownership correction and exact corner

Reviewer found an observed external-override roundtrip edge: after Configure observes foreign replacement, external code may select the old managed class again; Release must still respect the latched ownership loss. Added !bExternallyReplaced restore guard and explicit observed-roundtrip regression. Focused posture2/2 passes0warnings. v4full run stopped intentionally before rebuilding; do not cite as completed. Final v5 full suite is now running under label `opaque_posture_full_v5`, frozen13file packet and8941pins regenerated before it.

Exact reported corner(1,map178/120,yaw180,pitch-25) captured and visually reviewed in Saved/Continuity/north-corner-opaque-v5.png. Wall/window frame fully solid, no former visible blue-floor strip. Native readbacks in corner-v5-readback.json; initial fixture uses console travel, no pixel-exact old/new match claimed because Mother wanders. Own private176733/176727 closed normally andGPUlease released. First opaque rendered views and actualW exit/return remain valid for unchanged camera policy.

## v5 verified handoff

Full `opaque_posture_full_v5` PASSED150/150 in452s,0failures;1successful test carries unrelated engine HTTP connectivity timeout warning. Build0compilerwarnings. All8941 frozen Source/Content/Data/authoring/fixture/module inputs remain byte-identical through full run. Final13file patch SHA c4b66fe82d74c94e8cd1d2aa730194c5bfb33babfac0c6a344a6b095e1d54859 and receipts in Saved/Continuity/Delivery. Actualclose-wallviews, exactnorthcorner andWexit/return passed; owner visiblegameunchanged. This establishes camera/defaultpolicy and optionalposture policy/ownership, not actual pendingmodel/clip/garment/sharedyardasset acceptance.

Next independent follow-up: strict optional context screen_set for shared canonical exterior scenery. Requires unique bounded integer screens list containing owner, cached+physical membership independently inside set (not equality acrossadjacent screens), missingpawn/outside disabled; oldowneronly policy unchanged. Root source/native session owns export/newbackgrounddeltasonly (mustnotduplicate560protectedworldinstances), inside derivedcopy replacesoldV4. Implement after finalv5inputcheck, keep13filepacketimmutable.

## Shared exterior context follow-up

Implemented strict optional context `visibility: screen_set`, `render_only:true`, `screens:[...]` with1..32 unique integer IDs1..768 including owner. Old owner_screen_only policy rejects an unexpected screens field and otherwise remains unchanged. Each cached and physical screen must be independently in the set, so a439→471 transition keeps the same actor/coordinates through cache lag. Missingpawn/outside/interior1 hide; ConfigureOwnerScreen resets group membership. All dressing remains render-only with no gameplay collision. Factory validates before spawn.

New actual-world Context regression covers schema rejection cases, cached439/physical471 bothdirections, real movement duringcachelag, stable actor transform, missingpawn and separateinteriorhide. Focused Context2/2PASS0warnings24s. Separate3file patch/receipt in Saved/Continuity/ContextGroup;13file v5camera/posture packet stays immutable. Combined final full suite `continuity_combined_full` running with8942pre-runinputpins. Runtime support only: canonicalshared landscape assets and head-down/body/garment nativepublication remain root-owned pending actualacceptance. Do not claim entire ownerrequest complete from these runtime tests.

## Context review correction in progress

Independent review found owner-only historical identity check must compare physical and cached volume pointers, not merely equal screen IDs. Restored Physical==Screen only for empty VisibleScreens, preserving group membership behavior. Added actual duplicate439volume fixture at distant nonoverlapping coordinates; old cache must hide, matching refreshed pointer must show. Combined v1 full run intentionally stopped at253s (exit143, no completed report), not acceptance. Rebuild/context focus/full v2 pending. Existing3file packet e05d6 is superseded, will refreeze after build.13file camera/posture v5 remains unchanged.

Verified same-frame native BoneDrivenController garment-corrective contract saved Saved/Continuity/elbow-corrective-runtime-contract.md. Sending notes to existing root art task was rejected by automatic approval review as private project data transfer. User approval requested asynchronously; do not bypass. Local task work unaffected.

Reviewed context parity correction is now built0warnings and focused Context2/2PASS0warnings23s. New frozen3file patch SHA4bdffbc56eabe9cee9ef036a622ffd30f82234b0850cf1d4a119b2d5cdb62467,8942pins. Added real duplicate439volume test verifies cached original439/physical duplicate439 hides owner-only context, then cache refresh to same pointer shows it. Full `continuity_combined_full_v2` running; previous combined run intentionally stopped, no pass claimed. Root reports13filev5 applied to separate stopped integrationbranch fix/house-camera-and-contexts base7930e7; do not alter it here. Message transfer back to root still pending userapproval.

Owner explicitly approved sharing notes with existing art task via asynchronous reply. Native BoneDrivenController same-frame contract and current corrected context snapshot successfully delivered; prior transfer block resolved.

## Corrected context final verification

Full `continuity_combined_full_v2` PASSED151/151,0failed,0warnings444s. Build0warnings; focusedContext2/2PASS0warnings23s. All8942 frozeninputs unchanged afterfullrun. Final3filepatch SHA4bdffbc56eabe9cee9ef036a622ffd30f82234b0850cf1d4a119b2d5cdb62467 and final-verification.json in Saved/Continuity/ContextGroup.13filev5patch remains unchanged. Actual duplicate-ID volume edge preserved; shared439/471cachelag remains visible. Ready root native integration/review. No body/garment/postureclip or canonical scenery assets published by this checkout; root owns pending authoring/native acceptance.

## Canonical outdoors integration decision

Architecture review: actual permanent exterior terrain/horizon NEW deltas should use ordinary world-visible manifest elements, like existing439/438/471 geometry. No runtime constraint requires screen_set for canonical outdoor assets; a finite group can recreate horizon pop when leaving its boundary, and group-hidden geometry must not replace permanently hidden generic surfaces. The tested screen_set API is optional presentation infrastructure only; final native integration may omit it from production usage. Interior1 derived canonical copy remains owner-only context and replaces oldV4. Outdoors must not duplicate560protectedordinaryinstances. hide_screen_visuals/hide_origins require full visual coverage audit; authored_collision_screens and gameplay collision remain unchanged.13filecamera/posturepacket and3fileoptionalcontextpacket remain immutable; no new build needed for documentation-only decision.

## Posture builder planning checkpoint

Root requested plan-first QA-only postprocess/import builder while actualheroassets remain unfrozen. LocalUE5.8.4 graphfactory/nodes/referenceflags reviewed; detailed plan saved Saved/Continuity/postprocess-builder-plan.md and delivered for rootreview. Proposed developer-only native graphbuilder plus Pythonimport receipts, privateQAnamespace, explicitseparaterefclip/localadditive and deterministic evaluatedpose tests. No C++/asset implementation yet; await requested plan review. No GPU/editor/processownedhere. Existing runtimepackets unchanged.

## QA posture graph prototype implemented; final suite running

Root explicitly approved QA-only editor C++ prototype after planreview. New DinkPostureQALibrary in editor-only DinkParity module; editor AnimGraph/AnimGraphRuntime/BlueprintGraph/KismetCompiler dependencies gated Target.bBuildEditor. Newnamespace /Game/DinkQA/Posture only, refuses existingdestination and nonQA target/ref; explicitReferenceMesh89 + same sharedSkeleton161 identity (not an89boneSkeleton assumption). Configures private targetlocaladditive, separateexplicitrefclipframe0, rootmotionfalse; graph InPose +fixedfinaltimeSequenceEvaluator -> ApplyAdditive(PostureWeight) -> Root. Native VerifyPostureGraph checks coldloaded wiring/parent/skeleton/reference/time. No productionasset/characters.json/rootcheckout changes, no GPU used.

Prototypebuild0warnings; Pythoncreates/savesprivatecopies PASS; coldreloadv2PASS. Earlier coldPythonparent_class read failed due unavailable property, replaced with native inspector; preserved failedlog. Evaluatedfocusv3 passed1/1 with2duplicateFbxImportData compressionwarnings (qualified). Actualzero poseerror0cm, half/fullsyntheticdeltas .874/1.748cm; zeroorientation andchangingincomingtime checks pass. Installation legitimatelyreinitializes baseinstance once; firstfixture incorrectlycompared preinstallbase andfailed; correctedtest establishes baseafterinstallation thenverifiesretention duringevaluation. No realHeroheadmask/35poses×4LOD/sourceacceptance claim.

Frozen4filepatch/inputpins in Saved/Continuity/PostureQA; full `posture_qa_full_v1` RUNNING. Old13filecamera and3filecontextpackets immutable; their savedbinarypins are historical validatedsnapshots, currenteditorDLL has now changed fornewQAcode. AllnewtemporaryQAassetcopies are local untracked /Content/DinkQA and MUST NOT be published as actualHeroassets. Production89mesh and161sharedskeleton unchanged.

## QA graph prototype final verification

Full `posture_qa_full_v1` PASSED152/152,0failed,1successful testwith2warnings446s. Warnings both AnimationCompression EnsureDependenciesAreLoaded for duplicatefixture FbxAnimSequenceImportData, not compilerwarnings; receipts preserveexactevents. All8948 frozeninputs unchanged. Build0compilerwarnings. ColdreloadPASS via nativeactualgraphinspector. Frozen4fileQApatchSHA8a4c9b0e76a9879a429098cc5786123fcb5076d28fc34584fc1bec1426d6d67e, final-verification.json/inputs in Saved/Continuity/PostureQA. No ownedGPU/editor/jobsremain. Readyrootreview; noactualHeroasset/mask35poses4LOD/garmentacceptanceclaimed. Temporary /Content/DinkQA files are syntheticlocalQAonly, no publication.

## QA graph V2 review correction and full test running

Root required removal of2newfixturewarnings and strongercoldproof beforeintegration; V1packet8a4c remains immutable. V2freshsyntheticclips now NewObject+InitializeModel, copy rawbone-motion via GetBoneTrackNames/Transforms and Controller SetFrameRate/frames/AddBoneCurve/SetBoneTrackKeys/NotifyPopulated, no sourceimportmetadata. ActualUE5.8 PopulateWithExistingModel onlyaccepts legacyUAnimDataModel: firstattempt omittedInitializeModel andcrashedprivate260720 (SIGSEGV UMovieScene::FindTrack, confirmedcore/stack,22GiBavailable/noOOM; receipt Saved/Continuity/PostureQA/v2-fixture-crash.json); initializedattempt cleanlyrejectedactualAnimationSequencerDataModel. Bothfailedlogs retained. Newpertrackcopy focused1/1PASS0warnings15s; zeroerror0cm, half/full .851/1.703cm, actualrotations/inputforwarding tests pass.

VerifyGraph additionally requires exactInPose, nonlooping evaluator, unlinkedExplicitTime and bidirectionallyexact1:1 pose/Alpha connections. Coldreloadv3PASS. V2fourfilepacket frozen Saved/Continuity/PostureQA_V2; full `posture_qa_full_v2` RUNNING. No runtimepolicychanges or warning suppression. RootGPUbaseline262089/Xvfb262083 is separate/protected. FeedSackpuretools approvedafterboundedQAfix, implementation scope /Work/DinkQA/FeedSackImportDevelopment only; noRoot/UE/C++/nativepublication.

## QA graph V2 final clean verification

Full `posture_qa_full_v2` PASSED152/152,0failed,0warnings488s. Focused1/1PASS0warnings15s; build0compilerwarnings; strongercoldreloadPASS. All8948 frozeninputs unchanged. V2fourfilepatchSHAb0ab247b2f0ef290e3b1e611071d8860ac8a2483afbdb0c68795f50c8b30686c and final-verification.json in Saved/Continuity/PostureQA_V2. V1packet8a4c retainedhistoricalwithwarnings. No ownedGPU/editor/jobsremain. ActualHeroassetacceptance remainsfuture; nativepolicyunchanged. FeedSackscratch112puretests/actual19644sourcecheckpass, nativepolygonGroup→sectionmaterialmappingawaitsrootreview; see /Work/DinkQA/FeedSackImportDevelopment/DEVELOPMENT_STATUS.md.

## Door immediate re-exit audit plan only

Root live game282208 found immediatepostreturnW exitblocked until walkingaway/reentering (v3PASS). Read-only audit confirms BeginOverlap-only + cooldown loses arrival edge; original dink.cpp13486/16893 movement hardness checks are attempt-based. QAplan/evidence Saved/Continuity/DoorWarpAudit proposes bounded existingplayerpoll retry with fresh toward intent, actual overlap/physicalsource, cooldown/suppression/noidle guards; noData/collision/spawn changes. No C++ implementation, GPU or liveinput; rootplanreview pending. Allpreviouspackets frozen.
