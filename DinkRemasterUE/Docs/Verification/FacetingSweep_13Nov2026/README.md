# Faceting sweep: "fix blocky and polygon looking art" (13 Nov 2026)

Owner feedback while playing master `cb842dd2`. "Blocky" is the pixelated sprite cards, which leave as families are
bound (the batches after this one). This change is about the second half: static meshes that show their polygons.

## How it was looked for

1. **Every static mesh the game binds, alone, in the game.** `families.json`, the art manifests and `environment.json`
   name 161 static meshes (grass, ground and vista tiles left out). 159 of them were spawned on the empty meadow screen
   299 with `dink.CalSpawn`, grass off, and shot three-quarter from close (`parade_before_*.jpg`). This is unmodified
   master `cb842dd2`.
2. **The same in the source files.** A Blender script read the LOD0 of every source FBX and measured how much of its
   edge length is a hard-shaded edge between faces 6 to 55 degrees apart, the edges that show as facets. Untextured
   studio renders of the worst were looked at (`source_before_after.jpg`).
3. **In place.** The starting house (screen 1), its yard (439), the pig pen (407), a Windemere house (195), two dungeon
   screens (579, 260) and a Darklands screen (28) at the play camera, and placements of the families touched here, each
   from the play camera's height and close (`screens_before_after.jpg`, `placements_before_after_*.jpg`).
4. **The package files, for the two faults that drew meshes grey.** Every material package under `Content/Dink` (484 on
   master) was read for names of packages that do not exist, and every mesh that a data file binds was followed to its
   base materials for the instanced-mesh usage flag. The unit test added here repeats both without the editor.

## What was found, worst first

| # | What the game showed | Cause | Done here |
|---:|---|---|---|
| 1 | All 34 props of the unclaimed-families kit (PR #90: gold heaps, coins, hearts, statues, bookcase, tools, machines, the conch ...) grey with a faint checker, no colour, no normal map. The gold heap is a bare dome, a boulder pair is two faceted lumps. | `Content/Dink/Photoreal/Unclaimed/M_Struct_Baked` named the textures of the arrow as its defaults. The arrow was removed from the kit before the merge; the master then no longer compiles (`Failed to compile Material for platform SF_VULKAN_SM6, Default Material will be used in game`) and every instance of it falls back to the engine's default material. PR #90's captures were taken before the removal. | Kit imported again: the master is rebuilt on textures that exist. No other material package of the project names a missing package (484 read on master). Unit test `Scripts/tests/test_photoreal_material_references.py` fails on such a reference (it fails on master, passes here). |
| 2 | Boulders: lumps with diamond-shaped dents; the background (instanced) ones grey. | The six boulder classes were bound to `SM_Boulder_Fieldstone_01`, the old Stonebrook kit boulder. Its material `MI_Stonebrook_Fieldstone` has no "Used with Instanced Static Meshes" flag: `missing usage flag InstancedStaticMeshes! Default Material will be used in game`. Five placements, all on screen 244, are instanced. | The rows bind photoreal boulders: the four built for these classes (unclaimed pass, now imported) and the three field boulders. The same unit test follows every mesh that `families.json`, `town_houses.json` and `environment.json` bind to its base materials and fails when the flag is missing (it fails on master). Two more family meshes have no flag, the old kit fence and the old oak barrel; all their placements are actor cards, which are not instanced, so they draw correctly, and their materials are pinned by source contracts. The test lists them as exceptions and fails when an exception is no longer needed. No photoreal master material lacks the flag. |
| 3 | Thorn brambles: tangles of bent square sticks. | Canes were four-sided tubes through every second path point (a kink every 18 cm). | Six sides through every point; the bush is now a hedge twice as wide as deep (the next batch scales it to the thorn sprite). |
| 4 | Coins with ten-sided rims; the gold heap a smooth dome (behind the grey of 1). | Ten-segment discs; the heap's game mesh was a lathed dome with the coins baked on. | Coins: 24 sides and a chamfered rim. Heap: a three-lobed mound under two layers of coins in the source (no bare body shows), and in the game mesh the 55 coins that stand proudest are real discs that break the outline. |
| 5 | Jars: outlines of straight runs with corners; the jug's handles bent in three straight pieces. | The profile was lathed as given, a polyline; 22 to 28 sides. | Profile through a Catmull-Rom curve, 40 to 48 sides, handles of six segments. |
| 6 | Interior walls: the curved dungeon wall in flat strips; diagonal creases across stone faces; triangles in the plaster under raking light. Mild at the play camera. | The wall kits were exported flat shaded. | Smooth shading with hard edges only where faces meet at more than 28 degrees. Geometry is identical (the module table did not change). |

Seen and **not** changed here, with the reason:

- **The old Stonebrook kit pieces** (`Kits/Stonebrook`: candle with a twelve-sided flat-shaded stick and base, pie with a
  polygon rim, the stacked-board barrel, the feed sack) are stylised and faceted when seen alone. In the game they are
  used only inside the hand-dressed starting house, whose manifest (`stonebrook.json`) is bound to source contracts and
  their tests; the house reads well at the play camera (`ctx_001_house`). Left for a decision: swapping the two candles
  and the pie for the photoreal ones is a three-line change to that manifest.
- **The old split-rail fence** (`SM_Fence_SplitRail_4m_01`: sawn square posts and rails) is still bound by the row
  `fence_rail_ew`. Fences are laid as runs by the structures batch, which removes that row; binding the photoreal fence
  here would only swap one 4 m module per 18 m sprite.
- **Tree stumps** (`SM_Veg_Stump_01/02`, 47 placements): the root flares are flat fins that end in points (each root
  ridge is three samples wide in the generator). The fix is written (a blunt, finely sampled root in `bl_tree.py`
  `root_base`) and comes with the next change, which needs its own import and captures.
- **The cabbage** (`SM_Veg_Cabbage_01`, 4 placements): a few large bent leaf cards that read as crumpled green
  sheets. Next change.
- **Sprites that scripts create** (`create_sprite`: the pickups of screen 352, for one) are drawn as grey cylinders. That
  is the placeholder of `ADinkScriptSpriteActor` (`DinkScriptSpriteComponent.cpp`), not a mesh of a family; it has no
  origin ID and is outside this work. Reported to the coordinator.

## Files

| File | What it shows |
|---|---|
| `parade_before_1.jpg` to `_3.jpg` | Master `cb842dd2`: 159 bound static meshes, each alone on the meadow, in the game. The grey ones are the unclaimed kit (finding 1). |
| `unclaimed_kit_before_after_1.jpg`, `_2.jpg` | The 34 props of the unclaimed kit, master against this change, same camera. |
| `boulders_before_after.jpg` | The old kit boulder against the four boulders newly bound for its classes; the three field boulders (unchanged meshes, now also bound to boulder classes). |
| `jars_thorns_before_after.jpg` | The four jars and the three thorn meshes. |
| `walls_before_after.jpg` | The interior wall modules. The difference is small at this size; `source_before_after.jpg` shows it. |
| `source_before_after.jpg` | Untextured studio renders of the source LOD0: two jars, the curved and a straight dungeon wall, a plaster wall. |
| `screens_before_after.jpg` | Seven screens at the play camera, master against the exact tree of this change. The demon idol of screen 579 has its stone back; nothing else moves. |
| `placements_before_after_1.jpg` to `_3.jpg` | Placements in place, play camera height and close: boulders (the instanced ones of screen 244 among them), jars, bowl, gold heap, coins, dungeon and plaster walls, a bound thorn bush and thorn branch. "not captured" = no master shot of that placement was taken. |
| `screen_244_boulders_after.jpg` | Screen 244, where master drew four boulders grey. |
| `boulders_fit_none_vs_footprint_rejected.jpg` | Left: the boulder rows as committed (`fit` none, real size). Right: the same rows with `fit` footprint, tried and rejected (see below). |

## Checks

- **Game log of the capture on this tree** (50 shots, 12 screens, `Scripts/PhotorealQA/run_capture.sh`): no
  `Failed to compile Material`, no `missing usage flag`, no `Default Material will be used` line. The same capture of
  master logs one of each (the kit master, `MI_Stonebrook_Fieldstone`).
- `python3 -m unittest discover -s Scripts/tests`: 825 tests pass (private project copy with the binaries). The three
  tests of `test_photoreal_material_references.py` pass here; run against master's content two of them fail.
- `Scripts/test.sh Dink.Art`: 58/58.
- `python3 -I Scripts/art_coverage.py`: final 3,972, placeholder 2,483, cut 152, as on master.
  `Scripts/gate2_backlog.py` reproduces `doc/remaster/ALPHA_GATE2_BACKLOG.md` byte for byte.
- `Scripts/verify_sources.py --metadata-only` passes; `Scripts/scrub_private_paths.py --check` is clean.
- Every capture named above was looked at, sheet by sheet and the doubtful ones at full size.

## Not checked

- **The probe** (`Dink.Gameplay.Probe`) was not run. The change is visual: mesh and material packages and six `mesh`
  values in `families.json`; family meshes have no collision and family-dressed actors keep the original pixel rules
  for touch, hit, push and talk.
- **Boulder size.** The four boulders of the unclaimed pass are 0.8 to 1.5 m wide, about half of what their sprites
  show beside the hero (1.7 to 3.1 m), and smaller than the 3 m kit boulder they replace. Collision is the original
  hardbox, 4 to 9 m wide in the stretched outdoor layout, so the unseen margin around a boulder grows (it was there
  with the old boulder too). Fitting the rows to the sprite card (`fit` footprint) was tried in the game and rejected:
  rocks 6 to 9 m wide that swallow the camera and stand in each other, with soft textures
  (`boulders_fit_none_vs_footprint_rejected.jpg`). The remedy is in the source (build them at the size the sprite
  shows) and is the next change.
- **The gold heap in place, close.** On screen 352 the hero is set down among fifteen heaps and in this run touched
  the nearest four on arrival: they were picked up and left with their sparkle, as the `lgold` script says, so the
  close shot shows bare ground. The heaps further along the shore carry the new mesh in the play-camera shot; the mesh
  itself is in `unclaimed_kit_before_after_1.jpg`. In the master run the same four were not picked up; why the two
  runs differ was not found (the mesh takes no part in the touch test: family art has no collision and is not
  "authored geometry").
- **`SM_Boulder_Field_A_PR`** (unchanged, from the structures stream) shows a small black patch on one flank in the
  game. Not looked into.
- LOD1 and LOD2 of the rebuilt meshes were not shot; the parade is LOD0 at close range.
- Packaged build: not cooked. `Scripts/package.sh` may not cook `Content/Dink/Photoreal` by default (reported by the
  creatures session, not verified here).
- The Dink.Art run and the captures used a project copy whose C++ carries a two-line change for a later batch
  (`UDinkEnvironmentSubsystem` reads a second, absent data file). It is not in this change and does nothing without
  that file; master's own binaries were not rebuilt for this run.
