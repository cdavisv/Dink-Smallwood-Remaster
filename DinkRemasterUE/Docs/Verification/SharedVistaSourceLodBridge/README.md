# Read-only source-LOD inspection bridge

This isolated checkout is based on official master23 fb2ce8d3e72be5e8d052c4fff7767fe3c690e394. The change adds only a BlueprintPure DinkImport getter, its declaration and a metadata-only automation test. It returns detached JSON with schema `dink-static-mesh-source-lods/1`, mesh validity and per-source-model LOD index, original filename and the engine-resolved filename. It uses public `GetSourceModel` and `UAssetImportData::ResolveImportFilename`; it does not import, build, dirty or save a mesh.

`Dink.Import.Inspection.SourceLODRecords` covers null/empty input, three source models including empty/relative/absolute metadata, order, reflection, deterministic detached results and unchanged metadata/count/dirty state. The relative fixture does not create an FBX: this verifies delegation to the native resolver and its fallback, not the resolver branch for an existing package-relative file. The initial C++ checkpoint did not include Python execution; the separate read-only follow-up below now does. No SharedVista native import is claimed.

Validation used separate Content/ImportData copies and owned build outputs, UserDir and filesystem DDC, two CPU workers, unchanged engine/config/assertions. All seven observed custom Editor modules resolved to this worktree. The module monitor is a post-run observation, not native-batch pre-mutation clearance.

| Check | Actual result |
| --- | --- |
| Editor build | PASS,192s,149actions,zero compiler warnings |
| Focused new test | PASS1/1,43s,zero test warnings |
| First cold full suite | 153/154,1178s; existing WallsRemainSolid readiness deadline failed |
| Same-binary warm WallsRemainSolid | PASS1/1,23s,one test with warnings |
| Same-binary warm full suite | PASS154/154,718s,33 tests with warnings |
| Development Game build | PASS66.63s,zero compiler warnings; seven Editor DLLs unchanged |
| Full source audit | 2444 binaries,461 Python,22 shell,2182 ledger rows;zero errors/secrets |

The existing camera fixture starts its90-second readiness deadline before playable-world readiness. The cold run encountered1065 mesh compilation plus274 art-context meshes. Subsequent unchanged warm runs passed; cold-start readiness is not claimed to pass. The original failure and both reports remain preserved. The warm full run retained8562 identical inputs with no additions/deletions/changes.

Warnings were retained:793 EOS backend network events,406 engine HTTP events and32 sandbox-denied global EditorConfig JSON write attempts across33 successful tests. `-UserDir/-nowrite` does not redirect those JSON files on this UE version. No log suppression, plugin disabling, global config edits or assertion changes were used. A separate Saved-only mount-namespace experiment is proposed; no Unreal execution under it forms part of this proof.

Root Content5466/ImportData1209 files and initially inventoried module/save scopes remained unchanged. Additional protection checks confirmed seven Root DLLs plus six module metadata files and51 scoped older Root saves against a preceding full153 baseline;61 current Root saves were also stable against a mid-bridge inventory. Those scopes do not cover foreign UserDirs/protected owner saves. Own Development Game was built but not executed or packaged. Saved reports and launch logs remain under `Saved/BridgeProof` and `Saved/Automation/bridge_*`; selected summary receipts are retained here. No native asset, world composition, renderer or production integration acceptance is granted.

## Separate private-environment and Python follow-up

Root approved a Saved-only second environment: bubblewrap binds the host root read-only, the owned worktree writable, private Epic config over `~/.config/Epic` inside the child mount namespace only, private tmp/proc/dev, and unchanged HOME. The accepted inner launcher runs inside that namespace, retaining environment scrubbing, explicit UserDir/DDC/-nowrite and actual child module maps. Outer SHA3914951878e9a7e91fa3483b4968824a796481512ec98f8ff93f8a5b1971b1be; inner7c2caadca685b03fb3e77fa431d0df90967942a3e6b635e44c880a26fc5d0d04. Source, DLLs and earlier wrappers/reports were unchanged.

| Read-only comparison | Assertions | Actual process exit |
| --- | --- | --- |
| Original reflected new getter, null plus existing Oak3LOD | PASS |245: Python shutdown SIGSEGV |
| Unchanged WallsRemainSolid/environment control | PASS1/1,21s,one network-warning test |0 |
| Same Oak load only, no getter lookup/call | PASS |0 |
| New getter assertions, then release mesh/function references and Python gc.collect | PASS;45objects collected |0 |
| Same Oak load plus existing material-inspector callable cached, never invoked | PASS |245: same Python shutdown SIGSEGV |

Both failed commandlets completed their scripts with result0, then crashed in `_PyWeakref_ClearRef` → `PyGC_Collect` → `Py_FinalizeEx` → `FPythonScriptPlugin::ShutdownPython`. Retaining the existing callable without invoking any inspector reproduced this stack, so invocation of the new getter body is unnecessary for this failure. The exact engine/Python reference-lifetime mechanism remains unproven. Neither failure is converted to a pass; no engine patch, exception suppression, forced exit or test assertion change was used. The clean new-getter run released Python aliases while the interpreter/plugin were active, without engine GC or package saves.

Every run compared51404 pins before/after, with no added/missing/changed files, including all host Epic files, tracked source, owned Content, seven owned Editor DLLs and previously qualified Root protection scopes. Actual seven custom module paths were owned. Private FilterBar206B, ProjectEditorRecords372B and UBTTrace303–304B writes were captured. The control had no denied-read-only-filesystem or FilterBar warnings; network warnings remain. HOME and actual host Epic config bytes were unchanged. The capability inspected an existing cloned Oak: LOD0filename empty and LOD1/2existing native-resolved legacy paths. This is not proof that future SharedVista ImportLOD tasks populate newly approved source paths.

Saved/BridgeProof/BwrapEpoch2 preserves the exact setup/script pins, commands, launch maps, original crash logs and separate comparison receipts. No core was extracted; sandbox coredumpctl found no dump. No import, SharedVista batch or scene composition occurred. Public compact receipts here preserve the clean Python result, cleanup/command and all terminal outcomes; earlier cold/full/Game receipts retain their original scope. This follow-up changes documentation only.
