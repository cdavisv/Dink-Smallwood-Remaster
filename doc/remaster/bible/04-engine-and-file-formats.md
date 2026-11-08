# Dink Smallwood HD engine: technical reference for a UE5 remaster

All line cites are to `source/dink/dink.cpp` ("D:") unless another file is named; `dink.h` is in the same directory. Nothing in the repo was modified. Struct sizes and offsets were checked by compiling the `dink.h` structs with natural alignment and by parsing the shipped `bin/dink` files. Items marked **inferred** were not confirmed in code.

## 1. File formats

All integers are little-endian int32, `bool` is 1 byte, and structs use natural 4-byte alignment. Files are raw `fread` dumps of the structs. `rtRect32` is assumed to be `{left, top, right, bottom}` (**inferred**: it is defined in the Proton SDK, which is not in this repo).

**`dink.dat`** is one `map_info`, 11,488 bytes (dink.h:559, D:1636):
```c
char  name[20];      // @0
int32 loc[769];      // @20    1-based record number in map.dat; 0 = no screen
int32 music[769];    // @3096  0 none, -1 stop, N -> "N.mid", >1000 -> "(N-1000).mid"  (D:5309)
int32 indoor[769];   // @6172  only stops last_map (map dot) updating
int32 v[40]; char s[80]; char buffer[2000];
```
Screens are numbered 1..768 on a 32x24 grid: ±1 is left/right, ±32 is up/down (D:14060-14150).

**`map.dat`** is a sequence of `small_map` records, 31,280 bytes each; record k starts at `(k-1)*31280` (D:987). The shipped file holds 644 records.
```c
struct small_map {            // 31280 bytes
  char name[20];              // @0
  tile t[97];                 // @20    80 bytes each; t[0..95] used, row-major 12x8, 50px tiles
  int32 v[40]; char s[80];    // @7780, @7940
  sprite_placement sprite[101]; // @8020  220 bytes each; indices 1..99 used
  char script[13];            // @30240 screen base script
  char random[13], load[13];  // @30253, @30266
  char buffer[1000];          // @30279
};
struct tile { int32 num, property, althard, more2; uint8 more3, more4; int32 buff[15]; }; // 80
struct sprite_placement {     // 220 bytes
  int32 x,y,seq,frame,type,size;   // @0..20   size is a percentage, 0 means 100
  bool  active;                    // @24
  int32 rotation,special,brain;    // @28,32,36
  char  script[13],hit[13],die[13],talk[13]; // @40,53,66,79 (only script is read at placement)
  int32 speed,base_walk,base_idle,base_attack,base_hit,timer,que; // @92..116
  int32 hard;                      // @120  0 = HAS hardness, 1 = none (inverted)
  rtRect32 alt;                    // @124  clip rect within the frame
  int32 prop;                      // @140  1 = warp
  int32 warp_map,warp_x,warp_y;    // @144,148,152
  int32 parm_seq;                  // @156  anim played on the sprite before warping
  int32 base_die,gold,hitpoints,strength,defense,exp,sound,vision,nohit,touch_damage; // @160..196
  int32 buff[5];                   // @200
};
```
- **Tile index:** `set = num/128 + 1`, `idx = num%128`, source rect at `x=(idx%12)*50, y=(idx/12)*50` in `tiles/tsNN.bmp` (D:6774-6797). The base game has 41 tilesets; HD allows 61 and prefers a `.png` if present (D:826).
- **Placement types** (D:6036-6149): 0 = background, baked into the screen image; 1 = live sprite; 2 = not drawn, hardness only.
- **Animated tiles:** `num` 896..1023 (water) and 2304..2431 (fire) swap to following tilesets on a timer (D:16638-16716).

**`hard.dat`** is `struct hardness` (dink.h:553). The shipped file is 2,107,392 bytes, shorter than the 2,118,400-byte struct, so a parser must tolerate a short read.
```c
struct ts_block { uint8 px[51][51]; bool used; int32 hold; };  // 2608 bytes; indexed [x][y], 0..49 used
struct hardness { ts_block tile[800]; int32 index[8000]; };    // index at @2086400
```
- `index[tile.num]` gives the hardness-tile id; `tile.althard > 0` overrides it per placed tile (D:648).
- The shipped index has 5,248 entries (41x128) and some garbage values, so range-check to 0..799 as the engine does (D:667).
- Cell values in the shipped data are 0, 1, 2 and a single 3. 0 is walkable, 1 is solid, and 2 is "low" hardness that flying sprites and missiles pass and that does not start a push (D:13504, 13526). Any other non-zero value blocks.
- At runtime, `100+N` marks editor sprite N's hardbox; if that sprite has `prop != 0` it is a warp trigger (D:548-579).
- The `used` flag is 0 throughout the shipped file; ignore it.

**`dir.ff`** (FFReader.h:15, FFReader.cpp:144-153), verified against `graphics/dink/walk/dir.ff`:
- `int32 count`, then `count` packed 17-byte records `{int32 offset; char name[13];}`.
- The last record is a sentinel with an empty name and offset equal to the file size.
- Each entry is a raw BMP, uncompressed; its size is the next record's offset minus its own. If the next offset is 0 the reader skips one record (FFReader.cpp:157).
- Names are upper-case 8.3 on disk and lower-cased on load.
- Lookup order: loose file or `.png` in the DMOD directory, then the `.ff`, then loose base files (FFReader.cpp:206-303).

**Frame naming:** `<path-prefix><NN>.bmp`, NN from 01 with no gaps, up to 100 frames (D:1715, 2033). Art is 8-bit using `tiles/palette.bmp`. The colour key is white by default and black with `BLACK` (D:2191-2197); that it is done by palette index (255 and 0) is **inferred**, since the loader is in Proton.

**`.d` scripts** are byte-pair encoded (misc_util.cpp `dink_decompress`). If the first byte is over 127, `(b-128)` two-byte pairs follow. Then each byte over 127 expands recursively to its pair. CR becomes LF, tab becomes space, and NUL ends the file. A `.d` is preferred over a `.c`, and the DMOD directory over the base (D:3546-3594).

**`dink.ini`** has 1,051 lines; tokens are space-separated and keywords case-insensitive (D:2165-2627):
- `load_sequence[_now] <path-prefix> <seq> [<delay_ms> <xoff> <yoff> <hardL> <hardT> <hardR> <hardB>]`
  - If token 4 is a keyword instead: `BLACK` = black key and animated; `LEFTALIGN` = flag only; `NOTANIM` = each frame gets its own default origin.
  - `_now` only affects eager loading; HD loads everything on demand.
- `SET_SPRITE_INFO seq frame xoff yoff hardL hardT hardR hardB` overrides one frame.
- `SET_FRAME_SPECIAL seq frame 1` marks the hit frame.
- `SET_FRAME_DELAY seq frame ms`.
- `SET_FRAME_FRAME seq frame srcSeq srcFrame` aliases a frame; `srcSeq = -1` stores -1, meaning loop back to frame 1 (D:17049).
- Also: `STARTING_DINK_X/Y`, `playmidi`, and `gfx_alttext_disable` (HD).
- Offsets are the origin ("depth dot") within the bitmap; the hardbox is relative to that origin.
- Defaults when unset (D:1834-1923): `xoff = w - w/2 + w/6`, `yoff = h - h/4 - h/30`, hardbox = `±w/4` horizontally and `±h/10` vertically. For animations, frame 1's origin applies to every frame.

**Save game** `save<N>.dat` is one `player_info`, 326,052 bytes (dink.h:328, D:1023):

| Offset | Field |
|---|---|
| 0 | `version` |
| 4 | `gameinfo[196]` |
| 200 | `minutes` |
| 204-260 | `x, y, die, size, defense, dir, pframe, pseq, seq, frame, strength, base_walk, base_idle, base_hit, que` |
| 264 | `g_MagicData[9]`, 20 bytes each: `bool active; char name[10]; int32 seq @12; int32 frame @16` |
| 444 | `g_itemData[17]`, same layout |
| 784 | `curitem, unused, counter`, then `bool idle` @796 |
| 800 | `spmap[769]`, 404 bytes each: `uint8 type[100]; uint16 seq[100] @100; uint8 frame[100] @300; int32 last_time @400` |
| 311476 | `button[10]` |
| 311516 | `var[250]`, 32 bytes each: `int32 var; char name[20]; int32 scope @24; bool active @28` |
| 319516 | `push_active`, then `push_dir, push_timer, last_talk, mouse, item_magic @319536, last_map @319540` |
| 320048 | `mapdat[50], dinkdat[50], palette[50]` |
| 320198 | `tile[42]`, 50-byte filenames |
| 322298 | `func[100]`: `{char file[10]; char func[20];}` |
| 325300 | `m_gameTime`, `attack_wait`, `cbuff[742]` |

All stats (life, gold, exp and so on) live in `var[]` as DinkC globals, not in dedicated fields.

## 2. World model

- **Screen:** 640x480 logical. The playfield is x 20..619, y 0..399 (600x400). The status bar is 640x80 at y=400, with 20-px side bars (D:3053-3061). Sprite x includes the 20-px offset; the collision map is `hitmap[x-20][y]`, one byte per pixel.
- **Timing:** fixed step. Each `updateFrame` adds 16.67 ms to `g_dinkTick` (D:17304) and `base_timing` is hard-wired to 7 (D:17308). Status, sound and animated tiles update every 100 ms (D:17340). Each sprite has a `timer` in ms between brain runs: 33 for `add_sprite`, 0 for DinkC `create_sprite`, and the editor value for map sprites (D:16836, 4323, 6103).
- **Player speed:** the player's timer is 0 (D:17125); the `timer = 33` at D:18022 is unreachable code after a `break`. So the player moves 3 px per 60 Hz frame at `dinkspeed` 3, 6 at 2 and 12 at 1 (D:17311-17321).
- **Diagonals:** `speed - speed/3` px on each axis, integer maths (D:15050). For other sprites `changedir` sets `mx/my` the same way and caps speed at 49 (D:5596).
- **Animation:** per-frame delay comes from the sequence or from `sp_frame_delay`. A sequence ends when the next frame entry is under 1; then `seq = 0` and `nocontrol` clears (D:17062-17071).
- **Collision:** only the sprite's origin point is tested, pixel by pixel along the move path, with rollback to the last legal pixel (D:13486-13553). Live sprites never collide with each other. Map sprites with `hard == 0` stamp their hardbox into the hitmap as `100+index` (D:487). On diagonals the player slides around corners with 1-2 px nudges (D:15110-15316).
- **Push:** if the player is blocked by hardness other than 2 while facing a cardinal direction and holds for 600 ms, the engine plays `base_push(310)+dir`, sets `nocontrol`, and runs `PUSH` on scripted sprites whose hardbox (±2) contains the player's point (D:13525, 14768, 15600).
- **Screen change:** x<20, x>619, y<0 or y>399 changes screen if `loc[neighbour] > 0` and there is no screenlock; the player is placed at the opposite edge (D:14049-14166).
- **Smooth scroll (HD):** the old frame is captured and slid over 400 ms; during that time sprites draw but do not think (D:13829, 27, 17423).
- **Warp:** touching sprite hardness with `prop == 1` plays a sound and optional `parm_seq`, fades down over 300 ms, sets `x`, `y` and `&player_map`, loads the screen, and fades up (D:15337, 15683).
- **Screen load order** (D:6731-6828): `load_map`, reset `&vision` to 0, build hardness; run the base script's `main`; place sprites; run `main` on every sprite script.
- **Vision:** a placement with `vision != 0` exists only when it equals `&vision`, which the base script normally sets (D:6031). `force_vision` rebuilds the screen.
- **Editor-info persistence** (`spmap[screen].type[i]`, D:5773-5832, timers D:917-959):
  - 1 = removed for good.
  - 2 = live, no hardness. 3 = background, no hardness. 4 = live, hard. 5 = background, hard.
  - 6, 7, 8 = removed, returning after 5, 3 and 1 minutes.
  - For any non-zero type, the sprite's seq and frame are replaced by `editor_seq`/`editor_frame` and its script is cleared.
- **Depth:** ascending by `que != 0 ? que : y`; ties go to the lower sprite index (D:17193). Text sprites draw last.
- **Scale:** `size` % grows the destination rect symmetrically about the unscaled rect; the hardbox is not scaled (D:3246-3272).

## 3. Combat

- **Hit trigger:** when an animation advances onto a frame with `special == 1`, the engine calls `run_through_tag_list(h, strength)` (D:17086).
- **Hit test** (D:15460-15590): for each other active sprite, take its hardbox at its position, grow it by 5 (10 at the bottom), then extend it toward the attacker by direction:
  - Facing 4 or 6: 28 px horizontally and ±10 vertically.
  - Facing 2 or 8: 36 px vertically and ±10 horizontally.
  - With `sp_range` set: `range` horizontally, `range + range/6` vertically, plus `range/8` on the lateral sides.
  - A hit registers if the attacker's origin point is inside. Diagonals get no extension.
  - Quirk to reproduce: for direction 8 with a range, the lateral widening cancels itself (D:15519-15520).
- **Damage:** `strength/2 + rand()%((strength+1)/2) + 1`, minus the target's defense; if the result is below 1 there is a 50% chance of 1, otherwise 0 (D:15567, 6656). It accumulates in `sprite.damage` and is applied by the target's brain on its next think.
- **On hit:** the target's `HIT` procedure runs with `&enemy_sprite` set to the attacker, and the target acquires the attacker as `target` if it has a `base_attack` or touch damage. A sprite with `nohit` and a script only gets `HIT`.
- **Touch damage** (D:15629): if the player's point is inside a sprite's hardbox ±2, the player takes `touch_damage` through the same defense rule and gets 400 ms of `notouch` immunity. A value of -1 only runs `TOUCH`.
- **No knockback or hit flash exists in the engine.** `move_nohard` is just the "ignore hardness" flag on `move()`.
- **Missiles, brains 11 and 17** (D:14240-14430): move by `mx/my` each think.
  - On hardness (not type 2): run the missile script's `DAMAGE` with `&missile_target` = 0 or the sprite hit, otherwise play a sound and die.
  - On a sprite: the missile's point inside the target hardbox (inflated by `range`), excluding `brain_parm`/`brain_parm2` (the shooters) and `nohit` sprites. Damage is `strength/2 + rand()%(strength/2) + 1 - defense`, with a float variant at fixes level 1. The target gets 100 ms `notouch`, then `DAMAGE` and the target's `HIT` run.
  - Missiles die outside x -500..1000, y -500..700.
- **Bow:** hold to charge up to 500 in steps of 7 per 100 ms; release runs the weapon script, which reads `get_last_bow_power` (D:14564).
- **Magic:** every 100 ms `&magic_level += &magic`, capped at `&magic_cost`, paused while the inventory is open (D:5935). A cast runs `USE` only if `magic_level >= magic_cost`; holding the button repeats (D:14906-14943).
- **Experience:** awarded only if the kill's `last_hit` was the player; capped at 99,999 (D:615). The next level needs `100*level²` (D:235). When the animated counter reaches it, `&exp -= next` and `lraise.c raise()` runs (D:5866). The level-32 cap and the +1 stat/+3 life rewards are in that script. The engine has no stat caps.
- **Death:** when displayed life drops below 1, `dinfo.c die()` runs (D:5959).

**Brains** (dispatch D:16852-16880):

| # | Behaviour |
|---|---|
| 0 | None; honours `move` and `follow` only. |
| 1 | Player (D:14683). |
| 2 | Bounce off screen edges using `mx/my`. |
| 3 | Duck: random diagonal walk (1-in-12 chance per idle think), quacks and pauses, bounces at edges and off hardness. First hit turns it into a headless runner (base 110) and spawns a head; second hit kills it and runs `DUCKDIE` (D:12723). |
| 4 | Pig: like the duck with pig sounds; when hitpoints run out it becomes seq 164 with brain 7 (D:13356). |
| 5 | Play the sequence once, then stamp the last frame into the background and deactivate (corpses, blood) (D:15741). |
| 6 | Loop the sequence. |
| 7 | Play once, then deactivate. |
| 8 | Text sprite. |
| 9 | Diagonal monster (D:12887): takes damage, dies via the `DIE` script plus a death sprite. With a target inside `distance` (default 5) and `attack_wait` elapsed, it faces a cardinal direction and plays `base_attack+dir`, or runs script `ATTACK`. Otherwise it steers at the target every 200 ms or wanders on diagonals, reversing on hardness. |
| 10 | Cardinal monster (D:13234): same damage handling; calls script `ATTACK` when it has a target; wanders in cardinal directions. |
| 11 | Missile, looping animation. |
| 12 | Scale `size` toward `brain_parm` by 5 per think, then deactivate (D:15798). |
| 13 | Mouse cursor; a click runs `CLICK` on sprites with touch damage -1 (D:14477). |
| 14 | Button: runs `BUTTONON`/`BUTTONOFF` as the player's point enters or leaves its hardbox (D:16271). |
| 15 | Shadow: copies the position and size of sprite `brain_parm`. |
| 16 | People (D:13087): alternates standing for 400-3400 ms and walking diagonally for 500-3500 ms; turns at edges and on hardness. |
| 17 | Missile that dies when its animation ends. |

## 4. DinkC VM

- **Interpreter:** source text is re-tokenised on every execution. A script instance is a `refinfo` (dink.h:385) plus the whole file text. Procedures are found by scanning lines for `void <name>(`, case-insensitive (D:3717). `process_line` is one long chain of string compares (D:7070-11458).
- **Limits:** 400 instances, 200 callbacks, 250 variables in one table shared by globals and locals, names up to 19 characters including `&`, 512-character lines, 128 KB files, 200-character say text, 20 choices of 100 characters.
- **Variables:** scope 0 is global and is what gets saved; otherwise the scope is the script instance id and the variable dies with the script. Lookup is local first, then global (D:3920). Values are substituted into lines as text, longest name first (D:3981-4024).
- **Pseudo-variables:** `&current_sprite`, `&current_script`, `&return`, `&arg1..&arg9`, and in choices `&savegameinfo` and `&buttoninfo`.
- **Engine-bound globals**, which must be created in `main.c` (D:1086-1140): `&exp &strength &defense &cur_weapon &cur_magic &gold &magic &magic_level &vision &result &speed &timing &lifemax &life &level &player_map &last_text &update_status &missile_target &enemy_sprite &magic_cost &missle_source`. `&speed` and `&timing` are bound but never read.
- **Yield and resume:** `wait(ms)` registers a callback and returns; `process_callbacks` re-enters at the saved byte offset (D:8034, 11602). Other yielding calls: `say_stop*` (resumes when the text sprite dies), `move_stop`, `choice_start`, `show_bmp`, `wait_for_button`, `fade_up/down`, `draw_screen`, `load_game`, `restart_game`, `kill_game`.
- **Calls:** calling a local procedure or `external("file","proc",args)` loads a new instance with `proc_return` set to the caller. The caller yields and is resumed when the callee ends, with the result in `&return` (D:11326-11432).
- **`spawn`** creates a script owned by "sprite 1000", which survives screen changes; `script_attach(1000)` does the same for the current script (D:8181, 8075).
- **Engine-invoked procedures:** `main`, `talk`, `hit`, `die`, `duckdie`, `touch`, `push`, `attack`, `damage`, `click`, `buttonon`, `buttonoff`; for items `use`, `arm`, `armmovie`, `disarm`, `pickup`, `drop`, `holdingdrop`; plus `raise` and `die` in the two system scripts.
- **Scripts the engine loads by name:** `main`, `start`, `newgame`, `escape`, `button4`, `button6`..`button10`, `dnotalk`, `dnomagic`, `lraise`, `dinfo`.

**Built-ins** (all compared at D:7380-11326):
- **Flow and variables:** `if else return goto int make_global_int make_global_function external spawn run_script_by_number kill_this_task script_attach wait set_callback_random callback_kill debug LOGMSG breakpoint var_used scripts_used random inside_box math_abs math_sin math_cos math_tan math_sqrt math_mod`, and operators `= += -= *= /= * /`.
- **Text and UI:** `say say_stop say_stop_npc say_xy say_stop_xy choice_start busy show_bmp copy_bmp_to_screen wait_for_button stop_wait_for_button draw_status set_font_color initfont show_inventory show_quick_message SHOW_POPUP set_save_game_info`.
- **Sprite properties (`sp_*`):** `sp sp_x sp_y sp_mx sp_my sp_move_x sp_move_y sp_dir sp_speed sp_timing sp_size sp_que sp_brain sp_brain_parm sp_brain_parm2 sp_seq sp_pseq sp_pframe sp_frame sp_frame_delay sp_reverse sp_picfreeze sp_nodraw sp_noclip sp_nocontrol sp_active sp_disabled sp_kill sp_kill_wait sp_hard sp_nohit sp_notouch sp_touch_damage sp_hitpoints sp_strength sp_defense sp_exp sp_gold sp_range sp_distance sp_target sp_follow sp_attack_wait sp_attack_hit_sound sp_attack_hit_sound_speed sp_base_walk sp_base_idle sp_base_attack sp_base_hit sp_base_die sp_base_death sp_flying sp_move_nohard sp_freeze sp_sound sp_script sp_editor_num sp_custom sp_blood_seq sp_blood_num sp_clip_left sp_clip_top sp_clip_right sp_clip_bottom`.
- **Sprites and world:** `create_sprite move move_stop freeze unfreeze hurt kill_shadow is_script_attached get_sprite_with_this_brain get_next_sprite_with_this_brain get_rand_sprite_with_this_brain compare_sprite_script disable_all_sprites enable_all_sprites preload_seq init draw_screen draw_background draw_hard_map draw_hard_sprite load_screen force_vision fill_screen fade_up fade_down screenlock stop_entire_game dink_can_walk_off_screen push_active editor_type editor_seq editor_frame clear_editor_info map_tile map_hard_tile load_map load_palette load_tile set_smooth_follow`.
- **Player and inventory:** `add_item add_magic add_exp kill_this_item kill_this_magic kill_cur_item kill_cur_magic free_items free_magic count_item count_magic get_item get_magic compare_weapon compare_magic arm_weapon arm_magic activate_bow get_last_bow_power set_dink_speed get_dinkspeed set_dink_base_push set_button set_keep_mouse set_mode`.
- **Audio:** `playmidi stopmidi loopmidi turn_midi_on turn_midi_off stopcd playsound load_sound sound_set_vol sound_set_kill sound_set_survive kill_all_sounds set_music_vol`.
- **System:** `save_game load_game game_exist restart_game kill_game reset_timer get_version get_burn get_truecolor get_time_game get_time_real get_date_year get_date_month get_date_day`.
- **HD only:** `get_client_fork get_client_version get_platform is_base_game set_use_latest_fixes_level set_gfx_alttext_disable set_disable_savestates`.

**`say` rules:**
- Leading backtick codes pick the colour: `1`-`9`, `0`=10, `!`=11, `@`=12, `#`=13, `$`=14 (the default, yellow), `%`=15 (white); RGB table at D:11709.
- The text is a brain-8 sprite at `owner.x - 75`, `owner.y - (frameHeight - yoffset + 100)`, word-wrapped and centred in a 150-px box, shifted to stay under x=620 (D:4515-4553, 11833-11845).
- Lifetime is `max(2700, 77 * strlen)` ms (dink.h:235). The Talk button skips the line while the player is frozen (D:14751).
- Owner 1000 means no owner; `say_xy` uses a 620-px-wide box.

**Choice menus** (D:5072-5232): between `choice_start()` and `choice_end()` the parser accepts bare `set_y N`, `set_title_color N`, a `title_start(); ... title_end();` block, and lines of the form `(cond) "text"`. `&result` is the 1-based ordinal counting hidden options too.

## 5. HD additions over 1.08

- Fixed 60 Hz step and smooth screen scrolling.
- Full state saves: `quicksave.dat` (F5/F9), `autosave.dat` every 5 minutes when life is above 30%, and `continue_state.dat` on exit (D:18689, 19018-19055; GameMenu.cpp:20, 1164).
- Turbo: Tab runs 3 logic frames per render; Shift and Ctrl raise that to 9 and 25 (GameMenu.cpp:1128-1155).
- Touch controls and virtual buttons (`source/Component/`), gamepads through Proton providers, and a DMOD browser, URL installer and `.dmod` unpacker (`source/GUI/BrowseMenu.cpp`, `DMODInstallMenu.cpp`).
- PNG and true-colour art, OGG substitutes for MIDI, raised limits (dink.h:190-199), `sp_custom`, text backdrops.
- DinkC `get_version()` returns 114 (dink.h:196); the app is V2.08 (App.cpp:366).
- **Rendering:** a DirectDraw-style shim over fixed-function OpenGL (`source/video_gl.cpp`). There is no shader pipeline. The 640x480 image is scaled with aspect correction; the game is 4:3 only, with an optional stretch and bilinear "smoothing".
- **Platforms** (INSTALL.md:5-14): Windows (Visual Studio, FMOD), Linux (CMake, SDL2, Flatpak), macOS and iOS (Xcode), Android (Gradle and CMake), HTML5 (Emscripten).

## 6. UI

- **Status bar:** seq 180 frame 3 (640x80 at y=400), with frames 1 and 2 as the side bars (D:3034).
  - Strength, defense, magic: 3 digits at (81,415), (81,437), (81,459), seqs 182-184.
  - Gold: 5 digits at (298,457), seq 185. Exp `00000/00000` at (404,459), seq 181. Level at (523 or 528, 456), seq 442.
  - Health: seq 190 (max) and 451 (current) from (284,412), 10 HP per segment, wrapping after 110, capped at 220.
  - Weapon icon at (557,413), magic icon at (153,413).
  - Magic charge: a four-edge frame of seq 180 frames 6 and 7 around the magic icon, 25% per edge (D:2982).
- **Inventory** (D:16313-16636): background seq 423 frame 1 at (20,0). Magic is 2x4 from (45,83); items are 4x4 from (260,83); cells are 65x55 with an 83/75 pitch. That gives 8 magic and 16 item slots. The selector blinks between frames 2 and 3 every 400 ms; frames 4 and 5 mark the armed weapon and magic.
- **Choice box** (D:15895): seq 30 frames 2-4 at (48,44); text column x 184..463 from y=94 (or `set_y`); the selected line is white and the rest yellow; animated arrows are seqs 456/457 at x=126 and 462; paging happens when text passes y=335.
- **Map (button 6):** `button6.c` calls `show_bmp("tiles\map1.bmp", 1, 0)`. The engine draws the seq-165 dot at `((last_map-1)%32*20, (last_map-1)/32*20)` (D:16743).
- **Title screen:** DinkC (`start.c`) with a brain-13 cursor and buttons. HD wraps it in a native menu (New, Load, Continue, Add-ons, Options, About) and an F1 pause menu.
- **Fonts:** Proton bitmap fonts `interface/font_normal.rtfont` and `font_big.rtfont` (App.cpp:684-689), not the original TrueType; text scale is 0.88 on desktop.

## 7. Testing and debug hooks

- `-autotest` (`source/AutoTester.cpp`) is a UI smoke test: screenshots, DMOD install, new game. It makes no gameplay assertions. `tests/` holds only `dmod_cleanup.cpp` and `html5_loader.cjs`.
- Other flags: `-game <dmod>`, `-debug`, `-window`, `-skip`.
- Debug menu (`source/GUI/DebugMenu.cpp`): ghost walk (ignores hardness and screenlock), stat, gold and life cheats, DinkC debug logging (also Alt+D on Windows) which draws hit boxes, and force-save to slot 9. Button 7 draws the collision map when cheats are on (D:17456).
- **Best harness hook:** `SaveState` is a raw dump of `DinkGlobalsStatic`, all script instances with their text, and the full sprite array (D:18689-18731), so a reference run can be snapshotted and diffed.
- A screen warp can be scripted: set `&player_map`, then `load_screen(); draw_screen();`. `debug()` and `LOGMSG` write to `log.txt`.
- **Determinism:** logic uses C `rand()` at 41 call sites, and there is no `srand` anywhere in this repo. Whether Proton seeds it is unverified, so plan to patch in a fixed seed. The fixed 16.67 ms step helps, but script callbacks use the app game tick rather than `g_dinkTick` (D:11604).

## 8. Embedding an interpreter versus transpiling

The code points strongly toward embedding a faithful interpreter:
- **Loose parser.** Missing semicolons are accepted, and identifiers are case-insensitive (`Playsound`, `Debug`).
- **Compatibility bugs kept on purpose.** In `if (func() <op> x)`, the `<=`, `>=` and `!=` cases are all caught by the first `strchr(temp,'=')` branch (D:7171-7241). `/=` is deliberately broken unless `set_use_latest_fixes_level(1)` (D:11292).
- **Textual variable substitution** inside strings and expressions.
- **Runtime-mutable assets.** Scripts call `init("load_sequence_now ...")` to re-point sequences; every weapon's `arm()` does this. `load_tile`, `load_map`, `load_palette`, `map_tile` and `map_hard_tile` also change data at runtime.
- **Cooperative-yield semantics** that scripts depend on: `kill_this_task`, `script_attach(1000)`, and `sp_script` killing a sprite's previous scripts.
- **Stateful quirks:** values returned through `&return`/`&result`, `sp_*` returning -1 for dead sprites, the inverted `hard` flag, and the `&vision` reset on load.

A transpiler would have to reproduce all of this and would still not run DMODs, which ship raw `.c`/`.d` and their own `dink.ini`. The base game alone has 381 scripts.
