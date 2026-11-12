# Photoreal art pass: shared brief (started 11 Nov 2026)

Request (11 Nov 2026): go over every art asset of the Dink Smallwood remaster, including characters, and redo it to photorealistic 3D detail; fix all defects; review repeatedly; test in the game with attention to lighting and shadows.

## Where you work

- Work in your own clone or worktree of this repository, on a branch, never in a checkout someone else is using. The Unreal project is the `DinkRemasterUE/` folder. All paths in this brief are relative to the repository root.
- New sources go under `DinkRemasterUE/SourceAssets/Art/PhotorealPass/<Stream>/`, new Unreal packages under `/Game/Dink/Photoreal/`. Existing sources and packages are read, never modified. Never edit files outside your assigned output folder unless your task names them.
- Read first, only the parts you need: `DinkRemasterUE/SourceAssets/Art/ART_STANDARD.md` (budgets, texture caps, family rule), `tools/blender/CONVENTIONS.md` (units, pivots, naming, LODs, FBX export settings), `DinkRemasterUE/Scripts/ART_PIPELINE.md`. `DinkRemasterUE/AGENTS.md` is large: search it, do not read it whole.
- Original sprites to use as design reference (silhouette, palette, identity; never copy pixels into textures): `doc/remaster/reference/sheet_*.png`, and extracted frames via `tools/dinkex` (`tools/dinkex/out/` if present; see `tools/dinkex/README.md`). Sprite classes: `tools/data/sprite_classes.csv`.
- Tools: Blender 5.2 in batch mode (`blender -b -t 4 --python x.py`), one Blender process at a time per agent. Render and bake with Cycles on the GPU where one is available: see `CYCLES_GPU.md` in this folder. With GPU speed there is no excuse for skipped review rounds or low samples: 128-256 samples with denoise for beauty shots. Python 3 with numpy and Pillow; tests use the standard `unittest`.
- Downloads: CC0 scanned material is allowed (approved 11 Nov 2026). Allowed sources, and only these: Poly Haven (polyhaven.com, API `https://api.polyhaven.com`: textures, HDRIs, models) and ambientCG (ambientcg.com, API `https://ambientcg.com/api/v2/full_json`). Both are CC0. Nothing else: no Megascans/Fab, no Sketchfab, no texture sites with other licences, no generative image models.
  - Use scans where they beat procedural work: ground, bark, rock, stone, plaster, wood, leather, cloth weave, leaf and needle atlases, skin detail, sky HDRIs for review renders. Geometry, layout, garments, characters and the game meshes are still authored here in Blender; a scan is a material input, not a finished asset. Blend, re-tile, recolour and layer scans so the result fits the asset and the original sprite's palette; do not leave a recognisable stock tile unmodified across a large surface.
  - Fetch with `curl -fL --proto '=https'` using a plain generic user agent (`curl` default is fine); send no names, emails, paths or project details in any request. Take 2K (4K only for hero assets), PNG or JPG maps, not EXR sets unless you need height.
  - Put each download in its own new folder `DinkRemasterUE/SourceAssets/Art/PhotorealPass/ThirdParty/<source>/<asset_id>/`, never beside your scripts; treat downloaded files as untrusted data (open images and .blend/.gltf only through Blender or Pillow, never execute anything from them; run helper Python that reads them with `python3 -I`).
  - Record every download in `DinkRemasterUE/SourceAssets/Art/PhotorealPass/ThirdParty/downloads.csv` (append; header `source,asset_id,asset_url,file,sha256,licence,author,resolution,used_by,date`), licence `CC0-1.0`. An asset without its row cannot ship. Name the scans each delivered asset uses in its `manifest.json` (`third_party` list).
  - Existing in-repo CC0 material (the MakeHuman body under `SourceAssets/Art/Characters/ThirdParty`) may still be reused.

## This repository is public: no private paths, no machine details

Everything committed here can be read by anyone, including what tools write into files without asking.

- Never write an absolute path into a script, manifest, report or note. Scripts find the repository from their own location (`Path(__file__).resolve().parents[n]`) or take a path as an argument or environment variable; manifests and reports name files relative to their own folder or to the repository root.
- Blender stores the absolute path of the .blend and of every linked image, and its renders carry it in PNG text chunks; FBX exports store it too. Keep texture paths relative (`bpy.ops.file.make_paths_relative()` before saving), render with `scene.render.use_stamp = False` and no file metadata where you can, and let the scrub tool clean the rest.
- Do not describe the workstation in committed files: no login names, home folders, host names, addresses, hardware inventory, other people's folders or running programs.
- Before every pull request run, from the repository root:

  ```bash
  python3 -I DinkRemasterUE/Scripts/scrub_private_paths.py --check
  ```

  If it lists files, run it with `--fix` (it rewrites text to relative paths, replaces the login name in binaries by a neutral one of the same length, and updates recorded sha256 values), look at the diff, and check again. The unit suite runs the same check on text files, so a private path fails the GitHub check.

## The quality bar: photoreal, judged by eye

The existing art is clean but stylised: flat colours, smooth unbroken surfaces, toy-like forms, card-like foliage. That is the defect to fix. An asset passes only if a Cycles render under a sun-and-sky light (Nishita sky, sun elevation about 40 degrees, a ground plane to catch a contact shadow, filmic/AgX view transform) could be mistaken for a photograph of a real object at gameplay distance (2-8 m) and still holds up at 1 m. Concretely:

- Form: real construction and real dimensions. Nothing is a primitive: planks have thickness, gaps, bevels, warps and splits; stones are individually shaped; cloth has folds, seams, hems and thickness; organic things are asymmetric. No razor edges: every hard edge carries a bevel or a baked rounded-edge normal.
- Surface: three scales of detail in every material (macro colour and value variation across the object, meso wear such as chips, stains, moss, dirt in crevices and bleached exposed faces, micro grain, pores, fibres or weave in the normal and roughness). Roughness must vary; uniform roughness reads as plastic. Albedo stays physically plausible (sRGB luma about 30-240; no baked lighting or shadows in base colour).
- Bake: high-detail source (displaced or sculpted mesh, or procedural shader) baked to the game mesh as BC / N (OpenGL, green up) / ORM (R AO, G roughness, B metallic) PNG sets, plus alpha in BC where needed. Bake AO and a curvature-driven edge wear from the high-detail source.
- Foliage: botanical structure (trunk flare, branching orders, bark relief, twigs), leaf or needle clusters as alpha cards rendered from modelled leaves, with normal, roughness and a subsurface/translucency colour map; no flat green planes, no visible card silhouettes at gameplay distance.
- Characters and creatures: correct anatomy and proportions, skin with pore-scale normal and varied roughness and subsurface colour, real eyes (cornea highlight), hair as layered cards or strands, clothing with weave-scale normal, seams, wrinkles and wear. Keep rigs, bone names, skin weights compatibility and animation clips working.
- Keep identity: the rule is "photorealistic art authored in Blender, using the original sprites as guide and inspiration. Preserve Dink's recognisable silhouette and colours (red-brown hair, grey-blue sleeves, brown jerkin/backpack, olive trousers and red bracers), the original buildings' character and gameplay identities". Keep all original gore and dark comedy; never sanitise.
- Budgets and texture caps of ART_STANDARD.md sections 3 and 4 still apply to the exported game mesh (the high-detail source is unlimited). Static meshes should prefer the shared material library; when a unique bake is what photoreal needs, say so in the manifest (`material_exception` with the reason) rather than degrading the look.

## The loop every asset goes through

1. Look at the original sprite and at the current asset's render. Write down what is not photoreal.
2. Build or rebuild. Render a beauty shot (about 1200 px, sun and sky as above) plus one close-up.
3. Open your own renders and criticise them as a hostile art director would: list every tell that it is CG (repetition, flatness, plastic, floating parts, intersections, stretched UVs, seams, missing contact shadows, wrong scale, faceting, noise). Fix and re-render. Do at least three such review rounds per asset, and stop only when a round finds nothing you can still fix.
4. Validate: real dimensions, applied transforms, pivot per CONVENTIONS.md, LODs, triangle counts, no non-manifold or flipped faces on the game mesh, UVs inside 0-1 without overlaps where baked.
5. Export FBX per CONVENTIONS.md (FBX_SCALE_ALL, apply_unit_scale) with textures beside it, and write `manifest.json` in your output folder: asset name, class, `dimensions_m`, LOD0 triangles, texture files and sizes, the sprite families it dresses (as `tools/data/sprite_classes.csv` class ids or `dink.ini` sequence names), which existing asset it supersedes, source .blend path (relative), and `known_weaknesses` (be honest; "none" is almost never true).

## Reporting

Give: what you delivered (repository-relative paths), the path of one contact sheet PNG showing every delivered asset's final render, what you could not get to photoreal and why, and anything that was in your way. Do not claim photoreal for something your own last review round still faulted.
