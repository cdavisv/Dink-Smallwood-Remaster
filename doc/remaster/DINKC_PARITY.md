# DinkC script runtime: parity audit against the 1997 engine (15 Nov 2026)

The game must be playable from end to end, every optional quest and side area included, not only the probe's route to
`&story` 16. This audit checks, offline, every DinkC command and built-in function the 380 shipped scripts use, the
language the converter turns into Ink, and every brain the data uses, against the engine source `source/dink/dink.cpp`
(cited as D:line). It then lists the scripts the probe never runs and checks them statically for divergent commands and
softlocks.

The reference is `source/dink/dink.cpp`, the Dink Smallwood HD code base (redink1 fixes included). Where its behaviour
is a later safety fix over undefined 1997 behaviour, the row says so.

## Result in numbers

| | count |
|---|---|
| Distinct names called in `bin/dink/story/*.c` (tools/dinkc `calls.csv`, 10,409 calls) | 144: 129 engine commands and functions, 15 local procedure calls |
| Engine commands and functions audited | 129 |
| Equal to dink.cpp | 85 |
| Divergent, fixed in the fix PR (`fix/dinkc-parity`) | 10 commands, in 6 defects (A40-A45) |
| Divergent, open | 1 with a bug row (`script_attach`, A47, owner decision) and 9 minor or latent (`d` below); two of them have rows (A46 move timing/hardness, A48 `show_bmp`) |
| Recorded only | 17. These are 2D presentation (draw order, clipping, palette, death sequence, idle sequence), audio, or the title/escape UI that the remaster replaces. |
| Engine no-ops (`preload_seq`, `debug`, `load_sound`, `make_global_int`) | 4 |
| Not engine commands (`sp_prop` = owner decision OD1, the misspellings `freeeze`/`unfreeeze`) | 3 |
| Language constructs audited (if/else, operators, goto, return, menus, locals, script lifetime...) | 22: 2 divergent with an effect (callbacks = A40, `script_attach` = A47), 3 latent |
| Brains in use (map.dat and scripts) | 16 numbers. 5 defects touch them: create_sprite defaults (A41), warp boxes (A45), `stop_entire_game` (A44), scripted move (A46), pig/duck death details (A49) |
| Scripts with an entry point | 377. The probe runs 177 of them, 74 only in part; 200 never. 25 of those 200 are dead scripts that no map or script loads. |
| Director command lines the probe executes | 2,857 of 9,527 (30.0 %) |
| Script warp targets (`&player_map = N` / `load_screen(N)`) | 31, all real screens in dink.dat |
| Softlocks found | 1 class in the remake, fixed (A42); 1 in the 1997 scripts, kept (A50, owner decision); 1 path unverified (s2-ryan2). The fixed class: Dink stayed frozen after the pits (`s1-hole`, `s1-hole3`, `s6-hole`, `s6-hole2`) and after the cutscenes that load a screen from a script attached to 1000 (`s2-mdoor`, `s8-duck2`, `s3-mayor`, `en-gmog`) whenever no base script of the new screen unfreezes him |

## Method

1. **Inventory.** `tools/dinkc` parses every script (`python3 -m dinkc build ...`, see tools/dinkc). `calls.csv` gives
   each call with script, procedure and line. `tools/parity_audit/dinkc_commands.py` joins it with the verdicts below
   and prints the command table.
2. **Engine semantics.** Each command's branch in `process_line` (D:7323-11410) was located (the line ranges in the
   table). The sp_* setters and getters share `change_sprite` (D:5396) and were checked as a class against
   `UDinkDirector::SpriteProperty`; the other branches were read one by one, together with the helpers they call (change_sprite D:5396, add_sprite_dumb D:3089, kill_returning_stuff D:5049, load_map D:962,
   process_callbacks D:11602, ThinkSprite D:16791, the brains). Two read-only sub-audits covered the language
   constructs and the brains; every defect below was re-checked in both sources before it was fixed.
3. **Remaster side.** Converter `tools/dinkink/dinkink/convert.py`, runtime `UDinkStorySubsystem` (instances,
   procedures, menus, texts, callbacks, screen changes), `UDinkDirector` (the `>> command` handlers and the Ink
   EXTERNAL functions), `UDinkGameplay` and `DinkBrains.cpp` (event dispatch, brains), and the remaster tests in
   `Plugins/DinkParity/Source/DinkParity/Private/Tests`.
4. **Probe coverage.** `tools/parity_audit/dinkc_coverage.py <trace folder> <out>` reads the twenty probe traces
   (`Saved/Narrative/probe_ch*_trace.txt` and `stonebrook_probe_trace.txt`, from a probe run at master `7cd12fe4`). It
   counts the procedures they start and the director command lines they run. Output:
   [dinkc_parity/script_coverage.csv](dinkc_parity/script_coverage.csv).
5. **Static checks of what the probe does not run.**
   - `tools/parity_audit/dinkc_freeze_scan.py` walks every procedure's AST through both branches of each `if`. It lists
     the paths where `freeze(1)` reaches `return`, `kill_this_task` or the procedure's end with no `unfreeze(1)`, and
     marks the ones that change screen or hand over to another script on the way
     ([freeze_paths.csv](dinkc_parity/freeze_paths.csv)). It does not follow `goto`; those paths were read by hand.
   - `tools/parity_audit/dinkc_not_covered.py` lists each script the probe does not run in full, with the commands it
     uses that diverge: [scripts_not_covered.md](dinkc_parity/scripts_not_covered.md).
   - All 31 literal script warp targets were checked against dink.dat.
6. **Fixes.** Each fix carries a dink.cpp citation in the code and an automation test in
   `Tests/DinkDinkCParityTests.cpp` (`Dink.Parity.DinkC.*`). Each test runs the real converted script headless: a
   standalone story, a set fact or a stand-in sprite, then the script, then an assertion on the outcome.

## Commands and functions

Verdict: **E** equal; **F** divergent, fixed by the fix PR; **D** divergent, open, with a bug row; **d** divergent but
minor or latent; **R** recorded only (2D presentation or UI the remaster replaces); **N** engine no-op; **X** not an
engine command. "D:" is the dink.cpp line range of the command's branch.

| command | calls | scripts | verdict | dink.cpp | remaster | notes |
|---|---|---|---|---|---|---|
| `say_stop` | 1702 | 118 scripts | F | 7901-7932 | DinkStorySubsystem HandleSpokenLine | speaker 0 skipped, kill_text_owned_by(speaker, 1), blocks until the text ends: equal. kill_returning_stuff (D:7916) was missing: fixed (A40) |
| `wait` | 1549 | 149 scripts | F | 8034-8057 | DinkDirector wait | a one-shot callback after ms: equal; kill_returning_stuff (D:8043) missing: fixed (A40) |
| `preload_seq` | 681 | 142 scripts | N | 8059 | converter comment | asset preload |
| `unfreeze` | 377 | 104 scripts | E | 7380-7404 | SetFrozen | active sprites only; Dink: move input back |
| `create_sprite` | 340 | 95 scripts | F | 9041-9056, 3089-3135 | DinkDirector create_sprite + EXTERNAL | add_sprite_dumb: speed 0, timing 0, base_* -1; the remake used add_sprite (speed 1, timing 33, bases 0): fixed (A41) |
| `say` | 339 | 161 scripts | E | 7742-7765 | HandleSpokenLine | sprite 0 skipped, kill_text_owned_by(speaker) unless 1000, no block |
| `playsound` | 298 | 136 scripts | E | 8395-8411 | UDinkAudioSubsystem (cue) | audio routing, not script semantics |
| `init` | 289 | 17 scripts | R | 10400-10411, 2335-2460 | ApplyInitLine | dink.ini line; hardbox of a missing sequence applied (parity), the 2D frames are not |
| `freeze` | 269 | 115 scripts | E | 7406-7430 | SetFrozen | Dink: move input and gravity held |
| `sp_brain` | 255 | 160 scripts | E | 9699-9726 | SpriteProperty + DinkBrains | brains: see the brains table |
| `move_stop` | 216 | 53 scripts | d | 8588-8618, 12669 | StartMove/StepMove | blocks until arrival: equal. The move ignores sp_timing and, for sprites other than Dink, hardness (process_move runs inside the brain, D:12669, 16893); a 60 s escape the engine lacks (A46) |
| `sp_dir` | 216 | 47 scripts | E | 7489-7510 | SpriteProperty dir | changedir on a write |
| `sp_seq` | 212 | 94 scripts | E | 9616-9638 | SpriteProperty seq |  |
| `sp_speed` | 212 | 126 scripts | E | 9108-9125 | SpriteProperty speed | changedir on a write |
| `random` | 178 | 106 scripts | E | 8808-8826 | Gameplay::Random | range 0 returns base; rand() % range + base |
| `sp_timing` | 172 | 115 scripts | E | 10583-10602 | SpriteProperty timing |  |
| `sp_base_walk` | 162 | 108 scripts | E | 9450-9466 | SpriteProperty base_walk | -1 written (change_sprite_noreturn) |
| `sp_script` | 153 | 67 scripts | E | 8143-8179 | DinkDirector sp_script | kills the sprite's scripts, runs main at once unless no_running_main |
| `sp_pframe` | 144 | 64 scripts | E | 9598-9614 | SpriteProperty pframe |  |
| `sp_pseq` | 143 | 70 scripts | E | 9580-9596 | SpriteProperty pseq |  |
| `sp_y` | 138 | 107 scripts | E | 10563-10581 | SpriteProperty y |  |
| `sp_x` | 129 | 102 scripts | E | 10149-10166 | SpriteProperty x |  |
| `kill_this_task` | 118 | 74 scripts | E | 8272-8281 | DinkDirector kill_this_task | runs proc_return first, then kill_script |
| `sp_touch_damage` | 110 | 78 scripts | E | 9796-9812 | SpriteProperty touch_damage | -1 = touch runs the script |
| `sp_editor_num` | 93 | 93 scripts | E | 9681-9697 | EXTERNAL sp_editor_num |  |
| `sp_target` | 93 | 47 scripts | E | 9468-9484 | SpriteProperty target |  |
| `editor_type` | 92 | 92 scripts | d | 9640-9651 | DinkDirector editor_type | the engine writes spmap[*pmap] (the current map); the remake the instance's screen. Equal unless a script attached to 1000 changes screen first (no base script found doing it) |
| `sp_active` | 79 | 47 scripts | E | 9343-9360 | DeactivateSprite | scripts of the sprite end (process_callbacks D:11606-11620 a frame later in the engine) |
| `sp_hitpoints` | 78 | 72 scripts | E | 10294-10313 | SpriteProperty hitpoints |  |
| `sp_nohit` | 69 | 58 scripts | E | 10433-10451 | SpriteProperty nohit |  |
| `make_global_int` | 63 | main | N | 8677-8692 | converter: Ink VAR | globals are declared by the converter from main.c |
| `move` | 61 | 17 scripts | d | 8113-8141 | StartMove | as move_stop without the block; same open timing/hardness point (A46) |
| `debug` | 59 | 32 scripts | N | 8640-8653 | converter comment |  |
| `external` | 52 | 52 scripts | E | 11326-11376 | DinkDirector external | new instance, runs at once, caller waits if it blocks; &return unused by base scripts |
| `sp_brain_parm` | 50 | 33 scripts | E | 9814-9828 | SpriteProperty |  |
| `load_sound` | 49 | start | N | 8620-8638 | converter comment |  |
| `sp_exp` | 43 | 42 scripts | E | 9728-9743 | SpriteProperty |  |
| `sp_strength` | 42 | 36 scripts | E | 10358-10377 | SpriteProperty + stats |  |
| `say_stop_npc` | 42 | s2-bar, s2-man2, s2-out, s2-wench | F | 7934-7960 | HandleSpokenLine | skipped while the speaker talks (text_owned_by): equal; kill_returning_stuff missing: fixed (A40) |
| `sp` | 39 | 24 scripts | E | 9060-9086 | EXTERNAL sp | first sprite with that editor number, else 0 |
| `sp_frame` | 38 | 31 scripts | E | 9884-9915 | SpriteProperty frame |  |
| `sp_frame_delay` | 37 | 21 scripts | E | 9917-9935 | SpriteProperty |  |
| `say_stop_xy` | 37 | king, s1-ltr, s7-mil, start-3 | F | 7964-7988 | HandleSpokenLine | blocks; kill_returning_stuff missing: fixed (A40) |
| `sp_distance` | 36 | 30 scripts | E | 10413-10431 | SpriteProperty |  |
| `get_sprite_with_this_brain` | 36 | 25 scripts | E | 9201-9224 | EXTERNAL | lowest active handle with that brain, not Except; text sprites skipped (brain 8 is never asked) |
| `sp_base_attack` | 35 | 31 scripts | E | 9512-9528 | SpriteProperty |  |
| `screenlock` | 32 | 20 scripts | E | 10083-10097 | Gameplay::SetScreenLock | cleared by load_map |
| `playmidi` | 30 | 25 scripts | E | 8321-8347 | audio cue |  |
| `sp_attack_wait` | 29 | 29 scripts | E | 9325-9341 | SpriteProperty (now + ms) |  |
| `sp_range` | 28 | 25 scripts | E | 9127-9145 | SpriteProperty |  |
| `sp_defense` | 28 | 26 scripts | E | 10379-10398 | SpriteProperty + stats |  |
| `sp_hard` | 27 | 23 scripts | E | 9979-10004 | DinkDirector sp_hard | also the loaded map's flag |
| `script_attach` | 26 | 25 scripts | D | 8075-8087 | DinkDirector script_attach | the engine sets the instance's sprite, so &current_sprite becomes 1000 and later sp_* on it are ignored (change_sprite D:5396-5403); the remake keeps &current_sprite (A47, owner decision) |
| `editor_seq` | 25 | 25 scripts | E | 9653-9664 | EditorVariant |  |
| `editor_frame` | 25 | 25 scripts | E | 9666-9679 | EditorVariant |  |
| `draw_hard_sprite` | 24 | 21 scripts | E | 8089-8111 | Gameplay::DrawHardSprite |  |
| `sp_notouch` | 23 | 23 scripts | E | 10453-10471 | SpriteProperty |  |
| `sp_base_death` | 23 | 23 scripts | R | 9548-9564 | recorded | 2D death sequence; the remake's death presentation is the corpse/blood layer (gore audit) |
| `sp_que` | 20 | 16 scripts | R | 9416-9431 | recorded | 2D draw order |
| `sp_nodraw` | 20 | 10 scripts | E | 9164-9180 | actor hidden |  |
| `load_screen` | 19 | 18 scripts | F | 7874-7884, 1013-1015 | DinkDirector load_screen | load_map: Dink's move and freeze end. The remake kept the freeze when a script attached to 1000 still ran: pits softlocked: fixed (A42) |
| `draw_screen` | 19 | 18 scripts | E | 7767-7785 | one-frame block + PollScreenChange | the screen build (kill_all_scripts, base script, placements) happens at the next PollScreenChange |
| `draw_status` | 18 | 17 scripts | R | 7832-7848 | recorded | HUD reads the facts |
| `add_item` | 18 | 13 scripts | E | 7619-7631 | Gameplay::AddItem | pickup procedure in a new instance |
| `fade_down` | 17 | 16 scripts | d | 8245-8257 | FadeTarget + 600 ms block | the engine fade is palette cycling until done; the 600 ms length is assumed |
| `fade_up` | 17 | 16 scripts | d | 8259-8270 | FadeTarget + 600 ms block | as fade_down |
| `free_items` | 15 | 10 scripts | E | 7787-7798 | EXTERNAL free_items | 16 slots |
| `sp_nocontrol` | 14 | 14 scripts | R | 9147-9162 | recorded | Dink control lock while an animation plays (s1-hole*, item-*); the pawn ignores it |
| `sp_noclip` | 13 | 6 scripts | R | 9779-9794 | recorded | 2D clip |
| `sp_mx` | 12 | item-axe, item-fb, item-ice | E | 10214-10231 | SpriteProperty |  |
| `sp_my` | 12 | item-axe, item-fb, item-ice | E | 10245-10262 | SpriteProperty |  |
| `sp_reverse` | 12 | 5 scripts | R | 9761-9777 | recorded | 2D animation direction |
| `sp_flying` | 11 | 10 scripts | E | 10023-10043 | SpriteProperty |  |
| `sp_kill_wait` | 10 | 10 scripts | d | 10045-10062 | recorded | kill_wait delays a monster's next attack decision; recorded only (AI layer) |
| `set_callback_random` | 9 | 9 scripts | F | 7530-7544, 4266-4297, 11602-11688 | CallbackProc + Advance | fires into the idle instance; the engine kills it on wait, say_stop*, say_xy and before talk/hit/damage: the remake never did: fixed (A40) |
| `sp_size` | 9 | 5 scripts | E | 9381-9395 | actor scale |  |
| `sp_attack_hit_sound` | 9 | 6 scripts | R | 10315-10334 | recorded | audio |
| `count_item` | 9 | 5 scripts | E | 10168-10189 | EXTERNAL |  |
| `hurt` | 8 | 5 scripts | E | 9937-9977 | DinkDirector hurt | kill_returning_stuff of the target now done by StartProcedure(hit) |
| `kill_shadow` | 7 | dam-a1, dam-fire, dam-ice, dam-sfb | E | 9020-9039 | DinkDirector kill_shadow |  |
| `spawn` | 7 | 7 scripts | E | 8181-8202 | DinkDirector spawn |  |
| `add_magic` | 7 | 6 scripts | E | 7648-7660 | Gameplay::AddItem(magic) |  |
| `sp_brain_parm2` | 7 | 7 scripts | E | 9830-9845 | SpriteProperty |  |
| `sp_kill` | 7 | 5 scripts | E | 10064-10081 | KillAtMs |  |
| `draw_hard_map` | 6 | s1-h1-4, s1-roc, s4-ducks, s4-rock | E | 8224-8235 | Gameplay::DrawHardMap |  |
| `fill_screen` | 6 | 5 scripts | R | 8507-8525 | recorded | palette fill of the 2D buffer |
| `kill_this_item` | 6 | s2-out, s4-st1p | E | 7663-7675, 1505-1537 | Gameplay::KillThisItem |  |
| `say_xy` | 5 | 5 scripts | F | 7990-8008 | HandleSpokenLine | no block; kill_returning_stuff missing: fixed (A40) |
| `kill_game` | 4 | dinfo, escape, start, start-4 | E | 8283-8301 | quit |  |
| `sp_attack_hit_sound_speed` | 4 | item-axe, item-sw1, item-sw2, item-sw3 | R | 10336-10356 | recorded | audio |
| `sp_follow` | 4 | s1-duck, s3-freak | E | 9847-9862 | SpriteProperty follow |  |
| `compare_weapon` | 4 | s3-gobg, s3-st2p | E | 10473-10494 | EXTERNAL |  |
| `game_exist` | 3 | dinfo, escape, start-2 | E | 8566-8586 | EXTERNAL (save slot exists) |  |
| `stopmidi` | 3 | dinfo, s1-bul, start-2 | E | 8349-8356 | audio cue |  |
| `load_game` | 3 | dinfo, escape, start-2 | E | 8527-8564 | deferred LoadFromSlot | ends the caller (the engine returns at once, D:8558) |
| `get_rand_sprite_with_this_brain` | 3 | en-drag, s7-drag, sc-drag | E | 9251-9300 | EXTERNAL |  |
| `activate_bow` | 3 | item-b1, item-b2, item-b3 | E | 9397-9408 | Gameplay::ActivateBow |  |
| `get_last_bow_power` | 3 | item-b1, item-b2, item-b3 | E | 9410-9414 | EXTERNAL |  |
| `kill_cur_item` | 3 | item-bom, item-eli, item-nut | E | 7801-7806 | Gameplay::KillCurItem |  |
| `set_dink_speed` | 3 | item-bt, main | F | 7563-7575, 17311-17321 | DinkDirector set_dink_speed | dinkspeed sets Dink's walk speed every frame; the remake only recorded it, so Herb's boots (item-bt) did nothing: fixed (A43) |
| `set_mode` | 3 | newgame, start-1, start-2 | R | 8982-8994 | recorded | title/escape screen mode; the remake has its own menus |
| `sp_disabled` | 3 | s1-brg2, s2-bar | d | 9362-9379 | recorded | a disabled sprite is not drawn and does not think; used by s1-brg2 and s2-bar (2 calls) |
| `get_version` | 3 | s1-h1-m, s1-sack, start | E | 8828-8834 | EXTERNAL (DinkVersion) |  |
| `compare_sprite_script` | 3 | s4-rock, s4-sec1, s5-sec1 | d | 10520-10561 | EXTERNAL | the engine answers 0 for an inactive sprite or one whose script ended; the remake compares the name even then (s4-rock, s4-sec1, s5-sec1: their sprites are alive when asked) |
| `is_script_attached` | 2 | dam-fire, dam-sfb | E | 9089-9106 | EXTERNAL (instance id) | pairs with run_script_by_number |
| `run_script_by_number` | 2 | dam-fire, dam-sfb | E | 8204-8222 | StartProcedureIn + RunNow |  |
| `inside_box` | 2 | dam-icee, item-pig | E | 8784-8806 | EXTERNAL |  |
| `restart_game` | 2 | dinfo, escape | E | 8010-8032 | deferred ResetRuntime |  |
| `save_game` | 2 | escape, savebot | E | 8475-8488 | SaveToSlot |  |
| `sp_sound` | 2 | fire, savebot | R | 9302-9323 | recorded | looping sprite sound (fire.c, savebot.c) |
| `add_exp` | 2 | fish1, s7-boss | E | 7633-7645 | Gameplay::AddExp |  |
| `reset_timer` | 2 | newgame, start-1 | R | 7591-7598 | recorded | play-time clock of the save slot text |
| `arm_weapon` | 2 | newgame, start-1 | E | 7851-7860 | Gameplay::ArmWeapon |  |
| `force_vision` | 2 | s1-brg2, s1-h1-o | E | 8490-8505 | ForceOriginalHardnessVision |  |
| `show_popup` | 2 | s1-h1-m, s1-sack | R | 8938-8956 | recorded | HD mobile tip |
| `dink_can_walk_off_screen` | 2 | s2-culg | R | 10122-10133 | flag kept | screen edges are not walls in 3D |
| `sp_prop` | 2 | s5-end, s5-fguy | X | - | owner decision OD1 | not an engine command; behind fix switches that stay false |
| `get_burn` | 2 | s7-hell, s7-mil | E | 8974-8980 | EXTERNAL 0 |  |
| `show_bmp` | 1 | button6 | d | 7693-7706 | waits for a key, shows nothing | button6.c's map (tiles\map1.bmp) is not shown (A48) |
| `sp_base_idle` | 1 | dinfo | R | 9530-9546 | recorded |  |
| `set_button` | 1 | escape | R | 9745-9759 | recorded | key binding menu |
| `stop_entire_game` | 1 | lraise | F | 10099-10120, 17423-17440 | bStopEntireGame + Advance | no sprite thinks while the level-up menu is up; the remake only recorded it: monsters kept hitting Dink in lraise's menu: fixed (A44) |
| `freeeze` | 1 | s1-h3-3 | X | - | recorded | misspelling the engine ignores (s1-h3-3) |
| `unfreeeze` | 1 | s1-h3-3 | X | - | recorded | misspelling the engine ignores (s1-h3-3) |
| `scripts_used` | 1 | s1-ntree | E | 10281-10292 | EXTERNAL (live instances) |  |
| `count_magic` | 1 | s6-vend | E | 10191-10212 | EXTERNAL |  |
| `free_magic` | 1 | s6-vend | E | 7815-7827 | EXTERNAL |  |
| `is_base_game` | 1 | start | E | 8852-8859 | EXTERNAL 1 |  |
| `stopcd` | 1 | start-2 | E | 9486-9493 | audio cue |  |

**Local procedure calls** (`story();`, `buybottle();` ... 15 names, 24 call sites). The engine runs each call in a
new instance with fresh locals (D:11378-11407). The converter makes it an Ink tunnel on the same instance. All 24 call
sites were checked: no callee reads or writes a caller's local, and the two callees that call `kill_this_task`
(`s2-ca-g.c:186`, `start-2.c:89`) do it where the caller has already ended. Verdict: a different model with no
visible effect today.

## Language constructs

| construct | dink.cpp | remaster | verdict | scripts affected |
|---|---|---|---|---|
| if / else, braces, one statement per line | 7289-7310, 7363-7370, 7454-7486 | parser lexer, convert.py emit_if | E | none use multi-statement lines |
| unbraced nested if; `else if` after a true branch | 7339-7346 | parser `nested_if_no_braces`, `engine_else_after_comment` | latent | none found |
| simple condition `a op b` (needs spaces; one word = non-zero) | var_figure 4905-4982 | cond_expr | E | - |
| `if (func() == x)`; `> x` / `< x` compare against 0; the rest of the line is dropped | 7171-7243 | engine_cond | E | 88 call comparisons, all `==` or `get_version() > 108` |
| `func() != / <= / >= x` (the engine compares with 0, the converter keeps x) | 7171-7180 | convert.py engine_cond | latent (no base script uses it; the parser's emulation would fail the build) | none |
| `=` `+=` `-=` `*=` `/=` (right side one word or one call) | var_equals 4697-4848 | emit_assign | E | item-b1/b2/b3 `&mypower / 100` |
| division by 0 (the engine ignores it) | 4828-4838 | Ink `/` | latent | divisors are literals |
| `int &x [= e]` resets to 0, then assigns | make_int 4647-4695, 8694-8716 | `~ x = 0` then the assignment | E | - |
| lookup: script local first, then global | get_var 3920-3949 | per-instance local VARs (SwapIn/SwapOut) | E | s2-auntp, s7-boss shadow globals, declared before use |
| undeclared variable (reads 0, a write is lost) | 4716-4722 | engine branch + fix switch | E | s1-boat:3, s2-crock:5 |
| goto: file-wide labels, prefix match, level reset | locate_goto 3769-3827 | emit_goto | E | 44 cross-procedure gotos |
| goto to a missing label (runs to the end of the file) | 3822 | `->->` | E | s4-st1p:166, s4-st3p:74/82/91/98 |
| `return;` | 10604-10615, 7434 | `->->` | E | - |
| `return value`, `&return`, `&arg1..9` | 7434, 3846-3910 | v_return / arg VARs | not used by base scripts | - |
| `external()`: new instance, the caller's sprite, args | 11326-11376 | DinkDirector external | E | 52 calls |
| `spawn()`: sprite 1000, runs at once | 8181-8201 | DinkDirector spawn | E | - |
| menu `&result` counts hidden options | talk_get 5196-5231 | `~ result = N` with the original index | E | s3-chick, s1-wand ... |
| menu with no visible option (the engine keeps `&result` and goes on) | 5147-5153 | converter fallback sets `result = 0` | latent | none (no base menu is all-conditional) |
| `&savegameinfo` / `&buttoninfo` follow the option's position | 4087-4113 | `savegameinfo(index)` | E (text format: playthrough-qa stream) | dinfo, start-2, escape |
| title lines, `&var` interpolation (longest name first) | 5117-5132, var_replace 3995-4026 | text.py | E | gold scripts, lraise, healers, escape |
| end of procedure without `kill_this_task` (the instance stays) vs `kill_this_task` | run_script 11583-11590, kill_script 3377 | Idle vs FinishInstance | E | - |
| screen change kills every script not attached to 1000 | kill_all_scripts 3422 | OnScreenEntered | E | 24 `script_attach(1000)` sites |
| `script_attach(n)` also changes `&current_sprite` | 8075-8087 | only AttachedTo changes | **D (A47)** | s1-mh-f.c:37-40 visible; s7-boss.c:307, dam-icee.c:93 not visible |
| `set_callback_random` ended by say_stop / say_stop_npc / say_stop_xy / say_xy / wait and by talk/hit/damage | kill_returning_stuff 5049; 7916-8043; 14217, 14266, 14277, 14415, 15541, 15582, 9968 | never ended | **F (A40)** | en-drag, s7-drag, sc-drag, en-bong, s7-bong, sc-lock, s1-caves, s1-cave |
| `&current_sprite` in external (the caller's sprite) and spawn (1000) | 11336, 8188 | Instance.Sprite / HandleNoSprite | E | - |

## Brains

Counts: placements in map.dat (active slots 1-99 on screens dink.dat uses; type 0/2 background sprites are forced
to brain 0, D:6036-6046) / scripts that set the brain.

| brain | where used | verdict | notes | tests |
|---|---|---|---|---|
| 0 none | 3,941 / create_sprite x132, sp_brain x55 | E | follow matches D:13200 | indirect |
| 1 Dink | engine | not ported as a brain (the pawn) | bow ported (Dink.Gameplay.Bow); walk speed now follows set_dink_speed (A43) | Bow tests |
| 2 bounce | 0 / 0 | E (unused) | D:13616 | - |
| 3 duck | 89 / s8-da, treeduck | d (A49) | movement matches D:12780-12871; the first death skips the D:12744 `pseq` in base_walk check | Dink.AI.DuckAndPig, duckdie |
| 4 pig | 18 / 0 | d (A49) | death removes the pig at once: D:13378-13381 plays seq 164 under brain 7 first; damage is not held during a scripted move (D:13360) | Dink.AI.DuckAndPig |
| 5 / 7 play once | 0 / 17 files + 80 creates | E | - | - |
| 6 repeat | 28 / 21 files + 47 creates | E | - | weak |
| 8 text | engine (say) | story subsystem texts | timing strlen x 77 ms, min 2700 | Talk tests |
| 9 monster | 31 / 38 files + 8 creates | E in parity mode. Created ones got add_sprite defaults: **F (A41)**. Door boxes: **F (A45)** | targeting, attack, recal, screen edges match D:12887-13046; the 3D adaptation layer (wind-up, two attackers at most) is a deliberate play-mode change | Dink.AI.Monster.* |
| 10 dragon | 7 / en-drag, s7-boss, s7-drag, sc-drag | E | D:13234-13353 | bow target only |
| 11 missile | 0 / 56 creates, dam-ice | **F (A45)** | it crossed map.dat warp boxes (doors) | Missile tests + Dink.Parity.DinkC.WarpBoxIsHardForBrains |
| 12 scale | 0 / 25 files + 2 creates | E (created ones ran at timing 33: F A41) | D:15798 | gold shrink |
| 13 / 14 mouse, button | title screens (start*.c) | R | the remaster's own menus | - |
| 15 shadow | 0 / 12 creates | E (lagged at timing 33: F A41) | D:13218 | - |
| 16 people | 5 / 41 files | E in parity mode | find_action, edges, reverse match D:13048-13197; the NPC pace setting is a play-mode change | People tests |
| 17 missile, expires | 0 / dam-bom, dam-bom2 | E | D:14426 | - |
| all, while `stop_entire_game` | lraise.c | **F (A44)** | ThinkSprite(h, true) D:17423 | Dink.Parity.DinkC.StopEntireGamePausesSprites |
| all, scripted `move` / `move_stop` | 78 calls | **D (A46)** | the move runs inside the brain (process_move D:12669): the sp_timing gate slows it, hardness stops it unless move_nohard (D:16893); the remake moves at speed x 60 px/s through walls | - |

## Defects (bug list rows A40-A50)

| id | sev | defect | dink.cpp | status |
|---|---|---|---|---|
| A40 | S2 | `set_callback_random` timers were never ended. The engine ends them on `wait`, the say_stop family and `say_xy`, and when it runs `talk`, `hit` or `damage`. In the remaster, s1-caves roared and Dink complained every 5-15 s for as long as he stayed in the cave (in the original: at most twice). Dragons (s7-drag: 50 % chance to pick a random monster) and Boncas kept re-picking targets after Dink hit them, where the original stays locked on Dink. | 5049-5070, 7916, 7948, 7973, 7997, 8043, 9968, 14217, 14266, 14277, 14415, 15541, 15582 | fixed: `UDinkStorySubsystem::KillReturningStuff`; test `Dink.Parity.DinkC.CallbackEndsOnWaitSayAndHit` |
| A41 | S2 | `create_sprite` gave add_sprite's defaults (speed 1, timing 33, bases 0) instead of add_sprite_dumb's (speed 0, timing 0, bases -1). If Dink hits s1-gate's Chealse, she takes him as her target (base_attack 0 is not -1, D:15556) and then stands still for good (`in_this_base(seq, 0)`). Script fireballs without `sp_timing` (s2-cave2, s4-h1p, s8-da) fly at half speed. Created shadows and pickups lag, and created people walk at half pace. | 9041-9051, 3089-3135 | fixed: `UDinkDirector::InitDumbSprite`; test `Dink.Parity.DinkC.CreateSpriteUsesAddSpriteDumb` |
| A42 | S2 | Softlock: Dink stays frozen. `load_screen` is load_map, which ends Dink's freeze and move. The pits (s1-hole, s1-hole3, s6-hole, s6-hole2) and the cutscenes s2-mdoor, s8-duck2, s3-mayor and en-gmog freeze Dink, attach to 1000, load a screen and end without `unfreeze(1)`. In the remaster the screen change was noticed while that script still ran (fade_up), so Dink was not released. On 198, 182, 166 and 131 nothing else frees him (on 38, s2-mh-m's `main` does; on 586, 489 and 731 the next scene does). The probe never takes these routes: it reaches the rooms below through the pit warps. | 7874-7884, 1013-1015 | fixed in the `load_screen` handler; test `Dink.Parity.DinkC.LoadScreenUnfreezesDink` |
| A43 | S2 | `set_dink_speed` was only recorded, so Herb's boots (item-bt, sold in s1-boot) did nothing. dinkspeed 2 doubles Dink's walk speed (12/6/3 px per frame for 1/2/3). | 7563-7575, 17311-17321 | fixed: `ADinkGreyboxCharacter::DinkSpeedScale`; test `Dink.Parity.DinkC.SetDinkSpeedScalesWalk` |
| A44 | S2 | `stop_entire_game` was only recorded. In the original no sprite thinks while lraise.c's level-up menu is up. In the remaster, monsters kept walking and hitting, and touch damage kept landing, while the player chose an attribute after a kill in a fight. | 10099-10108, 17423, 17431-17440 | fixed: `UDinkDirector::bStopEntireGame`, handled in `UDinkStorySubsystem::Advance`; test `Dink.Parity.DinkC.StopEntireGamePausesSprites` |
| A45 | S3 | Every sprite but Dink crossed map.dat warp hardboxes (doors). `check_if_move_is_legal` reads `get_hard`, which keeps them hard; only Dink's walk uses `get_hard_play`. Villagers stood in doorways and fireballs flew through doors. | 13503, 527-546, 548-580 | fixed: `UDinkGameplay::CheckIfMoveIsLegal`; test `Dink.Parity.DinkC.WarpBoxIsHardForBrains` |
| A46 | S3 | Scripted `move`/`move_stop` ignore `sp_timing`, and ignore hardness for everyone but Dink. Cutscene walkers at timing 33 move twice as fast, and they pass walls where the original would stop them. The original could hang a `move_stop` there; the remaster has a 60 s escape. | 8113-8141, 8588-8618, 12669, 16836-16845, 16893 | open (needs the move stepped per brain think; it would move many probe traces) |
| A47 | S3 | `script_attach(1000)` leaves `&current_sprite` on the old sprite. In the engine it becomes 1000 and later sp_* on it are ignored. In the original, Martridge's scroll (s1-mh-f.c:37-40) stays on the floor after it is read; in the remaster it shrinks away, which is the author's evident intent. The HD engine's "Ignoring command" (D:5398) is a safety fix: the 1997 binary wrote out of bounds there. | 8075-8087, 5396-5403 | open: owner decision (keep the vanishing scroll, or match HD) |
| A48 | S3 | `show_bmp` waits for a key but shows nothing. button6.c's map (`tiles\map1.bmp`, the map key) appears as a blank pause. | 7693-7706 | open (UI: show the picture) |
| A49 | S3 | Brain details. The pig's death skips its seq-164 death animation under brain 7 (D:13378-13381). Pig damage is not held during a scripted move (D:13360). The duck's first death skips the D:12744 `pseq` in base_walk check. | 12744, 13360, 13378-13381 | open (cosmetic) |
| A50 | S2 | 1997 softlock kept. s3-st2p.c:30-42: buying the bow with 16 items carried leaves Dink and Arturous frozen (`return` without `unfreeze`). | - (script) | open: owner decision (a fix switch would be a deviation from 1997) |

## Scripts the probe does not run

Of 377 scripts with an entry point, the probe runs 177 (74 of them only in part) and never runs 200. 25 of the 200
are dead (no map placement and no script loads them). The rest:

- **Optional quests and areas.**
  - Stonebrook: the girl and the duck (s1-lg, s1-duck), the farm (s1-farm*), the wandering storyteller (s1-wand,
    s1-wand2), the boots shop (s1-boot, item-bt), the caves (s1-cave, s1-caves).
  - Terris: the secret rooms (s2-sec1..3), the fight (s2-fight), the crime scene (s2-crime), Ryan (s2-ryan2/3),
    the sales (s2-sale*), Martridge's house door (s2-mdoor).
  - Goblin and Windemere side areas: s3-1st, s3-larry, s3-freak, s3-gob*, s4-h1/h2 and their p-scripts, s4-st*
    shops.
  - Koka Isle, the snow castle and Hellfire: s8-* duck game, sc-* , s7-hell, s7-dgirl.
  - The extra weapons: item-axe, item-sw2/sw3, item-sfb, item-b2/b3.
  - The title, escape and death menus: start*, escape, dinfo.

  The full list, with each script's divergent commands and freeze paths, is
  [dinkc_parity/scripts_not_covered.md](dinkc_parity/scripts_not_covered.md).
- **Statically, after the fix PR.**
  - These scripts use no command whose remaster semantics are missing, other than the open rows above: A46 moves,
    A47 attach, A48 map picture, and the 2D-only `sp_nocontrol` / `sp_kill_wait` / `sp_disabled` / `sp_base_death`.
  - The commands they depend on and that the probe does not exercise are now covered by tests: callbacks
    (s1-cave/s1-caves, sc-lock, sc-drag), created sprites (s8-da, s2-tds, s3-larry, s2-ryan3, s1-rand),
    set_dink_speed (item-bt), load_screen from a 1000 script (s1-hole, s2-mdoor, s8-duck2), stop_entire_game (lraise).
- **Freeze paths** ([freeze_paths.csv](dinkc_parity/freeze_paths.csv)). 43 paths; all were read.
  - 18 pass through a screen change or a hand-over. Of these, the pits and s2-mdoor / s8-duck2 / s3-mayor / en-gmog are
    A42. The rest hand Dink to a script that unfreezes him: s2-cult's and s8-da's fights, item-pig's sp_script, and
    dinfo's restart or quit.
  - 25 do not. 22 end in a `goto`, and those were followed by hand. They are menu loops (escape, s1-lg, s2-healp,
    s2-out, s2-wand, s4-healp, s4-st1p, s4-st3p, s8-da betting) whose exits reach `unfreeze(1)`, or a fight that ends
    in one (s2-cult, s8-da). One exception: **s3-st2p.c:30-42**, Arturous's bow shop. "Buy a Bow" with all 16 item
    slots full shows "You are carrying too much", then `return`s with Dink and the shopkeeper still frozen. That is
    a softlock in the 1997 game as well, and the remaster keeps it; whether to fix it is the owner's decision (row
    A50).
  - The other three:
    - s1-h1-s.c's burning house walks Dink out through the door warp (load_map frees him).
    - s3-camp.c walks him off the screen; s3-camps freezes and frees him on the next screen.
    - s2-ryan2.c (started by s2-tds) ends `main` with Dink frozen, walking him north with `move_stop(1, 8, 0, 0)`.
      Only a screen change off the top edge frees him. Not verified at runtime: s2-ryan2 is never run, and in the
      remake a scripted move of Dink is a teleport.
- **Warps.** All 31 literal script warp targets are real screens. Map warps are checked by tools/analyse
  (`dst_in_bounds`).

## Probe traces

The fixes change what scripts and brains do on the probe's route, so trace md5s move. A40: the Bonca and dragon
fights and every callback's `rand()` draws. A41: every created sprite's timing; drops, fireballs and shadows are on
every chapter. A44: every level-up. A45: missiles and monsters at doors. A42 and A43 only touch screens and items the
probe does not use. The fix PR records the new table and these reasons in
`DinkRemasterUE/Plugins/DinkParity/Docs/packaged_probe.md`.

## Not checked

- No rendered play: every claim is from reading the two sources, and from the headless automation tests of the fix PR.
- `save_game`, `load_game`, `restart_game`, `force_vision`, `kill_game` and the audio commands were compared by their
  effect (which slot, what is reloaded, which cue), not against the engine's internals line by line.
- Getters on a dead or unknown sprite: the engine returns -1 (change_sprite D:5409-5411), the remake returns the
  last value (inactive sprite) or 0 (unknown handle). One base script tests a getter for -1: s3-st2p.c:12-17
  (Arturous's `hit` says "that pierced my lung" when `sp_pseq(&missle_source, -1)` is -1 and a bow is armed, else
  the "you could be doing much more damage with a bow" line). Which sprite `&missle_source` names after an arrow hit
  (missile_brain D:14318-14420 does not set it) was not traced, so this is not listed as a defect.
- The brain-1 human walk (the pawn), text_brain, the mouse/button brains 13/14 and the title UI.
- The 3D fitted-hardness geometry (`AuthoredActorMoveBlocked`). It is a deliberate rule (A7).
- Whether `rand()` draws match the engine exactly beyond what the probe determinism already covers (A25 belongs to the
  gore stream).
- Inkpot's look-ahead and variable-observer batching. Running out of the engine's `max_vars`. Sprite handle reuse across
  screens.
- The `savegameinfo` text format, which belongs to the playthrough-qa stream.
- `goto` paths in the freeze scan: they were followed by hand, not by the tool.
