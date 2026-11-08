# Stonebrook pig art candidate

Original project-authored domestic pig for `S407_P02`, `P05`, `P06`, `P07` and `P11`. The asset is an organic, continuous voxel-fused anatomical skin surface with a tapered domestic head, actual recessed nostrils, surface-seated mouth crease, small inset eyes, fleshy ears, cloven horn toes/dewclaws, curled tail and sparse modeled stubble. There are no sprite cards or third-party body/texture assets.

Anatomical reference only: [South Dakota State University livestock judging manual, External Parts of Swine, hosted by Utah State University Extension](https://extension.usu.edu/davis/files/Livestock_judging_manual-South_Dakota_State_University.pdf). No illustrations, reference photographs, geometry or textures from that publication are incorporated. Shape, rig, procedural materials and motions are original project work; no paid generators/downloads were used.

## Source and regeneration

Blender5.2.2LTS, Metric/metres, object transforms applied. Run these in separate background processes from any directory:

1. `blender -b -t 6 --python Tools/build_pig.py`
2. `blender -b -t 6 --python Tools/bake_pig.py`
3. `blender -b -t 6 --python Tools/export_pig.py`

The first script creates the editable anatomical mesh/compact rig, bone-heat skinning, rigid eye/ear/hoof masks, nearest-surface transfer for fine disconnected bristles, four actions and review portraits. Optional environment variable `PIG_PREVIEW_ACTIONS=Pig_Run,Pig_Feed` limits preview renders without changing the asset/actions. Bake creates unique UVs and2048 BC/N/ORM PNGs; the finalizer generates three real skeletal LODs, checks source geometry and animation continuity, then saves `SK_Pig.blend`. `Working` files are intermediate checkpoints. Final report/manifest values are authoritative.

## Rig and animation contract

Own quadruped skeleton, not Manny. Root `root` has identity rest basis (head0, tail+Y); source nose/actor-forward is+X, up+Z. Feet rest on Z0, pivot between feet. The final compact26-bone rig follows the guide core: root/pelvis, spine_01..03, neck_01..02, head/jaw, paired ears, tail_01..03, front upperarm/lowerarm/hand and rear thigh/calf/foot per side. The source builder uses convenient fore/hind aliases; finalization normalizes names and splits the final spine/neck spans, with every original animated global matrix verified unchanged to better than0.000001. All vertices have normalized weights, at most four influences. Bone heat keeps torso tissue anchored while the explicit feature masks prevent tiny eyes/hooves/bristles drifting away.

Actions are baked at30fps with no root motion:

| Action | Duration | Policy | Nominal speed |
|---|---:|---|---:|
| Idle |2.0s |Loop |0cm/s |
| Walk |0.6s |Loop |80cm/s |
| Run |0.4s |Loop |400cm/s |
| Feed |0.4s |One shot, neutral enter/recover |0cm/s |

Walk uses a four-beat foot sequence. Gallop uses paired fore/hind timing:0.64m stance sweep across0.16s establishes400cm/s nominal speed, followed by airborne recovery. The runtime retains the original gameplay positions/speeds: observed pigs can move approximately839cm/s, so its blendspace/play rate scales the400cm/s Run rather than changing the brain. Feed is a quick natural sniff/nibble intended only for actual nearby transient grain while stopped; movement interrupts it. Walk direction sequences41/43/47/49 are not feeding states. The original death script hides/removes pigs immediately, so no death clip is supplied at this stage.

`pig_pose_validation.json` checks every source animation frame for limb-chain continuity, stationary root and matching start/end poses. `pig_rig_report.json` records all26 final source rest matrices and profile settings. `pig_manifest.json` supplies animation durations/fps, names, source-forward and fitted torso/head box offsets/extents in actor-forward centimetres.

## Export and integration

Source stays in metres. The exporter converts only its temporary process copy to centimetres: mesh/edit-bone positions and pose-location keyframes times100, unit scale.01, FBX_SCALE_ALL/header1. It preserves identity root, armature wrapper `Armature`, no leaf bones, no extra roots. Three individual mesh FBXs have animation disabled. Four armature-only animation FBXs bake one selected action each, without NLA/all-action export. Unreal must import each mesh LOD explicitly; sibling objects in a single FBX did not reliably form real LODs in this project's earlier tests.

Source `.blend` retains full PBR graphs. Temporary FBX export graphs are cleared after saving the source because Unreal materials/textures come explicitly from the manifest. Eye roughness is separate; skin and damp snout have restrained subsurface settings. All four material families share the unique-UV2048 atlas set, with normal green inversion specified for Unreal.

Candidate status: the broad diagonal flank flap is resolved by the torso mask. A small compressed underbelly/hip crease remains visible in gallop quarter04; this is explicitly accepted for the first in-engine animation/camera review, not claimed as finished deformation polish. Review anatomy, lighting, fast locomotion and feed transitions in-engine before approval. No shared asset ledger changes are made until coordinated with the parent agent. This folder does not change gameplay, live maps, audio, existing characters, build outputs or test logs.

## Outdoor albedo review revision

Revision `skin-muzzle-linear-half-v2` halves only Skin/Muzzle linear albedo after the first outdoor screenshot clipped the pale source skin. The deterministic procedural palette and resumed procedural bake use the same corrected values. `Tools/correct_pig_albedo.py` migrates the stable baked source on its existing UVs, using the retained original atlas and nearest input texels during the color-only bake; it restores normal texture filtering for rendering. It never compounds the correction on a previousv2 atlas.

Skin median linearRGB changed from approximately[.468,.332,.314] to[.235,.165,.156]; muzzle from[.479,.250,.238] to[.238,.125,.120]. All480 eye,1168 hoof/dewclaw and450 stubble UV-centroid samples retain their original RGB bytes. The median dark nostril/lip color is unchanged; mixed boundary texels follow adjacent skin/muzzle recoloring. Normal/ORM PNGs and all seven FBXs are byte-identical. The combined mesh topology/positions/UV/weights/rest-bone/action fingerprint is identical before/after. No SSS, exposure, geometry, rig or gameplay change is included.

Original BC atlas and pre-revision source/metadata snapshots are retained under `Working/AlbedoV1`. `Working/albedo_v2_validation.json` records the protected hashes and geometry fingerprint. The actual outdoor comparison passed for this iteration: skin detail/pink color recovered and dark details remain intact. Coarse close-range pores and the documented gallop crease remain candidate polish. See Saved/Playtest/evidence/pigpen-final-focused.
