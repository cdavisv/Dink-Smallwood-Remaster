# Window lighting V1 — candidate

This lighting-only profile binds the original six window placements, held builder/FBX fingerprints and accepted practical points. It preserves the complete scene outside the `lights` member. Values are native Unreal centimetres/lumens/K, not Blender preview wattage.

Six170lm/5000K rectangles,80×130cm, stand30cm outside the clear openings and point inward. Native transmission, shadowing, performance and final appearance are unapproved. Global sunlight/sky and adaptive exposure are unchanged; diagnostic EV−4.5 is never installed as a gameplay default.

Use `Scripts/house_lighting.py` for check/apply; `import_stonebrook_art.py` applies this authority during actual Stonebrook metadata generation. Historical kit source lights are superseded only for this owner. Do not rerun the old Blender builder to change lighting or replace newer accepted prop meshes.
