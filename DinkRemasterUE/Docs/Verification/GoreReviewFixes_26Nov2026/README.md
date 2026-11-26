# Gore review follow-ups: dry outside the blood, soaked pool rims, pleated dragon wing, round cottage hole with embers

Made by stream art-gore-6 (Fable 5.2, 23 Nov 2026) and seen there in Blender only. Brought onto master `6dd60a8c8`, imported,
tested and captured mechanically by art-finish-1 (Opus, 26 Nov), who changed no mesh, texture or material and judged no look.
**FRAMES FOR FABLE: nothing in this change has been judged in the game.** Keep all original gore.

## What it is

- (a) Blood decal sheets matt outside the blood: the decal ORM maps regenerated (`Corpses/tools/gore_sheets.py`); the pale film
  round every splat was the sheet's own low roughness outside the alpha.
- (b) Soaked pool rims: `gore_sheets.blood_sheet` `soak_rim` and the kit importer's new material kind `soak` (cover dithered as
  the pit's; new parent `M_Struct_Baked_Soak`), used by the knight's and the dragon's pool cards.
- (c) Dragon remains rebuilt: pleated wing with real geometry, membrane roughness 0.90, pool card 3.5 cm up, LOD0 20,284
  triangles (soft budget 20,000).
- (d) Burning cottage: a round ragged roof hole with the ridge whole, pointed bundle ends, a sixth slot `MI_Stonebrook_Embers`
  (emissive map, 80 nits; new parent `M_Struct_Baked_Glow`), manifest rows edited.

Packages in this change (22): the ten re-imported corpse textures (`T_Corpse_Knight_Pool_*`, `T_Decal_Blood1997A/B_ORM`,
`T_Dragon_Corpse_*`), `SM_Dragon_Corpse_PR`, `MI_Dragon_Corpse_PR`, `MI_Dragon_Corpse_Pool`, `MI_Corpse_Knight_Pool`,
`M_Struct_Baked_Soak`, `SM_Cottage_Stonebrook_PR_Burning`, `MI_Stonebrook_Embers`, `M_Struct_Baked_Glow`,
`T_Stonebrook_Embers_{BC,N,ORM,E}`. The kit imports re-saved every package of both kits (and the content stamp re-imported
eleven other Stonebrook meshes in the copy); only the packages the branch meant to change are committed.

## Sheets

| sheet | what it shows |
|---|---|
| `01` to `04` | Blender, 23 Nov (art-gore-6): the knight's pool with the soak rim, the dragon's pleated wing, the cottage's round hole, the ember texture |
| `05_game_26nov_blood_splats.jpg` | the 1997 pictures 187 / 188 beside the splats of SCR_094, SCR_091 and SCR_126: play camera, top, low |
| `06_game_26nov_knight_and_dragon_pools.jpg` | 1997 275 and 216 beside the knight's pool (SCR_157) and the dragon's remains with its pool (SCR_158) |
| `07_game_26nov_dragon_212.jpg` | 1997 212 beside the dragon's remains on SCR_238 (in the sun) and SCR_100 |
| `08_game_26nov_burning_cottage.jpg` | the 1997 screen 439 in vision 1 beside the burning cottage: roof hole, embers, play camera |

Captured in copy `Saved/ArtFinish26Nov` (master `6dd60a8c8` + this change, both kits imported there) with art-gore-6's capture
scripts (`cap_{blood,pools,dragon212,cottage}_r1.txt`, output folder changed only), 1280 x 720.

## Open for Fable (named by art-gore-6)

- Does the dithered soak rim read as soaked earth or as noise at the play camera; is the pale film round S094_P06 gone; does
  the wing hold in the sun on 238; is emissive 80 right for the embers beside the fire cards; do the embers read as embers or
  as paving.

## Proof (26 Nov 2026, copy `Saved/ArtFinish26Nov` = master `6dd60a8c8` + this change)

- Editor build 0 warnings (no C++ in this change; clean build of the copy on master the same morning), game target 0 warnings.
- Kit imports `Corpses` (26 materials, 15 modules, 0 warnings) and `Structures/Stonebrook` (10 materials, 15 modules, 0
  warnings): the first import of kind `soak` and of an E-map row in that kit, both without a warning.
- `Dink.Art+Dink.Gore` 99/99 after each import; `Dink.Gameplay.Probe` 29/29 with the twenty md5s equal to the world-scale
  table of `packaged_probe.md` (Ch1 `ca319f4754` ... Ch20 `be78df8ac3`), run after both imports. Kernel: no Oops.
