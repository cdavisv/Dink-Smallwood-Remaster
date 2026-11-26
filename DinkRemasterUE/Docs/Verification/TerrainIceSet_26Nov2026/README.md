# Ice terrain set: tile class `ice` draws lake ice instead of trampled snow (26 November 2026)

The Ice set of the old branch `art/gate2-snow-ice` (Fable 5.2, made 14-15 Nov, 331 commits behind master), brought onto master
`6dd60a8c8` as ART-ONLY files plus a data binding by art-finish-1 (Opus, 26 Nov), who changed no texture and judged no look.
art-gore-6 (Fable, 23 Nov) rendered the set in Blender (`01_blender_23nov_ice_set.jpg`: reads as lake ice; weak: the 4 m tile
repeats visibly, the veins are thick) and found it worth bringing this way. **FRAMES FOR FABLE.**

In this change:

- `SourceAssets/Art/PhotorealPass/Terrain/Ice/` (5 maps + `set.json`) and its row in `Terrain/manifest.json`, as on that branch;
  `ice` taken out of the Snow set's `tile_classes`.
- `Environment/terrain_layers.json`: a layer `Ice` (set `Ice`, normal strength 1, no drift) and the class binding `ice` -> `Ice`
  (was `SnowTrampled`).
- Imported: `T_Env_Ice_{BC,N,ORM,H,Macro}`, `MI_Env_Terrain_Ice`; the world export regenerated `Data/Environment/ground_classes.json`
  (only the `ice` mapping and the 23 layer entries that follow from it changed).

NOT in this change (left on that branch on purpose): its C++ (surface kind plumbing, ground relief), the material code for the
`surface` keys (`snow`, `ice`, `void`: the glossy ice sheet, crack depth, sparkle), the relief block, Snow round 4 and the Void
layer. Without the `surface: ice` shading the set is drawn as an ordinary terrain layer (its own colour, normal and roughness).

| sheet | what it shows |
|---|---|
| `01_blender_23nov_ice_set.jpg` | art-gore-6's Blender look at the set |
| `02_frames_for_fable_26nov_ice_screens_before_after.jpg` | the 1997 screens 14, 112, 109, 111, then each before (master: ice drawn as SnowTrampled) and after: play camera, from above, low, close |

Proof in copy `Saved/ArtFinish26Nov` (master `6dd60a8c8` + this change): editor build 0 warnings (no C++), game target 0
warnings, environment import OK (23 terrain layers), world import `--region all --export` and Stonebrook OK,
`Dink.Art+Dink.Import+Dink.Movement.Landforms` 115/115, `Dink.Gameplay.Probe` 29/29 with the twenty md5s equal to the world-scale
table of `packaged_probe.md` (Ch1 `ca319f4754` ... Ch20 `be78df8ac3`). Kernel: no Oops.
