# The Mother's remains measure 29.5 cm after a corpse kit import (importer finding), 23 November 2026

Branch `art/corpse-mother-lod-bounds`, one commit on master 9ada93f1a. Headless only; nothing here changes what the game draws.

## The finding (art-gore-2, 23 Nov)

After any import of the corpse kit in a private copy, `Dink.Art.ImportedAssetScaleAndMaterials` failed (69/70) on
`SM_Corpse_Mother_PR`: 29.5 cm tall against the 26.8 of `stonebrook.json`. The package had to be put back from master by hand.

## Which size is right

26.8 cm: the thickness of the body lying on the floor.

The 1997 picture (355 frame 1, placement S001_P34) is a lying body on a card of 1.70 x 1.25 m; it fixes the footprint, not the height.
The mesh's body section is 1.60 x 1.05 m on the ground (LOD0 box x -80 .. 80, y -52.6 .. 52.5 cm) with the pool card round it, which
fits that card. The height is the body's own, and all three sources of it agree:

| | height |
|---|---|
| the kit manifest (`Corpses/manifest.json`, `dimensions_m`, written by the Blender build) | 0.268 m |
| the FBX in the tree, read by Blender (no render): z -0.0177 .. 0.2504 | 0.2681 m |
| master's package, LOD0 (`describe_master.json`): box z -1.77 .. 25.04 cm, ONE LOD, 51,088 triangles | 26.81 cm |

## Where 29.5 comes from

`describe_after14.json` is the package that art-gore-2's import produced (kept in his scratch folder), read headless:

- LOD0 is unchanged: 51,088 triangles, z -1.8 .. 25.0 cm.
- It now has generated LOD1 and LOD2 (`DinkLods` tag `kitlods1:51088:1.0,0.5,0.25:1000,2000`).
- LOD1 (25,542 triangles in the body section) has part of the underside at z -4.3 cm: 2.5 cm below LOD0's lowest point, under the floor
  and under the pool card (z 0.6), where nothing sees it. LOD2 is within 0.1 cm of LOD0.
- Unreal's mesh bounds cover every LOD: box z -4.35 .. 25.14 cm = 29.49 cm.

Why the import touched her at all: the importer's `DinkSource` stamp is the FBX's size and MTIME (`stamp_of`). Master's packages carry
`...:1794882825:town2` (the copy that imported them on 16 November); in any other copy the same FBX has another mtime, so every mesh of
the kit counts as changed, is imported again, and `add_kit_lods.ensure_lods` (the hook of #200) gives every single-LOD mesh over 5,000
triangles its LOD1/LOD2. Master's corpse packages hold one LOD each (`describe_master.json`: Mother, Joppa mother, soldier, dead Dink,
knight, maiden), so the same happens to all of them; only the Mother's LOD1 leaves the 1 cm tolerance.

## The change

- `stonebrook.json`: the Mother's row keeps the source height 26.8 and carries `bounds_tolerance_cm` 3.0 (the field the test already
  reads; three other manifests use it). 3 cm is far below any unit or scale error of a 240 x 240 x 26.8 cm mesh.
- `Scripts/tests/test_corpse_kit.py`: the row's size equals the kit manifest's source size; the tolerance covers the measured LOD chain
  and stays below 5 cm.
- `IMPORT.md`: what a corpse kit import does in another copy.

No package is changed: master's Mother keeps her single LOD.

## Not done here (for the code side)

- The mtime in the importer's stamp makes every kit import in another copy re-import and re-save every mesh. A content stamp (size and
  a hash) would stop that; the importer file is shared by three open drafts, so I left it.
- Master's corpse meshes have ONE LOD (the LODs of A200 were lost when the kit was imported again on 16 November). A kit import brings
  them back; nobody has committed those packages.

## Tests

Headless, copy `Saved/FableA` = master 9ada93f1a + this change and nothing else (0 source files differ, 0 extra), built clean:

- Clean build: OK, 0 warnings.
- `Dink.Art` 76/76 with the Mother package that the kit import of 23 November produced (three LODs, bounds 29.49 cm) in place:
  `Dink.Art.ImportedAssetScaleAndMaterials` passes. On master that same package failed it (art-gore-2's run of 23 November: 69/70).
- `Dink.Art` 76/76 with master's own package (one LOD, 26.81 cm) put back.
- `Dink.Gameplay.Probe` 29/29, all twenty chapter md5s equal the table of `packaged_probe.md` on master (Ch1 cff64df9d1 .. Ch20 b27010b31e).
- Python unit suite 1028 OK (master 1027 and the new one).
- Not run: a fresh corpse kit import with this row in place (the package above comes from one).
