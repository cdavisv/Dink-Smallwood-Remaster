# Verbatim review of the DinkC-to-Ink review queue

Pre-review of `tools/dinkink/out/review_queue.csv` (66 items, 11 high) against the policy: the 1997 script ships fully verbatim (every reachable line, option and dark line as written, nothing softened, censored or annotated); only genuine bugs are fixed (typos, inverted conditions, wrong-speaker lines), each fix is logged against the original file and kept behind `CONST fix_<script>_l<line> = false`, so the engine's live behaviour is the default. Nothing was edited: this file is the only output. No content is softened anywhere below.

Limits: everything below comes from reading `dink.cpp` and the data and tracing the engine's rules by hand; nothing was run in a game. Where an entry infers rather than traces (sprite-0 bubble position, the `sp_prop` meaning, the font renderer), it says so.

Sources: originals `bin/dink/story/*.c`; converted Ink `tools/dinkink/out/ink/*.ink`; engine `source/dink/dink.cpp` (line numbers below are for the copy in this repository); maps from `tools/dinkex/out/screens/`. `.d` files were checked only where noted.

## Summary

| Class | Count | Meaning |
|---|---:|---|
| RESOLVED-CORRECT | 49 | Ink already matches the engine; no action |
| CONVERTER-BUG | 3 | The converter's output differs from the engine, or its fix branch is wrong; converter rule to fix |
| AUTHOR-INTENT-SWITCH | 12 | Engine and author intent differ; engine live, intent behind a switch (8 switches exist, 4 still to create) |
| OWNER-DECISION | 2 | A judgement call the policy does not settle |
| **Total** | **66** | |

By severity:

| Severity | RESOLVED-CORRECT | CONVERTER-BUG | AUTHOR-INTENT-SWITCH | OWNER-DECISION | Total |
|---|---:|---:|---:|---:|---:|
| high | 5 | 0 | 6 | 0 | 11 |
| medium | 9 | 2 | 3 | 2 | 16 |
| low | 35 | 1 | 3 | 0 | 39 |

Headlines:

- The one default-path converter bug is **R0044** (`s3-chick.c:42`): the engine never speaks that line (missing comma, `get_parms` returns early with speaker 0) but the Ink does, and `DESIGN.md` states the opposite. R0015/R0016 emit non-existent commands in their intent branch.
- Four behaviours need a switch that does not exist yet: `s1-h3-8` (a `{` typed for a `}` makes two of three bed lines unreachable), `s2-man2:25` (wrong speaker, currently only a tag), `s1-wand2:187` (stray backtick), plus R0044's line.
- Three lines of written dialogue are never spoken by the 1997 engine and stay silent in the default build: `s2-jack:171`, `s4-sign3:17`, `s3-chick:42` (OD2).
- 5 of the 17 declared `fix_` constants have nothing behind them (the `goto mainloop` rows) and should be removed.
- 12 queue rows are the dead `spice.c`; nothing there is reachable or copied.

## Engine facts used (dink.cpp)

- **One statement per line.** After a statement `process_line` hands back the remainder of the line only for `if`/`else`/`{`/`}`; everything else returns 0 and `run_script` reads the next line (`ugly_return` 7058; `run_script` 11460-11590); `int &x = ...` is the one exception that continues into the assignment (8694-8712). The text after a statement's `;` is ignored.
- **Procedures** run from the `locate`d `void` line until the next line whose first word is `void` (7131, 7323); `}` never ends one. `return` ends it and resumes `proc_return` (7434-7452). End of file does the same (end of `run_script`).
- **Labels are file-wide.** A line whose first word ends in `:` and has no second word is a label and does nothing (7146). `goto` rescans from offset 0 for a line starting with the label text (`locate_goto` 3769-3827); a miss logs and leaves the position at the end of the buffer. A first word like `wait(200:` is read as a label.
- **Conditions.** `if` runs `process_line` on the rest of the line and tests `g_returnint` (7454-7480). With a plain variable test (`(&a >= &b)`) `var_figure` handles `==`, `>`, `<`, `!=`, `<=`, `>=` correctly (4905-4975). With a function on the left (`(func() op x)`) the text after the first `)` goes through the `strchr(temp, '=')`-first chain (7171-7240): `==`, `!=`, `<=`, `>=` all act as `==`, and `>`/`<` compare the result with the operator token, i.e. with 0.
- **Blocks and skipping.** A false `if` sets `skipnext`; the next `{` records `onlevel = level - 1` and everything is skipped until a `}` brings the level back to `onlevel` (7289-7360); an unbalanced block therefore skips to the next `void` line.
- **Arguments.** `get_parms` (4116) reads a string between the first two `"`, a number up to the next `,` or `)`, demands a `,` between parameters and otherwise returns true early leaving the rest zero (4206-4225); text after the closing `)` is ignored except an optional `;`. Only values starting with `&` are looked up (`decipher`, 3829).
- **Unknown names.** No match and no `(`: logged `MERROR`, line ignored (11436). With `(`: tried as a local procedure, then the global function table, then logged and skipped (11375-11430). `external` with a missing script logs and continues (11346-11351).
- **Variables.** `int &x` makes a script-local (scope = script instance number, `make_int` 4647); `get_var` looks local first, then global (3920); locals die with the instance (`kill_script` 3377). An undeclared name reads as 0 in conditions and arguments and writes are lost (`var_equals` 4721).
- **Speech.** `say` and `say_stop` reject speaker 0 (7750, 7908); `say_stop_npc` does not (7934). `say_stop`/`say_stop_npc` suspend the script until the bubble expires. Only a colour code at the very start of the text is parsed (`text_draw` 11810).

Shared patterns referred to in the entries:

- **Stray `}`** (R0028, R0031, R0033, R0038, R0039, R0041, R0045, R0048, R0063-R0066). A `}` with no open block only decrements the level (dink.cpp:7303-7316); the level is clamped (`if (level < 0) level = 0`, 7318, and each statement line starts with `if (level < 1) level = 1`, 7103). It matters only if a block skip is pending and the level lands exactly on `onlevel` (7309). Every stray brace in the queue sits at the end of a procedure or file with no skip pending, so the converter's 'ignored' is faithful.
- **Code after a procedure's closing brace** (R0032, R0037, R0040, R0047). `}` does not end a procedure in the engine. `process_line` stops only at a line whose first word is `void` (7131, 7323) and `run_script` otherwise keeps reading lines (11460-11590), so statements after a procedure's closing brace run exactly like the ones above it, and the Ink keeps them in the procedure.
- **Missing script file** (R0012, R0013, R0018, R0019, R0022). `load_script` returns 0 and logs `Script ... not found` when neither `.d` nor `.c` exists (3526-3650). For a map sprite the caller stores that 0 as the sprite's script (6146); for a screen's base script the result is tested `if (ms > 0)` (6807). Nothing runs and nothing else happens.

## Entries

Format per entry: queue row, original line(s) quoted exactly (line numbers are the file's), what the engine does, the Ink as converted, class and action. `...` marks lines omitted from a quotation. Ink quotations are exact; where the converter wrote U+00A0 to keep doubled spaces (DESIGN.md section 3) it shows here as a plain space.

### R0001: s1-h3-8.c line 7, `talk` (high) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `unclosed_block` (structure): block opened here in procedure talk is never closed. Conversion note: closed at procedure header at line 24, which is where the engine stops skipping too
- **Original:**

```text
   6  void talk(void)
   7  {
   8   int &maybe;
   9   &maybe = random(3,1);
  10     if (&maybe == 1)
  11     {
  12     say("Libby's bed, ahh yeah.", 1);
  13     {
  14     if (&maybe == 2)
  15     {
  16     say("Libby's bed, to dream the impossible dream...", 1);
  17     }
  18     if (&maybe == 3)
  19     {
  20     say("Libby's bed, looks lonely.", 1);
  21     }
  22  }
```

- **Engine:** Root cause is line 13: a `{` where a `}` was meant (it sits at the same indentation as the `}` lines 17 and 21; swapping it balances the file: opens at 7, 11, 15, 19 against closes at 13, 17, 21, 22). Line 7 is `talk`'s own brace and line 11 the `if` block that never closes, so the queue's two rows are one defect. Engine trace (`{`/`}`/skip logic, dink.cpp:7289-7360): for `&maybe == 1` line 12 is said and the stray block is entered, and the two later `if` tests sit inside the `== 1` block, so they can never run. For `&maybe` 2 or 3 the `== 1` test fails, the skip that starts at line 11 never sees its closing `}` (the level never returns to `onlevel`), and it runs on to the next `void` line. Net effect in the 1997 engine: one interaction in three says line 12; two in three say nothing; lines 16 and 20 are unreachable. The Ink nests the same way, so the default behaviour already matches the engine.
- **Ink as converted:**

```text
= p_talk
// void talk(void) (lines 6-23)
~ s1_h3_8__maybe = 0
~ s1_h3_8__maybe = random(3, 1)
{ s1_h3_8__maybe == 1:
    Libby's bed, ahh yeah. #id:s1-h3-8.talk.001 #say:say #spk:1 #col:14 #src:12
    { s1_h3_8__maybe == 2:
        Libby's bed, to dream the impossible dream... #id:s1-h3-8.talk.002 #say:say #spk:1 #col:14 #src:16
    }
    { s1_h3_8__maybe == 3:
        Libby's bed, looks lonely. #id:s1-h3-8.talk.003 #say:say #spk:1 #col:14 #src:20
    }
}
->->
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: missing (`fix_s1_h3_8_l13`).
- **Action:** Create `CONST fix_s1_h3_8_l13 = false` (log: `s1-h3-8.c:13`, `{` should be `}`). In the Ink, hoist the two nested conditionals out to the level of the first one and gate them: `{ fix_s1_h3_8_l13 and s1_h3_8__maybe == 2: ... }` and the same for 3. With the switch false they cannot run, exactly as in the engine; with it true all three lines speak. Keep IDs `s1-h3-8.talk.002` and `.003`. Needs converter rule C4. One switch covers R0001 and R0002. Switch does not exist yet.

### R0002: s1-h3-8.c line 11, `talk` (high) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `unclosed_block` (structure): block opened here in procedure talk is never closed. Conversion note: closed at procedure header at line 24, which is where the engine stops skipping too
- **Original:**

```text
   6  void talk(void)
   7  {
   8   int &maybe;
   9   &maybe = random(3,1);
  10     if (&maybe == 1)
  11     {
  12     say("Libby's bed, ahh yeah.", 1);
  13     {
  14     if (&maybe == 2)
  15     {
  16     say("Libby's bed, to dream the impossible dream...", 1);
  17     }
  18     if (&maybe == 3)
  19     {
  20     say("Libby's bed, looks lonely.", 1);
  21     }
  22  }
```

- **Engine:** Same as R0001: a stray `{` on line 13 nests the `== 2` and `== 3` tests inside the `== 1` block, so only line 12 can be said, one time in three.
- **Ink as converted:**

```text
= p_talk
// void talk(void) (lines 6-23)
~ s1_h3_8__maybe = 0
~ s1_h3_8__maybe = random(3, 1)
{ s1_h3_8__maybe == 1:
    Libby's bed, ahh yeah. #id:s1-h3-8.talk.001 #say:say #spk:1 #col:14 #src:12
    { s1_h3_8__maybe == 2:
        Libby's bed, to dream the impossible dream... #id:s1-h3-8.talk.002 #say:say #spk:1 #col:14 #src:16
    }
    { s1_h3_8__maybe == 3:
        Libby's bed, looks lonely. #id:s1-h3-8.talk.003 #say:say #spk:1 #col:14 #src:20
    }
}
->->
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: missing (`fix_s1_h3_8_l13`).
- **Action:** Same defect and same switch as R0001; no separate action.

### R0003: s2-jack.c line 171, `die` (high) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `engine_never_runs` (engine-differs): the engine does not run this statement (source error); intent: run it. Conversion note: engine live (nothing); intent behind fix_s2_jack_l171 (switch `fix_s2_jack_l171`)
- **Original:**

```text
 169  say_stop("`#Dink!  What have you done!", &temp2hold);
 170  wait(500);
 171  say_stop('I guess I just killed your husband.", 1);
 172  wait(500);
 173  say_stop("`#Jack wasn't always like that.  He used to be.. <bursts into tears>", &temp2hold);
```

- **Engine:** `say_stop('I guess I just killed your husband.", 1);` has mismatched quotes. `get_parms` reads a string as the text between the first and second `"` (dink.cpp:4164); with only one `"` the "string" is `, 1);` and `h` jumps past it, the following comma test fails and `get_parms` returns true early (4206-4225) with `g_nlist` zeroed, so the speaker is sprite 0 and `say_stop` logs `Sprite 0 can talk?` and returns without a bubble (7908-7913). Nothing blocks: the `wait(500)` before and after the line run back to back. The 1997 player never saw this line.
- **Ink as converted:**

```text
= p_die
// void die(void) (lines 163-180)
>> script_attach 1000 #cmd #src:165
>> freeze 1 #cmd #src:166
>> freeze {temp2hold} #cmd #src:167
>> wait 500 #cmd #src:168
Dink!  What have you done! #id:s2-jack.die.001 #say:say_stop #spk:temp2hold #col:13 #src:169
>> wait 500 #cmd #src:170
{ fix_s2_jack_l171:
    I guess I just killed your husband. #id:s2-jack.die.002 #say:say_stop #spk:1 #col:14 #src:171
}
>> wait 500 #cmd #src:172
Jack wasn't always like that.  He used to be.. <bursts into tears> #id:s2-jack.die.003 #say:say_stop #spk:temp2hold #col:13 #src:173
>> wait 500 #cmd #src:174
I know.  It's ok, I'm here now. #id:s2-jack.die.004 #say:say_stop #spk:1 #col:14 #src:175
~ exp = exp + 100
~ s2_aunt = 4
>> unfreeze 1 #cmd #src:178
>> unfreeze {temp2hold} #cmd #src:179
->->
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None to the Ink. Switch exists (`fix_s2_jack_l171`) and the intent text correctly drops the stray leading `'` (log that typo too: the original is `'I guess ... husband."`). Default build stays silent here. This is one of three never-spoken lines, see Owner decision OD2.

### R0004: s2-man2.c line 25, `main` (high) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `say_sprite_zero` (wrong-speaker): speaker is the bare word `current_sprite`, which reads 0: the text goes to sprite 0; intent: speaker &current_sprite. Conversion note: engine live (#spk:0); intended speaker in tag spk_intent
- **Original:**

```text
  20  if (&temp4hold == 1)
  21    {
  22  &myrand = random(5, 1);
  23    if (&myrand == 1)
  24    {
  25    say_stop_npc("`0Fight!!!", current_sprite);
  26    }
  27     goto mainloop;
  28    }
```

- **Engine:** `current_sprite` without `&` is not a variable. `get_parms` only substitutes values that start with `&` (4150-4155), so `atol("current_sprite")` gives 0 and the text goes to sprite 0. Unlike `say`/`say_stop`, `say_stop_npc` has no sprite-0 guard (7934-7959): `say_text(.., 0, ..)` (4515) builds the bubble at the zeroed slot 0's position (x 0 - 75, y 0 - offset), so it is expected to be drawn off the top-left of the screen rather than over the old man (not verified on screen), and the script still waits for the bubble's timer. While a sprite-0 bubble exists `text_owned_by(0)` is true (4996-5009) and further bare-word calls return at once without waiting. In short: the shout "Fight!!!" is effectively never seen in the 1997 game. The Ink is faithful (`#spk:0`) but the intended speaker is carried only in a tag, and a tag cannot be switched.
- **Ink as converted:**

```text
{ temp4hold == 1:
    ~ s2_man2__myrand = random(5, 1)
    { s2_man2__myrand == 1:
        Fight!!! #id:s2-man2.main.001 #say:say_stop_npc #spk:0 #col:10 #src:25 #spk_intent:current_sprite #review:s2-man2:25
    }
    -> d_s2_man2.lbl_mainloop // goto mainloop
}
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: missing (`fix_s2_man2_l25`).
- **Action:** Add `CONST fix_s2_man2_l25 = false` and switch the line, not the tag: `{ fix_s2_man2_l25: <line> #spk:current_sprite - else: <line> #spk:0 }`, same `#id` in both branches (only one runs), keep `#review`. Drop `#spk_intent`. Converter rule C1. The only occurrence in the corpus (grep for a bare `current_sprite` finds nothing else). Switch does not exist yet.

### R0005: s4-h2p2.c line 43, `hit` (high) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `unknown_statement` (engine-differs): `reutrn;` is not a statement; the engine ignores it and carries on; intent: return. Conversion note: engine live; `->->` behind fix_s4_h2p2_l43 (switch `fix_s4_h2p2_l43`)
- **Original:**

```text
  38  void hit( void )
  39  {
  40   if (&story > 10)
  41   {
  42    say_stop("`2First feed us, then beat us, is that how it is with you?", &current_sprite);
  43    reutrn;
  44   }
  45   say_stop("`2Strange customs you have.", &current_sprite);
  46  }
```

- **Engine:** `reutrn;` has no `(`, so it falls through every command test to the final `MERROR ... unknown` log (11436) and `process_line` returns 0: ignored. `say_stop` has already suspended and resumed the script, so after the first line is dismissed the engine continues past the block's `}` into line 45 and says the second line as well. Default behaviour in 1997: with `&story > 10` the player gets both lines.
- **Ink as converted:**

```text
= p_hit
// void hit( void ) (lines 38-46)
{ story > 10:
    First feed us, then beat us, is that how it is with you? #id:s4-h2p2.hit.001 #say:say_stop #spk:current_sprite #col:2 #src:42
    { fix_s4_h2p2_l43:
        ->->
    }
}
Strange customs you have. #id:s4-h2p2.hit.002 #say:say_stop #spk:current_sprite #col:2 #src:45
->->
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None. Switch exists (`fix_s4_h2p2_l43`, wraps `->->` inside the `story > 10` block) and the default (false) keeps the engine's two lines. Log the typo `reutrn` -> `return`.

### R0006: s4-sign3.c line 17, `talk` (high) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `engine_never_runs` (engine-differs): the engine does not run this statement (source error); intent: run it. Conversion note: engine live (nothing); intent behind fix_s4_sign3_l17 (switch `fix_s4_sign3_l17`)
- **Original:**

```text
   5  void talk( void )
   6  {
   7  if (&story > 10)
   8    {
   9    say_stop("`%Super-Fry Chicken opening soon.", &current_sprite);
  10    return;
  11    }
  12  
  13   freeze(1);
  14   say_stop("`%Hear ye, hear ye ...", &current_sprite);
  15   say_stop("`%By order of our great ducks the monthly tax shall be doubled.", &current_sprite);
  16   say_stop("`%This also applies to food donations.", &current_sprite);
  17   say_stop("`%Long live the ducks.", &current_sprite;
  18   unfreeze(1);
  19  }
```

- **Engine:** Line 17 lacks its `)`: `say_stop("`%Long live the ducks.", &current_sprite;`. In `get_parms` the second parameter finds neither `,` nor `)` in the rest of the line, so `crap` keeps the previous text, `h` is advanced by that text's length past the end of the line (4141-4157), `g_nlist[1]` becomes `atol` of the text (0), and the closing-paren test fails (4171-4186). Either way the speaker is 0 and `say_stop` returns without speaking (7908-7913); the line never appears and nothing blocks. `unfreeze(1)` on line 18 still runs.
- **Ink as converted:**

```text
= p_talk
// void talk( void ) (lines 5-19)
{ story > 10:
    Super-Fry Chicken opening soon. #id:s4-sign3.talk.001 #say:say_stop #spk:current_sprite #col:15 #src:9
    ->->
}
>> freeze 1 #cmd #src:13
Hear ye, hear ye ... #id:s4-sign3.talk.002 #say:say_stop #spk:current_sprite #col:15 #src:14
By order of our great ducks the monthly tax shall be doubled. #id:s4-sign3.talk.003 #say:say_stop #spk:current_sprite #col:15 #src:15
This also applies to food donations. #id:s4-sign3.talk.004 #say:say_stop #spk:current_sprite #col:15 #src:16
{ fix_s4_sign3_l17:
    Long live the ducks. #id:s4-sign3.talk.005 #say:say_stop #spk:current_sprite #col:15 #src:17
}
>> unfreeze 1 #cmd #src:18
->->
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None. Switch exists (`fix_s4_sign3_l17`); default false matches the engine. Log typo: missing `)`. Second never-spoken line, OD2.

### R0007: s4-st1p.c line 166, `sell` (high) - RESOLVED-CORRECT

- **Queue flagged:** `goto_missing_label` (engine-differs): no line starts with `mainloop:`; the engine runs off the end and the script stops; intent: probably jump back to `mainloop` (no such label exists). Conversion note: engine live (`-> DONE`); no target to put behind the switch (switch `fix_s4_st1p_l166`)
- **Original:**

```text
 165     unfreeze(1);
 166     goto mainloop;
 167     return;
```

- **Engine:** `goto mainloop;` calls `locate_goto` (dink.cpp:3769), which rescans the whole file from offset 0 for a line starting `mainloop:` (prefix match, 3809). There is none in this file, so it logs `Cannot goto` (3824) and leaves the read position at the end of the buffer; the `goto` handler returns 0 (8655-8660) and `run_script` has nothing left to read, so the procedure ends (a caller procedure, if any, would resume: `proc_return`, end of `run_script`). The `return;` after it is never read. These five `goto mainloop` lines are the only ones in the corpus without a `mainloop:` (the other six scripts keep it in `main`). The engine outcome is simply the end of the conversation after `unfreeze(1)`, which is also what the shop does when it works; there is no idle loop to jump to, so the 'intent' has no target. Ink `-> DONE` is the same observable behaviour.
- **Ink as converted:**

```text
>> unfreeze 1 #cmd #src:165
// goto mainloop: label missing (review fix_s4_st1p_l166; the engine ends the script)
-> DONE
->->
```

- **Class:** RESOLVED-CORRECT. Switch: declared but empty.
- **Action:** None to the Ink. The `CONST fix_..._l<N>` that the converter declares has nothing behind it (flipping it changes nothing): remove the constant and clear the `fix_const` column (rule C6).

### R0008: s4-st3p.c line 74, `buy` (high) - RESOLVED-CORRECT

- **Queue flagged:** `goto_missing_label` (engine-differs): no line starts with `mainloop:`; the engine runs off the end and the script stops; intent: probably jump back to `mainloop` (no such label exists). Conversion note: engine live (`-> DONE`); no target to put behind the switch (switch `fix_s4_st3p_l74`)
- **Original:**

```text
  73             unfreeze(1);
  74             goto mainloop;
  75             return;
```

- **Engine:** Same as R0007: `goto mainloop` finds no label, the procedure ends after `unfreeze(1)`, and Ink `-> DONE` is the same observable behaviour. Here inside `buy` after the purchase menu.
- **Ink as converted:**

```text
    -> d_s4_st3p.p_buys1 -> // buys1()
    >> unfreeze 1 #cmd #src:73
    // goto mainloop: label missing (review fix_s4_st3p_l74; the engine ends the script)
    -> DONE
    ->->
```

- **Class:** RESOLVED-CORRECT. Switch: declared but empty.
- **Action:** None to the Ink. The `CONST fix_..._l<N>` that the converter declares has nothing behind it (flipping it changes nothing): remove the constant and clear the `fix_const` column (rule C6).

### R0009: s4-st3p.c line 82, `buy` (high) - RESOLVED-CORRECT

- **Queue flagged:** `goto_missing_label` (engine-differs): no line starts with `mainloop:`; the engine runs off the end and the script stops; intent: probably jump back to `mainloop` (no such label exists). Conversion note: engine live (`-> DONE`); no target to put behind the switch (switch `fix_s4_st3p_l82`)
- **Original:**

```text
  81             unfreeze(1);
  82             goto mainloop;
  83             return;
```

- **Engine:** Same as R0007: `goto mainloop` finds no label, the procedure ends after `unfreeze(1)`, and Ink `-> DONE` is the same observable behaviour. Here inside `buy` after the purchase menu.
- **Ink as converted:**

```text
    -> d_s4_st3p.p_buybomb -> // buybomb()
    >> unfreeze 1 #cmd #src:81
    // goto mainloop: label missing (review fix_s4_st3p_l82; the engine ends the script)
    -> DONE
    ->->
```

- **Class:** RESOLVED-CORRECT. Switch: declared but empty.
- **Action:** None to the Ink. The `CONST fix_..._l<N>` that the converter declares has nothing behind it (flipping it changes nothing): remove the constant and clear the `fix_const` column (rule C6).

### R0010: s4-st3p.c line 91, `buy` (high) - RESOLVED-CORRECT

- **Queue flagged:** `goto_missing_label` (engine-differs): no line starts with `mainloop:`; the engine runs off the end and the script stops; intent: probably jump back to `mainloop` (no such label exists). Conversion note: engine live (`-> DONE`); no target to put behind the switch (switch `fix_s4_st3p_l91`)
- **Original:**

```text
  90             unfreeze(1);
  91             goto mainloop;
  92             return;
```

- **Engine:** Same as R0007: `goto mainloop` finds no label, the procedure ends after `unfreeze(1)`, and Ink `-> DONE` is the same observable behaviour. Here inside `buy` after the purchase menu.
- **Ink as converted:**

```text
    -> d_s4_st3p.p_buysw2 -> // buysw2()
    >> unfreeze 1 #cmd #src:90
    // goto mainloop: label missing (review fix_s4_st3p_l91; the engine ends the script)
    -> DONE
    ->->
```

- **Class:** RESOLVED-CORRECT. Switch: declared but empty.
- **Action:** None to the Ink. The `CONST fix_..._l<N>` that the converter declares has nothing behind it (flipping it changes nothing): remove the constant and clear the `fix_const` column (rule C6).

### R0011: s4-st3p.c line 98, `buy` (high) - RESOLVED-CORRECT

- **Queue flagged:** `goto_missing_label` (engine-differs): no line starts with `mainloop:`; the engine runs off the end and the script stops; intent: probably jump back to `mainloop` (no such label exists). Conversion note: engine live (`-> DONE`); no target to put behind the switch (switch `fix_s4_st3p_l98`)
- **Original:**

```text
  97     unfreeze(1);
  98     goto mainloop;
  99     return;
```

- **Engine:** Same as R0007: `goto mainloop` finds no label, the procedure ends after `unfreeze(1)`, and Ink `-> DONE` is the same observable behaviour. Here inside `buy` after the purchase menu.
- **Ink as converted:**

```text
>> unfreeze 1 #cmd #src:97
// goto mainloop: label missing (review fix_s4_st3p_l98; the engine ends the script)
-> DONE
->->
```

- **Class:** RESOLVED-CORRECT. Switch: declared but empty.
- **Action:** None to the Ink. The `CONST fix_..._l<N>` that the converter declares has nothing behind it (flipping it changes nothing): remove the constant and clear the `fix_const` column (rule C6).

### R0012: big.c (medium) - RESOLVED-CORRECT

- **Queue flagged:** `map_script_missing` (missing-script): map.dat references script 'big' (1 live reference(s): sprite rec 101 sprite 2 screens [149]) but there is no .c file. Conversion note: listed only; the engine logs 'Script not found' and the sprite has no script
- **Original:** Not a script; placement S149_P02 in `tools/dinkex/out/screens/SCR_149.json` has `'script': 'big'`
- **Engine:** `load_script` returns 0 and logs `Script ... not found` when neither `.d` nor `.c` exists (3526-3650). For a map sprite the caller stores that 0 as the sprite's script (6146); for a screen's base script the result is tested `if (ms > 0)` (6807). Nothing runs and nothing else happens. The sprite is S149_P02 (seq 32 frame 4, 249x300 px, brain 0): a static placement.
- **Ink as converted:**

```text
(no Ink file or knot; `coverage.csv` lists `big` as `missing`)
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. Nothing exists to convert and nothing may be invented. Runtime: a placement or base script naming a missing script must be a silent no-op, not an error.

### R0013: box-e.c (medium) - RESOLVED-CORRECT

- **Queue flagged:** `map_script_missing` (missing-script): map.dat references script 'box-e' (2 live reference(s): sprite rec 43 sprite 23 screens [66], sprite rec 43 sprite 24 screens [66]) but there is no .c file. Conversion note: listed only; the engine logs 'Script not found' and the sprite has no script
- **Original:** Not a script; placements S066_P23 and S066_P24 in `SCR_066.json` have `'script': 'box-e'`
- **Engine:** Same as R0012: no such file exists, so `load_script` returns 0 and nothing runs. The sprites are S066_P23 and S066_P24 (seq 158 frames 2 and 3, brain 0): static placements. The breakable boxes use `box1-e`/`box2-e` and seq 443/444, which these are not.
- **Ink as converted:**

```text
(no Ink file or knot; `coverage.csv` lists `box-e` as `missing`)
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. Nothing exists to convert and nothing may be invented. Runtime: a placement or base script naming a missing script must be a silent no-op, not an error.

### R0014: s1-boat.c line 3, `main` (medium) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `undeclared_variable` (engine-differs): &boat is never declared: the engine reads 0 and loses writes; intent: a variable that keeps its value. Conversion note: engine live; every use has the intent behind fix_s1_boat_l3 (switch `fix_s1_boat_l3`)
- **Original:**

```text
   1  void main( void )
   2  {
   3   if(&boat == 1)
   4   {
   5    sp_active(&current_sprite, 0);
   6    return;
   7   }
   8   &boat = 1;
   9   playsound(35, 22050, 0, 0, 0);
  10   sp_speed(&current_sprite, 1);
  11   move_stop(&current_sprite, 3, 750, 1);
  12   sp_active(&current_sprite, 0);
  13  }
```

- **Engine:** `&boat` is never declared. A read in a condition goes through `var_figure` (4905): `decipher_string` leaves the unknown name as text and `atol("&boat")` is 0, so `&boat == 1` is false. The write `&boat = 1` hits `var_equals`'s unknown-variable exit and is lost (4721). So in 1997 the boat sails every time. No existing global is a substring of `boat`, so `var_replace` (3995) cannot rewrite it. The script is dead (not in map.dat, dink.dat or any script), so the plan keeps it out of the shipped game.
- **Ink as converted:**

```text
VAR s1_boat__boat = 0 // undeclared in the original (see review)
CONST fix_s1_boat_l3 = false // review: undeclared variable &boat
...
= p_main
// void main( void ) (lines 1-13)
{ (fix_s1_boat_l3 and (s1_boat__boat == 1)) or (not fix_s1_boat_l3 and (0 == 1)):
    >> sp_active {current_sprite} 0 #cmd #src:5
    ->->
}
// (else-branch of `fix_s1_boat_l3`:) (engine: write to undeclared &boat is lost)
{ fix_s1_boat_l3:
    ~ s1_boat__boat = 1
}
>> playsound 35 22050 0 0 0 #cmd #src:9
>> sp_speed {current_sprite} 1 #cmd #src:10
>> move_stop {current_sprite} 3 750 1 #cmd #src:11
>> sp_active {current_sprite} 0 #cmd #src:12
->->
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None. Switch exists (`fix_s1_boat_l3`) and the Ink is correct on both sides. Dead script: low value.

### R0015: s1-h3-3.c line 8, `talk` (medium) - CONVERTER-BUG

- **Queue flagged:** `unknown_call` (engine-differs): freeeze() is not an engine command; the engine logs and skips it; intent: freeze. Conversion note: engine live (nothing); written call behind fix_s1_h3_3_l8 (switch `fix_s1_h3_3_l8`)
- **Original:**

```text
   6  void talk(void)
   7  {
   8   freeeze(1);
   9   say("Mr.SmileStein's bed, I shudder at what happens here.", 1);
  10   unfreeeze(1);
  11  }
```

- **Engine:** `freeeze(1);` is not a command. The first word is cut at `(` and compared (case-insensitively, full length, `compare` at 412) against every command; none matches. A line containing `(` is then tried as a local procedure call: the script is loaded again, `locate` finds no `void freeeze`, the function table has no entry, the engine logs `Procedure void freeeze not found` and kills the helper instance (11375-11430), and the line ends. Result: in 1997 Dink is not frozen during the bed's one-liner. The Ink default is correct. The intent branch is not: it emits `>> freeeze 1`, a command that does not exist, and `director_vocabulary.csv` now lists `freeeze` and `unfreeeze` as director commands (category `other`).
- **Ink as converted:**

```text
= p_talk
// void talk(void) (lines 6-12)
{ fix_s1_h3_3_l8:
    >> freeeze 1 #cmd #src:8
}
Mr.SmileStein's bed, I shudder at what happens here. #id:s1-h3-3.talk.001 #say:say #spk:1 #col:14 #src:9
{ fix_s1_h3_3_l10:
    >> unfreeeze 1 #cmd #src:10
}
->->
...
CONST fix_s1_h3_3_l8 = false // review: unknown command freeeze()
```

- **Class:** CONVERTER-BUG. Switch: exists.
- **Action:** Converter rule C2: in the intent branch emit the corrected command (`>> freeze 1 #cmd #src:8`), keep the original spelling in a comment, and keep misspellings out of `director_vocabulary.csv` and `director_commands.csv`. Switch exists (`fix_s1_h3_3_l8`); log typo `freeeze` -> `freeze`.

### R0016: s1-h3-3.c line 10, `talk` (medium) - CONVERTER-BUG

- **Queue flagged:** `unknown_call` (engine-differs): unfreeeze() is not an engine command; the engine logs and skips it; intent: unfreeze. Conversion note: engine live (nothing); written call behind fix_s1_h3_3_l10 (switch `fix_s1_h3_3_l10`)
- **Original:**

```text
   6  void talk(void)
   7  {
   8   freeeze(1);
   9   say("Mr.SmileStein's bed, I shudder at what happens here.", 1);
  10   unfreeeze(1);
  11  }
```

- **Engine:** `unfreeeze(1);` is not a command. The first word is cut at `(` and compared (case-insensitively, full length, `compare` at 412) against every command; none matches. A line containing `(` is then tried as a local procedure call: the script is loaded again, `locate` finds no `void unfreeeze`, the function table has no entry, the engine logs `Procedure void unfreeeze not found` and kills the helper instance (11375-11430), and the line ends. Result: nothing is unfrozen, which is harmless because `freeeze` never froze anyone. The Ink default is correct. The intent branch is not: it emits `>> unfreeeze 1`, a command that does not exist, and `director_vocabulary.csv` now lists `freeeze` and `unfreeeze` as director commands (category `other`).
- **Ink as converted:**

```text
= p_talk
// void talk(void) (lines 6-12)
{ fix_s1_h3_3_l8:
    >> freeeze 1 #cmd #src:8
}
Mr.SmileStein's bed, I shudder at what happens here. #id:s1-h3-3.talk.001 #say:say #spk:1 #col:14 #src:9
{ fix_s1_h3_3_l10:
    >> unfreeeze 1 #cmd #src:10
}
->->
...
CONST fix_s1_h3_3_l10 = false // review: unknown command unfreeeze()
```

- **Class:** CONVERTER-BUG. Switch: exists.
- **Action:** Same as R0015: intent branch must be `>> unfreeze 1`. Switch exists (`fix_s1_h3_3_l10`); log typo `unfreeeze` -> `unfreeze`.

### R0017: s1-slim.c line 40 (medium) - RESOLVED-CORRECT

- **Queue flagged:** `missing_script_reference` (missing-script): external refers to script 'ranstuff' which has no .c file. Conversion note: edge kept; the engine logs 'Script not found'
- **Original:**

```text
  34  void die( void )
  35  {
  36  playsound(29, 17050,0,0, 0);
  37    
  38    &save_x = sp_x(&current_sprite, -1);
  39    &save_y = sp_y(&current_sprite, -1);
  40    external("ranstuff", "small");
  41  
  42    int &hold = sp_editor_num(&current_sprite);
  43    if (&hold != 0)
  44    editor_type(&hold, 6); 
  45  }
```

- **Engine:** `external("ranstuff", "small")`: `load_script` fails, the engine logs `Couldn't find ranstuff.c` and the handler returns 0 (dink.cpp:11346-11351), so execution continues with the next line and does not block. `s1-slim` is dead (no placement or caller), so none of this runs in the shipped game.
- **Ink as converted:**

```text
>> playsound 29 17050 0 0 0 #cmd #src:36
~ save_x = sp_x(current_sprite, -1)
~ save_y = sp_y(current_sprite, -1)
>> external "ranstuff" "small" #cmd #src:40
~ s1_slim__hold = sp_editor_num(current_sprite)
{ s1_slim__hold != 0:
    >> editor_type {s1_slim__hold} 6 #cmd #src:44
}
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. Runtime note: an `external` whose target script does not exist must not block (the engine does not). No instance is reachable.

### R0018: s2-307s.c (medium) - RESOLVED-CORRECT

- **Queue flagged:** `map_script_missing` (missing-script): map.dat references script 's2-307s' (1 live reference(s): base rec 222 screens [307]) but there is no .c file. Conversion note: listed only; the engine logs 'Script not found' and the sprite has no script
- **Original:** Not a script; `SCR_307.json` has `base_script: 's2-307s'`
- **Engine:** Same as R0012: no such file exists, so `load_script` returns 0 and nothing runs. It is the base script of SCR_307, so that screen simply has no screen script.
- **Ink as converted:**

```text
(no Ink file or knot; `coverage.csv` lists `s2-307s` as `missing`)
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. Nothing exists to convert and nothing may be invented. Runtime: a placement or base script naming a missing script must be a silent no-op, not an error.

### R0019: s2-barp.c (medium) - RESOLVED-CORRECT

- **Queue flagged:** `map_script_missing` (missing-script): map.dat references script 's2-barp' (1 live reference(s): base rec 23 screens [34]) but there is no .c file. Conversion note: listed only; the engine logs 'Script not found' and the sprite has no script
- **Original:** Not a script; `SCR_034.json` has `base_script: 's2-barp'`
- **Engine:** Same as R0012: no such file exists, so `load_script` returns 0 and nothing runs. It is the base script of SCR_034 (an indoor screen), so that screen has no screen script.
- **Ink as converted:**

```text
(no Ink file or knot; `coverage.csv` lists `s2-barp` as `missing`)
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. Nothing exists to convert and nothing may be invented. Runtime: a placement or base script naming a missing script must be a silent no-op, not an error.

### R0020: s2-cave.c line 117, `main` (medium) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `malformed_as_label` (engine-differs): `wait(200:` ends in ':' so the engine treats it as a label (no-op); intent: wait(200). Conversion note: engine live; intent behind fix_s2_cave_l117 (switch `fix_s2_cave_l117`)
- **Original:**

```text
 115    move_stop(1, 6, 130, 1);
 116    say_stop("There's some old man in town who knows some magic.", 1);
 117     wait(200:
 118    say_stop("He might have a spell that could help us.", 1);
 119    wait(500);
```

- **Engine:** `   wait(200:` is split on spaces; its first word ends in `:` and there is no second word, so `process_line` takes it for a label and returns (7146-7149). Nothing waits. Default in 1997: no 200 ms pause between the two lines of the speech.
- **Ink as converted:**

```text
    >> move_stop 1 6 130 1 #cmd #src:115
    There's some old man in town who knows some magic. #id:s2-cave.main.027 #say:say_stop #spk:1 #col:14 #src:116
    { fix_s2_cave_l117:
        >> wait 200 #cmd #src:117
    }
    He might have a spell that could help us. #id:s2-cave.main.028 #say:say_stop #spk:1 #col:14 #src:118
    >> wait 500 #cmd #src:119
    >> sp_dir {s2_cave__dude} 2 #cmd #src:120
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None. Switch exists (`fix_s2_cave_l117`) and the intent (`>> wait 200`) is right. Log typo: missing `)`.

### R0021: s2-crock.c line 5, `main` (medium) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `undeclared_variable` (engine-differs): &mcrap is never declared: the engine reads 0 and loses writes; intent: a variable that keeps its value. Conversion note: engine live; every use has the intent behind fix_s2_crock_l5 (switch `fix_s2_crock_l5`)
- **Original:**

```text
   1  void main( void )
   2  {
   3  if (&caveguy > 4)
   4   {
   5  &mcrap = sp(22);
   6  sp_hard(&mcrap, 1);
   7  draw_hard_sprite(&mcrap);
   8  sp_active(&mcrap, 0);
   9  
  10  
  11    return;
  12   }
  13   }
  14   
```

- **Engine:** `&mcrap` is never declared, so `&mcrap = sp(22);` exits in `var_equals` before `sp(22)` is even evaluated (4721) and every later `&mcrap` argument reads as `atol("&mcrap")` = 0: `sp_hard`, `draw_hard_sprite` and `sp_active` all act on sprite 0 (`IsBadSpriteIndex(0)` is false, 7047). The Ink writes those commands with literal `0` and the intent with the variable. Dead script (not placed or called), so it does not ship.
- **Ink as converted:**

```text
= p_main
// void main( void ) (lines 1-14)
{ caveguy > 4:
    // (else-branch of `fix_s2_crock_l5`:) (engine: write to undeclared &mcrap is lost)
    { fix_s2_crock_l5:
        ~ s2_crock__mcrap = sp(22)
    }
    { fix_s2_crock_l5:
        >> sp_hard {s2_crock__mcrap} 1 #cmd #src:6
    - else:
        >> sp_hard 0 1 #cmd #src:6
    }
    { fix_s2_crock_l5:
        >> draw_hard_sprite {s2_crock__mcrap} #cmd #src:7
    - else:
        >> draw_hard_sprite 0 #cmd #src:7
    }
    { fix_s2_crock_l5:
        >> sp_active {s2_crock__mcrap} 0 #cmd #src:8
    - else:
        >> sp_active 0 0 #cmd #src:8
    }
    ->->
}
->->
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None. Switch exists (`fix_s2_crock_l5`); both branches correct.

### R0022: s2-mh-s.c (medium) - RESOLVED-CORRECT

- **Queue flagged:** `map_script_missing` (missing-script): map.dat references script 's2-mh-s' (1 live reference(s): base rec 427 screens [530]) but there is no .c file. Conversion note: listed only; the engine logs 'Script not found' and the sprite has no script
- **Original:** Not a script; `SCR_530.json` has `base_script: 's2-mh-s'`
- **Engine:** Same as R0012: no such file exists, so `load_script` returns 0 and nothing runs. It is the base script of SCR_530, so that screen has no screen script.
- **Ink as converted:**

```text
(no Ink file or knot; `coverage.csv` lists `s2-mh-s` as `missing`)
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. Nothing exists to convert and nothing may be invented. Runtime: a placement or base script naming a missing script must be a silent no-op, not an error.

### R0023: s3-dorks.c line 35, `die` (medium) - RESOLVED-CORRECT

- **Queue flagged:** `unclosed_block` (structure): block opened here in procedure die is never closed. Conversion note: closed at procedure header at line 47, which is where the engine stops skipping too
- **Original:**

```text
  34  void die( void )
  35  {
  36  if (get_sprite_with_this_brain(9, &current_sprite) == 0)
  37   {
  38    //no more brain 9 monsters here, lets unlock the screen
  39    screenlock(0);
  40    playsound(43, 22050,0,0,0);
  41   }
  42  
  43  &save_x = sp_x(&current_sprite, -1);
  44  &save_y = sp_y(&current_sprite, -1);
  45  external("emake","large");
  46  
  47  void attack( void )
```

- **Engine:** The unclosed block is the procedure's own `{`: the `}` is missing before the next `void` line. The engine ends a procedure at the next `void` line anyway (dink.cpp:7131, 7323), so every statement of `die` runs and nothing else changes. The Ink ends `die` at the same place. Note the file ends with a stray `}` after `attack` (R0045).
- **Ink as converted:**

```text
= p_die
// void die( void ) (lines 34-46)
{ get_sprite_with_this_brain(9, current_sprite) == 0:
    //no more brain 9 monsters here, lets unlock the screen
    >> screenlock 0 #cmd #src:39
    >> playsound 43 22050 0 0 0 #cmd #src:40
}
~ save_x = sp_x(current_sprite, -1)
~ save_y = sp_y(current_sprite, -1)
>> external "emake" "large" #cmd #src:45
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. No behavioural difference, so no switch needed.

### R0024: s3-gh.c line 57, `die` (medium) - RESOLVED-CORRECT

- **Queue flagged:** `unclosed_block` (structure): block opened here in procedure die is never closed. Conversion note: closed at procedure header at line 76, which is where the engine stops skipping too
- **Original:**

```text
  56  void die( void )
  57  {
  58    int &hold = sp_editor_num(&current_sprite);
  59    if (&hold != 0)
  60    editor_type(&hold, 6); 
  61  
  62  if (&gobpass == 1)
  63  {
  64  if (get_sprite_with_this_brain(9, &current_sprite) == 0)
  65   {
  66   if (get_sprite_with_this_brain(16, &current_sprite) == 0)
  67    {
  68  
  69    //no more brain 9 or 16 monsters here, lets introduce 'mog'
  70    spawn("s3-mog");
  71   }
  72  
  73   }
  74  
  75  }
  76  void attack( void )
```

- **Engine:** The unclosed block is the procedure's own `{`: the `}` is missing before the next `void` line. The engine ends a procedure at the next `void` line anyway (dink.cpp:7131, 7323), so every statement of `die` runs and nothing else changes. The Ink ends `die` at the same place.
- **Ink as converted:**

```text
= p_die
// void die( void ) (lines 56-75)
~ s3_gh__hold = sp_editor_num(current_sprite)
{ s3_gh__hold != 0:
    >> editor_type {s3_gh__hold} 6 #cmd #src:60
}
{ gobpass == 1:
    { get_sprite_with_this_brain(9, current_sprite) == 0:
        { get_sprite_with_this_brain(16, current_sprite) == 0:
            //no more brain 9 or 16 monsters here, lets introduce 'mog'
            >> spawn "s3-mog" #cmd #src:70
        }
    }
}
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. No behavioural difference, so no switch needed.

### R0025: s3-gs.c line 58, `die` (medium) - RESOLVED-CORRECT

- **Queue flagged:** `unclosed_block` (structure): block opened here in procedure die is never closed. Conversion note: closed at procedure header at line 79, which is where the engine stops skipping too
- **Original:**

```text
  57  void die( void )
  58  {
  59    int &hold = sp_editor_num(&current_sprite);
  60    if (&hold != 0)
  61    editor_type(&hold, 6); 
  62  
  63  if (&gobpass == 1)
  64  {
  65  if (get_sprite_with_this_brain(9, &current_sprite) == 0)
  66   {
  67   if (get_sprite_with_this_brain(16, &current_sprite) == 0)
  68    {
  69  
  70    //no more brain 9 or 16 monsters here, lets introduce 'mog'
  71    spawn("s3-mog");
  72   }
  73  
  74   }
  75  
  76  
  77  
  78  }
  79  void attack( void )
```

- **Engine:** The unclosed block is the procedure's own `{`: the `}` is missing before the next `void` line. The engine ends a procedure at the next `void` line anyway (dink.cpp:7131, 7323), so every statement of `die` runs and nothing else changes. The Ink ends `die` at the same place.
- **Ink as converted:**

```text
= p_die
// void die( void ) (lines 57-78)
~ s3_gs__hold = sp_editor_num(current_sprite)
{ s3_gs__hold != 0:
    >> editor_type {s3_gs__hold} 6 #cmd #src:61
}
{ gobpass == 1:
    { get_sprite_with_this_brain(9, current_sprite) == 0:
        { get_sprite_with_this_brain(16, current_sprite) == 0:
            //no more brain 9 or 16 monsters here, lets introduce 'mog'
            >> spawn "s3-mog" #cmd #src:71
        }
    }
}
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None. No behavioural difference, so no switch needed.

### R0026: s5-end.c line 33, `main` (medium) - OWNER-DECISION

- **Queue flagged:** `unknown_call` (engine-differs): sp_prop() is not an engine command; the engine logs and skips it; intent: unclear. Conversion note: engine live (nothing); written call behind fix_s5_end_l33 (switch `fix_s5_end_l33`)
- **Original:**

```text
  32   int &door = sp(2);
  33   sp_prop(&door, 1);
```

- **Engine:** `sp_prop(&door, N);` is not an engine command (no `sp_prop` anywhere in dink.cpp), so it is logged and skipped like `freeeze` (11375-11436). What it was probably for: `&door = sp(2)` is the placement with map index 2 on SCR_419, `S419_P02`, a warp door (seq 61, `prop` 1, warp to screen 228). In the engine a placement whose map `prop` is non-zero is walk-through and `special_block` treats it as a warp (dink.cpp:569-575, 737, 15337-15341), and no script command can change `prop`. So `sp_prop(&door, 0)` in `s5-fguy` (comment `//kill door`) looks like 'close the door for the dragon fight' and `sp_prop(&door, 1)` in `s5-end` like 'open it again'. That is inference from the data; the author's intent is not stated. In 1997 the door is simply a warp all along. The Ink default (nothing) is faithful; the intent branch emits an undefined command and `director_vocabulary.csv` documents it with an invented note (`set the property (-1 = leave unchanged)`).
- **Ink as converted:**

```text
~ s5_end__door = sp(2)
{ fix_s5_end_l33:
    >> sp_prop {s5_end__door} 1 #cmd #src:33
}
CONST fix_s5_end_l33 = false // review: unknown command sp_prop()
```

- **Class:** OWNER-DECISION. Switch: exists.
- **Action:** See Owner decision OD1. Whatever is decided, correct the vocabulary note (the `-1 = leave unchanged` rule is unverified; the only evidence points to a 0/1 map `prop` flag). Switch exists (`fix_s5_end_l33`).

### R0027: s5-fguy.c line 6, `main` (medium) - OWNER-DECISION

- **Queue flagged:** `unknown_call` (engine-differs): sp_prop() is not an engine command; the engine logs and skips it; intent: unclear. Conversion note: engine live (nothing); written call behind fix_s5_fguy_l6 (switch `fix_s5_fguy_l6`)
- **Original:**

```text
   3  //kill door
   4  
   5   int &door = sp(2);
   6   sp_prop(&door, 0);
```

- **Engine:** Same as R0026: `sp_prop` is not a command and is skipped; it was probably meant to toggle the map `prop` flag of the SCR_419 door (inference).
- **Ink as converted:**

```text
~ s5_fguy__door = sp(2)
{ fix_s5_fguy_l6:
    >> sp_prop {s5_fguy__door} 0 #cmd #src:6
}
CONST fix_s5_fguy_l6 = false // review: unknown command sp_prop()
```

- **Class:** OWNER-DECISION. Switch: exists.
- **Action:** See Owner decision OD1. Whatever is decided, correct the vocabulary note (the `-1 = leave unchanged` rule is unverified; the only evidence points to a 0/1 map `prop` flag). Switch exists (`fix_s5_fguy_l6`).

### R0028: mag-star.c line 26, `main` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure main. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
   3  void main( void )
   4  
   5  int &myx = sp_x(1,-1);
  ...
  25  kill_this_task();
  26  }
```

- **Engine:** `void main( void )` has no `{` at all (line 4 is blank), and the body is written without the opening brace; the engine does not need it and runs lines 5-25 in order. `kill_this_task()` on line 25 ends the instance, so the `}` on line 26 is never read. No effect.
- **Ink as converted:**

```text
>> sp_seq {mag_star__rcrap} 169 #cmd #src:22
>> sp_frame {mag_star__rcrap} 6 #cmd #src:23
>> kill_this_task #cmd #src:25
-> DONE
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0029: s1-h1-1c.c (low) - RESOLVED-CORRECT

- **Queue flagged:** `d_without_c` (missing-script): s1-h1-1c.d exists with no s1-h1-1c.c; the engine would load the .d. Conversion note: not parsed into an AST (the pipeline reads .c files only)
- **Original:**

```text
(decoded from s1-h1-1c.d; line numbers are text lines of the decoded file)
   6  void talk(void)
   7  {
   8   if (&story >= 3)
   9   {
  10   say("My bed is going to burn up!", 1);
  11   return;
  12   }
  13   say("This my bed.  So clean and neat!  Mom must have made it.", 1);
  14  }
```

- **Engine:** `s1-h1-1c.d` is a compressed script (`dink_decompress`, misc_util.cpp:15); the engine would load it, but nothing does: the name is not in map.dat, dink.dat, dink.ini or any script, so it is dead data. I decoded it with `tools/dinkc/dinkc/source.py`: it is a variant of `s1-h1-1` (the bed) whose only difference is the text `This my bed.  So clean and neat!  Mom must have made it.` (missing `is`).
- **Ink as converted:**

```text
(no Ink: the pipeline reads `.c` only; `coverage.csv` row `s1-h1-1c` is `missing`)
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None: unreachable, so outside 'every reachable line' and the plan's 'dead scripts stay out'. Optional: teach the pipeline to fall back to `.d` so such files are at least classified.

### R0030: s1-h1-m.c line 72, `main` (low) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `engine_condition_differs` (engine-differs): engine evaluates `get_version() > 0`; intent: `get_version() > 108`. Conversion note: engine live; written condition behind fix_s1_h1_m_l72 (switch `fix_s1_h1_m_l72`)
- **Original:**

```text
  72  if (get_version() > 108)
  73  {
  74  //iphone will be changed to "large" in filename automatically if applicable
  75  show_popup("interface/iphone/quicktip_feeding.rttex", 1000);
  76  
  77  }
```

- **Engine:** `if (get_version() > 108)` is a function comparison. In the `(`-conditional branch the engine takes the text after the first `)` (` > 108`), finds `>`, runs `get_version()` and rebuilds the test as `"<ver> >  > 108"` (7183-7194); `var_figure` then compares against the word `>`, whose value is 0 (4905-4940). So the engine evaluates `get_version() > 0`. `get_version()` returns `C_DINK_VERSION` = 114 (dink.cpp:8828, dink.h:196) and the remaster's director binds the same 114 (`DinkDirector.cpp:30`), so the engine test and the written test are both true and the two branches agree. The body is `show_popup` (a mobile quick-tip image), recorded as not part of the remaster UI in `director_status.csv`. A scan of all 380 scripts finds exactly these two function comparisons with `>`/`<`/`!=`/`<=`/`>=`.
- **Ink as converted:**

```text
    { (fix_s1_h1_m_l72 and (get_version() > 108)) or (not fix_s1_h1_m_l72 and (get_version() > 0)):
        //iphone will be changed to "large" in filename automatically if applicable
        >> show_popup "interface/iphone/quicktip_feeding.rttex" 1000 #cmd #src:75
    }
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None. Switch exists (`fix_s1_h1_m_l72`). Keep the runtime's `get_version` at 114 so both sides stay equal.

### R0031: s1-h1-m.c line 149, `talk` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure talk. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
 143  
 144   unfreeze(1);
 145   unfreeze(&current_sprite);
 146  
 147    }
 148  
 149  }
 150  
 151  void hit(void)
```

- **Engine:** Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position (line 147 closes `talk`; 149 comes after the last statement, then `void hit` ends the procedure).
- **Ink as converted:**

```text
}
{ result == 5:
    I'm finished with my chores, mother. #id:s1-h1-m.talk.014 #say:say_stop #spk:1 #col:14 #src:138
    >> wait 200 #cmd #src:139
    Good boy.  Go visit our neighbors while I prepare dinner. #id:s1-h1-m.talk.015 #say:say_stop #spk:current_sprite #col:13 #src:140
}
>> unfreeze 1 #cmd #src:144
>> unfreeze {current_sprite} #cmd #src:145
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0032: s1-h2-o.c line 192 (low) - RESOLVED-CORRECT

- **Queue flagged:** `code_after_procedure_block` (structure): statements after the closing brace of procedure talk. Conversion note: kept in the procedure: the engine runs everything up to the next void line
- **Original:**

```text
 187   }
 188  
 189  
 190  }
 191  
 192    unfreeze(&current_sprite);
 193    unfreeze(1);
 194  }
 195  
```

- **Engine:** Braces in `talk`: line 31 opens it, line 190 closes it, 194 is extra. Lines 192-193 (`unfreeze(&current_sprite); unfreeze(1);`) follow the closing brace, which does not end a procedure (code-after-brace pattern, see Shared patterns). They are reached on every path that does not `return` earlier, including the `Leave` choice, which falls through. The Ink keeps them in `p_talk` after the last conditional.
- **Ink as converted:**

```text
    Ahh the regrets, right Ethel? #id:s1-h2-o.talk.027 #say:say_stop #spk:1 #col:14 #src:183
    >> wait 200 #cmd #src:184
    Dink .. #id:s1-h2-o.talk.028 #say:say_stop #spk:current_sprite #col:3 #src:185
    You've got problems. #id:s1-h2-o.talk.029 #say:say_stop #spk:current_sprite #col:3 #src:186
}
>> unfreeze {current_sprite} #cmd #src:192
>> unfreeze 1 #cmd #src:193
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0033: s1-h2-o.c line 194, `talk` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure talk. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
 187   }
 188  
 189  
 190  }
 191  
 192    unfreeze(&current_sprite);
 193    unfreeze(1);
 194  }
 195  
```

- **Engine:** Same as R0032: the statements after `talk`'s closing brace still run and the Ink keeps them in `p_talk`. The queue row is the extra `}` on 194: Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position.
- **Ink as converted:**

```text
    Ahh the regrets, right Ethel? #id:s1-h2-o.talk.027 #say:say_stop #spk:1 #col:14 #src:183
    >> wait 200 #cmd #src:184
    Dink .. #id:s1-h2-o.talk.028 #say:say_stop #spk:current_sprite #col:3 #src:185
    You've got problems. #id:s1-h2-o.talk.029 #say:say_stop #spk:current_sprite #col:3 #src:186
}
>> unfreeze {current_sprite} #cmd #src:192
>> unfreeze 1 #cmd #src:193
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0034: s1-sack.c line 33, `touch` (low) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `engine_condition_differs` (engine-differs): engine evaluates `get_version() > 0`; intent: `get_version() > 108`. Conversion note: engine live; written condition behind fix_s1_sack_l33 (switch `fix_s1_sack_l33`)
- **Original:**

```text
  33  if (get_version() > 108)
  34  {
  35  //iphone will be changed to "large" in filename automatically if applicable
  36  show_popup("interface/iphone/quicktip_saving.rttex", 4000);
  37  
  38  }
  39  }
```

- **Engine:** Same as R0030: the engine evaluates `get_version() > 0`; version 114 makes it and the written `> 108` both true; the body is the recorded no-op `show_popup`.
- **Ink as converted:**

```text
{ (fix_s1_sack_l33 and (get_version() > 108)) or (not fix_s1_sack_l33 and (get_version() > 0)):
    //iphone will be changed to "large" in filename automatically if applicable
    >> show_popup "interface/iphone/quicktip_saving.rttex" 4000 #cmd #src:36
}
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: exists.
- **Action:** None. Switch exists (`fix_s1_sack_l33`).

### R0035: s1-wand2.c line 187, `makefun` (low) - AUTHOR-INTENT-SWITCH

- **Queue flagged:** `midtext_backtick` (text): backtick inside the text after the colour code; intent: unclear (the font renderer may read it as a colour change). Conversion note: kept verbatim
- **Original:**

```text
 187    say_stop("`9Hello, I'm Chance `Zands", &current_sprite);
```

- **Engine:** `text_draw` reads colour codes only at the start of the text (`while (cr[0] == '`')`, dink.cpp:11810-11830); the rest goes to `RTFont::DrawWrapped` (Proton SDK, not in this repository), so what the 1997/HD renderer does with a backtick in the middle (the pair backtick-Z is not a colour code) is unverified. The shipped Ink keeps it verbatim, which is the engine-live text. It is almost certainly a stray keystroke (a name `Chance `Zands`); there is no reading in which the backtick is wanted.
- **Ink as converted:**

```text
Hello, I'm Chance `Zands #id:s1-wand2.makefun.008 #say:say_stop #spk:current_sprite #col:9 #src:187 #review:s1-wand2:187
```

- **Class:** AUTHOR-INTENT-SWITCH. Switch: missing (`fix_s1_wand2_l187`).
- **Action:** Add `CONST fix_s1_wand2_l187 = false` and switch the text: `{ fix_s1_wand2_l187: Hello, I'm Chance Zands - else: Hello, I'm Chance `Zands }` (same tags, same `#id`). Log: `s1-wand2.c:187`, stray backtick. Converter rule C5. Runtime: the subtitle renderer must not treat a mid-text backtick as a colour code in the default build. Switch does not exist yet; confidence in the fix is high, in the original rendering low.

### R0036: s2-auntp.c line 12 (low) - RESOLVED-CORRECT

- **Queue flagged:** `local_shadows_global` (variables): local `int &temphold` has the same name as a global. Conversion note: uses of &temphold in this script are treated as the local, not the global (the engine looks up locals first once declared)
- **Original:**

```text
  10   if (&s2-aunt < 4)
  11   {
  12   int &temphold = create_sprite(160,150, 0, 0, 0);
  13   sp_script(&temphold, "s2-jack");
  14   wait(5);
  15   }
  16  int &myrand;
```

- **Engine:** `int &temphold = create_sprite(...)` declares a script-local; `make_int` only reuses a variable of the same scope (`var_exists`, 4599; `make_int`, 4647), so a new local is created next to the global `&temphold`. After that `get_var` (3920) finds the local first, which is what `decipher` uses. The local lives as long as the script instance (`kill_script`, 3377, drops it), and every later use of `&temphold` in this file (lines 29-185) is on a path with `&s2-aunt` below 4, i.e. after the declaration ran. Treating every use as the local is therefore exact.
- **Ink as converted:**

```text
VAR s2_auntp__temphold = 0
...
{ s2_aunt < 4:
    ~ s2_auntp__temphold = create_sprite(160, 150, 0, 0, 0)
    >> sp_script {s2_auntp__temphold} "s2-jack" #cmd #src:13
    >> wait 5 #cmd #src:14
}
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0037: s2-auntp.c line 192 (low) - RESOLVED-CORRECT

- **Queue flagged:** `code_after_procedure_block` (structure): statements after the closing brace of procedure main. Conversion note: kept in the procedure: the engine runs everything up to the next void line
- **Original:**

```text
 184     &s2-aunt = 1;
 185     unfreeze(&temphold);
 186      }
 187  
 188  
 189     unfreeze(1);
 190    }
 191  
 192  sp_brain(&current_sprite, 16);
 193  
 194  
 195  }
```

- **Engine:** `main`'s braces: line 4 opens, line 190 closes it (the block of line 144 closes on 186), 195 is extra. Lines 189 (`unfreeze(1)`) and 192 (`sp_brain(&current_sprite, 16);`) therefore sit at procedure level and run like any other statement (code-after-brace pattern, see Shared patterns). They run on every path that does not `return` (the `&s2-aunt == 2` branch returns on line 139). The Ink has both at the end of `p_main` after the last conditional.
- **Ink as converted:**

```text
    >> unfreeze {s2_auntp__temphold} #cmd #src:185
}
>> unfreeze 1 #cmd #src:189
>> sp_brain {current_sprite} 16 #cmd #src:192
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0038: s2-auntp.c line 195, `main` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure main. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
 184     &s2-aunt = 1;
 185     unfreeze(&temphold);
 186      }
 187  
 188  
 189     unfreeze(1);
 190    }
 191  
 192  sp_brain(&current_sprite, 16);
 193  
 194  
 195  }
```

- **Engine:** Same as R0037: lines 189 and 192 sit after the inner closing brace of `main` but still run on every path that does not return. The queue row is the extra `}`: Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position.
- **Ink as converted:**

```text
    >> unfreeze {s2_auntp__temphold} #cmd #src:185
}
>> unfreeze 1 #cmd #src:189
>> sp_brain {current_sprite} 16 #cmd #src:192
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0039: s2-ca-g.c line 160, `talk` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure talk. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
 153    }
 154  
 155     unfreeze(1);
 156     unfreeze(&current_sprite);
 157   
 158  
 159   }                                   
 160  }
```

- **Engine:** Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position (line 159 closes `talk`; `unfreeze(1)` and `unfreeze(&current_sprite)` on 155-156 run on every path).
- **Ink as converted:**

```text
        -> d_s2_ca_g.p_enter -> // enter()
    }
}
>> unfreeze 1 #cmd #src:155
>> unfreeze {current_sprite} #cmd #src:156
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0040: s2-healp.c line 113 (low) - RESOLVED-CORRECT

- **Queue flagged:** `code_after_procedure_block` (structure): statements after the closing brace of procedure talk. Conversion note: kept in the procedure: the engine runs everything up to the next void line
- **Original:**

```text
 106     unfreeze(1);
 107     goto mainloop;
 108     return;
 109  }
 110  
 111  
 112  }
 113  startchoice:
 114  &amount = &lifemax;
 115  &amount -= &life;
```

- **Engine:** In `talk`, the first block (`&life >= &lifemax`, plain-variable `>=`, handled by `var_figure` 4905) ends with `goto mainloop`, so it never reaches its own end. Line 112 closes `talk`'s brace, and what follows, from the label `startchoice:` on line 113, is the injured-case body: for `&life` below `&lifemax` the `if` is false, the engine skips its block, and continues at line 113 (code-after-brace pattern, see Shared patterns). `goto mainloop` jumps into `main`'s idle loop (labels are file-wide, 3769). The Ink does this: `{ life >= lifemax: ... }` then falls into `lbl_startchoice`.
- **Ink as converted:**

```text
// label `startok:` (no goto targets it)
{ life >= lifemax:
    -> m92 -> // menu, sets result
    { result == 1:
        -> d_s2_healp.p_buybottle -> // buybottle()
    }
    >> unfreeze 1 #cmd #src:106
    -> d_s2_healp.lbl_mainloop // goto mainloop
    ->->
}
...
= lbl_startchoice
// label `startchoice:` at line 113
~ s2_healp__amount = lifemax
~ s2_healp__amount = s2_healp__amount - life
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0041: s2-healp.c line 158, `talk` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure talk. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
 149    if (&result == 2)
 150    {
 151     buybottle();
 152    }
 153  
 154     unfreeze(1);
 155     goto mainloop;
 156     return;
 157  
 158  }
 159  
```

- **Engine:** Same as R0040: the code after `talk`'s closing brace, from `startchoice:`, is the live injured-case body. The queue row is the extra `}` on 158 after the last `goto mainloop; return;`, never reached: Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position.
- **Ink as converted:**

```text
>> unfreeze 1 #cmd #src:154
-> d_s2_healp.lbl_mainloop // goto mainloop
->->

```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0042: s2-jack.c line 63 (low) - RESOLVED-CORRECT

- **Queue flagged:** `trailing_text` (structure): text after call: ':'. Conversion note: ignored; the engine accepts a call without ';' so the command still runs
- **Original:**

```text
  59           say_stop("`6Why you little!!  Take this!", &current_sprite);
  60  sp_touch_damage(&current_sprite, 10);
  61  sp_speed(&current_sprite, 2);
  62  sp_brain(&current_sprite, 9);
  63  sp_target(&current_sprite, 1):
  64          }
```

- **Engine:** `sp_target(&current_sprite, 1):` ends in `:` instead of `;`. `get_parms` finishes at the `)` (4171-4186) and only looks at the next character to consume a `;`; anything else just returns true (4190-4199). The call runs, so the Ink's `>> sp_target` is right (inside the `&result == 3` block of `talk`, after the line that makes Jack hostile).
- **Ink as converted:**

```text
    Why you little!!  Take this! #id:s2-jack.talk.008 #say:say_stop #spk:current_sprite #col:6 #src:59
    >> sp_touch_damage {current_sprite} 10 #cmd #src:60
    >> sp_speed {current_sprite} 2 #cmd #src:61
    >> sp_brain {current_sprite} 9 #cmd #src:62
    >> sp_target {current_sprite} 1 #cmd #src:63
}
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0043: s2-jack.c line 160 (low) - RESOLVED-CORRECT

- **Queue flagged:** `trailing_text` (structure): text after call: ':'. Conversion note: ignored; the engine accepts a call without ';' so the command still runs
- **Original:**

```text
 156  Say("`6Oh, NOW YOU'VE DONE IT!", &current_sprite);
 157  sp_touch_damage(&current_sprite, 10);
 158  sp_speed(&current_sprite, 2);
 159  sp_brain(&current_sprite, 9);
 160  sp_target(&current_sprite, 1):
 161  }
```

- **Engine:** Same as R0042: the trailing `:` is ignored after the closing `)` and the call runs (in `hit`).
- **Ink as converted:**

```text
Oh, NOW YOU'VE DONE IT! #id:s2-jack.hit.001 #say:say #spk:current_sprite #col:6 #src:156
>> sp_touch_damage {current_sprite} 10 #cmd #src:157
>> sp_speed {current_sprite} 2 #cmd #src:158
>> sp_brain {current_sprite} 9 #cmd #src:159
>> sp_target {current_sprite} 1 #cmd #src:160
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0044: s3-chick.c line 42 (low) - CONVERTER-BUG

- **Queue flagged:** `missing_comma` (structure): missing comma after string argument in 'say_stop("`9Hello Dink, I\'m Christina." &current_sprite);'. Conversion note: split into two arguments; the engine's get_parms does not need the comma, so the line works in the game
- **Original:**

```text
  40     say_stop("My name's Dink, pleasure to meet you.", 1);
  41     wait(250);
  42     say_stop("`9Hello Dink, I'm Christina." &current_sprite);
  43     wait(250);
  44     say_stop("Just having a stroll around town?", 1);
```

- **Engine:** The queue and `DESIGN.md` say the engine's `get_parms` 'does not need the comma'. It does. After a string parameter `get_parms` demands a `,` before the next parameter and otherwise returns true at once (dink.cpp:4206-4225, the 'fake error' branch). `g_nlist` was zeroed on entry (4118), so the speaker handle is 0 and `say_stop` rejects it (7908-7913): line 42 is not spoken in 1997, and nothing blocks (the `wait(250)` lines on either side run back to back). The Ink speaks it, so the default build shows a line the engine never shows, with no switch.
- **Ink as converted:**

```text
    My name's Dink, pleasure to meet you. #id:s3-chick.talk.004 #say:say_stop #spk:1 #col:14 #src:40
    >> wait 250 #cmd #src:41
    Hello Dink, I'm Christina. #id:s3-chick.talk.005 #say:say_stop #spk:current_sprite #col:9 #src:42
    >> wait 250 #cmd #src:43
    Just having a stroll around town? #id:s3-chick.talk.006 #say:say_stop #spk:1 #col:14 #src:44
```

- **Class:** CONVERTER-BUG. Switch: missing (`fix_s3_chick_l42`).
- **Action:** Make it an engine-never-runs row: engine live = nothing; `{ fix_s3_chick_l42: Hello Dink, I'm Christina. #id:s3-chick.talk.005 #say:say_stop #spk:current_sprite #col:9 #src:42 }`, CONST declared, queue row with `fix_const`. Converter rule C3 (model the early return of `get_parms` for every call, not just this one) and correct `DESIGN.md` and the `conversion` text. Third never-spoken line, see OD2.

### R0045: s3-dorks.c line 56, `attack` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure attack. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
  47  void attack( void )
  48  {
  49  playsound(8, 5050,0,&current_sprite, 0);
  50  &mcounter = random(4000,0);
  51  sp_attack_wait(&current_sprite, &mcounter);
  52  }
  53  
  54  
  55  
  56  }
```

- **Engine:** Line 52 closes `attack`; the `}` on 56 is after the last statement of the file. Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position.
- **Ink as converted:**

```text
= p_attack
// void attack( void ) (lines 47-56)
>> playsound 8 5050 0 {current_sprite} 0 #cmd #src:49
~ s3_dorks__mcounter = random(4000, 0)
>> sp_attack_wait {current_sprite} {s3_dorks__mcounter} #cmd #src:51
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0046: s3-larry.c line 46 (low) - RESOLVED-CORRECT

- **Queue flagged:** `used_before_declared` (variables): &prom used at line 46 before its `int` at line 53. Conversion note: treated as the script's local; in the engine the use fails unless an earlier procedure run declared it
- **Original:**

```text
  40     if (&girl == 1)
  41     {
  42      say_stop("So, any other deals?", 1);
  43      wait(250);
  44      say_stop("`4Please sir, no more, I need to tend to my daughter.", &current_sprite);
  45      wait(250);
  46      say_stop("`6DADDY!!!!!!!!!", &prom);
  47      wait(250);
  48      say_stop("`4See what I mean..", &current_sprite);
  49      unfreeze(1);
  50      unfreeze(&current_sprite);
  51      return;
  52     }
  53     int &prom;
  54     &prom = create_sprite(310, 460, 0, 0, 0);
  55     sp_brain(&prom, 16);
```

- **Engine:** `talk` is run on the sprite's own script instance and that instance is not killed when the procedure ends (only instances that have a `proc_return` are, 11586-11593), so its locals persist between talks. `&girl` is set to 1 on line 63 only after line 53 (`int &prom;`) and the `create_sprite` on 54 have run in that instance, so the use on line 46, which needs `&girl == 1`, can only run after `&prom` exists. A new instance (after leaving the screen) starts with `main` and `&girl = 0`. The Ink keeps `s3_larry__prom` as a persistent variable and re-zeroes it where `int &prom;` runs, as the engine does (`make_int`, 4647).
- **Ink as converted:**

```text
VAR s3_larry__prom = 0
...
        DADDY!!!!!!!!! #id:s3-larry.talk.009 #say:say_stop #spk:s3_larry__prom #col:6 #src:46
...
    ~ s3_larry__prom = 0
    ~ s3_larry__prom = create_sprite(310, 460, 0, 0, 0)
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0047: s4-healp.c line 114 (low) - RESOLVED-CORRECT

- **Queue flagged:** `code_after_procedure_block` (structure): statements after the closing brace of procedure talk. Conversion note: kept in the procedure: the engine runs everything up to the next void line
- **Original:**

```text
 107     unfreeze(1);
 108     goto mainloop;
 109     return;
 110  }
 111  
 112  
 113  }
 114  startchoice:
 115  &amount = &lifemax;
 116  &amount -= &life;
```

- **Engine:** `s4-healp` is `s2-healp` with other sprite numbers, prices (100 gold) and one extra `&myrand = random(20, 1);` in `main`; the structure is identical, so the analysis of R0040/R0041 applies line for line (the converted files differ only in line numbers and those values).
- **Ink as converted:**

```text
// label `startok:` (no goto targets it)
{ life >= lifemax:
    -> m93 -> // menu, sets result
    { result == 1:
        -> d_s4_healp.p_buybottle -> // buybottle()
    }
    >> unfreeze 1 #cmd #src:107
    -> d_s4_healp.lbl_mainloop // goto mainloop
    ->->
}
...
= lbl_startchoice
// label `startchoice:` at line 114
~ s4_healp__amount = lifemax
~ s4_healp__amount = s4_healp__amount - life
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0048: s4-healp.c line 159, `talk` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure talk. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
 150    if (&result == 2)
 151    {
 152     buybottle();
 153    }
 154  
 155     unfreeze(1);
 156     goto mainloop;
 157     return;
 158  
 159  }
 160  
```

- **Engine:** `s4-healp` is `s2-healp` with other sprite numbers, prices (100 gold) and one extra `&myrand = random(20, 1);` in `main`; the structure is identical, so the analysis of R0040/R0041 applies line for line (the converted files differ only in line numbers and those values). The queue row is the extra `}` on 159: Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position.
- **Ink as converted:**

```text
>> unfreeze 1 #cmd #src:155
-> d_s4_healp.lbl_mainloop // goto mainloop
->->

```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0049: s4-st3p.c line 224, `talk` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
 223    if (&result == 3)
 224    {                                         f
 225   
 226    goto buy;
 227     //Stuff here
 228    }
```

- **Engine:** Line 224 is `{` followed by spaces and a stray `f`. The `{` is processed (level up; it also starts the skip if one is pending) and the remainder `f` is run as a statement: no command, no `(`, so it falls to `MERROR ... unknown` (11436) and returns 0; when the block is skipped (`&result != 3`) it is skipped with the rest of the block. No effect either way. The Ink keeps it as a comment and then does `goto buy`, as the engine does (`buy:` is on line 57, found by the file-wide scan).
- **Ink as converted:**

```text
{ result == 3:
    // [line 224: unrecognised statement, never executed: f]
    -> d_s4_st3p.lbl_buy // goto buy
    //Stuff here
}
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0050: s7-boss.c line 11 (low) - RESOLVED-CORRECT

- **Queue flagged:** `local_shadows_global` (variables): local `int &speed` has the same name as a global. Conversion note: uses of &speed in this script are treated as the local, not the global (the engine looks up locals first once declared)
- **Original:**

```text
  11  int &speed = 1;
```

- **Engine:** Same mechanism as R0036: `int &speed = 1;` creates a local that shadows the global `&speed` (declared in `main.c:19`) for this script instance, and every use of `&speed` in the file (lines 71, 108, 120, 127, 135, 143) comes after that declaration, in procedures of the same persistent instance. No other script reads the global `&speed`. The Ink uses `s7_boss__speed` for all of them.
- **Ink as converted:**

```text
VAR s7_boss__speed = 0
...
~ s7_boss__speed = 1
...
    >> sp_speed {current_sprite} {s7_boss__speed} #cmd #src:71
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0051: spice.c line 22, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  22  [lyric line, not reproduced here: see bin/dink/story/spice.c line 22]
```

- **Engine:** `spice.c` is dead: not in map.dat, dink.dat or any script, and `REMASTER_PLAN.md` section 5 already says dead scripts stay out, 'including the unused scene with pasted song lyrics'. `void 2become1` is not DinkC: lines 22-36 are pasted song lyrics, so the engine would log `unknown` for each line and do nothing (11436); it is never called anyway. The converter emits a comment instead of copying the text, which is also right on copyright grounds. This review does not quote those lines either.
- **Ink as converted:**

```text
// [line 22: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0052: spice.c line 23, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  23  [lyric line, not reproduced here: see bin/dink/story/spice.c line 23]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 23: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0053: spice.c line 24, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  24  [lyric line, not reproduced here: see bin/dink/story/spice.c line 24]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 24: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0054: spice.c line 25, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  25  [lyric line, not reproduced here: see bin/dink/story/spice.c line 25]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 25: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0055: spice.c line 26, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  26  [lyric line, not reproduced here: see bin/dink/story/spice.c line 26]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 26: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0056: spice.c line 28, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  28   (solo)
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 28: unrecognised statement, never executed: (solo)]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0057: spice.c line 30, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  30  [lyric line, not reproduced here: see bin/dink/story/spice.c line 30]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 30: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0058: spice.c line 31, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  31  [lyric line, not reproduced here: see bin/dink/story/spice.c line 31]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 31: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0059: spice.c line 32, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  32  [lyric line, not reproduced here: see bin/dink/story/spice.c line 32]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 32: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0060: spice.c line 34, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  34  [lyric line, not reproduced here: see bin/dink/story/spice.c line 34]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 34: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0061: spice.c line 35, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  35  [lyric line, not reproduced here: see bin/dink/story/spice.c line 35]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 35: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0062: spice.c line 36, `2become1` (low) - RESOLVED-CORRECT

- **Queue flagged:** `unknown_statement` (not-code): ignored. Conversion note: comment only
- **Original:**

```text
  36  [lyric line, not reproduced here: see bin/dink/story/spice.c line 36]
```

- **Engine:** Same as R0051: dead script; the lyric lines are not DinkC and never run; the Ink holds only a comment.
- **Ink as converted:**

```text
// [line 36: not DinkC and never executed; text not copied, see the original file]
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0063: start-3.c line 31, `click` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure click. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
  30  void click(void)
  31  }
  32  sp_brain(1,0);
  33  Playsound(17,22050,0,0,0);
```

- **Engine:** `void click(void)` is followed by `}` where `{` was meant. Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position: the engine starts the procedure at level 1, the `}` takes it to 0, and the next statement line raises it to 1 again, so every statement of `click` runs. `start-3` is dead (its registration is commented out in `start.c`, lines 108-111), so it does not ship.
- **Ink as converted:**

```text
= p_click
// void click(void) (lines 30-129)
>> sp_brain 1 0 #cmd #src:32
>> playsound 17 22050 0 0 0 #cmd #src:33
-> m34 -> // menu, sets result
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0064: start-3.c line 129, `click` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure click. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
 126  sp_seq(&crap, 197);
 127  sp_brain(1,13);
 128  
 129  }
```

- **Engine:** The `}` on line 129 closes `click` (line 31's `}` stood in for the opening brace) and is the last line of the procedure. Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position. Dead script (`start.c` 108-111).
- **Ink as converted:**

```text
>> sp_brain 1 13 #cmd #src:127
->->

```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0065: start-4.c line 31, `click` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure click. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
  30  void click(void)
  31  }
  32  Playsound(17,22050,0,0,0);
  33  kill_game();
  34  
  35  }
```

- **Engine:** Same as R0063: a `}` where `{` was meant after `void click(void)` is harmless, every statement of `click` runs. `start-4` is the live title-screen quit button (`start.c:115`): `click` plays sound 17 and calls `kill_game()`.
- **Ink as converted:**

```text
= p_click
// void click(void) (lines 30-35)
>> playsound 17 22050 0 0 0 #cmd #src:32
>> kill_game #cmd #src:33
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

### R0066: start-4.c line 35, `click` (low) - RESOLVED-CORRECT

- **Queue flagged:** `stray_close_brace` (structure): '}' with no open block in procedure click. Conversion note: ignored (the engine clamps its brace level at 0)
- **Original:**

```text
  30  void click(void)
  31  }
  32  Playsound(17,22050,0,0,0);
  33  kill_game();
  34  
  35  }
```

- **Engine:** The `}` on line 35 follows `kill_game();`, which ends the program, so it is never read. Stray-brace pattern (see Shared patterns): a lone `}` only lowers the level and changes nothing at this position.
- **Ink as converted:**

```text
= p_click
// void click(void) (lines 30-35)
>> playsound 17 22050 0 0 0 #cmd #src:32
>> kill_game #cmd #src:33
->->
```

- **Class:** RESOLVED-CORRECT.
- **Action:** None.

## Fix switch ledger

Every fix, logged against the original file. All constants default to `false` (the engine's behaviour).

| Constant | Original | What the fix does | Status |
|---|---|---|---|
| `fix_s1_boat_l3` | `s1-boat.c:3` | undeclared `&boat` (dead script) | exists |
| `fix_s1_h3_3_l8` | `s1-h3-3.c:8` | `freeeze` -> `freeze` | exists, intent branch wrong (C2) |
| `fix_s1_h3_3_l10` | `s1-h3-3.c:10` | `unfreeeze` -> `unfreeze` | exists, intent branch wrong (C2) |
| `fix_s1_h1_m_l72` | `s1-h1-m.c:72` | written `get_version() > 108` vs engine `> 0` | exists |
| `fix_s1_sack_l33` | `s1-sack.c:33` | same | exists |
| `fix_s2_cave_l117` | `s2-cave.c:117` | `wait(200:` -> `wait(200);` | exists |
| `fix_s2_crock_l5` | `s2-crock.c:5` | undeclared `&mcrap` (dead script) | exists |
| `fix_s2_jack_l171` | `s2-jack.c:171` | `'I guess ... husband."` quotes | exists |
| `fix_s4_h2p2_l43` | `s4-h2p2.c:43` | `reutrn;` -> `return;` | exists |
| `fix_s4_sign3_l17` | `s4-sign3.c:17` | missing `)` | exists |
| `fix_s5_end_l33` | `s5-end.c:33` | `sp_prop` (no such command) | exists, meaning undecided (OD1) |
| `fix_s5_fguy_l6` | `s5-fguy.c:6` | `sp_prop` (no such command) | exists, meaning undecided (OD1) |
| `fix_s1_h3_8_l13` | `s1-h3-8.c:13` | `{` should be `}` | TO CREATE (C4) |
| `fix_s2_man2_l25` | `s2-man2.c:25` | bare `current_sprite` -> `&current_sprite` | TO CREATE (C1) |
| `fix_s1_wand2_l187` | `s1-wand2.c:187` | stray backtick in `Chance `Zands` | TO CREATE (C5) |
| `fix_s3_chick_l42` | `s3-chick.c:42` | missing comma after the string | TO CREATE (C3) |
| `fix_s4_st1p_l166, fix_s4_st3p_l74/_l82/_l91/_l98` | `s4-st1p.c:166; s4-st3p.c:74, 82, 91, 98` | `goto mainloop` (no label, no target) | REMOVE: nothing behind them (C6) |

## Converter fixes to make

Deduplicated rules for `tools/dinkink` (and `DESIGN.md`):

- **C1, wrong speaker needs a switch (R0004).** For `say_sprite_zero` emit `{ fix_<script>_l<line>: <line> #spk:<intended> - else: <line> #spk:0 }` with the same `#id`, declare the CONST, fill `fix_const` in the queue; stop carrying the intent only in `#spk_intent` (a tag cannot be switched).
- **C2, typo'd calls (R0015, R0016).** In the intent branch of `unknown_call` emit the corrected command when the name is a typo of a known command (`freeeze` -> `freeze`, `unfreeeze` -> `unfreeze`), keep the original spelling in a comment, and never add misspellings to `director_vocabulary.csv`/`director_commands.csv`. For names with no known correction (`sp_prop`) see OD1.
- **C3, missing comma (R0044).** Model `get_parms` exactly: after a string parameter a missing `,` ends parsing with the remaining parameters 0 (dink.cpp:4206-4225). For `say`/`say_stop`/`say_xy`... the speaker is then 0 and the engine drops the line: classify as `engine_never_runs`, default nothing, written line behind `fix_<script>_l<line>`. Fix the `conversion` text and the sentence in `DESIGN.md` section 9 / queue generator that says the line works. Re-run the corpus for any other call whose argument list stops early.
- **C4, structural typo (R0001, R0002).** `unclosed_block` rows should report the root cause line (here 13, a `{` for a `}`), not the openers left unbalanced (7, 11), and need a hand-curated override (a small table of `script, line, replacement`) so both parses are emitted: default = the engine's nesting, intent = the balanced one behind `fix_<script>_l<line>`; for `s1-h3-8` hoist the two nested conditionals and gate them with the switch. The other three `unclosed_block` rows (R0023-R0025) are a missing procedure `}` before the next `void` and need nothing; downgrade them.
- **C5, stray character in text (R0035).** `midtext_backtick` should produce `{ fix_<script>_l<line>: <text without it> - else: <verbatim> }` with a CONST and `fix_const`. The subtitle renderer must not parse mid-text backticks as colour codes in the default build.
- **C6, switches with nothing behind them (R0007-R0011).** For `goto_missing_label` do not declare `CONST fix_..._l<N>` and leave `fix_const` empty (category `engine-matches-intent`). Latent: emit `->->` rather than `-> DONE` for 'ran off the end of the procedure', so a local-call callee returns to its caller as the engine does (`proc_return`); `kill_this_task` stays `-> DONE`. No shipped script is affected today.
- **C7, house-keeping.** Correct the invented `sp_prop` vocabulary note after OD1; add the never-spoken lines (R0003, R0006, R0044) to the queue as one category (`never-spoken`) so they can be listed for OD2; teach `coverage.csv` that `s1-h1-1c.d` is dead data (optional `.d` fallback).

## Owner decisions

- **OD1 (R0026, R0027): what should `sp_prop` do?** The 1997 scripts call a command that never existed to close and reopen the warp door on SCR_419 during the dragon fight (inferred from the map `prop` flag, not stated). Option A: leave both switches as recorded no-ops, so the door stays a warp throughout, as in 1997. Option B: define `sp_prop <sprite> <0|1>` in the director as 'set the placed sprite's `prop` (warp/walk-through) flag' and let the two existing switches turn the locking on. **Recommendation: B, with both switches left `false`**, so the default build is the 1997 behaviour and the intent is one flip away; confirm that the inferred meaning is what you want before it is written into the vocabulary.
- **OD2 (policy confirmation, R0003, R0006, R0044, plus R0001/R0002): ship with every `fix_` switch `false`?** Four typo bugs make written dialogue or behaviour unreachable in the 1997 engine: `s2-jack:171` ("I guess I just killed your husband."), `s4-sign3:17` ("Long live the ducks."), `s3-chick:42` (Christina's reply) and `s1-h3-8` (two of the three bed lines). Option A: ship them silent, per the policy that the engine's live behaviour is the default. Option B: enable the pure-typo ones in the shipped build. **Recommendation: A**, and reconsider after a playtest; the policy already says reachable lines only, and none of these is reachable in 1997.

Not owner decisions, already settled by the plan: dead scripts (`spice`, `s1-boat`, `s2-crock`, `start-3`, `s1-slim`) stay out; `show_popup` is not part of the remaster UI; the missing scripts stay missing.

## Observations outside the queue

- `s4-st1p` (`sell`) and `s4-st3p` (`buy`) end after `unfreeze(1)`; neither unfreezes the shopkeeper that `talk` froze (`freeze(&current_sprite)`), so in the engine the NPC stays frozen until the screen reloads. Probably invisible for a stationary shopkeeper; not verified in the running game.
- `s4-healp`/`s2-healp` rely on `goto mainloop` jumping from `talk`/`hit` into `main`'s idle loop; the runtime must run that as the same flow (`DESIGN.md` section 2 already says so).
- A same-line `if (cond) statement` whose statement contains `=`, `<` or `>` would be misread by the function-comparison branch (dink.cpp:7171-7240). A scan of all 380 scripts finds six same-line `if`s (`escape.c:35`, `item-pig.c:74`, `s1-hole.c:9`, `s2-sec1.c:34`, `s2-sec3.c:34`, `s3-sec1.c:34`); none has `=`, `<` or `>` after the condition, so none is affected.
