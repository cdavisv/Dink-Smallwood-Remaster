# Generated kit LODs may not change a mesh's size (SM_Corpse_Mother_PR 29.5 vs 26.8 cm, 23 Nov 2026)

Found by art-gore-2 (Master log 23 Nov 08:50): after any import of the corpse kit, SM_Corpse_Mother_PR measured 29.5 cm tall
against the 26.8 of stonebrook.json, and Dink.Art.ImportedAssetScaleAndMaterials failed (69/70).

## Which number is right
26.8. art-gore-3 (notes 23 Nov, item 3): the FBX measures 0.2681 m in Blender, the kit manifest says 0.268, master's
package (one LOD) is 26.8. The 29.5 appears only after the importer has re-saved the mesh with generated LOD1/LOD2.

## Cause (importer)
- import_town_exteriors.py re-imports a kit mesh whenever its stamp (FBX size + mtime) differs, i.e. in every copy other
  than the one that made the package, and then calls add_kit_lods.ensure_lods on every single-LOD mesh over 5,000
  triangles (A200, #200). The Mother corpse (51k triangles) gets engine-reduced LOD1/LOD2.
- A static mesh's bounds are the union of ALL its LODs (engine StaticMeshBuilder.cpp: `MeshBoundsBuilder +=
  StaticMeshLOD.SourceMeshBounds` for each LOD). The reduced LODs stand up to 2.7 cm higher than LOD0, so the mesh
  measures 29.5. ensure_lods' own check allows 3 % of the extent per section and LOD, so it did not catch it.

## Fix
ensure_lods compares the mesh's bounds before and after generating LODs. If any side moved more than 0.5 cm, a kit mesh
keeps its single imported LOD (metadata tag DinkLods `<tag>:single`, so later runs leave it alone) and a warning names the
move. The ten A200 TARGETS keep their LODs as decided in #154 (a warning only; the corpse Maiden's bounds move 4.2 cm,
as they already do on master; no size row tests them).

## Proof
Headless in copy Saved/ArtHooks23Nov (master 9ada93f1a + this branch): corpse kit import (`DINK_KIT=Corpses
Scripts/import_town_exteriors.sh`, -nullrhi) then Dink.Art.ImportedAssetScaleAndMaterials, and the full Dink suite: see
the PR text.

## Not changed
The mtime-based reimport stamp (every copy re-imports every kit mesh). Worth a content hash later; not needed for this.
