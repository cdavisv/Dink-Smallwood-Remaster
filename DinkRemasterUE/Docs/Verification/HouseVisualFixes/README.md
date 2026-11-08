# House exposure ownership and perimeter floor repair

The house camera could leave its exposure box while Dink remained inside. Returning through the real door then removed the authored −2EV bias, and rotating the camera changed the room's exposure. `UDinkScreenExposureComponent` now owns the original plain postprocess provider: it activates only when the first local pawn's selected **and physical** indoor screen match its owner. Screen/possession callbacks and a 100ms game-time refresh cover replacement controllers; teardown disables the provider and removes its timer/delegates. Camera, lighting values, query bounds, collision and gameplay remain unchanged.

Grazing rays also escaped beneath the northern floor perimeter before reaching the existing underfloor sheet. PerimeterSkirtV1 adds one closed, 96-triangle rim inside the recorded floor contour, from Z−18 to −0.2cm. It reuses the existing dark material and has no collision, navigation or overlaps. Its separate owner-screen context hides it outdoors, including hidden shadows/GI. The original 56 floor modules and UnderfloorV1 remain unchanged.

These are tested visual bug fixes. Photoreal furniture/hero candidates are not imported in this checkout. The dark room center/hero and bright distant outdoor terrain still need lighting/material review.

## Before and after

The exposure views are separate real keyboard returns, with their actual positions recorded. They are **not** an exact-camera pair. Both cameras lie beyond the former volume's blend range.

| Before: room override absent | After: room override retained |
| --- | --- |
| ![Clipped window and wall after returning](Evidence/GuardedRepeat/actual-return-settled.png) | ![Window and wall detail retained](Evidence/ExposureRender/Route/actual-return.png) |

The following floor pair has identical pawn/camera XYZ, rotation, FOV, arm, offsets and framing to a tolerance of 0.000001cm. The bounded ROI changes from 23 blue pixels to zero. All seven original escaping rays intersect actual loaded native skirt geometry. Normal pitch −10/−18/−25/−35 views also contain zero blue pixels in the measured floor ROI. This does not prove every possible world position or angle.

| Before: visible sky through perimeter | After: separate fitted rim |
| --- | --- |
| ![Blue perimeter slivers](Evidence/Baseline/north-floor-right.png) | ![Perimeter closed at the exact same camera](Evidence/SkirtRender/NorthFixtures/north-exact.png) |

[Exact native ray/pixel proof](Evidence/SkirtRender/exact_native_ray_and_pixel_proof.json) records the camera contract, pixel counts and native triangle intersections. The fresh-start control has 1.5mm additional floor clearance and is reported separately; it changes 21→0 pixels under the same −2EV policy.

## Verification

| Check | Result |
| --- | --- |
| Native build | Succeeded, no warnings; isolated project, unchanged engine |
| Before exposure regression | 1 failed test / seven expected ownership-state failures |
| Final exposure lifecycle | 1/1 pass, no warnings |
| Focused Art / Import | 24/24 and 12/12 pass, no warnings |
| Actual skirt owner/geometry/physics regression | 1/1 pass, no warnings; 56 floors preserved; 85 camera occluders retained |
| Full native suite | **145/145 pass, no warnings, 450s** |
| Full freeze | **8,852 files unchanged**; ten new probe saves only in a fresh isolated UserDir |
| Python | **116/116 pass**, including 25 skirt source/publication/geometry guards |
| Native skirt import and fresh saved verification | 48 vertices / 96 oriented source triangles / 96 Nanite triangles / one LOD; no collision or navigation |
| Protected import inputs | All 4,754 existing package files and 668 Data files unchanged; only one new package |
| Runtime publication | Only the new owner-context JSON added; original stonebrook/Vista/Underfloor unchanged |
| Rendered gameplay | Actual W exit/return and eight returned camera angles pass; all three contexts hidden/NoCollision outdoors |
| Capture freezes | Exposure 6,890 / skirt 6,893 files unchanged; both games quit normally; owned Xvfb released |

[Full native verification](Native/Full145/verification.json), [raw full report](Native/visualqa_full145.json), and [before/after hash maps](Native/Full145/before.json) retain the precise scope. Ten chapter receipts are in [Native/Chapters](Native/Chapters); completed step counts are 47/6/11/12/3/3/8/3/6/7. These are the enumerated automated routes, not an exhaustive manual world playthrough. The healer trace offers $13 for the recorded injury and executes the original “Get healed” dialogue.

All 1,322 prior ledger rows, including 483 audio rows, retain their original raw bytes. The 16 added source/native rows remain **candidate**. See [append receipt](Receipts/ledger_append_receipt.json). The frozen source guide retains one explicitly authorized `COLLISION_MISSING` error and zero warnings because this mesh must be render-only; the raw guide report is in the source bundle.

## Reproduce the bounded offline check

From `DinkRemasterUE/`, with NumPy and Pillow installed:

```sh
python3 Scripts/Playtest/verify_perimeter_skirt_capture.py \
  --qa-root Docs/Verification/HouseVisualFixes/Evidence \
  --out Saved/VisualQA/reproduced_skirt_capture.json
python3 -m unittest discover -s Scripts/tests -v
```

The offline checker has no Unreal/desktop access and refuses to overwrite its output. `read_perimeter_skirt_geometry.py` exports actual source triangles/world transforms from a verified owned native session. `visual_qa.py` verifies private display, PID/project/log receipt and supports distinct labels/readbacks. Use `private_qa_session.py` only after obtaining the private display lease; never send it to a foreign window. `pin_visual_scope.py` records native source/Config/Content/ImportData/module scope.

For fresh native verification, use `Scripts/build.sh` and `Scripts/test.sh Dink` with an isolated UserDir and filesystem DDC as documented in the playtest guide. The recorded run used two CPU cores and no engine edits. Do not rebuild or alter a checkout while any process has its libraries/assets loaded.

`import_perimeter_skirt_surface.py` supports guarded `preflight`, `import` and `verify` via `DINK_PERIMETER_SKIRT_MODE`; reports must be under the owned Saved tree. `verify` is appropriate for a normal LFS clone with saved assets. Import refuses existing destinations. `publish_perimeter_skirt_surface.py` is check-only by default and atomically adds only its context on `--apply`, after fresh saved verification. Never overwrite a published or foreign asset to recover a partial import.

## Raw failures and qualifications

- [Original failing exposure report](Native/exposure_before.json) and [before-test source](RawBefore/DinkScreenExposureTests.cpp) are distinct from the final lifecycle test.
- [Invalid exact-old-return fixture](Evidence/ExposureRender/FailedMatchedFixture/fixture.json): direct teleport to the old returned position retriggered the real exit warp. Its image is excluded from matched-camera evidence. The successful north fixture is safely away from the warp.
- [Initial normal-convention assertion failure](Evidence/SkirtRender/RH_convention_diagnostic_failure.json): UE uses CW front in its left-handed basis, so its geometric front is the negative RH cross after Y reflection. Source-oriented triangle identity and one-sided material/import flags are verified. The installed Python wrapper has no stored-normal getter; no stored shading-normal claim is made.
- [Quality queries](Evidence/ExposureRender/render_quality.json) and [148 room GI flags](Evidence/ExposureRender/room_gi_flags.json) rule out obvious disabled-GI/low-quality flags. They do not establish Lumen surface-cache/SDF coverage or a finished grade. Actual default exposure bias was not queried; installed engine default is +1.
- Nearby legacy cards and white distant proxies remain unfinished art. The east-boundary fence mismatch is qualified because native hit-component identity could not be read through protected Python fields. The west garden-fence route failed because its fixture crossed a visible fence; no collider deletion was applied. See the [issue ledger](Evidence/issue_ledger.json).

The renderer used serial RHI/submission diagnostic flags. Healthy captures do not establish a general engine/driver crash fix. The live SurfaceDelivery game, foreign movement checkout, engine installation and shared source/audio originals were untouched.
