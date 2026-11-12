# Window lighting V1 — candidate

This lighting-only profile binds the original six window placements, held builder/FBX fingerprints and accepted practical points. It preserves the complete scene outside the `lights` member. Values are native Unreal centimetres/lumens/K, not Blender preview wattage.

Six170lm/5000K rectangles,80×80cm, stand30cm outside the clear openings and point inward. Native transmission, shadowing, performance and final appearance are unapproved. Global sunlight/sky and adaptive exposure are unchanged; diagnostic EV−4.5 is never installed as a gameplay default.

Use `Scripts/house_lighting.py` for check/apply; `import_stonebrook_art.py` applies this authority during actual Stonebrook metadata generation. Historical kit source lights are superseded only for this owner. Do not rerun the old Blender builder to change lighting or replace newer accepted prop meshes.

Owner decision (12 Nov 2026): the source height went from 130 cm to 80 cm. With the 130 cm source the virtual-shadow-map shadow of these lights let thin bright lines through along the head of any character standing backlit near a window (Dink and Mother alike); at 80 cm they are gone, at 100 cm fainter, and no local-light shadow setting removes them. Width, lumens, colour, radius and position are unchanged. Evidence: `Docs/Verification/HeroDefectFixes_9Nov2026/Round3_12Nov2026/` and `Docs/Verification/HouseWindowLighting/SourceHeight80_12Nov2026/`.
