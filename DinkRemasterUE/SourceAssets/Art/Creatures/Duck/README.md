# Stonebrook duck (Quackers) and its faithful head-off death: candidate source art

This folder holds an original, project-authored white domestic duck (Pekin type) for the original game's brain-3 ducks and for Ethel's duck Quackers (`s1-oldd`: `S409_P07`, `S440_P02`, `S441_P11`). It also contains the original game's darkly comic duck death: the head comes off, the headless body keeps strutting, and the second hit removes it.

The palette follows the original sprites: sequences 21–29 (duck walk), 111–119 (bloody headless walk), 121–129 (severed head) and 187–189 (blood). Everything is produced by the deterministic Python in `Tools/` (seed 1997). No downloaded models, image textures, generative image models or sprite pixels were used.

Status: **candidate**. Nothing has been imported into Unreal, and no shared file outside this folder was changed.

## Revision 2 (realism pass and gore set)

`Previews/preview_duck_compare_v1_v2.png` shows the v1 and v2 beauty renders side by side. The v1 renders are kept in `Working/v1_previews/` (git-ignored).

**1. Plumage no longer reads as felt.**
- **Feather cards:** about 900 alpha-tested contour-feather cards plus 28 "pocket" cards over the lower wing edges. The cards follow the head→tail feather flow, rise slightly off the skin at the base and lie back toward the tip. They shade with the custom normal of the skin they grow from, which breaks up the silhouette into a soft, layered outline.
- **Normal detail and wear:** stronger feather-tract (pterylae) depth, per-feather sheen and roughness variation, and a soiled, muddy belly and vent.
- **Through the LOD chain and FBX:** the cards are kept out of the decimator and re-added as deterministic subsets: 100 % on LOD0, 50 % on LOD1 and 22 % on LOD2.
- **Materials:** still 4. `MI_Duck_Feather` is now masked (opacity = BC alpha) and two-sided.

**2. Folded wing built from real feathers.** Each wing has 24 lofted feathers conformed to the flank and layered:
- 5 primaries, with the tips stacked over the tail;
- 6 secondaries;
- 3 broad tertials along the back;
- 10 greater and lesser coverts, sunk into the shoulder and breast feathers.

Each feather has its own shaft, barbs, edge and wear texture, and the flank pocket cards lap over the lower edge, so there is no slab or panel edge.

**3. Pekin legs and posture.**
- **Posture:** the upper body is pitched 9° nose-up about the hip and lowered 2.7 cm, and the head is counter-tilted so the bill stays level.
- **Legs:** the tarsus is shorter and 20–30 % thicker (knee 9.2 cm, ankle 4.9 cm above the ground), and the feathered thighs now cover the knee.
- **Size:** 50.5 cm long, 46.6 cm tall and 21.7 cm wide.
- **Clips:** every clip was regenerated on the new proportions and rechecked.

**4. Original gore (owner decision).** Checked against `source/dink/dink.cpp` `duck_brain` (D:12723) and `one_time_brain` (D:15741), plus `dink.ini`:
- **First hit:** a head sprite spawns (brain 5, one-shot, seq 121–129: 4 × 125 ms, sliding at speed 1–3). It then freezes into the background as a head in a pool of blood. The body switches to the bloody headless walk (seq 111–119: 4 × 75 ms loop = 0.3 s, speed 1) and keeps wandering, dropping a random blood splat (seq 187–189) with 1 % chance per think.
- **Second hit:** seq 164 flash, then `duckdie`, and the body is gone.

To match that, this folder ships:
- `SK_Duck_Headless`: the same 23-bone skeleton and bind pose, with a neck stump, a raw wound cap (muscle, cartilage-ringed trachea, oesophagus, cervical vertebra with spinal cord, clots) and alpha-tested blood runs down the white neck feathers.
- `SM_Duck_Head`: a severed-head prop with a matching wound cap and blood. It has 3 LODs and a single 27-vertex convex `UCX_` hull for physics.
- **Clips:** `HeadlessRun` (0.3 s loop, the original's bloody-walk cadence: lurching, flapping, stump jerking, nominal 69.8 cm/s) and `HeadlessDeath` (1.6 s: a last lurch, topples, two kicks, still; hold the last frame).
- **Blood decal sources:** `T_Duck_BloodPool_*` and `T_Duck_BloodSpatter_*` (512 px; BC with alpha, N, ORM).
- The non-gory `Hit` and `Death` clips remain on the intact duck.
- `duck_gore_manifest.json` documents the original sequence and a step-by-step remaster wiring for the integrator.

## Revision 3 (focused plumage and wing smoothing)

The coordinator judged v2's cards to read as paper shingles at game distance. v3 makes these changes:
- **Body cards:** they lie almost flush (0.5–2.5° tilt, about 1–3 mm of lift), are 35–40 % larger, and have soft, ragged alpha edges with no hard rounded tip. Their albedo is matched to the skin underneath, with no crevice darkening, so card edges do not draw lines.
- **Card placement:** there are now about 380 body cards (down from 900). The breast, flank and belly are thinned by about 68 %; cards stay mainly on the back line, rump and tail coverts, plus 28 pocket cards over the lower wing edge.
- **Wing:** layer steps reduced by 30 %, feathers 20–60 % thinner (the coverts thinnest), coverts broader and more overlapping, and vane edges bevelled in the normal map.
- **Unchanged from v2:** legs, posture, gore assets and all clips.

`Previews/preview_duck_compare_v1_v2_v3.png` compares the three versions:
- **Top row:** a third-person game camera (4 m away, 1.7 m high, 35 mm lens), ×3 crop.
  - v2 and v3 are real renders from the same camera; v2 comes from the snapshot in `Working/v2`.
  - v1's source had already been overwritten, so its panel is its beauty render scaled to the same pixels per metre. This is an approximation, and the camera height differs.
- **Bottom row:** the close-up beauty renders.
- `Previews/preview_duck_game_distance.png` is the full v3 game-camera frame.

## Files

| Path | What |
|---|---|
| `SK_Duck.blend` | Editable metre source. Collections: `SK_Duck` and `SK_Duck_Headless` (both class `creature`, sharing one `Armature`) and `SM_Duck_Head` (`prop_small`, LOD0–2 plus `UCX_SM_Duck_Head_LOD0_01`). Contains 9 actions, the full PBR graphs and relative texture links. |
| `Export/SK_Duck_LOD0..2.fbx`, `Export/SK_Duck_Headless_LOD0..2.fbx` | One skinned mesh per file |
| `Export/SM_Duck_Head_LOD0..2.fbx` | Static head prop; the LOD0 file carries the UCX hull |
| `Export/A_Duck_{Idle,Walk,Run,Peck,Quack,Hit,Death,HeadlessRun,HeadlessDeath}.fbx` | Armature-only clips, one baked action each |
| `Textures/T_Duck_Atlas_{BC,N,ORM}.png` | Shared 2048 px unique-UV atlas. BC is sRGB with an alpha opacity mask. N is OpenGL tangent space (flip green in Unreal). ORM is linear (R = AO, G = roughness, B = metallic). |
| `Textures/T_Duck_Blood{Pool,Spatter}_{BC,N,ORM}.png` | Blood decal sources |
| `duck_manifest.json` | Importer-compatible `dink-creature-art/1` manifest. It lists SK_Duck and all 9 clips (headless clips tagged `mesh_variant`), and no origins. |
| `duck_gore_manifest.json` | Draft: headless variant (import against the SK_Duck skeleton), head prop with physics and spawn notes, decals, the original behaviour and remaster wiring |
| `duck_validation.json`, `duck_validation_cli.txt` | `dinkasset` validator output for all 3 assets (in-process, and from the `tools/blender/dink.py` CLI) |
| `duck_lod_report.json`, `duck_pose_validation.json`, `duck_rig_report.json`, `duck_texture_report.json`, `fbx_inspection.json`, `duck_origins.json` | Evidence: per-LOD numbers, per-frame pose checks, rig and solve values, texture statistics, byte-level FBX audit, 184 original duck placements |
| `ledger_rows_proposed.csv` | 37 proposed rows in the exact `asset_ledger.csv` columns, with the current sha256. The shared ledger is untouched. |
| `Previews/` | Images listed under Previews below |
| `Tools/` | `build_all.sh` and the stage scripts (below) |

Previews:
- `preview_duck_beauty.png`, `preview_duck_head_closeup.png`, `preview_duck_turnaround.png`;
- `preview_duck_clips.png` (all 9 clips);
- gore shots: `preview_duck_headless_gore.png`, `preview_duck_stump_closeup.png`, `preview_duck_head_prop.png`;
- `preview_duck_compare_v1_v2.png`.

## Rebuild

```bash
SourceAssets/Art/Creatures/Duck/Tools/build_all.sh   # blender -b --factory-startup -t 3; ~15 min with renders (DUCK_SKIP_RENDERS=1 to skip)
```

Stages:
1. `build_duck.py`
   - Anatomy comes from `duck_geometry.py`: a metaball body bisected on the decapitation plane, the feather-built wings, cards, caps, blood films, tail, bill, eyes and legs, plus the posture transform.
   - It then produces unique UVs (cards and films at reduced density), the 23-bone rig and procedural weights (cards, caps and films copy the nearest skin weights).
   - Finally, `duck_actions.py` builds the 9 clips with analytic leg IK and ground solves measured on the skinned mesh.
2. `texture_duck.py` rasterises UV space in numpy and synthesises the BC (with alpha), N and ORM maps from design-space positions. It also writes the blood decals.
3. `export_duck.py`
   - Splits out the three assets and builds the LODs (card subsets for the skeletal meshes; a convex hull for the head).
   - Runs the all-frame pose contract and the validator, then writes the manifests.
   - Exports FBX from a centimetre copy that is never saved (×100, unit scale 0.01, `FBX_SCALE_ALL`, `apply_unit_scale=True`).
4. `inspect_exports.py` (FBX audit), `render_duck.py` and `make_sheets.py` (previews), `duck_origins.py`, and `prepare_duck_ledger.py`.

## Numbers (this build)

**Validator: 3 of 3 assets pass, 0 errors.**

| Asset | LOD0 / LOD1 / LOD2 triangles | Warnings |
|---|---|---|
| SK_Duck | 20,898 / 10,444 / 5,176 | 4: `NON_MANIFOLD` on each LOD (the open feather cards, intended); `TEXEL_DENSITY` against a 512 px/m target |
| SK_Duck_Headless | 20,800 / 10,396 / 5,152 | 4: the same kinds as SK_Duck |
| SM_Duck_Head | 4,604 / 2,302 / 1,150 | 1: `TRIS_OVER_TARGET` (target 1,500, hard limit 5,000) |

- **Rig and weights:** 23 bones with a single identity `root`. Maximum influences are 4 on every skeletal LOD, with no unweighted vertices.
- **Materials:** 4 slots on SK_Duck; Feather and Feet only on the headless variant; Feather and Bill on the head prop.
- **Dimensions:**
  - Intact duck: 0.505 × 0.217 × 0.466 m.
  - Headless body: 0.407 × 0.217 × 0.337 m.
  - Head prop: 0.18 × 0.07 × 0.14 m.
  - LOD bounds stay within 2 mm of LOD0.
- **Clips (30 fps, root motion 0):**

| Clip | Duration | Loop | Nominal speed |
|---|---:|---|---:|
| Idle | 2.0 s | yes | |
| Walk | 0.4 s | yes | 32.3 cm/s |
| Run | 0.267 s | yes | 82.1 cm/s |
| Peck | 1.2 s | no | |
| Quack | 0.6 s | no | |
| Hit | 0.4 s | no | |
| Death | 1.5 s | no | |
| HeadlessRun | 0.3 s | yes | 69.8 cm/s |
| HeadlessDeath | 1.6 s | no | |

- **Per-frame checks (every frame of every clip):**
  - Joint gap: at most 5e-8 m.
  - Root motion: 0.
  - Loop seams: 0.
  - Lowest skinned vertex: at least −2.6 mm (HeadlessRun); Run −2.4 mm and Peck −2.3 mm; all other clips within 0.0 mm.
  - Planted-foot slip: Walk 0.04 mm, Hit 0.89 mm, all others 0.
- **FBX audit (18 files):** header is 1 cm, root is identity, node scales are 1, the 23 bone names are exact, each skeletal LOD file holds one mesh, clip files hold the armature only, and the static head prop carries its UCX hull.
- **Atlas:** 51.8 % coverage, median 1780 px/m. Normal slope is 0.8° at p50 and 7.6° at p99.

## Honest remaining gaps

- **Plumage (v3):** smooth and soft at game distance, with gentle relief and a lightly broken back and rump outline. Close up, the body is still a smooth shell with texture relief rather than true down; a strand or groom system would be the next step. Whether Unreal's masked anti-aliasing and TAA blur the card edges as Cycles does is unverified.
- **Wing:** it is softer in v3, but close up the stacked secondaries still show as a few distinct bands, and there is a small dark notch at the shoulder. Flapping (Run, Hit, the headless clips) still rotates the folded stack outward; it is not an anatomical spread.
- **Gore:** it is deliberately cartoon-bright and wet to match the original's tone. The blood runs read a little like paint, and the wound cap is a clean planar cut with no torn skin or feather tufts. There are no Niagara blood-spurt particles; the decal sources stand in for the original's random blood sprites.
- **Fidelity to the original:** the faithful second hit in the original is an instant removal with a flash. `HeadlessDeath` is an optional, more physical alternative.
- **Head prop:** its 4,604 triangles are over the `prop_small` target. Use LOD1 (2,302) as the gameplay mesh if needed.
- **Death:** the neck-slump solve hits its limit (2.5), so the intact Death's final head pose is plausible but not polished.
- **Not verified:** Unreal import (including the headless mesh against the SK_Duck skeleton), masked two-sided material cost, Physics Asset, head physics, decals and in-engine lighting. Byte-identical rebuild determinism was not re-checked; the ledger hashes are from this build.
- **Process:** earlier stage-1 runs in this pass, before I re-read the rules, used more than 3 Blender threads. `build_all.sh` is now pinned to `-t 3`, and the final full rebuild ran with it.
