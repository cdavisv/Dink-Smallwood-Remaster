# Optional UV2 seam transport candidate

Source-only review draft, no native or appearance acceptance. All original UV0/UV1 and geometry preserved; UV2 is an integer tag consumed by mesh vertex equality, never by material graphs. Original N/T .05degree/sign/zero limits remain unchanged. DESIGN_V2 documents one-ULP tangent reevaluation; no bitidentity claim. Original arrays in the extended NPZ are byte-exact.

Evidence/RawScripts preserves exact executed scripts. Scripts/portable_recipe.py changes only explicit path bindings in memory, checks pinned inputs and refuses protected or nonempty export destinations. Export via Blender --background --threads 2 --python Scripts/export_uv2_guard.py -- --project-root PROJECT --reference ORIGINAL20eNPZ --output DISPOSABLE. Verification via python Scripts/verify_serialized_guard.py with the same arguments requires the exact retained candidate in DISPOSABLE/FBX. Do not repeat exports to seek bitidentity. Portable export has not been rerun; original actual export is the retained candidate.

Native source pipeline draft and controls are outside this bundle in ../../PipelineDraft. No save/activation or Engine changes authorized by this document.
