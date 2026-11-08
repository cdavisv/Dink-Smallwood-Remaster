# dinkc: DinkC parser and script tables

Stage 1/3 tooling for the remaster (see `doc/remaster/REMASTER_PLAN.md` section 8). It
reads the base game's 380 `bin/dink/story/*.c` scripts plus `map.dat` and `dink.dat`,
builds a JSON syntax tree per script, and derives the tables the conversion stages
need. Python 3 standard library only. It never writes outside the `--out` directory.

```
cd tools/dinkc
python3 -m dinkc build --scripts ../../bin/dink/story --map ../../bin/dink/map.dat \
    --dat ../../bin/dink/dink.dat --out out
python3 -m dinkc parse ../../bin/dink/story/s3-st2p.c      # one AST to stdout
python3 -m unittest discover -s tests                      # about 1 s
```

`build` also decodes every `.d` file (byte-pair compressed copies the engine prefers
over the `.c`) and reports any that differ from their `.c`; `--no-d-check` skips this.

## How the engine reads a script (and therefore how this parser does)

The HD engine has no parser. `run_script` reads one physical line at a time
(`read_next_line`, `source/dink/dink.cpp:3484`), strips leading spaces and passes it to
`process_line` (D:7070). Before reading, CR becomes LF, TAB becomes a space and NUL ends
the file (`misc_util.cpp:87`). The rules that follow from the code, and that the parser
copies:

1. **One statement per line.** `process_line` peels off any number of the prefixes
   `{`, `}`, `else` and `if (...)`, then runs one statement. Anything after that
   statement on the same line is thrown away (most commands `return 0`, which makes
   `run_script` read the next line). `;` is optional.
2. **Procedures run from their `void` line to the next `void` line.** `locate` (D:3717)
   finds the first line whose first space-separated word is `void` and whose second
   word, cut at `(`, matches the name (case-insensitive). Execution starts on the next
   line and ends at the next line starting with `void`, at `return`, or at end of file.
   Statements after a procedure's closing `}` therefore still belong to it.
3. **Braces only matter for skipping.** A false `if` sets "skip next"; if the next
   thing is `{` the engine skips to the matching `}`, otherwise it skips the rest of
   that one line. A `void` line always stops skipping. So brace matching with "a
   `void` line closes every open block" reproduces the engine exactly; an extra `}` at
   procedure level only lowers a counter that is clamped at 0.
4. **`else`** runs its body only when the statement or block just before it was
   skipped. Comments reset that flag (see `engine_else_after_comment`).
5. **Conditions** are evaluated by `var_figure` (D:4905): one value, or exactly
   `a op b` split on spaces. Function comparisons such as `if (count_item("x") > 0)`
   go through a different branch (D:7171-7241) in which `<=`, `>=` and `!=` are all
   treated as `==`, and `>`/`<` compare against 0, and the rest of the line is
   dropped. The parser emulates that branch and records the effective comparison.
6. **Assignments** need spaces around the operator (`ev[2]` must be `=`, `+=`, `-=`,
   `*=`, `/=`, `*` or `/`); the right side is the first word only, or a single call.
7. **Labels** are lines whose first word ends in `:` with a short or empty second
   word. `goto x;` scans the whole file from the top for the first line starting with
   `x:` (prefix `x` if written without `;`), so labels are file-wide and gotos can
   jump into another procedure. A missing label runs off the end of the file and ends
   the script.
8. **Choice menus** (`talk_get`, D:5072) are read line by line after
   `choice_start()`: `set_y N`, `set_title_color N`, `title_start(); ... title_end();`
   (raw text lines), and option lines `(cond) (cond) "text"`. Every option line counts
   toward `&result`, including ones hidden by a false condition. A line in the menu
   that is not one of these aborts the menu.
9. **Names are case-insensitive** (`Playsound`, `Debug`). Built-ins win over local
   procedures of the same name; an unknown `name(...)` is tried as a local procedure
   and otherwise logged and ignored.

### Accepted grammar (informal)

```
script     := line*
line       := ws* ( comment | header | label | prefix* statement? ) trailing?
comment    := "//" any*
header     := "void" ws name ( "(" any* ")" )? ( "{" )?
label      := word ":" ( ws word<2 chars> )?
prefix     := "{" | "}" | "else" | "if" ws* "(" condition ")"
statement  := "int" ws var ( "=" rhs )? ";"?
            | var ws assign_op ws rhs ";"?            assign_op: = += -= *= /= * /
            | "return" rhs? ";"?
            | "goto" ws word ";"?
            | name "(" args? ")" ";"?                 choice_start() switches to menu mode
            | anything-else                           kept as an "unknown" node
menu       := ( "set_y" ws int | "set_title_color" ws int
              | "title_start" "(" ")" ";"? NL rawline* "title_end" ...
              | ( "(" condition ")" ws* )* '"' text '"' )* "choice_end" ...
args       := arg ( "," arg )*                        strings may contain , and )
expr       := C-like: int, &var, "string", name(args), unary - + !,
              * / + - == != < > <= >= && ||, parentheses
var        := "&" [A-Za-z0-9_] [A-Za-z0-9_-]*          note: '-' is legal (&s2-milder)
```

## Recovery rules (diagnostic codes)

Every recovery is recorded with `script`, `file`, `line`, `code`, `severity`
(`error` = malformed or behaves differently in the game, `warning`, `info`), `what`
and `recovery`. Nothing raises; unparseable text becomes an `unknown` or `raw` node.

| Code | Trigger | Recovery / engine behaviour |
|---|---|---|
| `unclosed_block` | `{` never closed before the next `void` or EOF | block closed there (engine stops skipping at `void` too) |
| `stray_close_brace` | `}` with nothing open in the procedure | ignored (engine clamps its level at 0) |
| `code_after_procedure_block` | statements after a procedure's closing `}` | kept in that procedure, which is where the engine runs them |
| `code_outside_procedure` | code before the first `void` | kept in `preamble`; never runs |
| `header_trailing`, `bad_header` | junk after / missing name in `void` line | ignored; procedure starts on the next line |
| `unknown_call` | `name(...)` that is not a built-in or local procedure (`freeeze`, `sp_prop`) | call node with `kind: unknown` and a `guess`; engine logs and skips |
| `unknown_statement` | text the engine cannot run (`reutrn;`, a stray `f`, song lyrics) | `unknown` node with `engine_executes: false` and a `guess` |
| `assign_no_spaces` | `&x=1` | `unknown` node with an assign `guess`; the engine does nothing |
| `malformed_as_label` | e.g. `wait(200:` (ends in `:`) | label node, a no-op, as in the engine |
| `missing_paren` | call without `)` | arguments recovered; if the command uses `get_parms` the engine does not run it (`engine_executes: false`) |
| `missing_comma` | `say("..." &x)` | split into two arguments; the engine does not need the comma |
| `string_quote` | `'text"` and other quote errors | string recovered; engine output is garbage, `engine_executes: false` |
| `arg_problem`, `expr_problem` | unparseable argument or expression text | leading valid expression kept |
| `bare_identifier_arg`, `say_sprite_zero` | `current_sprite` without `&` | `ident` node; engine reads 0. `say`/`say_stop` refuse sprite 0; `say_stop_npc` draws it at sprite 0 |
| `trailing_text` | text after a statement (`sp_target(...):`) | ignored, as the engine does |
| `if_no_paren`, `if_unclosed`, `if_no_body` | malformed `if` | best-effort condition / empty body |
| `engine_if_misparse` | `if (&a == 1) &b = 2;` on one line | AST keeps the intent; the engine treats it as a function comparison and drops the statement |
| `engine_if_rest_dropped` | statement after a function comparison on the same line | `engine_executes: false` |
| `engine_condition_differs` | the engine evaluates a different comparison (e.g. `get_version() > 108` is really `> 0`; `( &a == 1)` is always false) | `if.engine.effective` holds the real one |
| `engine_rhs_first_word` | `&x = &a + 1` | full expression kept; `engine_value` is what the engine assigns |
| `engine_div_assign` | `/=` with a call | noted (D:11292 quirk) |
| `nested_if_no_braces` | unbraced `if` whose body is another `if` with its body on a later line | parsed as C; the engine runs the inner body when the outer test is false |
| `engine_else_after_comment` | comment between an if body and `else` | `else_engine_never_runs: true` |
| `stray_else` | `else` with no `if` | `else_stray` node |
| `choice_bad_line`, `choice_empty`, `choice_empty_option`, `choice_option_quote`, `choice_unclosed`, `title_unclosed`, `choice_as_if_body` | menu problems | as described in the message |
| `goto_missing_label` | no line matches | `target: null`; the script ends |
| `goto_cross_procedure` (info) | label is in another procedure | resolved, `cross_procedure: true` |
| `goto_prefix_match` | the first matching line is not a plain label | resolved to it, as the engine does |
| `unused_label` (info) | label nobody jumps to | kept |
| `duplicate_procedure` | same name twice | the engine uses the first |
| `local_shadows_global` | `int &x` where `&x` is also a global | the script's uses count as the local in `facts.csv` |
| `undeclared_variable`, `used_before_declared`, `var_name_too_long` | variable problems | kept |
| `midtext_backtick`, `unknown_colour_code`, `say_too_long` | text problems | kept verbatim |
| `map_script_missing` | `map.dat` names a script with no `.c` | listed |
| `d_without_c`, `d_differs_from_c` | `.d` problems | listed; ASTs come from `.c` |
| `missing_script_reference`, `missing_external_procedure` | `external`/`spawn`/`sp_script`/`add_item` to a missing script/procedure | listed |

## AST schema (`out/ast/<script>.json`, `schema: dinkc-ast/1`)

```
{ "schema", "script", "file", "line_count",
  "preamble": [stmt],                  code before the first void (never runs)
  "procedures": [ { "name" (lower case), "name_written", "line", "end_line", "header",
                    "braced" (body was one {...} block, flattened), "body": [stmt] } ],
  "locals": [ {"name", "line", "procedure"} ],
  "diagnostics": [ ... ] }
```

Every statement has `type` and `line`. Optional on any statement: `engine_executes:
false` (the game never runs it), `leading: [comment|label]` (comments between an `if`
and its body).

| `type` | Fields |
|---|---|
| `call` | `name` (lower case), `name_written`, `args: [expr]`, `kind`: builtin / local / global_function / unknown, `guess` |
| `assign` | `target`, `op` (=, +=, -=, *=, /=), `op_written`, `value: expr` |
| `int` | `name`, `value: expr or null` |
| `return` | `value: expr or null` |
| `goto` | `label`, `exact_match` (written with `;`), `target: {line, procedure, is_label} or null`, `cross_procedure` |
| `label` | `name` |
| `if` | `cond: expr`, `cond_text`, `engine: {mode: simple / call_compare / call_bare / misparse / no_paren, effective, rest_dropped, always_false}`, `then: stmt`, `else: stmt or null`, `else_line`, `else_engine_never_runs` |
| `else_stray` | `body: stmt` |
| `block` | `body: [stmt]`, `end_line`, `closed` |
| `choice` | `set_y`, `title_color`, `title` (joined text), `title_lines`, `title_line`, `end_line`, `closed`, `aborted`, `options: [{index, line, text, conditions: [{text, expr, engine}]}]` |
| `comment` | `text` |
| `unknown` | `text`, `guess` |

Expressions: `int {value}`, `var {name}`, `string {value, unterminated?}`,
`call {name, args, kind}`, `binop {op, left, right}`, `unary {op, operand}`,
`ident {name}` (a bare word), `raw {text}`. Assignment values may carry
`engine_value`.

## Output tables (`out/`)

| File | Contents |
|---|---|
| `dialog_lines.csv` | `script, procedure, line, call` (say / say_stop / say_xy / say_stop_xy / say_stop_npc), `speaker` (sprite expression; empty for the `_xy` calls), `x, y` (for `_xy`), `colour_code` (characters after leading backticks), `colour` (palette index, 14 if none), `text` (colour prefix stripped), `vars` (`&vars` the engine substitutes, longest name first), `unknown_vars`, `engine_executes`, `raw_text` |
| `choices.json` | per menu: `script, procedure, line, end_line, set_y, title_color, title, aborted, uses_goto, notes`, and `options: [{index, line, text, conditions, hidden_unless, handled, branch: {if_line, statements: [{line, stmt}], gotos, local_calls}}]`, plus `else_branch`. Branches are the `if (&result == N)` blocks that follow the menu in the same statement list, following `else` chains |
| `facts.csv` | one row per global x script: `variable, declared_in, initial, engine_bound, script, procedures, reads, writes, read_lines, write_lines, compared_values` (literals compared in conditions, e.g. `==3;>=5`), `written_values` (e.g. `=2;+=1`; `init=` for make_global_int; `choice 1..N` for `&result`). Reads include conditions, arguments, right-hand sides, choice conditions and text interpolation |
| `globals.json` | every `make_global_int`: name -> [{script, line, procedure, initial}] |
| `script_kinds.csv` | `script, kind, tags, placed, placed_count, base_count, screens, called, called_by, engine_loaded, procedures, evidence` |
| `enemies.json` | scripts that are enemies/bosses or set `sp_hitpoints`: `stats` (every `sp_*` set on `&current_sprite` with value, procedure, line), `summary` (value set last in `main`, else last anywhere), `other_sprites` (stats set on created sprites), `drops` (`external` calls to `emake`/`make` or from `die`), `screenlock`, `sounds`, `behaviours`, `editor_stats` (non-zero per-placement values from `map.dat`) |
| `items.json` | weapons, magic, items and pickups: `given_by` (add_item/add_magic call sites), `icon_seq_frame`, and per procedure (`arm`, `disarm`, `use`, `pickup`, `touch`, ...) the effects: stat changes, `init()` sequence swaps, sounds, item removal |
| `shops.json` | scripts that do `&gold -= N`: `purchases: [{line, procedure, price, path, check (matching &gold comparison), grants, options (menu options whose branch reaches it)}]`, `gold_checks`, `gold_income` |
| `calls.csv` | every call (statement or nested): `name, kind, script, procedure, line, args, engine_executes` |
| `diagnostics.json` | `counts_by_code`, `count`, `diagnostics` (all per-script ones plus map/.d/reference checks) |
| `summary.json` | counts printed by the build |

### Script kinds

`kind` is the first matching tag in this order; `tags` lists all of them:
`system` (loaded by the engine by name, or started only by system scripts), `boss`
(enemy with 150+ hitpoints or "boss" in the name), `enemy` (brain 9/10 on itself, `en-`
prefix, or combat stats plus `die`), `weapon` (inventory script with `arm` that is not
consumed by `use`), `magic` (given by `add_magic`), `item` (consumable inventory
script), `projectile` (`dam-*`, missile `damage` scripts), `shop` (`&gold -=` with a
menu or `buy` procedure), `pickup` (`touch` that changes player stats or gives an
item), `container` (boxes, barrels, chests), `library` (`make`, `emake`, scripts only
reached through `external`), `sign`, `cutscene` (freezes Dink and runs `move_stop` or
4+ `say_stop` outside a `talk`), `npc` (`talk` with lines not spoken by Dink), `warp`
(changes screen), `object` (`talk` where only Dink speaks), `screen-base` (base script
of a screen), `empty`, `dead` (not placed live in `map.dat` and not called by any
script), `other`.

"Placed" means referenced by a live `map.dat` record: the record is used by a
`dink.dat` screen and, for sprites, the slot is active and of type 1 (types 0 and 2
are background and never load their script, D:6036-6146). "Called" means another
script names it in `external`, `spawn`, `sp_script`, `add_item`, `add_magic` or
`make_global_function`. `compare_weapon`, `count_item` and similar only reference it.

## Known limitations

- Variable scope is per script, not per procedure run: a name declared with `int`
  anywhere in the script counts as local everywhere in it. The engine creates locals
  at run time, so a use before the `int` executes can still hit a global.
- `choices.json` branches are found only in the statement list right after the menu.
  Menus that loop through labels (`escape.c`, the shops' `mainloop`) are flagged with
  `uses_goto` and notes rather than followed.
- Shop prices are literal `&gold -= N`; variable prices (`&amount`, `&bet`) are shown
  as the variable.
- Kind classification is heuristic; read `evidence` before relying on it.
- The `.d`-only script `s1-h1-1c` is reported but not parsed.
- A skipped `choice_start()` line (body of a false unbraced `if`) would make the engine
  run the option lines as statements; this does not occur in the base game, and the
  parser only flags it.
- The Proton font renderer (not in this repo) may treat a backtick in the middle of a
  line as a colour code; we only strip leading codes, as `say_text` does.
