# expanded: DinkExpanded content packs -> the plugin's runtime data

Design: `doc/remaster/EXPANDED_CONTENT.md`. Python 3.11+ standard library only (tomllib); runs `tools/dinkc` and
`tools/dinkink` (and so `inklecate`) on the 1997 scripts plus the packs' scripts.

```
cd tools/expanded
python3 -m expanded build [--analyse ../analyse/out] [--check] [--keep-work DIR]   # about 6 s
python3 -m unittest discover -s tests                                              # 20 tests, about 15 s
python3 -I probe_parity.py <test_expanded_off.log> <test_expanded_on.log>          # the parity proof
```

Reads `DinkRemasterUE/Plugins/DinkExpanded/Packs/<pack>/pack.toml` and `story/*.c`, the 1997 tables and story the project
ships (`DinkRemasterUE/Content/Dink/Data/{Gameplay,Facts,Story}`), `bin/dink/story`, `map.dat`, `dink.dat`, and, when it
exists, `tools/analyse/out/regions.csv` (join anchors must be on screens reached by design). Writes only
`DinkRemasterUE/Plugins/DinkExpanded/Content/Data` (or `--out`); `--check` writes nothing and exits 1 when that output is
stale (the unit test `TestCommittedOutput` does the same).

## pack.toml

```toml
[pack]            id, number (1-9: namespace x<n>), name, wave, status, draft
[[sheet]]         id, kind (wilderness|settlement|dungeon|interior), direction [x east, y south], gap_m
[[screen]]        screen (an unused 1997 map slot), sheet, grid [col, row], name, kind, region, base_script, music,
                  solids [[x0, y0, x1, y1], ...] (map pixels, hardness 1, greybox blocks)
[[placement]]     screen, index (1-99), x, y (map pixels), seq, frame, brain, size, script, kind (npc|creature|item|prop),
                  name, hard, hitpoints, strength, defense, exp, touch_damage, speed, timing, base_walk/idle/attack/die, nohit
[[join]]          id, from {screen, rect}, to {screen, point}, back {screen, rect}, return {screen, point},
                  requires {fact, at_least} (optional)
```

Map pixels are the 1997 playfield without the 20 px status bar (0..600 x 0..400). DinkC scripts use the engine's x (map x
plus 20), as the 1997 scripts do; `placements.csv` stores the engine x.

## Rules the build enforces

- pack screens are unused 1997 map slots: no map.dat record (`screens.csv`), no 1997 `&player_map = N`, owned once;
- scripts `x<n>-*`, not named like a 1997 script; placements on the pack's own screens; placement scripts are the pack's or
  1997 scripts (creatures reused);
- globals `&x<n>_*` with initial value 0; 1997 story globals read-only (engine stats such as gold, life, exp may change);
  no `script_attach`, `save_game`, `load_game`, `restart_game`, `kill_game`, no `&player_map =`;
- joins: from/return on 1997 screens, to/back on the pack's; the 1997 trigger and return point on open ground (hardness 0)
  in every vision, 40 px clear of scripted 1997 sprites and warps, on a screen reached by design;
- the converter flags nothing of high or medium priority in the pack scripts;
- the merged story keeps every 1997 container byte-identical and adds only `d_x<n>_*` knots and `x<n>_*` VARs (all 0).
