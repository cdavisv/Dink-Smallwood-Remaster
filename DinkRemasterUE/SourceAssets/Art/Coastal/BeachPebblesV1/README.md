# Beach pebble source candidate

Seven real-size stone variants follow original sequence92 frames5–11. Frame5/6 are single stones; later frames are sparse clusters. Original raw map verification resolves281origins with frame counts63/41/36/22/26/44/49. This mapping is a proposal against the pinned original/historical dataset, not activated game data.

The editable packed source is BeachPebbles_V6_ExplicitTriangles.blend. Each variant is prop_small, uses three explicit LODs, one registered MI_Shared_FieldstoneSeed2m material and CORNER SharedSurfaceData. UV patches do not overlap between stones and retain a2m aggregate area density. No private production material, new texture map, collision or runtime binding is included. REVIEW_ONLY scene objects are excluded from every exported FBX; lower LODs are hidden only for render review.

Export_V6 contains21individual mesh/LOD FBXs. The explicit export preserves LINEAR vertex colors and serialized tangents/binormals. Standard source validation passes7/7 with0errors and27warnings; warnings cover registered texture naming, texel-density boundary and soft triangle budgets. Independent binary channel checks pass21files. Fresh Blender reimport consumes every source corner once at the fixed source frame: position/UV/RGBA differences0, maximum measured normal angle0.0333003degrees under0.05. This is corner multiset correspondence, not triangle-adjacency proof or Unreal import acceptance.

The shared material uses existing registered source maps derived from Poly Haven Rock Boulder Dry (CC0; primary license verification included). Packed map bytes match the registered hashes. The source file is editable without external images or linked libraries. The original sprite guides are game references, not represented as CC0.

Evidence files retain historical QA/worktree paths for provenance; those paths are not runtime dependencies. Earlier failed UV/export-normal experiments remain in the external QA record and are not presented as selected assets.

Unresolved: independent source review/publication, native import and material/texture GPU conversion, explicit variant/origin placement, collision-free visual integration, source/native appearance review, and complete game artwork coverage. No all-art completion or production acceptance is claimed.

manifest.json declares every asset class, material, shared1024texture references, family and three LODs for the repository source-art checker. These declarations are source metadata only.
