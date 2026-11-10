# Art standard

Binding rules for every mesh, material and texture under `SourceAssets/Art` and `Content/Dink`. They build on the companion conventions ([`tools/blender/CONVENTIONS.md`](../../../tools/blender/CONVENTIONS.md): classes, pivots, units, naming, LODs, collision), which still apply where this page says nothing. Where the two disagree, this page wins.

`python3 -I Scripts/art_standard_check.py` checks sections 2 to 5, prints warnings (over a soft target) and exits 1 on any violation. It reads the library and the numbers from the tables on this page: change a rule here, not in the script.

## 1. Look

The owner's rule (`doc/remaster/REMASTER_PLAN.md` section 6, owner update 8 Nov 2026):

> photorealistic art authored in Blender, using the original sprites as guide and inspiration. Preserve Dink’s recognisable silhouette and colours (red-brown hair, grey-blue sleeves, brown jerkin/backpack, olive trousers and red bracers), the original buildings’ character and gameplay identities. Improve believable construction, materials, cloth, skin, wear and lighting. This owner request supersedes the earlier stylised-realism preference; use the original art as a design reference rather than copying its low-resolution rendering.

Consistency rules that make that look hold across the whole world:

- **Real size.** Meshes are modelled at real-world scale, like the player and the dressed screens, and are placed at real size (`fit: none` in `families.json`), not stretched to the greybox's layout-scaled cards.
- **One family looks like one family.** Every barrel in the game is the same barrel, every pine the same pine (with a stable per-placement yaw), until a variant is authored and bound on purpose. Variants that the plan requires are separate assets: scripted burnable trees look dry, bombable rocks look cracked.
- **One material library** (section 2): photoreal surfaces come from shared library materials, not from a private bake per prop.
- **Gameplay identity is never art's to change.** Origin IDs, scripts, hardness and collision stay; art that dresses a placement is visual only unless a reviewed art manifest replaces the screen's collision.

## 2. Shared material library

Static meshes (props, kit modules, foliage, buildings, doors, weapons) use materials from this table only. A new material is added to this table, with its texture set, before any mesh uses it; a material private to one prop (a unique bake such as `MI_Barrel_Oak_01_PhotoBaked`) is a violation. Characters and creatures are exempt: skin, eyes, hair and wardrobe sets belong to one rig.

| Material | Use | Defined in |
|---|---|---|
| `MI_Stonebrook_Oak` | oak timber: planks, beams, furniture, staves, fence rails, bark | `Stonebrook/art_manifest.json` |
| `MI_Stonebrook_Limewash` | limewashed plaster and timber walls | `Stonebrook/art_manifest.json` |
| `MI_Stonebrook_Fieldstone` | fieldstone masonry, hearths, boulders | `Stonebrook/art_manifest.json` |
| `MI_Stonebrook_Linen` | cloth: bedding, sacks, covers | `Stonebrook/art_manifest.json` |
| `MI_Stonebrook_WroughtIron` | iron: hoops, hinges, fittings, candle holders | `Stonebrook/art_manifest.json` |
| `MI_Stonebrook_Wicker` | wicker, woven straw, pastry crust | `Stonebrook/art_manifest.json` |
| `MI_Stonebrook_Soot` | soot and fire-blackened surfaces | `Stonebrook/art_manifest.json` |
| `MI_Stonebrook_Thatch` | roof thatch | `StonebrookExterior/exterior_manifest.json` |
| `MI_Stonebrook_OakLeaf` | leaf cards, grass blades | `StonebrookExterior/exterior_manifest.json` |
| `MI_Stonebrook_Meadow` | meadow ground (tiling) | `StonebrookExterior/exterior_manifest.json` |
| `MI_Stonebrook_Earth` | earth paths (tiling) | `StonebrookExterior/exterior_manifest.json` |

The tiling terrain and building sets of `SharedMaterials/manifest.json` (when that library is published) join as `MI_Shared_<Name>` (`MI_Shared_CobbleStreet`, `MI_Shared_TimberPlanks`, ...); the checker accepts exactly the names that manifest lists.

Every library material is a BC/N/ORM set (ORM: R occlusion, G roughness, B metallic; OpenGL normal, flipped green on import), 1024 px per 2 m of surface for tiling sets.

## 3. Triangle budgets

LOD0 triangles per asset, after export, per class from CONVENTIONS.md (the photoreal props already follow the same pair: soft 6,000, hard 20,000). Above the **hard cap** is a violation; between the **soft target** and the hard cap is a warning to justify in the asset's notes.

| Class | Soft target | Hard cap | Note |
|---|---:|---:|---|
| `prop_small` | 1,500 | 5,000 | under 0.6 m: candles, pies, cups, tools |
| `prop` | 6,000 | 20,000 | barrels, furniture, sacks, boulders |
| `prop_large` | 20,000 | 60,000 | fireplaces, wells, fence runs, carts |
| `foliage` | 8,000 | 25,000 | trees and plants; LOD0-LOD2 required |
| `kit_wall` | 2,500 | 8,000 | grid wall modules |
| `kit_floor` | 1,000 | 4,000 | floor modules, paths, decals, screen-fitted ground chunks |
| `kit_ceiling` | 1,000 | 4,000 | ceiling modules |
| `kit_piece` | 3,000 | 10,000 | doorways, posts, debris, other modular pieces |
| `door` | 4,000 | 12,000 | hinged leaves |
| `building` | 60,000 | 200,000 | whole buildings |
| `weapon` | 3,000 | 8,000 | held items |
| `character_hero` | 40,000 | 70,000 | Dink; LOD0-LOD3 required |
| `character_humanoid` | 20,000 | 35,000 | NPCs; LOD0-LOD3 required |
| `creature_quadruped` | 15,000 | 30,000 | pigs, dogs; LOD0-LOD2 required |
| `creature` | 25,000 | 60,000 | ducks, pillbugs, slimes, dragons; LOD0-LOD2 required |

## 4. Texture resolution

Largest texture edge per class, in pixels, from CONVENTIONS.md. Hero props (placed once or bound by origin) may use 2048; a prop that dresses a family across the world (a `families.json` row: small scatter repeated hundreds of times) is capped at 1024. Library sets are shared and count once.

| Class | Max edge | Max edge as family scatter | Texel density (px/m) |
|---|---:|---:|---:|
| `prop_small` | 2048 | 1024 | 1024 |
| `prop` | 2048 | 1024 | 512 |
| `prop_large` | 4096 | 2048 | 256 |
| `foliage` | 2048 | 2048 | trim sheet |
| `kit_wall` | 4096 | 4096 | trim sheet / 1024 per 2 m tiling |
| `kit_floor` | 4096 | 4096 | trim sheet / 1024 per 2 m tiling |
| `kit_ceiling` | 4096 | 4096 | trim sheet / 1024 per 2 m tiling |
| `kit_piece` | 4096 | 4096 | trim sheet |
| `door` | 2048 | 2048 | 512 |
| `building` | 4096 | 4096 | 256 |
| `weapon` | 2048 | 2048 | 1024 |
| `character_hero` | 4096 | 4096 | 1024 |
| `character_humanoid` | 4096 | 4096 | 1024 |
| `creature_quadruped` | 2048 | 2048 | 512 |
| `creature` | 4096 | 4096 | 512 |

## 5. Family binding

- **Authored screen architecture with no original sprite counterpart:** an explicit source record `authored_architecture: {"screens": [1], "purpose": "exposed interior roof adaptation"}` may replace a sprite-family declaration only for `kit_ceiling`, `kit_wall` or `kit_piece`. `screens` must be a nonempty unique list of positive integer screen IDs and `purpose` a nonempty description. Every actual runtime use of that mesh must be a direct `elements[].mesh` reference in a `dink-art/1` manifest on a declared screen, with no context, family, replacement, asset-list or different-screen uses. Missing/conflicting declarations do not qualify. Props and name-only matches never qualify. This exemption only addresses family identity; shared materials, triangle/texture caps, gameplay and collision rules still apply.

- **Every delivered mesh declares the sprite family or families it dresses.** A family is an original sprite sequence, written as the audit writes it (`173 bonuses/barrels/barel-`, the `dink.ini` number and path), or a class id from the data repo's `tools/data/sprite_classes.csv` (`barrel`, `tree_pine_large`). The declaration is a `families` list on the asset's entry in its source manifest, or a row in `Content/Dink/Data/Art/families.json` naming the mesh. A mesh with neither is a violation once it is imported under `Content/Dink`.
- **Exempt:** screen-fitted terrain that exists for one screen only: meshes named `SM_<Area>_<screen>_{Land,Bank,Water}_*`, `SM_Vista*`, `SM_Ground_*` and `SM_Path_*`. They dress that screen's ground.
- **`families.json` binds a family to one mesh** for every greybox placement that no origin or screen binding handles. A class row wins over a sequence row. Rows: `family`, `mesh` (`/Game/Dink/...`), `fit` (default and normal choice `none`: the mesh's authored real size, standing at the card's ground point; opt-in only: `footprint`, uniform scale to fit the layout-scaled sprite card's width and height, and `height`, to the card's height), `yaw_from_sprite` (default false: a stable per-origin yaw; true: the mesh front faces the sprite's view), optional `scripted` (true: also dress placements with a script; default false, so scripted variants stay distinct), `note`.
- **Bind only what reads right.** A family is bound to a mesh only when the mesh is that thing at that silhouette. A boulder is not pebbles, a chair is not a stool, a leafy oak is not a dead tree, a wicker basket is not a grave: leave those unbound and say so in the row notes of the nearest bound family.
- **Precedence.** Origin bindings (`replacements`, `hide_origins`, `hide_origins_by_vision`, `warp_overrides`, creature and character `placements`) and screen dressing (`hide_screen_visuals`, `authored_collision_screens`, any manifest with `elements`) win over a family row. The family layer only touches what is still greybox.
- **Visual only.** A family mesh has no collision and no navigation effect; the placement keeps its hardbox, its origin ID and its script, and is never tagged `DinkAuthoredArt` (which switches gameplay to authored geometry).

## 6. Delivery checklist

1. Source manifest entry: class, `dimensions_m`, materials (library names), `families`.
2. Export manifest (`Export/manifest.json` from `dink.py export_ue`) or export report with LOD0 triangles and texture sizes.
3. `python3 -I Scripts/art_standard_check.py` passes for the asset.
4. A `families.json` row if the mesh should dress its family across the world; `python3 -I Scripts/art_coverage.py` shows what it turned final.
