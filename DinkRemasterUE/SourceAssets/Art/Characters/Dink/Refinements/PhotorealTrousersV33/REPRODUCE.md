# Readback and reproduction

Use Blender5.2.2 LTS and Python3. The Blender source-preview/rebake helpers also use NumPy and OpenImageIO available in the authoring installation; inspect imports before running elsewhere. All commands below write reports/results to a separate new directory. They do not grant native asset or gameplay acceptance.

Set `dink_packet` to this relocated directory and `dink_out` to a new writable directory outside it. Use `ALSOFT_DRIVERS=null`, `-noaudio`, a private `XDG_CACHE_HOME` and two CPU threads for headless Blender; this avoids a known local audio-teardown hang. Do not repurpose HOME.

```bash
python3 "$dink_packet/Tools/verify_packet.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$dink_packet/Tools/verify_raw_fbx.py" --report "$dink_out/raw_fbx.json"
ALSOFT_DRIVERS=null XDG_CACHE_HOME="$dink_out/cache" blender -b --factory-startup -noaudio -t 2 -P "$dink_packet/Tools/verify_sources.py" -- --report "$dink_out/sources.json"
ALSOFT_DRIVERS=null XDG_CACHE_HOME="$dink_out/cache" blender -b --factory-startup -noaudio -t 2 -P "$dink_packet/Tools/verify_blender_fbx.py" -- --report "$dink_out/blender_fbx.json"
```

Create `dink_out` before invoking the report commands. `verify_packet.py` only reads supplied bytes and detects missing/changed/unlisted payloads; `__pycache__`/`.pyc` caches are explicitly outside the payload.

Optional source reproduction commands create NEW geometry exports, a fresh coarse bake or one detail preview. They are not deterministic byte-hash claims, do not overwrite the accepted artifacts and do not automate the entire original art-development history:

```bash
ALSOFT_DRIVERS=null XDG_CACHE_HOME="$dink_out/cache" blender -b --factory-startup -noaudio -t 2 -P "$dink_packet/Tools/export_geometry.py" -- --out "$dink_out/reexport"
ALSOFT_DRIVERS=null XDG_CACHE_HOME="$dink_out/cache" blender -b --factory-startup -noaudio -t 2 -P "$dink_packet/Tools/rebake_coarse.py" -- --out "$dink_out/rebake"
ALSOFT_DRIVERS=null XDG_CACHE_HOME="$dink_out/cache" blender -b --factory-startup -noaudio -t 2 -P "$dink_packet/Tools/render_source_preview.py" -- --out "$dink_out/preview"
```

The periodic weave's editable source is `Source/Helpers/MetricWeave_Tile_Source.blend`; its delivered normal tile is256px RGB16 OpenGL+Y Non-Color, repeated every.0288m with.0009m yarn pitch. `Evidence/weave_tile_bake_receipt.json` records the original CPU Cycles normal bake and full-pixel checks. A separate one-command tile-regeneration recipe is not supplied; use the editable source and those parameters for a new evaluated bake rather than claiming the packed artifact was regenerated here.

`Evidence/Physical/` contains the existing selected-fit35-pose results, not a portable full-body-anatomy solver. The exact35pose authority and2,790anchor authority are supplied under `Evidence/Authority/`. `Evidence/Authoring/` scripts retain historical paths and are archival evidence only. Do not execute them as relocated recipes.
