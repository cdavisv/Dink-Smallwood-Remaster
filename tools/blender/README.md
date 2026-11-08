# tools/blender: the Blender side of the Unreal asset pipeline

One scriptable path from a `.blend` to Unreal-ready files, plus an automatic checker that
rejects assets that break the conventions in [`CONVENTIONS.md`](CONVENTIONS.md).
Everything runs headless in Blender 5.2 (`/usr/bin/blender`), uses only Blender's bundled
Python and the standard library, needs no add-ons and no network.

**Unreal Engine is not installed on the dev machine.** Nothing here has been import-tested in
Unreal. See "Verified vs not verified" below.

```
tools/blender/
  CONVENTIONS.md        the rules and the reasons (read this first)
  README.md             this file
  run_tests.py          self-test: one command, drives headless Blender
  dink.py               wrapper: run one script, print only its JSON
  gen_class_table.py    renders the class table in CONVENTIONS.md from conventions.py
  dinkasset/
    conventions.py      constants and the class table (no bpy)
    common.py           shared Blender helpers
    validate.py         check a .blend against the conventions
    fix.py              opt-in, logged repairs
    make_lods.py        LOD chain + UCX_ collision generation
    export_ue.py        FBX + GLB export tree and manifest.json
    import_generated.py image-to-3D result -> compliant .blend
    fbxparse.py         stdlib binary-FBX reader used by the tests
  tests/                Blender-side helper scripts for run_tests.py
  out/                  generated, git-ignored (tests/, export/)
```

## Run the self-test

```
cd tools/blender && python3 run_tests.py        # about 25 s; add -v for test names
```

It builds test assets procedurally (a barrel prop with a tap on its front, a 2 m wall with a
door opening, a skinned tube, and a set of deliberately broken meshes), runs every script
and asserts on the results. Exit code 0 means all pass. `BLENDER=/path/to/blender` selects another binary.
Details of what is asserted are under "Verified vs not verified".

## The scripts

All scripts are invoked the same way and talk back through three channels:

* **JSON report** on stdout between the lines `@@DINK_REPORT_BEGIN@@` and `@@DINK_REPORT_END@@`
  (Blender prints its own log lines around it); `--report FILE` also writes it to a file.
* **Exit code**: `0` ok, `1` findings (validate) or rejections (export) or non-compliant import, `2` usage / file error, anything else is a crash.
* The saved `.blend` / export tree.

Two ways to call them:

```bash
# raw
blender -b --factory-startup -P tools/blender/dinkasset/validate.py -- --blend my.blend

# wrapper: stdout is only the JSON (or --summary for text), Blender noise suppressed, same exit code
python3 tools/blender/dink.py validate --blend my.blend
python3 tools/blender/dink.py --summary validate --blend my.blend
```

Common flags: `--blend FILE` (or start Blender with the file), `--collection NAME` (repeatable, restrict to
asset collections), `--report FILE`. Scripts that change data take `--output FILE` or `--inplace`.

### validate.py

```
dink.py validate --blend X.blend [--collection SM_Barrel_01] [--class prop] [--strict] [--report r.json]
```

Per asset: naming, class, unapplied/negative transforms, parenting, shared pivot across LODs, size range with a unit hint,
grid snapping (kits), pivot rule, triangle budget, loose/duplicate/zero-area geometry, non-manifold edges, inverted or inconsistent
normals, UV presence/count/overlap/range/texel density, material slots and names, texture names/sizes, collision presence and
convexity, LOD presence/monotonic/bounds, skeleton bones and skin weights. `--strict` makes warnings fail too.
`--class` supplies a class for collections lacking `dink_class`.

Report shape (abridged):

```json
{"tool":"validate","passed":false,"summary":{"assets":3,"assets_passed":1,"errors":4,"warnings":0},
 "scene_findings":[{"code":"SCENE_UNITS","severity":"error","message":"..."}],
 "assets":[{"name":"SM_Barrel_01","class":"prop","passed":false,"tris_per_lod":{"LOD0":344},
            "bounds":{"size_cm":[62,77,90],"unreal_min_cm":[...],"unreal_max_cm":[...]},
            "errors":1,"warnings":0,
            "findings":[{"code":"COLLISION_MISSING","severity":"error","asset":"SM_Barrel_01","message":"...","object":"...","data":{}}]}]}
```

Finding codes (severity can be lower than shown where noted; messages say how to fix):

| Area | Codes |
|---|---|
| scene / structure | `SCENE_UNITS` `NO_ASSETS` `ORPHAN_OBJECTS`(w) `ASSET_CLASS_MISSING` `ASSET_CLASS_UNKNOWN` `NO_MESH` `MULTI_MESH` `UNEXPECTED_OBJECT`(w) `STATIC_HAS_ARMATURE` `SOCKET_MISSING` |
| naming | `NAME_ASSET` `NAME_PREFIX` `NAME_OBJECT` `NAME_COLLISION` `NAME_MATERIAL` `NAME_TEXTURE`(w) `NAME_MESHDATA`(i) |
| transform, scale, pivot | `TRANSFORM_UNAPPLIED` `NEGATIVE_SCALE` `PARENTED` `ORIGIN_MISMATCH` `SCALE_RANGE` `SNAP` `PIVOT` `MODIFIERS`(w) |
| budget | `TRIS_OVER_BUDGET` `TRIS_OVER_TARGET`(w) |
| geometry | `LOOSE_GEOMETRY`(w) `DUPLICATE_VERTS`(w) `ZERO_AREA` `NON_MANIFOLD`(e or w by class) `NORMALS_INVERTED` `NORMALS_INCONSISTENT` |
| UV / materials / textures | `UV_MISSING` `UV_COUNT`(w) `UV_OVERLAP` `UV_RANGE`(w) `UV_DEGENERATE`(w) `TEXEL_DENSITY`(w) `SLOTS_OVER` `SLOT_UNUSED`(w) `MATERIAL_EMPTY_SLOT` `NO_MATERIAL`(w) `LOD_MATERIAL_MISMATCH`(w) `TEXTURE_SIZE` `TEXTURE_MISSING`(w) |
| collision | `COLLISION_MISSING` `COLLISION_NOT_CONVEX` `COLLISION_NOT_CLOSED` `COLLISION_DEGENERATE` `COLLISION_TOO_COMPLEX` `COLLISION_BOUNDS`(w) |
| LOD | `LOD_MISSING` `LOD_GAP` `LOD_NOT_DECREASING` `LOD_BOUNDS`(w) `LOD_UNEXPECTED`(i) |
| skeleton | `SKELETON_COUNT` `SKELETON_BONES` `SKELETON_ROOT` `SKELETON_BONE_NAME` `SKELETON_BONE_COUNT`(w) `SKIN_NO_ARMATURE_MODIFIER` `SKIN_UNWEIGHTED` `SKIN_INFLUENCES` `SKIN_ORPHAN_GROUPS`(w) |

(w) warning, (i) info, otherwise error. The UV overlap test is pure Python and is skipped above 120,000 triangles (reported as info).

### fix.py

Nothing runs unless asked for. Every fix is a flag and every action is logged in the report.

```
dink.py fix --blend in.blend --output out.blend [--collection NAME] [flags]
```

| Flag | Does |
|---|---|
| `--all-safe` | apply-transforms, merge-distance, remove-loose, remove-degenerate, recalc-normals, prune-slots, set-pivot |
| `--fix-units` | scene to Metric 1.0, geometry multiplied so real sizes are kept |
| `--apply-transforms` | unparent, bake rotation+scale (also negative scale, shared mesh data, shape keys) into the mesh |
| `--scale F` / `--height M` / `--longest M` | uniform scale to a factor / to a real-world height / longest side |
| `--merge-distance [M]` | merge vertices closer than M metres (default 0.01 mm), drop duplicate faces |
| `--remove-loose`, `--remove-degenerate` | loose vertices and wire edges; zero-area faces |
| `--recalc-normals` | consistent outward winding |
| `--prune-slots` | drop unused material slots, merge `.001` duplicates and duplicate slots |
| `--add-uvs` | automatic smart-project UVs where missing (low quality: hero assets need a hand unwrap) |
| `--set-pivot` | move the origin to the class rule position (skeletal: reported, not done) |
| `--rename [--name N]` | collection, objects, mesh data, collision, materials (and role-detectable images) to the convention |
| `--set-class C [--path P]` | write `dink_class` / `dink_path` on the selected collections |
| `--validate` | run the validator afterwards and embed its report (exit code 1 if it fails) |

Not offered on purpose: triangulation (the source keeps quads; export triangulates) and anything that changes the look
(subdivision, retopology, hole filling: `NON_MANIFOLD` stays reported).
Rigs: transforms and pivot of armatures are reported, not changed.

### make_lods.py

```
dink.py make_lods --blend in.blend --output out.blend [--lods] [--collision [auto|hull|grid|box]]
         [--ratios 0.5,0.25,0.1] [--cell 0.25] [--max-verts 32] [--force] [--replace] [--collection NAME]
```

* `--lods`: LOD1.. = Decimate-collapse of LOD0 at the class ratios (standard 0.5/0.25/0.10, skeletal 0.5/0.25/0.12), never under 24 triangles;
  LOD0 is renamed `<Asset>_LOD0`. Classes that use Nanite get nothing unless `--force`.
* `--collision`: `UCX_<LOD0 name>_NN` convex hulls (`hull` single hull, `grid` clip-and-merge for modular kit pieces, `box`).
  Skeletal classes are skipped (Physics Asset). Existing LODs/collision are kept unless `--replace`.

### export_ue.py

```
dink.py export_ue --blend in.blend [--out tools/blender/out/export] [--formats fbx,gltf] [--collection NAME]
         [--force] [--fbx-scale-mode all|local|units] [--source-root DIR] [--armature-export-name Armature] [--no-textures]
```

Validates every asset first and **rejects failing ones** (listed under `rejected`, exit 1) unless `--force`.
Per asset it writes, mirroring the Unreal content path:

```
<out>/Game/Dink/<ClassFolder>[/<dink_path>]/<Asset>.fbx       FBX: LODs, UCX_ collision, sockets, armature
<out>/Game/Dink/<ClassFolder>[/<dink_path>]/<Asset>.glb       glTF binary: LOD0 + skin, no collision
<out>/Game/Dink/<ClassFolder>[/<dink_path>]/Textures/T_*.png  images used by the materials
<out>/manifest.json                                           merged across runs, keyed by asset name
```

`manifest.json` per asset: `name`, `class`, `kind`, `content_path`, `files`, `source{blend, sha256, collection}`,
`tris` (per LOD), `lod_count`, `bounds_cm` (size and min/max in Blender axes **and** in expected Unreal axes, centimetres, relative to the pivot),
`pivot_rule`, `nanite`, `translucent`, `collision` (names), `material_slots`, `textures` (role, sRGB, normal green flip), `skeleton`,
`sockets`, `validation`, and `import_hints` (the settings the future Unreal import script should use). The file is documentation-derived
for Unreal; see CONVENTIONS.md section 2 for the exporter settings and why.

### import_generated.py

```
dink.py import_generated --input barrel.glb --name SM_Barrel_02 --class prop --height 0.9 \
        --out sources/Props/Tavern/SM_Barrel_02.blend --path Tavern --source "TRELLIS.2, seed 12, MIT"
        [--longest M] [--rotate X Y Z] [--no-uv] [--no-decimate] [--no-collision] [--no-lods]
```

OBJ (Y-up, -Z forward), GLB/glTF, FBX, PLY, STL. Joins all meshes, bakes every transform, optional `--rotate` degrees,
scales so the Z extent equals `--height` (or the longest side equals `--longest`), merges/cleans/recalcs normals, sets the pivot
at the world origin, creates the collection with its properties, unwraps if there are no UVs, renames materials and role-detectable
images, collapses an over-budget mesh to the class target, builds collision and LODs the class needs, saves, validates. Exit 0 only if the
saved file passes. Static classes only (rigging is manual). A generated mesh still needs a human to judge topology, UVs and textures.

## An agent doing one asset, end to end

1. **Bring it in.** Generated mesh: `import_generated.py --input ... --name SM_<Name> --class <class> --height <metres> --out <sources path>.blend --source "<tool, model, licence>"`.
   Hand-made: put the object in a collection named `SM_<Name>`, set `dink_class`
   (`fix.py --collection X --set-class prop --path Tavern --inplace`).
2. **Look at the verdict.** `dink.py --summary validate --blend FILE`. If the model went in with unapplied transforms, wrong pivot, `.001` names:
   `dink.py fix --blend FILE --inplace --all-safe --rename`. Unit confusion: `--fix-units` (scene) or `--height`.
3. **Generate what is missing.** `dink.py make_lods --blend FILE --inplace --collision` (and `--lods` for foliage, translucent or skeletal classes).
4. **Gate.** `dink.py validate --blend FILE` must exit 0. Remaining errors are things a script should not guess: budget overruns on hand-made meshes,
   open holes (`NON_MANIFOLD`), overlapping UVs, material-slot count, missing hulls on concave props. Fix them in Blender, never by loosening the validator.
5. **Export.** `dink.py export_ue --blend FILE --out out/export --source-root <sources root>`; hand `out/export/` and `manifest.json` to the Unreal import step.
6. **Record.** Add the ledger row for generated assets (tool, model, licence, redistribution proof).

Rules of thumb for agents: never edit exported files; always re-validate after any script that changes a `.blend`; treat `warning` as "look", `error` as "stop";
use `--collection` when a `.blend` holds several assets; scripts never touch other files than the ones named by `--output`/`--inplace`/`--out`.

## Verified vs not verified

**Verified on this machine (Blender 5.2.2 LTS, `python3 run_tests.py` passes):**

* validate rejects the broken fixtures for the intended codes (names, unapplied rotation/scale, negative scale, wrong pivot, wrong scale with unit hint,
  grid snap, triangle budget, material slots, missing UVs, overlapping UVs, non-manifold, zero-area, loose/duplicate vertices, inverted normals, missing collision, missing LODs, scene units,
  skeleton rules) and passes the good assets with no warnings; exit codes 0/1/2.
* fix repairs exactly what it claims (and nothing without flags), re-validation confirms; fix refuses to "repair" holes.
* make_lods gives the documented ratios (within 4 %), skinned LODs keep weights, convex hulls within the vertex cap, and the grid collision keeps the wall's door opening open
  while covering both columns and the lintel.
* export writes the file tree and manifest (hash, per-LOD triangles, bounds), rejects failing assets, merges manifests across runs.
* The exported **FBX bytes**, read with a stdlib parser independent of Blender's importer: `UnitScaleFactor = 100`, Z-up/front -Y header, every mesh node scale 1 and rotation 0 and translation 0
  (asset exported at the origin even though it sat elsewhere in the scene), triangulated, vertex extents x unit = manifest size, front marker still on -Y, collision and LOD nodes present, bones present.
* The exported **GLB**: accessor bounds in metres, Y-up, Blender front -Y = glTF +Z, LOD0 only.
* **Round trip**: re-importing FBX and GLB into Blender gives 62 x 77 x 90 cm for the barrel (same as the manifest, within 0.5 cm), the 200 x 20 x 350 cm wall with its pivot and three `UCX_` hulls,
  and the skinned tube at 24 x 24 x 120 cm with bone heads at 0/20/60/100 cm.
* import_generated turns an OBJ, a GLB and an FBX authored at three different scales/pivots into the same compliant 90 cm barrel, handles `--rotate`, and decimates a 59k-triangle result to the class target.
* The class table in CONVENTIONS.md equals `conventions.py`.

**Not verified (needs Unreal Engine 5.8):** that Unreal imports these FBX/GLB files at the stated size and orientation, `_LODn` and `UCX_` handling (Interchange vs legacy), sockets,
the armature Null node, shared-skeleton retargeting, Nanite/Lumen/Deck behaviour behind the budgets and class defaults, texture compression and green-channel flip, the mannequin bone list.
CONVENTIONS.md section 14 lists each one; the manifest `import_hints` are expectations, not results.

**Known gaps:** no animation export; no texture baking/ORM packing script; the UV-overlap test is pure Python (about 1 s for a clean 100k-triangle unwrap, slower when islands overlap heavily, skipped above 120k triangles);
vertex colours not exported; skeletal pivot/transform fixes are manual; `import_generated.py` does not rig; the `dink_master` material property is documented but not validated;
Blender "Collections" that are children of an asset are treated as part of it.

## Troubleshooting

* `MeshOptimizer is not available ... libbf_intern_meshopt_bridge.so` in the log: harmless, from the glTF exporter (meshopt compression is not used).
* `.blend1` files appear next to saved files: Blender backups, git-ignored.
* Blender prints a lot; use `dink.py` or take the text between the report markers.
* A validation failure after a fix usually means the asset has no class or a wrong one; check `dink_class` in Object Properties of the collection (Custom Properties).
