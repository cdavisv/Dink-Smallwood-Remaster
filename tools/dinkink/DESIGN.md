# dinkink: how DinkC maps to Ink

Stage 5 of the remaster pipeline (`doc/remaster/REMASTER_PLAN.md` section 8). Input is the
`tools/dinkc` output (ASTs plus tables); output is one Ink file per narrative script, a
root file, and the tables a human reviewer and the Unreal implementer need. This file is
the contract between the converter, the reviewer and `DinkNarrative` in Unreal.

Two rules decide every case below:

1. **Nothing is lost.** Every statement of a converted procedure comes out as Ink logic,
   an Ink output line, a tunnel/divert, or (for engine no-ops) an Ink comment. Coverage
   counts in against out.
2. **The words are untouched, and the default is what the 1997 engine did.** Where the
   engine does something other than what the author wrote, the engine behaviour is the
   live branch and the author's intent sits next to it behind a `CONST fix_<script>_l<line> = false`
   switch, listed in `review_queue.csv`.

Unreal Engine and Inkpot are not available to the converter, so runtime behaviour in
Unreal is unverified. Only plain Ink features are used (knots, stitches, tunnels,
sticky choices with conditions, multi-line conditionals, global `VAR`/`CONST`,
`EXTERNAL` functions, static tags). Things Inkpot must provide are marked **[runtime]**.

## 1. Files and names

| DinkC | Ink |
|---|---|
| script `s3-chick.c` | file `ink/s3-chick.ink`, one knot `=== d_s3_chick ===` |
| all scripts | root `ink/dink.ink`: `INCLUDE`s `_decls.ink` (globals, pseudo-variables, externals and their fallbacks) and every script file |
| procedure `talk` | entry stitch `d_s3_chick.on_talk` and body stitch `d_s3_chick.p_talk` |
| label `mainloop:` that some `goto` targets | stitch `lbl_mainloop` (plus continuation stitches, section 6) |
| a `choice_start()` menu at line 25 | stitch `m25`, called as a tunnel |

**Identifier mapping** (`names.csv` holds every pair; the build fails on any collision and
a test checks the table is a bijection):

- script name -> knot: lower case, `-` -> `_`, prefix `d_` (`s3-chick` -> `d_s3_chick`,
  `1gold` -> `d_1gold`). Ink knots, stitches and `VAR`s share one namespace, and the
  game has a global `&s2-nad` next to a script `s2-nad.c` and a script `die.c` next to
  70 `die` procedures, so the prefix is needed.
- procedure -> entry stitch `on_<name>` (a bare `story` stitch would clash with
  `&story`), body stitch `p_<name>`.
- global `&name` -> `VAR name`: drop `&`, lower case (DinkC names are case-insensitive),
  `-` -> `_` (`&s2-nad` -> `s2_nad`). A name that is an Ink keyword (`&return`) gets the
  prefix `v_`. No global contains `__`, so locals cannot collide with globals.
- script-local `int &x` in `s3-chick` -> `VAR s3_chick__x` (double underscore).
- `CONST fix_<script>_l<line>` (for example `fix_s2_jack_l171`) -> the review-queue row whose `fix_const` column names it.

The fact store keys facts by the original name without `&` (`story`, `s2-nad`); the
table gives the Ink spelling for each.

## 2. Procedures and entering a script

DinkC runs a procedure from its `void` line to the next `void` line; local calls such as
`buybottle();` run another procedure and come back. That is an Ink tunnel, so:

```
=== d_s3_chick ===
= on_talk                   // entry point the game uses
-> p_talk -> DONE
= p_talk                    // body; every exit is ->-> (DinkC `return` too)
...
->->
```

**[runtime] Entering a script:** set `current_sprite` (the actor's sprite handle, see
section 5) and, for `external`/`spawn` targets, `arg1`..`arg9`; then
`ChoosePathString("d_s3_chick.on_talk")` and `Continue()` until `canContinue` is false and no
choices are pending. The engine-invoked procedures are `main` (when the sprite or screen
loads), `talk`, `hit`, `die`, `touch`, `push`, `attack`, `use`, `arm`, `disarm`,
`pickup`, `drop`, `click`, `buttonon`, `buttonoff`, `damage`, `duckdie`, `raise` and
`armmovie`; every procedure gets an entry stitch, so the list in `names.csv` is complete.

**[runtime] One flow per script instance.** In DinkC, starting a procedure on a script
instance abandons whatever that instance was doing (`run_script` relocates it), and
several instances run at once (an NPC's idle loop, a spawned cutscene, the player's
conversation). Run each instance in its own Ink flow (ink 1.1 `SwitchFlow`) or story
instance; `ChoosePathString` resets the call stack, which matches the engine. Some
procedures never end on purpose: `s2-healp` `main` is an idle-animation loop
(`lbl_mainloop` -> `wait 500` -> random frame -> `goto mainloop`), and `talk`/`hit`
jump back into it.

`kill_this_task()` is a director command followed by `-> DONE`. A `goto` to a missing
label makes the engine run off the end of the procedure, so it becomes `->->` (the
procedure ends and a caller resumes, as with `proc_return`; section 9).

## 3. Spoken lines

Every `say`, `say_stop`, `say_xy`, `say_stop_xy` and `say_stop_npc` becomes one Ink
output line: the text with the colour prefix removed, escaped, then static tags.

```
Hey, how's it going? #id:s3-chick.talk.001 #say:say_stop #spk:1 #col:14 #src:36
Oh hi, pretty good. #id:s3-chick.talk.002 #say:say_stop #spk:current_sprite #col:9 #src:38
```

| Tag | Meaning |
|---|---|
| `id:<script>.<procedure>.<nnn>` | stable line ID: nth spoken line of that procedure in source order (VO and localisation key; `line_ids.csv`) |
| `say:<call>` | `say`, `say_xy` do **not** block; `say_stop`, `say_stop_xy`, `say_stop_npc` block until the text is dismissed or times out |
| `spk:<ref>` | speaker sprite: an integer is a handle (1 = Dink, 0 = the engine's unused sprite 0); otherwise it is the name of an Ink variable holding the handle (`current_sprite`, `s1_bul__dude`) **[runtime: read it with the variable getter]**. Absent for `_xy` lines |
| `x:<n>`, `y:<n>` | for `_xy` lines: original screen pixels |
| `col:<n>` | colour index after the backtick code (14 if none). The remaster's subtitle colour table maps it |
| `src:<line>` | line in the original `.c` file |
| `handle:<var>` | `int &text = say_xy(...)`: store the text sprite's handle in that Ink variable **[runtime]** |
| `review:<script>:<line>` | the line has a review-queue row (wrong speaker, odd text) |

**Switched lines.** A tag cannot be switched, so a line whose speaker or text differs between
engine and author is written twice, `{ fix_<script>_l<line>: <intent line> - else: <engine
line> }`, with the same `#id` (only one branch runs; `line_ids.csv` and coverage count it
once). The engine line is the default. Today: `s2-man2.c:25` (bare word `current_sprite`
reads 0: `#spk:0` live, `#spk:current_sprite` behind the switch) and `s1-wand2.c:187` (a
stray backtick in `Chance `Zands`: verbatim live, without the backtick behind the switch).

**Variables in text.** The engine substitutes `&var` in the text, longest name first,
case-insensitively. The converter does the same with the `vars` column of
`dialog_lines.csv`, writing `{gold}`. Names the engine does not know stay literal.

**Escaping.** Characters Ink would interpret are escaped with `\` (`\ { } [ ] | #`, `<`
before `>`, `-` before `>`, `/` before `/` or `*`, a leading `- * + = ~ ( >`, and a
leading `INCLUDE`/`VAR`/`CONST`/`LIST`/`EXTERNAL`/`TODO`). The compiler removes the
backslash. The Ink runtime also collapses runs of spaces and trims each line, which
would change 306 lines (`"Megapotion!  All stats..."`). So every space the runtime would
remove (leading, trailing, and the 2nd+ space of a run) is written as U+00A0.
**[runtime] The one display transform `DinkNarrative` must apply is
`Text.Replace(U+00A0, ' ')`.** If it forgets, the line still renders as a space. The tests
compile the story, run every line through the real `inklecate -p` runtime, apply that
transform and compare with the original character for character.

## 4. Menus (`choice_start`)

A menu becomes a tunnel to its own stitch, so it can sit anywhere, inside conditionals
too, and the code after it stays a literal copy of the DinkC `if (&result == N)` chain:

```
-> m25 ->
{ result == 1:
    ...
}
= m25
>> choice_start 0 0 #cmd #src:25
+ [Say hi #opt:s3-chick.talk.c1.1]
    ~ result = 1
    ->->
+ {mayor == 0} [Tell her about the planned assault #opt:s3-chick.talk.c1.3]
    ~ result = 3
    ->->
```

- Options keep their order. `~ result = N` uses the **original** position, so hidden
  options still count, as in `talk_get`.
- Conditions `(c1) (c2) "text"` become `{c1} {c2}` (all must hold).
- Choices are sticky (`+`) because `goto mainloop` reopens menus.
- `title_start` lines are output lines tagged `#title #id:<script>.<proc>.t<menu>.<k>
  #col:<title_color>`. `choice_start` args are `set_y` and `title_color` (0 = default).
- Option text substitutes variables like spoken text. The engine fills `&savegameinfo`
  and `&buttoninfo` per option from the option's position, so those become
  `{savegameinfo(N)}` / `{buttoninfo(N)}`, which are external functions returning strings.
- If every option has a condition, a fallback choice `+ -> ` sets `result = 0` so Ink
  does not stall when none is visible (engine behaviour unverified; listed for review).
- The option text is shown on the button only (`[...]`), never printed afterwards, as
  in DinkC.

## 5. Variables, values and expressions

**Globals -> Ink `VAR`s, declared once in `dink.ink` with their `make_global_int`
initial values.** Not external functions, because:
conditions in choices and branches stay readable (`{story >= 3}`); the compiler checks
every name; Ink's own save state holds them; and external-function reads are subject to
Ink's look-ahead. **[runtime]** `UDinkFactSubsystem` is synchronised with the story:
on load, push every fact into its `VAR`; `ObserveVariable` on every fact `VAR` writes
changes back. Engine-bound stats (`&gold`, `&life`, `&exp`, `&strength`...) are owned
by the stats component: the narrative layer pushes their current values in before
entering a knot and applies writes (`~ gold = gold - 100`) through the observer.

**Script locals -> `VAR <script>__<name>`**, declared in the script file. DinkC locals
belong to one script *instance* and survive across that instance's procedures (`main`
sets, `talk` reads). Ink has no per-instance storage. **[runtime]** When a script is
attached to more than one actor, save and restore that script's local `VAR`s
(`names.csv`, `scope=local`) per actor around each entry. `int &x;` resets the
variable to 0 when it runs, as in the engine.

**Pseudo-variables**: `current_sprite`, `current_script`, `arg1`..`arg9` and
`v_return` (`&return`) are `VAR`s the runtime sets.

**Sprite handles** are plain ints: 1 is Dink, other values come from the runtime
(`current_sprite`, `create_sprite`, `sp(editor_num)`, `get_sprite_with_this_brain`).

**Expressions.** `&&`/`||`/`!` -> `and`/`or`/`not`. Integer `/` truncates in both.
`random(range, base)` -> EXTERNAL `random(range, base)` (since 6 Nov 2026; it was Ink
`RANDOM(base, base + range - 1)`, which uses Ink's own generator and fails for range 0).
**[runtime]** Answer `(rand() % range) + base`, and `base` when range is 0 (dink.cpp
`random`), from one seedable source in call order. The `_decls.ink` fallback does the same with
`RANDOM` for `inklecate -p`. A bare word such as
`current_sprite` without `&` reads 0 in the engine and is written `0`.

**Engine condition semantics.** In `if (func(...) op x)` the engine turns `!=`, `<=`,
`>=` into `==` and compares `>`/`<` against 0. The converter writes the condition the
engine evaluates (`get_version() > 0`), with the written one behind a fix switch.
A condition the engine never takes (`always_false`) becomes `false`.

**Queries -> `EXTERNAL` functions.** A built-in whose value is used (`sp_x(&s, -1)`,
`count_item("item-b1")`, `create_sprite(...)`, `sp(22)`, `compare_weapon(...)`,
`get_sprite_with_this_brain(...)`, `game_exist(n)`, `is_script_attached`, ...) is
called as an external with the same name and arguments. **[runtime]** Bind each with
`lookaheadSafe = false` so Ink never calls it before the preceding command lines have
run. `dink.ink` contains a fallback Ink function for each (returns 0 or ""), so the
story also runs in `inklecate -p`. `create_sprite` used as a value is the only external
with a side effect (it spawns, then returns the handle).

## 6. Control flow

| DinkC | Ink |
|---|---|
| `if (c) {...} else {...}` | `{ c:` ... `- else:` ... `}` multi-line conditional, nested as written |
| `return;` | `->->` |
| `goto x;` | `-> knot.lbl_x` (labels are file-wide, so cross-procedure gotos work) |
| local call `buybottle();` | `-> knot.p_buybottle ->` |
| statement after a procedure's closing `}` | stays in that procedure, as the engine runs it |

**Labels.** Only labels that a `goto` targets split the code. At procedure level, the
code after the label moves into stitch `lbl_x` and the code before ends with `-> lbl_x`.
A label inside a block (`s1-lg` `duck:` six blocks deep) needs the rest of each
enclosing level as well: the converter cuts the enclosing statement lists at the block
holding the label into continuation stitches `c<line>`, and every path (falling off the
end of the block, or arriving through the label) diverts there. No statement is
duplicated, so every line keeps one ID. Jumping into a `then` block skips its `else`, as
the engine does. The 38 `mainloop` gotos in shops are this pattern: the menu re-opens
because `lbl_mainloop` contains the `-> mNN ->` tunnel.

An unused label is kept as a comment.

**Engine instance semantics not modelled:** the engine runs a local procedure call in a
*new* instance of the script (fresh locals); in Ink, caller and callee share the
script's `VAR`s. The base game's local procedures (shop `buy*`, `s1-wand` `story`/`news`)
declare their own locals, so this does not change behaviour here.

## 7. Director commands

A statement-level built-in call becomes a **command line**: an output line starting with
`>>` and tagged `#cmd`, plus `#src:<line>`. Arguments are separated by spaces: integer
literals as written, strings in double quotes, anything else as an Ink interpolation, so
the director receives values:

```
>> move_stop {current_sprite} 6 660 1 #cmd #src:126
>> playsound 12 22050 0 0 0 #cmd #src:174
```

**[runtime]** The director recognises command lines **by the `cmd` tag** (never by the
text), runs them in order, and calls `Continue()` again only after a blocking command
has finished. A spoken line that happens to begin with `>>` has no `cmd` tag.

Command lines rather than Ink tags carry commands because tags on a line without text
attach to the *next* line (so order between consecutive commands would be lost), and
because static tags cannot carry run-time values such as `{s1_bul__dude}`. Command lines
need nothing from the runtime beyond text and tags.

The full vocabulary with argument lists, blocking flags and real frequencies is
generated into `out/director_vocabulary.csv`; every instance is in
`out/director_commands.csv`; `README.md` has the reference table. Highlights:

| Command | Args | Blocks |
|---|---|---|
| `wait` | ms | yes |
| `move` / `move_stop` | sprite, dir (numpad: 4 left, 6 right, 8 up, 2 down, 1/3/7/9 diagonal), stop coordinate (x for 4/6/1/3/7/9, y for 2/8), ignore-hardness | no / yes |
| `freeze` / `unfreeze` | sprite | no |
| `fade_down` / `fade_up` | - | yes |
| `playsound` | sound, speed Hz, random Hz, sprite (0 = global), repeat | no |
| `playmidi` / `stopmidi` | file | no |
| `create_sprite` | x, y, brain, seq, frame (as a statement; see section 5 for the value form) | no |
| `sp_<prop>` | sprite, value (-1 = read only, no change) | no |
| `screenlock` | 0/1 | no |
| `load_screen` / `draw_screen` / `draw_hard_map` | - | no |
| `add_item` / `add_magic` | script, seq, frame | no |
| `add_exp` | amount, sprite | no |
| `external` | script, procedure, args | yes (runs another script's procedure) |
| `spawn` | script | no (starts that script's `main` as a separate flow) |
| `kill_this_task` | - | ends the script |
| `wait_for_button` | - | yes |

**Argument lists follow the engine's `get_parms`** (dink.cpp 4116-4231). It zeroes its
number list, then stops as soon as it needs a `,` that is not there. So a call with too few
arguments runs with the rest 0 (`sp_active(&temp1hold);` in `dam-icee` is `sp_active
sprite 0`, which removes the sprite, and is written `>> sp_active {temp1hold} 0`), and a
string followed by no comma (`say_stop("..." &current_sprite);`, `s3-chick.c:42`) leaves
the speaker 0, which `say`/`say_stop` reject, so that line is never spoken (section 9). Too
many arguments make the engine skip the command; the converter refuses to build rather than
guess (none exist). `director_commands.csv` shows the engine's list.

**Engine no-ops become comments**, counted in coverage as handled: `debug()` (dev
log), `preload_seq()` and `load_sound()` (asset preloading), `make_global_int()`
(becomes the `VAR` declaration). Comments from the original are kept as Ink comments.

**Coordinates** stay in original screen pixels (playfield 0-640 x 0-400 plus the
engine's offsets). The screen is the context: the screens a script is placed on (or,
for scripts attached with `sp_script`/`spawn`, the screens of the script that attaches
them, shown as `586 (via s3-tc)`) are in the file header, `coverage.csv` and
`director_commands.csv`; at run time the director uses the
active screen volume's transform from the layout stage.

**`&gold` and other stat writes** are variable assignments, not commands (section 5).
`director_commands.csv` still lists them (form `var-write`) so the implementer sees them.

## 8. Which scripts become Ink

Every script with at least one executable statement is converted in full, whatever its
kind. Until 6 Nov 2026 enemy, weapon, magic, item, projectile, pickup, container and
library scripts were treated as stage-5 data: without spoken lines they were left out
(`data-only`), with lines only their speaking procedures were kept (`data+lines`). That
was wrong for a runtime: the engine runs those procedures (an enemy's `die` calls the
`emake` drop table, which `create_sprite`s a `heart` whose `touch` heals; a weapon's
`arm` sets the strength bonus; `newgame`, `dinfo`, `lraise` and `escape` are run by name),
so the Unreal smoke run found `external`, `sp_script` and `spawn` calls into scripts the
story did not contain. The stat blocks are still data: stage 5's tables read them from
the ASTs, which are unchanged.

| Status | Rule |
|---|---|
| `converted` | any kind except `dead`/`empty`, with an executable statement: every procedure |
| `converted-dead` | kind `dead` (not placed, not called) with an executable statement: converted in full and marked in its header; the plan keeps dead scripts out of the shipped game, but the draft keeps their words |
| `dead` / `empty` | no executable statement; also a `.d` with no `.c` that nothing references (`s1-h1-1c`: dead data, review category `dead-data`) |
| `missing` | referenced but absent from the original: map/sp_script references `s2-307s`, `s2-barp`, `s2-mh-s`, `box-e`, `big`; `ranstuff` (called only by dead `s1-slim`; the engine finds nothing and nothing drops) |

`main.c` is converted too: its `make_global_int` lines stay comments (the globals are the
`VAR`s in `_decls.ink`), the rest (`set_dink_speed`, `sp_frame_delay`) is live.
Test `test_every_call_target_is_in_the_story` checks that every `external`, `spawn`,
`sp_script`, `add_item` and `add_magic` target of a converted script is in the story.

## 9. Bugs in the original (no silent fixes)

Engine behaviour is live; the author's intent is behind `CONST fix_<script>_l<line> = false` in
the script's file, in the form `{ fix_<script>_l<line>: <intent> - else: <engine> }`, with a row in
`review_queue.csv` (id, priority, category, script, line, what the engine does, what the
author meant, how it was converted). A reviewer decides by flipping the constant (or
deleting the branch). Cases:

| Source problem | Engine (live) | Intent (behind the switch) |
|---|---|---|
| statement the engine never runs (`missing_paren`, `string_quote`: "Long live the ducks.", "I guess I just killed your husband.") | nothing | the line, with its ID |
| missing comma after a string (`s3-chick.c:42`): `get_parms` returns early with the speaker 0 (dink.cpp 4206-4225), `say_stop` rejects it (7908) | nothing; the line is never spoken | the line, with its ID |
| a `{` typed for a `}` (`s1-h3-8.c:13`): the engine nests the later tests inside the first, so two of three lines cannot run (curated in `overrides.py`) | the nesting, which hoisted behind the switch cannot run | the nested tests hoisted out and run |
| unknown call, a misspelt command (`freeeze`, `unfreeeze`) | nothing | the corrected command (`freeze`), the written spelling in a comment; the misspelling is not a vocabulary entry |
| unknown call, no known command (`sp_prop`) | nothing | the call as written (meaning undecided, `director_vocabulary.csv` row category `unknown-command`) |
| `reutrn;` | nothing, execution continues | `->->` |
| `wait(200:` read as a label | nothing | `>> wait 200` |
| `goto` to a missing label (`mainloop` in five shop procedures) | the procedure ends (`->->`) | none: no target exists, so no switch and no `fix_` constant; review row category `engine-matches-intent` |
| function comparison the engine reads differently | the engine's comparison | the written one |
| `else` after a comment | else never runs | the else body |
| undeclared variable | reads 0, writes are lost | a script-local `VAR` |
| say to the bare word `current_sprite` (`s2-man2.c:25`) | the line with `#spk:0` | the line with `#spk:current_sprite` (the whole line is switched; a tag cannot be) |
| stray backtick in the text (`s1-wand2.c:187`) | the text verbatim | the text without the backtick (whole line switched) |
| blocks the engine closes elsewhere (`unclosed_block`), stray `}` | as parsed (the parser models the engine) | review row only; a procedure's own `{` left open before the next `void` is low priority (nothing changes) |
| text that is not code (pasted lyrics in `spice.c`) | ignored | comment pointing at the original line; the text is not copied |

Spoken lines the 1997 engine never speaks (`s2-jack.c:171`, `s4-sign3.c:17`, `s3-chick.c:42`,
and `s1-h3-8.c:16`/`:20` through one row at line 13) have review category `never-spoken`, so
they can be listed together. With every switch false they stay silent, as in 1997
(`line_ids.csv` column `live` is 0 for them). Whether to ship them silent is the owner's
decision (OD2 in `doc/remaster/verbatim_review.md`).

## 10. Outputs

`ink/*.ink`, `json/dink.json` (compiled root), `names.csv`, `line_ids.csv`,
`director_commands.csv`, `director_vocabulary.csv`, `shot_lists/<script>.md`,
`review_queue.csv`, `coverage.csv`, `compile_report.txt`. Column lists are in `README.md`.

**Shot lists** are written for cutscene scripts and for every other script with a
procedure that moves sprites, fades, or freezes Dink and runs 4+ `say_stop`s. They are
the same statements in plain language, numbered, with conditions as nested headings.
