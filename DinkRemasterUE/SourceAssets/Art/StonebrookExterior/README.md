# Stonebrook exterior art

Seven original Blender assets dress the starting house's exterior on screen 439: a long stone-and-timber cottage with modeled layered thatch, a branching oak with separate cupped leaves, a weathered fieldstone boulder, split-rail fence, individual grass blades, a 20 m meadow ground module and an 8 m irregular dirt-path module. The cottage front has a real door opening and shuttered windows. The modeled reed bundles are geometry; the house and trees use no full-object sprite cards.

The cottage is 18 m wide by 9 m deep at its walls, with roof overhangs and a chimney. Its opening is 1.5 m wide by 2.5 m high, offset 5.3 m east of the asset center on the front face. FBX converts Blender front-Y to Unreal front+Y. Placement uses screen source pixels and the same bilinear world transform as the original importer. The source center [285, 248.5] aligns the front door to the original trigger near [339, 294]. `geometry_checks.json` checks 15 rays through the actual cottage triangles at multiple heights and widths; all are clear. The source floor inside the doorway is a 22 cm stone sill that fits the character's step height.

`exterior_layout.json` replaces screen 439's legacy collision with the actual authored meshes. Retaining the old projected roof hardness would leave invisible 32 m blockers around the new 18 m cottage. The six meadow tiles provide physical ground; the cottage, fence, boulders and tree trunks block movement, while grass blades and dirt overlays have no collision. Ground tile origins are at their bottom center, with top Z = 10 cm; layout height -9.8 cm places the walking surface 0.2 cm above the original ground. Tile coverage is checked in `layout_checks.json`: an axis-aligned world grid, mapped back to source pixels, covers all four skewed screen corners with a 2 cm outer margin. All 2,501 sampled positions have physical floor beneath them.

The foliage manifest records `lod_union_dimensions_m` measured independently from all three FBX LODs as a source diagnostic. Correctly imported Unreal mesh bounds match LOD0's `dimensions_m`; the importer retains a strict 1 cm comparison and the tests separately require all three actual LODs. The earlier enlarged bounds came from incorrectly combining the three siblings into LOD0.

The south fence has a deliberate 4 m gateway aligned with the dirt path: `FenceSouth6` is omitted. This is a 3D traversal adaptation to give the farmyard a usable path into the neighboring screen; the other fence runs retain the original route. The meadow and path tile can extend slightly across the screen seam so walking out does not expose an art or floor hole. Screen quest-state fire and ruined-house art, animated foliage, realistic characters and the rest of the village remain future work.

`KIT_StonebrookExterior.blend` is the editable source, rebuilt with `../tools/build_exterior.py` in Blender 5.2.2 LTS. It reads the first kit's materials and creates four new 1024 px PBR sets (thatch, oak leaves, meadow and earth) from seed 439. No downloaded image or mesh is used. Existing oak, stone, iron and limewash textures are shared from `../Stonebrook/Textures`. Tree and grass include three LODs. Their leaf material is two-sided; Blender previews use normal strength 0.38; the Unreal bridge uses 0.35 XY strength and flips the green channel. Source and delivered files have SHA-256 rows and candidate status in `SourceAssets/asset_ledger.csv`.

Rebuild from the Unreal project root:

```bash
blender -b --factory-startup -P SourceAssets/Art/tools/build_exterior.py
blender -b --factory-startup -P SourceAssets/Art/tools/validate_exterior_geometry.py
python3 ../Dink-Smallwood-Remaster/tools/blender/dink.py validate --blend SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend --report SourceAssets/Art/StonebrookExterior/validation.json
python3 ../Dink-Smallwood-Remaster/tools/blender/dink.py export_ue --blend SourceAssets/Art/StonebrookExterior/KIT_StonebrookExterior.blend --out SourceAssets/Art/StonebrookExterior/Export --formats fbx,gltf --source-root SourceAssets/Art
blender -b --factory-startup -P SourceAssets/Art/tools/export_foliage_lods.py
python3 SourceAssets/Art/tools/validate_exterior_layout.py
python3 SourceAssets/Art/tools/record_stonebrook.py --exterior
```

`validation.json` records seven passing assets with no errors. Review warnings cover the cottage exceeding its preferred triangle target while remaining below the hard building budget, touching vertices inside joined architectural solids, lower LOD bounds, and intentionally open leaf/blade surfaces. `Export/manifest.json` includes per-asset export validation and expected bounds. `preview_exterior.png` is a Blender preview; in-game screenshots and walking tests are separate evidence.

Unreal does not interpret the companion exporter's sibling `_LODn` meshes as an FBX LODGroup; combining them merges the geometry into LOD0. `export_foliage_lods.py` therefore produces six separate FBXs, recorded in each foliage asset's `lod_fbx` list. Import LOD0, then attach LOD1 and LOD2 explicitly. Each file has exactly one render mesh; only LOD0 includes its custom collision. The source build runs this export step after saving. `foliage_lod_export.json` independently confirms all six files have zero zero-length normal vectors.

Oak LOD2 originally contained 27 coincident, reversed triangle pairs from collapsed branch geometry. Their smooth corner normals cancelled. The repair removes one duplicate face per pair, preserving every vertex, UV and exact bounds; the source generator applies the same repair after decimation. `foliage_normal_repair.json` records 162 bad corners becoming zero, with no change in dimensions.

Unreal preserves the repaired per-corner foliage normals (`recompute_normals=False`) and recomputes tangents. Recomputing normals on coincident leaf/branch vertices reintroduced cancelling normals after the source repair; preserving the validated source removed the remaining import warnings. Runtime art tests inspect the final rendered vertex normal buffers in every foliage LOD, rather than relying only on source normals or import metadata.
