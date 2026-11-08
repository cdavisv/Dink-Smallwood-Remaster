# Woodland crest verification

The Blender composition adds 43 grass/tree instances to the immutable V3 context, for 359 placements and 62 mesh references. The source checker preserves all 519 original mesh objects and verifies the actual added identities/transforms against placement data. A current receipt binds both source files; independent review's stale-scene regression fails with the original checker and is rejected by the fix. The unmodified builder reproduces the placements and preview pixels exactly. See `PeerReview`.

The loaded editor geometry audit passes all 644 rooms with no house or neighbor intrusion. The closest room remains 20.869 m away. Actual game screenshots and a real keyboard exit/return pass are in `../VistaFinal/Rendered`. The full integrated native run passes 138/138 with zero warnings and 8,743 unchanged inputs. Its local run label ends in139 from an early estimate; the report's actual count is138.

The runtime layer is `Content/Dink/Data/Art/stonebrook_vista_v4.json`; `Scripts/build_vista_context.py --output <path> --check` verifies exact source regeneration. It uses no collision, overlaps, navigation, hidden shadows or hidden GI. Broader material and clothing work remains in progress.
