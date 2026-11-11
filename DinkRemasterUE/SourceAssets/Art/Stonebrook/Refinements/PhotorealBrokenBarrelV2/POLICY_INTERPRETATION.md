# Role and raw validator findings

This is a source candidate for class `barrel_broken`, original173/frame6. It is not bound, imported or tagged `DinkAuthoredArt`. No actual placement hardbox, script, ID, collision or navigation policy changes. No UCX was invented to satisfy a generic prop checker.

The governing text is unchanged:

- ART_STANDARD.md opening: “Where the two disagree, this page wins.”
- ART_STANDARD.md §2: “Static meshes (props, kit modules, foliage, buildings, doors, weapons) use materials from this table only.” It calls a prop-private unique bake “a violation”. The listed shared oak/endgrain and Stonebrook wrought-iron graphs are used unchanged, at their physical2m tiling scale.
- ART_STANDARD.md §5: “A family mesh has no collision and no navigation effect; the placement keeps its hardbox, its origin ID and its script, and is never tagged `DinkAuthoredArt`”.
- CONVENTIONS.md §7: “**unique bakes** carry props and characters (UV islands must not overlap, `UV_OVERLAP`).” Its rationale says mirrored unique-texture UVs break baked AO and normals. This candidate does not introduce a unique prop bake; it reuses the approved tiling library.
- CONVENTIONS.md §9: “Classes with `collision = required` need `UCX_` hulls (props that characters collide with, every kit piece, doors, buildings).” This proposed family dressing is visual-only; it is not a new collidable prop.

**Interpretation, not an implemented validator change:** the later project rule requires shared library textures and visual-only family physics. A role-qualified validation profile should distinguish that role from a generic unique-baked/collidable prop without changing the semantic class, triangle/material/geometry limits, family declaration or actual runtime policy.

The raw generic validation report remains unchanged in Evidence/GUIDE_RAW.json: **2errors**, UV_OVERLAP and COLLISION_MISSING, plus soft triangle target/UVrange/shared N_GL naming/reference warnings. No full-guide PASS is claimed. The report used a joined in-memory surrogate of the28 editable pieces; the delivered source retains those pieces and is not a native/export-ready joined asset. A small physical per-face UV correction removed the prior collapsed-UV finding without shrinking tiling UVs or changing material graphs/geometry.

Proposed future profile (not delivered as code): require an explicit original family/class, exact shared-library material/texture identities and physical tiling evidence; continue strict finite/manifold/nondegenerate/bounds/pivot/triangle/material checks; inspect original/no-source-change evidence; require no render-mesh collision/navigation and preserve the placement's original gameplay policy in actual native tests. Report shared-tiling overlap and absent UCX as role facts rather than silently passing generic errors. Unknown/unique-bake/collidable roles retain generic requirements. Root has reviewed this precedence and cleared source-only archival publication with both raw findings disclosed. No new validator profile is required to preserve this honest source candidate. A role-qualified export/native contract remains unresolved before any export-ready or activation acceptance. This does not approve a full-guide PASS, native activation, class renaming or user waiver.
