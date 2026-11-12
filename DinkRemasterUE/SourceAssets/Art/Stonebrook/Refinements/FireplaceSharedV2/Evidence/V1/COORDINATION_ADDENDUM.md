# Shared graph contract clarification — 9 November2026

Post-freeze coordination with exterior owner; the 68 sealed payloads and candidate source are unchanged.

Fireplace QA Fieldstone2m uses the exact exterior donor maps, but its graph connects BC directly to Principled Base Color. It has no SharedSurfaceData/vertex tint. Exterior V6 uses SharedSurfaceData.R with factor .94+.10R. These are not graph-equivalent despite the same proposed MI_Shared_Fieldstone2m name. Exterior's registered contract should remain authoritative; Root must normalize/remap and review fireplace graphs or give the divergent QA proposal a distinct name before admission. Do not silently alias by material name.

All seven fireplace QA graphs use tangent NormalMap strength .7, ORM G/B directly to roughness/metallic, AO unused, opaque Principled. Exact same texture bytes alone do not prove identical material appearance. The reused oak graph also needs comparison with its registered shader before native binding.

Fireplace BlackenedIron2m/DullLead2m are separate material slots using direct maps; they do not implement exterior IronLead2Role's UV1.x selector. Any consolidation needs explicit role transport and review.

Fireplace FieldstoneCoursed2m is a generic derived stone-plus-mortar set. Exterior FieldstoneWall2m is a different photographed stone_wall set; retain distinct role names. Both coordinating Root and exterior owner were notified through their existing task threads. No canonical writes, native execution, or admission was performed here.
