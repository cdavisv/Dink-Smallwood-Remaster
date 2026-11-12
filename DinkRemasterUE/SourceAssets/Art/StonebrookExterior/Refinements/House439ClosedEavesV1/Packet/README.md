# Cottage 439 closed-eave source packet

Whole source appearance accepted for a native trial by the coordinating thread on 10 November 2026. This packet is source/export evidence. Native materials, collision behavior, camera/door traversal and final game appearance remain unverified for this new mesh.

## Preferred payload

- `Source/House439_ClosedEaves.blend`: editable packed authoring snapshot, SHA256 `233f6041c201fc2d8a6e92fd9dad63e292f8e88ba67a4bfd83e6e965b96f28c2`. Its parent is the accepted `House439_AllEavesFinalSurface.blend`, SHA256 `2f606055c7797dee6a2bccd081fa5cd570ea052d360df6369864e04081edab01`.
- `FBX/SM_Cottage_Stonebrook_01.fbx`: actual relocated export/readback, SHA256 `aa4e091a48f3337f7b9bda4b1f044786c46149c163df511978bebb86bc210f27`. One assembled house, 182,626 triangles, seven material slots, six original UCX hulls.
- `Textures/`: 54 exact image payload files corresponding to 54 authoring image datablocks, 53 distinct payload hashes. The connected graphs of the seven exported roles use 32 distinct image payloads. These counts are measured inventories, not the earlier estimated 45. The authoring snapshot retains its complete image context.
- `Renders/`: current four whole-house quadrants and four eave close-ups. `Reference/` preserves the original sequence-63 home guides and extraction provenance.

## Reproduce and inspect

From any working directory, use Blender 5.2.2 with CPU threads limited to two:

```sh
blender -b -t 2 --python /path/to/packet/Scripts/verify_relocated_source.py
blender -b -t 2 --python /path/to/packet/Scripts/export_validate.py
blender -b -t 2 --python /path/to/packet/Scripts/inventory_roles.py
```

The editable snapshot is authoritative. These recipes need only this packet. Historical warm-coat derivation scripts under `Provenance/` document prior authoring inputs and are not standalone procedural rebuild recipes.

The preferred exporter uses **EDGE smoothing metadata**. FACE smoothing loses normal-fan boundaries on import and fails normal/Mikk tolerances. An explicit-corner-vertex alternative also failed source-normal preservation and produced nonfinite tangents. Both failures are preserved in `Diagnostics/`; do not promote their FBX files or treat their scripts as preferred recipes.

## Verified scope

Independent relocation preserves 945 authoring geometry/UV/color/normal/transform signatures and all 54 external/packed texture bytes, dimensions, color spaces and relative paths. The export selects 314 high-detail source objects. Exact exported/imported positions, UV0, UV1, all 547,878 linear Color0 corners, named material roles and six hull positions/transforms pass. Normal max error is 0.032972 degrees; Mikk tangent max error is 0.032272 degrees, below the unchanged 0.05-degree gate. Zero tangents and bitangent-sign changes are both zero. FBX Z-up, front-axis index 1/sign -1 metadata, unit scale 100, identity assembly frame and source bounds are recorded in `Evidence/ROLE_BINDINGS_AND_FRAME.json`.

Local geometry audits cover the 31,934-triangle joined roof core and 5,568-triangle closed corner mesh. They have zero nonmanifold/inconsistent edges, self-overlaps, tiny triangles/UVs or zero/nonfinite TBN entries. This is not a global manifold claim for every inherited house ornament. All four accepted corner sectors, nonroof meshes, whole bounds and six source hulls are preserved. The last join preserves 12,452 protected prior roof faces exactly in geometry, UVs, colors and shading normals. Actual 37,356-corner protected decoded-normal max difference is below 0.000006 degrees.

## Provenance and native preparation

`Provenance/ArchitecturalSurfaceOrigins.md` records retained generic stone/wood/metal/plaster sources and qualifications. Its DressedReed section describes the predecessor library role. The current photo coat/cut override follows `ThatchPhotoOrigins.json` and the warm-coat derivation records; archived Poly Haven license evidence is included. No new external asset was downloaded during these eave repairs. Original game guides are reference evidence, not replacement photoreal textures.

`Evidence/ROLE_BINDINGS_AND_FRAME.json` inventories the actual seven exported material roles, connected images and normal-map graphs. Roof normal strength uses SharedSurfaceData.R; coat/cut selection uses UV1.X; weathering uses SharedSurfaceData.A. Native shader support and appropriate OpenGL-normal handling need explicit verification. Do not globally change unrelated material roles to add this roof carrier.

`Evidence/NATIVE_BASELINE_INVENTORY.json` snapshots read-only baseline `DinkBarrelCombinedDelivery` at `7fc61d3`, four Data hashes, 33 declared package dependencies and 99 protected material/fireplace packages. Preserve PR59's six rect and two practical lights, PR60's Chimney_Stonebrook_V8 and fired-clay fireplace replacement, cottage placement, portal/camera rules and every other Data field. Old A/B Data overlays are not authorized substitutes for fresh baseline inventory. Actual current native mesh material-slot bindings still require editor readback after the coordinated build lease. The frozen source render-size difference from the old native expected size is 1.416 cm in X and 1.038 cm in Y, slightly beyond that old 1 cm metadata tolerance. `FRAME_BASELINE_COMPARISON.json` records this measured difference. Fresh native bounds/expectations need review; do not alter frozen geometry or silently reuse the old expectations.

`NativePreparation/static_mesh_geometry_inspection.patch` adds only the historical read-only 157-line geometry inspector and four current-header declaration lines. `git apply --check` passes against 7fc61d3; it has NOT been applied or compiled here. Use an isolated current native checkout and its own build when the coordinator releases the lease. Do not restore an old complete header, reuse foreign DLLs, launch UE concurrently or count prior A/B runtime evidence as acceptance of this mesh.
