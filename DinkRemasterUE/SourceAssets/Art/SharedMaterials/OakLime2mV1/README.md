# Reusable oak and lime plaster, 2m

Three registered generic material roles, each1024px per2m: `MI_Shared_OakLonggrain2m`, `MI_Shared_OakEndgrain2m`, `MI_Shared_LimePlaster2m`. The authoritative records are in `../manifest.json`. These are material sources, not a private per-roof atlas. Six unrelated2m/4m coupons reuse the same three material datablocks. Longgrain is shared between frames and boards; there is no roof-only tint or mesh-specific AO.

Editable source shaders: `Shared2m_ProceduralSources.blend`; packed baked library: `Shared2m_LibraryCandidate.blend`; unrelated metric reuse: `GenericReuse_2m4m.blend`. `Textures/` holds9 BC/N_GL/ORM PNGs. BC is sRGB; N_GL/ORM linear. N_GL is OpenGL+Y, native green-flip true. ORM R255 material occlusion/Groughness/B0 dielectric. Source IOR and IORLevel plus derived F0/native-specular proposals are explicit in the registry; saved native interpretation is not yet verified.

Three derived masked camera materials are also registered, sharing these same9 maps with their opaque surface roles. They follow the existing `DinkCameraOpacity`1,shadow1,dither clip.5 convention. They do not introduce private textures or claim a UMaterialInstance parent that does not exist. No native packages, Data aliases or runtime activation are changed by this source admission.

Root accepted the source appearance from the frozen QA candidate. Material/image names were normalized to registered names; fresh reopening and `REGISTRATION_EQUIVALENCE.json` in the roof source prove unchanged mesh/shader/pixel content. `Review/reuse_2m4m.png` is the accepted pre-name-normalization render, not falsely labelled a fresh render of a renamed file. Generated oak albedo is an existing reference, not a measured scan. See PROVENANCE.md.
