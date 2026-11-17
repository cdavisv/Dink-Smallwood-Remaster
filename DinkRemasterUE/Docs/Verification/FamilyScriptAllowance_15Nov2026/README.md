# Family art for scripted placements whose script never changes the picture (A202, rest), 15-16 Nov 2026

## Defect

`DinkArtFamily::Decide` dresses a scripted placement only when its whole `families.json` row is `"scripted": true`. Two classes
mix scripts that change the sprite with scripts that do not, so the harmless ones kept their 1997 card:

| Placement | Class | Script | What the script does to its own sprite |
|---|---|---|---|
| S534_P10 | `tree_pine_large` | `s2-sec2` | `main`: `preload_seq(167)`, `sp_hard 0`, `draw_hard_sprite`. `talk`: two `say_stop` lines. `die` (run by `dam-fire.c` when a fireball hits a scripted tree): a `say` line, `sp_hard 0`. Never `sp_pseq`/`sp_pframe`/`sp_seq`/`sp_kill`/`sp_nodraw`/`sp_brain`/move. |
| S003_P15 | `cabinet_wood` | `s1-h3-4` | `talk`/`hit`: one `say` line each ("A small table.", "Ouch, splinters."). |
| S003_P16 | `cabinet_wood` | `s1-h3-1` | `talk`/`hit`: one `say` line each ("A nice wooden table.", "Stupid table!"). |

The screen scripts of 534 (none) and 3 (`s1-h3-s`: `&vision` and a random line) do not touch these sprites. Each script is used by
that one placement only (`placements.csv`).

The same rows hold placements that must keep their card, and still do: the burnable pines S307_P13 (`s2-sec1`), S659_P06 (`s2-sec3`),
S710_P14 (`s3-sec1`) (`die` burns them with `sp_seq 20` / `sp_pseq 89`; `environment.json` `burnable` draws them), and S366_P15
(`s2-fgate`, changes its picture).

Left out on purpose: S149_P02 (`tree_willow_large`, script `big`, which does not exist) stands at x 773, off the play area, and draws
no card at the play camera; S474_P01 (nut tree, `s1-ntree`) and S693_P06 (giant oak, `s4-tree`) belong to Fable packet VS-10.

## Fix (presentation only)

- `families.json` rows take an optional `scripted_scripts` (DinkC script names). A scripted placement whose script is listed is
  dressed like an unscripted one; every other scripted placement of the row keeps its card. Documented in the file's `about`.
- `FDinkFamilyBinding::ScriptedScripts`, `FDinkFamilyPlacement::ScriptName`; `Decide`:
  `if (P.bScripted && !B->bScripted && !B->ScriptedScripts.Contains(P.ScriptName)) return Scripted;` (FName: case-insensitive).
- Player blockers stay off for every scripted placement (unchanged `if (!P.bScripted)`), so Dink's collision is exactly as before.
- `Scripts/art_coverage.py` mirrors it (`scripted_scripts()`, `family_row_dresses_script()`).
- Rows: `tree_pine_large` `["s2-sec2"]`, `cabinet_wood` `["s1-h3-4", "s1-h3-1"]`.

No hardness, script, trace or sprite state changes: the family mesh is a visual component on the placement actor; the card is hidden
as for every other dressed placement, and `sp_active 0` still hides the whole actor.

## Coverage (`Scripts/art_coverage.py`, private smudged copy, shared `Saved/Import/coverage.csv`)

| | final | placeholder | cut | final by family |
|---|---|---|---|---|
| before (master) | 5,125 | 1,330 | 152 | 4,164 |
| after | 5,128 | 1,327 | 152 | 4,167 |

Exactly S003_P15, S003_P16 and S534_P10 moved from placeholder to final; no other row changed.

## Seen in the game

Same build, two capture runs (offscreen, 1280x720): before with master's `families.json`, after with this branch's. `dink.SceneAudit`
of the drawn primitives:

| Origin | Before | After |
|---|---|---|
| S534_P10 | `Card` (SM_DinkCard) | `FamilyArt` SM_Veg_Pine_Medium_01 (variant by origin hash) |
| S003_P15 | `Card` | `FamilyArt` SM_Cabinet_Oak_PR |
| S003_P16 | `Card` | `FamilyArt` SM_Cabinet_Oak_PR |
| S307_P13, S659_P06, S710_P14 | `BurnableBefore` SM_Veg_Pine_Dry_01 | the same (no family mesh, no second tree) |

- `534_talking_pine_before_after.jpg`: play camera looking south, close, overview. The pixel card becomes a pine at the same foot point.
- `003_tables_before_after.jpg`: overview (the brick-coloured table card becomes the wooden family mesh) and an after-only side view of
  S003_P15. At the default play camera (looking north from 280,230) both tables are behind the camera.
- `burnable_pines_unchanged.jpg`: 307, 659, 710 overviews, before and after: the dry burnable pine is unchanged (pixel differences are
  the wandering ducks and wind).

## Tests

- `Scripts/test.sh Dink.Art+Dink.Import+Dink.Gameplay.Probe` (private copy built from this branch on master 9cc796b6):
  **118/118 passed**, 0 failed (7 with warnings), 905 s. `Dink.Art.Family.ResolverPrecedence` now also checks `scripted_scripts`
  (listed script dressed, case-insensitive, trimmed; unlisted script, another row and a dressed screen keep their decision).
- `Dink.Gameplay.Probe`: all twenty chapters complete, every trace md5 equal to `Plugins/DinkParity/Docs/packaged_probe.md`
  (Ch1 b4ad88c02c ... Ch10 23fd57dfdc, Ch11 0d70cebfcd ... Ch20 84f33687af).
- `python3 -I Scripts/tests/test_family_script_allowance.py`: 4/4 (row parse, decision mirror, the shipped lists, and a static
  check that every listed script never calls a picture/position/kill function on `&current_sprite`). Coverage tests
  `test_creature_class_binding`, `test_town_house_coverage`, `test_screen_ground_coverage` still pass.
- Captures: `Scripts/PhotorealQA/run_capture.sh` (offscreen Vulkan, no X display, -nosound), not the :189 Xvfb session.

## Re-verified on master bd6d227a (16 Nov 2026)

Rebased on bd6d227a (structure sets with `families_yield`, people as class rows, the #141 probe table; `families.json`,
`DinkArtFamilySubsystem.cpp` and `art_coverage.py` merged cleanly), private copy synced with fresh timestamps (the build compiles
`DinkArtFamilySubsystem.cpp`), built, world regenerated with `--export` and `--region stonebrook`.
`Scripts/test.sh Dink.Art+Dink.Import+Dink.Gameplay.Probe` **121/121** (767 s); **all twenty probe md5s equal master's new table**
(Ch1 cc2e12fb5c ... Ch20 be28390b9d). A capture of the rebased tree on 3ff8cd25 (`rebased_check.jpg`, looked at): the tables of
SCR_003 (S003_P15 east, the overview) and the talking pine of 534 are drawn by their family meshes; the burnable pines of 307/659/710
are unchanged by this branch. The same capture on bd6d227a (`rebased_check_bd6d227a.jpg`, looked at) shows the same: tables and the talking pine as meshes, the burnable pines unchanged.

## Not checked

- The pine's look in dialogue (talk) and after a fireball (`die` keeps the picture; not driven in the capture).
- Whether `SM_Cabinet_Oak_PR` is the right mesh for the `cabinet_wood` class on table pictures (seq 87 frames 1 and 7): the class
  mapping is the same as for the 15 unscripted placements already dressed; the S003 scripts call them tables.
