# Starting-house photoreal furniture source candidate

This editable Blender iteration uses the original table `87_09`, bed `64_03`, and chair references as its guide. It rebuilds table joinery and broad chamfered corners, chair supports, mattress, pillow, and olive linen cover. Original bounds and placement matrices are retained; the table top is 6 mm lower after removal of raised nailheads.

`PhotorealPropsV1.blend` contains the room comparison and procedural materials. `PhotorealPropsV1_Export.blend` contains the three assets, packed baked materials, and 47 authored convex hulls. `Export/` contains FBX/GLB and nine 2048 px BC/normal/ORM maps. Existing geometry, materials, and imported packages elsewhere in the project are preserved.

Source validation passes all three assets with zero errors and three retained triangle-target warnings; every asset remains below the 20,000-triangle hard limit. FBX reimport preserves measured dimensions and 18 table, 16 chair, and 13 bed hulls. Packed-image reopen checks deliberately remove all file paths. See `final_handoff.json`, `guide_validation.json`, `roundtrip_receipt.json`, and `portable_reopen_receipt.json` for exact scope. The generated oak reference and its original prompt/provenance are retained in `Inputs/`.

This is a source-art delivery, with ledger status `candidate`. Native import, gameplay camera and lighting review, collision routes, original scripted interactions, and save identity remain acceptance gates. Existing runtime manifests continue to use the published assets. The extreme cloth close-up shows a filtering difference between procedural weave and the baked normal map; the actual FBX roundtrip images retain that evidence for native-distance review.

To rebuild, copy this directory to a working location and run:

```sh
python3 rebuild.py --root /path/to/working/copy --blender blender
```

The recipe uses Blender 5.2.2 LTS and four CPU threads. It writes only in the supplied bundle. Rebuilding changes source/export hashes and requires fresh validation and review; it does not automatically approve or publish a new candidate. Image paths are bundle-relative or packed. The integration review corrected the standalone `inspect.py` diagnostic to use these same relative paths; the Blender art and baked payloads remain byte-identical to the author's frozen delivery.
