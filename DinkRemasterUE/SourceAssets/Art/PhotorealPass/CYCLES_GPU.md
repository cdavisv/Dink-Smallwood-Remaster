# Cycles GPU rendering and baking in batch mode

Blender 5.2 renders and bakes with Cycles on the GPU in batch mode (`blender -b`). The art pass used an AMD card through HIP; the same recipe works for the other back ends by changing one name (`OPTIX` or `CUDA` for NVIDIA, `ONEAPI` for Intel, `METAL` on macOS).

## What to expect

- Results match the CPU: renders differ by at most a couple of 8-bit levels on a handful of pixels, DIFFUSE and AO bakes are bit-identical.
- A mid-range discrete GPU is roughly 15-20 times faster than four busy CPU threads for renders and bakes, and it leaves the CPU free:

| Job | CPU (4 threads) | GPU |
|---|---|---|
| Render 512x512, 64 spp, glass + metal + sky | 75.5 s | 3.9 s |
| Bake COMBINED 512², 64 spp | 50.3 s | 4.2 s |
| Bake DIFFUSE (color) 1024², subdivided mesh | 66.2 s | 4.8 s |
| Bake AO 1024², 64 spp | 75.9 s | 3.3 s |
| Bake NORMAL 1024² | 8.8 s | 3.8 s |

Blender startup (about 3 s) is not included.

## Recipe: put this at the top of a batch script

```python
import bpy

def use_gpu(scene=None, backend='HIP', only=None):
    """Render/bake on the GPU. `only` is a substring of the device name to pick one card
    (leave an integrated GPU off: it is slow and shares system memory). Returns True if a GPU is enabled."""
    scene = scene or bpy.context.scene
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = backend
    prefs.refresh_devices()
    found = False
    for d in prefs.devices:
        d.use = (d.type == backend and (only is None or only in d.name))
        found |= d.use
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU' if found else 'CPU'
    print('Cycles device:', scene.cycles.device, [d.name for d in prefs.devices if d.use])
    return found

use_gpu()
```

Call it after opening the .blend (`bpy.ops.wm.open_mainfile` resets the scene setting, not the preferences). `scene.cycles.device = 'GPU'` must be set on every scene you render or bake. `bpy.ops.object.bake(...)` then runs on the GPU with no other changes.

Do not save preferences from batch jobs. The code above changes preferences only in memory, which is what parallel jobs need.

Command line: keep `-t 2` to `-t 4`, because CPU threads still do scene sync and BVH build:

```bash
blender -b -t 4 file.blend --python job.py
```

## Checking it really used the GPU

Add `--debug-cycles` once and look for the `Path tracing on:` line in the log. It names the device; if it names a CPU, the job fell back. With HIP, `HIPEW initialization failed: Error opening HIP dynamic library` means the HIP runtime package of the GPU driver stack is not installed.

## Limits and cautions

- Video memory is shared with everything else on the machine (desktop, Unreal editors, a running game). Cycles on HIP has no out-of-core textures: if the scene does not fit, the render fails with `Out of memory` (an error in the log, not a silent fallback). Retry on the CPU then: `scene.cycles.device = 'CPU'`.
- Several Blender processes can share one card, but they compete for memory and time-slice. Prefer one or two GPU jobs at a time.
- Leave HIP-RT (`prefs.use_hiprt`) off: experimental and of little gain on older cards.
- OSL (Open Shading Language) is not supported on HIP (CPU and OptiX only). Scenes that need `scene.cycles.shading_system = True` must render on the CPU.
- OpenImageDenoise can run on the GPU: `scene.cycles.denoising_use_gpu = True` is fine.
- A Blender session that was open before the GPU runtime was installed must be restarted before it can see the device.
- Updating the GPU runtime and Blender separately can break the match between the runtime and Blender's precompiled kernels. Update both together.
