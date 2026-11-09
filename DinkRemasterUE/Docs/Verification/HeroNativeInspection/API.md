# Read-only hero asset inspection

`UDinkHeroInspectionLibrary` adds three editor-only JSON readers. They neither import, build, assign, dirty nor save assets.

| Python call | Schema | Readback |
| --- | --- | --- |
| `unreal.DinkHeroInspectionLibrary.inspect_skeleton_reference(skeleton)` | `dink-skeleton-reference/1` | Actual reference bones, parent/local bind transforms, virtual bones |
| `unreal.DinkHeroInspectionLibrary.inspect_skeletal_mesh_lod(mesh, lod, sample_vertices)` | `dink-skeletal-lod/1` | Mesh bind rig, material and section remaps, import/build settings, source and built vertex/index streams |
| `unreal.DinkHeroInspectionLibrary.inspect_texture_pixels(texture, pixels)` | `dink-texture-pixels/1` | Texture Source and existing platform mip metadata, hashes and supported typed samples |

Vertex and pixel requests are limited to 64 samples. Stream statistics and hashes cover the full inspected streams. Canonical data hashes use SHA-1; verification of source files, modules and packages uses SHA-256. Unavailable data is reported explicitly; callers must require the representations they need rather than treating absent arrays as empty valid geometry.

Complete pending asset compilation before inspecting existing loaded skeletal meshes. The verified Python caller loads its references and uses the existing `DinkCharacterArtLibrary.inspect_rig(mesh)` compilation barrier before the new readers. The new readers themselves do not request compilation.

The existing hand mesh has an 89-bone mesh bind rig while its shared Skeleton has 161 reference bones. Compare the actual compatible mesh names, parents and transforms; do not require the shared Skeleton inventory to contain only 89 bones.

A NullRHI commandlet may have Texture Source data but no platform mips. That is an explicit availability result, not proof of compressed pixels, float formats, shader decoding or GPU rendering. Candidate signed-RGB normal maps still require render-capable platform and image verification. Unsupported pixel formats retain an explicit unsupported state.

This delivery contains inspection code and tests only. It does not approve or import the unfinished hero candidate, change gameplay or select a production avatar.
