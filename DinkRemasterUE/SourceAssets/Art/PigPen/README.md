# Stonebrook pig pen 407 candidate

This source-only candidate replaces the pen's normal environment cards with the existing StonebrookExterior meadow, split-rail fence, grass, small fieldstones and trodden earth. It preserves all five live pig origins, original scripts, the west gate and the bully's eastern cutscene corridor. Runtime import and physical acceptance remain separate gates owned by the project importer.

`pigpen_layout.json` uses the same `dink-art/1` source schema as the courtyard. `generate_layout.py` rebuilds it from the canonical screen corners and original placement data. `source_inventory.json` retains every original ID, script, hardbox and editor type. The 62 raw placements include two overlapping hardness-only fence actors; 60 are normal visible placements. All 57 non-pig origins are hidden; five pig actors remain untouched for the creature presentation adapter. Background instances disappear with `hide_screen_visuals`.

The physical fence network follows the original enclosure centre-lines. Its west opening is x136.5, y230..286: 5.553 m across, leaving 4.993 m beyond the 56 cm player capsule. The outer western fence meets the courtyard's existing western fence at the screen seam. No new southern gate is invented. The old non-hard decorative rails P18/P23 are retired rather than made into new barriers; P23 would otherwise seal the original approach corridor. `layout_checks.json` records the geometry contract and explicitly labels it unimported.

Only ground and fences collide. Fieldstone pebbles, grass, dirt and grain do not. The feed-script target remains [200,180..400,306], with a player fixture at 300,250. The east corridor x500+ stays free of physical obstacles for Milder's diagonal scripted680,200 ->542,338 entry (canonical source660,200 ->522,338; DinkC X includes the20px screen margin). Pigs retain P02/P05/P06/P07/P11, their `die` scripts, brains, save IDs and feeding choreography.

Existing dependencies are listed in `../StonebrookExterior/exterior_manifest.json`. The importer must reuse those already imported paths, not import copies from PigPen. `art_manifest.json` lists the one new static asset. Dirt-path geometry is corner-anchored: source X 0..8 m and imported Y -2..0 m. The generator compensates for that pivot when placing centre-line spans; the meadow and fences are centre-anchored.

`KIT_PigPen.blend` contains original project-authored wheat kernels, informed by the extracted 431_04 grain sprite. `SM_FeedScatter_Wheat_01` measures 25×18×0.309 cm with a ground-centre pivot. Its 80 individual kernels are 7–9 mm long. There is no opaque backing disc and no collision geometry. One constant rough PBR material, `MI_PigPen_Wheat`, avoids unnecessary textures for this tiny asset. The same asset can dress original P37/P59 and the existing transient 430/431 actors while preserving their trajectory/timing.

The actual validator requires three LODs for this non-Nanite small prop. Loaded source triangle counts are 1280/672/208. Separate FBXs each contain exactly one render node, UnitScaleFactor 100 and no zero normals; `feed_lod_export.json` verifies them. Import `lod_fbx[0]` only, then attach the other two using the verified explicit `import_lod` path. The combined companion FBX is retained for source interchange and must not be merged into LOD0.

```bash
blender -b --factory-startup -t 4 -P SourceAssets/Art/PigPen/build_feed_scatter.py
python3 ../Dink-Smallwood-Remaster/tools/blender/dink.py validate --blend SourceAssets/Art/PigPen/KIT_PigPen.blend --report SourceAssets/Art/PigPen/validation.json
python3 ../Dink-Smallwood-Remaster/tools/blender/dink.py export_ue --blend SourceAssets/Art/PigPen/KIT_PigPen.blend --out SourceAssets/Art/PigPen/Export --formats fbx,gltf --source-root SourceAssets/Art
blender -b --factory-startup -t 4 -P SourceAssets/Art/PigPen/export_feed_lods.py
python3 SourceAssets/Art/PigPen/generate_layout.py
```

No Unreal imports/builds, generated-map edits or old-kit changes are part of these commands. Source validation passed 1/1 with zero errors and warnings. `preview_feed_scatter.png` is a Blender source preview, not a game screenshot. Before/after in-game evidence belongs under `Saved/Playtest/evidence/pigpen-*`.

The first rendered pass exposed green gaps between irregular dirt strips. The source now uses4m-wide spans with about0.8m longitudinal overlap and tiny deterministic row/column height offsets. Ground/fence collision and all pig origins are unchanged; the revised soil requires the next import/render comparison.

Grain presentation sits at0.6cm, above the highest soil patch at0.496cm. The transient marker still follows the original60cm-root trajectory; its mesh offset is-59.4cm. This avoids embedding the tiny kernels in opaque soil. Imported-asset regression compares kernel bottoms against actual delivered soil mesh bounds.
