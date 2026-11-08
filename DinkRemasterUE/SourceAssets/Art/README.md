# Stonebrook Blender art

The first authored art pass replaces the starting house's flat sprite furniture and large debug prisms with real 3D models. The room uses oak planks, limewashed timber walls, open windows, a 1.5 m clear doorway, a closed ceiling, a stone fireplace, beds with cloth covers, a table and chairs, barrels, a woven basket, a pig-feed sack and a pie. Authored Dink and mother candidates now replace the player mannequin and mother sprite; their editable sources, CC0 provenance and four-LOD pipeline are documented in [Characters/README.md](Characters/README.md). The starting house, cottage yard and pig pen have authored candidates; other regions still use the greybox.

`Stonebrook/KIT_Stonebrook.blend` is the editable source. `tools/build_stonebrook.py` reproduces all 14 models and seven 1024 px material sets from seed 1997 without downloaded models or images. Geometry has applied transforms, ground pivots, UVs and separate `UCX_` collision hulls. The FBX files declare metre units and import into Unreal centimetres at scale 1. The GLB files are previews containing embedded textures. `Stonebrook/preview_kit.png` shows the modeled kit under Blender lighting; game screenshots are separate evidence.

`Stonebrook/art_manifest.json` records mesh dimensions, material slots and relative texture paths. `Stonebrook/room_layout.json` places the kit in original screen pixels so the Unreal importer can use the same world transform as the game. The sack and pie retain their original live object IDs (`S001_P52`, `S001_P51`). The floor has its walking surface at Z=0, the ceiling its underside at Z=0, and wall modules start at their left floor corner. Materials provide base colour, OpenGL tangent normal and packed occlusion/roughness/metallic PNGs. Unreal must flip the normal green channel and import ORM as linear masks. Blender preview normal strength is 0.38; the Unreal material bridge uses a restrained 0.35 XY strength. FBX mirrors Blender Y: floor/ceiling modules extend toward negative Unreal Y, so the room importer offsets their pivot by their scaled Y extent to align the layout's northwest footprint corner.

Rebuild from the Unreal project directory:

```bash
blender -b --factory-startup -P SourceAssets/Art/tools/build_stonebrook.py
python3 ../tools/blender/dink.py validate --blend SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend --report SourceAssets/Art/Stonebrook/validation.json
python3 ../tools/blender/dink.py export_ue --blend SourceAssets/Art/Stonebrook/KIT_Stonebrook.blend --out SourceAssets/Art/Stonebrook/Export --formats fbx,gltf --source-root SourceAssets/Art
python3 SourceAssets/Art/tools/record_stonebrook.py
```

The companion project's [asset conventions](../../../tools/blender/CONVENTIONS.md) and [Blender workflow](../../../tools/blender/README.md) define the validation gate. The export uses the documented [Epic FBX pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine): separate convex collision pieces preserve doorway openings. `validation.json` and `Export/manifest.json` record the actual results; export rejects assets with errors. Warnings are retained for art review: joined furniture can need more texel density than one shared 1024 px set, and the bed, basket and barrel exceed their preferred triangle target while remaining below the hard budget. This is a local art candidate, with ledger status `candidate`; animated fire, ruin variants and wider-world art remain pending.

## Cottage yard

The [exterior kit](StonebrookExterior/README.md) adds seven assets for the cottage, yard ground, dirt path, fencing, oak, boulders and grass. Both editable Blender scenes are original project art. Import the interior first with `Scripts/import_stonebrook_art.sh`, then the yard with `Scripts/import_stonebrook_exterior.sh`; it reuses the interior barrels and feed sack. The importer assigns physical collision, validates centimetre dimensions, and publishes text dressing manifests without changing generated maps.

Foliage uses three explicit single-LOD FBX files, attached with Unreal's `import_lod`, and preserves its repaired source normals. The art regression checks verify actual loaded LOD counts, dimensions, materials, Nanite usage and rendered foliage normal buffers. Real keyboard walking and screenshots validate the physical scene separately. See [the import notes](../../Scripts/ART_PIPELINE.md) for the verified importer requirements and [desktop playtests](../../Scripts/Playtest/README.md) for the reproducible test session.


## Pig pen and Milder

| Delivery | Editable source | Integration |
|---|---|---|
| Five original live pigs | `Creatures/Pig/SK_Pig.blend` | Own26-bone rig,3mesh LODs, Idle/Walk/Run/Feed clips; `Scripts/import_creature_art.sh` |
| Pen environment and loose wheat | `PigPen/KIT_PigPen.blend` and `pigpen_layout.json` | Reuses the exterior kit, preserves the west gate; `Scripts/import_pigpen_art.sh` |
| Milder | `Characters/Milder/SK_Milder.blend` |89-bone shared humanoid rig,4LODs, plate/blue cloth/leather; `Scripts/import_milder_art.sh` |

Detailed source/provenance notes are in [Pig](Creatures/Pig/README.md), [Pig pen](PigPen/README.md) and [Milder](Characters/Milder/README.md). Pig skin/muzzle revision2 reduces clipped outdoor albedo without changing its geometry or motions. Grain sits above the opaque soil; its original script actor and trajectory remain unchanged. Milder attaches through the original `s1-bul` script identity and survives save/size/facing changes.

The374-row shared asset ledger includes these candidates and preserves all existing audio decisions. A validated source asset is still an art candidate: broader terrain, house-fire variants, remaining creatures/NPCs and deformation/material polish need further work. Rendered evidence is separate from Blender previews, under `Saved/Playtest/evidence/pigpen-final-focused`.
