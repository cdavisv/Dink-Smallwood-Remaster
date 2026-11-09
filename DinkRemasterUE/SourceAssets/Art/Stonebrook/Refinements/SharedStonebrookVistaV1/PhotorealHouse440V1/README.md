# Photoreal House440 source candidate

This is a bounded source and export candidate for the original 63_04-inspired two-tier house. The coordinating art review accepted its weathered quarried stone, recessed mortar and rounded thatch direction. Native world composition, original actor/vision/collider/warp behavior and final game appearance remain unverified here. No Content packages or runtime Data change in this source bundle.

The editable game mesh has114,354 triangles, five material roles and shared physical PBR tiles. Its single LOD stays below the200,000 hard building limit and retains the60,000 soft-target warning. All source faces remain closed/nonmanifold0 / zero-area 0;15 source point rays clear the door, which is not a native capsule test. Raw guide retains one deliberate COLLISION_MISSING render-only exception and two warnings (soft triangle target and60 coincident points on separate closed mortar boxes). The forced-export flag and raw error count remain in the manifest.

UVs intentionally repeat. There is one finite UV channel with no collapsed triangles; the guide overlap calculation is truncated and is not a no-overlap claim. Stone repeats1m, oak2m, thatch1.538m, glass1m and mortar2m. Native material UV multiplier and normal strength are1. Base color is sRGB; normal and ORM are linear, normal green flips on native import. ORM AO is255 and metallic0 for this building, measured from actual maps. Source IOR1.5/specularIOR levels are stone/oak/glass.5, thatch.2 and mortar.25. Opaque dark glazing is an explicitly accepted source proposal differing from V11 transmission.35.

SourceReference retains the self-contained original V11house-only high donor (575,320 evaluated triangles;333,784 base-data total), original 63_04 guide and the actual independently modeled fieldstone-normal surface. The latter editable bake scene includes the older V5 low mesh only as a hidden reference; SharedHouse440_GameV6.blend is the authoritative game derivative. Generated input provenance/full prompts accompany the original textures. No normal or height was inferred from generated base color.

The published blend and FBX are byte copies of approved V6. Actual FBX/GLB roundtrips retain114,354 oriented geometry/material triangles. FBX UVs are exact; GLB UV maximum float32-transfer difference is3.9582e-8. Raw failed rounded-key comparison logs remain in the original QA folder; direct numeric comparison resolved those fixture false positives. All 15 maps reopen from packed data without external texture paths.

Run the portable read-only audit with Blender 5.2.2:

```
blender -b --factory-startup -t 2 --python Tools/verify_payload.py -- --report /tmp/house-source-audit.json
```

Tools/run_guide.py writes its raw report outside this frozen bundle. Tools/export_candidate.py exports to a separate directory and refuses unexpected errors; it only authorizes the recorded render-only collision exception. Both preserve warnings. Copy the entire folder before running from a different directory; no tool requires the original QA path or another checkout.

New outdoor art uses ordinary world visibility. Never export the 560 existing references as duplicate outdoor actors. Interior owner 1 derives the canonical composition using the recorded front-plane translation and replaces old V4. Existing runtime references must resolve current guarded full main-manifest asset paths, preserving element identities/transforms, including newer barrel art; authoring references are not current native binding authority.
