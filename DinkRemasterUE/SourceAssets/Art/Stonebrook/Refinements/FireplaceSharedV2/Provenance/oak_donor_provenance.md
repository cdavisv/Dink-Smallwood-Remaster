# Shared surface provenance

All maps were authored/baked locally in Blender5.2.2 with CPU affinity0,1 and2threads. No paid provider, new image generation or UE execution occurred during this source registration.

Oak longgrain base color uses the immutable existing generated reference `Inputs/OakReference/AgedOak_Albedo_Raw.png`,SHA2562475c5a8a57e5d85570934d76b4a6566486a88dddfd7dff085a52c3e4209799f. Its original prompt and provenance are preserved alongside it. Original tool: built-in image_gen,model not exposed; no new call here. It is not a measured scan. The reference feeds BC only through periodic Blender shader sampling/tint. Independent periodic procedural microrelief and roughness supply N/ORM; no normal or roughness is extracted from albedo. Endgrain and plaster are procedural. V2 endgrain reduces regular bands and adds independent multiscale warp. No roof-specific AO, baked light, object-name dependence or atlas is present.

Registered materials and image names differ from Root-approved QA candidate only by SharedCandidate->Shared normalization and project-relative paths. Every PNG byte remains exact; fresh reopened source/shader/pixel equivalence is recorded. Author recipe `build_library.py` is copied with name normalization only. Reproduction must use a new copied directory to avoid overwriting indexed source payloads. Current source registration retains candidate status until native optical and runtime review.

The three opaque and three derived camera material definitions share the same9 maps. Derived camera graphs preserve the established opacity/shadow contract rather than creating private surface variants. See the authoritative registry for IOR/F0/green-flip and parent-role relationships.
