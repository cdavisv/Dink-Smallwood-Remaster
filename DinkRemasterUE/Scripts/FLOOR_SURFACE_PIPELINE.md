# Starting-house oak and underfloor refinements

`FloorOakV1` replaces only the oak material on a copy of the original floor mesh. The original geometry, UVs, per-face material indices, nail material, collision and Nanite settings remain intact. `UnderfloorV1` is a separate dark sheet below the boards, closing visible sky gaps. It uses a screen-owned render-only context with no collision, navigation, overlaps, hidden shadows or hidden GI. The original house and VistaV4 manifests remain the basis for placement; only the 57 floor mesh references change in the house manifest.

Source folders: `SourceAssets/Art/Stonebrook/Refinements/{FloorOakV1,UnderfloorV1}`. Their `REPRODUCE.txt` files describe Blender rebuilding. The source handoffs record the authoring checkpoint; native receipts describe the later import and runtime verification. The oak's generated albedo, prompt and calibration are retained in `FloorOakV1/Inputs` and `albedo_calibration.json`. Its coverage is art-directed, not a measured scan. The accepted 0.25 linear colour calibration and microrelief are baked into the textures; native colour gain and normal strength are both 1. Normal textures are OpenGL/Y+ with Unreal green-channel flip. Slot 1 retains the original WroughtIron nails.

After `git lfs pull` and `Scripts/build.sh`, verify the delivered native packages with UnrealEditor's Python commandlet. Run from the Unreal project directory, with no game/editor using that checkout:

```bash
UE_ROOT="${UE_ROOT:-$HOME/UnrealEngine/UE_5.8.4}"
DINK_FLOOR_MODE=verify DINK_FLOOR_REPORT="$PWD/Saved/Art/floor_surface_verified.json" \
  "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" "$PWD/DinkRemaster.uproject" \
  -run=pythonscript -script="$PWD/Scripts/import_floor_surface.py" -nullrhi -nosound -unattended
DINK_UNDERFLOOR_MODE=verify DINK_UNDERFLOOR_REPORT="$PWD/Saved/Art/underfloor_surface_verified.json" \
  "$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd" "$PWD/DinkRemaster.uproject" \
  -run=pythonscript -script="$PWD/Scripts/import_underfloor_surface.py" -nullrhi -nosound -unattended
python3 Scripts/publish_floor_surface.py --project "$PWD" \
  --verification "$PWD/Saved/Art/floor_surface_verified.json"
python3 Scripts/publish_underfloor_surface.py --project "$PWD" \
  --verification "$PWD/Saved/Art/underfloor_surface_verified.json"
```

Private validation uses a filesystem DDC (`-ddc=InstalledNoZenLocalFallback`), an explicit local cache path and its own `-UserDir`; it never modifies the shared engine or a running game's libraries. See the existing private QA and cook guidance for those switches. Normal cloning uses the LFS packages. New imports use `preflight`, then `import`, then a fresh `verify` process. Import refuses existing destinations, preserving published revisions. Inspect and preserve unpublished failed candidates before a scoped retry; create a new revision for published changes.

Publishers default to checking. Use `--apply` only after native verification to update the floor references or create the exact separate context JSON. They recheck source, saved-package and gameplay-data hashes immediately before publication. The underfloor binds the 56 floor transforms independently of their mesh paths. Its guide validation has one documented `COLLISION_MISSING` exception because this asset deliberately has no collision geometry; all other guide checks pass.

Material verification reads the saved property connections, texture/channel choices, UV channel, constants and complete input set. Python hides several material-property enum entries, and the engine library getter is unsafe on unsupported IDs. The editor-only `DinkMaterialArtLibrary` queries all inputs with native null checks, detecting reused nodes on WPO, emissive or hidden UV pins without editing the material. Native and Python regressions cover those links and stale publication receipts. Rendered walking and screenshots remain separate acceptance checks.
