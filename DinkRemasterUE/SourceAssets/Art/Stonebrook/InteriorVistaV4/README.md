# Starting-house woodland crest composition

Adds 43 instances of existing project meshes: 35 meadow grass clumps and eight PineV3 trees. The irregular crest conceals the finite terrain edge through the starting-house door. The immutable V3 bundle remains intact.

`Stonebrook_HorizonV4.blend` is the editable composition. Its texture paths resolve relative to this folder within the repository. `build_horizon.py` recreates it from V3 and existing textures. Run `check_source.py` with Blender 5.2.2 after any edit: `blender -b --factory-startup --python-exit-code 1 -P <script>`. The checker verifies all 519 original mesh objects and the 43 added mesh identities and transforms, including geometry, UVs, face materials, smoothing and corner normals. Its receipt binds the actual scene and additions hashes. `Scripts/build_vista_context.py` requires that current receipt before generating runtime placements.

`native-door-source-preview.png` is a Cycles CPU source render at a measured native camera position and FOV. It has no hero or native indoor lighting. A separate actual-game keyboard exit/return and window/door screenshot pass is in `Docs/Verification/VistaFinal`. The loaded geometry audit of 359 placements and 62 mesh references passes all 644 rooms with no house or neighbor intrusion.

The additions remain render-only and confined to screen 1. Scripts, warps, physical collision, audio and original courtyard actors retain their behavior. Inherited tree seams, surface finish, clothing and wider-world art remain ongoing work.
