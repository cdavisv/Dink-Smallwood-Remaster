# Photoreal barrel native tools — scratch handoff

This folder owns portable Python tools and pure tests only. No Unreal process, GPU session, build, import, project file, ledger, or frozen source payload was changed for this task. Read `handoff.json` for exact hashes and limits. Root must independently review the code before copying it to a stopped owned native checkout.

The starting house has three original barrel references: `assets[11]` and decorative `elements[144]`/`elements[145]` named `Barrel1`/`Barrel2`. The publisher finds exact identities/counts rather than trusting these current indices. It changes those three mesh strings only. Transforms, collision booleans, scripts, all other assets, lights, screen/warp ownership, saves and data are outside its write authority. Original complex-as-simple query policy is retained; authored UCX is inspected but is not the active query source.

The planned new payload is five packages: one mesh in `/Game/Dink/Props/Stonebrook/PhotorealBarrelV1`, one material in `/Game/Dink/Materials/Stonebrook/PhotorealBarrelV1` and three textures in `/Game/Dink/Textures/Stonebrook/PhotorealBarrelV1`. Optional `.uexp`/`.ubulk` sidecars are bound to those exact five package stems. Source is the selected portable `PhotorealBarrelV1` bundle. The handoff and all consumed/dependent file hashes are read dynamically; the tool-only publication fix to `inspect_payload.py` is accepted without changing the frozen art payload. Both author and publication source plans passed real binary-FBX/pixel checks, with identical asset plans and distinct current handoff hashes.

The importer/contract/publisher are scoped derivatives of the reviewed furniture framework, preserving its numerical matching, direct material graph, native filename, source/pixel, saved-package, atomic write and fresh-published clone safeguards. This deliberately keeps the barrel contract independent of furniture's fixed three-asset counts and all-dielectric metal assumption; no shared furniture globals are patched at runtime. The stdlib binary FBX parser is byte-identical to the furniture parser. `base_tools.json` records the upstream hashes.

Barrel-specific policy: 16,648 triangles, one `UCX_SM_Barrel_Oak_01_01` hull with exact eight-corner 75×75×100cm box, original bounds/pivot, one baked material, Nanite full fallback, source normals plus generated MikkTSpace tangents. BC is sRGB; normal is linear with green flip; ORM is linear with neutral R255 and variable B0..240. Wood must retain zero metallic and bare iron must retain high metallic values. Do not copy furniture's B0-everywhere assertion. Native verification must export each Texture.Source and compare every RGB pixel to its selected frozen image.

The native importer additionally pins custom project `.so`/`.modules`/`.target` files through exit, binds those pins into its receipt, and the publisher rechecks them before/after its concrete temporary output. Module symlinks fail. Sparse/invalid vertex, triangle and corner IDs and nonfinite coordinates/UVs are rejected before unsafe indexed native getters.

## Pure source audit and tests

From this scratch folder:

```sh
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 prepare_photoreal_barrel_plan.py --source /absolute/selected/PhotorealBarrelV1 --out /absolute/owned/source-plan.json
```

83 pure regressions pass. The publisher fixtures use synthetic FBX bytes and explicitly stub only those fixture FBX geometry/model reads. Separate real source audits parse all actual frozen FBX triangles, source normals, exact hull box, textures and file hashes without stubs. Pure tests do not establish Unreal import or render acceptance. Source audit output is refused inside the immutable source bundle.

## Native invocation after root review

Copy the four production files together: `barrel_contract.py`, `barrel_fbxparse.py`, `import_photoreal_barrel.py`, `publish_photoreal_barrel.py`. Copy the source-plan CLI and tests if desired. The existing read-only native `DinkMaterialArtLibrary` convex/hidden-material-property bridge must be built in the owned project.

Use the established private NullRHI editor commandlet invocation with `-run=pythonscript -script=<owned Scripts/import_photoreal_barrel.py>`, no display variables and own DDC/UserDir. Set `DINK_BARREL_SOURCE` to the selected frozen bundle and `DINK_BARREL_MODE` to `preflight`, then `import`, then `verify` in a fresh process. `DINK_BARREL_REPORT` must resolve under the owned project Saved directory. An unpublished `verify` needs `DINK_BARREL_IMPORT_RECEIPT` pointing to that completed import receipt (default `Saved/Art/photoreal_barrel_import.json`). Existing destinations always fail preflight/import: no replacement, implicit resume, deletion or reimport.

The expected old native baseline is 10,472 triangles, two original Oak/WroughtIron slots, original dimensions and complex-as-simple policy, derived from the existing original export manifest. Actual native root execution must confirm it; a mismatch is evidence to investigate, not permission to remove the assertion.

After successful fresh saved verification, run `publish_photoreal_barrel.py --project <ownproject> --source <samebundle> --verification <freshreceipt>` for a read-only check, then `--apply` for the three-string publication. The unpublished publisher retains atomic target replacement and a byte-bound publication receipt. Default/check/idempotence do not rewrite that receipt. A later normal published clone can verify with all three new references and no private Saved import/publication receipts. Its five entry package families and current Data remain pinned throughout native inspection. That fresh-published publisher default and `--apply` are zero-write checks with `scene_data_approval: false` and `writer_scope: none`; they never create a lock, temporary output or author receipt. Legitimate later scene merges require their own review and fresh verification; asset checks do not approve scene edits.

No native run, stored native corner-normal fingerprint, lighting, game collision/exit or final visual approval is claimed. Root owns those next gates, ledger/commit/LFS/PR delivery, and the protected visible SurfaceDelivery game remains untouched.


Current native evidence is under Docs/Verification/PhotorealBarrelNative. Reviewed preflight, import, independent saved verification, fresh published-state verification, full147 native checks and267 Python checks pass. Bounded private game collision/render views pass. The original frozen source bake script has a known stale NodeLink restoration issue; use an explicitly reviewed successor recipe for future rebaking in a separate output copy, never mutate this approved frozen bundle. Final lighting/hero/exterior remain separate goals.
