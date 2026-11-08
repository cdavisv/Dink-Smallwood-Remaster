# Pine refinement V3 — source candidate

This isolated candidate replaces the old flat diamond boughs with Sapling-generated branching and layered, original needle sprays. The young conical evergreen is adapted to the existing game footprint, rather than presented as an exact botanical reconstruction. Its source style review passed; Unreal import, alpha-mip behavior and actual game-camera appearance remain to be reviewed.

## Delivery and dimensions

`PineRefinementV3.blend` contains the editable three-LOD asset `SM_Pine_Stonebrook_V3`. Three separate `Export/*_LOD0/1/2.fbx` files contain one render LOD each; only LOD0 includes UCX. Static FBX coordinates are metres with header UnitScaleFactor 100. The mesh has a ground-level base pivot, identity transforms and dimensions 5.780095 × 5.865982 × 13 metres. The original trunk UCX vertices, faces and world transform are exactly preserved (approximately 46 × 43.75 × 200 cm). Lowest foliage is 1.07463 m.

LOD triangle counts are **22,270 / 10,942 / 6,784**, with two material slots and no Nanite requirement. Each LOD retains all **584 branch splines and 1,853 spray placements**; actual source ID attributes are independently checked. Lower LODs simplify branch cross sections and spray curvature, retaining every whorl and crown tip. The final equal-light, uncropped comparison and a downsized source thumbnail are in `Previews/`. These are Blender renders, not evidence of Unreal mip behavior.

## Materials and masking

Use only `MI_PineV3_Bark` and `MI_PineV3_Sprays` from `art_manifest.json`. Each uses original 2048px BC, tangent normal and ORM maps. BC is sRGB; N/ORM are linear. ORM packs occlusion/roughness/metallic. Normal green inversion and strength .5 are explicit in the manifest. Sprays require two-sided **masked** rendering, alpha clip **.12**, and alpha-coverage-preserving BC mips. The Blender graph uses `GREATER_THAN(.12)` before surface alpha, matching the planned binary engine mask. It does not rely on fractional transparency. Source mip statistics include actual coverage above the clip threshold, not only mean alpha; the 1px average alpha is .345098. Engine compression and distant sampling still need rendered QA.

`Working/NeedleSprig_High.blend` is the original atlas source: paired, closed modeled needles on fine woody twigs (6,336 needles), rendered for unlit albedo and tangent normals. Bark is original procedural texture work. No photo texture or downloaded tree mesh was used. The auxiliary `T_PineV3_Needles_*` maps and `pine_materials.json` document intermediate procedural work; they are not imported or assigned to the final asset. `pine_materials_used.json` and `art_manifest.json` are authoritative for the final two slots.

## Tools and provenance

Sapling Tree Gen **0.4.0**, GPL-3.0-or-later, supplies parameter-generated Weber–Penn branching using its `small_pine` preset, seed47103, with project tuning. The tool release ZIP is pinned to SHA256 `3022b572ab0000754cf9b77740b8161b86bb85380c959b321702fa9347cadb4e`, checked against published SHA256SUMS. `tool_receipt.json` records source, preset digest and installation details. The official Blender host denied download access, so the maintainer's linked release was used. The add-on is extracted under `/tmp/dink-qa-tools/sapling` and imported per process; no global Blender add-on preferences or desktop configuration are changed. Tool code is GPL; original generated project geometry and PBR authorship are recorded separately, without relabeling the tool as CC0.

Primary references: [official listing](https://extensions.blender.org/add-ons/sapling-tree-gen/), [maintainer release](https://github.com/meet-brad-ch/add_curve_sapling/releases/tag/v0.4.0), [maintainer guide](https://github.com/meet-brad-ch/add_curve_sapling/blob/main/README.md), [preset documentation](https://projects.blender.org/extensions/add_curve_sapling/src/branch/main/docs/presets.md), [USFS Scots pine reference](https://research.fs.usda.gov/feis/species-reviews/pinsyl), and [Virginia Tech pine reference](https://dendro.cnre.vt.edu/dendrology/syllabus/factsheet.cfm?ID=112). Repository CONVENTIONS and the remaster art bible guide export/budget/style decisions.

## Rebuild

From this folder, with Blender5.2.2 LTS and Python Pillow/NumPy available:

```sh
python Tools/setup_sapling.py
blender -b -t 6 --python Tools/make_textures.py
blender -b -t 6 --python Tools/render_needle_atlas.py
blender -b -t 6 --python Tools/build_pine.py
blender -b -t 6 --python Tools/review_lods.py
blender -b -t 6 --python Tools/validate_pine.py
blender -b -t 6 --python Tools/export_pine.py
```

The companion repo exporter is read-only and must remain available at its established adjacent path. `DINK_SAPLING_TOOL` can select an alternate isolated location containing the pinned release. Generation uses fixed seeds; rendering may vary with Blender/device versions. `Tools/finish_source.py` is an optional datablock-name cleanup already incorporated into the generator.

## Validation and limits

`pine_validation.json` passes with **0 errors / 5 warnings**: the deliberate studio ground outside the export collection, the preferred 8k foliage target (LOD0 remains below the agreed 25k hard limit), and one intentional open needle-card boundary warning per LOD. There are no wire edges or edges shared by more than two faces. `pine_source_checks.json` verifies actual ID retention, zero invalid corner normals, exact UCX preservation, alpha coverage, and all **227 original Fields artifact hashes**. `fbx_inspection.json` independently verifies file units, normals and per-file geometry. The close bough, portrait and three-LOD source reviews passed; a more mature broad pine silhouette and real engine mip coverage remain possible later refinements.

`candidate_ledger.csv` is local only. `art_manifest.json` proposes a distinct Refinements asset path; the parent integration task owns final mapping and installation. No original Fields file, global ledger, runtime layout, or existing asset was replaced. The protected-source receipt records the current global and original Fields hashes read-only. All delivered assets remain candidates pending engine review.
