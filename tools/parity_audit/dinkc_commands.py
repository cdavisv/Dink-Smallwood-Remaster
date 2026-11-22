#!/usr/bin/env python3
"""Command table of doc/remaster/DINKC_PARITY.md: counts from tools/dinkc/out/calls.csv, verdicts by hand (15 Nov 2026 audit).

Usage: python3 -I tools/parity_audit/dinkc_commands.py > table.md   (after `python3 -m dinkc build` in tools/dinkc)
"""
import csv, collections, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# verdict codes: E equal; F divergent, fixed by the fix PR; D divergent, open (bug row); d divergent, minor or latent (no row);
# R recorded only (2D presentation/UI with no 3D meaning, or replaced by remaster UI); N engine no-op; X not an engine command.
V = {
 'say_stop': ('D', '7901-7932', 'DinkStorySubsystem HandleSpokenLine', 'speaker 0 skipped, kill_text_owned_by(speaker, 1), blocks until the text ends: equal. kill_returning_stuff (D:7916) was missing: open, fix held back (A40)'),
 'say': ('E', '7742-7765', 'HandleSpokenLine', 'sprite 0 skipped, kill_text_owned_by(speaker) unless 1000, no block'),
 'say_stop_npc': ('D', '7934-7960', 'HandleSpokenLine', 'skipped while the speaker talks (text_owned_by): equal; kill_returning_stuff missing: open, fix held back (A40)'),
 'say_stop_xy': ('D', '7964-7988', 'HandleSpokenLine', 'blocks; kill_returning_stuff missing: open, fix held back (A40)'),
 'say_xy': ('D', '7990-8008', 'HandleSpokenLine', 'no block; kill_returning_stuff missing: open, fix held back (A40)'),
 'wait': ('D', '8034-8057', 'DinkDirector wait', 'a one-shot callback after ms: equal; kill_returning_stuff (D:8043) missing: open, fix held back (A40)'),
 'preload_seq': ('N', '8059', 'converter comment', 'asset preload'),
 'unfreeze': ('E', '7380-7404', 'SetFrozen', 'active sprites only; Dink: move input back'),
 'freeze': ('E', '7406-7430', 'SetFrozen', 'Dink: move input and gravity held'),
 'create_sprite': ('D', '9041-9056, 3089-3135', 'DinkDirector create_sprite + EXTERNAL', 'add_sprite_dumb: speed 0, timing 0, base_* -1; the remake uses add_sprite (speed 1, timing 33, bases 0). Fix written but held back: the probe\'s Jack step relies on the old defaults (A41)'),
 'playsound': ('E', '8395-8411', 'UDinkAudioSubsystem (cue)', 'audio routing, not script semantics'),
 'init': ('R', '10400-10411, 2335-2460', 'ApplyInitLine', 'dink.ini line; hardbox of a missing sequence applied (parity), the 2D frames are not'),
 'sp_brain': ('E', '9699-9726', 'SpriteProperty + DinkBrains', 'brains: see the brains table'),
 'move_stop': ('d', '8588-8618, 12669', 'StartMove/StepMove', 'blocks until arrival: equal. The move ignores sp_timing and, for sprites other than Dink, hardness (process_move runs inside the brain, D:12669, 16893); a 60 s escape the engine lacks (A46)'),
 'sp_dir': ('E', '7489-7510', 'SpriteProperty dir', 'changedir on a write'),
 'sp_seq': ('E', '9616-9638', 'SpriteProperty seq', ''),
 'sp_speed': ('E', '9108-9125', 'SpriteProperty speed', 'changedir on a write'),
 'random': ('E', '8808-8826', 'Gameplay::Random', 'range 0 returns base; rand() % range + base'),
 'sp_timing': ('E', '10583-10602', 'SpriteProperty timing', ''),
 'sp_base_walk': ('E', '9450-9466', 'SpriteProperty base_walk', '-1 written (change_sprite_noreturn)'),
 'sp_script': ('E', '8143-8179', 'DinkDirector sp_script', 'kills the sprite\'s scripts, runs main at once unless no_running_main'),
 'sp_pframe': ('E', '9598-9614', 'SpriteProperty pframe', ''),
 'sp_pseq': ('E', '9580-9596', 'SpriteProperty pseq', ''),
 'sp_y': ('E', '10563-10581', 'SpriteProperty y', ''),
 'sp_x': ('E', '10149-10166', 'SpriteProperty x', ''),
 'kill_this_task': ('E', '8272-8281', 'DinkDirector kill_this_task', 'runs proc_return first, then kill_script'),
 'sp_touch_damage': ('E', '9796-9812', 'SpriteProperty touch_damage', '-1 = touch runs the script'),
 'sp_editor_num': ('E', '9681-9697', 'EXTERNAL sp_editor_num', ''),
 'sp_target': ('E', '9468-9484', 'SpriteProperty target', ''),
 'editor_type': ('d', '9640-9651', 'DinkDirector editor_type', 'the engine writes spmap[*pmap] (the current map); the remake the instance\'s screen. Equal unless a script attached to 1000 changes screen first (no base script found doing it)'),
 'sp_active': ('E', '9343-9360', 'DeactivateSprite', 'scripts of the sprite end (process_callbacks D:11606-11620 a frame later in the engine)'),
 'sp_hitpoints': ('E', '10294-10313', 'SpriteProperty hitpoints', ''),
 'sp_nohit': ('E', '10433-10451', 'SpriteProperty nohit', ''),
 'make_global_int': ('N', '8677-8692', 'converter: Ink VAR', 'globals are declared by the converter from main.c'),
 'move': ('d', '8113-8141', 'StartMove', 'as move_stop without the block; same open timing/hardness point (A46)'),
 'debug': ('N', '8640-8653', 'converter comment', ''),
 'external': ('E', '11326-11376', 'DinkDirector external', 'new instance, runs at once, caller waits if it blocks; &return unused by base scripts'),
 'sp_brain_parm': ('E', '9814-9828', 'SpriteProperty', ''),
 'load_sound': ('N', '8620-8638', 'converter comment', ''),
 'sp_exp': ('E', '9728-9743', 'SpriteProperty', ''),
 'sp_strength': ('E', '10358-10377', 'SpriteProperty + stats', ''),
 'sp': ('E', '9060-9086', 'EXTERNAL sp', 'first sprite with that editor number, else 0'),
 'sp_frame': ('E', '9884-9915', 'SpriteProperty frame', ''),
 'sp_frame_delay': ('E', '9917-9935', 'SpriteProperty', ''),
 'sp_distance': ('E', '10413-10431', 'SpriteProperty', ''),
 'get_sprite_with_this_brain': ('E', '9201-9224', 'EXTERNAL', 'lowest active handle with that brain, not Except; text sprites skipped (brain 8 is never asked)'),
 'sp_base_attack': ('E', '9512-9528', 'SpriteProperty', ''),
 'screenlock': ('E', '10083-10097', 'Gameplay::SetScreenLock', 'cleared by load_map'),
 'playmidi': ('E', '8321-8347', 'audio cue', ''),
 'sp_attack_wait': ('E', '9325-9341', 'SpriteProperty (now + ms)', ''),
 'sp_range': ('E', '9127-9145', 'SpriteProperty', ''),
 'sp_defense': ('E', '10379-10398', 'SpriteProperty + stats', ''),
 'sp_hard': ('E', '9979-10004', 'DinkDirector sp_hard', 'also the loaded map\'s flag'),
 'script_attach': ('F', '8075-8087', 'DinkDirector script_attach', 'the engine sets the instance\'s sprite, so &current_sprite becomes 1000 and later sp_* on it are ignored (change_sprite D:5396-5403); the remake kept &current_sprite: fixed (A47); owner-approved deviation: s1-mh-f keeps its sprite so Martridge\'s scroll shrinks away'),
 'editor_seq': ('E', '9653-9664', 'EditorVariant', ''),
 'editor_frame': ('E', '9666-9679', 'EditorVariant', ''),
 'draw_hard_sprite': ('E', '8089-8111', 'Gameplay::DrawHardSprite', ''),
 'sp_notouch': ('E', '10453-10471', 'SpriteProperty', ''),
 'sp_base_death': ('R', '9548-9564', 'recorded', '2D death sequence; the remake\'s death presentation is the corpse/blood layer (gore audit)'),
 'sp_que': ('R', '9416-9431', 'recorded', '2D draw order'),
 'sp_nodraw': ('E', '9164-9180', 'actor hidden', ''),
 'load_screen': ('D', '7874-7884, 1013-1015', 'DinkDirector load_screen', 'load_map: Dink\'s move and freeze end. The remake keeps the freeze when a script attached to 1000 still runs: the pits softlock (A42; fixed by PR #137)'),
 'draw_screen': ('E', '7767-7785', 'one-frame block + PollScreenChange', 'the screen build (kill_all_scripts, base script, placements) happens at the next PollScreenChange'),
 'draw_status': ('R', '7832-7848', 'recorded', 'HUD reads the facts'),
 'add_item': ('E', '7619-7631', 'Gameplay::AddItem', 'pickup procedure in a new instance'),
 'fade_down': ('d', '8245-8257', 'FadeTarget + 600 ms block', 'the engine fade is palette cycling until done; the 600 ms length is assumed'),
 'fade_up': ('d', '8259-8270', 'FadeTarget + 600 ms block', 'as fade_down'),
 'free_items': ('E', '7787-7798', 'EXTERNAL free_items', '16 slots'),
 'sp_nocontrol': ('R', '9147-9162', 'recorded', 'Dink control lock while an animation plays (s1-hole*, item-*); the pawn ignores it'),
 'sp_noclip': ('R', '9779-9794', 'recorded', '2D clip'),
 'sp_mx': ('E', '10214-10231', 'SpriteProperty', ''),
 'sp_my': ('E', '10245-10262', 'SpriteProperty', ''),
 'sp_reverse': ('R', '9761-9777', 'recorded', '2D animation direction'),
 'sp_flying': ('E', '10023-10043', 'SpriteProperty', ''),
 'sp_kill_wait': ('d', '10045-10062', 'recorded', 'kill_wait delays a monster\'s next attack decision; recorded only (AI layer)'),
 'set_callback_random': ('D', '7530-7544, 4266-4297, 11602-11688', 'CallbackProc + Advance', 'fires into the idle instance; the engine kills it on wait, say_stop*, say_xy and before talk/hit/damage: the remake never did: open, fix held back (A40)'),
 'sp_size': ('E', '9381-9395', 'actor scale', ''),
 'sp_attack_hit_sound': ('R', '10315-10334', 'recorded', 'audio'),
 'count_item': ('E', '10168-10189', 'EXTERNAL', ''),
 'hurt': ('E', '9937-9977', 'DinkDirector hurt', 'kill_returning_stuff of the target now done by StartProcedure(hit)'),
 'kill_shadow': ('E', '9020-9039', 'DinkDirector kill_shadow', ''),
 'spawn': ('E', '8181-8202', 'DinkDirector spawn', ''),
 'add_magic': ('E', '7648-7660', 'Gameplay::AddItem(magic)', ''),
 'sp_brain_parm2': ('E', '9830-9845', 'SpriteProperty', ''),
 'sp_kill': ('E', '10064-10081', 'KillAtMs', ''),
 'draw_hard_map': ('E', '8224-8235', 'Gameplay::DrawHardMap', ''),
 'fill_screen': ('R', '8507-8525', 'recorded', 'palette fill of the 2D buffer'),
 'kill_this_item': ('E', '7663-7675, 1505-1537', 'Gameplay::KillThisItem', ''),
 'kill_game': ('E', '8283-8301', 'quit', ''),
 'sp_attack_hit_sound_speed': ('R', '10336-10356', 'recorded', 'audio'),
 'sp_follow': ('E', '9847-9862', 'SpriteProperty follow', ''),
 'compare_weapon': ('E', '10473-10494', 'EXTERNAL', ''),
 'game_exist': ('E', '8566-8586', 'EXTERNAL (save slot exists)', ''),
 'stopmidi': ('E', '8349-8356', 'audio cue', ''),
 'load_game': ('E', '8527-8564', 'deferred LoadFromSlot', 'ends the caller (the engine returns at once, D:8558)'),
 'get_rand_sprite_with_this_brain': ('E', '9251-9300', 'EXTERNAL', ''),
 'activate_bow': ('E', '9397-9408', 'Gameplay::ActivateBow', ''),
 'get_last_bow_power': ('E', '9410-9414', 'EXTERNAL', ''),
 'kill_cur_item': ('E', '7801-7806', 'Gameplay::KillCurItem', ''),
 'set_dink_speed': ('F', '7563-7575, 17311-17321', 'DinkDirector set_dink_speed', 'dinkspeed sets Dink\'s walk speed every frame; the remake only recorded it, so Herb\'s boots (item-bt) did nothing: fixed (A43)'),
 'set_mode': ('R', '8982-8994', 'recorded', 'title/escape screen mode; the remake has its own menus'),
 'sp_disabled': ('d', '9362-9379', 'recorded', 'a disabled sprite is not drawn and does not think; used by s1-brg2 and s2-bar (2 calls)'),
 'get_version': ('E', '8828-8834', 'EXTERNAL (DinkVersion)', ''),
 'compare_sprite_script': ('d', '10520-10561', 'EXTERNAL', 'the engine answers 0 for an inactive sprite or one whose script ended; the remake compares the name even then (s4-rock, s4-sec1, s5-sec1: their sprites are alive when asked)'),
 'is_script_attached': ('E', '9089-9106', 'EXTERNAL (instance id)', 'pairs with run_script_by_number'),
 'run_script_by_number': ('E', '8204-8222', 'StartProcedureIn + RunNow', ''),
 'inside_box': ('E', '8784-8806', 'EXTERNAL', ''),
 'restart_game': ('E', '8010-8032', 'deferred ResetRuntime', ''),
 'save_game': ('E', '8475-8488', 'SaveToSlot', ''),
 'sp_sound': ('R', '9302-9323', 'recorded', 'looping sprite sound (fire.c, savebot.c)'),
 'add_exp': ('E', '7633-7645', 'Gameplay::AddExp', ''),
 'reset_timer': ('R', '7591-7598', 'recorded', 'play-time clock of the save slot text'),
 'arm_weapon': ('E', '7851-7860', 'Gameplay::ArmWeapon', ''),
 'force_vision': ('E', '8490-8505', 'ForceOriginalHardnessVision', ''),
 'show_popup': ('R', '8938-8956', 'recorded', 'HD mobile tip'),
 'dink_can_walk_off_screen': ('R', '10122-10133', 'flag kept', 'screen edges are not walls in 3D'),
 'get_burn': ('E', '8974-8980', 'EXTERNAL 0', ''),
 'show_bmp': ('d', '7693-7706', 'waits for a key, shows nothing', 'button6.c\'s map (tiles\\map1.bmp) is not shown (A48)'),
 'sp_base_idle': ('R', '9530-9546', 'recorded', ''),
 'set_button': ('R', '9745-9759', 'recorded', 'key binding menu'),
 'stop_entire_game': ('F', '10099-10120, 17423-17440', 'bStopEntireGame + Advance', 'no sprite thinks while the level-up menu is up; the remake only recorded it: monsters kept hitting Dink in lraise\'s menu: fixed (A44)'),
 'scripts_used': ('E', '10281-10292', 'EXTERNAL (live instances)', ''),
 'count_magic': ('E', '10191-10212', 'EXTERNAL', ''),
 'free_magic': ('E', '7815-7827', 'EXTERNAL', ''),
 'is_base_game': ('E', '8852-8859', 'EXTERNAL 1', ''),
 'stopcd': ('E', '9486-9493', 'audio cue', ''),
 'sp_prop': ('X', '-', 'owner decision OD1', 'not an engine command; behind fix switches that stay false'),
 'freeeze': ('X', '-', 'recorded', 'misspelling the engine ignores (s1-h3-3)'),
 'unfreeeze': ('X', '-', 'recorded', 'misspelling the engine ignores (s1-h3-3)'),
}

rows = list(csv.DictReader(open(f'{ROOT}/tools/dinkc/out/calls.csv')))
cnt = collections.Counter(); scripts = collections.defaultdict(set); kind = {}
for r in rows:
    cnt[r['name']] += 1; scripts[r['name']].add(r['script']); kind[r['name']] = r['kind']
out = []
missing = []
for n, c in cnt.most_common():
    if kind[n] == 'local':
        continue
    if n not in V:
        missing.append(n); continue
    v, d, rem, note = V[n]
    sc = sorted(scripts[n])
    where = ', '.join(sc) if len(sc) <= 4 else f'{len(sc)} scripts'
    out.append(f'| `{n}` | {c} | {where} | {v} | {d} | {rem} | {note} |')
print('\n'.join(out))
print('MISSING', missing, file=__import__('sys').stderr)
tally = collections.Counter(V[n][0] for n in cnt if kind[n] != 'local' and n in V)
print('TALLY', dict(tally), 'total', sum(tally.values()), file=__import__('sys').stderr)
locs = sorted(n for n in cnt if kind[n] == 'local')
print('LOCALS', len(locs), locs, file=__import__('sys').stderr)
