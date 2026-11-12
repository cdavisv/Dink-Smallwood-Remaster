# Stonebrook SCR_440: two-storey house, farm tools and yard dressing (source candidate)

Original Blender source art for screen 440 in Stonebrook, east of Dink's cottage (SCR_439). The project
notes said this screen "needs a taller house, tools and Quackers". This folder holds the house and the
tools. Quackers (S440_P02, `s1-oldd`, vision 2) is built by a separate agent; this layout leaves the duck live and does not change it.

Status: **local candidate, not imported**. Unreal was deliberately not launched. Nothing in `Content/`,
`Content/Dink/Data`, `Scripts/`, the shared ledger or any other source directory was modified.

## What the original screen shows

The composite of tiles and placements from `tools/dinkex/out/screens/SCR_440.json` shows the following:

| Original | Placement | Treatment here |
|---|---|---|
| two-storey thatched cottage `home-04` (seq 63/4, split into P03 background + P11 live) | S440_P03, S440_P11 | `SM_House_Stonebrook_TwoStorey_01` |
| door art + warp door (`warp_map` 3) | S440_P04, S440_P06 | modelled recessed double door; `warp_overrides` row for P06 |
| two small lattice windows (`cabin-03`) | S440_P08, S440_P09 | leaded-glass windows on the east face, lower and upper (plus others) |
| leaning pitchfork, leaning long hook/scythe | S440_P21, S440_P22 (live, hard) | replacements, leaning on the east wall |
| axe, tongs, hatchet on the ground | S440_P23/P24/P25 | replacements at the original pixels |
| two `bar-sh` barrels | S440_P14, S440_P15 | existing `SM_Barrel_Oak_01`, original pixels, scripts retained |
| rail fence ×5, oak, weeds, tall grass | P01/P16/P18-20, P12, weeds | existing StonebrookExterior fence/oak/grass, reused by path |
| two tile-painted low rocks (Low hardness) | tiles | existing fieldstone boulder, scaled |

The house sprite has two stacked fieldstone storeys. A thick, rounded thatch pent roof skirts the lower
storey, and the upper storey is set back under a domed hipped thatch roof. Dark joist ends sit under both
eaves, with a planked double door and small dark windows. The 3D version keeps all of these at real scale:

- Lower storey 11.0 × 8.5 m, coursed fieldstone rubble, quoined corners and a 0.62 m wall thickness.
- Pent roof eave at 3.15 m with a rolled lip about 0.5 m thick. The upper storey is 8.8 × 6.3 m, set
  0.3 m north. The hipped roof's eave is at 6.9 m and the block-cut ridge with hazel liggers is at about
  10.5 m. A stone chimney at the back reaches 11.5 m.
- A recessed (46 cm) ledged oak double door with strap hinges, a threshold and a step stone. The lower
  and upper windows are leaded diamond-quarry casements with oak frames, stone sills, oak lintels and
  limewashed reveals.
- Like the SCR_439 cottage, the house is axis-aligned with the door to the south (Blender -Y, Unreal +Y).
  The door face centre sits on the original warp trigger (`layout_checks_440.json`).

Material language matches the SCR_439 cottage: fieldstone, limewash, oak, thatch and iron. The limewash and
wrought-iron sets are the existing `MI_Stonebrook_Limewash` / `MI_Stonebrook_WroughtIron`, reused by
relative path. The existing fieldstone, oak and thatch textures are 1024 px value-noise maps without
recognisable stones or straw, so this kit authors higher-fidelity sets with similar mean colours instead:

- rubble (2.4 m tile, angular coursed stones with pinning stones, lime joints and crustose lichen)
- combed thatch (2.0 m tile, course butt bands aligned with the geometry steps)
- weathered exterior oak
- leaded glass

The rubble and thatch height maps (`*_H.png`, 16-bit) also displace the wall and roof geometry, so the
silhouette relief matches the texture.

## Props

All props are closed solids at real size with a base-centre pivot. Each has its own unique 1024 px BC/N/ORM
set; the woodpile set is 2048 px. These sets are Cycles bakes of procedural node materials driven by
per-part mesh attributes. Each wooden part stores its own grain frame, so ring and fibre direction follow
the part, and log ends show rings, radial checks and a bark ring. Hand-polish masks make the handle grips
darker and glossier. Edge masks mark sharpened metal. Rust follows cavities, and convex edges wear bright.
The procedural `SRC_S440_*` materials stay in the .blend with fake users for re-baking.

| Asset | Class | Size m (x × y × z) | LOD0 / LOD1 / LOD2 tris | UCX | Origin |
|---|---|---|---|---|---|
| `SM_House_Stonebrook_TwoStorey_01` | building | 13.27 × 10.78 × 11.61 | 143396 / 71697 / 35847 | 5 | house |
| `SM_Pitchfork_Ash_01` | prop | 0.19 × 0.08 × 1.66 | 1316 / 658 / 328 | 2 | S440_P21 |
| `SM_Scythe_Ash_01` | prop | 0.81 × 0.24 × 1.56 | 2776 / 1388 / 694 | 2 | S440_P22 |
| `SM_Hoe_Ash_01` | prop | 0.17 × 0.18 × 1.43 | 1316 / 658 / 328 | 2 | new dressing |
| `SM_Shovel_Ash_01` | prop | 0.28 × 0.06 × 1.08 | 2036 / 1018 / 508 | 2 | new dressing |
| `SM_Axe_Felling_01` | prop | 0.87 × 0.24 × 0.04 | 1248 / 624 / 312 | 2 | S440_P23 |
| `SM_Hatchet_01` | prop_small | 0.41 × 0.17 × 0.04 | 1248 / 624 / 312 | 1 | S440_P25 |
| `SM_Tongs_Iron_01` | prop_small | 0.45 × 0.07 × 0.02 | 488 / 244 / 122 | 1 | S440_P24 |
| `SM_ChoppingBlock_Axe_01` | prop | 0.92 × 0.58 × 0.85 | 1364 / 682 / 340 | 1 | new dressing |
| `SM_Wheelbarrow_Oak_01` | prop | 0.65 × 1.69 × 0.77 | 4172 / 2086 / 1042 | 3 | new dressing |
| `SM_HayBale_01` | prop | 1.12 × 0.69 × 0.46 | 12912 / 7996 / 3998 | 1 | new dressing |
| `SM_WaterTrough_Oak_01` | prop | 1.50 × 0.66 × 0.50 | 2752 / 1376 / 688 | 1 | new dressing |
| `SM_Woodpile_Split_01` | prop | 2.20 × 0.47 × 1.12 | 4008 / 2004 / 1002 | 1 | new dressing |

## Files

- `make_textures_440.py`: host Python (numpy + Pillow); writes the tiling building PBR sets, seed 440.
- `build_440.py` (+ `lib440.py`, `mat440.py`, `house440.py`, `props440.py`): Blender. Builds every
  asset, bakes the props, makes 3 LODs with the companion `make_lods`, saves `KIT_Stonebrook440.blend`
  and writes `art_manifest.json`.
- `export_lods_440.py`: writes one FBX per LOD under `Export/LODs/`, because Unreal does not read the
  companion exporter's sibling LODs as a chain. It uses the companion `export_fbx`
  (`FBX_SCALE_ALL`, `apply_unit_scale=True`), parses every file for UnitScaleFactor 100 and zero-length
  normals, and writes `fbx_lod_export.json`.
- `Export/Game/...`, `Export/manifest.json`: output of `dink.py export_ue` (FBX with sibling LODs + GLB).
- `make_layout_440.py` writes three files:
  - `layout_440.json`: draft placement in original map pixels, same schema as
    `StonebrookExterior/exterior_layout.json`.
  - `runtime_manifest_440_draft.json`: the world_cm/offset_cm values the existing importer would publish.
  - `layout_checks_440.json`: checks against the original hardness and trigger.
- `render_previews.py` + `layout_preview.py`: Blender previews (below).
- `validation.json`: `dink.py validate` report. `ledger_rows_proposed.csv`: proposed rows with SHA-256.

Rebuild (from this directory):

```sh
python3 make_textures_440.py
blender -b --factory-startup -t 3 -P build_440.py              # ~13 min, mostly baking
python3 ../../../../tools/blender/dink.py validate --blend KIT_Stonebrook440.blend --report validation.json
python3 ../../../../tools/blender/dink.py export_ue --blend KIT_Stonebrook440.blend --out Export --formats fbx,gltf --source-root ..
blender -b --factory-startup -t 3 -P export_lods_440.py
python3 make_layout_440.py
for m in house props closeup layout; do blender -b --factory-startup -t 3 -P render_previews.py -- $m; done
python3 make_ledger_rows.py
```

## Layout and collision policy

The original house hardness is a tile outline of the projected roof, roughly 25 × 20 m and hollow inside.
As on screen 439, the layout asks for `authored_collision_screens: [440]`, so the house blocks with its
own walls. Its UCX boxes keep the 46 cm door recess open, so the P06 trigger stays reachable. The band
between the stone footprint and the old roof outline becomes walkable yard under the eaves. The fence,
oak, boulders, barrels, tools and new dressing collide. Grass does not.

Leaning tools use full Unreal rotators, computed against `FRotationMatrix` and checked by round trip in
`make_layout_440.py`. `preview_layout.png` places every row with the same bilinear transform, FBX Y
mirror and rotator maths as the runtime.

The importer (`Scripts/import_stonebrook_art.py`) hard-codes its `warp_overrides` per screen. Screen 440
needs the row given here before this layout can be published.

## Verified / not verified

Verified in Blender only:
- The validator passes with 0 errors.
- Every LOD FBX has UnitScaleFactor 100 and zero zero-length normals.
- Dimensions are recorded in the manifest.
- The door centre lies inside the original trigger rect.

Not verified: Unreal import, Nanite/LOD behaviour, material bridge settings, Lumen, actual walking,
camera occlusion by the deep eaves, and rendered gameplay screenshots.

## Validation numbers

- `dink.py validate` (after pass 2): 13 assets, 13 passed, **0 errors**. The 62 warnings break down as follows:
  - 54 `NAME_TEXTURE`: the validator reads the `.png` in Blender image names. The same applies to the existing kits.
  - 3 `NON_MANIFOLD` (building, allowed): open wall skins behind the quoins.
  - 1 `TRIS_OVER_TARGET`: the house has 145k LOD0 triangles against a 60k target; the hard limit is 200k.
  - 2 `TEXEL_DENSITY`: the shovel and axe exceed the 1024 px/m band, which is harmless.
  - 1 `COLLISION_BOUNDS`: the wheelbarrow hull is 7 cm beyond the mesh.
  - 1 `LOD_BOUNDS`: hay bale LOD2 dropped loose stalks.
- `dink.py export_ue`: all 13 assets exported to FBX + GLB (`Export/manifest.json`).
- `fbx_lod_export.json`: 39 per-LOD FBX files, all UnitScaleFactor 100, 0 zero-length normals.
- `cleanup_440.py` removed folded back-to-back face pairs from decimated LODs (bale LOD1/2, house LOD2),
  which otherwise exported cancelling normals.
- `layout_checks_440.json`: the door centre (312.5, 290) lies inside the original S440_P06 stamp
  [295, 263, 330, 293]. 23 % of the new stone footprint overlaps original solid/sprite/warp pixels,
  because the original house hardness is a hollow outline, not a filled area.

## Realism pass 2 (owner-approved refinement)

1. **Hay bale.** The bale is now one continuous compressed body (`lib440.rounded_box`, 12.9k LOD0 triangles):
   - rounded edges and faces bulging up to 1.4 cm;
   - two sisal bands seated in 9 mm grooves around the bale;
   - faint 1.5 mm flake creases;
   - straw fibres running continuously along the bale, baked at 2048 px;
   - 110 loose protruding stalks.

   The stalks are tagged with a `stalk` face attribute. `keep_stalk_lods` in `build_440.py` builds LOD1/2
   as a decimated body plus copied stalks (all of them in LOD1, every second one in LOD2), so the
   silhouette keeps its stalks.
2. **Bark and end grain** (`mat440.wood_material`):
   - **Bark:** interlacing vertical furrows from two scales of ridged noise along the grain, cross-checks
     splitting the plates into irregular blocks, per-plate tone, moss in crevices, crustose grey-green
     lichen and rare orange lichen on the plates.
   - **End grain:** uneven ring widths, a sapwood/heartwood split, and tapered radial drying checks that
     widen toward the bark.
   - **Axe marks:** four sets of short criss-cross cuts on the chopping-block top (`chop` face attribute),
     with a worn, lighter cutting surface.
3. **Thatch:**
   - The strand coordinate is now taken per ring vertex from the eave ring, so strands fan smoothly round
     the hips with no projection seam. Displacement samples the same coordinate.
   - The hip "spikes" were actually corner quoins and buried wall tops poking through the rounded thatch
     corners. Quoins now stop below the roofs (lower storey 2.95 m, upper 4.7 to 6.5 m), and the wall skins
     drop their buried tops by up to 0.9 m near each corner.
   - The course sawtooth was halved and the butt bands toned down. Strand streaks are longer.
4. **Stone walls:**
   - The rubble generator now mixes angular blocks, water-rounded cobbles, bedded slabs, wedges, split
     pairs and stacked pairs.
   - The wall material is a stacked 2.4 × 4.8 m set (2048 × 4096 px) mapped by absolute height. Its lower
     copy carries:
     - damp darkening up to about 0.5 m and a fainter one to 1 m;
     - green algae in the bottom ~40 cm and moss in the low joints;
     - rain splash-back speckle up to about 0.8 m.
   - The upper storey and chimney sample only the clean copy. Quoins and sills map into the clean copy.
5. **Leaning tools:** `make_layout_440.py` now runs a real contact test:
   - `build_440.py` exports each tool's convex-hull vertices (`hull_points_m`) and the measured
     displacement of the east wall skin (`east_wall_relief`, 25 cm cells).
   - Every hull vertex is transformed with the Unreal rotator, and the tool slides until its first vertex
     touches the displaced stone surface.
   - Results are in `layout_checks_440.json` → `leaning_tool_contact`: minimum gap 0.0 cm for all four
     tools, contact at 1.03 to 1.45 m, feet 0.24 to 0.30 m from the wall.
   - The scythe was turned so its blade runs along the wall; it previously stood 1 m off.

`preview_detail.png` is the bale/block/woodpile close-up. `preview_eastwall_tools.png` shows the laid-out
east wall: tools in contact and the grime band.

`merge_assets_440.py` replaces single collections in the kit after a `build_440.py -- --only` build, so one
prop can be re-baked without the ~25 min full build. The full build reproduces everything from scratch.

## Honest quality notes

- The grime band is a texture gradient. It reads at the wall foot, but there is no geometric soil contact.
  The meadow meets the wall at a straight line.
- The thatch is seamless now, but at close range it still shows faint horizontal course banding. The strands
  converge strongly near the top of the hips, so the texture looks compressed there.
- One quoin face per corner maps onto a wedge-shaped stone from the atlas, which looks odd at ground level.
- The bale reads as straw. The loose stalks are thicker than real straw so they survive at distance, and
  they look stiff at arm's length. LOD0 is 12.9k triangles, against a 6k prop target and 20k hard limit.
- The bark is now furrowed and irregular. The firewood end grain is plausible but uniformly pale across
  pieces.
- Tool handles are clean ash with grip polish; the iron is dark forged steel with cavity rust.
- Leaning-tool contact uses the wall skin's stone displacement on a 25 cm grid. It does not account for
  texture-only normal detail, and the ground is treated as flat (z = 0).
- Preview lighting is a Blender sky and sun on a dark meadow, not Lumen.
