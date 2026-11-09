# AGENTS.md

Operating instructions for AI agents and humans working on the Dink Smallwood Remaster Unreal
project. Read this file before doing any work here, and keep it accurate: when you learn a build
fact, a pitfall or a decision, write it down here and remove anything that has become wrong.
Label uncertain or temporary information as such.

## Photoreal basket source candidate (8 November 2026)

Source-only `art/photoreal-basket-source`, base7930e7b, adds portable Blender/FBX/GLB and2048BC/N/ORM under SourceAssets/Art/Stonebrook/Refinements/PhotorealBasketV1. The added decorative WickerBasket is distinct from the original grain sack S001_P52/422_12/s1-sack; room-context PNGs are explicitly not its direct sprite. Coordinating root approved source/export iteration only; native/game acceptance remains pending.19680triangles, guide0errors/1soft-targetwarning; separate complete UVoverlap0/truncationfalse, atlas83.2%/821px/m. Original kit bounds/pivot/authoredUCX retained, but rebuilt render triangles differ and complex-as-simple needs native gameplay verification. NoContent/runtime references change. Source recipe fixes use safe shader socketpairs; original archived trailing-space recipe retained separately with AST-equivalent canonical whitespace cleanup.

## Photoreal barrel source candidate (8 Nov 2026 UTC)

Source-only branch `art/photoreal-barrel-source`, base64d57e8f, adds the reviewed packed Blender barrel/triangulated export and2048BC/N/ORM payloads under SourceAssets/Art/Stonebrook/Refinements/PhotorealBarrelV1. No Content/runtime references change; native/game acceptance remains pending. Guide retains0errors2sourcewarnings/1exportwarning; exact original bounds/pivot and75x75x100cmUCX retained.56new ledger rows remain candidate; prior1353rows/483audio rows preserve rawbytes. The copied payload audit removes an author-only duplicate archival-file dependency, retaining approved source SHA; original handoff and correction are recorded in Docs/Verification/PhotorealBarrelSource.

## Native photoreal barrel checkpoint (8 November 2026 UTC)

The PhotorealBarrelV1 source from PR13 now has a reviewed native iteration: preflight/import/independent verification/fresh published verification pass. Full native147/147 passes with zero warnings; all8,956 recorded inputs unchanged. All267Python checks and full source audit pass. Exactly3mesh references change (one asset row plus Barrel1/Barrel2); transforms, scripts and existing complex-as-simple query policy remain unchanged. Five native packages and five candidate ledger rows are added; prior1,409raw ledger rows and483audio rows retain bytes. See Docs/Verification/PhotorealBarrelNative for actual scope and historical tool-version separation.

Actual source matching checks16,648triangles, finite UVs/geometric fronts, one retained8vertex UCXbox75x75x100cm, saved hidden material inputs and three Texture.Source images. Iron uses variable metallic B0..240 with AO R255; do not inherit furniture's dielectric-only constraint. Four resolved source filenames must identify the selected bundle. Module/package/source/Data guards bind import and saved verification; fresh published checks require no private author receipt and write nothing, even --apply.

A private45FPS render shows both barrels and realW contact atmap164.017/120, departure254.506/120;6,914runtime/source/module inputs unchanged, game/display quit normally. This bounded axis probe is not universal collision coverage. Opaque architecture is now the default: root combined151/151 native checks pass with zero warnings, and the exact178/120,yaw180,pitch-25 private render retains wall/frame with no exposed blue floor. Real W exit/return pass;6,920runtime inputs stay unchanged through normal shutdown. Optional posture/context APIs are present, but new hero/additive/landscape assets remain unfinished. See Docs/Verification/CameraContinuity. Hero/lighting/shared exterior remain unfinished.

The immutable source bake recipe has a later-discovered stale Blender NodeLink restoration risk. Approved baked payloads passed independent pixel checks; preserve their hashes. A corrected successor recipe is being developed work-only and must not silently mutate the frozen bundle or relabel earlier receipts. HANDOFF.md records current branches, process ownership and remaining gates for cross-account continuity.

## Native photoreal basket checkpoint (8 November 2026 UTC)

PhotorealBasketV1 preserves the original decorative basket dimensions114.4×94.2×67.2cm, placement and complex-as-simple policy while replacing only its asset row and WickerBasket element. Original S001_P52 grain/feed pickup, scripts and transforms remain unchanged. Five unique packages contain19,680triangles, one retained88×88×60cmUCX and2048BC/N/ORM; the UCX is verified but does not become the active query source. Native actual specular.21853724122047424 matches intended source normal-incidence F0 target.21853724634807323; sourceIOR1.46/IORLevel.25 is not copied directly. Other material-layer types need their own contracts.

Reviewed5tool/6test packet13e0386f passes97basket guards and364aggregatePython tests. Preflight/import/savedverify and fresh published verify pass; the latter needs no private author import receipt. Publisher default/--apply are zero-write in published state across8,887declared files. Full native151/151passes0warnings with9,128inputs unchanged and30inventoried old probe saves retained. Exact source filenames, actual oriented geometry/UV/fronts/retained hull, saved hidden material pins andTexture.Source pixels are checked.

Private game232554/display232548 closed normally;6,925runtime inputs unchanged. Real100msW samples reach the identified basket component atmap427.018/146.023 with0.027128cmremaining capsule sweep; actualWdeparture and door exit/return pass. A long-hold straight-X assertion failed because the curved basket permits sliding; a later approach-only PASS was rejected as contact proof. Both are preserved separately. These are bounded probes, not universal collision/reach or final house art acceptance. See Docs/Verification/PhotorealBasketNative; Hero, canonical exterior and lighting remain unfinished.

## Native photoreal furniture integration (8 Nov 2026 UTC)

Merged controls and house fixes (PR10/PR11, base f31d2434) plus the new table/bed/chair packages passed the complete native suite147/147 with zero warnings in432s. All8,884 source/tools/art/ledger/Content/ImportData/config/custom-module inputs stayed unchanged; the old-save inventory was empty (so its zero-change check is vacuous), and ten new probe slots are isolated. All184Python tests pass. See Docs/Verification/PhotorealPropsNative for precise historical/current scope and raw reports.

Exactly8mesh strings change (3asset rows, originalS001_P22/P23/P24 and2decorativechairs), preserving placement/script identities and complex-as-simple query collision. New meshes total34,884triangles with47retained UCX hulls; those hulls are verified but are not the active query source. Actual held-W door exit/return and12real-input interaction fixtures pass. Initial furniture screenshots used the old exposure/hero; final combined lighting and clothing acceptance remain pending. The read-only editor convex bridge returns actual hull transforms and detached mesh/local vertices without cooking/saving assets.

Fresh published-state furniture verification needs no private author receipt: it pins15entry packages and12native resolved source filenames, checks loaded geometry/UV/fronts/hulls/graphs/Texture.Source, and retains hashes through exit. Published publisher checks, including --apply, write nothing and explicitly give no scene-data approval. Prepublication import still refuses existing destinations and requires the original receipt chain. Never relax filename ownership or substitute another checkout's source. Relocated-clone execution must be recorded separately. The15new native ledger rows remain candidate and all1,338prior rows/483audio rows preserve raw bytes. Hero/center lighting, cloth filtering and wider-world old art remain unfinished.

## House visual fixes verified in an isolated stage (8 Nov 2026 UTC)

On base `e53cae95`, the exposure coordinator and additive PerimeterSkirtV1 passed145/145 native checks with0warnings in450s and116/116 Python tests. All8,852 source/runtime/authoring/module inputs stayed unchanged during the full run; ten new probe slots stayed in a fresh isolated UserDir. These fixes are merged in PR11 and also pass the later combined147 suite; the older visible SurfaceDelivery session remains unchanged. See `Docs/Verification/HouseVisualFixes`.

The real W exit/return and eight returned camera angles pass. Room bias−2 remains active even with the camera beyond the old bounds, and is disabled outdoors. Hero/center darkness and bright distant outdoor terrain remain unfinished lighting/material work; Epic GI quality3, Lumen and eye adaptation are enabled, but surface-cache/SDF coverage is not established. Query actual `r.DefaultFeature.AutoExposure.Bias` before calibration; installed engine default is+1, so absence of the authored−2 override does not imply a default bias0.

The new source-authored rim is48vertices/96triangles, oneLOD, full96-triangle Nanite fallback, Z−18..−.2cm and inside the recorded floor contour. It reuses DarkOak unchanged; no collision/nav/overlaps, owner-screen-only visibility and no hidden shadow/GI. Original56 floors, UnderfloorV1, gameplay and85 managed camera occluders are retained. Exact archived pawn/camera XYZ/rotation/FOV/arm/offsets/framing match; the north floor ROI goes23→0bluepixels and all7 escaped rays hit actual native ring geometry. Four measured pitches pass; this is not universal all-angle coverage. The source guide retains one explicit render-only COLLISION_MISSING exception, zero warnings. All16 new ledger rows remain candidate; all prior1,322 rows/483 audio rows are byte-preserved.

Keep raw before/failure evidence separate. A direct photo teleport to an old returned position retriggered its real exit warp and is INVALID matched-frame evidence. The successful north fixture is safely away from the door. UE CW-front geometry in its left-handed basis uses negative RH cross after Y reflection; the initial RH-front assertion failure was a convention error, preserved. Do not invent a Python stored-normal getter: installed StaticMeshDescription exposes normal attributes only through C++; verified source-face identity/import flags and actual rendered pixels are the evidence. Neighbor440 barrier identity remains qualified because Python HitResult component access is protected; the west fence route failure was a fixture-planning error. No global hiding or collision deletion was applied.

## Third-person controls and body motion (8 Nov 2026 UTC)

The owner requested walk/run, jump, zoom and more physical character movement, then asked for a clumsy Dink with a lower hop and occasional landing stumble. `ADinkGreyboxCharacter` keeps default run600cm/s and hold-LeftShift walk200cm/s. Current Space hop uses280cm/s launch, gravity1.45, hold cap80ms, one jump; acceleration1100, braking950, turn360deg/s and air control0.2. Q casts; LeftShift no longer casts. Dialogue/menu Space confirmation takes priority. Gamepad: left shoulder walk, bottom face jump, D-pad up/down zoom. Native transient Enhanced Input actions/context require no binary input-asset edits; UEnhancedInputComponent explicitly deletes legacy BindKey/BindAxisKey. Held gait polling changes the cap only on a gait transition, preserving external/script/test speed overrides.

`FDinkHeroPhysicality` adds player-only uneven shuffle/hunch/sway and a30% cosmetic landing catch-step after impact220cm/s+airtime180ms; recovery700ms/cooldown1.6s. Its private seeded stream never consumes combat/story RNG, and the layer neither moves the capsule root nor locks input. Shared NPC dynamics remain unchanged. Final clumsy suite144/144 and focused5/5 pass with0warnings; all8,902 full-suite input hashes stay unchanged. Actual1,126-frame private capture measures45.2cm hop, one forced+one normal-chance stumble; independently measured stationary root drift is below0.001cm. Teleport cancellation uses a200cm observed displacement heuristic; wider traversal and packaged behavior remain unverified. See Docs/Verification/ClumsyDink.

Mouse wheel adjusts the existing interior camera through a separate zoom offset, smoothly interpolated before room framing/occlusion. Limits180–650cm outdoors and180–320cm indoors; reversing at a limit responds immediately. `FDinkBodyDynamics` adds bounded damped mesh lean, starts/stops/turn response and independent idle sway to player and authored humanoid NPCs; player landings add a spring impulse. It uses observed displacement and game time, resets on teleports, and draws no gameplay random values. NPC script roots, original AI speed/timing, collision and hit math remain authoritative; this is secondary body motion, not ragdoll/cloth simulation.

New `Dink.Movement` automation exercises real controller Shift/Space input, measured speeds, jump/landing, frozen input, no double jump, camera persistence/limits and spring stability. When resetting a test story during an opening freeze, execute unfreeze BEFORE ResetRuntime: ResetSprites discards the director input-lock tracking. Build with `Scripts/build.sh -NoUBA` with access to the normal Unreal compiler caches; even this flag initializes cache services outside the restricted workspace.

Movement delivery verification:143/143 native checks pass in467s, with one successful Ch4Gold test carrying unrelated Epic HTTP telemetry/libcurl65 warnings; focused movement4/4 has0warnings. Independent review reproduced and fixed screen-transition zoom snaps and stale humanoid lean on sp_size/profile reconfiguration. Same-mode screen changes preserve ongoing zoom interpolation; replacement transforms reset owned lean bookkeeping correctly. Actual private keyboard/wheel evidence has1,081samples (walk200/run600cm/s, jump~108cm, zoom295–400cm), captured before those two fixes; the final regressions test the corrected paths.19suite-start source/module pins remain unchanged; end-state baseline comparisons pass3,403othertrackedfiles/1,874LFSassets plus5,510fixtures, without a whole-tree pre/post claim. See Docs/Verification/MovementControls. Wider-world jump traversal and packaged controls remain unverified.

## Current delivery checkpoint (7Nov2026 local /8Nov UTC)

Owner art direction update (8Nov2026 UTC): develop photorealistic art in Blender, using original Dink sprites as guide and inspiration. This latest owner request takes precedence over earlier stylised-realism preferences. Preserve recognisable original silhouettes, palette, placement/script identity and gameplay behaviour while improving real construction, materials and detail. New art and visual fixes develop in isolated sessions/checkouts; the visible SurfaceDelivery game remains frozen.

- FloorOakV1/UnderfloorV1 checkpoint (8Nov UTC):139/139 native tests,0warnings,436s; all8,835 inputs unchanged through testing and final GPU captures. The new oak is a material-only original-floor duplicate, retaining every vertex/UV/triangle group, both slot names, original nails, collision and Nanite settings. All56 floor instances plus the one asset row change mesh path only. One separate24-vertex/44-triangle underfloor closes real plank gaps at topZ=-16cm without collision/nav/overlaps. Its owner-screen context is hidden outdoors including hidden shadows/GI. Actual W exit and return pass; outside camera stays400cm. Same-camera blue floor ROI counts380/726 become0/0. Reader access errors were corrected using exact native reflected navigation property names in the same game; no restart or route teleport preceded the actual return. See Docs/Verification/SurfaceFinish and Scripts/FLOOR_SURFACE_PIPELINE.md.
- Saved-material verification uses the read-only editor DinkMaterialArtLibrary to inspect all connected property IDs, including Python-hidden pins. Direct BC/N/ORM links, channel choices, UV0 and specular.35 are checked; extra WPO/emissive/hidden UV connections are rejected even when reusing approved nodes. Eight real Unreal graph mutations and20 pure publication/source guard tests pass; all91Python tests and the integrated full source audit pass. Publishers recheck full gameplay-data hashes and exact saved package bytes before publication. Never rebuild a checkout whose libraries/assets are in use. Normal clones use LFS assets and verification mode; import refuses existing destinations. Clothing and furniture work-only candidates remain unpromoted.

- Starting-house VistaV4 and the qualified exterior-cottage camera policy pass the combined138/138 native suite with0warnings in472s; all8,743 tracked/runtime/generated/import/module inputs stayed unchanged. The local run label contains139 from an early estimate; the report count is138. See Docs/Verification/VistaFinal. A real W-key exit/return and separate window/door photographic fixtures pass. Stationary exterior camera distance remains400cm, with five cottage material slots fading only through the explicit occluder policy; physical collision, input and original warp positions are preserved.
- VistaV4 has359 render-only placements/62mesh references, including55 new V3 terrain/threshold packages and43 additional existing grass/tree instances. All644rooms pass loaded geometry checks, with no owner/neighbor intrusion. Source rebuilding reproduces all placements and preview pixels. After editing its Blender scene or additions JSON, run the source checker; the context generator requires a current receipt bound to both hashes. Independent stale-scene review failed the old helper and passes the fix;71Python tests pass. SourceShader edits require their own material/import review.
- Scripts/package.sh includes Dink/Props because the vista doorstep is loaded only through JSON. Private filesystem-DDC cooks should add -SkipZenStore through AdditionalCookerOptions: a Zen cooked-output server otherwise reuses the shared port, independently of the DDC graph. Keep UAT serialized with -WaitForUATMutex; do not signal another session's job or change shared cache data directories. Package and actual IoStore verification pass:62vista meshes and5fade materials present; packaged NullRHI startup loads the context actor and doorstep. See Docs/Verification/VistaFinal/package-verification.json. Game target82actions/44.98s; filesystem cook16.58s. Ordinary ExecCmds uses commas (Automation command chains alone parse semicolons).

- This project is delivered under DinkRemasterUE/ in the owner-selected GitHub repository. Original-engine files remain at the root. Scripts discover extraction data in the parent repo or the original sibling layout. The owner explicitly chose Git LFS for binary assets; the repository is now standalone and the asset upload is verified. Use git lfs pull; the existing release pack is only an optional recovery copy. UE5.8.4 stays outside the repo and must never be edited.
- The staged camera/fireplace snapshot passed130/130,0warnings,354s with666Data,225compiled files,7DLLs,8new material/mesh packages and651protected originals unchanged. All6 original gameplay traces and healer payment matched prior verification. See Docs/Verification/house-stage130.json. This is not a claim of full-world art or complete sanctuary/Mog gameplay.
- Actual W house exit/return passed. Native projection-based component occlusion now fades the foreground door jamb while preserving empty-doorway, behind-eye and beyond-pawn controls, physical collision and shadow behavior. Before/fixed captures and routes are in Docs/Verification.
- FireplaceV2 retains P19’s original transform/script, has251×111.5×300.4cm actual source dimensions,3authored fallback LODs15484/8050/4180 and6fitted hulls. Nanite follows the Blender source, with explicit PercentTriangles1.0 and material usage. Reported render bounds can include Nanite's coarse envelope; use source vertices and real hull queries for physical scale. Local firelight is40lm/2000K/55cm; global exposure is unchanged.
- Seven real-game capsule fixtures, real F/E responses and1,150sampled ordinary-Mother poses passed; sampling does not prove all possible AI paths. The window/door vista is now verified as an incremental runtime art pass. Surface finish, clothing repairs, story variants and wider-world graphics remain in progress; work-only wardrobe candidates are not promoted.
- Audio choices remain44SFX/28music; rejected9/44/48/49 stay excluded. The owner explicitly confirmed public redistribution rights for generated ElevenLabs audio; see SourceAssets/Audio/REDISTRIBUTION.md. Voice candidates remain candidates.
- Initial implementation is imported from local checkpoint afb04b9, overlaid with the exact verified camera/data/fireplace snapshot. The consolidated native delivery passed134/134 with0warnings in920s;2,992pinned files/DLLs stayed unchanged. Compiled runtime and asset bytes match that tested checkout. PR3 integration updates only the globals CSV provenance comment; all63fact rows remain identical (Docs/Verification/pr3-integration.json). See Docs/Verification/delivery-full134.json and delivery-input-pins.json. Camera ownership and asset-bootstrap independent reviews passed; import recovery is verified separately. Local Saved verification artifacts and generated/template assets remain ignored.

## What this is

- Unreal Engine 5.8 C++ project `DinkRemaster` for a free fan remaster of Dink Smallwood (1997).
- The companion **data repo** is the parent repository (`..`) in this layout, or `../Dink-Smallwood-Remaster` in a standalone sibling checkout (a fork of the Dink Smallwood HD
  engine). It holds the plan (`doc/remaster/REMASTER_PLAN.md`), the content bible
  (`doc/remaster/bible/`), the original game data (`bin/dink/`), the original engine source
  (`source/dink/dink.cpp`) and the Python extraction pipeline (`tools/`). Treat it as read-only
  from this project unless told otherwise. This project never reads it at run time; data needed at
  run time is copied in as text files with a regeneration script.
- Engine: Epic's prebuilt Linux build of UE 5.8.4 at `~/UnrealEngine/UE_5.8.4` (override with
  `UE_ROOT`). Never modify anything under it (see "Linux problems" for what the tools write there
  on their own).

## Commands (verified 5-6 Nov 2026 on the dev machine)

| What | Command | Time |
|---|---|---|
| Build editor target | `Scripts/build.sh` | ~28 s from clean, 2-8 s incremental |
| Run all tests headless | `Scripts/test.sh` | 8 Nov 2026 UTC (after the `external`/`spawn` fix, ten probe chapters): **136/136**, 0 warnings, 508 s. Before: 133/133 after the `sp_script` fix (nine chapters), 0 warnings, 463 s (an earlier run by another agent on the same tree: 133/133, 746 s under load). Before: main suite 130/130, 442 s (Camera integration receipt above). |
| Run a subset | `Scripts/test.sh Dink.Core.Combat` | ~13 s |
| Regenerate the globals table | `python3 Scripts/regen_globals.py [data repo path]` | < 1 s |
| Bring in the converted Ink story | `python3 Scripts/sync_story.py [--data <repo>] [--rebuild] [--check]` | < 1 s (`--rebuild` runs the converter first: ~9 s) |
| Bring in map.dat/dink.ini gameplay data | `python3 Scripts/sync_gameplay_data.py [--data <repo>] [--check]` | < 1 s (reads the data repo's `tools/dinkex/out`) |
| Build the game (non-editor) target | `$UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh DinkRemaster Linux Development -Project=<abs>/DinkRemaster.uproject -WaitMutex` | ~32 s (verified 6 Nov 2026 in the project dir; writes `Binaries/Linux/DinkRemaster`) |
| Cook and package the game (Linux, Development) | `Scripts/package.sh [stage dir]` | ~40 s from an empty `Saved/Cooked` (cook 22-42 s, 5,189 packages; shaders from the shared DDC), 30-65 s incremental; stage `Saved/StagedBuilds` 1.5 GB (`Content/Paks` 575 MB, binary 300 MB + 296 MB `.debug`/`.sym`); verified 7 Nov 2026 |
| Run the probe in the packaged game | `Scripts/run_packaged_tests.sh [stage dir] [filter]` | 10 chapters (Ch1-Ch9 and `ChAJoppa`, chapter 10), one process each: 7 + 6 + 2 + 7 + 1 + 2 + 6 + 4 + 2 + 2 s (8 Nov 2026 UTC; the PIE chapters take 39 + 25-32 + 9 + 28-35 + 1 + 2 + 31-33 + 10-12 + 10 + 6 s unloaded, up to 87 s on a loaded machine); prints `PARITY OK` per chapter (trace md5 equals the editor's) |
| Export the import bundle | `python3 Scripts/export_import_bundle.py [--data <data repo>]` | ~30 s |
| Greybox import, Stonebrook | `Scripts/import_greybox.sh --region stonebrook` | 8 s editor from a clean `_Generated/` (+ ~20 s import tests, + ~30 s export if no bundle); re-run 6 s |
| Greybox import, whole world | `Scripts/import_greybox.sh --region all` | 25 s editor (+ ~20 s tests); re-run 7 s |
| Copy the template character content | `Scripts/copy_template_content.sh [--force]` | < 1 s (run by the import) |
| Render evidence images (GPU, no display) | `Scripts/capture_greybox.sh [--region stonebrook]` | 8 s (2 min first time: shader compile). **Does not work yet**: renders nothing, exits 1 |

- `Scripts/build.sh` runs
  `$UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh DinkRemasterEditor Linux Development -Project=<abs>/DinkRemaster.uproject -WaitMutex -NoHotReloadFromIDE`,
  writes `Saved/Logs/build.log`, prints `BUILD OK: ...` or `BUILD FAILED ...` plus the first
  compiler errors, and exits with UBT's code (0 = success; a compile error gave 6). Extra
  arguments go to UBT (e.g. `-DisableAdaptiveUnity`, `-Clean`).
- `Scripts/test.sh` runs
  `env -u WAYLAND_DISPLAY -u DISPLAY UnrealEditor-Cmd <abs>/DinkRemaster.uproject -ExecCmds="Automation RunTests Dink; Quit" -ReportExportPath=<abs>/Saved/Automation/Report -nullrhi -unattended -nosplash -nopause -nosound -stdout -FullStdOutLogOutput`,
  writes `Saved/Logs/test.log` and `Saved/Automation/Report/index.json` (+ `index.html`), prints
  `TESTS PASSED: 31/31 passed, 0 failed (...)` or `TESTS FAILED ...` with the failing test paths,
  and exits 0 only if the editor exited 0 AND the report shows at least one test and no
  failures. Verified to fail (exit 1) on a deliberately broken test and on a filter that matches
  nothing. It needs a built project; it refuses to run otherwise.
- The game target also compiles, including Inkpot's InkPlusPlus and DinkNarrative
  (`Build.sh DinkRemaster Linux Development -Project=...`, ~32 s, 0 warnings, verified 6 Nov 2026; 17 s with the DinkProbe module on 7 Nov).
  It is cooked, packaged and run since 7 Nov 2026: see "Packaged build".
- Project files are NOT needed to build. Do not run `GenerateProjectFiles.sh` against the shared
  engine install: see "Linux problems".
- Every agent task that touches C++ ends with `Scripts/build.sh && Scripts/test.sh`, and both
  summary lines go in the handoff.
- `Scripts/import_greybox.sh` runs the commandlet
  `UnrealEditor-Cmd <abs>/DinkRemaster.uproject -run=DinkImportGreybox -Region=<region> -unattended -nosplash -nopause -nullrhi -nosound -stdout -FullStdOutLogOutput`
  (with `WAYLAND_DISPLAY`/`DISPLAY` unset), writes `Saved/Logs/import_<region>.log`, prints the
  importer's `DINK IMPORT OK: ...` line plus asset counts and size, then runs
  `Scripts/test.sh Dink.Import` (skip with `--no-test`). Exit 0 only if both succeed. Options:
  `--export` (re-export the bundle first; automatic when `ImportData/bundle.json` is missing),
  `--dry-run` (report only), `--data <data repo>`.

### Packaged build (proven 7 Nov 2026)

The probe runs in a packaged game and plays the same game as in PIE. Full account, with what the first design got wrong: `Plugins/DinkParity/Docs/packaged_probe.md`.

- **Modules.** The probe is its own module `DinkProbe` (`Plugins/DinkParity/Source/DinkProbe`, `DeveloperTool`: editor and Development game, never
  Shipping). `DinkParity` (every other test, `UnrealEd`) is module type `Editor`; the `DinkParity` entry in `DinkRemaster.uproject` has no
  allow-list any more. `DinkProbeTests.cpp` has `#if WITH_EDITOR` around PIE start/stop and the map load, `ProbeWorld()` for the world, and
  `DoesPackageExist` for the map in the package (a missing map is an error there, never a skip); the two repeat tests are editor-only.
- `Scripts/package.sh [stage dir]` (the game target `Source/DinkRemaster.Target.cs` has unity builds off like the editor target: pitfall 61): RunUAT `BuildCookRun` of the `DinkRemaster` game target, Linux, **Development** (Shipping has no
  automation tests), `-cook -stage -pak -iostore -compressed`, one map to cook (`L_Greybox_World`, sublevels by reference), staging to
  `Saved/StagedBuilds` (binary `<stage>/Linux/DinkRemaster/Binaries/Linux/DinkRemaster`), log `Saved/Logs/package.log`, one `PACKAGE OK` /
  `PACKAGE FAILED` line (it also checks that `Dink/Data/Story/dink.json` is in the pak). It refuses to run without the generated
  `L_Greybox_World`, without a built editor, or while a headless editor/UBT/UAT (or an editor/game of this project) is running; passes `-nocompileeditor`
  and `-cookdir=` for the content that is only loaded by string path (`Dink/{Kits,Audio,Creatures,NPC,Hero,Materials,Textures}`, `Characters`, `Input`).
  Run `Scripts/build.sh` first (the cook runs the editor binary). Not `-SkipCookingEditorContent`: see pitfall 50.
- `Scripts/run_packaged_tests.sh [stage dir] [filter]`: runs the packaged game headless
  (`-ExecCmds="Automation RunTests <filter>; Now; Quit" -nullrhi -unattended -nosound -UseFixedTimeStep -FPS=60 -DinkProbeHold`), parses the JSON report
  like `test.sh` (the exit code is not trusted alone; a "skipped" test counts as a failure), prints `TESTS PASSED/FAILED`, and for
  the probe runs one game process per chapter (a packaged process has one GameInstance; chapters hand over through
  `<stage>/Linux/DinkRemaster/Saved/SaveGames/probe_chN.sav`, as in the editor) and compares each chapter's trace md5 with the PIE trace in
  `Saved/Narrative` (`PARITY OK/DIFF`).
- **Proven:** cook without errors; `Dink/Data` (644 hardness files, story, CSVs, Art/Audio JSON) staged in the pak and read through it; string-loaded
  art loads (`DINK ART OK`, character and creature art in the game log); `Automation RunTests` runs a `DeveloperTool` module's tests in the game,
  exit code 0/255, `index.json` written; the ten probe chapters (Ch1-Ch9 and ChAJoppa, 7 Nov 2026 night, after the `external`/`spawn` fix) give the editor's trace md5s (b3760d52d7, 253e6f7268, e9fce770bc, d431e6780f,
  6c709d1069, 9e87080221, d50e5111f6, 28406402c0, 1db62e4adb, c532805f11 on both sides; one package run, 51 s with an incremental cook, then the ten processes). (Earlier the same day, after the `sp_script` fix: b3760d52d7, a5cfdf70bc, e9fce770bc, cd1b3bf820, 6c709d1069, 9e87080221, 7cc6e2fe93, 6697a02e52, 0ea9677ee2; before it chapters 1-6 matched with 50091fcc80... 7471375e32.)
  The probe's chapter trace needs a PIE-identical start: the DinkProbe module's `-DinkProbeHold` (world paused until the probe starts, story ticked before the greybox)
  and lower-cased event texts: pitfalls 47-49.
- Not proven / not done: Windows; a Shipping package (no tests by design); anything rendered (the run is `-nullrhi`); the packaged game with a window
  and input; the other test files in a package (editor-only); `&story 16`.

## Layout

```
DinkRemaster.uproject       UE 5.8 project; enables the Dink plugins, EnhancedInput, StateTree,
                            PythonScriptPlugin (editor), disables DinkExpanded and AndroidFileServer
Source/DinkRemaster/        thin primary game module (no gameplay code)
Plugins/DinkCore/           runtime rules (C++), see below
Plugins/DinkParity/         DinkParity (Editor module: automation tests in Private/Tests) and DinkProbe (DeveloperTool: the probe, also in Development game builds)
Plugins/DinkNarrative/      runtime: Ink story subsystem, director, floating text/menu, console (see "Narrative runtime")
  Docs/director_status.csv  every director command -> implemented / recorded (checked by a test)
Plugins/Inkpot/             THIRD-PARTY (MIT): Inkpot's InkPlusPlus C++ Ink runtime only (see "Narrative runtime")
Plugins/DinkImport/         editor shell: JSON-to-level importer, validators, commandlets (empty)
Plugins/DinkExpanded/       content-only plugin for non-original content, disabled by default
Content/Dink/Data/          text data read at run time (staged via DirectoriesToAlwaysStageAsUFS)
  Facts/dink_globals.csv    the 63 original globals with initial values (generated)
  Story/                    the converted Ink story (Scripts/sync_story.py; never hand-edit):
                            dink.json (inklecate 1.2.1, ink v21), names.csv, director_vocabulary.csv,
                            story_manifest.json (data repo commit, hashes)
  Gameplay/                 map.dat sprite fields, dink.ini frames (hardboxes, hit frames, loops, sizes),
                            screen base scripts, Hardness/SCR_nnn.txt (every screen's hardness map per
                            &vision) (Scripts/sync_gameplay_data.py; never hand-edit)
  AI/adaptation.ini         the 3D adaptation layer's numbers (hand-authored)
Content/Dink/_Generated/    GIT-IGNORED. Everything the greybox importer writes (never hand-edit;
                            delete it to rebuild from scratch): Shared/ (materials, card mesh),
                            Sprites/ (T_/MI_Sprite_<seq>_<frame>), Screens/SCR_nnn/ (ground
                            texture + material, SM_SCR_nnn_Visual/_CollSolid/_CollLow),
                            Maps/ (L_Greybox_<Region> + sublevels), import_manifest.json (hashes)
Content/Characters/, Content/Input/   GIT-IGNORED copies of the engine's third-person template
                            content (Scripts/copy_template_content.sh)
ImportData/                 GIT-IGNORED import bundle (Scripts/export_import_bundle.py)
Config/                     Default*.ini (third-person PC defaults; collision channels; rendering TODOs)
Scripts/                    build.sh, test.sh, regen_globals.py, sync_story.py, sync_gameplay_data.py, export_import_bundle.py,
                            import_greybox.sh, copy_template_content.sh, capture_greybox.sh
```

Planned content layout (bible 05 section A, not created yet):
`/Game/Dink/{Core,Hero,NPC,Enemies,Kits,Biomes,Items,Magic,UI,Audio,Cine,Data}`,
`/Game/Dink/World/{Overworld,Interiors/<Region>}`, and `/Game/Dink/_Generated/` (importer-owned,
never hand-edited).

### DinkCore classes

| File | What |
|---|---|
| `DinkOriginId.h` | `FDinkOriginId` {Screen 1..768, Placement 1..99}, text `S412_P03`, parse/format, hash |
| `DinkOriginComponent.h` | `UDinkOriginComponent`: origin ID, script name, source hash on every imported actor |
| `DinkFactTypes.h` | `FDinkFactCondition` {Fact, Op, Value} with Evaluate and text form `story >= 5` |
| `DinkFactSubsystem.h` | `UDinkFactSubsystem` (GameInstance): integer facts by original name, get/set/add, per-fact and global change delegates, CSV initial values, reset/restore |
| `DinkWorldStateSubsystem.h` | `UDinkWorldStateSubsystem`: per-origin overrides = original `editor_type` 1-8, game clock in ms, screen exit times, respawn rule |
| `DinkRandom.h` | `IDinkRandomSource` (`rand() % n`), seeded stream source, scripted test source |
| `DinkStatTypes.h` | `FDinkStats` (new-game defaults), level-up enums, missile "fixes level" enum |
| `DinkCombat.h` | `DinkRules::` exact ports of the original maths, each with its `dink.cpp` line; `UDinkCombatLibrary` for Blueprints |
| `DinkStatsComponent.h` | `UDinkStatsComponent`: damage intake, touch immunity, exp/level-up, magic charge, optional two-way mirror with the engine-kind facts (facts are the source of truth) |
| `DinkInventoryComponent.h` | `UDinkInventoryComponent`: 16 item + 8 magic slots of item IDs, one armed item and one armed spell |
| `DinkSaveGame.h` | `UDinkSaveGame` (v2): version, facts, overrides, exit times, clock, stats, inventory, screen, transform, `SubsystemState` (text blobs of other modules: "narrative"); capture/apply; versioned migration |
| `DinkSaveSubsystem.h` | `UDinkSaveSubsystem`: snapshot/apply/slot IO for a game instance + player actor; `OnSnapshotCaptured`/`OnSnapshotApplied` for modules outside DinkCore |
| `DinkLayout.h` | **The one coordinate transform**: `FDinkScreenCorners`, `DinkLayout::MapPixelToMetres` (bilinear, = tools/analyse), `MetresToUnreal`, inverse, local yaw, quad containment |
| `DinkCollision.h` | Channel/profile names for hardness: `DinkHardSolid`, `DinkHardLow`, `DinkProjectile` trace, `DinkWarpTrigger`, `DinkScreenVolume` (defined in `Config/DefaultEngine.ini`) |
| `DinkOriginComponent.h` | (extended) + sequence, frame, placement type, `ClassId`/`Category` (sprite_classes.csv), `ScriptKind` (script_kinds.csv) |
| `DinkInstanceOriginsComponent.h` | origins of placements imported as instances (background, editor type 0) |
| `Greybox/DinkScreenVolume.h` | `ADinkScreenVolume`: one per original screen; ID, region, kind, indoor, music, encounter/screenlock, interior, vision rules, corners, 4 edge walls; `SetLockBarriers` (locked-fight slabs on the open edges) |
| `Greybox/DinkPlaceholderActor.h` | `ADinkPlaceholderActor` (card + origin + vision gating), `ADinkWarpPlaceholderActor`, `ADinkScriptWarpActor`, `ADinkGreyboxScreen` (ground/blocker/collision meshes + background instances) |
| `Greybox/DinkWarpComponent.h` | `UDinkWarpComponent`: warp trigger box, destination, teleports the player on overlap |
| `Greybox/DinkGreyboxSubsystem.h` | world subsystem: current screen (on-screen display), `dink.Goto`, `dink.Vision`, `dink.Where`, warp cooldown, `SetScreenLocked` (one locked screen at a time) |
| `Greybox/DinkGreyboxCharacter.h` | `ADinkGreyboxCharacter` (third-person run/walk/jump; carries `UDinkStatsComponent` mirrored to facts + `UDinkInventoryComponent`) and `ADinkGreyboxGameMode` |

### DinkImport (editor module)

| File | What |
|---|---|
| `DinkImportBundle.h` | reader for `ImportData/` (screens, placements, warps, sprites, collision rectangles) |
| `DinkGreyboxImporter.h` | `FDinkGreyboxImporter::Run`: assets, maps, reconcile, coverage, report |
| `DinkImportGreyboxCommandlet.h` | `-run=DinkImportGreybox -Region=... [-DryRun] [-Bundle=dir]` |
| `DinkGreyboxCaptureCommandlet.h` | `-run=DinkGreyboxCapture -Region=... -AllowCommandletRendering` (evidence images) |
| `Private/DinkGreyboxAssets.*` | textures, materials, meshes, manifest hashes |

Tests: `Plugins/DinkParity/Source/DinkParity/Private/Tests/*.cpp`, named `Dink.Core.*` (33),
`Dink.Import.*` (10, `DinkImportTests.cpp`), `Dink.Narrative.*` (17, `DinkNarrativeTests.cpp`; `Director.SpScriptRunsMainAtOnce` and `Director.ExternalAndSpawnRunAtOnce` are the `sp_script` and `external`/`spawn` parity tests) and
`Dink.Gameplay.*` (32 on 7 Nov 2026: headless in `DinkGameplayTests.cpp` and `DinkAuthoredInteractionTests.cpp`, the probe chapters `Probe.Ch1Stonebrook`..`Ch9Windemere` and `Probe.ChAJoppa` (PIE, or a packaged game) and their two editor-only repeat tests in `Plugins/DinkParity/Source/DinkProbe/Private/DinkProbeTests.cpp`, `Texts.ExpiredTextKeepsARecycledHandle`) and
`Dink.AI.*` (12, `DinkAITests.cpp`).
Shared helpers in `DinkTestHelpers.h`.

## Conventions

- **Text first.** Gameplay rules live in C++; data lives in text (CSV/JSON/INI, later Ink) that
  diffs and that agents can read. Blueprints are only for composition and presentation (specific
  enemies, AnimBPs, widgets, VFX hookup). Tunables go in data, not in new formulas.
- **No Blueprint-to-Blueprint hard references.** Go through C++ interfaces, GameplayTags or
  subsystems.
- **Origin IDs everywhere.** Every actor converted from the original carries a
  `UDinkOriginComponent` with its `S{screen:03}_P{placement:02}` ID. World state, saves,
  coverage reports and parity tests key on it. Never invent IDs for original content; hand-made
  actors simply have no origin component.
- **The save model is the original's.** Facts + per-placement overrides + player stats and
  inventory + position. The world is never serialised; it is rebuilt from data plus the save.
- **Facts use original names** without `&` (`story`, `old_womans_duck`, `s2-nad`, and the typo
  `missle_source`). Do not rename them; parity tooling matches on them.
- **Port, then tune.** Original formulas are ported exactly into `DinkRules` with a source-line
  comment; the original numbers are the "Classic" data. Re-tuning happens in data.
- **Injectable randomness.** Rules take an `IDinkRandomSource&` and call `RandomModulo(n)` where
  the original calls `rand() % n`, in the same order. Tests use `FDinkScriptedRandomSource`.
- **Save changes need a migration step** in `UDinkSaveGame::MigrateToCurrentVersion` and a
  `CurrentVersion` bump; that includes changing a default value of a saved field (values equal to
  the default may not be written). Never edit an existing step. Add a test for each step.
- **Tests:** plain C++ automation tests, flags `DINK_TEST_FLAGS`, names `Dink.<Area>.<What>`.
  `Dink.Core.*` use no assets. `Dink.Import.*` read the git-ignored bundle and generated maps; when
  those are missing they pass with a "skipped" warning (test.sh reports "N with warnings"), so a
  fresh clone still passes; `Scripts/import_greybox.sh` runs them after every import. Expected log warnings/errors must be declared with `AddExpectedMessage`
  BEFORE the call that logs them. Game-instance subsystems in tests need a `UGameInstance` outer
  (`DinkTest::MakeOuterGameInstance()`).
- **Git:** never `git commit` or `git push` unless explicitly told to ("commit" means local only;
  it is not permission to push). Never add AI co-author lines (no `Co-Authored-By` for
  Claude/Codex/OpenAI etc.) to commits. The owner explicitly requested commits, PRs, review and merge for this delivery; origin is cdavisv/Dink-Smallwood-Remaster.
- **Binary assets:** use Git LFS through `.gitattributes`, including lockable Unreal packages and editable source art. Run `git lfs pull` and the full source verifier before building/importing. Expected asset hashes come from Git’s staged pointers; metadata-only verification does not establish missing binary contents. CSV/JSON/INI/Ink and source code stay plain Git text. Preserve modified local art. The historical release pack is optional recovery tooling, not the primary storage policy.
- **Secrets:** never commit credentials or tokens; local notes go in `agents_secret.md`
  (git-ignored).

## Data regeneration

`Content/Dink/Data/Facts/dink_globals.csv` is generated from the data repo:

```
cd ../Dink-Smallwood-Remaster/tools/dinkc && python3 -m dinkc build --scripts ../../bin/dink/story --map ../../bin/dink/map.dat --dat ../../bin/dink/dink.dat --out out
cd ../../../DinkRemasterUE && python3 Scripts/regen_globals.py
```

The first step writes only the data repo's git-ignored `tools/dinkc/out/`. The CSV header comment
records the data repo commit it came from (b1bf75d at creation). `Dink.Core.Facts.ShippedTable`
checks the count (63, 22 engine-bound) and key initial values.

## Greybox import (pipeline stage 6)

Turns the original world into a walkable greybox. Two steps, so the Unreal side never reads the
data repo:

1. `Scripts/export_import_bundle.py` (stdlib + numpy + Pillow, outside Unreal) gathers from the
   data repo's `tools/*/out/` into `ImportData/`: `screens.json`, `placements.json`, `warps.json`,
   `collision.json` (hardness merged into rectangles), `samples.json` (test points), `sprites.json`,
   `ground/SCR_nnn.png` (tile layer, 600x400), `sprites/<seq>_<frame>.png` (power-of-two, colour
   bled into transparent pixels) and `bundle.json` (data repo commit, input hashes, per-region
   counts, start, data notes). Deterministic: same input, byte-identical output. If an input is
   missing it prints the data-repo command that regenerates it.
2. The `DinkImportGreybox` commandlet (C++, `Plugins/DinkImport`) builds assets and maps.

Why C++ for the importer and Python only for the bundle: the image and hardness work needs
numpy/Pillow, which the editor's Python does not have; the importer needs mesh descriptions,
collision setup, level streaming and actor reconciliation, which are typed C++ APIs, and the
runtime classes it spawns (and the transform the tests check) must be C++ anyway.

**Output.** `/Game/Dink/_Generated/Maps/L_Greybox_<Region>` (`L_Greybox_World` for `all`): a
persistent level (game mode, player start, sun, sky light, atmosphere, height fog) with one
always-loaded sublevel per layout group: `_Mainland`, `_Joppa`, `_Darklands`, `_SnowIsle`,
`_Fragments`, `_Interiors` (only the groups the region has). Not World Partition: plain
always-loaded streaming levels are created and saved headless reliably
(`UEditorLevelUtils::CreateNewStreamingLevelForWorld`), need no external-actor files (5,500
tiny packages), and every sublevel is one file per landmass. Revisit World Partition when real
art makes streaming necessary.

| What | How |
|---|---|
| Axis mapping | metres x east / y south -> Unreal X / Y (cm), height -> Z. Left-handed Z-up, so this is not a mirror (yaw +90 turns east into south). Only in `DinkLayout` (DinkCore). |
| Ground | per screen one mesh, 12 x 8 quads following the bilinear map (screens are not rectangles), UV = original pixel / 600, 400; texture = the tile layer, stretched to 1024x512; lit material. |
| Blockers (visible) | hardness 1/3 grey 1.0 m prisms, 2 (low) blue 0.35 m, 100 (sprite hardbox) brown 1.0 m, 200 (warp hardbox) magenta 1.0 m; filled open water = translucent blue plane. |
| Collision | `CollisionSolid` (profile DinkHardSolid): ground + 3 m prisms of codes 1, 3, 100, 200 + filled canopy/void; `CollisionLow` (DinkHardLow, projectiles cross): code 2 + filled open water. Complex-as-simple trimeshes, one per screen. Hardness pixels are merged into rectangles (88,125 for the world). |
| Fills | the original draws hardness as outlines (open sea, canopy and the void around rooms are hardness 0). Code-0 components whose terrain group (tile_classes.csv, as tools/analyse groups it) is water / canopy / void are filled. Checked: no reached tools/analyse component is filled. |
| Edge walls | invisible 3 m walls on screen edges whose grid neighbour is missing, on another sheet, or not in this import (the original cannot walk off such an edge either). |
| Placements | 4,206 actors (`ADinkPlaceholderActor`; `ADinkWarpPlaceholderActor` for the 93 sprite warps) + 1,640 instances (background type 0 without vision gate, warp or missing picture) on the screen's `ADinkGreyboxScreen`. Card = original picture, two-sided, unlit, facing south; size = picture pixels x local layout scale ("layout": buildings, walls, trees, rocks, furniture... so card, painted ground and hardness agree) or x base 0.025 m/px ("base": npc, enemy, animal, pickup, effect). Hardness-only (type 2) cards are hidden in game. |
| Vision | 164 vision-gated placements are actors with `Vision`, `VisionCondition` (`vision == N`) and `VisionRules` (the DinkC `&vision = N` assignments with their enclosing conditions, e.g. `s1-h1-s:6 [(&story == 3)]`). Hidden at play start (the original loads screens with `&vision = 0`); `dink.Vision <screen> <N>` shows a variant. Collision follows vision 0. Outliner folder `<Group>/SCR_nnn/Vision_N`. |
| Warps | 93 sprite warps: trigger box = hardbox + 30 cm, on the placement actor. 19 script warps -> 23 sources: 18 placed ones fire on touching the placement (approximation: story conditions and dialogue not modelled), 5 are inactive markers (fired by cutscenes or other scripts). A trigger whose destination screen is not in the import is disabled. |
| Screens | one `ADinkScreenVolume` each (643; SCR_299 excluded, see below): ID, region, name, kind, indoor, music, encounter (screenlock, 35 screens), interior set, vision rules, corners. |
| Interiors | 74 indoor screens sit in their own space (tools/analyse packs them 3 km south of the world, sheet `interior:INT_nnn`), in the `_Interiors` sublevel, reached through their doors. |
| Start | SCR_001 (Dink's house) map pixel (314, 161), facing west: `main.c` sets `&player_map = 1`; `start-1.c` does `sp_x(1, 334)` (minus the 20 px bar), `sp_y(1, 161)`, `sp_dir(1, 4)`. Screen 1 *is* Dink's house in its normal state (vision 0); the burning and burnt sets are its vision 1 and 2 placements (`s1-h1-s`). |
| Character | `ADinkGreyboxCharacter`, 6 m/s, no jump, template camera boom; mesh `SKM_Manny_Simple` + `ABP_Unarmed`, input `IMC_Default` + `IMC_MouseLook` (copied from `Templates/TemplateResources/High/{Characters,Input}`). |

**Idempotent and traceable.** Assets carry content hashes in
`Content/Dink/_Generated/import_manifest.json`; generated actors carry tags `DinkGenerated`,
`DinkKey=<id>`, `DinkHash=<hash>`. A re-run rebuilds only changed assets/actors, respawns actors
moved by hand (reported as "moved by hand"), deletes generated actors whose origin left the
import, leaves untagged actors alone (reported as "foreign"), saves only changed packages and
prints `drift N` (0 = nothing written; verified: every file under `_Generated/` byte-identical
after a re-run). Reports: `Saved/Import/coverage.csv` (every screen, placement, script/sprite
warp and the start: what it became or why it was skipped; also `coverage_<region>.csv`) and
`Saved/Import/import_<region>.json`.

**Numbers (6 Nov 2026, data repo b1bf75d, warm DDC):** Stonebrook: 61 screens, 640 placement
actors, 134 instances, 13 warp triggers, 77 vision-gated; 654 assets + 3 maps, 21 MB; 8 s in the
editor from a clean `_Generated/`. Whole world: 643 screens, 4,206 actors + 1,640 instances =
5,846 placements, 116 warp triggers, 164 vision-gated; 4,191 assets (643 ground textures and
materials, 1,779 meshes, 558 sprite textures and materials, 10 shared) + 10 maps, 175 MB
(Screens 141 MB, Sprites 13 MB, Maps 22 MB); 25 s in the editor. Re-runs: 6-7 s, drift 0.

**Verified headless** (`Dink.Import.*`): transform = world_layout.json for all 5,846 placements
(max 0.14 mm, yaw 0.0002 deg); continuity across all 1,649 walkable crossings (gap 0) and none of
the 22 crossings cut between sheets is reached; no two imported screens overlap; map content =
bundle counts (origin actors, instances, unique IDs, every placement once, screen volumes, warps,
vision conditions); collision: sampled walkable pixels free with ground under them, solid pixels
block walkers and projectiles, low pixels block walkers only, the new-game start and 115 of the 116 warp
destinations free with ground under them (4,634 / 2,194 / 1,816 samples in the world; the 116th,
`SW_s2-culg_L42`, targets y 480, below its screen's 400 px map, and is an inactive marker); mesh faces point the right way;
PIE: the character spawns at the start, runs at 600 cm/s, vision-gated placements start hidden,
walking into Dink's front door lands on SCR_439.

**Rendered visual evidence is now available (6 Nov 2026).** `Scripts/playtest_desktop.py` captures the actual Hyprland viewport using `grim`, drives real keyboard input with `wtype`, and refuses to type if the Dink window loses focus. `Scripts/Playtest/README.md` describes reproducible routes and commands; evidence is in `Saved/Playtest/evidence`. The old `capture_greybox.sh` commandlet still fails because its scene capture does not tick/render; use the desktop workflow for rendered QA.

**Only a person at the editor can judge:** whether the world reads as Dink (cards facing south
look flat from the side; ground resolution 600x400 per screen), scale (are 60 x 40 m settlement
screens and 2.5 cm/px props right in third person; is the mainland, 236 s east-west at 6 m/s, too
small), dead stretches, sightlines (fog density 0.02, start 150 m: does the Edge plateau or the
Darklands show from the mainland), lighting/exposure, camera feel, whether invisible 3 m walls
and 1 m outline prisms are acceptable greybox language, and performance with everything loaded.

**How a human walks it:** build (`Scripts/build.sh`), import (`Scripts/import_greybox.sh
--region stonebrook` or `--region all`), open the editor with the project, File > Open Level >
`Content/Dink/_Generated/Maps/L_Greybox_World` (or `L_Greybox_Stonebrook`), press Play. WASD +
mouse; the top-left line shows the original screen (ID, region, area, kind, music, locks,
visions). Console (`~`): `dink.Goto 439` (any screen; optional map x y), `dink.Vision 1 2`
(burnt house), `dink.Where`, `dink.ScreenInfo 0`. Do not edit the generated maps; put
hand-made work in your own maps (a re-import would keep untagged actors, but `_Generated/` is
git-ignored and may be deleted).

**Questions the greybox is meant to answer:** Is the world too small or too big at 6 m/s (the
plan's per-kind scales: settlements x4, wilderness x2.75, dungeons x2.25, interiors x1.75)? Where
are the dead stretches (long wilderness runs with nothing on them, sea screens)? Do sightlines
break regions apart (can you see the Darklands, Joppa or the snow isle from the mainland; is the
escarpment a real wall)? Do settlements feel like places at 4x, or empty? Are interiors cramped
at 1.75x with a third-person camera? Does the trapezoid stretching between settlement and
wilderness read as natural? Which outline blockers (fences, shore lines) feel arbitrary in 3D?

## Narrative runtime (DinkNarrative, built 6 Nov 2026)

Runs the data repo's converted Ink story (`tools/dinkink`, contract: its `DESIGN.md`) inside
Unreal. Everything is C++ and text; no Blueprint or widget assets.

**Ink runtime: Inkpot's InkPlusPlus.** `Plugins/Inkpot` is a trimmed copy of
https://github.com/The-Chinese-Room/Inkpot at commit `34a2e9e940fceb83f733d81b6217b973d6a33be3`
(1 Nov 2026, release 1.42.21, "updated to build with Unreal 5.8"), licence MIT
(`Plugins/Inkpot/LICENSE`, Copyright (c) 2023 The Chinese Room; keep it). Only `LICENSE`,
`README.md`, `Inkpot.uplugin` and `Source/InkPlusPlus` (the C++ port of the ink runtime, depends on
Core/CoreUObject/Json only) are vendored. Left out on purpose: the `Inkpot` and `InkpotEditor`
modules (UObject story assets imported from `.ink` in the editor, gameplay tags, a blotter UI),
`Content/` (Blueprint widgets and import pipelines), `ThirdParty/` (125 MB of inklecate binaries;
we compile with the inklecate on PATH outside Unreal) and `TestInkSource/`. To take a newer
Inkpot: clone it, copy those four items over, re-apply the patches below. Patches (all marked
`DinkRemaster patch`):
1. `Inkpot.uplugin`: one module (`InkPlusPlus`), no `EditorScriptingUtilities` dependency,
   `CanContainContent` false, description says it is trimmed.
2. `Private/Ink/JsonExtension.cpp` line 11 and `Private/Ink/JsonSerialisation.cpp` lines 230 and
   251: `for (const TPair<FString, ...>& p : Map)` over maps whose keys are `UE::FSharedString` in
   5.8 binds to a temporary; clang 20 makes that an error (`-Wrange-loop-construct`). Changed to
   `const auto&` with `FString(*pair.Key)` where an FString is needed (upstream builds with MSVC).
Format check: inklecate 1.2.1 writes `inkVersion` 21; InkPlusPlus reads 18..21 (`Story.h`). The
story (377 knots, 930 entry points since the converter stopped leaving out "data" scripts on 6 Nov
2026) loads in well under a second. Ink save state: `inkSaveVersion` 10 with multi-flow.

**Story data in the project.** `python3 Scripts/sync_story.py` copies `out/json/dink.json`,
`names.csv` and `director_vocabulary.csv` from the data repo into `Content/Dink/Data/Story/`
(staged as plain files by `DirectoriesToAlwaysStageAsUFS=Dink/Data`, like the facts CSV), writes
`story_manifest.json`, and fails if the JSON is not ink v21, a knot of `names.csv` is missing, or a
`CONST fix_*` switch in `out/ink` is not `false`. `--rebuild` runs the converter first; if any
`out/ink/*.ink` is newer than `out/json/dink.json` it recompiles with inklecate into a temp dir
(it never writes the data repo except through the converter). Unchanged input = byte-identical
output ("no change"; verified with `--rebuild`). Run it whenever the converter output changes,
then `Scripts/test.sh Dink.Narrative`.

**Classes** (`Plugins/DinkNarrative/Source/DinkNarrative`):

| File | What |
|---|---|
| `DinkNarrativeTypes.h` | `FDinkStoryLine` (one output line, classified by its tags: Spoken / Command / Title / Text; tags parsed), `FDinkStoryChoice`, `DinkNarrative::ToDisplayText` (the U+00A0 -> space rule), command-arg splitting, knot/entry naming, the original font colour table, text duration |
| `DinkInkStory.h` | `FDinkInkStory`: wrapper over `Ink::FStory`; loads JSON + `names.csv` (`FDinkStoryNames`: fact <-> VAR, script locals, 930 entry points); flows, int VARs, choices, externals (`lookaheadSafe = false`), runtime errors |
| `DinkStorySubsystem.h` | `UDinkStorySubsystem` (GameInstance, tickable): the one story; script instances; stepping; menus; texts; fact mirroring; save/load; screen-entry `main`s; talk; smoke run; HUD drawing |
| `DinkDirector.h` | `UDinkDirector`: command registry (every vocabulary command), sprite handle table, the 30 EXTERNALs, movement, fades, audio stub, status table |
| `DinkGameplay.h` | `UDinkGameplay` + `FDinkGameplayData`: the engine's hit/touch/push/talk/damage/death/status/item rules and the seeded rand() source (see "Gameplay rules"); `FDinkHardnessMap`, `FDinkAdaptationSettings`; the brains' API |
| `Private/DinkBrains.cpp` | the brains (`ThinkSprite`, brains 0-17), movement against hardness, the animator, screenlock, the adaptation layer (see "Brains, locked fights and the 3D adaptation layer") |
| `DinkScriptSpriteComponent.h` | `UDinkScriptSpriteComponent` (sp_* data on the actor for the future animation/AI layers), `ADinkScriptSpriteActor` (create_sprite marker) |
| `Private/DinkNarrativePresentation.cpp` | floating text, menu and fade drawn on the HUD canvas (`AHUD::OnHUDPostRender`); `FDinkNarrativeInputProcessor` (Slate pre-processor: E talk/skip, Space/Enter skip/pick, Up/Down/W/S, 1-9, F/Left Ctrl attack, Q cast) |
| `Private/DinkNarrativeConsole.cpp` | console commands and `RunSmoke` |

**Script instances = Ink flows.** One `Ink::FStory` holds the game; every DinkC script instance
(the engine's `rinfo[]` entry: a script attached to a sprite) runs in its own named flow `i<id>`.
Why flows rather than one story object per instance: DinkC globals are shared by all scripts, and
one story means one variable store, so there is nothing to keep in sync between instances; each
flow has its own call stack, output and choices; the ink state JSON serialises all flows in one
blob, so save/load is one string. `StartProcedure(script, proc, sprite)` reuses the instance of that
script on that sprite (its locals survive: `main` sets, `talk` reads) and `ChoosePathString` with a
reset call stack abandons whatever it was doing, which is what `run_script` does; `external()`
and `spawn()` make new instances. Script locals (`VAR <script>__x`, global in Ink) and the
pseudo-variables (`current_sprite`, `current_script`, `arg1..9`, `v_return`) are copied into the
story before an instance steps and back out after (`SwapIn`/`SwapOut`), so two instances of one
script never see each other's locals. An instance lives on after its procedure returns (state
Idle) until `kill_this_task`, its sprite is removed, or a screen change (all but
`script_attach(1000)` instances end, as `kill_all_scripts` does).

**Stepping and blocking.** Each tick the subsystem advances game time (ms), moves sprites, expires
texts, fires `set_callback_random` timers into idle instances, then steps every Running instance
until it blocks, ends, reaches a menu or has run `MaxLinesPerStep` (5000) lines. A command line
goes to the director, which returns "continue", "end the script" or a block (time, a text, a moving
sprite, a child instance, one frame, the skip key); a blocked instance is skipped until the block
clears; nothing else waits. Spoken lines: `say`/`say_xy` show a text and continue; `say_stop*` wait
until the text times out (strlen x 77 ms, at least 2700 ms, dink.h) or the player skips; speaker 0
shows nothing and does not wait (the engine's "Sprite 0 can talk?"); `say_stop` first clears the
texts of the speaker and of Dink, `say` those of the speaker (dink.cpp D:7742-7930). Menus: the
choices after `choice_start` become `FDinkMenu` (title lines from `#title`); `Choose(i)` answers.
`bInstantMode` (tests, smoke run) completes every block at once and answers menus with
`AutoChooser`; `RunUntilIdle` steps until nothing can progress.

**Clock.** The story subsystem ticks inside its game world (`GetTickableGameObjectWorld` returns the world), so the
story clock is the world's time: the delta `UWorld::Tick` hands out (clamped by WorldSettings to 1/8 s at most, so a 1 s
editor hitch is 0.125 s of game time), times the time dilation (`slomo`), and nothing while the world is paused. It used
to be a world-less tickable: the editor ticked it with the raw frame delta (hitches of 175-260 ms seen in the probe's
real-time runs, `slomo` ignored). Without a world (headless tests) the engine ticks it with its own delta. A script
instance that survives a screen change (attached to 1000: an armed item's script, `dinfo`) is moved to the new screen
(`OnScreenEntered`), as the engine has one current map; before, `create_sprite` from a spell armed on another screen
put the missile on that screen, where no brain thinks for it. `PlayerAttack`, `PlayerCastMagic` and the talk key copy
the pawn's facing into Dink's `dir` first (`SyncDinkFacingFromActor`): item-fb.c reads `sp_dir(1, -1)`, which a cutscene
(s2-auntp: `sp_dir(1, 1)`) had left diagonal.

**Sprite handles.** `UDinkDirector` keeps `handle -> FDinkSprite` {actor (weak, may be none),
origin ID, screen, attached script, engine x/y (x includes the 20 px bar), dir, frozen, props,
move state}. 1 is Dink (the first local player's pawn). Placement actors get a handle the first
time a script addresses them (`sp(editor_num)` on the instance's screen, the actor a script runs
for); `create_sprite` and text sprites get the smallest free handle >= 2 (like `add_sprite`).
Sprites without actors are "virtual": every command still works on the record, which is what the
tests and the smoke run use. `sp()` of a placement removed by `editor_type` returns 0. On a screen
change the handles of the old screen are released. Positions go through `DinkLayout` with the
sprite's screen corners (the importer's transform): `move`/`move_stop` walk in numpad directions in
pixel space (speed 60 px/s per `sp_speed` point, ASSUMED) and stop when the x (dirs 4/6/1/3/7/9) or
y (2/8) coordinate passes the stop value, as the engine does; a move already past its stop ends at
once; a move that never arrives is ended after 30 s. Generated placeholders are Static; the
director makes an actor Movable at run time when a script moves it.

**Facts.** The fact store is the one source of truth. `UDinkStorySubsystem` pushes every fact
into its Ink VAR on load, reset and restore, and on every fact change; Ink's variable-changed event
writes story assignments back to the facts (with a guard against echo). `UDinkStatsComponent`
(bMirrorToFacts, on the greybox character) now mirrors both ways, so `~ gold = gold - 100` reaches
the player's stats, and pulls stats from the facts on reset/restore. `vision` changes call the
greybox's `SetScreenVision` for the current screen. After a load, facts are pushed into Ink again,
so a stale Ink value can never win (tested: every fact == its VAR after load).

**Save/load.** `UDinkSaveGame` v2 has `SubsystemState`; the story subsystem stores
`"narrative"` = JSON {Ink state with all flows, instances (vars, block, parent, callback, menu
titles), texts on screen with expiry, the open menu, the handle table with props, fade, music,
game time}. `UDinkSaveSubsystem` calls the story subsystem through its new
`OnSnapshotCaptured`/`OnSnapshotApplied` delegates. Actors are re-bound by origin ID after load.

**Screens and talking (play).** When the greybox's current screen changes, the subsystem sets
`&player_map`, sets `&vision` 0, ends the old screen's scripts, runs the screen volume's base
script `main` (one step, so it can set `&vision`), hides placements whose override removes them,
then makes every live (map.dat type 1) placement of the current vision a sprite with map.dat's
fields and runs its script's `main`, in placement order (see "Gameplay rules"); headless, without a
world, the same placements become virtual sprites and the base script comes from
`Gameplay/screens.csv`. `dink.ScreenScripts 0` turns this off. On a new game (no save loaded)
newgame.c `main` runs first (fists, armed), then the mother's opening scene plays on SCR_001. The
talk key (E) runs `talk` of the first sprite the original's rule finds (hardbox + 10 px, + 50 px in
Dink's facing direction, run_through_tag_list_talk), else of the nearest visible scripted actor
within 3.5 m in front of the player, unless Dink is frozen or a menu is open. Remaster rule: a screen change that ends every script unfreezes Dink (a warp or `dink.Goto`
can leave a screen mid-cutscene; the original cannot).

**Director command status** (`Plugins/DinkNarrative/Docs/director_status.csv`, regenerated by the
test `Dink.Narrative.Director.Vocabulary`, which fails when the committed copy is stale and prints
the `cp` command): 146 vocabulary rows, **111 implemented, 35 recorded, 0 not done** (7 Nov 2026, after the
brains: newly implemented `sp_brain`, `sp_seq`, `sp_pseq`, `sp_pframe`, `sp_frame`, `sp_frame_delay`, `sp_timing`,
`sp_base_walk`, `sp_base_attack`, `sp_target`, `sp_follow`, `sp_distance`, `sp_attack_wait`, `sp_flying`, `screenlock`;
before that 96/50 on 6 Nov 2026,
after the gameplay layer; it was 134 rows, 82/52: newly implemented `random`,
`get_rand_sprite_with_this_brain`, `is_script_attached`, `kill_shadow`, `run_script_by_number`,
`sp_mx`/`sp_my` (placeholder missile flight), `sp_nohit`, `sp_notouch`, `sp_exp`, `sp_range`,
`sp_brain_parm`/`sp_brain_parm2`, the `=magic_cost` write; new recorded rows `set_dink_speed`,
`sp_attack_hit_sound(_speed)`, `make_global_int`; `hurt`, `add_item`, `add_magic`, `kill_cur_item`,
`kill_this_item`, `arm_weapon` and `add_exp` now run the item scripts and the engine's rules, see
"Gameplay rules"; `sp_brain` and `sp_seq` stay "recorded" because their main job, AI and 2D
animation, is not built, although the gameplay layer acts on some brains and on hit frames). Implemented
includes wait, freeze/unfreeze, move/move_stop, sp_x/y/dir/active/speed/hitpoints/strength/
defense/touch_damage/nodraw/size/kill/script, create_sprite, editor_type/seq/frame (world-state
overrides), kill_this_task, script_attach, external, spawn, set_callback_random, choice_start,
fades, load_screen/draw_screen/force_vision, inventory and exp commands, save_game/load_game,
the audio commands (recorded journal plus approved local playback), the 5 spoken-line forms, the 13 engine-bound fact-write rows and the externals.
Recorded (accepted, stored on the sprite/actor or logged, never an error) are the 2D animation and
AI properties (sp_seq, sp_pseq, sp_pframe, sp_base_*, sp_brain..., init), collision rebuilds,
screenlock (flag only), status bar, title/escape-menu modes, show_bmp/show_popup, kill_game/
restart_game, and the converter's comment-only no-ops and fix-only misspellings. An unknown command
is `LogDinkNarrative` Error + skipped. Audio: `FDinkAudioStub` logs `LogDinkAudio: audio cue ...`
and keeps the list. Its optional playback callback feeds `UDinkAudioSubsystem`, which resolves only the approved Audio/approved.json routes, plays screen/script music and positional effects, and scans active `sp_sound` loops. Headless smoke/parity keeps the same cue text and order. `dink.Audio` reports the live selection and playback state.

**Whole-story smoke run** (`Dink.Narrative.Smoke.AllEntryPoints`, also `dink.SmokeRun`; report in
`Saved/Narrative/smoke_report.txt`): every one of the 930 entry points once, on a fresh story
state and fresh facts, commands stubbed, menus answered at random from seed 1997, cap 5000 lines.
Result 6 Nov 2026, after the converter change (data repo b1bf75d + working tree), unchanged on 7 Nov 2026 after
the brains (the smoke run advances no game time, so no brain thinks in it): 930 entry
points, 903 ran to completion, 27 hit the cap, 0 stalled, 0 with runtime errors, 0 unknown commands;
140,407 lines, 17,194 spoken lines, 122,987 commands, 88 menus, about 11 s. (Before: 597 entry
points, 571 complete, 26 capped, 0 errors.) All 27 capped entry points loop through blocking
commands, i.e. they are the original's endless loops (`main`/`talk`/`hit` of s2-bar, s2-healp,
s2-man2, s2-out, s2-wench, s4-healp, s7-girl, s7-mom: wait loops; s3-freak `main`/`talk` and s3-h1
`main`: a `move_stop` pacing loop; new: fish1 `main`, a swimming loop). Spoken lines not shown
because the speaker was 0: 4,558 (speakers held in globals that a screen's base script sets, which
an isolated entry-point run never ran). Targets the story calls but does not contain: only
`external ranstuff.small` (called by the dead s1-slim; the original has no ranstuff.c, so nothing
drops; the test fails on any other). `sp_script` of a script without `main` (dam-bomn) is the
engine's normal "attach, nothing to run" and no longer counted. Pitfall: InkPlusPlus logs some
story errors itself (`LogInkPlusPlus` Error); the smoke run captures that category into its report.

**Tests** (`Dink.Narrative.*`, 15): story loads (v21, 377 knots, 930 entries, 30 externals, every
fact has its VAR with the same initial value); every `d_*` knot, `on_*` and `p_*` stitch resolves;
mother (`s1-h1-m` talk), farmer SmileStein (`s1-h3-of` talk, nested menu writes
`&farmer_quest = 1`) and the toll bridge (`s1-brg2` talk: titled menu, `&gold -= 100` reaches facts
and stats, `&story = 7`, `kill_this_task`, the too-poor branch) with verbatim text and options,
checked against the original `.c` files when the data repo is beside the project; facts <-> Ink
both ways and after reset; blocking vs non-blocking order in game time, two instances at once,
skip; the U+00A0 rule on a real line; save/load mid-menu into fresh subsystems, then the
conversation continues; unknown command; vocabulary/status table; sprites, moves, editor_type,
sp(), audio stub; the smoke run; and in PIE on the generated Stonebrook map (skipped with a
warning if not generated): the new-game scene, Dink frozen and released, `sp_x` lands where the
screen volume maps it, the talk key opens her menu, `dink.Fact`/`dink.Say`/`dink.Run`; `Clock.FollowsWorldTime`:
one world tick of 100 ms moves the story clock 100 ms, `slomo 4` makes it 400, a paused world stops it.

## Gameplay rules (UDinkGameplay, built 6 Nov 2026)

`Plugins/DinkNarrative/Source/DinkNarrative/{Public,Private}/DinkGameplay.*`: the original engine's
rules that decide WHEN a script procedure runs, ported from `source/dink/dink.cpp` (line numbers
"D:n" in the comments) onto the director's sprite records. They work in the original's pixel space
(engine x includes the 20 px bar), so greybox actors (their position synced every tick) and virtual
sprites in headless tests behave the same. Owned by `UDinkStorySubsystem` (`GetGameplay()`); ticked
in `Advance` before scripts step.

**Data** (`python3 Scripts/sync_gameplay_data.py`, < 1 s, from the data repo's `tools/dinkex/out`;
idempotent, `--check`; writes `Content/Dink/Data/Gameplay/`): `frames.csv` (3,190 frames of dink.ini:
delay, the "special" hit flag, the picture's hardbox), `placements.csv` (all 5,846 map.dat
placements: type, engine x/y, seq/frame, vision, brain, script, hitpoints, strength, defense, exp,
nohit, touch_damage, speed, timing, base_*), `screens.csv` (base script per screen),
`gameplay_manifest.json`. `FDinkGameplayData` loads them. When a placement gets a sprite handle,
`InitPlacementSprite` copies map.dat's fields onto it (place_sprites_game).

| Trigger | Rule (source) | Here |
|---|---|---|
| screen load | only type-1 (live) placements of the current vision become sprites with scripts; removed ones (editor_type 1, or 6/7/8 not due) do not (place_sprites_game D:6040-6140) | `EnterScreenPlacements`: every live placement gets a handle (actor or virtual) and its `main` runs; the base script comes from the screen volume or `screens.csv` (headless) |
| hit | when a sprite's animation reaches a frame flagged special (D:16971): every active sprite except nohit-without-script whose hardbox +5/+5/+5/+10 (plus 28 px, or sp_range, towards the attacker's dir; 36 / range+range/6 up and down) holds the attacker; `&missle_source`, then damage `hurt_thing(strength/2 + rand()%((strength+1)/2) + 1)` if the target has hitpoints (or is Dink), last_hit, target, `&enemy_sprite`, `hit` (run_through_tag_list D:15460-15596) | `OnSequenceSet` (from `sp_seq`) schedules `RunThroughTagList` at the frame's time from `frames.csv` (fists/sword: 175 ms); `PlayerAttack` = the attack key: the armed item's `use` (D:14819) |
| touch | Dink's brain, every frame: sprites with touch_damage != 0 whose hardbox +2 px holds Dink; -1 runs `touch` only (again every frame until the script clears it); > 0: 400 ms notouch, last_hit, `touch`, hurt_thing on Dink; while Dink is notouch a damaging sprite ends the whole list (D:15629-15680) | `RunThroughTouchDamageList(1)` every tick |
| push | walking into hardness (not low) in a cardinal direction, push_active, after 600 ms `push` of scripted sprites whose hardbox +2 holds Dink (D:13526, 14768, 15600) | `UpdatePush` (PIE: movement input but < 30 cm/s speed); the walking direction becomes Dink's dir |
| talk | first sprite whose hardbox +10, plus 50 px (35 up/down) in Dink's dir, holds him and whose script has `talk` (run_through_tag_list_talk D:14171) | `FindTalkTarget`, then the old 3.5 m search as a greybox fallback |
| damage / die | hurt_thing adds `damage` (D:6656); the target's brain applies it next think: pill 9 / dragon 10 / people 16: hitpoints, at < 1 `die`, then (brain unchanged) add_kill_sprite = corpse + add_exp + gone (D:12887, 13234, 13087, 12359); duck 3: any damage, add_exp, `die`, headless; again: `duckdie`, gone (D:12723); pig 4: hitpoints, add_exp, `die`, corpse (D:13370); others never apply damage; Dink: &life -= damage (D:14697) | `ProcessDamage` every tick; `hurt` command; add_exp pays only if last_hit == 1 (D:615); corpses are not shown |
| status | every 100 ms while `&update_status` is 1 (D:17346, D:5836): spell charge (+&magic up to &magic_cost), level-up when exp reaches next_raise (exp -= it, `lraise` `raise`), `dinfo` `die` when life < 1 | `StatusTick`; the original's exp counter lags 10/tick and pauses while Dink is frozen or talking: here the threshold is checked directly, also paused while frozen or a menu is open |
| items | add_item/add_magic: slot + `pickup` in a new instance (D:6915); arm_weapon/arm_magic: old `disarm`, new `arm` (D:7850); kill_cur_item: `disarm`, `holdingdrop`, `drop`, the caller leaves (D:1480, 7801); kill_this_item (D:1505) | `AddItem`, `ArmWeapon`, `ArmMagic`, `KillCurItem`, `KillThisItem`; `ArmItemSlot`/`ArmMagicSlot` are the inventory screen's stand-in; item scripts run attached to 1000 |
| magic key | the armed spell's `use` when magic_level >= magic_cost (D:14941) | `PlayerCastMagic` |
| brain 12 | scale to brain_parm then gone, 5 size points per think (5 * base_timing / 4, base_timing 7, D:15798) | `ScaleBrain` in DinkBrains.cpp: a pickup with timing 0 shrinks for 18-19 frames (~0.3 s), then is gone. (The first port used mbase_timing 135, i.e. 165 per think, and removed pickups after two ticks: wrong.) |
| brains 11/17 | missile: flight, hardness, sprite tests, `damage` / `hit` (D:14240-14420) | `MissileBrain`, see "Brains, locked fights and the 3D adaptation layer" |
| brains 0-16 | the sprite's brain every frame (D:16858) | `ThinkSprite`, see that section |
| screenlock | Dink cannot leave the screen (D:10083, 14049) | `SetScreenLock`; greybox barriers; see that section |
| new game | newgame.c `main` (start-1.c's click does the same): fists added and armed | `StartNewGame`, run before the first screen's scripts when no save was loaded |
| random | DinkC `random(range, base)` = rand() % range + base, base for range 0 | the `random` EXTERNAL; `FDinkStreamRandomSource` seeded (`SetRandomSeed`, `dink.Seed`, `StorySeed` on reset); tests inject `FDinkScriptedRandomSource`; combat rolls and callback timers draw from the same source in call order |

Keys (Slate pre-processor): **F / Left Ctrl** attack (the original's Ctrl), **Q** cast
(Shift), **E** talk. Console: `dink.Attack`, `dink.Magic`, `dink.Arm <slot|item>`,
`dink.ArmMagic <slot|spell>`, `dink.Inventory`, `dink.Seed <n>`.

**What is a placeholder:** nothing is drawn of any animation (the frame stepper runs and lands hits, the
cards do not change; corpses are not spawned); missiles look like the create_sprite marker cylinder;
spell effects are whatever the spell script does with sprites; enemies and townsfolk are flat cards
that slide in the original's pixel steps; the wind-up telegraph is a debug sphere; lock barriers are grey
engine cubes. Blood, damage numbers, the exp counter animation and sounds are not shown (sound
cues go to the audio stub). The touch/push/talk boxes get the capsule radius in pixels added in 3D.

**Tests** (`Dink.Gameplay.*`, headless with virtual placements unless noted): furniture `hit`
lines in Ethel's and SmileStein's houses (facing away / out of reach: nothing); a pillbug dies in 3-4
fist hits, pays 5 exp, sets editor_type 6, and over 300 seeded kills drops a small heart 97 times
(1/3 expected) and nothing else; emake.medium over 2000 seeded runs (116/104/100/1680 for 1/20, 1/20,
1/20, 17/20; never food type 4); `random()` rules; mgold +15 and heart full heal by touch, once,
then gone; pillbug touch damage with 400 ms immunity and the defense pity point; editor_type 1
stays across re-entry and save/load, 6/7/8 return exactly after 300/180/60 s from the last exit;
sword pickup and arm (+4 strength, reach 40), disarm; fireball arm/cast/recharge in ceil(100/magic)
status steps (magic 1, 3, 7); level-up menu and dinfo once; Ethel's duck quest end to end and the
duck's death lines; pig feeding end to end (sack, feed, bully, mother's option); pushing the rock
`s1-roc`; eating a nut (`kill_cur_item`); `Magic.CastFacesThePawn` (the cast flies where the pawn faces, whatever
dir a script left); `Magic.SpellFliesOnTheCurrentScreen` (a spell armed on SCR_038 and cast on SCR_579 makes its
missile on 579 and the missile moves; failed before the `OnScreenEntered` fix); `Probe.Repeatable` (PIE: steps 1-28 of
chapter 1 in two sessions of one editor, event traces identical line by line; fails in about 160 s without the fixed step) and
`Probe.RepeatableChapter` (chapter 2 twice from chapter 1's save slot: loading a save and a five-chaser fight, identical traces).

**The probe, in chapters** (`Dink.Gameplay.Probe.Ch1Stonebrook` .. `Ch9Windemere`, `ChAJoppa`, PIE on `L_Greybox_World`, `Ch1` also on
`L_Greybox_Stonebrook` up to step 22; reports `Saved/Narrative/probe_chN.txt` (`stonebrook_probe.txt` for chapter 1), every event
of the run in game time in `probe_chN_trace.txt` (`stonebrook_probe_trace.txt`), the trace md5 in the report's first line). It
plays the game as `Docs/probe_route.md` describes it, using only teleports (for walking), `TryTalk`, `PlayerAttack` (one punch
per 450 ms of game time), `PlayerCastMagic`, standing on things, `ArmItemSlot`/`ArmMagicSlot` and skipping text, with the
adaptation layer off; no fact, stat or item is ever written. **Chapters are tests that start from the save slot the previous
test wrote** (`Saved/SaveGames/probe_ch<N>.sav`, written when the chapter reached its floor; a chapter that falls short deletes
its slot, so the next one fails with "run chapter N first"). The automation runner sorts by path, which is why the tests are
named `Ch1..Ch9`, then `ChAJoppa` for chapter 10 (no `Ch10`: `Ch10` would sort before `Ch2`; chapter 11 will be `ChB...`, and see pitfall 60); `Probe.Repeatable` and `Probe.RepeatableChapter` sort after them. Each chapter's report says how many steps it
completed; the floor in the test (second to last argument of `RunChapterTest`) makes a regression fail.

| Chapter | Steps (floor) | Wall | Game (trace md5) | What it plays |
|---|---|---|---|---|
| 1 `Ch1Stonebrook` | 47 of 47 | 39 s | 231 s (b3760d52d7) | new game, the pig, Ethel's duck, the nut, the fire, the letter (&story 6); Martridge's trial (cave Bonca with fists at 54 px, scroll: fireball); the toll (&story 7); Terris: Maria, Jack (fireballs, kited; `KiteAndCast`), the prisoner's cave, the bar, the teacher, three magic potions, Acid Rain, the idol, the cult's ambush; ends on SCR_625 (`s2-cave2`'s scripted warp) |
| 2 `Ch2Terris` | 6 of 6 | 25-32 s | 377 s (253e6f7268) | Nadine twice (&s2-nad 2), the cult of the Dead Dragon Carcass on SCR_238 (menu "Say something to the effect that you are going to save her"), four girls and Bishop Nelson killed with `KiteFight` (no damage taken), Mary's talk and the scripted walk home (&story 8) |
| 3 `Ch3Roads` | 11 of 11 | 9 s | 430 s (e9fce770bc) | gold heart on the road (SCR_524, lifemax +10), three `papgold` chests (+600 gold; SCR_005, 557, 747), four strength potions (SCR_681, strength 8), Christina, the girl in the bookstore street, the Mayor (&mayor 3); gold 724 |
| 4 `Ch4Gold` | 12 of 12 | 28-35 s | 845 s (d431e6780f) | gold for the bow, 724 -> 1072, no damage: the monsters of SCR_583 (Bong, Boncd), SCR_480 (two Bongs, fenced in by low hardness) and SCR_632 (two Bongs) kill each other or are shot over the fence (`Feud`), 5 minutes of waiting in Arturous's shop at 8x time dilation, a second round |
| 5 `Ch5Bow` | 3 of 3 | 1 s | 852 s (6c709d1069) | Arturous (menu "Buy a Bow and some arrows for $1000", gold 72 left), arm `item-b1`, the goblin gate guard on SCR_712 ("Ask the Goblin guard to let you in": armed bow, &mayor 3: **&gobpass 1**, `compare_weapon` and `free_items` verified) |
| 6 `Ch6Goblins` | 3 of 3 | 2 s | 864 s (9e87080221) | the healer in Terris (talk "Get healed", 1 gold per missing life; skipped at full life), goblin S680_P13 (`s3-gh`, 40 hp) pulled by a fireball from the east end of the strip and killed (the others stay peaceful), back out to SCR_712. The other three goblins are chapter 7 (they cannot be kited in that corridor) |
| 7 `Ch7Sanctuary` | 8 of 8 | 31-33 s | 1038 s (d50e5111f6, 2589 events) | goblin S680_P14 (`DuelFight`, 56 s), healer, S680_P11 (43 s), healer, S680_P12 (the last: its death `spawn`s Mog, 23 s), Mog (`DuelFight`, 25 s; his death warps to SCR_489, `&gobpass 5`), the Cast camp (SCR_489, `s3-camp.c`: Dink frozen, the scripted walk, `move(1, 2, 410, 1)` over the south edge to SCR_521 and `fade_down`; SCR_521's `s3-camps.c` `fade_up`, 18 s), the ambush scene to its first blow (dialogue skipped, `screenlock`, three knights with 40 hp each, `&mayor 4`, Dink free at 300,280, 10 s): hands over to chapter 8. Ends with life 26/26, gold 59, exp 800, strength 9 |
| 8 `Ch8Knights` | 3 of 3 | 10-12 s | 1095 s (28406402c0, 1443 events) | the three knights (`SquadFight`, 39 s: Dink takes one blow of 11, deals 43 of the 120 hit points with 28 punches, the knights deal the other 77 to each other; level-up at 900 exp: Defense), their gold (+180: 59 -> 239), the Mayor in Hiram's Bookstore (SCR_067, "Show him the scroll with the plans": `&mayor 5`), the parade on SCR_586 (`s3-tc.c`, 16 s): **`&story 10`**, `&mayor 6`. Ends with life 15/29, gold 239, strength 9, defense 1 |
| 9 `Ch9Windemere` | 6 of 6 | 10-26 s | 1144 s (1db62e4adb, 2323 events) | Pete's bomb (SCR_196, "See what's for sale", "Bomb - $20"), the two all-potion chests of the duck enclosure (SCR_536: strength 11, defense 3, magic 7), the bomb planted by the cracked rock and its explosion: `&s4-duck 1`; **the 27 ducks** (`KiteAndPunch` on the nearest, 38.7 s: 27 `die` and 27 `duckdie`, each `duckdie`'s `external("make", "foodduck")` runs at once, the last one's `spawn("s4-end")` too: **`&s4-duck 2`, `&story 11`**, the scene of Kelly and the guard to its end, Dink free at 147,233). Ends with life 15/29, gold 219, strength 11, defense 3 |
| 10 `ChAJoppa` | 7 of 7 | 6-20 s | 1178 s (c532805f11, 442 events) | the Windemere healer (SCR_195, 14 gold: life 29), the three pickups of route step 32 (SCR_663 `rpotion`: strength +1; SCR_603 `bpotion`: defense +1; SCR_742 chest `box2-sp` and its potion: strength +1), Joppa (SCR_419 by teleport, `s5-jops`: `&s5-jop 1`), the basement scene (SCR_229, `s5-base`, `s5-guy`: 15.2 s, `&s5-jop 2`), back up (SCR_419: `s5-jops` makes the family, `s5-fguy`'s scene 15.1 s, two `en-drag` dragons, `screenlock`): ends where the fight begins. Life 29/29, gold 205, strength 13, defense 4, magic 7, exp 200, level 4. **The stop** (below): the dragons |

**Chapter hashes of 7 Nov 2026, night, after the `external`/`spawn` fix** (final code; the whole probe (`Dink.Gameplay.Probe`, 12 tests) run twice by me, 12/12 and the same ten md5s, ten traces and ten state dumps `cmp`-equal; packaged: the same ten md5s): Ch1 b3760d52d7 (4338 events), Ch2 253e6f7268 (3092), Ch3 e9fce770bc (430), Ch4 d431e6780f (2121), Ch5 6c709d1069 (120), Ch6 9e87080221 (462), Ch7 d50e5111f6 (2589), Ch8 28406402c0 (1443), Ch9 1db62e4adb (2323), Ch10 c532805f11 (442). Before the fix (after the `sp_script` fix): b3760d52d7, a5cfdf70bc, e9fce770bc, cd1b3bf820, 6c709d1069, 9e87080221, 7cc6e2fe93, 6697a02e52, 0ea9677ee2 (344 events: the ducks stopped it). **Chapters 2, 4, 7, 8 and 9 moved; 1, 3, 5 and 6 did not** (the brief expected every hash to move, because every monster `die` runs `external("emake", ...)`. UNVERIFIED guess for the four that did not move: the child's first line runs at the same game time and in the same order as before when nothing else runs between the child's start and its first line in that story step, and the traces do not record anything else; I did not diff the traces to see which interleaving changed in the five that moved.) Every step of every chapter still completes (floors 47, 6, 11, 12, 3, 3, 8, 3, 6, 7) and **no step needed re-tuning**. The `DinkProbeTests.cpp` change for this was one step (the ducks, in Ch9) and a new chapter 10.

**Chapter hashes of 7 Nov 2026, evening, after the `sp_script` fix** (history) (final code; the whole probe run twice by me, then a third time inside another agent's full suite, 133/133,
and once more in the full suite below: the same nine md5s every time): Ch1 b3760d52d7 (4338 events), Ch2 a5cfdf70bc (3092), Ch3 e9fce770bc (430), Ch4 cd1b3bf820 (2121), Ch5 6c709d1069 (120;
unchanged: no `sp_script` runs in it), Ch6 9e87080221 (462), Ch7 7cc6e2fe93 (2589), Ch8 6697a02e52 (1443), Ch9 0ea9677ee2 (344). Before the fix: 50091fcc80, 103b0331f1, e0b643193a,
230f594539, 6c709d1069, 7471375e32, ea73eea592. **All chapters 1-4, 6, 7 changed hash and none of them needed re-tuning**: the event counts are the same as before and every
step completes (the fix runs the mains of `s2-cult`'s girls and Nelson, `dam-fire`, `papgold`, `s2-cbon`, `s3-dorks`... at once, which reorders `idle` lines and `rand()` draws
in the traces but not the fights tuned to them). The old trial (pitfall 53: Ch3 stopped at step 1 of 11, Ch6 at 1 of 3) did not honour `no_running_main`; this fix does (the
base script of a screen runs its first segment with `UDinkStorySubsystem::bNoRunningMain`, so a `sp_script` there still starts the main later, as `init_scripts` does). That is
the likely difference; it was not re-run without the guard to prove it.

**Determinism of the chapters** (7 Nov 2026): the whole probe (`Dink.Gameplay.Probe`) three times in a row on the final code (the third inside
the full suite, `Scripts/test.sh`): the six trace md5s above were identical in all three runs (4338, 3092, 430, 2121, 120 and 440 events), and
`RepeatableChapter` plays chapter 2 twice from the slot in two PIE sessions with identical traces. Every chapter's load compared with the
previous chapter's end: 0 of 122-152 state lines differ. The hashes change whenever gameplay code, the probe or an earlier chapter changes
(pitfall 33; this session's text-handle fix, pitfall 42, moved all of them): quote them with the tree they come from.

**Where the probe stops, and why** (7 Nov 2026, night, after the `external`/`spawn` fix): route Act D step 36, the two dragons of Joppa (SCR_419, `en-drag.c`, `s5-fguy.c`, `s5-end.c`; `&story 11 -> 12`). Played since the ducks' stop: step 31 the 27 ducks (Ch9 step 6; with `external`/`spawn` at once the last `duckdie` reaches `spawn("s4-end")`: `&s4-duck 2`, `&story 11`, the scene to its end), 28 the Windemere healer, 32 the three pickups, 33 Joppa, 34 the basement scene, 35 the return, the family, the two dragons (all Ch10). **The stop is a kit, not an engine gap**, and it is a measured one: from Ch10's slot (strength 13, defense 4, magic 7, life 29, gold 205, fists) a throw-away chapter that only punched the nearer dragon (`KiteAndPunch` from 44 px, later removed from the file) had Dink dead after 1.4 s and the family dead after 12-26 s (father 100 hp, mother and Gwen 50; any death sets `&life` 0, `s5-fguy.c:95-103` and the other two). The first punch makes the dragon target Dink (`en-drag.c:99-104`, `hit`) and its `attack_wait` has long passed, so its `attack` casts `hurt(Dink, 20)` at once: 20 - defense 4 = 16 (`resist` only when `random(40,1) <= magic`: 7 of 40), twice in the first second; the punches did 4, 1, 3 net of defense 8; `attack_wait` is then `random(5000,3000)`. The dragons need no approach (they cast from where they stand: `DragonBrain`, `dink.cpp:13234`) and touch only for 10, so this is a race: 160 hp at about 8 net damage a second (`Docs/probe_route.md` 2.5, 2.6, step 36: melee strength 20+, P(family lives) 94% at 5 s/10 s, 59% at 10/20, 18% at 15/30, 0 beyond 25/50). The route's plan is strength 14 from pickups + 3 level-ups on Attack + the 400-gold longsword armed (+4, `item-sw1.c:44`) = 20+; this run put all three level-ups into Defense (Ch7 and Ch8 answer "Increase Defense"), so strength is 13 and the sword would make 17, and gold is 205 (Pete's "Longsword - $400"; one Feud round of Ch4, about 200 gold, would pay it). Next: re-spend the level-ups (a change in Ch7/Ch8 that moves their hashes and re-tunes `DuelFight`/`SquadFight`, which were tuned with the defense) or accept strength 17 and a 30% chance, retrying from the slot with a different frame count (the run is deterministic: another start frame draws other numbers); a chapter 11 `ChB...` with the gold round, the sword and the dragons; heal in Windemere first. `// NEXT (design-level stop, 7 Nov 2026 night)` at the end of `BuildChapter10`. Beyond it: Acts E-G (castle, Edge of the World, the Darklands, Seth, the ending; Seth needs 6,500 gold and 25,500 exp: its own long test); `activate_bow` is still not usable (no hold-the-key action). The route has no "altar scene" or "bridge" between the ducks and Joppa: after step 31 comes the optional step 32 (pickups) and the walk to Joppa (the tunnel; the probe teleports).

*Why (all numbers from the traces).* The remake's knights have **100 hit points, not 40**: `s3-camps.c` sets 40 after `sp_script(.., "s3-dorks")`,
whose `main` sets 100, and the original runs that main at once (`dink.cpp:8164-8171`: `locate` + `run_script`), so the original's knights keep 40.
`DinkDirector.cpp`'s `sp_script` only starts main (`StartProcedure`, no `RunNow`), so it runs after the caller (the trace shows `sp_hitpoints 3 40`
and then, from instance 339, `sp_hitpoints 3 100`). Pitfall 53: fixing that moves every chapter's hash. The knights: defense 6, strength 12 (blows
7-12 against Dink's defense 0 and 26 life, touch 5 every 0.4 s), speed 1 timing 0 (60 px/s, 85 px/s on a diagonal), `attack_wait` `random(4000)`;
a fireball does 2-3 net. 3 x 100 hp is about 130 hits, 2.3 s of charge each, with no healer (screenlock). Tried: (1) `KiteFight` as the cult plays
it: Dink backs into a corner and the three arrive together (three blows in 150 ms, dead at 25-90 s); (2) `OrbitFight` (kept in the probe, unused): Dink
runs an ellipse at 180 px/s and fires along any row or column through a chaser. Three chasers steering at where he is stay about 0.7 x the track's
half-height behind (simulated 105-135 px, measured 90-105 px: 17-30 px from a blow's reach), so every cast (0.25 s still) puts him in reach, and a
row or column through a chaser comes up only every 3-5 s: 7-45 casts (all hit) before he died at 70-130 s, against 130 needed. The knights' blows
hit each other too (the melee rule hits every sprite in the box): with a dead Dink standing still they killed each other in 80-240 s, which no
living Dink can steer. What is missing, in order of cost: the original's 40 hp (pitfall 53); elixirs (25 gold, `s2-healp.c:68`) bought beforehand and
drunk in the fight (Dink has 59 gold); strength 34 for toe to toe (probe_route.md 2.5). The bow is still not usable (no hold-the-key action for
`activate_bow`; arrows do 5 at strength 9). Still UNVERIFIED: the ambush itself, the Mayor's scroll and the parade (`&story 10`), `activate_bow`.
`// NEXT (design-level stop, 7 Nov 2026)` in `BuildChapter7`.

*Chapter 4, the gold* (`Feud` in `BuildChapter4`): 276 gold were missing at the end of chapter 3 (724). The old plan kited SCR_583's Bong and
Boncd and got Dink killed. They do not need to be fought: `en-bong.c` and `en-boncd.c` `main` target `get_sprite_with_this_brain(9)`, the other
monster of the screen, so a pair fights itself from the first second (the Bong's blows of 6-10 on a 20-hp Boncd; two Bongs 10 and 10), nobody
hunts Dink until he hits one (`hit` re-targets the attacker, `sp_target(&current_sprite, &enemy_sprite)`), and a monster killed by another still
runs its `die` and drops its loot (`en-bong.c:89`, `emake large`: 50-74 gold). The Bong walks speed 2 timing 0: 120 px/s straight, 170 px/s on a
diagonal (`changedir` D:5640 gives a diagonal step the full speed on both axes), as fast as Dink: it cannot be kited, so the step keeps away
(`KiteFight` with `bNoStrike`, 170 px standoff) while two are alive, shoots a lone survivor only when one fireball kills it (hp <= 6; the
first hit makes it hunt him), and walks to the loot (or, after 10 s of the survivor wandering by it, straight to it). SCR_480's two Bongs
live in a pen of low hardness (a separate walk component: `bWalkReach`): Dink stands outside and shoots them across the fence, they cannot
come out (the ones he kills pay their exp). Five minutes later (`editor_type 6`) they are back; the wait is 302 s at `UGameplayStatics::SetGlobalTimeDilation`
8 (the story clock follows the world's, the respawn clock counts it: 8 s of wall time), in Arturous's shop (SCR_097, at 300,230: 299,328 is
inside the door's warp trigger). Round 1 gives 13 + 61 + 65 + 67 gold, round 2 14 + 58 + 70: gold 1072, life never below 13.

*`KiteFight` options* (`FFightOpts`; the defaults are the cult's behaviour exactly): `bNoStrike`, `StandDist`, `Pull` (a peaceful sprite he
strikes first: a goblin, Jack), `bWanderers` (peaceful brain-16 sprites with touch damage are threats to keep away from), `PaceFactor` (1.42
for diagonals), `FireLeadSec`, `MinEdge`, `StrikeMaxHp`, `WanderDist`, `PaceMarginSec`, `bFlee` (with nothing safe by the clock, run to the
reachable cell with the most room instead of standing in the corner: chapter 2's cult fight died of that standing once the fixed text-handle
bug stopped hiding sprites), `bArena`, `OpenWeight` (prefer cells with a free neighbourhood: `OpennessMap`), `bGoto`/`bForceGoto`, `bWalkReach`.
`KiteAndCast` (Jack) got the same openness rule: strike only from cells with at least 40% free neighbourhood, and the same flee fallback.

*`DuelFight`* (`FDuelOpts`, `FCtx::DuelFight(handle, opts)`): the melee tactic of chapter 7 (goblins, Mog). Each frame it reads the monster's attack state
(`seq`/`frame`/`base_attack`, `attack_wait`): the blow lands where Dink stands when the animation reaches its special frame (`ReachBox` is
`run_through_tag_list`'s box, `dink.cpp:15460-15540`, widened along the attacker's dir by its `range`), the monster stands still meanwhile, and an
attack starts only inside `sp_distance` once `attack_wait` has passed. It then (1) fires a charged fireball along a clear row or column while the monster is
farther than `CastFrom` (90 px); (2) dodges the blow under way by the shortest walk out of its box; (3) otherwise walks to the cheapest cell, over the 6 px grid,
where the fist's reach box (from the monster's picture, 0.175 s after the swing starts, Dink locked 0.4 s) hits and the expected blow does not, or cannot
start yet (`attack_wait` more than `GateMs` ahead: a punch + the step out + 60 ms must fit before the blow), never through the touch box of the monster
or of any other sprite with `touch_damage` (the goblins still walking about, run at 1.42 x their pace for a diagonal), and never from a cell whose punch would also
reach a peaceful sprite (it turns hostile); (4) with nothing to hit from, waits 60 px (Chebyshev) from it. `AvoidX/Y/R` keeps Dink away from a point (Mog appears at
317,301 when the last goblin dies and Dink stands frozen for his scene). A peaceful target is pulled first by a fireball (`bPull`). `OrbitFight`
(`FOrbitOpts`) is the three-chaser variant that did not work (see "Where the probe stops").

**Save slots between chapters** are also the test of the save system. Each chapter ends with `UDinkSaveSubsystem::SaveToSlot` and
a state dump (`probe_chN_state.txt`: screen, pawn, all 63 facts, stats, both inventories and what is armed, every override, the
world clock and exit times, every live script instance); the next chapter loads the slot and compares the same dump taken before
a frame runs: **0 of 122-142 lines differ** (facts, overrides, stats, inventory, armed items, position, story instances, the
generator state travels in the story state, so the fight after a load continues the same random stream). Found and fixed by
this: after `ApplySnapshot` the greybox still named the screen the pawn had left for up to 0.25 s, so the story "entered" it
(mother's scene on SCR_001, exit times) and then the saved one (`UDinkGreyboxSubsystem::RefreshCurrentScreen`, called by
`UDinkStorySubsystem::RestoreFromSave`).

*`KiteFight`* (`DinkProbe/Private/DinkProbeTests.cpp`): the multi-chaser fight of chapters 2, 4 and 6 (`KiteAndCast` is still Jack's, `KiteAndPunch` the
Bonca's). Every frame: chasers = brain 9/10 with hitpoints; each has a touch clearance (capsule + 6 px) and an attack distance
(max(sp_distance, 47 + range - 28) + 4, +10 more for anything but the one being struck); Dink walks at 180 px/s over a 6 px grid
and only to cells he reaches before every chaser could (arrival slack 0.15 s). Goals, nearest chaser as the target: a charged
fireball line (clear of every other sprite, 40-260 px) or 54-60 px level with it for a punch, both only where there is 50 px of
room to the nearest wall (the chaser rushes him after a hit); else the safe cell on a 130 px ring round them with room to run
(the farthest cell from a crowd is always a corner, and the crowd follows him in: cornered, he died). Friends (Mary, Nelson before
he turns) are never in the line of fire or the fist's reach, and a sprite running a "future hostile" script (Nelson's `s2-cman`) is
kept out of reach once only one girl is left, because he turns where he stands and holds Dink for the whole scene (the first
version took 9 damage from his first blow at 30 px). Girls hit each other (the melee rule hits every sprite in range): two died
of each other's blows in one run.

*Determinism.* The editor runs a fixed 60 Hz step (`FApp::SetUseFixedTimeStep`, restored at the end) and every probe
timing (timeouts, retries, punches, walking) is game time. Under the real-time step runs differ (checked: three real-time
runs gave three different traces, first parting at the Bonca fight, and differing from a fixed-step run at the
`findduck` roll at 12 s): frame lengths of 6-260 ms change on which frame waits end and brains think, so the one shared
`rand()` stream is drawn in another order (monster wander draws vs script `random()`), and everything after differs.
Also removed: a function-level `static` punch timer that outlived the PIE session, the Ink story's unseeded
`FMath::Rand()` seed (now `StorySeed`), wall-clock timeouts. `Probe.Repeatable` guards it.

*Jack (SCR_036).* 50 hp, `hit` makes him a brain-9 chaser (speed 2, touch 10: one touch kills a 10-life Dink). Because
`create_sprite`d chasers have `base_attack` 0 and `pill_brain` treats seq 0 as "still attacking", he walks one animation
cycle and then stands still until something changes his sequence (the next hit does): a faithful port, and why a player
can win by distance. The bookcase strip (engine x 230-270, y 150-290) splits the room, with a gap at y 130-150; a fireball
bursts on it. The probe plays it as a player could: walks at 180 px/s over a 6 px grid of cells at least 10 px from walls
and outside every warp trigger (door, stairs: stepping on one leaves the screen and resets Jack), stays out of Jack's touch
box plus a margin, steps level with him in a row or column with a clear line (no wall, no Maria, no furniture) 40 px
(stalled) or 70 px (walking) past his box, faces him, casts, holds for the cast animation, then walks to the safe cell
farthest from him by his walking distance. 7 casts (5 s apart at magic 2), Dink is never touched. No fact, stat or
Jack number is written.

*What the old "stuck wait" was.* The earlier failure reports (fireball charge frozen at 0-6, `item-fb.use` blocked in
`wait(100)`, Jack never damaged) were not a stuck script: instrumented, `item-fb.use` completed every wait and the charge
cycled 0 -> 100 every 5.0 s. The probe's wall timeout (300 s, later 60 s) is a whole number of casts, so its final
snapshot always caught the last cast in its 100 ms wait. In all 6 traces checked, every `wait` of the run (166-188 per run)
ended within one frame of its deadline (world-less real-time runs: up to 259 ms, one hitching frame). Jack took no damage
because (1) the first cast flew diagonal (stale `sp_dir(1)` = 1 from s2-auntp), and (2) the old tactic stood level with him
on the far side of the bookcase strip, so fireballs burst on it (observed: bursts at x 262-268, or flying past him).

**Tests** (`Dink.AI.*`, 12, headless on real screens' hardness, fixed seeds, adaptation off unless stated): a
pillbug on SCR_278 with Dink as target closes from 150 px to 0, never stands on a hard pixel or leaves its
screen, and wanders diagonally for 2 min; SmileStein (brain 16) walks and sits for 10 min in bounds and stops when
frozen; Ethel's duck (directions 1/3/4/6/7/9, quacks) and a pen pig (diagonals, oinks) for 3 min; a Bonca's hit
lands on its special frame (~350 ms) for exactly strength/2 + rand + 1 - defense, the pity point, no melee
immunity, touch damage once per 400 ms; en-bonc kills an idle new-game Dink in 7.3 s (bound from its numbers 7.7 s);
Dink (strength 4, 10 life, fists) beats the cave Bonca toe to toe with 3 life left while it fights back; missiles
stop at a wall (SCR_013) and fly over low hardness (SCR_014) while a non-flyer is held; screenlock on SCR_302
(two Boncas) and SCR_270 (pillbugs) until the last `die`, sound 43, a screen load clears it; the barrier slabs
block a pawn trace and a projectile trace in a throwaway world; the adaptation layer caps attackers at 2 with
wind-ups (off: 3 at once, none); freeze and a scripted move override the brain; the same seed gives the same fight.

**Respawn clock:** the story subsystem advances `UDinkWorldStateSubsystem`'s game clock in
`Advance`, calls `NotifyScreenExited` for the screen left and `ProcessRespawns` for the screen
entered (fix_dead_sprites), so editor_type 6/7/8 come back 5/3/1 minutes after the player last
left the screen.

## Brains, locked fights and the 3D adaptation layer (built 7 Nov 2026)

`Plugins/DinkNarrative/Source/DinkNarrative/Private/DinkBrains.cpp` (methods of `UDinkGameplay`): the
original engine's brains, ported from `source/dink/dink.cpp` onto the director's sprite records in the
original's screen pixels, so greybox actors (their position follows the sprite) and headless virtual sprites
run the same code. Plain C++, no State Tree (see "Decisions").

**Timing.** The 1997 engine is locked at 60 frames a second (D:17300: `base_timing` 7, so every
`speed * (base_timing / 4)` is just `speed`). `TickBrains` turns game time into whole 60 Hz engine frames
(at most 30 per call; a longer hitch drops the backlog). Each frame `ThinkSprite` (D:16790) runs for every
active sprite of Dink's screen except Dink (the pawn) and texts: the `sp_timing` gate (the brain thinks at most
once per timing ms; `create_sprite` sprites default to 33, map.dat placements to their `timing`), the brain,
the hardness check of the move it made, and the animator. Speed is pixels per think: speed 1 at timing 33 is
30 px/s, at timing 0 60 px/s.

| Brain | Ported from | What it does here |
|---|---|---|
| 0 none | `no_brain` D:13200 | scripted moves (director) and `sp_follow` only |
| 2 bounce | `bounce_brain` D:13616 | flies mx/my, bounces off the screen edges (picture box), no hardness; unused by the shipped data |
| 3 duck | `duck_brain` D:12723 | wanders 1/3/4/6/7/9, quacks (sound 1) and pauses; first hit: `die`, exp, head off, runs on as base 110 (speed 1, every frame); second: `duckdie`, gone (damage half in `ProcessDamage`) |
| 4 pig | `pig_brain` D:13356 | wanders diagonally, oinks (sounds 2-5) and pauses; dies at 0 hp |
| 5 / 7 | `one_time_brain` D:15741, `one_time_brain_for_real` D:15772 | play the sequence once, then gone (5's last frame would be drawn into the background: not drawn) |
| 6 repeat | `repeat_brain` D:15832 | loops its sequence (a placement starts from its map.dat picture) |
| 9 monster | `pill_brain` D:12887 + `process_target` D:12588, `get_distance_and_dir` D:12405 | wanders diagonally (1 in 12 at the end of a walk cycle), turns back near the screen edge, chases `sp_target` (re-aims every 200 ms, wanders in between), attacks with `base_attack`+dir when the target is nearer than `sp_distance` and `sp_attack_wait` has passed, runs the script's `attack` (sounds, the next attack wait) |
| 10 dragon | `dragon_brain` D:13234 | wanders in cardinal directions; with a target runs the script's `attack` whenever `sp_attack_wait` has passed (the dragon's fireballs, Seth's spells are script) |
| 11 / 17 missile | `missile_brain` D:14240, `missile_brain_expire` D:14426 | flies mx/my per think; a wall ends it (`damage` with &missile_target 0, or gone); low hardness 2 lets `sp_flying` missiles pass (every player missile sets it) and holds others at its edge; a placement's hardbox runs that sprite's `hit` and the missile's `damage`; sprites it overlaps (hardbox + range) take missile damage, get 100 ms notouch and run `hit`; 17 ends with its animation |
| 12 scale | `scale_brain` D:15798 | size moves 5 per think towards `brain_parm`, then gone (pickups: 19 frames, about 0.3 s) |
| 15 shadow | `shadow_brain` D:13218 | follows the sprite in `brain_parm`, gone with it |
| 16 people | `people_brain` D:13087, `find_action` D:13046 | sits (faces a random diagonal) or walks a random diagonal for 0.4-3.5 s at a time, turns back at the edges; killable |
| 1, 8, 13, 14 | | Dink is the pawn; texts are the story subsystem's; mouse and buttons are the title screen's: not ported |

Shared helpers, each a port: `ChangeDir` (changedir D:5596: mx/my from speed and dir, `base_walk`+dir with the
engine's fallbacks, frame reset), `AutoMove` (automove D:12214 + move D:13520: pixel by pixel, recording the
path), `CheckIfMoveIsLegal` (D:13416: the first hard pixel on the path puts the sprite back on the pixel before
it; low hardness lets flyers through and stops looking), `AutoReverse`/`AutoReverseDiag`, `GetHard` (get_hard
with its screenlock edge fix; hardboxes of removed placements read 0), `ProcessFollow`, `ProcessTarget`. The
animator (D:16956-17060) advances `seq`/`frame` from dink.ini's delays (or `sp_frame_delay`), wraps at a
`-1` frame, ends at an empty slot (seq 0, `seq_orig` remembered: walk cycles restart from it) and runs
`RunThroughTagList` on a special frame: that is how a monster's attack lands, with the original melee rule
against Dink's hardbox and &defense. Dink's own attack still lands at the hit frame's time (`OnSequenceSet`).
`sp_dir` and `sp_speed` run `ChangeDir` as in the engine (D:7505, 9118); `sp_attack_wait` stores game time + ms;
`create_sprite` makes add_sprite's sprite (speed 1, timing 33, size 100, base_* 0, dir 0); placements start
with dir 0. Scripted `move`/`move_stop` stay the director's (60 px/s per speed point, no hardness): every brain
yields while one runs, as the engine's brains call `process_move` first; `freeze` stops a brain but not a
scripted move.

**Hardness data.** `Content/Dink/Data/Gameplay/Hardness/SCR_nnn.txt` (644 files, 5.7 MB, generated by
`Scripts/sync_gameplay_data.py` from the data repo's `tools/dinkex/out/hardness/*.png` + `_owner.png`): per
&vision value, 400 rows of run-length tokens (`N` = N free pixels, `N:C` = N pixels of code C): 1 solid, 2 low,
3 other, 100+index for a placement's hardbox (the engine's own code, D:6136; warp boxes too). Loaded per screen
on first use (`FDinkGameplayData::GetHardness`). frames.csv gained `loop`, `empty`, `width`, `height`.

**Enemy attacks on Dink** (D:15460, 6656, 14697): a monster's special frame hits every sprite whose hardbox
(+5/+10, plus 28 px or `sp_range` towards its dir) holds it; Dink takes `strength/2 + rand()%((strength+1)/2) + 1`
minus &defense (1 at 50% when below 1) through `ProcessDamage`, no immunity after a melee hit (only touch damage
has its 400 ms); the hit sound is `sp_attack_hit_sound` or sound 9. No knock-back: the original has none.

**Locked fights** (`screenlock`, D:10083): `UDinkGameplay::SetScreenLock` keeps the director's flag and the
greybox in step. Headless, `CanDinkLeaveScreen()` is false while locked (did_player_cross_screen D:14049 clamps
Dink at the edge). In the greybox `UDinkGreyboxSubsystem::SetScreenLocked` raises `ADinkScreenVolume::SetLockBarriers`:
a 1.6 m slab (the engine's basic cube, profile DinkHardSolid: blocks pawns and projectiles) on every edge of
the screen that has no edge wall of its own, and the screen-info line says `[EXITS LOCKED]`. Unlocking follows
the scripts (the last brain-9 monster's `die` calls `screenlock(0)` and plays sound 43, the "secret found" cue,
which reaches the audio stub); a screen load clears the lock (load_map, D:1016). **Warps are not refused**: the
engine's warp code (special_block D:15337, process_warp_man D:15683) never reads `screenlock`, and two locked
screens (419, 577) do have sprite warps. The Bonca of Martridge's trial (SCR_100, `s1-cavem`) is not a locked
fight: `s1-cavem.c` never calls `screenlock`.

**3D adaptation layer** (`FDinkAdaptationSettings`, `Content/Dink/Data/AI/adaptation.ini`, hand-authored):
`Enabled=1`, `WindUpMs=450`, `MaxAttackers=2`, `HoldReaimMs=400`. On: a brain-9 monster (and a brain-10
caster) that may attack first winds up (stops, faces its target, prop `telegraph` 1, a red debug sphere over its
actor in PIE) for WindUpMs and then attacks in the direction it aimed (so a player who stepped away dodges);
at most MaxAttackers sprites wind up or attack the same target at once, the others hold position facing it and
look again after HoldReaimMs. Off = Classic, the original's rules exactly. Play reads the file in
`UDinkGameplay::Init` (on); the parity tests (`Dink.AI.*`, `Dink.Gameplay.*`, the probe) switch it off.

## Verified vs not verified

Verified on this machine (Arch-based Linux, Hyprland/Wayland session, Ryzen 5 7600X, 30 GB):

- Compiling C++ against the prebuilt 5.8.4 install with its bundled clang 20.1.8: editor target,
  unity and adaptive non-unity, plus the game target. Zero warnings.
- Headless automation tests via `UnrealEditor-Cmd -nullrhi` with a reliable exit code and JSON
  report; a full clean-checkout run (copy of the tracked files only) of build + test passes.
- A real `UGameInstance` (`InitializeStandalone`) creates the Dink subsystems, loads the facts
  table, and round-trips a save through a save slot on disk (`Saved/SaveGames`).

- The greybox import end to end headless (see "Greybox import"), including a PIE session driven
  by an automation test under `-nullrhi`.
- The converted Ink story on Inkpot's InkPlusPlus in the editor process: loads, every entry point
  runs (smoke run), conversations match the original text, save/load mid-conversation, and the
  new-game scene plus a talk in PIE on the generated Stonebrook map (see "Narrative runtime").
- The gameplay rules headless (hit, touch, push, death, drops and their odds, pickups, respawn,
  items, magic charge, level-up, Dink's death) and a deterministic PIE playthrough in ten chapters (106 steps) from the new game
  through the cult of Terris (&story 8), the roads and the Mayor, a gold loop, the bow (bought, armed), the goblin gate, the four goblins of the sanctuary, Mog, the Cast camp, the three knights, the Mayor's scroll and the parade (&story 10), Windemere's bomb, potions and cracked rock, the 27 ducks (`&story 11`), the healer, three pickups, Joppa's basement scene and the arrival of the two dragons on the generated world map, with save/load between chapters (see "The probe, in chapters"); all ten also in the packaged game with identical trace md5s. It stops at the Joppa dragons ("Where the probe stops, and why").
- Cook, package and run of the Linux Development game target; `Dink/Data` staged and read through the pak; the ten probe chapters in the packaged game
  with trace md5s identical to PIE's (7 Nov 2026, see "Packaged build").

NOT verified:

- The interactive editing workflow, Live Coding, the editor MCP server, Fab. Standalone play through the editor binary has now been rendered and exercised on the desktop.
- The full world's visual and play review. The starting house and cottage yard now have an authored Blender environment pass and rendered checks; most other screens remain greybox.
- Steam Deck scalability and a broad rendering/performance audit. Desktop Vulkan rendering is verified for the starting environments; authored rigid meshes use Nanite, while foliage retains conventional LODs.
- Packaging for Windows, a Shipping package, and anything of the packaged game that needs a GPU, a window or input (Linux Development
  cook, package and a headless probe run are verified: "Packaged build").
- Broad narrative presentation review across all scenes. The starting scene, floating dialogue and mother's menu were rendered and exercised with actual E/Space/number keys. Wrapping, fades and other conversations still need visual review. Timing constants remain assumptions: move speed 60 px/s per sp_speed point, fade 600 ms, talk range 3.5 m.
- Blueprint usability of the exposed functions (compiled, never opened in a graph).
- Combat feel, pushes and interactions across the full world. Actual F and Q input was verified in the rendered starting house; the source pixel reach and new visual footprints still need a mesh-aware interaction adaptation.
- How the brains look and feel in 3D: cards sliding in pixel steps at each region's scale, the Bonca's 50 px
  reach in metres, the 0.45 s wind-up and the two-attacker cap, the lock slabs. Only automated PIE runs (the
  probe: Martridge's Bonca and Jack fought with the real brains) and headless tests saw them; a broad fight-by-fight visual review remains pending. Fists, dialogue and a charged fireball were checked with the actual desktop F/E/Q keys.

## Linux problems hit, and fixes

1. **`-TestExit="Automation Test Queue Empty"` always exits 1.** On Linux it ends the process with
   `FUnixPlatformMisc::RequestExit(true)`, which `_exit(1)`s unless a return code was overridden,
   even when every test passed. Fix: use `-ExecCmds="Automation RunTests <filter>; Quit"`; the
   automation command line then logs `**** TEST COMPLETE. EXIT CODE: 0 ****` and exits 0, or 255
   on any failure or when no test matches.
2. **"Querying IsUsingWayland before SDL is initialized" every frame** (700+ lines) when the
   headless editor inherits a Wayland session; the automation report then marks every test
   "succeeded with warnings". Fix: run with `env -u WAYLAND_DISPLAY -u DISPLAY` (test.sh does).
3. **Ensure: "DinkFactSubsystem with ClassWithin of GameInstance was created in invalid Outer"**
   when a test did `NewObject<UDinkFactSubsystem>(GetTransientPackage())`. Fix: create a
   throwaway `UGameInstance` as outer (`DinkTest::MakeOuterGameInstance`).
4. **The editor wrote a `SecurityToken=` into `Config/DefaultEngine.ini`** on first start (the
   AndroidFileServer plugin's settings). Fix: the plugin is disabled in the `.uproject`; after
   that, a headless run leaves `Config/` and the `.uproject` unchanged (checked by checksum).
5. **`GenerateProjectFiles.sh` writes into the engine install**: about 6,000 IntelliSense files
   under `~/UnrealEngine/UE_5.8.4/.vscode`, `Engine/Intermediate/` and every engine plugin's
   `Intermediate/`. It was run once (in a scratch copy) and everything it created in the engine
   was removed again. Do not run it unless the owner accepts that; the build does not need it. It
   also creates `.vscode/`, `*.code-workspace`, `Makefile` and `.ignore` in the project (all
   git-ignored).
6. **UBT always writes to the engine and home directories, by design:** a dependency cache in
   `~/UnrealEngine/UE_5.8.4/Engine/Saved/UnrealBuildTool/Cache` (under 1 MB so far), its log in
   `~/.config/Epic/UnrealBuildTool/Log.txt`, and the editor writes per-user state under
   `~/.config/Epic/`. Unavoidable when building; harmless.
7. **Unreal Build Accelerator listens on `0.0.0.0:1345`** while a build runs (log line
   `UbaServer - Listening on 0.0.0.0:1345`). Local-only builds do not need it to be reachable; keep
   the port firewalled.
8. Not a problem, just surprising: UBT's "adaptive unity" uses `git status`, so new or modified
   files compile as separate translation units. Pass `-DisableAdaptiveUnity` to `build.sh` to
   check the real unity build (verified to compile).
9. **Editor commandlets have a working editor world.** `UEditorLoadingAndSavingUtils::NewBlankMap/
   LoadMap/SaveMap`, `UEditorLevelUtils::CreateNewStreamingLevelForWorld` and
   `FEditorFileUtils::SaveLevel` work in `-run=` commandlets with `-nullrhi`; PIE works in
   automation tests under `-nullrhi` (`FStartPIECommand`).
10. **A spawned `ADirectionalLight` ignores the spawn transform's rotation** (it came back as
   -84/-145/180, scale 2.5). The importer sets the root's world transform after every spawn.
11. **Meshes compile asynchronously after a map load** when their data is not in the DDC; traces
   then miss them. Tests call `FAssetCompilingManager::Get().FinishAllCompilation()` after
   `LoadMap`.
12. **Comparing transforms:** `FTransform::Equals` treats q and -q as different; compare rotations
   with `FQuat::AngularDistance`.
13. **`-run=pythonscript -script="file.py arg"`** needs `-FullStdOutLogOutput` to show anything on
   stdout. `EditorLevelLibrary` is deprecated in 5.8 (use the editor subsystems).
14. UE 5.8 API changes met here: `FJsonObject::Values` keys are `UE::FSharedString` (use
   `ToView()`), material usage flags via `UMaterial::SetUsageByFlag`, and a global `Rect` type
   clashes with a local helper of that name.
15. **Inkpot's InkPlusPlus does not compile with clang as shipped**: three range-for loops bind
   `const TPair<FString, ...>&` to map elements keyed by `UE::FSharedString` (5.8), which clang 20
   reports as `-Wrange-loop-construct` errors. Patched (see "Narrative runtime"); re-apply after
   updating Inkpot.
16. **InkPlusPlus logs some story errors with `UE_LOG(InkPlusPlus, Error)`** (its "exceptions"),
   which fail an automation test. Errors it reports through `OnError` are collected by
   `FDinkInkStory::TakeErrors`. A test that may hit runtime errors must declare them
   (`AddExpectedError(..., -1)`); the smoke run captures the category into its report.
17. **Generated placeholder actors are Static**: `SetActorLocation` on one only logs "Root has to be
   'Movable'". The director switches an actor's components to Movable before moving it.
18. **The new-game scene freezes Dink** (`freeze(1)` in the mother's `main` on SCR_001), which
   holds `PlayerController::SetIgnoreMoveInput`. PIE tests that drive the pawn either wait for the
   scene, skip it, or leave the screen (a screen change that ends every script unfreezes Dink).
   `SetIgnoreMoveInput` is a counter: the director calls it only when the frozen state changes.
19. `FMath::RoundToInt(double)` returns `int64`; `TestEqual(..., RoundToInt(x), 5)` is ambiguous.
   Cast to `int32`.

20. **`sp_touch_damage(x, -1)` is a write, not a read.** The director treated -1 as "read only" for
   every `sp_*`, so script-made pickups never became touchable. The engine writes -1 for the setters
   it implements with `change_sprite_noreturn` (dink.cpp D:5471): touch_damage, base_walk,
   base_idle, base_attack, base_die/base_death, base_hit, mx, my. Fixed in `SpriteProperty`.
21. **The greybox's current screen lags a teleport** by its check interval. Anything that turns the
   pawn's location into a screen's pixels must use the screen at the location
   (`UDinkDirector::ScreenAt`), or the pixels are computed against the old screen's corners and the
   next scripted move of Dink flings the pawn off the map (seen in the probe).
22. **`APawn::TeleportTo` fails on blocked spots** (it does not move the pawn); `dink.Goto` to a spot
   inside hardness silently stays put. The probe tries a ring of nearby spots.
23. **Removing an Ink flow that never existed** dereferenced the runtime's null flow map; an instance
   made by `load_script` (item scripts) has no flow until a procedure starts. `FDinkInkStory::RemoveFlow`
   checks `AliveFlowNames` first.
24. **Headless PIE runs can be killed from outside** (exit 137 once, 21 s in, while 21 of 30 GB were
   in use; no crash in the log; probably the OOM daemon, unverified). Rerun.

25. **Sprite references go stale when a script runs.** `FDinkSprite` records live in a `TMap`; a script run from
   inside a brain (`attack`, `hit`, `damage`, `die`) can `create_sprite`, which may reallocate the map. Brain
   code re-finds sprites by handle after every `RunProc`/`RunNow` (see `ThinkSprite`, `MissileBrain`).
26. **Hardness maps are big in memory** (240 KB per screen and vision once loaded; they stay cached). Tests
   that scan for a feature should look at a few screens, not all 644.
27. **PIE under the real-time step is not repeatable** (see "The probe, in chapters", Determinism). Probes and tests that
   need the same game twice set `FApp::SetUseFixedTimeStep(true)` / `SetFixedDeltaTime(1/60)` before PIE starts and restore
   it, and time everything in game time (`UDinkStorySubsystem::GetNowMs`), never `FPlatformTime`. No function-level
   `static` in test or gameplay code: it outlives the PIE session.
28. **A final-state snapshot at a timeout can catch a periodic action in flight.** The probe's old 300 s timeout was
   a multiple of the 5 s fireball cycle, so every failure report showed `item-fb.use` blocked in `wait(100)` with the charge
   at 0-6: it looked like a stuck script and was not. Check a suspected stuck wait over time (the trace) before blaming the
   director.
29. **The story ticks inside `UWorld::Tick`**, one frame before the greybox sets its current screen, so the new game
   starts (newgame.c: `sp_x(1, 334)`, fists) a frame after the pawn exists. A PIE test that teleports the pawn on its
   first frame gets flung by newgame's `sp_x`/`sp_y`; wait for `Story->bNewGamePending` to be false.
30. **Surviving script instances follow the current screen** (`OnScreenEntered`); an instance's `Screen` decides where
   its `create_sprite`s go and which sprites `sp()` finds. Sprites on another screen than Dink's are never thought for.
31. **Quitting the editor while PIE runs crashed** (SIGSEGV at 0x60: `EndPlayMap` asks the already-destroyed
   `UAssetEditorSubsystem`). `DinkParityModule` ends PIE on `OnEditorPreExit`.
32. The greybox's billboarding of sprite cards (`dink.Billboard`) walks every placement actor each frame; it is skipped
   when the app cannot render (`-nullrhi`: all headless runs), which took about 10 s off the probe.
33. **Chapter tests depend on each other through save slots** (`probe_ch<N>`). The runner sorts tests by path, so they are named
   `Ch1..Ch4`; a lone `Scripts/test.sh Dink.Gameplay.Probe.Ch3` uses the slot of the last complete run. A chapter's trace changes
   whenever anything it or an earlier chapter plays changes (kiting is chaotic: one frame earlier and another random number), and
   the next chapter then starts from a different game: rerun the chapters in order after touching gameplay code, not just one.
34. **A save moves the pawn in one step, the greybox's current screen lags** (0.25 s check): the story entered the screen the pawn
   had just left, then the saved one. `UDinkGreyboxSubsystem::RefreshCurrentScreen` after `RestoreFromSave`; a loaded game's first
   dump must equal the saved one (the chapters check it).
35. **Pixels past the map and gravity.** Scripts put Dink at y 480 (s2-culg.c:47) or walk him off the edge; there is no ground
   there and the pawn fell out of the world (Z -22405) and stayed. `SetFrozen` takes his gravity away while a script holds him.
36. **Warps fire on the original's hardness hit, not on overlap.** `special_block` (D:15337) runs from the walk code's hit test:
   Dink's own walking and a scripted `move` with nohard 0 trigger it (s1-h1-s.c walks him out of the burning house into the
   door), `move(1, dir, stop, 1)` (nohard 1: s2-culg.c, s3-camp.c) and sp_x/sp_y never do. The 3D trigger overlaps in both cases,
   so the director's `bMoveNoHard` feeds `UDinkGreyboxSubsystem::WarpSuppressed`. Before: Mary's scene sent Dink out of Nadine's
   house through the door he walked past. (A first try that suppressed warps for every frozen Dink broke the burning house.)
   A probe teleport that lands inside a warp's trigger (S067_P15 by the shop door) is bounced out at once.
37. **A step that reads sprites by script name sees the previous screen's** until the new screen is entered (a vanishing `papgold`
   made "the chest opened" true on arrival): gate such a `Done` on `OnScreen(Screen)`. And a "raised by N since the step began"
   mark must not be -1 when read (`FProbeState::Mark`).
38. **`Scripts/build.sh | tail && ...` does not stop on a failed build.** A header change in DinkCore with a DinkNarrative compile
   error leaves modules of two layouts side by side and the editor then misbehaves (greybox screen 0, "the new game did not
   start") instead of failing loudly; check `BUILD OK` before running tests.
39. **Fast chasers cannot be kited.** `en-pill2` moves 3 px a frame (timing 0), Dink walks 3 px a frame: equal speed in a closed
   rectangle, and the first fireball makes the bug target him. Slow chasers (girls 30 px/s, Nelson 15, Boncas 30) can. **The Bong is not slow**
   (`en-bong.c`: speed 2, timing 0 = 120 px/s, 170 px/s on a diagonal, since `changedir` gives a diagonal step the full speed on both axes);
   goblins `s3-gs`, Mog and the knights walk 60 px/s (85 diagonal). Anything that strikes from within 50 px of a wall gets cornered.
40. **The second PIE session of one editor sees the first one's world for a few frames** (`GEditor->PlayWorld` still points at it after
   `FEndPlayMapCommand`): a probe that loads a save in its first update loaded it into the vanishing world, and the new session then
   ran a plain new game (`RepeatableChapter` failed on it: "the runs part at event 1"). A chapter waits for a story clock under 10 s and
   `&story >= 1` (the new game's scene has begun) before it loads its slot.
41. **A loaded chapter's trace starts at the load.** The frames the new game ran before it (the mother's scene) vary with how long PIE took
   to start; `Events.Reset()` after the load comparison keeps them out of the trace and its md5.
42. **A text's expiry deleted whatever sprite had its handle.** The active text list outlives a screen change (which releases every sprite but
   Dink and the survivors); the handle went to the next sprite and `Sprites.Remove(handle)` at the text's end deleted it, silently: a Bong
   of SCR_480 vanished 2.7 s after Dink came from the screen where he had picked up gold, and the probe's gold loop never ended. In the
   engine a text is a slot with its own kill timer (D:16811-16823). `UDinkStorySubsystem::RemoveTextSprite` removes only a sprite that still is
   a text; test `Dink.Gameplay.Texts.ExpiredTextKeepsARecycledHandle` (fails without the check). The old chain depended on the bug (stray
   sprites, and their hardboxes, vanished in Stonebrook): with it fixed Jack's and the cult's fights needed the openness rule and the flee
   fallback (the hashes of all chapters moved).
43. **`C.Busy()` is true for ever on a screen whose script loops on `wait`** (a shop keeper's `mainloop`: `s2-healp`, `s2-out`): a step there
   must be a fight step (`bFight`, acts despite Busy) and not wait for `!Busy()`; and a `Done` must not ask for `!Busy()` after the talk
   (`talk` ends in `goto mainloop`).
44. **Shop interiors: a teleport to the doorstep lands inside the exit's warp trigger** and bounces back out (SCR_097 at 299,328): use 300,230.
45. **Pairs of `en-bong`/`en-boncd` fight each other** (see "Chapter 4, the gold"): a probe that hits one first gets the other's blows meant for
   it, and a fight that never starts is the cheapest gold in Act B. `Hostiles()` and `KiteFight`'s threat list can disagree for a frame
   (`GetHardbox` fails in some attack frames): a "sweep done" test needs a positive sign (a drop seen), not a smaller count.
46. **Time dilation is the probe's fast-forward** for waits with nothing alive near Dink (`Dilate`, reset in `Finish`); never during a fight.
47. **`FName` display case does not survive a cooked game.** `WITH_CASE_PRESERVING_NAME` is editor-only: in a package `FName("main").ToString()` is the
   engine's own `Main` (`Game`, `Start`, `Cmd`, `Say`...), in the editor it is what was typed. Anything printed from an FName that must equal the editor's text (the event
   trace, hence the probe md5) is lower-cased where it is written (`DinkStorySubsystem.cpp` event texts, the probe's trace writer). Compare names with FName equality, never as text.
48. **A packaged process starts the automation test 300 frames late** (the controller waits 5 s of ticker time = 300 fixed 1/60 s frames while the world already runs the
   new game): `-ExecCmds="Automation RunTests X; Now; Quit"` (`Now` is a sub-command of the same `Automation` command, `Automation Now` on its own is "unknown command") starts it at
   frame 5. The probe must begin one world frame after the world starts (story clock 16.667 ms), as in PIE: `-DinkProbeHold` (DinkProbe module) pauses the world until then.
49. **The tickable order of the story and greybox subsystems differs between PIE and a game process.** `UGameInstance::InitializeStandalone` makes a throwaway default world first;
   its greybox subsystem's slot in the engine's tickable list is reused by the real world's greybox, so the greybox ticks before the story (a screen change is seen one frame
   earlier, which moved every timestamp and the `rand()` draws). `DinkProbeHold` re-adds story then greybox to the list. Code that depends on which of two tickables runs first in a frame
   is not the same in a package.
50. **`-SkipCookingEditorContent` fails the cook** ("Content is missing from cook", exit 25): the engine's Landmass plugin (a cook startup package) references `/Engine/EditorMaterials`.
   Do not pass it. A hung `RunUAT` at "Reading oplog from Zen..." means another agent's editor restarted the shared Zen server: kill it and rerun.
51. **`pgrep -f` waits match their own shell.** A wait loop (or an agent's wrapper script) whose command line contains the pattern words (`UnrealEditor-Cmd`, `AutomationTool`...) waits for
   ever; keep those words out of argv (put the commands in a script file). `package.sh`'s own busy check ignores another project's visible game.
52. **Other agents write into this tree while you work** (another agent's `restart_game` sources and a chapter 6 extension of `DinkProbeTests.cpp` arrived during the packaging session). Never
   put back a file from your own backup copy: diff it against the live file and the other stage first (this session overwrote `DinkStorySubsystem.cpp` that way once and restored the
   other side's changes from its stage copy). When a chapter's hash moves, check the source mtime before blaming the packaging; compare PIE and packaged runs of the same source.
53. **`sp_script` starts `main` instead of running it** (parity bug, NOT fixed): `dink.cpp:8164-8171` runs the new script's main at once, so lines the caller sets after
   the `sp_script` override it; `DinkDirector.cpp` `sp_script` calls `StartProcedure` and the instance runs after the caller yields. Visible in `s3-camps.c:96-116`: the
   knights end with 100 hp (main of `s3-dorks`) instead of 40. A trial `Story->RunNow(MainId)` after the `StartProcedure` moved the trace md5 of every chapter (Ch1 1fc1c41a7b,
   Ch2 c444e7a247, Ch3 a6aa8e24c5, Ch4 9c441084c6, Ch5 ddfacf1458; Ch3 then stopped at step 1 of 11 and Ch6 at 1 of 3: the order of the mains of `dam-fire`, `papgold`,
   `s2-cbon`... changes every later `rand()` draw and the fights tuned to them), and was reverted (hashes back, checked). A real fix needs the chapters re-tuned and the
   packaged parity re-proved; it needs a unit test (a script that sets a stat after `sp_script` of a script that sets it too) and the `dink.cpp` citation above.
54. **The probe's wall-clock limits counted from the command's construction**: a test that queues two runs (`RepeatableChapter`) built both commands up front, so a first run
   slowed by a loaded machine (load average 22 from other agents' renders and editors: 96 s instead of 26 s) used up the second run's 60 s start-up limit ("the new game did not
   start"). `FProbeCommand` now counts from its first `Update`. Game time and traces are unaffected by load (fixed step); only the wall times in tables are, so they are unloaded figures.
55. **A dead Dink does not stop a probe step.** After `dinfo` runs (the death menu answers "Quit to Windows", `kill_game` is recorded and ignored) the step goes on, with the
   screen's monsters, until its game-time timeout; a chapter report that says "did not complete in N s" may be a Dink that died at 70 s. Grep the trace for `dink died`.
   Monsters' blows hit every sprite in the box, other monsters too: three knights around a dead Dink killed each other (80-240 s).

53. **`sp_script` runs `main` at once** (parity bug, FIXED 7 Nov 2026; test `Dink.Narrative.Director.SpScriptRunsMainAtOnce`). `dink.cpp:8155-8175` does `kill_scripts_owned_by`,
   `load_script`, then `locate(script, "MAIN"); run_script(script)` on the spot, unless `g_dglos.no_running_main` is set (`dink.cpp:8163, 8169`); the remake only started `main`
   (`StartProcedure`), which ran after the caller yielded, so `s3-camps.c:108-113` (`sp_script(.., "s3-dorks")`, whose main sets 100 hp, then `sp_hitpoints(.., 40)`) left the knights
   with 100 hp, not 40. `DinkDirector.cpp` `sp_script` now calls `Story->RunNow(MainId)` after the `StartProcedure`: the new instance runs in the caller's turn until it blocks
   (a main that waits or `say_stop`s stays Blocked and the tick continues it; the caller goes on at once, as `run_script` returns at the first block). `no_running_main` is true only
   in `BuildScreenBackground` while a screen's base script (`g_smallMap.script`) runs its main (`dink.cpp:6805-6814`); `init_scripts` (`dink.cpp:11690`) runs the mains of the sprites
   it attached once the screen is built. Here: `UDinkStorySubsystem::bNoRunningMain` is set around the base script's first `StepInstance` in `EnterScreen`, and `sp_script` then
   keeps the old deferred start (which is `init_scripts`' order). Unit test: a stand-in for script A runs `sp_hitpoints 7; sp_script s3-dorks; sp_hitpoints 40` (reads 100, defense 6, strength 12,
   touch 5 after the `sp_script`, 40 after the last line, and 40 after `RunUntilIdle`/`Advance`; B's main started once), a blocking main (`s1-bul`: `sp_speed 2` is set, the instance is
   Blocked on the wait, the caller's next line runs, `Advance(0.25)` takes it to its `say_stop`), `bNoRunningMain` (attached, main not run on the spot, run at the next `Advance`), and a
   replaced script (one live instance). Do not read a stat with `SpriteProperty(.., -1)` in a test: for `touch_damage` it WRITES -1 (`AlwaysWrite`). Every chapter hash moved (section "The probe, in chapters");
   nothing needed re-tuning. `spawn` and `external` have the same gap: pitfall 56.
54. **The probe's wall-clock limits counted from the command's construction**: a test that queues two runs (`RepeatableChapter`) built both commands up front, so a first run
   slowed by a loaded machine (load average 22 from other agents' renders and editors: 96 s instead of 26 s) used up the second run's 60 s start-up limit ("the new game did not
   start"). `FProbeCommand` now counts from its first `Update`. Game time and traces are unaffected by load (fixed step); only the wall times in tables are, so they are unloaded figures.
55. **A dead Dink does not stop a probe step.** After `dinfo` runs (the death menu answers "Quit to Windows", `kill_game` is recorded and ignored) the step goes on, with the
   screen's monsters, until its game-time timeout; a chapter report that says "did not complete in N s" may be a Dink that died at 70 s. Grep the trace for `dink died`.
   Monsters' blows hit every sprite in the box, other monsters too: three knights around a dead Dink killed each other (80-240 s).
56. **`external` and `spawn` run their script at once** (parity gap, FIXED 7 Nov 2026 night; test `Dink.Narrative.Director.ExternalAndSpawnRunAtOnce`; found by the ducks of Windemere). `dink.cpp:11326-11360` (`external`: `load_script`, `locate`, `proc_return = script`, `run_script(child)` on the spot; when the child's procedure ends `run_script(proc_return)` resumes the parent, `dink.cpp:11588-11590`; when it blocks `run_script` returns and the parent is only resumed by that end) and `dink.cpp:8181-8203` (`spawn`: `load_script(name, 1000)`, `locate(.., "MAIN")`, `run_script`). `DinkDirector.cpp` now calls `Story->RunNow(Child)` after `StartProcedure` in both. `external` returns no block when the child has ended (or ended its own caller, e.g. by `sp_script` on the caller's sprite): the caller's next line runs in the same turn, after the child's effects; it returns `Block(Child)` only if the child is still alive (a `wait`, a `say_stop`, a menu), and `UpdateBlocks` resumes the caller when the child is gone. `spawn` runs the new main until it blocks and the caller goes on. Before: the child's first line ran on the next story step, so s4-duck.c's `duckdie` (`UDinkGameplay` runs it with `RunProc`, then `DeactivateSprite(H, 0, true)`, which ends parent and child) never ran `external("make", "foodduck")` for the last duck and never reached `if (get_sprite_with_this_brain(3, ..) == 0) spawn("s4-end")` (`&s4-duck 2`, `&story 11`). **Deviation from the brief:** `spawn` does NOT get `sp_script`'s `bNoRunningMain` rule: `no_running_main` is read only in `sp_script` (`dink.cpp:8163, 8169`; it is set at `6812-6814` and cleared at `17673`), `spawn` and `external` run unconditionally, and none of the 7 `spawn` scripts (item-bom, item-eli, s3-gs, s3-gh, s4-duck, en-drag, s7-boss) is started inside a base script's first segment; the director mirrors the source. Other commands that start a script, checked: `run_script_by_number`, `hurt` -> `hit`, every `UDinkGameplay::RunProc` (hit, touch, push, die, duckdie, damage, attack) and `lraise` already `RunNow`; still deferred and left alone: the `set_callback_random` callbacks (`StartProcedure` in `Advance`, the instance runs in the same tick's pass loop; the original runs callbacks from the same tick), the screen's placement mains (`EnterScreenPlacements`, deferred on purpose: `init_scripts`, `dink.cpp:11690`, runs them after the screen is built) and the talk key (`TryTalk`: the proc starts in the next story step; the original calls `run_script` from the key handler; nothing needed it). Test (stand-in caller, real scripts): `external make sheart` leaves `&save_y` 101 and a seq-54 sprite at once, no block, the caller's own `&save_y = 55` stays 55 after `RunUntilIdle`/`Advance`; `spawn s4-end` leaves `&s4-duck 2`, `&story 11`, an instance owned by 1000 Blocked on its first `move_stop`; two headless `s4-duck` sprites killed through `ProcessDamage`: each `duckdie` makes its food sprite (seq 421) before the sprite is removed, the first finds the other duck alive, the second reaches `spawn("s4-end")` (main started once); `external s4-end main` stands in for a blocking child (`Block(Child)` with the child's id; the caller stays Blocked while it lives and goes on when instant mode finishes the moves). Run against the old code (both `RunNow` calls switched off for one build, then edited back): it fails 15 expectations (the child's effects, the food sprites, `&s4-duck 2`, `&story 11`, the block result 4 instead of 0). Chapters 2, 4, 7, 8, 9 changed hash (1, 3, 5, 6 did not), nothing needed re-tuning.
57. **Monsters' blows hit each other, so a Dink who is never hit wins a fight with several of them** (the knights, 40 hp each, 7 Nov 2026 night: `SquadFight`, 39 s, one blow taken). Do not tune a fight against several
   chasers on damage output: strength 9 against defense 6 does 1.4 a punch. Model each monster's blow box (pending and potential), stay out of every box, and stay where they come together to swing.
58. **A probe step's `P->Mark` must be reset by the step that set it.** `Mark` is one value for the whole run; the Pete step of chapter 9 left the gold it noted (239) in it, and the next step, which notes `strength` only
   `if (Mark < 0)`, waited 40 s for strength 240 while Dink punched the ducks. Steps that note a value end with `Mark = -1` (as `Reached` in chapter 3 does).
59. **`package.sh` refuses to run while ANY bash command line contains the words `UnrealEditor-Cmd`/`RunUAT`/`AutomationTool`** (pitfall 51, again: another agent's wait loop with a never-matching `pgrep` sat in the process list
   for 20 minutes). Check `ps` for a real editor/UBT/UAT, then `DINK_ALLOW_CONCURRENT=1 Scripts/package.sh`. The first package run of the night hung at "Reading oplog from Zen..." for 10 minutes while another agent's full
   suite started in this project (pitfall 50); killed and rerun after it ended: 28 s.

60. **A chapter after Ch9 must sort after it and before `Probe.Repeatable`.** The runner sorts by path: `Ch10` would run before `Ch2`. Chapter 10 is `ChAJoppa` (`'9' < 'A'` in either case order; `Ch9b...` would sort before `Ch9W...` if the sort ignores case). A chapter 11 is `ChB...`. `MakeChapter(10, ...)` still loads `probe_ch9` and writes `probe_ch10` (report and trace `probe_ch10*.txt`, which `run_packaged_tests.sh`'s parity glob `probe_ch*_trace.txt` finds); the packaged script's default list ends with `ChAJoppa`.
61. **The game target must not use unity builds** (`Source/DinkRemaster.Target.cs`, like the editor target). Adaptive unity picks the files to compile alone from the git working set; after the project moved into the fork and its files were committed, `DinkRemaster.Target` bundled `DinkGameplay.cpp`, `DinkBrains.cpp` and `DinkStorySubsystem.cpp` into `Module.DinkNarrative.cpp` and `package.sh` failed with `redefinition of 'Inside'` (DinkBrains.cpp:49 / DinkGameplay.cpp:39) and `redefinition of 'NAME_Main'` (DinkGameplay.cpp:29 / DinkStorySubsystem.cpp:31): file-local helpers in the three files share names. The editor build never showed it (unity off). With unity off in the game target the package builds (51 s). The collisions are still in the sources (rename or `namespace` them if a unity build is ever wanted); not touched here.
62. **`CheckOriginal` (verbatim checks against `bin/dink/story/<script>.c`) was silently skipped after the move into the fork:** it looked for `../Dink-Smallwood-Remaster/bin/...` next to the project; the data is now `../bin/...`. `DinkGameplayTests.cpp` and `DinkNarrativeTests.cpp` try the new path first, then the old sibling one. If a verbatim check starts failing after this, the test is right and the quoted text or the story is wrong.
63. **The Joppa dragons answer the first punch with a cast** (`en-drag.c`: `hit` re-targets the hitter, `attack_wait` is long past, so `attack` fires `hurt(Dink, 20)` at once: 16 net at defense 4; then `random(5000,3000)` ms). Numbers and the kit the fight needs are in "Where the probe stops, and why"; a Dink under about 40 life cannot trade punches with them. They are brain 10 cardinal wanderers that cast from where they stand and hurt by touch only (10).
64. **`SquadFight` and `Hostiles` do not agree about brain 10.** `SquadFight` takes brain-9 monsters only (the knights), `Hostiles` counts brain 9 and 10, `DuelFight` takes a handle. A first try of the dragons with `SquadFight` did nothing at all (no `probe:` events) because it found no foe: pick a tactic by brain.
65. **A probe chapter with floor 0 passes when its step fails.** A throw-away chapter (the dragons) reported `TESTS PASSED` with `0 of 1 steps`; read the first line of `Saved/Narrative/probe_chN.txt` and its `STOP step` line, not the test summary.
66. **`pgrep` printed before a run is not a wait.** A test run of this session started in the same second a headless editor of another agent appeared (28 s, no harm done); gate every build/test/package behind a loop that only continues when the `pgrep -f` pattern, written so that it cannot match its own command line, finds nothing (a script file in the scratchpad: `a="[U]nreal"; b="Editor-Cmd"` ... `pgrep -f "${a}${b}|..."`), and re-check right before a long run.

## Decisions and deviations from bible 05 section A

- **AI is plain C++, not State Trees (yet).** The plan's "four State Trees" would need `.uasset` State Tree
  assets, which cannot be created and tested headless from text here, and the brains must run on virtual
  sprites in headless tests anyway. So the brains are C++ on the director's sprite records
  (`UDinkGameplay::ThinkSprite(Handle, TickMs)` is the per-sprite entry point, public). A State Tree task can
  later wrap it: a "Classic brain" task calls `ThinkSprite` each 60 Hz step for its actor's handle, and the
  adaptation layer's decisions (`AdaptationAllowsAttack`, `CountAttackers`) are the natural conditions/tasks of
  the "chaser" tree. Until then the 3D layer is the data-driven `FDinkAdaptationSettings`.
- Brains run in the original's screen pixels against the original hardness map (not navmesh, not the 3D
  collision): parity first; the greybox actors follow. The player pawn still walks against the 3D collision.
- Scripted `move`/`move_stop` stay the director's (no hardness, 60 px/s per speed point, ignore sp_timing);
  the brains only yield to them. In the engine process_move runs inside the brain at the brain's timing and
  is checked against hardness (unverified whether any shipped cutscene depends on that).
- Warps are not refused during a locked fight, because the engine does not refuse them (see the brains section).
- The adaptation layer's telegraph has no animation: a debug sphere and a `telegraph` prop for the visual
  layer to read.

- No separate `UDinkFactRegistry`: the definitions table (name, initial value, kind) lives in
  `UDinkFactSubsystem` and is loaded from CSV. Split it out if facts gain more metadata.
- Origin ID text is `S412_P03` (two-digit placement, as the data repo's `tools/dinkex` writes);
  the bible's `S{screen:03}_P{sprite:03}` is accepted by the parser (1-3 digits) but not
  produced.
- Inventory slots hold `FName` item IDs = the original item script names (`item-fst`,
  `item-fb`). They map 1:1 to the future `UDinkItemDefinition`/`UDinkMagicDefinition`
  PrimaryAssetIds, which do not exist yet.
- `DinkRules::` namespace with separate melee, missile, touch and scripted-hurt functions
  instead of one `DinkCombat::ResolveDamage`: the original has four different rules.
- Missile damage has two variants. The base game runs the integer formula
  (`m_use_latest_fixes_level` is zero-initialised and no base script changes it); the float
  formula in bible 03's table is the HD engine's opt-in variant. `EDinkFixesLevel` selects;
  default `Original`.
- Respawn reference time is the later of "override set" and "player last left the screen"
  (the original uses only the per-screen exit time, `spmap[].last_time`; identical in every case
  the original can produce). The subsystem owns the game clock (`GameTimeMs`) and the per-screen
  exit times, and both are saved; bible 05 listed neither.
- `FDinkWorldOverride::Variant` (FName) replaces the original `editor_seq`/`editor_frame`.
- Added `UDinkSaveSubsystem` for slot IO; `UDinkSaveGame` stays a plain data object with
  capture/apply.
- `UDinkStatsComponent` applies damage immediately (the original defers to the target's next
  think), floors life at 0, and can mirror player stats one-way into the engine-kind facts so
  conditions like `level >= 2` work.
- Magic recharge: the documented `seconds = cost / (10 x magic)` is provided, plus the exact
  in-game value `ceil(cost / magic)` steps of 100 ms (`MagicRechargeSteps`); they differ when cost
  is not a multiple of magic (100 at magic 3: 3.33 s nominal, 3.4 s exact).
- Not built yet (out of this slice): `UDinkScreenSubsystem` (the greybox's `UDinkGreyboxSubsystem`
  tracks the current screen for now), reactions, actions, definitions data assets, AI,
  GameplayTags. (The director and the talk interaction exist: see "Narrative runtime".)
- `UDinkStatsComponent`'s fact mirror is two-way (it was one-way): the fact store is the one
  source of truth for the engine-bound stats, so scripts can write them. On a fact reset/restore the
  stats are pulled from the facts.
- Save version 2 adds `SubsystemState` (module text blobs) instead of DinkCore knowing about Ink;
  the narrative state is JSON text in it. Step 1 -> 2 is a no-op (older saves have none).
- Gameplay decisions (details in "Gameplay rules"): the engine's trigger rules run in the original's
  pixel space on the director's sprite records (greybox actors synced into it each tick), so the
  same code serves virtual sprites in headless tests; the per-frame and per-placement data comes in as
  text (`Scripts/sync_gameplay_data.py`), not as properties on the generated actors (no re-import
  needed); the touch/push/talk boxes get the capsule radius in pixels added in 3D; DinkC `random()`
  is an EXTERNAL answered by one seedable rand() stand-in (the converter used to emit Ink `RANDOM`);
  damage is applied on the next gameplay tick, not inside the command, which is the engine's
  "brain think" order; only type-1 (live) placements get sprites and run scripts on screen entry
  (before, every placement actor with a script ran `main`, including vision-gated background ones).
- Narrative decisions (details in "Narrative runtime"): InkPlusPlus used directly (not Inkpot's
  UObject/asset layer) so the story stays a text file; one story, one Ink flow per script instance;
  presentation drawn on the HUD canvas from C++ and keys via a Slate input pre-processor, so no
  widget or input assets.
- Greybox decisions (details in "Greybox import"): non-World-Partition persistent level + one
  always-loaded sublevel per landmass/interior group; `_Generated/`, `ImportData/` and the copied
  template content are git-ignored and regenerable; placement collision comes from the screen's
  hardness meshes, not from the placeholder (removable obstacles such as barrels are therefore
  permanent in the greybox); background (type 0) decoration is instanced; the start is SCR_001.
- SCR_299 ("Islets", unreached sea) is excluded: tools/analyse left it at its nominal grid
  position, where it covers 557 m2 of SCR_333 (Murkwood). The exporter excludes the unreached
  screen of any overlapping pair and fails if two reached screens overlap.

## Unfinished / next

- (Done 6 Nov 2026: the story subsystem drives the world-state clock and respawns; the gameplay
  layer's 100 ms status update charges magic; &cur_weapon/&cur_magic arm through `ArmItemSlot`/
  `ArmMagicSlot`.) Pause the charge while an inventory screen is open once there is one.
- AI follow-ups (see "Brains..."): State Tree wrappers around `ThinkSprite` when assets can be authored;
  scripted moves with hardness and brain timing; sp_reverse; brains 13/14 (title screen); corpses
  (add_kill_sprite pictures); a real telegraph and thorn barrier; probe: the Joppa dragons (a kit with strength 20+, "Where the probe stops, and why") and everything after them.
- Gameplay follow-ups (see "Gameplay rules"): animation (the hit currently lands on the hit frame's time with
  nothing drawn; init() sequence redefinitions are recorded, not applied, so the sword's own hit
  timing is dink.ini's), missile pictures and the bow (
  arrows/bow `activate_bow`), corpses/blood/damage numbers, an inventory screen (use
  `dink.Arm`/`ArmItemSlot`), the DNOTALK/DNOMAGIC "nothing here" lines, the status bar; animation
  reads the recorded sp_* props (`UDinkScriptSpriteComponent`); real
  a status bar for `draw_status`; show_bmp pictures; the
  per-screen order of base-script `main` vs placement `main`s is approximated (base script runs
  until its first block, then the placements).
- `GameDefaultMap` points at `L_Greybox_World` (git-ignored, so missing until imported);
  `EditorStartupMap` stays the empty engine map so headless runs stay light.
- Greybox follow-ups: vision-variant collision (only vision 0 is built); script warps with their
  real conditions (story facts, dialogue); doors' open animation and fade; thorn art for the screenlock barriers of the
  35 encounter screens; Landscape/elevation; billboarding or proxy meshes instead of flat cards;
  move removable hardboxes (barrels, bombable rocks) from the screen mesh to their actors; music
  per screen volume.

## Rendered debugging and authored environment art (6 Nov 2026)

See `Scripts/ART_PIPELINE.md` and `SourceAssets/Art/README.md` for the source workflow, verified FBX import details and production limitations. Blender 5.2.2 LTS, `grim`, `hyprctl` and `wtype` were already installed; no system package install or desktop config change was needed. Original Blender geometry and procedural textures are in the asset ledger with source hashes and candidate status. The starting house and yard are environment candidates. Authored Dink and mother candidates now replace Manny and the sprite, with CC0 MakeHuman anatomy, original project wardrobe, four real LODs and the exact existing 89-bone animation rig. The house-fire variants and other regions still need art.

- Interior: `Scripts/import_stonebrook_art.sh` imports 14 meshes and seven PBR material sets. Editable source: `SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend`.
- Exterior: `Scripts/import_stonebrook_exterior.sh` imports the cottage, oak, grass, rock, fencing, ground and path. Editable source: `SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend`.
- The source layouts are in original screen pixels. `UDinkArtSubsystem` discovers sorted `Content/Dink/Data/Art/*.json` environment manifests at play startup (house, yard and pig pen; other schemas use their own adapters), keeps original live actor IDs/scripts, and replaces visual and physical geometry for dressed screens. It never edits `_Generated` maps. For a greybox comparison, set `dink.ArtEnabled 0` before reloading the map (`open /Game/Dink/_Generated/Maps/L_Greybox_World`); set it back to 1 before another reload to restore art.
- Capsule radius is 28 cm (56 cm shoulders), not the third-person template's 42 cm. The old radius physically failed a roughly 61 cm furniture corner. Import tests retain a before/after swept-capsule check and now walk from spawn through the front door, outside, back inside and around the furniture without `SetActorLocation` shortcuts. Falling below the floor fails immediately.
- `UDinkWarpComponent` holds a pawn-specific in-progress guard across `TeleportTo`: overlap events occur synchronously, so setting only a timestamp after teleport allowed nested exit/entry warps and bounced the pawn back outside. Failure unwinds the guard too. A 0.75 s normal cooldown remains.
- True 3D replacement components use the `DinkAuthoredArt` tag and are skipped by sprite billboarding. Their mobility is set before runtime placement; the warp trigger's mobility must also be set before its authored location/extent override.
- Real E opened mother's menu; actual F ran fists; actual Q ran a charged fireball using a disposable, nonsaved spell fixture. Desktop routes independently passed exit, return and a long pause then walking farther inside. JSON observations, screenshots and original logs live in `Saved/Playtest/evidence`.
- Useful console commands: `dink.Player` prints real position, screen, camera, capsule and frozen-input state; `dink.Origin S001_P26` prints a live placement location; `dink.View <yaw> <pitch>` changes camera orientation without moving the pawn.
- `Dink.Art` tests load each kit and check source dimensions, material slots and LOD counts. Blender FBX mirrors Y: NW-anchored interior floor/ceiling modules require the scaled 2 m pivot offset; a missing offset caused an actual floor hole, caught by both headless walking and rendered W input.
- Unit conversion must be set in BOTH the task's FBX options and a reimported mesh's existing `asset_import_data`. Keep its source filename. Omitting the path led to a reproduced headless Slate file-picker crash; the stack showed `FReimportManager::GetNewReimportPath`. Corrected repeated imports verify every axis at centimetre scale before publishing the runtime manifest.
- The original postprocess parent shape keeps query geometry (QueryOnly, all responses Ignore, no overlaps). House exposure ownership now uses a separate `UDinkScreenExposureComponent`: the plain provider starts disabled and becomes unbound only for the first local pawn's selected AND physical indoor owner screen. Its architectural query bounds still remain local; provider containment deliberately follows owner activation, so do not test a far point against an active unbound provider to infer room scope. Keep bias−2/bloom.15/priority10/lights unchanged. Screen/possession callbacks plus a100ms game-time refresh cover controller replacement; teardown disables the provider and clears timer/delegates. Do not subclass the engine MinimalAPI postprocess component or loosen render-only art-context schema.
- Physical art uses real mesh footprints. Tagged authored actors now use complex geometry checks for hit/talk/touch/push with wall occlusion; virtual sprites and undressed actors retain original pixel rules. Tunables live in Content/Dink/Data/Interaction/authored.ini. Ground pickups use30cm beyond the body, raised pickups85cm with a45cm minimum elevation and140cm shoulder line. Twelve actual-keyboard regression cases passed, including near/far/facing-away furniture and reaching the table pie over a chair.

- Nanite material usage must be authored and saved, not merely mesh Nanite settings. The importer calls `MaterialEditingLibrary.set_base_material_usage(..., MATUSAGE_NANITE, True)` before compiling/saving every PBR material. Missing usage caused observed default-material fallback warnings in the game; `Dink.Art` asserts usage on every material of a Nanite-enabled mesh.
- Correctly imported foliage mesh bounds match source LOD0 dimensions. The initially larger bounds came from the erroneous import combining all LOD siblings into LOD0, not Unreal unioning a real LOD chain. Tests retain the strict 1 cm source/import check on `dimensions_m`, and verify three actual loaded LODs separately. `lod_union_dimensions_m` remains an independent diagnostic measured from exported source meshes, excluding collision.

- Authored foliage LODs need separate FBX imports. The companion exporter's combined FBX has sibling render meshes without an LODGroup; `combine_meshes=True` merged all into LOD0. Export local single-LOD files (`lod_fbx` in the art manifest), import LOD0 alone, then attach LOD1/2 with `StaticMeshEditorSubsystem.import_lod`. The subsystem is unavailable via `get_editor_subsystem` in a commandlet; its class default object was verified to expose the stateless import API. `Dink.Art` requires the real 3-LOD chain and originally caught this failure.

Earlier verified checkpoint (6 Nov 2026, after source-normal assertions): `BUILD OK` in 3 s, 0 warnings; `TESTS PASSED: 89/89`, 0 failures, 0 warnings in 148 s. Final report is `Saved/Automation/Report/index.html`; preserved receipts are `Saved/Playtests/Collision/final_full_suite*`. All 21 art meshes and real foliage LODs/materials/normals are covered. That checkpoint verified83 source/delivered art hashes; the current ledger receipt below covers311. Final rendered views are `Saved/Playtest/evidence/final-house-beauty.png` and `final-courtyard-beauty.png`; the physical route and interaction receipts are next to them.

Character import checkpoint (7 Nov 2026 UTC): `Scripts/import_character_art.sh` imported SK_Mother and SK_Dink with all89 bind transforms matching the original rig, four loaded LODs each and saved Physics Assets. Runtime `characters.json` preserves mother S001_P26 and maps the player mesh. The guarded native DinkCharacterArtLibrary assignment exists because Python exposes neither a writable Skeleton property nor the BlueprintSetter. Runtime NPCs use UDinkHumanoidComponent rather than the Pawn-dependent template AnimBP; the player retains its existing AnimBP and movement capsule. Skeletal export requires offscreen GPU resources; NullRHI FBX export was observed to assert in CPU-skin access. `Scripts/export_character_reference.sh` captures the verified reference workflow. Do not modify the original SK_Mannequin reference pose.

The owner supplied `/home/davisc/Downloads/audio_choices.csv`; an exact project copy is `SourceAssets/Audio/approved_choices.csv`. Selections are44SFX and28music, with punch09/bow44/axe48/bird49 rejected and notes preserved. `SourceAssets/Audio/tools/apply_choices.py` validates before patching ledger statuses and publishes `selection_manifest.json`; `Scripts/import_approved_audio.sh` imported all72 approved SoundWaves and atomically published runtime Audio/approved.json. Both MP3 deliveries and engine WAVs remain unchanged; existing licence metadata is preserved. Audio playback is implemented through DinkAudioSubsystem; focused Audio2/2, authored geometry6/6 and Art6/6 passed without warnings. Actual audio playback was verified by a5.95s isolated stereo PCM recording of approved music and real F-key swing playback. Full compiled-snapshot suite passed103/103 in177s; one warning was an engine background HTTP connectivity timeout during the otherwise clean script smoke run.

Named regression runs: `DINK_TEST_RUN=final_all_approved Scripts/test.sh` writes distinct Saved/Automation/final_all_approved and Saved/Logs/test_final_all_approved.log, plus a unique UE engine log. Run names are validated; default paths remain backward compatible. This prevents an active external Claude probe loop from overwriting these results. Preserve external edits: minimal compile compatibility fixes in DinkProbeTests.cpp renamed shadowing locals and used LexToString(FMD5Hash), without changing probe behavior.

Latest verified checkpoint (7 Nov2026 UTC): `Saved/Automation/final_all_verified/index.html` records103/103 passing, no failures, one engine LogHttp connectivity warning. All930 smoke entry points still have0errors/stalls (27 intentional idle-loop caps). Exact Core save regression, ordered Ch1/Ch2 chain and Audio checks also pass separately. Ch2's current probe baseline permits a partial4/6 route; this is NOT evidence of a complete Terris playthrough. Foreign Claude changed only its forward KiteFight tactics after compilation; production source hashes remain identical to the validated build. The scope/hash receipt is `Saved/Playtests/ApprovedAudioAndHumanoids/current_source_scope.json`.

Save/load ordering: `UDinkSaveSubsystem::ApplySnapshot` refreshes the physical cached Greybox screen immediately after pawn transform and BEFORE `OnSnapshotApplied` narrative callbacks. The prior0.25s cache delay invented exits625->1->625 and overwrote restored exit timestamps. The native refresh changes the cached pointer/audio notification only. New `Dink.Core.Save.ScreenCacheBeforeNarrativeRestore` checks the physical screen, exact facts/clock/exits at load and normal clock advance/no false exits on the first tick. Synthetic screen fixtures require both a registered first player controller and a valid BoundsWorld broad phase, in addition to their layout corners.

Final rendered receipts: `interactions-after-private-final/results.json` passed12/12; `dink-private-model` contains realW exit/yard/return/postwarp routes and animation frames; `npc-collision-final` contains12 position-linked mother frames; `audio-private-final` contains PID-verified mixer PCM and playback logs. These are under `Saved/Playtest/evidence`. The latest host test game is left open with audio; its PID/window/log/screenshot receipt is `final-host/launch.json`. Private Xvfb and the owned temporary audio sink were cleaned up. `Saved/Art/ledger_verification.json` verifies311/311 art/audio sources with no hash errors.

Next-art inventory: normal courtyard439 no longer has source cards. Its remaining original placements are vision1/2 fire/ruin effects and scripted mourners/duck. Pig pen407 is the strongest next normal-play priority: five live pigs P02/P05/P06/P07/P11 plus reusable fence/meadow/grass/rock kit. Neighbor471 can reuse the environment kit;438 needs a pillbug;440 needs a taller house, tools and Quackers. Burning/ruined courtyard variants remain required for story3+.


Pig-pen stage checkpoint (7 Nov2026): environment import407 and own-rig pig import succeeded in `/tmp/dink-pigpen-stage`, with separate source/build/save trees and only Content/SourceAssets/ImportData symlinked. The user-focused host game remains untouched and still uses the prior house/audio build. Stage `pig_geometry_committed_verified` passed8/8 and `pig_art_runtime_verified` passed9/9, zero warnings. These cover proposed-facing compound OBB/final-pose safety, normal-brain heading, fast human/pig locomotion, original five pig actors and death/save behavior,26bones/3LODs/4clips/4materials and actual blendspace endpoint weights. See Scripts/ART_PIPELINE.md and SourceAssets/Art/PigPen/README.md. Rendered after-route and Milder humanoid integration are pending at this checkpoint. Earlier7/8 geometry runs are superseded by the committed-heading/final-pose correction. Never replace live shared libraries while the owner is playing; finish staged verification first.


Final pig-pen checkpoint (7 Nov2026 UTC): the isolated build passed112/112 tests with zero warnings in264s. The durable report is `Saved/Automation/pigpen_all_verified/index.html`; `Saved/PigPenStage/focused_results.json` links focused checks, initial failure and final scope. All661 runtime Data files were hash-identical immediately before/after the clean full run. `final_source_audit.json` records zero compiled-source mismatches; only the read-only QA Python fixture evolved. Root project DLLs and its original live game remained untouched.

The first full run passed111/112: only generated director-status CSV parity failed after an external story sync changed vocabulary counts/spelling. Preserve that receipt in `Saved/PigPenStage/pigpen_all_vocabulary_drift`. Updating the factual status CSV in root/stage, then rerunning Vocabulary and the full suite, passed using the same binary. Future external story conversion can alter the shared Content data while a staged source tree is frozen; record before/after Data hashes rather than claiming all inputs stayed frozen without checking.

The final Art12 includes source/import scale/LODs/materials, own26-bone pig and original five actors/death/save, Milder script attachment/size2 grounding/save-facing/fast cadence, and actual visible food targeting. Grain bottom0.6cm clears maximum opaque soil0.496cm. Feeding occlusion uses visible kernel bounds near0.75cm rather than the legacy actor root60cm; reach/heading remain horizontal. Regression proves an overhead rail that falsely blocked the old ray does not block floor grain, while a true occluder and hidden/fresh food are rejected correctly.

Rendered acceptance is `Saved/Playtest/evidence/pigpen-final-focused/final-qa-receipt.json`: fresh actual sack pickup, explicitly recorded debug travel to407 outside the west gate, then actualW gate traversal and realF/original Milder scene passed. Pawn ended at299.654,250.056, pig_story1, input unfrozen. Camera-only close inspection restored offset/probe/FOV. The separate earlier `pigpen-after` receipt preserves the complete uninterrupted house/yard/north/gate route (controller interruption resumed from the same pawn). Do not describe the final debug-travel fixture as an uninterrupted walk. A distinct live nibble/feed-start was not observed during the final throw; the native actual-pig/ground-grain activation test passes.

Final shots show continuous Milder neck/armor, recovered pig skin detail, no green soil gaps and no towering neighbor sprite cards. Remaining neighboring ground/white terrain is greybox; house fire/ruins, wider regions, further creature/NPC art, coarse close-range pig pores and clean armor surfaces still need work. Source delivery hashes pass374/374, preserving all124 audio records. Candidate status remains appropriate. Private renderer21339 exited cleanly and its owned Xvfb20868 was stopped; the original host4028335 was verified alive. The separate visible final session is PID45497, title `DinkRemaster_Art_Test`, with approved audio. Its receipt is `Saved/Playtest/evidence/pigpen-final-host/launch.json`; original host4028335 and prior desktop focus were preserved. Do not rebuild this staged session's loaded DLLs while the owner is using it.


Stonebrook fields work in progress (7 Nov2026 UTC): `/tmp/dink-stonebrook-fields-stage` has an independent Source/build/save tree and LOCAL `Content/Dink/Data`; asset directories reference the permanent project. Do not publish its new runtime manifests to the live pig-pen stage without isolating that older session's Data first. Its older Core lacks retained-Low and mixed feeding-row fixes. Preserve both existing user game processes and never rebuild their loaded DLLs.

The current deferred-facing safety build passed31 focused tests with zero warnings: Audio2, Geometry9, Art13, field-water1, CoreSave5, NarrativeSave1. Receipts are under `Saved/StonebrookFieldsStage/fields_*_deferred_verified`; Audio is also `Saved/Automation/audio_decisions_reverified`. The actual438 P03 northwest turn deadlocked because rotating the large physical body at its starting point overlapped the pond ring even though the intended original one-pixel movement could proceed. A clear current-facing step may now retain its physical yaw until the desired endpoint-facing clears; logical AI direction/target remain original. Both physical poses stay clear. Optional saved authored-facing quaternion preserves the safe first step across save/load; older saves still use their established path. Regression first proved six failures on the old runtime, then passed exact two-step/save restoration and strengthened repeated fence-stop checks.

Fields471/438 preserve original Low water collision while replacing old visual/solid terrain with source-fitted land, banks and noncolliding water. Final471 reimport has pine22444/9004/6764 triangles with all560 bough cores at every LOD, and three aquatic plants grounded at waterZ=-80cm. Source has207 specifically documented shoreline/sliver/water validation exceptions and4 retained warnings; do not describe this as a raw zero-error source validation. Existing67 environment packages remain byte-identical. Pillbug uses its own43-bone rig/three LODs, no feeding clip; mixed-creature rows must not reset the real grain offset. All243 new Fields/Pillbug ledger rows remain candidate; global617 hashes pass with all124 prior audio records unchanged.

HandBindingV2 imported only new `SK_Dink_Hands` into `/Game/Dink/Hero/Refinements`, four LODs and the existing89-bone-compatible skeleton/material references. Source verifier proves all outside-hand positions/weights, UVs/materials/rest transforms unchanged; original99 character/creature/shared packages hash-identical. Close thumb-web folds remain candidate polish. New fist animation import and runtime presentation are still in progress; do not claim visible F-key animation or full-suite/render acceptance yet.

The CLI-only `-DisableUnity -DisableAdaptiveUnity` claim could not be reproduced during the house-wall regression rebuild: those flags, the additional `-NoUBTMakefiles`, and a temporary stage Saved XML still produced failing unity files (Inside, NAME_Main, FEnv collisions). The Saved XML was restored. Explicit `bUseUnityBuild = false; bUseAdaptiveUnityBuild = false;` in the isolated stage Editor.Target.cs produced126 individual compile/link actions. That stage-only compiler-setting divergence is intentional and its original target bytes are preserved at `Saved/HouseWalls/DinkRemasterEditor.Target.before.cs`; do not claim stage/root target-source identity. Do not rewrite unrelated gameplay files or the engine to work around this build issue.

Hero fist source import now passes in the isolated fields stage: `Scripts/import_hero_animation.sh` imports only new `AN_Dink_Fist` and publishes optional `Art/hero_actions.json`. The verified source mesh and clip each have89 bones/tracks; the unchanged shared `SK_Mannequin` Skeleton contains161 bones. `InspectCreatureAnimation.bone_count` measures the latter. Validate exact89 source/mesh track-name equality AND unchanged full161 reference poses/package hash, rather than falsely requiring the shared Skeleton to contain89. The first rejected import and diagnostic are preserved. Native duration0.400000006s, root motion0, finite poses, scale error0.0000171, matching endpoints; existing99 packages still byte-identical. Runtime F-key playback and save/damage-timing checks remain pending.

Post-import checkpoint (7 Nov2026): final field revisions, new hand mesh and imported fist source pass Art13/13 with zero warnings in16s, `Saved/Automation/fields_final_imports_art`. The global source ledger now verifies637/637 rows, including20 hand/fist candidate rows; all124 audio records remain unchanged. Actual fresh-start Space/W house exit and return both pass with the new hand mesh, no debug travel/fact/actor setters. Durable routes/three screenshots/receipt: `Saved/Playtest/evidence/fields-final/hand-house-receipt.json`; final screen1, map302.939/384.801, radius28cm, movement not ignored. Imported pillbug BC/N/ORM payloads are pixel-identical to source and their sampler/color-space/channel settings are correct (`fields-material-diagnostic` beside the routes). Lighting buffer diagnosis and rendered pond-edge chase remain active; do not claim those passed yet.

At11:10UTC both earlier host PIDs4028335 and45497 were independently absent from authoritative process listings; this work did not signal/close them. Do not assume old sessions are alive from their launch receipts. The new owned private QA process is separate; coordinate its clean close before rebuilding that stage. Launch a fresh visible verified test session after the current runtime/art gates. PineRefinementV3 source development is isolated from the frozen current Fields inputs because the current preserved-whorl pine still has visibly angular, sparse boughs.

## Photoreal feed sack V3 source delivery (8 November2026)

Source-only art/photoreal-feedsack-source, /home/davisc/Work/DinkFeedSackSourceDelivery, basefbfe083 afterBasket15. Approved source4a51bdb/exportf559cf4/actualFBX03a2b2f and original422_12/s1-sack provenance in SourceAssets/Art/Stonebrook/Refinements/PhotorealFeedSackV1. Grain/feed pickup S001_P52, distinct from decorativebasket. Two materialslots/IOR1.46+1.5/specIOR.22 retained; nativeF0mapping unapproved.19644triangles,3fresh2048maps,exactoriginalbounds/pivot/authoredUCX,guide0errors2retainedwarnings; actualFBX/UV/normals/materialID/hull and packedreopen/fullUVchecks pass.88newcandidateledgerrows preserve1471priorrows/audio483rawbytes. See Docs/Verification/PhotorealFeedSackSource. NoContent/native/runtime changes; actualgameacceptance pending. Localcommit requested; independentreview required beforepush. CandleV3sourcefinish remains QA-only/unapproved.

FeedSack finalsourcechecks: fullaudit2066binaryfiles/312Python/22shell/1559ledgerrows,0missing/hasherrors/secrets; sequentialmetadataauditPASS. All88newledgerpaths staged; original1471rows/483audio rows retainrawbytes. Exact75approvedpayloads unchanged. Twoinheritedtrailing-space lines explicitlyretained forbyteidentity, see whitespace_qualification.json. No engine/cache/native/runtimefiles added. Standalone copiedUV/FBX/source+exportpackedchecksPASS. Localcommitawaitsrootindependentreview beforepush.

## Photoreal candle source delivery (8 November2026)

Source-only art/photoreal-candle-source at /home/davisc/Work/DinkCandleSourceDelivery, base0c94a18 afterFeedSackPR17. Approvedsourcea6eb652a/export51e5dcc in SourceAssets/Art/Stonebrook/Refinements/PhotorealCandleV1; existingaddedcandle, no directoriginalspriteattribution.38source/41exportpins unchanged; separateNativeLODExports3FBXfiles eachsinglemesh4870/2434/1218tris,2slots preserved throughactualFBX. ImportLOD0alone/attachLOD1/2, nevercombine historicalsiblings. OriginalLOD0bounds/pivot/authoredUCX0 retained; LOD2minZ -4.11micrometres qualified. NativewaxSSS/flame/LODdistance/rendering remainunapproved. DefaultLitBC/N/ORMalone doesnotprovewaxSSS; BlenderwaxIOR1.44/spec.30/SSS.12/.008m retained. Sourceguide0errors2warnings, completeUVLOD0zerooverlap/LOD2fourtinyoverlaps0.0057percent retained withinclass.2percent. Source/exportpackedreopen andcopiedperLODFBXchecksPASS.94newcandidateledgerrows preserve1559prior/audio483rawbytes. NoContent/runtime/native edits. Localcommitonly beforeindependentreview; seeDocs/Verification/PhotorealCandleSource. PiefirstdraftQA-only stillpale/underbaked/notapproved.

Candlefinalsourcechecks: fullaudit2099binaryfiles/345Python/22shell/1653ledgerrows,0missing/hasherrors/secrets; sequentialmetadataPASS. All94newledgerpaths staged/hashmatching andall87approvedpayloads byteidentical; noignored/cachefiles. Gitwhitespacecheckclean. Standalone copiedsource/exportpackedreopens/fullUV andall3singleLODFBXroundtripsPASS. Rootindependentreviewbeforepush; thisisnotnativewax/flame/gameacceptance.

## Native feed sack checkpoint (8 November 2026 UTC)

PhotorealFeedSackV1 changes exactlythe assetrow andS001_P52 mesh strings; original scripts/transforms/WickerBasket/collisionpolicy unchanged. Sixnewpackages19,644tri/14,852jute+4,792cord/three shared2kBC/N/ORM retain original72.283x55.469x75cmbounds andone65x52x75UCX, which is verified but not active complex-as-simple geometry. Read-only material-binding API resolves actual imported names, not dense polygon-group IDs. Nativeactualspecular.19231277704238892/.2199999988079071 matchesF0 targets forsourceIOR1.46/1.5 andIORLevel.22.

Full152/152native0testwarnings517.259s,9240inputsunchanged/40oldscopedsavesstable;490PythonPASS. Freshpublishedverify needsno authorreceipt; publisherdefault/--applywritesnothing9256pins. Sourceaudit2117binary379Python22shell1664ledgerPASS;1658priorrawledgerrows/audio483preserved. Afterfull, onlyproductionroutehelperbudget changes100attempts/max.8sW versus35/.24 tosupportacceleration; actualsamegamekeyboardcontinuation+ASTequivalence and490Pythonrerun validateit. NoC++/Content/importtool/module changes afterfull; Docsstatusseparatelyqualified.

RealWpickup/removedspace/exit-return/originalfeeding andactualprivateSaveSubsystem APIloadPASS (not save-machineUI). TwoRootprivategames282208/293200 closednormally, each6931runtimepinsunchanged. Defaultroomcorner remainsdark; nativeassetappearance inspectedunder separatelylabeledtemporarylightchange, fullyrestored. Nofinalhouse lighting/hero/roof/exterior approval. Immediate re-exit while stilloverlappingarrivaldoor is anexistingusabilitybug discoveredbytesting; separateisolatedCorefix inprogress, notpartofSackassetcode. Allrawfixturefailures remainrecorded. SeeDocs/Verification/PhotorealFeedSackNative.

InstalledPython StaticMeshComponent hasget_world_transform, notget_component_transform. GameplayStatics.BeginDeferredActorSpawnFromClass isnotPython-reflected despiteC++UFUNCTION; do notassumethat C++Blueprintinternals arePythonAPI. Rootdiagnostic usedonlyoneexistingownedlightandrestoredoriginaltransform/intensity/radius, savingnoassets.

## Shared Stonebrook source-only checkpoint

Branch art/shared-stonebrook-vista-source baseb9a3d74 publishes379 frozen house440/willow/terrain/reed source files and379candidate rows (1664→2043), prior483audio raw records unchanged. Source-only: no Content/runtime changes; raw guide errors/warnings,16deferred studies and560existing-reference exclusions retained. Native collision/warp/story/LOD/material/world composition remain unapproved. See Docs/Verification/SharedStonebrookVistaSource and source combined catalogue; IndoorRoofV6 is blocked and excluded.

## Deliberate doorway re-exit (9 November 2026 UTC)

Arrival can already overlap the return trigger while the warp guard suppresses BeginOverlap. Ordinary player movement now retries an enabled walk_in door/exit at the existing0.25s poll, using only this frame's OnCharacterMovementUpdated acceleration/location and retained approach direction. Idle, away, frozen, dead, stale, unpossessed and NPC cases cannot retry. Existing0.75s cooldown, nohard suppression, atomic recursion guard, other warp types, spawn and collider data are unchanged. Weak pawn bindings are removed on rebinding/deinitialization.

Editor and standalone Development Game builds pass with zero compiler warnings. Root combined153/153 native tests pass with zero test warnings in498.917s,9,241inputs unchanged and51inventoried older saves stable. Independently reviewed author-stage real W proof confirms idle overlap does not bounce and deliberate re-exit works once without walking clear. Tangent/zero-approach/two-blocked-destination native cases are not claimed as tested. Source-only PR21 reconciliation changes authoring/status/ledger only; all runtime inputs retain tested bytes. SeeDocs/Verification/DoorOverlapRetry.
