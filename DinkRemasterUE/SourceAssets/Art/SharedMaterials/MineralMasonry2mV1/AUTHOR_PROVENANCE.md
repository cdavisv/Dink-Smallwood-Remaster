# Source and materials

Authoring: local Blender 5.2.2 LTS, Python/NumPy/Pillow. No paid services, network downloads, Unreal operations, canonical writes, commit or push. Only this QA folder is owned. The canonical derivative input path/hash and all 328 mesh records are in SOURCE_PRESERVATION.json. Checkout observed art/roof-native-current in <HOME>/Work/DinkRoofNativeDelivery; output is outside Git in this QA folder.

Original guide: References/64_05.png and placement receipt identify real S001_P19 / fireplace_brick / s1-h1-2, not sequence86 (which is the separate animated fire). Existing source geometry is authority for silhouette, aperture, chimney/roof interface and collision. Materials preserve coursed-masonry character and dark firebox; they do not reproduce the sprite's baked lighting.

Fieldstone maps: exact copies of exterior lane SharedIndividualStoneCandidateV1 maps, original CC0 Poly Haven rock_boulder_dry by Dimitrios Savva/Rico Cilliers. Donor recipe, physical-size assumption, normal attenuation and hashes retained in Provenance/stone_donor_manifest.json. No independent measured stone scale/BRDF claim. Generic surface has no private prop UV bake.

Iron and dull lead: exact exterior lane MetalworkV2 maps, manifest/CC0 source/finish recipe in Provenance/metal_donor_manifest.json. Iron uses fine scan structure from metal_plate_02 by Rob Tuytel with artist blackened finish; lead is artist-estimated, not scanned/calibrated lead. Prior V8 zinc is explicitly changed to dull lead flashing; Root must accept that material choice. One normal-map shader per material (no exterior UV1 variant selector dependency).

Oak: exact registered OakLime2mV1 OakLonggrain BC/N_GL/ORM maps, provenance copied. Logs use shared oak; no new private fuel atlas or emission map. Original atlas ember emission is replaced by physically non-emissive charcoal. No active fire VFX/light behavior is changed because no runtime assets/data are edited.

Mortar/soot: deterministic local artist-authored multiscale periodic noise, no photographic/calibrated claim. Shared 2m textures, material-appropriate albedo/roughness and fine height-derived OpenGL normals. ORM AO1/M0, roughness independent of baked lighting. build_textures.py preserves source algorithm/seed. Do NOT rerun this script alone over final donors: it writes a temporary procedural Fieldstone2m prototype which prepare_donors.py replaces with the exact exterior photographic maps.

Coursed stone: build_masonry.py combines shared stone and mortar into a reusable 2m square, ten .2m courses, .4m staggered blocks and approx8mm bedding; artist bevel normal and bounded block tone variation. No house/private UV bake. This is used on continuous chimney surfaces where individual-block maps alone read as a monolith. Existing modeled stone blocks use Fieldstone2m without double joints.

Rebuild order: build_textures.py; prepare_donors.py; build_masonry.py; Blender build_candidate.py; export_verify.py; audit_reopen.py; audit_binary.py; baseline_frames.py; render_review.py baseline/candidate; render_reuse.py. Absolute source paths are local authoring prerequisites, not portable cold-clone recipes. Final packed sources, maps, FBX and reports are portable review artifacts. Binary reader is copied unchanged from the interior-roof QA parser; its actual hash is in SHA256SUMS.json.
