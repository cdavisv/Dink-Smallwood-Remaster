# Shared roof native trial

Unreal saved exactly 23 fresh assets: eight roof meshes, nine shared textures and six opaque/masked materials. A separate fresh process reloaded and verified all 23 with Content read-only, zero imports and zero saves. Both exited normally; all 12,797 protected inputs and existing Content remained unchanged. Seven custom modules were observed and verified in each process. results.json records exact package hashes and report digests.

Checks compare source geometry, UV0, normals, authored convex hulls, material roles/graphs, Texture.Source pixels/settings and relative import filenames. Tolerances match the accepted roof readback: position .002 cm, UV0 .01/2048, normal component .005. Stored tangent-Y handedness remains NOT_PROVEN.

The earlier failed attempt saved 15 textures/materials before discovering relative mesh metadata was configured after verification. Its report and partial outputs remain preserved externally. Fix5c1ee69 configures relative sources before verification; a regression reproduces the original failure. This retry used fresh namespaces and overwrote no existing package.

Production activation, camera aliases, rendered gameplay, final appearance and cooking remain pending. These fresh assets currently have no new scene bindings.
