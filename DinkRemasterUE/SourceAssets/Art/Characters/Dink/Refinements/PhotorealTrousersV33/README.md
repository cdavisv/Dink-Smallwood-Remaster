# Dink trousers V33 — portable source candidate

Editable realistic olive trousers, guided by the original Dink sprites in `References/`. This is a **source-only candidate**, combining selected V19 fit, a fresh 2K coarse bake, a 256px metric weave tile and V32 metric stitches. It does not replace the playable character or establish production/native acceptance.

## Open and inspect

Open `Source/SK_Dink_Trousers_MetricArtV32_Context.blend` in Blender 5.2.2 LTS. Its eight meshes provide the unchanged character context around the trousers. The internal OSL stitch source/bytecode is included; use Cycles CPU with OSL for the intended source appearance. The editable fit checkpoint is `Source/SK_Dink_Trousers_FitV19_Context.blend`. `Source/Helpers/` contains a pants-only coarse procedural bake source and the 28.8mm weave-plane source. All used node images are packed and also supplied at relative paths. No external linked Blender libraries are needed.

`Export/SK_Dink_V33_Trousers_Hi.fbx` contains the trousers only (20,620 triangles); `SK_Dink_V33_Context_Hi.fbx` contains the eight-mesh context (62,964 triangles). Both retain the original 89-bone hierarchy and carry skin weights, not animations. The FBX unit scale is approximately1cm; source scenes use metres. Material aliases and exact export options are in `Export/export_receipt.json`. The GLB is a geometry-only skin preview with no materials or animations; it cannot show the OSL/weave/stitch appearance.

## Evidence and limits

Actual binary FBX checks match all named weights and three trouser UV channels, canonical89 metadata and bounded bind transforms. A separate actual Blender import verifies the exported geometry, UVs and weights. Packed-source reopening verifies local relative images and geometry/rig signatures. These reports are in `Evidence/`; historical absolute paths identify authoring provenance, not required dependencies. `Evidence/Authoring/` contains archived preparatory scripts, not portable entry points.

The 35-pose source check keeps actual legacy hand contact counts at zero and introduces no body/self count regression versus selected V15. Rest/idle body/self counts are zero. This is **not an all-motion-clear claim**: walk11 retains256 inner-rise self contacts and covered-body residuals. The corresponding front/back previews are included; Root selected this as compressed cloth without a visible hole in those views. Fixed199 local finger gaps are +2.583mm left/+4.219mm right, not universal clearance. The other seven context meshes,89rest bones and2,790 waist/cuff anchors retain their measured authority.

The actual production-guide run fails with22errors/8warnings. `Evidence/Guide/` preserves the raw JSON/log and classification: editable multi-mesh context/names, missing four-LOD chain, first-bracer whole-body bounds/pivot misinterpretation and one inherited shirt zero-area face. Thirteen context material slots also exceed the six-slot hero policy. No production guide PASS, native PhysicsAsset or finished whole-avatar quality is claimed. Historical guide/reference text about older mother/red-shirt assets or absent Unreal installations describes those earlier snapshots, not this candidate's acceptance.

`Previews/` are Blender source renders, including historical orthographic game-like framing. They are not screenshots from the running Unreal game. Other context garments, head, hair and gear remain unfinished legacy/reference art.

## Unreal proposal — unexecuted

Read `Shaders/UE_STITCH_GRAPH_COST_PROPOSAL.json` and `UE_Custom_Stitch_PROPOSAL.hlsl`. UV0 is the unique atlas/TBN basis; UV1 carries grain metres and UV2 carries seam distance/arc metres. UV2 is never a tangent basis. The native proposal uses signed normal decoding/RNM, world-normal output, explicit SkeletalMesh material usage and camera-relative no-offset world position **before** float conversion (`WPT_CameraRelativeNoOffsets`). Actual ~3.9km house-coordinate precision still needs testing. Standalone glslang syntax/math evidence is not Unreal/DXC compilation or GPU validation.

Three full32 UV channels apply to every vertex in the final combined skeletal LOD:24bytes per actual native vertex, not just the10,308 source trouser points. Actual duplication/allocation is unknown. The proposed2K+256 texture budget is13.417MiB with full mips; actual formats/mips/allocations, AA/shimmer, shader cost, cooked usage and gameplay remain pending. No new C++ inspector is required: PR28 already reads all skeletal UV channels and built basis values.

See `REPRODUCE.md`, `LICENSES.md`, `MANIFEST.json` and `SHA256SUMS.json`. Do not overwrite the packet when reproducing outputs.
