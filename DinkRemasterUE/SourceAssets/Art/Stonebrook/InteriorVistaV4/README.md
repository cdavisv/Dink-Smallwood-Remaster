# Starting-house woodland crest composition

Adds 43 instances of existing project meshes: 35 meadow grass clumps and eight PineV3 trees. The irregular crest conceals the finite terrain edge in the source doorway preview. The immutable V3 bundle remains intact.

`Stonebrook_HorizonV4.blend` is the editable composition. Its texture paths resolve relative to this folder within the repository. `build_horizon.py` recreates it from the V3 scene and existing textures. `check_source.py` reopens both scenes and checks every original mesh transform, geometry, UV, material binding and render visibility, plus the 43 additions and texture references. Run either script with Blender 5.2.2: `blender -b --factory-startup --python-exit-code 1 -P <script>`.

`native-door-source-preview.png` is a Cycles CPU source render at the measured native camera position and FOV. It has no hero or native indoor lighting. Native rendered acceptance is pending. The loaded Unreal geometry audit of 359 placements and 62 mesh references passes all 644 screens, with no house or neighbor intrusion and unchanged protected inputs.

All additions are render-only and confined to the existing screen 1 context. Scripts, warps, collision, audio and original courtyard actors remain authoritative. Inherited tree seams, surface finish and wider-world art remain ongoing work.
