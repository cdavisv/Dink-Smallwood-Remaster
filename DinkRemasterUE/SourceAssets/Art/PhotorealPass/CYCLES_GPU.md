# Cycles GPU rendering (HIP) on this machine

Verified 2026-11-12 on Blender 5.2.2 (Arch package `blender 17:5.2.2-3`, `/usr/bin/blender`)
with an AMD Radeon RX 6800 (gfx1030, 16 GB) and ROCm/HIP runtime 7.2.4 (`hip-runtime-amd`).

## Status

- HIP works in batch mode (`blender -b`). No kernel compile: Blender ships a precompiled
  `kernel_gfx1030.fatbin.zst`, so the first GPU render starts in about 1 s.
- Results match the CPU: identical renders (max 2/255 on 123 of 262k pixels) and bit-identical
  DIFFUSE/AO bakes.
- Measured with the machine at load ~32 (batch jobs running), 4 CPU threads for the CPU runs:

| Job | CPU (4 threads) | GPU (RX 6800, HIP) |
|---|---|---|
| Render 512x512, 64 spp, glass + metal + sky | 75.5 s | 3.9 s |
| Bake COMBINED 512², 64 spp | 50.3 s | 4.2 s |
| Bake DIFFUSE (color) 1024², subdivided mesh | 66.2 s | 4.8 s |
| Bake AO 1024², 64 spp | 75.9 s | 3.3 s |
| Bake NORMAL 1024² | 8.8 s | 3.8 s |

The GPU also frees the CPU for other jobs. Blender startup (~3 s) is not included.

## Recipe: put this at the top of a batch script

```python
import bpy

def use_hip_gpu(scene=None):
    """Render/bake on the RX 6800 via HIP. Returns True if the GPU is enabled."""
    scene = scene or bpy.context.scene
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'HIP'
    prefs.refresh_devices()
    found = False
    for d in prefs.devices:
        # Enable ONLY the discrete card. HIP also lists the Ryzen iGPU (gfx1036) and the CPU;
        # leave both off. The iGPU is slow and shares system RAM; the CPU is busy with other jobs.
        d.use = (d.type == 'HIP' and 'Radeon RX 6800' in d.name)
        found |= d.use
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU' if found else 'CPU'
    print('Cycles device:', scene.cycles.device,
          [d.name for d in prefs.devices if d.use])
    return found

use_hip_gpu()
```

Call it after opening the .blend (`bpy.ops.wm.open_mainfile` resets the scene setting,
not the preferences). `scene.cycles.device = 'GPU'` must be set on every scene you
render or bake. `bpy.ops.object.bake(...)` then runs on the GPU with no other changes.

Do not save preferences from batch jobs. The code above changes preferences only in memory,
which is what parallel jobs need.

Command line: keep `-t 2`-`-t 4`, because CPU threads still do scene sync and BVH build:

```bash
blender -b -t 4 file.blend --python job.py
```

## Checking it really used the GPU

Add `--debug-cycles` once and grep the log:

```
HIPEW initialization succeeded
Using precompiled kernel.
Path tracing on: AMD Radeon RX 6800 (HIP) [HIP_AMD Radeon RX 6800_0000:03:00]
```

If it says `Path tracing on: AMD Ryzen 5 7600X ... (CPU)`, it fell back to the CPU.
`HIPEW initialization failed: Error opening HIP dynamic library` means the
`hip-runtime-amd` package is missing.

No environment variables are needed. `libamdhip64.so.7` is in `/opt/rocm/lib`, which is in
the ld.so cache.

## Limits and cautions

- VRAM: 16 GB, shared with the desktop, the Unreal editors and any game. About 6 GB was already
  in use when this was tested. Watch it with
  `cat /sys/class/drm/card1/device/mem_info_vram_used`, or use `amdgpu_top` / `nvtop` if installed.
  Cycles on HIP has no out-of-core textures. If the scene doesn't fit, the render fails with
  `Out of memory` (an error in the log, not a silent fallback). Retry on CPU then:
  `scene.cycles.device = 'CPU'`.
- One GPU, many jobs: several Blender processes can share the card, but they compete for VRAM
  and time-slice. Prefer running 1-2 GPU jobs at a time over 5. The others queue faster than
  they would on the overloaded CPU anyway.
- Leave HIP-RT (`prefs.use_hiprt`) off. It is experimental, not needed here, and on RDNA2 it gives
  little gain over the BVH2 path.
- OSL (Open Shading Language) is not supported on HIP (CPU/OptiX only). Scenes that need
  `scene.cycles.shading_system = True` must render on CPU.
- OpenImageDenoise can run on the GPU (Blender reports "supports OpenImageDenoise"), so
  `scene.cycles.denoising_use_gpu = True` is fine.
- A Blender that was already open before 2026-11-12 08:07 (the owner's GUI Blender) must be
  restarted before it can see HIP. Batch jobs started after that see it automatically. Jobs that were already running stay on CPU until restarted.
- Updating ROCm or Blender separately (partial upgrade) can break the match between the HIP
  runtime and the kernel. Update both with the normal full system upgrade.
