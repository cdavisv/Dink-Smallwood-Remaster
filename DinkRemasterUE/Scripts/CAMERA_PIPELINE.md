# Interior camera material pipeline

The native camera follows the remaster plan’s shorter indoor arm, shoulder view and dithered architectural occluders. It changes only locally controlled camera presentation and the Camera collision channel of fully supported tagged mesh components. Pawn collision, input, yaw, warps and scripts retain their gameplay behavior. Original materials and collision responses are restored on leaving or destruction; unsupported materials retain their original camera collision.

Run `DINK_CAMERA_CHECK=1 Scripts/import_camera_materials.sh` to validate without changing assets or runtime Data. Run the script without that environment variable to generate missing unique variants and author camera tags/config. Existing variants are validated and never overwritten; choose a new `DINK_CAMERA_REVISION` to author a new material revision. Original Oak/Limewash packages remain byte-identical.

The variants duplicate the existing Blender-authored PBR materials and add DinkCameraOpacity through a ShadowPassSwitch. They use masked rendering, temporal opacity dithering and clip0.5, with default surface and shadow opacity1. This preserves direct shadows while fading visible architecture. The recipe records source material hashes, variant paths and validation results in Saved/Art/camera_materials_report.json. No new external textures, generators or paid assets are involved.

The framing footprint is derived from actual imported floor bounds and all authored transforms. Current support requires a horizontal convex quadrilateral. Coordinates are rounded to0.00001cm before hull construction to remove coincident float noise; comparison tolerance0.02cm. The camera computes bottom frustum rays from Unreal’s actual viewport projection, with a5cm floor inset and180cm minimum visible floor depth. It can switch shoulders and pan within150cm. Missing/unsupported framing data retains the normal camera policy.

Architecture receives explicit camera_occluder tags from kit_wall, kit_ceiling and kit_piece source classes; authored false overrides remain respected. Do not replace actual component obstruction queries with bounding-box-only fading: doorway holes must remain clear.

Dink/Camera is included in package.sh cook directories because JSON string paths do not create cook dependencies. Source/build/PIE validation does not prove packaged camera behavior; verify a new package separately.

Native stage verification and actual rendered W exit/return evidence are linked in AGENTS.md. The camera does not supply exterior scenery for the starting room; that art is developed separately.
