# Meadow ground tint (14 November 2026)

Change: `environment.json` `grass.ground_tint`, `UDinkEnvironmentSubsystem::TintMeadowGround`, `TintA..TintD` in `M_Env_Terrain` (see `IMPORT.md`, "Meadow ground under the grass carpet"). Visual only. Before = master d2754903 plus the interior light change (branch `fix/interior-light-round7`), after = with the tint; same session, regenerated world. Script: `Scripts/PhotorealQA/r7_script.py <tag> g0 g1`.

| Sheet | Camera | What it shows |
|---|---|---|
| `ground_tint_tools440_close_before_after.jpg` | screen 440, scythe and hand tools in their clearings | the bare ground of the clearings is olive instead of pale straw |
| `ground_tint_tools440_above_before_after.jpg` | same, from above | as above; the field itself hardly changes |
| `ground_tint_meadow440_far_above_before_after.jpg` | screen 440 from 9 m above | meadow beside the bare earth: slightly darker and greener |
| `ground_tint_shore604_before_after.jpg` | pond shore, play camera | no visible change at the play camera (the carpet covers the ground) |

Measured on the first sheet (sRGB means): clearing 188, 188, 126 before and 174, 179, 106 after; grass field 128, 140, 72 and 123, 138, 63.

What the last look still faults:

- The clearing is still lighter than the field round it (the screen blends MeadowTurf with RockyGrass, which is not tinted), and its rim is a clean oval.
- The pale wedge shapes all over a field seen from above are the sunlit tops of the grass patches, not the ground: the tint does not touch them. They need work on the grass patch meshes or their material.
- The tools in the clearings are thin and flat (asset side).
