# Stonebrook pillbug — candidate source art

Original modeled blue-green/ochre terrestrial-isopod creature for the six live pillbug placements on screen438: `S438_P02` through `S438_P07`. This replaces presentation only. Existing actor identity, scripts, vision flags, health, damage, targeting, movement numbers, death and save state remain authoritative.

The source has seven closed overlapping domed thoracic tergites, a sheltered cephalon, posterior pleotelson/uropods, fourteen articulated walking legs, inset lateral compound eyes, protected mouthparts and two jointed antennae. Curved rolled edges, restrained ochre wear, cuticle carinae, tarsal sutures and procedural mottling/pores give physical surface detail. The anatomy is deliberately enlarged to the original fantasy creature's role; it is not a biologically scaled garden woodlouse. Lower-leg shapes remain simplified for the project's Fable/Gothic viewing distance and are candidate polish, not photoreal close-up anatomy.

## Authoritative source behavior

`bin/dink/story/en-pill.c` gives the normal scripted variants brain9, speed1, HP8, touch damage1, EXP5, base_walk130 and base_death140. Screen438 P03/P04/P07 run that script. Vision1 variants P02/P05/P06 retain their original placement state (HP20/touch damage2); the art profile also covers those origins without changing visibility or stats. The original source walk sequences131/133 each contain five75ms frames: a0.375s cycle. Base_attack is−1, so contact damage does not imply an invented attack animation. Current native death hides/deactivates the original actor immediately after its original script/editor_type6 effects; one-frame corpse art141/143 is an existing wider presentation gap, not permission to delay or alter death here.

Canonical screen438 timing0/speed1 diagonal motion is approximately823–846cm/s under its actual bilinear transform, measured by the runtime/collision owner. Those gameplay numbers remain intact. A400cm/s nominal run clip supports roughly2.1× playback at that speed instead of relabeling a slow walk.

## Files and reproducible build

Run from the Unreal project root using Blender5.2.2LTS:

```
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Creatures/Pillbug/Tools/build_pillbug.py
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Creatures/Pillbug/Tools/bake_pillbug.py
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Creatures/Pillbug/Tools/export_pillbug.py
python3 SourceAssets/Art/Creatures/Pillbug/Tools/inspect_exports.py
ALSOFT_DRIVERS=null blender -b -t 6 --python SourceAssets/Art/Creatures/Pillbug/Tools/review_final.py
python3 SourceAssets/Art/Creatures/Pillbug/Tools/prepare_pillbug_ledger.py
```

`Working/Pillbug_Procedural.blend` preserves original procedural surface graphs and modeled anatomy before final reduction. `Working/Pillbug_Baked.blend` is the uniquely unwrapped24k-triangle atlas checkpoint. `SK_Pillbug.blend` is the final editable metres source with all three real mesh LODs,43-bone own rig, named actions, relative texture references and a clearly separated nonexported studio. No Manny geometry, skeleton or third-party mesh is included. `Previews` contains procedural and final-atlas review poses. `pillbug_manifest.json` is the independent runtime-import source contract; it does not replace or modify the global creature manifest itself.

The generator uses companion read-only `dinkasset` helpers for rest-pose decimation, convention validation and FBX export. `Tools/pillbug_actions.py` owns the original metachronal gait and fixed-length two-bone analytic IK. The first smart-projection UVs had0.44% overlap; the corrected pipeline derives seams, conformally unwraps and packs the islands, yielding zero measured overlap before baking. This fix is in the deterministic bake script.

## Rig, materials and export contract

- Class `creature`; own43-bone hierarchy with exactly one `root`, plus `pelvis`, seven `tergite_01..07`, `tail`, `head`, two14-leg chain bones per leg and four antennal bones. Cuticle is rigidly assigned rather than bone-heat skinned; maximum four exported weights are enforced. Normal/posed legs stay fixed-length and joined.
- Source metres, +Zup, +Xnose forward, ground/feet pivot at origin; identity root basis points its tail along+Y. Applied mesh/armature transforms. The source rest bounds include decorative antennae/leg reach; measured trunk/head body boxes exclude those reaches and provide actual physical proxy footprints in actor-forward Unreal centimetres.
- Three separate single-mesh skeletal FBXs: LOD0/1/2 =24000/12000/6000triangles. No Nanite. Physics Asset creation and inactive normal-locomotion assignment belong to the Unreal import stage; source meshes do not use oversized UCX boxes.
- Four opaque PBR slots: carapace, ochre cuticle edges/legs, flexible joint membranes and dark compound eyes. UniqueUV2048² BC(sRGB), tangent normal and ORM(linear; AO=R, roughness=G, metallic=B). No SSS, masked cards, texture downloads or baked studio lighting. Unreal importer uses normal green-channel flip according to the supplied manifest.
- In-place looped actions: Idle2s/81frames40fps; Walk0.375s/16frames40fps nominal80cm/s; Run0.375s/16frames40fps nominal400cm/s. End frame duplicates start for a continuous loop. Each leg's stance target moves backward in body coordinates while the actor advances; alternating left/right seven-leg waves distribute contacts. No Feed/Attack/Hit/Death action is invented for absent generic cues.
- Temporary export copy multiplies mesh coordinates, edit-bone translations and animated location keys/handles by100; scene unit scale0.01, FBX_SCALE_ALL, header1cm. Source stays in metres. Root identity, no leaf bones, Armature wrapper, same independently proven own-rig export recipe. FBX material graphs are cleared only in the temporary export process; full editable source graphs/atlas links are preserved.

`pillbug_validation.json`, `pillbug_lod_report.json`, `pillbug_pose_validation.json` and `fbx_inspection.json` record source gates. All-frame checks cover finite matrices, stationary root, unit scales, limb-joint continuity and matching loop endpoints. The sole source convention warning is the explicitly nonexported review ground outside the asset collection. Unreal loaded LOD/material/PhysicsAsset/animation and gameplay integration still require the parent's staged engine review; source validation does not claim those checks have run.

## Provenance

All geometry, rig, actions and procedural/baked textures are original project-authored work. No paid generation, downloaded body model, image texture, reference photo or third-party geometry was incorporated. Biology references were used for observation only:

- [UC IPM: Pillbugs and sowbugs](https://ipm.ucanr.edu/home-and-landscape/pillbugs-and-sowbugs/): seven leg pairs, segmented cuticle and habitat.
- [Missouri Department of Conservation: land isopods](https://mdc.mo.gov/discover-nature/field-guide/pillbugs-sowbugs-land-isopods): oval armored body, lateral compound eyes, antennae and mouthparts.
- [Utah State University Extension: pill bugs](https://extension.usu.edu/planthealth/ipm/notes_ag/veg-pill-bug): terrestrial-isopod anatomy.

The original Dink sprite sequences131/133/141/143 supplied silhouette/color and behavior reference only; none of their pixels are present in the new atlas. The companion RE-MASTER_PLAN art direction, bestiary and Blender CONVENTIONS remain the production guides. Candidate source ledger rows are local to this folder until the parent coordinates the shared merge.
