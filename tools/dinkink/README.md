# dinkink: DinkC scripts to Ink drafts

Stage 5 of the remaster pipeline (`doc/remaster/REMASTER_PLAN.md` section 8). Reads the
`tools/dinkc` output and writes one Ink file per narrative script, plus the tables a
reviewer and the Unreal implementer need. Python 3 standard library only; compiles with
the official `inklecate` (1.2.1). The mapping itself is specified in
[`DESIGN.md`](DESIGN.md); read it before changing the converter or the runtime side.

```
cd tools/dinkc && python3 -m dinkc build --scripts ../../bin/dink/story \
    --map ../../bin/dink/map.dat --dat ../../bin/dink/dink.dat --out out    # input
cd tools/dinkink
python3 -m dinkink build --ast ../dinkc/out --out out     # about 7 s, compiles every file
python3 -m dinkink build --ast ../dinkc/out --out out --no-file-check   # root file only, 1-2 s
python3 -m unittest discover -s tests                     # 44 tests, 12-27 s (builds into a temp dir)
```

`build` exits 1 if the root story or any script file fails to compile. It never writes
outside `--out`. The `.gitignore` keeps `out/` untracked.

## Output (`out/`)

| Path | Contents |
|---|---|
| `ink/<script>.ink` | one per converted script: locals and fix switches, then knot `d_<script>` with entry stitches `on_<proc>`, bodies `p_<proc>`, label/continuation stitches `lbl_*`/`c<line>`, menus `m<line>` |
| `ink/_decls.ink` | global `VAR`s (quest facts and engine stats with their `main.c` initial values), engine pseudo-variables, `EXTERNAL` queries and their fallback functions |
| `ink/dink.ink` | root: `INCLUDE`s `_decls.ink` and every script file |
| `json/dink.json` | the compiled root story (what Inkpot would load if `.ink` import fails) |
| `names.csv` | `kind` (knot / entry / local / global / pseudo / fix), `original`, `ink`, `scope`, `script`. One row per name; both columns are unique, so it maps both ways |
| `line_ids.csv` | `id`, `kind` (spoken / title / option), `script`, `procedure`, `line`, `call`, `speaker`, `colour`, `live` (0 = behind a fix switch), `text` (original, colour code removed) |
| `director_commands.csv` | every command instance: `script`, `procedure`, `line`, `command`, `form` (line / comment / var-write / fix-intent), `blocking`, `args` (as written in Ink), `kind`, `status`, `screens` |
| `director_vocabulary.csv` | one row per command or external: `category`, `args`, `blocking`, counts per form, number of scripts, note. Category `unknown-command` marks a name that is not an engine command (`sp_prop`: only its switched-off intent uses it; the remaster's director defines it by owner decision OD1, see DESIGN.md section 9); misspelt commands (`freeeze`) never appear, their intent branch emits the corrected command |
| `shot_lists/<script>.md` | plain-language beats for cutscenes and any procedure that moves sprites, fades, or freezes Dink for 4+ `say_stop`s |
| `review_queue.csv` | `id`, `priority` (high = changes what the player sees or does), `category`, `code`, `script`, `status`, `line`, `procedure`, `engine_behaviour`, `author_intent`, `conversion`, `fix_const` (empty when nothing is switched). Categories: `never-spoken` (written dialogue the 1997 engine never speaks: `s2-jack:171`, `s4-sign3:17`, `s3-chick:42`, `s1-h3-8:13`; all behind a switch), `wrong-speaker`, `text`, `engine-differs`, `engine-matches-intent` (`goto mainloop` with no such label: nothing to switch), `structure`, `variables`, `not-code`, `missing-script`, `dead-data`, `unverified`. IDs are numbered after sorting, so they move when rows are added or removed |
| `coverage.csv` | every script (380 plus 6 referenced but missing): `kind`, `status`, `reason`, placement/caller, `screens`, line/menu/option/command counts in and out, `fix_switches`, `compiles`, `compile_warnings` |
| `compile_report.txt` | inklecate errors and warnings, root and per file |
| `summary.json` | the counts the build prints |

Statuses: `converted` (whole script, every procedure), `converted-dead` (not placed and
not called, kept as a draft), `dead` (not placed, not called, no statements), `empty`,
`missing` (referenced by `map.dat`, `sp_script` or `external` but absent from the
original, or present only as `.d`). Since 6 Nov 2026 the script's kind no longer decides:
enemy, item, weapon, magic, pickup, projectile, container, library and system scripts are
converted in full because the engine runs their procedures (`die`, `touch`, `use`, the
`emake`/`make` drop tables...). Their stat blocks are still read as data from the ASTs.

"Compiles alone" means through a wrapper that includes only `_decls.ink` and that one
file; the script files share the globals, so none can compile with no declarations at all.

## What an Ink file looks like

```
VAR s3_chick__wherex = 0                     // script-local int
CONST fix_s2_cave_l117 = false               // a review-queue switch (engine bug; true only by owner decision)

=== d_s3_chick ===
= on_talk
-> p_talk -> DONE

= p_talk
>> freeze 1 #cmd #src:23
-> m25 -> // menu, sets result
{ result == 1:
    >> wait 400 #cmd #src:35
    Hey, how's it going? #id:s3-chick.talk.002 #say:say_stop #spk:1 #col:14 #src:36
}
->->

= m25
>> choice_start 0 0 #cmd #src:25
+ {mayor == 0} [Tell her about the planned assault #opt:s3-chick.talk.c1.3]
    ~ result = 3
    ->->
```

## Runtime contract (summary; details in DESIGN.md)

- Enter a procedure: set `current_sprite` (and `arg1`..`arg9`), then
  `ChoosePathString("d_<script>.on_<proc>")`. One Ink flow (or story instance) per
  script instance; entering a procedure replaces what that instance was running.
- Output lines with the `cmd` tag are director commands; everything else with an `id`
  tag is a spoken line, `title` lines head a menu.
- Display text = line text with U+00A0 replaced by a space.
- Bind every `EXTERNAL` with `lookaheadSafe = false`.
- Facts: observe every `VAR` in `_decls.ink` and mirror it into the fact store; push
  engine stats in before entering a knot.
- Script-local `VAR`s (`names.csv` scope `local`) are per script instance: save/restore
  them per actor when a script is attached to several actors.

## Tags on output lines

| Tag | On | Meaning |
|---|---|---|
| `id:<script>.<proc>.<nnn>` | spoken | stable line ID (titles `...t<menu>.<k>`, options `...c<menu>.<index>`) |
| `say:<call>` | spoken | `say`/`say_xy` do not block; `say_stop`/`say_stop_xy`/`say_stop_npc` block |
| `spk:<int or var>` | spoken | speaker handle (1 = Dink) or the Ink variable holding it |
| `x:`, `y:` | `_xy` lines | screen pixels |
| `col:<n>` | spoken, title | colour index (14 = default) |
| `handle:<var>` | spoken | store the text sprite's handle in that variable |
| `review:<script>:<line>` | spoken | the line has a review-queue row (wrong speaker, stray character); such a line is written twice inside `{ fix_<script>_l<line>: intent - else: engine }` with the same `id` (a tag cannot be switched) |
| `title`, `blank` | title | menu title line; `blank` = an empty title row |
| `opt:<id>` | choice | option ID (inside the choice brackets, so it is a choice tag) |
| `cmd` | command | director command line |
| `src:<line>` | all | line in the original `.c` |

## Director command reference

Command lines are `>> <name> <args> #cmd #src:<line>`; integer arguments are literal,
strings are quoted, everything else is interpolated by Ink, so the director receives
values. `B` = the director must finish it before calling `Continue()` again. Counts are
command lines in the converted scripts (build of Nov 2026); `director_vocabulary.csv`
has the full list (126 command and external names, 29 of them used as externals; build of 6 Nov 2026).

| Command | Args | B | Lines | Notes |
|---|---|---|---|---|
| `wait` | ms | B | 1513 | |
| `unfreeze` / `freeze` | sprite | | 374 / 267 | 1 = Dink (player control) |
| `move_stop` / `move` | sprite, dir, stop, ignore_hardness | B / - | 216 / 61 | numpad dirs; stop is x for 4,6,1,3,7,9 and y for 2,8 |
| `playsound` | sound, speed_hz, random_hz, sprite, repeat | | 179 | sprite 0 = not positional |
| `sp_<prop>` | sprite, value | | 1642 in all (`sp_prop` is not a 1997 command: see the `unknown-command` row) | `sp_brain`, `sp_speed`, `sp_seq`, `sp_pseq`/`sp_pframe` (pose), `sp_dir`, `sp_script`, `sp_active` (0 = remove), `sp_x`/`sp_y`, ...; -1 = no change |
| `choice_start` | set_y, title_color | B | 115 | a menu follows (title lines, then Ink choices) |
| `init` | dink.ini line | | 49 | weapon animation sets |
| `kill_this_task` | | B | 44 | followed by `-> DONE` |
| `editor_type` / `editor_seq` / `editor_frame` | editor_sprite, value | | 29 / 4 / 4 | persistent world overrides (spmap) |
| `playmidi` / `stopmidi` | file | | 29 / 3 | |
| `script_attach` | sprite | | 26 | 1000 = script survives screen change |
| `load_screen` + `draw_screen` | | - / B | 19 / 19 | warp to `player_map` |
| `fade_down` / `fade_up` | | B | 17 / 17 | |
| `add_item` / `add_magic` | script, seq, frame | | 17 / 7 | |
| `draw_status`, `draw_hard_sprite`, `draw_hard_map` | | | 12 / 9 / 6 | |
| `hurt` | sprite, damage | | 8 | |
| `external` | script, proc, args | B | 7 | base game: drop tables (`make`, `emake`) |
| `screenlock` | 0/1 | | 6 | locked fight |
| `spawn` | script | | 2 | start a script's `main` in parallel |
| `add_exp`, `activate_bow`, `save_game`, `load_game`, `restart_game`, `kill_game`, `set_mode`, `show_bmp`, `show_popup`, `fill_screen`, `force_vision`, ... | | | 1-6 each | see the CSV |

**Externals** (values): `create_sprite` (spawns and returns a handle, 251 uses), `sp_*`
getters (`sp_x(s, -1)`), `sp`, `sp_editor_num`, `count_item`, `compare_weapon`,
`free_items`, `get_sprite_with_this_brain`, `game_exist`, `get_version`,
`savegameinfo(n)`, `buttoninfo(n)`, `random(range, base)` (the engine's
`rand() % range + base`, base for range 0; an external so the runtime uses its own seedable
source; `_decls.ink` has an Ink fallback), ...

**Fact writes**: `&gold` (40 writes), `&vision`, `&player_map`, `&life`, `&exp`, ... are
assignments; `director_commands.csv` lists them with form `var-write`.

**Comments, not commands** (engine-side only): `preload_seq`, `load_sound`, `debug`,
`make_global_int`.

## What a reviewer checks per script

Open `ink/<script>.ink` next to `bin/dink/story/<script>.c` (every output line has
`#src:`) and, for scenes, `shot_lists/<script>.md`.

1. Every `say` in the `.c` has one line with the same words (`#src` matches); colour and
   speaker look right (`#spk:current_sprite` is the scripted sprite itself).
2. Menus: option order, the conditions in `{...}`, and that the `~ result = N` numbers
   match the original's `if (&result == N)` branches (hidden options keep their number).
3. `goto`s: the label stitch continues where the original label is, and loops
   (`mainloop`) go back to the menu or idle loop they did in the game.
4. Every `CONST fix_*` in the file: read its `review_queue.csv` row and decide; flipping
   the constant to `true` switches the line/branch to the author's intent. Rule: the
   engine's behaviour is the default (all switches `false`), the author's intent sits
   behind `fix_<script>_l<line>`, and nothing is softened; a defect with no distinct
   intent (`goto` to a missing label) gets a review row but no switch.
5. Fact writes (`~ story = 3`) and conditions match the original variables
   (`names.csv` gives the original names).
6. Commands: plausible order and blocking (a `say` that does not wait followed by a
   `wait` is how the original timed text).

## Limits

- Runtime behaviour in Unreal/Inkpot is unverified (neither is installed). The output
  uses plain Ink (knots, stitches, tunnels, sticky choices, multi-line conditionals,
  VAR/CONST, EXTERNAL, static tags; choice tags need ink 1.1 runtime semantics, which
  inklecate 1.2.1 output already assumes). Inkpot must provide external binding with
  `lookaheadSafe = false`, tag access, variable get/set/observe and multiple flows.
- DinkC locals are per script instance; here they are global `VAR`s prefixed with the
  script name (see the runtime contract). A local procedure call runs in a fresh
  instance in the engine; in Ink it shares the caller's variables.
- The engine's text substitution order is reproduced, but substituted values are ints
  printed by Ink; `&savegameinfo`/`&buttoninfo` are external string functions.
- `get_parms` is modelled for argument counts: a short argument list gets the engine's
  zeros and a missing comma after a string cuts the list short (`engine_args` in
  `dinkink/convert.py`); too many arguments make the build fail (none exist). Other bad
  `get_parms` types are not detected beyond what `tools/dinkc` flags. `tools/dinkc`
  itself still words its `missing_comma` diagnostic as "the line works"; dinkink ignores
  that text and writes its own review row.
- `script_kinds.csv` labels a script's kind heuristically (`s1-lg`, Chealse, is an
  `enemy` by stats); the kind only words the `reason`, it no longer decides what is
  converted.
- Screens for scripts attached at run time come from the attaching script
  (`586 (via s3-tc)`); scripts given as items (`s1-bul` via `item-pig`) have none.
- Shot lists are mechanical renderings of the statements, not direction.
