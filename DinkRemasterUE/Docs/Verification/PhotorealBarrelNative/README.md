# Reviewed photoreal barrel native iteration

The Blender barrel from source PR13 has passed a fresh guarded import and separate-process saved verification with the independently reviewed **83-test barrel framework**. Guarded publication then changed exactly three mesh references: the house barrel asset row and decorative `Barrel1`/`Barrel2`. Original transforms, identities, collision flags, all other furniture, lights and warp data remain unchanged. All267aggregate Python checks, the sequential full source audit and postpublication native147 suite pass. Actual in-game barrel appearance remains pending.

## Current evidence

| Check | Result and precise scope |
| --- | --- |
| Reviewed tool binding | All four production SHA256 values match the scratch handoff and [independent tool review](Review/independent_tool_review.json) |
| Native preflight | Pass, 20.20s; all recorded input scopes unchanged: [terminal](ReviewedNative/Attempt01_preflight/terminal.json) |
| Native import | Pass, 54.74s; only five new candidate packages created; protected Content/Data/source/art/tools/modules unchanged: [receipt](ReviewedNative/Attempt02_import/receipt.json), [terminal](ReviewedNative/Attempt02_import/terminal.json) |
| Fresh saved verification | Pass, 42.57s; no changes in any recorded scope; package bytes identical to import: [receipt](ReviewedNative/Attempt03_verify/receipt.json), [terminal](ReviewedNative/Attempt03_verify/terminal.json) |
| Exact geometry/UV matching | All 16,648 source triangles matched bijectively and cyclically; maximum position delta 0.000003815cm and UV delta 0.00000002981; source geometric fronts agree |
| Actual retained hull | One native transformed eight-vertex box, exact source match with zero vertex delta; source dimensions 75×75×100cm; [native hull diagnostic](ReviewedNative/Attempt03_verify/UCXDiagnostics/SM_Barrel_Oak_01.json) |
| Original native baseline | Confirmed original 10,472 triangles, two Oak/WroughtIron material slots, original bounds and complex-as-simple policy |
| Material and pixels | One direct BC/N/ORM graph plus specular0.35, exact native property IDs5/6/7/8/10/18, no hidden extra inputs; all three exported Texture.Source RGB images equal frozen source pixels |
| Source-file ownership | All four native filename getters (FBX+3PNG) resolve to this selected source bundle and match hashes |
| Runtime publication | Applied exactly3mesh strings, one asset row and two decorative instances: [applied receipt](Publication/applied.json) |
| Full native suite after publication | **147/147 pass, zero warnings/errors,545.19s**; all8,956pinned inputs unchanged; [raw report](Full147/raw_report.json), [verification](Full147/verification.json), [independent check](Full147/independent_check.json) |
| Isolated save scope | Ten inventoried earlier probe slots retain their hashes; ten new chapter slots stay in the fresh test UserDir. This is not an exhaustive owner-save inventory. |
| Pure guards | 83/83 barrel guards and all267aggregate Python tests pass: [barrel log](Review/python83.log), [aggregate log](PostPublication/python267.log) |
| Source/metadata audit | Sequential full audit passes1,990binaries/262Python/22shell/1,414ledger rows, zero errors or secret flags: [report](PostPublication/source_audit.json) |
| Native ledger | Five new candidate rows; all1,409prior raw rows and483audio rows retained: [append receipt](ledger_append_receipt.json) |

The raw before/after inventories accompany each reviewed native attempt. [Current summary](current_summary.json) records package hashes, native metrics, tool versions, source filename records, exact publication bytes and outstanding work. The aggregate Python result is its own recorded run. The full native suite is a separate completed run. No game-camera result is inferred from either NullRHI tests or import commandlets.

The new mesh keeps the original ground-center pivot/bounds, source normal import flags, generated MikkTSpace tangents and full Nanite triangle fallback. Actual native per-corner shading-normal arrays are not exposed by the installed Python wrapper; saved import/build flags and actual loaded geometric fronts are separate evidence. Complex-as-simple remains the active query collision policy. The authored UCX box is retained and verified; it must not be described as the active query source.

The iron is intentionally metallic: frozen ORM uses neutral AO R255 and variable metallic B0..240, with wood zero-metal regions. Native Texture.Source is compared pixel-for-pixel to these maps; the furniture pipeline's all-dielectric B0 constraint is not reused. Materials remain direct BC/N/ORM plus a direct specular0.35 constant with exact hidden property checks.

The reviewed contract/importer/publisher are self-contained, scoped derivatives of the proven furniture framework, plus custom-module byte guards and safe native indexed geometry checks. They do not dynamically import or modify the furniture contract. Import refuses existing destinations. Unpublished verification retains its successful import receipt chain; future published clones can verify their current entry-pinned five packages without private author Saved receipts. Fresh-published publisher checks, including `--apply`, are zero-write with no scene-data approval; that future clone path is covered by pure guards, but this barrel's actual relocated-clone run remains outstanding.

## Preserved earlier continuation

The pre-existing [README](HistoricalContinuation/README.md) is preserved byte-for-byte. Its seven barrel guards/191 aggregate tests and its original `Saved/BarrelNative` receipts describe an **earlier, different tool version**, not the reviewed version above. [Historical receipt paths](HistoricalContinuation/receipt_paths.json) and copied small receipt/terminal files identify that evidence without relabeling it.

The other author explicitly handed ownership back and permitted exact unpublished candidates to be archived. The five earlier packages, three tools and one test remain in the external `/home/artist/Work/DinkQA/BarrelNative/ContinuationCandidateArchive_20261108` archive and the owned `Saved/BarrelReviewed/PriorContinuationCandidate` copy. The [archive manifest](HistoricalContinuation/archive_manifest.json) binds their hashes. No package payloads are duplicated into these docs. Root then removed only those exact unpublished files and performed the reviewed fresh preflight/import/verify chain. Earlier successful receipts do not authorize different tool hashes or replacement package bytes.

## Remaining gates

The postpublication native147 suite passes with all enumerated tests successful and its full recorded input set unchanged. Actual game-camera lighting/material inspection, collision/door/reach routes and screenshot acceptance remain separate parent-owned work. Five native candidate ledger rows have been appended with prior bytes preserved; commit/LFS/PR delivery is pending at this checkpoint. Source/art approval and native saved-asset verification do not establish final starting-house photorealism, driver stability or whole-game art completion. The protected visible sessions and engine installation remain untouched by this documentation task.

## Qualified audit failure

The [first source audit](PostPublication/parallel_audit_false_failure.json) ran while synthetic publisher tests were creating temporary fixtures below `Scripts/tests`. It reported four fake temporary tool files as invalid Python; those fixture bytes intentionally are not executable source. The [sequential audit](PostPublication/source_audit.json), after the passing tests cleaned up their temporary folders, reports zero errors without a product-source edit. The raw failed report is retained; it is not presented as a game or production syntax failure.

## Rendered iteration

The private45FPSsession showed both new barrels with retained wood/iron/head-board detail. [Bounded collision probe](Render/fixture_results.json) used explicit setup positions followed by realW capsule sweeps: contact atmap164.017/120, then departure tomap254.506/120. All6,914recorded inputs stayed unchanged; game171912quit normally and owned display171906stopped. This is not universal collision coverage.

![Native barrel close view](Render/barrels-close.png)

The old wall-cutaway implementation still hides the nearby wall and reveals an outside-floor blue strip in this exact photo fixture. That separate camera case is handed to the opaque-wall fix session; it is not a new claim that every floor angle is repaired. Oldhero/roomlighting/vista remain unfinished. The combined door-loop proof is separately recorded under CombinedHouseRender.

## Published-state verification and source recipe limitation

A new published-state native process passed in44.17s with unchanged source/tools/art/Data/Content/modules. It retained all five entry package hashes and all four native source paths. See [receipt](PublishedVerify/receipt.json) and [terminal](PublishedVerify/terminal.json).

The immutable source bundle contains the original bake recipe. A later independent bake investigation identified stale Blender NodeLink handles during shader restoration; the original barrel bake completed, but the recipe has a reproducibility risk. Its approved baked payloads are independently verified and unchanged. A corrected successor recipe is being prepared in a separate QA folder; do not overwrite frozen source or relabel earlier receipts after a code change. This is an outstanding authoring-tool issue, not proof of an invalid current texture payload.
