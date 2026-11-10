# Mother clothing — Blender source candidate V1

Mother is an existing 3D anatomical character, not a sprite card. This isolated successor preserves her original head, hair, hands, skin, original unique UV layout, four mesh LOD topologies, normalized skin weights and exact 89-bone rest hierarchy. The source wardrobe was too body-tight and smooth in the existing portrait. This candidate eases its front chest panel, adds millimetre-scale drape and softens angular lower fold peaks without adding triangles. Red madder-like wool and an undyed linen apron retain the original character's red/apron identity; yarn irregularity, matte dielectric roughness, fine woven relief and a double stitched centre-front panel distinguish the two textiles. Original leather footwear base colour/roughness/normal are retained by the existing dark-leather colour mask. This is an art candidate, not a declaration of final photoreal quality.

The actual S001_P26 record is screen1/index26, sequence351/frame1, script `s1-h1-m`, walk base350. `Reference/original_guide.json` binds the original `dir.ff` archive and four directional first frames (351/353/357/359). The original sprite remains reference and inspiration; no gameplay record, script, animation binding or runtime manifest changes.

## Reproduction

From this directory, with Blender5.2.2 LTS and the unchanged project `tools/blender/dinkasset` exporter:

```sh
ALSOFT_DRIVERS=null SDL_AUDIODRIVER=dummy taskset -c 2 nice -n 12 blender -b -t 1 -setaudio Null --python Tools/build_clothing.py
ALSOFT_DRIVERS=null SDL_AUDIODRIVER=dummy taskset -c 2 nice -n 12 blender -b -t 1 -setaudio Null --python Tools/render_review.py
ALSOFT_DRIVERS=null SDL_AUDIODRIVER=dummy taskset -c 2 nice -n 12 blender -b -t 1 -setaudio Null --python Tools/bake_export.py
ALSOFT_DRIVERS=null SDL_AUDIODRIVER=dummy taskset -c 2 nice -n 12 blender -b -t 1 -setaudio Null --python Tools/readback.py
```

Use an owned `XDG_CACHE_HOME` if the Blender thumbnail cache is read-only. Null audio avoids the host PipeWire shutdown stall observed in the first local authoring attempts. The packed editable master retains procedural nodes. The packed `_Baked` sibling and separate BC/tangent-normal/ORM maps are an inspectable export candidate. All textures use the existing 4096 UV authority. Only the wardrobe slot changes; the other four original material families retain their graphs and original atlas pixels. Four FBXs use the established process-only centimetre conversion, explicit identity root and no added leaf bones/animations. The original `Characters/SK_Mother.blend`, exports and production content remain unchanged.

## Acceptance boundaries

Independent fresh-process readback compares actual stored candidate data against the baseline, including every rest matrix, polygon, UV coordinate, weight, nonwardrobe vertex and original atlas pixel. Geometry easing is clothing-only; maximum displacement is about4.2cm at the chest panel, not a skeleton/body change. Front, back and fabric-detail images are actual CPU Cycles renders, not generated concept images. The original first preview iteration remains outside the delivery under `DinkQA/MotherClothingArt/Iteration1` because its wool was still too pale/smooth.

No UE import, runtime/default activation or native animation acceptance is claimed. Before activation: independently import all89 bones against the existing native reference; inspect idle/walk/talk and elbow/waist extremes for new cloth/body penetration and LOD popping; retain the original source actor/script/save identity and capsule; verify atlas normal orientation and real room/daylight renders. Four unchanged LOD triangle counts and at most four influences avoid a geometry/skinning budget increase. This source version adds a separate three-map 4K wardrobe texture set: native compression, mip residency, texture memory and draw-call cost must be measured; consolidation into the shared atlas is a follow-up before any memory-budget approval. Procedural shader complexity is for Blender authoring only and is baked for the candidate export. No physics or collision authority is introduced.

Existing anatomy/textures remain MakeHuman CC0, with original notices in `Characters/Provenance`; Epic's compatibility rig retains its separate existing terms. Textile nodes, geometry easing and renders are original project work. No external texture library or AI image service was used.

Actual source checkpoint: fresh Blender readback PASS for both packed sources; independent binary FBX readback PASS for four exports/all89 baseline bone transforms; project asset validator0errors/9warnings. All four LODs have zero new collapsed or reversed cloth triangles. LOD0 near-coincident vertices increased46→47 within the validator0.01mm threshold; this is retained explicitly for deformation/fold review before activation. The other warning categories are unchanged (budget target/open boundaries/inherited lowLOD wire edges). See `review_report.json`; no native or performance approval is implied.

Roughness and yarn relief are artist-selected PBR inputs, not instrument measurements of a reference garment. The review is based on the actual rendered candidate and original sprite identity.
