# Hero native inspection bridge verification

The editor-only `DinkHeroInspectionLibrary` exposes read-only Skeleton, skeletal LOD and texture inspection. This delivery adds three source files and private ImageCore/RHI dependencies. It changes no gameplay, assets, production avatar mapping or Engine configuration. See [API.md](API.md) for contracts and unavailable states, and [validation.json](validation.json) for source hashes and measured results.

The isolated `test/hero-native-inspection` checkout at `/home/artist/Work/DinkHeroNativeProof` uses master24 `910cb599` as its base. Newer master27 audio/probe changes are outside this frozen verification snapshot and must be preserved during later integration.

## Results

| Check | Result |
| --- | --- |
| Editor build | Passed, 151 actions, 880.05 seconds, no compiler diagnostics |
| New inspector automation | 2/2 passed, no test warnings |
| Existing reference Python V2 | Clean exit, exact old/new 89-bone mesh bind agreement, shared Skeleton 161 bones |
| Source and built reference geometry | Both available: 23,423 vertices, 95,064 indices, maximum four weights; no invalid BoneMaps, nonfinite values or zero normals |
| Full native suite | 156/156 passed in 1,252 seconds; 140 without recorded warnings, 16 with environment warnings |
| Standalone Development Game build | Passed, 85 actions, 760.14 seconds, no compiler diagnostics |
| Source audits | Full and metadata passed: 2,444 binaries, 461 Python files, 22 shell files, 2,182 ledger rows; no errors or secret flags |

Fourteen full-suite tests recorded SDL/Wayland initialization warnings; two recorded HTTP connectivity timeout warnings. No warnings were suppressed and no assertions, deadlines or floors were changed. Both builds retained the action-result-store failure footer; successful cache storage is not claimed.

The full native process exited zero and strict postguards passed. Its Saved-only postprocessor then failed because its plain JSON reader rejected Unreal's UTF-8 BOM. The original supervisor therefore recorded child exit one. [full_report_readback.json](full_report_readback.json) is a separate BOM-aware derivation bound to the raw report hash, preserving both outcomes. There was no full rerun or replacement of the failed wrapper receipt. The separately reviewed Game prerequisite accepted these exact receipts.

## Protection and limits

All guarded Root/source/package/save scopes remained unchanged. Seven owned Editor DLLs and six module metadata files retained their bytes through the Game build. Actual focused/reference/full module maps identified the seven owned libraries; a Game build does not provide runtime module-map evidence. Root protection covers seven DLLs, six metadata files and scoped inventories of 51 preceding and 61 mid-bridge saves; it does not claim every unrelated user save directory.

The private mount namespace presents host files read-only, exposes only this owned checkout and private temporary/configuration directories for writes, and keeps HOME unchanged. Shared host Epic files are a bounded observation with explicit unavailable entries and no atomic whole-host quiescence claim. Other projects and user games were neither stopped nor controlled.

The existing texture Source is available, but platform mips are unavailable under NullRHI. This is not a candidate float-format, signed-normal, shader or GPU-fidelity result. No new hero import, material appearance parity, final character, LOD chain or scene acceptance is claimed. The frozen V267 hero remains a diagnostic candidate with unfinished visible wardrobe details.

## Preserved failures

The first Editor link failed for missing RHI symbols; only the private dependency was corrected. A later build stopped with status 143 for an unproved cause. A default-namespace detached launcher did not survive startup. The eventual reviewed host-level recovery succeeded. The first Python reference read returned `compiling_unavailable`; V2 completed already-pending compilation using the existing `InspectRig` barrier before hard readback assertions. These failures, and the later BOM postprocessor failure, remain in owned `Saved/HeroProof` receipts; none is relabeled as a clean original pass.

Raw build, private environment, full-suite and scoped protection records remain in the same checkout under `Saved/HeroProof`. These local records are not portable CI artifacts; the committed summary and source hashes describe their bounded conclusions. The two native regression tests exercise synthetic section remapping, four influences, UV seams, negative normals, invalid mappings and actual texture byte/settings/dirty-state preservation.
