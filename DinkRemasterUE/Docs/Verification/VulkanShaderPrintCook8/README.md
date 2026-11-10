# Vulkan ShaderPrint packaging correction

The Linux package crashed on its first rendered frame while Vulkan precached `FSubsurfaceDebugCS`. The exact shader extracted from the crash matched Cook7's global archive. All four variants failed Vulkan SPIR-V validation because a local ShaderPrint context stored an opaque image resource. This matches the resource-in-struct problem reported in [DXC issue 8417](https://github.com/microsoft/DirectXShaderCompiler/issues/8417).

Linux `Scripts/package.sh` now invokes `shaderprint_vulkan_workaround.py`. For the exact reviewed UE 5.8.4 header, it mounts a temporary copy of `ShaderPrint.ush` over that one path during UAT. The only shader change adds `COMPILER_VULKAN` to the existing global-resource branch. ShaderPrint, subsurface rendering, PSO precaching and other graphics features stay enabled. The installed Engine file remains unchanged; no complete Engine source file is distributed here. An exact known corrected header runs UAT normally; an unknown revision stops with an explicit error for review.

Use the existing packaging command from `DinkRemasterUE`:

```sh
UE_ROOT=/path/to/UE_5.8.4 Scripts/package.sh /path/to/dink-stage
```

Python 3 and bubblewrap are required for this Linux workaround (`bubblewrap` is the Arch package). Existing greybox import, template-content and Editor-build prerequisites still apply. The helper preserves the original UAT arguments, working directory and existing `/dev` scope. A real normal-helper attempt exposed `nodev` restrictions from a plain root bind: random-device reads and .NET crypto initialization failed before cooking. The retained three-mode probe reproduces that error and shows that binding the existing `/dev` restores both device reads and the same .NET native crypto function. It checks the host header's content, inode, mode and modification time before and after packaging. Its temporary directory is removed after UAT exits.

Actual validation:

- Cook8 completed successfully in 305.857 seconds. All 12,918 measured source/Editor inputs and the host Engine header/staging preimages remained unchanged; seven own Editor modules were observed.
- All four regenerated `FSubsurfaceDebugCS` variants pass `spirv-val --target-env vulkan1.3`. The original four invalid results remain recorded.
- Actual containers contain 23 shared plus 50 retained roof packages, seven maps, and three Art JSON payloads identical to source.
- Packaged CH1 passes cleanly and matches the current native trace exactly.
- Packaged rendering passes on the original installed RADV 26.2.5 driver with the original normal-pool launch arguments and PSO precaching enabled. Seven screenshots were reviewed. Actual held-W movement exits screen 1 to 439 and returns to 1; no route teleports. Normal process/display cleanup completed, with all 12,957 measured inputs unchanged.
- Four runtime warnings remain: two unused bindless settings and two Vulkan shutdown image-resource/leak messages. There were no log errors or missing-package/shader errors. This is bounded room/roof/door coverage, not whole-game or final-art approval.

The cook used the stricter QA namespace with the same exact corrected header bytes. The production helper's real bubblewrap mount, immutable host header, literal arguments, cleanup and known-corrected bypass were separately exercised using a fake Engine and fake UAT script; that test does not claim to run UAT. Five portable unit tests cover classification, command preservation, refusal paths and host changes. An additional normal-helper cook remains useful to confirm the complete delivery command.

`INDEX.json` pins original receipts and captures. It contains no raw core, authentication data, complete Engine header or raw shader binaries. The source runtime is the previously verified C6 snapshot; this delivery changes packaging scripts and documentation, with no C++/Content/Data changes. The separate visibility fix, barrel collision rollout, new fireplace/cottage imports and final photorealistic art remain unfinished.
