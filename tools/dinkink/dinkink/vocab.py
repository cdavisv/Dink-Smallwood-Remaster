"""Director command vocabulary.

Every statement-level DinkC built-in call becomes a command line `>> name args #cmd`.
`BLOCKING` lists the commands after which the engine yields (`ugly_return(2)` in
source/dink/dink.cpp process_line): the director must finish them before calling
Continue() again. Argument descriptions follow the engine's get_parms signatures.
"""

# name -> (category, argument description, note)
VOCAB = {
    "wait": ("timing", "ms", "pause the script"),
    "wait_for_button": ("timing", "", "wait for a button press (sets &result)"),
    "move": ("movement", "sprite, dir, stop_coord, ignore_hardness",
             "walk in numpad dir until x (dirs 4,6,1,3,7,9) or y (dirs 2,8) passes stop_coord"),
    "move_stop": ("movement", "sprite, dir, stop_coord, ignore_hardness",
                  "as move, but the script waits until the sprite arrives"),
    "freeze": ("control", "sprite", "stop the sprite's brain / player control (1 = Dink)"),
    "unfreeze": ("control", "sprite", "undo freeze"),
    "fade_down": ("screen", "", "fade to black; waits"),
    "fade_up": ("screen", "", "fade back in; waits"),
    "fill_screen": ("screen", "palette_index", "fill the screen with a colour"),
    "show_bmp": ("screen", "file, show_map_dot, unused", "full-screen picture until a key"),
    "copy_bmp_to_screen": ("screen", "file", "draw a picture as the background"),
    "playsound": ("audio", "sound, speed_hz, random_hz, sprite, repeat",
                  "sprite 0 = not positional"),
    "playmidi": ("audio", "file", "start music track"),
    "stopmidi": ("audio", "", "stop music"),
    "kill_all_sounds": ("audio", "", ""),
    "sound_set_kill": ("audio", "sound_instance", ""),
    "sound_set_survive": ("audio", "sound_instance, on", ""),
    "sound_set_vol": ("audio", "sound_instance, volume", ""),
    "stopcd": ("audio", "", "legacy CD audio stop"),
    "create_sprite": ("sprites", "x, y, brain, seq, frame",
                      "spawn an actor at screen pixels (statement form, handle unused)"),
    "sp_script": ("sprites", "sprite, script", "attach a script to a sprite and run its main"),
    "script_attach": ("sprites", "sprite", "re-own the running script (1000 = survive screen change)"),
    "sp_active": ("sprites", "sprite, 0/1", "0 removes the actor"),
    "hurt": ("combat", "sprite, damage", "apply damage"),
    "screenlock": ("world", "0/1", "lock the screen exits (locked fight)"),
    "load_screen": ("world", "", "load the screen in &player_map (warp)"),
    "draw_screen": ("world", "", "show the loaded screen; yields one frame"),
    "draw_hard_map": ("world", "", "rebuild collision"),
    "draw_hard_sprite": ("world", "sprite", "add a sprite's hardbox to collision"),
    "draw_status": ("ui", "", "redraw the status bar"),
    "draw_background": ("world", "", "redraw background"),
    "editor_type": ("world", "editor_sprite, type",
                    "persistent per-screen override (1 kill, 2-5 draw-only/hard, 6-8 respawn)"),
    "editor_seq": ("world", "editor_sprite, seq", "persistent override of the placement's seq"),
    "editor_frame": ("world", "editor_sprite, frame", "persistent override of the frame"),
    "force_vision": ("world", "vision", "reload the screen in another &vision"),
    "add_item": ("inventory", "script, seq, frame", "give an item"),
    "add_magic": ("inventory", "script, seq, frame", "give a spell"),
    "kill_this_item": ("inventory", "script", "remove an item"),
    "kill_this_magic": ("inventory", "script", "remove a spell"),
    "kill_cur_item": ("inventory", "", "remove the armed item; ends the item script"),
    "kill_cur_magic": ("inventory", "", "remove the armed spell"),
    "free_items": ("inventory", "", "query used as a statement (free slots)"),
    "free_magic": ("inventory", "", "query used as a statement"),
    "arm_weapon": ("inventory", "", "arm &cur_weapon"),
    "arm_magic": ("inventory", "", "arm &cur_magic"),
    "activate_bow": ("combat", "", "start the bow charge; yields"),
    "add_exp": ("stats", "amount, sprite", "experience with floating number at the sprite"),
    "external": ("scripts", "script, procedure, args...",
                 "run another script's procedure and wait for it (base game: drop tables)"),
    "spawn": ("scripts", "script", "start another script's main in parallel"),
    "run_script_by_number": ("scripts", "script_instance, procedure", ""),
    "kill_this_task": ("scripts", "", "end this script instance"),
    "callback_kill": ("scripts", "callback", ""),
    "set_callback_random": ("scripts", "procedure, min_ms, random_ms", "repeating timer into a procedure"),
    "choice_start": ("ui", "set_y, title_color", "a menu follows (Ink choices)"),
    "show_popup": ("ui", "text, ms", ""),
    "set_button": ("ui", "button, action", "key binding (escape menu)"),
    "set_mode": ("system", "mode", "engine mode switch (title screen)"),
    "save_game": ("system", "slot", ""),
    "load_game": ("system", "slot", "ends the script"),
    "restart_game": ("system", "", "ends the script"),
    "kill_game": ("system", "", "quit; ends the script"),
    "stop_entire_game": ("system", "0/1", "pause everything but this script"),
    "set_dink_speed": ("stats", "speed", "Dink's walk speed"),
    "dink_can_walk_off_screen": ("world", "0/1", ""),
    "reset_timer": ("system", "", ""),
    "init": ("animation", "dink.ini line", "redefine a sequence at run time (weapon animation sets)"),
    "load_palette": ("screen", "file", ""),
    "load_tile": ("world", "file, slot", ""),
    "map_tile": ("world", "tile_pos, tile", ""),
    "map_hard_tile": ("world", "tile_pos, hard", ""),
    "sp": ("sprites", "editor_sprite", "query used as a statement"),
}

# Commands after which the engine yields until something finishes.
BLOCKING = {"wait", "wait_for_button", "move_stop", "fade_down", "fade_up", "external",
            "draw_screen", "show_bmp", "activate_bow", "kill_cur_item", "kill_cur_magic",
            "kill_game", "kill_this_task", "load_game", "restart_game",
            "say_stop", "say_stop_xy", "say_stop_npc", "choice_start"}

# Engine no-ops for the remaster: kept as Ink comments.
NOOP = {"debug": "developer log", "preload_seq": "asset preload",
        "load_sound": "sound slot load", "make_global_int": "becomes a VAR in dink.ink",
        "breakpoint": "debugger", "logmsg": "developer log", "initfont": "font",
        "set_save_game_info": "save slot caption"}

SAY_CALLS = ("say", "say_stop", "say_xy", "say_stop_xy", "say_stop_npc")
SAY_BLOCKS = {"say": False, "say_xy": False, "say_stop": True, "say_stop_xy": True,
              "say_stop_npc": True}


def describe(name, signature):
    """(category, args, note, blocking) for any built-in."""
    if name in VOCAB:
        cat, args, note = VOCAB[name]
    elif name.startswith("sp_"):
        cat, args, note = ("sprites", "sprite, value",
                           "set the property (-1 = leave unchanged)")
    else:
        sig = signature or ""
        cat = "other"
        args = ", ".join("str" if c == "s" else "int" for c in sig)
        note = ""
    return cat, args, note, name in BLOCKING
