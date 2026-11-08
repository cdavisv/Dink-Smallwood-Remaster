# Photoreal barrel native integration candidate

The reviewed Blender barrel source from source PR13 is imported through dedicated barrel guards. Existing furniture tools are unchanged. Shared FBX geometry, UV, convex topology, material graph and source-file ownership checks are reused from `props_contract.py`.

The candidate uses 16,648 triangles, one baked material and three 2048 RGB BC/N/ORM maps. Iron retains authored metallic variation; wood remains dielectric. Source normals are imported, MikkTSpace tangents generated, Nanite uses full triangle fallback. The original complex-as-simple query policy is retained; the authored UCX hull is checked but is not the active query source.

`barrel_contract.py` permits exactly three scene mesh-string edits: the barrel asset row and decorative Barrel1/Barrel2. All transforms, collision flags, identities and unrelated rows must remain unchanged. Mixed/ambiguous publication states and foreign native source filenames are rejected. `publish_photoreal_barrel.py` defaults to a no-write check and requires fresh saved-native verification before `--apply`.

Initial preflight and native import passed. Five new candidate packages were created; protected Content, Data, source art, modules and tools remained unchanged during import. Separate saved-package verification and runtime publication/render acceptance are tracked in the project handoff. Work-only terminal reports and before/after inventories live under `Saved/BarrelNative`; the native receipt includes actual saved geometry, UVs/fronts, convex vertices/indices, material property connections, texture-source pixels and resolved source filenames.

Seven barrel guard tests pass; the combined Python suite passed 191 tests. The shared geometry/publication test cases remain in the furniture suite. This does not establish final native game-camera appearance, collision/reach routes, whole-game photorealism or lighting acceptance.
