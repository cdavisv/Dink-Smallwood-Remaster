# Stonebrook fields — source candidate

Original Blender terrain and conifer dressing for source screens471 and438.
This folder does not modify the original scripts, placement identities, enemies,
quests, screen exits or runtime data. Import and real rendered after-tests are
separate gates owned by the coordinating agent.

## Source fidelity and collision contract

Screen471 is a broad S-shaped stream, not an empty meadow. Its painted water is
smaller than its original physical blocked envelope. The fitted grass ends at
that envelope; a descending earth bank fills the band down to water at -0.8m.
There is no original bridge and none is added. Its three conifers and one oak
have original roots outside the south screen edge; their positions are retained
and they add no new gameplay colliders.

Screen438 has a small pond, painted low rocks, one broad tree and six original
pillbug actors. All six pillbug IDs, including vision1 placements, remain live.
Its original pond hardness is a closed Low ring, not filled water: the interior
is inaccessible through normal walking but must not become a new solid region.
The broad original willow uses the existing broadleaf oak as a candidate visual
substitute. A distinct drooping willow remains future art polish.

Both layouts request:

- `hide_screen_visuals`: retire the old baked ground/debug-prism visual mesh.
- `authored_collision_screens`: replace Solid with exact fitted dry-land support
  and the visible tree trunk. This avoids retaining arbitrary invisible walls.
- `preserve_low_collision_screens`: retain original CollisionLow, which includes
  both `low` and `fill_water`; keep its Pawn-block/projectile-pass semantics.
- Every bank and water element has `collision:false`. Bank UCX exist solely
  because the source floor class requires them; they are never enabled in game.
- Water has no UCX and no physical sheet. Its opaque reflective PBR surface has
  original baked small ripples and optional modest `uv_pan_speed:[.006,.001]`.

No blanket grass collider covers forbidden water. Low rocks are dressed with
nonblocking fitted instances of the existing fieldstone; the original Low
channel remains authoritative. Tiny isolated source Low pixels are recorded in
the inventory, not silently removed. No fences or new passages are invented.

## Reproduction

Tools: Blender5.2.2LTS, host Python3.14, Pillow, pinned Shapely2.1.2.
Install the optional geometry helper into a temporary target, not system Python:

```sh
uv pip install --python /usr/bin/python3 --target /tmp/dink-fields-tools314 shapely==2.1.2
/usr/bin/python3 SourceAssets/Art/StonebrookFields/prepare_fields.py
blender -b -t 4 --python SourceAssets/Art/StonebrookFields/build_fields.py
blender -b -t 4 --python SourceAssets/Art/StonebrookFields/refine_pine_lods.py
blender -b -t 4 --python SourceAssets/Art/StonebrookFields/export_fields.py
blender -b -t 6 --python SourceAssets/Art/StonebrookFields/preview_fields.py
```

The generator derives canonical pixels from original placements/corners, traces
the largest painted blue component, and partitions each sheared world quad into
land, bank and water. Constrained Delaunay triangulation retains holes rather
than bridging them with convex collision. Maximum module width/depth is6m.
Source SW pivots use Blender+Y importing as Unreal-Y, with explicit inverse-world
layout anchors; no inherited house-floor offset is required. Terrain texture
coordinates are continuous in world space across chunk edges.

`KIT_StonebrookFields.blend` remains fully editable. The conifer has three
independently modeled LODs, a lower-trunk UCX and genuine opaque needle geometry,
without alpha cards. Individual LOD FBXs prevent Unreal combining sibling LODs.
Old kit meshes, materials and textures are read as source references, never
rewritten. The new water texture files are original procedural256px PBR maps.

## Validation and explicit policy exceptions

`validation_raw.json` preserves the unmodified companion-validator result.
`validation_exceptions.json` records every waived error by asset and aborts on
any unexpected error. This is **not** a clean strict validator pass:

- SNAP: source-fitted shorelines and sheared screen boundaries cannot all lie
  on the0.5m grid without changing original physical land/water boundaries.
- SCALE_RANGE: one very small clipped boundary sliver closes the exact surface
  partition; it is deliberately retained rather than leaving a terrain hole.
- COLLISION_MISSING: the water modules intentionally have no physical collider.
- Pine triangle count may exceed the preferred8k foliage target while staying
  under the hard25k limit. The receipt records actual three-LOD triangle counts.

All exports are independently checked for FBX UnitScaleFactor100 and zero
zero-length normals. `layout_checks.json` quantifies the terrain partition and
protected actors. Geometric source checks do not substitute for runtime sweeps.

## Baseline evidence

Before importing this kit, the frozen stage captured six real GPU screenshots:
`/tmp/dink-stonebrook-fields-stage/Saved/Playtest/fields-before/receipt.json`.
Setup debug travel is explicitly recorded; subsequent W input is real:

-471 north bank:150,100 →136.391,204.582, physically blocked at the bank.
-439 west edge →438: arrival598.430,320.246.
-438 west-of-pond corridor:300,160 →298.321,256.116.

Private game78861 and Xvfb78735 exited cleanly after capture. Protected visible
games4028335 and45497 remained alive and received no input. No claims of final
rendered or walking acceptance are made by these source-only files.

## Rendered first-pass findings and source correction

The first private after-test preserved source boundaries and real transitions,
but the independent low pine LODs lost entire branch tiers. `refine_pine_lods.py`
now derives LOD1/2 from every one of the original16 whorls,112 branches and560
opaque bough cores, omitting fine needles and simplifying core detail. LOD0 and
trunk UCX remain unchanged. Actual triangles are22444/9004/6764. Three original
aquatic accents now root atwaterZ-80cm rather than hovering atlandZ0.

The initial after receipts are preserved separately in the isolated stage
`Saved/Playtest/fields-after`. They include realW439→438/471 transitions, dry
corridors, water-boundary rejection, vision0/1, and realF far rejection/near hit
via original en-pill sprite3. Normal bugs later stalled against the pondLow;
that movement issue is being investigated separately. Lighting variants at the
same close camera remained pale; Sun8/Sky1 and all camera settings were restored.
No final acceptance is claimed until the corrected source is reimported and seen.

Final source validation retains three near-coincident-vertex warnings (two pairs
per LOD, separation9.48micrometres at upper branch junctions nearZ11.8m). They
are not zero normals; the unchanged LOD0 export and all new LODs independently
pass the actual FBX normal check. These warnings remain visible in the raw report.
The final LOD comparison is `preview_pine_lods.png` (left0, centre1, right2).
